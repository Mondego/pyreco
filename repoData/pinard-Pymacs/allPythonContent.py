__FILENAME__ = dotEmacs
# -*- coding: utf-8 -*-
# jjEmacsPythoned.py
#

import sys
import os.path
import string
from Pymacs import lisp


sys.path.append(".")


interactions = {}


def debug(msg):
    msg = "<D> "+msg
    def t():
        lisp.message(msg)
        lisp.set_buffer("*LogBuffer*")
        lisp.goto_line(lisp.point_max())
        lisp.insert(msg+"\n")
    lisp.save_excursion(t)

def doMainConfig():
    # On emacs 22 enable cua mode:
    try:
        lisp.cua_mode(True)
        debug("Cua mode succesfully initialized")
    except Exception:
        debug("Failed Cua mode init")

def testExceptionFramework():
    try:
      lisp.give_me_an_error()
    except Protocol.ErrorException:
        debug("Errore get")


def initLogs():
    lisp.switch_to_buffer("*LogBuffer*")
    debug("Log Buffer succesfully initialized by Pymacs")



################ Callback for auto-reloading python modules if needed
def get_module_name_if_python_file_handle():
    fname=lisp.buffer_file_name()
    if fname==None:
        return None
    # check it:
    if fname[-3:] == '.py' and not fname.endswith("Pymacs.py")):
        # Ok, we have got something to do:
        # replace last / with a point and try it down:
        i=fname.rfind("/")
        pk=fname[:i]+"."+fname[i+1:-3]
        #debug("Reloading "+pk)
        return pk
    else:
        #say(" Nothing to do for:"+fname)
        return None

interactions[get_module_name_if_python_file_handle]=''

#### BASIC SAVE HOOK always called:
def save_hook(bufferFileName):
    #say("Nothing to do")
    pass

interactions[save_hook]=''

def installPymacsMenu():
    pass


interactions[debug]=''
interactions[initLogs]=''
interactions[doMainConfig]=''
interactions[testExceptionFramework]=''

########NEW FILE########
__FILENAME__ = menudemo
# -*- coding: utf-8 -*-
import sys
import os.path
import string
from Pymacs import lisp


sys.path.append(".")


interactions = {}

def testVectors():
    # Test vectors
    # Returns something like ["a" "b"] which is a emacs lisp vector
    return ("a", "b")



def installPymacsMenu():
    pass


interactions[testVectors]=''
interactions[installPymacsMenu]=''

########NEW FILE########
__FILENAME__ = utility
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2007 Giovanni Giorgi <jj@objectsroot.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.

from Pymacs import lisp
import time

# Utility support functions
class EmacsLog:
    def __init__(self,category):
        self.logBuffer="*LogBuffer*" # "*Pymacs Log Buffer*"
        self.category=category
        self.startTime=time.time()

    def show(self,level,msg):
        start=int(time.time()-self.startTime)
        mx=str(start)+" <"+level+"> PY "+self.category+" "+msg
        lisp.message(mx)
        #mx = mx + "\n"
        #lisp.set_buffer(self.logBuffer)
        #lisp.insert(mx)

    def info(self, msg):
        self.show("I",msg)

    def debug(self,msg):
        self.show("DEBUG",msg)


    # Finest debugging
    def debugf(self,msg):
        self.show("DEBUG FINER",msg)


class BufferMan:
    def __init__(self):
        self.bufferName=lisp.buffer_name()
        self.fname=lisp.buffer_file_name()

    def getBufferAsText(self):
        f=open(self.fname,"r")
        text=f.read()
        f.close()
        return text

    def writeBuffer(self,text):
        f=open(self.fname,"w")
        f.write(text)
        f.close()
        self.reloadBuffer()

    def reloadBuffer(self):
        # ;; (switch-to-buffer bname)
        # ;; (revert-buffer 'IGNORE-AUTO 'NOCONFIRM)
        lisp.switch_to_buffer(self.bufferName)
        lisp.revert_buffer(lisp.IGNORE_AUTO, lisp.NOCONFIRM)





log=EmacsLog("main")
log.debugf("Pymacs.utility Loaded and happy to serve you")


########NEW FILE########
__FILENAME__ = tester
# Script test for completition

import string
s=""

########NEW FILE########
__FILENAME__ = pym
# -*- coding: utf-8 -*-
"""Functions accessible from inside Emacs.

Filename: pym.py

Usage in Emacs: import them with
M-x pymacs-load pym

And then all functions here become available in Emacs as
pym-function-name with every _ replaced by - in the names.
"""

__author__ = "Fernando Perez. <fperez@pizero.colorado.edu>"
__license__= "GPL"

import re
from Pymacs import lisp

# lisp is the global which handles lisp-based interaction with the active
# Emacs buffer from which any function is called

# interactions is a global dict which MUST be updated for each new function
# defined which we want to be visible to Emacs. Each function must have an
# entry in it with the function as key (the function *object*, NOT its name as
# a string) and a string as value. At a minimum, this string will be empty,
# but it can contain the names of variables to be read interactively by the
# function, lisp-style.

# Functions meant to be used internally only (not exposed to Emacs) don't need
# an entry in interactions.

interactions = {}

#***************************************************************************
# WARNING: things from genutils copied verbatim here. For some reason pymacs
# does not import other modules correctly (my own, it seems ok with system
# stuff).

def indent(str,nspaces=4,ntabs=0):
    """Indent a string a given number of spaces or tabstops.

    indent(str,nspaces=4,ntabs=0) -> indent str by ntabs+nspaces.
    """

    ind = '\t'*ntabs+' '*nspaces
    outstr = '%s%s' % (ind,str.replace('\n','\n'+ind))
    if outstr.endswith('\n'+ind):
        return outstr[:-len(ind)]
    else:
        return outstr

# End of genutils copy/paste job.

#***************************************************************************
# Lisp utility functions, snatched from elsewhere.

def clean_undo_after(checkpoint):
        """\
Remove all intermediate boundaries from the Undo list since CHECKPOINT.
"""
        lisp("""
(let ((undo-list %s))
  (if (not (eq buffer-undo-list undo-list))
      (let ((cursor buffer-undo-list))
        (while (not (eq (cdr cursor) undo-list))
          (if (car (cdr cursor))
              (setq cursor (cdr cursor))
            (setcdr cursor (cdr (cdr cursor)))))))
  nil)
"""
             % (checkpoint or 'nil'))

#***************************************************************************
# Utility functions, none of which need an interactions[] entry.

def lisp_obj_info(obj):
    """Return various details about a lisp object as a string.

    Useful mainly for debugging purposes."""

    info = [obj,obj.__class__,obj.index,type(obj.index),repr(obj)]
    info = map(str,info)
    info = '\n'.join(info)
    return info

#---------------------------------------------------------------------------
def lisp_char(lisp_obj):
    """Return a single character string from a lisp char object.

    Used to extract characters from their lisp form as obtained in interactive
    functions with the c code. """
    text_form = repr(lisp_obj)
    try:
        return re.search(r"'\?(.)'",text_form).group(1)
    except:
        return None

