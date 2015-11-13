__FILENAME__ = avro_backend

"""
TO NOTE:
1) args must be entered into original python call in the same order they are used in the mainfunc
    given
2) must have matching number of args in args.avro as are required to call mainfunc, in proper order
3) mainfunc name needs to be the same as the name for the function added to the scala module
"""

import py_avro_inter as py_avro

def generate_scala_object(mainfunc, filename=None, rendered=None):   
    
    class_name = mainfunc + "_outer"
    if not rendered and filename:
        f = open(filename)
        rendered = f.read()
        f.close()
    
    output = """
import javro.JAvroInter
import org.apache.avro.Schema
import javro.scala_arr

class %s{
    %s
}
    """ %(class_name + "_data", rendered)
    
    output+= """

object %s{ 
    """%(class_name)
    output += generate_scala_main(rendered, mainfunc)    
    output += """
}
"""
    #print 'output is ', output
    return output


#multiple outputs????
def generate_scala_main(rendered, mainfunc):
    
    main = """
    def main(args: Array[String]){  
        var s = new JAvroInter("results.avro", "args.avro") 
        var results = new Array[Object](1)
        %s
        s.writeAvroFile(results)   
                
    }
    """ %(generate_func_call(rendered,mainfunc))
    return main

def generate_func_call(rendered, mainfunc):
    size = get_arg_amount(rendered, mainfunc)
    arg_types = get_arg_type(rendered, mainfunc)
    call = ""
    args = ""
    for i in range(size):
        call += """var arg%s = s.returnStored[%s](%s)
        """ %(i, arg_types[i], i) 
        args += "arg%s" %i
        if not i== (size-1):
            args+=', '    
    call += "results(0) = %s(%s).asInstanceOf[Object]" %('(new ' +mainfunc +'_outer_data()).' + mainfunc, args)
    return call

def get_arg_type(rendered, mainfunc):
    size = get_arg_amount(rendered, mainfunc)
    start_index = rendered.find(mainfunc)
    args_found = 0
    colon_indices=[]
    while (args_found < size):
        if colon_indices:
            colon_indices.append(rendered.index(':', colon_indices[-1]+1))
        else:
            colon_indices.append(rendered.index(':', start_index))
        args_found += 1
    types = parse_func(rendered, colon_indices, mainfunc)  
    return types  
    #return "Int"


def parse_func(rendered, colon_indices, mainfunc):
    comma_indices = []
    count = 0
    while len(comma_indices) < (len(colon_indices) -1):
        comma_indices.append(rendered.index(',', colon_indices[count]))
        count += 1 
    types = []
    count = 0
    while (len(types) < len(colon_indices)):
        if (len(types)==(len(colon_indices)-1)):
            types.append(rendered[colon_indices[count]+1:closing_paren_loc(rendered, rendered.find(mainfunc))])
        else:
            types.append(rendered[colon_indices[count]+1 : comma_indices[count]])
        count += 1
    #arg types are now between : and ,'s
    return types

#calculates arg amount in function simply by counting the commas...could be more rigorous, but
#can't think of a situation in which it won't work
def get_arg_amount(rendered, mainfunc):
    start = opening_paren_loc(rendered,rendered.find(mainfunc))
    end = closing_paren_loc(rendered,rendered.find(mainfunc))    
    index = start
    comma_count = 0
    while index < end:
        char = rendered[index]
        if char == ',':
            comma_count +=1
        index+=1
    return comma_count+1

def opening_paren_loc(str, start_index):
    index = start_index
    while index < len(str):
        char = str[index]
        if char == '(':
            return index
        else: index +=1
    return index

#returns the index of the closin paren
#first_paren is the index ideally of the opening paren, but still works if index is 
# before the first paren (of course assuming there aren't other parens in between

def closing_paren_loc(str, first_paren):
    paren_count = -1
    index = first_paren   
    while index < len(str):
        char = str[index]
        if char == ')' and paren_count == 0:
            return index      
        elif char == '(':
            paren_count+=1        
        elif char == ')':
            paren_count -= 1
        index+=1
    raise "No closing paren found"

if __name__ == '__main__':
    print "beginning"
    print(generate_scala_object('double', 'func1.scala'))
    print"DONE"
    

########NEW FILE########
__FILENAME__ = py_avro_inter
import sys
from avro import schema, datafile, io
from cStringIO import StringIO


"""
Module to read from and write to .avro files

TO NOTE:
1) lists can only be of one type
2) tuples are converted to lists
"""

stored = []

def getAvroType(pyObject):
    t = type(pyObject)
    if t == dict:
        return '"record"'
    elif t == list or t == tuple:
        if pyObject:
            listType = getAvroType(pyObject[0])
        else:
            #list is empty...
            listType = '"int"'
        entry = """{    "type":"array", "items": %s    }"""%(listType)
        return entry
    elif t == str:
        return '"string"'
    elif t == int:
        return '"int"'
    elif t == long:
        return '"long"'
    elif t == float:
        return '"double"'
    elif t == bool:
        return '"boolean"'
    elif t == type(None):
        return '"null"'
    else:
        raise Exception("Unrecognized type")
    return entry
        

def makeSchema(args):
    schema = """{
    "type": "record",
    "name": "args",
    "namespace": "SCALAMODULE",
    "fields": ["""
    count = 1
    size = """
        { "name": "size"    , "type": "int"    }"""
    if args:
        size += ","            
    schema = schema +size
    for arg in args:
        t = getAvroType(arg)
        entry = """
        {    "name": "arg%s"    , "type": %s    }"""%(count,t)
        if count != len(args):
            entry+= ','
        schema = schema + entry
        count+=1
    close = """
    ]
}"""
    schema = schema + close
    return schema

    
def write_avro_file(args, outsource='args.avro'):
    SCHEMA = schema.parse(makeSchema(args))
    rec_writer = io.DatumWriter(SCHEMA)   
        
    if outsource == sys.stdout:
        df_writer = datafile.DataFileWriter(sys.stdout, rec_writer, 
                                        writers_schema = SCHEMA, codec = 'deflate')
    
    else:
        df_writer = datafile.DataFileWriter(open(outsource,'wb'), rec_writer, 
                                        writers_schema = SCHEMA, codec = 'deflate')
    data = {}
    count = 1
    data['size'] = len(args)
    for arg in args:
        if type(arg) == tuple:
            arg = tupleToList(arg)
        data["arg%s"%(count)] = arg
        count +=1
    df_writer.append(data)
    df_writer.close()

#this function reads the specified avro file and stores the data in the global list stored
def read_avro_file(insource='results.avro'):
    rec_reader = io.DatumReader()
    if insource == sys.stdin:          
        input = sys.stdin.read()
        temp_file = StringIO(input)

        df_reader = datafile.DataFileReader(temp_file, rec_reader)
    else:
        df_reader = datafile.DataFileReader(open(insource), rec_reader)
    del stored[:]
    """
    for record in df_reader:
        size = record['size']
        for i in range(size):
            i = i+1
            arg = record["arg%s"%(i)]
            #print arg
            stored.append(arg)
    """
    return df_reader

def return_stored(index):
    if stored:
        return stored[index]
    else:
        read_avro_file()
        return stored[index]
    
def return_stored():
    if stored:
        return stored
    else:
        read_avro_file()
        return stored
        
def tupleToList(input):
    output = list(input)
    for i in range(len(output)):
        if type(output[i]) == tuple:
            output[i] = list(output[i])
    return output
        

if __name__ == '__main__': 
    args = sys.argv   
    #inputs = [[1.0*i for i in xrange(10000000)]]
    inputs = [1,2,[3,34]]
    import time
    print "about to write"
    start = time.time()
    write_avro_file(inputs)
    end = time.time()
    print "done writing"
    res = read_avro_file('args.avro')
    print 'FROM FILE:' + str(res)
    

########NEW FILE########
__FILENAME__ = ast_explorer
#!/usr/bin/env python

# Based on example basictreeview.py from:
# http://www.pygtk.org/pygtk2tutorial/examples/basictreeview.py

import pygtk
pygtk.require('2.0')
import gtk
import inspect
import re
from types import *

def debug_str(obj):
    if isinstance(obj, str):
        # TODO: needs escaping
        return "'" + obj + "'"
    elif isinstance(obj, list):
        return '[' + ', '.join([debug_str(x) for x in obj]) + ']'
    else:
        result = str(obj)
        result = re.sub(r'<_ast\.(.*) object at 0x[0-9a-f]+>', r'\1', result)
        return result

def generator_index(gen, index):
    import itertools
    return next(itertools.islice(gen, index, index+1))

class ASTExplorer:

    def button_release_event(self, treeview, event):
        if event.button == 3: # right click
            result = treeview.get_path_at_pos(int(event.x), int(event.y))
            if result != None:
                self.path_right_clicked = result[0]
                self.context_menu.popup(None, None, None, event.button, event.time, None)
                self.context_menu.show_all()

    def copy_expression(self, menuitem, event):
        if event.button == 1: # left click
            path = 'ast' + self.get_path(self.tree, self.path_right_clicked[1:])
            self.clipboard.set_text(path)
            self.path_right_clicked = None

    def reduced_pairs(self, obj):
        # Exclude lineno, col_offset (from Python AST), _fields
        # (from CodePy C++ AST) to simplify tree
        dict = obj.__dict__
        dict.pop('lineno', None)
        dict.pop('col_offset', None)
        dict.pop('_fields', None)
        return [(key, dict[key]) for key in sorted(dict.iterkeys())]

    def get_path(self, tree, path):
        if len(path) == 0:
            return ''
        key, value = generator_index(self.reduced_pairs(tree), path[0])
        result = '.' + key
        path = path[1:]
        if len(path) == 0:
            return result
        if isinstance(value, list):
            result += '[' + str(path[0]) + ']'
            value = value[path[0]]
            path = path[1:]
        return result + self.get_path(value, path)

    def add_tree(self, tree, parent):
        if isinstance(tree, (int, str, NoneType)):
            return
        for key, value in self.reduced_pairs(tree):
            attriter = self.treestore.append(parent, [key + ': ' + debug_str(value)])
            if isinstance(value, list):
                for i in range(0, len(value)):
                    elemiter = self.treestore.append(attriter, ['[' + str(i) + '] ' + debug_str(value[i])])
                    self.add_tree(value[i], elemiter)
            else:
                self.add_tree(value, attriter)

    # close the window and quit
    def delete_event(self, widget, event, data=None):
        gtk.main_quit()
        return False

    def __init__(self, tree):
        self.tree = tree

        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("AST Explorer")
        self.window.set_size_request(400, 500)
        self.window.connect("delete_event", self.delete_event)

        self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)

        # Create right-click context menu
        self.context_menu = gtk.Menu()
        menuitem_copyexpr = gtk.MenuItem("Copy expression")
        menuitem_copyexpr.connect('button-release-event' , self.copy_expression)
        self.context_menu.append(menuitem_copyexpr)

        # create a TreeStore with one string column to use as the
        # model and fill with data
        self.treestore = gtk.TreeStore(str)
        rootiter = self.treestore.append(None, [debug_str(self.tree)])
        self.add_tree(self.tree, rootiter)

        # create the TreeView using treestore and hook up button event
        self.treeview = gtk.TreeView(self.treestore)
        self.treeview.connect('button-release-event' , self.button_release_event)
        self.path_right_clicked = None

        # create the TreeViewColumn to display the data
        self.tvcolumn = gtk.TreeViewColumn()

        # add tvcolumn to treeview
        self.treeview.append_column(self.tvcolumn)

        # create a CellRendererText to render the data
        self.cell = gtk.CellRendererText()

        # add the cell to the tvcolumn and allow it to expand
        self.tvcolumn.pack_start(self.cell, True)

        # set the cell "text" attribute to column 0 - retrieve text
        # from that column in treestore
        self.tvcolumn.add_attribute(self.cell, 'text', 0)

        # make it searchable
        self.treeview.set_search_column(0)

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.add(self.treeview)
        self.window.add(self.scrolled_window)
        self.window.show_all()

        gtk.main()

class TestObject:
    def operation(self, x):
        return 2*x+5

if __name__ == "__main__":
    import ast_tools
    ast = ast_tools.parse_method(TestObject.operation)
    ASTExplorer(ast)

########NEW FILE########
__FILENAME__ = ast_tools
import cpp_ast as cpp
import python_ast as ast
import scala_ast as scala 
import inspect

try:
    from asp.util import *
except Exception,e:
    pass    

def is_python_node(x):
    return isinstance(x, ast.AST)    

def is_cpp_node(x):
    return isinstance(x, cpp.Generable)    

def is_scala_node(x):
    return isinstance(x, scala.Generable)

def parse_method(method):
    src = inspect.getsource(method)
    return ast.parse(src.lstrip())

class NodeVisitorCustomNodes(ast.NodeVisitor):
    # Based on NodeTransformer.generic_visit(), but visits all sub-nodes
    # matching is_node(), not just those derived from ast.AST. By default
    # behaves just like ast.NodeTransformer, but is_node() can be overridden.
    def generic_visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if self.is_node(item):
                        self.visit(item)
            elif self.is_node(value):
                self.visit(value)

    def is_node(self, x):
        return isinstance(x, ast.AST)

class NodeVisitor(NodeVisitorCustomNodes):
    def is_node(self, x):
        return isinstance(x, ast.AST) or is_cpp_node(x) or is_scala_node(x)

class NodeTransformerCustomNodes(ast.NodeTransformer):
    # Based on NodeTransformer.generic_visit(), but visits all sub-nodes
    # matching is_node(), not just those derived from ast.AST. By default
    # behaves just like ast.NodeTransformer, but is_node() can be overridden.
    def generic_visit(self, node):
        for field in node._fields:
            old_value = getattr(node, field, None)
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if self.is_node(value):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not self.is_node(value):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif self.is_node(old_value):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node

    def is_node(self, x):
        return isinstance(x, ast.AST)

class NodeTransformerCustomNodesExtended(NodeTransformerCustomNodes):
    """Extended version of NodeTransformerCustomNodes that also tracks line numbers"""
    def visit(self, node):
        result = super(NodeTransformerCustomNodesExtended, self).visit(node)
        return self.transfer_lineno(node, result)

    def transfer_lineno(self, node_from, node_to):
        if hasattr(node_from, 'lineno') and hasattr(node_to, 'lineno'):
            node_to.lineno = node_from.lineno
        if hasattr(node_from, 'col_offset') and hasattr(node_to, 'col_offset'):
            node_to.col_offset = node_from.col_offset
        return node_to

class NodeTransformer(NodeTransformerCustomNodesExtended):
    """Unified class for *transforming* Python and C++ AST nodes"""
    def is_node(self, x):
        return isinstance(x, ast.AST) or is_cpp_node(x) or is_scala_node(x)

class ASTNodeReplacer(NodeTransformer):
    """Class to replace Python AST nodes."""
    def __init__(self, original, replacement):
        self.original = original
        self.replacement = replacement

    def visit(self, node):
        eql = False
        if node.__class__ == self.original.__class__:
            eql = True
            for (field, value) in ast.iter_fields(self.original):
                if field != 'ctx' and node.__getattribute__(field) != value:
                    debug_print( str(node.__getattribute__(field)) + " != " + str(value) )
                    eql = False
                    break

        if eql:
            import copy
            debug_print( "Found something to replace!!!!" )
            return copy.deepcopy(self.replacement)
        else:
            return self.generic_visit(node)

class ASTNodeReplacerCpp(ASTNodeReplacer):
    def is_node(self, x):
        return is_cpp_node(x)

class ConvertAST(ast.NodeTransformer):
    """Class to convert from Python AST to C++ AST"""
    def visit_Num(self, node):
        return cpp.CNumber(node.n)

    def visit_Str(self, node):
        return cpp.String(node.s)

    def visit_Name(self, node):
        return cpp.CName(node.id)

    def visit_BinOp(self, node):
        return cpp.BinOp(self.visit(node.left),
                         self.visit(node.op),
                         self.visit(node.right))

    def visit_Add(self, node):
        return "+"
    def visit_Sub(self, node):
        return "-"
    def visit_Mult(self, node):
        return "*"
    def visit_Div(self, node):
        return "/"
    def visit_Mod(self, node):
        return "%"

    def visit_UnaryOp(self, node):
        return cpp.UnaryOp(self.visit(node.op),
                           self.visit(node.operand))

    def visit_Invert(self, node):
        return "-"
    def visit_USub(self, node):
        return "-"
    def visit_UAdd(self, node):
        return "+"
    def visit_Not(self, node):
        return "!"

    def visit_Subscript(self, node):
        return cpp.Subscript(self.visit(node.value),
                             self.visit(node.slice))

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Pass(self, _):
        return cpp.Expression()

    # by default, only do first statement in a module
    def visit_Module(self, node):
        return self.visit(node.body[0])

    def visit_Expr(self, node):
        return self.visit(node.value)

    # only single targets supported
    def visit_Assign(self, node):
        if is_python_node(node):
            return cpp.Assign(self.visit(node.targets[0]),
                              self.visit(node.value))
        elif is_cpp_node(node):
            return cpp.Assign(self.visit(node.lvalue),
                              self.visit(node.rvalue))
        else:
            raise Exception ("Unknown Assign node type")

    def visit_FunctionDef(self, node):
        debug_print("In FunctionDef:")
        debug_print(ast.dump(node))
        debug_print("----")
        return cpp.FunctionBody(cpp.FunctionDeclaration(cpp.Value("void",
                                                                  node.name),
                                                        self.visit(node.args)),
                                cpp.Block([self.visit(x) for x in node.body]))


    def visit_arguments(self, node):
        """Only return the basic case: everything is void*,  no named args, no default values"""
        return [cpp.Pointer(cpp.Value("void",self.visit(x))) for x in node.args]

    def visit_Call(self, node):
        """We only handle calls that are casts; everything else (eventually) will be
           translated into callbacks into Python."""
        if isinstance(node.func, ast.Name):
            if node.func.id == "int":
                return cpp.TypeCast(cpp.Value('int', ''), self.visit(node.args[0]))
            if node.func.id == "abs":
                return cpp.Call(cpp.CName("abs"), [self.visit(x) for x in node.args])

    def visit_Print(self, node):
        if len(node.values) > 0:
            text = '<< ' + str(self.visit(node.values[0]))
        else:
            text = ''
        for fragment in node.values[1:]:
            text += ' << \" \" << ' + str(self.visit(fragment))
        return cpp.Print(text, node.nl)

    def visit_Compare(self, node):
        # only handles 1 thing on right side for now (1st op and comparator)
        # also currently not handling: Is, IsNot, In, NotIn
        ops = {'Eq':'==','NotEq':'!=','Lt':'<','LtE':'<=','Gt':'>','GtE':'>='}
        op = ops[node.ops[0].__class__.__name__]
        return cpp.Compare(self.visit(node.left), op, self.visit(node.comparators[0]))

    def visit_If(self, node):
        test = self.visit(node.test)
        body = cpp.Block([self.visit(x) for x in node.body])
        if node.orelse == []:
            orelse = None
        else:
            orelse = cpp.Block([self.visit(x) for x in node.orelse])
        return cpp.IfConv(test, body, orelse)

    def visit_Return(self, node):
        return cpp.ReturnStatement(self.visit(node.value))
    
    
class ConvertPyAST_ScalaAST(ast.NodeTransformer):
    """Class to convert from Python AST to Scala AST"""    
    def visit_Num(self,node):
    	return scala.Number(node.n)
   
    def visit_Str(self,node):
	       return scala.String(node.s)

    def visit_Name(self,node):
	       return scala.Name(node.id)

    def visit_Add(self,node):
	       return "+"

    def visit_Sub(self,node):
	       return "-" 
    
    def visit_Mult(self,node):
	       return "*"

    def visit_Div(self,node):
	       return "/"

    def visit_Mod(self,node):
	       return "%"
    
    def visit_ClassDef(self,node):
        pass
    
    def visit_FunctionDef(self,node):
        return scala.Function(scala.FunctionDeclaration(node.name, self.visit(node.args)),
                            [self.visit(x) for x in node.body])
        
    def visit_Call(self,node):

        args = []
        for a in node.args:
            args.append(self.visit(a))
        return scala.Call(self.visit(node.func), args)
    
    def visit_arguments(self,node):  
        args = []
        for a in node.args:
            args.append(self.visit(a))
        return scala.Arguments(args)
        
    def visit_Return(self,node):
        return scala.ReturnStatement(self.visit(node.value))
        
    # only single targets supported
    def visit_Assign(self, node):
        if is_python_node(node):
            return scala.Assign(self.visit(node.targets[0]),
                          self.visit(node.value))
        #below happen ever?
        elif is_scala_node(node):
            return scala.Assign(self.visit(node.lvalue),
                          self.visit(node.rvalue))
        
    def visit_AugAssign(self,node):
        return scala.AugAssign(self.visit(node.target), self.visit(node.op), self.visit(node.value))
    
    def visit_Print(self,node):
        text = []
        if len(node.values) > 0:
            text.append(self.visit(node.values[0]))
        else:
            text = ''
        for fragment in node.values[1:]:
            text.append(self.visit(fragment))
        return scala.Print(text, node.nl, node.dest)
        
    def visit_If(self,node, inner_if = False):  
        test = self.visit(node.test)
        body = [self.visit(x) for x in node.body]
        
        if node.orelse == []:
            orelse = None
        else:
            if isinstance(node.orelse[0], ast.If):
                orelse = [self.visit_If(node.orelse[0], True)]
            else:
                orelse = [self.visit(x) for x in node.orelse]

        if inner_if:
            return scala.IfConv(test,body, orelse, True)
        else:
            return scala.IfConv(test, body, orelse)
    
    def visit_Subscript(self,node):
        context= ''
        if type(node.ctx) == ast.Store:
            context ='store'
        elif type(node.ctx) == ast.Load:
            context = 'load'
        else:
            raise Exception ("Unknown Subscript Context")
        return scala.Subscript(self.visit(node.value),self.visit(node.slice), context)
    
    def visit_List(self,node):
        elements = []
        for e in node.elts:
            elements.append(self.visit(e))
        return scala.List(elements)
    
    def visit_Tuple(self,node):        
        if node.elts:
            first = node.elts[0]
            if type(first) == ast.Str and first.s == 'TYPE_DECS':
                return scala.func_types(node.elts[1:])     
            else: 
                elements =[]
                for e in node.elts:
                    elements.append(self.visit(e))
                return scala.List(elements)
        else:
            return scala.List([])
            
    """"
    only for loops of type below work:
        for item in list:
    cannot use ranges yet..        
    """        
    def visit_For(self,node):
        body = [self.visit(x) for x in node.body]
        return scala.For(self.visit(node.target), self.visit(node.iter), body)
    
    def visit_While(self,node):
        newbody = []
        for stmt in node.body:
            newbody.append(self.visit(stmt))
        return scala.While(self.visit(node.test), newbody)

    def visit_Expr(self,node):
        return self.visit(node.value)
   
    def visit_Attribute(self,node):
        return scala.Attribute(self.visit(node.value), node.attr)
        
    def visit_Compare(self, node):
        # only handles 1 thing on right side for now (1st op and comparator)
        # also currently not handling: Is, IsNot, In, NotIn
        ops = {'Eq':'==','NotEq':'!=','Lt':'<','LtE':'<=','Gt':'>','GtE':'>='}
        op = ops[node.ops[0].__class__.__name__]
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        return scala.Compare(left, op, right)
        
    def visit_BinOp(self,node):
        return scala.BinOp(self.visit(node.left), self.visit(node.op),self.visit(node.right))

    def visit_BoolOp(self,node):
        values = []
        for v in node.values:
            values.append(self.visit(v))
        return scala.BoolOp(self.visit(node.op), values)
    
    def visit_UnaryOp(self,node):
	       return scala.UnaryOp(self.visit(node.op), self.visit(node.operand))
  

class LoopUnroller(object):
    class UnrollReplacer(NodeTransformer):
        def __init__(self, loopvar, increment):
            self.loopvar = loopvar
            self.increment = increment
            self.in_new_scope = False
            self.inside_for = False
            super(LoopUnroller.UnrollReplacer, self).__init__()

        def visit_CName(self, node):
            #print "node.name is ", node.name
            if node.name == self.loopvar:
                return cpp.BinOp(cpp.CName(self.loopvar), "+", cpp.CNumber(self.increment))
            else:
                return node

        def visit_Block(self, node):
            #print "visiting Block...."
            if self.inside_for:
                old_scope = self.in_new_scope
                self.in_new_scope = True
                #print "visiting block in ", node
                contents = [self.visit(x) for x in node.contents]
                retnode = cpp.Block(contents=[x for x in contents if x != None])
                self.in_new_scope = old_scope
            else:
                self.inside_for = True
                contents = [self.visit(x) for x in node.contents]
                retnode = cpp.Block(contents=[x for x in contents if x != None])

            return retnode

        # assigns take care of stuff like "int blah = foo"
        def visit_Value(self, node):
            if not self.in_new_scope:
                return None
            else:
                return node

        def visit_Pointer(self, node):
            if not self.in_new_scope:
                return None
            else:
                return node

        # ignore typecast declarators
        def visit_TypeCast(self, node):
            return cpp.TypeCast(node.tp, self.visit(node.value))

        # make lvalue not a declaration
        def visit_Assign(self, node):
            if not self.in_new_scope:
                if isinstance(node.lvalue, cpp.NestedDeclarator):
                    tp, new_lvalue = node.lvalue.subdecl.get_decl_pair()
                    rvalue = self.visit(node.rvalue)
                    return cpp.Assign(cpp.CName(new_lvalue), rvalue)

                if isinstance(node.lvalue, cpp.Declarator):
                    tp, new_lvalue = node.lvalue.get_decl_pair()
                    rvalue = self.visit(node.rvalue)
                    return cpp.Assign(cpp.CName(new_lvalue), rvalue)

            return cpp.Assign(self.visit(node.lvalue), self.visit(node.rvalue))

    def unroll(self, node, factor):
        """Given a For node, unrolls the loop with a given factor.

        If the number of iterations in the given loop is not a multiple of
        the unroll factor, a 'leftover' loop will be generated to run the
        remaining iterations.

        """

        import copy

        # we can't precalculate the number of leftover iterations in the case that
        # the number of iterations are not known a priori, so we build an Expression
        # and let the compiler deal with it
        #leftover_begin = cpp.BinOp(cpp.CNumber(factor),
        #                           "*", 
        #                           cpp.BinOp(cpp.BinOp(node.end, "+", 1), "/", cpp.CNumber(factor)))


        # we begin leftover iterations at factor*( (end-initial+1) / factor ) + initial
        # note that this works due to integer division
        leftover_begin = cpp.BinOp(cpp.BinOp(cpp.BinOp(cpp.BinOp(cpp.BinOp(node.end, "-", node.initial),
                                                 "+",
                                                    cpp.CNumber(1)),
                                           "/",
                                           cpp.CNumber(factor)),
                                     "*",
                                     cpp.CNumber(factor)),
                               "+",
                               node.initial)

        new_limit = cpp.BinOp(node.end, "-", cpp.CNumber(factor-1))
        
#        debug_print("Loop unroller called with ", node.loopvar)
#        debug_print("Number of iterations: ", num_iterations)
#        debug_print("Number of unrolls: ", num_unrolls)
#        debug_print("Leftover iterations: ", leftover)

        new_increment = cpp.BinOp(node.increment, "*", cpp.CNumber(factor))

        new_block = cpp.Block(contents=node.body.contents)
        for x in xrange(1, factor):
            new_extension = copy.deepcopy(node.body)
            new_extension = LoopUnroller.UnrollReplacer(node.loopvar, x).visit(new_extension)
            new_block.extend(new_extension.contents)

        return_block = cpp.UnbracedBlock()

        unrolled_for_node = cpp.For(
            node.loopvar,
            node.initial,
            new_limit,
            #node.end,
            new_increment,
            new_block)

        leftover_for_node = cpp.For(
            node.loopvar,
            leftover_begin,
            node.end,
            node.increment,
            node.body)


        return_block.append(unrolled_for_node)

        # if we *know* this loop has no leftover iterations, then
        # we return without the leftover loop
        if not (isinstance(node.initial, cpp.CNumber) and isinstance(node.end, cpp.CNumber) and
           ((node.end.num - node.initial.num + 1) % factor == 0)):
            return_block.append(leftover_for_node)

        return return_block


class LoopBlocker(object):
    def loop_block(self, node, block_size):
        outer_incr_name = cpp.CName(node.loopvar + node.loopvar)

        new_inner_for = cpp.For(
            node.loopvar,
            outer_incr_name,
            cpp.FunctionCall("min", [cpp.BinOp(outer_incr_name, 
                                               "+", 
                                               cpp.CNumber(block_size-1)), 
                                     node.end]),
            cpp.CNumber(1),
            node.body)

        new_outer_for = cpp.For(
            node.loopvar + node.loopvar,
            node.initial,
            node.end,
            cpp.BinOp(node.increment, "*", cpp.CNumber(block_size)),
            cpp.Block(contents=[new_inner_for]))
        debug_print(new_outer_for)
        return new_outer_for

class LoopSwitcher(NodeTransformer):
    """
    Class that switches two loops.  The user is responsible for making sure the switching
    is valid (i.e. that the code can still compile/run).  Given two integers i,j this
    class switches the ith and jth loops encountered.
    """

    
    def __init__(self):
        self.current_loop = -1
        self.saved_first_loop = None
        self.saved_second_loop = None
        super(LoopSwitcher, self).__init__()

    def switch(self, tree, i, j):
        """Switch the i'th and j'th loops in tree."""
        self.first_target = min(i,j)
        self.second_target = max(i,j)

        self.original_ast = tree
        
        return self.visit(tree)

    def visit_For(self, node):
        self.current_loop += 1

        debug_print("At loop %d, targets are %d and %d" % (self.current_loop, self.first_target, self.second_target))

        if self.current_loop == self.first_target:
            # save the loop
            debug_print("Saving loop")
            self.saved_first_loop = node
            new_body = self.visit(node.body)
            assert self.second_target < self.current_loop + 1, 'Tried to switch loops %d and %d but only %d loops available' % (self.first_target, self.second_target, self.current_loop + 1)
            # replace with the second loop (which has now been saved)
            return cpp.For(self.saved_second_loop.loopvar,
                           self.saved_second_loop.initial,
                           self.saved_second_loop.end,
                           self.saved_second_loop.increment,
                           new_body)


        if self.current_loop == self.second_target:
            # save this
            self.saved_second_loop = node
            # replace this
            debug_print("replacing loop")
            return cpp.For(self.saved_first_loop.loopvar,
                           self.saved_first_loop.initial,
                           self.saved_first_loop.end,
                           self.saved_first_loop.increment,
                           node.body)


        return cpp.For(node.loopvar,
                       node.initial,
                       node.end,
                       node.increment,
                       self.visit(node.body))

########NEW FILE########
__FILENAME__ = codegen_scala
from ast import *
from ast_tools import *
import scala_ast

BOOLOP_SYMBOLS = {
    And:        'and',
    Or:         'or'
}

BINOP_SYMBOLS = {
    Add:        '+',
    Sub:        '-',
    Mult:       '*',
    Div:        '/',
    FloorDiv:   '//',
    Mod:        '%',
    LShift:     '<<',
    RShift:     '>>',
    BitOr:      '|',
    BitAnd:     '&',
    BitXor:     '^'
}

CMPOP_SYMBOLS = {
    Eq:         '==',
    Gt:         '>',
    GtE:        '>=',
    In:         'in',
    Is:         'is',
    IsNot:      'is not',
    Lt:         '<',
    LtE:        '<=',
    NotEq:      '!=',
    NotIn:      'not in'
}

UNARYOP_SYMBOLS = {
    Invert:     '~',
    Not:        'not',
    UAdd:       '+',
    USub:       '-'
}

TYPES = {
    'int' : 'Int',
    'float': 'Float',
    'double': 'Double',
    'string': 'String', 
    'boolean': 'Boolean',
    'null': 'Unit'
    }

"""
POSSIBLE TYPES:
int
float
double
string
(array, type) i.e. (array, int)
(tuple, type, type [,type..]) i.e. (tuple, int, int)
boolean
specific class name
null
"""

ALL_SYMBOLS = {}
ALL_SYMBOLS.update(BOOLOP_SYMBOLS)
ALL_SYMBOLS.update(BINOP_SYMBOLS)
ALL_SYMBOLS.update(CMPOP_SYMBOLS)
ALL_SYMBOLS.update(UNARYOP_SYMBOLS)


def to_source(node):
    generator = SourceGenerator()
    generator.visit(node)
    return ''.join(generator.result)

class SourceGenerator(NodeVisitor):
    def __init__(self, func_types):
        self.result = []
        self.new_lines = 0
        self.indentation =0
        self.indent_with=' ' * 4
        self.stored_vals = {}
        self.current_func = ''
        self.prev_func = ''
        self.vars = {}       
        self.types = {}
        self.subl_count = 0
        self.set_func_types(func_types)

    
    def to_source(self, node):
        self.result = []
        self.visit(node)
        return ''.join(self.result)      
     
    def add_func_type(self, type):
        self.types.append(type)
             
    def already_def(self, var):
        if self.current_func in self.vars.keys():
            if var in self.vars[self.current_func]:
                return True
            else: 
                return False
    
    def store_var(self,var):
        if self.current_func in self.vars.keys():
            self.vars[self.current_func].append(var)
        else: self.vars[self.current_func] = [var]            
    
    def write(self,x):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)
            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0
        self.result.append(x)
        
    def newline(self, node=None, extra=0):
        if isinstance(node, Call) and self.new_lines ==-1:
            self.new_lines = 0
        else:
            self.new_lines = max(self.new_lines, 1 + extra)

    def body(self, statements):
        self.new_line = True
        self.indentation += 1
        for stmt in statements:
            self.visit(stmt)
        self.indentation -= 1
        
    def convert_types(self,input_type):
        if len(input_type) == 2 and input_type[0] == 'array':
            #return 'org.apache.avro.generic.GenericData.Array[%s]' % (convert_types(input_type[1]))
            return 'Array[%s]' %(self.convert_types(input_type[1]))
        elif len(input_type) == 2 and input_type[0] == 'list':
            return 'List[%s]' %(self.convert_types(input_type[1]))
        elif len(input_type) == 3 and input_type[0] == 'tuple':
            str = '('
            for x in input_type[1:]:
                str += self.convert_types(x) +','
            return str[0:-1] + ')'
        
        elif input_type in TYPES:
            return TYPES[input_type]
        else:
            print 'WARNING POTENTIAL SCALA TYPE MISMATCH OF:', input_type
            return input_type
        
    def set_func_types(self,types):
        source = []
        for func in types:
            name = func[0]
            #convert types somewhere?
            scala_arg_types, scala_ret_type = [],[]
            for arg in func[1]:
                scala_arg_types.append(self.convert_types(arg))
            scala_ret_type = self.convert_types(func[2])
            self.types[name] = [scala_arg_types, scala_ret_type]    
        
    def visit_Number(self, node):
        self.write(repr(node.num))

    def visit_String(self, node):
        self.write('"')
        self.write(node.text)
        self.write('"')
    
    def visit_Name(self, node):
        self.write(node.name)

    def visit_Expression(self, node):
        self.newline(node) #may cause problems in newline()
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if type(node.op) == ast.Pow:
            self.write('math.pow(')
            self.visit(node.left)
            self.write(', ')
            self.visit(node.right)
            self.write(')')
        else:
            self.write('(')
            self.visit(node.left)
            self.write(' ' + node.op + ' ')
            self.visit(node.right)
            self.write(')')
    
    def visit_BoolOp(self,node):
        self.newline(node)
        self.write('(')
        op = BOOLOP_SYMBOLS[type(node.op)]             
        self.visit(node.values[0])
        if op == 'and':
            self.write(' && ')
        elif op == 'or':
            self.write(' || ')
        else:
            raise Error("Unsupported BoolOp type")
        
        self.visit(node.values[1])
        self.write(')')   
    
    def visit_UnaryOp(self, node):
        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)] 
        self.write(op)  
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):        
        if node.context == 'load':
            if isinstance(node.index, ast.Slice):
                self.write('scala_lib.slice(')
                self.visit(node.value)
                self.write(', ')
                self.visit(node.index.lower)
                self.write(', ')
                self.visit(node.index.upper)
                self.write(')')
            else:
                self.visit(node.value)
                self.write('(')
                self.visit(node.index)
                self.write(')')
        else: 
            self.visit(node.value)
            self.write('(')
            if isinstance(node.index, ast.Slice):
                raise Exception("Slice assign not supported")
            self.visit(node.index)
            self.write(')')
            #will finish this in assign
        
    #what about newline stuff?? sort of n    
    #will need to replace outer 's with "" s ...
    #to do the above, for SString add a flag that if set the 's are removed
    
    def visit_Print(self, node):
        self.newline(node)
        if node.dest:
            self.write('System.err.')
        self.write('println(')
        plus = False
        for t in node.text: 
            if plus: self.write('+" " + ')  
            self.visit(t)
            plus = True
        self.write(')')

    def visit_List(self,node):
        elements = node.elements
        self.write('scala.collection.mutable.MutableList(')
        size = len(elements)
        for i in range(size):
            elem = elements[i]
            self.visit(elem)
            if i != size-1:
                self.write(', ')   
        self.write(')')         
             
    def visit_Attribute(self,node):
        self.visit(node.value)
        self.write('.' + node.attr)   
    
    def evaluate_func(self,node):
        if node.func.name == 'range':
            self.write('Range(0,')
            self.visit(node.args[0])
            self.write(')')
        elif node.func.name == 'len':
            self.visit(node.args[0])
            self.write('.length')
        elif node.func.name == 'int':
            self.visit(node.args[0])
            self.write('.asInstanceOf[Int]')
        elif node.func.name == 'str':
            self.write("Integer.parseInt(")
            self.visit(node.args[0])
            self.write(')')
        elif node.func.name == 'float':
            self.visit(node.args[0])
            self.write('.asInstanceOf[Double]')
        elif node.func.name == 'read_avro_file':
            self.write('(new JAvroInter("res.avro", "args.avro")).readModel(')
            self.visit(node.args[0])
            self.write(')')
        else:
            self.visit(node.func)
            self.write('(')
            comma = False
            for a in node.args:
                if comma: self.write(', ')
                self.visit(a)
                comma = True
            self.write(')')         
        
    def evaluate_attr_func(self,node):
        if node.func.attr == 'append':
            self.visit(node.func.value)            
            self.write(' += (')
            self.visit(node.args[0])
            self.write(')')
        else:
            self.visit(node.func)
            self.write('(')
            comma = False
            for a in node.args:
                if comma: self.write(', ')
                self.visit(a)
                comma = True
            self.write(')')                 
        
    def visit_Call(self,node):
        self.newline(node)             
        if isinstance(node.func,scala_ast.Name):
            self.evaluate_func(node)   
        elif isinstance(node.func,scala_ast.Attribute):
            self.evaluate_attr_func(node)
        
    def visit_Function(self,node):
        self.newline(node)
        self.visit(node.declaration)
        self.write('{ ')        
        self.body(node.body)
        self.current_func = self.prev_func
        self.write("\n}")
    
    def visit_FunctionDeclaration(self,node):
        self.write('def '+node.name+'( ')    
        self.prev_func = self.current_func    
        self.current_func = node.name
        arg_types = self.types[node.name][0]
        ret_type = self.types[node.name][1]
        
        self.visit_Arguments(node.args, arg_types)
        self.write('): %s =' %(ret_type))
        
    def visit_Arguments(self,node, types=None):   
        comma = False     
        for i in range(len(node.args)):
            if comma:self.write(', ')
            arg = node.args[i]
            self.visit(arg)
            if types:
                self.write(': %s' %types[i])
            else:
                self.write(': Any')
            comma = True
    
    def visit_ReturnStatement(self, node):
        self.newline(node)
        self.write('return ')
        self.new_lines = -1
        self.visit(node.retval)
        self.new_lines = 0
        
    def visit_Compare(self,node):
        self.newline(node,-1)
        self.write('(')
        self.visit(node.left)
        self.write(' %s ' %(node.op))
        self.visit(node.right)
        self.write(')')
    
    def visit_AugAssign(self,node):
        self.newline(node)
        self.visit(node.target)
        self.write(' ' + node.op +'= ')
        self.visit(node.value)
                   
    def visit_Assign(self,node):
        try:
            if node.lvalue.name == 'TYPE_DECS':
                self.visit(node.rvalue)
                return 0
        except: pass        
        self.newline(node)       
        self.stored_vals["lvalue"] = node.lvalue
        if not isinstance(node.lvalue, Subscript) and not isinstance(node.lvalue, Attribute)\
            and not self.already_def(node.lvalue.name):
            self.write('var ')
            self.store_var(node.lvalue.name)
        self.visit(node.lvalue)
        self.write(' = ')       
        self.new_lines = -1
        self.visit(node.rvalue)
        self.new_lines = 0   
    
    def visit_IfConv(self,node): 
        self.newline(node)
        if node.inner_if:
            self.write('else if (')
        else:
            self.write('if(')
        self.visit(node.test)
        self.write(') {')
        self.body(node.body)
        self.newline(node)
        self.write('}')
        
        if node.orelse:
            if not isinstance(node.orelse[0], IfConv):
                self.newline(node)
                self.write('else { ')
                self.body(node.orelse)
                self.newline(node)
                self.write('}')
            else:
                self.visit_IfConv(node.orelse[0])
  
    def visit_For(self,node):
        self.newline(node)
        self.write('for (')
        self.visit(node.target)
        self.write( ' <- ')
        self.visit(node.iter)
        self.write(') {')
        self.body(node.body)
        self.newline(node)
        self.write('}')
    
    def visit_While(self, node):
        self.newline(node)
        self.write('while (')
        #self.new_lines = -1
        self.visit(node.test)
        self.write(') {')
        self.newline(node)
        self.body(node.body)
        self.newline(node)
        self.write('}')
    
    
    
    
    
########NEW FILE########
__FILENAME__ = cpp_ast
import codepy.cgen
from cgen import *
import xml.etree.ElementTree as ElementTree

# these are additional classes that, along with codepy's classes, let
# programmers express the C code as a real AST (not the hybrid AST/strings/etc
# that codepy implements.

#TODO: add all of CodePy's classes we want to support

class CNumber(Generable):
    def __init__(self, num):
        self.num = num
        self._fields = []

#    def __str__(self):
#        return str(self.num)

    def to_xml(self):
        return ElementTree.Element("CNumber", attrib={"num":str(self.num)})

    def generate(self, with_semicolon=False):
        if with_semicolon:
            # This node type does not represent a complete C++ statement
            raise ValueError
        yield str(self.num)

class String(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield '\"%s\"' % self.text

class CName(Generable):
    def __init__(self, name):
        self.name = name
        self._fields = []

    def to_xml(self):
        return ElementTree.Element("CName", attrib={"name":str(self.name)})

    def generate(self, with_semicolon=False):
        if with_semicolon:
            # This node type does not represent a complete C++ statement
            raise ValueError
        yield self.name

class Expression(Generable):
    def __init__(self):
        super(Expression, self).__init__()
        self._fields = []

    def generate(self, with_semicolon=False):
        yield ""
        

class BinOp(Expression):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
        self._fields = ['left', 'right']

    def generate(self, with_semicolon=False):
        yield "(%s %s %s)" % (self.left, self.op, self.right) + (";" if with_semicolon else "")

    def split(self, x):
        return str(self).split(x)

    def to_xml(self):
        node = ElementTree.Element("BinOp", attrib={"op":str(self.op)})
        left = ElementTree.SubElement(node, "left")
        left.append(self.left.to_xml())
        right = ElementTree.SubElement(node, "right")
        right.append(self.right.to_xml())
        return node

class UnaryOp(Expression):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
        self._fields = ['operand']

    def generate(self, with_semicolon=False):
        yield "(%s(%s))" % (self.op, self.operand) + (";" if with_semicolon else "")

    def to_xml(self):
        node = ElementTree.Element("UnaryOp", attrib={"op":str(self.op)})
        operand = ElementTree.SubElement(node, "operand")
        operand.append(self.operand.to_xml())
        return node

class Subscript(Expression):
    def __init__(self, value, index):
        self.value = value
        self.index = index
        self._fields = ['value', 'index']

    def generate(self, with_semicolon=False):
        yield "%s[%s]" % (self.value, self.index)

    def to_xml(self):
        node = ElementTree.Element("Subscript")
        ElementTree.SubElement(node, "value").append(self.value.to_xml())
        ElementTree.SubElement(node, "index").append(self.index.to_xml())
        return node

class Call(Expression):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self._fields = ['func', 'args']

    def generate(self, with_semicolon=False): 
        yield "%s(%s)" % (self.func, ", ".join(map(str, self.args))) + (";" if with_semicolon else "")

    def to_xml(self):
        node = ElementTree.Element("Call", attrib={"func":str(self.func)})
        args = ElementTree.SubElement(node, "args")
        for x in self.args:
            args.append(x.to_xml())
        return node


class PostfixUnaryOp(Expression):
    def __init__(self, operand, op):
        self.operand = operand
        self.op = op
        self._fields = ['op', 'operand']

    def generate(self, with_semicolon=False):
        yield "((%s)%s)" % (self.operand, self.op) + (";" if with_semicolon else "")

    def to_xml(self):
        node = ElementTree.Element("PostfixUnaryOp", attrib={"op":str(self.op)})
        operand = ElementTree.SubElement(node, "operand")
        operand.append(self.operand.to_xml())
        return node


class ConditionalExpr(Expression):
    def __init__(self, test, body, orelse):
        self.test = test
        self.body = body
        self.orelse = orelse
        self._fields = ['test', 'body', 'orelse']

    def generate(self, with_semicolon=False):
        yield "(%s ? %s : %s)" % (self.test, self.body, self.orelse) + (";" if with_semicolon else "")

    def to_xml(self):
        node = ElementTree.Element("ConditionalExpr")
        ElementTree.SubElement(node, "test").append(self.test.to_xml())
        ElementTree.SubElement(node, "body").append(self.body.to_xml())
        ElementTree.SubElement(node, "orelse").append(self.orelse.to_xml())
        return node

class TypeCast(Expression):
    # "type" should be a declaration with an empty variable name
    # e.g. TypeCast(Pointer(Value('int', '')), ...)

    def __init__(self, tp, value):
        self.tp = tp
        self.value = value
        self._fields = ['tp', 'value']

    def generate(self, with_semicolon=False):
        yield "((%s)%s)" % (self.tp.inline(), self.value)

#class ForInitializer(codepy.cgen.Initializer):
#    def __str__(self):
#        return super(ForInitializer, self).__str__()[0:-1]

class Initializer(codepy.cgen.Initializer):
    def __init__(self, vdecl, data):
        self._fields = ['vdecl', 'data']
        super(Initializer, self).__init__(vdecl, data)

    def generate(self, with_semicolon=False):
        tp_lines, tp_decl = self.vdecl.get_decl_pair()
        tp_lines = list(tp_lines)
        for line in tp_lines[:-1]:
            yield line
        yield "%s %s = %s" % (tp_lines[-1], tp_decl, self.data) + (";" if with_semicolon else "")
    
class Pragma(codepy.cgen.Pragma):
    def __init__(self, value):
        self._fields = ['value']
        super(Pragma, self).__init__(value)

    def generate(self, with_semicolon=False):
        return super(Pragma, self).generate()

class RawFor(codepy.cgen.For):
    def __init__(self, start, condition, update, body):
        super(RawFor, self).__init__(start, condition, update, body)
        self._fields = ['start', 'condition', 'update', 'body']

    def generate(self, with_semicolon=False):
        return super(RawFor, self).generate()

    def to_xml(self):
        node = ElementTree.Element("For")
        if (not isinstance(self.start, str)):
            ElementTree.SubElement(node, "start").append(self.start.to_xml())
        else:
            ElementTree.SubElement(node,"start").text = self.start
            
        if (not isinstance(self.condition, str)):
            ElementTree.SubElement(node, "condition").append(self.condition.to_xml())
        else:
            ElementTree.SubElement(node, "condition").text = self.condition

        if (not isinstance(self.update, str)):
            ElementTree.SubElement(node, "update").append(self.update.to_xml())
        else:
            ElementTree.SubElement(node, "update").text = self.update
            
        ElementTree.SubElement(node, "body").append(self.body.to_xml())
        return node

class For(RawFor):
    #TODO: setting initial,end,etc should update the field in the shadow
    #TODO: should loopvar be a string or a CName?
    def __init__(self, loopvar, initial, end, increment, body):
        # use setattr on object so we don't use our special one during initialization
        object.__setattr__(self, "loopvar", loopvar)
        object.__setattr__(self, "initial", initial)
        object.__setattr__(self, "end", end)
        object.__setattr__(self, "increment", increment)
        self._fields = ['start', 'condition', 'update', 'body']

        super(For, self).__init__(
            Initializer(Value("int", self.loopvar), self.initial),
            BinOp(CName(self.loopvar), "<=", self.end),
            Assign(CName(self.loopvar), BinOp(CName(self.loopvar), "+", self.increment)),
            body)

    def set_underlying_for(self):
        self.start = Initializer(Value("int", self.loopvar), self.initial)
        self.condition = BinOp(CName(self.loopvar), "<=", self.end)
        self.update = Assign(CName(self.loopvar), BinOp(CName(self.loopvar), "+", self.increment))

    def generate(self, with_semicolon=False):
        return super(For, self).generate()

    def intro_line(self):
        return "for (%s; %s; %s)" % (self.start,
                                     self.condition,
                                     self.update)

    def __setattr__(self, name, val):
        # we want to convey changes to the for loop to the underlying
        # representation.
        object.__setattr__(self, name, val)
        if name in ["loopvar", "initial", "end", "increment"]:
            self.set_underlying_for()



class FunctionBody(codepy.cgen.FunctionBody):
    def __init__(self, fdecl, body):
        super(FunctionBody, self).__init__(fdecl, body)
        self._fields = ['fdecl', 'body']

    def generate(self, with_semicolon=False):
        return super(FunctionBody, self).generate()
        
    def to_xml(self):
        node = ElementTree.Element("FunctionBody")
        ElementTree.SubElement(node, "fdecl").append(self.fdecl.to_xml())
        ElementTree.SubElement(node, "body").append(self.body.to_xml())
        return node

class FunctionDeclaration(codepy.cgen.FunctionDeclaration):
    def __init__(self, subdecl, arg_decls):
        super(FunctionDeclaration, self).__init__(subdecl, arg_decls)
        self._fields = ['subdecl', 'arg_decls']

    def to_xml(self):
        node = ElementTree.Element("FunctionDeclaration")
        ElementTree.SubElement(node, "subdecl").append(self.subdecl.to_xml())
        arg_decls = ElementTree.SubElement(node, "arg_decls")
        for x in self.arg_decls:
            arg_decls.append(x.to_xml())
        return node

class Value(codepy.cgen.Value):
    def __init__(self, typename, name):
        super(Value, self).__init__(typename, name)
        self._fields = []
        
    def to_xml(self):
        return ElementTree.Element("Value", attrib={"typename":self.typename, "name":self.name})

class Pointer(codepy.cgen.Pointer):
    def __init__(self, subdecl):
        super(Pointer, self).__init__(subdecl)
        self._fields = ['subdecl']
        
    def to_xml(self):
        node = ElementTree.Element("Pointer")
        ElementTree.SubElement(node, "subdecl").append(self.subdecl.to_xml())
        return node

class Block(codepy.cgen.Block):
    def __init__(self, contents=[]):
        super(Block, self).__init__(contents)
        self._fields = ['contents']

    def generate(self, with_semicolon=False):
        yield "{"
        for item in self.contents:
            for item_line in item.generate(with_semicolon=True):
                yield "  " + item_line
        yield "}"       
    def to_xml(self):
        node = ElementTree.Element("Block")
        for x in self.contents:
            node.append(x.to_xml())
        return node

class UnbracedBlock(Block):
    def generate(self, with_semicolon=False):
        for item in self.contents:
            for item_line in item.generate(with_semicolon=True):
                yield " " + item_line


class Define(codepy.cgen.Define):
    def __init__(self, symbol, value):
        super(Define, self).__init__(symbol, value)
        self._fields = ['symbol', 'value']

    def generate(self, with_semicolon=False):
        return super(Define, self).generate()
        
    def to_xml(self):
        return ElementTree.Element("Define", attrib={"symbol":self.symbol, "value":self.value})

class Statement(codepy.cgen.Statement):
    def __init__(self, text):
        super(Statement, self).__init__(text)
        self._fields = []
        
    def to_xml(self):
        node = ElementTree.Element("Statement")
        node.text = self.text
        return node

class Assign(codepy.cgen.Assign):
    def __init__(self, lvalue, rvalue):
        super(Assign, self).__init__(lvalue, rvalue)
        self._fields = ['lvalue', 'rvalue']
        
    def to_xml(self):
        node = ElementTree.Element("Assign")
        ElementTree.SubElement(node, "lvalue").append(self.lvalue.to_xml())
        ElementTree.SubElement(node, "rvalue").append(self.rvalue.to_xml())
        return node

    def generate(self, with_semicolon=False):
        lvalue = self.lvalue.generate(with_semicolon=False).next()
        rvalue = str(self.rvalue)
        yield "%s = %s" % (lvalue, rvalue) + (";" if with_semicolon else "")

class FunctionCall(codepy.cgen.Generable):
    def __init__(self, fname, params=[]):
        self.fname = fname
        self.params = params
        self._fields = ['fname', 'params']

    def generate(self, with_semicolon=False):
        yield "%s(%s)" % (self.fname, ','.join(map(str, self.params))) + (";" if with_semicolon else "")

class Print(Generable):
    def __init__(self, text, newline):
        self.text = text
        self.newline = newline

    def generate(self, with_semicolon=True):
        if self.newline:
            yield 'std::cout %s << std::endl;' % self.text
        else:
            yield 'std::cout %s;' % self.text

class Compare(Generable):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
        self._fields = ('left', 'op', 'right')

    # cgen as of 4/24/2012 has a bug that directly calls split() on a Compare object.
    # see https://github.com/shoaibkamil/asp/issues/32
    def split(self, t):
        return str(self).split(t)

    def generate(self, with_semicolon=False):
        yield '%s %s %s' % (self.left, self.op, self.right)

class IfConv(If):
    def generate(self, with_semicolon=False):
        return super(IfConv, self).generate()



class ReturnStatement (Generable):
    def __init__ (self, retval):
        self.retval = retval
        self._fields = ['retval']
        
    def generate (self, with_semicolon=True):
        ret = 'return ' + str(self.retval)
        if with_semicolon:
            ret = ret + ';'
              
        yield ret

########NEW FILE########
__FILENAME__ = ctypes_converter
from ctypes import *

# converts from a class that is a ctypes Structure into the C declaration of the datatype
class StructConverter(object):
    # we currently do not support int8/int16/etc
    _typehash_ = {'c_int':'int',
                  'c_byte': 'byte',
                  'c_char': 'char',
                  'c_char_p': 'char*',
                  'c_double': 'double',
                  'c_longdouble': 'long double',
                  'c_float': 'float',
                  'c_long': 'long',
                  'c_longlong': 'long long',
                  'c_short': 'short',
                  'c_size_t': 'size_t',
                  'c_ssize_t': 'ssize_t',
                  'c_ubyte': 'unsigned char',
                  'c_uint': 'unsigned int',
                  'c_ulong': 'unsigned long',
                  'c_ulonglong': 'unsigned long long',
                  'c_ushort': 'unsigned short',
                  'c_void_p': 'void*',
                  'c_wchar': 'wchcar_t',
                  'c_wchar_p': 'wchar_t*',
                  'c_bool': 'bool'}
                  
    def __init__(self):
        self.all_structs = {}
    
    def visitor(self, item):
        if type(item) == type(POINTER(c_int)):
            return self.visitor(item._type_) + "*"
        elif type(item) == type(c_int * 4):
            # if it is an array:
            return (self.visitor(item._type_), item._length_)
        elif item.__name__ in self._typehash_:
            return self._typehash_[item.__name__]
        else:
            if item.__name__ not in self.all_structs.keys():
                self.convert(item)
            return item.__name__
    
    def convert(self, cl):
        """Top-level function for converting from ctypes Structure to it's C++ equivalent declaration.
        
        The function returns a hash with keys corresponding to structure names encountered, and values
        corresponding to the definition of the type.
        """
        def mapfunc(x):
            ret = self.visitor(x[1])
            if type(ret) is tuple:
                return "%s %s[%s];" % (ret[0], x[0], ret[1])
            else:
                return "%s %s;" % (ret, x[0])
        
        # try to avoid infinite recursion for types defined with self-recursion or mutual recursion
        self.all_structs[cl.__name__] = None
        
        fields = map(mapfunc, cl._fields_)
        self.all_structs[cl.__name__] = "struct %s { %s };" % (cl.__name__, '\n'.join(fields))
        
        return self.all_structs
########NEW FILE########
__FILENAME__ = python_ast
from ast import *



########NEW FILE########
__FILENAME__ = scala_ast
import ast

"""
I don't use the Generable class inheritance
"""

class Generable():
	pass

class func_types(Generable):	
	def __init__(self, types):
		self.types = types
		self._fields = []			
	
class Number(Generable):
	def __init__(self, num):
		self.num = num
		self._fields = []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class String(Generable):
	def __init__(self, text):
		self.text = text
		self._fields = ['text']
		self.done = False
	
	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class Name(Generable):
	def __init__(self,name):
		self.name= name
		self._fields= []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class Function(Generable):
	def __init__(self, declaration, body):
		self.declaration = declaration
		self.body = body
		self._fields = []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class Arguments(Generable):
	def __init__(self, args):
		self.args = args
		self._fields = []
		
class FunctionDeclaration(Generable):
	def __init__(self, name, args):
		self.name = name
		self.args = args

class Expression(Generable):
	def __init__(self):
		# ???
		super(Expression, self)
		self._fields = []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class Call(Expression):	
	def __init__(self, func, args):
		self.func = func
		self.args = args
		self._fields = []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
	
class Attribute(Expression):	
	def __init__(self, value, attr):	
		self.attr = attr
		self.value = value
		
class List(Expression):
	def __init__(self, elements):
		self.elements = elements
		self._fields = []
		
class BinOp(Expression):
	def __init__(self, left, op, right):
		self. left = left
		self.op = op
		self.right = right
		self._fields = ['left', 'right']
		self.done = False

class BoolOp(Expression):
	def __init__(self, op, values):
		self.op = op
		self.values = values
		self._fields = ['op', 'values']
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class UnaryOp(Expression):
	def __init__(self, op, operand):
		self.op = op
		self.operand = operand
		self._fields = ['operand']	

class Subscript(Expression):
	def __init__(self, value, index, context):
		self.value = value
		self.index = index
		self.context = context
		self._fields = ['value', 'index', 'context']

class Print(Generable):
	def __init__(self,text,newline,dest):
		self.text = text
		self.newline = newline
		self.dest= dest
		self.done = False
		
	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
		
class ReturnStatement(Generable):
	def __init__(self, retval):
		self.retval = retval
		self._fields = ['retval']
		self.done = False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
		
class AugAssign(Generable):
	def __init__(self, target, op, value):
		self.target = target
		self.op = op
		self.value = value
		self.done = False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
		

class Assign(Generable): #should this inherit from something else??
	def __init__(self, lvalue, rvalue):
		##??
		self.lvalue = lvalue
		self.rvalue= rvalue
		self._fields = ['lvalue', 'rvalue']
		self.done = False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
		
		
class Compare(Generable):
	def __init__(self, left,op,right):
		self.left = left
		self.op = op
		self.right = right
		self.done=False
		self._fields = ('left', 'op', 'right')
		
	def __iter__(self):	
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done=True
			return self
		
class IfConv(Generable):
	def __init__(self, test, body, orelse, inner_if=False):
		self.test = test
		self.body = body
		self.orelse = orelse
		self.inner_if = inner_if
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
		
class For(Generable): 
	def __init__(self, target, iter, body):
		self.target = target
		self.iter = iter
		self.body = body
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self

class While(Generable):
	def __init__(self, test, body):
		self.test = test
		self.body = body
		self._fields = []
		self.done= False

	def __iter__(self):
		return self
	
	def next(self):
		if self.done:
			raise StopIteration
		else:
			self.done = True
			return self
	
	
if __name__ == '__main__':
	pass


########NEW FILE########
__FILENAME__ = template
from mako.template import *

########NEW FILE########
__FILENAME__ = config
import re
import yaml
import os
import asp.jit.asp_module as asp_module
from codepy.cgen import Include


class CompilerDetector(object):
    """
    Detect if a particular compiler is available by trying to run it.
    """
    def detect(self, compiler):
        from pytools.prefork import call_capture_output
        try:
            retcode, stdout, stderr = call_capture_output([compiler, "--version"])
        except:
            return False

        return (retcode == 0)
        
class PlatformDetector(object):
    def __init__(self):
        self.rawinfo = []
        self.cuda_util_mod = asp_module.ASPModule(use_cuda=True)
        cuda_util_funcs = [ ("""
            void set_device(int dev) {
              int GPUCount;
              cudaGetDeviceCount(&GPUCount);
              if(GPUCount == 0) {
                dev = 0;
              } else if (dev >= GPUCount) {
                dev  = GPUCount-1;
              }
              cudaSetDevice(dev);
            }""", "set_device"),
            ("""
            boost::python::tuple device_compute_capability(int dev) {
              int major, minor;
              cuDeviceComputeCapability(&major, &minor, dev);
              return boost::python::make_tuple(major, minor);
            }""", "device_compute_capability"),
            ("""
            int get_device_count() {
              int count;
              cudaGetDeviceCount(&count);
              return count;
            }""", "get_device_count"),
            ("""
            int device_get_attribute( int attr, int dev) {
              int pi;
              cuDeviceGetAttribute(&pi, (CUdevice_attribute)attr, dev);
              return pi;
            }""", "device_get_attribute"),
            ("""
            size_t device_total_mem(int dev) {
                size_t bytes;
                cuDeviceTotalMem(&bytes, dev);
                return bytes;
            }""", "device_total_mem") ]
        for fbody, fname in cuda_util_funcs:
            self.cuda_util_mod.add_helper_function(fname, fbody, backend='cuda')
        self.cuda_device_id = None

    def get_num_cuda_devices(self):
        return self.cuda_util_mod.get_device_count()

    def set_cuda_device(self, device_id):
        self.cuda_device_id = device_id
        self.cuda_util_mod.set_device(device_id)
        
    def get_cuda_info(self):
        info = {}
        if self.cuda_device_id == None:
            raise RuntimeError("No CUDA device selected. Set device before querying.")
        attribute_list = [ # from CUdevice_attribute_enum at cuda.h:259
            ('max_threads_per_block',1),
            ('max_block_dim_x',2),
            ('max_block_dim_y',3),
            ('max_block_dim_z',4),
            ('max_grid_dim_x',5),
            ('max_grid_dim_y',6),
            ('max_grid_dim_z',7),
            ('max_shared_memory_per_block',8) ]
        d = self.cuda_device_id
        for key, attr in attribute_list:
            info[key] = self.cuda_util_mod.device_get_attribute(attr, d)
        info['total_mem']  = self.cuda_util_mod.device_total_mem(d)
        version = self.cuda_util_mod.device_compute_capability(d)
        info['capability'] = version
        info['supports_int32_atomics_in_global'] = False if version in [(1,0)] else True
        info['supports_int32_atomics_in_shared'] = False if version in [(1,0),(1,1)] else True
        info['supports_int64_atomics_in_global'] = False if version in [(1,0),(1,1)] else True
        info['supports_warp_vote_functions'] = False if version in [(1,0),(1,1)] else True
        info['supports_float64_arithmetic'] = False if version in [(1,0),(1,1),(1,2)] else True
        info['supports_int64_atomics_in_global'] = False if version[0] == 1 else True
        info['supports_float32_atomic_add'] = False if version[0] == 1 else True
        return info

    def get_cpu_info(self):
        self.rawinfo = self.read_cpu_info()
        info = {}
        info['numCores'] = self.parse_num_cores()
        info['vendorID'] = self.parse_cpu_info('vendor_id')
        info['model'] = int(self.parse_cpu_info('model'))
        info['cpuFamily'] = int(self.parse_cpu_info('cpu family'))
        info['cacheSize'] = int(self.parse_cpu_info('cache size'))
        info['capabilities'] = self.parse_capabilities()
        return info

    def get_compilers(self):
        return filter(CompilerDetector().detect, ["gcc", "icc", "nvcc"])

    def parse_capabilities(self):
        matcher = re.compile("flags\s+:")
        for line in self.rawinfo:
            if re.match(matcher, line):
                return line.split(":")[1].split(" ")
        
    def parse_num_cores(self):
        matcher = re.compile("processor\s+:")
        count = 0
        for line in self.rawinfo:
            if re.match(matcher, line):
                count +=1
        return count
        
    def parse_cpu_info(self, item):
        matcher = re.compile(item +"\s+:\s*(\w+)")
        for line in self.rawinfo:
            if re.match(matcher, line):
                return re.match(matcher, line).group(1)
        
    def read_cpu_info(self):
        return open("/proc/cpuinfo", "r").readlines()


class ConfigReader(object):
    """
    Interface for reading a per-user configuration file in YAML format.  The
    config file lives in ~/.asp_config.yml (on windows, ~ is equivalent to 
    \Users\<current user>).  
    
    On initialization, specify the specializer whose settings are going to be read.

    The format of the file should contain a specializer's
    settings in its own hash.  E.g.:
    specializer_foo:
      setting_one: value
      setting_two: value
    specializer_bar:
      setting_etc: value

    """
    def __init__(self, specializer):
        try:
            self.stream = open(os.path.expanduser("~")+'/.asp_config.yml')
            self.configs = yaml.load(self.stream)
        except:
            print "No configuration file ~/.asp_config.yml found."
            self.configs = {}

        self.specializer = specializer
            
        #translates from YAML file to Python dictionary


    # add functionality to iterate keys? 
    def get_option(self, key):
        """
        Given a key, return the value for that key, or None.
        """
        try:
            return self.configs[self.specializer][key]
        except KeyError:
            print "Configuration key %s not found" % key
            return None


########NEW FILE########
__FILENAME__ = asp_module
import codepy, codepy.jit, codepy.toolchain, codepy.bpl, codepy.cuda
from asp.util import *
import asp.codegen.cpp_ast as cpp_ast
import pickle
from variant_history import *
import sqlite3
import asp
import scala_module

class ASPDB(object):

    def __init__(self, specializer, persistent=False):
        """
        specializer must be specified so we avoid namespace collisions.
        """
        self.specializer = specializer

        if persistent:
            # create db file or load db
            # create a per-user cache directory
            import tempfile, os
            if os.name == 'nt':
                username = os.environ['USERNAME']
            else:
                username = os.environ['LOGNAME']

            self.cache_dir = tempfile.gettempdir() + "/asp_cache_" + username

            if not os.access(self.cache_dir, os.F_OK):
                os.mkdir(self.cache_dir)
            self.db_file = self.cache_dir + "/aspdb.sqlite3"
            self.connection = sqlite3.connect(self.db_file)
            self.connection.execute("PRAGMA temp_store = MEMORY;")
            self.connection.execute("PRAGMA synchronous = OFF;")
            
        else:
            self.db_file = None
            self.connection = sqlite3.connect(":memory:")


    def create_specializer_table(self):
        self.connection.execute('create table '+self.specializer+' (fname text, variant text, key text, perf real)')
        self.connection.commit()

    def close(self):
        self.connection.close()

    def table_exists(self):
        """
        Test if a table corresponding to this specializer exists.
        """
        cursor = self.connection.cursor()
        cursor.execute('select name from sqlite_master where name="%s"' % self.specializer)
        result = cursor.fetchall()
        return len(result) > 0

    def insert(self, fname, variant, key, value):
        if (not self.table_exists()):
                self.create_specializer_table()
        self.connection.execute('insert into '+self.specializer+' values (?,?,?,?)',
            (fname, variant, key, value))
        self.connection.commit()

    def get(self, fname, variant=None, key=None):
        """
        Return a list of entries.  If key and variant not specified, all entries from
        fname are returned.
        """
        if (not self.table_exists()):
            self.create_specializer_table()
            return []

        cursor = self.connection.cursor()
        query = "select * from %s where fname=?" % (self.specializer,)
        params = (fname,)

        if variant:
            query += " and variant=?"
            params += (variant,)
        
        if key:
            query += " and key=?"
            params += (key,)

        cursor.execute(query, params)

        return cursor.fetchall()

    def update(self, fname, variant, key, value):
        """
        Updates an entry in the db.  Overwrites the timing information with value.
        If the entry does not exist, does an insert.
        """
        if (not self.table_exists()):
            self.create_specializer_table()
            self.insert(fname, variant, key, value)
            return

        # check if the entry exists
        query = "select count(*) from "+self.specializer+" where fname=? and variant=? and key=?;"
        cursor = self.connection.cursor()
        cursor.execute(query, (fname, variant, key))
        count = cursor.fetchone()[0]
        
        # if it exists, do an update, otherwise do an insert
        if count > 0:
            query = "update "+self.specializer+" set perf=? where fname=? and variant=? and key=?"
            self.connection.execute(query, (value, fname, variant, key))
            self.connection.commit()
        else:
            self.insert(fname, variant, key, value)


    def delete(self, fname, variant, key):
        """
        Deletes an entry from the db.
        """
        if (not self.table_exists()):
            return

        query = "delete from "+self.specializer+" where fname=? and variant=? and key=?"
        self.connection.execute(query, (fname, variant, key))
        self.connection.commit()

    def destroy_db(self):
        """
        Delete the database.
        """
        if not self.db_file:
            return True

        import os
        try:
            self.close()
            os.remove(self.db_file)
        except:
            return False
        else:
            return True


class SpecializedFunction(object):
    """
    Class that encapsulates a function that is specialized.  It keeps track of variants,
    their timing information, which backend, functions to determine if a variant
    can run, as well as a function to generate keys from parameters.

    The signature for any run_check function is run(*args, **kwargs).
    The signature for the key function is key(self, *args, **kwargs), where the args/kwargs are
    what are passed to the specialized function.

    """
    
    def __init__(self, name, backend, db, variant_names=[], variant_funcs=[], run_check_funcs=[], 
                 key_function=None, call_policy=None):
        self.name = name
        self.backend = backend
        self.db = db
        self.variant_names = []
        self.variant_funcs = []
        self.run_check_funcs = []
        self.call_policy = call_policy
        
        if variant_names != [] and run_check_funcs == []:
            run_check_funcs = [lambda *args,**kwargs: True]*len(variant_names)
        
        for x in xrange(len(variant_names)):
            self.add_variant(variant_names[x], variant_funcs[x], run_check_funcs[x])

        if key_function:
            self.key = key_function

    def key(self, *args, **kwargs):
        """
        Function to generate keys.  This should almost always be overridden by a specializer, to make
        sure the information stored in the key is actually useful.
        """
        import hashlib
        return hashlib.md5(str(args)+str(kwargs)).hexdigest()


    def add_variant(self, variant_name, variant_func, run_check_func=lambda *args,**kwargs: True):
        """
        Add a variant of this function.  Must have same call signature.  Variant names must be unique.
        The variant_func parameter should be a CodePy Function object or a string defining the function.
        The run_check_func parameter should be a lambda function with signature run(*args,**kwargs).
        """
        if variant_name in self.variant_names:
            raise Exception("Attempting to add a variant with an already existing name %s to %s" %
                            (variant_name, self.name))
        self.variant_names.append(variant_name)
        self.variant_funcs.append(variant_func)
        self.run_check_funcs.append(run_check_func)
        
        if isinstance(self.backend.module, scala_module.ScalaModule):
            self.backend.module.add_to_module(variant_func)
            self.backend.module.add_to_init(variant_name)
        elif isinstance(variant_func, basestring):
            if isinstance(self.backend.module, codepy.cuda.CudaModule):#HACK because codepy's CudaModule doesn't have add_to_init()
                self.backend.module.boost_module.add_to_module([cpp_ast.Line(variant_func)])
                self.backend.module.boost_module.add_to_init([cpp_ast.Statement("boost::python::def(\"%s\", &%s)" % (variant_name, variant_name))])
            else:
                self.backend.module.add_to_module([cpp_ast.Line(variant_func)])
                if self.call_policy == "python_gc":
                    self.backend.module.add_to_init([cpp_ast.Statement("boost::python::def(\"%s\", &%s, boost::python::return_value_policy<boost::python::manage_new_object>())" % (variant_name, variant_name))])
                else:
                    self.backend.module.add_to_init([cpp_ast.Statement("boost::python::def(\"%s\", &%s)" % (variant_name, variant_name))])
        else:
            self.backend.module.add_function(variant_func)

        self.backend.dirty = True

    def pick_next_variant(self, *args, **kwargs):
        """
        Logic to pick the next variant to run.  If all variants have been run, then this should return the
        fastest variant.
        """
        # get variants that have run
        already_run = self.db.get(self.name, key=self.key(*args, **kwargs))


        if already_run == []:
            already_run_variant_names = []
        else:
            already_run_variant_names = map(lambda x: x[1], already_run)

        # which variants haven't yet run
        candidates = set(self.variant_names) - set(already_run_variant_names)

        # of these candidates, which variants *can* run
        for x in candidates:
            if self.run_check_funcs[self.variant_names.index(x)](*args, **kwargs):
                return x

        # if none left, pick fastest from those that have already run
        return sorted(already_run, lambda x,y: cmp(x[3],y[3]))[0][1]

    def __call__(self, *args, **kwargs):
        """
        Calling an instance of SpecializedFunction will actually call either the next variant to test,
        or the already-determined best variant.
        """
        if self.backend.dirty:
            self.backend.compile()

        which = self.pick_next_variant(*args, **kwargs)

        import time
        start = time.time()
        ret_val = self.backend.get_compiled_function(which).__call__(*args, **kwargs)
        elapsed = time.time() - start
        #FIXME: where should key function live?
        #print "doing update with %s, %s, %s, %s" % (self.name, which, self.key(args, kwargs), elapsed)
        self.db.update(self.name, which, self.key(*args, **kwargs), elapsed)
        #TODO: Should we use db.update instead of db.insert to avoid O(N) ops on already_run_variant_names = map(lambda x: x[1], already_run)?

        return ret_val

class HelperFunction(SpecializedFunction):
    """
    HelperFunction defines a SpecializedFunction that is not timed, and usually not called directly
    (although it can be).
    """
    def __init__(self, name, func, backend):
        self.name = name
        self.backend = backend
        self.variant_names, self.variant_funcs, self.run_check_funcs = [], [], []
        self.call_policy = None
        self.add_variant(name, func)


    def __call__(self, *args, **kwargs):
        if self.backend.dirty:
            self.backend.compile()
        return self.backend.get_compiled_function(self.name).__call__(*args, **kwargs)

class ASPBackend(object):
    """
    Class to encapsulate a backend for Asp.  A backend is the combination of a CodePy module
    (which contains the actual functions) and a CodePy compiler toolchain.
    """
    def __init__(self, module, toolchain, cache_dir, host_toolchain=None):
        self.module = module
        self.toolchain = toolchain
        self.host_toolchain = host_toolchain
        self.compiled_module = None
        self.cache_dir = cache_dir
        self.dirty = True
        self.compilable = True

    def compile(self):
        """
        Trigger a compile of this backend.  Note that CUDA needs to know about the C++
        backend as well.
        """
        if not self.compilable: return
        if isinstance(self.module, codepy.cuda.CudaModule):
            self.compiled_module = self.module.compile(self.host_toolchain,
                                                                        self.toolchain,
                                                                        debug=True, cache_dir=self.cache_dir)
        else:
            self.compiled_module = self.module.compile(self.toolchain,
                                                       debug=True, cache_dir=self.cache_dir)
        self.dirty = False

    def get_compiled_function(self, name):
        """
        Return a callable for a raw compiled function (that is, this must be a variant name rather than
        a function name).
        """
        try:
            func = getattr(self.compiled_module, name)
        except:
            raise AttributeError("Function %s not found in compiled module." % (name,))

        return func


class ASPModule(object):
    """
    ASPModule is the main coordination class for specializers.  A specializer creates an ASPModule to contain
    all of its specialized functions, and adds functions/libraries/etc to the ASPModule.

    ASPModule uses ASPBackend instances for each backend, ASPDB for its backing db for recording timing info,
    and instances of SpecializedFunction and HelperFunction for specialized and helper functions, respectively.
    """

    #FIXME: specializer should be required.
    def __init__(self, specializer="default_specializer", cache_dir=None, use_cuda=False, use_cilk=False, use_tbb=False, use_pthreads=False, use_scala=False):

        self.specialized_functions= {}
        self.helper_method_names = []

        self.db = ASPDB(specializer)
        
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            # create a per-user cache directory
            import tempfile, os
            if os.name == 'nt':
                username = os.environ['USERNAME']
            else:
                username = os.environ['LOGNAME']

            self.cache_dir = tempfile.gettempdir() + "/asp_cache_" + username
            if not os.access(self.cache_dir, os.F_OK):
                os.mkdir(self.cache_dir)

        self.backends = {}
        self.backends["c++"] = ASPBackend(codepy.bpl.BoostPythonModule(),
                                          codepy.toolchain.guess_toolchain(),
                                          self.cache_dir)
        if use_cuda:
            self.backends["cuda"] = ASPBackend(codepy.cuda.CudaModule(self.backends["c++"].module),
                                               codepy.toolchain.guess_nvcc_toolchain(),
                                               self.cache_dir,
                                               self.backends["c++"].toolchain)
            self.backends['cuda'].module.add_to_preamble([cpp_ast.Include('cuda.h', True)]) # codepy.CudaModule doesn't do this automatically for some reason
            self.backends['cuda'].module.add_to_preamble([cpp_ast.Include('cuda_runtime.h', True)]) # codepy.CudaModule doesn't do this automatically for some reason
            self.backends['c++'].module.add_to_preamble([cpp_ast.Include('cuda_runtime.h', True)]) # codepy.CudaModule doesn't do this automatically for some reason
            self.backends["cuda"].toolchain.cflags += ["-shared"]
        if use_cilk:
            self.backends["cilk"] = self.backends["c++"]
            self.backends["cilk"].toolchain.cc = "icc"
        if use_tbb:
            self.backends["tbb"] = self.backends["c++"]
            self.backends["tbb"].toolchain.cflags += ["-ltbb"]
        if use_pthreads:
            self.backends["pthreads"] = self.backends["c++"]
            self.backends["pthreads"].toolchain.cflags += ["-pthread"]	    
        if use_scala:
            self.backends["scala"] = ASPBackend(scala_module.ScalaModule(),
                                                scala_module.ScalaToolchain(),
                                                self.cache_dir)


    def add_library(self, feature, include_dirs, library_dirs=[], libraries=[], backend="c++"):
        self.backends[backend].toolchain.add_library(feature, include_dirs, library_dirs, libraries)
        
    def add_cuda_arch_spec(self, arch):
        archflag = '-arch='
        if 'sm_' not in arch: archflag += 'sm_' 
        archflag += arch
        self.backends["cuda"].toolchain.cflags += [archflag]

    def add_header(self, include_file, brackets=False, backend="c++"):
        """
        Add a header (e.g. #include "foo.h") to the module source file.
        With brackets=True, it will be C++-style #include <foo> instead.
        """
        self.backends[backend].module.add_to_preamble([cpp_ast.Include(include_file, brackets)])

    def add_to_preamble(self, pa, backend="c++"):
        if isinstance(pa, basestring):
            pa = [cpp_ast.Line(pa)]
        self.backends[backend].module.add_to_preamble(pa)

    def add_to_init(self, stmt, backend="c++"):
        if isinstance(stmt, str):
            stmt = [cpp_ast.Line(stmt)]
        if backend == "cuda":
            self.backends[backend].module.boost_module.add_to_init(stmt) #HACK because codepy's CudaModule doesn't have add_to_init()
        else:
            self.backends[backend].module.add_to_init(stmt)
        
    def add_to_module(self, block, backend="c++"):
        if isinstance(block, basestring):
            block = [cpp_ast.Line(block)]
        self.backends[backend].module.add_to_module(block)

    def add_function(self, fname, funcs, variant_names=[], run_check_funcs=[], key_function=None, 
                     backend="c++", call_policy=None):
        """
        Add a specialized function to the Asp module.  funcs can be a list of variants, but then
        variant_names is required (also a list).  Each item in funcs should be a string function or
        a cpp_ast FunctionDef.
        """
        if not isinstance(funcs, list):
            funcs = [funcs]
            variant_names = [fname]

        self.specialized_functions[fname] = SpecializedFunction(fname, self.backends[backend], self.db, variant_names,
                                                                variant_funcs=funcs, 
                                                                run_check_funcs=run_check_funcs,
                                                                key_function=key_function,
                                                                call_policy=call_policy)

    def add_helper_function(self, fname, func, backend="c++"):
        """
        Add a helper function, which is a specialized function that it not timed and has a single variant.
        """
        self.specialized_functions[fname] = HelperFunction(fname, func, self.backends[backend])


    def expose_class(self, classname, backend="c++"):
        """
        Expose a class or struct from C++ to Python, letting us pass instances back and forth
        between Python and C++.

        TODO: allow exposing *functions* within the class
        """
        self.backends[backend].module.add_to_init([cpp_ast.Line("boost::python::class_<%s>(\"%s\");\n" % (classname, classname))])


    def __getattr__(self, name):
        if name in self.specialized_functions:
            return self.specialized_functions[name]
        else:
            raise AttributeError("No method %s found; did you add it to this ASPModule?" % name)

    def generate(self):
        """
        Utility function for, during development, dumping out the generated
        source from all the underlying backends.
        """
        src = ""
        for x in self.backends.keys():
            src += "\nSource code for backend '" + x + "':\n" 
            src += str(self.backends[x].module.generate())

        return src


########NEW FILE########
__FILENAME__ = scala_module
import os
import os.path
import subprocess
from asp.avro_inter.py_avro_inter import *
import sys

class ScalaFunction:
    def __init__(self, classname, source_dir):
        self.classname = classname
        self.source_dir = source_dir                               
    
    def find_close(self,str):
        index = len(str)-1
        char = str[index]
        
        while (char!=']'):
            index -=1
            char = str[index]
        return index 

    def __call__(self, *args, **kwargs):
        write_avro_file(args, 'args.avro')
        prefix = os.environ['CLASSPATH']
        class_path = prefix +':'+self.source_dir + ':/root/asp/asp/avro_inter'
        
        # make_jar should be edited so that source.jar contains all the necessary files 
        # to be deployed to the slave nodes
        os.system('/root/asp/asp/jit/make_source_jar '+ self.source_dir)     
        os.environ['SOURCE_LOC'] = self.source_dir + "/source.jar"
        out = subprocess.Popen('/root/spark/run -cp '+class_path + ' ' +self.classname, shell=True)
        out.wait()
        if out.returncode != 0:
            print "return code is:" , out.returncode
            raise Exception("Bad return code")

        results = read_avro_file('results.avro')[0]        
        os.remove('args.avro')
        os.remove('results.avro')
        return results



class PseudoModule:
    '''Pretends to be a Python module that contains the generated functions.'''
    def __init__(self):
        self.__dict__["__special_functions"] = {}

    def __getattr__(self, name):
        if name in self.__dict__["__special_functions"].keys():
            return self.__dict__["__special_functions"][name]
        else:
            raise Error

    def __setattr__(self, name, value):
        self.__dict__["__special_functions"][name] = value

class ScalaModule:
    def __init__(self):
        self.mod_body = []
        self.init_body = []

    def add_to_init(self, body):
        self.init_body.extend([body])

    def add_function(self):
        # This is only for already compiled functions, I think
        pass

    def add_to_module(self, body):
        self.mod_body.extend(body)

    def add_to_preamble(self):
        pass

    def generate(self):
        s = ""
        for line in self.mod_body:
            if type(line) != str:
                raise Error("Not a string")
            s += line
        return s

    def compile(self, toolchain, debug=True, cache_dir=None):
        if cache_dir is None:
            import tempfile
            cache_dir = tempfile.gettempdir()
        else: 
            if not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)
        

        source_string = self.generate()
        hex_checksum = self.calculate_hex_checksum(source_string)
        mod_cache_dir = os.path.join(cache_dir, hex_checksum)
        # Should we assume that if the directory exists, then we don't need to
        # recompile?
        if not os.path.isdir(mod_cache_dir):
            os.makedirs(mod_cache_dir)
            filepath = os.path.join(mod_cache_dir, "asp_tmp.scala")
            source = open(filepath, 'w')
            source.write(source_string)
            source.close()            
            result = os.system("scalac -d %s %s" % (mod_cache_dir, filepath))                
            os.remove(filepath)
            if result != 0:
                os.system("rm -rf " +  mod_cache_dir)
                raise Exception("Could not compile")
               
        mod = PseudoModule()
        for fname in self.init_body:
            self.func = ScalaFunction(fname, mod_cache_dir)
            setattr(mod, fname, self.func)
        return mod

    # Method borrowed from codepy.jit
    def calculate_hex_checksum(self, source_string):
        try:
            import hashlib
            checksum = hashlib.md5()
        except ImportError:
            # for Python << 2.5
            import md5
            checksum = md5.new()

        checksum.update(source_string)
        #checksum.update(str(toolchain.abi_id()))
        return checksum.hexdigest()


class ScalaToolchain:
    pass

########NEW FILE########
__FILENAME__ = variant_history

class CodeVariantPerformanceDatabase(object):
    def __init__(self):
        self.variant_times = {}    
           # The measured performance data for a particular method
           # Dict of dicts, key: input key, value: dict  
           # Inner dict of times, key: v_id, value: time 
           # The set of v_ids contained in the dict may be 
           # much larger than the set of v_ids compiled by
           # a particular instance of a specializer
        self.oracular_best = {} 
           # The variant id of the best variant out of all 
           # currently compiled variants of a particular method
           # Dict of v_ids, key: input key, value: v_id or False

    def set_oracular_best(self, key, time_dict, v_id_set):
        # filter entries that failed to run or are not currently compiled
        succeeded = filter( lambda x: x[1] > 0 and x[0] in v_id_set, \
                            time_dict.iteritems() ) 
        if not succeeded: 
            print "Warning: ASP has tried every currently compiled variant for this input and none have run successfully. Add different variants."
            self.oracular_best[key] = False
        else: 
            name = min(succeeded, key=lambda p: p[1])[0] # key with min val
            self.oracular_best[key] = name

    def get_oracular_best(self, key):
        return self.oracular_best.get(key, False)

    def clear_oracle(self):
        self.oracular_best.clear() #newly added variant might be the best

    def add_time(self, key, elapsed, v_id, v_id_set):
        time_dict = self.variant_times.get(key,{})
        # TODO: Overwrite old times with new data? If so, reset best when?
        if v_id not in time_dict:
            time_dict[v_id] = elapsed
            if set(time_dict.keys()) >= v_id_set:
                self.set_oracular_best(key, time_dict, v_id_set)
            self.variant_times[key] = time_dict

    def get_measured_v_ids(self, key):
        return self.variant_times.get(key,{}).keys()

    def clear(self):
        self.variant_times.clear()
        self.oracular_best.clear()

    def get_picklable_obj(self):
        return { 'variant_times': self.variant_times }

    def set_from_pickled_obj(self, obj, v_id_set):
        self.variant_times = obj['variant_times']
        for k, time_dict in self.variant_times.iteritems():
            if set(time_dict.keys()) >= v_id_set:
                self.set_oracular_best(k, time_dict, v_id_set)


class CodeVariantUseCaseLimiter(object):
    def __init__(self):
        self.compilable = {} 
            # Track whether or not a variant is compilable on this machine
            # Dict of bools, key: v_id, val: bool
        self.input_limits_funcs = {} 
            # Return a function determining if a particular input is 
            # runnable with a particular variant
            # Dict of closures, key: v_id, val: closure returning bool 

    def is_allowed(self, v_id, *args, **kwargs):
        return self.compilable[v_id] and  \
               self.input_limits_funcs[v_id](*args, **kwargs)

    def append(self, v_id_list, limit_funcs, compilables):
        for v, lim, c in zip(v_id_list, limit_funcs, compilables):
            self.input_limits_funcs[v] = lim
            self.compilable[v] = c


class CodeVariantSelector(object):
    def __init__(self, perf_database, use_case_limiter):
        self.perf_database = perf_database
        self.use_case_limiter = use_case_limiter

    def get_v_id_to_run(self, v_id_set, key, *args, **kwargs):

        def exhaustive_search():
            candidates = v_id_set - set(self.perf_database.get_measured_v_ids(key))
            while candidates:
                v_id = candidates.pop()
                if self.use_case_limiter.is_allowed(v_id, *args, **kwargs):
                    return v_id
                self.perf_database.add_time(key, -1., v_id, v_id_set)
            return None

        best = self.perf_database.get_oracular_best(key)
        return best if best else exhaustive_search()
        return ret_func or error_func

    def use_supplied_function_to_generate_a_new_variant():
        pass

class CodeVariants(object):
    def __init__(self, variant_names, key_func, param_names):
        self.v_id_list = variant_names
        self.v_id_set = set(variant_names)
        self.make_key = key_func     
        self.param_names = param_names
        self.database = CodeVariantPerformanceDatabase()
        self.limiter = CodeVariantUseCaseLimiter()
        self.selector = CodeVariantSelector(self.database, self.limiter)

    def __contains__(self, v_id):
        return v_id in self.v_id_list

    def append(self, variant_names):
        self.v_id_list.extend(variant_names)
        self.v_id_set.update(variant_names)

    def get_picklable_obj(self):
        return {
                'variant_names': self.v_id_list,
                'param_names': self.param_names,
               }

    def set_from_pickled_obj(self, obj):
        if self.v_id_list != obj['variant_names']:
            print "Warning: Attempted to load pickled performance data for non-matching space of code variants."
            return
        self.param_names = obj['param_names']


########NEW FILE########
__FILENAME__ = cpp
# -----------------------------------------------------------------------------
# cpp.py
#
# Author:  David Beazley (http://www.dabeaz.com)
# Copyright (C) 2007
# All rights reserved
#
# This module implements an ANSI-C style lexical preprocessor for PLY. 
# -----------------------------------------------------------------------------
from __future__ import generators

# -----------------------------------------------------------------------------
# Default preprocessor lexer definitions.   These tokens are enough to get
# a basic preprocessor working.   Other modules may import these if they want
# -----------------------------------------------------------------------------

tokens = (
   'CPP_ID','CPP_INTEGER', 'CPP_FLOAT', 'CPP_STRING', 'CPP_CHAR', 'CPP_WS', 'CPP_COMMENT', 'CPP_POUND','CPP_DPOUND'
)

literals = "+-*/%|&~^<>=!?()[]{}.,;:\\\'\""

# Whitespace
def t_CPP_WS(t):
    r'\s+'
    t.lexer.lineno += t.value.count("\n")
    return t

t_CPP_POUND = r'\#'
t_CPP_DPOUND = r'\#\#'

# Identifier
t_CPP_ID = r'[A-Za-z_][\w_]*'

# Integer literal
def CPP_INTEGER(t):
    r'(((((0x)|(0X))[0-9a-fA-F]+)|(\d+))([uU]|[lL]|[uU][lL]|[lL][uU])?)'
    return t

t_CPP_INTEGER = CPP_INTEGER

# Floating literal
t_CPP_FLOAT = r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'

# String literal
def t_CPP_STRING(t):
    r'\"([^\\\n]|(\\(.|\n)))*?\"'
    t.lexer.lineno += t.value.count("\n")
    return t

# Character constant 'c' or L'c'
def t_CPP_CHAR(t):
    r'(L)?\'([^\\\n]|(\\(.|\n)))*?\''
    t.lexer.lineno += t.value.count("\n")
    return t

# Comment
def t_CPP_COMMENT(t):
    r'(/\*(.|\n)*?\*/)|(//.*?\n)'
    t.lexer.lineno += t.value.count("\n")
    return t
    
def t_error(t):
    t.type = t.value[0]
    t.value = t.value[0]
    t.lexer.skip(1)
    return t

import re
import copy
import time
import os.path

# -----------------------------------------------------------------------------
# trigraph()
# 
# Given an input string, this function replaces all trigraph sequences. 
# The following mapping is used:
#
#     ??=    #
#     ??/    \
#     ??'    ^
#     ??(    [
#     ??)    ]
#     ??!    |
#     ??<    {
#     ??>    }
#     ??-    ~
# -----------------------------------------------------------------------------

_trigraph_pat = re.compile(r'''\?\?[=/\'\(\)\!<>\-]''')
_trigraph_rep = {
    '=':'#',
    '/':'\\',
    "'":'^',
    '(':'[',
    ')':']',
    '!':'|',
    '<':'{',
    '>':'}',
    '-':'~'
}

def trigraph(input):
    return _trigraph_pat.sub(lambda g: _trigraph_rep[g.group()[-1]],input)

# ------------------------------------------------------------------
# Macro object
#
# This object holds information about preprocessor macros
#
#    .name      - Macro name (string)
#    .value     - Macro value (a list of tokens)
#    .arglist   - List of argument names
#    .variadic  - Boolean indicating whether or not variadic macro
#    .vararg    - Name of the variadic parameter
#
# When a macro is created, the macro replacement token sequence is
# pre-scanned and used to create patch lists that are later used
# during macro expansion
# ------------------------------------------------------------------

class Macro(object):
    def __init__(self,name,value,arglist=None,variadic=False):
        self.name = name
        self.value = value
        self.arglist = arglist
        self.variadic = variadic
        if variadic:
            self.vararg = arglist[-1]
        self.source = None

# ------------------------------------------------------------------
# Preprocessor object
#
# Object representing a preprocessor.  Contains macro definitions,
# include directories, and other information
# ------------------------------------------------------------------

class Preprocessor(object):
    def __init__(self,lexer=None):
        if lexer is None:
            lexer = lex.lexer
        self.lexer = lexer
        self.macros = { }
        self.path = []
        self.temp_path = []

        # Probe the lexer for selected tokens
        self.lexprobe()

        tm = time.localtime()
        self.define("__DATE__ \"%s\"" % time.strftime("%b %d %Y",tm))
        self.define("__TIME__ \"%s\"" % time.strftime("%H:%M:%S",tm))
        self.parser = None

    # -----------------------------------------------------------------------------
    # tokenize()
    #
    # Utility function. Given a string of text, tokenize into a list of tokens
    # -----------------------------------------------------------------------------

    def tokenize(self,text):
        tokens = []
        self.lexer.input(text)
        while True:
            tok = self.lexer.token()
            if not tok: break
            tokens.append(tok)
        return tokens

    # ---------------------------------------------------------------------
    # error()
    #
    # Report a preprocessor error/warning of some kind
    # ----------------------------------------------------------------------

    def error(self,file,line,msg):
        print("%s:%d %s" % (file,line,msg))

    # ----------------------------------------------------------------------
    # lexprobe()
    #
    # This method probes the preprocessor lexer object to discover
    # the token types of symbols that are important to the preprocessor.
    # If this works right, the preprocessor will simply "work"
    # with any suitable lexer regardless of how tokens have been named.
    # ----------------------------------------------------------------------

    def lexprobe(self):

        # Determine the token type for identifiers
        self.lexer.input("identifier")
        tok = self.lexer.token()
        if not tok or tok.value != "identifier":
            print("Couldn't determine identifier type")
        else:
            self.t_ID = tok.type

        # Determine the token type for integers
        self.lexer.input("12345")
        tok = self.lexer.token()
        if not tok or int(tok.value) != 12345:
            print("Couldn't determine integer type")
        else:
            self.t_INTEGER = tok.type
            self.t_INTEGER_TYPE = type(tok.value)

        # Determine the token type for strings enclosed in double quotes
        self.lexer.input("\"filename\"")
        tok = self.lexer.token()
        if not tok or tok.value != "\"filename\"":
            print("Couldn't determine string type")
        else:
            self.t_STRING = tok.type

        # Determine the token type for whitespace--if any
        self.lexer.input("  ")
        tok = self.lexer.token()
        if not tok or tok.value != "  ":
            self.t_SPACE = None
        else:
            self.t_SPACE = tok.type

        # Determine the token type for newlines
        self.lexer.input("\n")
        tok = self.lexer.token()
        if not tok or tok.value != "\n":
            self.t_NEWLINE = None
            print("Couldn't determine token for newlines")
        else:
            self.t_NEWLINE = tok.type

        self.t_WS = (self.t_SPACE, self.t_NEWLINE)

        # Check for other characters used by the preprocessor
        chars = [ '<','>','#','##','\\','(',')',',','.']
        for c in chars:
            self.lexer.input(c)
            tok = self.lexer.token()
            if not tok or tok.value != c:
                print("Unable to lex '%s' required for preprocessor" % c)

    # ----------------------------------------------------------------------
    # add_path()
    #
    # Adds a search path to the preprocessor.  
    # ----------------------------------------------------------------------

    def add_path(self,path):
        self.path.append(path)

    # ----------------------------------------------------------------------
    # group_lines()
    #
    # Given an input string, this function splits it into lines.  Trailing whitespace
    # is removed.   Any line ending with \ is grouped with the next line.  This
    # function forms the lowest level of the preprocessor---grouping into text into
    # a line-by-line format.
    # ----------------------------------------------------------------------

    def group_lines(self,input):
        lex = self.lexer.clone()
        lines = [x.rstrip() for x in input.splitlines()]
        for i in xrange(len(lines)):
            j = i+1
            while lines[i].endswith('\\') and (j < len(lines)):
                lines[i] = lines[i][:-1]+lines[j]
                lines[j] = ""
                j += 1

        input = "\n".join(lines)
        lex.input(input)
        lex.lineno = 1

        current_line = []
        while True:
            tok = lex.token()
            if not tok:
                break
            current_line.append(tok)
            if tok.type in self.t_WS and '\n' in tok.value:
                yield current_line
                current_line = []

        if current_line:
            yield current_line

    # ----------------------------------------------------------------------
    # tokenstrip()
    # 
    # Remove leading/trailing whitespace tokens from a token list
    # ----------------------------------------------------------------------

    def tokenstrip(self,tokens):
        i = 0
        while i < len(tokens) and tokens[i].type in self.t_WS:
            i += 1
        del tokens[:i]
        i = len(tokens)-1
        while i >= 0 and tokens[i].type in self.t_WS:
            i -= 1
        del tokens[i+1:]
        return tokens


    # ----------------------------------------------------------------------
    # collect_args()
    #
    # Collects comma separated arguments from a list of tokens.   The arguments
    # must be enclosed in parenthesis.  Returns a tuple (tokencount,args,positions)
    # where tokencount is the number of tokens consumed, args is a list of arguments,
    # and positions is a list of integers containing the starting index of each
    # argument.  Each argument is represented by a list of tokens.
    #
    # When collecting arguments, leading and trailing whitespace is removed
    # from each argument.  
    #
    # This function properly handles nested parenthesis and commas---these do not
    # define new arguments.
    # ----------------------------------------------------------------------

    def collect_args(self,tokenlist):
        args = []
        positions = []
        current_arg = []
        nesting = 1
        tokenlen = len(tokenlist)
    
        # Search for the opening '('.
        i = 0
        while (i < tokenlen) and (tokenlist[i].type in self.t_WS):
            i += 1

        if (i < tokenlen) and (tokenlist[i].value == '('):
            positions.append(i+1)
        else:
            self.error(self.source,tokenlist[0].lineno,"Missing '(' in macro arguments")
            return 0, [], []

        i += 1

        while i < tokenlen:
            t = tokenlist[i]
            if t.value == '(':
                current_arg.append(t)
                nesting += 1
            elif t.value == ')':
                nesting -= 1
                if nesting == 0:
                    if current_arg:
                        args.append(self.tokenstrip(current_arg))
                        positions.append(i)
                    return i+1,args,positions
                current_arg.append(t)
            elif t.value == ',' and nesting == 1:
                args.append(self.tokenstrip(current_arg))
                positions.append(i+1)
                current_arg = []
            else:
                current_arg.append(t)
            i += 1
    
        # Missing end argument
        self.error(self.source,tokenlist[-1].lineno,"Missing ')' in macro arguments")
        return 0, [],[]

    # ----------------------------------------------------------------------
    # macro_prescan()
    #
    # Examine the macro value (token sequence) and identify patch points
    # This is used to speed up macro expansion later on---we'll know
    # right away where to apply patches to the value to form the expansion
    # ----------------------------------------------------------------------
    
    def macro_prescan(self,macro):
        macro.patch     = []             # Standard macro arguments 
        macro.str_patch = []             # String conversion expansion
        macro.var_comma_patch = []       # Variadic macro comma patch
        i = 0
        while i < len(macro.value):
            if macro.value[i].type == self.t_ID and macro.value[i].value in macro.arglist:
                argnum = macro.arglist.index(macro.value[i].value)
                # Conversion of argument to a string
                if i > 0 and macro.value[i-1].value == '#':
                    macro.value[i] = copy.copy(macro.value[i])
                    macro.value[i].type = self.t_STRING
                    del macro.value[i-1]
                    macro.str_patch.append((argnum,i-1))
                    continue
                # Concatenation
                elif (i > 0 and macro.value[i-1].value == '##'):
                    macro.patch.append(('c',argnum,i-1))
                    del macro.value[i-1]
                    continue
                elif ((i+1) < len(macro.value) and macro.value[i+1].value == '##'):
                    macro.patch.append(('c',argnum,i))
                    i += 1
                    continue
                # Standard expansion
                else:
                    macro.patch.append(('e',argnum,i))
            elif macro.value[i].value == '##':
                if macro.variadic and (i > 0) and (macro.value[i-1].value == ',') and \
                        ((i+1) < len(macro.value)) and (macro.value[i+1].type == self.t_ID) and \
                        (macro.value[i+1].value == macro.vararg):
                    macro.var_comma_patch.append(i-1)
            i += 1
        macro.patch.sort(key=lambda x: x[2],reverse=True)

    # ----------------------------------------------------------------------
    # macro_expand_args()
    #
    # Given a Macro and list of arguments (each a token list), this method
    # returns an expanded version of a macro.  The return value is a token sequence
    # representing the replacement macro tokens
    # ----------------------------------------------------------------------

    def macro_expand_args(self,macro,args):
        # Make a copy of the macro token sequence
        rep = [copy.copy(_x) for _x in macro.value]

        # Make string expansion patches.  These do not alter the length of the replacement sequence
        
        str_expansion = {}
        for argnum, i in macro.str_patch:
            if argnum not in str_expansion:
                str_expansion[argnum] = ('"%s"' % "".join([x.value for x in args[argnum]])).replace("\\","\\\\")
            rep[i] = copy.copy(rep[i])
            rep[i].value = str_expansion[argnum]

        # Make the variadic macro comma patch.  If the variadic macro argument is empty, we get rid
        comma_patch = False
        if macro.variadic and not args[-1]:
            for i in macro.var_comma_patch:
                rep[i] = None
                comma_patch = True

        # Make all other patches.   The order of these matters.  It is assumed that the patch list
        # has been sorted in reverse order of patch location since replacements will cause the
        # size of the replacement sequence to expand from the patch point.
        
        expanded = { }
        for ptype, argnum, i in macro.patch:
            # Concatenation.   Argument is left unexpanded
            if ptype == 'c':
                rep[i:i+1] = args[argnum]
            # Normal expansion.  Argument is macro expanded first
            elif ptype == 'e':
                if argnum not in expanded:
                    expanded[argnum] = self.expand_macros(args[argnum])
                rep[i:i+1] = expanded[argnum]

        # Get rid of removed comma if necessary
        if comma_patch:
            rep = [_i for _i in rep if _i]

        return rep


    # ----------------------------------------------------------------------
    # expand_macros()
    #
    # Given a list of tokens, this function performs macro expansion.
    # The expanded argument is a dictionary that contains macros already
    # expanded.  This is used to prevent infinite recursion.
    # ----------------------------------------------------------------------

    def expand_macros(self,tokens,expanded=None):
        if expanded is None:
            expanded = {}
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.type == self.t_ID:
                if t.value in self.macros and t.value not in expanded:
                    # Yes, we found a macro match
                    expanded[t.value] = True
                    
                    m = self.macros[t.value]
                    if not m.arglist:
                        # A simple macro
                        ex = self.expand_macros([copy.copy(_x) for _x in m.value],expanded)
                        for e in ex:
                            e.lineno = t.lineno
                        tokens[i:i+1] = ex
                        i += len(ex)
                    else:
                        # A macro with arguments
                        j = i + 1
                        while j < len(tokens) and tokens[j].type in self.t_WS:
                            j += 1
                        if tokens[j].value == '(':
                            tokcount,args,positions = self.collect_args(tokens[j:])
                            if not m.variadic and len(args) !=  len(m.arglist):
                                self.error(self.source,t.lineno,"Macro %s requires %d arguments" % (t.value,len(m.arglist)))
                                i = j + tokcount
                            elif m.variadic and len(args) < len(m.arglist)-1:
                                if len(m.arglist) > 2:
                                    self.error(self.source,t.lineno,"Macro %s must have at least %d arguments" % (t.value, len(m.arglist)-1))
                                else:
                                    self.error(self.source,t.lineno,"Macro %s must have at least %d argument" % (t.value, len(m.arglist)-1))
                                i = j + tokcount
                            else:
                                if m.variadic:
                                    if len(args) == len(m.arglist)-1:
                                        args.append([])
                                    else:
                                        args[len(m.arglist)-1] = tokens[j+positions[len(m.arglist)-1]:j+tokcount-1]
                                        del args[len(m.arglist):]
                                        
                                # Get macro replacement text
                                rep = self.macro_expand_args(m,args)
                                rep = self.expand_macros(rep,expanded)
                                for r in rep:
                                    r.lineno = t.lineno
                                tokens[i:j+tokcount] = rep
                                i += len(rep)
                    del expanded[t.value]
                    continue
                elif t.value == '__LINE__':
                    t.type = self.t_INTEGER
                    t.value = self.t_INTEGER_TYPE(t.lineno)
                
            i += 1
        return tokens

    # ----------------------------------------------------------------------    
    # evalexpr()
    # 
    # Evaluate an expression token sequence for the purposes of evaluating
    # integral expressions.
    # ----------------------------------------------------------------------

    def evalexpr(self,tokens):
        # tokens = tokenize(line)
        # Search for defined macros
        i = 0
        while i < len(tokens):
            if tokens[i].type == self.t_ID and tokens[i].value == 'defined':
                j = i + 1
                needparen = False
                result = "0L"
                while j < len(tokens):
                    if tokens[j].type in self.t_WS:
                        j += 1
                        continue
                    elif tokens[j].type == self.t_ID:
                        if tokens[j].value in self.macros:
                            result = "1L"
                        else:
                            result = "0L"
                        if not needparen: break
                    elif tokens[j].value == '(':
                        needparen = True
                    elif tokens[j].value == ')':
                        break
                    else:
                        self.error(self.source,tokens[i].lineno,"Malformed defined()")
                    j += 1
                tokens[i].type = self.t_INTEGER
                tokens[i].value = self.t_INTEGER_TYPE(result)
                del tokens[i+1:j+1]
            i += 1
        tokens = self.expand_macros(tokens)
        for i,t in enumerate(tokens):
            if t.type == self.t_ID:
                tokens[i] = copy.copy(t)
                tokens[i].type = self.t_INTEGER
                tokens[i].value = self.t_INTEGER_TYPE("0L")
            elif t.type == self.t_INTEGER:
                tokens[i] = copy.copy(t)
                # Strip off any trailing suffixes
                tokens[i].value = str(tokens[i].value)
                while tokens[i].value[-1] not in "0123456789abcdefABCDEF":
                    tokens[i].value = tokens[i].value[:-1]
        
        expr = "".join([str(x.value) for x in tokens])
        expr = expr.replace("&&"," and ")
        expr = expr.replace("||"," or ")
        expr = expr.replace("!"," not ")
        try:
            result = eval(expr)
        except StandardError:
            self.error(self.source,tokens[0].lineno,"Couldn't evaluate expression")
            result = 0
        return result

    # ----------------------------------------------------------------------
    # parsegen()
    #
    # Parse an input string/
    # ----------------------------------------------------------------------
    def parsegen(self,input,source=None):

        # Replace trigraph sequences
        t = trigraph(input)
        lines = self.group_lines(t)

        if not source:
            source = ""
            
        self.define("__FILE__ \"%s\"" % source)

        self.source = source
        chunk = []
        enable = True
        iftrigger = False
        ifstack = []

        for x in lines:
            for i,tok in enumerate(x):
                if tok.type not in self.t_WS: break
            if tok.value == '#':
                # Preprocessor directive

                for tok in x:
                    if tok in self.t_WS and '\n' in tok.value:
                        chunk.append(tok)
                
                dirtokens = self.tokenstrip(x[i+1:])
                if dirtokens:
                    name = dirtokens[0].value
                    args = self.tokenstrip(dirtokens[1:])
                else:
                    name = ""
                    args = []
                
                if name == 'define':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        self.define(args)
                elif name == 'include':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        oldfile = self.macros['__FILE__']
                        for tok in self.include(args):
                            yield tok
                        self.macros['__FILE__'] = oldfile
                        self.source = source
                elif name == 'undef':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        self.undef(args)
                elif name == 'ifdef':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        if not args[0].value in self.macros:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'ifndef':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        if args[0].value in self.macros:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'if':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        result = self.evalexpr(args)
                        if not result:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'elif':
                    if ifstack:
                        if ifstack[-1][0]:     # We only pay attention if outer "if" allows this
                            if enable:         # If already true, we flip enable False
                                enable = False
                            elif not iftrigger:   # If False, but not triggered yet, we'll check expression
                                result = self.evalexpr(args)
                                if result:
                                    enable  = True
                                    iftrigger = True
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #elif")
                        
                elif name == 'else':
                    if ifstack:
                        if ifstack[-1][0]:
                            if enable:
                                enable = False
                            elif not iftrigger:
                                enable = True
                                iftrigger = True
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #else")

                elif name == 'endif':
                    if ifstack:
                        enable,iftrigger = ifstack.pop()
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #endif")
                else:
                    # Unknown preprocessor directive
                    pass

            else:
                # Normal text
                if enable:
                    chunk.extend(x)

        for tok in self.expand_macros(chunk):
            yield tok
        chunk = []

    # ----------------------------------------------------------------------
    # include()
    #
    # Implementation of file-inclusion
    # ----------------------------------------------------------------------

    def include(self,tokens):
        # Try to extract the filename and then process an include file
        if not tokens:
            return
        if tokens:
            if tokens[0].value != '<' and tokens[0].type != self.t_STRING:
                tokens = self.expand_macros(tokens)

            if tokens[0].value == '<':
                # Include <...>
                i = 1
                while i < len(tokens):
                    if tokens[i].value == '>':
                        break
                    i += 1
                else:
                    print("Malformed #include <...>")
                    return
                filename = "".join([x.value for x in tokens[1:i]])
                path = self.path + [""] + self.temp_path
            elif tokens[0].type == self.t_STRING:
                filename = tokens[0].value[1:-1]
                path = self.temp_path + [""] + self.path
            else:
                print("Malformed #include statement")
                return
        for p in path:
            iname = os.path.join(p,filename)
            try:
                data = open(iname,"r").read()
                dname = os.path.dirname(iname)
                if dname:
                    self.temp_path.insert(0,dname)
                for tok in self.parsegen(data,filename):
                    yield tok
                if dname:
                    del self.temp_path[0]
                break
            except IOError:
                pass
        else:
            print("Couldn't find '%s'" % filename)

    # ----------------------------------------------------------------------
    # define()
    #
    # Define a new macro
    # ----------------------------------------------------------------------

    def define(self,tokens):
        if isinstance(tokens,(str,unicode)):
            tokens = self.tokenize(tokens)

        linetok = tokens
        try:
            name = linetok[0]
            if len(linetok) > 1:
                mtype = linetok[1]
            else:
                mtype = None
            if not mtype:
                m = Macro(name.value,[])
                self.macros[name.value] = m
            elif mtype.type in self.t_WS:
                # A normal macro
                m = Macro(name.value,self.tokenstrip(linetok[2:]))
                self.macros[name.value] = m
            elif mtype.value == '(':
                # A macro with arguments
                tokcount, args, positions = self.collect_args(linetok[1:])
                variadic = False
                for a in args:
                    if variadic:
                        print("No more arguments may follow a variadic argument")
                        break
                    astr = "".join([str(_i.value) for _i in a])
                    if astr == "...":
                        variadic = True
                        a[0].type = self.t_ID
                        a[0].value = '__VA_ARGS__'
                        variadic = True
                        del a[1:]
                        continue
                    elif astr[-3:] == "..." and a[0].type == self.t_ID:
                        variadic = True
                        del a[1:]
                        # If, for some reason, "." is part of the identifier, strip off the name for the purposes
                        # of macro expansion
                        if a[0].value[-3:] == '...':
                            a[0].value = a[0].value[:-3]
                        continue
                    if len(a) > 1 or a[0].type != self.t_ID:
                        print("Invalid macro argument")
                        break
                else:
                    mvalue = self.tokenstrip(linetok[1+tokcount:])
                    i = 0
                    while i < len(mvalue):
                        if i+1 < len(mvalue):
                            if mvalue[i].type in self.t_WS and mvalue[i+1].value == '##':
                                del mvalue[i]
                                continue
                            elif mvalue[i].value == '##' and mvalue[i+1].type in self.t_WS:
                                del mvalue[i+1]
                        i += 1
                    m = Macro(name.value,mvalue,[x[0].value for x in args],variadic)
                    self.macro_prescan(m)
                    self.macros[name.value] = m
            else:
                print("Bad macro definition")
        except LookupError:
            print("Bad macro definition")

    # ----------------------------------------------------------------------
    # undef()
    #
    # Undefine a macro
    # ----------------------------------------------------------------------

    def undef(self,tokens):
        id = tokens[0].value
        try:
            del self.macros[id]
        except LookupError:
            pass

    # ----------------------------------------------------------------------
    # parse()
    #
    # Parse input text.
    # ----------------------------------------------------------------------
    def parse(self,input,source=None,ignore={}):
        self.ignore = ignore
        self.parser = self.parsegen(input,source)
        
    # ----------------------------------------------------------------------
    # token()
    #
    # Method to return individual tokens
    # ----------------------------------------------------------------------
    def token(self):
        try:
            while True:
                tok = next(self.parser)
                if tok.type not in self.ignore: return tok
        except StopIteration:
            self.parser = None
            return None

if __name__ == '__main__':
    import ply.lex as lex
    lexer = lex.lex()

    # Run a preprocessor
    import sys
    f = open(sys.argv[1])
    input = f.read()

    p = Preprocessor(lexer)
    p.parse(input,sys.argv[1])
    while True:
        tok = p.token()
        if not tok: break
        print(p.source, tok)




    







########NEW FILE########
__FILENAME__ = ctokens
# ----------------------------------------------------------------------
# ctokens.py
#
# Token specifications for symbols in ANSI C and C++.  This file is
# meant to be used as a library in other tokenizers.
# ----------------------------------------------------------------------

# Reserved words

tokens = [
    # Literals (identifier, integer constant, float constant, string constant, char const)
    'ID', 'TYPEID', 'ICONST', 'FCONST', 'SCONST', 'CCONST',

    # Operators (+,-,*,/,%,|,&,~,^,<<,>>, ||, &&, !, <, <=, >, >=, ==, !=)
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'OR', 'AND', 'NOT', 'XOR', 'LSHIFT', 'RSHIFT',
    'LOR', 'LAND', 'LNOT',
    'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',
    
    # Assignment (=, *=, /=, %=, +=, -=, <<=, >>=, &=, ^=, |=)
    'EQUALS', 'TIMESEQUAL', 'DIVEQUAL', 'MODEQUAL', 'PLUSEQUAL', 'MINUSEQUAL',
    'LSHIFTEQUAL','RSHIFTEQUAL', 'ANDEQUAL', 'XOREQUAL', 'OREQUAL',

    # Increment/decrement (++,--)
    'PLUSPLUS', 'MINUSMINUS',

    # Structure dereference (->)
    'ARROW',

    # Ternary operator (?)
    'TERNARY',
    
    # Delimeters ( ) [ ] { } , . ; :
    'LPAREN', 'RPAREN',
    'LBRACKET', 'RBRACKET',
    'LBRACE', 'RBRACE',
    'COMMA', 'PERIOD', 'SEMI', 'COLON',

    # Ellipsis (...)
    'ELLIPSIS',
]
    
# Operators
t_PLUS             = r'\+'
t_MINUS            = r'-'
t_TIMES            = r'\*'
t_DIVIDE           = r'/'
t_MODULO           = r'%'
t_OR               = r'\|'
t_AND              = r'&'
t_NOT              = r'~'
t_XOR              = r'\^'
t_LSHIFT           = r'<<'
t_RSHIFT           = r'>>'
t_LOR              = r'\|\|'
t_LAND             = r'&&'
t_LNOT             = r'!'
t_LT               = r'<'
t_GT               = r'>'
t_LE               = r'<='
t_GE               = r'>='
t_EQ               = r'=='
t_NE               = r'!='

# Assignment operators

t_EQUALS           = r'='
t_TIMESEQUAL       = r'\*='
t_DIVEQUAL         = r'/='
t_MODEQUAL         = r'%='
t_PLUSEQUAL        = r'\+='
t_MINUSEQUAL       = r'-='
t_LSHIFTEQUAL      = r'<<='
t_RSHIFTEQUAL      = r'>>='
t_ANDEQUAL         = r'&='
t_OREQUAL          = r'\|='
t_XOREQUAL         = r'^='

# Increment/decrement
t_INCREMENT        = r'\+\+'
t_DECREMENT        = r'--'

# ->
t_ARROW            = r'->'

# ?
t_TERNARY          = r'\?'

# Delimeters
t_LPAREN           = r'\('
t_RPAREN           = r'\)'
t_LBRACKET         = r'\['
t_RBRACKET         = r'\]'
t_LBRACE           = r'\{'
t_RBRACE           = r'\}'
t_COMMA            = r','
t_PERIOD           = r'\.'
t_SEMI             = r';'
t_COLON            = r':'
t_ELLIPSIS         = r'\.\.\.'

# Identifiers
t_ID = r'[A-Za-z_][A-Za-z0-9_]*'

# Integer literal
t_INTEGER = r'\d+([uU]|[lL]|[uU][lL]|[lL][uU])?'

# Floating literal
t_FLOAT = r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'

# String literal
t_STRING = r'\"([^\\\n]|(\\.))*?\"'

# Character constant 'c' or L'c'
t_CHARACTER = r'(L)?\'([^\\\n]|(\\.))*?\''

# Comment (C-Style)
def t_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')
    return t

# Comment (C++-Style)
def t_CPPCOMMENT(t):
    r'//.*\n'
    t.lexer.lineno += 1
    return t


    




########NEW FILE########
__FILENAME__ = lex
# -----------------------------------------------------------------------------
# ply: lex.py
#
# Copyright (C) 2001-2011,
# David M. Beazley (Dabeaz LLC)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.  
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.  
# * Neither the name of the David Beazley or Dabeaz LLC may be used to
#   endorse or promote products derived from this software without
#  specific prior written permission. 
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------

__version__    = "3.4"
__tabversion__ = "3.2"       # Version of table file used

import re, sys, types, copy, os

# This tuple contains known string types
try:
    # Python 2.6
    StringTypes = (types.StringType, types.UnicodeType)
except AttributeError:
    # Python 3.0
    StringTypes = (str, bytes)

# Extract the code attribute of a function. Different implementations
# are for Python 2/3 compatibility.

if sys.version_info[0] < 3:
    def func_code(f):
        return f.func_code
else:
    def func_code(f):
        return f.__code__

# This regular expression is used to match valid token names
_is_identifier = re.compile(r'^[a-zA-Z0-9_]+$')

# Exception thrown when invalid token encountered and no default error
# handler is defined.

class LexError(Exception):
    def __init__(self,message,s):
         self.args = (message,)
         self.text = s

# Token class.  This class is used to represent the tokens produced.
class LexToken(object):
    def __str__(self):
        return "LexToken(%s,%r,%d,%d)" % (self.type,self.value,self.lineno,self.lexpos)
    def __repr__(self):
        return str(self)

# This object is a stand-in for a logging object created by the 
# logging module.  

class PlyLogger(object):
    def __init__(self,f):
        self.f = f
    def critical(self,msg,*args,**kwargs):
        self.f.write((msg % args) + "\n")

    def warning(self,msg,*args,**kwargs):
        self.f.write("WARNING: "+ (msg % args) + "\n")

    def error(self,msg,*args,**kwargs):
        self.f.write("ERROR: " + (msg % args) + "\n")

    info = critical
    debug = critical

# Null logger is used when no output is generated. Does nothing.
class NullLogger(object):
    def __getattribute__(self,name):
        return self
    def __call__(self,*args,**kwargs):
        return self

# -----------------------------------------------------------------------------
#                        === Lexing Engine ===
#
# The following Lexer class implements the lexer runtime.   There are only
# a few public methods and attributes:
#
#    input()          -  Store a new string in the lexer
#    token()          -  Get the next token
#    clone()          -  Clone the lexer
#
#    lineno           -  Current line number
#    lexpos           -  Current position in the input string
# -----------------------------------------------------------------------------

class Lexer:
    def __init__(self):
        self.lexre = None             # Master regular expression. This is a list of
                                      # tuples (re,findex) where re is a compiled
                                      # regular expression and findex is a list
                                      # mapping regex group numbers to rules
        self.lexretext = None         # Current regular expression strings
        self.lexstatere = {}          # Dictionary mapping lexer states to master regexs
        self.lexstateretext = {}      # Dictionary mapping lexer states to regex strings
        self.lexstaterenames = {}     # Dictionary mapping lexer states to symbol names
        self.lexstate = "INITIAL"     # Current lexer state
        self.lexstatestack = []       # Stack of lexer states
        self.lexstateinfo = None      # State information
        self.lexstateignore = {}      # Dictionary of ignored characters for each state
        self.lexstateerrorf = {}      # Dictionary of error functions for each state
        self.lexreflags = 0           # Optional re compile flags
        self.lexdata = None           # Actual input data (as a string)
        self.lexpos = 0               # Current position in input text
        self.lexlen = 0               # Length of the input text
        self.lexerrorf = None         # Error rule (if any)
        self.lextokens = None         # List of valid tokens
        self.lexignore = ""           # Ignored characters
        self.lexliterals = ""         # Literal characters that can be passed through
        self.lexmodule = None         # Module
        self.lineno = 1               # Current line number
        self.lexoptimize = 0          # Optimized mode

    def clone(self,object=None):
        c = copy.copy(self)

        # If the object parameter has been supplied, it means we are attaching the
        # lexer to a new object.  In this case, we have to rebind all methods in
        # the lexstatere and lexstateerrorf tables.

        if object:
            newtab = { }
            for key, ritem in self.lexstatere.items():
                newre = []
                for cre, findex in ritem:
                     newfindex = []
                     for f in findex:
                         if not f or not f[0]:
                             newfindex.append(f)
                             continue
                         newfindex.append((getattr(object,f[0].__name__),f[1]))
                newre.append((cre,newfindex))
                newtab[key] = newre
            c.lexstatere = newtab
            c.lexstateerrorf = { }
            for key, ef in self.lexstateerrorf.items():
                c.lexstateerrorf[key] = getattr(object,ef.__name__)
            c.lexmodule = object
        return c

    # ------------------------------------------------------------
    # writetab() - Write lexer information to a table file
    # ------------------------------------------------------------
    def writetab(self,tabfile,outputdir=""):
        if isinstance(tabfile,types.ModuleType):
            return
        basetabfilename = tabfile.split(".")[-1]
        filename = os.path.join(outputdir,basetabfilename)+".py"
        tf = open(filename,"w")
        tf.write("# %s.py. This file automatically created by PLY (version %s). Don't edit!\n" % (tabfile,__version__))
        tf.write("_tabversion   = %s\n" % repr(__version__))
        tf.write("_lextokens    = %s\n" % repr(self.lextokens))
        tf.write("_lexreflags   = %s\n" % repr(self.lexreflags))
        tf.write("_lexliterals  = %s\n" % repr(self.lexliterals))
        tf.write("_lexstateinfo = %s\n" % repr(self.lexstateinfo))

        tabre = { }
        # Collect all functions in the initial state
        initial = self.lexstatere["INITIAL"]
        initialfuncs = []
        for part in initial:
            for f in part[1]:
                if f and f[0]:
                    initialfuncs.append(f)

        for key, lre in self.lexstatere.items():
             titem = []
             for i in range(len(lre)):
                  titem.append((self.lexstateretext[key][i],_funcs_to_names(lre[i][1],self.lexstaterenames[key][i])))
             tabre[key] = titem

        tf.write("_lexstatere   = %s\n" % repr(tabre))
        tf.write("_lexstateignore = %s\n" % repr(self.lexstateignore))

        taberr = { }
        for key, ef in self.lexstateerrorf.items():
             if ef:
                  taberr[key] = ef.__name__
             else:
                  taberr[key] = None
        tf.write("_lexstateerrorf = %s\n" % repr(taberr))
        tf.close()

    # ------------------------------------------------------------
    # readtab() - Read lexer information from a tab file
    # ------------------------------------------------------------
    def readtab(self,tabfile,fdict):
        if isinstance(tabfile,types.ModuleType):
            lextab = tabfile
        else:
            if sys.version_info[0] < 3:
                exec("import %s as lextab" % tabfile)
            else:
                env = { }
                exec("import %s as lextab" % tabfile, env,env)
                lextab = env['lextab']

        if getattr(lextab,"_tabversion","0.0") != __version__:
            raise ImportError("Inconsistent PLY version")

        self.lextokens      = lextab._lextokens
        self.lexreflags     = lextab._lexreflags
        self.lexliterals    = lextab._lexliterals
        self.lexstateinfo   = lextab._lexstateinfo
        self.lexstateignore = lextab._lexstateignore
        self.lexstatere     = { }
        self.lexstateretext = { }
        for key,lre in lextab._lexstatere.items():
             titem = []
             txtitem = []
             for i in range(len(lre)):
                  titem.append((re.compile(lre[i][0],lextab._lexreflags | re.VERBOSE),_names_to_funcs(lre[i][1],fdict)))
                  txtitem.append(lre[i][0])
             self.lexstatere[key] = titem
             self.lexstateretext[key] = txtitem
        self.lexstateerrorf = { }
        for key,ef in lextab._lexstateerrorf.items():
             self.lexstateerrorf[key] = fdict[ef]
        self.begin('INITIAL')

    # ------------------------------------------------------------
    # input() - Push a new string into the lexer
    # ------------------------------------------------------------
    def input(self,s):
        # Pull off the first character to see if s looks like a string
        c = s[:1]
        if not isinstance(c,StringTypes):
            raise ValueError("Expected a string")
        self.lexdata = s
        self.lexpos = 0
        self.lexlen = len(s)

    # ------------------------------------------------------------
    # begin() - Changes the lexing state
    # ------------------------------------------------------------
    def begin(self,state):
        if not state in self.lexstatere:
            raise ValueError("Undefined state")
        self.lexre = self.lexstatere[state]
        self.lexretext = self.lexstateretext[state]
        self.lexignore = self.lexstateignore.get(state,"")
        self.lexerrorf = self.lexstateerrorf.get(state,None)
        self.lexstate = state

    # ------------------------------------------------------------
    # push_state() - Changes the lexing state and saves old on stack
    # ------------------------------------------------------------
    def push_state(self,state):
        self.lexstatestack.append(self.lexstate)
        self.begin(state)

    # ------------------------------------------------------------
    # pop_state() - Restores the previous state
    # ------------------------------------------------------------
    def pop_state(self):
        self.begin(self.lexstatestack.pop())

    # ------------------------------------------------------------
    # current_state() - Returns the current lexing state
    # ------------------------------------------------------------
    def current_state(self):
        return self.lexstate

    # ------------------------------------------------------------
    # skip() - Skip ahead n characters
    # ------------------------------------------------------------
    def skip(self,n):
        self.lexpos += n

    # ------------------------------------------------------------
    # opttoken() - Return the next token from the Lexer
    #
    # Note: This function has been carefully implemented to be as fast
    # as possible.  Don't make changes unless you really know what
    # you are doing
    # ------------------------------------------------------------
    def token(self):
        # Make local copies of frequently referenced attributes
        lexpos    = self.lexpos
        lexlen    = self.lexlen
        lexignore = self.lexignore
        lexdata   = self.lexdata

        while lexpos < lexlen:
            # This code provides some short-circuit code for whitespace, tabs, and other ignored characters
            if lexdata[lexpos] in lexignore:
                lexpos += 1
                continue

            # Look for a regular expression match
            for lexre,lexindexfunc in self.lexre:
                m = lexre.match(lexdata,lexpos)
                if not m: continue

                # Create a token for return
                tok = LexToken()
                tok.value = m.group()
                tok.lineno = self.lineno
                tok.lexpos = lexpos

                i = m.lastindex
                func,tok.type = lexindexfunc[i]

                if not func:
                   # If no token type was set, it's an ignored token
                   if tok.type:
                      self.lexpos = m.end()
                      return tok
                   else:
                      lexpos = m.end()
                      break

                lexpos = m.end()

                # If token is processed by a function, call it

                tok.lexer = self      # Set additional attributes useful in token rules
                self.lexmatch = m
                self.lexpos = lexpos

                newtok = func(tok)

                # Every function must return a token, if nothing, we just move to next token
                if not newtok:
                    lexpos    = self.lexpos         # This is here in case user has updated lexpos.
                    lexignore = self.lexignore      # This is here in case there was a state change
                    break

                # Verify type of the token.  If not in the token map, raise an error
                if not self.lexoptimize:
                    if not newtok.type in self.lextokens:
                        raise LexError("%s:%d: Rule '%s' returned an unknown token type '%s'" % (
                            func_code(func).co_filename, func_code(func).co_firstlineno,
                            func.__name__, newtok.type),lexdata[lexpos:])

                return newtok
            else:
                # No match, see if in literals
                if lexdata[lexpos] in self.lexliterals:
                    tok = LexToken()
                    tok.value = lexdata[lexpos]
                    tok.lineno = self.lineno
                    tok.type = tok.value
                    tok.lexpos = lexpos
                    self.lexpos = lexpos + 1
                    return tok

                # No match. Call t_error() if defined.
                if self.lexerrorf:
                    tok = LexToken()
                    tok.value = self.lexdata[lexpos:]
                    tok.lineno = self.lineno
                    tok.type = "error"
                    tok.lexer = self
                    tok.lexpos = lexpos
                    self.lexpos = lexpos
                    newtok = self.lexerrorf(tok)
                    if lexpos == self.lexpos:
                        # Error method didn't change text position at all. This is an error.
                        raise LexError("Scanning error. Illegal character '%s'" % (lexdata[lexpos]), lexdata[lexpos:])
                    lexpos = self.lexpos
                    if not newtok: continue
                    return newtok

                self.lexpos = lexpos
                raise LexError("Illegal character '%s' at index %d" % (lexdata[lexpos],lexpos), lexdata[lexpos:])

        self.lexpos = lexpos + 1
        if self.lexdata is None:
             raise RuntimeError("No input string given with input()")
        return None

    # Iterator interface
    def __iter__(self):
        return self

    def next(self):
        t = self.token()
        if t is None:
            raise StopIteration
        return t

    __next__ = next

# -----------------------------------------------------------------------------
#                           ==== Lex Builder ===
#
# The functions and classes below are used to collect lexing information
# and build a Lexer object from it.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# get_caller_module_dict()
#
# This function returns a dictionary containing all of the symbols defined within
# a caller further down the call stack.  This is used to get the environment
# associated with the yacc() call if none was provided.
# -----------------------------------------------------------------------------

def get_caller_module_dict(levels):
    try:
        raise RuntimeError
    except RuntimeError:
        e,b,t = sys.exc_info()
        f = t.tb_frame
        while levels > 0:
            f = f.f_back                   
            levels -= 1
        ldict = f.f_globals.copy()
        if f.f_globals != f.f_locals:
            ldict.update(f.f_locals)

        return ldict

# -----------------------------------------------------------------------------
# _funcs_to_names()
#
# Given a list of regular expression functions, this converts it to a list
# suitable for output to a table file
# -----------------------------------------------------------------------------

def _funcs_to_names(funclist,namelist):
    result = []
    for f,name in zip(funclist,namelist):
         if f and f[0]:
             result.append((name, f[1]))
         else:
             result.append(f)
    return result

# -----------------------------------------------------------------------------
# _names_to_funcs()
#
# Given a list of regular expression function names, this converts it back to
# functions.
# -----------------------------------------------------------------------------

def _names_to_funcs(namelist,fdict):
     result = []
     for n in namelist:
          if n and n[0]:
              result.append((fdict[n[0]],n[1]))
          else:
              result.append(n)
     return result

# -----------------------------------------------------------------------------
# _form_master_re()
#
# This function takes a list of all of the regex components and attempts to
# form the master regular expression.  Given limitations in the Python re
# module, it may be necessary to break the master regex into separate expressions.
# -----------------------------------------------------------------------------

def _form_master_re(relist,reflags,ldict,toknames):
    if not relist: return []
    regex = "|".join(relist)
    try:
        lexre = re.compile(regex,re.VERBOSE | reflags)

        # Build the index to function map for the matching engine
        lexindexfunc = [ None ] * (max(lexre.groupindex.values())+1)
        lexindexnames = lexindexfunc[:]

        for f,i in lexre.groupindex.items():
            handle = ldict.get(f,None)
            if type(handle) in (types.FunctionType, types.MethodType):
                lexindexfunc[i] = (handle,toknames[f])
                lexindexnames[i] = f
            elif handle is not None:
                lexindexnames[i] = f
                if f.find("ignore_") > 0:
                    lexindexfunc[i] = (None,None)
                else:
                    lexindexfunc[i] = (None, toknames[f])
        
        return [(lexre,lexindexfunc)],[regex],[lexindexnames]
    except Exception:
        m = int(len(relist)/2)
        if m == 0: m = 1
        llist, lre, lnames = _form_master_re(relist[:m],reflags,ldict,toknames)
        rlist, rre, rnames = _form_master_re(relist[m:],reflags,ldict,toknames)
        return llist+rlist, lre+rre, lnames+rnames

# -----------------------------------------------------------------------------
# def _statetoken(s,names)
#
# Given a declaration name s of the form "t_" and a dictionary whose keys are
# state names, this function returns a tuple (states,tokenname) where states
# is a tuple of state names and tokenname is the name of the token.  For example,
# calling this with s = "t_foo_bar_SPAM" might return (('foo','bar'),'SPAM')
# -----------------------------------------------------------------------------

def _statetoken(s,names):
    nonstate = 1
    parts = s.split("_")
    for i in range(1,len(parts)):
         if not parts[i] in names and parts[i] != 'ANY': break
    if i > 1:
       states = tuple(parts[1:i])
    else:
       states = ('INITIAL',)

    if 'ANY' in states:
       states = tuple(names)

    tokenname = "_".join(parts[i:])
    return (states,tokenname)


# -----------------------------------------------------------------------------
# LexerReflect()
#
# This class represents information needed to build a lexer as extracted from a
# user's input file.
# -----------------------------------------------------------------------------
class LexerReflect(object):
    def __init__(self,ldict,log=None,reflags=0):
        self.ldict      = ldict
        self.error_func = None
        self.tokens     = []
        self.reflags    = reflags
        self.stateinfo  = { 'INITIAL' : 'inclusive'}
        self.files      = {}
        self.error      = 0

        if log is None:
            self.log = PlyLogger(sys.stderr)
        else:
            self.log = log

    # Get all of the basic information
    def get_all(self):
        self.get_tokens()
        self.get_literals()
        self.get_states()
        self.get_rules()
        
    # Validate all of the information
    def validate_all(self):
        self.validate_tokens()
        self.validate_literals()
        self.validate_rules()
        return self.error

    # Get the tokens map
    def get_tokens(self):
        tokens = self.ldict.get("tokens",None)
        if not tokens:
            self.log.error("No token list is defined")
            self.error = 1
            return

        if not isinstance(tokens,(list, tuple)):
            self.log.error("tokens must be a list or tuple")
            self.error = 1
            return
        
        if not tokens:
            self.log.error("tokens is empty")
            self.error = 1
            return

        self.tokens = tokens

    # Validate the tokens
    def validate_tokens(self):
        terminals = {}
        for n in self.tokens:
            if not _is_identifier.match(n):
                self.log.error("Bad token name '%s'",n)
                self.error = 1
            if n in terminals:
                self.log.warning("Token '%s' multiply defined", n)
            terminals[n] = 1

    # Get the literals specifier
    def get_literals(self):
        self.literals = self.ldict.get("literals","")

    # Validate literals
    def validate_literals(self):
        try:
            for c in self.literals:
                if not isinstance(c,StringTypes) or len(c) > 1:
                    self.log.error("Invalid literal %s. Must be a single character", repr(c))
                    self.error = 1
                    continue

        except TypeError:
            self.log.error("Invalid literals specification. literals must be a sequence of characters")
            self.error = 1

    def get_states(self):
        self.states = self.ldict.get("states",None)
        # Build statemap
        if self.states:
             if not isinstance(self.states,(tuple,list)):
                  self.log.error("states must be defined as a tuple or list")
                  self.error = 1
             else:
                  for s in self.states:
                        if not isinstance(s,tuple) or len(s) != 2:
                               self.log.error("Invalid state specifier %s. Must be a tuple (statename,'exclusive|inclusive')",repr(s))
                               self.error = 1
                               continue
                        name, statetype = s
                        if not isinstance(name,StringTypes):
                               self.log.error("State name %s must be a string", repr(name))
                               self.error = 1
                               continue
                        if not (statetype == 'inclusive' or statetype == 'exclusive'):
                               self.log.error("State type for state %s must be 'inclusive' or 'exclusive'",name)
                               self.error = 1
                               continue
                        if name in self.stateinfo:
                               self.log.error("State '%s' already defined",name)
                               self.error = 1
                               continue
                        self.stateinfo[name] = statetype

    # Get all of the symbols with a t_ prefix and sort them into various
    # categories (functions, strings, error functions, and ignore characters)

    def get_rules(self):
        tsymbols = [f for f in self.ldict if f[:2] == 't_' ]

        # Now build up a list of functions and a list of strings

        self.toknames = { }        # Mapping of symbols to token names
        self.funcsym =  { }        # Symbols defined as functions
        self.strsym =   { }        # Symbols defined as strings
        self.ignore   = { }        # Ignore strings by state
        self.errorf   = { }        # Error functions by state

        for s in self.stateinfo:
             self.funcsym[s] = []
             self.strsym[s] = []

        if len(tsymbols) == 0:
            self.log.error("No rules of the form t_rulename are defined")
            self.error = 1
            return

        for f in tsymbols:
            t = self.ldict[f]
            states, tokname = _statetoken(f,self.stateinfo)
            self.toknames[f] = tokname

            if hasattr(t,"__call__"):
                if tokname == 'error':
                    for s in states:
                        self.errorf[s] = t
                elif tokname == 'ignore':
                    line = func_code(t).co_firstlineno
                    file = func_code(t).co_filename
                    self.log.error("%s:%d: Rule '%s' must be defined as a string",file,line,t.__name__)
                    self.error = 1
                else:
                    for s in states: 
                        self.funcsym[s].append((f,t))
            elif isinstance(t, StringTypes):
                if tokname == 'ignore':
                    for s in states:
                        self.ignore[s] = t
                    if "\\" in t:
                        self.log.warning("%s contains a literal backslash '\\'",f)

                elif tokname == 'error':
                    self.log.error("Rule '%s' must be defined as a function", f)
                    self.error = 1
                else:
                    for s in states: 
                        self.strsym[s].append((f,t))
            else:
                self.log.error("%s not defined as a function or string", f)
                self.error = 1

        # Sort the functions by line number
        for f in self.funcsym.values():
            if sys.version_info[0] < 3:
                f.sort(lambda x,y: cmp(func_code(x[1]).co_firstlineno,func_code(y[1]).co_firstlineno))
            else:
                # Python 3.0
                f.sort(key=lambda x: func_code(x[1]).co_firstlineno)

        # Sort the strings by regular expression length
        for s in self.strsym.values():
            if sys.version_info[0] < 3:
                s.sort(lambda x,y: (len(x[1]) < len(y[1])) - (len(x[1]) > len(y[1])))
            else:
                # Python 3.0
                s.sort(key=lambda x: len(x[1]),reverse=True)

    # Validate all of the t_rules collected 
    def validate_rules(self):
        for state in self.stateinfo:
            # Validate all rules defined by functions

            

            for fname, f in self.funcsym[state]:
                line = func_code(f).co_firstlineno
                file = func_code(f).co_filename
                self.files[file] = 1

                tokname = self.toknames[fname]
                if isinstance(f, types.MethodType):
                    reqargs = 2
                else:
                    reqargs = 1
                nargs = func_code(f).co_argcount
                if nargs > reqargs:
                    self.log.error("%s:%d: Rule '%s' has too many arguments",file,line,f.__name__)
                    self.error = 1
                    continue

                if nargs < reqargs:
                    self.log.error("%s:%d: Rule '%s' requires an argument", file,line,f.__name__)
                    self.error = 1
                    continue

                if not f.__doc__:
                    self.log.error("%s:%d: No regular expression defined for rule '%s'",file,line,f.__name__)
                    self.error = 1
                    continue

                try:
                    c = re.compile("(?P<%s>%s)" % (fname,f.__doc__), re.VERBOSE | self.reflags)
                    if c.match(""):
                        self.log.error("%s:%d: Regular expression for rule '%s' matches empty string", file,line,f.__name__)
                        self.error = 1
                except re.error:
                    _etype, e, _etrace = sys.exc_info()
                    self.log.error("%s:%d: Invalid regular expression for rule '%s'. %s", file,line,f.__name__,e)
                    if '#' in f.__doc__:
                        self.log.error("%s:%d. Make sure '#' in rule '%s' is escaped with '\\#'",file,line, f.__name__)
                    self.error = 1

            # Validate all rules defined by strings
            for name,r in self.strsym[state]:
                tokname = self.toknames[name]
                if tokname == 'error':
                    self.log.error("Rule '%s' must be defined as a function", name)
                    self.error = 1
                    continue

                if not tokname in self.tokens and tokname.find("ignore_") < 0:
                    self.log.error("Rule '%s' defined for an unspecified token %s",name,tokname)
                    self.error = 1
                    continue

                try:
                    c = re.compile("(?P<%s>%s)" % (name,r),re.VERBOSE | self.reflags)
                    if (c.match("")):
                         self.log.error("Regular expression for rule '%s' matches empty string",name)
                         self.error = 1
                except re.error:
                    _etype, e, _etrace = sys.exc_info()
                    self.log.error("Invalid regular expression for rule '%s'. %s",name,e)
                    if '#' in r:
                         self.log.error("Make sure '#' in rule '%s' is escaped with '\\#'",name)
                    self.error = 1

            if not self.funcsym[state] and not self.strsym[state]:
                self.log.error("No rules defined for state '%s'",state)
                self.error = 1

            # Validate the error function
            efunc = self.errorf.get(state,None)
            if efunc:
                f = efunc
                line = func_code(f).co_firstlineno
                file = func_code(f).co_filename
                self.files[file] = 1

                if isinstance(f, types.MethodType):
                    reqargs = 2
                else:
                    reqargs = 1
                nargs = func_code(f).co_argcount
                if nargs > reqargs:
                    self.log.error("%s:%d: Rule '%s' has too many arguments",file,line,f.__name__)
                    self.error = 1

                if nargs < reqargs:
                    self.log.error("%s:%d: Rule '%s' requires an argument", file,line,f.__name__)
                    self.error = 1

        for f in self.files:
            self.validate_file(f)


    # -----------------------------------------------------------------------------
    # validate_file()
    #
    # This checks to see if there are duplicated t_rulename() functions or strings
    # in the parser input file.  This is done using a simple regular expression
    # match on each line in the given file.  
    # -----------------------------------------------------------------------------

    def validate_file(self,filename):
        import os.path
        base,ext = os.path.splitext(filename)
        if ext != '.py': return         # No idea what the file is. Return OK

        try:
            f = open(filename)
            lines = f.readlines()
            f.close()
        except IOError:
            return                      # Couldn't find the file.  Don't worry about it

        fre = re.compile(r'\s*def\s+(t_[a-zA-Z_0-9]*)\(')
        sre = re.compile(r'\s*(t_[a-zA-Z_0-9]*)\s*=')

        counthash = { }
        linen = 1
        for l in lines:
            m = fre.match(l)
            if not m:
                m = sre.match(l)
            if m:
                name = m.group(1)
                prev = counthash.get(name)
                if not prev:
                    counthash[name] = linen
                else:
                    self.log.error("%s:%d: Rule %s redefined. Previously defined on line %d",filename,linen,name,prev)
                    self.error = 1
            linen += 1
            
# -----------------------------------------------------------------------------
# lex(module)
#
# Build all of the regular expression rules from definitions in the supplied module
# -----------------------------------------------------------------------------
def lex(module=None,object=None,debug=0,optimize=0,lextab="lextab",reflags=0,nowarn=0,outputdir="", debuglog=None, errorlog=None):
    global lexer
    ldict = None
    stateinfo  = { 'INITIAL' : 'inclusive'}
    lexobj = Lexer()
    lexobj.lexoptimize = optimize
    global token,input

    if errorlog is None:
        errorlog = PlyLogger(sys.stderr)

    if debug:
        if debuglog is None:
            debuglog = PlyLogger(sys.stderr)

    # Get the module dictionary used for the lexer
    if object: module = object

    if module:
        _items = [(k,getattr(module,k)) for k in dir(module)]
        ldict = dict(_items)
    else:
        ldict = get_caller_module_dict(2)

    # Collect parser information from the dictionary
    linfo = LexerReflect(ldict,log=errorlog,reflags=reflags)
    linfo.get_all()
    if not optimize:
        if linfo.validate_all():
            raise SyntaxError("Can't build lexer")

    if optimize and lextab:
        try:
            lexobj.readtab(lextab,ldict)
            token = lexobj.token
            input = lexobj.input
            lexer = lexobj
            return lexobj

        except ImportError:
            pass

    # Dump some basic debugging information
    if debug:
        debuglog.info("lex: tokens   = %r", linfo.tokens)
        debuglog.info("lex: literals = %r", linfo.literals)
        debuglog.info("lex: states   = %r", linfo.stateinfo)

    # Build a dictionary of valid token names
    lexobj.lextokens = { }
    for n in linfo.tokens:
        lexobj.lextokens[n] = 1

    # Get literals specification
    if isinstance(linfo.literals,(list,tuple)):
        lexobj.lexliterals = type(linfo.literals[0])().join(linfo.literals)
    else:
        lexobj.lexliterals = linfo.literals

    # Get the stateinfo dictionary
    stateinfo = linfo.stateinfo

    regexs = { }
    # Build the master regular expressions
    for state in stateinfo:
        regex_list = []

        # Add rules defined by functions first
        for fname, f in linfo.funcsym[state]:
            line = func_code(f).co_firstlineno
            file = func_code(f).co_filename
            regex_list.append("(?P<%s>%s)" % (fname,f.__doc__))
            if debug:
                debuglog.info("lex: Adding rule %s -> '%s' (state '%s')",fname,f.__doc__, state)

        # Now add all of the simple rules
        for name,r in linfo.strsym[state]:
            regex_list.append("(?P<%s>%s)" % (name,r))
            if debug:
                debuglog.info("lex: Adding rule %s -> '%s' (state '%s')",name,r, state)

        regexs[state] = regex_list

    # Build the master regular expressions

    if debug:
        debuglog.info("lex: ==== MASTER REGEXS FOLLOW ====")

    for state in regexs:
        lexre, re_text, re_names = _form_master_re(regexs[state],reflags,ldict,linfo.toknames)
        lexobj.lexstatere[state] = lexre
        lexobj.lexstateretext[state] = re_text
        lexobj.lexstaterenames[state] = re_names
        if debug:
            for i in range(len(re_text)):
                debuglog.info("lex: state '%s' : regex[%d] = '%s'",state, i, re_text[i])

    # For inclusive states, we need to add the regular expressions from the INITIAL state
    for state,stype in stateinfo.items():
        if state != "INITIAL" and stype == 'inclusive':
             lexobj.lexstatere[state].extend(lexobj.lexstatere['INITIAL'])
             lexobj.lexstateretext[state].extend(lexobj.lexstateretext['INITIAL'])
             lexobj.lexstaterenames[state].extend(lexobj.lexstaterenames['INITIAL'])

    lexobj.lexstateinfo = stateinfo
    lexobj.lexre = lexobj.lexstatere["INITIAL"]
    lexobj.lexretext = lexobj.lexstateretext["INITIAL"]
    lexobj.lexreflags = reflags

    # Set up ignore variables
    lexobj.lexstateignore = linfo.ignore
    lexobj.lexignore = lexobj.lexstateignore.get("INITIAL","")

    # Set up error functions
    lexobj.lexstateerrorf = linfo.errorf
    lexobj.lexerrorf = linfo.errorf.get("INITIAL",None)
    if not lexobj.lexerrorf:
        errorlog.warning("No t_error rule is defined")

    # Check state information for ignore and error rules
    for s,stype in stateinfo.items():
        if stype == 'exclusive':
              if not s in linfo.errorf:
                   errorlog.warning("No error rule is defined for exclusive state '%s'", s)
              if not s in linfo.ignore and lexobj.lexignore:
                   errorlog.warning("No ignore rule is defined for exclusive state '%s'", s)
        elif stype == 'inclusive':
              if not s in linfo.errorf:
                   linfo.errorf[s] = linfo.errorf.get("INITIAL",None)
              if not s in linfo.ignore:
                   linfo.ignore[s] = linfo.ignore.get("INITIAL","")

    # Create global versions of the token() and input() functions
    token = lexobj.token
    input = lexobj.input
    lexer = lexobj

    # If in optimize mode, we write the lextab
    if lextab and optimize:
        lexobj.writetab(lextab,outputdir)

    return lexobj

# -----------------------------------------------------------------------------
# runmain()
#
# This runs the lexer as a main program
# -----------------------------------------------------------------------------

def runmain(lexer=None,data=None):
    if not data:
        try:
            filename = sys.argv[1]
            f = open(filename)
            data = f.read()
            f.close()
        except IndexError:
            sys.stdout.write("Reading from standard input (type EOF to end):\n")
            data = sys.stdin.read()

    if lexer:
        _input = lexer.input
    else:
        _input = input
    _input(data)
    if lexer:
        _token = lexer.token
    else:
        _token = token

    while 1:
        tok = _token()
        if not tok: break
        sys.stdout.write("(%s,%r,%d,%d)\n" % (tok.type, tok.value, tok.lineno,tok.lexpos))

# -----------------------------------------------------------------------------
# @TOKEN(regex)
#
# This decorator function can be used to set the regex expression on a function
# when its docstring might need to be set in an alternative way
# -----------------------------------------------------------------------------

def TOKEN(r):
    def set_doc(f):
        if hasattr(r,"__call__"):
            f.__doc__ = r.__doc__
        else:
            f.__doc__ = r
        return f
    return set_doc

# Alternative spelling of the TOKEN decorator
Token = TOKEN


########NEW FILE########
__FILENAME__ = yacc
# -----------------------------------------------------------------------------
# ply: yacc.py
#
# Copyright (C) 2001-2011,
# David M. Beazley (Dabeaz LLC)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.  
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.  
# * Neither the name of the David Beazley or Dabeaz LLC may be used to
#   endorse or promote products derived from this software without
#  specific prior written permission. 
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
#
# This implements an LR parser that is constructed from grammar rules defined
# as Python functions. The grammer is specified by supplying the BNF inside
# Python documentation strings.  The inspiration for this technique was borrowed
# from John Aycock's Spark parsing system.  PLY might be viewed as cross between
# Spark and the GNU bison utility.
#
# The current implementation is only somewhat object-oriented. The
# LR parser itself is defined in terms of an object (which allows multiple
# parsers to co-exist).  However, most of the variables used during table
# construction are defined in terms of global variables.  Users shouldn't
# notice unless they are trying to define multiple parsers at the same
# time using threads (in which case they should have their head examined).
#
# This implementation supports both SLR and LALR(1) parsing.  LALR(1)
# support was originally implemented by Elias Ioup (ezioup@alumni.uchicago.edu),
# using the algorithm found in Aho, Sethi, and Ullman "Compilers: Principles,
# Techniques, and Tools" (The Dragon Book).  LALR(1) has since been replaced
# by the more efficient DeRemer and Pennello algorithm.
#
# :::::::: WARNING :::::::
#
# Construction of LR parsing tables is fairly complicated and expensive.
# To make this module run fast, a *LOT* of work has been put into
# optimization---often at the expensive of readability and what might
# consider to be good Python "coding style."   Modify the code at your
# own risk!
# ----------------------------------------------------------------------------

__version__    = "3.4"
__tabversion__ = "3.2"       # Table version

#-----------------------------------------------------------------------------
#                     === User configurable parameters ===
#
# Change these to modify the default behavior of yacc (if you wish)
#-----------------------------------------------------------------------------

yaccdebug   = 1                # Debugging mode.  If set, yacc generates a
                               # a 'parser.out' file in the current directory

debug_file  = 'parser.out'     # Default name of the debugging file
tab_module  = 'parsetab'       # Default name of the table module
default_lr  = 'LALR'           # Default LR table generation method

error_count = 3                # Number of symbols that must be shifted to leave recovery mode

yaccdevel   = 0                # Set to True if developing yacc.  This turns off optimized
                               # implementations of certain functions.

resultlimit = 40               # Size limit of results when running in debug mode.

pickle_protocol = 0            # Protocol to use when writing pickle files

import re, types, sys, os.path

# Compatibility function for python 2.6/3.0
if sys.version_info[0] < 3:
    def func_code(f):
        return f.func_code
else:
    def func_code(f):
        return f.__code__

# Compatibility
try:
    MAXINT = sys.maxint
except AttributeError:
    MAXINT = sys.maxsize

# Python 2.x/3.0 compatibility.
def load_ply_lex():
    # Modified for asp
    import asp.ply.lex as lex
    return lex

# This object is a stand-in for a logging object created by the 
# logging module.   PLY will use this by default to create things
# such as the parser.out file.  If a user wants more detailed
# information, they can create their own logging object and pass
# it into PLY.

class PlyLogger(object):
    def __init__(self,f):
        self.f = f
    def debug(self,msg,*args,**kwargs):
        self.f.write((msg % args) + "\n")
    info     = debug

    def warning(self,msg,*args,**kwargs):
        self.f.write("WARNING: "+ (msg % args) + "\n")

    def error(self,msg,*args,**kwargs):
        self.f.write("ERROR: " + (msg % args) + "\n")

    critical = debug

# Null logger is used when no output is generated. Does nothing.
class NullLogger(object):
    def __getattribute__(self,name):
        return self
    def __call__(self,*args,**kwargs):
        return self
        
# Exception raised for yacc-related errors
class YaccError(Exception):   pass

# Format the result message that the parser produces when running in debug mode.
def format_result(r):
    repr_str = repr(r)
    if '\n' in repr_str: repr_str = repr(repr_str)
    if len(repr_str) > resultlimit:
        repr_str = repr_str[:resultlimit]+" ..."
    result = "<%s @ 0x%x> (%s)" % (type(r).__name__,id(r),repr_str)
    return result


# Format stack entries when the parser is running in debug mode
def format_stack_entry(r):
    repr_str = repr(r)
    if '\n' in repr_str: repr_str = repr(repr_str)
    if len(repr_str) < 16:
        return repr_str
    else:
        return "<%s @ 0x%x>" % (type(r).__name__,id(r))

#-----------------------------------------------------------------------------
#                        ===  LR Parsing Engine ===
#
# The following classes are used for the LR parser itself.  These are not
# used during table construction and are independent of the actual LR
# table generation algorithm
#-----------------------------------------------------------------------------

# This class is used to hold non-terminal grammar symbols during parsing.
# It normally has the following attributes set:
#        .type       = Grammar symbol type
#        .value      = Symbol value
#        .lineno     = Starting line number
#        .endlineno  = Ending line number (optional, set automatically)
#        .lexpos     = Starting lex position
#        .endlexpos  = Ending lex position (optional, set automatically)

class YaccSymbol:
    def __str__(self):    return self.type
    def __repr__(self):   return str(self)

# This class is a wrapper around the objects actually passed to each
# grammar rule.   Index lookup and assignment actually assign the
# .value attribute of the underlying YaccSymbol object.
# The lineno() method returns the line number of a given
# item (or 0 if not defined).   The linespan() method returns
# a tuple of (startline,endline) representing the range of lines
# for a symbol.  The lexspan() method returns a tuple (lexpos,endlexpos)
# representing the range of positional information for a symbol.

class YaccProduction:
    def __init__(self,s,stack=None):
        self.slice = s
        self.stack = stack
        self.lexer = None
        self.parser= None
    def __getitem__(self,n):
        if n >= 0: return self.slice[n].value
        else: return self.stack[n].value

    def __setitem__(self,n,v):
        self.slice[n].value = v

    def __getslice__(self,i,j):
        return [s.value for s in self.slice[i:j]]

    def __len__(self):
        return len(self.slice)

    def lineno(self,n):
        return getattr(self.slice[n],"lineno",0)

    def set_lineno(self,n,lineno):
        self.slice[n].lineno = lineno

    def linespan(self,n):
        startline = getattr(self.slice[n],"lineno",0)
        endline = getattr(self.slice[n],"endlineno",startline)
        return startline,endline

    def lexpos(self,n):
        return getattr(self.slice[n],"lexpos",0)

    def lexspan(self,n):
        startpos = getattr(self.slice[n],"lexpos",0)
        endpos = getattr(self.slice[n],"endlexpos",startpos)
        return startpos,endpos

    def error(self):
       raise SyntaxError


# -----------------------------------------------------------------------------
#                               == LRParser ==
#
# The LR Parsing engine.
# -----------------------------------------------------------------------------

class LRParser:
    def __init__(self,lrtab,errorf):
        self.productions = lrtab.lr_productions
        self.action      = lrtab.lr_action
        self.goto        = lrtab.lr_goto
        self.errorfunc   = errorf

    def errok(self):
        self.errorok     = 1

    def restart(self):
        del self.statestack[:]
        del self.symstack[:]
        sym = YaccSymbol()
        sym.type = '$end'
        self.symstack.append(sym)
        self.statestack.append(0)

    def parse(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        if debug or yaccdevel:
            if isinstance(debug,int):
                debug = PlyLogger(sys.stderr)
            return self.parsedebug(input,lexer,debug,tracking,tokenfunc)
        elif tracking:
            return self.parseopt(input,lexer,debug,tracking,tokenfunc)
        else:
            return self.parseopt_notrack(input,lexer,debug,tracking,tokenfunc)
        

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parsedebug().
    #
    # This is the debugging enabled version of parse().  All changes made to the
    # parsing engine should be made here.   For the non-debugging version,
    # copy this code to a method parseopt() and delete all of the sections
    # enclosed in:
    #
    #      #--! DEBUG
    #      statements
    #      #--! DEBUG
    #
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parsedebug(self,input=None,lexer=None,debug=None,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 

        # --! DEBUG
        debug.info("PLY: PARSE DEBUG START")
        # --! DEBUG

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            lex = load_ply_lex()
            lexer = lex.lexer

        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = "$end"
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            # --! DEBUG
            debug.debug('')
            debug.debug('State  : %s', state)
            # --! DEBUG

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = "$end"

            # --! DEBUG
            debug.debug('Stack  : %s',
                        ("%s . %s" % (" ".join([xx.type for xx in symstack][1:]), str(lookahead))).lstrip())
            # --! DEBUG

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t
                    
                    # --! DEBUG
                    debug.debug("Action : Shift and goto state %s", t)
                    # --! DEBUG

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    # --! DEBUG
                    if plen:
                        debug.info("Action : Reduce rule [%s] with %s and goto state %d", p.str, "["+",".join([format_stack_entry(_v.value) for _v in symstack[-plen:]])+"]",-t)
                    else:
                        debug.info("Action : Reduce rule [%s] with %s and goto state %d", p.str, [],-t)
                        
                    # --! DEBUG

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # --! TRACKING
                        if tracking:
                           t1 = targ[1]
                           sym.lineno = t1.lineno
                           sym.lexpos = t1.lexpos
                           t1 = targ[-1]
                           sym.endlineno = getattr(t1,"endlineno",t1.lineno)
                           sym.endlexpos = getattr(t1,"endlexpos",t1.lexpos)

                        # --! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            del statestack[-plen:]
                            p.callable(pslice)
                            # --! DEBUG
                            debug.info("Result : %s", format_result(pslice[0]))
                            # --! DEBUG
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        # --! TRACKING
                        if tracking:
                           sym.lineno = lexer.lineno
                           sym.lexpos = lexer.lexpos
                        # --! TRACKING

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.callable(pslice)
                            # --! DEBUG
                            debug.info("Result : %s", format_result(pslice[0]))
                            # --! DEBUG
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n,"value",None)
                    # --! DEBUG
                    debug.info("Done   : Returning %s", format_result(result))
                    debug.info("PLY: PARSE DEBUG END")
                    # --! DEBUG
                    return result

            if t == None:

                # --! DEBUG
                debug.error('Error  : %s',
                            ("%s . %s" % (" ".join([xx.type for xx in symstack][1:]), str(lookahead))).lstrip())
                # --! DEBUG

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type == "$end":
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        if errtoken and not hasattr(errtoken,'lexer'):
                            errtoken.lexer = lexer
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != "$end":
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == "$end":
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError("yacc: internal parser error!!!\n")

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt().
    #
    # Optimized version of parse() method.  DO NOT EDIT THIS CODE DIRECTLY.
    # Edit the debug version above, then copy any modifications to the method
    # below while removing #--! DEBUG sections.
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


    def parseopt(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            lex = load_ply_lex()
            lexer = lex.lexer
        
        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = '$end'

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # --! TRACKING
                        if tracking:
                           t1 = targ[1]
                           sym.lineno = t1.lineno
                           sym.lexpos = t1.lexpos
                           t1 = targ[-1]
                           sym.endlineno = getattr(t1,"endlineno",t1.lineno)
                           sym.endlexpos = getattr(t1,"endlexpos",t1.lexpos)

                        # --! TRACKING

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            del statestack[-plen:]
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        # --! TRACKING
                        if tracking:
                           sym.lineno = lexer.lineno
                           sym.lexpos = lexer.lexpos
                        # --! TRACKING

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    return getattr(n,"value",None)

            if t == None:

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        if errtoken and not hasattr(errtoken,'lexer'):
                            errtoken.lexer = lexer
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError("yacc: internal parser error!!!\n")

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # parseopt_notrack().
    #
    # Optimized version of parseopt() with line number tracking removed. 
    # DO NOT EDIT THIS CODE DIRECTLY. Copy the optimized version and remove
    # code in the #--! TRACKING sections
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def parseopt_notrack(self,input=None,lexer=None,debug=0,tracking=0,tokenfunc=None):
        lookahead = None                 # Current lookahead symbol
        lookaheadstack = [ ]             # Stack of lookahead symbols
        actions = self.action            # Local reference to action table (to avoid lookup on self.)
        goto    = self.goto              # Local reference to goto table (to avoid lookup on self.)
        prod    = self.productions       # Local reference to production list (to avoid lookup on self.)
        pslice  = YaccProduction(None)   # Production object passed to grammar rules
        errorcount = 0                   # Used during error recovery 

        # If no lexer was given, we will try to use the lex module
        if not lexer:
            lex = load_ply_lex()
            lexer = lex.lexer
        
        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        if tokenfunc is None:
           # Tokenize function
           get_token = lexer.token
        else:
           get_token = tokenfunc

        # Set up the state and symbol stacks

        statestack = [ ]                # Stack of parsing states
        self.statestack = statestack
        symstack   = [ ]                # Stack of grammar symbols
        self.symstack = symstack

        pslice.stack = symstack         # Put in the production
        errtoken   = None               # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol()
        sym.type = '$end'
        symstack.append(sym)
        state = 0
        while 1:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if not lookahead:
                if not lookaheadstack:
                    lookahead = get_token()     # Get the next token
                else:
                    lookahead = lookaheadstack.pop()
                if not lookahead:
                    lookahead = YaccSymbol()
                    lookahead.type = '$end'

            # Check the action table
            ltype = lookahead.type
            t = actions[state].get(ltype)

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t

                    symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount: errorcount -=1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen  = p.len

                    # Get production function
                    sym = YaccSymbol()
                    sym.type = pname       # Production name
                    sym.value = None

                    if plen:
                        targ = symstack[-plen-1:]
                        targ[0] = sym

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ
                        
                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            del statestack[-plen:]
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
                    else:

                        targ = [ sym ]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated 
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            p.callable(pslice)
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            lookaheadstack.append(lookahead)
                            symstack.pop()
                            statestack.pop()
                            state = statestack[-1]
                            sym.type = 'error'
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = 0
                        continue
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                if t == 0:
                    n = symstack[-1]
                    return getattr(n,"value",None)

            if t == None:

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = 0
                    errtoken = lookahead
                    if errtoken.type == '$end':
                        errtoken = None               # End of file!
                    if self.errorfunc:
                        global errok,token,restart
                        errok = self.errok        # Set some special functions available in error recovery
                        token = get_token
                        restart = self.restart
                        if errtoken and not hasattr(errtoken,'lexer'):
                            errtoken.lexer = lexer
                        tok = self.errorfunc(errtoken)
                        del errok, token, restart   # Delete special functions

                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken,"lineno"): lineno = lookahead.lineno
                            else: lineno = 0
                            if lineno:
                                sys.stderr.write("yacc: Syntax error at line %d, token=%s\n" % (lineno, errtoken.type))
                            else:
                                sys.stderr.write("yacc: Syntax error, token=%s" % errtoken.type)
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead.type != '$end':
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead.type == '$end':
                    # Whoa. We're really hosed here. Bail out
                    return

                if lookahead.type != 'error':
                    sym = symstack[-1]
                    if sym.type == 'error':
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        lookahead = None
                        continue
                    t = YaccSymbol()
                    t.type = 'error'
                    if hasattr(lookahead,"lineno"):
                        t.lineno = lookahead.lineno
                    t.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = t
                else:
                    symstack.pop()
                    statestack.pop()
                    state = statestack[-1]       # Potential bug fix

                continue

            # Call an error function here
            raise RuntimeError("yacc: internal parser error!!!\n")

# -----------------------------------------------------------------------------
#                          === Grammar Representation ===
#
# The following functions, classes, and variables are used to represent and
# manipulate the rules that make up a grammar. 
# -----------------------------------------------------------------------------

import re

# regex matching identifiers
_is_identifier = re.compile(r'^[a-zA-Z0-9_-]+$')

# -----------------------------------------------------------------------------
# class Production:
#
# This class stores the raw information about a single production or grammar rule.
# A grammar rule refers to a specification such as this:
#
#       expr : expr PLUS term 
#
# Here are the basic attributes defined on all productions
#
#       name     - Name of the production.  For example 'expr'
#       prod     - A list of symbols on the right side ['expr','PLUS','term']
#       prec     - Production precedence level
#       number   - Production number.
#       func     - Function that executes on reduce
#       file     - File where production function is defined
#       lineno   - Line number where production function is defined
#
# The following attributes are defined or optional.
#
#       len       - Length of the production (number of symbols on right hand side)
#       usyms     - Set of unique symbols found in the production
# -----------------------------------------------------------------------------

class Production(object):
    reduced = 0
    def __init__(self,number,name,prod,precedence=('right',0),func=None,file='',line=0):
        self.name     = name
        self.prod     = tuple(prod)
        self.number   = number
        self.func     = func
        self.callable = None
        self.file     = file
        self.line     = line
        self.prec     = precedence

        # Internal settings used during table construction
        
        self.len  = len(self.prod)   # Length of the production

        # Create a list of unique production symbols used in the production
        self.usyms = [ ]             
        for s in self.prod:
            if s not in self.usyms:
                self.usyms.append(s)

        # List of all LR items for the production
        self.lr_items = []
        self.lr_next = None

        # Create a string representation
        if self.prod:
            self.str = "%s -> %s" % (self.name," ".join(self.prod))
        else:
            self.str = "%s -> <empty>" % self.name

    def __str__(self):
        return self.str

    def __repr__(self):
        return "Production("+str(self)+")"

    def __len__(self):
        return len(self.prod)

    def __nonzero__(self):
        return 1

    def __getitem__(self,index):
        return self.prod[index]
            
    # Return the nth lr_item from the production (or None if at the end)
    def lr_item(self,n):
        if n > len(self.prod): return None
        p = LRItem(self,n)

        # Precompute the list of productions immediately following.  Hack. Remove later
        try:
            p.lr_after = Prodnames[p.prod[n+1]]
        except (IndexError,KeyError):
            p.lr_after = []
        try:
            p.lr_before = p.prod[n-1]
        except IndexError:
            p.lr_before = None

        return p
    
    # Bind the production function name to a callable
    def bind(self,pdict):
        if self.func:
            self.callable = pdict[self.func]

# This class serves as a minimal standin for Production objects when
# reading table data from files.   It only contains information
# actually used by the LR parsing engine, plus some additional
# debugging information.
class MiniProduction(object):
    def __init__(self,str,name,len,func,file,line):
        self.name     = name
        self.len      = len
        self.func     = func
        self.callable = None
        self.file     = file
        self.line     = line
        self.str      = str
    def __str__(self):
        return self.str
    def __repr__(self):
        return "MiniProduction(%s)" % self.str

    # Bind the production function name to a callable
    def bind(self,pdict):
        if self.func:
            self.callable = pdict[self.func]


# -----------------------------------------------------------------------------
# class LRItem
#
# This class represents a specific stage of parsing a production rule.  For
# example: 
#
#       expr : expr . PLUS term 
#
# In the above, the "." represents the current location of the parse.  Here
# basic attributes:
#
#       name       - Name of the production.  For example 'expr'
#       prod       - A list of symbols on the right side ['expr','.', 'PLUS','term']
#       number     - Production number.
#
#       lr_next      Next LR item. Example, if we are ' expr -> expr . PLUS term'
#                    then lr_next refers to 'expr -> expr PLUS . term'
#       lr_index   - LR item index (location of the ".") in the prod list.
#       lookaheads - LALR lookahead symbols for this item
#       len        - Length of the production (number of symbols on right hand side)
#       lr_after    - List of all productions that immediately follow
#       lr_before   - Grammar symbol immediately before
# -----------------------------------------------------------------------------

class LRItem(object):
    def __init__(self,p,n):
        self.name       = p.name
        self.prod       = list(p.prod)
        self.number     = p.number
        self.lr_index   = n
        self.lookaheads = { }
        self.prod.insert(n,".")
        self.prod       = tuple(self.prod)
        self.len        = len(self.prod)
        self.usyms      = p.usyms

    def __str__(self):
        if self.prod:
            s = "%s -> %s" % (self.name," ".join(self.prod))
        else:
            s = "%s -> <empty>" % self.name
        return s

    def __repr__(self):
        return "LRItem("+str(self)+")"

# -----------------------------------------------------------------------------
# rightmost_terminal()
#
# Return the rightmost terminal from a list of symbols.  Used in add_production()
# -----------------------------------------------------------------------------
def rightmost_terminal(symbols, terminals):
    i = len(symbols) - 1
    while i >= 0:
        if symbols[i] in terminals:
            return symbols[i]
        i -= 1
    return None

# -----------------------------------------------------------------------------
#                           === GRAMMAR CLASS ===
#
# The following class represents the contents of the specified grammar along
# with various computed properties such as first sets, follow sets, LR items, etc.
# This data is used for critical parts of the table generation process later.
# -----------------------------------------------------------------------------

class GrammarError(YaccError): pass

class Grammar(object):
    def __init__(self,terminals):
        self.Productions  = [None]  # A list of all of the productions.  The first
                                    # entry is always reserved for the purpose of
                                    # building an augmented grammar

        self.Prodnames    = { }     # A dictionary mapping the names of nonterminals to a list of all
                                    # productions of that nonterminal.

        self.Prodmap      = { }     # A dictionary that is only used to detect duplicate
                                    # productions.

        self.Terminals    = { }     # A dictionary mapping the names of terminal symbols to a
                                    # list of the rules where they are used.

        for term in terminals:
            self.Terminals[term] = []

        self.Terminals['error'] = []

        self.Nonterminals = { }     # A dictionary mapping names of nonterminals to a list
                                    # of rule numbers where they are used.

        self.First        = { }     # A dictionary of precomputed FIRST(x) symbols

        self.Follow       = { }     # A dictionary of precomputed FOLLOW(x) symbols

        self.Precedence   = { }     # Precedence rules for each terminal. Contains tuples of the
                                    # form ('right',level) or ('nonassoc', level) or ('left',level)

        self.UsedPrecedence = { }   # Precedence rules that were actually used by the grammer.
                                    # This is only used to provide error checking and to generate
                                    # a warning about unused precedence rules.

        self.Start = None           # Starting symbol for the grammar


    def __len__(self):
        return len(self.Productions)

    def __getitem__(self,index):
        return self.Productions[index]

    # -----------------------------------------------------------------------------
    # set_precedence()
    #
    # Sets the precedence for a given terminal. assoc is the associativity such as
    # 'left','right', or 'nonassoc'.  level is a numeric level.
    #
    # -----------------------------------------------------------------------------

    def set_precedence(self,term,assoc,level):
        assert self.Productions == [None],"Must call set_precedence() before add_production()"
        if term in self.Precedence:
            raise GrammarError("Precedence already specified for terminal '%s'" % term)
        if assoc not in ['left','right','nonassoc']:
            raise GrammarError("Associativity must be one of 'left','right', or 'nonassoc'")
        self.Precedence[term] = (assoc,level)
 
    # -----------------------------------------------------------------------------
    # add_production()
    #
    # Given an action function, this function assembles a production rule and
    # computes its precedence level.
    #
    # The production rule is supplied as a list of symbols.   For example,
    # a rule such as 'expr : expr PLUS term' has a production name of 'expr' and
    # symbols ['expr','PLUS','term'].
    #
    # Precedence is determined by the precedence of the right-most non-terminal
    # or the precedence of a terminal specified by %prec.
    #
    # A variety of error checks are performed to make sure production symbols
    # are valid and that %prec is used correctly.
    # -----------------------------------------------------------------------------

    def add_production(self,prodname,syms,func=None,file='',line=0):

        if prodname in self.Terminals:
            raise GrammarError("%s:%d: Illegal rule name '%s'. Already defined as a token" % (file,line,prodname))
        if prodname == 'error':
            raise GrammarError("%s:%d: Illegal rule name '%s'. error is a reserved word" % (file,line,prodname))
        if not _is_identifier.match(prodname):
            raise GrammarError("%s:%d: Illegal rule name '%s'" % (file,line,prodname))

        # Look for literal tokens 
        for n,s in enumerate(syms):
            if s[0] in "'\"":
                 try:
                     c = eval(s)
                     if (len(c) > 1):
                          raise GrammarError("%s:%d: Literal token %s in rule '%s' may only be a single character" % (file,line,s, prodname))
                     if not c in self.Terminals:
                          self.Terminals[c] = []
                     syms[n] = c
                     continue
                 except SyntaxError:
                     pass
            if not _is_identifier.match(s) and s != '%prec':
                raise GrammarError("%s:%d: Illegal name '%s' in rule '%s'" % (file,line,s, prodname))
        
        # Determine the precedence level
        if '%prec' in syms:
            if syms[-1] == '%prec':
                raise GrammarError("%s:%d: Syntax error. Nothing follows %%prec" % (file,line))
            if syms[-2] != '%prec':
                raise GrammarError("%s:%d: Syntax error. %%prec can only appear at the end of a grammar rule" % (file,line))
            precname = syms[-1]
            prodprec = self.Precedence.get(precname,None)
            if not prodprec:
                raise GrammarError("%s:%d: Nothing known about the precedence of '%s'" % (file,line,precname))
            else:
                self.UsedPrecedence[precname] = 1
            del syms[-2:]     # Drop %prec from the rule
        else:
            # If no %prec, precedence is determined by the rightmost terminal symbol
            precname = rightmost_terminal(syms,self.Terminals)
            prodprec = self.Precedence.get(precname,('right',0)) 
            
        # See if the rule is already in the rulemap
        map = "%s -> %s" % (prodname,syms)
        if map in self.Prodmap:
            m = self.Prodmap[map]
            raise GrammarError("%s:%d: Duplicate rule %s. " % (file,line, m) +
                               "Previous definition at %s:%d" % (m.file, m.line))

        # From this point on, everything is valid.  Create a new Production instance
        pnumber  = len(self.Productions)
        if not prodname in self.Nonterminals:
            self.Nonterminals[prodname] = [ ]

        # Add the production number to Terminals and Nonterminals
        for t in syms:
            if t in self.Terminals:
                self.Terminals[t].append(pnumber)
            else:
                if not t in self.Nonterminals:
                    self.Nonterminals[t] = [ ]
                self.Nonterminals[t].append(pnumber)

        # Create a production and add it to the list of productions
        p = Production(pnumber,prodname,syms,prodprec,func,file,line)
        self.Productions.append(p)
        self.Prodmap[map] = p

        # Add to the global productions list
        try:
            self.Prodnames[prodname].append(p)
        except KeyError:
            self.Prodnames[prodname] = [ p ]
        return 0

    # -----------------------------------------------------------------------------
    # set_start()
    #
    # Sets the starting symbol and creates the augmented grammar.  Production 
    # rule 0 is S' -> start where start is the start symbol.
    # -----------------------------------------------------------------------------

    def set_start(self,start=None):
        if not start:
            start = self.Productions[1].name
        if start not in self.Nonterminals:
            raise GrammarError("start symbol %s undefined" % start)
        self.Productions[0] = Production(0,"S'",[start])
        self.Nonterminals[start].append(0)
        self.Start = start

    # -----------------------------------------------------------------------------
    # find_unreachable()
    #
    # Find all of the nonterminal symbols that can't be reached from the starting
    # symbol.  Returns a list of nonterminals that can't be reached.
    # -----------------------------------------------------------------------------

    def find_unreachable(self):
        
        # Mark all symbols that are reachable from a symbol s
        def mark_reachable_from(s):
            if reachable[s]:
                # We've already reached symbol s.
                return
            reachable[s] = 1
            for p in self.Prodnames.get(s,[]):
                for r in p.prod:
                    mark_reachable_from(r)

        reachable   = { }
        for s in list(self.Terminals) + list(self.Nonterminals):
            reachable[s] = 0

        mark_reachable_from( self.Productions[0].prod[0] )

        return [s for s in list(self.Nonterminals)
                        if not reachable[s]]
    
    # -----------------------------------------------------------------------------
    # infinite_cycles()
    #
    # This function looks at the various parsing rules and tries to detect
    # infinite recursion cycles (grammar rules where there is no possible way
    # to derive a string of only terminals).
    # -----------------------------------------------------------------------------

    def infinite_cycles(self):
        terminates = {}

        # Terminals:
        for t in self.Terminals:
            terminates[t] = 1

        terminates['$end'] = 1

        # Nonterminals:

        # Initialize to false:
        for n in self.Nonterminals:
            terminates[n] = 0

        # Then propagate termination until no change:
        while 1:
            some_change = 0
            for (n,pl) in self.Prodnames.items():
                # Nonterminal n terminates iff any of its productions terminates.
                for p in pl:
                    # Production p terminates iff all of its rhs symbols terminate.
                    for s in p.prod:
                        if not terminates[s]:
                            # The symbol s does not terminate,
                            # so production p does not terminate.
                            p_terminates = 0
                            break
                    else:
                        # didn't break from the loop,
                        # so every symbol s terminates
                        # so production p terminates.
                        p_terminates = 1

                    if p_terminates:
                        # symbol n terminates!
                        if not terminates[n]:
                            terminates[n] = 1
                            some_change = 1
                        # Don't need to consider any more productions for this n.
                        break

            if not some_change:
                break

        infinite = []
        for (s,term) in terminates.items():
            if not term:
                if not s in self.Prodnames and not s in self.Terminals and s != 'error':
                    # s is used-but-not-defined, and we've already warned of that,
                    # so it would be overkill to say that it's also non-terminating.
                    pass
                else:
                    infinite.append(s)

        return infinite


    # -----------------------------------------------------------------------------
    # undefined_symbols()
    #
    # Find all symbols that were used the grammar, but not defined as tokens or
    # grammar rules.  Returns a list of tuples (sym, prod) where sym in the symbol
    # and prod is the production where the symbol was used. 
    # -----------------------------------------------------------------------------
    def undefined_symbols(self):
        result = []
        for p in self.Productions:
            if not p: continue

            for s in p.prod:
                if not s in self.Prodnames and not s in self.Terminals and s != 'error':
                    result.append((s,p))
        return result

    # -----------------------------------------------------------------------------
    # unused_terminals()
    #
    # Find all terminals that were defined, but not used by the grammar.  Returns
    # a list of all symbols.
    # -----------------------------------------------------------------------------
    def unused_terminals(self):
        unused_tok = []
        for s,v in self.Terminals.items():
            if s != 'error' and not v:
                unused_tok.append(s)

        return unused_tok

    # ------------------------------------------------------------------------------
    # unused_rules()
    #
    # Find all grammar rules that were defined,  but not used (maybe not reachable)
    # Returns a list of productions.
    # ------------------------------------------------------------------------------

    def unused_rules(self):
        unused_prod = []
        for s,v in self.Nonterminals.items():
            if not v:
                p = self.Prodnames[s][0]
                unused_prod.append(p)
        return unused_prod

    # -----------------------------------------------------------------------------
    # unused_precedence()
    #
    # Returns a list of tuples (term,precedence) corresponding to precedence
    # rules that were never used by the grammar.  term is the name of the terminal
    # on which precedence was applied and precedence is a string such as 'left' or
    # 'right' corresponding to the type of precedence. 
    # -----------------------------------------------------------------------------

    def unused_precedence(self):
        unused = []
        for termname in self.Precedence:
            if not (termname in self.Terminals or termname in self.UsedPrecedence):
                unused.append((termname,self.Precedence[termname][0]))
                
        return unused

    # -------------------------------------------------------------------------
    # _first()
    #
    # Compute the value of FIRST1(beta) where beta is a tuple of symbols.
    #
    # During execution of compute_first1, the result may be incomplete.
    # Afterward (e.g., when called from compute_follow()), it will be complete.
    # -------------------------------------------------------------------------
    def _first(self,beta):

        # We are computing First(x1,x2,x3,...,xn)
        result = [ ]
        for x in beta:
            x_produces_empty = 0

            # Add all the non-<empty> symbols of First[x] to the result.
            for f in self.First[x]:
                if f == '<empty>':
                    x_produces_empty = 1
                else:
                    if f not in result: result.append(f)

            if x_produces_empty:
                # We have to consider the next x in beta,
                # i.e. stay in the loop.
                pass
            else:
                # We don't have to consider any further symbols in beta.
                break
        else:
            # There was no 'break' from the loop,
            # so x_produces_empty was true for all x in beta,
            # so beta produces empty as well.
            result.append('<empty>')

        return result

    # -------------------------------------------------------------------------
    # compute_first()
    #
    # Compute the value of FIRST1(X) for all symbols
    # -------------------------------------------------------------------------
    def compute_first(self):
        if self.First:
            return self.First

        # Terminals:
        for t in self.Terminals:
            self.First[t] = [t]

        self.First['$end'] = ['$end']

        # Nonterminals:

        # Initialize to the empty set:
        for n in self.Nonterminals:
            self.First[n] = []

        # Then propagate symbols until no change:
        while 1:
            some_change = 0
            for n in self.Nonterminals:
                for p in self.Prodnames[n]:
                    for f in self._first(p.prod):
                        if f not in self.First[n]:
                            self.First[n].append( f )
                            some_change = 1
            if not some_change:
                break
        
        return self.First

    # ---------------------------------------------------------------------
    # compute_follow()
    #
    # Computes all of the follow sets for every non-terminal symbol.  The
    # follow set is the set of all symbols that might follow a given
    # non-terminal.  See the Dragon book, 2nd Ed. p. 189.
    # ---------------------------------------------------------------------
    def compute_follow(self,start=None):
        # If already computed, return the result
        if self.Follow:
            return self.Follow

        # If first sets not computed yet, do that first.
        if not self.First:
            self.compute_first()

        # Add '$end' to the follow list of the start symbol
        for k in self.Nonterminals:
            self.Follow[k] = [ ]

        if not start:
            start = self.Productions[1].name

        self.Follow[start] = [ '$end' ]

        while 1:
            didadd = 0
            for p in self.Productions[1:]:
                # Here is the production set
                for i in range(len(p.prod)):
                    B = p.prod[i]
                    if B in self.Nonterminals:
                        # Okay. We got a non-terminal in a production
                        fst = self._first(p.prod[i+1:])
                        hasempty = 0
                        for f in fst:
                            if f != '<empty>' and f not in self.Follow[B]:
                                self.Follow[B].append(f)
                                didadd = 1
                            if f == '<empty>':
                                hasempty = 1
                        if hasempty or i == (len(p.prod)-1):
                            # Add elements of follow(a) to follow(b)
                            for f in self.Follow[p.name]:
                                if f not in self.Follow[B]:
                                    self.Follow[B].append(f)
                                    didadd = 1
            if not didadd: break
        return self.Follow


    # -----------------------------------------------------------------------------
    # build_lritems()
    #
    # This function walks the list of productions and builds a complete set of the
    # LR items.  The LR items are stored in two ways:  First, they are uniquely
    # numbered and placed in the list _lritems.  Second, a linked list of LR items
    # is built for each production.  For example:
    #
    #   E -> E PLUS E
    #
    # Creates the list
    #
    #  [E -> . E PLUS E, E -> E . PLUS E, E -> E PLUS . E, E -> E PLUS E . ]
    # -----------------------------------------------------------------------------

    def build_lritems(self):
        for p in self.Productions:
            lastlri = p
            i = 0
            lr_items = []
            while 1:
                if i > len(p):
                    lri = None
                else:
                    lri = LRItem(p,i)
                    # Precompute the list of productions immediately following
                    try:
                        lri.lr_after = self.Prodnames[lri.prod[i+1]]
                    except (IndexError,KeyError):
                        lri.lr_after = []
                    try:
                        lri.lr_before = lri.prod[i-1]
                    except IndexError:
                        lri.lr_before = None

                lastlri.lr_next = lri
                if not lri: break
                lr_items.append(lri)
                lastlri = lri
                i += 1
            p.lr_items = lr_items

# -----------------------------------------------------------------------------
#                            == Class LRTable ==
#
# This basic class represents a basic table of LR parsing information.  
# Methods for generating the tables are not defined here.  They are defined
# in the derived class LRGeneratedTable.
# -----------------------------------------------------------------------------

class VersionError(YaccError): pass

class LRTable(object):
    def __init__(self):
        self.lr_action = None
        self.lr_goto = None
        self.lr_productions = None
        self.lr_method = None

    def read_table(self,module):
        if isinstance(module,types.ModuleType):
            parsetab = module
        else:
            if sys.version_info[0] < 3:
                exec("import %s as parsetab" % module)
            else:
                env = { }
                exec("import %s as parsetab" % module, env, env)
                parsetab = env['parsetab']

        if parsetab._tabversion != __tabversion__:
            raise VersionError("yacc table file version is out of date")

        self.lr_action = parsetab._lr_action
        self.lr_goto = parsetab._lr_goto

        self.lr_productions = []
        for p in parsetab._lr_productions:
            self.lr_productions.append(MiniProduction(*p))

        self.lr_method = parsetab._lr_method
        return parsetab._lr_signature

    def read_pickle(self,filename):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle

        in_f = open(filename,"rb")

        tabversion = pickle.load(in_f)
        if tabversion != __tabversion__:
            raise VersionError("yacc table file version is out of date")
        self.lr_method = pickle.load(in_f)
        signature      = pickle.load(in_f)
        self.lr_action = pickle.load(in_f)
        self.lr_goto   = pickle.load(in_f)
        productions    = pickle.load(in_f)

        self.lr_productions = []
        for p in productions:
            self.lr_productions.append(MiniProduction(*p))

        in_f.close()
        return signature

    # Bind all production function names to callable objects in pdict
    def bind_callables(self,pdict):
        for p in self.lr_productions:
            p.bind(pdict)
    
# -----------------------------------------------------------------------------
#                           === LR Generator ===
#
# The following classes and functions are used to generate LR parsing tables on 
# a grammar.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# digraph()
# traverse()
#
# The following two functions are used to compute set valued functions
# of the form:
#
#     F(x) = F'(x) U U{F(y) | x R y}
#
# This is used to compute the values of Read() sets as well as FOLLOW sets
# in LALR(1) generation.
#
# Inputs:  X    - An input set
#          R    - A relation
#          FP   - Set-valued function
# ------------------------------------------------------------------------------

def digraph(X,R,FP):
    N = { }
    for x in X:
       N[x] = 0
    stack = []
    F = { }
    for x in X:
        if N[x] == 0: traverse(x,N,stack,F,X,R,FP)
    return F

def traverse(x,N,stack,F,X,R,FP):
    stack.append(x)
    d = len(stack)
    N[x] = d
    F[x] = FP(x)             # F(X) <- F'(x)

    rel = R(x)               # Get y's related to x
    for y in rel:
        if N[y] == 0:
             traverse(y,N,stack,F,X,R,FP)
        N[x] = min(N[x],N[y])
        for a in F.get(y,[]):
            if a not in F[x]: F[x].append(a)
    if N[x] == d:
       N[stack[-1]] = MAXINT
       F[stack[-1]] = F[x]
       element = stack.pop()
       while element != x:
           N[stack[-1]] = MAXINT
           F[stack[-1]] = F[x]
           element = stack.pop()

class LALRError(YaccError): pass

# -----------------------------------------------------------------------------
#                             == LRGeneratedTable ==
#
# This class implements the LR table generation algorithm.  There are no
# public methods except for write()
# -----------------------------------------------------------------------------

class LRGeneratedTable(LRTable):
    def __init__(self,grammar,method='LALR',log=None):
        if method not in ['SLR','LALR']:
            raise LALRError("Unsupported method %s" % method)

        self.grammar = grammar
        self.lr_method = method

        # Set up the logger
        if not log:
            log = NullLogger()
        self.log = log

        # Internal attributes
        self.lr_action     = {}        # Action table
        self.lr_goto       = {}        # Goto table
        self.lr_productions  = grammar.Productions    # Copy of grammar Production array
        self.lr_goto_cache = {}        # Cache of computed gotos
        self.lr0_cidhash   = {}        # Cache of closures

        self._add_count    = 0         # Internal counter used to detect cycles

        # Diagonistic information filled in by the table generator
        self.sr_conflict   = 0
        self.rr_conflict   = 0
        self.conflicts     = []        # List of conflicts

        self.sr_conflicts  = []
        self.rr_conflicts  = []

        # Build the tables
        self.grammar.build_lritems()
        self.grammar.compute_first()
        self.grammar.compute_follow()
        self.lr_parse_table()

    # Compute the LR(0) closure operation on I, where I is a set of LR(0) items.

    def lr0_closure(self,I):
        self._add_count += 1

        # Add everything in I to J
        J = I[:]
        didadd = 1
        while didadd:
            didadd = 0
            for j in J:
                for x in j.lr_after:
                    if getattr(x,"lr0_added",0) == self._add_count: continue
                    # Add B --> .G to J
                    J.append(x.lr_next)
                    x.lr0_added = self._add_count
                    didadd = 1

        return J

    # Compute the LR(0) goto function goto(I,X) where I is a set
    # of LR(0) items and X is a grammar symbol.   This function is written
    # in a way that guarantees uniqueness of the generated goto sets
    # (i.e. the same goto set will never be returned as two different Python
    # objects).  With uniqueness, we can later do fast set comparisons using
    # id(obj) instead of element-wise comparison.

    def lr0_goto(self,I,x):
        # First we look for a previously cached entry
        g = self.lr_goto_cache.get((id(I),x),None)
        if g: return g

        # Now we generate the goto set in a way that guarantees uniqueness
        # of the result

        s = self.lr_goto_cache.get(x,None)
        if not s:
            s = { }
            self.lr_goto_cache[x] = s

        gs = [ ]
        for p in I:
            n = p.lr_next
            if n and n.lr_before == x:
                s1 = s.get(id(n),None)
                if not s1:
                    s1 = { }
                    s[id(n)] = s1
                gs.append(n)
                s = s1
        g = s.get('$end',None)
        if not g:
            if gs:
                g = self.lr0_closure(gs)
                s['$end'] = g
            else:
                s['$end'] = gs
        self.lr_goto_cache[(id(I),x)] = g
        return g

    # Compute the LR(0) sets of item function
    def lr0_items(self):

        C = [ self.lr0_closure([self.grammar.Productions[0].lr_next]) ]
        i = 0
        for I in C:
            self.lr0_cidhash[id(I)] = i
            i += 1

        # Loop over the items in C and each grammar symbols
        i = 0
        while i < len(C):
            I = C[i]
            i += 1

            # Collect all of the symbols that could possibly be in the goto(I,X) sets
            asyms = { }
            for ii in I:
                for s in ii.usyms:
                    asyms[s] = None

            for x in asyms:
                g = self.lr0_goto(I,x)
                if not g:  continue
                if id(g) in self.lr0_cidhash: continue
                self.lr0_cidhash[id(g)] = len(C)
                C.append(g)

        return C

    # -----------------------------------------------------------------------------
    #                       ==== LALR(1) Parsing ====
    #
    # LALR(1) parsing is almost exactly the same as SLR except that instead of
    # relying upon Follow() sets when performing reductions, a more selective
    # lookahead set that incorporates the state of the LR(0) machine is utilized.
    # Thus, we mainly just have to focus on calculating the lookahead sets.
    #
    # The method used here is due to DeRemer and Pennelo (1982).
    #
    # DeRemer, F. L., and T. J. Pennelo: "Efficient Computation of LALR(1)
    #     Lookahead Sets", ACM Transactions on Programming Languages and Systems,
    #     Vol. 4, No. 4, Oct. 1982, pp. 615-649
    #
    # Further details can also be found in:
    #
    #  J. Tremblay and P. Sorenson, "The Theory and Practice of Compiler Writing",
    #      McGraw-Hill Book Company, (1985).
    #
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    # compute_nullable_nonterminals()
    #
    # Creates a dictionary containing all of the non-terminals that might produce
    # an empty production.
    # -----------------------------------------------------------------------------

    def compute_nullable_nonterminals(self):
        nullable = {}
        num_nullable = 0
        while 1:
           for p in self.grammar.Productions[1:]:
               if p.len == 0:
                    nullable[p.name] = 1
                    continue
               for t in p.prod:
                    if not t in nullable: break
               else:
                    nullable[p.name] = 1
           if len(nullable) == num_nullable: break
           num_nullable = len(nullable)
        return nullable

    # -----------------------------------------------------------------------------
    # find_nonterminal_trans(C)
    #
    # Given a set of LR(0) items, this functions finds all of the non-terminal
    # transitions.    These are transitions in which a dot appears immediately before
    # a non-terminal.   Returns a list of tuples of the form (state,N) where state
    # is the state number and N is the nonterminal symbol.
    #
    # The input C is the set of LR(0) items.
    # -----------------------------------------------------------------------------

    def find_nonterminal_transitions(self,C):
         trans = []
         for state in range(len(C)):
             for p in C[state]:
                 if p.lr_index < p.len - 1:
                      t = (state,p.prod[p.lr_index+1])
                      if t[1] in self.grammar.Nonterminals:
                            if t not in trans: trans.append(t)
             state = state + 1
         return trans

    # -----------------------------------------------------------------------------
    # dr_relation()
    #
    # Computes the DR(p,A) relationships for non-terminal transitions.  The input
    # is a tuple (state,N) where state is a number and N is a nonterminal symbol.
    #
    # Returns a list of terminals.
    # -----------------------------------------------------------------------------

    def dr_relation(self,C,trans,nullable):
        dr_set = { }
        state,N = trans
        terms = []

        g = self.lr0_goto(C[state],N)
        for p in g:
           if p.lr_index < p.len - 1:
               a = p.prod[p.lr_index+1]
               if a in self.grammar.Terminals:
                   if a not in terms: terms.append(a)

        # This extra bit is to handle the start state
        if state == 0 and N == self.grammar.Productions[0].prod[0]:
           terms.append('$end')

        return terms

    # -----------------------------------------------------------------------------
    # reads_relation()
    #
    # Computes the READS() relation (p,A) READS (t,C).
    # -----------------------------------------------------------------------------

    def reads_relation(self,C, trans, empty):
        # Look for empty transitions
        rel = []
        state, N = trans

        g = self.lr0_goto(C[state],N)
        j = self.lr0_cidhash.get(id(g),-1)
        for p in g:
            if p.lr_index < p.len - 1:
                 a = p.prod[p.lr_index + 1]
                 if a in empty:
                      rel.append((j,a))

        return rel

    # -----------------------------------------------------------------------------
    # compute_lookback_includes()
    #
    # Determines the lookback and includes relations
    #
    # LOOKBACK:
    #
    # This relation is determined by running the LR(0) state machine forward.
    # For example, starting with a production "N : . A B C", we run it forward
    # to obtain "N : A B C ."   We then build a relationship between this final
    # state and the starting state.   These relationships are stored in a dictionary
    # lookdict.
    #
    # INCLUDES:
    #
    # Computes the INCLUDE() relation (p,A) INCLUDES (p',B).
    #
    # This relation is used to determine non-terminal transitions that occur
    # inside of other non-terminal transition states.   (p,A) INCLUDES (p', B)
    # if the following holds:
    #
    #       B -> LAT, where T -> epsilon and p' -L-> p
    #
    # L is essentially a prefix (which may be empty), T is a suffix that must be
    # able to derive an empty string.  State p' must lead to state p with the string L.
    #
    # -----------------------------------------------------------------------------

    def compute_lookback_includes(self,C,trans,nullable):

        lookdict = {}          # Dictionary of lookback relations
        includedict = {}       # Dictionary of include relations

        # Make a dictionary of non-terminal transitions
        dtrans = {}
        for t in trans:
            dtrans[t] = 1

        # Loop over all transitions and compute lookbacks and includes
        for state,N in trans:
            lookb = []
            includes = []
            for p in C[state]:
                if p.name != N: continue

                # Okay, we have a name match.  We now follow the production all the way
                # through the state machine until we get the . on the right hand side

                lr_index = p.lr_index
                j = state
                while lr_index < p.len - 1:
                     lr_index = lr_index + 1
                     t = p.prod[lr_index]

                     # Check to see if this symbol and state are a non-terminal transition
                     if (j,t) in dtrans:
                           # Yes.  Okay, there is some chance that this is an includes relation
                           # the only way to know for certain is whether the rest of the
                           # production derives empty

                           li = lr_index + 1
                           while li < p.len:
                                if p.prod[li] in self.grammar.Terminals: break      # No forget it
                                if not p.prod[li] in nullable: break
                                li = li + 1
                           else:
                                # Appears to be a relation between (j,t) and (state,N)
                                includes.append((j,t))

                     g = self.lr0_goto(C[j],t)               # Go to next set
                     j = self.lr0_cidhash.get(id(g),-1)     # Go to next state

                # When we get here, j is the final state, now we have to locate the production
                for r in C[j]:
                     if r.name != p.name: continue
                     if r.len != p.len:   continue
                     i = 0
                     # This look is comparing a production ". A B C" with "A B C ."
                     while i < r.lr_index:
                          if r.prod[i] != p.prod[i+1]: break
                          i = i + 1
                     else:
                          lookb.append((j,r))
            for i in includes:
                 if not i in includedict: includedict[i] = []
                 includedict[i].append((state,N))
            lookdict[(state,N)] = lookb

        return lookdict,includedict

    # -----------------------------------------------------------------------------
    # compute_read_sets()
    #
    # Given a set of LR(0) items, this function computes the read sets.
    #
    # Inputs:  C        =  Set of LR(0) items
    #          ntrans   = Set of nonterminal transitions
    #          nullable = Set of empty transitions
    #
    # Returns a set containing the read sets
    # -----------------------------------------------------------------------------

    def compute_read_sets(self,C, ntrans, nullable):
        FP = lambda x: self.dr_relation(C,x,nullable)
        R =  lambda x: self.reads_relation(C,x,nullable)
        F = digraph(ntrans,R,FP)
        return F

    # -----------------------------------------------------------------------------
    # compute_follow_sets()
    #
    # Given a set of LR(0) items, a set of non-terminal transitions, a readset,
    # and an include set, this function computes the follow sets
    #
    # Follow(p,A) = Read(p,A) U U {Follow(p',B) | (p,A) INCLUDES (p',B)}
    #
    # Inputs:
    #            ntrans     = Set of nonterminal transitions
    #            readsets   = Readset (previously computed)
    #            inclsets   = Include sets (previously computed)
    #
    # Returns a set containing the follow sets
    # -----------------------------------------------------------------------------

    def compute_follow_sets(self,ntrans,readsets,inclsets):
         FP = lambda x: readsets[x]
         R  = lambda x: inclsets.get(x,[])
         F = digraph(ntrans,R,FP)
         return F

    # -----------------------------------------------------------------------------
    # add_lookaheads()
    #
    # Attaches the lookahead symbols to grammar rules.
    #
    # Inputs:    lookbacks         -  Set of lookback relations
    #            followset         -  Computed follow set
    #
    # This function directly attaches the lookaheads to productions contained
    # in the lookbacks set
    # -----------------------------------------------------------------------------

    def add_lookaheads(self,lookbacks,followset):
        for trans,lb in lookbacks.items():
            # Loop over productions in lookback
            for state,p in lb:
                 if not state in p.lookaheads:
                      p.lookaheads[state] = []
                 f = followset.get(trans,[])
                 for a in f:
                      if a not in p.lookaheads[state]: p.lookaheads[state].append(a)

    # -----------------------------------------------------------------------------
    # add_lalr_lookaheads()
    #
    # This function does all of the work of adding lookahead information for use
    # with LALR parsing
    # -----------------------------------------------------------------------------

    def add_lalr_lookaheads(self,C):
        # Determine all of the nullable nonterminals
        nullable = self.compute_nullable_nonterminals()

        # Find all non-terminal transitions
        trans = self.find_nonterminal_transitions(C)

        # Compute read sets
        readsets = self.compute_read_sets(C,trans,nullable)

        # Compute lookback/includes relations
        lookd, included = self.compute_lookback_includes(C,trans,nullable)

        # Compute LALR FOLLOW sets
        followsets = self.compute_follow_sets(trans,readsets,included)

        # Add all of the lookaheads
        self.add_lookaheads(lookd,followsets)

    # -----------------------------------------------------------------------------
    # lr_parse_table()
    #
    # This function constructs the parse tables for SLR or LALR
    # -----------------------------------------------------------------------------
    def lr_parse_table(self):
        Productions = self.grammar.Productions
        Precedence  = self.grammar.Precedence
        goto   = self.lr_goto         # Goto array
        action = self.lr_action       # Action array
        log    = self.log             # Logger for output

        actionp = { }                 # Action production array (temporary)
        
        log.info("Parsing method: %s", self.lr_method)

        # Step 1: Construct C = { I0, I1, ... IN}, collection of LR(0) items
        # This determines the number of states

        C = self.lr0_items()

        if self.lr_method == 'LALR':
            self.add_lalr_lookaheads(C)

        # Build the parser table, state by state
        st = 0
        for I in C:
            # Loop over each production in I
            actlist = [ ]              # List of actions
            st_action  = { }
            st_actionp = { }
            st_goto    = { }
            log.info("")
            log.info("state %d", st)
            log.info("")
            for p in I:
                log.info("    (%d) %s", p.number, str(p))
            log.info("")

            for p in I:
                    if p.len == p.lr_index + 1:
                        if p.name == "S'":
                            # Start symbol. Accept!
                            st_action["$end"] = 0
                            st_actionp["$end"] = p
                        else:
                            # We are at the end of a production.  Reduce!
                            if self.lr_method == 'LALR':
                                laheads = p.lookaheads[st]
                            else:
                                laheads = self.grammar.Follow[p.name]
                            for a in laheads:
                                actlist.append((a,p,"reduce using rule %d (%s)" % (p.number,p)))
                                r = st_action.get(a,None)
                                if r is not None:
                                    # Whoa. Have a shift/reduce or reduce/reduce conflict
                                    if r > 0:
                                        # Need to decide on shift or reduce here
                                        # By default we favor shifting. Need to add
                                        # some precedence rules here.
                                        sprec,slevel = Productions[st_actionp[a].number].prec
                                        rprec,rlevel = Precedence.get(a,('right',0))
                                        if (slevel < rlevel) or ((slevel == rlevel) and (rprec == 'left')):
                                            # We really need to reduce here.
                                            st_action[a] = -p.number
                                            st_actionp[a] = p
                                            if not slevel and not rlevel:
                                                log.info("  ! shift/reduce conflict for %s resolved as reduce",a)
                                                self.sr_conflicts.append((st,a,'reduce'))
                                            Productions[p.number].reduced += 1
                                        elif (slevel == rlevel) and (rprec == 'nonassoc'):
                                            st_action[a] = None
                                        else:
                                            # Hmmm. Guess we'll keep the shift
                                            if not rlevel:
                                                log.info("  ! shift/reduce conflict for %s resolved as shift",a)
                                                self.sr_conflicts.append((st,a,'shift'))
                                    elif r < 0:
                                        # Reduce/reduce conflict.   In this case, we favor the rule
                                        # that was defined first in the grammar file
                                        oldp = Productions[-r]
                                        pp = Productions[p.number]
                                        if oldp.line > pp.line:
                                            st_action[a] = -p.number
                                            st_actionp[a] = p
                                            chosenp,rejectp = pp,oldp
                                            Productions[p.number].reduced += 1
                                            Productions[oldp.number].reduced -= 1
                                        else:
                                            chosenp,rejectp = oldp,pp
                                        self.rr_conflicts.append((st,chosenp,rejectp))
                                        log.info("  ! reduce/reduce conflict for %s resolved using rule %d (%s)", a,st_actionp[a].number, st_actionp[a])
                                    else:
                                        raise LALRError("Unknown conflict in state %d" % st)
                                else:
                                    st_action[a] = -p.number
                                    st_actionp[a] = p
                                    Productions[p.number].reduced += 1
                    else:
                        i = p.lr_index
                        a = p.prod[i+1]       # Get symbol right after the "."
                        if a in self.grammar.Terminals:
                            g = self.lr0_goto(I,a)
                            j = self.lr0_cidhash.get(id(g),-1)
                            if j >= 0:
                                # We are in a shift state
                                actlist.append((a,p,"shift and go to state %d" % j))
                                r = st_action.get(a,None)
                                if r is not None:
                                    # Whoa have a shift/reduce or shift/shift conflict
                                    if r > 0:
                                        if r != j:
                                            raise LALRError("Shift/shift conflict in state %d" % st)
                                    elif r < 0:
                                        # Do a precedence check.
                                        #   -  if precedence of reduce rule is higher, we reduce.
                                        #   -  if precedence of reduce is same and left assoc, we reduce.
                                        #   -  otherwise we shift
                                        rprec,rlevel = Productions[st_actionp[a].number].prec
                                        sprec,slevel = Precedence.get(a,('right',0))
                                        if (slevel > rlevel) or ((slevel == rlevel) and (rprec == 'right')):
                                            # We decide to shift here... highest precedence to shift
                                            Productions[st_actionp[a].number].reduced -= 1
                                            st_action[a] = j
                                            st_actionp[a] = p
                                            if not rlevel:
                                                log.info("  ! shift/reduce conflict for %s resolved as shift",a)
                                                self.sr_conflicts.append((st,a,'shift'))
                                        elif (slevel == rlevel) and (rprec == 'nonassoc'):
                                            st_action[a] = None
                                        else:
                                            # Hmmm. Guess we'll keep the reduce
                                            if not slevel and not rlevel:
                                                log.info("  ! shift/reduce conflict for %s resolved as reduce",a)
                                                self.sr_conflicts.append((st,a,'reduce'))

                                    else:
                                        raise LALRError("Unknown conflict in state %d" % st)
                                else:
                                    st_action[a] = j
                                    st_actionp[a] = p

            # Print the actions associated with each terminal
            _actprint = { }
            for a,p,m in actlist:
                if a in st_action:
                    if p is st_actionp[a]:
                        log.info("    %-15s %s",a,m)
                        _actprint[(a,m)] = 1
            log.info("")
            # Print the actions that were not used. (debugging)
            not_used = 0
            for a,p,m in actlist:
                if a in st_action:
                    if p is not st_actionp[a]:
                        if not (a,m) in _actprint:
                            log.debug("  ! %-15s [ %s ]",a,m)
                            not_used = 1
                            _actprint[(a,m)] = 1
            if not_used:
                log.debug("")

            # Construct the goto table for this state

            nkeys = { }
            for ii in I:
                for s in ii.usyms:
                    if s in self.grammar.Nonterminals:
                        nkeys[s] = None
            for n in nkeys:
                g = self.lr0_goto(I,n)
                j = self.lr0_cidhash.get(id(g),-1)
                if j >= 0:
                    st_goto[n] = j
                    log.info("    %-30s shift and go to state %d",n,j)

            action[st] = st_action
            actionp[st] = st_actionp
            goto[st] = st_goto
            st += 1


    # -----------------------------------------------------------------------------
    # write()
    #
    # This function writes the LR parsing tables to a file
    # -----------------------------------------------------------------------------

    def write_table(self,modulename,outputdir='',signature=""):
        basemodulename = modulename.split(".")[-1]
        filename = os.path.join(outputdir,basemodulename) + ".py"
        try:
            f = open(filename,"w")

            f.write("""
# %s
# This file is automatically generated. Do not edit.
_tabversion = %r

_lr_method = %r

_lr_signature = %r
    """ % (filename, __tabversion__, self.lr_method, signature))

            # Change smaller to 0 to go back to original tables
            smaller = 1

            # Factor out names to try and make smaller
            if smaller:
                items = { }

                for s,nd in self.lr_action.items():
                   for name,v in nd.items():
                      i = items.get(name)
                      if not i:
                         i = ([],[])
                         items[name] = i
                      i[0].append(s)
                      i[1].append(v)

                f.write("\n_lr_action_items = {")
                for k,v in items.items():
                    f.write("%r:([" % k)
                    for i in v[0]:
                        f.write("%r," % i)
                    f.write("],[")
                    for i in v[1]:
                        f.write("%r," % i)

                    f.write("]),")
                f.write("}\n")

                f.write("""
_lr_action = { }
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = { }
      _lr_action[_x][_k] = _y
del _lr_action_items
""")

            else:
                f.write("\n_lr_action = { ");
                for k,v in self.lr_action.items():
                    f.write("(%r,%r):%r," % (k[0],k[1],v))
                f.write("}\n");

            if smaller:
                # Factor out names to try and make smaller
                items = { }

                for s,nd in self.lr_goto.items():
                   for name,v in nd.items():
                      i = items.get(name)
                      if not i:
                         i = ([],[])
                         items[name] = i
                      i[0].append(s)
                      i[1].append(v)

                f.write("\n_lr_goto_items = {")
                for k,v in items.items():
                    f.write("%r:([" % k)
                    for i in v[0]:
                        f.write("%r," % i)
                    f.write("],[")
                    for i in v[1]:
                        f.write("%r," % i)

                    f.write("]),")
                f.write("}\n")

                f.write("""
_lr_goto = { }
for _k, _v in _lr_goto_items.items():
   for _x,_y in zip(_v[0],_v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = { }
       _lr_goto[_x][_k] = _y
del _lr_goto_items
""")
            else:
                f.write("\n_lr_goto = { ");
                for k,v in self.lr_goto.items():
                    f.write("(%r,%r):%r," % (k[0],k[1],v))
                f.write("}\n");

            # Write production table
            f.write("_lr_productions = [\n")
            for p in self.lr_productions:
                if p.func:
                    f.write("  (%r,%r,%d,%r,%r,%d),\n" % (p.str,p.name, p.len, p.func,p.file,p.line))
                else:
                    f.write("  (%r,%r,%d,None,None,None),\n" % (str(p),p.name, p.len))
            f.write("]\n")
            f.close()

        except IOError:
            e = sys.exc_info()[1]
            sys.stderr.write("Unable to create '%s'\n" % filename)
            sys.stderr.write(str(e)+"\n")
            return


    # -----------------------------------------------------------------------------
    # pickle_table()
    #
    # This function pickles the LR parsing tables to a supplied file object
    # -----------------------------------------------------------------------------

    def pickle_table(self,filename,signature=""):
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
        outf = open(filename,"wb")
        pickle.dump(__tabversion__,outf,pickle_protocol)
        pickle.dump(self.lr_method,outf,pickle_protocol)
        pickle.dump(signature,outf,pickle_protocol)
        pickle.dump(self.lr_action,outf,pickle_protocol)
        pickle.dump(self.lr_goto,outf,pickle_protocol)

        outp = []
        for p in self.lr_productions:
            if p.func:
                outp.append((p.str,p.name, p.len, p.func,p.file,p.line))
            else:
                outp.append((str(p),p.name,p.len,None,None,None))
        pickle.dump(outp,outf,pickle_protocol)
        outf.close()

# -----------------------------------------------------------------------------
#                            === INTROSPECTION ===
#
# The following functions and classes are used to implement the PLY
# introspection features followed by the yacc() function itself.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# get_caller_module_dict()
#
# This function returns a dictionary containing all of the symbols defined within
# a caller further down the call stack.  This is used to get the environment
# associated with the yacc() call if none was provided.
# -----------------------------------------------------------------------------

def get_caller_module_dict(levels):
    try:
        raise RuntimeError
    except RuntimeError:
        e,b,t = sys.exc_info()
        f = t.tb_frame
        while levels > 0:
            f = f.f_back                   
            levels -= 1
        ldict = f.f_globals.copy()
        if f.f_globals != f.f_locals:
            ldict.update(f.f_locals)

        return ldict

# -----------------------------------------------------------------------------
# parse_grammar()
#
# This takes a raw grammar rule string and parses it into production data
# -----------------------------------------------------------------------------
def parse_grammar(doc,file,line):
    grammar = []
    # Split the doc string into lines
    pstrings = doc.splitlines()
    lastp = None
    dline = line
    for ps in pstrings:
        dline += 1
        p = ps.split()
        if not p: continue
        try:
            if p[0] == '|':
                # This is a continuation of a previous rule
                if not lastp:
                    raise SyntaxError("%s:%d: Misplaced '|'" % (file,dline))
                prodname = lastp
                syms = p[1:]
            else:
                prodname = p[0]
                lastp = prodname
                syms   = p[2:]
                assign = p[1]
                if assign != ':' and assign != '::=':
                    raise SyntaxError("%s:%d: Syntax error. Expected ':'" % (file,dline))

            grammar.append((file,dline,prodname,syms))
        except SyntaxError:
            raise
        except Exception:
            raise SyntaxError("%s:%d: Syntax error in rule '%s'" % (file,dline,ps.strip()))

    return grammar

# -----------------------------------------------------------------------------
# ParserReflect()
#
# This class represents information extracted for building a parser including
# start symbol, error function, tokens, precedence list, action functions,
# etc.
# -----------------------------------------------------------------------------
class ParserReflect(object):
    def __init__(self,pdict,log=None):
        self.pdict      = pdict
        self.start      = None
        self.error_func = None
        self.tokens     = None
        self.files      = {}
        self.grammar    = []
        self.error      = 0

        if log is None:
            self.log = PlyLogger(sys.stderr)
        else:
            self.log = log

    # Get all of the basic information
    def get_all(self):
        self.get_start()
        self.get_error_func()
        self.get_tokens()
        self.get_precedence()
        self.get_pfunctions()
        
    # Validate all of the information
    def validate_all(self):
        self.validate_start()
        self.validate_error_func()
        self.validate_tokens()
        self.validate_precedence()
        self.validate_pfunctions()
        self.validate_files()
        return self.error

    # Compute a signature over the grammar
    def signature(self):
        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        try:
            sig = md5()
            if self.start:
                sig.update(self.start.encode('latin-1'))
            if self.prec:
                sig.update("".join(["".join(p) for p in self.prec]).encode('latin-1'))
            if self.tokens:
                sig.update(" ".join(self.tokens).encode('latin-1'))
            for f in self.pfuncs:
                if f[3]:
                    sig.update(f[3].encode('latin-1'))
        except (TypeError,ValueError):
            pass
        return sig.digest()

    # -----------------------------------------------------------------------------
    # validate_file()
    #
    # This method checks to see if there are duplicated p_rulename() functions
    # in the parser module file.  Without this function, it is really easy for
    # users to make mistakes by cutting and pasting code fragments (and it's a real
    # bugger to try and figure out why the resulting parser doesn't work).  Therefore,
    # we just do a little regular expression pattern matching of def statements
    # to try and detect duplicates.
    # -----------------------------------------------------------------------------

    def validate_files(self):
        # Match def p_funcname(
        fre = re.compile(r'\s*def\s+(p_[a-zA-Z_0-9]*)\(')

        for filename in self.files.keys():
            base,ext = os.path.splitext(filename)
            if ext != '.py': return 1          # No idea. Assume it's okay.

            try:
                f = open(filename)
                lines = f.readlines()
                f.close()
            except IOError:
                continue

            counthash = { }
            for linen,l in enumerate(lines):
                linen += 1
                m = fre.match(l)
                if m:
                    name = m.group(1)
                    prev = counthash.get(name)
                    if not prev:
                        counthash[name] = linen
                    else:
                        self.log.warning("%s:%d: Function %s redefined. Previously defined on line %d", filename,linen,name,prev)

    # Get the start symbol
    def get_start(self):
        self.start = self.pdict.get('start')

    # Validate the start symbol
    def validate_start(self):
        if self.start is not None:
            if not isinstance(self.start,str):
                self.log.error("'start' must be a string")

    # Look for error handler
    def get_error_func(self):
        self.error_func = self.pdict.get('p_error')

    # Validate the error function
    def validate_error_func(self):
        if self.error_func:
            if isinstance(self.error_func,types.FunctionType):
                ismethod = 0
            elif isinstance(self.error_func, types.MethodType):
                ismethod = 1
            else:
                self.log.error("'p_error' defined, but is not a function or method")
                self.error = 1
                return

            eline = func_code(self.error_func).co_firstlineno
            efile = func_code(self.error_func).co_filename
            self.files[efile] = 1

            if (func_code(self.error_func).co_argcount != 1+ismethod):
                self.log.error("%s:%d: p_error() requires 1 argument",efile,eline)
                self.error = 1

    # Get the tokens map
    def get_tokens(self):
        tokens = self.pdict.get("tokens",None)
        if not tokens:
            self.log.error("No token list is defined")
            self.error = 1
            return

        if not isinstance(tokens,(list, tuple)):
            self.log.error("tokens must be a list or tuple")
            self.error = 1
            return
        
        if not tokens:
            self.log.error("tokens is empty")
            self.error = 1
            return

        self.tokens = tokens

    # Validate the tokens
    def validate_tokens(self):
        # Validate the tokens.
        if 'error' in self.tokens:
            self.log.error("Illegal token name 'error'. Is a reserved word")
            self.error = 1
            return

        terminals = {}
        for n in self.tokens:
            if n in terminals:
                self.log.warning("Token '%s' multiply defined", n)
            terminals[n] = 1

    # Get the precedence map (if any)
    def get_precedence(self):
        self.prec = self.pdict.get("precedence",None)

    # Validate and parse the precedence map
    def validate_precedence(self):
        preclist = []
        if self.prec:
            if not isinstance(self.prec,(list,tuple)):
                self.log.error("precedence must be a list or tuple")
                self.error = 1
                return
            for level,p in enumerate(self.prec):
                if not isinstance(p,(list,tuple)):
                    self.log.error("Bad precedence table")
                    self.error = 1
                    return

                if len(p) < 2:
                    self.log.error("Malformed precedence entry %s. Must be (assoc, term, ..., term)",p)
                    self.error = 1
                    return
                assoc = p[0]
                if not isinstance(assoc,str):
                    self.log.error("precedence associativity must be a string")
                    self.error = 1
                    return
                for term in p[1:]:
                    if not isinstance(term,str):
                        self.log.error("precedence items must be strings")
                        self.error = 1
                        return
                    preclist.append((term,assoc,level+1))
        self.preclist = preclist

    # Get all p_functions from the grammar
    def get_pfunctions(self):
        p_functions = []
        for name, item in self.pdict.items():
            if name[:2] != 'p_': continue
            if name == 'p_error': continue
            if isinstance(item,(types.FunctionType,types.MethodType)):
                line = func_code(item).co_firstlineno
                file = func_code(item).co_filename
                p_functions.append((line,file,name,item.__doc__))

        # Sort all of the actions by line number
        p_functions.sort()
        self.pfuncs = p_functions


    # Validate all of the p_functions
    def validate_pfunctions(self):
        grammar = []
        # Check for non-empty symbols
        if len(self.pfuncs) == 0:
            self.log.error("no rules of the form p_rulename are defined")
            self.error = 1
            return 
        
        for line, file, name, doc in self.pfuncs:
            func = self.pdict[name]
            if isinstance(func, types.MethodType):
                reqargs = 2
            else:
                reqargs = 1
            if func_code(func).co_argcount > reqargs:
                self.log.error("%s:%d: Rule '%s' has too many arguments",file,line,func.__name__)
                self.error = 1
            elif func_code(func).co_argcount < reqargs:
                self.log.error("%s:%d: Rule '%s' requires an argument",file,line,func.__name__)
                self.error = 1
            elif not func.__doc__:
                self.log.warning("%s:%d: No documentation string specified in function '%s' (ignored)",file,line,func.__name__)
            else:
                try:
                    parsed_g = parse_grammar(doc,file,line)
                    for g in parsed_g:
                        grammar.append((name, g))
                except SyntaxError:
                    e = sys.exc_info()[1]
                    self.log.error(str(e))
                    self.error = 1

                # Looks like a valid grammar rule
                # Mark the file in which defined.
                self.files[file] = 1

        # Secondary validation step that looks for p_ definitions that are not functions
        # or functions that look like they might be grammar rules.

        for n,v in self.pdict.items():
            if n[0:2] == 'p_' and isinstance(v, (types.FunctionType, types.MethodType)): continue
            if n[0:2] == 't_': continue
            if n[0:2] == 'p_' and n != 'p_error':
                self.log.warning("'%s' not defined as a function", n)
            if ((isinstance(v,types.FunctionType) and func_code(v).co_argcount == 1) or
                (isinstance(v,types.MethodType) and func_code(v).co_argcount == 2)):
                try:
                    doc = v.__doc__.split(" ")
                    if doc[1] == ':':
                        self.log.warning("%s:%d: Possible grammar rule '%s' defined without p_ prefix",
                                         func_code(v).co_filename, func_code(v).co_firstlineno,n)
                except Exception:
                    pass

        self.grammar = grammar

# -----------------------------------------------------------------------------
# yacc(module)
#
# Build a parser
# -----------------------------------------------------------------------------

def yacc(method='LALR', debug=yaccdebug, module=None, tabmodule=tab_module, start=None, 
         check_recursion=1, optimize=0, write_tables=1, debugfile=debug_file,outputdir='',
         debuglog=None, errorlog = None, picklefile=None):

    global parse                 # Reference to the parsing method of the last built parser

    # If pickling is enabled, table files are not created

    if picklefile:
        write_tables = 0

    if errorlog is None:
        errorlog = PlyLogger(sys.stderr)

    # Get the module dictionary used for the parser
    if module:
        _items = [(k,getattr(module,k)) for k in dir(module)]
        pdict = dict(_items)
    else:
        pdict = get_caller_module_dict(2)

    # Collect parser information from the dictionary
    pinfo = ParserReflect(pdict,log=errorlog)
    pinfo.get_all()

    if pinfo.error:
        raise YaccError("Unable to build parser")

    # Check signature against table files (if any)
    signature = pinfo.signature()

    # Read the tables
    try:
        lr = LRTable()
        if picklefile:
            read_signature = lr.read_pickle(picklefile)
        else:
            read_signature = lr.read_table(tabmodule)
        if optimize or (read_signature == signature):
            try:
                lr.bind_callables(pinfo.pdict)
                parser = LRParser(lr,pinfo.error_func)
                parse = parser.parse
                return parser
            except Exception:
                e = sys.exc_info()[1]
                errorlog.warning("There was a problem loading the table file: %s", repr(e))
    except VersionError:
        e = sys.exc_info()
        errorlog.warning(str(e))
    except Exception:
        pass

    if debuglog is None:
        if debug:
            debuglog = PlyLogger(open(debugfile,"w"))
        else:
            debuglog = NullLogger()

    debuglog.info("Created by PLY version %s (http://www.dabeaz.com/ply)", __version__)


    errors = 0

    # Validate the parser information
    if pinfo.validate_all():
        raise YaccError("Unable to build parser")
    
    if not pinfo.error_func:
        errorlog.warning("no p_error() function is defined")

    # Create a grammar object
    grammar = Grammar(pinfo.tokens)

    # Set precedence level for terminals
    for term, assoc, level in pinfo.preclist:
        try:
            grammar.set_precedence(term,assoc,level)
        except GrammarError:
            e = sys.exc_info()[1]
            errorlog.warning("%s",str(e))

    # Add productions to the grammar
    for funcname, gram in pinfo.grammar:
        file, line, prodname, syms = gram
        try:
            grammar.add_production(prodname,syms,funcname,file,line)
        except GrammarError:
            e = sys.exc_info()[1]
            errorlog.error("%s",str(e))
            errors = 1

    # Set the grammar start symbols
    try:
        if start is None:
            grammar.set_start(pinfo.start)
        else:
            grammar.set_start(start)
    except GrammarError:
        e = sys.exc_info()[1]
        errorlog.error(str(e))
        errors = 1

    if errors:
        raise YaccError("Unable to build parser")

    # Verify the grammar structure
    undefined_symbols = grammar.undefined_symbols()
    for sym, prod in undefined_symbols:
        errorlog.error("%s:%d: Symbol '%s' used, but not defined as a token or a rule",prod.file,prod.line,sym)
        errors = 1

    unused_terminals = grammar.unused_terminals()
    if unused_terminals:
        debuglog.info("")
        debuglog.info("Unused terminals:")
        debuglog.info("")
        for term in unused_terminals:
            errorlog.warning("Token '%s' defined, but not used", term)
            debuglog.info("    %s", term)

    # Print out all productions to the debug log
    if debug:
        debuglog.info("")
        debuglog.info("Grammar")
        debuglog.info("")
        for n,p in enumerate(grammar.Productions):
            debuglog.info("Rule %-5d %s", n, p)

    # Find unused non-terminals
    unused_rules = grammar.unused_rules()
    for prod in unused_rules:
        errorlog.warning("%s:%d: Rule '%s' defined, but not used", prod.file, prod.line, prod.name)

    if len(unused_terminals) == 1:
        errorlog.warning("There is 1 unused token")
    if len(unused_terminals) > 1:
        errorlog.warning("There are %d unused tokens", len(unused_terminals))

    if len(unused_rules) == 1:
        errorlog.warning("There is 1 unused rule")
    if len(unused_rules) > 1:
        errorlog.warning("There are %d unused rules", len(unused_rules))

    if debug:
        debuglog.info("")
        debuglog.info("Terminals, with rules where they appear")
        debuglog.info("")
        terms = list(grammar.Terminals)
        terms.sort()
        for term in terms:
            debuglog.info("%-20s : %s", term, " ".join([str(s) for s in grammar.Terminals[term]]))
        
        debuglog.info("")
        debuglog.info("Nonterminals, with rules where they appear")
        debuglog.info("")
        nonterms = list(grammar.Nonterminals)
        nonterms.sort()
        for nonterm in nonterms:
            debuglog.info("%-20s : %s", nonterm, " ".join([str(s) for s in grammar.Nonterminals[nonterm]]))
        debuglog.info("")

    if check_recursion:
        unreachable = grammar.find_unreachable()
        for u in unreachable:
            errorlog.warning("Symbol '%s' is unreachable",u)

        infinite = grammar.infinite_cycles()
        for inf in infinite:
            errorlog.error("Infinite recursion detected for symbol '%s'", inf)
            errors = 1
        
    unused_prec = grammar.unused_precedence()
    for term, assoc in unused_prec:
        errorlog.error("Precedence rule '%s' defined for unknown symbol '%s'", assoc, term)
        errors = 1

    if errors:
        raise YaccError("Unable to build parser")
    
    # Run the LRGeneratedTable on the grammar
    if debug:
        errorlog.debug("Generating %s tables", method)
            
    lr = LRGeneratedTable(grammar,method,debuglog)

    if debug:
        num_sr = len(lr.sr_conflicts)

        # Report shift/reduce and reduce/reduce conflicts
        if num_sr == 1:
            errorlog.warning("1 shift/reduce conflict")
        elif num_sr > 1:
            errorlog.warning("%d shift/reduce conflicts", num_sr)

        num_rr = len(lr.rr_conflicts)
        if num_rr == 1:
            errorlog.warning("1 reduce/reduce conflict")
        elif num_rr > 1:
            errorlog.warning("%d reduce/reduce conflicts", num_rr)

    # Write out conflicts to the output file
    if debug and (lr.sr_conflicts or lr.rr_conflicts):
        debuglog.warning("")
        debuglog.warning("Conflicts:")
        debuglog.warning("")

        for state, tok, resolution in lr.sr_conflicts:
            debuglog.warning("shift/reduce conflict for %s in state %d resolved as %s",  tok, state, resolution)
        
        already_reported = {}
        for state, rule, rejected in lr.rr_conflicts:
            if (state,id(rule),id(rejected)) in already_reported:
                continue
            debuglog.warning("reduce/reduce conflict in state %d resolved using rule (%s)", state, rule)
            debuglog.warning("rejected rule (%s) in state %d", rejected,state)
            errorlog.warning("reduce/reduce conflict in state %d resolved using rule (%s)", state, rule)
            errorlog.warning("rejected rule (%s) in state %d", rejected, state)
            already_reported[state,id(rule),id(rejected)] = 1
        
        warned_never = []
        for state, rule, rejected in lr.rr_conflicts:
            if not rejected.reduced and (rejected not in warned_never):
                debuglog.warning("Rule (%s) is never reduced", rejected)
                errorlog.warning("Rule (%s) is never reduced", rejected)
                warned_never.append(rejected)

    # Write the table file if requested
    if write_tables:
        lr.write_table(tabmodule,outputdir,signature)

    # Write a pickled version of the tables
    if picklefile:
        lr.pickle_table(picklefile,signature)

    # Build the parser
    lr.bind_callables(pinfo.pdict)
    parser = LRParser(lr,pinfo.error_func)

    parse = parser.parse
    return parser

########NEW FILE########
__FILENAME__ = tree_grammar
"""Defines a parser for the tree grammar DSL.

The tree grammar DSL is used to define a set of tree node classes that
can be linked together into a tree data structure. In the context of
Asp, it is generally used to specify strongly-typed intermediate
representations. All nodes inherit from ast.AST and so the tree can be
processed with ast.NodeVisitor or ast.NodeTransformer.  The parser is
invoked like this:

import asp.tree_grammar
tree_grammar.parse('''
<tree grammar program goes here>
''', globals(), checker='NameOfCheckerClass')

In addition to checking that every tree is well-typed during initial
construction, the checker class can be invoked at any time to verify
that a particular tree is well-typed according to the grammar
definition (this is useful to do after the tree is modified):

NameOfCheckerClass().visit(root)

== Tree grammar program syntax ==

The syntax is inspired by BNF (Back-Naurus Form). There are two kinds
of rules, field rules and alternative rules.  Field rules have the
following form:

NodeTypeName(fieldname1=Type, fieldname2=Type, ... , fieldnamen=Type)

where Type is one of the following:

* Another NodeTypeName, or a fully-qualified built-in type like types.IntType
* Type*, indicating a list of whatever Type refers to
* (Type1 | Type2), indicating either Type1 or Type2 is acceptable (union type)
* If the "=Type" is omitted altogether, the type is unconstrained.

Here's a simple example:

VectorBinOp(left=types.IntType*, op=(ast.Add|ast.Mult), right=types.IntType*)
    check assert len(self.left) == len(self.right)

As above, field rules can optionally be followed by "check"
statements, consisting of the word "check" followed by an arbitrary
Python statement. This code is embedded into the class's constructor
and is intended to perform custom validation checks not expressible
in the tree grammar DSL. The resulting class would be used like this:

node = VectorBinOp([1,2,3], ast.Add, [4,5,6])

Here's a more complex multi-rule example:

BinOp(left=Expr, op=(ast.Add|ast.Mult), right=Expr)

Expr(value = ( Constant
             | Variable
             | InputCall) )

Constant(value = types.IntType)

Variable(name = types.StringType)

The "InputCall" node will be created automatically with no fields. It
could be used like this:

tree = BinOp(Expr(Variable('x')), ast.Add, Expr(Constant(1)))
const_value = tree.right.value.value

In cases like the Expr rule here, alternative rules can help to
simplify the syntax. In our example we could substitute:

Expr = Constant
     | Variable
     | InputCall

This creates an abstract base type called Expr, with Constant,
Variable, and InputCall subclassing it, and is used like this:

tree = BinOp(Variable('x'), ast.Add, Constant(1))
const_value = tree.right.value

The general form of an alternative rule is:

BaseTypeName = Alternative1
             | Alternative2
             | ...
             | AlternativeN

Type names appearing on the right-hand side of an
alternative rule must be defined in the same tree
grammar and can only appear in at most one such rule.
To avoid these restrictions, use a field rule instead.
"""

# Based loosely on calc example from ply-3.4 distribution

from collections import defaultdict

keywords = ('check',)

tokens = keywords + ('ID','embedded_python')

literals = ['=', '|', '*', '(', ')', ',', '.']

states = (
   ('check','exclusive'),
)

# Borrowed from basiclex.py in ply-3.4 examples
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    if t.value in keywords:
        t.type = t.value
    if t.value == 'check':
        t.lexer.begin('check')
    return t

def t_check_embedded_python(t):
    r'[^\n]*\n'
    t.lexer.begin('INITIAL')
    return t

t_ignore = " \t"
t_check_ignore = ""

def t_COMMENT(t):
    r'\#[^\n]*\n'
    pass
    
def t_newlines(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

def t_check_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)
    
# Build the lexer
import asp.ply.lex as lex
lex.lex()

# Parsing rules

precedence = (
    ('left','|'),
    ('left','*'),
    ('left','='),
    )

def p_tree_grammar(p):
    '''tree_grammar : rule
                    | tree_grammar rule'''
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_rule(p):
    '''rule : field_rule
            | alternatives_rule'''
    p[0] = p[1]

def p_field_rule(p):
    'field_rule : ID "(" fields_list ")" checks_list'
    p[0] = FieldRule(p[1], p[3], p[5])

def p_fields_list(p):
    '''fields_list : field
                   | fields_list "," field'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_field(p):
    '''field : ID
             | ID "=" expression'''
    if len(p) == 2:
        p[0] = (p[1],)
    else:
        p[0] = (p[1], p[3])

def p_checks_list(p):
    '''checks_list : 
                   | checks_list check embedded_python'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = []

def p_expression(p):
    '''expression : class_name
                  | expression '*'
                  | '(' expression ')'
                  | expression '|' expression '''
    if len(p) == 2:
        p[0] = p[1]
    elif p[2] == '*':
        p[0] = ListOf(p[1])
    elif p[1] == '(':
        p[0] = p[2]
    elif p[2] == '|':
        if isinstance(p[1], OneOf):
            expr_list = p[1].expr_list
            expr_list.append(p[3])
            p[0] = OneOf(expr_list)
        else:
            p[0] = OneOf([p[1], p[3]])

def p_class_name(p):
    '''class_name : ID
                  | class_name '.' ID'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = "%s.%s" % (p[1], p[3])

def p_alternatives_rule(p):
    'alternatives_rule : ID "=" alternatives_list'
    p[0] = AlternativesRule(p[1], p[3])

def p_alternatives_list(p):
    '''alternatives_list : class_name
                         | alternatives_list '|' class_name'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")


class FieldRule:
    def __init__(self, name, fields_list, checks_list):
        self.name = name
        self.count = 0
        self.fields_list = fields_list
        self.checks_list = checks_list

    def __repr__(self):
        return "%s(%s)" % (self.name, str.join(',', map(str, self.fields_list)))

    def generate(self, parent_map, all_classes):
        field_names = map(lambda x: x[0], self.fields_list)
        return('''
class %s(%s):
    def __init__(self, %s, lineno=None, col_offset=None):
        self._fields = (%s,)
        self._attributes = ('lineno', 'col_offset',)
        super(%s, self).__init__(lineno=lineno, col_offset=col_offset)
%s
        self.check()

    def check(self):
%s
%s

    def __deepcopy__(self, memo):
        return %s(%s)
        '''
        %
        (self.name, parent_map[self.name],
         str.join(',', field_names),
         str.join(',', map(lambda x: "'%s'" % x, field_names)),
         self.name,
         str.join('\n', map(lambda x: "        self.%s = %s" % (x, x), field_names)),
         str.join('\n', map(lambda x: "        %s" % self.generate_check(x), self.fields_list)),
         str.join('\n', map(lambda x: "        %s" % x.strip(), self.checks_list)),
         self.name,
         str.join(', ', map(lambda x: "copy.deepcopy(self.%s, memo)" % x, field_names))
        )
        )

    def generate_check(self, field):
        return "assert %s, 'Invalid type %%s for field \\'%s\\' of rule \\'%s\\' (value=%%s)' %% (type(self.%s), self.%s)" % (self.generate_check_helper("self.%s" % field[0], field[1] if len(field) > 1 else 'object'), field[0], self.name, field[0], field[0])

    def generate_check_helper(self, name, field_type):
        if isinstance(field_type, OneOf):
            return str.join(' or ', map(lambda x: self.generate_check_helper(name, x), field_type.expr_list))
        elif isinstance(field_type, ListOf):
            var_name = self.fresh_identifier()
            return "len(filter(lambda %s: not (%s), %s)) == 0" % (var_name, self.generate_check_helper(var_name, field_type.expr), name)
        else:
            return "isinstance(%s, %s)" % (name, field_type)

    def get_classes(self):
        result_list = [self.name]
        for x in self.fields_list:
            if len(x) > 1:
                self.get_classes_helper(result_list, x[1])
        return result_list

    def get_classes_helper(self, result_list, field_type):
        if isinstance(field_type, OneOf):
            for x in field_type.expr_list:
                self.get_classes_helper(result_list, x)
        elif isinstance(field_type, ListOf):
            self.get_classes_helper(result_list, field_type.expr)
        else:
            result_list.append(field_type)

    def get_parent_map(self):
        return dict()

    def fresh_identifier(self):
        self.count += 1
        return 'x%d' % self.count

class AlternativesRule:
    def __init__(self, name, alternatives):
        self.name = name
        self.alternatives = alternatives

    def __repr__(self):
        return "%s = %s" % (self.name, str.join(' | ', map(str, self.alternatives)))

    def generate(self, parent_map, all_classes):
        return '''
class %s(%s):
    def __init__(self, lineno=None, col_offset=None):
        self._attributes = ('lineno', 'col_offset',)
        super(%s, self).__init__(lineno=lineno, col_offset=col_offset)
''' % (self.name, parent_map[self.name], self.name)

    def get_classes(self):
        result = [self.name]
        result.extend(self.alternatives)
        return result

    def get_parent_map(self):
        return dict(map(lambda x: (x, self.name), self.alternatives))

class ListOf:
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return "ListOf(%s)" % (self.expr)

class OneOf:
    def __init__(self, expr_list):
        self.expr_list = expr_list

    def __repr__(self):
        return "OneOf(%s)" % (self.expr_list)

def generate_checker_class(checker, rules):
    result = "class %s(ast.NodeVisitor):" % checker
    for rule in rules:
        result += '''
    def visit_%s(self, node):
        node.check()
        self.generic_visit(node)
        ''' % rule
    return result

def parse(tree_grammar, global_dict, checker=None):
    import ply.yacc as yacc
    yacc.yacc()
    result = yacc.parse(tree_grammar)

    parent_map = defaultdict(lambda: 'ast.AST')
    for rule in result:
        rule_map = rule.get_parent_map()
        assert len(set(parent_map.keys()) & set(rule_map.keys())) == 0, 'Same class occured in two alternative rules, but can only have one base class'
        parent_map.update(rule_map)

    program = "import copy\n"

    classes_with_rules = []
    all_classes = []
    for rule in result:
        classes_with_rules.append(rule.name)
        all_classes.extend(rule.get_classes())
    all_classes = set(filter(lambda x: not("." in x), all_classes))
    classes_with_rules = set(classes_with_rules)

    for rule in result:
        program += rule.generate(parent_map, all_classes)

    for x in all_classes - classes_with_rules:
        program += '''
class %s(%s):
    def __init__(self, lineno=None, col_offset=None):
        self._attributes = ('lineno', 'col_offset',)
        super(%s, self).__init__(lineno=lineno, col_offset=col_offset)
''' % (x, parent_map[x], x)

    if checker != None:
        program = "import ast\n" + program + "\n" + generate_checker_class(checker, classes_with_rules) + "\n"

    program = program + "\n"

    exec(program, global_dict)

########NEW FILE########
__FILENAME__ = util
# common utilities for all asp.* to use
from __future__ import print_function
import os

def debug_print(*args):
    if 'ASP_DEBUG' in os.environ:
        for arg in args:
            print(arg, end='')
        print()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ASP documentation build configuration file, created by
# sphinx-quickstart on Tue Jun 28 15:26:53 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ASP'
copyright = u'2011, SEJITS Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'ASPdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'ASP.tex', u'ASP Documentation',
   u'SEJITS Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'asp', u'ASP Documentation',
     [u'SEJITS Team'], 1)
]

########NEW FILE########
__FILENAME__ = array_doubler
# really dumb example of using templates w/asp

class ArrayDoubler(object):
    
    def __init__(self):
        self.pure_python = True

    def double_using_template(self, arr):
        import asp.codegen.templating.template as template
        mytemplate = template.Template(filename="templates/double_template.mako", disable_unicode=True)
        rendered = mytemplate.render(num_items=len(arr))

        import asp.jit.asp_module as asp_module
        mod = asp_module.ASPModule()
        # remember, must specify function name when using a string
        mod.add_function("double_in_c", rendered)
        return mod.double_in_c(arr)

    def double(self, arr):
        return map (lambda x: x*2, arr)
        


########NEW FILE########
__FILENAME__ = arraydoubler_test
import unittest

from array_doubler import *

class BasicTests(unittest.TestCase):
    def test_pure_python(self):
        arr = [1.0,2.0,3.0]
        result = ArrayDoubler().double(arr)
        self.assertEquals(result[0], 2.0)

    def test_generated(self):
        arr = [1.0, 2.0, 3.0]
        result = ArrayDoubler().double_using_template(arr)
        self.assertEquals(result[0], 2.0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = array_map
# really dumb example of using tree transformations w/asp

import asp.codegen.ast_tools as ast_tools
import asp.codegen.python_ast as ast
import asp.codegen.cpp_ast as cpp
#import asp.codegen.ast_explorer as ast_explorer

class Converter(ast_tools.ConvertAST):
    pass

class ArrayMap(object):

    def __init__(self):
        self.pure_python = True

    def map_using_trees(self, arr):
        operation_ast = ast_tools.parse_method(self.operation)
        expr_ast = operation_ast.body[0].body[0].value
        converter = Converter()
        expr_cpp = converter.visit(expr_ast)

        import asp.codegen.templating.template as template
        mytemplate = template.Template(filename="templates/map_template.mako", disable_unicode=True)
        rendered = mytemplate.render(num_items=len(arr), expr=expr_cpp)

        import asp.jit.asp_module as asp_module
        mod = asp_module.ASPModule()
        mod.add_function("map_in_c", rendered)
        return mod.map_in_c(arr)

    def map(self, arr):
        for i in range(0, len(arr)):
            arr[i] = self.operation(arr[i])

########NEW FILE########
__FILENAME__ = arraymap_test
import unittest

from array_map import *

class ArrayMapExample(ArrayMap):
    def operation(self, x):
        return 2*x+5

class BasicTests(unittest.TestCase):
    def test_pure_python(self):
        example = ArrayMapExample()
        arr = [1.0, 2.0, 3.0, 4.0]
        example.map(arr)
        self.assertEquals(arr[0], 7.0)

    def test_generated(self):
        example = ArrayMapExample()
        arr = [1.0, 2.0, 3.0, 4.0]
        example.map_using_trees(arr)
        self.assertEquals(arr[0], 7.0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = asp_module_tests
import unittest2 as unittest
import asp.jit.asp_module as asp_module
import asp.codegen.cpp_ast as cpp_ast 
from mock import Mock

class TimerTest(unittest.TestCase):
    def test_timer(self):
        pass
#         mod = asp_module.ASPModule()
#         mod.add_function("void test(){;;;;}", "test")
# #        mod.test()
#         self.failUnless("test" in mod.times.keys())

class CallPoliciesTests(unittest.TestCase):
    def test_adding_with_call_policy(self):
        mod = asp_module.ASPModule()
        
        # add a struct to the module
        mod.add_to_module("struct foo { int a; };\n")
        
        # we also want to expose the struct to Python so we can pass instances
        # back and forth
        mod.expose_class("foo")
        
        # add a function that returns a pointer to this arbitrary struct
        # we have to specify a call policy because we are returning a pointer to a C++ object
        mod.add_function("get_foo", "struct foo* get_foo() { struct foo* f = new foo; f->a = 10; return f; }\n",
                         call_policy="python_gc")

        # add a function that takes a foo and returns the int
        mod.add_function("get_int", "int get_int(struct foo* f) { return f->a; }")

        # take a look at the generated code
        # print mod.generate()

        # let's create a foo
        foo = mod.get_foo()
        
        # and now let's make sure that if we pass foo back to C++, it is the same instance
        self.assertEqual(mod.get_int(foo), 10)
        
       
class ASPDBTests(unittest.TestCase):
    def test_creating_db(self):
        db = asp_module.ASPDB("test_specializer")

    def test_create_db_if_nonexistent(self):
        db = asp_module.ASPDB("test")
        self.assertTrue(db.connection)
    
    def test_create_table(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()
        db.create_specializer_table()

        db.connection.execute.assert_called_with(
            'create table test (fname text, variant text, key text, perf real)')

    def test_insert(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()
        db.table_exists = Mock(return_value = True)
        db.create_specializer_table()

        db.insert("func", "func", "KEY", 4.321)

        db.connection.execute.assert_called_with(
                'insert into test values (?,?,?,?)', ("func", "func", "KEY", 4.321))

    def test_create_if_insert_into_nonexistent_table(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()

        # this is kind of a complicated situation.  we want the cursor to
        # return an array when fetchall() is called on it, and we want this
        # cursor to be created when the mock connection is asked for a cursor

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        db.connection.cursor.return_value = mock_cursor
        db.create_specializer_table = Mock()

        db.insert("func", "v1", "KEY", 4.321)

        self.assertTrue(db.create_specializer_table.called)

    def test_get(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()
        db.table_exists = Mock(return_value = True)
        db.create_specializer_table()

        # see note about mocks in test_create_if...

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = ['hello']
        db.connection.cursor.return_value = mock_cursor
        db.create_specializer_table = Mock()

        db.get("func")

        mock_cursor.execute.assert_called_with("select * from test where fname=?",
            ("func",))

    def test_update(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()
        db.table_exists = Mock(return_value = True)
        
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        db.connection.cursor.return_value = mock_cursor


        db.update("foo", "foo_v1", "KEY", 3.21)

        db.connection.execute.assert_called_with("update test set perf=? where fname=? and variant=? and key=?",
                                               (3.21, "foo", "foo_v1", "KEY"))

    def test_delete(self):
        db = asp_module.ASPDB("test")
        db.close() # close the real connection so we can mock it out
        db.connection = Mock()
        db.table_exists = Mock(return_value = True)

        db.delete("foo", "foo_v1", "KEY")

        db.connection.execute.assert_called_with("delete from test where fname=? and variant=? and key=?",
                                                 ("foo", "foo_v1", "KEY"))






class SpecializedFunctionTests(unittest.TestCase):
        

    def test_creating(self):
        a = asp_module.SpecializedFunction("foo", None, Mock())

    def test_add_variant(self):        
        mock_backend = asp_module.ASPBackend(Mock(), None, Mock())
        a = asp_module.SpecializedFunction("foo", mock_backend, Mock())
        a.add_variant("foo_1", "void foo_1(){return;}")
        self.assertEqual(a.variant_names[0], "foo_1")
        self.assertEqual(len(a.variant_funcs), 1)

        # also check to make sure the backend added the function
        self.assertTrue(mock_backend.module.add_to_module.called)

        self.assertRaises(Exception, a.add_variant, "foo_1", None)

    def test_add_variant_at_instantiation(self):
        mock_backend = asp_module.ASPBackend(Mock(), None, Mock())
        a = asp_module.SpecializedFunction("foo", mock_backend, Mock(),
                                           ["foo_1"], ["void foo_1(){return;}"])
        self.assertEqual(len(a.variant_funcs), 1)
        self.assertTrue(mock_backend.module.add_to_module.called)

    def test_call(self):
        # this is a complicated situation.  we want the backend to have a fake
        # module, and that fake module should return a fake compiled module.
        # we'll cheat by just returning itself.
        mock_backend_module = Mock()
        mock_backend_module.compile.return_value = mock_backend_module
        mock_backend = asp_module.ASPBackend(mock_backend_module, None, Mock())
        mock_db = Mock()
        mock_db.get.return_value = []
        a = asp_module.SpecializedFunction("foo", mock_backend, mock_db)
        a.add_variant("foo_1", "void foo_1(){return;}")
        # test a call
        a()

        # it should call foo() on the backend module
        self.assertTrue(mock_backend_module.foo_1.called)

    def test_calling_with_multiple_variants(self):
        # this is a complicated situation.  we want the backend to have a fake
        # module, and that fake module should return a fake compiled module.
        # we'll cheat by just returning itself.
        mock_backend_module = Mock()
        mock_backend_module.compile.return_value = mock_backend_module
        mock_backend = asp_module.ASPBackend(mock_backend_module, None, Mock())
        mock_db = Mock()
        mock_db.get.return_value = []

        a = asp_module.SpecializedFunction("foo", mock_backend, mock_db)
        a.add_variant("foo_1", "void foo_1(){return;}")
        a.add_variant("foo_2", "void foo_2(){}")
        
        # test 2 calls
        a()
        # ensure the second one sees that foo_1 was called the first time
        mock_db.get.return_value = [["foo", "foo_1", None, None]]
        a()

        # it should call both variants on the backend module
        self.assertTrue(mock_backend_module.foo_1.called)
        self.assertTrue(mock_backend_module.foo_2.called)

    def test_pick_next_variant(self):
        mock_db = Mock()
        mock_db.get.return_value = []
        a = asp_module.SpecializedFunction("foo", Mock(), mock_db)
        a.add_variant("foo_1", "void foo_1(){return;}")
        a.add_variant("foo_2", "void foo_2(){}")

        self.assertEqual(a.pick_next_variant(), "foo_1")

        # now if one has run
        mock_db.get.return_value = [[None, "foo_1", None, None]]
        self.assertEqual(a.pick_next_variant(), "foo_2")

        # now if both have run
        mock_db.get.return_value = [[None, "foo_1", None, 1.0],
                                    [None, "foo_2", None, 2.0]]

        self.assertEqual(a.pick_next_variant(), "foo_1")




class HelperFunctionTests(unittest.TestCase):
    def test_creating(self):
        f = asp_module.HelperFunction("foo", "void foo(){}", Mock())

    def test_call(self):
        # this is a complicated situation.  we want the backend to have a fake
        # module, and that fake module should return a fake compiled module.
        # we'll cheat by just returning itself.
        mock_backend_module = Mock()
        mock_backend_module.compile.return_value = mock_backend_module
        mock_backend = asp_module.ASPBackend(mock_backend_module, None, Mock())
        a = asp_module.HelperFunction("foo", "void foo(){}", mock_backend)
        # test a call
        a()

        # it should call foo() on the backend module
        self.assertTrue(mock_backend_module.foo.called)


class ASPModuleMiscTests(unittest.TestCase):
    def test_generate(self):
        a = asp_module.ASPModule()
        mock_backend = Mock()
        a.backends["c++"] = mock_backend

        a.generate()

        self.assertTrue(mock_backend.module.generate.called)


        

class SingleFuncTests(unittest.TestCase):
    def test_adding_function(self):
        m = asp_module.ASPModule()
        m.add_function("foo", "void foo(){return;}")

        self.assertTrue(isinstance(m.specialized_functions["foo"],
                                   asp_module.SpecializedFunction))

    def test_adding_and_calling(self):
        m = asp_module.ASPModule()
        m.add_function("foo", "PyObject* foo(){Py_RETURN_TRUE;}")
        self.assertTrue(m.foo())

    def test_db_integration(self):
        m = asp_module.ASPModule()
        m.add_function("foo", "void foo(){return;}")
        m.foo()

        # Now let's check the db for what's inside
        self.assertEqual(len(m.db.get("foo")), 1)

    def test_helper_function(self):
        m = asp_module.ASPModule()
        m.add_helper_function("foo_helper", "PyObject* foo_helper(){Py_RETURN_TRUE;}")

        self.assertTrue("foo_helper" in m.specialized_functions)

        self.assertTrue(m.foo_helper())
         


class MultipleFuncTests(unittest.TestCase):
    def test_adding_multiple_variants(self):
        mod = asp_module.ASPModule()
        mod.add_function("foo", ["void foo_1(){};", "void foo_2(){};"],
                         ["foo_1", "foo_2"])
        self.assertTrue("foo_1" in mod.specialized_functions["foo"].variant_names)

    def test_running_multiple_variants(self):
        mod = asp_module.ASPModule()
        mod.add_function("foo", ["void foo_1(){/*printf(\"running foo1\\n\");*/};", 
                                 "void foo_2(){/*printf(\"running foo2\\n\");*/};"],
                         ["foo_1", "foo_2"])
        mod.foo()
        mod.foo()

        self.assertEqual(len(mod.db.get("foo")), 2)

    def test_running_variants_with_unrunnable_inputs(self):
        mod = asp_module.ASPModule()
        mod.add_function("foo", ["void foo_1(int a){};", "void foo_2(int a){};"],
                         ["foo_1", "foo_2"], [lambda *args,**kwargs: True, lambda *args,**kwargs: args[0] < 2])
        mod.foo(1)
        mod.foo(1)
        mod.foo(10)
        mod.foo(10)

        self.assertEqual(len(filter(lambda x: x[1]==u'foo_2',mod.db.get("foo"))),1)


"""


    def test_adding_multiple_versions(self):
        mod = asp_module.ASPModule()
        mod.add_function_with_variants(
            ["void test_1(){return;}", "void test_2(){return;}"],
            "test",
            ["test_1", "test_2"])
        mod.compile()
        self.failUnless("test" in mod.compiled_methods.keys())
        self.failUnless("test_1" in mod.compiled_methods["test"])

    def test_running_multiple_variants(self):
        mod = asp_module.ASPModule()
        mod.add_function_with_variants(
            ["PyObject* test_1(PyObject* a){return a;}", 
             "PyObject* test_2(PyObject* b){Py_RETURN_NONE;}"],
            "test",
            ["test_1", "test_2"])
        result1 = mod.test("a")
        result2 = mod.test("a")
        self.assertEqual(set([result1,result2]) == set(["a", None]), True)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best("test"),
            False)
        
    def test_running_multiple_variants_and_inputs(self):
        mod = asp_module.ASPModule()
	key_func = lambda name, *args, **_: (name, args) 
        mod.add_function_with_variants(
            ["void test_1(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); }", 
             "void test_2(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(b); for(; c > 0; c--) a = PyNumber_Add(a,b); }"] ,
            "test",
            ["test_1", "test_2"],
            key_func )
        val = 2000000
        mod.test(1,val)
        mod.test(1,val)
        mod.test(val,1)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,val)), # best time found for this input
            False)
        self.assertEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",7,7)), # this input never previously tried
            False)
        self.assertEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",val,1)), # only one variant timed for this input
            False)
        mod.test(val,1)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",val,1)), # now both variants have been timed
            False)
        self.assertEqual(mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,val)), 'test_1')
        self.assertEqual(mod.compiled_methods["test"].database.get_oracular_best(key_func("test",val,1)), 'test_2')

    def test_adding_variants_incrementally(self):
        mod = asp_module.ASPModule()
	key_func = lambda name, *args, **_: (name, args) 
        mod.add_function_with_variants(
            ["PyObject* test_1(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); return a;}"], 
            "test",
            ["test_1"],
            key_func )
        mod.test(1,20000)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), # best time found for this input
            False)
        mod.add_function_with_variants(
             ["PyObject* test_2(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(b); for(; c > 0; c--) a = PyNumber_Add(a,b); return b;}"] ,
            "test",
            ["test_2"] )
        self.assertEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), # time is no longer definitely best
            False)
        mod.test(1,20000)
        mod.test(1,20000)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), # best time found again
            False)
        self.assertEqual(mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), 'test_1')

    def test_pickling_variants_data(self):
        mod = asp_module.ASPModule()
	key_func = lambda name, *args, **_: (name, args) 
        mod.add_function_with_variants(
            ["PyObject* test_1(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); return a;}", 
             "PyObject* test_2(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(b); for(; c > 0; c--) a = PyNumber_Add(a,b); return b;}"] ,
            "test",
            ["test_1", "test_2"],
            key_func )
        mod.test(1,2)
        mod.test(1,2)
        mod.test(2,1)
        mod.save_method_timings("test")
        mod.clear_method_timings("test")
        mod.restore_method_timings("test")
        self.assertNotEqual(
            mod.compiled_methods["test"].database.variant_times[key_func("test",1,2)], # time found for this input
            False)
        self.assertEqual(
            key_func("test",7,7) not in mod.compiled_methods["test"].database.variant_times, # this input never previously tried
            True)
        self.assertEqual(
            len(mod.compiled_methods["test"].database.variant_times[key_func("test",2,1)]), # only one variant timed for this input
            1)

    def test_dealing_with_preidentified_compilation_errors(self):
        mod = asp_module.ASPModule()
        key_func = lambda name, *args, **_: (name, args)
        mod.add_function_with_variants(
            ["PyObject* test_1(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); return a;}", 
             "PyObject* test_2(PyObject* a, PyObject* b){ /*Dummy*/}",
             "PyObject* test_3(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(b); for(; c > 0; c--) a = PyNumber_Add(a,b); return b;}"] ,
            "test",
            ["test_1", "test_2", "test_3"],
            key_func,
            [lambda name, *args, **kwargs: True]*3,
            [True, False, True],
            ['a', 'b'] )
        mod.test(1,20000)
        mod.test(1,20000)
        mod.test(1,20000)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), # best time found for this input
            False)
        self.assertEqual(
            mod.compiled_methods["test"].database.variant_times[("test",(1,20000))]['test_2'], # second variant was uncompilable
            -1)

    # Disabled, currently failing
    ""
    def test_dealing_with_preidentified_runtime_errors(self):
        mod = asp_module.ASPModule()
        key_func = lambda name, *args, **_: (name, args)
        mod.add_function_with_variants(
            ["PyObject* test_1(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); return a;}", 
             "PyObject* test_2(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(a); for(; c > 0; c--) b = PyNumber_Add(b,a); return a;}", 
             "PyObject* test_3(PyObject* a, PyObject* b){ long c = PyInt_AS_LONG(b); for(; c > 0; c--) a = PyNumber_Add(a,b); return b;}"] ,
            "test",
            ["test_1", "test_2", "test_3"],
            key_func,
            [lambda name, *args, **kwargs: True, lambda name, *args, **kwargs: args[1] < 10001, lambda name, *args, **kwargs: True],
            [True]*3,
            ['a', 'b'] )
        result1 = mod.test(1,20000)
        result2 = mod.test(1,20000)
        result3 = mod.test(1,20000)
        result1 = mod.test(1,10000)
        result2 = mod.test(1,10000)
        result3 = mod.test(1,10000)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,20000)), # best time found for this input
            False)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.get_oracular_best(key_func("test",1,10000)), # best time found for this input
            False)
        self.assertEqual(
            mod.compiled_methods["test"].database.variant_times[("test",(1,20000))]['test_2'], # second variant was unrannable for 20000
            -1)
        self.assertNotEqual(
            mod.compiled_methods["test"].database.variant_times[("test",(1,10000))]['test_2'], # second variant was runnable for 10000
            -1)
    """

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ast_tools_test
import unittest

from asp.codegen.ast_tools import *
from asp.codegen.cpp_ast import *
import asp.codegen.python_ast as python_ast

class NodeVisitorTests(unittest.TestCase):
    def test_for_python_nodes(self):
        class Dummy(NodeVisitor):
            def visit_Name(self, node):
                return False
        p = python_ast.Name("hello", False)
        self.assertFalse(Dummy().visit(p))

    def test_for_cpp_nodes(self):
        class Dummy(NodeVisitor):
            def visit_CName(self, node):
                return False
        c = CName("hello")
        self.assertFalse(Dummy().visit(c))

    def test_for_cpp_children(self):
        class Dummy(NodeVisitor):
            def __init__(self):
                self.worked = False
            def visit_CName(self, _):
                self.worked = True

        c = BinOp(CNumber(1), "+", CName("hello"))
        d = Dummy()
        d.visit(c)
        self.assertTrue(d.worked)


class NodeTransformerTests(unittest.TestCase):

    class Dummy(NodeTransformer):
        def visit_Name(self, _):
            return python_ast.Name("hi", False)
        def visit_CName(self, _):
            return CName("hi")

    def test_for_python_nodes(self):
        p = python_ast.Name("hello", False)
        result = self.Dummy().visit(p)
        self.assertEqual(result.id, "hi")

    def test_for_cpp_nodes(self):
        c = CName("hello")
        result = self.Dummy().visit(c)
        self.assertEqual(result.name, "hi")

    def test_for_cpp_children(self):
        c = BinOp(CNumber(1), "+", CName("hello"))
        result = self.Dummy().visit(c)
        self.assertEqual(result.right.name, "hi")


class LoopUnrollerTests(unittest.TestCase):
    def setUp(self):
        # this is "for(int i=0, i<8; i+=1) { a[i] = i; }"
        self.test_ast = For(
            "i",
            CNumber(0),
            CNumber(7),
            CNumber(1),
            Block(contents=[Assign(Subscript(CName("a"), CName("i")),
                   CName("i"))]))

    def test_unrolling_by_2(self):
        result = LoopUnroller().unroll(self.test_ast, 2)
        # print result
        wanted_result ='for(int i=0;(i<=(7-1));i=(i+(1*2)))\n {\n a[i]=i;\n a[(i+1)]=(i+1);\n}'
        
        self.assertEqual(str(result).replace(' ',''), str(wanted_result).replace(' ', ''))




    def test_unrolling_by_4(self):
        result = LoopUnroller().unroll(self.test_ast, 4)
        # print result
        wanted_result = 'for(inti=0;(i<=(7-3));i=(i+(1*4)))\n{\na[i]=i;\na[(i+1)]=(i+1);\na[(i+2)]=(i+2);\na[(i+3)]=(i+3);\n}'

        self.assertEqual(str(result).replace(' ',''), str(wanted_result).replace(' ', ''))

    def test_imperfect_unrolling (self):
        result = LoopUnroller().unroll(self.test_ast, 3)
        wanted_result = 'for(inti=0;(i<=(7-2));i=(i+(1*3)))\n{\na[i]=i;\na[(i+1)]=(i+1);\na[(i+2)]=(i+2);\n}\nfor(inti=(((((7-0)+1)/3)*3)+0);(i<=7);i=(i+1))\n{\na[i]=i;\n}'

        # print str(result)
        self.assertEqual(str(result).replace(' ',''), str(wanted_result).replace(' ', ''))

    def test_with_1_index(self):
        test_ast = For("i",
                       CNumber(1),
                       CNumber(9),
                       CNumber(1),
                       Block(contents=[Assign(Subscript(CName("a"), CName("i")), CName("i"))]))
        result = LoopUnroller().unroll(test_ast, 2)
        # print result

class LoopBlockerTests(unittest.TestCase):
    def test_basic_blocking(self):
        # this is "for(int i=0, i<=7; i+=1) { a[i] = i; }"
        test_ast = For(
            "i",
            CNumber(0),
            CNumber(7),
            CNumber(1),
            Block(contents=[Assign(Subscript(CName("a"), CName("i")),
                   CName("i"))]))

        wanted_output = "for(intii=0;(ii<=7);ii=(ii+(1*2)))\n{\nfor(inti=ii;(i<=min((ii+1),7));i=(i+1))\n{\na[i]=i;\n}\n}"
        output = str(LoopBlocker().loop_block(test_ast, 2)).replace(' ', '')
        self.assertEqual(output, wanted_output)


class LoopSwitcherTests(unittest.TestCase):
    def test_basic_switching(self):
        test_ast = For("i",
                       CNumber(0),
                       CNumber(7),
                       CNumber(1),
                       Block(contents=[For("j",
                                       CNumber(0),
                                       CNumber(3),
                                       CNumber(1),
                                       Block(contents=[Assign(CName("v"), CName("i"))]))]))
        wanted_output = "for(intj=0;(j<=3);j=(j+1))\n{\nfor(inti=0;(i<=7);i=(i+1))\n{\nv=i;\n}\n}"
        output = str(LoopSwitcher().switch(test_ast, 0, 1)).replace(' ','')
        self.assertEqual(output, wanted_output)

    def test_more_switching(self):
        test_ast = For("i",
                       CNumber(0),
                       CNumber(7),
                       CNumber(1),
                       Block(contents=[For("j",
                                       CNumber(0),
                                       CNumber(3),
                                       CNumber(1),
                                       Block(contents=[For("k",
                                                           CNumber(0),
                                                           CNumber(4),
                                                           CNumber(1),
                                                           Block(contents=[Assign(CName("v"), CName("i"))]))]))]))
        
        wanted_output = "for(intj=0;(j<=3);j=(j+1))\n{\nfor(inti=0;(i<=7);i=(i+1))\n{\nfor(intk=0;(k<=4);k=(k+1))\n{\nv=i;\n}\n}\n}"
        output = str(LoopSwitcher().switch(test_ast, 0, 1)).replace(' ','')
        self.assertEqual(output, wanted_output)

        test_ast = For("i",
                       CNumber(0),
                       CNumber(7),
                       CNumber(1),
                       Block(contents=[For("j",
                                       CNumber(0),
                                       CNumber(3),
                                       CNumber(1),
                                       Block(contents=[For("k",
                                                           CNumber(0),
                                                           CNumber(4),
                                                           CNumber(1),
                                                           Block(contents=[Assign(CName("v"), CName("i"))]))]))]))

        wanted_output = "for(intk=0;(k<=4);k=(k+1))\n{\nfor(intj=0;(j<=3);j=(j+1))\n{\nfor(inti=0;(i<=7);i=(i+1))\n{\nv=i;\n}\n}\n}"
        output = str(LoopSwitcher().switch(test_ast, 0, 2)).replace(' ','')
        self.assertEqual(output, wanted_output)
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = codegen_test
import unittest2 as unittest

from asp.codegen.ast_tools import *

class ReplacerTests(unittest.TestCase):
	def test_num(self):
		a = ast.BinOp(ast.Num(4), ast.Add(), ast.Num(9))
		result = ASTNodeReplacer(ast.Num(4), ast.Num(5)).visit(a)
		self.assertEqual(a.left.n, 5)

	def test_Name(self):
		a = ast.BinOp(ast.Num(4), ast.Add(), ast.Name("variable", None))
		result = ASTNodeReplacer(ast.Name("variable", None), ast.Name("my_variable", None)).visit(a)
		self.assertEqual(a.right.id, "my_variable")

		

class ConversionTests(unittest.TestCase):
    def test_num(self):
        a = ast.Num(4)
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "4")

    def test_Name(self):
        a = ast.Name("hello", None)
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "hello")

    def test_BinOp(self):
        a = ast.BinOp(ast.Num(4), ast.Add(), ast.Num(9))
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "(4 + 9)")

    def test_UnaryOp(self):
        a = ast.UnaryOp(ast.USub(), ast.Name("goober", None))
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "(-(goober))")

    def test_Subscript(self):
        a = ast.Subscript(ast.Name("hello", None),
                        ast.Index(ast.Num(4)),
                        None)
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "hello[4]")

    def test_Assign(self):
        a = ast.Assign([ast.Name("hello", None)], ast.Num(4))
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "hello = 4")

    def test_simple_FunctionDef(self):
        a = ast.FunctionDef("hello",
                            ast.arguments([], None, None, []),
                            [ast.BinOp(ast.Num(10), ast.Add(), ast.Num(20))], [])
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "void hello()\n{\n  (10 + 20);\n}")
    def test_FunctionDef_with_arguments(self):
        a = ast.FunctionDef("hello",
                            ast.arguments([ast.Name("world", None)], None, None, []),
                            [ast.BinOp(ast.Num(10), ast.Add(), ast.Num(20))], [])
        b = ConvertAST().visit(a)
        self.assertEqual(str(b), "void hello(void *world)\n{\n  (10 + 20);\n}")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = config_test
import unittest

from asp.config import *

class ConfigReaderTest(unittest.TestCase):
    def test_get_option(self):
        config = ConfigReader("gmm")
        config.configs = yaml.load("""
                                   gmm:
                                     option1: True
                                     option2: something
                                   """)
        self.assertNotEqual(config.get_option('option1'), None)
        self.assertEqual(config.get_option('qwerty'), None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = cpp_ast_test
import unittest2 as unittest
from asp.codegen.cpp_ast import *
import xml.etree.ElementTree as ElementTree

class GenerationTests(unittest.TestCase):
    # these are simply regression tests for some of the more complicated ast
    # nodes to make sure we don't muck them up when fixing our handling of
    # semicolons.
    def test_For(self):
        f = For("i", CNumber(0), CNumber(10), CNumber(1), Block())
        self.assertEqual(str(f), "for (int i = 0; (i <= 10); i = (i + 1))\n{\n}")

    def test_BinOp(self):
        b = BinOp(CNumber(5), "-", CNumber(5))
        self.assertEqual(str(b), "(5 - 5)")

    def test_Assign(self):
        f = Assign(CName("foo"), BinOp(CNumber(5), "+", CNumber(5)))
        self.assertEqual(str(f), "foo = (5 + 5)")

    def test_UnaryOp(self):
        u = UnaryOp("++", CName("foo"))
        self.assertEqual(str(u), "(++(foo))")

    def test_Block(self):
        b = Block(contents=[FunctionCall(CName("foo")), FunctionCall(CName("boo"))])
        self.assertEqual(str(b), "{\n  foo();\n  boo();\n}")

class ForTests(unittest.TestCase):
    def test_init(self):
        # For(loopvar, initial, end, increment)
        f = For("i", CNumber(0), CNumber(10), CNumber(1), Block())
        self.assertEqual(str(f), "for (int i = 0; (i <= 10); i = (i + 1))\n{\n}")

    def test_change_loopvar(self):
        f = For("i", CNumber(0), CNumber(10), CNumber(1), Block())
        f.loopvar = "j"
        self.assertEqual(str(f), "for (int j = 0; (j <= 10); j = (j + 1))\n{\n}")

@unittest.skip("Ignoring XML tests since we don't currently use XML representation.")
class XMLTests(unittest.TestCase):
    def test_BinOp(self):
        t = BinOp(CNumber(5), '+', CName("foo"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<BinOp op=\"+\"><left><CNumber num=\"5\" /></left>"+
                         "<right><CName name=\"foo\" /></right></BinOp>")

    def test_UnaryOp(self):
        t = UnaryOp("++", CNumber(5))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<UnaryOp op=\"++\"><operand><CNumber num=\"5\" /></operand></UnaryOp>")

    def test_Subscript(self):
        t = Subscript(CName("foo"), CNumber("5"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Subscript><value><CName name=\"foo\" /></value>"+
                         "<index><CNumber num=\"5\" /></index></Subscript>")

    def test_Call(self):
        t = Call("foo", [CName("arg")])
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Call func=\"foo\"><args><CName name=\"arg\" /></args></Call>")

    def test_PostfixUnaryOp(self):
        t = PostfixUnaryOp(CName("foo"), "--");
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<PostfixUnaryOp op=\"--\"><operand><CName name=\"foo\" /></operand></PostfixUnaryOp>")

    def test_ConditionalExpr(self):
        t = ConditionalExpr(CName("foo"), CName("bar"), CName("baz"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<ConditionalExpr><test><CName name=\"foo\" /></test><body><CName name=\"bar\" /></body><orelse><CName name=\"baz\" /></orelse></ConditionalExpr>")

    def test_RawFor(self):
        t = RawFor(CName("foo"), CName("bar"), CName("baz"), CName("bin"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<For><start><CName name=\"foo\" /></start><condition><CName name=\"bar\" /></condition>"+
                         "<update><CName name=\"baz\" /></update><body><CName name=\"bin\" /></body></For>")

    def test_FunctionBody(self):
        t = FunctionBody(CName("foo"), CName("bar"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<FunctionBody><fdecl><CName name=\"foo\" /></fdecl><body><CName name=\"bar\" /></body></FunctionBody>")

    def test_FunctionDeclaration(self):
        t = FunctionDeclaration(CName("foo"), [CName("bar")])
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<FunctionDeclaration><subdecl><CName name=\"foo\" /></subdecl><arg_decls><CName name=\"bar\" /></arg_decls></FunctionDeclaration>")

    def test_Value(self):
        t = Value("int", "foo")
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Value name=\"foo\" typename=\"int\" />")

    def test_Pointer(self):
        t = Pointer(Value("int", "foo"))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Pointer><subdecl><Value name=\"foo\" typename=\"int\" /></subdecl></Pointer>")
                                              

    def test_Block(self):
        t = Block(contents=[CName("foo")])
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Block><CName name=\"foo\" /></Block>")

    def test_Define(self):
        t = Define("foo", "defined_to")
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Define symbol=\"foo\" value=\"defined_to\" />")

    def test_Statement(self):
        t = Statement("foo")
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Statement>foo</Statement>")

    def test_Assign(self):
        t = Assign(CName("foo"), CNumber(5))
        self.assertEqual(ElementTree.tostring(t.to_xml()),
                         "<Assign><lvalue><CName name=\"foo\" /></lvalue><rvalue><CNumber num=\"5\" /></rvalue></Assign>")

    def test_whole_ast(self):
        """ A test using the pickled whole AST from one of the stencil kernel test cases."""
        import pickle
        t = pickle.load(open("tests/pickled_ast"))
        t.to_xml()
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ctypes_converter_test
import unittest
from ctypes import *
from asp.codegen.ctypes_converter import *

def normalize(a):
    return ''.join(a.split())

class BasicConversionTests(unittest.TestCase):
    def test_int_field(self):
        class Foo(Structure):
            _fields_ = [("x", c_int), ("y", c_int)]
            
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo"]), normalize("struct Foo { int x; int y; };"))
        
    def test_mixed_fields(self):
        class Foo2(Structure):
            _fields_ = [("x", c_int), ("y", c_bool), ("z", c_void_p), ("a", c_ushort)]
            
        self.assertEquals(normalize(StructConverter().convert(Foo2)["Foo2"]), normalize("struct Foo2 { int x; bool y; void* z; unsigned short a; };"))

    def test_pointer_field(self):
        class Foo(Structure):
            _fields_ = [("x", c_int), ("y", POINTER(c_int)), ("z", POINTER(POINTER(c_double)))]
            
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo"]), normalize("struct Foo { int x; int* y; double** z;};"))
    
    def test_array_field(self):
        class Foo(Structure):
            _fields_ = [("x", c_int * 4)]
        
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo"]), normalize("struct Foo {int x[4];};"))
        
class NestedConversionTests(unittest.TestCase):
    def test_simple_two_structs(self):
        class Foo2(Structure):
            _fields_ = [("x", c_int)]
        class Foo(Structure):
            _fields_ = [("f", Foo2)]
            
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo"]), normalize("struct Foo { Foo2 f; };"))
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo2"]), normalize("struct Foo2 { int x; };"))
    
    def test_self_recursive_struct(self):
        class Foo(Structure):
            pass
        Foo._fields_ = [("x", POINTER(Foo))]
        
        self.assertEquals(normalize(StructConverter().convert(Foo)["Foo"]), normalize("struct Foo { Foo* x; };"))
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = cuda_test
# adapted from CodePy's nvcc example.
# requires PyCuda, CodePy, ASP, and CUDA 3.0+

from codepy.cgen import *
from codepy.bpl import BoostPythonModule
from codepy.cuda import CudaModule
from codepy.cgen.cuda import CudaGlobal
import asp.jit.asp_module as asp_module
import unittest2 as unittest

class CUDATest(unittest.TestCase):
    def test_cuda(self):
        mod = asp_module.ASPModule(use_cuda=True)

        # create the host code
        mod.add_to_preamble("""
        #define N 10
        void add_launch(int*,int*,int*);
        """,backend="c++") 
        mod.add_helper_function("foo_1", """int foo_1(){
        int a[N], b[N], c[N];
        int *dev_a, *dev_b, *dev_c;
        cudaMalloc( (void**)&dev_a, N * sizeof(int) );
        cudaMalloc( (void**)&dev_b, N * sizeof(int) );
        cudaMalloc( (void**)&dev_c, N * sizeof(int) );
        for (int i=0; i<N; i++) {
            a[i] = -i;
            b[i] = i * i;
        }
        cudaMemcpy( dev_a, a, N * sizeof(int),
                              cudaMemcpyHostToDevice );
        cudaMemcpy( dev_b, b, N * sizeof(int),
                              cudaMemcpyHostToDevice );
        cudaMemcpy( c, dev_c, N * sizeof(int),
                              cudaMemcpyDeviceToHost );
        add_launch(dev_a, dev_b, dev_c);
        cudaFree( dev_a );
        cudaFree( dev_b );
        cudaFree( dev_c );
        return 0;}""",backend="cuda")
        # create device code
        mod.add_to_module("""
        #define N 10
        __global__ void add( int *a, int *b, int *c ) {
            int tid = blockIdx.x;    // handle the data at this index
            if (tid < N)
                c[tid] = a[tid] + b[tid];
        }
        void add_launch(int *a, int *b, int *c) {
            add<<<N,1>>>( a, b, c );
        }
        """, backend='cuda')
        # test a call
        ret = mod.foo_1() 
        self.assertTrue(ret == 0)
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = platform_detector_test
import unittest

from asp.config import *

class CompilerDetectorTests(unittest.TestCase):
    def test_detect(self):
        self.assertTrue(CompilerDetector().detect("gcc"))

        self.assertFalse(CompilerDetector().detect("lkasdfj"))

class CPUInfoTests(unittest.TestCase):

    def test_num_cores(self):
        def read_cpu_info(self):
            return open("tests/cpuinfo").readlines()
        
        PlatformDetector.read_cpu_info = read_cpu_info
        pd = PlatformDetector()

        info = pd.get_cpu_info()
        self.assertEqual(info['numCores'], 8)
    
    def test_vendor_and_model(self):
        def read_cpu_info(self):
            return open("tests/cpuinfo").readlines()
        
        PlatformDetector.read_cpu_info = read_cpu_info
        pd = PlatformDetector()

        info = pd.get_cpu_info()
        self.assertEqual(info['vendorID'], "GenuineIntel")
        self.assertEqual(info['model'], 30)
        self.assertEqual(info['cpuFamily'], 6)

    def test_cache_size(self):
        def read_cpu_info(self):
            return open("tests/cpuinfo").readlines()
        
        PlatformDetector.read_cpu_info = read_cpu_info
        pd = PlatformDetector()

        info = pd.get_cpu_info()
        self.assertEqual(info['cacheSize'], 8192)
    
    def test_capabilities(self):
        def read_cpu_info(self):
            return open("tests/cpuinfo").readlines()
        
        PlatformDetector.read_cpu_info = read_cpu_info
        pd = PlatformDetector()
       
        info = pd.get_cpu_info()
        self.assertEqual(info['capabilities'].count("sse"), 1)

    def test_compilers(self):
        compilers = PlatformDetector().get_compilers()
        self.assertTrue("gcc" in compilers)

class GPUInfoTest(unittest.TestCase):

    def test_properties(self):
        pd = PlatformDetector()
        compilers = pd.get_compilers()
        if "nvcc" in compilers and pd.get_num_cuda_devices() > 0:
            info = {}
            pd.set_cuda_device(0)
            info = pd.get_cuda_info()
            self.assertTrue(info['total_mem'] > 0)
        else: self.assertTrue(True) # Undesirable to have the test fail on machinces without GPUs

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = bilateral_filter.2
from stencil_kernel import *
import sys
import numpy
import math

width = 50
height = 50
image_in = open('mallard_tiny.raw', 'rb')
stdev_d = 1
stdev_s = 70
radius = 1

class Kernel(object):
   def kernel(self, in_img, filter_d, filter_s, out_img):
       for x in out_img.interior_points():
           for y in in_img.neighbors(x, 1):
               out_img[x] += in_img[y] * filter_d[int(distance(x, y))] * filter_s[abs(int(in_img[x]-in_img[y]))]

def gaussian(stdev, length):
    result = StencilGrid([length])
    scale = 1.0/(stdev*math.sqrt(2.0*math.pi))
    divisor = -1.0 / (2.0 * stdev * stdev)
    for x in xrange(length):
       result[x] = scale * math.exp(float(x) * float(x) * divisor)
    return result

pixels = map(ord, list(image_in.read(width * height))) # Read in grayscale values
intensity = float(sum(pixels))/len(pixels)

kernel = Kernel()
kernel.should_unroll = False
out_grid = StencilGrid([width,height])
out_grid.ghost_depth = radius
in_grid = StencilGrid([width,height])
in_grid.ghost_depth = radius
for x in range(-radius,radius+1):
    for y in range(-radius,radius+1):
        in_grid.neighbor_definition[1].append( (x,y) )

for x in range(0,width):
    for y in range(0,height):
        in_grid.data[(x, y)] = pixels[y * width + x]

kernel.kernel(in_grid, gaussian(stdev_d, radius*2), gaussian(stdev_s, 256), out_grid)

for x in range(0,width):
    for y in range(0,height):
        pixels[y * width + x] = out_grid.data[(x, y)]
out_intensity = float(sum(pixels))/len(pixels)
for i in range(0, len(pixels)):
    pixels[i] = min(255, max(0, int(pixels[i] * (intensity/out_intensity))))

image_out = open('out.raw', 'wb')
image_out.write(''.join(map(chr, pixels)))

########NEW FILE########
__FILENAME__ = bilateral_filter
from stencil_kernel import *
import sys
import numpy
import math

width = 50
height = 50
image_in = open('mallard_tiny.raw', 'rb')
stdev_d = 1
stdev_s = 70
radius = 1

class Kernel(StencilKernel):
   def kernel(self, in_img, filter_d, filter_s, out_img):
       for x in out_img.interior_points():
           for y in in_img.neighbors(x, 1):
               out_img[x] += in_img[y] * filter_d[int(distance(x, y))] * filter_s[abs(int(in_img[x]-in_img[y]))]

def gaussian(stdev, length):
    result = StencilGrid([length])
    scale = 1.0/(stdev*math.sqrt(2.0*math.pi))
    divisor = -1.0 / (2.0 * stdev * stdev)
    for x in xrange(length):
       result[x] = scale * math.exp(float(x) * float(x) * divisor)
    return result

pixels = map(ord, list(image_in.read(width * height))) # Read in grayscale values
intensity = float(sum(pixels))/len(pixels)

kernel = Kernel(inject_failure="manhattan_distance")
kernel.should_unroll = False
out_grid = StencilGrid([width,height])
out_grid.ghost_depth = radius
in_grid = StencilGrid([width,height])
in_grid.ghost_depth = radius
for x in range(-radius,radius+1):
    for y in range(-radius,radius+1):
        in_grid.neighbor_definition[1].append( (x,y) )

for x in range(0,width):
    for y in range(0,height):
        in_grid.data[(x, y)] = pixels[y * width + x]

kernel.kernel(in_grid, gaussian(stdev_d, radius*2), gaussian(stdev_s, 256), out_grid)

for x in range(0,width):
    for y in range(0,height):
        pixels[y * width + x] = out_grid.data[(x, y)]
out_intensity = float(sum(pixels))/len(pixels)
for i in range(0, len(pixels)):
    pixels[i] = min(255, max(0, int(pixels[i] * (intensity/out_intensity))))

image_out = open('out.raw', 'wb')
image_out.write(''.join(map(chr, pixels)))

########NEW FILE########
__FILENAME__ = gdb
import subprocess
import re

class gdb(object):
    def __init__(self, python_file, cpp_file, cpp_start_line):
        self.process = subprocess.Popen(["PYTHONPATH=stencil:../.. gdb python"],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='.')
        self.process.stdin.write("run " + python_file + "\n")
        self.process.stdin.write("break " + cpp_file + ":" + str(cpp_start_line) + "\n")
        self.process.stdin.write("run " + python_file + "\n")
        self.process.stdin.write("delete 0\n")

    # Read up to current position in output
    def sync_pos(self):
        self.process.stdin.write("echo sync375023\\n\n")
        line = "\n"
        while line:
            line = self.process.stdout.readline()
            if 'sync375023' in line:
                break
        line = self.process.stdout.read(len("(gdb) "))

    def get_current_stack(self):
        self.sync_pos()
        self.process.stdin.write("back\n")
        line = self.process.stdout.readline().strip()
        m = re.match(r'^#([0-9]+)\s+(.*::)?([A-Za-z0-9_]+)\s+(\(.*\))? at (.*):([0-9]+)$', line)
        if m and m.group(1) == '0':
            result = dict()
            result['stack_frame_number'] = m.group(1)
            result['namespace'] = m.group(2)
            result['method_name'] = m.group(3)
            result['params'] = m.group(4)
            result['filename'] = m.group(5)
            result['line_no'] = int(m.group(6))
            return result
        else:
            raise RuntimeError('Could not match regex on stack line:', line)

    def next(self):
        self.process.stdin.write("next\n")

    def quit(self):
        self.process.stdin.write("quit\n")
        self.process.stdout.read() # Read to end

    def read_expr(self, expr):
        self.sync_pos()
        self.process.stdin.write("print " + expr + "\n")
        self.process.stdin.write("echo sentinel07501923\\n\n")
        line = self.process.stdout.readline().strip()
        if 'sentinel07501923' in line:
            return None
        else:
            m = re.match(r'^\$([0-9]+)\s+=\s+(.*)$', line)
            if m:
                return m.group(2)
            else:
                raise RuntimeError('Could not match regex on expression print:', line)

if __name__ == '__main__':
    gdb = gdb()
    for x in range(10):
        stack = gdb.get_current_stack()
        print stack['line_no']
        print 'x1:', gdb.read_expr('x1')
        print 'x2:', gdb.read_expr('x2')
        print 'x3:', gdb.read_expr('x3')
        gdb.next()

    gdb.quit()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python
# -*- coding: utf-8 -*-
 
# Based on http://developer.qt.nokia.com/wiki/PySideTutorials_Simple_Dialog

import cgi
import sys
import gdb
import pdb
import datetime
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtDeclarative import QDeclarativeView

def log(str):
    print datetime.datetime.now() - start_time, str

class WatchRemover(object):
    def __init__(self, form, row):
        self.form = form
        self.row = row

    def remove_watch(self):
        log('Removing watch ' + self.form.watches[self.row][0] + ", " + self.form.watches[self.row][1])
        self.form.watches.pop(self.row)
        self.form.update_watch_widgets()

class AddWatchForm(QDialog):
    def __init__(self, cpponly=False, parent=None):
        self.fontFamily = "Courier"
        super(AddWatchForm, self).__init__(parent)
        self.setWindowTitle("Add Watch")

        if not cpponly:
            self.layout_lang = QHBoxLayout()
            self.radiobutton_cpp = QRadioButton('C++')
            self.radiobutton_cpp.setChecked(True)
            self.radiobutton_python = QRadioButton('Python')
            self.layout_lang.addWidget(self.radiobutton_cpp)
            self.layout_lang.addWidget(self.radiobutton_python)

        self.layout_expr = QHBoxLayout()
        self.layout_expr.addWidget(QLabel('Expression to watch'))
        self.lineedit_expr = QLineEdit()
        self.layout_expr.addWidget(self.lineedit_expr)

        self.button_step_over = QPushButton("Add")
        self.button_step_over.clicked.connect(self.accept)
        self.button_close = QPushButton("Cancel")
        self.button_close.clicked.connect(self.reject)

        self.right_panel = QVBoxLayout()
        self.right_panel.addStretch()

        self.button_hlayout = QHBoxLayout()
        self.button_hlayout.addWidget(self.button_step_over)
        self.button_hlayout.addWidget(self.button_close)

        self.vlayout = QVBoxLayout()
        if not cpponly:
            self.vlayout.addLayout(self.layout_lang)
        self.vlayout.addLayout(self.layout_expr)
        self.vlayout.addLayout(self.button_hlayout)

        self.setLayout(self.vlayout)
        self.mixedText = mixedText

class Form(QDialog):
    def __init__(self, mixedText, python_file_gdb, cpp_file, cpp_start_line, python_file_pdb, python_start_line, next_dict, cpp_offset_lines=0, python_offset_lines=0, parent=None, watches=[], cpponly=False):
        self.python_file_gdb = python_file_gdb
        self.cpp_file = cpp_file
        self.cpp_start_line = cpp_start_line
        self.next_dict = next_dict
        self.python_file_pdb = python_file_pdb
        self.python_start_line = python_start_line
        self.cpp_offset_lines = cpp_offset_lines
        self.python_offset_lines = python_offset_lines
        self.watches = watches
        self.cpponly = cpponly

        self.fontFamily = "Courier"
        super(Form, self).__init__(parent)
        self.setWindowTitle("SEJITS Integrated Debugger")
        self.resize(1920, 1024)
        self.textedit = QTextEdit()
        self.textedit.setReadOnly(True)
        self.textedit.setLineWrapMode(QTextEdit.NoWrap)
        self.button_step_over = QPushButton("Step over")
        self.button_step_over.clicked.connect(self.stepOver)
        self.button_restart = QPushButton("Restart")
        self.button_restart.clicked.connect(self.restart)
        self.button_close = QPushButton("Close")
        self.button_close.clicked.connect(self.accept)

        self.lang_colors = dict()
        self.lang_colors['C++'] = '#ff0000'
        self.lang_colors['Python'] = '#0000ff'

        if self.cpponly:
            self.watches = [x for x in watches if x[0] == 'C++']
        self.watch_layout = QGridLayout()
        self.watch_values = dict()

        self.button_add_watch = QPushButton("Add watch")
        self.button_add_watch.clicked.connect(self.add_watch)

        self.right_panel = QVBoxLayout()
        self.right_panel.addLayout(self.watch_layout)
        self.right_panel.addWidget(self.button_add_watch)
        self.right_panel.addStretch()

        self.button_hlayout = QHBoxLayout()
        self.button_hlayout.addWidget(self.button_step_over)
        self.button_hlayout.addWidget(self.button_restart)
        self.button_hlayout.addWidget(self.button_close)

        self.edit_watch_hlayout = QHBoxLayout()
        self.edit_watch_hlayout.addWidget(self.textedit)
        self.edit_watch_hlayout.addLayout(self.right_panel)
        self.edit_watch_hlayout.setStretch(0, 3)
        self.edit_watch_hlayout.setStretch(1, 1)

        self.vlayout = QVBoxLayout()
        self.vlayout.addLayout(self.edit_watch_hlayout)
        self.vlayout.addLayout(self.button_hlayout)

        self.setLayout(self.vlayout)
        self.mixedText = mixedText
        self.gdb = gdb.gdb(self.python_file_gdb, self.cpp_file, self.cpp_start_line)
        self.pdb = pdb.pdb(self.python_file_pdb, self.python_start_line)
        self.updateView()
        self.update_watch_widgets()

    def emptyOutGrid(self, grid):
        for row in range(0, grid.rowCount()):
            for col in range(0, grid.columnCount()):
                item = grid.itemAtPosition(row, col)
                if item != None:
                    item.widget().hide()
                    grid.removeItem(item)

    def update_watch_widgets(self):
        self.emptyOutGrid(self.watch_layout)
        self.watch_values = dict()
        self.watch_removers = []
        row = 0
        for watch in self.watches:
            self.watch_values[watch] = QLineEdit()
            self.watch_layout.addWidget(QLabel('<font color="' + self.lang_colors[watch[0]] + '">' + watch[1] + '</font>'), row, 0)
            self.watch_layout.addWidget(self.watch_values[watch], row, 1)
            self.watch_layout.addWidget(QLabel('<font color="' + self.lang_colors[watch[0]] + '">' + watch[0] + '</font>'), row, 2)
            button_delete = QToolButton()
            button_delete.setIcon(QIcon('delete.png'))
            self.watch_removers.append(WatchRemover(self, row))
            button_delete.clicked.connect(self.watch_removers[-1].remove_watch)
            self.watch_layout.addWidget(button_delete, row, 3)
            row = row + 1
        self.updateView()

    def get_line_from_cpp_line(self, cpp_line):
        current_line = 0
        current_cpp_line = 0
        for line in self.mixedText.split("\n"):
            if len(line) > 1 and line[0] == '@':
                if current_cpp_line == cpp_line:
                    return current_line
                current_cpp_line += 1
            current_line += 1
        return -1

    def get_line_from_python_line(self, python_line):
        if self.cpponly:
            return -1
        current_line = 0
        current_python_line = 0
        for line in self.mixedText.split("\n"):
            if not (len(line) > 1 and line[0] == '@'):
                if current_python_line == python_line:
                    return current_line
                current_python_line += 1
            current_line += 1
        return -1

    def updateView(self):
        try:
            stack = self.gdb.get_current_stack()
            cpp_line = stack['line_no'] - 1 - self.cpp_offset_lines
            stack = self.pdb.get_current_stack()
            python_line = stack['line_no'] - 1 - self.python_offset_lines
            current_cpp_line = self.get_line_from_cpp_line(cpp_line)
            current_python_line = self.get_line_from_python_line(python_line)
        except Exception as e:
            print e
            current_cpp_line = -1
            current_python_line = -1
            self.button_step_over.setDisabled(True)

        hScrollBarPosition = self.textedit.horizontalScrollBar().value()
        vScrollBarPosition = self.textedit.verticalScrollBar().value()

        html = "<font face=\"" + self.fontFamily + "\"><b>" + "<table><tr><td width=\"20\">";
        for line in range(len(self.mixedText.split("\n"))):
            if line == current_cpp_line:
                html += "<img src=\"current_line_cpp.png\"/><br/>"
            elif line == current_python_line:
                html += "<img src=\"current_line_python.png\"/><br/>"
            else:
                html += "&nbsp;<br/>"
        html += "</td><td>" + self.render() + "</td></tr></table>" + "</b></font>"
        self.textedit.setHtml(html)

        self.textedit.horizontalScrollBar().setValue(hScrollBarPosition)
        self.textedit.verticalScrollBar().setValue(vScrollBarPosition)

        for watch in self.watch_values.keys():
            if watch[0] == 'C++':
                value = self.gdb.read_expr(watch[1])
                if value == None:
                    self.watch_values[watch].setText('<unavailable>')
                else:
                    self.watch_values[watch].setText(value)
            elif watch[0] == 'Python':
                value = self.pdb.read_expr(watch[1])
                self.watch_values[watch].setText(value)

    def render(self):
        x = ''
        for line in self.mixedText.split("\n"):
            line = cgi.escape(line).replace(' ', '&nbsp;')
            if len(line) > 1 and line[0] == '@':
                line = line[1:]
                x += "<font color=\"" + self.lang_colors['C++'] + "\">" + line + "</font>" + "<br/>"
            else:
                if self.cpponly:
                    x += "<font color=\"" + self.lang_colors['C++'] + "\">// " + line + "</font>" + "<br/>"
                else:
                    x += "<font color=\"" + self.lang_colors['Python'] + "\">" + line + "</font>" + "<br/>"
        return x

    def stepOver(self):
        # Get current lines
        stack = self.gdb.get_current_stack()
        cpp_line = stack['line_no'] - 6 # First 5 lines of real C++ file are headers and stuff
        stack = self.pdb.get_current_stack()
        python_line = stack['line_no'] - 1 # Adjust to zero based

        try:
            if self.cpponly:
                to_step = [0,1]
            else:
                to_step = self.next_dict[tuple([python_line, cpp_line])]
        except:
            print 'Missing dictionary entry for line combination', tuple([python_line, cpp_line])
            return
        for x in range(to_step[0]):
            self.pdb.next()
        for x in range(to_step[1]):
            self.gdb.next()
        self.updateView()

        stack = self.gdb.get_current_stack()
        cpp_line_after = stack['line_no'] - 6 # First 5 lines of real C++ file are headers and stuff
        stack = self.pdb.get_current_stack()
        python_line_after = stack['line_no'] - 1 # Adjust to zero based
        log('Step over clicked, moved from lines (' + str(python_line) + ',' + str(cpp_line) + ') to lines (' + str(python_line_after) + ',' + str(cpp_line_after) + ')')

    def restart(self):
        log('Restart clicked')
        self.gdb.quit()
        self.pdb.quit()
        self.gdb = gdb.gdb(self.python_file_gdb, self.cpp_file, self.cpp_start_line)
        self.pdb = pdb.pdb(self.python_file_pdb, self.python_start_line)
        self.button_step_over.setEnabled(True)
        self.updateView()

    def add_watch(self):
        log('Add watch clicked')
        add_watch_form = AddWatchForm(cpponly=self.cpponly, parent=self)
        if add_watch_form.exec_() == QDialog.Accepted:
            lang = 'C++'
            if not self.cpponly and add_watch_form.radiobutton_python.isChecked():
                lang = 'Python'
            expr = add_watch_form.lineedit_expr.text()
            self.watches.append( (lang, expr) )
            self.update_watch_widgets()
            log('Add watch completed, added ' + lang + ', ' + expr)

start_time = datetime.datetime.now()
log('Starting')
app = QApplication(sys.argv)
example_num = int(sys.argv[1])
cpponly = (len(sys.argv) > 2 and sys.argv[2] == 'cpponly')
if example_num == 1:
    mixedText = """\
from stencil_kernel import *
import stencil_grid
import numpy

class ExampleKernel(StencilKernel):
    def kernel(self, in_grid, out_grid):
@void kernel(PyObject *in_grid, PyObject *out_grid)
@{
@  #define _out_grid_array_macro(_d0,_d1) (_d1+(_d0 * 5))
@  #define _in_grid_array_macro(_d0,_d1) (_d1+(_d0 * 5))
@  npy_double *_my_out_grid = ((npy_double *)PyArray_DATA(out_grid));
@  npy_double *_my_in_grid = ((npy_double *)PyArray_DATA(in_grid));
        for x in out_grid.interior_points():
@  for (int x1 = 2; (x1 <= 4); x1 = (x1 + 1))
@  {
@    #pragma ivdep
@    for (int x2 = 2; (x2 <= 4); x2 = (x2 + 1))
@    {
@      int x3;
@      x3 = _out_grid_array_macro(x1, x2);
            for y in in_grid.neighbors(x, 1):
                out_grid[x] = out_grid[x] + in_grid[y]
@      _my_out_grid[x3] = (_my_out_grid[x3] + _my_in_grid[_in_grid_array_macro((x1 + 1), (x2 + 0))]);
@      _my_out_grid[x3] = (_my_out_grid[x3] + _my_in_grid[_in_grid_array_macro((x1 + -1), (x2 + 0))]);
@      _my_out_grid[x3] = (_my_out_grid[x3] + _my_in_grid[_in_grid_array_macro((x1 + 0), (x2 + 1))]);
@      _my_out_grid[x3] = (_my_out_grid[x3] + _my_in_grid[_in_grid_array_macro((x1 + 0), (x2 + -1))]);
@    }
@  }
@}

in_grid = StencilGrid([5,5])
for x in range(0,5):
    for y in range(0,5):
        in_grid.data[x,y] = x + y

out_grid = StencilGrid([5,5])
ExampleKernel().kernel(in_grid, out_grid)
"""
    next_dict = {(5,4): (0,1), (5,5): (1,1),
                 (6,6): (0,1), (6,9): (0,1), (6,12): (1,1),
                 (7,13): (1,0), (8,13): (1,1),
                 (7,14): (1,0), (8,14): (1,1),
                 (7,15): (1,0), (8,15): (1,1),
                 (7,16): (1,0), (8,16): (2,1),
                 (6,19): (1,1)
                }
    # watches = [('C++','x1'), ('C++', 'x2'), ('C++', 'x3'), ('C++', '_my_out_grid[x3]'),
    #            ('Python', 'x'), ('Python', 'y'), ('Python', 'out_grid[x]'), ('Python', 'in_grid[y]')]
    watches = []
    form = Form(mixedText, 'stencil_kernel_example.py', '/tmp/asp_cache/ca3a79b1ef34c14cdd7df371368ecb01/module.cpp', 7, 'stencil_kernel_example.2.py', ['break 17', 'continue', 's'], next_dict, cpp_offset_lines=5, watches=watches, cpponly=cpponly)
elif example_num == 2:
    mixedText = """\
from stencil_kernel import *
import sys
import numpy
import math

width = 50
height = 50
image_in = open('mallard_tiny.raw', 'rb')
stdev_d = 1
stdev_s = 70
radius = stdev_d * 3

class Kernel(StencilKernel):
   def kernel(self, in_img, filter_d, filter_s, out_img):
@  void kernel(PyObject *in_img, PyObject *filter_d, PyObject *filter_s, PyObject *out_grid)
@  {
@    #define _filter_s_array_macro(_d0) (_d0)
@    #define _in_img_array_macro(_d0,_d1) (_d1+(_d0 * 50))
@    #define _filter_d_array_macro(_d0) (_d0)
@    #define _out_grid_array_macro(_d0,_d1) (_d1+(_d0 * 50))
@    npy_double *_my_filter_s = ((npy_double *)PyArray_DATA(filter_s));
@    npy_double *_my_in_img = ((npy_double *)PyArray_DATA(in_img));
@    npy_double *_my_filter_d = ((npy_double *)PyArray_DATA(filter_d));
@    npy_double *_my_out_grid = ((npy_double *)PyArray_DATA(out_grid));
       for x in out_img.interior_points():
@    for (int x1 = 1; (x1 <= 48); x1 = (x1 + 1))
@    {
@      #pragma ivdep
@      for (int x2 = 1; (x2 <= 48); x2 = (x2 + 1))
@      {
@        int x3;
@        x3 = _out_grid_array_macro(x1, x2);
           for y in in_img.neighbors(x, 1):
               out_img[x] += in_img[y] * filter_d[int(distance(x, y))] * filter_s[abs(int(in_img[x]-in_img[y]))]
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 1), (x2 + 0))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 1), (x2 + 0))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + -1), (x2 + 0))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + -1), (x2 + 0))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 1))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 0), (x2 + 1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + -1))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 0), (x2 + -1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + -1), (x2 + -1))] * _my_filter_d[int(2)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + -1), (x2 + -1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + -1), (x2 + 0))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + -1), (x2 + 0))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + -1), (x2 + 1))] * _my_filter_d[int(2)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + -1), (x2 + 1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + -1))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 0), (x2 + -1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] * _my_filter_d[int(0)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 1))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 0), (x2 + 1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 1), (x2 + -1))] * _my_filter_d[int(2)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 1), (x2 + -1))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 1), (x2 + 0))] * _my_filter_d[int(1)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 1), (x2 + 0))])))]));
@        _my_out_grid[x3] = (_my_out_grid[x3] + ((_my_in_img[_in_img_array_macro((x1 + 1), (x2 + 1))] * _my_filter_d[int(2)]) * _my_filter_s[abs(int((_my_in_img[_in_img_array_macro((x1 + 0), (x2 + 0))] - _my_in_img[_in_img_array_macro((x1 + 1), (x2 + 1))])))]));
@      }
@    }
@  }

def gaussian(stdev, length):
    result = StencilGrid([length])
    scale = 1.0/(stdev*math.sqrt(2.0*math.pi))
    divisor = -1.0 / (2.0 * stdev * stdev)
    for x in xrange(length):
       result[x] = scale * math.exp(float(x) * float(x) * divisor)
    return result

pixels = map(ord, list(image_in.read(width * height))) # Read in grayscale values
intensity = float(sum(pixels))/len(pixels)

kernel = Kernel()
kernel.should_unroll = False
out_grid = StencilGrid([width,height])
out_grid.ghost_depth = radius
in_grid = StencilGrid([width,height])
in_grid.ghost_depth = radius
for x in range(-radius,radius+1):
    for y in range(-radius,radius+1):
        in_grid.neighbor_definition[1].append( (x,y) )

for x in range(0,width):
    for y in range(0,height):
        in_grid.data[(x, y)] = pixels[y * width + x]

kernel.kernel(in_grid, gaussian(stdev_d, radius*2), gaussian(stdev_s, 256), out_grid)

for x in range(0,width):
    for y in range(0,height):
        pixels[y * width + x] = out_grid.data[(x, y)]
out_intensity = float(sum(pixels))/len(pixels)
for i in range(0, len(pixels)):
    pixels[i] = min(255, max(0, int(pixels[i] * (intensity/out_intensity))))

image_out = open('out.raw', 'wb')
image_out.write(''.join(map(chr, pixels)))
"""
    next_dict = {(13, 6) : (0,1), (13, 7) : (0,1), (13, 8) : (0,1), (13, 9) : (1,1),
                 (14, 10): (0,1), (14, 13): (0,1), (14, 16): (1,1),
                 (15, 17): (1,0), (16, 17): (1,1), 
                 (15, 18): (1,0), (16, 18): (1,1), 
                 (15, 19): (1,0), (16, 19): (1,1), 
                 (15, 20): (1,0), (16, 20): (1,1), 
                 (15, 21): (1,0), (16, 21): (1,1), 
                 (15, 22): (1,0), (16, 22): (1,1), 
                 (15, 23): (1,0), (16, 23): (1,1), 
                 (15, 24): (1,0), (16, 24): (1,1), 
                 (15, 25): (1,0), (16, 25): (1,1), 
                 (15, 26): (1,0), (16, 26): (1,1), 
                 (15, 27): (1,0), (16, 27): (1,1), 
                 (15, 28): (1,0), (16, 28): (1,1), 
                 (15, 29): (1,0), (16, 29): (2,1), 
                }
    form = Form(mixedText, 'bilateral_filter.py', '/tmp/asp_cache/476da69a7cd754a699054871fbf8ae12/module.cpp', 12, 'bilateral_filter.2.py', ['break 44', 'continue', 's', 'r', 's', 'r', 's'], next_dict, cpp_offset_lines=5, cpponly=cpponly)
else:
    raise RuntimeError("Invalid example number, must be 1 or 2")
form.show()
result = app.exec_()
log('Exiting with result ' + str(result))
sys.exit(result)


########NEW FILE########
__FILENAME__ = pdb
import subprocess
import re
import os

class pdb(object):
    def __init__(self, python_file, python_start_line):
        self.process = subprocess.Popen(["PYTHONPATH=../../specializers/stencil:../.. python -u /usr/bin/pdb " + python_file],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, cwd='.')
        for line in python_start_line:
            self.process.stdin.write(line + "\n")

    # Read up to current position in output
    def sync_pos(self):
        self.process.stdin.write("print 'sync375023'\n")
        line = "\n"
        while line:
            line = self.process.stdout.readline()
            if 'sync375023' in line:
                break
        line = self.process.stdout.read(len("(Pdb) "))

    def get_current_stack(self):
        self.sync_pos()
        self.process.stdin.write("bt\n")
        while True:
            line = self.process.stdout.readline().strip()
            if len(line) > 0 and line[0] == '>':
                m = re.match(r'^> (.*)\(([0-9]+)\)([A-Za-z0-9_]+)\(\)', line)
                if m:
                    result = dict()
                    result['filename'] = m.group(1)
                    result['line_no'] = int(m.group(2))
                    result['method_name'] = m.group(3)
                    return result
                else:
                    raise RuntimeError('Could not match regex on stack line:', line)

    def next(self):
        self.process.stdin.write("n\n")

    def quit(self):
        self.process.stdin.write("quit\n")
        self.process.stdout.read() # Read to end

    def read_expr(self, expr):
        self.sync_pos()
        self.process.stdin.write("print " + expr + "\n")
        return self.process.stdout.readline().strip()

if __name__ == '__main__':
    pdb = pdb()
    for x in range(10):
        stack = pdb.get_current_stack()
        print stack['line_no']
        print 'x:', pdb.read_expr('x')
        print 'y:', pdb.read_expr('y')
        print 'out_grid[x]:', pdb.read_expr('out_grid[x]')
        print 'in_grid[y]:', pdb.read_expr('in_grid[y]')
        pdb.next()

    pdb.quit()

########NEW FILE########
__FILENAME__ = assert_utils
"""Utilities for checking object types using assertions.
"""

from types import *

def assert_has_type(x, t, x_name='obj'):
    if type(t) is ListType:
        type_found = False
        for t2 in t:
            if isinstance(x, t2):
                type_found = True
        assert type_found, "%s is not one of the types %s: %s" % (x_name, t, `x`)
    else:
        assert isinstance(x, t), "%s is not %s: %s" % (x_name, t, `x`)

def assert_is_list_of(lst, t, lst_name='list'):
    assert_has_type(lst, ListType, lst_name)
    for x in lst:
        assert_has_type(x, t, "%s element" % lst_name)

########NEW FILE########
__FILENAME__ = stencil_convert
"""Takes an unrolled StencilModel and converts it to a C++ AST.

The third stage in processing. Input must be processed with
StencilUnrollNeighborIter first to remove neighbor loops and
InputElementZeroOffset nodes. Done once per call.
"""

import ast
import asp.codegen.cpp_ast as cpp_ast
import asp.codegen.ast_tools as ast_tools
import stencil_model
from assert_utils import *

class StencilConvertAST(ast_tools.ConvertAST):
    def __init__(self, model, input_grids, output_grid, inject_failure=None):
        assert_has_type(model, stencil_model.StencilModel)
        assert len(input_grids) == len(model.input_grids), 'Incorrect number of input grids'
        self.model = model
        self.input_grids = input_grids
        self.output_grid = output_grid
        self.output_grid_name = 'out_grid'
        self.dim_vars = []
        self.var_names = [self.output_grid_name]
        self.next_fresh_var = 0
        self.inject_failure = inject_failure
        super(StencilConvertAST, self).__init__()

    def run(self):
        self.model = self.visit(self.model)
        assert_has_type(self.model, cpp_ast.FunctionBody)
        StencilConvertAST.VerifyOnlyCppNodes().visit(self.model)
        return self.model

    class VerifyOnlyCppNodes(ast_tools.NodeVisitorCustomNodes):
        def visit(self, node):
            for field, value in ast.iter_fields(node):
                if type(value) in [StringType, IntType, LongType, FloatType]:
                    pass
                elif isinstance(value, list):
                    for item in value:
                        if ast_tools.is_cpp_node(item):
                            self.visit(item)
                elif ast_tools.is_cpp_node(value):
                    self.visit(value)
                else:
                    assert False, 'Expected only codepy.cgen.Generable nodes and primitives but found %s' % value

    # Visitors
    
    def visit_StencilModel(self, node):
        self.argdict = dict()
        for i in range(len(node.input_grids)):
            self.var_names.append(node.input_grids[i].name)
            self.argdict[node.input_grids[i].name] = self.input_grids[i]
        self.argdict[self.output_grid_name] = self.output_grid

        assert node.border_kernel.body == [], 'Border kernels not yet implemented'

        func_name = "kernel"
        arg_names = [x.name for x in node.input_grids] + [self.output_grid_name]
        args = [cpp_ast.Pointer(cpp_ast.Value("PyObject", x)) for x in arg_names]

        body = cpp_ast.Block()

        # generate the code to unpack arrays into C++ pointers and macros for accessing
        # the arrays
        body.extend([self.gen_array_macro_definition(x) for x in self.argdict])
        body.extend(self.gen_array_unpack())

        body.append(self.visit_interior_kernel(node.interior_kernel))
        return cpp_ast.FunctionBody(cpp_ast.FunctionDeclaration(cpp_ast.Value("void", func_name), args),
                                    body)

    def visit_interior_kernel(self, node):
        cur_node, ret_node = self.gen_loops(node)

        body = cpp_ast.Block()
        
        self.output_index_var = cpp_ast.CName(self.gen_fresh_var())
        body.append(cpp_ast.Value("int", self.output_index_var))
        body.append(cpp_ast.Assign(self.output_index_var,
                                   self.gen_array_macro(
                                       self.output_grid_name, [cpp_ast.CName(x) for x in self.dim_vars])))

        replaced_body = None
        for gridname in self.argdict.keys():
            replaced_body = [ast_tools.ASTNodeReplacer(
                            ast.Name(gridname, None), ast.Name("_my_"+gridname, None)).visit(x) for x in node.body]
        body.extend([self.visit(x) for x in replaced_body])

        cur_node.body = body

        return ret_node

    def visit_OutputAssignment(self, node):
        return cpp_ast.Assign(self.visit(stencil_model.OutputElement()), self.visit(node.value))

    def visit_Constant(self, node):
        return node.value

    def visit_ScalarBinOp(self, node):
        return super(StencilConvertAST, self).visit_BinOp(ast.BinOp(node.left, node.op, node.right))

    def visit_OutputElement(self, node):
        return cpp_ast.Subscript("_my_" + self.output_grid_name, self.output_index_var)

    def visit_InputElement(self, node):
        index = self.gen_array_macro(node.grid.name,
                                     map(lambda x,y: cpp_ast.BinOp(cpp_ast.CName(x), "+", cpp_ast.CNumber(y)),
                                         self.dim_vars,
                                         node.offset_list))
        return cpp_ast.Subscript("_my_" + node.grid.name, index)

    def visit_InputElementExprIndex(self, node):
        return cpp_ast.Subscript("_my_" + node.grid.name, self.visit(node.index))

    def visit_MathFunction(self, node):
        return cpp_ast.FunctionCall(cpp_ast.CName(node.name), params=map(self.visit, node.args))

    # Helper functions
    
    def gen_array_macro_definition(self, arg):
        array = self.argdict[arg]
        defname = "_"+arg+"_array_macro"
        params = "(" + ','.join(["_d"+str(x) for x in xrange(array.dim)]) + ")"
        calc = "(_d%d" % (array.dim-1)
        for x in range(0,array.dim-1):
            calc += "+(_d%s * %s)" % (str(x), str(array.data.strides[x]/array.data.itemsize))
        calc += ")"
        return cpp_ast.Define(defname+params, calc)

    def gen_array_macro(self, arg, point):
        name = "_%s_array_macro" % arg
        return cpp_ast.Call(cpp_ast.CName(name), point)

    def gen_array_unpack(self):
        ret =  [cpp_ast.Assign(cpp_ast.Pointer(cpp_ast.Value("npy_double", "_my_"+x)), 
                cpp_ast.TypeCast(cpp_ast.Pointer(cpp_ast.Value("npy_double", "")), cpp_ast.FunctionCall(cpp_ast.CName("PyArray_DATA"), params=[cpp_ast.CName(x)])))
                for x in self.argdict.keys()]

        return ret

    def gen_loops(self, node):
        dim = len(self.output_grid.shape)

        ret_node = None
        cur_node = None

        def add_one(n):
            if self.inject_failure == 'loop_off_by_one':
                return cpp_ast.CNumber(n.num + 1)
            else:
                return n

        for d in xrange(dim):
            dim_var = self.gen_fresh_var()
            self.dim_vars.append(dim_var)

            initial = cpp_ast.CNumber(self.output_grid.ghost_depth)
            end = cpp_ast.CNumber(self.output_grid.shape[d]-self.output_grid.ghost_depth-1)
            increment = cpp_ast.CNumber(1)
            if d == 0:
                ret_node = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node = ret_node
            elif d == dim-2:
                # add OpenMP parallel pragma to 2nd innermost loop
                pragma = cpp_ast.Pragma("omp parallel for")
                for_node = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node.body = cpp_ast.Block(contents=[pragma, for_node])
                cur_node = for_node
            elif d == dim-1:
                # add ivdep pragma to innermost node
                pragma = cpp_ast.Pragma("ivdep")
                for_node = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment,
                                            cpp_ast.Block())
                cur_node.body = cpp_ast.Block(contents=[pragma, for_node])
                cur_node = for_node
            else:
                cur_node.body = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node = cur_node.body

        
        return (cur_node, ret_node)

    def gen_fresh_var(self):
        while True:
            self.next_fresh_var += 1
            var = "x%d" % self.next_fresh_var
            if var not in self.var_names:
                return var

class StencilConvertASTCilk(StencilConvertAST):
    class CilkFor(cpp_ast.For):
        def intro_line(self):
            return "cilk_for (%s; %s; %s += %s)" % (self.start, self.condition, self.loopvar, self.increment)

    def gen_loops(self, node):
        dim = len(self.output_grid.shape)

        ret_node = None
        cur_node = None

        for d in xrange(dim):
            dim_var = self.gen_fresh_var()
            self.dim_vars.append(dim_var)

            initial = cpp_ast.CNumber(self.output_grid.ghost_depth)
            end = cpp_ast.CNumber(self.output_grid.shape[d]-self.output_grid.ghost_depth-1)
            increment = cpp_ast.CNumber(1)
            if d == 0:
                ret_node = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node = ret_node
            elif d == dim-2:
                cur_node.body = StencilConvertASTCilk.CilkFor(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node = cur_node.body
            else:
                cur_node.body = cpp_ast.For(dim_var, add_one(initial), add_one(end), increment, cpp_ast.Block())
                cur_node = cur_node.body

        return (cur_node, ret_node)

########NEW FILE########
__FILENAME__ = stencil_grid
"""A two-dimension grid of numeric values, used for input and output to a stencil kernel.
"""

import numpy
import math

class StencilGrid(object):

    def __init__(self, size):
        self.dim = len(size)
        self.data = numpy.zeros(size)
        self.shape = size
        self.ghost_depth = 1

        self.set_grid_variables()
        self.set_interior()
        # add default neighbor definition
        self.set_default_neighbor_definition()

    # want this to be indexable
    def __getitem__(self, x):
        return self.data[x]

    def __setitem__(self, x, y):
        self.data[x] = y

    def set_grid_variables(self):
        self.grid_variables = ["DIM"+str(x) for x in range(0,self.dim)]

    def set_interior(self):
        """
        Sets the number of interior points in each dimension
        """
        self.interior = [x-2*self.ghost_depth for x in self.shape]

    def set_default_neighbor_definition(self):
        """
        Sets the default for neighbors[0] and neighbors[1].  Note that neighbors[1]
        does not include the center point.
        """
        self.neighbor_definition = []

        self.neighbor_definition.append([tuple([0 for x in range(self.dim)])])
        self.neighbor_definition.append([])

        for x in range(self.dim):
            for y in [0, 1, -1]:
                tmp = list(self.neighbor_definition[0][0])
                tmp[x] += y
                tmp = tuple(tmp)
                if tmp != self.neighbor_definition[0][0]:
                    self.neighbor_definition[1].append(tmp)



    def interior_points(self):
        """
        Iterator over the interior points of the grid.  Only executed
        in pure Python mode; in SEJITS mode, it should be executed only
        in the translated language/library.
        """
        import itertools
        all_dims = [range(self.ghost_depth,self.shape[x]-self.ghost_depth) for x in range(0,self.dim)]
        for item in itertools.product(*all_dims):
            yield tuple(item)

    def border_points(self):
        """
        Iterator over the border points of a grid.  Only executed in pure Python
        mode; in SEJITS mode, it should be executed only in the translated
        language/library.
        """
        # TODO
        return []


    def neighbors(self, center, neighbors_id):
        """
        Returns the list of neighbors with the given neighbors_id. By
        default, IDs 0 and 1 give the list consisting of all
        points at a distance of 0 and 1 from the center point,
        respectively. Uses neighbor_definition to determine what the
        neighbors are.
        """
        # return tuples for each neighbor
        for neighbor in self.neighbor_definition[neighbors_id]:
            yield tuple(map(lambda a,b: a+b, list(center), list(neighbor)))

    def __repr__(self):
        return self.data.__repr__()

def distance(x,y):
    return math.sqrt(sum([(x[i]-y[i])**2 for i in range(0,len(x))]))

def manhattan_distance(x,y):
    return sum([abs(x[i]-y[i]) for i in range(0,len(x))])

########NEW FILE########
__FILENAME__ = stencil_kernel
"""The main driver, intercepts the kernel() call and invokes the other components.

Stencil kernel classes are subclassed from the StencilKernel class
defined here. At initialization time, the text of the kernel() method
is parsed into a Python AST, then converted into a StencilModel by
stencil_python_front_end. The kernel() function is replaced by
shadow_kernel(), which intercepts future calls to kernel().

During each call to kernel(), stencil_unroll_neighbor_iter is called
to unroll neighbor loops, stencil_convert is invoked to convert the
model to C++, and an external compiler tool is invoked to generate a
binary which then efficiently completes executing the call. The binary
is cached for future calls.
"""

import numpy
import inspect
from stencil_grid import *
from stencil_python_front_end import *
from stencil_unroll_neighbor_iter import *
from stencil_optimize_cpp import *
from stencil_convert import *
import asp.codegen.python_ast as ast
import asp.codegen.cpp_ast as cpp_ast
import asp.codegen.ast_tools as ast_tools
from asp.util import *
import copy

# may want to make this inherit from something else...
class StencilKernel(object):
    def __init__(self, with_cilk=False, inject_failure=None):
        self.inject_failure = inject_failure

        # we want to raise an exception if there is no kernel()
        # method defined.
        try:
            dir(self).index("kernel")
        except ValueError:
            raise Exception("No kernel method defined.")

        # get text of kernel() method and parse into a StencilModel
        self.kernel_src = inspect.getsource(self.kernel)
        # print(self.kernel_src)
        self.kernel_ast = ast.parse(self.remove_indentation(self.kernel_src))
        # print(ast.dump(self.kernel_ast, include_attributes=True))
        self.model = StencilPythonFrontEnd().parse(self.kernel_ast)
        # print(ast.dump(self.model, include_attributes=True))

        self.pure_python = False
        self.pure_python_kernel = self.kernel
        self.should_unroll = True
        self.should_cacheblock = False
        self.block_size = 1
        
        # replace kernel with shadow version
        self.kernel = self.shadow_kernel

        self.specialized_sizes = None
        self.with_cilk = with_cilk

    def remove_indentation(self, src):
        return src.lstrip()

    def add_libraries(self, mod):
        # these are necessary includes, includedirs, and init statements to use the numpy library
        mod.add_library("numpy",[numpy.get_include()+"/numpy"])
        mod.add_header("arrayobject.h")
        mod.add_to_init([cpp_ast.Statement("import_array();")])
        if self.with_cilk:
            mod.module.add_to_preamble([cpp_ast.Include("cilk/cilk.h", True)])
        

    def shadow_kernel(self, *args):
        if self.pure_python:
            return self.pure_python_kernel(*args)

        #FIXME: instead of doing this short-circuit, we should use the Asp infrastructure to
        # do it, by passing in a lambda that does this check
        # if already specialized to these sizes, just run
        if self.specialized_sizes and self.specialized_sizes == [y.shape for y in args]:
            debug_print("match!")
            self.mod.kernel(*[y.data for y in args])
            return

        # otherwise, do the first-run flow

        # ask asp infrastructure for machine and platform info, including if cilk+ is available
        #FIXME: impelement.  set self.with_cilk=true if cilk is available
        
        input_grids = args[0:-1]
        output_grid = args[-1]
        model = copy.deepcopy(self.model)
        model = StencilUnrollNeighborIter(model, input_grids, output_grid, inject_failure=self.inject_failure).run()

        # depending on whether cilk is available, we choose which converter to use
        if not self.with_cilk:
            Converter = StencilConvertAST
        else:
            Converter = StencilConvertASTCilk

        # generate variant with no unrolling, then generate variants for various unrollings
        base_variant = Converter(model, input_grids, output_grid, inject_failure=self.inject_failure).run()
        variants = [base_variant]
        variant_names = ["kernel"]

        # we only cache block if the size is large enough for blocking
        # or if the user has told us to
        
        if (len(args[0].shape) > 1 and args[0].shape[0] > 128):
            self.should_cacheblock = True
            self.block_sizes = [16, 32, 48, 64, 128, 160, 192, 256]
        else:
            self.should_cacheblock = False
            self.block_sizes = []

        if self.should_cacheblock and self.should_unroll:
            import itertools
            for b in list(set(itertools.permutations(self.block_sizes, len(args[0].shape)-1))):
                for u in [1,2,4,8]:
                    # ensure the unrolling is valid for the given blocking

                    #if b[len(b)-1] >= u:
                    if args[0].shape[len(args[0].shape)-1] >= u:
                        c = list(b)
                        c.append(1)
                        #variants.append(Converter(model, input_grids, output_grid, unroll_factor=u, block_factor=c).run())
                        
                        variant = StencilOptimizeCpp(copy.deepcopy(base_variant), output_grid.shape, unroll_factor=u, block_factor=c).run()
                        variants.append(variant)
                        variant_names.append("kernel_block_%s_unroll_%s" % ('_'.join([str(y) for y in c]) ,u))

                        debug_print("ADDING BLOCKED")
                        
        if self.should_unroll:
            for x in [2,4,8,16]: #,32,64]:
                check_valid = max(map(
                    # FIXME: is this the right way to figure out valid unrollings?
                    lambda y: (y.shape[-1]-2*y.ghost_depth) % x,
                    args))

                if check_valid == 0:
                    debug_print("APPENDING VARIANT %s" % x)
                    variants.append(StencilOptimizeCpp(copy.deepcopy(base_variant), output_grid.shape, unroll_factor=x).run())
                    variant_names.append("kernel_unroll_%s" % x)

        debug_print(variant_names)
        from asp.jit import asp_module

        mod = self.mod = asp_module.ASPModule()
        self.add_libraries(mod)

        self.set_compiler_flags(mod)
        mod.add_function("kernel", variants, variant_names)

        # package arguments and do the call 
        myargs = [y.data for y in args]
        mod.kernel(*myargs)

        # save parameter sizes for next run
        self.specialized_sizes = [x.shape for x in args]

    def set_compiler_flags(self, mod):
        import asp.config
        
        if self.with_cilk or asp.config.CompilerDetector().detect("icc"):
            mod.backends["c++"].toolchain.cc = "icc"
            mod.backends["c++"].toolchain.cflags += ["-intel-extensions", "-fast", "-restrict"]
            mod.backends["c++"].toolchain.cflags += ["-openmp", "-fno-fnalias", "-fno-alias"]
            mod.backends["c++"].toolchain.cflags += ["-I/usr/include/x86_64-linux-gnu"]
            mod.backends["c++"].toolchain.cflags.remove('-fwrapv')
            mod.backends["c++"].toolchain.cflags.remove('-O2')
            mod.backends["c++"].toolchain.cflags.remove('-g')
            mod.backends["c++"].toolchain.cflags.remove('-g')
            mod.backends["c++"].toolchain.cflags.remove('-fno-strict-aliasing')
        else:
            # mod.backends["c++"].toolchain.cflags += ["-fopenmp", "-O3", "-msse3", "-Wno-unknown-pragmas"]
            mod.backends["c++"].toolchain.cflags += ["-fopenmp", "-ggdb", "-msse3", "-Wno-unknown-pragmas"]

        while mod.backends["c++"].toolchain.cflags.count('-Os') > 0:
            mod.backends["c++"].toolchain.cflags.remove('-Os')
        while mod.backends["c++"].toolchain.cflags.count('-O2') > 0:
            mod.backends["c++"].toolchain.cflags.remove('-O2')
        debug_print("toolchain" + str(mod.backends["c++"].toolchain.cflags))

########NEW FILE########
__FILENAME__ = stencil_kernel_simplified
class StencilKernel(object):
    def __init__(self, with_cilk=False):
        self.kernel_ast = ast.parse(inspect.getsource(self.kernel))
        self.model = StencilPythonFrontEnd().parse(self.kernel_ast)
        self.pure_python_kernel = self.kernel
        self.kernel = self.shadow_kernel

    def shadow_kernel(self, *args):
        model = StencilUnrollNeighborIter(model, args[0:-1], args[-1]).run()
        func = StencilConvertAST(model, args[0:-1], args[-1]).run()
        func = StencilOptimizeCpp(func, args[-1].shape, unroll_factor=4, block_factor=16).run()
        variants = [variant]; variant_names = ["kernel"]

        mod = ASPModule()
        mod.add_function("kernel", func)
        mod.kernel(*[y.data for y in args])

class StencilPythonFrontEnd(ast_tools.NodeTransformer):
    # ...
    def visit_BinOp(self, node):
        return ScalarBinOp(self.visit(node.left), node.op, self.visit(node.right))

    def visit_Num(self, node):
        return Constant(node.n)

    def visit_Call(self, node):
        assert isinstance(node.func, ast.Name), 'Cannot call expression'
        if node.func.id == 'distance' and len(node.args) == 2:
            if ((node.args[0].id == self.neighbor_target.name and node.args[1].id == self.kernel_target.name) or \
                (node.args[0].id == self.kernel_target.name and node.args[1].id == self.neighbor_target.name)):
                return NeighborDistance()
            elif ((node.args[0].id == self.neighbor_target.name and node.args[1].id == self.neighbor_target.name) or \
                  (node.args[0].id == self.kernel_target.name and node.args[1].id == self.kernel_target.name)):
                return Constant(0)
            else:
                assert False, 'Unexpected arguments to distance (expected previously defined grid point)'
        else:
            return MathFunction(node.func.id, map(self.visit, node.args))
    # ...

class StencilConvertAST(ast_tools.ConvertAST):
    # ...
    def visit_InputElementExprIndex(self, node):
        return cpp_ast.Subscript("_my_" + node.grid.name, self.visit(node.index))

    def visit_ScalarBinOp(self, node):
        return super(StencilConvertAST, self).visit_BinOp(ast.BinOp(node.left, node.op, node.right))

    def visit_MathFunction(self, node):
        return cpp_ast.FunctionCall(cpp_ast.CName(node.name), params=map(self.visit, node.args))
    # ...

########NEW FILE########
__FILENAME__ = stencil_model
"""Defines the semantic model, a tree data structure representing a valid stencil kernel program.

The semantic model is specified using Asp's tree_grammar DSL.  The
stencil_model classes have generated assertions and additional manual
structural checks to prevent the construction of a tree not
corresponding to a valid stencil kernel program.
"""

import types
import ast
from assert_utils import *

from asp.tree_grammar import *
parse('''
# Tree grammar for stencil semantic model, based on language specification and other feedback

StencilModel(input_grids=Identifier*, interior_kernel=Kernel, border_kernel=Kernel)
    check StencilModelStructuralConstraintsVerifier(self).verify()
    check assert len(set([x.name for x in self.input_grids]))==len(self.input_grids), 'Input grids must have distinct names'

Identifier(name)

Kernel(body=(StencilNeighborIter | OutputAssignment)*)

StencilNeighborIter(grid=Identifier, neighbors_id=Constant, body=OutputAssignment*)
    check assert self.neighbors_id.value >= 0, "neighbors_id must be nonnegative but was: %d" % self.neighbors_id.value

# Assigns Expr to current output element
OutputAssignment(value=Expr)

Expr = Constant
     | Neighbor      # Refers to current neighbor inside a StencilNeighborIter
     | OutputElement # Refers to current output element
     | InputElement
     | InputElementZeroOffset
     | InputElementExprIndex
     | ScalarBinOp
     | MathFunction
     | NeighborDistance

Constant(value = types.IntType | types.LongType | types.FloatType)

# Offsets are relative to current output element location, given as a list of integers,
# one per dimension.
InputElement(grid=Identifier, offset_list=types.IntType*)

# Input element at same position as current output element
InputElementZeroOffset(grid=Identifier)

# Input element at an index given by an expression (must be 1D grid)
InputElementExprIndex(grid=Identifier, index=Expr)

# Use a built-in pure math function
MathFunction(name, args=Expr*)
    check assert self.name in math_functions.keys(), "Tried to use function \'%s\' not in math_functions list" % self.name
    check assert len(self.args) == math_functions[self.name], "Expected %d arguments to math function \'%s\' but received %d arguments" % (math_functions[self.name], self.name, len(self.args))

ScalarBinOp(left=Expr, op=(ast.Add|ast.Sub|ast.Mult|ast.Div|ast.FloorDiv|ast.Mod), right=Expr)
''', globals(), checker='StencilModelChecker')

# Gives number of arguments for each math function
math_functions = {'int':1, 'abs':1}

# Verifies a few structural constraints (semantic properties) of the tree
class StencilModelStructuralConstraintsVerifier(ast.NodeVisitor):
    def __init__(self, stencil_model):
        assert_has_type(stencil_model, StencilModel)
        self.model = stencil_model
        self.in_stencil_neighbor_iter = False
        super(StencilModelStructuralConstraintsVerifier, self).__init__()

    def verify(self):
        self.visit(self.model)

    def visit_StencilModel(self, node):
        self.input_grid_names = map(lambda x: x.name, node.input_grids)
        self.generic_visit(node)

    def visit_Identifier(self, node):
        assert node.name in self.input_grid_names, 'Identifier %s not listed among input grid identifiers' % node.name

    def visit_StencilNeighborIter(self, node):
        self.in_stencil_neighbor_iter = True
        self.generic_visit(node)
        self.in_stencil_neighbor_iter = False

    def visit_Neighbor(self, node):
        assert self.in_stencil_neighbor_iter, 'Neighbor node allowed only inside StencilNeighborIter'

########NEW FILE########
__FILENAME__ = stencil_model_interpreter
"""Takes a StencilModel and interprets it (slowly) in Python.

Facilitates isolation of bugs between stages in the specializer.
"""

from stencil_model import *
from stencil_grid import distance
import ast
from assert_utils import *
import math

class StencilModelInterpreter(ast.NodeVisitor):
    def __init__(self, stencil_model, input_grids, output_grid):
        assert_has_type(stencil_model, StencilModel)
        assert len(input_grids) == len(stencil_model.input_grids), 'Incorrect number of input grids'
        self.model = stencil_model
        self.input_grids = input_grids
        self.output_grid = output_grid
        super(StencilModelInterpreter, self).__init__()

    def run(self):
        self.visit(self.model)

    def visit_StencilModel(self, node):
        self.input_dict = dict()
        for i in range(len(node.input_grids)):
            self.input_dict[node.input_grids[i].name] = self.input_grids[i]
            
        for x in self.output_grid.interior_points():
            self.current_output_point = x
            self.visit(node.interior_kernel)
        for x in self.output_grid.border_points():
            self.current_output_point = x
            self.visit(node.border_kernel)

    def visit_Identifier(self, node):
        return self.input_dict[node.name]

    def visit_StencilNeighborIter(self, node):
        grid = self.visit(node.grid)
        neighbors_id = self.visit(node.neighbors_id)
        self.current_neighbor_grid = grid
        for x in grid.neighbors(self.current_output_point, neighbors_id):
            self.current_neighbor_point = x
            for statement in node.body:
                self.visit(statement)

    def visit_OutputAssignment(self, node):
        self.output_grid[self.current_output_point] = self.visit(node.value)
        
    def visit_Constant(self, node):
        return node.value

    def visit_Neighbor(self, node):
        return self.current_neighbor_grid[self.current_neighbor_point]

    def visit_OutputElement(self, node):
        return self.output_grid[self.current_output_point]

    def visit_InputElement(self, node):
        grid = self.visit(node.grid)
        x = tuple(map(lambda a,b: a+b, list(self.current_output_point), node.offset_list))
        return grid[x]

    def visit_InputElementZeroOffset(self, node):
        grid = self.visit(node.grid)
        return grid[self.current_output_point]

    def visit_InputElementExprIndex(self, node):
        grid = self.visit(node.grid)
        return grid[self.visit(node.index)]

    def visit_ScalarBinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if type(node.op) is ast.Add:
            return left + right
        elif type(node.op) is ast.Sub:
            return left - right
        elif type(node.op) is ast.Mult:
            return left * right
        elif type(node.op) is ast.Div:
            return left / right
        elif type(node.op) is ast.FloorDiv:
            return left // right

    math_func_to_python_func = {'abs': abs, 'int': int}

    def visit_MathFunction(self, node):
        func = self.math_func_to_python_func[node.name]
        args = map(self.visit, node.args)
        return apply(func, args)

    def visit_NeighborDistance(self, node):
        return distance(self.current_neighbor_point, self.current_output_point)

########NEW FILE########
__FILENAME__ = stencil_optimize_cpp
from asp.codegen.cpp_ast import *
import asp.codegen.ast_tools as ast_tools
from asp.util import *

class StencilOptimizeCpp(ast_tools.ConvertAST):
    """
    Does unrolling and cache blocking on the C++ AST representation.
    """
    
    def __init__(self, model, output_grid_shape, unroll_factor, block_factor=None):    
        self.model = model
        self.output_grid_shape = output_grid_shape
        self.unroll_factor = unroll_factor
        self.block_factor = block_factor
        super(StencilOptimizeCpp, self).__init__()

    def run(self):
        self.model = self.visit(self.model)
        return self.model

    def visit_FunctionDeclaration(self, node):
        if self.block_factor:
            node.subdecl.name = "kernel_block_%s_unroll_%s" % ('_'.join([str(x) for x in self.block_factor]), self.unroll_factor)
        else:
            node.subdecl.name = "kernel_unroll_%s" % self.unroll_factor
        return node

    def visit_FunctionBody(self, node):
        # need to add the min macro, which is used by blocking
        macro = Define("min(_a,_b)", "(_a < _b ?  _a : _b)")
        node.body.contents.insert(0, macro)
        self.visit(node.fdecl)
        for i in range(0, len(node.body.contents)):
            node.body.contents[i] = self.visit(node.body.contents[i])
        return node

    def visit_For(self, node):
        inner = FindInnerMostLoop().find(node)
        if self.block_factor:
            (inner, node) = self.block_loops(inner=inner, unblocked=node)
        new_inner = ast_tools.LoopUnroller().unroll(inner, self.unroll_factor)
        node = ast_tools.ASTNodeReplacerCpp(inner, new_inner).visit(node)
        return node

    def block_loops(self, inner, unblocked):
        #factors = [self.block_factor for x in self.output_grid_shape]
        #factors[len(self.output_grid_shape)-1] = 1

        
        # use the helper class below to do the actual blocking.
        blocked = StencilCacheBlocker().block(unblocked, self.block_factor)

        # need to update inner to point to the innermost in the new blocked version
        inner = FindInnerMostLoop().find(blocked)

        assert(inner != None)
        return [inner, blocked]

  

class StencilCacheBlocker(object):
    """
    Class that takes a tree of perfectly-nested For loops (as in a stencil) and performs standard cache blocking
    on them.  Usage: StencilCacheBlocker().block(tree, factors) where factors is a tuple, one for each loop nest
    in the original tree.
    """
    class StripMineLoopByIndex(ast_tools.NodeTransformer):
        """Helper class that strip mines a loop of a particular index in the nest."""
        def __init__(self, index, factor):
            self.current_idx = -1
            self.target_idx = index
            self.factor = factor
            super(StencilCacheBlocker.StripMineLoopByIndex, self).__init__()
            
        def visit_For(self, node):
            self.current_idx += 1

            debug_print("Searching for loop %d, currently at %d" % (self.target_idx, self.current_idx))

            if self.current_idx == self.target_idx:
                debug_print("Before blocking:")
                debug_print(node)
                
                return ast_tools.LoopBlocker().loop_block(node, self.factor)
            else:
                return For(node.loopvar,
                           node.initial,
                           node.end,
                           node.increment,
                           self.visit(node.body))
            
    def block(self, tree, factors):
        """Main method in StencilCacheBlocker.  Used to block the loops in the tree."""
        # first we apply strip mining to the loops given in factors
        for x in xrange(len(factors)):
            debug_print("Doing loop %d by %d" % (x*2, factors[x]))

            # we may want to not block a particular loop, e.g. when doing Rivera/Tseng blocking
            if factors[x] > 1:
                tree = StencilCacheBlocker.StripMineLoopByIndex(x*2, factors[x]).visit(tree)
            debug_print(tree)

        # now we move all the outer strip-mined loops to be outermost
        for x in xrange(1,len(factors)):
            if factors[x] > 1:
                tree = self.bubble(tree, 2*x, x)

        return tree
        
    def bubble(self, tree, index, new_index):
        """
        Helper function to 'bubble up' a loop at index to be at new_index (new_index < index)
        while preserving the ordering of the loops between index and new_index.
        """
        for x in xrange(index-new_index):
            debug_print("In bubble, switching %d and %d" % (index-x-1, index-x))
            tree = ast_tools.LoopSwitcher().switch(tree, index-x-1, index-x)
        return tree

class FindInnerMostLoop(ast_tools.NodeVisitor):
    """
    Helper class that returns the innermost loop of perfectly nested loops.
    """
    def __init__(self):
        self.inner_most = None

    def find(self, node):
        self.visit(node)
        return self.inner_most

    def visit_For(self, node):
        self.inner_most = node
        self.visit(node.body)

########NEW FILE########
__FILENAME__ = stencil_python_front_end
"""Takes a Python AST and converts it to a corresponding StencilModel.

Throws an exception if the input does not represent a valid stencil
kernel program. This is the first stage of processing and is done only
once when a stencil class is initialized.
"""

from stencil_model import *
from assert_utils import *
import ast
from asp.util import *
import asp.codegen.ast_tools as ast_tools

# class to convert from Python AST to StencilModel
class StencilPythonFrontEnd(ast_tools.NodeTransformer):
    def __init__(self):
        super(StencilPythonFrontEnd, self).__init__()

    def parse(self, ast):
        return self.visit(ast)

    def visit_Module(self, node):
        body = map(self.visit, node.body)
        assert len(body) == 1
        assert_has_type(body[0], StencilModel)
        return body[0]

    def visit_FunctionDef(self, node):
        assert len(node.decorator_list) == 0
        args = self.visit(node.args)
        assert args[0].name == 'self'
        self.output_arg = args[-1]
        self.input_args = args[1:-1]
        self.input_arg_ids = map(lambda x: x.name, self.input_args)
        kernels = map(self.visit, node.body)
        interior_kernels = map(lambda x: x['kernel'], filter(lambda x: x['kernel_type'] == 'interior_points', kernels))
        border_kernels = map(lambda x: x['kernel'], filter(lambda x: x['kernel_type'] == 'border_points', kernels))
        assert len(interior_kernels) <= 1, 'Can only have one loop over interior points'
        assert len(border_kernels) <= 1, 'Can only have one loop over border points'
        return StencilModel(self.input_args,
                            interior_kernels[0] if len(interior_kernels) > 0 else Kernel([]),
                            border_kernels[0] if len(border_kernels) > 0 else Kernel([]))

    def visit_arguments(self, node):
        assert node.vararg == None, 'kernel function may not take variable argument list'
        assert node.kwarg == None, 'kernel function may not take variable argument list'
        return map (self.visit, node.args)

    def visit_Name(self, node):
        return Identifier(node.id)

    def visit_For(self, node):
        # check if this is the right kind of For loop
        if (type(node.iter) is ast.Call and
            type(node.iter.func) is ast.Attribute):

            if (node.iter.func.attr == "interior_points" or
                node.iter.func.attr == "border_points"):
                assert node.iter.args == [] and node.iter.starargs == None and node.iter.kwargs == None, 'Invalid argument list for %s()' % node.iter.func.attr
                grid = self.visit(node.iter.func.value)
                assert grid.name == self.output_arg.name, 'Can only iterate over %s of output grid "%s" but "%s" was given' % (node.iter.func.attr, self.output_arg.name, grid.name)
                self.kernel_target = self.visit(node.target)
                body = map(self.visit, node.body)
                self.kernel_target = None
                return {'kernel_type': node.iter.func.attr, 'kernel': Kernel(body, lineno=node.lineno, col_offset=node.col_offset)}

            elif node.iter.func.attr == "neighbors":
                assert len(node.iter.args) == 2 and node.iter.starargs == None and node.iter.kwargs == None, 'Invalid argument list for neighbors()'
                neighbor_grid = self.visit(node.iter.func.value)
                self.neighbor_grid = neighbor_grid
                assert self.neighbor_grid.name in self.input_arg_ids, 'Can only iterate over neighbors in an input grid but "%s" was given' % self.neighbor_grid.name
                neighbors_of_grid = self.visit(node.iter.args[0])
                assert neighbors_of_grid.name == self.kernel_target.name, 'Can only iterate over neighbors of an output grid point but "%s" was given' % neighbors_of_grid.name
                self.neighbor_target = self.visit(node.target)
                body = map(self.visit, node.body)
                self.neighbor_target = None
                self.neigbor_grid = None
                neighbors = self.visit(node.iter.args[1])
                return StencilNeighborIter(neighbor_grid, neighbors, body)
            else:
                assert False, 'Invalid call in For loop argument \'%s\', can only iterate over interior_points, boder_points, or neighbor_points of a grid' % node.iter.func.attr
        else:
            assert False, 'Unexpected For loop \'%s\', can only iterate over interior_points, boder_points, or neighbor_points of a grid' % node

    def visit_AugAssign(self, node):
        target = self.visit(node.target)
        assert type(target) is OutputElement, 'Only assignments to current output element permitted'
        return OutputAssignment(ScalarBinOp(target, node.op, self.visit(node.value), lineno=node.lineno, col_offset=node.col_offset))

    def visit_Assign(self, node):
        targets = map (self.visit, node.targets)
        assert len(targets) == 1 and type(targets[0]) is OutputElement, 'Only assignments to current output element permitted'
        return OutputAssignment(self.visit(node.value))

    def visit_Subscript(self, node):
        if type(node.slice) is ast.Index:
            grid = self.visit(node.value)
            target = self.visit(node.slice.value)
            if isinstance(target, Identifier):
                if grid.name == self.output_arg.name and target.name == self.kernel_target.name:
                    return OutputElement()
                elif isinstance(target, Identifier) and target.name == self.kernel_target.name:
                    return InputElementZeroOffset(grid)
                elif grid.name == self.neighbor_grid.name and target.name == self.neighbor_target.name:
                    return Neighbor()
                else:
                    assert False, 'Unexpected subscript index \'%s\' on grid \'%s\'' % (target.name, grid.name)
            elif isinstance(target, Expr):
                return InputElementExprIndex(grid, target)
            else:
                assert False, 'Unexpected subscript index \'%s\' on grid \'%s\'' % (target, grid.name)
        else:
            assert False, 'Unsupported subscript object \'%s\' on grid \'%s\'' % (node.slice, grid.name)

    def visit_BinOp(self, node):
        return ScalarBinOp(self.visit(node.left), node.op, self.visit(node.right))

    def visit_Num(self, node):
        return Constant(node.n)

    def visit_Call(self, node):
        assert isinstance(node.func, ast.Name), 'Cannot call expression'
        if node.func.id == 'distance' and len(node.args) == 2:
            if ((node.args[0].id == self.neighbor_target.name and node.args[1].id == self.kernel_target.name) or \
                (node.args[0].id == self.kernel_target.name and node.args[1].id == self.neighbor_target.name)):
                return NeighborDistance()
            elif ((node.args[0].id == self.neighbor_target.name and node.args[1].id == self.neighbor_target.name) or \
                  (node.args[0].id == self.kernel_target.name and node.args[1].id == self.kernel_target.name)):
                return Constant(0)
            else:
                assert False, 'Unexpected arguments to distance (expected previously defined grid point)'
        else:
            return MathFunction(node.func.id, map(self.visit, node.args))

########NEW FILE########
__FILENAME__ = stencil_unroll_neighbor_iter
"""Unrolls neighbor loops and InputElementZeroOffset nodes in a StencilModel.

The second stage in stencil kernel processing, after
stencil_python_front_end and before stencil_convert. This stage is
done once per call because the dimensions of the input are needed.
"""

from stencil_model import *
from stencil_grid import *
import ast
from assert_utils import *
from copy import deepcopy

class StencilUnrollNeighborIter(ast.NodeTransformer):
    def __init__(self, stencil_model, input_grids, output_grid, inject_failure=None):
        assert_has_type(stencil_model, StencilModel)
        assert len(input_grids) == len(stencil_model.input_grids), 'Incorrect number of input grids'
        self.model = stencil_model
        self.input_grids = input_grids
        self.output_grid = output_grid
        self.inject_failure = inject_failure
        super(StencilUnrollNeighborIter, self).__init__()

    class NoNeighborIterChecker(ast.NodeVisitor):
        def __init__(self):
            super(StencilUnrollNeighborIter.NoNeighborIterChecker, self).__init__()

        def visit_StencilNeighborIter(self, node):
            assert False, 'Encountered StencilNeighborIter but all should have been removed'

        def visit_InputElementZeroOffset(self, node):
            assert False, 'Encountered InputElementZeroOffset but all should have been removed'

        def visit_NeighborDistance(self, node):
            assert False, 'Encountered NeighborDistance but all should have been removed'

    def run(self):
        self.visit(self.model)
        StencilModelChecker().visit(self.model)
        StencilUnrollNeighborIter.NoNeighborIterChecker().visit(self.model)
        return self.model

    def visit_StencilModel(self, node):
        self.input_dict = dict()
        for i in range(len(node.input_grids)):
            self.input_dict[node.input_grids[i].name] = self.input_grids[i]
        self.generic_visit(node)

    def visit_Kernel(self, node):
        body = []
        for statement in node.body:
            if type(statement) is StencilNeighborIter:
                body.extend(self.visit_StencilNeighborIter_return_list(statement))
            else:
                body.append(self.visit(statement))
        return Kernel(body)

    def visit_StencilNeighborIter_return_list(self, node):
        grid = self.input_dict[node.grid.name]
        neighbors_id = node.neighbors_id.value
        zero_point = tuple([0 for x in range(grid.dim)])
        result = []
        self.current_neighbor_grid_id = node.grid
        for x in grid.neighbors(zero_point, neighbors_id):
            self.offset_list = list(x)
            for statement in node.body:
                result.append(self.visit(deepcopy(statement)))
        self.offset_list = None
        self.current_neighbor_grid = None
        return result

    def visit_Neighbor(self, node):
        return InputElement(self.current_neighbor_grid_id, self.offset_list)

    def visit_InputElementZeroOffset(self, node):
        grid = self.input_dict[node.grid.name]
        zero_point = tuple([0 for x in range(grid.dim)])
        return InputElement(node.grid, zero_point)

    def visit_InputElementExprIndex(self, node):
        grid = self.input_dict[node.grid.name]
        assert grid.dim == 1, 'Grid \'%s\' has dimension %s but expected dimension 1 because this kernel indexes into it using an expression' % (grid, grid.dim)
        self.generic_visit(node)
        return node

    def visit_NeighborDistance(self, node):
        zero_point = tuple([0 for x in range(len(self.offset_list))])
        if self.inject_failure=='manhattan_distance':
            return Constant(manhattan_distance(zero_point, self.offset_list))
        else:
            return Constant(distance(zero_point, self.offset_list))

########NEW FILE########
__FILENAME__ = stencil_kernel_example.2
from stencil_kernel import *
import stencil_grid
import numpy

class ExampleKernel(object):
    def kernel(self, in_grid, out_grid):
        for x in out_grid.interior_points():
            for y in in_grid.neighbors(x, 1):
                out_grid[x] = out_grid[x] + in_grid[y]

in_grid = StencilGrid([5,5])
for x in range(0,5):
    for y in range(0,5):
        in_grid.data[x,y] = x + y

out_grid = StencilGrid([5,5])
ExampleKernel().kernel(in_grid, out_grid)
print out_grid

########NEW FILE########
__FILENAME__ = stencil_kernel_example
from stencil_kernel import *
import stencil_grid
import numpy

class ExampleKernel(StencilKernel):
    def kernel(self, in_grid, out_grid):
        for x in out_grid.interior_points():
            for y in in_grid.neighbors(x, 1):
                out_grid[x] = out_grid[x] + in_grid[y]

in_grid = StencilGrid([5,5])
for x in range(0,5):
    for y in range(0,5):
        in_grid.data[x,y] = x + y

out_grid = StencilGrid([5,5])
ExampleKernel(inject_failure='loop_off_by_one').kernel(in_grid, out_grid)
print out_grid

########NEW FILE########
