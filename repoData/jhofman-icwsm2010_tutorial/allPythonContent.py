__FILENAME__ = hstream
#!/usr/bin/env python
#
# file: hstream.py
#
# description: simple class for implementing hadoop streaming jobs in python
#   adapted from: 
#     http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python
#
# usage: inherit the HStream class and define the mapper and reducer
# functions, e.g. in myjob.py:
#
#   from hstream import HStream
#
#   class MyJob(Hstream):
#     def mapper(self, record):
#       # ...
#       self.write_output( (key, value) )
#
#     def reducer(self, key, records):
#       # ...
#       for record in records:
#           # ...
#       self.write_output( (key, value) )
#
#   if __name__=='__main__':
#     MyJob()
#
# to run mapper: ./myjob.py -m < input
# to run reducer: ./myjob.py -m < input
# to run full job: ./myjob.py -l < input
#
# to specify additional command line arguments, append arg=val after
# the -[m|r|l] switch, e.g. ./myjob.py -m max=10. you can then
# retrieve these arguments using self.args,
# e.g. self.args['max']. this is often useful for loading a parameter
# when initializing the mapper or reducer, e.g. in mapper_init,
# self.max = self.args['max'], which will then be acessible as
# self.max in mapper().
# 
# see examples for more details.
#
# author: jake hofman (hofman@yahoo-inc.com)
#

from itertools import groupby
from operator import itemgetter
import sys
from optparse import OptionParser
from StringIO import StringIO


class HStream:
    """
    simple wrapper class to facilitate writing hadoop streaming jobs
    in python. inherit the class and define mapper and reducer functions.
    see header of hstream.py for more details.
    """
    default_delim='\t'
    default_istream=sys.stdin
    default_ostream=sys.stdout
    default_estream=sys.stderr
    
    def __init__(self,
                 delim=default_delim,
                 istream=default_istream,
                 ostream=default_ostream):
        self.delim=delim
        self.istream=istream
        self.ostream=ostream

        self.parse_args()
        
    def read_input(self): 
        for line in self.istream:
            yield line.rstrip('\n').split(self.delim)

    def write_output(self,s):
        if type(s) is str:
            self.ostream.write(s + '\n')
        else:
            self.ostream.write(self.delim.join(map(str,s)) + '\n')

    def map(self):
        self.mapper_init()

        for record in self.read_input():
            self.mapper(record)

        self.mapper_end()

    def reduce(self):
        self.reducer_init()

        data = self.read_input()
        for key, records in groupby(data, itemgetter(0)):
            self.reducer(key, records)

        self.reducer_end()

    def combine(self):
        data = self.read_input()
        self.combiner( data )

    def mapper_init(self):
        return

    def mapper(self, record):
        self.write_output(record[0])

    def mapper_end(self):
        return

    def reducer_init(self):
        return

    def reducer(self, key, records):
        for record in records:
            self.write_output(self.delim.join(record))

    def reducer_end(self):
        return

    def combiner(self, records):
        for record in records:
            self.write_output(self.delim.join(record))

    def parse_args(self):
        
        parser=OptionParser()
        parser.add_option("-m","--map",
                          help="run mapper",
                          action="store_true",
                          dest="run_map",
                          default="False")
        parser.add_option("-r","--reduce",
                          help="run reduce",
                          action="store_true",
                          dest="run_reduce",
                          default="False")
        parser.add_option("-c","--combine",
                          help="run combiner",
                          action="store_true",
                          dest="run_combine",
                          default="False")
        parser.add_option("-l","--local",
                          help="run local test of map | sort | reduce",
                          action="store_true",
                          dest="run_local",
                          default="False")

        opts, args = parser.parse_args()

        self.args=dict([s.split('=',1) for s in args])

        if opts.run_map is True:
            self.map()
        elif opts.run_reduce is True:
            self.reduce()
        elif opts.run_combine is True:
            self.combine()
        elif opts.run_local is True:
            self.run_local()
            

    def run_local(self):
        map_output=StringIO()

        # map stdin to temporary string stream
        self.istream=sys.stdin
        self.ostream=map_output
        self.map()

        # sort string stream
        map_output.seek(0)        
        reduce_input=StringIO(''.join(sorted(map_output)))

        # reduce string stream to stdout
        self.istream=reduce_input
        self.ostream=sys.stdout
        self.reduce()

        
if __name__=='__main__':
    
    pass

########NEW FILE########
__FILENAME__ = adjacency_list
#!/usr/bin/env python
#
# file: adjacency_list.py
#
# description: converts edge list to adjacency list
#
# usage: see run_toygraph
#
# author: jake hofman (gmail: jhofman)
#

import sys
sys.path.append('.')
from hstream import HStream

