__FILENAME__ = connection
import json
import socket
import time
from threading import Thread


class UnknownBreakpoint(Exception):
    pass


class ConnectionNotBootstrapped(Exception):
    pass


class Breakpoint(object):
    def __init__(self, bpnum, filename, line, enabled=True, temporary=False, funcname=None):
        self.bpnum = bpnum
        self.filename = filename
        self.line = line
        self.enabled = enabled
        self.temporary = temporary
        self.funcname = funcname

    def __unicode__(self):
        return u'%s:%s' % (self.filename, self.line)


def command_buffer(debugger):
    "Buffer input from a socket, yielding complete command packets."
    remainder = ''
    while True:
        new_buffer = debugger.socket.recv(1024)

        if not new_buffer:
            # If recv() returns None, the socket has closed
            break
        else:
            # print "CLIENT NEW BUFFER: %s >%s<" % (len(new_buffer), new_buffer[:50])
            if new_buffer[-1] == debugger.ETX:
                terminator = new_buffer[-1]
                full_buffer = remainder + new_buffer[:-1]
            else:
                terminator = None
                full_buffer = remainder + new_buffer

            messages = full_buffer.split(debugger.ETX)
            if terminator is None:
                remainder = messages.pop()
            else:
                remainder = ''
            for message in messages:
                # print "READ %s bytes" % len(message)
                event, data = json.loads(message)

                if hasattr(debugger, 'on_%s' % event):
                    getattr(debugger, 'on_%s' % event)(**data)
                else:
                    print "Unknown server event:", event

    # print "FINISH PROCESSING CLIENT COMMAND BUFFER"


class Debugger(object):
    "A networked connection to a debugger session"

    ETX = '\x03'

    def __init__(self, host, port, proc=None):
        self.host = host
        self.port = port

        self.proc = proc

        # By default, no view is known.
        # It must be set after
        self.view = None

    def start(self):
        "Start the debugger session"
        connected = False
        while not connected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                connected = True
            except socket.error, e:
                print "Waiting for connection...", e
                time.sleep(1.0)

        t = Thread(target=command_buffer, args=(self,))
        t.daemon = True
        t.start()

    def stop(self):
        "Shut down the debugger session"
        if self.proc is not None:
            # If this is a local debugger session, kill the child process.
            self.output('quit')

        self.socket.shutdown(socket.SHUT_WR)

        if self.proc is not None:
            # If this is a local debugger session, wait for
            # the child process to die.
            # print "Waiting for child process to die..."
            self.proc.wait()

    def output(self, event, **data):
        "Send a single command packet to the debugger"
        try:
            # print "OUTPUT %s byte message" % len(json.dumps((event, data)) + Debugger.ETX)
            self.socket.sendall(json.dumps((event, data)) + Debugger.ETX)
        except socket.error, e:
            print "CLIENT ERROR", e
        except AttributeError, e:
            print "No client yet", e

    #################################################################
    # Utilities for retrieving current breakpoints.
    #################################################################

    def breakpoint(self, bp):
        """Retrieve a specific breakpoint object.

        Accepts either a breakpoint number, or a (filename, line) tuple
        """
        try:
            if isinstance(bp, tuple):
                filename, line = bp
                return self.bp_index[filename][line]
            else:
                return self.bp_list[bp]
        except AttributeError:
            raise ConnectionNotBootstrapped()
        except KeyError:
            raise UnknownBreakpoint()

    def breakpoints(self, filename):
        try:
            return self.bp_index.get(filename, {})
        except AttributeError:
            raise ConnectionNotBootstrapped()

    #################################################################
    # Commands that can be passed to the debugger
    #################################################################

    def create_breakpoint(self, filename, line, temporary=False):
        "Create a new, enabled breakpoint at the specified line of the given file"
        self.output('break', filename=filename, line=line, temporary=temporary)

    def enable_breakpoint(self, breakpoint):
        "Enable an existing breakpoint"
        self.output('enable', bpnum=breakpoint.bpnum)

    def disable_breakpoint(self, breakpoint):
        "Disable an existing breakpoint"
        self.output('disable', bpnum=breakpoint.bpnum)

    def ignore_breakpoint(self, breakpoint, count):
        """Ignore an existing breakpoint for `count` iterations

        Use a count of 0 to restore the breakpoint.
        """
        self.output('ignore', bpnum=breakpoint.bpnum, count=count)

    def clear_breakpoint(self, breakpoint):
        "Clear an existing breakpoint"
        self.output('clear', bpnum=breakpoint.bpnum)

    def do_run(self):
        "Set the debugger running until the next breakpoint"
        self.output('continue')

    def do_step(self):
        "Step through one stack frame"
        self.output('step')

    def do_next(self):
        "Go to the next line in the current stack frame"
        self.output('next')

    def do_return(self):
        "Return to the previous stack frame"
        self.output('return')

    #################################################################
    # Handlers for events raised by the debugger
    #################################################################

    def on_bootstrap(self, breakpoints):
        self.bp_index = {}
        self.bp_list = [None]
        for bp_data in breakpoints:
            self.on_breakpoint_create(**bp_data)

    def on_breakpoint_create(self, **bp_data):
        bp = Breakpoint(**bp_data)
        self.bp_index.setdefault(bp.filename, {}).setdefault(bp.line, bp)
        self.bp_list.append(bp)
        if bp.enabled:
            self.view.on_breakpoint_enable(bp=bp)
        else:
            self.view.on_breakpoint_disable(bp=bp)

    def on_breakpoint_enable(self, bpnum):
        bp = self.bp_list[bpnum]
        bp.enabled = True
        self.view.on_breakpoint_enable(bp=bp)

    def on_breakpoint_disable(self, bpnum):
        bp = self.bp_list[bpnum]
        bp.enabled = False
        self.view.on_breakpoint_disable(bp=bp)

    def on_breakpoint_ignore(self, bpnum, count):
        bp = self.bp_list[bpnum]
        bp.ignore = count
        self.view.on_breakpoint_ignore(bp=bp, count=count)

    def on_breakpoint_clear(self, bpnum):
        bp = self.bp_list[bpnum]
        self.view.on_breakpoint_clear(bp=bp)

    def on_stack(self, stack):
        self.stack = stack
        self.view.on_stack(stack=stack)

    def on_restart(self):
        self.view.on_restart()

    def on_call(self, args):
        self.view.on_call(args)

    def on_return(self, retval):
        self.view.on_return(retval)

    def on_line(self, filename, line):
        self.view.on_line(filename, line)

    def on_exception(self, name, value):
        self.view.on_exception(name=name, value=value)

    def on_postmortem(self):
        self.view.on_postmortem()

    def on_info(self, message):
        self.view.on_info(message=message)

    def on_warning(self, message):
        self.view.on_warning(message=message)

    def on_error(self, message):
        self.view.on_error(message=message)

########NEW FILE########
__FILENAME__ = main
'''
This is the main entry point for the Bugjar GUI.
'''
from Tkinter import *

import argparse
import os
import subprocess
import time

from bugjar import VERSION
from bugjar.view import MainWindow
from bugjar.connection import Debugger
from bugjar.net import run as net_run


