__FILENAME__ = run-tests
import sys
import unittest
from unittest.loader import TestLoader
from templatetk.testsuite import suite

root_suite = suite()
common_prefix = 'templatetk.testsuite.'


def find_all_tests():
    suites = [suite()]
    while suites:
        s = suites.pop()
        try:
            suites.extend(s)
        except TypeError:
            yield s


class BetterLoader(TestLoader):

    def loadTestsFromName(self, name, module=None):
        if name == 'suite':
            return suite()
        for testcase in find_all_tests():
            testname = '%s.%s.%s' % (
                testcase.__class__.__module__,
                testcase.__class__.__name__,
                testcase._testMethodName
            )
            if testname == name:
                return testcase
            if testname.startswith(common_prefix):
                if testname[len(common_prefix):] == name:
                    return testcase
        print >> sys.stderr, 'Error: could not find testcase "%s"' % name
        sys.exit(1)


unittest.main(testLoader=BetterLoader(), defaultTest='suite')

########NEW FILE########
__FILENAME__ = asttransform
# -*- coding: utf-8 -*-
"""
    templatetk.asttransform
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module turns an ASTS into a regular Python ast for compilation.
    The generated AST is not a regular AST but will have all the template
    logic encapsulated in a function named 'root'.  If the ast is compiled
    and evaluated against a dictionary, that function can be cached::

        def compile_template(node):
            namespace = {}
            ast = to_ast(node, node.config)
            code = compile(ast, node.filename.encode('utf-8'), 'expr')
            exec code in namespace
            return namespace['root']

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from . import nodes
from .nodeutils import NodeVisitor
from .idtracking import IdentManager
from .fstate import FrameState


try:
    import ast
    have_ast = True
except ImportError:
    import _ast as ast
    have_ast = False


_context_target_map = {
    'store':        ast.Store,
    'param':        ast.Param,
    'load':         ast.Load
}


_cmpop_to_ast = {
    'eq':       ast.Eq,
    'ne':       ast.NotEq,
    'gt':       ast.Gt,
    'gteq':     ast.GtE,
    'lt':       ast.Lt,
    'lteq':     ast.LtE,
    'in':       ast.In,
    'notin':    ast.NotIn
}


def fix_missing_locations(node):
    """Adds missing locations so that the code becomes compilable
    by the Python interpreter.
    """
    def _fix(node, lineno, col_offset):
        if 'lineno' in node._attributes:
            if getattr(node, 'lineno', None) is None:
                node.lineno = lineno
            else:
                lineno = node.lineno
        if 'col_offset' in node._attributes:
            if getattr(node, 'col_offset', None) is None:
                node.col_offset = col_offset
            else:
                col_offset = node.col_offset
        for child in ast.iter_child_nodes(node):
            _fix(child, lineno, col_offset)
    _fix(node, 1, 0)
    return node


def to_ast(node):
    """Converts a template node to a python AST ready for compilation."""
    transformer = ASTTransformer(node.config)
    return transformer.transform(node)


class ASTTransformer(NodeVisitor):
    bcinterp_module = __name__.split('.')[0] + '.bcinterp'
    exception_module = __name__.split('.')[0] + '.exceptions'

    def __init__(self, config):
        NodeVisitor.__init__(self)
        if not have_ast:
            raise RuntimeError('Python 2.6 or later required for AST')
        self.config = config
        self.ident_manager = IdentManager()

    def transform(self, node):
        assert isinstance(node, nodes.Template), 'can only transform ' \
            'templates, got %r' % node.__class__.__name__
        return self.visit(node, None)

    def visit(self, node, state):
        rv = NodeVisitor.visit(self, node, state)
        assert rv is not None, 'visitor for %r failed' % node
        return rv

    def visit_block(self, nodes, state):
        result = []
        if nodes:
            for node in nodes:
                rv = self.visit(node, state)
                if isinstance(rv, ast.AST):
                    result.append(rv)
                else:
                    result.extend(rv)
        return result

    def make_getattr(self, dotted_name, lineno=None):
        parts = dotted_name.split('.')
        expr = ast.Name(parts.pop(0), ast.Load(), lineno=lineno)
        for part in parts:
            expr = ast.Attribute(expr, part, ast.Load())
        return expr

    def make_call(self, dotted_name, args, dyn_args=None, lineno=None):
        return ast.Call(self.make_getattr(dotted_name), args, [],
                        dyn_args, None, lineno=lineno)

    def make_rtstate_func(self, name, lineno=None):
        body = [ast.Assign([ast.Name('config', ast.Store())],
                           ast.Attribute(ast.Name('rtstate', ast.Load()),
                                         'config', ast.Load()))]
        funcargs = ast.arguments([ast.Name('rtstate', ast.Param())], None,
                                 None, [])
        return ast.FunctionDef(name, funcargs, body, [], lineno=lineno)

    def make_target_context(self, ctx):
        return _context_target_map[ctx]()

    def make_cmp_op(self, opname):
        return _cmpop_to_ast[opname]()

    def make_name_tuple(self, target_tuple, as_ast=True):
        assert isinstance(target_tuple, nodes.Tuple)
        assert target_tuple.ctx in ('store', 'param')
        def walk(obj):
            rv = []
            for node in obj.items:
                if isinstance(node, nodes.Name):
                    val = node.name
                    if as_ast:
                        val = ast.Str(val)
                    rv.append(val)
                elif isinstance(node, nodes.Tuple):
                    rv.append(walk(node))
                else:
                    assert 0, 'unsupported assignment to %r' % node
            if as_ast:
                return ast.Tuple(rv, ast.Load())
            return tuple(rv)
        return walk(target_tuple)

    def make_const(self, val, fstate):
        if isinstance(val, (int, float, long)):
            return ast.Num(val)
        elif isinstance(val, basestring):
            return ast.Str(val)
        elif isinstance(val, tuple):
            return ast.Tuple([self.make_const(x, fstate) for x in val],
                             ast.Load())
        elif isinstance(val, list):
            return ast.List([self.make_const(x, fstate) for x in val],
                            ast.Load())
        elif isinstance(val, dict):
            return ast.Dict([self.make_const(k, fstate) for k in val.keys()],
                            [self.make_const(v, fstate) for v in val.values()])
        elif val in (None, True, False):
            return ast.Name(str(val), ast.Load())
        assert 0, 'Unsupported constant value for compiler'

    def make_runtime_imports(self):
        yield ast.ImportFrom('__future__', [ast.alias('division', None)], 0)
        yield ast.ImportFrom(self.bcinterp_module,
                             [ast.alias('*', None)], 0)
        yield ast.ImportFrom(self.exception_module,
                             [ast.alias('*', None)], 0)

    def write_output(self, expr, fstate, lineno=None):
        if isinstance(expr, basestring):
            expr = ast.Str(unicode(expr))
        else:
            expr = self.make_call('rtstate.info.finalize', [expr])
        if fstate.buffer is None:
            expr = ast.Yield(expr)
        else:
            expr = ast.Call(ast.Attribute(ast.Name(fstate.buffer, ast.Load()),
                            'append', ast.Load()), [expr], [], None, None)
        return ast.Expr(expr, lineno=lineno)

    def make_resolve_call(self, node, fstate):
        args = [self.visit(x, fstate) for x in node.args]
        kwargs = [self.visit(x, fstate) for x in node.kwargs]
        dyn_args = dyn_kwargs = None
        if node.dyn_args is not None:
            dyn_args = self.visit(node.dyn_args, fstate)
        if node.dyn_kwargs is not None:
            dyn_kwargs = self.visit(node.dyn_kwargs, fstate)
        return ast.Call(ast.Name('resolve_call_args', ast.Load()),
                        args, kwargs, dyn_args, dyn_kwargs)

    def inject_scope_code(self, fstate, body):
        """This has to be called just before doing any modifications on the
        scoped code and after all inner frames were visisted.  This is required
        because the injected code will also need the knowledge of the inner
        frames to know which identifiers are required to lookup in the outer
        frame that the outer frame might not need.
        """
        before = []

        for alias, old_name in fstate.required_aliases.iteritems():
            before.append(ast.Assign([ast.Name(alias, ast.Store())],
                                      ast.Name(old_name, ast.Load())))
        for inner_func in fstate.inner_functions:
            before.extend(inner_func)

        # at that point we know about the inner states and can see if any
        # of them need variables we do not have yet assigned and we have to
        # resolve for them.
        for target, sourcename in fstate.iter_required_lookups():
            before.append(ast.Assign([ast.Name(target, ast.Store())],
                self.make_call('rtstate.lookup_var',
                               [ast.Str(sourcename)])))

        dummy_yield = []
        if fstate.buffer is None:
            dummy_yield.append(ast.If(ast.Num(0),
                [ast.Expr(ast.Yield(ast.Num(0)))], []))
        body[:] = before + body + dummy_yield

    def locals_to_dict(self, fstate, reference_node, lineno=None):
        keys = []
        values = []
        for name, local_id in fstate.iter_vars(reference_node):
            keys.append(ast.Str(name))
            values.append(ast.Name(local_id, ast.Load()))
        return ast.Dict(keys, values, lineno=lineno)

    def context_to_lookup(self, fstate, reference_node, lineno=None):
        locals = self.locals_to_dict(fstate, reference_node)
        if not locals.keys:
            return self.make_getattr('rtstate.context')
        return self.make_call('MultiMappingLookup',
            [ast.Tuple([locals, self.make_getattr('rtstate.context')],
                       ast.Load())], lineno=lineno)

    def make_assign(self, target, expr, fstate, lineno=None):
        assert isinstance(target, nodes.Name), 'can only assign to names'
        target_node = self.visit(target, fstate)
        rv = [ast.Assign([target_node], expr, lineno=lineno)]
        if fstate.root and isinstance(target_node, ast.Name):
            rv.append(ast.Expr(self.make_call('rtstate.export_var',
                                              [ast.Str(target.name),
                                               ast.Name(target_node.id,
                                                        ast.Load())])))
        return rv

    def make_template_lookup(self, template_expression, fstate):
        return [
            ast.Assign([ast.Name('template_name', ast.Store())],
                       self.visit(template_expression, fstate)),
            ast.Assign([ast.Name('template', ast.Store())],
                       self.make_call('rtstate.get_template',
                                      [ast.Name('template_name',
                                                ast.Load())]))
        ]

    def make_template_info(self, behavior):
        return ast.Assign([ast.Name('info', ast.Store())],
                           self.make_call('rtstate.info.make_info',
                                          [ast.Name('template', ast.Load()),
                                           ast.Name('template_name', ast.Load()),
                                           ast.Str(behavior)]))

    def make_template_generator(self, vars):
        return self.make_call('config.yield_from_template',
                              [ast.Name('template', ast.Load()),
                               ast.Name('info', ast.Load()),
                               vars])

    def make_template_render_call(self, vars, behavior):
        return [
            self.make_template_info(behavior),
            ast.For(ast.Name('event', ast.Store()),
                    self.make_template_generator(vars),
                    [ast.Expr(ast.Yield(ast.Name('event', ast.Load())))], [])
        ]

    def visit_Template(self, node, fstate):
        assert fstate is None, 'framestate passed to template visitor'
        fstate = FrameState(self.config, ident_manager=self.ident_manager,
                            root=True)
        fstate.analyze_identfiers(node.body)
        rv = ast.Module(lineno=1)
        root = self.make_rtstate_func('root')
        root.body.extend(self.visit_block(node.body, fstate))
        self.inject_scope_code(fstate, root.body)
        rv.body = list(self.make_runtime_imports()) + [root]

        setup = self.make_rtstate_func('setup')
        setup.body.append(ast.Expr(self.make_call('register_block_mapping',
            [self.make_getattr('rtstate.info'),
             ast.Name('blocks', ast.Load())])))

        blocks_keys = []
        blocks_values = []
        for block_node in node.find_all(nodes.Block):
            block_fstate = fstate.derive(scope='hard')
            block = self.make_rtstate_func('block_' + block_node.name)
            block.body.extend(self.visit_block(block_node.body, block_fstate))
            self.inject_scope_code(block_fstate, block.body)
            rv.body.append(block)
            blocks_keys.append(ast.Str(block_node.name))
            blocks_values.append(ast.Name('block_' + block_node.name,
                                          ast.Load()))

        rv.body.append(setup)
        rv.body.append(ast.Assign([ast.Name('blocks', ast.Store())],
                                  ast.Dict(blocks_keys, blocks_values)))

        return fix_missing_locations(rv)

    def visit_Output(self, node, fstate):
        rv = []
        for child in node.nodes:
            if isinstance(child, nodes.TemplateData):
                what = child.data
            else:
                what = self.visit(child, fstate)
            rv.append(self.write_output(what, fstate, lineno=child.lineno))
        return rv

    def visit_For(self, node, fstate):
        loop_fstate = fstate.derive()
        loop_fstate.analyze_identfiers([node.target], preassign=True)
        loop_fstate.add_special_identifier(self.config.forloop_accessor,
                                           preassign=True)
        if self.config.forloop_parent_access:
            fstate.add_implicit_lookup(self.config.forloop_accessor)
        loop_fstate.analyze_identfiers(node.body)

        body = []
        loop_else_fstate = fstate.derive()

        if node.else_:
            loop_else_fstate.analyze_identfiers(node.else_)
            did_not_iterate = self.ident_manager.temporary()
            body.append(ast.Assign([ast.Name(did_not_iterate, ast.Store())],
                                    ast.Num(0)))

        if (fstate.config.allow_noniter_unpacking or
            not fstate.config.strict_tuple_unpacking) and \
           isinstance(node.target, nodes.Tuple):
            iter_name = self.ident_manager.temporary()
            target = ast.Name(iter_name, ast.Store())
            body.append(ast.Assign([self.visit(node.target, loop_fstate)],
                ast.Call(ast.Name('lenient_unpack_helper', ast.Load()),
                         [ast.Name('config', ast.Load()),
                          ast.Name(iter_name, ast.Load()),
                          self.make_name_tuple(node.target)], [], None, None)))
        else:
            target = self.visit(node.target, loop_fstate)

        if self.config.forloop_parent_access:
            parent = self.visit(nodes.Name(self.config.forloop_accessor,
                                           'load'), fstate)
        else:
            parent = ast.Name('None', ast.Load())

        iter = self.visit(node.iter, fstate)
        wrapped_iter = self.make_call('config.wrap_loop', [iter, parent])

        loop_accessor = self.visit(nodes.Name(self.config.forloop_accessor,
                                              'store'), loop_fstate)
        tuple_target = ast.Tuple([target, loop_accessor], ast.Store())

        body.extend(self.visit_block(node.body, loop_fstate))
        self.inject_scope_code(loop_fstate, body)

        rv = [ast.For(tuple_target, wrapped_iter, body, [],
                      lineno=node.lineno)]

        if node.else_:
            rv.insert(0, ast.Assign([ast.Name(did_not_iterate, ast.Store())],
                                    ast.Num(1)))
            else_if = ast.If(ast.Name(did_not_iterate, ast.Load()), [], [])
            else_if.body.extend(self.visit_block(node.else_, loop_else_fstate))
            self.inject_scope_code(loop_fstate, else_if.body)
            rv.append(else_if)

        return rv

    def visit_Continue(self, node, fstate):
        return [ast.Continue(lineno=node.lineno)]

    def visit_Break(self, node, fstate):
        return [ast.Break(lineno=node.lineno)]

    def visit_If(self, node, fstate):
        test = self.visit(node.test, fstate)

        condition_fstate = fstate.derive()
        condition_fstate.analyze_identfiers(node.body)
        body = self.visit_block(node.body, condition_fstate)
        self.inject_scope_code(condition_fstate, body)

        if node.else_:
            condition_fstate_else = fstate.derive()
            condition_fstate_else.analyze_identfiers(node.else_)
            else_ = self.visit_block(node.else_, condition_fstate_else)
            self.inject_scope_code(condition_fstate, else_)
        else:
            else_ = []

        return [ast.If(test, body, else_)]

    def visit_ExprStmt(self, node, fstate):
        return ast.Expr(self.visit(node.node, fstate), lineno=node.lineno)

    def visit_Scope(self, node, fstate):
        scope_fstate = fstate.derive()
        scope_fstate.analyze_identfiers(node.body)
        rv = list(self.visit_block(node.body, scope_fstate))
        self.inject_scope_code(scope_fstate, rv)
        return rv

    def visit_FilterBlock(self, node, fstate):
        filter_fstate = fstate.derive()
        filter_fstate.analyze_identfiers(node.body)
        buffer_name = self.ident_manager.temporary()
        filter_fstate.buffer = buffer_name

        filter_args = self.make_resolve_call(node, filter_fstate)
        filter_call = self.make_call('rtstate.info.call_block_filter',
                                     [ast.Str(node.name),
                                      ast.Name(buffer_name, ast.Load())],
                                     filter_args)

        rv = list(self.visit_block(node.body, filter_fstate))
        rv = [ast.Assign([ast.Name(buffer_name, ast.Store())],
                          ast.List([], ast.Load()))] + rv + [
            self.write_output(filter_call, fstate),
            ast.Assign([ast.Name(buffer_name, ast.Store())],
                        ast.Name('None', ast.Load()))
        ]
        self.inject_scope_code(filter_fstate, rv)
        return rv

    def visit_Assign(self, node, fstate):
        # TODO: also allow assignments to tuples
        return self.make_assign(node.target, self.visit(node.node, fstate),
                                fstate, lineno=node.lineno)

    def visit_Import(self, node, fstate):
        vars = self.context_to_lookup(fstate, node)
        lookup = self.make_template_lookup(node.template, fstate)
        info = self.make_template_info('import')
        gen = self.make_template_generator(vars)
        module = self.make_call('info.make_module', [gen])
        rv = lookup + [info]
        rv.extend(self.make_assign(node.target, module, fstate,
                                   lineno=node.lineno))
        return rv

    def visit_FromImport(self, node, fstate):
        vars = self.context_to_lookup(fstate, node)
        lookup = self.make_template_lookup(node.template, fstate)
        info = self.make_template_info('import')
        gen = self.make_template_generator(vars)
        module = self.make_call('info.make_module', [gen])
        mod = self.ident_manager.temporary()
        rv = lookup + [info, ast.Assign([ast.Name(mod, ast.Store())], module)]
        for item in node.items:
            rv.extend(self.make_assign(item.target, self.make_call(
                'config.resolve_from_import',
                [module, self.visit(item.name, fstate)]), fstate,
                lineno=node.lineno))
        return rv

    def visit_Include(self, node, fstate):
        vars = self.context_to_lookup(fstate, node)
        lookup = self.make_template_lookup(node.template, fstate)
        render = self.make_template_render_call(vars, 'include')
        if node.ignore_missing:
            return ast.TryExcept(lookup, [ast.ExceptHandler(
                ast.Name('TemplateNotFound', ast.Load()), None,
                [ast.Pass()])], render)
        return lookup + render

    def visit_Extends(self, node, fstate):
        vars = self.context_to_lookup(fstate, node)
        lookup = self.make_template_lookup(node.template, fstate)
        render = self.make_template_render_call(vars, 'extends')
        return lookup + render + [ast.Return(None)]

    def visit_Block(self, node, fstate):
        block_name = ast.Str(node.name)
        vars = self.context_to_lookup(fstate, node)
        return ast.For(ast.Name('event', ast.Store()),
                       self.make_call('rtstate.evaluate_block',
                                      [block_name, vars]),
                       [ast.Expr(ast.Yield(ast.Name('event', ast.Load())))],
                       [], lineno=node.lineno)

    def visit_CallOut(self, node, fstate):
        callback = self.visit(node.callback, fstate)
        vars = self.context_to_lookup(fstate, node)
        ctx = self.make_call('rtstate.info.make_callout_context', [vars])
        ctxname = fstate.ident_manager.temporary()
        rv = [
            ast.Assign([ast.Name(ctxname, ast.Store())], ctx),
            ast.For(ast.Name('event', ast.Store()),
                      ast.Call(callback, [ast.Name(ctxname, ast.Load())], [],
                               None, None),
                      [self.write_output(ast.Name('event', ast.Load()),
                                         fstate)], [])
        ]
        for sourcename, local_id in fstate.local_identifiers.iteritems():
            rv.append(ast.Assign([ast.Name(local_id, ast.Store())],
                self.make_call('config.resolve_callout_var',
                    [ast.Name(ctxname, ast.Load()), ast.Str(sourcename)])))
        return rv

    def visit_Name(self, node, fstate):
        name = fstate.lookup_name(node.name, node.ctx)
        ctx = self.make_target_context(node.ctx)
        return ast.Name(name, ctx)

    def visit_Getattr(self, node, fstate):
        obj = self.visit(node.node, fstate)
        attr = self.visit(node.attr, fstate)
        return self.make_call('config.getattr', [obj, attr],
                              lineno=node.lineno)

    def visit_Getitem(self, node, fstate):
        obj = self.visit(node.node, fstate)
        arg = self.visit(node.arg, fstate)
        return self.make_call('config.getitem', [obj, arg],
                              lineno=node.lineno)

    def visit_Call(self, node, fstate):
        obj = self.visit(node.node, fstate)
        call_args = self.make_resolve_call(node, fstate)
        return self.make_call('rtstate.info.call', [obj], call_args,
                              lineno=node.lineno)

    def visit_Const(self, node, fstate):
        return self.make_const(node.value, fstate)

    def visit_TemplateData(self, node, fstate):
        return self.make_call('config.mark_safe', [ast.Str(node.data)],
                              lineno=node.lineno)

    def visit_Tuple(self, node, fstate):
        return ast.Tuple([self.visit(x, fstate) for x in node.items],
                         self.make_target_context(node.ctx))

    def visit_List(self, node, fstate):
        return ast.List([self.visit(x, fstate) for x in node.items],
                        ast.Load())

    def visit_Dict(self, node, fstate):
        keys = []
        values = []
        for pair in node.items:
            keys.append(self.visit(pair.key, fstate))
            values.append(self.visit(pair.value, fstate))
        return ast.Dict(keys, values, lineno=node.lineno)

    def visit_Filter(self, node, fstate):
        value = self.visit(node.node, fstate)
        filter_args = self.make_resolve_call(node, fstate)
        return self.make_call('rtstate.info.call_filter',
            [ast.Str(node.name), value], filter_args, lineno=node.lineno)

    def visit_CondExpr(self, node, fstate):
        test = self.visit(node.test, fstate)
        true = self.visit(node.true, fstate)
        false = self.visit(node.false, fstate)
        return ast.IfExp(test, true, false, lineno=node.lineno)

    def visit_MarkSafe(self, node, fstate):
        return self.make_call('config.mark_safe',
            [self.visit(node.expr, fstate)], lineno=node.lineno)

    def visit_MarkSafeIfAutoescape(self, node, fstate):
        value = self.visit(node.expr, fstate)
        return ast.IfExp(self.make_getattr('rtstate.info.autoescape'),
                         self.make_call('config.mark_safe', [value]),
                         value)

    def visit_Function(self, node, fstate):
        name = self.visit(node.name, fstate)
        defaults = ast.List([self.visit(x, fstate) for x in node.defaults],
                            ast.Load())
        arg_names = ast.Tuple([ast.Str(x.name) for x in node.args], ast.Load())
        buffer_name = self.ident_manager.temporary()
        func_fstate = fstate.derive()
        func_fstate.analyze_identfiers(node.args)
        func_fstate.analyze_identfiers(node.body)
        func_fstate.buffer = buffer_name

        internal_name = fstate.ident_manager.temporary()
        body = [ast.Assign([ast.Name(buffer_name, ast.Store())],
                           ast.List([], ast.Load()))]
        body.extend(self.visit_block(node.body, func_fstate))
        funcargs = ast.arguments([self.visit(x, func_fstate)
                                  for x in node.args], None, None, [])
        self.inject_scope_code(func_fstate, body)
        body.append(ast.Return(self.make_call('rtstate.info.concat_template_data',
            [ast.Name(buffer_name, ast.Load())])))

        # XXX: because inner_functions are prepended, the config alias is not
        # yet set up so we have to use rtstate.config.  Is that bad?  I mean,
        # it's certainly not beautiful, but not sure what a beautiful solution
        # would look like.
        fstate.inner_functions.append((
            ast.FunctionDef(internal_name, funcargs, body, [],
                            lineno=node.lineno),
            ast.Assign([ast.Name(internal_name, ast.Store())],
                       self.make_call('rtstate.config.wrap_function',
                       [name, ast.Name(internal_name, ast.Load()),
                        arg_names, defaults], lineno=node.lineno))
        ))
        return ast.Name(internal_name, ast.Load())

    def visit_Slice(self, node, fstate):
        start = self.visit(node.start, fstate)
        if node.stop is not None:
            stop = self.visit(node.stop, fstate)
        else:
            stop = self.Name('None', ast.Load())
        if node.step is not None:
            step = self.visit(node.step, fstate)
        else:
            stop = self.Name('None', ast.Load())
        return self.make_call('slice', [start, stop, step],
                              lineno=node.lineno)

    def binexpr(operator):
        def visitor(self, node, fstate):
            a = self.visit(node.left, fstate)
            b = self.visit(node.right, fstate)
            return ast.BinOp(a, operator(), b, lineno=node.lineno)
        return visitor

    def visit_Concat(self, node, fstate):
        arg = ast.List([self.visit(x, fstate) for x in node.nodes], ast.Load())
        return self.make_call('config.concat', [self.make_getattr('rtstate.info'), arg],
                              lineno=node.lineno)

    visit_Add = binexpr(ast.Add)
    visit_Sub = binexpr(ast.Sub)
    visit_Mul = binexpr(ast.Mult)
    visit_Div = binexpr(ast.Div)
    visit_FloorDiv = binexpr(ast.FloorDiv)
    visit_Mod = binexpr(ast.Mod)
    visit_Pow = binexpr(ast.Pow)
    del binexpr

    def visit_And(self, node, fstate):
        left = self.visit(node.left, fstate)
        right = self.visit(node.right, fstate)
        return ast.BoolOp(ast.And(), [left, right], lineno=node.lineno)

    def visit_Or(self, node, fstate):
        left = self.visit(node.left, fstate)
        right = self.visit(node.right, fstate)
        return ast.BoolOp(ast.Or(), [left, right], lineno=node.lineno)

    def visit_Compare(self, node, fstate):
        left = self.visit(node.expr, fstate)
        ops = []
        comparators = []
        for op in node.ops:
            ops.append(self.make_cmp_op(op.op))
            comparators.append(self.visit(op.expr, fstate))
        return ast.Compare(left, ops, comparators, lineno=node.lineno)

    def visit_Keyword(self, node, fstate):
        return ast.keyword(node.key, self.visit(node.value, fstate),
                           lineno=node.lineno)

    def unary(operator):
        def visitor(self, node, fstate):
            return ast.UnaryOp(operator(), self.visit(node.node, fstate),
                               lineno=node.lineno)
        return visitor

    visit_Pos = unary(ast.UAdd)
    visit_Neg = unary(ast.USub)
    visit_Not = unary(ast.Not)
    del unary

########NEW FILE########
__FILENAME__ = bcinterp
# -*- coding: utf-8 -*-
"""
    templatetk.bcinterp
    ~~~~~~~~~~~~~~~~~~~

    Provides basic utilities that help interpreting the bytecode that comes
    from the AST transformer.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
