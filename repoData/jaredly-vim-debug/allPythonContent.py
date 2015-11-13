__FILENAME__ = install-vim-debug
#!/usr/bin/env python

text = '''\
" DBGp client: a remote debugger interface to the DBGp protocol
"
" Script Info and Documentation  {{{
"=============================================================================
"    Copyright: Copyright (C) 2010 Jared Forsyth
"      License:	The MIT License

" Do not source this script when python is not compiled in.
if !has("python")
    finish
endif

" set this to 0 to enable the automatic mappings
" any other value will disable the mappings
let g:vim_debug_disable_mappings = 0

python << EOF
import vim
try:
    from vim_debug.commands import debugger_cmd
    vim.command('let has_debug = 1')
except ImportError, e:
    vim.command('let has_debug = 0')
    print 'python module vim_debug not found...'
EOF

if !has_debug
    finish
endif

command! -nargs=* Dbg python debugger_cmd('<args>')

" Debugger highlighting
hi DbgCurrent term=reverse ctermfg=White ctermbg=Red gui=reverse
hi DbgBreakPt term=reverse ctermfg=White ctermbg=Green gui=reverse
sign define current text=->  texthl=DbgCurrent linehl=DbgCurrent
sign define breakpt text=B>  texthl=DbgBreakPt linehl=DbgBreakPt
'''

import os, platform, sys
which = platform.system()
user = os.path.expanduser('~')
vim_dir = os.environ.get('VIM')
if vim_dir is None:
    if (which == 'Linux') or (which == 'Darwin'):
        vim_dir = os.path.join(user, '.vim')
    elif which == 'Windows':
        vim_dir = os.path.join(user, 'vimfiles')
    else:
        print>>sys.stderr, 'No $VIM directory found'
        sys.exit(1)
vim_dir = os.path.join(vim_dir, 'plugin')
if not os.path.exists(vim_dir):
    os.makedirs(vim_dir)
fname = os.path.join(vim_dir, 'debugger.vim')
if os.path.exists(fname):
    print>>sys.stderr, 'Looks like it\'s already installed (at %s)' % fname
    sys.exit(2)
print 'installing to %s' % fname
open(fname, 'w').write(text)
print 'finished'




# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = commands
import os
import sys
import vim
import socket
import traceback
from new_debugger import Debugger

import shlex

def get_vim(name, default, fn=str):
    if vim.eval('exists("%s")' % name) == '1':
        return vim.eval(name)
    return default

_old_commands = _commands = {}
def debugger_cmd(plain):
    global _commands, debugger
    if not _commands:
        return start(*shlex.split(plain))
    if ' ' in plain:
        name, plain = plain.split(' ', 1)
        args = shlex.split(plain)
    else:
        name = plain
        plain = ''
        args = []
    if name not in _commands:
        print '[usage:] dbg command [options]'
        tpl = ' - %-7s :: %s'
        leader = get_vim('mapleader', '\\')
        for command in _commands:
            print tpl % (command, _commands[command]['options'].get('help', ''))
            if 'lead' in _commands[command]['options']:
                print '           shortcut: %s%s' % (leader, _commands[command]['options']['lead'])
        return
    cmd = _commands[name]
    try:
        if not callable(cmd['function']):
            if debugger.bend.connected():
                    debugger.bend.command(cmd['function'])
        elif cmd['options'].get('plain', False):
            cmd['function'](plain)
        else:
            cmd['function'](*args)
    except (EOFError, socket.error):
        if debugger is not None:
            debugger.disable()
    if name == 'quit':
        _commands = None
        debugger = None

def cmd(name, help='', plain=False):
    def decor(fn):
        _commands[name] = {'function':fn, 'options': {'help':help, 'plain':plain}}
        return fn
    return decor

debugger = None

def start(url = None):
    global debugger
    if debugger and debugger.started:
        return
    if url is not None:
        if url in ('.', '-'):
            pass
        elif url.isdigit():
            urls = load_urls()
            num = int(url)
            if num < 0 or num >= len(urls):
                print 'invalid session number'
                url = None
            else:
                url = urls.pop(num)
                urls.insert(0, url)
        else:
            save_url(url)
        if url is not None:
            debugger = Debugger()
            fname = vim.current.buffer.name
            debugger.init_vim()
            global _commands
            _commands = debugger.commands()
            if url == '.':
                if not (os.path.exists(fname) and fname.endswith('.py')):
                    print 'Current file is not python (or doesn\'t exist on your hard drive)'
                    return
                debugger.start_py(fname)
            elif url == '-':
                debugger.start()
            else:
                debugger.start_url(url)
            return
    urls = load_urls()
    if not urls:
        print 'No saved sessions'
    for i, url in enumerate(urls):
        print '    %d) %s' % (i, url)
    print '''\
usage: dbg - (no auto start)
       dbg . (autostart current file -- python)
       dbg url (autostart a URL -- PHP)
       dbg num (autostart a past url -- PHP)'''

session_path = os.path.expanduser('~/.vim/vim_phpdebug.sess')

def load_urls():
    if os.path.exists(session_path):
        return open(session_path).read().split('\n')
    return []

def save_url(url):
    urls = load_urls()
    urls.insert(0, url)
    urls = urls[:5]
    open(session_path, 'w').write('\n'.join(urls))


########NEW FILE########
__FILENAME__ = dbgp
import socket
import base64
import xml.dom.minidom

class DBGP:
    """ DBGp Procotol class """
    def __init__(self, options, log=lambda text:None, type=None):
        self.sock = PacketSocket(options)
        self.cid = 0
        self.received = 0
        self.handlers = {}
        self.addCommandHandler = self.handlers.__setitem__
        self.connect = self.sock.accept
        self.close = self.sock.close
        self.log = log
        self._type = type

    def connected(self):
        return self.sock.connected

    def command(self, cmd, *args, **kargs):
        tpl = '%s -i %d%s%s'
        self.cid += 1
        data = kargs.pop('data', '')
        str_args = ''.join(' -%s %s' % arg for arg in zip(args[::2], args[1::2])) # args.iteritems())
        if data:
            b64data = ' -- ' + base64.encodestring(data)[:-1]
            if self._type == 'python':
                str_args += ' -l %d' % (len(b64data)-4)
        else:
            b64data = ''
        cmd = tpl % (cmd, self.cid, str_args, b64data)
        self.log('SEND: %s' % cmd)
        self.sock.send(cmd)
        if not kargs.get('suppress', False):
            self.get_packets()
        return self.cid
    
    def get_packets(self, force=0):
        while self.received < self.cid or force > 0:
            force -= 1
            if not self.sock.sock:
                return
            packet = self.sock.read_packet()
            # print 'packet:', self.received, self.cid
            # print packet.toprettyxml(indent='   ')
            self.log('RECV: %s' % packet.toprettyxml(indent='   '))
            if packet.tagName == 'response':
                if packet.getAttribute('transaction_id') == '':
                    self.handlers['error'](packet.firstChild)
                    continue
                id = int(packet.getAttribute('transaction_id'))
                if id > self.received:
                    self.received = id
                else:
                    print 'weird -- received is greater than the id I just got: %d %d' % (self.received, id)
                cmd = packet.getAttribute('command')
                if cmd in self.handlers:
                    self.handlers[cmd](packet)
                else:
                    raise TypeError('invalid packet type:', cmd)
            elif packet.tagName == 'stream':
                if '<stream>' in self.handlers and packet.firstChild is not None:
                    text = base64.decodestring(packet.firstChild.data)
                    self.handlers['<stream>'](packet.getAttribute('type'), text)
            elif packet.tagName == 'init':
                self.handlers['<init>'](packet)
            else:
                print 'tagname', packet.tagName

