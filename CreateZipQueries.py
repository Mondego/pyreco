__author__ = 'andreadsouza'

import json
import sys
import multiprocessing as mp
from ASTUtils import DFGraph, AssignmentNode
import os

"""
Q_LIBS=["collections",
      "json",
      "threading",
      "simplejson",
      "encode",
      "decimal",
      "cStringIO",
      "jeevesdb",
      "importlib",
      "discover_runner",
      "coffin",
      "freenasUI",
      "iondb",
      "formtools",
      "nogeos",
      "south","django","os","re"]
"""
MAX_RANK=3
graph_folder='graphs-zip/'

def create_query(graph_text, Q_LIB):
    lib=None
    if Q_LIB=='builtins':
        lib=dir(__builtins__)
    else:
        lib=[Q_LIB]
    try:
        q_list=[]
        df_graph=json.loads(graph_text)
        print "Foldername:"+df_graph['folder'],"File:"+df_graph['file']
        graph=DFGraph.deserialize(df_graph['graph'])
        for node in graph.dfs():
            node_val=graph.graph_dict[node]
            if isinstance(node_val, AssignmentNode):
                for src in node_val.src:
                    dot_pos=src.find('.')
                    if dot_pos!=-1:
                        if src[:dot_pos] in lib:
                            calls=graph.find_calls(node, src)
                            calls_list=[]
                            if calls:
                                for call in calls:
                                    call_dict=call.__dict__
                                    map(call_dict.pop, ['val','adjList','parent','op','src'])
                                    calls_list.append(call_dict)
                                if calls_list:
                                    query={
                                        'folder':df_graph['folder'],
                                        'file':df_graph['file'],
                                        'type':src,
                                        'obj':node_val.tgt,
                                        'calls':calls_list,
                                        'context':node_val.context
                                    }
                                    q_list.append(query)
                                    break
    except:
        print "Error",sys.exc_info()
        print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
    return q_list

def create_queries(file, queue, Q_LIB):
    print file
    graph=""
    q_list=[]
    with open(graph_folder+'/'+file,'r') as file:
        for line in file:
            if line.strip()=='-'*60:
                try:
                   q_list.extend(create_query(graph, Q_LIB))
                   graph=""
                except:
                    print "Unexpected error in worker:", sys.exc_info()
                    graph=""
                    continue
            else:
                graph+=line

    if q_list:
        for query in q_list:
            queue.put(query)
        queue.put("$"*20)


def listener(q, Q_LIB):
    f=open('queries/query-'+Q_LIB+'.txt','w')
    while(1):
        msg=q.get()
        if msg!='kill':
            if isinstance(msg, dict):
                f.write(json.dumps(msg))
                f.write('\n'+'-' * 20 + '\n')
            else:
                f.write(msg+'\n')
        else:
            break
    f.close()

def main():
    Q_LIBS=[]
    for line in open('Top100.txt','r'):
        lib=line.split(':')[0]
        print "LIB:",lib
        Q_LIBS.append(
            lib
        )
    for Q_LIB in Q_LIBS:
        manager=mp.Manager()
        q=manager.Queue()
        pool=mp.Pool(mp.cpu_count())
        watcher = pool.apply_async(listener,(q, Q_LIB))

        jobs=[]

        count=0
        for f_name in os.listdir(graph_folder):
            job=pool.apply_async(create_queries,(f_name, q, Q_LIB))
            #with open(graph_folder+'/'+f_name, 'r') as file:
            jobs.append(job)
            count+=1

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
