__FILENAME__ = ast
class Node(object):
	def __init__(self, t, *args):
		self.type = t
		self.args = args
		
	def __str__(self):
		s = "type: " + str(self.type) + "\n"
		s += "".join( ["i: " + str(i) + "\n" for i in self.args])
		return s
########NEW FILE########
__FILENAME__ = builder
import sys

from llvm import *
from llvm.core import *

import ptypes as types
from helpers import *
from ast import Node
from context import Context

# http://mdevan.nfshost.com/llvm-py/userguide.html#install


class Writer(object):

	def __init__(self):
		self.functions={}
		self.contexts = []
		self.counter = 0
		
	def get_var(self,name):
		for c in self.contexts[::-1]:
			if c.has_variable(name):
				return c.get_variable(name)
		raise Exception, "Variable %s doesn't exist" % name
		
	def set_var(self,name,value):
		self.contexts[-1].set_variable(name,value)

	def set_param(self,name,value):
		self.contexts[-1].set_param(name,value)
		
	def get_builder(self):
		return self.contexts[-1].get_builder()
		
	def get_current(self):
		return self.contexts[-1].current
		
	def get_function(self):
		for c in self.contexts[::-1]:
			if c.current.__class__ == Function:
				return c.current
		
	def descend(self,node):
		return self(node)

	def __call__(self,ast):
		
		if ast.__class__ != Node:
			return ast
			
		if ast.type == "program":
			mod_name = self.descend(ast.args[0])
			if not mod_name:
				mod_name = "pascal_program"
			
			self.module = Module.new(mod_name)
			stdio = add_stdio(self.module)
			for f in stdio:
				self.functions[f] = stdio[f]
			
			main = create_main(self.module)
			
			block = Builder.new(main.append_basic_block("entry"))
			
			self.contexts.append(Context(main,block))
			self.descend(ast.args[1])
			
			self.get_builder().ret(c_int(0))
			
			return self.module
			
		elif ast.type == "block":

			self.descend(ast.args[0]) # Var
			self.descend(ast.args[1]) # Function def
			self.descend(ast.args[2]) # Statement
		
		elif ast.type in ["var_list","statement_list","function_list"]:
			for son in ast.args:
				self.descend(son)
				
		elif ast.type == "var":
			var_name = self.descend(ast.args[0])
			var_type_name = self.descend(ast.args[1])
			builder = self.get_builder()
			v = var_init(builder, var_name, var_type_name)
			self.set_var(var_name,v)
			
		elif ast.type == "type":
			return str(ast.args[0]).upper()
			
		elif ast.type == "identifier":
			return str(ast.args[0]).lower()
			
		elif ast.type in ["function_call","function_call_inline"]:
			builder = self.get_builder()
			
			function_name = self.descend(ast.args[0])
			
			arguments = []			
			if len(ast.args) > 1:
				if ast.args[1]:
					arguments = self.descend(ast.args[1])

			if function_name in ['write','writeln']:
				if str(arguments[0].type) == 'double':
					function_name += "real"
				elif str(arguments[0].type) == 'i32':
					function_name += "int"
				

			function = self.module.get_function_named(function_name)
			return builder.call(function,arguments)
			
		elif ast.type == "parameter_list":
			l = []
			l.extend(self.descend(ast.args[0]))
			l.extend(self.descend(ast.args[1]))
			return l
			
		elif ast.type == "parameter":
			c = ast.args[0]
			if c.type == "identifier":
				label = self.descend(ast.args[0])
				c = self.get_var(label)
			else:
				c = self.descend(ast.args[0])
			return [c]
			
		elif ast.type == "assign":
			builder = self.get_builder()
			varName = self.descend(ast.args[0])
			value = self.descend(ast.args[1])
			ref = self.get_var(varName)
			builder.store(value, ref)
			return varName
			
		elif ast.type in ['procedure','function']:
			
			def get_params(node):
				""" Return a list of tuples of params """
				if node.type == 'parameter':
					return [(self.descend(node.args[0]), types.translation[self.descend(node.args[1])])]
				else:
					l = []
					for p in node.args:
						l.extend(get_params(p))
					return l
				
			head = ast.args[0]
			if head.type == 'procedure_head':
				return_type = types.void
			else:
				return_type = types.translation[self.descend(head.args[-1])]
				
			name = self.descend(head.args[0])
			if len(head.args) > 1:
				params = get_params(head.args[1])
			else:
				params = []
			code = ast.args[1]
			
			ftype = types.function(return_type,[ i[1] for i in params ])
			f = Function.new(self.module, ftype, name)
			fb = Builder.new(f.append_basic_block("entry"))
			
			self.contexts.append(Context( f,fb ))
			b = self.get_builder()
			for i,p in enumerate(params):
				x = f.args[i]; x.name = p[0]
				self.set_param(p[0],x)
				
			if ast.type == 'function':
				type_name = types.reverse_translation[return_type]
				v = var_init(b, name, type_name)
				self.set_var(name,v)
			self.descend(code)
			b = self.get_builder()
			if ast.type == 'procedure':
				b.ret_void()
			else:
				b.ret(b.load(self.get_var(name)))
			self.contexts.pop()
		
        

		elif ast.type == "while":
			self.counter += 1
			now = self.get_function()
			builder = self.get_builder()
			
			
			loop = now.append_basic_block("loop_%d" % self.counter)			
			body = now.append_basic_block("body_%d" % self.counter)
			tail = now.append_basic_block("tail_%d" % self.counter)

			# do while code
			self.contexts.append(Context(loop))
			b = self.get_builder()
			cond = self.descend(ast.args[0])
			b.cbranch(cond,body,tail)
			self.contexts.pop()
			
			self.contexts.append(Context(body))
			b = self.get_builder()
			self.descend(ast.args[1])
			# repeat
			b.branch(loop)
			self.contexts.pop()
			
			# start loop
			builder.branch(loop)
			self.contexts[-1].builder = Builder.new(tail)
			
		elif ast.type == "repeat":
			cond = Node('not',ast.args[1])
			body = ast.args[0]
			
			while_b = Node('while',cond,body)
			final = Node('statement_list',body,while_b)
			return self.descend(final)
			
		elif ast.type == "for":
			
			direction = self.descend(ast.args[1])
			limit = ast.args[2]
			builder = self.get_builder()
			
			# var declaration
			varname = self.descend(ast.args[0].args[0])
			vartype = "INTEGER"
			v = var_init(builder, varname, vartype)
			self.set_var(varname,v)
			
			# var init
			variable = self.descend(ast.args[0])
			
			# cond
			var1 = Node('element',Node('identifier',varname))
			var1_name = Node('identifier',varname)

			sign = Node('sign',(direction == "to") and '<=' or '>=')
			comp = Node('op',sign,var1,limit)
			
			# body
			op = Node('sign',(direction == "to") and '+' or '-')
			varvalue = Node('op',op,var1,Node('element',Node('integer',1)))
			increment = Node('assign',var1_name,varvalue)
			
			body = Node('statement_list',ast.args[3],increment)
			
			# do while
			while_block = Node('while',comp,body)			
			
			self.descend(while_block)
			
			
		elif ast.type == "if":
			now = self.get_function()
			builder = self.get_builder()
			
			#if
			cond = self.descend(ast.args[0])
			
			# the rest
			self.counter += 1
			tail = now.append_basic_block("tail_%d" % self.counter)
			
			# then
			then_block = now.append_basic_block("if_%d" % self.counter)
			self.contexts.append( Context(then_block)  )
			self.descend(ast.args[1])
			b = self.get_builder()
			b.branch(tail)
			b.position_at_end(tail)
			self.contexts.pop()
			
			# else
			else_block = now.append_basic_block("else_%d" % self.counter)
			self.contexts.append( Context(else_block)  )
			if len(ast.args) > 2:
				self.descend(ast.args[2])
			b = self.get_builder()
			b.branch(tail)
			b.position_at_end(tail)
			self.contexts.pop()
			
			builder.cbranch(cond,then_block,else_block)
			self.contexts[-1].builder = Builder.new(tail)
				

		elif ast.type in ["sign","and_or"]:
			return ast.args[0]
			
		elif ast.type == 'not':
			v = self.descend(ast.args[0])
			builder = self.get_builder()
			return builder.not_(v)

		elif ast.type == "op":
			sign = self.descend(ast.args[0])
			v1 = self.descend(ast.args[1])
			v2 = self.descend(ast.args[2])
			
			builder = self.get_builder()
			
			if sign == "+":
				return builder.add(v1, v2)
			elif sign == "-":
				return builder.sub(v1, v2)
			elif sign == "*":
				return builder.mul(v1, v2)
			elif sign == "/":
				return builder.fdiv(v1, v2)
			elif sign == "div":
				return builder.sdiv(v1, v2)
			elif sign == "mod":
				return builder.urem(v1, v2)
			elif sign in [">",">=","=","<=","<","<>"]:
				return compare(sign,v1,v2,builder)
			elif sign == "and":
				return builder.and_(v1,v2)
			elif sign == "or":
				return builder.or_(v1,v2)
			else:
				print sign	
				
				
		elif ast.type == "element":
			builder = self.get_builder()
			
			e = ast.args[0]
			if e.type == "identifier":
				ref = self.get_var(self.descend(e))
				if ref.__class__ == Argument:
					return ref
				return builder.load(ref)
			else:
				return self.descend(ast.args[0])
			
		elif ast.type == "string":
			b = self.get_builder()
			s = c_string(self.module,ast.args[0])
			return pointer(b,s)
			
		elif ast.type == "integer":
			return c_int(int(ast.args[0]))
			
		elif ast.type == "real":
			return c_real(float(ast.args[0]))
			
		else:
			print "unknown:", ast.type
			sys.exit()

