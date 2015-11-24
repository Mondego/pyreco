import ast
from ASTUtils import get_node_value

class ASTFunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        super(ASTFunctionVisitor, self).__init__()
        self.func_list = []

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            if '.'.join(get_node_value(arg))=='self':
                self.func_list.append('self.'+node.name)
                break
        return self.generic_visit(node)