#---------------------------------------------------------------------------
def is_yes(lisp_obj):
    """Check whether an interactive lisp character reply is a yes (y/Y)"""

    try:
        return lisp_char(lisp_obj).lower() == 'y'
    except:
        return 0

#---------------------------------------------------------------------------
def cut_region(mode='string'):
    """Return the active region and remove it from Emacs.

    The mode parameter (default 'string') defines whether to return the region
    as a string or as a list of lines (mode='list').

    It is the caller's responsibility to insert the updated text at the
    end back in the Emacs buffer with a call to lisp.insert(...)."""

    start, end = lisp.point(), lisp.mark(lisp.t)
    # BUG: buffer_substring() can't extract regions with dos line endings (\r\n)
    # It dumps a traceback.
    region = lisp.buffer_substring(start, end)
    if mode == 'list':
        region = region.splitlines()
    lisp.delete_region(start, end)
    return region
    # cut_region() doesn't need an entry in interactions[] b/c it's meant to
    # be used internally by other functions in this module, not directly
    # from Emacs

#---------------------------------------------------------------------------
def insert_text(text,offset=0):
    """Insert text in buffer and move cursor to a certain offset.

    If called with no offset, leaves the cursor at the current position."""

    # save undo state so we can roll everything into a single operation for undo
    checkpoint = lisp.buffer_undo_list.value()
    user_pos = lisp.point()
    lisp.insert(text)
    lisp.goto_char(user_pos+offset)
    # Collapse all operations into a single one, for Undo.
    clean_undo_after(checkpoint)

#---------------------------------------------------------------------------
def insert_indented_text(text,offset):
    """Insert indented text in buffer and move cursor to a certain offset."""

    # save undo state so we can roll everything into a single operation for undo
    checkpoint = lisp.buffer_undo_list.value()
    # figure out if we are indented or not, and adapt text accordingly
    indent_level = get_line_offset()
    if indent_level > 0:
        text = indent(text,indent_level)
    # perform actual insertion with proper cursor positioning
    offset += indent_level
    lisp.beginning_of_line()
    user_pos = lisp.point()
    lisp.insert(text)
    lisp.goto_char(user_pos+offset)
    # Collapse all operations into a single one, for Undo.
    clean_undo_after(checkpoint)

#---------------------------------------------------------------------------
def get_line_offset():
    """Return number of characters cursor is offset from margin.    """
    user_pos = lisp.point()
    lisp.beginning_of_line()
    line_start = lisp.point()
    lisp.goto_char(user_pos)
    return user_pos - line_start
# end get_line_offset()

#---------------------------------------------------------------------------
def newfn_string(name,sep,end,args=''):
    """Template for a new function definition.

    Returns the string containing the definition and the integer offset for
    cursor positioning."""

    # prepare text
    out = ''
    sep = lisp_char(sep)
    if sep is not None:
        out += '#'+sep*77+'\n'
    out += 'def '+name+'('+args
    offset = len(out)
    out += '):\n'
    out += '    """\n'*2
    if is_yes(end):
        out += '# end '+name+'()\n'
    return out,offset

#***************************************************************************
# 'Public' functions (exposed to Emacs). All these MUST have an interactions[]
# entry

def bow():
    """Break a region replacing all whitespace with newlines.

    Originally an example in Pymacs' README."""

    region = cut_region()
    lisp.insert('\n'.join(region.split()))

# Update interactions[] for functions meant to be visible in Emacs.

# Interaction strings follow some funny emacs-lisp conventions, with the first
# letter being a code and the rest a prompt. Use `C-h f interactive' in Emacs
# to get a description.  The simplest one is a prompt for a string, which is
# given as a string of the form 's<prompt>'.

# Will print 'name ' in the minibuffer and get a string:
#interactions[deft] = 'sNew function name? '

# The c code is for characters, and the Pymacs readme says they are returned
# to python as ints, but that doesn't seem to be the case. Instead I'm getting
# Pymacs.Lisp objects, which have a repr() of the form "lisp('?<char>')" where
# <char> is the returned character.

interactions[bow] = ''

# Note that trying to set interactions as a function attribute:
# bow.interactions = ''
# is NOT WORKING. The module loads in Emacs, but no functions are actually
# recognized. Tested with Python 2.1, it might work with Python 2.2

#-----------------------------------------------------------------------------
def dos2unix():
    """Remove DOS line endings from a region.
    """
    # Save undo state so we can roll everything into a single operation for undo
    checkpoint = lisp.buffer_undo_list.value()
    region = cut_region('list')
    lisp.insert('\n'.join(region)+'\n')
    # Collapse all operations into a single one, for Undo.
    clean_undo_after(checkpoint)

# BUG: it's not working b/c of a bug in lisp.buffer_substring(), so let's not
# activate it for now.
#interactions[dos2unix] = ''

#---------------------------------------------------------------------------
def newfn(name,sep,end,args=''):
    """Insert a template for a new function definition."""

    insert_indented_text(*newfn_string(name,sep,end))

new_template = 'sNew %s name? \n'\
               'cEnter separator (RET for none): \n'\
               'cPrint end marker (y/[N])? '

interactions[newfn] = new_template % 'function'

#-----------------------------------------------------------------------------
def newweave(name,sep,end,use_blitz):
    """Insert a template for a new weave function definition.
    """

    blitz,ending = '',''
    if is_yes(use_blitz):
        blitz = ",type_factories = blitz_type_factories"
    if is_yes(end):
        ending = "\n# end %s()" % (name,)

    head,offset = newfn_string(name,sep,0)
    head += \
'''
    code = \\
"""

"""
    return weave.inline(code,[]%(blitz)s)%(ending)s
''' % locals()
    insert_indented_text(head,offset)

interactions[newweave] = new_template % 'weave function'
interactions[newweave] += '\ncUse blitz type factories (y/[N])? '

#---------------------------------------------------------------------------
def newmeth(name,sep,end):
    """Insert a template for a new method definition.    """

    insert_indented_text(*newfn_string(name,sep,end,'self'))

interactions[newmeth] = new_template % 'method'

#---------------------------------------------------------------------------
def newclass(name,sep,end):
    """Template for new class definition.    """
    out =  ('class %s:\n' % (name,)) + ('    """\n'*2) + '\n'
    offset = get_line_offset()+len(out) + len ("    def __init__(self")
    new_str = newfn_string('__init__',None,None,'self')[0]
    out += indent(new_str)
    if is_yes(end):
        out += '# end class '+name+'\n'
    insert_indented_text(out,offset)

interactions[newclass] = new_template % 'class'

########NEW FILE########
__FILENAME__ = rebox
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 1991-1998, 2000, 2002, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>, 1991-04.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""\
Handling of boxed comments in various box styles.

