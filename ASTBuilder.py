import _ast
from ASTAnalyser import ASTAnalyser
from ASTFunctionVisitor import ASTFunctionVisitor
import sys
import multiprocessing
from ASTUtils import DEBUG
import os
import ast
import json
import pprint

class ASTBuilder:
    def __init__(self, src):
        self.src = src

    def build_AST(self):
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
            return astVisitor.df_graph.serialize()
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

def read_source(srcfile):
    return open(srcfile).read()


f_graph = open('graphs/graph.txt', 'w')
i=0
for subdir in os.listdir('repoData'):
    print('Foldername: ' + subdir)
    filename = 'repoData/' + subdir + '/allPythonContent.py'
    fullfile = read_source(filename)
    file_splits = fullfile.split('########NEW FILE########')
    for piece in file_splits:
        piece = piece.strip()
        piece_name = piece.split('\n')[0]
        try:
            print piece_name
            df_graph = ASTBuilder(piece).build_AST()
            if df_graph:
                prog_info={
                    'folder':subdir,
                    'file':piece_name,
                    'graph':df_graph}
                json.dump(prog_info, f_graph, indent=4, ensure_ascii=False)
                f_graph.write('\n'+'-' * 20 + '\n')

        except:
            print sys.exc_info()
            f_test=open('srcfiles/test.py', 'w')
            f_test.write(piece)
            f_test.close()
            raise
    i+=1

f_graph.close()
print ('There are ' + str(i) + ' parsable projects in total.')
