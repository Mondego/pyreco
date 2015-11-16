import ast


class ASTFunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        super(ASTFunctionVisitor, self).__init__()
        self.func_list = []

    def visit_FunctionDef(self, node):
        fname=node.name
        if 'self' in [arg.id for arg in node.args.args]:
            fname='self.'+fname
        self.func_list.append(fname)
        return self.generic_visit(node)
