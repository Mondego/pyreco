__FILENAME__ = example
'''
Simple example file showing how a spreadsheet can be translated to python and executed
'''

from __future__ import division
from pycel.excelutil import *
from pycel.excellib import *
import os
from pycel.excelcompiler import ExcelCompiler
from os.path import normpath,abspath

if __name__ == '__main__':
    
    fname = normpath(abspath("../example/example.xlsx"))
    
    print "Loading %s..." % fname
    
    # load  & compile the file to a graph, starting from D1
    c = ExcelCompiler(filename=fname)
    
    print "Compiling..., starting from D1"
    sp = c.gen_graph('D1',sheet='Sheet1')
    
    # test evaluation
    print "D1 is %s" % sp.evaluate('Sheet1!D1')
    
    print "Setting A1 to 200"
    sp.set_value('Sheet1!A1',200)
    
    print "D1 is now %s (the same should happen in Excel)" % sp.evaluate('Sheet1!D1')
    
    # show the graph usisng matplotlib
    print "Plotting using matplotlib..."
    sp.plot_graph()

    # export the graph, can be loaded by a viewer like gephi
    print "Exporting to gexf..."
    sp.export_to_gexf(fname + ".gexf")
    
    print "Serializing to disk..."
    sp.save_to_file(fname + ".pickle")

    print "Done"
########NEW FILE########
__FILENAME__ = addin
"""
Simple Excel addin, requires www.pyxll.com
"""

from pyxll import xl_func, get_config, xl_macro, get_active_object
from pyxll import xl_menu
import win32api
import webbrowser
import os
import win32com.client
from pycel.excelwrapper import ExcelComWrapper
from pycel.excelcompiler import ExcelCompiler

@xl_menu("Open log file", menu="PyXLL")
def on_open_logfile():
    # the PyXLL config is accessed as a ConfigParser.ConfigParser object
    config = get_config()
    if config.has_option("LOG", "path") and config.has_option("LOG", "file"):
        path = os.path.join(config.get("LOG", "path"), config.get("LOG", "file"))
        webbrowser.open("file://%s" % path)

def xl_app():
    xl_window = get_active_object()
    xl_app = win32com.client.Dispatch(xl_window).Application
    return xl_app

@xl_menu("Compile selection", menu="Pycel")
def compile_selection_menu():
    curfile = xl_app().ActiveWorkbook.FullName
    newfile = curfile + ".pickle"
    selection = xl_app().Selection
    seed = selection.Address
    
    if not selection or seed.find(',') > 0:
        win32api.MessageBox(0, "You must select a cell or a rectangular range of cells", "Pycel")
        return
    
    res = win32api.MessageBox(0, "Going to compile %s to %s starting from %s" % (curfile,newfile,seed), "Pycel", 1)
    if res == 2: return
    
    sp = do_compilation(curfile, seed)
    win32api.MessageBox(0, "Compilation done, graph has %s nodes and %s edges" % (len(sp.G.nodes()),len(sp.G.edges())) , "Pycel")

def do_compilation(fname,seed, sheet=None):
    excel = ExcelComWrapper(fname,app=xl_app())
    c = ExcelCompiler(filename=fname, excel=excel)
    sp = c.gen_graph(seed, sheet=sheet)
    sp.save_to_file(fname + ".pickle")
    sp.export_to_gexf(fname + ".gexf")
    return sp

########NEW FILE########
__FILENAME__ = excelcompiler
import excellib
from excellib import *
from excelutil import *
from excelwrapper import ExcelComWrapper
from math import *
from networkx.classes.digraph import DiGraph
from networkx.drawing.nx_pydot import write_dot
from networkx.drawing.nx_pylab import draw, draw_circular
from networkx.readwrite.gexf import write_gexf
from tokenizer import ExcelParser, f_token, shunting_yard
import cPickle
import logging
import networkx as nx


__version__ = filter(str.isdigit, "$Revision: 2524 $")
__date__ = filter(str.isdigit, "$Date: 2011-09-06 17:05:00 +0100 (Tue, 06 Sep 2011) $")
__author__ = filter(str.isdigit, "$Author: dg2d09 $")


class Spreadsheet(object):
    def __init__(self,G,cellmap):
        super(Spreadsheet,self).__init__()
        self.G = G
        self.cellmap = cellmap
        self.params = None

    @staticmethod
    def load_from_file(fname):
        f = open(fname,'rb')
        obj = cPickle.load(f)
        #obj = load(f)
        return obj
    
    def save_to_file(self,fname):
        f = open(fname,'wb')
        cPickle.dump(self, f, protocol=2)
        f.close()

    def export_to_dot(self,fname):
        write_dot(self.G,fname)
                    
    def export_to_gexf(self,fname):
        write_gexf(self.G,fname)
    
    def plot_graph(self):
        import matplotlib.pyplot as plt

        pos=nx.spring_layout(self.G,iterations=2000)
        #pos=nx.spectral_layout(G)
        #pos = nx.random_layout(G)
        nx.draw_networkx_nodes(self.G, pos)
        nx.draw_networkx_edges(self.G, pos, arrows=True)
        nx.draw_networkx_labels(self.G, pos)
        plt.show()
    
    def set_value(self,cell,val,is_addr=True):
        if is_addr:
            cell = self.cellmap[cell]

        if cell.value != val:
            # reset the node + its dependencies
            self.reset(cell)
            # set the value
            cell.value = val
        
    def reset(self, cell):
        if cell.value is None: return
        #print "resetting", cell.address()
        cell.value = None
        map(self.reset,self.G.successors_iter(cell)) 

    def print_value_tree(self,addr,indent):
        cell = self.cellmap[addr]
        print "%s %s = %s" % (" "*indent,addr,cell.value)
        for c in self.G.predecessors_iter(cell):
            self.print_value_tree(c.address(), indent+1)

    def recalculate(self):
        for c in self.cellmap.values():
            if isinstance(c,CellRange):
                self.evaluate_range(c,is_addr=False)
            else:
                self.evaluate(c,is_addr=False)
                
    def evaluate_range(self,rng,is_addr=True):

        if is_addr:
            rng = self.cellmap[rng]

        # its important that [] gets treated ad false here
        if rng.value:
            return rng.value

        cells,nrows,ncols = rng.celladdrs,rng.nrows,rng.ncols

        if nrows == 1 or ncols == 1:
            data = [ self.evaluate(c) for c in cells ]
        else:
            data = [ [self.evaluate(c) for c in cells[i]] for i in range(len(cells)) ] 
        
        rng.value = data
        
        return data

    def evaluate(self,cell,is_addr=True):

        if is_addr:
            cell = self.cellmap[cell]
            
        # no formula, fixed value
        if not cell.formula or cell.value != None:
            #print "  returning constant or cached value for ", cell.address()
            return cell.value
        
        # recalculate formula
        # the compiled expression calls this function
        def eval_cell(address):
            return self.evaluate(address)
        
        def eval_range(rng):
            return self.evaluate_range(rng)
                
        try:
            #print "Evalling: %s, %s" % (cell.address(),cell.python_expression)
            vv = eval(cell.compiled_expression)
            #print "Cell %s evalled to %s" % (cell.address(),vv)
            if vv is None:
                print "WARNING %s is None" % (cell.address())
            cell.value = vv
        except Exception as e:
            if e.message.startswith("Problem evalling"):
                raise e
            else:
                raise Exception("Problem evalling: %s for %s, %s" % (e,cell.address(),cell.python_expression)) 
        
        return cell.value

class ASTNode(object):
    """A generic node in the AST"""
    
    def __init__(self,token):
        super(ASTNode,self).__init__()
        self.token = token
    def __str__(self):
        return self.token.tvalue
    def __getattr__(self,name):
        return getattr(self.token,name)

    def children(self,ast):
        args = ast.predecessors(self)
        args = sorted(args,key=lambda x: ast.node[x]['pos'])
        #args.reverse()
        return args

    def parent(self,ast):
        args = ast.successors(self)
        return args[0] if args else None
    
    def emit(self,ast,context=None):
        """Emit code"""
        self.token.tvalue
    
class OperatorNode(ASTNode):
    def __init__(self,*args):
        super(OperatorNode,self).__init__(*args)
        
        # convert the operator to python equivalents
        self.opmap = {
                 "^":"**",
                 "=":"==",
                 "&":"+",
                 "":"+" #union
                 }

    def emit(self,ast,context=None):
        xop = self.tvalue
        
        # Get the arguments
        args = self.children(ast)
        
        op = self.opmap.get(xop,xop)
        
        if self.ttype == "operator-prefix":
            return "-" + args[0].emit(ast,context=context)

        parent = self.parent(ast)
        # dont render the ^{1,2,..} part in a linest formula
        #TODO: bit of a hack
        if op == "**":
            if parent and parent.tvalue.lower() == "linest": 
                return args[0].emit(ast,context=context)

        #TODO silly hack to work around the fact that None < 0 is True (happens on blank cells)
        if op == "<" or op == "<=":
            aa = args[0].emit(ast,context=context)
            ss = "(" + aa + " if " + aa + " is not None else float('inf'))" + op + args[1].emit(ast,context=context)
        elif op == ">" or op == ">=":
            aa = args[1].emit(ast,context=context)
            ss =  args[0].emit(ast,context=context) + op + "(" + aa + " if " + aa + " is not None else float('inf'))"
        else:
            ss = args[0].emit(ast,context=context) + op + args[1].emit(ast,context=context)
        
        #avoid needless parentheses
        if parent and not isinstance(parent,FunctionNode):
            ss = "("+ ss + ")" 
        
        return ss