The user documentation for this tool may be found at:

    http://pymacs.progiciels-bpi.ca/rebox.html
"""

## Note: a double hash comment introduces a group of functions or methods.

__metatype__ = type
import re, sys

## Batch specific features.

def main(*arguments):
    refill = True
    style = None
    tabify = False
    verbose = False
    width = 79
    import getopt
    options, arguments = getopt.getopt(arguments, 'ns:tvw:', ['help'])
    for option, value in options:
        if option == '--help':
            sys.stdout.write(__doc__)
            sys.exit(0)
        elif option == '-n':
            refill = False
        elif option == '-s':
            style = int(value)
        elif option == '-t':
            tabify = True
        elif option == '-v':
            verbose = True
        elif option == '-w':
            width = int(value)
    if len(arguments) == 0:
        text = sys.stdin.read()
    elif len(arguments) == 1:
        handle = file(arguments[0])
        text = handle.read()
        handle.close()
    else:
        sys.stderr.write("Invalid usage, try `rebox --help' for help.\n")
        sys.exit(1)
    old_style, new_style, text, position = engine(
        text, style=style, width=width, refill=refill, tabify=tabify)
    if text is None:
        sys.stderr.write("* Cannot rebox to style %d.\n" % new_style)
        sys.exit(1)
    sys.stdout.write(text)
    if verbose:
        if old_style == new_style:
            sys.stderr.write("Reboxed with style %d.\n" % old_style)
        else:
            sys.stderr.write("Reboxed from style %d to %d.\n"
                             % (old_style, new_style))

## Emacs specific features.

def pymacs_load_hook():
    global interactions, lisp, Let, region, comment, set_default_style
    from Pymacs import lisp, Let
    emacs_rebox = Emacs_Rebox()
    # Declare functions for Emacs to import.
    interactions = {}
    region = emacs_rebox.region
    interactions[region] = 'P'
    comment = emacs_rebox.comment
    interactions[comment] = 'P'
    set_default_style = emacs_rebox.set_default_style

class Emacs_Rebox:

    def __init__(self):
        self.default_style = None

    def set_default_style(self, style):
        """\
Set the default style to STYLE.
"""
        self.default_style = style

    def region(self, flag):
        """\
Rebox the boxed comment in the current region, obeying FLAG.
"""
        self.emacs_engine(flag, self.find_region)

    def comment(self, flag):
        """\
Rebox the surrounding boxed comment, obeying FLAG.
"""
        self.emacs_engine(flag, self.find_comment)

    def emacs_engine(self, flag, find_limits):
        """\
Rebox text while obeying FLAG.  Call FIND_LIMITS to discover the extent
of the boxed comment.
"""
        # `C-u -' means that box style is to be decided interactively.
        if flag == lisp['-']:
            flag = self.ask_for_style()
        # If FLAG is zero or negative, only change default box style.
        if isinstance(flag, int) and flag <= 0:
            self.default_style = -flag
            lisp.message("Default style set to %d" % -flag)
            return
        # Decide box style and refilling.
        if flag is None:
            style = self.default_style
            refill = True
        elif isinstance(flag, int):
            if self.default_style is None:
                style = flag
            else:
                style = merge_styles(self.default_style, flag)
            refill = True
        else:
            flag = flag.copy()
            if isinstance(flag, list):
                style = self.default_style
                refill = False
            else:
                lisp.error("Unexpected flag value %s" % flag)
        # Prepare for reboxing.
        lisp.message("Reboxing...")
        checkpoint = lisp.buffer_undo_list.value()
        start, end = find_limits()
        text = lisp.buffer_substring(start, end)
        width = lisp.fill_column.value()
        tabify = lisp.indent_tabs_mode.value() is not None
        point = lisp.point()
        if start <= point < end:
            position = point - start
        else:
            position = None
        # Rebox the text and replace it in Emacs buffer.
        old_style, new_style, text, position = engine(
            text, style=style, width=width,
            refill=refill, tabify=tabify, position=position)
        if text is None:
            lisp.error("Cannot rebox to style %d" % new_style)
        lisp.delete_region(start, end)
        lisp.insert(text)
        if position is not None:
            lisp.goto_char(start + position)
        # Collapse all operations into a single one, for Undo.
        self.clean_undo_after(checkpoint)
        # We are finished, tell the user.
        if old_style == new_style:
            lisp.message("Reboxed with style %d" % old_style)
        else:
            lisp.message("Reboxed from style %d to %d"
                         % (old_style, new_style))

    def ask_for_style(self):
        """\
Request the style interactively, using the minibuffer.
"""
        language = quality = type = None
        while language is None:
            lisp.message("\
Box language is 100-none, 200-/*, 300-//, 400-#, 500-;, 600-%%")
            key = lisp.read_char()
            if key >= ord('0') and key <= ord('6'):
                language = key - ord('0')
        while quality is None:
            lisp.message("\
Box quality/width is 10-simple/1, 20-rounded/2, 30-starred/3 or 40-starred/4")
            key = lisp.read_char()
            if key >= ord('0') and key <= ord('4'):
                quality = key - ord('0')
        while type is None:
            lisp.message("\
Box type is 1-opened, 2-half-single, 3-single, 4-half-double or 5-double")
            key = lisp.read_char()
            if key >= ord('0') and key <= ord('5'):
                type = key - ord('0')
        return 100*language + 10*quality + type

    def find_region(self):
        """\
Return the limits of the region.
"""
        return lisp.point(), lisp.mark(lisp.t)

    def find_comment(self):
        """\
Find and return the limits of the block of comments following or enclosing
the cursor, or return an error if the cursor is not within such a block
of comments.  Extend it as far as possible in both directions.
"""
        let = Let().push_excursion()
        try:
            # Find the start of the current or immediately following comment.
            lisp.beginning_of_line()
            lisp.skip_chars_forward(' \t\n')
            lisp.beginning_of_line()
            if not language_matcher[0](self.remainder_of_line()):
                temp = lisp.point()
                if not lisp.re_search_forward('\\*/', None, lisp.t):
                    lisp.error("outside any comment block")
                lisp.re_search_backward('/\\*')
                if lisp.point() > temp:
                    lisp.error("outside any comment block")
                temp = lisp.point()
                lisp.beginning_of_line()
                lisp.skip_chars_forward(' \t')
                if lisp.point() != temp:
                    lisp.error("text before start of comment")
                lisp.beginning_of_line()
            start = lisp.point()
            language = guess_language(self.remainder_of_line())
            # Find the end of this comment.
            if language == 2:
                lisp.search_forward('*/')
                if not lisp.looking_at('[ \t]*$'):
                    lisp.error("text after end of comment")
            lisp.end_of_line()
            if lisp.eobp():
                lisp.insert('\n')
            else:
                lisp.forward_char(1)
            end = lisp.point()
            # Try to extend the comment block backwards.
            lisp.goto_char(start)
            while not lisp.bobp():
                if language == 2:
                    lisp.skip_chars_backward(' \t\n')
                    if not lisp.looking_at('[ \t]*\n[ \t]*/\\*'):
                        break
                    if lisp.point() < 2:
                        break
                    lisp.backward_char(2)
                    if not lisp.looking_at('\\*/'):
                        break
                    lisp.re_search_backward('/\\*')
                    temp = lisp.point()
                    lisp.beginning_of_line()
                    lisp.skip_chars_forward(' \t')
                    if lisp.point() != temp:
                        break
                    lisp.beginning_of_line()
                else:
                    lisp.previous_line(1)
                    if not language_matcher[language](self.remainder_of_line()):
                        break
                start = lisp.point()
            # Try to extend the comment block forward.
            lisp.goto_char(end)
            while language_matcher[language](self.remainder_of_line()):
                if language == 2:
                    lisp.re_search_forward('[ \t]*/\\*')
                    lisp.re_search_forward('\\*/')
                    if lisp.looking_at('[ \t]*$'):
                        lisp.beginning_of_line()
                        lisp.forward_line(1)
                        end = lisp.point()
                else:
                    lisp.forward_line(1)
                    end = lisp.point()
            return start, end
        finally:
            let.pops()

    def remainder_of_line(self):
        """\