from types import CodeType
from itertools import izip

from .asttransform import to_ast
from .runtime import RuntimeInfo
from .nodes import Node


def compile_ast(ast, filename='<string>'):
    """Compiles an AST node to bytecode"""
    if isinstance(filename, unicode):
        filename = filename.encode('utf-8')

    # XXX: this is here for debugging purposes during development.
    if os.environ.get('TEMPLATETK_AST_DEBUG'):
        from astutil.codegen import to_source
        print >> sys.stderr, '-' * 80
        ast = to_source(ast)
        print >> sys.stderr, ast
        print >> sys.stderr, '-' * 80

    return compile(ast, filename, 'exec')


def encode_filename(filename):
    """Python requires filenames to be strings."""
    if isinstance(filename, unicode):
        return filename.encode('utf-8')
    return filename


def run_bytecode(code_or_node, filename=None):
    """Evaluates given bytecode, an AST node or an actual ATST node.  This
    returns a dictionary with the results of the toplevel bytecode execution.
    """
    if isinstance(code_or_node, Node):
        code_or_node = to_ast(code_or_node)
        if filename is None:
            filename = encode_filename(code_or_node.filename)
    if not isinstance(code_or_node, CodeType):
        if filename is None:
            filename = '<string>'
        code_or_node = compile_ast(code_or_node, filename)
    namespace = {}
    exec code_or_node in namespace
    return namespace


def recursive_make_undefined(config, targets):
    result = []
    for name in targets:
        if isinstance(name, tuple):
            result.append(recursive_make_undefined(config, name))
        else:
            result.append(config.undefined_variable(name))
    return tuple(result)


def _unpack_tuple_silent(config, values, targets):
    for name, value in izip(targets, values):
        if isinstance(name, tuple):
            yield lenient_unpack_helper(config, value, name)
        else:
            yield value
    diff = len(targets) - len(values)
    for x in xrange(diff):
        yield config.undefined_variable(targets[len(targets) + x - 1])


def lenient_unpack_helper(config, iterable, targets):
    """Can unpack tuples to target names without raising exceptions.  This
    is used by the compiled as helper function in case the config demands
    this behavior.
    """
    try:
        values = tuple(iterable)
    except TypeError:
        if not config.allow_noniter_unpacking:
            raise
        return recursive_make_undefined(config, targets)

    if config.strict_tuple_unpacking:
        return values

    return _unpack_tuple_silent(config, values, targets)


def resolve_call_args(*args, **kwargs):
    """A simple helper function that keeps the compiler code clean.  This
    is used at runtime as a callback for forwarding calls.
    """
    return args, kwargs


def register_block_mapping(info, mapping):
    def _make_executor(render_func):
        def executor(info, vars):
            rtstate = RuntimeState(vars, info.config, info.template_name)
            return render_func(rtstate)
        return executor
    for name, render_func in mapping.iteritems():
        info.register_block(name, _make_executor(render_func))


class RuntimeState(object):
    runtime_info_class = RuntimeInfo

    def __init__(self, context, config, template_name, info=None):
        self.context = context
        self.config = config
        if info is None:
            info = self.runtime_info_class(self.config, template_name)
        self.info = info

    def get_template(self, template_name):
        """Looks up a template."""
        return self.info.get_template(template_name)

    def evaluate_block(self, name, vars=None, level=1):
        """Evaluates a single block."""
        return self.info.evaluate_block(name, level, vars)

    def export_var(self, name, value):
        """Called by the runtime for toplevel assignments."""
        self.info.exports[name] = value

    def lookup_var(self, name):
        """The compiled code will try to find unknown variables with the
        help of this function.  This is the bytecode compiled equivalent
        of :meth:`templatetk.interpreter.InterpreterState.resolve_var` but
        only called for variables that are not yet resolved.
        """
        try:
            return self.context[name]
        except KeyError:
            return self.config.undefined_variable(name)


