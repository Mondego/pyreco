__FILENAME__ = start_vdebug
import sys
import os
import inspect

directory = os.path.dirname(inspect.getfile(inspect.currentframe()))
sys.path.append(directory)

import socket
import traceback
import vdebug.runner
import vdebug.event
import vim

class DebuggerInterface:
    """Acts as a facade layer to the debugger client.

    Most methods are just redirected to the Runner class. Fatal 
    exceptions are caught and handled here.
    """
    def __init__(self):
        self.runner = vdebug.runner.Runner()
        self.event_dispatcher = vdebug.event.Dispatcher(self.runner)

    def __del__(self):
        self.runner.close_connection()

    def run(self):
        """Tell the debugger to run, until the next breakpoint or end of script.
        """
        try:
            self.runner.run()
        except Exception as e:
            self.handle_exception(e)

    def run_to_cursor(self):
        """Run to the current VIM cursor position.
        """
        try:
            self.runner.run_to_cursor()
        except Exception as e:
            self.handle_exception(e)

    def step_over(self):
        """Step over to the next statement.
        """
        try:
            self.runner.step_over()
        except Exception as e:
            self.handle_exception(e)

    def step_into(self):
        """Step into a statement on the current line.
        """
        try:
            self.runner.step_into()
        except Exception as e:
            self.handle_exception(e)

    def step_out(self):
        """Step out of the current statement.
        """
        try:
            self.runner.step_out()
        except Exception as e:
            self.handle_exception(e)

    def handle_opt(self,option,value = None):
        """Set an option, overwriting the existing value.
        """
        try:
            if value is None:
                return self.runner.ui.say(vdebug.opts.Options.get(option))
            else:
                self.runner.ui.say("Setting vdebug option '%s' to: %s"\
                                    %(option,value))
                vim.command('let g:vdebug_options["%s"] = "%s"' %(option,value))
                return vdebug.opts.Options.overwrite(option,value)

        except Exception as e:
            self.handle_exception(e)


    def handle_return_keypress(self):
        """React to a <enter> keypress event.
        """
        try:
            return self.event_dispatcher.by_position()
        except Exception as e:
            self.handle_exception(e)

    def handle_double_click(self):
        """React to a mouse double click event.
        """
        try:
            return self.event_dispatcher.by_position()
        except Exception as e:
            self.handle_exception(e)

    def handle_visual_eval(self):
        """React to eval during visual selection.
        """
        try:
            return self.event_dispatcher.visual_eval()
        except Exception as e:
            self.handle_exception(e)

    def handle_eval(self,args):
        """Evaluate a code snippet specified by args.
        """
        try:
            return self.runner.eval(args)
        except Exception as e:
            self.handle_exception(e)

    def eval_under_cursor(self):
        """Evaluate the property under the cursor.
        """
        try:
            return self.event_dispatcher.eval_under_cursor()
        except Exception as e:
            self.handle_exception(e)

    def toggle_breakpoint_window(self):
        """Open or close the breakpoint window.
        """
        try:
            return self.runner.toggle_breakpoint_window()
        except Exception as e:
            self.handle_exception(e)

    def set_breakpoint(self,args = None):
        """Set a breakpoint, specified by args.
        """
        try:
            self.runner.set_breakpoint(args)
        except Exception as e:
            self.handle_exception(e)

    def remove_breakpoint(self,args = None):
        """Remove one or more breakpoints, specified by args.
        """
        try:
            self.runner.remove_breakpoint(args)
        except Exception as e:
            self.handle_exception(e)

    def get_context(self):
        """Get all the variables in the default context
        """
        try:
            self.runner.get_context()
        except Exception as e:
            self.handle_exception(e)


    def detach(self):
        """Detach the debugger, so the script runs to the end.
        """
        try:
            self.runner.detach()
            self.runner.close_connection()
        except Exception as e:
            self.handle_exception(e)

    def close(self):
        """Close the connection, or the UI if already closed.
        """
        if self.runner.is_alive():
            self.runner.close_connection()
        else:
            self.runner.close()

    """ Exception handlers """

    def handle_timeout(self):
        """Handle a timeout, which is pretty normal. 
        """
        self.runner.close()
        self.runner.ui.say("No connection was made")

    def handle_interrupt(self):
        """Handle a user interrupt, which is pretty normal. 
        """
        self.runner.close()
        self.runner.ui.say("Connection cancelled")

    def handle_socket_end(self):
        """Handle a socket closing, which is pretty normal.
        """
        self.runner.ui.say("Connection to the debugger has been closed")
        self.runner.close_connection()

    def handle_vim_error(self,e):
        """Handle a VIM error.

        This should NOT occur under normal circumstances.
        """
        self.runner.ui.error("A Vim error occured: "+\
                str(e)+\
                "\n"+ traceback.format_exc())

    def handle_readable_error(self,e):
        """Simply print an error, since it is human readable enough.
        """
        self.runner.ui.error(str(e))

    def handle_dbgp_error(self,e):
        """Simply print an error, since it is human readable enough.
        """
        self.runner.ui.error(str(e.args[0]))

    def handle_general_exception(self):
        """Handle an unknown error of any kind.
        """
        self.runner.ui.error("An error occured: "+\
                str(sys.exc_info()[0])+\
                "\n"+ traceback.format_exc())

    def handle_exception(self,e):
        """Switch on the exception type to work out how to handle it.
        """
        if isinstance(e,vdebug.dbgp.TimeoutError):
            self.handle_timeout()
        elif isinstance(e,vdebug.util.UserInterrupt):
            try:
                self.handle_interrupt()
            except:
                pass
        elif isinstance(e,vdebug.event.EventError):
            self.handle_readable_error(e)
        elif isinstance(e,vdebug.breakpoint.BreakpointError):
            self.handle_readable_error(e)
        elif isinstance(e,vdebug.log.LogError):
            self.handle_readable_error(e)
        elif isinstance(e,vdebug.dbgp.DBGPError):
            self.handle_dbgp_error(e)
        elif isinstance(e,(EOFError,socket.error)):
            self.handle_socket_end()
        elif isinstance(e,KeyboardInterrupt):
            print "Keyboard interrupt - debugging session cancelled"
            try:
                self.runner.close()
            except:
                pass
        else:
            self.handle_general_exception()
        """
        elif isinstance(e,vim.error):
            self.handle_vim_error(e)
        """

########NEW FILE########
__FILENAME__ = breakpoint
import base64
import vdebug.log

class Store:

    def __init__(self):
        self.breakpoints = {}
        self.api = None

    def link_api(self,api):
        self.api = api
        num_bps = len(self.breakpoints)
        if num_bps > 0:
            vdebug.log.Log("Registering %i breakpoints with the debugger" % num_bps)
        for id, bp in self.breakpoints.iteritems():
            res = self.api.breakpoint_set(bp.get_cmd())
            bp.set_debugger_id(res.get_id())

    # Update line-based breakpoints with a dict of IDs and lines
    def update_lines(self,lines):
        for id, line in lines.iteritems():
            try:
                self.breakpoints[id].set_line(line)
                vdebug.log.Log("Updated line number of breakpoint %s to %s"\
                                    %(str(id),str(line)) )
            except ValueError:
                pass
                # No method set_line, not a line breakpoint

    def unlink_api(self):
        self.api = None

    def add_breakpoint(self,breakpoint):
        vdebug.log.Log("Adding " + str(breakpoint))
        self.breakpoints[str(breakpoint.get_id())] = breakpoint
        breakpoint.on_add()
        if self.api is not None:
            res = self.api.breakpoint_set(breakpoint.get_cmd())
            breakpoint.set_debugger_id(res.get_id())

    def remove_breakpoint(self,breakpoint):
        self.remove_breakpoint_by_id(\
                breakpoint.get_id())

    def remove_breakpoint_by_id(self,id):
        id = str(id)
        if id not in self.breakpoints:
            raise BreakpointError("No breakpoint matching ID %s" % id)
        vdebug.log.Log("Removing breakpoint id %s" % id)
        if self.api is not None:
            dbg_id = self.breakpoints[id].get_debugger_id()
            if dbg_id is not None:
                self.api.breakpoint_remove(dbg_id)
        self.breakpoints[id].on_remove()
        del self.breakpoints[id]

    def clear_breakpoints(self):
        for id in self.breakpoints.keys():
            self.remove_breakpoint_by_id(id)
        self.breakpoints = {}

    def find_breakpoint(self,file,line):
        found = None
        for id, bp in self.breakpoints.iteritems():
            if bp.type == "line":
                if bp.get_file() == file and\
                        bp.get_line() == line:
                    found = bp.get_id()
                    break
        return found

    def get_sorted_list(self):
        keys = self.breakpoints.keys()
        keys.sort()
        return map(self.breakpoints.get,keys)

class BreakpointError(Exception):
    pass

class Breakpoint:
    """ Abstract factory for creating a breakpoint object.

    Use the class method parse to create a concrete subclass
    of a specific type.
    """
    type = None
    id = 11000
    dbg_id = None

    def __init__(self,ui):
        self.id = Breakpoint.id
        Breakpoint.id += 1 
        self.ui = ui

    def get_id(self):
        return self.id

    def set_debugger_id(self,dbg_id):
        self.dbg_id = dbg_id

    def get_debugger_id(self):
        return self.dbg_id

    def on_add(self):
        self.ui.register_breakpoint(self)

    def on_remove(self):
        self.ui.remove_breakpoint(self)

    @classmethod
    def parse(self,ui,args):
        if args is None:
            args = ""
        args = args.strip()
        if len(args) == 0:
            """ Line breakpoint """
            row = ui.get_current_row()
            try:
                file = ui.get_current_file()
                line = ui.get_current_line()
                if len(line.strip()) == 0:
                    raise BreakpointError('Cannot set a breakpoint ' +\
                                            'on an empty line')
            except vdebug.util.FilePathError:
                raise BreakpointError('No file, cannot set breakpoint')
            return LineBreakpoint(ui,file,row)
        else:
            arg_parts = args.split(' ')
            type = arg_parts.pop(0)
            type.lower()
            if type == 'conditional':
                row = ui.get_current_row()
                file = ui.get_current_file()
                if len(arg_parts) == 0:
                    raise BreakpointError("Conditional breakpoints " +\
                            "require a condition to be specified")
                cond = " ".join(arg_parts)
                return ConditionalBreakpoint(ui,file,row,cond)
            elif type == 'watch':
                if len(arg_parts) == 0:
                    raise BreakpointError("Watch breakpoints " +\
                            "require a condition to be specified")
                expr = " ".join(arg_parts)
                vdebug.log.Log("Expression: %s"%expr)
                return WatchBreakpoint(ui,expr)
            elif type == 'exception':
                if len(arg_parts) == 0:
                    raise BreakpointError("Exception breakpoints " +\
                            "require an exception name to be specified")
                return ExceptionBreakpoint(ui,arg_parts[0])
            elif type == 'return':
                l = len(arg_parts)
                if l == 0:
                    raise BreakpointError("Return breakpoints " +\
                            "require a function name to be specified")
                return ReturnBreakpoint(ui,arg_parts[0])
            elif type == 'call':
                l = len(arg_parts)
                if l == 0:
                    raise BreakpointError("Call breakpoints " +\
                            "require a function name to be specified")
                return CallBreakpoint(ui,arg_parts[0])
            else:
                raise BreakpointError("Unknown breakpoint type, " +\
                        "please choose one of: conditional, exception,"+\
                        "call or return")

    def get_cmd(self):
        pass

    def __str__(self):
        return "%s breakpoint, id %i" %(self.type,self.id)

class LineBreakpoint(Breakpoint):
    type = "line"

    def __init__(self,ui,file,line):
        Breakpoint.__init__(self,ui)
        self.file = file
        self.line = line

    def get_line(self):
        return self.line

    def set_line(self,line):
        self.line = int(line)

    def get_file(self):
        return self.file

    def get_cmd(self):
        cmd = "-t " + self.type
        cmd += " -f " + self.file.as_remote()
        cmd += " -n " + str(self.line)
        cmd += " -s enabled"
        
        return cmd

class TemporaryLineBreakpoint(LineBreakpoint):
    def on_add(self):
        pass

    def on_remove(self):
        pass

    def get_cmd(self):
        cmd = LineBreakpoint.get_cmd(self)
        return cmd + " -r 1"

class ConditionalBreakpoint(LineBreakpoint):
    type = "conditional"

    def __init__(self,ui,file,line,condition):
        LineBreakpoint.__init__(self,ui,file,line)
        self.condition = condition

    def get_cmd(self):
        cmd = LineBreakpoint.get_cmd(self)
        cmd += " -- " + base64.encodestring(self.condition)
        return cmd

class WatchBreakpoint(Breakpoint):
    type = "watch"

    def __init__(self,ui,expr):
        Breakpoint.__init__(self,ui)
        self.expr = expr

    def get_cmd(self):
        cmd = "-t " + self.type
        cmd += " -- " + base64.encodestring(self.expr)
        return cmd


class ExceptionBreakpoint(Breakpoint):
    type = "exception"

    def __init__(self,ui,exception):
        Breakpoint.__init__(self,ui)
        self.exception = exception

    def get_cmd(self):
        cmd = "-t " + self.type
        cmd += " -x " + self.exception
        cmd += " -s enabled"
        return cmd

class CallBreakpoint(Breakpoint):
    type = "call"

    def __init__(self,ui,function):
        Breakpoint.__init__(self,ui)
        self.function = function

    def get_cmd(self):
        cmd = "-t " + self.type
        cmd += " -m %s" % self.function
        cmd += " -s enabled"
        return cmd

class ReturnBreakpoint(CallBreakpoint):
    type = "return"

########NEW FILE########
__FILENAME__ = dbgp
import xml.etree.ElementTree as ET
import socket
import vdebug.log
import base64
import time

""" Response objects for the DBGP module."""

