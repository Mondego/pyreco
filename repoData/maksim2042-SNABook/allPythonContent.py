__FILENAME__ = generate_acme
import networkx as net

o=net.Graph()

o.add_edge('Conrad','Mary')
o.add_edge('Conrad','Cindy')
o.add_edge('Conrad','Alice')
o.add_edge('Alice','Brad')
o.add_edge('Alice','Angie')
o.add_edge('Alice','Jim')
o.add_edge('Cindy','Samuel')
o.add_edge('Cindy','Dave')
o.add_edge('Cindy','Frida')
net.draw(o)

a=net.Graph()
a.add_edge('Cindy','Samuel')
a.add_edge('Cindy','Conrad')
a.add_edge('Samuel','Frida')
a.add_edge('Conrad','Frida')
a.add_edge('Alice','Frida')
a.add_edge('Angie','Frida')
a.add_edge('Dave','Frida')
a.add_edge('Mary','Frida')
a.add_edge('Brad','Mary')
a.add_node('Jim')
net.draw(a)

net.write_pajek(o,'../chapter1/ACME_orgchart.net')
net.write_pajek(a,'../chapter1/ACME_advice.net')
########NEW FILE########
__FILENAME__ = LJ_fetch
#!/usr/bin/env python
# encoding: utf-8
"""
LJ_fetch.py

Created by Maksim Tsvetovat on 2011-04-28.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import networkx as net
import urllib


def read_lj_friends(g, name):
    # fetch the friend-list from LiveJournal
    response=urllib.urlopen('http://www.livejournal.com/misc/fdata.bml?user='+name)
    for line in response.readlines():
        #Comments in the response start with a '#'
        if line.startswith('#'): continue 
        
        # the format is "< name" (incoming) or "> name" (outgoing)
        parts=line.split()
        
        #make sure that we don't have an empty line
        if len(parts)==0: continue
        
        #add the edge to the network
        if parts[0]=='<': 
            g.add_edge(parts[1],name)
        else:
            g.add_edge(name,parts[1])

def snowball_sampling(g, center, max_depth=1, current_depth=0, taboo_list=[]):
    # if we have reached the depth limit of the search, bomb out.
    print center, current_depth, max_depth, taboo_list
    if current_depth==max_depth: 
        print 'out of depth'
        return taboo_list
    if center in taboo_list:
        print 'taboo' 
        return taboo_list #we've been here before
    else:
        taboo_list.append(center) # we shall never return
        
    read_lj_friends(g, center)
    
    for node in g.neighbors(center):
        taboo_list=snowball_sampling(g, node, current_depth=current_depth+1, max_depth=max_depth, taboo_list=taboo_list)
    
    return taboo_list
    
    







def main():
    g=net.Graph()
#    read_lj_friends(g,'kozel_na_sakse')
    snowball_sampling(g,'kozel_na_sakse')
    

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = draw_triads
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
import triadic

def draw(G,pos,ax):
   for n in G:
       c=Circle(pos[n],radius=0.2,alpha=0.5)
       ax.add_patch(c)
       G.node[n]['patch']=c
   for u,v in G.edges():
       n1=G.node[u]['patch']
       n2=G.node[v]['patch']
       e = FancyArrowPatch(n1.center,n2.center,patchA=n1,patchB=n2,
                           arrowstyle='-|>',
                           connectionstyle='arc3,rad=0.2',
                           mutation_scale=10.0,
                           lw=1, alpha=0.5, color='k')
       ax.add_patch(e)
   ax.text(0.5,0.0,name,transform=ax.transAxes,horizontalalignment='center')
   ax.set_xlim(-1.0,3.0)
   ax.set_ylim(-0.5,1.5)
   plt.axis('equal')
   plt.axis('off')
   return 

t=triadic.triad_graphs()
n=len(t)
pos={'a':(0,0),'b':(1,1),'c':(2,0)}
fig=plt.figure(figsize=(8,2))
fig.subplots_adjust(left=0,right=1,top=1.0)
i=1
for name,graph in sorted(t.items()):
    ax=plt.subplot(2,n/2,i)
    draw(graph,pos,ax)
    i+=1
plt.savefig('triads.png')
plt.draw()
plt.show()

########NEW FILE########
__FILENAME__ = hc
__author__ = """\n""".join(['Maksim Tsvetovat <maksim@tsvetovat.org',
                            'Drew Conway <drew.conway@nyu.edu>',
                            'Aric Hagberg <hagberg@lanl.gov>'])

from collections import defaultdict
import networkx as nx
import numpy
from scipy.cluster import hierarchy
from scipy.spatial import distance
import matplotlib.pyplot as plt


def create_hc(G, t=1.0):
    """
    Creates hierarchical cluster of graph G from distance matrix
    Maksim Tsvetovat ->> Generalized HC pre- and post-processing to work on labelled graphs and return labelled clusters
    The threshold value is now parameterized; useful range should be determined experimentally with each dataset
    """

    """Modified from code by Drew Conway"""
    
    ## Create a shortest-path distance matrix, while preserving node labels
    labels=G.nodes()    
    path_length=nx.all_pairs_shortest_path_length(G)
    distances=numpy.zeros((len(G),len(G))) 
    i=0   
    for u,p in path_length.items():
        j=0
        for v,d in p.items():
            distances[i][j]=d
            distances[j][i]=d
            if i==j: distances[i][j]=0
            j+=1
        i+=1
    
    # Create hierarchical cluster
    Y=distance.squareform(distances)
    Z=hierarchy.complete(Y)  # Creates HC using farthest point linkage
    # This partition selection is arbitrary, for illustrive purposes
    membership=list(hierarchy.fcluster(Z,t=t))
    # Create collection of lists for blockmodel
    partition=defaultdict(list)
    for n,p in zip(list(range(len(G))),membership):
        partition[p].append(labels[n])
    return list(partition.values())



########NEW FILE########
__FILENAME__ = hiclus_blockmodel
__author__ = """\n""".join(['Maksim Tsvetovat <maksim@tsvetovat.org','Drew Conway <drew.conway@nyu.edu>',
                            'Aric Hagberg <hagberg@lanl.gov>'])

from collections import defaultdict
import networkx as nx
import numpy
from scipy.cluster import hierarchy
from scipy.spatial import distance
import matplotlib.pyplot as plt
import hc

"""Draw a blockmodel diagram of a clustering alongside the original network"""


def hiclus_blockmodel(G):
    # Extract largest connected component into graph H
    H=nx.connected_component_subgraphs(G)[0]
    # Create parititions with hierarchical clustering
    partitions=hc.create_hc(H)
    # Build blockmodel graph
    BM=nx.blockmodel(H,partitions)


    # Draw original graph
    pos=nx.spring_layout(H,iterations=100)
    fig=plt.figure(1,figsize=(6,10))
    ax=fig.add_subplot(211)
    nx.draw(H,pos,with_labels=False,node_size=10)
    plt.xlim(0,1)
    plt.ylim(0,1)

    # Draw block model with weighted edges and nodes sized by number of internal nodes
    node_size=[BM.node[x]['nnodes']*10 for x in BM.nodes()]
    edge_width=[(2*d['weight']) for (u,v,d) in BM.edges(data=True)]
    # Set positions to mean of positions of internal nodes from original graph
    posBM={}
    for n in BM:
        xy=numpy.array([pos[u] for u in BM.node[n]['graph']])
        posBM[n]=xy.mean(axis=0)
    ax=fig.add_subplot(212)
    nx.draw(BM,posBM,node_size=node_size,width=edge_width,with_labels=False)
    plt.xlim(0,1)
    plt.ylim(0,1)
    plt.axis('off')
########NEW FILE########
__FILENAME__ = hijackers
#!/usr/bin/env python
# encoding: utf-8
"""
hijackers.py

