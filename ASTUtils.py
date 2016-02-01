import ast

GLOBAL_PREFIX="glob:"
ARG_PREFIX="arg:"

def get_node_value(node, obj_list=[], prefix=''):
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
        else:
            break

    if prefix=='':
        for i in range(1,len(node_val)):
            obj_val=".".join(node_val[:i])
            if obj_val in obj_list:
                node_val=[obj_val]+node_val[i:]
                break
            elif ARG_PREFIX+obj_val in obj_list:
                node_val=[ARG_PREFIX+obj_val]+node_val[i:]
                break
            elif GLOBAL_PREFIX+obj_val in obj_list:
                node_val=[GLOBAL_PREFIX+obj_val]+node_val[i:]
                break
    else:
        node_val=[prefix+node_val[0]]+node_val[1:]

    return node_val

