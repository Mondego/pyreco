__FILENAME__ = code_hasher
"""
This module provides a CodeHasher object that groups raw code lines in
full code blocks ready for execution.
"""

import token
import tokenize
import re
import StringIO
import platform

from options import parse_options

PYTHON_VERSION = int(''.join(str(s) for s in 
                            platform.python_version_tuple()[:2]))

def xreadlines(s):
    """ Helper function to use a string in the code hasher:
    blocks = iterblock(xreadlines('1\n2\n\n3'))
    """
    if  s and not s[-1]=="\n":
        s += "\n"
    return (line for line in StringIO.StringIO(s))


##############################################################################
class Token(object):
    """ A token object"""

    def __init__(self, token_desc):
        """ Builds a token object from the output of
            tokenize.generate_tokens"""
        self.type = token.tok_name[token_desc[0]]
        self.content = token_desc[1]
        self.start_row = token_desc[2][0]
        self.start_col = token_desc[2][1]
        self.end_row = token_desc[3][0]
        self.end_col = token_desc[3][1]

    def __repr__(self):
        return str((self.type, self.content))


##############################################################################
class CodeLine(object):
    """ An object representing a full logical line of code """
    string = ""
    open_symbols = {'{':0, '(':0, '[':0}
    closing_symbols = {'}':'{', ')':'(', ']':'['} 
    brakets_balanced = True
    end_col = 0
    last_token_type = ""
    complete = False
    options = {}

    def __init__(self, start_row):
        self.start_row = start_row
        self.end_row = start_row
    
    def append(self, token):
        """ Appends a token to the line while keeping the integrity of
            the line, and checking if the logical line is complete.
        """
        # The token content does not include whitespace, so we need to pad it
        # adequately
        token_started_new_line = False
        if token.start_row > self.end_row:
            self.end_col = 0
            token_started_new_line = True
        self.string += (token.start_col - self.end_col) * " " + token.content
        self.end_row = token.end_row
        self.end_col = token.end_col
        self.last_token_type = token.type

        # Keep count of the open and closed brakets.
        if token.type == 'OP':
            if token.content in self.open_symbols:
                self.open_symbols[token.content] += 1
            elif token.content in self.closing_symbols:
                self.open_symbols[self.closing_symbols[token.content]] += -1
            self.brakets_balanced = ( self.open_symbols.values() == [0, 0, 0] ) 
        
        self.complete = ( self.brakets_balanced 
                          and ( token.type in ('NEWLINE', 'ENDMARKER')
                                or ( token_started_new_line
                                      and token.type == 'COMMENT' )
                              )
                        )
        if ( token.type == 'COMMENT' 
                    and token_started_new_line 
                    and token.content[:10] == "#pyreport " ):
            self.options.update(parse_options(self.string[10:].split(" "))[0])

    def isnewblock(self):
        """ This functions checks if the code line start a new block.
        """
        # First get read of the leading empty lines:
        string = re.sub(r"\A([\t ]*\n)*", "", self.string)
        if re.match(r"elif|else|finally|except| |\t", string):
            return False
        else:
            return True        

    def __repr__(self):
        return('<CodeLine object, id %i, line %i, %s>'
                    % (id(self), self.start_row, repr(self.string) ) )


##############################################################################
class CodeBlock(object):
    """ Object that represents a full executable block """
    string = ""
    options = {}

    def __init__(self, start_row):
        self.start_row = start_row
        self.end_row = start_row

    def append(self, codeline):
        self.string += codeline.string
        self.options.update(codeline.options)

    def __repr__(self):
        return('<CodeBlock object, id %i, line %i, options %s\n%s>'
                    % (id(self), self.start_row, 
                            repr(self.options), self.string ) )


##############################################################################
class CodeHasher(object):
    """ Implements a object that transforms an iterator of raw code lines
        in an iterator of code blocks.

        Input:
            self.xreadlines: iterator to raw lines of code, such as 
                                 file.xreadlines()

        Output: Generators :
            self.itercodeblocks
            self.itercodelines
            self.itertokens
    """
    options = {}

    def __init__(self, xreadlines):
        """ The constructor takes as an argument an iterator on lines such 
            as the xreadline method of a file, or what is returned by the 
            xreadline function of this module.
        """
        self.xreadlines = xreadlines

    def next_line_generator(self):
        return self.xreadlines.next().expandtabs()

    def itercodeblocks(self):
        """ Returns a generator on the blocks of this code.
        """
        codeblock = CodeBlock(0)
        last_line_has_decorator = False
        for codeline in self.itercodelines():            
            if codeline.isnewblock() and not last_line_has_decorator :
                if codeblock.string:
                    self.options.update(codeblock.options)
                    codeblock.options.update(self.options)
                    yield codeblock
                codeblock = CodeBlock(codeline.start_row)
                codeblock.append(codeline)
                line_start = codeline.string.lstrip('\n')
                if line_start and line_start[0] == '@':
                        last_line_has_decorator = True
                        continue
# FIXME: I don't understand the purpose of this code. Until I don't have
# a test case that fail, I leave it commented out.
#                line_end = codeline.string.rstrip(" \n")
#                if line_end and line_end == ':' : 
#                    if codeblock.string:
#                        self.options.update(codeblock.options)
#                        codeblock.options.update(self.options)
#                        yield codeblock
#                    codeblock = CodeBlock(codeline.start_row)
            else:
                codeblock.append(codeline)
            last_line_has_decorator = False
        else:
            self.options.update(codeblock.options)
            codeblock.options.update(self.options)
            yield codeblock

    def itercodelines(self):
        """ Returns a generator on the logical lines of this code.
        """
        codeline = CodeLine(0)
        for token in self.itertokens():
            codeline.append(token)
            if codeline.complete:
                codeline.string = '\n'.join(s.rstrip(' ') 
                                    for s in codeline.string.split('\n'))
                yield codeline
                codeline = CodeLine(codeline.end_row + 1)
        if codeline.string:
            codeline.string = '\n'.join(s.rstrip(' ') 
                                    for s in codeline.string.split('\n'))
            yield codeline

    def itertokens(self):
        """ Returns a generator on the tokens of this code.
        """
        last_token = None
        for token_desc in tokenize.generate_tokens(self.next_line_generator):

            if PYTHON_VERSION < 26:
                yield Token(token_desc)
            else:
                # As of 2.6, tokenize.generate_tokens() chops newlines off
                # then end of comments and returns them as NL tokens. This
                # confuses the logic of the rest of pyreport, so we append
                # missing \n to COMMENT tokens, and gobble NL following a
                # comment.
                if token_desc[0] == tokenize.NL and \
                        last_token == tokenize.COMMENT:
                    last_token = token_desc[0]
                    continue
                else:
                    if token_desc[0] == tokenize.COMMENT \
                            and token_desc[1][-1] != '\n':
                        new_td = (token_desc[0], token_desc[1]+'\n', 
                                  token_desc[2], token_desc[3], token_desc[4])
                        token_desc = new_td

                    last_token = token_desc[0]
                    yield Token(token_desc)


iterblocks = lambda xreadlines: CodeHasher(xreadlines).itercodeblocks()




########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python
import numpy as np
import pylab as pl

#from pylab import imshow
#!
#! Some graphical explorations of the Julia sets with python and pyreport
#!#########################################################################
#$
#$ We start by defining a function J:
#$ \[ J_c : z \rightarrow z^2 + c \]
#$

def J(c):
    return lambda z : z**2 + c

x, y = np.ogrid[-1:1:0.002, -1:1:0.002]
z = x + y*1j

#! If we study the divergence of function J under repeated iteration
#! depending on its inital conditions we get a very pretty graph
thresh_time = np.zeros_like(z)
for i in range(40):
    z = J(0.285)(z)
    thresh_time += (z*np.conj(z) > 4)
pl.figure(0)
pl.axes([0, 0, 1, 1])
pl.axis('off')
pl.imshow(thresh_time.real, cmap=pl.cm.bone)
pl.show()

