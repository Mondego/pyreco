import json
import sys
import multiprocessing as mp
from ASTUtils import DFGraph, AssignmentNode
from collections import Counter
import os

"""
Script to get the most frequently used modules
"""

def find_libs(df_graph, q):
    lib_count=Counter()
    for node_num in df_graph.dfs():
        node=df_graph[node_num]
        if isinstance(node,AssignmentNode):
            for src in node.src:
                pos=src.find('.')
                if pos!=-1:
                    try:
                        lib=src[:pos]
                        if lib!='self':
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
    with open("Top10.txt","w") as f:
        for lib, freq in lib_counter.most_common(20):
            f.write(lib+':'+str(freq)+'\n')

def main():
    manager=mp.Manager()
    q=manager.Queue()
    pool=mp.Pool(mp.cpu_count())

    watcher = pool.apply_async(listener,(q,))

    jobs=[]

    graph_folder='graphs/'
    for f_name in os.listdir(graph_folder):
        graph=""
        with open(graph_folder+'/'+f_name,'r') as file:
            for line in file:
                if line.strip()=='-' * 20:
                    try:
                        df_graphs=json.loads(graph)
                        for g in df_graphs['files']:
                            print 'Folder:'+df_graphs['folder'],"File:"+g['file']
                            df_graph=DFGraph.deserialize(g['graph'])
                            job=pool.apply_async(find_libs,(df_graph,q))
                            jobs.append(job)
                        graph=""
                    except:
                        print "Unexpected error in worker:", sys.exc_info()[0]
                        with open("check-json.txt",'w') as f:
                            f.write(graph)
                        break
                else:
                    graph+=line

    for job in jobs:
        try:
            job.get()
        except:
            continue

    q.put('kill')
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
