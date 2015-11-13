__FILENAME__ = checker
# -*- test-case-name: pyflakes -*-
# (c) 2005-2010 Divmod, Inc.
# See LICENSE file for details

import __builtin__
import os.path
import _ast

from pyflakes import messages


# utility function to iterate over an AST node's children, adapted
# from Python 2.6's standard ast module
try:
    import ast
    iter_child_nodes = ast.iter_child_nodes
except (ImportError, AttributeError):
    def iter_child_nodes(node, astcls=_ast.AST):
        """
        Yield all direct child nodes of *node*, that is, all fields that are nodes
        and all items of fields that are lists of nodes.
        """
        for name in node._fields:
            field = getattr(node, name, None)
            if isinstance(field, astcls):
                yield field
            elif isinstance(field, list):
                for item in field:
                    yield item


class Binding(object):
    """
    Represents the binding of a value to a name.

    The checker uses this to keep track of which names have been bound and
    which names have not. See L{Assignment} for a special type of binding that
    is checked with stricter rules.

    @ivar used: pair of (L{Scope}, line-number) indicating the scope and
                line number that this binding was last used
    """

    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.used = False


    def __str__(self):
        return self.name


    def __repr__(self):
        return '<%s object %r from line %r at 0x%x>' % (self.__class__.__name__,
                                                        self.name,
                                                        self.source.lineno,
                                                        id(self))



class UnBinding(Binding):
    '''Created by the 'del' operator.'''



class Importation(Binding):
    """
    A binding created by an import statement.

    @ivar fullName: The complete name given to the import statement,
        possibly including multiple dotted components.
    @type fullName: C{str}
    """
    def __init__(self, name, source):
        self.fullName = name
        name = name.split('.')[0]
        super(Importation, self).__init__(name, source)



class Argument(Binding):
    """
    Represents binding a name as an argument.
    """



class Assignment(Binding):
    """
    Represents binding a name with an explicit assignment.

    The checker will raise warnings for any Assignment that isn't used. Also,
    the checker does not consider assignments in tuple/list unpacking to be
    Assignments, rather it treats them as simple Bindings.
    """



class FunctionDefinition(Binding):
    _property_decorator = False



class ExportBinding(Binding):
    """
    A binding created by an C{__all__} assignment.  If the names in the list
    can be determined statically, they will be treated as names for export and
    additional checking applied to them.

    The only C{__all__} assignment that can be recognized is one which takes
    the value of a literal list containing literal strings.  For example::

        __all__ = ["foo", "bar"]

    Names which are imported and not otherwise used but appear in the value of
    C{__all__} will not have an unused import warning reported for them.
    """
    def names(self):
        """
        Return a list of the names referenced by this binding.
        """
        names = []
        if isinstance(self.source, _ast.List):
            for node in self.source.elts:
                if isinstance(node, _ast.Str):
                    names.append(node.s)
        return names



class Scope(dict):
    importStarred = False       # set to True when import * is found
    usesLocals = False


    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), dict.__repr__(self))


    def __init__(self):
        super(Scope, self).__init__()



class ClassScope(Scope):
    pass



class FunctionScope(Scope):
    """
    I represent a name scope for a function.

    @ivar globals: Names declared 'global' in this function.
    """
    def __init__(self):
        super(FunctionScope, self).__init__()
        self.globals = {}



class ModuleScope(Scope):
    pass


# Globally defined names which are not attributes of the __builtin__ module.
_MAGIC_GLOBALS = ['__file__', '__builtins__']



