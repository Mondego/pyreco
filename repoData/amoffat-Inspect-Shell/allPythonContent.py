__FILENAME__ = inspect_shell
#===============================================================================
# Copyright (C) 2011 by Andrew Moffat
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#===============================================================================


import sys
import StringIO
import contextlib
import struct
import traceback
import inspect
import threading
import random
import socket
import json



import rlcompleter
try: import readline
except ImportError: readline = None







interface = "localhost"
default_port = 1234
reconnect_tries = 3
version = "1.0"



# actions that the shell can make to the server
COMMAND = "\x00"
AUTO_COMPLETE = "\x01"



class PortInUseException(Exception): pass
class Disconnected(Exception): pass




# this is used when we "exec" the code sent from the shell.  it essentially
# captures all stdout and returns it as a string.  we use a contextmanager
# to make absolutely sure that the real stdout is reassigned to sys.stdout
# no matter what happens 
@contextlib.contextmanager
def stdoutIO():
    stdout = StringIO.StringIO()
    old_out = sys.stdout
    sys.stdout = stdout
    yield stdout
    sys.stdout = old_out







def run_shell_server(f_globals, interface, port):     
    auto_complete = rlcompleter.Completer(namespace=f_globals)
           
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try: sock.bind((interface, port))
    except Exception, e:
        if isinstance(e, socket.error) and getattr(e, "errno", False) == 98:
            raise PortInUseException("%d in use" % port)
        else: raise
        
    sock.listen(100)   
    
    
    
    def run_repl(sock):
        
        def do_reply(data):
            data = json.dumps(data)
            out = struct.pack("!i", len(data)) + data
            sock.sendall(out)

        while True:
            
            # read the length of the request
            request_length = 5
            data = []
            while request_length:
                try: chunk = sock.recv(request_length)
                except: return
                
                # socket is done sending, but we're clearly not done
                # receiving.  this would be an error, but let's not
                # disrupt our process, so just return
                if not chunk: return
                
                data.append(chunk)
                request_length -= len(chunk)
            data = "".join(data)
            
            # debugging
            #print repr(data)
            
            action, request_length = struct.unpack("!ci", data)
            
            
            # read the request and load it with json
            request = []
            while request_length:
                chunk = sock.recv(request_length)
                request.append(chunk)
                request_length -= len(chunk)
            data = json.loads("".join(request))
            
            
            if action == COMMAND:
                with stdoutIO() as stdout:
                    # lets us exec AND eval
                    try: exec compile(data, "<dummy>", "single") in f_globals, f_globals
                    except: print traceback.format_exc()
    
                out = stdout.getvalue()
                try: do_reply(out)
                except: return
            
            elif action == AUTO_COMPLETE:
                ac = auto_complete.complete(*data)
                try: do_reply(ac)
                except: return
            
    
    # our main loop for dispatching new connections
    while True:
        new_conn, addr = sock.accept()
        ct = threading.Thread(target=run_repl, args=(new_conn,))
        ct.daemon = True
        ct.start()
        




class Shell(object):
    prompt_template = "{interface}:{port:d}> "
    banner_template = "\n>> Inspect Shell v{version}\n>> https://github.com/amoffat/Inspect-Shell\n"

    def __init__(self, interface, port):
        self.interface = interface
        self.port = port
        
    def reconnect(self):
        self.sock = socket.socket()
        self.sock.connect((self.interface, self.port))
        self.sock.settimeout(30)
        
        
    def send(self, command, data):
        sent = False
        for i in xrange(reconnect_tries):
            try: reply = self._do_request(command, data)
            except Disconnected: self.reconnect()
            else: return reply
            
        raise Disconnected, "and tried %d times to reconnect" % reconnect_tries
        
        
    def _do_request(self, action, data):
        data = json.dumps(data)
        data = action + struct.pack("!i", len(data)) + data
        
        try: self.sock.sendall(data)
        except: raise Disconnected
        
        
        # read the length of the reply
        reply_length = 4
        data = []
        while reply_length:
            chunk = self.sock.recv(reply_length)
            if not chunk: raise Disconnected
            
            data.append(chunk)
            reply_length -= len(chunk)
        data = "".join(data)
        reply_length = struct.unpack("!i", data)[0]
        
        
        # read the reply
        reply = []
        while reply_length:
            chunk = self.sock.recv(reply_length)
            if not chunk: raise Disconnected
            reply.append(chunk)
            reply_length -= len(chunk)
        
        return json.loads("".join(reply))
        
        
    def run(self):
        print Shell.banner_template.format(version=version)
        prompt = Shell.prompt_template.format(
            interface=self.interface,
            port=self.port
        )
        
        try: self.reconnect()
        except socket.error:
            print "** ERROR connecting to %s:%d, are you sure you added \
\"import inspect_shell\" to the top of your script? **\n" % (self.interface, self.port)
           
        while True:
            try: line = raw_input(prompt)
            except (EOFError, KeyboardInterrupt):
                print('')
                return
            
            reply = self.send(COMMAND, line)         
            print reply
            









# running from commandline, open a shell
if __name__ == "__main__":    
    try: port = int(sys.argv[1])
    except: port = default_port
    
    shell = Shell(interface, port)
    
    if readline:
        import os
        import atexit
        
        histfile = os.path.join(os.path.expanduser("~"), ".inspect_shell_history")
        try: readline.read_history_file(histfile)
        except IOError: pass
        atexit.register(readline.write_history_file, histfile)
        
        # set up auto-completion
        def auto_completer(*args): return shell.send(AUTO_COMPLETE, args)        
        readline.set_completer(auto_completer)
        readline.parse_and_bind("tab: complete")
        
    shell.run()
    
    
# it's being imported, run the shell server
else:
    caller = inspect.stack()[1][0]
    f_globals = caller.f_globals
    port = f_globals.get("inspect_shell_port", default_port)
    
    st = threading.Thread(target=run_shell_server, args=(f_globals, interface, port))
    st.daemon = True
    st.start()
    
########NEW FILE########