Return all characters between point and end of line in Emacs buffer.
"""
        return lisp('''\
(buffer-substring (point) (save-excursion (skip-chars-forward "^\n") (point)))
''')

    def clean_undo_after_old(self, checkpoint):
        """\
Remove all intermediate boundaries from the Undo list since CHECKPOINT.
"""
        # Declare some Lisp functions.
        car = lisp.car
        cdr = lisp.cdr
        eq = lisp.eq
        setcdr = lisp.setcdr
        # Remove any `nil' delimiter recently added to the Undo list.
        cursor = lisp.buffer_undo_list.value()
        if not eq(cursor, checkpoint):
            tail = cdr(cursor)
            while not eq(tail, checkpoint):
                if car(tail):
                    cursor = tail
                    tail = cdr(cursor)
                else:
                    tail = cdr(tail)
                    setcdr(cursor, tail)

    def clean_undo_after(self, checkpoint):
        """\
Remove all intermediate boundaries from the Undo list since CHECKPOINT.
"""
        lisp("""
(let ((undo-list %s))
  (if (not (eq buffer-undo-list undo-list))
      (let ((cursor buffer-undo-list))
        (while (not (eq (cdr cursor) undo-list))
          (if (car (cdr cursor))
              (setq cursor (cdr cursor))
            (setcdr cursor (cdr (cdr cursor)))))))
  nil)
"""
             % (checkpoint or 'nil'))

## Reboxing main control.

def engine(text, style=None, width=79, refill=True, tabify=False,
           position=None):
    """\
Add, delete or adjust a boxed comment held in TEXT, according to STYLE.
STYLE values are explained at beginning of this file.  Any zero attribute
in STYLE indicates that the corresponding attribute should be recovered
from the currently existing box.  Produced lines will not go over WIDTH
columns if possible, if refilling gets done.  But if REFILL is false, WIDTH
is ignored.  If TABIFY is true, the beginning of produced lines will have
spaces replace by TABs.  POSITION is either None, or a character position
within TEXT.  Returns four values: the old box style, the new box style,
the reformatted text, and either None or the adjusted value of POSITION in
the new text.  The reformatted text is returned as None if the requested
style does not exist.
"""
    last_line_complete = text and text[-1] == '\n'
    if last_line_complete:
        text = text[:-1]
    lines = text.expandtabs().split('\n')
    # Decide about refilling and the box style to use.
    new_style = 111
    old_template = guess_template(lines)
    new_style = merge_styles(new_style, old_template.style)
    if style is not None:
        new_style = merge_styles(new_style, style)
    new_template = template_registry.get(new_style)
    # Interrupt processing if STYLE does not exist.
    if not new_template:
        return old_template.style, new_style, None, None
    # Remove all previous comment marks, and left margin.
    if position is not None:
        marker = Marker()
        marker.save_position(text, position, old_template.characters())
    lines, margin = old_template.unbuild(lines)
    # Ensure only one white line between paragraphs.
    counter = 1
    while counter < len(lines) - 1:
        if lines[counter] == '' and lines[counter-1] == '':
            del lines[counter]
        else:
            counter = counter + 1
    # Rebuild the boxed comment.
    lines = new_template.build(lines, width, refill, margin)
    # Retabify to the left only.
    if tabify:
        for counter in range(len(lines)):
            tabs = len(re.match(' *', lines[counter]).group()) / 8
            lines[counter] = '\t' * tabs + lines[counter][8*tabs:]
    # Restore the point position.
    text = '\n'.join(lines)
    if last_line_complete:
        text = text + '\n'
    if position is not None:
        position = marker.get_position(text, new_template.characters())
    return old_template.style, new_style, text, position

def guess_language(line):
    """\
Guess the language in use for LINE.
"""
    for language in range(len(language_matcher) - 1, 1, -1):
        if language_matcher[language](line):
            return language
    return 1

def guess_template(lines):
    """\
Find the heaviest box template matching LINES.
"""
    best_template = None
    for template in list(template_registry.values()):
        if best_template is None or template > best_template:
            if template.match(lines):
                best_template = template
    return best_template

def left_margin_size(lines):
    """\
Return the width of the left margin for all LINES.  Ignore white lines.
"""
    margin = None
    for line in lines:
        counter = len(re.match(' *', line).group())
        if counter != len(line):
            if margin is None or counter < margin:
                margin = counter
    if margin is None:
        margin = 0
    return margin

def merge_styles(original, update):
    """\
Return style attributes as per ORIGINAL, in which attributes have been
overridden by non-zero corresponding style attributes from UPDATE.
"""
    style = [original / 100, original / 10 % 10, original % 10]
    merge = update / 100, update / 10 % 10, update % 10
    for counter in range(3):
        if merge[counter]:
            style[counter] = merge[counter]
    return 100*style[0] + 10*style[1] + style[2]

## Refilling logic.

def refill_lines(lines, width,
                 cached_refiller=[]):
    """\
Refill LINES, trying to not produce lines having more than WIDTH columns.
"""
    if not cached_refiller:
        for Refiller in Refiller_Gnu_Fmt, Refiller_Textwrap, Refiller_Dumb:
            refiller = Refiller()
            new_lines = refiller.fill(lines, width)
            if new_lines is not None:
                cached_refiller.append(refiller)
                return new_lines
    return cached_refiller[0].fill(lines, width)

class Refiller:
    available = True

    def fill(self, lines, width):
        if self.available:
            new_lines = []
            start = 0
            while start < len(lines) and not lines[start]:
                start = start + 1
            end = start
            while end < len(lines):
                while end < len(lines) and lines[end]:
                    end = end + 1
                new_lines = new_lines + self.fill_paragraph(lines[start:end],
                                                            width)
                while end < len(lines) and not lines[end]:
                    end = end + 1
                if end < len(lines):
                    new_lines.append('')
                    start = end
            return new_lines

class Refiller_Gnu_Fmt(Refiller):
    """\
