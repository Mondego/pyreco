import json
import sys
import multiprocessing as mp
from ASTUtils import DFGraph, AssignmentNode
import os

Q_LIB="os"

def get_queries(df_graph):
    queries=[]
    for node in df_graph.dfs():
        node_val=df_graph.graph_dict[node]
        if isinstance(node_val, AssignmentNode):
            for src in node_val.src:
                dot_pos=src.find('.')
                if dot_pos!=-1:
                    lib=src[:dot_pos]
                    if lib==Q_LIB:
                        calls=df_graph.find_calls(node, src)
                        if calls:
                            query={
                                'type':src,
                                'line':calls[0].lineNum,
                                'col':calls[0].colOffset,
                                'results':[]
                            }
                            for call in calls:
                                query['results'].append(
                                    call.tgt
                                )
                            queries.append(query)


    return queries



def create_queries(df_graphs, queue):
    query_list=[]
    for g in df_graphs['files']:
        print 'Folder:'+df_graphs['folder'],"File:"+g['file']
        df_graph=DFGraph.deserialize(g['graph'])
        #df_graph=DFGraph.deserialize(json.load(open("check-json.txt")))
        #df_graph=json.load(open("check-json.txt"))
        queries=get_queries(df_graph)
        if queries:
            q_file={
                'file':g['file'],
                'queries':queries
            }
            query_list.append(q_file)

    if query_list:
        query={
            'folder':df_graphs['folder'],
            'q_list':query_list
        }
        queue.put(query)

def listener(q):
    f=open('queries/queries-'+Q_LIB+'.txt','w')
    while(1):
        msg=q.get()
        if msg!='kill':
            f.write(json.dumps(msg))
            f.write('\n'+'-' * 20 + '\n')
        else:
            break
    f.close()


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
                        job=pool.apply_async(create_queries, (df_graphs,q))
                        jobs.append(job)
                        graph=""
                    except:
                        print "Unexpected error in worker:", sys.exc_info()[0]
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
