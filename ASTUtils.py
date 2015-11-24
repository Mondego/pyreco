import ast

def get_node_value(node):
    node_val = []
    while node != "":
        if isinstance(node, ast.Name):
            node_val = [node.id] + node_val
            break
        elif isinstance(node, ast.Tuple):
            t_val=[]
            for t in node.elts:
                t_val.append('.'.join(get_node_value(t)))
            node_val=[','.join(t_val)]+node_val
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