Created by Maksim Tsvetovat on 2011-08-16.
Copyright (c) 2011 Maksim Tsvetovat. All rights reserved.
"""

import sys
import os

import csv ## we'll use the built-in CSV library
import networkx as net
import multimode as mm
import triadic

# open the file
in_file=csv.reader(open('9_11_edgelist.txt','rb'))

g=net.Graph()
for line in in_file:
    g.add_edge(line[0],line[1],weight=line[2],conf=line[3])
    

#first, let's make sure that all nodes in the graph have the 'flight' attribute
for n in g.nodes_iter(): g.node[n]['flight']='None'

attrb=csv.reader(open('9_11_attrib.txt','rb'))
for line in attrb:
    g.node[line[0]]['flight']=line[1]


# Connected_component_subgraphs() returns a list of components, sorted largest to smallest
components=net.connected_component_subgraphs(g)

# pick the first and largest component
cc = components[0]

# type-string tells the function what attribute to differentiate on
mm.plot_multimode(cc,type_string='flight')

# run triadic analysis
census, node_census = triadic.triadic_census(cc2)
########NEW FILE########
__FILENAME__ = multimode
import networkx as net
import matplotlib.pyplot as plot
from collections import defaultdict

def plot_multimode(m,layout=net.spring_layout, type_string='type', with_labels=True, filename_prefix='',output_type='pdf'):

    ## create a default color order and an empty color-map
    colors=['r','g','b','c','m','y','k']
    colormap={}
    d=net.degree(m)  #we use degree for sizing nodes
    pos=layout(m)  #compute layout 
    
    #Now we need to find groups of nodes that need to be colored differently
    nodesets=defaultdict(list)
    for n in m.nodes():
        try:
            t=m.node[n][type_string]
        except KeyError:
            ##this happens if a node doesn't have a type_string -- give it a None value
            t='None'
        nodesets[t].append(n)
        
    ## Draw each group of nodes separately, using its own color settings
    print "drawing nodes..."
    i=0
    for key in nodesets.keys():
        ns=[d[n]*100 for n in nodesets[key]]
        net.draw_networkx_nodes(m,pos,nodelist=nodesets[key], node_size=ns, node_color=colors[i], alpha=0.6)
        colormap[key]=colors[i]
        i+=1
        if i==len(colors): 
            i=0  ### wrap around the colormap if we run out of colors
    print colormap  
    
    ## Draw edges using a default drawing mechanism
    print "drawing edges..."
    net.draw_networkx_edges(m,pos,width=0.5,alpha=0.5)  
    
    print "drawing labels..."
    if with_labels: 
        net.draw_networkx_labels(m,pos,font_size=12)
    plot.axis('off')
    if filename_prefix is not '':
        plot.savefig(filename_prefix+'.'+output_type)
########NEW FILE########
__FILENAME__ = triadic
"""
Determines the triadic census of a graph
"""
import networkx as nx
__author__ = "\n".join(['Max Tsvetovat (maksim@tsvetovat.org)', 'revised from code by Alex Levenson (alex@isnontinvain.com) and Diederik van Liere (diederik.vanliere@rotman.utoronto.ca)'])

#    (C) Maksim Tsvetovat, 2011

#    Revised from triadic.py by
#    (C) Reya Group: http://www.reyagroup.com
#    Alex Levenson (alex@isnotinvain.com)
#    Diederik van Liere (diederik.vanliere@rotman.utoronto.ca)
#    BSD license.

__all__ = ["triadic_census"]

triad_names = ("003", "012", "102", "021D","021U", "021C", "111D", "111U",
               "030T", "030C", "201", "120D","120U", "120C", "210", "300")
tricodes = (1, 2, 2, 3, 2, 4, 6, 8, 2, 6, 5, 7, 3, 8, 7, 11, 2, 6, 4, 8, 5, 9,
            9, 13, 6, 10, 9, 14, 7, 14, 12, 15, 2, 5, 6, 7, 6, 9, 10, 14, 4, 9,
            9, 12, 8, 13, 14, 15, 3, 7, 8, 11, 7, 12, 14, 15, 8, 14, 13, 15, 
            11, 15, 15, 16)
tricode_to_name = dict((i,triad_names[tricodes[i] - 1])
                       for i in range(len(tricodes)))

def triad_graphs(type=None):
    # Returns dictionary mapping triad names to triad graphs
    def abc_graph():
        g=nx.DiGraph()
        g.add_nodes_from('abc')
        return g
    tg = dict((n, abc_graph()) for n in triad_names)
    tg['012'].add_edges_from([('a','b')])
    tg['102'].add_edges_from([('a','b'),('b','a')])
    tg['102'].add_edges_from([('a','b'),('b','a')])
    tg['021D'].add_edges_from([('b','a'),('b','c')])
    tg['021U'].add_edges_from([('a','b'),('c','b')])
    tg['021C'].add_edges_from([('a','b'),('b','c')])
    tg['111D'].add_edges_from([('a','c'),('c','a'),('b','c')])
    tg['111U'].add_edges_from([('a','c'),('c','a'),('c','b')])
    tg['030T'].add_edges_from([('a','b'),('c','b'),('a''c')])
    tg['030C'].add_edges_from([('b','a'),('c','b'),('a','c')])
    tg['201'].add_edges_from([('a','b'),('b','a'),('a','c'),('c','a')])
    tg['120D'].add_edges_from([('b','c'),('b','a'),('a','c'),('c','a')])
    tg['120C'].add_edges_from([('a','b'),('b','c'),('a','c'),('c','a')])
    tg['120U'].add_edges_from([('a','b'),('c','b'),('a','c'),('c','a')])
    tg['210'].add_edges_from([('a','b'),('b','c'),('c','b'),('a','c'),
                               ('c','a')])
    tg['300'].add_edges_from([('a','b'),('b','a'),('b','c'),('c','b'),
                               ('a','c'),('c','a')])
    return tg

def _tricode(G, v, u, w):
    """This is some fancy magic that comes from Batagelj and Mrvar's paper.
    It treats each link between v,u,w as a bit in the binary representation 
    of an integer. This number then is mapped to one of the 16 triad types.
    """
    combos = ((v, u, 1), (u, v, 2), (v, w, 4), 
              (w, v, 8), (u, w, 16), (w, u, 32))
    return sum(x for u,v,x in combos if v in G[u])

def triadic_census(G):
    """
    Determines the triadic census of a digraph

    Triadic census is a count of how many of the 16 possible types of 
    triad are present in a directed graph.

    Parameters
    ----------
    G : digraph
        A NetworkX DiGraph 
        If a non-directed graph is passed in, it will be converted to a symmetric directed graph

    Returns
    -------
    census : dict
        Dictionary with triad names as keys and number of occurances as values
    
    node_census : dict of dicts
        Dictionary with node IDs as keys, and a triadic census for each node as a value
        The value is a dict with triad names as keys and number of occurances as values

    Notes
    -----
    This algorithm has complexity O(m) where m is the number of edges in the
    graph.

    Refrences
    ---------
    .. [1] Vladimir Batagelj and Andrej Mrvar,  A subquadratic triad 
        census algorithm for large sparse networks with small maximum degree,
        University of Ljubljana,
        http://vlado.fmf.uni-lj.si/pub/networks/doc/triads/triads.pdf
    """
    if not G.is_directed():
        G=nx.DiGraph(G) # convert an undirected graph to a directed graph
        #raise nx.NetworkXError("Not defined for undirected graphs.")
      
    # initialze the count to zero
    census = dict((name, 0) for name in triad_names)
    node_census = dict ((v, dict((name, 0) for name in triad_names)) for v in G.nodes())
    n = len(G)
    m = dict(zip(G, range(n)))
    for v in G:
        vnbrs = set(G.pred[v]) | set(G.succ[v])
        for u in vnbrs:
            if m[u] <= m[v]:
                continue
            neighbors = (vnbrs | set(G.succ[u]) | set(G.pred[u])) - set([u,v])
            # calculate dyadic triads instead of counting them
            if v in G[u] and u in G[v]:
                census["102"] += n - len(neighbors) - 2
                node_census[v]["102"] += n - len(neighbors) - 2
            else:
                census["012"] += n - len(neighbors) - 2
                node_census[v]["012"] += n - len(neighbors) - 2
            # count connected triads
            for w in neighbors:
                if (m[u] < m[w]) or  (m[v] < m[w] and 
                                      m[w] < m[u] and 
                                      not v in G.pred[w] and 
                                      not v in G.succ[w]):
                    code = _tricode(G, v, u, w)
                    census[tricode_to_name[code]] += 1
                    node_census[v][tricode_to_name[code]] += 1

    # null triads = total number of possible triads - all found triads        
    census["003"] = ((n * (n - 1) * (n - 2)) / 6) - sum(census.values())
    return census, node_census


########NEW FILE########
__FILENAME__ = crunchbase
import networkx as net
import urllib
import json

cp=net.DiGraph() #company to person
ci=net.DiGraph() #company to investor
cc=net.DiGraph() #company to company -- competitors


def get_company(cp,ci,cc,name):

name='twitter'    
response=urllib.urlopen('http://api.crunchbase.com/v/1/company/'+name+'.js')
s=""
for l in response.readlines() : s=s+l
js=json.loads(s)
print len(s), len(js), len(js['relationships'])
##get the list of employees, competitors and investor
for e in js['relationships']:
    person=e['person']['permalink']
    cp.add_edge(name,person)
    
for c in js['competitions']:
    company = c['competitor']['permalink']
    cc.add_edge(name,company)
    
for round in js['funding_rounds']:
    for i in round['investments']:
        investor=i['financial_org']
        if investor != None:    
            ci.add_edge(name,investor['permalink'])
    
########NEW FILE########
__FILENAME__ = two_mode
#!/usr/bin/env python
# encoding: utf-8
"""
two_mode.py