def jar_run(debugger):
    # Set up the root Tk context
    root = Tk()

    # Construct a window debugging the nominated program
    view = MainWindow(root, debugger)

    # Run the main loop
    try:
        view.mainloop()
    except KeyboardInterrupt:
        view.on_quit()


def local():
    "Run a Bugjar session on a local process"
    parser = argparse.ArgumentParser(
        description='Debug a python script with a graphical interface.',
        version=VERSION
    )

    parser.add_argument(
        "-p", "--port",
        metavar='PORT',
        help="Port number to use for debugger communications (default=3742)",
        action="store",
        type=int,
        default=3742,
        dest="port"
    )

    parser.add_argument(
        'filename',
        metavar='script.py',
        help='The script to debug.'
    )
    parser.add_argument(
        'args', nargs=argparse.REMAINDER,
        help='Arguments to pass to the script you are debugging.'
    )

    options = parser.parse_args()

    # Start the program to be debugged
    proc = subprocess.Popen(
        ["bugjar-net", options.filename] + options.args,
        stdin=None,
        stdout=None,
        stderr=None,
        shell=False,
        bufsize=1,
        close_fds='posix' in sys.builtin_module_names
    )
    # Pause, ever so briefly, so that the net can be established.
    time.sleep(0.1)

    # Create a connection to the debugger instance
    debugger = Debugger('localhost', options.port, proc=proc)

    # Run the debugger
    jar_run(debugger)


def jar():
    "Connect a Bugjar GUI to a remote headless session."
    parser = argparse.ArgumentParser(
        description='Connect a Bugjar GUI session to a headless debugger.',
        version=VERSION
    )

    parser.add_argument(
        "-H", "--host",
        metavar='HOSTNAME',
        help="Hostname/IP address where the headless debugger is running (default=localhost)",
        action="store",
        default="localhost",
        dest="hostname")
    parser.add_argument(
        "-p", "--port",
        metavar='PORT',
        help="Port number where where the headless debugger is running (default=3742)",
        action="store",
        type=int,
        default=3742,
        dest="port"
    )

    options = parser.parse_args()

    # Create a connection to the remote debugger instance
    debugger = Debugger(options.hostname, options.port, proc=None)

    # Run the debugger
    jar_run(debugger)


def net():
    "Create a headless Bugjar session."
    parser = argparse.ArgumentParser(
        description='Run a script inside a headless Bugjar session.',
        version=VERSION
    )

    parser.add_argument(
        "-H", "--host",
        metavar='HOSTNAME',
        help="Hostname/IP address where the headless debugger will listen for connections (default=0.0.0.0)",
        action="store",
        default="0.0.0.0",
        dest="hostname")
    parser.add_argument(
        "-p", "--port",
        metavar='PORT',
        help="Port number where the headless debugger will listen for connections (default=3742)",
        action="store",
        type=int,
        default=3742,
        dest="port"
    )
    parser.add_argument(
        'filename',
        metavar='script.py',
        help='The script to debug.'
    )
    parser.add_argument(
        'args', nargs=argparse.REMAINDER,
        help='Arguments to pass to the script you are debugging.'
    )

    options = parser.parse_args()

    # Convert the filename provided on the command line into a canonical form
    filename = os.path.abspath(options.filename)
    filename = os.path.normcase(filename)

    # Run the debugger
    net_run(options.hostname, options.port, filename, *options.args)

if __name__ == '__main__':
    local()

########NEW FILE########
__FILENAME__ = net
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""A Python debugger that takes commands via a socket.

This code is substantially derived from the code for PDB,
the builtin debugger. The code was copied from the source
code for Python 2.7.5.

The original PDB code is:
    Copyright © 2001-2013 Python Software Foundation; All Rights Reserved

License terms for the original PDB code can be found here:
    http://docs.python.org/2/license.html
