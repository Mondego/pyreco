import _ast
from ASTParser import ASTParser
import sys

class ASTBuilder:
	def __init__(self, src):
		self.src=src
		
	def build_AST(self):
			try:
				astTree=compile(self.src, "<string>", "exec", _ast.PyCF_ONLY_AST)
				astVisitor=ASTParser()
				astVisitor.visit(astTree)
#				for node in astVisitor.df_graph:
#					print(node)
#				print("-"*20)
				return astVisitor.df_graph
			except:
#				print "Unexpected error:",sys.exc_info()[0]
				pass

