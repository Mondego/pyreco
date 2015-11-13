__FILENAME__ = bfs_benchmark
#! /usr/bin/env python

from collections import deque
import utilities

def breadth_first_search(graph, node, num_nodes):
    """
    Does a breadth-first search of the graph starting at the node.
    Returns the first num_nodes nodes (excluding direct neighbors)
    """
    neighbors = set(graph[node])
    looked_at = set(graph[node])
    looked_at.add(node)
    visited = []
    queue = deque(graph[node])

    while queue and len(visited)<num_nodes:
        next_node = queue.popleft()
        if next_node not in neighbors:
            visited.append(next_node)
        queue.extend(n for n in graph[next_node] if n not in looked_at)
        looked_at.update(graph[next_node])

    return visited

def bfs_benchmark(train_file, test_file, submission_file, num_predictions):
    """
    Runs the breadth-first search benchmark.
    """
    graph = utilities.read_graph(train_file)
    test_nodes = utilities.read_nodes_list(test_file)
    test_predictions = [breadth_first_search(graph, node, num_predictions)
                        for node in test_nodes]
    utilities.write_submission_file(submission_file, 
                                    test_nodes, 
                                    test_predictions)

if __name__=="__main__":
    bfs_benchmark("../Data/train.csv",
                  "../Data/test.csv",
                  "../Submissions/bfs_benchmark_updated.csv",
                  10)

########NEW FILE########
__FILENAME__ = random_benchmark
#! /usr/bin/env python

import random
import utilities

def read_nodes_from_training(file_name):
    """
    Returns a list of all the nodes in the graph
    """
    node_set = set()

    for nodes in utilities.edges_generator(file_name):
        for node in nodes:
            node_set.add(node)

    return list(node_set)

def random_benchmark(train_file, test_file, submission_file, num_predictions):
    """
    Runs the random benchmark.
    """
    nodes = read_nodes_from_training(train_file)
    test_nodes = utilities.read_nodes_list(test_file)
    test_predictions = [[random.choice(nodes) for x in range(num_predictions)]
                        for node in test_nodes]
    utilities.write_submission_file(submission_file, 
                                    test_nodes, 
                                    test_predictions)

if __name__=="__main__":
    random_benchmark("../Data/train.csv",
                     "../Data/test.csv",
                     "../Submissions/random_benchmark.csv",
                     10)


########NEW FILE########
__FILENAME__ = top_k_benchmark
#! /usr/bin/env python

import random
import utilities

def get_top_k_nodes(file_name, k):
    """
    Returns a list of the top k most followed nodes
    """
    node_followers = {}

    for nodes in utilities.edges_generator(file_name):
        if nodes[1] not in node_followers:
            node_followers[nodes[1]] = 0
        node_followers[nodes[1]] += 1

    return sorted(node_followers.keys(), 
                  key=lambda n: node_followers[n], 
                  reverse = True)[:k]

def top_k_benchmark(train_file, test_file, submission_file, num_predictions):
    """
    Runs the top k benchmark
    """
    top_k_nodes = get_top_k_nodes(train_file, num_predictions)
    test_nodes = utilities.read_nodes_list(test_file)
    test_predictions = [top_k_nodes for node in test_nodes]
    utilities.write_submission_file(submission_file, 
                                    test_nodes, 
                                    test_predictions)

if __name__=="__main__":
    top_k_benchmark("../Data/train.csv",
                    "../Data/test.csv",
                     "../Submissions/top_k_benchmark.csv",
                    10)

########NEW FILE########
__FILENAME__ = utilities
import csv

def edges_generator(file_name):
    """
    Generator that returns edges given a 2-column csv graph file
    """

    f = open(file_name)
    reader = csv.reader(f)
    # Ignore the header
    reader.next()

    for edges in reader:
        nodes = [int(node) for node in edges] 
        yield nodes

    f.close()

def read_graph(file_name):
    """
    Reads a sparsely represented directed graph into a dictionary
    """
    
    # Store the graph as a dictionary of edges
    graph = {}

    def initialize_node(node):
        if node not in graph:
            graph[node] = []

    for nodes in edges_generator(file_name):
        for node in nodes:
            initialize_node(node)
        graph[nodes[0]].append(nodes[1])

    return graph

def read_nodes_list(test_file):
    """
    Reads of single-column list of nodes
    """

    f = open(test_file)
    reader = csv.reader(f)
    reader.next() # ignore header

    nodes = []
    for row in reader:
        nodes.append(int(row[0]))
    return nodes
    f.close()

def write_submission_file(submission_file, test_nodes, test_predictions):
    """
    Writes the submission file
    """

    f = open(submission_file, "w")
    writer = csv.writer(f)
    writer.writerow(["source_node", "destination_nodes"])

    for source_node, dest_nodes in zip(test_nodes, test_predictions):
        writer.writerow([str(source_node),
                         " ".join([str(n) for n in dest_nodes])])
    f.close()

########NEW FILE########