class Checker(object):
    """
    I check the cleanliness and sanity of Python code.

    @ivar _deferredFunctions: Tracking list used by L{deferFunction}.  Elements
        of the list are two-tuples.  The first element is the callable passed
        to L{deferFunction}.  The second element is a copy of the scope stack
        at the time L{deferFunction} was called.

    @ivar _deferredAssignments: Similar to C{_deferredFunctions}, but for
        callables which are deferred assignment checks.
    """

    nodeDepth = 0
    traceTree = False

    def __init__(self, tree, filename=None):
        if filename is None:
            filename = '(none)'
        self._deferredFunctions = []
        self._deferredAssignments = []
        self.dead_scopes = []
        self.messages = []
        self.filename = filename
        self.scopeStack = [ModuleScope()]
        self.futuresAllowed = True
        self.root = tree
        self.handleChildren(tree)
        self._runDeferred(self._deferredFunctions)
        # Set _deferredFunctions to None so that deferFunction will fail
        # noisily if called after we've run through the deferred functions.
        self._deferredFunctions = None
        self._runDeferred(self._deferredAssignments)
        # Set _deferredAssignments to None so that deferAssignment will fail
        # noisly if called after we've run through the deferred assignments.
        self._deferredAssignments = None
        del self.scopeStack[1:]
        self.popScope()
        self.check_dead_scopes()


    def deferFunction(self, callable):
        '''
        Schedule a function handler to be called just before completion.

        This is used for handling function bodies, which must be deferred
        because code later in the file might modify the global scope. When
        `callable` is called, the scope at the time this is called will be
        restored, however it will contain any new bindings added to it.
        '''
        self._deferredFunctions.append((callable, self.scopeStack[:]))


    def deferAssignment(self, callable):
        """
        Schedule an assignment handler to be called just after deferred
        function handlers.
        """
        self._deferredAssignments.append((callable, self.scopeStack[:]))


    def _runDeferred(self, deferred):
        """
        Run the callables in C{deferred} using their associated scope stack.
        """
        for handler, scope in deferred:
            self.scopeStack = scope
            handler()


    def scope(self):
        return self.scopeStack[-1]
    scope = property(scope)

    def popScope(self):
        self.dead_scopes.append(self.scopeStack.pop())


    def check_dead_scopes(self):
        """
        Look at scopes which have been fully examined and report names in them
        which were imported but unused.
        """
        for scope in self.dead_scopes:
            export = isinstance(scope.get('__all__'), ExportBinding)
            if export:
                all = scope['__all__'].names()
                if os.path.split(self.filename)[1] != '__init__.py':
                    # Look for possible mistakes in the export list
                    undefined = set(all) - set(scope)
                    for name in undefined:
                        self.report(
                            messages.UndefinedExport,
                            scope['__all__'].source,
                            name)
            else:
                all = []

            # Look for imported names that aren't used.
            for importation in scope.itervalues():
                if isinstance(importation, Importation):
                    if not importation.used and importation.name not in all:
                        self.report(
                            messages.UnusedImport,
                            importation.source,
                            importation.name)


    def pushFunctionScope(self):
        self.scopeStack.append(FunctionScope())

    def pushClassScope(self):
        self.scopeStack.append(ClassScope())

    def report(self, messageClass, *args, **kwargs):
        self.messages.append(messageClass(self.filename, *args, **kwargs))

    def lowestCommonAncestor(self, lnode, rnode, stop=None):
        if not stop:
            stop = self.root
        if lnode is stop:
            return lnode
        if rnode is stop:
            return rnode

        if lnode is rnode:
            return lnode
        if (lnode.level > rnode.level):
            return self.lowestCommonAncestor(lnode.parent, rnode, stop)
        if (rnode.level > lnode.level):
            return self.lowestCommonAncestor(lnode, rnode.parent, stop)
        if lnode.parent is rnode.parent:
            return lnode.parent
        else:
            return self.lowestCommonAncestor(lnode.parent, rnode.parent, stop)

    def descendantOf(self, node, ancestors, stop=None):
        for a in ancestors: 
            try:
                p = self.lowestCommonAncestor(node, a, stop)
                if not p is stop:
                    return True
            except AttributeError:
                # Skip some bogus objects like <_ast.Pass>
                pass
        return False

    def onFork(self, parent, lnode, rnode, items):
            return int(self.descendantOf(lnode, items, parent)) + \
                int(self.descendantOf(rnode, items, parent))

    def differentForks(self, lnode, rnode):
        "True, if lnode and rnode are located on different forks of IF/TRY"
        ancestor = self.lowestCommonAncestor(lnode, rnode)
        if isinstance(ancestor, _ast.If):
            for fork in (ancestor.body, ancestor.orelse):
                if self.onFork(ancestor, lnode, rnode, fork) == 1:
                    return True
        if isinstance(ancestor, _ast.TryExcept):
            for fork in (ancestor.body, ancestor.handlers, ancestor.orelse):
                if self.onFork(ancestor, lnode, rnode, fork) == 1:
                    return True
        return False

    def handleChildren(self, tree):
        for node in iter_child_nodes(tree):
            self.handleNode(node, tree)

    def isDocstring(self, node):
        """
        Determine if the given node is a docstring, as long as it is at the
        correct place in the node tree.
        """
        return isinstance(node, _ast.Str) or \
               (isinstance(node, _ast.Expr) and
                isinstance(node.value, _ast.Str))

    def handleNode(self, node, parent):
        node.parent = parent
        if self.traceTree:
            print '  ' * self.nodeDepth + node.__class__.__name__
        self.nodeDepth += 1
        if self.futuresAllowed and not \
               (isinstance(node, _ast.ImportFrom) or self.isDocstring(node)):
            self.futuresAllowed = False
        nodeType = node.__class__.__name__.upper()
        node.level = self.nodeDepth
        try:
            handler = getattr(self, nodeType)
            handler(node)
        finally:
            self.nodeDepth -= 1
        if self.traceTree:
            print '  ' * self.nodeDepth + 'end ' + node.__class__.__name__

    def ignore(self, node):
        pass

    # "stmt" type nodes
    RETURN = DELETE = PRINT = WHILE = IF = WITH = RAISE = TRYEXCEPT = \
        TRYFINALLY = ASSERT = EXEC = EXPR = handleChildren

    CONTINUE = BREAK = PASS = ignore

    # "expr" type nodes
    BOOLOP = BINOP = UNARYOP = IFEXP = DICT = SET = YIELD = COMPARE = \
    CALL = REPR = ATTRIBUTE = SUBSCRIPT = LIST = TUPLE = handleChildren

    NUM = STR = ELLIPSIS = ignore

    # "slice" type nodes
    SLICE = EXTSLICE = INDEX = handleChildren

    # expression contexts are node instances too, though being constants
    LOAD = STORE = DEL = AUGLOAD = AUGSTORE = PARAM = ignore

    # same for operators
    AND = OR = ADD = SUB = MULT = DIV = MOD = POW = LSHIFT = RSHIFT = \
    BITOR = BITXOR = BITAND = FLOORDIV = INVERT = NOT = UADD = USUB = \
    EQ = NOTEQ = LT = LTE = GT = GTE = IS = ISNOT = IN = NOTIN = ignore

    # additional node types
    COMPREHENSION = EXCEPTHANDLER = KEYWORD = handleChildren

    def addBinding(self, loc, value, reportRedef=True):
        '''Called when a binding is altered.

        - `loc` is the location (an object with lineno and optionally
          col_offset attributes) of the statement responsible for the change
        - `value` is the optional new value, a Binding instance, associated
          with the binding; if None, the binding is deleted if it exists.
        - if `reportRedef` is True (default), rebinding while unused will be
          reported.
        '''
        if (isinstance(self.scope.get(value.name), FunctionDefinition)
                    and isinstance(value, FunctionDefinition)):
            if not value._property_decorator:
                if not self.differentForks(loc, self.scope[value.name].source):
                    self.report(messages.RedefinedFunction,
                            loc, value.name, self.scope[value.name].source)

        if not isinstance(self.scope, ClassScope):
            for scope in self.scopeStack[::-1]:
                existing = scope.get(value.name)
                if (isinstance(existing, Importation)
                        and not existing.used
                        and (not isinstance(value, Importation) or value.fullName == existing.fullName)
                        and reportRedef):

                    if not self.differentForks(loc, existing.source):
                        self.report(messages.RedefinedWhileUnused,
                                loc, value.name, existing.source)

        if isinstance(value, UnBinding):
            try:
                del self.scope[value.name]
            except KeyError:
                self.report(messages.UndefinedName, loc, value.name)
        else:
            self.scope[value.name] = value

    def GLOBAL(self, node):
        """
        Keep track of globals declarations.
        """
        if isinstance(self.scope, FunctionScope):
            self.scope.globals.update(dict.fromkeys(node.names))

    def LISTCOMP(self, node):
        # handle generators before element
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.elt, node)

    GENERATOREXP = SETCOMP = LISTCOMP

    # dictionary comprehensions; introduced in Python 2.7
    def DICTCOMP(self, node):
        for gen in node.generators:
            self.handleNode(gen, node)
        self.handleNode(node.key, node)
        self.handleNode(node.value, node)

    def FOR(self, node):
        """
        Process bindings for loop variables.
        """
        vars = []
        def collectLoopVars(n):
            if isinstance(n, _ast.Name):
                vars.append(n.id)
            elif isinstance(n, _ast.expr_context):
                return
            else:
                for c in iter_child_nodes(n):
                    collectLoopVars(c)

        collectLoopVars(node.target)
        for varn in vars:
            if (isinstance(self.scope.get(varn), Importation)
                    # unused ones will get an unused import warning
                    and self.scope[varn].used):
                self.report(messages.ImportShadowedByLoopVar,
                            node, varn, self.scope[varn].source)

        self.handleChildren(node)

    def NAME(self, node):
        """
        Handle occurrence of Name (which can be a load/store/delete access.)
        """
        if node.id == 'locals' and isinstance(node.parent, _ast.Call):
            # we are doing locals() call in current scope
            self.scope.usesLocals = True

        # Locate the name in locals / function / globals scopes.
        if isinstance(node.ctx, (_ast.Load, _ast.AugLoad)):
            # try local scope
            importStarred = self.scope.importStarred
            try:
                self.scope[node.id].used = (self.scope, node)
            except KeyError:
                pass
            else:
                return

            # try enclosing function scopes

            for scope in self.scopeStack[-2:0:-1]:
                importStarred = importStarred or scope.importStarred
                if not isinstance(scope, FunctionScope):
                    continue
                try:
                    scope[node.id].used = (self.scope, node)
                except KeyError:
                    pass
                else:
                    return

            # try global scope

            importStarred = importStarred or self.scopeStack[0].importStarred
            try:
                self.scopeStack[0][node.id].used = (self.scope, node)
            except KeyError:
                if ((not hasattr(__builtin__, node.id))
                        and node.id not in _MAGIC_GLOBALS
                        and not importStarred):
                    if (os.path.basename(self.filename) == '__init__.py' and
                        node.id == '__path__'):
                        # the special name __path__ is valid only in packages
                        pass
                    else:
                        self.report(messages.UndefinedName, node, node.id)
        elif isinstance(node.ctx, (_ast.Store, _ast.AugStore)):
            # if the name hasn't already been defined in the current scope
            if isinstance(self.scope, FunctionScope) and node.id not in self.scope:
                # for each function or module scope above us
                for scope in self.scopeStack[:-1]:
                    if not isinstance(scope, (FunctionScope, ModuleScope)):
                        continue
                    # if the name was defined in that scope, and the name has
                    # been accessed already in the current scope, and hasn't
                    # been declared global
                    if (node.id in scope
                            and scope[node.id].used
                            and scope[node.id].used[0] is self.scope
                            and node.id not in self.scope.globals):
                        # then it's probably a mistake
                        self.report(messages.UndefinedLocal,
                                    scope[node.id].used[1],
                                    node.id,
                                    scope[node.id].source)
                        break

            if isinstance(node.parent,
                          (_ast.For, _ast.comprehension, _ast.Tuple, _ast.List)):
                binding = Binding(node.id, node)
            elif (node.id == '__all__' and
                  isinstance(self.scope, ModuleScope)):
                binding = ExportBinding(node.id, node.parent.value)
            else:
                binding = Assignment(node.id, node)
            if node.id in self.scope:
                binding.used = self.scope[node.id].used
            self.addBinding(node, binding)
        elif isinstance(node.ctx, _ast.Del):
            if isinstance(self.scope, FunctionScope) and \
                   node.id in self.scope.globals:
                del self.scope.globals[node.id]
            else:
                self.addBinding(node, UnBinding(node.id, node))
        else:
            # must be a Param context -- this only happens for names in function
            # arguments, but these aren't dispatched through here
            raise RuntimeError(
                "Got impossible expression context: %r" % (node.ctx,))


    def FUNCTIONDEF(self, node):
        # the decorators attribute is called decorator_list as of Python 2.6
        if hasattr(node, 'decorators'):
            for deco in node.decorators:
                self.handleNode(deco, node)
        else:
            for deco in node.decorator_list:
                self.handleNode(deco, node)

        # Check for property decorator
        func_def = FunctionDefinition(node.name, node)
        
        if hasattr(node, 'decorators'):
            for decorator in node.decorators:
                if getattr(decorator, 'attr', None) in ('setter', 'deleter'):
                    func_def._property_decorator = True
        else:
            for decorator in node.decorator_list:
                if getattr(decorator, 'attr', None) in ('setter', 'deleter'):
                    func_def._property_decorator = True

        self.addBinding(node, func_def)
        self.LAMBDA(node)

    def LAMBDA(self, node):
        for default in node.args.defaults:
            self.handleNode(default, node)

        def runFunction():
            args = []

            def addArgs(arglist):
                for arg in arglist:
                    if isinstance(arg, _ast.Tuple):
                        addArgs(arg.elts)
                    else:
                        if arg.id in args:
                            self.report(messages.DuplicateArgument,
                                        node, arg.id)
                        args.append(arg.id)

            self.pushFunctionScope()
            addArgs(node.args.args)
            # vararg/kwarg identifiers are not Name nodes
            if node.args.vararg:
                args.append(node.args.vararg)
            if node.args.kwarg:
                args.append(node.args.kwarg)
            for name in args:
                self.addBinding(node, Argument(name, node), reportRedef=False)
            if isinstance(node.body, list):
                # case for FunctionDefs
                for stmt in node.body:
                    self.handleNode(stmt, node)
            else:
                # case for Lambdas
                self.handleNode(node.body, node)
            def checkUnusedAssignments():
                """
                Check to see if any assignments have not been used.
                """
                for name, binding in self.scope.iteritems():
                    if (not binding.used and not name in self.scope.globals
                        and not self.scope.usesLocals
                        and isinstance(binding, Assignment)):
                        self.report(messages.UnusedVariable,
                                    binding.source, name)
            self.deferAssignment(checkUnusedAssignments)
            self.popScope()

        self.deferFunction(runFunction)


    def CLASSDEF(self, node):
        """
        Check names used in a class definition, including its decorators, base
        classes, and the body of its definition.  Additionally, add its name to
        the current scope.
        """
        # decorator_list is present as of Python 2.6
        for deco in getattr(node, 'decorator_list', []):
            self.handleNode(deco, node)
        for baseNode in node.bases:
            self.handleNode(baseNode, node)
        self.pushClassScope()
        for stmt in node.body:
            self.handleNode(stmt, node)
        self.popScope()
        self.addBinding(node, Binding(node.name, node))

    def ASSIGN(self, node):
        self.handleNode(node.value, node)
        for target in node.targets:
            self.handleNode(target, node)

    def AUGASSIGN(self, node):
        # AugAssign is awkward: must set the context explicitly and visit twice,
        # once with AugLoad context, once with AugStore context
        node.target.ctx = _ast.AugLoad()
        self.handleNode(node.target, node)
        self.handleNode(node.value, node)
        node.target.ctx = _ast.AugStore()
        self.handleNode(node.target, node)

    def IMPORT(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            importation = Importation(name, node)
            self.addBinding(node, importation)

    def IMPORTFROM(self, node):
        if node.module == '__future__':
            if not self.futuresAllowed:
                self.report(messages.LateFutureImport, node,
                            [n.name for n in node.names])
        else:
            self.futuresAllowed = False

        for alias in node.names:
            if alias.name == '*':
                self.scope.importStarred = True
                self.report(messages.ImportStarUsed, node, node.module)
                continue
            name = alias.asname or alias.name
            importation = Importation(name, node)
            if node.module == '__future__':
                importation.used = (self.scope, node)
            self.addBinding(node, importation)

########NEW FILE########
__FILENAME__ = messages
# (c) 2005 Divmod, Inc.  See LICENSE file for details

class Message(object):
    message = ''
    message_args = ()
    def __init__(self, filename, loc, use_column=True):
        self.filename = filename
        self.lineno = loc.lineno
        self.col = getattr(loc, 'col_offset', None) if use_column else None

    def __str__(self):
        return '%s:%s: %s' % (self.filename, self.lineno, self.message % self.message_args)


class UnusedImport(Message):
    message = '%r imported but unused'
    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc, use_column=False)
        self.message_args = (name,)