class MultiMappingLookup(object):

    def __init__(self, mappings):
        self.mappings = mappings

    def __contains__(self, key):
        for d in self.mappings:
            if key in d:
                return True
        return False

    def __getitem__(self, key):
        for d in self.mappings:
            try:
                return d[key]
            except KeyError:
                continue
        raise KeyError(key)

    def __iter__(self):
        found = set()
        for d in self.mappings:
            for key in d:
                if key not in found:
                    found.add(key)
                    yield key

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
"""
    templatetk.config
    ~~~~~~~~~~~~~~~~~

    Implements the compiler configuration object that is passed around
    the system.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from types import MethodType, FunctionType
from itertools import imap

from .runtime import LoopContext, Function
from .utils import Markup


#: the types we support for context functions
_context_function_types = (FunctionType, MethodType)


class Undefined(object):
    # better object by default
    pass


class Config(object):

    def __init__(self):
        self.intercepted_binops = frozenset()
        self.intercepted_unops = frozenset()
        self.forloop_accessor = 'loop'
        self.forloop_parent_access = True
        self.strict_tuple_unpacking = False
        self.allow_noniter_unpacking = False
        self.markup_type = Markup

    def get_autoescape_default(self, template_name):
        return False

    def mark_safe(self, value):
        return self.markup_type(value)

    def getattr(self, obj, attribute):
        # XXX: better defaults maybe
        try:
            return getattr(obj, str(attribute))
        except (UnicodeError, AttributeError):
            try:
                return obj[attribute]
            except (TypeError, LookupError):
                 Undefined()

    def getitem(self, obj, attribute):
        if isinstance(attribute, slice):
            # needed to support the legacy interface of the subscript op
            if attribute.step is None:
                return obj[attribute.start:attribute.stop]
            return obj[attribute]
        return self.getattr(obj, attribute)

    def concat(self, info, iterable):
        return u''.join(imap(unicode, iterable))

    def finalize(self, obj, autoescape):
        if autoescape:
            if hasattr(obj, '__html__'):
                obj = obj.__html__()
            else:
                obj = self.markup_type.escape(unicode(obj))
        return unicode(obj)

    def is_undefined(self, obj):
        return isinstance(obj, Undefined)

    def undefined_variable(self, name):
        return Undefined()

    def is_context_function(self, obj):
        return isinstance(obj, _context_function_types) and \
               getattr(obj, 'contextfunction', False)

    def is_eval_context_function(self, obj):
        return isinstance(obj, _context_function_types) and \
               getattr(obj, 'evalcontextfunction', False)

    def get_filters(self):
        return {}

    def wrap_loop(self, iterator, parent=None):
        return LoopContext(iterator, parent)

    def join_path(self, parent, template_name):
        return template_name

    def get_template(self, template_name):
        raise NotImplementedError('Default config cannot load templates')

    def yield_from_template(self, template, info, view=None):
        raise NotImplementedError('Cannot yield from template objects')

    def iter_template_blocks(self, template):
        raise NotImplementedError('Cannot get blocks from template')

    def make_module(self, template_name, exports, body):
        raise NotImplementedError('Cannot create modules')

    def make_callout_context(self, info, lookup):
        raise NotImplementedError('Cannot create callout contexts')

    def callout_context_changes(self, callout_context):
        raise NotImplementedError('Cannot find callout context changes')

    def wrap_function(self, name, callable, arguments, defaults):
        return Function(self, name, callable, arguments, defaults)

    def resolve_from_import(self, module, attribute):
        return self.getattr(module, attribute)

    def resolve_callout_var(self, callout_ctx, name):
        return callout_ctx[name]

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
    templatetk.exceptions
    ~~~~~~~~~~~~~~~~~~~~~

    Implements the public exception classes.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


class TemplateException(Exception):
    pass


class TemplateNotFound(TemplateException):

    def __init__(self, template_name):
        Exception.__init__(self)
        self.template_name = template_name


class TemplatesNotFound(TemplateNotFound):

    def __init__(self, template_names):
        TemplateNotFound.__init__(self, template_names[0])
        self.template_names = template_names


class BlockNotFoundException(TemplateException):
    pass


class BlockLevelOverflowException(TemplateException):
    pass

########NEW FILE########
__FILENAME__ = frontend
# -*- coding: utf-8 -*-
"""
    templatetk.frontend
    ~~~~~~~~~~~~~~~~~~~

    Basic interface to extend on for template evaluation.  This interface
    is recommended but not necessary.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from .bcinterp import run_bytecode, RuntimeState
from .interpreter import Interpreter, BasicInterpreterState


class Template(object):

    def __init__(self, name, config):
        self.name = name
        self.config = config

    def render(self, context):
        return u''.join(self.execute(context))

    def execute(self, context):
        raise NotImplementedError()


class CompiledTemplate(Template):

    def __init__(self, name, config, code_or_node):
        Template.__init__(self, name, config)
        namespace = run_bytecode(code_or_node)
        self.root_func = namespace['root']

    def execute(self, context):
        rtstate = RuntimeState(context, self.config, self.name)
        return self.root_func(rtstate)


class InterpretedTemplate(Template):
    interpreter_state_class = BasicInterpreterState

    def __init__(self, name, config, node):
        Template.__init__(self, name, config)
        self.node = node

    def execute(self, context):
        state = self.interpreter_state_class(self.config, context)
        interpreter = Interpreter(self.config)
        return interpreter.execute(self.node, state)

########NEW FILE########
__FILENAME__ = fstate
# -*- coding: utf-8 -*-
"""
    templatetk.fstate
    ~~~~~~~~~~~~~~~~~

    Provides an object that encapsulates the state in a frame.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from . import nodes
from .idtracking import IdentTracker, IdentManager


class FrameState(object):

    def __init__(self, config, parent=None, scope='soft',
                 ident_manager=None, root=False):
        assert scope in ('soft', 'hard'), 'unknown scope type'
        self.config = config
        self.parent = parent
        self.scope = scope

        # a map of all identifiers that are active for this current frame.
        # The key is the actual name in the source (y), the value is the
        # name of the local identifier (l_y_0 for instance).
        self.local_identifiers = {}

        # A set of all source names (y) that were referenced from an outer
        # scope at any point in the execution.
        self.from_outer_scope = set()

        # Like `local_identifiers` but also includes identifiers that were
        # referenced from an outer scope.
        self.referenced_identifiers = {}

        # Variables that need to have aliases set up.  The key is the
        # new local name (as in local_identifiers ie: l_y_1) and the value
        # is the old name (l_y_0)
        self.required_aliases = {}

        # variables that require lookup.  The key is the local id (l_y_0),
        # the value is the sourcename (y).
        self.requires_lookup = {}

        # A helper mapping that stores for each source name (y) the node
        # that assigns it.  This is used to to figure out if a variable is
        # assigned at the beginning of the block or later.  If the source
        # node is `None` it means the variable is assigned at the very top.
        self.unassigned_until = {}

        self.inner_functions = []
        self.inner_frames = []
        self.nodes = []
        if ident_manager is None:
            ident_manager = IdentManager()
        self.ident_manager = ident_manager
        self.root = root
        self.buffer = None

    def derive(self, scope='soft', record=True):
        rv = self.__class__(self.config, self, scope, self.ident_manager)
        if record:
            self.inner_frames.append(rv)
        return rv

    def analyze_identfiers(self, nodes, preassign=False):
        tracker = IdentTracker(self, preassign)
        for node in nodes:
            tracker.visit(node)
            self.nodes.append(node)

    def add_special_identifier(self, name, preassign=False):
        self.analyze_identfiers([nodes.Name(name, 'param')],
                                preassign=preassign)

    def add_implicit_lookup(self, name):
        self.analyze_identfiers([nodes.Name(name, 'load')])

    def iter_vars(self, reference_node=None):
        found = set()
        for idmap in self.ident_manager.iter_identifier_maps(self):
            for name, local_id in idmap.iteritems():
                if name in found:
                    continue
                found.add(name)
                if reference_node is not None and \
                   self.var_unassigned(name, reference_node):
                    continue
                yield name, local_id

    def var_unassigned(self, name, reference_node):
        if reference_node is None:
            return True
        assigning_node = self.unassigned_until[name]
        # assigned on block start
        if assigning_node is None:
            return False

        for node in self.iter_frame_nodes():
            if node is reference_node:
                break
            if node is assigning_node:
                return False
        return True

    def iter_inner_referenced_vars(self):
        """Iterates over all variables that are referenced by any of the
        inner frame states from this frame state.  This way we can exactly
        know what variables need to be resolved by an outer frame.
        """
        for inner_frame in self.inner_frames:
            for name, local_id in inner_frame.referenced_identifiers.iteritems():
                if name not in inner_frame.from_outer_scope:
                    continue
                if local_id in inner_frame.required_aliases:
                    local_id = inner_frame.required_aliases[local_id]
                yield local_id, name

    def iter_frame_nodes(self):
        """Iterates over all nodes in the frame in the order they
        appear.
        """
        for node in self.nodes:
            yield node
            for child in node.iter_child_nodes():
                yield child

    def lookup_name(self, name, ctx):
        """Looks up a name to a generated identifier."""
        assert ctx in ('load', 'store', 'param'), 'unknown context'
        for idmap in self.ident_manager.iter_identifier_maps(self):
            if name not in idmap:
                continue
            if ctx != 'load' and idmap is not self.local_identifiers:
                raise AssertionError('tried to store to an identifier '
                                     'that does not have an alias in the '
                                     'identifier map.  Did you forget to '
                                     'analyze_identfiers()?')
            return idmap[name]

        raise AssertionError('identifier %r not found.  Did you forget to '
                             'analyze_identfiers()?' % name)

    def iter_required_lookups(self):
        """Return a dictionary with all required lookups."""
        rv = dict(self.requires_lookup)
        rv.update(self.iter_inner_referenced_vars())
        return rv.iteritems()

########NEW FILE########
__FILENAME__ = idtracking
# -*- coding: utf-8 -*-
"""
    templatetk.idtracking
    ~~~~~~~~~~~~~~~~~~~~~

    Tracks how identifiers are being used in a frame.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from .nodeutils import NodeVisitor


class IdentTracker(NodeVisitor):
    """A helper class that tracks the usage of identifiers."""

    def __init__(self, frame, preassign=False):
        NodeVisitor.__init__(self)
        self.frame = frame
        self.preassign = preassign

    def visit_Block(self, node):
        # do not enter blocks.  It would not harm but cause some
        # totally unnecessary lookups.
        pass

    def visit_Name(self, node):
        from_outer_scope = False
        reused_local_id = False
        local_id = None

        for idmap in self.frame.ident_manager.iter_identifier_maps(self.frame):
            if node.name not in idmap:
                continue
            local_id = idmap[node.name]
            reused_local_id = True
            if idmap is not self.frame.local_identifiers:
                from_outer_scope = True
                if node.ctx != 'load':
                    old = local_id
                    local_id = self.frame.ident_manager.override(node.name)
                    if not self.preassign:
                        self.frame.required_aliases[local_id] = old
            break

        if local_id is None:
            local_id = self.frame.ident_manager.encode(node.name)

        if node.ctx != 'load' or not reused_local_id:
            self.frame.local_identifiers[node.name] = local_id
            unassigned_until = node.ctx != 'param' and node or None
            self.frame.unassigned_until[node.name] = unassigned_until
        if node.ctx == 'load' and not reused_local_id:
            self.frame.requires_lookup[local_id] = node.name
            self.frame.unassigned_until[node.name] = None

        self.frame.referenced_identifiers[node.name] = local_id
        if from_outer_scope:
            self.frame.from_outer_scope.add(node.name)

    def visit_For(self, node):
        self.visit(node.iter)

    def visit_If(self, node):
        self.visit(node.test)

    def vist_Block(self):
        pass

    def visit_Function(self, node):
        self.visit(node.name)
        for arg in node.defaults:
            self.visit(arg)

    def visit_FilterBlock(self, node):
        for arg in node.args:
            self.visit(arg)
        for kwarg in node.kwargs:
            self.visit(kwarg)
        if node.dyn_args is not None:
            self.visit(node.dyn_args)
        if node.dyn_kwargs is not None:
            self.visit(node.dyn_kwargs)


class IdentManager(object):

    def __init__(self, short_ids=False):
        self.index = 1
        self.short_ids = short_ids

    def next_num(self):
        num = self.index
        self.index += 1
        return num

    def override(self, name):
        return self.encode(name, self.next_num())

    def encode(self, name, suffix=0):
        if self.short_ids:
            return 'l%d' % self.next_num()
        return 'l_%s_%d' % (name, suffix)

    def decode(self, name):
        if self.short_ids:
            raise RuntimeError('Cannot decode with short ids')
        if name[:2] != 'l_':
            return False
        return name[2:].rsplit('_', 1)[0]

    def iter_identifier_maps(self, start, stop_at_hard=True):
        ptr = start
        while ptr is not None:
            yield ptr.local_identifiers
            if stop_at_hard and ptr.scope == 'hard':
                break
            ptr = ptr.parent

    def temporary(self):
        return 't%d' % self.next_num()