class OperandNode(ASTNode):
    def __init__(self,*args):
        super(OperandNode,self).__init__(*args)
    def emit(self,ast,context=None):
        t = self.tsubtype
        
        if t == "logical":
            return str(self.tvalue.lower() == "true")
        elif t == "text" or t == "error":
            #if the string contains quotes, escape them
            val = self.tvalue.replace('"','\\"')
            return '"' + val + '"'
        else:
            return str(self.tvalue)

class RangeNode(OperandNode):
    """Represents a spreadsheet cell or range, e.g., A5 or B3:C20"""
    def __init__(self,*args):
        super(RangeNode,self).__init__(*args)
    
    def get_cells(self):
        return resolve_range(self.tvalue)[0]
    
    def emit(self,ast,context=None):
        # resolve the range into cells
        rng = self.tvalue.replace('$','')
        sheet = context.curcell.sheet + "!" if context else ""
        if is_range(rng):
            sh,start,end = split_range(rng)
            if sh:
                str = 'eval_range("' + rng + '")'
            else:
                str = 'eval_range("' + sheet + rng + '")'
        else:
            sh,col,row = split_address(rng)
            if sh:
                str = 'eval_cell("' + rng + '")'
            else:
                str = 'eval_cell("' + sheet + rng + '")'
                
        return str
    
class FunctionNode(ASTNode):
    """AST node representing a function call"""
    def __init__(self,*args):
        super(FunctionNode,self).__init__(*args)
        self.numargs = 0

        # map  excel functions onto their python equivalents
        self.funmap = excellib.FUNCTION_MAP
        
    def emit(self,ast,context=None):
        fun = self.tvalue.lower()
        str = ''

        # Get the arguments
        args = self.children(ast)
        
        if fun == "atan2":
            # swap arguments
            str = "atan2(%s,%s)" % (args[1].emit(ast,context=context),args[0].emit(ast,context=context))
        elif fun == "pi":
            # constant, no parens
            str = "pi"
        elif fun == "if":
            # inline the if
            if len(args) == 2:
                str = "%s if %s else 0" %(args[1].emit(ast,context=context),args[0].emit(ast,context=context))
            elif len(args) == 3:
                str = "(%s if %s else %s)" % (args[1].emit(ast,context=context),args[0].emit(ast,context=context),args[2].emit(ast,context=context))
            else:
                raise Exception("if with %s arguments not supported" % len(args))

        elif fun == "array":
            str += '['
            if len(args) == 1:
                # only one row
                str += args[0].emit(ast,context=context)
            else:
                # multiple rows
                str += ",".join(['[' + n.emit(ast,context=context) + ']' for n in args])
                     
            str += ']'
        elif fun == "arrayrow":
            #simply create a list
            str += ",".join([n.emit(ast,context=context) for n in args])
        elif fun == "linest" or fun == "linestmario":
            
            str = fun + "(" + ",".join([n.emit(ast,context=context) for n in args])

            if not context:
                degree,coef = -1,-1
            else:
                #linests are often used as part of an array formula spanning multiple cells,
                #one cell for each coefficient.  We have to figure out where we currently are
                #in that range
                degree,coef = get_linest_degree(context.excel,context.curcell)
                
            # if we are the only linest (degree is one) and linest is nested -> return vector
            # else return the coef.
            if degree == 1 and self.parent(ast):
                if fun == "linest":
                    str += ",degree=%s)" % degree
                else:
                    str += ")"
            else:
                if fun == "linest":
                    str += ",degree=%s)[%s]" % (degree,coef-1)
                else:
                    str += ")[%s]" % (coef-1)

        elif fun == "and":
            str = "all([" + ",".join([n.emit(ast,context=context) for n in args]) + "])"
        elif fun == "or":
            str = "any([" + ",".join([n.emit(ast,context=context) for n in args]) + "])"
        else:
            # map to the correct name
            f = self.funmap.get(fun,fun)
            str = f + "(" + ",".join([n.emit(ast,context=context) for n in args]) + ")"

        return str

def create_node(t):
    """Simple factory function"""
    if t.ttype == "operand":
        if t.tsubtype == "range":
            return RangeNode(t)
        else:
            return OperandNode(t)
    elif t.ttype == "function":
        return FunctionNode(t)
    elif t.ttype.startswith("operator"):
        return OperatorNode(t)
    else:
        return ASTNode(t)

class Operator:
    """Small wrapper class to manage operators during shunting yard"""
    def __init__(self,value,precedence,associativity):
        self.value = value
        self.precedence = precedence
        self.associativity = associativity

def shunting_yard(expression):
    """
    Tokenize an excel formula expression into reverse polish notation
    
    Core algorithm taken from wikipedia with varargs extensions from
    http://www.kallisti.net.nz/blog/2008/02/extension-to-the-shunting-yard-algorithm-to-allow-variable-numbers-of-arguments-to-functions/
    """
    #remove leading =
    if expression.startswith('='):
        expression = expression[1:]
        
    p = ExcelParser();
    p.parse(expression)

    # insert tokens for '(' and ')', to make things clearer below
    tokens = []
    for t in p.tokens.items:
        if t.ttype == "function" and t.tsubtype == "start":
            t.tsubtype = ""
            tokens.append(t)
            tokens.append(f_token('(','arglist','start'))
        elif t.ttype == "function" and t.tsubtype == "stop":
            tokens.append(f_token(')','arglist','stop'))
        elif t.ttype == "subexpression" and t.tsubtype == "start":
            t.tvalue = '('
            tokens.append(t)
        elif t.ttype == "subexpression" and t.tsubtype == "stop":
            t.tvalue = ')'
            tokens.append(t)
        else:
            tokens.append(t)

    #print "tokens: ", "|".join([x.tvalue for x in tokens])

    #http://office.microsoft.com/en-us/excel-help/calculation-operators-and-precedence-HP010078886.aspx
    operators = {}
    operators[':'] = Operator(':',8,'left')
    operators[''] = Operator(' ',8,'left')
    operators[','] = Operator(',',8,'left')
    operators['u-'] = Operator('u-',7,'left') #unary negation
    operators['%'] = Operator('%',6,'left')
    operators['^'] = Operator('^',5,'left')
    operators['*'] = Operator('*',4,'left')
    operators['/'] = Operator('/',4,'left')
    operators['+'] = Operator('+',3,'left')
    operators['-'] = Operator('-',3,'left')
    operators['&'] = Operator('&',2,'left')
    operators['='] = Operator('=',1,'left')
    operators['<'] = Operator('<',1,'left')
    operators['>'] = Operator('>',1,'left')
    operators['<='] = Operator('<=',1,'left')
    operators['>='] = Operator('>=',1,'left')
    operators['<>'] = Operator('<>',1,'left')
            
    output = collections.deque()
    stack = []
    were_values = []
    arg_count = []
    
    for t in tokens:
        if t.ttype == "operand":

            output.append(create_node(t))
            if were_values:
                were_values.pop()
                were_values.append(True)
                
        elif t.ttype == "function":

            stack.append(t)
            arg_count.append(0)
            if were_values:
                were_values.pop()
                were_values.append(True)
            were_values.append(False)
            
        elif t.ttype == "argument":
            
            while stack and (stack[-1].tsubtype != "start"):
                output.append(create_node(stack.pop()))   
            
            if were_values.pop(): arg_count[-1] += 1
            were_values.append(False)
            
            if not len(stack):
                raise Exception("Mismatched or misplaced parentheses")
        
        elif t.ttype.startswith('operator'):

            if t.ttype.endswith('-prefix') and t.tvalue =="-":
                o1 = operators['u-']
            else:
                o1 = operators[t.tvalue]

            while stack and stack[-1].ttype.startswith('operator'):
                
                if stack[-1].ttype.endswith('-prefix') and stack[-1].tvalue =="-":
                    o2 = operators['u-']
                else:
                    o2 = operators[stack[-1].tvalue]
                
                if ( (o1.associativity == "left" and o1.precedence <= o2.precedence)
                        or
                      (o1.associativity == "right" and o1.precedence < o2.precedence) ):
                    
                    output.append(create_node(stack.pop()))
                else:
                    break
                
            stack.append(t)
        
        elif t.tsubtype == "start":
            stack.append(t)
            
        elif t.tsubtype == "stop":
            
            while stack and stack[-1].tsubtype != "start":
                output.append(create_node(stack.pop()))
            
            if not stack:
                raise Exception("Mismatched or misplaced parentheses")
            
            stack.pop()

            if stack and stack[-1].ttype == "function":
                f = create_node(stack.pop())
                a = arg_count.pop()
                w = were_values.pop()
                if w: a += 1
                f.num_args = a
                #print f, "has ",a," args"
                output.append(f)

    while stack:
        if stack[-1].tsubtype == "start" or stack[-1].tsubtype == "stop":
            raise Exception("Mismatched or misplaced parentheses")
        
        output.append(create_node(stack.pop()))

    #print "Stack is: ", "|".join(stack)
    #print "Ouput is: ", "|".join([x.tvalue for x in output])
    
    # convert to list
    result = [x for x in output]
    return result
   
def build_ast(expression):
    """build an AST from an Excel formula expression in reverse polish notation"""
    
    #use a directed graph to store the tree
    G = DiGraph()
    
    stack = []
    
    for n in expression:
        # Since the graph does not maintain the order of adding nodes/edges
        # add an extra attribute 'pos' so we can always sort to the correct order
        if isinstance(n,OperatorNode):
            if n.ttype == "operator-infix":
                arg2 = stack.pop()
                arg1 = stack.pop()
                G.add_node(arg1,{'pos':1})
                G.add_node(arg2,{'pos':2})
                G.add_edge(arg1, n)
                G.add_edge(arg2, n)
            else:
                arg1 = stack.pop()
                G.add_node(arg1,{'pos':1})
                G.add_edge(arg1, n)
                
        elif isinstance(n,FunctionNode):
            args = [stack.pop() for _ in range(n.num_args)]
            args.reverse()
            for i,a in enumerate(args):
                G.add_node(a,{'pos':i})
                G.add_edge(a,n)
            #for i in range(n.num_args):
            #    G.add_edge(stack.pop(),n)
        else:
            G.add_node(n,{'pos':0})

        stack.append(n)
        
    return G,stack.pop()