########NEW FILE########
__FILENAME__ = context
from llvm.core import *

class Context(object):
	def __init__(self,current,builder = False):
		self.current = current
		if not builder:
			self.builder = Builder.new(self.current)
		else:
			self.builder = builder
		
		self.variables = {}
		self.params = {}
		
	def has_variable(self,name):
		return name in self.variables or name in self.params
		
	def set_variable(self,name,value):
		self.variables[name] = value
		
	def set_param(self,name,value):
		self.params[name] = value
		
	def get_variable(self,name):
		if name in self.params:
			return self.params[name]
		if name in self.variables:
			return self.variables[name]
		raise Exception, "Variable %s doesn't exist" % name
			
	def get_builder(self):
		return self.builder
########NEW FILE########
__FILENAME__ = graph
import pydot
from ast import Node


def graph(node, filename):
	edges = descend(node)
	g=pydot.graph_from_edges(edges) 
	if filename:
		f = filename + ".png"
	else:
		f = "graph.png"
	g.write_png(f, prog='dot') 
	

def descend(node):	
	edges = []
	if node.__class__ != Node:
		return []
	
	for i in node.args:
		edges.append((s(node),s(i)))
		edges += descend(i)
	return edges
	
	
def s(node):
	if node.__class__ != Node:
		return "%s (%s)" % (node,id(node))
	return "%s (%s)" % (node.type,id(node))
	
########NEW FILE########
__FILENAME__ = hello
from llvm import *
from llvm.core import *
import ptypes as types
from helpers import *

m = Module.new('my_module')

stdio = add_stdio(m)

printf = stdio['printf']


ty_func = Type.function(types.integer, [])
f = m.add_function(ty_func, "main1")
bb = f.append_basic_block("entry")
builder = Builder.new(bb)

tpointer = Type.pointer(Type.pointer(types.int8, 0), 0)	
ft = Type.function(types.integer,[ types.integer, tpointer  ] )
main = m.add_function( ft, "main"   )
bb = main.append_basic_block("entry")
builder = Builder.new(bb)
builder.call(printf,   (
	pointer(builder,c_string(m, "hell yeah")),

))
builder.ret(c_int(5))

