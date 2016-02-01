import _ast
from ASTParser import ASTParser
from ASTFunctionVisitor import ASTFunctionVisitor
import sys
import os


class ASTBuilder:
	def __init__(self, src):
		self.src=src
		
	def build_AST(self):
			astTree = None
			try:
				astTree=compile(self.src, "<string>", "exec", _ast.PyCF_ONLY_AST)
			except:
				return 
			try:
				functionVisitor=ASTFunctionVisitor()
				functionVisitor.visit(astTree)
				astVisitor=ASTParser(func_list=functionVisitor.func_list)
				astVisitor.visit(astTree)
				# for df_graph in astVisitor.df_graph.values():
				# 	for node in df_graph:
				# 		print(node)
				# 	print("-"*10)
				# print("-"*20)
				return astVisitor.df_graph.values()
			except:
				print "Unexpected error:",sys.exc_info()[0]
				raise

def read_source(srcfile):
	return open(srcfile).read()

i = 0
f_graph = open('graph.txt', 'w')
for subdir in os.listdir('repoData'):
	print('Foldername: ' + subdir)
	f_graph.write('\n' + 'Foldername:' + subdir)
	filename = 'repoData/' + subdir + '/allPythonContent.py'
	fullfile = read_source(filename)
	file_splits = fullfile.split('########NEW FILE########')
	for piece in file_splits:
		piece = piece.strip()
		piece_name = piece.split('\n')[0]
		df_graphs = ASTBuilder(piece).build_AST()
		if df_graphs:
			f_graph.write('\n' + piece_name + '\n')
			for graph in df_graphs:
				for node in graph:
					f_graph.write(str(node) + '\n')
				i += 1
				f_graph.write('-'*20 + '\n')
f_graph.close()
print ('There are ' + str(i) + ' parsable files in total.')
