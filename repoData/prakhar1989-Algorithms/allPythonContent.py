__FILENAME__ = bellman_ford
""" The bellman ford algorithm for calculating single source shortest
paths - CLRS style """
graph = { 
    's' : {'t':6, 'y':7},
    't' : {'x':5, 'z':-4, 'y':8 },
    'y' : {'z':9, 'x':-3},
    'z' : {'x':7, 's': 2},
    'x' : {'t':-2}
}

INF = float('inf')

dist = {}
predecessor = {}

def initialize_single_source(graph, s):
    for v in graph:
        dist[v] = INF
        predecessor[v] = None
    dist[s] = 0
    
def relax(graph, u, v):
    if dist[v] > dist[u] + graph[u][v]:
        dist[v] = dist[u] + graph[u][v]
        predecessor[v] = u

def bellman_ford(graph, s):
    initialize_single_source(graph, s)
    edges = [(u, v) for u in graph for v in graph[u].keys()]
    number_vertices = len(graph)
    for i in range(number_vertices-1):
        for (u, v) in edges:
            relax(graph, u, v)
    for (u, v) in edges:
        if dist[v] > dist[u] + graph[u][v]:
            return False # there exists a negative cycle
    return True

def get_distances(graph, s):
    if bellman_ford(graph, s):
        return dist
    return "Graph contains a negative cycle"

print get_distances(graph, 's')

########NEW FILE########
__FILENAME__ = dijkstra
from heapq import heappush, heappop
# graph = { 
#     's' : {'t':6, 'y':7},
#     't' : {'x':5, 'z':4, 'y':8 },
#     'y' : {'z':9, 'x':3},
#     'z' : {'x':7, 's': 2},
#     'x' : {'t':2}
# }

def read_graph(file):
    graph = dict()
    with open(file) as f:
        for l in f:
            (u, v, w) = l.split()
            if int(u) not in graph:
                graph[int(u)] = dict()
            graph[int(u)][int(v)] = int(w)
    return graph

inf = float('inf')
def dijkstra(graph, s):
    n = len(graph.keys())
    dist = dict()
    Q = list()
    
    for v in graph:
        dist[v] = inf
    dist[s] = 0
    
    heappush(Q, (dist[s], s))

    while Q:
        d, u = heappop(Q)
        if d < dist[u]:
            dist[u] = d
        for v in graph[u]:
            if dist[v] > dist[u] + graph[u][v]:
                dist[v] = dist[u] + graph[u][v]
                heappush(Q, (dist[v], v))
    return dist

graph = read_graph("graph.txt")
print dijkstra(graph, 1)

########NEW FILE########
__FILENAME__ = floyd
""" Floyd warshall in numpy and standard implementation """
from numpy import * 
inf = float('inf')
graph = [
    [0, 3, 8, inf, -4], 
    [inf, 0, inf, 1, 7], 
    [inf, 4, 0, inf, inf], 
    [2, inf, -5, 0, inf], 
    [inf, inf, inf, 6, 0]
]

def make_matrix(file, n):
    graph = [[inf for i in range(n)] for i in range(n)]
    with open(file) as f:
        for l in f:
           (i, j, w) = l.split() 
           graph[int(i)-1][int(j)-1] = int(w)
    return graph

def floyd_warshall(graph):
    n = len(graph)
    D = graph
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if i==j:
                    D[i][j] = 0
                else:
                    D[i][j] = min(D[i][j], D[i][k] + D[k][j])
    return D

def fastfloyd(D):
	_,n = D.shape
	for k in xrange(n):
		i2k = reshape(D[k,:],(1,n))
		k2j = reshape(D[:,k],(n,1))
		D = minimum(D,i2k+k2j)
	return D.min() if not any(D.diagonal() < 0) else None

def get_min_dist(D):
    if negative_cost_cycle(D):
        return "Negative cost cycle"
    return min(i for d in D for i in d)

def negative_cost_cycle(D):
    n = len(D)
    for i in range(n):
        if D[i][i] < 0:
            return True
    return False

# print get_min_dist(floyd_warshall(graph))
n = 1000
gr = make_matrix("g1.txt", n)
#D = floyd_warshall(gr)
print fastfloyd(array(gr))
# print get_min_dist(D)
# print D

########NEW FILE########
__FILENAME__ = johnsons_apsp
""" Johnson's algorithm for all-pairs shortest path problem.
Reimplemented Bellman-Ford and Dijkstra's for clarity"""
from heapq import heappush, heappop
from datetime import datetime
from copy import deepcopy
graph = { 
    'a' : {'b':-2},
    'b' : {'c':-1},
    'c' : {'x':2, 'a':4, 'y':-3},
    'z' : {'x':1, 'y':-4},
    'x' : {},
    'y' : {},
}

inf = float('inf')
dist = {}

def read_graph(file,n):
    graph = dict()
    with open(file) as f:
        for l in f:
            (u, v, w) = l.split()
            if int(u) not in graph:
                graph[int(u)] = dict()
            graph[int(u)][int(v)] = int(w)
    for i in range(n):
        if i not in graph:
            graph[i] = dict()
    return graph

def dijkstra(graph, s):
    n = len(graph.keys())
    dist = dict()
    Q = list()
    
    for v in graph:
        dist[v] = inf
    dist[s] = 0
    
    heappush(Q, (dist[s], s))

    while Q:
        d, u = heappop(Q)
        if d < dist[u]:
            dist[u] = d
        for v in graph[u]:
            if dist[v] > dist[u] + graph[u][v]:
                dist[v] = dist[u] + graph[u][v]
                heappush(Q, (dist[v], v))
    return dist

def initialize_single_source(graph, s):
    for v in graph:
        dist[v] = inf
    dist[s] = 0
    
def relax(graph, u, v):
    if dist[v] > dist[u] + graph[u][v]:
        dist[v] = dist[u] + graph[u][v]

def bellman_ford(graph, s):
    initialize_single_source(graph, s)
    edges = [(u, v) for u in graph for v in graph[u].keys()]
    number_vertices = len(graph)
    for i in range(number_vertices-1):
        for (u, v) in edges:
            relax(graph, u, v)
    for (u, v) in edges:
        if dist[v] > dist[u] + graph[u][v]:
            return False # there exists a negative cycle
    return True

def add_extra_node(graph):
    graph[0] = dict()
    for v in graph.keys():
        if v != 0:
            graph[0][v] = 0

def reweighting(graph_new):
    add_extra_node(graph_new)
    if not bellman_ford(graph_new, 0):
        # graph contains negative cycles
        return False
    for u in graph_new:
        for v in graph_new[u]:
            if u != 0:
                graph_new[u][v] += dist[u] - dist[v]
    del graph_new[0]
    return graph_new

def johnsons(graph_new):
    graph = reweighting(graph_new)
    if not graph:
        return False
    final_distances = {}
    for u in graph:
        final_distances[u] = dijkstra(graph, u)

    for u in final_distances:
        for v in final_distances[u]:
            final_distances[u][v] += dist[v] - dist[u]
    return final_distances
            
def compute_min(final_distances):
    return min(final_distances[u][v] for u in final_distances for v in final_distances[u])

if __name__ == "__main__":
    # graph = read_graph("graph.txt", 1000)
    graph_new = deepcopy(graph)
    t1 = datetime.utcnow()
    final_distances =  johnsons(graph_new)
    if not final_distances:
        print "Negative cycle"
    else:
        print compute_min(final_distances)
    print datetime.utcnow() - t1

########NEW FILE########
__FILENAME__ = kp
def read_data(data):
    weights = []
    values = []
    for d in data:
        weights.append(int(d.split()[1]))
        values.append(int(d.split()[0]))
    return (weights, values)

def knapsack_rep(weights, values, W):
    """ knapsack with repetition """
    k = [0]*(W + 1)
    for w in range(1, W+1):
        k[w] = max([k[w-i] + values[i] if weights[i]<=w else 0 for i in range(len(weights))])
    return k[-1]

def knapsack(weights, values, W):
    """ knapsack without repetition. Takes O(w) space 
    Reference - http://books.google.co.in/books?id=u5DB7gck08YC&printsec=frontcover&dq=knapsack+problem&hl=en&sa=X&ei=1sbmUJSwDYWGrAeLi4GgCQ&ved=0CDUQ6AEwAA#v=onepage&q&f=true
    """
    optimal_vals = [0]*(W+1)
    for j in range(0, len(weights)):
        for w in range(W, weights[j]-1, -1):
            if optimal_vals[w-weights[j]] + values[j] > optimal_vals[w]:
                optimal_vals[w] = optimal_vals[w-weights[j]] + values[j]
    return optimal_vals[-1]

with open("kpdata2.txt") as f:
    (weights, values) = read_data(f)
# print knapsack_rep(weights, values, 10000)
#print knapsack(weights, values, 2000000)

########NEW FILE########
__FILENAME__ = longest_subsequence
def longest_seq(seq):
    """ returns the longest increasing subseqence 
    in a sequence """
    count = [1] * len(seq)
    prev = [0] * len(seq)
    for i in range(1, len(seq)):
        dist = []
        temp_prev = {}
        for j in range(i):
            if seq[j] < seq[i]:
                dist.append(count[j])
                temp_prev[count[j]] = j
            else:
                temp_prev[0] = j
                dist.append(0)
        count[i] = 1 + max(dist)
        prev[i] = temp_prev[max(dist)]
    
    # path
    path = [seq[prev.index(max(prev))]]
    i = prev.index(max(prev))
    while i>1:
        path.append(seq[prev[i]])
        i = prev[i]
    return max(count), path[::-1]