Use both Knuth algorithm and protection for full stops at end of sentences.
"""

    def fill(self, lines, width):
        if self.available:
            import tempfile, os
            name = tempfile.mktemp()
            handle = file(name, 'w')
            handle.write('\n'.join(lines) + '\n')
            handle.close()
            handle = os.popen('fmt -cuw %d %s' % (width, name))
            text = handle.read()
            os.remove(name)
            if handle.close() is None:
                return [line.expandtabs() for line in text.split('\n')[:-1]]

class Refiller_Textwrap(Refiller):
    """\
No Knuth algorithm, but protection for full stops at end of sentences.
"""
    def __init__(self):
        try:
            from textwrap import TextWrapper
        except ImportError:
            self.available = False
        else:
            self.wrapper = TextWrapper(fix_sentence_endings=1)

    def fill_paragraph(self, lines, width):
        # FIXME: This one fills indented lines more aggressively than the
        # dumb refiller.  I'm not sure what it the best thing to do, but
        # ideally, all refillers should behave more or less the same way.
        self.wrapper.width = width
        prefix = ' ' * left_margin_size(lines)
        self.wrapper.initial_indent = prefix
        self.wrapper.subsequent_indent = prefix
        return self.wrapper.wrap(' '.join(lines))

class Refiller_Dumb(Refiller):
    """\
No Knuth algorithm, nor even protection for full stops at end of sentences.
"""

    def fill_paragraph(self, lines, width):
        margin = left_margin_size(lines)
        prefix = ' ' * margin
        new_lines = []
        new_line = ''
        for line in lines:
            counter = len(line) - len(line.lstrip())
            if counter > margin:
                if new_line:
                    new_lines.append(prefix + new_line)
                    new_line = ''
                indent = ' ' * (counter - margin)
            else:
                indent = ''
            for word in line.split():
                if new_line:
                    if len(new_line) + 1 + len(word) > width:
                        new_lines.append(prefix + new_line)
                        new_line = word
                    else:
                        new_line = new_line + ' ' + word
                else:
                    new_line = indent + word
                    indent = ''
        if new_line:
            new_lines.append(prefix + new_line)
        return new_lines

## Marking logic.

class Marker:
    """\
Heuristics to simulate a marker while reformatting boxes.
"""

    def save_position(self, text, position, ignorable):
        """\
Given a TEXT and a POSITION in that text, save the adjusted position
by faking that all IGNORABLE characters before POSITION were removed.
"""
        ignore = {}
        for character in ' \t\r\n' + ignorable:
            ignore[character] = None
        counter = 0
        for character in text[:position]:
            if character in ignore:
                counter = counter + 1
        self.position = position - counter

    def get_position(self, text, ignorable, latest=0):
        """\
Given a TEXT, return the value that would yield the currently saved position,
if it was saved by `save_position' with IGNORABLE.  Unless the position lies
within a series of ignorable characters, LATEST has no effect in practice.
If LATEST is true, return the biggest possible value instead of the smallest.
"""
        ignore = {}
        for character in ' \t\r\n' + ignorable:
            ignore[character] = None
        counter = 0
        position = 0
        if latest:
            for character in text:
                if character in ignore:
                    counter = counter + 1
                else:
                    if position == self.position:
                        break
                    position = position + 1
        elif self.position > 0:
            for character in text:
                if character in ignore:
                    counter = counter + 1
                else:
                    position = position + 1
                    if position == self.position:
                        break
        return position + counter

## Template processing.

class Template:

    def __init__(self, style, weight, lines):
        """\
Digest and register a single template.  The template is numbered STYLE,
has a parsing WEIGHT, and is described by one to three LINES.
STYLE should be used only once through all `declare_template' calls.