#! We can also do that systematicaly for other values of c:
pl.axes([0, 0, 1, 1])
pl.axis('off')
pl.rcParams.update({'figure.figsize': [10.5, 5]})
c_values = (0.285 + 0.013j, 0.45 - 0.1428j, -0.70176 -0.3842j,
            -0.835-0.2321j, -0.939 +0.167j, -0.986+0.87j)

for i, c in enumerate(c_values):
    thresh_time = np.zeros_like(z)
    z = x + y*1j
    for n in range(40):
        z = J(c)(z)
        thresh_time += z*np.conj(z) > 4
    pl.subplot(2, 3, i+1)
    pl.imshow(thresh_time.real)
    pl.axis('off')
pl.show()

########NEW FILE########
__FILENAME__ = main
"""
The main code of pyreport.
"""
# Author: Gael Varoquaux  <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style

# Standard library import
import sys
import re
import os
# to treat StdIn, StdOut as files:
import cStringIO
from docutils import core as docCore
from docutils import io as docIO
import copy
from traceback import format_exc
import __builtin__ # to override import ! :->
import platform
import tokenize
import token

# Local imports
from options import allowed_types, default_options, HAVE_PDFLATEX, \
        verbose_execute, silent_execute
import code_hasher
from python_parser import python2html

DEBUG = False
PYTHON_VERSION = int(''.join(str(s) for s in
                            platform.python_version_tuple()[:2]))

#------------------------ Initialisation and option parsing ------------------
def guess_names_and_types(options, allowed_types=allowed_types):
    """ This function tries to transform the current state of the options 
        to something useable. It tries to match user requests with the 
        different types possible.
    """
    # If we processing the stdin and no output has been chosen yet, output to
    # stdout
    if options.infilename == "-" and not options.outfilename :
        options.outfilename = "-"
    if not options.infilename == "-" and hasattr(options.infilename, "startswith"):
        options.infilename = os.path.abspath(options.infilename).replace(os.sep, '/')
        os.chdir(os.path.dirname(options.infilename))
    # If we are outputing to a stream rather than a file not every output
    # type is allowed
    if options.outfilename == "-" or options.outfile:
        for extension in set(("pdf", "ps", "eps", "dvi")):
                allowed_types.pop(extension,None)
    elif not options.outfilename:
        options.outfilename = os.path.splitext(options.infilename)[0]

    # Find types for figures and output:
    if options.outtype is None:
        if options.figuretype:
            for key in allowed_types.keys():
                if not options.figuretype in allowed_types[key]:
                    allowed_types.pop(key)
        # FIXME: pdf should not be hard coded, but this should be the first 
        # Along the list of allowed types.
        if "pdf" in  allowed_types:
            options.outtype = "pdf"
        elif "html" in allowed_types:
            options.outtype = "html"
        else:
            options.outtype = "rst"
        if options.verbose:
            print >> sys.stderr, "No output type specified, outputting to %s" \
                            % options.outtype

    if options.outtype in allowed_types:
        if options.figuretype is None:
            options.figuretype = allowed_types[options.outtype][0]
        elif not options.figuretype in allowed_types[options.outtype]:
            print >> sys.stderr, "Warning: %s figures requested incompatible with %s output" % (options.figuretype, options.outtype)
            options.figuretype = allowed_types[options.outtype][0]
            print >> sys.stderr, "Using %s figures" % options.figuretype
    else:
        print >> sys.stderr, "Error: unsupported output type requested"
        sys.exit(1)

    return options

def open_outfile(options):
    """ This make sure we have an output stream or file to write to.
        It is the last step setting up the options before compilation
    """
    # If no file-like object has been open yet, open one now.
    # Reminder: options.outfile should always be without the extention
    if options.outfilename == "-":
        options.outfile = sys.stdout
    elif not options.outfile:
        outfilename = "%s.%s" % (options.outfilename, options.outtype)
        if not options.quiet:
            print >> sys.stderr, "Outputing report to " + outfilename
        # Special case (ugly): binary files:
        if options.outtype in set(("pdf", "ps", "eps", "dvi")):
            outfilename = "%s.tex" % (options.outfilename)
        options.outfile = open(outfilename,"w")

#---------------------------- Subroutines ------------------------------------
if DEBUG:
    try:
        os.mkdir("DEBUG")
    except OSError:
        pass
    def DEBUGwrite(variable, filename):
        """ If DEBUG is enabled, writes variable to the file given by "filename"
        """
        debug_file = open("DEBUG" + os.sep + filename,'w')
        debug_file.write(variable.__repr__())
        debug_file.close()
else:
    def DEBUGwrite(variable, filename):
        pass

#-------------- Subroutines for python code hashing --------------------------
def first_block(options):
    """ This function creates the first block that is injected in the code to 
        get it started.
    """
    # Overload sys.argv
    new_argv = []
    if not options.infilename == None:
        new_argv = [options.infilename, ]
    if not options.arguments == None:
        new_argv += options.arguments.split(' ')
    codeblock = code_hasher.CodeBlock(0)
    codeblock.string = "\n\nimport sys\nsys.argv = %s\n" % new_argv
    return codeblock

#-------------- Subroutines for python code execution ------------------------
class SandBox(object):
    """ Implements a sandbox environement for executing code into.
    """
    
    # List holding the figures created by the call last executed
    current_figure_list = ()
    
    # List holding all the figures created through all the calls.
    total_figure_list = ()
    
    namespace = {}

    def __init__(self, myshow, options = default_options):
        """ This object acts as a memory for the code blocks. The
            reason we pass it pylab, is so that it can retrieve the figurelist
        """
        self.initial_options = options
        self.options = copy.copy(options)
        self.myshow = myshow
    
        self.__call__(first_block(options))
    
    def __call__(self, block):
        return self.executeblock(block)

    def executeblock(self, block):
        """ Excute a python command block, returns the stderr and the stdout 
        generated, and the list of figures generated."""
    
        block_text = "\n\n" + block.string
        line_number = block.start_row
        #self.options._update_loose(block.options)
        out_value = ""
    
        # This import should not be needed, but it works around a very
        # strange bug I encountered once.
        import cStringIO
        # create file-like string to capture output
        code_out = cStringIO.StringIO()
        code_err = cStringIO.StringIO()
   
        captured_exception = None
        # capture output and errors
        sys.stdout = code_out
        sys.stderr = code_err
        try:
            exec block_text in self.namespace
        except Exception, captured_exception:
            if isinstance(captured_exception, KeyboardInterrupt):
                raise captured_exception
            print >> sys.stderr, format_exc()      
        
        # restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
            
        out_value = code_out.getvalue()
        error_value = code_err.getvalue()
            
        code_out.close()
        code_err.close()

        if captured_exception: 
            print >> sys.stderr, "Error in executing script on block starting line ", line_number ,": " 
            print >> sys.stderr, error_value
        self.namespace = globals()
        self.namespace.update(locals())

        if out_value and not self.options.noecho:
            if self.options.outfilename == "-" :
                print >> sys.stderr, out_value
            else:
                print out_value
        if self.myshow:
            self.current_figure_list = self.myshow.figure_list[
                                        len(self.total_figure_list):]
            self.total_figure_list = self.myshow.figure_list

        #if self.options.silent:
        #    error_value = ""
            
        return (block.start_row, block.string, out_value, error_value, 
                                                self.current_figure_list)

# FIXME: Check the structure of the code doing the overloading, it may not be 
# optimal.

class PylabShow(object):
    """ Factory for creating a function to replace pylab.show .
    """
    figure_list = ()
    
    figure_extension = "eps"

    def _set_options(self,options):
        if not options.outfilename in set(("-", None)):
            self.basename =  "%s_pyreport_" % os.path.splitext(
                        os.path.basename(options.infilename))[0]
        else:
            self.basename =  "_pyreport_"
        # XXX: Use pylab's pdf output
        #if options.figuretype == "pdf":
        #    self.figure_extension = "eps"
        #else:
        self.figure_extension = options.figuretype
        
    def __call__(self):
        figure_name = '%s%d.%s' % ( self.basename,
                len(self.figure_list), self.figure_extension )
        self.figure_list += (figure_name, )
        print "Here goes figure %s" % figure_name
        import pylab
        pylab.savefig(figure_name)


myshow = PylabShow()