Created by Maksim Tsvetovat on 2011-08-17.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import csv 
import math
import networkx as net
import matplotlib.pyplot as plot

## Import bi-partite (bi-modal) functions
from networkx.algorithms import bipartite as bi

def trim_edges(g, weight=1):
	g2=net.Graph()
	for f, to, edata in g.edges(data=True):
		if edata['weight'] > weight:
			g2.add_edge(f,to,edata)
	return g2


## Read the data from a CSV file
## We use the Universal new-line mode since many CSV files are created with Excel
r=csv.reader(open('campaign_short.csv','rU'))

## 2-mode graphs are usually directed. Here, their direction implies money flow
g=net.Graph()

## we need to keep track separately of nodes of all types
pacs=[]
candidates=[]

## Construct a directed graph from edges in the CSV file
for row in r: 
    if row[0] not in pacs: 
        pacs.append(row[0])
    if row[12] not in candidates: 
        candidates.append(row[12])
    g.add_edge(row[0],row[12], weight=int(row[10]))
    
## compute the projected graph
pacnet=bi.weighted_projected_graph(g, pacs, ratio=False)
pacnet=net.connected_component_subgraphs(pacnet)[0]
weights=[math.log(edata['weight']) for f,t,edata in pacnet.edges(data=True)]

net.draw_networkx(p,width=weights, edge_color=weights)



## Compute the candidate network
cannet=bi.weighted_projected_graph(g, candidates, ratio=False)
cannet=net.connected_component_subgraphs(cannet)[0]
weights=[math.log(edata['weight']) for f,t,edata in cannet.edges(data=True)]
plot.figure(2) ## switch to a fresh canvas
net.draw_networkx(cannet,width=weights, edge_color=weights)


plot.figure(3)
plot.hist(weights)

## The weights histogram is logarithmic; we should compute the original weight = e^log_weight
cannet_trim=trim_edges(cannet, weight=math.exp(0.9))

plot.figure(4)
## re-calculate weights based on the new graph
weights=[edata['weight'] for f,t,edata in cannet_trim.edges(data=True)]
net.draw_networkx(cannet_trim,width=weights, edge_color=weights)
########NEW FILE########
__FILENAME__ = construct
#!/usr/bin/env python
# encoding: utf-8
"""
friedkin.py

Created by Maksim Tsvetovat on 2011-08-08.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import networkx as net
import matplotlib.pyplot as plot
import matplotlib.colors as colors
import random as r

class Person(object):
    
    def __init__(self, id):
        #Start with a single initial preference
        self.id=id
        self.i = r.random()
        self.a = self.i
        #we value initial opinion and subsequent information equally
        self.alpha=0.9
    
    def __str__(self):
        return(str(self.id))
        
    def _roulette_choice(self,names,values, inverse=False):
        """ 
            roulette method makes unequally weighted choices based on a set of values
            Names and values should be lists of equal lengths
            values are between 0 and 1
            if inverse=False, names with higher values have a higher probability of being chosen; 
            if inverse=True, names with lower values have hight probability
            
        """
        wheel=names
        for i in range(len(names)):
            if not inverse:
                wheel.extend([names[i] for x in range(1+int(values[i]*10))])
            else:
                wheel.extend([names[i] for x in range(1+int((1-values[i])*10))])
        return(r.choice(wheel))
        

    def interact(self):
        """
            instead of looking at all of the neighbors, let's pick a random node and exchange information with him
            this will create an edge and weigh it with their similarity.
            
            Phase II -- make roulette choice instead of random choice
        """
        neighbors=g[self].keys()
        values=[v['weight'] for v in g[self].values()]
        
        ## roll dice and decide to communicate with similar (0.6), dissimilar(0.3) or random (0.1)
        roll=r.random()
        if r <= 0.1 or len(neighbors)==0:
            partner=r.choice(g.nodes())
        elif r<=0.1:
            partner=self._roulette_choice(neighbors,values,inverse=True)
        else:
            partner=self._roulette_choice(neighbors,values,inverse=False)
        
        w=0.5
        s=self.a*w + partner.a*w
        # update my beliefs = initial belief plus sum of all influences
        self.a=(1-self.alpha)*self.i + self.alpha*s
        g.add_edge(self,partner,weight=(1-self.a-partner.a))
        


def consensus(g):
    """
    Calculcate consensus opinion of the graph
    """
    aa=[n.a for n in g.nodes()]
    return min(aa),max(aa),sum(aa)/len(aa)

def trim_edges(g, weight=1):
    g2=net.Graph()
    for f, to, edata in g.edges(data=True):
        if edata != {}:
            if edata['weight'] > weight:
                g2.add_edge(f,to,edata)
    return g2

density=0.05
decay_rate=0.01
network_size=100
runtime=200
g=net.Graph()


## create a network of Person objects
for i in range(network_size):
    p=Person(i)
    g.add_node(p)

##this will be a simple random graph, with random weights
for x in g.nodes():
    for y in g.nodes():
        if r.random()<=density: g.add_edge(x,y,weight=r.random())

col=[n.a for n in g.nodes()]
pos=net.spring_layout(g)
net.draw_networkx(g,pos=pos, node_color=col,cmap=plot.cm.Reds)

cons=[]
for i in range(runtime):
    for node in g.nodes():
        node.interact()

    #degrade edge weights by a fixed rate
    for f,t,data in g.edges(data=True):
        data['weight']=data['weight']*(1-decay_rate)
        if data['weight']<0.1: g.remove_edge(f,t)

    col=[n.a for n in g.nodes()] 
    ew=[1000*edata['weight'] for f,to,edata in g.edges(data=True)]  
    plot.figure(2)
    plot.plot(col)   
    
    cons.append(consensus(g))
 
plot.figure(i)
g2=trim_edges(g, weight=0.3)
col=[n.a for n in g2.nodes()]
net.draw_networkx(g2,node_color=col, cmap=plot.cm.Reds) #,edge_color=ew,edge_cmap=plot.cm.RdPu)

plot.figure(i+1)
plot.plot(cons)

########NEW FILE########
__FILENAME__ = friedkin
#!/usr/bin/env python
# encoding: utf-8
"""
friedkin.py

Created by Maksim Tsvetovat on 2011-08-08.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import networkx as net
import matplotlib.pyplot as plot
import matplotlib.colors as colors
import random as r

class Person(object):
    
    def __init__(self, id):
        #Start with a single initial preference
        self.id=id
        self.i = r.random()
        self.a = self.i
        #we value initial opinion and subsequent information equally
        self.alpha=0.9
    
    def __str__(self):
        return(str(self.id))
        
    def step(self):
        #loop through the neighbors and aggregate their preferences
        neighbors=g[self]
        #all nodes in the list of neighbors are equally weighted, including self
        w=1/float((len(neighbors)+1))
        s=w*self.a
        for node in neighbors:
            s+=w*node.a

        # update my beliefs = initial belief plus sum of all influences
        self.a=(1-self.alpha)*self.i + self.alpha*s