One of the lines should contain the substring `box' to represent the comment
to be boxed, and if three lines are given, `box' should appear in the middle
one.  Lines containing only spaces are implied as necessary before and after
the the `box' line, so we have three lines.

Normally, all three template lines should be of the same length.  If the first
line is shorter, it represents a start comment string to be bundled within the
first line of the comment text.  If the third line is shorter, it represents
an end comment string to be bundled at the end of the comment text, and
refilled with it.
"""
        assert style not in template_registry, \
               "Style %d defined more than once" % style
        self.style = style
        self.weight = weight
        # Make it exactly three lines, with `box' in the middle.
        start = lines[0].find('box')
        if start >= 0:
            line1 = None
            line2 = lines[0]
            if len(lines) > 1:
                line3 = lines[1]
            else:
                line3 = None
        else:
            start = lines[1].find('box')
            if start >= 0:
                line1 = lines[0]
                line2 = lines[1]
                if len(lines) > 2:
                    line3 = lines[2]
                else:
                    line3 = None
            else:
                assert 0, "Erroneous template for %d style" % style
        end = start + len('box')
        # Define a few booleans.
        self.merge_nw = line1 is not None and len(line1) < len(line2)
        self.merge_se = line3 is not None and len(line3) < len(line2)
        # Define strings at various cardinal directions.
        if line1 is None:
            self.nw = self.nn = self.ne = None
        elif self.merge_nw:
            self.nw = line1
            self.nn = self.ne = None
        else:
            if start > 0:
                self.nw = line1[:start]
            else:
                self.nw = None
            if line1[start] != ' ':
                self.nn = line1[start]
            else:
                self.nn = None
            if end < len(line1):
                self.ne = line1[end:].rstrip()
            else:
                self.ne = None
        if start > 0:
            self.ww = line2[:start]
        else:
            self.ww = None
        if end < len(line2):
            self.ee = line2[end:]
        else:
            self.ee = None
        if line3 is None:
            self.sw = self.ss = self.se = None
        elif self.merge_se:
            self.sw = self.ss = None
            self.se = line3.rstrip()
        else:
            if start > 0:
                self.sw = line3[:start]
            else:
                self.sw = None
            if line3[start] != ' ':
                self.ss = line3[start]
            else:
                self.ss = None
            if end < len(line3):
                self.se = line3[end:].rstrip()
            else:
                self.se = None
        # Define parsing regexps.
        if self.merge_nw:
            self.regexp1 = re.compile(' *' + regexp_quote(self.nw) + '.*$')
        elif self.nw and not self.nn and not self.ne:
            self.regexp1 = re.compile(' *' + regexp_quote(self.nw) + '$')
        elif self.nw or self.nn or self.ne:
            self.regexp1 = re.compile(
                ' *' + regexp_quote(self.nw) + regexp_ruler(self.nn)
                + regexp_quote(self.ne) + '$')
        else:
            self.regexp1 = None
        if self.ww or self.ee:
            self.regexp2 = re.compile(
                ' *' + regexp_quote(self.ww) + '.*'
                + regexp_quote(self.ee) + '$')
        else:
            self.regexp2 = None
        if self.merge_se:
            self.regexp3 = re.compile('.*' + regexp_quote(self.se) + '$')
        elif self.sw and not self.ss and not self.se:
            self.regexp3 = re.compile(' *' + regexp_quote(self.sw) + '$')
        elif self.sw or self.ss or self.se:
            self.regexp3 = re.compile(
                ' *' + regexp_quote(self.sw) + regexp_ruler(self.ss)
                + regexp_quote(self.se) + '$')
        else:
            self.regexp3 = None
        # Save results.
        template_registry[style] = self

    def __cmp__(self, other):
        return cmp(self.weight, other.weight)

    def characters(self):
        """\
Return a string of characters which may be used to draw the box.
"""
        characters = ''
        for text in (self.nw, self.nn, self.ne,
                     self.ww, self.ee,
                     self.sw, self.ss, self.se):
            if text:
                for character in text:
                    if character not in characters:
                        characters = characters + character
        return characters

    def match(self, lines):
        """\
Returns true if LINES exactly match this template.
"""
        start = 0
        end = len(lines)
        if self.regexp1 is not None:
            if start == end or not self.regexp1.match(lines[start]):
                return 0
            start = start + 1
        if self.regexp3 is not None:
            if end == 0 or not self.regexp3.match(lines[end-1]):
                return 0
            end = end - 1
        if self.regexp2 is not None:
            for line in lines[start:end]:
                if not self.regexp2.match(line):
                    return 0
        return 1

    def unbuild(self, lines):
        """\
Remove all comment marks from LINES, as hinted by this template.  Returns the
cleaned up set of lines, and the size of the left margin.
"""
        margin = left_margin_size(lines)
        # Remove box style marks.
        start = 0
        end = len(lines)
        if self.regexp1 is not None:
            lines[start] = unbuild_clean(lines[start], self.regexp1)
            start = start + 1
        if self.regexp3 is not None:
            lines[end-1] = unbuild_clean(lines[end-1], self.regexp3)
            end = end - 1
        if self.regexp2 is not None:
            for counter in range(start, end):
                lines[counter] = unbuild_clean(lines[counter], self.regexp2)
        # Remove the left side of the box after it turned into spaces.
        delta = left_margin_size(lines) - margin
        for counter in range(len(lines)):
            lines[counter] = lines[counter][delta:]
        # Remove leading and trailing white lines.
        start = 0
        end = len(lines)
        while start < end and lines[start] == '':
            start = start + 1
        while end > start and lines[end-1] == '':
            end = end - 1
        return lines[start:end], margin

    def build(self, lines, width, refill, margin):
        """\
Put LINES back into a boxed comment according to this template, after
having refilled them if REFILL.  The box should start at column MARGIN,
and the total size of each line should ideally not go over WIDTH.
"""
        # Merge a short end delimiter now, so it gets refilled with text.
        if self.merge_se:
            if lines:
                lines[-1] = lines[-1] + '  ' + self.se
            else:
                lines = [self.se]
        # Reduce WIDTH according to left and right inserts, then refill.
        if self.ww:
            width = width - len(self.ww)
        if self.ee:
            width = width - len(self.ee)
        if refill:
            lines = refill_lines(lines, width)
        # Reduce WIDTH further according to the current right margin,
        # and excluding the left margin.
        maximum = 0
        for line in lines:
            if line:
                if line[-1] in '.!?':
                    length = len(line) + 1
                else:
                    length = len(line)
                if length > maximum:
                    maximum = length
        width = maximum - margin
        # Construct the top line.
        if self.merge_nw:
            lines[0] = ' ' * margin + self.nw + lines[0][margin:]
            start = 1
        elif self.nw or self.nn or self.ne:
            if self.nn:
                line = self.nn * width
            else:
                line = ' ' * width
            if self.nw:
                line = self.nw + line
            if self.ne:
                line = line + self.ne
            lines.insert(0, (' ' * margin + line).rstrip())
            start = 1
        else:
            start = 0
        # Construct all middle lines.
        for counter in range(start, len(lines)):
            line = lines[counter][margin:]
            line = line + ' ' * (width - len(line))
            if self.ww:
                line = self.ww + line
            if self.ee:
                line = line + self.ee
            lines[counter] = (' ' * margin + line).rstrip()
        # Construct the bottom line.
        if self.sw or self.ss or self.se and not self.merge_se:
            if self.ss:
                line = self.ss * width
            else:
                line = ' ' * width
            if self.sw:
                line = self.sw + line
            if self.se and not self.merge_se:
                line = line + self.se
            lines.append((' ' * margin + line).rstrip())
        return lines

def regexp_quote(text):
    """\
Return a regexp matching TEXT without its surrounding space, maybe
followed by spaces.  If STRING is nil, return the empty regexp.
Unless spaces, the text is nested within a regexp parenthetical group.
"""
    if text is None:
        return ''
    if text == ' ' * len(text):
        return ' *'
    return '(' + re.escape(text.strip()) + ') *'

def regexp_ruler(character):
    """\
Return a regexp matching two or more repetitions of CHARACTER, maybe
followed by spaces.  Is CHARACTER is nil, return the empty regexp.
Unless spaces, the ruler is nested within a regexp parenthetical group.
"""
    if character is None:
        return ''
    if character == ' ':
        return '  +'
    return '(' + re.escape(character + character) + '+) *'

def unbuild_clean(line, regexp):
    """\
Return LINE with all parenthetical groups in REGEXP erased and replaced by an
equivalent number of spaces, except for trailing spaces, which get removed.
"""
    match = re.match(regexp, line)
    groups = match.groups()
    for counter in range(len(groups)):
        if groups[counter] is not None:
            start, end = match.span(1 + counter)
            line = line[:start] + ' ' * (end - start) + line[end:]
    return line.rstrip()

## Template data.

# Matcher functions for a comment start, indexed by numeric LANGUAGE.
language_matcher = []
for pattern in (r' *(/\*|//+|#+|;+|%+)',
                r'',            # 1
                r' */\*',       # 2
                r' *//+',       # 3
                r' *#+',        # 4
                r' *;+',        # 5
                r' *%+'):       # 6
    language_matcher.append(re.compile(pattern).match)

# Template objects, indexed by numeric style.
template_registry = {}

def make_generic(style, weight, lines):
    """\
Add various language digit to STYLE and generate one template per language,
all using the same WEIGHT.  Replace `?' in LINES accordingly.
"""
    for language, character in ((300, '/'),  # C++ style comments
                                (400, '#'),  # scripting languages
                                (500, ';'),  # Lisp and assembler
                                (600, '%')): # TeX and PostScript
        new_style = language + style
        if 310 < new_style <= 319:
            # Disallow quality 10 with C++.
            continue
        new_lines = []
        for line in lines:
            new_lines.append(line.replace('?', character))
        Template(new_style, weight, new_lines)

# Generic programming language templates.