class AdjacencyList(HStream):
    def mapper(self, record):
        
        if len(record) != 2:
            sys.stderr.write("\t".join(record)+'\n')
            return
        else:
            source, target = record

            # write out two records for each edge,
            # the first indicating that the source points to the
            # target
            # second indiciating that the target is pointed to by the
            # source
            self.write_output((source,'>',target))
            self.write_output((target,'<',source))

    def reducer(self, key, records):
        in_neighbors=set()
        out_neighbors=set()

        for record in records:
            assert len(record) == 3

            u, dir, v = record
            
            if dir == '>':
                # if u points to v, store as an out neighbor
                out_neighbors.add(v)
            if dir == '<':
                # if u is pointed to by v, store as an in neighbor
                in_neighbors.add(v)

        # degree is number of neighbors
        in_degree=len(in_neighbors)
        out_degree=len(out_neighbors)

        # write out node, in/out degrees, in/out neighbors
        self.write_output((key,
                           in_degree,
                           out_degree,
                           " ".join(in_neighbors),
                           " ".join(out_neighbors)))


if __name__ == '__main__':

    AdjacencyList()

########NEW FILE########
__FILENAME__ = bfs
#!/usr/bin/env python
#
# file: bfs.py
#
# description: runs one round of breadth-first search
#
# usage: see run_toygraph
#
# author: jake hofman (gmail: jhofman)
#

import sys
sys.path.append('.')
from hstream import HStream
from collections import defaultdict

class BreadthFirstSearch(HStream):

    def mapper(self, record):
        if len(record) != 3:
            sys.stderr.write("\t".join(record)+'\n')
            return

        node, distance, neighbors = record

        # output original record
        self.write_output(record)

        # use float for distance to accomodate 'inf'
        distance = float(distance)

        # if node is reachable, neighbors are distance+1 away
        if distance < float('inf') and neighbors:

            # output each neighbor and distance+1
            for neighbor in neighbors.split(' '):
                self.write_output( (neighbor, int(distance+1)) )


    def reducer(self, key, records):

        # initialize minimum distance
        min_distance = float('inf')

        for record in records:

            if len(record) == 3:
                # original record
                node, distance, neighbors = record

            elif len(record) == 2:
                # updated distance
                node, distance = record

            else:
                sys.stderr.write("\t".join(record)+'\n')
                return

            # update minimum distance
            min_distance = min(min_distance, float(distance))

        # convert to int or leave as 'inf')
        if min_distance < float('inf'):
            min_distance = int(min_distance)
            
        self.write_output( (node, min_distance, neighbors) )
                    
if __name__=='__main__':
    BreadthFirstSearch()
                        


########NEW FILE########
__FILENAME__ = bfs_init
#!/usr/bin/env python
#
# file: bfs_init.py
#
# description: initialize breadth-first search
#
# usage: see run_toygraph
#
# author: jake hofman (gmail: jhofman)
#

import sys
sys.path.append('.')
from hstream import HStream
from collections import defaultdict

class BreadthFirstSearchInit(HStream):

    def mapper_init(self):
        # get source node id from argument (specified as source=node after -[m|r|l] switch) 
        self.source = self.args['source']

    def mapper(self, record):
        if len(record) != 5:
            sys.stderr.write("\t".join(record)+'\n')
            return

        node, in_degree, out_degree, in_neighbors, out_neighbors = record

        # mark distance to source node as 0, other nodes as inf
        if node == self.source:
            distance = 0
        else:
            distance = float('inf')

        self.write_output( (node, distance, out_neighbors) )
                    
if __name__=='__main__':
    BreadthFirstSearchInit()
                        


########NEW FILE########
__FILENAME__ = clustering
#!/usr/bin/env python
#
# file: clustering.py
#
# description: calculates number of directed triangles each node is a
# member of, as well as size of one/two-hop neighborhoods.
#
# usage: see run_toygraph
#
# author: jake hofman (gmail: jhofman)
#

import sys
sys.path.append('.')
from hstream import HStream
from collections import defaultdict

class ClusteringCoefficient(HStream):
    def mapper(self, record):

        if len(record) != 5:
            sys.stderr.write("\t".join(record)+'\n')
            return
        else:
            u, in_degree, out_degree, in_neighbors, out_neighbors = record

            # note: for completed inbound triangles, swap in and out neighbors
            # in_neighbors, out_neighbors = out_neighbors, in_neighbors

            # pass all out_neighbors to each in_neighbor
            # to compile directed two-hop neighborhood
            #
            # read as "v goes through u to reach out_neighbors"
            [self.write_output((v,u,out_neighbors)) \
             for v in in_neighbors.split()]


    def reducer(self, key, records):        
        # dictionaries to store one and two hop neighbors
        # note: two hop includes one hop neighbors
        onehop={}
        twohop=defaultdict(int)

        for record in records:
            if len(record) == 2:
                # no out-neighbors
                # just record v as one hop neighbor
                u, v = record
                onehop[v]=1

            else:
                assert len(record) == 3
                u, v, ws  = record

                # record one and two hop neighbors
                onehop[v]=1
                for w in ws.split():
                    twohop[w]+=1

        # node degree
        size_onehop=len(onehop)
        # number of nodes within two hops
        size_twohop=size_onehop+len(twohop)

        # find intersection of nodes in one and two hop neighborhoods
        # sum up number of paths to second hop node
        onetwo=[twohop[k] for k in onehop.keys() if k in twohop]
        triangles=0.5*sum(onetwo)

        # number of nodes exactly two hops away
        size_twohop-=len(onetwo)
        
        self.write_output((key, triangles, size_onehop, size_twohop))