print m
if True:# m.verify() is None:
	m.to_bitcode(file("test.bc", "w"))
	import os
	#os.system("llvm-as test.bc | opt -std-compile-opts -f > test_opt.bc")
	#os.system("lli test.bc > success.txt")
	#os.system("llc test.bc -o program.c")
	#os.system("gcc program.c -o a.out")
else:
	print "error"
########NEW FILE########
__FILENAME__ = helpers
from llvm.core import *
import ptypes as types


def compare(sign,v1,v2,builder):
	""" [">",">=","=","<=","<","<>"] """
	
	if sign == ">":
		i_cod = IPRED_UGT
		f_cod = RPRED_OGT
	elif sign == ">=":
		i_cod = IPRED_UGE
		f_cod = RPRED_OGE
	elif sign == "=":
		i_cod = IPRED_EQ
		f_cod = RPRED_OEQ
	elif sign == "<=":
		i_cod = IPRED_ULE
		f_cod = RPRED_OLE
	elif sign == "<":
		i_cod = IPRED_ULT
		f_cod = RPRED_OLT
	elif sign == "<>":
		i_cod = IPRED_NE
		f_cod = RPRED_ONE
	else:
		return c_boolean(False)
	
	if v1.type == types.integer:
		return builder.icmp(i_cod, v1, v2)
	elif v1.type == types.real:
		return builder.fcmp(f_cod, v1, v2)
	else:
		return c_boolean(False)
	

def c_boolean(val):
	if val:
		return c_int(1).icmp(IPRED_UGT,c_int(0))
	else:
		return c_int(0).icmp(IPRED_UGT,c_int(1))

def c_int(val):
	return Constant.int(types.integer,val)

def c_real(val):
	return Constant.real(types.real, val)

def c_string(context,val,name=""):
	""" Creates a string for LLVM """
	str = context.add_global_variable(Type.array(types.int8, len(val) + 1), name)
	str.initializer = Constant.stringz(val)
	return str
	
def pointer(block,val):
	""" Returns the pointer for a value """
	return block.gep(val,(  c_int(0), c_int(0) ))
	
	
def eval_type(v):
	if type(v) == type(1):
		return c_int(v)
	if type(v) == type(1.0):
		return c_real(v)
	if type(v) == type(""):
		return c_string(v)
	if type(v) == type(True):
		return c_boolean(v)
	else:
		return types.void
	
def var_init(builder, name, type_name, value=False):
	if not value:
		v = eval_type(types.defaults[type_name])
	else:
		v = eval_type(value)
	t = types.translation[type_name]
	ref = builder.alloca(t)
	builder.store(v,ref)
	return ref
	
def add_stdio(mod):
	""" Adds stdio functions to a module """
	return {
		"printf": mod.add_function(types.function(types.void, (Type.pointer(types.int8, 0),), 1), "printf"),
		"writeln": create_write(mod,ln=True),
		"write": create_write(mod),
		"writeint": create_write_alt('integer',mod),
		"writereal": create_write_alt('real',mod),
		"writelnint": create_write_alt('integer',mod,ln=True),
		"writelnreal": create_write_alt('real',mod,ln=True)
	}
	
def create_main(mod):
	""" Returns a main function """
	
	tpointer = Type.pointer(Type.pointer(types.int8, 0), 0)	
	ft = Type.function(types.integer,[ types.integer, tpointer  ] )
	return mod.add_function(ft, "main")


def create_write(mod,ln=False):
	""" Creates a stub of println """
	
	if ln:
		fname = "writeln"
	else:
		fname = "write"
	printf = mod.get_function_named("printf")
	
	string_pointer = Type.pointer(types.int8, 0)
	
	f = mod.add_function(
		types.function(types.void, (string_pointer,) )
	, fname)
	bb = f.append_basic_block("entry")	
	builder = Builder.new(bb)
	builder.call(printf,   (
		f.args[0],
	))
	
	if ln:
		builder.call(printf,   (
			pointer(builder, c_string(mod,"\n")),
		))
	builder.ret_void()
	return f

def create_write_alt(type_,mod,ln=False):
	if type_ == 'integer':
		fname = 'writeint'
		code = '%d'
		argtype = types.integer
	elif type_ == 'real':
		fname = 'writereal'
		code = '%f'
		argtype = types.real
		
	if ln:
		fname = fname.replace("write","writeln")
		code += "\n"
	
	printf = mod.get_function_named("printf")
	
	funcType = Type.function(Type.void(), [argtype])  
	print_alt = mod.add_function(funcType, fname)  

	bb = print_alt.append_basic_block('bb')  
	b = Builder.new(bb)  
	
	stringConst = c_string(mod,code)
	stringConst = pointer(b,stringConst)
	
	b.call(printf,[stringConst,print_alt.args[0]])
	b.ret_void()
	return print_alt;
	
	
class Block(object):
    def __init__(self, builder, where, label):
        self.emit = builder
        self.block = where.append_basic_block(label)
        self.post_block = fun.append_basic_block("__break__" + label)

    def __enter__(self):
        self.emit.branch(self.block)
        self.emit.position_at_end(self.block)
        return self.block, self.post_block

    def __exit__(self, *arg):
        self.emit.branch(self.post_block)
        self.emit.position_at_end(self.post_block)

class IfBlock(Block):
    count = 0
    def __init__(self, emit, fun, cond):
        Block.__init__(self, emit, fun, "if_%d" % self.__class__.count)
        self.__class__.count += 1
        emit.cbranch(cond, self.block, self.post_block)
########NEW FILE########
__FILENAME__ = ptypes
from llvm.core import *

# auxiliary
void = Type.void()
boolean = Type.int(1)
int8 = Type.int(8)

integer = Type.int()
real  = Type.double()
char = Type.int()
string = lambda x: Type.array( integer, x )

function = Type.function

def procedure(*args):
	return Type.function(void, args)
	
	
translation = {
	"INTEGER": integer,
	"REAL": real,
	"CHAR": char
}

class ReverseDict(object):
	def __init__(self,dic):
		self.dic = dic
	def __getitem__(self,p):
		for k in self.dic:
			if self.dic[k] == p:
				return k
				
reverse_translation = ReverseDict(translation)
				
