__author__ = 'andreadsouza'

import json
import sys
import multiprocessing as mp
from ASTUtils import DFGraph, AssignmentNode
from collections import Counter
import os

"""
Script to get the most frequently used modules
"""

def find_libs(graph_text, q):
    graph=json.loads(graph_text)
    folder, file =graph['folder'], graph['file']
    print "Foldername:"+folder,"File:"+file
    df_graph=DFGraph.deserialize(graph['graph'])
    lib_count=Counter()
    for node_num in df_graph.dfs():
        node=df_graph.graph_dict[node_num]
        if isinstance(node,AssignmentNode):
            for src in node.src:
                pos=src.find('.')
                if pos!=-1:
                    try:
                        lib=src[:pos]
                        if lib!='self':
                            if lib in dir(__builtins__):
                                lib_count['builtins']+=1
                            else:
                                lib_count[lib]+=1
                    except ImportError:
                        pass
    q.put(lib_count)
    return

def listener(q):
    lib_counter=Counter()
    while(1):
        counter=q.get()
        if isinstance(counter, Counter):
            lib_counter+=counter
        else:
            break
    with open("Top100.txt","w") as f:
        for lib, freq in lib_counter.most_common(120):
            f.write(lib+':'+str(freq)+'\n')


def main():
    manager=mp.Manager()
    q=manager.Queue()
    pool=mp.Pool(mp.cpu_count())

    watcher = pool.apply_async(listener,(q,))

    jobs=[]

    graph_folder='graphs-zip/'
    count=0
    for f_name in os.listdir(graph_folder):
        graph=""
        with open(graph_folder+'/'+f_name, 'r') as file:
            graph=""
            for line in file:
                if line.strip()=='-'*60:
                    try:
                        job=pool.apply_async(find_libs, (graph,q))
                        jobs.append(job)
                        graph=""
                    except:
                        print "Unexpected error in worker:", sys.exc_info()[0]
                        break
                else:
                    graph+=line
        count+=1

    for job in jobs:
        try:
            job.get()
        except:
            continue

    q.put('kill')
    pool.close()
    pool.join()
    print "done computing top 100"

if __name__ == '__main__':
    main()