if __name__ == '__main__':

    ClusteringCoefficient()

########NEW FILE########
__FILENAME__ = degree_dist
#!/usr/bin/env python
#
# file: degree_dist.py
#
# description: calculates degree distribution from adjacency list
#
# usage: see run_toygraph
#
# author: jake hofman (gmail: jhofman)
#

import sys
sys.path.append('.')
from hstream import HStream

class DegreeDistribution(HStream):
    def mapper(self, record):
        # assumes input of:
        # node in_degree out_degree in_neighbors out_neighbors

        if len(record) != 5:
            sys.stderr.write("\t".join(record)+'\n')
            return
        else:
            node, in_degree, out_degree, in_neighbors, out_neighbors = record

            # output node's in-degree and count of 1 as
            # in_k, 1
            bin = 'in_' + in_degree
            self.write_output( (bin, 1) )

            # output node's out-degree and count of 1 as
            # out_k, 1
            bin = 'out_' + out_degree
            self.write_output( (bin, 1) )


    def reducer(self, key, records):
        # total number of nodes with this degree
        total = 0
        
        for record in records:
            if len(record) != 2:
                sys.stderr.write("\t".join(record)+'\n')
                return

            bin, count = record

            # increment node count
            total += int(count)

        # write result as
        # (in|out), degree, count
        direction, degree = bin.split('_')
        self.write_output( (direction, degree, total) )

if __name__ == '__main__':

    DegreeDistribution()

########NEW FILE########
__FILENAME__ = hstream
../hstream.py
########NEW FILE########
__FILENAME__ = hstream
../hstream.py
########NEW FILE########
__FILENAME__ = wordcount
#!/usr/bin/env python
#
# file: wordcount.py
#
# description: the obligatory wordcount example for an introduction to
# mapreduce, implemented in hadoop streaming using a simple wrapper
# class (hstream). counts the number of times each word in the input
# occurs.
#
# usage:
#   locally:
#     map only: cat input.txt | ./wordcount.py -m
#     map+"shuffle": cat input.txt | ./wordcount.py -m | sort -k1
#     map+"shuffle"+reduce: cat input.txt | ./wordcount.py -r
#       which is equivalent to:
#       cat input.txt | ./wordcount.py -m | sort -k1 | ./wordcount.py -r
#   distributed:
#     (assumes $HADOOP_HOME is set to your hadoop install)
#
#     $HADOOP_HOME/bin/hadoop jar $HADOOP_HOME/contrib/streaming/hadoop-*-streaming.jar \
#       -input input.txt \
#       -output wc_output \
#       -mapper 'wordcount.py -m' \
#       -reducer 'wordcount.py -r' \
#       -file wordcount.py \
#       -file hstream.py
#
# author: jake hofman (gmail: jhofman)
#

# import simple hadoop streaming class to simply definition of mapper
# and reducer functions
import sys
sys.path.append('.')
from hstream import HStream


class WordCount(HStream):
    """
    hadoop streaming class to count the number of times each word in
    the input occurs.
    """
    
    def mapper(self, record):
        """
        the wordcount mapper, which splits each line into words and
        produces an intermediate key (the word) and value (count of 1)
        for each word occurence on the line.
        """
        
        # join all words on the the line into one string
        # and split on whitespace, producing a tuple of words
        #
        # note: record is a tuple, automatically split on the default
        # delimiter (tab)
        words = " ".join(record).split()

        # loop over each word, writing the word (as key) and count of
        # 1 (as value)
        for word in words:
            self.write_output((word, 1))


    def reducer(self, key, records):
        """
        the wordcount reducer, which receives all intermediate records
        for a given word (the key) and adds the corresponding counts
        (the values).
        """

        # total counts for this word
        total = 0

        # loop over records, adding counts to total
        for record in records:
            # extract the fields from the tuple
            word, count = record

            # note: record is a tuple of strings, so explicitly cast
            # to an int here
            total += int(count)

        self.write_output( (word, total) )


if __name__ == '__main__':
    # call the class
    #
    # this reads command line arguments from sys.argv to check for
    # flag indicating which function(s) to perform.
    # 
    # i.e. "-m runs the mapper, -r the reducer, and -l runs the
    # mapper, followed by sort, followed by the reducer"
    WordCount()
    

########NEW FILE########
