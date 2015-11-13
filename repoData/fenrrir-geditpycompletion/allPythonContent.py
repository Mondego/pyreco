__FILENAME__ = complete
# Copyright (C) 2006 Aaron Griffin
# Copyright (C) 2008 Rodrigo Pinheiro Marques de Araujo
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.



import sys, tokenize, cStringIO, types
from token import NAME, DEDENT, NEWLINE, STRING
from keyword import kwlist

debugstmts=[]
def dbg(s): debugstmts.append(s)
def showdbg():
    for d in debugstmts: print "DBG: %s " % d

def complete(contentfile, match, line):
    cmpl = Completer()
    cmpl.evalsource(contentfile, line)
    all = cmpl.get_completions(match,'') + kw_complete(match)
    return all

def kw_complete(match):
    return [ {"abbr": kw, "word" : kw[len(match):],"info" : "keyword " + kw } for kw in kwlist if kw.startswith(match) ]


class Completer(object):
    def __init__(self):
       self.compldict = {}
       self.parser = PyParser()

    def evalsource(self,text,line=0):
        sc = self.parser.parse(text,line)
        src = sc.get_code()
        dbg("source: %s" % src)
        try: exec(src) in self.compldict
        except: dbg("parser: %s, %s" % (sys.exc_info()[0],sys.exc_info()[1]))
        for l in sc.locals:
            try: exec(l) in self.compldict
            except: dbg("locals: %s, %s [%s]" % (sys.exc_info()[0],sys.exc_info()[1],l))

    def _cleanstr(self,doc):
        return doc.replace('"',' ').replace("'",' ')

    def get_arguments(self,func_obj):
        def _ctor(obj):
            try: return class_ob.__init__.im_func
            except AttributeError:
                for base in class_ob.__bases__:
                    rc = _find_constructor(base)
                    if rc is not None: return rc
            return None

        arg_offset = 1
        if type(func_obj) == types.ClassType: func_obj = _ctor(func_obj)
        elif type(func_obj) == types.MethodType: func_obj = func_obj.im_func
        else: arg_offset = 0
        
        arg_text=''
        if type(func_obj) in [types.FunctionType, types.LambdaType]:
            try:
                cd = func_obj.func_code
                real_args = cd.co_varnames[arg_offset:cd.co_argcount]
                defaults = func_obj.func_defaults or ''
                defaults = map(lambda name: "=%s" % name, defaults)
                defaults = [""] * (len(real_args)-len(defaults)) + defaults
                items = map(lambda a,d: a+d, real_args, defaults)
                if func_obj.func_code.co_flags & 0x4:
                    items.append("...")
                if func_obj.func_code.co_flags & 0x8:
                    items.append("***")
                arg_text = (','.join(items)) + ')'

            except:
                dbg("arg completion: %s: %s" % (sys.exc_info()[0],sys.exc_info()[1]))
                pass
        if len(arg_text) == 0:
            # The doc string sometimes contains the function signature
            #  this works for alot of C modules that are part of the
            #  standard library
            doc = func_obj.__doc__
            if doc:
                doc = doc.lstrip()
                pos = doc.find('\n')
                if pos > 0:
                    sigline = doc[:pos]
                    lidx = sigline.find('(')
                    ridx = sigline.find(')')
                    if lidx > 0 and ridx > 0:
                        arg_text = sigline[lidx+1:ridx] + ')'
        if len(arg_text) == 0: arg_text = ')'
        return arg_text

    def get_completions(self,context,match):
        dbg("get_completions('%s','%s')" % (context,match))
        stmt = ''
        if context: stmt += str(context)
        if match: stmt += str(match)
        try:
            result = None
            all = {}
            ridx = stmt.rfind('.')
            if len(stmt) > 0 and stmt[-1] == '(':
                result = eval(_sanitize(stmt[:-1]), self.compldict)
                doc = result.__doc__
                if doc == None: doc = ''
                args = self.get_arguments(result)
                return [{'word':self._cleanstr(args),'info':self._cleanstr(doc)}]
            elif ridx == -1:
                match = stmt
                all = self.compldict
            else:
                match = stmt[ridx+1:]
                stmt = _sanitize(stmt[:ridx])
                result = eval(stmt, self.compldict)
                all = dir(result)

            dbg("completing: stmt:%s" % stmt)
            completions = []

            try: maindoc = result.__doc__
            except: maindoc = ' '
            if maindoc == None: maindoc = ' '
            for m in all:
                if m == "_PyCmplNoType": continue #this is internal
                try:
                    dbg('possible completion: %s' % m)
                    if m.find(match) == 0:
                        if result == None: inst = all[m]
                        else: inst = getattr(result,m)
                        try: doc = inst.__doc__
                        except: doc = maindoc
                        typestr = str(inst)
                        if doc == None or doc == '': doc = maindoc

                        wrd = m[len(match):]
                        c = {'word':wrd, 'abbr':m,  'info':self._cleanstr(doc)}
                        if "function" in typestr:
                            c['word'] += '('
                            c['abbr'] += '(' + self._cleanstr(self.get_arguments(inst))
                        elif "method" in typestr:
                            c['word'] += '('
                            c['abbr'] += '(' + self._cleanstr(self.get_arguments(inst))
                        elif "module" in typestr:
                            c['word'] += '.'
                        elif "class" in typestr:
                            c['word'] += '('
                            c['abbr'] += '('
                        completions.append(c)
                except:
                    i = sys.exc_info()
                    dbg("inner completion: %s,%s [stmt='%s']" % (i[0],i[1],stmt))
            return completions
        except:
            i = sys.exc_info()
            dbg("completion: %s,%s [stmt='%s']" % (i[0],i[1],stmt))
            return []