class Response:
    """Contains response data from a command made to the debugger."""
    ns = '{urn:debugger_protocol_v1}'

    def __init__(self,response,cmd,cmd_args,api):
        self.response = response
        self.cmd = cmd
        self.cmd_args = cmd_args
        self.xml = None
        self.api = api
        if "<error" in self.response:
            self.__parse_error()

    def __parse_error(self):
        """Parse an error message which has been returned
        in the response, then raise it as a DBGPError."""
        xml = self.as_xml()
        err_el = xml.find('%serror' % self.ns)
        if err_el is None:
            raise DBGPError("Could not parse error from return XML",1)
        else:
            code = err_el.get("code")
            if code is None:
                raise ResponseError(
                        "Missing error code in response",
                        self.response)
            elif int(code) == 4:
                raise CmdNotImplementedError('Command not implemented')
            msg_el = err_el.find('%smessage' % self.ns)
            if msg_el is None:
                raise ResponseError(
                        "Missing error message in response",
                        self.response)
            raise DBGPError(msg_el.text,code)

    def get_cmd(self):
        """Get the command that created this response."""
        return self.cmd

    def get_cmd_args(self):
        """Get the arguments to the command."""
        return self.cmd_args

    def as_string(self):
        """Return the full response as a string.

        There is a __str__ method, which will render the
        whole object as a string and should be used for
        displaying.
        """
        return self.response

    def as_xml(self):
        """Get the response as element tree XML.

        Returns an xml.etree.ElementTree.Element object.
        """
        if self.xml == None:
            self.xml = ET.fromstring(self.response)
            self.__determine_ns()
        return self.xml

    def __determine_ns(self):
        tag_repr = str(self.xml.tag)
        if tag_repr[0] != '{':
            raise DBGPError('Invalid or missing XML namespace',1)
        else:
            ns_parts = tag_repr.split('}')
            self.ns = ns_parts[0] + '}'

    def __str__(self):
        return self.as_string()

class ContextNamesResponse(Response):
    def names(self):
        names = {}
        for c in list(self.as_xml()):
            names[int(c.get('id'))] = c.get('name')
        return names

class StatusResponse(Response):
    """Response object returned by the status command."""

    def __str__(self):
        return self.as_xml().get('status')

class StackGetResponse(Response):
    """Response object used by the stack_get command."""

    def get_stack(self):
        return list(self.as_xml())

class ContextGetResponse(Response):
    """Response object used by the context_get command.

    The property nodes are converted into ContextProperty
    objects, which are much easier to use."""

    def __init__(self,response,cmd,cmd_args,api):
        Response.__init__(self,response,cmd,cmd_args,api)
        self.properties = []

    def get_context(self):
        for c in list(self.as_xml()):
            self.create_properties(ContextProperty(c))

        return self.properties

    def create_properties(self,property):
        self.properties.append(property)
        for p in property.children:
            self.create_properties(p)

class EvalResponse(ContextGetResponse):
    """Response object returned by the eval command."""
    def __init__(self,response,cmd,cmd_args,api):
        try:
            ContextGetResponse.__init__(self,response,cmd,cmd_args,api)
        except DBGPError as e:
            if int(e.args[1]) == 206:
                raise EvalError()
            else:
                raise e

    def get_context(self):
        code = self.get_code()
        for c in list(self.as_xml()):
            self.create_properties(EvalProperty(c,code,self.api.language))

        return self.properties

    def get_code(self):
        cmd = self.get_cmd_args()
        parts = cmd.split('-- ')
        return base64.decodestring(parts[1])


class BreakpointSetResponse(Response):
    """Response object returned by the breakpoint_set command."""

    def get_id(self):
        return int(self.as_xml().get('id'))

    def __str__(self):
        return self.as_xml().get('id')

class FeatureGetResponse(Response):
    """Response object specifically for the feature_get command."""

    def is_supported(self):
        """Whether the feature is supported or not."""
        xml = self.as_xml()
        return int(xml.get('supported'))

    def __str__(self):
        if self.is_supported():
            xml = self.as_xml()
            return xml.text
        else:
            return "* Feature not supported *"

class Api:
    """Api for eBGP commands.

    Uses a Connection object to read and write with the debugger,
    and builds commands and returns the results.
    """

    conn = None
    transID = 0

    def __init__(self,connection):
        """Create a new Api using a Connection object.

        The Connection object specifies the debugger connection,
        and the Protocol provides a OO api to interacting
        with it.

        connection -- The Connection object to use
        """
        self.language = None
        self.protocol = None
        self.idekey = None
        self.startfile = None
        self.conn = connection
        if self.conn.isconnected() == 0:
            self.conn.open()
        self.__parse_init_msg(self.conn.recv_msg())

    def __parse_init_msg(self,msg):
        """Parse the init message from the debugger"""
        xml = ET.fromstring(msg)
        self.language = xml.get("language")
        if self.language is None:
            raise ResponseError(
                "Invalid XML response from debugger",
                msg)
        self.language = self.language.lower()
        self.idekey = xml.get("idekey")
        self.version = xml.get("api_version")
        self.startfile = xml.get("fileuri")

    def send_cmd(self,cmd,args = '',
            res_cls = Response):
        """Send a command to the debugger.

        This method automatically adds a unique transaction
        ID to the command which is required by the debugger.

        Returns a Response object, which contains the
        response message and command.

        cmd -- the command name, e.g. 'status'
        args -- arguments for the command, which is optional 
                for certain commands (default '')
        """
        args = args.strip()
        send = cmd.strip()
        self.transID += 1
        send += ' -i '+ str(self.transID)
        if len(args) > 0:
            send += ' ' + args
        vdebug.log.Log("Command: "+send,\
                vdebug.log.Logger.DEBUG)
        self.conn.send_msg(send)
        msg = self.conn.recv_msg()
        vdebug.log.Log("Response: "+msg,\
                vdebug.log.Logger.DEBUG)
        return res_cls(msg,cmd,args,self)

    def status(self):
        """Get the debugger status.

        Returns a Response object.
        """
        return self.send_cmd('status','',StatusResponse)

    def feature_get(self,name):
        """Get the value of a feature from the debugger.

        See the DBGP documentation for a list of features.

        Returns a FeatureGetResponse object.

        name -- name of the feature, e.g. encoding
        """
        return self.send_cmd(
                'feature_get',
                '-n '+str(name),
                FeatureGetResponse)

    def feature_set(self,name,value):
        """Set the value of a debugger feature.

        See the DBGP documentation for a list of features.

        Returns a Response object.

        name -- name of the feature, e.g. encoding
        value -- new value for the feature
        """
        return self.send_cmd(
                'feature_set',
                '-n ' + str(name) + ' -v ' + str(value))

    def run(self):
        """Tell the debugger to start or resume
        execution."""
        return self.send_cmd('run','',StatusResponse)

    def eval(self,code):
        """Tell the debugger to start or resume
        execution."""
        code_enc = base64.encodestring(code)
        args = '-- %s' % code_enc

        """ The python engine incorrectly requires length.
        if self.language == 'python':
            args = ("-l %i " % len(code_enc) ) + args"""
            
        return self.send_cmd('eval',args,EvalResponse)

    def step_into(self):
        """Tell the debugger to step to the next
        statement.

        If there's a function call, the debugger engine
        will break on the first statement in the function.
        """
        return self.send_cmd('step_into','',StatusResponse)

    def step_over(self):
        """Tell the debugger to step to the next
        statement.

        If there's a function call, the debugger engine
        will stop at the next statement after the function call.
        """
        return self.send_cmd('step_over','',StatusResponse)

    def step_out(self):
        """Tell the debugger to step out of the statement.

        The debugger will step out of the current scope.
        """
        return self.send_cmd('step_out','',StatusResponse)

    def stop(self):
        """Tell the debugger to stop execution.

        The script is terminated immediately."""
        return self.send_cmd('stop','',StatusResponse)

    def stack_get(self):
        """Get the stack information.
        """
        return self.send_cmd('stack_get','',StackGetResponse)

    def context_get(self,context = 0):
        """Get the context variables.
        """
        return self.send_cmd('context_get',\
                '-c %i' % int(context),\
                ContextGetResponse)

    def context_names(self):
        """Get the context types.
        """
        return self.send_cmd('context_names','',ContextNamesResponse)

    def property_get(self,name):
        """Get a property.
        """
        return self.send_cmd('property_get','-n %s -d 0' % name,ContextGetResponse)

    def detach(self):
        """Tell the debugger to detach itself from this
        client.

        The script is not terminated, but runs as normal
        from this point."""
        ret = self.send_cmd('detach','',StatusResponse)
        self.conn.close()
        return ret

    def breakpoint_set(self,cmd_args):
        """Set a breakpoint.

        The breakpoint type is defined by the arguments, see the
        Breakpoint class for more detail."""
        return self.send_cmd('breakpoint_set',cmd_args,\
                BreakpointSetResponse)

    def breakpoint_list(self):
        return self.send_cmd('breakpoint_list')

    def breakpoint_remove(self,id):
        """Remove a breakpoint by ID.

        The ID is that returned in the response from breakpoint_set."""
        return self.send_cmd('breakpoint_remove','-d %i' % id,Response)

"""Connection module for managing a socket connection
between this client and the debugger."""

class Connection:
    """DBGP connection class, for managing the connection to the debugger.

    The host, port and socket timeout are configurable on object construction.
    """

    sock = None
    address = None
    isconned = 0

    def __init__(self, host = '', port = 9000, timeout = 30, input_stream = None):
        """Create a new Connection.

        The connection is not established until open() is called.

        host -- host name where debugger is running (default '')
        port -- port number which debugger is listening on (default 9000)
        timeout -- time in seconds to wait for a debugger connection before giving up (default 30)
        input_stream -- object for checking input stream and user interrupts (default None)
        """
        self.port = port
        self.host = host
        self.timeout = timeout
        self.input_stream = input_stream

    def __del__(self):
        """Make sure the connection is closed."""
        self.close()

    def isconnected(self):
        """Whether the connection has been established."""
        return self.isconned

    def open(self):
        """Listen for a connection from the debugger. Listening for the actual
        connection is handled by self.listen()."""
        print 'Waiting for a connection (Ctrl-C to cancel, this message will self-destruct in ',self.timeout,' seconds...)'
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serv.setblocking(0)
            serv.bind((self.host, self.port))
            serv.listen(5)
            (self.sock, self.address) = self.listen(serv, self.timeout)
            self.sock.settimeout(None)
        except socket.timeout:
            serv.close()
            raise TimeoutError("Timeout waiting for connection")
        except:
            serv.close()
            raise

        self.isconned = 1
        serv.close()

    def listen(self, serv, timeout):
        """Non-blocking listener. Provides support for keyboard interrupts from
        the user. Although it's non-blocking, the user interface will still
        block until the timeout is reached.

        serv -- Socket server to listen to.
        timeout -- Seconds before timeout.
        """
        start = time.time()
        while True:
            if (time.time() - start) > timeout:
                raise socket.timeout
            try:
                """Check for user interrupts"""
                if self.input_stream is not None:
                    self.input_stream.probe()
                return serv.accept()
            except socket.error:
                pass

    def close(self):
        """Close the connection."""
        if self.sock != None:
            vdebug.log.Log("Closing the socket",\
                            vdebug.log.Logger.DEBUG)
            self.sock.close()
            self.sock = None
        self.isconned = 0

    def __recv_length(self):
        """Get the length of the proceeding message."""
        length = ''
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError('Socket Closed')
            if c == '\0':
                return int(length)
            if c.isdigit():
                length = length + c

    def __recv_null(self):
        """Receive a null byte."""
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError('Socket Closed')
            if c == '\0':
                return

    def __recv_body(self, to_recv):
        """Receive a message of a given length.

        to_recv -- length of the message to receive
        """
        body = ''
        while to_recv > 0:
            buf = self.sock.recv(to_recv)
            if buf == '':
                self.close()
                raise EOFError('Socket Closed')
            to_recv -= len(buf)
            body = body + buf
        return body

    def recv_msg(self):
        """Receive a message from the debugger.

        Returns a string, which is expected to be XML.
        """
        length = self.__recv_length()
        body     = self.__recv_body(length)
        self.__recv_null()
        return body

    def send_msg(self, cmd):
        """Send a message to the debugger.

        cmd -- command to send
        """
        self.sock.send(cmd + '\0')

class ContextProperty:

    ns = '{urn:debugger_protocol_v1}'

    def __init__(self,node,parent = None,depth = 0):
        self.parent = parent
        self.__determine_type(node)
        self._determine_displayname(node)
        self.encoding = node.get('encoding')
        self.depth = depth

        self.size = node.get('size')
        self.value = ""
        self.is_last_child = False

        self._determine_children(node)
        self.__determine_value(node)
        self.__init_children(node)
        if self.type == 'scalar':
            self.size = len(self.value) - 2

    def __determine_value(self,node):
        if self.has_children:
            self.value = ""
            return

        self.value = self._get_enc_node_text(node,'value')
        if self.value is None:
            if self.encoding == 'base64':
                if node.text is None:
                    self.value = ""
                else:
                    self.value = base64.decodestring(node.text)
            elif not self.is_uninitialized() \
                    and not self.has_children:
                self.value = node.text

        if self.value is None:
            self.value = ""

        self.num_crs = self.value.count('\n')
        if self.type.lower() in ("string","str","scalar"):
            self.value = '`%s`' % self.value.replace('`','\\`')

    def __determine_type(self,node):
        type = node.get('classname')
        if type is None:
            type = node.get('type')
        if type is None:
            type = 'unknown'
        self.type = type

    def _determine_displayname(self,node):
        display_name = node.get('fullname')
        if display_name == None:
            display_name = self._get_enc_node_text(node,'fullname',"")
        if display_name == '::':
            display_name = self.type
        self.display_name = display_name

    def _get_enc_node_text(self,node,name,default =
            None):
        n = node.find('%s%s' %(self.ns, name))
        if n is not None and n.text is not None:
            if n.get('encoding') == 'base64':
                val = base64.decodestring(n.text)
            else:
                val = n.text
        else:
            val = None
        if val is None:
            return default
        else:
            return val

    def _determine_children(self,node):
        children = node.get('numchildren')
        if children is None:
            children = node.get('children')
        if children is None:
            children = 0
        else:
            children = int(children)
        self.num_declared_children = children
        self.has_children = True if children > 0 else False
        self.children = []

    def __init_children(self,node):
        if self.has_children:
            idx = 0
            tagname = '%sproperty' % self.ns
            children = list(node)
            if children is not None:
                for c in children:
                    if c.tag == tagname:
                        idx += 1
                        p = self._create_child(c,self,self.depth+1)
                        self.children.append(p)
                        if idx == self.num_declared_children:
                            p.mark_as_last_child()

    def _create_child(self,node,parent,depth):
        return ContextProperty(node,parent,depth)

    def mark_as_last_child(self):
        self.is_last_child = True

    def is_uninitialized(self):
        if self.type == 'uninitialized':
            return True
        else:
            return False

    def child_count(self):
        return len(self.children)

    def type_and_size(self):
        size = None
        if self.has_children:
            size = self.num_declared_children
        elif self.size is not None:
            size = self.size

        if size is None:
            return self.type
        else:
            return "%s [%s]" %(self.type,size)