"""

import bdb
import linecache
import json
import os
import re
import socket
import sys
from threading import Thread
import traceback

try:
    from Queue import Queue
except ImportError:
    from queue import Queue  # python 3.x


class Restart(Exception):
    """Causes a debugger to be restarted for the debugged python program."""
    pass


class ClientClose(Exception):
    """Causes a debugger to wait for a new debugger client to connect."""
    pass


__all__ = ["Debugger"]


def find_function(funcname, filename):
    cre = re.compile(r'def\s+%s\s*[(]' % re.escape(funcname))
    try:
        fp = open(filename)
    except IOError:
        return None
    # consumer of this info expects the first line to be 1
    line = 1
    answer = None
    while 1:
        line = fp.readline()
        if line == '':
            break
        if cre.match(line):
            answer = funcname, filename, line
            break
        line = line + 1
    fp.close()
    return answer


def command_buffer(debugger):
    "Buffer input from a socket, yielding complete command packets."
    remainder = ''
    while True:
        new_buffer = debugger.client.recv(1024)

        if not new_buffer:
            # If recv() returns None, the socket has closed
            break
        else:
            # print "SERVER NEW BUFFER: %s >%s<" % (len(new_buffer), new_buffer[:50])
            if new_buffer[-1] == debugger.ETX:
                terminator = new_buffer[-1]
                full_buffer = remainder + new_buffer[:-1]
            else:
                terminator = None
                full_buffer = remainder + new_buffer

            messages = full_buffer.split(debugger.ETX)
            if terminator is None:
                remainder = messages.pop()
            else:
                remainder = ''
            for message in messages:
                # print "READ %s bytes" % len(message)
                command, args = json.loads(message)
                try:
                    debugger.commands.put(json.loads(message))
                except ValueError:
                    print "Invalid command: %s" % message

    # print "FINISH PROCESSING SERVER COMMAND BUFFER"
    debugger.commands.put(('close', {}))


class Debugger(bdb.Bdb):
    NOT_STARTED = 0
    STARTING = 1
    STARTED = 2

    ETX = '\x03'

    def __init__(self, socket, host, port, skip=None):
        bdb.Bdb.__init__(self, skip=skip)

        self._run_state = Debugger.NOT_STARTED
        self.mainpyfile = ''
        self.socket = socket
        self.host = host
        self.port = port
        self.client = None
        self.command_thread = None
        self.commands = None

    def output(self, event, **data):
        try:
            # print "OUTPUT %s byte %s message" % (len(json.dumps((event, data)) + Debugger.ETX), event)
            # print json.dumps((event, data))
            self.client.sendall(json.dumps((event, data)) + Debugger.ETX)
        except socket.error, e:
            pass
            # print "CLIENT ERROR", e
        except AttributeError:
            pass
            # print "No client yet"

    def output_stack(self):
        "Output the current stack"
        # If this is a normal operational stack frame,
        # the top two frames are BDB and the Bugjar frame
        # that is executing the program.
        # If this is an exception, there are 2 extra frames
        # from the Bugjar net.
        # All these frames can be ignored.
        if self.stack[1][0].f_code.co_filename == '<string>':
            str_index = 2
        elif self.stack[3][0].f_code.co_filename == '<string>':
            str_index = 4

        stack_data = [
            (
                line_no,
                {
                    'filename': frame.f_code.co_filename,
                    'locals': dict((k, repr(v)) for k, v in frame.f_locals.items()),
                    'globals': dict((k, repr(v)) for k, v in frame.f_globals.items()),
                    'builtins': dict((k, repr(v)) for k, v in frame.f_builtins.items()),
                    'restricted': frame.f_restricted,
                    'lasti': repr(frame.f_lasti),
                    'exc_type': repr(frame.f_exc_type),
                    'exc_value': repr(frame.f_exc_value),
                    'exc_traceback': repr(frame.f_exc_traceback),
                    'current': frame is self.curframe,
                }
            )
            for frame, line_no in self.stack[str_index:]
        ]
        self.output('stack', stack=stack_data)

    def forget(self):
        self.line = None
        self.stack = []
        self.curindex = 0
        self.curframe = None

    def setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]
        # The f_locals dictionary is updated from the actual frame
        # locals whenever the .f_locals accessor is called, so we
        # cache it here to ensure that modifications are not overwritten.
        self.curframe_locals = self.curframe.f_locals

    # Override Bdb methods

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self._run_state == Debugger.STARTING:
            return
        if self.stop_here(frame):
            self.output('call', args=argument_list)
            self.interaction(frame, None)

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        if self._run_state == Debugger.STARTING:
            if (self.mainpyfile != self.canonic(frame.f_code.co_filename) or frame.f_lineno <= 0):
                return
            self._run_state = Debugger.STARTED
        self.output('line', filename=self.canonic(frame.f_code.co_filename), line=frame.f_lineno)
        self.interaction(frame, None)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        if self._run_state == Debugger.STARTING:
            return
        frame.f_locals['__return__'] = return_value
        self.output('return', retval=repr(return_value))
        self.interaction(frame, None)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        if self._run_state == Debugger.STARTING:
            return
        exc_type, exc_value, exc_traceback = exc_info
        frame.f_locals['__exception__'] = exc_type, exc_value
        if isinstance(exc_type, basestring):
            exc_type_name = exc_type
        else:
            exc_type_name = exc_type.__name__
        self.output('exception', name=exc_type_name, value=repr(exc_value))
        self.interaction(frame, exc_traceback)

    # General interaction function

    def interaction(self, frame, tb):
        self.setup(frame, tb)
        self.output_stack()
        while 1:
            try:
                # print "Server Wait for input..."
                command, args = self.commands.get(block=True)

                # print "Server command:", command, args
                if hasattr(self, 'do_%s' % command):
                    try:
                        resume = getattr(self, 'do_%s' % command)(**args)
                        if resume:
                            # print "resume running"
                            break
                    except (ClientClose, Restart):
                        # Reraise any control exceptions
                        raise
                    except Exception, e:
                        # print "Unknown problem with command %s: %s" % (command, e)
                        self.output('error', message='Unknown problem with command %s: %s' % (command, e))
                else:
                    # print "Unknown command %s" % command
                    self.output('error', message='Unknown command: %s' % command)

            except (socket.error, AttributeError, ClientClose):
                # Problem with connection; look for new client
                print "Listening on %s:%s for a bugjar client" % (self.host, self.port)
                client, addr = self.socket.accept()

                print "Got connection from", client.getpeername()
                self.client = client

                # Start the command queue
                self.commands = Queue()
                self.command_thread = Thread(target=command_buffer, args=(self,))
                self.command_thread.daemon = True
                self.command_thread.start()

                # print "Bootstrap the state of a new connection..."
                self.output(
                    'bootstrap',
                    breakpoints=[
                        {
                            'bpnum': bp.number,
                            'filename': bp.file,
                            'line': bp.line,
                            'temporary': bp.temporary,
                            'enabled': bp.enabled,
                            'funcname': bp.funcname
                        }
                        for bp in bdb.Breakpoint.bpbynumber[1:]
                    ]
                )

                # print "Describe initial stack..."
                self.output_stack()

        # print "END INTERACTION LOOP"
        self.forget()

    # Debugger Commands

    def do_break(self, filename, line, temporary=False):
        # Check for reasonable breakpoint
        if self.is_executable_line(filename, line):
            # now set the break point
            err = self.set_break(filename, line, temporary, None, None)
            if err:
                self.output('error', message=err)
            else:
                bp = self.get_breaks(filename, line)[-1]
                self.output(
                    'breakpoint_create',
                    bpnum=bp.number,
                    filename=bp.file,
                    line=bp.line,
                    temporary=bp.temporary,
                    funcname=bp.funcname
                )
        else:
            self.output('error', message="%s:%s is not executable" % (filename, line))

    def is_executable_line(self, filename, line):
        """Check whether specified line is executable.

        Return True if it is, False if not (e.g. a docstring, comment, blank
        line or EOF).
        """
        # this method should be callable before starting debugging, so default
        # to "no globals" if there is no current frame
        globs = self.curframe.f_globals if hasattr(self, 'curframe') else None
        code = linecache.getline(filename, line, globs)
        if not code:
            return False
        code = code.strip()
        # Don't allow setting breakpoint at a blank line
        if (not code or (code[0] == '#') or (code[:3] == '"""') or code[:3] == "'''"):
            return False
        return True

    def do_enable(self, bpnum):
        if not (0 <= bpnum < len(bdb.Breakpoint.bpbynumber)):
            self.output('error', message='No breakpoint numbered %s' % bpnum)
        else:
            bp = bdb.Breakpoint.bpbynumber[bpnum]
            bp.enable()
            self.output('breakpoint_enable', bpnum=bpnum)

    def do_disable(self, bpnum):
        bpnum = int(bpnum)
        if not (0 <= bpnum < len(bdb.Breakpoint.bpbynumber)):
            self.output('error', message='No breakpoint numbered %s' % bpnum)
        else:
            bp = bdb.Breakpoint.bpbynumber[bpnum]
            bp.disable()
            self.output('breakpoint_disable', bpnum=bpnum)

    # def do_condition(self, arg):
    #     # arg is breakpoint number and condition
    #     args = arg.split(' ', 1)
    #     try:
    #         bpnum = int(args[0].strip())
    #     except ValueError:
    #         # something went wrong
    #         self.output('error', message='Breakpoint index %r is not a number' % args[0])
    #         return
    #     try:
    #         cond = args[1]
    #     except:
    #         cond = None
    #     try:
    #         bp = bdb.Breakpoint.bpbynumber[bpnum]
    #     except IndexError:
    #         self.output('error', message='Breakpoint index %r is not valid' % args[0])
    #         return
    #     if bp:
    #         bp.cond = cond
    #         if not cond:
    #             self.output('msg', message='Breakpoint %s is now unconditional' % bpnum)

    def do_ignore(self, bpnum, count):
        """arg is bp number followed by ignore count."""
        try:
            count = int(count)
        except ValueError:
            count = 0

        if not (0 <= bpnum < len(bdb.Breakpoint.bpbynumber)):
            self.output('error', message='No breakpoint numbered %s' % bpnum)
        else:
            bp = bdb.Breakpoint.bpbynumber[bpnum]
            bp.ignore = count
            if count > 0:
                self.output('breakpoint_ignore', bpnum=bpnum, count=count)
            else:
                self.output('breakpoint_enable', bpnum=bpnum)

    def do_clear(self, bpnum):
        bpnum = int(bpnum)
        if not (0 <= bpnum < len(bdb.Breakpoint.bpbynumber)):
            self.output('error', message='No breakpoint numbered %s' % bpnum)
        else:
            err = self.clear_bpbynumber(bpnum)
            if err:
                self.output('error', message=err)
            else:
                self.output('breakpoint_clear', bpnum=bpnum)

    # def do_up(self, arg):
    #     if self.curindex == 0:
    #         self.output('error', message='Already at oldest frame')
    #     else:
    #         self.curindex = self.curindex - 1
    #         self.curframe = self.stack[self.curindex][0]
    #         self.curframe_locals = self.curframe.f_locals
    #         self.output_stack()
    #         self.lineno = None

    # def do_down(self, arg):
    #     if self.curindex + 1 == len(self.stack):
    #         self.output('error', message='Alread at newest frame')
    #     else:
    #         self.curindex = self.curindex + 1
    #         self.curframe = self.stack[self.curindex][0]
    #         self.curframe_locals = self.curframe.f_locals
    #         self.output_stack()
    #         self.lineno = None

    # def do_until(self, arg):
    #     self.set_until(self.curframe)
    #     return 1

    def do_step(self):
        self.set_step()
        return 1

    def do_next(self):
        self.set_next(self.curframe)
        return 1

    def do_restart(self, **argv):
        """Restart program by raising an exception to be caught in the main
        debugger loop.  If arguments were given, set them in sys.argv."""
        if argv:
            argv0 = sys.argv[0:1]
            sys.argv = argv
            sys.argv[:0] = argv0
        raise Restart

    def do_return(self):
        self.set_return(self.curframe)
        return 1

    def do_continue(self):
        self.set_continue()
        return 1

    # def do_jump(self, arg):
    #     if self.curindex + 1 != len(self.stack):
    #         self.output('error', message='You can only jump within the bottom frame')
    #         return
    #     try:
    #         arg = int(arg)
    #     except ValueError:
    #         self.output('error', message="The 'jump' command requires a line number")
    #     else:
    #         try:
    #             # Do the jump, fix up our copy of the stack, and display the
    #             # new position
    #             self.curframe.f_lineno = arg
    #             self.stack[self.curindex] = self.stack[self.curindex][0], arg
    #             self.output_stack()
    #         except ValueError, e:
    #             self.output('error', message="Jump failed: %s" % e)

    # def do_debug(self, arg):
    #     sys.settrace(None)
    #     globals = self.curframe.f_globals
    #     locals = self.curframe_locals
    #     p = Debugger(...)
    #     p.prompt = "(%s) " % self.prompt.strip()
    #     self.output("ENTERING RECURSIVE DEBUGGER")
    #     sys.call_tracing(p.run, (arg, globals, locals))
    #     self.output("LEAVING RECURSIVE DEBUGGER")
    #     sys.settrace(self.trace_dispatch)
    #     self.lastcmd = p.lastcmd

    def do_quit(self):
        self._user_requested_quit = True
        self.set_quit()
        return 1

    def do_close(self):
        """Respond to a closed socket.

        This isn't actually a user comman,but it's something the command
        queue can generate in response to the socket closing; we handle
        it as a user command for the sake of elegance.
        """
        # print "Close down socket"
        self.client = None
        # print "Wait for command thread"
        self.command_thread.join()
        # print "Thread is dead"
        self.commands = None
        raise ClientClose

    # def do_args(self, arg):
    #     co = self.curframe.f_code
    #     locals = self.curframe_locals
    #     n = co.co_argcount
    #     if co.co_flags & 4:
    #         n = n + 1
    #     if co.co_flags & 8:
    #         n = n + 1
    #     for i in range(n):
    #         name = co.co_varnames[i]
    #         self.output('arg', name=locals.get(name, '*** undefined ***'))

    # def do_retval(self, arg):
    #     if '__return__' in self.curframe_locals:
    #         self.output('retval', value=self.curframe_locals['__return__'])
    #     else:
    #         self.output('error', message='Not yet returned!')

    # def _getval(self, arg):
    #     try:
    #         return eval(arg, self.curframe.f_globals,
    #                     self.curframe_locals)
    #     except:
    #         t, v = sys.exc_info()[:2]
    #         if isinstance(t, str):
    #             exc_type_name = t
    #         else:
    #             exc_type_name = t.__name__
    #         # self.output({'***', exc_type_name + ':', repr(v))
    #         raise

    # def do_print(self, arg):
    #     try:
    #         self.output(repr(self._getval(arg)))
    #     except:
    #         pass
    # do_p = do_print

    def _runscript(self, filename):
        # The script has to run in __main__ namespace (or imports from
        # __main__ will break).
        #
        # So we clear up the __main__ and set several special variables
        # (this gets rid of debugger's globals and cleans old variables on restarts).
        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update({
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": __builtins__,
        })

        # When bdb sets tracing, a number of call and line events happens
        # BEFORE debugger even reaches user's code (and the exact sequence of
        # events depends on python version). So we take special measures to
        # avoid stopping before we reach the main script (see user_line and
        # user_call for details).
        self._run_state = Debugger.STARTING
        self.mainpyfile = self.canonic(filename)
        self._user_requested_quit = False
        self.run('execfile(%r)' % filename)