class Scope(object):
    def __init__(self,name,indent):
        self.subscopes = []
        self.docstr = ''
        self.locals = []
        self.parent = None
        self.name = name
        self.indent = indent

    def add(self,sub):
        #print 'push scope: [%s@%s]' % (sub.name,sub.indent)
        sub.parent = self
        self.subscopes.append(sub)
        return sub

    def doc(self,str):
        """ Clean up a docstring """
        d = str.replace('\n',' ')
        d = d.replace('\t',' ')
        while d.find('  ') > -1: d = d.replace('  ',' ')
        while d[0] in '"\'\t ': d = d[1:]
        while d[-1] in '"\'\t ': d = d[:-1]
        self.docstr = d

    def local(self,loc):
        if not self._hasvaralready(loc):
            self.locals.append(loc)

    def copy_decl(self,indent=0):
        """ Copy a scope's declaration only, at the specified indent level - not local variables """
        return Scope(self.name,indent)

    def _hasvaralready(self,test):
        "Convienance function... keep out duplicates"
        if test.find('=') > -1:
            var = test.split('=')[0].strip()
            for l in self.locals:
                if l.find('=') > -1 and var == l.split('=')[0].strip():
                    return True
        return False

    def get_code(self):
        # we need to start with this, to fix up broken completions
        # hopefully this name is unique enough...
        str = '"""'+self.docstr+'"""\n'
        for l in self.locals:
            if l.startswith('import'): str += l+'\n'
        str += 'class _PyCmplNoType:\n    def __getattr__(self,name):\n        return None\n'
        for sub in self.subscopes:
            str += sub.get_code()
        for l in self.locals:
            if not l.startswith('import'): str += l+'\n'

        return str

    def pop(self,indent):
        #print 'pop scope: [%s] to [%s]' % (self.indent,indent)
        outer = self
        while outer.parent != None and outer.indent >= indent:
            outer = outer.parent
        return outer

    def currentindent(self):
        #print 'parse current indent: %s' % self.indent
        return '    '*self.indent

    def childindent(self):
        #print 'parse child indent: [%s]' % (self.indent+1)
        return '    '*(self.indent+1)

class Class(Scope):
    def __init__(self, name, supers, indent):
        Scope.__init__(self,name,indent)
        self.supers = supers
    def copy_decl(self,indent=0):
        c = Class(self.name,self.supers,indent)
        c.docstr = self.docstr
        c.locals = self.locals
        for s in self.subscopes:
            c.add(s.copy_decl(indent+1))
        return c
    def get_code(self):
        str = '%sclass %s' % (self.currentindent(),self.name)
        if len(self.supers) > 0: str += '(%s)' % ','.join(self.supers)
        str += ':\n'
        if len(self.docstr) > 0: str += self.childindent()+'"""'+self.docstr+'"""\n'
        if len(self.subscopes) > 0:
            for s in self.subscopes: str += s.get_code()
        else:
            str += '%spass\n' % self.childindent()
        for l in self.locals:
            str += '%s%s\n' % (self.childindent(),l)
        return str


class Function(Scope):
    def __init__(self, name, params, indent):
        Scope.__init__(self,name,indent)
        self.params = params
    def copy_decl(self,indent=0):
        f = Function(self.name,self.params,indent)
        f.docstr = self.docstr
        f.locals = self.locals
        return f 
    def get_code(self):
        str = "%sdef %s(%s):\n" % \
            (self.currentindent(),self.name,','.join(self.params))
        if len(self.docstr) > 0: str += self.childindent()+'"""'+self.docstr+'"""\n'
        for l in self.locals:
            if isinstance(self.parent, Class) and l.startswith('self'):
                self.parent.local(l[5:])
            str += '%s%s\n' % (self.childindent(),l)
        str += "%spass\n" % self.childindent()
        return str