if __name__ == "__main__":
    seq = [5, 2, 8, 10, 3, 6, 9, 7]
    seq2 = [0, 8, 3, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]
    print longest_seq(seq2)


########NEW FILE########
__FILENAME__ = max_subsquare_matrix
""" Given a binary matrix, find out the maximum size square sub-matrix with all 1s.
For example, consider the below binary matrix.
   0  1  1  0  1 
   1  1  0  1  0 
   0  1  1  1  0
   1  1  1  1  0
   1  1  1  1  1
   0  0  0  0  0
The maximum square sub-matrix with all set bits is
    1  1  1
    1  1  1
    1  1  1
"""
from copy import deepcopy
matrix = [[0,1,1,0,1],[1,1,0,1,0],[0,1,1,1,0],
          [1,1,1,1,0],[1,1,1,1,1],[0,0,0,0,0]]

def find_sub_matrix_size(matrix):
    copy_matrix = deepcopy(matrix)
    for i in range(1, len(matrix)):
        for j in range(1, len(matrix[0])):
            if matrix[i][j] == 1:
                copy_matrix[i][j] = min(copy_matrix[i-1][j], 
                                    copy_matrix[i][j-1],
                                    copy_matrix[i-1][j-1]) + 1
            else:
                copy_matrix[i][j] = 0
    return max([item for rows in copy_matrix for item in rows])

print find_sub_matrix_size(matrix)

########NEW FILE########
__FILENAME__ = clustering
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
from graph import graph
from union_find.unionfind import UnionFind

data = """1 2 6808
1 3 5250
1 4 74
1 5 3659
1 6 8931
1 7 1273
1 8 7545
1 9 879
1 10 7924
1 11 7710
1 12 4441
1 13 8166
1 14 4493
1 15 3043
1 16 7988
1 17 2504
1 18 2328
1 19 1730
1 20 8841
2 3 4902
2 4 812
2 5 6617
2 6 6892
2 7 8672
2 8 1729
2 9 6672
2 10 1662
2 11 7046
2 12 3121
2 13 241
2 14 7159
2 15 9454
2 16 9628
2 17 5351
2 18 3712
2 19 5564
2 20 9595
3 4 3782
3 5 1952
3 6 9231
3 7 3322
3 8 3214
3 9 5129
3 10 1951
3 11 8601
3 12 8960
3 13 9755
3 14 9993
3 15 5195
3 16 3331
3 17 8633
3 18 3560
3 19 8778
3 20 7780
4 5 5000
4 6 4521
4 7 4516
4 8 2578
4 9 9923
4 10 7143
4 11 3981
4 12 5882
4 13 6886
4 14 31
4 15 6326
4 16 2437
4 17 6995
4 18 3946
4 19 2603
4 20 3234
5 6 8696
5 7 6896
5 8 5665
5 9 5601
5 10 5119
5 11 5118
5 12 3724
5 13 1618
5 14 3755
5 15 9569
5 16 8588
5 17 4576
5 18 4914
5 19 8123
5 20 4158
6 7 2495
6 8 3894
6 9 3065
6 10 4564
6 11 5430
6 12 5502
6 13 6873
6 14 6941
6 15 8054
6 16 4330
6 17 2233
6 18 2281
6 19 9360
6 20 5475
7 8 2739
7 9 4442
7 10 4843
7 11 8503
7 12 5466
7 13 5370
7 14 8012
7 15 3909
7 16 3503
7 17 1844
7 18 5374
7 19 7081
7 20 9837
8 9 3060
8 10 5421
8 11 5098
8 12 4080
8 13 3019
8 14 8318
8 15 9158
8 16 2031
8 17 722
8 18 4052
8 19 1072
8 20 9529
9 10 7569
9 11 563
9 12 5705
9 13 9597
9 14 4813
9 15 6965
9 16 8810
9 17 5046
9 18 17
9 19 1710
9 20 2262
10 11 3444
10 12 370
10 13 8675
10 14 5780
10 15 6209
10 16 2586
10 17 9086
10 18 4323
10 19 1212
10 20 79
11 12 1975
11 13 1665
11 14 3396
11 15 9439
11 16 594
11 17 5821
11 18 6006
11 19 836
11 20 2450
12 13 6821
12 14 5835
12 15 8470
12 16 3141
12 17 9413
12 18 760
12 19 3568
12 20 7424
13 14 4357
13 15 6374
13 16 7456
13 17 6025
13 18 9458
13 19 3064
13 20 9874
14 15 9946
14 16 6500
14 17 2476
14 18 4187
14 19 6686
14 20 9103
15 16 8910
15 17 5182
15 18 4761
15 19 8506
15 20 4676
16 17 881
16 18 4769
16 19 2903
16 20 66
17 18 2747
17 19 7119
17 20 2874
18 19 6302
18 20 7382
19 20 1143
"""

def max_k_clustering(gr, k):
    sorted_edges = sorted(gr.get_edge_weights())
    uf = UnionFind()
    #initialize each node as its cluster
    for n in gr.nodes(): 
        uf.insert(n)
    for (w, (u, v)) in sorted_edges:
        if uf.count_groups() <= k: 
            return uf.get_sets()
        if uf.get_leader(u) != uf.get_leader(v):
            uf.make_union(uf.get_leader(u), uf.get_leader(v))
    
def compute_spacing(c1, c2):
    min = float('inf')
    for n in c1:
        for v in c2:
            cost = gr.get_edge_weight((n, v))
            if cost < min:
                min = cost
    return min

def get_max_spacing(clusters):
    min = float('inf')
    for u in clusters:
        for v in clusters:
            if u!= v:
                spacing = compute_spacing(u,v)
                if spacing < min:
                    min = spacing
    return min

if __name__ == "__main__":
    edges = [l.split() for l in data.splitlines()]
    gr = graph()

    for (u, v, w) in edges:
        if u not in gr.nodes():
            gr.add_node(u)
        if v not in gr.nodes():
            gr.add_node(v)
        gr.add_edge((u, v), int(w))

    print "Min Spacing - %s " % (get_max_spacing(max_k_clustering(gr, 4)))

########NEW FILE########
__FILENAME__ = digraph
from graph import graph
from copy import deepcopy
class digraph(graph):
    """
    Directed Graph class - made of nodes and edges

    methods: add_edge, add_edges, add_node, add_nodes, has_node,
    has_edge, nodes, edges, neighbors, del_node, del_edge, node_order,
    set_edge_weight, get_edge_weight, 
    """

    DEFAULT_WEIGHT = 1
    DIRECTED = True

    def __init__(self):
        self.node_neighbors = {}

    def __str__(self):
        return "Directed Graph \nNodes: %s \nEdges: %s" % (self.nodes(), self.edges())

    def add_edge(self, edge, wt=1, label=""):
        """
        Add an edge to the graph connecting two nodes.
        An edge, here, is a pair of node like C(m, n) or a tuple
        with m as head and n as tail :  m -> n
        """
        u, v = edge
        if (v not in self.node_neighbors[u]):
            self.node_neighbors[u][v] = wt
        else:
            raise Exception("Edge (%s, %s) already added in the graph" % (u, v))

    def del_edge(self, edge):
        """
        Deletes an edge from a graph. An edge, here, is a pair like
        C(m,n) or a tuple
        """
        u, v = edge
        if not self.has_edge(edge):
            raise Exception("Edge (%s, %s) not an existing edge" % (u, v))
        del self.node_neighbors[u][v]

    def del_node(self, node):
        """
        Deletes a node from a graph
        """
        for each in list(self.neighbors(node)):
            if (each != node):
                self.del_edge((node, each))
        for n in self.nodes():
            if self.has_edge((n, node)):
                self.del_edge((n, node))
        del(self.node_neighbors[node])

    def get_transpose(self):
        """ Returns the transpose of the graph
        with edges reversed and nodes same """
        digr = deepcopy(self)
        for (u, v) in self.edges():
            digr.del_edge((u, v))
            digr.add_edge((v, u))
        return digr