class PacketSocket:
    def __init__(self, options):
        self.options = options
        self.sock = None
        self.connected = False

    def accept(self):
        # print 'waiting for a new connection on port %d for %d seconds...' % (self.options.get('port', 9000),
        #                                                                      self.options.get('wait', 5))
        self.connected = False
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.setdefaulttimeout(20)
        serv.settimeout(5)
        try:
            serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serv.bind(('', self.options.get('port', 9000)))
            serv.listen(self.options.get('listens', 5))
            print 'waiting for a connection'
            (self.sock, address) = serv.accept()
        except socket.timeout:
            serv.close()
            return False

        # print 'connection from ', address
        self.connected = True
        serv.close()
        return True
    
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False

    def read(self, size):
        '''main receiving class...'''
        text = ''
        while size > 0:
            buf = self.sock.recv(size)
            if buf == '':
                self.close()
                raise EOFError, 'Socket Closed'
            text += buf
            size -= len(buf)
        return text

    def read_number(self):
        length = ''
        while 1:
            if not self.sock:
                raise EOFError, 'Socket Closed'
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            if c == '\0':
                return int(length)
            if c.isdigit():
                length += c

    def read_null(self):
        '''read a null byte'''
        c = self.sock.recv(1)
        if c != '\0':
            raise Exception('invalid response from debug server')
        '''
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            if c == '\0':
                return
                '''

    def read_packet(self):
        '''read a packet from the server and return the xml tree'''
        length = self.read_number()
        body = self.read(length)
        self.read_null()
        return xml.dom.minidom.parseString(body).firstChild

    def send(self, cmd):
        self.sock.send(cmd + '\0')

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = debugger
# -*- c--oding: ko_KR.UTF-8 -*-
# remote PHP debugger : remote debugger interface to DBGp protocol
#
# Copyright (c) 2010 Jared Forsyth
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# Authors:
#    Seung Woo Shin <segv <at> sayclub.com>
#    Sam Ghods <sam <at> box.net>
#    Jared Forsyth <jared@jaredforsyth.com>

import os
import sys
import vim
import base64
import textwrap
import xml.dom.minidom

from ui import DebugUI
from protocol import DbgProtocol

class BreakPointManager:
    """ Breakpoint manager class """
    def __init__(self):
        """ initalize """
        self.breakpt = {}
        self.revmap = {}
        self.startbno = 10000
        self.maxbno = self.startbno
    def clear(self):
        """ clear of breakpoint number """
        self.breakpt.clear()
        self.revmap.clear()
        self.maxbno = self.startbno
    def add(self, file, line, exp = ''):
        """ add break point at file:line """
        self.maxbno = self.maxbno + 1
        self.breakpt[self.maxbno] = { 'file':file, 'line':line, 'exp':exp, 'id':None }
        return self.maxbno
    def remove(self, bno):
        """ remove break point numbered with bno """
        del self.breakpt[bno]
    def find(self, file, line):
        """ find break point and return bno(breakpoint number) """
        for bno in self.breakpt.keys():
            if self.breakpt[bno]['file'] == file and self.breakpt[bno]['line'] == line:
                return bno
        return None
    def getfile(self, bno):
        """ get file name of breakpoint numbered with bno """
        return self.breakpt[bno]['file']
    def getline(self, bno):
        """ get line number of breakpoint numbered with bno """
        return self.breakpt[bno]['line']
    def getexp(self, bno):
        """ get expression of breakpoint numbered with bno """
        return self.breakpt[bno]['exp']
    def getid(self, bno):
        """ get Debug Server's breakpoint numbered with bno """
        return self.breakpt[bno]['id']
    def setid(self, bno, id):
        """ get Debug Server's breakpoint numbered with bno """
        self.breakpt[bno]['id'] = id
    def list(self):
        """ return list of breakpoint number """
        return self.breakpt.keys()