class PyParser:
    def __init__(self):
        self.top = Scope('global',0)
        self.scope = self.top
        self.lvaleu = None

    def _parsedotname(self,pre=None):
        #returns (dottedname, nexttoken)
        name = []
        if pre == None:
            tokentype, token, indent = self.next()
            if tokentype != NAME and token != '*':
                return ('', token)
        else: token = pre
        name.append(token)
        while True:
            tokentype, token, indent = self.next()
            if token != '.': break
            tokentype, token, indent = self.next()
            if tokentype != NAME: break
            name.append(token)
        return (".".join(name), token)

    def _parseimportlist(self):
        imports = []
        while True:
            name, token = self._parsedotname()
            if not name: break
            name2 = ''
            if token == 'as': name2, token = self._parsedotname()
            imports.append((name, name2))
            while token != "," and "\n" not in token:
                tokentype, token, indent = self.next()
            if token != ",": break
        return imports

    def _parenparse(self):
        name = ''
        names = []
        level = 1
        while True:
            tokentype, token, indent = self.next()
            if token in (')', ',') and level == 1:
                names.append(name)
                name = ''
            if token == '(':
                level += 1
            elif token == ')':
                level -= 1
                if level == 0: break
            elif token == ',' and level == 1:
                pass
            else:
                name += str(token)
        return names

    def _parsefunction(self,indent):
        self.scope=self.scope.pop(indent)
        tokentype, fname, ind = self.next()
        if tokentype != NAME: return None

        tokentype, open, ind = self.next()
        if open != '(': return None
        params=self._parenparse()

        tokentype, colon, ind = self.next()
        if colon != ':': return None

        return Function(fname,params,indent)

    def _parseclass(self,indent):
        self.scope=self.scope.pop(indent)
        tokentype, cname, ind = self.next()
        if tokentype != NAME: return None

        super = []
        tokentype, next, ind = self.next()
        if next == '(':
            super=self._parenparse()
        elif next != ':': return None

        return Class(cname,super,indent)

    def _parseassignment(self):
        assign=''
        tokentype, token, indent = self.next()
        if tokentype == tokenize.STRING or token == 'str':  
            return '""'
        elif token == '(' or token == 'tuple':
            return '()'
        elif token == '[' or token == 'list':
            return '[]'
        elif token == '{' or token == 'dict':
            return '{}'
        elif tokentype == tokenize.NUMBER:
            return '0'
        elif token == 'open' or token == 'file':
            return 'file'
        elif token == 'None':
            return '_PyCmplNoType()'
        elif token == 'type':
            return 'type(_PyCmplNoType)' #only for method resolution
        else:
            assign += token
            level = 0
            while True:
                tokentype, token, indent = self.next()
                if token in ('(','{','['):
                    level += 1
                elif token in (']','}',')'):
                    level -= 1
                    if level == 0: break
                elif level == 0:
                    if token in (';','\n'): break
                    assign += token
        return "%s" % assign

    def next(self):
        type, token, (lineno, indent), end, self.parserline = self.gen.next()
        if lineno == self.curline:
            #print 'line found [%s] scope=%s' % (line.replace('\n',''),self.scope.name)
            self.currentscope = self.scope
        return (type, token, indent)

    def _adjustvisibility(self):
        newscope = Scope('result',0)
        scp = self.currentscope
        while scp != None:
            if type(scp) == Function:
                slice = 0
                #Handle 'self' params
                if scp.parent != None and type(scp.parent) == Class:
                    slice = 1
                    p = scp.params[0]
                    i = p.find('=')
                    if i != -1: p = p[:i]
                    newscope.local('%s = %s' % (scp.params[0],scp.parent.name))
                for p in scp.params[slice:]:
                    i = p.find('=')
                    if i == -1:
                        newscope.local('%s = _PyCmplNoType()' % p)
                    else:
                        newscope.local('%s = %s' % (p[:i],_sanitize(p[i+1])))

            for s in scp.subscopes:
                ns = s.copy_decl(0)
                newscope.add(ns)
            for l in scp.locals: newscope.local(l)
            scp = scp.parent


        self.currentscope = newscope

        return self.currentscope

    #p.parse(vim.current.buffer[:],vim.eval("line('.')"))
    def parse(self,text,curline=0):
        self.curline = int(curline)
        buf = cStringIO.StringIO(''.join(text) + '\n')
        self.gen = tokenize.generate_tokens(buf.readline)
        self.currentscope = self.scope

        try:
            freshscope=True
            while True:
                tokentype, token, indent = self.next()
                #dbg( 'main: token=[%s] indent=[%s]' % (token,indent))

                if tokentype == DEDENT or token == "pass":
                    self.scope = self.scope.pop(indent)
                elif token == 'def':
                    func = self._parsefunction(indent)
                    if func == None:
                        print "function: syntax error..."
                        continue
                    freshscope = True
                    self.scope = self.scope.add(func)
                elif token == 'class':
                    cls = self._parseclass(indent)
                    if cls == None:
                        print "class: syntax error..."
                        continue
                    freshscope = True
                    self.scope = self.scope.add(cls)
                    
                elif token == 'import':
                    imports = self._parseimportlist()
                    for mod, alias in imports:
                        loc = "import %s" % mod
                        if len(alias) > 0: loc += " as %s" % alias
                        self.scope.local(loc)
                    freshscope = False
                elif token == 'from':
                    mod, token = self._parsedotname()
                    if not mod or token != "import":
                        print "from: syntax error..."
                        continue
                    names = self._parseimportlist()
                    for name, alias in names:
                        loc = "from %s import %s" % (mod,name)
                        if len(alias) > 0: loc += " as %s" % alias
                        self.scope.local(loc)
                    freshscope = False
                elif tokentype == STRING:
                    if freshscope: self.scope.doc(token)
                elif tokentype == NAME:
                    self.lvalue = token
                    name,token = self._parsedotname(token) 
                    if token == '=':
                        stmt = self._parseassignment()
                        if stmt != None:
                            self.scope.local("%s = %s" % (name,stmt))
                    freshscope = False
        except StopIteration: #thrown on EOF
            pass
        except:
            dbg("parse error: %s, %s @ %s" %
                (sys.exc_info()[0], sys.exc_info()[1], self.parserline))
        return self._adjustvisibility()