defaults = {
	"INTEGER": 0,
	"REAL": 0.0,
	"CHAR": '_'
}
########NEW FILE########
__FILENAME__ = parser
import sys, os
from subprocess import Popen, PIPE

from ply import yacc,lex

from tokens import *
from rules import *
from semantic import *
from codegen.builder import *

def get_input(file=False):
	if file:
		f = open(file,"r")
		data = f.read()
		f.close()
	else:
		data = ""
		while True:
			try:
				data += raw_input() + "\n"
			except:
				break
	return data

def main(options={},filename=False):
	logger = yacc.NullLogger()
	yacc.yacc(debug = logger, errorlog= logger )
	
	data = get_input(filename)
	ast =  yacc.parse(data,lexer = lex.lex(nowarn=1))	
	
	if options.graph:
		from codegen.graph import graph
		graph(ast, filename)
	
	try:
		check(ast)
	except Exception, e:
		print "Error: %s" % e
		sys.exit()
	
	try:
		o = Writer()(ast)
	except Exception, e:
		print "Error(2): %s" % e
		sys.exit()

	if not hasattr(o,"ptr"):
		print "Error compiling"
		sys.exit()
		
	if options.verbose:
		print o
		if options.run:
			print 20*"-" + " END " + 20*"-"
		
	if options.run:
		
		# hack
		from llvm.core import _core
		bytecode = _core.LLVMGetBitcodeFromModule(o.ptr)
		
		p = Popen(['lli'],stdout=PIPE, stdin=PIPE)
		sys.stdout.write(p.communicate(bytecode)[0])
	else:		
		o.to_bitcode(file("tmp/middle.bc", "w"))
		#os.system("llvm-as tmp/middle.bc | opt -std-compile-opts -f > tmp/optimized.bc")
		os.system("llc -f -o=tmp/middle.s tmp/middle.bc")
		os.system("gcc -o %s tmp/middle.s" % options.filename)
	
	
if __name__ == '__main__':
	main()
########NEW FILE########
__FILENAME__ = rules
from codegen.ast import Node
import sys
# META

#start = 'block'

precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVISION'),
    ('left', 'DIV', 'MOD'),
    ('left', 'EQ', 'NEQ', 'LTE','LT','GT','GTE'),
    ('left', 'OR', 'AND'),
)


def p_program_start(t):
	'program : header SEMICOLON block DOT'
	t[0] = Node('program',t[1],t[3])

def p_header(t):
	'header : PROGRAM identifier'
	t[0] = t[2]
	
def p_block(t):
	"""block : variable_declaration_part procedure_or_function statement_part
	"""
	t[0] = Node('block',t[1],t[2],t[3])
	
	
def p_variable_declaration_part(t):
	"""variable_declaration_part : VAR variable_declaration_list
	 |
	"""
	if len(t) > 1:
		t[0] = t[2]

def p_variable_declaration_list(t):
	"""variable_declaration_list : variable_declaration variable_declaration_list
	 | variable_declaration
	"""
	# function and procedure missing here
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node('var_list',t[1],t[2])

def p_variable_declaration(t):
	"""variable_declaration : identifier COLON type SEMICOLON"""
	t[0] = Node('var',t[1],t[3])
	
	
	
def p_procedure_or_function(t):
	"""procedure_or_function : proc_or_func_declaration SEMICOLON procedure_or_function
		| """
		
	if len(t) == 4:
		t[0] = Node('function_list',t[1],t[3])
		
		
def p_proc_or_func_declaration(t):
	""" proc_or_func_declaration : procedure_declaration
               | function_declaration """
	t[0] = t[1]
		
		
def p_procedure_declaration(t):
	"""procedure_declaration : procedure_heading SEMICOLON block"""
	t[0] = Node("procedure",t[1],t[3])
		
		
def p_procedure_heading(t):
	""" procedure_heading : PROCEDURE identifier 
	| PROCEDURE identifier LPAREN parameter_list RPAREN"""
	
	if len(t) == 3:
		t[0] = Node("procedure_head",t[2])
	else:
		t[0] = Node("procedure_head",t[2],t[4])
		
		
def p_function_declaration(t):
	""" function_declaration : function_heading SEMICOLON block"""
	t[0] = Node('function',t[1],t[3])
	
	
def p_function_heading(t):
	""" function_heading : FUNCTION type
	 	| FUNCTION identifier COLON type
		| FUNCTION identifier LPAREN parameter_list RPAREN COLON type"""
	if len(t) == 3:
		t[0] = Node("function_head",t[2])
	elif len(t) == 5:
		t[0] = Node("function_head",t[2],t[3])
	else:
		t[0] = Node("function_head",t[2],t[4],t[7])

	
def p_parameter_list(t):
	""" parameter_list : parameter COMMA parameter_list
	| parameter"""
	if len(t) == 4:
		t[0] = Node("parameter_list", t[1], t[3])
	else:
		t[0] = t[1]
		
def p_parameter(t):
	""" parameter : identifier COLON type"""
	t[0] = Node("parameter", t[1], t[3])

def p_type(t):
	""" type : TREAL 
	| TINTEGER
	| TCHAR
	| TSTRING """
	t[0] = Node('type',t[1].lower())
	
def p_statement_part(t):
	"""statement_part : BEGIN statement_sequence END"""
	t[0] = t[2]
	
def p_statement_sequence(t):
	"""statement_sequence : statement SEMICOLON statement_sequence
	 | statement"""
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node('statement_list',t[1],t[3])
	
def p_statement(t):
	"""statement : assignment_statement
	 | statement_part
	 | if_statement
	 | while_statement
	 | repeat_statement
	 | for_statement
	 | procedure_or_function_call
	 |
	"""
	if len(t) > 1:
		t[0] = t[1]
	
	
def p_procedure_or_function_call(t):
	""" procedure_or_function_call : identifier LPAREN param_list RPAREN
	| identifier """
	
	if len(t) == 2:
		t[0] = Node("function_call", t[1])
	else:
		t[0] = Node("function_call",t[1],t[3])