class Debugger:
    """ Main Debugger class """


    #################################################################################################################
    # Internal functions
    #
    def __init__(self, port = 9000, max_children = '32', max_data = '1024', max_depth = '1', minibufexpl = '0', debug = 0):
        """ initialize Debugger """
        self.debug = debug

        self.current = None
        self.file = None
        self.lasterror = None
        self.msgid = 0
        self.running = 0
        self.stacks = []
        self.curstack = 0
        self.laststack = 0
        self.bptsetlst = {} 

        self.status = None
        self.max_children = max_children
        self.max_data = max_data
        self.max_depth = max_depth

        self.protocol = DbgProtocol(port)

        self.ui = DebugUI(minibufexpl)
        self.breakpt = BreakPointManager()

        vim.command('sign unplace *')

    def clear(self):
        self.current = None
        self.lasterror = None
        self.msgid = 0
        self.running = 0
        self.stacks = []
        self.curstack = 0
        self.laststack = 0
        self.bptsetlst = {} 

        self.protocol.close()

    def send(self, msg):
        """ send message """
        self.protocol.send_msg(msg)
        # log message
        if self.debug:
            self.ui.windows['trace'].write(str(self.msgid) + ' : send =====> ' + msg)
    def recv(self, count=10000):
        """ receive message until response is last transaction id or received count's message """
        while count>0:
            count = count - 1
            # recv message and convert to XML object
            txt = self.protocol.recv_msg()
            res = xml.dom.minidom.parseString(txt)
            # log messages {{{
            if self.debug:
                self.ui.windows['trace'].write( str(self.msgid) + ' : recv <===== {{{     ' + txt)
                self.ui.windows['trace'].write('}}}')
            # handle message
            self.handle_msg(res)
            # exit, if response's transaction id == last transaction id
            try:
                if int(res.firstChild.getAttribute('transaction_id')) == int(self.msgid):
                    return
            except:
                pass

    def send_command(self, cmd, arg1 = '', arg2 = ''):
        """ send command (do not receive response) """
        self.msgid = self.msgid + 1
        line = cmd + ' -i ' + str(self.msgid)
        if arg1 != '':
            line = line + ' ' + arg1
        if arg2 != '':
            line = line + ' -- ' + base64.encodestring(arg2)[0:-1]
        self.send(line)
        return self.msgid
    #
    #
    #################################################################################################################

    #################################################################################################################
    # Internal message handlers
    #
    def handle_msg(self, res):
        """ call appropraite message handler member function, handle_XXX() """
        fc = res.firstChild
        try:
            handler = getattr(self, 'handle_' + fc.tagName)
            handler(res)
        except AttributeError:
            print 'Debugger.handle_'+fc.tagName+'() not found, please see the LOG___WINDOW'
        self.ui.go_srcview()
    def handle_response(self, res):
        """ call appropraite response message handler member function, handle_response_XXX() """
        if res.firstChild.hasAttribute('reason') and res.firstChild.getAttribute('reason') == 'error':
            self.handle_response_error(res)
            return
        errors = res.getElementsByTagName('error')
        if len(errors)>0:
            self.handle_response_error(res)
            return

        command = res.firstChild.getAttribute('command')
        try:
            handler = getattr(self, 'handle_response_' + command)
        except AttributeError:
            print res.toprettyxml()
            print 'Debugger.handle_response_'+command+'() not found, please see the LOG___WINDOW'
            return
        handler(res)
        return

    def handle_init(self, res):
        """handle <init> tag
        <init appid="7035" fileuri="file:///home/segv/htdocs/index.php" language="PHP" protocol_version="1.0">
            <engine version="2.0.0beta1">
                Xdebug
            </engine>
            <author>
                Derick Rethans
            </author>
            <url>
                http://xdebug.org
            </url>
            <copyright>
                Copyright (c) 2002-2004 by Derick Rethans
            </copyright>
        </init>"""
     
        file = res.firstChild.getAttribute('fileuri')
        self.ui.set_srcview(file, 1)

    def handle_response_error(self, res):
        """ handle <error> tag """
        self.ui.windows['trace'].write_xml_childs(res)

    def handle_response_stack_get(self, res):
        """handle <response command=stack_get> tag
        <response command="stack_get" transaction_id="1 ">
            <stack filename="file:///home/segv/htdocs/index.php" level="0" lineno="41" where="{main}"/>
        </response>"""

        stacks = res.getElementsByTagName('stack')
        if len(stacks)>0:
            self.curstack = 0
            self.laststack = len(stacks) - 1

            self.stacks = []
            for s in stacks:
                self.stacks.append( {'file': s.getAttribute('filename'),
                                     'line': int(s.getAttribute('lineno')),
                                     'where': s.getAttribute('where'),
                                     'level': int(s.getAttribute('level'))
                                     } )

            self.ui.windows['stack'].clean()
            self.ui.windows['stack'].highlight_stack(self.curstack)

            self.ui.windows['stack'].write_xml_childs(res.firstChild) #str(res.toprettyxml()))
            self.ui.set_srcview( self.stacks[self.curstack]['file'], self.stacks[self.curstack]['line'] )


    def handle_response_step_out(self, res):
        """handle <response command=step_out> tag
        <response command="step_out" reason="ok" status="break" transaction_id="1 "/>"""
        if res.firstChild.hasAttribute('reason') and res.firstChild.getAttribute('reason') == 'ok':
            if res.firstChild.hasAttribute('status'):
                self.status = res.firstChild.getAttribute('status')
            return
        else:
            print res.toprettyxml()
    def handle_response_step_over(self, res):
        """handle <response command=step_over> tag
        <response command="step_over" reason="ok" status="break" transaction_id="1 "/>"""
        if res.firstChild.hasAttribute('reason') and res.firstChild.getAttribute('reason') == 'ok':
            if res.firstChild.hasAttribute('status'):
                self.status = res.firstChild.getAttribute('status')
            return
        else:
            print res.toprettyxml()
    def handle_response_step_into(self, res):
        """handle <response command=step_into> tag
        <response command="step_into" reason="ok" status="break" transaction_id="1 "/>"""
        if res.firstChild.hasAttribute('reason') and res.firstChild.getAttribute('reason') == 'ok':
            if res.firstChild.hasAttribute('status'):
                self.status = res.firstChild.getAttribute('status')
            return
        else:
            print res.toprettyxml()
    def handle_response_run(self, res):
        """handle <response command=run> tag
        <response command="step_over" reason="ok" status="break" transaction_id="1 "/>"""
        if res.firstChild.hasAttribute('status'):
            self.status = res.firstChild.getAttribute('status')
            return
    def handle_response_breakpoint_set(self, res):
        """handle <response command=breakpoint_set> tag
        <responsponse command="breakpoint_set" id="110180001" transaction_id="1"/>"""
        if res.firstChild.hasAttribute('id'):
            tid = int(res.firstChild.getAttribute('transaction_id'))
            bno = self.bptsetlst[tid]
            del self.bptsetlst[tid]
            self.breakpt.setid(bno, str(res.firstChild.getAttribute('id')))
            #try:
            #except:
            #    print "can't find bptsetlst tid=", tid
            #    pass
    def handle_response_eval(self, res):
        """handle <response command=eval> tag """
        self.ui.windows['watch'].write_xml_childs(res)
    def handle_response_property_get(self, res):
        """handle <response command=property_get> tag """
        self.ui.windows['watch'].write_xml_childs(res)
    def handle_response_context_get(self, res):
        """handle <response command=context_get> tag """
        self.ui.windows['watch'].write_xml_childs(res)
    def handle_response_feature_set(self, res):
        """handle <response command=feature_set> tag """
        self.ui.windows['watch'].write_xml_childs(res)
    def handle_response_status(self, res):
        self.status = res.firstChild.getAttribute('status')
    def handle_response_default(self, res):
        """handle <response command=context_get> tag """
        print res.toprettyxml()
    #
    #
    #################################################################################################################

    #################################################################################################################
    # debugger command functions
    #
    #     usage:
    #
    #     dbg = Debugger()                    # create Debugger Object
    #     dbg.run()                                 # run() method initialize windows, debugger connection and send breakpoints, ...
    #     dbg.run()                                 # run() method sends 'run -i ...' message
    #     dbg.command('step_into')    # sends 'step_into' message
    #     dbg.stop()                                # stop debugger
    #

    def command(self, cmd, arg1 = '', arg2 = ''):
        """ general command sender (receive response too) """
        if self.running == 0:
            print "Not connected\n"
            return
        msgid = self.send_command(cmd, arg1, arg2)
        self.recv()
        return msgid

    def run(self):
        """ start debugger or continue """
        if self.protocol.isconnected():
            self.command('run')
            self.update()
        else:
            self.clear()
            if not self.protocol.accept():
                print textwrap.dedent('''\
                        Unable to connect to debug server. Things to check:
                            - you refreshed the page during the 5 second
                              period
                            - you have the xdebug extension installed (apt-get
                              install php5-xdebug on ubuntu)
                            - you set the XDEBUG_SESSION_START cookie
                            - "xdebug.remote_enable = 1" is in php.ini (not
                              enabled by default)
                        If you have any questions, look at
                            http://tech.blog.box.net/2007/06/20/how-to-debug-php-with-vim-and-xdebug-on-linux/
                        ''')
                return False
            self.ui.debug_mode()
            self.running = 1

            self.recv(1)

            # set max data to get with eval results
            self.command('feature_set', '-n max_children -v ' + self.max_children)
            self.command('feature_set', '-n max_data -v ' + self.max_data)
            self.command('feature_set', '-n max_depth -v ' + self.max_depth)

            self.command('step_into')

            flag = 0
            for bno in self.breakpt.list():
                msgid = self.send_command('breakpoint_set',
                 '-t line -f ' + self.breakpt.getfile(bno) + ' -n ' + str(self.breakpt.getline(bno)) + ' -s enabled',
                 self.breakpt.getexp(bno))
                self.bptsetlst[msgid] = bno
                flag = 1
            if flag:
                self.recv()

            self.ui.go_srcview()

    def quit(self):
        self.ui.normal_mode()
        self.clear()
        #vim.command('MiniBufExplorer')

    def stop(self):
        self.clear()

    def up(self):
        if self.curstack > 0:
            self.curstack -= 1
            self.ui.windows['stack'].highlight_stack(self.curstack)
            self.ui.set_srcview(self.stacks[self.curstack]['file'], self.stacks[self.curstack]['line'])

    def down(self):
        if self.curstack < self.laststack:
            self.curstack += 1
            self.ui.windows['stack'].highlight_stack(self.curstack)
            self.ui.set_srcview(self.stacks[self.curstack]['file'], self.stacks[self.curstack]['line'])

    def mark(self, exp = ''):
        (row, rol) = vim.current.window.cursor
        file = vim.current.buffer.name

        bno = self.breakpt.find(file, row)
        if bno != None:
            id = self.breakpt.getid(bno)
            self.breakpt.remove(bno)
            vim.command('sign unplace ' + str(bno))
            if self.protocol.isconnected():
                self.send_command('breakpoint_remove', '-d ' + str(id))
                self.recv()
        else:
            bno = self.breakpt.add(file, row, exp)
            vim.command('sign place ' + str(bno) + ' name=breakpt line=' + str(row) + ' file=' + file)
            if self.protocol.isconnected():
                msgid = self.send_command('breakpoint_set', \
                                                                    '-t line -f ' + self.breakpt.getfile(bno) + ' -n ' + str(self.breakpt.getline(bno)), \
                                                                    self.breakpt.getexp(bno))
                self.bptsetlst[msgid] = bno
                self.recv()

    def watch_input(self, mode, arg = ''):
        self.ui.windows['watch'].input(mode, arg)

    def property_get(self, name = ''):
        if name == '':
            name = vim.eval('expand("<cword>")')
        self.ui.windows['watch'].write('--> property_get: '+name)
        self.command('property_get', '-n '+name)
        
    def watch_execute(self):
        """ execute command in watch window """
        (cmd, expr) = self.ui.windows['watch'].get_command()
        if cmd == 'exec':
            self.command('exec', '', expr)
            print cmd, '--', expr
        elif cmd == 'eval':
            self.command('eval', '', expr)
            print cmd, '--', expr
        elif cmd == 'property_get':
            self.command('property_get', '-d %d -n %s' % (self.curstack,    expr))
            print cmd, '-n ', expr
        elif cmd == 'context_get':
            self.command('context_get', ('-d %d' % self.curstack))
            print cmd
        else:
            print "no commands", cmd, expr

    def update(self):
        self.command('status')
        if self.status == 'break':
            self.command('stack_get')
        elif self.status == 'stopping':
            print 'Program has finished running. (exiting)'
            vim.command(':!')
            self.quit()
        elif self.status == 'starting':
            print 'Execution hasn\'t started yet...'
        elif self.status == 'running':
            print 'Code is running right now...'
        elif self.status == 'stopped':
            print 'We\'ve been disconnected! (exiting)'
            vim.command(':!')
            self.quit()

    #
    #
    #################################################################################################################