########NEW FILE########
__FILENAME__ = graph
class graph(object):
    """
    Graph class - made of nodes and edges

    methods: add_edge, add_edges, add_node, add_nodes, has_node,
    has_edge, nodes, edges, neighbors, del_node, del_edge, node_order,
    set_edge_weight, get_edge_weight, 
    """

    DEFAULT_WEIGHT = 1
    DIRECTED = False

    def __init__(self):
        self.node_neighbors = {}

    def __str__(self):
        return "Undirected Graph \nNodes: %s \nEdges: %s" % (self.nodes(), self.edges())

    def add_nodes(self, nodes):
        """
        Takes a list of nodes as input and adds these to a graph
        """
        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        """
        Adds a node to the graph
        """
        if node not in self.node_neighbors:
            self.node_neighbors[node] = {}
        else:
            raise Exception("Node %s is already in graph" % node)

    def has_node(self, node):
        """
        Returns boolean to indicate whether a node exists in the graph
        """
        return node in self.node_neighbors

    def add_edge(self, edge, wt=1, label=""):
        """
        Add an edge to the graph connecting two nodes.
        An edge, here, is a pair of node like C(m, n) or a tuple
        """
        u, v = edge
        if (v not in self.node_neighbors[u] and u not in self.node_neighbors[v]):
            self.node_neighbors[u][v] = wt
            if (u!=v):
                self.node_neighbors[v][u] = wt
        else:
            raise Exception("Edge (%s, %s) already added in the graph" % (u, v))

    def add_edges(self, edges):
        """ Adds multiple edges in one go. Edges, here, is a list of
        tuples"""
        for edge in edges:
            self.add_edge(edge)

    def nodes(self):
        """
        Returns a list of nodes in the graph
        """
        return list(self.node_neighbors.keys())

    def has_edge(self, edge):
        """
        Returns a boolean to indicate whether an edge exists in the
        graph. An edge, here, is a pair of node like C(m, n) or a tuple
        """
        u, v = edge
        if v not in self.node_neighbors[u]:
            return False
        return True

    def neighbors(self, node):
        """
        Returns a list of neighbors for a node
        """
        if not self.has_node(node):
            raise "Node %s not in graph" % node
        return self.node_neighbors[node].keys()

    def del_node(self, node):
        """
        Deletes a node from a graph
        """
        for each in list(self.neighbors(node)):
            if (each != node):
                self.del_edge((each, node))
        del(self.node_neighbors[node])

    def del_edge(self, edge):
        """
        Deletes an edge from a graph. An edge, here, is a pair like
        C(m,n) or a tuple
        """
        u, v = edge
        if not self.has_edge(edge):
            raise Exception("Edge (%s, %s) not an existing edge" % (u, v))
        del self.node_neighbors[u][v]
        if (u!=v):
            del self.node_neighbors[v][u]

    def node_order(self, node):
        """
        Return the order or degree of a node
        """
        return len(self.neighbors(node))


    def edges(self):
        """
        Returns a list of edges in the graph
        """
        edge_list = []
        for node in self.nodes():
            for each in self.neighbors(node):
                edge_list.append((node, each))
        return edge_list

    # Methods for setting properties on nodes and edges
    def set_edge_weight(self, edge, wt):
        """Set the weight of the edge """
        u, v = edge
        self.node_neighbors[u][v] = wt
        if u != v:
            self.node_neighbors[v][u] = wt

    def get_edge_weight(self, edge):
        """Returns the weight of an edge """
        u, v = edge
        if not self.has_edge((u, v)):
            raise Exception("%s not an existing edge" % edge)
        return self.node_neighbors[u].get(v, self.DEFAULT_WEIGHT)

    def get_edge_weights(self):
        """ Returns a list of all edges with their weights """
        edge_list = []
        unique_list = {}
        for u in self.nodes():
            for v in self.neighbors(u):
                if not  unique_list.get(v) or u not in unique_list.get(v):
                    edge_list.append((self.node_neighbors[u][v], (u, v)))
                    if u not in unique_list:
                        unique_list[u] = [v]
                    else:
                        unique_list[u].append(v)
        return edge_list

########NEW FILE########
__FILENAME__ = graph_algorithms
from collections import deque
from copy import deepcopy
from union_find.unionfind import UnionFind
import heapq

def BFS(gr, s):
    """ Breadth first search 
    Returns a list of nodes that are "findable" from s """
    if not gr.has_node(s):
        raise Exception("Node %s not in graph" % s)
    nodes_explored = [s]
    q = deque([s])
    while len(q)!=0:
        node = q.popleft()
        for each in gr.neighbors(node):
            if each not in nodes_explored:
                nodes_explored.append(each)
                q.append(each)
    return nodes_explored

def shortest_hops(gr, s):
    """ Finds the shortest number of hops required
    to reach a node from s. Returns a dict with mapping:
    destination node from s -> no. of hops
    """
    if not gr.has_node(s):
        raise Exception("Node %s is not in graph" % s)
    else:
        dist = {}
        q = deque([s])
        nodes_explored = [s]
        for n in gr.nodes():
            if n == s: dist[n] = 0
            else: dist[n] = float('inf')
        while len(q) != 0:
            node = q.popleft()
            for each in gr.neighbors(node):
                if each not in nodes_explored:
                    nodes_explored.append(each)
                    q.append(each)
                    dist[each] = dist[node] + 1
        return dist

def undirected_connected_components(gr):
    """ Returns a list of connected components
    in an undirected graph """
    if gr.DIRECTED:
        raise Exception("This method works only with a undirected graph")
    explored = []
    con_components = []
    for node in gr.nodes():
        if node not in explored:
            reachable_nodes = BFS(gr, node)
            con_components.append(reachable_nodes)
            explored += reachable_nodes
    return con_components

def DFS(gr, s):
    """ Depth first search wrapper """
    path = []
    depth_first_search(gr, s, path)
    return path

def depth_first_search(gr, s, path):
    """ Depth first search 
    Returns a list of nodes "findable" from s """
    if s in path: return False
    path.append(s)
    for each in gr.neighbors(s):
        if each not in path:
            depth_first_search(gr, each, path)

def topological_ordering(digr_ori):
    """ Returns a topological ordering for a 
    acyclic directed graph """
    if not digr_ori.DIRECTED:
        raise Exception("%s is not a directed graph" % digr)
    digr = deepcopy(digr_ori)
    ordering = []
    n = len(digr.nodes())
    while n > 0:
        sink_node = find_sink_node(digr)
        ordering.append((sink_node, n))
        digr.del_node(sink_node)
        n -= 1
    return ordering

def find_sink_node(digr):
    """ Finds a sink node (node with all incoming arcs) 
    in the directed graph. Valid for a acyclic graph only """
    # first node is taken as a default
    node = digr.nodes()[0]
    while digr.neighbors(node):
        node = digr.neighbors(node)[0]
    return node

def directed_connected_components(digr):
    """ Returns a list of strongly connected components
    in a directed graph using Kosaraju's two pass algorithm """
    if not digr.DIRECTED:
        raise Exception("%s is not a directed graph" % digr)
    finishing_times = DFS_loop(digr.get_transpose())
    # use finishing_times in descending order
    nodes_explored, connected_components = [], []
    for node in finishing_times[::-1]:
        component = []
        outer_dfs(digr, node, nodes_explored, component)
        if component:
            nodes_explored += component
            connected_components.append(component)
    return connected_components

def outer_dfs(digr, node, nodes_explored, path):
    if node in path or node in nodes_explored: 
        return False
    path.append(node)
    for each in digr.neighbors(node):
        if each not in path or each not in nodes_explored:
            outer_dfs(digr, each, nodes_explored, path)

def DFS_loop(digr):
    """ Core DFS loop used to find strongly connected components
    in a directed graph """
    node_explored = [] # list for keeping track of nodes explored
    finishing_times = [] # list for adding nodes based on their finishing times
    for node in digr.nodes():
        if node not in node_explored:
            leader_node = node
            inner_DFS(digr, node, node_explored, finishing_times)
    return finishing_times 

def inner_DFS(digr, node, node_explored, finishing_times):
    """ Inner DFS used in DFS loop method """
    node_explored.append(node) # mark explored
    for each in digr.neighbors(node):
        if each not in node_explored:
            inner_DFS(digr, each, node_explored, finishing_times)
    global finishing_counter
    # adds nodes based on increasing order of finishing times
    finishing_times.append(node) 

def shortest_path(digr, s):
    """ Finds the shortest path from s to every other vertex findable
    from s using Dijkstra's algorithm in O(mlogn) time. Uses heaps
    for super fast implementation """
    nodes_explored = [s]
    nodes_unexplored = DFS(digr, s)[1:] # all accessible nodes from s
    dist = {s:0}
    node_heap = []

    for n in nodes_unexplored:
        min = compute_min_dist(digr, n, nodes_explored, dist)
        heapq.heappush(node_heap, (min, n))

    while len(node_heap) > 0:
        min_dist, nearest_node = heapq.heappop(node_heap)
        dist[nearest_node] = min_dist
        nodes_explored.append(nearest_node)
        nodes_unexplored.remove(nearest_node)

        # recompute keys for just popped node
        for v in digr.neighbors(nearest_node):
            if v in nodes_unexplored:
                for i in range(len(node_heap)):
                    if node_heap[i][1] == v:
                        node_heap[i] = (compute_min_dist(digr, v, nodes_explored, dist), v)
                        heapq.heapify(node_heap)

    return dist

def compute_min_dist(digr, n, nodes_explored, dist):
    """ Computes the min dist of node n from a set of
    nodes explored in digr, using dist dict. Used in shortest path """
    min = float('inf')
    for v in nodes_explored:
        if digr.has_edge((v, n)):
            d = dist[v] + digr.get_edge_weight((v, n))
            if d < min: min = d
    return min