class EvalProperty(ContextProperty):
    def __init__(self,node,code,language,parent=None,depth=0):
        self.code = code
        self.language = language.lower()
        if parent is None:
            self.is_parent = True
        else:
            self.is_parent = False
        ContextProperty.__init__(self,node,parent,depth)

    def _create_child(self,node,parent,depth):
        return EvalProperty(node,self.code,self.language,parent,depth)

    def _determine_displayname(self,node):
        if self.is_parent:
            self.display_name = self.code
        else:
            if self.language == 'php' or \
                    self.language == 'perl':
                if self.parent.type == 'array':
                    self.display_name = self.parent.display_name + \
                        "['%s']" % node.get('name')
                else:
                    self.display_name = self.parent.display_name + \
                        "->"+node.get('name')
            else:
                name = node.get('name')
                if name is None:
                    name = "?"
                    name = self._get_enc_node_text(node,'name','?')
                if self.parent.type == 'list':
                    self.display_name = self.parent.display_name + name
                else:
                    self.display_name = self.parent.display_name + \
                        "." + name


""" Errors/Exceptions """
class TimeoutError(Exception):
    pass

class DBGPError(Exception):
    """Raised when the debugger returns an error message."""
    pass

class CmdNotImplementedError(Exception):
    """Raised when the debugger returns an error message."""
    pass

class EvalError(Exception):
    """Raised when some evaluated code is invalid."""
    pass

class ResponseError(Exception):
    """An error caused by an unexpected response from the
    debugger (e.g. invalid format XML)."""
    pass

########NEW FILE########
__FILENAME__ = event
# coding=utf-8
import vdebug.log
import vdebug.opts
import vim
import re

class Dispatcher:
    def __init__(self,runner):
        self.runner = runner

    def visual_eval(self):
        if self.runner.is_alive():
            event = VisualEvalEvent()
            return event.execute(self.runner)

    def eval_under_cursor(self):
        if self.runner.is_alive():
            event = CursorEvalEvent()
            return event.execute(self.runner)

    def by_position(self):
        if self.runner.is_alive():
            event = self._get_event_by_position()
            if event is not None:
                return event.execute(self.runner)
            else:
                vdebug.log.Log("No executable event found at current cursor position",\
                        vdebug.log.Logger.DEBUG)
                return False

    def _get_event_by_position(self):
        buf_name = vim.current.buffer.name
        p = re.compile('.*[\\\/]([^\\\/]+)')
        m = p.match(buf_name)
        if m is None:
            return None

        window_name = m.group(1)
        if window_name == self.runner.ui.watchwin.name:
            lineno = vim.current.window.cursor[0]
            vdebug.log.Log("User action in watch window, line %s" % lineno,\
                    vdebug.log.Logger.DEBUG)
            line = self.runner.ui.watchwin.buffer[lineno-1].strip()
            if lineno == 1:
                return WatchWindowContextChangeEvent()
            elif line.startswith(vdebug.opts.Options.get('marker_closed_tree')):
                return WatchWindowPropertyGetEvent()
            elif line.startswith(vdebug.opts.Options.get('marker_open_tree')):
                return WatchWindowHideEvent()
        elif window_name == self.runner.ui.stackwin.name:
            return StackWindowLineSelectEvent()

class Event:
    """Base event class.
    """
    def execute(self,runner):
        pass

class VisualEvalEvent(Event):
    """Evaluate a block of code given by visual selection in Vim.
    """
    def execute(self,runner):
        selection = vim.eval("Vdebug_get_visual_selection()")
        runner.eval(selection)
        return True

class CursorEvalEvent(Event):
    """Evaluate the variable currently under the cursor.
    """
    char_regex = {
        "default" : "a-zA-Z0-9_.\[\]'\"",
        "ruby" : "$@a-zA-Z0-9_.\[\]'\"",
        "perl" : "$a-zA-Z0-9_{}'\"",
        "php" : "$@%a-zA-Z0-9_\[\]'\"\->"
    }

    var_regex = {
        "default" : "^[a-zA-Z_]",
        "ruby" : "^[$@a-zA-Z_]",
        "php" : "^[\$A-Z]",
        "perl" : "^[$@%]"
    }

    def execute(self,runner):
        lineno = vim.current.window.cursor[0]
        colno = vim.current.window.cursor[1]
        line = vim.current.buffer[lineno-1]
        lang = runner.api.language
        if lang in self.char_regex:
            reg = self.char_regex[lang]
        else:
            reg = self.char_regex['default']

        p = re.compile('['+reg+']')
        var = ""
        linelen = len(line)

        for i in range(colno,linelen):
            char = line[i]
            if p.match(char):
                var += char
            else:
                break

        if colno > 0:
            for i in range(colno-1,-1,-1):
                char = line[i]
                if p.match(char):
                    var = char + var
                else:
                    break

        if lang in self.var_regex:
            reg = self.var_regex[lang]
        else:
            reg = self.var_regex["default"]

        f = re.compile(reg)
        if f.match(var) is None:
            runner.ui.error("Cannot find a valid variable under the cursor")
            return False

        if len(var):
            runner.eval(var)
            return True
        else:
            runner.ui.error("Cannot find a valid variable under the cursor")
            return False

class StackWindowLineSelectEvent(Event):
    """Move the the currently selected file and line in the stack window
    """
    def execute(self,runner):
        lineno = vim.current.window.cursor[0]

        vdebug.log.Log("User action in stack window, line %s" % lineno,\
                vdebug.log.Logger.DEBUG)
        line = runner.ui.stackwin.buffer[lineno-1]
        if line.find(" @ ") == -1:
            return False
        filename_pos = line.find(" @ ") + 3
        file_and_line = line[filename_pos:]
        line_pos = file_and_line.rfind(":")
        file = vdebug.util.LocalFilePath(file_and_line[:line_pos])
        lineno = file_and_line[line_pos+1:]
        runner.ui.sourcewin.set_file(file)
        runner.ui.sourcewin.set_line(lineno)

class WatchWindowPropertyGetEvent(Event):
    """Open a tree node in the watch window.

    This retrieves the child nodes and displays them underneath.
    """
    def execute(self,runner):
        lineno = vim.current.window.cursor[0]
        line = vim.current.buffer[lineno-1]
        pointer_index = line.find(vdebug.opts.Options.get('marker_closed_tree'))
        step = len(vdebug.opts.Options.get('marker_closed_tree')) + 1

        eq_index = line.find('=')
        if eq_index == -1:
            raise EventError("Cannot read the selected property")

        name = line[pointer_index+step:eq_index-1]
        context_res = runner.api.property_get(name)
        rend = vdebug.ui.vimui.ContextGetResponseRenderer(context_res)
        output = rend.render(pointer_index - 1)
        if vdebug.opts.Options.get('watch_window_style') == 'expanded':
          runner.ui.watchwin.delete(lineno,lineno+1)
        runner.ui.watchwin.insert(output.rstrip(),lineno-1,True)

class WatchWindowHideEvent(Event):
    """Close a tree node in the watch window.
    """
    def execute(self,runner):
        lineno = vim.current.window.cursor[0]
        line = vim.current.buffer[lineno-1]
        pointer_index = line.find(vdebug.opts.Options.get('marker_open_tree'))

        buf_len = len(vim.current.buffer)
        end_lineno = buf_len - 1
        for i in range(lineno,end_lineno):
            buf_line = vim.current.buffer[i]
            char = buf_line[pointer_index]
            if char != " ":
                end_lineno = i - 1
                break
        runner.ui.watchwin.delete(lineno,end_lineno+1)
        if vdebug.opts.Options.get('watch_window_style') == 'expanded':
            append = "\n" + "".rjust(pointer_index) + "|"
        else:
            append = ""
        runner.ui.watchwin.insert(line.replace(\
                    vdebug.opts.Options.get('marker_open_tree'),\
                    vdebug.opts.Options.get('marker_closed_tree'),1) + \
                append,lineno-1,True)

class WatchWindowContextChangeEvent(Event):
    """Event used to trigger a watch window context change.

    The word under the VIM cursor is retrieved, and context_get called with the
    new context name.
    """

    def execute(self,runner):
        column = vim.current.window.cursor[1]
        line = vim.current.buffer[0]

        vdebug.log.Log("Finding context name at column %s" % column,\
                vdebug.log.Logger.DEBUG)

        tab_end_pos = self.__get_word_end(line,column)
        tab_start_pos = self.__get_word_start(line,column)

        if tab_end_pos == -1 or \
                tab_start_pos == -1:
            raise EventError("Failed to find context name under cursor")

        context_name = line[tab_start_pos:tab_end_pos]
        vdebug.log.Log("Context name: %s" % context_name,\
                vdebug.log.Logger.DEBUG)
        if context_name[0] == '*':
            runner.ui.say("This context is already showing")
            return False

        context_id = self.__determine_context_id(\
                runner.context_names,context_name)

        if context_id == -1:
            raise EventError("Could not resolve context name")
            return False
        else:
            runner.get_context(context_id)
            return True

    def __get_word_end(self,line,column):
        tab_end_pos = -1
        line_len = len(line)
        i = column
        while i < line_len:
            if line[i] == ']':
                tab_end_pos = i-1
                break
            i += 1
        return tab_end_pos

    def __get_word_start(self,line,column):
        tab_start_pos = -1
        j = column
        while j >= 0:
            if line[j] == '[':
                tab_start_pos = j+2
                break
            j -= 1
        return tab_start_pos

    def __determine_context_id(self,context_names,context_name):
        found_id = -1
        for id in context_names.keys():
            name = context_names[id]
            vdebug.log.Log(name +", "+context_name)
            if name == context_name:
                found_id = id
                break
        return found_id

class EventError(Exception):
    pass

########NEW FILE########
__FILENAME__ = log
import time
import sys
import os

class Logger:
    """ Abstract class for all logger implementations.
    
    Concrete classes will log messages using various methods,
    e.g. write to a file.
    """

    (ERROR,INFO,DEBUG) = (0,1,2)
    TYPES = ("ERROR","Info","Debug")
    debug_level = ERROR

    def __init__(self,debug_level):
        pass

    def log(self, string, level):
        """ Log a message """
        pass

    def shutdown(self):
        """ Action to perform when closing the logger """
        pass

    def time(self):
        """ Get a nicely formatted time string """
        return time.strftime("%a %d %Y %H:%M:%S", \
                time.localtime())

    def format(self,string,level):
        display_level = self.TYPES[level]
        """ Format the error message in a standard way """
        return "- [%s] {%s} %s" %(display_level, self.time(), str(string))


class WindowLogger(Logger):
    """ Log messages to a window.

    The window object is passed in on construction, but
    only created if a message is written.
    """
    def __init__(self,debug_level,window):
        self.window = window
        self.debug_level = int(debug_level)

    def shutdown(self):
        if self.window is not None:
            self.window.destroy()

    def log(self, string, level):
        if level > self.debug_level:
            return
        if not self.window.is_open:
            self.window.create()
        self.window.write(\
                self.format(string,level)+"\n")


class FileLogger(Logger):
    """ Log messages to a window.

    The window object is passed in on construction, but
    only created if a message is written.
    """
    def __init__(self,debug_level,filename):
        self.filename = os.path.expanduser(filename)
        self.f = None
        self.debug_level = int(debug_level)

    def __open(self):
        try:
            self.f = open(self.filename,'w')
        except IOError as e:
            raise LogError("Invalid file name '%s' for log file: %s" \
                    %(self.filename,str(e)))
        except:
            raise LogError("Error using file '%s' as a log file: %s" \
                    %(self.filename,sys.exc_info()[0]))


    def shutdown(self):
        if self.f is not None:
            self.f.close()

    def log(self, string, level):
        if level > self.debug_level:
            return
        if self.f is None:
            self.__open()
        self.f.write(\
            self.format(string,level)+"\n")
        self.f.flush()

class Log:

    loggers = {}

    def __init__(self,string,level = Logger.INFO):
        Log.log(string,level)

    @classmethod
    def log(cls, string, level = Logger.INFO):
        for k, l in cls.loggers.iteritems():
            l.log(string,level)

    @classmethod
    def set_logger(cls, logger):
        k = logger.__class__.__name__
        if k in cls.loggers:
            cls.loggers[k].shutdown()
        cls.loggers[k] = logger

    @classmethod
    def remove_logger(cls, type):
        if type in cls.loggers.iteritems():
            cls.loggers[type].shutdown()
            del cls.loggers[type]
            return True
        return False

    @classmethod
    def shutdown(cls):
        for k, l in cls.loggers.iteritems():
            l.shutdown()
        cls.loggers = {}

class LogError(Exception):
    pass


########NEW FILE########
__FILENAME__ = opts

