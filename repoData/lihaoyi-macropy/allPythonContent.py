__FILENAME__ = macro_module
from macropy.core.macros import *
from macropy.core.quotes import macros, q, u

_ = None  # makes IDE happy

macros = Macros()

@macros.expr
def f(tree, **kw):
    names = ('arg' + str(i) for i in xrange(100))

    @Walker
    def underscore_search(tree, collect, **kw):
        if isinstance(tree, Name) and tree.id == "_":
            name = names.next()
            tree.id = name
            collect(name)
            return tree

    tree, used_names = underscore_search.recurse_collect(tree)

    new_tree = q[lambda: ast[tree]]
    new_tree.args.args = [Name(id = x) for x in used_names]
    return new_tree
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import target

########NEW FILE########
__FILENAME__ = target
from macro_module import macros, f, _

my_func = f[_ + (1 * _)]
print my_func(10, 20) # 30

print reduce(f[_ + _], [1, 2, 3])  # 6
print filter(f[_ % 2 != 0], [1, 2, 3])  # [1, 3]
print map(f[_  * 10], [1, 2, 3])  # [10, 20, 30]

########NEW FILE########
__FILENAME__ = macro_module
from macropy.core.macros import *

macros = Macros()

@macros.expr
def expand(tree, **kw):
    return tree


########NEW FILE########
__FILENAME__ = run
import macropy.activate
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.first_macro.nop.macro_module import macros, expand

print expand[1 + 2]

########NEW FILE########
__FILENAME__ = macro_module
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
macros = Macros()

@macros.expr
def expand(tree, **kw):
    addition = 10
    return q[lambda x: x * ast[tree] + u[addition]]

########NEW FILE########
__FILENAME__ = run
import macropy.activate
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.first_macro.quasiquote.macro_module import macros, expand

func = expand[1 + 2]
print func(5)

########NEW FILE########
__FILENAME__ = macro_module
from macropy.core.macros import *
from macropy.core.quotes import macros, q, u

_ = None  # makes IDE happy

macros = Macros()

@macros.expr
def f(tree, gen_sym, **kw):


    @Walker
    def underscore_search(tree, collect, **kw):
        if isinstance(tree, Name) and tree.id == "_":
            name = gen_sym()
            tree.id = name
            collect(name)
            return tree

    tree, used_names = underscore_search.recurse_collect(tree)

    new_tree = q[lambda: ast[tree]]
    new_tree.args.args = [Name(id = x) for x in used_names]
    return new_tree
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import macro_module
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.hygiene.gen_sym.macro_module import macros, f, _

arg0 = 10

func = f[_ + arg0]

# prints 11, using `gen_sym`. Otherwise it would print `2`
print func(1)

########NEW FILE########
__FILENAME__ = macro_module
from macropy.core.macros import *
from macropy.core.quotes import macros, q, u

_ = None  # makes IDE happy

macros = Macros()

@macros.expr
def f(tree, **kw):
    names = ('arg' + str(i) for i in xrange(100))

    @Walker
    def underscore_search(tree, collect, **kw):
        if isinstance(tree, Name) and tree.id == "_":
            name = names.next()
            tree.id = name
            collect(name)
            return tree

    tree, used_names = underscore_search.recurse_collect(tree)

    new_tree = q[lambda: ast[tree]]
    new_tree.args.args = [Name(id = x) for x in used_names]
    return new_tree
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import macro_module
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.hygiene.hygiene_failures.macro_module import macros, f, _

arg0 = 10

func = f[_ + arg0]

print func(1)
# 2
# should print 11
########NEW FILE########
__FILENAME__ = macro_module
# macro_module.py
from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, u

macros = Macros()

@macros.expr
def log(tree, exact_src, **kw):
    new_tree = hq[wrap(u[exact_src(tree)], ast[tree])]
    return new_tree

def wrap(txt, x):
    print txt + " -> " + repr(x)
    return x
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import macro_module
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.hygiene.hygienic_quasiquotes.macro_module import macros, log

wrap = 3 # try to confuse it

log[1 + 2 + 3]
# 1 + 2 + 3 -> 6
# it still works despite trying to confuse it with `wraps`

########NEW FILE########
__FILENAME__ = macro_module
# macro_module.py
from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, u, unhygienic

macros = Macros()

@macros.expr
def log(tree, exact_src, **kw):
    new_tree = hq[wrap(unhygienic[log_func], u[exact_src(tree)], ast[tree])]
    return new_tree


def wrap(printer, txt, x):
    printer(txt + " -> " + repr(x))
    return x

@macros.expose_unhygienic
def log_func(txt):
    print txt
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import macro_module
import target
########NEW FILE########
__FILENAME__ = target
from docs.examples.hygiene.unhygienic.macro_module import macros, log

buffer = []
def log_func(txt):
    buffer.append(txt)

log[1 + 2 + 3]
log[1 + 2]
# doesn't print anything

print buffer
# ['1 + 2 + 3 -> 6', '1 + 2 -> 3']
########NEW FILE########
__FILENAME__ = run
import macropy.activate
import target
########NEW FILE########
__FILENAME__ = target
from macropy.case_classes import macros, case

@case
class Point(x, y): pass

p = Point(1, 2)

print str(p) # Point(1, 2)
print p.x    # 1
print p.y    # 2
print Point(1, 2) == Point(1, 2) # True
x, y = p
print x, y   # (1, 2)
########NEW FILE########
__FILENAME__ = activate
"""Shorthand import to initialize MacroPy"""
import macropy

macropy.activate()

########NEW FILE########
__FILENAME__ = case_classes
"""Macro providing an extremely concise way of declaring classes"""
from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, name, unhygienic, u
from macropy.core.analysis import Scoped
macros = Macros()

def apply(f):
    return f()


class CaseClass(object):
    __slots__ = []

    def copy(self, **kwargs):
        old = map(lambda a: (a, getattr(self, a)), self._fields)
        new = kwargs.items()
        return self.__class__(**dict(old + new))

    def __str__(self):
        return self.__class__.__name__ + "(" + ", ".join(str(getattr(self, x)) for x in self.__class__._fields) + ")"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        try:
            return self.__class__ == other.__class__ \
                and all(getattr(self, x) == getattr(other, x) for x in self.__class__._fields)
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        for x in self.__class__._fields:
            yield getattr(self, x)


class Enum(object):
    def __new__(cls, *args, **kw):
        if not hasattr(cls, "all"):
            cls.all = []
        thing = object.__new__(cls, *args, **kw)
        cls.all.append(thing)
        return thing

    @property
    def next(self):
        return self.__class__.all[(self.id + 1) % len(self.__class__.all)]
    @property
    def prev(self):
        return self.__class__.all[(self.id - 1) % len(self.__class__.all)]

    def __str__(self):
        return self.__class__.__name__ + "." + self.name

    def __repr__(self):
        return self.__str__()


    def __iter__(self):
        for x in self.__class__._fields:
            yield getattr(self, x)

def enum_new(cls, **kw):
    if len(kw) != 1:
        raise TypeError("Enum selection can only take exactly 1 named argument: " + len(kw) + " found.")

    [(k, v)] = kw.items()

    for value in cls.all:
        if getattr(value, k) == v:
            return value

    raise ValueError("No Enum found for %s=%s" % (k, v))

def noop_init(*args, **kw):
    pass

def extract_args(bases):
    args = []
    vararg = None
    kwarg = None
    defaults = []
    for base in bases:
        if type(base) is Name:
            args.append(base.id)

        elif type(base) is List:
            vararg = base.elts[0].id

        elif type(base) is Set:
            kwarg = base.elts[0].id

        elif type(base) is BinOp and type(base.op) is BitOr:
            args.append(base.left.id)
            defaults.append(base.right)
        else:
            assert False, "Illegal expression in case class signature: " + unparse(base)

    all_args = args[:]
    if vararg:
        all_args.append(vararg)
    if kwarg:

        all_args.append(kwarg)
    return args, vararg, kwarg, defaults, all_args


def find_members(tree, name):
    @Scoped
    @Walker
    def find_member_assignments(tree, collect, stop, scope, **kw):
        if name in scope.keys():
            stop()
        elif type(tree) is Assign:
            self_assigns = [
                t.attr for t in tree.targets
                if type(t) is Attribute
                and type(t.value) is Name
                and t.value.id == name
            ]
            map(collect, self_assigns)
    return find_member_assignments.collect(tree)

def split_body(tree, gen_sym):
        new_body = []
        outer = []
        init_body = []
        for statement in tree.body:
            if type(statement) is ClassDef:
                outer.append(case_transform(statement, gen_sym, [Name(id=tree.name)]))
                with hq as a:
                    name[tree.name].b = name[statement.name]
                a_old = a[0]
                a_old.targets[0].attr = statement.name

                a_new = parse_stmt(unparse(a[0]))[0]
                outer.append(a_new)
            elif type(statement) is FunctionDef:
                new_body.append(statement)
            else:
                init_body.append(statement)
        return new_body, outer, init_body


def prep_initialization(init_fun, args, vararg, kwarg, defaults, all_args):

    init_fun.args = arguments(
        args = [Name(id="self")] + [Name(id = id) for id in args],
        vararg = vararg,
        kwarg = kwarg,
        defaults = defaults
    )

    for x in all_args:
        with hq as a:
            unhygienic[self.x] = name[x]

        a[0].targets[0].attr = x

        init_fun.body.append(a[0])


def shared_transform(tree, gen_sym, additional_args=[]):
    with hq as methods:
        def __init__(self, *args, **kwargs):
            pass

        _fields = []
        _varargs = None
        _kwargs = None
        __slots__ = []

    init_fun, set_fields, set_varargs, set_kwargs, set_slots, = methods

    args, vararg, kwarg, defaults, all_args = extract_args(
        [Name(id=x) for x in additional_args] + tree.bases
    )

    if vararg:
        set_varargs.value = Str(vararg)

    if kwarg:
        set_kwargs.value = Str(kwarg)

    nested = [
        n
        for f in tree.body
        if type(f) is FunctionDef
        if len(f.args.args) > 0
        for n in find_members(f.body, f.args.args[0].id)
    ]

    additional_members = find_members(tree.body, "self") + nested

    prep_initialization(init_fun, args, vararg, kwarg, defaults, all_args)
    set_fields.value.elts = map(Str, args)
    set_slots.value.elts = map(Str, all_args + additional_members)
    new_body, outer, init_body = split_body(tree, gen_sym)
    init_fun.body.extend(init_body)
    tree.body = new_body
    tree.body = methods + tree.body

    return outer


def case_transform(tree, gen_sym, parents):

    outer = shared_transform(tree, gen_sym)

    tree.bases = parents
    assign = FunctionDef(
        gen_sym("prepare_"+tree.name),
        arguments([], None, None, []),
        outer,
        [hq[apply]]
    )
    return [tree] + ([assign] if len(outer) > 0 else [])

@macros.decorator
def case(tree, gen_sym, **kw):
    """Macro providing an extremely concise way of declaring classes"""
    x = case_transform(tree, gen_sym, [hq[CaseClass]])

    return x


@macros.decorator
def enum(tree, gen_sym, exact_src, **kw):

    count = [0]
    new_assigns = []
    new_body = []
    def handle(expr):
        assert type(expr) in (Name, Call), stmt.value
        if type(expr) is Name:
            expr.ctx = Store()
            self_ref = Attribute(value=Name(id=tree.name), attr=expr.id)
            with hq as code:
                ast[self_ref] = name[tree.name](u[count[0]], u[expr.id])
            new_assigns.extend(code)
            count[0] += 1

        elif type(expr) is Call:
            assert type(expr.func) is Name
            self_ref = Attribute(value=Name(id=tree.name), attr=expr.func.id)
            id = expr.func.id
            expr.func = Name(id=tree.name)

            expr.args = [Num(count[0]), Str(id)] + expr.args
            new_assigns.append(Assign([self_ref], expr))
            count[0] += 1

    for stmt in tree.body:
        try:
            if type(stmt) is Expr:
                assert type(stmt.value) in (Tuple, Name, Call)
                if type(stmt.value) is Tuple:
                    map(handle, stmt.value.elts)
                else:
                    handle(stmt.value)
            elif type(stmt) is FunctionDef:
                new_body.append(stmt)
            else:
                assert False

        except AssertionError as e:
            assert False, "Can't have `%s` in body of enum" % unparse(stmt).strip("\n")

    tree.body = new_body + [Pass()]

    shared_transform(tree, gen_sym, additional_args=["id", "name"])

    with hq as code:
        name[tree.name].__new__ = staticmethod(enum_new)
        name[tree.name].__init__ = noop_init


    tree.bases = [hq[Enum]]

    return [tree] + new_assigns + code
########NEW FILE########
__FILENAME__ = console
"""Shorthand import to initialize the MacroPy console"""
import macropy.activate
macropy.console()
########NEW FILE########
__FILENAME__ = analysis
"""Walker that performs simple name-binding analysis as it traverses the AST"""
from walkers import *
from macropy.core import merge_dicts

__all__ = ['Scoped']
@Walker
def find_names(tree, collect, stop, **kw):
    if type(tree) in [Attribute, Subscript]:
        stop()
    if isinstance(tree, Name):
        collect((tree.id, tree))

@Walker
def find_assignments(tree, collect, stop, **kw):
    if type(tree) in [ClassDef, FunctionDef]:
        collect((tree.name, tree))
        stop()
    if type(tree) is Assign:
        for x in find_names.collect(tree.targets):
            collect(x)


def extract_arg_names(args):
    return dict(
        ([(args.vararg, args.vararg)] if args.vararg else []) +
        ([(args.kwarg, args.kwarg)] if args.kwarg else []) +
        [pair for x in args.args for pair in find_names.collect(x)]
    )

class Scoped(Walker):
    """
    Used in conjunction with `@Walker`, via

    @Scoped
    @Walker
    def my_func(tree, scope, **kw):
        ...

    This decorator wraps the `Walker` and injects in a `scope` argument into
    the function. This argument is a dictionary of names which are in-scope
    in the present `tree`s environment, starting from the `tree` on which the
    recursion was start.

    This can be used to track the usage of a name binding through the AST
    snippet, and detecting when the name gets shadowed by a more tightly scoped
    name binding.
    """

    def __init__(self, walker):
        self.walker = walker

    def recurse_collect(self, tree, sub_kw=[], **kw):

        kw['scope'] = kw.get('scope', dict(find_assignments.collect(tree)))
        return Walker.recurse_collect(self, tree, sub_kw, **kw)

    def func(self, tree, set_ctx_for, scope, **kw):
        def extend_scope(tree, *dicts, **kw):
            new_scope = merge_dicts(*([scope] + list(dicts)))
            if "remove" in kw:
                for rem in kw['remove']:
                    del new_scope[rem]

            set_ctx_for(tree, scope=new_scope)
        if type(tree) is Lambda:
            extend_scope(tree.body, extract_arg_names(tree.args))

        if type(tree) in (GeneratorExp, ListComp, SetComp, DictComp):
            iterator_vars = {}
            for gen in tree.generators:
                extend_scope(gen.target, iterator_vars)
                extend_scope(gen.iter, iterator_vars)
                iterator_vars.update(dict(find_names.collect(gen.target)))
                extend_scope(gen.ifs, iterator_vars)

            if type(tree) is DictComp:
                extend_scope(tree.key, iterator_vars)
                extend_scope(tree.value, iterator_vars)
            else:
                extend_scope(tree.elt, iterator_vars)

        if type(tree) is FunctionDef:

            extend_scope(tree.args, {tree.name: tree})
            extend_scope(
                tree.body,
                {tree.name: tree},
                extract_arg_names(tree.args),
                dict(find_assignments.collect(tree.body)),
            )

        if type(tree) is ClassDef:
            extend_scope(tree.bases, remove=[tree.name])
            extend_scope(tree.body, dict(find_assignments.collect(tree.body)), remove=[tree.name])

        if type(tree) is ExceptHandler:
            extend_scope(tree.body, {tree.name.id: tree.name})

        if type(tree) is For:
            extend_scope(tree.body, dict(find_names.collect(tree.target)))

        return self.walker.func(
            tree,
            set_ctx_for=set_ctx_for,
            scope=scope,
            **kw
        )
########NEW FILE########
__FILENAME__ = cleanup
"""Filters used to touch up the not-quite-perfect ASTs that we allow macros
to return."""


from ast import *
from macropy.core.util import register
from macros import filters
from walkers import Walker


@register(filters)
def fix_ctx(tree, **kw):
    return ast_ctx_fixer.recurse(tree, ctx=Load())


@Walker
def ast_ctx_fixer(tree, stop, set_ctx, set_ctx_for, **kw):
    ctx = kw.get("ctx", None)
    """Fix any missing `ctx` attributes within an AST; allows you to build
    your ASTs without caring about that stuff and just filling it in later."""
    if "ctx" in type(tree)._fields and (not hasattr(tree, "ctx") or tree.ctx is None):
        tree.ctx = ctx

    if type(tree) is arguments:
        set_ctx_for(tree.args, ctx=Param())
        set_ctx_for(tree.defaults, ctx=Load())

    if type(tree) is AugAssign:
        set_ctx_for(tree.target, ctx=AugStore())
        set_ctx_for(tree.value, ctx=AugLoad())

    if type(tree) is Attribute:
        set_ctx_for(tree.value, ctx=Load())

    if type(tree) is Assign:
        set_ctx_for(tree.targets, ctx=Store())
        set_ctx_for(tree.value, ctx=Load())

    if type(tree) is Delete:
        set_ctx_for(tree.targets, ctx=Del())



@register(filters)
def fill_line_numbers(tree, lineno, col_offset, **kw):
    """Fill in line numbers somewhat more cleverly than the
    ast.fix_missing_locations method, which doesn't take into account the
    fact that line numbers are monotonically increasing down lists of AST
    nodes."""
    if type(tree) is list:
        for sub in tree:
            if isinstance(sub, AST) \
                    and hasattr(sub, "lineno") \
                    and hasattr(sub, "col_offset") \
                    and (sub.lineno, sub.col_offset) > (lineno, col_offset):

                lineno = sub.lineno
                col_offset = sub.col_offset

            fill_line_numbers(sub, lineno, col_offset)
    elif isinstance(tree, AST):
        if not (hasattr(tree, "lineno") and hasattr(tree, "col_offset")):
            tree.lineno = lineno
            tree.col_offset = col_offset
        for name, sub in iter_fields(tree):
            fill_line_numbers(sub, tree.lineno, tree.col_offset)

    return tree


########NEW FILE########
__FILENAME__ = console
"""Implementation and activation of a basic macro-powered REPL."""
import code
import ast

import sys

from macropy.core.macros import expand_entire_ast, detect_macros


