__FILENAME__ = pagerank
"""pagerank.py illustrates how to use the pregel.py library, and tests
that the library works.

It illustrates pregel.py by computing the PageRank for a randomly
chosen 10-vertex web graph.

It tests pregel.py by computing the PageRank for the same graph in a
different, more conventional way, and showing that the two outputs are
near-identical."""

from pregel import Vertex, Pregel

# The next two imports are only needed for the test.  
from numpy import mat, eye, zeros, ones, linalg
import random

num_workers = 4
num_vertices = 10

def main():
    vertices = [PageRankVertex(j,1.0/num_vertices,[]) 
                for j in range(num_vertices)]
    create_edges(vertices)
    pr_test = pagerank_test(vertices)
    print "Test computation of pagerank:\n%s" % pr_test
    pr_pregel = pagerank_pregel(vertices)
    print "Pregel computation of pagerank:\n%s" % pr_pregel
    diff = pr_pregel-pr_test
    print "Difference between the two pagerank vectors:\n%s" % diff
    print "The norm of the difference is: %s" % linalg.norm(diff)

def create_edges(vertices):
    """Generates 4 randomly chosen outgoing edges from each vertex in
    vertices."""
    for vertex in vertices:
        vertex.out_vertices = random.sample(vertices,4)

def pagerank_test(vertices):
    """Computes the pagerank vector associated to vertices, using a
    standard matrix-theoretic approach to computing pagerank.  This is
    used as a basis for comparison."""
    I = mat(eye(num_vertices))
    G = zeros((num_vertices,num_vertices))
    for vertex in vertices:
        num_out_vertices = len(vertex.out_vertices)
        for out_vertex in vertex.out_vertices:
            G[out_vertex.id,vertex.id] = 1.0/num_out_vertices
    P = (1.0/num_vertices)*mat(ones((num_vertices,1)))
    return 0.15*((I-0.85*G).I)*P

def pagerank_pregel(vertices):
    """Computes the pagerank vector associated to vertices, using
    Pregel."""
    p = Pregel(vertices,num_workers)
    p.run()
    return mat([vertex.value for vertex in p.vertices]).transpose()

class PageRankVertex(Vertex):

    def update(self):
        # This routine has a bug when there are pages with no outgoing
        # links (never the case for our tests).  This problem can be
        # solved by introducing Aggregators into the Pregel framework,
        # but as an initial demonstration this works fine.
        if self.superstep < 50:
            self.value = 0.15 / num_vertices + 0.85*sum(
                [pagerank for (vertex,pagerank) in self.incoming_messages])
            outgoing_pagerank = self.value / len(self.out_vertices)
            self.outgoing_messages = [(vertex,outgoing_pagerank) 
                                      for vertex in self.out_vertices]
        else:
            self.active = False

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = pregel
"""pregel.py is a python 2.6 module implementing a toy single-machine
version of Google's Pregel system for large-scale graph processing."""

import collections
import threading

class Vertex():

    def __init__(self,id,value,out_vertices):
        # This is mostly self-explanatory, but has a few quirks:
        #
        # self.id is included mainly because it's described in the
        # Pregel paper.  It is used briefly in the pagerank example,
        # but not in any essential way, and I was tempted to omit it.
        #
        # Each vertex stores the current superstep number in
        # self.superstep.  It's arguably not wise to store many copies
        # of global state in instance variables, but Pregel's
        # synchronous nature lets us get away with it.
        self.id = id 
        self.value = value
        self.out_vertices = out_vertices
        self.incoming_messages = []
        self.outgoing_messages = []
        self.active = True
        self.superstep = 0
   
class Pregel():

    def __init__(self,vertices,num_workers):
        self.vertices = vertices
        self.num_workers = num_workers

    def run(self):
        """Runs the Pregel instance."""
        self.partition = self.partition_vertices()
        while self.check_active():
            self.superstep()
            self.redistribute_messages()

    def partition_vertices(self):
        """Returns a dict with keys 0,...,self.num_workers-1
        representing the worker threads.  The corresponding values are
        lists of vertices assigned to that worker."""
        partition = collections.defaultdict(list)
        for vertex in self.vertices:
            partition[self.worker(vertex)].append(vertex)
        return partition

    def worker(self,vertex):
        """Returns the id of the worker that vertex is assigned to."""
        return hash(vertex) % self.num_workers

    def superstep(self):
        """Completes a single superstep.  

        Note that in this implementation, worker threads are spawned,
        and then destroyed during each superstep.  This creation and
        destruction causes some overhead, and it would be better to
        make the workers persistent, and to use a locking mechanism to
        synchronize.  The Pregel paper suggests that this is how
        Google's Pregel implementation works."""
        workers = []
        for vertex_list in self.partition.values():
            worker = Worker(vertex_list)
            workers.append(worker)
            worker.start()
        for worker in workers:
            worker.join()

    def redistribute_messages(self):
        """Updates the message lists for all vertices."""
        for vertex in self.vertices:
            vertex.superstep +=1
            vertex.incoming_messages = []
        for vertex in self.vertices:
            for (receiving_vertix,message) in vertex.outgoing_messages:
                receiving_vertix.incoming_messages.append((vertex,message))

    def check_active(self):
        """Returns True if there are any active vertices, and False
        otherwise."""
        return any([vertex.active for vertex in self.vertices])

class Worker(threading.Thread):

    def __init__(self,vertices):
        threading.Thread.__init__(self)
        self.vertices = vertices

    def run(self):
        self.superstep()

    def superstep(self):
        """Completes a single superstep for all the vertices in
        self."""
        for vertex in self.vertices:
            if vertex.active:
                vertex.update()

########NEW FILE########