class MyImport(object):
    """ Factory to create an __import__ call to override the builtin.
    """
    
    original_import = __import__
    
    def __init__(self, options):
        self.options = options
    
    
    def __call__(self, name, globals=None, locals=None, fromlist=None, 
                    **kwargs):
        if name == "pylab":
            return self.pylab_import(name, globals, locals, fromlist,
                        **kwargs)
        return self.original_import(name, globals, locals, fromlist,
                        **kwargs)

    if PYTHON_VERSION >= 26:
        def __call__(self, name, globals=None, locals=None,
                        fromlist=None, level=-1):
            if name == "pylab":
                return self.pylab_import(name, globals, locals, fromlist,
                        level=level)
            return self.original_import(name, globals, locals, fromlist,
                        level=level)
    
    
    def pylab_import(self, name, globals=None, locals=None,
                     fromlist=None, level=-1):
        matplotlib = self.original_import("matplotlib")
        matplotlib.interactive(False)
        # FIXME: Still no good solution to plot without X. The following
        # trick does not work well as all features have not been
        # implemented in the ps and gd backends.
        # Set the backend to just about anything that does not
        # display (althought using gd just doesn't do the trick
        ##if self.options.figuretype in set(("pdf", "ps", "eps")):
        ##    matplotlib.use('ps')
        ##else:
        ##    matplotlib.use('gd')
        imported = self.original_import(name, globals, locals, fromlist)
        imported.show = myshow
        return imported


def execute_block_list(block_list, options=copy.copy(default_options)):
    """ Executes the list of statement in a sandbox. Returns a list of the
        results for each statement: 
        (line number, statement, stdout, stdin, figure_list)
    """
    if not options.noexecute:
        if not options.quiet :
            print >> sys.stderr, "Running python script %s:\n" % \
                                                        options.infilename
        # FIXME: I really have to have a close look at this code path. It
        # smells
        myshow._set_options(options)
        #__builtin__.__import__ = myimport
        __builtin__.__import__ = MyImport(options)
        
        execute_block = SandBox(myshow, options=options)

    else:
        execute_block = lambda block : [block.start_row, block.string, 
                                                None, None, ()] 

    output_list = map(execute_block, block_list)
  
    # python can have strange histerisis effect, with kwargs and passing by
    # reference. We need to reinitialise these to there defaults:
    execute_block.figure_list = ()
    return output_list
 

#-------------- Subroutines for formatting blocks hashing --------------------
def hash_block(block, options):
    """ Separate an answer block into comment blocks, input blocks, error 
        blocks and output blocks.

    >>> hash_block((1,'print "foo"',"foo",None,()),default_options)
    [['inputBlock', 'print "foo"', 2], ['outputBlock', 'foo', ()]]
    """
    output_list = py2commentblocks( block[1], block[0], options)
    lastindex = _last_input_block(output_list)
    out = output_list[:lastindex]
    if block[2]:
        out += [['outputBlock', block[2], block[4]], ]
    if block[3]:
        out += [['errorBlock', block[3]], ]
    out += output_list[lastindex:]
    return out


def shape_output_list(output_list, options):
    """ Transform the output_list from a simple capture of stdout, stderr...
        to a list of blocks that can be passed to the compiler.

    >>> shape_output_list([(1,'print "foo"',"foo",None,())], default_options)
    [['rstBlock', ''], ['inputBlock', 'print "foo"', 2], ['outputBlock', 'foo', ()]]
    """
    # FIXME: Where does this options comme from ? Looks like it has become 
    # global, maybe pyreport.options shouldn't be called like this to avoid
    # this kind of errors.
    output_list =  [ hash_block(block, options) for block in output_list ]
    # FIXME: We are going to need to find a better way of doing this !
    DEBUGwrite(output_list, 'output_list3')

    # Maybe the condense and the reduce should be the same operation.
    output_list = condense_output_list(output_list, options)

    DEBUGwrite( output_list, 'condensedoutputlist')

    output_list = map(check_rst_block, output_list)
    DEBUGwrite( output_list, 'checkedoutput_list')
    return output_list


def py2commentblocks(string, firstlinenum, options):
    r""" Hashes the given string into a list of code blocks, litteral comments 
        blocks and latex comments.

        >>> py2commentblocks("a\n#!b\n#c", 1, default_options)
        [['inputBlock', 'a\n', 2], ['textBlock', 'b\n'], ['commentBlock', '#c\n', 3]]
        >>> default_options._update_loose({'latexliterals': True})
        >>> py2commentblocks("a\n#$Latex\n", 1, default_options)
        [['inputBlock', 'a\n', 2], ['latexBlock', 'Latex\n']]
    """
    input_stream = cStringIO.StringIO(string)
    block_list = []
    pos = 0
    current_block = ""
    newline = True
    linenum = 0
    last_token = None
    for tokendesc in tokenize.generate_tokens(input_stream.readline):

        if PYTHON_VERSION >= 26:
            # As of 2.6, tokenize.generate_tokens() chops newlines off
            # then end of comments and returns them as NL tokens. This
            # confuses the logic of the rest of pyreport, so we gobble
            # NL following a comment.
            if last_token == tokenize.COMMENT and \
                    tokendesc[0] == tokenize.NL:
                last_token = tokendesc[0]
                continue
            else:
                last_token = tokendesc[0]

        tokentype = token.tok_name[tokendesc[0]]
        startpos = tokendesc[2][1]
        tokencontent = tokendesc[1]
        if tokendesc[2][0] > linenum:
            # We just started a new line
            tokencontent = startpos * " " + tokencontent
            newline = True
        elif startpos > pos :
            tokencontent = (startpos - pos) * " " + tokencontent
        pos = startpos + len(tokendesc[1])
        linenum = tokendesc[2][0]
        reallinenum = linenum + firstlinenum - 1
        if newline and tokentype == 'COMMENT' :
            if current_block:
                block_list += [ [ "inputBlock", current_block, reallinenum ], ]
            current_block = ""
            pos = 0
            lines = tokencontent.splitlines()
            lines = map(lambda z : z + "\n", lines[:])
            for line in lines:
                if line[0:3] == "#!/" and reallinenum == 1:
                    # This is a "#!/foobar on the first line, this 
                    # must be an executable call
                    block_list += [ ["inputBlock", line, reallinenum], ]
                elif line[0:3] == "#%s " % options.commentchar :
                    block_list += [ [ "textBlock", line[3:]], ]
                elif line[0:2] == "#%s" % options.commentchar :
                    block_list += [ ["textBlock", line[2:]], ]
                elif options.latexliterals and line[0:2] == "#$" :
                    block_list += [ ["latexBlock", line[2:]], ]
                else:
                    block_list += [ ["commentBlock", line, reallinenum], ]
        else:
            current_block += tokencontent
        newline = False
    if current_block :
        block_list += [ [ "inputBlock", current_block, reallinenum ], ]
    return block_list


def condense_output_list(output_list, options):
    """ Takes the "output_list", made of list of blocks of different 
        type and merges successiv blocks of the same type.

    >>> condense_output_list([[['inputBlock', 'a', 4]], 
    ...             [['inputBlock', "b", 2], ['outputBlock', 'c', ()]]],
    ...             default_options)
    [['textBlock', ''], ['inputBlock', 'ab', 4], ['outputBlock', 'c', ()]]
    """
    out_list = [['textBlock', ''], ]
    for blocks in output_list:
        for block in blocks:
            if block[0] == "commentBlock":
                block[0] = "inputBlock"
            if options.nocode and block[0] == "inputBlock":
                continue
            elif block[0] == out_list[-1][0]:
                out_list[-1][1] += block[1]
                if block[0] == 'outputBlock':
                    out_list[-1][2] += block[2]
                    out_list[-1][1] = re.sub(r"(\n)+", r"\n", out_list[-1][1])
            else:
                out_list += [block]
    return out_list


def _last_input_block(output_list):
    """ return the index of the last input block in the given list of blocks.
    """
    lastindex = 0
    for index, block in enumerate(output_list):
        if block[0] == "inputBlock":
            lastindex = index
    return lastindex + 1


