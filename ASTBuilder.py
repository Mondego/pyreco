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
            #raise
        return dfgraph


def worker(folder, q):
    filename = 'repoData/' + folder + '/allPythonContent.py'
    fullfile = open(filename).read()
    file_splits = fullfile.split('########NEW FILE########')
    for piece in file_splits:
        piece = piece.strip()
        piece_name = piece.split('\n')[0]
        try:
            print "Foldername:"+folder, "Filename:"+piece_name
            df_graph = ASTBuilder(piece).build_AST()
            if df_graph is not None:
                if int(df_graph['count'])>1:
                    prog_info={
                        'folder':folder,
                        'file':piece_name,
                        'graph':df_graph}
                    q.put(prog_info)
        except:
            print "Unexpected error in worker:", sys.exc_info()[0]
            f_test=open('srcfiles/test.py', 'w')
            f_test.write(piece)
            f_test.close()

            q.put('kill')
            raise
    filename.close()

def listener(q):
    f=open('graphs/graph-json.txt', 'w')
    while 1:
        msg=q.get()
        if msg == 'kill':
            print 'Parsing done!'
            break
        json.dump(msg, f, indent=4, ensure_ascii=False)
        f.write('\n'+'-' * 20 + '\n')
        f.flush()
    f.close()

def main():
    manager = mp.Manager()
    q = manager.Queue()
    pool = mp.Pool(mp.cpu_count())

    watcher = pool.apply_async(listener, (q,))

    jobs = []
    for proj in os.listdir('repoData'):
        job = pool.apply_async(worker, (proj, q))
        jobs.append(job)

    for job in jobs:
        try:
            job.get()
        except:
            continue

    q.put('kill')
    pool.close()
    pool.join()

if __name__=="__main__":
    main()