########NEW FILE########
__FILENAME__ = errors

error_msg = { \
    # 000 Command parsing errors
    0   : """no error""",                                                                                                                                                      \
    1   : """parse error in command""",                                                                                                                                        \
    2   : """duplicate arguments in command""",                                                                                                                                \
    3   : """invalid options (ie, missing a required option)""",                                                                                                               \
    4   : """Unimplemented command""",                                                                                                                                         \
    5   : """Command not available (Is used for async commands. For instance if the engine is in state "run" than only "break" and "status" are available). """,               \
    # 100 : File related errors
    100 : """can not open file (as a reply to a "source" command if the requested source file can't be opened)""",                                                             \
    101 : """stream redirect failed """,                                                                                                                                       \
    # 200 Breakpoint, or code flow errors
    200 : """breakpoint could not be set (for some reason the breakpoint could not be set due to problems registering it)""",                                                  \
    201 : """breakpoint type not supported (for example I don't support 'watch' yet and thus return this error)""",                                                            \
    202 : """invalid breakpoint (the IDE tried to set a breakpoint on a line that does not exist in the file (ie "line 0" or lines past the end of the file)""",               \
    203 : """no code on breakpoint line (the IDE tried to set a breakpoint on a line which does not have any executable code. The debugger engine is NOT required to """     + \
          """return this type if it is impossible to determine if there is code on a given location. (For example, in the PHP debugger backend this will only be """         + \
          """returned in some special cases where the current scope falls into the scope of the breakpoint to be set)).""",                                                    \
    204 : """Invalid breakpoint state (using an unsupported breakpoint state was attempted)""",                                                                                                                                                      \
    205 : """No such breakpoint (used in breakpoint_get etc. to show that there is no breakpoint with the given ID)""",                                                        \
    206 : """Error evaluating code (use from eval() (or perhaps property_get for a full name get))""",                                                                         \
    207 : """Invalid expression (the expression used for a non-eval() was invalid) """,                                                                                        \
    # 300 Data errors
    300 : """Can not get property (when the requested property to get did not exist, this is NOT used for an existing but uninitialized property, which just gets the """    + \
          """type "uninitialised" (See: PreferredTypeNames)).""",                                                                                                              \
    301 : """Stack depth invalid (the -d stack depth parameter did not exist (ie, there were less stack elements than the number requested) or the parameter was < 0)""",      \
    302 : """Context invalid (an non existing context was requested) """,                                                                                                      \
    # 900 Protocol errors
    900 : """Encoding not supported""",                                                                                                                                        \
    998 : """An internal exception in the debugger occurred""",                                                                                                                \
    999 : """Unknown error """                                                                                                                                                 \
}

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = new_debugger
import subprocess
import textwrap
import socket
import vim
import sys
import os
import imp

from ui import DebugUI
from dbgp import DBGP

def vim_init():
    '''put DBG specific keybindings here -- e.g F1, whatever'''
    vim.command('ca dbg Dbg')

def vim_quit():
    '''remove DBG specific keybindings'''
    vim.command('cuna dbg')

def get_vim(name, default, fn=str):
    if vim.eval('exists("%s")' % name) == '1':
        return vim.eval(name)
    return default