class Options:
    instance = None

    def __init__(self,options):
        self.options = options
    
    @classmethod
    def set(cls,options):
        """Create an Options instance with the provided dictionary of
        options"""
        cls.instance = Options(options)

    @classmethod
    def inst(cls):
        """Get the Options instance.
        """
        if cls.instance is None:
            raise OptionsError("No options have been set")
        return cls.instance

    @classmethod
    def get(cls,name,as_type = str):
        """Get an option by name.

        Raises an OptionsError if the option doesn't exist.
        """
        inst = cls.inst()
        if name in inst.options:
            return as_type(inst.options[name])
        else:
            raise OptionsError("No option with key '%s'" % name)

    @classmethod
    def overwrite(cls,name,value):
        inst = cls.inst()
        inst.options[name] = value

    @classmethod
    def isset(cls,name):
        """Checks whether the option exists and is set.

        By set, it means whether the option has length. All the option
        values are strings.
        """
        inst = cls.inst()
        if name in inst.options and \
            len(inst.options[name]) > 0:
            return True
        else:
            return False

class OptionsError(Exception):
    pass


########NEW FILE########
__FILENAME__ = runner
# coding=utf-8

import vdebug.dbgp
import vdebug.log
import vdebug.ui.vimui
import socket
import vim
import vdebug.breakpoint
import vdebug.opts
import vdebug.util

class Runner:
    """ Class that stitches together all the debugger components.

    This instantiates the connection and debugger vdebug.ui, and provides
    an interface that Vim can use to send commands.
    """

    def __init__(self):
        self.api = None
        vdebug.opts.Options.set(vim.eval('g:vdebug_options'))
        self.breakpoints = vdebug.breakpoint.Store()
        self.keymapper = vdebug.util.Keymapper()
        self.ui = vdebug.ui.vimui.Ui(self.breakpoints)

    def open(self):
        """ Open the connection and debugging vdebug.ui.

        If either of these are already open, the current
        connection or vdebug.ui is used.
        """
        try:
            if self.ui.is_modified():
                self.ui.error("Modified buffers must be saved before debugging")
                return
            vdebug.opts.Options.set(vim.eval('g:vdebug_options'))

            if vdebug.opts.Options.isset('debug_file'):
                vdebug.log.Log.set_logger(vdebug.log.FileLogger(\
                        vdebug.opts.Options.get('debug_file_level'),\
                        vdebug.opts.Options.get('debug_file')))
            self.listen(\
                    vdebug.opts.Options.get('server'),\
                    vdebug.opts.Options.get('port',int),\
                    vdebug.opts.Options.get('timeout',int))

            self.ui.open()
            self.keymapper.map()
            self.ui.set_listener_details(\
                    vdebug.opts.Options.get('server'),\
                    vdebug.opts.Options.get('port'),\
                    vdebug.opts.Options.get('ide_key'))

            addr = self.api.conn.address
            vdebug.log.Log("Found connection from " + str(addr),vdebug.log.Logger.INFO)
            self.ui.set_conn_details(addr[0],addr[1])

            self.set_features()
            self.breakpoints.update_lines(self.ui.get_breakpoint_sign_positions())
            self.breakpoints.link_api(self.api)

            cn_res = self.api.context_names()
            self.context_names = cn_res.names()
            vdebug.log.Log("Available context names: %s" %\
                    str(self.context_names),vdebug.log.Logger.DEBUG)

            if vdebug.opts.Options.get('break_on_open',int) == 1:
                status = self.api.step_into()
            else:
                status = self.api.run()
            self.refresh(status)
        except Exception:
            self.close()
            raise

    def set_features(self):
        """Evaluate vim dictionary of features and pass to debugger.

        Errors are caught if the debugger doesn't like the feature name or
        value. This doesn't break the loop, so multiple features can be set
        even in the case of an error."""
        features = vim.eval('g:vdebug_features')
        for name, value in features.iteritems():
            try:
                self.api.feature_set(name, value)
            except vdebug.dbgp.DBGPError as e:
                error_str = "Failed to set feature %s: %s" %(name,str(e.args[0]))
                self.ui.error(error_str)

    def refresh(self,status):
        """The main action performed after a deubugger step.
    
        Updates the status window, current stack, source
        file and line and watch window."""    
        if not self.is_alive():
            self.ui.error("Cannot update: no connection")
        else:

            if str(status) == "interactive":
                self.ui.error("Debugger engine says it is in interactive mode,"+\
                        "which is not supported: closing connection")
                self.close_connection()
            elif str(status) in ("stopping","stopped"):
                self.ui.statuswin.set_status("stopped")
                self.ui.say("Debugging session has ended")
                self.close_connection(False)
                if vdebug.opts.Options.get('continuous_mode', int) != 0:
                    self.open()
                    return
            else:
                vdebug.log.Log("Getting stack information")
                self.ui.statuswin.set_status(status)
                stack_res = self.update_stack()
                stack = stack_res.get_stack()

                self.cur_file = vdebug.util.RemoteFilePath(stack[0].get('filename'))
                self.cur_lineno = stack[0].get('lineno')

                vdebug.log.Log("Moving to current position in source window")
                self.ui.set_source_position(\
                        self.cur_file,\
                        self.cur_lineno)

                self.get_context(0)

    def get_context(self,context_id = 0):
        self.ui.watchwin.clean()
        name = self.context_names[context_id]
        vdebug.log.Log("Getting %s variables" % name)
        context_res = self.api.context_get(context_id)
        rend = vdebug.ui.vimui.ContextGetResponseRenderer(\
                context_res,"%s at %s:%s" \
                %(name,self.ui.sourcewin.file,self.cur_lineno),\
                self.context_names, context_id)
        self.ui.watchwin.accept_renderer(rend)

    def toggle_breakpoint_window(self):
        """Open or close the breakpoint window.

        The window appears as a horizontal split below the
        currently selected window."""
        if self.ui.breakpointwin.is_open:
            self.ui.breakpointwin.destroy()
        else:
            self.ui.breakpointwin.create()

    def is_alive(self):
        """Whether the connection is open."""
        if self.api is not None and \
            self.api.conn.isconnected():
                return True
        return False

    def run(self):
        """Tell the debugger to run.

        It will run until the end of the execution or until a
        breakpoint is reached."""
        if not self.is_alive():
            self.open()
        else:
            vdebug.log.Log("Running")
            self.ui.statuswin.set_status("running")
            res = self.api.run()
            self.refresh(res)

    def step_over(self):
        """Step over to the next statement."""
        if not self.is_alive():
            self.open()
        else:
            vdebug.log.Log("Stepping over")
            self.ui.statuswin.set_status("running")
            res = self.api.step_over()
            self.refresh(res)

    def step_into(self):
        """Step into the next statement."""
        if not self.is_alive():
            self.open()
        else:
            vdebug.log.Log("Stepping into statement")
            self.ui.statuswin.set_status("running")
            res = self.api.step_into()
            self.refresh(res)

    def step_out(self):
        """Step out of the current context."""
        if not self.is_alive():
            self.open()
        else:
            vdebug.log.Log("Stepping out of statement")
            self.ui.statuswin.set_status("running")
            res = self.api.step_out()
            self.refresh(res)

    def remove_breakpoint(self,args):
        """Remove a breakpoint, by ID or "*"."""
        if args is None:
            args = ""
        args = args.strip()
        if len(args) == 0:
            self.ui.error("ID or '*' required to remove a breakpoint: run "+\
                    "':breakpointWindow' to see breakpoints and their IDs")
            return

        if args == '*':
            self.breakpoints.clear_breakpoints()
        else:
            arg_parts = args.split(" ")
            for id in arg_parts:
                self.breakpoints.remove_breakpoint_by_id(id)

    def set_breakpoint(self,args):
        bp = vdebug.breakpoint.Breakpoint.parse(self.ui,args)
        if bp.type == "line":
            id = self.breakpoints.find_breakpoint(\
                    bp.get_file(),\
                    bp.get_line())
            if id is not None:
                self.breakpoints.remove_breakpoint_by_id(id)
                return
        self.breakpoints.add_breakpoint(bp)

    def eval(self,code):
        """Evaluate a snippet of code and show the response on the watch window.
        """
        try:
            vdebug.log.Log("Evaluating code: "+code)
            context_res = self.api.eval(code)
            rend = vdebug.ui.vimui.ContextGetResponseRenderer(\
                    context_res,"Eval of: '%s'" \
                    %context_res.get_code())
            self.ui.watchwin.clean()
            self.ui.watchwin.accept_renderer(rend)
        except vdebug.dbgp.EvalError:
            self.ui.error("Failed to evaluate invalid code, '%s'" % code)

    def run_to_cursor(self):
        """Tell the debugger to run to the current cursor position.

        This fails if the current window is not the source window.
        """
        row = self.ui.get_current_row()
        file = self.ui.get_current_file()
        vdebug.log.Log(file)
        vdebug.log.Log(self.ui.sourcewin.get_file())
        if file != self.ui.sourcewin.get_file():
            self.ui.error("Run to cursor only works in the source window!")
            return
        vdebug.log.Log("Running to position: line %s of %s" %(row,file))
        bp = vdebug.breakpoint.TemporaryLineBreakpoint(self.ui,file,row)
        self.api.breakpoint_set(bp.get_cmd())
        self.run()

    def listen(self,server,port,timeout):
        """Open the vdebug.dbgp API with connection.

        Uses existing connection if possible.
        """
        if self.is_alive():
            vdebug.log.Log("Cannot open a new connection \
                while one already exists",\
                vdebug.log.Logger.ERROR)
            return
        else:
            while True:
                ide_key = vdebug.opts.Options.get('ide_key')
                check_ide_key = True
                if len(ide_key) == 0:
                    check_ide_key = False
                    
                connection = vdebug.dbgp.Connection(server,port,\
                        timeout,vdebug.util.InputStream())

                self.api = vdebug.dbgp.Api(connection)
                if check_ide_key and ide_key != self.api.idekey:
                    print "Ignoring debugger connection with IDE key '%s'" \
                            % self.api.idekey
                    self.api.detach()
                else:
                    break

    def update_stack(self):
        """Update the stack window with the current stack info.
        """
        if not self.is_alive():
            self.ui.error("Cannot update the stack: no debugger connection")
        else:
            self.ui.stackwin.clean()
            res = self.api.stack_get()
            renderer = vdebug.ui.vimui.StackGetResponseRenderer(res)
            self.ui.stackwin.accept_renderer(renderer)
            return res

    def detach(self):
        """Detach the debugger engine, and allow it to continue execution.
        """
        if not self.is_alive():
            self.ui.error("Cannot detach: no debugger connection")
        else:
            self.ui.say("Detaching the debugger")
            self.api.detach()

    def close_connection(self,stop = True):
        """ Close the connection to the debugger.
        """
        self.breakpoints.unlink_api()
        self.ui.mark_as_stopped()
        try:
            if self.is_alive():
                vdebug.log.Log("Closing the connection")
                if stop:
                    if vdebug.opts.Options.get('on_close') == 'detach':
                        try:
                            self.api.detach()
                        except vdebug.dbgp.CmdNotImplementedError:
                            self.ui.error('Detach is not supported by the debugger, stopping instead')
                            vdebug.opts.Options.overwrite('on_close','stop')
                            self.api.stop()
                    else:
                        self.api.stop()
                self.api.conn.close()
                self.api = None
            else:
                self.api = None
        except EOFError:
            self.api = None
            self.ui.say("Connection has been closed")
        except socket.error:
            self.api = None
            self.ui.say("Connection has been closed")

    def close(self):
        """ Close both the connection and vdebug.ui.
        """
        self.close_connection()
        self.ui.close()
        self.keymapper.unmap()

########NEW FILE########
__FILENAME__ = interface
class Ui():
    """Abstract for the UI, used by the debugger
    """
    watchwin = None
    stackwin = None
    statuswin = None
    logwin = None
    sourcewin = None

    def __init__(self):
        self.is_open = False

    def __del__(self):
        self.close()

    def open(self):
        pass

    def say(self,string):
        pass

    def close(self):
        pass

    def log(self):
        pass

class Window:
    """Abstract for UI windows
    """
    name = "WINDOW"
    is_open = False

    def __del__(self):
        self.destroy()

    def on_create(self):
        """ Callback for after the window is created """
        pass

    def create(self):
        """ Create the window """
        pass

    def write(self, msg):
        """ Write string in the window """
        pass

    def insert(self, msg, position = None):
        """ Insert a string somewhere in the window """
        pass

    def destroy(self):
        """ Close window """
        pass

    def clean(self):
        """ clean all data in buffer """
        pass

########NEW FILE########
__FILENAME__ = vimui
# coding=utf-8
import vdebug.ui.interface
import vdebug.util
import vim
import vdebug.log
import vdebug.opts