def minimum_spanning_tree(gr):
    """ Uses prim's algorithm to return the minimum 
    cost spanning tree in a undirected connected graph.
    Works only with undirected and connected graphs """
    s = gr.nodes()[0] 
    nodes_explored = [s]
    nodes_unexplored = gr.nodes()
    nodes_unexplored.remove(s)
    min_cost, node_heap = 0, []

    #computes the key for each vertex in unexplored
    for n in nodes_unexplored:
        min = compute_key(gr, n, nodes_explored)
        heapq.heappush(node_heap, (min, n))

    while len(nodes_unexplored) > 0:
        # adds the cheapest to "explored"
        node_cost, min_node = heapq.heappop(node_heap)
        min_cost += node_cost
        nodes_explored.append(min_node)
        nodes_unexplored.remove(min_node)

        # recompute keys for neighbors of deleted node
        for v in gr.neighbors(min_node):
            if v in nodes_unexplored:
                for i in range(len(node_heap)):
                    if node_heap[i][1] == v:
                        node_heap[i] = (compute_key(gr, v, nodes_explored), v)
                        heapq.heapify(node_heap)
    return min_cost

def compute_key(gr, n, nodes_explored):
    """ computes minimum key for node n from a set of nodes_explored
    in graph gr. Used in Prim's implementation """
    min = float('inf')
    for v in gr.neighbors(n):
        if v in nodes_explored:
            w = gr.get_edge_weight((n, v))
            if w < min: min = w
    return min

def kruskal_MST(gr):
    """ computes minimum cost spanning tree in a undirected, 
    connected graph using Kruskal's MST. Uses union-find data structure
    for running times of O(mlogn) """
    sorted_edges = sorted(gr.get_edge_weights())
    uf = UnionFind()
    min_cost = 0
    for (w, (u, v)) in sorted_edges:
        if (not uf.get_leader(u) and not uf.get_leader(v)) \
                or (uf.get_leader(u) != uf.get_leader(v)):
            uf.insert(u, v)
            min_cost += w
    return min_cost

def max_k_clustering(gr, k):
    sorted_edges = sorted(gr.get_edge_weights())
    uf = UnionFind()
    #initialize each node as its cluster
    for n in gr.nodes(): 
        uf.insert(n)
    for (w, (u, v)) in sorted_edges:
        if uf.count_groups() <= k: 
            return uf.get_sets()
        if uf.get_leader(u) != uf.get_leader(v):
            uf.make_union(uf.get_leader(u), uf.get_leader(v))
    
def compute_spacing(c1, c2):
    min = float('inf')
    for n in c1:
        for v in c2:
            cost = gr.get_edge_weight((n, v))
            if cost < min:
                min = cost
    return min

def get_max_spacing(clusters):
    min = float('inf')
    for u in clusters:
        for v in clusters:
            if u!= v:
                spacing = compute_spacing(u,v)
                if spacing < min:
                    min = spacing
    return min

########NEW FILE########
__FILENAME__ = heapsort
from minheap import minheap
import random

def heapsort(nums):
    h = minheap(nums)
    return [h.heappop() for i in range(h.max_elements())]

if __name__ == "__main__":
    a = [random.choice(range(100)) for i in range(40)]
    print heapsort(a) == sorted(a)

########NEW FILE########
__FILENAME__ = maxheap
from minheap import minheap
class maxheap(minheap):
    """
    Heap class - made of keys and items
    methods: build_heap, heappush, heappop
    """

    MAX_HEAP = True

    def __str__(self):
        return "Max-heap with %s items" % (len(self.heap))

    def heapify(self, i):
        l = self.leftchild(i)
        r = self.rightchild(i)
        largest = i
        if l < self.max_elements() and self.heap[l] > self.heap[largest]:
            largest = l
        if r < self.max_elements() and self.heap[r] > self.heap[largest]:
            largest = r
        if largest != i:
            self.heap[i], self.heap[largest] = self.heap[largest], self.heap[i]
            self.heapify(largest)

    def heappush(self, x):
        """ Adds a new item x in the heap"""
        i = len(self.heap)
        self.heap.append(x)
        parent = self.parent(i)
        while parent != [] and self.heap[i] > self.heap[parent]:
            self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]
            i = parent
            parent = self.parent(i)

########NEW FILE########
__FILENAME__ = minheap
import math
class minheap(object):
    """
    Heap class - made of keys and items
    methods: build_heap, heappush, heappop
    """

    MIN_HEAP = True

    def __init__(self, nums=None):
        self.heap = []
        if nums:
            self.build_heap(nums)
    
    def __str__(self):
        return "Min-heap with %s items" % (len(self.heap))

    def max_elements(self):
        return len(self.heap)

    def height(self):
        return math.ceil(math.log(len(self.heap))/math.log(2))

    def is_leaf(self, i):
        """ returns True if i is a leaf node """
        return i > int(math.ceil( (len(self.heap)- 2) / 2))

    def parent(self, i):
        if i == 0:
            return []
        elif i % 2 != 0: # odd
            return (i-1)/2
        return int(math.floor((i-1)/2))

    def leftchild(self, i):
        if not self.is_leaf(i):
            return 2*i+1
        return []

    def rightchild(self, i):
        if not self.is_leaf(i):
            return 2*i+2
        return []

    def heapify(self, i):
        l = self.leftchild(i)
        r = self.rightchild(i)
        smallest = i
        if l < self.max_elements() and self.heap[l] < self.heap[smallest]:
            smallest = l
        if r < self.max_elements() and self.heap[r] < self.heap[smallest]:
            smallest = r
        if smallest != i:
            self.heap[i], self.heap[smallest] = self.heap[smallest], self.heap[i]
            self.heapify(smallest)

    def build_heap(self, elem):
        """ transforms a list of elements into a heap
        in linear time """
        self.heap = elem[:]
        last_leaf = int(math.ceil( (len(self.heap)- 2) / 2))
        for i in range(last_leaf, -1, -1):
            self.heapify(i)
        

    def heappush(self, x):
        """ Adds a new item x in the heap"""
        i = len(self.heap)
        self.heap.append(x)
        parent = self.parent(i)
        while parent != [] and self.heap[i] < self.heap[parent]:
            self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]
            i = parent
            parent = self.parent(i)

    def heappop(self):
        """ extracts the root of the heap, min or max
        depending on the kind of heap"""
        if self.max_elements():
            self.heap[0], self.heap[-1] = self.heap[-1], self.heap[0]
            pop = self.heap.pop()
            self.heapify(0)
            return pop
        raise Exception("Heap is empty")

########NEW FILE########
__FILENAME__ = stack-adt
class Stack(object):
    """ A simple stack ADT with top as the end of a list """
    def __init__(self):
        self.items = []

    def __str__(self):
        return ("Stack of size: %d" % len(self.items))

    def isEmpty(self):
        return len(self.items) == 0

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def top(self):
        if self.isEmpty(): return None
        return self.items[len(self.items)-1]

def string_reverse(s):
    stack = Stack()
    rev = []
    for c in s: stack.push(c)
    while not stack.isEmpty():
        rev.append(stack.pop())
    return "".join(rev)

def match_paren(parens):
    """ returns true or false if parenthesis
    expression passed is matching"""
    stack = Stack()
    for b in parens:
        if b == "(":
            stack.push(1)
        else: # b == ")"
            if not stack.isEmpty():
                stack.pop()
            else:
                return False
    return stack.isEmpty()

def infix_to_postfix(infixexpr):
    prec = { '+': 2, '-': 2, '*': 3, '/': 3,'(': 1 } # denoting precedence
    operator_stack = Stack()
    operators = "+-*/()"
    output_list = []
    for token in infixexpr.split():
        if token not in operators:
            output_list.append(token)
        elif token == "(":
            operator_stack.push("(")
        elif token == ")":
            topToken = operator_stack.pop()
            while topToken != "(":
                output_list.append(topToken)
                topToken = operator_stack.pop()
        else: # an operator
            while (not operator_stack.isEmpty()) and \
                (prec[operator_stack.top()] >= prec[token]):
                output_list.append(operator_stack.pop())
            operator_stack.push(token)

    # tokens exhausted - empty out the stack
    while not operator_stack.isEmpty():
        output_list.append(operator_stack.pop())
    return " ".join(output_list)


if __name__ == "__main__":
    expr = ["A * B + C * D", "( A + B ) * C - ( D - E ) * ( F + G )"]
    for e in expr:
        print infix_to_postfix(e)

########NEW FILE########
__FILENAME__ = kandane
# The maximum subarray problem is the task of finding the contiguous subarray within a one-dimensional array of numbers which has the largest sum. Kadane's algorithm finds the maximum subarray sum in linear time.
# For example, in the array { -1, 3, -5, 4, 6, -1, 2, -7, 13, -3 }, the maximum subarray sum is 17 (from the highlighted subarray).

def find_max_subarray(numbers):
    max_till_here = [0]*len(numbers)
    max_value = 0
    for i in range(len(numbers)):
        max_till_here[i] = max(numbers[i], max_till_here[i-1] + numbers[i])
        max_value = max(max_value, max_till_here[i])
    return max_value


def find_max_subarray2(numbers):
    """ shorter version """
    max_till_here = [numbers[0]]
    for n in numbers:
        max_till_here.append(max(n, max_till_here[-1] + n))
    return max(max_till_here)

print find_max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) # 6
print find_max_subarray([ -1, 3, -5, 4, 6, -1, 2, -7, 13, -3 ]) # 17