import types
class Registrar:
    def __init__(self, args=(), kwds=(), named=True):
        if named:
            self.reg = {}
        else:
            self.reg = []
        self.args = args
        self.kwds = kwds
        self.named = named

    def register(self, *args, **kwds):
        def meta(func):
            self.add(func, args, kwds)

        return meta

    def add(self, func, args, kwds):
        if self.named:
            self.reg[args[0]] = {'function':func, 'args':args[1:], 'kwds':kwds}
        else:
            self.reg.append({'function':func, 'args':args, 'kwds':kwds})
        return func

    def bind(self, inst):
        res = {}
        for key, value in self.reg.iteritems():
            value = value.copy()
            res[key] = value
            if callable(value['function']):
                value['function'] = types.MethodType(value['function'], inst, inst.__class__)
        return res

    __call__ = register

class CmdRegistrar(Registrar):
    def add(self, func, args, kwds):
        lead = kwds.get('lead', '')

        disabled_mappings = False
        if vim.eval("exists('g:vim_debug_disable_mappings')") != "0":
            disabled_mappings = vim.eval("g:vim_debug_disable_mappings") != "0"

        if lead and not disabled_mappings:
            vim.command('map <Leader>%s :Dbg %s<cr>' % (lead, args[0]))
        dct = {'function':func, 'options':kwds}
        for name in args:
            self.reg[name] = dct