class Context(object):
    """A small context object that nodes in the AST can use to emit code"""
    def __init__(self,curcell,excel):
        # the current cell for which we are generating code
        self.curcell = curcell
        # a handle to an excel instance
        self.excel = excel

class ExcelCompiler(object):
    """Class responsible for taking an Excel spreadsheet and compiling it to a Spreadsheet instance
       that can be serialized to disk, and executed independently of excel.
       
       Must be run on Windows as it requires a COM link to an Excel instance.
       """
       
    def __init__(self, filename=None, excel=None, *args,**kwargs):

        super(ExcelCompiler,self).__init__()
        self.filename = filename
        
        if excel:
            # if we are running as an excel addin, this gets passed to us
            self.excel = excel
        else:
            # TODO: use a proper interface so we can (eventually) support loading from file (much faster)  Still need to find a good lib though.
            self.excel = ExcelComWrapper(filename=filename)
            self.excel.connect()
            
        self.log = logging.getLogger("decode.{0}".format(self.__class__.__name__))
        
    def cell2code(self,cell):
        """Generate python code for the given cell"""
        if cell.formula:
            e = shunting_yard(cell.formula or str(cell.value))
            ast,root = build_ast(e)
            code = root.emit(ast,context=Context(cell,self.excel))
        else:
            ast = None
            code = str('"' + cell.value + '"' if isinstance(cell.value,unicode) else cell.value)
            
        return code,ast

    def add_node_to_graph(self,G, n):
        G.add_node(n)
        G.node[n]['sheet'] = n.sheet
        
        if isinstance(n,Cell):
            G.node[n]['label'] = n.col + str(n.row)
        else:
            #strip the sheet
            G.node[n]['label'] = n.address()[n.address().find('!')+1:]
            
    def gen_graph(self, seed, sheet=None):
        """Given a starting point (e.g., A6, or A3:B7) on a particular sheet, generate
           a Spreadsheet instance that captures the logic and control flow of the equations."""
        
        # starting points
        cursheet = sheet if sheet else self.excel.get_active_sheet()
        self.excel.set_sheet(cursheet)
        
        seeds,nr,nc = Cell.make_cells(self.excel, seed, sheet=cursheet)
        seeds = list(flatten(seeds))
        
        print "Seed %s expanded into %s cells" % (seed,len(seeds))
        
        # only keep seeds with formulas or numbers
        seeds = [s for s in seeds if s.formula or isinstance(s.value,(int,float))]

        print "%s filtered seeds " % len(seeds)
        
        # cells to analyze: only formulas
        todo = [s for s in seeds if s.formula]

        print "%s cells on the todo list" % len(todo)

        # map of all cells
        cellmap = dict([(x.address(),x) for x in seeds])
        
        # directed graph
        G = nx.DiGraph()

        # match the info in cellmap
        for c in cellmap.itervalues(): self.add_node_to_graph(G, c)

        while todo:
            c1 = todo.pop()
            
            print "Handling ", c1.address()
            
            # set the current sheet so relative addresses resolve properly
            if c1.sheet != cursheet:
                cursheet = c1.sheet
                self.excel.set_sheet(cursheet)
            
            # parse the formula into code
            pystr,ast = self.cell2code(c1)

            # set the code & compile it (will flag problems sooner rather than later)
            c1.python_expression = pystr
            c1.compile()                
            
            # get all the cells/ranges this formula refers to
            deps = [x.tvalue.replace('$','') for x in ast.nodes() if isinstance(x,RangeNode)]
            
            # remove dupes
            deps = uniqueify(deps)
            
            for dep in deps:
                
                # if the dependency is a multi-cell range, create a range object
                if is_range(dep):
                    # this will make sure we always have an absolute address
                    rng = CellRange(dep,sheet=cursheet)
                    
                    if rng.address() in cellmap:
                        # already dealt with this range
                        # add an edge from the range to the parent
                        G.add_edge(cellmap[rng.address()],cellmap[c1.address()])
                        continue
                    else:
                        # turn into cell objects
                        cells,nrows,ncols = Cell.make_cells(self.excel,dep,sheet=cursheet)

                        # get the values so we can set the range value
                        if nrows == 1 or ncols == 1:
                            rng.value = [c.value for c in cells]
                        else:
                            rng.value = [ [c.value for c in cells[i]] for i in range(len(cells)) ] 

                        # save the range
                        cellmap[rng.address()] = rng
                        # add an edge from the range to the parent
                        self.add_node_to_graph(G, rng)
                        G.add_edge(rng,cellmap[c1.address()])
                        # cells in the range should point to the range as their parent
                        target = rng
                else:
                    # not a range, create the cell object
                    cells = [Cell.resolve_cell(self.excel, dep, sheet=cursheet)]
                    target = cellmap[c1.address()]

                # process each cell                    
                for c2 in flatten(cells):
                    # if we havent treated this cell allready
                    if c2.address() not in cellmap:
                        if c2.formula:
                            # cell with a formula, needs to be added to the todo list
                            todo.append(c2)
                            #print "appended ", c2.address()
                        else:
                            # constant cell, no need for further processing, just remember to set the code
                            pystr,ast = self.cell2code(c2)
                            c2.python_expression = pystr
                            c2.compile()     
                            #print "skipped ", c2.address()
                        
                        # save in the cellmap
                        cellmap[c2.address()] = c2
                        # add to the graph
                        self.add_node_to_graph(G, c2)
                        
                    # add an edge from the cell to the parent (range or cell)
                    G.add_edge(cellmap[c2.address()],target)
            
        print "Graph construction done, %s nodes, %s edges, %s cellmap entries" % (len(G.nodes()),len(G.edges()),len(cellmap))

        sp = Spreadsheet(G,cellmap)
        
        return sp

if __name__ == '__main__':
    
    # some test formulas
    inputs = [
              '=SUM((A:A 1:1))',
              '=A1',
              '=atan2(A1,B1)',
              '=5*log(sin()+2)',
              '=5*log(sin(3,7,9)+2)',
              '=3 + 4 * 2 / ( 1 - 5 ) ^ 2 ^ 3',
              '=1+3+5',
              '=3 * 4 + 5',
              '=50',
              '=1+1',
              '=$A1',
              '=$B$2',
              '=SUM(B5:B15)',
              '=SUM(B5:B15,D5:D15)',
              '=SUM(B5:B15 A7:D7)',
              '=SUM(sheet1!$A$1:$B$2)',
              '=[data.xls]sheet1!$A$1',
              '=SUM((A:A,1:1))',
              '=SUM((A:A A1:B1))',
              '=SUM(D9:D11,E9:E11,F9:F11)',
              '=SUM((D9:D11,(E9:E11,F9:F11)))',
              '=IF(P5=1.0,"NA",IF(P5=2.0,"A",IF(P5=3.0,"B",IF(P5=4.0,"C",IF(P5=5.0,"D",IF(P5=6.0,"E",IF(P5=7.0,"F",IF(P5=8.0,"G"))))))))',
              '={SUM(B2:D2*B3:D3)}',
              '=SUM(123 + SUM(456) + (45<6))+456+789',
              '=AVG(((((123 + 4 + AVG(A1:A2))))))',
              
              # E. W. Bachtal's test formulae
              '=IF("a"={"a","b";"c",#N/A;-1,TRUE}, "yes", "no") &   "  more ""test"" text"',
              #'=+ AName- (-+-+-2^6) = {"A","B"} + @SUM(R1C1) + (@ERROR.TYPE(#VALUE!) = 2)',
              '=IF(R13C3>DATE(2002,1,6),0,IF(ISERROR(R[41]C[2]),0,IF(R13C3>=R[41]C[2],0, IF(AND(R[23]C[11]>=55,R[24]C[11]>=20),R53C3,0))))',
              '=IF(R[39]C[11]>65,R[25]C[42],ROUND((R[11]C[11]*IF(OR(AND(R[39]C[11]>=55, ' + 
                  'R[40]C[11]>=20),AND(R[40]C[11]>=20,R11C3="YES")),R[44]C[11],R[43]C[11]))+(R[14]C[11] ' +
                  '*IF(OR(AND(R[39]C[11]>=55,R[40]C[11]>=20),AND(R[40]C[11]>=20,R11C3="YES")), ' +
                  'R[45]C[11],R[43]C[11])),0))',
              '=(propellor_charts!B22*(propellor_charts!E21+propellor_charts!D21*(engine_data!O16*D70+engine_data!P16)+propellor_charts!C21*(engine_data!O16*D70+engine_data!P16)^2+propellor_charts!B21*(engine_data!O16*D70+engine_data!P16)^3)^2)^(1/3)*(1*D70/5.33E-18)^(2/3)*0.0000000001*28.3495231*9.81/1000',
              '=(3600/1000)*E40*(E8/E39)*(E15/E19)*LN(E54/(E54-E48))',
              '=IF(P5=1.0,"NA",IF(P5=2.0,"A",IF(P5=3.0,"B",IF(P5=4.0,"C",IF(P5=5.0,"D",IF(P5=6.0,"E",IF(P5=7.0,"F",IF(P5=8.0,"G"))))))))',
              '=LINEST(X5:X32,W5:W32^{1,2,3})',
              '=IF(configurations!$G$22=3,sizing!$C$303,M14)',
              '=0.000001042*E226^3-0.00004777*E226^2+0.0007646*E226-0.00075',
              '=LINEST(G2:G17,E2:E17,FALSE)',
              '=IF(AI119="","",E119)',
              '=LINEST(B32:(INDEX(B32:B119,MATCH(0,B32:B119,-1),1)),(F32:(INDEX(B32:F119,MATCH(0,B32:B119,-1),5)))^{1,2,3,4})',
              ]

    for i in inputs:
        print "**************************************************"
        print "Formula: ", i

        e = shunting_yard(i);
        print "RPN: ",  "|".join([str(x) for x in e])
        
        G,root = build_ast(e)
        
        print "Python code: ", root.emit(G,context=None)
        print "**************************************************"

