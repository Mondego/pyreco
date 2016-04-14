import _ast
from ASTAnalyser import ASTAnalyser
from ASTFunctionVisitor import ASTFunctionVisitor
import sys
import os
import json
import multiprocessing as mp

class ASTBuilder:
    def __init__(self, src):
        self.src = src

    def build_AST(self):
        dfgraph=None
        astTree = None
        try:
            astTree = compile(self.src, "<string>", "exec", _ast.PyCF_ONLY_AST)
        except:
            return

        try:
            functionVisitor = ASTFunctionVisitor()
            functionVisitor.visit(astTree)
            astVisitor = ASTAnalyser(func_list=functionVisitor.func_list)
            astVisitor.visit(astTree)
            dfgraph=astVisitor.df_graph.serialize()
        except:
            print "Unexpected error:", sys.exc_info()[0]
        return dfgraph


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
                    if int(df_graph['count'])>1:
                        prog_info={
                            'file':file_name,
                            'graph':df_graph}
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
    for proj in os.listdir('repoData'):
        job = pool.apply_async(worker, (proj,))
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