class RedefinedWhileUnused(Message):
    message = 'redefinition of unused %r from line %r'
    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class ImportShadowedByLoopVar(Message):
    message = 'import %r from line %r shadowed by loop variable'
    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class ImportStarUsed(Message):
    message = "'from %s import *' used; unable to detect undefined names"
    def __init__(self, filename, loc, modname):
        Message.__init__(self, filename, loc)
        self.message_args = (modname,)


class UndefinedName(Message):
    message = 'undefined name %r'
    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)



class UndefinedExport(Message):
    message = 'undefined name %r in __all__'
    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)



class UndefinedLocal(Message):
    message = "local variable %r (defined in enclosing scope on line %r) referenced before assignment"
    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class DuplicateArgument(Message):
    message = 'duplicate argument %r in function definition'
    def __init__(self, filename, loc, name):
        Message.__init__(self, filename, loc)
        self.message_args = (name,)


class RedefinedFunction(Message):
    message = 'redefinition of function %r from line %r'
    def __init__(self, filename, loc, name, orig_loc):
        Message.__init__(self, filename, loc)
        self.message_args = (name, orig_loc.lineno)


class LateFutureImport(Message):
    message = 'future import(s) %r after other statements'
    def __init__(self, filename, loc, names):
        Message.__init__(self, filename, loc)
        self.message_args = (names,)


class UnusedVariable(Message):
    """
    Indicates that a variable has been explicity assigned to but not actually
    used.
    """

    message = 'local variable %r is assigned to but never used'
    def __init__(self, filename, loc, names):
        Message.__init__(self, filename, loc)
        self.message_args = (names,)

########NEW FILE########
__FILENAME__ = pyflakes

"""
Implementation of the command-line I{pyflakes} tool.
"""

import sys
import os
import _ast

checker = __import__('pyflakes.checker').checker

def check(codeString, filename):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError, value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            print >> sys.stderr, "%s: problem decoding source" % (filename, )
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            print >> sys.stderr, '%s:%d: %s' % (filename, lineno, msg)
            print >> sys.stderr, line

            if offset is not None:
                print >> sys.stderr, " " * offset, "^"

        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            print warning
        return len(w.messages)


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        return check(file(filename, 'U').read() + '\n', filename)
    except IOError, msg:
        print >> sys.stderr, "%s: %s" % (filename, msg.args[1])
        return 1


def main():
    warnings = 0
    args = sys.argv[1:]
    if args:
        for arg in args:
            if os.path.isdir(arg):
                for dirpath, dirnames, filenames in os.walk(arg):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            warnings += checkPath(os.path.join(dirpath, filename))
            else:
                warnings += checkPath(arg)
    else:
        warnings += check(sys.stdin.read(), '<stdin>')

    raise SystemExit(warnings > 0)