#-------------- Subroutines for report output --------------------------------
def protect(string):
    r''' Protects all the "\" in a string by adding a second one before

    >>> protect(r'\foo \*')
    '\\\\foo \\\\*'
    '''
    return re.sub(r"\\", r"\\\\", string)


def safe_unlink(filename):
    """ Remove a file from the disk only if it exists, if not r=fails silently
    """
    if os.path.exists(filename):
        os.unlink(filename)



def tex2pdf(filename, options):
    """ Compiles a TeX file with pdfLaTeX (or LaTeX, if or dvi ps requested)
        and cleans up the mess afterwards
    """
    if options.verbose:
        execute = verbose_execute
    else:
        execute = silent_execute
    if not options.quiet :
        print >> sys.stderr, "Compiling document to "+options.outtype
    if options.outtype == "ps":
        execute("latex --interaction scrollmode %s.tex -output-directory=%s" %(filename, os.path.dirname(filename)))
        execute("dvips %s.dvi -o %s.ps" % (filename, filename) )
    elif options.outtype == "dvi":
        execute("latex --interaction scrollmode %s.tex " % filename)
    elif options.outtype == "eps":
        execute("latex --interaction scrollmode %s.tex -output-directory=%s" %(filename, os.path.dirname(filename)))
        execute("dvips -E %s.dvi -o %s.eps" % (filename, filename))
    elif options.outtype == "pdf":
        if HAVE_PDFLATEX:
            execute( "pdflatex --interaction scrollmode %s.tex -output-directory=%s" %(filename, os.path.dirname(filename)))
        else:
            execute("latex --interaction scrollmode %s.tex -output-directory=%s" %(filename, os.path.dirname(filename)))
            execute("dvips -E %s.dvi -o %s.eps" % (filename, filename))
            print "Doing pdf %s" % filename
            execute("epstopdf %s.eps" % filename)

    safe_unlink(filename+".tex")
    safe_unlink(filename+".log")
    safe_unlink(filename+".aux")
    safe_unlink(filename+".out")


def epstopdf(figure_name):
    """ Converts eps file generated by the script to a pdf file, using epstopdf
        with the right flags.
    """
    os.environ['GS_OPTIONS'] = "-dCompressPages=false -dAutoFilterColorImages=false -dDownsampleColorImages=false -dDownsampleColorImages=false -dColorImageResolution=1200 -dAutoFilterGrayImages=false -dGrayImageResolution=1200 -dDownsampleMonoImages=false -dMonoImageResolution=1200 -dColorImageFilter=/FlateEncode -dGrayImageFilter=/FlateEncode -dMonoImageFilter=/FlateEncode"
    os.environ['GS_OPTIONS'] = "-dUseFlatCompression=true -dPDFSETTINGS=/prepress -sColorImageFilter=FlateEncode -sGrayImageFilter=FlateEncode -dAutoFilterColorImages=false -dAutoFilterGrayImages=false -dEncodeColorImages=false -dEncodeGrayImages=false -dEncodeMonoImages=false"
    os.system("epstopdf --nocompress " + figure_name)
    #safe_unlink(figure_name)
    return (os.path.splitext(figure_name)[0]+".pdf")


def rst2latex(rst_string):
    """ Calls docutils' engine to convert a rst string to a LaTeX file.
    """
    overrides = {'output_encoding': 'latin1', 'initial_header_level': 0}
    tex_string = docCore.publish_string(
                source=rst_string, 
                writer_name='latex', settings_overrides=overrides)
    return tex_string


def rst2html(rst_string):
    """ Calls docutils' engine to convert a rst string to an html file.
    """
    overrides = {'output_encoding': 'latin1', 'initial_header_level': 1}
    html_string = docCore.publish_string(
                source=rst_string, 
                writer_name='html', settings_overrides=overrides)
    return html_string

def check_rst_block(block):
    """ Check if every textBlock can be compiled as Rst. Change it to 
        textBlock if so.

    >>> check_rst_block(["textBlock","foo"])
    ['rstBlock', 'foo']
    >>> check_rst_block(["textBlock","**foo"])
    ['textBlock', '**foo']
    """
    publisher = docCore.Publisher( source_class = docIO.StringInput,
                        destination_class = docIO.StringOutput )
    publisher.set_components('standalone', 'restructuredtext', 'pseudoxml')
    publisher.process_programmatic_settings(None, None, None)
    if block[0] == "textBlock":
        publisher.set_source(block[1], None)
        compiled_rst = publisher.reader.read(publisher.source,
                                publisher.parser, publisher.settings)
        if compiled_rst.parse_messages:
            # FIXME: It would be nice to add the line number where the error 
            # happened
            print >> sys.stderr, """Error reading rst on literate comment line 
falling back to plain text"""
        else:
            block[0] = "rstBlock"
    return block


class ReportCompiler(object):
    """ Compiler obejct that contains all the data and the call to produce 
        the final document from the output block list
    """

    preamble = ".. header:: Compiled with pyreport\n"
    #preamble = ""
   
    inputBlocktpl = r"""
::

    %(textBlock)s

"""
    latexBlocktpl = r"""

.. raw:: LaTeX

    %s
    
"""
    errorBlocktpl = r"""

.. error::

  ::

    %s
    
"""

    outputBlocktpl = r"""
.. class:: answer

  ::

    %s
    
"""

    figuretpl = r"""
.. image:: %s.eps

"""


    textBlocktpl = r"""::

    %s
"""

    figure_list = ()

    indent = True

    def __init__(self, options):
        self.empty_listing = re.compile(re.escape(self.outputBlocktpl[:-5] % ''), re.DOTALL)

    def add_indent(self, string):
        if self.indent:
            return string.replace("\n","\n    ")
        else:
            return string

    def block2rst(self, block):
        """given a output block, returns a rst string
        """
        # FIXME: Do this with a dictionary. Actually, the objects dictionary
        # It self, just name the attributes and methods well
        if block[0] == "inputBlock":
            if callable(self.inputBlocktpl):
                rst_text = self.inputBlocktpl(block[1], block[2])
            else:
                data = {'linenumber' : block[2],
                        'textBlock' : self.add_indent(block[1]),
                        }
                rst_text = self.inputBlocktpl % data
                rst_text = re.sub(self.empty_listing ,"" , rst_text)
        elif block[0] == "errorBlock":
            rst_text = self.errorBlocktpl % (self.add_indent(block[1]))
        elif block[0] == "latexBlock":
            rst_text = self.latexBlocktpl % (self.add_indent(block[1]))
        elif block[0] == "rstBlock":
            rst_text = "\n" + block[1] + "\n" 
        elif block[0] == "textBlock":
            rst_text = self.textBlocktpl % (self.add_indent(block[1])) 
        elif block[0] == "outputBlock":
            rst_text = self.outputBlocktpl % ((block[1]).replace("\n","\n    "))
            for figure_name in block[2]:
                rst_text = re.sub("Here goes figure " + re.escape(figure_name),
                        self.figuretpl % (os.path.splitext(figure_name)[0]),
                        rst_text)
            rst_text = re.sub(self.empty_listing, "", rst_text)
            self.figure_list += block[2]
        return rst_text

    def blocks2rst_string( self, output_list ):
        """ given a list of output blocks, returns a rst string ready to 
        be compiled"""
        output_list = map( self.block2rst, output_list)
        rst_string = "".join(output_list)
        # To make the ouput more compact and readable:
        rst_string = re.sub(r"\n\n(\n)+","\n\n",rst_string)
        DEBUGwrite( rst_string, "pyreport.rst")
        return rst_string

    def compile( self, output_list, fileobject, options):
        """ Compiles the output_list to the rst file given the filename"""
        rst_string = self.preamble + self.blocks2rst_string(output_list)
        print >>fileobject, rst_string


class TracCompiler(ReportCompiler):
    def inputBlocktpl(self, pythonstring, startlinnum):
        if re.search(r'\S', pythonstring):
            return r"""
    .. code-block:: python

        %s

""" % pythonstring.replace("\n","\n        ")
        else:
            return "\n"