def run(hostname, port, filename, *args):
    # Hide "debugger.py" from argument list
    sys.argv[0] = filename
    sys.argv[1:] = args

    # Replace debugger's dir with script's dir in front of module search path.
    sys.path[0] = os.path.dirname(filename)

    # Create a socket and listen on it for a client debugger
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    s.bind((hostname, port))
    s.listen(1)

    debugger = Debugger(s, hostname, port)

    while True:
        try:
            # print 'Start the script'
            debugger._runscript(filename)

            if debugger._user_requested_quit:
                # print 'user requested exit'
                break

            debugger.output('restart')
        except Restart:
            print "Restarting", filename, "with arguments:"
            print "\t" + " ".join(sys.argv[1:])
        except KeyboardInterrupt:
            print "Keyboard interrupt"
            debugger.client = None
            break
        except SystemExit:
            print "System exit"
            debugger.client = None
            break
        except socket.error:
            print "Controller client disappeared; can't recover"
            debugger.client = None
            break
        except:
            traceback.print_exc()
            debugger.output('postmortem')
            t = sys.exc_info()[2]
            debugger.interaction(None, t)

    if debugger.client:
        # print "closing connection"
        debugger.client.shutdown(socket.SHUT_WR)

########NEW FILE########
__FILENAME__ = view
"""A module containing a visual representation of the connection

This is the "View" of the MVC world.
"""
import os
from Tkinter import *
from tkFont import *
from ttk import *
import tkMessageBox
import tkFileDialog
import webbrowser

from bugjar import VERSION, NUM_VERSION
from bugjar.widgets import DebuggerCode, BreakpointView, StackView, InspectorView