class Ui(vdebug.ui.interface.Ui):
    """Ui layer which manages the Vim windows.
    """

    def __init__(self,breakpoints):
        vdebug.ui.interface.Ui.__init__(self)
        self.is_open = False
        self.breakpoint_store = breakpoints
        self.emptybuffer = None
        self.breakpointwin = BreakpointWindow(self,'rightbelow 7new')
        self.current_tab = "1"
        self.tabnr = None

    def is_modified(self):
       modified = int(vim.eval('&mod'))
       if modified:
           return True
       else:
           return False

    def open(self):
        if self.is_open:
            return
        self.is_open = True

        try:
            existing_buffer = True
            cur_buf_name = vim.eval("bufname('%')")
            if cur_buf_name is None:
                existing_buffer = False
                cur_buf_name = ''

            self.current_tab = vim.eval("tabpagenr()")

            vim.command('silent tabnew')
            self.empty_buf_num = vim.eval('bufnr("%")')
            if existing_buffer:
                vim.command('call Vdebug_edit("%s")' % cur_buf_name)

            self.tabnr = vim.eval("tabpagenr()")

            srcwin_name = self.__get_srcwin_name()

            self.watchwin = WatchWindow(self,'vertical belowright new')
            self.watchwin.create()

            self.stackwin = StackWindow(self,'belowright new')
            self.stackwin.create()

            self.statuswin = StatusWindow(self,'belowright new')
            self.statuswin.create()
            self.statuswin.set_status("loading")

            self.watchwin.set_height(20)
            self.statuswin.set_height(5)

            logwin = LogWindow(self,'rightbelow 6new')
            vdebug.log.Log.set_logger(\
                    vdebug.log.WindowLogger(\
                    vdebug.opts.Options.get('debug_window_level'),\
                    logwin))

            winnr = self.__get_srcwinno_by_name(srcwin_name)
            self.sourcewin = SourceWindow(self,winnr)
            self.sourcewin.focus()
        except Exception as e:
            self.is_open = False
            raise e

    def set_source_position(self,file,lineno):
        self.sourcewin.set_file(file)
        self.sourcewin.set_line(lineno)
        self.sourcewin.place_pointer(lineno)

    def mark_as_stopped(self):
        if self.is_open:
            if self.sourcewin:
                self.sourcewin.remove_pointer()
            if self.statuswin:
                self.statuswin.set_status("stopped")
                self.remove_conn_details()

    def set_conn_details(self,addr,port):
        self.statuswin.insert("Connected to %s:%s" %(addr,port),2,True)

    def remove_conn_details(self):
        self.statuswin.insert("Not connected",2,True)

    def set_listener_details(self,addr,port,idekey):
        details = "Listening on %s:%s" %(addr,port)
        if len(idekey):
            details += " (IDE key: %s)" % idekey
        self.statuswin.insert(details,1,True)

    def get_current_file(self):
        return vdebug.util.LocalFilePath(vim.current.buffer.name)

    def get_current_row(self):
        return vim.current.window.cursor[0]

    def get_current_line(self):
        return self.get_line(self.get_current_row())

    def get_line(self,row):
        return vim.eval("getline(" + str(row) + ")")

    def register_breakpoint(self,breakpoint):
        if breakpoint.type == 'line':
            self.place_breakpoint(breakpoint.id,\
                    breakpoint.file,breakpoint.line)
        if self.breakpointwin.is_open:
            self.breakpointwin.add_breakpoint(breakpoint)

    def place_breakpoint(self,sign_id,file,line):
        vim.command('sign place '+str(sign_id)+\
                ' name=breakpt line='+str(line)+\
                ' file='+file.as_local())

    def remove_breakpoint(self,breakpoint):
        id = breakpoint.id
        vim.command('sign unplace %i' % id)
        if self.breakpointwin.is_open:
            self.breakpointwin.remove_breakpoint(id)

    def get_breakpoint_sign_positions(self):
        sign_lines = self.command('sign place').split("\n")
        positions = {}
        for line in sign_lines:
            if "name=breakpt" in line:
                attributes = line.strip().split()
                lineinfo = attributes[0].split('=')
                idinfo = attributes[1].split('=')
                positions[idinfo[1]] = lineinfo[1]
        return positions

    # Execute a vim command and return the output.
    def command(self,cmd):
        vim.command('redir => _tmp')
        vim.command('silent %s' % cmd)
        vim.command('redir END')
        return vim.eval('_tmp')

    def say(self,string):
        """ Vim picks up Python prints, so just print """
        print str(string)
        vdebug.log.Log(string,vdebug.log.Logger.INFO)

    def error(self,string):
        vim.command('echohl Error | echo "'+\
                str(string).replace('"','\\"')+\
                '" | echohl None')
        vdebug.log.Log(string,vdebug.log.Logger.ERROR)

    def close(self):
        if not self.is_open:
            return
        self.is_open = False

        vdebug.log.Log.remove_logger('WindowLogger')
        if self.tabnr:
            vim.command('silent! '+self.tabnr+'tabc!')
        if self.current_tab:
            vim.command('tabn '+self.current_tab)

        if self.empty_buf_num:
            vim.command('bw' + self.empty_buf_num)

        if self.watchwin:
            self.watchwin.destroy()
        if self.stackwin:
            self.stackwin.destroy()
        if self.statuswin:
            self.statuswin.destroy()

        self.watchwin = None
        self.stackwin = None
        self.statuswin = None


    def __get_srcwin_name(self):
        return vim.current.buffer.name

    def __get_srcwinno_by_name(self,name):
        i = 1
        vdebug.log.Log("Searching for win by name %s" % name,\
                vdebug.log.Logger.INFO)
        for w in vim.windows:
            vdebug.log.Log("Win %d, name %s" %(i,w.buffer.name),\
                vdebug.log.Logger.INFO)
            if w.buffer.name == name:
                break
            else:
                i += 1

        vdebug.log.Log("Returning window number %d" % i,\
                vdebug.log.Logger.INFO)
        return i

    def __get_buf_list(self):
        return vim.eval("range(1, bufnr('$'))")

class SourceWindow(vdebug.ui.interface.Window):

    file = None
    pointer_sign_id = '6145'
    breakpoint_sign_id = '6146'

    def __init__(self,ui,winno):
        self.winno = str(winno)

    def focus(self):
        vim.command(self.winno+"wincmd w")

    def command(self,cmd,silent = True):
        self.focus()
        prepend = "silent " if silent else ""
        command_str = prepend + self.winno + "wincmd " + cmd
        vim.command(command_str)

    def set_file(self,file):
        if file == self.file:
            return
        self.file = file
        vdebug.log.Log("Setting source file: "+file,vdebug.log.Logger.INFO)
        self.focus()
        vim.command('call Vdebug_edit("%s")' % str(file).replace("\\", "\\\\"))

    def set_line(self,lineno):
        self.focus()
        vim.command("normal %sgg" % str(lineno))

    def get_file(self):
        self.focus()
        self.file = vdebug.util.LocalFilePath(vim.eval("expand('%:p')"))
        return self.file

    def clear_signs(self):
        vim.command('sign unplace *')

    def place_pointer(self,line):
        vdebug.log.Log("Placing pointer sign on line "+str(line),\
                vdebug.log.Logger.INFO)
        self.remove_pointer()
        vim.command('sign place '+self.pointer_sign_id+\
                ' name=current line='+str(line)+\
                ' file='+self.file)

    def remove_pointer(self):
        vim.command('sign unplace %s' % self.pointer_sign_id)

class Window(vdebug.ui.interface.Window):
    name = "WINDOW"
    open_cmd = "new"
    creation_count = 0

    def __init__(self,ui,open_cmd):
        self.buffer = None
        self.ui = ui
        self.open_cmd = open_cmd
        self.is_open = False

    def getwinnr(self):
        return int(vim.eval("bufwinnr('"+self.name+"')"))

    def set_height(self,height):
        height = int(height)
        minheight = int(vim.eval("&winminheight"))
        if height < minheight:
            height = minheight
        if height <= 0:
            height = 1
        self.command('set winheight=%i' % height)

    def write(self, msg, return_focus = True, after = "normal G"):
        if not self.is_open:
            self.create()
        if return_focus:
            prev_win = vim.eval('winnr()')
        if self.buffer_empty():
            self.buffer[:] = str(msg).split('\n')
        else:
            self.buffer.append(str(msg).split('\n'))
        self.command(after)
        if return_focus:
            vim.command('%swincmd W' % prev_win)

    def insert(self, msg, lineno = None, overwrite = False, allowEmpty = False):
        if not self.is_open:
            self.create()
        """ insert into current position in buffer"""
        if len(msg) == 0 and allowEmpty == False:
            return
        if self.buffer_empty():
            self.buffer[:] = str(msg).split('\n')
        else:
            if lineno == None:
                (lineno, rol) = vim.current.window.cursor
            remaining_buffer = str(msg).split('\n')
            if overwrite:
                lfrom = lineno + 1
            else:
                lfrom = lineno
            remaining_buffer.extend(self.buffer[lfrom:])
            del self.buffer[lineno:]
            if self.buffer_empty():
                self.buffer[:] = remaining_buffer
            else:
                for line in remaining_buffer:
                    self.buffer.append(line)
            self.command(str(lfrom))

    def delete(self,start_line,end_line):
        try:
            self.buffer[end_line]
            remaining_buffer = self.buffer[end_line:]
            del self.buffer[start_line:]
            self.buffer.append(remaining_buffer)
        except IndexError:
            del self.buffer[start_line:]

    def buffer_empty(self):
        if len(self.buffer) == 1 \
                and len(self.buffer[0]) == 0:
            return True
        else:
            return False

    def create(self):
        """ create window """
        vim.command('silent ' + self.open_cmd + ' ' + self.name)
        vim.command("setlocal buftype=nofile modifiable "+ \
                "winfixheight winfixwidth")
        self.buffer = vim.current.buffer
        self.is_open = True
        self.creation_count += 1
        self.on_create()

    def destroy(self):
        """ destroy window """
        if self.buffer == None or len(dir(self.buffer)) == 0:
            return
        self.is_open = False
        if int(vim.eval('buffer_exists("'+self.name+'")')) == 1:
            vim.command('bwipeout ' + self.name)

    def clean(self):
        """ clean all datas in buffer """
        self.buffer[:] = []

    def command(self, cmd):
        """ go to my window & execute command """
        winnr = self.getwinnr()
        if winnr != int(vim.eval("winnr()")):
            vim.command(str(winnr) + 'wincmd w')
        vim.command(cmd)

    def accept_renderer(self,renderer):
        self.write(renderer.render())

class BreakpointWindow(Window):
    name = "DebuggerBreakpoints"
    is_visible = False
    header = """===========================================================
 ID      | TYPE        | DATA
==========================================================="""

    def on_create(self):
        self.clean()
        self.write(self.header)
        self.command('setlocal syntax=debugger_breakpoint')
        for bp in self.ui.breakpoint_store.get_sorted_list():
            self.add_breakpoint(bp)
        if self.creation_count == 1:
            cmd = 'silent! au BufWinLeave %s :silent! bdelete %s' %(self.name,self.name)
            vim.command('%s | python debugger.runner.ui.breakpointwin.is_open = False' % cmd)

    def add_breakpoint(self,breakpoint):
        bp_str = " %-7i | %-11s | " %(breakpoint.id,breakpoint.type)
        if breakpoint.type == 'line':
            bp_str += "%s:%s" %(breakpoint.file,str(breakpoint.line))
        elif breakpoint.type == 'conditional':
            bp_str += "%s:%s when (%s)" \
                %(breakpoint.file,str(breakpoint.line),breakpoint.condition)
        elif breakpoint.type == 'exception':
            bp_str += "Exception: %s" % breakpoint.exception
        elif breakpoint.type == 'call' or \
                breakpoint.type == 'return':
            bp_str += "Function: %s" % breakpoint.function

        self.write(bp_str)

    def remove_breakpoint(self,breakpoint_id):
        i = 0
        for l in self.buffer:
            bp_str = " %i " % breakpoint_id
            bp_id_len = len(bp_str)
            if l[:bp_id_len] == bp_str:
                del self.buffer[i]
            i += 1

class LogWindow(Window):
    name = "DebuggerLog"

    def on_create(self):
        self.command('setlocal syntax=debugger_log')
        if self.creation_count == 1:
            vim.command('silent! au BufWinLeave %s :silent! bdelete %s' %(self.name,self.name))

    def write(self, msg, return_focus = True):
        Window.write(self, msg,return_focus=True)

class StackWindow(Window):
    name = "DebuggerStack"

    def on_create(self):
        self.command('inoremap <buffer> <cr> <esc>'+\
                ':python debugger.handle_return_keypress()<cr>')
        self.command('nnoremap <buffer> <cr> '+\
                ':python debugger.handle_return_keypress()<cr>')
        self.command('nnoremap <buffer> <2-LeftMouse> '+\
                ':python debugger.handle_double_click()<cr>')
        self.command('setlocal syntax=debugger_stack')
        if self.creation_count == 1:
            cmd = 'silent! au BufWinLeave %s :silent! bdelete %s' %(self.name,self.name)
            vim.command('%s | python debugger.runner.ui.stackwin.is_open = False' % cmd)

    def write(self, msg, return_focus = True):
        Window.write(self, msg, after="normal gg")

class WatchWindow(Window):
    name = "DebuggerWatch"

    def on_create(self):
        self.command('inoremap <buffer> <cr> <esc>'+\
                ':python debugger.handle_return_keypress()<cr>')
        self.command('nnoremap <buffer> <cr> '+\
                ':python debugger.handle_return_keypress()<cr>')
        self.command('nnoremap <buffer> <2-LeftMouse> '+\
                ':python debugger.handle_double_click()<cr>')
        self.command('setlocal syntax=debugger_watch')
        if self.creation_count == 1:
            cmd = 'silent! au BufWinLeave %s :silent! bdelete %s' %(self.name,self.name)
            vim.command('%s | python debugger.runner.ui.watchwin.is_open = False' % cmd)

    def write(self, msg, return_focus = True):
        Window.write(self, msg, after="normal gg")

class StatusWindow(Window):
    name = "DebuggerStatus"

    def on_create(self):
        keys = vdebug.util.Keymapper()
        output = "Status: starting\nListening on port\nNot connected\n\n"
        output += "Press %s to start debugging, " %(keys.run_key())
        output += "%s to stop/close. " %(keys.close_key())
        output += "Type :help Vdebug for more information."

        self.write(output)

        self.command('setlocal syntax=debugger_status')
        if self.creation_count == 1:
            cmd = 'au BufWinLeave %s :silent! bdelete %s' %(self.name,self.name)
            vim.command('%s | python debugger.runner.ui.statuswin.is_open = False' % cmd)

    def set_status(self,status):
        self.insert("Status: "+str(status),0,True)


class ResponseRenderer:
    def __init__(self,response):
        self.response = response

    def render(self):
        pass

class StackGetResponseRenderer(ResponseRenderer):
    def render(self):
        stack = self.response.get_stack()
        string = ""
        for s in stack:
            where = s.get('where') if s.get('where') else 'main'
            file = vdebug.util.FilePath(s.get('filename'))
            line = "[%(num)s] %(where)s @ %(file)s:%(line)s" \
                    %{'num':s.get('level'),'where':where,\
                    'file':str(file.as_local()),'line':s.get('lineno')}
            string += line + "\n"
        return string