def p_param_list(t):
	""" param_list : param_list COMMA param
	 | param """
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node("parameter_list",t[1],t[3])

def p_param(t):
	""" param : expression """
	t[0] = Node("parameter",t[1])

	
def p_if_statement(t):
	"""if_statement : IF expression THEN statement ELSE statement
	| IF expression THEN statement
	"""
	
	if len(t) == 5:
		t[0] = Node('if',t[2],t[4])
	else:
		t[0] = Node('if',t[2],t[4],t[6])
	
def p_while_statement(t):
	"""while_statement : WHILE expression DO statement"""
	t[0] = Node('while',t[2],t[4])
	
	
def p_repeat_statement(t):
	"""repeat_statement : REPEAT statement UNTIL expression"""
	t[0] = Node('repeat',t[2],t[4])
	
def p_for_statement(t):
	"""for_statement : FOR assignment_statement TO expression DO statement
	| FOR assignment_statement DOWNTO expression DO statement
	"""
	t[0] = Node('for',t[2],t[3],t[4],t[6])
	
def p_assignment_statement(t):
	"""assignment_statement : identifier ASSIGNMENT expression"""
	t[0] = Node('assign',t[1],t[3])
	
def p_expression(t):
	"""expression : expression and_or expression_m
	| expression_m
	"""
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node('op',t[2],t[1],t[3])

def p_expression_m(t):
	""" expression_m : expression_s
	| expression_m sign expression_s"""
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node('op',t[2],t[1],t[3])
	
def p_expression_s(t):
	""" expression_s : element 
	| expression_s psign element"""
	if len(t) == 2:
		t[0] = t[1]
	else:
		t[0] = Node('op',t[2],t[1],t[3])

def p_and_or(t):
	""" and_or : AND
	| OR """
	t[0] = Node('and_or',t[1])

def p_psign(t):
	"""psign : TIMES
	| DIVISION"""
	t[0] = Node('sign',t[1])

def p_sign(t):
	"""sign : PLUS
	| MINUS
	| DIV
	| MOD
	| EQ
	| NEQ
	| LT
	| LTE
	| GT
	| GTE
	"""
	t[0] = Node('sign',t[1])


def p_element(t):
	"""element : identifier
	| real
	| integer
	| string
	| char
	| LPAREN expression RPAREN
	| NOT element
	| function_call_inline
	"""
	if len(t) == 2:
		t[0] = Node("element",t[1])
	elif len(t) == 3:
		# not e
		t[0] = Node('not',t[2])
	else:
		# ( e )
		t[0] = Node('element',t[2])
		
def p_function_call_inline(t):
	""" function_call_inline : identifier LPAREN param_list RPAREN"""
	t[0] = Node('function_call_inline',t[1],t[3])
	
def p_identifier(t):
	""" identifier : IDENTIFIER """
	t[0] = Node('identifier',str(t[1]).lower())
	
def p_real(t):
	""" real : REAL """
	t[0] = Node('real',t[1])
	
def p_integer(t):
	""" integer : INTEGER """
	t[0] = Node('integer',t[1])

def p_string(t):
	""" string : STRING """
	t[0] = Node('string',t[1])

def p_char(t):
	""" char : CHAR """
	t[0] = Node('char',t[1])

def p_error(t):
	print "Syntax error in input, in line %d!" % t.lineno
	sys.exit()
########NEW FILE########
__FILENAME__ = semantic
types = ['integer','real','char','string','boolean','void']

class Any(object):
	def __eq__(self,o):
		return True
	def __ne__(self,o):
		return False

class Context(object):
	def __init__(self,name=None):
		self.variables = {}
		self.var_count = {}
		self.name = name
	
	def has_var(self,name):
		return name in self.variables
	
	def get_var(self,name):
		return self.variables[name]
	
	def set_var(self,name,typ):
		self.variables[name] = typ
		self.var_count[name] = 0

contexts = []
functions = {
	'write':('void',[
			("a",Any())
		]),
	'writeln':('void',[
			("a",Any())
		]),
	'writeint':('void',[
			("a",'integer')
		]),
	'writereal':('void',[
			("a",'real')
		]),
	'writelnint':('void',[
			("a",'integer')
		]),
	'writelnreal':('void',[
			("a",'real')
		])
}

def pop():
	count = contexts[-1].var_count
	for v in count:
		if count[v] == 0:
			print "Warning: variable %s was declared, but not used." % v
	contexts.pop()

def check_if_function(var):
	if var.lower() in functions and not is_function_name(var.lower()):
		raise Exception, "A function called %s already exists" % var
		
def is_function_name(var):
	for i in contexts[::-1]:
		if i.name == var:
			return True
	return False
		
		
def has_var(varn):
	var = varn.lower()
	check_if_function(var)
	for c in contexts[::-1]:
		if c.has_var(var):
			return True
	return False

def get_var(varn):
	var = varn.lower()
	for c in contexts[::-1]:
		if c.has_var(var):
			c.var_count[var] += 1
			return c.get_var(var)
	raise Exception, "Variable %s is referenced before assignment" % var
	
def set_var(varn,typ):
	var = varn.lower()
	check_if_function(var)
	now = contexts[-1]
	if now.has_var(var):
		raise Exception, "Variable %s already defined" % var
	else:
		now.set_var(var,typ.lower())
	
def get_params(node):
	if node.type == "parameter":
		return [check(node.args[0])]
	else:
		l = []
		for i in node.args:
			l.extend(get_params(i))
		return l
		
def flatten(n):
	if not is_node(n): return [n]
	if not n.type.endswith("_list"):
		return [n]
	else:
		l = []
		for i in n.args:
			l.extend(flatten(i))
		return l
		

def is_node(n):
	return hasattr(n,"type")

