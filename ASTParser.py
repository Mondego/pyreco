import ast
from GraphNode import GraphNode

class ASTParser(ast.NodeVisitor):
    def __init__(self):
        super(ASTParser,self).__init__()
        self.df_graph=[]
        self.obj_list=[]

    def visit_Assign(self, node):
        if isinstance(node.value,ast.Call):
            if isinstance(node.value.func, ast.Name) :
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.df_graph.append(
                                GraphNode(node.value.func.id,
                                          '--becomes--',
                                          target.id))
                            self.obj_list.append(target.id)

        return self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value,ast.Name):
            if node.value.id in self.obj_list:
                self.df_graph.append(
                    GraphNode(node.value.id,
                              '--calls--',
                              node.attr))

        return self.generic_visit(node)