########NEW FILE########
__FILENAME__ = interpreter
# -*- coding: utf-8 -*-
"""
    templatetk.interpreter
    ~~~~~~~~~~~~~~~~~~~~~~

    Interprets the abstract template syntax tree.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from itertools import izip, chain
from contextlib import contextmanager

from .nodeutils import NodeVisitor
from .runtime import RuntimeInfo
from .exceptions import TemplateNotFound
from . import nodes


empty_iter = iter(())


class InterpreterInternalException(BaseException):
    pass


class ContinueLoop(InterpreterInternalException):
    pass


class BreakLoop(InterpreterInternalException):
    pass


class StopExecutionException(InterpreterInternalException):
    pass


def _assign_name(node, value, state):
    state.assign_var(node.name, value)


def _assign_tuple(node, value, state):
    try:
        values = tuple(value)
    except TypeError:
        if not state.config.allow_noniter_unpacking:
            raise
        return
    if state.config.strict_tuple_unpacking and \
       len(values) != len(node.items):
        raise ValueError('Dimension mismatch on tuple unpacking')
    for subnode, item_val in izip(node.items, value):
        assign_to_state(subnode, item_val, state)


_node_assigners = {
    nodes.Name:         _assign_name,
    nodes.Tuple:        _assign_tuple
}


def assign_to_state(node, value, state):
    func = _node_assigners[node.__class__]
    assert node.can_assign() and func is not None, \
        'Cannot assign to %r' % node
    return func(node, value, state)


class InterpreterState(object):
    runtime_info_class = RuntimeInfo

    def __init__(self, config, template_name, info=None, vars=None):
        self.config = config
        if info is None:
            info = self.make_runtime_info(template_name)
        self.info = info

    def make_runtime_info(self, template_name):
        return self.runtime_info_class(self.config, template_name)

    def evaluate_block(self, node, level=1):
        return self.info.evaluate_block(node.name, level, self)

    @contextmanager
    def frame(self):
        self.push_frame()
        try:
            yield
        finally:
            self.pop_frame()

    def push_frame(self):
        pass

    def pop_frame(self):
        pass

    def __getitem__(self, key):
        raise NotImplementedError()

    def __contains__(self, key):
        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False

    def __iter__(self):
        raise NotImplementedError()

    def resolve_var(self, key):
        try:
            return self.__getitem__(key)
        except KeyError:
            return self.config.undefined_variable(key)

    def assign_var(self, key, value):
        raise NotImplementedError('assigning variables')

    def get_template(self, template_name):
        return self.info.get_template(template_name)

    def get_or_select_template(self, template_name_or_list):
        return self.info.get_or_select_template(template_name_or_list)


class BasicInterpreterState(InterpreterState):

    def __init__(self, config, template_name=None, info=None, vars=None):
        InterpreterState.__init__(self, config, template_name, info, vars)
        self.context = []
        if vars is not None:
            self.context.append(vars)
        self.push_frame()
        self.toplevel = self.context[-1]

    def push_frame(self):
        self.context.append({})

    def pop_frame(self):
        self.context.pop()

    def assign_var(self, key, value):
        ctx = self.context[-1]
        ctx[key] = value
        if ctx is self.toplevel:
            self.info.exports[key] = value

    def __getitem__(self, key):
        for d in reversed(self.context):
            try:
                return d[key]
            except KeyError:
                continue
        raise KeyError(key)

    def __iter__(self):
        found = set()
        for d in reversed(self.context):
            for key in d:
                if key not in found:
                    found.add(key)
                    yield key


class Interpreter(NodeVisitor):
    """The interpreter can be used to evaluate a given ASTS.  Internally
    it is based on a generator model.  Statement nodes yield unicode
    chunks and can be evaluated one after another based on that.  Expression
    nodes return the result of their operation.
    """

    def __init__(self, config):
        NodeVisitor.__init__(self)
        self.config = config

    def resolve_call_args(self, node, state):
        args = [self.visit(arg, state) for arg in node.args]
        kwargs = dict(self.visit(arg, state) for arg in node.kwargs)
        if node.dyn_args is not None:
            dyn_args = self.visit(node.dyn_args, state)
        else:
            dyn_args = ()
        if node.dyn_kwargs is not None:
            for key, value in self.visit(node.dyn_kwargs, state).iteritems():
                if key in kwargs:
                    raise TypeError('got multiple values for keyword '
                                    'argument %r' % key)
                kwargs[key] = value
        return chain(args, dyn_args), kwargs

    def evaluate(self, node, state):
        assert state.config is self.config, 'config mismatch'
        return self.visit(node, state)

    def execute(self, node, state):
        try:
            for event in self.evaluate(node, state):
                yield event
        except StopExecutionException:
            pass
        except InterpreterInternalException, e:
            raise AssertionError('An interpreter internal exception '
                                 'was raised.  ASTS might be invalid. '
                                 'Got (%r)' % e)

    def make_block_executor(self, node, state_class):
        def executor(info, vars):
            state = state_class(info.config, info.template_name, info, vars)
            for event in self.visit_block(node.body, state):
                yield event
        return executor

    def visit_block(self, nodes, state):
        if nodes:
            for node in nodes:
                rv = self.visit(node, state)
                assert rv is not None, 'visitor for %r failed' % node
                for event in rv:
                    yield event

    def iter_blocks(self, node, state_class):
        for block in node.find_all(nodes.Block):
            yield block.name, self.make_block_executor(block, state_class)

    def visit_Template(self, node, state):
        for block, executor in self.iter_blocks(node, type(state)):
            state.info.register_block(block, executor)
        for event in self.visit_block(node.body, state):
            yield event

    def visit_Output(self, node, state):
        for node in node.nodes:
            yield state.info.finalize(self.visit(node, state))

    def visit_For(self, node, state):
        parent = None
        if self.config.forloop_parent_access:
            parent = state.resolve_var(self.config.forloop_accessor)
        iterator = self.visit(node.iter, state)

        state.push_frame()
        iterated = False
        for item, loop_state in self.config.wrap_loop(iterator, parent):
            try:
                iterated = True
                state.assign_var(self.config.forloop_accessor, loop_state)
                assign_to_state(node.target, item, state)
                for event in self.visit_block(node.body, state):
                    yield event
            except ContinueLoop:
                continue
            except BreakLoop:
                break
        state.pop_frame()

        if not iterated and node.else_:
            state.push_frame()
            for event in self.visit_block(node.else_, state):
                yield event
            state.pop_frame()

    def visit_Continue(self, node, state):
        raise ContinueLoop()

    def visit_Break(self, node, state):
        raise BreakLoop()

    def visit_If(self, node, state):
        test = self.visit(node.test, state)
        eventiter = ()
        if test:
            eventiter = self.visit_block(node.body, state)
        elif node.else_ is not None:
            eventiter = self.visit_block(node.else_, state)

        state.push_frame()
        for event in eventiter:
            yield event
        state.pop_frame()

    def visit_Assign(self, node, state):
        assert node.target.ctx == 'store'
        value = self.visit(node.node, state)
        assign_to_state(node.target, value, state)
        return empty_iter

    def visit_CallOut(self, node, state):
        callback = self.visit(node.callback, state)
        ctx = state.info.make_callout_context(state)
        for event in callback(ctx):
            yield event
        for key, value in state.config.callout_context_changes(ctx):
            state.assign_var(key, value)

    def visit_Name(self, node, state):
        assert node.ctx == 'load', 'visiting store nodes does not make sense'
        return state.resolve_var(node.name)

    def visit_Getattr(self, node, state):
        obj = self.visit(node.node, state)
        attr = self.visit(node.attr, state)
        return self.config.getattr(obj, attr)

    def visit_Getitem(self, node, state):
        obj = self.visit(node.node, state)
        attr = self.visit(node.arg, state)
        return self.config.getitem(obj, attr)

    def visit_Call(self, node, state):
        obj = self.visit(node.node, state)
        args, kwargs = self.resolve_call_args(node, state)
        return state.info.call(obj, args, kwargs)

    def visit_Keyword(self, node, state):
        return node.key, self.visit(node.value, state)

    def visit_Const(self, node, state):
        return node.value

    def visit_TemplateData(self, node, state):
        return state.config.markup_type(node.data)

    def visit_Tuple(self, node, state):
        assert node.ctx == 'load'
        return tuple(self.visit(x, state) for x in node.items)

    def visit_List(self, node, state):
        return list(self.visit(x, state) for x in node.items)

    def visit_Dict(self, node, state):
        return dict(self.visit(x, state) for x in node.items)

    def visit_Pair(self, node, state):
        return self.visit(node.key, state), self.visit(node.value, state)

    def visit_CondExpr(self, node, state):
        if self.visit(node.test, state):
            return self.visit(node.true, state)
        return self.visit(node.false, state)

    def binexpr(node_class):
        functor = nodes.binop_to_func[node_class.operator]
        def visitor(self, node, state):
            a = self.visit(node.left, state)
            b = self.visit(node.right, state)
            return functor(a, b)
        return visitor

    visit_Add = binexpr(nodes.Add)
    visit_Sub = binexpr(nodes.Sub)
    visit_Mul = binexpr(nodes.Mul)
    visit_Div = binexpr(nodes.Div)
    visit_FloorDiv = binexpr(nodes.FloorDiv)
    visit_Mod = binexpr(nodes.Mod)
    visit_Pow = binexpr(nodes.Pow)
    del binexpr

    def visit_And(self, node, state):
        rv = self.visit(node.left, state)
        if not rv:
            return False
        return self.visit(node.right, state)

    def visit_Or(self, node, state):
        rv = self.visit(node.left, state)
        if rv:
            return rv
        return self.visit(node.right, state)

    def unary(node_class):
        functor = nodes.uaop_to_func[node_class.operator]
        def visitor(self, node, state):
            return functor(self.visit(node.node, state))
        return visitor

    visit_Pos = unary(nodes.Pos)
    visit_Neg = unary(nodes.Neg)
    visit_Not = unary(nodes.Not)
    del unary

    def visit_Compare(self, node, state):
        left = self.visit(node.expr, state)
        for op in node.ops:
            right = self.visit(op.expr, state)
            if not nodes.cmpop_to_func[op.op](left, right):
                return False
            left = right
        return True

    def visit_Filter(self, node, state):
        value = self.visit(node.node, state)
        args, kwargs = self.resolve_call_args(node, state)
        return state.info.call_filter(node.name, value, args, kwargs)

    def visit_Slice(self, node, state):
        return slice(self.visit(node.start, state),
                     self.visit(node.stop, state),
                     self.visit(node.step, state))

    def visit_MarkSafe(self, node, state):
        return state.config.markup_type(self.visit(node.expr, state))

    def visit_MarkSafeIfAutoescape(self, node, state):
        value = self.visit(node.expr, state)
        if state.info.autoescape:
            value = state.config.markup_type(self.visit(node.expr, state))
        return value

    def visit_Function(self, node, state):
        defaults = [self.visit(x, state) for x in node.defaults]
        def _eval_func(*args):
            state.push_frame()
            for target, value in izip(node.args, args):
                assign_to_state(target, value, state)
            rv = u''.join(self.visit_block(node.body, state))
            state.pop_frame()
            return self.config.markup_type(rv)
        name = self.visit(node.name, state)
        arg_names = tuple([x.name for x in node.args])
        return state.config.wrap_function(name, _eval_func, arg_names,
                                          defaults)

    def visit_Scope(self, node, state):
        with state.frame():
            for event in self.visit_block(node.body, state):
                yield event

    def visit_ExprStmt(self, node, state):
        self.visit(node.node, state)
        return empty_iter

    def visit_Block(self, node, state):
        with state.frame():
            for event in state.evaluate_block(node):
                yield event

    def visit_Extends(self, node, state):
        template_name = self.visit(node.template, state)
        template = state.get_template(template_name)
        info = state.info.make_info(template, template_name, 'extends')
        for event in state.config.yield_from_template(template, info,
                                                      state):
            yield event
        raise StopExecutionException()

    def visit_FilterBlock(self, node, state):
        with state.frame():
            value = ''.join(self.visit_block(node.body, state))
            args, kwargs = self.resolve_call_args(node, state)
            yield state.info.call_filter(node.name, value, args, kwargs)

    def visit_Include(self, node, state):
        template_name = self.visit(node.template, state)
        try:
            template = state.get_or_select_template(template_name)
        except TemplateNotFound:
            if not node.ignore_missing:
                raise
            return
        info = state.info.make_info(template, template_name, 'include')
        for event in state.config.yield_from_template(template, info,
                                                      state):
            yield event

    def resolve_import(self, node, state):
        template_name = self.visit(node.template, state)
        template = state.get_template(template_name)
        info = state.info.make_info(template, template_name, 'import')
        gen = state.config.yield_from_template(template, info,
                                               state)
        return info.make_module(gen)

    def visit_Import(self, node, state):
        module = self.resolve_import(node, state)
        assign_to_state(node.target, module, state)
        return empty_iter

    def visit_FromImport(self, node, state):
        module = self.resolve_import(node, state)
        for item in node.items:
            name = self.visit(item.name, state)
            imported_object = state.config.resolve_from_import(module, name)
            assign_to_state(item.target, imported_object, state)
        return empty_iter

########NEW FILE########
__FILENAME__ = jscompiler
# -*- coding: utf-8 -*-
"""
    templatetk.jscompiler
    ~~~~~~~~~~~~~~~~~~~~~

    This module can compile a node tree to JavaScript.  Not all that
    can be compiled to Python bytecode can also be compiled to JavaScript
    though.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from StringIO import StringIO

from . import nodes
from .nodeutils import NodeVisitor
from .idtracking import IdentManager
from .fstate import FrameState
from .utils import json


class StopFrameCompilation(Exception):
    pass


class JavaScriptWriter(object):

    def __init__(self, stream, indentation=2):
        self.stream_stack = [stream]
        self.indentation = indentation

        self._new_lines = 0
        self._first_write = True
        self._indentation = 0

    def indent(self):
        self._indentation += 1

    def outdent(self, step=1):
        self._indentation -= step

    def write(self, x):
        """Write a string into the output stream."""
        stream = self.stream_stack[-1]
        if self._new_lines:
            if self.indentation >= 0:
                if not self._first_write:
                    stream.write('\n' * self._new_lines)
                self._first_write = False
                stream.write(' ' * (self.indentation * self._indentation))
            self._new_lines = 0
        if isinstance(x, unicode):
            x = x.encode('utf-8')
        stream.write(x)

    def write_newline(self, node=None, extra=0):
        self._new_lines = max(self._new_lines, 1 + extra)
        if node is not None and node.lineno != self._last_line:
            self._write_debug_info = node.lineno
            self._last_line = node.lineno

    def write_line(self, x, node=None, extra=0):
        self.write_newline(node, extra)
        self.write(x)

    def dump_object(self, obj):
        separators = None
        if self.indentation < 0:
            separators = (',', ':')
        return json.dumps(obj, separators=separators)

    def write_repr(self, obj):
        return self.write(self.dump_object(obj))

    def write_from_buffer(self, buffer):
        buffer.seek(0)
        while 1:
            chunk = buffer.read(4096)
            if not chunk:
                break
            self.stream_stack[-1].write(chunk)

    def start_buffering(self):
        new_stream = StringIO()
        self.stream_stack.append(new_stream)
        return new_stream

    def end_buffering(self):
        self.stream_stack.pop()


def to_javascript(node, stream=None, short_ids=False, indentation=2):
    """Converts a template to JavaScript."""
    if stream is None:
        stream = StringIO()
        as_string = True
    else:
        as_string = False
    gen = JavaScriptGenerator(stream, node.config, short_ids, indentation)
    gen.visit(node, None)
    if as_string:
        return stream.getvalue()