make_generic(11, 115, ('? box',))

make_generic(12, 215, ('? box ?',
                       '? --- ?'))

make_generic(13, 315, ('? --- ?',
                       '? box ?',
                       '? --- ?'))

make_generic(14, 415, ('? box ?',
                       '???????'))

make_generic(15, 515, ('???????',
                       '? box ?',
                       '???????'))

make_generic(16, 615, ('?????',
                       '? box',
                       '?????'))

make_generic(17, 715, ('?????',
                       '? box',
                       '?????'))

make_generic(21, 125, ('?? box',))

make_generic(22, 225, ('?? box ??',
                       '?? --- ??'))

make_generic(23, 325, ('?? --- ??',
                       '?? box ??',
                       '?? --- ??'))

make_generic(24, 425, ('?? box ??',
                       '?????????'))

make_generic(25, 525, ('?????????',
                       '?? box ??',
                       '?????????'))

make_generic(26, 526, ('??????',
                       '?? box',
                       '??????'))

make_generic(27, 527, ('??????',
                       '?? box',
                       '??????'))

make_generic(31, 135, ('??? box',))

make_generic(32, 235, ('??? box ???',
                       '??? --- ???'))

make_generic(33, 335, ('??? --- ???',
                       '??? box ???',
                       '??? --- ???'))

make_generic(34, 435, ('??? box ???',
                       '???????????'))

make_generic(35, 535, ('???????????',
                       '??? box ???',
                       '???????????'))

make_generic(36, 536, ('???????',
                       '??? box',
                       '???????'))

make_generic(37, 537, ('???????',
                       '??? box',
                       '???????'))

make_generic(41, 145, ('???? box',))

make_generic(42, 245, ('???? box ????',
                       '???? --- ????'))

make_generic(43, 345, ('???? --- ????',
                       '???? box ????',
                       '???? --- ????'))

make_generic(44, 445, ('???? box ????',
                       '?????????????'))

make_generic(45, 545, ('?????????????',
                       '???? box ????',
                       '?????????????'))

make_generic(46, 546, ('????????',
                       '???? box',
                       '????????'))

make_generic(47, 547, ('????????',
                       '???? box',
                       '????????'))

# Textual (non programming) templates.

Template(111, 113, ('box',))

Template(112, 213, ('| box |',
                    '+-----+'))

Template(113, 313, ('+-----+',
                    '| box |',
                    '+-----+'))

Template(114, 413, ('| box |',
                    '*=====*'))

Template(115, 513, ('*=====*',
                    '| box |',
                    '*=====*'))

Template(116, 613, ('+----',
                    '| box',
                    '+----'))

Template(117, 713, ('*====',
                    '| box',
                    '*===='))

Template(121, 123, ('| box |',))

Template(122, 223, ('| box |',
                    '`-----\''))

Template(123, 323, ('.-----.',
                    '| box |',
                    '`-----\''))

Template(124, 423, ('| box |',
                    '\\=====/'))

Template(125, 523, ('/=====\\',
                    '| box |',
                    '\\=====/'))

Template(126, 623, ('.----',
                    '| box',
                    '`----'))

Template(127, 723, ('/====',
                    '| box',
                    '\\===='))


Template(141, 143, ('| box ',))

Template(142, 243, ('* box *',
                    '*******'))

Template(143, 343, ('*******',
                    '* box *',
                    '*******'))

Template(144, 443, ('X box X',
                    'XXXXXXX'))

Template(145, 543, ('XXXXXXX',
                    'X box X',
                    'XXXXXXX'))

Template(146, 643, ('*****',
                    '* box',
                    '*****'))

Template(147, 743, ('XXXXX',
                    'X box',
                    'XXXXX'))

# C language templates.

Template(211, 118, ('/* box */',))

Template(212, 218, ('/* box */',
                    '/* --- */'))

Template(213, 318, ('/* --- */',
                    '/* box */',
                    '/* --- */'))

Template(214, 418, ('/* box */',
                    '/* === */'))

Template(215, 518, ('/* === */',
                    '/* box */',
                    '/* === */'))

Template(216, 618, ('/* ---',
                    '   box',
                    '   ---*/'))

Template(217, 718, ('/* ===',
                    '   box',
                    '   ===*/'))

Template(221, 128, ('/* ',
                    '   box',
                    '*/'))

Template(222, 228, ('/*    .',
                    '| box |',
                    '`----*/'))

Template(223, 328, ('/*----.',
                    '| box |',
                    '`----*/'))

Template(224, 428, ('/*    \\',
                    '| box |',
                    '\\====*/'))

Template(225, 528, ('/*====\\',
                    '| box |',
                    '\\====*/'))

Template(226, 628, ('/*---',
                    '| box',
                    '`----*/'))

Template(227, 728, ('/*===',
                    '| box',
                    '\\====*/'))

Template(231, 138, ('/*    ',
                    ' | box',
                    ' */   '))

Template(232, 238, ('/*        ',
                    ' | box | ',
                    ' *-----*/'))

Template(233, 338, ('/*-----* ',
                    ' | box | ',
                    ' *-----*/'))

Template(234, 438, ('/* box */',
                    '/*-----*/'))

Template(235, 538, ('/*-----*/',
                    '/* box */',
                    '/*-----*/'))

Template(236, 638, ('/*---- ',
                    ' | box ',
                    ' *----*/'))

Template(237, 738, ('/*----',
                    '   box',
                    '  ----*/'))

Template(241, 148, ('/*    ',
                    ' * box',
                    ' */   '))

Template(242, 248, ('/*     * ',
                    ' * box * ',
                    ' *******/'))

Template(243, 348, ('/******* ',
                    ' * box * ',
                    ' *******/'))

Template(244, 448, ('/* box */',
                    '/*******/'))

Template(245, 548, ('/*******/',
                    '/* box */',
                    '/*******/'))

Template(246, 648, ('/******* ',
                    ' * box * ',
                    ' *******/'))

Template(247, 748, ('/****',
                    '  box',
                    ' *****/'))

Template(251, 158, ('/* ',
                    ' * box',
                    ' */   '))

if __name__ == '__main__':
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = ppppconfig
# -*- coding: utf-8 -*-
# p4 configuration for Pymacs.


# Overall Pymacs configuration
# ============================

# VERSION is the name of the Pymacs version, as declared within setup.py.

def get_version():
    for line in open('setup.cfg'):
        if '=' in line:
            key, value = line.split('=', 1)
            if key.strip() == 'version':
                return value.strip()

VERSION = get_version()
del get_version


# Configuration for the Emacs Lisp side
# =====================================

# DEFADVICE_OK is 't' when it is safe to use defadvice.  It has been reported
# that, at least under Aquamacs (a MacOS X native port of Emacs), one gets
# "Lisp nesting exceeds `max-lisp-eval-depth'" messages while requesting
# functions documentation (we do not know why).  Set this variable to 'nil'
# as a way to avoid the problem.