########NEW FILE########
__FILENAME__ = harness

import textwrap
import _ast

from twisted.trial import unittest

from pyflakes import checker


class Test(unittest.TestCase):

    def flakes(self, input, *expectedOutputs, **kw):
        ast = compile(textwrap.dedent(input), "<test>", "exec",
                      _ast.PyCF_ONLY_AST)
        w = checker.Checker(ast, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort()
        expectedOutputs.sort()
        self.assert_(outputs == expectedOutputs, '''\
for input:
%s
expected outputs:
%s
but got:
%s''' % (input, repr(expectedOutputs), '\n'.join([str(o) for o in w.messages])))
        return w

########NEW FILE########
__FILENAME__ = test_imports

from sys import version_info

from pyflakes import messages as m
from pyflakes.test import harness

class Test(harness.Test):

    def test_unusedImport(self):
        self.flakes('import fu, bar', m.UnusedImport, m.UnusedImport)
        self.flakes('from baz import fu, bar', m.UnusedImport, m.UnusedImport)

    def test_aliasedImport(self):
        self.flakes('import fu as FU, bar as FU', m.RedefinedWhileUnused, m.UnusedImport)
        self.flakes('from moo import fu as FU, bar as FU', m.RedefinedWhileUnused, m.UnusedImport)

    def test_usedImport(self):
        self.flakes('import fu; print fu')
        self.flakes('from baz import fu; print fu')

    def test_redefinedWhileUnused(self):
        self.flakes('import fu; fu = 3', m.RedefinedWhileUnused)
        self.flakes('import fu; del fu', m.RedefinedWhileUnused)
        self.flakes('import fu; fu, bar = 3', m.RedefinedWhileUnused)
        self.flakes('import fu; [fu, bar] = 3', m.RedefinedWhileUnused)

    def test_redefinedIf(self):
        """
        Test that importing a module twice within an if
        block does raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        i = 2
        if i==1:
            import os
            import os
        os.path''', m.RedefinedWhileUnused)

    def test_redefinedIfElse(self):
        """
        Test that importing a module twice in if
        and else blocks does not raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        i = 2
        if i==1:
            import os
        else:
            import os
        os.path''')

    def test_redefinedTry(self):
        """
        Test that importing a module twice in an try block
        does raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        try:
            import os
            import os
        except:
            pass
        os.path''', m.RedefinedWhileUnused)

    def test_redefinedTryExcept(self):
        """
        Test that importing a module twice in an try
        and except block does not raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        try:
            import os
        except:
            import os
        os.path''')

    def test_redefinedTryNested(self):
        """
        Test that importing a module twice using a nested
        try/except and if blocks does not issue a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        try:
            if True:
                if True:
                    import os
        except:
            import os
        os.path''')

    def test_redefinedByFunction(self):
        self.flakes('''
        import fu
        def fu():
            pass
        ''', m.RedefinedWhileUnused)

    def test_redefinedInNestedFunction(self):
        """
        Test that shadowing a global name with a nested function definition
        generates a warning.
        """
        self.flakes('''
        import fu
        def bar():
            def baz():
                def fu():
                    pass
        ''', m.RedefinedWhileUnused, m.UnusedImport)

    def test_redefinedByClass(self):
        self.flakes('''
        import fu
        class fu:
            pass
        ''', m.RedefinedWhileUnused)


    def test_redefinedBySubclass(self):
        """
        If an imported name is redefined by a class statement which also uses
        that name in the bases list, no warning is emitted.
        """
        self.flakes('''
        from fu import bar
        class bar(bar):
            pass
        ''')


    def test_redefinedInClass(self):
        """
        Test that shadowing a global with a class attribute does not produce a
        warning.
        """
        self.flakes('''
        import fu
        class bar:
            fu = 1
        print fu
        ''')

    def test_usedInFunction(self):
        self.flakes('''
        import fu
        def fun():
            print fu
        ''')

    def test_shadowedByParameter(self):
        self.flakes('''
        import fu
        def fun(fu):
            print fu
        ''', m.UnusedImport)

        self.flakes('''
        import fu
        def fun(fu):
            print fu
        print fu
        ''')

    def test_newAssignment(self):
        self.flakes('fu = None')

    def test_usedInGetattr(self):
        self.flakes('import fu; fu.bar.baz')
        self.flakes('import fu; "bar".fu.baz', m.UnusedImport)

    def test_usedInSlice(self):
        self.flakes('import fu; print fu.bar[1:]')

    def test_usedInIfBody(self):
        self.flakes('''
        import fu
        if True: print fu
        ''')

    def test_usedInIfConditional(self):
        self.flakes('''
        import fu
        if fu: pass
        ''')

    def test_usedInElifConditional(self):
        self.flakes('''
        import fu
        if False: pass
        elif fu: pass
        ''')

    def test_usedInElse(self):
        self.flakes('''
        import fu
        if False: pass
        else: print fu
        ''')

    def test_usedInCall(self):
        self.flakes('import fu; fu.bar()')

    def test_usedInClass(self):
        self.flakes('''
        import fu
        class bar:
            bar = fu
        ''')

    def test_usedInClassBase(self):
        self.flakes('''
        import fu
        class bar(object, fu.baz):
            pass
        ''')

    def test_notUsedInNestedScope(self):
        self.flakes('''
        import fu
        def bleh():
            pass
        print fu
        ''')

    def test_usedInFor(self):
        self.flakes('''
        import fu
        for bar in range(9):
            print fu
        ''')

    def test_usedInForElse(self):
        self.flakes('''
        import fu
        for bar in range(10):
            pass
        else:
            print fu
        ''')

    def test_redefinedByFor(self):
        self.flakes('''
        import fu
        for fu in range(2):
            pass
        ''', m.RedefinedWhileUnused)

    def test_shadowedByFor(self):
        """
        Test that shadowing a global name with a for loop variable generates a
        warning.
        """
        self.flakes('''
        import fu
        fu.bar()
        for fu in ():
            pass
        ''', m.ImportShadowedByLoopVar)

    def test_shadowedByForDeep(self):
        """
        Test that shadowing a global name with a for loop variable nested in a
        tuple unpack generates a warning.
        """
        self.flakes('''
        import fu
        fu.bar()
        for (x, y, z, (a, b, c, (fu,))) in ():
            pass
        ''', m.ImportShadowedByLoopVar)

    def test_usedInReturn(self):
        self.flakes('''
        import fu
        def fun():
            return fu
        ''')

    def test_usedInOperators(self):
        self.flakes('import fu; 3 + fu.bar')
        self.flakes('import fu; 3 % fu.bar')
        self.flakes('import fu; 3 - fu.bar')
        self.flakes('import fu; 3 * fu.bar')
        self.flakes('import fu; 3 ** fu.bar')
        self.flakes('import fu; 3 / fu.bar')
        self.flakes('import fu; 3 // fu.bar')
        self.flakes('import fu; -fu.bar')
        self.flakes('import fu; ~fu.bar')
        self.flakes('import fu; 1 == fu.bar')
        self.flakes('import fu; 1 | fu.bar')
        self.flakes('import fu; 1 & fu.bar')
        self.flakes('import fu; 1 ^ fu.bar')
        self.flakes('import fu; 1 >> fu.bar')
        self.flakes('import fu; 1 << fu.bar')

    def test_usedInAssert(self):
        self.flakes('import fu; assert fu.bar')

    def test_usedInSubscript(self):
        self.flakes('import fu; fu.bar[1]')

    def test_usedInLogic(self):
        self.flakes('import fu; fu and False')
        self.flakes('import fu; fu or False')
        self.flakes('import fu; not fu.bar')

    def test_usedInList(self):
        self.flakes('import fu; [fu]')

    def test_usedInTuple(self):
        self.flakes('import fu; (fu,)')

    def test_usedInTry(self):
        self.flakes('''
        import fu
        try: fu
        except: pass
        ''')

    def test_usedInExcept(self):
        self.flakes('''
        import fu
        try: fu
        except: pass
        ''')

    def test_redefinedByExcept(self):
        self.flakes('''
        import fu
        try: pass
        except Exception, fu: pass
        ''', m.RedefinedWhileUnused)

    def test_usedInRaise(self):
        self.flakes('''
        import fu
        raise fu.bar
        ''')

    def test_usedInYield(self):
        self.flakes('''
        import fu
        def gen():
            yield fu
        ''')

    def test_usedInDict(self):
        self.flakes('import fu; {fu:None}')
        self.flakes('import fu; {1:fu}')

    def test_usedInParameterDefault(self):
        self.flakes('''
        import fu
        def f(bar=fu):
            pass
        ''')

    def test_usedInAttributeAssign(self):
        self.flakes('import fu; fu.bar = 1')

    def test_usedInKeywordArg(self):
        self.flakes('import fu; fu.bar(stuff=fu)')

    def test_usedInAssignment(self):
        self.flakes('import fu; bar=fu')
        self.flakes('import fu; n=0; n+=fu')

    def test_usedInListComp(self):
        self.flakes('import fu; [fu for _ in range(1)]')
        self.flakes('import fu; [1 for _ in range(1) if fu]')

    def test_redefinedByListComp(self):
        self.flakes('import fu; [1 for fu in range(1)]', m.RedefinedWhileUnused)


    def test_usedInTryFinally(self):
        self.flakes('''
        import fu
        try: pass
        finally: fu
        ''')

        self.flakes('''
        import fu
        try: fu
        finally: pass
        ''')

    def test_usedInWhile(self):
        self.flakes('''
        import fu
        while 0:
            fu
        ''')

        self.flakes('''
        import fu
        while fu: pass
        ''')

    def test_usedInGlobal(self):
        self.flakes('''
        import fu
        def f(): global fu
        ''', m.UnusedImport)

    def test_usedInBackquote(self):
        self.flakes('import fu; `fu`')

    def test_usedInExec(self):
        self.flakes('import fu; exec "print 1" in fu.bar')

    def test_usedInLambda(self):
        self.flakes('import fu; lambda: fu')

    def test_shadowedByLambda(self):
        self.flakes('import fu; lambda fu: fu', m.UnusedImport)

    def test_usedInSliceObj(self):
        self.flakes('import fu; "meow"[::fu]')

    def test_unusedInNestedScope(self):
        self.flakes('''
        def bar():
            import fu
        fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_methodsDontUseClassScope(self):
        self.flakes('''
        class bar:
            import fu
            def fun(self):
                fu
        ''', m.UnusedImport, m.UndefinedName)

    def test_nestedFunctionsNestScope(self):
        self.flakes('''
        def a():
            def b():
                fu
            import fu
        ''')

    def test_nestedClassAndFunctionScope(self):
        self.flakes('''
        def a():
            import fu
            class b:
                def c(self):
                    print fu
        ''')

    def test_importStar(self):
        self.flakes('from fu import *', m.ImportStarUsed)


    def test_packageImport(self):
        """
        If a dotted name is imported and used, no warning is reported.
        """
        self.flakes('''
        import fu.bar
        fu.bar
        ''')


    def test_unusedPackageImport(self):
        """
        If a dotted name is imported and not used, an unused import warning is
        reported.
        """
        self.flakes('import fu.bar', m.UnusedImport)


    def test_duplicateSubmoduleImport(self):
        """
        If a submodule of a package is imported twice, an unused import warning
        and a redefined while unused warning are reported.
        """
        self.flakes('''
        import fu.bar, fu.bar
        fu.bar
        ''', m.RedefinedWhileUnused)
        self.flakes('''
        import fu.bar
        import fu.bar
        fu.bar
        ''', m.RedefinedWhileUnused)


    def test_differentSubmoduleImport(self):
        """
        If two different submodules of a package are imported, no duplicate
        import warning is reported for the package.
        """
        self.flakes('''
        import fu.bar, fu.baz
        fu.bar, fu.baz
        ''')
        self.flakes('''
        import fu.bar
        import fu.baz
        fu.bar, fu.baz
        ''')

    def test_assignRHSFirst(self):
        self.flakes('import fu; fu = fu')
        self.flakes('import fu; fu, bar = fu')
        self.flakes('import fu; [fu, bar] = fu')
        self.flakes('import fu; fu += fu')

    def test_tryingMultipleImports(self):
        self.flakes('''
        try:
            import fu
        except ImportError:
            import bar as fu
        ''')
    test_tryingMultipleImports.todo = ''

    def test_nonGlobalDoesNotRedefine(self):
        self.flakes('''
        import fu
        def a():
            fu = 3
            return fu
        fu
        ''')

    def test_functionsRunLater(self):
        self.flakes('''
        def a():
            fu
        import fu
        ''')

    def test_functionNamesAreBoundNow(self):
        self.flakes('''
        import fu
        def fu():
            fu
        fu
        ''', m.RedefinedWhileUnused)

    def test_ignoreNonImportRedefinitions(self):
        self.flakes('a = 1; a = 2')

    def test_importingForImportError(self):
        self.flakes('''
        try:
            import fu
        except ImportError:
            pass
        ''')
    test_importingForImportError.todo = ''

    def test_importedInClass(self):
        '''Imports in class scope can be used through self'''
        self.flakes('''
        class c:
            import i
            def __init__(self):
                self.i
        ''')
    test_importedInClass.todo = 'requires evaluating attribute access'

    def test_futureImport(self):
        '''__future__ is special'''
        self.flakes('from __future__ import division')
        self.flakes('''
        "docstring is allowed before future import"
        from __future__ import division
        ''')

    def test_futureImportFirst(self):
        """
        __future__ imports must come before anything else.
        """
        self.flakes('''
        x = 5
        from __future__ import division
        ''', m.LateFutureImport)
        self.flakes('''
        from foo import bar
        from __future__ import division
        bar
        ''', m.LateFutureImport)