########NEW FILE########
__FILENAME__ = excellib
'''
Python equivalents of various excel functions
'''
from __future__ import division
import numpy as np
from math import log
from pycel.excelutil import flatten

######################################################################################
# A dictionary that maps excel function names onto python equivalents. You should
# only add an entry to this map if the python name is different to the excel name
# (which it may need to be to  prevent conflicts with existing python functions 
# with that name, e.g., max).

# So if excel defines a function foobar(), all you have to do is add a function
# called foobar to this module.  You only need to add it to the function map,
# if you want to use a different name in the python code. 

# Note: some functions (if, pi, atan2, and, or, array, ...) are already taken care of
# in the FunctionNode code, so adding them here will have no effect.
FUNCTION_MAP = {
      "ln":"xlog",
      "min":"xmin",
      "min":"xmin",
      "max":"xmax",
      "sum":"xsum",
      "gammaln":"lgamma"
      }

######################################################################################
# List of excel equivalent functions
# TODO: needs unit testing

def value(text):
    # make the distinction for naca numbers
    if text.find('.') > 0:
        return float(text)
    else:
        return int(text)

def xlog(a):
    if isinstance(a,(list,tuple,np.ndarray)):
        return [log(x) for x in flatten(a)]
    else:
        #print a
        return log(a)

def xmax(*args):
    # ignore non numeric cells
    data = [x for x in flatten(args) if isinstance(x,(int,float))]
    
    # however, if no non numeric cells, return zero (is what excel does)
    if len(data) < 1:
        return 0
    else:
        return max(data)

def xmin(*args):
    # ignore non numeric cells
    data = [x for x in flatten(args) if isinstance(x,(int,float))]
    
    # however, if no non numeric cells, return zero (is what excel does)
    if len(data) < 1:
        return 0
    else:
        return min(data)

def xsum(*args):
    # ignore non numeric cells
    data = [x for x in flatten(args) if isinstance(x,(int,float))]
    
    # however, if no non numeric cells, return zero (is what excel does)
    if len(data) < 1:
        return 0
    else:
        return sum(data)

def average(*args):
    l = list(flatten(*args))
    return sum(l) / len(l)
    
def right(text,n):
    #TODO: hack to deal with naca section numbers
    if isinstance(text, unicode) or isinstance(text,str):
        return text[-n:]
    else:
        # TODO: get rid of the decimal
        return str(int(text))[-n:]

    
def index(*args):
    array = args[0]
    row = args[1]
    
    if len(args) == 3:
        col = args[2]
    else:
        col = 1
        
    if isinstance(array[0],(list,tuple,np.ndarray)):
        # rectangular array
        array[row-1][col-1]
    elif row == 1 or col == 1:
        return array[row-1] if col == 1 else array[col-1]
    else:
        raise Exception("index (%s,%s) out of range for %s" %(row,col,array))
        

def lookup(value, lookup_range, result_range):
    
    # TODO
    if not isinstance(value,(int,float)):
        raise Exception("Non numeric lookups (%s) not supported" % value)
    
    # TODO: note, may return the last equal value
    
    # index of the last numeric value
    lastnum = -1
    for i,v in enumerate(lookup_range):
        if isinstance(v,(int,float)):
            if v > value:
                break
            else:
                lastnum = i
                

    if lastnum < 0:
        raise Exception("No numeric data found in the lookup range")
    else:
        if i == 0:
            raise Exception("All values in the lookup range are bigger than %s" % value)
        else:
            if i >= len(lookup_range)-1:
                # return the biggest number smaller than value
                return result_range[lastnum]
            else:
                return result_range[i-1]

def linest(*args, **kwargs):

    Y = args[0]
    X = args[1]
    
    if len(args) == 3:
        const = args[2]
        if isinstance(const,str):
            const = (const.lower() == "true")
    else:
        const = True
        
    degree = kwargs.get('degree',1)
    
    # build the vandermonde matrix
    A = np.vander(X, degree+1)
    
    if not const:
        # force the intercept to zero
        A[:,-1] = np.zeros((1,len(X)))
    
    # perform the fit
    (coefs, residuals, rank, sing_vals) = np.linalg.lstsq(A, Y)
        
    return coefs

def npv(*args):
    discount_rate = args[0]
    cashflow = args[1]
    return sum([float(x)*(1+discount_rate)**-(i+1) for (i,x) in enumerate(cashflow)])

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = excelutil
from __future__ import division
from itertools import izip
import collections
import functools
import re
import string

#TODO: only supports rectangular ranges
class CellRange(object):
    def __init__(self,address,sheet=None):

        self.__address = address.replace('$','')
        
        sh,start,end = split_range(address)
        if not sh and not sheet:
            raise Exception("Must pass in a sheet")
        
        # make sure the address is always prefixed with the range
        if sh:
            sheet = sh
        else:
            self.__address = sheet + "!" + self.__address
        
        addr,nrows,ncols = resolve_range(address,sheet=sheet)
        
        # dont allow messing with these params
        self.__celladdr = addr
        self.__nrows = nrows
        self.__ncols = ncols
        self.__sheet = sheet
        
        self.value = None

    def __str__(self):
        return self.__address 
    
    def address(self):
        return self.__address
    
    @property
    def celladdrs(self):
        return self.__celladdr
    
    @property
    def nrows(self):
        return self.__nrows

    @property
    def ncols(self):
        return self.__ncols

    @property
    def sheet(self):
        return self.__sheet
    
class Cell(object):
    ctr = 0
    
    @classmethod
    def next_id(cls):
        cls.ctr += 1
        return cls.ctr
    
    def __init__(self, address, sheet, value=None, formula=None):
        super(Cell,self).__init__()
        
        # remove $'s
        address = address.replace('$','')
        
        sh,c,r = split_address(address)
        
        # both are empty
        if not sheet and not sh:
            raise Exception("Sheet name may not be empty for cell address %s" % address)
        # both exist but disagree
        elif sh and sheet and sh != sheet:
            raise Exception("Sheet name mismatch for cell address %s: %s vs %s" % (address,sheet, sh))
        elif not sh and sheet:
            sh = sheet 
        else:
            pass
                
        # we assume a cell's location can never change
        self.__sheet = str(sheet)
        self.__formula = str(formula) if formula else None
        
        self.__sheet = sh
        self.__col = c
        self.__row = int(r)
        self.__col_idx = col2num(c)
            
        self.value = str(value) if isinstance(value,unicode) else value
        self.python_expression = None
        self._compiled_expression = None
        
        # every cell has a unique id
        self.__id = Cell.next_id()

    @property
    def sheet(self):
        return self.__sheet

    @property
    def row(self):
        return self.__row

    @property
    def col(self):
        return self.__col

    @property
    def formula(self):
        return self.__formula

    @property
    def id(self):
        return self.__id

    @property
    def compiled_expression(self):
        return self._compiled_expression

    # code objects are not serializable
    def __getstate__(self):
        d = dict(self.__dict__)
        f = '_compiled_expression'
        if f in d: del d[f]
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.compile() 
    
    def clean_name(self):
        return self.address().replace('!','_').replace(' ','_')
        
    def address(self, absolute=True):
        if absolute:
            return "%s!%s%s" % (self.__sheet,self.__col,self.__row)
        else:
            return "%s%s" % (self.__col,self.__row)
    
    def address_parts(self):
        return (self.__sheet,self.__col,self.__row,self.__col_idx)
        
    def compile(self):
        if not self.python_expression: return
        
        # if we are a constant string, surround by quotes
        if isinstance(self.value,(str,unicode)) and not self.formula and not self.python_expression.startswith('"'):
            self.python_expression='"' + self.python_expression + '"'
        
        try:
            self._compiled_expression = compile(self.python_expression,'<string>','eval')
        except Exception as e:
            raise Exception("Failed to compile cell %s with expression %s: %s" % (self.address(),self.python_expression,e)) 
    
    def __str__(self):
        if self.formula:
            return "%s%s" % (self.address(), self.formula)
        else:
            return "%s=%s" % (self.address(), self.value)

    @staticmethod
    def inc_col_address(address,inc):
        sh,col,row = split_address(address)
        return "%s!%s%s" % (sh,num2col(col2num(col) + inc),row)

    @staticmethod
    def inc_row_address(address,inc):
        sh,col,row = split_address(address)
        return "%s!%s%s" % (sh,col,row+inc)
        
    @staticmethod
    def resolve_cell(excel, address, sheet=None):
        r = excel.get_range(address)
        f = r.Formula if r.Formula.startswith('=') else None
        v = r.Value
        
        sh,c,r = split_address(address)
        
        # use the sheet specified in the cell, else the passed sheet
        if sh: sheet = sh

        c = Cell(address,sheet,value=v, formula=f)
        return c

    @staticmethod
    def make_cells(excel, range, sheet=None):
        cells = [];

        if is_range(range):
            # use the sheet specified in the range, else the passed sheet
            sh,start,end = split_range(range)
            if sh: sheet = sh

            ads,numrows,numcols = resolve_range(range)
            # ensure in the same nested format as fs/vs will be
            if numrows == 1:
                ads = [ads]
            elif numcols == 1:
                ads = [[x] for x in ads]
                
            # get everything in blocks, is faster
            r = excel.get_range(range)
            fs = r.Formula
            vs = r.Value
            
            for it in (list(izip(*x)) for x in izip(ads,fs,vs)):
                row = []
                for c in it:
                    a = c[0]
                    f = c[1] if c[1] and c[1].startswith('=') else None
                    v = c[2]
                    cl = Cell(a,sheet,value=v, formula=f)
                    row.append(cl)
                cells.append(row)
            
            #return as vector
            if numrows == 1:
                cells = cells[0]
            elif numcols == 1:
                cells = [x[0] for x in cells]
            else:
                pass
        else:
            c = Cell.resolve_cell(excel, range, sheet=sheet)
            cells.append(c)

            numrows = 1
            numcols = 1
            
        return (cells,numrows,numcols)
    