########NEW FILE########
__FILENAME__ = max_area_histogram
"""
Find the maximum rectangle (in terms of area) under a histogram in linear time.
I mean the area of largest rectangle that fits entirely in the Histogram.


http://tech-queries.blogspot.in/2011/03/maximum-area-rectangle-in-histogram.html
http://stackoverflow.com/questions/4311694/maximize-the-rectangular-area-under-histogram
http://tech-queries.blogspot.in/2011/09/find-largest-sub-matrix-with-all-1s-not.html
http://stackoverflow.com/questions/3806520/finding-maximum-size-sub-matrix-of-all-1s-in-a-matrix-having-1s-and-0s

"""

# hist represented as ith bar has height h(i) 
histogram = [6, 4, 2, 1, 3, 4, 5, 2, 6]

"""
steps -
1. Find Li - no. of adjacent bars to the left that have h >= h(i)
2. Find Ri - no. of adjacent bars to the right that have h >= h(i)
3. Area = h(i) * (L(i) + R(i) + 1)
4. compute max area
"""

def get_L(hist):
    L = [0]*len(hist)
    for i in range(1, len(hist)):
        if hist[i] > hist[i-1]:
            L[i] = i
        else:
            L[i] = L[i-1]
    return L

print get_L(histogram)

def find_Ri(hist, i):
    right_edge = 0
    for j in range(i+1, len(hist)):
        if hist[j] >= hist[i]:
            right_edge += 1
        else:
            return right_edge
    return right_edge

def get_area(hist, i):
    return hist[i] * (find_Li(hist, i) + find_Ri(hist, i) + 1)


def get_max_area(hist):
    max_area = 0
    for i in range(len(hist)):
        area = get_area(hist, i)
        if area > max_area:
            max_area = area
    return max_area

def max_rectangle_area(histogram):
    """Find the area of the largest rectangle that fits entirely under
    the histogram.

    """
    stack = []
    top = lambda: stack[-1]
    max_area = 0
    pos = 0 # current position in the histogram
    for pos, height in enumerate(histogram):
        start = pos # position where rectangle starts
        while True:
            if not stack or height > top().height:
                stack.append(Info(start, height)) # push
            elif stack and height < top().height:
                max_area = max(max_area, top().height*(pos-top().start))
                start, _ = stack.pop()
                continue
            break # height == top().height goes here

    pos += 1
    for start, height in stack:
        max_area = max(max_area, height*(pos-start))

    return max_area

print max_rectangle_area(histogram)

########NEW FILE########
__FILENAME__ = countinversion
def sort_and_count(a):
    """ counts the number of inversions
    in an array and returns the count and the
    sorted array in O(nlogn) time

    >>> sort_and_count([1, 3, 5, 2, 4, 6])
    ([1, 2, 3, 4, 5, 6], 3)
    """

    if len(a) == 1: return (a, 0)
    (b, x) = sort_and_count(a[:(len(a)/2)])
    (c, y) = sort_and_count(a[(len(a)/2):])
    (d, z) = merge_and_count_inv(b, c)
    return (d, x + y + z)

def merge_and_count_inv(b, c):
    d = []
    count = 0
    i, j = 0,0
    while i < len(b) and j < len(c):
        if b[i] <= c[j]:
            d.append(b[i])
            i += 1
        else: 
            d.append(c[j])
            j += 1
            # this works because all elements in b < c
            count += len(b[i:])
    if b[i:]: d += b[i:]
    if c[j:]: d += c[j:]
    return d, count

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose = True)

########NEW FILE########
__FILENAME__ = karatsuba
def karatsuba(x, y, b=10):
    """ returns product of x, y. Uses base b
    in karatsuba algorithm
    Gives running time of O(n^1.585) as opposed to
    O(n^2) of naive multiplication
    >>> karatsuba(1234223123412323, 1234534213423333123)
    1523690672850721578619752112274729L
    """
    nx, ny = len(str(x))/2, len(str(y))/2
    if x < 1000 or y < 1000: return x * y
    m = nx if nx < ny else ny
    x1 = x / (b**m)
    x0 = x % (x1 * (b**m))
    y1 = y / (b**m)
    y0 = y % (y1 * (b**m))
    z1 = karatsuba(x1,y1,b)
    z3 = karatsuba(x0,y0,b)
    z2 = karatsuba(x1 + x0, y1 + y0, b) - z1 - z3
    return (b**(2*m))*z1 + (b**m)*z2 + z3

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)

########NEW FILE########
__FILENAME__ = quicksort
from random import randint
def qsort(a, start, end):
    """ quicksort in O(nlogn) and no extra
    memory. In place implementation
    >>> from random import sample
    >>> rand_list = [sample(range(100), 10) for j in range(10)]
    >>> sortedresult = [sorted(r) for r in rand_list]
    >>> for r in rand_list: qsort(r, 0, len(r)-1)
    >>> result = [sortedresult[i] == rand_list[i] for i in range(len(rand_list))]
    >>> print sum(result)
    10
    """
    if start < end:
        p = choosepivot(start, end)
        if p != start:
            a[p], a[start] = a[start], a[p]
        equal = partition(a, start, end)
        qsort(a, start, equal-1)
        qsort(a, equal+1, end)

def partition(a, l, r):
    """ partition array with pivot at a[0]
    in the array a[l...r] that returns the
    index of pivot element
    """
    pivot, i = a[l], l+1
    for j in range(l+1, r+1):
        if a[j] <= pivot:
            a[i],a[j] = a[j],a[i]
            i += 1
    # swap pivot to its correct place
    a[l], a[i-1] = a[i-1], a[l]
    return i-1

def choosepivot(s, e):
    return randint(s,e)

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)

########NEW FILE########
__FILENAME__ = scheduling
""" data of the form -> wi, li 
(wi -> wieght of job i, li -> length of job i)
"""
test_data = """8 50
74 59
31 73
45 79
24 10
41 66
93 43
88 4
28 30
41 13
4 70
10 58
61 34
100 79
17 36
98 27
13 68
11 34
"""

def get_times(data):
    lines = [l for l in data.splitlines()]
    jobs = ((int(l.split()[0]), int(l.split()[1])) for l in lines)
    times = ((j[0]/float(j[1]), j[0], j[1]) for j in jobs)
    length, total_completion_time = 0,0
    for job in sorted(times, reverse=True):
        length += job[2]
        total_completion_time += job[1]*length
    print total_completion_time

get_times(test_data) # ans -> 164566

########NEW FILE########
__FILENAME__ = selection_deter
# selection problem solved deterministically
from sorting import mergesort
def median_of_medians(a):
    n = len(a)
    p = range(0, n, 5) + [n]
    sublist = [a[p[i]:p[i+1]] for i in range(len(p)-1)]
    mergelist = [mergesort(s)[len(s)/2] for s in sublist]
    # TODO: make this call recursive
    return mergelist[len(mergelist)/2]

def select(a, i):
    """ returns the ith order statistic in array a 
    in linear time.""" 
    if i < 1 or i > len(a):
        return None
    if len(a) <= 1: return a
    # choose pivot
    p = median_of_medians(a)

    # partioning
    lesser = [x for x in a if x < p]
    greater = [x for x in a if x > p]
    j = len(lesser)

    if j == i:
        return p
    elif i < j:
        return select(lesser, i)
    else: # i > j
        return select(greater, i-j)


########NEW FILE########
__FILENAME__ = selection_random
from random import randint
def partition(a, l, r):
    """ partitions the array a 
    with pivot as the first element"""
    pivot, i = a[l], l+1
    for j in range(l+1, r+1):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i-1], a[l] = a[l], a[i-1]
    return i-1

def random_selection(a, start, end, i):
    """ returns the ith order statistic 
    in the array a in linear time 
    >>> from random import sample
    >>> test_cases = [sample(range(20), 10) for i in range(10)]
    >>> orders = [randint(0, 9) for i in range(10)] 
    >>> results = [sorted(test_cases[i])[orders[i]] == random_selection(test_cases[i], 0, len(test_cases[i])-1, orders[i]) for i in range(10)]
    >>> print sum(results)
    10
    """
    if start < end:
        p = choosePivot(start, end)
        a[start], a[p] = a[p], a[start]
        j = partition(a, start, end)
        if j == i: return a[i]
        if j < i:
            return random_selection(a, j+1, end, i)
        else: # j > i
            return random_selection(a, start, j-1, i)
    else:
        return a[start]

def choosePivot(s, e):
    return randint(s,e)

if __name__ == "__main__":
    from doctest import testmod
    testmod(verbose=True)

########NEW FILE########
__FILENAME__ = sorting
def mergesort(arr):
    """ perform mergesort on a list of numbers 

    >>> mergesort([5, 4, 1, 6, 2, 3, 9, 7])
    [1, 2, 3, 4, 5, 6, 7, 9]

    >>> mergesort([3, 2, 4, 2, 1])
    [1, 2, 2, 3, 4]
    """
    n = len(arr)
    if n <= 1: return arr
    a1 = arr[:n/2]
    a2 = arr[n/2:]
    a1 = mergesort(a1)
    a2 = mergesort(a2)
    return merge(a1, a2)

def merge(arr_a, arr_b):
    arr_c = []
    i, j = (0, 0)
    while i < len(arr_a) and j < len(arr_b):
        if arr_a[i] <= arr_b[j]:
            arr_c.append(arr_a[i])
            i += 1
        else:
            arr_c.append(arr_b[j])
            j += 1
    if arr_a[i:]: arr_c += arr_a[i:]
    if arr_b[j:]: arr_c += arr_b[j:]
    return arr_c