DEFADVICE_OK = 't'


# PYTHON gets the command name of the Python interpreter.

def get_python():
    import os
    return os.getenv('PYTHON') or 'python'

PYTHON = get_python()
del get_python


# Configuration for Python (Pymacs helper)
# ========================================

# It has been reported that intercepting all signals (and optionally writing
# a trace of them, create IO problems within the Pymacs helper itself.  So for
# now, IO_ERRORS_WITH_SIGNALS is blindly set to True, until I know better.
# When True, only the Interrupt signal gets monitored.

IO_ERRORS_WITH_SIGNALS = True


# OLD_EXCEPTIONS is True for old Python or Jython versions.

def get_old_exceptions():
    return not isinstance(Exception, type)

OLD_EXCEPTIONS = get_old_exceptions()
del get_old_exceptions


# PYTHON3 is True within Python 3.

def get_python3():
    import sys
    return sys.version_info[0] == 3

PYTHON3 = get_python3()
del get_python3

########NEW FILE########
__FILENAME__ = t01_pppp_works
# -*- coding: utf-8 -*-

# Checking if the Poor's Python Pre-Processor works.

exec(compile(open('../pppp').read(), '../pppp', 'exec'))

def setup_module(module):
    run.synclines = False
    run.context = {'TRUE': True, 'FALSE': False}

def validate(input, expected):

    def validate1(input, expected):
        fragments = []
        run.transform_file('pppp.py', input.splitlines(True), fragments.append)
        output = ''.join(fragments)
        assert output == expected, (output, expected)

    validate1(input, expected)
    prefix = ' ' * run.indent
    validate1(
            ''.join([prefix + line for line in input.splitlines(True)]),
            ''.join([prefix + line for line in expected.splitlines(True)]))

def test_none():

    yield (validate,
            '',

            '')

    yield (validate,
            'line1\n',

            'line1\n')

    yield (validate,
            'line1\n'
            'line2\n',

            'line1\n'
            'line2\n')

def test_yes():

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'line2\n'
            'line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            '    line2\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'line1\n'
            'line2\n'
            'if TRUE:\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'if TRUE:\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'line2\n'
            'if TRUE:\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'if TRUE:\n'
            '    line2\n'
            'if TRUE:\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'if TRUE:\n'
            '    line3\n',

            'line1\n'
            'line2\n'
            'line3\n')

def test_no():

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'line2\n'
            'line3\n',

            'line2\n'
            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            '    line2\n'
            'line3\n',

            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            '    line2\n'
            '    line3\n',

            '')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'line3\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            '    line3\n',

            'line1\n')

    yield (validate,
            'line1\n'
            'line2\n'
            'if FALSE:\n'
            '    line3\n',

            'line1\n'
            'line2\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'if FALSE:\n'
            '    line2\n'
            'line3\n',

            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'line2\n'
            'if FALSE:\n'
            '    line3\n',

            'line2\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'if FALSE:\n'
            '    line2\n'
            'if FALSE:\n'
            '    line3\n',

            '')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'if FALSE:\n'
            '    line3\n',

            'line1\n')

def test_unknown():

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'line3\n')

    yield (validate,
            'if UNKNOWN:\n'
            '    line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'if UNKNOWN:\n'
            '    line3\n',

            'if UNKNOWN:\n'
            '    line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'if UNKNOWN:\n'
            '    line3\n')

def test_yes_else():

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'else:\n'
            '    line2\n'
            'line3\n',

            'line1\n'
            'line3\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line1\n'
            'line2\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line1\n'
            'line2\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'if TRUE:\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line1\n'
            'line2\n')

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'else:\n'
            '    line2\n'
            'if TRUE:\n'
            '    line3\n',

            'line1\n'
            'line3\n')

def test_no_else():

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'else:\n'
            '    line2\n'
            'line3\n',

            'line2\n'
            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line3\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line1\n'
            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'if FALSE:\n'
            '    line2\n'
            'else:\n'
            '    line3\n',

            'line3\n')

    yield (validate,
            'if FALSE:\n'
            '    line1\n'
            'else:\n'
            '    line2\n'
            'if FALSE:\n'
            '    line3\n',

            'line2\n')

def test_unknown_else():

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line3\n'
            'line4\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line3\n'
            'line4\n')

def test_elif():

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line2\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line4\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line3\n'
            'else:\n'
            '    line4\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line3\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif TRUE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line3\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line4\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif FALSE:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif TRUE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'else:\n'
            '    line4\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif FALSE:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'else:\n'
            '    line5\n'
            'line6\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            'elif UNKNOWN:\n'
            '    line3\n'
            'elif UNKNOWN:\n'
            '    line4\n'
            'else:\n'
            '    line5\n'
            'line6\n')

def test_nesting():

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            '    if TRUE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line2\n'
            'line3\n'
            'line5\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            '    if FALSE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line2\n'
            'line4\n'
            'line5\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if TRUE:\n'
            '    line2\n'
            '    if UNKNOWN:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line2\n'
            'if UNKNOWN:\n'
            '    line3\n'
            'else:\n'
            '    line4\n'
            'line5\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            '    if TRUE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line6\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            '    if FALSE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line6\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if FALSE:\n'
            '    line2\n'
            '    if UNKNOWN:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'line6\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    if TRUE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    line3\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    if FALSE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n')

    yield (validate,
            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    if UNKNOWN:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n',

            'line1\n'
            'if UNKNOWN:\n'
            '    line2\n'
            '    if UNKNOWN:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'else:\n'
            '    line6\n'
            'line7\n')

def test_regression():

    yield (validate,
            'if TRUE:\n'
            '    line1\n'
            'else:\n'
            '    line2\n'
            '    if FALSE:\n'
            '        line3\n'
            '    else:\n'
            '        line4\n'
            '    line5\n'
            'line6\n',

            'line1\n'
            'line6\n')

########NEW FILE########
__FILENAME__ = t10_pyfile_loads
# -*- coding: utf-8 -*-

# Checking if Pymacs.py loads.

def test_1():
    import setup

########NEW FILE########
__FILENAME__ = t20_helper_loads
# -*- coding: utf-8 -*-

# Checking if the Pymacs helper loads.

import setup

def test_1():
    setup.start_python()
    setup.stop_python()

########NEW FILE########
__FILENAME__ = t30_elfile_loads
# -*- coding: utf-8 -*-

# Checking if pymacs.el loads.

import setup

def test_1():
    setup.start_emacs()
    setup.stop_emacs()

########NEW FILE########
__FILENAME__ = t40_pymacs_loads
# -*- coding: utf-8 -*-

# Checking if Emacs loads the Python helper.

import setup

def test_1():
    setup.start_emacs()
    output = setup.ask_emacs(('(progn\n'
                              '  (pymacs-start-services)\n'
                              '  (not (null pymacs-transit-buffer)))\n'),
                             'prin1')
    assert output == 't', output
    setup.stop_emacs()

########NEW FILE########