class ContextGetResponseRenderer(ResponseRenderer):

    def __init__(self,response,title = None,contexts = {},current_context = 0):
        ResponseRenderer.__init__(self,response)
        self.title = title
        self.contexts = contexts
        self.current_context = current_context

    def render(self,indent = 0):
        res = self.__create_tabs()

        if self.title:
            res += "- %s\n\n" % self.title

        properties = self.response.get_context()
        num_props = len(properties)
        vdebug.log.Log("Writing %i properties to the context window" % num_props,\
                vdebug.log.Logger.INFO )
        for idx, prop in enumerate(properties):
            final = False
            try:
                next_prop = properties[idx+1]
            except IndexError:
                final = True
                next_prop = None
            res += self.__render_property(prop,next_prop,final,indent)

        vdebug.log.Log("Writing to context window:\n"+res,vdebug.log.Logger.DEBUG)

        return res

    def __create_tabs(self):
        res = []
        if self.contexts:
            for id,name in self.contexts.iteritems():
                if self.current_context == id:
                    name = "*"+name
                res.append("[ %s ]" % name)
        if res:
            return " ".join(res) + "\n\n"
        else:
            return ""

    def __render_property(self,p,next_p,last = False,indent = 0):
        line = "%(indent)s %(marker)s %(name)s = (%(type)s)%(value)s" \
                %{'indent':"".rjust((p.depth * 2)+indent),\
                'marker':self.__get_marker(p),'name':p.display_name.encode('latin1'),\
                'type':p.type_and_size(),'value': " " + p.value}
        line = line.rstrip() + "\n"

        if vdebug.opts.Options.get('watch_window_style') == 'expanded':
            depth = p.depth
            if next_p and not last:
                next_depth = next_p.depth
                if depth == next_depth:
                    next_sep = "|"
                    num_spaces = depth * 2
                elif depth > next_depth:
                    next_sep = "/"
                    num_spaces = (depth * 2) - 1
                else:
                    next_sep = "\\"
                    num_spaces = (depth * 2) + 1

                line += "".rjust(num_spaces+indent) + " " + next_sep + "\n"
            elif depth > 0:
                line += "".rjust((depth * 2) - 1 + indent) + " /" + "\n"
        return line

    def __get_marker(self,property):
        char = vdebug.opts.Options.get('marker_default')
        if property.has_children:
            if property.child_count() == 0:
                char = vdebug.opts.Options.get('marker_closed_tree')
            else:
                char = vdebug.opts.Options.get('marker_open_tree')
        return char

########NEW FILE########
__FILENAME__ = util
import vdebug.opts
import vdebug.log
import vim
import re
import os
import urllib
import time

class Keymapper:
    """Map and unmap key commands for the Vim user interface.
    """

    exclude = ["run","set_breakpoint","eval_visual"]

    def __init__(self):
        self._reload_keys()
        self.is_mapped = False
        self.existing = []

    def run_key(self):
        return self.keymaps['run']

    def close_key(self):
        return self.keymaps['close']

    def map(self):
        if self.is_mapped:
            return
        self._store_old_map()
        self._reload_keys()
        for func in self.keymaps:
            if func not in self.exclude:
                key = self.keymaps[func]
                map_cmd = "noremap %s%s :python debugger.%s()<cr>" %\
                    (self.leader,key,func)
                vim.command(map_cmd)
        self.is_mapped = True

    def _reload_keys(self):
        self.keymaps = vim.eval("g:vdebug_keymap")
        self.leader = vim.eval("g:vdebug_leader_key")

    def _store_old_map(self):
        vim.command('let tempfile=tempname()')
        tempfile = vim.eval("tempfile")
        vim.command('mkexrc! %s' % (tempfile))
        regex = re.compile(r'^([nvxsoilc]|)(nore)?map!?')
        split_regex = re.compile(r'\s+')
        keys = set(v for (k,v) in self.keymaps.items() if k not in self.exclude)
        special = set(["<buffer>", "<silent>", "<special>", "<script>", "<expr>", "<unique>"])
        for line in open(tempfile, 'r'):
            if not regex.match(line):
                continue
            parts = split_regex.split(line)[1:]
            for p in parts:
                if p in special:
                    continue
                elif p in keys:
                    vdebug.log.Log("Storing existing key mapping, '%s' " % line,
                                   vdebug.log.Logger.DEBUG)
                    self.existing.append(line)
                else:
                    break
        os.remove(tempfile)

    def unmap(self):
        if self.is_mapped:
            self.is_mapped = False

            for func in self.keymaps:
                key = self.keymaps[func]
                if func not in self.exclude:
                    vim.command("unmap %s%s" %(self.leader,key))
            for mapping in self.existing:
                vdebug.log.Log("Remapping key with '%s' " % mapping,\
                        vdebug.log.Logger.DEBUG)
                vim.command(mapping)

class FilePath:
    is_win = False

    """Normalizes a file name and allows for remote and local path mapping.
    """
    def __init__(self,filename):
        if filename is None or \
            len(filename) == 0:
            raise FilePathError("Missing or invalid file name")
        filename = urllib.unquote(filename)
        if filename.startswith('file:'):
            filename = filename[5:]
            if filename.startswith('///'):
                filename = filename[2:]

        p = re.compile('^/?[a-zA-Z]:')
        if p.match(filename):
            self.is_win = True
            if filename[0] == "/":
                filename = filename[1:]

        self.local = self._create_local(filename)
        self.remote = self._create_remote(filename)

    def _create_local(self,f):
        """Create the file name as a locally valid version.

        Uses the "local_path" and "remote_path" options.
        """
        ret = f
        if ret[2] == "/":
            ret = ret.replace("/","\\")

        if vdebug.opts.Options.isset('path_maps'):
            for remote, local in vdebug.opts.Options.get('path_maps', dict).items():
                if remote in ret:
                    vdebug.log.Log("Replacing remote path (%s) " % remote +\
                            "with local path (%s)" % local ,\
                            vdebug.log.Logger.DEBUG)
                    ret = ret.replace(remote,local)
                    break
        return ret

    def _create_remote(self,f):
        """Create the file name valid for the remote server.

        Uses the "local_path" and "remote_path" options.
        """
        ret = f

        if vdebug.opts.Options.isset('path_maps'):
            for remote, local in vdebug.opts.Options.get('path_maps', dict).items():
                if local in ret:
                    vdebug.log.Log("Replacing local path (%s) " % local +\
                            "with remote path (%s)" % remote ,\
                            vdebug.log.Logger.DEBUG)
                    ret = ret.replace(local,remote)
                    break

        if ret[2] == "\\":
            ret = ret.replace("\\","/")

        if self.is_win:
            return "file:///"+ret
        else:
            return "file://"+ret

    def as_local(self,quote = False):
        if quote:
            return urllib.quote(self.local)
        else:
            return self.local

    def as_remote(self):
        return self.remote

    def __eq__(self,other):
        if isinstance(other,FilePath):
            if other.as_local() == self.as_local():
                return True
        return False

    def __ne__(self,other):
        if isinstance(other,FilePath):
            if other.as_local() == self.as_local():
                return False
        return True

    def __add__(self,other):
        return self.as_local() + other

    def __radd__(self,other):
        return other + self.as_local()

    def __str__(self):
        return self.as_local()

    def __repr__(self):
        return str(self)

class LocalFilePath(FilePath):
    def _create_local(self,f):
        """Create the file name as a locally valid version.

        Uses the "local_path" and "remote_path" options.
        """
        return f

class RemoteFilePath(FilePath):
    def _create_remote(self,f):
        """Create the file name valid for the remote server.

        Uses the "local_path" and "remote_path" options.
        """
        return f

class FilePathError(Exception):
    pass

class InputStream:
    """Get a character from Vim's input stream.

    Used to check for keyboard interrupts."""

    def probe(self):
        try:
            vim.eval("getchar(0)")
            time.sleep(0.1)
        except: # vim.error
            raise UserInterrupt()

class UserInterrupt(Exception):
    """Raised when a user interrupts connection wait."""

########NEW FILE########
__FILENAME__ = test_breakpoint_breakpoint
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
import vdebug.breakpoint
import vdebug.util
import base64
from mock import Mock

class LineBreakpointTest(unittest.TestCase):

    def test_get_file(self):
        """ Test that the line number is retrievable."""
        ui = None
        file = "/path/to/file"
        line = 1
        bp = vdebug.breakpoint.LineBreakpoint(ui,file,line)
        self.assertEqual(bp.get_file(),file)

    def test_get_line(self):
        """ Test that the line number is retrievable."""
        ui = None
        file = "/path/to/file"
        line = 10
        bp = vdebug.breakpoint.LineBreakpoint(ui,file,line)
        self.assertEqual(bp.get_line(),line)

    def test_get_cmd(self):
        """ Test that the dbgp command is correct."""
        ui = None
        file = vdebug.util.FilePath("/path/to/file")
        line = 20
        bp = vdebug.breakpoint.LineBreakpoint(ui,file,line)
        self.assertEqual(bp.get_cmd(),"-t line -f file://%s -n %i -s enabled" %(file, line))

    def test_on_add_sets_ui_breakpoint(self):
        """ Test that the breakpoint is placed on the source window."""
        ui = Mock()
        file = vdebug.util.FilePath("/path/to/file")
        line = 20
        bp = vdebug.breakpoint.LineBreakpoint(ui,file,line)
        bp.on_add()
        ui.register_breakpoint.assert_called_with(bp)

    def test_on_remove_deletes_ui_breakpoint(self):
        """ Test that the breakpoint is removed from the source window."""
        ui = Mock()
        file = vdebug.util.FilePath("/path/to/file")
        line = 20
        bp = vdebug.breakpoint.LineBreakpoint(ui,file,line)
        bp.on_remove()
        ui.remove_breakpoint.assert_called_with(bp)

class ConditionalBreakpointTest(unittest.TestCase):
    def setUp(self):
        vdebug.opts.Options.set({})

    def test_get_cmd(self):
        """ Test that the dbgp command is correct."""
        ui = None
        file = vdebug.util.FilePath("/path/to/file")
        line = 20
        condition = "$x > 20"
        bp = vdebug.breakpoint.ConditionalBreakpoint(ui,file,line,condition)
        b64cond = base64.encodestring(condition)
        exp_cmd = "-t conditional -f file://%s -n %i -s enabled -- %s" %(file, line, b64cond)
        self.assertEqual(bp.get_cmd(), exp_cmd)

class ExceptionBreakpointTest(unittest.TestCase):
    def test_get_cmd(self):
        """ Test that the dbgp command is correct."""
        ui = None
        exception = "ExampleException"
        bp = vdebug.breakpoint.ExceptionBreakpoint(ui,exception)
        exp_cmd = "-t exception -x %s -s enabled" % exception
        self.assertEqual(bp.get_cmd(), exp_cmd)

class CallBreakpointTest(unittest.TestCase):
    def test_get_cmd(self):
        """ Test that the dbgp command is correct."""
        ui = None
        function = "myfunction"
        bp = vdebug.breakpoint.CallBreakpoint(ui,function)
        exp_cmd = "-t call -m %s -s enabled" % function
        self.assertEqual(bp.get_cmd(), exp_cmd)

class ReturnBreakpointTest(unittest.TestCase):
    def test_get_cmd(self):
        """ Test that the dbgp command is correct."""
        ui = None
        function = "myfunction"
        bp = vdebug.breakpoint.ReturnBreakpoint(ui,function)
        exp_cmd = "-t return -m %s -s enabled" % function
        self.assertEqual(bp.get_cmd(), exp_cmd)


class BreakpointTest(unittest.TestCase):

    def test_id_is_unique(self):
        """Test that each vdebug.breakpoint has a unique ID.

        Consecutively generated breakpoints should have
        different IDs."""
        bp1 = vdebug.breakpoint.Breakpoint(None)
        bp2 = vdebug.breakpoint.Breakpoint(None)

        self.assertNotEqual(bp1.get_id(),bp2.get_id())

    def test_parse_with_line_breakpoint(self):
        """ Test that a LineBreakpoint is created."""
        Mock.__len__ = Mock(return_value=1)
        ui = Mock()
        ret = vdebug.breakpoint.Breakpoint.parse(ui,"")
        self.assertIsInstance(ret,vdebug.breakpoint.LineBreakpoint)

    def test_parse_with_empty_line_raises_error(self):
        """ Test that a LineBreakpoint is created."""
        Mock.__len__ = Mock(return_value=0)
        ui = Mock()
        re = 'Cannot set a breakpoint on an empty line'
        self.assertRaisesRegexp(vdebug.breakpoint.BreakpointError,\
                re,vdebug.breakpoint.Breakpoint.parse,ui,"")

    def test_parse_with_conditional_breakpoint(self):
        """ Test that a ConditionalBreakpoint is created."""
        ui = Mock()
        ret = vdebug.breakpoint.Breakpoint.parse(ui,"conditional $x == 3")
        self.assertIsInstance(ret,vdebug.breakpoint.ConditionalBreakpoint)
        self.assertEqual(ret.condition, "$x == 3")

    def test_parse_with_conditional_raises_error(self):
        """ Test that an exception is raised with invalid conditional args."""
        ui = Mock()
        args = "conditional"
        re = "Conditional breakpoints require a condition "+\
                "to be specified"
        self.assertRaisesRegexp(vdebug.breakpoint.BreakpointError,\
                re, vdebug.breakpoint.Breakpoint.parse, ui, args)

    def test_parse_with_exception_breakpoint(self):
        """ Test that a ExceptionBreakpoint is created."""
        ui = Mock()
        ret = vdebug.breakpoint.Breakpoint.parse(ui,"exception ExampleException")
        self.assertIsInstance(ret,vdebug.breakpoint.ExceptionBreakpoint)
        self.assertEqual(ret.exception, "ExampleException")

    def test_parse_with_exception_raises_error(self):
        """ Test that an exception is raised with invalid exception args."""
        ui = Mock()
        args = "exception"
        re = "Exception breakpoints require an exception name "+\
                "to be specified"
        self.assertRaisesRegexp(vdebug.breakpoint.BreakpointError,\
                re, vdebug.breakpoint.Breakpoint.parse, ui, args)


    def test_parse_with_call_breakpoint(self):
        """ Test that a CallBreakpoint is created."""
        ui = Mock()
        ret = vdebug.breakpoint.Breakpoint.parse(ui,"call myfunction")
        self.assertIsInstance(ret,vdebug.breakpoint.CallBreakpoint)
        self.assertEqual(ret.function , "myfunction")

    def test_parse_with_call_raises_error(self):
        """ Test that an exception is raised with invalid call args."""
        ui = Mock()
        args = "call"
        re = "Call breakpoints require a function name "+\
                "to be specified"
        self.assertRaisesRegexp(vdebug.breakpoint.BreakpointError,\
                re, vdebug.breakpoint.Breakpoint.parse, ui, args)

    def test_parse_with_return_breakpoint(self):
        """ Test that a ReturnBreakpoint is created."""
        ui = Mock()
        ret = vdebug.breakpoint.Breakpoint.parse(ui,"return myfunction")
        self.assertIsInstance(ret,vdebug.breakpoint.ReturnBreakpoint)
        self.assertEqual(ret.function, "myfunction")

    def test_parse_with_return_raises_error(self):
        """ Test that an exception is raised with invalid return args."""
        ui = Mock()
        args = "return"
        re = "Return breakpoints require a function name "+\
                "to be specified"
        self.assertRaisesRegexp(vdebug.breakpoint.BreakpointError,\
                re, vdebug.breakpoint.Breakpoint.parse, ui, args)