def filename_normalizer(base_path):
    """Generate a fuction that will normalize a full path into a
    display name, by removing a common prefix.

    In most situations, this will be removing the current working
    directory.
    """
    def _normalizer(filename):
        if filename.startswith(base_path):
            return filename[len(base_path):]
        else:
            return filename
    return _normalizer


class MainWindow(object):
    def __init__(self, root, debugger):
        '''
        -----------------------------------------------------
        | main button toolbar                               |
        -----------------------------------------------------
        |       < ma | in content area >      |             |
        |            |                        |             |
        | File list  | File name              | Inspector   |
        | (stack/    | Code area              |             |
        | breakpnts) |                        |             |
        |            |                        |             |
        |            |                        |             |
        -----------------------------------------------------
        |     status bar area                               |
        -----------------------------------------------------

        '''

        # Obtain and expand the current working directory.
        base_path = os.path.abspath(os.getcwd())
        base_path = os.path.normcase(base_path) + '/'

        # Create a filename normalizer based on the CWD.
        self.filename_normalizer = filename_normalizer(base_path)

        self.debugger = debugger
        # Associate the debugger with this view.
        self.debugger.view = self

        # Root window
        self.root = root
        self.root.title('Bugjar')
        self.root.geometry('1024x768')

        # Prevent the menus from having the empty tearoff entry
        self.root.option_add('*tearOff', FALSE)
        # Catch the close button
        self.root.protocol("WM_DELETE_WINDOW", self.cmd_quit)
        # Catch the "quit" event.
        self.root.createcommand('exit', self.cmd_quit)

        # Setup the menu
        self._setup_menubar()

        # Set up the main content for the window.
        self._setup_button_toolbar()
        self._setup_main_content()
        self._setup_status_bar()

        # Now configure the weights for the root frame
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        debugger.start()

    ######################################################
    # Internal GUI layout methods.
    ######################################################

    def _setup_menubar(self):
        # Menubar
        self.menubar = Menu(self.root)

        # self.menu_Apple = Menu(self.menubar, name='Apple')
        # self.menubar.add_cascade(menu=self.menu_Apple)

        self.menu_file = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label='File')

        self.menu_program = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_program, label='Program')

        self.menu_help = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_help, label='Help')

        # self.menu_Apple.add_command(label='Test', command=self.cmd_dummy)

        # self.menu_file.add_command(label='New', command=self.cmd_dummy, accelerator="Command-N")
        self.menu_file.add_command(label='Open...', command=self.cmd_open_file, accelerator="Command-O")
        self.root.bind('<Command-o>', self.cmd_open_file)
        # self.menu_file.add_command(label='Close', command=self.cmd_dummy)

        self.menu_program.add_command(label='Run', command=self.cmd_run, accelerator="R")
        self.root.bind('<r>', self.cmd_run)
        self.menu_program.add_command(label='Step', command=self.cmd_step, accelerator="S")
        self.root.bind('<s>', self.cmd_step)
        self.menu_program.add_command(label='Next', command=self.cmd_next, accelerator="N")
        self.root.bind('<n>', self.cmd_next)
        self.menu_program.add_command(label='Return', command=self.cmd_return, accelerator="BackSpace")
        self.root.bind('<BackSpace>', self.cmd_return)

        self.menu_help.add_command(label='Open Documentation', command=self.cmd_bugjar_docs)
        self.menu_help.add_command(label='Open Bugjar project page', command=self.cmd_bugjar_page)
        self.menu_help.add_command(label='Open Bugjar on GitHub', command=self.cmd_bugjar_github)
        self.menu_help.add_command(label='Open BeeWare project page', command=self.cmd_beeware_page)

        # last step - configure the menubar
        self.root['menu'] = self.menubar

    def _setup_button_toolbar(self):
        '''
        The button toolbar runs as a horizontal area at the top of the GUI.
        It is a persistent GUI component
        '''

        # Main toolbar
        self.toolbar = Frame(self.root)
        self.toolbar.grid(column=0, row=0, sticky=(W, E))

        # Buttons on the toolbar
        self.run_button = Button(self.toolbar, text='Run', command=self.cmd_run)
        self.run_button.grid(column=0, row=0)

        self.step_button = Button(self.toolbar, text='Step', command=self.cmd_step)
        self.step_button.grid(column=1, row=0)

        self.next_button = Button(self.toolbar, text='Next', command=self.cmd_next)
        self.next_button.grid(column=2, row=0)

        self.return_button = Button(self.toolbar, text='Return', command=self.cmd_return)
        self.return_button.grid(column=3, row=0)

        self.toolbar.columnconfigure(0, weight=0)
        self.toolbar.rowconfigure(0, weight=0)

    def _setup_main_content(self):
        '''
        Sets up the main content area. It is a persistent GUI component
        '''

        # Main content area
        self.content = PanedWindow(self.root, orient=HORIZONTAL)
        self.content.grid(column=0, row=1, sticky=(N, S, E, W))

        # Create subregions of the content
        self._setup_file_lists()
        self._setup_code_area()
        self._setup_inspector()

        # Set up weights for the left frame's content
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.content.pane(0, weight=1)
        self.content.pane(1, weight=2)
        self.content.pane(2, weight=1)

    def _setup_file_lists(self):

        self.file_notebook = Notebook(self.content, padding=(0, 5, 0, 5))
        self.content.add(self.file_notebook)

        self._setup_stack_frame_list()
        self._setup_breakpoint_list()

    def _setup_stack_frame_list(self):
        self.stack_frame = Frame(self.content)
        self.stack_frame.grid(column=0, row=0, sticky=(N, S, E, W))
        self.file_notebook.add(self.stack_frame, text='Stack')

        self.stack = StackView(self.stack_frame, normalizer=self.filename_normalizer)
        self.stack.grid(column=0, row=0, sticky=(N, S, E, W))

        # # The tree's vertical scrollbar
        self.stack_scrollbar = Scrollbar(self.stack_frame, orient=VERTICAL)
        self.stack_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # # Tie the scrollbar to the text views, and the text views
        # # to each other.
        self.stack.config(yscrollcommand=self.stack_scrollbar.set)
        self.stack_scrollbar.config(command=self.stack.yview)

        # Setup weights for the "stack" tree
        self.stack_frame.columnconfigure(0, weight=1)
        self.stack_frame.columnconfigure(1, weight=0)
        self.stack_frame.rowconfigure(0, weight=1)

        # Handlers for GUI events
        self.stack.bind('<<TreeviewSelect>>', self.on_stack_frame_selected)

    def _setup_breakpoint_list(self):
        self.breakpoints_frame = Frame(self.content)
        self.breakpoints_frame.grid(column=0, row=0, sticky=(N, S, E, W))
        self.file_notebook.add(self.breakpoints_frame, text='Breakpoints')

        self.breakpoints = BreakpointView(self.breakpoints_frame, normalizer=self.filename_normalizer)
        self.breakpoints.grid(column=0, row=0, sticky=(N, S, E, W))

        # The tree's vertical scrollbar
        self.breakpoints_scrollbar = Scrollbar(self.breakpoints_frame, orient=VERTICAL)
        self.breakpoints_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # Tie the scrollbar to the text views, and the text views
        # to each other.
        self.breakpoints.config(yscrollcommand=self.breakpoints_scrollbar.set)
        self.breakpoints_scrollbar.config(command=self.breakpoints.yview)

        # Setup weights for the "breakpoint list" tree
        self.breakpoints_frame.columnconfigure(0, weight=1)
        self.breakpoints_frame.columnconfigure(1, weight=0)
        self.breakpoints_frame.rowconfigure(0, weight=1)

        # Handlers for GUI events
        self.breakpoints.tag_bind('breakpoint', '<Double-Button-1>', self.on_breakpoint_double_clicked)
        self.breakpoints.tag_bind('breakpoint', '<<TreeviewSelect>>', self.on_breakpoint_selected)
        self.breakpoints.tag_bind('file', '<<TreeviewSelect>>', self.on_breakpoint_file_selected)

    def _setup_code_area(self):
        self.code_frame = Frame(self.content)
        self.code_frame.grid(column=1, row=0, sticky=(N, S, E, W))

        # Label for current file
        self.current_file = StringVar()
        self.current_file_label = Label(self.code_frame, textvariable=self.current_file)
        self.current_file_label.grid(column=0, row=0, sticky=(W, E))

        # Code display area
        self.code = DebuggerCode(self.code_frame, debugger=self.debugger)
        self.code.grid(column=0, row=1, sticky=(N, S, E, W))

        # Set up weights for the code frame's content
        self.code_frame.columnconfigure(0, weight=1)
        self.code_frame.rowconfigure(0, weight=0)
        self.code_frame.rowconfigure(1, weight=1)

        self.content.add(self.code_frame)

    def _setup_inspector(self):
        self.inspector_frame = Frame(self.content)
        self.inspector_frame.grid(column=2, row=0, sticky=(N, S, E, W))

        self.inspector = InspectorView(self.inspector_frame)
        self.inspector.grid(column=0, row=0, sticky=(N, S, E, W))

        # The tree's vertical scrollbar
        self.inspector_scrollbar = Scrollbar(self.inspector_frame, orient=VERTICAL)
        self.inspector_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # Tie the scrollbar to the text views, and the text views
        # to each other.
        self.inspector.config(yscrollcommand=self.inspector_scrollbar.set)
        self.inspector_scrollbar.config(command=self.inspector.yview)

        # Setup weights for the "breakpoint list" tree
        self.inspector_frame.columnconfigure(0, weight=1)
        self.inspector_frame.columnconfigure(1, weight=0)
        self.inspector_frame.rowconfigure(0, weight=1)

        self.content.add(self.inspector_frame)

    def _setup_status_bar(self):
        # Status bar
        self.statusbar = Frame(self.root)
        self.statusbar.grid(column=0, row=2, sticky=(W, E))

        # Current status
        self.run_status = StringVar()
        self.run_status_label = Label(self.statusbar, textvariable=self.run_status)
        self.run_status_label.grid(column=0, row=0, sticky=(W, E))
        self.run_status.set('Not running')

        # Main window resize handle
        self.grip = Sizegrip(self.statusbar)
        self.grip.grid(column=1, row=0, sticky=(S, E))

        # Set up weights for status bar frame
        self.statusbar.columnconfigure(0, weight=1)
        self.statusbar.columnconfigure(1, weight=0)
        self.statusbar.rowconfigure(0, weight=0)

    ######################################################
    # Utility methods for controlling content
    ######################################################

    def show_file(self, filename, line=None, breakpoints=None):
        """Show the content of the nominated file.

        If specified, line is the current line number to highlight. If the
        line isn't currently visible, the window will be scrolled until it is.

        breakpoints is a list of line numbers that have current breakpoints.

        If refresh is true, the file will be reloaded and redrawn.
        """
        # Set the filename label for the current file
        self.current_file.set(self.filename_normalizer(filename))

        # Update the code view; this means changing the displayed file
        # if necessary, and updating the current line.
        if filename != self.code.filename:
            self.code.filename = filename
            for bp in self.debugger.breakpoints(filename).values():
                if bp.enabled:
                    self.code.enable_breakpoint(bp.line)
                else:
                    self.code.disable_breakpoint(bp.line)

        self.code.line = line

    ######################################################
    # TK Main loop
    ######################################################

    def mainloop(self):
        self.root.mainloop()

    ######################################################
    # TK Command handlers
    ######################################################

    def cmd_quit(self):
        "Quit the debugger"
        self.debugger.stop()
        self.root.quit()

    def cmd_run(self, event=None):
        "Run until the next breakpoint, or end of execution"
        self.debugger.do_run()

    def cmd_step(self, event=None):
        "Step into the next line of code"
        self.debugger.do_step()

    def cmd_next(self, event=None):
        "Run the next line of code in the current frame"
        self.debugger.do_next()

    def cmd_return(self, event=None):
        "Return to the previous frame"
        self.debugger.do_return()

    def cmd_open_file(self, event=None):
        "Open a file in the breakpoint pane"
        filename = tkFileDialog.askopenfilename(initialdir=os.path.abspath(os.getcwd()))

        if filename:
            # Convert to canonical form
            filename = os.path.abspath(filename)
            filename = os.path.normcase(filename)

            # Show the file contents
            self.code.filename = filename

            # Ensure the file appears on the breakpoint list
            self.breakpoints.insert_filename(filename)

            # Show the breakpoint panel
            self.file_notebook.select(self.breakpoints_frame)

            # ... select the new filename
            self.breakpoints.selection_set(filename)

            # .. and clear any currently selected item on the stack tree
            self.stack.selection_remove(self.stack.selection())

    def cmd_bugjar_page(self):
        "Show the Bugjar project page"
        webbrowser.open_new('http://pybee.org/bugjar')

    def cmd_bugjar_github(self):
        "Show the Bugjar GitHub repo"
        webbrowser.open_new('http://github.com/pybee/bugjar')

    def cmd_bugjar_docs(self):
        "Show the Bugjar documentation"
        # If this is a formal release, show the docs for that
        # version. otherwise, just show the head docs.
        if len(NUM_VERSION) == 3:
            webbrowser.open_new('http://bugjar.readthedocs.org/en/v%s/' % VERSION)
        else:
            webbrowser.open_new('http://bugjar.readthedocs.org/')

    def cmd_beeware_page(self):
        "Show the BeeWare project page"
        webbrowser.open_new('http://pybee.org/')

    ######################################################
    # Handlers for GUI actions
    ######################################################

    def on_stack_frame_selected(self, event):
        "When a stack frame is selected, highlight the file and line"
        if event.widget.selection():
            _, index = event.widget.selection()[0].split(':')
            line, frame = self.debugger.stack[int(index)]

            # Display the file in the code view
            self.show_file(filename=frame['filename'], line=line)

            # Display the contents of the selected frame in the inspector
            self.inspector.show_frame(frame)

            # Clear any currently selected item on the breakpoint tree
            self.breakpoints.selection_remove(self.breakpoints.selection())

    def on_breakpoint_selected(self, event):
        "When a breakpoint on the tree has been selected, show the breakpoint"
        if event.widget.selection():
            parts = event.widget.focus().split(':')
            bp = self.debugger.breakpoint((parts[0], int(parts[1])))
            self.show_file(filename=bp.filename, line=bp.line)

            # Clear any currently selected item on the stack tree
            self.stack.selection_remove(self.stack.selection())

    def on_breakpoint_file_selected(self, event):
        "When a file is selected on the breakpoint tree, show the file"
        if event.widget.selection():
            filename = event.widget.focus()
            self.show_file(filename=filename)

            # Clear any currently selected item on the stack tree
            self.stack.selection_remove(self.stack.selection())

    def on_breakpoint_double_clicked(self, event):
        "When a breakpoint on the tree is double clicked, toggle it's status"
        if event.widget.selection():
            parts = event.widget.focus().split(':')
            bp = self.debugger.breakpoint((parts[0], int(parts[1])))
            if bp.enabled:
                self.debugger.disable_breakpoint(bp)
            else:
                self.debugger.enable_breakpoint(bp)

            # Clear any currently selected item on the stack tree
            self.stack.selection_remove(self.stack.selection())

    ######################################################
    # Handlers for debugger responses
    ######################################################

    def on_stack(self, stack):
        "A report of a new stack"
        # Make sure the stack frame list is displayed
        self.file_notebook.select(self.stack_frame)

        # Update the stack list
        self.stack.update_stack(stack)

        if len(stack) > 0:
            # Update the display of the current file
            line = stack[-1][0]
            filename = stack[-1][1]['filename']
            self.show_file(filename=filename, line=line)

            # Select the current stack frame in the frame list
            self.stack.selection_set('frame:%s' % (len(stack) - 1))
        else:
            # No current frame (probably end of execution),
            # so clear the current line marker
            self.code.line = None

    def on_line(self, filename, line):
        "A single line of code has been executed"
        self.run_status.set('Line (%s:%s)' % (filename, line))

    def on_call(self, args):
        "A callable has been invoked"
        self.run_status.set('Call: %s' % args)

    def on_return(self, retval):
        "A callable has returned"
        self.run_status.set('Return: %s' % retval)

    def on_exception(self, name, value):
        "An exception has been raised"
        self.run_status.set('Exception: %s - %s' % (name, value))
        tkMessageBox.showwarning(message='%s: %s' % (name, value))

    def on_postmortem(self):
        "An exception has been raised"
        self.run_status.set('Post mortem mode')
        tkMessageBox.showerror(message='Entering post mortem mode. Step/Next will restart')

    def on_restart(self):
        "The code has finished running, and will start again"
        self.run_status.set('Not running')
        tkMessageBox.showinfo(message='Program has finished, and will restart.')

    def on_info(self, message):
        "The debugger needs to inform the user of something"
        tkMessageBox.showinfo(message=message)

    def on_warning(self, message):
        "The debugger needs to warn the user of something"
        tkMessageBox.showwarning(message=message)

    def on_error(self, message):
        "The debugger needs to report an error"
        tkMessageBox.showerror(message=message)

    def on_breakpoint_enable(self, bp):
        "A breakpoint has been enabled in the debugger"
        # If the breakpoint is in the currently displayed file, updated
        # the display of the breakpoint.
        if bp.filename == self.code.filename:
            self.code.enable_breakpoint(bp.line, temporary=bp.temporary)

        # ... then update the display of the breakpoint on the tree
        self.breakpoints.update_breakpoint(bp)

    def on_breakpoint_disable(self, bp):
        "A breakpoint has been disabled in the debugger"
        # If the breakpoint is in the currently displayed file, updated
        # the display of the breakpoint.
        if bp.filename == self.code.filename:
            self.code.disable_breakpoint(bp.line)

        # ... then update the display of the breakpoint on the tree
        self.breakpoints.update_breakpoint(bp)

    def on_breakpoint_ignore(self, bp, count):
        "A breakpoint has been ignored by the debugger"
        # If the breakpoint is in the currently displayed file, updated
        # the display of the breakpoint.
        if bp.filename == self.code.filename:
            self.code.ignore_breakpoint(bp.line)

        # ... then update the display of the breakpoint on the tree
        self.breakpoints.update_breakpoint(bp)

    def on_breakpoint_clear(self, bp):
        "A breakpoint has been cleared in the debugger"
        # If the breakpoint is in the currently displayed file, updated
        # the display of the breakpoint.
        if bp.filename == self.code.filename:
            self.code.clear_breakpoint(bp.line)

        # ... then update the display of the breakpoint on the tree
        self.breakpoints.update_breakpoint(bp)