class MoinCompiler(ReportCompiler):
    figuretpl = r"""

inline:%s

"""
    textBlocktpl = """
%s
"""
    inputBlocktpl = r"""

{{{#!python
%(textBlock)s
}}}
"""
    rstBlocktpl = r"""
{{{#!rst
%s
}}}
"""
    indent = False
    preamble = "## Compiled with pyreport"

    def __init__(self):
        self.empty_listing = re.compile( "("
            + re.escape(self.outputBlocktpl[:-5] % '')
            + ")|("
            + re.escape(self.inputBlocktpl % {"textBlock" : "\n\n"})
            + ")"
            , re.DOTALL)


class HtmlCompiler(ReportCompiler):
    figuretpl = r"""

.. image:: %s.png
"""

    textBlocktpl = r"""
.. class:: text

  ::

    %s
    
"""

    def inputBlocktpl(self, pythonstring, startlinnum):
        """ Given a python string returns a raw html rst insert with the pretty 
            printing implemented in html.
        """
        return r"""
.. raw:: html

    %s

""" % (python2html(pythonstring)).replace("\n","\n    ")


    def compile(self, output_list, fileobject, options):
        """ Compiles the output_list to the html file given the filename
        """
        html_string = rst2html(self.blocks2rst_string(output_list))
        cssextra = r"""
        pre.answer {
            margin-bottom: 1px ;
            margin-top: 1px ;
            margin-left: 6ex ;
            font-family: serif ;
            font-size: 100% ;
            background-color: #cccccc ; 
        }
        pre.text {
        }
        .pysrc {
            font-weight: normal;
            /*background-color: #eeece0;*/
            background-color: #eef2f7;
            background-image: url("yellow-white.png");
            background-position:  right;
            background-repeat: repeat-y;
            border: 1px solid;
            border-color: #999999;
            margin: 20px;
            padding:10px 10px 10px 20px;
            font-size: smaller;
            white-space: pre ;
        }

        .pykeyword {
            font-weight: bold;
            color: #262668 ;
        }
        .pycomment { color: #007600; }
        /*.pystring { color: #ad0000; }*/
        .pystring { color: #0000bb; }
        .pynumber { color:purple; }
        .pyoperator { color:purple; font-weight: bold; }
        .pytext { color:black; }
        .pyerror { font-weight: bold; color: red; }

        .bracket {
            height: 4px;
            width: 10px;
        }
        .bracketfill {
            width: 10px;
            background-color: #FFFFFF; 
        }
        .collapse {
            border: 0px; 
            background-color: #99CCFF; 
            padding: 0px;
            font-size: xx-small;
            text-align: right;
        }
        </style>

<!-- http://www.randomsnippets.com/2008/02/12/how-to-hide-and-show-your-div/ -->
<script language="javascript"> 
function toggle_hidden(showHideDiv, switchTextDiv) {
    var ele = document.getElementById(showHideDiv);
    var eleinv = document.getElementById(showHideDiv+'inv');
    var text = document.getElementById(switchTextDiv);
    if(ele.style.display == "block") {
        ele.style.display = "none";
        eleinv.style.display = "block";
        text.innerHTML = "<small>+</small>";
        }
    else {
        ele.style.display = "block";
        eleinv.style.display = "none";
        text.innerHTML = " <small>&nbsp;</small>" ;
        }
    } 

function hide_all(contentDiv,controlDiv){
    var text = document.getElementById('hideall');
    if (contentDiv.constructor == Array) {
        for(i=0; i < contentDiv.length; i++) {
        toggle_hidden(contentDiv[i], controlDiv[i]);
        }
    }
    else {
        toggle_hidden(contentDiv, controlDiv);
    }

}
</script>
        """
        html_string = re.sub(r"</style>", protect(cssextra), html_string)
        hideall = r"""<body><div id="hideall" class="collapse"
            onclick="hide_all("""
        hideall += str( ['pysrc%d' % x for x in range(python2html.pysrcid)])
        hideall += ","
        hideall += str( ['toggle%d' % x for x in range(python2html.pysrcid)])
        hideall += r""")">toggle all code blocks</div><br>
        """
        html_string = re.sub(r"<body>", protect(hideall), html_string)
        print >>fileobject, html_string