def check(node):
	if not is_node(node):
		if hasattr(node,"__iter__") and type(node) != type(""):
			for i in node:
				check(i)
		else:
			return node
	else:
		if node.type in ['identifier']:
			return node.args[0]
			
		elif node.type in ['var_list','statement_list','function_list']:
			return check(node.args)
			
		elif node.type in ["program","block"]:
			contexts.append(Context())
			check(node.args)
			pop()
			
		elif node.type == "var":
			var_name = node.args[0].args[0]
			var_type = node.args[1].args[0]
			set_var(var_name, var_type)
			
		elif node.type in ['function','procedure']:
			head = node.args[0]
			name = head.args[0].args[0].lower()
			check_if_function(name)
			
			if len(head.args) == 1:
				args = []
			else:
				args = flatten(head.args[1])
				args = map(lambda x: (x.args[0].args[0],x.args[1].args[0]), args)
				
			if node.type == 'procedure':
				rettype = 'void'
			else:
				rettype = head.args[-1].args[0].lower()
				
			functions[name] = (rettype,args)
			
			
			contexts.append(Context(name))
			for i in args:
				set_var(i[0],i[1])
			check(node.args[1])
			pop()
			
		elif node.type in ["function_call","function_call_inline"]:
			fname = node.args[0].args[0].lower()
			if fname not in functions:
				raise Exception, "Function %s is not defined" % fname
			if len(node.args) > 1:
				args = get_params(node.args[1])
			else:
				args = []
			rettype,vargs = functions[fname]
		
			if len(args) != len(vargs):
				raise Exception, "Function %s is expecting %d parameters and got %d" % (fname, len(vargs), len(args))
			else:
				for i in range(len(vargs)):
					if vargs[i][1] != args[i]:
						raise Exception, "Parameter #%d passed to function %s should be of type %s and not %s" % (i+1,fname,vargs[i][1],args[i])
			
			return rettype
			
		elif node.type == "assign":	
				varn = check(node.args[0]).lower()
				if is_function_name(varn):
					vartype = functions[varn][0]
				else:
					if not has_var(varn):
						raise Exception, "Variable %s not declared" % varn
					vartype = get_var(varn)
				assgntype = check(node.args[1])
				
				if vartype != assgntype:
					raise Exception, "Variable %s is of type %s and does not support %s" % (varn, vartype, assgntype)
				
				
		elif node.type == 'and_or':
			op = node.args[0].args[0]
			for i in range(1,2):
				a = check(node.args[i])
				if a != "boolean":
					raise Exception, "%s requires a boolean. Got %s instead." % (op,a)

			
		elif node.type == "op":
			
			op = node.args[0].args[0]
			vt1 = check(node.args[1])
			vt2 = check(node.args[2])

			if vt1 != vt2:
				raise Exception, "Arguments of operation '%s' must be of the same type. Got %s and %s." % (op,vt1,vt2)
				
			if op in ['mod','div']:
				if vt1 != 'integer':
					raise Exception, "Operation %s requires integers." % op
			
			if op == '/':
				if vt1 != 'real':
					raise Exception, "Operation %s requires reals." % op
				
			if op in ['=','<=','>=','>','<','<>']:
				return 'boolean'
			else:
				return vt1	
			
				
		elif node.type in ['if','while','repeat']:
			if node.type == 'repeat':
				c = 1
			else:
				c = 0
			t = check(node.args[c])
			if t != 'boolean':
				raise Exception, "%s condition requires a boolean. Got %s instead." % (node.type,t)
			
			# check body
			check(node.args[1-c])
			
			# check else
			if len(node.args) > 2:
				check(node.args[2])
				
			
		elif node.type == 'for':
			contexts.append(Context())
			v = node.args[0].args[0].args[0].lower()
			set_var(v,'INTEGER')
			
			st = node.args[0].args[1].args[0].type.lower()
			if st != 'integer':
				raise Exception, 'For requires a integer as a starting value'
			
			fv = node.args[2].args[0].type.lower()
			if fv != 'integer':
				raise Exception, 'For requires a integer as a final value'
			
			check(node.args[3])
			
			pop()
			
		elif node.type == 'not':
			return check(node.args[0])
			
		elif node.type == "element":
			if node.args[0].type == 'identifier':
				return get_var(node.args[0].args[0])
			elif node.args[0].type == 'function_call_inline':
				return check(node.args[0])
			else:
				if node.args[0].type in types:
					return node.args[0].type
				else:
					return check(node.args[0])
			
			
		else:
			print "semantic missing:", node.type
########NEW FILE########
__FILENAME__ = tokens
QUOTE = r'(\'|")'


tokens = (

	# assignment
	'IDENTIFIER',
	'ASSIGNMENT',
	'SEMICOLON',
	'COLON',
	'COMMA',

	'COMMENT',

	# main
	'PROGRAM',
	'DOT',
	
	# blocks
	'VAR',
	'BEGIN',
	'END',
	
	# control flow
	'IF',
	'THEN',
	'ELSE',
	'FOR',
	'WHILE',
	'REPEAT',
	'UNTIL',
	'DO',
	'TO',
	'DOWNTO',
	
	# logic
	'AND',
	'OR',
	'NOT',
	
	# operations
	'PLUS',
	'MINUS',
	'TIMES',
	'DIVISION',
	'DIV',
	'MOD',
	
	# comparations
	'EQ',
	'NEQ',
	'LT',
	'GT',
	'LTE',
	'GTE',
	
	# functions
	'LPAREN',
	'RPAREN',
#	'LBRACKET',
#	'RBRACKET',
	'PROCEDURE',
	'FUNCTION',

	# types
	'REAL',
	'INTEGER',
	'STRING',
	'CHAR',
	
	# types names
	'TREAL',
	'TINTEGER',
	'TSTRING',
	'TCHAR',
)


# Regular statement rules for tokens.
t_DOT			= r"\."

t_ASSIGNMENT	= r":="
t_SEMICOLON		= r";"
t_COLON			= r":"
t_COMMA			= r","

t_PLUS			= r"\+"
t_MINUS			= r"\-"
t_TIMES			= r"\*"
t_DIVISION		= r"/"

t_EQ			= r"\="
t_NEQ			= r"\<\>"
t_LT			= r"\<"
t_GT			= r"\>"
t_LTE			= r"\<\="
t_GTE			= r"\>\="