def quicksort(a):
    """ quicksort implementation in python
    NOTE: This algo uses O(n) extra space
    to compute quicksort.

    >>> quicksort([6, 4, 8, 2, 1, 9, 10])
    [1, 2, 4, 6, 8, 9, 10]
    """
    n = len(a)
    if n<=1:
        return a
    else:
        from random import randrange
        pivot = a.pop(randrange(n))
        lesser = quicksort([x for x in a if x < pivot])
        greater = quicksort([x for x in a if x >= pivot])
        return lesser + [pivot] + greater


def selectionsort(a):
    """ selectionsort implementation

    >>> selectionsort([6, 4, 8, 2, 1, 9, 10])
    [1, 2, 4, 6, 8, 9, 10]
    """
    for i in range(len(a)):
        min = i
        for j in range(i,len(a)):
            if a[j] < a[min]: 
                min = j
        a[i],a[min] = a[min], a[i]
    return a

def bubblesort(a):
    """ bubble sort implementation
    
    >>> bubblesort([6, 4, 8, 2, 1, 9, 10])
    [1, 2, 4, 6, 8, 9, 10]
    """
    for i in range(len(a)):
        for j in range(i, len(a)):
            if a[i] > a[j]:
                a[i], a[j] = a[j], a[i]
    return a


def insertionsort(a):
    """ insertion sort implementation
    >>> insertionsort([6, 4, 8, 2, 1, 9, 10])
    [1, 2, 4, 6, 8, 9, 10]
    """
    for i in range(len(a)):
        item = a[i]
        j = i
        while j > 0 and a[j-1] > item:
            a[j],a[j-1] = a[j-1],a[j]
            j -= 1
    return a

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)

########NEW FILE########
__FILENAME__ = assign
import os, sys
import operator
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
from graphs.graph import graph
from itertools import *
from union_find.unionfind import UnionFind

def ham_dist(e1, e2):
    """ computes hamming distance between two strings e1 and e2 """
    ne = operator.ne
    return sum(imap(ne, e1, e2))

path = "clustering3.txt"
nodes = open(path).readlines()
uf = UnionFind()

# bitcount = {i: nodes[i].count('1') for i in range(len(nodes))}
# similar = [(bitcount[i]-9, ham_dist(nodes[i], nodes[0])) for i in range(1, len(nodes))]
# print nodes[1].count('1') - nodes[2].count('1')
# print hamdist(nodes[1], nodes[2])
for i in range(len(nodes)):
    for j in range(i+1, len(nodes)):
        print i, j, ham_dist(nodes[i], nodes[j])

########NEW FILE########
__FILENAME__ = digraph_test
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
import unittest
from graphs.digraph import digraph

class test_graph(unittest.TestCase):

    def setUp(self):
        self.gr = digraph()
        self.gr.add_nodes(["a", "b", "c", "d", "e", "f"])
        self.gr.add_edges([("a","b"), ("b", "c"), ("a", "d"), ("d", "e"), ("d", "f")])
        self.gr.add_edge(("f", "b"))

    def test_nodes_method(self):
        self.assertEqual(len(self.gr.nodes()), 6)

    def test_add_node_method(self):
        self.gr.add_node("g")
        self.assertEqual(len(self.gr.nodes()), 7)

    def test_has_node_method(self):
        self.assertTrue(self.gr.has_node("a"))

    def test_neighbors_method(self):
        self.assertEqual(len(self.gr.neighbors("a")), 2)

    def test_del_node_method(self):
        self.gr.del_node("a")
        self.assertFalse(self.gr.has_node("a"))
        self.assertEqual(len(self.gr.edges()), 4)

    def test_has_edge_method(self):
        self.assertTrue(self.gr.has_edge(("a", "b")))
        self.assertFalse(self.gr.has_edge(("b", "a")))

    def test_add_duplicate_node_method_throws_exception(self):
        self.assertRaises(Exception, self.gr.add_node, "a")

    def test_del_nonexistent_node_throws_exception(self):
        self.assertRaises(Exception, self.gr.del_node, "z")

    def test_add_duplicate_edge_throws_exception(self):
        self.assertRaises(Exception, self.gr.add_edge, ("a", "b"))

    def test_adding_self_loop(self):
        self.gr.add_edge(("a", "a"))
        self.assertTrue(self.gr.has_edge(("a", "a")))

    def test_remove_self_loop(self):
        self.gr.add_edge(("a", "a"))
        self.gr.del_edge(("a", "a"))
        self.assertFalse(self.gr.has_edge(("a", "a")))

    def test_edges_method(self):
        self.assertEqual(len(self.gr.edges()), 6)

    def test_node_orders_method(self):
        self.assertEqual(self.gr.node_order("d"), 2)

    def test_del_edge_method(self):
        self.gr.del_edge(("b", "c"))
        self.assertFalse(self.gr.has_edge(("b", "c")))

    def test_deleting_non_existing_edge_raises_exception(self):
        self.assertRaises(Exception, self.gr.del_edge, ("a", "z"))

    def test_get_default_weight(self):
        self.assertEqual(self.gr.get_edge_weight(("a", "b")), 1)

    def test_set_weight_on_existing_edge(self):
        self.gr.set_edge_weight(("a", "b"), 10)
        self.assertEqual(self.gr.get_edge_weight(("a", "b")), 10)

    def test_weight_for_nonexisting_edge(self):
        self.assertRaises(Exception, self.gr.get_edge_weight, ("a", "c"))

    def test_get_transpose_method(self):
        transpose = self.gr.get_transpose()
        self.assertEqual(len(transpose.nodes()), len(self.gr.nodes()))
        self.assertEqual(len(transpose.edges()), len(self.gr.edges()))
        self.assertTrue(self.gr.has_edge(("a", "b")))
        self.assertTrue(transpose.has_edge(("b", "a")))
        self.assertFalse(transpose.has_edge(("a", "b")))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = graph_algorithms_test
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
import unittest
from graphs.digraph import digraph
from graphs.graph import graph
from graphs.graph_algorithms import *

