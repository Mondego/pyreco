from os import listdir
from os.path import join
from ASTBuilder import ASTBuilder
import sys

src_path="repoData/"
flist=[f for f in listdir(src_path) if f.endswith(".py")]
for f in flist:
    try:
        fname=join(src_path,f)
        ASTBuilder(fname).build_AST()
    except SyntaxError as e:
        print "Syntax error in {0}".format(fname)
        pass
    except:
        print "Unexpected error:", sys.exc_info()[0]
        pass