class TestSpecialAll(harness.Test):
    """
    Tests for suppression of unused import warnings by C{__all__}.
    """
    def test_ignoredInFunction(self):
        """
        An C{__all__} definition does not suppress unused import warnings in a
        function scope.
        """
        self.flakes('''
        def foo():
            import bar
            __all__ = ["bar"]
        ''', m.UnusedImport, m.UnusedVariable)


    def test_ignoredInClass(self):
        """
        An C{__all__} definition does not suppress unused import warnings in a
        class scope.
        """
        self.flakes('''
        class foo:
            import bar
            __all__ = ["bar"]
        ''', m.UnusedImport)


    def test_warningSuppressed(self):
        """
        If a name is imported and unused but is named in C{__all__}, no warning
        is reported.
        """
        self.flakes('''
        import foo
        __all__ = ["foo"]
        ''')


    def test_unrecognizable(self):
        """
        If C{__all__} is defined in a way that can't be recognized statically,
        it is ignored.
        """
        self.flakes('''
        import foo
        __all__ = ["f" + "oo"]
        ''', m.UnusedImport)
        self.flakes('''
        import foo
        __all__ = [] + ["foo"]
        ''', m.UnusedImport)


    def test_unboundExported(self):
        """
        If C{__all__} includes a name which is not bound, a warning is emitted.
        """
        self.flakes('''
        __all__ = ["foo"]
        ''', m.UndefinedExport)

        # Skip this in __init__.py though, since the rules there are a little
        # different.
        for filename in ["foo/__init__.py", "__init__.py"]:
            self.flakes('''
            __all__ = ["foo"]
            ''', filename=filename)


    def test_usedInGenExp(self):
        """
        Using a global in a generator expression results in no warnings.
        """
        self.flakes('import fu; (fu for _ in range(1))')
        self.flakes('import fu; (1 for _ in range(1) if fu)')


    def test_redefinedByGenExp(self):
        """
        Re-using a global name as the loop variable for a generator
        expression results in a redefinition warning.
        """
        self.flakes('import fu; (1 for fu in range(1))', m.RedefinedWhileUnused)


    def test_usedAsDecorator(self):
        """
        Using a global name in a decorator statement results in no warnings,
        but using an undefined name in a decorator statement results in an
        undefined name warning.
        """
        self.flakes('''
        from interior import decorate
        @decorate
        def f():
            return "hello"
        ''')

        self.flakes('''
        from interior import decorate
        @decorate('value')
        def f():
            return "hello"
        ''')

        self.flakes('''
        @decorate
        def f():
            return "hello"
        ''', m.UndefinedName)


