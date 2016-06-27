import ast
import sys
from collections import defaultdict

DEBUG=0
#flag to switch on for debug msgs

#Subscript(value=Attribute(value=Name(id='self', ctx=Load()), attr='fields', ctx=Load()), slice=Index(value=Str(s='summary')), ctx=Load()
def get_node_value(node, live_obj=None):
    #print ast.dump(node)
    #print "in ASTUtils get_node_value"
    original_node=node
    node_val = []
    try:
        while node != "":
            if isinstance(node, ast.Name):
                #print live_obj,node.id, node.id in live_obj.keys()
                if live_obj:
                    suffix=".".join(node_val)
                    if node.id in live_obj.keys():
                        node_val=[]
                        for val in live_obj[node.id]:
                            node_val += [val+"."+suffix]
                    else:
                        node_val = [node.id] + node_val
                else:
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
            elif isinstance(node, ast.Subscript):
                node_value=node_val
                node_val=get_node_value(node.value)
                if node_val:
                    node_val[-1]+='['+'.'.join(get_node_value(node.slice))+']'
                node_val+=node_value
                break
            elif isinstance(node, ast.Index):
                if isinstance(node.value, ast.Str):
                    node_val=["'"+node.value.s+"'"]
                elif isinstance(node.value, ast.Num):
                    node_val=[str(node.value.n)]
                break
            else:
                break
    except:
        print sys.exc_info()
        print ast.dump(original_node)
    return node_val

def get_arg_value(node, live_objs):
    if DEBUG:
        print "get_arg_value", live_objs
    node_val=[]
    join=False
    while node !="":
        if isinstance(node, ast.Name):
            node_id=node.id
            if node_id in live_objs.keys():
                node_value=node_val
                node_val=[]
                for val in live_objs[node_id]:
                    node_val.append(
                        '.'.join([val]+node_value))
            else:
                node_val=[node_id]+node_val
                join=True
            node=""
        elif isinstance(node, ast.Str):
            node_val=node.s
            node=""
        elif isinstance(node, ast.Attribute):
            node_val = [node.attr] + node_val
            node = node.value
            join=True
        elif isinstance(node, ast.Tuple):
            t_val=[]
            for t in node.elts:
                t_val.append(get_arg_value(t, live_objs))
            node_val=t_val
            node=""
        elif isinstance(node, ast.List):
            for l in node.elts:
                node_val.append(get_arg_value(l, live_objs))
            node=""
        elif isinstance(node, ast.Call):
            node = node.func
            join=True
        elif isinstance(node, ast.Num):
            node_val=node.n
            node=""
        elif isinstance(node,ast.Dict):
            d_val=[]
            for key, val in zip(node.keys,node.values):
                k_val=get_arg_value(key, live_objs)
                v_val=get_arg_value(val, live_objs)
                if k_val and v_val:
                    d_val.append(k_val)
                    d_val.append(v_val)
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


def add_context(var_name, fn_node, live_objs):
    if DEBUG:
        print "get_context",live_objs
    context=defaultdict(list)
    if hasattr(fn_node, 'args'):
        if fn_node.args:
            for arg in fn_node.args:
                arg_value=get_arg_value(arg,live_objs)
                if arg_value:
                    context['arg_val'].append(arg_value)
                    context['arg_type'].append(
                        arg.__class__.__name__
                    )

    if hasattr(fn_node, 'keywords'):
        if fn_node.keywords:
            for keyword in fn_node.keywords:
                keyword_value=get_arg_value(keyword.value,live_objs)
                if keyword_value:
                    context['keyword_val'].append(keyword_value)
                    context['keyword_key'].append(keyword.arg)
                    context['keyword_type'].append(
                        keyword.value.__class__.__name__)
    context['obj_name'].append(var_name)
    return context


class GraphNode():
    def __init__(self, src, op, tgt,
                 adjList=None, val=None,
                 parent=None):
        self.src=src
        self.op=op
        self.tgt=tgt

        if adjList:
            self.adjList=adjList
        else:
            self.adjList=list()

        if val:
            self.val=val
        else:
            self.val=dict()

        if parent:
            self.parent=parent
        else:
            self.parent=list()


    def __str__(self):
        return "{0} {1} {2} {3} {4} {5}".\
            format(self.src, self.op, self.tgt,
                   self.adjList, self.parent)

class AssignmentNode(GraphNode):
    def __init__(self, src, tgt,
                 lineNum = "", colOffset = "",
                 context= None, adjList=None,
                 val=None, parent=None):
        GraphNode.__init__(self,
                           src, "--becomes--", tgt,
                           adjList, val, parent)
        self.lineNum=lineNum
        self.colOffset=colOffset
        if context:
            self.context=context
        else:
            self.context=dict()

    def __str__(self):
        return "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format(
            self.src, self.op, self.tgt,
            self.adjList, self.val, self.parent,
            self.lineNum, self.colOffset, self.context)