def is_range(address):
    return address.find(':') > 0

def split_range(rng):
    if rng.find('!') > 0:
        sh,r = rng.split("!")
        start,end = r.split(':')
    else:
        sh = None
        start,end = rng.split(':')
    
    return sh,start,end
        
def split_address(address):
    sheet = None
    if address.find('!') > 0:
        sheet,address = address.split('!')
    
    #ignore case
    address = address.upper()
    
    # regular <col><row> format    
    if re.match('^[A-Z\$]+[\d\$]+$', address):
        col,row = filter(None,re.split('([A-Z\$]+)',address))
    # R<row>C<col> format
    elif re.match('^R\d+C\d+$', address):
        row,col = address.split('C')
        row = row[1:]
    # R[<row>]C[<col>] format
    elif re.match('^R\[\d+\]C\[\d+\]$', address):
        row,col = address.split('C')
        row = row[2:-1]
        col = col[2:-1]
    else:
        raise Exception('Invalid address format ' + address)
    
    return (sheet,col,row)

def resolve_range(rng, flatten=False, sheet=''):
    
    sh, start, end = split_range(rng)
    
    if sh and sheet:
        if sh != sheet:
            raise Exception("Mismatched sheets %s and %s" % (sh,sheet))
        else:
            sheet += '!'
    elif sh and not sheet:
        sheet = sh + "!"
    elif sheet and not sh:
        sheet += "!"
    else:
        pass

    # single cell, no range
    if not is_range(rng):  return ([sheet + rng],1,1)

    sh, start_col, start_row = split_address(start)
    sh, end_col, end_row = split_address(end)
    start_col_idx = col2num(start_col)
    end_col_idx = col2num(end_col);

    start_row = int(start_row)
    end_row = int(end_row)

    # single column
    if  start_col == end_col:
        nrows = end_row - start_row + 1
        data = [ "%s%s%s" % (s,c,r) for (s,c,r) in zip([sheet]*nrows,[start_col]*nrows,range(start_row,end_row+1))]
        return data,len(data),1
    
    # single row
    elif start_row == end_row:
        ncols = end_col_idx - start_col_idx + 1
        data = [ "%s%s%s" % (s,num2col(c),r) for (s,c,r) in zip([sheet]*ncols,range(start_col_idx,end_col_idx+1),[start_row]*ncols)]
        return data,1,len(data)
    
    # rectangular range
    else:
        cells = []
        for r in range(start_row,end_row+1):
            row = []
            for c in range(start_col_idx,end_col_idx+1):
                row.append(sheet + num2col(c) + str(r))
                
            cells.append(row)
    
        if flatten:
            # flatten into one list
            l = flatten(cells)
            return l,1,len(l)
        else:
            return cells, len(cells), len(cells[0]) 

# e.g., convert BA -> 53
def col2num(col):
    
    if not col:
        raise Exception("Column may not be empty")
    
    tot = 0
    for i,c in enumerate([c for c in col[::-1] if c != "$"]):
        if c == '$': continue
        tot += (ord(c)-64) * 26 ** i
    return tot

# convert back
def num2col(num):
    
    if num < 1:
        raise Exception("Number must be larger than 0: %s" % num)
    
    s = ''
    q = num
    while q > 0:
        (q,r) = divmod(q,26)
        if r == 0:
            q = q - 1
            r = 26
        s = string.ascii_uppercase[r-1] + s
    return s

def address2index(a):
    sh,c,r = split_address(a)
    return (col2num(c),int(r))

def index2addres(c,r,sheet=None):
    return "%s%s%s" % (sheet + "!" if sheet else "", num2col(c), r)

def get_linest_degree(excel,cl):
    # TODO: assumes a row or column of linest formulas & that all coefficients are needed

    sh,c,r,ci = cl.address_parts()
    # figure out where we are in the row

    # to the left
    i = ci - 1
    while i > 0:
        f = excel.get_formula_from_range(index2addres(i,r))
        if f is None or f != cl.formula:
            break
        else:
            i = i - 1
        
    # to the right
    j = ci + 1
    while True:
        f = excel.get_formula_from_range(index2addres(j,r))
        if f is None or f != cl.formula:
            break
        else:
            j = j + 1
    
    # assume the degree is the number of linest's
    degree =  (j - i - 1) - 1  #last -1 is because an n degree polynomial has n+1 coefs

    # which coef are we (left most coef is the coef for the highest power)
    coef = ci - i 

    # no linests left or right, try looking up/down
    if degree == 0:
        # up
        i = r - 1
        while i > 0:
            f = excel.get_formula_from_range("%s%s" % (c,i))
            if f is None or f != cl.formula:
                break
            else:
                i = i - 1
            
        # down
        j = r + 1
        while True:
            f = excel.get_formula_from_range("%s%s" % (c,j))
            if f is None or f != cl.formula:
                break
            else:
                j = j + 1

        degree =  (j - i - 1) - 1
        coef = r - i
    
    # if degree is zero -> only one linest formula -> linear regression -> degree should be one
    return (max(degree,1),coef) 

def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el

