__FILENAME__ = pythranmagic
"""
Pythran integration into IPython

* provides the %%pythran magic function to ipython
"""
#-----------------------------------------------------------------------------
# Copyright (C) 2010-2011, IPython Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import imp
from IPython.core.magic import Magics, magics_class, cell_magic

import pythran

@magics_class
class PythranMagics(Magics):

    def __init__(self, shell):
        super(PythranMagics,self).__init__(shell)
        self._reloads = {}

    def _import_all(self, module):
        for k,v in module.__dict__.items():
            if not k.startswith('__'):
                self.shell.push({k:v})

    @cell_magic
    def pythran(self, line, cell):
        """
        Compile and import everything from a Pythran code cell

        %%pythran
        #pythran export foo(int)
        def foo(x):
            return x + x
        """
        module_name = "pythranized"
        module_path  = pythran.compile_pythrancode(module_name, cell)
        module = imp.load_dynamic(module_name, module_path)
        self._import_all(module)



def load_ipython_extension(ipython):
    """Load the extension in IPython."""
    ipython.register_magics(PythranMagics)

########NEW FILE########
__FILENAME__ = aliases
"""
Aliases gather aliasing informations
"""
import ast
from global_declarations import GlobalDeclarations
from pythran.intrinsic import Intrinsic
import pythran.metadata as md
from pythran.passmanager import ModuleAnalysis
from pythran.syntax import PythranSyntaxError
from pythran.tables import functions, methods, modules
from pythran.syntax import PythranSyntaxError


class Aliases(ModuleAnalysis):
    """Gather aliasing informations across nodes."""
    class Info(object):
        def __init__(self, state, aliases):
            self.state = state
            self.aliases = aliases

    def __init__(self):
        self.result = dict()
        self.aliases = dict()
        super(Aliases, self).__init__(GlobalDeclarations)

    def expand_unknown(self, node):
        # should include built-ins too?
        unkowns = {None}.union(self.global_declarations.values())
        return unkowns.union(node.args)

    @staticmethod
    def access_path(node):
        def rec(w, n):
            if isinstance(n, ast.Name):
                return w.get(n.id, n.id)
            elif isinstance(n, ast.Attribute):
                return rec(w, n.value)[n.attr]
            elif isinstance(n, ast.FunctionDef):
                return node.name
            else:
                return node
        return rec(modules, node)

    # aliasing created by expressions
    def add(self, node, values=None):
        if not values:  # no given target for the alias
            if isinstance(node, Intrinsic):
                values = {node}  # an Intrinsic always aliases to itself
            else:
                values = set()  # otherwise aliases to nothing
        assert isinstance(values, set)
        self.result[node] = Aliases.Info(self.aliases.copy(), values)
        return values

    def visit_BoolOp(self, node):
        return self.add(node, set.union(*map(self.visit, node.values)))

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        return self.add(node)

    visit_BinOp = visit_UnaryOp
    visit_Compare = visit_UnaryOp

    def visit_IfExp(self, node):
        self.visit(node.test)
        rec = map(self.visit, [node.body, node.orelse])
        return self.add(node, set.union(*rec))

    def visit_Dict(self, node):
        self.generic_visit(node)
        return self.add(node)  # not very accurate

    def visit_Set(self, node):
        self.generic_visit(node)
        return self.add(node)  # not very accurate

    def call_return_alias(self, node):
        func = node.func
        aliases = set()
        if isinstance(func, ast.Attribute):
            _, signature = methods.get(func.attr,
                                       functions.get(func.attr,
                                                     [(None, None)])[0])
            if signature and signature.return_alias:
                aliases = signature.return_alias(node)
        elif isinstance(func, ast.Name):
            func_aliases = self.result[func].aliases
            for func_alias in func_aliases:
                signature = None
                if isinstance(func_alias, ast.FunctionDef):
                    _, signature = functions.get(
                        func_alias.name,
                        [(None, None)])[0]
                    if signature and signature.return_alias:
                        aliases.update(signature.return_alias(node))
                elif hasattr(func_alias, 'return_alias'):
                    aliases.update(func_alias.return_alias(node))
                else:
                    pass  # better thing to do ?
        [self.add(a) for a in aliases if a not in self.result]
        return aliases or self.expand_unknown(node)

    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        # special handler for bind functions
        if isinstance(f, ast.Attribute) and f.attr == "partial":
            return self.add(node, {node})
        else:
            return_alias = self.call_return_alias(node)
            # expand collected aliases
            all_aliases = set()
            for value in return_alias:
                if value is None:
                    all_aliases.add(None)
                elif value in self.result:
                    all_aliases.update(self.result[value].aliases)
                else:
                    try:
                        ap = Aliases.access_path(value)
                        all_aliases.update(self.aliases.get(ap, ()))
                    except NotImplementedError:
                        # should we do something better here?
                        all_aliases.add(value)
                        pass
            return_alias = all_aliases
            return self.add(node, return_alias)

    visit_Num = visit_UnaryOp
    visit_Str = visit_UnaryOp

    def visit_Attribute(self, node):
        return self.add(node, {Aliases.access_path(node)})

    def visit_Subscript(self, node):
        self.generic_visit(node)
        # could be enhanced through better handling of containers
        return self.add(node)

    def visit_Name(self, node):
        if node.id not in self.aliases:
            err = ("identifier {0} unknown, either because "
                   "it is an unsupported intrinsic, "
                   "the input code is faulty, "
                   "or... pythran is buggy.")
            raise PythranSyntaxError(err.format(node.id), node)
        return self.add(node, self.aliases[node.id].copy())

    def visit_List(self, node):
        self.generic_visit(node)
        return self.add(node)  # not very accurate

    def visit_Tuple(self, node):
        self.generic_visit(node)
        return self.add(node)  # not very accurate

    def visit_comprehension(self, node):
        self.aliases[node.target.id] = {node.target}
        self.generic_visit(node)

    def visit_ListComp(self, node):
        map(self.visit_comprehension, node.generators)
        self.visit(node.elt)
        return self.add(node)

    visit_SetComp = visit_ListComp

    visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node):
        map(self.visit_comprehension, node.generators)
        self.visit(node.key)
        self.visit(node.value)
        return self.add(node)

    # aliasing created by statements

    def visit_FunctionDef(self, node):
        self.aliases = dict()
        for module in modules:
            self.aliases.update((v, {v})
                                for k, v in modules[module].iteritems())
        self.aliases.update((f.name, {f})
                            for f in self.global_declarations.itervalues())
        self.aliases.update((arg.id, {arg})
                            for arg in node.args.args)
        self.generic_visit(node)

    def visit_Assign(self, node):
        md.visit(self, node)
        value_aliases = self.visit(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.aliases[t.id] = value_aliases or {t}
                for alias in list(value_aliases):
                    if isinstance(alias, ast.Name):
                        self.aliases[alias.id].add(t)
            else:
                self.visit(t)

    def visit_For(self, node):
        self.aliases[node.target.id] = {node.target}
        # Error may come from false branch evaluation so we have to try again
        try:
            self.generic_visit(node)
        except PythranSyntaxError:
            self.generic_visit(node)

    def visit_While(self, node):
        # Error may come from false branch evaluation so we have to try again
        try:
            self.generic_visit(node)
        except PythranSyntaxError:
            self.generic_visit(node)

    def visit_If(self, node):
        md.visit(self, node)
        self.visit(node.test)
        false_aliases = {k: v.copy() for k, v in self.aliases.iteritems()}
        try:  # first try the true branch
            map(self.visit, node.body)
            true_aliases, self.aliases = self.aliases, false_aliases
        except PythranSyntaxError:  # it failed, try the false branch
            map(self.visit, node.orelse)
            raise  # but still throw the exception, maybe we are in a For
        try:  # then try the false branch
            map(self.visit, node.orelse)
        except PythranSyntaxError:  # it failed
            # we still get some info from the true branch, validate them
            self.aliases = true_aliases
            raise  # and let other visit_ handle the issue
        for k, v in true_aliases.iteritems():
            if k in self.aliases:
                self.aliases[k].update(v)
            else:
                assert isinstance(v, set)
                self.aliases[k] = v

    def visit_ExceptHandler(self, node):
        if node.name:
            self.aliases[node.name.id] = {node.name}
        self.generic_visit(node)


class StrictAliases(Aliases):
    """
    Gather aliasing informations across nodes,
    without adding unsure aliases.
    """
    def expand_unknown(self, node):
        return {}

########NEW FILE########
__FILENAME__ = ancestors
"""
Ancestors computes the ancestors of each node
"""
import ast
from pythran.passmanager import ModuleAnalysis


class Ancestors(ModuleAnalysis):
    '''
    Associate each node with the list of its ancestors

    Based on the tree view of the AST: each node has the Module as parent.
    The result of this analysis is a dictionary with nodes as key,
    and list of nodes as values.
    '''

    def __init__(self):
        self.result = dict()
        self.current = list()
        super(Ancestors, self).__init__()

    def generic_visit(self, node):
        self.result[node] = list(self.current)
        self.current.append(node)
        super(Ancestors, self).generic_visit(node)
        self.current.pop()

########NEW FILE########
__FILENAME__ = argument_effects
"""
ArgumentEffects computes write effect on arguments
"""
import ast
import networkx as nx
from aliases import Aliases
from global_declarations import GlobalDeclarations
import pythran.intrinsic as intrinsic
from pythran.passmanager import ModuleAnalysis
from pythran.tables import modules


class ArgumentEffects(ModuleAnalysis):
    '''Gathers inter-procedural effects on function arguments.'''
    class FunctionEffects(object):
        def __init__(self, node):
            self.func = node
            if isinstance(node, ast.FunctionDef):
                self.update_effects = [False] * len(node.args.args)
            elif isinstance(node, intrinsic.Intrinsic):
                self.update_effects = [isinstance(x, intrinsic.UpdateEffect)
                                       for x in node.argument_effects]
            elif isinstance(node, ast.alias):
                self.update_effects = []
            elif isinstance(node, intrinsic.Class):
                self.update_effects = []
            else:
                raise NotImplementedError

    class ConstructorEffects(object):
        def __init__(self, node):
            self.func = node
            self.update_effects = [False]

    def __init__(self):
        self.result = nx.DiGraph()
        self.node_to_functioneffect = dict()
        super(ArgumentEffects, self).__init__(Aliases, GlobalDeclarations)

    def prepare(self, node, ctx):
        super(ArgumentEffects, self).prepare(node, ctx)
        for n in self.global_declarations.itervalues():
            fe = ArgumentEffects.FunctionEffects(n)
            self.node_to_functioneffect[n] = fe
            self.result.add_node(fe)
        for m in modules:
            for name, intrinsic in modules[m].iteritems():
                fe = ArgumentEffects.FunctionEffects(intrinsic)
                self.node_to_functioneffect[intrinsic] = fe
                self.result.add_node(fe)
        self.all_functions = [fe.func for fe in self.result]

    def run(self, node, ctx):
        super(ArgumentEffects, self).run(node, ctx)
        keep_going = True  # very naive approach
        while keep_going:
            keep_going = False
            for function in self.result:
                for ue in enumerate(function.update_effects):
                    update_effect_index, update_effect = ue
                    if not update_effect:
                        continue
                    for pred in self.result.predecessors(function):
                        edge = self.result.edge[pred][function]
                        for fp in enumerate(edge["formal_parameters"]):
                            i, formal_parameter_index = fp
                            # propagate the impurity backward if needed.
                            # Afterward we may need another graph iteration
                            ith_effectiv = edge["effective_parameters"][i]
                            if (formal_parameter_index == update_effect_index
                                    and not pred.update_effects[ith_effectiv]):
                                pred.update_effects[ith_effectiv] = True
                                keep_going = True

        return {f.func: f.update_effects for f in self.result}

    def argument_index(self, node):
        while isinstance(node, ast.Subscript):
            node = node.value
        for node_alias in self.aliases[node].aliases:
            try:
                return self.current_function.func.args.args.index(node_alias)
            except ValueError:
                pass
        return -1

    def visit_FunctionDef(self, node):
        self.current_function = self.node_to_functioneffect[node]
        assert self.current_function in self.result
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        n = self.argument_index(node.target)
        if n >= 0:
            self.current_function.update_effects[n] = True
        self.generic_visit(node)

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Subscript):
                n = self.argument_index(t)
                if n >= 0:
                    self.current_function.update_effects[n] = True
        self.generic_visit(node)

    def visit_Call(self, node):
        for i, arg in enumerate(node.args):
            n = self.argument_index(arg)
            if n >= 0:
                func_aliases = self.aliases[node].state[
                    Aliases.access_path(node.func)]

                # expand argument if any
                func_aliases = reduce(
                    lambda x, y: x + (
                        self.all_functions
                        if (isinstance(y, ast.Name)
                            and self.argument_index(y) >= 0)
                        else [y]),
                    func_aliases,
                    list())

                for func_alias in func_aliases:
                    # special hook for binded functions
                    if isinstance(func_alias, ast.Call):
                        bound_name = func_alias.args[0].id
                        func_alias = self.global_declarations[bound_name]
                    func_alias = self.node_to_functioneffect[func_alias]
                    predecessors = self.result.predecessors(func_alias)
                    if self.current_function not in predecessors:
                        self.result.add_edge(
                            self.current_function,
                            func_alias,
                            effective_parameters=[],
                            formal_parameters=[])
                    edge = self.result.edge[self.current_function][func_alias]
                    edge["effective_parameters"].append(n)
                    edge["formal_parameters"].append(i)
        self.generic_visit(node)

########NEW FILE########
__FILENAME__ = argument_read_once
"""
ArgumentReadOnce counts the usages of each argument of each function
"""
import ast
from aliases import Aliases
from global_declarations import GlobalDeclarations
import networkx as nx
import pythran.intrinsic as intrinsic
from pythran.passmanager import ModuleAnalysis
from pythran.tables import modules


class ArgumentReadOnce(ModuleAnalysis):
    '''Counts the usages of each argument of each function'''

    class FunctionEffects(object):
        def __init__(self, node):
            self.func = node
            self.dependencies = lambda ctx: 0
            if isinstance(node, ast.FunctionDef):
                self.read_effects = [-1] * len(node.args.args)
            elif isinstance(node, intrinsic.Intrinsic):
                self.read_effects = [
                    1 if isinstance(x, intrinsic.ReadOnceEffect)
                    else 2 for x in node.argument_effects]
            elif isinstance(node, ast.alias):
                self.read_effects = []
            elif isinstance(node, intrinsic.Class):
                self.read_effects = []
            else:
                raise NotImplementedError

    class ConstructorEffects(object):
        def __init__(self, node):
            self.func = node
            self.dependencies = lambda ctx: 0
            self.read_effects = [0]

    class Context(object):
        def __init__(self, function, index, path, global_dependencies):
            self.function = function
            self.index = index
            self.path = path
            self.global_dependencies = global_dependencies

    def __init__(self):
        self.result = set()
        self.node_to_functioneffect = dict()
        super(ArgumentReadOnce, self).__init__(Aliases, GlobalDeclarations)

    def prepare(self, node, ctx):
        super(ArgumentReadOnce, self).prepare(node, ctx)
        for n in self.global_declarations.itervalues():
            fe = ArgumentReadOnce.FunctionEffects(n)
            self.node_to_functioneffect[n] = fe
            self.result.add(fe)
        for m in modules:
            for name, intrinsic in modules[m].iteritems():
                fe = ArgumentReadOnce.FunctionEffects(intrinsic)
                self.node_to_functioneffect[intrinsic] = fe
                self.result.add(fe)
        self.all_functions = [fe.func for fe in self.result]

    def run(self, node, ctx):
        ModuleAnalysis.run(self, node, ctx)
        for fun in self.result:
            for i in xrange(len(fun.read_effects)):
                self.recursive_weight(fun, i, set())
        return {f.func: f.read_effects for f in self.result}

    def recursive_weight(self, function, index, predecessors):
        #TODO : Find out why it happens in some cases
        if len(function.read_effects) <= index:
            return 0
        if function.read_effects[index] == -1:
            # In case of recursive/cyclic calls
            cycle = function in predecessors
            predecessors.add(function)
            if cycle:
                function.read_effects[index] = 2 * function.dependencies(
                    ArgumentReadOnce.Context(function, index,
                                             predecessors, False))
            else:
                function.read_effects[index] = function.dependencies(
                    ArgumentReadOnce.Context(function, index,
                                             predecessors, True))
        return function.read_effects[index]

    def argument_index(self, node):
        while isinstance(node, ast.Subscript):
            node = node.value
        if node in self.aliases:
            for n_alias in self.aliases[node].aliases:
                try:
                    return self.current_function.func.args.args.index(n_alias)
                except ValueError:
                    pass
        return -1

    def local_effect(self, node, effect):
        index = self.argument_index(node)
        return lambda ctx: effect if index == ctx.index else 0

    def generic_visit(self, node):
        lambdas = map(self.visit, ast.iter_child_nodes(node))
        if lambdas:
            return lambda ctx: sum(l(ctx) for l in lambdas)
        else:
            return lambda ctx: 0

    def visit_FunctionDef(self, node):
        self.current_function = self.node_to_functioneffect[node]
        assert self.current_function in self.result
        self.current_function.dependencies = self.generic_visit(node)

    def visit_Return(self, node):
        dep = self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            local = self.local_effect(node.value, 2)
            return lambda ctx: dep(ctx) + local(ctx)
        else:
            return dep

    def visit_Assign(self, node):
        dep = self.generic_visit(node)
        local = [self.local_effect(t, 2) for t in node.targets
                 if isinstance(t, ast.Subscript)]
        return lambda ctx: dep(ctx) + sum(l(ctx) for l in local)

    def visit_AugAssign(self, node):
        dep = self.generic_visit(node)
        local = self.local_effect(node.target, 2)
        return lambda ctx: dep(ctx) + local(ctx)

    def visit_For(self, node):
        iter_local = self.local_effect(node.iter, 1)
        iter_deps = self.visit(node.iter)
        body_deps = map(self.visit, node.body)
        else_deps = map(self.visit, node.orelse)
        return lambda ctx: iter_local(ctx) + iter_deps(ctx) + 2 * sum(
            l(ctx) for l in body_deps) + sum(l(ctx) for l in else_deps)

    def visit_While(self, node):
        test_deps = self.visit(node.test)
        body_deps = map(self.visit, node.body)
        else_deps = map(self.visit, node.orelse)
        return lambda ctx: test_deps(ctx) + 2 * sum(
            l(ctx) for l in body_deps) + sum(l(ctx) for l in else_deps)

    def visit_If(self, node):
        test_deps = self.visit(node.test)
        body_deps = map(self.visit, node.body)
        else_deps = map(self.visit, node.orelse)
        return lambda ctx: test_deps(ctx) + max(sum(
            l(ctx) for l in body_deps), sum(l(ctx) for l in else_deps))

    def visit_Call(self, node):
        l0 = self.generic_visit(node)
        index_corres = dict()
        func = None
        for i, arg in enumerate(node.args):
            n = self.argument_index(arg)
            if n >= 0:
                func_aliases = self.aliases[node].state[
                    Aliases.access_path(node.func)]

                # expand argument if any
                func_aliases = reduce(
                    lambda x, y: x + (
                        self.all_functions
                        if (isinstance(y, ast.Name)
                            and self.argument_index(y) >= 0)
                        else [y]),
                    func_aliases,
                    list())

                for func_alias in func_aliases:
                    # special hook for binded functions
                    if isinstance(func_alias, ast.Call):
                        bound_name = func_alias.args[0].id
                        func_alias = self.global_declarations[bound_name]
                    func_alias = self.node_to_functioneffect[func_alias]
                    index_corres[n] = i
                    func = func_alias

        return lambda ctx: l0(ctx) + self.recursive_weight(
            func, index_corres[ctx.index], ctx.path) if (
            (ctx.index in index_corres) and ctx.global_dependencies) else 0

    def visit_Subscript(self, node):
        dep = self.generic_visit(node)
        local = self.local_effect(node.value, 2)
        return lambda ctx: dep(ctx) + local(ctx)

    def visit_comprehension(self, node):
        dep = self.generic_visit(node)
        local = self.local_effect(node.iter, 1)
        return lambda ctx: dep(ctx) + local(ctx)

########NEW FILE########
__FILENAME__ = bounded_expressions
"""
BoundedExpressions gathers temporary objects
"""
from pythran.passmanager import ModuleAnalysis
import ast


class BoundedExpressions(ModuleAnalysis):
    '''Gathers all nodes that are bound to an identifier.'''

    Boundable = (
        ast.Name,
        ast.Subscript,
        ast.BoolOp,
        )

    def __init__(self):
        self.result = set()
        super(BoundedExpressions, self).__init__()

    def isboundable(self, node):
        return any(isinstance(node, t) for t in BoundedExpressions.Boundable)

    def visit_Assign(self, node):
        self.result.add(node.value)
        if self.isboundable(node.value):
            self.result.add(node.value)
        self.generic_visit(node)

    def visit_Call(self, node):
        for n in node.args:
            if self.isboundable(n):
                self.result.add(n)
        self.generic_visit(node)

    def visit_Return(self, node):
        node.value and self.visit(node.value)
        if node.value:
            self.result.add(node.value)
            if self.isboundable(node.value):
                self.result.add(node.value)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        if node in self.result:
            self.result.update(node.values)
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if node in self.result:
            self.result.add(node.slice)

########NEW FILE########
__FILENAME__ = cfg
"""
Computes the Control Flow Graph of a function
"""
import ast
import networkx as nx
from pythran.passmanager import FunctionAnalysis


class CFG(FunctionAnalysis):
    """
    Computes the Control Flow Graph of a function

    The processing of a node yields a pair containing
    * the OUT nodes, to be linked with the IN nodes of the successor
    * the RAISE nodes, nodes that stop the control flow (exception/break/...)
    """
    def __init__(self):
        self.result = nx.DiGraph()
        super(CFG, self).__init__()

    def visit_FunctionDef(self, node):
        # the function itself is the entry point
        self.result.add_node(node)
        currs = (node,)
        for n in node.body:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, _ = self.visit(n)
        # add an edge to None for nodes that end the control flow
        # without a return
        self.result.add_node(None)
        for curr in currs:
            self.result.add_edge(curr, None)
        #nx.draw_graphviz(self.result)
        #nx.write_dot(self.result, node.name + '.dot')

    def visit_Pass(self, node):
        """OUT = node, RAISES = ()"""
        return (node,), ()

    # All these nodes have the same behavior as pass
    visit_Assign = visit_AugAssign = visit_Import = visit_Pass
    visit_Expr = visit_Print = visit_ImportFrom = visit_Pass
    visit_Yield = visit_Delete = visit_Pass

    def visit_Return(self, node):
        """OUT = (), RAISES = ()"""
        return (), ()

    def visit_For(self, node):
        """
        OUT = (node,) + last body statements
        RAISES = body's that are not break or continue
        """
        currs = (node,)
        break_currs = (node,)
        raises = ()
        # handle body
        for n in node.body:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, nraises = self.visit(n)
            for nraise in nraises:
                if type(nraise) is ast.Break:
                    break_currs += (nraise,)
                elif type(nraise) is ast.Continue:
                    self.result.add_edge(nraise, node)
                else:
                    raises += (nraise,)
        # add the backward loop
        for curr in currs:
            self.result.add_edge(curr, node)
        # the else statement if needed
        if node.orelse:
            for n in node.orelse:
                self.result.add_node(n)
                for curr in currs:
                    self.result.add_edge(curr, n)
                currs, nraises = self.visit(n)
        return break_currs + currs, raises

    visit_While = visit_For

    def visit_If(self, node):
        """
        OUT = true branch U false branch
        RAISES = true branch U false branch
        """
        currs = (node,)
        raises = ()
        # true branch
        for n in node.body:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, nraises = self.visit(n)
            raises += nraises
        tcurrs = currs
        # false branch
        currs = (node,)
        for n in node.orelse:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, nraises = self.visit(n)
            raises += nraises
        return tcurrs + currs, raises

    def visit_Raise(self, node):
        """OUT = (), RAISES = (node)"""
        return (), (node,)

    visit_Break = visit_Continue = visit_Raise

    def visit_Assert(self, node):
        """OUT = RAISES = (node)"""
        return (node,), (node,)

    def visit_TryExcept(self, node):
        """
        OUT = body's U handler's
        RAISES = handler's
        this equation is not has good has it could be...
        but we need type information to be more accurate
        """
        currs = (node,)
        raises = ()
        for handler in node.handlers:
            self.result.add_node(handler)
        for n in node.body:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, nraises = self.visit(n)
            for nraise in nraises:
                if type(nraise) is ast.Raise:
                    for handler in node.handlers:
                        self.result.add_edge(nraise, handler)
                else:
                    raises += (nraise,)
        for handler in node.handlers:
            ncurrs, nraises = self.visit(handler)
            currs += ncurrs
            raises += nraises
        return currs, raises

    def visit_ExceptHandler(self, node):
        """OUT = body's, RAISES = body's"""
        currs = (node,)
        raises = ()
        for n in node.body:
            self.result.add_node(n)
            for curr in currs:
                self.result.add_edge(curr, n)
            currs, nraises = self.visit(n)
            raises += nraises
        return currs, raises

########NEW FILE########
__FILENAME__ = constant_expressions
"""
ConstantExpressions gathers constant expression
"""
import ast
from aliases import Aliases
from globals_analysis import Globals
from locals_analysis import Locals
from pure_expressions import PureExpressions
from pythran.intrinsic import Intrinsic
from pythran.passmanager import NodeAnalysis
from pythran.tables import modules


class ConstantExpressions(NodeAnalysis):
    """Identify constant expressions"""
    def __init__(self):
        self.result = set()
        super(ConstantExpressions, self).__init__(Globals, Locals,
                                                  PureExpressions, Aliases)

    def add(self, node):
        self.result.add(node)
        return True

    def visit_BoolOp(self, node):
        return all(map(self.visit, node.values)) and self.add(node)

    def visit_BinOp(self, node):
        rec = all(map(self.visit, (node.left, node.right)))
        return rec and self.add(node)

    def visit_UnaryOp(self, node):
        return self.visit(node.operand) and self.add(node)

    def visit_IfExp(self, node):
        rec = all(map(self.visit, (node.test, node.body, node.orelse)))
        return rec and self.add(node)

    def visit_Compare(self, node):
        rec = all(map(self.visit, [node.left] + node.comparators))
        return rec and self.add(node)

    def visit_Call(self, node):
        rec = all(map(self.visit, node.args + [node.func]))
        return rec and self.add(node)

    visit_Num = add
    visit_Str = add

    def visit_Subscript(self, node):
        rec = all(map(self.visit, (node.value, node.slice)))
        return rec and self.add(node)

    def visit_Name(self, node):
        if node in self.aliases:
            is_function = lambda x: (isinstance(x, Intrinsic) or
                                     isinstance(x, ast.FunctionDef) or
                                     isinstance(x, ast.alias))
            pure_fun = all(alias in self.pure_expressions and
                           is_function(alias)
                           for alias in self.aliases[node].aliases)
            return pure_fun and self.add(node)
        else:
            return False

    def visit_Attribute(self, node):
        def rec(w, n):
            if isinstance(n, ast.Name):
                return w[n.id]
            elif isinstance(n, ast.Attribute):
                return rec(w, n.value)[n.attr]
        return rec(modules, node).isconst() and self.add(node)

    def visit_Dict(self, node):
        rec = all(map(self.visit, node.keys + node.values))
        return rec and self.add(node)

    def visit_List(self, node):
        return all(map(self.visit, node.elts)) and self.add(node)

    visit_Tuple = visit_List
    visit_Set = visit_List

    def visit_Slice(self, node):
        # ultra-conservative, indeed
        return False

    def visit_Index(self, node):
        return self.visit(node.value) and self.add(node)

########NEW FILE########
__FILENAME__ = dependencies
"""
Dependencies lists the functions and types required by a function
"""
import ast
import math
from pythran.passmanager import ModuleAnalysis
from pythran.tables import modules


class Dependencies(ModuleAnalysis):
    def __init__(self):
        self.result = set()
        super(Dependencies, self).__init__()

    def visit_List(self, node):
        self.result.add(('__builtin__', 'list'))
        self.generic_visit(node)

    def visit_Tuple(self, node):
        self.result.add(('__builtin__', 'tuple'))
        self.generic_visit(node)

    def visit_Set(self, node):
        self.result.add(('__builtin__', 'set'))
        self.generic_visit(node)

    def visit_Dict(self, node):
        self.result.add(('__builtin__', 'dict'))
        self.generic_visit(node)

    def visit_Str(self, node):
        self.result.add(('__builtin__', 'str'))
        self.generic_visit(node)

    def visit_Pow(self, node):
        self.result.add(('__builtin__', 'pow'))
        self.generic_visit(node)

    def visit_In(self, node):
        self.result.add(('__builtin__', 'in'))
        self.generic_visit(node)

    visit_NotIn = visit_In

    def visit_Is(self, node):
        self.result.add(('__builtin__', 'id'))
        self.generic_visit(node)

    visit_IsNot = visit_Is

    def visit_Print(self, node):
        self.result.add(('__builtin__', 'print'))
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.result.add(('__builtin__', 'assert'))
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.result.add(('types', 'generator'))
        self.generic_visit(node)

    def visit_Mod(self, node):
        self.result.add(('operator_', 'mod'))

    def visit_FloorDiv(self, node):
        self.result.add(('operator_', 'floordiv'))

    def visit_Num(self, node):
        if type(node.n) is complex:
            self.result.add(('types', 'complex'))
        elif type(node.n) is long:
            self.result.add(('types', 'long'))
        elif math.isnan(node.n):
            self.result.add(('numpy', 'nan'))
        elif math.isinf(node.n):
            self.result.add(('numpy', 'inf'))

        self.generic_visit(node)

    def visit_Attribute(self, node):
        def rec(w, n):
            if isinstance(n, ast.Name):
                return (n.id,)
            elif isinstance(n, ast.Attribute):
                id = rec(w, n.value)
                if len(id) > 1:
                    plast, last = id[-2:]
                    if plast == '__builtin__' and last.startswith('__'):
                        id = id[:-2] + id[-1:]
                return id + (n.attr,)
        attr = rec(modules, node)

        attr and self.result.add(attr)

########NEW FILE########
__FILENAME__ = globals_analysis
"""
Globals computes the value of globals()
"""
import ast
from global_declarations import GlobalDeclarations
from pythran.passmanager import ModuleAnalysis
from pythran.tables import modules


class Globals(ModuleAnalysis):
    def __init__(self):
        self.result = set()
        super(Globals, self).__init__(GlobalDeclarations)

    def visit(self, node):
        pass  # everything is done by the run method

    def run(self, node, ctx):
        super(Globals, self).run(node, ctx)
        return set(self.global_declarations.keys()
                   + [i for i in modules if i.startswith('__')])

########NEW FILE########
__FILENAME__ = global_declarations
"""
GlobalDeclarations gathers top-level declarations
"""
import ast
from pythran.passmanager import ModuleAnalysis


class GlobalDeclarations(ModuleAnalysis):
    """Generates a function name -> function node binding"""
    def __init__(self):
        self.result = dict()
        super(GlobalDeclarations, self).__init__()

    def visit_Import(self, node):
        self.result.update((a.name, a) for a in node.names)

    def visit_ImportFrom(self, node):
        self.result.update((a.asname or a.name, a) for a in node.names)

    def visit_FunctionDef(self, node):
        self.result[node.name] = node
        # no generic visit here, so no diving into function body

########NEW FILE########
__FILENAME__ = global_effects
"""
GlobalEffects computes function effect on global state
"""
import ast
import networkx as nx
from aliases import Aliases
from global_declarations import GlobalDeclarations
from pythran.passmanager import ModuleAnalysis
import pythran.intrinsic as intrinsic
from pythran.tables import modules


class GlobalEffects(ModuleAnalysis):
    """Add a flag on each function that updates a global variable."""

    class FunctionEffect(object):
        def __init__(self, node):
            self.func = node
            if isinstance(node, ast.FunctionDef):
                self.global_effect = False
            elif isinstance(node, intrinsic.Intrinsic):
                self.global_effect = node.global_effects
            elif isinstance(node, ast.alias):
                self.global_effect = False
            elif isinstance(node, str):
                self.global_effect = False
            elif isinstance(node, intrinsic.Class):
                self.global_effect = False
            else:
                print type(node), node
                raise NotImplementedError

    def __init__(self):
        self.result = nx.DiGraph()
        self.node_to_functioneffect = dict()
        super(GlobalEffects, self).__init__(Aliases, GlobalDeclarations)

    def prepare(self, node, ctx):
        super(GlobalEffects, self).prepare(node, ctx)

        def register_node(n):
            fe = GlobalEffects.FunctionEffect(n)
            self.node_to_functioneffect[n] = fe
            self.result.add_node(fe)

        map(register_node, self.global_declarations.itervalues())
        for m in modules:
            map(register_node, modules[m].itervalues())
        self.all_functions = [fe.func for fe in self.result]

    def run(self, node, ctx):
        super(GlobalEffects, self).run(node, ctx)
        keep_going = True
        while keep_going:
            keep_going = False
            for function in self.result:
                if function.global_effect:
                    for pred in self.result.predecessors(function):
                        if not pred.global_effect:
                            keep_going = pred.global_effect = True
        return {f.func for f in self.result if f.global_effect}

    def visit_FunctionDef(self, node):
        self.current_function = self.node_to_functioneffect[node]
        assert self.current_function in self.result
        self.generic_visit(node)

    def visit_Print(self, node):
        self.current_function.global_effect = True

    def visit_Call(self, node):
        # try to get all aliases of the function, if possible
        # else use [] as a fallback
        ap = Aliases.access_path(node.func)
        func_aliases = self.aliases[node].state.get(ap, [])
        # expand argument if any
        func_aliases = reduce(
            lambda x, y: x + (self.all_functions
                              if isinstance(y, ast.Name) else [y]),
            func_aliases,
            list())
        for func_alias in func_aliases:
            # special hook for binded functions
            if isinstance(func_alias, ast.Call):
                bound_name = func_alias.args[0].id
                func_alias = self.global_declarations[bound_name]
            func_alias = self.node_to_functioneffect[func_alias]
            self.result.add_edge(self.current_function, func_alias)
        self.generic_visit(node)

########NEW FILE########
__FILENAME__ = has_break
"""
HasBreak detects if a loop has a direct break
"""
from pythran.passmanager import NodeAnalysis


class HasBreak(NodeAnalysis):

    def __init__(self):
        self.result = False
        super(HasBreak, self).__init__()

    def visit_For(self, node):
        return

    def visit_Break(self, node):
        self.result = True

########NEW FILE########
__FILENAME__ = has_continue
"""
HasContinue detects if a loop has a direct continue
"""
from pythran.passmanager import NodeAnalysis


class HasContinue(NodeAnalysis):

    def __init__(self):
        self.result = False
        super(HasContinue, self).__init__()

    def visit_For(self, node):
        return

    def visit_Continue(self, node):
        self.result = True

########NEW FILE########
__FILENAME__ = identifiers
"""
Identifiers gathers all identifiers used in a node
"""
import ast
from pythran.passmanager import NodeAnalysis


class Identifiers(NodeAnalysis):
    """Gather all identifiers used throughout a node."""
    def __init__(self):
        self.result = set()
        super(Identifiers, self).__init__()

    def visit_Name(self, node):
        self.result.add(node.id)

    def visit_FunctionDef(self, node):
        self.result.add(node.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.generic_visit(node)
        self.result.add(node.module)

    def visit_alias(self, node):
        self.result.add(node.name)
        if node.asname:
            self.result.add(node.asname)

########NEW FILE########
__FILENAME__ = imported_ids
"""
ImportedIds gathers identifiers imported by a node
"""
import ast
from globals_analysis import Globals
from locals_analysis import Locals
import pythran.metadata as md
from pythran.passmanager import NodeAnalysis


class ImportedIds(NodeAnalysis):
    """Gather ids referenced by a node and not declared locally"""
    def __init__(self):
        self.result = set()
        self.current_locals = set()
        self.is_list = False
        self.in_augassign = False
        super(ImportedIds, self).__init__(Globals, Locals)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store) and not self.in_augassign:
            self.current_locals.add(node.id)
        elif (node.id not in self.visible_globals
                and node.id not in self.current_locals):
            self.result.add(node.id)

    def visit_FunctionDef(self, node):
        self.current_locals.add(node.name)
        current_locals = self.current_locals.copy()
        self.current_locals.update(arg.id for arg in node.args.args)
        map(self.visit, node.body)
        self.current_locals = current_locals

    def visit_AnyComp(self, node):
        current_locals = self.current_locals.copy()
        map(self.visit, node.generators)
        self.visit(node.elt)
        self.current_locals = current_locals

    visit_ListComp = visit_AnyComp
    visit_SetComp = visit_AnyComp
    visit_DictComp = visit_AnyComp
    visit_GeneratorExp = visit_AnyComp

    def visit_Assign(self, node):
        #order matter as an assignation
        #is evaluted before being assigned
        md.visit(self, node)
        self.visit(node.value)
        map(self.visit, node.targets)

    def visit_AugAssign(self, node):
        self.in_augassign = True
        self.generic_visit(node)
        self.in_augassign = False

    def visit_Lambda(self, node):
        current_locals = self.current_locals.copy()
        self.current_locals.update(arg.id for arg in node.args.args)
        self.visit(node.body)
        self.current_locals = current_locals

    def visit_Import(self, node):
        self.current_locals.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node):
        self.current_locals.update(alias.name for alias in node.names)

    def visit_Attribute(self, node):
        pass

    def prepare(self, node, ctx):
        super(ImportedIds, self).prepare(node, ctx)
        if self.is_list:  # so that this pass can be called on list
            node = node.body[0]
        self.visible_globals = set(self.globals) - self.locals[node]

    def run(self, node, ctx):
        if isinstance(node, list):  # so that this pass can be called on list
            self.is_list = True
            node = ast.If(ast.Num(1), node, [])
        return super(ImportedIds, self).run(node, ctx)

########NEW FILE########
__FILENAME__ = lazyness_analysis
"""
LazynessAnalysis returns number of time a name is use.
"""
import ast
from aliases import Aliases
from argument_effects import ArgumentEffects
from identifiers import Identifiers
from pure_expressions import PureExpressions
import pythran.metadata as md
import pythran.openmp as openmp
from pythran.passmanager import FunctionAnalysis
from pythran.syntax import PythranSyntaxError


class LazynessAnalysis(FunctionAnalysis):
    """
    Returns number of time a name is used. +inf if it is use in a
    loop, if a variable used to compute it is modify before
    its last use or if it is use in a function call (as it is not an
    interprocedural analysis)
    >>> import ast, passmanager, backend
    >>> code = "def foo(): c = 1; a = c + 2; c = 2; b = c + c + a; return b"
    >>> node = ast.parse(code)
    >>> pm = passmanager.PassManager("test")
    >>> res = pm.gather(LazynessAnalysis, node)
    >>> res['a'], res['b'], res['c']
    (inf, 1, 2)
    """
    INF = float('inf')

    def __init__(self):
        # map variable with maximum count of use in the programm
        self.result = dict()
        # map variable with current count of use
        self.name_count = dict()
        # map variable to variables needed to compute it
        self.use = dict()
        # gather variables which can't be compute later. (variables used
        # to compute it have changed
        self.dead = set()
        # prevent any form of Forward Substitution for variables used in loops
        self.in_loop = False
        # prevent any form of Forward Substitution at omp frontier
        self.in_omp = set()
        super(LazynessAnalysis, self).__init__(ArgumentEffects, Aliases,
                                               PureExpressions)

    def modify(self, name, loc):
        # if we modify a variable, all variables that needed it
        # to be compute are dead and its aliases too
        dead_vars = [var for var, deps in self.use.iteritems() if name in deps]
        self.dead.update(dead_vars)
        for var in dead_vars:
            dead_aliases = [alias.id for alias in self.aliases[loc].state[var]
                            if isinstance(alias, ast.Name)]
            self.dead.update(dead_aliases)

    def assign_to(self, node, from_, loc):
        # a reassigned variable is not dead anymore
        if node.id in self.dead:
            self.dead.remove(node.id)
        # we keep the bigger possible number of use
        self.result[node.id] = max(self.result.get(node.id, 0),
                                   self.name_count.get(node.id, 0))
        # assign variable don't come from before omp pragma anymore
        self.in_omp.discard(node.id)
        # note this variable as modified
        self.modify(node.id, loc)
        # prepare a new variable count
        self.name_count[node.id] = 0
        self.use[node.id] = set(from_)

    def visit(self, node):
        old_omp = self.in_omp
        omp_nodes = md.get(node, openmp.OMPDirective)
        if omp_nodes:
            self.in_omp = set(self.name_count.keys())
        super(LazynessAnalysis, self).visit(node)
        if omp_nodes:
            new_nodes = set(self.name_count).difference(self.in_omp)
            self.dead.update(new_nodes)
        self.in_omp = old_omp

    def visit_FunctionDef(self, node):
        self.ids = self.passmanager.gather(Identifiers, node, self.ctx)
        self.generic_visit(node)

    def visit_Assign(self, node):
        md.visit(self, node)
        self.visit(node.value)
        ids = self.passmanager.gather(Identifiers, node.value, self.ctx)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assign_to(target, ids, node.value)
                if node.value not in self.pure_expressions:
                    self.result[target.id] = LazynessAnalysis.INF
            elif isinstance(target, ast.Subscript):
                # if we modify just a part of a variable, it can't be lazy
                var_name = target.value
                while isinstance(var_name, ast.Subscript):
                    self.visit(var_name.slice)
                    var_name = var_name.value
                # variable is modified so other variables that use it dies
                self.modify(var_name.id, node.value)
                # and this variable can't be lazy
                self.result[var_name.id] = LazynessAnalysis.INF
            else:
                raise PythranSyntaxError("Assign to unknown node", node)

    def visit_AugAssign(self, node):
        md.visit(self, node)
        # augassigned variable can't be lazy
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            # variable is modified so other variables that use it dies
            self.modify(node.target.id, node.value)
            # and this variable can't be lazy
            self.result[node.target.id] = LazynessAnalysis.INF
        elif isinstance(node.target, ast.Subscript):
            var_name = node.target.value
            while isinstance(var_name, ast.Subscript):
                var_name = var_name.value
            # variable is modified so other variables that use it dies
            self.modify(var_name.id, node.value)
            # and this variable can't be lazy
            self.result[var_name.id] = LazynessAnalysis.INF
        else:
            raise PythranSyntaxError("AugAssign to unknown node", node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.use:
            # we only care about variable local to the function
            is_loc_var = lambda x: isinstance(x, ast.Name) and x.id in self.ids
            alias_names = filter(is_loc_var, self.aliases[node].aliases)
            alias_names = {x.id for x in alias_names}
            alias_names.add(node.id)
            for alias in alias_names:
                if (node.id in self.dead or
                        self.in_loop or
                        node.id in self.in_omp):
                    self.result[alias] = LazynessAnalysis.INF
                elif alias in self.name_count:
                    self.name_count[alias] += 1
                else:
                    # a variable may alias to assigned value (with a = b, 'b'
                    # alias on 'a' as modifying 'a' will modify 'b' too)
                    pass
        elif isinstance(node.ctx, ast.Param):
            self.name_count[node.id] = 0
            self.use[node.id] = set()
        elif isinstance(node.ctx, ast.Store):
            # Store is only for exception
            self.name_count[node.id] = LazynessAnalysis.INF
            self.use[node.id] = set()
        else:
            # we ignore globals
            pass

    def visit_If(self, node):
        md.visit(self, node)
        self.visit(node.test)
        old_count = dict(self.name_count)
        old_dead = set(self.dead)
        old_deps = {a: set(b) for a, b in self.use.iteritems()}

        if isinstance(node.body, list):
            map(self.visit, node.body)
        else:
            self.visit(node.body)
        mid_count = self.name_count
        mid_dead = self.dead
        mid_deps = self.use

        self.name_count = old_count
        self.dead = old_dead
        self.use = old_deps
        if isinstance(node.orelse, list):
            map(self.visit, node.orelse)
        else:
            self.visit(node.orelse)

        #merge use variable
        for key in self.use:
            if key in mid_deps:
                self.use[key].update(mid_deps[key])
        for key in mid_deps:
            if key not in self.use:
                self.use[key] = set(mid_deps[key])

        #value is the worse case of both branches
        names = set(self.name_count.keys() + mid_count.keys())
        for name in names:
            val_body = mid_count.get(name, 0)
            val_else = self.name_count.get(name, 0)
            self.name_count[name] = max(val_body, val_else)

        #dead var are still dead
        self.dead.update(mid_dead)

    visit_IfExp = visit_If

    def visit_For(self, node):
        md.visit(self, node)
        ids = self.passmanager.gather(Identifiers, node.iter, self.ctx)
        for id in ids:
            # iterate value can't be lazy
            self.result[id] = LazynessAnalysis.INF
        if isinstance(node.target, ast.Name):
            self.assign_to(node.target, ids, node.iter)
            self.result[node.target.id] = LazynessAnalysis.INF
        else:
            err = "Assignation in for loop not to a Name"
            raise PythranSyntaxError(err, node)

        self.in_loop = True
        map(self.visit, node.body)
        self.in_loop = False

        map(self.visit, node.orelse)

    def visit_While(self, node):
        md.visit(self, node)
        self.visit(node.test)

        self.in_loop = True
        map(self.visit, node.body)
        self.in_loop = False

        map(self.visit, node.orelse)

    def func_args_lazyness(self, func_name, args, node):
        for fun in self.aliases[func_name].aliases:
            if isinstance(fun, ast.Call):  # call to partial functions
                self.func_args_lazyness(fun.args[0], fun.args[1:] + args, node)
            elif fun in self.argument_effects:
                # when there is an argument effet, we apply "modify" to the arg
                for i, arg in enumerate(self.argument_effects[fun]):
                    # check len of args as default is 11 args
                    if arg and len(args) > i:
                        if isinstance(args[i], ast.Name):
                            self.modify(args[i].id, node)
            elif isinstance(fun, ast.Name):
                # it may be a variable to a function. Lazyness will be compute
                # correctly thanks to aliasing
                continue
            else:
                raise PythranSyntaxError("Bad call in LazynessAnalysis", node)

    def visit_Call(self, node):
        md.visit(self, node)
        map(self.visit, node.args)
        self.func_args_lazyness(node.func, node.args, node)

    def run(self, node, ctx):
        super(LazynessAnalysis, self).run(node, ctx)

        # update result with last name_count values
        for name, val in self.name_count.iteritems():
            old_val = self.result.get(name, 0)
            self.result[name] = max(old_val, val)
        return self.result

########NEW FILE########
__FILENAME__ = literals
"""
Literals lists nodes that are only literals
"""
import ast
from pythran.passmanager import ModuleAnalysis


class Literals(ModuleAnalysis):
    """
        Store variable that save only Literals (with no construction cost)
    """
    def __init__(self):
        self.result = set()
        super(Literals, self).__init__()

    def visit_Assign(self, node):
        # list, dict, set and other are not considered as Literals as they have
        # a constructor which may be costly and they can be updated using
        # function call
        basic_type = (ast.Num, ast.Lambda, ast.Str)
        if any(isinstance(node.value, type) for type in basic_type):
            targets_id = {target.id for target in node.targets
                          if isinstance(target, ast.Name)}
            self.result.update(targets_id)

########NEW FILE########
__FILENAME__ = locals_analysis
"""
Locals computes the value of locals()
"""
import ast
import pythran.metadata as md
from pythran.passmanager import ModuleAnalysis


class Locals(ModuleAnalysis):
    """
    Statically compute the value of locals() before each statement

    Yields a dictionary binding every node to the set of variable names defined
    *before* this node.

    Following snippet illustrates its behavior:
    >>> import ast, passmanager
    >>> pm = passmanager.PassManager('test')
    >>> code = '''
    ... def b(n):
    ...     m = n + 1
    ...     def b(n):
    ...         return n + 1
    ...     return b(m)'''
    >>> tree = ast.parse(code)
    >>> l = pm.gather(Locals, tree)
    >>> l[tree.body[0].body[0]]
    set(['n'])
    >>> l[tree.body[0].body[1]]
    set(['b', 'm', 'n'])
    """

    def __init__(self):
        self.result = dict()
        self.locals = set()
        self.nesting = 0
        super(Locals, self).__init__()

    def generic_visit(self, node):
        super(Locals, self).generic_visit(node)
        if node not in self.result:
            self.result[node] = self.result[self.expr_parent]

    def store_and_visit(self, node):
        self.expr_parent = node
        self.result[node] = self.locals.copy()
        self.generic_visit(node)

    def visit_Module(self, node):
        self.expr_parent = node
        self.result[node] = self.locals
        map(self.visit, node.body)

    def visit_FunctionDef(self, node):
        # special case for nested functions
        if self.nesting:
            self.locals.add(node.name)
        self.nesting += 1
        self.expr_parent = node
        self.result[node] = self.locals.copy()
        parent_locals = self.locals.copy()
        map(self.visit, node.args.defaults)
        self.locals.update(arg.id for arg in node.args.args)
        map(self.visit, node.body)
        self.locals = parent_locals
        self.nesting -= 1

    def visit_Assign(self, node):
        self.expr_parent = node
        self.result[node] = self.locals.copy()
        md.visit(self, node)
        self.visit(node.value)
        self.locals.update(t.id for t in node.targets
                           if isinstance(t, ast.Name))
        map(self.visit, node.targets)

    def visit_For(self, node):
        self.expr_parent = node
        self.result[node] = self.locals.copy()
        md.visit(self, node)
        self.visit(node.iter)
        self.locals.add(node.target.id)
        map(self.visit, node.body)
        map(self.visit, node.orelse)

    def visit_Import(self, node):
        self.result[node] = self.locals.copy()
        self.locals.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node):
        self.result[node] = self.locals.copy()
        self.locals.update(alias.name for alias in node.names)

    def visit_ExceptHandler(self, node):
        self.expr_parent = node
        self.result[node] = self.locals.copy()
        if node.name:
            self.locals.add(node.name.id)
        node.type and self.visit(node.type)
        map(self.visit, node.body)

    # statements that do not define a new variable
    visit_Return = store_and_visit
    visit_Yield = store_and_visit
    visit_TryExcept = store_and_visit
    visit_AugAssign = store_and_visit
    visit_Print = store_and_visit
    visit_While = store_and_visit
    visit_If = store_and_visit
    visit_Raise = store_and_visit
    visit_Assert = store_and_visit
    visit_Expr = store_and_visit
    visit_Pass = store_and_visit
    visit_Break = store_and_visit
    visit_Continue = store_and_visit

########NEW FILE########
__FILENAME__ = local_declarations
"""
LocalDeclarations gathers declarations local to a node
"""
import ast
from pythran.passmanager import NodeAnalysis


class LocalDeclarations(NodeAnalysis):
    """Gathers all local symbols from a function"""
    def __init__(self):
        self.result = set()
        super(LocalDeclarations, self).__init__()

    def visit_Assign(self, node):
        for t in node.targets:
            assert isinstance(t, ast.Name) or isinstance(t, ast.Subscript)
            if isinstance(t, ast.Name):
                self.result.add(t)

    def visit_For(self, node):
        assert isinstance(node.target, ast.Name)
        self.result.add(node.target)
        map(self.visit, node.body)
        map(self.visit, node.orelse)

########NEW FILE########
__FILENAME__ = node_count
"""
NodeCount counts the number of nodes in a node
"""
import ast
from pythran.passmanager import NodeAnalysis


class NodeCount(NodeAnalysis):
    """
    Count the number of nodes included in a node

    This has nothing to do with execution time or whatever,
    its mainly use is to prevent the AST from growing too much when unrolling

    >>> import ast, passmanager, backend
    >>> node = ast.parse("if 1: return 3")
    >>> pm = passmanager.PassManager("test")
    >>> print pm.gather(NodeCount, node)
    5
    """

    def __init__(self):
        self.result = 0
        super(NodeCount, self).__init__()

    def generic_visit(self, node):
        self.result += 1
        super(NodeCount, self).generic_visit(node)

########NEW FILE########
__FILENAME__ = optimizable_comprehension
"""
OptimizableComp finds whether a comprehension can be optimized.
"""
import ast
from pythran.passmanager import NodeAnalysis
from identifiers import Identifiers


class OptimizableComprehension(NodeAnalysis):
    """Find whether a comprehension can be optimized."""
    def __init__(self):
        self.result = set()
        super(OptimizableComprehension, self).__init__(Identifiers)

    def check_comprehension(self, iters):
        targets = {gen.target.id for gen in iters}
        optimizable = True

        for it in iters:
            ids = self.passmanager.gather(Identifiers, it, self.ctx)
            optimizable &= all(((ident == it.target.id)
                                | (ident not in targets)) for ident in ids)

        return optimizable

    def visit_ListComp(self, node):
        if (self.check_comprehension(node.generators)):
            self.result.add(node)

    def visit_GeneratorExp(self, node):
        if (self.check_comprehension(node.generators)):
            self.result.add(node)

########NEW FILE########
__FILENAME__ = ordered_global_declarations
"""
OrderedGlobalDeclarations orders all global functions.
"""
import ast
from pythran.passmanager import ModuleAnalysis
from aliases import StrictAliases
from globals_analysis import Globals
from global_declarations import GlobalDeclarations


class OrderedGlobalDeclarations(ModuleAnalysis):
    '''Order all global functions according to their callgraph depth'''
    def __init__(self):
        self.result = dict()
        super(OrderedGlobalDeclarations, self).__init__(
            StrictAliases, GlobalDeclarations)

    def visit_FunctionDef(self, node):
        self.curr = node
        self.result[node] = set()
        self.generic_visit(node)

    def visit_Name(self, node):
        if node in self.strict_aliases:
            for alias in self.strict_aliases[node].aliases:
                if isinstance(alias, ast.FunctionDef):
                    self.result[self.curr].add(alias)
                elif isinstance(alias, ast.Call):  # this is a bind
                    for alias in self.strict_aliases[alias.args[0]].aliases:
                        self.result[self.curr].add(alias)

    def run(self, node, ctx):
        # compute the weight of each function
        # the weight of a function is the number functions it references
        super(OrderedGlobalDeclarations, self).run(node, ctx)
        old_count = -1
        new_count = 0
        # iteratively propagate weights
        while new_count != old_count:
            for k, v in self.result.iteritems():
                [v.update(self.result[f]) for f in list(v)]
            old_count = new_count
            new_count = reduce(lambda acc, s: acc + len(s),
                               self.result.itervalues(), 0)
        # return functions, the one with the greatest weight first
        return sorted(self.result.iterkeys(), reverse=True,
                      key=lambda s: len(self.result[s]))

########NEW FILE########
__FILENAME__ = parallel_maps
"""
ParallelMaps detects parallel map(...)
"""
import ast
from aliases import Aliases
from pure_expressions import PureExpressions
from pythran.passmanager import ModuleAnalysis
from pythran.tables import modules


class ParallelMaps(ModuleAnalysis):
    '''Yields the est of maps that could be parallel'''
    def __init__(self):
        self.result = set()
        super(ParallelMaps, self).__init__(PureExpressions, Aliases)

    def visit_Call(self, node):
        if all(alias == modules['__builtin__']['map']
                for alias in self.aliases[node.func].aliases):
            if all(self.pure_expressions.__contains__(f)
                    for f in self.aliases[node.args[0]].aliases):
                self.result.add(node)

    def display(self, data):
        for node in data:
            print "I:", "{0} {1}".format(
                "call to the `map' intrinsic could be parallel",
                "(line {0})".format(node.lineno)
                )

########NEW FILE########
__FILENAME__ = potential_iterator
"""
PotentialIterator finds if it is possible to use an iterator.
"""
import ast
from aliases import Aliases
from argument_read_once import ArgumentReadOnce
from pythran.passmanager import NodeAnalysis


class PotentialIterator(NodeAnalysis):
    """Find whether an expression can be replaced with an iterator."""
    def __init__(self):
        self.result = set()
        NodeAnalysis.__init__(self, Aliases, ArgumentReadOnce)

    def visit_For(self, node):
        self.result.add(node.iter)
        self.generic_visit(node)

    def visit_Compare(self, node):
        if type(node.ops[0]) in [ast.In, ast.NotIn]:
            self.result.update(node.comparators)
        self.generic_visit(node)

    def visit_Call(self, node):
        for i, arg in enumerate(node.args):
            isReadOnce = lambda f: (f in self.argument_read_once
                                    and self.argument_read_once[f][i] <= 1)
            if all(isReadOnce(alias)
                   for alias in self.aliases[node.func].aliases):
                self.result.add(arg)
        self.generic_visit(node)

########NEW FILE########
__FILENAME__ = pure_expressions
"""
PureExpressions detects functions without side-effects.
"""
import ast
from argument_effects import ArgumentEffects
from global_effects import GlobalEffects
from aliases import Aliases
from pythran.passmanager import ModuleAnalysis


class PureExpressions(ModuleAnalysis):
    '''Yields the set of pure expressions'''
    def __init__(self):
        self.result = set()
        super(PureExpressions, self).__init__(ArgumentEffects, GlobalEffects,
                                              Aliases)

    def visit_FunctionDef(self, node):
        map(self.visit, node.body)
        # Pure functions are already compute, we don't need to add them again
        return False

    def generic_visit(self, node):
        is_pure = all(map(self.visit, ast.iter_child_nodes(node)))
        if is_pure:
            self.result.add(node)
        return is_pure

    def visit_Call(self, node):
        # check if all arguments are Pures
        is_pure = all(self.visit(arg) for arg in node.args)
        # check if all possible function used are Pures
        func_aliases = self.aliases[node.func].aliases
        is_pure &= func_aliases.issubset(self.result)
        # check for chained call
        is_pure &= self.visit(node.func)
        if is_pure:
            self.result.add(node)
        return is_pure

    def run(self, node, ctx):
        super(PureExpressions, self).prepare(node, ctx)
        no_arg_effect = set()
        for func, ae in self.argument_effects.iteritems():
            if not any(ae):
                no_arg_effect.add(func)
        self.result = no_arg_effect.difference(self.global_effects)
        self.visit(node)
        return self.result

########NEW FILE########
__FILENAME__ = scope
"""
Scope computes scope information
"""
import ast
from ancestors import Ancestors
from collections import defaultdict
import pythran.openmp as openmp
from pythran.passmanager import FunctionAnalysis
from use_def_chain import UseDefChain


class Scope(FunctionAnalysis):
    '''
    Associate each variable declaration with the node that defines it

    Whenever possible, associate the variable declaration to an assignment,
    otherwise to a node that defines a bloc (e.g. a For)
    This takes OpenMP information into accounts!
    The result is a dictionary with nodes as key and set of names as values
    '''

    def __init__(self):
        self.result = defaultdict(lambda: set())
        self.decl_holders = (ast.FunctionDef, ast.For,
                             ast.While, ast.TryExcept)
        super(Scope, self).__init__(Ancestors, UseDefChain)

    def visit_OMPDirective(self, node):
        for dep in node.deps:
            if type(dep) is ast.Name:
                self.openmp_deps.setdefault(dep.id, []).append(dep)

    def visit_FunctionDef(self, node):
        # first gather some info about OpenMP declarations
        self.openmp_deps = dict()
        self.generic_visit(node)

        # then compute scope informations
        # unlike use-def chains, this takes OpenMP annotations into account
        for name, udgraph in self.use_def_chain.iteritems():
            # get all refs to that name
            refs = [udgraph.node[n]['name'] for n in udgraph]
            # add OpenMP refs (well, the parent of the holding stmt)
            refs.extend(self.ancestors[d][-3]   # -3 to get the right parent
                        for d in self.openmp_deps.get(name, []))
            # get their ancestors
            ancestors = map(self.ancestors.__getitem__, refs)
            # common ancestors
            prefixes = filter(lambda x: len(set(x)) == 1, zip(*ancestors))
            common = prefixes[-1][0]  # the last common ancestor

            # now try to attach the scope to an assignment.
            # This will be the first assignment found in the bloc
            if type(common) in self.decl_holders:
                # get all refs that define that name
                refs = [udgraph.node[n]['name']
                        for n in udgraph if udgraph.node[n]['action'] == 'D']
                refs.extend(self.openmp_deps.get(name, []))
                # get their parent
                prefs = set()
                for r in refs:
                    if type(self.ancestors[r][-1]) is openmp.OMPDirective:
                        # point to the parent of the stmt holding the metadata
                        prefs.add(self.ancestors[r][-4])
                    else:
                        prefs.add(self.ancestors[r][-1])
                # set the defining statement to the first assign in the body
                # unless another statements uses it before
                # or the common itselfs holds a dependency
                if common not in prefs:
                    for c in common.body:
                        if c in prefs:
                            if type(c) is ast.Assign:
                                common = c
                            break
            self.result[common].add(name)

########NEW FILE########
__FILENAME__ = use_def_chain
"""
UsedDefChain build used-define chains analysis for each variable.
"""
import ast
from itertools import product
import networkx as nx
from globals_analysis import Globals
from imported_ids import ImportedIds
import pythran.metadata as md
from pythran.passmanager import FunctionAnalysis
from pythran.syntax import PythranSyntaxError


class UseDefChain(FunctionAnalysis):
    """Build use-define chains analysis for each variable.

       This analyse visit ast and build nodes each time it encounters an
       ast.Name node. It is a U (use) node when context is store and D (define)
       when context is Load or Param.
       This node is linked to all previous possible states in the program.
       Multiple state can happen when we use if-else statement, and loop
       can happen too with for and while statement.
       Result is a dictionary which associate a graph to the matching name.
    """
    def __init__(self):
        self.result = dict()
        self.current_node = dict()
        self.use_only = dict()
        self.in_loop = False
        self.break_ = dict()
        self.continue_ = dict()
        super(UseDefChain, self).__init__(Globals)

    def merge_dict_set(self, into_, from_):
        for i in from_:
            if i in into_:
                into_[i].update(from_[i])
            else:
                into_[i] = from_[i]

    def add_loop_edges(self, prev_node):
        self.merge_dict_set(self.continue_, self.current_node)
        for id in self.continue_:
            if id in self.result:
                graph = self.result[id]
            else:
                graph = self.use_only[id]
            if id in prev_node and prev_node[id] != self.continue_[id]:
                entering_node = [i for j in prev_node[id]
                                 for i in graph.successors_iter(j)]
            else:
                cond = lambda x: graph.in_degree(x) == 0
                entering_node = filter(cond, graph)
            graph.add_edges_from(product(self.continue_[id],
                                 entering_node))
        self.continue_ = dict()

    def visit_Name(self, node):
        if node.id not in self.result and node.id not in self.use_only:
            if not (isinstance(node.ctx, ast.Store) or
                    isinstance(node.ctx, ast.Param)):
                if node.id not in self.globals:
                    err = "identifier {0} is used before assignment"
                    raise PythranSyntaxError(err.format(node.id), node)
                else:
                    self.use_only[node.id] = nx.DiGraph()
                    self.use_only[node.id].add_node("D0",
                                                    action="D", name=node)
            else:
                self.result[node.id] = nx.DiGraph()
                self.result[node.id].add_node("D0", action="D", name=node)
            self.current_node[node.id] = set(["D0"])
        else:
            if node.id in self.result:
                graph = self.result[node.id]
            else:
                graph = self.use_only[node.id]
            if (isinstance(node.ctx, ast.Store) or
                    isinstance(node.ctx, ast.Param)):
                if node.id in self.use_only:
                    err = ("identifier {0} has a global linkage and can't"
                           "be assigned")
                    raise PythranSyntaxError(err.format(node.id), node)
                node_name = "D{0}".format(len(graph))
                graph.add_node(node_name, action="D", name=node)
            elif isinstance(node.ctx, ast.Load):
                node_name = "U{0}".format(len(graph))
                graph.add_node(node_name, action="U", name=node)
            else:
                return  # Other context are unused and Del is ignored
            prev_nodes = self.current_node.get(node.id, set())
            edges_list = zip(prev_nodes, [node_name] * len(prev_nodes))
            graph.add_edges_from(edges_list)
            self.current_node[node.id] = set([node_name])

    def visit_Assign(self, node):
        md.visit(self, node)
        # in assignation, left expression is compute before the assignation
        # to the right expression
        self.visit(node.value)
        map(self.visit, node.targets)

    def visit_AugAssign(self, node):
        md.visit(self, node)
        self.visit(node.value)
        self.visit(node.target)
        var = node.target
        while isinstance(var, ast.Subscript):
            var = var.value
        if isinstance(var, ast.Name):
            var = var.id
        else:
            err = "AugAssign can't be used on {0}"
            raise PythranSyntaxError(err.format(var), node)
        last_node = self.current_node[var].pop()
        self.result[var].node[last_node]['action'] = "UD"
        self.current_node[var] = set([last_node])

    def visit_If(self, node):
        md.visit(self, node)
        swap = False
        self.visit(node.test)

        #if an identifier is first used in orelse and we are in a loop,
        #we swap orelse and body
        undef = self.passmanager.gather(ImportedIds, node.body, self.ctx)
        if not all(i in self.current_node for i in undef) and self.in_loop:
            node.body, node.orelse = node.orelse, node.body
            swap = True

        #body
        old_node = {i: set(j) for i, j in self.current_node.iteritems()}
        map(self.visit, node.body)

        #orelse
        new_node = self.current_node
        self.current_node = old_node
        map(self.visit, node.orelse)

        if swap:
            node.body, node.orelse = node.orelse, node.body

        #merge result
        self.merge_dict_set(self.current_node, new_node)

    def visit_IfExp(self, node):
        md.visit(self, node)
        swap = False
        self.visit(node.test)

        #if an identifier is first used in orelse and we are in a loop,
        #we swap orelse and body
        undef = self.passmanager.gather(ImportedIds, node.body, self.ctx)
        if undef and self.in_loop:
            node.body, node.orelse = node.orelse, node.body
            swap = True

        #body
        old_node = {i: set(j) for i, j in self.current_node.iteritems()}
        self.visit(node.body)

        #orelse
        new_node = self.current_node
        self.current_node = old_node
        self.visit(node.orelse)

        if swap:
            node.body, node.orelse = node.orelse, node.body

        #merge result
        self.merge_dict_set(self.current_node, new_node)

    def visit_Break(self, node):
        md.visit(self, node)
        self.merge_dict_set(self.break_, self.current_node)

    def visit_Continue(self, node):
        md.visit(self, node)
        self.merge_dict_set(self.continue_, self.current_node)

    def visit_While(self, node):
        md.visit(self, node)
        prev_node = {i: set(j) for i, j in self.current_node.iteritems()}
        self.visit(node.test)
        #body
        self.in_loop = True
        old_node = {i: set(j) for i, j in self.current_node.iteritems()}
        map(self.visit, node.body)
        self.add_loop_edges(prev_node)
        self.in_loop = False

        #orelse
        new_node = self.current_node
        self.merge_dict_set(self.current_node, old_node)
        map(self.visit, node.orelse)

        #merge result
        self.merge_dict_set(self.current_node, new_node)
        self.merge_dict_set(self.current_node, self.break_)
        self.break_ = dict()

    def visit_For(self, node):
        md.visit(self, node)
        self.visit(node.iter)

        #body
        self.in_loop = True
        old_node = {i: set(j) for i, j in self.current_node.iteritems()}
        self.visit(node.target)
        map(self.visit, node.body)
        self.add_loop_edges(old_node)
        self.in_loop = False

        #orelse
        new_node = self.current_node
        self.merge_dict_set(self.current_node, old_node)
        map(self.visit, node.orelse)

        #merge result
        self.merge_dict_set(self.current_node, new_node)
        self.merge_dict_set(self.current_node, self.break_)
        self.break_ = dict()

    def visit_TryExcept(self, node):
        md.visit(self, node)

        #body
        all_node = dict()
        for stmt in node.body:
            self.visit(stmt)
            for k, i in self.current_node.iteritems():
                if k not in all_node:
                    all_node[k] = i
                else:
                    all_node[k].update(i)

        no_except = self.current_node

        #except
        for ex in node.handlers:
            self.current_node = dict(all_node)
            self.visit(ex)

            #merge result
            self.merge_dict_set(no_except, self.current_node)

        self.current_node = no_except

        if node.orelse:
            err = ("orelse should have been removed in previous passes")
            raise PythranSyntaxError(err, node)

    def visit_TryFinally(self, node):
        err = ("This node should have been removed in previous passes")
        raise PythranSyntaxError(err, node)

########NEW FILE########
__FILENAME__ = use_omp
"""
UseOMP detects if a function use OpenMP
"""
from pythran.passmanager import FunctionAnalysis


class UseOMP(FunctionAnalysis):
    """Detects if a function use openMP"""
    def __init__(self):
        self.result = False
        super(UseOMP, self).__init__()

    def visit_OMPDirective(self, node):
        self.result = True

########NEW FILE########
__FILENAME__ = yield_points
"""
YieldPoints gathers all yield points from a node
"""
import ast
from pythran.passmanager import FunctionAnalysis


class YieldPoints(FunctionAnalysis):
    '''Gathers all yield points of a generator, if any.'''
    def __init__(self):
        self.result = list()
        super(YieldPoints, self).__init__()

    def visit_Yield(self, node):
        self.result.append(node)

########NEW FILE########
__FILENAME__ = backend
'''
This module contains all pythran backends.
    * Cxx dumps the AST into C++ code
    * Python dumps the AST into Python code
'''

import ast
from cxxgen import *
from cxxtypes import *

from analyses import LocalDeclarations, GlobalDeclarations, Scope, Dependencies
from analyses import YieldPoints, BoundedExpressions, ArgumentEffects
from passmanager import Backend

from tables import operator_to_lambda, modules, type_to_suffix
from tables import pytype_to_ctype_table
from tables import pythran_ward
from typing import Types
from syntax import PythranSyntaxError

from openmp import OMPDirective

from math import isnan, isinf

import cStringIO
import unparse
import metadata


class Python(Backend):
    '''
    Produces a Python representation of the AST.

    >>> import ast, passmanager
    >>> node = ast.parse("print 'hello world'")
    >>> pm = passmanager.PassManager('test')
    >>> print pm.dump(Python, node)
    print 'hello world'
    '''

    def __init__(self):
        self.result = ''
        super(Python, self).__init__()

    def visit(self, node):
        output = cStringIO.StringIO()
        unparse.Unparser(node, output)
        self.result = output.getvalue()


def templatize(node, types, default_types=None):
    if not default_types:
        default_types = [None] * len(types)
    if types:
        return Template(
            ["typename {0} {1}".format(t, "= {0}".format(d) if d else "")
             for t, d in zip(types, default_types)],
            node)
    else:
        return node


def strip_exp(s):
    if s.startswith('(') and s.endswith(')'):
        return s[1:-1]
    else:
        return s


class Cxx(Backend):
    '''
    Produces a C++ representation of the AST.

    >>> import ast, passmanager
    >>> node = ast.parse("print 'hello world'")
    >>> pm = passmanager.PassManager('test')
    >>> r = pm.dump(Cxx, node)
    >>> print r
    #include <pythonic/__builtin__/print.hpp>
    #include <pythonic/__builtin__/str.hpp>
    namespace __pythran_test
    {
      pythonic::__builtin__::print(pythonic::types::str("hello world"));
    }
    '''

    # recover previous generator state
    generator_state_holder = "__generator_state"
    generator_state_value = "__generator_value"
    # flags the last statement of a generator
    final_statement = "that_is_all_folks"

    def __init__(self):
        self.declarations = list()
        self.definitions = list()
        self.break_handlers = list()
        self.result = None
        super(Cxx, self).__init__(Dependencies, GlobalDeclarations,
                                  BoundedExpressions, Types, ArgumentEffects,
                                  Scope)

    # mod
    def visit_Module(self, node):
        # build all types
        def gen_include(t):
            return "/".join(("pythonic",) + t) + ".hpp"
        headers = map(Include, sorted(map(gen_include, self.dependencies)))

        # remove top-level strings
        fbody = (n for n in node.body if not isinstance(n, ast.Expr))
        body = map(self.visit, fbody)

        nsbody = body + self.declarations + self.definitions
        ns = Namespace(pythran_ward + self.passmanager.module_name, nsbody)
        self.result = CompilationUnit(headers + [ns])

    # local declaration processing
    def process_locals(self, node, node_visited, *skipped):
        locals = self.scope[node].difference(skipped)
        if not locals or self.yields:
            return node_visited  # no processing

        locals_visited = []
        for varname in locals:
            vartype = self.local_types[varname]
            decl = Statement("{} {}".format(vartype, varname))
            locals_visited.append(decl)
        self.ldecls = [ld for ld in self.ldecls if ld.id not in locals]
        return Block(locals_visited + [node_visited])

    # openmp processing
    def process_omp_attachements(self, node, stmt, index=None):
        l = metadata.get(node, OMPDirective)
        if l:
            directives = list()
            for directive in reversed(l):
                # special hook for default for index scope
                if isinstance(node, ast.For):
                    target = node.target
                    hasfor = 'for' in directive.s
                    nodefault = 'default' not in directive.s
                    noindexref = all(x.id != target.id for x in directive.deps)
                    if (hasfor and nodefault and noindexref and
                            target.id not in self.scope[node]):
                        directive.s += ' private({})'
                        directive.deps.append(ast.Name(target.id, ast.Load()))
                directive.deps = map(self.visit, directive.deps)
                directives.append(directive)
            if index is None:
                stmt = AnnotatedStatement(stmt, directives)
            else:
                stmt[index] = AnnotatedStatement(stmt[index], directives)
        return stmt

    # stmt
    def visit_FunctionDef(self, node):
        class CachedTypeVisitor:
            class CachedType:
                def __init__(self, s):
                    self.s = s

                def generate(self, ctx):
                    return self.s

            def __init__(self, other=None):
                if other:
                    self.cache = other.cache.copy()
                    self.rcache = other.rcache.copy()
                    self.mapping = other.mapping.copy()
                else:
                    self.cache = dict()
                    self.rcache = dict()
                    self.mapping = dict()

            def __call__(self, node):
                if node not in self.mapping:
                    t = node.generate(self)
                    if t in self.rcache:
                        self.mapping[node] = self.mapping[self.rcache[t]]
                        self.cache[node] = self.cache[self.rcache[t]]
                    else:
                        self.rcache[t] = node
                        self.mapping[node] = len(self.mapping)
                        self.cache[node] = t
                return CachedTypeVisitor.CachedType(
                    "__type{0}".format(self.mapping[node]))

            def typedefs(self):
                l = sorted(self.mapping.items(), key=lambda x: x[1])
                L = list()
                visited = set()  # the same value must not be typedefed twice
                for k, v in l:
                    if v not in visited:
                        typename = "__type" + str(v)
                        L.append(Typedef(Value(self.cache[k], typename)))
                        visited.add(v)
                return L

        # prepare context and visit function body
        fargs = node.args.args

        formal_args = [arg.id for arg in fargs]
        formal_types = ["argument_type" + str(i) for i in xrange(len(fargs))]

        self.ldecls = self.passmanager.gather(LocalDeclarations, node)

        self.local_names = {sym.id for sym in self.ldecls}.union(formal_args)
        self.extra_declarations = []

        lctx = CachedTypeVisitor()
        self.local_types = {n: self.types[n].generate(lctx)
                            for n in self.ldecls}
        self.local_types.update((n.id, t) for n, t in self.local_types.items())

        # choose one node among all the ones with the same name for each name
        self.ldecls = {n for _, n in
                       {n.id: n for n in self.ldecls}.iteritems()}

        # 0 is used as initial_state, thus the +1
        self.yields = {k: (1 + v, "yield_point{0}".format(1 + v)) for (v, k) in
                       enumerate(self.passmanager.gather(YieldPoints, node))}

        # gather body dump
        operator_body = map(self.visit, node.body)

        # compute arg dump
        default_arg_values = (
            [None] * (len(node.args.args) - len(node.args.defaults))
            + [self.visit(n) for n in node.args.defaults])
        default_arg_types = (
            [None] * (len(node.args.args) - len(node.args.defaults))
            + [self.types[n] for n in node.args.defaults])

        # compute type dump
        result_type = self.types[node][0]

        callable_type = Typedef(Value("void", "callable"))

        def make_function_declaration(rtype, name, ftypes, fargs,
                                      defaults=None, attributes=[]):
            if defaults is None:
                defaults = [None] * len(ftypes)
            arguments = list()
            for i, (t, a, d) in enumerate(zip(ftypes, fargs, defaults)):
                if self.yields:
                    rvalue_ref = ""
                elif self.argument_effects[node][i]:
                    rvalue_ref = "&&"
                else:
                    rvalue_ref = " const &"
                argument = Value(
                    t + rvalue_ref,
                    "{0}{1}".format(a, "= {0}".format(d) if d else ""))
                arguments.append(argument)
            return FunctionDeclaration(Value(rtype, name), arguments,
                                       *attributes)

        def make_const_function_declaration(rtype, name, ftypes, fargs,
                                            defaults=None):
            return make_function_declaration(rtype, name, ftypes, fargs,
                                             defaults, ["const"])

        if self.yields:  # generator case
            # a generator has a call operator that returns the iterator

            next_name = "__generator__{0}".format(node.name)
            instanciated_next_name = "{0}{1}".format(
                next_name,
                "<{0}>".format(
                    ", ".join(formal_types)) if formal_types else "")

            operator_body.append(
                Statement("{0}: return result_type();".format(
                    Cxx.final_statement)))

            next_declaration = [
                FunctionDeclaration(Value("result_type", "next"), []),
                EmptyStatement()]  # empty statement to force a comma ...

            # the constructors
            next_constructors = [
                FunctionBody(
                    FunctionDeclaration(Value("", next_name), []),
                    Line(': {}(0) {{}}'.format(Cxx.generator_state_holder))
                    )]
            if formal_types:
                #if all parameters have a default value, we don't need default
                # constructor
                if default_arg_values and all(default_arg_values):
                    next_constructors = list()
                next_constructors.append(FunctionBody(
                    make_function_declaration("", next_name, formal_types,
                                              formal_args, default_arg_values),
                    Line("{0} {{ }}".format(
                        ": {0}".format(
                            ", ".join(
                                ["{0}({0})".format(fa) for fa in formal_args]
                                +
                                ["{0}(0)".format(
                                    Cxx.generator_state_holder)]))))
                    ))

            next_iterator = [
                FunctionBody(
                    FunctionDeclaration(Value("void", "operator++"), []),
                    Block([Statement("next()")])),
                FunctionBody(
                    FunctionDeclaration(
                        Value("typename {0}::result_type".format(
                            instanciated_next_name),
                            "operator*"),
                        [], "const"),
                    Block([
                        ReturnStatement(
                            Cxx.generator_state_value)])),
                FunctionBody(
                    FunctionDeclaration(
                        Value("pythonic::types::generator_iterator<{0}>"
                              .format(next_name),
                              "begin"),
                        []),
                    Block([Statement("next()"),
                           ReturnStatement(
                               "pythonic::types::generator_iterator<{0}>"
                               "(*this)".format(next_name))])),
                FunctionBody(
                    FunctionDeclaration(
                        Value("pythonic::types::generator_iterator<{0}>"
                              .format(next_name),
                              "end"),
                        []),
                    Block([ReturnStatement(
                        "pythonic::types::generator_iterator<{0}>()"
                        .format(next_name))])),
                FunctionBody(
                    FunctionDeclaration(
                        Value("bool", "operator!="),
                        [Value("{0} const &".format(next_name), "other")],
                        "const"),
                    Block([ReturnStatement(
                        "{0}!=other.{0}".format(
                            Cxx.generator_state_holder))])),
                FunctionBody(
                    FunctionDeclaration(
                        Value("bool", "operator=="),
                        [Value("{0} const &".format(next_name), "other")],
                        "const"),
                    Block([ReturnStatement(
                        "{0}==other.{0}".format(
                            Cxx.generator_state_holder))])),
                ]
            next_signature = templatize(
                FunctionDeclaration(
                    Value(
                        "typename {0}::result_type".format(
                            instanciated_next_name),
                        "{0}::next".format(instanciated_next_name)),
                    []),
                formal_types)

            next_body = operator_body
            # the dispatch table at the entry point
            next_body.insert(0, Statement("switch({0}) {{ {1} }}".format(
                Cxx.generator_state_holder,
                " ".join("case {0}: goto {1};".format(num, where)
                         for (num, where) in sorted(
                             self.yields.itervalues(),
                             key=lambda x: x[0])))))

            ctx = CachedTypeVisitor(lctx)
            next_members = ([Statement("{0} {1}".format(ft, fa))
                             for (ft, fa) in zip(formal_types, formal_args)]
                            + [Statement(
                                "{0} {1}".format(self.types[k].generate(ctx),
                                                 k.id))
                               for k in self.ldecls]
                            + [Statement("{0} {1}".format(v, k))
                               for k, v in self.extra_declarations]
                            + [Statement("{0} {1}".format("long",
                               Cxx.generator_state_holder))]
                            + [Statement(
                                "typename {0}::result_type {1}".format(
                                    instanciated_next_name,
                                    Cxx.generator_state_value))])

            extern_typedefs = [Typedef(Value(t.generate(ctx), t.name))
                               for t in self.types[node][1] if not t.isweak()]
            iterator_typedef = [
                Typedef(
                    Value("pythonic::types::generator_iterator<{0}>".format(
                        "{0}<{1}>".format(next_name, ", ".join(formal_types))
                        if formal_types else next_name),
                        "iterator")),
                Typedef(Value(result_type.generate(ctx),
                              "value_type"))]
            result_typedef = [
                Typedef(Value(result_type.generate(ctx), "result_type"))]
            extra_typedefs = (ctx.typedefs()
                              + extern_typedefs
                              + iterator_typedef
                              + result_typedef)

            next_struct = templatize(
                Struct(next_name,
                       extra_typedefs
                       + next_members
                       + next_constructors
                       + next_iterator
                       + next_declaration),
                formal_types)
            next_definition = FunctionBody(next_signature, Block(next_body))

            operator_declaration = [
                templatize(
                    make_const_function_declaration(
                        instanciated_next_name,
                        "operator()",
                        formal_types,
                        formal_args,
                        default_arg_values),
                    formal_types,
                    default_arg_types),
                EmptyStatement()]
            operator_signature = make_const_function_declaration(
                instanciated_next_name,
                "{0}::operator()".format(node.name),
                formal_types,
                formal_args)
            operator_definition = FunctionBody(
                templatize(operator_signature, formal_types),
                Block([ReturnStatement("{0}({1})".format(
                    instanciated_next_name,
                    ", ".join(formal_args)))])
                )

            topstruct_type = templatize(
                Struct("type", extra_typedefs),
                formal_types)
            topstruct = Struct(
                node.name,
                [topstruct_type, callable_type]
                + operator_declaration)

            self.declarations.append(next_struct)
            self.definitions.append(next_definition)

        else:  # regular function case
            # a function has a call operator to be called
            # and a default constructor to create instances
            fscope = "type{0}::".format("<{0}>".format(", ".join(formal_types))
                                        if formal_types
                                        else "")
            ffscope = "{0}::{1}".format(node.name, fscope)

            operator_declaration = [
                templatize(
                    make_const_function_declaration(
                        "typename {0}result_type".format(fscope),
                        "operator()",
                        formal_types,
                        formal_args,
                        default_arg_values),
                    formal_types,
                    default_arg_types),
                EmptyStatement()
                ]
            operator_signature = make_const_function_declaration(
                "typename {0}result_type".format(ffscope),
                "{0}::operator()".format(node.name),
                formal_types,
                formal_args)
            ctx = CachedTypeVisitor(lctx)
            operator_local_declarations = (
                [Statement("{0} {1}".format(
                 self.types[k].generate(ctx), k.id)) for k in self.ldecls]
                + [Statement("{0} {1}".format(v, k))
                   for k, v in self.extra_declarations]
                )
            dependent_typedefs = ctx.typedefs()
            operator_definition = FunctionBody(
                templatize(operator_signature, formal_types),
                Block(dependent_typedefs
                      + operator_local_declarations
                      + operator_body)
                )

            ctx = CachedTypeVisitor()
            extra_typedefs = (
                [Typedef(Value(t.generate(ctx), t.name))
                 for t in self.types[node][1] if not t.isweak()]
                + [Typedef(Value(
                    result_type.generate(ctx),
                    "result_type"))]
                )
            extra_typedefs = ctx.typedefs() + extra_typedefs
            return_declaration = [
                templatize(
                    Struct("type", extra_typedefs),
                    formal_types,
                    default_arg_types
                    )
                ]
            topstruct = Struct(node.name,
                               [callable_type]
                               + return_declaration
                               + operator_declaration)

        self.declarations.append(topstruct)
        self.definitions.append(operator_definition)

        return EmptyStatement()

    def visit_Return(self, node):
        if self.yields:
            return Block([
                Statement("{0} = -1".format(
                    Cxx.generator_state_holder)),
                Statement("goto {0}".format(
                    Cxx.final_statement))
                ])
        else:
            stmt = ReturnStatement(self.visit(node.value))
            return self.process_omp_attachements(node, stmt)

    def visit_Delete(self, node):
        return EmptyStatement()

    def visit_Yield(self, node):
        num, label = self.yields[node]
        return "".join(n for n in Block([
            Assign(Cxx.generator_state_holder, num),
            ReturnStatement("{0} = {1}".format(
                Cxx.generator_state_value,
                self.visit(node.value))),
            Statement("{0}:".format(label))
            ]).generate())

    def visit_Assign(self, node):
        if not all(isinstance(n, ast.Name) or isinstance(n, ast.Subscript)
                   for n in node.targets):
            raise PythranSyntaxError(
                "Must assign to an identifier or a subscript",
                node)
        value = self.visit(node.value)
        targets = [self.visit(t) for t in node.targets]
        alltargets = "= ".join(targets)
        islocal = any(metadata.get(t, metadata.LocalVariable)
                      for t in node.targets)
        if len(targets) == 1 and isinstance(node.targets[0], ast.Name):
            islocal |= node.targets[0].id in self.scope[node]
        if islocal and not self.yields:
            # remove this decl from local decls
            tdecls = {t.id for t in node.targets}
            self.ldecls = {d for d in self.ldecls if d.id not in tdecls}
            # add a local declaration
            alltargets = '{} {}'.format(self.local_types[node.targets[0]],
                                        alltargets)
        stmt = Assign(alltargets, value)
        return self.process_omp_attachements(node, stmt)

    def visit_AugAssign(self, node):
        value = self.visit(node.value)
        target = self.visit(node.target)
        l = operator_to_lambda[type(node.op)]
        if type(node.op) in (ast.FloorDiv, ast.Mod, ast.Pow):
            stmt = Assign(target, l(target, value))
        else:
            stmt = Statement(l(target, '')[1:-2] + '= {0}'.format(value))
        return self.process_omp_attachements(node, stmt)

    def visit_Print(self, node):
        values = [self.visit(n) for n in node.values]
        stmt = Statement("pythonic::__builtin__::print{0}({1})".format(
            "" if node.nl else "_nonl",
            ", ".join(values))
            )
        return self.process_omp_attachements(node, stmt)

    def visit_For(self, node):
        if not isinstance(node.target, ast.Name):
            raise PythranSyntaxError(
                "Using something other than an identifier as loop target",
                node.target)
        iter = self.visit(node.iter)
        target = self.visit(node.target)

        if node.orelse:
            break_handler = "__no_breaking{0}".format(len(self.break_handlers))
        else:
            break_handler = None
        self.break_handlers.append(break_handler)

        local_iter = "__iter{0}".format(len(self.break_handlers))
        local_target = "__target{0}".format(len(self.break_handlers))

        local_iter_decl = Assignable(DeclType(iter))
        local_target_decl = NamedType("{0}::iterator".format(local_iter_decl))
        if self.yields:
            self.extra_declarations.append((local_iter, local_iter_decl,))
            self.extra_declarations.append((local_target, local_target_decl,))
            local_target_decl = ""
            local_iter_decl = ""

        loop_body = Block(map(self.visit, node.body))

        self.break_handlers.pop()

        # eventually add local_iter in a shared clause
        omp = metadata.get(node, OMPDirective)
        if omp:
            for directive in omp:
                if 'parallel' in directive.s:
                    directive.s += ' shared({})'
                    directive.deps.append(ast.Name(local_iter, ast.Param()))

        prelude = Statement("{0} {1} = {2}".format(
            local_iter_decl, local_iter, iter)
            )

        auto_for = bool(metadata.get(node.target, metadata.LocalVariable))
        auto_for |= (type(node.target) is ast.Name
                     and node.target.id in self.scope[node])
        auto_for &= not self.yields and not omp

        loop_body = self.process_locals(node, loop_body, node.target.id)

        if auto_for:
            self.ldecls = {d for d in self.ldecls if d.id != node.target.id}
            loop = AutoFor(target, local_iter, loop_body)
        else:
            if node.target.id in self.scope[node] and not self.yields:
                self.ldecls = {d for d in self.ldecls
                               if d.id != node.target.id}
                local_type = "typename decltype({})::reference ".format(
                    local_target)
            else:
                local_type = ""
            loop_body_prelude = Statement("{} {}= *{}".format(local_type,
                                                              target,
                                                              local_target))
            loop = For(
                "{0} {1} = {2}.begin()".format(
                    local_target_decl,
                    local_target,
                    local_iter),
                "{0} < {1}.end()".format(
                    local_target,
                    local_iter),
                "++{0}".format(local_target),
                Block([loop_body_prelude, loop_body])
                )
        stmts = [prelude, loop]

        # in that case when can proceed to a reserve
        for comp in metadata.get(node, metadata.Comprehension):
            stmts.insert(1,
                         Statement("pythonic::utils::reserve({0},{1})".format(
                             comp.target,
                             local_iter)))

        if break_handler:
            orelse = map(self.visit, node.orelse)
            orelse_label = Statement("{0}:".format(break_handler))
            stmts.append(Block(orelse + [orelse_label]))

        return Block(self.process_omp_attachements(node, stmts, 1))

    def visit_While(self, node):
        test = self.visit(node.test)

        if node.orelse:
            break_handler = "__no_breaking{0}".format(len(self.break_handlers))
        else:
            break_handler = None
        self.break_handlers.append(break_handler)

        body = [self.visit(n) for n in node.body]

        self.break_handlers.pop()

        while_ = While(test, Block(body))

        if break_handler:
            orelse = map(self.visit, node.orelse)
            orelse_label = Statement("{0}:".format(break_handler))
            return Block([while_] + orelse + [orelse_label])
        else:
            return while_

    def visit_TryExcept(self, node):
        body = [self.visit(n) for n in node.body]
        except_ = list()
        [except_.extend(self.visit(n)) for n in node.handlers]
        return TryExcept(Block(body), except_, None)

    def visit_ExceptHandler(self, node):
        name = self.visit(node.name) if node.name else None
        body = [self.visit(m) for m in node.body]
        if not isinstance(node.type, ast.Tuple):
            return [ExceptHandler(
                node.type and node.type.attr,
                Block(body),
                name)]
        else:
            elts = [p.attr for p in node.type.elts]
            return [ExceptHandler(o, Block(body), name) for o in elts]

    def visit_If(self, node):
        test = self.visit(node.test)
        body = [self.visit(n) for n in node.body]
        orelse = [self.visit(n) for n in node.orelse]
        if isinstance(node.test, ast.Num) and node.test.n == 1:
            stmt = Block(body)
        else:
            stmt = If(test, Block(body), Block(orelse) if orelse else None)
        return self.process_locals(node,
                                   self.process_omp_attachements(node, stmt))

    def visit_Raise(self, node):
        type = node.type and self.visit(node.type)
        if node.inst:
            if isinstance(node.inst, ast.Tuple):
                inst = ['"{0}"'.format(e.s) for e in node.inst.elts]
            else:
                inst = [node.inst.s]
        else:
            inst = None
        if inst:
            return Statement("throw {0}({1})".format(type, ", ".join(inst)))
        else:
            return Statement("throw {0}".format(type or ""))

    def visit_Assert(self, node):
        params = [self.visit(node.test), node.msg and self.visit(node.msg)]
        sparams = ", ".join(map(strip_exp, filter(None, params)))
        return Statement("pythonic::pythran_assert({0})".format(sparams))

    def visit_Import(self, node):
        return EmptyStatement()  # everything is already #included

    def visit_ImportFrom(self, node):
        assert False, "should be filtered out by the expand_import pass"

    def visit_Expr(self, node):
        # turn docstring into comments
        if type(node.value) is ast.Str:
            stmt = Line("//" + node.value.s.replace('\n', '\n//'))
        # other expressions are processed normally
        else:
            stmt = Statement(self.visit(node.value))
        return self.process_locals(node,
                                   self.process_omp_attachements(node, stmt))

    def visit_Pass(self, node):
        stmt = EmptyStatement()
        return self.process_omp_attachements(node, stmt)

    def visit_Break(self, node):
        if self.break_handlers[-1]:
            return Statement("goto {0}".format(self.break_handlers[-1]))
        else:
            return Statement("break")

    def visit_Continue(self, node):
        return Statement("continue")

    # expr
    def visit_BoolOp(self, node):
        values = [self.visit(value) for value in node.values]
        if node in self.bounded_expressions:
            op = operator_to_lambda[type(node.op)]
        elif isinstance(node.op, ast.And):
            op = lambda l, r: '({0} and {1})'.format(l, r)
        elif isinstance(node.op, ast.Or):
            op = lambda l, r: '({0} or {1})'.format(l, r)
        return reduce(op, values)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return operator_to_lambda[type(node.op)](left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        return operator_to_lambda[type(node.op)](operand)

    def visit_IfExp(self, node):
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)
        return "({0} ? {1} : {2})".format(test, body, orelse)

    def visit_List(self, node):
        if not node.elts:  # empty list
            return "pythonic::__builtin__::list()"
        else:
            elts = [self.visit(n) for n in node.elts]
            # constructor disambiguation, clang++ workaround
            if len(elts) == 1:
                elts.append('pythonic::types::single_value()')
                return "{0}({{ {1} }})".format(
                    Assignable(self.types[node]),
                    ", ".join(elts))
            else:
                return "{0}({{ {1} }})".format(
                    Assignable(self.types[node]),
                    ", ".join(elts))

    def visit_Set(self, node):
        if not node.elts:  # empty set
            return "pythonic::__builtin__::set()"
        else:
            elts = [self.visit(n) for n in node.elts]
            return "{0}({{ {1} }})".format(
                Assignable(self.types[node]),
                ", ".join(elts))

    def visit_Dict(self, node):
        if not node.keys:  # empty dict
            return "pythonic::__builtin__::dict()"
        else:
            keys = [self.visit(n) for n in node.keys]
            values = [self.visit(n) for n in node.values]
            return "{0}({{ {1} }})".format(
                Assignable(self.types[node]),
                ", ".join("{{ {0}, {1} }}".format(k, v)
                          for k, v in zip(keys, values)))

    def visit_Tuple(self, node):
        elts = map(self.visit, node.elts or ())
        return "pythonic::types::make_tuple({0})".format(", ".join(elts))

    def visit_Compare(self, node):
        left = self.visit(node.left)
        ops = [operator_to_lambda[type(n)] for n in node.ops]
        comparators = [self.visit(n) for n in node.comparators]
        all_compare = zip(ops, comparators)
        op, right = all_compare[0]
        output = [op(left, right)]
        left = right
        for op, right in all_compare[1:]:
            output.append(op(left, right))
            left = right
        return " and ".join(output)

    def visit_Call(self, node):
        args = [self.visit(n) for n in node.args]
        func = self.visit(node.func)
        # special hook for getattr, as we cannot represent it in C++
        if func == 'pythonic::__builtin__::proxy::getattr{}':
            return ('pythonic::__builtin__::getattr<{}>({})'
                    .format('pythonic::types::attr::' + node.args[1].s,
                            args[0]))
        else:
            return "{}({})".format(func, ", ".join(args))

    def visit_Num(self, node):
        if type(node.n) == complex:
            return "{0}({1}, {2})".format(
                pytype_to_ctype_table[complex],
                repr(node.n.real),
                repr(node.n.imag))
        elif type(node.n) == long:
            return 'pythran_long({0})'.format(node.n)
        elif isnan(node.n):
            return 'pythonic::numpy::nan'
        elif isinf(node.n):
            return ('+' if node.n > 0 else '-') + 'pythonic::numpy::inf'
        else:
            return repr(node.n) + type_to_suffix.get(type(node.n), "")

    def visit_Str(self, node):
        quoted = node.s.replace('"', '\\"').replace('\n', '\\n"\n"')
        return 'pythonic::types::str("{0}")'.format(quoted)

    def visit_Attribute(self, node):
        def rec(w, n):
            if isinstance(n, ast.Name):
                return w[n.id], (n.id,)
            elif isinstance(n, ast.Attribute):
                r = rec(w, n.value)
                if len(r[1]) > 1:
                    plast, last = r[1][-2:]
                    if plast == '__builtin__' and last.startswith('__'):
                        return r[0][n.attr], r[1][:-2] + r[1][-1:] + (n.attr,)
                return r[0][n.attr], r[1] + (n.attr,)
        obj, path = rec(modules, node)
        path = ('pythonic',) + path
        return ('::'.join(path) if obj.isliteral()
                else ('::'.join(path[:-1]) + '::proxy::' + path[-1] + '{}'))

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        # positive static index case
        if (isinstance(node.slice, ast.Index)
                and isinstance(node.slice.value, ast.Num)
                and (node.slice.value.n >= 0)
                and any(isinstance(node.slice.value.n, t)
                        for t in (int, long))):
            return "std::get<{0}>({1})".format(node.slice.value.n, value)
        # slice optimization case
        elif (isinstance(node.slice, ast.Slice)
                and (isinstance(node.ctx, ast.Store)
                     or node not in self.bounded_expressions)):
            slice = self.visit(node.slice)
            return "{1}({0})".format(slice, value)
        # extended slice case
        elif isinstance(node.slice, ast.ExtSlice):
            slice = self.visit(node.slice)
            return "{1}({0})".format(','.join(slice), value)
        # standard case
        else:
            slice = self.visit(node.slice)
            return "{1}[{0}]".format(slice, value)

    def visit_Name(self, node):
        if node.id in self.local_names:
            return node.id
        elif node.id in self.global_declarations:
            return "{0}()".format(node.id)
        else:
            return node.id

    # other
    def visit_ExtSlice(self, node):
        return map(self.visit, node.dims)

    def visit_Slice(self, node):
        args = []
        for field in ('lower', 'upper', 'step'):
            nfield = getattr(node, field)
            arg = (self.visit(nfield) if nfield
                   else 'pythonic::__builtin__::None')
            args.append(arg)
        if node.step is None or (type(node.step) is ast.Num
                                 and node.step.n == 1):
            return "pythonic::types::contiguous_slice({},{})".format(args[0],
                                                                     args[1])
        else:
            return "pythonic::types::slice({},{},{})".format(*args)

    def visit_Index(self, node):
        return self.visit(node.value)

########NEW FILE########
__FILENAME__ = config
import ConfigParser as configparser
import sys
import os


def init_cfg(sys_file, user_file):
    sys_config_dir = os.path.dirname(__file__)
    sys_config_path = os.path.join(sys_config_dir, sys_file)

    user_config_dir = os.environ.get('XDG_CONFIG_HOME', '~')
    user_config_path = os.path.expanduser(
        os.path.join(user_config_dir, user_file))

    cfg = configparser.SafeConfigParser()
    cfg.read([sys_config_path, user_config_path])

    return cfg

cfg = init_cfg('pythran.cfg', '.pythranrc')

########NEW FILE########
__FILENAME__ = cxxgen
"""
Generator for C/C++.
"""

# Serge Guelton: The licensing terms are not set in the source package, but
# pypi[1] says the software is under the MIT license, so I reproduce it here
# [1] http://pypi.python.org/pypi/cgen
#
# Copyright (C) 2008 Andreas Kloeckner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"


class Generable(object):
    def __str__(self):
        """Return a single string (possibly containing newlines) representing
        this code construct."""
        return "\n".join(l.rstrip() for l in self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""
        raise NotImplementedError


class Declarator(Generable):
    def generate(self, with_semicolon=True):
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = list(tp_lines)
        for line in tp_lines[:-1]:
            yield line
        sc = ";"
        if not with_semicolon:
            sc = ""
        if tp_decl is None:
            yield "%s%s" % (tp_lines[-1], sc)
        else:
            yield "%s %s%s" % (tp_lines[-1], tp_decl, sc)

    def get_decl_pair(self):
        """Return a tuple ``(type_lines, rhs)``.

        *type_lines* is a non-empty list of lines (most often just a
        single one) describing the type of this declarator. *rhs* is the right-
        hand side that actually contains the function/array/constness notation
        making up the bulk of the declarator syntax.
        """

    def inline(self, with_semicolon=True):
        """Return the declarator as a single line."""
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = " ".join(tp_lines)
        if tp_decl is None:
            return tp_lines
        else:
            return "%s %s" % (tp_lines, tp_decl)


class Value(Declarator):
    """A simple declarator: *typename* and *name* are given as strings."""

    def __init__(self, typename, name):
        self.typename = typename
        self.name = name

    def get_decl_pair(self):
        return [self.typename], self.name


class NestedDeclarator(Declarator):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    @property
    def name(self):
        return self.subdecl.name

    def get_decl_pair(self):
        return self.subdecl.get_decl_pair()


class DeclSpecifier(NestedDeclarator):
    def __init__(self, subdecl, spec, sep=' '):
        NestedDeclarator.__init__(self, subdecl)
        self.spec = spec
        self.sep = sep

    def get_decl_pair(self):
        def add_spec(sub_it):
            it = iter(sub_it)
            try:
                yield "%s%s%s" % (self.spec, self.sep, it.next())
            except StopIteration:
                pass

            for line in it:
                yield line

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return add_spec(sub_tp), sub_decl


class NamespaceQualifier(DeclSpecifier):
    def __init__(self, namespace, subdecl):
        DeclSpecifier.__init__(self, subdecl, namespace, '::')


class Typedef(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "typedef")


class Static(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "static")


class Const(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("const %s" % sub_decl)


class FunctionDeclaration(NestedDeclarator):
    def __init__(self, subdecl, arg_decls, *attributes):
        NestedDeclarator.__init__(self, subdecl)
        self.arg_decls = arg_decls
        self.attributes = attributes

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("%s(%s) %s" % (
            sub_decl,
            ", ".join(ad.inline() for ad in self.arg_decls),
            " ".join(self.attributes))
            )


class Struct(Declarator):
    """A structure declarator."""

    def __init__(self, tpname, fields):
        """Initialize the structure declarator.
        *tpname* is the name of the structure.
        *fields* is a list of :class:`Declarator` instances.
        """
        self.tpname = tpname
        self.fields = fields

    def get_decl_pair(self):
        def get_tp():
            if self.tpname is not None:
                yield "struct %s" % self.tpname
            else:
                yield "struct"
            yield "{"
            for f in self.fields:
                for f_line in f.generate():
                    yield "  " + f_line
            yield "} "
        return get_tp(), ""


# template --------------------------------------------------------------------
class Template(NestedDeclarator):
    def __init__(self, template_spec, subdecl):
        self.template_spec = template_spec
        self.subdecl = subdecl

    def generate(self, with_semicolon=False):
        yield "template <%s>" % ", ".join(self.template_spec)
        for i in self.subdecl.generate(with_semicolon):
            yield i
        if(not isinstance(self.subdecl, FunctionDeclaration)
                and not isinstance(self.subdecl, Template)):
            yield ";"


# control flow/statement stuff ------------------------------------------------
class ExceptHandler(Generable):
    def __init__(self, name, body, alias=None):
        self.name = name
        assert isinstance(body, Generable)
        self.body = body
        self.alias = alias

    def generate(self):
        if self.name is None:
            yield "catch(...)"
        else:
            yield "catch (pythonic::types::%s const& %s)" % (self.name,
                                                             self.alias or '')
        for line in self.body.generate():
            yield line


class TryExcept(Generable):
    def __init__(self, try_, except_, else_=None):
        self.try_ = try_
        assert isinstance(try_, Generable)
        self.except_ = except_

    def generate(self):
        yield "try"

        for line in self.try_.generate():
            yield line

        for exception in self.except_:
            for line in exception.generate():
                yield "  " + line


class If(Generable):
    def __init__(self, condition, then_, else_=None):
        self.condition = condition

        assert isinstance(then_, Generable)
        if else_ is not None:
            assert isinstance(else_, Generable)

        self.then_ = then_
        self.else_ = else_

    def generate(self):
        yield "if (%s)" % self.condition

        for line in self.then_.generate():
            yield line

        if self.else_ is not None:
            yield "else"
            for line in self.else_.generate():
                yield line


class Loop(Generable):
    def __init__(self, body):
        self.body = body

    def generate(self):
        if self.intro_line() is not None:
            yield self.intro_line()

        for line in self.body.generate():
            yield line


class While(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return "while (%s)" % self.condition


class For(Loop):
    def __init__(self, start, condition, update, body):
        self.start = start
        self.condition = condition
        self.update = update

        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return "for (%s; %s; %s)" % (self.start, self.condition, self.update)


class AutoFor(Loop):
    def __init__(self, target, iter, body):
        self.target = target
        self.iter = iter

        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return ("for (typename decltype({1})::iterator::reference "
                "{0}: {1})".format(self.target,
                                   self.iter))


# simple statements -----------------------------------------------------------
class Define(Generable):
    def __init__(self, symbol, value):
        self.symbol = symbol
        self.value = value

    def generate(self):
        yield "#define %s %s" % (self.symbol, self.value)


class Include(Generable):
    def __init__(self, filename, system=True):
        self.filename = filename
        self.system = system

    def generate(self):
        if self.system:
            yield "#include <%s>" % self.filename
        else:
            yield "#include \"%s\"" % self.filename


class Statement(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield self.text + ";"


class AnnotatedStatement(Generable):
    def __init__(self, stmt, annotations):
        self.stmt = stmt
        self.annotations = annotations

    def generate(self):
        for directive in self.annotations:
            pragma = "#pragma " + directive.s
            yield pragma.format(*directive.deps)
        for s in self.stmt.generate():
            yield s


class ReturnStatement(Statement):
    def generate(self):
        yield "return " + self.text + ";"


class EmptyStatement(Statement):
    def __init__(self):
        Statement.__init__(self, "")


class Assign(Generable):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

    def generate(self):
        yield "%s = %s;" % (self.lvalue, self.rvalue)


class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text


# initializers ----------------------------------------------------------------
class FunctionBody(Generable):
    def __init__(self, fdecl, body):
        """Initialize a function definition. *fdecl* is expected to be
        a :class:`FunctionDeclaration` instance, while *body* is a
        :class:`Block`.
        """
        self.fdecl = fdecl
        self.body = body

    def generate(self):
        for f_line in self.fdecl.generate(with_semicolon=False):
            yield f_line
        for b_line in self.body.generate():
            yield b_line


# block -----------------------------------------------------------------------
class Block(Generable):
    def __init__(self, contents=[]):
        self.contents = contents[:]
        for item in self.contents:
            assert isinstance(item, Generable), item

    def generate(self):
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield "  " + item_line
        yield "}"


class Module(Block):
    def generate(self):
        for c in self.contents:
            for line in c.generate():
                yield line


class Namespace(Block):
    def __init__(self, name, contents=[]):
        Block.__init__(self, contents)
        self.name = name

    def generate(self):
        yield "namespace " + self.name
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield "  " + item_line
        yield "}"


# copy-pasted from codepy.bpl, which is a real mess...
# the original code was under MIT License
# cf. http://pypi.python.org/pypi/codepy
# so I reproduce it here
#
# Copyright (C) 2008 Andreas Kloeckner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

class BoostPythonModule(object):
    def __init__(self, name="module", max_arity=None):
        self.name = name
        self.preamble = []
        self.mod_body = []
        self.init_body = []

    def add_to_init(self, body):
        """Add the blocks or statements contained in the iterable *body* to the
        module initialization function.
        """
        self.init_body.extend(body)

    def add_to_preamble(self, pa):
        self.preamble.extend(pa)

    def add_function(self, func, name=None):
        """Add a function to be exposed. *func* is expected to be a
        :class:`cgen.FunctionBody`.
        """
        if not name:
            name = func.fdecl.name

        self.mod_body.append(func)
        self.init_body.append(
            Statement("boost::python::def(\"%s\", &%s)" % (name,
                                                           func.fdecl.name)))

    def generate(self):
        """Generate (i.e. yield) the source code of the
        module line-by-line.
        """
        body = (self.preamble + [Line()]
                + self.mod_body
                + [Line(), Line("BOOST_PYTHON_MODULE(%s)" % self.name)]
                + [Block(self.init_body)])

        return Module(body)

    def __str__(self):
        return str(self.generate())


class CompilationUnit(object):

    def __init__(self, body):
        self.body = body

    def __str__(self):
        return '\n'.join('\n'.join(s.generate()) for s in self.body)

########NEW FILE########
__FILENAME__ = cxxtypes
'''
This module defines classes needed to manipulate c++ types from pythran.
'''
import tables
from config import cfg


class Weak:
    """
    Type Qualifier used to represent a weak type

    When a weak type is combined with another type, the weak type is suppressed
    """
    pass


class Type(object):
    """
    A generic type object to be sub-classed

    It maintains a set of qualifiers and
    a tuple of fields used for type comparison.

    The keyword arguments are used to built the internal representation:
    one attribute per key with the associated value
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self.qualifiers = self.qualifiers.copy()  # avoid sharing
        self.fields = tuple(sorted(kwargs.keys()))

    def isweak(self):
        return Weak in self.qualifiers

    def all_types(self):
        return {self}

    def __eq__(self, other):
        havesameclass = self.__class__ == other.__class__
        if havesameclass:
            same = lambda x, y: getattr(self, x) == getattr(other, y)
            return all(same(x, y) for x, y in zip(self.fields, other.fields))
        else:
            return False

    def __add__(self, other):
        if self.isweak() and not other.isweak():
            return other
        if other.isweak() and not self.isweak():
            return self
        if self == other:
            return self
        if isinstance(other, CombinedTypes) and self in other.types:
            return other
        return CombinedTypes([self, other])

    def __repr__(self):
        return self.generate(lambda x: x)


class NamedType(Type):
    """
    A generic type object, to hold scalar types and such

    >>> NamedType('long long')
    long long
    """
    def __init__(self, repr, qualifiers=set()):
        super(NamedType, self).__init__(repr=repr, qualifiers=qualifiers)

    def generate(self, ctx):
        return self.repr


class PType(Type):
    """
    A generic parametric type
    """

    prefix = "__ptype{0}"
    count = 0

    def __init__(self, fun, type):
        super(PType, self).__init__(fun=fun,
                                    type=type,
                                    qualifiers=type.qualifiers,
                                    name=PType.prefix.format(PType.count))
        PType.count += 1

    def generate(self, ctx):
        return ctx(self.type).generate(ctx)

    def instanciate(self, caller, arguments):
        return InstanciatedType(self.fun,
                                self.name,
                                arguments,
                                caller,
                                self.qualifiers)


class InstanciatedType(Type):
    """
    A type instanciated from a parametric type
    """
    def __init__(self, fun, name, arguments, caller, qualifiers):
        super(InstanciatedType, self).__init__(fun=fun,
                                               name=name,
                                               arguments=arguments,
                                               qualifiers=qualifiers)
        if fun == caller:
            self.qualifiers.add(Weak)

    def generate(self, ctx):
        if self.arguments:
            args = ", ".join(ctx(arg).generate(ctx) for arg in self.arguments)
            template_params = "<{0}>".format(args)
        else:
            template_params = ""

        return "typename {0}::type{1}::{2}".format(self.fun.name,
                                                   template_params,
                                                   self.name)


class CombinedTypes(Type):
    """
    type resulting from the combination of other types

    >>> NamedType('long') + NamedType('long')
    long
    >>> NamedType('long') + NamedType('char')
    typename __combined<char,long>::type
    """

    def __init__(self, types):
        super(CombinedTypes, self).__init__(
            types=types,
            qualifiers=set.union(*[t.qualifiers for t in types])
            )

    def __add__(self, other):
        if isinstance(other, CombinedTypes):
            return CombinedTypes([self, other])
        if other in self.types:
            return self
        if other.isweak() and not self.isweak():
            return self
        if self == other:
            return self
        return CombinedTypes([self, other])

    def all_types(self):
        out = set()
        for t in self.types:
            out.update(t.all_types())
        return out

    def generate(self, ctx):
        # gather all underlying types and make sure they do not appear twice
        mct = cfg.getint('typing', 'max_container_type')
        all_types = self.all_types()
        fot0 = lambda t:  type(t) is IndexableType
        fot1 = lambda t: type(t) is ContainerType
        fit = lambda t: not fot0(t) and not fot1(t)
        it = filter(fit, all_types)
        ot0 = filter(fot0, all_types)
        ot1 = filter(fot1, all_types)
        icombined = sorted(set(ctx(t).generate(ctx) for t in it))
        lcombined0 = sorted(set(ctx(t).generate(ctx) for t in ot0))[-mct:]
        lcombined1 = sorted(set(ctx(t).generate(ctx) for t in ot1))[-mct:]
        combined = icombined + lcombined0 + lcombined1
        if len(combined) == 1:
            return combined[0]
        else:
            return 'typename __combined<{0}>::type'.format(",".join(combined))


class ArgumentType(Type):
    """
    A type to hold function arguments

    >>> ArgumentType(4)
    typename std::remove_cv<\
typename std::remove_reference<argument_type4>::type>::type
    """
    def __init__(self, num, qualifiers=set()):
        super(ArgumentType, self).__init__(num=num,
                                           qualifiers=qualifiers)

    def generate(self, ctx):
        argtype = "argument_type{0}".format(self.num)
        noref = "typename std::remove_reference<{0}>::type".format(argtype)
        return "typename std::remove_cv<{0}>::type".format(noref)


class DependentType(Type):
    """
    A class to be sub-classed by any type that depends on another type
    """
    def __init__(self, of):
        super(DependentType, self).__init__(of=of,
                                            qualifiers=of.qualifiers)


class Assignable(DependentType):
    """
    A type which can be assigned

    It is used to make the difference between
    * transient types (e.g. generated from expression template)
    * assignable types (typically type of a variable)

    >>> Assignable(NamedType("long"))
    typename pythonic::assignable<long>::type
    """

    def generate(self, ctx):
        return 'typename pythonic::assignable<{0}>::type'.format(
            self.of.generate(ctx))


class Lazy(DependentType):
    """
    A type which can be a reference

    It is used to make a lazy evaluation of numpy expressions

    >>> Lazy(NamedType("long"))
    typename pythonic::lazy<long>::type
    """

    def generate(self, ctx):
        return 'typename pythonic::lazy<{0}>::type'.format(
            self.of.generate(ctx))


class DeclType(NamedType):
    """
    Gather the type of a variable

    >>> DeclType("toto")
    typename std::remove_cv<\
typename std::remove_reference<decltype(toto)>::type>::type
    """

    def generate(self, ctx):
        return ('typename std::remove_cv<'
                'typename std::remove_reference<'
                'decltype({0})>::type>::type'.format(self.repr))


class ContentType(DependentType):
    '''
    Type of the object in a container

    >>> ContentType(DeclType('l'))
    typename pythonic::types::content_of<typename std::remove_cv<\
typename std::remove_reference<decltype(l)>::type>::type>::type
    '''

    def generate(self, ctx):
        # the content of a container can be inferred directly
        if type(self.of) in (ListType, SetType, ContainerType):
            return self.of.of.generate(ctx)
        return 'typename pythonic::types::content_of<{0}>::type'.format(
            ctx(self.of).generate(ctx))


class IteratorContentType(DependentType):
    '''
    Type of an iterator over the content of a container

    >>> IteratorContentType(NamedType('str'))
    typename std::remove_cv<typename std::iterator_traits<\
typename std::remove_reference<str>::type::iterator>::value_type>::type
    '''

    def generate(self, ctx):
        # special hook to avoid delegating this trivial computation to c++
        if type(self.of) is ReturnType and type(self.of.ftype) is DeclType:
            if self.of.ftype.repr == '__builtin__::proxy::xrange()':
                return ctx(NamedType('long')).generate(ctx)
        iterator_value_type = ctx(self.of).generate(ctx)
        return 'typename std::remove_cv<{0}>::type'.format(
            'typename std::iterator_traits<{0}>::value_type'.format(
                'typename std::remove_reference<{0}>::type::iterator'.format(
                    iterator_value_type)
                )
            )


class GetAttr(Type):
    '''
    Type of a named attribute

    >>> GetAttr(NamedType('complex'), 'real')
    decltype(pythonic::__builtin__::getattr<pythonic::types::attr::real>\
(std::declval<complex>()))
    '''
    def __init__(self, param, attr):
        super(GetAttr, self).__init__(
            qualifiers=param.qualifiers,
            param=param,
            attr=attr)

    def generate(self, ctx):
        return ('decltype(pythonic::__builtin__::getattr<{}>({}))'
                .format('pythonic::types::attr::' + self.attr,
                        'std::declval<' + self.param.generate(ctx) + '>()'))


class ReturnType(Type):
    '''
    Return type of a call with arguments

    >>> ReturnType(NamedType('math::cos'), [NamedType('float')])
    decltype(std::declval<math::cos>()(std::declval<float>()))
    '''
    def __init__(self, ftype, args):
        args_qualifiers = [arg.qualifiers for arg in args]
        super(ReturnType, self).__init__(
            qualifiers=ftype.qualifiers.union(*args_qualifiers),
            ftype=ftype,
            args=args)

    def generate(self, ctx):
        # the return type of a constructor is obvious
        cg = self.ftype.generate(ctx)
        cg = 'std::declval<{0}>()'.format(cg)
        args = ("std::declval<{0}>()".format(ctx(arg).generate(ctx))
                for arg in self.args)
        return 'decltype({0}({1}))'.format(cg, ", ".join(args))


class ElementType(Type):
    '''
    Type of the ith element of a tuple or container

    >>> t = TupleType([NamedType('int'), NamedType('str')])
    >>> ElementType(1, t)
    typename std::tuple_element<1,typename std::remove_reference<\
decltype(pythonic::types::make_tuple(std::declval<int>(), \
std::declval<str>()))>::type>::type
    '''

    def __init__(self, index, of):
        super(ElementType, self).__init__(qualifiers=of.qualifiers,
                                          of=of,
                                          index=index)

    def generate(self, ctx):
        return 'typename std::tuple_element<{0},{1}>::type'.format(
            self.index,
            'typename std::remove_reference<{0}>::type'.format(
                ctx(self.of).generate(ctx)
                )
            )


class ListType(DependentType):
    '''
    Type holding a list of stuff of the same type

    >>> ListType(NamedType('int'))
    pythonic::types::list<int>
    '''

    def generate(self, ctx):
        return 'pythonic::types::list<{0}>'.format(ctx(self.of).generate(ctx))


class SetType(DependentType):
    '''
    Type holding a set of stuff of the same type

    >>> SetType(NamedType('int'))
    pythonic::types::set<int>
    '''

    def generate(self, ctx):
        return 'pythonic::types::set<{0}>'.format(ctx(self.of).generate(ctx))


class TupleType(Type):
    '''
    Type holding a tuple of stuffs of various types

    >>> TupleType([NamedType('int'), NamedType('bool')])
    decltype(pythonic::types::make_tuple(std::declval<int>(), \
std::declval<bool>()))
    '''
    def __init__(self, ofs):
        if ofs:
            qualifiers = set.union(*[of.qualifiers for of in ofs])
        else:
            qualifiers = set()

        super(TupleType, self).__init__(ofs=ofs, qualifiers=qualifiers)

    def generate(self, ctx):
        elts = (ctx(of).generate(ctx) for of in self.ofs)
        telts = ('std::declval<{0}>()'.format(elt) for elt in elts)
        return 'decltype(pythonic::types::make_tuple({0}))'.format(
            ", ".join(telts))


class DictType(Type):
    '''
    Type holding a dict of stuff of the same key and value type

    >>> DictType(NamedType('int'), NamedType('float'))
    pythonic::types::dict<int,float>
    '''

    def __init__(self, of_key, of_value):
        super(DictType, self).__init__(
            qualifiers=of_key.qualifiers.union(of_value.qualifiers),
            of_key=of_key,
            of_value=of_value
            )

    def generate(self, ctx):
        return 'pythonic::types::dict<{0},{1}>'.format(
            ctx(self.of_key).generate(ctx),
            ctx(self.of_value).generate(ctx))


class ContainerType(DependentType):
    '''
    Type of any container of stuff of the same type

    >>> ContainerType(NamedType('int'))
    container<typename std::remove_reference<int>::type>
    '''

    def generate(self, ctx):
        return 'container<typename std::remove_reference<{0}>::type>'.format(
            ctx(self.of).generate(ctx))


class IndexableType(DependentType):
    '''
    Type of any container indexed by the same type

    >>> IndexableType(NamedType('int'))
    indexable<int>
    '''

    def generate(self, ctx):
        return 'indexable<{0}>'.format(ctx(self.of).generate(ctx))


class ExpressionType(Type):
    '''
    Result type of an operator call

    >>> op = lambda x,y: x + '+' + y
    >>> ExpressionType(op, [NamedType('long'), NamedType('int')])
    decltype(std::declval<long>()+std::declval<int>())
    '''
    def __init__(self, op, exprs):
        super(ExpressionType, self).__init__(
            qualifiers=set.union(*[expr.qualifiers for expr in exprs]),
            op=op,
            exprs=exprs)

    def generate(self, ctx):
        texprs = (ctx(expr).generate(ctx) for expr in self.exprs)
        return 'decltype({0})'.format(
            self.op(*["std::declval<{0}>()".format(t) for t in texprs]))

########NEW FILE########
__FILENAME__ = frontend
"""
    This module contains pythran frontend
"""
import ast
import re
from openmp import GatherOMPData
from syntax import check_syntax
from transformations import ExtractTopLevelStmts, NormalizeIdentifiers


def parse(pm, code):
    # hacky way to turn OpenMP comments into strings
    code = re.sub(r'(\s*)#\s*(omp\s[^\n]+)', r'\1"\2"', code)

    # front end
    ir = ast.parse(code)

    # remove top - level statements
    pm.apply(ExtractTopLevelStmts, ir)

    # parse openmp directive
    pm.apply(GatherOMPData, ir)

    # avoid conflicts with cxx keywords
    renamings = pm.apply(NormalizeIdentifiers, ir)
    check_syntax(ir)
    return ir, renamings

########NEW FILE########
__FILENAME__ = intrinsic
'''
This module contains all classes used to model intrinsics behavior.
'''


class UpdateEffect(object):
    pass


class ReadEffect(object):
    pass


class ReadOnceEffect(ReadEffect):
    pass


class Intrinsic(object):
    def __init__(self, **kwargs):
        self.argument_effects = kwargs.get('argument_effects',
                                           (UpdateEffect(),) * 11)
        self.global_effects = kwargs.get('global_effects', False)
        self.return_alias = kwargs.get('return_alias', lambda x: {None})

    def isliteral(self):
        return False

    def isfunction(self):
        return False

    def isstaticfunction(self):
        return False

    def ismethod(self):
        return False

    def isattribute(self):
        return False

    def isconst(self):
        return not any(
            isinstance(x, UpdateEffect) for x in self.argument_effects
            ) and not self.global_effects

    def isreadonce(self, n):
        return isinstance(self.argument_effects[n], ReadOnceEffect)

    def combiner(self, s, node):
        pass


class FunctionIntr(Intrinsic):
    def __init__(self, **kwargs):
        kwargs.setdefault('combiners', ())
        super(FunctionIntr, self).__init__(**kwargs)
        self.combiners = kwargs['combiners']

    def isfunction(self):
        return True

    def isstaticfunction(self):
        return True

    def add_combiner(self, _combiner):
        self.combiners += (_combiner,)

    def combiner(self, s, node):
        for comb in self.combiners:
            comb(s, node)


class UserFunction(FunctionIntr):
    def __init__(self, *combiners, **kwargs):
        kwargs.setdefault('return_alias', lambda x: {None})
        kwargs['combiners'] = combiners
        super(UserFunction, self).__init__(**kwargs)


class ConstFunctionIntr(FunctionIntr):
    def __init__(self, **kwargs):
        kwargs.setdefault('argument_effects',
                          (ReadEffect(),) * 10)
        super(ConstFunctionIntr, self).__init__(**kwargs)


class ConstExceptionIntr(FunctionIntr):
    def __init__(self, **kwargs):
        kwargs.setdefault('argument_effects',
                          (ReadEffect(),) * 10)
        super(ConstExceptionIntr, self).__init__(**kwargs)


class ReadOnceFunctionIntr(ConstFunctionIntr):
    def __init__(self):
        super(ReadOnceFunctionIntr, self).__init__(
            argument_effects=(ReadOnceEffect(),) * 11)


class MethodIntr(FunctionIntr):
    def __init__(self, *combiners, **kwargs):
        kwargs.setdefault('argument_effects',
                          (UpdateEffect(),) + (ReadEffect(),) * 10)
        kwargs['combiners'] = combiners
        super(MethodIntr, self).__init__(**kwargs)

    def ismethod(self):
        return True

    def isstaticfunction(self):
        return False


class ConstMethodIntr(MethodIntr):
    def __init__(self, *combiners):
        super(ConstMethodIntr, self).__init__(
            *combiners,
            argument_effects=(ReadEffect(),) * 12)


class AttributeIntr(Intrinsic):
    def __init__(self, val):
        self.val = val
        super(AttributeIntr, self).__init__()

    def isattribute(self):
        return True


class ConstantIntr(Intrinsic):
    def __init__(self):
        super(ConstantIntr, self).__init__(argument_effects=())

    def isliteral(self):
        return True


class Class(Intrinsic):
    def __init__(self, d):
        super(Class, self).__init__()
        self.d = d

    def __getitem__(self, key):
        return self.d[key]

########NEW FILE########
__FILENAME__ = metadata
'''
This module provides a way to pass information between passes as metadata.
    * add attaches a metadata to a node
    * get retrieves all metadata from a particular class attached to a node
'''

from ast import AST  # so that metadata are walkable as regular ast nodes


class Metadata(AST):
    def __init__(self):
        self.data = list()
        self._fields = ('data',)

    def __iter__(self):
        return iter(self.data)

    def append(self, data):
        self.data.append(data)


class LocalVariable(AST):
    pass


class Lazy(AST):
    pass


class Comprehension(AST):
    def __init__(self, *args):  # no positional argument to be deep copyable
        if args:
            self.target = args[0]


def add(node, data):
    if not hasattr(node, 'metadata'):
        setattr(node, 'metadata', Metadata())
        node._fields += ('metadata',)
    getattr(node, 'metadata').append(data)


def get(node, class_):
    if hasattr(node, 'metadata'):
        return [s for s in getattr(node, 'metadata') if isinstance(s, class_)]
    else:
        return []


def visit(self, node):
    if hasattr(node, 'metadata'):
        self.visit(node.metadata)

########NEW FILE########
__FILENAME__ = middlend
'''
This module turns a python AST into an optimized, pythran compatible ast
'''

from optimizations import GenExpToImap, ListCompToMap, ListCompToGenexp
from transformations import (ExpandBuiltins, ExpandImports, ExpandImportAll,
                             FalsePolymorphism, NormalizeCompare,
                             NormalizeException, NormalizeMethodCalls,
                             NormalizeReturn, NormalizeTuples,
                             RemoveComprehension, RemoveNestedFunctions,
                             RemoveLambdas, UnshadowParameters)


def refine(pm, node, optimizations):
    """refine node in place until it matches pythran's expectations"""

    # sanitize input
    pm.apply(ExpandImportAll, node)
    pm.apply(NormalizeTuples, node)
    pm.apply(ExpandBuiltins, node)
    pm.apply(ExpandImports, node)
    pm.apply(NormalizeException, node)
    pm.apply(NormalizeMethodCalls, node)

    #Some early optimizations
    pm.apply(ListCompToMap, node)
    pm.apply(GenExpToImap, node)

    pm.apply(NormalizeTuples, node)
    pm.apply(RemoveLambdas, node)
    pm.apply(NormalizeCompare, node)
    pm.apply(RemoveNestedFunctions, node)
    pm.apply(ListCompToGenexp, node)
    pm.apply(RemoveComprehension, node)

    # sanitize input
    pm.apply(NormalizeTuples, node)
    pm.apply(RemoveNestedFunctions, node)
    pm.apply(NormalizeReturn, node)
    pm.apply(UnshadowParameters, node)
    pm.apply(FalsePolymorphism, node)

    # some extra optimizations
    for optimization in optimizations:
        pm.apply(optimization, node)

########NEW FILE########
__FILENAME__ = openmp
'''
This modules contains OpenMP-related stuff.
    * OMPDirective is used to represent OpenMP annotations in the AST
    * GatherOMPData turns OpenMP-like string annotations into metadata
'''

import metadata
from ast import AST
import ast
import re
from passmanager import Transformation

keywords = {
    'atomic',
    'barrier',
    'capture',
    'collapse',
    'copyin',
    'copyprivate',
    'critical',
    'default',
    'final',
    'firstprivate',
    'flush',
    'for',
    'if',
    'lastprivate',
    'master',
    'mergeable',
    'none',
    'nowait',
    'num_threads',
    'omp',
    'ordered',
    'parallel',
    'private',
    'read',
    'reduction',
    'schedule',
    'section',
    'sections',
    'shared',
    'single',
    'task',
    'taskwait',
    'taskyield',
    'threadprivate',
    'untied',
    'update',
    'write'
}

reserved_contex = {
    'default',
    'schedule',
}


class OMPDirective(AST):
    '''Turn a string into a context-dependent metadata.
    >>> o = OMPDirective("omp for private(a,b) shared(c)")
    >>> o.s
    'omp for private({},{}) shared({})'
    >>> [ type(dep) for dep in o.deps ]
    [<class '_ast.Name'>, <class '_ast.Name'>, <class '_ast.Name'>]
    >>> [ dep.id for dep in o.deps ]
    ['a', 'b', 'c']
    '''

    def __init__(self, *args):  # no positional argument to be deep copyable
        if not args:
            return

        self.deps = []

        def tokenize(s):
            '''A simple contextual "parser" for an OpenMP string'''
            # not completely satisfying if there are strings in if expressions
            out = ''
            par_count = 0
            curr_index = 0
            in_reserved_context = False
            while curr_index < len(s):
                m = re.match('^([a-zA-Z_]\w*)', s[curr_index:])
                if m:
                    word = m.group(0)
                    curr_index += len(word)
                    if (in_reserved_context
                            or (par_count == 0 and word in keywords)):
                        out += word
                        in_reserved_context = word in reserved_contex
                    else:
                        v = '{}'
                        self.deps.append(ast.Name(word, ast.Load()))
                        out += v
                elif s[curr_index] == '(':
                    par_count += 1
                    curr_index += 1
                    out += '('
                elif s[curr_index] == ')':
                    par_count -= 1
                    curr_index += 1
                    out += ')'
                    if par_count == 0:
                        in_reserved_context = False
                else:
                    if s[curr_index] == ',':
                        in_reserved_context = False
                    out += s[curr_index]
                    curr_index += 1
            return out

        self.s = tokenize(args[0])
        self._fields = ('deps',)


##
class GatherOMPData(Transformation):
    '''Walks node and collect string comments looking for OpenMP directives.'''

    # there is a special handling for If and Expr, so not listed here
    statements = ("FunctionDef", "Return", "Delete", "Assign", "AugAssign",
                  "Print", "For", "While", "Raise", "TryExcept", "TryFinally",
                  "Assert", "Import", "ImportFrom", "Pass", "Break",)

    # these fields hold statement lists
    statement_lists = ("body", "orelse", "finalbody",)

    def __init__(self):
        Transformation.__init__(self)
        # Remap self.visit_XXXX() to self.attach_data() generic method
        for s in GatherOMPData.statements:
            setattr(self, "visit_" + s, lambda node_: self.attach_data(node_))
        self.current = list()

    def isompdirective(self, node):
        return isinstance(node, ast.Str) and node.s.startswith("omp ")

    def visit_Expr(self, node):
        if self.isompdirective(node.value):
            self.current.append(node.value.s)
            return None
        else:
            self.attach_data(node)
            return node

    def visit_If(self, node):
        if self.isompdirective(node.test):
            self.visit(ast.Expr(node.test))
            return self.visit(ast.If(ast.Num(1), node.body, node.orelse))
        else:
            return self.attach_data(node)

    def attach_data(self, node):
        '''Generic method called for visit_XXXX() with XXXX in
        GatherOMPData.statements list

        '''
        if self.current:
            for curr in self.current:
                md = OMPDirective(curr)
                metadata.add(node, md)
            self.current = list()
        # add a Pass to hold some directives
        for field_name, field in ast.iter_fields(node):
            if field_name in GatherOMPData.statement_lists:
                if (field
                        and isinstance(field[-1], ast.Expr)
                        and self.isompdirective(field[-1].value)):
                    field.append(ast.Pass())
        self.generic_visit(node)

        # add an If to hold scoping OpenMP directives
        directives = metadata.get(node, OMPDirective)
        field_names = {n for n, _ in ast.iter_fields(node)}
        has_no_scope = field_names.isdisjoint(GatherOMPData.statement_lists)
        if directives and has_no_scope:
            # some directives create a scope, but the holding stmt may not
            # artificially create one here if needed
            sdirective = ''.join(d.s for d in directives)
            scoping = ('parallel', 'task', 'section')
            if any(s in sdirective for s in scoping):
                node = ast.If(ast.Num(1), [node], [])
        return node

########NEW FILE########
__FILENAME__ = constant_folding
"""
ConstantFolding performs some kind of partial evaluation.
"""
import ast
from pythran.analyses import ConstantExpressions
from pythran.passmanager import Transformation
from pythran.tables import modules
from pythran.transformations import NormalizeTuples


class ConstantFolding(Transformation):
    '''
    Replace constant expression by their evaluation.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(): return 1+3")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ConstantFolding, node)
    >>> print pm.dump(backend.Python, node)
    def foo():
        return 4
    '''

    # maximum length of folded sequences
    # containers larger than this are not unfolded to limit code size growth
    MAX_LEN = 2 ** 8

    class ConversionError(Exception):
        pass

    def __init__(self):
        Transformation.__init__(self, ConstantExpressions)

    def prepare(self, node, ctx):
        self.env = {'__builtin__': __import__('__builtin__')}

        for module_name in modules:
            not_builtin = ["__builtin__", "__exception__", "__dispatch__",
                           "__iterator__"]
            # module starting with "__" are pythran internal module and
            # should not be imported in the Python interpreter
            if not module_name.startswith('__'):
                import_name = module_name
                if module_name == "operator_":
                    import_name = "operator"
                self.env[module_name] = __import__(import_name)
            elif module_name not in not_builtin:
                try:
                    self.env[module_name] = __import__(module_name.strip('_'))
                except:
                    try:
                        # should try from another package than builtin,
                        # e.g. for ndarray
                        self.env[module_name] = getattr(
                            self.env['__builtin__'],
                            module_name.strip('_'))
                    except:
                        pass

        try:
            eval(compile(node, '<constant_folding>', 'exec'), self.env)
        except Exception as e:
            print ast.dump(node)
            print 'error in constant folding: ', e
            pass
        super(ConstantFolding, self).prepare(node, ctx)

    def to_ast(self, value):
        if (type(value) in (int, long, float, complex)):
            return ast.Num(value)
        elif isinstance(value, bool):
            return ast.Attribute(ast.Name('__builtin__', ast.Load()),
                                 'True' if value else 'False', ast.Load())
        elif isinstance(value, str):
            return ast.Str(value)
        elif isinstance(value, list) and len(value) < ConstantFolding.MAX_LEN:
            #SG: unsure whether it Load or something else
            return ast.List(map(self.to_ast, value), ast.Load())
        elif isinstance(value, tuple) and len(value) < ConstantFolding.MAX_LEN:
            return ast.Tuple(map(self.to_ast, value), ast.Load())
        elif isinstance(value, set) and len(value) < ConstantFolding.MAX_LEN:
            return ast.Set(map(self.to_ast, value))
        elif isinstance(value, dict) and len(value) < ConstantFolding.MAX_LEN:
            keys = map(self.to_ast, value.iterkeys())
            values = map(self.to_ast, value.itervalues())
            return ast.Dict(keys, values)
        else:
            raise ConstantFolding.ConversionError()

    def generic_visit(self, node):
        if node in self.constant_expressions:
            try:
                fake_node = ast.Expression(
                    node.value if isinstance(node, ast.Index) else node)
                code = compile(fake_node, '<constant folding>', 'eval')
                value = eval(code, self.env)
                new_node = self.to_ast(value)
                if (isinstance(node, ast.Index)
                        and not isinstance(new_node, ast.Index)):
                    new_node = ast.Index(new_node)
                return new_node
            except Exception:  # as e:
                #print ast.dump(node)
                #print 'error in constant folding: ', e
                return Transformation.generic_visit(self, node)
        else:
            return Transformation.generic_visit(self, node)

########NEW FILE########
__FILENAME__ = dead_code_elimination
"""
DeadCodeElimination remove useless code
"""
import ast
from pythran.analyses import PureExpressions, UseDefChain

from pythran.passmanager import Transformation


class DeadCodeElimination(Transformation):
    """
        Remove useless statement like:
            - assignment to unused variables
            - remove alone pure statement

        >>> import ast, passmanager, backend
        >>> pm = passmanager.PassManager("test")
        >>> node = ast.parse("def foo(): a = [2, 3]; return 1")
        >>> node = pm.apply(DeadCodeElimination, node)
        >>> print pm.dump(backend.Python, node)
        def foo():
            pass
            return 1
        >>> node = ast.parse("def foo(): 'a simple string'; return 1")
        >>> node = pm.apply(DeadCodeElimination, node)
        >>> print pm.dump(backend.Python, node)
        def foo():
            pass
            return 1
        >>> node = ast.parse('''
        ... def bar(a):
        ...     return a
        ... def foo(a):
        ...    bar(a)
        ...    return 1''')
        >>> node = pm.apply(DeadCodeElimination, node)
        >>> print pm.dump(backend.Python, node)
        def bar(a):
            return a
        def foo(a):
            pass
            return 1
    """
    def __init__(self):
        super(DeadCodeElimination, self).__init__(PureExpressions,
                                                  UseDefChain)

    def used_target(self, node):
        if isinstance(node, ast.Name):
            udc = self.use_def_chain[node.id]
            is_use = lambda x: udc.node[x]['action'] in ("U", "UD")
            use_count = len(filter(is_use, udc.nodes()))
            return use_count != 0
        return True

    def visit_Assign(self, node):
        node.targets = filter(self.used_target, node.targets)
        if node.targets:
            return node
        elif node.value in self.pure_expressions:
            return ast.Pass()
        else:
            return ast.Expr(value=node.value)

    def visit_Expr(self, node):
        if (node in self.pure_expressions and
                not isinstance(node.value, ast.Yield)):
            return ast.Pass()
        return node

########NEW FILE########
__FILENAME__ = forward_substitution
"""
Replace variable that can be lazy evaluated and used only once by their full
computation code.
"""
import ast
from pythran.analyses import LazynessAnalysis, UseDefChain, Literals
from pythran.passmanager import Transformation


class _LazyRemover(Transformation):
    """
        Helper removing D node and replacing U node by D node assigned value.
        Search value of the D (define) node provided in the constructor (which
        is in an Assign) and replace the U node provided in the constructor too
        by this value.

        Assign Stmt is removed if only one value was assigned.
    """
    def __init__(self, ctx, U, D):
        super(_LazyRemover, self).__init__()
        self.U = U
        self.ctx = ctx
        self.D = D
        self.capture = None

    def visit_Name(self, node):
        if node in self.U:
            return self.capture
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if self.D in node.targets:
            self.capture = node.value
            if len(node.targets) == 1:
                return ast.Pass()
            node.targets.remove(self.D)
        return node


class ForwardSubstitution(Transformation):
    """
        Replace variable that can be lazy evaluated and used only once by their
        full computation code.

        >>> import ast, passmanager, backend
        >>> pm = passmanager.PassManager("test")
        >>> node = ast.parse("def foo(): a = [2, 3]; print a")
        >>> node = pm.apply(ForwardSubstitution, node)
        >>> print pm.dump(backend.Python, node)
        def foo():
            pass
            print [2, 3]
        >>> node = ast.parse("def foo(): a = 2; print a + a")
        >>> node = pm.apply(ForwardSubstitution, node)
        >>> print pm.dump(backend.Python, node)
        def foo():
            pass
            print (2 + 2)
    """
    def __init__(self):
        super(ForwardSubstitution, self).__init__(LazynessAnalysis,
                                                  UseDefChain,
                                                  Literals)

    def visit_FunctionDef(self, node):
        for name, udgraph in self.use_def_chain.iteritems():
            # 1. check if the usedefchains have only two nodes (a def and an
            # use) and if it can be forwarded (lazyness == 1 means variables
            # used to define the variable are not modified and the variable is
            # use only once
            # 2. Check if variable is forwardable and if it is literal
            if ((len(udgraph.nodes()) == 2 and
                 self.lazyness_analysis[name] == 1) or
                (self.lazyness_analysis[name] != float('inf') and
                 name in self.literals)):
                def get(action):
                    return [udgraph.node[n]['name'] for n in udgraph.nodes()
                            if udgraph.node[n]['action'] == action]
                U = get("U")
                D = get("D")
                # we can't forward if multiple definition for a variable are
                # possible or if this variable is a parameter from a function
                if (len(D) == 1 and len(get("UD")) == 0 and
                        not isinstance(D[0].ctx, ast.Param)):
                    node = _LazyRemover(self.ctx, U, D[0]).visit(node)
        return node

########NEW FILE########
__FILENAME__ = gen_exp_to_imap
"""
GenExpToImap transforms generator expressions into iterators
"""
import ast
from pythran.analyses import OptimizableComprehension
from pythran.passmanager import Transformation
from pythran.transformations import NormalizeTuples


class GenExpToImap(Transformation):
    '''
    Transforms generator expressions into iterators.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("(x*x for x in range(10))")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(GenExpToImap, node)
    >>> print pm.dump(backend.Python, node)
    import itertools
    itertools.imap((lambda x: (x * x)), range(10))
    '''

    def __init__(self):
        Transformation.__init__(self, NormalizeTuples,
                                OptimizableComprehension)

    def visit_Module(self, node):
        self.generic_visit(node)
        importIt = ast.Import(names=[ast.alias(name='itertools', asname=None)])
        node.body.insert(0, importIt)
        return node

    def make_Iterator(self, gen):
        if gen.ifs:
            ldFilter = ast.Lambda(
                ast.arguments([ast.Name(gen.target.id, ast.Param())],
                              None, None, []), ast.BoolOp(ast.And(), gen.ifs))
            ifilterName = ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='ifilter', ctx=ast.Load())
            return ast.Call(ifilterName, [ldFilter, gen.iter], [], None, None)
        else:
            return gen.iter

    def visit_GeneratorExp(self, node):

        if node in self.optimizable_comprehension:

            self.generic_visit(node)

            iters = [self.make_Iterator(gen) for gen in node.generators]
            variables = [ast.Name(gen.target.id, ast.Param())
                         for gen in node.generators]

            # If dim = 1, product is useless
            if len(iters) == 1:
                iterAST = iters[0]
                varAST = ast.arguments([variables[0]], None, None, [])
            else:
                prodName = ast.Attribute(
                    value=ast.Name(id='itertools', ctx=ast.Load()),
                    attr='product', ctx=ast.Load())

                iterAST = ast.Call(prodName, iters, [], None, None)
                varAST = ast.arguments([ast.Tuple(variables, ast.Store())],
                                       None, None, [])

            imapName = ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='imap', ctx=ast.Load())

            ldBodyimap = node.elt
            ldimap = ast.Lambda(varAST, ldBodyimap)

            return ast.Call(imapName, [ldimap, iterAST], [], None, None)

        else:
            return self.generic_visit(node)

########NEW FILE########
__FILENAME__ = iter_transformation
"""
IterTransformation replaces expressions by iterators when possible.
"""
import ast
from pythran.analyses import PotentialIterator, Aliases
from pythran.passmanager import Transformation
from pythran.tables import equivalent_iterators


class IterTransformation(Transformation):
    '''
    Replaces expressions by iterators when possible.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("""                      \\n\
def foo(l):                                       \\n\
    return __builtin__.sum(l)                     \\n\
def bar(n):                                       \\n\
    return foo(__builtin__.range(n)) \
""")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(IterTransformation, node)
    >>> print pm.dump(backend.Python, node)
    import itertools
    def foo(l):
        return __builtin__.sum(l)
    def bar(n):
        return foo(__builtin__.xrange(n))
    '''
    def __init__(self):
        Transformation.__init__(self, PotentialIterator, Aliases)

    def find_matching_builtin(self, node):
        if node.func in self.aliases:
            for k, v in self.aliases.iteritems():
                if (isinstance(k, ast.Attribute)
                        and isinstance(k.value, ast.Name)):
                    if k.value.id == "__builtin__":
                        if self.aliases[node.func].aliases == v.aliases:
                            return k.attr

    def visit_Module(self, node):
        self.generic_visit(node)
        importIt = ast.Import(names=[ast.alias(name='itertools', asname=None)])
        return ast.Module(body=([importIt] + node.body))

    def visit_Call(self, node):
        if node in self.potential_iterator:
            f = self.find_matching_builtin(node)
            if f in equivalent_iterators:
                (ns, new) = equivalent_iterators[f]
                node.func = ast.Attribute(
                    value=ast.Name(id=ns, ctx=ast.Load()),
                    attr=new, ctx=ast.Load())
        return self.generic_visit(node)

########NEW FILE########
__FILENAME__ = list_comp_to_genexp
"""
ListCompToGenexp transforms list comprehension into genexp
"""
import ast
from pythran.analyses import PotentialIterator
from pythran.passmanager import Transformation
from pythran.transformations import NormalizeTuples


class ListCompToGenexp(Transformation):
    '''
    Transforms list comprehension into genexp
    >>> import ast, passmanager, backend
    >>> node = ast.parse("""                      \\n\
def foo(l):                                       \\n\
    return __builtin__.sum(l)                     \\n\
def bar(n):                                       \\n\
    return foo([x for x in __builtin__.range(n)]) \
""")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ListCompToGenexp, node)
    >>> print pm.dump(backend.Python, node)
    def foo(l):
        return __builtin__.sum(l)
    def bar(n):
        return foo((x for x in __builtin__.range(n)))
    '''
    def __init__(self):
        Transformation.__init__(self, NormalizeTuples,
                                PotentialIterator)

    def visit_ListComp(self, node):
        self.generic_visit(node)
        if node in self.potential_iterator:
            return ast.GeneratorExp(node.elt, node.generators)
        else:
            return node

########NEW FILE########
__FILENAME__ = list_comp_to_map
"""
ListCompToMap transforms list comprehension into intrinsics.
"""
import ast
from pythran.analyses import OptimizableComprehension
from pythran.passmanager import Transformation
from pythran.transformations import NormalizeTuples


class ListCompToMap(Transformation):
    '''
    Transforms list comprehension into intrinsics.
    >>> import ast, passmanager, backend
    >>> node = ast.parse("[x*x for x in range(10)]")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ListCompToMap, node)
    >>> print pm.dump(backend.Python, node)
    __builtin__.map((lambda x: (x * x)), range(10))
    '''

    def __init__(self):
        Transformation.__init__(self, NormalizeTuples,
                                OptimizableComprehension)

    def make_Iterator(self, gen):
        if gen.ifs:
            ldFilter = ast.Lambda(
                ast.arguments([ast.Name(gen.target.id, ast.Param())],
                              None, None, []), ast.BoolOp(ast.And(), gen.ifs))
            ifilterName = ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='ifilter', ctx=ast.Load())
            return ast.Call(ifilterName, [ldFilter, gen.iter], [], None, None)
        else:
            return gen.iter

    def visit_ListComp(self, node):

        if node in self.optimizable_comprehension:

            self.generic_visit(node)

            iterList = []
            varList = []

            for gen in node.generators:
                iterList.append(self.make_Iterator(gen))
                varList.append(ast.Name(gen.target.id, ast.Param()))

            # If dim = 1, product is useless
            if len(iterList) == 1:
                iterAST = iterList[0]
                varAST = ast.arguments([varList[0]], None, None, [])
            else:
                prodName = ast.Attribute(
                    value=ast.Name(id='itertools', ctx=ast.Load()),
                    attr='product', ctx=ast.Load())

                iterAST = ast.Call(prodName, iterList, [], None, None)
                varAST = ast.arguments([ast.Tuple(varList, ast.Store())],
                                       None, None, [])

            mapName = ast.Attribute(
                value=ast.Name(id='__builtin__', ctx=ast.Load()),
                attr='map', ctx=ast.Load())

            ldBodymap = node.elt
            ldmap = ast.Lambda(varAST, ldBodymap)

            return ast.Call(mapName, [ldmap, iterAST], [], None, None)

        else:
            return self.generic_visit(node)

########NEW FILE########
__FILENAME__ = loop_full_unrolling
"""
LoopFullUnrolling fully unrolls loops with static bounds
"""
import ast
from copy import deepcopy
from pythran import metadata
from pythran.analyses import HasBreak, HasContinue, NodeCount
from pythran.openmp import OMPDirective
from pythran.passmanager import Transformation


class LoopFullUnrolling(Transformation):
    '''
    Fully unroll loops with static bounds

    >>> import ast, passmanager, backend
    >>> node = ast.parse('for j in [1,2,3]: i += j')
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(LoopFullUnrolling, node)
    >>> print pm.dump(backend.Python, node)
    j = 1
    i += j
    j = 2
    i += j
    j = 3
    i += j
    '''

    MAX_NODE_COUNT = 512

    def visit_For(self, node):
        # first unroll children if needed or possible
        self.generic_visit(node)

        # if the user added some OpenMP directive, trust him and no unroll
        has_omp = metadata.get(node, OMPDirective)
        # a break or continue in the loop prevents unrolling too
        has_break = any(self.passmanager.gather(HasBreak, n, self.ctx)
                        for n in node.body)
        has_cont = any(self.passmanager.gather(HasContinue, n, self.ctx)
                       for n in node.body)
        # do not unroll too much to prevent code growth
        node_count = self.passmanager.gather(NodeCount, node, self.ctx)

        if type(node.iter) is ast.List:
            isvalid = not(has_omp or has_break or has_cont)
            total_count = node_count * len(node.iter.elts)
            issmall = total_count < LoopFullUnrolling.MAX_NODE_COUNT
            if isvalid and issmall:
                def unroll(elt):
                    return ([ast.Assign([deepcopy(node.target)], elt)]
                            + deepcopy(node.body))
                return reduce(list.__add__, map(unroll, node.iter.elts))
        return node

########NEW FILE########
__FILENAME__ = pow2
"""
Replaces **2 by a call to pow2
"""
import ast
from pythran.passmanager import Transformation


class Pow2(Transformation):
    '''
    Replaces **2 by a call to pow2

    >>> import ast, passmanager, backend
    >>> node = ast.parse('a**2')
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(Pow2, node)
    >>> print pm.dump(backend.Python, node)
    __builtin__.pow2(a)
    '''

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if (type(node.op) is ast.Pow
                and type(node.right) is ast.Num
                and node.right.n == 2):
            return ast.Call(
                ast.Attribute(
                    ast.Name('__builtin__', ast.Load()),
                    'pow2',
                    ast.Load()),
                [node.left],
                [],
                None,
                None
                )
        else:
            return node

########NEW FILE########
__FILENAME__ = passmanager
'''
This module provides classes and functions for pass management.
There are two kinds of passes: transformations and analysis.
    * ModuleAnalysis, FunctionAnalysis and NodeAnalysis are to be
      subclassed by any pass that collects information about the AST.
    * gather is used to gather (!) the result of an analyses on an AST node.
    * Backend is to be sub-classed by any pass that dumps the AST content.
    * dump is used to dump (!) the AST using the given backend.
    * Transformation is to be sub-classed by any pass that updates the AST.
    * apply is used to apply (sic) a transformation on an AST node.
'''

import ast
import re


def uncamel(name):
    '''Transforms CamelCase naming convention into C-ish convention'''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class AnalysisContext(object):
    '''
    Class that stores the hierarchy of node visited:
        * parent module
        * parent function
    '''
    def __init__(self):
        self.module = None
        self.function = None


class ContextManager(object):
    '''
    Class to be inherited from to add automatic update of
       AnalysisContext `ctx' to a node visitor.
       The optional analysis dependencies are listed in `dependencies'.
    '''
    def __init__(self, *dependencies):
        self.deps = dependencies
        self.ctx = AnalysisContext()

    def visit(self, node):
        if isinstance(node, ast.Module):
            self.ctx.module = node
        elif isinstance(node, ast.FunctionDef):
            self.ctx.function = node
            for D in self.deps:
                if issubclass(D, FunctionAnalysis):
                    d = D()
                    d.passmanager = self.passmanager
                    d.ctx = self.ctx
                    setattr(self, uncamel(D.__name__), d.run(node, self.ctx))
        return super(ContextManager, self).visit(node)

    def prepare(self, node, ctx):
        '''Gather analysis result required by this analysis'''
        if not self.ctx.module and ctx and ctx.module:
            self.ctx.module = ctx.module
        if not self.ctx.function and ctx and ctx.function:
            self.ctx.function = ctx.function
        for D in self.deps:
            if issubclass(D, ModuleAnalysis):
                rnode = node if isinstance(node, ast.Module) else ctx.module
            elif issubclass(D, FunctionAnalysis):
                if ctx and ctx.function:
                    rnode = ctx.function
                else:
                    continue
            else:
                rnode = node
            d = D()
            d.passmanager = self.passmanager
            setattr(self, uncamel(D.__name__), d.run(rnode, ctx))

    def run(self, node, ctx):
        '''Override this to add special pre or post processing handlers.'''
        self.prepare(node, ctx)
        return self.visit(node)


class Analysis(ContextManager, ast.NodeVisitor):
    '''
    A pass that does not change its content but gathers informations
    about it.
    '''
    def __init__(self, *dependencies):
        '''`dependencies' holds the type of all analysis required by this
            analysis. `self.result' must be set prior to calling this
            constructor.'''
        assert hasattr(self, "result"), (
            "An analysis must have a result attribute when initialized")
        ContextManager.__init__(self, *dependencies)

    def run(self, node, ctx):
        super(Analysis, self).run(node, ctx)
        return self.result

    def display(self, data):
        print data

    def apply(self, node, ctx):
        self.display(self.run(node, ctx))


class ModuleAnalysis(Analysis):
    '''An analysis that operates on a whole module.'''
    pass


class FunctionAnalysis(Analysis):
    '''An analysis that operates on a function.'''
    pass


class NodeAnalysis(Analysis):
    '''An analysis that operates on any node.'''
    pass


class Backend(ModuleAnalysis):
    '''A pass that produces code from an AST.'''
    pass


class Transformation(ContextManager, ast.NodeTransformer):
    '''A pass that updates its content.'''

    def run(self, node, ctx):
        n = super(Transformation, self).run(node, ctx)
        ast.fix_missing_locations(n)
        return n

    def apply(self, node, ctx):
        return self.run(node, ctx)


class PassManager(object):
    '''
    Front end to the pythran pass system.
    '''
    def __init__(self, module_name):
        self.module_name = module_name

    def gather(self, analysis, node, ctx=None):
        '''High-level function to call an `analysis' on a `node', eventually
        using a `ctx'.'''
        assert issubclass(analysis, Analysis)
        a = analysis()
        a.passmanager = self
        return a.run(node, ctx)

    def dump(self, backend, node):
        '''High-level function to call a `backend' on a `node' to generate
        code for module `module_name'.'''
        assert issubclass(backend, Backend)
        b = backend()
        b.passmanager = self
        return b.run(node, None)

    def apply(self, transformation, node, ctx=None):
        '''
        High-level function to call a `transformation' on a `node',
        eventually using a `ctx'.
        If the transformation is an analysis, the result of the analysis
        is displayed.
        '''
        assert any(issubclass(transformation, T) for T in
                   (Transformation, Analysis))
        a = transformation()
        a.passmanager = self
        return a.apply(node, ctx)

########NEW FILE########
__FILENAME__ = spec
'''
This module provides a dummy parser for pythran annotations.
    * spec_parser reads the specs from a python module and returns them.
'''
import ply.lex as lex
import ply.yacc as yacc
import os.path
from numpy import array
from numpy import uint8, uint16, uint32, uint64
from numpy import int8, int16, int32, int64
from numpy import float32, float64
from numpy import complex64, complex128


class SpecParser:
    """ A parser that scans a file lurking for lines such as the one below.
    It then generates a pythran-compatible signature to inject into compile.
#pythran export a((float,(int,long),str list) list list)
#pythran export a(str)
#pythran export a( (str,str), int, long list list)
#pythran export a( {str} )
"""

    ## lex part
    reserved = {
        'pythran': 'PYTHRAN',
        'export': 'EXPORT',
        'list': 'LIST',
        'set': 'SET',
        'dict': 'DICT',
        'str': 'STR',
        'bool': 'BOOL',
        'complex': 'COMPLEX',
        'int': 'INT',
        'long': 'LONG',
        'float': 'FLOAT',
        'uint8': 'UINT8',
        'uint16': 'UINT16',
        'uint32': 'UINT32',
        'uint64': 'UINT64',
        'int8': 'INT8',
        'int16': 'INT16',
        'int32': 'INT32',
        'int64': 'INT64',
        'float32': 'FLOAT32',
        'float64': 'FLOAT64',
        'complex64': 'COMPLEX64',
        'complex128': 'COMPLEX128',
        }
    tokens = (['IDENTIFIER', 'SHARP', 'COMMA', 'COLUMN', 'LPAREN', 'RPAREN']
              + list(reserved.values())
              + ['LARRAY', 'RARRAY'])

    # token <> regexp binding
    t_SHARP = r'\#'
    t_COMMA = r','
    t_COLUMN = r':'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_RARRAY = r'\]'
    t_LARRAY = r'\['

    def t_IDENTIFER(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = SpecParser.reserved.get(t.value, 'IDENTIFIER')
        return t

    def t_NUMBER(self, t):
        r'[0-9]+'
        t.type = 'NUMBER'
        return t

    # skipped characters
    t_ignore = ' \t\r'

    # error handling
    def t_error(self, t):
        t.lexer.skip(1)

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    ## yacc part

    def p_exports(self, p):
        '''exports :
                   | export exports'''
        p[0] = self.exports

    def p_export(self, p):
        '''export : SHARP PYTHRAN EXPORT IDENTIFIER LPAREN opt_types RPAREN
                  | SHARP PYTHRAN EXPORT EXPORT LPAREN opt_types RPAREN'''
        # handle the unlikely case where a function name is ... export :-)
        self.exports[p[4]] = self.exports.get(p[4], ()) + (p[6],)

    def p_opt_types(self, p):
        '''opt_types :
                     | types'''
        p[0] = p[1] if len(p) == 2 else []

    def p_types(self, p):
        '''types : type
                 | type COMMA types'''
        p[0] = [p[1]] + ([] if len(p) == 2 else p[3])

    def p_type(self, p):
        '''type : term
                | type LIST
                | type SET
                | type LARRAY RARRAY
                | type COLUMN type DICT
                | LPAREN types RPAREN'''
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 3 and p[2] == 'list':
            p[0] = [p[1]]
        elif len(p) == 3 and p[2] == 'set':
            p[0] = {p[1]}
        elif len(p) == 4 and p[3] == ')':
            p[0] = tuple(p[2])
        elif len(p) == 4 and p[3] == ']':
            p[0] = array([p[1]])
        elif len(p) == 5:
            p[0] = {p[1]: p[3]}
        else:
            raise SyntaxError("Invalid Pythran spec. "
                              "Unknown text '{0}'".format(p.value))

    def p_term(self, p):
        '''term : STR
                | BOOL
                | COMPLEX
                | INT
                | LONG
                | FLOAT
                | UINT8
                | UINT16
                | UINT32
                | UINT64
                | INT8
                | INT16
                | INT32
                | INT64
                | FLOAT32
                | FLOAT64
                | COMPLEX64
                | COMPLEX128'''
        p[0] = eval(p[1])

    def p_error(self, p):
        p_val = p.value if p else ''
        err = SyntaxError("Invalid Pythran spec near '" + str(p_val) + "'")
        err.lineno = self.lexer.lineno
        if self.input_file:
            err.filename = self.input_file
        raise err

    def __init__(self, **kwargs):
        self.lexer = lex.lex(module=self, debug=0)
        self.parser = yacc.yacc(module=self,
                                debug=0,
                                tabmodule='pythran.parsetab')

    def __call__(self, path):
        self.exports = dict()
        self.input_file = None
        if os.path.isfile(path):
            self.input_file = path
            with file(path) as fd:
                data = fd.read()
        else:
            data = path
        # filter out everything that does not start with a #pythran
        pythran_data = "\n".join((line if line.startswith('#pythran') else ''
                                  for line in data.split('\n')))
        self.parser.parse(pythran_data, lexer=self.lexer)
        if not self.exports:
            import logging
            logging.warn("No pythran specification, "
                         "no function will be exported")
        return self.exports


def spec_parser(input):
    return SpecParser()(input)

########NEW FILE########
__FILENAME__ = syntax
'''
This module performs a few early syntax check on the input AST.
It checks the conformance of the input code to Pythran specific
constraints.
'''

import ast
import tables


class PythranSyntaxError(SyntaxError):
    def __init__(self, msg, node=None):
        SyntaxError.__init__(self, msg)
        if node:
            self.lineno = node.lineno
            self.offset = node.col_offset


class SyntaxChecker(ast.NodeVisitor):
    '''
    Visit an AST and raise a PythranSyntaxError upon unsupported construct
    '''

    def __init__(self):
        self.attributes = set()
        for module in tables.modules.itervalues():
            self.attributes.update(module.iterkeys())

    def visit_Module(self, node):
        err = ("Top level statements can only be strings, functions, comments"
               " or imports")
        for n in node.body:
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Str):
                continue
            else:
                if not any(isinstance(n, getattr(ast, t))
                           for t in ('FunctionDef', 'Import', 'ImportFrom',)):
                    raise PythranSyntaxError(err, n)
        self.generic_visit(node)

    def visit_Interactive(self, node):
        raise PythranSyntaxError("Interactive session not supported", node)

    def visit_Expression(self, node):
        raise PythranSyntaxError("Interactive expressions not supported", node)

    def visit_Suite(self, node):
        raise PythranSyntaxError(
            "Suites are specific to Jython and not supported", node)

    def visit_ClassDef(self, node):
        raise PythranSyntaxError("Classes not supported")

    def visit_Print(self, node):
        self.generic_visit(node)
        if node.dest:
            raise PythranSyntaxError(
                "Printing to a specific stream not supported", node.dest)

    def visit_With(self, node):
        raise PythranSyntaxError("With statements not supported")

    def visit_Call(self, node):
        self.generic_visit(node)
        if node.keywords:
            raise PythranSyntaxError("Call with keywords not supported", node)
        if node.starargs:
            raise PythranSyntaxError("Call with star arguments not supported",
                                     node)
        if node.kwargs:
            raise PythranSyntaxError("Call with kwargs not supported", node)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.args.vararg:
            raise PythranSyntaxError("Varargs not supported", node)
        if node.args.kwarg:
            raise PythranSyntaxError("Keyword arguments not supported",
                                     node)

    def visit_Raise(self, node):
        self.generic_visit(node)
        if node.tback:
            raise PythranSyntaxError(
                "Traceback in raise statements not supported",
                node)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr not in self.attributes:
            raise PythranSyntaxError(
                "Attribute '{0}' unknown".format(node.attr),
                node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name not in tables.modules:
                raise PythranSyntaxError(
                    "Module '{0}' unknown.".format(alias.name),
                    node)

    def visit_ImportFrom(self, node):
        if node.level != 0:
            raise PythranSyntaxError("Specifying a level in an import", node)
        if not node.module:
            raise PythranSyntaxError("import from without module", node)
        module = node.module
        if module not in tables.modules:
            raise PythranSyntaxError("Module '{0}' unknown".format(module),
                                     node)
        for alias in node.names:
            if alias.name == '*':
                continue
            if alias.name not in tables.modules[module]:
                raise PythranSyntaxError(
                    "identifier '{0}' not found in module '{1}'".format(
                        alias.name,
                        module),
                    node)

    def visit_Exec(self, node):
        raise PythranSyntaxError("Exec statement not supported", node)

    def visit_Global(self, node):
        raise PythranSyntaxError("Global variables not supported", node)


def check_syntax(node):
    '''Does nothing but raising PythranSyntaxError when needed'''
    SyntaxChecker().visit(node)

########NEW FILE########
__FILENAME__ = tables
'''
This modules provides the translation tables from python to c++.
'''

import ast
import cxxtypes

from intrinsic import Class
from intrinsic import ConstFunctionIntr, FunctionIntr, ReadOnceFunctionIntr
from intrinsic import ConstMethodIntr, MethodIntr, AttributeIntr, ConstantIntr
from intrinsic import ConstExceptionIntr
from intrinsic import UpdateEffect, ReadEffect
import numpy
import sys

pythran_ward = '__pythran_'

namespace = "pythonic"

pytype_to_ctype_table = {
    complex: 'std::complex<double>',
    bool: 'bool',
    int: 'long',
    long: 'pythran_long_t',
    float: 'double',
    str: 'pythonic::types::str',
    None: 'void',
    numpy.int8: 'int8_t',
    numpy.int16: 'int16_t',
    numpy.int32: 'int32_t',
    numpy.int64: 'int64_t',
    numpy.uint8: 'uint8_t',
    numpy.uint16: 'uint16_t',
    numpy.uint32: 'uint32_t',
    numpy.uint64: 'uint64_t',
    numpy.float32: 'float',
    numpy.float64: 'double',
    numpy.complex64: 'std::complex<float>',
    numpy.complex128: 'std::complex<double>',
    }

type_to_suffix = {
    int: "L",
    long: "LL",
    }

cxx_keywords = {
    'and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor',
    'bool', 'break', 'case', 'catch', 'char', 'class',
    'compl', 'const', 'const_cast', 'continue', 'default', 'delete',
    'do', 'double', 'dynamic_cast', 'else', 'enum', 'explicit',
    'export', 'extern', 'false', 'float', 'for', 'friend',
    'goto', 'if', 'inline', 'int', 'long', 'mutable', 'namespace', 'new',
    'not', 'not_eq', 'operator', 'or', 'or_eq', 'private', 'protected',
    'public', 'register', 'reinterpret_cast', 'return', 'short', 'signed',
    'sizeof', 'static', 'static_cast',
    'struct', 'switch', 'template', 'this', 'throw', 'true',
    'try', 'typedef', 'typeid', 'typename', 'union', 'unsigned',
    'using', 'virtual', 'void', 'volatile', 'wchar_t', 'while',
    'xor', 'xor_eq',
    # C++11 additions
    'constexpr', 'decltype', 'noexcept', 'nullptr', 'static_assert',
    # reserved namespaces
    'std',
    }


operator_to_lambda = {
    # boolop
    ast.And: lambda l, r: "(({0})?({1}):({0}))".format(l, r),
    ast.Or: lambda l, r: "(({0})?({0}):({1}))".format(l, r),
    # operator
    ast.Add: lambda l, r: "({0} + {1})".format(l, r),
    ast.Sub: lambda l, r: "({0} - {1})".format(l, r),
    ast.Mult: lambda l, r: "({0} * {1})".format(l, r),
    ast.Div: lambda l, r: "({0} / {1})".format(l, r),
    ast.Mod: lambda l, r: "(pythonic::operator_::mod({0}, {1}))".format(l, r),
    ast.Pow: lambda l, r: "pythonic::__builtin__::pow({0}, {1})".format(l, r),
    ast.LShift: lambda l, r: "({0} << {1})".format(l, r),
    ast.RShift: lambda l, r: "({0} >> {1})".format(l, r),
    ast.BitOr: lambda l, r: "({0} | {1})".format(l, r),
    ast.BitXor: lambda l, r: "({0} ^ {1})".format(l, r),
    ast.BitAnd: lambda l, r: "({0} & {1})".format(l, r),
    #** assume from __future__ import division
    ast.FloorDiv: lambda l, r: ("(pythonic::operator_::floordiv"
                                "({0}, {1}))".format(l, r)),
    # unaryop
    ast.Invert: lambda o: "(~{0})".format(o),
    ast.Not: lambda o: "(not {0})".format(o),
    ast.UAdd: lambda o: "(+{0})".format(o),
    ast.USub: lambda o: "(-{0})".format(o),
    # cmpop
    ast.Eq: lambda l, r: "({0} == {1})".format(l, r),
    ast.NotEq: lambda l, r: "({0} != {1})".format(l, r),
    ast.Lt: lambda l, r: "({0} < {1})".format(l, r),
    ast.LtE: lambda l, r: "({0} <= {1})".format(l, r),
    ast.Gt: lambda l, r: "({0} > {1})".format(l, r),
    ast.GtE: lambda l, r: "({0} >= {1})".format(l, r),
    ast.Is: lambda l, r: ("(pythonic::__builtin__::id({0}) == "
                          "pythonic::__builtin__::id({1}))".format(l, r)),
    ast.IsNot: lambda l, r: ("(pythonic::__builtin__::id({0}) != "
                             "pythonic::__builtin__::id({1}))".format(l, r)),
    ast.In: lambda l, r: "(pythonic::in({1}, {0}))".format(l, r),
    ast.NotIn: lambda l, r: "(not pythonic::in({1}, {0}))".format(l, r),
    }

equivalent_iterators = {
    "range": ("__builtin__", "xrange"),
    "filter": ("itertools", "ifilter"),
    "map": ("itertools", "imap"),
    "zip": ("itertools", "izip")
    }

# each module consist in a module_name <> set of symbols
modules = {
    "__builtin__": {
        "abs": ConstFunctionIntr(),
        "BaseException": ConstExceptionIntr(),
        "SystemExit": ConstExceptionIntr(),
        "KeyboardInterrupt": ConstExceptionIntr(),
        "GeneratorExit": ConstExceptionIntr(),
        "Exception": ConstExceptionIntr(),
        "StopIteration": ConstExceptionIntr(),
        "StandardError": ConstExceptionIntr(),
        "Warning": ConstExceptionIntr(),
        "BytesWarning": ConstExceptionIntr(),
        "UnicodeWarning": ConstExceptionIntr(),
        "ImportWarning": ConstExceptionIntr(),
        "FutureWarning": ConstExceptionIntr(),
        "UserWarning": ConstExceptionIntr(),
        "SyntaxWarning": ConstExceptionIntr(),
        "RuntimeWarning": ConstExceptionIntr(),
        "PendingDeprecationWarning": ConstExceptionIntr(),
        "DeprecationWarning": ConstExceptionIntr(),
        "BufferError": ConstExceptionIntr(),
        "ArithmeticError": ConstExceptionIntr(),
        "AssertionError": ConstExceptionIntr(),
        "AttributeError": ConstExceptionIntr(),
        "EnvironmentError": ConstExceptionIntr(),
        "EOFError": ConstExceptionIntr(),
        "ImportError": ConstExceptionIntr(),
        "LookupError": ConstExceptionIntr(),
        "MemoryError": ConstExceptionIntr(),
        "NameError": ConstExceptionIntr(),
        "ReferenceError": ConstExceptionIntr(),
        "RuntimeError": ConstExceptionIntr(),
        "SyntaxError": ConstExceptionIntr(),
        "SystemError": ConstExceptionIntr(),
        "TypeError": ConstExceptionIntr(),
        "ValueError": ConstExceptionIntr(),
        "FloatingPointError": ConstExceptionIntr(),
        "OverflowError": ConstExceptionIntr(),
        "ZeroDivisionError": ConstExceptionIntr(),
        "IOError": ConstExceptionIntr(),
        "OSError": ConstExceptionIntr(),
        "IndexError": ConstExceptionIntr(),
        "KeyError": ConstExceptionIntr(),
        "UnboundLocalError": ConstExceptionIntr(),
        "NotImplementedError": ConstExceptionIntr(),
        "IndentationError": ConstExceptionIntr(),
        "TabError": ConstExceptionIntr(),
        "UnicodeError": ConstExceptionIntr(),
        #  "UnicodeDecodeError": ConstExceptionIntr(),
        #  "UnicodeEncodeError": ConstExceptionIntr(),
        #  "UnicodeTranslateError": ConstExceptionIntr(),
        "all": ReadOnceFunctionIntr(),
        "any": ReadOnceFunctionIntr(),
        "bin": ConstFunctionIntr(),
        "bool_": ConstFunctionIntr(),
        "chr": ConstFunctionIntr(),
        "cmp": ConstFunctionIntr(),
        "complex": ConstFunctionIntr(),
        "dict": ReadOnceFunctionIntr(),
        "divmod": ConstFunctionIntr(),
        "enumerate": ReadOnceFunctionIntr(),
        "file": ConstFunctionIntr(),
        "filter": ReadOnceFunctionIntr(),
        "float_": ConstFunctionIntr(),
        "getattr": ConstFunctionIntr(),
        "hex": ConstFunctionIntr(),
        "id": ConstFunctionIntr(),
        "int_": ConstFunctionIntr(),
        "iter": FunctionIntr(),  # not const
        "len": ConstFunctionIntr(),
        "list": ReadOnceFunctionIntr(),
        "long_": ConstFunctionIntr(),
        "map": ReadOnceFunctionIntr(),
        "max": ReadOnceFunctionIntr(),
        "min": ReadOnceFunctionIntr(),
        "next": FunctionIntr(),  # not const
        "oct": ConstFunctionIntr(),
        "ord": ConstFunctionIntr(),
        "open": ConstFunctionIntr(),
        "pow": ConstFunctionIntr(),
        "pow2": ConstFunctionIntr(),
        "range": ConstFunctionIntr(),
        "reduce": ReadOnceFunctionIntr(),
        "reversed": ReadOnceFunctionIntr(),
        "round": ConstFunctionIntr(),
        "set": ReadOnceFunctionIntr(),
        "sorted": ConstFunctionIntr(),
        "str": ConstFunctionIntr(),
        "sum": ReadOnceFunctionIntr(),
        "tuple": ReadOnceFunctionIntr(),
        "xrange": ConstFunctionIntr(),
        "zip": ReadOnceFunctionIntr(),
        "False": ConstantIntr(),
        "None": ConstantIntr(),
        "True": ConstantIntr(),
        },
    "numpy": {
        "abs": ConstFunctionIntr(),
        "absolute": ConstFunctionIntr(),
        "add": ConstFunctionIntr(),
        "alen": ConstFunctionIntr(),
        "all": ConstMethodIntr(),
        "allclose": ConstFunctionIntr(),
        "alltrue": ConstFunctionIntr(),
        "amax": ConstFunctionIntr(),
        "amin": ConstFunctionIntr(),
        "angle": ConstFunctionIntr(),
        "any": ConstMethodIntr(),
        "append": ConstFunctionIntr(),
        "arange": ConstFunctionIntr(),
        "arccos": ConstFunctionIntr(),
        "arccos": ConstFunctionIntr(),
        "arccosh": ConstFunctionIntr(),
        "arcsin": ConstFunctionIntr(),
        "arcsin": ConstFunctionIntr(),
        "arcsinh": ConstFunctionIntr(),
        "arctan": ConstFunctionIntr(),
        "arctan": ConstFunctionIntr(),
        "arctan2": ConstFunctionIntr(),
        "arctan2": ConstFunctionIntr(),
        "arctanh": ConstFunctionIntr(),
        "argmax": ConstFunctionIntr(),
        "argmin": ConstFunctionIntr(),
        "argsort": ConstFunctionIntr(),
        "argwhere": ConstFunctionIntr(),
        "around": ConstFunctionIntr(),
        "array": ConstFunctionIntr(),
        "array2string": ConstFunctionIntr(),
        "array_equal": ConstFunctionIntr(),
        "array_equiv": ConstFunctionIntr(),
        "array_split": ConstFunctionIntr(),
        "array_str": ConstFunctionIntr(),
        "asarray": ConstFunctionIntr(),
        "asarray_chkfinite": ConstFunctionIntr(),
        "ascontiguousarray": ConstFunctionIntr(),
        "asscalar": ConstFunctionIntr(),
        "atleast_1d": ConstFunctionIntr(),
        "atleast_2d": ConstFunctionIntr(),
        "atleast_3d": ConstFunctionIntr(),
        "average": ConstFunctionIntr(),
        "base_repr": ConstFunctionIntr(),
        "binary_repr": ConstFunctionIntr(),
        "bincount": ConstFunctionIntr(),
        "bitwise_and": ConstFunctionIntr(),
        "bitwise_not": ConstFunctionIntr(),
        "bitwise_or": ConstFunctionIntr(),
        "bitwise_xor": ConstFunctionIntr(),
        "ceil": ConstFunctionIntr(),
        "clip": ConstFunctionIntr(),
        "concatenate": ConstFunctionIntr(),
        "complex": ConstFunctionIntr(),
        #"complex128": ConstFunctionIntr(),
        "complex64": ConstFunctionIntr(),
        "conj": ConstFunctionIntr(),
        "conjugate": ConstFunctionIntr(),
        "copy": ConstFunctionIntr(),
        "copyto": FunctionIntr(argument_effects=[UpdateEffect(), ReadEffect(),
                                                 ReadEffect(), ReadEffect()]),
        "copysign": ConstFunctionIntr(),
        "cos": ConstFunctionIntr(),
        "cosh": ConstFunctionIntr(),
        "cumprod": ConstMethodIntr(),
        "cumproduct": ConstMethodIntr(),
        "cumsum": ConstMethodIntr(),
        "deg2rad": ConstFunctionIntr(),
        "degrees": ConstFunctionIntr(),
        "delete_": ConstFunctionIntr(),
        "diag": ConstFunctionIntr(),
        "diagflat": ConstFunctionIntr(),
        "diagonal": ConstFunctionIntr(),
        "diff": ConstFunctionIntr(),
        "digitize": ConstFunctionIntr(),
        "divide": ConstFunctionIntr(),
        "dot": ConstFunctionIntr(),
        "double_": ConstFunctionIntr(),
        "e": ConstantIntr(),
        "ediff1d": ConstFunctionIntr(),
        "empty": ConstFunctionIntr(),
        "empty_like": ConstFunctionIntr(),
        "equal": ConstFunctionIntr(),
        "exp": ConstFunctionIntr(),
        "expm1": ConstFunctionIntr(),
        "eye": ConstFunctionIntr(),
        "fabs": ConstFunctionIntr(),
        "finfo": ConstFunctionIntr(),
        "fix": ConstFunctionIntr(),
        "flatnonzero": ConstFunctionIntr(),
        "fliplr": ConstFunctionIntr(),
        "flipud": ConstFunctionIntr(),
        #"float128": ConstFunctionIntr(),
        "float32": ConstFunctionIntr(),
        "float64": ConstFunctionIntr(),
        "float_": ConstFunctionIntr(),
        "floor": ConstFunctionIntr(),
        "floor_divide": ConstFunctionIntr(),
        "fmax": ConstFunctionIntr(),
        "fmin": ConstFunctionIntr(),
        "fmod": ConstFunctionIntr(),
        "frexp": ConstFunctionIntr(),
        "fromfunction": ConstFunctionIntr(),
        "fromiter": ConstFunctionIntr(),
        "fromstring": ConstFunctionIntr(),
        "greater": ConstFunctionIntr(),
        "greater_equal": ConstFunctionIntr(),
        "hypot": ConstFunctionIntr(),
        "identity": ConstFunctionIntr(),
        "indices": ConstFunctionIntr(),
        "inf": ConstantIntr(),
        "inner": ConstFunctionIntr(),
        "insert": ConstFunctionIntr(),
        "intersect1d": ConstFunctionIntr(),
        "int16": ConstFunctionIntr(),
        "int32": ConstFunctionIntr(),
        "int64": ConstFunctionIntr(),
        "int8": ConstFunctionIntr(),
        "invert": ConstFunctionIntr(),
        "iscomplex": ConstFunctionIntr(),
        "isfinite": ConstFunctionIntr(),
        "isinf": ConstFunctionIntr(),
        "isnan": ConstFunctionIntr(),
        "isneginf": ConstFunctionIntr(),
        "isposinf": ConstFunctionIntr(),
        "isreal": ConstFunctionIntr(),
        "isrealobj": ConstFunctionIntr(),
        "isscalar": ConstFunctionIntr(),
        "issctype": ConstFunctionIntr(),
        "ldexp": ConstFunctionIntr(),
        "left_shift": ConstFunctionIntr(),
        "less": ConstFunctionIntr(),
        "less_equal": ConstFunctionIntr(),
        "lexsort": ConstFunctionIntr(),
        "linspace": ConstFunctionIntr(),
        "log": ConstFunctionIntr(),
        "log10": ConstFunctionIntr(),
        "log1p": ConstFunctionIntr(),
        "log2": ConstFunctionIntr(),
        "logaddexp": ConstFunctionIntr(),
        "logaddexp2": ConstFunctionIntr(),
        "logspace": ConstFunctionIntr(),
        "logical_and": ConstFunctionIntr(),
        "logical_not": ConstFunctionIntr(),
        "logical_or": ConstFunctionIntr(),
        "logical_xor": ConstFunctionIntr(),
        "max": ConstMethodIntr(),
        "maximum": ConstFunctionIntr(),
        "mean": ConstMethodIntr(),
        "median": ConstFunctionIntr(),
        "min": ConstMethodIntr(),
        "minimum": ConstFunctionIntr(),
        "mod": ConstFunctionIntr(),
        "multiply": ConstFunctionIntr(),
        "nan": ConstantIntr(),
        "nan_to_num": ConstFunctionIntr(),
        "nanargmax": ConstFunctionIntr(),
        "nanargmin": ConstFunctionIntr(),
        "nanmax": ConstFunctionIntr(),
        "nanmin": ConstFunctionIntr(),
        "nansum": ConstFunctionIntr(),
        "ndenumerate": ConstFunctionIntr(),
        "ndindex": ConstFunctionIntr(),
        "ndim": ConstFunctionIntr(),
        "negative": ConstFunctionIntr(),
        "nextafter": ConstFunctionIntr(),
        "NINF": ConstantIntr(),
        "nonzero": ConstFunctionIntr(),
        "not_equal": ConstFunctionIntr(),
        "ones": ConstFunctionIntr(),
        "ones_like": ConstFunctionIntr(),
        "outer": ConstFunctionIntr(),
        "pi": ConstantIntr(),
        "place": FunctionIntr(),
        "power": ConstFunctionIntr(),
        "prod": ConstMethodIntr(),
        "product": ConstFunctionIntr(),
        "ptp": ConstFunctionIntr(),
        "put": FunctionIntr(),
        "putmask": FunctionIntr(),
        "rad2deg": ConstFunctionIntr(),
        "radians": ConstFunctionIntr(),
        "rank": ConstFunctionIntr(),
        "ravel": ConstFunctionIntr(),
        "reciprocal": ConstFunctionIntr(),
        "remainder": ConstFunctionIntr(),
        "repeat": ConstFunctionIntr(),
        "reshape": ConstMethodIntr(),
        "resize": ConstMethodIntr(),
        "right_shift": ConstFunctionIntr(),
        "rint": ConstFunctionIntr(),
        "roll": ConstFunctionIntr(),
        "rollaxis": ConstFunctionIntr(),
        "rot90": ConstFunctionIntr(),
        "round": ConstFunctionIntr(),
        "round_": ConstFunctionIntr(),
        "searchsorted": ConstFunctionIntr(),
        "select": ConstFunctionIntr(),
        "shape": ConstFunctionIntr(),
        "sign": ConstFunctionIntr(),
        "signbit": ConstFunctionIntr(),
        "sin": ConstFunctionIntr(),
        "sinh": ConstFunctionIntr(),
        "size": ConstFunctionIntr(),
        "sometrue": ConstFunctionIntr(),
        "sort": ConstFunctionIntr(),
        "sort_complex": ConstFunctionIntr(),
        "spacing": ConstFunctionIntr(),
        "split": ConstFunctionIntr(),
        "sqrt": ConstFunctionIntr(),
        "square": ConstFunctionIntr(),
        "subtract": ConstFunctionIntr(),
        "sum": ConstMethodIntr(),
        "swapaxes": ConstMethodIntr(),
        "take": ConstFunctionIntr(),
        "tan": ConstFunctionIntr(),
        "tanh": ConstFunctionIntr(),
        "tile": ConstFunctionIntr(),
        "trace": ConstFunctionIntr(),
        "transpose": ConstMethodIntr(),
        "tri": ConstMethodIntr(),
        "tril": ConstMethodIntr(),
        "trim_zeros": ConstMethodIntr(),
        "triu": ConstMethodIntr(),
        "true_divide": ConstFunctionIntr(),
        "trunc": ConstFunctionIntr(),
        "uint16": ConstFunctionIntr(),
        "uint32": ConstFunctionIntr(),
        "uint64": ConstFunctionIntr(),
        "uint8": ConstFunctionIntr(),
        "union1d": ConstFunctionIntr(),
        "unique": ConstFunctionIntr(),
        "unwrap": ConstFunctionIntr(),
        "where": ConstFunctionIntr(),
        "zeros": ConstFunctionIntr(),
        "zeros_like": ConstFunctionIntr(),
        },
    "time": {
        "sleep": FunctionIntr(global_effects=True),
        "time": FunctionIntr(global_effects=True),
        },
    "math": {
        "isinf": ConstFunctionIntr(),
        "modf": ConstFunctionIntr(),
        "frexp": ConstFunctionIntr(),
        "factorial": ConstFunctionIntr(),
        "gamma": ConstFunctionIntr(),
        "lgamma": ConstFunctionIntr(),
        "trunc": ConstFunctionIntr(),
        "erf": ConstFunctionIntr(),
        "erfc": ConstFunctionIntr(),
        "asinh": ConstFunctionIntr(),
        "atanh": ConstFunctionIntr(),
        "acosh": ConstFunctionIntr(),
        "radians": ConstFunctionIntr(),
        "degrees": ConstFunctionIntr(),
        "hypot": ConstFunctionIntr(),
        "tanh": ConstFunctionIntr(),
        "cosh": ConstFunctionIntr(),
        "sinh": ConstFunctionIntr(),
        "atan": ConstFunctionIntr(),
        "atan2": ConstFunctionIntr(),
        "asin": ConstFunctionIntr(),
        "tan": ConstFunctionIntr(),
        "log": ConstFunctionIntr(),
        "log1p": ConstFunctionIntr(),
        "expm1": ConstFunctionIntr(),
        "ldexp": ConstFunctionIntr(),
        "fmod": ConstFunctionIntr(),
        "fabs": ConstFunctionIntr(),
        "copysign": ConstFunctionIntr(),
        "acos": ConstFunctionIntr(),
        "cos": ConstFunctionIntr(),
        "sin": ConstFunctionIntr(),
        "exp": ConstFunctionIntr(),
        "sqrt": ConstFunctionIntr(),
        "log10": ConstFunctionIntr(),
        "isnan": ConstFunctionIntr(),
        "ceil": ConstFunctionIntr(),
        "floor": ConstFunctionIntr(),
        "pow": ConstFunctionIntr(),
        "pi": ConstantIntr(),
        "e": ConstantIntr(),
        },
    "functools": {
        "partial": FunctionIntr(),
        },
    "bisect": {
        "bisect_left": ConstFunctionIntr(),
        "bisect_right": ConstFunctionIntr(),
        "bisect": ConstFunctionIntr(),
        },
    "cmath": {
        "cos": FunctionIntr(),
        "sin": FunctionIntr(),
        "exp": FunctionIntr(),
        "sqrt": FunctionIntr(),
        "log10": FunctionIntr(),
        "isnan": FunctionIntr(),
        "pi": ConstantIntr(),
        "e": ConstantIntr(),
        },
    "itertools": {
        "count": ReadOnceFunctionIntr(),
        "imap": ReadOnceFunctionIntr(),
        "ifilter": ReadOnceFunctionIntr(),
        "islice": ReadOnceFunctionIntr(),
        "product": ConstFunctionIntr(),
        "izip": ReadOnceFunctionIntr(),
        "combinations": ConstFunctionIntr(),
        "permutations": ConstFunctionIntr(),
        },
    "random": {
        "seed": FunctionIntr(global_effects=True),
        "random": FunctionIntr(global_effects=True),
        "randint": FunctionIntr(global_effects=True),
        "randrange": FunctionIntr(global_effects=True),
        "gauss": FunctionIntr(global_effects=True),
        "uniform": FunctionIntr(global_effects=True),
        "expovariate": FunctionIntr(global_effects=True),
        "sample": FunctionIntr(global_effects=True),
        "choice": FunctionIntr(global_effects=True),
        },
    "omp": {
        "set_num_threads": FunctionIntr(global_effects=True),
        "get_num_threads": FunctionIntr(global_effects=True),
        "get_max_threads": FunctionIntr(global_effects=True),
        "get_thread_num": FunctionIntr(global_effects=True),
        "get_num_procs": FunctionIntr(global_effects=True),
        "in_parallel": FunctionIntr(global_effects=True),
        "set_dynamic": FunctionIntr(global_effects=True),
        "get_dynamic": FunctionIntr(global_effects=True),
        "set_nested": FunctionIntr(global_effects=True),
        "get_nested": FunctionIntr(global_effects=True),
        "init_lock": FunctionIntr(global_effects=True),
        "destroy_lock": FunctionIntr(global_effects=True),
        "set_lock": FunctionIntr(global_effects=True),
        "unset_lock": FunctionIntr(global_effects=True),
        "test_lock": FunctionIntr(global_effects=True),
        "init_nest_lock": FunctionIntr(global_effects=True),
        "destroy_nest_lock": FunctionIntr(global_effects=True),
        "set_nest_lock": FunctionIntr(global_effects=True),
        "unset_nest_lock": FunctionIntr(global_effects=True),
        "test_nest_lock": FunctionIntr(global_effects=True),
        "get_wtime": FunctionIntr(global_effects=True),
        "get_wtick": FunctionIntr(global_effects=True),
        "set_schedule": FunctionIntr(global_effects=True),
        "get_schedule": FunctionIntr(global_effects=True),
        "get_thread_limit": FunctionIntr(global_effects=True),
        "set_max_active_levels": FunctionIntr(global_effects=True),
        "get_max_active_levels": FunctionIntr(global_effects=True),
        "get_level": FunctionIntr(global_effects=True),
        "get_ancestor_thread_num": FunctionIntr(global_effects=True),
        "get_team_size": FunctionIntr(global_effects=True),
        "get_active_level": FunctionIntr(global_effects=True),
        "in_final": FunctionIntr(global_effects=True),
        },
    "operator_": {
        "lt": ConstFunctionIntr(),
        "le": ConstFunctionIntr(),
        "eq": ConstFunctionIntr(),
        "ne": ConstFunctionIntr(),
        "ge": ConstFunctionIntr(),
        "gt": ConstFunctionIntr(),
        "__lt__": ConstFunctionIntr(),
        "__le__": ConstFunctionIntr(),
        "__eq__": ConstFunctionIntr(),
        "__ne__": ConstFunctionIntr(),
        "__ge__": ConstFunctionIntr(),
        "__gt__": ConstFunctionIntr(),
        "not_": ConstFunctionIntr(),
        "__not__": ConstFunctionIntr(),
        "truth": ConstFunctionIntr(),
        "is_": ConstFunctionIntr(),
        "is_not": ConstFunctionIntr(),
        "__abs__": ConstFunctionIntr(),
        "add": ConstFunctionIntr(),
        "__add__": ConstFunctionIntr(),
        "and_": ConstFunctionIntr(),
        "__and__": ConstFunctionIntr(),
        "div": ConstFunctionIntr(),
        "__div__": ConstFunctionIntr(),
        "floordiv": ConstFunctionIntr(),
        "__floordiv__": ConstFunctionIntr(),
        "inv": ConstFunctionIntr(),
        "invert": ConstFunctionIntr(),
        "__inv__": ConstFunctionIntr(),
        "__invert__": ConstFunctionIntr(),
        "lshift": ConstFunctionIntr(),
        "__lshift__": ConstFunctionIntr(),
        "mod": ConstFunctionIntr(),
        "__mod__": ConstFunctionIntr(),
        "mul": ConstFunctionIntr(),
        "__mul__": ConstFunctionIntr(),
        "neg": ConstFunctionIntr(),
        "__neg__": ConstFunctionIntr(),
        "or_": ConstFunctionIntr(),
        "__or__": ConstFunctionIntr(),
        "pos": ConstFunctionIntr(),
        "__pos__": ConstFunctionIntr(),
        "rshift": ConstFunctionIntr(),
        "__rshift__": ConstFunctionIntr(),
        "sub": ConstFunctionIntr(),
        "__sub__": ConstFunctionIntr(),
        "truediv": ConstFunctionIntr(),
        "__truediv__": ConstFunctionIntr(),
        "__xor__": ConstFunctionIntr(),
        "concat": ConstFunctionIntr(),
        "__concat__": ConstFunctionIntr(),
        "iadd": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__iadd__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "iand": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__iand__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "iconcat": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__iconcat__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "idiv": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__idiv__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "ifloordiv": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__ifloordiv__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "ilshift": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__ilshift__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "imod": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__imod__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "imul": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__imul__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "ior": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__ior__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "ipow": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__ipow__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "irshift": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__irshift__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "isub": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__isub__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "itruediv": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__itruediv__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "ixor": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__ixor__": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "contains": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "__contains__": ConstFunctionIntr(),
        "countOf": ConstFunctionIntr(),
        "delitem": FunctionIntr(
            argument_effects=[UpdateEffect(), ReadEffect()]),
        "__delitem__": FunctionIntr(
            argument_effects=[UpdateEffect(), ReadEffect()]),
        "getitem": ConstFunctionIntr(),
        "__getitem__": ConstFunctionIntr(),
        "indexOf": ConstFunctionIntr(),
        "__theitemgetter__": ConstFunctionIntr(),
        "itemgetter": MethodIntr(
            return_alias=lambda node: {
                modules['operator_']['__theitemgetter__']}
            ),

    },
    "string": {
        "ascii_lowercase": ConstantIntr(),
        "ascii_uppercase": ConstantIntr(),
        "ascii_letters": ConstantIntr(),
        "digits": ConstantIntr(),
        "find": ConstFunctionIntr(),
        "hexdigits": ConstantIntr(),
        "octdigits": ConstantIntr(),
        },
    "__list__": {
        "append": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                unary_op=lambda f: cxxtypes.ListType(f),
                register=True)
            ),
        "extend": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                register=True)
            ),
        "index": ConstMethodIntr(),
        #"pop": MethodIntr(), dispatched
        "reverse": MethodIntr(),
        "sort": MethodIntr(),
        #"count": ConstMethodIntr(), dispatched
        "insert": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[2],
                unary_op=lambda f: cxxtypes.ListType(f),
                register=True)
            ),
        },

    "__iterator__": {
        #"next": MethodIntr(), dispatched
        },
    "__str__": {
        "capitalize": ConstMethodIntr(),
        #"count": ConstMethodIntr(), dispatched
        "endswith": ConstMethodIntr(),
        "startswith": ConstMethodIntr(),
        "find": ConstMethodIntr(),
        "isalpha": ConstMethodIntr(),
        "isdigit": ConstMethodIntr(),
        "join": ConstMethodIntr(),
        "lower": ConstMethodIntr(),
        "replace": ConstMethodIntr(),
        "split": ConstMethodIntr(),
        "strip": ConstMethodIntr(),
        "lstrip": ConstMethodIntr(),
        "rstrip": ConstMethodIntr(),
        "upper": ConstMethodIntr(),
        },
    "__set__": {
        "add": MethodIntr(
            lambda self, node:
            self.combine(
                node.args[0],
                node.args[1],
                unary_op=lambda f: cxxtypes.SetType(f),
                register=True)
            ),
        "discard": MethodIntr(),
        "isdisjoint": ConstMethodIntr(),
        "union_": ConstMethodIntr(),
        "intersection": ConstMethodIntr(),
        "intersection_update": MethodIntr(
            lambda self, node:
            [
                self.combine(
                    node.args[0],
                    node_args_k,
                    register=True)
                for node_args_k in node.args[1:]
                ]
            ),
        "difference": ConstMethodIntr(),
        "difference_update": MethodIntr(
            lambda self, node:
            [
                self.combine(
                    node.args[0],
                    node_args_k,
                    register=True)
                for node_args_k in node.args[1:]
                ]
            ),
        "symmetric_difference": ConstMethodIntr(),
        "symmetric_difference_update": MethodIntr(
            lambda self, node:
            [
                self.combine(
                    node.args[0],
                    node_args_k,
                    register=True)
                for node_args_k in node.args[1:]
                ]
            ),
        "issuperset": ConstMethodIntr(),
        "issubset": ConstMethodIntr(),
        },
    "__exception__": {
        "args": AttributeIntr(0),
        "errno": AttributeIntr(1),
        "strerror": AttributeIntr(2),
        "filename": AttributeIntr(3),
        },
    "__float__": {
        "is_integer": ConstMethodIntr(),
        },
    "__complex___": {
        "real": AttributeIntr(0),
        "imag": AttributeIntr(1),
        "conjugate": ConstMethodIntr(),
        },
    "__dict__": {
        "fromkeys": ConstFunctionIntr(),
        "get": ConstMethodIntr(),
        "has_key": ConstMethodIntr(),
        "items": MethodIntr(),
        "iteritems": MethodIntr(),
        "iterkeys": MethodIntr(),
        "itervalues": MethodIntr(),
        "keys": MethodIntr(),
        #"pop": MethodIntr(), dispatched
        "popitem": MethodIntr(),
        "setdefault": MethodIntr(
            lambda self, node:
            len(node.args) == 3 and
            self.combine(
                node.args[0],
                node.args[1],
                unary_op=lambda x: cxxtypes.DictType(
                    x,
                    self.result[node.args[2]]),
                register=True),
            return_alias=lambda node: {
                ast.Subscript(node.args[0],
                              ast.Index(node.args[1]),
                              ast.Load())
                }
            ),
        "values": MethodIntr(),
        "viewitems": MethodIntr(),
        "viewkeys": MethodIntr(),
        "viewvalues": MethodIntr(),
        },
    "__file__": {
        # Member variables
        "closed": AttributeIntr(0),
        "mode": AttributeIntr(1),
        "name": AttributeIntr(2),
        "newlines": AttributeIntr(3),
        # Member functions
        "close": MethodIntr(global_effects=True),
        "flush": MethodIntr(global_effects=True),
        "fileno": MethodIntr(),
        "isatty": MethodIntr(),
        #"next": MethodIntr(global_effects=True), dispatched
        "read": MethodIntr(global_effects=True),
        "readline": MethodIntr(global_effects=True),
        "readlines": MethodIntr(global_effects=True),
        "xreadlines": MethodIntr(global_effects=True),
        "seek": MethodIntr(global_effects=True),
        "tell": MethodIntr(),
        "truncate": MethodIntr(global_effects=True),
        "write": MethodIntr(global_effects=True),
        "writelines": MethodIntr(global_effects=True),
        },
    "__finfo__": {
        "eps": AttributeIntr(0),
        },
    "__ndarray__": {
        "dtype": AttributeIntr(7),
        "fill": MethodIntr(),
        "flat": AttributeIntr(6),
        "flatten": MethodIntr(),
        "item": MethodIntr(),
        "itemsize": AttributeIntr(4),
        "nbytes": AttributeIntr(5),
        "ndim": AttributeIntr(1),
        "shape": AttributeIntr(0),
        "size": AttributeIntr(3),
        "strides": AttributeIntr(2),
        "T": AttributeIntr(8),
        "tolist": ConstMethodIntr(),
        "tostring": ConstMethodIntr(),
        },
    # conflicting method names must be listed here
    "__dispatch__": {
        "clear": MethodIntr(),
        "copy": ConstMethodIntr(),
        "count": ConstMethodIntr(),
        "next": MethodIntr(),
        "pop": MethodIntr(),
        "remove": MethodIntr(),
        "update": MethodIntr(
            lambda self, node:
            [
                self.combine(
                    node.args[0],
                    node_args_k,
                    register=True)
                for node_args_k in node.args[1:]
                ]
            ),
        },
    }

# VMSError is only available on VMS
if 'VMSError' in sys.modules['__builtin__'].__dict__:
    modules['__builtin__']['VMSError'] = ConstExceptionIntr()

# WindowsError is only available on Windows
if 'WindowsError' in sys.modules['__builtin__'].__dict__:
    modules['__builtin__']['WindowsError'] = ConstExceptionIntr()

# create symlinks for classes
modules['__builtin__']['__set__'] = Class(modules['__set__'])
modules['__builtin__']['__dict__'] = Class(modules['__dict__'])
modules['__builtin__']['__list__'] = Class(modules['__list__'])
modules['__builtin__']['__complex___'] = Class(modules['__complex___'])

# a method name to module binding
methods = {}
for module, elems in modules.iteritems():
    for elem, signature in elems.iteritems():
        if signature.ismethod():
            assert elem not in methods  # we need unicity
            methods[elem] = (module, signature)

# a function name to module binding
functions = {}
for module, elems in modules.iteritems():
    for elem, signature in elems.iteritems():
        if signature.isstaticfunction():
            functions.setdefault(elem, []).append((module, signature,))

# a attribute name to module binding
attributes = {}
for module, elems in modules.iteritems():
    for elem, signature in elems.iteritems():
        if signature.isattribute():
            assert elem not in attributes  # we need unicity
            attributes[elem] = (module, signature,)

########NEW FILE########
__FILENAME__ = allpairs
import numpy as np
#pythran export sqr_dists(float[][], float[][])
#pythran export sqr_dists_loops(float[][], float[][])
#bench u = 300; d = 300; import numpy as np; b = np.ones((u,d)); a = np.ones((u,d)); sqr_dists(a, b)

def sqr_dists(X,Y):
  return np.array([[np.sum( (x-y) ** 2) for x in X] for y in Y])

def sqr_dists_loops(X,Y):
  m,n = X.shape[0], Y.shape[0]
  D = np.zeros((m,n))
  for i in xrange(m):
    for j in xrange(n):
      D[i,j] = np.sum( (X[i] -Y[j]) ** 2)
  return D


########NEW FILE########
__FILENAME__ = allpairs_distances
#pythran export allpairs_distances(int)
#runas allpairs_distances(100)
#bench allpairs_distances(100)
import numpy as np

def dists(X,Y):
  return np.array([[np.sum( (x-y) ** 2) for x in X] for y in Y])

def allpairs_distances(d):
    #X = np.random.randn(1000,d)
    #Y = np.random.randn(200,d)
    X = np.arange(600*d).reshape(600,d)
    Y = np.arange(200*d).reshape(200,d)
    return dists(X,Y)

########NEW FILE########
__FILENAME__ = allpairs_distances_loops
#pythran export allpairs_distances_loops(int)
#runas allpairs_distances_loops(100)
#bench allpairs_distances_loops(100)
import numpy as np

def dists(X,Y):
  result = np.zeros( (X.shape[0], Y.shape[0]), X.dtype)
  for i in xrange(X.shape[0]):
    for j in xrange(Y.shape[0]):
      result[i,j] = np.sum( (X[i,:] - Y[j,:]) ** 2)
  return result

def allpairs_distances_loops(d):
    #X = np.random.randn(1000,d)
    #Y = np.random.randn(200,d)
    X = np.ones((500,d))
    Y = np.ones((200,d))
    return dists(X,Y)

########NEW FILE########
__FILENAME__ = another_quicksort
#pythran export QuickSort(float list)
#runas QuickSort(range(10))
#bench a = range(200000); QuickSort(a)

# swap two value of the list
def swap (l, idx1, idx2):
    if (idx1 != idx2):
        tmp = l[idx1]
        l[idx1] = l[idx2]
        l[idx2] = tmp

# partition the list using the value at pivot index size / 2 and return the
# new pivot index
def partition (l):
    size = len (l)
    # the pivot indfex
    pivot_idx = size / 2
    # the pivot value
    val = l[pivot_idx]
    # the idx of last unsorted elemet
    idx = size - 1
    # move the pivot to the end
    if (pivot_idx != idx):
        swap (l, pivot_idx, idx)

    # the pivot must stay at the end until the final swap
    idx = idx - 1
    # go through the list of the elements to be sorted
    i = 0
    while (i <= idx):
        if (l[i] > val) :
            while ((l[idx] > val) and (idx > i)):
                idx = idx - 1
            if (idx != i):
                swap (l, i, idx)
                idx = idx - 1
            else:
                break
        i = i+1
    # finally bring the pivot at its final place
    assert ((idx == i) or (idx + 1 == i))
    swap (l, i, size - 1)
    return i

def QuickSort (l):
    size = len (l)
    if size > 1:
        # Get the lists of bigger and smaller items and final position of pivot
        idx = partition (l)
        l1 = []
        l2 = []
        for i in range (0, idx):
            l1.append (l[i])
        for i in range (idx, size):
            l2.append (l[i])
        # Recursively sort elements smaller than the pivot
        QuickSort(l1);
        # Recursively sort elements at least as big as the pivot
        QuickSort(l2);
        for i in range (0, len (l1)):
            l[i] = l1[i]
        for i in range (0, len (l2)):
            l[len (l1) + i] = l2[i]
    return l

########NEW FILE########
__FILENAME__ = approximated_callgraph
#pythran export approximated_callgraph(int)
#runas approximated_callgraph(1000)
#bench approximated_callgraph(2500)
def call(i, j):
    return i+j

def approximated_callgraph(size):
    out= list()
    for i in xrange(size):
        out.append(map(lambda j:call(i, j), xrange(size)))
    return out

########NEW FILE########
__FILENAME__ = arc_distance
#pythran export arc_distance(float [], float[], float[], float[])
#runas import numpy as np; arc_distance(np.array([12.4,0.5,-5.6,12.34,9.21]),np.array([-5.6,3.4,2.3,-23.31,12.6]),np.array([3.45,1.5,55.4,567.0,43.2]),np.array([56.1,3.4,1.34,-56.9,-3.4]))
#bench import numpy.random; N=5000000; a, b, c, d = numpy.random.rand(N), numpy.random.rand(N), numpy.random.rand(N), numpy.random.rand(N); arc_distance(a, b, c, d)

import numpy as np
def arc_distance(theta_1, phi_1,
                 theta_2, phi_2):
    """
    Calculates the pairwise arc distance between all points in vector a and b.
    """
    temp = np.sin((theta_2-theta_1)/2)**2+np.cos(theta_1)*np.cos(theta_2)*np.sin((phi_2-phi_1)/2)**2
    distance_matrix = 2 * (np.arctan2(np.sqrt(temp),np.sqrt(1-temp)))
    return distance_matrix

########NEW FILE########
__FILENAME__ = arc_distance_list
#from https://bitbucket.org/FedericoV/numpy-tip-complex-modeling/src/806c968e3705/src/simulations/list_arc_distance.py?at=default
from math import sin, cos, atan2, sqrt, pi
from random import random

#pythran export arc_distance_list( (float, float) list, (float, float) list)
#runas arc_distance_list([(12.4,0.5),(-5.6,12.34),(9.21,-5.6),(3.4,2.3),(-23.31,12.6)],[(3.45,1.5),(55.4,567.0),(43.2,56.1),(3.4,1.34),(-56.9,-3.4)])
#bench import random; N=1000; a = [(random.random(), random.random()) for i in xrange(N)]; b = [(random.random(), random.random()) for i in xrange(N)]; arc_distance_list(a,b)
def arc_distance_list(a, b):
    distance_matrix = []
    for theta_1, phi_1 in a:
        temp_matrix = [ 2 * (atan2(sqrt(temp), sqrt(1 - temp))) for temp in [ sin((theta_2 - theta_1) / 2) ** 2 + cos(theta_1) * cos(theta_2) * sin((phi_2 - phi_1) / 2) ** 2  for theta_2, phi_2 in b ] ]
        distance_matrix.append(temp_matrix)

    return distance_matrix

#print  arc_distance_list([(12.4,0.5),(-5.6,12.34),(9.21,-5.6),(3.4,2.3),(-23.31,12.6)],[(3.45,1.5),(55.4,567.0),(43.2,56.1),(3.4,1.34),(-56.9,-3.4)])

########NEW FILE########
__FILENAME__ = babylonian
#pythran export is_square(long)
#runas is_square(12345678987654321234567 ** 256)
#bench is_square(12345678987654321234567 ** 256)
#from http://stackoverflow.com/questions/2489435/how-could-i-check-if-a-number-is-a-perfect-square

def is_square(apositiveint):
  x = apositiveint // 2
  seen = { x }
  while x * x != apositiveint:
    x = (x + (apositiveint // x)) // 2
    if x in seen: return False
    seen.add(x)
  return True

########NEW FILE########
__FILENAME__ = blacksholes
#runas BlackScholes(range(1,100), range(1,100), range(1,100), 0.5, 0.76, 12)
#bench BlackScholes(range(1,400001), range(1,400001), range(1,400001), 0.5, 0.76, 400000)
#pythran export BlackScholes(float list, float list, float list, float, float, int)
import math


def BlackScholes(stock_price, option_strike, option_years, Riskfree,  Volatility, nb_opt):
    RSQRT2PI = 1 / math.sqrt(math.pi * 2)
    A1 = 0.31938153
    A2 = -0.356563782
    A3 = 1.781477937
    A4 = -1.821255978
    A5 = 1.330274429
    call_result = []
    put_result = []
    for opt in xrange(0, nb_opt) :
        sqrtT = math.sqrt(option_years[opt])
        d1 = math.log(stock_price[opt] / option_strike[opt])
        d1 += (Riskfree + 0.5 * Volatility * Volatility) * option_years[opt]
        d1 /= (Volatility * sqrtT)
        d2 = d1 - Volatility * sqrtT
        K = 1.0 / (1.0 + 0.2316419 * abs(d1))
        CNDD1 = RSQRT2PI * math.exp(-0.5 * d1 * d1) * (K * (A1 + K * (A2 + K * (A3 + K * (A4 + K * A5)))))
        K = 1.0 / (1.0 + 0.2316419 * abs(d2))
        CNDD2 = RSQRT2PI * math.exp(-0.5 * d2 * d2) * (K * (A1 + K * (A2 + K * (A3 + K * (A4 + K * A5)))))
        expRT = math.exp(-Riskfree * option_years[opt])
        call_result.append(stock_price[opt] * CNDD1 - option_strike[opt] * expRT * CNDD2)
        put_result.append(option_strike[opt] * expRT * (1.0 - CNDD2) - stock_price[opt] * (1.0 - CNDD1))
    return call_result, put_result

########NEW FILE########
__FILENAME__ = brownian
#pythran export brownian_bridge(int, int, float, float, int)
#runas brownian_bridge(1,5,1.35,2.65,4)
#bench brownian_bridge(1,5,0.35,4.65,100000)

import random
from math import sqrt

def linspace(begin, end, nbsteps):
    assert begin < end
    return [ begin + i*(end-begin)/nbsteps for i in xrange(nbsteps) ]

def zeros(n): return [0.]*n

# should be "from random import gauss as norm", but not reproducible...
def norm(m,u):
    return ((m*u+0.15)%1)



# moyenne du pont en t entre les points (t1,b1) et (t2,b2):
def moy(t1,t2,b1,b2,t): return (1.*(t2*b1-t1*b2)+t*(b2-b1))/(t2-t1)
def p(t): t=1
# variance du pont en t entre les points (t1,b1) et (t2,b2):
def var(t1,t2,b1,b2,t): return (1.*t-t1)*(t2-t)/(t2-t1)

def brownian_bridge(ti, tf, bi, bf, n):
    """
    simulation d'un pont brownien sur [ti,tf],
    avec les valeurs extremes bi et bf
    et n points par unite de temps
    sortie :
    - T   : positions temporelles des echantillons
    - B   : valeurs des echantillons
    """

    n        = int(n*(tf-ti))     # nombre de points
    T        = linspace(ti,tf,n)  # points d'echantillonnage
    pas      = (tf-ti)/(n-1.)     # pas d'echantillonnage
    B        = zeros(n)           # initialisation du brownien
    B[0]     = bi                 # valeur initiale
    B[n-1]   = bf                 # valeur finale
    t1       = ti
    for k in range(1,n-1):               # construction du pont en ti+k*pas
        m = moy(t1,tf,B[k-1],bf,t1+pas)  # sur les intervalle [ti+(k-1)*pas,tf]
        v = var(t1,tf,B[k-1],bf,t1+pas)  # avec les valeurs limites B[k-1],et bf
        B[k] = m+sqrt(v)*norm(0,1)
        t1  += pas
    return T, B

########NEW FILE########
__FILENAME__ = bubble_sort
#adapted from http://www.daniweb.com/software-development/python/code/216689/sorting-algorithms-in-python
#pythran export bubble_sort(int list)
#runas bubble_sort([-4,1,45,-6,123,4,6,1,34,-8,12])
#bench import random; in_ = random.sample(xrange(1000000000), 4000); bubble_sort(in_)
def bubble_sort(list0):
    list1=[x for x in list0 ] # simulate copy
    for i in xrange(0, len(list1) - 1):
        swap_test = False
        for j in range(0, len(list1) - i - 1):
            if list1[j] > list1[j + 1]:
                list1[j], list1[j + 1] = list1[j + 1], list1[j]  # swap
            swap_test = True
        if swap_test == False:
            break
    return list1

########NEW FILE########
__FILENAME__ = calculate_u
# from the paper `using cython to speedup numerical python programs'
#pythran export timeloop(float, float, float, float, float, float list list, float list list, float list list)
#bench A=[range(70) for i in xrange(100)] ; B=[range(70) for i in xrange(100)] ; C=[range(70) for i in xrange(100)] ; timeloop(1,2,.01,.1,.18, A,B,C )
#runas A=[range(20) for i in xrange(10)] ; B=[range(20) for i in xrange(10)] ; C=[range(20) for i in xrange(10)] ; timeloop(1,2,.01,.1,.18, A,B,C )
def timeloop(t, t_stop, dt, dx, dy, u, um, k):
    while t <= t_stop:
        t += dt
        new_u = calculate_u(dt, dx, dy, u, um, k)
        um = u
        u = new_u
    return u

def calculate_u(dt, dx, dy, u, um, k):
    up = [ [0.]*len(u[0]) for i in xrange(len(u)) ]
    "omp parallel for"
    for i in xrange(1, len(u)-1):
        for j in xrange(1, len(u[0])-1):
            up[i][j] = 2*u[i][j] - um[i][j] + \
                (dt/dx)**2*(
                        (0.5*(k[i+1][j] + k[i][j])*(u[i+1][j] - u[i][j]) -
                            0.5*(k[i][j] + k[i-1][j])*(u[i][j] - u[i-1][j]))) + \
                        (dt/dy)**2*(
                                (0.5*(k[i][j+1] + k[i][j])*(u[i][j+1] - u[i][j]) -
                                    0.5*(k[i][j] + k[i][j-1])*(u[i][j] - u[i][j-1])))
    return up

########NEW FILE########
__FILENAME__ = caxpy
#pythran export CAXPY(int, complex, complex list, int, complex list, int)
#runas CAXPY(2,complex(1.1,2.3),[complex(1,2),complex(2,3),complex(3,4),complex(5,6)],2,[complex(3,4),complex(1,2),complex(2,3),complex(5,6)],3)
def CAXPY(N,CA,CX,INCX,CY,INCY):
#  Purpose
#  =======
#
#     CAXPY constant times a vector plus a vector.
#
#  Further Details
#  ===============
#
#     jack dongarra, linpack, 3/11/78.
#     modified 12/3/93, array(1) declarations changed to array(#)
#
#  =====================================================================
#
        if N <= 0:
                return
        if (abs(CA) == 0.0E+0):
                return
        if (INCX == 1 and INCY == 1):
                "omp parallel for"
                for I in range(N):
                        CY[I] = CY[I] + CA*CX[I]
#
#        code for both increments equal to 1
#
        else:
#
#        code for unequal increments or equal increments
#          not equal to 1
#
                IX = 0
                IY = 0
                if (INCX < 0):
                        IX = (-N+1)*INCX
                if (INCY < 0):
                        IY = (-N+1)*INCY
                for I in range(N):
                        CY[IY] = CY[IY] + CA*CX[IX]
                        IX = IX + INCX
                        IY = IY + INCY
        return CY

########NEW FILE########
__FILENAME__ = ccopy
#pythran export CCOPY(int, complex list, int, complex list, int)
#runas CCOPY(2,[complex(1,2),complex(2,3),complex(3,4),complex(5,6)],2,[complex(3,4),complex(1,2),complex(2,3),complex(5,6)],3)
#bench sz = 20000000; in1 = map(complex, xrange(sz), xrange(sz)); in2 = map(complex, xrange(sz), xrange(sz));CCOPY(sz / 6,in1,2,in2,3)
def CCOPY(N,CX,INCX,CY,INCY):
#  Purpose
#  =======
#
#     CCOPY copies a vector x to a vector y.
#
#  Further Details
#  ===============
#
#
#  =====================================================================
#
      	if N <= 0:
		return
      	if (INCX==1 and INCY==1):
#
#        code for both increments equal to 1
#
		for I in range(N):
			CY[I] = CX[I]
	else:
#
#        code for unequal increments or equal increments
#          not equal to 1
#
	        IX = 0
        	IY = 0
		if (INCX < 0):
			IX = (-N+1)*INCX
		if (INCY < 0):
			IY = (-N+1)*INCY
		for I in range(N):
			CY[IY] = CX[IX]
	            	IX = IX + INCX
        	    	IY = IY + INCY
	return

########NEW FILE########
__FILENAME__ = cdotc
#pythran export CDOTC(int, complex list, int, complex list, int)
#runas CDOTC(2,[complex(1,2),complex(2,3),complex(3,4),complex(5,6)],2,[complex(3,4),complex(1,2),complex(2,3),complex(5,6)],3)
#bench sz = 20000000; in1 = map(complex, xrange(sz), xrange(sz)); in2 = map(complex, xrange(sz), xrange(sz));CDOTC(sz / 6,in1,2,in2,3)
def CDOTC(N,CX,INCX,CY,INCY):
#     .. Scalar Arguments ..
#      INTEGER INCX,INCY,N
#     ..
#     .. Array Arguments ..
#      COMPLEX CX(#),CY(#)
#     ..
#
#  Purpose
#  =======
#
#     forms the dot product of two vectors, conjugating the first
#     vector.
#
#  Further Details
#  ===============
#
#     jack dongarra, linpack,  3/11/78.
#     modified 12/3/93, array(1) declarations changed to array(#)
#
#  =====================================================================
#
    CTEMP = complex(0.0,0.0)
    CDOTC = complex(0.0,0.0)
    if (N <= 0):
        return
    if (INCX == 1 and  INCY == 1):

#
#        code for both increments equal to 1
#
        for I in range(N):
            CTEMP = CTEMP + (CX[I].conjugate())*CY[I]
    else:
#
#        code for unequal increments or equal increments
#          not equal to 1
#
        IX = 0
        IY = 0
        if (INCX < 0):
            IX = (-N+1)*INCX
        if (INCY < 0):
            IY = (-N+1)*INCY
        for I in range(N):
            CTEMP = CTEMP + (CX[IX].conjugate())*CY[IY]
            IX = IX + INCX
            IY = IY + INCY
    return CTEMP


########NEW FILE########
__FILENAME__ = cdotu
#pythran export CDOTU(int, complex list, int, complex list, int)
#runas CDOTU(2,[complex(1,2),complex(2,3),complex(3,4),complex(5,6)],2,[complex(3,4),complex(1,2),complex(2,3),complex(5,6)],3)
#bench sz = 20000000; in1 = map(complex, xrange(sz), xrange(sz)); in2 = map(complex, xrange(sz), xrange(sz));CDOTU(sz / 6,in1,2,in2,3)
def CDOTU(N,CX,INCX,CY,INCY):
#     .. Scalar Arguments ..
#     INTEGER INCX,INCY,N
#     ..
#     .. Array Arguments ..
#     COMPLEX CX(#),CY(#)
#     ..
#
#  Purpose
#  =======
#
#     CDOTU forms the dot product of two vectors.
#
#  Further Details
#  ===============
#
#     jack dongarra, linpack, 3/11/78.
#     modified 12/3/93, array(1) declarations changed to array(#)
#
#  =====================================================================
#
#     .. Local Scalars ..
#     COMPLEX CTEMP
#     INTEGER I,IX,IY
#     ..
      	CTEMP = complex(0.0,0.0)
	CDOTU = complex(0.0,0.0)
      	if (N <= 0):
		return
    	if (INCX == 1 and INCY == 1):
#
#        code for both increments equal to 1
#
		for I in range(N):
			CTEMP = CTEMP + CX[I]*CY[I]
      	else:
#
#        code for unequal increments or equal increments
#          not equal to 1
#
         	IX = 0
         	IY = 0
	 	if (INCX < 0):
			IX = (-N+1)*INCX
	 	if (INCY < 0):
			IY = (-N+1)*INCY
	 	for I in range(N):
            		CTEMP = CTEMP + CX[IX]*CY[IY]
            		IX = IX + INCX
            		IY = IY + INCY
      	return CTEMP

########NEW FILE########
__FILENAME__ = crotg
#pythran export CROTG(complex, complex, float, complex)
#runas CROTG(complex(1,2),complex(5,6),3.4,complex(10,-3))
import math

def CROTG(CA,CB,C=0,S=0):
#     .. Scalar Arguments ..
#      COMPLEX CA,CB,S
#      REAL C
#     ..
#
#  Purpose
#  =======
#
#  CROTG determines a complex Givens rotation.
#
#  =====================================================================
#
#     .. Local Scalars ..
#      COMPLEX ALPHA
#      REAL NORM,SCALE
#     ..
    if (abs(CA) == 0.):
        C = 0.
        S = complex(1.,0.)
        CA = CB
    else:
        SCALE = abs(CA) + abs(CB)
        NORM = SCALE*math.sqrt((abs(CA/SCALE))**2+ (abs(CB/SCALE))**2)
        ALPHA = CA/abs(CA)
        C = abs(CA)/NORM
        S = ALPHA*(CB.conjugate())/NORM
        CA = ALPHA*NORM
    return [CA,CB,C,S]




########NEW FILE########
__FILENAME__ = deriv
#pythran export deriv(int, float, complex, complex list, complex list, complex list, complex list list, float)
#runas deriv(3,4.5,complex(2,3),[complex(3,4),complex(1,2),complex(2,3),complex(5,6)],[complex(1,2),complex(2,3),complex(5,6),complex(3,4)],[complex(2,3),complex(3,4),complex(1,2),complex(5,6)],[[complex(2,3),complex(3,4),complex(1,2),complex(5,6)],[complex(2,3),complex(3,4),complex(1,2),complex(5,6)],[complex(2,3),complex(3,4),complex(1,2),complex(5,6)],[complex(2,3),complex(3,4),complex(1,2),complex(5,6)],[complex(2,3),complex(3,4),complex(1,2),complex(5,6)]],3.5)
def deriv(n,sig,alp,dg,dh1,dh3,bin,nu):
    dh2=[complex(0,0) for _ in dh1]
    ci = complex(0.0,1.0)
    dh1[0]=complex(0.5,0)*ci*complex(sig,0)
    exp1 = complex(-0.5,0)
    dh2[0]=alp;
    exp2 = complex(-1.0,0)
    dh3[0]=-2.0*nu
    exp3 = complex(-1.0,0)
    for i in range(1,n):
        dh1[i]=dh1[i-1]*exp1
        exp1=exp1-1.0
        dh2[i]=dh2[i-1]*exp2
        exp2=exp2-1.0
        dh3[i]=-nu*dh3[i-1]*exp3
        exp3=exp3-1.0
    dg[0]=1.0
    dg[1]=dh1[0]+dh2[0]+dh3[0]
    for i in range(2,n+1):
        dg[i]=dh1[i-1]+dh2[i-1]+dh3[i-1]
        for j in range(1,i):
            dg[i]=dg[i]+bin[j-1][i-1]*(dh1[j-1]+dh2[j-1]+dh3[j-1])*dg[i-j]
    return dg

########NEW FILE########
__FILENAME__ = deuxd_convolution
#pythran export conv(float[][], float[][])
#runas import numpy as np ; x = np.tri(300,300)*0.5 ; w = np.tri(5,5)*0.25 ; conv(x,w)
#bench import numpy as np ; x = np.tri(150,150)*0.5 ; w = np.tri(5,5)*0.25 ; conv(x,w)
import numpy as np

def clamp(i, offset, maxval):
    j = max(0, i + offset)
    return min(j, maxval)


def reflect(pos, offset, bound):
    idx = pos+offset
    return min(2*(bound-1)-idx,max(idx,-idx))


def conv(x, weights):
    sx = x.shape
    sw = weights.shape
    result = np.zeros_like(x)
    for i in xrange(sx[0]):
        for j in xrange(sx[1]):
            for ii in xrange(sw[0]):
                for jj in xrange(sw[1]):
                    idx = clamp(i,ii-sw[0]/2,sw[0]), clamp(j,jj-sw[0]/2,sw[0])
                    result[i,j] += x[idx] * weights[ii,jj]
    return result

########NEW FILE########
__FILENAME__ = diffusion_numpy
#pythran export diffuseNumpy(float [][], float [][], int)
#runas import numpy as np;lx,ly=(2**7,2**7);u=np.zeros([lx,ly],dtype=np.double);u[lx/2,ly/2]=1000.0;tempU=np.zeros([lx,ly],dtype=np.double);diffuseNumpy(u,tempU,500)
#unittest.skip gsliced array error (dep not taken into account)

import numpy as np


def diffuseNumpy(u, tempU, iterNum):
    """
    Apply Numpy matrix for the Forward-Euler Approximation
    """
    mu = .1

    for n in range(iterNum):
        tempU[1:-1, 1:-1] = u[1:-1, 1:-1] + mu * (
            u[2:, 1:-1] - 2 * u[1:-1, 1:-1] + u[0:-2, 1:-1] +
            u[1:-1, 2:] - 2 * u[1:-1, 1:-1] + u[1:-1, 0:-2])
        u[:, :] = tempU[:, :]
        tempU[:, :] = 0.0

########NEW FILE########
__FILENAME__ = diffusion_pure_python
# Reference: http://continuum.io/blog/the-python-and-the-complied-python
#pythran export diffusePurePython(float [][], float [][], int)
#runas import numpy as np;lx,ly=(2**7,2**7);u=np.zeros([lx,ly],dtype=np.double);u[lx/2,ly/2]=1000.0;tempU=np.zeros([lx,ly],dtype=np.double);diffusePurePython(u,tempU,500)
#bench import numpy as np;lx,ly=(2**6,2**6);u=np.zeros([lx,ly],dtype=np.double);u[lx/2,ly/2]=1000.0;tempU=np.zeros([lx,ly],dtype=np.double);diffusePurePython(u,tempU,55)

import numpy as np


def diffusePurePython(u, tempU, iterNum):
    """
    Apply nested iteration for the Forward-Euler Approximation
    """
    mu = .1
    row = u.shape[0]
    col = u.shape[1]

    for n in range(iterNum):
        for i in range(1, row - 1):
            for j in range(1, col - 1):
                tempU[i, j] = u[i, j] + mu * (
                    u[i + 1, j] - 2 * u[i, j] + u[i - 1, j] +
                    u[i, j + 1] - 2 * u[i, j] + u[i, j - 1])
        for i in range(1, row - 1):
            for j in range(1, col - 1):
                u[i, j] = tempU[i, j]
                tempU[i, j] = 0.0

########NEW FILE########
__FILENAME__ = emin
#from https://gist.github.com/andersx/6061586
#runas run()
#bench run()
#pythran export run()

# A simple energy minimization program that uses steepest descent 
# and a force field to minimize the energy of water in internal coordinates.
# Written by Jan H. Jensen, 2013


def Eandg(rOH,thetaHOH):

    """"
    Arguments: (internal coordinates of the water molecule)

    rOH            O-H bond distance
    thetaHOH       H-O-H bond angle


    Returns:

    E              Molecular force field energy
    grOH           O-H bond stretch gradient
    grthetaHOH     H-O-H bond angle bend gradient 

    
    Force field parameters:

    kOH            Harmonic force constant, O-H bond strech
    rOHe           Equilibrium distance, O-H
    kHOH           Harmonic angle bend force constant, H-O-H angle bend
    thetaHOHe      Equilibrium angle, H-O-H

    """

    kOH = 50.0
    rOHe = 0.95
    kHOH = 50.0
    thetaHOHe = 104.5


    E = 2 * kOH * (rOH - rOHe)**2 + kHOH * (thetaHOH - thetaHOHe)**2
    grOH = 2 * kOH * (rOH - rOHe)
    grthetaHOH = 2 * kHOH * (thetaHOH - thetaHOHe)

    return (E, grOH, grthetaHOH)

def run():
    c = 0.005
    n_steps = 1000000

    #starting geometry
    rOH = 10.0
    thetaHOH = 180.0



    for i in range(n_steps):
        (E,grOH,gthetaHOH) = Eandg(rOH,thetaHOH)
        if (abs(grOH) >0.001/c or abs(gthetaHOH) > 0.01/c ):
            rOH = rOH - c*grOH
            thetaHOH = thetaHOH - c*gthetaHOH

    converged = (abs(grOH) >0.001/c or abs(gthetaHOH) > 0.01/c )

    return converged, E,rOH,thetaHOH

########NEW FILE########
__FILENAME__ = euler13
#pythran export solve(int)
#runas solve(0)
def solve(v):
    t = (
    37107287533902102798797998220837590246510135740250,
    46376937677490009712648124896970078050417018260538,
    74324986199524741059474233309513058123726617309629,
    91942213363574161572522430563301811072406154908250,
    23067588207539346171171980310421047513778063246676,
    89261670696623633820136378418383684178734361726757,
    28112879812849979408065481931592621691275889832738,
    44274228917432520321923589422876796487670272189318,
    47451445736001306439091167216856844588711603153276,
    70386486105843025439939619828917593665686757934951,
    62176457141856560629502157223196586755079324193331,
    64906352462741904929101432445813822663347944758178,
    92575867718337217661963751590579239728245598838407,
    58203565325359399008402633568948830189458628227828,
    80181199384826282014278194139940567587151170094390,
    35398664372827112653829987240784473053190104293586,
    86515506006295864861532075273371959191420517255829,
    71693888707715466499115593487603532921714970056938,
    54370070576826684624621495650076471787294438377604,
    53282654108756828443191190634694037855217779295145,
    36123272525000296071075082563815656710885258350721,
    45876576172410976447339110607218265236877223636045,
    17423706905851860660448207621209813287860733969412,
    81142660418086830619328460811191061556940512689692,
    51934325451728388641918047049293215058642563049483,
    62467221648435076201727918039944693004732956340691,
    15732444386908125794514089057706229429197107928209,
    55037687525678773091862540744969844508330393682126,
    18336384825330154686196124348767681297534375946515,
    80386287592878490201521685554828717201219257766954,
    78182833757993103614740356856449095527097864797581,
    16726320100436897842553539920931837441497806860984,
    48403098129077791799088218795327364475675590848030,
    87086987551392711854517078544161852424320693150332,
    59959406895756536782107074926966537676326235447210,
    69793950679652694742597709739166693763042633987085,
    41052684708299085211399427365734116182760315001271,
    65378607361501080857009149939512557028198746004375,
    35829035317434717326932123578154982629742552737307,
    94953759765105305946966067683156574377167401875275,
    88902802571733229619176668713819931811048770190271,
    25267680276078003013678680992525463401061632866526,
    36270218540497705585629946580636237993140746255962,
    24074486908231174977792365466257246923322810917141,
    91430288197103288597806669760892938638285025333403,
    34413065578016127815921815005561868836468420090470,
    23053081172816430487623791969842487255036638784583,
    11487696932154902810424020138335124462181441773470,
    63783299490636259666498587618221225225512486764533,
    67720186971698544312419572409913959008952310058822,
    95548255300263520781532296796249481641953868218774,
    76085327132285723110424803456124867697064507995236,
    37774242535411291684276865538926205024910326572967,
    23701913275725675285653248258265463092207058596522,
    29798860272258331913126375147341994889534765745501,
    18495701454879288984856827726077713721403798879715,
    38298203783031473527721580348144513491373226651381,
    34829543829199918180278916522431027392251122869539,
    40957953066405232632538044100059654939159879593635,
    29746152185502371307642255121183693803580388584903,
    41698116222072977186158236678424689157993532961922,
    62467957194401269043877107275048102390895523597457,
    23189706772547915061505504953922979530901129967519,
    86188088225875314529584099251203829009407770775672,
    11306739708304724483816533873502340845647058077308,
    82959174767140363198008187129011875491310547126581,
    97623331044818386269515456334926366572897563400500,
    42846280183517070527831839425882145521227251250327,
    55121603546981200581762165212827652751691296897789,
    32238195734329339946437501907836945765883352399886,
    75506164965184775180738168837861091527357929701337,
    62177842752192623401942399639168044983993173312731,
    32924185707147349566916674687634660915035914677504,
    99518671430235219628894890102423325116913619626622,
    73267460800591547471830798392868535206946944540724,
    76841822524674417161514036427982273348055556214818,
    97142617910342598647204516893989422179826088076852,
    87783646182799346313767754307809363333018982642090,
    10848802521674670883215120185883543223812876952786,
    71329612474782464538636993009049310363619763878039,
    62184073572399794223406235393808339651327408011116,
    66627891981488087797941876876144230030984490851411,
    60661826293682836764744779239180335110989069790714,
    85786944089552990653640447425576083659976645795096,
    66024396409905389607120198219976047599490197230297,
    64913982680032973156037120041377903785566085089252,
    16730939319872750275468906903707539413042652315011,
    94809377245048795150954100921645863754710598436791,
    78639167021187492431995700641917969777599028300699,
    15368713711936614952811305876380278410754449733078,
    40789923115535562561142322423255033685442488917353,
    44889911501440648020369068063960672322193204149535,
    41503128880339536053299340368006977710650566631954,
    81234880673210146739058568557934581403627822703280,
    82616570773948327592232845941706525094512325230608,
    22918802058777319719839450180888072429661980811197,
    77158542502016545090413245809786882778948721859617,
    72107838435069186155435662884062257473692284509516,
    20849603980134001723930671666823555245252804609722,
    53503534226472524250874054075591789781264330331690,
    )
    # prevent constant evaluation
    return str(sum(t) + v)[0:10]


########NEW FILE########
__FILENAME__ = euler14
#!/usr/bin/env python
# taken from http://www.ripton.net/blog/?p=51
#pythran export euler14(int)
#runas euler14(1000000)
#bench euler14(650000)

"""Project Euler, problem 14

The following iterative sequence is defined for the set of positive integers:

n -> n / 2 (n is even)
n -> 3n + 1 (n is odd)

Which starting number, under one million, produces the longest chain?
"""

def next_num(num):
    if num & 1:
        return 3 * num + 1
    else:
        return num // 2



def series_length(num, lengths):
    if num in lengths:
        return lengths[num]
    else:
        num2 = next_num(num)
        result = 1 + series_length(num2, lengths)
        lengths[num] = result
        return result

def euler14(MAX_NUM):
    num_with_max_length = 1
    max_length = 0
    lengths = {1: 0}
    for ii in xrange(1, MAX_NUM):
        length = series_length(ii, lengths)
        if length > max_length:
            max_length = length
            num_with_max_length = ii
    return num_with_max_length, max_length

########NEW FILE########
__FILENAME__ = extrema
#runas run_extrema(10,[1.2,3.4,5.6,7.8,9.0,2.1,4.3,5.4,6.5,7.8])
#bench import random; n=3000000; a = [random.random() for i in xrange(n)]; run_extrema(n, a)
#pythran export run_extrema(int, float list)
def extrema_op(a, b):
    a_min_idx, a_min_val, a_max_idx, a_max_val = a
    b_min_idx, b_min_val, b_max_idx, b_max_val = b
    if a_min_val < b_min_val:
        if a_max_val > b_max_val:
            return a
        else:
            return a_min_idx, a_min_val, b_max_idx, b_max_val
    else:
        if a_max_val > b_max_val:
            return b_min_idx, b_min_val, a_max_idx, a_max_val
        else:
            return b

def extrema_id(x):
    return -1, 1., 1, 0.

def indices(A):
    return xrange(len(A))

def extrema(x, x_id):
    return reduce(extrema_op, zip(indices(x), x, indices(x), x), x_id)

def run_extrema(n,a):
    #import random
    #a = [random.random() for i in xrange(n)]

    a_id = extrema_id(0.)
    return extrema(a, a_id)

########NEW FILE########
__FILENAME__ = factorize_naive
#taken from http://eli.thegreenplace.net/2012/01/16/python-parallelizing-cpu-bound-tasks-with-multiprocessing/

#pythran export factorize_naive(long)
#runas factorize_naive(12222L)
#bench factorize_naive(3241618756762348687L)
def factorize_naive(n):
    """ A naive factorization method. Take integer 'n', return list of
        factors.
    """
    if n < 2:
        return []
    factors = []
    p = 2L

    while True:
        if n == 1:
            return factors

        r = n % p
        if r == 0:
            factors.append(p)
            n = n / p
        elif p * p >= n:
            factors.append(n)
            return factors
        elif p > 2:
            # Advance in steps of 2 over odd numbers
            p += 2
        else:
            # If p == 2, get to 3
            p += 1
    assert False, "unreachable"

########NEW FILE########
__FILENAME__ = fannkuch
#imported from https://bitbucket.org/pypy/benchmarks/src/846fa56a282b0e8716309f891553e0af542d8800/own/fannkuch.py?at=default
#pythran export fannkuch(int)
#runas fannkuch(9)
#bench fannkuch(9)

def fannkuch(n):
    count = range(1, n+1)
    max_flips = 0
    m = n-1
    r = n
    check = 0
    perm1 = range(n)
    perm = range(n)

    while 1:
        if check < 30:
            #print "".join(str(i+1) for i in perm1)
            check += 1

        while r != 1:
            count[r-1] = r
            r -= 1

        if perm1[0] != 0 and perm1[m] != m:
            perm = perm1[:]
            flips_count = 0
            k = perm[0]
            while k:
                perm[:k+1] = perm[k::-1]
                flips_count += 1
                k = perm[0]

            if flips_count > max_flips:
                max_flips = flips_count

        while r != n:
            perm1.insert(r, perm1.pop(0))
            count[r] -= 1
            if count[r] > 0:
                break
            r += 1
        else:
            return max_flips


########NEW FILE########
__FILENAME__ = fbcorr
# from https://github.com/numba/numba/blob/master/examples/fbcorr.py
#pythran export fbcorr(float list list list list, float list list list list)
#runas imgs = [ [ [ [ i+j+k for i in xrange(3) ] for j in xrange(16) ] for j in xrange(16) ] for k in xrange(16) ]; filters = [ [ [ [ i+2*j-k for i in xrange(3) ] for j in xrange(5) ] for j in xrange(5) ] for k in xrange(6) ] ; fbcorr(imgs, filters)
#bench imgs = [ [ [ [ i+j+k for i in xrange(11) ] for j in xrange(16) ] for j in xrange(16) ] for k in xrange(16) ]; filters = [ [ [ [ i+2*j-k for i in xrange(11) ] for j in xrange(5) ] for j in xrange(5) ] for k in xrange(6) ] ; fbcorr(imgs, filters)

def fbcorr(imgs, filters):
    n_imgs, n_rows, n_cols, n_channels = (len(imgs), len(imgs[0]), len(imgs[0][0]), len(imgs[0][0][0]))
    n_filters, height, width, n_ch2 = (len(filters), len(filters[0]), len(filters[0][0]), len(filters[0][0][0]))
    output = [ [ [ [ 0 for i in xrange(n_cols - width + 1) ] for j in xrange(n_rows - height + 1) ] for k in xrange(n_filters) ] for l in xrange(n_imgs) ]
    for ii in xrange(n_imgs):
        for rr in xrange(n_rows - height + 1):
            for cc in xrange(n_cols - width + 1):
                for hh in xrange(height):
                    for ww in xrange(width):
                        for jj in xrange(n_channels):
                            for ff in xrange(n_filters):
                                imgval = imgs[ii][rr + hh][cc + ww][jj]
                                filterval = filters[ff][hh][ww][jj]
                                output[ii][ff][rr][cc] += imgval * filterval
    return output

########NEW FILE########
__FILENAME__ = fbcorr_numpy
"""
This file demonstrates a filterbank correlation loop.
"""

#pythran export fbcorr(float[][][][], float[][][][], float[][][][])
#bench import numpy; in_ = numpy.arange(10*20*30*7.).reshape(10,20,30,7); filter = numpy.arange(2*3*4*7.).reshape(2,3,4,7); out = numpy.empty((10,2,18,27), dtype=numpy.float); fbcorr(in_, filter, out)
def fbcorr(imgs, filters, output):
    n_imgs, n_rows, n_cols, n_channels = imgs.shape
    n_filters, height, width, n_ch2 = filters.shape

    "omp parallel for"
    for ii in range(n_imgs):
        for rr in range(n_rows - height + 1):
            for cc in range(n_cols - width + 1):
                for hh in xrange(height):
                    for ww in xrange(width):
                        for jj in range(n_channels):
                            for ff in range(n_filters):
                                imgval = imgs[ii, rr + hh, cc + ww, jj]
                                filterval = filters[ff, hh, ww, jj]
                                output[ii, ff, rr, cc] += imgval * filterval


########NEW FILE########
__FILENAME__ = fdtd
#from http://stackoverflow.com/questions/19367488/converting-function-to-numbapro-cuda
#pythran export fdtd(float[][], int)
#runas import numpy ; a = numpy.ones((1000,1000)); fdtd(a,20)
#bench import numpy ; a = numpy.arange(10000.).reshape(100,100); fdtd(a,25)
import numpy as np

def fdtd(input_grid, steps):
    grid = input_grid.copy()
    old_grid = np.zeros_like(input_grid)
    previous_grid = np.zeros_like(input_grid)

    l_x = grid.shape[0]
    l_y = grid.shape[1]

    for i in range(steps):
        np.copyto(previous_grid, old_grid)
        np.copyto(old_grid, grid)

        for x in range(l_x):
            for y in range(l_y):
                grid[x,y] = 0.0
                if 0 < x+1 < l_x:
                    grid[x,y] += old_grid[x+1,y]
                if 0 < x-1 < l_x:
                    grid[x,y] += old_grid[x-1,y]
                if 0 < y+1 < l_y:
                    grid[x,y] += old_grid[x,y+1]
                if 0 < y-1 < l_y:
                    grid[x,y] += old_grid[x,y-1]

                grid[x,y] /= 2.0
                grid[x,y] -= previous_grid[x,y]

    return grid

########NEW FILE########
__FILENAME__ = fft
#pythran export fft(complex [])
#runas from numpy import ones ; a = ones(2**10, dtype=complex) ; fft(a)
#bench from numpy import ones ; a = ones(2**14, dtype=complex) ; fft(a)

import math, numpy as np

def fft(x):
   N = x.shape[0]
   if N == 1:
       return np.array(x)
   e=fft(x[::2])
   o=fft(x[1::2])
   M=N//2
   l=[ e[k] + o[k]*math.e**(-2j*math.pi*k/N) for k in xrange(M) ]
   r=[ e[k] - o[k]*math.e**(-2j*math.pi*k/N) for k in xrange(M) ]
   return np.array(l+r)


########NEW FILE########
__FILENAME__ = fibo
#pythran export test(int)
#runas test(12)
#bench test(33)
def rfibo(n):
    if n < 2: return n
    else:
        n_1 = rfibo(n-1)
        n_2 = rfibo(n-2)
        return n_1 + n_2
def fibo(n):
    if n < 10: return rfibo(n)
    else:
        n_1 = 0
        "omp task shared(n,n_1)"
        n_1 = fibo(n-1)
        n_2 = fibo(n-2)
        "omp taskwait"
        return n_1 + n_2

def test(n):
    "omp parallel"
    "omp single"
    f = fibo(n)
    return f

########NEW FILE########
__FILENAME__ = fibo_seq
#pythran export fibo(int)
#runas fibo(700)
#bench fibo(300000)
def fibo(n):
    a,b = 1L,1L
    for i in range(n):
        a,b = a+b, a
    return a

########NEW FILE########
__FILENAME__ = gauss
#pythran export gauss(int, float list list, float list)
#pythran export gauss(int, complex list list, complex list)
#runas gauss(4,[[10.0,-6.0,3.5,3.2],[6.7,2.8,-.65,1.2],[9.2,3.0,5.4,1.3],[1.6,8.3,2.5,5.2]],[33.4,4.5,-5.4,-13.4])
def pivot(n,i,a,b):
    i0=i
    amp0=abs(a[i-1][i-1])
    for j in range(i+1,n+1):
        amp=abs(a[i-1][j-1])
        if amp>amp0:
            i0=j
            amp0=amp
    if i==i0:
        return
    temp=b[i-1]
    b[i-1]=b[i0-1];
    b[i0-1]=temp;
    for j in range(i,n+1):
        temp=a[j-1][i-1]
        a[j-1][i-1]=a[j-1][i0-1]
        a[j-1][i0-1]=temp

def gauss(n,a,b):
#     Downward elimination.
    for i in range(1,n+1):
        if i<n:
            pivot(n,i,a,b)
        a[i-1][i-1]=1.0/a[i-1][i-1]
        b[i-1]=b[i-1]*a[i-1][i-1]
        if i<n:
            for j in range(i+1,n+1):
                a[j-1][i-1]=a[j-1][i-1]*a[i-1][i-1]
            for k in range(i+1,n+1):
                b[k-1]=b[k-1]-a[i-1][k-1]*b[i-1]
                for j in range(i+1,n+1):
                    a[j-1][k-1]=a[j-1][k-1]-a[i-1][k-1]*a[j-1][i-1]
#     Back substitution.
    for i in range(n-1,0,-1):
        for j in range(i,n):
            b[i-1]=b[i-1]-a[j][i-1]*b[j]
    return b


########NEW FILE########
__FILENAME__ = growcut
#from http://continuum.io/blog/numba_performance
#runas test(50)
#bench test(28)

import math
import numpy as np
def window_floor(idx, radius):
    if radius > idx:
        return 0
    else:
        return idx - radius


def window_ceil(idx, ceil, radius):
    if idx + radius > ceil:
        return ceil
    else:
        return idx + radius

def python_kernel(image, state, state_next, window_radius):
    changes = 0
    sqrt_3 = math.sqrt(3.0)

    height = image.shape[0]
    width = image.shape[1]

    for j in xrange(width):
        for i in xrange(height):

            winning_colony = state[i, j, 0]
            defense_strength = state[i, j, 1]

            for jj in xrange(window_floor(j, window_radius),
                             window_ceil(j+1, width, window_radius)):
                for ii in xrange(window_floor(i, window_radius),
                                 window_ceil(i+1, height, window_radius)):
                    if (ii == i and jj == j):
                        continue

                    d = image[i, j, 0] - image[ii, jj, 0]
                    s = d * d
                    for k in range(1, 3):
                        d = image[i, j, k] - image[ii, jj, k]
                        s += d * d
                    gval = 1.0 - math.sqrt(s)/sqrt_3

                    attack_strength = gval * state[ii, jj, 1]

                    if attack_strength > defense_strength:
                        defense_strength = attack_strength
                        winning_colony = state[ii, jj, 0]
                        changes += 1

            state_next[i, j, 0] = winning_colony
            state_next[i, j, 1] = defense_strength

    return changes

#pythran export test(int)
def test(N):
    image = np.zeros((N, N, 3))
    state = np.zeros((N, N, 2))
    state_next = np.empty_like(state)


    # colony 1 is strength 1 at position 0,0
    # colony 0 is strength 0 at all other positions
    state[0, 0, 0] = 1
    state[0, 0, 1] = 1
    return python_kernel(image, state, state_next, 10)

########NEW FILE########
__FILENAME__ = guerre
#pythran export guerre(complex list, int, complex, float, int)
#runas guerre([complex(1,2),complex(3,4),complex(5,6),complex(7,8)],2,complex(5.6,4.3),-3.4,20)
#bench guerre([complex(1,2),complex(3,4),complex(5,6),complex(7,8)],2,complex(5.6,4.3),-3.4,400000)
def guerre(a,n,z,err,nter):
    az = [complex(0,0) for i in xrange(50)]
    azz = [complex(0,0) for i in xrange(50)]
    ci=complex(0.0,1.0)
    eps=1.0e-20
#  The coefficients of p'[z] and p''[z].
    for i in range(1,n+1):
        az[i-1]=float(i)*a[i]
    for i in range(1,n):
        azz[i-1]=float(i)*az[i]
    dz=err+1
    itera=0
    jter=0
    while abs(dz)>err and itera<nter:
        p=a[n-1]+a[n]*z
        for i in range(n-1,0,-1):
            p=a[i-1]+z*p
        if abs(p)<eps:
            return z
        pz=az[n-2]+az[n-1]*z
        for i in range(n-2,0,-1):
            pz=az[i-1]+z*pz
        pzz=azz[n-3]+azz[n-2]*z
        for i in range(n-3,0,-1):
            pzz=azz[i-1]+z*pzz
#  The Laguerre perturbation.
        f=pz/p
        g=(f**2)-pzz/p
        h= n*g#cmath.sqrt((float(n)-1.0)*(n*g-(f**2)))
        amp1=abs(f+h);
        amp2=abs(f-h);
        if amp1>amp2:
            dz=float(-n)/(f+h)
        else:
            dz=float(-n)/(f-h)
        itera=itera+1
#   Rotate by 90 degrees to avoid limit cycles. 
        jter=jter+1
        if jter==10:
            jter=1
            dz=dz*ci
        z=z+dz
        if jter==100:
            raise RuntimeError("Laguerre method not converging")
    return z

########NEW FILE########
__FILENAME__ = harris
#from parakeet testbed
#runas import numpy as np ; M, N = 4, 6 ; I = np.arange(M*N, dtype=np.float64).reshape(M,N) ; harris(I)
#bench import numpy as np ; M, N = 6000, 4000 ; I = np.arange(M*N, dtype=np.float64).reshape(M,N) ; harris(I)

#pythran export harris(float64[][])
import numpy as np



def harris(I):
  m,n = I.shape
  dx = (I[1:, :] - I[:m-1, :])[:, 1:]
  dy = (I[:, 1:] - I[:, :n-1])[1:, :]

  #
  #   At each point we build a matrix
  #   of derivative products
  #   M =
  #   | A = dx^2     C = dx * dy |
  #   | C = dy * dx  B = dy * dy |
  #
  #   and the score at that point is:
  #      det(M) - k*trace(M)^2
  #
  A = dx * dx
  B = dy * dy
  C = dx * dy
  tr = A + B
  det = A * B - C * C
  k = 0.05
  return det - k * tr * tr

########NEW FILE########
__FILENAME__ = hasting
#from http://wiki.scipy.org/Cookbook/Theoretical_Ecology/Hastings_and_Powell
#pythran export fweb(float [], float, float, float, float, float, float, float)
import numpy as np
def fweb(y, t, a1, a2, b1, b2, d1, d2):
    yprime = np.empty((3,))
    yprime[0] = y[0] * (1. - y[0]) - a1*y[0]*y[1]/(1. + b1 * y[0])
    yprime[1] = a1*y[0]*y[1] / (1. + b1 * y[0]) - a2 * y[1]*y[2] / (1. + b2 * y[1]) - d1 * y[1]
    yprime[2] = a2*y[1]*y[2]/(1. + b2*y[1]) - d2*y[2]
    return yprime

########NEW FILE########
__FILENAME__ = histogram
#pythran export histogram(float list, int)
#runas histogram([ (i*1.1+j*2.3)%10 for i in xrange(100) for j in xrange(100) ],10)
#bench histogram([ (i*1.1+j*2.3)%10 for i in xrange(1000) for j in xrange(2000) ],10)
def histogram(data, bin_width):
    lower_bound, upper_bound = min(data), max(data)
    out_data=[0]*(1+bin_width)
    for i in data:
        out_data[ int(bin_width * (i - lower_bound) / ( upper_bound - lower_bound)) ]+=1
    out_data[-2]+=out_data[-1]
    out_data.pop()
    return out_data

########NEW FILE########
__FILENAME__ = hyantes_core
#pythran export run(float, float, float, float, float, float, int, int, float list list)
#bench run(0,0,90,90, 1, 100, 80, 80, [ [i/10., i/10., i/20.] for i in xrange(160) ])
#runas run(0,0,90,90, 1, 100, 80, 80, [ [i/10., i/10., i/20.] for i in xrange(80) ])
import math
def run(xmin, ymin, xmax, ymax, step, range_, range_x, range_y, t):
    pt = [ [0]*range_y for _ in range(range_x)]
    "omp parallel for"
    for i in xrange(range_x):
        for j in xrange(range_y):
            s = 0
            for k in t:
                tmp = 6368.* math.acos( math.cos(xmin+step*i)*math.cos( k[0] ) *
                                       math.cos((ymin+step*j)-k[1])+  math.sin(xmin+step*i)*math.sin(k[0]))
                if tmp < range_:
                    s+=k[2] / (1+tmp)
            pt[i][j] = s
    return pt

########NEW FILE########
__FILENAME__ = hyantes_core_numpy
#pythran export run(float, float, float, float, float, float, int, int, float[][])
#bench import numpy ; run(0,0,90,90, 1, 100, 80, 80, numpy.array([ [i/10., i/10., i/20.] for i in xrange(160)],dtype=numpy.double))
#runas import numpy ; run(0,0,90,90, 1, 100, 80, 80, numpy.array([ [i/10., i/10., i/20.] for i in xrange(80)],dtype=numpy.double))
import numpy as np
def run(xmin, ymin, xmax, ymax, step, range_, range_x, range_y, t):
    X,Y = t.shape
    pt = np.zeros((X,Y))
    "omp parallel for"
    for i in range(X):
        for j in range(Y):
            for k in t:
                tmp = 6368.* np.arccos( np.cos(xmin+step*i)*np.cos( k[0] ) * np.cos((ymin+step*j)-k[1])+  np.sin(xmin+step*i)*np.sin(k[0]))
                if tmp < range_:
                    pt[i][j]+=k[2] / (1+tmp)
    return pt

########NEW FILE########
__FILENAME__ = insertion_sort
#pythran export insertion_sort(float list)
#runas insertion_sort([1.3,5.6,-34.4,34.4,32,1.2,0,0.0,3.4,1.3])
#bench import random; in_ = random.sample(xrange(10000000), 6000) + [4.5]; insertion_sort(in_)
def insertion_sort(list2):
    for i in range(1, len(list2)):
        save = list2[i]
        j = i
        while j > 0 and list2[j - 1] > save:
            list2[j] = list2[j - 1]
            j -= 1
        list2[j] = save

########NEW FILE########
__FILENAME__ = julia_pure_python
# --- Python / Numpy imports -------------------------------------------------
import numpy as np
from time import time
#pythran export compute_julia(float, float, int, float, float, int)

def kernel(zr, zi, cr, ci, lim, cutoff):
    ''' Computes the number of iterations `n` such that 
        |z_n| > `lim`, where `z_n = z_{n-1}**2 + c`.
    '''
    count = 0
    while ((zr*zr + zi*zi) < (lim*lim)) and count < cutoff:
        zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
        count += 1
    return count

def compute_julia(cr, ci, N, bound=1.5, lim=1000., cutoff=1e6):
    ''' Pure Python calculation of the Julia set for a given `c`.  No NumPy
        array operations are used.
    '''
    julia = np.empty((N, N), np.uint32)
    grid_x = np.linspace(-bound, bound, N)
    t0 = time()
    "omp parallel for default(none) shared(grid_x, cr, ci, lim, cutoff, julia)"
    for i, x in enumerate(grid_x):
        for j, y in enumerate(grid_x):
            julia[i,j] = kernel(x, y, cr, ci, lim, cutoff)
    return julia, time() - t0

########NEW FILE########
__FILENAME__ = kmeans
#pythran export test()
#norunas test() because of random input
#bench test()
import  math, random

# a point is a tuple
# a cluster is a list of tuple and a point (the centroid)

def calculateCentroid(cluster):
    reduce_coord = lambda i: reduce(lambda x,p : x + p[i], cluster,0.0)
    centroid_coords = [reduce_coord(i)/len(cluster) for i in range(len(cluster[0]))]
    return centroid_coords

def kmeans(points, k, cutoff):
    initial = random.sample(points, k)
    clusters = [[p] for p in initial]
    centroids = [ calculateCentroid(c) for c in clusters ]
    while True:
        lists = [ [] for c in clusters]
        for p in points:
            smallest_distance = getDistance(p,centroids[0])
            index = 0
            for i in range(len(clusters[1:])):
                distance = getDistance(p, centroids[i+1])
                if distance < smallest_distance:
                    smallest_distance = distance
                    index = i+1
            lists[index].append(p)
        biggest_shift = 0.0
        for i in range(len(clusters)):
            if lists[i]:
                new_cluster, new_centroid = (lists[i], calculateCentroid(lists[i]))
                shift = getDistance(centroids[i], new_centroid)
                clusters[i] = new_cluster
                centroids[i] = new_centroid
                biggest_shift = max(biggest_shift, shift)
        if biggest_shift < cutoff:
            break
    return clusters

def getDistance(a, b):
    ret = reduce(lambda x,y: x + pow((a[y]-b[y]), 2),range(len(a)),0.0)
    return math.sqrt(ret)

def makeRandomPoint(n, lower, upper):
    return [random.uniform(lower, upper) for i in range(n)]

def test():
    num_points, dim, k, cutoff, lower, upper = 500, 10, 50, 0.001, 0, 2000
    points = [ makeRandomPoint(dim, lower, upper) for i in range(num_points) ]
    clusters = kmeans(points, k, cutoff)
    #for c in clusters:
    #    print c
    return clusters

########NEW FILE########
__FILENAME__ = l2norm
#from http://stackoverflow.com/questions/7741878/how-to-apply-numpy-linalg-norm-to-each-row-of-a-matrix/7741976#7741976
#pythran export l2_norm(float64[][])
#runas import numpy as np ; N = 100 ; x = np.arange(N*N, dtype=np.float64).reshape((N,N)) ; l2_norm(x)
#bench import numpy as np ; N = 10000 ; x = np.arange(N*N, dtype=np.float64).reshape((N,N)) ; l2_norm(x)
import numpy as np
def l2_norm(x):
    return np.sqrt(np.sum(np.abs(x)**2, 1))

########NEW FILE########
__FILENAME__ = laplace
#runas calc(60,100)
#bench calc(120,200)
#pythran export calc(int, int)
def update(u):
    dx = 0.1
    dy = 0.1
    dx2 = dx*dx
    dy2 = dy*dy
    nx, ny = len(u), len(u[0])
    for i in xrange(1,nx-1):
        for j in xrange(1, ny-1):
            u[i][j] = ((u[i+1][ j] + u[i-1][ j]) * dy2 +
                    (u[i][ j+1] + u[i][ j-1]) * dx2) / (2*(dx2+dy2))

def calc(N, Niter=100):
    u = [ [0]*N for _ in xrange(N)]
    u[0] = [1] * N
    for i in range(Niter):
        update(u)
    return u

########NEW FILE########
__FILENAME__ = loopy_jacob
#pythran export loopy(int list list, int, int, int)
#runas data = [[1, 45, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 60, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0]] ; loopy(data, 0, 100, 100)
#skip.bench data = [[1, 45, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0]] + [[0, 60, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0]] * 200 ; loopy(data, 0, 100, 100) TOO_SLOW
def _WarningErrorHandler(msg,fatal, _WarningCount):
    if _WarningCount > 200:
        raise RuntimeError(msg)
    else:
        return _WarningCount +1

def loopy(_PopulationSetInfo_Data, _WarningCount, _NumberOfTriesToGenerateThisIndividual, _NumberOfTriesToGenerateThisSimulationStep):
    #### Functions Allowed in Expressions ####
    IndividualID = 0
    Repetition = 0
    Time = 0
    _ResultsInfo_Data = []
    #### Create State Handler Functions and State Classification Vector ##### 
    ############### Execute Simulation ###############
    ####### Subject Loop #######
    _Subject = 0
    while _Subject < (len(_PopulationSetInfo_Data)):
        IndividualID = IndividualID +1
        # Comment/Uncomment the next line to disable/enable printing of verbose information
        #print "Simulating Individual #" + str(IndividualID)
        _NumberOfTriesToGenerateThisIndividual = 1
        ##### Repetition Loop #####
        Repetition = 0
        while Repetition < (1000):
            # Reset repeat individual repetition flag in case it was set
            _RepeatSameIndividualRepetition = False
            #Init all parameters - Resetting them to zero
            # Comment/Uncomment the next line to disable/enable printing of verbose information
            #print "  Repetition = " + str(Repetition)
            Gender, Age, State0, State1, State2, State3Terminal, Example_6___Main_Process, Example_6___Main_Process_Entered, State0_Entered, State1_Entered, State2_Entered, State3Terminal_Entered = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            # Init parameters from population set
            [Gender, Age, State0, State1, State2, State3Terminal, Example_6___Main_Process, Example_6___Main_Process_Entered, State0_Entered, State1_Entered, State2_Entered, State3Terminal_Entered] = _PopulationSetInfo_Data[IndividualID-1]
            # Init parameters from Initialization Phase
            # Reset time and load first vector into results
            Time = 0
            # Load the initial condition into the results vector for this individual
            _ResultsInfoForThisIndividual = [ [IndividualID, Repetition, Time ,Gender, Age, State0, State1, State2, State3Terminal, Example_6___Main_Process, Example_6___Main_Process_Entered, State0_Entered, State1_Entered, State2_Entered, State3Terminal_Entered] ]
            _Terminate_Time_Loop = False or State3Terminal != 0
            _NumberOfTriesToGenerateThisSimulationStep = 0
            _RepeatSameSimulationStep = False
            ##### Time Loop #####
            while Time < 3:
                if _RepeatSameSimulationStep:
                    # if repeating the same simulation step, reset the flag to avoid infinite loops
                    _RepeatSameSimulationStep = False
                    # Load the previous time step results into the results vector for this individual
                    [_IgnoreIndividualID, _IgnoreRepetition, _IgnoreTime ,Gender, Age, State0, State1, State2, State3Terminal, Example_6___Main_Process, Example_6___Main_Process_Entered, State0_Entered, State1_Entered, State2_Entered, State3Terminal_Entered] = _ResultsInfoForThisIndividual[-1]
                    _Terminate_Time_Loop = False
                elif _Terminate_Time_Loop:
                    # If the time loop has to be terminated
                    break
                else:
                    # If not repeating the same simulation step, nor terminating, increase the time counter
                    Time = Time + 1
                # Comment/Uncomment the next line to disable/enable printing of verbose information
                #print "    Time Step = " + str(Time)
                # Reset Warning/Error Count
                _WarningCountBeforeThisSimulationStep = _WarningCount
                # Increase the number of Tries counter
                _NumberOfTriesToGenerateThisSimulationStep = _NumberOfTriesToGenerateThisSimulationStep + 1
                ##### Phase 1 - Pre State Transition #####
                # Processing the rule: "Affected Parameter: Age; Simulation Phase: Pre-stateOccurrence Probability: 1; Applied Formula: Age +1; Rule Notes: Age Increase; ; 
                _LastExpressionString = "Processing the expression: _Threshold = 1 ."
                # This expression should expand to: _Threshold = 1
                try:
                    # Building Step #0: _Threshold = 1
                    _Temp = 1
                    if not (-1e-14 <= _Temp  <= 1.00000000000001):
                        _WarningCount = _WarningErrorHandler("The occurrence probability threshold defined by a rule does not evaluate to a number between 0 and 1 within a tolerance specified by the system option parameter SystemPrecisionForProbabilityBoundCheck. The occurrence probability was evaluated to: " + str(_Temp) + " for the rule: " + 'Affected Parameter: Age; Simulation Phase: Pre-stateOccurrence Probability: 1; Applied Formula: Age +1; Rule Notes: Age Increase; ; ', True, _WarningCount) 
                except:
                    _WarningCount = _WarningErrorHandler(_LastExpressionString, True, _WarningCount)
                # Expression building complete - assign to destination parameter 
                _Threshold = _Temp
                if  0.5 < _Threshold:
                    _LastExpressionString = "Processing the expression: Age = Age +1 ."
                    # This expression should expand to: Age = Age +1
                    try:
                        # Building Step #0: Age = Age
                        _Temp0 = Age
                        # Building Step #1: Age = Age +1
                        _Temp = _Temp0 +1
                    except:
                        _WarningCount = _WarningErrorHandler(_LastExpressionString, True, _WarningCount)
                    # Expression building complete - assign to destination parameter 
                    Age = _Temp
                    pass
                ##### End of Rule Processing #####
                ##### Error Handlers #####
                if _WarningCount <= _WarningCountBeforeThisSimulationStep:
                    # Load New results to the results vector
                    _ResultsInfoForThisIndividual.append([IndividualID, Repetition, Time ,Gender, Age, State0, State1, State2, State3Terminal, Example_6___Main_Process, Example_6___Main_Process_Entered, State0_Entered, State1_Entered, State2_Entered, State3Terminal_Entered])
                    _NumberOfTriesToGenerateThisSimulationStep = 0
                else:
                    #print "    Repeating the same simulation step due to an error - probably a bad validity check"
                    _RepeatSameSimulationStep = True
                    if _NumberOfTriesToGenerateThisSimulationStep >= 5:
                        if _NumberOfTriesToGenerateThisIndividual < 2:
                            # Repeat the calculations for this person
                            _RepeatSameIndividualRepetition = True 
                            break
                        else:
                            _WarningCount = _WarningErrorHandler("The simulation was halted since the number of tries to recalculate the same person has been exceeded. If this problem consistently repeats itself, check the formulas to see if these cause too many out of bounds numbers to be generated. Alternatively, try raising the system option NumberOfTriesToRecalculateSimulationOfIndividualFromStart which is now defined as 2  .  ", True, _WarningCount)
            if _RepeatSameIndividualRepetition:
                #print "  Repeating the same repetition for the same individual due to exceeding the allowed number of simulation steps recalculations for this individual"
                _NumberOfTriesToGenerateThisIndividual = _NumberOfTriesToGenerateThisIndividual + 1
            else:
                # If going to the next individual repetition, save the results and increase the counter
                # Load New results to the results vector
                _ResultsInfo_Data.extend(_ResultsInfoForThisIndividual)
                Repetition = Repetition + 1
        _Subject = _Subject + 1
    # Comment/Uncomment the next lines to disable/enable dumping output file
    return _ResultsInfo_Data


########NEW FILE########
__FILENAME__ = mandel
#runas mandel(20,0,0, 8)
#bench mandel(400,0,0, 75)
#pythran export mandel(int, float, float, int)
def mandel(size, x_center, y_center, max_iteration):
    out= [ [ 0 for i in xrange(size) ] for j in xrange(size) ]
    for i in xrange(size):
        "omp parallel for"
        for j in xrange(size):
            x,y = ( x_center + 4.0*float(i-size/2)/size,
                      y_center + 4.0*float(j-size/2)/size
                    )

            a,b = (0.0, 0.0)
            iteration = 0

            while (a**2 + b**2 <= 4.0 and iteration < max_iteration):
                a,b = a**2 - b**2 + x, 2*a*b + y
                iteration += 1
            if iteration == max_iteration:
                color_value = 255
            else:
                color_value = iteration*10 % 255
            out[i][j]=color_value
    return out

########NEW FILE########
__FILENAME__ = matmul
#runas a=[ [ float(i) for i in xrange(60)] for j in xrange(60)] ; matrix_multiply(a,a)
#skip.bench a=[ [ float(i) for i in xrange(600)] for j in xrange(400)] ; matrix_multiply(a,a) SEGFAULT
#pythran export matrix_multiply(float list list, float list list)
def zero(n,m): return [[0 for row in xrange(n)] for col in xrange(m)]
def matrix_multiply(m0, m1):
    new_matrix = zero(len(m0),len(m1[0]))
    for i in xrange(len(m0)):
        for j in xrange(len(m1[0])):
            r=0
            "omp parallel for reduction(+:r)"
            for k in xrange(len(m1)):
                r += m0[i][k]*m1[k][j]
            new_matrix[i][j]=r
    return new_matrix

########NEW FILE########
__FILENAME__ = monte_carlo
# http://code.activestate.com/recipes/577263-numerical-integration-using-monte-carlo-method/
# Numerical Integration using Monte Carlo method
# FB - 201006137
#pythran export montecarlo_integration(float, float, int, float list, int)
#runas montecarlo_integration(1.,10.,100,[x/100. for x in range(100)],100)
#bench montecarlo_integration(1.,10.,650000,[x/100. for x in range(100)],100)
import math


def montecarlo_integration(xmin, xmax, numSteps,rand,randsize):
    # define any function here!
    def f(x):
        return math.sin(x)

    # find ymin-ymax
    ymin = f(xmin)
    ymax = ymin
    for i in xrange(numSteps):
        x = xmin + (xmax - xmin) * float(i) / numSteps
        y = f(x)
        if y < ymin: ymin = y
        if y > ymax: ymax = y

    # Monte Carlo
    rectArea = (xmax - xmin) * (ymax - ymin)
    numPoints = numSteps # bigger the better but slower!
    ctr = 0
    for j in xrange(numPoints):
        x = xmin + (xmax - xmin) * rand[j%randsize]
        y = ymin + (ymax - ymin) * rand[j%randsize]
        if math.fabs(y) <= math.fabs(f(x)):
            if f(x) > 0 and y > 0 and y <= f(x):
                ctr += 1 # area over x-axis is positive
            if f(x) < 0 and y < 0 and y >= f(x):
                ctr -= 1 # area under x-axis is negative

    fnArea = rectArea * float(ctr) / numPoints
    return fnArea

########NEW FILE########
__FILENAME__ = monte_carlo_pricer
#unittest.skip np.random not supported yet
import numpy as np
def step(dt, prices, c0, c1, noises):
    return prices * np.exp(c0 * dt + c1 * noises)

def monte_carlo_pricer(paths, dt, interest, volatility):
    c0 = interest - 0.5 * volatility ** 2
    c1 = volatility * np.sqrt(dt)

    for j in xrange(1, paths.shape[1]): # for all trials
        prices = paths[:, j - 1]
        # generate normally distributed random number
        noises = np.random.normal(0., 1., prices.size)
        # calculate the next batch of prices for all trials
        paths[:, j] = step(dt, prices, c0, c1, noises)

########NEW FILE########
__FILENAME__ = morphology
#skip.pythran export dilate_decompose(int[][], int)
#pythran export dilate_decompose_loops(float[][], int)
#skip.pythran export dilate_decompose_interior(int[][], int[][])
#skip.runas import numpy as np ; image = np.random.randint(0, 256,  (width, height)) / 256.0 ; dilate_decompose_loops(image)
#runas import numpy as np ; image = np.tri(100, 200) /2.0 ; dilate_decompose_loops(image, 4)
#bench import numpy as np ; image = np.tri(500, 600) /2.0 ; dilate_decompose_loops(image, 4)

from numpy import empty_like

def dilate_decompose_loops(x, k):
  m,n = x.shape
  y = empty_like(x)
  for i in xrange(m):
    for j in xrange(n):
      left_idx = max(0, i-k/2)
      right_idx = min(m, i+k/2+1)
      currmax = x[left_idx, j]
      for ii in xrange(left_idx+1, right_idx):
        elt = x[ii, j]
        if elt > currmax:
          currmax = elt
      y[i, j] = currmax
  z = empty_like(x)
  for i in xrange(m):
    for j in xrange(n):
      left_idx = max(0, j-k/2)
      right_idx = min(n, j+k/2+1)
      currmax = y[i,left_idx]
      for jj in xrange(left_idx+1, right_idx):
        elt = y[i,jj]
        if elt > currmax:
          currmax = elt
      z[i,j] = currmax
  return z

#def dilate_1d_naive(x_strip,  k):
#  """
#  Given a 1-dimensional input and 1-dimensional output, 
#  fill output with 1d dilation of input 
#  """
#  nelts = len(x_strip)
#  y_strip = empty_like(x_strip)
#  half = k / 2 
#  for idx in xrange(nelts):
#    left_idx = max(idx-half,0)
#    right_idx = min(idx+half+1, nelts)
#    currmax = x_strip[left_idx]
#    for j in xrange(left_idx+1, right_idx):
#      elt = x_strip[j]
#      if elt > currmax:
#        currmax = elt
#    y_strip[idx] = currmax 
#  return y_strip
#
#def dilate_decompose(x, k): 
#  import numpy as np
#  m,n = x.shape
#  y = np.array([dilate_1d_naive(x[row_idx, :], k) for row_idx in xrange(m)])
#  return np.array([dilate_1d_naive(y[:, col_idx], k) for col_idx in xrange(n)]).T
#
#def dilate_1d_interior(x_strip, k):
#  
#  nelts = len(x_strip)
#  y_strip = empty_like(x_strip)
#  half = k / 2 
#  
#  interior_start = half+1
#  interior_stop = max(nelts-half, interior_start)
#  
#  # left boundary
#  for i in xrange(min(half+1, nelts)):
#    left_idx = max(i-half,0)
#    right_idx = min(i+half+1, nelts)
#    currmax = x_strip[left_idx]
#    for j in xrange(left_idx+1, right_idx):
#      elt = x_strip[j]
#      if elt > currmax:
#        currmax = elt
#    y_strip[i] = currmax 
#    
#  #interior 
#  for i in xrange(interior_start, interior_stop):
#    left_idx = i-half
#    right_idx = i+half+1
#    currmax = x_strip[left_idx]
#    for j in xrange(left_idx+1, right_idx):
#      elt = x_strip[j]
#      if elt > currmax:
#        currmax = elt
#    y_strip[i] = currmax 
#  
#  # right boundary
#  for i in xrange(interior_stop, nelts):
#    left_idx = max(i-half, 0)
#    right_idx = nelts
#    currmax = x_strip[left_idx]
#    for j in xrange(left_idx+1, right_idx):
#      elt = x_strip[j]
#      if elt > currmax:
#        currmax = elt
#    y_strip[i] = currmax 
#  return y_strip 
#
#def dilate_decompose_interior(x, k): 
#  m,n = x.shape
#  y = np.array([dilate_1d_interior(x[row_idx, :],k) for row_idx in xrange(m)])
#  return np.array([dilate_1d_interior(y[:, col_idx],k) for col_idx in xrange(n)]).T

########NEW FILE########
__FILENAME__ = mulmod
#from http://stackoverflow.com/questions/19350395/python-jit-for-known-bottlenecks
#pythran export gf2mulmod(long, long, long)
#runas x, y, m = 2**1024 , 2**65-1, 2**67-1; gf2mulmod(x, y, m)
#bench x, y, m = 2**(7 * 2**15) , 2**1775-1, 2**1777-1; gf2mulmod(x, y, m)

def gf2mulmod(x,y,m):
    z = 0
    while x > 0:
        if (x & 1) != 0:
            z ^= y
        y <<= 1
        y2 = y ^ m
        if y2 < y:
            y = y2
        x >>= 1
    return z

########NEW FILE########
__FILENAME__ = multi_export
#pythran export a(int)
#pythran export a(float)
#pythran export a(str)
#runas a(2.4)
#runas a(2)
#runas a("hello world")
def a(i): return i

########NEW FILE########
__FILENAME__ = nd_local_maxima
#from https://github.com/iskandr/parakeet/blob/master/benchmarks/nd_local_maxima.py
#pythran export local_maxima(float [][][][])
#runas import numpy as np ; shape = (8,6,4,2) ; x = np.arange(8*6*4*2, dtype=np.float64).reshape(*shape) ; local_maxima(x)
import numpy as np

def wrap(pos, offset, bound):
    return ( pos + offset ) % bound

def clamp(pos, offset, bound):
    return min(bound-1,max(0,pos+offset))

def reflect(pos, offset, bound):
    idx = pos+offset
    return min(2*(bound-1)-idx,max(idx,-idx))


def local_maxima(data, mode=wrap):
  wsize = data.shape
  result = np.ones(data.shape, bool)
  for pos in np.ndindex(data.shape):
    myval = data[pos]
    for offset in np.ndindex(wsize):
      neighbor_idx = tuple(mode(p, o-w/2, w) for (p, o, w) in zip(pos, offset, wsize))
      result[pos] &= (data[neighbor_idx] <= myval)
  return result

########NEW FILE########
__FILENAME__ = nqueens
#bench n_queens(9)
#runas n_queens(6)
#pythran export n_queens(int)

# Pure-Python implementation of itertools.permutations().
def permutations(iterable, r=None):
    """permutations(range(3), 2) --> (0,1) (0,2) (1,0) (1,2) (2,0) (2,1)"""
    pool = tuple(iterable)
    n = len(pool)
    if r is None:
        r = n
    indices = range(n)
    cycles = range(n-r+1, n+1)[::-1]
    yield tuple(pool[i] for i in indices[:r])
    while n:
        for i in reversed(xrange(r)):
            cycles[i] -= 1
            if cycles[i] == 0:
                indices[i:] = indices[i+1:] + indices[i:i+1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                yield tuple(pool[i] for i in indices[:r])
                break
        else:
            return


# From http://code.activestate.com/recipes/576647/
def n_queens(queen_count):
    """N-Queens solver.

    Args:
        queen_count: the number of queens to solve for. This is also the
            board size.

    Yields:
        Solutions to the problem. Each yielded value is looks like
        (3, 8, 2, 1, 4, ..., 6) where each number is the column position for the
        queen, and the index into the tuple indicates the row.
    """
    out =list()
    cols = range(queen_count)
    #for vec in permutations(cols):
    for vec in permutations(cols,None):
        if (queen_count == len(set(vec[i]+i for i in cols))
                        == len(set(vec[i]-i for i in cols))):
            #yield vec
            out.append(vec)
    return out

########NEW FILE########
__FILENAME__ = pairwise
#from http://jakevdp.github.com/blog/2012/08/24/numba-vs-cython/
#runas X = [ [i/100.+j for i in xrange(100) ] for j in xrange(30) ] ; pairwise(X)
#bench X = [ [i/100.+j for i in xrange(800) ] for j in xrange(100) ] ; pairwise(X)
#pythran export pairwise(float list list)

import math
def pairwise(X):
    M = len(X)
    N = len(X[0])
    D = [ [0 for x in xrange(M) ] for y in xrange(M) ]
    "omp parallel for"
    for i in xrange(M):
        for j in xrange(M):
            d = 0.0
            for k in xrange(N):
                tmp = X[i][k] - X[j][k]
                d += tmp * tmp
            D[i][j] = math.sqrt(d)
    return D

########NEW FILE########
__FILENAME__ = pairwise_numpy
#from http://jakevdp.github.com/blog/2012/08/24/numba-vs-cython/
#runas import numpy as np ; X = np.linspace(0,10,20000).reshape(200,100) ; pairwise(X)
#bench import numpy as np ; X = np.linspace(0,10,10000).reshape(100,100) ; pairwise(X)
#pythran export pairwise(float [][])

import numpy as np
def pairwise(X):
    M, N = X.shape
    D = np.empty((M,M))
    for i in range(M):
        for j in range(M):
            d = 0.0
            for k in xrange(N):
                tmp = X[i,k] - X[j,k]
                d += tmp * tmp
            D[i,j] = np.sqrt(d)
    return D

########NEW FILE########
__FILENAME__ = periodic_dist
#pythran export dist(float [], float[], float[], int, bool, bool, bool)
#runas import numpy as np ; N = 20 ; x = np.arange(0., N, 0.1) ; L = 4 ; periodic = True ; dist(x, x, x, L,periodic, periodic, periodic)
#bench import numpy as np ; N = 300 ; x = np.arange(0., N, 0.1) ; L = 4 ; periodic = True ; dist(x, x, x, L,periodic, periodic, periodic)
import numpy as np

def dist(x, y, z, L, periodicX, periodicY, periodicZ):
    " ""Computes distances between all particles and places the result in a matrix such that the ij th matrix entry corresponds to the distance between particle i and j"" "
    N = len(x)
    xtemp = np.tile(x,(N,1))
    dx = xtemp - xtemp.T
    ytemp = np.tile(y,(N,1))
    dy = ytemp - ytemp.T
    ztemp = np.tile(z,(N,1))
    dz = ztemp - ztemp.T

    # Particles 'feel' each other across the periodic boundaries
    if periodicX:
        dx[dx>L/2]=dx[dx > L/2]-L
        dx[dx<-L/2]=dx[dx < -L/2]+L

    if periodicY:
        dy[dy>L/2]=dy[dy>L/2]-L
        dy[dy<-L/2]=dy[dy<-L/2]+L

    if periodicZ:
        dz[dz>L/2]=dz[dz>L/2]-L
        dz[dz<-L/2]=dz[dz<-L/2]+L

    # Total Distances
    d = np.sqrt(dx**2+dy**2+dz**2)

    # Mark zero entries with negative 1 to avoid divergences
    d[d==0] = -1

    return d, dx, dy, dz

########NEW FILE########
__FILENAME__ = perm
#pythran export permutations(int list)
#runas permutations([1,4,5,6,12])
#bench in_ = range(9); permutations(in_)
def permutations(iterable):
    """permutations(range(3), 2) --> (0,1) (0,2) (1,0) (1,2) (2,0) (2,1)"""
    out=[]
    pool = tuple(iterable)
    n = len(pool)
    r = n
    indices = range(n)
    cycles = range(n-r+1, n+1)[::-1]
    out.append( tuple([pool[i] for i in indices[:r]]))
    while 1:
        for i in reversed(xrange(r)):
            cycles[i] -= 1
            if cycles[i] == 0:
                indices[i:] = indices[i+1:] + indices[i:i+1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                out.append( tuple([pool[i] for i in indices[:r]]))
                break
        else:
            return out

########NEW FILE########
__FILENAME__ = pivot
#pythran export pivot(int, int, int list list, int list)
#pythran export pivot(int, int, float list list, float list)
#pythran export pivot(int, int, complex list list, complex list)
#runas pivot(5,1,[[1,2,4,-6,1],[12,3,8,1,6],[-3,7,13,-6,1],[7,4,-3,1,78],[4,1,8,5,3]],[43,-2,7,1,67])
#runas pivot(5,1,[[1.4,2.2,4.3,-6.4,1.6],[12.2,3.4,8.4,1.1,6.2],[-3.6,7.8,13.2,-6.1,1.5],[7.2,4.4,-3.5,1.6,78.4],[4.4,1.4,8.2,5.6,3.]],[43.3,-2.3,7.2,1.5,67.6])
#runas pivot(2,1,[[complex(1.3,-3),complex(3,4)],[complex(10.2,2.3),complex(-3,4)]],[complex(1.2,12.3),complex(-4.3,2.4)])
def pivot(n,i,a,b):
    i0=i
    amp0=abs(a[i-1][i-1])
    for j in range(i+1,n+1):
        amp=abs(a[i-1][j-1])
        if amp>amp0:
            i0=j
            amp0=amp
    if i==i0:
        return
    temp=b[i-1]
    b[i-1]=b[i0-1];
    b[i0-1]=temp;
    for j in range(i,n+1):
        temp=a[j-1][i-1]
        a[j-1][i-1]=a[j-1][i0-1]
        a[j-1][i0-1]=temp
    return a,b


########NEW FILE########
__FILENAME__ = pi_buffon
#pythran export pi_estimate(int,float list, int)
#runas pi_estimate(4000,[x/100. for x in range(100)],100)
#bench pi_estimate(2200000,[x/1000. for x in range(1000)],1000)
from math import sqrt, pow
from random import random

def pi_estimate(DARTS,rand,randsize):
    hits = 0
    "omp parallel for reduction(+:hits)"
    for i in xrange (0, DARTS):
        x = rand[i%randsize]
        y = rand[(randsize-i)%randsize]
        dist = sqrt(pow(x, 2) + pow(y, 2))
        if dist <= 1.0:
            hits += 1.0
    # hits / throws = 1/4 Pi
    pi = 4 * (hits / DARTS)
    return pi


########NEW FILE########
__FILENAME__ = primes_sieve
# from http://stackoverflow.com/questions/3939660/sieve-of-eratosthenes-finding-primes-python
# using a list instead of generator as return values

#pythran export primes_sieve(int)
#runas primes_sieve(100)
#bench primes_sieve(6000000)
def primes_sieve(limit):
    a = [True] * limit                          # Initialize the primality list
    a[0] = a[1] = False
    primes=list()

    for (i, isprime) in enumerate(a):
        if isprime:
            primes.append(i)
            for n in xrange(i*i, limit, i):     # Mark factors non-prime
                a[n] = False

    return primes

########NEW FILE########
__FILENAME__ = primes_sieve2
#pythran export get_primes7(int)
#from http://blog.famzah.net/2010/07/01/cpp-vs-python-vs-perl-vs-php-performance-benchmark/
#runas get_primes7(100)
#bench get_primes7(7000000)
def get_primes7(n):
	"""
	standard optimized sieve algorithm to get a list of prime numbers
	--- this is the function to compare your functions against! ---
	"""
	if n < 2:  return []
	if n == 2: return [2]
	# do only odd numbers starting at 3
	s = range(3, n+1, 2)
	# n**0.5 simpler than math.sqr(n)
	mroot = n ** 0.5
	half = len(s)
	i = 0
	m = 3
	while m <= mroot:
		if s[i]:
			j = (m*m-3)//2  # int div
			s[j] = 0
			while j < half:
				s[j] = 0
				j += m
		i = i+1
		m = 2*i+3
	return [2]+[x for x in s if x]

########NEW FILE########
__FILENAME__ = pselect
#pythran export pselect(int)
#runas pselect(0)
#runas pselect(1)
def pselect(n):
    if n:
        a=sel0
    else:
        a=sel1
    l=list()
    a(l)
    return l

def sel0(n):
    n.append(1)
def sel1(n):
    n.append(2.)

########NEW FILE########
__FILENAME__ = queens_numba
#pythran export solve(int)
#unittest.skip requires extensive typing, use enable_two_steps_typing from the cfg file 
def hits(x1, y1, x2, y2):
    "Check whether a queen positioned at (x1, y1) will hit a queen at position (x2, y2)"
    return x1 == x2 or y1 == y2 or abs(x1 - x2) == abs(y1 - y2)

def hitsany(x, y, queens_x, queens_y):
    "Check whether a queen positioned at (x1, y1) will hit any other queen"
    for i in range(len(queens_x)):
        if hits(x, y, queens_x[i], queens_y[i]):
            return True

    return False

def _solve(n, queens_x, queens_y):
    "Solve the queens puzzle"
    if n == 0:
        return True

    for x in range(1, 9):
        for y in range(1, 9):
            if not hitsany(x, y, queens_x, queens_y):
                queens_x.append(x)
                queens_y.append(y)

                if _solve(n - 1, queens_x, queens_y):
                    return True

                queens_x.pop()
                queens_y.pop()

    return False

def solve(n):
    queens_x = []
    queens_y = []

    if _solve(n, queens_x, queens_y):
        return queens_x, queens_y
    else:
        return None


#print(solve(8))
# %timeit solve(8)

# Comment out @jit/@autojit
# print(solve(8))
# %timeit solve(8)


########NEW FILE########
__FILENAME__ = quicksort
#pythran export quicksort(int list, int, int)
#runas quicksort(range(10),0,9)
def partition(list, start, end):
    pivot = list[end]                          # Partition around the last value
    bottom = start-1                           # Start outside the area to be partitioned
    top = end                                  # Ditto

    done = 0
    while not done:                            # Until all elements are partitioned...

        while not done:                        # Until we find an out of place element...
            bottom = bottom+1                  # ... move the bottom up.

            if bottom == top:                  # If we hit the top...
                done = 1                       # ... we are done.
                break

            if list[bottom] > pivot:           # Is the bottom out of place?
                list[top] = list[bottom]       # Then put it at the top...
                break                          # ... and start searching from the top.

        while not done:                        # Until we find an out of place element...
            top = top-1                        # ... move the top down.
            if top == bottom:                  # If we hit the bottom...
                done = 1                       # ... we are done.
                break

            if list[top] < pivot:              # Is the top out of place?
                list[bottom] = list[top]       # Then put it at the bottom...
                break                          # ...and start searching from the bottom.

    list[top] = pivot                          # Put the pivot in its place.
    return top                                 # Return the split point


def do_quicksort(list, start, end):
    if start < end:                            # If there are two or more elements...
        split = partition(list, start, end)    # ... partition the sublist...
        do_quicksort(list, start, split-1)        # ... and sort both halves.
        do_quicksort(list, split+1, end)

def quicksort(l,s,e):
    do_quicksort(l,s,e)

########NEW FILE########
__FILENAME__ = ramsurf
#pythran export deriv(int, float, float, complex list, complex list, complex list, float list list, float)

import cmath

#This subroutine finds a root of a polynomial of degree n > 2
#        by Laguerre's method.
def guerre(a,n,z,err,nter):
    az = [complex(0,0) for i in xrange(50)]
    azz = [complex(0,0) for i in xrange(50)]
    ci=complex(0.0,1.0)
    eps=1.0e-20
#  The coefficients of p'[z] and p''[z].
    for i in range(1,n+1):
        az[i-1]=float(i)*a[i]
    for i in range(1,n):
        azz[i-1]=float(i)*az[i]
    dz=err+1
    itera=0
    jter=0
    while abs(dz)>err and itera<nter:
        p=a[n-1]+a[n]*z
        for i in range(n-1,0,-1):
            p=a[i-1]+z*p
        if abs(p)<eps:
            return z
        pz=az[n-2]+az[n-1]*z
        for i in range(n-2,0,-1):
            pz=az[i-1]+z*pz
        pzz=azz[n-3]+azz[n-2]*z
        for i in range(n-3,0,-1):
            pzz=azz[i-1]+z*pzz
#  The Laguerre perturbation.
        f=pz/p
        g=(f**2)-pzz/p
        h= n*g#cmath.sqrt((float(n)-1.0)*(n*g-(f**2)))
        amp1=abs(f+h);
        amp2=abs(f-h);
        if amp1>amp2:
            dz=float(-n)/(f+h)
        else:
            dz=float(-n)/(f-h)
        itera=itera+1
#   Rotate by 90 degrees to avoid limit cycles. 
        jter=jter+1
        if jter==10:
            jter=1
            dz=dz*ci
        z=z+dz
        if jter==100:
            raise RuntimeError("Laguerre method not converging")
    return z

#   The root-finding subroutine. 
def fndrt(a,n):
    z=[complex(0,0) for k in xrange(n) ]
    if n==1:
        z[0]=-a[0]/a[1]
        return None
    if n>2:
        for k in range(n,2,-1):
#   Obtain an approximate root.
            root=complex(0.0,0)
            err=1.0e-12
            root = guerre(a,k,root,err,1000)
#   Refine the root by iterating five more times.
            err=0.0;
            root = guerre(a,k,root,err,5)
            z[k-1]=root
#   Divide out the factor [z-root].
            for i in range(k,0,-1):
                a[i-1]=a[i-1]+root*a[i]
            for i in range(1,k+1):
                a[i-1]=a[i];
#   Solve the quadratic equation.
    z[1]=0.5*(-a[1]+cmath.sqrt(a[1]*a[1]-4.0*a[0]*a[2]))/a[2]
    z[0]=0.5*(-a[1]-cmath.sqrt(a[1]*a[1]-4.0*a[0]*a[2]))/a[2]
    return z

#   Rows are interchanged for stability.
def pivot(n,i,a,b):
    i0=i
    amp0=abs(a[i-1][i-1])
    for j in range(i+1,n+1):
        amp=abs(a[i-1][j-1])
        if amp>amp0:
            i0=j
            amp0=amp
    if i==i0:
        return
    temp=b[i-1]
    b[i-1]=b[i0-1];
    b[i0-1]=temp;
    for j in range(i,n+1):
        temp=a[j-1][i-1]
        a[j-1][i-1]=a[j-1][i0-1]
        a[j-1][i0-1]=temp

def gauss(n,a,b):
#     Downward elimination.
    for i in range(1,n+1):
        if i<n:
            pivot(n,i,a,b)
        a[i-1][i-1]=1.0/a[i-1][i-1]
        b[i-1]=b[i-1]*a[i-1][i-1]
        if i<n:
            for j in range(i+1,n+1):
                a[j-1][i-1]=a[j-1][i-1]*a[i-1][i-1]
            for k in range(i+1,n+1):
                b[k-1]=b[k-1]-a[i-1][k-1]*b[i-1]
                for j in range(i+1,n+1):
                    a[j-1][k-1]=a[j-1][k-1]-a[i-1][k-1]*a[j-1][i-1]
#     Back substitution.
    for i in range(n-1,0,-1):
        for j in range(i,n):
            b[i-1]=b[i-1]-a[j][i-1]*b[j]

#     The derivatives of the operator function at x=0.
def deriv(n,sig,alp,dg,dh1,dh3,bin,nu):
    dh2=[complex(0,0) for n in dh1]
    ci = complex(0.0,1.0)
    dh1[0]=complex(0.5,0)*ci*complex(sig,0)
    exp1 = complex(-0.5,0)
    dh2[0]=alp;
    exp2 = complex(-1.0,0)
    dh3[0]=-2.0*nu
    exp3 = complex(-1.0,0)
    for i in range(1,n):
        dh1[i]=dh1[i-1]*exp1
        exp1=exp1-1.0
        dh2[i]=dh2[i-1]*exp2
        exp2=exp2-1.0
        dh3[i]=-nu*dh3[i-1]*exp3
        exp3=exp3-1.0
    dg[0]=1.0
    dg[1]=dh1[0]+dh2[0]+dh3[0]
    for i in range(2,n+1):
        dg[i]=dh1[i-1]+dh2[i-1]+dh3[i-1]
        for j in range(1,i):
            dg[i]=dg[i]+bin[j-1][i-1]*(dh1[j-1]+dh2[j-1]+dh3[j-1])*dg[i-j]

#     The coefficients of the rational approximation.
def epade(np,ns,ip,k0,dr,pd1,pd2):
    m=40
    dg = range(m)
    dh1 = range(m)
    dh3 = range(m)
    a = [[ 0 for i in range(m)] for j in range(m)]
    b = range(m);
    bin = [[ 0 for i in range(m)] for j in range(m)]
    fact = range(m)
    ci=complex(0.0,1.0)
    sig=k0*dr
    n=2*np
    if ip==1:
        nu=0.0
        alp=0.0
    else:
        nu=1.0
        alp=-0.25
#     The factorials
    fact[0]=1.0
    for i in range(1,n):
        fact[i]=(i+1)*fact[i-1]
#     The binomial coefficients.;
    for i in range(0,n+1):
        bin[0][i]=1.0
        bin[i][i]=1.0
    for i in range(2,n+1):
        for j in range(1,i):
            bin[j][i]=bin[j-1][i-1]+bin[j][i-1]
    for i in range(0,n):
        for j in range(0,n):
             a[i][j]=0.0
#     The accuracy constraints.;
    deriv(n, sig, alp, dg, dh1, dh3, bin, nu)
    for i in range(0,n):
        b[i]=dg[i+1]
    for i in range(1,n+1):
        if 2*i-1<=n:
            a[2*i-2][i-1]=fact[i-1]
        for j in range(1,i+1):
            if 2*j<=n:
                a[2*j-1][i-1]=-bin[j][i]*fact[j-1]*dg[i-j]
#     The stability constraints.;
    if ns>=1:
        z1=-3.0
        b[n-1]=-1.0
        for j in range(1,np+1): 
            a[2*j-2][n-1]=z1 ** j
            a[2*j-1][n-1]=0.0
    if ns>=2:
        z1=-1.5
        b[n-2]=-1.0
        for j in range(1,np+1):
            a[2*j-2][n-2]=z1 ** j
            a[2*j-1][n-2]=0.0
    gauss(n,a,b)
    dh1[0]=1.0
    for j in range(1,np+1):
        dh1[j]=b[2*j-2]
    dh2=fndrt(dh1,np)
    for j in range(0,np):
        pd1[j]=-1.0/dh2[j]
    dh1[0]=1.0
    for j in range(1,np+1):
        dh1[j]=b[2*j-1]
    dh2=fndrt(dh1,np)
    for j in range(0,np):
        pd2[j]=-1.0/dh2[j]

#     The tridiagonal matrices.
def matrc(nz,np,iz,dz,k0,rhob,alpw,alpb,ksq,ksqw,ksqb,f1,f2,f3,r1,r2,r3,s1,s2,s3,pd1,pd2,izsrf):
    a1=k0*k0/6.0
    a2=2.0*k0*k0/3.0
    a3=k0*k0/6.0
    cfact=0.5/(dz*dz)
    dfact=1.0/12.0
    for i in range(0,iz):
        f1[i]=1.0/alpw[i]
        f2[i]=1.0
        f3[i]=alpw[i]
        ksq[i]=ksqw[i]
    ii=0
    for i in range(iz,nz+2):
        f1[i]=rhob[ii]/alpb[ii]
        f2[i]=1.0/rhob[ii]
        f3[i]=alpb[ii]
        ksq[i]=ksqb[ii]
        ii+=1
    for i in range(1,nz+1):
#     Discretization by Galerkin's method.
        c1=cfact*f1[i]*(f2[i-1]+f2[i])*f3[i-1]
        c2=-cfact*f1[i]*(f2[i-1]+2.0*f2[i]+f2[i+1])*f3[i]
        c3=cfact*f1[i]*(f2[i]+f2[i+1])*f3[i+1]
        d1=c1+dfact*(ksq[i-1]+ksq[i])
        d2=c2+dfact*(ksq[i-1]+complex(6.0,0)*ksq[i]+ksq[i+1])
        d3=c3+dfact*(ksq[i]+ksq[i+1])
        for j in range(0,np):
            r1[j][i]=a1+pd2[j]*d1
            r2[j][i]=a2+pd2[j]*d2
            r3[j][i]=a3+pd2[j]*d3
            s1[j][i]=a1+pd1[j]*d1
            s2[j][i]=a2+pd1[j]*d2
            s3[j][i]=a3+pd1[j]*d3
#     The entries above the surface.
    for j in range(0,np):
        for i in range(0,izsrf):
            r1[j][i]=0.0
            r2[j][i]=1.0
            r3[j][i]=0.0
            s1[j][i]=0.0
            s2[j][i]=0.0
            s3[j][i]=0.0
#     The matrix decomposition.
    for j in range(0,np):
        for i in range(1,nz+1):
            rfact=complex(1.0,0)/(r2[j][i]-r1[j][i]*r3[j][i-1])
            r1[j][i]=r1[j][i]*rfact
            r3[j][i]=r3[j][i]*rfact
            s1[j][i]=s1[j][i]*rfact
            s2[j][i]=s2[j][i]*rfact
            s3[j][i]=s3[j][i]*rfact

##     Matrix updates.
#def updat(fs1,nz,np,iz,ib,dr,dz,eta,omega,rmax,c0,k0,ci,r,rp,rs,rb,zb,cw,cb,rhob,attn, \
#alpw,alpb,ksq,ksqw,ksqb,f1,f2,f3,r1,r2,r3,s1,s2,s3,pd1,pd2,rsrf,zsrf,izsrf,isrf,attw):
##     Varying bathymetry.
#    if r>=rb[ib]:
#        ib=ib+1
#    if r>=rsrf[isrf]:
#        isrf=isrf+1
#    jzsrf=izsrf
#    z=zsrf[isrf-1]+(r+0.5*dr-rsrf[isrf-1])*(zsrf[isrf]-zsrf[isrf-1])/(rsrf[isrf]-rsrf[isrf-1])
#    izsrf=int(z/dz)
#    jz=iz
#    z=zb[ib-1]+(r+0.5*dr-rb[ib-1])*(zb[ib]-zb[ib-1])/(rb[ib]-rb[ib-1])
#    iz=int(1.0+z/dz)
#    iz=max(2,iz)
#    iz=min(nz,iz)
#    if iz!=jz or izsrf != jzsrf:
#        matrc(nz,np,iz,dz,k0,rhob,alpw,alpb,ksq,ksqw,ksqb,f1,f2,f3,r1,r2,r3,s1,s2,s3,pd1,pd2,izsrf)
##     Varying profiles.
#    if r>=rp:
#        rp = profl(fs1,nz,ci,dz,eta,omega,rmax,c0,k0,rp,cw,cb,rhob,attn,alpw,alpb,ksqw,ksqb,attw)
#        matrc(nz,np,iz,dz,k0,rhob,alpw,alpb,ksq,ksqw,ksqb,f1,f2,f3,r1,r2,r3,s1,s2,s3,pd1,pd2,izsrf)
##     Turn off the stability constraints.
#    if r>=rs:
#        ns=0
#        epade(np,ns,1,k0,dr,pd1,pd2)
#        matrc(nz,np,iz,dz,k0,rhob,alpw,alpb,ksq,ksqw,ksqb,f1,f2,f3,r1,r2,r3,s1,s2,s3,pd1,pd2,izsrf)
#    return ib,isrf,izsrf,iz,rp

########NEW FILE########
__FILENAME__ = rc4
#from http://www.emoticode.net/python/python-implementation-of-rc4-algorithm.html
#runas data = "e"*100 ; key = "f"*3 ; rc4_crypt(data, key)
#bench data = "e"*2000000 ; key = "f"*3 ; rc4_crypt(data, key)
#pythran export rc4_crypt(str, str)

#RC4 Implementation
def rc4_crypt( data , key ):

    S = range(256)
    j = 0
    out = []

    #KSA Phase
    for i in range(256):
        j = (j + S[i] + ord( key[i % len(key)] )) % 256
        S[i] , S[j] = S[j] , S[i]

    #PRGA Phase
    for char in data:
        i = j = 0
        i = ( i + 1 ) % 256
        j = ( j + S[i] ) % 256
        S[i] , S[j] = S[j] , S[i]
        out.append(chr(ord(char) ^ S[(S[i] + S[j]) % 256]))

    return ''.join(out)

########NEW FILE########
__FILENAME__ = roman_decode
#from http://rosettacode.org/wiki/Roman_numerals/Decode#Python
#runas decode('MCMXC')
#runas decode('MMVIII')
#runas decode('MDCLXVI')
#pythran export decode(str)

def decode( roman ):
    s, t = 'MDCLXVI', (1000, 500, 100, 50, 10, 5, 1)
    _rdecode = dict(zip(s, t))
    result = 0
    for r, r1 in zip(roman, roman[1:]):
        rd, rd1 = _rdecode[r], _rdecode[r1]
        result += -rd if rd < rd1 else rd
    return result + _rdecode[roman[-1]]

########NEW FILE########
__FILENAME__ = rosen
import numpy as np

#runas import numpy as np; r = np.arange(1000000, dtype=float); rosen(r)
#bench import numpy as np; r = np.arange(50000000); rosen(r)
#pythran export rosen(int[])
#pythran export rosen(float[])

def rosen(x):
    t0 = 100 * (x[1:] - x[:-1] ** 2) ** 2
    t1 = (1 - x[:-1]) ** 2
    return np.sum(t0 + t1)

########NEW FILE########
__FILENAME__ = scrabble
#from http://stackoverflow.com/questions/18345202/functional-vs-imperative-style-in-python
#pythran export scrabble_fun_score(str, str: int dict)
#pythran export scrabble_imp_score(str, str: int dict)
#runas scrabble_fun_score('tralala', {'t': 1, 'r': 2, 'a': 3, 'l': 4})
#runas scrabble_fun_score('tralala', {'t': 1, 'r': 2, 'a': 3, 'l': 4})
#bench import string; import random; a = "".join([random.choice(string.letters) for i in xrange(12000000)]); v = dict(zip(string.letters, range(1000))); scrabble_fun_score(a, v)

def scrabble_fun_score(word, scoretable):
    return sum([scoretable.get(x, 0) for x in word])


def scrabble_imp_score(word, scoretable):
    score = 0
    for letter in word:
        if letter in scoretable:
            score += scoretable[letter]
    return score

########NEW FILE########
__FILENAME__ = sexy_primes
#from http://stackoverflow.com/questions/11641098/interpreting-a-benchmark-in-c-clojure-python-ruby-scala-and-others
#pythran export primes_below(int)
#runas primes_below(1000)
#bench primes_below(15000)
def is_prime(n):
      return all((n%j > 0) for j in xrange(2, n))

def primes_below(x):
        return [[j-6, j] for j in xrange(9, x+1) if is_prime(j) and is_prime(j-6)]


########NEW FILE########
__FILENAME__ = slowparts
#from https://groups.google.com/forum/#!topic/parakeet-python/p-flp2kdE4U
#pythran export slowparts(int, int, float [][][], float [][][], float [][], float [][], float [][][], float [][][], int)
#runas import numpy as np ;d = 10 ;re = 5 ;params = (d, re, np.ones((2*d, d+1, re)), np.ones((d, d+1, re)),  np.ones((d, 2*d)), np.ones((d, 2*d)), np.ones((d+1, re, d)), np.ones((d+1, re, d)), 1) ; slowparts(*params)
#bench import numpy as np ;d = 87 ;re = 5 ;params = (d, re, np.ones((2*d, d+1, re)), np.ones((d, d+1, re)),  np.ones((d, 2*d)), np.ones((d, 2*d)), np.ones((d+1, re, d)), np.ones((d+1, re, d)), 1) ; slowparts(*params)
from numpy import zeros, power, tanh
def slowparts(d, re, preDz, preWz, SRW, RSW, yxV, xyU, resid):
    """ computes the linear algebra intensive part of the gradients of the grae
    """
    fprime = lambda x: 1 - power(tanh(x), 2)

    partialDU = zeros((d+1, re, 2*d, d))
    for k in range(2*d):
        for i in range(d):
            partialDU[:,:,k,i] = fprime(preDz[k]) * fprime(preWz[i]) * (SRW[i,k] + RSW[i,k]) * yxV[:,:,i]

    return partialDU

########NEW FILE########
__FILENAME__ = smoothing
#from http://www.parakeetpython.com/
#pythran export smoothing(float[], float)
#runas import numpy as np ; a = np.arange(0,1,10e-3) ; smoothing(a, .4)
#bench import numpy as np ; a = np.arange(0,1,1.5e-6) ;smoothing(a, .4)

def smoothing(x, alpha):
  """
  Exponential smoothing of a time series
  For x = 10**6 floats
  - Python runtime: 9 seconds
  - Parakeet runtime: .01 seconds
  """
  s = x.copy()
  for i in xrange(1, len(x)):
    s[i] = alpha * x[i] + (1 - alpha) * s[i-1]
  return s

########NEW FILE########
__FILENAME__ = sobelfilter
#skip.runas import Image; im = Image.open("Scribus.gif"); image_list = list(im.getdata()); cols, rows = im.size; res = range(len(image_list)); sobelFilter(image_list, res, cols, rows)
#runas cols = 100; rows = 100 ;image_list=[x%10+y%20 for x in xrange(cols) for y in xrange(rows)]; sobelFilter(image_list, cols, rows)
#bench cols = 1000; rows = 500 ;image_list=[x%10+y%20 for x in xrange(cols) for y in xrange(rows)]; sobelFilter(image_list, cols, rows)
#pythran export sobelFilter(int list, int, int)
def sobelFilter(original_image, cols, rows):
    edge_image = range(len(original_image))
    for i in xrange(rows):
        edge_image[i * cols] = 255
        edge_image[((i + 1) * cols) - 1] = 255

    for i in xrange(1, cols - 1):
        edge_image[i] = 255
        edge_image[i + ((rows - 1) * cols)] = 255

    for iy in xrange(1, rows - 1):
        for ix in xrange(1, cols - 1):
            sum_x = 0
            sum_y = 0
            sum = 0
            #x gradient approximation
            sum_x += original_image[ix - 1 + (iy - 1) * cols] * -1
            sum_x += original_image[ix + (iy - 1) * cols] * -2
            sum_x += original_image[ix + 1 + (iy - 1) * cols] * -1
            sum_x += original_image[ix - 1 + (iy + 1) * cols] * 1
            sum_x += original_image[ix + (iy + 1) * cols] * 2
            sum_x += original_image[ix + 1 + (iy + 1) * cols] * 1
            sum_x = min(255, max(0, sum_x))
            #y gradient approximatio
            sum_y += original_image[ix - 1 + (iy - 1) * cols] * 1
            sum_y += original_image[ix + 1 + (iy - 1) * cols] * -1
            sum_y += original_image[ix - 1 + (iy) * cols] * 2
            sum_y += original_image[ix + 1 + (iy) * cols] * -2
            sum_y += original_image[ix - 1 + (iy + 1) * cols] * 1
            sum_y += original_image[ix + 1 + (iy + 1) * cols] * -1
            sum_y = min(255, max(0, sum_y))

            #GRADIENT MAGNITUDE APPROXIMATION
            sum = abs(sum_x) + abs(sum_y)

            #make edges black and background white
            edge_image[ix + iy * cols] = 255 - (255 & sum)
    return edge_image

########NEW FILE########
__FILENAME__ = stone
#pythran export whetstone(int)
#runas whetstone(2*10**2)
#bench whetstone(1500)
"""
/*
 * C Converted Whetstone Double Precision Benchmark
 *        Version 1.2    22 March 1998
 *
 *    (c) Copyright 1998 Painter Engineering, Inc.
 *        All Rights Reserved.
 *
 *        Permission is granted to use, duplicate, and
 *        publish this text and program as long as it
 *        includes this entire comment block and limited
 *        rights reference.
 *
 * Converted by Rich Painter, Painter Engineering, Inc. based on the
 * www.netlib.org benchmark/whetstoned version obtained 16 March 1998.
 *
 * A novel approach was used here to keep the look and feel of the
 * FORTRAN version.  Altering the FORTRAN-based array indices,
 * starting at element 1, to start at element 0 for C, would require
 * numerous changes, including decrementing the variable indices by 1.
 * Instead, the array E1[] was declared 1 element larger in C.  This
 * allows the FORTRAN index range to function without any literal or
 * variable indices changes.  The array element E1[0] is simply never
 * used and does not alter the benchmark results.
 *
 * The major FORTRAN comment blocks were retained to minimize
 * differences between versions.  Modules N5 and N12, like in the
 * FORTRAN version, have been eliminated here.
 *
 * An optional command-line argument has been provided [-c] to
 * offer continuous repetition of the entire benchmark.
 * An optional argument for setting an alternate LOOP count is also
 * provided.  Define PRINTOUT to cause the POUT() function to print
 * outputs at various stages.  Final timing measurements should be
 * made with the PRINTOUT undefined.
 *
 * Questions and comments may be directed to the author at
 *            r.painter@ieee.org
 */
"""
from math import sin as DSIN, cos as DCOS, atan as DATAN, log as DLOG, exp as DEXP, sqrt as DSQRT


def whetstone(loopstart):

#    The actual benchmark starts here.
    T  = .499975;
    T1 = 0.50025;
    T2 = 2.0;

#    With loopcount LOOP=10, one million Whetstone instructions
#    will be executed in EACH MAJOR LOOP..A MAJOR LOOP IS EXECUTED
#    'II' TIMES TO INCREASE WALL-CLOCK TIMING ACCURACY.
    LOOP = loopstart;
    II   = 1;

    JJ = 1;

    while JJ <= II:

        N1  = 0;
        N2  = 12 * LOOP;
        N3  = 14 * LOOP;
        N4  = 345 * LOOP;
        N6  = 210 * LOOP;
        N7  = 32 * LOOP;
        N8  = 899 * LOOP;
        N9  = 616 * LOOP;
        N10 = 0;
        N11 = 93 * LOOP;
    #    Module 1: Simple identifiers
        X1  =  1.0;
        X2  = -1.0;
        X3  = -1.0;
        X4  = -1.0;

        for I in xrange(1,N1+1):
            X1 = (X1 + X2 + X3 - X4) * T;
            X2 = (X1 + X2 - X3 + X4) * T;
            X3 = (X1 - X2 + X3 + X4) * T;
            X4 = (-X1+ X2 + X3 + X4) * T;

    #    Module 2: Array elements
        E1 =  [ 1.0, -1.0, -1.0, -1.0 ]

        for I in xrange(1,N2+1):
            E1[0] = ( E1[0] + E1[1] + E1[2] - E1[3]) * T;
            E1[1] = ( E1[0] + E1[1] - E1[2] + E1[3]) * T;
            E1[2] = ( E1[0] - E1[1] + E1[2] + E1[3]) * T;
            E1[3] = (-E1[0] + E1[1] + E1[2] + E1[3]) * T;


    #    Module 3: Array as parameter
        for I in xrange(1,N3+1):
            PA(E1, T, T2);


    #    Module 4: Conditional jumps
        J = 1;
        for I in xrange(1,N4+1):
            if J == 1:
                J = 2;
            else:
                J = 3;

            if J > 2:
                J = 0;
            else:
                J = 1;

            if J < 1:
                J = 1;
            else:
                J = 0;


    #    Module 5: Omitted
    #     Module 6: Integer arithmetic

        J = 1;
        K = 2;
        L = 3;

        for I in xrange(1,N6+1):
            J = J * (K-J) * (L-K);
            K = L * K - (L-J) * K;
            L = (L-K) * (K+J);
            E1[L-2] = J + K + L;
            E1[K-2] = J * K * L;


    #    Module 7: Trigonometric functions
        X = 0.5;
        Y = 0.5;

        for I in xrange(1,N7+1):
            X = T * DATAN(T2*DSIN(X)*DCOS(X)/(DCOS(X+Y)+DCOS(X-Y)-1.0));
            Y = T * DATAN(T2*DSIN(Y)*DCOS(Y)/(DCOS(X+Y)+DCOS(X-Y)-1.0));


    #    Module 8: Procedure calls
        X = 1.0;
        Y = 1.0;
        Z = 1.0;

        for I in xrange(1,N8+1):
            Z=P3(X,Y,T, T2)

    #    Module 9: Array references
        J = 1;
        K = 2;
        L = 3;
        E1[0] = 1.0;
        E1[1] = 2.0;
        E1[2] = 3.0;

        for I in xrange(1,N9+1):
            P0(E1, J, K, L)


    #    Module 10: Integer arithmetic
        J = 2;
        K = 3;

        for I in xrange(1,N10+1):
            J = J + K;
            K = J + K;
            J = K - J;
            K = K - J - J;


    #    Module 11: Standard functions
        X = 0.75;

        for I in xrange(1,N11+1):
            X = DSQRT(DEXP(DLOG(X)/T1));

        JJ+=1


    KIP = (100.0*LOOP*II)
    return KIP

def PA(E, T, T2):
    J = 0;

    while J<6:
        E[0] = ( E[0] + E[1] + E[2] - E[3]) * T;
        E[1] = ( E[0] + E[1] - E[2] + E[3]) * T;
        E[2] = ( E[0] - E[1] + E[2] + E[3]) * T;
        E[3] = (-E[0] + E[1] + E[2] + E[3]) / T2;
        J += 1;

def P0(E1, J, K, L):
    E1[J-1] = E1[K-1];
    E1[K-1] = E1[L-1];
    E1[L-1] = E1[J-1];

def P3(X, Y, T, T2):
    X1 = X;
    Y1 = Y;
    X1 = T * (X1 + Y1);
    Y1 = T * (X1 + Y1);
    return (X1 + Y1) / T2;


########NEW FILE########
__FILENAME__ = sumarray3d
#from http://stackoverflow.com/questions/20076030/lack-of-speedup-and-erroneous-results-with-openmp-and-cython/20183767#20183767
#pythran export summation(float32[][], float32[], float32[][])
#runas import numpy as np ; N=30 ; pos = np.arange(N*3., dtype=np.float32).reshape((N,3)) ; w = np.ones(N, dtype=np.float32) ; p =  np.arange(N*3., dtype=np.float32).reshape((N,3)) ; summation(pos, w, p)
#bench import numpy as np ; N=300 ; pos = np.arange(1, N*3. + 1, dtype=np.float32).reshape((N,3)) ; w = np.ones(N, dtype=np.float32) ; p =  np.arange(N*3., dtype=np.float32).reshape((N,3)) ; summation(pos, w, p)
import numpy as np
def summation(pos, weights, points):
  n_points = len(points)
  n_weights = len(weights)
  sum_array3d = np.zeros((n_points,3))
  def compute(i):
    pxi = points[i, 0]
    pyi = points[i, 1]
    pzi = points[i, 2]
    total = 0.0
    for j in xrange(n_weights):
      weight_j = weights[j]
      xj = pos[j,0]
      yj = pos[j,1]
      zj = pos[j,2]
      dx = pxi - pos[j, 0]
      dy = pyi - pos[j, 1]
      dz = pzi - pos[j, 2]
      dr = 1.0/np.sqrt(dx*dx + dy*dy + dz*dz)
      total += weight_j * dr
      sum_array3d[i,0] += weight_j * dx
      sum_array3d[i,1] += weight_j * dy
      sum_array3d[i,2] += weight_j * dz
    return total 
  sum_array = np.array([compute(i) for i in xrange(n_points)])
  return sum_array, sum_array3d

########NEW FILE########
__FILENAME__ = sum_primes
# taken from http://oddbloke.uwcs.co.uk/parallel_benchmarks/
#pythran export sum_primes(int)
#runas sum_primes(200)
#bench sum_primes(320000)
import math
def isprime(n):
    """Returns True if n is prime and False otherwise"""
    if n < 2:
        return False
    if n == 2:
        return True
    max = int(math.ceil(math.sqrt(n)))
    i = 2
    while i <= max:
        if n % i == 0:
            return False
        i += 1
    return True

def sum_primes(n):
    """Calculates sum of all primes below given integer n"""
    return sum([x for x in xrange(2,n) if isprime(x)])

########NEW FILE########
__FILENAME__ = vibr_energy
#from http://stackoverflow.com/questions/17112550/python-and-numba-for-vectorized-functions
#pythran export calculate_vibr_energy(float[], float[],int [])
#pythran export calculate_vibr_energy(float[], float[], int)
#pythran export calculate_vibr_energy(float[], float[], float)
#pythran export calculate_vibr_energy(float[], float[], float [])
#runas import numpy as np ; a = np.sin(np.ones(1000000)) ; b = np.cos(np.ones(1000000)) ; n = np.arange(1000000); calculate_vibr_energy(a, b, n)
#runas import numpy as np ; a = np.sin(np.ones(1000000)) ; b = np.cos(np.ones(1000000)) ; calculate_vibr_energy(a, b, 10)
#runas import numpy as np ; a = np.sin(np.ones(1000000)) ; b = np.cos(np.ones(1000000)) ; calculate_vibr_energy(a, b, 10.)
#runas import numpy as np ; a = np.sin(np.ones(1000000)) ; b = np.cos(np.ones(1000000)) ; n = np.arange(1000000, dtype=np.double); calculate_vibr_energy(a, b, n)
#bench import numpy as np ; a = np.sin(np.ones(1000000)) ; b = np.cos(np.ones(1000000)) ; n = np.arange(1000000); calculate_vibr_energy(a, b, n)
import numpy
def calculate_vibr_energy(harmonic, anharmonic, i):
    return numpy.exp(-harmonic * i - anharmonic * (i ** 2))

########NEW FILE########
__FILENAME__ = wave_simulation
# from https://github.com/sklam/numba-example-wavephysics
#runas test(50)
#bench test(55000)
import numpy as np
from math import ceil

def physics(masspoints, dt, plunk, which):
  ppos = masspoints[1]
  cpos = masspoints[0]
  N = cpos.shape[0]
  # apply hooke's law
  HOOKE_K = 2100000.
  DAMPING = 0.0001
  MASS = .01

  force = np.zeros((N, 2))
  for i in range(1, N):
    dx, dy = cpos[i] - cpos[i - 1]
    dist = np.sqrt(dx**2 + dy**2)
    assert dist != 0
    fmag = -HOOKE_K * dist
    cosine = dx / dist
    sine = dy / dist
    fvec = np.array([fmag * cosine, fmag * sine])
    force[i - 1] -= fvec
    force[i] += fvec

  force[0] = force[-1] = 0, 0
  force[which][1] += plunk
  accel = force / MASS

  # verlet integration
  npos = (2 - DAMPING) * cpos - (1 - DAMPING) * ppos + accel * (dt**2)

  masspoints[1] = cpos
  masspoints[0] = npos

#pythran export test(int)
def test(PARTICLE_COUNT):
    SUBDIVISION = 300
    FRAMERATE = 60
    count = PARTICLE_COUNT
    width, height = 600, 200

    masspoints = np.empty((2, count, 2), np.float64)
    initpos = np.zeros(count, np.float64)
    for i in range(1, count):
        initpos[i] = initpos[i - 1] + float(width) / count
    masspoints[:, :, 0] = initpos
    masspoints[:, :, 1] = height / 2
    f = 15
    plunk_pos = count // 2
    physics( masspoints, 1./ (SUBDIVISION * FRAMERATE), f, plunk_pos)
    return masspoints[0, count // 2]

########NEW FILE########
__FILENAME__ = wdist
#from http://stackoverflow.com/questions/19277244/fast-weighted-euclidean-distance-between-points-in-arrays/19277334#19277334
#pythran export slow_wdist(float64 [][], float64 [][], float64[][])
#runas import numpy as np ; A = np.arange(6.).reshape((2,3)) ; B =  np.arange(1,7.).reshape((2,3)) ; W = np.arange(2,8.).reshape((2,3)) ; slow_wdist(A,B,W)
#bench S = 520.; import numpy as np ; A = np.arange(S).reshape((2,S / 2)) ; B =  np.arange(1,1 + S).reshape((2,S / 2)) ; W = np.arange(2,S + 2).reshape((2,S / 2)) ; slow_wdist(A,B,W)

import numpy as np
def slow_wdist(A, B, W):

    k,m = A.shape
    _,n = B.shape
    D = np.zeros((m, n))

    for ii in xrange(m):
        for jj in xrange(n):
            wdiff = (A[:,ii] - B[:,jj]) / W[:,ii]
            D[ii,jj] = np.sqrt((wdiff**2).sum())
    return D

########NEW FILE########
__FILENAME__ = zero
#pythran export zero(int, int)
#runas zero(10,20)
#bench zero(6000,6000)
def zero(n,m): return [[0 for row in xrange(n)] for col in xrange(m)]


########NEW FILE########
__FILENAME__ = euler01
#pythran export solve(int)
#runas solve(1000)
def solve(max):
    '''
    If we list all the natural numbers below 10 that are multiples of 3 or 5, we get 3, 5, 6 and 9. The sum of these multiples is 23.

    Find the sum of all the multiples of 3 or 5 below 1000.
    '''

    n = 0
    for i in xrange(1, max):
        if not i % 5 or not i % 3:
            n = n + i

    return n

########NEW FILE########
__FILENAME__ = euler02
#skip.runas solve(4000000)
#skip.pythran export solve(int)
#unitest.skip bad type inference
def solve(max):
    '''
    Each new term in the Fibonacci sequence is generated by adding the previous two terms. By starting with 1 and 2, the first 10 terms will be:
    
    1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ...
    
    Find the sum of all the even-valued terms in the sequence which do not exceed four million.
    '''

    cache = {}
    def fib(n):
        cache[n] = cache.get(n, 0) or (n <= 1 and 1 or fib(n-1) + fib(n-2))
        return cache[n]

    n = 0
    i = 0
    while fib(i) <= max:
        if not fib(i) % 2: n = n + fib(i)
        i = i + 1

    return n

########NEW FILE########
__FILENAME__ = euler03
#pythran export solve(int)
#runas solve(600851475143)
def solve(n):
    '''
    The prime factors of 13195 are 5, 7, 13 and 29.
    
    What is the largest prime factor of the number 600851475143 ?
    '''

    i = 2
    while i * i < n:
        while n % i == 0:
            n = n / i
        i = i + 1

    return n

########NEW FILE########
__FILENAME__ = euler04
#pythran export solve(int)
#runas solve(3)
def solve(digit):
    '''
    A palindromic number reads the same both ways. The largest palindrome made from the product of two 2-digit numbers is 9009 = 91 x 99.
    
    Find the largest palindrome made from the product of two 3-digit numbers.
    '''

    n = 0
    for a in xrange(10 ** digit - 1, 10 ** (digit - 1), -1):
        for b in xrange(a, 10 ** (digit - 1), -1):
            x = a * b
            if x > n:
                s = str(a * b)
                if s == s[::-1]:
                    n = a * b

    return n

########NEW FILE########
__FILENAME__ = euler05
#pythran export solve(int, int)
#runas solve(1, 20)
def solve(start, end):
    '''
    2520 is the smallest number that can be divided by each of the numbers from 1 to 10 without any remainder.
    
    What is the smallest number that is evenly divisible by all of the numbers from 1 to 20?
    '''
    def gcd(a,b): return b and gcd(b, a % b) or a
    def lcm(a,b): return a * b / gcd(a,b)

    n = 1
    for i in xrange(start, end + 1):
        n = lcm(n, i)

    return n

########NEW FILE########
__FILENAME__ = euler06
#runas solve(100)
#pythran export solve(int)
def solve(max):
    '''
    The sum of the squares of the first ten natural numbers is,
    1^2 + 2^2 + ... + 10^2 = 385
    The square of the sum of the first ten natural numbers is,
    (1 + 2 + ... + 10)^2 = 552 = 3025
    Hence the difference between the sum of the squares of the first ten natural numbers and the square of the sum is 3025 - 385 = 2640.
    
    Find the difference between the sum of the squares of the first one hundred natural numbers and the square of the sum.
    '''

    r = xrange(1, max + 1)
    a = sum(r)
    return a * a - sum(i*i for i in r)

########NEW FILE########
__FILENAME__ = euler07
#pythran export solve(int)
#runas solve(10001)
def solve(p):
    '''
    By listing the first six prime numbers: 2, 3, 5, 7, 11, and 13, we can see that the 6th prime is 13.

    What is the 10001st prime number?
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def prime(x):
        ''' Returns the xth prime '''

        lastn = prime_list[-1]
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    return prime(p - 1)

########NEW FILE########
__FILENAME__ = euler08
#runas solve(5)
#pythran export solve(int)
def solve(cons):
    '''
    Find the greatest product of five consecutive digits in the 1000-digit number.

    73167176531330624919225119674426574742355349194934
    96983520312774506326239578318016984801869478851843
    85861560789112949495459501737958331952853208805511
    12540698747158523863050715693290963295227443043557
    66896648950445244523161731856403098711121722383113
    62229893423380308135336276614282806444486645238749
    30358907296290491560440772390713810515859307960866
    70172427121883998797908792274921901699720888093776
    65727333001053367881220235421809751254540594752243
    52584907711670556013604839586446706324415722155397
    53697817977846174064955149290862569321978468622482
    83972241375657056057490261407972968652414535100474
    82166370484403199890008895243450658541227588666881
    16427171479924442928230863465674813919123162824586
    17866458359124566529476545682848912883142607690042
    24219022671055626321111109370544217506941658960408
    07198403850962455444362981230987879927244284909188
    84580156166097919133875499200524063689912560717606
    05886116467109405077541002256983155200055935729725
    71636269561882670428252483600823257530420752963450
    '''

    s = '7316717653133062491922511967442657474235534919493496983520312774506326239578318016984801869478851843858615607891129494954595017379583319528532088055111254069874715852386305071569329096329522744304355766896648950445244523161731856403098711121722383113622298934233803081353362766142828064444866452387493035890729629049156044077239071381051585930796086670172427121883998797908792274921901699720888093776657273330010533678812202354218097512545405947522435258490771167055601360483958644670632441572215539753697817977846174064955149290862569321978468622482839722413756570560574902614079729686524145351004748216637048440319989000889524345065854122758866688116427171479924442928230863465674813919123162824586178664583591245665294765456828489128831426076900422421902267105562632111110937054421750694165896040807198403850962455444362981230987879927244284909188845801561660979191338754992005240636899125607176060588611646710940507754100225698315520005593572972571636269561882670428252483600823257530420752963450'
    n = 0
    for i in xrange(0, len(s)-4):
        p = 1
        for j in xrange(i,i+cons):
            p = p * int(s[j])
        if p > n: n = p

    return n

########NEW FILE########
__FILENAME__ = euler09
#pythran export solve(int)
#runas solve(1000)
def solve(v):
    '''
    A Pythagorean triplet is a set of three natural numbers, a  b  c, for which,
    a^2 + b^2 = c^2
    For example, 3^2 + 4^2 = 9 + 16 = 25 = 5^2.
    
    There exists exactly one Pythagorean triplet for which a + b + c = 1000.
    Find the product abc.
    '''

    for a in xrange(1, v):
        for b in xrange(a, v):
            c = v - a - b
            if c > 0:
                if c*c == a*a + b*b:
                    return a*b*c

########NEW FILE########
__FILENAME__ = euler10
#runas solve(2000000)
#pythran export solve(int)
def solve(max):
    '''
    The sum of the primes below 10 is 2 + 3 + 5 + 7 = 17.
    
    Find the sum of all the primes below two million.
    '''

    sieve = [True] * max    # Sieve is faster for 2M primes

    def mark(sieve, x):
        for i in xrange(x+x, len(sieve), x):
            sieve[i] = False

    for x in xrange(2, int(len(sieve) ** 0.5) + 1):
        if sieve[x]: mark(sieve, x)

    return sum(i for i in xrange(2, len(sieve)) if sieve[i])

########NEW FILE########
__FILENAME__ = euler11
#runas solve(4)
#pythran export solve(int)
def solve(adj):
    nums = [
        [ 8, 2,22,97,38,15, 0,40, 0,75, 4, 5, 7,78,52,12,50,77,91, 8,],
        [49,49,99,40,17,81,18,57,60,87,17,40,98,43,69,48, 4,56,62, 0,],
        [81,49,31,73,55,79,14,29,93,71,40,67,53,88,30, 3,49,13,36,65,],
        [52,70,95,23, 4,60,11,42,69,24,68,56, 1,32,56,71,37, 2,36,91,],
        [22,31,16,71,51,67,63,89,41,92,36,54,22,40,40,28,66,33,13,80,],
        [24,47,32,60,99, 3,45, 2,44,75,33,53,78,36,84,20,35,17,12,50,],
        [32,98,81,28,64,23,67,10,26,38,40,67,59,54,70,66,18,38,64,70,],
        [67,26,20,68, 2,62,12,20,95,63,94,39,63, 8,40,91,66,49,94,21,],
        [24,55,58, 5,66,73,99,26,97,17,78,78,96,83,14,88,34,89,63,72,],
        [21,36,23, 9,75, 0,76,44,20,45,35,14, 0,61,33,97,34,31,33,95,],
        [78,17,53,28,22,75,31,67,15,94, 3,80, 4,62,16,14, 9,53,56,92,],
        [16,39, 5,42,96,35,31,47,55,58,88,24, 0,17,54,24,36,29,85,57,],
        [86,56, 0,48,35,71,89, 7, 5,44,44,37,44,60,21,58,51,54,17,58,],
        [19,80,81,68, 5,94,47,69,28,73,92,13,86,52,17,77, 4,89,55,40,],
        [ 4,52, 8,83,97,35,99,16, 7,97,57,32,16,26,26,79,33,27,98,66,],
        [88,36,68,87,57,62,20,72, 3,46,33,67,46,55,12,32,63,93,53,69,],
        [ 4,42,16,73,38,25,39,11,24,94,72,18, 8,46,29,32,40,62,76,36,],
        [20,69,36,41,72,30,23,88,34,62,99,69,82,67,59,85,74, 4,36,16,],
        [20,73,35,29,78,31,90, 1,74,31,49,71,48,86,81,16,23,57, 5,54,],
        [ 1,70,54,71,83,51,54,69,16,92,33,48,61,43,52, 1,89,19,67,48,],
    ]

    def seqs(nums, row, col):
        if row + adj <= len(nums):                                yield list(nums[i][col] for i in xrange(row, row+adj))
        if col + adj <= len(nums[row]):                           yield list(nums[row][i] for i in xrange(col, col+adj))
        if row + adj <= len(nums) and col + adj <= len(nums[row]):yield list(nums[row+i][col+i] for i in xrange(0,adj))
        if row + adj <= len(nums) and col >= adj - 1:             yield list(nums[row+i][col-i] for i in xrange(0,adj))

    def product(seq):
        n = 1
        for x in seq: n = n * x
        return n

    def list_seqs(nums):
        for row in xrange(0, len(nums)):
            for col in xrange(0, len(nums[row])):
                for seq in seqs(nums, row, col):
                    yield seq

    return max(product(seq) for seq in list_seqs(nums))


########NEW FILE########
__FILENAME__ = euler12
#runas solve(500)
#pythran export solve(int)
def solve(nfact):

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def prime(x):
        ''' Returns the xth prime '''

        lastn = prime_list[-1]
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    def num_factors(n):
        ''' Returns the number of factors of n, including 1 and n '''
        div = 1
        x = 0
        while n > 1:
            c = 1
            while not n % prime(x):
                c = c + 1
                n = n / prime(x)
            x = x + 1
            div = div * c
        return div

    for i in xrange(1, 1000000000):
        n = i * (i+1) / 2
        if num_factors(n) > nfact:
            return n
            break


########NEW FILE########
__FILENAME__ = euler13
#runas solve()
#pythran export solve()
def solve():
    return str(sum((
    37107287533902102798797998220837590246510135740250,
    46376937677490009712648124896970078050417018260538,
    74324986199524741059474233309513058123726617309629,
    91942213363574161572522430563301811072406154908250,
    23067588207539346171171980310421047513778063246676,
    89261670696623633820136378418383684178734361726757,
    28112879812849979408065481931592621691275889832738,
    44274228917432520321923589422876796487670272189318,
    47451445736001306439091167216856844588711603153276,
    70386486105843025439939619828917593665686757934951,
    62176457141856560629502157223196586755079324193331,
    64906352462741904929101432445813822663347944758178,
    92575867718337217661963751590579239728245598838407,
    58203565325359399008402633568948830189458628227828,
    80181199384826282014278194139940567587151170094390,
    35398664372827112653829987240784473053190104293586,
    86515506006295864861532075273371959191420517255829,
    71693888707715466499115593487603532921714970056938,
    54370070576826684624621495650076471787294438377604,
    53282654108756828443191190634694037855217779295145,
    36123272525000296071075082563815656710885258350721,
    45876576172410976447339110607218265236877223636045,
    17423706905851860660448207621209813287860733969412,
    81142660418086830619328460811191061556940512689692,
    51934325451728388641918047049293215058642563049483,
    62467221648435076201727918039944693004732956340691,
    15732444386908125794514089057706229429197107928209,
    55037687525678773091862540744969844508330393682126,
    18336384825330154686196124348767681297534375946515,
    80386287592878490201521685554828717201219257766954,
    78182833757993103614740356856449095527097864797581,
    16726320100436897842553539920931837441497806860984,
    48403098129077791799088218795327364475675590848030,
    87086987551392711854517078544161852424320693150332,
    59959406895756536782107074926966537676326235447210,
    69793950679652694742597709739166693763042633987085,
    41052684708299085211399427365734116182760315001271,
    65378607361501080857009149939512557028198746004375,
    35829035317434717326932123578154982629742552737307,
    94953759765105305946966067683156574377167401875275,
    88902802571733229619176668713819931811048770190271,
    25267680276078003013678680992525463401061632866526,
    36270218540497705585629946580636237993140746255962,
    24074486908231174977792365466257246923322810917141,
    91430288197103288597806669760892938638285025333403,
    34413065578016127815921815005561868836468420090470,
    23053081172816430487623791969842487255036638784583,
    11487696932154902810424020138335124462181441773470,
    63783299490636259666498587618221225225512486764533,
    67720186971698544312419572409913959008952310058822,
    95548255300263520781532296796249481641953868218774,
    76085327132285723110424803456124867697064507995236,
    37774242535411291684276865538926205024910326572967,
    23701913275725675285653248258265463092207058596522,
    29798860272258331913126375147341994889534765745501,
    18495701454879288984856827726077713721403798879715,
    38298203783031473527721580348144513491373226651381,
    34829543829199918180278916522431027392251122869539,
    40957953066405232632538044100059654939159879593635,
    29746152185502371307642255121183693803580388584903,
    41698116222072977186158236678424689157993532961922,
    62467957194401269043877107275048102390895523597457,
    23189706772547915061505504953922979530901129967519,
    86188088225875314529584099251203829009407770775672,
    11306739708304724483816533873502340845647058077308,
    82959174767140363198008187129011875491310547126581,
    97623331044818386269515456334926366572897563400500,
    42846280183517070527831839425882145521227251250327,
    55121603546981200581762165212827652751691296897789,
    32238195734329339946437501907836945765883352399886,
    75506164965184775180738168837861091527357929701337,
    62177842752192623401942399639168044983993173312731,
    32924185707147349566916674687634660915035914677504,
    99518671430235219628894890102423325116913619626622,
    73267460800591547471830798392868535206946944540724,
    76841822524674417161514036427982273348055556214818,
    97142617910342598647204516893989422179826088076852,
    87783646182799346313767754307809363333018982642090,
    10848802521674670883215120185883543223812876952786,
    71329612474782464538636993009049310363619763878039,
    62184073572399794223406235393808339651327408011116,
    66627891981488087797941876876144230030984490851411,
    60661826293682836764744779239180335110989069790714,
    85786944089552990653640447425576083659976645795096,
    66024396409905389607120198219976047599490197230297,
    64913982680032973156037120041377903785566085089252,
    16730939319872750275468906903707539413042652315011,
    94809377245048795150954100921645863754710598436791,
    78639167021187492431995700641917969777599028300699,
    15368713711936614952811305876380278410754449733078,
    40789923115535562561142322423255033685442488917353,
    44889911501440648020369068063960672322193204149535,
    41503128880339536053299340368006977710650566631954,
    81234880673210146739058568557934581403627822703280,
    82616570773948327592232845941706525094512325230608,
    22918802058777319719839450180888072429661980811197,
    77158542502016545090413245809786882778948721859617,
    72107838435069186155435662884062257473692284509516,
    20849603980134001723930671666823555245252804609722,
    53503534226472524250874054075591789781264330331690,
    )))[0:10]


########NEW FILE########
__FILENAME__ = euler14
#runas solve(1000000)
#pythran export solve(int)
def solve(max_init):
    cache = { 1: 1 }
    def chain(cache, n):
        if not cache.get(n,0):
            if n % 2: cache[n] = 1 + chain(cache, 3*n + 1)
            else: cache[n] = 1 + chain(cache, n/2)
        return cache[n]

    m,n = 0,0
    for i in xrange(1, max_init):
        c = chain(cache, i)
        if c > m: m,n = c,i

    return n


########NEW FILE########
__FILENAME__ = euler15
#runas solve()
#pythran export solve()
def solve():
    def fact(n):
        f = 1L
        for x in xrange(1, n+1): f = f * x
        return f

    return fact(40) / fact(20) / fact(20)


########NEW FILE########
__FILENAME__ = euler16
#runas solve(1000)
#pythran export solve(int)
def solve(pow2):
    def digits(n):
        s = 0
        while n > 0:
            s = s + (n % 10)
            n = n / 10
        return s

    return digits(pow(2L,pow2))


########NEW FILE########
__FILENAME__ = euler17
#runas solve(1, 1000)
#pythran export solve(int, int)
#FIXME unittest.skip conflicting name for end
def solve(start, end):
    '''
    How many letters would be needed to write all the numbers in words from 1 to 1000?
    '''

    words = [
        (   1,  'one'      , ''     ),
        (   2,  'two'      , ''     ),
        (   3,  'three'    , ''     ),
        (   4,  'four'     , ''     ),
        (   5,  'five'     , ''     ),
        (   6,  'six'      , ''     ),
        (   7,  'seven'    , ''     ),
        (   8,  'eight'    , ''     ),
        (   9,  'nine'     , ''     ),
        (  10,  'ten'      , ''     ),
        (  11,  'eleven'   , ''     ),
        (  12,  'twelve'   , ''     ),
        (  13,  'thirteen' , ''     ),
        (  14,  'fourteen' , ''     ),
        (  15,  'fifteen'  , ''     ),
        (  16,  'sixteen'  , ''     ),
        (  17,  'seventeen', ''     ),
        (  18,  'eighteen' , ''     ),
        (  19,  'nineteen' , ''     ),
        (  20,  'twenty'   , ''     ),
        (  30,  'thirty'   , ''     ),
        (  40,  'forty'    , ''     ),
        (  50,  'fifty'    , ''     ),
        (  60,  'sixty'    , ''     ),
        (  70,  'seventy'  , ''     ),
        (  80,  'eighty'   , ''     ),
        (  90,  'ninety'   , ''     ),
        ( 100,  'hundred'  , 'and'  ),
        (1000,  'thousand' , 'and'  ),
    ]
    words.reverse()

    def spell(n, words):
        word = []
        while n > 0:
            for num in words:
                if num[0] <= n:
                    div = n / num[0]
                    n = n % num[0]
                    if num[2]: word.append(' '.join(spell(div, words)))
                    word.append(num[1])
                    if num[2] and n: word.append(num[2])
                    break
        return word

    return sum(len(word) for n in xrange(start, end + 1) for word in spell(n, words))


########NEW FILE########
__FILENAME__ = euler18
#runas solve(16384)
#pythran export solve(int)
def solve(max_route):
    '''
    By starting at the top of the triangle below and moving to adjacent numbers on the row below, the maximum total from top to bottom is 23.

    3
    7 5
    2 4 6
    8 5 9 3

    That is, 3 + 7 + 4 + 9 = 23.

    Find the maximum total from top to bottom of the triangle below:

    75
    95 64
    17 47 82
    18 35 87 10
    20 04 82 47 65
    19 01 23 75 03 34
    88 02 77 73 07 63 67
    99 65 04 28 06 16 70 92
    41 41 26 56 83 40 80 70 33
    41 48 72 33 47 32 37 16 94 29
    53 71 44 65 25 43 91 52 97 51 14
    70 11 33 28 77 73 17 78 39 68 17 57
    91 71 52 38 17 14 91 43 58 50 27 29 48
    63 66 04 68 89 53 67 30 73 16 69 87 40 31
    04 62 98 27 23 09 70 98 73 93 38 53 60 04 23

    NOTE: As there are only 16384 routes, it is possible to solve this problem by trying every route. However, Problem 67, is the same challenge with a triangle containing one-hundred rows; it cannot be solved by brute force, and requires a clever method! ;o)
    '''

    triangle = [
        [75,                                                         ],
        [95, 64,                                                     ],
        [17, 47, 82,                                                 ],
        [18, 35, 87, 10,                                             ],
        [20,  4, 82, 47, 65,                                         ],
        [19,  1, 23, 75,  3, 34,                                     ],
        [88,  2, 77, 73,  7, 63, 67,                                 ],
        [99, 65,  4, 28,  6, 16, 70, 92,                             ],
        [41, 41, 26, 56, 83, 40, 80, 70, 33,                         ],
        [41, 48, 72, 33, 47, 32, 37, 16, 94, 29,                     ],
        [53, 71, 44, 65, 25, 43, 91, 52, 97, 51, 14,                 ],
        [70, 11, 33, 28, 77, 73, 17, 78, 39, 68, 17, 57,             ],
        [91, 71, 52, 38, 17, 14, 91, 43, 58, 50, 27, 29, 48,         ],
        [63, 66,  4, 68, 89, 53, 67, 30, 73, 16, 69, 87, 40, 31,     ],
        [ 4, 62, 98, 27, 23,  9, 70, 98, 73, 93, 38, 53, 60,  4, 23, ],
    ]

    def path(triangle, num):
        s = triangle[0][0]
        col = 0
        for row in xrange(1, len(triangle)):
            if num % 2: col = col + 1
            num = num / 2
            s = s + triangle[row][col]
        return s

    return max(path(triangle, n) for n in xrange(0, max_route))

########NEW FILE########
__FILENAME__ = euler19
#runas solve()
#unittest.skip date time not supported
#pythran export solve()
def solve():
    '''
    You are given the following information, but you may prefer to do some research for yourself.

    1 Jan 1900 was a Monday.
    Thirty days has September,
    April, June and November.
    All the rest have thirty-one,
    Saving February alone,
    Which has twenty-eight, rain or shine.
    And on leap years, twenty-nine.
    A leap year occurs on any year evenly divisible by 4, but not on a century unless it is divisible by 400.

    How many Sundays fell on the first of the month during the twentieth century (1 Jan 1901 to 31 Dec 2000)?
    '''
    import datetime

    sundays = 0
    for year in xrange(1901, 2001):
        for month in xrange(1, 13):
            d = datetime.date(year, month, 1)
            if d.weekday() == 6:
                sundays = sundays + 1

    return sundays


########NEW FILE########
__FILENAME__ = euler20
#runas solve(100)
#pythran export solve(int)
def solve(v):
    '''
    Find the sum of digits in 100!
    '''

    def digits(n):
        s = 0
        while n > 0:
            s = s + (n % 10)
            n = n / 10
        return s

    n = 1L
    for i in xrange(1,v): n = n*i
    return digits(n)


########NEW FILE########
__FILENAME__ = euler21
#runas solve(10000)
#pythran export solve(int)
'''
 Let d(n) be defined as the sum of proper divisors of n (numbers less than n which divide evenly into n).
 If d(a) = b and d(b) = a, where a  b, then a and b are an amicable pair and each of a and b are called amicable numbers.

 For example, the proper divisors of 220 are 1, 2, 4, 5, 10, 11, 20, 22, 44, 55 and 110; therefore d(220) = 284. The proper divisors of 284 are 1, 2, 4, 71 and 142; so d(284) = 220.

 Evaluate the sum of all the amicable numbers under 10000.
'''

def divisors(n): return list(i for i in xrange(1, n/2+1) if n % i == 0)
def solve(m):
	pair = dict( ((n, sum(divisors(n))) for n in xrange(1, m)) )
	return sum(n for n in xrange(1, m) if pair.get(pair[n], 0) == n and pair[n] != n)

########NEW FILE########
__FILENAME__ = euler22
#runas solve()
#pythran export solve()
'''
 Using names.txt (right click and 'Save Link/Target As...'), a 46K text file containing over five-thousand first names, begin by sorting it into alphabetical order. Then working out the alphabetical value for each name, multiply this value by its alphabetical position in the list to obtain a name score.

 For example, when the list is sorted into alphabetical order, COLIN, which is worth 3 + 15 + 12 + 9 + 14 = 53, is the 938th name in the list. So, COLIN would obtain a score of 938 x 53 = 49714.

 What is the total of all the name scores in the file?
 '''


def worth(name):
	return sum(ord(letter) - ord('A') + 1 for letter in name)
def solve():
 names = open('euler/names22.txt').read().replace('"', '').split(',')
 names.sort()

 return sum((i+1) * worth(names[i]) for i in xrange(0, len(names)))

########NEW FILE########
__FILENAME__ = euler23
#runas solve()
#unittest.skip recursive generators
#pythran export solve()
'''
 A perfect number is a number for which the sum of its proper divisors is exactly equal to the number. For example, the sum of the proper divisors of 28 would be 1 + 2 + 4 + 7 + 14 = 28, which means that 28 is a perfect number.

 A number whose proper divisors are less than the number is called deficient and a number whose proper divisors exceed the number is called abundant.

 As 12 is the smallest abundant number, 1 + 2 + 3 + 4 + 6 = 16, the smallest number that can be written as the sum of two abundant numbers is 24. By mathematical analysis, it can be shown that all integers greater than 28123 can be written as the sum of two abundant numbers. However, this upper limit cannot be reduced any further by analysis even though it is known that the greatest number that cannot be expressed as the sum of two abundant numbers is less than this limit.

 Find the sum of all the positive integers which cannot be written as the sum of two abundant numbers.
 '''

def solve():
    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)
    lastn      = prime_list[-1]
    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def factors(n):
        ''' Returns a prime factors of n as a list '''
        _refresh(n)
        x, xp, f = 0, prime_list[0], []
        while xp <= n:
            if not n % xp:
                f.append(xp)
                n = n / xp
            else:
                x = x + 1
                xp = prime_list[x]
        return f

    def all_factors(n):
        ''' Returns all factors of n, including 1 and n '''
        f = factors(n)
        elts = sorted(set(f))
        numelts = len(elts)
        def gen_inner(i):
            if i >= numelts:
                yield 1
                return
            thiselt = elts[i]
            thismax = f.count(thiselt)
            powers = [1]
            for j in xrange(thismax):
                powers.append(powers[-1] * thiselt)
            for d in gen_inner(i+1):
                for prime_power in powers:
                    yield prime_power * d
        for d in gen_inner(0):
            yield d

    MAX = 28124
    _refresh(MAX/2)
    abundants = [n for n in xrange(1, MAX) if sum(all_factors(n)) > n+n]
    abundants_dict = dict.fromkeys(abundants, 1)

    total = 0
    for n in xrange(1, MAX):
        sum_of_abundants = 0
        for a in abundants:
            if a > n: break
            if abundants_dict.get(n - a):
                sum_of_abundants = 1
                break
            if not sum_of_abundants:
                total = total + n

    return total

########NEW FILE########
__FILENAME__ = euler24
#runas solve(1000000)
#pythran export solve(int)
'''
A permutation is an ordered arrangement of objects. For example, 3124 is one possible permutation of the digits 1, 2, 3 and 4. If all of the permutations are listed numerically or alphabetically, we call it lexicographic order. The lexicographic permutations of 0, 1 and 2 are:

012   021   102   120   201   210

What is the millionth lexicographic permutation of the digits 0, 1, 2, 3, 4, 5, 6, 7, 8 and 9?
'''

def fact(n):
     f = 1
     for x in xrange(1, n+1): f = f * x
     return f

def permutation(orig_nums, n):
     nums = list(orig_nums)
     perm = []
     while len(nums):
         divider = fact(len(nums)-1)
         pos = n / divider
         n = n % divider
         perm.append(nums[pos])
         nums = nums[0:pos] + nums[pos+1:]
     return perm

def solve(perm):
  return ''.join(str(x) for x in permutation(range(0,10), perm - 1))

########NEW FILE########
__FILENAME__ = euler25
#runas solve(1000)
#pythran export solve(int)
'''
What is the first term in the Fibonacci sequence to contain 1000 digits
'''

import math
def solve(digit):
 phi = (1 + pow(5, 0.5)) / 2
 c = math.log10(5) / 2
 logphi = math.log10(phi)
 n = 1
 while True:
     if n * logphi - c >= digit - 1:
         return n
         break
     n = n + 1

########NEW FILE########
__FILENAME__ = euler26
#runas solve(1000)
#pythran export solve(int)
'''
Find the value of d < 1000 for which 1 / d contains the longest recurring cycle
'''

def cycle_length(n):
    i = 1
    if n % 2 == 0: return cycle_length(n / 2)
    if n % 5 == 0: return cycle_length(n / 5)
    while True:
        if (pow(10L, i) - 1) % n == 0: return i
        else: i = i + 1

def solve(v):
 m = 0
 n = 0
 for d in xrange(1,v):
     c = cycle_length(d)
     if c > m:
         m = c
         n = d

 return n

########NEW FILE########
__FILENAME__ = euler27
#runas solve(1000)
#pythran export solve(int)
'''
Euler published the remarkable quadratic formula:

n^2 + n + 41

It turns out that the formula will produce 40 primes for the consecutive values n = 0 to 39. However, when n = 40, 402 + 40 + 41 = 40(40 + 1) + 41 is divisible by 41, and certainly when n = 41, 41^2 + 41 + 41 is clearly divisible by 41.

Using computers, the incredible formula  n^2 - 79n + 1601 was discovered, which produces 80 primes for the consecutive values n = 0 to 79. The product of the coefficients, -79 and 1601, is -126479.

Considering quadratics of the form:

n^2 + an + b, where |a| <= 1000 and |b| <= 1000

where |n| is the modulus/absolute value of n
e.g. |11| = 11 and |4| = 4
Find the product of the coefficients, a and b, for the quadratic expression that produces the maximum number of primes for consecutive values of n, starting with n = 0.

'''

def solve(edge):
 prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
 prime_dict = dict.fromkeys(prime_list, 1)

 def _isprime(n):
     ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
     isprime = n >= 2 and 1 or 0
     for prime in prime_list:                    # Check for factors with all primes
         if prime * prime > n: break             # ... up to sqrt(n)
         if not n % prime:
             isprime = 0
             break
     if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
     return isprime

 def _refresh(x):
     ''' Refreshes primes upto x '''
     lastn = prime_list[-1]
     while lastn <= x:                           # Keep working until we've got up to x
         lastn = lastn + 1                       # Check the next number
         if _isprime(lastn):
             prime_list.append(lastn)            # Maintain a list for sequential access

 def prime(x):
     ''' Returns the xth prime '''

     lastn = prime_list[-1]
     while len(prime_list) <= x:                 # Keep working until we've got the xth prime
         lastn = lastn + 1                       # Check the next number
         if _isprime(lastn):
             prime_list.append(lastn)            # Maintain a list for sequential access
     return prime_list[x]

 max_pair = (0,0,0)
 for a in xrange(-1 * edge + 1, edge):
     for b in xrange(max(2, 1-a), edge): # b >= 2, a + b + 1 >= 2
         n, count = 0, 0
         while True:
             v = n*n + a*n + b
             _refresh(v)
             if _isprime(v): count = count + 1
             else: break
             n = n + 1
         if count > max_pair[2]:
             max_pair = (a,b,count)

 return max_pair[0] * max_pair[1]

########NEW FILE########
__FILENAME__ = euler28
#runas solve(10001)
#pythran export solve(int)
'''
Starting with the number 1 and moving to the right in a clockwise direction a 5 by 5 spiral is formed as follows:
43                49
    21 22 23 24 25
    20  7  8  9 10
    19  6  1  2 11
    18  5  4  3 12
    17 16 15 14 13
37                31
                    57
1
6*4
19*4
39*4
69*4

It can be verified that the sum of both diagonals is 101.

What is the sum of both diagonals in a 1001 by 1001 spiral formed in the same way?
'''

def solve(size):
 diagonal = 1L
 start = 1
 for width in xrange(3, size + 1, 2):
     increment = width - 1
     count = increment * 4
     diagonal = diagonal + start * 4 + increment * 10
     start = start + count

 return diagonal

########NEW FILE########
__FILENAME__ = euler29
#runas solve(2, 100)
#pythran export solve(int, int)
'''
How many distinct terms are in the sequence generated by ab for 2 <= a <= 100 and 2 <= b <= 100
'''

def solve(start, end):
 terms = {}
 count = 0
 for a in xrange(start, end + 1):
     for b in xrange(start, end + 1):
         c = pow(long(a),b)
         if not terms.get(c, 0):
             terms[c] = 1
             count = count + 1

 return count

########NEW FILE########
__FILENAME__ = euler30
#runas solve(5)
#pythran export solve(int)

'''
Surprisingly there are only three numbers that can be written as the sum of fourth powers of their digits:

1634 = 1^4 + 6^4 + 3^4 + 4^4
8208 = 8^4 + 2^4 + 0^4 + 8^4
9474 = 9^4 + 4^4 + 7^4 + 4^4
As 1 = 1^4 is not a sum it is not included.

The sum of these numbers is 1634 + 8208 + 9474 = 19316.

Find the sum of all the numbers that can be written as the sum of fifth powers of their digits.
'''

def power_of_digits(n, p):
    s = 0
    while n > 0:
        d = n % 10
        n = n / 10
        s = s + pow(d, p)
    return s


def solve(p):
 return sum(n for n in xrange(2, 200000) if power_of_digits(n, p) == n)


########NEW FILE########
__FILENAME__ = euler31
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
def solve():
    '''
    In England the currency is made up of pound, P, and pence, p, and there are eight coins in general circulation:

    1p, 2p, 5p, 10p, 20p, 50p, P1 (100p) and P2 (200p).
    It is possible to make P2 in the following way:

    1 P1 + 1 50p + 2 20p + 1 5p + 1 2p + 3 1p
    How many different ways can P2 be made using any number of coins?
    '''

    coins = [1, 2, 5, 10, 20, 50, 100, 200]

    def balance(pattern): return sum(coins[x]*pattern[x] for x in xrange(0, len(pattern)))

    def gen(pattern, coinnum, num):
        coin = coins[coinnum]
        for p in xrange(0, num/coin + 1):
            newpat = pattern[:coinnum] + (p,)
            bal = balance(newpat)
            if bal > num: return
            elif bal == num: yield newpat
            elif coinnum < len(coins)-1:
                for pat in gen(newpat, coinnum+1, num):
                    yield pat

    return sum(1 for pat in gen((), 0, 200))



########NEW FILE########
__FILENAME__ = euler32
#runas solve()
#unittest.skip recursive generator
#pythran export solve()

''' From O'Reilly's Python Cookbook '''

def _combinators(_handle, items, n):
    if n==0:
        yield []
        return
    for i, item in enumerate(items):
        this_one = [ item ]
        for cc in _combinators(_handle, _handle(items, i), n-1):
            yield this_one + cc

def combinations(items, n):
    ''' take n distinct items, order matters '''
    def skipIthItem(items, i):
        return items[:i] + items[i+1:]
    return _combinators(skipIthItem, items, n)

def uniqueCombinations(items, n):
    ''' take n distinct items, order is irrelevant '''
    def afterIthItem(items, i):
        return items[i+1:]
    return _combinators(afterIthItem, items, n)

def selections(items, n):
    ''' take n (not necessarily distinct) items, order matters '''
    def keepAllItems(items, i):
        return items
    return _combinators(keepAllItems, items, n)

def permutations(items):
    ''' take all items, order matters '''
    return combinations(items, len(items))

def solve():
    '''
    The product 7254 is unusual, as the identity, 39 x 186 = 7254, containing multiplicand, multiplier, and product is 1 through 9 pandigital.

    Find the sum of all products whose multiplicand/multiplier/product identity can be written as a 1 through 9 pandigital.

    HINT: Some products can be obtained in more than one way so be sure to only include it once in your sum.
    '''

    ''' From O'Reilly's Python Cookbook '''


    def num(l):
        s = 0
        for n in l: s = s * 10 + n
        return s

    product = {}
    for perm in permutations(range(1,10)):
        for cross in range(1,4):            # Number can't be more than 4 digits
            for eq in range(cross+1, 6):    # Result can't be less than 4 digits
                a = num(perm[0:cross])
                b = num(perm[cross:eq])
                c = num(perm[eq:9])
                if a * b == c: product[c] = 1

    return sum(p for p in product)


########NEW FILE########
__FILENAME__ = euler33
#runas solve(2)
#pythran export solve(int)
def solve(digit):
    '''
    The fraction 49/98 is a curious fraction, as an inexperienced mathematician in attempting to simplify it may incorrectly believe that 49/98 = 4/8, which is correct, is obtained by cancelling the 9s.

    We shall consider fractions like, 30/50 = 3/5, to be trivial examples.

    There are exactly four non-trivial examples of this type of fraction, less than one in value, and containing two digits in the numerator and denominator.

    If the product of these four fractions is given in its lowest common terms, find the value of the denominator.
    '''

    def fractions():
        for numerator in map(str, xrange(10 ** (digit - 1), 10 ** digit)):
            for denominator in map(str, xrange(int(numerator)+1, 10 ** digit)):
                if numerator == denominator: continue
                if numerator[1] == denominator[1] and numerator[1] == '0': continue
                if numerator[0] == denominator[0] and int(numerator) * int(denominator[1]) == int(denominator) * int(numerator[1]): yield(int(numerator), int(denominator))
                if numerator[0] == denominator[1] and int(numerator) * int(denominator[0]) == int(denominator) * int(numerator[1]): yield(int(numerator), int(denominator))
                if numerator[1] == denominator[1] and int(numerator) * int(denominator[0]) == int(denominator) * int(numerator[0]): yield(int(numerator), int(denominator))
                if numerator[1] == denominator[0] and int(numerator) * int(denominator[1]) == int(denominator) * int(numerator[0]): yield(int(numerator), int(denominator))

    def gcd(a,b): return b and gcd(b, a % b) or a

    numerator = 1
    denominator = 1
    for frac in fractions():
        numerator = numerator * frac[0]
        denominator = denominator * frac[1]

    g = gcd(numerator, denominator)
    return denominator / g


########NEW FILE########
__FILENAME__ = euler34
#runas solve()
#pythran export solve()
def solve():
    '''
    145 is a curious number, as 1! + 4! + 5! = 1 + 24 + 120 = 145.
    
    Find the sum of all numbers which are equal to the sum of the factorial of their digits.
    
    Note: as 1! = 1 and 2! = 2 are not sums they are not included.
    '''

    fact = [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880]

    def sum_of_digits_factorial(n):
        s = 0
        while n > 0:
            d = n % 10
            s = s + fact[d]
            n = n / 10
        return s

    return sum(n for n in xrange(10, 100000) if n == sum_of_digits_factorial(n))

########NEW FILE########
__FILENAME__ = euler35
#runas solve(1000000)
#pythran export solve(int)
def solve(a):
    '''
    The number, 197, is called a circular prime because all rotations of the digits: 197, 971, and 719, are themselves prime.
    
    There are thirteen such primes below 100: 2, 3, 5, 7, 11, 13, 17, 31, 37, 71, 73, 79, and 97.
    
    How many circular primes are there below one million?
    '''

    sieve = [True] * a
    sieve[0] = sieve[1] = False

    def mark(sieve, x):
        for i in xrange(x+x, len(sieve), x):
            sieve[i] = False

    for x in xrange(2, int(len(sieve) ** 0.5) + 1):
        mark(sieve, x)

    def circular(n):
        digits = []
        while n > 0:
            digits.insert(0, str(n % 10))
            n = n / 10
        for d in xrange(1, len(digits)):
            yield int(''.join(digits[d:] + digits[0:d]))

    count = 0
    for n, p in enumerate(sieve):
        if p:
            iscircularprime = 1
            for m in circular(n):
                if not sieve[m]:
                    iscircularprime = 0
                    break
            if iscircularprime:
                count = count + 1

    return count

########NEW FILE########
__FILENAME__ = euler36
#runas solve()
#pythran export solve()
def solve():
    '''
    The decimal number, 585 = 10010010012 (binary), is palindromic in both bases.
    
    Find the sum of all numbers, less than one million, which are palindromic in base 10 and base 2.
    
    (Please note that the palindromic number, in either base, may not include leading zeros.)
    '''

    def ispalindrome(n, base):
        digits = []
        reverse = []
        while n > 0:
            d = str(n % base)
            digits.append(d)
            reverse.insert(0, d)
            n = n / base
        return digits == reverse

    return sum(n for n in xrange(1, 1000000) if ispalindrome(n, 10) and ispalindrome(n, 2))


########NEW FILE########
__FILENAME__ = euler37
#runas solve()
#pythran export solve()
def solve():
    '''
    The number 3797 has an interesting property. Being prime itself, it is possible to continuously remove digits from left to right, and remain prime at each stage: 3797, 797, 97, and 7. Similarly we can work from right to left: 3797, 379, 37, and 3.
    
    Find the sum of the only eleven primes that are both truncatable from left to right and right to left.
    
    NOTE: 2, 3, 5, and 7 are not considered to be truncatable primes.
    '''

    import math

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def prime(x):
        ''' Returns the xth prime '''

        lastn = prime_list[-1]
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    digits = range(0, 10)
    prime_digits = (2, 3, 5, 7)


    def num(l):
        s = 0
        for n in l: s = s * 10 + n
        return s

    def is_left_truncatable(l):
        is_truncatable = 1
        for size in xrange(1, len(l)+1):
            n = num(l[:size])
            _refresh(int(math.sqrt(n)))
            if not _isprime(n):
                is_truncatable = 0
                break
        return is_truncatable

    def is_right_truncatable(l):
        is_truncatable = 1
        for size in xrange(0, len(l)):
            n = num(l[size:])
            _refresh(int(math.sqrt(n)))
            if not _isprime(n):
                is_truncatable = 0
                break
        return is_truncatable

    def gen(result, number):
        if len(number) > 6: return
        number = list(number)
        number.append(0)
        for digit in digits:
            number[-1] = digit
            if is_left_truncatable(number):
                if is_right_truncatable(number) and len(number) > 1:
                    result.append(num(number))
                gen(result, number)

    result = []
    gen(result, [])
    return sum(result)


########NEW FILE########
__FILENAME__ = euler38
#runas solve()
#pythran export solve()
def solve():
    '''
    Take the number 192 and multiply it by each of 1, 2, and 3:
    
    192 x 1 = 192
    192 x 2 = 384
    192 x 3 = 576
    By concatenating each product we get the 1 to 9 pandigital, 192384576. We will call 192384576 the concatenated product of 192 and (1,2,3)
    
    The same can be achieved by starting with 9 and multiplying by 1, 2, 3, 4, and 5, giving the pandigital, 918273645, which is the concatenated product of 9 and (1,2,3,4,5).
    
    What is the largest 1 to 9 pandigital 9-digit number that can be formed as the concatenated product of an integer with (1,2, ... , n) where n > 1?
    '''

    def get_pandigital(n):
        pandigital = ''
        for x in xrange(1, 10):
            pandigital += str(x * n)
            if len(pandigital) >= 9: break
        if len(pandigital) == 9 and sorted(dict.fromkeys(list(pandigital)).keys()) == list("123456789"): return pandigital
        else: return ''

    max = ''
    for n in xrange(1, 10000):
        p = get_pandigital(n)
        if p and p > max: max = p

    return max


########NEW FILE########
__FILENAME__ = euler39
#runas solve(1000)
#pythran export solve(int)
def solve(n):
    '''
    If p is the perimeter of a right angle triangle with integral length sides, {a,b,c}, there are exactly three solutions for p = 120.
    
    {20,48,52}, {24,45,51}, {30,40,50}
    
    For which value of p < 1000, is the number of solutions maximised?
    '''

    maxp, maxsol = 0, 0
    for p in xrange(12, n + 1, 2):
        solutions = 0
        # a < b < c. So a is at most 1/3 of p. b is between a and (p-a)/2
        for a in xrange(1, p/3):
            a2 = a*a
            for b in xrange(a, (p-a)/2):
                c = p - a - b
                if a2 + b*b == c*c: solutions = solutions + 1
        if solutions > maxsol: maxp, maxsol = p, solutions

    return maxp

########NEW FILE########
__FILENAME__ = euler40
#runas solve()
#pythran export solve()
def solve():
    '''
    An irrational decimal fraction is created by concatenating the positive integers:
    
    0.123456789101112131415161718192021...
    
    It can be seen that the 12th digit of the fractional part is 1.
    
    If dn represents the nth digit of the fractional part, find the value of the following expression.
    
    d1 x d10 x d100 x d1000 x d10000 x d100000 x d1000000
    
    0 digit < 1
    1 digit < + 9 * 1           10
    2 digit < + 90 * 2          190
    3 digit < + 900 * 3         2890
    4 digit < + 9000 * 4
    5 digit < + 90000 * 5
    '''

    def digit_at(n):
        digits = 1
        n = n - 1
        while True:
            numbers = 9 * pow(10L, digits-1) * digits
            if n > numbers: n = n - numbers
            else: break
            digits = digits + 1
        num = n / digits + pow(10L, digits-1)
        return int(str(num)[n % digits])

    return digit_at(1) * digit_at(10) * digit_at(100) * digit_at(1000) * digit_at(10000) * digit_at(100000) * digit_at(1000000)


########NEW FILE########
__FILENAME__ = euler41
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
''' From O'Reilly's Python Cookbook '''

def _combinators(_handle, items, n):
    if n==0:
        yield []
        return
    for i, item in enumerate(items):
        this_one = [ item ]
        for cc in _combinators(_handle, _handle(items, i), n-1):
            yield this_one + cc

def combinations(items, n):
    ''' take n distinct items, order matters '''
    def skipIthItem(items, i):
        return items[:i] + items[i+1:]
    return _combinators(skipIthItem, items, n)

def uniqueCombinations(items, n):
    ''' take n distinct items, order is irrelevant '''
    def afterIthItem(items, i):
        return items[i+1:]
    return _combinators(afterIthItem, items, n)

def selections(items, n):
    ''' take n (not necessarily distinct) items, order matters '''
    def keepAllItems(items, i):
        return items
    return _combinators(keepAllItems, items, n)

def permutations(items):
    ''' take all items, order matters '''
    return combinations(items, len(items))
def solve():
    '''
    We shall say that an n-digit number is pandigital if it makes use of all the digits 1 to n exactly once. For example, 2143 is a 4-digit pandigital and is also prime.
    
    What is the largest n-digit pandigital prime that exists?
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access



    # Pan-digital primes are 4 or 7 digits. Others divisible by 3
    _refresh(2766)    # sqrt(7654321)
    for perm in permutations(range(7, 0, -1)):
        num = 0
        for n in perm: num = num * 10 + n
        if _isprime(num):
            return num
            break


########NEW FILE########
__FILENAME__ = euler42
#runas solve()
#pythran export solve()
def solve():
    '''
    The nth term of the sequence of triangle numbers is given by, t_n = 1/2 x n(n+1); so the first ten triangle numbers are:
    
    1, 3, 6, 10, 15, 21, 28, 36, 45, 55, ...
    
    By converting each letter in a word to a number corresponding to its alphabetical position and adding these values we form a word value. For example, the word value for SKY is 19 + 11 + 25 = 55 = t_10. If the word value is a triangle number then we shall call the word a triangle word.
    
    Using words.txt (right click and 'Save Link/Target As...'), a 16K text file containing nearly two-thousand common English words, how many are triangle words?
    
    '''
    def worth(word): return sum(ord(letter) - ord('A') + 1 for letter in word)

    words = open('euler/words42.txt').read().replace('"', '').split(',')
    triangle_numbers = dict.fromkeys(list(n*(n+1)/2 for n in xrange(1, 100)), 1)

    return sum(1 for word in words if worth(word) in triangle_numbers)


########NEW FILE########
__FILENAME__ = euler43
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
def solve():
    '''
    The number, 1406357289, is a 0 to 9 pandigital number because it is made up of each of the digits 0 to 9 in some order, but it also has a rather interesting sub-string divisibility property.
    
    Let d1 be the 1st digit, d2 be the 2nd digit, and so on. In this way, we note the following:
    
    d2 d3 d4 = 406 is divisible by 2
    d3 d4 d5 = 063 is divisible by 3
    d4 d5 d6 = 635 is divisible by 5
    d5 d6 d7 = 357 is divisible by 7
    d6 d7 d8 = 572 is divisible by 11
    d7 d8 d9 = 728 is divisible by 13
    d8 d9 d10= 289 is divisible by 17
    
    Find the sum of all 0 to 9 pandigital numbers with this property.
    '''

    def _combinators(_handle, items, n):
        if n==0:
            yield []
            return
        for i, item in enumerate(items):
            this_one = [ item ]
            for cc in _combinators(_handle, _handle(items, i), n-1):
                yield this_one + cc

    def combinations(items, n):
        ''' take n distinct items, order matters '''
        def skipIthItem(items, i):
            return items[:i] + items[i+1:]
        return _combinators(skipIthItem, items, n)

    def permutations(items):
        ''' take all items, order matters '''
        return combinations(items, len(items))

    def num(l):
        s = 0
        for n in l: s = s * 10 + n
        return s

    def subdiv(l, n): return num(l) % n == 0

    total = 0
    for perm in permutations((0,1,2,3,4,6,7,8,9)):
        perm.insert(5, 5)               # d6 must be 5
        if (subdiv(perm[7:10], 17) and
            subdiv(perm[6:9],  13) and
            subdiv(perm[5:8],  11) and
            subdiv(perm[4:7],   7) and
            subdiv(perm[3:6],   5) and
            subdiv(perm[2:5],   3) and
            subdiv(perm[1:4],   2)):
                total += num(perm)

    return total


########NEW FILE########
__FILENAME__ = euler44
#runas solve()
#pythran export solve()
def solve():
    '''
    Pentagonal numbers are generated by the formula, P_n=n(3n-1)/2. The first ten pentagonal numbers are:
    
    1, 5, 12, 22, 35, 51, 70, 92, 117, 145, ...
    
    It can be seen that P_4 + P_7 = 22 + 70 = 92 = P_8. However, their difference, 70 - 22 = 48, is not pentagonal.
    
    Find the pair of pentagonal numbers, P_j and P_k, for which their sum and difference is pentagonal and D = |P_k - P_j| is minimised; what is the value of D?
    '''

    MAX = 2000
    pent = [ n * (3*n - 1) / 2 for n in xrange(1, 2*MAX) ]
    pdic = dict.fromkeys(pent)

    def main2():
        for j in xrange(0, MAX):
            for k in xrange(j+1, 2*MAX-1):
                p_j = pent[j]
                p_k = pent[k]
                p_sum = p_j + p_k
                p_diff = p_k - p_j
                if pdic.has_key(p_sum) and pdic.has_key(p_diff):
                    return p_diff

    return main2()


########NEW FILE########
__FILENAME__ = euler45
#runas solve()
#pythran export solve()
def solve():
    '''
    Triangle, pentagonal, and hexagonal numbers are generated by the following formulae:
    
    Triangle        T_n=n(n+1)/2        1, 3, 6, 10, 15, ...
    Pentagonal      P_n=n(3n-1)/2       1, 5, 12, 22, 35, ...
    Hexagonal       H_n=n(2n-1)         1, 6, 15, 28, 45, ...
    
    It can be verified that T_285 = P_165 = H_143 = 40755.
    
    Find the next triangle number that is also pentagonal and hexagonal.
    '''

    MAX = 100000
    triangle = [ n * (  n + 1) / 2 for n in xrange(0, MAX) ]
    pentagon = [ n * (3*n - 1) / 2 for n in xrange(0, MAX) ]
    hexagon  = [ n * (2*n - 1)     for n in xrange(0, MAX) ]
    pentagon_dict = dict.fromkeys(pentagon, 1)
    hexagon_dict  = dict.fromkeys(hexagon, 1)

    for t in xrange(286, MAX):
        v = triangle[t]
        if pentagon_dict.has_key(v) and hexagon_dict.has_key(v):
            return v
            break


########NEW FILE########
__FILENAME__ = euler46
#runas solve()
#pythran export solve()
def solve():
    '''
    It was proposed by Christian Goldbach that every odd composite number can be written as the sum of a prime and twice a square.
    
     9 =  7 + 2 x 1^2
    15 =  7 + 2 x 2^2
    21 =  3 + 2 x 3^2
    25 =  7 + 2 x 3^2
    27 = 19 + 2 x 2^2
    33 = 31 + 2 x 1^2
    It turns out that the conjecture was false.
    
    What is the smallest odd composite that cannot be written as the sum of a prime and twice a square?
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def prime(x):
        ''' Returns the xth prime '''

        lastn = prime_list[-1]
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    MAX = 10000
    squares = dict.fromkeys((x*x for x in xrange(1, MAX)), 1)
    _refresh(MAX)

    for x in xrange(35, MAX, 2):
        if not _isprime(x):
            is_goldbach = 0
            for p in prime_list[1:]:
                if p >= x: break
                if squares.has_key((x - p)/2):
                    is_goldbach = 1
                    break
            if not is_goldbach:
                return x
                break


########NEW FILE########
__FILENAME__ = euler47
#runas solve()
#pythran export solve()
def solve():
    '''
    Find the first four consecutive integers to have four distinct prime factors
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
            break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime
    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def primes_factors(n):
        ''' Returns a prime factors of n as a list '''
        _refresh(n)
        x, xp, f = 0, prime_list[0], []
        while xp <= n:
            if not n % xp:
                f.append(xp)
                n = n / xp
            else:
                x = x + 1
                xp = prime_list[x]
        return f

    def distinct_factors(n): return len(dict.fromkeys(primes_factors(n)).keys())

    factors = [0, 1, distinct_factors(2), distinct_factors(3)]
    while True:
        if factors[-4::] == [4,4,4,4]: break
        else: factors.append(distinct_factors(len(factors)))

    return len(factors)-4


########NEW FILE########
__FILENAME__ = euler48
#runas solve()
#pythran export solve()
def solve():
    '''
    Find the last ten digits of the series, 1^1 + 2^2 + 3^3 + ... + 1000^1000.
    '''

    s = 0L
    mod = pow(10, 10)
    for x in xrange(1, 1001):
        s = s + pow(long(x), x)

    return s % mod


########NEW FILE########
__FILENAME__ = euler49
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
def solve():
    '''
    The arithmetic sequence, 1487, 4817, 8147, in which each of the terms increases by 3330, is unusual in two ways: (i) each of the three terms are prime, and, (ii) each of the 4-digit numbers are permutations of one another.
    
    There are no arithmetic sequences made up of three 1-, 2-, or 3-digit primes, exhibiting this property, but there is one other 4-digit increasing sequence.
    
    What 12-digit number do you form by concatenating the three terms in this sequence?
    
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)
    lastn      = prime_list[-1]

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn) 
    def isprime(x):
        ''' Returns 1 if x is prime, 0 if not. Uses a pre-computed dictionary '''
        _refresh(x)                                 # Compute primes up to x (which is a bit wasteful)
        return prime_dict.get(x, 0) 
    
    def _combinators(_handle, items, n):
        if n==0:
            yield []
            return
        for i, item in enumerate(items):
            this_one = [ item ]
            for cc in _combinators(_handle, _handle(items, i), n-1):
                yield this_one + cc

    def combinations(items, n):
        ''' take n distinct items, order matters '''
        def skipIthItem(items, i):
            return items[:i] + items[i+1:]
        return _combinators(skipIthItem, items, n)

    def permutations(items):
        ''' take all items, order matters '''
        return combinations(items, len(items))
    
    _refresh(10000)
    for num in xrange(1000, 10000):
        if str(num).find('0') >= 0: continue
    
        if isprime(num):
            prime_permutations = { num: 1 }
            for x in permutations(list(str(num))):
                next_num = int(''.join(x))
                if isprime(next_num):
                    prime_permutations[next_num] = 1
    
            primes = sorted(prime_permutations.keys())
            for a in xrange(0, len(primes)):
                if primes[a] == 1487: continue
                for b in xrange(a+1, len(primes)):
                    c = (primes[a] + primes[b]) / 2
                    if prime_permutations.has_key(c):
                        return str(primes[a]) + str(c) + str(primes[b])
                        exit()


########NEW FILE########
__FILENAME__ = euler50
#runas solve(1000000)
#pythran export solve(int)
def solve(m):
    '''
    The prime 41, can be written as the sum of six consecutive primes:
    
    41 = 2 + 3 + 5 + 7 + 11 + 13
    This is the longest sum of consecutive primes that adds to a prime below one-hundred.
    
    The longest sum of consecutive primes below one-thousand that adds to a prime, contains 21 terms, and is equal to 953.
    
    Which prime, below one-million, can be written as the sum of the most consecutive primes?
    '''
    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)
    lastn      = prime_list[-1]
    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        lastn      = prime_list[-1]
        ''' Refreshes primes upto x '''
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def prime(x):
        ''' Returns the xth prime '''
        lastn      = prime_list[-1]
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    def isprime(x):
        ''' Returns 1 if x is prime, 0 if not. Uses a pre-computed dictionary '''
        _refresh(x)                                 # Compute primes up to x (which is a bit wasteful)
        return prime_dict.get(x, 0)

    MAX = 5000
    prime(MAX)

    def check_length(n, below):
        maxprime = 0
        for x in xrange(0, below):
            total = sum(prime_list[x:x+n])
            if total > below: break
            if isprime(total): maxprime = total
        return maxprime

    for n in xrange(1000, 0, -1):
        maxprime = check_length(n, m)
        if maxprime:
            return maxprime
            break


########NEW FILE########
__FILENAME__ = euler51
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
def solve():
    '''
    By replacing the 1st digit of *57, it turns out that six of the possible values: 157, 257, 457, 557, 757, and 857, are all prime.
    
    By replacing the 3rd and 4th digits of 56**3 with the same digit, this 5-digit number is the first example having seven primes, yielding the family: 56003, 56113, 56333, 56443, 56663, 56773, and 56993. Consequently 56003, being the first member of this family, is the smallest prime with this property.
    
    Find the smallest prime which, by replacing part of the number (not necessarily adjacent digits) with the same digit, is part of an eight prime value family.
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)
    lastn      = prime_list[-1]

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    def prime(x):
        ''' Returns the xth prime '''
        while len(prime_list) <= x:                 # Keep working until we've got the xth prime
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access
        return prime_list[x]

    def isprime(x):
        ''' Returns 1 if x is prime, 0 if not. Uses a pre-computed dictionary '''
        _refresh(x)                                 # Compute primes up to x (which is a bit wasteful)
        return prime_dict.get(x, 0)

    def _combinators(_handle, items, n):
        if n==0:
            yield []
            return
        for i, item in enumerate(items):
            this_one = [ item ]
            for cc in _combinators(_handle, _handle(items, i), n-1):
                yield this_one + cc

    def uniqueCombinations(items, n):
        ''' take n distinct items, order is irrelevant '''
        def afterIthItem(items, i):
            return items[i+1:]
        return _combinators(afterIthItem, items, n)

    cache = {}
    def prime_family_length(n, digits):
        if cache.has_key((n, digits)): return cache[n, digits]

        num, nums, count = list(str(n)), [], 0
        if len(dict.fromkeys(num[d] for d in digits).keys()) > 1:
            return cache.setdefault((n, digits), 0)                                # The digits must have the same number

        for d in range(0 in digits and 1 or 0, 10):                                 # Ensure 0 is not the first digit
            for x in digits: num[x] = str(d)
            n = int(''.join(num))
            if prime.isprime(n): count += 1
            nums.append(n)
        for n in nums: cache[n, digits] = count
        return count

    prime._refresh(100000)

    n, max, max_count, combos = 10, 0, 0, {}
    while max_count < 8:
        p = prime.prime(n)
        digits = range(0, len(str(p)))
        for size in xrange(1, len(digits)):
            patterns = combos.setdefault((len(digits), size),
                tuple(tuple(sorted(p)) for p in uniqueCombinations(digits, size)))
            for pat in patterns:
                count = prime_family_length(p, pat)
                if count > max_count: max, max_count = p, count
        n += 1

    return p

########NEW FILE########
__FILENAME__ = euler52
#runas solve()
#pythran export solve()
def solve():
    '''
    It can be seen that the number, 125874, and its double, 251748, contain exactly the same digits, but in a different order.
    
    Find the smallest positive integer, x, such that 2x, 3x, 4x, 5x, and 6x, contain the same digits.
    '''

    def multiples_have_same_digits(n):
        digit_keys = dict.fromkeys(list(str(n)))
        for x in xrange(2, 4):
            for d in list(str(x * n)):
                if not digit_keys.has_key(d): return False
        return True

    n = 0
    while True:
        n = n + 9                           # n must be a multiple of 9 for this to happen
        if multiples_have_same_digits(n):
            return n
            break


########NEW FILE########
__FILENAME__ = euler53
#runas solve(1000000)
#pythran export solve(int)
def solve(m):
    '''
    There are exactly ten ways of selecting three from five, 12345:
    
    123, 124, 125, 134, 135, 145, 234, 235, 245, and 345
    
    In combinatorics, we use the notation, 5C3 = 10.
    
    In general,
    
    nCr = n! / r!(nr)! where r <= n, n! = n x (n-1)...x 3 x 2 x 1, and 0! = 1.
    
    It is not until n = 23, that a value exceeds one-million: 23C10 = 1144066.
    
    How many, not necessarily distinct, values of  nCr, for 1 <= n <= 100, are greater than one-million?
    '''

    fact_c = { 0: 1L, 1: 1L }
    def fact(n): return fact_c.has_key(n) and fact_c[n] or fact_c.setdefault(n, n * fact(n-1))

    count = 0
    for n in xrange(1, 101):
        for r in xrange(0, n):
            ncr = fact(n) / fact(r) / fact(n-r)
            if ncr > m: count += 1
    return count


########NEW FILE########
__FILENAME__ = euler54
#runas solve()
#unittest.skip type can't be deducte
#pythran export solve()
def solve():
    '''
    In the card game poker, a hand consists of five cards and are ranked, from lowest to highest, in the following way:
    
    High Card: Highest value card.
    One Pair: Two cards of the same value.
    Two Pairs: Two different pairs.
    Three of a Kind: Three cards of the same value.
    Straight: All cards are consecutive values.
    Flush: All cards of the same suit.
    Full House: Three of a kind and a pair.
    Four of a Kind: Four cards of the same value.
    Straight Flush: All cards are consecutive values of same suit.
    Royal Flush: Ten, Jack, Queen, King, Ace, in same suit.
    The cards are valued in the order:
    2, 3, 4, 5, 6, 7, 8, 9, 10, Jack, Queen, King, Ace.
    
    If two players have the same ranked hands then the rank made up of the highest value wins; for example, a pair of eights beats a pair of fives (see example 1 below). But if two ranks tie, for example, both players have a pair of queens, then highest cards in each hand are compared (see example 4 below); if the highest cards tie then the next highest cards are compared, and so on.
    
    Consider the following five hands dealt to two players:
    
    Hand        Player 1            Player 2          Winner
    1       5H 5C 6S 7S KD      2C 3S 8S 8D TD      Player 2
            Pair of Fives       Pair of Eights
    
    2       5D 8C 9S JS AC      2C 5C 7D 8S QH      Player 1
            Highest card Ace    Highest card Queen
    
    3       2D 9C AS AH AC      3D 6D 7D TD QD      Player 2
            Three Aces          Flush with Diamonds
    
    4       4D 6S 9H QH QC      3D 6D 7H QD QS      Player 1
            Pair of Queens      Pair of Queens
            Highest card Nine   Highest card Seven
    
    5       2H 2D 4C 4D 4S      3C 3D 3S 9S 9D      Player 1
            Full House          Full House
            With Three Fours    with Three Threes
    
    The file, poker.txt, contains one-thousand random hands dealt to two players. Each line of the file contains ten cards (separated by a single space): the first five are Player 1's cards and the last five are Player 2's cards. You can assume that all hands are valid (no invalid characters or repeated cards), each player's hand is in no specific order, and in each hand there is a clear winner.
    
    How many hands does Player 1 win?
    '''
    
    value = { '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14 }
    all_kinds = tuple(reversed(sorted(value.values())))
    all_suits = list('DCSH')
    
    def make_hand(cards):
        hand = {}
        for card in cards:
            hand.setdefault(value[card[0]], {})[card[1]] = 1
            hand.setdefault(card[1], {})[value[card[0]]] = 1
        return hand
    
    def get(hash, arr): return ((i, hash.get(i, {})) for i in arr)
    def has(hash, arr): return not sum(1 for i in arr if i not in hash)
    
    def rank(hand):
        # Royal flush
        for suit, kinds in get(hand, all_suits):
            if has(kinds, tuple('TJQKA')):
                return (9,0,0)
    
        # Straight flush
        for suit, kinds in get(hand, all_suits):
            kinds = sorted(kind for kind in kinds.keys())
            if len(kinds) == 5 and kinds[4] - kinds[0] == 4:
                return (8, kinds[0],0)
    
        # Four of a kind
        for kind, suits in get(hand, all_kinds):
            if len(suits.keys()) == 4:
                return (7, kind,0)
    
        # Full house
        for kind, suits in get(hand, all_kinds):
            if len(suits.keys()) == 3:
                for kind2, suits2 in get(hand, all_kinds):
                    if len(suits2.keys()) == 2:
                        return (6, kind, kind2)
    
        # Flush
        for suit, kinds in get(hand, all_suits):
            if len(kinds.keys()) == 5:
                return (5,0,0)
    
        # Straight
        kinds = sorted(kind for kind in all_kinds if hand.has_key(kind))
        if len(kinds) == 5 and kinds[4] - kinds[0] == 4:
            return (4, kinds[0],0)
    
        # Three of a kind
        for kind, suits in get(hand, all_kinds):
            if len(suits.keys()) == 3:
                return (3, kind,0)
    
        # Two pairs
        for kind, suits in get(hand, all_kinds):
            if len(suits.keys()) == 2:
                for kind2, suits2 in get(hand, all_kinds):
                    if kind != kind2 and len(suits2.keys()) == 2:
                        return (2, kind, kind2)
    
        # One pair
        for kind, suits in get(hand, all_kinds):
            if len(suits.keys()) == 2:
                return (1, kind,0)
    
        for kind in all_kinds:
            if kind in hand:
                return (0, kind,0)
    
        return (0,0,0)
    
    
    count = 0
    for hand in open('poker.txt'):
        hands = hand.split(' ')
        p1, p2 = make_hand(hands[0:5]), make_hand(hands[5:10])
        v1, v2 = rank(p1), rank(p2)
        if v1 > v2: count += 1
    return count


########NEW FILE########
__FILENAME__ = euler55
#runas solve(10000)
#pythran export solve(int)
def solve(e):
    '''
    If we take 47, reverse and add, 47 + 74 = 121, which is palindromic.
    
    Not all numbers produce palindromes so quickly. For example,
    
    349 + 943 = 1292,
    1292 + 2921 = 4213
    4213 + 3124 = 7337
    
    That is, 349 took three iterations to arrive at a palindrome.
    
    Although no one has proved it yet, it is thought that some numbers, like 196, never produce a palindrome. A number that never forms a palindrome through the reverse and add process is called a Lychrel number. Due to the theoretical nature of these numbers, and for the purpose of this problem, we shall assume that a number is Lychrel until proven otherwise. In addition you are given that for every number below ten-thousand, it will either (i) become a palindrome in less than fifty iterations, or, (ii) no one, with all the computing power that exists, has managed so far to map it to a palindrome. In fact, 10677 is the first number to be shown to require over fifty iterations before producing a palindrome: 4668731596684224866951378664 (53 iterations, 28-digits).
    
    Surprisingly, there are palindromic numbers that are themselves Lychrel numbers; the first example is 4994.
    
    How many Lychrel numbers are there below ten-thousand?
    
    NOTE: Wording was modified slightly on 24 April 2007 to emphasise the theoretical nature of Lychrel numbers.
    '''

    def is_lychrel(n):
        #n = str(n)
        for count in xrange(0, 50):
            n = str(int(n) + int(n[::-1]))
            if n == n[::-1]: return False
        return True

    return sum(1 for n in xrange(0, e) if is_lychrel(str(n)))


########NEW FILE########
__FILENAME__ = euler56
#runas solve()
#pythran export solve()
def solve():
    '''
    A googol (10^100) is a massive number: one followed by one-hundred zeros; 100^100 is almost unimaginably large: one followed by two-hundred zeros. Despite their size, the sum of the digits in each number is only 1.
    
    Considering natural numbers of the form, a^b, where a, b < 100, what is the maximum digital sum?
    '''

    max = 0
    for a in xrange(0, 100):
        for b in xrange(0, 100):
            ds = sum(int(digit) for digit in str(long(a)**b))
            if ds > max: max = ds
    return max


########NEW FILE########
__FILENAME__ = euler57
#runas solve()
#pythran export solve()
def solve():
    '''
    It is possible to show that the square root of two can be expressed as an infinite continued fraction.
    
    sqrt(2) = 1 + 1/(2 + 1/(2 + 1/(2 + ... ))) = 1.414213...
    
    By expanding this for the first four iterations, we get:
    
    1 + 1/2 = 3/2 = 1.5
    1 + 1/(2 + 1/2) = 7/5 = 1.4
    1 + 1/(2 + 1/(2 + 1/2)) = 17/12 = 1.41666...
    1 + 1/(2 + 1/(2 + 1/(2 + 1/2))) = 41/29 = 1.41379...
    
    The next three expansions are 99/70, 239/169, and 577/408, but the eighth expansion, 1393/985, is the first example where the number of digits in the numerator exceeds the number of digits in the denominator.
    
    In the first one-thousand expansions, how many fractions contain a numerator with more digits than denominator?
    '''

    num, den, count = 3L, 2L, 0
    for iter in xrange(0, 1000):
        num, den = num + den + den, num + den
        if len(str(num)) > len(str(den)):
            count += 1
    return count


########NEW FILE########
__FILENAME__ = euler58
#runas solve()
#pythran export solve()
def solve():
    '''
    Starting with 1 and spiralling anticlockwise in the following way, a square spiral with side length 7 is formed.
    
    37 36 35 34 33 32 31
    38 17 16 15 14 13 30
    39 18  5  4  3 12 29
    40 19  6  1  2 11 28
    41 20  7  8  9 10 27
    42 21 22 23 24 25 26
    43 44 45 46 47 48 49
    
    It is interesting to note that the odd squares lie along the bottom right diagonal, but what is more interesting is that 8 out of the 13 numbers lying along both diagonals are prime; that is, a ratio of 8/13 ~ 62%.
    
    If one complete new layer is wrapped around the spiral above, a square spiral with side length 9 will be formed. If this process is continued, what is the side length of the square spiral for which the ratio of primes along both diagonals first falls below 10%?
    '''

    prime_list = [2, 3, 5, 7, 11, 13, 17, 19, 23]   # Ensure that this is initialised with at least 1 prime
    prime_dict = dict.fromkeys(prime_list, 1)

    def _isprime(n):
        ''' Raw check to see if n is prime. Assumes that prime_list is already populated '''
        isprime = n >= 2 and 1 or 0
        for prime in prime_list:                    # Check for factors with all primes
            if prime * prime > n: break             # ... up to sqrt(n)
            if not n % prime:
                isprime = 0
                break
        if isprime: prime_dict[n] = 1               # Maintain a dictionary for fast lookup
        return isprime

    def _refresh(x):
        ''' Refreshes primes upto x '''
        lastn      = prime_list[-1]
        while lastn <= x:                           # Keep working until we've got up to x
            lastn = lastn + 1                       # Check the next number
            if _isprime(lastn):
                prime_list.append(lastn)            # Maintain a list for sequential access

    _refresh(50000)

    width, diagonal, base, primes = 1, 1, 1, 0
    while True:
        width = width + 2
        increment = width - 1
        for i in xrange(0, 4):
            diagonal = diagonal + increment
            if i < 3 and _isprime(diagonal): primes += 1
        base = base + 4
        if primes * 10 < base:
            return width
            break


########NEW FILE########
__FILENAME__ = euler59
#runas solve()
#unittest.skip recursive generator
#pythran export solve()
def solve():
    '''
    Each character on a computer is assigned a unique code and the preferred standard is ASCII (American Standard Code for Information Interchange). For example, uppercase A = 65, asterisk (*) = 42, and lowercase k = 107.
    
    A modern encryption method is to take a text file, convert the bytes to ASCII, then XOR each byte with a given value, taken from a secret key. The advantage with the XOR function is that using the same encryption key on the cipher text, restores the plain text; for example, 65 XOR 42 = 107, then 107 XOR 42 = 65.
    
    For unbreakable encryption, the key is the same length as the plain text message, and the key is made up of random bytes. The user would keep the encrypted message and the encryption key in different locations, and without both "halves", it is impossible to decrypt the message.
    
    Unfortunately, this method is impractical for most users, so the modified method is to use a password as a key. If the password is shorter than the message, which is likely, the key is repeated cyclically throughout the message. The balance for this method is using a sufficiently long password key for security, but short enough to be memorable.
    
    Your task has been made easy, as the encryption key consists of three lower case characters. Using cipher1.txt (right click and 'Save Link/Target As...'), a file containing the encrypted ASCII codes, and the knowledge that the plain text must contain common English words, decrypt the message and find the sum of the ASCII values in the original text.
    '''
    
    def _combinators(_handle, items, n):
        if n==0:
            yield []
            return
        for i, item in enumerate(items):
            this_one = [ item ]
            for cc in _combinators(_handle, _handle(items, i), n-1):
                yield this_one + cc

    def selections(items, n):
        ''' take n (not necessarily distinct) items, order matters '''
        def keepAllItems(items, i):
            return items
        return _combinators(keepAllItems, items, n)
    
    code = tuple(int(c) for c in open('cipher1.txt').read().split(','))
    
    def decrypt(code, password):
        l = len(password)
        return tuple(c ^ password[i % l] for i, c in enumerate(code))
    
    def text(code): return ''.join(chr(c) for c in code)
    
    n = 0
    for password in selections(tuple((ord(c) for c in list('abcdefghijklmnopqrstuvwxyz'))), 3):
        c = decrypt(code, password)
        t = text(c)
        if t.find(' the ') > 0:
            return sum(c)
            break


########NEW FILE########
__FILENAME__ = average_position
#pythran export average_position(str:(float,float) dict, str:(float,float) dict)
#runas d = {"e":(1,2) } ; e = {"d":(2,1) } ; average_position(e,d)

def average_position(pos1,pos2):
	pos_avg={}
	for k in pos1:
		if pos2.has_key(k):
			pos_avg[k]=((pos1[k][0]+pos2[k][0])/2,(pos1[k][1]+pos2[k][1])/2)
		else:
			pos_avg[k]=pos1[k]
	for k in pos2:
		if pos1.has_key(k):
			if not pos_avg.has_key(k):
				pos_avg[k]=((pos1[k][0]+pos2[k][0])/2,(pos1[k][1]+pos2[k][1])/2)
		else:
			pos_avg[k]=pos2[k]
	return pos_avg

########NEW FILE########
__FILENAME__ = score_text
#pythran export score_text(str, str:int dict)
#runas score_text("e", { "d": 1 })
import string

def score_text(txt,kwdict):

	score=0
	for kw in kwdict.keys():
		if string.find(txt,kw)>-1:
			score+=kwdict[kw]
	return score

########NEW FILE########
__FILENAME__ = omp_atomic_add
def omp_atomic_add():
    sum = 0
    LOOPCOUNT=1000
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum += i
    return sum == (LOOPCOUNT * (LOOPCOUNT -1 ) ) /2

########NEW FILE########
__FILENAME__ = omp_atomic_bitand
def omp_atomic_bitand():
    sum = 0
    LOOPCOUNT = 1000
    logics = [1]*LOOPCOUNT
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum &= logics[i]
    return sum == 0

########NEW FILE########
__FILENAME__ = omp_atomic_bitor
def omp_atomic_bitor():
    sum = 0
    LOOPCOUNT = 1000
    logics = [1]*LOOPCOUNT
    logics[LOOPCOUNT/2] = 0
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum |= logics[i]
    return sum == 1

########NEW FILE########
__FILENAME__ = omp_atomic_bitxor
def omp_atomic_bitxor():
    sum = 0
    LOOPCOUNT = 1000
    logics = [0]*LOOPCOUNT
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum ^= logics[i]
    return sum == 0

########NEW FILE########
__FILENAME__ = omp_atomic_div
def omp_atomic_div():
    sum = 362880
    LOOPCOUNT = 10
    "omp parallel for"
    for i in xrange(1,LOOPCOUNT):
        "omp atomic"
        sum /= i
    return sum == 1

########NEW FILE########
__FILENAME__ = omp_atomic_lshift
def omp_atomic_lshift():
    sum = 1
    LOOPCOUNT = 10
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum <<= 1
    return sum == 2 ** LOOPCOUNT

########NEW FILE########
__FILENAME__ = omp_atomic_prod
def omp_atomic_prod():
    sum = 1
    LOOPCOUNT = 10
    "omp parallel for"
    for i in xrange(1,LOOPCOUNT):
        "omp atomic"
        sum *= i
    return sum == 362880

########NEW FILE########
__FILENAME__ = omp_atomic_rshift
def omp_atomic_rshift():
    sum = 1024
    LOOPCOUNT = 10
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum >>= 1
    return sum == 1

########NEW FILE########
__FILENAME__ = omp_atomic_sub
def omp_atomic_sub():
    sum = 0.
    LOOPCOUNT = 1000
    "omp parallel for"
    for i in xrange(LOOPCOUNT):
        "omp atomic"
        sum -= i
    return sum == -(LOOPCOUNT*(LOOPCOUNT-1))/2

########NEW FILE########
__FILENAME__ = omp_barrier
def omp_barrier():
    import omp
    from time import sleep
    result1 = 0
    result2 = 0
    if 'omp parallel':
        rank = omp.get_thread_num()
        if rank == 1:
            sleep(0.5)
            result2 = 3
        'omp barrier'
        if rank == 2:
            result1 = result2
    return result1 == 3

########NEW FILE########
__FILENAME__ = omp_critical
def omp_critical():
    sum = 0
    if 'omp parallel':
        mysum = 0
        'omp for'
        for i in range(1000):
            mysum += i
        'omp critical'
        sum += mysum
    return sum == 999 * 1000 / 2

########NEW FILE########
__FILENAME__ = omp_flush
import omp
from time import sleep


def omp_flush():
    result1 = 0
    result2 = 0
    if 'omp parallel':
        rank = omp.get_thread_num()
        'omp barrier'
        if rank == 1:
            result2 = 3
            'omp flush (result2)'
            dummy = result2
        if rank == 0:
            sleep(0.5)
            'omp flush(result2)'
            result1 = result2
    return result1 == result2 and result2 == dummy and result2 == 3

########NEW FILE########
__FILENAME__ = omp_for_firstprivate
def omp_for_firstprivate():
    sum = 0
    sum0 = 12345
    sum1 = 0
    import omp
    LOOPCOUNT = 1000
    if 'omp parallel private(sum1)':
        'omp single'
        threadsnum = omp.get_num_threads()
        'omp for firstprivate(sum0)'
        for i in range(1, LOOPCOUNT+1):
            sum0+=i
            sum1 = sum0
        'omp critical'
        sum+=sum1
    known_sum = 12345* threadsnum+ (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    return sum == known_sum

########NEW FILE########
__FILENAME__ = omp_for_lastprivate
def omp_for_lastprivate():
    sum = 0
    i0 = -1
    LOOPCOUNT = 1000
    if 'omp parallel':
        sum0 = 0
        'omp for schedule(static,7) lastprivate(i0)'
        for i in range(1, LOOPCOUNT + 1):
            sum0 += i
            i0 = i
        'omp critical'
        sum+=sum0
    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    return (sum == known_sum) and (i0 == LOOPCOUNT)

########NEW FILE########
__FILENAME__ = omp_for_nowait
def omp_for_nowait():
    LOOPCOUNT = 1000
    myarray = [0]*LOOPCOUNT
    result = 0
    count = 0
    import omp
    if 'omp parallel':
        rank = omp.get_thread_num()
        'omp for nowait'
        for i in range(LOOPCOUNT):
            if i == 0:
                while i < LOOPCOUNT**2: i+=1
                count = 1
                'omp flush(count)'
        for i in range(LOOPCOUNT):
            'omp flush(count)'
            if count ==0:
                result = 1
    return result == 1

########NEW FILE########
__FILENAME__ = omp_for_ordered
def omp_for_ordered():
    sum = 0
    is_larger = 1
    last_i = 0
    if 'omp parallel':
        my_is_larger = 1
        'omp for schedule(static,1) ordered'
        for i in range(1,100):
            if 'omp ordered':
                my_is_larger &= i > last_i
                last_i = i
                sum += i
        'omp critical'
        is_larger &= my_is_larger
    known_sum = (99 * 100) / 2
    return known_sum == sum and is_larger

########NEW FILE########
__FILENAME__ = omp_for_private
def do_some_work():
    import math
    sum = 0.
    for i in range(1000):
        sum+=math.sqrt(i)

def omp_for_private():
    sum = 0
    sum0 = 0
    LOOPCOUNT = 1000
    if 'omp parallel':
        sum1 = 0
        'omp for private(sum0) schedule(static,1)'
        for i in range(1, LOOPCOUNT+1):
            sum0 = sum1
            'omp flush'
            sum0 += i
            do_some_work()
            'omp flush'
            sum1 = sum0
        'omp critical'
        sum += sum1
    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_for_reduction
def omp_for_reduction():
    DOUBLE_DIGITS = 20
    MAX_FACTOR = 10
    KNOWN_PRODUCT = 3628800
    rounding_error = 1.e-9
    result = 0
    LOOPCOUNT=1000
    logicsArray = [0]*LOOPCOUNT
    sum = 0
    product = 1
    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    dt = 1. / 3.
    dsum=0.
    logics = logicsArray
    logic_and = 1
    logic_or = 0
    bit_and = 1
    bit_or = 0
    exclusiv_bit_or = 0

    # testing integer addition
    'omp parallel for schedule(dynamic,1) reduction(+:sum)'
    for j in range(1, LOOPCOUNT+1):
        sum = sum + j
    if known_sum != sum:
        result+=1
        print 'Error in sum with integers'

    # testing integer substaction
    diff = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    'omp parallel for schedule(dynamic,1) reduction(-:diff)'
    for j in range(1, LOOPCOUNT+1):
        diff = diff - j
    if diff != 0:
        result+=1
        print 'Error in difference with integers'

    # testing integer multiplication
    'omp parallel for schedule(dynamic,1) reduction(*:product)'
    for j in range(1, MAX_FACTOR +1):
        product *= j
    known_product = KNOWN_PRODUCT
    if known_product != product:
        result+=1
        print 'Error in product with integers'

    # testing bit and
    logics = [1] * LOOPCOUNT
    'omp parallel for schedule(dynamic,1) reduction(&:logic_and)'
    for logic in logics:
        logic_and = logic_and & logic
    if not logic_and:
        result+=1
        print 'Error in bit and part 1'

    logics[LOOPCOUNT/2]=0
    'omp parallel for schedule(dynamic,1) reduction(&:logic_and)'
    for logic in logics:
        logic_and = logic_and & logic
    if logic_and:
        result+=1
        print 'Error in bit and part 2'

    # testing bit or
    logics = [0] * LOOPCOUNT
    'omp parallel for schedule(dynamic,1) reduction(|:logic_or)'
    for logic in logics:
        logic_or = logic_or | logic
    if logic_or:
        result+=1
        print 'Error in logic or part 1'

    logics[LOOPCOUNT/2]=1
    'omp parallel for schedule(dynamic,1) reduction(|:logic_or)'
    for logic in logics:
        logic_or = logic_or | logic
    if not logic_or:
        result+=1
        print 'Error in logic or part 2'

    # testing exclusive bit or
    logics = [0] * LOOPCOUNT
    'omp parallel for schedule(dynamic,1) reduction(^:exclusiv_bit_or)'
    for logic in logics:
        exclusiv_bit_or = exclusiv_bit_or ^ logic
    if exclusiv_bit_or:
        result+=1
        print 'Error in exclusive bit or part 1'

    logics[LOOPCOUNT/2]=1
    'omp parallel for schedule(dynamic,1) reduction(^:exclusiv_bit_or)'
    for logic in logics:
        exclusiv_bit_or = exclusiv_bit_or ^ logic
    if not logic_or:
        result+=1
        print 'Error in exclusive bit or part 2'

    return result == 0

########NEW FILE########
__FILENAME__ = omp_for_schedule_auto
def omp_for_schedule_auto():
    import omp
    sum = 0
    sum0 = 12345
    sum1 = 0
    if 'omp parallel private(sum1)':
        if 'omp single':
            threadsnum = omp.get_num_threads()
        'omp for firstprivate(sum0) schedule(auto)'
        for i in xrange(1, 1001):
            sum0 += i
            sum1 = sum0
        if 'omp critical':
            sum += sum1
    known_sum = 12345 * threadsnum + (1000 * (1000 + 1)) / 2
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_for_schedule_dynamic
def omp_for_schedule_dynamic():
    CFDMAX_SIZE = 100
    chunk_size = 7
    tids = [0]*CFDMAX_SIZE
    count = 0
    tmp_count = 0
    result = 0
    import omp
    if 'omp parallel shared(tids)':
        tid = omp.get_thread_num()
        'omp for schedule(dynamic, chunk_size)'
        for i in range(CFDMAX_SIZE):
            tids[i] = tid

    for i in range(CFDMAX_SIZE-1):
        if tids[i] != tids[i+1]:
            count +=1

    tmp = [1] * (count + 1)
    for i in range(CFDMAX_SIZE-1):
        if tids[i] != tids[i+1]:
            tmp_count+=1
            tmp[tmp_count] = 1
        else:
            tmp[tmp_count]+=1

    for i in range(count):
        if tmp[i]%chunk_size != 0:
            result+=1
    if tmp[count]%chunk_size != CFDMAX_SIZE%chunk_size:
        result+=1
    return result == 0

########NEW FILE########
__FILENAME__ = omp_for_schedule_guided
import omp
from time import sleep


def omp_for_schedule_guided():
    tids = range(1001)
    maxiter = 0
    result = True
    notout = True
    if 'omp parallel':
        if 'omp single':
            threads = omp.get_num_threads()

    if threads<2:
        print "This test only works with at least two threads"
        result = False

    if 'omp parallel shared(tids, maxiter)':
        tid = omp.get_num_threads()
        'omp for nowait schedule(guided)'
        for j in xrange(1000):
            count = 0
            'omp flush(maxiter)'
            if j > maxiter:
                if 'omp critical':
                    maxiter = j
            'omp flush(notout, maxiter)'
            while notout and count < 0.0005 and maxiter == j:
                'omp flush(notout, maxiter)'
                sleep(0.0001)
                count += 0.0001
            tids[j] = tid

        notout = False
        'omp flush(maxiter, notout)'

    last_threadnr = tids[0]
    global_chunknr = 0
    local_chunknr = [0 for i in xrange(10)]
    openwork = 1000;
    tids[1000] = -1

    for i in xrange(1,1001):
        if last_threadnr == tids[i]:
            pass
        else:
            global_chunknr += 1
            local_chunknr[last_threadnr] += 1
            last_threadnr = tids[i]

    chuncksize = range(global_chunknr)

    global_chunknr = 0
    determined_chunksize = 1
    last_threadnr = tids[0]

    for i in xrange(1,1001):
        if last_threadnr == tids[i]:
            determined_chunksize += 1
        else:
            chuncksize[global_chunknr] = determined_chunksize
            global_chunknr += 1
            local_chunknr[last_threadnr] += 1
            last_threadnr = tids[i]
            determined_chunksize = 1

    expected_chunk_size = openwork / threads
    c = chuncksize[0] / expected_chunk_size

    for i in xrange(global_chunknr):
        if expected_chunk_size > 1:
            expected_chunk_size = c * openwork / threads
        if abs(chuncksize[i] - expected_chunk_size) >= 2:
            result = False

        openwork -= chuncksize[i]
    return result

########NEW FILE########
__FILENAME__ = omp_for_schedule_static
import omp
from time import sleep


def omp_for_schedule_static():
    tmp_count = 1
    result = True
    chunk_size = 7
    CFSMAX_SIZE = 1000
    tids = [0] * (CFSMAX_SIZE + 1)
    notout = True
    maxiter = 0

    if 'omp parallel shared(tids)':
        if 'omp single':
            threads = omp.get_num_threads()

    if threads < 2:
        print 'E: This test only works with at least two threads'
        return False

    tids[CFSMAX_SIZE] = -1

    if 'omp parallel shared(tids)':
        tid = omp.get_thread_num()

        'omp for nowait schedule(static,chunk_size)'
        for j in xrange(CFSMAX_SIZE):
            count = 0
            'omp flush(maxiter)'
            if j > maxiter:
                'omp critical'
                maxiter = j
            while notout and count < 0.01 and maxiter == j:
                'omp flush(maxiter,notout)'
                sleep(0.0005)
                count += 0.0005

            tids[j] = tid

        notout = False
        'omp flush(maxiter, notout)'

    lasttid = tids[0]
    tmp_count = 0

    for i in xrange(CFSMAX_SIZE + 1):
        if tids[i] == lasttid:
            tmp_count += 1
            continue
        if tids[i] == ((lasttid + 1)%threads) or (tids[i] == -1):
            if tmp_count == chunk_size:
                tmp_count = 1
                lastid = tids[i]
            else:
                if tids[i] == -1:
                    if i == CFSMAX_SIZE:
                        break
                    else:
                        print "E: Last thread (thread with number -1) was found before the end.\n"
                        result = False
                else:
                    print "E: chunk size was " + str(tmp_count) + ". (assigned was " + str(chunk_size) + ")\n"
                    result = False
        else:
            print "E: Found thread with number " + str(tids[i]) + " (should be inbetween 0 and " + str(threads - 1) + ").\n"
            result = False
    return result


########NEW FILE########
__FILENAME__ = omp_for_schedule_static_3
import omp
from time import sleep


def omp_for_schedule_static_3():
    tmp_count = 1
    result = True
    chunk_size = 7
    tids = range(1001)
    notout = True
    maxiter = 0

    if 'omp parallel shared(tids)':
        if 'omp single':
            threads = omp.get_num_threads()

    if threads < 2:
        print "E: This test only works with at least two threads"
        return False

    tids[1000] = -1

    if 'omp parallel shared(tids)':
        tid = omp.get_thread_num()
        'omp for nowait schedule(static,chunk_size)'
        for j in xrange(1000):
            count = 0
            'omp flush(maxiter)'
            if j > maxiter:
                if 'omp critical':
                    maxiter = j

            while notout and count < 0.01 and maxiter == j:
                'omp flush(maxiter,notout)'
                sleep(0.0005)
                count += 0.0005

            tids[j] = tid

        notout = False
    lasttid = tids[0]
    tmp_count = 0
    for i in xrange(1001):
        if tids[i] == lasttid:
            tmp_count += 1
            continue

        if tids[i] == (lasttid + 1) % threads or tids[i] == -1:
            if tmp_count == chunk_size:
                tmp_count = 1
                lasttid = tids[i]
            else:
                if tids[i] == -1:
                    if i == 1000:
                        break;
                    else:
                        print "E: Last thread (thread with number -1) was\
found before the end.\n"
                        result = False
                else:
                    print "ERROR: chunk size was " + str(tmp_count) +\
                    ". (assigned was " + str(chunk_size) + ")\n"
                    result = False
        else:
            print "ERROR: Found thread with number " + str(tids[i]) +\
            " (should be inbetween 0 and " + str(threads - 1) + ").\n"
            result = False

    tids = range(1000)
    tids2 = range(1000)

    if 'omp parallel':
        'omp for schedule(static) nowait'
        for n in xrange(1000):
            if 1000 == n + 1:
                sleep(0.0005)
            tids[n] = omp.get_thread_num()
        'omp for schedule(static) nowait'
        for m in xrange(1, 1001):
            tids2[m-1] = omp.get_thread_num()

    for i in xrange(1000):
        if tids[i] != tids2[i]:
            print "E: Chunk no. " + str(i) + " was assigned once to thread " +\
            str(tids[i]) + " and later to thread " + str(tids2[i]) + ".\n"
            result = False
    return result

########NEW FILE########
__FILENAME__ = omp_get_num_threads
def omp_get_num_threads():
    import omp
    nthreads = 0
    nthreads_lib = -1

    if 'omp parallel':
        if 'omp critical':
            nthreads += 1
        if 'omp single':
            nthreads_lib = omp.get_num_threads()

    return nthreads == nthreads_lib

########NEW FILE########
__FILENAME__ = omp_get_wtick
def omp_get_wtick():
    import omp
    tick = omp.get_wtick()
    return tick > 0.0 and tick < 0.01


########NEW FILE########
__FILENAME__ = omp_get_wtime
def omp_get_wtime():
    import omp
    from time import sleep
    wait_time = 1

    start = omp.get_wtime()
    sleep(wait_time)
    end = omp.get_wtime()
    measured_time = end - start

    return measured_time > 0.99 * wait_time and measured_time < 1.01 * wait_time

########NEW FILE########
__FILENAME__ = omp_in_parallel
def omp_in_parallel():
    import omp
    serial = 1
    isparallel = 0

    serial = omp.in_parallel()

    if 'omp parallel':
        if 'omp single':
            isparallel = omp.in_parallel()

    if 'omp parallel':
        if 'omp single':
            pass

    return not serial and isparallel

########NEW FILE########
__FILENAME__ = omp_master
def omp_master():
    import omp
    threads = 0
    executing_thread = -1

    if 'omp parallel':
        if 'omp master':
            if 'omp critical':
                threads += 1
            executing_thread = omp.get_thread_num()
    return threads == 1 and executing_thread == 0

########NEW FILE########
__FILENAME__ = omp_master_3
def omp_master_3():
    import omp
    tid_result = 0
    nthreads = 0
    executing_thread = -1

    if 'omp parallel':
        if 'omp master':
            tid = omp.get_thread_num()
            if tid != 0:
                if 'omp critical':
                    tid_result += 1
            if 'omp critical':
                nthreads += 1
            executing_thread = omp.get_thread_num()
    return nthreads == 1 and executing_thread == 0 and tid_result == 0

########NEW FILE########
__FILENAME__ = omp_nested
def omp_nested():
    import omp
    counter = 0
    omp.set_nested(1)

    if 'omp parallel shared(counter)':
        if 'omp critical':
            counter += 1

        if 'omp parallel':
            if 'omp critical':
                counter -= 1
    return counter != 0

########NEW FILE########
__FILENAME__ = omp_parallel_copyin
#unittest.skip threadprivate not supported
def omp_parallel_copyin():
    sum = 0
    sum1 = 7
    num_threads = 0

    if 'omp parallel copyin(sum1) private(i)':
        'omp for'
        for i in xrange(1, 1000):
            sum1 += i
        if 'omp critical':
            sum += sum1
            num_threads += 1

    known_sum = (999 * 1000) / 2 + 7 * num_threads
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_parallel_default
def omp_parallel_default():
    import omp
    sum = 0
    known_sum = (1000 * (1000 + 1)) / 2

    if "omp parallel default(shared)":
        mysum = 0
        'omp for'
        for i in xrange(1, 1001):
            mysum += i

        if 'omp critical':
            sum += mysum

    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_parallel_firstprivate
def omp_parallel_firstprivate():
    sum = 0
    sum1 = 7
    num_threads = 0

    if 'omp parallel firstprivate(sum1)':
        'omp for'
        for i in xrange(1,1000):
            sum1 += i

        if 'omp critical':
            sum += sum1
            num_threads += 1

    known_sum = (999 * 1000) / 2 + 7 * num_threads
    return sum == known_sum

########NEW FILE########
__FILENAME__ = omp_parallel_for_firstprivate
def omp_parallel_for_firstprivate():
    sum = 0
    i2 = 3

    'omp parallel for reduction(+:sum) firstprivate(i2)'
    for i in xrange(1,1001):
        sum += i + i2

    known_sum = (1000 * (1000 + 1)) / 2 + i2 * 1000;
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_parallel_for_if
def omp_parallel_for_if():
    using = 0
    num_threads = 0
    import omp
    sum = 0
    sum2 = 0
    LOOPCOUNT=1000
    'omp parallel for if(using == 1)'
    for i in range(LOOPCOUNT+1):
        num_threads = omp.get_num_threads()
        sum+=i
    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    return known_sum == sum and num_threads == 1

########NEW FILE########
__FILENAME__ = omp_parallel_for_lastprivate
def omp_parallel_for_lastprivate():
    sum = 0
    i0 = -1
    'omp parallel for reduction(+:sum) schedule(static,7) lastprivate(i0)'
    for i in xrange(1,1001):
        sum += i
        i0 = i

    known_sum = (1000 * (1000 + 1)) / 2
    return known_sum == sum and i0 == 1000

########NEW FILE########
__FILENAME__ = omp_parallel_for_ordered
def omp_parallel_for_ordered():
    sum = 0
    is_larger = True
    last_i = 0
    def check_i_islarger2(i_):
        islarger = i_ > last_i
        last_i = i_
        return islarger

    'omp parallel for schedule(static, 1) ordered'
    for i in xrange(1,100):
        ii = i
        if 'omp ordered':
            is_larger = check_i_islarger2(i) and is_larger
            sum += ii

    known_sum = (99 * 100) / 2
    return known_sum == sum and is_larger

########NEW FILE########
__FILENAME__ = omp_parallel_for_private
import math

def some_work():
    sum = 0;
    for i in xrange(0, 1000):
        sum += math.sqrt (i)

def omp_parallel_for_private():
    sum = 0
    i2 = 0

    'omp parallel for reduction(+: sum) schedule(static, 1) private(i2)'
    for i in xrange(1, 1001):
        i2 = i
        'omp flush'
        some_work()
        'omp flush'
        sum += i2

    known_sum = (1000 * (1000 + 1)) / 2
    return known_sum == sum;

########NEW FILE########
__FILENAME__ = omp_parallel_for_reduction
def omp_parallel_for_reduction():
    import math
    dt = 0.5
    rounding_error = 1.E-9

    sum = 0
    dsum = 0
    dt = 1. / 3.
    result = True
    product = 1
    logic_and = 1
    logic_or = 0
    bit_and = 1
    bit_or = 0
    exclusiv_bit_or = 0
    i = 0

    known_sum = (1000 * (1000 + 1)) / 2

    'omp parallel for schedule(dynamic,1) private(i) reduction(+:sum)'
    for i in xrange(1,1001):
        sum += i

    if known_sum != sum:
        print "E: reduction(+:sum)"
        result = False

    diff = (1000 * (1000 + 1)) / 2

    'omp parallel for schedule(dynamic,1) private(i) reduction(-:diff)'
    for i in xrange(1,1001):
        diff -= i

    if diff != 0:
        print "E: reduction(-:diff)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    dknown_sum = (1 - dpt) / (1 - dt)

    'omp parallel for schedule(dynamic,1) private(i) reduction(+:dsum)'
    for i in xrange(0,20):
        dsum += math.pow(dt, i)

    if abs(dsum-dknown_sum) > rounding_error:
        print "E: reduction(+:dsum)"
        result = False

    dsum = 0
    dpt = 1
    for i in xrange(0, 20):
        dpt *= dt
    ddiff = (1 - dpt) / (1 - dt)

    'omp parallel for schedule(dynamic,1) private(i) reduction(-:ddiff)'
    for i in xrange(0,20):
        ddiff -= math.pow(dt, i)

    if abs(ddiff) > rounding_error:
        print "E: reduction(-:ddiff)"
        result = False

    'omp parallel for schedule(dynamic,1) private(i) reduction(*:product)'
    for i in xrange(1,11):
        product *= i

    known_product = 3628800

    if known_product != product:
        print "E: reduction(*:product)"
        result = False

    logics = [1 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) private(i) reduction(&&:logic_and)'
    for i in xrange(0, 1000):
        logic_and = (logic_and and logics[i])

    if not logic_and:
        print "E: reduction(&&:logic_and)"
        result = False

    logic_and = 1;
    logics[1000/2]=0

    'omp parallel for schedule(dynamic,1) private(i) reduction(&&:logic_and)'
    for i in xrange(0, 1000):
        logic_and = (logic_and and logics[i])

    if logic_and:
        print "E: reduction(&&:logic_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) private(i) reduction(||:logic_or)'
    for i in xrange(0, 1000):
        logic_or = (logic_or or logics[i])

    if logic_or:
        print "E: reduction(||:logic_or)"
        result = False

    logic_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) private(i) reduction(||:logic_or)'
    for i in xrange(0, 1000):
        logic_or = (logic_or or logics[i])

    if not logic_or:
        print "E: reduction(||:logic_or) with logics[1000/2]=1"
        result = False

    logics = [1 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) private(i) reduction(&:bit_and)'
    for i in xrange(0, 1000):
        bit_and = (bit_and & logics[i])

    if not bit_and:
        print "E: reduction(&:bit_and)"
        result = False

    bit_and = 1;
    logics[1000/2]=0

    'omp parallel for schedule(dynamic,1) private(i) reduction(&:bit_and)'
    for i in xrange(0, 1000):
        bit_and = (bit_and & logics[i])

    if bit_and:
        print "E: reduction(&:bit_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) private(i) reduction(|:bit_or)'
    for i in xrange(0, 1000):
        bit_or = (bit_or | logics[i])

    if bit_or:
        print "E: reduction(|:bit_or)"
        result = False

    bit_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) private(i) reduction(|:bit_or)'
    for i in xrange(0, 1000):
        bit_or = (bit_or | logics[i])

    if not bit_or:
        print "E: reduction(|:bit_or) with logics[1000/2]=1"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) private(i) reduction(^:exclusiv_bit_or)'
    for i in xrange(0, 1000):
        exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or)"
        result = False

    exclusiv_bit_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) private(i) reduction(^:exclusiv_bit_or)'
    for i in xrange(0, 1000):
        exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if not exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or) with logics[1000/2]=1"
        result = False
    return result

########NEW FILE########
__FILENAME__ = omp_parallel_if
def omp_parallel_if():
    control = 1
    sum = 0
    known_sum = (1000 * (1000 + 1)) / 2
    if 'omp parallel if(control==0)':
        mysum = 0
        for i in xrange(1,1001):
            mysum += i
        if 'omp critical':
            sum += mysum

    return sum == known_sum

########NEW FILE########
__FILENAME__ = omp_parallel_num_threads
unittest.skip
#segfault ....
def omp_parallel_num_threads():
    import omp
    max_threads = 0
    failed = 0

    if 'omp parallel':
        if 'omp master':
            max_threads = omp.get_num_threads()

    for threads in xrange(1, max_threads + 1):
        nthreads = 0
        if 'omp parallel reduction(+:failed) num_threads(threads)':
            failed += (threads != omp.get_num_threads())
            'omp atomic'
            nthreads += 1
        failed += (nthreads != threads)

    return not failed

########NEW FILE########
__FILENAME__ = omp_parallel_private
def omp_parallel_private():
    sum = 0
    num_threads = 0

    if 'omp parallel':
        sum1 = 7
        'omp for'
        for i in xrange(1, 1000):
            sum1 += i

        if 'omp critical':
            sum += sum1
            num_threads += 1

    known_sum = (999 * 1000) / 2 + 7 * num_threads

    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_parallel_reduction
def omp_parallel_reduction():
    import math
    dt = 0.5
    rounding_error = 1.E-9

    sum = 0
    dsum = 0
    dt = 1. / 3.
    result = True
    product = 1
    logic_and = 1
    logic_or = 0
    bit_and = 1
    bit_or = 0
    exclusiv_bit_or = 0

    known_sum = (1000 * (1000 + 1)) / 2

    'omp parallel for schedule(dynamic,1) reduction(+:sum)'
    for i in xrange(1,1001):
        sum += i

    if known_sum != sum:
        print "E: reduction(+:sum)"
        result = False

    diff = (1000 * (1000 + 1)) / 2

    'omp parallel for schedule(dynamic,1) reduction(-:diff)'
    for i in xrange(1,1001):
        diff -= i

    if diff != 0:
        print "E: reduction(-:diff)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    dknown_sum = (1 - dpt) / (1 - dt)

    'omp parallel for schedule(dynamic,1) reduction(+:dsum)'
    for i in xrange(0,20):
        dsum += math.pow(dt, i)

    if abs(dsum-dknown_sum) > rounding_error:
        print "E: reduction(+:dsum)"
        result = False

    dsum = 0
    dpt = 1
    for i in xrange(0, 20):
        dpt *= dt
    ddiff = (1 - dpt) / (1 - dt)

    'omp parallel for schedule(dynamic,1) reduction(-:ddiff)'
    for i in xrange(0,20):
        ddiff -= math.pow(dt, i)

    if abs(ddiff) > rounding_error:
        print "E: reduction(-:ddiff)"
        result = False

    'omp parallel for schedule(dynamic,1) reduction(*:product)'
    for i in xrange(1,11):
        product *= i

    known_product = 3628800

    if known_product != product:
        print "E: reduction(*:product)"
        result = False

    logics = [1 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) reduction(&&:logic_and)'
    for i in xrange(0, 1000):
        logic_and = (logic_and and logics[i])

    if not logic_and:
        print "E: reduction(&&:logic_and)"
        result = False

    logic_and = 1;
    logics[1000/2]=0

    'omp parallel for schedule(dynamic,1) reduction(&&:logic_and)'
    for i in xrange(0, 1000):
        logic_and = (logic_and and logics[i])

    if logic_and:
        print "E: reduction(&&:logic_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) reduction(||:logic_or)'
    for i in xrange(0, 1000):
        logic_or = (logic_or or logics[i])

    if logic_or:
        print "E: reduction(||:logic_or)"
        result = False

    logic_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) reduction(||:logic_or)'
    for i in xrange(0, 1000):
        logic_or = (logic_or or logics[i])

    if not logic_or:
        print "E: reduction(||:logic_or) with logics[1000/2]=1"
        result = False

    logics = [1 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) reduction(&:bit_and)'
    for i in xrange(0, 1000):
        bit_and = (bit_and & logics[i])

    if not bit_and:
        print "E: reduction(&:bit_and)"
        result = False

    bit_and = 1;
    logics[1000/2]=0

    'omp parallel for schedule(dynamic,1) reduction(&:bit_and)'
    for i in xrange(0, 1000):
        bit_and = (bit_and & logics[i])

    if bit_and:
        print "E: reduction(&:bit_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) reduction(|:bit_or)'
    for i in xrange(0, 1000):
        bit_or = (bit_or | logics[i])

    if bit_or:
        print "E: reduction(|:bit_or)"
        result = False

    bit_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) reduction(|:bit_or)'
    for i in xrange(0, 1000):
        bit_or = (bit_or | logics[i])

    if not bit_or:
        print "E: reduction(|:bit_or) with logics[1000/2]=1"
        result = False

    logics = [0 for i in xrange(0,1000)]

    'omp parallel for schedule(dynamic,1) reduction(^:exclusiv_bit_or)'
    for i in xrange(0, 1000):
        exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or)"
        result = False

    exclusiv_bit_or = 0;
    logics[1000/2]=1

    'omp parallel for schedule(dynamic,1) reduction(^:exclusiv_bit_or)'
    for i in xrange(0, 1000):
        exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if not exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or) with logics[1000/2]=1"
        result = False
    return result

########NEW FILE########
__FILENAME__ = omp_parallel_sections_firstprivate
def omp_parallel_sections_firstprivate():
    sum = 7
    sum0 = 11

    if 'omp parallel sections firstprivate(sum0)':
        if 'omp section':
            if 'omp critical':
                sum += sum0
        if 'omp section':
            if 'omp critical':
                sum += sum0
        if 'omp section':
            if 'omp critical':
                sum += sum0
    known_sum=11*3+7
    return (known_sum==sum)

########NEW FILE########
__FILENAME__ = omp_parallel_sections_lastprivate
def omp_parallel_sections_lastprivate():
    sum =0
    sum0 = 0
    i0 = -1
    if 'omp parallel sections private(sum0) lastprivate(i0)':
        if 'omp section':
            sum0 = 0
            for i in xrange(1, 400):
                sum0 += i
                i0 = i
            if 'omp critical':
                sum += sum0
        if 'omp section':
            sum0 = 0
            for i in xrange(400, 700):
                sum0 += i
                i0 = i
            if 'omp critical':
                sum += sum0
        if 'omp section':
            sum0 = 0
            for i in xrange(700, 1000):
                sum0 += i
                i0 = i
            if 'omp critical':
                sum += sum0

    known_sum = (999 * 1000) / 2
    return known_sum == sum and i0 == 999

########NEW FILE########
__FILENAME__ = omp_parallel_sections_private
def omp_parallel_sections_private():
    sum = 7
    sum0 = 0

    if 'omp parallel sections private(sum0)':
        if 'omp section':
            sum0 = 0
            for i in xrange(0, 400):
                sum0 += i
            if 'omp critical':
                sum += sum0
        if 'omp section':
            sum0 = 0
            for i in xrange(400, 700):
                sum0 += i
            if 'omp critical':
                sum += sum0
        if 'omp section':
            sum0 = 0
            for i in xrange(700, 1000):
                sum0 += i
            if 'omp critical':
                sum += sum0

    known_sum = (999 * 1000) / 2 + 7;
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_parallel_sections_reduction
def omp_parallel_sections_reduction():
    import math
    dt = 0.5
    rounding_error = 1.E-9

    sum = 7
    dsum = 0
    dt = 1. / 3.
    result = True
    product = 1
    logic_and = 1
    logic_or = 0
    bit_and = 1
    bit_or = 0
    i = 0
    exclusiv_bit_or = 0

    known_sum = (1000 * 999) / 2 + 7

    if 'omp parallel sections private(i) reduction(+:sum)':
        if 'omp section':
            for i in xrange(1,300):
                sum += i
        if 'omp section':
            for i in xrange(300,700):
                sum += i
        if 'omp section':
            for i in xrange(700,1000):
                sum += i

    if known_sum != sum:
        print "E: reduction(+:sum)"
        result = False

    diff = (1000 * 999) / 2

    if 'omp parallel sections private(i) reduction(-:diff)':
        if 'omp section':
            for i in xrange(1,300):
                diff -= i
        if 'omp section':
            for i in xrange(300,700):
                diff -= i
        if 'omp section':
            for i in xrange(700,1000):
                diff -= i

    if diff != 0:
        print "E: reduction(-:diff)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    dknown_sum = (1 - dpt) / (1 - dt)

    if 'omp parallel sections private(i) reduction(+:dsum)':
        if 'omp section':
            for i in xrange(0,7):
                dsum += math.pow(dt, i)
        if 'omp section':
            for i in xrange(7,14):
                dsum += math.pow(dt, i)
        if 'omp section':
            for i in xrange(14,20):
                dsum += math.pow(dt, i)

    if abs(dsum-dknown_sum) > rounding_error:
        print "E: reduction(+:dsum)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    ddiff = (1 - dpt) / (1 - dt)

    if 'omp parallel sections private(i) reduction(-:ddiff)':
        if 'omp section':
            for i in xrange(0,6):
                ddiff -= math.pow(dt, i)
        if 'omp section':
            for i in xrange(6,12):
                ddiff -= math.pow(dt, i)
        if 'omp section':
            for i in xrange(12,20):
                ddiff -= math.pow(dt, i)

    if abs(ddiff) > rounding_error:
        print "E: reduction(-:ddiff)"
        result = False

    if 'omp parallel sections private(i) reduction(*:product)':
        if 'omp section':
            for i in xrange(1,3):
                product *= i
        if 'omp section':
            for i in xrange(3,6):
                product *= i
        if 'omp section':
            for i in xrange(6,11):
                product *= i

    known_product = 3628800

    if known_product != product:
        print "E: reduction(*:product)"
        result = False

    logics = [1 for i in xrange(0,1000)]

    if 'omp parallel sections private(i) reduction(&&:logic_and)':
        if 'omp section':
            for i in xrange(0, 300):
                logic_and = (logic_and and logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                logic_and = (logic_and and logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                logic_and = (logic_and and logics[i])

    if not logic_and:
        print "E: reduction(&&:logic_and)"
        result = False

    logic_and = 1;
    logics[1000/2]=0

    if 'omp parallel sections private(i) reduction(&&:logic_and)':
        if 'omp section':
            for i in xrange(0, 300):
                logic_and = (logic_and and logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                logic_and = (logic_and and logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                logic_and = (logic_and and logics[i])

    if logic_and:
        print "E: reduction(&&:logic_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel sections private(i) reduction(||:logic_or)':
        if 'omp section':
            for i in xrange(0, 300):
                logic_or = (logic_or or logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                logic_or = (logic_or or logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                logic_or = (logic_or or logics[i])

    if logic_or:
        print "E: reduction(||:logic_or)"
        result = False

    logic_or = 0;
    logics[1000/2]=1

    if 'omp parallel sections private(i) reduction(||:logic_or)':
        if 'omp section':
            for i in xrange(0, 300):
                logic_or = (logic_or or logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                logic_or = (logic_or or logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                logic_or = (logic_or or logics[i])

    if not logic_or:
        print "E: reduction(||:logic_or) with logics[1000/2]=1"
        result = False

    logics = [1 for i in xrange(0,1000)]

    if 'omp parallel sections private(i) reduction(&:bit_and)':
        if 'omp section':
            for i in xrange(0, 300):
                bit_and = (bit_and & logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                bit_and = (bit_and & logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                bit_and = (bit_and & logics[i])

    if not bit_and:
        print "E: reduction(&:bit_and)"
        result = False

    bit_and = 1;
    logics[1000/2]=0

    if 'omp parallel sections private(i) reduction(&:bit_and)':
        if 'omp section':
            for i in xrange(0, 300):
                bit_and = (bit_and & logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                bit_and = (bit_and & logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                bit_and = (bit_and & logics[i])

    if bit_and:
        print "E: reduction(&:bit_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel sections private(i) reduction(|:bit_or)':
        if 'omp section':
            for i in xrange(0, 300):
                bit_or = (bit_or | logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                bit_or = (bit_or | logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                bit_or = (bit_or | logics[i])

    if bit_or:
        print "E: reduction(|:bit_or)"
        result = False

    bit_or = 0;
    logics[1000/2]=1

    if 'omp parallel sections private(i) reduction(|:bit_or)':
        if 'omp section':
            for i in xrange(0, 300):
                bit_or = (bit_or | logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                bit_or = (bit_or | logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                bit_or = (bit_or | logics[i])

    if not bit_or:
        print "E: reduction(|:bit_or) with logics[1000/2]=1"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel sections private(i) reduction(^:exclusiv_bit_or)':
        if 'omp section':
            for i in xrange(0, 300):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or)"
        result = False

    exclusiv_bit_or = 0;
    logics[1000/2]=1

    if 'omp parallel sections private(i) reduction(^:exclusiv_bit_or)':
        if 'omp section':
            for i in xrange(0, 300):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
        if 'omp section':
            for i in xrange(300, 700):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
        if 'omp section':
            for i in xrange(700, 1000):
                exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if not exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or) with logics[1000/2]=1"
        result = False
    return result

########NEW FILE########
__FILENAME__ = omp_parallel_shared
def omp_parallel_shared():
    sum = 0
    LOOPCOUNT = 1000
    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2
    if 'omp parallel shared(sum)':
        mysum = 0
        'omp for'
        for i in xrange(1, LOOPCOUNT + 1):
            mysum += i
        if 'omp critical':
            sum += mysum

    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_sections_firstprivate
def omp_sections_firstprivate():
    sum = 7
    sum0 = 11

    if 'omp parallel':
        if 'omp sections firstprivate(sum0)':
            if 'omp section':
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                if 'omp critical':
                    sum += sum0
    known_sum=11*3+7
    return (known_sum==sum)

########NEW FILE########
__FILENAME__ = omp_sections_lastprivate
def omp_sections_lastprivate():
    sum =0
    sum0 = 0
    i0 = -1
    if 'omp parallel':
        if 'omp sections private(sum0) lastprivate(i0)':
            if 'omp section':
                sum0 = 0
                for i in xrange(1, 400):
                    sum0 += i
                    i0 = i
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                sum0 = 0
                for i in xrange(400, 700):
                    sum0 += i
                    i0 = i
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                sum0 = 0
                for i in xrange(700, 1000):
                    sum0 += i
                    i0 = i
                if 'omp critical':
                    sum += sum0

    known_sum = (999 * 1000) / 2
    return known_sum == sum and i0 == 999

########NEW FILE########
__FILENAME__ = omp_sections_nowait
def omp_sections_nowait():
    import omp
    from time import sleep
    result = False
    count = 0

    if 'omp parallel':
        rank = omp.get_thread_num()

        if 'omp sections nowait':
            if 'omp section':
                sleep(0.01)
                count = 1
                'omp flush(count)'
            if 'omp section':
                pass

        if 'omp sections':
            if 'omp section':
                pass
            if 'omp section':
                if count == 0:
                    result = True
    return result

########NEW FILE########
__FILENAME__ = omp_sections_private
def omp_sections_private():
    sum = 7
    sum0 = 0

    if 'omp parallel':
        if 'omp sections private(sum0)':
            if 'omp section':
                sum0 = 0
                for i in xrange(0, 400):
                    sum0 += i
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                sum0 = 0
                for i in xrange(400, 700):
                    sum0 += i
                if 'omp critical':
                    sum += sum0
            if 'omp section':
                sum0 = 0
                for i in xrange(700, 1000):
                    sum0 += i
                if 'omp critical':
                    sum += sum0

    known_sum = (999 * 1000) / 2 + 7;
    return known_sum == sum

########NEW FILE########
__FILENAME__ = omp_sections_reduction
def omp_sections_reduction():
    import math
    dt = 0.5
    rounding_error = 1.E-9

    sum = 7
    dsum = 0
    dt = 1. / 3.
    result = True
    product = 1
    logic_and = 1
    logic_or = 0
    bit_and = 1
    bit_or = 0
    i = 0
    exclusiv_bit_or = 0

    known_sum = (1000 * 999) / 2 + 7

    if 'omp parallel':
        if 'omp sections private(i) reduction(+:sum)':
            if 'omp section':
                for i in xrange(1,300):
                    sum += i
            if 'omp section':
                for i in xrange(300,700):
                    sum += i
            if 'omp section':
                for i in xrange(700,1000):
                    sum += i

    if known_sum != sum:
        print "E: reduction(+:sum)"
        result = False

    diff = (1000 * 999) / 2

    if 'omp parallel':
        if 'omp sections private(i) reduction(-:diff)':
            if 'omp section':
                for i in xrange(1,300):
                    diff -= i
            if 'omp section':
                for i in xrange(300,700):
                    diff -= i
            if 'omp section':
                for i in xrange(700,1000):
                    diff -= i

    if diff != 0:
        print "E: reduction(-:diff)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    dknown_sum = (1 - dpt) / (1 - dt)

    if 'omp parallel':
        if 'omp sections private(i) reduction(+:dsum)':
            if 'omp section':
                for i in xrange(0,7):
                    dsum += math.pow(dt, i)
            if 'omp section':
                for i in xrange(7,14):
                    dsum += math.pow(dt, i)
            if 'omp section':
                for i in xrange(14,20):
                    dsum += math.pow(dt, i)

    if abs(dsum-dknown_sum) > rounding_error:
        print "E: reduction(+:dsum)"
        result = False

    dsum = 0
    dpt = 0
    for i in xrange(0, 20):
        dpt *= dt
    ddiff = (1 - dpt) / (1 - dt)

    if 'omp parallel':
        if 'omp sections private(i) reduction(-:ddiff)':
            if 'omp section':
                for i in xrange(0,6):
                    ddiff -= math.pow(dt, i)
            if 'omp section':
                for i in xrange(6,12):
                    ddiff -= math.pow(dt, i)
            if 'omp section':
                for i in xrange(12,20):
                    ddiff -= math.pow(dt, i)

    if abs(ddiff) > rounding_error:
        print "E: reduction(-:ddiff)"
        result = False

    if 'omp parallel':
        if 'omp sections private(i) reduction(*:product)':
            if 'omp section':
                for i in xrange(1,3):
                    product *= i
            if 'omp section':
                for i in xrange(3,6):
                    product *= i
            if 'omp section':
                for i in xrange(6,11):
                    product *= i

    known_product = 3628800

    if known_product != product:
        print "E: reduction(*:product)"
        result = False

    logics = [1 for i in xrange(0,1000)]

    if 'omp parallel':
        if 'omp sections private(i) reduction(&&:logic_and)':
            if 'omp section':
                for i in xrange(0, 300):
                    logic_and = (logic_and and logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    logic_and = (logic_and and logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    logic_and = (logic_and and logics[i])

    if not logic_and:
        print "E: reduction(&&:logic_and)"
        result = False

    logic_and = 1;
    logics[1000/2]=0

    if 'omp parallel':
        if 'omp sections private(i) reduction(&&:logic_and)':
            if 'omp section':
                for i in xrange(0, 300):
                    logic_and = (logic_and and logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    logic_and = (logic_and and logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    logic_and = (logic_and and logics[i])

    if logic_and:
        print "E: reduction(&&:logic_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel':
        if 'omp sections private(i) reduction(||:logic_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    logic_or = (logic_or or logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    logic_or = (logic_or or logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    logic_or = (logic_or or logics[i])

    if logic_or:
        print "E: reduction(||:logic_or)"
        result = False

    logic_or = 0;
    logics[1000/2]=1

    if 'omp parallel':
        if 'omp sections private(i) reduction(||:logic_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    logic_or = (logic_or or logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    logic_or = (logic_or or logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    logic_or = (logic_or or logics[i])

    if not logic_or:
        print "E: reduction(||:logic_or) with logics[1000/2]=1"
        result = False

    logics = [1 for i in xrange(0,1000)]

    if 'omp parallel':
        if 'omp sections private(i) reduction(&:bit_and)':
            if 'omp section':
                for i in xrange(0, 300):
                    bit_and = (bit_and & logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    bit_and = (bit_and & logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    bit_and = (bit_and & logics[i])

    if not bit_and:
        print "E: reduction(&:bit_and)"
        result = False

    bit_and = 1;
    logics[1000/2]=0

    if 'omp parallel':
        if 'omp sections private(i) reduction(&:bit_and)':
            if 'omp section':
                for i in xrange(0, 300):
                    bit_and = (bit_and & logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    bit_and = (bit_and & logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    bit_and = (bit_and & logics[i])

    if bit_and:
        print "E: reduction(&:bit_and) with logics[1000/2]=0"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel':
        if 'omp sections private(i) reduction(|:bit_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    bit_or = (bit_or | logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    bit_or = (bit_or | logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    bit_or = (bit_or | logics[i])

    if bit_or:
        print "E: reduction(|:bit_or)"
        result = False

    bit_or = 0;
    logics[1000/2]=1

    if 'omp parallel':
        if 'omp sections private(i) reduction(|:bit_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    bit_or = (bit_or | logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    bit_or = (bit_or | logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    bit_or = (bit_or | logics[i])

    if not bit_or:
        print "E: reduction(|:bit_or) with logics[1000/2]=1"
        result = False

    logics = [0 for i in xrange(0,1000)]

    if 'omp parallel':
        if 'omp sections private(i) reduction(^:exclusiv_bit_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or)"
        result = False

    exclusiv_bit_or = 0;
    logics[1000/2]=1

    if 'omp parallel':
        if 'omp sections private(i) reduction(^:exclusiv_bit_or)':
            if 'omp section':
                for i in xrange(0, 300):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
            if 'omp section':
                for i in xrange(300, 700):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])
            if 'omp section':
                for i in xrange(700, 1000):
                    exclusiv_bit_or = (exclusiv_bit_or ^ logics[i])

    if not exclusiv_bit_or:
        print "E: reduction(^:exclusiv_bit_or) with logics[1000/2]=1"
        result = False
    return result

########NEW FILE########
__FILENAME__ = omp_single
def omp_single():
    nr_threads_in_single = 0
    result = 0
    nr_iterations = 0
    LOOPCOUNT = 1000

    if 'omp parallel':
        for i in xrange(LOOPCOUNT):
            if 'omp single':
                'omp flush'
                nr_threads_in_single += 1
                'omp flush'
                nr_iterations += 1
                nr_threads_in_single -= 1
                result += nr_threads_in_single
    return result == 0 and nr_iterations == LOOPCOUNT

########NEW FILE########
__FILENAME__ = omp_single_copyprivate
def omp_single_copyprivate():
    result = 0
    nr_iterations = 0
    LOOPCOUNT = 1000
    j = 0

    if 'omp parallel private(j)':
        for i in xrange(LOOPCOUNT):
            if 'omp single copyprivate(j)':
                nr_iterations += 1
                j = i
            if 'omp critical':
                result += j - i
            'omp barrier'
    return result == 0 and nr_iterations == LOOPCOUNT


########NEW FILE########
__FILENAME__ = omp_single_nowait
def omp_single_nowait():
    total_iterations = 0
    nr_iterations = 0
    LOOPCOUNT = 1000
    i = 0

    if 'omp parallel private(i)':
        for i in xrange(LOOPCOUNT):
            if 'omp single nowait':
                'omp atomic'
                nr_iterations += 1

    if 'omp parallel private(i)':
        my_iterations = 0
        for i in xrange(LOOPCOUNT):
            if 'omp single nowait':
                my_iterations += 1
        if 'omp critical':
            total_iterations += my_iterations

    return nr_iterations == LOOPCOUNT and total_iterations == LOOPCOUNT

########NEW FILE########
__FILENAME__ = omp_single_private
def omp_single_private():
    nr_threads_in_single = 0
    nr_iterations = 0
    result = 0
    LOOPCOUNT = 1000

    if 'omp parallel':
        myresult = 0
        myit = 0
        for i in xrange(LOOPCOUNT):
            if 'omp single private(nr_threads_in_single)':
                nr_threads_in_single = 0
                'omp flush'
                nr_threads_in_single += 1
                'omp flush'
                myit += 1
                myresult += nr_threads_in_single
        if 'omp critical':
            result += nr_threads_in_single
            nr_iterations += myit

    return result == 0 and nr_iterations == LOOPCOUNT

########NEW FILE########
__FILENAME__ = omp_task
def omp_task():
    import omp
    from time import sleep
    NUM_TASKS = 25
    tids = range(NUM_TASKS)

    if 'omp parallel':
        for i in xrange(NUM_TASKS):
            myi = i
            if 'omp task':
                sleep(0.01)
                tids[myi] = omp.get_thread_num()
    for i in xrange(NUM_TASKS):
        if tids[0] != tids[i]:
            return True

    return False

########NEW FILE########
__FILENAME__ = omp_taskwait
def omp_taskwait():
    from time import sleep
    result1 = 0
    result2 = 0
    NUM_TASKS = 25
    array = [0 for _ in range(NUM_TASKS)]

    if 'omp parallel':
        if 'omp single':
            for i in xrange(NUM_TASKS):
                myi = i
                if 'omp task firstprivate(myi)':
                    sleep(0.01)
                    array[myi] = 1

            'omp taskwait'

            for i in xrange(NUM_TASKS):
                if array[i] != 1:
                    result1 += 1

            for i in xrange(NUM_TASKS):
                myi = i
                if 'omp task firstprivate(myi)':
                    array[myi] = 2

    for i in xrange(NUM_TASKS):
        if array[i] != 2:
            result2 += 1

    return result1 == 0 and result2 == 0

########NEW FILE########
__FILENAME__ = omp_taskyield
def omp_taskyield():
    import omp
    from time import sleep
    NUM_TASKS = 25
    count = 0
    start_id = [0 for _ in xrange(NUM_TASKS)]
    current_id = [0 for _ in xrange(NUM_TASKS)]

    if 'omp parallel':
        if 'omp single':
            for i in xrange(NUM_TASKS):
                myi = i
                if 'omp task firstprivate(myi) untied':
                    sleep(0.01)
                    start_id[myi] = omp.get_thread_num()

                    'omp taskyield'

                    if start_id[myi] % 2 == 0:
                        sleep(0.01)
                        current_id[myi] = omp.get_thread_num()

    for i in xrange(NUM_TASKS):
        if current_id[i] == start_id[i]:
            count += 1

    return count < NUM_TASKS


########NEW FILE########
__FILENAME__ = omp_task_final
unittest.skip
#final semble ne pas fonctionner
def omp_task_final():
    import omp
    from time import sleep
    error = 0
    NUM_TASKS = 25
    tids = range(NUM_TASKS)

    if 'omp parallel':
        if 'omp single':
            for i in xrange(NUM_TASKS):
                myi = i
                if 'omp task final(i>=10) private(k) firstprivate(myi)':
                    sleep(0.01)
                    tids[myi] = omp.get_thread_num()
            'omp taskwait'

    for i in xrange(10, NUM_TASKS):
        if tids[10] != tids[i]:
            print i, tids[10], tids[i]
            error += 1

    print error
    return error == 0

########NEW FILE########
__FILENAME__ = omp_task_firstprivate
def omp_task_firstprivate():
    sum = 1234
    result = 0
    LOOPCOUNT = 1000
    NUM_TASKS = 25

    known_sum = 1234 + (LOOPCOUNT * (LOOPCOUNT + 1)) / 2

    if 'omp parallel':
        if 'omp single':
            for i in xrange(NUM_TASKS):
                if 'omp task firstprivate(sum)':
                    for j in xrange(LOOPCOUNT + 1):
                        'omp flush'
                        sum += j
                    if sum != known_sum:
                        if 'omp critical':
                            result += 1

    return result == 0

########NEW FILE########
__FILENAME__ = omp_task_if
def omp_task_if():
    from time import sleep
    count = 0
    condition_false = False
    result = False

    if 'omp parallel':
        if 'omp single':
            if 'omp task if(condition_false) shared(count, result)':
                sleep(0.5)
                result = (count == 0)

            count = 1

    return result

########NEW FILE########
__FILENAME__ = omp_task_imp_firstprivate
def omp_task_imp_firstprivate():
    i = 5
    k = 0
    result = 0
    NUM_TASKS = 25
    task_result = 1

    if 'omp parallel firstprivate(i)':
        if 'omp single':
            for k in xrange(NUM_TASKS):
                if 'omp task  shared(result, task_result)':
                    if i != 5:
                        task_result = 0

                    for j in xrange(0, NUM_TASKS):
                        i += 1
            'omp taskwait'
            result = task_result and i == 5
    return result

########NEW FILE########
__FILENAME__ = omp_task_private
def omp_task_private():
    sum = 0
    result = 0
    LOOPCOUNT = 1000
    NUM_TASKS = 25

    known_sum = (LOOPCOUNT * (LOOPCOUNT + 1)) / 2

    if 'omp parallel':
        if 'omp single':
            for i in xrange(0, NUM_TASKS):
                if 'omp task private(sum) shared(result, known_sum)':
                    sum = 0
                    for j in xrange(0, LOOPCOUNT + 1):
                        'omp flush'
                        sum += j
                    if sum != known_sum:
                        if 'omp critical':
                            result += 1
    return result == 0

########NEW FILE########
__FILENAME__ = omp_task_shared
def omp_task_shared():
    i = 0
    k = 0
    result = 0
    NUM_TASKS = 25

    if 'omp parallel':
        if 'omp single':
            for k in xrange(0, NUM_TASKS):
                if 'omp task shared(i)':
                    'omp atomic'
                    i += 1
    result = i
    return result == NUM_TASKS

########NEW FILE########
__FILENAME__ = omp_task_untied
def omp_task_untied():
    import omp
    from time import sleep
    NUM_TASKS = 25
    start_id = [0 for _ in xrange(NUM_TASKS)]
    current_id = [0 for _ in xrange(NUM_TASKS)]
    count = 0

    if 'omp parallel':
        if 'omp single':
            for i in xrange(NUM_TASKS):
                myi = i
                if 'omp task firstprivate(myi) untied':
                    sleep(0.01)
                    start_id[myi] = omp.get_thread_num()

                    'omp taskwait'

                    if start_id[myi] % 2 != 0:
                        sleep(0.01)
                        current_id[myi] = omp.get_thread_num()

    for i in xrange(NUM_TASKS):
        if current_id[i] == start_id[i]:
            count += 1

    return count < NUM_TASKS

########NEW FILE########
__FILENAME__ = 100doors
#from http://rosettacode.org/wiki/100_doors#Python
#pythran export unoptimized()
#runas unoptimized()
#pythran export optimized()
#runas optimized()
#pythran export one_liner_list_comprehension()
#runas one_liner_list_comprehension()
#pythran export one_liner_generator_comprehension()
#runas one_liner_generator_comprehension()

def unoptimized():
    doors = [False] * 100
    for i in xrange(100):
        for j in xrange(i, 100, i+1):
            doors[j] = not doors[j]
        print "Door %d:" % (i+1), 'open' if doors[i] else 'close'

def optimized():
    for i in xrange(1, 101):
        root = i ** 0.5
        print "Door %d:" % i, 'open' if root == int(root) else 'close'

def one_liner_list_comprehension():
    print '\n'.join(['Door %s is %s' % (i, ['closed', 'open'][(i**0.5).is_integer()]) for i in xrange(1, 10001)])

def one_liner_generator_comprehension():
    print '\n'.join('Door %s is %s' % (i, 'closed' if i**0.5 % 1 else 'open') for i in range(1, 101))

########NEW FILE########
__FILENAME__ = ackermann
#from http://rosettacode.org/wiki/Ackermann_function#Python
#pythran export ack1(int, int)
#pythran export ack2(int, int)
#pythran export ack3(int, int)
#runas ack1(2, 2)
#runas ack2(2, 1)
#runas ack3(1, 2)

def ack1(M, N):
   return (N + 1) if M == 0 else (
         ack1(M-1, 1) if N == 0 else ack1(M-1, ack1(M, N-1)))


def ack2(M, N):
    if M == 0:
        return N + 1
    elif N == 0:
        return ack1(M - 1, 1)
    else:
        return ack1(M - 1, ack1(M, N - 1))


def ack3(M, N):
   return (N + 1)   if M == 0 else (
          (N + 2)   if M == 1 else (
          (2*N + 3) if M == 2 else (
          (8*(2**N - 1) + 5) if M == 3 else (
          ack2(M-1, 1) if N == 0 else ack2(M-1, ack2(M, N-1))))))

########NEW FILE########
__FILENAME__ = appolonius
import math
#from http://rosettacode.org/wiki/Problem_of_Apollonius#Python
#pythran export solveApollonius((float, float, float), (float, float, float), (float, float, float), int, int, int)
#runas c1, c2, c3 = (0., 0., 1.), (4., 0., 1.), (2., 4., 2.); solveApollonius(c1, c2, c3, 1, 1, 1)
#runas c1, c2, c3 = (0., 0., 1.), (4., 0., 1.), (2., 4., 2.); solveApollonius(c1, c2, c3, -1, -1, -1)

def solveApollonius(c1, c2, c3, s1, s2, s3):
    '''
    >>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), 1,1,1)
    >>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), -1,-1,-1)
    '''
    x1, y1, r1 = c1
    x2, y2, r2 = c2
    x3, y3, r3 = c3

    v11 = 2*x2 - 2*x1
    v12 = 2*y2 - 2*y1
    v13 = x1*x1 - x2*x2 + y1*y1 - y2*y2 - r1*r1 + r2*r2
    v14 = 2*s2*r2 - 2*s1*r1

    v21 = 2*x3 - 2*x2
    v22 = 2*y3 - 2*y2
    v23 = x2*x2 - x3*x3 + y2*y2 - y3*y3 - r2*r2 + r3*r3
    v24 = 2*s3*r3 - 2*s2*r2

    w12 = v12/v11
    w13 = v13/v11
    w14 = v14/v11

    w22 = v22/v21-w12
    w23 = v23/v21-w13
    w24 = v24/v21-w14

    P = -w23/w22
    Q = w24/w22
    M = -w12*P-w13
    N = w14 - w12*Q

    a = N*N + Q*Q - 1
    b = 2*M*N - 2*N*x1 + 2*P*Q - 2*Q*y1 + 2*s1*r1
    c = x1*x1 + M*M - 2*M*x1 + P*P + y1*y1 - 2*P*y1 - r1*r1

# Find a root of a quadratic equation. This requires the circle centers not to be e.g. colinear
    D = b*b-4*a*c
    rs = (-b-math.sqrt(D))/(2*a)

    xs = M+N*rs
    ys = P+Q*rs

    return (xs, ys, rs)

########NEW FILE########
__FILENAME__ = array_concatenation
#from http://rosettacode.org/wiki/Array_concatenation#Python
#pythran export array_concatenation(int list, int list, int list, int list, int list)
#runas arr1 = [1, 2, 3]; arr2 = [4, 5, 6]; arr3 = [7, 8, 9]; arr5 = [4, 5, 6]; arr6 = [7, 8, 9]; array_concatenation(arr1, arr2, arr3, arr5, arr6)

def array_concatenation(arr1, arr2, arr3, arr5, arr6):
    arr4 = arr1 + arr2
    assert arr4 == [1, 2, 3, 4, 5, 6]
    arr4.extend(arr3)
    assert arr4 == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    arr6 += arr5
    assert arr6 == [7, 8, 9, 4, 5, 6]

########NEW FILE########
__FILENAME__ = average_loop_length
#from http://rosettacode.org/wiki/Average_loop_length#Python
#pythran export analytical(int)
#pythran export testing(int, int)
#runas analytical(10)
#runas avg = testing(10, 10**5); theory = analytical(10); abs((avg / theory - 1) * 100) < 0.1

#from __future__ import division # Only necessary for Python 2.X
from math import factorial
from random import randrange

def analytical(n):
	return sum(factorial(n) / pow(n, i) / float(factorial(n -i)) for i in range(1, n+1))

def testing(n, times):
    count = 0
    for i in range(times):
        x, bits = 1, 0
        while not (bits & x):
            count += 1
            bits |= x
            x = 1 << randrange(n)
    return count / times

########NEW FILE########
__FILENAME__ = exponential
#from http://rosettacode.org/wiki/Generator/Exponential#Python
#pythran export test(int, int)
#runas test(2, 3)

#FIXME unittest.skip

from itertools import islice, count

def powers(m):
    for n in count():
        yield n ** m

def filtered(s1, s2):
    v, f = next(s1), next(s2)
    while True:
        if v > f:
            f = next(s2)
            continue
        elif v < f:
            yield v
        v = next(s1)

def test(sq, cu):
    squares, cubes = powers(sq), powers(cu)
    f = filtered(squares, cubes)
    return list(islice(f, 20, 30))

########NEW FILE########
__FILENAME__ = gamma_function
#from http://rosettacode.org/wiki/Gamma_function#Python
#pythran export test(int)
#FIXME unittest.skip
#runas test(11)

def test(end):
    _a =    [ 1.00000000000000000000, 0.57721566490153286061, -0.65587807152025388108,
             -0.04200263503409523553, 0.16653861138229148950, -0.04219773455554433675,
             -0.00962197152787697356, 0.00721894324666309954, -0.00116516759185906511,
             -0.00021524167411495097, 0.00012805028238811619, -0.00002013485478078824,
             -0.00000125049348214267, 0.00000113302723198170, -0.00000020563384169776,
              0.00000000611609510448, 0.00000000500200764447, -0.00000000118127457049,
              0.00000000010434267117, 0.00000000000778226344, -0.00000000000369680562,
              0.00000000000051003703, -0.00000000000002058326, -0.00000000000000534812,
              0.00000000000000122678, -0.00000000000000011813, 0.00000000000000000119,
              0.00000000000000000141, -0.00000000000000000023, 0.00000000000000000002
           ]
    def gamma (x):
       y  = float(x) - 1.0;
       sm = _a[-1];
       for an in _a[-2::-1]:
          sm = sm * y + an;
       return 1.0 / sm;

    return [ gamma(i/3.0) for i in range(1,end)]

########NEW FILE########
__FILENAME__ = generic_swap
#from http://rosettacode.org/wiki/Generic_swap#Python
#pythran export swap(str, int)
#runas swap("e", 15)

def swap(a, b):
    return b, a

########NEW FILE########
__FILENAME__ = gray_code
#from http://rosettacode.org/wiki/Gray_code
#pythran export bin2gray(int list)
#pythran export gray2bin(int list)
#pythran export int2bin(int)
#pythran export bin2int(int list)
#runas [int2bin(i) for i in xrange(16)]
#runas [bin2gray(int2bin(i)) for i in xrange(16)]
#runas [gray2bin(bin2gray(int2bin(i))) for i in xrange(16)]
#runas [bin2int(gray2bin(bin2gray(int2bin(i)))) for i in xrange(16)]

def bin2gray(bits):
    return bits[:1] + [i ^ ishift for i, ishift in zip(bits[:-1], bits[1:])]

def gray2bin(bits):
    b = [bits[0]]
    for nextb in bits[1:]: b.append(b[-1] ^ nextb)
    return b


def int2bin(n):
    'From positive integer to list of binary bits, msb at index 0'
    if n:
        bits = []
        while n:
            n,remainder = divmod(n, 2)
            bits.insert(0, remainder)
        return bits
    else: return [0]


def bin2int(bits):
    'From binary bits, msb at index 0 to integer'
    i = 0
    for bit in bits:
        i = i * 2 + bit
    return i

########NEW FILE########
__FILENAME__ = greatest_common_divisor
#from http://rosettacode.org/wiki/Greatest_common_divisor#Python
#pythran export gcd_iter(int, int)
#pythran export gcd(int, int)
#pythran export gcd_bin(int, int)
#runas gcd_iter(40902, 24140)
#runas gcd(40902, 24140)
#runas gcd_bin(40902, 24140)

def gcd_iter(u, v):
    while v:
        u, v = v, u % v
    return abs(u)

def gcd(u, v):
    return gcd(v, u % v) if v else abs(u)

def gcd_bin(u, v):
    u, v = abs(u), abs(v) # u >= 0, v >= 0
    if u < v:
        u, v = v, u # u >= v >= 0
    if v == 0:
        return u

    # u >= v > 0
    k = 1
    while u & 1 == 0 and v & 1 == 0: # u, v - even
        u >>= 1; v >>= 1
        k <<= 1

    t = -v if u & 1 else u
    while t:
        while t & 1 == 0:
            t >>= 1
        if t > 0:
            u = t
        else:
            v = -t
        t = u - v
    return u * k

########NEW FILE########
__FILENAME__ = greatest_element_of_a_list
#from http://rosettacode.org/wiki/Greatest_element_of_a_list#Python
#pythran export test(str list)
#runas test(['1\n', ' 2.3\n', '4.5e-1\n', '0.01e4\n', '-1.2'])
#FIXME unittest.skip

def test(floatstrings):
    return max(float(x) for x in floatstrings)

########NEW FILE########
__FILENAME__ = greatest_subsequential_sum
#from http://rosettacode.org/wiki/Greatest_subsequential_sum#Python
#pythran export maxsum(int list)
#pythran export maxsumseq(int list)
#pythran export maxsumit(int list)
#runas maxsum([0, 1, 0])
#runas maxsumseq([-1, 2, -1, 3, -1])
#runas maxsumit([-1, 1, 2, -5, -6])

def maxsum(sequence):
    """Return maximum sum."""
    maxsofar, maxendinghere = 0, 0
    for x in sequence:
        # invariant: ``maxendinghere`` and ``maxsofar`` are accurate for ``x[0..i-1]``          
        maxendinghere = max(maxendinghere + x, 0)
        maxsofar = max(maxsofar, maxendinghere)
    return maxsofar


def maxsumseq(sequence):
    start, end, sum_start = -1, -1, -1
    maxsum_, sum_ = 0, 0
    for i, x in enumerate(sequence):
        sum_ += x
        if maxsum_ < sum_: # found maximal subsequence so far
            maxsum_ = sum_
            start, end = sum_start, i
        elif sum_ < 0: # start new sequence
            sum_ = 0
            sum_start = i
    assert maxsum_ == maxsum(sequence)
    assert maxsum_ == sum(sequence[start + 1:end + 1])
    return sequence[start + 1:end + 1]


def maxsumit(iterable):
    maxseq = seq = []
    start, end, sum_start = -1, -1, -1
    maxsum_, sum_ = 0, 0
    for i, x in enumerate(iterable):
        seq.append(x); sum_ += x
        if maxsum_ < sum_:
            maxseq = seq; maxsum_ = sum_
            start, end = sum_start, i
        elif sum_ < 0:
            seq = []; sum_ = 0
            sum_start = i
    assert maxsum_ == sum(maxseq[:end - start])
    return maxseq[:end - start]

########NEW FILE########
__FILENAME__ = hailstone_sequence
#from http://rosettacode.org/wiki/Hailstone_sequence#Python
#pythran export hailstone(int)
#runas hailstone(27)
#runas max((len(hailstone(i)), i) for i in range(1,100000))

def hailstone(n):
    seq = [n]
    while n>1:
        n = 3*n + 1 if n & 1 else n//2
        seq.append(n)
    return seq

########NEW FILE########
__FILENAME__ = hamming_numbers
#from http://rosettacode.org/wiki/Hamming_numbers#Python
#pythran export test(int, int)
#runas test(20, 1690)
#FIXME unittest.skip
from itertools import islice

def hamming2():
    '''\
    This version is based on a snippet from:
        http://dobbscodetalk.com/index.php?option=com_content&task=view&id=913&Itemid=85
 
        When expressed in some imaginary pseudo-C with automatic
        unlimited storage allocation and BIGNUM arithmetics, it can be
        expressed as:
            hamming = h where
              array h;
              n=0; h[0]=1; i=0; j=0; k=0;
              x2=2*h[ i ]; x3=3*h[j]; x5=5*h[k];
              repeat:
                h[++n] = min(x2,x3,x5);
                if (x2==h[n]) { x2=2*h[++i]; }
                if (x3==h[n]) { x3=3*h[++j]; }
                if (x5==h[n]) { x5=5*h[++k]; } 
    '''
    h = 1
    _h=[h]    # memoized
    multipliers  = [2, 3, 5]
    multindeces  = [0 for i in multipliers] # index into _h for multipliers
    multvalues   = [x * _h[i] for x,i in zip(multipliers, multindeces)]
    yield h
    while True:
        h = min(multvalues)
        _h.append(h)
        for (n,(v,x,i)) in enumerate(zip(multvalues, multipliers, multindeces)):
            if v == h:
                i += 1
                multindeces[n] = i
                multvalues[n]  = x * _h[i]
        # cap the memoization
        mini = min(multindeces)
        if mini >= 1000:
            del _h[:mini]
            multindeces = [i - mini for i in multindeces]
        #
        yield h

def test(v1, v2):
    return list(islice(hamming2(), v1)), list(islice(hamming2(), v2, v2 + 1))

########NEW FILE########
__FILENAME__ = happy_numbers
#from http://rosettacode.org/wiki/Happy_numbers#Python
#pythran export happy(int)
#runas [x for x in xrange(500) if happy(x)][:8]

def happy(n):
    past = set()
    while n <> 1:
        n = sum(int(i)**2 for i in str(n))
        if n in past:
            return False
        past.add(n)
    return True

########NEW FILE########
__FILENAME__ = harshad_or_niven_series
#from http://rosettacode.org/wiki/Harshad_or_Niven_series#Python
#pythran export test()
#runas test()
#FIXME unittest.skip

import itertools
def harshad():
    for n in itertools.count(1):
        if n % sum(int(ch) for ch in str(n)) == 0:
            yield n

def test():
    l = list(itertools.islice(harshad(), 0, 20))
    for n in harshad():
        if n > 1000:
            r = n
            break

    from itertools import count, islice
    harshad_ = (n for n in count(1) if n % sum(int(ch) for ch in str(n)) == 0)
    l2 = list(islice(harshad_, 0, 20))
    r2  = next(x for x in harshad_ if x > 1000)
    return r,l, r2, l2

########NEW FILE########
__FILENAME__ = palindrome
#from http://rosettacode.org/wiki/Palindrome_detection#Python
#pythran export test()
#runas test()

def is_palindrome(s):
    return s == s[::-1]

def is_palindrome_r2(s):
    return not s or s[0] == s[-1] and is_palindrome_r2(s[1:-1])

def is_palindrome_r(s):
    if len(s) <= 1:
        return True
    elif s[0] != s[-1]:
        return False
    else:
        return is_palindrome_r(s[1:-1])

def test_(f, good, bad):
    if all(f(x) for x in good) and not any(f(x) for x in bad):
        print 'function passed all %d tests' % (len(good)+len(bad))

def test():
    pals = ['', 'a', 'aa', 'aba', 'abba']
    notpals = ['aA', 'abA', 'abxBa', 'abxxBa']
    test_(is_palindrome, pals, notpals)
    test_(is_palindrome_r, pals, notpals)
    test_(is_palindrome_r2, pals, notpals)

########NEW FILE########
__FILENAME__ = pangram
#from http://rosettacode.org/wiki/Pangram_checker#Python
#pythran export ispangram(str)
#runas ispangram("The quick brown fox jumps over the lazy dog")
#runas ispangram("The brown fox jumps over the lazy dog")

import string

def ispangram(sentence, alphabet=string.ascii_lowercase):
    alphaset = set(alphabet)
    return alphaset <= set(sentence.lower())

########NEW FILE########
__FILENAME__ = pascal
#from http://rosettacode.org/wiki/Pascal%27s_triangle#Python
#pythran export pascal(int)
#pythran export pascal_(int)
#runas pascal(10)
#runas pascal_(10)

def pascal(n):
    """Prints out n rows of Pascal's triangle.
    It returns False for failure and True for success."""
    row = [1]
    k = [0]
    for x in range(max(n,0)):
        print row
        row=[l+r for l,r in zip(row+k,k+row)]
    return n>=1

def scan(op, seq, it):
    a = []
    result = it
    a.append(it)
    for x in seq:
        result = op(result, x)
        a.append(result)
    return a

def pascal_(n):
    def nextrow(row, x):
        return [l+r for l,r in zip(row+[0,],[0,]+row)]
    return scan(nextrow, range(n-1), [1,])

########NEW FILE########
__FILENAME__ = perf
#from http://rosettacode.org/wiki/Perfect_numbers#Python
#pythran export perf(int)
#pythran export perf_(int)
#runas map(perf, range(20))
#runas map(perf_, range(20))

def perf(n):
    sum = 0
    for i in xrange(1, n):
        if n % i == 0:
            sum += i
    return sum == n

def perf_(n):
    return n == sum(i for i in xrange(1, n) if n % i == 0)

########NEW FILE########
__FILENAME__ = permutations
#from http://rosettacode.org/wiki/Permutations#Python
#pythran export test(int)
#runas test(3)

def test(n):
    import itertools
    return [values for values in itertools.permutations(range(1, n + 1))]

########NEW FILE########
__FILENAME__ = permutation_derangement
#from http://rosettacode.org/wiki/Permutations/Derangements#Python
from itertools import permutations
import math

#pythran export test(int, int, int)
#runas test(4, 10, 20)

def derangements(n):
    'All deranged permutations of the integers 0..n-1 inclusive'
    return ( perm for perm in permutations(range(n))
             if all(indx != p for indx, p in enumerate(perm)) )

def subfact(n):
    if n == 2 or n == 0:
        return 1
    elif n == 1:
        return 0
    elif  1 <= n <=18:
        return round(math.factorial(n) / math.e)
    elif n.imag == 0 and n.real == int(n.real) and n > 0:
        return (n-1) * ( subfact(n - 1) + subfact(n - 2) )
    else:
        raise ValueError()

def _iterlen(iter):
    'length of an iterator without taking much memory'
    l = 0
    for x in iter:
        l += 1
    return l

def test(n1, n2, n3):
    print("Derangements of %s" % range(n1))
    for d in derangements(n1):
        print("  %s" % (d,))
    print("\nTable of n vs counted vs calculated derangements")
    for n in range(n2):
        print("%2i %-5i %-5i" %
              (n, _iterlen(derangements(n)), subfact(n)))
    print("\n!%i = %i" % (n3, subfact(n3)))

########NEW FILE########
__FILENAME__ = permutation_rank
#from http://rosettacode.org/wiki/Permutations/Rank_of_a_permutation#Python
#pythran export test()
#runas test()
from math import factorial as fact
from random import randrange

def identity_perm(n):
    return list(range(n))

def unranker1(n, r, pi):
    while n > 0:
        n1, (rdivn, rmodn) = n-1, divmod(r, n)
        pi[n1], pi[rmodn] = pi[rmodn], pi[n1]
        n = n1
        r = rdivn
    return pi

def init_pi1(n, pi):
    pi1 = [-1] * n
    for i in range(n):
        pi1[pi[i]] = i
    return pi1

def ranker1(n, pi, pi1):
    if n == 1:
        return 0
    n1 = n-1
    s = pi[n1]
    pi[n1], pi[pi1[n1]] = pi[pi1[n1]], pi[n1]
    pi1[s], pi1[n1] = pi1[n1], pi1[s]
    return s + n * ranker1(n1, pi, pi1)

def unranker2(n, r, pi):
    while n > 0:
        n1 = n-1
        s, rmodf = divmod(r, fact(n1))
        pi[n1], pi[s] = pi[s], pi[n1]
        n = n1
        r = rmodf
    return pi

def ranker2(n, pi, pi1):
    if n == 1:
        return 0
    n1 = n-1
    s = pi[n1]
    pi[n1], pi[pi1[n1]] = pi[pi1[n1]], pi[n1]
    pi1[s], pi1[n1] = pi1[n1], pi1[s]
    return s * fact(n1) + ranker2(n1, pi, pi1)

def get_random_ranks(permsize, samplesize):
    perms = fact(permsize)
    ranks = set()
    while len(ranks) < samplesize:
        ranks |= set( randrange(perms)
                      for r in range(samplesize - len(ranks)) )
    return ranks

def test1(comment, unranker, ranker):
    n, samplesize, n2 = 3, 4, 12
    print(comment)
    perms = []
    for r in range(fact(n)):
        pi = identity_perm(n)
        perm = unranker(n, r, pi)
        perms.append((r, perm))
    for r, pi in perms:
        pi1 = init_pi1(n, pi)
        print('  From rank %s to %s back to %s' % (r, pi, ranker(n, pi[:], pi1)))
    print('\n  %s random individual samples of %s items:' % (samplesize, n2))
    for r in get_random_ranks(n2, samplesize):
        pi = identity_perm(n2)
        print('    ' + ' '.join('%s' % i for i in unranker(n2, r, pi)))
    print('')

def test2(comment, unranker):
    samplesize, n2 = 4, 20
    print(comment)
    print('  %s random individual samples of %s items:' % (samplesize, n2))
    txt = ''
    for r in get_random_ranks(n2, samplesize):
        pi = identity_perm(n2)
        txt += '\n' + ''.join(str(unranker(n2, r, pi)))
    print(txt, '')

def test():
    test1('First ordering:', unranker1, ranker1)
    test1('Second ordering:', unranker2, ranker2)
    test2('First ordering, large number of perms:', unranker1)

########NEW FILE########
__FILENAME__ = permutation_swap
#from http://rosettacode.org/wiki/Permutations_by_swapping#Python
#pythran export test()
#runas test()
#unittest.skip requires two-step typing

def s_permutations(seq):
    items = [[]]
    for j in seq:
        new_items = []
        for i, item in enumerate(items):
            if i % 2:
                # step up
                new_items += [item[:i] + [j] + item[i:]
                    for i in range(len(item) + 1)]
            else:
                # step down
                new_items += [item[:i] + [j] + item[i:]
                    for i in range(len(item), -1, -1)]
        items = new_items

    return [(tuple(item), -1 if i % 2 else 1)
        for i, item in enumerate(items)]

def test():
    for n in (3, 4):
        print '\nPermutations and sign of %i items' % n
        for i in s_permutations(range(n)):
            print 'Perm: ', i

########NEW FILE########
__FILENAME__ = permutation_test
#from http://rosettacode.org/wiki/Permutation_test#Python
#pythran export permutationTest(int list, int list)
#pythran export permutationTest2(int list, int list)
#runas permutationTest([85, 88, 75, 66, 25, 29, 83, 39, 97], [68, 41, 10, 49, 16, 65, 32, 92, 28, 98])
#runas permutationTest2([85, 88, 75, 66, 25, 29, 83, 39, 97], [68, 41, 10, 49, 16, 65, 32, 92, 28, 98])
from itertools import combinations as comb

def statistic(ab, a):
    sumab, suma = sum(ab), sum(a)
    return ( suma / len(a) - (sumab -suma) / (len(ab) - len(a)) )

def permutationTest(a, b):
    ab = a + b
    Tobs = statistic(ab, a)
    under = 0
    for count, perm in enumerate(comb(ab, len(a)), 1):
        if statistic(ab, perm) <= Tobs:
            under += 1
    return under * 100. / count

def permutationTest2(a, b):
    ab = a + b
    Tobs = sum(a)
    under = 0
    for count, perm in enumerate(comb(ab, len(a)), 1):
        if sum(perm) <= Tobs:
            under += 1
    return under * 100. / count

########NEW FILE########
__FILENAME__ = pi
#from http://rosettacode.org/wiki/Pi#Python
#pythran export test()
#runas test()
#FIXME unittest.skip

def calcPi():
    q, r, t, k, n, l = 1, 0, 1, 1, 3, 3
    while True:
        if 4*q+r-t < n*t:
            yield n
            nr = 10*(r-n*t)
            n  = ((10*(3*q+r))//t)-10*n
            q  *= 10
            r  = nr
        else:
            nr = (2*q+r)*l
            nn = (q*(7*k)+2+(r*l))//(t*l)
            q  *= k
            t  *= l
            l  += 2
            k += 1
            n  = nn
            r  = nr

def test():
    pi_digits = calcPi()
    res = list()
    for i, d in enumerate(pi_digits):
        res.append(str(d))
        if i>50:
            return res

########NEW FILE########
__FILENAME__ = pick
#from http://rosettacode.org/wiki/Pick_random_element#Python
#pythran export test()
#runas test()

def test():
    import random
    res = {"foo":0, "bar":0, "baz":0}
    for i in xrange(500):
        res[random.choice(res.keys())] += 1
    return res

########NEW FILE########
__FILENAME__ = poly_div
#from http://rosettacode.org/wiki/Polynomial_long_division#Python
from itertools import izip
from math import fabs

#pythran export poly_div(int list, int list)
#runas poly_div([-42, 0, -12, 1], [-3, 1, 0, 0])

def degree(poly):
    while poly and poly[-1] == 0:
        poly.pop()   # normalize
    return len(poly)-1

def poly_div(N, D):
    dD = degree(D)
    dN = degree(N)
    if dD < 0: raise ZeroDivisionError
    if dN >= dD:
        q = [0] * dN
        while dN >= dD:
            d = [0]*(dN - dD) + D
            mult = q[dN - dD] = N[-1] / float(d[-1])
            d = [coeff*mult for coeff in d]
            N = [fabs ( coeffN - coeffd ) for coeffN, coeffd in izip(N, d)]
            dN = degree(N)
        r = N
    else:
        q = [0]
        r = N
    return q, r

########NEW FILE########
__FILENAME__ = power_set
#from http://rosettacode.org/wiki/Power_set#Python
#pythran export p(int list)
#pythran export list_powerset(int list)
#pythran export list_powerset2(int list)
#runas p([1,2,3])
#runas list_powerset([1,2,3])
#runas list_powerset2([1,2,3])


def list_powerset(lst):
    # the power set of the empty set has one element, the empty set
    result = [[]]
    for x in lst:
        # for every additional element in our set
        # the power set consists of the subsets that don't
        # contain this element (just take the previous power set)
        # plus the subsets that do contain the element (use list
        # comprehension to add [x] onto everything in the
        # previous power set)
        result.extend([subset + [x] for subset in result])
    return result

# the above function in one statement
def list_powerset2(lst):
    return reduce(lambda result, x: result + [subset + [x] for subset in result],
            lst, [[]])

def p(l):
    if not l: return [[]]
    return p(l[1:]) + [[l[0]] + x for x in p(l[1:])]

########NEW FILE########
__FILENAME__ = price_fraction
#from http://rosettacode.org/wiki/Price_fraction#Python
#pythran export pricerounder(float)
#runas map(pricerounder, [0.3793, 0.4425, 0.0746, 0.6918, 0.2993, 0.5486, 0.7848, 0.9383, 0.2292, 0.9560])

import bisect
def pricerounder(pricein):
    _cout = [.10, .18, .26, .32, .38, .44, .50, .54, .58, .62, .66, .70, .74, .78, .82, .86, .90, .94, .98, 1.00]
    _cin  = [.06, .11, .16, .21, .26, .31, .36, .41, .46, .51, .56, .61, .66, .71, .76, .81, .86, .91, .96, 1.01]
    return _cout[ bisect.bisect_right(_cin, pricein) ]

########NEW FILE########
__FILENAME__ = primality
#from http://rosettacode.org/wiki/Primality_by_trial_division#Python
#pythran exprot test()
#runas test()
#FIXME unittest.skip

def prime(a):
    return not (a < 2 or any(a % x == 0 for x in xrange(2, int(a**0.5) + 1)))

def prime2(a):
    if a == 2: return True
    if a < 2 or a % 2 == 0: return False
    return not any(a % x == 0 for x in xrange(3, int(a**0.5) + 1, 2))

def prime3(a):
    if a < 2: return False
    if a == 2 or a == 3: return True # manually test 2 and 3   
    if a % 2 == 0 or a % 3 == 0: return False # exclude multiples of 2 and 3

    maxDivisor = a**0.5
    d, i = 5, 2
    while d <= maxDivisor:
        if a % d == 0: return False
        d += i
        i = 6 - i # this modifies 2 into 4 and viceversa

    return True

def test():
    return [i for i in range(40) if prime(i)], [i for i in range(40) if prime2(i)], [i for i in range(40) if prime3(i)]

########NEW FILE########
__FILENAME__ = prime_decomposition
#from http://rosettacode.org/wiki/Prime_decomposition#Python
#pythran export fac(int)
#runas fac(2**59 - 1)
#pythran export test_decompose(int)
#runas test_decompose(2**59 - 1)
import math

def decompose(n):
    primelist = [2, 3]
    for p in primes(primelist):
        if p*p > n: break
        while n % p == 0:
            yield p
            n /=p
    if n > 1:
        yield n

def test_decompose(to):
    return [i for i in decompose(to)]

def primes(primelist):
    for n in primelist: yield n

    n = primelist[-1]
    while True:
        n += 2
        for x in primelist:
            if not n % x: break
            if x * x > n:
                primelist.append(n)
                yield n
                break

def fac(n):
    step = lambda x: 1 + x*4 - (x/2)*2
    maxq = long(math.floor(math.sqrt(n)))
    d = 1
    q = n % 2 == 0 and 2 or 3
    while q <= maxq and n % q != 0:
        q = step(d)
        d += 1
    res = []
    if q <= maxq:
        res.extend(fac(n//q))
        res.extend(fac(q))
    else: res=[n]
    return res

########NEW FILE########
__FILENAME__ = proba_choice
#from http://rosettacode.org/wiki/Probabilistic_choice#Python
#pythran export test()
#runas test()

import random, bisect

def probchoice(items, probs, bincount=1000):
    '''
    Splits the interval 0.0-1.0 in proportion to probs
    then finds where each random.random() choice lies
    '''

    prob_accumulator = 0
    accumulator = []
    for p in probs:
        prob_accumulator += p
        accumulator.append(prob_accumulator)

    while True:
        r = random.random()
        yield items[bisect.bisect(accumulator, r)]

def probchoice2(items, probs, bincount=1000):
    '''
    Puts items in bins in proportion to probs
    then uses random.choice() to select items.

    Larger bincount for more memory use but
    higher accuracy (on avarage).
    '''

    bins = []
    for item,prob in zip(items, probs):
        bins += [item]*int(bincount*prob)
    while True:
        yield random.choice(bins)


def tester(func=probchoice, items='good bad ugly'.split(),
        probs=[0.5, 0.3, 0.2],
        trials = 100000
        ):
    def problist2string(probs):
        '''
        Turns a list of probabilities into a string
        Also rounds FP values
        '''
        return ",".join('%8.6f' % (p,) for p in probs)

    counter = dict()
    it = func(items, probs)
    for dummy in xrange(trials):
        k = it.next()
        if k in counter:
            counter[k] += 1
        else:
            counter[k] = 1
    print "\n##\n##\n##"
    print "Trials:              ", trials
    print "Items:               ", ' '.join(items)
    print "Target probability:  ", problist2string(probs)
    print "Attained probability:", problist2string(
        counter[x]/float(trials) for x in items)

def test():
    items = 'aleph beth gimel daleth he waw zayin heth'.split()
    probs = [1/(float(n)+5) for n in range(len(items))]
    probs[-1] = 1-sum(probs[:-1])
    tester(probchoice, items, probs, 1000000)
    tester(probchoice2, items, probs, 1000000)

########NEW FILE########
__FILENAME__ = pythagor_triples
#from http://rosettacode.org/wiki/Pythagorean_triples#Python
#pythran export triples(int)
#runas triples(10)
#runas triples(100)
#runas triples(1000)
#runas triples(10000)
#runas triples(100000)

def triples(lim, a = 3, b = 4, c = 5):
    l = a + b + c
    if l > lim: return (0, 0)
    return reduce(lambda x, y: (x[0] + y[0], x[1] + y[1]), [
            (1, lim / l),
            triples(lim,  a - 2*b + 2*c,  2*a - b + 2*c,  2*a - 2*b + 3*c),
            triples(lim,  a + 2*b + 2*c,  2*a + b + 2*c,  2*a + 2*b + 3*c),
            triples(lim, -a + 2*b + 2*c, -2*a + b + 2*c, -2*a + 2*b + 3*c) ])

########NEW FILE########
__FILENAME__ = ramsey
#from http://rosettacode.org/wiki/Ramsey%27s_theorem#Python
#pythran export test()
#runas test()

def test():
    range17 =  range(17)
    a = [['0'] * 17 for i in range17]
    for i in range17:
        a[i][i] = '-'
    for k in range(4):
        for i in range17:
            j = (i + pow(2, k)) % 17
            a[i][j] = a[j][i] = '1'
    for row in a:
        print(' '.join(row))

########NEW FILE########
__FILENAME__ = rangeexpend
#from http://rosettacode.org/wiki/Range_expansion#Python
#pythran export rangeexpand(str)
#runas rangeexpand('-6,-3--1,3-5,7-11,14,15,17-20')

def rangeexpand(txt):
    lst = []
    for r in txt.split(','):
        if '-' in r[1:]:
            r0, r1 = r[1:].split('-', 1)
            lst += range(int(r[0] + r0), int(r1) + 1)
        else:
            lst.append(int(r))
    return lst

########NEW FILE########
__FILENAME__ = rangeextract
#from http://rosettacode.org/wiki/Range_extraction#Python
#pythran export test_range_extract(int list list)
#runas test_range_extract([[-8, -7, -6, -3, -2, -1, 0, 1, 3, 4, 5, 7, 8, 9, 10, 11, 14, 15, 17, 18, 19, 20], [0, 1, 2, 4, 6, 7, 8, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39]])

def range_extract(lst):
    'Yield 2-tuple ranges or 1-tuple single elements from list of increasing ints'
    lenlst = len(lst)
    i = 0
    while i< lenlst:
        low = lst[i]
        while i <lenlst-1 and lst[i]+1 == lst[i+1]: i +=1
        hi = lst[i]
        if   hi - low >= 2:
            yield [low, hi]
        elif hi - low == 1:
            yield [low]
            yield [hi]
        else:
            yield [low]
        i += 1

def test_range_extract(on):
    return [list(range_extract(i)) for i in on]

########NEW FILE########
__FILENAME__ = read_conf
#from http://rosettacode.org/wiki/Read_a_configuration_file#Python
#pythran export readconf(str)
#runas readconf("rosetta/read_conf.cfg")

def readconf(fn):
    ret = {}
    fp = file(fn)
    for line in fp:
        # Assume whitespace is ignorable
        line = line.strip()
        if not line or line.startswith('#'): continue

        boolval = "True"
        # Assume leading ";" means a false boolean
        if line.startswith(';'):
            # Remove one or more leading semicolons
            line = line.lstrip(';')
            # If more than just one word, not a valid boolean
            if len(line.split()) != 1: continue
            boolval = "False"

        bits = line.split(None, 1)
        if len(bits) == 1:
            # Assume booleans are just one standalone word
            k = bits[0]
            v = boolval
        else:
            # Assume more than one word is a string value
            k, v = bits
        ret[k.lower()] = v
    fp.close()
    return ret

########NEW FILE########
__FILENAME__ = read_file
#from http://rosettacode.org/wiki/Read_entire_file#Python
#pythran export readfile()
#runas readfile()

def readfile():
    return open("rosetta/read_conf.cfg").read()

########NEW FILE########
__FILENAME__ = read_line
#from http://rosettacode.org/wiki/Read_a_file_line_by_line#Python
#pythran export readfile()
#runas readfile()

def readfile():
    return [line for line in file("rosetta/read_conf.cfg")]

########NEW FILE########
__FILENAME__ = read_specific_line
#from http://rosettacode.org/wiki/Read_a_specific_line_from_a_file#Python
#pythran export readline(int)
#runas readline(6)

def readline(n):
    from itertools import islice

    f = open('rosetta/read_conf.cfg')
    linelist = list(islice(f, n, n + 1))
    assert linelist != [], 'Not ' + str(n) + ' lines in file'
    line = linelist[0]
    f.close()
    return line

########NEW FILE########
__FILENAME__ = real_const
#from http://rosettacode.org/wiki/Real_constants_and_functions#Python
#pythran export test()
#runas test()

def test():
    import math
    x = 3.5
    y = -0.2
    print math.e          # e
    print math.pi         # pi
    print math.sqrt(x)    # square root  (Also commonly seen as x ** 0.5 to obviate importing the math module)
    print math.log(x)     # natural logarithm
    print math.log10(x)   # base 10 logarithm
    print math.exp(x)     # e raised to the power of x
    print abs(x)          # absolute value
    print math.floor(x)   # floor
    print math.ceil(x)    # ceiling
    print x ** y          # exponentiation 
    print pow(x, y)

########NEW FILE########
__FILENAME__ = reduce_row_echelon
#from http://rosettacode.org/wiki/Reduced_row_echelon_form#Python
#pythran export ToReducedRowEchelonForm(int list list)
#runas mtx = [ [ 1, 2, -1, -4], [ 2, 3, -1, -11], [-2, 0, -3, 22],]; ToReducedRowEchelonForm(mtx)

def ToReducedRowEchelonForm( M):
    if not M: return
    lead = 0
    rowCount = len(M)
    columnCount = len(M[0])
    for r in range(rowCount):
        if lead >= columnCount:
            return
        i = r
        while M[i][lead] == 0:
            i += 1
            if i == rowCount:
                i = r
                lead += 1
                if columnCount == lead:
                    return
        M[i],M[r] = M[r],M[i]
        lv = M[r][lead]
        M[r] = [ mrx / lv for mrx in M[r]]
        for i in range(rowCount):
            if i != r:
                lv = M[i][lead]
                M[i] = [ iv - lv*rv for rv,iv in zip(M[r],M[i])]
        lead += 1

########NEW FILE########
__FILENAME__ = remove_duplicate
#from http://rosettacode.org/wiki/Remove_duplicate_elements#Python
#pythran export unique(int list)
#runas unique([1, 2, 3, 2, 3, 4])

def unique(items):
    return list(set(items))

########NEW FILE########
__FILENAME__ = repeat_string
#from http://rosettacode.org/wiki/Repeat_a_string
#pythran export test(int)
#runas test(5)

def test(n):
    return "ha" * n, n * "ha"

########NEW FILE########
__FILENAME__ = rep_string
#from http://rosettacode.org/wiki/Rep-string#Python
#pythran export is_repeated(str)
#pythran export reps(str)
#runas matchstr ="1001110011 1110111011 0010010010 1010101010 1111111111 0100101101 0100100 101 11 00 1"; [reps(i) for i in matchstr.split()]
#runas matchstr ="1001110011 1110111011 0010010010 1010101010 1111111111 0100101101 0100100 101 11 00 1"; [is_repeated(i) for i in matchstr.split()]

def is_repeated(text):
    'check if the first part of the string is repeated throughout the string'
    for x in range(len(text)//2, 0, -1):
        if text.startswith(text[x:]): return x
    return 0

def reps(text):
    return [text[:x] for x in range(1, 1 + len(text) // 2)
            if text.startswith(text[x:])]

########NEW FILE########
__FILENAME__ = return_multiple
#from http://rosettacode.org/wiki/Return_multiple_values
#pythran export addsub(int, int)
#runas addsub(33, 12)

def addsub(x, y):
    return x + y, x - y

########NEW FILE########
__FILENAME__ = roman_decode
#from http://rosettacode.org/wiki/Roman_numerals/Decode#Python
#pythran export decode(str)
#runas decode('MCMXC')
#runas decode('MMVIII')
#runas decode('MDCLXVI')

def decode( roman ):
    _rdecode = dict(zip('MDCLXVI', (1000, 500, 100, 50, 10, 5, 1)))
    result = 0
    for r, r1 in zip(roman, roman[1:]):
        rd, rd1 = _rdecode[r], _rdecode[r1]
        result += -rd if rd < rd1 else rd
    return result + _rdecode[roman[-1]]

########NEW FILE########
__FILENAME__ = yin_and_yang
# from http://rosettacode.org/wiki/Yin_and_yang#Python
#pythran export yinyang(int)
#runas yinyang(4)

import math
def yinyang(n=3):
        radii   = [i * n for i in [1, 3, 6]]
        ranges  = [list(range(-r, r+1)) for r in radii]
        squares = [[ (x,y) for x in rnge for y in rnge]
                   for rnge in ranges]
        circles = [[ (x,y) for x,y in sqrpoints
                     if math.hypot(x,y) <= radius ]
                   for sqrpoints, radius in zip(squares, radii)]
        m = {(x,y):' ' for x,y in squares[-1]}
        for x,y in circles[-1]:
                m[x,y] = '*'
        for x,y in circles[-1]:
                if x>0: m[(x,y)] = '.'
        for x,y in circles[-2]:
                m[(x,y+3*n)] = '*'
                m[(x,y-3*n)] = '.'
        for x,y in circles[-3]:
                m[(x,y+3*n)] = '.'
                m[(x,y-3*n)] = '*'
        return '\n'.join(''.join(m[(x,y)] for x in reversed(ranges[-1])) for y in ranges[-1])

########NEW FILE########
__FILENAME__ = zeckendorf_number_representation
#from http://rosettacode.org/wiki/Zeckendorf_number_representation#Python
#pythran export test(int)
#pythran export z(int)
#pythran export zeckendorf(int)
#runas test(20)
#runas ['%3i: %8s' % (i, ''.join(str(d) for d in zeckendorf(i))) for i in range(21)]
#runas ['%3i: %8s' % (i, ''.join(str(d) for d in z(i))) for i in range(21)]

def fib():
    memo = [1, 2]
    while True:
        memo.append(sum(memo))
        yield memo.pop(0)

def sequence_down_from_n(n, seq_generator):
    seq = []
    for s in seq_generator():
        seq.append(s)
        if s >= n: break
    return seq[::-1]

def zeckendorf(n):
    if n == 0: return [0]
    seq = sequence_down_from_n(n, fib)
    digits, nleft = [], n
    for s in seq:
        if s <= nleft:
            digits.append(1)
            nleft -= s
        else:
            digits.append(0)
    assert nleft == 0, 'Check all of n is accounted for'
    assert sum(x*y for x,y in zip(digits, seq)) == n, 'Assert digits are correct'
    while digits[0] == 0:
        # Remove any zeroes padding L.H.S.
        digits.pop(0)
    return digits

def z(n):
    if n == 0 : return [0]
    fib = [2,1]
    while fib[0] < n: fib[0:0] = [sum(fib[:2])]
    dig = []
    for f in fib:
        if f <= n:
            dig, n = dig + [1], n - f
        else:
            dig += [0]
    return dig if dig[0] else dig[1:]

def test(n):
    return sequence_down_from_n(n, fib)


########NEW FILE########
__FILENAME__ = zig_zag_matrix
#from http://rosettacode.org/wiki/Zig-zag_matrix#Python
#pythran export zigzag(int)
#pythran export czigzag(int)
#runas zigzag(5)
#runas czigzag(5)

def zigzag(n):
    def move(i, j):
        if j < (n - 1):
            return max(0, i-1), j+1
        else:
            return i+1, j
    a = [[0] * n for _ in xrange(n)]
    x, y = 0, 0
    for v in xrange(n * n):
        a[y][x] = v
        if (x + y) & 1:
            x, y = move(x, y)
        else:
            y, x = move(y, x)
    return a

def czigzag(COLS):
    def CX(x, ran):
      while True:
        x += 2 * next(ran)
        yield x
        x += 1
        yield x
    ran = []
    d = -1
    for V in CX(1,iter(list(range(0,COLS,2)) + list(range(COLS-1-COLS%2,0,-2)))):
      ran.append(iter(range(V, V+COLS*d, d)))
      d *= -1

    r=[]
    for x in range(0,COLS):
        t=[]
        for y in range(x, x+COLS):
            t.append(next(ran[y]))
        r.append(t)
    return r

########NEW FILE########
__FILENAME__ = test_advanced
from test_env import TestEnv
from unittest import skip

class TestAdvanced(TestEnv):

    def test_generator_enumeration(self):
        code = '''
def dummy_generator(l):
    for i in l: yield i
def generator_enumeration(begin, end):
    return [i for i in enumerate(dummy_generator(range(begin,end)))]'''
        self.run_test(code, 2, 10, generator_enumeration=[int, int])

    def test_augassign_floordiv(self):
        self.run_test("def augassign_floordiv(i,j): k=i ; k//=j; return k",
                2, 5, augassign_floordiv=[int, int])

    def test_builtin_constructors(self):
        self.run_test("def builtin_constructors(l): return map(int,l)",
                [1.5, 2.5], builtin_constructors=[[float]])

    def test_tuple_sum(self):
        self.run_test("def tuple_sum(tpl): return sum(tpl)", (1, 2, 3.5), tuple_sum=[(int, int, float)])

    def test_minus_unary_minus(self):
        self.run_test("def minus_unary_minus(a): return a - -1", 1, minus_unary_minus=[int])

    def test_bool_op_casting(self):
        self.run_test('''
def bool_op_casting():
    l=[]
    L=[1]
    M=[2]
    if (l and L) or M:
        return (l and L) or M
    else:
        return M''', bool_op_casting=[])

    def test_map_on_generator(self):
        self.run_test('def map_on_generator(l): return map(float,(x*x for x in l))', [1,2,3], map_on_generator=[[int]])

    def test_map2_on_generator(self):
        self.run_test('def map2_on_generator(l): return map(lambda x,y : x*y, l, (y for x in l for y in l if x < 1))', [0,1,2,3], map2_on_generator=[[int]])

    def test_map_none_on_generator(self):
        self.run_test('def map_none_on_generator(l): return map(None,(x*x for x in l))', [1,2,3], map_none_on_generator=[[int]])

    def test_enumerate_on_generator(self):
        self.run_test("def enumerate_on_generator(n): return map(lambda (x,y) : x, enumerate((y for x in xrange(n) for y in xrange(x))))", 5, enumerate_on_generator=[int])

    def test_map_none2_on_generator(self):
        self.run_test('def map_none2_on_generator(l): return map(None,(x*x for x in l), (2*x for x in l))', [1,2,3], map_none2_on_generator=[[int]])

    def test_max_interface_arity(self):
        self.run_test('def max_interface_arity({0}):pass'.format(*['_'+str(i) for i in xrange(42)]), range(42), max_interface_arity=[[int]*42])

    def test_multiple_max(self):
        self.run_test('def multiple_max(i,j,k): return max(i,j,k)', 1, 1.5, False, multiple_max=[int, float, bool])

    def test_zip_on_generator(self):
        self.run_test('def zip_on_generator(n): return zip((i for i in xrange(n)), (i*2 for i in xrange(1,n+1)))', 5, zip_on_generator=[int])

    def test_parallel_enumerate(self):
        self.run_test('def parallel_enumerate(l):\n k = [0]*(len(l) + 1)\n "omp parallel for"\n for i,j in enumerate(l):\n  k[i+1] = j\n return k', range(1000), parallel_enumerate=[[int]])

    def test_ultra_nested_functions(self):
        code = '''
def ultra_nested_function(n):
	def foo(y):
		def bar(t): return t
		return bar(y)
	return foo(n)'''
        self.run_test(code, 42, ultra_nested_function=[int])

    def test_generator_sum(self):
        code = '''
def generator_sum(l0,l1):
    return sum(x*y for x,y in zip(l0,l1))'''
        self.run_test(code, range(10), range(10), generator_sum=[[int],[int]])

    def test_tuple_to_list(self):
        self.run_test('def tuple_to_list(t): return list(t)', (1,2,3), tuple_to_list=[(int, int, int)])

    def test_in_generator(self):
        self.run_test("def in_generator(n):return 1. in (i*i for i in xrange(n))", 5, in_generator=[int])

    def test_tuple_unpacking_in_generator(self):
        code = '''
def foo(l):
    a, b = 1,0
    yield a
    yield b
def tuple_unpacking_in_generator(n):
    f = foo(range(n))
    return 0 in f'''
        self.run_test(code, 10, tuple_unpacking_in_generator=[int])

    def test_loop_tuple_unpacking_in_generator(self):
        code= '''
def foo(l):
    for i,j in enumerate(l):
        yield i,j
def loop_tuple_unpacking_in_generator(n):
    f = foo(range(n))
    return (0,0) in f'''
        self.run_test(code, 10, loop_tuple_unpacking_in_generator=[int])

    def test_assign_in_except(self):
        code = '''
def assign_in_except():
    try:
        a=1
    except:
        a+=a
    return a'''
        self.run_test(code, assign_in_except=[])

    def test_combiner_on_empty_list(self):
        code = '''
def b(l):
    l+=[1]
    return l
def combiner_on_empty_list():
    return b(list()) + b([])'''
        self.run_test(code, combiner_on_empty_list=[])

    def test_dict_comprehension_with_tuple(self):
        self.run_test('def dict_comprehension_with_tuple(n): return { x:y for x,y in zip(range(n), range(1+n)) }', 10, dict_comprehension_with_tuple=[int])

    def test_nested_comprehension_with_tuple(self):
        self.run_test('def nested_comprehension_with_tuple(l): return [[ x+y for x,y in sqrpoints ] for sqrpoints in l]', [[(x,x)]*5 for x in range(10)], nested_comprehension_with_tuple=[[[(int,int)]]])

    def test_hashable_tuple(self):
        self.run_test('def hashable_tuple(): return { (1,"e", 2.5) : "r" }', hashable_tuple=[])

    def test_conflicting_names(self):
        self.run_test('def map(): return 5', map=[])

    def test_multiple_compares(self):
        self.run_test('def multiple_compares(x): return 1 < x < 2, 1 < x + 1 < 2', 0.5, multiple_compares=[float])

    def test_default_arg0(self):
        self.run_test('def default_arg0(n=12): return n', default_arg0=[])

    def test_default_arg1(self):
        self.run_test('def default_arg1(m,n=12): return m+n', 1, default_arg1=[int])

    def test_default_arg2(self):
        self.run_test('def default_arg2(n=12): return n', 1, default_arg2=[int])

    def test_default_arg3(self):
        self.run_test('def default_arg3(m,n=12): return m+n', 1, 2, default_arg3=[int,int])

    def test_long_to_float_conversion(self):
        self.run_test('def long_to_float_conversion(l): return float(l)', 12345678912345678L, long_to_float_conversion=[long])

    @skip("lists as zeros parameter are not supported")
    def test_list_as_zeros_parameter(self):
        self.run_test('def list_as_zeros_parameter(n): from numpy import zeros ; return zeros([n,n])', 3, list_as_zeros_parameter=[int])

    def test_add_arrays(self):
        self.run_test('def add_arrays(s): return (s,s) + (s,)', 1, add_arrays=[int])

    def test_tuple_to_tuple(self):
        self.run_test('def tuple_to_tuple(t): return tuple((1, t))',
                      '2',
                      tuple_to_tuple=[str])

    def test_array_to_tuple(self):
        self.run_test('def array_to_tuple(t): return tuple((1, t))',
                      2,
                      array_to_tuple=[int])

    def test_list_to_tuple(self):
        self.run_test('def list_to_tuple(t): return tuple([1, t])',
                      2,
                      list_to_tuple=[int])

########NEW FILE########
__FILENAME__ = test_analyses
from test_env import TestEnv
import unittest 

class TestAnalyses(TestEnv):

    def test_imported_ids_shadow_intrinsic(self):
        self.run_test("def imported_ids_shadow_intrinsic(range): return [ i*range for i in [1,2,3] ]", 2, imported_ids_shadow_intrinsic=[int])

    def test_shadowed_variables(self):
        self.run_test("def shadowed_variables(a): b=1 ; b+=a ; a= 2 ; b+=a ; return a,b", 18, shadowed_variables=[int])

    def test_decl_shadow_intrinsic(self):
        self.run_test("def decl_shadow_intrinsic(l): len=lambda l:1 ; return len(l)", [1,2,3], decl_shadow_intrinsic=[[int]])

    def test_used_def_chains(self):
        self.run_test("def use_def_chain(a):\n i=a\n for i in xrange(4):\n  print i\n  i=5.4\n  print i\n  break\n  i = 4\n return i", 3, use_def_chain=[int])

    def test_used_def_chains2(self):
        self.run_test("def use_def_chain2(a):\n i=a\n for i in xrange(4):\n  print i\n  i='lala'\n  print i\n  i = 4\n return i", 3, use_def_chain2=[int])

    def test_importedids(self):
        self.run_test("def importedids(a):\n i=a\n for i in xrange(4):\n  if i==0:\n   b = []\n  else:\n   b.append(i)\n return b", 3, importedids=[int])

    def test_falsepoly(self):
        self.run_test("def falsepoly():\n i = 2\n if i:\n  i='ok'\n else:\n  i='lolo'\n return i", falsepoly=[])

########NEW FILE########
__FILENAME__ = test_base
from test_env import TestEnv

class TestBase(TestEnv):
    def test_pass(self):
        self.run_test("def pass_(a):pass", 1, pass_=[int])

    def test_empty_return(self):
        self.run_test("def empty_return(a,b,c):return", 1,1,True, empty_return=[int,float,bool])

    def test_identity(self):
        self.run_test("def identity(a): return a", 1.5, identity=[float])

    def test_compare(self):
        self.run_test("def compare(a,b,c):\n if a < b < c: return a\n else: return b != c", 1,2,3, compare=[int, int, int])

    def test_arithmetic(self):
        self.run_test("def arithmetic(a,b,c): return a+b*c", 1,2,3.3, arithmetic=[int,int, float])

    def test_boolop(self):
        self.run_test("def boolop(a,b,c): return a and b or c", True, True, False, boolop=[bool,bool, bool])

    def test_operator(self):
        self.run_test("def operator_(a,b,c): return (a+b-b*a/(a%b)**(a<<a>>b|b^a&a/b)//c)",1,2,1.5, operator_=[int,int, float])

    def test_unaryop(self):
        self.run_test("def unaryop(a): return not(~(+(-a)))", 1, unaryop=[int])

    def test_expression(self):
        self.run_test("def expression(a,b,c): a+b*c", 1,2,3.3, expression=[int,int, float])

    def test_recursion(self):
        code="""
def fibo(n): return n if n <2 else fibo(n-1) + fibo(n-2)
def fibo2(n): return fibo2(n-1) + fibo2(n-2) if n > 1 else n
"""
        self.run_test(code, 4, fibo=[int], fibo2=[float])

    def test_manual_list_comprehension(self):
        self.run_test("def f(l):\n ll=list()\n for k in l:\n  ll+=[k]\n return ll\ndef manual_list_comprehension(l): return f(l)", [1,2,3], manual_list_comprehension=[[int]])

    def test_list_comprehension(self):
        self.run_test("def list_comprehension(l): return [ x*x for x in l ]", [1,2,3], list_comprehension=[[int]])

    def test_dict_comprehension(self):
        self.run_test("def dict_comprehension(l): return { i: 1 for i in l if len(i)>1 }", ["1","12","123"], dict_comprehension=[[str]])

    def test_filtered_list_comprehension(self):
        self.run_test("def filtered_list_comprehension(l): return [ x*x for x in l if x > 1 if x <10]", [1,2,3], filtered_list_comprehension=[[int]])

    def test_multilist_comprehension(self):
        self.run_test("def multilist_comprehension(l): return [ x*y for x in l for y in l]", [1,2,3], multilist_comprehension=[[int]])

    def test_zipped_list_comprehension(self):
        self.run_test("def zipped_list_comprehension(l): return [ x*y for x,y in zip(l,l) ]", [1,2,3], zipped_list_comprehension=[[int]])

    def test_zip(self):
        self.run_test("def zip_(l0,l1): return zip(l0,l1)", [1,2,3],["one", "two", "three"], zip_=[[int], [str]])

    def test_multizip(self):
        self.run_test("def multizip(l0,l1): return zip(l0,zip(l0,l1))", [1,2,3],["one", "two", "three"], multizip=[[int], [str]])

    def test_reduce(self):
        self.run_test("def reduce_(l): return reduce(lambda x,y:x+y, l)", [0,1.1,2.2,3.3], reduce_=[[float]])

    def test_another_reduce(self):
        self.run_test("def another_reduce(l0,l1): return reduce(lambda x,(y,z):x+y+z, zip(l0, l1),0)", [0.4,1.4,2.4,3.4], [0,1.1,2.2,3.3], another_reduce=[[float],[float]])

    def test_sum(self):
        self.run_test("def sum_(l): return sum(l)", [0,1.1,2.2,3.3], sum_=[[float]])

    def test_multisum(self):
        self.run_test("def multisum(l0, l1): return sum(l0) + sum(l1)", [0,1.1,2.2,3.3],[1,2,3], multisum=[[float],[int]])

    def test_max(self):
        self.run_test("def max_(l):return max(l)", [ 1.1, 2.2 ], max_=[[float]])

    def test_multimax(self):
        self.run_test("def multimax(l,v):return max(v,max(l))", [ 1.1, 2.2 ], 3, multimax=[[float],int])

    def test_min(self):
        self.run_test("def min_(l):return min(l)", [ 1.1, 2.2 ], min_=[[float]])

    def test_multimin(self):
        self.run_test("def multimin(l,v):return min(v,min(l))", [ 1.1, 2.2 ], 3, multimin=[[float],int])

    def test_map_none(self):
        self.run_test("def map_none(l0): return map(None, l0)", [0,1,2], map_none=[[int]])

    def test_map_none2(self):
        self.run_test("def map_none2(l0): return map(None, l0, l0)", [0,1,2], map_none2=[[int]])

    def test_map(self):
        self.run_test("def map_(l0, l1, v): return map(lambda x,y:x*v+y, l0, l1)", [0,1,2], [0,1.1,2.2], 2, map_=[[int], [float], int])

    def test_multimap(self):
        self.run_test("def multimap(l0, l1, v): return map(lambda x,y:x*v+y, l0, map(lambda z:z+1,l1))", [0,1,2], [0,1.1,2.2], 2, multimap=[[int], [float], int])

    def test_intrinsic_map(self):
        self.run_test("def intrinsic_map(l): return map(max,l)",[[0,1,2],[2,0,1]], intrinsic_map=[[[int]]])

    def test_range1(self):
        self.run_test("def range1_(e): return range(e)", 3, range1_=[int])

    def test_range2(self):
        self.run_test("def range2_(b,e): return range(b,e)", 1, 3, range2_=[int,int])

    def test_range3(self):
        self.run_test("def range3_(b,e,s): return range(b,e,s)", 8,3,-2, range3_=[int,int,int])

    def test_range4(self):
        self.run_test("def range4_(b,e,s): return range(b,e,s)", 8,2,-2, range4_=[int,int,int])

    def test_range5(self):
        self.run_test("def range5_(b,e,s): return range(b,e,s)", 3,8,1, range5_=[int,int,int])

    def test_range6(self):
        self.run_test("def range6_(b,e,s): return range(b,e,s)", 3,8,3, range6_=[int,int,int])

    def test_range7(self):
        self.run_test("def range7_(b,e,s): return range(b,e,s)", 3,9,3, range7_=[int,int,int])

    def test_rrange1(self):
        self.run_test("def rrange1_(e): return list(reversed(range(e)))", 3, rrange1_=[int])

    def test_rrange2(self):
        self.run_test("def rrange2_(b,e): return set(reversed(range(b,e)))", 1, 3, rrange2_=[int,int])
    
    def test_rrange3(self):
        self.run_test("def rrange3_(b,e,s): return list(reversed(range(b,e,s)))", 8,3,-2, rrange3_=[int,int,int])
    
    def test_rrange4(self):
        self.run_test("def rrange4_(b,e,s): return set(reversed(range(b,e,s)))", 8,2,-2, rrange4_=[int,int,int])
    
    def test_rrange5(self):
        self.run_test("def rrange5_(b,e,s): return list(reversed(range(b,e,s)))", 3,8,1, rrange5_=[int,int,int])

    def test_rrange6(self):
        self.run_test("def rrange6_(b,e,s): return set(reversed(range(b,e,s)))", 3,8,3, rrange6_=[int,int,int])

    def test_rrange7(self):
        self.run_test("def rrange7_(b,e,s): return list(reversed(range(b,e,s)))", 3,9,3, rrange7_=[int,int,int])

    def test_multirange(self):
        self.run_test("def multirange(i): return map(lambda x,y:y*x/2, range(1,i), range(i,1,-1))", 3, multirange=[int])

    def test_xrange1(self):
        self.run_test("def xrange1_(e): return list(xrange(e))", 3, xrange1_=[int])

    def test_xrange2(self):
        self.run_test("def xrange2_(b,e): return list(xrange(b,e))", 1, 3, xrange2_=[int,int])

    def test_xrange3(self):
        self.run_test("def xrange3_(b,e,s): return list(xrange(b,e,s))", 8,3,-2, xrange3_=[int,int,int])

    def test_xrange4(self):
        self.run_test("def xrange4_(b,e,s): return list(xrange(b,e,s))", 3,8,1, xrange4_=[int,int,int])

    def test_xrange5(self):
        self.run_test("def xrange5_(e): return max(xrange(e))", 3, xrange5_=[int])

    def test_multixrange(self):
        self.run_test("def multixrange(i): return map(lambda x,y:y*x/2, xrange(1,i), xrange(i,1,-1))", 3, multixrange=[int])

    def test_print(self):
        self.run_test("def print_(a,b,c,d): print a,b,c,d,'e',1.5,", [1,2,3.1],3,True, "d", print_=[[float], int, bool, str])

    def test_assign(self):
        self.run_test("def assign(a): b=2*a ; return b", 1, assign=[int])

    def test_multiassign(self):
        self.run_test("def multiassign(a):\n c=b=a\n return c", [1], multiassign=[[int]])

    def test_list(self):
        self.run_test("def list_(a): b=2*a;c=b/2;return max(c,b)", 1, list_=[int])

    def test_if(self):
        self.run_test("def if_(a,b):\n if a>b: return a\n else: return b", 1, 1.1, if_=[int, float])

    def test_while(self):
        self.run_test("def while_(a):\n while(a>0): a-=1\n return a", 8, while_=[int])

    def test_for(self):
        self.run_test("def for_(l):\n s=0\n for i in l:\n  s+=i\n return s", [0,1,2], for_=[[float]])

    def test_declarations(self):
        code = """
def declarations():
    if True:
        a=0
        while a <3:
            b = 1
            a = b + a
    else:
        a=1
    return a + b
"""
        self.run_test(code, declarations=[])

    def test_lambda(self):
        code = """
def lambda_():
    l=lambda x,y: x+y
    return l(1,2) + l(1.2,2)
"""
        self.run_test(code, lambda_=[])

    def test_multidef1(self):
        self.run_test("def def10(): pass\ndef def11(): def10()", def11=[])

    def test_multidef2(self):
        self.run_test("def def21(): def20()\ndef def20(): pass", def21=[])

    def test_multidef3(self):
        self.run_test("def def31(): return 1\ndef def30(): return def31()", def31=[])

    def test_multidef4(self):
       self.run_test("def def41(): return def40()\ndef def40(): return 1", def41=[])

    def test_tuple(self):
        self.run_test("def tuple_(t): return t[0]+t[1]", (0,1), tuple_=[(int, int)])

    def test_nested_list_comprehension(self):
        self.run_test("def nested_list_comprehension(): return [ [ x+y for x in xrange(10) ] for y in xrange(20) ]", nested_list_comprehension=[])

    def test_delete(self):
        self.run_test("def delete_(v): del v", 1, delete_=[int])

    def test_continue(self):
        self.run_test("def continue_():\n for i in xrange(3):continue\n return i", continue_=[])

    def test_break(self):
        self.run_test("def break_():\n for i in xrange(3):break\n return i", break_=[])

    def test_assert(self):
        self.run_test("def assert_(i): assert i > 0", 1, assert_=[int])

    def test_assert_with_msg(self):
        self.run_test("def assert_with_msg(i): assert i > 0, 'hell yeah'", 1, assert_with_msg=[int])

    def test_import_from(self):
        self.run_test("def import_from(): from math import cos ; return cos(1.)", import_from=[])

    def test_len(self):
        self.run_test("def len_(i,j,k): return len(i)+len(j)+len(k)", "youpi", [1,2],[], len_=[str,[int], [float]])

    def test_in_string(self):
        self.run_test("def in_string(i,j): return i in j", "yo", "youpi", in_string=[str,str])

    def test_not_in_string(self):
        self.run_test("def not_in_string(i,j): return i not in j", "yo", "youpi", not_in_string=[str,str])

    def test_in_list(self):
        self.run_test("def in_list(i,j): return i in j", 1, [1,2,3], in_list=[int,[int]])

    def test_not_in_list(self):
        self.run_test("def not_in_list(i,j): return i not in j", False, [True, True, True], not_in_list=[bool,[bool]])

    def test_subscript(self):
        self.run_test("def subscript(l,i): l[0]=l[0]+l[i]", [1], 0, subscript=[[int], int])

    def test_nested_lists(self):
        self.run_test("def nested_lists(l,i): return l[0][i]", [[1]], 0, nested_lists=[[[int]],int])

    def test_nested_tuples(self):
        self.run_test("def nested_tuples(l,i): return l[i][1]", [(0.1,1,)], 0, nested_tuples=[[(float,int)],int])

    def test_return_empty_list(self):
        self.run_test("def return_empty_list(): return list()", return_empty_list=[])

    def test_empty_list(self):
        self.run_test("def empty_list(): a=[]", empty_list=[])

    def test_multi_list(self):
        self.run_test("def multi_list(): return [[[2.0],[1,2,3]],[[2.0],[1,2,3]]]", multi_list=[])

    def test_empty_tuple(self):
        self.run_test("def empty_tuple(): a=()", empty_tuple=[])

    def test_multi_tuple(self):
        self.run_test("def multi_tuple(): return (1,('e',2.0),[1,2,3])", multi_tuple=[])

    def test_augmented_assign0(self):
        self.run_test("def augmented_assign0(a):\n a+=1.5\n return a", 12, augmented_assign0=[int])

    def test_augmented_assign1(self):
        self.run_test("def augmented_assign1(a):\n a-=1.5\n return a", 12, augmented_assign1=[int])

    def test_augmented_assign2(self):
        self.run_test("def augmented_assign2(a):\n a*=1.5\n return a", 12, augmented_assign2=[int])

    def test_augmented_assign3(self):
        self.run_test("def augmented_assign3(a):\n a/=1.5\n return a", 12, augmented_assign3=[int])

    def test_augmented_assign4(self):
        self.run_test("def augmented_assign4(a):\n a %= 5\n return a", 12, augmented_assign4=[int])

    def test_augmented_assign5(self):
        self.run_test("def augmented_assign5(a):\n a//=2\n return a", 12, augmented_assign5=[int])

    def test_augmented_assign6(self):
        self.run_test("def augmented_assign6(a):\n a**=5\n return a", 12, augmented_assign6=[int])

    def test_augmented_assign7(self):
        self.run_test("def augmented_assign7(a):\n a<<=1\n return a", 12, augmented_assign7=[int])

    def test_augmented_assign8(self):
        self.run_test("def augmented_assign8(a):\n a>>=1\n return a", 12, augmented_assign8=[int])

    def test_augmented_assign9(self):
        self.run_test("def augmented_assign9(a):\n a^=1\n return a", 12, augmented_assign9=[int])

    def test_augmented_assignA(self):
        self.run_test("def augmented_assignA(a):\n a|=1\n return a", 12, augmented_assignA=[int])

    def test_augmented_assignB(self):
        self.run_test("def augmented_assignB(a):\n a&=1\n return a", 12, augmented_assignB=[int])

    def test_augmented_list_assign(self):
        self.run_test("def augmented_list_assign(l):\n a=list()\n a+=l\n return a", [1,2], augmented_list_assign=[[int]])

    def test_initialization_list(self):
        self.run_test("def initialization_list(): return [1, 2.3]", initialization_list=[])

    def test_multiple_assign(self):
        self.run_test("def multiple_assign():\n a=0 ; b = a\n a=1.5\n return a, b", multiple_assign=[])

    def test_multiple_return1(self):
        self.run_test("def multiple_return1(a):\n if True:return 1\n else:\n  return a", 2,  multiple_return1=[int])

    def test_multiple_return2(self):
        self.run_test("def multiple_return2(a):\n if True:return 1\n else:\n  b=a\n  return b", 2,  multiple_return2=[int])

    def test_multiple_return3(self):
        self.run_test("def multiple_return3(a):\n if True:return 1\n else:\n  b=a\n  return a+b", 2,  multiple_return3=[int])

    def test_id(self):
        self.run_test("def id_(a):\n c=a\n return id(a)==id(c)", [1,2,3], id_=[[int]])

    def test_delayed_max(self):
        self.run_test("def delayed_max(a,b,c):\n m=max\n return m(a,b) + m(b,c)", 1, 2, 3.5, delayed_max=[int, int, float])

    def test_slicing(self):
        self.run_test("def slicing(l): return l[0:1] + l[:-1]",[1,2,3,4], slicing=[[int]])

    def test_not_so_deep_recursive_calls(self):
        code="""
def a(i): return b(i)
def b(i): return b(a(i-1)) if i else i
def not_so_deep_recursive_calls(i):return b(i)"""
        self.run_test(code,3, not_so_deep_recursive_calls=[int])

    def test_deep_recursive_calls(self):
        code="""
def a(i): return a(i-1) + b(i) if i else i
def b(i): return b(i-1)+a(i-1) if i else c(i-1) if i+1 else i
def c(i): return c(i-1) if i>0 else 1
def deep_recursive_calls(i):a(i)+b(i) +c(i)"""
        self.run_test(code,3, deep_recursive_calls=[int])

    def test_dummy_nested_def(self):
        code="""
def dummy_nested_def(a):
    def the_dummy_nested_def(b):return b
    return the_dummy_nested_def(a)"""
        self.run_test(code,3, dummy_nested_def=[int])

    def test_nested_def(self):
        code="""
def nested_def(a):
    def the_nested_def(b):return a+b
    return the_nested_def(3)"""
        self.run_test(code,3, nested_def=[int])

    def test_none(self):
        self.run_test("def none_(l):\n if len(l)==0: return\n else: return l", [], none_=[[int]])

    def test_import(self):
        self.run_test("import math\ndef import_(): return math.cos(1)", import_=[])

    def test_local_import(self):
        self.run_test("def local_import_(): import math;return math.cos(1)", local_import_=[])

    def test_abs(self):
        self.run_test("def abs_(a): return abs(a)", -1.3, abs_=[float])

    def test_all(self):
        self.run_test("def all_(a): return all(a)", [True, False, True], all_=[[bool]])

    def test_any(self):
        self.run_test("def any_(a): return any(a)", [0, 1, 2], any_=[[int]])

    def test_bin(self):
        self.run_test("def bin_(a): return bin(a)", 54321, bin_=[int])

    def test_chr(self):
        self.run_test("def chr_(a): return chr(a)", 42, chr_=[int])

    def test_cmp(self):
        self.run_test("def cmp_(a,b): return cmp(a,b)", 1, 4.5, cmp_=[int, float])

    def test_complex(self):
        self.run_test("def complex_(a): return complex(a)", 1, complex_=[int])

    def test_divmod(self):
        self.run_test("def divmod_(a,b): return divmod(a,b)", 5, 2, divmod_=[int,int])

    def test_enumerate(self):
        self.run_test("def enumerate_(l): return [ x for x in enumerate(l) ]", ["a","b","c"], enumerate_=[[str]])

    def test_enumerat2(self):
        self.run_test("def enumerate2_(l): return [ x for x in enumerate(l, 3) ]", ["a","b","c"], enumerate2_=[[str]])

    def test_filter(self):
        self.run_test("def filter_(l): return filter(lambda x:x%2, l)", [1,2,3], filter_=[[int]])

    def test_hex(self):
        self.run_test("def hex_(a): return hex(a)", 18, hex_=[int])

    def test_oct(self):
        self.run_test("def oct_(a): return oct(a)", 18, oct_=[int])

    def test_pow(self):
        self.run_test("def pow_(a): return pow(a,15)", 18, pow_=[int])

    def test_reversed(self):
        self.run_test("def reversed_(l): return [x for x in reversed(l)]", [1,2,3], reversed_=[[int]])

    def test_round(self):
        self.run_test("def round_(v): return round(v) + round(v,2)", 0.1234, round_=[float])

    def test_sorted(self):
        self.run_test("def sorted_(l): return [x for x in sorted(l)]", [1,2,3], sorted_=[[int]])

    def test_str(self):
        self.run_test("def str_(l): return str(l)", [1,2,3.5], str_=[[float]])

    def test_append(self):
        self.run_test("def append(): l=[] ; l.append(1) ; return l", append=[])

    def test_append_in_call(self):
        self.run_test("def call(l):l.append(1.)\ndef append_in_call(): l=[] ; call(l) ; l.append(1) ; return l", append_in_call=[])

    def test_complex_append_in_call(self):
        code="""
def foo(a,b):
	i = 3*b
	if not i in a:
		a.append(i)
def complex_append_in_call(l1,l2):
	b = []
	for x in l1:
		if not x in l2:
			foo(b,x)"""
        self.run_test(code, [1,2,3],[2],complex_append_in_call=[[int],[int]])

    def test_complex_number(self):
        code="""
def complex_number():
    c=complex(0,1)
    return c.real + c.imag"""
        self.run_test(code, complex_number=[])

    def test_raise(self):
        self.run_test("def raise_():\n raise RuntimeError('pof')", raise_=[], check_exception=True)

    def test_complex_number_serialization(self):
        self.run_test("def complex_number_serialization(l): return [x+y for x in l for y in l]", [complex(1,0), complex(1,0)], complex_number_serialization=[[complex]])

    def test_complex_conj(self):
        self.run_test("def complex_conjugate(c): return c.conjugate()", complex(0,1), complex_conjugate=[complex])

    def test_cast(self):
        self.run_test("def cast(i,f): return float(i)+int(f)", 1,1.5, cast=[int, float])

    def test_subscript_assignment(self):
        code="""
def foo(A):
    A[0]=1.5
def subscript_assignment ():
    a=range(1)
    foo(a)
    return a[0]"""
        self.run_test(code,subscript_assignment=[])

    def test_conflicting_keywords(self):
        code="""
def export(template):
    return [ new*new for new in template ]"""
        self.run_test(code, [1], export=[[int]])

    def test_forelse(self):
        code="""
def forelse():
    l=0
    for i in range(10):
        if i > 3:break
        for j in range(10):
            if j > 5:break
            l+=1
        else:
            l*=2
    else:
        l*=3
    return l"""
        self.run_test(code, forelse=[])

    def test_tuples(self):
        self.run_test("def tuples(n): return ((1,2.,'e') , [ x for x in tuple([1,2,n])] )", 1, tuples=[int])

    def test_long_assign(self):
        self.run_test("def _long_assign():\n b=10L\n c = b + 10\n return c", _long_assign=[])

    def test_long(self):
        self.run_test("def _long(a): return a+34",111111111111111L, _long=[long])

    def test_reversed_slice(self):
        self.run_test("def reversed_slice(l): return l[::-2]", [0,1,2,3,4], reversed_slice=[[int]])

    def test_shadow_parameters(self):
        code="""
def shadow_parameters(l):
    if False:l=None
    return l"""
        self.run_test(code, [1], shadow_parameters=[[int]])

    def test_yielder(self):
        code="""
def iyielder(i):
    for k in xrange(i+18):
        yield k
    return

def yielder():
    f=iyielder(1)
    b=f.next()
    return [i*i for i in f]"""
        self.run_test(code, yielder=[])

    def test_yield_with_default_param(self):
        code="""
def foo(a=1000):
    for i in xrange(10):
        yield a

def yield_param():
    it = foo()
    return [i for i in it]"""
        self.run_test(code, yield_param=[])

    def test_set(self):
        code="""
def set_(a,b):
    S=set()
    S.add(a)
    S.add(b)
    return len(S)"""
        self.run_test(code, 1,2,set_=[int, int])
    def test_in_set(self):
        code="""
def in_set(a):
    S=set()
    S.add(a)
    return a in S"""
        self.run_test(code, 1.5, in_set=[float])

    def test_return_set(self):
        self.run_test("def return_set(l): return set(l)", [1,2,3,3], return_set=[[int]])

    def test_import_set(self):
        self.run_test("def import_set(l): l.add(1) ; return l", {0,2}, import_set=[{int}])

    def test_raw_set(self):
        self.run_test("def raw_set(): return { 1, 1., 2 }", raw_set=[])

    def test_iter_set(self):
        self.run_test("def iter_set(s):\n l=0\n for k in s: l+=1\n return l", { "a", "b", "c" } , iter_set=[{str}])

    def test_set_comprehension(self):
        self.run_test("def set_comprehension(l): return { i*i for i in l }", [1 , 2, 1, 3], set_comprehension=[[int]])

    def test_slicer(self):
        code="""
def slicer(l):
    l[2:5]=[1,2]
    return l"""
        self.run_test(code,[1,2,3,4,5,6,7,8,9], slicer=[[int]])

    def test_generator_expression(self):
        code="""
def generator_expression(l):
    return sum(x for x in l if x == 1)"""
        self.run_test(code,[1,1,1,2], generator_expression=[[int]])

    def test_default_parameters(self):
        code="""
def dp(b,a=1.2):
    return a

def default_parameters():
    a=1
    c=dp(a)
    d=dp(5,"yeah")
    return str(c)+d"""
        self.run_test(code, default_parameters=[])

    def test_import_as(self):
        code="""
from math import cos as COS
def import_as():
    x=.42
    import math as MATH
    return MATH.sin(x)**2 + COS(x)**2"""
        self.run_test(code, import_as=[])

    def test_tuple_unpacking(self):
        self.run_test("def tuple_unpacking(t): a,b = t ; return a, b", (1,"e"), tuple_unpacking=[(int, str)])

    def test_list_unpacking(self):
        self.run_test("def list_unpacking(t): [a,b] = t ; return a, b", (1,2), list_unpacking=[(int, int)])

    def test_recursive_attr(self):
        self.run_test("def recursive_attr(): return {1,2,3}.union({1,2}).union({5})", recursive_attr=[])

    def test_range_negative_step(self):
        self.run_test("""def range_negative_step(n):
        o=[]
        for i in xrange(n, 0, -1): o.append(i)
        return o""", 10, range_negative_step=[int])

    def test_reversed_range_negative_step(self):
        self.run_test("""def reversed_range_negative_step(n):
        o=[]
        for i in reversed(xrange(n, 0, -1)): o.append(i)
        return o""", 10, reversed_range_negative_step=[int])

    def test_update_empty_list(self):
        self.run_test('''
def update_empty_list(l):
    p = list()
    return p + l[:1]''', range(5), update_empty_list=[[int]])

    def test_update_list_with_slice(self):
        self.run_test('''
def update_list_with_slice(l):
    p = list()
    for i in xrange(10):
        p += l[:1]
    return p,i''', range(5), update_list_with_slice=[[int]])

    def test_add_slice_to_list(self):
        self.run_test('''
def add_slice_to_list(l):
    p = list()
    for i in xrange(10):
        p = p + l[:1]
    return p,i''', range(5), add_slice_to_list=[[int]])

    def test_bool_(self):
        self.run_test("def _bool(d): return bool(d)", 3, _bool=[int])

    def test_complex_add(self):
        self.run_test("def complex_add(): a = 1j ; b = 2 ; return a + b", complex_add=[])

    def test_complex_sub(self):
        self.run_test("def complex_sub(): a = 1j ; b = 2 ; return a - b", complex_sub=[])

    def test_complex_mul(self):
        self.run_test("def complex_mul(): a = 1j ; b = 2 ; return a * b", complex_mul=[])

    def test_complex_div(self):
        self.run_test("def complex_div(): a = 1j ; b = 2 ; return a / b", complex_div=[])

    def test_modulo_int0(self):
        self.run_test("def modulo_int0(n): return n%3, (-n)%3",
                      5,
                      modulo_int0=[int])

    def test_modulo_int1(self):
        self.run_test("def modulo_int1(n): return n%3, (-n)%3",
                      3,
                      modulo_int1=[int])

    def test_modulo_float0(self):
        self.run_test("def modulo_float0(n): return n%3, (-n)%3",
                      5.4,
                      modulo_float0=[float])

    def test_modulo_float1(self):
        self.run_test("def modulo_float1(n): return n%3, (-n)%3",
                      3.5,
                      modulo_float1=[float])

    def test_floordiv_int0(self):
        self.run_test("def floordiv_int0(n): return n%3, (-n)%3",
                      5,
                      floordiv_int0=[int])

    def test_floordiv_int1(self):
        self.run_test("def floordiv_int1(n): return n//2, (-n)//2",
                      3,
                      floordiv_int1=[int])

    def test_floordiv_float0(self):
        self.run_test("def floordiv_float0(n): return n//2, (-n)//2",
                      5.4,
                      floordiv_float0=[float])

    def test_floordiv_float1(self):
        self.run_test("def floordiv_float1(n): return n//2, (-n)//2",
                      3.5,
                      floordiv_float1=[float])

########NEW FILE########
__FILENAME__ = test_bisect
import unittest
from test_env import TestEnv

class TestBisect(TestEnv):

    def test_bisect_left0(self):
        self.run_test("def bisect_left0(l,a): from bisect import bisect_left ; return bisect_left(l,a)", [0,1,2,3],2, bisect_left0=[[int],int])

    def test_bisect_left1(self):
        self.run_test("def bisect_left1(l,a): from bisect import bisect_left ; return bisect_left(l,a,1)", [0,1,2,3],2, bisect_left1=[[int],int])

    def test_bisect_left2(self):
        self.run_test("def bisect_left2(l,a): from bisect import bisect_left ; return bisect_left(l,a)", [1,1,1,1],1, bisect_left2=[[int],int])

    def test_bisect_left3(self):
        self.run_test("def bisect_left3(l,a): from bisect import bisect_left ; return bisect_left(l,a,1,2)", [0,1,1,3],2, bisect_left3=[[int],int])

    def test_bisect_left4(self):
        self.run_test("def bisect_left4(l,a): from bisect import bisect_left ; return bisect_left(l,a)", [1,1,1,1],2, bisect_left4=[[int],int])

    def test_bisect_right0(self):
        self.run_test("def bisect_right0(l,a): from bisect import bisect_right ; return bisect_right(l,a)", [0,1,2,3],2, bisect_right0=[[int],int])

    def test_bisect_right1(self):
        self.run_test("def bisect_right1(l,a): from bisect import bisect_right ; return bisect_right(l,a,1)", [0,1,2,3],2, bisect_right1=[[int],int])

    def test_bisect_right2(self):
        self.run_test("def bisect_right2(l,a): from bisect import bisect_right ; return bisect_right(l,a)", [1,1,1,1],1, bisect_right2=[[int],int])

    def test_bisect_right3(self):
        self.run_test("def bisect_right3(l,a): from bisect import bisect_right ; return bisect_right(l,a,1,2)", [0,1,1,3],2, bisect_right3=[[int],int])

    def test_bisect_right4(self):
        self.run_test("def bisect_right4(l,a): from bisect import bisect_right ; return bisect_right(l,a)", [1,1,1,1],2, bisect_right4=[[int],int])

########NEW FILE########
__FILENAME__ = test_blas
from test_env import TestEnv

class TestBlas(TestEnv):

    def test_naive_matrix_multiply(self):
        code="""
def matrix_multiply(m0, m1):
    new_matrix = []
    for i in xrange(len(m0)):
        new_matrix.append([0]*len(m1[0]))

    for i in xrange(len(m0)):
        for j in xrange(len(m1[0])):
            for k in xrange(len(m1)):
                new_matrix[i][j] += m0[i][k]*m1[k][j]
    return new_matrix"""
        self.run_test(code, [[0,1],[1,0]], [[1,2],[2,1]], matrix_multiply=[[[int]],[[int]]])


########NEW FILE########
__FILENAME__ = test_cases
# todo: check http://code.google.com/p/unladen-swallow/wiki/Benchmarks
import unittest
from test_env import TestFromDir
import os

class TestCases(TestFromDir):

    path = os.path.join(os.path.dirname(__file__),"cases")


TestCases.populate(TestCases)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_constant_folding
from test_env import TestEnv

class TestConstantUnfolding(TestEnv):

    def test_constant_folding_int_literals(self):
        self.run_test("def constant_folding_int_literals(): return 1+2*3.5", constant_folding_int_literals=[])

    def test_constant_folding_str_literals(self):
        self.run_test("def constant_folding_str_literals(): return \"1\"+'2'*3", constant_folding_str_literals=[])

    def test_constant_folding_list_literals(self):
        self.run_test("def constant_folding_list_literals(): return [1]+[2]*3", constant_folding_list_literals=[])

    def test_constant_folding_set_literals(self):
        self.run_test("def constant_folding_set_literals(): return {1,2,3,3}", constant_folding_set_literals=[])

    def test_constant_folding_builtins(self):
        self.run_test("def constant_folding_builtins(): return map(len,zip(range(2), range(2)))", constant_folding_builtins=[])

    def test_constant_folding_imported_functions(self):
        self.run_test("def constant_folding_imported_functions(): from math import cos ; return float(int(10*cos(1)))", constant_folding_imported_functions=[])

    def test_constant_folding_list_method_calls(self):
        self.run_test("def foo(n): l=[] ; l.append(n) ; return l\ndef constant_folding_list_method_calls(n): return foo(n)", 1, constant_folding_list_method_calls=[int])

    def test_constant_folding_complex_calls(self):
        self.run_test("def constant_folding_complex_calls(): return complex(1,1)", constant_folding_complex_calls=[])

    def test_constant_folding_expansive_calls(self):
        self.run_test("def constant_folding_expansive_calls(): return range(2**6)", constant_folding_expansive_calls=[])

    def test_constant_folding_too_expansive_calls(self):
        self.run_test("def constant_folding_too_expansive_calls(): return range(2**16)", constant_folding_too_expansive_calls=[])

########NEW FILE########
__FILENAME__ = test_conversion
from test_env import TestEnv
from unittest import skip
import numpy as np

class TestConversion(TestEnv):

    def test_list_of_uint16(self):
        self.run_test('def list_of_uint16(l): return l', [1,2,3,4], list_of_uint16=[[np.uint16]])

    def test_set_of_int32(self):
        self.run_test('def set_of_int32(l): return l', {1,2,3,-4}, set_of_int32=[{np.int32}])

    def test_dict_of_int64_and_int8(self):
        self.run_test('def dict_of_int64_and_int8(l): return l', {1:1,2:3,3:4,-4:-5}, dict_of_int64_and_int8=[{np.int64:np.int8}])

    def test_tuple_of_uint8_and_int16(self):
        self.run_test('def tuple_of_uint8_and_int16(l): return l', (5, -146), tuple_of_uint8_and_int16=[(np.uint8, np.int16)])

    def test_array_of_uint32(self):
        self.run_test('def array_of_uint32(l): return l', np.ones(2,dtype=np.uint32), array_of_uint32=[np.array([np.uint32])])

    def test_array_of_uint64_to_uint32(self):
        self.run_test('def array_of_uint64_to_uint32(l): import numpy ; return l, numpy.array(l, numpy.uint32)', np.ones(2,dtype=np.uint64), array_of_uint64_to_uint32=[np.array([np.uint64])])

    def test_list_of_float64(self):
        self.run_test('def list_of_float64(l): return [2 * _ for _ in l]', [1,2], list_of_float64=[[np.float64]])

    def test_set_of_float32(self):
        self.run_test('def set_of_float32(l): return { _ / 2 for _ in l}', {np.float32(1),np.float32(2)}, set_of_float32=[{np.float32}])

    def test_dict_of_complex64_and_complex_128(self):
        self.run_test('def dict_of_complex64_and_complex_128(l): return l.keys(), l.values()', {np.complex64(3.1+1.1j):4.5+5.5j}, dict_of_complex64_and_complex_128=[{np.complex64:np.complex128}])


########NEW FILE########
__FILENAME__ = test_copperhead
from test_env import TestEnv

class TestCopperhead(TestEnv):

# from copperhead test suite
# https://github.com/copperhead

    def test_saxpy(self):
        self.run_test("def saxpy(a, x, y): return map(lambda xi, yi: a * xi + yi, x, y)", 1.5, [1,2,3], [0.,2.,4.], saxpy=[float,[int], [float]])

    def test_saxpy2(self):
        self.run_test("def saxpy2(a, x, y): return [a*xi+yi for xi,yi in zip(x,y)]", 1.5, [1,2,3], [0.,2.,4.], saxpy2=[float,[int], [float]])

    def test_saxpy3(self):
        code="""
def saxpy3(a, x, y):
    def triad(xi, yi): return a * xi + yi
    return map(triad, x, y)
"""
        self.run_test(code,  1.5, [1,2,3], [0.,2.,4.], saxpy3=[float,[int], [float]])

    def test_saxpy4(self):
        code="""
def saxpy4(a, x, y):
    return manual(y,x,a)
def manual(y,x,a):
    __list=list()
    for __tuple in zip(y,x):
        __list.append(__tuple[0]*a+__tuple[1])
    return __list
"""
        self.run_test(code,  1.5, [1,2,3], [0.,2.,4.], saxpy4=[float,[int], [float]])

    def test_sxpy(self):
        code="""
def sxpy(x, y):
    def duad(xi, yi): return xi + yi
    return map(duad, x, y)
"""
        self.run_test(code,  [1,2,3], [0.,2.,4.], sxpy=[[int], [float]])

    def test_incr(self):
        self.run_test("def incr(x): return map(lambda xi: xi + 1, x)", [0., 0., 0.], incr=[[float]])

    def test_as_ones(self):
        self.run_test("def as_ones(x): return map(lambda xi: 1, x)", [0., 0., 0.], as_ones=[[float]])

    def test_idm(self):
        self.run_test("def idm(x): return map(lambda b: b, x)", [1, 2, 3], idm=[[int]])

    def test_incr_list(self):
        self.run_test("def incr_list(x): return [xi + 1 for xi in x]", [1., 2., 3.], incr_list=[[float]])


    def test_idx(self):
        code="""
def idx(x):
    def id(xi): return xi
    return map(id, x)"""
        self.run_test(code, [1,2,3], idx=[[int]])

    def test_rbf(self):
        code="""
from math import exp
def norm2_diff(x, y):
   def el(xi, yi):
       diff = xi - yi
       return diff * diff
   return sum(map(el, x, y))

def rbf(ngamma, x, y):
   return exp(ngamma * norm2_diff(x,y))"""
        self.run_test(code, 2.3, [1,2,3], [1.1,1.2,1.3], rbf=[float,[float], [float]])

# from copperhead-new/copperhead/prelude.py
    def test_indices(self):
        self.run_test("def indices(A):return range(len(A))",[1,2], indices=[[int]])

    def test_gather(self):
        self.run_test("def gather(x, indices): return [x[i] for i in indices]", [1,2,3,4,5],[0,2,4], gather=[[int], [int]])

    def test_scatter(self):
        code="""
def indices(x): return xrange(len(x))
def scatter(src, indices_, dst):
    assert len(src)==len(indices_)
    result = list(dst)
    for i in xrange(len(src)):
        result[indices_[i]] = src[i]
    return result
"""
        self.run_test(code, [0.0,1.0,2.,3,4,5,6,7,8,9],[5,6,7,8,9,0,1,2,3,4],[0,0,0,0,0,0,0,0,0,0,18], scatter=[[float], [int], [float]])

    def test_scan(self):
        code="""
def prefix(A): return scan(lambda x,y:x+y, A)
def scan(f, A):
    B = list(A)
    for i in xrange(1, len(B)):
        B[i] = f(B[i-1], B[i])
    return B
"""
        self.run_test(code, [1,2,3], prefix=[[float]])



# from Copperhead: Compiling an Embedded Data Parallel Language
# by Bryan Catanzaro, Michael Garland and Kurt Keutzer
# http://www.eecs.berkeley.edu/Pubs/TechRpts/2010/EECS-2010-124.html

    def test_spvv_csr(self):
        code="""
def spvv_csr(x, cols, y):
    def gather(x, indices): return [x[i] for i in indices]
    z = gather(y, cols)
    return sum(map(lambda a, b: a * b, x, z))
"""
        self.run_test(code, [1,2,3],[0,1,2],[5.5,6.6,7.7], spvv_csr=[[int], [int], [float]])

    def test_spmv_csr(self):
        code="""
def spvv_csr(x, cols, y):
    def gather(x, indices): return [x[i] for i in indices]
    z = gather(y, cols)
    return sum(map(lambda a, b: a * b, x, z))
def spmv_csr(Ax, Aj, x):
    return map(lambda y, cols: spvv_csr(y, cols, x), Ax, Aj)
"""
        self.run_test(code, [[0,1,2],[0,1,2],[0,1,2]],[[0,1,2],[0,1,2],[0,1,2]],[0,1,2], spmv_csr=[[[int]], [[int]], [int]])

    def test_spmv_ell(self):
        code="""
def indices(x): return xrange(len(x))
def spmv_ell(data, idx, x):
    def kernel(i):
        return sum(map(lambda Aj, J: Aj[i] * x[J[i]], data, idx))
    return map(kernel, indices(x))
"""
        self.run_test(code, [[0,1,2],[0,1,2],[0,1,2]],[[0,1,2],[0,1,2],[0,1,2]],[0,1,2], spmv_ell=[[[int]], [[int]], [int]])

    def test_vadd(self):
        self.run_test("def vadd(x, y): return map(lambda a, b: a + b, x, y)", [0.,1.,2.],[5.,6.,7.], vadd=[[float], [float]])

    def test_vmul(self):
        self.run_test("def vmul(x, y): return map(lambda a, b: a * b, x, y)", [0.,1.,2.],[5.,6.,7.], vmul=[[float], [float]])

    def test_form_preconditioner(self):
        code="""
def vadd(x, y): return map(lambda a, b: a + b, x, y)
def vmul(x, y): return map(lambda a, b: a * b, x, y)
def form_preconditioner(a, b, c):
    def det_inverse(ai, bi, ci):
        return 1.0/(ai * ci - bi * bi)
    indets = map(det_inverse, a, b, c)
    p_a = vmul(indets, c)
    p_b = map(lambda a, b: -a * b, indets, b)
    p_c = vmul(indets, a)
    return p_a, p_b, p_c
"""
        self.run_test(code, [1,2,3],[0,1,2],[5.5,6.6,7.7],form_preconditioner=[[int], [int], [float]])

    def test_precondition(self):
        code="""
def precondition(u, v, p_a, p_b, p_c):
    def vadd(x, y): return map(lambda a, b: a + b, x, y)
    def vmul(x, y): return map(lambda a, b: a * b, x, y)
    e = vadd(vmul(p_a, u), vmul(p_b, v))
    f = vadd(vmul(p_b, u), vmul(p_c, v))
    return e, f
"""
        self.run_test(code, [1,2,3], [5.5,6.6,7.7],[1,2,3], [5.5,6.6,7.7],[8.8,9.9,10.10], precondition=[[int], [float], [int], [float], [float]])


########NEW FILE########
__FILENAME__ = test_dict
from test_env import TestEnv

class TestDict(TestEnv):

    def test_dict_(self):
        self.run_test("def dict_(): a=dict()", dict_=[])

    def test_assigned_dict(self):
        self.run_test("def assigned_dict(k):\n a=dict() ; a[k]=18", "yeah", assigned_dict=[str])

    def test_print_empty_dict(self):
        self.run_test("def print_empty_dict():\n print dict()", print_empty_dict=[])

    def test_print_dict(self):
        self.run_test("def print_dict(k):\n a= dict() ; a[k]='youpi'\n print a", 5, print_dict=[int])

    def test_empty_dict(self):
        self.run_test("def empty_dict(): return {}", empty_dict=[])

    def test_initialized_dict(self):
        self.run_test("def initialized_dict(): return {1:'e', 5.2:'f'}", initialized_dict=[])

    def test_dict_contains(self):
        self.run_test("def dict_contains(v): return v in { 'a':1, 'e': 2 }", "e", dict_contains=[str])

    def test_emptydict_contains(self):
        self.run_test("def emptydict_contains(v): return v in dict()", "e", emptydict_contains=[str])

    def test_dict_get_item(self):
        self.run_test("def dict_get_item(a): return a['e']", {'e':1, 'f':2}, dict_get_item=[{str:int}])

    def test_dict_len(self):
        self.run_test("def dict_len(d): return len(d)", {1:'e', 2:'f'}, dict_len=[{int:str}])
    def test_dict_set_item(self):
        self.run_test("def dict_set_item():\n a= dict() ; a[1.5]='s'\n return a", dict_set_item=[])
    def test_dict_set_item_bis(self):
        self.run_test("def dict_set_item_bis():\n a= dict() ; a[1]='s'\n return a", dict_set_item_bis=[])
    def test_dict_clear(self):
        self.run_test("def dict_clear(a):\n a.clear()\n return a", {'e':'E' }, dict_clear=[{str:str}])
    def test_dict_copy(self):
        code="""
def dict_copy(a):
    b = a.copy()
    c = a
    a.clear()
    return c,b"""
        self.run_test(code,  {1:2 }, dict_copy=[{int:int}])

    def test_dict_from_keys(self):
        return self.run_test("def dict_from_keys(a): return dict.fromkeys(a), dict.fromkeys(a,1)", [1.5,2.5,3.5], dict_from_keys=[[float]])

    def test_dict_get(self):
        return self.run_test("def dict_get(a): return a.get(1.5) + a.get(2, 18)", {1.5:2 }, dict_get=[{float:int}])

    def test_dict_get_none(self):
        return self.run_test("def dict_get_none(a): return a.get(1)", {1.5:2 }, dict_get_none=[{float:int}])

    def test_dict_has_key(self):
        return self.run_test("def dict_has_key(a): return (a.has_key(False), a.has_key(True))", {False:0}, dict_has_key=[{bool:int}])

    def test_dict_items(self):
        return self.run_test("def dict_items(a): return sorted(a.items())", { 'a':1, 'e': 2 }, dict_items=[{str:int}])

    def test_dict_for(self):
        return self.run_test("def dict_for(a): return sorted([x for x in a])", { 'a':1, 'e': 2 }, dict_for=[{str:int}])

    def test_dict_iteritems(self):
        return self.run_test("def dict_iteritems(a): return sorted([ x for x in a.iteritems()])", { 'a':1, 'e': 2 }, dict_iteritems=[{str:int}])

    def test_dict_iterkeys(self):
        return self.run_test("def dict_iterkeys(a): return sorted([ x*2 for x in a.iterkeys()])", { 1:'a', 2:'b' }, dict_iterkeys=[{int:str}])

    def test_dict_itervalues(self):
        return self.run_test("def dict_itervalues(a): return sorted([ x*2 for x in a.itervalues()])", { 1:'a', 2:'b' }, dict_itervalues=[{int:str}])

    def test_dict_keys(self):
        return self.run_test("def dict_keys(a): return sorted([ x*2 for x in a.keys()])", { 1:'a', 2:'b' }, dict_keys=[{int:str}])

    def test_dict_values(self):
        return self.run_test("def dict_values(a): return sorted([ x*2 for x in a.values()])", { 1:'a', 2:'b' }, dict_values=[{int:str}])

    def test_dict_pop(self):
        return self.run_test("def dict_pop(a): return a.pop(1), a.pop(3,'e'), a", { 1:'a', 2:'b' }, dict_pop=[{int:str}])

    def test_dict_popitem(self):
        return self.run_test("def dict_popitem(a): return a.popitem(), a", { 1:'a' }, dict_popitem=[{int:str}])

    def test_dict_setdefault(self):
        return self.run_test("def dict_setdefault():\n a={1.5:2 }\n return a.setdefault(1.5) + a.setdefault(2, 18)", dict_setdefault=[])

    def test_dict_update(self):
        return self.run_test("def dict_update(a):\n a.update([(1,'e')])\n a.update({2:'c'})\n return a", { 1:'a', 2:'b' }, dict_update=[{int:str}])

    def test_dict_viewitems(self):
        return self.run_test("def dict_viewitems(a):\n d=a.viewitems()\n return sorted(d)", { 1:'a', 2:'b' }, dict_viewitems=[{int:str}])

    def test_dict_viewkeys(self):
        return self.run_test("def dict_viewkeys(a):\n d=a.viewkeys()\n return sorted(d)", { 1:'a', 2:'b' }, dict_viewkeys=[{int:str}])

    def test_dict_viewvalues(self):
        return self.run_test("def dict_viewvalues(a):\n d=a.viewvalues()\n return sorted(d)", { 1:'a', 2:'b' }, dict_viewvalues=[{int:str}])

    def test_dict_viewitems_contains(self):
        return self.run_test("def dict_viewitems_contains(a):\n d=a.viewitems()\n return (1,'a') in d, (2,'e') in d", { 1:'a', 2:'b' }, dict_viewitems_contains=[{int:str}])

    def test_dict_viewkeys_contains(self):
        return self.run_test("def dict_viewkeys_contains(a):\n d=a.viewkeys()\n return 1 in d, 3 in d", { 1:'a', 2:'b' }, dict_viewkeys_contains=[{int:str}])

    def test_dict_viewvalues_contains(self):
        return self.run_test("def dict_viewvalues_contains(a):\n d=a.viewvalues()\n return 'a' in d, 'e' in d", { 1:'a', 2:'b' }, dict_viewvalues_contains=[{int:str}])

    def test_dict_update_combiner(self):
        return self.run_test("def dict_update_combiner():\n a=dict()\n a.update({1:'e'})\n return a", dict_update_combiner=[])

    def test_dict_setdefault_combiner(self):
        return self.run_test("def dict_setdefault_combiner():\n a=dict()\n a.setdefault(1,'e')\n return a", dict_setdefault_combiner=[])

########NEW FILE########
__FILENAME__ = test_doc
import unittest
import doctest
import pythran
import inspect
import os

class TestDoctest(unittest.TestCase):
    '''
    Enable automatic doctest integration to unittest

    Every module in the pythran package is scanned for doctests
    and one test per module is created
    '''
    def test_tutorial(self):
        failed, _ = doctest.testfile('../../doc/TUTORIAL.rst')
        self.assertEqual(failed, 0)

    def test_internal(self):
        tmpfile = self.adapt_rst('../../doc/INTERNAL.rst')
        failed, _ = doctest.testfile(tmpfile, False)
        self.assertEqual(failed, 0)
        os.remove(tmpfile)

    def test_cli(self):
        tmpfile = self.adapt_rst('../../doc/CLI.rst')
        failed, _ = doctest.testfile(tmpfile, False)
        self.assertEqual(failed, 0)
        os.remove(tmpfile)

    def adapt_rst(self, relative_path):
        """
        replace '$>' with '>>>' and execute theses command lines by creating a shell
        return the path of the new adapted tmp file
        """
        import re
        from tempfile import NamedTemporaryFile
        filepath = os.path.join(os.path.dirname(__file__), relative_path)
        rst_doc = file(filepath).read()
        rst_doc = re.sub(r'\.\.(\s+>>>)', r'\1', rst_doc)  # hidden doctest
        sp = re.sub(r'\$>(.*?)$',
                    r'>>> import subprocess ; print subprocess.check_output("\1", shell=True),',
                    rst_doc,
                    flags=re.MULTILINE)
        f = NamedTemporaryFile(delete=False)
        f.write(sp)
        f.close()
        return f.name

def generic_test_package(self, mod):
    failed, _ = doctest.testmod(mod)
    self.assertEqual(failed, 0)

def add_module_doctest(module_name):
    module = getattr(pythran, module_name)
    if inspect.ismodule(module):
        setattr(TestDoctest, 'test_' + module_name,
            lambda self: generic_test_package(self, module))

map(add_module_doctest, dir(pythran))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_env
from pythran import compile_pythrancode
from pythran.backend import Python
from pythran.middlend import refine
from pythran.passmanager import PassManager
from pythran.toolchain import _parse_optimization
import pythran.frontend as frontend
from imp import load_dynamic
import unittest
import os
import re
import sys
from numpy import ndarray
import numpy.testing as npt
import ast


class TestEnv(unittest.TestCase):
    """
    Test environment to validate a pythran execution against python
    """

    # default options used for the c++ compiler
    PYTHRAN_CXX_FLAGS = ['-O0', '-fopenmp',
                         '-Wall', '-Wno-unknown-pragmas']
    TEST_RETURNVAL = "TEST_RETURNVAL"

    def assertAlmostEqual(self, ref, res):
        if hasattr(ref, '__iter__'):
            if isinstance(ref, ndarray):
                npt.assert_array_almost_equal(ref, res)
            else:
                self.assertEqual(len(ref), len(res))
                for iref, ires in zip(ref, res):
                    self.assertAlmostEqual(iref, ires)
        else:
            try:
                unittest.TestCase.assertAlmostEqual(self, ref, res)
            except TypeError:
                raise AssertionError("Reference mismatch: pythran return value"
                                     " differs from python.")

    def compare_pythonpythran_results(self, python_ref, pythran_res):
        # Compare pythran result against python ref and raise if mismatch
        try:
            if python_ref != pythran_res:
                print "Python result: ", python_ref
                print "Pythran result: ", pythran_res
                self.assertAlmostEqual(python_ref, pythran_res)
        except ValueError:
            if hasattr(python_ref, '__iter__'):
                self.assertEqual(len(python_ref), len(pythran_res))
                for iref, ires in zip(python_ref, pythran_res):
                    self.assertAlmostEqual(iref, ires)

    def run_test(self, code, *params, **interface):
        """Test if a function call return value is unchanged when
        executed using python eval or compiled with pythran.

        Args:
           code (str):  python (pythran valid) module to test.
           params (tuple): arguments to pass to the function to test.
           prelude (fct): function to call between 'code' and the c++
                          generated code
           interface (dict): pythran interface for the module to test.
                             Each key is the name of a function to call,
                             the value is a list of the arguments' type.
                             Special keys are 'module_name', 'prelude',
                             'runas', 'check_refcount', 'check_exception'
                             and 'check_output'.

        Returns: nothing.

        Raises:
           AssertionError by 'unittest' if return value differ.
           SyntaxError if code is not python valid.
           pythran.CompileError if generated code can't be compiled.
           ...possibly others...
        """

        # Extract special keys from interface.
        module_name = interface.pop('module_name', None)
        prelude = interface.pop('prelude', None)
        check_output = interface.pop('check_output', True)
        runas = interface.pop('runas', None)
        check_refcount = interface.pop('check_refcount', False)
        check_exception = interface.pop('check_exception', False)
        if runas:
            # runas is a python code string to run the test. By convention
            # the last statement of the sequence is the value to test.
            # We insert ourselves a variable to capture this value:
            # "a=1; b=2; myfun(a+b,a-b)" => "a=1; b=2; RES=myfun(a+b,a-b)"
            runas_commands = runas.split(";")
            begin = ";".join(runas_commands[:-1]+[''])
            exec code+"\n"+begin in {}  # this just tests the syntax of runas
            last = self.TEST_RETURNVAL + '=' + runas_commands[-1]
            runas = begin+"\n"+last

        for name in sorted(interface.keys()):
            if not runas:
                # No runas provided, derive one from interface and params
                attributes = []
                runas = ""
                for p in params:
                    if isinstance(p, str):
                        param = "'{0}'".format(p)
                    elif isinstance(p, ndarray):
                        param = "numpy.{0}".format(
                            repr(p).replace("\n", "")
                                   .replace("dtype=", "dtype=numpy."))
                        runas = "import numpy\n"
                    else:
                         # repr preserve the "L" suffix for long
                        param = repr(p)
                    attributes.append(param.replace("nan", "float('nan')")
                                           .replace("inf", "float('inf')"))
                arglist = ",".join(attributes)
                function_call = "{0}({1})".format(name, arglist)
                runas += self.TEST_RETURNVAL + '=' + function_call

            # Caller may requires some cleaning
            prelude and prelude()

            # Produce the reference, python-way, run in an separated 'env'
            env = {'__builtin__': __import__('__builtin__')}
            refcode = code+"\n"+runas

            # Compare if exception raised in python and in pythran are the same
            python_exception_type = None
            pythran_exception_type = None
            try:
                if check_output:
                    exec refcode in env
                    python_ref = env[self.TEST_RETURNVAL]
                    if check_refcount:
                        python_refcount = sys.getrefcount(python_ref)
            except BaseException as e:
                python_exception_type = type(e)
                if not check_exception:
                    raise

            # If no module name was provided, create one
            modname = module_name or ("test_" + name)

            # Compile the code using pythran
            cxx_compiled = compile_pythrancode(modname, code,
                interface, cxxflags=self.PYTHRAN_CXX_FLAGS)

            try:
                if not check_output:
                    return

                # Caller may requires some cleaning
                prelude and prelude()
                pymod = load_dynamic(modname, cxx_compiled)

                try:
                    # Produce the pythran result, exec in the loaded module ctx
                    exec runas in pymod.__dict__
                except BaseException as e:
                    pythran_exception_type = type(e)
                else:
                    pythran_res = getattr(pymod, self.TEST_RETURNVAL)
                    if check_refcount:
                        pythran_refcount = sys.getrefcount(pythran_res)
                        self.assertEqual(python_refcount, pythran_refcount)
                    # Test Results, assert if mismatch
                    if python_exception_type:
                        raise AssertionError(
                                "expected exception was %s, but nothing happend!" %
                                python_exception_type)
                    self.compare_pythonpythran_results(python_ref, pythran_res)

            finally:
                # Clean temporary DLL
                os.remove(cxx_compiled)

            # Only compare the type of exceptions raised
            if pythran_exception_type != python_exception_type:
                if python_exception_type is None:
                    raise e
                else:
                    raise AssertionError(
                    "expected exception was %s, but received %s" %
                    (python_exception_type, pythran_exception_type))

    def check_ast(self, code, ref, optimizations):
        """
            Check if a final node is the same as expected

            Parameters
            ----------
            code : str
                code we want to check after refine and optimizations
            ref : str
                The expected dump for the AST
            optimizations : [optimization]
                list of optimisation to apply

            Raises
            ------
            is_same : AssertionError
                Raise if the result is not the one expected.
        """
        pm = PassManager("testing")

        ir, _ = frontend.parse(pm, code)

        optimizations = map(_parse_optimization, optimizations)
        refine(pm, ir, optimizations)

        content = pm.dump(Python, ir)

        if content != ref:
            raise AssertionError(
            "AST is not the one expected. Reference was %s,"
            "but received %s" % (repr(ref), repr(content)))


class TestFromDir(TestEnv):
    """ This class load test from individual .py in a directory and expose
    them to the unittest framework. Methods are added to the class (not the
    instance object) because py.test will collect tests by introspection before
    eventually instanciating the classe for each test.

    It is intended to be subclassed and then initialized using the static
    populate() method.

    A few class attributes defined the behavior:

    check_output -- Trigger code execution and match return value for Pythran
                    compiled code against pure python. If set to False, only
                    the compilation step is checked.
    files        -- list of files to load, if empty path is used (see below)
    path         -- path where every .py will be loaded
    interface    -- method returning the Pythran interface to use (dict)

    """

    check_output = True
    files = None
    path = "defined_by_subclass"
    runas_marker = '#runas '

    @classmethod
    def interface(cls, name=None, file=None):
        ''' Return Pythran specs.'''
        default_value = {name: []}
        try:
            from pythran import spec_parser
            specs = spec_parser(open(file).read()) if file else default_value
        except SyntaxError:
            specs = default_value
        return specs

    def __init__(self, *args, **kwargs):
        # Dynamically add methods for unittests, second stage (cf populate())
        TestFromDir.populate(self, stub=False)

        super(TestFromDir, self).__init__(*args, **kwargs)

    class TestFunctor(object):
        """ This Functor holds for test_* dynamically added method, one per
        input file. It takes at initialization all the informations required
        for a straightforward dispatch to TestEnv.run_test()

        """

        def __init__(
            self, test_env, module_name, module_code, check_output=True,
                runas=None, **specs):
            self.test_env = test_env
            self.module_name = module_name
            self.module_code = module_code
            self.runas = runas
            self.specs = specs
            self.check_output = check_output

        def __name__(self):
            return self.module_name

        def __call__(self):
            if "unittest.skip" in self.module_code:
                return self.test_env.skipTest("Marked as skippable")
            self.test_env.run_test(self.module_code,
                                   module_name=self.module_name,
                                   check_output=self.check_output,
                                   runas=self.runas,
                                   **self.specs)

    @staticmethod
    def populate(target, stub=True):
        """Add unittests methods to `target`.

        The python unittest framework detect method named test_* by
        introspection on the class before instanciation. Unfortunately to
        access the TestEnv instance from the method the Functor has to be
        initialized after `target` instantiation. Thus there is a two-stage
        initialization: first we populate the class with 'stub' functions, just
        to satisfy python unittest collect, and then at intanciation the stub
        are replace with the Functor properly initialized with a reference to
        "self"

        """
        import glob
        if not target.files:
            # No explicit list of files, default to load the whole directory
            target.files = glob.glob(os.path.join(target.path, "*.py"))

        for filepath in target.files:
            # Module name is file name, also external interface default value
            name, _ = os.path.splitext(os.path.basename(filepath))
            specs = target.interface(name, filepath)
            runas_list = [line for line in file(filepath).readlines()
                          if line.startswith(TestFromDir.runas_marker)]
            runas_list = runas_list or [None]
            runcount = 0
            for n, runas in enumerate(runas_list):
                if runas:
                    runas = runas.replace(TestFromDir.runas_marker, '')
                    runcount = runcount+1
                    suffix = "_run"+str(runcount)
                else:
                    suffix = '_norun'
                if stub:
                    func = lambda: None
                else:
                    func = TestFromDir.TestFunctor(target, name,
                        file(filepath).read(), runas=runas,
                        check_output=(runas is not None), **specs)

                setattr(target, "test_"+name+suffix+str(n), func)

########NEW FILE########
__FILENAME__ = test_euler
import unittest
from test_env import TestFromDir
import os
import glob

class TestEuler(TestFromDir):
    path = os.path.join(os.path.dirname(__file__),"euler")
    files = glob.glob(os.path.join(path,"euler*.py"))

TestEuler.populate(TestEuler)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_exception
from test_env import TestEnv
import unittest

class TestException(TestEnv):

    def test_BaseException(self):
        self.run_test("def BaseException_():\n try: raise BaseException('a','b','c')\n except BaseException as e: return e.args", BaseException_=[])

    def test_SystemExit(self):
        self.run_test("def SystemExit_():\n try: raise SystemExit('a','b','c')\n except SystemExit as e: return e.args", SystemExit_=[])

    def test_KeyboardInterrupt(self):
        self.run_test("def KeyboardInterrupt_():\n try: raise KeyboardInterrupt('a','b','c')\n except KeyboardInterrupt as e: return e.args", KeyboardInterrupt_=[])

    def test_GeneratorExit(self):
        self.run_test("def GeneratorExit_():\n try: raise GeneratorExit('a','b','c')\n except GeneratorExit as e: return e.args", GeneratorExit_=[])

    def test_Exception(self):
        self.run_test("def Exception_():\n try: raise Exception('a','b','c')\n except Exception as e: return e.args", Exception_=[])

    def test_StopIteration(self):
        self.run_test("def StopIteration_():\n try: raise StopIteration('a','b','c')\n except StopIteration as e: return e.args", StopIteration_=[])

    def test_StandardError(self):
        self.run_test("def StandardError_():\n try: raise StandardError('a','b','c')\n except StandardError as e: return e.args", StandardError_=[])

    def test_Warning(self):
        self.run_test("def Warning_():\n try: raise Warning('a','b','c')\n except Warning as e: return e.args", Warning_=[])

    def test_BytesWarning(self):
        self.run_test("def BytesWarning_():\n try: raise BytesWarning('a','b','c')\n except BytesWarning as e: return e.args", BytesWarning_=[])

    def test_UnicodeWarning(self):
        self.run_test("def UnicodeWarning_():\n try: raise UnicodeWarning('a','b','c')\n except UnicodeWarning as e: return e.args", UnicodeWarning_=[])

    def test_ImportWarning(self):
        self.run_test("def ImportWarning_():\n try: raise ImportWarning('a','b','c')\n except ImportWarning as e: return e.args", ImportWarning_=[])

    def test_FutureWarning(self):
        self.run_test("def FutureWarning_():\n try: raise FutureWarning('a','b','c')\n except FutureWarning as e: return e.args", FutureWarning_=[])

    def test_UserWarning(self):
        self.run_test("def UserWarning_():\n try: raise UserWarning('a','b','c')\n except UserWarning as e: return e.args", UserWarning_=[])

    def test_SyntaxWarning(self):
        self.run_test("def SyntaxWarning_():\n try: raise SyntaxWarning('a','b','c')\n except SyntaxWarning as e: return e.args", SyntaxWarning_=[])

    def test_RuntimeWarning(self):
        self.run_test("def RuntimeWarning_():\n try: raise RuntimeWarning('a','b','c')\n except RuntimeWarning as e: return e.args", RuntimeWarning_=[])

    def test_PendingDeprecationWarning(self):
        self.run_test("def PendingDeprecationWarning_():\n try: raise PendingDeprecationWarning('a','b','c')\n except PendingDeprecationWarning as e: return e.args", PendingDeprecationWarning_=[])

    def test_DeprecationWarning(self):
        self.run_test("def DeprecationWarning_():\n try: raise DeprecationWarning('a','b','c')\n except DeprecationWarning as e: return e.args", DeprecationWarning_=[])

    def test_BufferError(self):
        self.run_test("def BufferError_():\n try: raise BufferError('a','b','c')\n except BufferError as e: return e.args", BufferError_=[])

    def test_ArithmeticError(self):
        self.run_test("def ArithmeticError_():\n try: raise ArithmeticError('a','b','c')\n except ArithmeticError as e: return e.args", ArithmeticError_=[])

    @unittest.skip("incompatible with py.test")
    def test_AssertionError(self):
        self.run_test("def AssertionError_():\n try: raise AssertionError('a','b','c')\n except AssertionError as e: return e.args", AssertionError_=[])

    def test_AttributeError(self):
        self.run_test("def AttributeError_():\n try: raise AttributeError('a','b','c')\n except AttributeError as e: return e.args", AttributeError_=[])

    def test_EnvironmentError4(self):
        self.run_test("def EnvironmentError4_():\n try: raise EnvironmentError('a','b','c','d')\n except EnvironmentError as e: return e.args", EnvironmentError4_=[])

    def test_EnvironmentError3(self):
        self.run_test("def EnvironmentError3_():\n try: raise EnvironmentError('a','b','c')\n except EnvironmentError as e: return e.args", EnvironmentError3_=[])

    def test_EnvironmentError2(self):
        self.run_test("def EnvironmentError2_():\n try: raise EnvironmentError('a','b')\n except EnvironmentError as e: return e.args", EnvironmentError2_=[])

    def test_EnvironmentError1(self):
        self.run_test("def EnvironmentError1_():\n try: raise EnvironmentError('a')\n except EnvironmentError as e: return e.args", EnvironmentError1_=[])

    def test_EOFError(self):
        self.run_test("def EOFError_():\n try: raise EOFError('a','b','c')\n except EOFError as e: return e.args", EOFError_=[])

    def test_ImportError(self):
        self.run_test("def ImportError_():\n try: raise ImportError('a','b','c')\n except ImportError as e: return e.args", ImportError_=[])

    def test_LookupError(self):
        self.run_test("def LookupError_():\n try: raise LookupError('a','b','c')\n except LookupError as e: return e.args", LookupError_=[])

    def test_MemoryError(self):
        self.run_test("def MemoryError_():\n try: raise MemoryError('a','b','c')\n except MemoryError as e: return e.args", MemoryError_=[])

    def test_NameError(self):
        self.run_test("def NameError_():\n try: raise NameError('a','b','c')\n except NameError as e: return e.args", NameError_=[])

    def test_ReferenceError(self):
        self.run_test("def ReferenceError_():\n try: raise ReferenceError('a','b','c')\n except ReferenceError as e: return e.args", ReferenceError_=[])

    def test_RuntimeError(self):
        self.run_test("def RuntimeError_():\n try: raise RuntimeError('a','b','c')\n except RuntimeError as e: return e.args", RuntimeError_=[])

    def test_SyntaxError(self):
        self.run_test("def SyntaxError_():\n try: raise SyntaxError('a','b','c')\n except SyntaxError as e: return e.args", SyntaxError_=[])

    def test_SystemError(self):
        self.run_test("def SystemError_():\n try: raise SystemError('a','b','c')\n except SystemError as e: return e.args", SystemError_=[])

    def test_TypeError(self):
        self.run_test("def TypeError_():\n try: raise TypeError('a','b','c')\n except TypeError as e: return e.args", TypeError_=[])

    def test_ValueError(self):
        self.run_test("def ValueError_():\n try: raise ValueError('a','b','c')\n except ValueError as e: return e.args", ValueError_=[])

    def test_FloatingPointError(self):
        self.run_test("def FloatingPointError_():\n try: raise FloatingPointError('a','b','c')\n except FloatingPointError as e: return e.args", FloatingPointError_=[])

    def test_OverflowError(self):
        self.run_test("def OverflowError_():\n try: raise OverflowError('a','b','c')\n except OverflowError as e: return e.args", OverflowError_=[])

    def test_ZeroDivisionError(self):
        self.run_test("def ZeroDivisionError_():\n try: raise ZeroDivisionError('a','b','c')\n except ZeroDivisionError as e:\n  return e.args", ZeroDivisionError_=[])

    def test_IOError(self):
        self.run_test("def IOError_():\n try: raise IOError('a','b','c')\n except IOError as e: return e.args", IOError_=[])

    def test_OSError(self):
        self.run_test("def OSError_():\n try: raise OSError('a','b','c')\n except OSError as e: return e.args", OSError_=[])

    def test_IndexError(self):
        self.run_test("def IndexError_():\n try: raise IndexError('a','b','c')\n except IndexError as e: return e.args", IndexError_=[])

    def test_KeyError(self):
        self.run_test("def KeyError_():\n try: raise KeyError('a','b','c')\n except KeyError as e: return e.args", KeyError_=[])

    def test_UnboundLocalError(self):
        self.run_test("def UnboundLocalError_():\n try: raise UnboundLocalError('a','b','c')\n except UnboundLocalError as e: return e.args", UnboundLocalError_=[])

    def test_NotImplementedError(self):
        self.run_test("def NotImplementedError_():\n try: raise NotImplementedError('a','b','c')\n except NotImplementedError as e: return e.args", NotImplementedError_=[])

    def test_IndentationError(self):
        self.run_test("def IndentationError_():\n try: raise IndentationError('a','b','c')\n except IndentationError as e: return e.args", IndentationError_=[])

    def test_TabError(self):
        self.run_test("def TabError_():\n try: raise TabError('a','b','c')\n except TabError as e: return e.args", TabError_=[])

    def test_UnicodeError(self):
        self.run_test("def UnicodeError_():\n try: raise UnicodeError('a','b','c')\n except UnicodeError as e: return e.args", UnicodeError_=[])

    def test_multiple_exception(self):
        self.run_test("def multiple_exception_():\n try:\n  raise OverflowError('a','b','c')\n except IOError as e:\n  a=2 ; print a ; return e.args\n except OverflowError as e:\n  return e.args", multiple_exception_=[])

    def test_multiple_tuple_exception(self):
        self.run_test("def multiple_tuple_exception_():\n try:\n  raise OverflowError('a','b','c')\n except (IOError, OSError):\n  a=3;print a\n except OverflowError as e:\n  return e.args", multiple_tuple_exception_=[])

    def test_reraise_exception(self):
        self.run_test("def reraise_exception_():\n try:\n  raise OverflowError('a','b','c')\n except IOError:\n  raise\n except:  return 'ok'", reraise_exception_=[])

    def test_raiseinst_exception(self):
        self.run_test("def raiseinst_exception_():\n try:\n  raise OverflowError, ('a','b','c')\n except OverflowError as e:\n  return e.args", raiseinst_exception_=[])

    def test_else2_exception(self):
        self.run_test("def else2_exception_():\n try:\n  raise 1\n  return 0,'bad'\n except:\n  a=2\n else:\n  return 0,'bad2'\n return a,'ok'", else2_exception_=[])

    def test_else_exception(self):
        self.run_test("def else_exception_():\n try:\n  a=2\n except:\n  return 0,'bad'\n else:\n  return a,'ok'\n return 0,'bad2'", else_exception_=[])

    def test_enverror_exception(self):
        self.run_test("def enverror_exception_():\n try:\n  raise EnvironmentError('a','b','c')\n except EnvironmentError as e:\n  return (e.errno,e.strerror,e.filename)", enverror_exception_=[])

    def test_finally_exception(self):
        self.run_test("def finally_exception_():\n try:\n  a=2\n except:\n  return 0,'bad'\n finally:\n  return a,'good'", finally_exception_=[])

    def test_finally2_exception(self):
        self.run_test("def finally2_exception_():\n try:\n  raise 1\n  return 0,'bad'\n except:\n  a=2\n finally:\n  return a,'good'", finally2_exception_=[])

    def test_str1_exception(self):
        self.run_test("def str1_exception_():\n try:\n  raise EnvironmentError('a')\n except EnvironmentError as e:\n  return str(e)", str1_exception_=[])

    def test_str2_exception(self):
        self.run_test("def str2_exception_():\n try:\n  raise EnvironmentError('a','b')\n except EnvironmentError as e:\n  return str(e)", str2_exception_=[])

    def test_str3_exception(self):
        self.run_test("def str3_exception_():\n try:\n  raise EnvironmentError('a','b','c')\n except EnvironmentError as e:\n  return str(e)", str3_exception_=[])

    def test_str4_exception(self):
        self.run_test("def str4_exception_():\n try:\n  raise EnvironmentError('a','b','c','d')\n except EnvironmentError as e:\n  return str(e)", str4_exception_=[])

    def test_str5_exception(self):
        self.run_test("def str5_exception_():\n try:\n  raise EnvironmentError('a','b','c','d','e')\n except EnvironmentError as e:\n  return str(e)", str5_exception_=[])

    def test_no_msg_exception(self):
        self.run_test("def no_msg_exception_():\n try: raise IndexError()\n except IndexError as e: return e.args", no_msg_exception_=[])

# test if exception translators are registered in pythran

    def test_BaseException_register(self):
        self.run_test("def BaseException_(): raise BaseException('abc')", BaseException_=[], check_exception=True)

    def test_SystemExit_register(self):
        self.run_test("def SystemExit_():\n raise SystemExit('a','b','c')", SystemExit_=[], check_exception=True)

    def test_KeyboardInterrupt_register(self):
        self.run_test("def KeyboardInterrupt_():\n raise KeyboardInterrupt('a','b','c')", KeyboardInterrupt_=[], check_exception=True)

    def test_GeneratorExit_register(self):
        self.run_test("def GeneratorExit_():\n raise GeneratorExit('a','b','c')", GeneratorExit_=[], check_exception=True)

    def test_Exception_register(self):
        self.run_test("def Exception_():\n raise Exception('a','b','c')", Exception_=[], check_exception=True)

    def test_StopIteration_register(self):
        self.run_test("def StopIteration_():\n raise StopIteration('a','b','c')", StopIteration_=[], check_exception=True)

    def test_StandardError_register(self):
        self.run_test("def StandardError_():\n raise StandardError('a','b','c')", StandardError_=[], check_exception=True)

    def test_Warning_register(self):
        self.run_test("def Warning_():\n raise Warning('a','b','c')", Warning_=[], check_exception=True)

    def test_BytesWarning_register(self):
        self.run_test("def BytesWarning_():\n raise BytesWarning('a','b','c')", BytesWarning_=[], check_exception=True)

    def test_UnicodeWarning_register(self):
        self.run_test("def UnicodeWarning_():\n raise UnicodeWarning('a','b','c')", UnicodeWarning_=[], check_exception=True)

    def test_ImportWarning_register(self):
        self.run_test("def ImportWarning_():\n raise ImportWarning('a','b','c')", ImportWarning_=[], check_exception=True)

    def test_FutureWarning_register(self):
        self.run_test("def FutureWarning_():\n raise FutureWarning('a','b','c')", FutureWarning_=[], check_exception=True)

    def test_UserWarning_register(self):
        self.run_test("def UserWarning_():\n raise UserWarning('a','b','c')", UserWarning_=[], check_exception=True)

    def test_SyntaxWarning_register(self):
        self.run_test("def SyntaxWarning_():\n raise SyntaxWarning('a','b','c')", SyntaxWarning_=[], check_exception=True)

    def test_RuntimeWarning_register(self):
        self.run_test("def RuntimeWarning_():\n raise RuntimeWarning('a','b','c')", RuntimeWarning_=[], check_exception=True)

    def test_PendingDeprecationWarning_register(self):
        self.run_test("def PendingDeprecationWarning_():\n raise PendingDeprecationWarning('a','b','c')", PendingDeprecationWarning_=[], check_exception=True)

    def test_DeprecationWarning_register(self):
        self.run_test("def DeprecationWarning_():\n raise DeprecationWarning('a','b','c')", DeprecationWarning_=[], check_exception=True)

    def test_BufferError_register(self):
        self.run_test("def BufferError_():\n raise BufferError('a','b','c')", BufferError_=[], check_exception=True)

    def test_ArithmeticError_register(self):
        self.run_test("def ArithmeticError_():\n raise ArithmeticError('a','b','c')", ArithmeticError_=[], check_exception=True)

    @unittest.skip("incompatible with py.test")
    def test_AssertionError_register(self):
        self.run_test("def AssertionError_():\n raise AssertionError('a','b','c')", AssertionError_=[], check_exception=True)

    def test_AttributeError_register(self):
        self.run_test("def AttributeError_():\n raise AttributeError('a','b','c')", AttributeError_=[], check_exception=True)

    def test_EnvironmentError4_register(self):
        self.run_test("def EnvironmentError4_():\n raise EnvironmentError('a','b','c','d')", EnvironmentError4_=[], check_exception=True)

    def test_EnvironmentError3_register(self):
        self.run_test("def EnvironmentError3_():\n raise EnvironmentError('a','b','c')", EnvironmentError3_=[], check_exception=True)

    def test_EnvironmentError2_register(self):
        self.run_test("def EnvironmentError2_():\n raise EnvironmentError('a','b')", EnvironmentError2_=[], check_exception=True)

    def test_EnvironmentError1_register(self):
        self.run_test("def EnvironmentError1_():\n raise EnvironmentError('a')", EnvironmentError1_=[], check_exception=True)

    def test_EOFError_register(self):
        self.run_test("def EOFError_():\n raise EOFError('a','b','c')", EOFError_=[], check_exception=True)

    def test_ImportError_register(self):
        self.run_test("def ImportError_():\n raise ImportError('a','b','c')", ImportError_=[], check_exception=True)

    def test_LookupError_register(self):
        self.run_test("def LookupError_():\n raise LookupError('a','b','c')", LookupError_=[], check_exception=True)

    def test_MemoryError_register(self):
        self.run_test("def MemoryError_():\n raise MemoryError('a','b','c')", MemoryError_=[], check_exception=True)

    def test_NameError_register(self):
        self.run_test("def NameError_():\n raise NameError('a','b','c')", NameError_=[], check_exception=True)

    def test_ReferenceError_register(self):
        self.run_test("def ReferenceError_():\n raise ReferenceError('a','b','c')", ReferenceError_=[], check_exception=True)

    def test_RuntimeError_register(self):
        self.run_test("def RuntimeError_():\n raise RuntimeError('a','b','c')", RuntimeError_=[], check_exception=True)

    def test_SyntaxError_register(self):
        self.run_test("def SyntaxError_():\n raise SyntaxError('a','b','c')", SyntaxError_=[], check_exception=True)

    def test_SystemError_register(self):
        self.run_test("def SystemError_():\n raise SystemError('a','b','c')", SystemError_=[], check_exception=True)

    def test_TypeError_register(self):
        self.run_test("def TypeError_():\n raise TypeError('a','b','c')", TypeError_=[], check_exception=True)

    def test_ValueError_register(self):
        self.run_test("def ValueError_():\n raise ValueError('a','b','c')", ValueError_=[], check_exception=True)

    def test_FloatingPointError_register(self):
        self.run_test("def FloatingPointError_():\n raise FloatingPointError('a','b','c')", FloatingPointError_=[], check_exception=True)

    def test_OverflowError_register(self):
        self.run_test("def OverflowError_():\n raise OverflowError('a','b','c')", OverflowError_=[], check_exception=True)

    def test_ZeroDivisionError_register(self):
        self.run_test("def ZeroDivisionError_():\n raise ZeroDivisionError('a','b','c')", ZeroDivisionError_=[], check_exception=True)

    def test_IOError_register(self):
        self.run_test("def IOError_():\n raise IOError('a','b','c')", IOError_=[], check_exception=True)

    def test_OSError_register(self):
        self.run_test("def OSError_():\n raise OSError('a','b','c')", OSError_=[], check_exception=True)

    def test_IndexError_register(self):
        self.run_test("def IndexError_():\n raise IndexError('a','b','c')", IndexError_=[], check_exception=True)

    def test_KeyError_register(self):
        self.run_test("def KeyError_():\n raise KeyError('a','b','c')", KeyError_=[], check_exception=True)

    def test_UnboundLocalError_register(self):
        self.run_test("def UnboundLocalError_():\n raise UnboundLocalError('a','b','c')", UnboundLocalError_=[], check_exception=True)

    def test_NotImplementedError_register(self):
        self.run_test("def NotImplementedError_():\n raise NotImplementedError('a','b','c')", NotImplementedError_=[], check_exception=True)

    def test_IndentationError_register(self):
        self.run_test("def IndentationError_():\n raise IndentationError('a','b','c')", IndentationError_=[], check_exception=True)

    def test_TabError_register(self):
        self.run_test("def TabError_():\n raise TabError('a','b','c')", TabError_=[], check_exception=True)

    def test_UnicodeError_register(self):
        self.run_test("def UnicodeError_():\n raise UnicodeError('a','b','c')", UnicodeError_=[], check_exception=True)

    def test_multiple_exception_register(self):
        self.run_test("def multiple_exception_():\n raise OverflowError('a','b','c')", multiple_exception_=[], check_exception=True)

    def test_multiple_tuple_exception_register(self):
        self.run_test("def multiple_tuple_exception_():\n raise OverflowError('a','b','c')", multiple_tuple_exception_=[], check_exception=True)

    def test_reraise_exception_register(self):
        self.run_test("def reraise_exception_():\n raise OverflowError('a','b','c')", reraise_exception_=[], check_exception=True)

    def test_raiseinst_exception_register(self):
        self.run_test("def raiseinst_exception_():\n raise OverflowError, ('a','b','c')", raiseinst_exception_=[], check_exception=True)

    def test_enverror_exception_register(self):
        self.run_test("def enverror_exception_():\n raise EnvironmentError('a','b','c')", enverror_exception_=[], check_exception=True)

    def test_str1_exception_register(self):
        self.run_test("def str1_exception_():\n raise EnvironmentError('a')", str1_exception_=[], check_exception=True)

    def test_str2_exception_register(self):
        self.run_test("def str2_exception_():\n raise EnvironmentError('a','b')", str2_exception_=[], check_exception=True)

    def test_str3_exception_register(self), check_exception=True:
        self.run_test("def str3_exception_():\n raise EnvironmentError('a','b','c')", str3_exception_=[], check_exception=True)

    def test_str4_exception_register(self):
        self.run_test("def str4_exception_():\n raise EnvironmentError('a','b','c','d')", str4_exception_=[], check_exception=True)

    def test_str5_exception_register(self):
        self.run_test("def str5_exception_():\n raise EnvironmentError('a','b','c','d','e')", str5_exception_=[], check_exception=True)

    def test_no_msg_exception_register(self):
        self.run_test("def no_msg_exception_():\n raise IndexError()", no_msg_exception_=[], check_exception=True)

########NEW FILE########
__FILENAME__ = test_file
import unittest
from tempfile import mkstemp
from test_env import TestEnv

class TestFile(TestEnv):

    def __init__(self, *args, **kwargs):
            super(TestEnv, self).__init__(*args, **kwargs)
            self.file_content = """azerty\nqwerty\n\n"""

    def tempfile(self):
            filename=mkstemp()[1]
            f=open(filename,"w")
            f.write(self.file_content)
            f.close()
            self.filename = filename
            return filename

    def reinit_file(self):
            f=open(self.filename,"w")
            f.write(self.file_content)
            f.close()
            return self.filename

    def test_filename_only_constructor(self):
            filename=mkstemp()[1]
            self.run_test("def filename_only_constructor(filename):\n file(filename)", filename, filename_only_constructor=[str])

    def test_open(self):
            filename=mkstemp()[1]
            self.run_test("def _open(filename):\n file(filename)", filename, _open=[str])

    def test_open_write(self):
            filename=mkstemp()[1]
            self.run_test("""def _open_write(filename):\n f=file(filename,"w+")\n f.write("azert")""", filename, _open_write=[str])
            assert(open(filename).read()== "azert")

    def test_open_append(self):
            filename=mkstemp()[1]
            self.run_test("""def _open_append(filename):\n f=file(filename,"a")\n f.write("azert")""", filename, _open_append=[str])
            assert(open(filename).read()== "azert"*2)

    def test_open_bit(self):
            filename=mkstemp()[1]
            self.tempfile()
            self.run_test("""def _open_bit(filename):\n f=file(filename,"rb")\n return f.read()""", filename, _open_bit=[str])

    def test_writing_mode_constructor(self):
            # Expecting file to be erased.
            # But python execution of test will erase it before pythran can :s
            self.tempfile()
            self.run_test("""def writing_mode_constructor(filename):\n f=file(filename, "w")\n f.close()""", self.filename,prelude=self.reinit_file, writing_mode_constructor=[str])
            assert(open(self.filename).read()=="")

    #TODO : tester le differents modes du constructeur

    def test_write(self):
            self.filename=mkstemp()[1]
            content="""q2\naze23\n"""
            self.run_test("""def _write(filename):\n f=file(filename,'a+')\n f.write("""+str('str("""q2\naze23\n""")')+""")\n f.close()""", self.filename, _write=[str])
            assert(open(self.filename).read()==content*2)

    def test_writelines(self):
            self.filename=mkstemp()[1]
            content=["""azerty""", "qsdfgh", "12345524"]
            self.run_test("""def _writelines(filename,_content):\n f=file(filename,'a+')\n f.writelines(_content)\n f.close()""", self.filename, content, _writelines=[str, [str]])
            assert(open(self.filename).read()==str().join(content)*2)

    def test_close(self):
        filename=mkstemp()[1]
        self.run_test("""
def file_close(filename):
	f=file(filename,'w')
	f.close()
	try: 
		f.write("q")
	except:pass""", filename, file_close=[str])

    def test_read(self):
            self.tempfile()
            self.run_test("def _read(filename):\n f=file(filename)\n return f.read()", self.filename, _read=[str])

    def test_read_size(self):
            self.tempfile()
            self.run_test("def _read_size(filename, size):\n f=file(filename)\n return f.read(size)", self.filename, 10, _read_size=[str, int])

    def test_read_oversize(self):
            self.tempfile()
            self.run_test("def _read_oversize(filename, size):\n f=file(filename)\n return f.read(size)", self.filename, len(self.file_content)+5, _read_oversize=[str, int])

    def test_readline(self):
            self.tempfile()
            self.run_test("def _readline(filename):\n f=file(filename)\n return [f.readline(),f.readline(), f.readline(),f.readline(),f.readline()]", self.filename, _readline=[str])

    def test_readline_size(self):
           self.tempfile()
           self.run_test("def _readline_size(filename):\n f=file(filename)\n return [f.readline(7),f.readline(3),f.readline(4),f.readline(),f.readline(10)]", self.filename, _readline_size=[str])

    def test_readline_size_bis(self):
           self.tempfile()
           self.run_test("def _readline_size_bis(filename):\n f=file(filename)\n return [f.readline(4),f.readline(3),f.readline(10),f.readline(),f.readline(5)]", self.filename, _readline_size_bis=[str])

    def test_readlines(self):
            self.tempfile()
            self.run_test("def _readlines(filename):\n f=file(filename)\n return f.readlines()", self.filename, _readlines=[str])

    def test_offset_read(self):
            self.tempfile()
            self.run_test("""def _offset_read(filename):\n f=file(filename)\n f.seek(5)\n return f.read()""", self.filename, _offset_read=[str])

    def test_offset_write(self):
            self.tempfile()
            self.run_test("""def _offset_write(filename):\n f=file(filename, "a")\n f.seek(5)\n f.write("aze")\n f.close()\n return file(filename,"r").read()""", self.filename, prelude = self.reinit_file, _offset_write=[str])

    def test_next(self):
            self.tempfile()
            self.run_test("""def _next(filename):\n f=file(filename)\n return [f.next(),f.next()]""", self.filename, _next=[str])

    def test_iter(self):
            self.tempfile()
            self.run_test("""def _iter(filename):\n f=file(filename)\n return [l for l in f]""", self.filename, _iter=[str])

    def test_fileno(self):
            self.tempfile()
            # Useless to check if same fileno, just checking if fct can be called
            self.run_test("""def _fileno(filename):\n f=file(filename)\n a=f.fileno()\n return a!= 0""", self.filename, _fileno=[str])

    def test_isatty(self):
            self.tempfile()
            self.run_test("""def _isatty(filename):\n f=file(filename)\n return f.isatty()""", self.filename, _isatty=[str])

    def test_truncate(self):
            self.tempfile()
            self.run_test("""def _truncate(filename):\n f=file(filename, 'a')\n f.seek(3)\n f.truncate()\n f.close()\n return open(filename).read()""", self.filename, _truncate=[str])

    def test_truncate_size(self):
            self.tempfile()
            self.run_test("""def _truncate_size(filename):\n f=file(filename, 'a')\n f.truncate(4)\n f.close()\n return open(filename).read()""", self.filename, _truncate_size=[str])

    def test_flush(self):
            self.tempfile()
            # Don't know how to check properly, just checking fct call.
            self.run_test("""def _flush(filename):\n f=file(filename, 'a')\n f.flush()""", self.filename, _flush=[str])

    def test_tell(self):
            self.tempfile()
            self.run_test("""def _tell(filename):\n f=file(filename)\n f.read(3)\n return f.tell()""", self.filename, _tell=[str])

    def test_seek(self):
            self.tempfile()
            self.run_test("""def _seek(filename):\n f=file(filename, 'a')\n f.seek(3)\n return f.tell()""", self.filename, _seek=[str])

    def test_attribute_closed(self):
           self.tempfile()
           self.run_test("""def _attribute_closed(filename):\n f=file(filename, 'a')\n return f.closed""", self.filename, _attribute_closed=[str])

    def test_attribute_name(self):
           self.tempfile()
           self.run_test("""def _attribute_name(filename):\n return file(filename, 'a').name""", self.filename, _attribute_name=[str])

    def test_attribute_mode(self):
           self.tempfile()
           self.run_test("""def _attribute_mode(filename):\n return file(filename, 'a').mode""", self.filename, _attribute_mode=[str])

    def test_attribute_newlines(self):
           self.tempfile()
           self.run_test("""def _attribute_newlines(filename):\n return file(filename, 'a').newlines""", self.filename, _attribute_newlines=[str])

    def test_map_iter(self):
           self.tempfile()
           self.run_test("""def _map_iter(filename):\n f=file(filename)\n return map(lambda s: len(s), f)""", self.filename, _map_iter=[str])

    # The following tests insures the PROXY compatibility with rvalues
    def test_rvalue_write(self):
            self.filename=mkstemp()[1]
            self.run_test("""def _rvalue_write(filename):\n file(filename,'a+').write("aze")""", self.filename, _rvalue_write=[str])

    def test_rvalue_writelines(self):
            self.filename=mkstemp()[1]
            self.run_test("""def _rvalue_writelines(filename):\n file(filename,'a+').writelines(["azerty", "qsdfgh", "12345524"])""", self.filename, _rvalue_writelines=[str])

    def test_rvalue_close(self):
        filename=mkstemp()[1]
        self.run_test("""
def _rvalue_close(filename):
	file(filename,'w').close()""", filename, _rvalue_close=[str])

    def test_rvalue_read(self):
            self.tempfile()
            self.run_test("def _rvalue_read(filename):\n return file(filename).read()", self.filename, _rvalue_read=[str])

    def test_rvalue_readline(self):
            self.tempfile()
            self.run_test("def _rvalue_readline(filename):\n return file(filename).readline()", self.filename, _rvalue_readline=[str])

    def test_rvalue_readlines(self):
            self.tempfile()
            self.run_test("def _rvalue_readlines(filename):\n return file(filename).readlines()", self.filename, _rvalue_readlines=[str])

    def test_rvalue_next(self):
            self.tempfile()
            self.run_test("""def _rvalue_next(filename):\n return file(filename).next()""", self.filename, _rvalue_next=[str])

    def test_rvalue_fileno(self):
            self.tempfile()
            # Useless to check if same fileno, just checking if fct can be called
            self.run_test("""def _rvalue_fileno(filename):\n file(filename).fileno()""", self.filename, _rvalue_fileno=[str])

    def test_rvalue_isatty(self):
            self.tempfile()
            self.run_test("""def _rvalue_isatty(filename):\n return file(filename).isatty()""", self.filename, _rvalue_isatty=[str])

    def test_rvalue_truncate(self):
            self.tempfile()
            self.run_test("""def _rvalue_truncate(filename):\n file(filename, 'a').truncate(3)""", self.filename, _rvalue_truncate=[str])

    def test_rvalue_flush(self):
            self.tempfile()
            self.run_test("""def _rvalue_flush(filename):\n file(filename, 'a').flush()""", self.filename, _rvalue_flush=[str])

    def test_rvalue_tell(self):
            self.tempfile()
            self.run_test("""def _rvalue_tell(filename):\n return file(filename, 'a').tell()""", self.filename, _rvalue_tell=[str])

    def test_rvalue_seek(self):
            self.tempfile()
            self.run_test("""def _rvalue_seek(filename):\n file(filename, 'a').seek(3)""", self.filename, _rvalue_seek=[str])

    def test_xreadlines(self):
            self.tempfile()
            self.run_test("""def _xreadlines(filename):\n f=file(filename)\n return [l for l in f.xreadlines()]""", self.filename, _xreadlines=[str])

########NEW FILE########
__FILENAME__ = test_gwebb
import unittest
from test_env import TestFromDir
import os

class TestGWebb(TestFromDir):

    path = os.path.join(os.path.dirname(__file__),"g webb")


TestGWebb.populate(TestGWebb)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_import_all
from test_env import TestEnv

class TestImportAll(TestEnv):

    def test_import_all(self):
        self.run_test("from math import *\ndef import_all(l): return cos(l)", 3.3, import_all=[float])

    def test_import_cmath_all(self):
        self.run_test("from cmath import *\ndef import_cmath_all(l): return cos(l)", 2.2, import_cmath_all=[float])

    def test_import_all_cos(self):
        self.run_test("from math import *\nfrom math import cos\ndef import_all_cos(l): return cos(l)", 1.1, import_all_cos=[float])

    def test_import_all_twice(self):
        self.run_test("from math import *\nfrom math import *\ndef import_all_twice(l): return cos(l)", 0.1, import_all_twice=[float])

    def test_import_same_name(self):
        self.run_test("from math import *\ndef cos(l): return 100", 0.1, cos=[float])


########NEW FILE########
__FILENAME__ = test_itertools
import unittest
from test_env import TestEnv

class TestItertools(TestEnv):

    def test_imap(self):
        self.run_test("def imap_(l0,v): from itertools import imap; return sum(imap(lambda x:x*v, l0))", [0,1,2], 2, imap_=[[int], int])

    def test_imap_on_generator(self):
        self.run_test("def imap_on_generator(l,v): from itertools import imap; return sum(imap(lambda x:x*v, (y for x in l for y in xrange(x))))", [2,3,5], 1, imap_on_generator=[[int], int])

    def test_imap2(self):
        self.run_test("def imap2_(l0, l1,v): from itertools import imap; return sum(imap(lambda x,y:x*v+y, l0, l1))", [0,1,2], [0,1.1,2.2], 1, imap2_=[[int], [float], int])

    def test_imap2_ineq_size(self):
        self.run_test("def imap2_(l0, l1,v): from itertools import imap; return sum(imap(lambda x,y:x*v+y, l0, l1))", [0,1,2,3], [0,1.1,2.2], 1, imap2_=[[int], [float], int])

    def test_imap2_on_generator(self):
        self.run_test("def imap2_on_generator(l0,l1,v): from itertools import imap; return sum(imap(lambda x,y:x*v+y, (z*z for x in l0 for z in xrange(x)), (z*2 for y in l1 for z in xrange(y))))", [0,1,2,3], [3,2,1,0], 2, imap2_on_generator=[[int], [float], int])

    def test_imap_none(self):
        self.run_test("""
def imap_none(l0): 
    from itertools import imap
    t= 0
    for a in imap(None, l0) : 
        t += a[0]
    return t
""", [0,1,2], imap_none=[[int]])

    def test_imap_none2(self):
        self.run_test("""
def imap_none2(l0): 
    from itertools import imap
    t=0 
    for a in imap(None, l0, l0) : 
        t += sum(a)
    return t
""", [0,1,2], imap_none2=[[int]])

    def test_imap_none_on_generators(self):
        self.run_test("""
def imap_none_g(l0): 
    from itertools import imap
    t= 0
    for a in imap(None, (y for x in l0 for y in xrange(x))) : 
        t += a[0]
    return t
""", [0,1,2], imap_none_g=[[int]])

    def test_imap_none2_on_generators(self):
        self.run_test("""
def imap_none2_g(l0): 
    from itertools import imap
    t=0 
    for a in imap(None, (z for x in l0 for z in xrange(x)), (z for y in l0 for z in xrange(y))) : 
        t += sum(a)
    return t
""", [0,1,2], imap_none2_g=[[int]])

    def test_ifilter_init(self):
        self.run_test("def ifilter_init(l0): from itertools import ifilter; return list(ifilter(lambda x: x > 2 , l0))", [0,1,2,3,4,5], ifilter_init=[[int]])

    def test_ifilter_final(self):
        self.run_test("def ifilter_final(l0): from itertools import ifilter; return list(ifilter(lambda x: x < 2, l0))", [0,1,2,3,4,5], ifilter_final=[[int]])

    def test_ifilter_on_generator(self):
        self.run_test("def ifilterg_(l0): from itertools import ifilter; return list(ifilter(lambda x: (x % 2) == 1, (y for x in l0 for y in xrange(x))))", [0,1,2,3,4,5], ifilterg_=[[int]])

    def test_ifilter_none(self):
        self.run_test("""
def ifiltern_(l0): 
  from itertools import ifilter; 
  s = 0
  for b in (ifilter(None, l0)):
    s += 1
  return b,s
""", [True,False,True,True], ifiltern_=[[bool]])

    def test_product(self):
        self.run_test("def product_(l0,l1): from itertools import product; return sum(map(lambda (x,y) : x*y, product(l0,l1)))", [0,1,2,3,4,5], [10,11], product_=[[int],[int]])

    def test_product_on_generator(self):
        self.run_test("def product_g(l0,l1): from itertools import product; return sum(map(lambda (x,y) : x*y, product((y for x in l0 for y in xrange(x)),(y for x in l1 for y in xrange(x)))))", [0,1,2,3,4], [4,3,2,1,0], product_g=[[int],[int]])

    def test_itertools(self):
        self.run_test("def test_it(l0,l1): import itertools; return sum(itertools.imap(lambda (x,y) : x*y, itertools.product(itertools.ifilter(lambda x : x > 2, l0), itertools.ifilter(lambda x : x < 12, l1))))", [0,1,2,3,4,5], [10,11,12,13,14,15], test_it=[[int],[int]])

    def test_izip(self):
        self.run_test("def izip_(l0,l1): from itertools import izip; return sum(map(lambda (x,y) : x*y, izip(l0,l1)))", [0,1,2], [10,11,12], izip_=[[int],[int]])

    def test_izip_on_generator(self):
        self.run_test("def izipg_(l0,l1): from itertools import izip; return sum(map(lambda (x,y) : x*y, izip((z for x in l0 for z in xrange(x)),(z for x in l1 for z in xrange(x)))))", [0,1,2,3], [3,2,1,0], izipg_=[[int],[int]])

    def test_islice0(self):
        self.run_test("def islice0(l): from itertools import islice ; return [x for x in islice(l, 1,30,3)]", range(100), islice0=[[int]])

    def test_islice1(self):
        self.run_test("def islice1(l): from itertools import islice ; return [x for x in islice(l, 16)]", range(100), islice1=[[int]])

    def test_count0(self):
        self.run_test("def count0(): from itertools import count ; c = count() ; next(c); next(c); return next(c)", count0=[])

    def test_count1(self):
        self.run_test("def count1(n): from itertools import count ; c = count(n) ; next(c); next(c); return next(c)", 100, count1=[int])

    def test_count2(self):
        self.run_test("def count2(n): from itertools import count ; c = count(n,3.2) ; next(c); next(c); return next(c)", 100, count2=[int])

    def test_next_enumerate(self):
        self.run_test("def next_enumerate(n): x = enumerate(n) ; next(x) ; return map(None, x)", range(5), next_enumerate=[[int]])

    def test_next_generator(self):
        self.run_test("def next_generator(n): x = (i for i in xrange(n) for j in xrange(i)) ; next(x) ; return map(None, x)", 5, next_generator=[int])

    def test_next_imap(self):
        self.run_test("def next_imap(n): from itertools import imap ; x = imap(abs,n) ; next(x) ; return map(None, x)", range(-5,5), next_imap=[[int]])

    def test_next_imap_none(self):
        self.run_test("def next_imap_none(n): from itertools import imap ; x = imap(None,n) ; next(x) ; return map(None, x)", range(-5,5), next_imap_none=[[int]])

    def test_next_ifilter(self):
        self.run_test("def next_ifilter(n): from itertools import ifilter ; x = ifilter(abs,n) ; next(x) ; return map(None, x)", range(-5,5), next_ifilter=[[int]])

    def test_next_ifilter_none(self):
        self.run_test("def next_ifilter_none(n): from itertools import ifilter ; x = ifilter(None,n) ; next(x) ; return map(None, x)", range(-5,5), next_ifilter_none=[[int]])

    def test_next_product(self):
        self.run_test("def next_product(n): from itertools import product ; x = product(n,n) ; next(x) ; return map(None, x)", range(-5,5), next_product=[[int]])

    def test_next_izip(self):
        self.run_test("def next_izip(n): from itertools import izip ; x = izip(n,n) ; next(x) ; return map(None, x)", range(-5,5), next_izip=[[int]])

    def test_next_islice(self):
        self.run_test("def next_islice(n): from itertools import islice ; x = islice(n,8) ; next(x) ; return map(None, x)", range(-5,5), next_islice=[[int]])

    def test_next_count(self):
        self.run_test("def next_count(n): from itertools import count ; x = count(n) ; next(x) ; return next(x)", 5, next_count=[int])

    def test_iter(self):
        self.run_test("def iter_(n): r = iter(range(5,n)) ; next(r) ; return next(r)", 12, iter_=[int])

    def test_ifilter_with_nested_lambdas(self):
        code = '''
def ifilter_with_nested_lambdas(N):
    perf = lambda n: n == sum(i for i in xrange(1, n) if n % i == 0)
    return map(perf, xrange(20))'''
        self.run_test(code, 10, ifilter_with_nested_lambdas=[int])

    def test_combinations_on_generator(self):
        self.run_test("def combinations_g(l0,a): from itertools import combinations; return sum(map(lambda (x,y) : x*y, combinations((y for x in l0 for y in xrange(x)),a)))", [0,1,2], 2, combinations_g=[[int],int])

    def test_next_combinations(self):
        self.run_test("def next_combinations(n): from itertools import combinations ; x = combinations(n,2) ; next(x) ; return map(None, x)", range(5), next_combinations=[[int]])

    def test_combinations(self):
        self.run_test("def combinations_(l0,a): from itertools import combinations; return sum(map(lambda (x,y) : x*y, combinations(l0,a)))", [0,1,2,3,4,5], 2, combinations_=[[int],int])

    def test_permutations_on_generator(self):
        self.run_test("def permutations_g(l0,a): from itertools import permutations; return sum(map(lambda (x,y) : x*y, permutations((y for x in l0 for y in xrange(x)),a)))", [0,1,2], 2, permutations_g=[[int],int])

    def test_next_permutations(self):
        self.run_test("def next_permutations(n):"
                      "  from itertools import permutations ;"
                      "  x = permutations(n,2) ;"
                      "  next(x) ;"
                      "  return map(None, x)",
                      range(5),
                      next_permutations=[[int]])

    def test_permutations(self):
        '''Test permutation without second arg'''
        self.run_test("def permutations_2_(l0): "
                      "  from itertools import permutations;"
                      "  return list(permutations(l0))",
                      [0, 1, 2, 3],
                      permutations_2_=[[int]])

    def test_permutations_with_prefix(self):
        self.run_test("def permutations_(l0,a):"
                      "  from itertools import permutations;"
                      "  return list(permutations(l0,a))",
                      [0,1,2,3,4,5], 2,
                      permutations_=[[int],int])

    def test_imap_over_array(self):
        self.run_test("def imap_over_array(l):"
                      "  from itertools import imap ;"
                      "  from numpy import arange ;"
                      "  t = tuple(imap(lambda x: 1, (l,l))) ;"
                      "  return arange(10).reshape(5,2)[t]",
                      3,
                      imap_over_array=[int])

    def test_imap_over_several_arrays(self):
        self.run_test("def imap_over_several_arrays(l):"
                      "  from itertools import imap ;"
                      "  from numpy import arange ;"
                      "  t = tuple(imap(lambda x,y: 1, (l,l), (l, l, l))) ;"
                      "  return arange(10).reshape(5,2)[t]",
                      3,
                      imap_over_several_arrays=[int])

########NEW FILE########
__FILENAME__ = test_list
from test_env import TestEnv

class TestList(TestEnv):

    def test_extend_(self):
        self.run_test("def extend_(a):\n b=[1,2,3]\n b.extend(a)\n return b", [1.2], extend_=[[float]])

    def test_remove_(self):
        self.run_test("def remove_(a):\n b=[1,2,3]\n b.remove(a)\n return b", 2, remove_=[int])

    def test_index_(self):
        self.run_test("def index_(a):\n b=[1,2,3,8,7,4]\n return b.index(a)", 8, index_=[int])

    def test_pop_(self):
        self.run_test("def pop_(a):\n b=[1,3,4,5,6,7]\n return b.pop(a)", 2, pop_=[int])

    def test_popnegatif_(self):
        self.run_test("def popnegatif_(a):\n b=[1,3,4,5,6,7]\n return b.pop(a)", -2, popnegatif_=[int])

    def test_popempty_(self):
        self.run_test("def popempty_():\n b=[1,3,4,5,6,7]\n return b.pop()", popempty_=[])

    def test_count_(self):
        self.run_test("def count_(a):\n b=[1,3,4,5,3,7]\n return b.count(a)",3, count_=[int])

    def test_reverse_(self):
        self.run_test("def reverse_():\n b=[1,2,3]\n b.reverse()\n return b", reverse_=[])

    def test_sort_(self):
        self.run_test("def sort_():\n b=[1,3,5,4,2]\n b.sort()\n return b", sort_=[])

    def test_insert_(self):
        self.run_test("def insert_(a,b):\n c=[1,3,5,4,2]\n c.insert(a,b)\n return c",2,5, insert_=[int,int])

    def test_insertneg_(self):
        self.run_test("def insertneg_(a,b):\n c=[1,3,5,4,2]\n c.insert(a,b)\n return c",-1,-2, insertneg_=[int,int])

    def test_subscripted_slice(self):
        self.run_test("def subscripted_slice(l): a=l[2:6:2] ; return a[1]", range(10), subscripted_slice=[[int]])

    def test_list_comparison(self):
        self.run_test("def list_comparison(l): return max(l)", [[1,2,3],[1,4,1],[1,4,8,9]], list_comparison=[[[int]]])

    def test_list_equal_comparison_true(self):
        self.run_test("def list_comparison_true(l1,l2):  return l1==l2",
                      [1,2,3],[1,4,1], list_comparison_true=[[int],[int]])

    def test_list_equal_comparison_false(self):
        self.run_test("def list_comparison_false(l1,l2): return l1==l2",
                      [1,4,1],[1,4,1], list_comparison_false=[[int],[int]])

    def test_list_equal_comparison_different_sizes(self):
        self.run_test("def list_comparison_different_sizes(l1,l2): return l1==l2",
                      [1,4,1],[1,4,1,5], list_comparison_different_sizes=[[int],[int]])

    def test_list_unequal_comparison_false(self):
        self.run_test("def list_comparison_unequal_false(l1,l2):  return l1!=l2",
                      [1,2,3],[1,4,1], list_comparison_unequal_false=[[int],[int]])

    def test_list_unequal_comparison_true(self):
        self.run_test("def list_comparison_unequal_true(l1,l2): return l1!=l2",
                      [1,4,1],[1,4,1], list_comparison_unequal_true=[[int],[int]])

    def test_list_unequal_comparison_different_sizes(self):
        self.run_test("def list_unequal_comparison_different_sizes(l1,l2): return l1!=l2",
                      [1,4,1],[1,4,1,5], list_unequal_comparison_different_sizes=[[int],[int]])

    def test_assigned_slice(self):
        self.run_test("def assigned_slice(l): l[0]=l[2][1:3] ; return l",
                      [[1,2,3],[1,4,1],[1,4,8,9]], assigned_slice=[[[int]]])


########NEW FILE########
__FILENAME__ = test_math
from test_env import TestEnv

class TestMath(TestEnv):

    def test_cos_(self):
        self.run_test("def cos_(a):\n from math import cos\n return cos(a)", 1, cos_=[int])

    def test_exp_(self):
        self.run_test("def exp_(a):\n from math import exp\n return exp(a)", 1, exp_=[int])

    def test_sqrt_(self):
        self.run_test("def sqrt_(a):\n from math import sqrt\n return sqrt(a)", 1, sqrt_=[int])

    def test_log10_(self):
        self.run_test("def log10_(a):\n from math import log10\n return log10(a)", 1, log10_=[int])

    def test_isnan_(self):
        self.run_test("def isnan_(a):\n from math import isnan\n return isnan(a)", 1, isnan_=[int])

    def test_pi_(self):
        self.run_test("def pi_():\n from math import pi\n return pi", pi_=[])

    def test_e_(self):
        self.run_test("def e_():\n from math import e\n return e", e_=[])

    def test_asinh_(self):
        self.run_test("def asinh_(a):\n from math import asinh\n return asinh(a)",1, asinh_=[float])

    def test_atanh_(self):
        self.run_test("def atanh_(a):\n from math import atanh\n return atanh(a)",.1, atanh_=[float])

    def test_acosh_(self):
        self.run_test("def acosh_(a):\n from math import acosh\n return acosh(a)",1, acosh_=[int])

    def test_radians_(self):
        self.run_test("def radians_(a):\n from math import radians\n return radians(a)",1, radians_=[int])

    def test_degrees_(self):
        self.run_test("def degrees_(a):\n from math import degrees\n return degrees(a)",1, degrees_=[int])

    def test_hypot_(self):
        self.run_test("def hypot_(a,b):\n from math import hypot\n return hypot(a,b)",3,4, hypot_=[int,int])

    def test_tanh_(self):
        self.run_test("def tanh_(a):\n from math import tanh\n return tanh(a)",1, tanh_=[int])

    def test_cosh_(self):
        self.run_test("def cosh_(a):\n from math import cosh\n return cosh(a)",1, cosh_=[float])

    def test_sinh_(self):
        self.run_test("def sinh_(a):\n from math import sinh\n return sinh(a)",1, sinh_=[int])

    def test_atan_(self):
        self.run_test("def atan_(a):\n from math import atan\n return atan(a)",1, atan_=[int])

    def test_atan2_(self):
        self.run_test("def atan2_(a,b):\n from math import atan2\n return atan2(a,b)",2,4, atan2_=[int,int])

    def test_asin_(self):
        self.run_test("def asin_(a):\n from math import asin\n return asin(a)",1, asin_=[int])

    def test_tan_(self):
        self.run_test("def tan_(a):\n from math import tan\n return tan(a)",1, tan_=[int])

    def test_log_(self):
        self.run_test("def log_(a):\n from math import log\n return log(a)",1, log_=[int])

    def test_log1p_(self):
        self.run_test("def log1p_(a):\n from math import log1p\n return log1p(a)",1, log1p_=[int])

    def test_expm1_(self):
        self.run_test("def expm1_(a):\n from math import expm1\n return expm1(a)",1, expm1_=[int])

    def test_ldexp_(self):
        self.run_test("def ldexp_(a,b):\n from math import ldexp\n return ldexp(a,b)",3,4, ldexp_=[int,int])

    def test_fmod_(self):
        self.run_test("def fmod_(a,b):\n from math import fmod\n return fmod(a,b)",5.3,2, fmod_=[float,int])

    def test_fabs_(self):
        self.run_test("def fabs_(a):\n from math import fabs\n return fabs(a)",1, fabs_=[int])

    def test_copysign_(self):
        self.run_test("def copysign_(a,b):\n from math import copysign\n return copysign(a,b)",2,-2, copysign_=[int,int])

    def test_acos_(self):
        self.run_test("def acos_(a):\n from math import acos\n return acos(a)",1, acos_=[int])

    def test_erf_(self):
        self.run_test("def erf_(a):\n from math import erf\n return erf(a)",1, erf_=[int])

    def test_erfc_(self):
        self.run_test("def erfc_(a):\n from math import erfc\n return erfc(a)",1, erfc_=[int])

    def test_gamma_(self):
        self.run_test("def gamma_(a):\n from math import gamma\n return gamma(a)",1, gamma_=[int])

    def test_lgamma_(self):
        self.run_test("def lgamma_(a):\n from math import lgamma\n return lgamma(a)",1, lgamma_=[int])

    def test_trunc_(self):
        self.run_test("def trunc_(a):\n from math import trunc\n return trunc(a)",1, trunc_=[int])

    def test_factorial_(self):
        self.run_test("def factorial_(a):\n from math import factorial\n return factorial(a)",2, factorial_=[int])

    def test_modf_(self):
        self.run_test("def modf_(a):\n from math import modf\n return modf(a)",2, modf_=[int])

    def test_frexp_(self):
        self.run_test("def frexp_(a):\n from math import frexp\n return frexp(a)",2.2, frexp_=[float])

    def test_isinf_(self):
        self.run_test("def isinf_(a):\n from math import isinf\n n=1\n while not isinf(a):\n  a=a*a\n  n+=1\n return isinf(a)", 2., isinf_=[float])

########NEW FILE########
__FILENAME__ = test_none
from test_env import TestEnv
from unittest import skip

class TestNone(TestEnv):

    def test_returned_none(self):
        code = '''
def dummy(l):
    if l: return None
    else: return l
def returned_none(a):
    return dummy(a)'''
        self.run_test(code, [1, 2], returned_none=[[int]])

    def test_returned_none_member(self):
        code = '''
def dummy(l):
    if not l: return None
    else: return l
def returned_none_member(a):
    return dummy(a).count(1)'''
        self.run_test(code, [1, 2], returned_none_member=[[int]])

########NEW FILE########
__FILENAME__ = test_normalize_methods
from test_env import TestEnv

class TestBase(TestEnv):

    def test_normalize_methods0(self):
        self.run_test("def normalize_methods0(): c = complex(1) ; return complex.conjugate(c)", normalize_methods0=[])

    def test_shadow_import0(self):
        self.run_test("def shadow_import0(math): math.add(1)", {1,2}, shadow_import0=[{int}])

    def test_shadow_import1(self):
        self.run_test("def shadow_import1(): math={ 1 } ; math.add(1)", shadow_import1=[])

    def test_shadow_import2(self):
        self.run_test("def shadow_import2(s):\n for set in s : set.add(1)", [{1},{2}], shadow_import2=[[{int}]])

    def test_shadow_import3(self):
        self.run_test("def shadow_import3(s): import math ; math = set ; set.add(s, 1)", {1}, shadow_import3=[{int}])

    def test_shadow_import4(self):
        self.run_test("import math\ndef shadow_import4(math): math.add(1)", {1}, shadow_import4=[{int}])

    def test_builtin_support0(self):
        self.run_test("def builtin_support0(a): return __builtin__.list(a)", [1, 2],  builtin_support0=[[int]])

########NEW FILE########
__FILENAME__ = test_numpy
import unittest
from test_env import TestEnv
import numpy

class TestNumpy(TestEnv):
    def test_numpy_augassign0(self):
        self.run_test('def numpy_augassign0(a): a+=1; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign0=[numpy.array([numpy.array([int])])])

    def test_numpy_augassign1(self):
        self.run_test('def numpy_augassign1(a): a*=2; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign1=[numpy.array([numpy.array([int])])])

    def test_numpy_augassign2(self):
        self.run_test('def numpy_augassign2(a): a-=2; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign2=[numpy.array([numpy.array([int])])])

    def test_numpy_augassign3(self):
        self.run_test('def numpy_augassign3(a): a/=2; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign3=[numpy.array([numpy.array([int])])])

    def test_numpy_augassign4(self):
        self.run_test('def numpy_augassign4(a): a|=2; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign4=[numpy.array([numpy.array([int])])])

    def test_numpy_augassign5(self):
        self.run_test('def numpy_augassign5(a): a&=2; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_augassign5=[numpy.array([numpy.array([int])])])


    def test_numpy_faugassign0(self):
        self.run_test('def numpy_faugassign0(a): a[a>5]+=1; return a',
                      numpy.arange(100),
                      numpy_faugassign0=[numpy.array([int])])

    def test_numpy_faugassign1(self):
        self.run_test('def numpy_faugassign1(a): a[a>3]*=2; return a',
                      numpy.arange(100),
                      numpy_faugassign1=[numpy.array([int])])

    def test_numpy_faugassign2(self):
        self.run_test('def numpy_faugassign2(a): a[a>30]-=2; return a',
                      numpy.arange(100),
                      numpy_faugassign2=[numpy.array([int])])

    def test_numpy_faugassign3(self):
        self.run_test('def numpy_faugassign3(a): a[a<40]/=2; return a',
                      numpy.arange(100),
                      numpy_faugassign3=[numpy.array([int])])

    def test_numpy_faugassign4(self):
        self.run_test('def numpy_faugassign4(a): a[a<4]|=2; return a',
                      numpy.arange(100),
                      numpy_faugassign4=[numpy.array([int])])

    def test_numpy_faugassign5(self):
        self.run_test('def numpy_faugassign5(a): a[a>8]&=2; return a',
                      numpy.arange(100),
                      numpy_faugassign5=[numpy.array([int])])

    def test_broadcast0(self):
        self.run_test('def numpy_broadcast0(a): a[0] = 1 ; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_broadcast0=[numpy.array([numpy.array([int])])])

    def test_broadcast1(self):
        self.run_test('def numpy_broadcast1(a): a[1:-1] = 1 ; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_broadcast1=[numpy.array([numpy.array([int])])])

    def test_broadcast2(self):
        self.run_test('def numpy_broadcast2(a): a[1:-1,1:-1] = 1 ; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_broadcast2=[numpy.array([numpy.array([int])])])

    def test_broadcast3(self):
        self.run_test('def numpy_broadcast3(a): a[1:-1,1] = 1 ; return a',
                      numpy.arange(100).reshape((10, 10)),
                      numpy_broadcast3=[numpy.array([numpy.array([int])])])

    def test_broadcast4(self):
        self.run_test('def numpy_broadcast4(a): a[:,1,1] = 1 ; return a',
                      numpy.arange(100).reshape((5,5,4)),
                      numpy_broadcast4=[numpy.array([numpy.array([numpy.array([int])])])])

    def test_extended_slicing0(self):
        self.run_test("def numpy_extended_slicing0(a): return a[2,1:-1]",
                      numpy.arange(100).reshape((10, 10)),
                      numpy_extended_slicing0=[numpy.array([numpy.array([int])])])

    def test_extended_slicing1(self):
        self.run_test("def numpy_extended_slicing1(a): return a[1:-1,2]",
                      numpy.arange(100).reshape((10, 10)),
                      numpy_extended_slicing1=[numpy.array([numpy.array([int])])])

    def test_extended_slicing2(self):
        self.run_test("def numpy_extended_slicing2(a): return a[2,1:-1]",
                      numpy.arange(30).reshape((3,5,2)),
                      numpy_extended_slicing2=[numpy.array([numpy.array([numpy.array([int])])])])

    def test_extended_slicing3(self):
        self.run_test("def numpy_extended_slicing3(a): return a[1:-1,2]",
                      numpy.arange(30).reshape((3,5,2)),
                      numpy_extended_slicing3=[numpy.array([[[int]]])])

    def test_extended_slicing4(self):
        self.run_test("def numpy_extended_slicing4(a): return a[1:-1,2:-2]",
                      numpy.arange(100).reshape((10, 10)),
                      numpy_extended_slicing4=[numpy.array([numpy.array([int])])])

    def test_extended_slicing5(self):
        self.run_test("def numpy_extended_slicing5(a): return a[1:-1]",
                      numpy.arange(100).reshape((10, 10)),
                      numpy_extended_slicing5=[numpy.array([numpy.array([int])])])

    def test_extended_slicing6(self):
        self.run_test("def numpy_extended_slicing6(a): return a[1:-1,2:-2, 3:-3]",
                      numpy.arange(60).reshape((3,5,4)),
                      numpy_extended_slicing6=[numpy.array([numpy.array([numpy.array([int])])])])

    def test_extended_slicing7(self):
        self.run_test("def numpy_extended_slicing7(a): return a[1:-1, 2, 1]",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_slicing7=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_slicing8(self):
        self.run_test("def numpy_extended_slicing8(a): return a[1:-1,2:-2, 1:2]",
                      numpy.arange(60).reshape((3,5,4)),
                      numpy_extended_slicing8=[numpy.array([numpy.array([numpy.array([int])])])])

    def test_extended_slicing9(self):
        self.run_test("def numpy_extended_slicing9(a): return a[1:-1, 2, 1, 1:2]",
                      numpy.arange(120).reshape((3,5,2,4)),
                      numpy_extended_slicing9=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_slicing10(self):
        self.run_test("def numpy_extended_slicing10(a): return a[1, 2, 1:-1]",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_slicing10=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_slicing11(self):
        self.run_test("def numpy_extended_slicing11(a): return a[1, 2, 1:-1, 1]",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_slicing11=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum0(self):
        self.run_test("def numpy_extended_sum0(a): import numpy ; return numpy.sum(a)",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum0=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum1(self):
        self.run_test("def numpy_extended_sum1(a): import numpy ; return numpy.sum(a[1])",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum1=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum2(self):
        self.run_test("def numpy_extended_sum2(a): import numpy ; return numpy.sum(a[1,0])",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum2=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum3(self):
        self.run_test("def numpy_extended_sum3(a): import numpy ; return numpy.sum(a[1:-1])",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum3=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum4(self):
        self.run_test("def numpy_extended_sum4(a): import numpy ; return numpy.sum(a[1:-1,0])",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum4=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_extended_sum5(self):
        self.run_test("def numpy_extended_sum5(a): import numpy ; return numpy.sum(a)",
                      numpy.arange(120).reshape((3,5,4,2)),
                      numpy_extended_sum5=[numpy.array([numpy.array([numpy.array([numpy.array([int])])])])])

    def test_numpy_shape_as_function(self):
         self.run_test("def numpy_shape_as_function(a): import numpy ; return numpy.shape(a)",
                       numpy.ones(3, numpy.int16),
                       numpy_shape_as_function=[numpy.array([numpy.int16])])

    def test_numpy_size_as_function(self):
         self.run_test("def numpy_size_as_function(a): import numpy ; return numpy.size(a)",
                       numpy.ones(3, numpy.int16),
                       numpy_size_as_function=[numpy.array([numpy.int16])])

    def test_numpy_ndim_as_function(self):
         self.run_test("def numpy_ndim_as_function(a): import numpy ; return numpy.ndim(a)",
                       numpy.ones(3, numpy.int16),
                       numpy_ndim_as_function=[numpy.array([numpy.int16])])

    def test_numpy_bool(self):
        self.run_test("def numpy_bool(n): import numpy ; return numpy.ones(n, bool)",
                      5,
                      numpy_bool=[int])

    def test_numpy_int(self):
        self.run_test("def numpy_int(n): import numpy ; return numpy.ones(n, int)",
                      5,
                      numpy_int=[int])

    def test_numpy_float(self):
        self.run_test("def numpy_float(n): import numpy ; return numpy.ones(n, float)",
                      5,
                      numpy_float=[int])

    def test_numpy_int16(self):
        self.run_test("def numpy_int16(n): import numpy ; return numpy.ones(n, numpy.int16)",
                      5,
                      numpy_int16=[int])

    def test_numpy_uint16(self):
        self.run_test("def numpy_uint16(n): import numpy ; return numpy.ones(n, numpy.uint16)",
                      5,
                      numpy_uint16=[int])

    def test_numpy_uint64(self):
        self.run_test("def numpy_uint64(n): import numpy ; return numpy.ones(n, numpy.uint64)",
                      5,
                      numpy_uint64=[int])

    def test_numpy_float(self):
        self.run_test("def numpy_float(n): import numpy ; return numpy.ones(n, numpy.float)",
                      5,
                      numpy_float=[int])

    def test_numpy_complex(self):
        self.run_test("def numpy_complex(n): import numpy ; return numpy.ones(n, numpy.complex)",
                      5,
                      numpy_complex=[int])

    def test_numpy_complex64(self):
        self.run_test("def numpy_complex64(n): import numpy ; return numpy.ones(n, numpy.complex64)",
                      5,
                      numpy_complex64=[int])

    def test_numpy_double(self):
        self.run_test("def numpy_double(n): import numpy ; return numpy.ones(n, numpy.double)",
                      5,
                      numpy_double=[int])

    def test_numpy_complex_export(self):
        self.run_test("def numpy_complex_export(a): import numpy ; return numpy.sum(a)",
                      numpy.array([1+1j]),
                      numpy_complex_export=[numpy.array([complex])])

    def test_assign_gsliced_array(self):
        self.run_test("""def assign_gsliced_array():
   import numpy as np;
   a = np.array([[[1,2],[3,4]],[[5,6],[7,8]]])
   b = np.array([[[9,10],[11,12]],[[13,14],[15,16]]])
   a[:,:] = b[:,:]
   return a,b;""", assign_gsliced_array=[])

    def test_assign_sliced_array(self):
        self.run_test("""def assign_sliced_array():
   import numpy as np;
   a = np.array([1,2,3]);
   b = np.array([1,2,3]);
   c=a[1:]
   c=b[1:]
   b[2] = -1;
   return c;""", assign_sliced_array=[])

    def test_filter_array_0(self):
        self.run_test('def filter_array_0(n): import numpy ; a = numpy.zeros(n) ; return a[a>1]',
                      10,
                      filter_array_0=[int])

    def test_filter_array_1(self):
        self.run_test('def filter_array_1(n): import numpy ; a = numpy.arange(n) ; return a[a>4]',
                      10,
                      filter_array_1=[int])

    def test_filter_array_2(self):
        self.run_test('def filter_array_2(n): import numpy ; a = numpy.arange(n) ; return (a+a)[a>4]',
                      10,
                      filter_array_2=[int])

    def test_filter_array_3(self):
        self.run_test('def filter_array_3(n): import numpy ; a = numpy.arange(n) ; return (-a)[a>4]',
                      10,
                      filter_array_3=[int])

    @unittest.skip("filtering a slice")
    def test_filter_array_4(self):
        self.run_test('def filter_array_4(n): import numpy ; a = numpy.arange(n) ; return a[1:-1][a[1:-1]>4]',
                      10,
                      filter_array_4=[int])

    @unittest.skip("filtering a slice")
    def test_filter_array_5(self):
        self.run_test('def filter_array_5(n): import numpy ; a = numpy.arange(n) ; return (a[1:-1])[a[1:-1]>4]',
                      10,
                      filter_array_5=[int])

    def test_assign_ndarray(self):
        code = """
def assign_ndarray(t):
    import numpy as np;
    a = np.array([1,2,3]);
    b = np.array([1,2,3]);
    if t:
      c = a;
    else:
      c=b;
    if t:
      c=b;
    b[0] = -1;
    return c;"""
        self.run_test(code,
                      1,
                      assign_ndarray=[int])

    def test_bitwise_nan_bool(self):
        self.run_test("def np_bitwise_nan_bool(a): import numpy as np ; return ~(a<5)", numpy.arange(10), np_bitwise_nan_bool=[numpy.array([int])])

    def test_frexp0(self):
        self.run_test("def np_frexp0(a): import numpy as np ; return np.frexp(a)", 1.5, np_frexp0=[float])

    def test_frexp1(self):
        self.run_test("def np_frexp1(a): import numpy as np ; return np.frexp(a)", numpy.array([1.1,2.2,3.3]), np_frexp1=[numpy.array([float])])

    def test_frexp2(self):
        self.run_test("def np_frexp2(a): import numpy as np ; return np.frexp(a+a)", numpy.array([1.1,2.2,3.3]), np_frexp2=[numpy.array([float])])

    def test_gslice0(self):
        self.run_test("def np_gslice0(a): import numpy as np; return a[1:9,5:7]", numpy.array(range(10*9)).reshape(10,9), np_gslice0=[numpy.array([[int]])])

    def test_gslice1(self):
        self.run_test("def np_gslice1(a): import numpy as np ; return a[1:9,0:1, 3:6]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice1=[numpy.array([[[int]]])])

    def test_gslice2(self):
        self.run_test("def np_gslice2(a): import numpy as np ; return a[:,0:1, 3:6]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice2=[numpy.array([[[int]]])])

    def test_gslice3(self):
        self.run_test("def np_gslice3(a): import numpy as np ; return a[:-1,0:-1, -3:7]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice3=[numpy.array([[[int]]])])

    def test_gslice4(self):
        self.run_test("def np_gslice4(a): import numpy as np ; return a[1,0:-1, -3:7]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice4=[numpy.array([[[int]]])])

    def test_gslice5(self):
        self.run_test("def np_gslice5(a): import numpy as np ; return a[1,0:-1, 7]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice5=[numpy.array([[[int]]])])

    def test_gslice6(self):
        self.run_test("def np_gslice6(a): import numpy as np ; return a[:-1, :][1:,:]", numpy.array(range(10*9*8)).reshape(10,9,8), np_gslice6=[numpy.array([[[int]]])])

    def test_ndindex0(self):
        self.run_test("def np_ndindex0(): import numpy as np ; return [x for x in np.ndindex(5,6)]",
                      np_ndindex0=[])

    def test_ndindex1(self):
        self.run_test("def np_ndindex1(a): import numpy as np ; return [x for x in np.ndindex(a)]", 3, np_ndindex1=[int])

    def test_ndindex2(self):
        self.run_test("def np_ndindex2(n): import numpy as np ; return [x for x in np.ndindex((n,n))]", 3, np_ndindex2=[int])

    def test_ndenumerate0(self):
        self.run_test("def np_ndenumerate0(a): import numpy as np ; return [x for x in np.ndenumerate(a)]", numpy.array([[1, 2], [3, 4]]), np_ndenumerate0=[numpy.array([[int]])])

    def test_ndenumerate1(self):
        self.run_test("def np_ndenumerate1(a): import numpy as np ; return [x for x in np.ndenumerate(a)]", numpy.array([1, 2, 3, 4]), np_ndenumerate1=[numpy.array([int])])

    def test_nansum0(self):
        self.run_test("def np_nansum0(a): import numpy as np  ; return np.nansum(a)" , numpy.array([[1, 2], [3, numpy.nan]]), np_nansum0=[numpy.array([[float]])])

    def test_nansum1(self):
        self.run_test("def np_nansum1(a): import numpy as np ; return np.nansum(a)" , numpy.array([[1, 2], [numpy.NINF, numpy.nan]]), np_nansum1=[numpy.array([[float]])])

    def test_nansum2(self):
        self.run_test("def np_nansum2(a): import numpy as np ; return np.nansum(a)", [1, numpy.nan], np_nansum2=[[float]])

    def test_nanmin0(self):
        self.run_test("def np_nanmin0(a): import numpy as np ; return np.nanmin(a)" , numpy.array([[1, 2], [3, numpy.nan]]), np_nanmin0=[numpy.array([[float]])])

    def test_nanmin1(self):
        self.run_test("def np_nanmin1(a): import numpy as np ; return np.nanmin(a)" , numpy.array([[1, 2], [numpy.NINF, numpy.nan]]), np_nanmin1=[numpy.array([[float]])])

    def test_nanmax0(self):
        self.run_test("def np_nanmax0(a): import numpy as np ; return np.nanmax(a)" , numpy.array([[1, 2], [3, numpy.nan]]),  np_nanmax0=[numpy.array([[float]])])

    def test_nanmax1(self):
        self.run_test("def np_nanmax1(a): import numpy as np ; return np.nanmax(a)" , numpy.array([[1, 2], [numpy.inf, numpy.nan]]) , np_nanmax1=[numpy.array([[float]])])

    def test_np_residual(self):
        self.run_test("""import numpy as np
def np_residual():
    nx, ny, nz= 75, 75, 100
    hx, hy = 1./(nx-1), 1./(ny-1)

    P_left, P_right = 0, 0
    P_top, P_bottom = 1, 0
    P = np.ones((nx, ny, nz), np.float64)
    d2x = np.zeros_like(P)
    d2y = np.zeros_like(P)

    d2x[1:-1] = (P[2:]   - 2*P[1:-1] + P[:-2]) / hx/hx
    d2x[0]    = (P[1]    - 2*P[0]    + P_left)/hx/hx
    d2x[-1]   = (P_right - 2*P[-1]   + P[-2])/hx/hx

    d2y[:,1:-1] = (P[:,2:] - 2*P[:,1:-1] + P[:,:-2])/hy/hy
    d2y[:,0]    = (P[:,1]  - 2*P[:,0]    + P_bottom)/hy/hy
    d2y[:,-1]   = (P_top   - 2*P[:,-1]   + P[:,-2])/hy/hy

    return d2x + d2y + 5*np.cosh(P).mean()**2
""", np_residual=[])

    def test_np_func2(self):
        self.run_test("""import numpy as np
def np_func2(x):
    f = [x[0] * np.cos(x[1]) - 4,
         x[1]*x[0] - x[1] - 5]
    df = np.array([[np.cos(x[1]), -x[0] * np.sin(x[1])],
                   [x[1], x[0] - 1]])
    return f, df
""", [1.0, 2.0, 3.0], np_func2=[[float]])

    def test_np_peval(self):
        self.run_test("""import numpy
def np_peval(x, p):
    return p[0]*numpy.sin(2*numpy.pi*p[1]*x+p[2])
""", 12., [1.0, 2.0, 3.0], np_peval=[float, [float]])

    def test_np_residuals(self):
        self.run_test("""import numpy
def np_residuals():
    x = numpy.arange(0,6e-2,6e-2/30)
    A,k,theta = 10, 1.0/3e-2, numpy.pi/6
    return A*numpy.sin(2*numpy.pi*k*x+theta)
""", np_residuals=[])

    def test_np_func_deriv(self):
        self.run_test("""import numpy
def np_func_deriv(x, sign=1.0):
    dfdx0 = sign*(-2*x[0] + 2*x[1] + 2)
    dfdx1 = sign*(2*x[0] - 4*x[1])
    return numpy.array([ dfdx0, dfdx1 ])
""", [-1.0, 1.0], -1.0, np_func_deriv=[[float], float])

    def test_np_func(self):
        self.run_test("""import numpy
def np_func(x, sign=1.0):
    return sign*(2*x[0]*x[1] + 2*x[0] - x[0]**2 - 2*x[1]**2)
""", [-1.0, 1.0], -1.0, np_func=[[float], float])

    def test_rosen_hess_p(self):
        self.run_test("""import numpy
def np_rosen_hess_p(x, p):
    x = numpy.asarray(x)
    Hp = numpy.zeros_like(x)
    Hp[0] = (1200*x[0]**2 - 400*x[1] + 2)*p[0] - 400*x[0]*p[1]
    Hp[1:-1] = -400*x[:-2]*p[:-2]+(202+1200*x[1:-1]**2-400*x[2:])*p[1:-1] \
               -400*x[1:-1]*p[2:]
    Hp[-1] = -400*x[-2]*p[-2] + 200*p[-1]
    return Hp
""",
                      runas="""
import numpy; np_rosen_hess_p(numpy.array([1.3, 0.7, 0.8, 1.9, 1.2]), numpy.array([2.3, 1.7, 1.8, 2.9, 2.2]))""",
                      np_rosen_hess_p=[numpy.array([float]), numpy.array([float])])

    def test_rosen_hess(self):
        self.run_test("""import numpy
def np_rosen_hess(x):
    x = numpy.asarray(x)
    H = numpy.diag(-400*x[:-1],1) - numpy.diag(400*x[:-1],-1)
    diagonal = numpy.zeros_like(x)
    diagonal[0] = 1200*x[0]**2-400*x[1]+2
    diagonal[-1] = 200
    diagonal[1:-1] = 202 + 1200*x[1:-1]**2 - 400*x[2:]
    H = H + numpy.diag(diagonal)
    return H
""",
                      runas="import numpy; np_rosen_hess(numpy.array([1.3, 0.7, 0.8, 1.9, 1.2]))",
                      np_rosen_hess=[numpy.array([float])])

    def test_rosen_der(self):
        self.run_test("""import numpy
def np_rosen_der(x):
    xm = x[1:-1]
    xm_m1 = x[:-2]
    xm_p1 = x[2:]
    der = numpy.zeros_like(x)
    der[1:-1] = 200*(xm-xm_m1**2) - 400*(xm_p1 - xm**2)*xm - 2*(1-xm)
    der[0] = -400*x[0]*(x[1]-x[0]**2) - 2*(1-x[0])
    der[-1] = 200*(x[-1]-x[-2]**2)
    return der
""",
                      runas="import numpy; np_rosen_der( numpy.array([1.3, 0.7, 0.8, 1.9, 1.2]))",
                      np_rosen_der=[numpy.array([float])])

    def test_rosen(self):
        self.run_test("import numpy\ndef np_rosen(x): return sum(100.0*(x[1:]-x[:-1]**2.0)**2.0 + (1-x[:-1])**2.0)",
                      runas="import numpy; np_rosen(numpy.array([1.3, 0.7, 0.8, 1.9, 1.2]))",
                      np_rosen=[numpy.array([float])])

    def test_nanargmax0(self):
        self.run_test("def np_nanargmax0(a): from numpy import nanargmax; return nanargmax(a)", numpy.array([[numpy.nan, 4], [2, 3]]),  np_nanargmax0=[numpy.array([[float]])])

    def test_nanargmin0(self):
        self.run_test("def np_nanargmin0(a): from numpy import nanargmin ; return nanargmin(a)", numpy.array([[numpy.nan, 4], [2, 3]]), np_nanargmin0=[numpy.array([[float]])])

    def test_nan_to_num0(self):
        self.run_test("def np_nan_to_num0(a): import numpy as np ; return np.nan_to_num(a)", numpy.array([numpy.inf, -numpy.inf, numpy.nan, -128, 128]), np_nan_to_num0=[numpy.array([float])])

    def test_median0(self):
        self.run_test("def np_median0(a): from numpy import median ; return median(a)", numpy.array([[1, 2], [3, 4]]), np_median0=[numpy.array([[int]])])

    def test_median1(self):
        self.run_test("def np_median1(a): from numpy import median ; return median(a)", numpy.array([1, 2, 3, 4,5]), np_median1=[numpy.array([int])])

    def test_mean0(self):
        self.run_test("def np_mean0(a): from numpy import mean ; return mean(a)", numpy.array([[1, 2], [3, 4]]), np_mean0=[numpy.array([[int]])])

    def test_logspace0(self):
        self.run_test("def np_logspace0(start, stop): from numpy import logspace ; start, stop = 3., 4. ; return logspace(start, stop, 4)", 3., 4., np_logspace0=[float, float])

    def test_logspace1(self):
        self.run_test("def np_logspace1(start, stop): from numpy import logspace ; return logspace(start, stop, 4, False)", 3., 4., np_logspace1=[float, float])

    def test_logspace2(self):
        self.run_test("def np_logspace2(start, stop): from numpy import logspace ; return logspace(start, stop, 4, True, 2.0)", 3., 4., np_logspace2=[float, float])

    def test_lexsort0(self):
        self.run_test("def np_lexsort0(surnames): from numpy import lexsort ; first_names = ('Heinrich', 'Galileo', 'Gustav') ; return lexsort((first_names, surnames))", ('Hertz',    'Galilei', 'Hertz'), np_lexsort0=[(str, str, str)])

    def test_lexsort1(self):
        self.run_test("def np_lexsort1(a): from numpy import lexsort ; b = [9,4,0,4,0,2,1] ; return lexsort((a,b))", [1,5,1,4,3,4,4], np_lexsort1=[[int]])

    def test_item0(self):
        self.run_test("def np_item0(a): return a.item(3)", numpy.array([[3, 1, 7],[2, 8, 3],[8, 5, 3]]), np_item0=[numpy.array([[int]])])

    def test_item1(self):
        self.run_test("def np_item1(a): return a.item(7)", numpy.array([[3, 1, 7],[2, 8, 3],[8, 5, 3]]), np_item1=[numpy.array([[int]])])

    def test_item2(self):
        self.run_test("def np_item2(a): return a.item((0,1))",numpy.array([[3, 1, 7],[2, 8, 3],[8, 5, 3]]),  np_item2=[numpy.array([[int]])])

    def test_item3(self):
        self.run_test("def np_item3(a): return a.item((2,2))", numpy.array([[3, 1, 7],[2, 8, 3],[8, 5, 3]]), np_item3=[numpy.array([[int]])])

    def test_item4(self):
        self.run_test("def np_item4(a): return a.item(-2)", numpy.array([[3, 1, 7],[2, 8, 3],[8, 5, 3]]), np_item4=[numpy.array([[int]])])

    def test_issctype0(self):
        self.run_test("def np_issctype0(): from numpy import issctype, int32 ; a = int32 ; return issctype(a)", np_issctype0=[])

    def test_issctype1(self):
        self.run_test("def np_issctype1(): from numpy import issctype ; a = list ; return issctype(a)", np_issctype1=[])

    def test_issctype2(self):
        self.run_test("def np_issctype2(a): from numpy import issctype ; return issctype(a)", 3.1, np_issctype2=[float])

    def test_isscalar0(self):
        self.run_test("def np_isscalar0(a): from numpy import isscalar ; return isscalar(a)", 3.1, np_isscalar0=[float])

    def test_isscalar1(self):
        self.run_test("def np_isscalar1(a): from numpy import isscalar ; return isscalar(a)", [3.1], np_isscalar1=[[float]])

    def test_isscalar2(self):
        self.run_test("def np_isscalar2(a): from numpy import isscalar ; return isscalar(a)", '3.1', np_isscalar2=[str])

    def test_isrealobj0(self):
        self.run_test("def np_isrealobj0(a): from numpy import isrealobj ; return isrealobj(a)", numpy.array([1,2,3.]), np_isrealobj0=[numpy.array([float])])

    def test_isrealobj1(self):
        self.run_test("def np_isrealobj1(a): from numpy import isrealobj ; return isrealobj(a)", numpy.array([1,2,3.,4 + 1j]).reshape(2,2), np_isrealobj1=[numpy.array([[complex]])])

    def test_isreal0(self):
        self.run_test("def np_isreal0(a): from numpy import isreal ; return isreal(a)", numpy.array([1,2,3.]), np_isreal0=[numpy.array([float])])

    def test_isreal1(self):
        self.run_test("def np_isreal1(a): from numpy import isreal ; return isreal(a)", numpy.array([1,2,3.,4 + 1j]).reshape(2,2), np_isreal1=[numpy.array([[complex]])])

    def test_iscomplex0(self):
        self.run_test("def np_iscomplex0(a): from numpy import iscomplex ; return iscomplex(a)", numpy.array([1, 2, 3.]), np_iscomplex0=[numpy.array([float])])

    def test_iscomplex1(self):
        self.run_test("def np_iscomplex1(a): from numpy import iscomplex ; return iscomplex(a)", numpy.array([1,2,3.,4 + 1j]).reshape(2,2), np_iscomplex1=[numpy.array([[complex]])])

    def test_intersect1d0(self):
        self.run_test("def np_intersect1d0(a): from numpy import intersect1d ; b = [3, 1, 2, 1] ; return intersect1d(a,b)", [1, 3, 4, 3], np_intersect1d0=[[int]])

    def test_insert0(self):
        self.run_test("def np_insert0(a): from numpy import insert ; return insert(a, 1, 5)", numpy.array([[1, 1], [2, 2], [3, 3]]), np_insert0=[numpy.array([[int]])])

    def test_insert1(self):
        self.run_test("def np_insert1(a): from numpy import insert ; return insert(a, [1,2], [5,6])", numpy.array([[1, 1], [2, 2], [3, 3]]), np_insert1=[numpy.array([[int]])])

    def test_insert2(self):
        self.run_test("def np_insert2(a): from numpy import insert ; return insert(a, [1,1], [5.2,6,7])", numpy.array([[1, 1], [2, 2], [3, 3]]), np_insert2=[numpy.array([[int]])])

    def test_inner0(self):
        self.run_test("def np_inner0(x): from numpy import inner ; y = 3 ; return inner(x,y)", 2, np_inner0=[int])

    def test_inner1(self):
        self.run_test("def np_inner1(x): from numpy import inner ; y = [2, 3] ; return inner(x,y)", [2, 3], np_inner1=[[int]])

    def test_indices0(self):
        self.run_test("def np_indices0(s): from numpy import indices ; return indices(s)", (2, 3), np_indices0=[(int, int)])

    def test_identity0(self):
        self.run_test("def np_identity0(a): from numpy import identity ; return identity(a)", 3, np_identity0=[int])

    def test_identity1(self):
        self.run_test("def np_identity1(a): from numpy import identity ;return identity(a)", 4, np_identity1=[int])

    def test_fromstring0(self):
        self.run_test("def np_fromstring0(a): from numpy import fromstring, uint8 ; return fromstring(a, uint8)", '\x01\x02', np_fromstring0=[str])

    def test_fromstring1(self):
        self.run_test("def np_fromstring1(a): from numpy import fromstring, uint8 ; a = '\x01\x02\x03\x04' ; return fromstring(a, uint8,3)", '\x01\x02\x03\x04', np_fromstring1=[str])

    def test_fromstring2(self):
        self.run_test("def np_fromstring2(a): from numpy import fromstring, uint32 ; return fromstring(a, uint32,-1, ' ')", '1 2 3 4', np_fromstring2=[str])

    def test_fromstring3(self):
        self.run_test("def np_fromstring3(a): from numpy import fromstring, uint32 ; return fromstring(a, uint32,2, ',')", '1,2, 3, 4', np_fromstring3=[str])

    def test_outer0(self):
        self.run_test("def np_outer0(x): from numpy import outer ; return outer(x, x+2)", numpy.arange(6).reshape(2,3), np_outer0=[numpy.array([[int]])])

    def test_outer1(self):
        self.run_test("def np_outer1(x): from numpy import outer; return outer(x, range(6))", numpy.arange(6).reshape(2,3), np_outer1=[numpy.array([[int]])])

    def test_place0(self):
        self.run_test("def np_place0(x): from numpy import place, ravel ; place(x, x>1, ravel(x**2)); return x", numpy.arange(6).reshape(2,3), np_place0=[numpy.array([[int]])])

    def test_place1(self):
        self.run_test("def np_place1(x): from numpy import place ; place(x, x>1, [57, 58]); return x", numpy.arange(6).reshape(2,3), np_place1=[numpy.array([[int]])])

    def test_product(self):
        self.run_test("def np_product(x):\n from numpy import product\n return product(x)", numpy.arange(1, 10), np_product=[numpy.array([int])])

    def test_prod_(self):
        self.run_test("def np_prod_(x):\n from numpy import prod\n return x.prod()", numpy.arange(1, 10), np_prod_=[numpy.array([int])])

    def test_prod_expr(self):
        self.run_test("def np_prod_expr(x):\n from numpy import ones, prod\n return (x + ones(10)).prod()", numpy.arange(10), np_prod_expr=[numpy.array([int])])

    def test_prod2_(self):
        self.run_test("def np_prod2_(x):\n from numpy import prod\n return x.prod()", numpy.arange(1, 11).reshape(2,5), np_prod2_=[numpy.array([[int]])])

    def test_prod3_(self):
        self.run_test("def np_prod3_(x):\n from numpy import prod\n return x.prod(1)", numpy.arange(1, 11).reshape(2,5), np_prod3_=[numpy.array([[int]])])

    def test_prod4_(self):
        self.run_test("def np_prod4_(x):\n from numpy import prod\n return x.prod(0)", numpy.arange(1, 11).reshape(2,5), np_prod4_=[numpy.array([[int]])])

    def test_prod5_(self):
        self.run_test("def np_prod5_(x):\n from numpy import prod\n return x.prod(0)", numpy.arange(1, 11), np_prod5_=[numpy.array([int])])

    def test_ptp0(self):
        self.run_test("def np_ptp0(x): from numpy import ptp ; return ptp(x)", numpy.arange(4).reshape(2,2), np_ptp0=[numpy.array([[int]])])

    def test_ptp1(self):
        self.run_test("def np_ptp1(x): from numpy import ptp ; return ptp(x,0)", numpy.arange(4).reshape(2,2), np_ptp1=[numpy.array([[int]])])

    def test_ptp2(self):
        self.run_test("def np_ptp2(x): from numpy import ptp ; return ptp(x,1)", numpy.arange(4).reshape(2,2), np_ptp2=[numpy.array([[int]])])

    def test_put0(self):
        self.run_test("def np_put0(x): from numpy import put ; put(x, [0,2], [-44, -55]); return x", numpy.arange(5), np_put0=[numpy.array([int])])

    def test_put1(self):
        self.run_test("def np_put1(x): from numpy import put ; put(x, [0,2,3], [57, 58]); return x", numpy.arange(6).reshape(2, 3), np_put1=[numpy.array([[int]])])

    def test_put2(self):
        self.run_test("def np_put2(x): from numpy import put ; put(x, 2, 57); return x", numpy.arange(6).reshape(2,3), np_put2=[numpy.array([[int]])])

    def test_putmask0(self):
        self.run_test("def np_putmask0(x): from numpy import putmask ; putmask(x, x>1, x**2); return x", numpy.arange(6).reshape(2,3), np_putmask0=[numpy.array([[int]])])

    def test_putmask1(self):
        self.run_test("def np_putmask1(x): from numpy import putmask; putmask(x, x>1, [57, 58]); return x", numpy.arange(6).reshape(2,3), np_putmask1=[numpy.array([[int]])])

    def test_ravel(self):
        self.run_test("def np_ravel(x): from numpy import ravel ; return ravel(x)", numpy.arange(6).reshape(2,3), np_ravel=[numpy.array([[int]])])

    def test_repeat(self):
        self.run_test("def np_repeat(x): from numpy import repeat; return repeat(x, 3)", numpy.arange(3), np_repeat=[numpy.array([int])])

    def test_resize4(self):
        self.run_test("def np_resize4(x): from numpy import resize ; return resize(x, (6,7))", numpy.arange(24).reshape(2,3,4), np_resize4=[numpy.array([[[int]]])])

    def test_resize3(self):
        self.run_test("def np_resize3(x): from numpy import resize; return resize(x, (6,6))", numpy.arange(24).reshape(2,3,4), np_resize3=[numpy.array([[[int]]])])

    def test_resize2(self):
        self.run_test("def np_resize2(x): from numpy import resize; return resize(x, (3,3))", numpy.arange(24).reshape(2,3,4), np_resize2=[numpy.array([[[int]]])])

    def test_resize1(self):
        self.run_test("def np_resize1(x): from numpy import resize; return resize(x, 32)", numpy.arange(24), np_resize1=[numpy.array([int])])

    def test_resize0(self):
        self.run_test("def np_resize0(x): from numpy import resize; return resize(x, 12)", numpy.arange(24), np_resize0=[numpy.array([int])])

    def test_rollaxis2(self):
        self.run_test("def np_rollaxis2(x): from numpy import rollaxis; return rollaxis(x, 2)", numpy.arange(24).reshape(2,3,4), np_rollaxis2=[numpy.array([[[int]]])])

    def test_rollaxis1(self):
        self.run_test("def np_rollaxis1(x): from numpy import rollaxis; return rollaxis(x, 1, 2)", numpy.arange(24).reshape(2,3,4), np_rollaxis1=[numpy.array([[[int]]])])

    def test_rollaxis0(self):
        self.run_test("def np_rollaxis0(x): from numpy import rollaxis; return rollaxis(x, 1)", numpy.arange(24).reshape(2,3,4), np_rollaxis0=[numpy.array([[[int]]])])

    def test_roll6(self):
        self.run_test("def np_roll6(x): from numpy import roll; return roll(x[:,:,:-1], -1, 2)", numpy.arange(24).reshape(2,3,4), np_roll6=[numpy.array([[[int]]])])

    def test_roll5(self):
        self.run_test("def np_roll5(x): from numpy import roll; return roll(x, -1, 2)", numpy.arange(24).reshape(2,3,4), np_roll5=[numpy.array([[[int]]])])

    def test_roll4(self):
        self.run_test("def np_roll4(x): from numpy import roll; return roll(x, 1, 1)", numpy.arange(24).reshape(2,3,4), np_roll4=[numpy.array([[[int]]])])

    def test_roll3(self):
        self.run_test("def np_roll3(x): from numpy import roll; return roll(x, -1, 0)", numpy.arange(24).reshape(2,3,4), np_roll3=[numpy.array([[[int]]])])

    def test_roll2(self):
        self.run_test("def np_roll2(x): from numpy import roll; return roll(x, -1)", numpy.arange(24).reshape(2,3,4), np_roll2=[numpy.array([[[int]]])])

    def test_roll1(self):
        self.run_test("def np_roll1(x): from numpy import roll; return roll(x, 10)", numpy.arange(24).reshape(2,3,4), np_roll1=[numpy.array([[[int]]])])

    def test_roll0(self):
        self.run_test("def np_roll0(x): from numpy import roll; return roll(x, 3)", numpy.arange(24).reshape(2,3,4), np_roll0=[numpy.array([[[int]]])])

    def test_searchsorted3(self):
        self.run_test("def np_searchsorted3(x): from numpy import searchsorted; return searchsorted(x, [[3,4],[1,87]])", numpy.arange(6), np_searchsorted3=[numpy.array([int])])

    def test_searchsorted2(self):
        self.run_test("def np_searchsorted2(x): from numpy import searchsorted; return searchsorted(x, [[3,4],[1,87]], 'right')", numpy.arange(6), np_searchsorted2=[numpy.array([int])])

    def test_searchsorted1(self):
        self.run_test("def np_searchsorted1(x): from numpy import searchsorted; return searchsorted(x, 3)", numpy.arange(6), np_searchsorted1=[numpy.array([int])])

    def test_searchsorted0(self):
        self.run_test("def np_searchsorted0(x): from numpy import searchsorted; return searchsorted(x, 3, 'right')", numpy.arange(6), np_searchsorted0=[numpy.array([int])])

    def test_rank1(self):
        self.run_test("def np_rank1(x): from numpy import rank; return rank(x)", numpy.arange(24).reshape(2,3,4), np_rank1=[numpy.array([[[int]]])])

    def test_rank0(self):
        self.run_test("def np_rank0(x): from numpy import rank; return rank(x)", numpy.arange(6), np_rank0=[numpy.array([int])])

    def test_rot904(self):
        self.run_test("def np_rot904(x): from numpy import rot90; return rot90(x, 4)", numpy.arange(24).reshape(2,3,4), np_rot904=[numpy.array([[[int]]])])

    def test_rot903(self):
        self.run_test("def np_rot903(x): from numpy import rot90; return rot90(x, 2)", numpy.arange(24).reshape(2,3,4), np_rot903=[numpy.array([[[int]]])])

    def test_rot902(self):
        self.run_test("def np_rot902(x): from numpy import rot90; return rot90(x, 3)", numpy.arange(24).reshape(2,3,4), np_rot902=[numpy.array([[[int]]])])

    def test_rot900(self):
        self.run_test("def np_rot900(x): from numpy import rot90; return rot90(x)", numpy.arange(24).reshape(2,3,4), np_rot900=[numpy.array([[[int]]])])

    def test_rot901(self):
        self.run_test("def np_rot901(x): from numpy import rot90; return rot90(x)", numpy.arange(4).reshape(2,2), np_rot901=[numpy.array([[int]])])

    def test_select2(self):
        self.run_test("def np_select2(x): from numpy import select; condlist = [x<3, x>5]; choicelist = [x, x**2]; return select(condlist, choicelist)", numpy.arange(10).reshape(2,5), np_select2=[numpy.array([[int]])])

    def test_select1(self):
        self.run_test("def np_select1(x): from numpy import select; condlist = [x<3, x>5]; choicelist = [x+3, x**2]; return select(condlist, choicelist)", numpy.arange(10), np_select1=[numpy.array([int])])

    def test_select0(self):
        self.run_test("def np_select0(x): from numpy import select; condlist = [x<3, x>5]; choicelist = [x, x**2]; return select(condlist, choicelist)", numpy.arange(10), np_select0=[numpy.array([int])])

    def test_sometrue0(self):
        self.run_test("def np_sometrue0(a): from numpy import sometrue ; return sometrue(a)", numpy.array([[True, False], [True, True]]), np_sometrue0=[numpy.array([[bool]])])

    def test_sometrue1(self):
        self.run_test("def np_sometrue1(a): from numpy import sometrue ; return sometrue(a, 0)", numpy.array([[True, False], [False, False]]), np_sometrue1=[numpy.array([[bool]])])

    def test_sometrue2(self):
        self.run_test("def np_sometrue2(a): from numpy import sometrue ; return sometrue(a)", [-1, 0, 5], np_sometrue2=[[int]])

    def test_sort0(self):
        self.run_test("def np_sort0(a): from numpy import sort ; return sort(a)", numpy.array([[1,6],[7,5]]), np_sort0=[numpy.array([[int]])])

    def test_sort1(self):
        self.run_test("def np_sort1(a): from numpy import sort ; return sort(a)", numpy.array([2, 1, 6, 3, 5]), np_sort1=[numpy.array([int])])

    def test_sort2(self):
        self.run_test("def np_sort2(a): from numpy import sort ; return sort(a)", numpy.arange(2*3*4, 0, -1).reshape(2,3,4), np_sort2=[numpy.array([[[int]]])])

    def test_sort3(self):
        self.run_test("def np_sort3(a): from numpy import sort ; return sort(a, 0)", numpy.arange(2*3*4, 0, -1).reshape(2,3,4), np_sort3=[numpy.array([[[int]]])])

    def test_sort4(self):
        self.run_test("def np_sort4(a): from numpy import sort ; return sort(a, 1)", numpy.arange(2*3*4, 0, -1).reshape(2,3,4), np_sort4=[numpy.array([[[int]]])])

    def test_sort_complex0(self):
        self.run_test("def np_sort_complex0(a): from numpy import sort_complex ; return sort_complex(a)", numpy.array([[1,6],[7,5]]), np_sort_complex0=[numpy.array([[int]])])

    def test_sort_complex1(self):
        self.run_test("def np_sort_complex1(a): from numpy import sort_complex ; return sort_complex(a)", numpy.array([1 + 2j, 2 - 1j, 3 - 2j, 3 - 3j, 3 + 5j]), np_sort_complex1=[numpy.array([complex])])

    def test_split0(self):
        self.run_test("def np_split0(a): from numpy import split,array2string ; return map(array2string,split(a, 3))", numpy.arange(12), np_split0=[numpy.array([int])])

    def test_split1(self):
        self.run_test("def np_split1(a):\n from numpy import split\n try:\n  print split(a, 5)\n  return False\n except ValueError:\n  return True", numpy.arange(12), np_split1=[numpy.array([int])])

    def test_split2(self):
        self.run_test("def np_split2(a): from numpy import split, array2string; return map(array2string,split(a, [0,1,5]))", numpy.arange(12).reshape(6,2), np_split2=[numpy.array([[int]])])

    def test_take0(self):
        self.run_test("def np_take0(a):\n from numpy import take\n return take(a, [0,1])", numpy.arange(24).reshape(2,3,4), np_take0=[numpy.array([[[int]]])])

    def test_take1(self):
        self.run_test("def np_take1(a):\n from numpy import take\n return take(a, [[0,0,2,2],[1,0,1,2]])", numpy.arange(24).reshape(2,3,4), np_take1=[numpy.array([[[int]]])])

    def test_swapaxes_(self):
        self.run_test("def np_swapaxes_(a):\n from numpy import swapaxes\n return swapaxes(a, 1, 2)", numpy.arange(24).reshape(2,3,4), np_swapaxes_=[numpy.array([[[int]]])])

    def test_tile0(self):
        self.run_test("def np_tile0(a): from numpy import tile ; return tile(a, 3)", numpy.arange(4), np_tile0=[numpy.array([int])])

    def test_tile1(self):
        self.run_test("def np_tile1(a): from numpy import tile ; return tile(a, (3, 2))", numpy.arange(4), np_tile1=[numpy.array([int])])

    def test_tolist0(self):
        self.run_test("def np_tolist0(a): return a.tolist()", numpy.arange(12), np_tolist0=[numpy.array([int])])

    def test_tolist1(self):
        self.run_test("def np_tolist1(a): return a.tolist()", numpy.arange(12).reshape(3,4), np_tolist1=[numpy.array([[int]])])

    def test_tolist2(self):
        self.run_test("def np_tolist2(a): return a.tolist()", numpy.arange(2*3*4*5).reshape(2,3,4,5), np_tolist2=[numpy.array([[[[int]]]])])

    def test_tostring0(self):
        self.run_test("def np_tostring0(a): return a.tostring()", numpy.arange(80, 100), np_tostring0=[numpy.array([int])])

    def test_tostring1(self):
        self.run_test("def np_tostring1(a): return a.tostring()", numpy.arange(500, 600), np_tostring1=[numpy.array([int])])

    def test_fromiter0(self):
        self.run_test("def g(): yield 1 ; yield 2\ndef np_fromiter0(): from numpy import fromiter, float32 ; iterable = g() ; return fromiter(iterable, float32)", np_fromiter0=[])

    def test_fromiter1(self):
        self.run_test("def np_fromiter1(): from numpy import fromiter, float32 ; iterable = (x*x for x in range(5)) ; return fromiter(iterable, float32, 5)", np_fromiter1=[])

    def test_fromfunction0(self):
        self.run_test("def np_fromfunction0(s): from numpy import fromfunction ; return fromfunction(lambda i: i == 1, s)", (3,), np_fromfunction0=[(int,)])

    def test_fromfunction1(self):
        self.run_test("def np_fromfunction1(s): from numpy import fromfunction; return fromfunction(lambda i, j: i + j, s)", (3, 3), np_fromfunction1=[(int, int)])

    def test_flipud0(self):
        self.run_test("def np_flipud0(x): from numpy import flipud ; return flipud(x)", numpy.arange(9).reshape(3,3), np_flipud0=[numpy.array([[int]])])

    def test_fliplr0(self):
        self.run_test("def np_fliplr0(x): from numpy import fliplr ; return fliplr(x)", numpy.arange(9).reshape(3,3), np_fliplr0=[numpy.array([[int]])])

    def test_flatten0(self):
        self.run_test("def np_flatten0(x): return x.flatten()", numpy.array([[1,2], [3,4]]), np_flatten0=[numpy.array([[int]])])

    def test_flatnonzero0(self):
        self.run_test("def np_flatnonzero0(x): from numpy import flatnonzero ; return flatnonzero(x)", numpy.arange(-2, 3), np_flatnonzero0=[numpy.array([int])])

    def test_flatnonzero1(self):
        self.run_test("def np_flatnonzero1(x): from numpy import flatnonzero ;  return flatnonzero(x[1:-1])", numpy.arange(-2, 3), np_flatnonzero1=[numpy.array([int])])

    def test_fix0(self):
        self.run_test("def np_fix0(x): from numpy import fix ; return fix(x)", 3.14, np_fix0=[float])

    def test_fix1(self):
        self.run_test("def np_fix1(x): from numpy import fix ; return fix(x)", 3, np_fix1=[int])

    def test_fix2(self):
        self.run_test("def np_fix2(x): from numpy import fix ; return fix(x)", numpy.array([2.1, 2.9, -2.1, -2.9]), np_fix2=[numpy.array([float])])

    def test_fix3(self):
        self.run_test("def np_fix3(x): from numpy import fix ; return fix(x)", numpy.array([2.1, 2.9, -2.1, -2.9]), np_fix3=[numpy.array([float])])

    def test_fix4(self):
        self.run_test("def np_fix4(x): from numpy import fix ; return fix(x+x)", numpy.array([2.1, 2.9, -2.1, -2.9]), np_fix4=[numpy.array([float])])

    def test_finfo0(self):
        self.run_test("def np_finfo0(): from numpy import finfo, float64 ; x = finfo(float64) ; return x.eps", np_finfo0=[])

    def test_fill0(self):
        self.run_test("def np_fill0(x): x.fill(5) ; return x", numpy.ones((2, 3)), np_fill0=[numpy.array([[float]])])

    def test_eye0(self):
        self.run_test("def np_eye0(x): from numpy import eye ; return eye(x)", 2, np_eye0=[int])

    def test_eye1(self):
        self.run_test("def np_eye1(x): from numpy import eye ; return eye(x, x+1)", 2, np_eye1=[int])

    def test_eye1b(self):
        self.run_test("def np_eye1b(x): from numpy import eye ; return eye(x, x-1)", 3, np_eye1b=[int])

    def test_eye2(self):
        self.run_test("def np_eye2(x): from numpy import eye ; return eye(x, x, 1)", 2, np_eye2=[int])

    def test_eye3(self):
        self.run_test("def np_eye3(x): from numpy import eye, int32 ; return eye(x, x, 1, int32)", 2, np_eye3=[int])

    def test_ediff1d0(self):
        self.run_test("def np_ediff1d0(x): from numpy import ediff1d ; return ediff1d(x)", [1,2,4,7,0], np_ediff1d0=[[int]])

    def test_ediff1d1(self):
        self.run_test("def np_ediff1d1(x): from numpy import ediff1d ; return ediff1d(x)", [[1,2,4],[1,6,24]], np_ediff1d1=[[[int]]])

    def test_dot0(self):
        self.run_test("def np_dot0(x, y): from numpy import dot ; return dot(x,y)", 2, 3, np_dot0=[int, int])

    def test_dot1(self):
        self.run_test("def np_dot1(x): from numpy import dot ; y = [2, 3] ; return dot(x,y)", [2, 3], np_dot1=[[int]])

    def test_dot2(self):
        self.run_test("def np_dot2(x): from numpy import dot ; y = [2j, 3j] ; return dot(x,y)", [2j, 3j], np_dot2=[[complex]])

    def test_dot3(self):
        self.run_test("def np_dot3(x): from numpy import array, dot ; y = array([2, 3]) ; return dot(x+x,y)", numpy.array([2, 3]), np_dot3=[numpy.array([int])])

    def test_dot4(self):
        self.run_test("def np_dot4(x): from numpy import dot ; y = [2, 3] ; return dot(x,y)", numpy.array([2, 3]), np_dot4=[numpy.array([int])])

    def test_digitize0(self):
        self.run_test("def np_digitize0(x): from numpy import array, digitize ; bins = array([0.0, 1.0, 2.5, 4.0, 10.0]) ; return digitize(x, bins)", numpy.array([0.2, 6.4, 3.0, 1.6]), np_digitize0=[numpy.array([float])])

    def test_digitize1(self):
        self.run_test("def np_digitize1(x): from numpy import array, digitize ; bins = array([ 10.0, 4.0, 2.5, 1.0, 0.0]) ; return digitize(x, bins)", numpy.array([0.2, 6.4, 3.0, 1.6]), np_digitize1=[numpy.array([float])])

    def test_diff0(self):
        self.run_test("def np_diff0(x): from numpy import diff; return diff(x)", numpy.array([1, 2, 4, 7, 0]), np_diff0=[numpy.array([int])])

    def test_diff1(self):
        self.run_test("def np_diff1(x): from numpy import diff; return diff(x,2)", numpy.array([1, 2, 4, 7, 0]), np_diff1=[numpy.array([int])])

    def test_diff2(self):
        self.run_test("def np_diff2(x): from numpy import diff; return diff(x)", numpy.array([[1, 3, 6, 10], [0, 5, 6, 8]]), np_diff2=[numpy.array([[int]])])

    def test_diff3(self):
        self.run_test("def np_diff3(x): from numpy import diff; return diff(x,2)", numpy.array([[1, 3, 6, 10], [0, 5, 6, 8]]), np_diff3=[numpy.array([[int]])])

    def test_diff4(self):
        self.run_test("def np_diff4(x): from numpy import diff; return diff(x + x)", numpy.array([1, 2, 4, 7, 0]), np_diff4=[numpy.array([int])])

    def test_trace0(self):
        self.run_test("def np_trace0(x): from numpy import trace; return trace(x)", numpy.arange(9).reshape(3,3), np_trace0=[numpy.array([[int]])])

    def test_trace1(self):
        self.run_test("def np_trace1(x): from numpy import trace; return trace(x, 1)", numpy.arange(12).reshape(3,4), np_trace1=[numpy.array([[int]])])

    def test_trace2(self):
        self.run_test("def np_trace2(x): from numpy import trace; return trace(x, 1)", numpy.arange(12).reshape(3,4), np_trace2=[numpy.array([[int]])])

    def test_tri0(self):
        self.run_test("def np_tri0(a): from numpy import tri; return tri(a)", 3, np_tri0=[int])

    def test_tri1(self):
        self.run_test("def np_tri1(a): from numpy import tri; return tri(a, 4)", 3, np_tri1=[int])

    def test_tri2(self):
        self.run_test("def np_tri2(a): from numpy import tri; return tri(a, 3, -1)", 4, np_tri2=[int])

    def test_tri3(self):
        self.run_test("def np_tri3(a): from numpy import tri, int64; return tri(a, 5, 1, int64)", 3, np_tri3=[int])

    def test_trim_zeros0(self):
        self.run_test("""
def np_trim_zeros0(x):
    from numpy import array, trim_zeros
    return trim_zeros(x)""", numpy.array((0, 0, 0, 1, 2, 3, 0, 2, 1, 0)), np_trim_zeros0=[numpy.array([int])])

    def test_trim_zeros1(self):
        self.run_test("""
def np_trim_zeros1(x):
    from numpy import array, trim_zeros
    return trim_zeros(x, "f")""", numpy.array((0, 0, 0, 1, 2, 3, 0, 2, 1, 0)), np_trim_zeros1=[numpy.array([int])])

    def test_trim_zeros2(self):
        self.run_test("""
def np_trim_zeros2(x):
    from numpy import trim_zeros
    return trim_zeros(x, "b")""", numpy.array((0, 0, 0, 1, 2, 3, 0, 2, 1, 0)), np_trim_zeros2=[numpy.array([int])])

    def test_triu0(self):
        self.run_test("def np_triu0(x): from numpy import triu; return triu(x)", numpy.arange(12).reshape(3,4), np_triu0=[numpy.array([[int]])])

    def test_triu1(self):
        self.run_test("def np_triu1(x): from numpy import triu; return triu(x, 1)", numpy.arange(12).reshape(3,4), np_triu1=[numpy.array([[int]])])

    def test_triu2(self):
        self.run_test("def np_triu2(x): from numpy import triu; return triu(x, -1)", numpy.arange(12).reshape(3,4), np_triu2=[numpy.array([[int]])])

    def test_tril0(self):
        self.run_test("def np_tril0(x): from numpy import tril; return tril(x)", numpy.arange(12).reshape(3,4), np_tril0=[numpy.array([[int]])])

    def test_tril1(self):
        self.run_test("def np_tril1(x): from numpy import tril; return tril(x, 1)", numpy.arange(12).reshape(3,4), np_tril1=[numpy.array([[int]])])

    def test_tril2(self):
        self.run_test("def np_tril2(x): from numpy import tril; return tril(x, -1)", numpy.arange(12).reshape(3,4), np_tril2=[numpy.array([[int]])])

    def test_union1d(self):
        self.run_test("def np_union1d(x): from numpy import arange, union1d ; y = arange(1,4); return union1d(x, y)", numpy.arange(-1,2), np_union1d=[numpy.array([int])])

    def test_unique0(self):
        self.run_test("def np_unique0(x): from numpy import unique ; return unique(x)", numpy.array([1,1,2,2,2,1,5]), np_unique0=[numpy.array([int])])

    def test_unique1(self):
        self.run_test("def np_unique1(x): from numpy import unique ; return unique(x)", numpy.array([[1,2,2],[2,1,5]]), np_unique1=[numpy.array([[int]])])

    def test_unique2(self):
        self.run_test("def np_unique2(x): from numpy import unique ; return unique(x, True)", numpy.array([1,1,2,2,2,1,5]), np_unique2=[numpy.array([int])])

    def test_unique3(self):
        self.run_test("def np_unique3(x): from numpy import unique ; return unique(x, True, True)", numpy.array([1,1,2,2,2,1,5]), np_unique3=[numpy.array([int])])

    def test_unwrap0(self):
        self.run_test("def np_unwrap0(x): from numpy import unwrap, pi ; x[:3] += 2*pi; return unwrap(x)", numpy.arange(6), np_unwrap0=[numpy.array([int])])

    def test_unwrap1(self):
        self.run_test("def np_unwrap1(x): from numpy import unwrap, pi ; x[:3] += 2*pi; return unwrap(x, 4)", numpy.arange(6), np_unwrap1=[numpy.array([int])])

    def test_unwrap2(self):
        self.run_test("def np_unwrap2(x): from numpy import unwrap, pi ; x[:3] -= 2*pi; return unwrap(x, 4)", numpy.arange(6), np_unwrap2=[numpy.array([int])])

    def test_nonzero0(self):
        self.run_test("def np_nonzero0(x): from numpy import nonzero ; return nonzero(x)", numpy.arange(6), np_nonzero0=[numpy.array([int])])

    def test_nonzero1(self):
        self.run_test("def np_nonzero1(x): from numpy import nonzero ; return nonzero(x>8)", numpy.arange(6), np_nonzero1=[numpy.array([int])])

    def test_nonzero2(self):
        self.run_test("def np_nonzero2(x): from numpy import nonzero ; return nonzero(x>0)", numpy.arange(6).reshape(2,3), np_nonzero2=[numpy.array([[int]])])

    def test_diagflat3(self):
        self.run_test("def np_diagflat3(a): from numpy import diagflat ; return diagflat(a)", numpy.arange(2), np_diagflat3=[numpy.array([int])])

    def test_diagflat4(self):
        self.run_test("def np_diagflat4(a): from numpy import diagflat ; return diagflat(a,1)", numpy.arange(3), np_diagflat4=[numpy.array([int])])

    def test_diagflat5(self):
        self.run_test("def np_diagflat5(a): from numpy import diagflat ; return diagflat(a,-2)", numpy.arange(4), np_diagflat5=[numpy.array([int])])

    def test_diagonal0(self):
        self.run_test("def np_diagonal0(a): from numpy import diagonal ; return diagonal(a)", numpy.arange(10).reshape(2,5), np_diagonal0=[numpy.array([[int]])])

    def test_diagonal1(self):
        self.run_test("def np_diagonal1(a): from numpy import diagonal ; return diagonal(a,1)", numpy.arange(9).reshape(3,3), np_diagonal1=[numpy.array([[int]])])

    def test_diagonal2(self):
        self.run_test("def np_diagonal2(a): from numpy import diagonal ; return diagonal(a,-2)", numpy.arange(9).reshape(3,3), np_diagonal2=[numpy.array([[int]])])

    def test_diag0(self):
        self.run_test("def np_diag0(a): from numpy import diag ; return diag(a)", numpy.arange(10).reshape(2,5), np_diag0=[numpy.array([[int]])])

    def test_diag1(self):
        self.run_test("def np_diag1(a): from numpy import diag ; return diag(a,1)", numpy.arange(9).reshape(3,3), np_diag1=[numpy.array([[int]])])

    def test_diag2(self):
        self.run_test("def np_diag2(a): from numpy import diag ; return diag(a,-2)", numpy.arange(9).reshape(3,3), np_diag2=[numpy.array([[int]])])

    def test_diag2b(self):
        self.run_test("def np_diag2b(a): from numpy import diag ; return diag(a,-2)", numpy.arange(12).reshape(4,3), np_diag2b=[numpy.array([[int]])])

    def test_diag3(self):
        self.run_test("def np_diag3(a): from numpy import diag ; return diag(a)", numpy.arange(2), np_diag3=[numpy.array([int])])

    def test_diag4(self):
        self.run_test("def np_diag4(a): from numpy import diag ; return diag(a,1)", numpy.arange(3), np_diag4=[numpy.array([int])])

    def test_diag5(self):
        self.run_test("def np_diag5(a): from numpy import diag; return diag(a,-2)", numpy.arange(4), np_diag5=[numpy.array([int])])

    def test_delete0(self):
        self.run_test("def np_delete0(a): from numpy import delete ; return delete(a, 1)", numpy.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]]), np_delete0=[numpy.array([[int]])])

    def test_delete1(self):
        self.run_test("def np_delete1(a): from numpy import delete ; return delete(a, [1,3,5])", numpy.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]]), np_delete1=[numpy.array([[int]])])

    def test_where0(self):
        self.run_test("""def np_where0(a):
    from numpy import arange, where
    b = arange(5, 17).reshape(3,4)
    c = [[0, 1, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0]]
    return where(c , a, b)""", numpy.arange(12).reshape(3,4), np_where0=[numpy.array([[int]])])

    def test_where1(self):
        self.run_test("""def np_where1(a):
    from numpy import arange, where
    c = [[0, 1, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0]]
    return where(True , a, c)""", numpy.arange(12).reshape(3,4), np_where1=[numpy.array([[int]])])

    def test_where2(self):
        self.run_test("""def np_where2(a):
    from numpy import arange, where
    c = [[0, 1, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0]]
    return where(False , a, c)""", numpy.arange(12).reshape(3,4), np_where2=[numpy.array([[int]])])

    def test_where3(self):
        self.run_test("""def np_where3(a):
    from numpy import arange, where
    c = [[0, 1, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0]]
    return where(True , a, 5)""", numpy.arange(12).reshape(3,4), np_where3=[numpy.array([[int]])])

    def test_where4(self):
        self.run_test("""def np_where4(a):
    from numpy import arange, where
    c = [[0, 1, 1, 1], [0, 0, 1, 1], [1, 0, 0, 0]]
    return where(False , a, 6)""", numpy.arange(12).reshape(3,4), np_where4=[numpy.array([[int]])])

    def test_where5(self):
        self.run_test("""def np_where5(a):
    from numpy import arange, where
    b = arange(5, 17).reshape(3,4)
    return where(a>5 , a, b)""", numpy.arange(12).reshape(3,4), np_where5=[numpy.array([[int]])])

    def test_where6(self):
        self.run_test("""def np_where6(a):
    from numpy import arange, where
    return where(a>5 , 1, 2)""", numpy.arange(12).reshape(3,4), np_where6=[numpy.array([[int]])])

    def test_where7(self):
        self.run_test("""def np_where7(a):
    from numpy import arange, where
    return where(a>5)""", numpy.arange(12).reshape(3,4), np_where7=[numpy.array([[int]])])

    def test_cumprod_(self):
        self.run_test("def np_cumprod_(a):\n from numpy import cumprod\n return a.cumprod()", numpy.arange(10), np_cumprod_=[numpy.array([int])])

    def test_cumprod2_(self):
        self.run_test("def np_cumprod2_(a):\n from numpy import cumprod\n return a.cumprod()", numpy.arange(10).reshape(2,5), np_cumprod2_=[numpy.array([[int]])])

    def test_cumprod3_(self):
        self.run_test("def np_cumprod3_(a):\n from numpy import cumprod\n return a.cumprod(1)", numpy.arange(10).reshape(2,5), np_cumprod3_=[numpy.array([[int]])])

    def test_cumprod4_(self):
        self.run_test("def np_cumprod4_(a):\n from numpy import cumprod\n return a.cumprod(0)", numpy.arange(10).reshape(2,5), np_cumprod4_=[numpy.array([[int]])])

    def test_cumprod5_(self):
        self.run_test("def np_cumprod5_(a):\n from numpy import cumprod\n return a.cumprod(0)", numpy.arange(10), np_cumprod5_=[numpy.array([int])])

    def test_copy0(self):
        code= '''
def test_copy0(x):
    import numpy as np
    y = x
    z = np.copy(x)
    x[0] = 10
    return x[0], y[0], z[0]'''
        self.run_test(code, numpy.array([1, 2, 3]), test_copy0=[numpy.array([int])])

    def test_clip0(self):
        self.run_test("def np_clip0(a): from numpy import clip ; return clip(a,1,8)", numpy.arange(10), np_clip0=[numpy.array([int])])

    def test_clip1(self):
        self.run_test("def np_clip1(a): from numpy import  clip ; return clip(a,3,6)", numpy.arange(10), np_clip1=[numpy.array([int])])

    def test_concatenate0(self):
        self.run_test("def np_concatenate0(a): from numpy import array, concatenate ; b = array([[5, 6]]) ; return concatenate((a,b))", numpy.array([[1, 2], [3, 4]]), np_concatenate0=[numpy.array([[int]])])

    def test_bincount0(self):
        self.run_test("def np_bincount0(a): from numpy import bincount ; return bincount(a)", numpy.arange(5), np_bincount0=[numpy.array([int])])

    def test_bincount1(self):
        self.run_test("def np_bincount1(a, w): from numpy import bincount; return bincount(a,w)", numpy.array([0, 1, 1, 2, 2, 2]), numpy.array([0.3, 0.5, 0.2, 0.7, 1., -0.6]), np_bincount1=[numpy.array([int]), numpy.array([float])])

    def test_binary_repr0(self):
        self.run_test("def np_binary_repr0(a): from numpy import binary_repr ; return binary_repr(a)", 3, np_binary_repr0=[int])

    def test_binary_repr1(self):
        self.run_test("def np_binary_repr1(a): from numpy import binary_repr ; return binary_repr(a)", -3, np_binary_repr1=[int])

    def test_binary_repr2(self):
        self.run_test("def np_binary_repr2(a): from numpy import binary_repr ; return binary_repr(a,4)", 3, np_binary_repr2=[int])

    def test_binary_repr3(self):
        self.run_test("def np_binary_repr3(a): from numpy import binary_repr ; return binary_repr(a,4)", -3, np_binary_repr3=[int])

    def test_base_repr0(self):
        self.run_test("def np_base_repr0(a): from numpy import base_repr ; return base_repr(a)", 5, np_base_repr0=[int])

    def test_base_repr1(self):
        self.run_test("def np_base_repr1(a): from numpy import base_repr ; return base_repr(a,5)", 6, np_base_repr1=[int])

    def test_base_repr2(self):
        self.run_test("def np_base_repr2(a): from numpy import base_repr ; return base_repr(a,5,3)", 7, np_base_repr2=[int])

    def test_base_repr3(self):
        self.run_test("def np_base_repr3(a): from numpy import base_repr ; return base_repr(a, 16)", 10, np_base_repr3=[int])

    def test_base_repr4(self):
        self.run_test("def np_base_repr4(a): from numpy import base_repr ; return base_repr(a, 16)", 32, np_base_repr4=[int])

    def test_average0(self):
        self.run_test("def np_average0(a): from numpy import average ; return average(a)", numpy.arange(10), np_average0=[numpy.array([int])])

    def test_average1(self):
        self.run_test("def np_average1(a): from numpy import average ; return average(a,1)", numpy.arange(10).reshape(2,5), np_average1=[numpy.array([[int]])])

    def test_average2(self):
        self.run_test("def np_average2(a): from numpy import average ; return average(a,None, range(10))", numpy.arange(10), np_average2=[numpy.array([int])])

    def test_average3(self):
        self.run_test("def np_average3(a): from numpy import average ; return average(a,None, a)", numpy.arange(10).reshape(2,5), np_average3=[numpy.array([[int]])])

    def test_atleast_1d0(self):
        self.run_test("def np_atleast_1d0(a): from numpy import atleast_1d ; return atleast_1d(a)", 1, np_atleast_1d0=[int])

    def test_atleast_1d1(self):
        self.run_test("def np_atleast_1d1(a): from numpy import atleast_1d ; r = atleast_1d(a) ; return r is a", numpy.arange(2), np_atleast_1d1=[numpy.array([int])])

    def test_atleast_2d0(self):
        self.run_test("def np_atleast_2d0(a): from numpy import atleast_2d ; return atleast_2d(a)", 1, np_atleast_2d0=[int])

    def test_atleast_2d1(self):
        self.run_test("def np_atleast_2d1(a): from numpy import atleast_2d ; r = atleast_2d(a) ; return r is a", numpy.arange(2).reshape(1,2), np_atleast_2d1=[numpy.array([[int]])])

    def test_atleast_2d2(self):
        self.run_test("def np_atleast_2d2(a): from numpy import atleast_2d ; r = atleast_2d(a) ; return r", numpy.arange(2), np_atleast_2d2=[numpy.array([int])])

    def test_atleast_3d0(self):
        self.run_test("def np_atleast_3d0(a): from numpy import atleast_3d ; return atleast_3d(a)", 1, np_atleast_3d0=[int])

    def test_atleast_3d1(self):
        self.run_test("def np_atleast_3d1(a): from numpy import atleast_3d ; r = atleast_3d(a) ; return r is a", numpy.arange(8).reshape(2,2,2), np_atleast_3d1=[numpy.array([[[int]]])])

    def test_atleast_3d2(self):
        self.run_test("def np_atleast_3d2(a): from numpy import atleast_3d ; r = atleast_3d(a) ; return r", numpy.arange(8).reshape(2,4), np_atleast_3d2=[numpy.array([[int]])])

    def test_atleast_3d3(self):
        self.run_test("def np_atleast_3d3(a): from numpy import atleast_3d ; r = atleast_3d(a) ; return r", numpy.arange(8), np_atleast_3d3=[numpy.array([int])])

    def test_asscalar0(self):
        self.run_test("def np_asscalar0(a): from numpy import asscalar; return asscalar(a)", numpy.array([1], numpy.int32), np_asscalar0=[numpy.array([numpy.int32])])

    def test_asscalar1(self):
        self.run_test("def np_asscalar1(a): from numpy import asscalar; return asscalar(a)", numpy.array([[1]], numpy.int64), np_asscalar1=[numpy.array([numpy.int64])])

    def test_ascontiguousarray0(self):
        self.run_test("def np_ascontiguousarray0(a):\n from numpy import ascontiguousarray\n return ascontiguousarray(a)", (1,2,3), np_ascontiguousarray0=[(int, int, int)])

    def test_asarray_chkfinite0(self):
        self.run_test("def np_asarray_chkfinite0(a):\n from numpy import asarray_chkfinite\n return asarray_chkfinite(a)", (1,2,3), np_asarray_chkfinite0=[(int, int, int)])

    def test_asarray_chkfinite1(self):
        self.run_test("def np_asarray_chkfinite1(a, x):\n from numpy import asarray_chkfinite\n try: return asarray_chkfinite(a)\n except ValueError: return asarray_chkfinite(x)", [[1,2],[numpy.nan,4]], [[1.,2.],[3.,4.]], np_asarray_chkfinite1=[[[float]], [[float]]])

    def test_asarray0(self):
        self.run_test("def np_asarray0(a):\n from numpy import asarray\n return asarray(a)", (1,2,3), np_asarray0=[(int, int, int)])

    def test_asarray1(self):
        self.run_test("def np_asarray1(a):\n from numpy import asarray\n return asarray(a)", [(1,2),(3,4)], np_asarray1=[[(int, int)]])

    def test_asarray2(self):
        self.run_test("def np_asarray2(a):\n from numpy import asarray, int8\n return asarray(a, int8)", [1., 2., 3.], np_asarray2=[[float]])

    def test_asarray3(self):
        self.run_test("def np_asarray3(a):\n from numpy import asarray; b = asarray(a) ; return a is b", numpy.arange(3), np_asarray3=[numpy.array([int])])

    def test_array_str0(self):
        self.run_test("def np_array_str0(x): from numpy import array_str ; return array_str(x)", numpy.arange(3), np_array_str0=[numpy.array([int])])

    def test_array_split0(self):
        self.run_test("def np_array_split0(a): from numpy import array_split, array2string ; return map(array2string,array_split(a, 3))", numpy.arange(12), np_array_split0=[numpy.array([int])])

    def test_array_split1(self):
        self.run_test("def np_array_split1(a): from numpy import array_split, array2string ; return map(array2string,array_split(a, 5))", numpy.arange(12), np_array_split1=[numpy.array([int])])

    def test_array_split2(self):
        self.run_test("def np_array_split2(a): from numpy import array_split, array2string ; return map(array2string,array_split(a, 4))", numpy.arange(12).reshape(6,2), np_array_split2=[numpy.array([[int]])])

    def test_array_split3(self):
        self.run_test("def np_array_split3(a): from numpy import array_split, array2string ; return map(array2string,array_split(a, [0,1,5]))", numpy.arange(12).reshape(6,2), np_array_split3=[numpy.array([[int]])])

    def test_array_equiv0(self):
        self.run_test("def np_array_equiv0(a): from numpy import array_equiv ;  b = [1,2] ; return array_equiv(a,b)", [1, 2], np_array_equiv0=[[int]])

    def test_array_equiv1(self):
        self.run_test("def np_array_equiv1(a): from numpy import array_equiv ;  b = [1,3] ; return array_equiv(a,b)", [1, 2], np_array_equiv1=[[int]])

    def test_array_equiv2(self):
        self.run_test("def np_array_equiv2(a): from numpy import array_equiv ;  b = [[1,2],[1,2]] ; return array_equiv(a,b)", [1, 2], np_array_equiv2=[[int]])

    def test_array_equiv3(self):
        self.run_test("def np_array_equiv3(a): from numpy import array_equiv ;  b = [[1,2],[1,3]] ; return array_equiv(a,b)", [1, 2], np_array_equiv3=[[int]])

    def test_array_equal0(self):
        self.run_test("def np_array_equal0(a): from numpy import array_equal ;  b = [1,2] ; return array_equal(a,b)", [1, 2], np_array_equal0=[[int]])

    def test_array_equal1(self):
        self.run_test("def np_array_equal1(a): from numpy import array, array_equal ;  b = array([1,2]) ; return array_equal(a,b)", numpy.array([1,2]), np_array_equal1=[numpy.array([int])])

    def test_array_equal2(self):
        self.run_test("def np_array_equal2(a): from numpy import array, array_equal ;  b = array([[1,2],[3,5]]) ; return array_equal(a,b)", numpy.array([[1,2],[3,5]]), np_array_equal2=[numpy.array([[int]])])

    def test_array_equal3(self):
        self.run_test("def np_array_equal3(a): from numpy import array, array_equal ;  b = array([[1,2],[4,5]]) ; return array_equal(a,b)", numpy.array([[1,2],[3,5]]), np_array_equal3=[numpy.array([[int]])])

    def test_array_equal4(self):
        self.run_test("def np_array_equal4(a): from numpy import array, array_equal ;  b = array([1,2,3]) ; return array_equal(a,b)", numpy. array([1,2]), np_array_equal4=[numpy.array([int])])

    def test_array2string0(self):
        self.run_test("def np_array2string0(x): from numpy import array2string ; return array2string(x)", numpy.arange(3), np_array2string0=[numpy.array([int])])

    def test_argwhere0(self):
        self.run_test("def np_argwhere0(x): from numpy import argwhere ; return argwhere(x)", numpy.arange(6), np_argwhere0=[numpy.array([int])])

    def test_argwhere1(self):
        self.run_test("def np_argwhere1(x): from numpy import argwhere ; return argwhere(x>8)", numpy.arange(6), np_argwhere1=[numpy.array([int])])

    def test_argwhere2(self):
        self.run_test("def np_argwhere2(x): from numpy import argwhere ; return argwhere(x>0)", numpy.arange(6).reshape(2,3), np_argwhere2=[numpy.array([[int]])])

    def test_around0(self):
        self.run_test("def np_around0(x): from numpy import around ; return around(x)", [0.37, 1.64], np_around0=[[float]])

    def test_around1(self):
        self.run_test("def np_around1(x): from numpy import around ; return around(x, 1)", [0.37, 1.64], np_around1=[[float]])

    def test_around2(self):
        self.run_test("def np_around2(x): from numpy import  around ; return around(x, -1)", [0.37, 1.64], np_around2=[[float]])

    def test_around3(self):
        self.run_test("def np_around3(x): from numpy import around ; return around(x)", [.5, 1.5, 2.5, 3.5, 4.5], np_around3=[[float]])

    def test_around4(self):
        self.run_test("def np_around4(x): from numpy import around ; return around(x,1)", [1,2,3,11], np_around4=[[int]])

    def test_around5(self):
        self.run_test("def np_around5(x): from numpy import around ; return around(x,-1)", [1,2,3,11], np_around5=[[int]])

    def test_argsort0(self):
        self.run_test("def np_argsort0(x): from numpy import argsort ; return argsort(x)", numpy.array([3, 1, 2]), np_argsort0=[numpy.array([int])])

    def test_argsort1(self):
        self.run_test("def np_argsort1(x): from numpy import argsort ; return argsort(x)", numpy.array([[3, 1, 2], [1 , 2, 3]]), np_argsort1=[numpy.array([[int]])])

    def test_argmax0(self):
        self.run_test("def np_argmax0(a): from numpy import argmax ; return argmax(a)", numpy.arange(6).reshape(2,3), np_argmax0=[numpy.array([[int]])])

    def test_argmax1(self):
        self.run_test("def np_argmax1(a): from numpy import argmax ; return argmax(a+a)", numpy.arange(6).reshape(2,3), np_argmax1=[numpy.array([[int]])])

    def test_argmin0(self):
        self.run_test("def np_argmin0(a): from numpy import argmin ; return argmin(a)", numpy.arange(6).reshape(2,3), np_argmin0=[numpy.array([[int]])])

    def test_argmin1(self):
        self.run_test("def np_argmin1(a): from numpy import argmin ; return argmin(a)", [1,2,3], np_argmin1=[[int]])

    def test_append0(self):
        self.run_test("def np_append0(a): from numpy import append ; b = [[4, 5, 6], [7, 8, 9]] ; return append(a,b)", [1, 2, 3], np_append0=[[int]])

    def test_append1(self):
        self.run_test("def np_append1(a): from numpy import append,array ; b = array([[4, 5, 6], [7, 8, 9]]) ; return append(a,b)", [1, 2, 3], np_append1=[[int]])

    def test_append2(self):
        self.run_test("def np_append2(a): from numpy import append,array ; b = array([[4, 5, 6], [7, 8, 9]]) ; return append(a,b)", numpy.array([1, 2, 3]), np_append2=[numpy.array([int])])

    def test_angle0(self):
        self.run_test("def np_angle0(a): from numpy import angle ; return angle(a)", [1.0, 1.0j, 1+1j], np_angle0=[[complex]])

    def test_angle1(self):
        self.run_test("def np_angle1(a): from numpy import angle ; return angle(a)", numpy.array([1.0, 1.0j, 1+1j]), np_angle1=[numpy.array([complex])])

    def test_angle2(self):
        self.run_test("def np_angle2(a): from numpy import angle ; return angle(a,True)", 1 + 1j, np_angle2=[complex])

    def test_angle3(self):
        self.run_test("def np_angle3(a): from numpy import angle ; return angle(a,True)", 1, np_angle3=[int])

    def test_any0(self):
        self.run_test("def np_any0(a): from numpy import any ; return any(a)", numpy.array([[True, False], [True, True]]), np_any0=[numpy.array([[bool]])])

    def test_any1(self):
        self.run_test("def np_any1(a): from numpy import any ;  return any(a, 0)", numpy.array([[True, False], [False, False]]), np_any1=[numpy.array([[bool]])])

    def test_any2(self):
        self.run_test("def np_any2(a): from numpy import any ; return any(a)", [-1, 0, 5], np_any2=[[int]])

    def test_array1D_(self):
        self.run_test("def np_array1D_(a):\n from numpy import array\n return array(a)", [1,2,3], np_array1D_=[[int]])

    def test_array2D_(self):
        self.run_test("def np_array2D_(a):\n from numpy import array\n return array(a)", [[1,2],[3,4]], np_array2D_=[[[int]]])

    def test_array_typed(self):
        self.run_test("def np_array_typed(a):\n from numpy import array, int64\n return array(a, int64)", [1.,2.,3.], np_array_typed=[[float]])

    def test_zeros_(self):
        self.run_test("def np_zeros_(a): from numpy import zeros; return zeros(a)", (10, 5), np_zeros_=[(int, int)])

    def test_ones_(self):
        self.run_test("def np_ones_(a): from numpy import ones; return ones(a)", (10, 5), np_ones_=[(int, int)])

    def test_flat_zeros_(self):
        self.run_test("def np_flat_zeros_(a): from numpy import zeros; return zeros(a)", 10, np_flat_zeros_=[int])

    def test_flat_ones_(self):
        self.run_test("def np_flat_ones_(a): from numpy import ones; return ones(a)", 5, np_flat_ones_=[int])

    def test_acces1D_(self):
        self.run_test("def np_acces1D_(a): return a[1]", numpy.array([1,2,3]), np_acces1D_=[numpy.array([int])])

    def test_accesSimple_(self):
        self.run_test("def np_accesSimple_(a): return a[1]", numpy.array([[1,2],[3,4]]), np_accesSimple_=[numpy.array([[int]])])

    def test_accesMultiple_(self):
        self.run_test("def np_accesMultiple_(a): return a[1,0]", numpy.array([[1,2],[3,4]]), np_accesMultiple_=[numpy.array([[int]])])

    def test_accesMultipleND_(self):
        self.run_test("def np_accesMultipleND_(a): return a[1,0]", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_accesMultipleND_=[numpy.array([[[int]]])])

    def test_accesMultipleNDSplit_(self):
        self.run_test("def np_accesMultipleNDSplit_(a): return a[1][0]", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_accesMultipleNDSplit_=[numpy.array([[[int]]])])

    def test_shape_(self):
        self.run_test("def np_shape_(a): return a.shape", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_shape_=[numpy.array([[[int]]])])

    def test_input_array_(self):
        self.run_test("import numpy\n\ndef input_array_(a):\n return a.shape", runas="import numpy; input_array_(numpy.array([[1,2],[3,4]]))", input_array_=[numpy.array([[int]])])

    def test_change_array1D_(self):
        self.run_test("def np_change_array1D_(a):\n a[0,0,0] = 36\n return a", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_change_array1D_=[numpy.array([[[int]]])])

    def test_change_arrayND_(self):
        self.run_test("def np_change_arrayND_(a):\n from numpy import array\n a[0,0] = array([99,99])\n return a", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_change_arrayND_=[numpy.array([[[int]]])])

    def test_ndim_(self):
        self.run_test("def np_ndim_(a): return a.ndim", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_ndim_=[numpy.array([[[int]]])])

    def test_stride_(self):
        self.run_test("def np_stride_(a): return a.strides", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_stride_=[numpy.array([[[int]]])])

    def test_size_(self):
        self.run_test("def np_size_(a): return a.size", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_size_=[numpy.array([[[int]]])])

    def test_itemsize_(self):
        self.run_test("def np_itemsize_(a): return a.itemsize", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_itemsize_=[numpy.array([[[int]]])])

    def test_nbytes_(self):
        self.run_test("def np_nbytes_(a): return a.nbytes", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_nbytes_=[numpy.array([[[int]]])])

    def test_flat_(self):
        self.run_test("def np_flat_(a): return [i for i in a.flat]", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_flat_=[numpy.array([[[int]]])])

    def test_str_(self):
        self.run_test("def np_str_(a): return str(a)", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_str_=[numpy.array([[[int]]])])

    def test_len_(self):
        self.run_test("def np_len_(a): return len(a)", numpy.array([[[1,2],[3,4]],[[5,6],[7,8]]]), np_len_=[numpy.array([[[int]]])])

    def test_empty_(self):
        self.run_test("def np_empty_(a):\n from numpy import empty\n a = empty(a)\n return a.strides, len(a)", (3, 2), np_empty_=[(int, int)])

    def test_arange(self):
        self.run_test("def np_arange_(a):\n from numpy import arange\n return arange(a)", 10, np_arange_=[int])

    def test_arange1(self):
        self.run_test("def np_arange1_(a):\n from numpy import arange\n return arange(a, 10)", 1, np_arange1_=[int])

    def test_arange2(self):
        self.run_test("def np_arange2_(a):\n from numpy import arange\n return arange(a, 10)", 0.5, np_arange2_=[float])

    def test_arange3(self):
        self.run_test("def np_arange3_(a):\n from numpy import arange\n return arange(a, 9.5)", 0.5, np_arange3_=[float])

    def test_arange4(self):
        self.run_test("def np_arange4_(a):\n from numpy import arange\n return arange(a, 9.3, 1)", 0.2, np_arange4_=[float])

    def test_arange5(self):
        self.run_test("def np_arange5_(a):\n from numpy import arange\n return arange(a, 2, 0.3)", 1, np_arange5_=[int])

    def test_arange6(self):
        self.run_test("def np_arange6_(a):\n from numpy import arange\n return arange(a, 3.3, 0.5)", 0.2, np_arange6_=[float])

    def test_arange7(self):
        self.run_test("def np_arange7_(a):\n from numpy import arange\n return arange(a, 4.5, -0.2)", 1, np_arange7_=[int])

    def test_arange8(self):
        self.run_test("def np_arange8_(a):\n from numpy import arange\n return arange(a, 1, -0.1)", 4.5, np_arange8_=[float])

    def test_arange9(self):
        self.run_test("def np_arange9_(a):\n from numpy import arange\n return arange(a, -12, -3.2)", 4.5, np_arange9_=[float])

    def test_arange10(self):
        self.run_test("def np_arange10_(a):\n from numpy import arange\n return arange(a, -5.5, -0.1)", -5, np_arange10_=[int])

    def test_arange11(self):
        self.run_test("def np_arange11_(a):\n from numpy import arange, uint8\n return arange(a, 255, 1, uint8)", 0, np_arange11_=[int])

    def test_arange12(self):
        self.run_test("def np_arange12_(a):\n from numpy import arange, float32\n return arange(a, 25, 1., float32)", 0, np_arange12_=[int])

    def test_linspace(self):
        self.run_test("def np_linspace_(a):\n from numpy import linspace\n return linspace(a,4,32)", 1, np_linspace_=[int])

    def test_linspace1(self):
        self.run_test("def np_linspace1_(a):\n from numpy import linspace\n return linspace(a,32.5,2)", 0.4, np_linspace1_=[float])

    def test_linspace2(self):
        self.run_test("def np_linspace2_(a):\n from numpy import linspace\n return linspace(a,32.5,32, False)", 0.4, np_linspace2_=[float])

    def test_linspace3(self):
        self.run_test("def np_linspace3_(a):\n from numpy import linspace\n return linspace(1,a)", 4, np_linspace3_=[int])

    def test_sin(self):
        self.run_test("def np_sin_(a):\n from numpy import sin\n return sin(a)", numpy.linspace(0,6), np_sin_=[numpy.array([float])])

    def test_pi(self):
        self.run_test("def np_pi_():\n from numpy import pi\n return pi", np_pi_=[])

    def test_e(self):
        self.run_test("def np_e_():\n from numpy import e\n return e", np_e_=[])

    def test_ones_like_(self):
        self.run_test("def np_ones_like_(a):\n from numpy import ones_like, array\n return ones_like(array(a))", [[i,j,k,l] for i in xrange(5) for j in xrange(4) for k in xrange(6) for l in xrange(8)], np_ones_like_=[[[int]]])

    def test_zeros_like_(self):
        self.run_test("def np_zeros_like_(a):\n from numpy import zeros_like, array\n return zeros_like(array(a))", [[i,j,k,l] for i in xrange(5) for j in xrange(4) for k in xrange(6) for l in xrange(8)], np_zeros_like_=[[[int]]])

    def test_empty_like_(self):
        self.run_test("def np_empty_like_(a):\n from numpy import empty_like, array\n return empty_like(array(a)).shape", [[i,j,k,l] for i in xrange(5) for j in xrange(4) for k in xrange(6) for l in xrange(8)], np_empty_like_=[[[int]]])

    def test_reshape_(self):
        self.run_test("def np_reshape_(a): return a.reshape(2,5)", numpy.arange(10), np_reshape_=[numpy.array([int])], check_refcount=True)

    def test_duplicate(self):
        self.run_test("def np_duplicate(a): return a, a", numpy.arange(10), np_duplicate=[numpy.array([int])], check_refcount=True)

    def test_broadcast(self):
        self.run_test("def np_broadcast(): import numpy; a = numpy.arange(3); return a, a", np_broadcast=[], check_refcount=True)

    def test_broadcast_dup(self):
        self.run_test("def np_broadcast_dup(): import numpy; a = numpy.arange(10); return a, a.reshape(2,5)", np_broadcast_dup=[], check_refcount=True)

    def test_reshape_expr(self):
        self.run_test("def np_reshape_expr(a): return (a + a).reshape(2,5)", numpy.ones(10), np_reshape_expr=[numpy.array([float])])

    def test_cumsum_(self):
        self.run_test("def np_cumsum_(a): return a.cumsum()", numpy.arange(10), np_cumsum_=[numpy.array([int])])

    def test_cumsum2_(self):
        self.run_test("def np_cumsum2_(a): return a.cumsum()", numpy.arange(10).reshape(2,5), np_cumsum2_=[numpy.array([[int]])])

    def test_cumsum3_(self):
        self.run_test("def np_cumsum3_(a): return a.cumsum(1)", numpy.arange(10).reshape(2,5), np_cumsum3_=[numpy.array([[int]])])

    def test_cumsum4_(self):
        self.run_test("def np_cumsum4_(a): return a.cumsum(0)", numpy.arange(10).reshape(2,5), np_cumsum4_=[numpy.array([[int]])])

    def test_cumsum5_(self):
        self.run_test("def np_cumsum5_(a): return a.cumsum(0)", numpy.arange(10), np_cumsum5_=[numpy.array([int])])

    def test_sum_(self):
        self.run_test("def np_sum_(a): return a.sum()", numpy.arange(10), np_sum_=[numpy.array([int])])

    def test_sum_bool(self):
        self.run_test("def np_sum_bool(a): return (a > 2).sum()", numpy.arange(10), np_sum_bool=[numpy.array([int])])

    def test_sum_bool2(self):
        self.run_test("def np_sum_bool2(a): return a.sum()", numpy.ones(10,dtype=bool).reshape(2,5), np_sum_bool2=[numpy.array([[bool]])])

    def test_sum_expr(self):
        self.run_test("def np_sum_expr(a):\n from numpy import ones\n return (a + ones(10)).sum()", numpy.arange(10), np_sum_expr=[numpy.array([int])])

    def test_sum2_(self):
        self.run_test("def np_sum2_(a): return a.sum()", numpy.arange(10).reshape(2,5), np_sum2_=[numpy.array([[int]])])

    def test_sum3_(self):
        self.run_test("def np_sum3_(a): return a.sum(1)", numpy.arange(10).reshape(2,5), np_sum3_=[numpy.array([[int]])])

    def test_sum4_(self):
        self.run_test("def np_sum4_(a): return a.sum(0)", numpy.arange(10).reshape(2,5), np_sum4_=[numpy.array([[int]])])

    def test_sum5_(self):
        self.run_test("def np_sum5_(a): return a.sum(0)", numpy.arange(10), np_sum5_=[numpy.array([int])])

    def test_amin_amax(self):
        self.run_test("def np_amin_amax(a):\n from numpy import amin,amax\n return amin(a), amax(a)",numpy.arange(10),  np_amin_amax=[numpy.array([int])])

    def test_min_(self):
        self.run_test("def np_min_(a): return a.min()", numpy.arange(10), np_min_=[numpy.array([int])])

    def test_min2_(self):
        self.run_test("def np_min2_(a): return a.min()", numpy.arange(10).reshape(2,5), np_min2_=[numpy.array([[int]])])

    def test_min3_(self):
        self.run_test("def np_min3_(a): return a.min(1)", numpy.arange(10).reshape(2,5), np_min3_=[numpy.array([[int]])])

    def test_min4_(self):
        self.run_test("def np_min4_(a): return a.min(0)", numpy.arange(10).reshape(2,5), np_min4_=[numpy.array([[int]])])

    def test_min5_(self):
        self.run_test("def np_min5_(a): return a.min(0)", numpy.arange(10), np_min5_=[numpy.array([int])])

    def test_max_(self):
        self.run_test("def np_max_(a): return a.max()", numpy.arange(10), np_max_=[numpy.array([int])])

    def test_max2_(self):
        self.run_test("def np_max2_(a): return a.max()", numpy.arange(10).reshape(2,5), np_max2_=[numpy.array([[int]])])

    def test_max3_(self):
        self.run_test("def np_max3_(a): return a.max(1)", numpy.arange(10).reshape(2,5), np_max3_=[numpy.array([[int]])])

    def test_max4_(self):
        self.run_test("def np_max4_(a): return a.max(0)", numpy.arange(10).reshape(2,5), np_max4_=[numpy.array([[int]])])

    def test_max5_(self):
        self.run_test("def np_max5_(a): return a.max(0)", numpy.arange(10), np_max5_=[numpy.array([int])])

    def test_all_(self):
        self.run_test("def np_all_(a): return a.all()", numpy.arange(10), np_all_=[numpy.array([int])])

    def test_all2_(self):
        self.run_test("def np_all2_(a): return a.all()", numpy.ones(10).reshape(2,5), np_all2_=[numpy.array([[float]])])

    def test_all3_(self):
        self.run_test("def np_all3_(a): return a.all(1)", numpy.arange(10).reshape(2,5), np_all3_=[numpy.array([[int]])])

    def test_all4_(self):
        self.run_test("def np_all4_(a): return a.all(0)", numpy.ones(10).reshape(2,5), np_all4_=[numpy.array([[float]])])

    def test_all5_(self):
        self.run_test("def np_all5_(a): return a.all(0)", numpy.arange(10), np_all5_=[numpy.array([int])])

    def test_transpose_(self):
        self.run_test("def np_transpose_(a): return a.transpose()", numpy.arange(24).reshape(2,3,4), np_transpose_=[numpy.array([[[int]]])])

    def test_transpose_expr(self):
        self.run_test("def np_transpose_expr(a): return (a + a).transpose()", numpy.ones(24).reshape(2,3,4), np_transpose_expr=[numpy.array([[[float]]])])

    def test_transpose2_(self):
        self.run_test("def np_transpose2_(a): return a.transpose((2,0,1))", numpy.arange(24).reshape(2,3,4), np_transpose2_=[numpy.array([[[int]]])])

    def test_add0(self):
        self.run_test("def np_add0(a, b): return a + b", numpy.ones(10), numpy.ones(10), np_add0=[numpy.array([float]), numpy.array([float])])

    def test_add1(self):
        self.run_test("def np_add1(a, b): return a + b + a", numpy.ones(10), numpy.ones(10), np_add1=[numpy.array([float]), numpy.array([float])])

    def test_add2(self):
        self.run_test("def np_add2(a, b): return a + b + 1", numpy.ones(10), numpy.ones(10), np_add2=[numpy.array([float]), numpy.array([float])])

    def test_add3(self):
        self.run_test("def np_add3(a, b): return 1. + a + b + 1.", numpy.ones(10), numpy.ones(10), np_add3=[numpy.array([float]), numpy.array([float])])

    def test_add4(self):
        self.run_test("def np_add4(a, b): return ( a + b ) + ( a + b )", numpy.ones(10), numpy.ones(10), np_add4=[numpy.array([float]), numpy.array([float])])

    def test_add5(self):
        self.run_test("def np_add5(a, b): return (-a) + (-b)", numpy.ones(10), numpy.ones(10), np_add5=[numpy.array([float]), numpy.array([float])])

    def test_sub0(self):
        self.run_test("def np_sub0(a, b): return a - b", numpy.ones(10), numpy.ones(10), np_sub0=[numpy.array([float]), numpy.array([float])])

    def test_sub1(self):
        self.run_test("def np_sub1(a, b): return a - b - a", numpy.ones(10), numpy.ones(10), np_sub1=[numpy.array([float]), numpy.array([float])])

    def test_sub2(self):
        self.run_test("def np_sub2(a, b): return a - b - 1", numpy.ones(10), numpy.ones(10), np_sub2=[numpy.array([float]), numpy.array([float])])

    def test_sub3(self):
        self.run_test("def np_sub3(a, b): return 1. - a - b - 1.", numpy.ones(10), numpy.ones(10), np_sub3=[numpy.array([float]), numpy.array([float])])

    def test_sub4(self):
        self.run_test("def np_sub4(a, b): return ( a - b ) - ( a - b )", numpy.ones(10), numpy.ones(10), np_sub4=[numpy.array([float]), numpy.array([float])])

    def test_addsub0(self):
        self.run_test("def np_addsub0(a, b): return a - b + a", numpy.ones(10), numpy.ones(10), np_addsub0=[numpy.array([float]), numpy.array([float])])

    def test_addsub1(self):
        self.run_test("def np_addsub1(a, b): return a + b - a", numpy.ones(10), numpy.ones(10), np_addsub1=[numpy.array([float]), numpy.array([float])])

    def test_addsub2(self):
        self.run_test("def np_addsub2(a, b): return a + b - 1", numpy.ones(10), numpy.ones(10), np_addsub2=[numpy.array([float]), numpy.array([float])])

    def test_addsub3(self):
        self.run_test("def np_addsub3(a, b): return 1. + a - b + 1.", numpy.ones(10), numpy.ones(10), np_addsub3=[numpy.array([float]), numpy.array([float])])

    def test_addsub4(self):
        self.run_test("def np_addsub4(a, b): return ( a - b ) + ( a + b )", numpy.ones(10), numpy.ones(10), np_addsub4=[numpy.array([float]), numpy.array([float])])

    def test_addcossub0(self):
        self.run_test("def np_addcossub0(a, b): from numpy import cos ; return a - b + cos(a)", numpy.ones(10), numpy.ones(10), np_addcossub0=[numpy.array([float]), numpy.array([float])])

    def test_addcossub1(self):
        self.run_test("def np_addcossub1(a, b): from numpy import cos ; return a + cos(b - a)", numpy.ones(10), numpy.ones(10), np_addcossub1=[numpy.array([float]), numpy.array([float])])

    def test_addcossub2(self):
        self.run_test("def np_addcossub2(a, b): from numpy import cos ; return a + cos(b - 1)", numpy.ones(10), numpy.ones(10), np_addcossub2=[numpy.array([float]), numpy.array([float])])

    def test_addcossub3(self):
        self.run_test("def np_addcossub3(a, b): from numpy import cos ; return cos(1. + a - b + cos(1.))", numpy.ones(10), numpy.ones(10), np_addcossub3=[numpy.array([float]), numpy.array([float])])

    def test_addcossub4(self):
        self.run_test("def np_addcossub4(a, b): from numpy import cos ; return cos( a - b ) + ( a + b )", numpy.ones(10), numpy.ones(10), np_addcossub4=[numpy.array([float]), numpy.array([float])])

    def test_sin0(self):
        self.run_test("def np_sin0(a, b): from numpy import sin ; return sin(a) + b", numpy.ones(10), numpy.ones(10), np_sin0=[numpy.array([float]), numpy.array([float])])

    def test_tan0(self):
        self.run_test("def np_tan0(a, b): from numpy import tan ; return tan(a - b)", numpy.ones(10), numpy.ones(10), np_tan0=[numpy.array([float]), numpy.array([float])])

    def test_arccos0(self):
        self.run_test("def np_arccos0(a, b): from numpy import arccos ; return arccos(a - b) + 1", numpy.ones(10), numpy.ones(10), np_arccos0=[numpy.array([float]), numpy.array([float])])

    def test_arcsin0(self):
        self.run_test("def np_arcsin0(a, b): from numpy import arcsin ; return arcsin(a + b - a + -b) + 1.", numpy.ones(10), numpy.ones(10), np_arcsin0=[numpy.array([float]), numpy.array([float])])

    def test_arctan0(self):
        self.run_test("def np_arctan0(a, b): from numpy import arctan ; return arctan(a -0.5) + a", numpy.ones(10), numpy.ones(10), np_arctan0=[numpy.array([float]), numpy.array([float])])

    def test_arctan20(self):
        self.run_test("def np_arctan20(a, b): from numpy import arctan2 ; return b - arctan2(a , b)", numpy.ones(10), numpy.ones(10), np_arctan20=[numpy.array([float]), numpy.array([float])])

    def test_cos1(self):
        self.run_test("def np_cos1(a): from numpy import cos; return cos(a)", 5, np_cos1=[int])

    def test_sin1(self):
        self.run_test("def np_sin1(a): from numpy import sin; return sin(a)", 0.5, np_sin1=[float])

    def test_tan1(self):
        self.run_test("def np_tan1(a): from numpy import tan; return tan(a)", 0.5, np_tan1=[float])

    def test_arccos1(self):
        self.run_test("def np_arccos1(a): from numpy import arccos ; return arccos(a)", 1, np_arccos1=[int])

    def test_arcsin1(self):
        self.run_test("def np_arcsin1(a): from numpy import arcsin ; return arcsin(a)", 1, np_arcsin1=[int])

    def test_arctan1(self):
        self.run_test("def np_arctan1(a): from numpy import arctan ; return arctan(a)", 0.5, np_arctan1=[float])

    def test_arctan21(self):
        self.run_test("def np_arctan21(a): from numpy import arctan2 ; b = .5 ; return arctan2(a , b)", 1., np_arctan21=[float])

    def test_sliced0(self):
        self.run_test("def np_sliced0(a): return a[2:12]", numpy.ones(20), np_sliced0=[numpy.array([float])])

    def test_sliced1(self):
        self.run_test("def np_sliced1(a): return a[2:12:3]", numpy.ones(20), np_sliced1=[numpy.array([float])])

    def test_sliced2(self):
        self.run_test("def np_sliced2(a): return -a[2:12:3]", numpy.ones(20), np_sliced2=[numpy.array([float])])

    def test_sliced3(self):
        self.run_test("def np_sliced3(a): return a[1:11:3] -a[2:12:3]", numpy.ones(20), np_sliced3=[numpy.array([float])])

    def test_sliced4(self):
        self.run_test("def np_sliced4(a): return a[1:11] -a[2:12]", numpy.ones(20), np_sliced4=[numpy.array([float])])

    def test_sliced5(self):
        self.run_test("def np_sliced5(a): return (-a[1:11]) + 3*a[2:12]", numpy.ones(20), np_sliced5=[numpy.array([float])])

    def test_sliced6(self):
        self.run_test("def np_sliced6(a): return a[3:4]", numpy.arange(12).reshape(6,2), np_sliced6=[numpy.array([[int]])])

    def test_sliced7(self):
        self.run_test("def np_sliced7(a): a[3:4] = 1 ; return a", numpy.arange(12).reshape(6,2), np_sliced7=[numpy.array([[int]])])

    def test_sliced8(self):
        self.run_test("def np_sliced8(a): a[1:2] = 1 ; return a", numpy.arange(12).reshape(3,2,2), np_sliced8=[numpy.array([[[int]]])])

    def test_sliced9(self):
        self.run_test("def np_sliced9(a): from numpy import arange ; a[1:2] = arange(4).reshape(1,2,2) ; return a", numpy.arange(12).reshape(3,2,2), np_sliced9=[numpy.array([[[int]]])])

    def test_sliced10(self):
        self.run_test("def np_sliced10(a): from numpy import arange ; a[1:-1:2] = arange(4).reshape(1,2,2) ; return a", numpy.arange(12).reshape(3,2,2), np_sliced10=[numpy.array([[[int]]])])

    def test_sliced11(self):
        self.run_test("def np_sliced11(a): return a[1::-2]", numpy.arange(12).reshape(3,2,2), np_sliced11=[numpy.array([[[int]]])])

    def test_sliced12(self):
        self.run_test("def np_sliced12(a): return a[1::-2]", numpy.arange(12), np_sliced12=[numpy.array([int])])

    def test_sliced13(self):
        self.run_test("def np_sliced13(a): return a[3::-3]", numpy.arange(11), np_sliced13=[numpy.array([int])])

    def test_alen0(self):
        self.run_test("def np_alen0(a): from numpy import alen ; return alen(a)", numpy.ones((5,6)), np_alen0=[numpy.array([[float]])])

    def test_alen1(self):
        self.run_test("def np_alen1(a): from numpy import alen ; return alen(-a)", numpy.ones((5,6)), np_alen1=[numpy.array([[float]])])

    def test_allclose0(self):
        self.run_test("def np_allclose0(a): from numpy import allclose ; return allclose([1e10,1e-7], a)", [1.00001e10,1e-8], np_allclose0=[[float]])

    def test_allclose1(self):
        self.run_test("def np_allclose1(a): from numpy import allclose; return allclose([1e10,1e-8], +a)", numpy.array([1.00001e10,1e-9]), np_allclose1=[numpy.array([float])])

    def test_allclose2(self):
        self.run_test("def np_allclose2(a): from numpy import array, allclose; return allclose(array([1e10,1e-8]), a)", numpy.array([1.00001e10,1e-9]), np_allclose2=[numpy.array([float])])

    def test_allclose3(self):
        self.run_test("def np_allclose3(a): from numpy import allclose; return allclose(a, a)", [1.0, numpy.nan], np_allclose3=[[float]])

    def test_alltrue0(self):
        self.run_test("def np_alltrue0(b): from numpy import alltrue ; return alltrue(b)", numpy.array([True, False, True, True]), np_alltrue0=[numpy.array([bool])])

    def test_alltrue1(self):
        self.run_test("def np_alltrue1(a): from numpy import alltrue ; return alltrue(a >= 5)", numpy.array([1, 5, 2, 7]), np_alltrue1=[numpy.array([int])])

    def test_negative_mod(self):
        self.run_test("def np_negative_mod(a): return a % 5", numpy.array([-1, -5, -2, 7]), np_negative_mod=[numpy.array([int])])


# automatic generation of basic test cases for ufunc
binary_ufunc = (
        'add','arctan2',
        'bitwise_and', 'bitwise_or', 'bitwise_xor',
        'copysign',
        'divide',
        'equal',
        'floor_divide', 'fmax', 'fmin', 'fmod',
        'greater', 'greater_equal',
        'hypot',
        'ldexp', 'left_shift', 'less', 'less_equal', 'logaddexp', 'logaddexp2', "logical_and", "logical_or", "logical_xor",
        'maximum', 'minimum', 'mod','multiply',
        'nextafter','not_equal',
        'power',
        'remainder','right_shift',
        'subtract',
        'true_divide',
        )

unary_ufunc = (
        'abs', 'absolute', 'arccos', 'arccosh', 'arcsin', 'arcsinh', 'arctan', 'arctanh',
        'bitwise_not',
        'ceil', 'conj', 'conjugate', 'cos', 'cosh',
        'deg2rad', 'degrees',
        'exp', 'expm1',
        'fabs', 'floor',
        'isinf', 'isneginf', 'isposinf', 'isnan', 'invert', 'isfinite',
        'log', 'log10', 'log1p', 'log2', 'logical_not',
        'negative',
        'rad2deg', 'radians','reciprocal', 'rint', 'round', 'round_',
        'sign', 'signbit',
         'sin', 'sinh', 'spacing', 'sqrt', 'square',
        'tan', 'tanh','trunc',
        )

for f in unary_ufunc:
    if 'bitwise_' in f or 'invert' in f:
        setattr(TestNumpy, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(a): from numpy import {0} ; return {0}(a)', numpy.ones(10, numpy.int32), np_{0}=[numpy.array([numpy.int32])])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_scalar', eval("lambda self: self.run_test('def np_{0}_scalar(a): from numpy import {0} ; return {0}(a)', 1, np_{0}_scalar=[int])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_matrix', eval("lambda self: self.run_test('def np_{0}_matrix(a): from numpy import {0} ; return {0}(a)', numpy.ones((5,2), numpy.int32), np_{0}_matrix=[numpy.array([numpy.array([numpy.int32])])])".format(f)))
    else:
        setattr(TestNumpy, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(a): from numpy import {0} ; return {0}(a)', numpy.ones(10), np_{0}=[numpy.array([float])])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_scalar', eval("lambda self: self.run_test('def np_{0}_scalar(a): from numpy import {0} ; return {0}(a+0.5)', 0.5, np_{0}_scalar=[float])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_matrix', eval("lambda self: self.run_test('def np_{0}_matrix(a): from numpy import {0} ; return {0}(a)', numpy.ones((2,5)), np_{0}_matrix=[numpy.array([numpy.array([float])])])".format(f)))

for f in binary_ufunc:
    if 'bitwise_' in f or 'ldexp' in f or '_shift' in f :
        setattr(TestNumpy, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(a): from numpy import {0} ; return {0}(a,a)', numpy.ones(10, numpy.int32), np_{0}=[numpy.array([numpy.int32])])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_scalar', eval("lambda self: self.run_test('def np_{0}_scalar(a): from numpy import {0} ; return {0}(a, a-1)', 1, np_{0}_scalar=[int])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_matrix', eval("lambda self: self.run_test('def np_{0}_matrix(a): from numpy import {0} ; return {0}(a,a)', numpy.ones((2,5), numpy.int32), np_{0}_matrix=[numpy.array([numpy.array([numpy.int32])])])".format(f)))
    else:
        setattr(TestNumpy, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(a): from numpy import {0} ; return {0}(a,a)', numpy.ones(10), np_{0}=[numpy.array([float])])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_scalar', eval("lambda self: self.run_test('def np_{0}_scalar(a): from numpy import {0} ; return {0}(a+0.5, a+0.5)', 0.5, np_{0}_scalar=[float])".format(f)))
        setattr(TestNumpy, 'test_' + f + '_matrix', eval("lambda self: self.run_test('def np_{0}_matrix(a): from numpy import {0} ; return {0}(a,a)', numpy.ones((2,5)) - 0.2 , np_{0}_matrix=[numpy.array([numpy.array([float])])])".format(f)))

########NEW FILE########
__FILENAME__ = test_openmp
import unittest
from test_env import TestFromDir
import os
import pythran

class TestOpenMP(TestFromDir):
    path = os.path.join(os.path.dirname(__file__),"openmp")

class TestOpenMPLegacy(TestFromDir):
    '''
    Test old style OpenMP constructs, not using comments but strings
    and relying on function-scope locals
    '''
    path = os.path.join(os.path.dirname(__file__),"openmp.legacy")

    @staticmethod
    def interface(name, file=None):
        return { name: [] }

# only activate OpenMP tests if the underlying compiler supports OpenMP
try:
    pythran.compile_cxxcode('#include <omp.h>', cxxflags=['-fopenmp'])
    TestOpenMP.populate(TestOpenMP)
    TestOpenMPLegacy.populate(TestOpenMPLegacy)
except pythran.CompileError:
    pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_operator
import unittest
from test_env import TestEnv

class TestOperator(TestEnv):

    def test_lt(self):
        self.run_test("def lt(a,b):\n from operator import lt\n return lt(a,b)", 1, 2, lt=[int,int])

    def test_le(self):
        self.run_test("def le(a,b):\n from operator import le\n return le(a,b)", 1, 2, le=[int,int])

    def test_eq(self):
        self.run_test("def eq(a,b):\n from operator import eq\n return eq(a,b)", 2, 2, eq=[int,int])

    def test_ne(self):
        self.run_test("def ne(a,b):\n from operator import ne\n return ne(a,b)", 2, 2, ne=[int,int])

    def test_ge(self):
        self.run_test("def ge(a,b):\n from operator import ge\n return ge(a,b)", 2, 2, ge=[int,int])

    def test_gt(self):
        self.run_test("def gt(a,b):\n from operator import gt\n return gt(a,b)", 2, 2, gt=[int,int])

    def test___lt__(self):
        self.run_test("def __lt__(a,b):\n from operator import __lt__\n return __lt__(a,b)", 2, 2, __lt__=[int,int])

    def test___le__(self):
        self.run_test("def __le__(a,b):\n from operator import __le__\n return __le__(a,b)", 2, 2, __le__=[int,int])

    def test___eq__(self):
        self.run_test("def __eq__(a,b):\n from operator import __eq__\n return __eq__(a,b)", 2, 2, __eq__=[int,int])

    def test___ne__(self):
        self.run_test("def __ne__(a,b):\n from operator import __ne__\n return __ne__(a,b)", 2, 2, __ne__=[int,int])

    def test___ge__(self):
        self.run_test("def __ge__(a,b):\n from operator import __ge__\n return __ge__(a,b)", 2, 2, __ge__=[int,int])

    def test___gt__(self):
        self.run_test("def __gt__(a,b):\n from operator import __gt__\n return __gt__(a,b)", 2, 2, __gt__=[int,int])

    def test_not_(self):
        self.run_test("def not_(a):\n from operator import not_\n return not_(a)", True, not_=[bool])

    def test___not__(self):
        self.run_test("def __not__(a):\n from operator import __not__\n return __not__(a)", True, __not__=[bool])

    def test_truth(self):
        self.run_test("def truth(a):\n from operator import truth\n return truth(a)", True, truth=[bool])

    def test_is_(self):
        self.run_test("def is_(a,b):\n from operator import is_\n return is_(a,b)", 2, 2, is_=[int,int])

    def test_is_not(self):
        self.run_test("def is_not(a,b):\n from operator import is_not\n return is_not(a,b)", 1, 2, is_not=[int,int])

    def test___abs__(self):
        self.run_test("def __abs__(a):\n from operator import __abs__\n return __abs__(a)", -2, __abs__=[int])

    def test__add_(self):
        self.run_test("def add(a,b):\n from operator import add\n return add(a,b)", -1, 2, add=[int,int])

    def test___add__(self):
        self.run_test("def __add__(a,b):\n from operator import __add__\n return __add__(a,b)", -1, 2, __add__=[int,int])

    def test_and_(self):
        self.run_test("def and_(a,b):\n from operator import and_\n return and_(a,b)", 0x01, 0x02, and_=[int,int])

    def test___and__(self):
        self.run_test("def __and__(a,b):\n from operator import __and__\n return __and__(a,b)", 0x01, 0x02, __and__=[int,int])

    def test_div(self):
        self.run_test("def div(a,b):\n from operator import div\n return div(a,b)", 5, 2, div=[int,int])

    def test___div__(self):
        self.run_test("def __div__(a,b):\n from operator import __div__\n return __div__(a,b)", 5, 2, __div__=[int,int])

    def test_floordiv(self):
        self.run_test("def floordiv(a,b):\n from operator import floordiv\n return floordiv(a,b)", 5, 2, floordiv=[int,int])

    def test___floordiv__(self):
        self.run_test("def __floordiv__(a,b):\n from operator import __floordiv__\n return __floordiv__(a,b)", 5, 2, __floordiv__=[int,int])

    def test_inv(self):
        self.run_test("def inv(a):\n from operator import inv\n return inv(a)", 0x02, inv=[int])

    def test_invert(self):
        self.run_test("def invert(a):\n from operator import invert\n return invert(a)", 0x02, invert=[int])

    def test___inv__(self):
        self.run_test("def __inv__(a):\n from operator import __inv__\n return __inv__(a)", 0x02, __inv__=[int])

    def test___invert__(self):
        self.run_test("def __invert__(a):\n from operator import __invert__\n return __invert__(a)", 0x02, __invert__=[int])

    def test_lshift(self):
        self.run_test("def lshift(a,b):\n from operator import lshift\n return lshift(a,b)", 0x02, 1, lshift=[int,int])

    def test___lshift__(self):
        self.run_test("def __lshift__(a,b):\n from operator import __lshift__\n return __lshift__(a,b)",0x02 , 1, __lshift__=[int,int])

    def test_mod(self):
        self.run_test("def mod(a,b):\n from operator import mod\n return mod(a,b)", 5, 2, mod=[int,int])

    def test___mod__(self):
        self.run_test("def __mod__(a,b):\n from operator import __mod__\n return __mod__(a,b)", 5, 2, __mod__=[int,int])

    def test_mul(self):
        self.run_test("def mul(a,b):\n from operator import mul\n return mul(a,b)", 5, 2, mul=[int,int])

    def test___mul__(self):
        self.run_test("def __mul__(a,b):\n from operator import __mul__\n return __mul__(a,b)", 5, 2, __mul__=[int,int])

    def test_neg(self):
        self.run_test("def neg(a):\n from operator import neg\n return neg(a)", 1, neg=[int])

    def test___neg__(self):
        self.run_test("def __neg__(a):\n from operator import __neg__\n return __neg__(a)", 1, __neg__=[int])

    def test_or_(self):
        self.run_test("def or_(a,b):\n from operator import or_\n return or_(a,b)", 0x02, 0x01, or_=[int,int])

    def test___or__(self):
        self.run_test("def __or__(a,b):\n from operator import __or__\n return __or__(a,b)", 0x02, 0x01, __or__=[int,int])

    def test_pos(self):
        self.run_test("def pos(a):\n from operator import pos\n return pos(a)", 2, pos=[int])

    def test___pos__(self):
        self.run_test("def __pos__(a):\n from operator import __pos__\n return __pos__(a)", 2, __pos__=[int])

    def test_rshift(self):
        self.run_test("def rshift(a,b):\n from operator import rshift\n return rshift(a,b)", 0x02, 1, rshift=[int,int])

    def test___rshift__(self):
        self.run_test("def __rshift__(a,b):\n from operator import __rshift__\n return __rshift__(a,b)", 0x02, 1, __rshift__=[int,int])

    def test_sub(self):
        self.run_test("def sub(a,b):\n from operator import sub\n return sub(a,b)", 5, 2, sub=[int,int])

    def test___sub__(self):
        self.run_test("def __sub__(a,b):\n from operator import __sub__\n return __sub__(a,b)", 5, 2, __sub__=[int,int])

    def test_truediv(self):
        self.run_test("def truediv(a,b):\n from operator import truediv\n return truediv(a,b)", 5, 2, truediv=[int,int])

    def test___truediv__(self):
        self.run_test("def __truediv__(a,b):\n from operator import __truediv__\n return __truediv__(a,b)", 5, 2, __truediv__=[int,int])

    def test___xor__(self):
        self.run_test("def __xor__(a,b):\n from operator import __xor__\n return __xor__(a,b)", 0x02, 0x01, __xor__=[int,int])

    def test_iadd(self):
        self.run_test("def iadd(a,b):\n from operator import iadd\n return iadd(a,b)", -1, 3, iadd=[int,int])

    def test_iadd_argument_modification_not_mutable(self):
        self.run_test("def iadd2(b):\n a = -1\n from operator import iadd\n iadd(a,b)\n return a", 3, iadd2=[int])

    def test_iadd_argument_modification_mutable(self):
        self.run_test("def iadd3(b):\n a = []\n from operator import iadd\n iadd(a,b)\n return a", [3], iadd3=[[int]])

    def test_iadd_argument_modification_mutable2(self):
        self.run_test("def iadd4(b):\n from operator import iadd\n return iadd([],b)", [3], iadd4=[[int]])

    def test___iadd__(self):
        self.run_test("def __iadd__(a,b):\n from operator import __iadd__\n return __iadd__(a,b)", 1, -4, __iadd__=[int,int])

    def test___iadd___argument_modification_not_mutable(self):
        self.run_test("def __iadd2__(b):\n a = -1\n from operator import __iadd__\n __iadd__(a,b)\n return a", 3, __iadd2__=[int])

    def test___iadd___argument_modification_mutable(self):
        self.run_test("def __iadd3__(b):\n a = []\n from operator import __iadd__\n __iadd__(a,b)\n return a", [3], __iadd3__=[[int]])

    def test___iadd___argument_modification_mutable2(self):
        self.run_test("def __iadd4__(b):\n from operator import __iadd__\n return __iadd__([],b)", [3], __iadd4__=[[int]])


    def test_iand(self):
        self.run_test("def iand(a,b):\n from operator import iand\n return iand(a,b)", 0x01, 0x11, iand=[int,int])

    def test_iand2(self):
        self.run_test("def iand2(b):\n from operator import iand\n a=0x01\n return iand(a,b)", 0x11, iand2=[int])

    def test_iand3(self):
        self.run_test("def iand3(b):\n from operator import iand\n a=0x01\n iand(a,b)\n return a", 0x11, iand3=[int])

    def test___iand__(self):
        self.run_test("def __iand__(a,b):\n from operator import __iand__\n return __iand__(a,b)", 0x10, 0xFF, __iand__=[int,int])

    def test_iconcat(self):
        self.run_test("def iconcat(a,b):\n from operator import iconcat\n return iconcat(a,b)", [3], [4], iconcat=[[int],[int]])

    def test_iconcat2(self):
        self.run_test("def iconcat2(b):\n from operator import iconcat\n a=[3]\n return iconcat(a,b)", [4], iconcat2=[[int]])

    def test_iconcat3(self):
        self.run_test("def iconcat3(b):\n from operator import iconcat\n a=[3]\n iconcat(a,b)\n return a", [4], iconcat3=[[int]])

    def test_iconcat4(self):
        self.run_test("def iconcat4(b):\n from operator import iconcat\n a=[]\n iconcat(a,b)\n return a", [4], iconcat4=[[int]])

    def test_iconcat5(self):
        self.run_test("def iconcat5(b):\n from operator import iconcat\n return iconcat([],b)", [4], iconcat5=[[int]])

    def test___iconcat__(self):
        self.run_test("def __iconcat__(a,b):\n from operator import __iconcat__\n return __iconcat__(a,b)", [3], [4], __iconcat__=[[int],[int]])

    def test_idiv(self):
        self.run_test("def idiv(a,b):\n from operator import idiv\n return idiv(a,b)", 5, 2, idiv=[int,int])

    def test_idiv2(self):
        self.run_test("def idiv2(b):\n from operator import idiv\n a=5\n return idiv(a,b)", 2, idiv2=[int])

    def test_idiv3(self):
        self.run_test("def idiv3(b):\n from operator import idiv\n a=5\n idiv(a,b)\n return a", 2, idiv3=[int])

    def test___idiv__(self):
        self.run_test("def __idiv__(a,b):\n from operator import __idiv__\n return __idiv__(a,b)", 5, 2, __idiv__=[int,int])

    def test_ifloordiv(self):
        self.run_test("def ifloordiv(a,b):\n from operator import ifloordiv\n return ifloordiv(a,b)", 5, 2, ifloordiv=[int,int])

    def test___ifloordiv__(self):
        self.run_test("def __ifloordiv__(a,b):\n from operator import __ifloordiv__\n return __ifloordiv__(a,b)", 5, 2, __ifloordiv__=[int,int])

    def test_ilshift(self):
        self.run_test("def ilshift(a,b):\n from operator import ilshift\n return ilshift(a,b)", 0x02, 3, ilshift=[int,int])

    def test___ilshift__(self):
        self.run_test("def __ilshift__(a,b):\n from operator import __ilshift__\n return __ilshift__(a,b)", 0x02, 3, __ilshift__=[int,int])

    def test_imod(self):
        self.run_test("def imod(a,b):\n from operator import imod\n return imod(a,b)", 4, 2, imod=[int,int])

    def test___imod__(self):
        self.run_test("def __imod__(a,b):\n from operator import __imod__\n return __imod__(a,b)", 5, 3, __imod__=[int,int])

    def test_imul(self):
        self.run_test("def imul(a,b):\n from operator import imul\n return imul(a,b)", 5, -1, imul=[int,int])

    def test___imul__(self):
        self.run_test("def __imul__(a,b):\n from operator import __imul__\n return __imul__(a,b)", -6.1, -2, __imul__=[float,int])

    def test_ior(self):
        self.run_test("def ior(a,b):\n from operator import ior\n return ior(a,b)", 0x02, 0x01, ior=[int,int])

    def test___ior__(self):
        self.run_test("def __ior__(a,b):\n from operator import __ior__\n return __ior__(a,b)", 0x02, 0x02, __ior__=[int,int])

    def test_ipow(self):
        self.run_test("def ipow(a,b):\n from operator import ipow\n return ipow(a,b)", 5, 5, ipow=[int,int])

    def test___ipow__(self):
        self.run_test("def __ipow__(a,b):\n from operator import __ipow__\n return __ipow__(a,b)", 2, 8, __ipow__=[int,int])

    def test_irshift(self):
        self.run_test("def irshift(a,b):\n from operator import irshift\n return irshift(a,b)", 0x02, 3, irshift=[int,int])

    def test___irshift__(self):
        self.run_test("def __irshift__(a,b):\n from operator import __irshift__\n return __irshift__(a,b)", 0x02, 1, __irshift__=[int,int])

    def test_isub(self):
        self.run_test("def isub(a,b):\n from operator import isub\n return isub(a,b)", 5, -8, isub=[int,int])

    def test___isub__(self):
        self.run_test("def __isub__(a,b):\n from operator import __isub__\n return __isub__(a,b)", -8, 5, __isub__=[int,int])

    def test_itruediv(self):
        self.run_test("def itruediv(a,b):\n from operator import itruediv\n return itruediv(a,b)", 5, 2, itruediv=[int,int])

    def test_itruediv2(self):
        self.run_test("def itruediv2(b):\n from operator import itruediv\n a=5\n return itruediv(a,b)", 2, itruediv2=[int])

    def test_itruediv3(self):
        self.run_test("def itruediv3(b):\n from operator import itruediv\n a=5\n itruediv(a,b)\n return a", 2, itruediv3=[int])

    def test___itruediv__(self):
        self.run_test("def __itruediv__(a,b):\n from operator import __itruediv__\n return __itruediv__(a,b)", 5, 2, __itruediv__=[int,int])

    def test_ixor(self):
        self.run_test("def ixor(a,b):\n from operator import ixor\n return ixor(a,b)", 0x02, 0x01, ixor=[int,int])

    def test___ixor__(self):
        self.run_test("def __ixor__(a,b):\n from operator import __ixor__\n return __ixor__(a,b)", 0x02, 0x02, __ixor__=[int,int])

    def test_concat(self):
        self.run_test("def concat(a,b):\n from operator import concat\n return concat(a,b)", [3], [4], concat=[[int],[int]])

    def test___concat__(self):
        self.run_test("def __concat__(a,b):\n from operator import __concat__\n return __concat__(a,b)", [], [1], __concat__=[[int],[int]])

    def test_contains(self):
        self.run_test("def contains(a,b):\n from operator import contains\n return contains(a,b)", [1,2,3,4], 2, contains=[[int],int])

    def test___contains__(self):
        self.run_test("def __contains__(a,b):\n from operator import __contains__\n return __contains__(a,b)", [1,2,3,4], 5, __contains__=[[int],int])

    def test_countOf(self):
        self.run_test("def countOf(a,b):\n from operator import countOf\n return countOf(a,b)", [1,2,3,4,3,3,3,2,3,1], 3, countOf=[[int],int])

    def test_delitem(self):
        self.run_test("def delitem(a,b):\n from operator import delitem\n return delitem(a,b)", [1,2,3,4], 3, delitem=[[int],int])

    def test___delitem__(self):
        self.run_test("def __delitem__(a,b):\n from operator import __delitem__\n return __delitem__(a,b)", [1,2,3,4], 2, __delitem__=[[int],int])

    def test_getitem(self):
        self.run_test("def getitem(a,b):\n from operator import getitem\n return getitem(a,b)", [4,3,2,1], 1, getitem=[[int],int])

    def test___getitem__(self):
        self.run_test("def __getitem__(a,b):\n from operator import __getitem__\n return __getitem__(a,b)", [4,3,2,1], 2, __getitem__=[[int],int])

    def test_indexOf(self):
        self.run_test("def indexOf(a,b):\n from operator import indexOf\n return indexOf(a,b)", [4,3,2,1], 4, indexOf=[[int],int])
         
    def test_itemgetter(self):
        self.run_test("def itemgetter(i,a):\n from operator import itemgetter\n g = itemgetter(i)\n return g(a)", 2, [4,3,2,1], itemgetter=[int,[int]])

    def test_itemgetter2(self):
       self.run_test("def foo():\n from operator import itemgetter\n g = itemgetter(1)", foo=[])

    def test_itemgetter3(self):
        self.run_test("def itemgetter3(i,j,k,a):\n from operator import itemgetter\n g = itemgetter(i,j,k)\n return g(a)", 2, 3, 4, [4,3,2,1,0], itemgetter3=[int,int,int,[int]])

########NEW FILE########
__FILENAME__ = test_optimizations
from test_env import TestEnv


class TestOptimization(TestEnv):

    def test_genexp(self):
        self.run_test("def test_genexp(n): return sum((x*x for x in xrange(n)))", 5, test_genexp=[int])

    def test_genexp_2d(self):
        self.run_test("def test_genexp_2d(n1, n2): return sum((x*y for x in xrange(n1) for y in xrange(n2)))", 2, 3, test_genexp_2d=[int, int])

    def test_genexp_if(self):
        self.run_test("def test_genexp_if(n): return sum((x*x for x in xrange(n) if x < 4))", 5, test_genexp_if=[int])

    def test_genexp_mixedif(self):
        self.run_test("def test_genexp_mixedif(m, n): return sum((x*y for x in xrange(m) for y in xrange(n) if x < 4))", 2, 3, test_genexp_mixedif=[int, int])

    def test_genexp_triangular(self):
        self.run_test("def test_genexp_triangular(n): return sum((x*y for x in xrange(n) for y in xrange(x)))", 2, test_genexp_triangular=[int])

    def test_aliased_readonce(self):
        self.run_test("""
def foo(f,l):
    return map(f,l[1:])
def alias_readonce(n): 
    map = foo
    return map(lambda (x,y): x*y < 50, zip(xrange(n), xrange(n)))
""", 10, alias_readonce=[int])

    def test_replace_aliased_map(self):
        self.run_test("""
def alias_replaced(n): 
    map = filter
    return list(map(lambda x : x < 5, xrange(n)))
""", 10, alias_replaced=[int])

    def test_listcomptomap_alias(self):
        self.run_test("""
def foo(f,l):
    return map(f,l[3:])
def listcomptomap_alias(n): 
    map = foo
    return list([x for x in xrange(n)])
""", 10, listcomptomap_alias=[int])

    def test_readonce_return(self):
        self.run_test("""
def foo(l):
    return l
def readonce_return(n):
    l = foo(range(n))
    return l[:]
""", 5, readonce_return=[int])

    def test_readonce_assign(self):
        self.run_test("""
def foo(l):
    l[2] = 5
    return range(10)
def readonce_assign(n):
    return foo(range(n))
""", 5, readonce_assign=[int])

    def test_readonce_assignaug(self):
        self.run_test("""
def foo(l):
    l += [2,3]
    return range(10)
def readonce_assignaug(n):
    return foo(range(n))
""", 5, readonce_assignaug=[int])

    def test_readonce_for(self):
        self.run_test("""
def foo(l):
    s = []
    for x in xrange(10):
        s.extend(list(l))
    return s
def readonce_for(n):
    return foo(range(n))
""", 5, readonce_for=[int])

    def test_readonce_2for(self):
        self.run_test("""
def foo(l):
    s = 0
    for x in l:
        s += x
    for x in l:
        s += x
    return range(s)
def readonce_2for(n):
    return foo(range(n))
""", 5, readonce_2for=[int])

    def test_readonce_while(self):
        self.run_test("""
def foo(l):
    r = []
    while (len(r) < 50):
        r.extend(list(l))
    return r
def readonce_while(n):
    return foo(range(n))
""", 5, readonce_while=[int])

    def test_readonce_if(self):
        self.run_test("""
def h(l):
    return sum(l)
def g(l):
    return sum(l)
def foo(l):
    if True:
        return g(l)
    else:
        return h(l)
def readonce_if(n):
    return foo(range(n))
""", 5, readonce_if=[int])

    def test_readonce_if2(self):
        self.run_test("""
def h(l):
    return sum(l)
def g(l):
    return max(l[1:])
def foo(l):
    if True:
        return g(l)
    else:
        return h(l)
def readonce_if2(n):
    return foo(range(n))
""", 5, readonce_if2=[int])

    def test_readonce_slice(self):
        self.run_test("""
def foo(l):
    return list(l[:])
def readonce_slice(n):
    return foo(range(n))
""", 5, readonce_slice=[int])

    def test_readonce_listcomp(self):
        self.run_test("""
def foo(l):
    return [z for x in l for y in l for z in range(x+y)]
def readonce_listcomp(n):
    return foo(range(n))
""", 5, readonce_listcomp=[int])

    def test_readonce_genexp(self):
        self.run_test("""
def foo(l):
    return (z for x in l for y in l for z in range(x+y))
def readonce_genexp(n):
    return list(foo(range(n)))
""", 5, readonce_genexp=[int])

    def test_readonce_recursive(self):
        self.run_test("""
def foo(l,n):
    if n < 5:
        return foo(l,n+1)
    else:
        return sum(l)
def readonce_recursive(n): 
    return foo(range(n),0)
""", 5, readonce_recursive=[int])

    def test_readonce_recursive2(self):
        self.run_test("""
def foo(l,n):
    if n < 5:
        return foo(l,n+1)
    else:
        return sum(l[1:])
def readonce_recursive2(n): 
    return foo(range(n),0)
""", 5, readonce_recursive2=[int])

    def test_readonce_cycle(self):
        self.run_test("""
def foo(l,n):
    if n < 5:
        return bar(l,n)
    else:
        return sum(l)
def bar(l,n):
    return foo(l, n+1)
def readonce_cycle(n): 
    return foo(range(n),0)
""", 5, readonce_cycle=[int])

    def test_readonce_cycle2(self):
        self.run_test("""
def foo(l,n):
    if n < 5:
        return bar(l,n)
    else:
        return sum(l)
def bar(l,n):
    return foo(l, n+1)
def readonce_cycle2(n): 
    return foo(range(n),0)
""", 5, readonce_cycle2=[int])

    def test_omp_forwarding(self):
        init = """
def foo():
    a = 2
    #omp parallel
    if 1:
        print a
"""
        ref = """import itertools
def foo():
    a = 2
    'omp parallel'
    if 1:
        print a
    return __builtin__.None
def __init__():
    return __builtin__.None
__init__()"""
        self.check_ast(init, ref, ["pythran.optimizations.ForwardSubstitution"])

    def test_omp_forwarding2(self):
        init = """
def foo():
    #omp parallel
    if 1:
        a = 2
        print a
"""
        ref = """import itertools
def foo():
    'omp parallel'
    if 1:
        pass
        print 2
    return __builtin__.None
def __init__():
    return __builtin__.None
__init__()"""
        self.check_ast(init, ref, ["pythran.optimizations.ForwardSubstitution"])

    def test_omp_forwarding3(self):
        init = """
def foo():
    #omp parallel
    if 1:
        a = 2
    print a
"""
        ref = """import itertools
def foo():
    'omp parallel'
    if 1:
        a = 2
    print a
    return __builtin__.None
def __init__():
    return __builtin__.None
__init__()"""
        self.check_ast(init, ref, ["pythran.optimizations.ForwardSubstitution"])

    def test_full_unroll0(self):
        init = """
def full_unroll0():
    k = []
    for i,j in zip([1,2,3],[4,5,6]): k.append((i,j))
    return k"""

        ref = """import itertools
def full_unroll0():
    k = []
    __tuple1 = (1, 4)
    j = __tuple1[1]
    i = __tuple1[0]
    __list__.append(k, (i, j))
    __tuple1 = (2, 5)
    j = __tuple1[1]
    i = __tuple1[0]
    __list__.append(k, (i, j))
    __tuple1 = (3, 6)
    j = __tuple1[1]
    i = __tuple1[0]
    __list__.append(k, (i, j))
    return k
def __init__():
    return __builtin__.None
__init__()"""

        self.check_ast(init, ref, ["pythran.optimizations.ConstantFolding", "pythran.optimizations.LoopFullUnrolling"])


    def test_full_unroll1(self):
        self.run_test("""
def full_unroll1():
    c = 0
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    for m in range(3):
                        c += 1
    return c""", full_unroll1=[])

########NEW FILE########
__FILENAME__ = test_random
from test_env import TestEnv

class TestRandom(TestEnv):

    def test_random_(self):
        self.run_test("def random_(n): from random import random ; s= sum(random() for x in range(n)) ; return abs(s/n -.5) < .05", 10**5, random_=[int])

    def test_gauss_(self):
        self.run_test("def gauss_(n, mu, sigma): from random import gauss ; s= sum(gauss(mu,sigma) for x in range(n)) ; return abs(s/n -mu)/sigma < .05", 10**6, 5, 2, gauss_=[int, int, int])

    def test_uniform_(self):
        self.run_test("def uniform_(n,b,e): from random import uniform ; s= sum(uniform(b,e) for x in range(n)) ; return abs(s/n - (b+e)*.5) < .05", 10**6, 5, 25, uniform_=[int, int, int])

    def test_expovariate_(self):
        self.run_test("def expovariate_(n,l): from random import expovariate ; s= sum(expovariate(l) for x in range(n)) ; return abs(s/n - 1/l) < .05", 10**6, 5., expovariate_=[int,  float])

    def test_randrange0(self):
        self.run_test("def randrange0(n): from random import randrange ; s= sum(randrange(n) for x in range(n)) ; return abs(s/n - n/2) < .05", 10**7,  randrange0=[int])

    def test_randrange1(self):
        self.run_test("def randrange1(n): from random import randrange ; s= sum(randrange(-n,n) for x in range(n)) ; return abs(s/n) < .05", 10**7,  randrange1=[int])

    def test_randrange2(self):
        self.run_test("def randrange2(n): from random import randrange ; s= [randrange(3,n,3)%3==0 for x in range(n)] ; return all(s)" , 10**4,  randrange2=[int])

    def test_randint(self):
        self.run_test("def randint_(n): from random import randint ; s= [randint(0,n/1000) for x in range(n)] ; return abs(sum(s)/n) < .05, len(set(s))", 10**6,  randint_=[int])

    def test_sample_(self):
        self.run_test("def sample_(n,k): from random import sample ; s = sum(sum(sample(range(n),k)) for x in range(n)) ; return abs(s/float(n*n)) < .05  ", 10**4, 4, sample_=[int, int])

    def test_choice(self):
        self.run_test("def choice_(n): from random import choice ; s= sum(choice(range(n)) for x in xrange(n)) ; return abs(s/n - n/2) < .05", 10**5,  choice_=[int])

    def test_random_seed(self):
        self.run_test("def random_seed(): from random import random, seed ; seed(1) ; a = random() ; seed(1); b = random(); return a == b", random_seed=[])

########NEW FILE########
__FILENAME__ = test_rec
from test_env import TestEnv

class TestBase(TestEnv):

    def test_rec0(self):
        self.run_test("""
def test_rec0(n):
  z = 1
  if n > 1:
    z = n * test_rec0(n-1)
  return z""", 5, test_rec0=[int])

    def test_rec1(self):
        self.run_test("""
def test_rec1(n):
  z = 1
  while n > 1:
    z = n * test_rec1(n-1)
    n -= 1
  return z""", 5, test_rec1=[int])

########NEW FILE########
__FILENAME__ = test_rosetta
import unittest
from test_env import TestFromDir
import os


class TestRosetta(TestFromDir):

    path = os.path.join(os.path.dirname(__file__),"rosetta")

TestRosetta.populate(TestRosetta)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scipy
from test_env import TestEnv
# from http://www.scipy.org/Download , weave/example directory

class TestScipy(TestEnv):

    def test_laplace(self):
        code="""
def laplace(u,dx, dy):
    nx, ny=len(u), len(u[0])
    for i in range(1, nx-1):
        for j in range(1, ny-1):
            u[i][j] = ((u[i-1][j] + u[i+1][j])*dy**2 +
                      (u[i][j-1] + u[i][j+1])*dx**2)/(2.0*(dx**2 + dy**2))
"""
        self.run_test(code, [[0.1,0.2,0.3],[0.1,0.2,0.3],[0.1,0.2,0.3]], 0.01, 0.02, laplace=[[[float]], float, float])

    def test_recursive_fibonnaci(self):
        code="""
def recursive_fibonnaci(a):
    if a <= 2:
        return 1
    else:
        return recursive_fibonnaci(a-2) + recursive_fibonnaci(a-1)
        """
        self.run_test(code, 5, recursive_fibonnaci=[int])

    def test_iterative_fibonnaci(self):
        code="""
def iterative_fibonnaci(a):
    if a <= 2:
        return 1
    last = next_to_last = 1
    i = 2
    while i < a:
        result = last + next_to_last
        next_to_last = last
        last = result
        i+=1
    return result;
"""
        self.run_test(code, 5, iterative_fibonnaci=[int])

    def test_binary_search(self):
        code="""
def binary_search(seq, t):
    min = 0; max = len(seq) - 1
    while 1:
        if max < min:
            return -1
        m = (min + max) / 2
        if seq[m] < t:
            min = m + 1
        elif seq[m] > t:
            max = m - 1
        else:
            return m
"""
        self.run_test(code,[1,2,3,4,5,6,7,8,9], 4, binary_search=[[int], int])

    def test_ramp(self):
        code="""
def ramp(result, start, end):
    size=len(result)
    assert size > 1
    step = (end-start)/(size-1)
    for i in xrange(size):
        result[i] = start + step*i
"""
        self.run_test(code,[0 for x in xrange(10)], 1.5, 9.5, ramp=[[float], float, float])

########NEW FILE########
__FILENAME__ = test_set
import unittest
from test_env import TestEnv

class TestSet(TestEnv):

    def test_cpy_constructor(self):
        code="""
def are_equal(s1):
    s2 = set(s1)
    return s2 == s1
"""
        self.run_test(code, {'jack', 'sjoerd'}, are_equal=[{str}])
    def test_in(self):
        self.run_test("def _in(a,b):\n return b in a", {'aze', 'qsd'},'qsd', _in=[{str},str])

    def test_empty_in(self):
        self.run_test("def empty_in(b):\n return b in set()",'qsd', empty_in=[str])

    def test_len(self):
        self.run_test("def _len(a):\n return len(a)", {'aze', 'qsd', 'azeqsd'}, _len=[{str}])

    def test_disjoint(self):
        self.run_test("def _isdisjoint(a,b):\n return a.isdisjoint(b)", {1,3,2}, {7,2,5}, _isdisjoint=[{int},{float}])

    def test_operator_le(self):
        self.run_test("def _le(a,b):\n return a <= b", {1.,5.}, {1,2,5}, _le=[{float},{int}])

    def test_issubset(self):
        self.run_test("def _issubset(a,b):\n return a.issubset(b)", {1.,5.}, {1,2,5}, _issubset=[{float},{int}])

    def test_operator_lt(self):
        self.run_test("def _lt(a,b):\n return a < b", {1.,5.}, {1,2,5}, _lt=[{float},{int}])

    def test_operator_ge(self):
        self.run_test("def _ge(a,b):\n return a >= b", {1.,5.}, {1,2,5}, _ge=[{float},{int}])

    def test_issuperset(self):
        self.run_test("def _issuperset(a,b):\n return a.issuperset(b)", {1.,5.}, {1,2,5}, _issuperset=[{float},{int}])

    def test_operator_gt(self):
        self.run_test("def _gt(a,b):\n return a > b", {1.,5.}, {1,2,5}, _gt=[{float},{int}])

    def test_clear(self):
        self.run_test("def _clear(a):\n a.clear()\n return a", {1.,5.}, _clear=[{float}])

    def test_pop(self):
        self.run_test("def _pop(a):\n a.pop()\n return a", {1.,5.}, _pop=[{float}])

    def test_remove(self):
        self.run_test("def _remove(a,b):\n a.remove(b)\n return a", {1,3}, 1., _remove=[{int}, float])

    def test_remove_strict(self):
        self.run_test("def _remove_strict(a,b):\n a.remove(b)\n return a <= {3} and a >= {3}", {1,3}, 1., _remove_strict=[{int}, float])

    def test_discard(self):
        self.run_test("def _discard(a ,b):\n a.discard(b)\n return a", {1,3}, 1., _discard=[{int},float])

    def test_copy(self):
        self.run_test("def _copy(a):\n b=a.copy()\n return a <= {3} and a >= {3} and not a is b", {1,3}, _copy=[{int}])

    def test_fct_union(self):
        self.run_test("def _fct_union(b, c):\n a={1.}\n return a.union(b, c)", {1,3}, {1.,3.,4.,5.,6.} , _fct_union=[{int},{float}])

    def test_fct_union_empty_set(self):
        self.run_test("def _fct_union_empty_set(b, c):\n a=set()\n return a.union(b, c)", {1,3}, {1.,3.,4.,5.,6.} , _fct_union_empty_set=[{int},{float}])

    def test_fct_union_empty_set_list(self):
        self.run_test("def _fct_union_empty_set_list(b, c):\n a=set()\n return a.union(b, c)", {1,3}, [1.,3.,4.,5.,6.] , _fct_union_empty_set_list=[{int},[float]])

    def test_fct_union_list(self):
        self.run_test("def _fct_union_list(b, c):\n a={1.}\n return a.union(b, c)", [1,3], {1.,3.,4.,5.,6.} , _fct_union_list=[[int],{float}])

    def test_fct_union_1arg(self):
        self.run_test("def _fct_union_1arg(b):\n a={1.}\n return a.union(b)", {1,3,4,5,6}, _fct_union_1arg=[{int}])

    def test_operator_union(self):
        self.run_test("def _operator_union(b, c):\n a={1.}\n return (a | b | c)", {1,3,4,5,6}, {1.,2.,4.}, _operator_union=[{int},{float}])

    def test_update(self):
        self.run_test("def _update(b, c):\n a={1.}\n a.update(b, c)\n return a", {1,3}, {1.,3.,4.,5.,6.} , _update=[{int},{float}])

    def test_update_list(self):
        self.run_test("def _update_list(b, c):\n a={1.}; a.update(b, c); return a", {1,3}, [1.,3.,4.,5.,6.] , _update_list=[{int},[float]])

    def test_update_empty_set_list(self):
        self.run_test("def _update_empty_set_list(b, c):\n a=set()\n a.update(b, c)\n return a", {1,3}, [1.,3.,4.,5.,6.] , _update_empty_set_list=[{int},[float]])

    def test_operator_update(self):
        self.run_test("def _operator_update(b, c):\n a={1.,10.}\n a |= b | c\n return a", {1,3,4,5,6}, {1.,2.,4.}, _operator_update=[{int},{float}])

    def test_fct_intersection(self):
        self.run_test("def _fct_intersection(b, c):\n a={1.}\n return a.intersection(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_intersection=[{int},{float}])

    def test_fct_intersection_empty_set(self):
        self.run_test("def _fct_intersection_empty_set(b, c):\n a=set()\n return a.intersection(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_intersection_empty_set=[{int},{float}])

    def test_fct_intersection_list(self):
        self.run_test("def _fct_intersection_list(b, c):\n a={1.}\n return a.intersection(b,c)", {1,3,4,5,6}, [1.,2.,4.], _fct_intersection_list=[{int},[float]])

    def test_operator_intersection(self):
        self.run_test("def _operator_intersection(b, c):\n a={1.}\n return (a & b & c)", {1,3,4,5,6}, {1.,2.,4.}, _operator_intersection=[{int},{float}])

    def test_fct_intersection_update(self):
        self.run_test("def _fct_intersection_update(b, c):\n a={1.,10.}\n return a.intersection_update(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_intersection_update=[{int},{float}])

    def test_fct_intersection_update_empty_set(self):
        self.run_test("def _fct_intersection_update_empty_set(b, c):\n a=set()\n return a.intersection_update(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_intersection_update_empty_set=[{int},{float}])

    def test_fct_intersection_empty_set_update(self):
        self.run_test("def _fct_intersection_empty_set_update(c):\n a={1}\n b=set()\n return a.intersection_update(b,c)", {1.,2.,4.}, _fct_intersection_empty_set_update=[{float}])

    def test_fct_intersection_update_list(self):
        self.run_test("def _fct_intersection_update_list(b, c):\n a={1.,10.}\n return a.intersection_update(b,c)", [1,3,4,5,6], {1.,2.,4.}, _fct_intersection_update_list=[[int],{float}])

    def test_operator_intersection_update(self):
        self.run_test("def _operator_intersection_update(b, c):\n a={1.}\n a &= b & c\n return a", {1,3,4,5,6}, {1.,2.,4.}, _operator_intersection_update=[{int},{float}])

    @unittest.skip("pythran -E + pythran success")
    def test_operator_intersection_update_empty_set(self):
        self.run_test("def _operator_intersection_update_empty_set(b, c):\n a=set()\n a &= b & c\n return a", {1,3,4,5,6}, {1.,2.,4.}, _operator_intersection_update_empty_set=[{int},{float}])

    def test_fct_difference(self):
        self.run_test("def _fct_difference(b, c):\n a={1.,5.,10.}\n return a.difference(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_difference=[{int},{float}])

    def test_fct_difference_empty_set(self):
        self.run_test("def _fct_difference_empty_set(b, c):\n a=set()\n return a.difference(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_difference_empty_set=[{int},{float}])

    def test_fct_difference_list(self):
        self.run_test("def _fct_difference_list(b, c):\n a={1.,5.,10.}\n return a.difference(b,c)", [1,3,4,5,6], {1.,2.,4.}, _fct_difference_list=[[int],{float}])

    def test_operator_difference(self):
        self.run_test("def _operator_difference(b, c):\n a={1.}\n return (a - b - c)", {1,3,4,5,6}, {1.,2.,4.}, _operator_difference=[{int},{float}])

    def test_operator_difference_1arg(self):
        self.run_test("def _operator_difference_1arg(b):\n a={1.,2.,5.}\n return (b - a)", {1,3,4,5,6}, _operator_difference_1arg=[{int}])

    def test_fct_difference_update(self):
        self.run_test("def _fct_difference_update(b, c):\n a={1.,5.,10.}\n return a.difference_update(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_difference_update=[{int},{float}])

    def test_fct_difference_update_empty_set(self):
        self.run_test("def _fct_difference_update_empty_set(b, c):\n a=set()\n return a.difference_update(b,c)", {1,3,4,5,6}, {1.,2.,4.}, _fct_difference_update_empty_set=[{int},{float}])

    def test_fct_difference_update_list(self):
        self.run_test("def _fct_difference_update_list(b, c):\n a={1.,5.,10.}\n return a.difference_update(b,c)", {1,3,4,5,6}, [1.,2.,4.], _fct_difference_update_list=[{int},[float]])

    def test_operator_difference_update(self):
        self.run_test("def _operator_difference_update(b, c):\n a={1.}\n a -= b - c\n return a", {1,3,4,5,6}, {1.,2.,4.}, _operator_difference_update=[{int},{float}])

    def test_fct_symmetric_difference(self):
        self.run_test("def _fct_symmetric_difference(b, c):\n return (b.symmetric_difference(c))", {1,3,6}, {1.,2.,5.}, _fct_symmetric_difference=[{int},{float}])

    def test_fct_symmetric_difference_empty_set(self):
        self.run_test("def _fct_symmetric_difference_empty_set(c):\n b=set()\n return (b.symmetric_difference(c))", {1.,2.,5.}, _fct_symmetric_difference_empty_set=[{float}])

    def test_fct_symmetric_difference_list(self):
        self.run_test("def _fct_symmetric_difference_list(b, c):\n return (b.symmetric_difference(c))", {1,3,6}, [1.,2.,5.], _fct_symmetric_difference_list=[{int},[float]])

    def test_operator_symmetric_difference(self):
        self.run_test("def _operator_symmetric_difference(b, c):\n return (b ^ c)", {1,3,6}, {1.,2.,5.}, _operator_symmetric_difference=[{int},{float}])

    def test_fct_symmetric_difference_update(self):
        self.run_test("def _fct_symmetric_difference_update(b, c):\n return (c.symmetric_difference_update(b))", {1,3,6}, {1.,2.,5.}, _fct_symmetric_difference_update=[{int},{float}])

    def test_fct_symmetric_difference_update_empty_set(self):
        self.run_test("def _fct_symmetric_difference_update_empty_set(b):\n c=set()\n return (c.symmetric_difference_update(b))", {1.,2.,5.}, _fct_symmetric_difference_update_empty_set=[{float}])

    def test_fct_symmetric_difference_update2(self):
        self.run_test("def _fct_symmetric_difference_update2(b, c):\n return (b.symmetric_difference_update(c))", {1,3,6}, {1.,2.,5.}, _fct_symmetric_difference_update2=[{int},{float}])

    def test_fct_symmetric_difference_update_list(self):
        self.run_test("def _fct_symmetric_difference_update_list(b, c):\n return (b.symmetric_difference_update(c))", {1,3,6}, [1.,2.,5.], _fct_symmetric_difference_update_list=[{int},[float]])

    def test_operator_symmetric_difference_update(self):
        self.run_test("def _operator_symmetric_difference_update(b, c):\n b ^= c\n return b", {1,3,6}, {1.,2.,5.}, _operator_symmetric_difference_update=[{int},{float}])

    def test_operator_symmetric_difference_update2(self):
        self.run_test("def _operator_symmetric_difference_update2(b, c):\n c ^= b\n return c", {1,3,6}, {1.,2.,5.}, _operator_symmetric_difference_update2=[{int},{float}])

    # Check if conflict between set.pop() & list.pop()
    def test_conflict_pop(self):
        self.run_test("def _conflict_pop(a,b):\n a.pop()\n b.pop()\n return len(a)+len(b)", {1.,5.}, [1,2], _conflict_pop=[{float},[int]])

    def test_set_to_bool_conversion(self):
        self.run_test("def set_to_bool_conversion(s, t): return (1 if s else 0), (t if t else set())",
                      set(), {1, 2},set_to_bool_conversion=[{int}, {int}])

    def test_print_set(self):
        self.run_test("def print_set(s): return str(s)", {1, 2}, print_set=[{int}])

    def test_print_empty_set(self):
        self.run_test("def print_empty_set(s): return str(s)", set(), print_empty_set=[{int}])


########NEW FILE########
__FILENAME__ = test_simd
from test_env import TestEnv
import numpy

class TestSimd(TestEnv):

    PYTHRAN_CXX_FLAGS = TestEnv.PYTHRAN_CXX_FLAGS + ['-DUSE_BOOST_SIMD', '-march=native']

    def test_simd_arc_distance(self):
        code = '''
import numpy as np
def simd_arc_distance_kernel(theta_1, phi_1,
                       theta_2, phi_2):
    """
    Calculates the pairwise arc distance between all points in vector a and b.
    """
    temp = np.sin((theta_2-theta_1)/2)**2+np.cos(theta_1)*np.cos(theta_2)*np.sin((phi_2-phi_1)/2)**2
    distance_matrix = 2 * (np.arctan2(np.sqrt(temp),np.sqrt(1-temp)))
    return distance_matrix
def simd_arc_distance(n):
    r = np.ones(n)
    return simd_arc_distance_kernel(r, r, r, r)
'''
        self.run_test(code, 40, simd_arc_distance=[int])

    def test_simd_rosen(self):
        code = '''
import numpy
def simd_rosen_der(n):
    x = numpy.ones(n)
    xm = x[1:-1]
    xm_m1 = x[:-2]
    xm_p1 = x[2:]
    der = numpy.zeros_like(x)
    der[1:-1] = (+ 200 * (xm - xm_m1 ** 2)
                 - 400 * (xm_p1 - xm ** 2) * xm
                 - 2 * (1 - xm))
    der[0] = -400 * x[0] * (x[1] - x[0] ** 2) - 2 * (1 - x[0])
    der[-1] = 200 * (x[-1] - x[-2] ** 2)
    return der'''
        self.run_test(code, 40, simd_rosen_der=[int])



# automatic generation of basic test cases for ufunc
binary_ufunc = (
        'add','arctan2',
        'bitwise_and', 'bitwise_or', 'bitwise_xor',
        'copysign',
        'divide',
        #'equal',
        'floor_divide', 'fmax', 'fmin', 'fmod',
        #'greater', 'greater_equal',
        'hypot',
        #'less', 'less_equal',  'logaddexp2', "logical_and", "logical_or", "logical_xor",
        'ldexp', 'left_shift', 'logaddexp',
        'maximum', 'minimum', 'mod','multiply',
        #'not_equal',
        'nextafter',
        'power',
        'remainder','right_shift',
        'subtract',
        'true_divide',
        )

unary_ufunc = (
        'abs', 'absolute', 'arccos', 'arccosh', 'arcsin', 'arcsinh', 'arctan', 'arctanh',
        'bitwise_not',
        'ceil', 'conj', 'conjugate', 'cos', 'cosh',
        'deg2rad', 'degrees',
        'exp', 'expm1',
        'fabs', 'floor',
        # 'isneginf', 'isposinf'
        'isinf', 'isnan', 'invert', 'isfinite',
        # 'logical_not'
        'log10', 'log1p', 'log2',
        'negative',
        'rad2deg', 'radians','reciprocal', 'rint', 'round', 'round_',
        'sign', 'signbit',
        'sin', 'sinh', 'spacing', 'sqrt', 'square',
        'tan', 'tanh','trunc',
        )

for f in unary_ufunc:
    if 'bitwise_' in f or 'invert' in f:
        setattr(TestSimd, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(): from numpy import ones, int32, {0} ; a = ones(10, int32) ; return {0}(a)', np_{0}=[])".format(f)))
    else:
        setattr(TestSimd, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(): from numpy import ones, {0} ; a = ones(10) ; return {0}(a)', np_{0}=[])".format(f)))

for f in binary_ufunc:
    if 'bitwise_' in f or 'ldexp' in f or '_shift' in f :
        setattr(TestSimd, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(): from numpy import ones, int32, {0} ; a = ones(10, int32) ; return {0}(a,a)', np_{0}=[])".format(f)))
    else:
        setattr(TestSimd, 'test_' + f, eval("lambda self: self.run_test('def np_{0}(): from numpy import ones, {0} ; a = ones(10) ; return {0}(a,a)', np_{0}=[])".format(f)))

########NEW FILE########
__FILENAME__ = test_spec_parser
import unittest
from pythran import spec_parser
import os.path

#pythran export a((float,(int,long),str list) list list)
#pythran export a(str)
#pythran export a( (str,str), int, long list list)
#pythran export a( long set )
#pythran export a( long:str dict )
#pythran export a( long )
#pythran export a( long[] )
#pythran export a( long[][] )
#pythran export a( int8 )
#pythran export a( uint8 )
#pythran export a( int16 )
#pythran export a( uint16 )
#pythran export a( int32 )
#pythran export a( uint32 )
#pythran export a( int64 )
#pythran export a( uint64 )
#pythran export a( float32 )
#pythran export a( float64 )
#pythran export a( complex64 )
#pythran export a( complex128 )
#pythran export a( int8 set )
#pythran export a( uint8 list)
#pythran export a( int16 [])
#pythran export a( uint16 [][])
#pythran export a( (int32, ( uint32 , int64 ) ) )
#pythran export a( uint64:float32 dict )
#pythran export a( float64, complex64, complex128 )

class TestSpecParser(unittest.TestCase):

    def test_parser(self):
        real_path = os.path.splitext(os.path.realpath(__file__))[0]+".py"
        print spec_parser(real_path)

########NEW FILE########
__FILENAME__ = test_str
from test_env import TestEnv

class TestStr(TestEnv):

    def test_str_startswith0(self):
        self.run_test("def str_startswith0(s0, s1): return s0.startswith(s1)", "barbapapa", "barba", str_startswith0=[str, str])

    def test_str_startswith1(self):
        self.run_test("def str_startswith1(s0, s1): return s0.startswith(s1)", "barbapapa", "barbi", str_startswith1=[str, str])

    def test_str_endswith0(self):
        self.run_test("def str_endswith0(s0, s1): return s0.endswith(s1)", "barbapapa", "papa", str_endswith0=[str, str])

    def test_str_endswith1(self):
        self.run_test("def str_endswith1(s0, s1): return s0.endswith(s1)", "barbapapa", "papy", str_endswith1=[str, str])

    def test_str_empty(self):
        self.run_test("def str_empty(s0): return '>o_/' if s0 else '0x0'", "", str_empty=[str])

    def test_str_failed_conversion(self):
        self.run_test("def str_failed_conversion(s):\n try: return long(s)\n except: return 42", "prout", str_failed_conversion=[str])

    def test_str_replace0(self):
        self.run_test("def str_replace0(s): return s.replace('er', 'rer')", "parler", str_replace0=[str])

    def test_str_replace1(self):
        self.run_test("def str_replace1(s): return s.replace('er', 'rer', 1)", "erlang manger dessert", str_replace1=[str])

    def test_str_replace2(self):
        self.run_test("def str_replace2(s): return s.replace('', 'du vide surgit rien', 1)", "j aime les moulinettes a fromage", str_replace2=[str])

    def test_str_ascii_letters(self):
        self.run_test("def str_ascii_letters(): import string; return string.ascii_letters", str_ascii_letters=[])

    def test_str_ascii_lowercase(self):
        self.run_test("def str_ascii_lowercase(): import string; return string.ascii_lowercase", str_ascii_lowercase=[])

    def test_str_ascii_uppercase(self):
        self.run_test("def str_ascii_uppercase(): import string; return string.ascii_uppercase", str_ascii_uppercase=[])

    def test_str_digits(self):
        self.run_test("def str_digits(): import string; return string.digits", str_digits=[])

    def test_str_hexdigits(self):
        self.run_test("def str_hexdigits(): import string; return string.hexdigits", str_hexdigits=[])

    def test_str_octdigits(self):
        self.run_test("def str_octdigits(): import string; return string.octdigits", str_octdigits=[])

    def test_str_lower(self):
        self.run_test("def str_lower(s): return s.lower()", "ThiS iS a TeST", str_lower=[str])

    def test_str_upper(self):
        self.run_test("def str_upper(s): return s.upper()", "ThiS iS a TeST", str_upper=[str])

    def test_str_capitalize(self):
        self.run_test("def str_capitalize(s): return s.capitalize()", "thiS iS a TeST", str_capitalize=[str])

    def test_str_strip(self):
        self.run_test("def str_strip(s): return s.strip()", "       ThiS iS a TeST        ", str_strip=[str])

    def test_str_strip2(self):
        self.run_test("def str_strip2(s): return s.strip(\"TSih\")", "ThiS iS a TeST", str_strip2=[str])

    def test_str_lstrip(self):
        self.run_test("def str_lstrip(s): return s.lstrip()", "       ThiS iS a TeST        ", str_lstrip=[str])

    def test_str_lstrip2(self):
        self.run_test("def str_lstrip2(s): return s.lstrip(\"TSih\")", "ThiS iS a TeST", str_lstrip2=[str])

    def test_str_rstrip(self):
        self.run_test("def str_rstrip(s): return s.rstrip()", "       ThiS iS a TeST        ", str_rstrip=[str])

    def test_str_rstrip2(self):
        self.run_test("def str_rstrip2(s): return s.rstrip(\"TSih\")", "ThiS iS a TeST", str_rstrip2=[str])

    def test_str_format(self):
        self.run_test("def str_format(a): return '%.2f %.2f' % (a, a)", 43.23, str_format=[float])

    def test_str_join0(self):
        self.run_test("def str_join0(): a = ['1'] ; a.pop() ; return 'e'.join(a)", str_join0=[])

    def test_str_join1(self):
        self.run_test("def str_join1(): a = ['l', 'l'] ; return 'o'.join(a)", str_join1=[])

    def test_str_join2(self):
        self.run_test("def str_join2(a): from itertools import ifilter; return 'o'.join(ifilter(len, a))", ['l', 'l'], str_join2=[[str]])

    def test_str_find0(self):
        self.run_test("def str_find0(s): return s.find('pop')", "popop", str_find0=[str])

    def test_str_find1(self):
        self.run_test("def str_find1(s): return s.find('pap')", "popop", str_find1=[str])

    def test_str_reversal(self):
        self.run_test("def str_reversal(s): return map(ord,reversed(s))", "dear", str_reversal=[str])

    def test_str_substring_iteration(self):
        self.run_test("def str_substring_iteration(s): return map(ord, s[1:-1])", "pythran", str_substring_iteration=[str])

    def test_str_isalpha(self):
        self.run_test("def str_isalpha(s, t, u): return s.isalpha(), t.isalpha(), u.isalpha()", "e", "1", "", str_isalpha=[str,str, str])

    def test_str_isdigit(self):
        self.run_test("def str_isdigit(s, t, u): return s.isdigit(), t.isdigit(), u.isdigit()", "e", "1", "", str_isdigit=[str,str, str])

    def test_str_count(self):
        self.run_test("def str_count(s, t, u, v): return s.count(t), s.count(u), s.count(v)",
                      "pythran is good for health", "py", "niet", "t",
                      str_count=[str, str, str, str])

########NEW FILE########
__FILENAME__ = test_time
from test_env import TestEnv

class TestTime(TestEnv):

    def test_time_and_sleep(self):
        self.run_test("""
def time_and_sleep():
    import time
    begin = time.time()
    time.sleep(2)
    end = time.time()
    return (end - begin) < 2.05 and (end - begin) > 1.95""", time_and_sleep=[])

########NEW FILE########
__FILENAME__ = test_typing
from test_env import TestEnv
import unittest

class TestTyping(TestEnv):

    def test_list_of_set(self):
        code = '''
def list_of_set():
    l=[set()]
    l[0].add("12")
    return l'''
        self.run_test(code, list_of_set=[])

    def test_dict_of_set(self):
        code = '''
def dict_of_set():
    l={0:set()}
    l[0].add("12")
    return l'''
        self.run_test(code, dict_of_set=[])

    def test_typing_aliasing_and_indices(self):
        self.run_test('def typing_aliasing_and_indices(): d={};e={}; f = e or d; f[1]="e"; return d,e,f', typing_aliasing_and_indices=[])

    def test_typing_aliasing_and_combiner(self):
        self.run_test('def typing_aliasing_and_combiner(): d=set();e=set(); f = e or d; f.add("e"); return d,e,f', typing_aliasing_and_combiner=[])

    def test_typing_aliasing_and_combiner_back(self):
        self.run_test('def typing_aliasing_and_combiner_back(): d=set();e=set(); f = e or d; e.add("e"); return d,e,f', typing_aliasing_and_combiner_back=[])

    def test_typing_aliasing_and_update(self):
        code = '''
def foo(d):
    f=d
    f+=[1]
def typing_aliasing_and_update():
    a= []
    foo(a)
    return a'''
        self.run_test(code, typing_aliasing_and_update=[])

    def test_functional_variant_container0(self):
        code='''
import math
def functional_variant_container0():
    l=[]
    l.append(math.cos)
    l.append(math.sin)
    return l[0](12)'''
        self.run_test(code, functional_variant_container0=[])

    def test_functional_variant_container1(self):
        code='''
import math
def functional_variant_container1():
    l=[math.cos, math.sin]
    return l[0](12)'''
        self.run_test(code, functional_variant_container1=[])

    @unittest.skip("bad typing: need backward propagation")
    def test_type_set_in_loop(self):
        code = '''
def type_set_in_loop():
    a = [[]]
    for i in range(2):
        b = []
        for j in a:
            b += [j] + [[1]]
        a = b
    return a,b'''
        self.run_test(code, type_set_in_loop=[])

    @unittest.skip("bad typing: need backward propagation")
    def test_type_set_in_while(self):
        code = '''
def type_set_in_while():
    a = [[]]
    n = 3
    while n:
        b = []
        for j in a:
            b += [j] + [[1]]
        a = b
        n -= 1
    return a,b'''
        self.run_test(code, type_set_in_while=[])

    @unittest.skip("issue #78")
    def test_recursive_interprocedural_typing0(self):
        code = '''
from cmath import exp, pi

def fft(x):
    N = len(x)
    if N <= 1: return x
    even = fft(x[0::2])
    odd =  fft(x[1::2])
    return [even[k] + exp(-2j*pi*k/N)*odd[k] for k in xrange(N/2)] + \
           [even[k] - exp(-2j*pi*k/N)*odd[k] for k in xrange(N/2)]

def recursive_interprocedural_typing0():
   l = [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
   z = fft(l)
   return z'''
        self.run_test(code, recursive_interprocedural_typing0=[])

    @unittest.skip("issue #89")
    def test_recursive_interprocedural_typing1(self):
        code = '''
def s_perm(seq):
    if not seq:
        return [[]]
    else:
        new_items = []
        for item in s_perm(seq[:-1]):
            new_items += [item + seq for i in range(1)]
        return new_items
def recursive_interprocedural_typing1():
    l = [1,2,3]
    return s_perm(l)'''
        self.run_test(code, recursive_interprocedural_typing1=[])

########NEW FILE########
__FILENAME__ = toolchain
'''
This module contains all the stuff to make your way from python code to
a dynamic library, see __init__.py for exported interfaces.
'''
import sys
import re
import os.path
import sysconfig
import shutil
import logging
logger = logging.getLogger(__name__)

from cxxgen import *
import ast
from middlend import refine
from backend import Cxx
import frontend
from config import cfg
from passmanager import PassManager
from numpy import get_include
from typing import extract_constructed_types, pytype_to_ctype, pytype_to_deps
from tables import pythran_ward, functions
from intrinsic import ConstExceptionIntr

from os import devnull
from subprocess import check_call, check_output, STDOUT, CalledProcessError
from tempfile import mkstemp, NamedTemporaryFile
import networkx as nx


def _format_cmdline(cmd):
    """No comma when printing a command line allows for copy/paste"""
    return "'" + "' '".join(cmd) + "'"


def _extract_all_constructed_types(v):
    return sorted(set(reduce(lambda x, y: x + y,
                            (extract_constructed_types(t) for t in v), [])),
                  key=len)


def _extract_specs_dependencies(specs):
    deps = set()
    for _, signatures in specs.iteritems():
        for _, signature in enumerate(signatures):
            for t in signature:
                deps.update(pytype_to_deps(t))
    return deps


def _parse_optimization(optimization):
    '''Turns an optimization of the form
        my_optim
        my_package.my_optim
        into the associated symbol'''
    splitted = optimization.split('.')
    if len(splitted) == 1:
        splitted = ['pythran', 'optimizations'] + splitted
    return reduce(getattr, splitted[1:], __import__(splitted[0]))


def _python_cppflags():
    return ["-I" + sysconfig.get_config_var("INCLUDEPY")]


def _numpy_cppflags():
    return ["-I" + os.path.join(get_include(), 'numpy')]


def _pythran_cppflags():
    curr_dir = os.path.dirname(os.path.dirname(__file__))
    get = lambda *x: '-I' + os.path.join(curr_dir, *x)
    return [get('.'), get('pythran')]


def _python_ldflags():
    return ["-L" + sysconfig.get_config_var("LIBPL"),
            "-lpython" + sysconfig.get_config_var('VERSION')]


def _get_temp(content, suffix=".cpp"):
    '''Get a temporary file for given content, default extension is .cpp
       It is user's responsability to delete when done.'''
    fd, fdpath = mkstemp(suffix)
    with os.fdopen(fd, "w") as cpp:
        cpp.write(content)
    return fd, fdpath


class HasArgument(ast.NodeVisitor):
    '''Checks if a given function has arguments'''
    def __init__(self, fname):
        self.fname = fname

    def visit_Module(self, node):
        for n in node.body:
            if type(n) is ast.FunctionDef and n.name == self.fname:
                return len(n.args.args) > 0
        return False

# PUBLIC INTERFACE STARTS HERE


class CompileError(Exception):
    """ Holds an exception when the C++ compilation failed"""

    def __init__(self, cmdline, output):
            self.cmdline = _format_cmdline(cmdline)
            self.output = output
            self._message = "\n".join(["Compile error!\n",
                                       "******** Command line was: ********",
                                       self.cmdline,
                                       "\n******** Output :  ********\n",
                                       self.output])
            super(CompileError, self).__init__(self._message)


def cxxflags():
    """The C++ flags to compile a Pythran generated cpp file"""
    return (cfg.get('user', 'cxxflags').split() +
            cfg.get('sys', 'cxxflags').split())


def cppflags():
    """The C++ flags to preprocess a Pythran generated cpp file"""
    return (_python_cppflags() +
            _numpy_cppflags() +
            _pythran_cppflags() +
            cfg.get('sys', 'cppflags').split() +
            cfg.get('user', 'cppflags').split())


def ldflags():
    """The linker flags to link a Pythran code into a shared library"""
    return (_python_ldflags() +
            cfg.get('sys', 'ldflags').split() +
            cfg.get('user', 'ldflags').split())


def generate_cxx(module_name, code, specs=None, optimizations=None):
    '''python + pythran spec -> c++ code
    returns a BoostPythonModule object

    '''
    pm = PassManager(module_name)

    # front end
    ir, renamings = frontend.parse(pm, code)

    # middle-end
    optimizations = (optimizations or
                     cfg.get('pythran', 'optimizations').split())
    optimizations = map(_parse_optimization, optimizations)
    refine(pm, ir, optimizations)

    # back-end
    content = pm.dump(Cxx, ir)

    # instanciate the meta program
    if specs is None:

        class Generable:
            def __init__(self, content):
                self.content = content

            def __str__(self):
                return str(self.content)

            generate = __str__

        mod = Generable(content)
    else:
        # uniform typing
        for fname, signatures in specs.items():
            if not isinstance(signatures, tuple):
                specs[fname] = (signatures,)

        mod = BoostPythonModule(module_name)
        mod.use_private_namespace = False
        # very low value for max_arity leads to various bugs
        min_val = 2
        specs_max = [max(map(len, s)) for s in specs.itervalues()]
        max_arity = max([min_val] + specs_max)
        mod.add_to_preamble([Define("BOOST_PYTHON_MAX_ARITY", max_arity)])
        mod.add_to_preamble([Define("BOOST_SIMD_NO_STRICT_ALIASING", "1")])
        mod.add_to_preamble([Include("pythonic/core.hpp")])
        mod.add_to_preamble([Include("pythonic/python/core.hpp")])
        mod.add_to_preamble(map(Include, _extract_specs_dependencies(specs)))
        mod.add_to_preamble(content.body)
        mod.add_to_init([
            Line('#ifdef PYTHONIC_TYPES_NDARRAY_HPP\nimport_array()\n#endif')])

        # topologically sorted exceptions based on the inheritance hierarchy.
        # needed because otherwise boost python register_exception handlers
        # do not catch exception type in the right way
        # (first valid exception is selected)
        # Inheritance has to be taken into account in the registration order.
        exceptions = nx.DiGraph()
        for function_name, v in functions.iteritems():
            for mname, symbol in v:
                if isinstance(symbol, ConstExceptionIntr):
                    exceptions.add_node(
                        getattr(sys.modules[mname], function_name))

        # add edges based on class relationships
        for n in exceptions:
            if n.__base__ in exceptions:
                exceptions.add_edge(n.__base__, n)

        sorted_exceptions = nx.topological_sort(exceptions)
        mod.add_to_init([
            # register exception only if they can be raise from C++ world to
            # Python world. Preprocessors variables are set only if deps
            # analysis detect that this exception can be raised
            Line('#ifdef PYTHONIC_BUILTIN_%s_HPP\n'
                 'boost::python::register_exception_translator<'
                 'pythonic::types::%s>(&pythonic::translate_%s);\n'
                 '#endif' % (n.__name__.upper(), n.__name__, n.__name__)
                 ) for n in sorted_exceptions])

        for function_name, signatures in specs.iteritems():
            internal_func_name = renamings.get(function_name,
                                               function_name)
            for sigid, signature in enumerate(signatures):
                numbered_function_name = "{0}{1}".format(internal_func_name,
                                                         sigid)
                arguments_types = [pytype_to_ctype(t) for t in signature]
                has_arguments = HasArgument(internal_func_name).visit(ir)
                arguments = ["a{0}".format(i)
                             for i in xrange(len(arguments_types))]
                name_fmt = pythran_ward + "{0}::{1}::type{2}"
                args_list = ", ".join(arguments_types)
                specialized_fname = name_fmt.format(module_name,
                                                    internal_func_name,
                                                    "<{0}>".format(args_list)
                                                    if has_arguments else "")
                result_type = ("typename std::remove_cv<"
                               "typename std::remove_reference"
                               "<typename {0}::result_type>::type"
                               ">::type").format(specialized_fname)
                mod.add_to_init(
                    [Statement("pythonic::python_to_pythran<{0}>()".format(t))
                     for t in _extract_all_constructed_types(signature)])
                mod.add_to_init([Statement(
                    "pythonic::pythran_to_python<{0}>()".format(result_type))])
                mod.add_function(
                    FunctionBody(
                        FunctionDeclaration(
                            Value(
                                result_type,
                                numbered_function_name),
                            [Value(t, a)
                             for t, a in zip(arguments_types, arguments)]),
                        Block([Statement("return {0}()({1})".format(
                            pythran_ward + '{0}::{1}'.format(
                                module_name, internal_func_name),
                            ', '.join(arguments)))])
                    ),
                    function_name
                )
        # call __init__() to execute top-level statements
        init_call = '::'.join([pythran_ward + module_name, '__init__()()'])
        mod.add_to_init([Statement(init_call)])
    return mod


def compile_cxxfile(cxxfile, module_so=None, **kwargs):
    '''c++ file -> native module
    Return the filename of the produced shared library
    Raises CompileError on failure

    '''
    # FIXME: not sure about overriding the user defined compiler here...
    compiler = kwargs.get('cxx', cfg.get('user', 'cxx'))

    _cppflags = cppflags() + kwargs.get('cppflags', [])
    _cxxflags = cxxflags() + kwargs.get('cxxflags', [])
    _ldflags = ldflags() + kwargs.get('ldflags', [])

    # Get output filename from input filename if not set
    module_so = module_so or (os.path.splitext(cxxfile)[0] + ".so")
    try:
        cmd = ([compiler, cxxfile]
               + _cppflags
               + _cxxflags
               + ["-shared", "-o", module_so]
               + _ldflags)
        logger.info("Command line: " + _format_cmdline(cmd))
        output = check_output(cmd, stderr=STDOUT)
    except CalledProcessError as e:
        raise CompileError(e.cmd, e.output)
    logger.info("Generated module: " + module_so)
    logger.info("Output: " + output)

    return module_so


def compile_cxxcode(cxxcode, module_so=None, keep_temp=False,
                    **kwargs):
    '''c++ code (string) -> temporary file -> native module.
    Returns the generated .so.

    '''

    # Get a temporary C++ file to compile
    fd, fdpath = _get_temp(cxxcode)
    module_so = compile_cxxfile(fdpath, module_so, **kwargs)
    if not keep_temp:
        # remove tempfile
        os.remove(fdpath)
    else:
        logger.warn("Keeping temporary generated file:" + fdpath)

    return module_so


def compile_pythrancode(module_name, pythrancode, specs=None,
                        opts=None, cpponly=False, module_so=None,
                        **kwargs):
    '''Pythran code (string) -> c++ code -> native module
    Returns the generated .so (or .cpp if `cpponly` is set to true).

    '''

    # Autodetect the Pythran spec if not given as parameter
    from spec import spec_parser
    if specs is None:
        specs = spec_parser(pythrancode)

    # Generate C++, get a BoostPythonModule object
    module = generate_cxx(module_name, pythrancode, specs, opts)

    if cpponly:
        # User wants only the C++ code
        _, output_file = _get_temp(str(module))
        if module_so:
            shutil.move(output_file, module_so)
            output_file = module_so
        logger.info("Generated C++ source file: " + output_file)
    else:
        # Compile to binary
        output_file = compile_cxxcode(str(module.generate()),
                                      module_so=module_so,
                                      **kwargs)

    return output_file


def compile_pythranfile(file_path, module_so=None, module_name=None,
                        cpponly=False, **kwargs):
    '''Pythran file -> c++ file -> native module
    Returns the generated .so (or .cpp if `cpponly` is set to true).

    '''
    if not module_so:
        # derive module name from input file name
        basedir, basename = os.path.split(file_path)
        module_name = module_name or os.path.splitext(basename)[0]

        # derive destination from file name
        module_so = os.path.join(basedir, module_name + ".so")
    else:
        # derive module name from destination module_so name
        _, basename = os.path.split(module_so)
        module_name = module_name or os.path.splitext(basename)[0]

    dl = compile_pythrancode(module_name, file(file_path).read(),
                             module_so=module_so, cpponly=cpponly, **kwargs)
    return module_so


def test_compile():
    '''Simple passthrough compile test.
    May raises CompileError Exception.

    '''
    module_so = compile_cxxcode("\n".join([
        "#define BOOST_PYTHON_MAX_ARITY 4",
        "#include <pythonic/core.hpp>"
        ]))
    module_so and os.remove(module_so)

########NEW FILE########
__FILENAME__ = expand_builtins
"""
ExpandBuiltins replaces builtins by their full paths
"""
import ast
from pythran.analyses import Globals, Locals
from pythran.passmanager import Transformation
from pythran.tables import modules
from pythran.syntax import PythranSyntaxError


class ExpandBuiltins(Transformation):
    '''
    Expands all builtins into full paths.
    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(): return list()")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ExpandBuiltins, node)
    >>> print pm.dump(backend.Python, node)
    def foo():
        return __builtin__.list()
    '''

    def __init__(self):
        Transformation.__init__(self, Locals, Globals)

    def visit_Name(self, node):
        s = node.id
        if (isinstance(node.ctx, ast.Load)
                and s not in self.locals[node]
                and s not in self.globals
                and s in modules['__builtin__']):
            if s == 'getattr':
                raise PythranSyntaxError("You fool! Trying a getattr?", node)
            return ast.Attribute(
                ast.Name('__builtin__', ast.Load()),
                s,
                node.ctx)
        else:
            return node

########NEW FILE########
__FILENAME__ = expand_imports
"""
ExpandImports replaces imports by their full paths
"""
import ast
from pythran.passmanager import Transformation
from pythran.tables import namespace


class ExpandImports(Transformation):
    '''
    Expands all imports into full paths.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("from math import cos ; cos(2)")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ExpandImports, node)
    >>> print pm.dump(backend.Python, node)
    import math as pythonic::math
    math.cos(2)
    '''

    def __init__(self):
        Transformation.__init__(self)
        self.imports = set()
        self.symbols = dict()

    def visit_Module(self, node):
        node.body = [k for k in (self.visit(n) for n in node.body) if k]
        imports = [ast.Import([ast.alias(i, namespace + "::" + i)])
                   for i in self.imports]
        node.body = imports + node.body
        ast.fix_missing_locations(node)
        return node

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
            self.symbols[alias.asname or alias.name] = (alias.name,)
        return None

    def visit_ImportFrom(self, node):
        self.imports.add(node.module)
        for alias in node.names:
            self.symbols[alias.asname or alias.name] = (
                node.module,
                alias.name,
                )
        return None

    def visit_FunctionDef(self, node):
        self.symbols.pop(node.name, None)
        gsymbols = self.symbols.copy()
        [self.symbols.pop(arg.id, None) for arg in node.args.args]
        node.body = [k for k in (self.visit(n) for n in node.body) if k]
        self.symbols = gsymbols
        return node

    def visit_Assign(self, node):
        new_node = self.generic_visit(node)
        [self.symbols.pop(t.id, None)
         for t in new_node.targets if isinstance(t, ast.Name)]
        return new_node

    def visit_Name(self, node):
        if node.id in self.symbols:
            new_node = reduce(
                lambda v, o: ast.Attribute(v, o, ast.Load()),
                self.symbols[node.id][1:],
                ast.Name(self.symbols[node.id][0], ast.Load())
                )
            new_node.ctx = node.ctx
            ast.copy_location(new_node, node)
            return new_node
        return node

########NEW FILE########
__FILENAME__ = expand_import_all
"""
ExpandImportAll replaces import * by all their modules
"""
import ast
from pythran.passmanager import Transformation
from pythran.tables import modules


class ExpandImportAll(Transformation):
    '''
    Expands all import when '*' detected

    >>> import ast, passmanager, backend
    >>> node = ast.parse("from math import *")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(ExpandImportAll, node)
    >>> print pm.dump(backend.Python, node)
    from math import asinh, atan2, fmod, atan, isnan, factorial, pow, \
copysign, cos, cosh, ldexp, hypot, isinf, floor, sinh, acosh, tan, ceil, exp, \
trunc, asin, expm1, e, log, fabs, tanh, log10, atanh, radians, sqrt, frexp, \
lgamma, erf, erfc, modf, degrees, acos, pi, log1p, sin, gamma
    '''

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == '*':
                node.names.pop()
                node.names.extend(ast.alias(fname, None)
                                  for fname in modules[node.module])
        return node

########NEW FILE########
__FILENAME__ = extract_top_level_stmts
"""
ExtractTopLevelStmts moves top level statements into __init__
"""
import ast
from pythran.passmanager import Transformation


class ExtractTopLevelStmts(Transformation):
    """
    Turns top level statements into __init__.
    """

    TYPEDEFS = (ast.ClassDef, ast.FunctionDef, ast.Import, ast.ImportFrom)

    def visit_Module(self, node):
        module_body = list()
        init_body = list()
        for stmt in node.body:
            if type(stmt) in ExtractTopLevelStmts.TYPEDEFS:
                module_body.append(stmt)
            else:
                init_body.append(stmt)
        init = ast.FunctionDef('__init__',
                               ast.arguments([], None, None, []),
                               init_body,
                               [])
        module_body.append(init)
        node.body = module_body
        return node

########NEW FILE########
__FILENAME__ = false_polymorphism
"""
FalsePolymorphism rename variable if possible to avoid false polymorphism
"""
import ast
from pythran.passmanager import Transformation
from pythran.analyses import UseDefChain, UseOMP, Globals, Identifiers


class FalsePolymorphism(Transformation):
    """
    Rename variable when possible to avoid false polymorphism.
    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(): a = 12; a = 'babar'")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(FalsePolymorphism, node)
    >>> print pm.dump(backend.Python, node)
    def foo():
        a = 12
        a_ = 'babar'
    """
    def __init__(self):
        super(FalsePolymorphism, self).__init__(UseDefChain, UseOMP)

    def visit_FunctionDef(self, node):
        #function using openmp are ignored
        if not self.use_omp:
            self.identifiers = self.passmanager.gather(Identifiers, node,
                                                       self.ctx)
            for name, udgraph in self.use_def_chain.iteritems():
                group_variable = list()
                while udgraph:
                    e = udgraph.nodes_iter().next()
                    to_change = set()
                    to_analyse_pred = set([e])
                    to_analyse_succ = set()
                    while to_analyse_pred or to_analyse_succ:
                        if to_analyse_pred:
                            n = to_analyse_pred.pop()
                            to_change.add(n)
                            to_analyse_succ.update(udgraph.successors(n))
                            to_analyse_succ -= to_change
                        else:
                            n = to_analyse_succ.pop()
                            if (udgraph.node[n]['action'] == 'U' or
                                    udgraph.node[n]['action'] == 'UD'):
                                to_change.add(n)
                                to_analyse_succ.update(udgraph.successors(n))
                                to_analyse_succ -= to_change
                        if (udgraph.node[n]['action'] == 'U' or
                                udgraph.node[n]['action'] == 'UD'):
                            to_analyse_pred.update(udgraph.predecessors(n))
                            to_analyse_pred -= to_change
                    nodes_to_change = [udgraph.node[k]['name']
                                       for k in to_change]
                    group_variable.append(nodes_to_change)
                    udgraph.remove_nodes_from(to_change)
                if len(group_variable) > 1:
                    self.identifiers.remove(name)
                    for group in group_variable:
                        while name in self.identifiers:
                            name += "_"
                        for var in group:
                            var.id = name
                        self.identifiers.add(name)
        return node

########NEW FILE########
__FILENAME__ = normalize_compare
"""
NormalizeCompare turns complex compare into function calls
"""
import ast
from pythran.analyses import ImportedIds
from pythran.passmanager import Transformation


class NormalizeCompare(Transformation):
    '''
    Turns multiple compare into a function with proper temporaries.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(a): return 0 < a + 1 < 3")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(NormalizeCompare, node)
    >>> print pm.dump(backend.Python, node)
    def foo(a):
        return foo_compare0(a)
    def foo_compare0(a):
        $0 = 0
        $1 = (a + 1)
        if ($0 < $1):
            pass
        else:
            return 0
        $2 = 3
        if ($1 < $2):
            pass
        else:
            return 0
        return 1
    '''

    def visit_Module(self, node):
        self.compare_functions = list()
        self.generic_visit(node)
        node.body.extend(self.compare_functions)
        return node

    def visit_FunctionDef(self, node):
        self.prefix = node.name
        self.generic_visit(node)
        return node

    def visit_Compare(self, node):
        node = self.generic_visit(node)
        if len(node.ops) > 1:
            # in case we have more than one compare operator
            # we generate an auxillary function
            # that lazily evaluates the needed parameters
            imported_ids = self.passmanager.gather(ImportedIds, node, self.ctx)
            imported_ids = sorted(imported_ids)
            binded_args = [ast.Name(i, ast.Load()) for i in imported_ids]

            # name of the new function
            forged_name = "{0}_compare{1}".format(self.prefix,
                                                  len(self.compare_functions))

            # call site
            call = ast.Call(ast.Name(forged_name, ast.Load()),
                            binded_args, [], None, None)

            # new function
            arg_names = [ast.Name(i, ast.Param()) for i in imported_ids]
            args = ast.arguments(arg_names, None, None, [])

            body = []  # iteratively fill the body (yeah, feel your body!)
            body.append(ast.Assign([ast.Name('$0', ast.Store())], node.left))
            for i, exp in enumerate(node.comparators):
                body.append(ast.Assign([ast.Name('${}'.format(i+1),
                                                 ast.Store())],
                                       exp))
                cond = ast.Compare(ast.Name('${}'.format(i), ast.Load()),
                                   [node.ops[i]],
                                   [ast.Name('${}'.format(i+1), ast.Load())])
                body.append(ast.If(cond,
                                   [ast.Pass()],
                                   [ast.Return(ast.Num(0))]))
            body.append(ast.Return(ast.Num(1)))

            forged_fdef = ast.FunctionDef(forged_name, args, body, [])
            self.compare_functions.append(forged_fdef)

            return call
        else:
            return node

########NEW FILE########
__FILENAME__ = normalize_exception
"""
NormalizeException simplifies try blocks
"""
import ast
from pythran.passmanager import Transformation


class NormalizeException(Transformation):
    '''
    Transform else statement in try except block in nested try except.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("try:print 't'\\nexcept: print 'x'\\nelse: print 'e'")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(NormalizeException, node)
    >>> print pm.dump(backend.Python, node)
    try:
        print 't'
        try:
            print 'e'
        except:
            pass
    except:
        print 'x'
    '''
    def visit_TryExcept(self, node):
        if node.orelse:
            node.body.append(
                ast.TryExcept(
                    node.orelse,
                    [ast.ExceptHandler(None, None, [ast.Pass()])],
                    []
                    )
                )
            node.orelse = []
        return node

    def visit_TryFinally(self, node):
        node.body.extend(node.finalbody)
        node.finalbody.append(ast.Raise(None, None, None))
        return ast.TryExcept(
            node.body,
            [ast.ExceptHandler(None, None, node.finalbody)],
            [])

########NEW FILE########
__FILENAME__ = normalize_identifiers
"""
NormalizeIdentifiers prevents conflicts with c++ keywords
"""
import ast
from pythran.analyses import Identifiers
from pythran.passmanager import Transformation
from pythran.tables import cxx_keywords


class NormalizeIdentifiers(Transformation):
    '''
    Prevents naming conflict with c++ keywords by appending extra '_'
    to conflicting names.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def namespace(union):pass")
    >>> pm = passmanager.PassManager("test")
    >>> d = pm.apply(NormalizeIdentifiers, node)
    >>> print pm.dump(backend.Python, node)
    def namespace_(union_):
        pass
    '''

    def __init__(self):
        self.renamings = dict()
        Transformation.__init__(self, Identifiers)

    def rename(self, name):
        if name not in self.renamings:
            new_name = name
            while new_name in self.identifiers:
                new_name += "_"
            self.renamings[name] = new_name
        return self.renamings[name]

    def run(self, node, ctx):
        super(NormalizeIdentifiers, self).run(node, ctx)
        return self.renamings

    def visit_Name(self, node):
        if node.id in cxx_keywords:
            node.id = self.rename(node.id)
        return node

    def visit_FunctionDef(self, node):
        if node.name in cxx_keywords:
            node.name = self.rename(node.name)
        self.visit(node.args)
        [self.visit(n) for n in node.body]
        return node

    def visit_alias(self, node):
        if node.name in cxx_keywords:
            node.name = self.rename(node.name)
        if node.asname:
            if node.asname in cxx_keywords:
                node.asname = self.rename(node.asname)
        return node

    def visit_ImportFrom(self, node):
        self.generic_visit(node)
        if node.module and node.module in cxx_keywords:
            node.module = self.rename(node.module)
        return node

    def visit_Attribute(self, node):
        self.visit(node.value)
        if node.attr in cxx_keywords:
            node.attr += "_"  # cross fingers
        # Always true as long as we don't have custom classes.
        return node

########NEW FILE########
__FILENAME__ = normalize_method_calls
"""
NormalizeMethodCalls turns built in method calls into function calls
"""
import ast
from pythran.analyses import Globals
from pythran.passmanager import Transformation
from pythran.tables import attributes, functions, methods, modules, namespace


class NormalizeMethodCalls(Transformation):
    '''
    Turns built in method calls into function calls.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("l.append(12)")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(NormalizeMethodCalls, node)
    >>> print pm.dump(backend.Python, node)
    __list__.append(l, 12)
    '''

    def __init__(self):
        Transformation.__init__(self, Globals)
        self.imports = set()
        self.to_import = set()

    def visit_Module(self, node):
        """
            When we normalize call, we need to add correct import for method
            to function transformation.

            a.max()

            for numpy array will become:

            numpy.max(a)

            so we have to import numpy.
        """
        self.generic_visit(node)
        new_imports = self.to_import - self.globals
        imports = [ast.Import(names=[ast.alias(name=mod,
                                     asname=namespace + "::" + mod)])
                   for mod in new_imports]
        node.body = imports + node.body
        return node

    def visit_FunctionDef(self, node):
        self.imports = self.globals.copy()
        [self.imports.discard(arg.id) for arg in node.args.args]
        self.generic_visit(node)
        return node

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.asname or alias.name)
        return node

    def visit_Assign(self, node):
        n = self.generic_visit(node)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.imports.discard(t.id)
        return n

    def visit_For(self, node):
        node.iter = self.visit(node.iter)
        if isinstance(node.target, ast.Name):
            self.imports.discard(node.target.id)
        if node.body:
            node.body = [self.visit(n) for n in node.body]
        if node.orelse:
            node.orelse = [self.visit(n) for n in node.orelse]
        return node

    def visit_Attribute(self, node):
        node = self.generic_visit(node)
        # storing in an attribute -> not a getattr
        if type(node.ctx) is not ast.Load:
            return node
        # method name -> not a getattr
        elif node.attr in methods:
            return node
        # imported module -> not a getattr
        elif type(node.value) is ast.Name and node.value.id in self.imports:
            return node
        # not listed as attributed -> not a getattr
        elif node.attr not in attributes:
            return node
        # A getattr !
        else:
            return ast.Call(ast.Attribute(ast.Name('__builtin__', ast.Load()),
                                          'getattr',
                                          ast.Load()),
                            [node.value, ast.Str(node.attr.upper())],
                            [], None, None)

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if isinstance(node.func, ast.Attribute):
            lhs = node.func.value
            if node.func.attr in methods:
                isname = isinstance(lhs, ast.Name)
                ispath = isname or isinstance(lhs, ast.Attribute)
                if not ispath or (isname and lhs.id not in self.imports):
                    node.args.insert(0, node.func.value)
                    mod = methods[node.func.attr][0]
                    self.to_import.add(mod)
                    node.func = ast.Attribute(
                        ast.Name(mod, ast.Load()),
                        node.func.attr,
                        ast.Load())
            if node.func.attr in methods or node.func.attr in functions:
                def renamer(v):
                    name = '__{0}__'.format(v)
                    if name in modules:
                        return name
                    else:
                        name += '_'
                        if name in modules:
                            return name
                    return v

                def rec(n):
                    if isinstance(n, ast.Attribute):
                        n.attr = renamer(n.attr)
                        rec(n.value)
                    elif isinstance(n, ast.Name):
                        n.id = renamer(n.id)
                rec(node.func.value)

        return node

########NEW FILE########
__FILENAME__ = normalize_return
"""
NormalizeReturn adds return statement where relevant
"""
import ast
from pythran.analyses import CFG, YieldPoints
from pythran.passmanager import Transformation


class NormalizeReturn(Transformation):
    '''
    Adds Return statement when they are implicit,
    and adds the None return value when not set

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(y): print y")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(NormalizeReturn, node)
    >>> print pm.dump(backend.Python, node)
    def foo(y):
        print y
        return __builtin__.None
    '''

    def __init__(self):
        super(NormalizeReturn, self).__init__(CFG)

    def visit_FunctionDef(self, node):
        self.yield_points = self.passmanager.gather(YieldPoints, node)
        map(self.visit, node.body)
        # Look for nodes that have no successors
        for n in self.cfg.predecessors(None):
            if type(n) not in (ast.Return, ast.Raise):
                if self.yield_points:
                    node.body.append(ast.Return(None))
                else:
                    none = ast.Attribute(ast.Name("__builtin__", ast.Load()),
                                         'None', ast.Load())
                    node.body.append(ast.Return(none))
                break

        return node

    def visit_Return(self, node):
        if not node.value and not self.yield_points:
            none = ast.Attribute(ast.Name("__builtin__", ast.Load()),
                                 'None', ast.Load())
            node.value = none
        return node

########NEW FILE########
__FILENAME__ = normalize_tuples
"""
NormalizeTuples removes implicit variable -> tuple conversion
"""
import ast
from pythran.passmanager import Transformation


class _ConvertToTuple(ast.NodeTransformer):
    def __init__(self, tuple_id, renamings):
        self.tuple_id = tuple_id
        self.renamings = renamings

    def visit_Name(self, node):
        if node.id in self.renamings:
            nnode = reduce(
                lambda x, y: ast.Subscript(
                    x,
                    ast.Index(ast.Num(y)),
                    ast.Load()),
                self.renamings[node.id],
                ast.Name(self.tuple_id, ast.Load())
                )
            nnode.ctx = node.ctx
            return nnode
        return node


class NormalizeTuples(Transformation):
    """
    Remove implicit tuple -> variable conversion.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("a=(1,2.) ; i,j = a")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(NormalizeTuples, node)
    >>> print pm.dump(backend.Python, node)
    a = (1, 2.0)
    if 1:
        __tuple10 = a
        i = __tuple10[0]
        j = __tuple10[1]
    """
    tuple_name = "__tuple"

    def __init__(self):
        self.counter = 0
        Transformation.__init__(self)

    def traverse_tuples(self, node, state, renamings):
        if isinstance(node, ast.Name):
            if state:
                renamings[node.id] = state
        elif isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            [self.traverse_tuples(n, state + (i,), renamings)
             for i, n in enumerate(node.elts)]
        elif type(node) in (ast.Subscript, ast.Attribute):
            if state:
                renamings[node] = state
        else:
            raise NotImplementedError

    def visit_comprehension(self, node):
        renamings = dict()
        self.traverse_tuples(node.target, (), renamings)
        if renamings:
            self.counter += 1
            return ("{0}{1}".format(
                NormalizeTuples.tuple_name,
                self.counter),
                renamings)
        else:
            return node

    def visit_AnyComp(self, node, *fields):
        for field in fields:
            setattr(node, field, self.visit(getattr(node, field)))
        generators = map(self.visit, node.generators)
        nnode = node
        for i, g in enumerate(generators):
            if isinstance(g, tuple):
                gtarget = "{0}{1}".format(g[0], i)
                nnode.generators[i].target = ast.Name(
                    gtarget,
                    nnode.generators[i].target.ctx)
                nnode = _ConvertToTuple(gtarget, g[1]).visit(nnode)
        for field in fields:
            setattr(node, field, getattr(nnode, field))
        node.generators = nnode.generators
        return node

    def visit_ListComp(self, node):
        return self.visit_AnyComp(node, 'elt')

    def visit_SetComp(self, node):
        return self.visit_AnyComp(node, 'elt')

    def visit_DictComp(self, node):
        return self.visit_AnyComp(node, 'key', 'value')

    def visit_GeneratorExp(self, node):
        return self.visit_AnyComp(node, 'elt')

    def visit_Lambda(self, node):
        self.generic_visit(node)
        for i, arg in enumerate(node.args.args):
            renamings = dict()
            self.traverse_tuples(arg, (), renamings)
            if renamings:
                self.counter += 1
                nname = "{0}{1}".format(
                    NormalizeTuples.tuple_name,
                    self.counter)
                node.args.args[i] = ast.Name(nname, ast.Param())
                node.body = _ConvertToTuple(nname, renamings).visit(node.body)
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        extra_assign = [node]
        for i, t in enumerate(node.targets):
            if isinstance(t, ast.Tuple) or isinstance(t, ast.List):
                renamings = dict()
                self.traverse_tuples(t, (), renamings)
                if renamings:
                    self.counter += 1
                    gtarget = "{0}{1}{2}".format(
                        NormalizeTuples.tuple_name,
                        self.counter,
                        i)
                    node.targets[i] = ast.Name(gtarget, node.targets[i].ctx)
                    for rename, state in sorted(renamings.iteritems()):
                        nnode = reduce(
                            lambda x, y: ast.Subscript(
                                x,
                                ast.Index(ast.Num(y)),
                                ast.Load()),
                            state,
                            ast.Name(gtarget, ast.Load()))
                        if isinstance(rename, str):
                            extra_assign.append(
                                ast.Assign(
                                    [ast.Name(rename, ast.Store())],
                                    nnode))
                        else:
                            extra_assign.append(ast.Assign([rename], nnode))
        return (ast.If(ast.Num(1), extra_assign, [])
                if len(extra_assign) > 1
                else extra_assign)

    def visit_For(self, node):
        target = node.target
        if isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            renamings = dict()
            self.traverse_tuples(target, (), renamings)
            if renamings:
                self.counter += 1
                gtarget = "{0}{1}".format(
                    NormalizeTuples.tuple_name,
                    self.counter
                    )
                node.target = ast.Name(gtarget, node.target.ctx)
                for rename, state in sorted(renamings.iteritems()):
                    nnode = reduce(
                        lambda x, y: ast.Subscript(
                            x,
                            ast.Index(ast.Num(y)),
                            ast.Load()),
                        state,
                        ast.Name(gtarget, ast.Load()))
                    if isinstance(rename, str):
                        node.body.insert(0,
                                         ast.Assign(
                                             [ast.Name(rename, ast.Store())],
                                             nnode)
                                         )
                    else:
                        node.body.insert(0, ast.Assign([rename], nnode))

        self.generic_visit(node)
        return node

########NEW FILE########
__FILENAME__ = remove_comprehension
"""
RemoveComprehension turns list comprehension into function calls
"""
import ast
from pythran import metadata
from pythran.analyses import ImportedIds
from pythran.passmanager import Transformation


class RemoveComprehension(Transformation):
    """
    Turns all list comprehension from a node into new function calls.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("[x*x for x in (1,2,3)]")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(RemoveComprehension, node)
    >>> print pm.dump(backend.Python, node)
    list_comprehension0()
    def list_comprehension0():
        __target = __builtin__.list()
        for x in (1, 2, 3):
            __list__.append(__target, (x * x))
        return __target
    """

    def __init__(self):
        self.count = 0
        Transformation.__init__(self)

    def nest_reducer(self, x, g):
        def wrap_in_ifs(node, ifs):
            return reduce(lambda n, if_: ast.If(if_, [n], []), ifs, node)
        metadata.add(g.target, metadata.LocalVariable())
        return ast.For(g.target, g.iter, [wrap_in_ifs(x, g.ifs)], [])

    def visit_AnyComp(self, node, comp_type, comp_module, comp_method):
        node.elt = self.visit(node.elt)
        name = "{0}_comprehension{1}".format(comp_type, self.count)
        self.count += 1
        args = self.passmanager.gather(ImportedIds, node, self.ctx)
        self.count_iter = 0

        starget = "__target"
        body = reduce(self.nest_reducer,
                      reversed(node.generators),
                      ast.Expr(
                          ast.Call(
                              ast.Attribute(
                                  ast.Name(comp_module, ast.Load()),
                                  comp_method,
                                  ast.Load()),
                              [ast.Name(starget, ast.Load()), node.elt],
                              [],
                              None,
                              None
                              )
                          )
                      )
        # add extra metadata to this node
        metadata.add(body, metadata.Comprehension(starget))
        init = ast.Assign(
            [ast.Name(starget, ast.Store())],
            ast.Call(
                ast.Attribute(
                    ast.Name('__builtin__', ast.Load()),
                    comp_type,
                    ast.Load()
                    ),
                [], [], None, None)
            )
        result = ast.Return(ast.Name(starget, ast.Load()))
        sargs = sorted(ast.Name(arg, ast.Param()) for arg in args)
        fd = ast.FunctionDef(name,
                             ast.arguments(sargs, None, None, []),
                             [init, body, result],
                             [])
        self.ctx.module.body.append(fd)
        return ast.Call(
            ast.Name(name, ast.Load()),
            [ast.Name(arg.id, ast.Load()) for arg in sargs],
            [],
            None,
            None
            )  # no sharing !

    def visit_ListComp(self, node):
        return self.visit_AnyComp(node, "list", "__list__", "append")

    def visit_SetComp(self, node):
        return self.visit_AnyComp(node, "set", "__set__", "add")

    def visit_DictComp(self, node):
        # this is a quickfix to match visit_AnyComp signature
        # potential source of improvement there!
        node.elt = ast.List(
            [ast.Tuple([node.key, node.value], ast.Load())],
            ast.Load()
            )
        return self.visit_AnyComp(node, "dict", "__dispatch__", "update")

    def visit_GeneratorExp(self, node):
        node.elt = self.visit(node.elt)
        name = "generator_expression{0}".format(self.count)
        self.count += 1
        args = self.passmanager.gather(ImportedIds, node, self.ctx)
        self.count_iter = 0

        body = reduce(self.nest_reducer,
                      reversed(node.generators),
                      ast.Expr(ast.Yield(node.elt))
                      )

        sargs = sorted(ast.Name(arg, ast.Param()) for arg in args)
        fd = ast.FunctionDef(name,
                             ast.arguments(sargs, None, None, []),
                             [body],
                             [])
        self.ctx.module.body.append(fd)
        return ast.Call(
            ast.Name(name, ast.Load()),
            [ast.Name(arg.id, ast.Load()) for arg in sargs],
            [],
            None,
            None
            )  # no sharing !

########NEW FILE########
__FILENAME__ = remove_lambdas
"""
RemoveLambdas turns lambda into regular functions
"""
import ast
from copy import copy
from pythran.analyses import GlobalDeclarations, ImportedIds
from pythran.passmanager import Transformation
from pythran.tables import modules


class _LambdaRemover(Transformation):

    def __init__(self, pm, name, ctx, lambda_functions, imports):
        Transformation.__init__(self)
        self.passmanager = pm
        self.ctx = ctx
        self.prefix = name
        self.lambda_functions = lambda_functions
        self.imports = imports
        self.global_declarations = pm.gather(GlobalDeclarations, ctx.module)

    def visit_Lambda(self, node):
        if modules['functools'] not in self.global_declarations.values():
            import_ = ast.Import([ast.alias('functools', None)])
            self.imports.append(import_)
            self.global_declarations['functools'] = modules['functools']

        self.generic_visit(node)
        forged_name = "{0}_lambda{1}".format(
            self.prefix,
            len(self.lambda_functions))

        ii = self.passmanager.gather(ImportedIds, node, self.ctx)
        ii.difference_update(self.lambda_functions)  # remove current lambdas

        binded_args = [ast.Name(iin, ast.Load()) for iin in sorted(ii)]
        former_nbargs = len(node.args.args)
        node.args.args = ([ast.Name(iin, ast.Param()) for iin in sorted(ii)]
                          + node.args.args)
        forged_fdef = ast.FunctionDef(
            forged_name,
            copy(node.args),
            [ast.Return(node.body)],
            [])
        self.lambda_functions.append(forged_fdef)
        proxy_call = ast.Name(forged_name, ast.Load())
        if binded_args:
            return ast.Call(
                ast.Attribute(
                    ast.Name('functools', ast.Load()),
                    "partial",
                    ast.Load()
                    ),
                [proxy_call] + binded_args,
                [],
                None,
                None)
        else:
            return proxy_call


class RemoveLambdas(Transformation):
    '''
    Turns lambda into top-level functions.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(y): lambda x:y+x")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(RemoveLambdas, node)
    >>> print pm.dump(backend.Python, node)
    import functools
    def foo(y):
        functools.partial(foo_lambda0, y)
    def foo_lambda0(y, x):
        return (y + x)
    '''

    def visit_Module(self, node):
        self.lambda_functions = list()
        self.imports = list()
        self.generic_visit(node)
        node.body = self.imports + node.body + self.lambda_functions
        return node

    def visit_FunctionDef(self, node):
        lr = _LambdaRemover(self.passmanager, node.name, self.ctx,
                            self.lambda_functions, self.imports)
        node.body = map(lr.visit, node.body)
        return node

########NEW FILE########
__FILENAME__ = remove_nested_functions
"""
RemoveNestedFunctions turns nested function into top-level functions
"""
import ast
from pythran.analyses import GlobalDeclarations, ImportedIds
from pythran.passmanager import Transformation
from pythran.tables import modules


class _NestedFunctionRemover(Transformation):
    def __init__(self, pm, ctx):
        Transformation.__init__(self)
        self.ctx = ctx
        self.passmanager = pm
        self.global_declarations = pm.gather(GlobalDeclarations, ctx.module)

    def visit_FunctionDef(self, node):
        if modules['functools'] not in self.global_declarations.values():
            import_ = ast.Import([ast.alias('functools', None)])
            self.ctx.module.body.insert(0, import_)
            self.global_declarations['functools'] = modules['functools']

        self.ctx.module.body.append(node)

        former_name = node.name
        former_nbargs = len(node.args.args)
        new_name = "pythran_{0}".format(former_name)

        ii = self.passmanager.gather(ImportedIds, node, self.ctx)
        binded_args = [ast.Name(iin, ast.Load()) for iin in sorted(ii)]
        node.args.args = ([ast.Name(iin, ast.Param()) for iin in sorted(ii)]
                          + node.args.args)

        class Renamer(ast.NodeTransformer):
            def visit_Call(self, node):
                self.generic_visit(node)
                if (isinstance(node.func, ast.Name)
                        and node.func.id == former_name):
                    node.func.id = new_name
                    node.args = (
                        [ast.Name(iin, ast.Load()) for iin in sorted(ii)]
                        + node.args
                        )
                return node
        Renamer().visit(node)

        node.name = new_name
        proxy_call = ast.Name(new_name, ast.Load())

        new_node = ast.Assign(
            [ast.Name(former_name, ast.Store())],
            ast.Call(
                ast.Attribute(
                    ast.Name('functools', ast.Load()),
                    "partial",
                    ast.Load()
                    ),
                [proxy_call] + binded_args,
                [],
                None,
                None
                )
            )

        self.generic_visit(node)
        return new_node


class RemoveNestedFunctions(Transformation):
    '''
    Replace nested function by top-level functions
    and a call to a bind intrinsic that
    generates a local function with some arguments binded.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(x):\\n def bar(y): return x+y\\n bar(12)")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(RemoveNestedFunctions, node)
    >>> print pm.dump(backend.Python, node)
    import functools
    def foo(x):
        bar = functools.partial(pythran_bar, x)
        bar(12)
    def pythran_bar(x, y):
        return (x + y)
    '''

    def visit_Module(self, node):
        map(self.visit, node.body)
        return node

    def visit_FunctionDef(self, node):
        nfr = _NestedFunctionRemover(self.passmanager, self.ctx)
        node.body = map(nfr.visit, node.body)
        return node

########NEW FILE########
__FILENAME__ = unshadow_parameters
"""
UnshadowParameters prevents the shadow parameter phenomenon
"""
import ast
from pythran.analyses import Identifiers
from pythran.passmanager import Transformation


class UnshadowParameters(Transformation):
    '''
    Prevents parameter shadowing by creating new variable.

    >>> import ast, passmanager, backend
    >>> node = ast.parse("def foo(a): a=None")
    >>> pm = passmanager.PassManager("test")
    >>> node = pm.apply(UnshadowParameters, node)
    >>> print pm.dump(backend.Python, node)
    def foo(a):
        a_ = a
        a_ = None
    '''

    def __init__(self):
        Transformation.__init__(self, Identifiers)

    def visit_FunctionDef(self, node):
        self.argsid = {arg.id for arg in node.args.args}
        self.renaming = {}
        [self.visit(n) for n in node.body]
        # do it twice to make sure all renaming are done
        [self.visit(n) for n in node.body]
        for k, v in self.renaming.iteritems():
            node.body.insert(
                0,
                ast.Assign(
                    [ast.Name(v, ast.Store())],
                    ast.Name(k, ast.Load())
                    )
                )
        return node

    def update(self, node):
        if isinstance(node, ast.Name) and node.id in self.argsid:
            if node.id not in self.renaming:
                new_name = node.id
                while new_name in self.identifiers:
                    new_name = new_name + "_"
                self.renaming[node.id] = new_name

    def visit_Assign(self, node):
        map(self.update, node.targets)
        try:
            self.generic_visit(node)
        except AttributeError:
            pass
        return node

    def visit_AugAssign(self, node):
        self.update(node.target)
        return self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.renaming:
            node.id = self.renaming[node.id]
        return node

########NEW FILE########
__FILENAME__ = typing
'''
This module performs the return type inference, according to symbolic types,
   It then reorders function declarations according to the return type deps.
    * type_all generates a node -> type binding
'''

import ast
from numpy import ndarray
import networkx as nx

from tables import (pytype_to_ctype_table, operator_to_lambda, modules,
                    methods, functions)
from analyses import (GlobalDeclarations, YieldPoints, LocalDeclarations,
                      OrderedGlobalDeclarations, StrictAliases,
                      LazynessAnalysis)
from passmanager import ModuleAnalysis, Transformation
from syntax import PythranSyntaxError
from cxxtypes import *
from intrinsic import UserFunction, MethodIntr
import itertools
import operator
import metadata
import intrinsic
from config import cfg
from collections import defaultdict


# networkx backward compatibility
if not "has_path" in nx.__dict__:
    def has_path(G, source, target):
        try:
            nx.shortest_path(G, source, target)
        except nx.NetworkXNoPath:
            return False
        return True
    nx.has_path = has_path


##
def pytype_to_ctype(t):
    '''python -> c++ type binding'''
    if isinstance(t, list):
        return 'pythonic::types::list<{0}>'.format(pytype_to_ctype(t[0]))
    if isinstance(t, set):
        return 'pythonic::types::set<{0}>'.format(pytype_to_ctype(list(t)[0]))
    elif isinstance(t, dict):
        tkey, tvalue = t.items()[0]
        return 'pythonic::types::dict<{0},{1}>'.format(pytype_to_ctype(tkey),
                                                       pytype_to_ctype(tvalue))
    elif isinstance(t, tuple):
        return 'decltype(pythonic::types::make_tuple({0}))'.format(
            ", ".join('std::declval<{}>()'.format(
                pytype_to_ctype(_)) for _ in t)
            )
    elif isinstance(t, ndarray):
        return 'pythonic::types::ndarray<{0},{1}>'.format(
            pytype_to_ctype(t.flat[0]), t.ndim)
    elif t in pytype_to_ctype_table:
        return pytype_to_ctype_table[t]
    else:
        raise NotImplementedError("{0}:{1}".format(type(t), t))


def pytype_to_deps(t):
    '''python -> c++ type binding'''
    if isinstance(t, list):
        return {'pythonic/types/list.hpp'}.union(pytype_to_deps(t[0]))
    if isinstance(t, set):
        return {'pythonic/types/set.hpp'}.union(pytype_to_deps(list(t)[0]))
    elif isinstance(t, dict):
        tkey, tvalue = t.items()[0]
        return {'pythonic/types/dict.hpp'}.union(pytype_to_deps(tkey),
                                                 pytype_to_deps(tvalue))
    elif isinstance(t, tuple):
        return {'pythonic/types/tuple.hpp'}.union(*map(pytype_to_deps, t))
    elif isinstance(t, ndarray):
        return {'pythonic/types/ndarray.hpp'}.union(pytype_to_deps(t[0]))
    elif t in pytype_to_ctype_table:
        return {'pythonic/types/{}.hpp'.format(t.__name__)}
    else:
        raise NotImplementedError("{0}:{1}".format(type(t), t))


def extract_constructed_types(t):
    if isinstance(t, list) or isinstance(t, ndarray):
        return [pytype_to_ctype(t)] + extract_constructed_types(t[0])
    elif isinstance(t, set):
        return [pytype_to_ctype(t)] + extract_constructed_types(list(t)[0])
    elif isinstance(t, dict):
        tkey, tvalue = t.items()[0]
        return ([pytype_to_ctype(t)]
                + extract_constructed_types(tkey)
                + extract_constructed_types(tvalue))
    elif isinstance(t, tuple):
        return ([pytype_to_ctype(t)]
                + sum(map(extract_constructed_types, t), []))
    elif t == long:
        return [pytype_to_ctype(t)]
    elif t == str:
        return [pytype_to_ctype(t)]
    else:
        return []


class TypeDependencies(ModuleAnalysis):
    '''
    Gathers the callees of each function required for type inference

    This analyse produces a directed graph with functions as nodes and edges
    between nodes when a function might call another.
    '''

    NoDeps = "None"

    def __init__(self):
        self.result = nx.DiGraph()
        self.current_function = None
        ModuleAnalysis.__init__(self, GlobalDeclarations)

    def prepare(self, node, ctx):
        super(TypeDependencies, self).prepare(node, ctx)
        for k, v in self.global_declarations.iteritems():
            self.result.add_node(v)
        self.result.add_node(TypeDependencies.NoDeps)

    def visit_any_conditionnal(self, node):
        '''
        Set and restore the in_cond variable whenever a node
        the children of which may not be executed is visited
        '''
        in_cond = self.in_cond
        self.in_cond = True
        self.generic_visit(node)
        self.in_cond = in_cond

    def visit_FunctionDef(self, node):
        assert self.current_function is None
        self.current_function = node
        self.naming = dict()
        self.in_cond = False  # True when we are in a if, while or for
        self.generic_visit(node)
        self.current_function = None

    def visit_Return(self, node):
        '''
        Gather all the function call that led to the creation of the
        returned expression and add an edge to each of this function.

        When visiting an expression, one returns a list of frozensets.  Each
        element of the list is linked to a possible path, each element of a
        frozenset is linked to a dependency.
        '''
        if node.value:
            v = self.visit(node.value)
            for dep_set in v:
                if dep_set:
                    for dep in dep_set:
                        self.result.add_edge(dep, self.current_function)
                else:
                    self.result.add_edge(TypeDependencies.NoDeps,
                                         self.current_function)

    visit_Yield = visit_Return

    def update_naming(self, name, value):
        '''
        Update or renew the name <-> dependencies binding
        depending on the in_cond state
        '''
        if self.in_cond:
            self.naming.setdefault(name, []).extend(value)
        else:
            self.naming[name] = value

    def visit_Assign(self, node):
        v = self.visit(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.update_naming(t.id, v)

    def visit_AugAssign(self, node):
        v = self.visit(node.value)
        t = node.target
        if isinstance(t, ast.Name):
            self.update_naming(t.id, v)

    def visit_For(self, node):
        self.naming.update({node.target.id: self.visit(node.iter)})
        self.visit_any_conditionnal(node)

    def visit_BoolOp(self, node):
        return sum((self.visit(value) for value in node.values), [])

    def visit_BinOp(self, node):
        args = map(self.visit, (node.left, node.right))
        return list({frozenset.union(*x) for x in itertools.product(*args)})

    def visit_UnaryOp(self, node):
        return self.visit(node.operand)

    def visit_Lambda(self, node):
        assert False

    def visit_IfExp(self, node):
        return self.visit(node.body) + self.visit(node.orelse)

    def visit_Compare(self, node):
        return [frozenset()]

    def visit_Call(self, node):
        args = map(self.visit, node.args)
        func = self.visit(node.func)
        params = args + [func or []]
        return list({frozenset.union(*p) for p in itertools.product(*params)})

    def visit_Num(self, node):
        return [frozenset()]

    def visit_Str(self, node):
        return [frozenset()]

    def visit_Attribute(self, node):
        return [frozenset()]

    def visit_Subscript(self, node):
        return self.visit(node.value)

    def visit_Name(self, node):
        if node.id in self.naming:
            return self.naming[node.id]
        elif node.id in self.global_declarations:
            return [frozenset([self.global_declarations[node.id]])]
        else:
            return [frozenset()]

    def visit_List(self, node):
        if node.elts:
            return list(set(sum(map(self.visit, node.elts), [])))
        else:
            return [frozenset()]

    visit_Set = visit_List

    def visit_Dict(self, node):
        if node.keys:
            items = node.keys + node.values
            return list(set(sum(map(self.visit, items), [])))
        else:
            return [frozenset()]

    visit_Tuple = visit_List

    def visit_Slice(self, node):
        return [frozenset()]

    def visit_Index(self, node):
        return [frozenset()]

    visit_If = visit_any_conditionnal
    visit_While = visit_any_conditionnal


class Reorder(Transformation):
    '''
    Reorder top-level functions to prevent circular type dependencies
    '''
    def __init__(self):
        Transformation.__init__(self, TypeDependencies,
                                OrderedGlobalDeclarations)

    def prepare(self, node, ctx):
        super(Reorder, self).prepare(node, ctx)
        none_successors = self.type_dependencies.successors(
            TypeDependencies.NoDeps)
        candidates = sorted(none_successors)
        while candidates:
            new_candidates = list()
            for n in candidates:
                # remove edges that imply a circular dependency
                for p in sorted(self.type_dependencies.predecessors(n)):
                    if nx.has_path(self.type_dependencies, n, p):
                        try:
                            while True:  # may be multiple edges
                                self.type_dependencies.remove_edge(p, n)
                        except:
                            pass  # no more edges to remove
                    # nx.write_dot(self.type_dependencies,"b.dot")
                if not n in self.type_dependencies.successors(n):
                    new_candidates.extend(self.type_dependencies.successors(n))
            candidates = new_candidates

    def visit_Module(self, node):
        newbody = list()
        olddef = list()
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                olddef.append(stmt)
            else:
                newbody.append(stmt)
            try:
                newdef = nx.topological_sort(
                    self.type_dependencies,
                    self.ordered_global_declarations)
                newdef = [f for f in newdef if isinstance(f, ast.FunctionDef)]

            except nx.exception.NetworkXUnfeasible:
                raise PythranSyntaxError("Infinite function recursion",
                                         stmt)
        assert set(newdef) == set(olddef)
        node.body = newbody + newdef
        return node


class UnboundableRValue(Exception):
    pass


class Types(ModuleAnalysis):
    '''
    Infer symbolic type for all AST node
    '''

    def __init__(self):
        self.result = dict()
        self.result["bool"] = NamedType("bool")
        self.combiners = defaultdict(UserFunction)
        self.current_global_declarations = dict()
        self.max_recompute = 1  # max number of use to be lazy
        ModuleAnalysis.__init__(self, StrictAliases, LazynessAnalysis)
        self.curr_locals_declaration = None

    def prepare(self, node, ctx):
        self.passmanager.apply(Reorder, node, ctx)
        for mname, module in modules.iteritems():
            for fname, function in module.iteritems():
                tname = 'pythonic::{0}::proxy::{1}'.format(mname, fname)
                self.result[function] = NamedType(tname)
                self.combiners[function] = function
        super(Types, self).prepare(node, ctx)

    def run(self, node, ctx):
        super(Types, self).run(node, ctx)
        final_types = self.result.copy()
        for head in self.current_global_declarations.itervalues():
            if head not in final_types:
                final_types[head] = "void"
        return final_types

    def register(self, ptype):
        """register ptype as a local typedef"""
        # Too many of them leads to memory burst
        if len(self.typedefs) < cfg.getint('typing', 'max_combiner'):
            self.typedefs.append(ptype)
            return True
        return False

    def node_to_id(self, n, depth=0):
        if isinstance(n, ast.Name):
            return (n.id, depth)
        elif isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Slice):
                return self.node_to_id(n.value, depth)
            else:
                return self.node_to_id(n.value, 1 + depth)
        # use return_alias information if any
        elif isinstance(n, ast.Call):
            func = n.func
            for alias in self.strict_aliases[func].aliases:
                # handle backward type dependencies from method calls
                signature = None
                if isinstance(alias, MethodIntr):
                    signature = alias
                #if isinstance(alias, ast.Attribute):
                #    _, signature = methods.get(
                #            func.attr,
                #            functions.get(func.attr, [(None, None)])[0]
                #            )
                #elif isinstance(alias, ast.Name):
                #    _, signature = functions.get(func.attr, [(None, None)])[0]
                if signature:
                    return_alias = (signature.return_alias
                                    and signature.return_alias(n))
                    if return_alias:  # else new location -> unboundable
                        assert len(return_alias), 'Too many return aliases'
                        return self.node_to_id(list(return_alias)[0], depth)
        raise UnboundableRValue()

    def isargument(self, node):
        """ checks whether node aliases to a parameter"""
        try:
            node_id, _ = self.node_to_id(node)
            return (node_id in self.name_to_nodes and
                    any([isinstance(n, ast.Name) and
                         isinstance(n.ctx, ast.Param)
                         for n in self.name_to_nodes[node_id]]))
        except UnboundableRValue:
                return False

    def combine(self, node, othernode, op=None, unary_op=None, register=False):
        if register and node in self.strict_aliases:
            self.combine_(node, othernode, op or operator.add,
                          unary_op or (lambda x: x), register)
            for a in self.strict_aliases[node].aliases:
                self.combine_(a, othernode, op or operator.add,
                              unary_op or (lambda x: x), register)
        else:
            self.combine_(node, othernode, op or operator.add,
                          unary_op or (lambda x: x), register)

    def combine_(self, node, othernode, op, unary_op, register):
        try:
            if register:  # this comes from an assignment,
                          # so we must check where the value is assigned
                node_id, depth = self.node_to_id(node)
                if depth > 0:
                    node = ast.Name(node_id, ast.Load())
                self.name_to_nodes.setdefault(node_id, set()).add(node)

                former_unary_op = unary_op

                # update the type to reflect container nesting
                unary_op = lambda x: reduce(lambda t, n: ContainerType(t),
                                            xrange(depth), former_unary_op(x))

            if isinstance(othernode, ast.FunctionDef):
                new_type = NamedType(othernode.name)
                if node not in self.result:
                    self.result[node] = new_type
            else:
                # only perform inter procedural combination upon stage 0
                if register and self.isargument(node) and self.stage == 0:
                    node_id, _ = self.node_to_id(node)
                    if node not in self.result:
                        self.result[node] = unary_op(self.result[othernode])
                    assert self.result[node], "found an alias with a type"

                    parametric_type = PType(self.current,
                                            self.result[othernode])
                    if self.register(parametric_type):

                        current_function = self.combiners[self.current]

                        def translator_generator(args, op, unary_op):
                            ''' capture args for translator generation'''
                            def interprocedural_type_translator(s, n):
                                translated_othernode = ast.Name(
                                    '__fake__', ast.Load())
                                s.result[translated_othernode] = (
                                    parametric_type.instanciate(
                                        s.current,
                                        [s.result[arg] for arg in n.args]))
                                # look for modified argument
                                for p, effective_arg in enumerate(n.args):
                                    formal_arg = args[p]
                                    if formal_arg.id == node_id:
                                        translated_node = effective_arg
                                        break
                                try:
                                    s.combine(translated_node,
                                              translated_othernode,
                                              op, unary_op, register=True)
                                except NotImplementedError:
                                    pass
                                    # this may fail when the effective
                                    #parameter is an expression
                                except UnboundLocalError:
                                    pass
                                    # this may fail when translated_node
                                    #is a default parameter
                            return interprocedural_type_translator
                        translator = translator_generator(
                            self.current.args.args,
                            op, unary_op)  # deferred combination
                        current_function.add_combiner(translator)
                else:
                    new_type = unary_op(self.result[othernode])
                    if node not in self.result:
                        self.result[node] = new_type
                    else:
                        self.result[node] = op(self.result[node], new_type)
        except UnboundableRValue:
            pass
        except:
            #print ast.dump(othernode)
            raise

    def visit_FunctionDef(self, node):
        self.curr_locals_declaration = self.passmanager.gather(
            LocalDeclarations,
            node)
        self.current = node
        self.typedefs = list()
        self.name_to_nodes = {arg.id: {arg} for arg in node.args.args}
        self.yield_points = self.passmanager.gather(YieldPoints, node)

        # two stages, one for inter procedural propagation
        self.stage = 0
        self.generic_visit(node)

        # and one for backward propagation
        # but this step is generally costly
        if cfg.getboolean('typing', 'enable_two_steps_typing'):
            self.stage = 1
            self.generic_visit(node)

        # propagate type information through all aliases
        for name, nodes in self.name_to_nodes.iteritems():
            final_node = ast.Name("__fake__" + name, ast.Load())
            for n in nodes:
                self.combine(final_node, n)
            for n in nodes:
                self.result[n] = self.result[final_node]
        self.current_global_declarations[node.name] = node
        # return type may be unset if the function always raises
        return_type = self.result.get(node, NamedType("void"))
        self.result[node] = (Assignable(return_type), self.typedefs)
        for k in self.passmanager.gather(LocalDeclarations, node):
            self.result[k] = self.get_qualifier(k)(self.result[k])

    def get_qualifier(self, node):
        lazy_res = self.lazyness_analysis[node.id]
        return Lazy if lazy_res <= self.max_recompute else Assignable

    def visit_Return(self, node):
        self.generic_visit(node)
        if not self.yield_points:
            if node.value:
                self.combine(self.current, node.value)
            else:
                self.result[self.current] = NamedType("none_type")

    def visit_Yield(self, node):
        self.generic_visit(node)
        self.combine(self.current, node.value)

    def visit_Assign(self, node):
        self.visit(node.value)
        for t in node.targets:
            self.combine(t, node.value, register=True)
            if t in self.curr_locals_declaration:
                self.result[t] = self.get_qualifier(t)(self.result[t])
            if isinstance(t, ast.Subscript):
                if self.visit_AssignedSubscript(t):
                    for alias in self.strict_aliases[t.value].aliases:
                        fake = ast.Subscript(alias, t.value, ast.Store())
                        self.combine(fake, node.value, register=True)

    def visit_AugAssign(self, node):
        self.visit(node.value)
        self.combine(node.target, node.value,
                     lambda x, y: x + ExpressionType(
                         operator_to_lambda[type(node.op)],
                         [x, y]), register=True)
        if isinstance(node.target, ast.Subscript):
            if self.visit_AssignedSubscript(node.target):
                for alias in self.strict_aliases[node.target.value].aliases:
                    fake = ast.Subscript(alias, node.target.value, ast.Store())
                    self.combine(fake,
                                 node.value,
                                 lambda x, y: x + ExpressionType(
                                     operator_to_lambda[type(node.op)],
                                     [x, y]),
                                 register=True)

    def visit_For(self, node):
        self.visit(node.iter)
        self.combine(node.target, node.iter,
                     unary_op=IteratorContentType, register=True)
        node.body and map(self.visit, node.body)
        node.orelse and map(self.visit, node.orelse)

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        [self.combine(node, value) for value in node.values]

    def visit_BinOp(self, node):
        self.generic_visit(node)
        wl, wr = [self.result[x].isweak() for x in (node.left, node.right)]
        if (isinstance(node.op, ast.Add) and any([wl, wr])
                and not all([wl, wr])):
        # assumes the + operator always has the same operand type
        # on left and right side
            F = operator.add
        else:
            F = lambda x, y: ExpressionType(
                operator_to_lambda[type(node.op)], [x, y])

        fake_node = ast.Name("#", ast.Param())
        self.combine(fake_node, node.left, F)
        self.combine(fake_node, node.right, F)
        self.combine(node, fake_node)
        del self.result[fake_node]

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        f = lambda x: ExpressionType(operator_to_lambda[type(node.op)], [x])
        self.combine(node, node.operand, unary_op=f)

    def visit_IfExp(self, node):
        self.generic_visit(node)
        [self.combine(node, n) for n in (node.body, node.orelse)]

    def visit_Compare(self, node):
        self.generic_visit(node)
        all_compare = zip(node.ops, node.comparators)
        for op, comp in all_compare:
            self.combine(node, comp,
                         unary_op=lambda x: ExpressionType(
                             operator_to_lambda[type(op)],
                             [self.result[node.left], x])
                         )

    def visit_Call(self, node):
        self.generic_visit(node)
        for alias in self.strict_aliases[node.func].aliases:
            # this comes from a bind
            if isinstance(alias, ast.Call):
                a0 = alias.args[0]
                bounded_name = a0.id
                # by construction of the bind construct
                assert len(self.strict_aliases[a0].aliases) == 1
                bounded_function = list(self.strict_aliases[a0].aliases)[0]
                fake_name = ast.Name(bounded_name, ast.Load())
                fake_node = ast.Call(fake_name, alias.args[1:] + node.args,
                                     [], None, None)
                self.combiners[bounded_function].combiner(self, fake_node)
                # force recombination of binded call
                for n in self.name_to_nodes[node.func.id]:
                    self.result[n] = ReturnType(self.result[alias.func],
                                                [self.result[arg]
                                                 for arg in alias.args])
            # handle backward type dependencies from function calls
            else:
                self.combiners[alias].combiner(self, node)

        # recurring nightmare
        isweak = any(self.result[n].isweak() for n in node.args + [node.func])
        if self.stage == 0 and isweak:
            # maybe we can get saved if we have a hint about
            # the called function return type
            for alias in self.strict_aliases[node.func].aliases:
                if alias is self.current and alias in self.result:
                    # great we have a (partial) type information
                    self.result[node] = self.result[alias]
                    return

        # special handler for getattr: use the attr name as an enum member
        if type(node.func) is (ast.Attribute) and node.func.attr == 'getattr':
            F = lambda f: GetAttr(self.result[node.args[0]], node.args[1].s)
        # default behavior
        else:
            F = lambda f: ReturnType(f,
                                     [self.result[arg] for arg in node.args])
        # op is used to drop previous value there
        self.combine(node, node.func, op=lambda x, y: y, unary_op=F)

    def visit_Num(self, node):
        self.result[node] = NamedType(pytype_to_ctype_table[type(node.n)])

    def visit_Str(self, node):
        self.result[node] = NamedType(pytype_to_ctype_table[str])

    def visit_Attribute(self, node):
        def rec(w, n):
            if isinstance(n, ast.Name):
                return w[n.id], (n.id,)
            elif isinstance(n, ast.Attribute):
                r = rec(w, n.value)
                if len(r[1]) > 1:
                    plast, last = r[1][-2:]
                    if plast == '__builtin__' and last.startswith('__'):
                        return r[0][n.attr], r[1][:-2] + r[1][-1:] + (n.attr,)
                return r[0][n.attr], r[1] + (n.attr,)
        obj, path = rec(modules, node)
        path = ('pythonic',) + path
        if obj.isliteral():
            self.result[node] = DeclType('::'.join(path))
        else:
            self.result[node] = DeclType(
                '::'.join(path[:-1]) + '::proxy::' + path[-1] + '()')

    def visit_Slice(self, node):
        self.generic_visit(node)
        if node.step is None or (type(node.step) is ast.Num
                                 and node.step.n == 1):
            self.result[node] = NamedType('pythonic::types::contiguous_slice')
        else:
            self.result[node] = NamedType('pythonic::types::slice')

    def visit_Subscript(self, node):
        self.visit(node.value)
        # type of a[1:2, 3, 4:1] is the type of: declval(a)(slice, long, slice)
        if isinstance(node.slice, ast.ExtSlice):
            self.visit(node.slice)
            f = lambda t: ExpressionType(
                lambda a, *b: "{0}({1})".format(a, ", ".join(b)),
                [t] + [self.result[d] for d in node.slice.dims]
                )
        elif (type(node.slice) is (ast.Index)
                and type(node.slice.value) is ast.Num
                and node.slice.value.n >= 0):
            # type of a[2] is the type of an elements of a
            # this special case is to make type inference easier
            # for the back end compiler
            f = lambda t: ElementType(node.slice.value.n, t)
        else:
            # type of a[i] is the return type of the matching function
            self.visit(node.slice)
            f = lambda x: ExpressionType(
                lambda a, b: "{0}[{1}]".format(a, b),
                [x, self.result[node.slice]]
                )
        f and self.combine(node, node.value, unary_op=f)

    def visit_AssignedSubscript(self, node):
        if type(node.slice) not in (ast.Slice, ast.ExtSlice):
            self.visit(node.slice)
            self.combine(node.value, node.slice,
                         unary_op=IndexableType, register=True)
            for alias in self.strict_aliases[node.value].aliases:
                self.combine(alias, node.slice,
                             unary_op=IndexableType, register=True)
            return True
        else:
            return False

    def visit_Name(self, node):
        if node.id in self.name_to_nodes:
            for n in self.name_to_nodes[node.id]:
                self.combine(node, n)
        elif node.id in self.current_global_declarations:
            self.combine(node, self.current_global_declarations[node.id])
        else:
            self.result[node] = NamedType(node.id, {Weak})

    def visit_List(self, node):
        self.generic_visit(node)
        if node.elts:
            for elt in node.elts:
                self.combine(node, elt, unary_op=ListType)
        else:
            self.result[node] = NamedType("pythonic::types::empty_list")

    def visit_Set(self, node):
        self.generic_visit(node)
        if node.elts:
            for elt in node.elts:
                self.combine(node, elt, unary_op=SetType)
        else:
            self.result[node] = NamedType("pythonic::types::empty_set")

    def visit_Dict(self, node):
        self.generic_visit(node)
        if node.keys:
            for key, value in zip(node.keys, node.values):
                self.combine(node, key,
                             unary_op=lambda x: DictType(x,
                                                         self.result[value]))
        else:
            self.result[node] = NamedType("pythonic::types::empty_dict")

    def visit_ExceptHandler(self, node):
        if node.type and node.name:
            if not isinstance(node.type, ast.Tuple):
                tname = NamedType(
                    'pythonic::types::{0}'.format(node.type.attr))
                self.result[node.type] = tname
                self.combine(node.name, node.type, register=True)
        map(self.visit, node.body)

    def visit_Tuple(self, node):
        self.generic_visit(node)
        try:
            types = [self.result[elt] for elt in node.elts]
            self.result[node] = TupleType(types)
        except:
            pass  # not very harmonious with the combine method ...

    def visit_Index(self, node):
        self.generic_visit(node)
        self.combine(node, node.value)

    def visit_arguments(self, node):
        for i, arg in enumerate(node.args):
            self.result[arg] = ArgumentType(i)
        map(self.visit, node.defaults)

########NEW FILE########
__FILENAME__ = unparse
"""
This code is extracted from the python source tree, and thus under the PSF
License.
"""

"Usage: unparse.py <path to source file>"


import sys
import ast
import cStringIO
import os
import metadata
import openmp


# Large float and imaginary literals get turned into infinities in the AST.
# We unparse those infinities to INFSTR.
INFSTR = "1e" + repr(sys.float_info.max_10_exp + 1)


def interleave(inter, f, seq):
    """Call f on each item in seq, calling inter() in between.
    """
    seq = iter(seq)
    try:
        f(next(seq))
    except StopIteration:
        pass
    else:
        for x in seq:
            inter()
            f(x)


class Unparser:
    """Methods in this class recursively traverse an AST and
    output source code for the abstract syntax; original formatting
    is disregarded. """

    def __init__(self, tree, file=sys.stdout):
        """Unparser(tree, file=sys.stdout) -> None.
         Print the source for tree to file."""
        self.f = file
        self.future_imports = []
        self._indent = 0
        self.line_marker = ""
        self.dispatch(tree)
        self.f.write("")
        self.f.flush()

    def fill(self, text=""):
        "Indent a piece of text, according to the current indentation level"
        self.f.write(self.line_marker + "    " * self._indent + text)
        self.line_marker = "\n"

    def write(self, text):
        "Append a piece of text to the current line."
        self.f.write(text)

    def enter(self):
        "Print ':', and increase the indentation."
        self.write(":")
        self._indent += 1

    def leave(self):
        "Decrease the indentation level."
        self._indent -= 1

    def dispatch(self, tree):
        "Dispatcher function, dispatching tree type T to method _T."
        #display omp directive in python dump
        for omp in metadata.get(tree, openmp.OMPDirective):
            deps = list()
            for dep in omp.deps:
                old_file = self.f
                self.f = cStringIO.StringIO()
                self.dispatch(dep)
                deps.append(self.f.getvalue())
                self.f = old_file
            directive = omp.s.format(*deps)
            self._Expr(ast.Expr(ast.Str(s=directive)))

        if isinstance(tree, list):
            for t in tree:
                self.dispatch(t)
            return
        meth = getattr(self, "_" + tree.__class__.__name__)
        meth(tree)

    ############### Unparsing methods ######################
    # There should be one method per concrete grammar type #
    # Constructors should be grouped by sum type. Ideally, #
    # this would follow the order in the grammar, but      #
    # currently doesn't.                                   #
    ########################################################

    def _Module(self, tree):
        # Goes through each top-level statement. If the special __init__()
        # function is found, add a call to it because it's a special Pythran
        # feature.
        has_init = False
        for stmt in tree.body:
            self.dispatch(stmt)
            if (type(stmt) is ast.FunctionDef and
                    stmt.name == '__init__'):
                has_init = True
        # Call __init__() in which top statements are moved.
        if has_init:
            self.fill("__init__()")

    # stmt
    def _Expr(self, tree):
        self.fill()
        self.dispatch(tree.value)

    def _Import(self, t):
        self.fill("import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _ImportFrom(self, t):
        # A from __future__ import may affect unparsing, so record it.
        if t.module and t.module == '__future__':
            self.future_imports.extend(n.name for n in t.names)

        self.fill("from ")
        self.write("." * t.level)
        if t.module:
            self.write(t.module)
        self.write(" import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _Assign(self, t):
        self.fill()
        for target in t.targets:
            self.dispatch(target)
            self.write(" = ")
        self.dispatch(t.value)

    def _AugAssign(self, t):
        self.fill()
        self.dispatch(t.target)
        self.write(" " + self.binop[t.op.__class__.__name__] + "= ")
        self.dispatch(t.value)

    def _Return(self, t):
        self.fill("return")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)

    def _Pass(self, t):
        self.fill("pass")

    def _Break(self, t):
        self.fill("break")

    def _Continue(self, t):
        self.fill("continue")

    def _Delete(self, t):
        self.fill("del ")
        interleave(lambda: self.write(", "), self.dispatch, t.targets)

    def _Assert(self, t):
        self.fill("assert ")
        self.dispatch(t.test)
        if t.msg:
            self.write(", ")
            self.dispatch(t.msg)

    def _Exec(self, t):
        self.fill("exec ")
        self.dispatch(t.body)
        if t.globals:
            self.write(" in ")
            self.dispatch(t.globals)
        if t.locals:
            self.write(", ")
            self.dispatch(t.locals)

    def _Print(self, t):
        self.fill("print ")
        do_comma = False
        if t.dest:
            self.write(">>")
            self.dispatch(t.dest)
            do_comma = True
        for e in t.values:
            if do_comma:
                self.write(", ")
            else:
                do_comma = True
            self.dispatch(e)
        if not t.nl:
            self.write(",")

    def _Global(self, t):
        self.fill("global ")
        interleave(lambda: self.write(", "), self.write, t.names)

    def _Yield(self, t):
        self.write("(")
        self.write("yield")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _Raise(self, t):
        self.fill('raise ')
        if t.type:
            self.dispatch(t.type)
        if t.inst:
            self.write(", ")
            self.dispatch(t.inst)
        if t.tback:
            self.write(", ")
            self.dispatch(t.tback)

    def _TryExcept(self, t):
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()

        for ex in t.handlers:
            self.dispatch(ex)
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _TryFinally(self, t):
        if len(t.body) == 1 and isinstance(t.body[0], ast.TryExcept):
            # try-except-finally
            self.dispatch(t.body)
        else:
            self.fill("try")
            self.enter()
            self.dispatch(t.body)
            self.leave()

        self.fill("finally")
        self.enter()
        self.dispatch(t.finalbody)
        self.leave()

    def _ExceptHandler(self, t):
        self.fill("except")
        if t.type:
            self.write(" ")
            self.dispatch(t.type)
        if t.name:
            self.write(" as ")
            self.dispatch(t.name)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _ClassDef(self, t):
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("class " + t.name)
        if t.bases:
            self.write("(")
            for a in t.bases:
                self.dispatch(a)
                self.write(", ")
            self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _FunctionDef(self, t):
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("def " + t.name + "(")
        self.dispatch(t.args)
        self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _For(self, t):
        self.fill("for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _If(self, t):
        self.fill("if ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        # collapse nested ifs into equivalent elifs.
        while (t.orelse and len(t.orelse) == 1 and
               isinstance(t.orelse[0], ast.If)):
            t = t.orelse[0]
            self.fill("elif ")
            self.dispatch(t.test)
            self.enter()
            self.dispatch(t.body)
            self.leave()
        # final else
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _While(self, t):
        self.fill("while ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _With(self, t):
        self.fill("with ")
        self.dispatch(t.context_expr)
        if t.optional_vars:
            self.write(" as ")
            self.dispatch(t.optional_vars)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    # expr
    def _Str(self, tree):
        # if from __future__ import unicode_literals is in effect,
        # then we want to output string literals using a 'b' prefix
        # and unicode literals with no prefix.
        if "unicode_literals" not in self.future_imports:
            self.write(repr(tree.s))
        elif isinstance(tree.s, str):
            self.write("b" + repr(tree.s))
        elif isinstance(tree.s, unicode):
            self.write(repr(tree.s).lstrip("u"))
        else:
            assert False, "shouldn't get here"

    def _Name(self, t):
        self.write(t.id)

    def _Repr(self, t):
        self.write("`")
        self.dispatch(t.value)
        self.write("`")

    def _Num(self, t):
        repr_n = repr(t.n)
        # Parenthesize negative numbers, to avoid turning (-1)**2 into -1**2.
        if repr_n.startswith("-"):
            self.write("(")
        # Substitute overflowing decimal literal for AST infinities.
        self.write(repr_n.replace("inf", INFSTR))
        if repr_n.startswith("-"):
            self.write(")")

    def _List(self, t):
        self.write("[")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("]")

    def _ListComp(self, t):
        self.write("[")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("]")

    def _GeneratorExp(self, t):
        self.write("(")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write(")")

    def _SetComp(self, t):
        self.write("{")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _DictComp(self, t):
        self.write("{")
        self.dispatch(t.key)
        self.write(": ")
        self.dispatch(t.value)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _comprehension(self, t):
        self.write(" for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        for if_clause in t.ifs:
            self.write(" if ")
            self.dispatch(if_clause)

    def _IfExp(self, t):
        self.write("(")
        self.dispatch(t.body)
        self.write(" if ")
        self.dispatch(t.test)
        self.write(" else ")
        self.dispatch(t.orelse)
        self.write(")")

    def _Set(self, t):
        assert(t.elts)  # should be at least one element
        self.write("{")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("}")

    def _Dict(self, t):
        self.write("{")

        def write_pair(pair):
            k, v = pair
            self.dispatch(k)
            self.write(": ")
            self.dispatch(v)
        interleave(lambda: self.write(", "), write_pair, zip(t.keys, t.values))
        self.write("}")

    def _Tuple(self, t):
        self.write("(")
        if len(t.elts) == 1:
            (elt,) = t.elts
            self.dispatch(elt)
            self.write(",")
        else:
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write(")")

    unop = {"Invert": "~", "Not": "not", "UAdd": "+", "USub": "-"}

    def _UnaryOp(self, t):
        self.write("(")
        self.write(self.unop[t.op.__class__.__name__])
        self.write(" ")
        # If we're applying unary minus to a number, parenthesize the number.
        # This is necessary: -2147483648 is different from -(2147483648) on
        # a 32-bit machine (the first is an int, the second a long), and
        # -7j is different from -(7j).  (The first has real part 0.0, the
        #second has real part -0.0.)
        if isinstance(t.op, ast.USub) and isinstance(t.operand, ast.Num):
            self.write("(")
            self.dispatch(t.operand)
            self.write(")")
        else:
            self.dispatch(t.operand)
        self.write(")")

    binop = {"Add": "+", "Sub": "-", "Mult": "*", "Div": "/", "Mod": "%",
             "LShift": "<<", "RShift": ">>", "BitOr": "|", "BitXor": "^",
             "BitAnd": "&", "FloorDiv": "//", "Pow": "**"}

    def _BinOp(self, t):
        self.write("(")
        self.dispatch(t.left)
        self.write(" " + self.binop[t.op.__class__.__name__] + " ")
        self.dispatch(t.right)
        self.write(")")

    cmpops = {"Eq": "==", "NotEq": "!=", "Lt": "<", "LtE": "<=", "Gt": ">",
              "GtE": ">=", "Is": "is", "IsNot": "is not", "In": "in",
              "NotIn": "not in"}

    def _Compare(self, t):
        self.write("(")
        self.dispatch(t.left)
        for o, e in zip(t.ops, t.comparators):
            self.write(" " + self.cmpops[o.__class__.__name__] + " ")
            self.dispatch(e)
        self.write(")")

    boolops = {ast.And: 'and', ast.Or: 'or'}

    def _BoolOp(self, t):
        self.write("(")
        s = " %s " % self.boolops[t.op.__class__]
        interleave(lambda: self.write(s), self.dispatch, t.values)
        self.write(")")

    def _Attribute(self, t):
        self.dispatch(t.value)
        # Special case: 3.__abs__() is a syntax error, so if t.value
        # is an integer literal then we need to either parenthesize
        # it or add an extra space to get 3 .__abs__().
        if isinstance(t.value, ast.Num) and isinstance(t.value.n, int):
            self.write(" ")
        self.write(".")
        self.write(t.attr)

    def _Call(self, t):
        self.dispatch(t.func)
        self.write("(")
        comma = False
        for e in t.args:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.dispatch(e)
        for e in t.keywords:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.dispatch(e)
        if t.starargs:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.write("*")
            self.dispatch(t.starargs)
        if t.kwargs:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.write("**")
            self.dispatch(t.kwargs)
        self.write(")")

    def _Subscript(self, t):
        self.dispatch(t.value)
        self.write("[")
        self.dispatch(t.slice)
        self.write("]")

    # slice
    def _Ellipsis(self, t):
        self.write("...")

    def _Index(self, t):
        self.dispatch(t.value)

    def _Slice(self, t):
        if t.lower:
            self.dispatch(t.lower)
        self.write(":")
        if t.upper:
            self.dispatch(t.upper)
        if t.step:
            self.write(":")
            self.dispatch(t.step)

    def _ExtSlice(self, t):
        interleave(lambda: self.write(', '), self.dispatch, t.dims)

    # others
    def _arguments(self, t):
        first = True
        # normal arguments
        defaults = [None] * (len(t.args) - len(t.defaults)) + t.defaults
        for a, d in zip(t.args, defaults):
            if first:
                first = False
            else:
                self.write(", ")
            self.dispatch(a),
            if d:
                self.write("=")
                self.dispatch(d)

        # varargs
        if t.vararg:
            if first:
                first = False
            else:
                self.write(", ")
            self.write("*")
            self.write(t.vararg)

        # kwargs
        if t.kwarg:
            if first:
                first = False
            else:
                self.write(", ")
            self.write("**" + t.kwarg)

    def _keyword(self, t):
        self.write(t.arg)
        self.write("=")
        self.dispatch(t.value)

    def _Lambda(self, t):
        self.write("(")
        self.write("lambda ")
        self.dispatch(t.args)
        self.write(": ")
        self.dispatch(t.body)
        self.write(")")

    def _alias(self, t):
        self.write(t.name)
        if t.asname:
            self.write(" as " + t.asname)


def roundtrip(filename, output=sys.stdout):
    with open(filename, "r") as pyfile:
        source = pyfile.read()
    tree = compile(source, filename, "exec", ast.PyCF_ONLY_AST)
    Unparser(tree, output)


def testdir(a):
    try:
        names = [n for n in os.listdir(a) if n.endswith('.py')]
    except OSError:
        sys.stderr.write("Directory not readable: %s" % a)
    else:
        for n in names:
            fullname = os.path.join(a, n)
            if os.path.isfile(fullname):
                output = cStringIO.StringIO()
                print 'Testing %s' % fullname
                try:
                    roundtrip(fullname, output)
                except Exception as e:
                    print '  Failed to compile, exception is %s' % repr(e)
            elif os.path.isdir(fullname):
                testdir(fullname)


def main(args):
    if args[0] == '--testdir':
        for a in args[1:]:
            testdir(a)
    else:
        for a in args:
            roundtrip(a)

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pythran documentation build configuration file, created by
# sphinx-quickstart on Wed Feb 19 20:57:04 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

from pythran import __version__

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pythran'
copyright = u'2014, Serge Guelton, Pierrick Brunet et al.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

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
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'haiku'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {'sidebarwidth':200}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = 'pythran.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {'**': ['globaltoc.html']}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

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
htmlhelp_basename = 'Pythrandoc'


########NEW FILE########