class CallNode(GraphNode):
    def __init__(self, src, tgt,
                 lineNum = "", colOffset = "",
                 adjList=None, val=None, parent=None):
        GraphNode.__init__(self,
                           src, "--calls--", tgt,
                           adjList, val, parent)
        self.lineNum=lineNum
        self.colOffset=colOffset

    def __str__(self):
        return "{0} {1} {2} {3} {4} {5} {6} {7}".format(
            self.src, self.op, self.tgt,
            self.adjList, self.parent, self.val,
            self.lineNum, self.colOffset)

class DeadNode(GraphNode):
    def __init__(self, src, adjList=None, val=None, parent=None):
        GraphNode.__init__(self,
                           src, "--dies--", "",
                           adjList, val, parent)

    def __str__(self):
        return "{0} {1} {2} {3} {4}".format(
            self.src,
            self.op,
            self.adjList,
            self.val,
            self.parent)

class DummyNode(GraphNode):
    def __init__(self, adjList=None, val=None, parent=None):
        GraphNode.__init__(self,
                           "", "", "",
                           adjList, val, parent)

    def __str__(self):
        return "{0}".format(
            self.adjList
        )

class DFGraph():
    def __init__(self, graph_dict=None, start_vertex='', count=''):
        if graph_dict is None:
            self.graph_dict={}
        else:
            self.graph_dict=graph_dict
        self.start_vertex=start_vertex
        if not count:
            self.count=len(self.graph_dict.keys())
        else:
            self.count=count

    def add_node(self, graphNode):
        if DEBUG:
            print 'add_node beg', graphNode

        self.count += 1
        node = str(self.count)

        graphNode.val = {}
        if self.count == 1:
            self.start_vertex = node

        for p in graphNode.parent:
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
            results.append(vertex)
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

    def find_calls(self, assign_node, assign_val):
        var_name=self.graph_dict[assign_node].tgt

        def find_calls_in_graph(c_node, visited=None, result=None):
            try:
                current_node=self.graph_dict[c_node]

                if result is None:
                    result=defaultdict(list)

                if visited is None:
                    visited=set()

                if c_node in visited:
                    return result
                else:
                    visited.add(c_node)


                if isinstance(current_node, AssignmentNode) and\
                                current_node.tgt != var_name:

                    if current_node.context:
                        if current_node.context.has_key('keyword_type') and \
                        current_node.context.has_key('keyword_val'):
                            for key, val in zip(current_node.context['keyword_type'],
                                                current_node.context['keyword_val']):
                                if key=='Call':
                                    result['other'].append(val)
                        if current_node.context.has_key('arg_type') and \
                        current_node.context.has_key('arg_val'):
                            for key, val in zip(current_node.context['arg_type'],
                                                current_node.context['arg_val']):
                                if key=='Name' and isinstance(val, list):
                                    for value in val:
                                        result['other'].append(value)

                    if var_name in current_node.val.keys():
                        result['other'].extend(current_node.src)
                    else:
                        return result
                        
                if isinstance(current_node, CallNode):
                    if hasattr(current_node,'val'):
                        if var_name in current_node.val.keys():
                            if assign_val in current_node.val[var_name]:
                                if current_node.src==var_name:
                                    result['object'].append(current_node)
                                else:
                                    if current_node.src in current_node.val.keys():
                                        for src in current_node.val[current_node.src]:
                                            result['other'].append(
                                                src+'.'+current_node.tgt
                                            )
                        else:
                            return result
                    else:
                        return result

                if isinstance(c_node, DeadNode) and \
                        c_node.src==var_name:
                    return result

                if current_node.adjList:
                    for adj_node_num in current_node.adjList:
                        result_node=find_calls_in_graph(adj_node_num, visited, None)
                        if result_node:
                            for k, v in result_node.items():
                                result[k].extend(v)
                    return result
            except:
                print "Error in ASTUtils",sys.exc_info()
                print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                return result
            
        return find_calls_in_graph(assign_node)

    def find_assignments_and_calls(self, object_name, lib):
        count=self.count

        while isinstance(self.graph_dict[str(count)], DeadNode):
            count-=1

        def find_assignments_and_calls_in_graph(c_node, visited=None, assignments=None, calls=None):
            current_node=self.graph_dict[c_node]

            if assignments is None:
                assignments=list()

            if calls is None:
                calls=defaultdict(list)
            if visited is None:
                visited=set()

            visited.add(c_node)

            if isinstance(current_node, AssignmentNode):
                if current_node.tgt == object_name:
                    if any(lib in src for src in current_node.src):
                        assignments.append(current_node)
                        return assignments, calls
                else:
                    calls['other'].extend(current_node.src)

                if current_node.context:
                    if current_node.context.has_key('keyword_type') and \
                    current_node.context.has_key('keyword_val'):
                        for key, val in zip(current_node.context['keyword_type'],
                                            current_node.context['keyword_val']):
                            if key=='Call':
                                calls['other'].append(val)
                    if current_node.context.has_key('arg_type') and \
                    current_node.context.has_key('arg_val'):
                        for key, val in zip(current_node.context['arg_type'],
                                            current_node.context['arg_val']):
                            if key=='Name' and isinstance(val, list):
                                for value in val:
                                    calls['other'].append(value)

            if isinstance(current_node, CallNode):
                if current_node.src == object_name:
                    if any(lib in src for src in current_node.val[object_name]):
                        calls['object'].append(current_node)
                else:
                    if current_node.src in current_node.val.keys():
                        for src in current_node.val[current_node.src]:
                            calls['other'].append(
                                src+'.'+current_node.tgt
                            )

            if current_node.parent:
                for adj_node_num in current_node.parent:
                    if adj_node_num not in visited and adj_node_num>0:
                        find_assignments_and_calls_in_graph(
                            adj_node_num, visited, assignments, calls)
                if not assignments and c_node>2:
                    find_assignments_and_calls_in_graph(
                        str(int(c_node)-1), visited, assignments, calls)
            return assignments, calls

        return find_assignments_and_calls_in_graph(str(count))

    def find_definitions_and_calls(self, object_name):
        count=self.count
        definitions=None
        assignment_nodes=None
        calls=None
        #while not isinstance(self.graph_dict[str(count)], CallNode):
                #and \
                #self.graph_dict[str(count)].tgt!='query_method':
        while isinstance(self.graph_dict[str(count)], DeadNode):
            count-=1
        print "find_definitions_and_calls"
        definitions=self.graph_dict[str(count)].val[object_name]

        def find_calls(c_node, definitions, visited=None, assign_nodes=None, calls=None):
            current_node=self.graph_dict[c_node]
            if calls is None:
                calls=defaultdict(list)

            if assign_nodes is None:
                assign_nodes=list()

            if visited is None:
                visited=set()

            visited.add(c_node)

            if isinstance(current_node, AssignmentNode):
                if current_node.tgt == object_name:
                    src=set(current_node.src)&set(definitions)
                    if src:
                        assign_nodes.append(current_node)
                        for val in src:
                            definitions.remove(val)

                else:
                    calls['other'].extend(current_node.src)

                if current_node.context:
                    if current_node.context.has_key('keyword_type') and \
                    current_node.context.has_key('keyword_val'):
                        for key, val in zip(current_node.context['keyword_type'],
                                            current_node.context['keyword_val']):
                            if key=='Call':
                                calls['other'].append(val)
                    if current_node.context.has_key('arg_type') and \
                    current_node.context.has_key('arg_val'):
                        for key, val in zip(current_node.context['arg_type'],
                                            current_node.context['arg_val']):
                            if key=='Name' and isinstance(val, list):
                                for value in val:
                                    calls['other'].append(value)

            if not definitions:
                return assign_nodes, calls

            if isinstance(current_node, CallNode):
                if current_node.src == object_name:
                    if not current_node.tgt=='query_method':
                        calls['object'].append(current_node.tgt)

                else:
                    if current_node.src in current_node.val.keys():
                        for src in current_node.val[current_node.src]:
                            calls['other'].append(
                                src+'.'+current_node.tgt
                            )

            if current_node.parent:
                for adj_node_num in current_node.parent:
                    if adj_node_num not in visited and adj_node_num>0:
                        ass_nodes, call_nodes=find_calls(
                            adj_node_num, definitions, visited, None, None)
                        if ass_nodes:
                            for node in ass_nodes:
                                for val in node.src:
                                    if val in definitions:
                                        definitions.remove(val)

                            assign_nodes.extend(ass_nodes)
                        if call_nodes:
                            for k, v in call_nodes.items():
                                calls[k].extend(v)
                        if not definitions:
                            return assign_nodes, calls

            return assign_nodes, calls

        if definitions:
            assignment_nodes, calls=find_calls(str(count), definitions[:])

        return assignment_nodes, calls


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

    @staticmethod
    def deserialize(graph_json):
        if DEBUG:
            print "in deserialize"

        df_graph=DFGraph(start_vertex=graph_json['start_vertex'],
                         count=int(graph_json['count']))
        graph={}
        for node, node_val in graph_json['graph_dict'].items():
            node_type=node_val['type']
            if node_type=='AssignmentNode':
                graph[node]=\
                    AssignmentNode(node_val['src'],
                                   node_val['tgt'],
                                   node_val['lineNum'],
                                   node_val['colOffset'],
                                   node_val['context'],
                                   node_val['adjList'],
                                   node_val['val'],)

            elif node_type=='CallNode':
                graph[node]=\
                    CallNode(node_val['src'],
                             node_val['tgt'],
                             node_val['lineNum'],
                             node_val['colOffset'],
                             node_val['adjList'],
                             node_val['val'])
            elif node_type=='DeadNode':
                graph[node]=\
                    DeadNode(node_val['src'],
                             node_val['adjList'],
                             node_val['val'])
            elif node_type=='DummyNode':
                graph[node]=\
                    DummyNode(node_val['adjList'],
                              node_val['val'])

        df_graph.graph_dict=graph
        return df_graph