i__author__ = 'andreadsouza'

from ASTBuilder import ASTBuilder
import multiprocessing as mp
from zipfile import ZipFile
import os
import json

def worker(folder, count):
    zf=ZipFile(folder,'r')
    df_graphs=[]
    for f in zf.namelist():
        if f.endswith('.py'):
            file=zf.read(f)
            print count, "Foldername:"+folder, \
                "Filename:"+f
            try:
                df_graph = ASTBuilder(file).build_AST()
                if df_graph is not None:
                    df_json=df_graph.serialize()
                    if int(df_json['count'])>1:
                        prog_info={
                            'folder':folder,
                            'file':f,
                            'graph':df_json}
                        df_graphs.append(prog_info)
            except:
                print "Error while parsing file:",f
                pass

    if df_graphs:
        with open('graphs-zip/graph'+str(count)+'.txt','w') as f:
            for graph in df_graphs:
                f.write(json.dumps(graph))
                f.write('\n'+'-'*60+'\n')

def main():
    pool = mp.Pool(mp.cpu_count())
    jobs = []
    count=10000
    folder='/home/andrea/github-projects-20'
    for proj in os.listdir(folder):
        count+=1
        job=pool.apply_async(worker, (folder+'/'+proj, count))
        jobs.append(job)

    for job in jobs:
        try:
            job.get()
        except:
            continue

    pool.close()
    pool.join()

if __name__=="__main__":
    main()