class TexCompiler(ReportCompiler):
    empty_listing = re.compile(
            r"""\\begin\{lstlisting\}\{\}\s*\\end\{lstlisting\}""", re.DOTALL)
    
    inputBlocktpl = r"""
    
.. raw:: LaTeX

    {\inputBlocksize
    \lstset{escapebegin={\color{darkgreen}},backgroundcolor=\color{lightblue},fillcolor=\color{lightblue},numbers=left,name=pythoncode,firstnumber=%(linenumber)d,xleftmargin=0pt,fillcolor=\color{white},frame=single,fillcolor=\color{lightblue},rulecolor=\color{lightgrey},basicstyle=\ttfamily\inputBlocksize}
    \begin{lstlisting}{}
    %(textBlock)s
    \end{lstlisting}
    }
    
    
"""
    outputBlocktpl =  r"""
.. raw:: LaTeX

    \lstset{backgroundcolor=,numbers=none,name=answer,xleftmargin=3ex,frame=none}
    \begin{lstlisting}{}
    %s
    \end{lstlisting}
    
"""
    errorBlocktpl = r"""

.. raw:: LaTeX


    {\color{red}{\bfseries Error: }
    \begin{verbatim}%s\end{verbatim}}
    
"""
    figuretpl = r'''
    \end{lstlisting}
    \\centerline{\includegraphics[scale=0.5]{%s}}
    \\begin{lstlisting}{}'''
    
    def __init__(self, options):
        self.preamble = r"""
    \usepackage{listings}
    \usepackage{color}
    \usepackage{graphicx}

    \definecolor{darkgreen}{cmyk}{0.7, 0, 1, 0.5}
    \definecolor{darkblue}{cmyk}{1, 0.8, 0, 0}
    \definecolor{lightblue}{cmyk}{0.05,0,0,0.05}
    \definecolor{grey}{cmyk}{0.1,0.1,0.1,1}
    \definecolor{lightgrey}{cmyk}{0,0,0,0.5}
    \definecolor{purple}{cmyk}{0.8,1,0,0}

    \makeatletter
        \let\@oddfoot\@empty\let\@evenfoot\@empty
        \def\@evenhead{\thepage\hfil\slshape\leftmark
                        {\rule[-0.11cm]{-\textwidth}{0.03cm}
                        \rule[-0.11cm]{\textwidth}{0.03cm}}}
        \def\@oddhead{{\slshape\rightmark}\hfil\thepage
                        {\rule[-0.11cm]{-\textwidth}{0.03cm}
                        \rule[-0.11cm]{\textwidth}{0.03cm}}}
        \let\@mkboth\markboth
        \markright{{\bf %s }\hskip 3em  \today}
        \def\maketitle{
            \centerline{\Large\bfseries\@title}
            \bigskip
        }
    \makeatother


    \lstset{language=python,
            extendedchars=true,
            aboveskip = 0.5ex,
            belowskip = 0.6ex,
            basicstyle=\ttfamily,
            keywordstyle=\sffamily\bfseries,
            identifierstyle=\sffamily,
            commentstyle=\slshape\color{darkgreen},
            stringstyle=\rmfamily\color{blue},
            showstringspaces=false,
            tabsize=4,
            breaklines=true,
            numberstyle=\footnotesize\color{grey},
            classoffset=1,
            morekeywords={eyes,zeros,zeros_like,ones,ones_like,array,rand,indentity,mat,vander},keywordstyle=\color{darkblue},
            classoffset=2,
            otherkeywords={[,],=,:},keywordstyle=\color{purple}\bfseries,
            classoffset=0""" % ( re.sub( "_", r'\\_', options.infilename) ) + options.latexescapes * r""",
            mathescape=true""" +"""
            }
    """

        if options.nocode:
            latex_column_sep = r"""
    \setlength\columnseprule{0.4pt}
    """
        else:
            latex_column_sep = ""


        latex_doublepage = r"""
    \usepackage[landscape,left=1.5cm,right=1.1cm,top=1.8cm,bottom=1.2cm]{geometry}
    \usepackage{multicol}
    \def\inputBlocksize{\small}
    \makeatletter
        \renewcommand\normalsize{%
        \@setfontsize\normalsize\@ixpt\@xipt%
        \abovedisplayskip 8\p@ \@plus4\p@ \@minus4\p@
        \abovedisplayshortskip \z@ \@plus3\p@
        \belowdisplayshortskip 5\p@ \@plus3\p@ \@minus3\p@
        \belowdisplayskip \abovedisplayskip
        \let\@listi\@listI}
        \normalsize
        \renewcommand\small{%
        \@setfontsize\small\@viiipt\@ixpt%
        \abovedisplayskip 5\p@ \@plus2\p@ \@minus2\p@
        \abovedisplayshortskip \z@ \@plus1\p@
        \belowdisplayshortskip 3\p@ \@plus\p@ \@minus2\p@
        \def\@listi{\leftmargin\leftmargini
                    \topsep 3\p@ \@plus\p@ \@minus\p@
                    \parsep 2\p@ \@plus\p@ \@minus\p@
                    \itemsep \parsep}%
        \belowdisplayskip \abovedisplayskip
        }
        \renewcommand\footnotesize{%
        \@setfontsize\footnotesize\@viipt\@viiipt
        \abovedisplayskip 4\p@ \@plus2\p@ \@minus2\p@
        \abovedisplayshortskip \z@ \@plus1\p@
        \belowdisplayshortskip 2.5\p@ \@plus\p@ \@minus\p@
        \def\@listi{\leftmargin\leftmargini
                    \topsep 3\p@ \@plus\p@ \@minus\p@
                    \parsep 2\p@ \@plus\p@ \@minus\p@
                    \itemsep \parsep}%
        \belowdisplayskip \abovedisplayskip
        }
        \renewcommand\scriptsize{\@setfontsize\scriptsize\@vipt\@viipt}
        \renewcommand\tiny{\@setfontsize\tiny\@vpt\@vipt}
        \renewcommand\large{\@setfontsize\large\@xpt\@xiipt}
        \renewcommand\Large{\@setfontsize\Large\@xipt{13}}
        \renewcommand\LARGE{\@setfontsize\LARGE\@xiipt{14}}
        \renewcommand\huge{\@setfontsize\huge\@xivpt{18}}
        \renewcommand\Huge{\@setfontsize\Huge\@xviipt{22}}
        \setlength\parindent{14pt}
        \setlength\smallskipamount{3\p@ \@plus 1\p@ \@minus 1\p@}
        \setlength\medskipamount{6\p@ \@plus 2\p@ \@minus 2\p@}
        \setlength\bigskipamount{12\p@ \@plus 4\p@ \@minus 4\p@}
        \setlength\headheight{12\p@}
        \setlength\headsep   {25\p@}
        \setlength\topskip   {9\p@}
        \setlength\footskip{30\p@}
        \setlength\maxdepth{.5\topskip}
    \makeatother

    \AtBeginDocument{
    \setlength\columnsep{1.1cm}
    """ + latex_column_sep + r"""
    \begin{multicols*}{2}
    \small}
    \AtEndDocument{\end{multicols*}}
    """

        if options.double:
            self.preamble += latex_doublepage
        else:
            self.preamble += r"""\usepackage[top=2.1cm,bottom=2.1cm,left=2cm,right=2cm]{geometry}
    \def\inputBlocksize{\normalsize}
        """

        if options.outtype == "tex":
            self.compile = self.compile2tex
        else:
            self.compile = self.compile2pdf


    def compile2tex(self, output_list, fileobject, options):
        """ Compiles the output_list to the tex file given the filename
        """
        tex_string = rst2latex(self.blocks2rst_string(output_list))
        tex_string = re.sub(r"\\begin{document}", 
                        protect(self.preamble) + r"\\begin{document}", tex_string)
        tex_string = re.sub(self.empty_listing, "", tex_string)
        # XXX: no need to use epstopdf: we are now using MPL'pdf output
        #if options.figuretype == "pdf":
        #    if options.verbose:
        #        print >> sys.stderr, "Compiling figures"
        #    self.figure_list = map(epstopdf, self.figure_list)
        print >>fileobject, tex_string


    def compile2pdf(self, output_list, fileobject, options):
        """ Compiles the output_list to the tex file given the filename
        """
        self.compile2tex( output_list, fileobject, options)
        fileobject.close()
        tex2pdf(options.outfilename, options)
        map(safe_unlink, self.figure_list)
        self.figure_list = ()


compilers = {
    'html': HtmlCompiler,
    'rst' : ReportCompiler,
    'moin': MoinCompiler,
    'trac': TracCompiler,
}

#------------------------------- Entry point ---------------------------------

def main(pyfile, overrides={}, initial_options=copy.copy(default_options), 
                global_allowed_types=allowed_types):
    """ Process the stream (file or stringIO object) given by pyfile, execute
        it, and compile a report at the end.
        
        Default options that can be overriden by the script should be given 
        through the initial_options objects (that can by created by using the 
        pyreport.options object, and its method _update_careful).

        Overrides that impose options can be given through the overrides 
        dictionary. It takes the same keys and values than the initial_options 
        object and is the recommended way to specify output type,...

        To retrive the report in the calling program, just pass a StringIO 
        object as the outfile, in the overides.

        example:
            pyreport.main(StringIO_object, overrides={'outtype':'html',
                    'outfile':StringIO_object, 'silent':True,
                    'infilename':'Report generated by me'}
    """
    # Beware of passing by reference. We need to make copies of options as
    # Much as possible to avoid histerisis effects:
    options = copy.copy(initial_options)
    allowed_types = global_allowed_types.copy()

    # Options used to start the parsing:
    parsing_options = copy.copy(options)
    parsing_options._update_loose(overrides)
    # Slice the input file into code blocks
    block_list = code_hasher.iterblocks(pyfile)
    # FIXME: Need to deal with the script's options
    script_options = {}

    # Override the options given by the script by the command line switch
    script_options.update(overrides)
    # And now merge this to the default options (! this a not a dict)
    options._update_loose(script_options)
    options = guess_names_and_types(options, allowed_types=allowed_types)

    # Process the blocks
    output_list = execute_block_list(block_list, options)
    DEBUGwrite( output_list, 'output_list')

    open_outfile(options)
   
    output_list = shape_output_list(output_list, options)
    
    global compilers
    compiler = compilers.get(options.outtype, TexCompiler)(options)
    compiler.compile( output_list, options.outfile, options)


########NEW FILE########
__FILENAME__ = options
"""
This files is where all the options-related code is.
"""

# Standard library imports
import copy
import os
from optparse import OptionParser
import sys

# Local imports
from version import __version__

def silent_execute( string, return_stderr=True):
    """ Execute the given shell adding '> /dev/null' if under a posix OS 
        and '> nul' under windows.
    """
    if sys.platform.startswith('win') or return_stderr:
        return os.system(string + " > " + os.devnull)
    else:
        return os.system('%s >%s 2>%s' % (string, os.devnull,
                                                    os.devnull))


def verbose_execute(string):
    """ Execute getting errors """
    if os.system(string) != 0:
        raise RuntimeError('Unable to execute %r' % string)

# A dictionary describing the supported output type (as the keys of the
# dictionnary) and the figure type allowed for each.
allowed_types = {
        "html": ("png", "jpg") ,
        "rst" : ("png", "pdf", "ps", "jpg"), 
        "moin": ("png", "jpg") ,
        "trac" : ("png", "pdf", "ps", "jpg"), 
}

# Find out what output type we can provide (do we have latex ? epstopdf ?)
# FIXME: Have a look at mpl to see how they do this.
if not silent_execute("latex --help"):
    allowed_types.update({
        "tex" : ("pdf", "eps", "ps"),
        "dvi" : ("eps",),
        "ps"  : ("eps",),
        "eps" : ("eps",),
    })
    # Why the hell does epstopdf return 65280 !!
    if  silent_execute("epstopdf --help", return_stderr=False) in (0, 65280):
        allowed_types.update({
            "pdf" : ("pdf",),
            "tex" : ("pdf", "eps","ps"),
        })

if not silent_execute("pdflatex --help"):
    HAVE_PDFLATEX = True
