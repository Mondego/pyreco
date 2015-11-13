from os import listdir
from os.path import join
from ASTBuilder import ASTBuilder

__author__ = 'andreadsouza'

src_path="srcfiles/"

for f in listdir(src_path):
    fname=join(src_path,f)
    ASTBuilder(fname).build_AST()