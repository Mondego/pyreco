import ast
from ASTUtils import get_node_value
from collections import defaultdict


class ASTFunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        super(ASTFunctionVisitor, self).__init__()
        self.func_list = defaultdict(list)


    def visit_FunctionDef(self, node):
        """Overloaded functions have same name"""
        fn_name=node.name
        arg_list=[]
        if node.args.args:
            for arg in node.args.args:
                if arg=='self':
                    fn_name=arg+'.'+fn_name
                else:
                    arg_list.append('.'.join(get_node_value(arg)))
        self.func_list[node.name].append(arg_list)
        return self.generic_visit(node)
