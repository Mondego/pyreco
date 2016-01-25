import _ast
from ASTParser import ASTParser
from ASTFunctionVisitor import ASTFunctionVisitor
import sys

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

			