def _sanitize(str):
    val = ''
    level = 0
    for c in str:
        if c in ('(','{','['):
            level += 1
        elif c in (']','}',')'):
            level -= 1
        elif level == 0:
            val += c
    return val

sys.path.extend(['.','..'])

########NEW FILE########
__FILENAME__ = configuration
"""
Read and write gconf entry for python code completion. Uses caching to save
number of look-ups.

This code is alpha, it doesn't do very much input validation!
"""
# Copyright (C) 2008 Michael Mc Donnell
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import gconf

GCONF_PLUGIN_PATH = "/apps/gedit-2/plugins/pythoncodecompletion/"
GCONF_KEYBINDING_COMPLETE = GCONF_PLUGIN_PATH + "keybindings/complete"
DEFAULT_KEYBINDING_COMPLETE = "ctrl+alt+space"
MODIFIER_CTRL = "ctrl"
MODIFIER_ALT = "alt"
MODIFIER_SHIFT = "shift"
KEY = "key"

__client = gconf.client_get_default ();
#_client.add_dir(GCONF_PLUGIN_PATH, gconf.CLIENT_PRELOAD_NONE)
__client.add_dir("/apps/gedit-2", gconf.CLIENT_PRELOAD_NONE)

# Cached keybinding
__keybindingComplete = ""
__keybindingCompleteTuple = {}

def getKeybindingComplete():
    """
    Returns a string with the keybinding used to do code completion from the
    configuration file, e.g. "ctrl+alt+space"
    """
    global __keybindingComplete
    # Get keybinding from cache, then gconf or else use default.
    if len(__keybindingComplete) == 0:
        keybinding = __client.get_string(GCONF_KEYBINDING_COMPLETE)
        __keybindingCompleteTuple = {} # Invalidate cache
        if not keybinding:
            __keybindingComplete = DEFAULT_KEYBINDING_COMPLETE
        else:
            __keybindingComplete = keybinding
    
    return __keybindingComplete
    
def getKeybindingCompleteTuple():
    """
    Returns a tuple with the keybinding used to do code completion from the
    configuration file, e.g. {"alt" : True, "ctrl" : True, "key" : "space"}.
    """
    global __keybindingCompleteTuple
    # Return cached result
    if len(__keybindingCompleteTuple) != 0:
        return __keybindingCompleteTuple
        
    # Parse keybinding
    alt = False
    ctrl = False
    shift = False
    key = ""
    keybinding = getKeybindingComplete().split('+')
    keybindingTuple = {
        MODIFIER_CTRL : False,
        MODIFIER_ALT : False,
        MODIFIER_SHIFT : False,
        KEY : ""
    }
    
    for s in keybinding:
        s = s.lower()
        if s == MODIFIER_ALT:
            keybindingTuple[MODIFIER_ALT] = True
        elif s == MODIFIER_CTRL:
            keybindingTuple[MODIFIER_CTRL] = True
        elif s == MODIFIER_SHIFT:
            keybindingTuple[MODIFIER_SHIFT] = True
        else:
            keybindingTuple[KEY] = s 
    
    __keybindingCompleteTuple = keybindingTuple
    
    return __keybindingCompleteTuple
    