class Python26Tests(harness.Test):
    """
    Tests for checking of syntax which is valid in PYthon 2.6 and newer.
    """
    if version_info < (2, 6):
        skip = "Python 2.6 required for class decorator tests."


    def test_usedAsClassDecorator(self):
        """
        Using an imported name as a class decorator results in no warnings,
        but using an undefined name as a class decorator results in an
        undefined name warning.
        """
        self.flakes('''
        from interior import decorate
        @decorate
        class foo:
            pass
        ''')

        self.flakes('''
        from interior import decorate
        @decorate("foo")
        class bar:
            pass
        ''')

        self.flakes('''
        @decorate
        class foo:
            pass
        ''', m.UndefinedName)

########NEW FILE########
__FILENAME__ = test_other
# (c) 2005-2010 Divmod, Inc.
# See LICENSE file for details

"""
Tests for various Pyflakes behavior.
"""

from sys import version_info

from pyflakes import messages as m
from pyflakes.test import harness


class Test(harness.Test):

    def test_duplicateArgs(self):
        self.flakes('def fu(bar, bar): pass', m.DuplicateArgument)

    def test_localReferencedBeforeAssignment(self):
        self.flakes('''
        a = 1
        def f():
            a; a=1
        f()
        ''', m.UndefinedName)
    test_localReferencedBeforeAssignment.todo = 'this requires finding all assignments in the function body first'

    def test_redefinedFunction(self):
        """
        Test that shadowing a function definition with another one raises a
        warning.
        """
        self.flakes('''
        def a(): pass
        def a(): pass
        ''', m.RedefinedFunction)

    def test_redefinedClassFunction(self):
        """
        Test that shadowing a function definition in a class suite with another
        one raises a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            def a(): pass
        ''', m.RedefinedFunction)

    def test_redefinedIfElseFunction(self):
        """
        Test that shadowing a function definition twice in an if
        and else block does not raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        if True:
            def a(): pass
        else:
            def a(): pass
        ''')

    def test_redefinedIfFunction(self):
        """
        Test that shadowing a function definition within an if block
        raises a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        if True:
            def a(): pass
            def a(): pass
        ''', m.RedefinedFunction)

    def test_redefinedTryExceptFunction(self):
        """
        Test that shadowing a function definition twice in try
        and except block does not raise a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        try:
            def a(): pass
        except:
            def a(): pass
        ''')

    def test_redefinedTryFunction(self):
        """
        Test that shadowing a function definition within a try block
        raises a warning.

        Issue #13: https://github.com/kevinw/pyflakes/issues/13
        """
        self.flakes('''
        try:
            def a(): pass
            def a(): pass
        except:
            pass
        ''', m.RedefinedFunction)

    def test_functionDecorator(self):
        """
        Test that shadowing a function definition with a decorated version of
        that function does not raise a warning.
        """
        self.flakes('''
        from somewhere import somedecorator

        def a(): pass
        a = somedecorator(a)
        ''')

    def test_classFunctionDecorator(self):
        """
        Test that shadowing a function definition in a class suite with a
        decorated version of that function does not raise a warning.
        """
        self.flakes('''
        class A:
            def a(): pass
            a = classmethod(a)
        ''')

    def test_unaryPlus(self):
        '''Don't die on unary +'''
        self.flakes('+1')


    def test_undefinedBaseClass(self):
        """
        If a name in the base list of a class definition is undefined, a
        warning is emitted.
        """
        self.flakes('''
        class foo(foo):
            pass
        ''', m.UndefinedName)


    def test_classNameUndefinedInClassBody(self):
        """
        If a class name is used in the body of that class's definition and
        the name is not already defined, a warning is emitted.
        """
        self.flakes('''
        class foo:
            foo
        ''', m.UndefinedName)


    def test_classNameDefinedPreviously(self):
        """
        If a class name is used in the body of that class's definition and
        the name was previously defined in some other way, no warning is
        emitted.
        """
        self.flakes('''
        foo = None
        class foo:
            foo
        ''')


    def test_comparison(self):
        """
        If a defined name is used on either side of any of the six comparison
        operators, no warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x < y
        x <= y
        x == y
        x != y
        x >= y
        x > y
        ''')


    def test_identity(self):
        """
        If a deefined name is used on either side of an identity test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x is y
        x is not y
        ''')


    def test_containment(self):
        """
        If a defined name is used on either side of a containment test, no
        warning is emitted.
        """
        self.flakes('''
        x = 10
        y = 20
        x in y
        x not in y
        ''')


    def test_loopControl(self):
        """
        break and continue statements are supported.
        """
        self.flakes('''
        for x in [1, 2]:
            break
        ''')
        self.flakes('''
        for x in [1, 2]:
            continue
        ''')


    def test_ellipsis(self):
        """
        Ellipsis in a slice is supported.
        """
        self.flakes('''
        [1, 2][...]
        ''')


    def test_extendedSlice(self):
        """
        Extended slices are supported.
        """
        self.flakes('''
        x = 3
        [1, 2][x,:]
        ''')