class Influencer(Person):
    def __init__(self,id):
        self.id=id
        self.i = r.random()
        self.a = 1 ## opinion is strong and immovable
    
    def step(self):
        pass

density=0.6
g=net.Graph()

time=100

## create a network of Person objects
for i in range(10):
    p=Person(i)
    g.add_node(p)

##this will be a simple random graph
for x in g.nodes():
    for y in g.nodes():
        if r.random()<=density: g.add_edge(x,y)


influencers=4
connections=4
##add the influencers to the network and connect each to 3 other nodes
for i in range(influencers):
    inf=Influencer("Inf"+str(i))
    for x in range(connections):
        g.add_edge(r.choice(g.nodes()), inf)
    
            

col=[n.a for n in g.nodes()]
pos=net.spring_layout(g)
net.draw_networkx(g,pos=pos, node_color=col,cmap=plot.cm.Reds)
plot.figure(2)

for i in range(time):
    for node in g.nodes():
        node.step()
    
    col=[n.a for n in g.nodes()]  
    print col  
    plot.plot(col)    
plot.figure(i)
net.draw_networkx(g, pos=pos ,node_color=col, cmap=plot.cm.Reds)
    


########NEW FILE########
__FILENAME__ = sqlgraph
from functools import wraps

__author__ = "Alex Kouznetsov"

import networkx
import sqlite3
import simplejson
import base64

def _prepare_tables(conn, name):
    c = conn.cursor()
    c.execute('''drop table if exists "%s_edges"''' % name)
    c.execute('''drop table if exists "%s_nodes"''' % name)
    c.execute('''create table "%s_nodes" (node, attributes)''' % name)
    c.execute('''create table "%s_edges" (efrom, eto, attributes)''' % name)
    conn.commit()
    c.close()

def write_sqlite(G, sqlfile):
    ''' Graphs with same names will overwrite each other'''
    sq = SqlGraph(sqlfile, G.name)
    sq.from_nx(G)
    return sq

def read_sqlite(sqlfile, name):
    sq = SqlGraph(sqlfile, name)
    return sq.to_nx()

def _encode(name):
    ''' Before using graph names in tables we need to convert
    to something that won't upset sqlite.'''
    return base64.encodestring(name).replace('\n', '')

def _decode(name):
    return base64.decodestring(name)

def cursored(func):
    @wraps(func)
    def wrapper(sqlgraph, *args, **kwargs):
        supplied_cursor = kwargs.get('cursor', None)
        cursor = supplied_cursor or sqlgraph.conn.cursor()
        kwargs['cursor'] = cursor
        result = func(sqlgraph, *args, **kwargs)
        if not supplied_cursor:
            cursor.connection.commit()
            cursor.close()
        return result
    return wrapper


class SqlGraph(object):
    def __init__(self, sqlfile, name):
        self.conn = sqlite3.connect(sqlfile)
        self.name = _encode(name)

    @cursored
    def add_node(self, node, attr_dict=None, cursor=None):
        attributes = simplejson.dumps(attr_dict)
        cursor.execute('''insert or replace into "%s_nodes" (node, attributes)
            values(?,?)''' % self.name, (node, attributes))

    @cursored
    def add_edge(self, fromnode, tonode, attr_dict=None, cursor=None):
        attributes = simplejson.dumps(attr_dict)
        cursor.execute('''insert or replace into "%s_edges" (efrom, eto, attributes)
            values(?,?,?)''' % self.name, (fromnode, tonode, attributes))

    @cursored
    def remove_node(self, node, cursor=None):
        cursor.execute('delete from "%s_nodes" where node=?' % self.name, (node,))

    @cursored
    def remove_edge(self, fromnode, tonode, cursor=None):
        cursor.execute('delete from "%s_edges" where efrom=? and eto=?' % self.name, (fromnode, tonode))

    @cursored
    def get_node_data(self, node, cursor=None):
        result = cursor.execute('select * from "%s_nodes" where node=?'%self.name, (node,))
        for row in result:
            return row[0]
        else:
            raise Exception('Node %s is not in graph.' % node)

    @cursored
    def get_edge_data(self, fromnode, tonode, cursor=None):
        result = cursor.execute('select * from "%s_edges" where efrom=? and eto=?' % self.name, (fromnode, tonode))
        for row in result:
            return row[0]
        else:
            raise Exception('Edge %s:%s is not in graph.' % (fromnode, tonode))

    def from_nx(self, G):
        self.name = _encode(G.name)
        _prepare_tables(self.conn, self.name)
        c = self.conn.cursor()
        for node, attr_dict in G.node.items():
            self.add_node(node, attr_dict, cursor=c)
        for efrom, eto, attr_dict in G.edges(data=True):
            self.add_edge(efrom, eto, attr_dict, cursor=c)
        self.conn.commit()
        c.close()

    def to_nx(self):
        G = networkx.Graph()
        c = self.conn.cursor()
        for row in c.execute('select * from "%s_nodes"' % self.name):
            G.add_node(row[0], attr_dict=simplejson.loads(row[1]))
        for row in c.execute('select * from "%s_edges"' % self.name):
            G.add_edge(row[0], row[1], attr_dict=simplejson.loads(row[2]))
        self.conn.commit()
        c.close()
        G.name = _decode(self.name)
        return G

########NEW FILE########
__FILENAME__ = scrape_crunchbase
import networkx as net

import requests
import simplejson as json

from collections import deque

comp=net.Graph()
base_url='http://api.crunchbase.com/v/1/company/'
ext='.js'
company='facebook'

q=deque()
visited=[]
q.append(company)

while len(q)>0:
    firm=q.popleft()
    url=base_url+firm+ext
    visited.append(firm)
    
    print firm, url 
    resp=requests.get(url)
    data=json.loads(resp.content)


    for c in data['competitions']:
        comp.add_edge(firm,c['competitor']['name'])
        if c['competitor']['name'] not in visited:
            q.append(c['competitor']['permalink'])
    
########NEW FILE########
__FILENAME__ = collect
import tweepy

# First, the basics

"""
Consumer key 	wADh1LqyQCR3OmEGqK3SDg
Consumer secret 	FzKWL6bMfL6oHvHwh9daANHuSScXua5K386513FbU6c
Request token URL 	https://api.twitter.com/oauth/request_token
Authorize URL 	https://api.twitter.com/oauth/authorize
Access token URL 	https://api.twitter.com/oauth/access_token
Access token 	153439378-AuXJgQ8oHmnY0JSabav6kGNoVg5iOB7t9CF3B3cF
Access token secret 	LKm3AlD0fhCE4ofZXYZALxtsMNBaRqXmJWiTgUT1Jlo
"""

access_token='153439378-AuXJgQ8oHmnY0JSabav6kGNoVg5iOB7t9CF3B3cF'
access_token_secret='LKm3AlD0fhCE4ofZXYZALxtsMNBaRqXmJWiTgUT1Jlo'


def connect():
	auth = tweepy.OAuthHandler("myAuthToken",access_token)
	auth.set_access_token("myAccessToken", access_token_secret)
	api = tweepy.API(auth)
	if api and api.verity_credentials():
		return api
	else:
		print("Login failed.")



query = '"someScreenName" OR "#sometag"' # a valid Twitter search query

def run_search(query = query):
	q = {
		'q': query,
		'lang': 'en',
	}
	
	api = connect()
	try:
		for status in Cursor(api.search, **q).items():
			process_tweet(status)
	except TweepError:
		traceback.print_exc()
		raise
########NEW FILE########
__FILENAME__ = collect_stream
import tweepy

class MyStreamListener(tweepy.StreamListener):
    def on_error(self, status_code):
        print 'An error has occured! Status code %s.' % status_code
        return True # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'
        time.sleep(10)
        return True

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        #print "Delete notice for %s. %s" % (status_id, user_id)
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        print "!!! Limitation notice received: %s" % str(track)
        return
        
    def on_status(self, status):
        process_tweet(status)
    	   return True # or False if you want the stream to disconnect