def setKeybindingComplete(keybinding):
    """
    Saves a string with the keybinding used to do code completion to the gconf
    entry, e.g. "ctrl+alt+space".
    """
    global __keybindingComplete
    global __keybindingCompleteTuple
    __client.set_string(GCONF_KEYBINDING_COMPLETE, keybinding)
    __keybindingComplete = keybinding
    __keybindingCompleteTuple = {}
      
if __name__ == "__main__":
    __client.set_string(GCONF_KEYBINDING_COMPLETE, DEFAULT_KEYBINDING_COMPLETE)
    print "Old keybindging was:", getKeybindingComplete()
    print "Old keybindging tuple was:", getKeybindingCompleteTuple()
    newKeybinding = "ctrl+space"
    print "Setting to new keybinding:", newKeybinding
    setKeybindingComplete(newKeybinding)
    print "New keybinding is:", getKeybindingComplete()
    print "New keybinding tuple is:", getKeybindingCompleteTuple()

########NEW FILE########
__FILENAME__ = configurationdialog
# Copyright (C) 2008 Michael Mc Donnell
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
import gtk
import gtk.gdk
import logging
import keybindingwidget
import configuration

TEXT_KEYBINDING = "Keybinding:"
TEXT_TITLE = "Configure python code completion"
DEFAULT_WINDOW_WIDTH = 370
DEFAULT_WINDOW_HEIGHT = 0
LOG_NAME = "ConfigurationDialog"

log = logging.getLogger(LOG_NAME)

class ConfigurationDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self)
        self.set_border_width(5)
        self.set_title(TEXT_TITLE)
        self.set_default_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.changes = []
        keybinding = configuration.getKeybindingComplete()
        log.info("Got keybinding from gconf %s" % str(keybinding))
        self.__setKeybinding(keybinding)
        
        self.table = gtk.Table(2, 2, homogeneous=False)
        self.table.set_row_spacings(4)
        self.table.set_col_spacings(4)
        self.vbox.pack_start(self.table, expand=False, fill=False, padding=4) 
        
        lblKeybinding = gtk.Label()
        lblKeybinding.set_text(TEXT_KEYBINDING)
        self.table.attach(lblKeybinding, 0, 1, 0, 1, xoptions=False, yoptions=False)        
        
        self.__kbWidget = keybindingwidget.KeybindingWidget()
        self.__kbWidget.setKeybinding(keybinding)
        self.table.attach(self.__kbWidget, 1, 2, 0, 1, xoptions=False, yoptions=False)
        
        # Buttons in the action area
        btnClose = gtk.Button(stock=gtk.STOCK_CLOSE)
        self.__btnApply = gtk.Button(stock=gtk.STOCK_APPLY)
        self.__btnApply.set_sensitive(False)
        btnClear =  gtk.Button(stock=gtk.STOCK_CLEAR)
        self.action_area.add(btnClear)
        self.action_area.add(self.__btnApply)
        self.action_area.add(btnClose)
        
        # Connect all signals
        self.__kbWidget.connect("keybinding-changed", self.on_keybinding_changed)
        btnClose.connect("clicked", self.close)
        self.__btnApply.connect("clicked", self.applyChanges)
        btnClear.connect("clicked", self.clearChanges)
        self.connect('delete-event', self.close)
        
        self.show_all()
    
    def __getKeybinding(self):
        return self.__keybinding
        
    def __setKeybinding(self, keybinding):
        self.__keybinding = keybinding
        
    def on_keybinding_changed(self, widget, keybinding):
        log.info("on_keybinding_changed")
        log.info("New keybinding is %s" % str(keybinding))
        change1 = (configuration.setKeybindingComplete, keybinding)
        change2 = (self.__setKeybinding, keybinding)
        self.changes.append(change1)
        self.changes.append(change2)
        
        self.__btnApply.set_sensitive(True)
        
    def clearChanges(self, widget):
        log.info("clearChanges")
        self.changes = []
        self.__kbWidget.setKeybinding(self.__getKeybinding())
        self.__btnApply.set_sensitive(False)
    
    def applyChanges(self, widget):
        log.info("applyChanges")
        # Commit changes (function pointer, data)
        for change in self.changes:
            change[0](change[1])
        
        self.__btnApply.set_sensitive(False)
        
    def close(self, widget, *event):
        log.info("close")
        self.hide()
        self.destroy()
        
if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    
    dlg = ConfigurationDialog()

    gtk.main()