t_LPAREN		= r"\("
t_RPAREN		= r"\)"
#t_LBRACKET		= r"\["
#t_RBRACKET		= r"\]"

t_REAL			= r"(\-)*[0-9]+\.[0-9]+"
t_INTEGER		= r"(\-)*[0-9]+"


reserved_keywords = {
	'program':	'PROGRAM',
	'var':		'VAR',
	'begin':	'BEGIN',
	'end':		'END',
	
	'if':		'IF',
	'then':		'THEN',
	'else':		'ELSE',
	'for':		'FOR',
	'while':	'WHILE',
	'repeat':	'REPEAT',
	'do':		'DO',
	'to':		'TO',
	'downto':	'DOWNTO',
	'until':	'UNTIL',
	
	
	'and':		'AND',
	'or':		'OR',
	'not':		'NOT',
	
	'div':		'DIV',
	'mod':		'MOD',
	
	'procedure':'PROCEDURE',
	'function':	'FUNCTION',
	
	'real':		'TREAL',
	'integer':	'TINTEGER',
	'string':	'TSTRING',
	'char':	'TCHAR',
}

def t_IDENTIFIER(t):
	r"[a-zA-Z]([a-zA-Z0-9])*"
	if t.value.lower() in reserved_keywords:
		t.type = reserved_keywords[t.value.lower()]
	return t


def t_CHAR(t):
	r"(\'([^\\\'])\')|(\"([^\\\"])\")"
	return t

def t_STRING(t): 
    r"(\"([^\\\"]|(\\.))*\")|(\'([^\\\']|(\\.))*\')"
    escaped = 0 
    str = t.value[1:-1] 
    new_str = "" 
    for i in range(0, len(str)): 
        c = str[i] 
        if escaped: 
            if c == "n": 
                c = "\n" 
            elif c == "t": 
                c = "\t" 
            new_str += c 
            escaped = 0 
        else: 
            if c == "\\": 
                escaped = 1 
            else: 
                new_str += c 
    t.value = new_str 
    return t



def t_COMMENT(t):
	r"{[^}]*}"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# A string containing ignored characters (spaces and tabs).
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print "Illegal character '%s'" % t.value[0]



if __name__ == '__main__':
	# Build the lexer
	from ply import lex
	import sys 
	
	lex.lex()
	
	if len(sys.argv) > 1:
		f = open(sys.argv[1],"r")
		data = f.read()
		f.close()
	else:
		data = ""
		while 1:
			try:
				data += raw_input() + "\n"
			except:
				break
	
	lex.input(data)
	
	# Tokenize
	while 1:
	    tok = lex.token()
	    if not tok: break      # No more input
	    print tok
	


########NEW FILE########
__FILENAME__ = cod
#!/usr/bin/env python

from llvm.core import *

# create a module
module = Module.new ("tut2")

# create a function type taking 2 integers, return a 32-bit integer
ty_int    = Type.int (32)
func_type = Type.function (ty_int, (ty_int, ty_int))

# create a function of that type
gcd = Function.new (module, func_type, "gcd")

# name function args
x = gcd.args[0]; x.name = "x"
y = gcd.args[1]; y.name = "y"

# implement the function

# blocks...
entry = gcd.append_basic_block ("entry")
ret   = gcd.append_basic_block ("return")
cond_false   = gcd.append_basic_block ("cond_false")
cond_true    = gcd.append_basic_block ("cond_true")
cond_false_2 = gcd.append_basic_block ("cond_false_2")

# create a llvm::IRBuilder
bldr = Builder.new (entry)
x_eq_y = bldr.icmp (IPRED_EQ, x, y, "tmp")
bldr.cbranch (x_eq_y, ret, cond_false)


bldr.position_at_end (cond_false)
x_lt_y = bldr.icmp (IPRED_ULT, x, y, "tmp")
bldr.cbranch (x_lt_y, cond_true, cond_false_2)

bldr.position_at_end (cond_true)
y_sub_x = bldr.sub (y, x, "tmp")
recur_1 = bldr.call (gcd, (x, y_sub_x,), "tmp")
bldr.ret (recur_1)

bldr.position_at_end (cond_false_2)
x_sub_y = bldr.sub (x, y, "x_sub_y")
recur_2 = bldr.call (gcd, (x_sub_y, y,), "tmp")
bldr.ret (recur_2)


bldr.position_at_end (ret)
bldr.ret(x)

print module
########NEW FILE########
__FILENAME__ = loops
# encoding=utf-8
from __future__ import with_statement
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
 
# ヘルパー関数
def new_str_const(val):
    '''新しい文字列定数を生成する'''
    global mod, int8_type
    str = mod.add_global_variable(Type.array(int8_type, len(val) + 1), "")
    str.initializer = Constant.stringz(val)
    return str
 
def gep_first(emit, val):
    '''配列の先頭アドレスを取得する'''
    global int_type
    return emit.gep(val, (int_zero, int_zero))
 
def int_const(val):
    '''整数定数値オブジェクトを生成する'''
    global int_type
    return Constant.int(int_type, val)
 
class new_block(object):
    '''制御構造を表すためのヘルパークラス'''
    def __init__(self, emit, fun, label):
        self.emit = emit
        self.block = fun.append_basic_block(label)
        self.post_block = fun.append_basic_block("__break__" + label)
 
    def __enter__(self):
        self.emit.branch(self.block)
        self.emit.position_at_end(self.block)
        return self.block, self.post_block
 
    def __exit__(self, *arg):
        self.emit.branch(self.post_block)
        self.emit.position_at_end(self.post_block)
 
class emit_if(new_block):
    '''制御構造を表すためのヘルパークラス'''
    count = 0
    def __init__(self, emit, fun, cond):
        new_block.__init__(self, emit, fun, "if_%d" % self.__class__.count)
        self.__class__.count += 1
        emit.cbranch(cond, self.block, self.post_block)
 
# よく使う型はあらかじめ取っておく
int_type = Type.int()
int8_type = Type.int(8)
int_zero = int_const(0)
 
# ----------------------------------------------------------------------------
# コード生成
# ----------------------------------------------------------------------------
 