class JavaScriptGenerator(NodeVisitor):

    def __init__(self, stream, config, short_ids=False, indentation=2):
        NodeVisitor.__init__(self)
        self.config = config
        self.writer = JavaScriptWriter(stream, indentation)
        self.ident_manager = IdentManager(short_ids=short_ids)

    def begin_rtstate_func(self, name, with_writer=True):
        self.writer.write_line('function %s(rts) {' % name)
        self.writer.indent()
        if with_writer:
            self.writer.write_line('var w = rts.writeFunc;')

    def end_rtstate_func(self):
        self.writer.outdent()
        self.writer.write_line('}')

    def compile(self, node):
        assert isinstance(node, nodes.Template), 'can only transform ' \
            'templates, got %r' % node.__class__.__name__
        return self.visit(node, None)

    def write_scope_code(self, fstate):
        vars = []
        already_handled = set()
        for alias, old_name in fstate.required_aliases.iteritems():
            already_handled.add(alias)
            vars.append('%s = %s' % (alias, old_name))

        # at that point we know about the inner states and can see if any
        # of them need variables we do not have yet assigned and we have to
        # resolve for them.
        for target, sourcename in fstate.iter_required_lookups():
            already_handled.add(target)
            vars.append('%s = rts.lookupVar("%s")' % (
                target,
                sourcename
            ))

        # handle explicit var
        for name, local_id in fstate.local_identifiers.iteritems():
            if local_id not in already_handled:
                vars.append(local_id)

        if vars:
            self.writer.write_line('var %s;' % ', '.join(vars));

    def write_assign(self, target, expr, fstate):
        assert isinstance(target, nodes.Name), 'can only assign to names'
        name = fstate.lookup_name(target.name, 'store')
        self.writer.write_line('%s = ' % name)
        self.visit(expr, fstate)
        self.writer.write(';')
        if fstate.root:
            self.writer.write_line('rts.exportVar("%s", %s);' % (
                target.name,
                name
            ))

    def make_target_name_tuple(self, target):
        assert target.ctx in ('store', 'param')
        assert isinstance(target, (nodes.Name, nodes.Tuple))

        if isinstance(target, nodes.Name):
            return [target.name]

        def walk(obj):
            rv = []
            for node in obj.items:
                if isinstance(node, nodes.Name):
                    rv.append(node.name)
                elif isinstance(node, nodes.Tuple):
                    rv.append(walk(node))
                else:
                    assert 0, 'unsupported assignment to %r' % node
            return rv
        return walk(target)

    def write_assignment(self, node, fstate):
        rv = []
        def walk(obj):
            if isinstance(obj, nodes.Name):
                rv.append(fstate.lookup_name(obj.name, node.ctx))
                return
            for child in obj.items:
                walk(child)
        walk(node)
        self.writer.write(', '.join(rv))

    def write_context_as_object(self, fstate, reference_node):
        d = dict(fstate.iter_vars(reference_node))
        if not d:
            self.writer.write('rts.context')
            return
        self.writer.write('rts.makeOverlayContext({')
        for idx, (name, local_id) in enumerate(d.iteritems()):
            if idx:
                self.writer.write(', ')
            self.writer.write('%s: %s' % (self.writer.dump_object(name), local_id))
        self.writer.write('})')

    def start_buffering(self, fstate):
        self.writer.write_line('w = rts.startBuffering()')

    def return_buffer_contents(self, fstate, write_to_var=False):
        tmp = self.ident_manager.temporary()
        self.writer.write_line('var %s = rts.endBuffering();' % tmp)
        self.writer.write_line('w = %s[0];' % tmp)
        if write_to_var:
            self.writer.write_line('%s = %s[1];' % (tmp, tmp))
            return tmp
        else:
            self.writer.write_line('return %s[1];' % tmp)

    def visit_block(self, nodes, fstate):
        self.writer.write_newline()
        try:
            for node in nodes:
                self.visit(node, fstate)
        except StopFrameCompilation:
            pass

    def visit_Template(self, node, fstate):
        assert fstate is None, 'framestate passed to template visitor'
        fstate = FrameState(self.config, ident_manager=self.ident_manager,
                            root=True)
        fstate.analyze_identfiers(node.body)

        self.writer.write_line('(function(rt) {')
        self.writer.indent()

        self.begin_rtstate_func('root')
        buffer = self.writer.start_buffering()
        self.visit_block(node.body, fstate)
        self.writer.end_buffering()
        self.write_scope_code(fstate)
        self.writer.write_from_buffer(buffer)
        self.end_rtstate_func()

        self.begin_rtstate_func('setup', with_writer=False)
        self.writer.write_line('rt.registerBlockMapping(rts.info, blocks);')
        self.end_rtstate_func()

        for block_node in node.find_all(nodes.Block):
            block_fstate = fstate.derive(scope='hard')
            block_fstate.analyze_identfiers(block_node.body)
            self.begin_rtstate_func('block_' + block_node.name)
            buffer = self.writer.start_buffering()
            self.visit_block(block_node.body, block_fstate)
            self.writer.end_buffering()
            self.write_scope_code(block_fstate)
            self.writer.write_from_buffer(buffer)
            self.end_rtstate_func()

        self.writer.write_line('var blocks = {');
        for idx, block_node in enumerate(node.find_all(nodes.Block)):
            if idx:
                self.writer.write(', ')
            self.writer.write('"%s": block_%s' % (block_node.name,
                                                  block_node.name))
        self.writer.write('};')

        self.writer.write_line('return rt.makeTemplate(root, setup, blocks);')

        self.writer.outdent()
        self.writer.write_line('})')

    def visit_For(self, node, fstate):
        loop_fstate = fstate.derive()
        loop_fstate.analyze_identfiers([node.target], preassign=True)
        loop_fstate.add_special_identifier(self.config.forloop_accessor,
                                           preassign=True)
        if self.config.forloop_parent_access:
            fstate.add_implicit_lookup(self.config.forloop_accessor)
        loop_fstate.analyze_identfiers(node.body)

        loop_else_fstate = fstate.derive()
        if node.else_:
            loop_else_fstate.analyze_identfiers(node.else_)

        self.writer.write_line('rt.iterate(')
        self.visit(node.iter, loop_fstate)
        nt = self.make_target_name_tuple(node.target)
        self.writer.write(', ')
        if self.config.forloop_parent_access:
            self.visit(nodes.Name(self.config.forloop_accessor, 'load'), fstate)
        else:
            self.writer.write('null')
        self.writer.write(', %s, function(%s, ' % (
            self.writer.dump_object(nt),
            loop_fstate.lookup_name(self.config.forloop_accessor, 'store')
        ))
        self.write_assignment(node.target, loop_fstate)
        self.writer.write(') {')

        self.writer.indent()
        buffer = self.writer.start_buffering()
        self.visit_block(node.body, loop_fstate)
        self.writer.end_buffering()
        self.write_scope_code(loop_fstate)
        self.writer.write_from_buffer(buffer)
        self.writer.outdent()
        self.writer.write_line('}, ');

        if node.else_:
            self.writer.write('function() {')
            self.writer.indent()
            buffer = self.writer.start_buffering()
            self.visit_block(node.else_, loop_else_fstate)
            self.writer.end_buffering()
            self.write_scope_code(loop_else_fstate)
            self.writer.write_from_buffer(buffer)
            self.writer.outdent()
            self.writer.write('}')
        else:
            self.writer.write('null')

        self.writer.write(');')

    def visit_If(self, node, fstate):
        self.writer.write_line('if (')
        self.visit(node.test, fstate)
        self.writer.write(') { ')

        condition_fstate = fstate.derive()
        condition_fstate.analyze_identfiers(node.body)
        self.writer.indent()
        buffer = self.writer.start_buffering()
        self.visit_block(node.body, condition_fstate)
        self.writer.end_buffering()
        self.write_scope_code(condition_fstate)
        self.writer.write_from_buffer(buffer)
        self.writer.outdent()

        if node.else_:
            self.writer.write_line('} else {')
            self.writer.indent()
            condition_fstate_else = fstate.derive()
            condition_fstate_else.analyze_identfiers(node.else_)
            buffer = self.writer.start_buffering()
            self.visit_block(node.else_, condition_fstate_else)
            self.writer.end_buffering()
            self.write_scope_code(condition_fstate)
            self.writer.write_from_buffer(buffer)
            self.writer.outdent()
        else:
            else_ = []
        self.writer.write_line('}')

    def visit_Output(self, node, fstate):
        for child in node.nodes:
            self.writer.write_line('w(')
            if isinstance(child, nodes.TemplateData):
                self.writer.write_repr(child.data)
            else:
                self.writer.write('rts.info.finalize(')
                self.visit(child, fstate)
                self.writer.write(')')
            self.writer.write(');')

    def visit_Extends(self, node, fstate):
        self.writer.write_line('return rts.extendTemplate(')
        self.visit(node.template, fstate)
        self.writer.write(', ')
        self.write_context_as_object(fstate, node)
        self.writer.write(', w);')

        if fstate.root:
            raise StopFrameCompilation()

    def visit_Block(self, node, fstate):
        self.writer.write_line('rts.evaluateBlock("%s", ' % node.name)
        self.write_context_as_object(fstate, node)
        self.writer.write(');')

    def visit_Function(self, node, fstate):
        func_fstate = fstate.derive()
        func_fstate.analyze_identfiers(node.args)
        func_fstate.analyze_identfiers(node.body)

        argnames = [x.name for x in node.args]
        self.writer.write('rt.wrapFunction(')
        self.visit(node.name, fstate)
        self.writer.write(', %s, [' % self.writer.dump_object(argnames))

        for idx, arg in enumerate(node.defaults or ()):
            if idx:
                self.writer.write(', ')
            self.visit(arg, func_fstate)

        self.writer.write('], function(')

        for idx, arg in enumerate(node.args):
            if idx:
                self.writer.write(', ')
            self.visit(arg, func_fstate)

        self.writer.write(') {')
        self.writer.write_newline()
        self.writer.indent()

        buffer = self.writer.start_buffering()
        self.start_buffering(func_fstate)
        self.visit_block(node.body, func_fstate)
        self.writer.end_buffering()
        self.write_scope_code(func_fstate)
        self.writer.write_from_buffer(buffer)
        self.return_buffer_contents(func_fstate)

        self.writer.outdent()
        self.writer.write_line('})')

    def visit_Assign(self, node, fstate):
        self.writer.write_newline()
        self.write_assign(node.target, node.node, fstate)

    def visit_Name(self, node, fstate):
        name = fstate.lookup_name(node.name, node.ctx)
        self.writer.write(name)

    def visit_Const(self, node, fstate):
        self.writer.write_repr(node.value)

    def visit_Getattr(self, node, fstate):
        self.visit(node.node, fstate)
        self.writer.write('[')
        self.visit(node.attr, fstate)
        self.writer.write(']')

    def visit_Getitem(self, node, fstate):
        self.visit(node.node, fstate)
        self.writer.write('[')
        self.visit(node.arg, fstate)
        self.writer.write(']')

    def visit_Call(self, node, fstate):
        # XXX: For intercepting this it would be necessary to extract the
        # rightmost part of the dotted expression in node.node so that the
        # owner can be preserved for JavaScript (this)
        self.visit(node.node, fstate)
        self.writer.write('(')
        for idx, arg in enumerate(node.args):
            if idx:
                self.writer.write(', ')
            self.visit(arg, fstate)
        self.writer.write(')')

        if node.kwargs or node.dyn_args or node.dyn_kwargs:
            raise NotImplementedError('Dynamic calls or keyword arguments '
                                      'not available with javascript')

    def visit_TemplateData(self, node, fstate):
        self.writer.write('rt.markSafe(')
        self.writer.write_repr(node.data)
        self.writer.write(')')

    def visit_Tuple(self, node, fstate):
        raise NotImplementedError('Tuples not possible in JavaScript')

    def visit_List(self, node, fstate):
        self.writer.write('[')
        for idx, child in enumerate(node.items):
            if idx:
                self.writer.write(', ')
            self.visit(child, fstate)
        self.writer.write(']')

    def visit_Dict(self, node, fstate):
        self.writer.write('({')
        for idx, pair in enumerate(node.items):
            if idx:
                self.writer.write(', ')
            if not isinstance(pair.key, nodes.Const):
                raise NotImplementedError('Constant dict key required with javascript')
            # hack to have the same logic as json.dumps for keys
            self.writer.write(json.dumps({pair.key.value: 0})[1:-4] + ': ')
            self.visit(pair.value, fstate)
        self.writer.write('})')

    def visit_Filter(self, node, fstate):
        self.writer.write('rts.info.callFilter(')
        self.writer.write(', ')
        self.writer.write_repr(node.name)
        self.visit(node.node, fstate)
        self.writer.write(', [')
        for idx, arg in enumerate(node.args):
            if idx:
                self.writer.write(', ')
            self.visit(arg, fstate)
        self.writer.write('])')

        if node.kwargs or node.dyn_args or node.dyn_kwargs:
            raise NotImplementedError('Dynamic calls or keyword arguments '
                                      'not available with javascript')

    def visit_CondExpr(self, node, fstate):
        self.writer.write('(')
        self.visit(node.test, fstate)
        self.writer.write(' ? ')
        self.visit(node.true, fstate)
        self.writer.write(' : ')
        self.visit(node.false, fstate)
        self.writer.write(')')

    def visit_Slice(self, node, fstate):
        raise NotImplementedError('Slicing not possible with JavaScript')

    def binexpr(operator):
        def visitor(self, node, fstate):
            self.writer.write('(')
            self.visit(node.left, fstate)
            self.writer.write(' %s ' % operator)
            self.visit(node.right, fstate)
            self.writer.write(')')
        return visitor

    def visit_Concat(self, node, fstate):
        self.writer.write('rt.concat(rts.info, [')
        for idx, child in enumerate(node.nodes):
            if idx:
                self.writer.write(', ')
            self.visit(child, fstate)
        self.writer.write('])')

    visit_Add = binexpr('+')
    visit_Sub = binexpr('-')
    visit_Mul = binexpr('*')
    visit_Div = binexpr('/')
    visit_Mod = binexpr('%')
    del binexpr

    def visit_FloorDiv(self, node, fstate):
        self.writer.write('parseInt(')
        self.visit(node.left, fstate)
        self.writer.write(' / ')
        self.visit(node.right, fstate)
        self.writer.write(')')

    def visit_Pow(self, node, fstate):
        self.writer.write('Math.pow(')
        self.visit(node.left, fstate)
        self.writer.write(', ')
        self.visit(node.right, fstate)
        self.writer.write(')')

    def visit_And(self, node, fstate):
        self.writer.write('(')
        self.visit(node.left, fstate)
        self.writer.write(' && ')
        self.visit(node.right, fstate)
        self.writer.write(')')

    def visit_Or(self, node, fstate):
        self.writer.write('(')
        self.visit(node.left, fstate)
        self.writer.write(' || ')
        self.visit(node.right, fstate)
        self.writer.write(')')

    def visit_Not(self, node, fstate):
        self.writer.write('!(')
        self.visit(node.node, fstate)
        self.writer.write(')')

    def visit_Compare(self, node, fstate):
        self.writer.write('(')
        self.visit(node.expr, fstate)
        assert len(node.ops) == 1, 'Comparison of two expressions is supported'
        self.visit(node.ops[0], fstate)
        self.writer.write(')')

    def visit_Operand(self, node, fstate):
        cmp_ops = {
            'gt': '>',
            'gteq': '>=',
            'eq': '==',
            'ne': '!=',
            'lteq': '<=',
            'lt': '<'
        }

        self.writer.write(' ')
        self.writer.write(cmp_ops.get(node.op, ''))
        self.writer.write(' ')
        self.visit(node.expr, fstate)

########NEW FILE########
__FILENAME__ = nodes
# -*- coding: utf-8 -*-
"""
    templatetk.nodes
    ~~~~~~~~~~~~~~~~

    Implements the AST of the templating language itself.  To avoid confusion
    in terms with the Python AST which is used for compilation, this is
    internally as ATST (Abstract Template Syntax Tree).

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import operator
from itertools import izip
from collections import deque


binop_to_func = {
    '*':        operator.mul,
    '/':        operator.truediv,
    '//':       operator.floordiv,
    '**':       operator.pow,
    '%':        operator.mod,
    '+':        operator.add,
    '-':        operator.sub
}

uaop_to_func = {
    'not':      operator.not_,
    '+':        operator.pos,
    '-':        operator.neg
}

cmpop_to_func = {
    'eq':       operator.eq,
    'ne':       operator.ne,
    'gt':       operator.gt,
    'gteq':     operator.ge,
    'lt':       operator.lt,
    'lteq':     operator.le,
    'in':       lambda a, b: a in b,
    'notin':    lambda a, b: a not in b
}


nodes_by_name = {}


class Impossible(Exception):
    """Raised if the node could not perform a requested action."""


class NodeType(type):
    """A metaclass for nodes that handles the field and attribute
    inheritance.  fields and attributes from the parent class are
    automatically forwarded to the child."""

    def __new__(cls, name, bases, d):
        newslots = []
        assert len(bases) == 1, 'multiple inheritance not allowed'
        for attr in 'fields', 'attributes':
            names = d.get(attr, ())
            storage = []
            storage.extend(getattr(bases[0], attr, ()))
            storage.extend(names)
            assert len(storage) == len(set(storage)), 'layout conflict'
            d[attr] = tuple(storage)
            newslots.extend(names)
        d.setdefault('abstract', False)
        d['__slots__'] = newslots
        rv = type.__new__(cls, name, bases, d)
        assert name not in nodes_by_name, 'Node naming conflict %r' % name
        nodes_by_name[name] = rv
        return rv


class Node(object):
    """Baseclass for all templatetk nodes.  There are a number of nodes available
    of different types.  There are four major types:

    -   :class:`Stmt`: statements
    -   :class:`Expr`: expressions
    -   :class:`Helper`: helper nodes
    -   :class:`Template`: the outermost wrapper node

    All nodes have fields and attributes.  Fields may be other nodes, lists,
    or arbitrary values.  Fields are passed to the constructor as regular
    positional arguments, attributes as keyword arguments.  Each node has
    two attributes: `lineno` (the line number of the node) and `config`.
    The `config` attribute is set at the end of the parsing process for
    all nodes automatically.
    """
    __metaclass__ = NodeType
    fields = ()
    attributes = ('lineno', 'config')
    abstract = True

    def __init__(self, *fields, **attributes):
        if self.abstract:
            raise TypeError('abstract nodes are not instanciable')
        if fields:
            if len(fields) != len(self.fields):
                if not self.fields:
                    raise TypeError('%r takes 0 arguments' %
                                    self.__class__.__name__)
                raise TypeError('%r takes 0 or %d argument%s, got %d' % (
                    self.__class__.__name__,
                    len(self.fields),
                    len(self.fields) != 1 and 's' or '',
                    len(fields)
                ))
            for name, arg in izip(self.fields, fields):
                setattr(self, name, arg)
        for attr in self.attributes:
            setattr(self, attr, attributes.pop(attr, None))
        if attributes:
            raise TypeError('unknown attribute %r' %
                            iter(attributes).next())

    def iter_fields(self, exclude=None, only=None):
        """This method iterates over all fields that are defined and yields
        ``(key, value)`` tuples.  Per default all fields are returned, but
        it's possible to limit that to some fields by providing the `only`
        parameter or to exclude some using the `exclude` parameter.  Both
        should be sets or tuples of field names.
        """
        for name in self.fields:
            if (exclude is only is None) or \
               (exclude is not None and name not in exclude) or \
               (only is not None and name in only):
                try:
                    yield name, getattr(self, name)
                except AttributeError:
                    pass

    def iter_child_nodes(self, exclude=None, only=None):
        """Iterates over all direct child nodes of the node.  This iterates
        over all fields and yields the values of they are nodes.  If the value
        of a field is a list all the nodes in that list are returned.
        """
        for field, item in self.iter_fields(exclude, only):
            if isinstance(item, list):
                for n in item:
                    if isinstance(n, Node):
                        yield n
            elif isinstance(item, Node):
                yield item

    def find(self, node_type):
        """Find the first node of a given type.  If no such node exists the
        return value is `None`.
        """
        for result in self.find_all(node_type):
            return result

    def find_all(self, node_type):
        """Find all the nodes of a given type.  If the type is a tuple,
        the check is performed for any of the tuple items.
        """
        for child in self.iter_child_nodes():
            if isinstance(child, node_type):
                yield child
            for result in child.find_all(node_type):
                yield result

    def set_ctx(self, ctx):
        """Reset the context of a node and all child nodes.  Per default the
        parser will all generate nodes that have a 'load' context as it's the
        most common one.  This method is used in the parser to set assignment
        targets and other nodes to a store context.
        """
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if 'ctx' in node.fields:
                node.ctx = ctx
            todo.extend(node.iter_child_nodes())
        return self

    def set_lineno(self, lineno, override=False):
        """Set the line numbers of the node and children."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            if 'lineno' in node.attributes:
                if node.lineno is None or override:
                    node.lineno = lineno
            todo.extend(node.iter_child_nodes())
        return self

    def set_config(self, config):
        """Set the config for all nodes."""
        todo = deque([self])
        while todo:
            node = todo.popleft()
            node.config = config
            todo.extend(node.iter_child_nodes())
        return self

    def __eq__(self, other):
        return type(self) is type(other) and \
               tuple(self.iter_fields()) == tuple(other.iter_fields())

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join('%s=%r' % (arg, getattr(self, arg, None)) for
                      arg in self.fields)
        )