class TestUnusedAssignment(harness.Test):
    """
    Tests for warning about unused assignments.
    """

    def test_unusedVariable(self):
        """
        Warn when a variable in a function is assigned a value that's never
        used.
        """
        self.flakes('''
        def a():
            b = 1
        ''', m.UnusedVariable)


    def test_unusedVariable_asLocals(self):
        """
        Using locals() it is perfectly valid to have unused variables
        """
        self.flakes('''
        def a():
            b = 1
            return locals()
        ''')

    def test_unusedVariable_noLocals(self):
        """
        Using locals() in wrong scope should not matter
        """
        self.flakes('''
        def a():
            locals()
            def a():
                b = 1
                return
        ''', m.UnusedVariable)


    def test_assignToGlobal(self):
        """
        Assigning to a global and then not using that global is perfectly
        acceptable. Do not mistake it for an unused local variable.
        """
        self.flakes('''
        b = 0
        def a():
            global b
            b = 1
        ''')


    def test_assignToMember(self):
        """
        Assigning to a member of another object and then not using that member
        variable is perfectly acceptable. Do not mistake it for an unused
        local variable.
        """
        # XXX: Adding this test didn't generate a failure. Maybe not
        # necessary?
        self.flakes('''
        class b:
            pass
        def a():
            b.foo = 1
        ''')


    def test_assignInForLoop(self):
        """
        Don't warn when a variable in a for loop is assigned to but not used.
        """
        self.flakes('''
        def f():
            for i in range(10):
                pass
        ''')


    def test_assignInListComprehension(self):
        """
        Don't warn when a variable in a list comprehension is assigned to but
        not used.
        """
        self.flakes('''
        def f():
            [None for i in range(10)]
        ''')


    def test_generatorExpression(self):
        """
        Don't warn when a variable in a generator expression is assigned to but not used.
        """
        self.flakes('''
        def f():
            (None for i in range(10))
        ''')


    def test_assignmentInsideLoop(self):
        """
        Don't warn when a variable assignment occurs lexically after its use.
        """
        self.flakes('''
        def f():
            x = None
            for i in range(10):
                if i > 2:
                    return x
                x = i * 2
        ''')


    def test_tupleUnpacking(self):
        """
        Don't warn when a variable included in tuple unpacking is unused. It's
        very common for variables in a tuple unpacking assignment to be unused
        in good Python code, so warning will only create false positives.
        """
        self.flakes('''
        def f():
            (x, y) = 1, 2
        ''')


    def test_listUnpacking(self):
        """
        Don't warn when a variable included in list unpacking is unused.
        """
        self.flakes('''
        def f():
            [x, y] = [1, 2]
        ''')


    def test_closedOver(self):
        """
        Don't warn when the assignment is used in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                return foo
            return bar
        ''')


    def test_doubleClosedOver(self):
        """
        Don't warn when the assignment is used in an inner function, even if
        that inner function itself is in an inner function.
        """
        self.flakes('''
        def barMaker():
            foo = 5
            def bar():
                def baz():
                    return foo
            return bar
        ''')



class Python25Test(harness.Test):
    """
    Tests for checking of syntax only available in Python 2.5 and newer.
    """
    if version_info < (2, 5):
        skip = "Python 2.5 required for if-else and with tests"

    def test_ifexp(self):
        """
        Test C{foo if bar else baz} statements.
        """
        self.flakes("a = 'moo' if True else 'oink'")
        self.flakes("a = foo if True else 'oink'", m.UndefinedName)
        self.flakes("a = 'moo' if True else bar", m.UndefinedName)


    def test_withStatementNoNames(self):
        """
        No warnings are emitted for using inside or after a nameless C{with}
        statement a name defined beforehand.
        """
        self.flakes('''
        from __future__ import with_statement
        bar = None
        with open("foo"):
            bar
        bar
        ''')

    def test_withStatementSingleName(self):
        """
        No warnings are emitted for using a name defined by a C{with} statement
        within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            bar
        bar
        ''')


    def test_withStatementAttributeName(self):
        """
        No warnings are emitted for using an attribute as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo.bar:
            pass
        ''')


    def test_withStatementSubscript(self):
        """
        No warnings are emitted for using a subscript as the target of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[0]:
            pass
        ''')


    def test_withStatementSubscriptUndefined(self):
        """
        An undefined name warning is emitted if the subscript used as the
        target of a C{with} statement is not defined.
        """
        self.flakes('''
        from __future__ import with_statement
        import foo
        with open('foo') as foo[bar]:
            pass
        ''', m.UndefinedName)


    def test_withStatementTupleNames(self):
        """
        No warnings are emitted for using any of the tuple of names defined by
        a C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as (bar, baz):
            bar, baz
        bar, baz
        ''')


    def test_withStatementListNames(self):
        """
        No warnings are emitted for using any of the list of names defined by a
        C{with} statement within the suite or afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as [bar, baz]:
            bar, baz
        bar, baz
        ''')


    def test_withStatementComplicatedTarget(self):
        """
        If the target of a C{with} statement uses any or all of the valid forms
        for that part of the grammar (See
        U{http://docs.python.org/reference/compound_stmts.html#the-with-statement}),
        the names involved are checked both for definedness and any bindings
        created are respected in the suite of the statement and afterwards.
        """
        self.flakes('''
        from __future__ import with_statement
        c = d = e = g = h = i = None
        with open('foo') as [(a, b), c[d], e.f, g[h:i]]:
            a, b, c, d, e, g, h, i
        a, b, c, d, e, g, h, i
        ''')


    def test_withStatementSingleNameUndefined(self):
        """
        An undefined name warning is emitted if the name first defined by a
        C{with} statement is used before the C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        bar
        with open('foo') as bar:
            pass
        ''', m.UndefinedName)


    def test_withStatementTupleNamesUndefined(self):
        """
        An undefined name warning is emitted if a name first defined by a the
        tuple-unpacking form of the C{with} statement is used before the
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        baz
        with open('foo') as (bar, baz):
            pass
        ''', m.UndefinedName)


    def test_withStatementSingleNameRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by the name defined by a C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as bar:
            pass
        ''', m.RedefinedWhileUnused)


    def test_withStatementTupleNamesRedefined(self):
        """
        A redefined name warning is emitted if a name bound by an import is
        rebound by one of the names defined by the tuple-unpacking form of a
        C{with} statement.
        """
        self.flakes('''
        from __future__ import with_statement
        import bar
        with open('foo') as (bar, baz):
            pass
        ''', m.RedefinedWhileUnused)


    def test_withStatementUndefinedInside(self):
        """
        An undefined name warning is emitted if a name is used inside the
        body of a C{with} statement without first being bound.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz
        ''', m.UndefinedName)


    def test_withStatementNameDefinedInBody(self):
        """
        A name defined in the body of a C{with} statement can be used after
        the body ends without warning.
        """
        self.flakes('''
        from __future__ import with_statement
        with open('foo') as bar:
            baz = 10
        baz
        ''')


    def test_withStatementUndefinedInExpression(self):
        """
        An undefined name warning is emitted if a name in the I{test}
        expression of a C{with} statement is undefined.
        """
        self.flakes('''
        from __future__ import with_statement
        with bar as baz:
            pass
        ''', m.UndefinedName)

        self.flakes('''
        from __future__ import with_statement
        with bar as bar:
            pass
        ''', m.UndefinedName)



class Python27Test(harness.Test):
    """
    Tests for checking of syntax only available in Python 2.7 and newer.
    """
    if version_info < (2, 7):
        skip = "Python 2.7 required for dict/set comprehension tests"

    def test_dictComprehension(self):
        """
        Dict comprehensions are properly handled.
        """
        self.flakes('''
        a = {1: x for x in range(10)}
        ''')

    def test_setComprehensionAndLiteral(self):
        """
        Set comprehensions are properly handled.
        """
        self.flakes('''
        a = {1, 2, 3}
        b = {x for x in range(10)}
        ''')

########NEW FILE########
__FILENAME__ = test_script

"""
Tests for L{pyflakes.scripts.pyflakes}.
"""

import sys
from StringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from pyflakes.scripts.pyflakes import checkPath

def withStderrTo(stderr, f):
    """
    Call C{f} with C{sys.stderr} redirected to C{stderr}.
    """
    (outer, sys.stderr) = (sys.stderr, stderr)
    try:
        return f()
    finally:
        sys.stderr = outer



class CheckTests(TestCase):
    """
    Tests for L{check} and L{checkPath} which check a file for flakes.
    """
    def test_missingTrailingNewline(self):
        """
        Source which doesn't end with a newline shouldn't cause any
        exception to be raised nor an error indicator to be returned by
        L{check}.
        """
        fName = self.mktemp()
        FilePath(fName).setContent("def foo():\n\tpass\n\t")
        self.assertFalse(checkPath(fName))


    def test_checkPathNonExisting(self):
        """
        L{checkPath} handles non-existing files.
        """
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath('extremo'))
        self.assertEquals(err.getvalue(), 'extremo: No such file or directory\n')
        self.assertEquals(count, 1)


    def test_multilineSyntaxError(self):
        """
        Source which includes a syntax error which results in the raised
        L{SyntaxError.text} containing multiple lines of source are reported
        with only the last line of that source.
        """
        source = """\