class MacroConsole(code.InteractiveConsole):
    def __init__(self, locals=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.bindings = []


    def runsource(self, source, filename="<input>", symbol="single"):
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            code = ""
            pass

        if code is None:
            # This means it's incomplete
            return True

        try:
            tree = ast.parse(source)
            bindings = detect_macros(tree)

            for p, names in bindings:
                __import__(p)

            self.bindings.extend([(sys.modules[p], bindings) for (p, bindings) in bindings])

            tree = expand_entire_ast(tree, source, self.bindings)

            tree = ast.Interactive(tree.body)
            code = compile(tree, filename, symbol, self.compile.compiler.flags, 1)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            self.showsyntaxerror(filename)
            # This means there's a syntax error
            return False

        self.runcode(code)
        # This means it was successfully compiled; `runcode` takes care of
        # any runtime failures
        return False


########NEW FILE########
__FILENAME__ = exact_src
"""Logic related to lazily performing the computation necessary to finding
the source extent of an AST.

Exposed to each macro as an `exact_src` funciton."""

from macropy.core import unparse
from macropy.core.macros import injected_vars
from ast import *
from macropy.core.util import Lazy, distinct, register
from walkers import Walker


def linear_index(line_lengths, lineno, col_offset):
    prev_length = sum(line_lengths[:lineno-1]) + lineno-2
    out = prev_length + col_offset + 1
    return out

@Walker
def indexer(tree, collect, **kw):
    try:
        unparse(tree)
        collect((tree.lineno, tree.col_offset))
    except Exception, e:
        pass

_transforms = {
    GeneratorExp: "(%s)",
    ListComp: "[%s]",
    SetComp: "{%s}",
    DictComp: "{%s}"
}


@register(injected_vars)
def exact_src(tree, src, **kw):

    def exact_src_imp(tree, src, indexes, line_lengths):
        all_child_pos = sorted(indexer.collect(tree))
        start_index = linear_index(line_lengths(), *all_child_pos[0])

        last_child_index = linear_index(line_lengths(), *all_child_pos[-1])

        first_successor_index = indexes()[min(indexes().index(last_child_index)+1, len(indexes())-1)]

        for end_index in range(last_child_index, first_successor_index+1):

            prelim = src[start_index:end_index]
            prelim = _transforms.get(type(tree), "%s") % prelim


            if isinstance(tree, stmt):
                prelim = prelim.replace("\n" + " " * tree.col_offset, "\n")

            if isinstance(tree, list):
                prelim = prelim.replace("\n" + " " * tree[0].col_offset, "\n")

            try:
                if isinstance(tree, expr):
                    x = "(" + prelim + ")"
                else:
                    x = prelim
                import ast
                parsed = ast.parse(x)
                if unparse(parsed).strip() == unparse(tree).strip():
                    return prelim

            except SyntaxError as e:
                pass
        raise ExactSrcException()

    positions = Lazy(lambda: indexer.collect(tree))
    line_lengths = Lazy(lambda: map(len, src.split("\n")))
    indexes = Lazy(lambda: distinct([linear_index(line_lengths(), l, c) for (l, c) in positions()] + [len(src)]))
    return lambda t: exact_src_imp(t, src, indexes, line_lengths)
class ExactSrcException(Exception):
    pass

########NEW FILE########
__FILENAME__ = exporters
"""Ways of dealing with macro-expanded code, e.g. caching or re-serializing it."""
import os
import shutil
from macropy.core import unparse
from py_compile import wr_long
import marshal
import imp
class NullExporter(object):
    def export_transformed(self, code, tree, module_name, file_name):
        pass

    def find(self, file, pathname, description, module_name, package_path):
        pass

class SaveExporter(object):
    def __init__(self, directory="exported", root=os.getcwd()):
        self.root = root
        self.directory = directory
        shutil.rmtree(directory, ignore_errors=True)
        shutil.copytree(root, directory)

    def export_transformed(self, code, tree, module_name, file_name):

        new_path = os.path.join(
            self.root,
            self.directory,
            os.path.relpath(file_name, self.root)
        )

        with open(new_path, "w") as f:
            f.write(unparse(tree))

    def find(self, file, pathname, description, module_name, package_path):
        pass

suffix = __debug__ and 'c' or 'o'
class PycExporter(object):
    def __init__(self, root=os.getcwd()):
        self.root = root

    def export_transformed(self, code, tree, module_name, file_name):
        f = open(file_name + suffix , 'wb')
        f.write('\0\0\0\0')
        timestamp = long(os.fstat(f.fileno()).st_mtime)
        wr_long(f, timestamp)
        marshal.dump(code, f)
        f.flush()
        f.seek(0, 0)
        f.write(imp.get_magic())

    def find(self, file, pathname, description, module_name, package_path):

        try:
            f = open(file.name + suffix, 'rb')
            py_time = os.fstat(file.fileno()).st_mtime
            pyc_time = os.fstat(f.fileno()).st_mtime

            if py_time > pyc_time:
                return None
            x = imp.load_compiled(module_name, pathname + suffix, f)
            return x
        except Exception, e:
            print e

########NEW FILE########
__FILENAME__ = failure
"""Transform macro expansion errors into runtime errors with nice stack traces.
T"""

from macropy.core.macros import *

from macropy.core.hquotes import macros, hq
import traceback


class MacroExpansionError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def raise_error(ex):
    raise ex

@register(filters)
def clear_errors(tree, **kw):
    if isinstance(tree, Exception):
        tb = traceback.format_exc()
        msg = tree.message
        if type(tree) is not AssertionError or tree.args == ():
            msg = "".join(tree.args) + "\nCaused by Macro-Expansion Error:\n" + tb
        return hq[raise_error(MacroExpansionError(msg))]
    else:
        return tree

########NEW FILE########
__FILENAME__ = gen_sym
"""Logic related to generated a stream of unique symbols for macros to use.

Exposes this functionality as the `gen_sym` function.
"""

from macropy.core.macros import *

@register(injected_vars)
def gen_sym(tree, **kw):
    """Create a generator that creates symbols which are not used in the given
    `tree`. This means they will be hygienic, i.e. it guarantees that they will
    not cause accidental shadowing, as long as the scope of the new symbol is
    limited to `tree` e.g. by a lambda expression or a function body"""
    @Walker
    def name_finder(tree, collect, **kw):
        if type(tree) is Name:
            collect(tree.id)
        if type(tree) is Import:
            names = [x.asname or x.name for x in tree.names]
            map(collect, names)
        if type(tree) is ImportFrom:
            names = [x.asname or x.name for x in tree.names]
            map(collect, names)
        if type(tree) in (FunctionDef, ClassDef):
            collect(tree.name)

    found_names = set(name_finder.collect(tree))

    def name_for(name="sym"):

        if name not in found_names:
            found_names.add(name)
            return name
        offset = 1
        while name + str(offset) in found_names:

            offset += 1
        found_names.add(name + str(offset))
        return name + str(offset)
    return name_for


########NEW FILE########
__FILENAME__ = hquotes
"""Hygienic Quasiquotes, which pull in names from their definition scope rather
than their expansion scope."""
from macropy.core.macros import *

from macropy.core.quotes import macros, q, unquote_search, u, ast, ast_list, name
from macropy.core.analysis import Scoped

macros = Macros()

@macro_stub
def unhygienic():
    """Used to delimit a section of a hq[...] that should not be hygienified"""

from macros import filters, injected_vars, post_processing

@register(injected_vars)
def captured_registry(**kw):
    return []

@register(post_processing)
def post_proc(tree, captured_registry, gen_sym, **kw):
    if captured_registry == []:
        return tree

    unpickle_name = gen_sym("unpickled")
    with q as pickle_import:
        from pickle import loads as x

    pickle_import[0].names[0].asname = unpickle_name

    import pickle

    syms = [Name(id=sym) for val, sym in captured_registry]
    vals = [val for val, sym in captured_registry]

    with q as stored:
        ast_list[syms] = name[unpickle_name](u[pickle.dumps(vals)])

    from cleanup import ast_ctx_fixer
    stored = ast_ctx_fixer.recurse(stored)

    tree.body = map(fix_missing_locations, pickle_import + stored) + tree.body

    return tree

@register(filters)
def hygienate(tree, captured_registry, gen_sym, **kw):
    @Walker
    def hygienator(tree, stop, **kw):
        if type(tree) is Captured:
            new_sym = [sym for val, sym in captured_registry if val is tree.val]
            if not new_sym:
                new_sym = gen_sym(tree.name)

                captured_registry.append((tree.val, new_sym))
            else:
                new_sym = new_sym[0]
            return Name(new_sym, Load())

    return hygienator.recurse(tree)


@macros.block
def hq(tree, target, **kw):
    tree = unquote_search.recurse(tree)
    tree = hygienator.recurse(tree)
    tree = ast_repr(tree)

    return [Assign([target], tree)]


@macros.expr
def hq(tree, **kw):
    """Hygienic Quasiquote macro, used to quote sections of code while ensuring
    that names within the quoted code will refer to the value bound to that name
    when the code was quoted. Used together with the `u`, `name`, `ast`,
    `ast_list`, `unhygienic` unquotes."""
    tree = unquote_search.recurse(tree)
    tree = hygienator.recurse(tree)
    tree = ast_repr(tree)
    return tree


@Scoped
@Walker
def hygienator(tree, stop, scope, **kw):
    if type(tree) is Name and \
            type(tree.ctx) is Load and \
            tree.id not in scope.keys():

        stop()

        return Captured(
            tree,
            tree.id
        )

    if type(tree) is Literal:
        stop()
        return tree

    res = check_annotated(tree)
    if res:
        id, subtree = res
        if 'unhygienic' == id:
            stop()
            tree.slice.value.ctx = None
            return tree.slice.value


########NEW FILE########
__FILENAME__ = import_hooks
"""Plumbing related to hooking into the import process, unrelated to MacroPy"""

import sys
import imp
import ast
import macropy.activate
from macros import *
import traceback

class _MacroLoader(object):
    """Performs the loading of a module with macro expansion."""
    def __init__(self, mod):
        self.mod = mod


    def load_module(self, fullname):
        self.mod.__loader__ = self
        return self.mod


@singleton
class MacroFinder(object):
    """Loads a module and looks for macros inside, only providing a loader if
    it finds some."""
    def find_module(self, module_name, package_path):
        try:
            try:
                (file, pathname, description) = imp.find_module(
                    module_name.split('.')[-1],
                    package_path
                )

                txt = file.read()
            except:
                return

            # short circuit heuristic to fail fast if the source code can't
            # possible contain the macro import at all
            if "macros" not in txt:
                return

            # check properly the AST if the macro import really exists
            tree = ast.parse(txt)

            bindings = detect_macros(tree)

            if bindings == []:
                return # no macros found, carry on

            mod = macropy.exporter.find(file, pathname, description, module_name, package_path)

            if mod:
                return _MacroLoader(mod)

            for (p, _) in bindings:
                __import__(p)

            modules = [(sys.modules[p], bindings) for (p, bindings) in bindings]

            tree = expand_entire_ast(tree, txt, modules)

            ispkg = False
            mod = sys.modules.setdefault(module_name, imp.new_module(module_name))

            if ispkg:
                mod.__path__ = []
                mod.__package__ = module_name
            else:
                mod.__package__ = module_name.rpartition('.')[0]
            mod.__file__ = file.name
            code = compile(tree, file.name, "exec")


            try:
                exec code in mod.__dict__
                macropy.exporter.export_transformed(code, tree, module_name, file.name)
            except Exception as e:

                traceback.print_exc()

            return _MacroLoader(mod)

        except Exception, e:
            print e

            traceback.print_exc()
            pass

########NEW FILE########
__FILENAME__ = macros
"""The main source of all things MacroPy"""

import sys
import imp
import ast
import itertools
from ast import *
from util import *
from walkers import *


# Monkey Patching pickle to pickle module objects properly
import pickle
pickle.Pickler.dispatch[type(pickle)] = pickle.Pickler.save_global


class WrappedFunction(object):
    """Wraps a function which is meant to be handled (and removed) by macro
    expansion, and never called directly with square brackets."""

    def __init__(self, func, msg):
        self.func = func
        self.msg = msg
        import functools
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __getitem__(self, i):
        raise TypeError(self.msg.replace("%s", self.func.__name__))


def macro_function(func):
    """Wraps a function, to provide nicer error-messages in the common
    case where the macro is imported but macro-expansion isn't triggered"""
    return WrappedFunction(
        func,
        "Macro `%s` illegally invoked at runtime; did you import it "
        "properly using `from ... import macros, %s`?"
    )


def macro_stub(func):
    """Wraps a function that is a stub meant to be used by macros but never
    called directly."""
    return WrappedFunction(
        func,
        "Stub `%s` illegally invoked at runtime; is it used "
        "properly within a macro?"
    )


class Macros(object):
    """A registry of macros belonging to a module; used via

    ```python
    macros = Macros()

    @macros.expr
    def my_macro(tree):
        ...
    ```

    Where the decorators are used to register functions as macros belonging
    to that module.
    """

    class Registry(object):
        def __init__(self, wrap = lambda x: x):
            self.registry = {}
            self.wrap = wrap

        def __call__(self, f, name=None):

            if name is not None:
                self.registry[name] = self.wrap(f)
            if hasattr(f, "func_name"):
                self.registry[f.func_name] = self.wrap(f)
            if hasattr(f, "__name__"):
                self.registry[f.__name__] = self.wrap(f)

            return self.wrap(f)

    def __init__(self):
        # Different kinds of macros
        self.expr = Macros.Registry(macro_function)
        self.block = Macros.Registry(macro_function)
        self.decorator = Macros.Registry(macro_function)

        self.expose_unhygienic = Macros.Registry()


# For other modules to hook into MacroPy's workflow while
# keeping this module itself unaware of their presence.
injected_vars = []      # functions to inject values throughout each files macros
filters = []            # functions to call on every macro-expanded snippet
post_processing = []    # functions to call on every macro-expanded file

def expand_entire_ast(tree, src, bindings):

    def expand_macros(tree):
        """Go through an AST, hunting for macro invocations and expanding any that
        are found"""

        def expand_if_in_registry(macro_tree, body_tree, args, registry, **kwargs):
            """check if `tree` is a macro in `registry`, and if so use it to expand `args`"""
            if isinstance(macro_tree, Name) and macro_tree.id in registry:

                (the_macro, the_module) = registry[macro_tree.id]
                try:
                    new_tree = the_macro(
                        tree=body_tree,
                        args=args,
                        src=src,
                        expand_macros=expand_macros,
                        **dict(kwargs.items() + file_vars.items())
                    )
                except Exception as e:
                    new_tree = e

                for filter in reversed(filters):
                    new_tree = filter(
                        tree=new_tree,
                        args=args,
                        src=src,
                        expand_macros=expand_macros,
                        lineno=macro_tree.lineno,
                        col_offset=macro_tree.col_offset,
                        **dict(kwargs.items() + file_vars.items())
                    )

                return new_tree
            elif isinstance(macro_tree, Call):
                args.extend(macro_tree.args)
                return expand_if_in_registry(macro_tree.func, body_tree, args, registry)

        def preserve_line_numbers(func):
            """Decorates a tree-transformer function to stick the original line
            numbers onto the transformed tree"""
            def run(tree):
                pos = (tree.lineno, tree.col_offset) if hasattr(tree, "lineno") and hasattr(tree, "col_offset") else None
                new_tree = func(tree)

                if pos:
                    t = new_tree
                    while type(t) is list:
                        t = t[0]

                    (t.lineno, t.col_offset) = pos
                return new_tree
            return run

        @preserve_line_numbers
        def macro_expand(tree):
            """Tail Recursively expands all macros in a single AST node"""
            if isinstance(tree, With):
                assert isinstance(tree.body, list), real_repr(tree.body)
                new_tree = expand_if_in_registry(tree.context_expr, tree.body, [], block_registry, target=tree.optional_vars)


                if new_tree:
                    if isinstance(new_tree, expr):
                        new_tree = [Expr(new_tree)]
                    if isinstance(new_tree, Exception): raise new_tree
                    assert isinstance(new_tree, list), type(new_tree)
                    return macro_expand(new_tree)

            if isinstance(tree, Subscript) and type(tree.slice) is Index:

                new_tree = expand_if_in_registry(tree.value, tree.slice.value, [], expr_registry)

                if new_tree:
                    assert isinstance(new_tree, expr), type(new_tree)
                    return macro_expand(new_tree)

            if isinstance(tree, ClassDef) or isinstance(tree, FunctionDef):
                seen_decs = []
                additions = []
                while tree.decorator_list != []:
                    dec = tree.decorator_list[0]
                    tree.decorator_list = tree.decorator_list[1:]

                    new_tree = expand_if_in_registry(dec, tree, [], decorator_registry)

                    if new_tree is None:
                        seen_decs.append(dec)
                    else:
                        tree = new_tree
                        tree = macro_expand(tree)
                        if type(tree) is list:
                            additions = tree[1:]
                            tree = tree[0]
                        elif isinstance(tree, expr):
                            tree = [Expr(tree)]
                            break
                if type(tree) is ClassDef or type(tree) is FunctionDef:
                    tree.decorator_list = seen_decs
                if len(additions) == 0:
                    return tree
                else:
                    return [tree] + additions

            return tree

        @Walker
        def macro_searcher(tree, **kw):
            x = macro_expand(tree)
            return x

        tree = macro_searcher.recurse(tree)

        return tree


    file_vars = {}


    for v in injected_vars:
        file_vars[v.func_name] = v(tree=tree, src=src, expand_macros=expand_macros, **file_vars)


    allnames = [
        (m, name, asname)
        for m, names in bindings
        for name, asname in names
    ]

    def extract_macros(pick_registry):
        return {
            asname: (registry[name], ma)
            for ma, name, asname in allnames
            for registry in [pick_registry(ma.macros).registry]
            if name in registry.keys()
        }

    block_registry = extract_macros(lambda x: x.block)
    expr_registry = extract_macros(lambda x: x.expr)
    decorator_registry = extract_macros(lambda x: x.decorator)

    tree = expand_macros(tree)

    for post in post_processing:
        tree = post(
            tree=tree,
            src=src,
            expand_macros=expand_macros,
            **file_vars
        )

    return tree


def detect_macros(tree):
    """Look for macros imports within an AST, transforming them and extracting
    the list of macro modules."""
    bindings = []

    for stmt in tree.body:
        if isinstance(stmt, ImportFrom) \
                and stmt.names[0].name == 'macros' \
                and stmt.names[0].asname is None:
            __import__(stmt.module)
            mod = sys.modules[stmt.module]

            bindings.append((
                stmt.module,
                [(t.name, t.asname or t.name) for t in stmt.names[1:]]
            ))

            stmt.names = [
                name for name in stmt.names
                if name.name not in mod.macros.block.registry
                if name.name not in mod.macros.expr.registry
                if name.name not in mod.macros.decorator.registry
            ]

            stmt.names.extend([
                alias(x, x) for x in
                mod.macros.expose_unhygienic.registry.keys()
            ])

    return bindings

def check_annotated(tree):
    """Shorthand for checking if an AST is of the form something[...]"""
    if isinstance(tree, Subscript) and \
                    type(tree.slice) is Index and \
                    type(tree.value) is Name:
        return tree.value.id, tree.slice.value


########NEW FILE########
__FILENAME__ = quotes
"""Implementation of the Quasiquotes macro.

`u`, `name`, `ast` and `ast_list` are the unquote delimiters, used to
interpolate things into a quoted section.
"""
from macropy.core.macros import *


macros = Macros()




@Walker
def unquote_search(tree, **kw):

    res = check_annotated(tree)
    if res:
        func, right = res
        for f in [u, name, ast, ast_list]:
            if f.__name__ == func:
                return f(right)



@macros.expr
def q(tree, **kw):
    tree = unquote_search.recurse(tree)
    tree = ast_repr(tree)
    return tree


@macros.block
def q(tree, target, **kw):
    """Quasiquote macro, used to lift sections of code into their AST
    representation which can be manipulated at runtime. Used together with
    the `u`, `name`, `ast`, `ast_list` unquotes."""
    body = unquote_search.recurse(tree)
    new_body = ast_repr(body)
    return [Assign([target], new_body)]


@macro_stub
def u(tree):
    """Splices a value into the quoted code snippet, converting it into an AST
    via ast_repr"""
    return Literal(Call(Name(id="ast_repr"), [tree], [], None, None))


@macro_stub
def name(tree):
    "Splices a string value into the quoted code snippet as a Name"
    return Literal(Call(Name(id="Name"), [], [keyword("id", tree)], None, None))


@macro_stub
def ast(tree):
    "Splices an AST into the quoted code snippet"
    return Literal(tree)


@macro_stub
def ast_list(tree):
    """Splices a list of ASTs into the quoted code snippet as a List node"""
    return Literal(Call(Name(id="List"), [], [keyword("elts", tree)], None, None))


########NEW FILE########
__FILENAME__ = analysis
import unittest
from walkers import Walker
from macropy.core.analysis import Scoped
from macropy.core import *
import ast

@Scoped
@Walker
def scoped(tree, scope, collect, **kw):
    try:
        if scope != {}:
            collect((unparse(tree), {k: type(v) for k, v in scope.items()}))
    except:
        pass

class Tests(unittest.TestCase):
    def test_simple_expr(self):
        tree = parse_expr("(lambda x: a)")

        assert scoped.collect(tree) == [('a', {'x': ast.Name})]

        tree = parse_expr("(lambda x, y: (lambda z: a))")

        assert scoped.collect(tree) == [
            ('(lambda z: a)', {'y': ast.Name, 'x': ast.Name}),
            ('z', {'y': ast.Name, 'x': ast.Name}),
            ('z', {'y': ast.Name, 'x': ast.Name}),
            ('a', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name})
        ]

        tree = parse_expr("[e for (a, b) in c for d in e if f]")

        assert scoped.collect(tree) == [
            ('e', {'a': ast.Name, 'b': ast.Name, 'd': ast.Name}),
            ('d', {'a': ast.Name, 'b': ast.Name}),
            ('e', {'a': ast.Name, 'b': ast.Name}),
            ('f', {'a': ast.Name, 'b': ast.Name, 'd': ast.Name})
        ]


        tree = parse_expr("{k: v for k, v in d}")

        assert scoped.collect(tree) == [
            ('k', {'k': ast.Name, 'v': ast.Name}),
            ('v', {'k': ast.Name, 'v': ast.Name})
        ]

    def test_simple_stmt(self):
        tree = parse_stmt("""
def func(x, y):
    return x
        """)

        assert scoped.collect(tree) == [
            ('\n\ndef func(x, y):\n    return x', {'func': ast.FunctionDef}),
            ('x, y', {'func': ast.FunctionDef}),
            ('x', {'func': ast.FunctionDef}),
            ('y', {'func': ast.FunctionDef}),
            ('\nreturn x', {'y': ast.Name, 'x': ast.Name, 'func': ast.FunctionDef}),
            ('x', {'y': ast.Name, 'x': ast.Name, 'func': ast.FunctionDef})
        ]

        tree = parse_stmt("""
def func(x, y):
    z = 10
    return x
        """)

        assert scoped.collect(tree) == [
            ('\n\ndef func(x, y):\n    z = 10\n    return x', {'func': ast.FunctionDef}),
            ('x, y', {'func': ast.FunctionDef}),
            ('x', {'func': ast.FunctionDef}),
            ('y', {'func': ast.FunctionDef}),
            ('\nz = 10', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name, 'func': ast.FunctionDef}),
            ('z', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name, 'func': ast.FunctionDef}),
            ('10', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name, 'func': ast.FunctionDef}),
            ('\nreturn x', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name, 'func': ast.FunctionDef}),
            ('x', {'y': ast.Name, 'x': ast.Name, 'z': ast.Name, 'func': ast.FunctionDef})
        ]

        tree = parse_stmt("""
class C(A, B):
    z = 10
    print z
        """)


        assert scoped.collect(tree) == [
            ('\n\nclass C(A, B):\n    z = 10\n    print z', {'C': ast.ClassDef}),
            ('\nz = 10', {'z': ast.Name}),
            ('z', {'z': ast.Name}),
            ('10', {'z': ast.Name}),
            ('\nprint z', {'z': ast.Name}),
            ('z', {'z': ast.Name})
        ]

        tree = parse_stmt("""
def func(x, y):
    def do_nothing(): pass
    class C(): pass
    print 10
        """)


        assert scoped.collect(tree) == [
            ('\n\ndef func(x, y):\n\n    def do_nothing():\n        pass\n\n    class C:\n        pass\n    print 10', {'func': ast.FunctionDef}),
            ('x, y', {'func': ast.FunctionDef}),
            ('x', {'func': ast.FunctionDef}),
            ('y', {'func': ast.FunctionDef}),
            ('\n\ndef do_nothing():\n    pass', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('\npass', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('\n\nclass C:\n    pass', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('\npass', {'y': ast.Name, 'x': ast.Name, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('\nprint 10', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef}),
            ('10', {'y': ast.Name, 'x': ast.Name, 'C': ast.ClassDef, 'do_nothing': ast.FunctionDef, 'func': ast.FunctionDef})
        ]

        tree = parse_stmt("""
try:
    pass
except Exception as e:
    pass
        """)

        assert scoped.collect(tree) == [
            ('\npass', {'e': ast.Name})
        ]

        # This one still doesn't work right
        tree = parse_stmt("""
C = 1
class C:
    C
C
        """)

########NEW FILE########
__FILENAME__ = exact_src
from macropy.core.test.exact_src_macro import macros, f


def run0():
    return f[1 * max(1, 2, 3)]

def run1():
    return f[1 * max((1,'2',"3"))]

def run_block():
    with f as x:
        print "omg"
        print "wtf"
        if 1:
            print 'omg'
        else:
            import math
            math.acos(0.123)

    return x

########NEW FILE########
__FILENAME__ = exact_src_macro
from macropy.core.macros import *
from macropy.core.quotes import macros, q
macros = Macros()

@macros.expr
def f(tree, exact_src, **kw):
    return Str(s=exact_src(tree))

@macros.block
def f(tree, exact_src, target, **kw):
    with q as s:
        x = y
    s[0].value = Str(s=exact_src(tree))
    return s
########NEW FILE########
__FILENAME__ = pyc_cache
from macropy.core.test.exporters.pyc_cache_macro import macros, f
from macropy.core.test import exporters

exporters.pyc_cache_count += 1
f[1]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
########NEW FILE########
__FILENAME__ = pyc_cache_macro
from macropy.core.macros import *
from macropy.core.test import exporters
macros = Macros()

@macros.expr
def f(tree, **kw):

    exporters.pyc_cache_macro_count += 1
    return Num(n = 10)

########NEW FILE########
__FILENAME__ = save
from macropy.core.test.exporters.save_macro import macros, f


def run():
    return f[1 + 1]
      
########NEW FILE########
__FILENAME__ = save_macro
from macropy.core.macros import *
from macropy.core.test import exporters
from macropy.core.hquotes import macros, hq
macros = Macros()

def double(x):
    return x * x
@macros.expr
def f(tree, **kw):
    n = 10
    return hq[double(ast[tree]) + n]

########NEW FILE########
__FILENAME__ = failure
from macropy.core.test.failure_macro import macros, f, g, h, i

def run1():

    return f[0]

def run2():
    return g[0]

def run3():
    with h:
        pass

def run4():
    @i
    def x():
        pass
########NEW FILE########
__FILENAME__ = failure_macro
from macropy.core.failure import MacroExpansionError
from macropy.core.macros import *

macros = Macros()

@macros.expr
def f(tree, gen_sym, **kw):
    raise Exception("i am a cow")

@macros.expr
def g(tree, gen_sym, **kw):
    assert False, "i am a cow"

@macros.block
def h(tree, gen_sym, **kw):
    raise Exception("i am a cow")

@macros.decorator
def i(tree, gen_sym, **kw):
    raise Exception("i am a cow")
########NEW FILE########
__FILENAME__ = gen_sym
from macropy.core.test.gen_sym_macro import macros, f
sym1 = 10
def run():
    arg1 = 3
    sym3 = 10
    sym4 = 1
    f = 10
    return f[1 * max(1, 2, 3)]


########NEW FILE########
__FILENAME__ = gen_sym_macro
from macropy.core.macros import *

macros = Macros()

@macros.expr
def f(tree, gen_sym, **kw):
    symbols = [gen_sym(), gen_sym(), gen_sym(), gen_sym(), gen_sym()]
    assert symbols == ["sym2", "sym5", "sym6", "sym7", "sym8"], symbols
    renamed = [gen_sym("max"), gen_sym("max"), gen_sym("run"), gen_sym("run")]
    assert renamed == ["max1", "max2", "run1", "run2"], renamed
    unchanged = [gen_sym("grar"), gen_sym("grar"), gen_sym("omg"), gen_sym("omg")]
    assert unchanged == ["grar", "grar1", "omg", "omg1"], unchanged
    return Num(n = 10)

########NEW FILE########
__FILENAME__ = hq
from macropy.core.test.hquotes.hq_macro import macros, expand, expand_unhygienic, unhygienic

double = "double"
value = 1
def run1():
    return expand[str(value) + " " + double + " "]

def run2():
    x = 1
    with expand:
        x = x + 1
    return x

def run3():
    x = 1
    with expand_unhygienic:
        x = x + 1
    return x

def run_error():
    unhygienic[10]

########NEW FILE########
__FILENAME__ = hq2
from macropy.core.test.hquotes.hq_macro2 import macros, expand_block, expand, expand_block_complex

double = "double"
value = 1

def run1():
    return expand[str(value) + " " + double + " "]

def run2():
    x = 1
    with expand_block:
        pass
    return x

def run3():
    x = 1
    with expand_block_complex:
        pass
    return x

########NEW FILE########
__FILENAME__ = hq_macro
from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, unhygienic

macros = Macros()

value = 2

def double(x):
    return x * value

@macros.expr
def expand(tree, gen_sym, **kw):
    tree = hq[str(value) + "x: " + double(ast[tree])]
    return tree

@macros.block
def expand(tree, gen_sym, **kw):
    v = 5
    with hq as new_tree:
        return v
    return new_tree

@macros.block
def expand_unhygienic(tree, gen_sym, **kw):

    v = 5
    with hq as new_tree:
        unhygienic[x] = unhygienic[x] + v

    return new_tree
########NEW FILE########
__FILENAME__ = hq_macro2
from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, unhygienic
from macropy.tracing import macros, show_expanded

macros = Macros()

value = 2

def double(x):
    return x * value

@macros.expr
def expand(tree, **kw):
    tree = hq[(lambda cow, prefix: prefix + "x: " + cow(ast[tree]))(double, str(value))]
    return tree


@macros.block
def expand_block(tree, **kw):
    v = 5
    with hq as new_tree:
        x = v
        y = x + v
        z = x + y + v
        return z
    return new_tree

@macros.block
def expand_block_complex(tree, **kw):
    v = 5
    with hq as new_tree:
        x = v
        def multiply(start, *args):
            func = lambda a, b: a * b
            accum = 1
            for a in [start] + list(args):
                accum = func(accum, a)
            return accum
        y = x + v
        z = x + y + v
        return multiply(z, 2, 3, 4)

    return new_tree
########NEW FILE########
__FILENAME__ = aliases
from macropy.core.test.macros.aliases_macro import macros, e, f as f_new


def run_normal():
    return e[1 * max(1, 2, 3)]

def run_aliased():
    return f_new[1 * max((1,'2',"3"))]

def run_ignored():
    return g[1123]

########NEW FILE########
__FILENAME__ = aliases_macro
from macropy.core.macros import *
from macropy.core.quotes import macros, q
macros = Macros()

@macros.expr
def e(tree, exact_src, **kw):
    return Str("omg")

@macros.expr
def f(tree, exact_src, **kw):
    return Str("wtf")

@macros.expr
def g(tree, exact_src, **kw):
    return Str("bbq")

########NEW FILE########
__FILENAME__ = argument
from macropy.core.test.macros.argument_macros import macros, expr_macro, block_macro, decorator_macro
import math

def run():
    x = expr_macro(1 + math.sqrt(5))[10 + 10 + 10]

    with block_macro(1 + math.sqrt(5)) as y:
        x = x + 1

    @decorator_macro(1 + math.sqrt(5))
    def f():
        pass

    return x
########NEW FILE########
__FILENAME__ = argument_macros
from macropy.core.macros import *

macros = Macros()

@macros.expr
def expr_macro(tree, args, **kw):

    assert map(unparse, args) == ["(1 + math.sqrt(5))"], unparse(args)
    return tree

@macros.block
def block_macro(tree, args, **kw):
    assert map(unparse, args) == ["(1 + math.sqrt(5))"], unparse(args)
    return tree

@macros.decorator
def decorator_macro(tree, args, **kw):
    assert map(unparse, args) == ["(1 + math.sqrt(5))"], unparse(args)
    return tree

########NEW FILE########
__FILENAME__ = basic_block
from macropy.core.test.macros.basic_block_macro import macros, my_macro

def run():
    x = 10
    with my_macro as y:
        x = x + 1
    return x
########NEW FILE########
__FILENAME__ = basic_block_macro
from macropy.core.macros import *

macros = Macros()

@macros.block
def my_macro(tree, target, **kw):
    assert unparse(target) == "y"
    assert unparse(tree).strip() == "x = (x + 1)", unparse(tree)
    return tree * 3

########NEW FILE########
__FILENAME__ = basic_decorator
from macropy.core.test.macros.basic_decorator_macro import macros, my_macro, my_macro2

def outer(x):
    return x
def middle(x):
    return x
def inner(x):
    return x

@outer
@my_macro2
@middle
@my_macro
@inner
def run():
    x = 10
    x = x + 1
    return x


########NEW FILE########
__FILENAME__ = basic_decorator_macro
from macropy.core.macros import *

macros = Macros()

@macros.decorator
def my_macro(tree, **kw):
    assert unparse(tree).strip() == "\n".join([
    "@inner",
    "def run():",
    "    x = 10",
    "    x = (x + 1)",
    "    return x"]), unparse(tree)

    b = tree.body
    tree.body = [b[0], b[1], b[1], b[1], b[1], b[2]]
    return tree

@macros.decorator
def my_macro2(tree, **kw):
    assert unparse(tree).strip() == "\n".join([
    "@middle",
    "@my_macro",
    "@inner",
    "def run():",
    "    x = 10",
    "    x = (x + 1)",
    "    return x"]), unparse(tree)

    return tree

########NEW FILE########
__FILENAME__ = basic_expr
from macropy.core.test.macros.basic_expr_macro import macros, f

def run():
    f = 10
    return f[1 * max(1, 2, 3)]
########NEW FILE########
__FILENAME__ = basic_expr_macro
from macropy.core.macros import *

macros = Macros()

@macros.expr
def f(tree, **kw):
    assert unparse(tree) == "(1 * max(1, 2, 3))", unparse(tree)
    return Num(n = 10)

########NEW FILE########
__FILENAME__ = line_number_error_source
from macropy.core.test.macros.line_number_macro import macros, expand

def run(x):
    y = 0
    with expand:
        x = x - 1
        y = 1 / x

    return x

########NEW FILE########
__FILENAME__ = line_number_macro
from macropy.core.macros import *

macros = Macros()

@macros.block
def expand(tree, **kw):
    import copy
    return tree * 10

########NEW FILE########
__FILENAME__ = line_number_source
from macropy.core.test.macros.line_number_macro import macros, expand

def run(x, throw):
    with expand:
        x = x + 1

    if throw:
        raise Exception("lol")

    return x

########NEW FILE########
__FILENAME__ = not_imported
from macropy.core.test.macros.not_imported_macro import macros, g
from macropy.core.test.macros.not_imported_macro import f

def run1():
    f = [1, 2, 3, 4, 5]
    g = 1
    return f[g[3]]

def run2():
    return f[g[3]]
########NEW FILE########
__FILENAME__ = not_imported_macro
from macropy.core.macros import *

macros = Macros()

@macros.expr
def g(tree, **kw):
    return Num(n = 0)

@macros.expr
def f(tree, **kw):
    return Num(n = 0)
########NEW FILE########
__FILENAME__ = quote_macro
from macropy.core.macros import *
from macropy.core.quotes import macros, q
macros = Macros()

@macros.block
def my_macro(tree, **kw):
    with q as code:
        x = x / 2
        y = 1 / x
        x = x / 2
        y = 1 / x
        x = x / 2
        y = 1 / x
    return code

########NEW FILE########
__FILENAME__ = quote_source
from macropy.core.test.macros.quote_macro import macros, my_macro

def run(x):
    pass
    pass
    with my_macro:
        pass
    pass
    return x

########NEW FILE########
__FILENAME__ = quotes
import unittest

from macropy.core.macros import *
from macropy.core.quotes import macros, q, u

class Tests(unittest.TestCase):

    def test_simple(self):

        a = 10
        b = 2
        data1 = q[1 + u[a + b]]
        data2 = q[1 + (a + b)]

        assert eval(unparse(data1)) == 13
        assert eval(unparse(data2)) == 13
        a = 1
        assert eval(unparse(data1)) == 13
        assert eval(unparse(data2)) == 4


    def test_structured(self):

        a = [1, 2, "omg"]
        b = ["wtf", "bbq"]
        data1 = q[[x for x in u[a + b]]]

        assert(eval(unparse(data1)) == [1, 2, "omg", "wtf", "bbq"])
        b = []
        assert(eval(unparse(data1)) == [1, 2, "omg", "wtf", "bbq"])


    def test_quote_unquote(self):

        x = 1
        y = 2
        a = q[u[x + y]]
        assert(eval(unparse(a)) == 3)
        x = 0
        y = 0
        assert(eval(unparse(a)) == 3)


    def test_unquote_name(self):
        n = "x"
        x = 1
        y = q[name[n] + name[n]]

        assert(eval(unparse(y)) == 2)

    def test_quote_unquote_ast(self):

        a = q[x + y]
        b = q[ast[a] + z]

        x, y, z = 1, 2, 3
        assert(eval(unparse(b)) == 6)
        x, y, z = 1, 3, 9
        assert(eval(unparse(b)) == 13)


    def test_quote_unquote_block(self):

        a = 10
        b = ["a", "b", "c"]
        c = []
        with q as code:
            c.append(a)
            c.append(u[a])
            c.extend(u[b])

        exec(unparse(code))
        assert(c == [10, 10, 'a', 'b', 'c'])
        c = []
        a, b = None, None
        exec(unparse(code))
        assert(c == [None, 10, 'a', 'b', 'c'])

    def test_bad_unquote_error(self):
        with self.assertRaises(TypeError) as ce:
            x = u[10]

        assert ce.exception.message == (
            "Stub `u` illegally invoked at runtime; "
            "is it used properly within a macro?"
        )
########NEW FILE########
__FILENAME__ = unparse
import unittest

from macropy.core.macros import *

def convert(code):
    " string -> ast -> string "
    return unparse(parse_stmt(code))

class Tests(unittest.TestCase):

    def convert_test(self, code):
        # check if unparsing the ast of code yields the same source
        self.assertEqual(code.rstrip(), convert(code))

    def test_expr(self):
        self.assertEqual(convert("1 +2 / a"), "\n(1 + (2 / a))")

    def test_stmts(self):
        self.convert_test("""
import foo
from foo import bar
foo = something
bar += 4
return
pass
break
continue
del a, b, c
assert foo, bar
print 'hello', 'world'
del foo
global foo, bar, baz
(yield foo)""")

    def test_Exec(self):
        self.convert_test("""
exec 'foo'
exec 'foo' in bar
exec 'foo' in bar, {}""")

    def test_Raise(self):
        self.convert_test("""
raise
raise Exception(e)
raise Exception, init_arg
raise Exception, init_arg, traceback""")

    def test_Try(self):
        self.convert_test("""
try:
    foo
except:
    pass
try:
    foo
except Exeption as name:
    bar
except Exception:
    123
except:
    pass
else:
    baz
finally:
    foo.close()
try:
    foo
finally:
    foo.close()""")

    def test_ClassDef(self):
        self.convert_test("""

@decorator
@decorator2
class Foo(bar, baz):
    pass

class Bar:
    pass""")

    def test_FunctionDef(self):
        # also tests the arguments object
        self.convert_test("""

@decorator
@decorator2
def foo():
    bar

def foo(arg, arg2, kw=5, *args, **kwargs):
    pass""")

    def test_For(self):
        self.convert_test("""
for a in b:
    pass
else:
    bar
for a in b:
    pass""")

    def test_If(self):
        self.convert_test("""
if foo:
    if foo:
        pass
    else:
        pass
if foo:
    pass
elif c:
    if foo:
        pass
    elif a:
        pass
    elif b:
        pass
    else:
        pass
""")

    def test_While(self):
        self.convert_test("""
while a:
    pass
else:
    pass
while a:
    pass""")

    def test_With(self):
        self.convert_test("""
with a as b:
    c""")

    def test_datatypes(self):
        self.convert_test("""
[1, 5.0, [(-6)]]
{1, 2, 3, 4}
{1:2, 5:8}
(1, 2, 3)
""")
        self.convert_test("\n'abcd'")

    def test_comprehension(self):
        self.convert_test("""
(5 if foo else bar)
(x for x in abc)
(x for x in abc if foo)
[x for x in abc if foo]
{x for x in abc if foo}
{x: y for x in abc if foo}
""")

    def test_unaryop(self):
        self.convert_test("""
(not foo)
(~ 9)
(+ 1)
""")

    def test_bnops(self):
        self.convert_test("\n(1 >> (2 | 3))")
        self.convert_test("\n(a >= b)")

    def test_misc(self):
        self.convert_test("\na.attr") # Attribute
        self.convert_test("""
f()
f(a, k=8, e=9, *b, **c)""") # Call
        #self.convert_test("\n...") # Ellipsis
        self.convert_test("""
a[1]
a[1:2]
a[2:3:4]
a[(1,)]""") # subscript, Index, Slice, extslice
        self.convert_test("""
(lambda k, f, a=6, *c, **kw: 7)
(lambda: 7)
""")
########NEW FILE########
__FILENAME__ = walkers
import unittest

from macropy.core.macros import *
from macropy.core.quotes import macros, q, u

class Tests(unittest.TestCase):
    def test_transform(self):
        tree = parse_expr('(1 + 2) * "3" + ("4" + "5") * 6')
        goal = parse_expr('((("1" * "2") + 3) * ((4 * 5) + "6"))')

        @Walker
        def transform(tree, **kw):
            if type(tree) is Num:
                return Str(s = str(tree.n))
            if type(tree) is Str:
                return Num(n = int(tree.s))
            if type(tree) is BinOp and type(tree.op) is Mult:
                return BinOp(tree.left, Add(), tree.right)
            if type(tree) is BinOp and type(tree.op) is Add:
                return BinOp(tree.left, Mult(), tree.right)

        assert unparse(transform.recurse(tree)) == unparse(goal)

    def test_collect(self):

        tree = parse_expr('(((1 + 2) + (3 + 4)) + ((5 + 6) + (7 + 8)))')
        total = [0]
        @Walker
        def sum(tree, collect, **kw):
            if type(tree) is Num:
                total[0] = total[0] + tree.n
                return collect(tree.n)

        tree, collected = sum.recurse_collect(tree)
        assert total[0] == 36
        assert collected == [1, 2, 3, 4, 5, 6, 7, 8]

        collected = sum.collect(tree)
        assert collected == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_ctx(self):
        tree = parse_expr('(1 + (2 + (3 + (4 + (5)))))')

        @Walker
        def deepen(tree, ctx, set_ctx, **kw):
            if type(tree) is Num:
                tree.n = tree.n + ctx
            else:
                return set_ctx(ctx=ctx + 1)

        new_tree = deepen.recurse(tree, ctx=0)
        goal = parse_expr('(2 + (4 + (6 + (8 + 9))))')
        assert unparse(new_tree) == unparse(goal)

    def test_stop(self):
        tree = parse_expr('(1 + 2 * 3 + 4 * (5 + 6) + 7)')
        goal = parse_expr('(0 + 2 * 3 + 4 * (5 + 6) + 0)')

        @Walker
        def stopper(tree, stop, **kw):
            if type(tree) is Num:
                tree.n = 0
            if type(tree) is BinOp and type(tree.op) is Mult:
                stop()

        new_tree = stopper.recurse(tree)
        assert unparse(goal) == unparse(new_tree)

########NEW FILE########
__FILENAME__ = util
"""Functions that are nice to have but really should be in the python std lib"""

def flatten(xs):
    """Recursively flattens a list of lists of lists (arbitrarily, non-uniformly
    deep) into a single big list."""
    res = []
    def loop(ys):
        for i in ys:
            if isinstance(i, list): loop(i)
            elif i is None: pass
            else: res.append(i)
    loop(xs)
    return res



def singleton(cls):
    """Decorates a class to turn it into a singleton."""
    obj = cls()
    obj.__name__ = cls.__name__

    return obj


def merge_dicts(*my_dicts):
    """Combines a bunch of dictionaries together, later dictionaries taking
    precedence if there is a key conflict"""
    return dict((k,v) for d in my_dicts for (k,v) in d.items())

class Lazy:
    def __init__(self, thunk):
        self.thunk = thunk
        self.val = None
    def __call__(self):
        if self.val is None:
            self.val = [self.thunk()]
        return self.val[0]

def distinct(l):
    """Builds a new list with all duplicates removed"""
    s = []
    for i in l:
       if i not in s:
          s.append(i)
    return s

def register(array):
    """A decorator to add things to lists without stomping over its value"""
    def x(val):
        array.append(val)
        return val
    return x

def box(x):
    "None | T => [T]"
    return [x] if x else []

########NEW FILE########
__FILENAME__ = walkers
"""Implementation of Walkers, a nice way of transforming and traversing ASTs."""

from macropy.core import *
from ast import *


class Walker(object):
    """
    @Walker decorates a function of the form:

    @Walker
    def transform(tree, **kw):
        ...
        return new_tree


    Which is used via:

    new_tree = transform.recurse(old_tree, initial_ctx)
    new_tree = transform.recurse(old_tree)
    new_tree, collected = transform.recurse_collect(old_tree, initial_ctx)
    new_tree, collected = transform.recurse_collect(old_tree)
    collected = transform.collect(old_tree, initial_ctx)
    collected = transform.collect(old_tree)

    The `transform` function takes the tree to be transformed, in addition to
    a set of `**kw` which provides additional functionality:


    - `set_ctx`: this is a function, used via `set_ctx(name=value)` anywhere in
      `transform`, which will cause any children of `tree` to receive `name` as
      an argument with a value `value.
    - `set_ctx_for`: this is similar to `set_ctx`, but takes an additional
      parameter `tree` (i.e. `set_ctx_for(tree, name=value)`) and `name` is
      only injected into the parameter list of `transform` when `tree` is the
      AST snippet being transformed.
    - `collect`: this is a function used via `collect(thing)`, which adds
      `thing` to the `collected` list returned by `recurse_collect`.
    - `stop`: when called via `stop()`, this prevents recursion on children
      of the current tree.

    These additional arguments can be declared in the signature, e.g.:

    @Walker
    def transform(tree, ctx, set_ctx, **kw):
        ... do stuff with ctx ...
        set_ctx(...)
        return new_tree

    for ease of use.
    """
    def __init__(self, func):
        self.func = func

    def walk_children(self, tree, sub_kw=[], **kw):
        if isinstance(tree, AST):
            aggregates = []

            for field, old_value in iter_fields(tree):

                old_value = getattr(tree, field, None)
                specific_sub_kw = [
                    (k, v)
                    for item, kws in sub_kw
                    if item is old_value
                    for k, v in kws.items()
                ]
                new_value, new_aggregate = self.recurse_collect(old_value, sub_kw, **dict(kw.items() + specific_sub_kw))
                aggregates.extend(new_aggregate)
                setattr(tree, field, new_value)

            return aggregates

        elif isinstance(tree, list) and len(tree) > 0:
            aggregates = []
            new_tree = []

            for t in tree:
                new_t, new_a = self.recurse_collect(t, sub_kw, **kw)
                if type(new_t) is list:
                    new_tree.extend(new_t)
                else:
                    new_tree.append(new_t)
                aggregates.extend(new_a)

            tree[:] = new_tree
            return aggregates

        else:
            return []

    def recurse(self, tree, **kw):
        """Traverse the given AST and return the transformed tree."""
        return self.recurse_collect(tree, **kw)[0]

    def collect(self, tree, **kw):
        """Traverse the given AST and return the transformed tree."""
        return self.recurse_collect(tree, **kw)[1]

    def recurse_collect(self, tree, sub_kw=[], **kw):
        """Traverse the given AST and return the transformed tree together
        with any values which were collected along with way."""

        if isinstance(tree, AST) or type(tree) is Literal or type(tree) is Captured:
            aggregates = []
            stop_now = [False]

            def stop():
                stop_now[0] = True


            new_ctx = dict(**kw)
            new_ctx_for = sub_kw[:]

            def set_ctx(**new_kw):
                new_ctx.update(new_kw)

            def set_ctx_for(tree, **kw):
                new_ctx_for.append((tree, kw))

            # Provide the function with a bunch of controls, in addition to
            # the tree itself.
            new_tree = self.func(
                tree=tree,
                collect=aggregates.append,
                set_ctx=set_ctx,
                set_ctx_for=set_ctx_for,
                stop=stop,
                **kw
            )

            if new_tree is not None:
                tree = new_tree

            if not stop_now[0]:
                aggregates.extend(self.walk_children(tree, new_ctx_for, **new_ctx))

        else:
            aggregates = self.walk_children(tree, sub_kw, **kw)

        return tree, aggregates



########NEW FILE########
__FILENAME__ = js_snippets
from macropy.core.macros import *
from macropy.core.quotes import macros, q, u, ast
import pjs
from pjs.converter import Scope

std_lib = [
    'modules.js',
    'functions.js',
    'classes.js',
    '__builtin__.js',
]

import os
path = os.path.dirname(pjs.__file__) + "/data/pjslib.js"
std_lib_script = open(path).read()

macros = Macros()


@macros.expr
def js(tree, **kw):
    javascript = pjs.converter.Converter("").convert_node(tree, Scope())
    return Str(javascript)


@macros.expr
def pyjs(tree, **kw):
    javascript = pjs.converter.Converter("").convert_node(tree, Scope())
    return q[(ast[tree], u[javascript])]

########NEW FILE########
__FILENAME__ = pattern
import inspect

from abc import ABCMeta, abstractmethod
from ast import *

from macropy.core import util
from macropy.core.macros import *

from macropy.core.quotes import macros, q
from macropy.core.hquotes import macros, hq
macros = Macros()


class PatternMatchException(Exception):
    """Thrown when a nonrefutable pattern match fails"""
    pass


class PatternVarConflict(Exception):
    """Thrown when a pattern attempts to match a variable more than once."""
    pass


def _vars_are_disjoint(var_names):
    return len(var_names)== len(set(var_names))


class Matcher(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def var_names(self):
        """
        Returns a container of the variable names which may be modified upon a
        successful match.
        """
        pass

    @abstractmethod
    def match(self, matchee):
        """
        Returns ([(varname, value)...]) if there is a match.  Otherwise,
        raise PatternMatchException().  This should be stateless.
        """
        pass

    def _match_value(self, matchee):
        """
        Match against matchee and produce an internal dictionary of the values
        for each variable.
        """
        self.var_dict = {}
        for (varname, value) in self.match(matchee):
            self.var_dict[varname] = value

    def get_var(self, var_name):
        return self.var_dict[var_name]


class LiteralMatcher(Matcher):

    def __init__(self, val):
        self.val = val

    def var_names(self):
        return []

    def match(self, matchee):
        if self.val != matchee:
            raise PatternMatchException("Literal match failed")
        return []


class TupleMatcher(Matcher):

    def __init__(self, *matchers):
        self.matchers = matchers
        if not _vars_are_disjoint(util.flatten([m.var_names() for m in
            matchers])):
            raise PatternVarConflict()

    def var_names(self):
        return util.flatten([matcher.var_names() for matcher in self.matchers])

    def match(self, matchee):
        updates = []
        if (not isinstance(matchee, tuple) or 
                len(matchee) != len(self.matchers)):
            raise PatternMatchException("Expected tuple of %d elements" %
                    (len(self.matchers),))
        for (matcher, sub_matchee) in zip(self.matchers, matchee):
            match = matcher.match(sub_matchee)
            updates.extend(match)
        return updates


class ParallelMatcher(Matcher):

    def __init__(self, matcher1, matcher2):
        self.matcher1 = matcher1
        self.matcher2 = matcher2
        if not _vars_are_disjoint(util.flatten([matcher1.var_names(),
            matcher2.var_names()])):
            raise PatternVarConflict()

    def var_names(self):
        return util.flatten([self.matcher1.var_names(),
            self.matcher2.var_names()])

    def match(self, matchee):
        updates = []
        for matcher in [self.matcher1, self.matcher2]:
            match = matcher.match(matchee)
            updates.extend(match)
        return updates


class ListMatcher(Matcher):

    def __init__(self, *matchers):
        self.matchers = matchers
        if not _vars_are_disjoint(util.flatten([m.var_names() for m in
            matchers])):
            raise PatternVarConflict()

    def var_names(self):
        return util.flatten([matcher.var_names() for matcher in self.matchers])

    def match(self, matchee):
        updates = []
        if (not isinstance(matchee, list) or len(matchee) != len(self.matchers)):
            raise PatternMatchException("Expected list of length %d" %
                    (len(self.matchers),))
        for (matcher, sub_matchee) in zip(self.matchers, matchee):
            match = matcher.match(sub_matchee)
            updates.extend(match)
        return updates


class NameMatcher(Matcher):

    def __init__(self, name):
        self.name = name

    def var_names(self):
        return [self.name]

    def match(self, matchee):
        return [(self.name, matchee)]


class WildcardMatcher(Matcher):
    
    def __init__(self):
        pass

    def var_names(self):
        return ['_']

    def match(self, matchee):
        return [('_', 3)]


class ClassMatcher(Matcher):

    def __init__(self, clazz, positionalMatchers, **kwMatchers):
        self.clazz = clazz
        self.positionalMatchers = positionalMatchers
        self.kwMatchers = kwMatchers

        # This stores which fields of the object we will need to look at.
        if not _vars_are_disjoint(util.flatten([m.var_names() for m in
            positionalMatchers + kwMatchers.values()])):
            raise PatternVarConflict()

    def var_names(self):
        return (util.flatten([matcher.var_names() 
            for matcher in self.positionalMatchers + self.kwMatchers.values()]))

    def default_unapply(self, matchee, kw_keys):
        if not isinstance(matchee, self.clazz):
            raise PatternMatchException("Matchee should be of type %r" %
                    (self.clazz,))
        pos_values = []
        kw_dict = {}

# We don't get the argspec unless there are actually positional matchers
        def genPosValues():
            arg_spec = inspect.getargspec(self.clazz.__init__)
            for arg in arg_spec.args:
                if arg != 'self':
                    yield(getattr(matchee, arg, None))
        pos_values = genPosValues()
        for kw_key in kw_keys:
            if not hasattr(matchee, kw_key):
                raise PatternMatchException("Keyword argument match failed: no"
                        + " attribute %r" % (kw_key,))
            kw_dict[kw_key] = getattr(matchee, kw_key)
        return pos_values, kw_dict

    def match(self, matchee):
        updates = []
        if hasattr(self.clazz, '__unapply__'):
            pos_vals, kw_dict = self.clazz.__unapply__(matchee,
                    self.kwMatchers.keys())
        else:
            pos_vals, kw_dict = self.default_unapply(matchee,
                    self.kwMatchers.keys())
        for (matcher, sub_matchee) in zip(self.positionalMatchers,
                pos_vals):
            updates.extend(matcher.match(sub_matchee))
        for key, val in kw_dict.items():
            updates.extend(self.kwMatchers[key].match(val))
        return updates


def build_matcher(tree, modified):
    if isinstance(tree, Num):
        return hq[LiteralMatcher(u[tree.n])]
    if isinstance(tree, Str):
        return hq[LiteralMatcher(u[tree.s])]
    if isinstance(tree, Name):
        if tree.id in ['True', 'False', 'None']:
            return hq[LiteralMatcher(ast[tree])]
        elif tree.id in ['_']:
            return hq[WildcardMatcher()]
        modified.add(tree.id)
        return hq[NameMatcher(u[tree.id])]
    if isinstance(tree, List):
        sub_matchers = []
        for child in tree.elts:
            sub_matchers.append(build_matcher(child, modified))
        return Call(Name('ListMatcher', Load()), sub_matchers, [], None, None)
    if isinstance(tree, Tuple):
        sub_matchers = []
        for child in tree.elts:
            sub_matchers.append(build_matcher(child, modified))
        return Call(Name('TupleMatcher', Load()), sub_matchers, [], None, None)
    if isinstance(tree, Call):
        sub_matchers = []
        for child in tree.args:
            sub_matchers.append(build_matcher(child, modified))
        positional_matchers = List(sub_matchers, Load())
        kw_matchers = []
        for kw in tree.keywords:
            kw_matchers.append(
                    keyword(kw.arg, build_matcher(kw.value, modified)))
        return Call(Name('ClassMatcher', Load()), [tree.func,
            positional_matchers], kw_matchers, None, None)
    if (isinstance(tree, BinOp) and isinstance(tree.op, BitAnd)):
        sub1 = build_matcher(tree.left, modified)
        sub2 = build_matcher(tree.right, modified)
        return Call(Name('ParallelMatcher', Load()), [sub1, sub2], [], None,
                None)

    raise Exception("Unrecognized tree " + repr(tree))


def _is_pattern_match_stmt(tree):
    return (isinstance(tree, Expr) and
            _is_pattern_match_expr(tree.value))


def _is_pattern_match_expr(tree):
    return (isinstance(tree, BinOp) and
            isinstance(tree.op, LShift))


@macros.block
def _matching(tree, gen_sym, **kw):
    """
    This macro will enable non-refutable pattern matching.  If a pattern match
    fails, an exception will be thrown.
    """
    @Walker
    def func(tree, **kw):
        if _is_pattern_match_stmt(tree):
            modified = set()
            matcher = build_matcher(tree.value.left, modified)
            temp = gen_sym()
            # lol random names for hax
            with hq as assignment:
                name[temp] = ast[matcher]

            statements = [assignment, Expr(hq[name[temp]._match_value(ast[tree.value.right])])]

            for var_name in modified:
                statements.append(Assign([Name(var_name, Store())], hq[name[temp].get_var(u[var_name])]))

            return statements
        else:
            return tree

    func.recurse(tree)
    return [tree]


def _rewrite_if(tree, var_name=None, **kw_args):
    # TODO refactor into a _rewrite_switch and a _rewrite_if
    """
    Rewrite if statements to treat pattern matches as boolean expressions.

    Recall that normally a pattern match is a statement which will throw a
    PatternMatchException if the match fails.  We can therefore use try-blocks
    to produce the desired branching behavior.

    var_name is an optional parameter used for rewriting switch statements.  If
    present, it will transform predicates which are expressions into pattern
    matches.
    """

    # with q as rewritten:
    #     try:
    #         with matching:
    #             u%(matchPattern)
    #         u%(successBody)
    #     except PatternMatchException:
    #         u%(_maybe_rewrite_if(failBody))
    # return rewritten
    if not isinstance(tree, If):
        return tree

    if var_name:
        tree.test = BinOp(tree.test, LShift(), Name(var_name, Load()))
    elif not (isinstance(tree.test, BinOp) and isinstance(tree.test.op, LShift)):
        return tree      

    handler = ExceptHandler(hq[PatternMatchException], None, tree.orelse)
    try_stmt = TryExcept(tree.body, [handler], [])

    macroed_match = With(Name('_matching', Load()), None, [Expr(tree.test)])
    try_stmt.body = [macroed_match] + try_stmt.body

    if len(handler.body) == 1: # (== tree.orelse)
        # Might be an elif
        handler.body = [_rewrite_if(handler.body[0], var_name)]
    elif not handler.body:
        handler.body = [Pass()]

    return try_stmt


@macros.block
def switch(tree, args, gen_sym, **kw):
    """
    If supplied one argument x, switch will treat the predicates of any
    top-level if statements as patten matches against x.

    Pattern matches elsewhere are ignored.  The advantage of this is the
    limited reach ensures less interference with existing code.
    """
    new_id = gen_sym()
    for i in xrange(len(tree)):
        tree[i] = _rewrite_if(tree[i], new_id)
    tree = [Assign([Name(new_id, Store())], args[0])] + tree
    return tree


@macros.block
def patterns(tree, **kw):
    """
    This enables patterns everywhere!  NB if you use this macro, you will not be
    able to use real left shifts anywhere.
    """
    with q as new:
        with _matching:
            None

    new[0].body = Walker(lambda tree, **kw: _rewrite_if(tree)).recurse(tree)

    return new

########NEW FILE########
__FILENAME__ = pinq
from ast import Call

from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, ast, name, ast_list
from macropy.quick_lambda import macros, f, _
import sqlalchemy

macros = Macros()

# workaround for inability to pickle modules



@macros.expr
def sql(tree, **kw):
    x = process(tree)
    x = expand_let_bindings.recurse(x)

    return x

@macros.expr
def query(tree, gen_sym, **kw):
    x = process(tree)
    x = expand_let_bindings.recurse(x)
    sym = gen_sym()
    # return q[(lambda query: query.bind.execute(query).fetchall())(ast[x])]
    new_tree = hq[(lambda query: name[sym].bind.execute(name[sym]).fetchall())(ast[x])]
    new_tree.func.args = arguments([Name(id=sym)], None, None, [])
    return new_tree


def process(tree):
    @Walker
    def recurse(tree, **kw):
        if type(tree) is Compare and type(tree.ops[0]) is In:
            return hq[(ast[tree.left]).in_(ast[tree.comparators[0]])]

        elif type(tree) is GeneratorExp:

            aliases = map(f[_.target], tree.generators)
            tables = map(f[_.iter], tree.generators)

            aliased_tables = map(lambda x: hq[(ast[x]).alias().c], tables)

            elt = tree.elt
            if type(elt) is Tuple:
                sel = hq[ast_list[elt.elts]]
            else:
                sel = hq[[ast[elt]]]

            out = hq[sqlalchemy.select(ast[sel])]

            for gen in tree.generators:
                for cond in gen.ifs:
                    out = hq[ast[out].where(ast[cond])]


            out = hq[(lambda x: ast[out])()]
            out.func.args.args = aliases
            out.args = aliased_tables
            return out
    return recurse.recurse(tree)

def generate_schema(engine):
    metadata = sqlalchemy.MetaData(engine)
    metadata.reflect()
    class Db: pass
    db = Db()
    for table in metadata.sorted_tables:
        setattr(db, table.name, table)
    return db


@Walker
def _find_let_bindings(tree, ctx, stop, collect, **kw):
    if type(tree) is Call and type(tree.func) is Lambda:
        stop()
        collect(tree)
        return tree.func.body

    elif type(tree) in [Lambda, GeneratorExp, ListComp, SetComp, DictComp]:
        stop()
        return tree

@Walker
def expand_let_bindings(tree, **kw):
    tree, chunks = _find_let_bindings.recurse_collect(tree)
    for v in chunks:
        let_tree = v
        let_tree.func.body = tree
        tree = let_tree
    return tree


########NEW FILE########
__FILENAME__ = pyxl_strings

from macropy.core.macros import *


import tokenize
from pyxl.codec.tokenizer import pyxl_tokenize



macros = Macros()


@macros.expr
def p(tree, **kw):
    import StringIO
    new_string = tokenize.untokenize(pyxl_tokenize(StringIO.StringIO('(' + tree.s + ')').readline)).rstrip().rstrip("\\")
    total_string = "from __future__ import unicode_literals;" + new_string
    new_tree = ast.parse(total_string)
    return new_tree.body[1].value

########NEW FILE########
__FILENAME__ = tco
from macropy.core.macros import *
from macropy.experimental.pattern import macros, switch, _matching, ClassMatcher, NameMatcher

from macropy.core.hquotes import macros, hq

__all__ = ['tco']

macros = Macros()

in_tc_stack = [False]

@singleton
class TcoIgnore:
    pass

@singleton
class TcoCall:
    pass


def trampoline(func, args, kwargs):
    """
    Repeatedly apply a function until it returns a value.

    The function may return (tco.CALL, func, args, kwargs) or (tco.IGNORE,
    func, args, kwargs) or just a value.
    """
    ignoring = False
    while True:
        # We can only set this if we know it will be immediately unset by func
        if hasattr(func, 'tco'):
            in_tc_stack[0] = True
        result = func(*args, **kwargs)
        # for performance reasons, do not use pattern matching here
        if isinstance(result, tuple):
            if result[0] is TcoCall:
                func = result[1]
                args = result[2]
                kwargs = result[3]
                continue
            elif result[0] is TcoIgnore:
                ignoring = True
                func = result[1]
                args = result[2]
                kwargs = result[3]
                continue
        if ignoring:
            return None
        else:
            return result



def trampoline_decorator(func):
    import functools
    @functools.wraps(func)
    def trampolined(*args, **kwargs):
        if in_tc_stack[0]:
            in_tc_stack[0] = False
            return func(*args, **kwargs)
        in_tc_stack.append(False)
        return trampoline(func, args, kwargs)

    trampolined.tco = True
    return trampolined


@macros.decorator
def tco(tree, **kw):

    @Walker
    # Replace returns of calls
    def return_replacer(tree, **kw):
        with switch(tree):
            if Return(value=Call(
                    func=func, 
                    args=args, 
                    starargs=starargs, 
                    kwargs=kwargs)):
                if starargs:
                    with hq as code:
                    # get rid of starargs
                        return (TcoCall,
                                ast[func],
                                ast[List(args, Load())] + list(ast[starargs]),
                                ast[kwargs or Dict([],[])])
                else:
                    with hq as code:
                        return (TcoCall,
                                ast[func],
                                ast[List(args, Load())],
                                ast[kwargs or Dict([], [])])

                return code
            else:
                return tree

    # Replace calls (that aren't returned) which happen to be in a tail-call
    # position
    def replace_tc_pos(node):
        with switch(node):
            if Expr(value=Call(
                    func=func,
                    args=args,
                    starargs=starargs,
                    kwargs=kwargs)):
                if starargs:
                    with hq as code:
                    # get rid of starargs
                        return (TcoIgnore,
                                ast[func],
                                ast[List(args, Load())] + list(ast[starargs]),
                                ast[kwargs or Dict([],[])])
                else:
                    with hq as code:
                        return (TcoIgnore,
                                ast[func],
                                ast[List(args, Load())],
                                ast[kwargs or Dict([], [])])
                return code
            elif If(test=test, body=body, orelse=orelse):
                body[-1] = replace_tc_pos(body[-1])
                if orelse:
                    orelse[-1] = replace_tc_pos(orelse[-1])
                return If(test, body, orelse)
            else:
                return node

    tree = return_replacer.recurse(tree)

    tree.decorator_list = ([hq[trampoline_decorator]] +
            tree.decorator_list)

    tree.body[-1] = replace_tc_pos(tree.body[-1])

    return tree

########NEW FILE########
__FILENAME__ = js_snippets
import unittest

from macropy.experimental.js_snippets import macros, pyjs, js, std_lib_script
from macropy.tracing import macros, require


from selenium import webdriver

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
    @classmethod
    def tearDownClass(cls):
        cls.driver.close()

    def exec_js(self, script):
        return Tests.driver.execute_script(
            std_lib_script + "return " + script
        )

    def exec_js_func(self, script, *args):
        arg_list = ", ".join("arguments[%s]" % i for i in range(len(args)))
        return Tests.driver.execute_script(
            std_lib_script + "return (" + script + ")(%s)" % arg_list,
            *args
        )
    def test_literals(self):
        # these work
        with require:
            self.exec_js(js[10]) == 10
            self.exec_js(js["i am a cow"]) == "i am a cow"

        # these literals are buggy, and it seems to be PJs' fault
        # ??? all the results seem to turn into strings ???
        with require:
            self.exec_js(js[3.14]) == str(3.14)
            self.exec_js(js[[1, 2, 'lol']]) == str([1, 2, 'lol'])
            self.exec_js(js[{"moo": 2, "cow": 1}]) == str({"moo": 2, "cow": 1})

        # set literals don't work so this throws an exception at macro-expansion time
        #self.exec_js(js%{1, 2, 'lol'})

    def test_executions(self):
        with require:
            self.exec_js(js[(lambda x: x * 2)(10)]) == 20
            self.exec_js(js[sum([x for x in range(10) if x > 5])]) == 30

    def test_pyjs(self):
        # cross-compiling a trivial predicate
        code, javascript = pyjs[lambda x: x > 5 and x % 2 == 0]

        for i in range(10):
            with require:
                code(i) == self.exec_js_func(javascript, i)


        code, javascript = pyjs[lambda n: [
            x for x in range(n)
            if 0 == len([
                y for y in range(2, x-2)
                if x % y == 0
            ])
        ]]
        # this is also wrongly stringifying the result =(
        with require:
            str(code(20)) == str(self.exec_js_func(javascript, 20))

########NEW FILE########
__FILENAME__ = pattern
import unittest

from macropy.experimental.pattern import macros, _matching, switch, patterns, LiteralMatcher, TupleMatcher, PatternMatchException, NameMatcher, ListMatcher, PatternVarConflict, ClassMatcher, WildcardMatcher
from ast import BinOp

class Foo(object):
    def __init__(self, x, y):
          self.x = x
          self.y = y


class Bar(object):
    def __init__(self, a):
          self.a = a


class Baz(object):
    def __init__(self, b):
        self.b = b


class Screwy(object):
    def __init__(self, a, b):
        self.x = a
        self.y = b


class Tests(unittest.TestCase):

    def test_literal_matcher(self):
        matcher = LiteralMatcher(5)
        self.assertEquals([], matcher.match(5))
        with self.assertRaises(PatternMatchException):
            self.assertFalse(matcher.match(4))

    def test_wildcard_matcher(self):
        _ = 2
        with patterns:
            _ << 5
        self.assertEquals(2, _)

    def test_tuple_matcher(self):
        matcher = TupleMatcher(
                LiteralMatcher(5),
                TupleMatcher(
                    LiteralMatcher(4),
                    LiteralMatcher(5)))
        with self.assertRaises(PatternMatchException):
            matcher.match((5, 5))
        self.assertEquals([], matcher.match((5, (4, 5))))

    def test_class_matcher(self):
        self.assertEquals([],
                ClassMatcher(Foo, [LiteralMatcher(5),
                    LiteralMatcher(6)]).match(Foo(5,6)))
        with self.assertRaises(PatternMatchException):
            ClassMatcher(Foo, [LiteralMatcher(5),
                LiteralMatcher(6)]).match(Foo(5,7))

        matcher1 = ClassMatcher(Foo, [NameMatcher('a'),
                NameMatcher('b')])
        matcher1._match_value(Foo(4, 5))
        a = matcher1.get_var('a')
        b = matcher1.get_var('b')

    def test_disjoint_vars_tuples(self):
        with self.assertRaises(PatternVarConflict):
            TupleMatcher(NameMatcher('x'), NameMatcher('x'))
        TupleMatcher(NameMatcher('y'), NameMatcher('x'))

    def test_disjoint_vars_lists(self):
        with self.assertRaises(PatternVarConflict):
            ListMatcher(NameMatcher('x'), NameMatcher('x'))
        ListMatcher(NameMatcher('y'), NameMatcher('x'))

    def test_basic_matching(self):
        with _matching:
            Foo(a, b) << Foo(3, 5)
            self.assertEquals(3, a)
            self.assertEquals(5, b)

    def test_compound_matching(self):
        with _matching:
            Foo(x, Foo(4, y)) << Foo(2, Foo(4, 7))
        self.assertEquals(2, x)
        self.assertEquals(7, y)
        with _matching:
            Foo("hey there", Foo(x, y)) << Foo("hey there", Foo(1, x))
        self.assertEquals(1, x)
        self.assertEquals(2, y)

    def test_match_exceptions(self):
        with self.assertRaises(PatternMatchException):
            with patterns:
                Foo(x, Foo(4, y)) << Foo(2, 7)
        with self.assertRaises(PatternMatchException):
            with patterns:
                Foo(x, Foo(4, y)) << Foo(2, Foo(5, 7))

    def test_disjoint_varnames_assertion(self):
        with self.assertRaises(PatternVarConflict):
            with _matching:
                Foo(x, x) << Foo(3, 4)
        with self.assertRaises(PatternVarConflict):
            with _matching:
                Foo(x, Foo(4, x)) << Foo(3, 4)

    def test_boolean_matching(self):
        with self.assertRaises(PatternMatchException):
            with _matching:
                Foo(True, x) << Foo(False, 5)
        self.assertTrue(True)
        self.assertFalse(False)

    def test_atomicity(self):
        x = 1
        y = 5
        with self.assertRaises(PatternMatchException):
            with _matching:
                (x, (3, y)) << (2, (4, 6))
        self.assertEquals(1, x)
        self.assertEquals(5, y)
        with _matching:
            (x, (3, y)) << (2, (3, 6))
        self.assertEquals(2, x)
        self.assertEquals(6, y)

    def test_switch(self):
        branch_reached = -1
        with switch(Bar(6)):
            if Bar(5):
                branch_reached = 1
            else:
                branch_reached = 2
        self.assertEquals(branch_reached, 2)

    def test_instance_checking(self):
        blah = Baz(5)
        branch_reached = -1
        reached_end = False
        with switch(blah):
            if Foo(lol, wat):
                branch_reached = 1
            elif Bar(4):
                branch_reached = 2
            elif Baz(x):
                branch_reached = 3
                self.assertEquals(5, x)
            self.assertEquals(8, 1 << 3)
            reached_end=True
        self.assertTrue(reached_end)
        self.assertEquals(3, branch_reached)

    def test_patterns_macro(self):
        blah = Baz(5)
        branch_reached = -1
        with patterns:
            if Foo(lol, wat) << blah:
                branch_reached = 1
            elif Bar(4) << blah:
                branch_reached = 2
            elif Baz(x) << blah:
                self.assertEquals(5, x)
                branch_reached = 3
        self.assertEquals(3, branch_reached)

    def test_keyword_matching(self):
        foo = Foo(21, 23)
        with patterns:
            Foo(x=x) << foo
        self.assertEquals(21, x)

    def test_no_rewrite_normal_ifs(self):
        branch_reached = -1
        with patterns:
            if False:
                branch_reached = 1
        self.assertEquals(-1, branch_reached)

    def test_ast_pattern_matching(self):
        binop_ast = BinOp(3, 4, 5)
        with patterns:
            BinOp(left=x, op=op, right=y) << binop_ast
        self.assertEquals(3, x)
        self.assertEquals(4, op)
        self.assertEquals(5, y)

########NEW FILE########
__FILENAME__ = pinq
import unittest

from sqlalchemy import create_engine, func
from macropy.experimental.pinq import macros, sql, query, generate_schema
import os


engine = create_engine("sqlite://")

for line in open(__file__ + "/../world.sql").read().split(";"):
    engine.execute(line.strip())
db = generate_schema(engine)

def compare_queries(query1, query2, post_process=lambda x: x):
    res1 = engine.execute(query1).fetchall()
    res2 = engine.execute(query2).fetchall()
    try:
        assert post_process(res1) == post_process(res2)
    except Exception, e:
        print ("FAILURE")
        print (e)
        print (query1)
        print ("\n".join(map(str, post_process(res1))))
        print (query2)
        print ("\n".join(map(str, post_process(res2))))
        raise (e)

class Tests(unittest.TestCase):

    def test_expand_lets(self):
        """
        This tests the sorta knotty logic involved in making the for-
        comprehension variable available *outside* of the comprehension
        when used in PINQ
        """
        """
        tree = q[(lambda x: x + (lambda y: y + 1)(3))(5)]
        goal = q[(lambda x: (lambda y: (x + (y + 1)))(3))(5)]

        new_tree = expand_let_bindings.recurse(tree)
        import ast
        assert ast.dump(new_tree) == ast.dump(goal)

        tree = q[(lambda x: x + (lambda y: y + 1)(3) + (lambda z: z + 2)(4))(5)]
        goal = q[(lambda x: (lambda z: (lambda y: ((x + (y + 1)) + (z + 2)))(3))(4))(5)]

        new_tree = expand_let_bindings.recurse(tree)
        assert ast.dump(new_tree) == ast.dump(goal)

        tree = q[(lambda x: (x, lambda w: (lambda y: y + 1)(3) + (lambda z: z + 2)(4)))(5)]
        goal = q[(lambda x: (x, (lambda w: (lambda z: (lambda y: ((y + 1) + (z + 2)))(3))(4))))(5)]

        new_tree = expand_let_bindings.recurse(tree)
        assert ast.dump(new_tree) == ast.dump(goal)
        """
    """
    Most examples taken from
    http://sqlzoo.net/wiki/Main_Page
    """
    def test_basic(self):
        # all countries in europe
        compare_queries(
            "SELECT name FROM country WHERE continent = 'Europe'",
            sql[(x.name for x in db.country if x.continent == 'Europe')]
        )
        # countries whose area is bigger than 10000000
        compare_queries(
            "SELECT name, surface_area FROM country WHERE surface_area > 10000000",
            sql[((x.name, x.surface_area) for x in db.country if x.surface_area > 10000000)]
        )

    def test_nested(self):

        # countries on the same continent as India or Iran
        compare_queries(
            """
            SELECT name, continent FROM country
            WHERE continent IN (
                SELECT continent FROM country
                WHERE name IN ('India', 'Iran')
            )
            """,
            sql[(
                (x.name, x.continent) for x in db.country
                if x.continent in (
                    y.continent for y in db.country
                    if y.name in ['India', 'Iran']
                )
            )]
        )

        # countries in the same continent as Belize or Belgium
        compare_queries(
            """
            SELECT w.name, w.continent
            FROM country w
            WHERE w.continent in (
                SELECT z.continent
                FROM country z
                WHERE z.name = 'Belize' OR z.name = 'Belgium'
            )
            """,
            sql[(
                (c.name, c.continent) for c in db.country
                if c.continent in (
                    x.continent for x in db.country
                    if (x.name == 'Belize') | (x.name == 'Belgium')
                )
            )]
        )

    def test_operators(self):
        # countries in europe with a DNP per capita larger than the UK
        compare_queries(
            """
            SELECT name FROM country
            WHERE gnp/population > (
                SELECT gnp/population FROM country
                WHERE name = 'United Kingdom'
            )
            AND continent = 'Europe'
            """,
            sql[(
                x.name for x in db.country
                if x.gnp / x.population > (
                    y.gnp / y.population for y in db.country
                    if y.name == 'United Kingdom'
                )
                if (x.continent == 'Europe')
            )]
        )

    def test_aggregate(self):
        # the population of the world
        compare_queries(
            "SELECT SUM(population) FROM country",
            sql[(func.sum(x.population) for x in db.country)]
        )
        # number of countries whose area is at least 1000000
        compare_queries(
            "select count(*) from country where surface_area >= 1000000",
            sql[(func.count(x.name) for x in db.country if x.surface_area >= 1000000)]
        )

    def test_aliased(self):

        # continents whose total population is greater than 100000000
        compare_queries(
            """
            SELECT DISTINCT(x.continent)
            FROM country x
            WHERE 100000000 < (
                SELECT SUM(w.population)
                from country w
                WHERE w.continent = x.continent
            )
            """,
            sql[(
                func.distinct(x.continent) for x in db.country
                if (
                    func.sum(w.population) for w in db.country
                    if w.continent == x.continent
                ).as_scalar() > 100000000
            )]
        )

    def test_query_macro(self):
        query = sql[(
            func.distinct(x.continent) for x in db.country
            if (
                func.sum(w.population) for w in db.country
                if w.continent == x.continent
            ) > 100000000
        )]
        sql_results = engine.execute(query).fetchall()
        query_macro_results = query[(
            func.distinct(x.continent) for x in db.country
            if (
                func.sum(w.population) for w in db.country
                if w.continent == x.continent
            ) > 100000000
        )]
        assert sql_results == query_macro_results


    def test_join(self):
        # number of cities in Asia
        compare_queries(
            """
            SELECT COUNT(t.name)
            FROM country c
            JOIN city t
            ON (t.country_code = c.code)
            WHERE c.continent = 'Asia'
            """,
            sql[(
                func.count(t.name)
                for c in db.country
                for t in db.city
                if t.country_code == c.code
                if c.continent == 'Asia'
            )]
        )

        # name and population for each country and city where the city's
        # population is more than half the country's
        compare_queries(
            """
            SELECT t.name, t.population, c.name, c.population
            FROM country c
            JOIN city t
            ON t.country_code = c.code
            WHERE t.population > c.population / 2
            """,
            sql[(
                (t.name, t.population, c.name, c.population)
                for c in db.country
                for t in db.city
                if t.country_code == c.code
                if t.population > c.population / 2
            )],
            lambda x: sorted(map(str, x))
        )
    def test_join_complicated(self):
        compare_queries(
            """
            SELECT t.name, t.population, c.name, c.population
            FROM country c
            JOIN city t
            ON t.country_code = c.code
            AND t.population * 1.0 / c.population = (
                SELECT MAX(tt.population * 1.0 / c.population)
                FROM city tt
                WHERE tt.country_code = t.country_code
            )
            """,
            sql[(
                (t.name, t.population, c.name, c.population)
                for c in db.country
                for t in db.city
                if t.country_code == c.code
                if t.population * 1.0 / c.population == (
                    func.max(tt.population * 1.0 / c.population)
                    for tt in db.city
                    if tt.country_code == t.country_code
                )
            )],
            lambda x: sorted(map(str, x))
        )

    def test_order_group(self):
        # the name of every country sorted in order
        compare_queries(
            "SELECT c.name FROM country c ORDER BY c.population",
            sql[((c.name for c in db.country).order_by(c.population))]
        )

        # sum up the population of every country using GROUP BY instead of a JOIN
        compare_queries(
            """
            SELECT t.country_code, sum(t.population)
            FROM city t GROUP BY t.country_code
            ORDER BY sum(t.population)
            """,
            sql[
                ((t.country_code, func.sum(t.population)) for t in db.city)
                .group_by(t.country_code)
                .order_by(func.sum(t.population))
            ]
        )

    def test_limit_offset(self):
        # bottom 10 countries by population
        compare_queries(
            "SELECT c.name FROM country c ORDER BY c.population LIMIT 10",
            sql[
                (c.name for c in db.country)
                .order_by(c.population)
                .limit(10)
            ]
        )

        # bottom 100 to 110 countries by population
        compare_queries(
            "SELECT c.name FROM country c ORDER BY c.population LIMIT 10 OFFSET 100",
            sql[
                (c.name for c in db.country)
                .order_by(c.population)
                .limit(10)
                .offset(100)
            ]
        )

        # top 10 countries by population
        compare_queries(
            "SELECT c.name FROM country c ORDER BY c.population DESC LIMIT 10",
            sql[
                (c.name for c in db.country)
                .order_by(c.population.desc())
                .limit(10)
            ]
        )



########NEW FILE########
__FILENAME__ = pyxl_snippets

from macropy.case_classes import macros, case
from macropy.experimental.pyxl_strings import macros, p
from macropy.tracing import macros, require


from pyxl.html import *
import re
import unittest
from xml.etree import ElementTree

def normalize(string):
    return ElementTree.tostring(
        ElementTree.fromstring(
            re.sub("\n *", "", string)
        )
    , encoding='utf8', method='xml')

class Tests(unittest.TestCase):
    def test_inline_python(self):

        image_name = "bolton.png"
        image = p['<img src="/static/images/{image_name}" />']

        text = "Michael Bolton"
        block = p['<div>{image}{text}</div>']

        element_list = [image, text]
        block2 = p['<div>{element_list}</div>']

        with require:
            block2.to_string() == '<div><img src="/static/images/bolton.png" />Michael Bolton</div>'


    def test_dynamic(self):
        items = ['Puppies', 'Dragons']
        nav = p['<ul />']
        for text in items:
            nav.append(p['<li>{text}</li>'])

        with require:
            str(nav) == "<ul><li>Puppies</li><li>Dragons</li></ul>"

    def test_attributes(self):
        fruit = p['<div data-text="tangerine" />']
        with require:
            fruit.data_text == "tangerine"
        fruit.set_attr('data-text', 'clementine')
        with require:
            fruit.attr('data-text') == "clementine"


    def test_interpreter(self):
        safe_value = "<b>Puppies!</b>"
        unsafe_value = "<script>bad();</script>"
        unsafe_attr = '">'
        pyxl_blob = p["""<div class="{unsafe_attr}">
                   {unsafe_value}
                   {rawhtml(safe_value)}
               </div>"""]
        target_blob = '<div class="&quot;&gt;">&lt;script&gt;bad();&lt;/script&gt;<b>Puppies!</b></div>'
        with require:
            normalize(pyxl_blob.to_string()) == normalize(target_blob)

    def test_modules(self):
        from pyxl.element import x_element
        @case
        class User(name, profile_picture):
            pass

        class x_user_badge(x_element):
            __attrs__ = {
                'user': object,
            }
            def render(self):
                return p["""
                    <div>
                        <img src="{self.user.profile_picture}" style="float: left; margin-right: 10px;"/>
                        <div style="display: table-cell;">
                            <div>{self.user.name}</div>
                            {self.children()}
                        </div>
                    </div>"""]

        user = User("cowman", "http:/www.google.com")
        content = p['<div>Any arbitrary content...</div>']
        pyxl_blob = p['<user_badge user="{user}">{content}</user_badge>']
        target_blob = """
        <div>
            <img src="http:/www.google.com" style="float: left; margin-right: 10px;" />
            <div style="display: table-cell;"><div>cowman</div>
            <div>Any arbitrary content...</div></div>
        </div>"""

        with require:
            normalize(pyxl_blob.to_string()) == normalize(target_blob)




########NEW FILE########
__FILENAME__ = tco
import unittest
from macropy.experimental.tco import macros, tco
from macropy.case_classes import macros, case
from macropy.experimental.pattern import macros, switch, _matching, ClassMatcher


class Tests(unittest.TestCase):
    def test_tco_basic(self):
        @tco
        def foo(n):
            if n == 0:
                return 1
            return foo(n-1)
        self.assertEquals(1, foo(3000))


    def test_tco_returns(self):

        @case
        class Cons(x, rest): pass

        @case
        class Nil(): pass

        def my_range(n):
            cur = Nil()
            for i in reversed(range(n)):
                cur = Cons(i, cur)
            return cur

        @tco
        def oddLength(xs):
            with switch(xs):
                if Nil():
                    return False
                else:
                    return evenLength(xs.rest)

        @tco
        def evenLength(xs):
            with switch(xs):
                if Nil():
                    return True
                else:
                    return oddLength(xs.rest)

        self.assertTrue(True, evenLength(my_range(2000)))
        self.assertTrue(True, oddLength(my_range(2001)))
        # if we get here, then we haven't thrown a stack overflow.  success.

    def test_implicit_tailcall(self):
        """Tests for when there is an implicit return None"""
        blah = []

        @tco
        def appendStuff(n):
            if n != 0:
                blah.append(n)
                appendStuff(n-1)

        appendStuff(10000)
        self.assertEquals(10000, len(blah))

    def test_util_func_compatibility(self):
        def util():
            return 3 + 4

        @tco
        def f(n):
            if n == 0:
                return util()
            else:
                return f(n-1)

        self.assertEquals(7, f(1000))

        def util2():
            return None

        @tco
        def f2(n):
            if n == 0:
                return util2()
            else:
                return f2(n-1)

        self.assertEquals(None, f2(1000))

    def test_tailcall_methods(self):

        class Blah(object):
            @tco
            def foo(self, n):
                if n == 0:
                    return 1
                return self.foo(n-1)

        self.assertEquals(1, Blah().foo(5000))

    def test_cross_calls(self):
        def odd(n):
            if n == 0:
                return False
            return even(n-1)

        @tco
        def even(n):
            if n == 0:
                return True
            return odd(n-1)

        def fact(n):
            @tco
            def helper(n, cumulative):
                if n == 0:
                    return cumulative
                return helper(n - 1, n * cumulative)
            return helper(n, 1)

        self.assertEquals(120, fact(5))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = peg
"""Macro to easily define recursive-descent PEG parsers"""
import re

from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, u
from macropy.quick_lambda import macros, f
from macropy.case_classes import macros, case


from collections import defaultdict

"""
PEG Parser Atoms
================
Sequence: e1 e2             ,       Seq
Ordered choice: e1 / e2     |       Or
Zero-or-more: e*            .rep    Rep
One-or-more: e+             .rep1
Optional: e?                .opt
And-predicate: &e           &       And
Not-predicate: !e           -       Not
"""

macros = Macros()


@macros.block
def peg(tree, gen_sym, **kw):
    """Macro to easily define recursive-descent PEG parsers"""
    potential_targets = [
        target.id for stmt in tree
        if type(stmt) is Assign
        for target in stmt.targets
    ]

    for statement in tree:
        if type(statement) is Assign:
            new_tree = process(statement.value, potential_targets, gen_sym)
            statement.value = hq[
                Parser.Named(lambda: ast[new_tree], [u[statement.targets[0].id]])
            ]

    return tree


@macros.expr
def peg(tree, gen_sym, **kw):
    """Macro to easily define recursive-descent PEG parsers"""
    return process(tree, [], gen_sym)


def process(tree, potential_targets, gen_sym):
    @Walker
    def PegWalker(tree, stop, collect, **kw):
        if type(tree) is Str:
            stop()
            return hq[Parser.Raw(ast[tree])]
        if type(tree) is Name and tree.id in potential_targets:
            collect(tree.id)
        if type(tree) is BinOp and type(tree.op) is RShift:
            tree.left, b_left = PegWalker.recurse_collect(tree.left)
            tree.right = hq[lambda bindings: ast[tree.right]]
            names = distinct(flatten(b_left))
            tree.right.args.args = map(f[Name(id = _)], names)
            tree.right.args.defaults = [hq[[]]] * len(names)
            tree.right.args.kwarg = gen_sym("kw")
            stop()

            return tree

        if type(tree) is BinOp and type(tree.op) is FloorDiv:
            tree.left, b_left = PegWalker.recurse_collect(tree.left)
            stop()
            collect(b_left)
            return tree

        if type(tree) is Tuple:
            result = hq[Parser.Seq([])]

            result.args[0].elts = tree.elts
            all_bindings = []
            for i, elt in enumerate(tree.elts):
                result.args[0].elts[i], bindings = PegWalker.recurse_collect(tree.elts[i])
                all_bindings.append(bindings)
            stop()
            collect(all_bindings)
            return result

        if type(tree) is Compare and type(tree.ops[0]) is Is:
            left_tree, bindings = PegWalker.recurse_collect(tree.left)
            new_tree = hq[ast[left_tree].bind_to(u[tree.comparators[0].id])]
            stop()
            collect(bindings + [tree.comparators[0].id])
            return new_tree

    new_tree = PegWalker.recurse(tree)
    return new_tree


def cut():
    """Used within a Seq parser (p1, p2, p3,...) to commit the Seq to that
    alternative.

    After the Seq passes the `cut`, any failure becomes fatal, and backtracking
    is not performed. This improves performance and improves the quality
    of the error messages."""


@case
class Input(string, index):
    pass


@case
class Success(output, bindings, remaining):
    """
    output: the final value that was parsed
    bindings: named value bindings, created by the `is` keyword
    remaining: an Input representing the unread portion of the input
    """
    pass


@case
class Failure(remaining, failed, fatal | False):
    """
    remaining: an Input representing the unread portion of the input
    failed: a List[Parser], containing the stack of parsers in
            effect at time of failure
    fatal: whether a parent parser which receives this result from a child
           should continue backtracking
    """
    @property
    def index(self):
        return self.remaining.index
    @property
    def trace(self):
        return [x for f in self.failed for x in f.trace_name]

    @property
    def msg(self):
        """A pretty human-readable error message representing this Failure"""
        line_length = 60

        string = self.remaining.string
        index = self.index
        line_start = string.rfind('\n', 0, index+1)

        line_end = string.find('\n', index+1, len(string))
        if line_end == -1:
            line_end = len(string)

        line_num = string.count('\n', 0, index)

        offset = min(index - line_start , 40)

        msg = "index: " + str(self.index) + ", line: " + str(line_num + 1) + ", col: " + str(index - line_start) + "\n" + \
              " / ".join(self.trace) + "\n" + \
              string[line_start+1:line_end][index - offset - line_start:index+line_length-offset - line_start] + "\n" + \
              (offset-1) * " " + "^" + "\n" +\
              "expected: " + self.failed[-1].short_str()
        return msg

class ParseError(Exception):
    """An exception that wraps a Failure"""
    def __init__(self, failure):
        self.failure = failure
        Exception.__init__(self, failure.msg)


@case
class Parser:
    def parse(self, string):
        """String -> value; throws ParseError in case of failure"""
        res = Parser.Full(self).parse_input(Input(string, 0))
        if type(res) is Success:
            return res.output
        else:
            raise ParseError(res)

    def parse_partial(self, string):
        """String -> Success | Failure"""
        return self.parse_input(Input(string, 0))

    def parse_string(self, string):
        """String -> Success | Failure"""
        return Parser.Full(self).parse_input(Input(string, 0))

    def parse_input(self, input):
        """Input -> Success | Failure"""

    @property
    def trace_name(self):
        return []

    def bind_to(self, string):
        return Parser.Named(lambda: self, [string])

    def __and__(self, other):   return Parser.And([self, other])

    def __or__(self, other):    return Parser.Or([self, other])

    def __neg__(self):          return Parser.Not(self)

    @property
    def join(self):
        return self // "".join
    @property
    def rep1(self):
        return Parser.And([Parser.Rep(self), self])

    @property
    def rep(self):
        return Parser.Rep(self)

    def rep1_with(self, other):
        return Parser.Seq([self, Parser.Seq([other, self]).rep]) // (lambda x: [x[0]] + [y[1] for y in x[1]])

    def rep_with(self, other):
        return self.rep1_with(other) | Parser.Succeed([])
    @property
    def opt(self):
        return Parser.Or([self, Parser.Raw("")])

    @property
    def r(self):
        """Creates a regex-matching parser from the given raw parser"""
        return Parser.Regex(self.string)
    def __mul__(self, n):   return Parser.RepN(self, n)

    def __floordiv__(self, other):   return Parser.Transform(self, other)

    def __pow__(self, other):   return Parser.Transform(self, lambda x: other(*x))

    def __rshift__(self, other): return Parser.TransformBound(self, other)

    class Full(parser):
        def parse_input(self, input):
            res = self.parser.parse_input(input)
            if type(res) is Success and res.remaining.index < len(input.string):
                return Failure(res.remaining, [self])
            else:
                return res
        def short_str(self):
            return self.parser.short_str()

    class Raw(string):
        def parse_input(self, input):
            if input.string[input.index:].startswith(self.string):
                return Success(self.string, {}, input.copy(index = input.index + len(self.string)))
            else:
                return Failure(input, [self])

        def short_str(self):
            return repr(self.string)

    class Regex(regex_string):
        def parse_input(self, input):
            match = re.match(self.regex_string, input.string[input.index:])
            if match:
                group = match.group()
                return Success(group, {}, input.copy(index = input.index + len(group)))
            else:
                return Failure(input, [self])

        def short_str(self):
            return repr(self.regex_string) + ".r"

    class Seq(children):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])
            committed = False
            for child in self.children:
                if child is cut:
                    committed = True
                else:
                    res = child.parse_input(current_input)

                    if type(res) is Failure:
                        if committed or res.fatal:
                            return Failure(res.remaining, [self] + res.failed, True)
                        else:
                            return res

                    current_input = res.remaining
                    results.append(res.output)
                    for k, v in res.bindings.items():
                        result_dict[k] = v

            return Success(results, result_dict, current_input)

        def short_str(self):
            return "(" + ", ".join(map(lambda x: x.short_str(), self.children)) + ")"
    class Or(children):
        def parse_input(self, input):
            for child in self.children:
                res = child.parse_input(input)

                if type(res) is Success:
                    return res
                elif res.fatal:
                    res.failed = [self] + res.failed
                    return res


            return Failure(input, [self])

        def __or__(self, other):   return Parser.Or(self.children + [other])

        def short_str(self):
            return "(" + " | ".join(map(lambda x: x.short_str(), self.children)) + ")"

    class And(children):
        def parse_input(self, input):
            results = [child.parse_input(input) for child in self.children]
            failures = [res for res in results if type(res) is Failure]
            if failures == []:
                return results[0]
            else:
                failures[0].failed = [self] + failures[0].failed
                return failures[0]

        def __and__(self, other):   return Parser.And(self.children + [other])

        def short_str(self):
            return "(" + " & ".join(map(lambda x: x.short_str(), self.children)) + ")"

    class Not(parser):
        def parse_input(self, input):
            if type(self.parser.parse_input(input)) is Success:
                return Failure(input, [self])
            else:
                return Success(None, {}, input)

        def short_str(self):
            return "-" + self.parser.short_str()

    class Rep(parser):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])

            while True:
                res = self.parser.parse_input(current_input)
                if type(res) is Failure:
                    if res.fatal:
                        res.failed = [self] + res.failed
                        return res
                    else:
                        return Success(results, result_dict, current_input)

                current_input = res.remaining

                for k, v in res.bindings.items():
                    result_dict[k] = result_dict[k] + [v]

                results.append(res.output)


    class RepN(parser, n):
        def parse_input(self, input):
            current_input = input
            results = []
            result_dict = defaultdict(lambda: [])

            for i in range(self.n):
                res = self.parser.parse_input(current_input)
                if type(res) is Failure:
                    res.failed = [self] + res.failed
                    return res

                current_input = res.remaining

                for k, v in res.bindings.items():
                    result_dict[k] = result_dict[k] + [v]

                results.append(res.output)

            return Success(results, result_dict, current_input)

        def short_str(self):
            return self.parser.short_str() + "*" + n

    class Transform(parser, func):
        def parse_input(self, input):
            res = self.parser.parse_input(input)

            if type(res) is Success:
                res.output = self.func(res.output)
            else:
                res.failed = [self] + res.failed
            return res

        def short_str(self):
            return self.parser.short_str()

    class TransformBound(parser, func):
        def parse_input(self, input):
            res = self.parser.parse_input(input)
            if type(res) is Success:
                res.output = self.func(**res.bindings)
                res.bindings = {}
            else:
                res.failed = [self] + res.failed
            return res

        def short_str(self):
            return self.parser.short_str()

    class Named(parser_thunk, trace_name):
        self.stored_parser = None
        @property
        def parser(self):
            if not self.stored_parser:
                self.stored_parser = self.parser_thunk()

            return self.stored_parser
        def parse_input(self, input):

            res = self.parser.parse_input(input)
            if type(res) is Success:
                res.bindings = {self.trace_name[0]: res.output}
            else:
                res.failed = [self] + res.failed
            return res

        def short_str(self):
            return self.trace_name[0]

    class Succeed(string):
        def parse_input(self, input):
            return Success(self.string, {}, input)

    class Fail():
        def parse_input(self, input):
            return Failure(input, [self])

        def short_str(self):
            return "fail"
########NEW FILE########
__FILENAME__ = quick_lambda
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from macropy.core.hquotes import macros, hq, ast, u, name
from macropy.core.cleanup import ast_ctx_fixer
macros = Macros()

def _():
    """Placeholder for a function argument in the `f` macro."""


@macros.expr
def f(tree, gen_sym, **kw):
    """Macro to concisely create function literals; any `_`s within the
    wrapped expression becomes an argument to the generated function."""
    @Walker
    def underscore_search(tree, collect, **kw):
        if isinstance(tree, Name) and tree.id == "_":
            name = gen_sym("_")
            tree.id = name
            collect(name)
            return tree

    tree, used_names = underscore_search.recurse_collect(tree)

    new_tree = q[lambda: ast[tree]]
    new_tree.args.args = [Name(id = x) for x in used_names]
    return new_tree


@macros.expr
def lazy(tree, **kw):
    """Macro to wrap an expression in a lazy memoizing thunk. This can be
    called via `thing()` to extract the value. The wrapped expression is
    only evaluated the first time the thunk is called and the result cached
    for all subsequent evaluations."""
    return hq[Lazy(lambda: ast[tree])]


def get_interned(store, index, thunk):

    if store[index] is None:
        store[index] = [thunk()]

    return store[index][0]


@register(injected_vars)
def interned_count(**kw):
    return [0]

@register(injected_vars)
def interned_name(gen_sym, **kw):
    return gen_sym()

@register(post_processing)
def interned_processing(tree, gen_sym, interned_count, interned_name, **kw):

    if interned_count[0] != 0:
        with q as code:
            name[interned_name] = [None for x in range(u[interned_count[0]])]

        code = ast_ctx_fixer.recurse(code)
        code = map(fix_missing_locations, code)

        tree.body = code + tree.body

    return tree



@macros.expr
def interned(tree, interned_name, interned_count, **kw):
    """Macro to intern the wrapped expression on a per-module basis"""
    interned_count[0] += 1

    return hq[get_interned(name[interned_name], interned_count[0] - 1, lambda: ast[tree])]

########NEW FILE########
__FILENAME__ = string_interp
import re

from macropy.core.macros import *
from macropy.core.hquotes import macros, hq, u, ast_list

macros = Macros()

@macros.expr
def s(tree, **kw):
    """Macro to easily interpolate values into string literals."""
    captured = []
    new_string = ""
    chunks = re.split("{(.*?)}", tree.s)
    for i in range(0, len(chunks)):
        if i % 2 == 0:
            new_string += chunks[i]
        else:
            new_string += "%s"
            captured += [chunks[i]]

    result = hq[u[new_string] % tuple(ast_list[map(parse_expr, captured)])]

    return result

########NEW FILE########
__FILENAME__ = case_classes
from macropy.case_classes import macros, case, enum, enum_new
from macropy.core.failure import MacroExpansionError
from macropy.tracing import macros, show_expanded
import unittest

class Tests(unittest.TestCase):

    def test_basic(self):

        @case
        class Point(x, y):
            pass

        for x in range(1, 10):
            for y in range(1, 10):
                p = Point(x, y)
                assert(str(p) == repr(p) == "Point(%s, %s)" % (x, y))
                assert(p.x == x)
                assert(p.y == y)
                assert(Point(x, y) == Point(x, y))
                assert((Point(x, y) != Point(x, y)) is False)

    def test_advanced(self):

        @case
        class Point(x, y):
            def length(self):
                return (self.x ** 2 + self.y ** 2) ** 0.5

        assert(Point(3, 4).length() == 5)
        assert(Point(5, 12).length() == 13)
        assert(Point(8, 15).length() == 17)

        a = Point(1, 2)
        b = a.copy(x = 3)

        assert(a == Point(1, 2))
        assert(b == Point(3, 2))
        c = b.copy(y = 4)
        assert(a == Point(1, 2))
        assert(b == Point(3, 2))
        assert(c == Point(3, 4))

    def test_nested(self):

        @case
        class List():
            def __len__(self):
                return 0

            def __iter__(self):
                return iter([])

            class Nil:
                pass

            class Cons(head, tail):
                def __len__(self):
                    return 1 + len(self.tail)

                def __iter__(self):
                    current = self

                    while len(current) > 0:
                        yield current.head
                        current = current.tail

        assert isinstance(List.Cons(None, None), List)
        assert isinstance(List.Nil(), List)

        my_list = List.Cons(1, List.Cons(2, List.Cons(3, List.Nil())))
        empty_list = List.Nil()

        assert len(my_list) == 3
        assert sum(iter(my_list)) == 6
        assert sum(iter(empty_list)) == 0

    def test_body_init(self):
        @case
        class Point(x, y):
            if True:
                self.length = (self.x**2 + self.y**2) ** 0.5

        assert Point(3, 4).length == 5

    def test_varargs_kwargs(self):
        @case
        class PointArgs(x, y, [rest]):
            def extra_count(self):
                return len(self.rest)

        assert PointArgs(3, 4).extra_count() == 0
        assert PointArgs(3, 4, 5).extra_count() == 1
        assert PointArgs(3, 4, 5, 6).extra_count() == 2
        assert PointArgs(3, 4, 5, 6, 7).rest == (5, 6, 7)

        with self.assertRaises(TypeError):
            PointArgs(3, 4, p = 0)


        @case
        class PointKwargs(x, y, {rest}):
            pass
        assert PointKwargs(1, 2).rest == {}
        assert PointKwargs(1, 2, k = 10).rest == {"k": 10}
        assert PointKwargs(1, 2, a=1, b=2).rest == {"a": 1, "b": 2}

        with self.assertRaises(TypeError):
            PointKwargs(3, 4, 4)

        @case
        class PointAll([args], {kwargs}):
            pass
        assert PointAll(1, 2, 3, a=1, b=2, c=3).args == (1, 2, 3)
        assert PointAll(1, 2, 3, a=1, b=2, c=3).kwargs == {"a": 1, "b": 2, "c": 3}
    def test_default_values(self):
        @case
        class Point(x | 0, y | 0):
            pass
        assert str(Point()) == "Point(0, 0)"
        assert str(Point(1)) == "Point(1, 0)"
        assert str(Point(1, 2)) == "Point(1, 2)"
        assert str(Point(y = 5)) == "Point(0, 5)"
        assert str(Point(y = 5, x = 7)) == "Point(7, 5)"
    def test_overriding_methods(self):
        @case
        class Point(x, y):
            def __str__(self):
                return "mooo " + super(Point, self).__str__()

            def __init__(self):
                self.x = 10
                self.y = 10

        assert str(Point()) == "mooo Point(10, 10)"

    def test_destructuring(self):
        @case
        class Point(x, y):
            pass

        p = Point(1, 2)
        x, y = p


    def test_definition_error(self):
        with self.assertRaises(MacroExpansionError) as ce:
            @case
            class Point(1 + 2):
                pass
        assert ce.exception.message == (
            "Illegal expression in case class signature: (1 + 2)"
        )

    def test_cannot_detect_self(self):
        @case
        class Point(x, y):
            self.w = 10
            def f(self):
                self.z = 1
                def fail(self):
                    self.k = 1
                def fail2(selfz):
                    self[0] = 1
                    self.j = 1
                    self.m = 10

            def g(this):
                this.cow = 10
        p = Point(1, 2)

        # these should raise an error if they're uninitialized
        with self.assertRaises(AttributeError):
            p.z
        with self.assertRaises(AttributeError):
            p.cow

        p.f()
        p.g()
        assert p.x == 1
        assert p.y == 2
        assert p.w == 10
        assert p.z == 1
        assert p.cow == 10
        with self.assertRaises(AttributeError):
            Point.k

        p.j = 1
        p.m = 12
        assert p.j == 1
        assert p.m == 12
        assert Point._fields == ['x', 'y']




    def test_enum(self):

        @enum
        class Direction:
            North, South, East, West

        assert Direction(name="North") is Direction.North

        assert repr(Direction.North) == str(Direction.North) == "Direction.North"

        # getting name
        assert Direction.South.name == "South"


        # selecting by id
        assert Direction(id=2) is Direction.East

        # getting id
        assert Direction.West.id == 3


        # `next` and `prev` properties
        assert Direction.North.next is Direction.South
        assert Direction.West.prev is Direction.East

        # `next` and `prev` wrap-around
        assert Direction.West.next is Direction.North
        assert Direction.North.prev is Direction.West

        # `all`
        assert Direction.all == [
            Direction.North,
            Direction.South,
            Direction.East,
            Direction.West
        ]



    def test_multiline_enum(self):
        @enum
        class Direction:
            North
            South
            East
            West

        assert Direction(name="North") is Direction.North
        assert Direction(name="West") is Direction.West

    def test_complex_enum(self):
        @enum
        class Direction(alignment, continents):
            North("Vertical", ["Northrend"])
            East("Horizontal", ["Azeroth", "Khaz Modan", "Lordaeron"])
            South("Vertical", ["Pandaria"])
            West("Horizontal", ["Kalimdor"])

            @property
            def opposite(self):
                return Direction(id=(self.id + 2) % 4)

            def padded_name(self, n):
                return (" " * n) + self.name + (" " * n)

        # members
        assert Direction.North.alignment == "Vertical"
        assert Direction.East.continents == ["Azeroth", "Khaz Modan", "Lordaeron"]

        # properties
        assert Direction.North.opposite is Direction.South

        # methods
        assert Direction.South.padded_name(2) == "  South  "

    def test_enum_error(self):
        with self.assertRaises(MacroExpansionError) as e:
            @enum
            class Direction:
                2
        assert e.exception.message == "Can't have `2` in body of enum"

        with self.assertRaises(MacroExpansionError) as e:
            @enum
            class Direction:
                a()(b)
        assert e.exception.message == "Can't have `a()(b)` in body of enum"


########NEW FILE########
__FILENAME__ = peg
import unittest
from macropy.peg import macros, peg, Success, cut, ParseError

from macropy.tracing import macros, require
from macropy.quick_lambda import macros, f, _
class Tests(unittest.TestCase):
    def test_basic(self):
        parse1 = peg["Hello World"]
        with require:
            parse1.parse_string("Hello World").output == 'Hello World'
            parse1.parse_string("Hello, World").index == 0

        parse2 = peg[("Hello World", (".").r)]
        with require:
            parse2.parse_string("Hello World").index == 11
            parse2.parse_string("Hello World1").output == ['Hello World', '1']
            parse2.parse_string("Hello World ").output == ['Hello World', ' ']

    def test_operators(self):
        parse1 = peg["Hello World"]

        parse2 = peg[(parse1, "!".rep1)]
        with require:
            parse2.parse_string("Hello World!!!").output == ['Hello World', ['!', '!', '!']]
            parse2.parse_string("Hello World!").output  == ['Hello World', ['!']]
            parse2.parse_string("Hello World").index == 11

        parse3 = peg[(parse1, ("!" | "?"))]

        with require:
            parse3.parse_string("Hello World!").output == ['Hello World', '!']
            parse3.parse_string("Hello World?").output == ['Hello World', '?']
            parse3.parse_string("Hello World%").index == 11

        parse4 = peg[(parse1, "!".rep & "!!!")]

        with require:
            parse4.parse_string("Hello World!!!").output == ['Hello World', ['!', '!', '!']]
            parse4.parse_string("Hello World!!").index == 11

        parse4 = peg[(parse1, "!".rep & "!!!")]

        with require:
            parse4.parse_string("Hello World!!!").output == ["Hello World", ["!", "!", "!"]]

        parse5 = peg[(parse1, "!".rep & -"!!!")]
        with require:
            parse5.parse_string("Hello World!!").output == ["Hello World", ['!', '!']]
            parse5.parse_string("Hello World!!!").index == 11

        parse6 = peg[(parse1, "!" * 3)]
        with require:
            parse6.parse_string("Hello World!").index == 12
            parse6.parse_string("Hello World!!").index == 13
            parse6.parse_string("Hello World!!!").output == ["Hello World", ['!', '!', '!']]
            parse6.parse_string("Hello World!!!!").index == 14


    def test_conversion(self):
        parse1 = peg[("Hello World", "!".rep1) // f[_[1]]]

        with require:
            parse1.parse_string("Hello World!!!").output == ['!', '!', '!']
            parse1.parse_string("Hello World").index == 11

        parse2 = parse1 // len

        with require:
            parse2.parse_string("Hello World!!!").output == 3


    def test_block(self):
        with peg:
            parse1 = ("Hello World", "!".rep1) // f[_[1]]
            parse2 = parse1 // len

        with require:
            parse1.parse_string("Hello World!!!").output == ['!', '!', '!']
            parse1.parse_string("Hello World").index == 11
            parse2.parse_string("Hello World!!!").output == 3

    def test_recursive(self):
        with peg:
            expr = ("(", expr, ")").rep | ""

        with require:
            expr.parse_string("()").output
            expr.parse_string("(()())").output
            expr.parse_partial("(((()))))").output

            expr.parse_partial("((()))))").output
            expr.parse_string("((()))))").index == 6
            expr.parse_partial(")((()()))(").output == []
            expr.parse_string(")((()()))(").index == 0
            expr.parse_partial(")()").output == []
            expr.parse_string(")()").index == 0

    def test_bindings(self):
        with peg:
            short = ("omg" is wtf) >> wtf * 2
            medium = ("omg" is o, " ", "wtf" is w, " ", "bb+q".r is b) >> o + w + b
            seq1 = ("l", ("ol".rep1) is xxx) >> xxx
            seq2 = ("l", ("ol" is xxx).rep1) >> xxx
            seq3 = ("l", ("ol" is xxx).rep1) >> sum(map(len, xxx))
        with require:
            short.parse_string('omg').output == 'omgomg'
            short.parse_string('omgg').index == 3
            short.parse_string('cow').index == 0
            medium.parse_string('omg wtf bbq').output == 'omgwtfbbq'
            medium.parse_string('omg wtf bbbbbq').output == 'omgwtfbbbbbq'
            medium.parse_string('omg wtf bbqq').index == 11
            seq3.parse_string("lolololol").output == 8

        for x in ["lol", "lolol", "ol", "'"]:
            if type(seq1.parse_string(x)) is Success:

                require[seq1.parse_string(x).output == seq2.parse_string(x).output]
            else:

                require[seq1.parse_string(x).index == seq2.parse_string(x).index]

    def test_arithmetic(self):
        """
        PEG grammar from Wikipedia

        Op      <- "+" / "-" / "*" / "/"
        Value   <- [0-9]+ / '(' Expr ')'
        Expr <- Value (Op Value)*

        simplified it to remove operator precedence
        """

        def reduce_chain(chain):
            chain = list(reversed(chain))
            o_dict = {
                "+": f[_+_],
                "-": f[_-_],
                "*": f[_*_],
                "/": f[_/_],
            }
            while len(chain) > 1:
                a, [o, b] = chain.pop(), chain.pop()
                chain.append(o_dict[o](a, b))
            return chain[0]

        with peg:
            op = '+' | '-' | '*' | '/'
            value = '[0-9]+'.r // int | ('(', expr, ')') // f[_[1]]
            expr = (value, (op, value).rep is rest) >> reduce_chain([value] + rest)

        with require:
            expr.parse("123") == 123
            expr.parse("((123))") == 123
            expr.parse("(123+456+789)") == 1368
            expr.parse("(6/2)")  == 3
            expr.parse("(1+2+3)+2") == 8
            expr.parse("(((((((11)))))+22+33)*(4+5+((6))))/12*(17+5)")  == 1804


    def test_cut(self):
        with peg:
            expr1 = ("1", cut, "2", "3") | ("1", "b", "c")
            expr2 = ("1", "2", "3") | ("1", "b", "c")

        with require:
            expr1.parse_string("1bc").index == 1
            expr2.parse_string("1bc").output == ['1', 'b', 'c']

    def test_short_str(self):
        with peg:
            p1 = "omg"
            p2 = "omg".r
            p3 = "omg" | "wtf"
            p4 = "omg", "wtf"
            p5 = "omg" & "wtf"
            p6 = p1
            p7 = "a" | "b" | "c"
            p8 = ("1" | "2" | "3") & "\d".r & ("2" | "3") | p7

        with require:
            p1.parser.short_str() == "'omg'"
            p2.parser.short_str() == "'omg'.r"
            p3.parser.short_str() == "('omg' | 'wtf')"
            p4.parser.short_str() == "('omg', 'wtf')"
            p5.parser.short_str() == "('omg' & 'wtf')"
            p6.parser.short_str() == "p1"
            p7.parser.short_str() == "('a' | 'b' | 'c')"
            p8.parser.short_str() == "((('1' | '2' | '3') & '\\\\d'.r & ('2' | '3')) | p7)"

    def test_bindings_json(self):

        def test(parser, string):
            import json
            try:
                assert parser.parse(string) == json.loads(string)
            except Exception, e:
                print(parser.parse_string(string))
                print(json.loads(string))
                raise e

        def decode(x):
            x = x.decode('unicode-escape')
            try:
                return str(x)
            except:
                return x
        escape_map = {
            '"': '"',
            '/': '/',
            '\\': '\\',
            'b': '\b',
            'f': '\f',
            'n': '\n',
            'r': '\r',
            't': '\t'
        }

        """
        JSON <- S? ( Object / Array / String / True / False / Null / Number ) S?

        Object <- "{"
                     ( String ":" JSON ( "," String ":" JSON )*
                     / S? )
                 "}"

        Array <- "["
                    ( JSON ( "," JSON )*
                    / S? )
                "]"

        String <- S? ["] ( [^ " \ U+0000-U+001F ] / Escape )* ["] S?

        Escape <- [\] ( [ " / \ b f n r t ] / UnicodeEscape )

        UnicodeEscape <- "u" [0-9A-Fa-f]{4}

        True <- "true"
        False <- "false"
        Null <- "null"

        Number <- Minus? IntegralPart fractPart? expPart?

        Minus <- "-"
        IntegralPart <- "0" / [1-9] [0-9]*
        fractPart <- "." [0-9]+
        expPart <- ( "e" / "E" ) ( "+" / "-" )? [0-9]+
        S <- [ U+0009 U+000A U+000D U+0020 ]+
        """
        with peg:
            json_doc = (space, (obj | array), space) // f[_[1]]
            json_exp = (space, (obj | array | string | true | false | null | number), space) // f[_[1]]

            pair = (string is k, space, ':', cut, json_exp is v) >> (k, v)
            obj = ('{', cut, pair.rep_with(",") // dict, space, '}') // f[_[1]]
            array = ('[', cut, json_exp.rep_with(","), space, ']') // f[_[1]]

            string = (space, '"', (r'[^"\\\t\n]'.r | escape | unicode_escape).rep.join is body, '"') >> "".join(body)
            escape = ('\\', ('"' | '/' | '\\' | 'b' | 'f' | 'n' | 'r' | 't') // escape_map.get) // f[_[1]]
            unicode_escape = ('\\', 'u', ('[0-9A-Fa-f]'.r * 4).join).join // decode

            true = 'true' >> True
            false = 'false' >> False
            null = 'null' >> None

            number = decimal | integer
            integer = ('-'.opt, integral).join // int
            decimal = ('-'.opt, integral, ((fract, exp).join) | fract | exp).join // float

            integral = '0' | '[1-9][0-9]*'.r
            fract = ('.', '[0-9]+'.r).join
            exp = (('e' | 'E'), ('+' | '-').opt, "[0-9]+".r).join

            space = '\s*'.r

        # test Success
        number.parse("0.123456789e-12")
        test(json_exp, r'{"\\": 123}')
        test(json_exp, "{}")

        test(string, '"i am a cow lol omfg"')
        test(array, '[1, 2, "omg", ["wtf", "bbq", 42]]')
        test(obj, '{"omg": "123", "wtf": 456, "bbq": "789"}')
        test(json_exp, '{"omg": 1, "wtf": 12.4123}  ')
        test(json_exp, """
            {
                "firstName": "John",
                "lastName": "Smith",
                "age": 25,
                "address": {
                    "streetAddress": "21 2nd Street",
                    "city": "New York",
                    "state": "NY",
                    "postalCode": 10021
                },
                "phoneNumbers": [
                    {
                        "type": "home",
                        "number": "212 555-1234"
                    },
                    {
                        "type": "fax",
                        "number": "646 555-4567"
                    }
                ]
            }
        """)

        # test Failure
        with self.assertRaises(ParseError) as e:
            json_exp.parse('{    : 1, "wtf": 12.4123}')

        assert e.exception.message ==\
"""
index: 5, line: 1, col: 6
json_exp / obj
{    : 1, "wtf": 12.4123}
     ^
expected: '}'
""".strip()

        with self.assertRaises(ParseError) as e:
            json_exp.parse('{"omg": "123", "wtf": , "bbq": "789"}')

        assert e.exception.message ==\
"""
index: 22, line: 1, col: 23
json_exp / obj / pair / v / json_exp
{"omg": "123", "wtf": , "bbq": "789"}
                      ^
expected: (obj | array | string | true | false | null | number)
""".strip()

        with self.assertRaises(ParseError) as e:
            json_exp.parse("""{
                    "firstName": "John",
                    "lastName": "Smith",
                    "age": 25,
                    "address": {
                        "streetAddress": "21 2nd Street",
                        "city": "New York",
                        "state": "NY",
                        "postalCode": 10021
                    },
                    "phoneNumbers": [
                        {
                            "type": "home",
                            "number": "212 555-1234"
                        },
                        {
                            "type": "fax",
                            "number": 646 555-4567"
                        }
                    ]
                }
            """)

        assert e.exception.message == \
"""
index: 655, line: 18, col: 43
json_exp / obj / pair / v / json_exp / array / json_exp / obj
                         "number": 646 555-4567"
                                       ^
expected: '}'
""".strip()


        # full tests, taken from http://www.json.org/JSON_checker/
        for i in range(1, 34):
            if i not in [18]: # skipping the "too much nesting" failure test

                with self.assertRaises(ParseError):
                    json_doc.parse(open(__file__ + "/../peg_json/fail%s.json" % i).read())

        for i in [1, 2, 3]:
            test(json_exp, open(__file__ + "/../peg_json/pass%s.json" % i).read())

########NEW FILE########
__FILENAME__ = quick_lambda
import unittest

from macropy.quick_lambda import macros, f, _, lazy, interned
from macropy.tracing import macros, show_expanded
class Tests(unittest.TestCase):
    def test_basic(self):
        assert map(f[_ - 1], [1, 2, 3]) == [0, 1, 2]
        assert reduce(f[_ + _], [1, 2, 3]) == 6

    def test_partial(self):
        basetwo = f[int(_, base=2)]
        assert basetwo('10010') == 18

    def test_attribute(self):
        assert map(f[_.split(' ')[0]], ["i am cow", "hear me moo"]) == ["i", "hear"]

    def test_no_args(self):
        from random import random
        thunk = f[random()]
        assert thunk() != thunk()

    def test_name_collision(self):
        sym0 = 1
        sym1 = 2
        func1 = f[_ + sym0]
        assert func1(10) == 11
        func2 = f[_ + sym0 + _ + sym1]
        assert func2(10, 10) == 23

    def test_lazy(self):
        wrapped = [0]
        def func():
            wrapped[0] += 1

        thunk = lazy[func()]

        assert wrapped[0] == 0

        thunk()
        assert wrapped[0] == 1
        thunk()
        assert wrapped[0] == 1

    def test_interned(self):

        wrapped = [0]
        def func():
            wrapped[0] += 1

        def wrapped_func():
            return interned[func()]

        assert wrapped[0] == 0
        wrapped_func()
        assert wrapped[0] == 1
        wrapped_func()
        assert wrapped[0] == 1
########NEW FILE########
__FILENAME__ = string_interp
import unittest


from macropy.string_interp import macros, s


class Tests(unittest.TestCase):
    def test_string_interpolate(self):
        a, b = 1, 2
        c = s["{a} apple and {b} bananas"]
        assert(c == "1 apple and 2 bananas")


    def test_string_interpolate_2(self):
        apple_count = 10
        banana_delta = 4
        c = s["{apple_count} {'apples'} and {apple_count + banana_delta} {''.join(['b', 'a', 'n', 'a', 'n', 'a', 's'])}"]

        assert(c == "10 apples and 14 bananas")

########NEW FILE########
__FILENAME__ = tracing
import unittest
from ast import *
from macropy.tracing import macros, trace, log, require, show_expanded
from macropy.core.quotes import macros, q, Literal
result = []

def log(x):
    result.append(x)
    pass


class Tests(unittest.TestCase):

    def test_basic(self):

        log[1 + 2]
        log["omg" * 3]

        assert(result[-2:] == [
            "1 + 2 -> 3",
            "\"omg\" * 3 -> 'omgomgomg'"
        ])

    def test_combo(self):

        trace[1 + 2 + 3 + 4]

        assert(result[-3:] == [
            "1 + 2 -> 3",
            "1 + 2 + 3 -> 6",
            "1 + 2 + 3 + 4 -> 10"
        ])

    def test_fancy(self):
        trace[[len(x)*3 for x in ['omg', 'wtf', 'b' * 2 + 'q', 'lo' * 3 + 'l']]]

        assert(result[-14:] == [
            "'b' * 2 -> 'bb'",
            "'b' * 2 + 'q' -> 'bbq'",
            "'lo' * 3 -> 'lololo'",
            "'lo' * 3 + 'l' -> 'lololol'",
            "['omg', 'wtf', 'b' * 2 + 'q', 'lo' * 3 + 'l'] -> ['omg', 'wtf', 'bbq', 'lololol']",
            "len(x) -> 3",
            "len(x)*3 -> 9",
            "len(x) -> 3",
            "len(x)*3 -> 9",
            "len(x) -> 3",
            "len(x)*3 -> 9",
            "len(x) -> 7",
            "len(x)*3 -> 21",
            "[len(x)*3 for x in ['omg', 'wtf', 'b' * 2 + 'q', 'lo' * 3 + 'l']] -> [9, 9, 9, 21]"
        ])

    def test_function_call(self):
        trace[sum([sum([1, 2, 3]), min(4, 5, 6), max(7, 8, 9)])]
        assert(result[-5:] == [
            "sum([1, 2, 3]) -> 6",
            "min(4, 5, 6) -> 4",
            "max(7, 8, 9) -> 9",
            "[sum([1, 2, 3]), min(4, 5, 6), max(7, 8, 9)] -> [6, 4, 9]",
            "sum([sum([1, 2, 3]), min(4, 5, 6), max(7, 8, 9)]) -> 19"
        ])


    def test_require(self):
        with self.assertRaises(AssertionError) as cm:
            require[1 == 10]

        assert cm.exception.message == "Require Failed\n1 == 10 -> False"

        require[1 == 1]

        with self.assertRaises(AssertionError) as cm:
            require[3**2 + 4**2 != 5**2]


        require[3**2 + 4**2 == 5**2]

    def test_require_block(self):
        with self.assertRaises(AssertionError) as cm:
            a = 10
            b = 2
            with require:
                a > 5
                a * b == 20
                a < 2
        assert cm.exception.message == "Require Failed\na < 2 -> False"


    def test_show_expanded(self):

        from macropy.core import ast_repr
        show_expanded[q[1 + 2]]

        assert "BinOp(left=Num(n=1), op=Add(), right=Num(n=2))" in result[-1]

        with show_expanded:
            a = 1
            b = 2
            with q as code:
                print a + u[b + 1]

        assert result[-3] == '\na = 1'
        assert result[-2] == '\nb = 2'
        assert "code = [Print(dest=None, values=[BinOp(left=Name(id='a', ctx=Load()), op=Add(), right=ast_repr((b + 1)))], nl=True)]" in result[-1]

########NEW FILE########
__FILENAME__ = tracing

from macropy.core.macros import *
from macropy.core.hquotes import macros, u, hq, unhygienic

import copy

macros = Macros()


def wrap(printer, txt, x):
    string = txt + " -> " + repr(x)
    printer(string)
    return x


def wrap_simple(printer, txt, x):
    string = txt
    printer(string)
    return x


@macros.expr
def log(tree, exact_src, **kw):
    """Prints out source code of the wrapped expression and the value it
    evaluates to"""
    new_tree = hq[wrap(unhygienic[log], u[exact_src(tree)], ast[tree])]
    return new_tree


@macros.expr
def show_expanded(tree, expand_macros,  **kw):
    """Prints out the expanded version of the wrapped source code, after all
    macros inside it have been expanded"""
    expanded_tree = expand_macros(tree)
    new_tree = hq[wrap_simple(unhygienic[log], u[unparse(expanded_tree)], ast[expanded_tree])]
    return new_tree


@macros.block
def show_expanded(tree, expand_macros, **kw):
    """Prints out the expanded version of the wrapped source code, after all
    macros inside it have been expanded"""
    new_tree = []
    for stmt in tree:
        new_stmt = expand_macros(stmt)

        with hq as code:
            unhygienic[log](u[unparse(new_stmt)])
        new_tree.append(code)
        new_tree.append(new_stmt)

    return new_tree


def trace_walk_func(tree, exact_src):
    @Walker
    def trace_walk(tree, stop, **kw):

        if isinstance(tree, expr) and \
                tree._fields != () and \
                type(tree) is not Name:

            try:
                literal_eval(tree)
                stop()
                return tree
            except ValueError:
                txt = exact_src(tree)
                trace_walk.walk_children(tree)
                wrapped = hq[wrap(unhygienic[log], u[txt], ast[tree])]
                stop()
                return wrapped

        elif isinstance(tree, stmt):
            txt = exact_src(tree)
            trace_walk.walk_children(tree)
            with hq as code:
                unhygienic[log](u[txt])
            stop()
            return [code, tree]

    return trace_walk.recurse(tree)


@macros.expr
def trace(tree, exact_src, **kw):
    """Traces the wrapped code, printing out the source code and evaluated
    result of every statement and expression contained within it"""
    ret = trace_walk_func(tree, exact_src)
    return ret


@macros.block
def trace(tree, exact_src, **kw):
    """Traces the wrapped code, printing out the source code and evaluated
    result of every statement and expression contained within it"""
    ret = trace_walk_func(tree, exact_src)

    return ret


def require_transform(tree, exact_src):
    ret = trace_walk_func(copy.deepcopy(tree), exact_src)
    trace_walk_func(copy.deepcopy(tree), exact_src)
    new = hq[ast[tree] or wrap_require(lambda log: ast[ret])]
    return new


def wrap_require(thunk):
    out = []
    thunk(out.append)
    raise AssertionError("Require Failed\n" + "\n".join(out))


@macros.expr
def require(tree, exact_src, **kw):
    """A version of assert that traces the expression's evaluation in the
    case of failure. If used as a block, performs this on every expression
    within the block"""
    return require_transform(tree, exact_src)


@macros.block
def require(tree, exact_src, **kw):
    """A version of assert that traces the expression's evaluation in the
    case of failure. If used as a block, performs this on every expression
    within the block"""
    for expr in tree:
        expr.value = require_transform(expr.value, exact_src)

    return tree


@macros.expose_unhygienic
def log(x):
    print(x)

########NEW FILE########
__FILENAME__ = run_tests
import unittest
import macropy.activate

import macropy.test

unittest.TextTestRunner().run(macropy.test.Tests)





########NEW FILE########
