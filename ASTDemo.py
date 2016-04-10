from os import listdir
from os.path import join
from ASTBuilder import ASTBuilder
import sys
from ASTUtils import DEBUG
import pprint
import multiprocessing

src_path="srcfiles/"
#flist=[f for f in listdir(src_path) if f.endswith(".py")]
flist=['test.py']
for f in flist:
    try:
        fname=join(src_path,f)
        print("FILENAME:"+f)

        df_graph=ASTBuilder(open(fname).read()).build_AST()

        if DEBUG:
            print "in ASTDemo"
            print pprint.pprint(df_graph)

    except SyntaxError as e:
        print "Syntax error in {0}".format(fname)
        pass
    except:
        print "Unexpected error:", sys.exc_info()[0]
        pass