else:
    HAVE_PDFLATEX = False

# Build a parser object
usage = """usage: %prog [options] pythonfile

Processes a python script and pretty prints the results using LateX. If 
the script uses "show()" commands (from pylab) they are caught by 
%prog and the resulting graphs are inserted in the output pdf.
Comments lines starting with "#!" are interprated as rst lines
and pretty printed accordingly in the pdf.
    By Gael Varoquaux"""

# Defaults are put to None and False in order to be able to track the changes.
option_parser = OptionParser(usage=usage, version="%prog " +__version__ )

option_parser.add_option("-o", "--outfile", dest="outfilename",
                help="write report to FILE", metavar="FILE")
option_parser.add_option("-x", "--noexecute",
                action="store_true", dest="noexecute", default=False,
                help="do not run the code, just extract the literate comments")
option_parser.add_option("-n", "--nocode",
                dest="nocode", action="store_true", default=False,
                help="do not display the source code")
option_parser.add_option("-d", "--double",
                dest="double", action="store_true", default=False,
                help="compile to two columns per page "
                     "(only for pdf or tex output)")
option_parser.add_option("-t", "--type", metavar="TYPE",
                action="store", type="string", dest="outtype",
                default=None,
                help="output to TYPE, TYPE can be " + 
                                        ", ".join(allowed_types.keys()))
option_parser.add_option("-f", "--figuretype", metavar="TYPE",
                action="store", type="string", dest="figuretype",
                default=None,
                help="output figure type TYPE  (TYPE can be of %s depending on report output type)" 
                % (", ".join(reduce(lambda x, y : set(x).union(y) , allowed_types.values()) )) )
option_parser.add_option("-c", "--commentchar",
                action="store", dest="commentchar", default="!",
                metavar="CHAR",
                help='literate comments start with "#CHAR" ')
option_parser.add_option("-l", "--latexliterals",
                action="store_true", dest="latexliterals",
                default=False,
                help='allow LaTeX literal comment lines starting with "#$" ')
option_parser.add_option("-e", "--latexescapes",
                action="store_true", dest="latexescapes",
                default=False,
                help='allow LaTeX math mode escape in code wih dollar signs ')
option_parser.add_option("-p", "--nopyreport",
                action="store_true", dest="nopyreport", default=False,
                help="disallow the use of #pyreport lines in the processed "
                     "file to specify options")
option_parser.add_option("-q", "--quiet",
                action="store_true", dest="quiet", default=False,
                help="don't print status messages to stderr")
option_parser.add_option("-v", "--verbose",
                action="store_true", dest="verbose", default=False,
                help="print all the message, including tex messages")
option_parser.add_option("-s", "--silent",
                dest="silent",action="store_true",
                default=False,
                help="""Suppress the display of warning and errors in the report""")
option_parser.add_option( "--noecho",
                dest="noecho",action="store_true",
                default=False,
                help="""Turns off the echoing of the output of the script on the standard out""")
option_parser.add_option("-a", "--arguments",
                action="store", dest="arguments",
                default=None, type="string", metavar="ARGS",
                help='pass the arguments "ARGS" to the script')

# Create default options
default_options, _not_used = option_parser.parse_args(args =[])
default_options._update_loose({
                                   'infilename': None,
                                   'outfile': None,
                               })

def parse_options(arguments, initial_options=copy.copy(default_options), 
                                    allowed_types=allowed_types):
    """ Parse options in the arguments list given.
        Return a dictionary containing all the options different specified,
        and only these, and the arguments.
        Returns outfilename without the extension ! (important)

    >>> parse_options(['-o','foo.ps','-s',])
    ({'outfilename': 'foo', 'outtype': 'ps', 'silent': True}, [])
    """
    (options, args) = option_parser.parse_args(args=arguments)
    if (options.outtype == None and 
            options.outfilename and 
            '.' in options.outfilename) :
        basename, extension = os.path.splitext(options.outfilename)
        if extension[1:] in allowed_types:
            options.outtype = extension[1:]
            options.outfilename = basename
    options_dict = options.__dict__
    initial_options_dict = initial_options.__dict__
    
    return diff_dict(options_dict, initial_options_dict), args

def diff_dict(dict1, dict2):
    """ Returns a dictionary with all the elements of dict1 that are not in
        dict 2.

    >>> diff_dict({1:2, 3:4}, {1:3, 3:4, 2:4})
    {1: 2}
    """
    return_dict = {}
    for key in dict1:
        if key in dict2:
            if not dict1[key] == dict2[key]:
                return_dict[key] = dict1[key]
        else:
            return_dict[key] = dict1[key]
    return return_dict




########NEW FILE########
__FILENAME__ = pyreport
#!/usr/bin/env python
"""
Tool that takes python script and runs it. Returns the results and special
comments (literate comments) embedded in the code in a pdf (or html, or rst...)
"""
# Author: Gael Varoquaux  <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2005 Gael Varoquaux
# License: BSD Style

#TODO: - Extend unit tests
#      - Rework error reporting code to print the line where the error
#        happened
#      - Bug in the HTML pretty printer ? Line returns seem to big.
#      - Proper documentation
#      - Rework to API to allow better use from external programs
#      - Process some strings as literal-comments:
#               Strings starting a new line
#               Need an option to enable this
#               Maybe a strict mode, where the string has to be preceeded by
#               A line with a special comment
#      - Numbering in html + switch to remove numbering
#      - Inverse mode: process a rest file and execute some special blocks
#      - some output to make man pages ?
#      - Long, long term: use reportlab to avoid the dependencies on
#          LaTeX

# Standard library import
import sys

# Local imports
from main import main
from options import parse_options, option_parser

#------------------------------- Entry point ---------------------------------
def commandline_call():
    """ Entry point of the program when called from the command line
    """
    options, args = parse_options(sys.argv[1:])
    
    if not len(args)==1:
        if len(args)==0:
            option_parser.print_help()
        else:
            print  >> sys.stderr, "1 argument: input file"
        sys.exit(1)

    import time
    t1 = time.time()
    if args[0] == "-":
        pyfile = sys.stdin
    else:
        pyfile = open(args[0],"r")

    # Store the name of the input file for later use
    options.update({'infilename':args[0]})

    main(pyfile, overrides=options)
    # FIXME: wath about the options defined in the script: options.quiet
    if not 'quiet' in options:
        print >>sys.stderr, "Ran script in %.2fs" % (time.time() - t1)


if __name__ == '__main__':
    commandline_call()

########NEW FILE########
__FILENAME__ = python_parser
"""
Python synthax higlighting

Borrowed from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52298
"""

# Original copyright : 2001 by Juergen Hermann <jh@web.de>
import cgi, cStringIO, keyword, token, tokenize

