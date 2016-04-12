import ast
from collections import defaultdict

DEBUG=0
#flag to switch on for debug msgs

def get_node_value(node):
    node_val = []
    while node != "":
        if isinstance(node, ast.Name):
            node_val = [node.id] + node_val
            break
        elif isinstance(node, ast.Tuple) or \
                isinstance(node, ast.List):
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
    return node_val

def get_arg_value(node):
    node_val=[]
    join=False
    while node !="":
        if isinstance(node, ast.Name):
            node_val=[node.id]+node_val
            node=""
            join=True
        elif isinstance(node, ast.Str):
            node_val=[node.s]+node_val
            node=""
            join=True
        elif isinstance(node, ast.Attribute):
            node_val = [node.attr] + node_val
            node = node.value
            join=True
        elif isinstance(node, ast.Tuple):
            t_val=[]
            for t in node.elts:
                t_val.append(get_arg_value(t))
            node_val=tuple(t_val)
            node=""
        elif isinstance(node, ast.List):
            for l in node.elts:
                node_val.append(get_arg_value(l))
            node=""
        elif isinstance(node, ast.Call):
            node = node.func
            join=True
        elif isinstance(node, ast.Num):
            node_val=[node.n]
            node=""
        elif isinstance(node,ast.Dict):
            d_val=[]
            for key, val in zip(node.keys,node.values):
                k_val=get_arg_value(key)
                v_val=get_arg_value(val)
                if k_val and v_val:
                    d_val.append((k_val,v_val))
            node_val=d_val
            node=""
        else:
            #args of the following types are ignored currently
            # BinOp, Subscript, GeneratorExp, Lambda, UnaryOp
            #print "get_arg_value", ast.dump(node)
            break
    if join:
        node_val='.'.join(node_val)

    return node_val


def get_context(node):
    context=defaultdict(list)
    if hasattr(node, 'args'):
        if node.args:
            for arg in node.args:
                arg_value=get_arg_value(arg)
                if arg_value:
                    context['args'].append(
                        get_arg_value(arg))
    if hasattr(node, 'keywords'):
        if node.keywords:
            for keyword in node.keywords:

                context['keywords'].append(
                    (keyword.arg,
                    get_arg_value(keyword.value))
                )
    return context


class GraphNode():
    def __init__(self, src, op, tgt,
                 adjList='', val=''):
        self.src=src
        self.op=op
        self.tgt=tgt
        self.adjList=adjList
        self.val=val

    def __str__(self):
        return "{0} {1} {2} {3} {4}".format(self.src,
                                    self.op,
                                    self.tgt,
                                    self.adjList)

class AssignmentNode(GraphNode):
    def __init__(self, src, tgt,
                 lineNum = "", colOffset = "",
                 context= ""):
        GraphNode.__init__(self,
                           src, "--becomes--", tgt)
        self.lineNum=lineNum
        self.colOffset=colOffset
        self.context=context

    def __str__(self):
        return "{0} {1} {2} {3} {4} {5} {6} {7}".format(
            self.src,
            self.op,
            self.tgt,
            self.adjList,
            self.val,
            self.lineNum,
            self.colOffset,
            self.context)

class CallNode(GraphNode):
    def __init__(self, src, tgt,
                 lineNum = "", colOffset = ""):
        GraphNode.__init__(self,
                           src, "--calls--", tgt)
        self.lineNum=lineNum
        self.colOffset=colOffset

    def __str__(self):
        return "{0} {1} {2} {3} {4} {5} {6}".format(
            self.src,
            self.op,
            self.tgt,
            self.adjList,
            self.val,
            self.lineNum,
            self.colOffset)

class DeadNode(GraphNode):
    def __init__(self, src):
        GraphNode.__init__(self,
                           src, "--dies--", "")

    def __str__(self):
        return "{0} {1} {2} {3}".format(
            self.src,
            self.op,
            self.adjList,
            self.val)

class DummyNode(GraphNode):
    def __init__(self):
        GraphNode.__init__(self,
                           "", "", "")

    def __str__(self):
        return "{0}".format(
            self.adjList
        )

class DFGraph():
    def __init__(self, graph_dict=None, start_vertex=''):
        if graph_dict is None:
            self.graph_dict={}
        else:
            self.graph_dict=graph_dict
        self.start_vertex=start_vertex
        self.count=len(self.graph_dict.keys())

    def add_node(self, graphNode, parent):
        if DEBUG:
            print 'add_node beg', graphNode, parent

        self.count += 1
        node = str(self.count)

        graphNode.val = {}
        if self.count == 1:
            self.start_vertex = node

        for p in parent:
            p_node = self.graph_dict[p]
            """Add in parent's adjacency List"""
            if not p_node.adjList:
                p_node.adjList = []
            p_node.adjList.append(node)

            """Compute the values of live objects"""
            if p_node.val:
                for key, values in p_node.val.items():
                    """Node values are a union of the parent's vals"""
                    if key in graphNode.val.keys():
                        for value in values:
                            if value not in graphNode.val[key]:
                                graphNode.val[key].append(value)
                    else:
                        graphNode.val[key] = values[:]

        if isinstance(graphNode, AssignmentNode):
            graphNode.val[graphNode.tgt] = graphNode.src

        elif isinstance(graphNode, DeadNode):
            graphNode.val.pop(graphNode.src)

        self.graph_dict[node] = graphNode
        if DEBUG:
            print node, self.graph_dict[node]
        return node

    def bfs(self):
        visited, queue = set(), [self.start_vertex]
        results=[]
        while queue:
            vertex = queue.pop(0)
            if vertex not in visited:
                results.append(self.graph_dict[vertex])
                visited.add(vertex)
                queue.extend(self.graph_dict[vertex].adjList)
        return results

    def dfs(self):
        visited, stack = set(), [self.start_vertex]
        results=[]
        while stack:
            vertex = stack.pop()
            results.append(self.graph_dict[vertex])
            if vertex not in visited:
                visited.add(vertex)
                stack.extend(
                    set(self.graph_dict[vertex].adjList) - visited)
        return results

    def find_paths(self, start, path=None, result=[]):
        if path is None:
            path=[]

        path=path+[start]
        adjList=self.graph_dict[start].adjList
        if not adjList:
            res=[]
            for node in path:
                res.append(self.graph_dict[node])
            result.append(res)
            return result
        else:
            for node in adjList:
               self.find_paths(node,
                               path)
        return result

    """To find all paths from start to leaf node in the graph"""
    def find_all_paths(self):
        res=self.find_paths(self.start_vertex)
        return res

    """To convert DF_Graph to JSON"""
    def serialize(self):
        if DEBUG:
            print "in serialize"

        result=None
        graph=self.graph_dict.copy()
        if graph:
            for key in graph.keys():
                graph[key]=graph[key].__dict__
                graph[key]['type']=self.graph_dict[key].__class__.__name__
            result=self.__dict__
            result['graph_dict']=graph
        return result