class Debugger:
    ''' This is the main debugger class... '''
    options = {'port':9000, 'max_children':32, 'max_data':'1024', 'minbufexpl':0, 'max_depth':1}
    def __init__(self):
        self.started = False
        self.watching = {}
        self._type = None

    def init_vim(self):
        self.ui = DebugUI()
        self.settings = {}
        for k,v in self.options.iteritems():
            self.settings[k] = get_vim(k, v, type(v))
        vim_init()

    def start_url(self, url):
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += 'XDEBUG_SESSION_START=vim_phpdebug'
        self._type = 'php'
        # only linux and mac supported atm
        command = 'xdg-open' if sys.platform.startswith('linux') else 'open'
        try:
            subprocess.Popen((command, url), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            print 'failed to start a browser. aborting debug session'
            return
        return self.start()

    def start_py(self, fname):
        if os.name == 'nt':
            _,PYDBGP,_ = imp.find_module('dbgp')
            PYDBGP = PYDBGP + '/../EGG-INFO/scripts/pydbgp.py'
            subprocess.Popen(('python.exe',PYDBGP, '-d', 'localhost:9000', fname), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.Popen(('pydbgp.py', '-d', 'localhost:9000', fname), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self._type = 'python'
        return self.start()

    def start(self):
        ## self.breaks = BreakPointManager()
        self.started = True
        self.bend = DBGP(self.settings, self.ui.windows['log'].write, self._type)
        for key, value in self.handle.bind(self).iteritems():
            if callable(value['function']):
                fn = value['function']
            else:
                tmp = self
                for item in value['function'].split('.'):
                    tmp = getattr(tmp, item)
                fn = tmp
            self.bend.addCommandHandler(key, fn)
        self.bend.addCommandHandler('<stream>', self.ui.windows['output'].add)
        if not self.bend.connect():
            print textwrap.dedent('''\
                Unable to connect to debug server. Things to check:
                    - you refreshed the page during the 5 second
                        period
                    - you have the xdebug extension installed (apt-get
                        install php5-xdebug on ubuntu)
                    - you set the XDEBUG_SESSION_START cookie
                    - "xdebug.remote_enable = 1" is in php.ini (not
                        enabled by default)
                If you have any questions, look at
                    http://tech.blog.box.net/2007/06/20/how-to-debug-php-with-vim-and-xdebug-on-linux/
                ''')
            return False
        self.ui.startup()

        self.bend.get_packets(1)

        self.bend.command('feature_set', 'n', 'max_children', 'v', self.settings['max_children'])
        self.bend.command('feature_set', 'n', 'max_data', 'v', self.settings['max_data'])
        self.bend.command('feature_set', 'n', 'max_depth', 'v', self.settings['max_depth'])
        self.bend.command('stdout', 'c', '1')
        self.bend.command('stderr', 'c', '1')
        for name in ('max_children', 'max_data', 'max_depth'):
            self.bend.command('feature_set', 'n', name, 'v', self.settings[name], suppress=True)

        self.bend.command('step_into')
        self.bend.command('context_get')
        self.bend.command('stack_get')
        self.bend.command('status')

        self.ui.go_srcview()

    def set_status(self, status):
        self.status = status
        # self.party

    ''' setup + register vim commands '''
    cmd = CmdRegistrar()

    cmd('over', help='step over next function call', lead='o')('step_over')
    cmd('into', help='step into next function call', lead='i')('step_into')
    cmd('out', help='step out of current function call', lead='t')('step_out')
    cmd('run', help='continue execution until a breakpoint is reached or the program ends', lead='r')('run')

    @cmd('eval', help='eval some code', plain=True)
    def eval_(self, code):
        self.bend.command('eval', data=code)
        self.bend.command('context_get')

    @cmd('quit', 'stop', 'exit', help='exit the debugger')
    def quit(self):
        self.bend.close()
        self.ui.close()
        vim_quit()

    @cmd('up', help='go up the stack', lead='u')
    def up(self):
        self.ui.stack_up()

    @cmd('down', help='go down the stack', lead='d')
    def down(self):
        self.ui.stack_down()

    @cmd('watch', help='execute watch functions', lead='w')
    def watch(self):
        lines = self.ui.windows['watch'].expressions.buffer
        self.watching = {}
        for i, line in enumerate(lines[1:]):
            if not line.strip():continue
            # self.ui.windows['log'].write('evalling:' + line)
            tid = self.bend.command('eval', data=line, suppress=True)
            self.watching[tid] = i+1
        self.bend.get_packets()

    @cmd('break', help='set a breakpoint', lead='b')
    def break_(self):
        (row, col) = vim.current.window.cursor
        file = os.path.abspath(vim.current.buffer.name)
        if not os.path.exists(file):
            print 'Not in a file'
            return
        bid = self.ui.break_at(file, row)
        if bid == -1:
            tid = self.bend.cid + 1
            self.ui.queue_break(tid, file, row)
            self.bend.command('breakpoint_set', 't', 'line', 'f', 'file://' + file, 'n', row, data='')
        else:
            tid = self.bend.cid + 1
            self.ui.queue_break_remove(tid, bid)
            self.bend.command('breakpoint_remove', 'd', bid)

    @cmd('here', help='continue execution until the cursor (tmp breakpoint)', lead='h')
    def here(self):
        (row, col) = vim.current.window.cursor
        file = os.path.abspath(vim.current.buffer.name)
        if not os.path.exists(file):
            print 'Not in a file'
            return
        tid = self.bend.cid + 1
        # self.ui.queue_break(tid, file, row)
        self.bend.command('breakpoint_set', 't', 'line', 'r', '1', 'f', 'file://' + file, 'n', row, data='')
        self.bend.command('run')

    def commands(self):
        self._commands = self.cmd.bind(self)
        return self._commands

    handle = Registrar()
    @handle('stack_get')
    def _stack_get(self, node):
        line = self.ui.windows['stack'].refresh(node)
        self.ui.set_srcview(line[2], line[3])

    @handle('breakpoint_set')
    def _breakpoint_set(self, node):
        self.ui.set_break(int(node.getAttribute('transaction_id')), node.getAttribute('id'))
        self.ui.go_srcview()

    @handle('breakpoint_remove')
    def _breakpoint_remove(self, node):
        self.ui.clear_break(int(node.getAttribute('transaction_id')))
        self.ui.go_srcview()

    def _status(self, node):
        if node.getAttribute('reason') == 'ok':
            self.set_status(node.getAttribute('status'))

    def _change(self, node):
        if node.getAttribute('reason') == 'ok':
            self.set_status(node.getAttribute('status'))
            if self.status != 'stopping':
                try:
                    self.bend.command('context_get')
                    self.bend.command('stack_get')
                except (EOFError, socket.error):
                    self.disable()
            else:
                self.disable()

    def disable(self):
        print 'Execution has ended; connection closed. type :Dbg quit to exit debugger'
        self.ui.unhighlight()
        for cmd in self._commands.keys():
            if cmd not in ('quit', 'close'):
                self._commands.pop(cmd)

    @handle('<init>')
    def _init(self, node):
        file = node.getAttribute('fileuri')
        self.ui.set_srcview(file, 1)

    handle('status')(_status)
    handle('stdout')(_status)
    handle('stderr')(_status)
    handle('step_into')(_change)
    handle('step_out')(_change)
    handle('step_over')(_change)
    handle('run')(_change)

    def _log(self, node):
        self.ui.windows['log'].write(node.toprettyxml(indent='   '))
        pass # print node

    @handle('eval')
    def _eval(self, node):
        id = int(node.getAttribute('transaction_id'))
        if id in self.watching:
            self.ui.windows['watch'].set_result(self.watching.pop(id), node)
            self.ui.windows['watch'].expressions.focus()

    handle('property_get')(_log)
    handle('property_set')(_log)

    @handle('context_get')
    def _context_get(self, node):
        self.ui.windows['scope'].refresh(node)

    handle('feature_set')(_log)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = protocol

import socket
import base64

class DbgProtocol:
    """ DBGp Procotol class """
    def __init__(self, port = 9000):
        socket.setdefaulttimeout(5)
        self.port = port
        self.sock = None
        self.isconned = False
    def isconnected(self):
        return self.isconned
    def accept(self):
        print 'waiting for a new connection on port '+str(self.port)+' for 5 seconds...'
        self.isconned = False
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serv.bind(('', self.port))
            serv.listen(5)
            (self.sock, address) = serv.accept()
        except socket.timeout:
            serv.close()
            self.close()
            # self.stop()
            print 'timeout'
            return False

        print 'connection from ', address
        self.isconned = True
        serv.close()
        return True
    def close(self):
        if self.sock != None:
            self.sock.close()
            self.sock = None
        self.isconned = 0
    def recv_length(self):
        #print '* recv len'
        length = ''
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            #print '    GET(',c, ':', ord(c), ') : length=', len(c)
            if c == '\0':
                return int(length)
            if c.isdigit():
                length = length + c
    def recv_null(self):
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            if c == '\0':
                return
    def recv_body(self, to_recv):
        body = ''
        while to_recv > 0:
            buf = self.sock.recv(to_recv)
            if buf == '':
                self.close()
                raise EOFError, 'Socket Closed'
            to_recv -= len(buf)
            body = body + buf
        return body
    def recv_msg(self):
        length = self.recv_length()
        body = self.recv_body(length)
        self.recv_null()
        return body
    def send_msg(self, cmd):
        self.sock.send(cmd + '\0')


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = stack


class StackMan:
    def __init__(self):
        self.stack = []

    def update(self, node):
        stack = node.getElementsByTagName('stack')
        self.stack = list(map(item.getAttribute, ('level', 'where', 'filename', 'lineno')) for item in stack)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = subwindows
from window import VimWindow
import errors
import base64

class StackWindow(VimWindow):
    '''Keeps track of the current execution stack'''
    name = 'STACK'
    dtext = '[[Execution Stack - most recent call first]]'
    def __init__(self, name = None):
        VimWindow.__init__(self, name)
        self.at = 0

    def refresh(self, node):
        self.at = 0
        stack = node.getElementsByTagName('stack')
        self.stack = list(map(item.getAttribute, ('level', 'where', 'filename', 'lineno')) for item in stack)
        self.clear()
        tpl = '%-2s %-15s %s:%s' 
        lines = list(tpl % tuple(item) for item in self.stack)
        self.writelines(lines)
        self.highlight(0)
        return self.stack[0]

    def on_create(self):
        self.command('highlight CurStack term=reverse ctermfg=White ctermbg=Red gui=reverse')
        self.highlight(0)

    def highlight(self, num):
        self.command('syntax clear')
        self.command('syntax region CurStack start="^%d " end="$"' % num)

class LogWindow(VimWindow):
    '''I don't actually know what this does...'''
    name = 'LOG'
    dtext = '[[Logs all traffic]]'

    def on_create(self):
        self.command('set nowrap fdm=marker fmr={{{,}}} fdl=0')

class OutputWindow(VimWindow):
    '''Logs the stdout + stderr'''
    name = 'STDOUT_STDERR'
    dtext = '[[Stdout and Stderr are copied here for your convenience]]\n'

    def on_create(self):
        self.command('set wrap fdm=marker fmr={{{,}}} fdl=0')
        self.command('setlocal wfw')
        self.last = 'stdout'

    def add(self, type, text):
        # TODO: highlight stderr
        if type != self.last:
            self.last = type
            if type == 'stderr':
                self.write('[[STDERR]]')
            else:
                self.write('[[STDOUT]]')
        lines = text.split('\n')
        self.buffer[-1] += lines[0]
        for line in lines[1:]:
            self.buffer.append(line)
        self.command('normal G')

class WatchWindow:
    ''' window for watch expressions '''

    def __init__(self):
        self.expressions = VimWindow('WATCH')
        self.expressions.dtext = '[[Type expressions here]]'
        self.results = VimWindow('RESULTS')
        self.results.dtext = '[[type \w for them to be evaluated]]'

    def create(self, where=None):
        self.expressions.create('leftabove new')
        self.results.create('vertical belowright new')

    def destroy(self):
        self.expressions.destroy()
        self.results.destroy()

    def set_result(self, line, node):
        l = len(self.results.buffer)
        for a in range(len(self.results.buffer)-1, line):
            self.results.buffer.append('')
        errors = node.getElementsByTagName('error')
        if len(errors):
            res = 'ERROR: ' + str(get_child_text(errors[0], 'message'))
        else:
            prop = node.getElementsByTagName('property')[0]
            res = str(get_text(prop))
            if not res:
                res = str(get_child_text(prop, 'value'))
        self.results.buffer[line] = res

def get_text(node):
    if not hasattr(node.firstChild, 'data'):
        return ''
    data = node.firstChild.data
    if node.getAttribute('encoding') == 'base64':
        return base64.decodestring(data)
    return data

def get_child_text(node, child_tag):
    tags = node.getElementsByTagName(child_tag)
    if not tags:
        return ''
    return get_text(tags[0])

class ScopeWindow(VimWindow):
    ''' lists the current scope (context) '''

    name = 'SCOPE'
    dtext = '[[Current scope variables...]]'

    def refresh(self, node):
        self.clear()
        for child in node.getElementsByTagName('property'):
            name = child.getAttribute('fullname')
            type = child.getAttribute('type')
            children = child.getAttribute('children')
            if not name:
                text = get_child_text(child, 'value')
                name = get_child_text(child, 'fullname')
            else:
                if not child.firstChild:
                    text = ''
                elif hasattr(child.firstChild, 'data'):
                    text = child.firstChild.data
                else:
                    text = ''
                if child.hasAttribute('encoding') and child.getAttribute('encoding') == 'base64':
                    text = base64.decodestring(text)
            self.write('%-20s = %-10s /* type: %s */' % (name, text, type))

help_text = '''\
[ Function Keys ]                 |                      
  <F1>   resize                   | [ Normal Mode ]      
  <F2>   step into                |   ,e  eval           
  <F3>   step over                |                      
  <F4>   step out                 |                      
  <F5>   run                      | [ Command Mode ]     
  <F6>   quit debugging           | :Bp toggle breakpoint
                                  | :Up stack up         
  <F11>  get all context          | :Dn stack down       
  <F12>  get property at cursor   |                      
'''

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = ui
import os
import vim

from subwindows import WatchWindow, StackWindow, ScopeWindow, OutputWindow, LogWindow

class DebugUI:
    """ DEBUGUI class """
    def __init__(self, minibufexpl = 0):
        """ initialize object """
        self.windows = {
            'watch':WatchWindow(),
            'stack':StackWindow(),
            'scope':ScopeWindow(),
            'output':OutputWindow(),
            'log':LogWindow(),
            # 'status':StatusWindow()
        }
        self.mode     = 0 # normal mode
        self.file     = None
        self.line     = None
        self.winbuf   = {}
        self.breaks   = {}
        self.waiting  = {}
        self.toremove = {}
        self.cursign  = None
        self.sessfile = "/tmp/debugger_vim_saved_session." + str(os.getpid())
        self.minibufexpl = minibufexpl

    def startup(self):
        """ change mode to debug """
        if self.mode == 1: # is debug mode ?
            return
        self.mode = 1
        if self.minibufexpl == 1:
            vim.command('CMiniBufExplorer')         # close minibufexplorer if it is open
        # save session
        vim.command('mksession! ' + self.sessfile)
        for i in range(1, len(vim.windows)+1):
            vim.command(str(i)+'wincmd w')
            self.winbuf[i] = vim.eval('bufnr("%")') # save buffer number, mksession does not do job perfectly
                                                    # when buffer is not saved at all.

        vim.command('silent topleft new')           # create srcview window (winnr=1)
        for i in range(2, len(vim.windows)+1):
            vim.command(str(i)+'wincmd w')
            vim.command('hide')
        self.create()
        vim.command('1wincmd w') # goto srcview window(nr=1, top-left)
        self.cursign = '1'

        self.set_highlight()

    def close(self):
        """ restore mode to normal """
        if self.mode == 0: # is normal mode ?
            return

        vim.command('sign unplace 1')
        vim.command('sign unplace 2')
        for bid in self.breaks.keys():
            file, line, tid = self.breaks.pop(bid)
            vim.command('sign unplace %d file=%s' % (tid, file))

        # destory all created windows
        self.destroy()

        # restore session
        vim.command('source ' + self.sessfile)
        os.system('rm -f ' + self.sessfile)

        self.set_highlight()

        self.winbuf.clear()
        self.file = None
        self.line = None
        self.mode = 0
        self.cursign = None

        if self.minibufexpl == 1:
            vim.command('MiniBufExplorer')                 # close minibufexplorer if it is open

    def create(self):
        """ create windows """
        self.windows['output'].create('vertical belowright new')
        self.windows['scope'].create('aboveleft new')
        self.windows['log'].create('aboveleft new')
        self.windows['stack'].create('aboveleft new')
        self.windows['watch'].create('aboveleft new')
        width = self.windows['output'].width + self.windows['scope'].width
        self.windows['output'].command('vertical res %d' % (width/2))
        self.windows['watch'].results.command('vertical res %d' % (width/4))

    def set_highlight(self):
        """ set vim highlight of debugger sign """
        vim.command("highlight DbgCurrent term=reverse ctermfg=White ctermbg=Red gui=reverse")
        vim.command("highlight DbgBreakPt term=reverse ctermfg=White ctermbg=Green gui=reverse")

    def unhighlight(self):
        self.windows['stack'].clear()
        self.windows['stack'].write('\n\n!!!!!---- Debugging has ended. Type `:dbg quit` to exit ----!!!!!\n\n')
        self.windows['stack'].command('syntax clear')
        self.windows['stack'].command('syntax region CurStack start="^!!!!!---- " end="$"')
        self.go_srcview()
        vim.command('sign unplace ' + self.cursign)

    def stack_up(self):
        stack = self.windows['stack']
        if stack.at > 0:
            stack.at -= 1
            stack.highlight(stack.at)
            item = stack.stack[stack.at]
            self.set_srcview(item[2], item[3])

    def stack_down(self):
        stack = self.windows['stack']
        if stack.at < len(stack.stack)-1:
            stack.at += 1
            stack.highlight(stack.at)
            item = stack.stack[stack.at]
            self.set_srcview(item[2], item[3])

    def queue_break(self, tid, file, line):
        self.waiting[tid] = file, line

    def queue_break_remove(self, tid, bid):
        self.toremove[tid] = bid

    def set_break(self, tid, bid):
        if tid in self.waiting:
            file, line = self.waiting[tid]
            self.breaks[bid] = file, line, tid
            vim.command('sign place %d name=breakpt line=%d file=%s' % (tid, line, file))
        else:
            pass # print 'failed to set breakpoint... %d : %s' % (tid, self.waiting)

    def clear_break(self, tid):
        bid = self.toremove.pop(tid)
        if bid in self.breaks:
            file, line, tid = self.breaks.pop(bid)
            vim.command('sign unplace %d file=%s' % (tid, file))
        else:
            print 'failed to remove', bid

    def break_at(self, file, line):
        # self.windows['log'].write('looking for %s line %s in %s' % (file, line, self.breaks))
        for bid, value in self.breaks.iteritems():
            if value[:2] == (file, line):
                return bid
        return -1

    def destroy(self):
        """ destroy windows """
        for window in self.windows.values():
            window.destroy()

    def go_srcview(self):
        vim.command('1wincmd w')

    def next_sign(self):
        if self.cursign == '1':
            return '2'
        else:
            return '1'

    def set_srcview(self, file, line):
        """ set srcview windows to file:line and replace current sign """
        if os.name == 'nt':
            file = os.path.normpath(file)
            file = file[6:]
        else:
            pass

        if file.startswith('file:'):
            file = file[len('file:'):]
            if file.startswith('///'):
                file = file[2:]

        if file == self.file and self.line == line:
            return

        nextsign = self.next_sign()

        if file != self.file:
            self.file = file
            self.go_srcview()
            vim.command('silent edit! ' + file)

        cmd = 'sign place %s name=current line=%s file=%s' % (nextsign, line, file)

        vim.command(str(cmd))
        vim.command('sign unplace ' + self.cursign)

        vim.command('sign jump ' + nextsign + ' file='+file)
        #vim.command('normal z.')

        self.line = line
        self.cursign = nextsign

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = window
import vim

class VimWindow:
    """ wrapper class of window of vim """
    name = 'DEBUG_WINDOW'
    dtext = ''
    def __init__(self, name = None, special=True, height=0):
        """ initialize """
        if name is not None:
            self.name = name
        self.buffer = None
        self.height = height
        self.firstwrite = 1
        self.special = special

    def isprepared(self):
        """ check window is OK """
        if self.buffer == None or len(dir(self.buffer)) == 0 or self.getwinnr() == -1:
            return 0
        return 1
    def prepare(self):
        """ check window is OK, if not then create """
        if not self.isprepared():
            self.create()
    def on_create(self):
        pass
    def getwinnr(self):
        return int(vim.eval("bufwinnr('"+self.name+"')"))

    def write(self, msg):
        """ append last """
        self.writelines(msg.splitlines())

    def writelines(self, lines):
        # print 'writing', lines
        lines = list(str(item) for item in lines)
        self.prepare()
        # if self.firstwrite == 1:
        #     self.firstwrite = 0
        #     self.buffer[:] = lines
        # else:
        self.buffer.append(lines)
        self.command('normal G')
        #self.window.cursor = (len(self.buffer), 1)

    def create(self, method = 'new'):
        """ create window """
        vim.command('silent ' + method + ' ' + self.name)
        vim.command("setlocal buftype=nofile")
        vim.command("setlocal nobuflisted")
        # vim.command("setlocal nomodifiable")
        self.buffer = vim.current.buffer
        self.buffer[:] = [self.dtext]
        self.buffer.append('')
        if self.height != 0:
            vim.command('res %d' % self.height)
        self.width = int( vim.eval("winwidth(0)") )
        self.height = int( vim.eval("winheight(0)") )
        self.on_create()

    def destroy(self):
        """ destroy window """
        if self.buffer == None or len(dir(self.buffer)) == 0:
            return
        self.command('bd %d' % self.buffer.number)
        self.firstwrite = 1

    def clear(self):
        """ clean all datas in buffer """
        self.prepare()
        self.buffer[:] = [self.dtext]
        self.firstwrite = 1

    def command(self, cmd):
        """ go to my window & execute command """
        self.prepare()
        winnr = self.getwinnr()
        if winnr != int(vim.eval("winnr()")):
            vim.command(str(winnr) + 'wincmd w')
        vim.command(cmd)

    def focus(self):
        self.prepare()
        winnr = self.getwinnr()
        if winnr != int(vim.eval("winnr()")):
            vim.command(str(winnr) + 'wincmd w')

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = _commands
import sys
import vim
import traceback
from debugger import Debugger

def debugger_init(debug = 0):
    global debugger

    # get needed vim variables

    # port that the engine will connect on
    port = int(vim.eval('debuggerPort'))
    if port == 0:
        port = 9000

    # the max_depth variable to set in the engine
    max_children = vim.eval('debuggerMaxChildren')
    if max_children == '':
        max_children = '32'

    max_data = vim.eval('debuggerMaxData')
    if max_data == '':
        max_data = '1024'

    max_depth = vim.eval('debuggerMaxDepth')
    if max_depth == '':
        max_depth = '1'

    minibufexpl = int(vim.eval('debuggerMiniBufExpl'))
    if minibufexpl == 0:
        minibufexpl = 0

    debugger = Debugger(port, max_children, max_data, max_depth, minibufexpl, debug)

import shlex

_commands = {}
def debugger_cmd(plain):
    if ' ' in plain:
        name, plain = plain.split(' ', 1)
        args = shlex.split(plain)
    else:
        name = plain
        plain = ''
        args = []
    if name not in _commands:
        print '[usage:] dbg command [options]'
        for command in _commands:
            print ' - ', command, '      ::', _commands[command]['help']
        return
    cmd = _commands[name]
    if cmd['plain']:
        return cmd['cmd'](plain)
    else:
        cmd['cmd'](*args)

def cmd(name, help='', plain=False):
    def decor(fn):
        _commands[name] = {'cmd':fn, 'help':help, 'plain':plain}
        return fn
    return decor

def debugger_command(msg, arg1 = '', arg2 = ''):
    try:
        debugger.command(msg, arg1, arg2)
        debugger.update()
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

@cmd('run', 'run until the next break point (or the end)')
def debugger_run():
    try:
        debugger.run()
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

# @cmd('watch', 'watch a value')
def debugger_watch_input(cmd, arg = ''):
    try:
        if arg == '<cword>':
            arg = vim.eval('expand("<cword>")')
        debugger.watch_input(cmd, arg)
    except:
        debugger.ui.windows['trace'].write( sys.exc_info() )
        debugger.ui.windows['trace'].write( "".join(traceback.format_tb(sys.exc_info()[2])) )
        debugger.stop()
        print 'Connection closed, stop debugging'

@cmd('ctx', 'refresh the context (scope)')
def debugger_context():
    try:
        debugger.command('context_get')
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging'

@cmd('e', 'eval some text', plain=True)
def debugger_eval(stuff):
    debugger.command("eval", '', stuff)

def debugger_property(name = ''):
    try:
        debugger.property_get()
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

def debugger_mark(exp = ''):
    try:
        debugger.mark(exp)
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

def debugger_up():
    try:
        debugger.up()
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

def debugger_down():
    try:
        debugger.down()
    except:
        debugger.ui.windows['trace'].write(sys.exc_info())
        debugger.ui.windows['trace'].write("".join(traceback.format_tb( sys.exc_info()[2])))
        debugger.stop()
        print 'Connection closed, stop debugging', sys.exc_info()

def debugger_quit():
    global debugger
    debugger.quit()

mode = 0
def debugger_resize():
    global mode
    mode = mode + 1
    if mode >= 3:
        mode = 0

    if mode == 0:
        vim.command("wincmd =")
    elif mode == 1:
        vim.command("wincmd |")
    if mode == 2:
        vim.command("wincmd _")

# vim: et sw=4 sts=4

########NEW FILE########