########NEW FILE########
__FILENAME__ = keybindingwidget
"""
A widget for entering keybindings, e.g. ctr+alt+space.

Signals: keybinding-changed
"""
# Copyright (C) 2008 Michael Mc Donnell
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import gtk
from gtk import gdk
import gobject
import pygtk
import string

import logging

ACTIVATED_TEXT = "Press new keybinding..."
LOG_NAME = "KeybindingWidget"
COLOR_FOCUS_IN = "white"
DEFAULT_TEXT = "None set"
WIDTH_CHARS = 18

log = logging.getLogger(LOG_NAME)

class KeybindingWidget(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)
        log.info("Initializing KeybindingWidget.")
        
        self._label = gtk.Label()
        self._label.set_text(DEFAULT_TEXT)
        self._label.set_width_chars(WIDTH_CHARS)
        self._label.set_alignment(0.0, 0.5)
        self._label.unset_flags(gtk.CAN_FOCUS)
        self.add(self._label)
        
        events = gdk.BUTTON_PRESS_MASK | gdk.KEY_PRESS_MASK | gdk.FOCUS_CHANGE_MASK
        self.add_events(events)
        
        self.active = False
        
        self._keybinding = []
    
    def getKeybinding(self):
        return self._keybinding
    
    def setKeybinding(self, keybinding):
        self._keybinding = keybinding
        self._label.set_text(keybinding)
        
    def do_button_press_event(self, event):
        log.info("do_button_press_event()")
        log.info("Grabbing focus.")
        self.set_flags(gtk.CAN_FOCUS)
        self.grab_focus()
        self.modify_bg(gtk.STATE_NORMAL, gdk.color_parse(COLOR_FOCUS_IN))
        self.active = True

    def do_key_press_event(self, event):
        if not self.active:
            return False
        log.info("do_key_press_event()")
        key_name = gdk.keyval_name(event.keyval)
        log.info("key_name = " + str(key_name))
        
        # Deactivate on Escape
        if key_name == "Escape":
            self.deactivate()
            return True

        keybinding = []
        
        # FIXME Doesn't work with any super combination
        # FIXME What if keys are already used by another plugin?
        if key_name == "space" or key_name == "Tab" \
            or key_name in string.ascii_letters:
            # Check for Ctrl
            if event.state & gdk.CONTROL_MASK:
                log.info("Ctrl held down.")
                keybinding.append("ctrl")
            # Check for Alt
            if event.state & gdk.MOD1_MASK:
                log.info("Alt held down.")
                keybinding.append("alt")
            # Check for Shift
            if event.state & gdk.SHIFT_MASK:
                log.info("Shift held down.")
                keybinding.append("shift")

            keybinding.append(key_name.lower())
            log.info("Setting key keybinding to " + '+'.join(keybinding))
            self.setKeybinding('+'.join(keybinding))
            self.deactivate()
            self.emit("keybinding-changed", self.getKeybinding())
            return True
            
    def do_focus_out_event(self, event):
        log.info("do_focus_out_event()")
        self.deactivate()
        
    def deactivate(self):
        # Revert color back to normal
        default_bg_color = self.parent.get_style().bg[gtk.STATE_NORMAL]
        self.modify_bg(gtk.STATE_NORMAL, default_bg_color)
        self.unset_flags(gtk.CAN_FOCUS)
        self.active = False
        keybinding = self.getKeybinding()
        
        if not keybinding:
            self._label.set_text(DEFAULT_TEXT)
        else:
            self._label.set_text(keybinding)
        

gobject.type_register(KeybindingWidget)
gobject.signal_new("keybinding-changed", KeybindingWidget,
                       gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,))

# Tests below

def on_keybinding_changed(widget, keybinding):
    print "on_keybinding_changed()"
    print "New keybinding is", keybinding

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(logging.DEBUG)

    win = gtk.Window()
    win.set_border_width(5)
    win.set_title('KeybindingWidget test')
    win.connect('delete-event', gtk.main_quit)

    hbox = gtk.HBox(homogeneous=False, spacing=4)
    win.add(hbox)

    table = gtk.Table(2, 2, homogeneous=False)
    table.set_row_spacings(4)
    table.set_col_spacings(4)
    hbox.pack_start(table)

    lblKeybinding = gtk.Label()
    lblKeybinding.set_text("Keybinding:")
    # Put in upper left quadrant
    table.attach(lblKeybinding, 0, 1, 0, 1, xoptions=False, yoptions=False)
    
    kbind = KeybindingWidget()
    # Put in upper right quadrant
    table.attach(kbind, 1, 2, 0, 1, xoptions=False, yoptions=False)
    kbind.connect("keybinding-changed", on_keybinding_changed)

    lblStuff = gtk.Label()
    lblStuff.set_text("Enter stuff:")
    # Put in lower left quadrant
    table.attach(lblStuff, 0, 1, 1, 2, xoptions=False, yoptions=False)
    
    entryStuff = gtk.Entry()
    # Put in lower right quadrant
    table.attach(entryStuff, 1, 2, 1, 2, xoptions=False, yoptions=False)
    
    win.show_all()

    gtk.main()

