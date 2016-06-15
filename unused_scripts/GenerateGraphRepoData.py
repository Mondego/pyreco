from ASTBuilder import ASTBuilder
import multiprocessing as mp
import sys
import os
import json

def worker(folder):
    filename = 'repoData/' + folder + '/allPythonContent.py'
    fullfile = open(filename).read()
    file_splits = fullfile.split('########NEW FILE########')
    df_graphs={
        'folder':folder,
        'files':[]}
    for piece in file_splits:
        piece = piece.strip()
        piece_name = piece.split('\n')[0].strip()
        if len(piece_name.split())==3:
            file_name = piece_name.split()[2]
            try:
                print "Foldername:"+folder, "Filename:"+file_name
                df_graph = ASTBuilder(piece).build_AST()
                if df_graph is not None:
                    df_json=df_graph.serialize()
                    if int(df_json['count'])>1:
                        prog_info={
                            'file':file_name,
                            'graph':df_json}
                        df_graphs['files'].append(prog_info)
            except:
                print "Unexpected error in worker:", sys.exc_info()[0]
                f_test=open('srcfiles/test.py', 'w')
                f_test.write(piece)
                f_test.close()

    proc_name=str(os.getpid())
    if df_graphs['files']:
        f=open('graphs/graph-'+proc_name+'.txt','a')
        f.write(json.dumps(df_graphs))
        f.write('\n'+'-' * 20 + '\n')
        f.close()

def main():
    pool = mp.Pool(mp.cpu_count())
    jobs = []
    #count=0
    for proj in os.listdir('repoData'):
        job = pool.apply_async(worker, (proj,))
        #count+=1
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