########NEW FILE########
__FILENAME__ = test_dbgp_api
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
import vdebug.dbgp
from mock import MagicMock, patch

class ApiTest(unittest.TestCase):      
    """Test the Api class in the vdebug.dbgp module."""

    init_msg = """<?xml version="1.0"
        encoding="iso-8859-1"?>\n<init
        xmlns="urn:debugger_api_v1"
        xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
        fileuri="file:///usr/local/bin/cake" language="PHP"
        api_version="1.0" appid="30130"
        idekey="netbeans-xdebug"><engine
        version="2.2.0"><![CDATA[Xdebug]]></engine><author><![CDATA[Derick
        Rethans]]></author><url><![CDATA[http://xdebug.org]]></url><copyright><![CDATA[Copyright
        (c) 2002-2012 by Derick
        Rethans]]></copyright></init>"""

    def setUp(self):
        with patch('vdebug.dbgp.Connection') as c:
            self.c = c.return_value
            self.c.recv_msg.return_value = self.init_msg
            self.c.isconnected.return_value = 1
            self.p = vdebug.dbgp.Api(self.c)

    def test_init_msg_parsed(self):
        """Test that the init message from the debugger is
        parsed successfully"""
        assert self.p.language == "php"
        assert self.p.version == "1.0"
        assert self.p.idekey == "netbeans-xdebug"

    def test_status_send_adds_trans_id(self):
        """Test that the status command sends the right
        format command and adds a transaction ID"""
        self.p.conn.send_msg = MagicMock()
        self.p.status()
        self.p.conn.send_msg.assert_called_once_with('status -i 1')

    def test_status_retval(self):
        """Test that the status command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="status"
                      xmlns="urn:debugger_api_v1"
                      status="starting"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.status()
        assert str(status_res) == "starting"

    def test_run_retval(self):
        """Test that the run command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="run"
                      xmlns="urn:debugger_api_v1"
                      status="running"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "running"

    def test_step_into_retval(self):
        """Test that the step_into command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="step_into"
                      xmlns="urn:debugger_api_v1"
                      status="break"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "break"

    def test_step_over_retval(self):
        """Test that the step_over command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="step_into"
                      xmlns="urn:debugger_api_v1"
                      status="break"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "break"

    def test_step_out_retval(self):
        """Test that the step_out command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="step_into"
                      xmlns="urn:debugger_api_v1"
                      status="break"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "break"

    def test_stop_retval(self):
        """Test that the stop command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="stop"
                      xmlns="urn:debugger_api_v1"
                      status="stopping"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "stopping"

    def test_detatch_retval(self):
        """Test that the detatch command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n
            <response command="detatch"
                      xmlns="urn:debugger_api_v1"
                      status="stopped"
                      reason="ok"
                      transaction_id="transaction_id">
                message data
            </response>"""
        status_res = self.p.run()
        assert str(status_res) == "stopped"

    def test_feature_get_retval(self):
        """Test that the feature_get command receives a message from the api."""
        self.p.conn.recv_msg.return_value = """<?xml
            version="1.0" encoding="iso-8859-1"?>\n<response
            xmlns="urn:debugger_api_v1"
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
            command="feature_get" transaction_id="2"
            feature_name="encoding"
            supported="1"><![CDATA[iso-8859-1]]></response>"""
        res = self.p.feature_get('encoding')
        self.assertEqual(str(res),"iso-8859-1")
        self.assertEqual(res.is_supported(),1)

class apiInvalidInitTest(unittest.TestCase):

    init_msg = """<?xml version="1.0"
        encoding="iso-8859-1"?>\n<init
        xmlns="urn:debugger_api_v1"
        xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
        fileuri="file:///usr/local/bin/cake" language="PHP"
        api_version="1.0" appid="30130"
        idekey="netbeans-xdebug"><engine
        version="2.2.0"><![CDATA[Xdebug]]></engine><author><![CDATA[Derick
        Rethans]]></author><url><![CDATA[http://xdebug.org]]></url><copyright><![CDATA[Copyright
        (c) 2002-2012 by Derick
        Rethans]]></copyright></init>"""

    invalid_init_msg = """<?xml version="1.0"
        encoding="iso-8859-1"?>\n<invalid
        xmlns="urn:debugger_api_v1">\n</invalid>"""

    def test_invalid_response_raises_error(self):
        with patch('vdebug.dbgp.Connection') as c:
            c = c.return_value
            c.recv_msg.return_value = self.invalid_init_msg
            c.isconnected.return_value = 1
            re = "Invalid XML response from debugger"
            self.assertRaisesRegexp(vdebug.dbgp.ResponseError,re,vdebug.dbgp.Api,c)


########NEW FILE########
__FILENAME__ = test_dbgp_connection
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
import vdebug.dbgp

class SocketMockError():
    pass

class SocketMock():
    def __init__(self):
        self.response = []
        self.last_msg = None

    def recv(self,length):
        ret = self.response[0]
        if len(ret) >= length:
            chars = ret[0:length]
            newval = ret[length:]
            if len(newval) > 0:
                self.response[0] = newval
            else:
                self.response.pop(0)
            return "".join(chars)
        else:
            self.response.pop(0)
            return ''

    def add_response(self,res):
        res = str(res)
        self.response.append(list(res))
        self.response.append(['\0'])

    def send(self,msg):
        self.last_msg = msg

    def get_last_sent(self):
        return self.last_msg

    def close(self):
        pass


class ConnectionTest(unittest.TestCase):      

    def setUp(self):
        self.conn = vdebug.dbgp.Connection('', 0)
        self.conn.sock = SocketMock()

    """
    Test that the recv_msg method reads from the socket object.

    The socket's recv() method is called for three purposes
        1. Message length
        2. Message body
        3. A finishing null byte
    """
    def test_read(self):
        self.conn.sock.add_response(3)
        self.conn.sock.add_response('foo')
        self.conn.sock.add_response('\0')

        response = self.conn.recv_msg()
        assert response == 'foo'

    """
    Test a longer read.
    """
    def test_read_long(self):
        self.conn.sock.add_response(24)
        self.conn.sock.add_response('this is a longer message')
        self.conn.sock.add_response('\0')

        response = self.conn.recv_msg()
        assert response == 'this is a longer message'

    """
    Test that an EOFError is raised if the socket appears to be closed.
    """
    def test_read_eof(self):
        self.conn.sock.add_response('')
        self.assertRaises(EOFError,self.conn.recv_msg)

    """ 
    Test that the send_msg command calls send on the socket, 
    and adds a null byte to the string.
    """
    def test_send(self):
        cmd = 'this is a cmd'
        self.conn.send_msg(cmd)
        sent = self.conn.sock.get_last_sent()
        assert sent == cmd+'\0'

########NEW FILE########
__FILENAME__ = test_dbgp_context_property
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
import vdebug.dbgp
import xml.etree.ElementTree as ET