def foo():
    '''

def bar():
    pass

def baz():
    '''quux'''
"""

        # Sanity check - SyntaxError.text should be multiple lines, if it
        # isn't, something this test was unprepared for has happened.
        def evaluate(source):
            exec source
        exc = self.assertRaises(SyntaxError, evaluate, source)
        self.assertTrue(exc.text.count('\n') > 1)

        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)

        self.assertEqual(
            err.getvalue(),
            """\
%s:8: invalid syntax
    '''quux'''
           ^
""" % (sourcePath.path,))


    def test_eofSyntaxError(self):
        """
        The error reported for source files which end prematurely causing a
        syntax error reflects the cause for the syntax error.
        """
        source = "def foo("
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: unexpected EOF while parsing
def foo(
         ^
""" % (sourcePath.path,))


    def test_nonDefaultFollowsDefaultSyntaxError(self):
        """
        Source which has a non-default argument following a default argument
        should include the line number of the syntax error.  However these
        exceptions do not include an offset.
        """
        source = """\
def foo(bar=baz, bax):
    pass
"""
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: non-default argument follows default argument
def foo(bar=baz, bax):
""" % (sourcePath.path,))


    def test_nonKeywordAfterKeywordSyntaxError(self):
        """
        Source which has a non-keyword argument after a keyword argument should
        include the line number of the syntax error.  However these exceptions
        do not include an offset.
        """
        source = """\
foo(bar=baz, bax)
"""
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEqual(count, 1)
        self.assertEqual(
            err.getvalue(),
            """\
%s:1: non-keyword arg after keyword arg
foo(bar=baz, bax)
""" % (sourcePath.path,))


    def test_permissionDenied(self):
        """
        If the a source file is not readable, this is reported on standard
        error.
        """
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent('')
        sourcePath.chmod(0)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "%s: Permission denied\n" % (sourcePath.path,))


    def test_misencodedFile(self):
        """
        If a source file contains bytes which cannot be decoded, this is
        reported on stderr.
        """
        source = u"""\
# coding: ascii
x = "\N{SNOWMAN}"
""".encode('utf-8')
        sourcePath = FilePath(self.mktemp())
        sourcePath.setContent(source)
        err = StringIO()
        count = withStderrTo(err, lambda: checkPath(sourcePath.path))
        self.assertEquals(count, 1)
        self.assertEquals(
            err.getvalue(), "%s: problem decoding source\n" % (sourcePath.path,))

########NEW FILE########
__FILENAME__ = test_undefined_names

from _ast import PyCF_ONLY_AST

from twisted.trial.unittest import TestCase

from pyflakes import messages as m, checker
from pyflakes.test import harness


class Test(harness.Test):
    def test_undefined(self):
        self.flakes('bar', m.UndefinedName)

    def test_definedInListComp(self):
        self.flakes('[a for a in range(10) if a]')


    def test_functionsNeedGlobalScope(self):
        self.flakes('''
        class a:
            def b():
                fu
        fu = 1
        ''')

    def test_builtins(self):
        self.flakes('range(10)')


    def test_magicGlobalsFile(self):
        """
        Use of the C{__file__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__file__')


    def test_magicGlobalsBuiltins(self):
        """
        Use of the C{__builtins__} magic global should not emit an undefined
        name warning.
        """
        self.flakes('__builtins__')


    def test_magicGlobalsName(self):
        """
        Use of the C{__name__} magic global should not emit an undefined name
        warning.
        """
        self.flakes('__name__')


    def test_magicGlobalsPath(self):
        """
        Use of the C{__path__} magic global should not emit an undefined name
        warning, if you refer to it from a file called __init__.py.
        """
        self.flakes('__path__', m.UndefinedName)
        self.flakes('__path__', filename='package/__init__.py')


    def test_globalImportStar(self):
        '''Can't find undefined names with import *'''
        self.flakes('from fu import *; bar', m.ImportStarUsed)

    def test_localImportStar(self):
        '''A local import * still allows undefined names to be found in upper scopes'''
        self.flakes('''
        def a():
            from fu import *
        bar
        ''', m.ImportStarUsed, m.UndefinedName)

    def test_unpackedParameter(self):
        '''Unpacked function parameters create bindings'''
        self.flakes('''
        def a((bar, baz)):
            bar; baz
        ''')

    def test_definedByGlobal(self):
        '''"global" can make an otherwise undefined name in another function defined'''
        self.flakes('''
        def a(): global fu; fu = 1
        def b(): fu
        ''')
    test_definedByGlobal.todo = ''

    def test_globalInGlobalScope(self):
        """
        A global statement in the global scope is ignored.
        """
        self.flakes('''
        global x
        def foo():
            print x
        ''', m.UndefinedName)

    def test_del(self):
        '''del deletes bindings'''
        self.flakes('a = 1; del a; a', m.UndefinedName)

    def test_delGlobal(self):
        '''del a global binding from a function'''
        self.flakes('''
        a = 1
        def f():
            global a
            del a
        a
        ''')

    def test_delUndefined(self):
        '''del an undefined name'''
        self.flakes('del a', m.UndefinedName)

    def test_globalFromNestedScope(self):
        '''global names are available from nested scopes'''
        self.flakes('''
        a = 1
        def b():
            def c():
                a
        ''')

    def test_laterRedefinedGlobalFromNestedScope(self):
        """
        Test that referencing a local name that shadows a global, before it is
        defined, generates a warning.
        """
        self.flakes('''
        a = 1
        def fun():
            a
            a = 2
            return a
        ''', m.UndefinedLocal)

    def test_laterRedefinedGlobalFromNestedScope2(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global declared in an enclosing scope, before it is defined, generates
        a warning.
        """
        self.flakes('''
            a = 1
            def fun():
                global a
                def fun2():
                    a
                    a = 2
                    return a
        ''', m.UndefinedLocal)


    def test_intermediateClassScopeIgnored(self):
        """
        If a name defined in an enclosing scope is shadowed by a local variable
        and the name is used locally before it is bound, an unbound local
        warning is emitted, even if there is a class scope between the enclosing
        scope and the local scope.
        """
        self.flakes('''
        def f():
            x = 1
            class g:
                def h(self):
                    a = x
                    x = None
                    print x, a
            print x
        ''', m.UndefinedLocal)


    def test_doubleNestingReportsClosestName(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        variable declared in two different outer scopes before it is defined
        in the innermost scope generates an UnboundLocal warning which
        refers to the nearest shadowed name.
        """
        exc = self.flakes('''
            def a():
                x = 1
                def b():
                    x = 2 # line 5
                    def c():
                        x
                        x = 3
                        return x
                    return x
                return x
        ''', m.UndefinedLocal).messages[0]
        self.assertEqual(exc.message_args, ('x', 5))


    def test_laterRedefinedGlobalFromNestedScope3(self):
        """
        Test that referencing a local name in a nested scope that shadows a
        global, before it is defined, generates a warning.
        """
        self.flakes('''
            def fun():
                a = 1
                def fun2():
                    a
                    a = 1
                    return a
                return a
        ''', m.UndefinedLocal)

    def test_nestedClass(self):
        '''nested classes can access enclosing scope'''
        self.flakes('''
        def f(foo):
            class C:
                bar = foo
                def f(self):
                    return foo
            return C()

        f(123).f()
        ''')

    def test_badNestedClass(self):
        '''free variables in nested classes must bind at class creation'''
        self.flakes('''
        def f():
            class C:
                bar = foo
            foo = 456
            return foo
        f()
        ''', m.UndefinedName)

    def test_definedAsStarArgs(self):
        '''star and double-star arg names are defined'''
        self.flakes('''
        def f(a, *b, **c):
            print a, b, c
        ''')

    def test_definedInGenExp(self):
        """
        Using the loop variable of a generator expression results in no
        warnings.
        """
        self.flakes('(a for a in xrange(10) if a)')



class NameTests(TestCase):
    """
    Tests for some extra cases of name handling.
    """
    def test_impossibleContext(self):
        """
        A Name node with an unrecognized context results in a RuntimeError being
        raised.
        """
        tree = compile("x = 10", "<test>", "exec", PyCF_ONLY_AST)
        # Make it into something unrecognizable.
        tree.body[0].targets[0].ctx = object()
        self.assertRaises(RuntimeError, checker.Checker, tree)

########NEW FILE########
