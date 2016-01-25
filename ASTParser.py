import ast
import re
from GraphNode import GraphNode
from ASTUtils import get_node_value, GLOBAL_PREFIX, ARG_PREFIX



class ASTParser(ast.NodeVisitor):
    def __init__(self, func_list):
        super(ASTParser, self).__init__()
        self.df_graph = {}
        self.parent_scope = ""
        self.scope = ""
        self.branch_no = 0
        self.obj_list = {}
        self.func_list = func_list
        self.imports = {}

    def visit_Module(self, node):
        scope="module"
        self.obj_list[scope]=[]
        self.scope=scope
        self.generic_visit(node)
        self.clear_obj_list(scope)
        self.del_nodes_from_graph("main")

    def visit_FunctionDef(self,node):
        scope='_'.join(['function',node.name])
        self.obj_list[scope]=[]
        self.scope=scope
        for arg in node.args.args:
            if isinstance(arg, ast.Name):
                self.obj_list[scope].append(ARG_PREFIX+arg.id)
            elif isinstance(arg, ast.Tuple):
                for var in arg.elts:
                    self.obj_list[scope].append(ARG_PREFIX+var.id)
        self.generic_visit(node)
        self.clear_obj_list(scope)

    def visit_ImportFrom(self, node):
		lib = node.module
		for name in node.names:
			if name.asname is not None:
				alias = name.asname
				if lib is None:
					pass
				elif alias not in self.imports.keys():
					self.imports[alias] = [lib + '.' + name.name]
				else:
					if '.'.join([lib,name.name]) not in self.imports[alias]:
						self.imports[alias].append('.'.join([lib,name.name]))
			else:
				module = name.name
				if lib is None:
					pass
				elif '*' == module:
					self.add_lib_objects(lib)
				elif module not in self.imports.keys():
					self.imports[module] = [lib + '.' + module]
				else:
					if '.'.join([lib,module]) not in self.imports[module]:
						self.imports[module].append('.'.join([lib,module]))
		return self.generic_visit(node)


    def visit_Import(self, node):
        for name in node.names:
            if name.asname is not None:
                self.imports[name.name] = [name.asname]
        return self.generic_visit(node)

    def visit_Assign(self, node):
        obj_list=[obj for values in self.obj_list.values() for obj in values]
        for target in node.targets:
            tgt=[target]
            if isinstance(target, ast.Tuple):
                tgt=target.elts
            t_value=[]
            for t in tgt:
                t_value.append(".".join(get_node_value(t)))
            target=','.join(t_value)

            if self.scope == "module":
                target=GLOBAL_PREFIX+target

            self.kill_obj_after_reassignment(target)
            if isinstance(node.value, ast.Call):
                src_func_name = get_node_value(node.value.func, obj_list)
                fn_name = ".".join(src_func_name)
                if fn_name not in self.func_list:
                    srclist = self.get_source_list(src_func_name)
                    for func_name in srclist:
                        self.add_node_to_graph(
                            GraphNode(func_name,'--becomes--', target))
                    self.obj_list[self.scope].append(target)
        return self.generic_visit(node)

    def visit_Attribute(self, node):
        obj_list=[obj for values in self.obj_list.values() for obj in values]
        attr_func_name = get_node_value(node, obj_list)
        if len(attr_func_name) != 0:
            if ARG_PREFIX not in attr_func_name[0] \
                    and attr_func_name[0] in obj_list:
                self.add_node_to_graph(
                    GraphNode(".".join(attr_func_name[:-1]),
                              '--calls--', attr_func_name[-1]))
        return self.generic_visit(node)

    def visit_Subscript(self, node):
        """dummy function to prevent visiting the nodes if subscripts are present"""

    def visit_For(self,node):
         """dummy function to prevent visiting the nodes if for loops are present"""

    def visit_With(self, node):

        with_expr=".".join(get_node_value(node.context_expr))
        scope="_".join(['with',with_expr])
        self.scope=scope
        self.obj_list[self.scope]=[]
        if isinstance(node.context_expr, ast.Call):
            target = ".".join(get_node_value(node.optional_vars))
            if len(target) != 0:
                self.add_node_to_graph(
                    GraphNode(with_expr,'--becomes--', target))
                self.obj_list[self.scope].append(target)
        self.generic_visit(node)
        self.clear_obj_list(scope)

    def visit_If(self, node):
        parent=self.scope
        self.parent_scope=parent
        self.branch_no+=1
        scope='_'.join(['if',str(self.branch_no)])
        self.obj_list[scope]=[]
        self.scope=scope
        self.visit(node.test)
        for obj in node.body:
            self.visit(obj)
        self.clear_obj_list(scope)

        scope='_'.join(['else',str(self.branch_no)])
        self.parent_scope=parent
        self.obj_list[scope]=[]
        self.scope=scope
        for obj in node.orelse:
            self.visit(obj)
        self.clear_obj_list(scope)
        self.del_nodes_from_graph(parent)


    def visit_IfExp(self, node):
        parent=self.scope
        self.parent_scope=parent
        self.branch_no+=1
        scope='_'.join(['if',str(self.branch_no)])
        self.obj_list[scope]=[]
        self.scope=scope
        self.visit(node.test)
        self.visit(node.body)
        self.clear_obj_list(scope)

        scope='_'.join(['else',str(self.branch_no)])
        self.parent_scope=parent
        self.obj_list[scope]=[]
        self.scope=scope
        self.visit(node.orelse)
        self.clear_obj_list(scope)
        self.del_nodes_from_graph(parent)



    def visit_TryExcept(self, node):
        parent=self.scope
        self.parent_scope=parent
        self.branch_no+=1
        scope='_'.join(['try',str(self.branch_no)])
        self.obj_list[scope]=[]
        self.scope=scope
        for obj in node.body:
            self.visit(obj)
        self.clear_obj_list(scope)
        self.parent_scope=parent
        for obj in node.handlers:
            self.visit(obj)
        self.del_nodes_from_graph(parent)


    def visit_ExceptHandler(self, node):
        self.branch_no+=1
        scope='_'.join(['except',str(self.branch_no)])
        self.obj_list[scope]=[]
        self.scope=scope
        for obj in node.body:
            self.visit(obj)
        self.clear_obj_list(scope)
        self.branch_no+=1

    def add_node_to_graph(self, node):
        scope_type=self.scope.split("_")[0]
        if "main" not in self.df_graph.keys():
            self.df_graph["main"]=[]
        if scope_type in ["if","else","try","except"]:
            if self.scope not in self.df_graph.keys():
                if self.parent_scope in self.df_graph.keys():
                    self.df_graph[self.scope]=self.df_graph[self.parent_scope][:]
                else:
                    self.df_graph[self.scope]=self.df_graph["main"][:]
            self.df_graph[self.scope].append(node)
        else:
            for key in self.df_graph.keys():
                self.df_graph[key].append(node)

    def del_nodes_from_graph(self,scope):
        if scope in self.df_graph.keys():
            del self.df_graph[scope]

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

    def clear_obj_list(self,scope):
        if scope in self.obj_list.keys():
            for obj in self.obj_list[scope]:
                self.add_node_to_graph(
                    GraphNode(obj, '--dies--', ''))
            del self.obj_list[scope]
        self.scope="module"

    def kill_obj_after_reassignment(self, target):
        object_list=self.obj_list[self.scope]
        if target in object_list:
                self.add_node_to_graph(
                    GraphNode(target, '--dies--', ''))
                self.obj_list[self.scope].remove(target)
        elif ARG_PREFIX +target in object_list:
            self.add_node_to_graph(
                GraphNode(ARG_PREFIX +target, '--dies--', ''))
            self.obj_list[self.scope].remove(ARG_PREFIX +target)
        else:
            for t in target.split(","):
                if t in object_list:
                    self.add_node_to_graph(
                        GraphNode(t, '--dies--', ''))
                    self.obj_list[self.scope].remove(t)