class Stmt(Node):
    """Base node for all statements."""
    abstract = True


class Helper(Node):
    """Nodes that exist in a specific context only."""
    abstract = True


class Template(Node):
    """Node that represents a template.  This must be the outermost node that
    is passed to the compiler.
    """
    fields = ('body',)


class Output(Stmt):
    """A node that holds multiple expressions which are then printed out.
    This is used both for the `print` statement and the regular template data.
    """
    fields = ('nodes',)


class Extends(Stmt):
    """Represents an extends statement."""
    fields = ('template',)


class For(Stmt):
    """The for loop.  `target` is the target for the iteration (usually a
    :class:`Name` or :class:`Tuple`), `iter` the iterable.  `body` is a list
    of nodes that are used as loop-body, and `else_` a list of nodes for the
    `else` block.  If no else node exists it has to be an empty list.
    """
    fields = ('target', 'iter', 'body', 'else_')


class If(Stmt):
    """If `test` is true, `body` is rendered, else `else_`."""
    fields = ('test', 'body', 'else_')


class FilterBlock(Stmt):
    """Node for filter sections."""
    fields = ('body', 'name', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')


class Block(Stmt):
    """A node that represents a block."""
    fields = ('name', 'body')


class Include(Stmt):
    """A node that represents the include tag."""
    fields = ('template', 'ignore_missing')


class Import(Stmt):
    """A node that represents the import tag."""
    fields = ('template', 'target')


class FromImport(Stmt):
    """A node that represents the from import tag.  The items have to be
    FromImportItems.
    """
    fields = ('template', 'items')


class FromImportItem(Helper):
    fields = ('target', 'name')


class ExprStmt(Stmt):
    """A statement that evaluates an expression and discards the result."""
    fields = ('node',)


class Assign(Stmt):
    """Assigns an expression to a target."""
    fields = ('target', 'node')


class CallOut(Stmt):
    """A node that freezes the context down and into a dict, calls a
    callback and then restores the context which might be modified by the
    callback.
    """
    fields = ('callback',)


class Expr(Node):
    """Baseclass for all expressions."""
    abstract = True

    def can_assign(self):
        """Check if it's possible to assign something to this node."""
        return False


class Function(Expr):
    """Defines a function expression."""
    fields = ('name', 'args', 'defaults', 'body')


class BinExpr(Expr):
    """Baseclass for all binary expressions."""
    fields = ('left', 'right')
    operator = None
    abstract = True


class UnaryExpr(Expr):
    """Baseclass for all unary expressions."""
    fields = ('node',)
    operator = None
    abstract = True


class Name(Expr):
    """Looks up a name or stores a value in a name.
    The `ctx` of the node can be one of the following values:

    -   `store`: store a value in the name
    -   `load`: load that name
    -   `param`: like `store` but if the name was defined as function parameter.
    """
    fields = ('name', 'ctx')

    def can_assign(self):
        if self.ctx == 'load':
            return False
        return self.name not in ('true', 'false', 'none',
                                 'True', 'False', 'None')


class Literal(Expr):
    """Baseclass for literals."""
    abstract = True


class Const(Literal):
    """All constant values.  The parser will return this node for simple
    constants such as ``42`` or ``"foo"`` but it can be used to store more
    complex values such as lists too.  Only constants with a safe
    representation (objects where ``eval(repr(x)) == x`` is true).
    """
    fields = ('value',)


class TemplateData(Literal):
    """A constant template string."""
    fields = ('data',)


class Tuple(Literal):
    """For loop unpacking and some other things like multiple arguments
    for subscripts.  Like for :class:`Name` `ctx` specifies if the tuple
    is used for loading the names or storing.
    """
    fields = ('items', 'ctx')

    def can_assign(self):
        if self.ctx not in ('param', 'store'):
            return False
        for item in self.items:
            if not item.can_assign():
                return False
        return True


class List(Literal):
    """Any list literal such as ``[1, 2, 3]``"""
    fields = ('items',)


class Dict(Literal):
    """Any dict literal such as ``{1: 2, 3: 4}``.  The items must be a list of
    :class:`Pair` nodes.
    """
    fields = ('items',)


class Pair(Helper):
    """A key, value pair for dicts."""
    fields = ('key', 'value')


class Keyword(Helper):
    """A key, value pair for keyword arguments where key is a string."""
    fields = ('key', 'value')


class CondExpr(Expr):
    """A conditional expression (inline if expression).  (``{{
    foo if bar else baz }}``)
    """
    fields = ('test', 'true', 'false')


class Filter(Expr):
    """This node applies a filter on an expression.  `name` is the name of
    the filter, the rest of the fields are the same as for :class:`Call`.

    If the `node` of a filter is `None` the contents of the last buffer are
    filtered.  Buffers are created by macros and filter blocks.
    """
    fields = ('node', 'name', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')


class Test(Expr):
    """Applies a test on an expression.  `name` is the name of the test, the
    rest of the fields are the same as for :class:`Call`.
    """
    fields = ('node', 'name', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')


class Call(Expr):
    """Calls an expression.  `args` is a list of arguments, `kwargs` a list
    of keyword arguments (list of :class:`Keyword` nodes), and `dyn_args`
    and `dyn_kwargs` has to be either `None` or a node that is used as
    node for dynamic positional (``*args``) or keyword (``**kwargs``)
    arguments.
    """
    fields = ('node', 'args', 'kwargs', 'dyn_args', 'dyn_kwargs')


class Getitem(Expr):
    """Get an attribute or item from an expression and prefer the item."""
    fields = ('node', 'arg')

    def can_assign(self):
        return False


class Getattr(Expr):
    """Get an attribute or item from an expression that is a ascii-only
    bytestring and prefer the attribute.
    """
    fields = ('node', 'attr')

    def can_assign(self):
        return False


class Slice(Expr):
    """Represents a slice object.  This must only be used as argument for
    :class:`Getitem`.
    """
    fields = ('start', 'stop', 'step')


class Concat(Expr):
    """Concatenates the list of expressions provided after converting them to
    unicode.
    """
    fields = ('nodes',)


class Compare(Expr):
    """Compares an expression with some other expressions.  `ops` must be a
    list of :class:`Operand`\s.
    """
    fields = ('expr', 'ops')


class Operand(Helper):
    """Holds an operator and an expression."""
    fields = ('op', 'expr')

if __debug__:
    Operand.__doc__ += '\nThe following operators are available: ' + \
        ', '.join(sorted('``%s``' % x for x in set(binop_to_func) |
                  set(uaop_to_func) | set(cmpop_to_func)))


class Mul(BinExpr):
    """Multiplies the left with the right node."""
    operator = '*'


class Div(BinExpr):
    """Divides the left by the right node."""
    operator = '/'


class FloorDiv(BinExpr):
    """Divides the left by the right node and truncates conver the
    result into an integer by truncating.
    """
    operator = '//'


class Add(BinExpr):
    """Add the left to the right node."""
    operator = '+'


class Sub(BinExpr):
    """Substract the right from the left node."""
    operator = '-'


class Mod(BinExpr):
    """Left modulo right."""
    operator = '%'


class Pow(BinExpr):
    """Left to the power of right."""
    operator = '**'


class And(BinExpr):
    """Short circuited AND."""
    operator = 'and'


class Or(BinExpr):
    """Short circuited OR."""
    operator = 'or'


class Not(UnaryExpr):
    """Negate the expression."""
    operator = 'not'


class Neg(UnaryExpr):
    """Make the expression negative."""
    operator = '-'


class Pos(UnaryExpr):
    """Make the expression positive (noop for most expressions)"""
    operator = '+'


class MarkSafe(Expr):
    """Mark the wrapped expression as safe (wrap it as `Markup`)."""
    fields = ('expr',)


class MarkSafeIfAutoescape(Expr):
    """Mark the wrapped expression as safe (wrap it as `Markup`) but
    only if autoescaping is active.
    """
    fields = ('expr',)


class Continue(Stmt):
    """Continue a loop."""


class Break(Stmt):
    """Break a loop."""


class Scope(Stmt):
    """An artificial scope."""
    fields = ('body',)


# make sure nobody creates custom nodes
def _failing_new(*args, **kwargs):
    raise TypeError('can\'t create custom node types')
NodeType.__new__ = staticmethod(_failing_new); del _failing_new

########NEW FILE########
__FILENAME__ = nodeutils
# -*- coding: utf-8 -*-
"""
    templatetk.nodeutils
    ~~~~~~~~~~~~~~~~~~~~

    Various utilities useful for node processing.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from .nodes import Node


class NodeVisitor(object):
    """Walks the abstract syntax tree and call visitor functions for every
    node found.  The visitor functions may return values which will be
    forwarded by the `visit` method.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.
    """

    def __init__(self):
        self._visitor_cache = {}

    def get_visitor(self, node):
        """Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        visitor = self._visitor_cache.get(node.__class__)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, None)
            self._visitor_cache[node.__class__] = visitor
        return visitor

    def visit(self, node, *args, **kwargs):
        """Visit a node."""
        f = self.get_visitor(node)
        if f is not None:
            return f(node, *args, **kwargs)
        return self.generic_visit(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        for node in node.iter_child_nodes():
            self.visit(node, *args, **kwargs)


class NodeTransformer(NodeVisitor):
    """Walks the abstract syntax tree and allows modifications of nodes.

    The `NodeTransformer` will walk the AST and use the return value of the
    visitor functions to replace or remove the old node.  If the return
    value of the visitor function is `None` the node will be removed
    from the previous location otherwise it's replaced with the return
    value.  The return value may be the original node in which case no
    replacement takes place.
    """

    def generic_visit(self, node, *args, **kwargs):
        for field, old_value in node.iter_fields():
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, Node):
                        value = self.visit(value, *args, **kwargs)
                        if value is None:
                            continue
                        elif not isinstance(value, Node):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, Node):
                new_node = self.visit(old_value, *args, **kwargs)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node

    def visit_list(self, node, *args, **kwargs):
        """As transformers may return lists in some places this method
        can be used to enforce a list as return value.
        """
        rv = self.visit(node, *args, **kwargs)
        if not isinstance(rv, list):
            rv = [rv]
        return rv

########NEW FILE########
__FILENAME__ = runtime
# -*- coding: utf-8 -*-
"""
    templatetk.runtime
    ~~~~~~~~~~~~~~~~~~

    Runtime helpers.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from .exceptions import BlockNotFoundException, BlockLevelOverflowException, \
     TemplateNotFound, TemplatesNotFound


class RuntimeInfo(object):
    """While the template engine is interpreting the ASTS or compiled
    code it has to keep a bunch of information around.  This does not
    keep the actual variables around, that is intepreter/compiled code
    dependent.
    """

    def __init__(self, config, template_name=None):
        self.config = config
        self.template_name = template_name
        self.autoescape = config.get_autoescape_default(template_name)
        self.volatile = False
        self.filters = config.get_filters()
        self.block_executers = {}
        self.template_cache = {}
        self.exports = {}

    def get_template(self, template_name):
        """Gets a template from cache or if it's not there, it will newly
        load it and cache it.
        """
        template_name = self.config.join_path(self.template_name,
                                              template_name)

        if template_name in self.template_cache:
            return self.template_cache[template_name]
        rv = self.config.get_template(template_name)
        self.template_cache[template_name] = rv
        return rv

    def select_template(self, template_names):
        for name in template_names:
            try:
                return self.get_template(name)
            except TemplateNotFound:
                pass
        raise TemplatesNotFound(template_names)

    def get_or_select_template(self, template_name_or_list):
        if isinstance(template_name_or_list, basestring):
            return self.get_template(template_name_or_list)
        else:
            return self.select_template(template_name_or_list)

    def get_filter(self, name):
        try:
            return self.filters[name]
        except KeyError:
            raise RuntimeError('Filter %r not found' % name)

    def call_block_filter(self, name, buffered_block, args, kwargs):
        data = self.concat_template_data(buffered_block)
        return self.call_filter(name, data, args, kwargs)

    def concat_template_data(self, buffered_data):
        data = u''.join(buffered_data)
        if self.autoescape:
            data = self.config.markup_type(data)
        return data

    def call_filter(self, name, obj, args, kwargs):
        func = self.get_filter(name)
        return func(obj, *args, **kwargs)

    def call_test(self, name, obj, args, kwargs):
        func = self.get_test(name)
        return func(obj, *args, **kwargs)

    def call(self, obj, args, kwargs):
        return obj(*args, **kwargs)

    def register_block(self, name, executor):
        self.block_executers.setdefault(name, []).append(executor)

    def evaluate_block(self, name, level=1, vars=None):
        try:
            func = self.block_executers[name][level - 1]
        except KeyError:
            raise BlockNotFoundException(name)
        except IndexError:
            raise BlockLevelOverflowException(name, level)
        return func(self, vars)

    def make_info(self, template, template_name, behavior='extends'):
        assert behavior in ('extends', 'include', 'import')
        rv = self.__class__(self.config, template_name)
        rv.template_cache = self.template_cache
        if behavior == 'extends':
            rv.block_executers.update(self.block_executers)
        return rv

    def make_module(self, gen):
        """Make this info and evaluated template generator into a module."""
        body = list(gen)
        return self.config.make_module(self.template_name, self.exports,
                                       body)

    def make_callout_context(self, lookup):
        return self.config.make_callout_context(self, lookup)

    def finalize(self, value):
        return self.config.finalize(value, self.autoescape)


class Function(object):
    """Wraps a function.  Currently pretty much a noop but can be used
    to further customize the calling behavior.
    """

    def __init__(self, config, name, callable, arguments, defaults):
        self.__name__ = name
        self._config = config
        self._callable = callable
        self._arguments = arguments
        self._arg_count = len(arguments)
        self._defaults = defaults

    def __call__(self, *args, **kwargs):
        pos_args = list(args[:self._arg_count])
        off = len(args)
        if off != self._arg_count:
            for idx, name in enumerate(self._arguments[len(pos_args):]):
                try:
                    value = kwargs.pop(name)
                except KeyError:
                    try:
                        value = self._defaults[idx - self._arg_count + off]
                    except IndexError:
                        value = self._config.undefined_variable(name)
                pos_args.append(value)
        return self._callable(*pos_args)


class LoopContextBase(object):
    """Base implementation for a loop context.  Solves most problems a
    loop context has to solve and implements the base interface that is
    required by the system.
    """

    def __init__(self, iterable, parent=None):
        self._iterator = iter(iterable)
        self.index0 = -1

        # try to get the length of the iterable early.  This must be done
        # here because there are some broken iterators around where there
        # __len__ is the number of iterations left (i'm looking at your
        # listreverseiterator!).
        try:
            self._length = len(iterable)
        except (TypeError, AttributeError):
            self._length = None

    @property
    def length(self):
        if self._length is None:
            # if was not possible to get the length of the iterator when
            # the loop context was created (ie: iterating over a generator)
            # we have to convert the iterable into a sequence and use the
            # length of that.
            iterable = tuple(self._iterator)
            self._iterator = iter(iterable)
            self._length = len(iterable) + self.index0 + 1
        return self._length

    def __iter__(self):
        return LoopContextIterator(self)


class LoopContext(LoopContextBase):
    """A loop context for dynamic iteration.  This does not have to be used
    but it's a good base implementation.
    """

    def __init__(self, iterable, parent=None):
        LoopContextBase.__init__(self, iterable, parent)
        self.parent = parent

    def cycle(self, *args):
        """Cycles among the arguments with the current loop index."""
        if not args:
            raise TypeError('no items for cycling given')
        return args[self.index0 % len(args)]

    first = property(lambda x: x.index0 == 0)
    last = property(lambda x: x.index0 + 1 == x.length)
    index = property(lambda x: x.index0 + 1)
    revindex = property(lambda x: x.length - x.index0)
    revindex0 = property(lambda x: x.length - x.index)

    def __len__(self):
        return self.length

    def __repr__(self):
        return '<%s %r/%r>' % (
            self.__class__.__name__,
            self.index,
            self.length
        )


class LoopContextIterator(object):
    """The iterator for a loop context."""
    __slots__ = ('context',)

    def __init__(self, context):
        self.context = context

    def __iter__(self):
        return self

    def next(self):
        ctx = self.context
        ctx.index0 += 1
        return ctx._iterator.next(), ctx

########NEW FILE########
__FILENAME__ = astutil
# -*- coding: utf-8 -*-
"""
    templatetk.testsuite.astutil
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests AST utilities.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

import ast

from . import TemplateTestCase
from .. import astutil


class SExprTestCase(TemplateTestCase):

    def test_to_sexpr(self):
        node = ast.parse('''def test():
            foo = 1
            bar = 2
            meh = [1, 2, bar, foo]
            return [-x for x in meh]\
        ''')

        expected = ('Module',
        ('body',
         [('FunctionDef',
           ('name', (':', 'test')),
           ('args',
            ('arguments',
             ('args', []),
             ('vararg', (':', None)),
             ('kwarg', (':', None)),
             ('defaults', []))),
           ('body',
            [('Assign',
              ('targets', [('Name', ('id', (':', 'foo')), ('ctx', 'Store'))]),
              ('value', ('Num', ('n', (':', 1))))),
             ('Assign',
              ('targets', [('Name', ('id', (':', 'bar')), ('ctx', 'Store'))]),
              ('value', ('Num', ('n', (':', 2))))),
             ('Assign',
              ('targets', [('Name', ('id', (':', 'meh')), ('ctx', 'Store'))]),
              ('value',
               ('List',
                ('elts',
                 [('Num', ('n', (':', 1))),
                  ('Num', ('n', (':', 2))),
                  ('Name', ('id', (':', 'bar')), ('ctx', 'Load')),
                  ('Name', ('id', (':', 'foo')), ('ctx', 'Load'))]),
                ('ctx', 'Load')))),
             ('Return',
              ('value',
               ('ListComp',
                ('elt',
                 ('UnaryOp',
                  ('op', 'USub'),
                  ('operand',
                   ('Name', ('id', (':', 'x')), ('ctx', 'Load'))))),
                ('generators',
                 [('comprehension',
                   ('target',
                    ('Name', ('id', (':', 'x')), ('ctx', 'Store'))),
                   ('iter',
                    ('Name', ('id', (':', 'meh')), ('ctx', 'Load'))),
                   ('ifs', []))]))))]),
           ('decorator_list', []))]))

        self.assert_equal(astutil.to_sexpr(node), expected)

    def test_from_sexpr(self):
        node = ast.parse('''def test():
            foo = 1
            bar = 2
            meh = [1, 2, bar, foo]

            class Foo(object):
                pass

            return [-x for x in meh], Foo()\
        ''')

        node2 = astutil.from_sexpr(astutil.to_sexpr(node))
        expected = astutil.to_sexpr(node)
        got = astutil.to_sexpr(node2)
        self.assert_equal(expected, got)
        astutil.fix_missing_locations(node2)

        ns = {}
        exec compile(node2, '', 'exec') in ns
        something, obj = ns['test']()
        self.assert_equal(something, [-1, -2, -2, -1])
        self.assert_equal(obj.__class__.__name__, 'Foo')


def suite():
    import unittest

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SExprTestCase))
    return suite

