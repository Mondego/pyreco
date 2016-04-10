import re
from ASTUtils import *
from collections import defaultdict


class ASTAnalyser(ast.NodeVisitor):
    """
    df_graph: Data-FLow graph for the source file
    scope: Current scope
    parent_node: List to keep track of parents for the current node
    obj_list: List of the live objects, mapped with their scopes
    ignore_list: List of objects to be ignored while considering attribute calls (function arguments)
    func_list: Dict of functions in the source file and their respective arguments
    imports: Dict of Libraries and their modules imported with info on the alias used in the source file
    """
    def __init__(self, func_list):
        self.df_graph = DFGraph()
        self.scope = ""
        self.parent_node = ""
        self.obj_list = defaultdict(dict)
        self.ignore_list=defaultdict(list)
        self.func_list = func_list
        self.imports = dict()
        #might require defaultdict(list)
        self.add_node_to_graph(DummyNode())

    """ClassDef(identifier name, expr* bases, stmt* body, expr* decorator_list)"""
    def visit_ClassDef(self,node):
        if DEBUG:
            print "visit_ClassDef"
        count=str(self.df_graph.count)
        scope='_'.join(['class',node.name, count])
        self.ignore_list[scope]=\
            self.ignore_list[self.scope][:]

        fn_parent=''
        cls_parent=''
        node_num=self.parent_node
        if node.body:
            for stmt in node.body:
                self.scope=scope
                if isinstance(stmt,ast.FunctionDef):
                    if not fn_parent:
                        fn_parent=self.parent_node
                    self.parent_node=fn_parent
                    self.visit(stmt)

                elif isinstance(stmt,ast.ClassDef):
                    if not cls_parent:
                        cls_parent=self.parent_node
                    self.parent_node=cls_parent
                    self.visit(stmt)

                else:
                    self.parent_node=node_num
                    self.visit(stmt)
                    node_num=self.parent_node
        self.parent_node=node_num
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)


    """Module(stmt* body)"""
    def visit_Module(self, node):
        if DEBUG:
            print "visit_Module"
        scope = "module"
        self.ignore_list[scope]=\
            self.ignore_list[self.scope][:]
        fn_parent=''
        cls_parent=''
        node_num=self.parent_node
        if node.body:
            for stmt in node.body:
                self.scope=scope
                if isinstance(stmt,ast.FunctionDef):
                    if not fn_parent:
                        fn_parent=self.parent_node
                    self.parent_node=fn_parent
                    self.visit(stmt)

                elif isinstance(stmt,ast.ClassDef):
                    if not cls_parent:
                        cls_parent=self.parent_node
                    self.parent_node=cls_parent
                    self.visit(stmt)

                else:
                    self.parent_node=node_num
                    self.visit(stmt)
                    node_num=self.parent_node

        self.parent_node=node_num
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)


    """FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)"""
    def visit_FunctionDef(self, node):
        if DEBUG:
            print "visit_FunctionDef"
        count=str(self.df_graph.count)
        scope = '_'.join(['function', node.name, count])
        self.ignore_list[scope]=\
            self.ignore_list[self.scope][:]

        """Ignoring Function args"""
        if node.args.args:
            for arg in node.args.args:
                arg_val='.'.join(get_node_value(arg))
                if arg_val!='self':
                    self.ignore_list[scope].append(arg_val)

        fn_parent=''
        cls_parent=''
        node_num=self.parent_node
        if node.body:
            for stmt in node.body:
                self.scope=scope
                if isinstance(stmt,ast.FunctionDef):
                    if not fn_parent:
                        fn_parent=self.parent_node
                    self.parent_node=fn_parent
                    self.visit(stmt)

                elif isinstance(stmt,ast.ClassDef):
                    if not cls_parent:
                        cls_parent=self.parent_node
                    self.parent_node=cls_parent
                    self.visit(stmt)

                else:
                    self.parent_node=node_num
                    self.visit(stmt)
                    node_num=self.parent_node

        self.parent_node=node_num
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)

    """
    ImportFrom(identifier? module, alias* names, int? level)
    (might have to change implementation)
    """
    def visit_ImportFrom(self, node):
        if DEBUG:
            print "visit_ImportFrom"
        lib = node.module
        for name in node.names:
            if name.asname is not None:
                alias = name.asname
                if lib is None:
                    pass
                elif alias not in self.imports.keys():
                    self.imports[alias] = [lib + '.' + name.name]
                else:
                    if '.'.join([lib, name.name]) not in self.imports[alias]:
                        self.imports[alias].append('.'.join([lib, name.name]))
            else:
                module = name.name
                if lib is None:
                    pass
                elif '*' == module:
                    self.add_lib_objects(lib)
                elif module not in self.imports.keys():
                    self.imports[module] = [lib + '.' + module]
                else:
                    if '.'.join([lib, module]) not in self.imports[module]:
                        self.imports[module].append('.'.join([lib, module]))

    """Import(alias* names)"""
    def visit_Import(self, node):
        if DEBUG:
            print "visit_Import"

        """Alias names are stored in the imports dict"""
        if node.names:
            for name in node.names:
                if name.asname is not None:
                    self.imports[name.name] = [name.asname]

    """Assign(expr* targets, expr value)"""
    def visit_Assign(self, node):
        if DEBUG:
            print "visit_Assign"

        obj_list = [obj for values in self.obj_list.values() for obj in values.keys()]

        if node.targets:
            for target in node.targets:
                ignoreAssignment=False

                """Ignore Subscript-ed Assignments"""
                if isinstance(target, ast.Subscript):
                    ignoreAssignment = True

                tgt = [target]
                if isinstance(target, ast.Tuple):
                    tgt = target.elts
                t_value = []

                for t in tgt:
                    t_value.append(".".join(get_node_value(t)))
                target = ','.join(t_value)

                if not ignoreAssignment:
                    ignore_list=self.ignore_list[self.scope]
                    if target in ignore_list:
                        self.ignore_list[self.scope].remove(target)

                    """
                    if self.scope == "module":
                        target = GLOBAL_PREFIX + target
                    elif self.scope.startswith("class"):
                        target = CLASS_PREFIX + target
                    """
                    if isinstance(node.value, ast.Call):
                        src_func_name = get_node_value(node.value.func)
                        fn_name = ".".join(src_func_name)

                        if not self.is_function_in_src(fn_name):
                            srclist = self.get_source_list(src_func_name)

                            """clause for function argument assignments"""
                            """
                            if self.scope.startswith('function'):
                                index=self.scope.find('_')
                                function_name=self.scope[index+1:]
                                if self.func_list[function_name]:
                                    for arg_list in self.func_list[function_name]:
                                        if target in arg_list:
                                            target=ARG_PREFIX+':'+target
                            """
                            self.add_node_to_graph(
                                AssignmentNode(srclist, target,
                                               node.lineno, node.col_offset))

                            self.obj_list[self.scope][target]=srclist
                    else:
                        if target in obj_list:
                            self.kill_obj_after_reassignment(target)

    """Attribute(expr value, identifier attr, expr_context ctx)"""
    def visit_Attribute(self, node):
        if DEBUG:
            print "visit_Attribute"

        obj_list = [obj for values in self.obj_list.values() for obj in values.keys()]
        ignore_list = self.ignore_list[self.scope]

        attr_name=".".join(
            get_node_value(node.value))

        if attr_name in obj_list and attr_name not in ignore_list:
            self.add_node_to_graph(
                CallNode(attr_name,
                          node.attr,
                          node.lineno, node.col_offset))

    def visit_Subscript(self, node):
        """dummy function to prevent visiting the nodes if subscripts are present"""

    """For(expr target, expr iter, stmt* body, stmt* orelse)"""
    def visit_For(self, node):
        if DEBUG:
            print "visit_For"

        self.visit(node.iter)

        scope = "_".join(['for']+
                         self.parent_node)
        parent_scope=self.scope
        self.obj_list[scope] = {}

        """Target may contain tuples"""
        if get_node_value(node.target):
            targets=get_node_value(node.target)[0].split(",")

            for tgt in targets:
                self.ignore_list[scope].append(tgt)


        parent=self.parent_node
        else_node=parent
        for_node=parent

        if node.body:
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for stmt in node.body:
                self.scope=scope
                self.visit(stmt)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            for_node=self.parent_node

        if node.orelse:
            scope="_".join(['for-else']+
                           self.parent_node)
            self.parent_node=parent
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for stmt in node.orelse:
                self.scope=scope
                self.visit(stmt)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            else_node=self.parent_node

        parent=set(for_node+else_node)
        self.parent_node=list(parent)


    """While(expr test, stmt* body, stmt* orelse)"""
    def visit_While(self, node):
        if DEBUG:
            print "visit_While"

        self.visit(node.test)

        parent=self.parent_node
        else_node=self.parent_node
        parent_scope=self.scope

        if node.body:
            scope = "_".join(['while']+
                         self.parent_node)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for stmt in node.body:
                self.scope=scope
                self.visit(stmt)
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)
        while_node=self.parent_node

        if node.orelse:
            self.parent_node=parent
            scope= "_".join(['while-else']+
                         self.parent_node)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for stmt in node.orelse:
                self.scope=scope
                self.visit(stmt)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            else_node=self.parent_node

        parent=set(while_node+else_node)
        self.parent_node=list(parent)

    """With(expr context_expr, expr? optional_vars, stmt* body)"""
    def visit_With(self, node):
        if DEBUG:
            print "visit_With"

        with_expr = [".".join(get_node_value(node.context_expr))]
        scope = "_".join(['with']+ with_expr)
        self.ignore_list[scope]=\
            self.ignore_list[self.scope][:]
        self.scope = scope

        if isinstance(node.context_expr, ast.Call):
            target = ".".join(get_node_value(node.optional_vars))
            if len(target) != 0:
                self.add_node_to_graph(
                    AssignmentNode(with_expr,target,
                                   node.lineno, node.col_offset))
                self.obj_list[self.scope][target]=with_expr

        if node.body:
            for stmt in node.body:
                self.scope=scope
                self.visit(stmt)

        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)

    """If(expr test, stmt* body, stmt* orelse)"""
    def visit_If(self, node):
        if DEBUG:
            print "visit_If"

        self.visit(node.test)
        parent = self.parent_node
        else_node=self.parent_node
        parent_scope=self.scope

        if node.body:
            scope = '_'.join(['if']+parent)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for obj in node.body:
                self.scope = scope
                self.visit(obj)

            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
        if_node=self.parent_node


        if node.orelse:
            self.parent_node=parent
            scope = '_'.join(['else']+
                             self.parent_node)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for obj in node.orelse:
                self.scope = scope
                self.visit(obj)

            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            else_node=self.parent_node

        parent=set(if_node+else_node)
        self.parent_node=list(parent)

    """IfExp(expr test, expr body, expr orelse)"""
    def visit_IfExp(self, node):
        if DEBUG:
            print "visit_IfExp"

        self.visit(node.test)
        parent = self.parent_node
        else_node=self.parent_node
        parent_scope=self.scope

        scope = '_'.join(['ifexp']+parent)
        self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
        self.scope = scope
        self.visit(node.body)
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)
        if_node=self.parent_node


        scope = '_'.join(['else']+parent)
        self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
        self.scope = scope
        self.visit(node.orelse)
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)
        else_node=self.parent_node

        parent=set(if_node+else_node)
        self.parent_node=list(parent)


    """TryExcept(stmt* body, excepthandler* handlers, stmt* orelse)"""
    def visit_TryExcept(self, node):
        if DEBUG:
            print "visit_TryExcept"

        parent = self.parent_node
        except_node = parent
        else_node = parent
        parent_scope=self.scope

        if node.body:
            scope = '_'.join(['try']+parent)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for obj in node.body:
                self.scope = scope
                self.visit(obj)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)

        try_node=self.parent_node

        if node.handlers:
            """ the scoping is handled in ExceptHandler node """
            for obj in node.handlers:
                self.parent_node = parent
                self.visit(obj)
            except_node=self.parent_node

        if node.orelse:
            scope = '_'.join(['try-else']+ parent)
            self.parent_node = parent
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for stmt in node.orelse:
                self.scope = scope
                self.visit(stmt)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            else_node=self.parent_node

        parent=set(try_node+except_node+else_node)
        self.parent_node=list(parent)

    """TryFinally(stmt* body, stmt* finalbody)"""
    def visit_TryFinally(self, node):
        if DEBUG:
            print "visit_TryFinally"

        parent = self.parent_node
        finally_node = parent
        parent_scope=self.scope

        if node.body:
            scope = '_'.join(['try']+parent)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            for obj in node.body:
                self.scope = scope
                self.visit(obj)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)

        try_node=self.parent_node

        if node.finalbody:
            scope = '_'.join(['try-finally']+ parent)
            self.ignore_list[scope]=\
                self.ignore_list[parent_scope][:]
            self.parent_node = parent
            for stmt in node.finalbody:
                self.scope = scope
                self.visit(stmt)
            self.clear_obj_list(scope)
            self.clear_ignore_list(scope)
            finally_node=self.parent_node

        parent=set(try_node+finally_node)
        self.parent_node=list(parent)

    """ExceptHandler(expr? type, expr? name, stmt* body)"""
    def visit_ExceptHandler(self, node):
        if DEBUG:
            print "visit_ExceptHandler"

        scope = '_'.join(['except']+
                         self.parent_node)
        self.ignore_list[scope]=\
                self.ignore_list[self.scope][:]

        for obj in node.body:
            self.scope = scope
            self.visit(obj)
        self.clear_obj_list(scope)
        self.clear_ignore_list(scope)

    def is_function_in_src(self, function_name):
        if DEBUG:
            print "is_function_in_src"
        if function_name in self.func_list.keys():
            return True
        return False

    def add_node_to_graph(self, node):
        if DEBUG:
            print "add_node_to_graph"

        self.parent_node=\
            [self.df_graph.add_node(node,self.parent_node)]

    def add_lib_objects(self, lib_name):
        try:
            lib = __import__(lib_name)
            pattern = re.compile('__\\w+__')
            for member in dir(lib):
                if pattern.match(member) is None:
                    if member not in self.imports.keys():
                        self.imports[member] = [lib_name + '.' + member]
                    else:
                        self.imports[member].append(lib_name + '.' + member)
        except:
            pass

    def get_source_list(self, source_fn_list, suffix="", result=None):
        if DEBUG:
            print "get_source_list"

        if result is None:
            result = []
        if len(source_fn_list) == 0:
            if len(result) == 0:
                return [suffix[1:]]
            return result
        elif ".".join(source_fn_list) in self.imports.keys():
            key = ".".join(source_fn_list)
            for value in self.imports[key]:
                result.append(value + suffix)
            return result
        else:
            return self.get_source_list(source_fn_list[:-1],
                                        "." + source_fn_list[-1]
                                        + suffix, result)

    """
    Deletes the objects in a given scope only
    if they aren't alive in a parent scope
    """
    def clear_obj_list(self, scope):
        if DEBUG:
            print "in clear_obj_list"
            print "scope:", scope
            print "obj_list",self.obj_list

        obj_list=self.obj_list[scope].keys()
        live_obj_list=[]
        for key in self.obj_list.keys():
            if key!=scope:
                live_obj_list.extend(
                    self.obj_list[key].keys())

        for obj in obj_list:
            if obj not in live_obj_list:
                self.add_node_to_graph(
                            DeadNode(obj))

            self.obj_list[scope].pop(obj)
        self.obj_list.pop(scope)

    def clear_ignore_list(self, scope):
        if DEBUG:
            print "in clear_ignore_list"
        if scope in self.ignore_list.keys():
            del self.ignore_list[scope]


    """
    Kills an object if it is in current scope
    Ignores the object in current scope otherwise
    """
    def kill_obj_after_reassignment(self, target):
        if DEBUG:
            print "in kill_obj_after_reassignment"

        object_list = self.obj_list[self.scope]
        if target in object_list.keys():
            self.obj_list[self.scope].pop(target)
            self.add_node_to_graph(DeadNode(target))
        else:
            if target not in self.ignore_list[self.scope]:
                self.ignore_list[self.scope].append(target)