def uniqueify(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

if __name__ == '__main__':
    pass
########NEW FILE########
__FILENAME__ = excelwrapper
try:
    import win32com.client
    #http://www.py2exe.org/index.cgi/IncludingTypelibs
    #win32com.client.gencache.is_readonly=False
    #win32com.client.gencache.GetGeneratePath()
    from win32com.client import Dispatch
    from win32com.client import constants 
    import pythoncom
except Exception as e:
    print "WARNING: cant import win32com stuff:",e

import os
from os import path

class ExcelComWrapper(object):
    
    def __init__(self, filename, app=None):
        
        super(ExcelComWrapper,self).__init__()
        
        self.filename = path.abspath(filename)
        self.app = app
      
    def connect(self):
        #http://devnulled.com/content/2004/01/com-objects-and-threading-in-python/
        # TODO: dont need to uninit?
        #pythoncom.CoInitialize()
        if not self.app:
            self.app = Dispatch("Excel.Application")
            self.app.Visible = True
            self.app.DisplayAlerts = 0
            self.app.Workbooks.Open(self.filename)
        else:
            # if we are running as an excel addin, this gets passed to us
            pass
    
    def save(self):
        self.app.ActiveWorkbook.Save()
    
    def save_as(self, filename, delete_existing=False):
        if delete_existing and os.path.exists(filename):
            os.remove(filename)
        self.app.ActiveWorkbook.SaveAs(filename)
  
    def close(self):
        self.app.ActiveWorkbook.Close(False)
  
    def quit(self):
        return self.app.Quit()

    def set_sheet(self,s):
        return self.app.ActiveWorkbook.Worksheets(s).Activate()
    
    def get_sheet(self):
        return self.app.ActiveWorkbook.ActiveSheet
            
    def get_range(self, range):
        #print '*',range
        if range.find('!') > 0:
            sheet,range = range.split('!')
            return self.app.ActiveWorkbook.Worksheets(sheet).Range(range)
        else:        
            return self.app.ActiveWorkbook.ActiveSheet.Range(range)

    def get_used_range(self):
        return self.app.ActiveWorkbook.ActiveSheet.UsedRange

    def get_active_sheet(self):
        return self.app.ActiveWorkbook.ActiveSheet.Name
    
    def get_cell(self,r,c):
        return self.app.ActiveWorkbook.ActiveSheet.Cells(r,c)
        
    def get_value(self,r,c):
        return self.get_cell(r, c).Value
    
    def set_value(self,r,c,val):
        self.get_cell(r, c).Value = val

    def get_formula(self,r,c):
        f = self.get_cell(r, c).Formula
        return f if f.startswith("=") else None 
    
    def has_formula(self,range):
        f = self.get_range(range).Formula
        return f and f.startswith("=")
    
    def get_formula_from_range(self,range):
        f = self.get_range(range).Formula
        if isinstance(f, (list,tuple)):
            if any(filter(lambda x: x[0].startswith("="),f)):
                return [x[0] for x in f];
            else:
                return None
        else:
            return f if f.startswith("=") else None 
    
    def get_formula_or_value(self,name):
        r = self.get_range(name)
        return r.Formula or r.Value

    def get_row(self,row):
        return [self.get_value(row,col+1) for col in range(self.get_used_range().Columns.Count)]

    def set_calc_mode(self,automatic=True):
        if automatic:
            self.app.Calculation = constants.xlCalculationAutomatic
        else:
            self.app.Calculation = constants.xlCalculationManual

    def set_screen_updating(self,update):
        self.app.ScreenUpdating = update

    def run_macro(self,macro):
        self.app.Run(macro)

########NEW FILE########
__FILENAME__ = tokenizer
#========================================================================
# Description: Tokenise an Excel formula using an implementation of
#              E. W. Bachtal's algorithm, found here:
#
#                  http://ewbi.blogs.com/develops/2004/12/excel_formula_p.html
#
#              Tested with Python v2.5 (win32)
#      Author: Robin Macharg
#   Copyright: Algorithm (c) E. W. Bachtal, this implementation (c) R. Macharg
#
# CVS Info:
# $Header: T:\\cvsarchive/Excel\040export\040&\040import\040XML/ExcelXMLTransform/EWBI_Javascript_port/jsport.py,v 1.5 2006/12/07 13:41:08 rmacharg Exp $
#
# Modification History
#
# Date         Author Comment
# =======================================================================
# 2006/11/29 - RMM  - Made strictly class-based.
#                     Added parse, render and pretty print methods
# 2006/11    - RMM  - RMM = Robin Macharg
#                           Created
# 2011/10    - Dirk Gorissen - Patch to support scientific notation
#========================================================================
import re
import collections

#========================================================================
#       Class: ExcelParserTokens
# Description: Inheritable container for token definitions
#
#  Attributes: Self explanatory
#
#     Methods: None
#========================================================================
class ExcelParserTokens:
    TOK_TYPE_NOOP           = "noop";
    TOK_TYPE_OPERAND        = "operand";
    TOK_TYPE_FUNCTION       = "function";
    TOK_TYPE_SUBEXPR        = "subexpression";
    TOK_TYPE_ARGUMENT       = "argument";
    TOK_TYPE_OP_PRE         = "operator-prefix";
    TOK_TYPE_OP_IN          = "operator-infix";
    TOK_TYPE_OP_POST        = "operator-postfix";
    TOK_TYPE_WSPACE         = "white-space";
    TOK_TYPE_UNKNOWN        = "unknown"
    
    TOK_SUBTYPE_START       = "start";
    TOK_SUBTYPE_STOP        = "stop";
    TOK_SUBTYPE_TEXT        = "text";
    TOK_SUBTYPE_NUMBER      = "number";
    TOK_SUBTYPE_LOGICAL     = "logical";
    TOK_SUBTYPE_ERROR       = "error";
    TOK_SUBTYPE_RANGE       = "range";
    TOK_SUBTYPE_MATH        = "math";
    TOK_SUBTYPE_CONCAT      = "concatenate";
    TOK_SUBTYPE_INTERSECT   = "intersect";
    TOK_SUBTYPE_UNION       = "union";

#========================================================================
#       Class: f_token 
# Description: Encapsulate a formula token
#
#  Attributes:   tvalue - 
#                 ttype - See token definitions, above, for values
#              tsubtype - See token definitions, above, for values
#
#     Methods: f_token  - __init__()
#========================================================================
class f_token:
    def __init__(self, value, type, subtype):
        self.tvalue   = value
        self.ttype    = type
        self.tsubtype = subtype

    def __str__(self):
        return self.tvalue
#========================================================================
#       Class: f_tokens 
# Description: An ordered list of tokens

#  Attributes:        items - Ordered list 
#                     index - Current position in the list
#
#     Methods: f_tokens     - __init__()
#              f_token      - add()      - Add a token to the end of the list
#              None         - addRef()   - Add a token to the end of the list
#              None         - reset()    - reset the index to -1
#              Boolean      - BOF()      - End of list?
#              Boolean      - EOF()      - Beginning of list?
#              Boolean      - moveNext() - Move the index along one
#              f_token/None - current()  - Return the current token
#              f_token/None - next()     - Return the next token (leave the index unchanged)
#              f_token/None - previous() - Return the previous token (leave the index unchanged)
#========================================================================
class f_tokens:
    def __init__(self):
        self.items = []
        self.index = -1
  
    def add(self, value, type, subtype=""):
        if (not subtype):
            subtype = ""
        token = f_token(value, type, subtype)
        self.addRef(token)
        return token
        
    def addRef(self, token):
        self.items.append(token)
        
    def reset(self):
        self.index = -1
 
    def BOF(self):
        return self.index <= 0

    def EOF(self):
        return self.index >= (len(self.items) - 1)

    def moveNext(self):
        if self.EOF():
            return False
        self.index += 1
        return True
    
    def current(self):
        if self.index == -1:
            return None
        return self.items[self.index]

    def next(self):
        if self.EOF():
            return None
        return self.items[self.index + 1]
    
    def previous(self):
        if self.index < 1:
            return None
        return self.items[self.index -1]

#========================================================================
#       Class: f_tokenStack 
#    Inherits: ExcelParserTokens - a list of token values
# Description: A LIFO stack of tokens
#
#  Attributes:        items - Ordered list 
#
#     Methods: f_tokenStack - __init__()
#              None         - push(token) - Push a token onto the stack
#              f_token/None - pop()       - Pop a token off the stack
#              f_token/None - token()     - Non-destructively return the top item on the stack
#              String       - type()      - Return the top token's type
#              String       - subtype()   - Return the top token's subtype
#              String       - value()     - Return the top token's value
#========================================================================
class f_tokenStack(ExcelParserTokens):
    def __init__(self):
        self.items = []
    
    def push(self, token):
        self.items.append(token)
    
    def pop(self):
        token = self.items.pop()
        return f_token("", token.ttype, self.TOK_SUBTYPE_STOP)
        
    def token(self):
        # Note: this uses Pythons and/or "hack" to emulate C's ternary operator (i.e. cond ? exp1 : exp2)
        return ((len(self.items) > 0) and [self.items[len(self.items) - 1]] or [None])[0]
    
    def value(self):
        return ((self.token()) and [(self.token()).tvalue] or [""])[0]    

    def type(self):
        t = self.token()
        return ((self.token()) and [(self.token()).ttype] or [""])[0]
    
    def subtype(self):
        return ((self.token()) and [(self.token()).tsubtype] or [""])[0]

#========================================================================
#       Class: ExcelParser
# Description: Parse an Excel formula into a stream of tokens

#  Attributes:
#
#     Methods: f_tokens - getTokens(formula) - return a token stream (list)
#========================================================================
class ExcelParser(ExcelParserTokens):
    def getTokens(self, formula):
    
        def currentChar():
            return formula[offset]
    
        def doubleChar():
            return formula[offset:offset+2]
        
        def nextChar():
            # JavaScript returns an empty string if the index is out of bounds,
            # Python throws an IndexError.  We mimic this behaviour here.
            try:
                formula[offset+1]
            except IndexError:
                return ""
            else:            
                return formula[offset+1]
        
        def EOF():
            return offset >= len(formula)
    
        tokens     = f_tokens()
        tokenStack = f_tokenStack()
        offset     = 0
        token      = ""
        inString   = False
        inPath     = False
        inRange    = False
        inError    = False
    
        while (len(formula) > 0):
            if (formula[0] == " "):
                formula = formula[1:]
            else:
                if (formula[0] == "="):
                    formula = formula[1:]
                break;    
    
        # state-dependent character evaluation (order is important)
        while not EOF():
               
            # double-quoted strings
            # embeds are doubled
            # end marks token
            if inString:
                if currentChar() == "\"":
                    if nextChar() == "\"":
                        token += "\""
                        offset += 1
                    else:
                        inString = False
                        tokens.add(token, self.TOK_TYPE_OPERAND, self.TOK_SUBTYPE_TEXT)
                        token = ""
                else:
                    token += currentChar()
                offset += 1
                continue
    
            # single-quoted strings (links)
            # embeds are double
            # end does not mark a token
            if inPath:
                if currentChar() == "'":
                    if nextChar() == "'":
                        token += "'"
                        offset += 1
                    else:
                        inPath = False
                else:
                    token += currentChar()
                offset += 1;
                continue;    
    
            # bracketed strings (range offset or linked workbook name)
            # no embeds (changed to "()" by Excel)
            # end does not mark a token
            if inRange:
                if currentChar() == "]":
                    inRange = False
                token += currentChar()
                offset += 1
                continue
    
            # error values
            # end marks a token, determined from absolute list of values
            if inError:
                token += currentChar()
                offset += 1
                if ",#NULL!,#DIV/0!,#VALUE!,#REF!,#NAME?,#NUM!,#N/A,".find("," + token + ",") != -1:
                    inError = False
                    tokens.add(token, self.TOK_TYPE_OPERAND, self.TOK_SUBTYPE_ERROR)
                    token = ""
                continue;
    
            # scientific notation check
            regexSN = '^[1-9]{1}(\.[0-9]+)?[eE]{1}$';
            if (("+-").find(currentChar()) != -1):
                if len(token) > 1:
                    if re.match(regexSN,token):
                        token += currentChar();
                        offset += 1;
                        continue;
              
            # independent character evaulation (order not important)
            #
            # establish state-dependent character evaluations
            if currentChar() == "\"":
                if len(token) > 0:
                    # not expected
                    tokens.add(token, self.TOK_TYPE_UNKNOWN)
                    token = ""
                inString = True
                offset += 1
                continue
    
            if currentChar() == "'":
                if len(token) > 0:
                    # not expected
                    tokens.add(token, self.TOK_TYPE_UNKNOWN)
                    token = ""
                inPath = True
                offset += 1
                continue
    
            if (currentChar() == "["):
                inRange = True
                token += currentChar()
                offset += 1
                continue
    
            if (currentChar() == "#"):
                if (len(token) > 0):
                    # not expected
                    tokens.add(token, self.TOK_TYPE_UNKNOWN)
                    token = ""
                inError = True
                token += currentChar()
                offset += 1
                continue
    
            # mark start and end of arrays and array rows
            if (currentChar() == "{"):
                if (len(token) > 0):
                    # not expected
                    tokens.add(token, self.TOK_TYPE_UNKNOWN)
                    token = ""
                tokenStack.push(tokens.add("ARRAY", self.TOK_TYPE_FUNCTION, self.TOK_SUBTYPE_START))
                tokenStack.push(tokens.add("ARRAYROW", self.TOK_TYPE_FUNCTION, self.TOK_SUBTYPE_START))
                offset += 1
                continue
    
            if (currentChar() == ";"):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.addRef(tokenStack.pop())
                tokens.add(",", self.TOK_TYPE_ARGUMENT)
                tokenStack.push(tokens.add("ARRAYROW", self.TOK_TYPE_FUNCTION, self.TOK_SUBTYPE_START))
                offset += 1
                continue
    
            if (currentChar() == "}"):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.addRef(tokenStack.pop())
                tokens.addRef(tokenStack.pop())
                offset += 1
                continue
    
            # trim white-space
            if (currentChar() == " "):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.add("", self.TOK_TYPE_WSPACE)
                offset += 1
                while ((currentChar() == " ") and (not EOF())):
                    offset += 1
                continue
    
            # multi-character comparators
            if (",>=,<=,<>,".find("," + doubleChar() + ",") != -1):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.add(doubleChar(), self.TOK_TYPE_OP_IN, self.TOK_SUBTYPE_LOGICAL)
                offset += 2
                continue
    
            # standard infix operators
            if ("+-*/^&=><".find(currentChar()) != -1):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.add(currentChar(), self.TOK_TYPE_OP_IN)
                offset += 1
                continue
    
            # standard postfix operators
            if ("%".find(currentChar()) != -1):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.add(currentChar(), self.TOK_TYPE_OP_POST)
                offset += 1
                continue
    
            # start subexpression or function
            if (currentChar() == "("):
                if (len(token) > 0):
                    tokenStack.push(tokens.add(token, self.TOK_TYPE_FUNCTION, self.TOK_SUBTYPE_START))
                    token = ""
                else:
                    tokenStack.push(tokens.add("", self.TOK_TYPE_SUBEXPR, self.TOK_SUBTYPE_START))
                offset += 1
                continue
    
            # function, subexpression, array parameters
            if (currentChar() == ","):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                if (not (tokenStack.type() == self.TOK_TYPE_FUNCTION)):
                    tokens.add(currentChar(), self.TOK_TYPE_OP_IN, self.TOK_SUBTYPE_UNION)
                else:
                    tokens.add(currentChar(), self.TOK_TYPE_ARGUMENT)
                offset += 1
                continue
    
            # stop subexpression
            if (currentChar() == ")"):
                if (len(token) > 0):
                    tokens.add(token, self.TOK_TYPE_OPERAND)
                    token = ""
                tokens.addRef(tokenStack.pop())
                offset += 1
                continue
    
            # token accumulation
            token += currentChar()
            offset += 1
    
        # dump remaining accumulation
        if (len(token) > 0): 
            tokens.add(token, self.TOK_TYPE_OPERAND)
    
        # move all tokens to a new collection, excluding all unnecessary white-space tokens
        tokens2 = f_tokens()
    
        while (tokens.moveNext()):
            token = tokens.current();
    
            if (token.ttype == self.TOK_TYPE_WSPACE):
                if ((tokens.BOF()) or (tokens.EOF())):
                    pass
                elif (not(
                     ((tokens.previous().ttype == self.TOK_TYPE_FUNCTION) and (tokens.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or 
                     ((tokens.previous().ttype == self.TOK_TYPE_SUBEXPR) and (tokens.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or 
                     (tokens.previous().ttype == self.TOK_TYPE_OPERAND)
                    )
                  ):
                    pass
                elif (not(
                     ((tokens.next().ttype == self.TOK_TYPE_FUNCTION) and (tokens.next().tsubtype == self.TOK_SUBTYPE_START)) or
                     ((tokens.next().ttype == self.TOK_TYPE_SUBEXPR) and (tokens.next().tsubtype == self.TOK_SUBTYPE_START)) or
                     (tokens.next().ttype == self.TOK_TYPE_OPERAND)
                     )
                   ):
                    pass
                else:
                    tokens2.add(token.tvalue, self.TOK_TYPE_OP_IN, self.TOK_SUBTYPE_INTERSECT)
                continue
    
            tokens2.addRef(token);
    
        # switch infix "-" operator to prefix when appropriate, switch infix "+" operator to noop when appropriate, identify operand 
        # and infix-operator subtypes, pull "@" from in front of function names
        while (tokens2.moveNext()):
            token = tokens2.current()
            if ((token.ttype == self.TOK_TYPE_OP_IN) and (token.tvalue == "-")):
                if (tokens2.BOF()):
                    token.ttype = self.TOK_TYPE_OP_PRE
                elif (
                   ((tokens2.previous().ttype == self.TOK_TYPE_FUNCTION) and (tokens2.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or
                   ((tokens2.previous().ttype == self.TOK_TYPE_SUBEXPR) and (tokens2.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or
                   (tokens2.previous().ttype == self.TOK_TYPE_OP_POST) or 
                   (tokens2.previous().ttype == self.TOK_TYPE_OPERAND)
                  ):
                    token.tsubtype = self.TOK_SUBTYPE_MATH;
                else:
                    token.ttype = self.TOK_TYPE_OP_PRE
                continue
    
            if ((token.ttype == self.TOK_TYPE_OP_IN) and (token.tvalue == "+")):
                if (tokens2.BOF()):
                    token.ttype = self.TOK_TYPE_NOOP
                elif (
                   ((tokens2.previous().ttype == self.TOK_TYPE_FUNCTION) and (tokens2.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or 
                   ((tokens2.previous().ttype == self.TOK_TYPE_SUBEXPR) and (tokens2.previous().tsubtype == self.TOK_SUBTYPE_STOP)) or 
                   (tokens2.previous().ttype == self.TOK_TYPE_OP_POST) or 
                   (tokens2.previous().ttype == self.TOK_TYPE_OPERAND)
                  ):
                    token.tsubtype = self.TOK_SUBTYPE_MATH
                else:
                    token.ttype = self.TOK_TYPE_NOOP
                continue
    
            if ((token.ttype == self.TOK_TYPE_OP_IN) and (len(token.tsubtype) == 0)):
                if (("<>=").find(token.tvalue[0:1]) != -1):
                    token.tsubtype = self.TOK_SUBTYPE_LOGICAL
                elif (token.tvalue == "&"):
                    token.tsubtype = self.TOK_SUBTYPE_CONCAT
                else:
                    token.tsubtype = self.TOK_SUBTYPE_MATH
                continue
        
            if ((token.ttype == self.TOK_TYPE_OPERAND) and (len(token.tsubtype) == 0)):
                try:
                    float(token.tvalue)
                except ValueError, e:
                    if ((token.tvalue == 'TRUE') or (token.tvalue == 'FALSE')):
                        token.tsubtype = self.TOK_SUBTYPE_LOGICAL
                    else:
                        token.tsubtype = self.TOK_SUBTYPE_RANGE
                else:
                    token.tsubtype = self.TOK_SUBTYPE_NUMBER
                continue
    
            if (token.ttype == self.TOK_TYPE_FUNCTION):
                if (token.tvalue[0:1] == "@"):
                    token.tvalue = token.tvalue[1:]
                continue
    
        tokens2.reset();
    
        # move all tokens to a new collection, excluding all noops
        tokens = f_tokens()
        while (tokens2.moveNext()):
            if (tokens2.current().ttype != self.TOK_TYPE_NOOP):
                tokens.addRef(tokens2.current())
    
        tokens.reset()
        return tokens    

    def parse(self, formula):
        self.tokens = self.getTokens(formula)
        
    def render(self):
        output = ""
        if self.tokens:
            for t in self.tokens.items:
                if   t.ttype == self.TOK_TYPE_FUNCTION and t.tsubtype == self.TOK_SUBTYPE_START:     output += t.tvalue + "("
                elif t.ttype == self.TOK_TYPE_FUNCTION and t.tsubtype == self.TOK_SUBTYPE_STOP:      output += ")"
                elif t.ttype == self.TOK_TYPE_SUBEXPR  and t.tsubtype == self.TOK_SUBTYPE_START:     output += "("
                elif t.ttype == self.TOK_TYPE_SUBEXPR  and t.tsubtype == self.TOK_SUBTYPE_STOP:      output += ")"
                # TODO: add in RE substitution of " with "" for strings
                elif t.ttype == self.TOK_TYPE_OPERAND  and t.tsubtype == self.TOK_SUBTYPE_TEXT:      output += "\"" + t.tvalue + "\""
                elif t.ttype == self.TOK_TYPE_OP_IN    and t.tsubtype == self.TOK_SUBTYPE_INTERSECT: output += " "                    

                else: output += t.tvalue
        return output
    
    def prettyprint(self):
        indent = 0
        output = ""
        if self.tokens:
            for t in self.tokens.items:
                #print "'",t.ttype,t.tsubtype,t.tvalue,"'"
                if (t.tsubtype == self.TOK_SUBTYPE_STOP):
                    indent -= 1
    
                output += "    "*indent + t.tvalue + " <" + t.ttype +"> <" + t.tsubtype + ">" + "\n"
                
                if (t.tsubtype == self.TOK_SUBTYPE_START):
                    indent += 1;
        return output

class Operator:
    def __init__(self,value,precedence,associativity):
        self.value = value
        self.precedence = precedence
        self.associativity = associativity

class ASTNode(object):
    def __init__(self,token):
        super(ASTNode,self).__init__()
        self.token = token
    def emit(self):
        self.token.tvalue
    def __str__(self):
        return self.token.tvalue
    
class OperatorNode(ASTNode):
    def __init__(self,*args):
        super(OperatorNode,self).__init__(*args)
    def emit(self):
        pass

class RangeNode(ASTNode):
    def __init__(self,*args):
        super(RangeNode,self).__init__(*args)
    def emit(self):
        pass
    
class FunctionNode(ASTNode):
    def __init__(self,*args):
        super(FunctionNode,self).__init__(*args)
        self.numargs = 0
        
    def emit(self):
        pass

def create_node(t):
    if t.ttype == "operand" and t.tsubtype == "range":
        return RangeNode(t)
    elif t.ttype == "function":
        return FunctionNode(t)
    elif t.ttype == "operator":
        return OperatorNode(t)
    else:
        return ASTNode(t)

def shunting_yard(expression):
    
    #remove leading =
    if expression.startswith('='):
        expression = expression[1:]
        
    p = ExcelParser();
    p.parse(expression)

    # insert tokens for '(' and ')', to make things cleaner below
    tokens = []
    for t in p.tokens.items:
        if t.ttype == "function" and t.tsubtype == "start":
            t.tsubtype = ""
            tokens.append(t)
            tokens.append(f_token('(','arglist','start'))
        elif t.ttype == "function" and t.tsubtype == "stop":
            #t.tsubtype = ""
            #tokens.append(t)
            tokens.append(f_token(')','arglist','stop'))
        elif t.ttype == "subexpression" and t.tsubtype == "start":
            t.tvalue = '('
            tokens.append(t)
        elif t.ttype == "subexpression" and t.tsubtype == "stop":
            t.tvalue = ')'
            tokens.append(t)
        else:
            tokens.append(t)

    print "tokens: ", "|".join([x.tvalue for x in tokens])

    #http://office.microsoft.com/en-us/excel-help/calculation-operators-and-precedence-HP010078886.aspx
    operators = {}
    operators[':'] = Operator(':',8,'left')
    operators[''] = Operator(' ',8,'left')
    operators[','] = Operator(',',8,'left')
    operators['u-'] = Operator('u-',7,'left') #unary negation
    operators['%'] = Operator('%',6,'left')
    operators['^'] = Operator('^',5,'left')
    operators['*'] = Operator('*',4,'left')
    operators['/'] = Operator('/',4,'left')
    operators['+'] = Operator('+',3,'left')
    operators['-'] = Operator('-',3,'left')
    operators['&'] = Operator('&',2,'left')
    operators['='] = Operator('=',1,'left')
    operators['<'] = Operator('<',1,'left')
    operators['>'] = Operator('>',1,'left')
    operators['<='] = Operator('<=',1,'left')
    operators['>='] = Operator('>=',1,'left')
    operators['<>'] = Operator('<>',1,'left')
            
    output = collections.deque()
    stack = []
    were_values = []
    arg_count = []
    
    def po():
        print "output: ", "|".join([x.tvalue for x in output])
    def so():
        print "stack:", "|".join([x.tvalue for x in stack])
    
    for t in tokens:
        if t.ttype == "operand":
            
            output.append(create_node(t))

            if were_values:
                were_values.pop()
                were_values.append(True)
                
        elif t.ttype == "function":
            stack.append(t)
            arg_count.append(0)
            if were_values:
                were_values.pop()
                were_values.append(True)
            were_values.append(False)
            
        elif t.ttype == "argument":
            
            while stack and (stack[-1].tsubtype != "start"):
                output.append(create_node(stack.pop()))   
            
            if were_values.pop(): arg_count[-1] += 1
            were_values.append(False)
            
            if not len(stack):
                raise Exception("Mismatched or misplaced parentheses")
        
        elif t.ttype.startswith('operator'):
            if t.ttype.endswith('-prefix') and t.tvalue =="-":
                o1 = operators['u-']
            else:
                o1 = operators[t.tvalue]

                
            while stack and stack[-1].ttype.startswith('operator'):
                
                if stack[-1].ttype.endswith('-prefix') and stack[-1].tvalue =="-":
                    o2 = operators['u-']
                else:
                    o2 = operators[stack[-1].tvalue]
                
                if ( (o1.associativity == "left" and o1.precedence <= o2.precedence)
                        or
                      (o1.associativity == "right" and o1.precedence < o2.precedence) ):
                    
                    output.append(create_node(stack.pop()))
                else:
                    break
                
            stack.append(t)
        
        elif t.tsubtype == "start":
            stack.append(t)
            
        elif t.tsubtype == "stop":
            
            while stack and stack[-1].tsubtype != "start":
                output.append(create_node(stack.pop()))
            
            if not stack:
                raise Exception("Mismatched or misplaced parentheses")
            
            stack.pop()

            if stack and stack[-1].ttype == "function":
                f = create_node(stack.pop())
                a = arg_count.pop()
                w = were_values.pop()
                if w: a += 1
                f.num_args = a
                print f, "has ",a," args"
                output.append(f)

    while stack:
        if stack[-1].tsubtype == "start" or stack[-1].tsubtype == "stop":
            raise Exception("Mismatched or misplaced parentheses")
        
        output.append(create_node(stack.pop()))

    #print "Stack is: ", "|".join(stack)
    #print "Ouput is: ", "|".join([x.tvalue for x in output])
    return output

if __name__ == "__main__":
    
    
    # Test inputs
    inputs = [
              # Simple test formulae
              '=3 + 4 * 2 / ( 1 - 5 ) ^ 2 ^ 3',
              '=1+3+5',
              '=3 * 4 + 5',
              '=50',
              '=1+1',
              '=5*log(sin()+2)',
              '=5*log(sin(3,7,9)+2)',
              '=$A1',
              '=$B$2',
              '=SUM(B5:B15)',
              '=SUM(B5:B15,D5:D15)',
              '=SUM(B5:B15 A7:D7)',
              '=SUM(sheet1!$A$1:$B$2)',
              '=[data.xls]sheet1!$A$1',
              '=SUM((A:A 1:1))',
              '=SUM((A:A,1:1))',
              '=SUM((A:A A1:B1))',
              '=SUM(D9:D11,E9:E11,F9:F11)',
              '=SUM((D9:D11,(E9:E11,F9:F11)))',
              '=IF(P5=1.0,"NA",IF(P5=2.0,"A",IF(P5=3.0,"B",IF(P5=4.0,"C",IF(P5=5.0,"D",IF(P5=6.0,"E",IF(P5=7.0,"F",IF(P5=8.0,"G"))))))))',
              '={SUM(B2:D2*B3:D3)}',
              '=SUM(123 + SUM(456) + (45<6))+456+789',
              '=AVG(((((123 + 4 + AVG(A1:A2))))))',
              
              # E. W. Bachtal's test formulae
              '=+ AName- (-+-+-2^6) = {"A","B"} + @SUM(R1C1) + (@ERROR.TYPE(#VALUE!) = 2)',
              '=IF(R13C3>DATE(2002,1,6),0,IF(ISERROR(R[41]C[2]),0,IF(R13C3>=R[41]C[2],0, IF(AND(R[23]C[11]>=55,R[24]C[11]>=20),R53C3,0))))',
              '=IF(R[39]C[11]>65,R[25]C[42],ROUND((R[11]C[11]*IF(OR(AND(R[39]C[11]>=55, ' + 
                  'R[40]C[11]>=20),AND(R[40]C[11]>=20,R11C3="YES")),R[44]C[11],R[43]C[11]))+(R[14]C[11] ' +
                  '*IF(OR(AND(R[39]C[11]>=55,R[40]C[11]>=20),AND(R[40]C[11]>=20,R11C3="YES")), ' +
                  'R[45]C[11],R[43]C[11])),0))',
              '=(propellor_charts!B22*(propellor_charts!E21+propellor_charts!D21*(engine_data!O16*D70+engine_data!P16)+propellor_charts!C21*(engine_data!O16*D70+engine_data!P16)^2+propellor_charts!B21*(engine_data!O16*D70+engine_data!P16)^3)^2)^(1/3)*(1*D70/5.33E-18)^(2/3)*0.0000000001*28.3495231*9.81/1000',
              '=(3600/1000)*E40*(E8/E39)*(E15/E19)*LN(E54/(E54-E48))',
              '=IF(P5=1.0,"NA",IF(P5=2.0,"A",IF(P5=3.0,"B",IF(P5=4.0,"C",IF(P5=5.0,"D",IF(P5=6.0,"E",IF(P5=7.0,"F",IF(P5=8.0,"G"))))))))',
              '=LINEST(X5:X32,W5:W32^{1,2,3})',
              '=IF(configurations!$G$22=3,sizing!$C$303,M14)',
              '=0.000001042*E226^3-0.00004777*E226^2+0.0007646*E226-0.00075',
              '=LINEST(G2:G17,E2:E17,FALSE)',
              '=IF(AI119="","",E119)'
              '=LINEST(B32:(INDEX(B32:B119,MATCH(0,B32:B119,-1),1)),(F32:(INDEX(B32:F119,MATCH(0,B32:B119,-1),5)))^{1,2,3,4})',
              '=IF(H61<$E$8,3600*1000*1000/9.81*U61/F61*($E$2*9.81/Q61)*LN($E$2/ABS($E$2-$E$5))/1000,"")'
              '=LINEST(X5:X32,W5:W32^{1,2,3})',
              '=IF("a"={"a","b";"c",#N/A;-1,TRUE}, "yes", "no") &   "  more ""test"" text"',
              
              ]

    p = ExcelParser()

    for i in inputs:
        print "========================================"
        print "Formula:     " + i
        print "RPN:     " + "|".join([x.token.tvalue for x in shunting_yard(i)])
        p.parse(i)
        print "Pretty printed:\n", p.prettyprint()

########NEW FILE########