########NEW FILE########
__FILENAME__ = bcinterp
# -*- coding: utf-8 -*-
"""
    templatetk.testsuite.bcinterp
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the bytecode "interpreter".

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from . import _basicexec

from .. import nodes
from ..bcinterp import run_bytecode, RuntimeState


class BCInterpTestCase(_basicexec.BasicExecTestCase):

    def get_exec_namespace(self, node, ctx, config, info=None):
        rtstate = RuntimeState(ctx, config, 'dummy', info)
        return run_bytecode(node, '<dummy>'), rtstate

    def _execute(self, node, ctx, config, info):
        ns, rtstate = self.get_exec_namespace(node, ctx, config, info)
        ns['setup'](rtstate)
        return ns['root'](rtstate)

    def _evaluate(self, node, ctx, config, info):
        n = nodes
        node = n.Template(
            [n.Assign(n.Name('__result__', 'store'), node)], lineno=1
        ).set_config(config)
        ns, rtstate = self.get_exec_namespace(node, ctx, config)
        ns['setup'](rtstate)
        for event in ns['root'](rtstate):
            pass
        return rtstate.info.exports['__result__']


def suite():
    return _basicexec.make_suite(BCInterpTestCase, __name__)

########NEW FILE########
__FILENAME__ = interpreter
# -*- coding: utf-8 -*-
"""
    templatetk.testsuite.interpreter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the AST interpreter.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

from . import _basicexec

from ..interpreter import Interpreter, BasicInterpreterState


class InterpreterTestCase(_basicexec.BasicExecTestCase):
    interpreter_state_class = BasicInterpreterState

    def make_interpreter_state(self, config, ctx, info=None):
        return self.interpreter_state_class(config, info=info, vars=ctx)

    def make_interpreter(self, config):
        return Interpreter(config)

    def make_interpreter_and_state(self, config, ctx, info):
        if ctx is None:
            ctx = {}
        state = self.make_interpreter_state(config, ctx, info)
        intrptr = self.make_interpreter(config)
        return intrptr, state

    def _evaluate(self, node, ctx, config, info):
        intrptr, state = self.make_interpreter_and_state(config, ctx, info)
        return intrptr.evaluate(node, state)

    def _execute(self, node, ctx, config, info):
        intrptr, state = self.make_interpreter_and_state(config, ctx, info)
        return intrptr.execute(node, state)

    def iter_template_blocks(self, template, config):
        intrptr = Interpreter(config)
        return intrptr.iter_blocks(template.node,
                                   self.interpreter_state_class)


def suite():
    return _basicexec.make_suite(InterpreterTestCase, __name__)