########NEW FILE########
__FILENAME__ = pythoncodecompletion
# Copyright (C) 2006-2007 Osmo Salomaa
# Copyright (C) 2008 Rodrigo Pinheiro Marques de Araujo
# Copyright (C) 2008 Michael Mc Donnell                      
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


"""Complete python code with Ctrl+Alt+Space key combination."""


import gedit
import gobject
import gtk
import re
from complete import complete
import configurationdialog
import configuration

class CompletionWindow(gtk.Window):

    """Window for displaying a list of completions."""

    def __init__(self, parent, callback):

        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.set_decorated(False)
        self.store = None
        self.view = None
        self.completions = None
        self.complete_callback = callback
        self.set_transient_for(parent)
        self.set_border_width(1)
        self.text = gtk.TextView()
        self.text_buffer = gtk.TextBuffer()
        self.text.set_buffer(self.text_buffer)
        self.text.set_size_request(300, 200)
        self.text.set_sensitive(False)
        self.init_tree_view()
        self.init_frame()
        self.connect('focus-out-event', self.focus_out_event) 
        self.connect('key-press-event', self.key_press_event)
        self.grab_focus()

    
    def key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide()
        elif event.keyval == gtk.keysyms.BackSpace:
            self.hide()
        elif event.keyval in (gtk.keysyms.Return, gtk.keysyms.Tab):
            self.complete()
        elif event.keyval == gtk.keysyms.Up:
            self.select_previous()
        elif event.keyval == gtk.keysyms.Down:
            self.select_next()

    def complete(self):
        self.complete_callback(self.completions[self.get_selected()]['completion'])

    def focus_out_event(self, *args):
        self.hide()
    
    def get_selected(self):
        """Get the selected row."""

        selection = self.view.get_selection()
        return selection.get_selected_rows()[1][0][0]

    def init_frame(self):
        """Initialize the frame and scroller around the tree view."""

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)
        scroller.add(self.view)
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_OUT)
        hbox = gtk.HBox()
        hbox.add(scroller)

        scroller_text = gtk.ScrolledWindow() 
        scroller_text.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroller_text.add(self.text)
        hbox.add(scroller_text)
        frame.add(hbox)
        self.add(frame)

    def init_tree_view(self):
        """Initialize the tree view listing the completions."""

        self.store = gtk.ListStore(gobject.TYPE_STRING)
        self.view = gtk.TreeView(self.store)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("", renderer, text=0)
        self.view.append_column(column)
        self.view.set_enable_search(False)
        self.view.set_headers_visible(False)
        self.view.set_rules_hint(True)
        selection = self.view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        self.view.set_size_request(200, 200)
        self.view.connect('row-activated', self.row_activated)

    def row_activated(self, tree, path, view_column, data = None):
        self.complete()

    def select_next(self):
        """Select the next completion."""

        row = min(self.get_selected() + 1, len(self.store) - 1)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def select_previous(self):
        """Select the previous completion."""

        row = max(self.get_selected() - 1, 0)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def set_completions(self, completions):
        """Set the completions to display."""

        self.completions = completions
        self.completions.reverse()
        self.resize(1, 1)
        self.store.clear()
        for completion in completions:
            self.store.append([unicode(completion['abbr'])])
        self.view.columns_autosize()
        self.view.get_selection().select_path(0)
        self.text_buffer.set_text(self.completions[self.get_selected()]['info'])

    def set_font_description(self, font_desc):
        """Set the label's font description."""

        self.view.modify_font(font_desc)