class PythonParser:
    """ Send colored python source.
    """

    _KEYWORD = token.NT_OFFSET + 1
    _TEXT    = token.NT_OFFSET + 2

    def __init__(self):
        """ Store the source text.
        """
        self._tags = {
            token.NUMBER: 'pynumber',
            token.OP: 'pyoperator',
            token.STRING: 'pystring',
            tokenize.COMMENT: 'pycomment',
            tokenize.ERRORTOKEN: 'pyerror',
            self._KEYWORD: 'pykeyword',
            self._TEXT: 'pytext',
        }
        self.pysrcid = 0;


    def __call__(self, raw):
        """ Parse and send the colored source.
        """
        self.out = cStringIO.StringIO()
        self.raw = raw.expandtabs().strip()
        # store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0
        while 1:
            pos = self.raw.find('\n', pos) + 1
            if not pos: break
            self.lines.append(pos)
        self.lines.append(len(self.raw))
        #
        # parse the source and write it
        self.pos = 0
        text = cStringIO.StringIO(self.raw)
        self.out.write("<table width=100% cellpadding=0 cellspacing=0 " +
                     """onclick="toggle_hidden('pysrc%d','toggle%d');"><tr>
                        <td rowspan="3"> """ % (self.pysrcid, self.pysrcid) )
        self.out.write("""<div class="pysrc" id="pysrc%dinv" style="display:
                       none">...</div>"""% self.pysrcid)
        self.out.write('<div class="pysrc" id="pysrc%d" style="display: block ">'% self.pysrcid)

        try:
            tokenize.tokenize(text.readline, self.format)
        except tokenize.TokenError, ex:
            msg = ex[0]
            line = ex[1][0]
            print >> self.out, ("<h3>ERROR: %s</h3>%s" %
                (msg, self.raw[self.lines[line]:]))
        self.out.write('</div>')
        self.out.write('''
                       </td> 
                       <td colspan="2" class="collapse bracket"></td>
                       </tr>
                       <tr>
                       <td class="bracketfill"></td>
                       <td width=5px class="collapse"> 
                           <div id="toggle%d">
                           <small>.</small>
                           </div>
                       </td>
                       </tr>
                       <tr><td colspan="2" class="collapse bracket"></td>
                       </tr>
                       </table>
                       ''' % (self.pysrcid))
        self.pysrcid += 1
        return self.out.getvalue()

    def format(self, toktype, toktext, (srow, scol), (erow, ecol), line):
        """ Token handler.
        """
        
        # calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)
        #
        # handle newlines
        if toktype in [token.NEWLINE, tokenize.NL]:
            # No need, for that: the css attribute "white-space: pre;" will 
            # take care of that.
            self.out.write("\n")
            return
        #
        # send the original whitespace, if needed
        if newpos > oldpos:
            self.out.write(self.raw[oldpos:newpos])
        #
        # skip indenting tokens
        if toktype in [token.INDENT, token.DEDENT]:
            self.pos = newpos
            return
        #
        # map token type to a color group
        if token.LPAR <= toktype and toktype <= token.OP:
            toktype = token.OP
        elif toktype == token.NAME and keyword.iskeyword(toktext):
            toktype = self._KEYWORD
        style = self._tags.get(toktype, self._tags[self._TEXT])
        #
        # send text
        self.out.write('<span class="%s">' % (style, ))
        self.out.write(cgi.escape(toktext))
        self.out.write('</span>')

python2html = PythonParser()



########NEW FILE########
__FILENAME__ = test_code_hasher
"""
Unit tests for the code hasher.
"""

from nose.tools import assert_equal

import pyreport.code_hasher as ch


def line_signature(line_object):
    return (line_object.string, line_object.end_row, line_object.options)


def line_list_signature(line_list):
    signature = [line_signature(line) for line in line_list]
    # This is unfortunately required because of a change in the token
    # module between python 2.4 and python 2.5
    if signature[-1][0] == '':
        signature.pop()
    return signature


########################################################################
# Test the separation in logical lines

def check_signature(in_string, signature):
    hasher = ch.CodeHasher(ch.xreadlines(in_string))
    code_line_list = [l for l in hasher.itercodelines()]
    signature2 = line_list_signature(code_line_list)
    assert_equal(signature, signature2)


def test_lines():
    check_signature('a\na', [('a\n', 1, {}), ('a\n', 2, {})])


def test_comments():
    check_signature('a\n#a\na', [('a\n', 1, {}), ('#a\na\n', 3, {})])


def test_options():
    check_signature('a\n#pyreport -n\na', 
                    [('a\n', 1, {}), ('#pyreport -n\na\n', 3, {})])


########################################################################
# Test the separation in code blocks

def is_single_block(string):
    codeblock = ch.CodeBlock(0)
    codeblock.string = '\n'.join(s.rstrip(' ')
                    for s in 
                    ''.join(ch.xreadlines(string.expandtabs())).split('\n'))
    block_list = list( ch.iterblocks(ch.xreadlines(string)) )
    assert_equal(line_list_signature([codeblock]), 
                        line_list_signature(block_list))


def test_empty():
    is_single_block("a")


def test_comment_in_block():
    is_single_block("""
if 1:
    print "a"
    # foo

# foo

    print "b"
""")


def test_double_blank_line():
    is_single_block("""
if 1:
    a = (1, 
           4)
                        

    a""")


def test_indented_comment():
    is_single_block("""
if 1:

    # Comment

    a""")


def test_function_declaration():
    is_single_block("def foo():\n foo")


def test_tabbed_block():
    is_single_block("def foo():\n\tfoo")


def test_decorator():
    is_single_block("@staticmethod\ndef foo():\n foo")


def test_double_function():
    string = """
def f():
    pass

def g():
    pass
"""
    blocks = list(ch.iterblocks(ch.xreadlines(string)))
    # This should be made of three blocks, the last one of them
    # empty.
    assert_equal(len(blocks), 3)


def test_double_function_tabs():
    string = """
def f():
\tpass

def g():
\tpass
"""
    blocks = list(ch.iterblocks(ch.xreadlines(string)))
    # This should be made of three blocks, the last one of them
    # empty.
    assert_equal(len(blocks), 3)


def test_double_function_non_empty_line():
    string = """
def f():
\tpass
\t
def g():
\tpass
"""
    blocks = list(ch.iterblocks(ch.xreadlines(string)))
    # This should be made of three blocks, the last one of them
    # empty.
    assert_equal(len(blocks), 3)


########################################################################
# Test if the code is indeed kept similar by the hash

def is_same_code(codestring):
    out = ''.join([i.string
                for i in ch.iterblocks(ch.xreadlines(codestring))])
    assert_equal(codestring.expandtabs(), out)


def test_long_block():
    is_same_code("def f():\n\t1\n\t2\n")


########################################################################
if __name__ == "__main__" :
    import nose
    nose.runmodule()


########NEW FILE########
__FILENAME__ = test_main
"""
Unit tests for pyreports main functionnality.
"""

# Standard library imports
import pydoc
from cStringIO import StringIO as S
import unittest

from nose.tools import assert_equal

from pyreport import main
from pyreport.code_hasher import xreadlines


##############################################################################
def test_check_rst_block():
    assert_equal(main.check_rst_block(['textBlock','foo']),
                       ['rstBlock', 'foo'])
    assert_equal(main.check_rst_block(['textBlock','*fo**o']),
                        ['textBlock', '*fo**o'])



##############################################################################
class TestMain(unittest.TestCase):

    def setUp(self):
        self.outString = S()

    def test_empty_file(self):
        main.main(xreadlines(""), 
                overrides={'outfile':self.outString, 'outtype':'rst',
                            'quiet':True}),
        self.assertEqual(self.outString.getvalue(),
                '.. header:: Compiled with pyreport\n\n\n\n')

    def test_hello_world(self):
        main.main(xreadlines("print 'hello world'"), 
                overrides={'outfile':self.outString, 'outtype':'rst',
                            'quiet':True, 'noecho':True }),
        self.assertEqual(self.outString.getvalue(),
            ".. header:: Compiled with pyreport\n\n\n::\n\n    print 'hello world'\n    \n\n.. class:: answer\n\n  ::\n\n    hello world\n    \n    \n\n")


##############################################################################
def profile():
    """ Use hotshot to profile the calls to main """
    import hotshot, cStringIO
    Prof = hotshot.Profile("pyreport.stats")
    outString=cStringIO.StringIO()
    Prof.runcall(main.main,cStringIO.StringIO(""),
                    overrides={'outfile':outString, 'outtype':'rst'})
    import hotshot.stats
    stats = hotshot.stats.load("pyreport.stats")
    stats.print_stats(50)


def document():
    """ Use pydoc to generate documentation"""
    pydoc.writedoc('pyreport')


##############################################################################
if __name__ == '__main__':
    from nose import runmodule
    runmodule()
    document()
    #profile()
   

########NEW FILE########
__FILENAME__ = test_options
"""
Unit tests for pyreport's options functionnality.
"""

from nose.tools import assert_equal

from pyreport import options

##############################################################################
def test_parse_options():
    assert_equal(options.parse_options([]), ({}, []) )
    assert_equal(options.parse_options(['foo']), ({}, ['foo']) )
    assert_equal(options.parse_options(['-t','foo']), 
                            ({'outtype': 'foo'}, []) )

  

########NEW FILE########
__FILENAME__ = version
"""
This file is required only for loose coupling and avoiding import loops.
"""
# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright: Gael Varoquaux
# License: BSD

__version__ = "0.3.4b"


########NEW FILE########