########NEW FILE########
__FILENAME__ = _basicexec
# -*- coding: utf-8 -*-
"""
    templatetk.testsuite._basicexec
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Some basic baseclasses for execution that are used by the interpreter
    and the compiled-code runner.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from . import TemplateTestCase
from .. import nodes
from ..config import Config
from ..exceptions import TemplateNotFound


class _SimpleTemplate(object):

    def __init__(self, template_name, node, test_case):
        self.template_name = template_name
        self.node = node
        self.test_case = test_case


class _CallOutContext(object):

    def __init__(self, lookup):
        self.lookup = lookup
        self.local_changes = {}

    def __getitem__(self, key):
        if key in self.local_changes:
            return self.local_changes[key]
        return self.lookup[key]

    def __setitem__(self, key, value):
        self.local_changes[key] = value


class BasicExecTestCase(TemplateTestCase):

    def assert_result_matches(self, node, ctx, expected, config=None):
        if config is None:
            config = Config()
        node.set_config(config)
        rv = u''.join(self.execute(node, ctx, config))
        self.assert_equal(rv, expected)

    def assert_template_fails(self, node, ctx, exception, config=None):
        if config is None:
            config = Config()
        node.set_config(config)
        with self.assert_raises(exception):
            for event in self.execute(node, ctx, config):
                pass

    def make_inheritance_config(self, templates):
        test_case = self

        class Module(object):

            def __init__(self, name, exports, contents):
                self.__dict__.update(exports)
                self.__name__ = name
                self.body = contents

        class CustomConfig(Config):
            def get_template(self, name):
                try:
                    return _SimpleTemplate(name, templates[name], test_case)
                except KeyError:
                    raise TemplateNotFound(name)
            def yield_from_template(self, template, info, vars=None):
                return template.test_case.execute(template.node, ctx=vars,
                                                  config=self, info=info)
            def iter_template_blocks(self, template):
                return test_case.iter_template_blocks(template, self)
            def make_module(self, template_name, exports, body):
                return Module(template_name, exports, ''.join(body))
            def make_callout_context(self, info, lookup):
                return _CallOutContext(lookup)
            def callout_context_changes(self, callout_context):
                return callout_context.local_changes.iteritems()
        return CustomConfig()

    def find_ctx_config(self, ctx, config, node):
        if config is None:
            config = node.config
            if config is None:
                config = Config()
        node.set_config(config)
        if ctx is None:
            ctx = {}
        return ctx, config

    def execute(self, node, ctx=None, config=None, info=None):
        ctx, config = self.find_ctx_config(ctx, config, node)
        return self._execute(node, ctx, config, info)

    def evaluate(self, node, ctx=None, config=None, info=None):
        ctx, config = self.find_ctx_config(ctx, config, node)
        return self._evaluate(node, ctx, config, info)

    def _execute(self, node, ctx, config, info):
        raise NotImplementedError()

    def _evaluate(self, node, ctx, config, info):
        raise NotImplementedError()

    def iter_template_blocks(self, template, config):
        raise NotImplementedError()


class IfConditionTestCase(object):

    def test_basic_if(self):
        n = nodes

        template = n.Template([
            n.If(n.Name('value', 'load'), [n.Output([n.Const('body')])],
                 [n.Output([n.Const('else')])])])

        self.assert_result_matches(template, dict(value=True), 'body')
        self.assert_result_matches(template, dict(value=False), 'else')

    def test_if_scoping(self):
        n = nodes

        template = n.Template([
            n.Output([n.Name('a', 'load'), n.Const(';')]),
            n.If(n.Const(True), [n.Assign(n.Name('a', 'store'), n.Const(23)),
                                 n.Output([n.Name('a', 'load')])], []),
            n.Output([n.Const(';'), n.Name('a', 'load')])])

        self.assert_result_matches(template, dict(a=42), '42;23;42')


class FilterBlockTestCase(object):

    def test_basic_filtering(self):
        n = nodes
        config = Config()
        config.get_filters = lambda: {'uppercase': lambda x: x.upper()}

        template = n.Template([
            n.FilterBlock([
                n.Output([n.Const('Hello '), n.Name('name', 'load')])
            ], 'uppercase', [], [], None, None)
        ])

        self.assert_result_matches(template, dict(name='World'), 'HELLO WORLD',
                                   config=config)

    def test_filter_scoping(self):
        n = nodes
        config = Config()
        config.get_filters = lambda: {'uppercase': lambda x: x.upper()}

        template = n.Template([
            n.FilterBlock([
                n.Output([n.Const('Hello '), n.Name('x', 'load'),
                          n.Const(';')]),
                n.Assign(n.Name('x', 'store'), n.Const(23)),
                n.Output([n.Name('x', 'load')])
            ], 'uppercase', [], [], None, None),
            n.Output([n.Const(';'), n.Name('x', 'load')])
        ])

        self.assert_result_matches(template, dict(x=42), 'HELLO 42;23;42',
                                   config=config)


class ForLoopTestCase(object):

    def test_basic_loop(self):
        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load')])
            ], None)
        ])

        self.assert_result_matches(template, dict(
            iterable=[1, 2, 3, 4]
        ), '1234')

    def test_loop_with_counter(self):
        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(':'),
                          n.Getattr(n.Name('loop', 'load'),
                                    n.Const('index0')),
                          n.Const(';')])
            ], None)
        ])

        self.assert_result_matches(template, dict(
            iterable=[1, 2, 3, 4]
        ), '1:0;2:1;3:2;4:3;')

    def test_loop_with_custom_context(self):
        from ..runtime import LoopContextBase

        class CustomLoopContext(LoopContextBase):
            def __call__(self):
                return unicode(self.index0)

        class MyConfig(Config):
            def wrap_loop(self, iterator, parent=None):
                return CustomLoopContext(iterator)

        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(':'),
                          n.Call(n.Name('loop', 'load'), [], [], None, None),
                          n.Const(';')])
            ], None)
        ])

        self.assert_result_matches(template, dict(
            iterable=[1, 2, 3, 4]
        ), '1:0;2:1;3:2;4:3;', config=MyConfig())

    def test_loop_with_parent_access(self):
        config = Config()

        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Name('iterable', 'load'), [
                n.Output([n.Getattr(n.Name('loop', 'load'), n.Const('parent'))])
            ], None)
        ])

        self.assert_result_matches(template, dict(
            loop=42,
            iterable=[1]
        ), '42', config=config)

    def test_loop_else_body(self):
        config = Config()

        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Name('iterable', 'load'), [
                n.Output([n.Getattr(n.Name('loop', 'load'), n.Const('parent'))])
            ], [n.Output([n.Const('ELSE')])])
        ])

        self.assert_result_matches(template, dict(
            iterable=[]
        ), 'ELSE', config=config)

    def test_silent_loop_unpacking(self):
        config = Config()
        config.allow_noniter_unpacking = True
        config.undefined_variable = lambda x: '<%s>' % x

        n = nodes
        template = n.Template([
            n.For(n.Tuple([n.Name('item', 'store'), n.Name('whoop', 'store')],
                          'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(';')])
            ], None)
        ])

        self.assert_result_matches(template, dict(
            iterable=[1, 2, 3, 4]
        ), '<item>;<item>;<item>;<item>;', config=config)

    def test_loud_loop_unpacking(self):
        config = Config()
        config.allow_noniter_unpacking = False

        n = nodes
        template = n.Template([
            n.For(n.Tuple([n.Name('item', 'store'), n.Name('whoop', 'store')],
                          'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(';')])
            ], None)
        ])

        self.assert_template_fails(template, dict(iterable=[1, 2, 3]),
                                   exception=TypeError, config=config)

    def test_strict_loop_unpacking_behavior(self):
        config = Config()
        config.strict_tuple_unpacking = True

        n = nodes
        template = n.Template([
            n.For(n.Tuple([n.Name('item', 'store'), n.Name('whoop', 'store')],
                          'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(';')])
            ], None)
        ])

        self.assert_template_fails(template, dict(iterable=[(1, 2, 3)]),
                                   exception=ValueError, config=config)

    def test_lenient_loop_unpacking_behavior(self):
        config = Config()
        config.strict_tuple_unpacking = False
        config.undefined_variable = lambda x: '<%s>' % x

        n = nodes
        template = n.Template([
            n.For(n.Tuple([n.Name('item', 'store'), n.Name('whoop', 'store')],
                          'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(';'),
                          n.Name('whoop', 'load')])
            ], None)
        ])

        self.assert_result_matches(template, dict(iterable=[(1, 2, 3)]),
            '1;2', config=config)

        template = n.Template([
            n.For(n.Tuple([n.Name('item', 'store'), n.Name('whoop', 'store')],
                          'store'), n.Name('iterable', 'load'), [
                n.Output([n.Name('item', 'load'), n.Const(';'),
                          n.Name('whoop', 'load')])
            ], None)
        ])

        self.assert_result_matches(template, dict(iterable=[(1,)]),
            '1;<whoop>', config=config)

    def test_loop_controls(self):
        n = nodes
        template = n.Template([
            n.For(n.Name('item', 'store'), n.Const([1, 2, 3]), [
                n.Output([n.Name('item', 'load'), n.Const(';')]),
                n.If(n.Compare(n.Getattr(n.Name('loop', 'load'),
                                         n.Const('index0')),
                               [n.Operand('eq', n.Const(1))]), [n.Break()], [])
            ], [])])

        self.assert_result_matches(template, dict(), '1;2;')

        template = n.Template([
            n.For(n.Name('item', 'store'), n.Const([1, 2, 3]), [
                n.If(n.Compare(n.Getattr(n.Name('loop', 'load'),
                                         n.Const('index0')),
                               [n.Operand('eq', n.Const(1))]), [n.Continue()], []),
                n.Output([n.Name('item', 'load'), n.Const(';')])
            ], [])])

        self.assert_result_matches(template, dict(), '1;3;')

    def test_artifical_scope(self):
        n = nodes

        template = n.Template([
            n.Assign(n.Name('testing', 'store'), n.Const(42)),
            n.Output([n.Name('testing', 'load'), n.Const(';')]),
            n.Scope([
                n.Assign(n.Name('testing', 'store'), n.Const(23)),
                n.Output([n.Name('testing', 'load'), n.Const(';')])
            ]),
            n.Output([n.Name('testing', 'load'), n.Const(';')])
        ])

        self.assert_result_matches(template, dict(), '42;23;42;')

    def test_exprstmt(self):
        n = nodes
        called = []

        def testfunc():
            called.append(23)

        template = n.Template([
            n.ExprStmt(n.Call(n.Name('test', 'load'), [], [], None, None)),
            n.Output([n.Const('42')])
        ])

        self.assert_result_matches(template, dict(test=testfunc), '42')
        self.assert_equal(called, [23])


class ExpressionTestCase(object):

    def assert_expression_equals(self, node, expected, ctx=None, config=None):
        rv = self.evaluate(node, ctx, config)
        self.assert_equal(rv, expected)

    def test_basic_binary_arithmetic(self):
        n = nodes
        test = self.assert_expression_equals

        test(n.Add(n.Const(1), n.Const(1)), 2)
        test(n.Sub(n.Const(42), n.Const(19)), 23)
        test(n.Sub(n.Const(42), n.Const(19)), 23)
        test(n.Mul(n.Const(2), n.Name('var', 'load')), 6, ctx=dict(var=3))
        test(n.Mul(n.Const('test'), n.Const(3)), 'testtesttest')
        test(n.Div(n.Const(42), n.Const(2)), 21.0)
        test(n.Div(n.Const(42), n.Const(4)), 10.5)
        test(n.FloorDiv(n.Const(42), n.Const(4)), 10)
        test(n.Mod(n.Const(42), n.Const(4)), 2)
        test(n.Pow(n.Const(2), n.Const(4)), 16)

    def test_basic_binary_logicals(self):
        n = nodes
        test = self.assert_expression_equals
        not_called_buffer = []

        def simplecall(func):
            return n.Call(n.Name(func.__name__, 'load'), [], [], None, None)

        def not_called():
            not_called_buffer.append(42)

        test(n.And(n.Const(42), n.Const(23)), 23)
        test(n.And(n.Const(0), n.Const(23)), False)
        test(n.Or(n.Const(42), n.Const(23)), 42)
        test(n.Or(n.Const(0), n.Const(23)), 23)
        test(n.And(n.Const(0), simplecall(not_called)), False,
             ctx=dict(not_called=not_called))
        test(n.Or(n.Const(42), simplecall(not_called)), 42,
             ctx=dict(not_called=not_called))
        self.assert_equal(not_called_buffer, [])

    def test_unary(self):
        n = nodes
        test = self.assert_expression_equals

        test(n.Pos(n.Const(-42)), -42)
        test(n.Neg(n.Const(-42)), 42)
        test(n.Neg(n.Const(42)), -42)
        test(n.Not(n.Const(0)), True)
        test(n.Not(n.Const(42)), False)

    def test_general_expressions(self):
        n = nodes
        test = self.assert_expression_equals

        weird_getattr_config = Config()
        weird_getattr_config.getattr = lambda obj, attr: (obj, attr, 'attr')
        weird_getattr_config.getitem = lambda obj, item: (obj, item, 'item')

        test(n.Const(42), 42)
        test(n.Const("test"), "test")
        test(n.Getattr(n.Const('something'),
                       n.Const('the_attribute')),
             ('something', 'the_attribute', 'attr'),
             config=weird_getattr_config)
        test(n.Getitem(n.Const('something'),
                       n.Const('the_attribute')),
             ('something', 'the_attribute', 'item'),
             config=weird_getattr_config)

    def test_compare_expressions(self):
        n = nodes
        test = self.assert_expression_equals

        test(n.Compare(n.Const(1), [
            n.Operand('lt', n.Const(2)),
            n.Operand('lt', n.Const(3))
        ]), True)

        test(n.Compare(n.Const(1), [
            n.Operand('lt', n.Const(32)),
            n.Operand('lt', n.Const(3))
        ]), False)

        test(n.Compare(n.Const(42), [
            n.Operand('gt', n.Const(32)),
            n.Operand('lt', n.Const(100))
        ]), True)

        test(n.Compare(n.Const('test'), [
            n.Operand('in', n.Const('testing'))
        ]), True)

        test(n.Compare(n.Const('testing'), [
            n.Operand('notin', n.Const('test'))
        ]), True)

    def test_template_literal(self):
        n = nodes
        cfg = Config()

        rv = self.evaluate(n.TemplateData('Hello World!'), config=cfg)
        self.assert_equal(type(rv), cfg.markup_type)
        self.assert_equal(unicode(rv), 'Hello World!')

    def test_complex_literals(self):
        n = nodes
        test = self.assert_expression_equals

        test(n.Tuple([n.Const(1), n.Name('test', 'load')], 'load'), (1, 2),
             ctx=dict(test=2))
        test(n.List([n.Const(1), n.Name('test', 'load')]), [1, 2],
             ctx=dict(test=2))
        test(n.Dict([n.Pair(n.Const('foo'), n.Const('bar')),
                     n.Pair(n.Const('baz'), n.Const('blah'))]),
             dict(foo='bar', baz='blah'))

    def test_condexpr(self):
        n = nodes
        test = self.assert_expression_equals
        not_called_buffer = []

        def simplecall(func):
            return n.Call(n.Name(func.__name__, 'load'), [], [], None, None)

        def not_called():
            not_called_buffer.append(42)

        test(n.CondExpr(n.Const(1), n.Const(42), simplecall(not_called)), 42,
             ctx=dict(not_called=not_called))
        test(n.CondExpr(n.Const(0), simplecall(not_called), n.Const(23)), 23,
             ctx=dict(not_called=not_called))

        self.assert_equal(not_called_buffer, [])

    def test_call(self):
        n = nodes
        test = self.assert_expression_equals

        def foo(a, b, c, d):
            return a, b, c, d

        test(n.Call(n.Name('foo', 'load'), [n.Const(1)],
             [n.Keyword('c', n.Const(3))], n.Const((2,)),
             n.Const({'d': 4})), (1, 2, 3, 4), ctx=dict(foo=foo))

        test(n.Call(n.Name('foo', 'load'), [n.Const(1), n.Const(2)],
             [n.Keyword('c', n.Const(3))], None,
             n.Const({'d': 4})), (1, 2, 3, 4), ctx=dict(foo=foo))

        test(n.Call(n.Name('foo', 'load'), [n.Const(1)],
             [n.Keyword('c', n.Const(3))], None,
             n.Const({'b': 2, 'd': 4})), (1, 2, 3, 4), ctx=dict(foo=foo))

        self.assert_template_fails(n.Template(
            n.Output([n.Call(n.Name('foo', 'load'), [n.Const(1)],
            [n.Keyword('c', n.Const(3))], None,
            n.Const({'c': 2, 'b': 23, 'd': 4}))])), ctx=dict(foo=foo),
            exception=TypeError)

    def test_filters(self):
        n = nodes
        test = self.assert_expression_equals

        config = Config()
        config.get_filters = lambda: {'uppercase': lambda x: x.upper()}

        test(n.Filter(n.Const('hello'), 'uppercase', [], [], None, None),
             'HELLO', config=config)

    def test_slicing(self):
        n = nodes
        test = self.assert_expression_equals

        test(n.Getitem(n.Const('Hello'), n.Slice(n.Const(1), n.Const(None),
                                                 n.Const(2))), 'el')
        test(n.Getitem(n.Const('Hello'), n.Slice(n.Const(None), n.Const(-1),
                                                 n.Const(1))), 'Hell')
        test(n.Getitem(n.Const('Hello'), n.Slice(n.Const(None), n.Const(-1),
                                                 n.Const(None))), 'Hell')

    def test_mark_safe(self):
        n = nodes
        cfg = Config()

        rv = self.evaluate(n.MarkSafe(n.Const('<Hello World!>')), config=cfg)
        self.assert_equal(type(rv), cfg.markup_type)
        self.assert_equal(unicode(rv), '<Hello World!>')

    def test_mark_safe_if_autoescape(self):
        n = nodes

        cfg = Config()
        cfg.get_autoescape_default = lambda x: False
        rv = self.evaluate(n.MarkSafeIfAutoescape(n.Const('<Hello World!>')), config=cfg)
        self.assert_not_equal(type(rv), unicode)
        self.assert_equal(unicode(rv), '<Hello World!>')

        cfg = Config()
        cfg.get_autoescape_default = lambda x: True
        rv = self.evaluate(n.MarkSafeIfAutoescape(n.Const('<Hello World!>')),
                           config=cfg)
        self.assert_equal(type(rv), cfg.markup_type)
        self.assert_equal(unicode(rv), '<Hello World!>')


class InheritanceTestCase(object):

    def test_blocks(self):
        n = nodes

        index_template = n.Template([
            n.Assign(n.Name('foo', 'store'), n.Const(42)),
            n.Assign(n.Name('bar', 'store'), n.Const(23)),
            n.Block('the_block', [
                n.Output([n.Const('block contents')])
            ])
        ])

        self.assert_result_matches(index_template, dict(), 'block contents')

    def test_basic_inheritance(self):
        n = nodes

        index_template = n.Template([
            n.Extends(n.Const('layout.html')),
            n.Block('the_block', [
                n.Output([n.Const('block contents')])
            ])
        ])
        layout_template = n.Template([
            n.Output([n.Const('before block;')]),
            n.Block('the_block', [n.Output([n.Const('default contents')])]),
            n.Output([n.Const(';after block')])
        ])

        config = self.make_inheritance_config({
            'index.html':       index_template,
            'layout.html':      layout_template
        })

        self.assert_result_matches(index_template, dict(),
            'before block;block contents;after block', config=config)


class IncludeTestCase(object):

    def test_basic_include(self):
        n = nodes

        index_template = n.Template([
            n.Output([n.Const('1\n')]),
            n.Include(n.Const('include.html'), False),
            n.Output([n.Const('\n2')])
        ])
        include_template = n.Template([
            n.Output([n.Const('A')]),
        ])

        config = self.make_inheritance_config({
            'index.html':       index_template,
            'include.html':     include_template
        })

        self.assert_result_matches(index_template, dict(),
            '1\nA\n2', config=config)

    def test_basic_include_ignore_missing(self):
        n = nodes

        index_template = n.Template([
            n.Output([n.Const('1\n')]),
            n.Include(n.Const('includemissing.html'), True),
            n.Output([n.Const('\n2')])
        ])
        include_template = n.Template([
            n.Output([n.Const('A')]),
        ])

        config = self.make_inheritance_config({
            'index.html':       index_template
        })

        self.assert_result_matches(index_template, dict(),
            '1\n\n2', config=config)


class ImportTestCase(object):

    def test_basic_imports(self):
        n = nodes

        index_template = n.Template([
            n.Import(n.Const('import.html'), n.Name('foo', 'store')),
            n.Output([n.Getattr(n.Name('foo', 'load'), n.Const('bar'))])
        ])
        import_template = n.Template([
            n.Assign(n.Name('bar', 'store'), n.Const(42))
        ])

        config = self.make_inheritance_config({
            'index.html':       index_template,
            'import.html':      import_template
        })

        self.assert_result_matches(index_template, dict(),
            '42', config=config)

    def test_from_imports(self):
        n = nodes

        index_template = n.Template([
            n.FromImport(n.Const('import.html'), [
                n.FromImportItem(n.Name('foo', 'store'), n.Const('foo')),
                n.FromImportItem(n.Name('x', 'store'), n.Const('bar'))]),
            n.Output([n.Name('foo', 'load'), n.Const('|'), n.Name('x', 'load')])
        ])
        import_template = n.Template([
            n.Assign(n.Name('foo', 'store'), n.Const(42)),
            n.Assign(n.Name('bar', 'store'), n.Const(23))
        ])

        config = self.make_inheritance_config({
            'index.html':       index_template,
            'import.html':      import_template
        })

        self.assert_result_matches(index_template, dict(),
            '42|23', config=config)


class FunctionTestCase(object):

    def test_basic_function(self):
        n = nodes

        t = n.Template([
            n.Assign(n.Name('test', 'store'), n.Function(n.Const('test'),
                [n.Name('x', 'param')], [], [
                n.Output([n.Const('x: '), n.Name('x', 'load')])
            ])),
            n.Output([n.Call(n.Name('test', 'load'), [n.Const(42)],
                             [], None, None)])
        ])

        self.assert_result_matches(t, dict(), 'x: 42')

    def test_as_expression(self):
        n = nodes

        t = n.Template([
            n.Output([n.Call(n.Function(n.Const('test'),
                [n.Name('x', 'param')], [], [
                n.Output([n.Const('x: '), n.Name('x', 'load')])
            ]), [n.Const(23)], [], None, None)])
        ])

        self.assert_result_matches(t, dict(), 'x: 23')

    def test_scoping(self):
        n = nodes

        t = n.Template([
            n.Assign(n.Name('y', 'store'), n.Const(42)),
            n.Output([n.Call(n.Function(n.Const('test'),
                [n.Name('x', 'param')], [], [
                n.Output([n.Name('y', 'load'), n.Const(' '),
                          n.Name('x', 'load')])
            ]), [n.Const(23)], [], None, None)])
        ])

        self.assert_result_matches(t, dict(), '42 23')

    def test_problematic_scoping(self):
        n = nodes

        t = n.Template([
            n.Assign(n.Name('test', 'store'), n.Function(n.Const('test'),
                [n.Name('x', 'param')], [], [
                n.Output([n.Name('y', 'load'), n.Const(' '),
                          n.Name('x', 'load')])
            ])),
            n.Output([n.Call(n.Name('test', 'load'), [n.Const(2)],
                             [], None, None), n.Const(' ')]),
            n.Assign(n.Name('y', 'store'), n.Const(3)),
            n.Output([n.Call(n.Name('test', 'load'), [n.Const(2)],
                             [], None, None)])
        ])

        self.assert_result_matches(t, dict(y=1), '1 2 3 2')


class CallOutTestCase(object):

    def test_basic_callout(self):
        def callback(context):
            old_var = context['var']
            context['var'] = 42
            yield unicode(old_var)

        n = nodes

        t = n.Template([
            n.Assign(n.Name('var', 'store'), n.Const(23)),
            n.CallOut(n.Name('callback', 'load')),
            n.Output([n.Const('|')]),
            n.Output([n.Name('var', 'load')])
        ])

        config = self.make_inheritance_config({})
        self.assert_result_matches(t, dict(callback=callback),
                                   '23|42', config=config)


def make_suite(test_class, module):
    import unittest

    def mixin(class_):
        return type(class_.__name__, (test_class, class_), {
            '__module__': module
        })

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(mixin(IfConditionTestCase)))
    suite.addTest(unittest.makeSuite(mixin(ForLoopTestCase)))
    suite.addTest(unittest.makeSuite(mixin(FilterBlockTestCase)))
    suite.addTest(unittest.makeSuite(mixin(ExpressionTestCase)))
    suite.addTest(unittest.makeSuite(mixin(InheritanceTestCase)))
    suite.addTest(unittest.makeSuite(mixin(IncludeTestCase)))
    suite.addTest(unittest.makeSuite(mixin(ImportTestCase)))
    suite.addTest(unittest.makeSuite(mixin(FunctionTestCase)))
    suite.addTest(unittest.makeSuite(mixin(CallOutTestCase)))
    return suite

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    templatetk.utils
    ~~~~~~~~~~~~~~~~

    Various utilities

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from cgi import escape
try:
    import simplejson as json
except ImportError:
    import json


class Markup(unicode):

    @classmethod
    def escape(cls, value):
        return cls(escape(value))

    def __html__(self):
        return self


class _Missing(object):
    __slots__ = ()

    def __repr__(self):
        return 'missing'

    def __reduce__(self):
        return 'missing'


missing = _Missing()
del _Missing

########NEW FILE########
__FILENAME__ = django_template_debug
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    django_template_debug
    ~~~~~~~~~~~~~~~~~~~~~

    Hackery with django templates without having to have a whole django
    project.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from django.conf import settings
try:
    settings.configure(TEMPLATE_DEBUG=True)
except RuntimeError:
    # reload hackery
    pass

from django import template


def parse_template(source):
    return template.Template(source)


def render_template(source, *args, **kwargs):
    ctx = template.Context(dict(*args, **kwargs))
    return parse_template(source).render(ctx)

########NEW FILE########
