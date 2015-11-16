import ast
import re
from GraphNode import GraphNode

class ASTParser(ast.NodeVisitor):
    def __init__(self, func_list):
        super(ASTParser, self).__init__()
        self.df_graph = []
        self.obj_list = []
        self.func_list = func_list
        self.imports = {}

    def add_lib_objects(self, lib_name):
        try:
            lib = __import__(lib_name)
            pattern = re.compile('__\\w+__|_\\w+')
            for member in dir(lib):
                if pattern.match(member) is None:
                    if member not in self.imports.keys():
                        self.imports[member] = [lib_name + '.' + member]
                    else:
                        self.imports[member].append(lib_name + '.' + member)
        except ImportError as e:
            print e
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

    def get_node_value(self, node):
        node_val = []
        while node != "":
            if isinstance(node, ast.Name):
                node_val = [node.id] + node_val
                break
            elif isinstance(node, ast.Attribute):
                node_val = [node.attr] + node_val
                node = node.value
            elif isinstance(node, ast.Call):
                node = node.func
            elif isinstance(node, ast.Subscript):
                node = node.value
            else:
                break
        return node_val



    def visit_ImportFrom(self, node):
        lib = node.module
        for name in node.names:
            if name.asname is not None:
                alias = name.asname
                if alias not in self.imports.keys():
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
        if isinstance(node.value, ast.Call):
            src_func_name = self.get_node_value(node.value.func)
            for target in node.targets:
                tgt=[target]
                if isinstance(target, ast.Tuple):
                    tgt=target.elts
                t_value=[]
                for t in tgt:
                    t_value.append(".".join(self.get_node_value(t)))
                fn_name = ".".join(src_func_name)
                if fn_name not in self.func_list:
                    srclist = self.get_source_list(src_func_name, "", [])
                    for func_name in srclist:
                        self.df_graph.append(
                            GraphNode(func_name,
                                      '--becomes--',
                                      ','.join(t_value)))
                    self.obj_list.append(t_value)

        return self.generic_visit(node)

    def visit_Attribute(self, node):
        attr_func_name = self.get_node_value(node)
        if len(attr_func_name) != 0:
            if ".".join(attr_func_name[:-1]) in self.obj_list:
                self.df_graph.append(
                    GraphNode(".".join(attr_func_name[:-1]),
                              '--calls--',
                              attr_func_name[-1]))

        return self.generic_visit(node)
    