class CompletionPlugin(gedit.Plugin):

    """Complete python code with the tab key."""

    re_alpha = re.compile(r"\w+", re.UNICODE | re.MULTILINE)
    re_non_alpha = re.compile(r"\W+", re.UNICODE | re.MULTILINE)

    def __init__(self):

        gedit.Plugin.__init__(self)
        self.completes = None
        self.completions = None
        self.name = "CompletionPlugin"
        self.popup = None
        self.window = None

    def activate(self, window):
        """Activate plugin."""

        self.window = window
        self.popup = CompletionWindow(window, self.complete)
        handler_ids = []
        callback = self.on_window_tab_added
        handler_id = window.connect("tab-added", callback)
        handler_ids.append(handler_id)
        window.set_data(self.name, handler_ids)
        for view in window.get_views():
            self.connect_view(view)

    def cancel(self):
        """Hide the completion window and return False."""

        self.hide_popup()
        return False

    def complete(self, completion):
        """Complete the current word."""

        doc = self.window.get_active_document()
        index = self.popup.get_selected()
        doc.insert_at_cursor(completion)
        self.hide_popup()
        
    def connect_view(self, view):
        """Connect to view's signals."""

        handler_ids = []
        callback = self.on_view_key_press_event
        handler_id = view.connect("key-press-event", callback)
        handler_ids.append(handler_id)
        view.set_data(self.name, handler_ids)

    def create_configure_dialog(self):
        """Creates and displays a ConfigurationDialog."""
        dlg = configurationdialog.ConfigurationDialog()
        return dlg

    def deactivate(self, window):
        """Deactivate plugin."""

        widgets = [window]
        widgets.append(window.get_views())
        widgets.append(window.get_documents())
        for widget in widgets:
            handler_ids = widget.get_data(self.name)
            for handler_id in handler_ids:
                widget.disconnect(handler_id)
            widget.set_data(self.name, None)
        self.hide_popup()
        self.popup = None
        self.window = None

    def display_completions(self, view, event):
        """Find completions and display them."""

        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if not self.re_alpha.match(char) and not char == ".":
                start.forward_char()
                break
        incomplete = unicode(doc.get_text(start, insert))
        incomplete += unicode(event.string)
        if incomplete.isdigit():
            return self.cancel()
        completes =  complete( doc.get_text(*doc.get_bounds()), incomplete, insert.get_line())
        if not completes:
            return self.cancel()
        self.completes = completes

        if "." in incomplete:
            incompletelist = incomplete.split('.')
            newword = incompletelist[-1]
            self.completions = list(x['abbr'][len(newword):] for x in completes)
            length = len(newword)
        else:
            self.completions = list(x['abbr'][len(incomplete):] for x in completes)
            length = len(incomplete)
        for x in completes:
            x['completion'] = x['abbr'][length:]
        window = gtk.TEXT_WINDOW_TEXT
        rect = view.get_iter_location(insert)
        x, y = view.buffer_to_window_coords(window, rect.x, rect.y)
        x, y = view.translate_coordinates(self.window, x, y)
        self.show_popup(completes, x, y)

    def hide_popup(self):
        """Hide the completion window."""

        self.popup.hide()
        self.completes = None
        self.completions = None

    def is_configurable(self):
        """Show the plugin as configurable in gedits plugin list."""
        return True

    def on_view_key_press_event(self, view, event):
        """Display the completion window or complete the current word."""
        active_doc = self.window.get_active_document()
        if active_doc is None or active_doc.get_mime_type() != 'text/x-python':
            return self.cancel()

        # FIXME This might result in a clash with other plugins eg. snippets
        # FIXME This code is not portable! 
        #  The "Alt"-key might be mapped to something else
        # TODO Find out which keybinding are already in use.
        keybinding = configuration.getKeybindingCompleteTuple()
        ctrl_pressed = (event.state & gtk.gdk.CONTROL_MASK) == gtk.gdk.CONTROL_MASK
        alt_pressed = (event.state & gtk.gdk.MOD1_MASK) == gtk.gdk.MOD1_MASK
        shift_pressed = (event.state & gtk.gdk.SHIFT_MASK) == gtk.gdk.SHIFT_MASK
        keyval = gtk.gdk.keyval_from_name(keybinding[configuration.KEY])
        key_pressed = (event.keyval == keyval)

        # It's ok if a key is pressed and it's needed or
        # if a key is not pressed if it isn't needed.
        ctrl_ok = not (keybinding[configuration.MODIFIER_CTRL] ^ ctrl_pressed )
        alt_ok =  not (keybinding[configuration.MODIFIER_ALT] ^ alt_pressed )
        shift_ok = not (keybinding[configuration.MODIFIER_SHIFT] ^ shift_pressed )

        if ctrl_ok and alt_ok and shift_ok and key_pressed or event.keyval == gtk.keysyms.period:
            return self.display_completions(view, event)
        
        return self.cancel()

    def on_window_tab_added(self, window, tab):
        """Connect the document and view in tab."""

        context = tab.get_view().get_pango_context()
        font_desc = context.get_font_description()
        self.popup.set_font_description(font_desc)
        self.connect_view(tab.get_view())


    def show_popup(self, completions, x, y):
        """Show the completion window."""

        root_x, root_y = self.window.get_position()
        self.popup.move(root_x + x + 24, root_y + y + 44)
        self.popup.set_completions(completions)
        self.popup.show_all()
        

########NEW FILE########