class ContextPropertyDefaultTest(unittest.TestCase):
    def __get_context_property(self,xml_string):
        xml = ET.fromstring(xml_string)
        firstnode = xml[0]
        return vdebug.dbgp.ContextProperty(firstnode)

    def test_single_property(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1"
xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
command="context_get" transaction_id="3"
context="0"><property name="$argc" fullname="$argc"
address="39795424"
type="int"><![CDATA[4]]></property></response>""")

        self.assertEqual(prop.display_name,'$argc')
        self.assertEqual(prop.value,'4')
        self.assertEqual(prop.type,'int')
        self.assertEqual(prop.depth,0)
        self.assertIsNone(prop.size)
        self.assertFalse(prop.has_children)

    def test_undefined_property(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1"
xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
command="context_get" transaction_id="3"
context="0"><property name="$uid"
fullname="$uid" type="uninitialized"></property></response>""")

        self.assertEqual(prop.display_name,'$uid')
        self.assertEqual(prop.value,'')
        self.assertEqual(prop.type,'uninitialized')
        self.assertEqual(prop.depth,0)
        self.assertIsNone(prop.size)
        self.assertFalse(prop.has_children)

    def test_child_properties(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1"
xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
command="context_get" transaction_id="3"
context="0"><property name="$argv"
fullname="$argv" address="39794056" type="array"
children="1" numchildren="4" page="0"
pagesize="32"><property name="0" fullname="$argv[0]"
address="39794368" type="string" size="19"
encoding="base64"><![CDATA[L3Vzci9sb2NhbC9iaW4vY2FrZQ==]]></property><property
name="1" fullname="$argv[1]" address="39794640"
type="string" size="8"
encoding="base64"><![CDATA[VGRkLnRlc3Q=]]></property><property
name="2" fullname="$argv[2]" address="39794904"
type="string" size="8"
encoding="base64"><![CDATA[LS1zdGRlcnI=]]></property><property
name="3" fullname="$argv[3]" address="39795168"
type="string" size="3"
encoding="base64"><![CDATA[QWxs]]></property></property></response>""")

        self.assertEqual(prop.display_name,'$argv')
        self.assertEqual(prop.value,'')
        self.assertEqual(prop.type,'array')
        self.assertEqual(prop.depth,0)
        self.assertTrue(prop.has_children)
        self.assertEqual(prop.child_count(),4)

class ContextPropertyAltTest(unittest.TestCase):
    def __get_context_property(self,xml_string):
        xml = ET.fromstring(xml_string)
        firstnode = xml[0]
        return vdebug.dbgp.ContextProperty(firstnode)

    def test_single_property(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1"
xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
command="context_get" transaction_id="3"
context="0"><property  type="int" children="0" size="0"><value><![CDATA[1]]></value><name encoding="base64"><![CDATA[bXl2YXI=
]]></name><fullname encoding="base64"><![CDATA[bXl2YXI=
]]></fullname></property></response>""")

        self.assertEqual(prop.display_name,'myvar')
        self.assertEqual(prop.value,'1')
        self.assertEqual(prop.type,'int')
        self.assertEqual(prop.depth,0)
        self.assertFalse(prop.has_children)

    def test_child_properties(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="utf-8"?>
<response xmlns="urn:debugger_protocol_v1" command="contex_get" context="0" transaction_id="13"><property  pagesize="10" numchildren="3" children="1" type="list" page="0" size="3"><property  type="int" children="0" size="0"><value><![CDATA[1]]></value><name encoding="base64"><![CDATA[WzBd
]]></name><fullname encoding="base64"><![CDATA[bXlsaXN0WzBd
]]></fullname></property><property  type="int" children="0" size="0"><value><![CDATA[2]]></value><name encoding="base64"><![CDATA[WzFd
]]></name><fullname encoding="base64"><![CDATA[bXlsaXN0WzFd
]]></fullname></property><property  type="int" children="0" size="0"><value><![CDATA[3]]></value><name encoding="base64"><![CDATA[WzJd
]]></name><fullname encoding="base64"><![CDATA[bXlsaXN0WzJd
]]></fullname></property><name encoding="base64"><![CDATA[bXlsaXN0
]]></name><fullname encoding="base64"><![CDATA[bXlsaXN0
]]></fullname></property></response>""")

        self.assertEqual(prop.display_name,'mylist')
        self.assertEqual(prop.value,'')
        self.assertEqual(prop.type,'list')
        self.assertEqual(prop.depth,0)
        self.assertTrue(prop.has_children)
        self.assertEqual(prop.child_count(),3)

    def test_string(self):
        prop = self.__get_context_property(\
            """<?xml version="1.0" encoding="utf-8"?>
<response xmlns="urn:debugger_protocol_v1" command="contex_get" context="0" transaction_id="13"><property  type="str" children="0" size="5"><value encoding="base64"><![CDATA[d29ybGQ=
]]></value><name encoding="base64"><![CDATA[b2JqX3Zhcg==
]]></name><fullname encoding="base64"><![CDATA[b2JqLm9ial92YXI=
]]></fullname></property></response>""")

        self.assertEqual(prop.display_name,'obj.obj_var')
        self.assertEqual(prop.value,'`world`')
        self.assertEqual(prop.type,'str')
        self.assertFalse(prop.has_children)


########NEW FILE########
__FILENAME__ = test_dbgp_response
import sys
if __name__ == "__main__":
    sys.path.append('../plugin/python/')
import unittest2 as unittest
import vdebug.dbgp
import xml
from mock import Mock

class ResponseTest(unittest.TestCase): 
    """Test the response class in the vdebug.dbgp module."""

    def test_get_cmd(self):
        """Test that the get_cmd() method returns the command"""
        cmd = "status"
        res = vdebug.dbgp.Response("",cmd,"",Mock())
        assert res.get_cmd() == cmd

    def test_get_cmd_args(self):
        """Test that the get_cmd_args() method return command arguments"""
        cmd_args = "-a abcd"
        res = vdebug.dbgp.Response("","",cmd_args,Mock())
        assert res.get_cmd_args() == cmd_args

    def test_as_string(self):
        """Test that the as_string() method returns the
        raw response string"""
        response = "<?xml..."
        res = vdebug.dbgp.Response(response,"","",Mock())
        assert res.as_string() == response

    def test_as_xml_is_element(self):
        if sys.version_info < (2, 7):
            return
        """Test that the as_xml() method returns an XML
        element"""
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1"
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug" 
            command="status" transaction_id="1" status="starting" 
            reason="ok"></response>"""
        res = vdebug.dbgp.Response(response,"","",Mock())
        self.assertIsInstance(res.as_xml(),xml.etree.ElementTree.Element)

    def test_error_tag_raises_exception(self):
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1" 
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
            command="stack_get" transaction_id="4"><error
            code="5"><message><![CDATA[command is not available]]>
            </message></error></response>"""
        re = "command is not available"
        self.assertRaisesRegexp(vdebug.dbgp.DBGPError,re,vdebug.dbgp.Response,response,"","",Mock())

class StatusResponseTest(unittest.TestCase): 
    """Test the behaviour of the StatusResponse class."""
    def test_string_is_status_text(self):
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1"
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug" 
            command="status" transaction_id="1" status="starting" 
            reason="ok"></response>"""
        res = vdebug.dbgp.StatusResponse(response,"","",Mock())
        assert str(res) == "starting"

class FeatureResponseTest(unittest.TestCase): 
    """Test the behaviour of the FeatureResponse class."""
    def test_feature_is_supported(self):
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1" 
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug" 
            command="feature_get" transaction_id="2" 
            feature_name="max_depth" supported="1"><![CDATA[1]]></response>"""
        res = vdebug.dbgp.FeatureGetResponse(response,"","",Mock())
        assert res.is_supported() == 1

    def test_feature_is_not_supported(self):
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1" 
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug" 
            command="feature_get" transaction_id="2" 
            feature_name="max_depth" supported="0"><![CDATA[0]]></response>"""
        res = vdebug.dbgp.FeatureGetResponse(response,"","",Mock())
        assert res.is_supported() == 0

class StackGetTest(unittest.TestCase): 
    """Test the behaviour of the StackGetResponse class."""
    def test_string_is_status_text(self):
        response = """<?xml version="1.0" encoding="iso-8859-1"?>
            <response xmlns="urn:debugger_protocol_v1" 
            xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
            command="stack_get" transaction_id="8">
                <stack where="{main}" level="0" type="file"
                filename="file:///usr/local/bin/cake" lineno="4">
                </stack>
            </response>"""
        res = vdebug.dbgp.StackGetResponse(response,"","",Mock())
        stack = res.get_stack()
        assert stack[0].get('filename') == "file:///usr/local/bin/cake"
        assert len(stack) == 1

class ContextGetTest(unittest.TestCase):
    response = """<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1"
xmlns:xdebug="http://xdebug.org/dbgp/xdebug"
command="context_get" transaction_id="3"
context="0"><property name="$argc" fullname="$argc"
address="39795424"
type="int"><![CDATA[4]]></property><property name="$argv"
fullname="$argv" address="39794056" type="array"
children="1" numchildren="4" page="0"
pagesize="32"><property name="0" fullname="$argv[0]"
address="39794368" type="string" size="19"
encoding="base64"><![CDATA[L3Vzci9sb2NhbC9iaW4vY2FrZQ==]]></property><property
name="1" fullname="$argv[1]" address="39794640"
type="string" size="8"
encoding="base64"><![CDATA[VGRkLnRlc3Q=]]></property><property
name="2" fullname="$argv[2]" address="39794904"
type="string" size="8"
encoding="base64"><![CDATA[LS1zdGRlcnI=]]></property><property
name="3" fullname="$argv[3]" address="39795168"
type="string" size="3"
encoding="base64"><![CDATA[QWxs]]></property></property><property
name="$cdstring" fullname="$cdstring"
type="uninitialized"></property><property name="$cdup"
fullname="$cdup" type="uninitialized"></property><property
name="$cwd" fullname="$cwd"
type="uninitialized"></property><property name="$dir"
fullname="$dir" type="uninitialized"></property><property
name="$dirs" fullname="$dirs"
type="uninitialized"></property><property name="$f"
fullname="$f" type="uninitialized"></property><property
name="$f_parts" fullname="$f_parts"
type="uninitialized"></property><property name="$f_user"
fullname="$f_user"
type="uninitialized"></property><property name="$i"
fullname="$i" type="uninitialized"></property><property
name="$idx" fullname="$idx"
type="uninitialized"></property><property name="$op"
fullname="$op" type="uninitialized"></property><property
name="$pass" fullname="$pass"
type="uninitialized"></property><property
name="$require_chown" fullname="$require_chown"
type="uninitialized"></property><property name="$retval"
fullname="$retval"
type="uninitialized"></property><property name="$tmp_files"
fullname="$tmp_files"
type="uninitialized"></property><property name="$uid"
fullname="$uid" type="uninitialized"></property><property
name="$user" fullname="$user"
type="uninitialized"></property></response>
"""

    def test_properties_are_objects(self):
        res = vdebug.dbgp.ContextGetResponse(self.response,"","",Mock())
        context = res.get_context()
        assert len(context) == 23
        self.assertIsInstance(context[0],vdebug.dbgp.ContextProperty)

    def test_int_property_attributes(self):
        res = vdebug.dbgp.ContextGetResponse(self.response,"","",Mock())
        context = res.get_context()
        prop = context[0]

        assert prop.display_name == "$argc"
        assert prop.type == "int"
        assert prop.value == "4"
        assert prop.has_children == False

    def test_array_property_attributes(self):
        res = vdebug.dbgp.ContextGetResponse(self.response,"","",Mock())
        context = res.get_context()
        prop = context[1]

        assert prop.display_name == "$argv"
        assert prop.type == "array"
        assert prop.value == ""
        assert prop.has_children == True
        assert prop.child_count() == 4

    def test_string_property_attributes(self):
        res = vdebug.dbgp.ContextGetResponse(self.response,"","",Mock())
        context = res.get_context()
        prop = context[2]

        assert prop.display_name == "$argv[0]"
        assert prop.type == "string"
        assert prop.value == "`/usr/local/bin/cake`"
        assert prop.has_children == False
        assert prop.size == "19"

class ContextGetAlternateTest(unittest.TestCase):
    response = """<?xml version="1.0" encoding="utf-8"?>
<response xmlns="urn:debugger_protocol_v1" command="context_get" context="0" transaction_id="15"><property  pagesize="10" numchildren="3" children="1" type="list" page="0" size="3"><name encoding="base64"><![CDATA[bXlsaXN0
]]></name><fullname encoding="base64"><![CDATA[bXlsaXN0
]]></fullname></property><property  type="int" children="0" size="0"><value><![CDATA[1]]></value><name encoding="base64"><![CDATA[bXl2YXI=
]]></name><fullname encoding="base64"><![CDATA[bXl2YXI=
]]></fullname></property><property  pagesize="10" numchildren="4" children="1" type="Example" page="0" size="0"><name encoding="base64"><![CDATA[b2Jq
]]></name><fullname encoding="base64"><![CDATA[b2Jq
]]></fullname></property></response>"""

    def test_properties_are_objects(self):
        res = vdebug.dbgp.ContextGetResponse(self.response,"","",Mock())
        context = res.get_context()
        assert len(context) == 3
        self.assertIsInstance(context[0],vdebug.dbgp.ContextProperty)


########NEW FILE########
__FILENAME__ = test_opts_options
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
from vdebug.opts import Options,OptionsError

class OptionsTest(unittest.TestCase):

    def tearDown(self):
        Options.instance = None

    def test_has_instance(self):
        Options.set({1:"hello",2:"world"})
        self.assertIsInstance(Options.inst(),Options)

    def test_get_option(self):
        Options.set({'foo':"hello",'bar':"world"})
        self.assertEqual("hello",Options.get('foo'))

    def test_get_option_as_type(self):
        Options.set({'foo':"1",'bar':"2"})
        opt = Options.get('foo',int)
        self.assertIsInstance(opt,int)
        self.assertEqual(1,opt)

    def test_option_is_not_set(self):
        Options.set({'foo':"",'bar':"2"})
        self.assertFalse(Options.isset("monkey"))

    def test_option_is_not_valid(self):
        Options.set({'foo':"",'bar':"2"})
        self.assertFalse(Options.isset("monkey"))

    def test_option_isset(self):
        Options.set({'foo':"",'bar':"2"})
        self.assertTrue(Options.isset("bar"))

    def test_uninit_raises_error(self):
        self.assertRaises(OptionsError,Options.isset,'something')

    def test_get_raises_error(self):
        Options.set({'foo':"1",'bar':"2"})
        self.assertRaises(OptionsError,Options.get,'something')

########NEW FILE########
__FILENAME__ = test_util_filepath
if __name__ == "__main__":
    import sys
    sys.path.append('../plugin/python/')
import unittest2 as unittest
""" Mock vim import """
import vdebug.opts
from vdebug.util import FilePath,FilePathError

class LocalFilePathTest(unittest.TestCase):

    def setUp(self):
        vdebug.opts.Options.set({'path_maps':{}})

    def test_as_local(self):
        filename = "/home/user/some/path"
        file = FilePath(filename)
        self.assertEqual(filename,file.as_local())

    def test_remote_prefix(self):
        prefix = "file://"
        filename = "/home/user/some/path"
        file = FilePath(prefix+filename)
        self.assertEqual(filename,file.as_local())

    def test_quoted(self):
        quoted = "file:///home/user/file%2etcl"
        file = FilePath(quoted)
        self.assertEqual("/home/user/file.tcl",file.as_local())

    def test_win(self):
        quoted = "file:///C:/home/user/file%2etcl"
        file = FilePath(quoted)
        self.assertEqual("C:\\home\\user\\file.tcl",file.as_local())

    def test_as_remote(self):
        filename = "/home/user/some/path"
        file = FilePath(filename)
        self.assertEqual("file://"+filename,file.as_remote())

    def test_eq(self):
        filename = "/home/user/some/path"
        file1 = FilePath(filename)
        file2 = FilePath(filename)
        assert file1 == file2

    def test_eq_false(self):
        filename1 = "/home/user/some/path"
        file1 = FilePath(filename1)
        filename2 = "/home/user/some/other/path"
        file2 = FilePath(filename2)
        self.assertFalse(file1 == file2)

    def test_neq(self):
        filename1 = "/home/user/some/path"
        file1 = FilePath(filename1)
        filename2 = "/home/user/some/other/path"
        file2 = FilePath(filename2)
        assert file1 != file2

    def test_neq_false(self):
        filename = "/home/user/some/path"
        file1 = FilePath(filename)
        file2 = FilePath(filename)
        self.assertFalse(file1 != file2)

    def test_add(self):
        filename = "/home/user/some/path"
        file = FilePath(filename)
        append = "/myfile.txt"
        assert (file + append) == (filename + append)

    def test_add_reverse(self):
        filename = "/user/some/path"
        file = FilePath(filename)
        prepend = "/home/"
        assert (prepend + file) == (prepend + filename)

    def test_empty_file_raises_error(self):
        self.assertRaises(FilePathError,FilePath,"")

class RemotePathTest(unittest.TestCase):
    def setUp(self):
        vdebug.opts.Options.set({'path_maps':{'remote1':'local1', 'remote2':'local2'}})

    def test_as_local(self):
        filename = "/remote1/path/to/file"
        file = FilePath(filename)
        self.assertEqual("/local1/path/to/file",file.as_local())

        filename = "/remote2/path/to/file"
        file = FilePath(filename)
        self.assertEqual("/local2/path/to/file",file.as_local())

    def test_as_local_with_uri(self):
        filename = "file:///remote1/path/to/file"
        file = FilePath(filename)
        self.assertEqual("/local1/path/to/file",file.as_local())

        filename = "file:///remote2/path/to/file"
        file = FilePath(filename)
        self.assertEqual("/local2/path/to/file",file.as_local())

    def test_as_local_does_nothing(self):
        filename = "/the/remote/path/to/file"
        file = FilePath(filename)
        self.assertEqual("/the/remote/path/to/file",file.as_local())

    def test_as_remote_with_unix_paths(self):
        filename = "/local1/path/to/file"
        file = FilePath(filename)
        self.assertEqual("file:///remote1/path/to/file",file.as_remote())

        filename = "file:///local2/path/to/file"
        file = FilePath(filename)
        self.assertEqual("file:///remote2/path/to/file",file.as_remote())

    def test_as_remote_with_win_paths(self):
        filename = "C:/local1/path/to/file"
        file = FilePath(filename)
        self.assertEqual("file:///C:/remote1/path/to/file",file.as_remote())

        filename = "file:///C:/local2/path/to/file"
        file = FilePath(filename)
        self.assertEqual("file:///C:/remote2/path/to/file",file.as_remote())

    def test_as_remote_with_backslashed_win_paths(self):
        filename = "C:\\local1\\path\\to\\file"
        file = FilePath(filename)
        self.assertEqual("file:///C:/remote1/path/to/file",file.as_remote())

        filename = "C:\\local2\\path\\to\\file"
        file = FilePath(filename)
        self.assertEqual("file:///C:/remote2/path/to/file",file.as_remote())

        filename = "C:/local2/path/to/file"
        file = FilePath(filename)
        self.assertEqual("C:\\local2\\path\\to\\file",file.as_local())

########NEW FILE########
__FILENAME__ = vim

class MockVim:
    pass

########NEW FILE########
__FILENAME__ = vdebugtests
import unittest2 as unittest
import sys

sys.path.append('tests')
sys.path.append('plugin/python')
vdebugLoader = unittest.TestLoader()
suites = vdebugLoader.discover('tests','test_*.py')
result = unittest.TextTestRunner().run(suites)
if result.failures:
    exit(1)
elif result.errors:
    exit(2)

########NEW FILE########