class test_graph(unittest.TestCase):

    def setUp(self):
        self.gr = graph()
        self.gr.add_nodes(["s", "a", "b", "c", "d", "e", "f", "g", "h", "j", "k", "l"])
        self.gr.add_edges([("s", "a"), ("s", "b"), ("a", "c"), ("c", "e")])
        self.gr.add_edges([("e", "d"), ("d", "b"), ("a", "b"), ("c", "d")])
        self.gr.add_edges([("g", "h"), ("f", "g")])
        self.gr.add_edges([("j", "k"), ("j", "l")])

        self.digr = digraph()
        self.digr.add_nodes(['s', 'a', 'b', 'c', 'd', 'e', 'f'])
        self.digr.add_edges([("s", "a"), ("a", "b"), ("b", "a"), ("c", "b")])
        self.digr.add_edges([("b", "s"), ("s", "d"), ("d", "e"), ("e", "d")])
        self.digr.add_edges([("b", "f"), ("e", "f")])

    def test_bfs_undirected_graph(self):
        self.assertEqual(len(BFS(self.gr, "s")), 6)
        self.assertEqual(len(BFS(self.gr, "j")), 3)
        self.assertEqual(len(BFS(self.gr, "g")), 3)

    def test_bfs_directed_graph(self):
        self.assertEqual(len(BFS(self.digr, "s")), 6)
        self.assertEqual(len(BFS(self.digr, "c")), 7)
        self.assertEqual(len(BFS(self.digr, "f")), 1)

    def test_dfs_undirected_graph(self):
        self.assertEqual(len(DFS(self.gr, "s")), 6)
        self.assertEqual(len(DFS(self.gr, "j")), 3)
        self.assertEqual(len(DFS(self.gr, "g")), 3)

    def test_dfs_directed_graph(self):
        self.assertEqual(len(DFS(self.digr, "s")), 6)
        self.assertEqual(len(DFS(self.digr, "c")), 7)
        self.assertEqual(len(DFS(self.digr, "f")), 1)

    def test_shortest_hops_undirected_graph(self):
        self.assertEqual(shortest_hops(self.gr, "s")["c"], 2)
        self.assertEqual(shortest_hops(self.gr, "c")["s"], 2)
        self.assertEqual(shortest_hops(self.gr, "s")["s"], 0)
        self.assertEqual(shortest_hops(self.gr, "c")["j"], float('inf'))

    def test_shortest_hops_directed_graph(self):
        self.assertEqual(shortest_hops(self.digr, "s")["f"], 3)
        self.assertEqual(shortest_hops(self.digr, "f")["s"], float('inf'))
        self.assertEqual(shortest_hops(self.digr, "s")["s"], 0)
        self.assertEqual(shortest_hops(self.digr, "s")["c"], float('inf'))

    def test_undirected_connected_component(self):
        self.assertEqual(len(undirected_connected_components(self.gr)), 3)
        self.assertRaises(Exception, undirected_connected_components, self.digr)

    def test_topological_ordering(self):
        dag = digraph() # directed acyclic graph
        dag.add_nodes(["a", "b", "c", "d", "e", "f", "g", "h"])
        dag.add_edges([("a", "b"), ("a", "c"), ("a", "e"), ("d", "a")])
        dag.add_edges([("g", "b"), ("g", "f"), ("f", "e"), ("h", "f"), ("h", "a")])
        order = {o[0]: o[1] for o in topological_ordering(dag)}
        self.assertEqual(sum([order[u] < order[v] for (u, v) in 
                         dag.edges()]), len(dag.edges())) # all comparisons are True

    def test_directed_connected_components(self):
        digr = digraph()
        digr.add_nodes(["a", "b", "c", "d", "e", "f", "g", "h", "i"])
        digr.add_edges([("b", "a"), ("a", "c"), ("c", "b"), ("d", "b")])
        digr.add_edges([("d", "f"), ("f", "e"), ("e", "d"), ("g", "e")])
        digr.add_edges([("g", "h"), ("h", "i"), ("i", "g")])
        self.assertEqual(len(directed_connected_components(digr)), 3)
        digr2 = digraph()
        digr2.add_nodes(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"])
        digr2.add_edges([("a", "b"), ("b", "c"), ("c", "a"), ("b", "d"), ("d", "e")])
        digr2.add_edges([("e", "f"), ("f", "g"), ("g", "e"), ("d", "g"), ("i", "f")])
        digr2.add_edges([("h", "g"), ("c", "h"), ("c", "k"), ("h", "i"), ("i", "j")])
        digr2.add_edges([("h", "j"), ("j", "k"), ("k", "h")])
        self.assertEqual(len(directed_connected_components(digr2)), 4)

    def test_shortest_path_in_directed_graph(self):
        digr = digraph()
        digr.add_nodes(["a", "b", "c", "d", "e", "f"])
        digr.add_edge(("a", "b"), 7)
        digr.add_edge(("a", "c"), 9)
        digr.add_edge(("a", "f"), 14) 
        digr.add_edge(("f", "e"), 9)
        digr.add_edge(("c", "f"), 2)
        digr.add_edge(("c", "d"), 11)
        digr.add_edge(("b", "c"), 10)
        digr.add_edge(("b", "d"), 15)
        digr.add_edge(("d", "e"), 6)
        self.assertEqual(shortest_path(digr, "a")["a"], 0)
        self.assertEqual(shortest_path(digr, "a")["b"], 7)
        self.assertEqual(shortest_path(digr, "a")["c"], 9)
        self.assertEqual(shortest_path(digr, "a")["d"], 20)
        self.assertEqual(shortest_path(digr, "a")["e"], 20)
        self.assertEqual(shortest_path(digr, "a")["f"], 11)

    def test_prims_minimum_spanning_tree(self):
        lines = [l for l in open("tests/edges.txt")]
        lines = lines[1:]
        edges = (l.split() for l in lines)
        gr = graph()
        for (u, v, w) in edges:
            if u not in gr.nodes():
                gr.add_node(u)
            if v not in gr.nodes():
                gr.add_node(v)
            gr.add_edge( (u, v), int(w) )

        min_cost = minimum_spanning_tree(gr)
        self.assertEqual(min_cost, 39)

    def test_kruskals_minimum_spanning_tree(self):
        lines = [l for l in open("tests/edges.txt")]
        lines = lines[1:]
        edges = (l.split() for l in lines)
        gr = graph()
        for (u, v, w) in edges:
            if u not in gr.nodes():
                gr.add_node(u)
            if v not in gr.nodes():
                gr.add_node(v)
            gr.add_edge( (u, v), int(w) )
        min_cost = kruskal_MST(gr)
        self.assertEqual(min_cost, 39)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = graph_test
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
import unittest
from graphs.graph import graph


class test_graph(unittest.TestCase):

    def setUp(self):
        self.gr = graph()
        self.gr.add_nodes(["a", "b", "c", "d", "e", "f"])
        self.gr.add_edge(("a","b"))
        self.gr.add_edge(("a","f"))
        self.gr.add_edge(("b","c"))
        self.gr.add_edge(("c","e"))
        self.gr.add_edge(("c","d"))
        self.gr.add_edge(("d","f"))

    def test_nodes_method(self):
        self.assertEqual(len(self.gr.nodes()), 6)

    def test_add_node_method(self):
        self.gr.add_node("g")
        self.assertEqual(len(self.gr.nodes()), 7)

    def test_has_node_method(self):
        self.assertTrue(self.gr.has_node("a"))

    def test_neighbors_method(self):
        self.assertEqual(len(self.gr.neighbors("a")), 2)

    def test_del_node_method(self):
        self.gr.del_node("a")
        self.assertFalse(self.gr.has_node("a"))
        self.assertEqual(len(self.gr.edges()), 8)

    def test_has_edge_method(self):
        self.assertTrue(self.gr.has_edge(("a", "b")))
        self.assertFalse(self.gr.has_edge(("a", "d")))

    def test_add_duplicate_node_method_throws_exception(self):
        self.assertRaises(Exception, self.gr.add_node, "a")

    def test_del_nonexistent_node_throws_exception(self):
        self.assertRaises(Exception, self.gr.del_node, "z")

    def test_add_duplicate_edge_throws_exception(self):
        self.assertRaises(Exception, self.gr.add_edge, ("a", "b"))

    def test_add_edge_from_non_existing_node(self):
        self.assertRaises(Exception, self.gr.add_edge, ("b", "z"))

    def test_adding_self_loop(self):
        self.gr.add_edge(("a", "a"))
        self.assertTrue(self.gr.has_edge(("a", "a")))

    def test_remove_self_loop(self):
        self.gr.add_edge(("a", "a"))
        self.gr.del_edge(("a", "a"))
        self.assertFalse(self.gr.has_edge(("a", "a")))

    def test_edges_method(self):
        self.assertEqual(len(self.gr.edges()), 2*6)

    def test_add_edges_method(self):
        self.gr.add_edges([("a", "c"), ("c", "f"), ("d", "e")])
        self.assertTrue(self.gr.has_edge(("a", "c")))
        self.assertTrue(self.gr.has_edge(("c", "f")))
        self.assertTrue(self.gr.has_edge(("d", "e")))

    def test_node_orders_method(self):
        self.assertEqual(self.gr.node_order("c"), 3)

    def test_del_edge_method(self):
        self.gr.del_edge(("a", "f"))
        self.assertFalse(self.gr.has_edge(("a", "f")))

    def test_deleting_non_existing_edge_raises_exception(self):
        self.assertRaises(Exception, self.gr.del_edge, ("a", "z"))

    def test_get_default_weight(self):
        self.assertEqual(self.gr.get_edge_weight(("a", "b")), 1)

    def test_set_weight_on_existing_edge(self):
        self.gr.set_edge_weight(("a", "b"), 10)
        self.assertEqual(self.gr.get_edge_weight(("a", "b")), 10)

    def test_weight_for_nonexisting_edge(self):
        self.assertRaises(Exception, self.gr.get_edge_weight, ("a", "c"))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = heap_test
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
import unittest
from heaps.minheap import minheap
from heaps.maxheap import maxheap
import random

class test_heap(unittest.TestCase):

    def setUp(self):
        self.h = minheap()
        self.m = maxheap()
        self.a = [random.choice(range(50)) for i in range(10)]
        self.h.build_heap(self.a)
        self.m.build_heap(self.a)

    def test_heap_pop(self):
        self.assertEqual(min(self.a), self.h.heappop())
        self.assertEqual(max(self.a), self.m.heappop())
    
    def test_max_elements(self):
        self.assertEqual(len(self.a), self.h.max_elements())
        self.assertEqual(len(self.a), self.m.max_elements())

    def test_heap_sort(self):
        sorted_h = [self.h.heappop() for i in range(self.h.max_elements())]
        sorted_m = [self.m.heappop() for i in range(self.m.max_elements())]
        self.assertEqual(sorted_h, sorted(self.a))
        self.assertEqual(sorted_m, sorted(self.a, reverse=True))

    def test_heap_push_method(self):
        self.h.heappush(-1)
        self.assertEqual(-1, self.h.heappop())
        self.m.heappush(100)
        self.assertEqual(100, self.m.heappop())

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = unionfind_test
import os, sys
sys.path.append(os.path.join(os.getcwd(), os.path.pardir))
import unittest
from union_find.unionfind import UnionFind

class test_unionfind(unittest.TestCase):

    def setUp(self):
        self.uf = UnionFind()
        self.uf.insert("a", "b")
        self.uf.insert("b", "c")
        self.uf.insert("i", "j")

    def test_get_parent_method(self):
        self.assertEqual("a", self.uf.get_leader("a"))
        self.assertEqual("a", self.uf.get_leader("b"))
        self.assertEqual("a", self.uf.get_leader("c"))
        self.assertEqual("i", self.uf.get_leader("j"))
        self.assertEqual("i", self.uf.get_leader("i"))
        self.assertNotEqual(self.uf.get_leader("a"), self.uf.get_leader("i"))

    def test_insert_method(self):
        self.uf.insert("c", "d")
        self.assertEqual(self.uf.get_leader("c"), self.uf.get_leader("d"))
        self.assertEqual(self.uf.get_leader("a"), self.uf.get_leader("d"))

    def test_insert_one_node(self):
        self.uf.insert('z')
        self.assertEqual(self.uf.get_leader('z'), 'z')
        self.assertEqual(self.uf.count_groups(), 3)

    def test_make_union_method(self):
        self.uf.make_union(self.uf.get_leader("a"), self.uf.get_leader("i"))
        self.assertEqual(self.uf.get_leader("a"), self.uf.get_leader("i"))

    def test_make_union_with_invalid_leader_raises_exception(self):
        self.assertRaises(Exception, self.uf.make_union, "a", "z")

    def test_get_count(self):
        self.uf.insert("z", "y")
        self.assertEqual(self.uf.count_groups(), 3)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = binarysearchtree
""" Binary Search Tree
Methods - find_element(value), get_max(), get_min(), successor(value),
          insert, delete, values() """

class Node(object):
    def __init__(self, value):
        self.right = None
        self.left = None
        self.parent = None
        self.value = value

    def __repr__(self):
        return "Node with value - %s" % self.value


class BinarySearchTree(object):
    def __init__(self):
        self.root = None
        self.len = 0

    def __len__(self):
        return self.len 

    def is_empty(self):
        return self.root == None

    def _inorder(self, node, values):
        if node != None:
            self._inorder(node.left, values)
            values.append(node.value)
            self._inorder(node.right, values)

    def _preorder(self, node, values):
        if node != None:
            values.append(node.value)
            self._preorder(node.left, values)
            self._preorder(node.right, values)

    def _postorder(self, node, values):
        if node != None:
            self._postorder(node.left, values)
            self._postorder(node.right, values)
            values.append(node.value)
            
    def values(self, reverse = False, order="in"):
        values = []
        if order == "in":
            self._inorder(self.root, values)
        elif order == "pre":
            self._preorder(self.root, values)
        else: #order is post
            self._postorder(self.root, values)
        if reverse:
            return values[::-1]
        return values

    def _search(self, root, value):
        if not root or root.value == value: 
            return root
        if value < root.value:
            return self._search(root.left, value)
        else:
            return self._search(root.right, value)

    def find_element(self, value):
        return self._search(self.root, value)

    def _extremes(self, root, find_min = True):
        while (find_min and root.left) or (not find_min and root.right):
            if find_min:
                root = root.left
            else: # find max
                root = root.right
        return root

    def get_min(self):
        """ returns the element with the minimum value """
        return self._extremes(self.root, find_min=True)

    def get_max(self):
        """ returns the element with the maximum value """
        return self._extremes(self.root, find_min=False)
    
    def successor(self, value):
        """ returns the successor of the element with value - value"""
        node = self.find_element(value)
        if not node: 
            return None
        if node.right:
            return self._extremes(node.right, find_min=True)
        parent = node.parent
        while parent and parent.right == node:
            node = parent
            parent = parent.parent
        return parent

    def insert(self, value):
        new_node = Node(value)
        if self.is_empty():
            self.root = new_node
        else:
            node = self.root
            while node and node.value != value:
                parent = node
                if node.value < value:
                    node = node.right
                else:
                    node = node.left
            if parent.value > value:
                parent.left = new_node
            else:
                parent.right = new_node
            new_node.parent = parent
        self.len += 1
        return
    
    def delete(self, value):
        """ deletes a node from tree with value - value """
        node = self.find_element(value)
        if not node:
            return None
        if not node.left or not node.right:
            node_spliced = node 
        else:
            node_spliced = self.successor(node.value)
        if node_spliced.left:
            temp_node = node_spliced.left
        else:
            temp_node = node_spliced.right
        if temp_node:
            temp_node.parent = node_spliced.parent
        if not node_spliced.parent:
            self.root = temp_node
        elif node_spliced == node_spliced.parent.left:
            node_spliced.parent.left = temp_node
        else:
            node_spliced.parent.right = temp_node
        
        if node != node_spliced:
            node.value = node_spliced.value
        return node_spliced

########NEW FILE########
__FILENAME__ = trie
""" Tries in python 
Methods -  insert_key(k, v)
           has_key(k)
           retrie_val(k)
           start_with_prefix(prefix)
"""
# HELPERS #
def _get_child_branches(tr):
    if tr == []:
        return []
    return tr[1:]

def _get_child_branch(tr, c):
    for branch in _get_child_branches(tr):
        if branch[0] == c:
            return branch
    return None

def _retrive_branch(k, trie_list):
    if k == "":
        return None
    tr = trie_list
    for c in k:
        child_branch = _get_child_branch(tr, c)
        if not child_branch:
            return None
        tr = child_branch
    return tr

def _is_trie_bucket(bucket):
    if len(bucket) != 2:
        return False
    if type(bucket[1]) is tuple:
        return True

def _get_bucket_key(bucket):
    if not _is_trie_bucket(bucket):
        return None
    return bucket[1][0] 

# HAS_KEY #
def has_key(k, tr):
    if k == "":
        return None
    key_tuple = _retrive_branch(k, tr)
    if not key_tuple:
        return False
    return True

# RETRIE_VAL
def retrie_val(k, tr):
    if k == "":
        return None
    key_tuple = _retrive_branch(k, tr)
    if not key_tuple:
        return None
    return key_tuple[1]


def insert_key(key, v, trie_list):
    if key == "":
        return None
    elif has_key(key, trie_list):
        return None
    else:
        tr = trie_list
        for char in key:
            branch = _get_child_branch(tr, char)
            if branch == None:
                new_branch = [char]
                tr.append(new_branch)
                tr = new_branch
            else:
                tr = branch
        tr.append((key, v))
        return None


def start_with_prefix(prefix, trie):
    branch = _retrive_branch(prefix, trie)
    if not branch:
        return []
    prefix_list = []
    q = branch[1:]
    while q:
        curr_branch = q.pop(0)
        if _is_trie_bucket(curr_branch):
            prefix_list.append(_get_bucket_key(curr_branch))
        else:
            q.extend(curr_branch[1:])
    return prefix_list

if __name__ == "__main__":
    trie = [[]]
    states = """
            Alabama
            Alaska
            Arizona
            Arkansas
            California
            Colorado
            Connecticut
            Delaware
            Florida
            Georgia
            Hawaii
            Idaho
            Illinois
            Indiana
            Iowa
            Kansas
            Kentucky
            Louisiana
            Maine
            Maryland
            Massachusetts
            Michigan
            Minnesota
            Mississippi
            Missouri
            Montana
            Nebraska
            Nevada
            New Hampshire
            New Jersey
            New Mexico
            New York
            North Carolina
            North Dakota
            Ohio
            Oklahoma
            Oregon
            Pennsylvania
            Rhode Island
            South Carolina
            South Dakota
            Tennessee
            Texas
            Utah
            Vermont
            Virginia
            Washington
            West Virginia
            Wisconsin
            Wyoming"""    
    states_list = [w.strip().lower() for w in states.splitlines() if w]
    for state in states_list:
        insert_key(state, True, trie)
    print start_with_prefix("new", trie)

########NEW FILE########
__FILENAME__ = unionfind
class UnionFind(object):
    """ Disjoint Set data structure supporting union and find operations used
    for Kruskal's MST algorithm 
    Methods - 
        insert(a, b) -> inserts 2 items in the sets
        get_leader(a) -> returns the leader(representative) corresponding to item a
        make_union(leadera, leaderb) -> unions two sets with leadera and leaderb
        in O(nlogn) time where n the number of elements in the data structure
        count_keys() -> returns the number of groups in the data structure
    """

    def __init__(self):
        self.leader = {}
        self.group = {}
        self.__repr__ = self.__str__

    def __str__(self):
        return str(self.group)

    def get_sets(self):
        """ returns a list of all the sets in the data structure"""
        return [i[1] for i in self.group.items()]

    def insert(self, a, b=None):
        """ takes a hash of object and inserts it in the
        data structure """

        leadera = self.get_leader(a)
        leaderb = self.get_leader(b)

        if not b:
            # only one item is inserted
            if a not in self.leader:
                # a is not already in any set
                self.leader[a] = a
                self.group[a] = set([a])
                return 

        if leadera is not None:
            if leaderb is not None:
                if leadera == leaderb: return # Do nothing
                self.make_union(leadera, leaderb)
            else:
                # leaderb is none
                self.group[leadera].add(b)
                self.leader[b] = leadera
        else:
            if leaderb is not None:
                # leadera is none
                self.group[leaderb].add(a)
                self.leader[a] = leaderb
            else:
                self.leader[a] = self.leader[b] = a
                self.group[a] = set([a, b])

    def get_leader(self, a):
        return self.leader.get(a)

    def count_groups(self):
        """ returns a count of the number of groups/sets in the
        data structure"""
        return len(self.group.keys())

    def make_union(self, leadera, leaderb):
        """ takes union of two sets with leaders, leadera and leaderb
        in O(nlogn) time """
        if leadera not in self.group or leaderb not in self.group:
            raise Exception("Invalid leader specified leadera -%s, leaderb - %s" % (leadera, leaderb))
        groupa = self.group[leadera]
        groupb = self.group[leaderb]
        if len(groupa) < len(groupb):
            # swap a and b if a is a smaller set
            leadera, groupa, leaderb, groupb = leaderb, groupb, leadera, groupa
        groupa |= groupb # taking union of a with b
        del self.group[leaderb] # delete b
        for k in groupb:
            self.leader[k] = leadera

if __name__ == "__main__":
    uf = UnionFind()
    uf.insert("a", "b")

########NEW FILE########