def start_stream(username, password, listener, follow=(), track=():
	'''	
         follow: list of users to follow
		track: list of keywords to track
    '''
	print 'Connecting as %s/%s' % (username, password)
	stream = tweepy.Stream(username, password, listener, timeout=60)
	if follow or track:
		print "Starting filter on %s/%s" % (','.join(follow), ','.join(track))
		stream.filter(follow=follow, track=track, async=True)
	else:
		print "Starting sample"
		stream.sample(async=True)

# Process a sample stream:

listener = MyStreamListener()
start_stream("myusername","mypassword",listener)
########NEW FILE########
__FILENAME__ = commands
                               
>>> len(retweets)
>>> net.draw(retweets)
>>> undir_retweets=retweets.to_undirected()
>>> comps=net.connected_component_subgraphs(undir_retweets)
>>> len(comps)
>>> len(comps[0])
>>> net.draw(comps[0])

degrees=net.degree(comps[0])

degrees=sorted_degree(comps[0])
degrees[:10] 

plot.hist(net.degree(comps[0]).values(),50)

core=trim_degrees(comps[0])

len(core)
2836

len(hashtag_net)
1753

net.draw(hashtag_net)

core=net.connected_component_subgraphs(hashtag_net)[0]
net.draw(core)

core.remove_node('earthquake')
core2=trim_edges(hashtag_net, weight=2)
net.draw(core2)

core3=trim_edges(hashtag_net, weight=10)
net.draw(core3)
########NEW FILE########
__FILENAME__ = webcast
import json
import heatmap
import networkx as net
import matplotlib.pyplot as plot

def trim_degrees(g, degree=1):
    """
    Trim the graph by removing nodes with degree less then value of the degree parameter
    Returns a copy of the graph, so it's non-destructive.
    """
    g2=g.copy()
    d=net.degree(g2)
    for n in g2.nodes():
        if d[n]<=degree: g2.remove_node(n)
    return g2

def sorted_degree(g):
    d=net.degree(g)
    ds = sorted(d.iteritems(), key=lambda (k,v): (-v,k))
    return ds

def add_or_inc_edge(g,f,t):
    """
    Adds an edge to the graph IF the edge does not exist already. 
    If it does exist, increment the edge weight.
    Used for quick-and-dirty calculation of projected graphs from 2-mode networks.
    """
    if g.has_edge(f,t):
        g[f][t]['weight']+=1
    else:
        g.add_edge(f,t,weight=1)
        
def trim_edges(g, weight=1):
    """
    Remove edges with weights less then a threshold parameter ("weight")
    """
    g2=net.Graph()
    for f, to, edata in g.edges(data=True):
        if edata['weight'] > weight:
            g2.add_edge(f,to,edata)
    return g2

file="data.json"
i = open(file,'rb')

retweets=net.DiGraph()
hashtag_net=net.Graph()

for tweet in i:
    js=json.loads(tweet)
    
    ### process tweet to extract information
    try:
        author=js['user']['screen_name']
        entities=js['entities']
        mentions=entities['user_mentions']
        hashtags=entities['hashtags']
    
        for rt in mentions:
            alter=rt['screen_name']
            retweets.add_edge(author,alter)
        
        tags=[tag['text'].lower() for tag in hashtags]
        for t1 in tags:
            for t2 in tags:
                if t1 is not t2:
                    add_or_inc_edge(hashtag_net,t1,t2)      
    except KeyError:
        print ':-('
        continue
    
    

########NEW FILE########
__FILENAME__ = webcast
import networkx as net
import matplotlib.pyplot as plot
import math
import csv 

file="retweets.txt"

g=net.Graph() #create a blank graph

reader=csv.reader(open(file,'rb'),delimiter=' ')
for line in reader:
    g.add_edge(line[0],line[1],weight=int(line[2]))
    

"""    
    In [17]: len(g)
    Out[17]: 129461
"""

components=net.connected_component_subgraphs(g)

"""
In [21]: len(components)
Out[21]: 17202
"""

l=[len(c) for c in components]

"""
In [24]: l[:10]
Out[24]: 
[65044,
 204,
 103,
 81,
 77,
 72,
 71,
 68,
 64,
 60]
 
net.draw(components[1])
"""

g1=components[0]
degree=net.degree(g1)

weights=[edata['weight'] for f,t,edata in g1.edges(data=True)]
hist=plot.hist(weights,100)


def trim_edges(g, weight=1):
    """
    Remove edges with weights less then a threshold parameter ("weight")
    """
    g2=net.Graph()
    for f, to, edata in g.edges(data=True):
        if edata['weight'] > weight:
            g2.add_edge(f,to,edata)
    return g2

"""
In [74]: g2=trim_edges(g1)
In [75]: len(g2)
Out[75]: 24657

In [78]: g2=trim_edges(g1, weight=2)
In [79]: len(g2)
Out[79]: 16451
....
In [82]: g2=trim_edges(g1, weight=10)
In [84]: len(g2)
Out[84]: 3357

In [91]: g3=net.connected_component_subgraphs(g2)[0]
In [92]: len(g3)
Out[92]: 1461
"""

degree=net.degree(g3)
pos=net.spring_layout(g3)
ns=[degree[n]*100 for n in g3.nodes()]
net.draw_networkx(g3,pos=pos,node_size=ns,with_labels=False)

def sorted_degree(g):
    d=net.degree(g)
    ds = sorted(d.iteritems(), key=lambda (k,v): (-v,k))
    return ds
    


"""
In [127]: ds=sorted_degree(g3)

In [128]: ds[:10]
Out[128]: 
[('alarabiya_ar', 97),
 ('AJArabic', 50),
 ('Shorouk_News', 44),
 ('Ghonim', 35),
 ('AJEnglish', 34),
 ('AlArabiya_Eng', 33),
 ('AymanM', 30),
 ('monaeltahawy', 26),
 ('EANewsFeed', 21),
 ('HGhazaryan', 20)]
"""

def sorted_map(dct):
    ds = sorted(dct.iteritems(), key=lambda (k,v): (-v,k))
    return ds
    
btw=net.betweenness_centrality(g3)
ns=[btw[n]*1000+10 for n in g3.nodes()]
net.draw_networkx(g3,pos=pos,node_size=ns,with_labels=False)

bs=sorted_map(btw)
bs[:10]

"""
[('Ghonim', 0.30948683318099868),
 ('alarabiya_ar', 0.22141480094013333),
 ('monaeltahawy', 0.21103708928780715),
 ('shary20', 0.21082511576960963),
 ('dadlani', 0.16175663741677401),
 ('AJArabic', 0.13889259139494639),
 ('Reza_Kahlili', 0.12907330369968981),
 ('CFHeather', 0.12113052931463912),
 ('WSJ', 0.12103851658308157),
 ('PERSIA_MAX_NEWS', 0.12016294134886295)]"""

pr=net.pagerank(g3)
ns=[pr[n]*1000+10 for n in g3.nodes()]
net.draw_networkx(g3,pos=pos,node_size=ns,with_labels=False)

prs=sorted_map(btw)
prs[:10]

"""
[('Ghonim', 0.30948683318099868),
 ('alarabiya_ar', 0.22141480094013333),
 ('monaeltahawy', 0.21103708928780715),
 ('shary20', 0.21082511576960963),
 ('dadlani', 0.16175663741677401),
 ('AJArabic', 0.13889259139494639),
 ('Reza_Kahlili', 0.12907330369968981),
 ('CFHeather', 0.12113052931463912),
 ('WSJ', 0.12103851658308157),
 ('PERSIA_MAX_NEWS', 0.12016294134886295)]

"""

########NEW FILE########
__FILENAME__ = english_stoplist
#!/usr/bin/env python
# encoding: utf-8
"""
english_stoplist.py

Created by Maksim Tsvetovat on 2011-12-08.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import string

stoplist_str="""
a
a's
able
about
above
according
accordingly
across
actually
after
afterwards
again
against
ain't
all
allow
allows
almost
alone
along
already
also
although
always
am
among
amongst
an
and
another
any
anybody
anyhow
anyone
anything
anyway
anyways
anywhere
apart
appear
appreciate
appropriate
are
aren't
around
as
aside
ask
asking
associated
at
available
away
awfully
b
be
became
because
become
becomes
becoming
been
before
beforehand
behind
being
believe
below
beside
besides
best
better
between
beyond
both
brief
but
by
c
c'mon
c's
came
can
can't
cannot
cant
cause
causes
certain
certainly
changes
clearly
co
com
come
comes
concerning
consequently
consider
considering
contain
containing
contains
corresponding
could
couldn't
course
currently
d
definitely
described
despite
did
didn't
different
do
does
doesn't
doing
don't
done
down
downwards
during
e
each
edu
eg
eight
either
else
elsewhere
enough
entirely
especially
et
etc
even
ever
every
everybody
everyone
everything
everywhere
ex
exactly
example
except
f
far
few
fifth
first
five
followed
following
follows
for
former
formerly
forth
four
from
further
furthermore
g
get
gets
getting
given
gives
go
goes
going
gone
got
gotten
greetings
h
had
hadn't
happens
hardly
has
hasn't
have
haven't
having
he
he's
hello
help
hence
her
here
here's
hereafter
hereby
herein
hereupon
hers
herself
hi
him
himself
his
hither
hopefully
how
howbeit
however
i
i'd
i'll
i'm
i've
ie
if
ignored
immediate
in
inasmuch
inc
indeed
indicate
indicated
indicates
inner
insofar
instead
into
inward
is
isn't
it
it'd
it'll
it's
its
itself
j
just
k
keep
keeps
kept
know
knows
known
l
last
lately
later
latter
latterly
least
less
lest
let
let's
like
liked
likely
little
look
looking
looks
ltd
m
mainly
many
may
maybe
me
mean
meanwhile
merely
might
more
moreover
most
mostly
much
must
my
myself
n
name
namely
nd
near
nearly
necessary
need
needs
neither
never
nevertheless
new
next
nine
no
nobody
non
none
noone
nor
normally
not
nothing
novel
now
nowhere
o
obviously
of
off
often
oh
ok
okay
old
on
once
one
ones
only
onto
or
other
others
otherwise
ought
our
ours
ourselves
out
outside
over
overall
own
p
particular
particularly
per
perhaps
placed
please
plus
possible
presumably
probably
provides
q
que
quite
qv
r
rather
rd
re
really
reasonably
regarding
regardless
regards
relatively
respectively
right
s
said
same
saw
say
saying
says
second
secondly
see
seeing
seem
seemed
seeming
seems
seen
self
selves
sensible
sent
serious
seriously
seven
several
shall
she
should
shouldn't
since
six
so
some
somebody
somehow
someone
something
sometime
sometimes
somewhat
somewhere
soon
sorry
specified
specify
specifying
still
sub
such
sup
sure
t
t's
take
taken
tell
tends
th
than
thank
thanks
thanx
that
that's
thats
the
their
theirs
them
themselves
then
thence
there
there's
thereafter
thereby
therefore
therein
theres
thereupon
these
they
they'd
they'll
they're
they've
think
third
this
thorough
thoroughly
those
though
three
through
throughout
thru
thus
to
together
too
took
toward
towards
tried
tries
truly
try
trying
twice
two
u
un
under
unfortunately
unless
unlikely
until
unto
up
upon
us
use
used
useful
uses
using
usually
uucp
v
value
various
very
via
viz
vs
w
want
wants
was
wasn't
way
we
we'd
we'll
we're
we've
welcome
well
went
were
weren't
what
what's
whatever
when
whence
whenever
where
where's
whereafter
whereas
whereby
wherein
whereupon
wherever
whether
which
while
whither
who
who's
whoever
whole
whom
whose
why
will
willing
wish
with
within
without
won't
wonder
would
would
wouldn't
x
y
yes
yet
you
you'd
you'll
you're
you've
your
yours
yourself
yourselves
z
zero
rt
via
"""

stoplist=[w.strip() for w in stoplist_str.split('\n') if w !='']

########NEW FILE########
__FILENAME__ = process_tweets
#!/usr/bin/env python
# encoding: utf-8
"""
reprocess.py

Created by Maksim Tsvetovat on 2012-02-15.
Copyright (c) 2012 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import simplejson as json 
from dateutil import parser
import networkx as net


def add_or_inc_edge(g,f,t):
    """
    Adds an edge to the graph IF the edge does not exist already. 
    If it does exist, increment the edge weight.
    Used for quick-and-dirty calculation of projected graphs from 2-mode networks.
    """
    if g.has_edge(f,t):
        g[f][t]['weight']+=1
    else:
        g.add_edge(f,t,weight=1)



tweet_dir='tweet_data/'
filez=os.listdir(tweet_dir)
g=net.DiGraph()
for file in filez:
#file=filez[0]
    f_in=open(tweet_dir+file,'rb')
    
    print "<<<<"+file+">>>>>"
    ### each line in the file corresponds to 1 tweet in a raw format
    ### we will build retweet networks from the at-tags in the file
    for line in f_in:
        try:
            tweet=json.loads(line)
        except:
            ##some JSON records are malformed. Skip them
            continue
        
        ## harvest attags from the JSON structure; skip tweet if there is an error
        try:
            author=tweet['user']['screen_name']
            attags=tweet['entities']['user_mentions']
            ret_from=tweet['in_reply_to_screen_name']
        except:
            continue
        
        if ret_from:
            print author, ret_from
            add_or_inc_edge(g,author,ret_from)

        for attag in attags:
            print author, attag['screen_name']
            add_or_inc_edge(g,author,attag['screen_name'])
        
    
        print '.',
    print "@@@@@"
########NEW FILE########
__FILENAME__ = states
#!/usr/bin/env python
# encoding: utf-8
"""
states.py

Created by Maksim Tsvetovat on 2012-01-02.
Copyright c 2012 __MyCompanyName__. All rights reserved.
"""

states=sorted(['AL', 'MT',
 'AK', 'NE',
 'AZ', 'NV',
 'AR', 'NH',
 'CA', 'NJ',
 'CO', 'NM',
 'CT', 'NY',
 'DE', 'NC',
 'FL', 'ND',
 'GA', 'OH',
 'HI', 'OK',
 'ID', 'OR',
 'IL', 'PA',
 'IN', 'RI',
 'IA', 'SC',
 'KS', 'SD',
 'KY', 'TN',
 'LA', 'TX',
 'ME', 'UT',
 'MD', 'VT',
 'MA', 'VA',
 'MI', 'WA',
 'MN', 'WV',
 'MS', 'WI',
 'MO', 'WY'])
 
 
########NEW FILE########
__FILENAME__ = tutorial
import networkx as net
import process_tweets

retweets=process_tweets.g

len(retweets)

retweets.remove_edges_from(retweets.selfloop_edges())
undir=net.to_networkx_graph(retweets)
core=net.k_core(undir)

len(core)

net.draw(core)


########NEW FILE########
__FILENAME__ = multimode
import networkx as net
import matplotlib.pyplot as plot
from collections import defaultdict

def plot_multimode(m,layout=net.spring_layout, type_string='type', with_labels=True, filename_prefix='',output_type='pdf'):

    ## create a default color order and an empty color-map
    colors=['r','g','b','c','m','y','k']
    colormap={}
    d=net.degree(m)  #we use degree for sizing nodes
    pos=layout(m)  #compute layout 
    
    #Now we need to find groups of nodes that need to be colored differently
    nodesets=defaultdict(list)
    for n in m.nodes():
        try:
            t=m.node[n][type_string]
        except KeyError:
            ##this happens if a node doesn't have a type_string -- give it a None value
            t='None'
        nodesets[t].append(n)
        
    ## Draw each group of nodes separately, using its own color settings
    print "drawing nodes..."
    i=0
    for key in nodesets.keys():
        #ns=[d[n]*100 for n in nodesets[key]]
        net.draw_networkx_nodes(m,pos,nodelist=nodesets[key], node_color=colors[i], alpha=0.6) #node_size=ns,
        colormap[key]=colors[i]
        i+=1
        if i==len(colors): 
            i=0  ### wrap around the colormap if we run out of colors
    print colormap  
    
    ## Draw edges using a default drawing mechanism
    print "drawing edges..."
    net.draw_networkx_edges(m,pos,width=0.5,alpha=0.5)  
    
    print "drawing labels..."
    if with_labels: 
        net.draw_networkx_labels(m,pos,font_size=12)
    plot.axis('off')
    if filename_prefix is not '':
        plot.savefig(filename_prefix+'.'+output_type)
########NEW FILE########
__FILENAME__ = pac_types
pac_types_str="""
C = Communication Cost
D = Delegate
E = Electioneering Communication
H = House
I = Independent Expenditor (Person or Group)
N = PAC - Nonqualified
O = Independent Expenditure-Only (Super PACs)
P = Presidential
Q = PAC - Qualified
S = Senate
U = Single Candidate Independent Expenditure
X = Party Nonqualified
Y = Party Qualified
Z = National Party Nonfederal Account 
""".replace(' = ','=').strip().split('\n')

pac_types=dict([tuple(row.split('=')) for row in pac_types_str])
########NEW FILE########
__FILENAME__ = two_mode
#!/usr/bin/env python
# encoding: utf-8
"""
two_mode.py

Created by Maksim Tsvetovat on 2011-08-17.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import csv 
import math
import networkx as net
import matplotlib.pyplot as plot

## Import bi-partite (bi-modal) functions
from networkx.algorithms import bipartite as bi

def trim_edges(g, weight=1):
	g2=net.Graph()
	for f, to, edata in g.edges(data=True):
		if edata['weight'] > weight:
			g2.add_edge(f,to,edata)
	return g2


## Read the data from a CSV file
## We use the Universal new-line mode since many CSV files are created with Excel
r=csv.reader(open('campaign_short.csv','rU'))

## 2-mode graphs are usually directed. Here, their direction implies money flow
g=net.Graph()

## we need to keep track separately of nodes of all types
pacs=[]
candidates=[]

## Construct a directed graph from edges in the CSV file
for row in r: 
    if row[0] not in pacs: 
        pacs.append(row[0])
    if row[12] not in candidates: 
        candidates.append(row[12])
    g.add_edge(row[0],row[12], weight=int(row[10]))
    
## compute the projected graph
pacnet=bi.weighted_projected_graph(g, pacs, ratio=False)
pacnet=net.connected_component_subgraphs(pacnet)[0]
weights=[math.log(edata['weight']) for f,t,edata in pacnet.edges(data=True)]

net.draw_networkx(p,width=weights, edge_color=weights)



## Compute the candidate network
cannet=bi.weighted_projected_graph(g, candidates, ratio=False)
cannet=net.connected_component_subgraphs(cannet)[0]
weights=[math.log(edata['weight']) for f,t,edata in cannet.edges(data=True)]
plot.figure(2) ## switch to a fresh canvas
net.draw_networkx(cannet,width=weights, edge_color=weights)


plot.figure(3)
plot.hist(weights)

## The weights histogram is logarithmic; we should compute the original weight = e^log_weight
cannet_trim=trim_edges(cannet, weight=math.exp(0.9))

plot.figure(4)
## re-calculate weights based on the new graph
weights=[edata['weight'] for f,t,edata in cannet_trim.edges(data=True)]
net.draw_networkx(cannet_trim,width=weights, edge_color=weights)
########NEW FILE########
__FILENAME__ = webcast
import networkx as net
from networkx.algorithms import bipartite as bi

from collections import Counter

candidates={}
can_file=open('2012/foiacn.txt','rb')
for line in can_file:
    cid=line[0:9]
    name=line[9:47].strip()
    party=line[47:50]
    inc=line[56]
    zip=line[147:152]
    candidates[cid]={'name':name,'party':party,'type':ctype,'inc':inc,'zip':zip}

[(k,pacs[k]) for k in pacs.keys()[:10]]

ctype_counter=Counter()
for can in candidates.values():
    ctype_counter[can['type']]+=1
ctype_counter

from pac_types import pac_types
pacs={}
pac_file=open('2012/foiacm.txt','rb')
for line in pac_file:
    pid=line[0:9]
    ctype=line[0]
    name=line[9:99].strip()
    party=line[232-235]
    ctype=line[231]
    zip=line[225:230]
    pacs[pid]={'name':name,'party':party,'type':ctype,'zip':zip}

ctype_counter=Counter()
for pac in pacs.values():
    ctype_counter[pac['type']]+=1
ctype_counter


g=net.Graph()
can_list=[]
pac_list=[]
contrib=open('2012/itpas2.txt','rb')
for line in contrib:
    pid=line[0:9]
    cid=line[52:61]
    #amt=int(line[36:43])
    g.add_edge(pid,cid)
    if cid not in can_list: can_list.append(cid)
    if pid not in pac_list: pac_list.append(pid)
    if pid in pacs: 
        g.node[pid]=pacs[pid]
    else:
        pacs[pid]={'type':'unknown'}
    if cid in candidates: 
        g.node[cid]=candidates[cid]
    else:
        candidates[cid]={'type':'unknown'}
        

cannet=bi.weighted_projected_graph(g, can_list, ratio=False)

def trim_edges(g, weight=1):
	g2=net.Graph()
	for f, to, edata in g.edges(data=True):
		if edata['weight'] > weight:
			g2.add_edge(f,to,edata)
			g2.node[f]=g.node[f]
			g2.node[to]=g.node[to]
	return g2

import multimode as mm

cancore=trim_edges(cannet, weight=50)
mm.plot_multimode(cancore, type_string='party')

pacnet=bi.weighted_projected_graph(g, pac_list, ratio=False)
paccore = trim_edges(pacnet, weight=50)


def sorted_map(dct):
    ds = sorted(dct.iteritems(), key=lambda (k,v): (-v,k))
    return ds

d=sorted_map(net.degree(paccore))
c=sorted_map(net.closeness_centrality(paccore))
inf_pacs=[pacs[pid] for pid,deg in d[:10]]
close_pacs=[pacs[pid] for pid,deg in c[:10]]


"""
[{'name': 'NATIONAL ASSOCIATION OF REALTORS POLITICAL ACTION COMMITTEE',
  'party': ' ',
  'type': 'Q',
  'zip': '60611'},
 {'name': 'AT&T INC. FEDERAL POLITICAL ACTION COMMITTEE (AT&T FEDERAL PAC)',
  'party': ' ',
  'type': 'Q',
  'zip': '75202'},
 {'name': 'UNITED PARCEL SERVICE INC. PAC',
  'party': ' ',
  'type': 'Q',
  'zip': '30328'},
 {'name': 'HONEYWELL INTERNATIONAL POLITICAL ACTION COMMITTEE',
  'party': ' ',
  'type': 'Q',
  'zip': '20001'},
 {'name': "LOCKHEED MARTIN CORPORATION EMPLOYEES' POLITICAL ACTION COMMITTEE",
  'party': ' ',
  'type': 'Q',
  'zip': '22202'},
 {'name': 'NATIONAL BEER WHOLESALERS ASSOCIATION POLITICAL ACTION COMMITTEE',
  'party': ' ',
  'type': 'Q',
  'zip': '22314'},
 {'name': 'GENERAL ELECTRIC COMPANY POLITICAL ACTION COMMITTEE (GEPAC)',
  'party': ' ',
  'type': 'Q',
  'zip': '20004'},
 {'name': 'COMCAST CORPORATION POLITICAL ACTION COMMITTEE- FEDERAL',
  'party': ' ',
  'type': 'Q',
  'zip': '19103'},
 {'name': 'THE BOEING COMPANY POLITICAL ACTION COMMITTEE',
  'party': ' ',
  'type': 'Q',
  'zip': '22209'},
 {'name': 'VERIZON COMMUNICATIONS INC./VERIZON WIRELESS GOOD GOVERNMENT CLUB (VERIZON/VERIZON WIRELES',
  'party': ' ',
  'type': 'Q',
  'zip': '20005'}]
  """

########NEW FILE########
__FILENAME__ = collector
import tweetstream
from webcast import *
import networkx as net


words = ["Obama", "Romney", "republican","democrat","election"]
##people = [123,124,125]
#locations = ["-122.75,36.8", "-121.75,37.8"] #, follow=people, locations=locations


retweets=net.DiGraph()
hashtag_net=net.Graph()
spatial=net.Graph()

import geocoder
geo = geocoder.geocoder()

with tweetstream.FilterStream("<your user ID>", "<password>", track=words) as stream:
	for js in stream:
		
	### process tweet to extract information
		try:
			author=js['user']['screen_name']
			entities=js['entities']
			mentions=entities['user_mentions']
			hashtags=entities['hashtags']
			location=geo.geocode(js)

			for rt in mentions:
				alter=rt['screen_name']
				retweets.add_edge(author,alter)

			tags=[tag['text'].lower() for tag in hashtags]
			for t1 in tags: 
				if location is not None and 'city' in location:
					spatial.add_node(location['city'],type='location',lat=location['latitude'],lon=location['longitude'])
					add_or_inc_edge(spatial,t1,location['city'])
					
				for t2 in tags:
					if t1 is not t2:
						add_or_inc_edge(hashtag_net,t1,t2)      
		except :
			print ':-('
			continue



########NEW FILE########
__FILENAME__ = geocoder
#!/usr/bin/env python
# encoding: utf-8
"""
geocoder.py

Created by Maksim Tsvetovat on 2011-12-12.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

#!/usr/bin/env python
# encoding: utf-8
"""
geocoder2.py

Created by Maksim Tsvetovat on 2011-08-11.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import Yahoo as yy_module
import geopy
import bsddb
import json
import unicodedata
import urllib
import logging
l=logging.getLogger("GEOCODER")


class geocoder(object):
    
    def __init__(self):
        yahoo_api_key='dj0yJmk9Qm9UQVljSEVMUlpRJmQ9WVdrOWNscEVPRGcwTldrbWNHbzlNVGMzTVRBeE56QTJNZy0tJnM9Y29uc3VtZXJzZWNyZXQmeD03MQ--'
        yahoo_secret='eeae1d9c40a5a5eec7aea5505c90c0115b799e9f'
        self.yy=yy_module.Yahoo(yahoo_api_key)
        self.db = bsddb.btopen('/tmp/location_cache.db', 'c')
        l.info('Geocoder initialized')

    def geocode(self,js):
        location=""
        
        ## first try to get the coordinates from a mobile device
        try:        
            geo=str(js['geo'])
            if geo and geo != 'None':
                l.debug(">>>> Geo "+geo)
                return(self._parse_geo(geo))
        except KeyError:
            pass
        
        try:
            location=js['user']['location']
            if location != None and location != '':
                return (self._geocode_loc(location))
        except KeyError:
            return None


    def _parse_geo(self,geo):
        """parse the Twitter geo string
        {u'type': u'Point', u'coordinates': [40.14117668, -74.8490068]}
        """
        l.debug(geo + str(type(geo)))
        try :
            if type(geo)==str: 
                geo=json.loads(geo)
            
            if geo['type']=='Point':
                lat=float(geo['coordinates'][0])
                lat=float(geo['coordinates'][1])
                return self._reverse_geocode(lat,lon)
        except:
            return None

    def _parse_point(self, str_pt):
        lat,lon=str_pt.split()
        return float(lat), float(lon)

    def _parse_ut(self, loc):
        """Parse UberTwitter location Strings -- e.g. ÜT: 40.708612,-73.92678"""
        lat, lon = loc.split()[1].split(',')
        return self._reverse_geocode(lat,lon)

    def _parse_iphone(self, loc):
        """Parse iPhone location strings"""
        lat, lon = loc.split()[1].split(',')
        return self._reverse_geocode(lat,lon)         
            

    def _reverse_geocode(self,lat,lon):
        try :
            place=yy.reverse(float(lat),float(lon))
            return place
        except:
            l.debug('reverse geo FAIL')
            return None

    def _geocode_loc(self,loc):
        
        loc_str= loc.encode('utf-8') #self.toAscii(loc)
        
        if loc_str == None or loc_str is '': 
            return None
        elif loc_str.startswith('ÜT:'):
            return self._parse_ut(loc_str)
        elif loc_str.startswith('iPhone'):
            return self._parse_iphone(loc_str)
        
        ## generate a hash-key for caching
        key=str(hash(loc_str))    
        
        ## check if we have already cached this data
        if self.db.has_key(key):
            l.debug("@<<<< read"+loc+" "+key)
            return json.loads(self.db[key])
        
        ## GEOCODE!!!    
        place=''
        if loc != '':
            try :
                place=self.yy.geocode(loc)
            except UnicodeEncodeError:
                return None
            
        ## Check if geocoding went OK, otherwise return None
        if place != '':
            l.debug("@ write >>>>"+loc+" "+key)
            self.db[key]=json.dumps(place)
            return place
        else:
            return None
        

        

########NEW FILE########
__FILENAME__ = webcast
import json
import networkx as net
import matplotlib.pyplot as plot

def trim_degrees(g, degree=1):
    """
    Trim the graph by removing nodes with degree less then value of the degree parameter
    Returns a copy of the graph, so it's non-destructive.
    """
    g2=g.copy()
    d=net.degree(g2)
    for n in g2.nodes():
        if d[n]<=degree: g2.remove_node(n)
    return g2

def sorted_degree(g):
    d=net.degree(g)
    ds = sorted(d.iteritems(), key=lambda (k,v): (-v,k))
    return ds

def add_or_inc_edge(g,f,t):
    """
    Adds an edge to the graph IF the edge does not exist already. 
    If it does exist, increment the edge weight.
    Used for quick-and-dirty calculation of projected graphs from 2-mode networks.
    """
    if g.has_edge(f,t):
        g[f][t]['weight']+=1
    else:
        g.add_edge(f,t,weight=1)
        
def trim_edges(g, weight=1):
    """
    Remove edges with weights less then a threshold parameter ("weight")
    """
    g2=net.Graph()
    for f, to, edata in g.edges(data=True):
        if edata['weight'] > weight:
            g2.add_edge(f,to,edata)
    return g2


########NEW FILE########
__FILENAME__ = Yahoo
"""
Wrapper to the Yahoo's new PlaceFinder API. (doc says that the API RELEASE 1.0 (22 JUNE 2010))
"""
import xml.dom.minidom
from geopy import util
from geopy import Point
from urllib import urlencode
from urllib2 import urlopen
from geopy.geocoders.base import Geocoder
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json


class Yahoo(Geocoder):

    BASE_URL = "http://where.yahooapis.com/geocode?%s"

    def __init__(self, app_id, format_string='%s', output_format=None):
        self.app_id = app_id
        self.format_string = format_string
        
        if output_format != None:
            from warnings import warn
            warn('geopy.geocoders.yahoo.Yahoo: The `output_format` parameter is deprecated '+
                 'and now ignored. JSON will be used internally.', DeprecationWarning)

    def geocode(self, string, exactly_one=True):
        params = {'location': self.format_string % string,
                  'appid': self.app_id,
                  'flags': 'J'
                 }
        url = self.BASE_URL % urlencode(params)
        util.logger.debug("Fetching %s..." % url)
        return self.geocode_url(url, exactly_one)

    def geocode_url(self, url, exactly_one=True):
        page = urlopen(url)
        return self.parse_json(page, exactly_one)

    def reverse(self, coord, exactly_one=True):
        (lat, lng) = coord
        params = {'location': '%s,%s' % (lat, lng),
                  'gflags' : 'R',
                  'appid': self.app_id,
                  'flags': 'J'
                 }
        url = self.BASE_URL % urlencode(params)
        return self.geocode_url(url, exactly_one)

    
    def parse_json(self, page, exactly_one=True):
        if not isinstance(page, basestring):
            page = util.decode_page(page)
        doc = json.loads(page)
        results = doc.get('ResultSet', []).get('Results', [])
    
        def parse_result(place):
            line1, line2, line3, line4 = place.get('line1'), place.get('line2'), place.get('line3'), place.get('line4')
            address = util.join_filter(", ", [line1, line2, line3, line4])
            city = place.get('city')
            state = place.get('state')
            country = place.get('country')
            location = util.join_filter(", ", [address, city, country])
            lat, lng = place.get('latitude'), place.get('longitude')
            #if lat and lng:
            #    point = Point(floatlat, lng)
            #else:
            #    point = None
            #return (place, location, (float(lat), float(lng)))
            return (place)
    
        if exactly_one:
            if len(results) > 0:
                return parse_result(results[0])
            else: return []
        else:
            return [parse_result(result) for result in results]
########NEW FILE########