########NEW FILE########
__FILENAME__ = widgets
from ttk import *

from tkreadonly import ReadOnlyCode

from pygments.lexers import PythonLexer

from bugjar.connection import ConnectionNotBootstrapped, UnknownBreakpoint


class DebuggerCode(ReadOnlyCode):
    def __init__(self, *args, **kwargs):
        self.debugger = kwargs.pop('debugger')
        kwargs['lexer'] = PythonLexer(stripnl=False)
        ReadOnlyCode.__init__(self, *args, **kwargs)

        # Set up styles for line numbers
        self.lines.tag_configure('enabled', background='red')
        self.lines.tag_configure('disabled', background='gray')
        self.lines.tag_configure('ignored', background='green')
        self.lines.tag_configure('temporary', background='pink')

        self.line_bind('<Double-1>', self.on_line_double_click)
        self.name_bind('<Double-1>', self.on_name_double_click)

    def enable_breakpoint(self, line, temporary=False):
        self.lines.tag_remove(
            'disabled',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'ignored',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        if temporary:
            self.lines.tag_remove(
                'enabled',
                '%s.0' % line,
                '%s.0' % (line + 1)
            )
            self.lines.tag_add(
                'temporary',
                '%s.0' % line,
                '%s.0' % (line + 1)
            )
        else:
            self.lines.tag_remove(
                'temporary',
                '%s.0' % line,
                '%s.0' % (line + 1)
            )
            self.lines.tag_add(
                'enabled',
                '%s.0' % line,
                '%s.0' % (line + 1)
            )

    def disable_breakpoint(self, line):
        self.lines.tag_remove(
            'enabled',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'ignored',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'temporary',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_add(
            'disabled',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )

    def clear_breakpoint(self, line):
        self.lines.tag_remove(
            'enabled',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'disabled',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'ignored',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )
        self.lines.tag_remove(
            'temporary',
            '%s.0' % line,
            '%s.0' % (line + 1)
        )

    def on_line_double_click(self, event):
        "When a line number is double clicked, set a breakpoint"
        try:
            # If a breakpoint already exists on this line,
            # find it and toggle it.
            bp = self.debugger.breakpoint((self.filename, event.line))
            if bp.enabled:
                self.debugger.disable_breakpoint(bp)
            else:
                self.debugger.enable_breakpoint(bp)
        except UnknownBreakpoint:
            # No breakpoint for this line; create one.
            self.debugger.create_breakpoint(self.filename, event.line)
        except ConnectionNotBootstrapped:
            print "Connection not configured"

    def on_name_double_click(self, event):
        "When a code variable is clicked on... do something"
        pass


class BreakpointView(Treeview):
    def __init__(self, *args, **kwargs):
        # Only a single stack frame can be selected at a time.
        kwargs['selectmode'] = 'browse'
        self.normalizer = kwargs.pop('normalizer')
        Treeview.__init__(self, *args, **kwargs)

        # self['columns'] = ('line',)
        # self.column('line', width=100, anchor='center')
        self.heading('#0', text='File')
        # self.heading('line', text='Line')

        # Set up styles for line numbers
        self.tag_configure('enabled', foreground='red')
        self.tag_configure('disabled', foreground='gray')
        self.tag_configure('ignored', foreground='green')
        self.tag_configure('temporary', foreground='pink')

    def insert_filename(self, filename):
        "Ensure that a specific filename exists in the breakpoint tree"
        if not self.exists(filename):
            # First, establish the index at which to insert this child.
            # Do this by getting a list of children, sorting the list by name
            # and then finding how many would sort less than the label for
            # this node.
            files = sorted(self.get_children(''), reverse=False)
            index = len([item for item in files if item > filename])

            # Now insert a new node at the index that was found.
            self.insert(
                '', index, self._nodify(filename),
                text=self.normalizer(filename),
                open=True,
                tags=['file']
            )

    def update_breakpoint(self, bp):
        """Update the visualization of a breakpoint in the tree.

        If the breakpoint isn't arlready on the tree, add it.
        """
        self.insert_filename(bp.filename)

        # Determine the right tag for the line number
        if bp.enabled:
            if bp.temporary:
                tag = 'temporary'
            else:
                tag = 'enabled'
        else:
            tag = 'disabled'

        # Update the display for the line number,
        # adding a new tree node if necessary.
        if self.exists(unicode(bp)):
            self.item(unicode(bp), tags=['breakpoint', tag])
        else:
            # First, establish the index at which to insert this child.
            # Do this by getting a list of children, sorting the list by name
            # and then finding how many would sort less than the label for
            # this node.
            lines = sorted((int(self.item(item)['text']) for item in self.get_children(bp.filename)), reverse=False)
            index = len([line for line in lines if line < bp.line])

            # Now insert a new node at the index that was found.
            self.insert(
                self._nodify(bp.filename), index, unicode(bp),
                text=unicode(bp.line),
                open=True,
                tags=['breakpoint', tag]
            )

    def _nodify(self, node):
        "Escape any problem characters in a node name"
        return node.replace('\\', '/')

    def selection_set(self, node):
        """Node names on the breakpoint tree are the filename.

        On Windows, this requires escaping, because backslashes
        in filenames cause problems with Tk.
        """
        Treeview.selection_set(self, self._nodify(node))


class StackView(Treeview):
    def __init__(self, *args, **kwargs):
        # Only a single stack frame can be selected at a time.
        kwargs['selectmode'] = 'browse'
        self.normalizer = kwargs.pop('normalizer')
        Treeview.__init__(self, *args, **kwargs)

        self['columns'] = ('line',)
        self.column('line', width=50, anchor='center')
        self.heading('#0', text='File')
        self.heading('line', text='Line')

    def update_stack(self, stack):
        "Update the display of the stack"
        # Retrieve the current stack list
        displayed = self.get_children()

        # Iterate over the entire stack. Update each entry
        # in the stack to match the current frame description.
        # If we need to add an extra frame, do so.
        index = 0
        for line, frame in stack:
            if index < len(displayed):
                self.item(
                    displayed[index],
                    text=self.normalizer(frame['filename']),
                    values=(line,)
                )
            else:
                self.insert(
                    '', index, 'frame:%s' % index,
                    text=self.normalizer(frame['filename']),
                    open=True,
                    values=(line,)
                )
            index = index + 1

        # If we've stepped back out of a frame, there will
        # be less frames than are currently displayed;
        # delete the excess entries.
        for i in range(index, len(displayed)):
            self.delete(displayed[i])


class InspectorView(Treeview):
    def __init__(self, *args, **kwargs):
        # Only a single stack frame can be selected at a time.
        kwargs['selectmode'] = 'browse'
        Treeview.__init__(self, *args, **kwargs)

        self.locals = self.insert(
            '', 'end', ':builtins:',
            text='builtins',
            open=False,
        )

        self.globals = self.insert(
            '', 'end', ':globals:',
            text='globals',
            open=False,
        )

        self.locals = self.insert(
            '', 'end', ':locals:',
            text='locals',
            open=True,
        )

        self['columns'] = ('value',)
        self.column('#0', width=150, anchor='w')
        self.column('value', width=200, anchor='w')
        self.heading('#0', text='Name')
        self.heading('value', text='Value')

    def show_frame(self, frame):
        "Update the display of the stack frame"
        self.update_node(':builtins:', frame['builtins'])
        self.update_node(':globals:', frame['globals'])
        self.update_node(':locals:', frame['locals'])

    def update_node(self, parent, frame):
        # Retrieve the current stack list
        displayed = self.get_children(parent)

        # The next part is a dual iteration: a primary iteration
        # over all the variables in the frame, with a secondary
        # iteration over all the current displayed tree nodes.
        # The iteration finishes when we reach the end of the
        # primary iteration.
        display = 0
        index = 0
        variables = sorted(frame.items())

        while index < len(variables):
            name, value = variables[index]
            node_name = '%s%s' % (parent, name)
            if display < len(displayed):
                if node_name == displayed[display]:
                    # Name matches the expected index.
                    # Update the existing node value, and
                    # move to the next displayed index.
                    self.item(
                        node_name,
                        text=name,
                        values=(value,)
                    )
                    index = index + 1
                    display = display + 1
                elif node_name > displayed[display]:
                    # The variable name will sort after the next
                    # displayed name. This means a variable has
                    # passed out of scope, and should be deleted.
                    # Move to the next displayed index.
                    self.delete(displayed[display])
                    display = display + 1
                else:
                    # The variable name will sort before the next
                    # displayed name. This means a new variable
                    # has entered scope and must be added.
                    self.insert(
                        parent, index, node_name,
                        text=name,
                        values=(value,)
                    )
                    index = index + 1
            else:
                # There are no more displayed nodes, but there are still
                # variables in the frame; we add them all to the end
                self.insert(
                    parent, 'end', node_name,
                    text=name,
                    values=(value,)
                )
                index = index + 1

        # Primary iteration has ended, which means we've run out of variables
        # in the frame. However, there may still be display nodes. Delete
        # them, because they are stale.
        for i in range(display, len(displayed)):
            self.delete(displayed[i])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bugjar documentation build configuration file, created by
# sphinx-quickstart on Sat Jul 27 14:58:42 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bugjar

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bugjar'
copyright = u'2013, Russell Keith-Magee'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(str(n) for n in bugjar.NUM_VERSION[:2])
# The full version, including alpha/beta/rc tags.
release = bugjar.VERSION

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
htmlhelp_basename = 'Bugjardoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bugjar.tex', u'Bugjar Documentation',
   u'Russell Keith-Magee', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bugjar', u'Bugjar Documentation',
     [u'Russell Keith-Magee'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bugjar', u'Bugjar Documentation',
   u'Russell Keith-Magee', 'Bugjar', 'A graphical Python debugger.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