# モジュールを定義
mod = Module.new("plus1")
# モジュールに外部関数「printf」を追加
printf = mod.add_function(
    Type.function(
        Type.void(),
        (Type.pointer(int8_type, 0),), 1), "printf")
 
# --- 関数 plus1() ---
# モジュールに関数「plus1」を追加
plus1_fun = mod.add_function(
    Type.function(Type.void(), (int_type,)), "plus1")
 
# インストラクションコードを送出する
emit = Builder.new(plus1_fun.append_basic_block("entry"))
emit.call(printf,
    (
        gep_first(emit, new_str_const("%s: %d¥n")),
        gep_first(emit, new_str_const("test")),
        emit.mul(plus1_fun.args[0], int_const(2))
        )
    )
emit.ret_void()
 
# --- 関数 loop() ---
# モジュールに関数「loop」を追加
loop_fun = mod.add_function(
    Type.function(Type.void(), ()), "loop")
 
# インストラクションコードを送出する
emit = Builder.new(loop_fun.append_basic_block("entry"))
count_var = emit.alloca(int_type)
 
emit.store(int_zero, count_var)
with new_block(emit, loop_fun, "loop") as (loop, _break):
    with emit_if(emit, loop_fun,
            emit.icmp(IPRED_ULT, emit.load(count_var), int_const(10))):
        emit.call(plus1_fun,
            (
                emit.load(count_var),
                )
            )
        emit.store(emit.add(emit.load(count_var), int_const(1)), count_var)
        emit.branch(loop)
emit.ret_void()

print mod
########NEW FILE########
__FILENAME__ = t
# encoding=utf-8
from __future__ import with_statement
from llvm.core import *
from llvm.passes import *
from llvm.ee import *
 
# ヘルパー関数
def new_str_const(val):
    '''新しい文字列定数を生成する'''
    global mod, int8_type
    str = mod.add_global_variable(Type.array(int8_type, len(val) + 1), "")
    str.initializer = Constant.stringz(val)
    return str
 
def gep_first(emit, val):
    '''配列の先頭アドレスを取得する'''
    global int_type
    return emit.gep(val, (int_zero, int_zero))
 
def int_const(val):
    '''整数定数値オブジェクトを生成する'''
    global int_type
    return Constant.int(int_type, val)
 
class new_block(object):
    '''制御構造を表すためのヘルパークラス'''
    def __init__(self, emit, fun, label):
        self.emit = emit
        self.block = fun.append_basic_block(label)
        self.post_block = fun.append_basic_block("__break__" + label)
 
    def __enter__(self):
        self.emit.branch(self.block)
        self.emit.position_at_end(self.block)
        return self.block, self.post_block
 
    def __exit__(self, *arg):
        self.emit.branch(self.post_block)
        self.emit.position_at_end(self.post_block)
 
class emit_if(new_block):
    '''制御構造を表すためのヘルパークラス'''
    count = 0
    def __init__(self, emit, fun, cond):
        new_block.__init__(self, emit, fun, "if_%d" % self.__class__.count)
        self.__class__.count += 1
        emit.cbranch(cond, self.block, self.post_block)
 
# よく使う型はあらかじめ取っておく
int_type = Type.int()
int8_type = Type.int(8)
int_zero = int_const(0)
 
# ----------------------------------------------------------------------------
# コード生成
# ----------------------------------------------------------------------------
 
# モジュールを定義
mod = Module.new("plus1")
# モジュールに外部関数「printf」を追加
printf = mod.add_function(
    Type.function(
        Type.void(),
        (Type.pointer(int8_type, 0),), 1), "printf")
 
# --- 関数 plus1() ---
# モジュールに関数「plus1」を追加
plus1_fun = mod.add_function(
    Type.function(Type.void(), (int_type,)), "plus1")
 
# インストラクションコードを送出する
emit = Builder.new(plus1_fun.append_basic_block("entry"))
emit.call(printf,
    (
        gep_first(emit, new_str_const("%s: %d\n")),
        gep_first(emit, new_str_const("test")),
        emit.mul(plus1_fun.args[0], int_const(2))
        )
    )
emit.ret_void()
 
# --- 関数 loop() ---
# モジュールに関数「loop」を追加
loop_fun = mod.add_function(
    Type.function(Type.void(), ()), "loop")
 
# インストラクションコードを送出する
emit = Builder.new(loop_fun.append_basic_block("entry"))
count_var = emit.alloca(int_type)
 
emit.store(int_zero, count_var)
with new_block(emit, loop_fun, "loop") as (loop, _break):
    with emit_if(emit, loop_fun,
            emit.icmp(IPRED_ULT, emit.load(count_var), int_const(10))):
        emit.call(plus1_fun,
            (
                emit.load(count_var),
                )
            )
        emit.store(emit.add(emit.load(count_var), int_const(1)), count_var)
        emit.branch(loop)
emit.ret_void()
 
# ----------------------------------------------------------------------------
# 最適化
# ----------------------------------------------------------------------------

print mod
sys.exit()

mp = ModuleProvider.new(mod) 
print "BEFORE:", loop_fun
 
pm = PassManager.new()
pm.add(TargetData.new(''))
pm.add(PASS_FUNCTION_INLINING)
pm.run(mod)
 
fp = FunctionPassManager.new(mp)
fp.add(TargetData.new(''))
fp.add(PASS_BLOCK_PLACEMENT)
fp.add(PASS_INSTRUCTION_COMBINING)
fp.add(PASS_TAIL_CALL_ELIMINATION)
fp.add(PASS_AGGRESSIVE_DCE)
# fp.add(PASS_CFG_SIMPLIFICATION) # XXX: バグってる
fp.add(PASS_DEAD_INST_ELIMINATION)
fp.add(PASS_DEAD_CODE_ELIMINATION)
for fun in mod.functions:
    fp.run(fun)
 
print "AFTER:", loop_fun
 
# ----------------------------------------------------------------------------
# 実行
# ----------------------------------------------------------------------------
ee = ExecutionEngine.new(mp)
ee.run_function(loop_fun, ())
########NEW FILE########
