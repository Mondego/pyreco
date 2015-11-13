__FILENAME__ = dispatcher
"""

m2wsgi.device.dispatcher:  general-purpose request dispatching hub
==================================================================


This is a device for receiving requests from mongrel2 and dispatching them
to handlers.  It's designed to give you more flexibility over routing than
using a raw PUSH socket.


Basic Usage
-----------

Suppose you have Mongrel2 pushing requests out to tcp://127.0.0.1:9999.
Instead of connecting your handlers directly to this socket, run the
dispatcher device like so::

    python -m m2wsgi.device.dispatcher \
              tcp://127.0.0.1:9999
              tcp://127.0.0.1:8888

Then you can launch your handlers against the device's output socket and have
them chat with it about their availability.  Make sure you specify the conn
type to m2wsgi::

    m2wsgi --conn-type=Dispatcher dotted.app.name tcp://127.0.0.1:8888

To make it worthwhile, you'll probably want to run several handler processes
connecting to the dispatcher.

One important use-case for the dispatcher is to implement "sticky sessions".
By passing the --sticky option, you ensure that all requests from a specific
connction will be routed to the same handler.

By default, handler stickiness is associated with mongrel2's internal client
id.  You can associated it with e.g. a session cookie by providing a regex
to extract the necessary information from the request.  The information from
any capturing groups in the regex forms the sticky session key.

Here's how you might implement stickiness based on a session cookie::

    python -m m2wsgi.device.dispatcher \
              --sticky-regex="SESSIONID=([A-Za-z0-9]+)"
              tcp://127.0.0.1:9999
              tcp://127.0.0.1:8888

Note that the current implementation of sticky sessions is based on consistent
hashing.  This has the advantage that multiple dispatcher devices can keep
their handler selection consistent without any explicit coordination; the
downside is that adding handlers will cause some sessions to be moved to the
new handler.



OK, but why?
------------

In the standard PULL-based protocol, each handler process connects with a PULL
socket and requests are sent round-robin to all connected handlers.  This is
great for throughput but has some limitations:

  * there's no way to control which requests get routed to which handler,
    e.g. to implement sticky sessions or coordinate large uploads.
  * there's no way for a handler to cleanly disconnect - if it goes offline 
    with pending requests queued to it, those requests can get dropped.

In the XREQ-based protocol offered by this device, each socket instead connects
with a XREQ socket.  When it's ready for work, the handler sends an explicit
message identifying itself and we start pushing it requests.

To effect a clean disconnect, the handler can send a special disconnect message
(the single byte "X") and this device will flush any queued requests, then
respond with an "X" request.  At this point the handler knows that no more
requests will be sent its way, and it can safely terminate.

The basic version of this device just routes reqeusts round-robin, and there's
a subclass that can implement basic sticky sessions.  More complex logic can
easily be built in a custom subclass.


Any Downsides?
--------------

Yes, a little.  The device is not notified when handlers die unexpectedly,
so it will keep sending them requests which are silently dropped by zmq.

To mitigate this the device sends periodic "ping" signals out via a PUB
socket.  Handlers that don't respond to a ping within a certain amount of
time are considered dead and dropped.  By default the ping triggers every
second.

Still working on a way to have the best of both worlds, but zmq doesn't want
to deliver any disconnection info to userspace.  The underlying socket has
a list of connected handlers at any given time, it just won't tell me
about it :-(

"""

import os
import re
import errno
import threading
from textwrap import dedent
from collections import deque

import zmq.core.poll

from m2wsgi.io.standard import Connection
from m2wsgi.util import CheckableQueue
from m2wsgi.util.conhash import ConsistentHash


class Dispatcher(object):
    """Device for dispatching requests to handlers."""

    def __init__(self,send_sock,recv_sock,disp_sock=None,ping_sock=None,
                      ping_interval=1):
        self.running = False
        if recv_sock is None:
            recv_sock = Connection.copysockspec(send_sock,-1)
            if recv_sock is None:
                raise ValueError("could not infer recv socket spec")
        if ping_sock is None:
            ping_sock = Connection.copysockspec(disp_sock,1)
            if ping_sock is None:
                raise ValueError("could not infer ping socket spec")
        if isinstance(send_sock,basestring):
            send_sock = Connection.makesocket(zmq.PULL,send_sock)
        if isinstance(recv_sock,basestring):
            recv_sock = Connection.makesocket(zmq.PUB,recv_sock)
        if isinstance(disp_sock,basestring):
            disp_sock = Connection.makesocket(zmq.XREP,disp_sock,bind=True)
        if isinstance(ping_sock,basestring):
            ping_sock = Connection.makesocket(zmq.PUB,ping_sock,bind=True)
        self.send_sock = send_sock
        self.recv_sock = recv_sock
        self.disp_sock = disp_sock
        self.ping_sock = ping_sock
        self.ping_interval = ping_interval
        self.pending_requests = deque()
        self.pending_responses = deque()
        #  The set of all active handlers is an opaque data type.
        #  Subclasses can use anything they want.
        self.active_handlers = self.init_active_handlers()
        #  Handlers that have been sent a ping and haven't yet sent a
        #  reply are "dubious".  Handlers that have sent a disconnect
        #  signal but haven't been sent a reply are "disconnecting".
        #  Anything else is "alive".
        self.dubious_handlers = set()
        self.disconnecting_handlers = CheckableQueue()
        self.alive_handlers = set()
        #  The state of our ping cycle.
        #  0:  quiescent; no requests, all handlers dubious
        #  1:  need to send a new ping
        #  2:  ping sent, ping timeout alarm pending
        #  3:  ping timeout alarm fired, needs action
        self.ping_state = 0
        #  We implement the ping timer by having a background thread
        #  write into this pipe for each 'ping'.  This avoids having
        #  to constantly query the current time and calculate timeouts.
        #  We could do this with SIGALRM but it would preclude using the
	#  device as part of a larger program.
        (self.ping_pipe_r,self.ping_pipe_w) = os.pipe()
        self.ping_thread = None
        self.ping_cond = threading.Condition()

    def close(self):
        """Shut down the device, closing all its sockets."""
        #  Stop running, waking up the select() if necessary.
        self.running = False
        os.write(self.ping_pipe_w,"X")
        #  Close the ping pipe, then shut down the background thread.
        (r,w) = (self.ping_pipe_r,self.ping_pipe_w)
        (self.ping_pipe_r,self.ping_pipe_w) = (None,None)
        os.close(r)
        os.close(w)
        if self.ping_thread is not None:
            with self.ping_cond:
                self.ping_cond.notify()
            self.ping_thread.join()
        #  Now close down all our zmq sockets
        self.ping_sock.close()
        self.disp_sock.close()
        self.send_sock.close()
        self.recv_sock.close()

    def _run_ping_thread(self):
        """Background thread that periodically wakes up the main thread.

        This code is run in a background thread.  It periodically wakes
        up the main thread by writing to self.ping_pipe_w.  We do things
        this way so that the main thread doesn't have to constantly query
        the current time and calculate timeouts.
        """
        #  Each time the main thread wants to trigger a ping, it will
        #  notify on self.ping_cond to wake us up.  Otherwise we'd
        #  never go to sleep when no requests are coming in.
        with self.ping_cond:
            while self.running:
                self.ping_cond.wait()
                #  Rather than using time.sleep(), we do a select-with-timeout
                #  on the ping pipe so that any calls to close() will wake us
                #  up immediately.
                socks = [self.ping_pipe_r]
                if socks[0] is None:
                    break
                zmq.core.poll.select(socks,[],socks,timeout=self.ping_interval)
                self._trigger_ping_alarm()
                self.ping_state = 3
                                     
    def _trigger_ping_alarm(self):
        """Trigger the ping alarm by writing to self.ping_pipe_w."""
        w = self.ping_pipe_w
        if w is not None:
            try:
                os.write(w,"P")
            except EnvironmentError:
                pass

    def run(self):
        """Run the socket handling loop."""
        self.running = True
        #  Send an initial ping, to activate any handlers that have
        #  already started up before us.
        while not self.send_ping() and self.running:
            zmq.core.select.poll([self.ping_pipe_r],[self.ping_sock],[])
        #  Run the background thread that interrupts us whenever we
        #  need to process a ping.
        self.ping_thread = threading.Thread(target=self._run_ping_thread)
        self.ping_thread.start()
        #  Enter the dispatch loop.
        #  Any new handlers that come online will introduce themselves
        #  by sending us an empty message, or at the very least will
        #  be picked up on the next scheduled ping.
        while self.running:
            ready = self.poll()
            #  If we're quiescent and there are requests ready, go
            #  to active pinging of handlers.
            if self.ping_state == 0:
                if self.send_sock in ready or self.pending_requests:
                    self.ping_state = 1
            #  If we need to send a ping but there's no work to do, go
            #  quiescent instead of waking everyone up.
            elif self.ping_state == 1:
                if not self.has_active_handlers():
                    self.ping_state = 0
                elif not self.alive_handlers:
                    if self.send_sock not in ready:
                        if not self.pending_requests:
                            self.ping_state = 0
            #  If we need to send a ping, try to do so.  This might fail
            #  if the socket isn't ready for it, so we retry on next iter.
            #  If successful, schedule a ping alarm.
            if self.ping_state == 1:
                if self.send_ping():
                    with self.ping_cond:
                        self.ping_state = 2
                        self.ping_cond.notify()
            #  When the ping alarm goes, any dubious handlers get dropped
            #  and any alive handlers get marked as dubious.  We will send
            #  them a new ping message and they must respond before the next
            #  ping alarm to stay active.
            if self.ping_state == 3:
                os.read(self.ping_pipe_r,1)
                for handler in self.dubious_handlers:
                    try:
                        self.rem_active_handler(handler)
                    except ValueError:
                        pass
                self.dubious_handlers = self.alive_handlers
                self.alive_handlers = set()
                self.ping_state = 1
            #  Disconnect any handlers that are waiting for it.
            if self.disconnecting_handlers:
                self.send_disconnect_messages()
            #  Forward any response data back to mongrel2.
            if self.disp_sock in ready or self.pending_responses:
                self.read_handler_responses()
            #  If we have some active handlers, we can dispatch a request.
            #  Note that we only send a single request then re-enter
            #  this loop, to give other handlers a chance to wake up.
            if self.has_active_handlers():
                req = self.get_pending_request()
                if req is not None:
                    try:
                        if not self.dispatch_request(req):
                            self.pending_requests.append(req)
                    except Exception:
                        self.pending_requests.append(req)
                        raise
            #  Otherwise, try to get one into memory so we know that
            #  we should be pinging handlers.
            elif not self.pending_requests:
                req = self.get_pending_request()
                if req is not None:
                    self.pending_requests.append(req)

    def poll(self):
        """Get the sockets that are ready for reading.

        Which sockets we poll depends on what state we're in.
        We don't want to e.g. constantly wake up due to pending
        requests when we don't have any handlers to deal with them.
        """
        #  Always poll for new responses from handlers, and
        #  for ping timeout alarms.
        rsocks = [self.disp_sock,self.ping_pipe_r]
        wsocks = []
        try:
            #  Poll for new requests if we have handlers ready, or if
            #  we have no pending requests.
            if self.has_active_handlers() or not self.pending_requests:
                rsocks.append(self.send_sock)
            #  Poll for ability to send requests if we have some queued
            if self.pending_requests and self.has_active_handlers():
                wsocks.append(self.disp_sock)
            #  Poll for ability to send shutdown acks if we have some queued
            if self.disconnecting_handlers:
                if self.disp_sock not in wsocks:
                    wsocks.append(self.disp_sock)
            #  Poll for ability to send responses if we have some pending
            if self.pending_responses:
                wsocks.append(self.recv_sock)
            #  Poll for writability of ping socket if we must ping
            if self.ping_state == 1:
                wsocks.append(self.ping_sock)
            #  OK, we can now actually poll.
            (ready,_,_) = zmq.core.poll.select(rsocks,wsocks,[])
            return ready
        except zmq.ZMQError, e:
            if e.errno not in (errno.EINTR,):
                raise
            return []

    def init_active_handlers(self):
        """Initialise and return the container for active handlers.

        By default this is a CheckableQueue object.  Subclasses can override
        this method to use a different container datatype.
        """
        return CheckableQueue()

    def has_active_handlers(self):
        """Check whether we have any active handlers.

        By default this calls bool(self.active_handlers).  Subclasses can
        override this method if they use a strange container datatype.
        """
        return bool(self.active_handlers)

    def rem_active_handler(self,handler):
        """Remove the given handler from the list of active handlers.

        Subclasses may need to override this if they are using a custom
        container type for the active handlers, and it doesn't have a 
        remove() method.
        """
        self.active_handlers.remove(handler)

    def add_active_handler(self,handler):
        """Add the given handler to the list of active handlers.

        Subclasses may need to override this if they are using a custom
        container type for the active handlers, and it doesn't have an
        append() method.
        """
        self.active_handlers.append(handler)

    def is_active_handler(self,handler):
        """Check whether the given handler is in the list of active handlers.

        Subclasses may need to override this if they are using a custom
        container type that doesn't support __contains__.
        """
        return (handler in self.active_handlers)

    def send_ping(self):
        """Send a ping to all listening handlers.

        This asks them to check in with the dispatcher, so we can get their
        address and start sending them requests.  It might fail is the
        ping socket isn't ready; returns bool indicating success.
        """
        try:
            self.ping_sock.send("",zmq.NOBLOCK)
            return True
        except zmq.ZMQError, e:
            if e.errno not in (errno.EINTR,zmq.EAGAIN,):
                raise
            return False

    def send_disconnect_messages(self):
        """Send disconnection messages to anyone who needs it.

        This will give the handler a chance to either report back that
        it's still alive, or terminate cleanly.
        """
        try:
            handler = None
            while True:
                handler = self.disconnecting_handlers.popleft()
                self.disp_sock.send(handler,zmq.SNDMORE|zmq.NOBLOCK)
                self.disp_sock.send("",zmq.SNDMORE|zmq.NOBLOCK)
                self.disp_sock.send("X",zmq.NOBLOCK)
                try:
                    self.rem_active_handler(handler)
                except ValueError:
                    pass
                handler = None
        except zmq.ZMQError, e:
            if handler is not None:
                self.disconnecting_handlers.append(handler)
            if e.errno not in (errno.EINTR,zmq.EAGAIN,):
                raise
        except IndexError:
            pass
        
    def read_handler_responses(self):
        """Read responses coming in from handlers.

        This might be heartbeat messages letting us know the handler is
        still alive, explicit disconnect messages, or response data to
        forward back to mongrel2.
        """
        try:
            while True:
                if self.pending_responses:
                    resp = self.pending_responses.popleft()
                    handler = None
                else:
                    resp = None
                    handler = self.disp_sock.recv(zmq.NOBLOCK)
                    delim = self.disp_sock.recv(zmq.NOBLOCK)
                    assert delim == "", "non-empty msg delimiter: "+delim
                    resp = self.disp_sock.recv(zmq.NOBLOCK)
                if resp == "X":
                    self.mark_handler_disconnecting(handler)
                else:
                    if handler is not None:
                        self.mark_handler_alive(handler)
                    if resp:
                        self.recv_sock.send(resp,zmq.NOBLOCK)
                    resp = None
        except zmq.ZMQError, e:
            if resp is not None:
                self.pending_responses.appendleft(resp)
            if e.errno not in (errno.EINTR,zmq.EAGAIN,):
                raise

    def mark_handler_disconnecting(self,handler):
        """Mark the given handler as disconncting.

        We'll try to send it a disconnect message as soon as possible.
        """
        self.disconnecting_handlers.append(handler)
        try:
           self.alive_handlers.remove(handler)
        except KeyError:
            pass
        try:
           self.dubious_handlers.remove(handler)
        except KeyError:
            pass

    def mark_handler_alive(self,handler):
        """Mark the given handler as alive.

        This means we can dispatch requests to this handler and have a
        reasonable chance of them being handled.
        """
        if not self.is_active_handler(handler):
            self.add_active_handler(handler)
        self.alive_handlers.add(handler)
        try:
           self.dubious_handlers.remove(handler)
        except KeyError:
            pass
        try:
           self.disconnecting_handlers.remove(handler)
        except ValueError:
            pass

    def get_pending_request(self):
        """Get a pending request, or None is there's nothing pending."""
        if self.pending_requests:
            return self.pending_requests.popleft()
        try:
            return self.send_sock.recv(zmq.NOBLOCK)
        except zmq.ZMQError, e:
            if e.errno not in (errno.EINTR,zmq.EAGAIN,):
                raise
        return None

    def dispatch_request(self,req):
        """Dispatch a single request to an active handler.

        The default implementation iterates throught the handlers in a
        round-robin fashion.  For more sophisticated routing logic you
        might override this method to do e.g. consistent hashing based
        on a session cookie.

        Returns True if the request was successfully dispatched, False
        otherwise (and the dispatcher will keep it in memory to try again).
        """
        try:
            while True:
                handler = self.active_handlers.popleft()
                try:
                    return self.send_request_to_handler(req,handler)
                finally:
                    self.active_handlers.append(handler)
        except IndexError:
            return False

    def send_request_to_handler(self,req,handler):
        """Send the given request to the given handler."""
        try:
            self.disp_sock.send(handler,zmq.SNDMORE|zmq.NOBLOCK)
            self.disp_sock.send("",zmq.SNDMORE|zmq.NOBLOCK)
            self.disp_sock.send(req,zmq.NOBLOCK)
            return True
        except zmq.ZMQError, e:
            if e.errno not in (errno.EINTR,zmq.EAGAIN,):
                raise
            return False


class StickyDispatcher(Dispatcher):
    """Dispatcher implementing sticky sessions using consistent hashing.

    This is Dispatcher subclass tries to route the same connection to the
    same handler across multiple requests, by selecting the handler based
    on a consistent hashing algorithm.

    By default the handler is selected based on the connection id.  You
    can override this by providing a regular expression which will be run
    against each request; the contents of all capturing groups will become
    the handler selection key.
    """

    def __init__(self,send_sock,recv_sock,disp_sock=None,ping_sock=None,
                      ping_interval=1,sticky_regex=None):
        if sticky_regex is None:
            #  Capture connid from "svrid conid path headers body"
            sticky_regex = r"^[^\s]+ ([^\s]+ )"
        if isinstance(sticky_regex,basestring):
            sticky_regex = re.compile(sticky_regex)
        self.sticky_regex = sticky_regex
        super(StickyDispatcher,self).__init__(send_sock,recv_sock,disp_sock,
                                              ping_sock,ping_interval)

    def init_active_handlers(self):
        return ConsistentHash()

    def has_active_handlers(self):
        return bool(self.active_handlers)

    def add_active_handler(self,handler):
        self.active_handlers.add_target(handler)

    def rem_active_handler(self,handler):
        try:
            self.active_handlers.rem_target(handler)
        except (KeyError,):
            pass

    def is_active_handler(self,handler):
        return self.active_handlers.has_target(handler)

    def dispatch_request(self,req):
        #  Extract sticky key using regex
        m = self.sticky_regex.search(req)
        if m is None:
            key = req
        elif m.groups():
            key = "".join(m.groups())
        else:
            key = m.group(0)
        #  Select handler based on sticky key
        handler = self.active_handlers[key]
        return self.send_request_to_handler(req,handler)


if __name__ == "__main__":
    import optparse
    op = optparse.OptionParser(usage=dedent("""
    usage:  m2wsgi.device.dispatcher [options] send_spec [recv_spec] disp_spec [ping_spec]
    """))
    op.add_option("","--ping-interval",type="int",default=1,
                  help="interval between handler pings")
    op.add_option("","--sticky",action="store_true",
                  help="use sticky client <-a >handler pairing")
    op.add_option("","--sticky-regex",
                  help="regex for extracting sticky connection key")
    (opts,args) = op.parse_args()
    if opts.sticky_regex:
        opts.sticky = True
    if len(args) == 2:
        args = [args[0],None,args[1]]
    kwds = opts.__dict__
    if kwds.pop("sticky",False):
        d = StickyDispatcher(*args,**kwds)
    else:
        kwds.pop("sticky_regex",None)
        d = Dispatcher(*args,**kwds)
    try:
        d.run()
    finally:
        d.close()


########NEW FILE########
__FILENAME__ = response
"""

m2wsgi.device.response:  device for sending a canned response
=============================================================


This is a simple device for sending a canned response to all requests.
You might use it for e.g. automatically redirecting based on host or route
information.   Use it like so::

    #  Redirect requests to canonical domain
    python -m m2wsgi.device.response \
              --code=302
              --status="Moved Permanently"\
              --header-Location="http://www.example.com%(PATH)s"
              --body="Redirecting to http://www.example.com\r\n"
              tcp://127.0.0.1:9999


Some things to note:

    * you can separately specify the status code, message, headers and body.

    * the body and headers can contain python string-interpolation patterns,
      which will be filled in with values from the request headers.

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


import sys
import traceback

from m2wsgi.io.standard import Connection


def response(conn,code=200,status="OK",headers={},body=""):
    """Run the response device."""
    if isinstance(conn,basestring):
        conn = Connection(conn)
    status_line = "HTTP/1.1 %d %s\r\n" % (code,status,)
    while True:
        req = conn.recv()
        try:
            prefix = req.headers.get("PATTERN","").split("(",1)[0]
            req.headers["PREFIX"] = prefix
            req.headers["MATCH"] = req.headers.get("PATH","")[len(prefix):]
            req.headers.setdefault("host","")
            req.respond(status_line)
            for (k,v) in headers.iteritems():
                req.respond(k)
                req.respond(": ")
                req.respond(v % req.headers)
                req.respond("\r\n")
            rbody = body % req.headers
            req.respond("Content-Length: %d\r\n\r\n" % (len(rbody),))
            if rbody:
                req.respond(rbody)
        except Exception:
            req.disconnect()
            traceback.print_exc()


if __name__ == "__main__":
    #  We're doing our own option parsing so we can handle
    #  arbitrary --header-<HEADER> options.  It's really not so hard...
    def help():
        sys.stderr.write(dedent("""
        usage:  m2wsgi.device.response [options] send_spec [recv_spec]

            --code=CODE     the status code to send
            --status=MSG    the status message to send
            --header-K=V    a key/value header pair to send
            --body=BODY     the response body to send

        """))
    kwds = {}
    conn_kwds = {}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if not arg.startswith("-"):
            break
        if arg.startswith("--code="):
            kwds["code"] = int(arg.split("=",1)[1])
        elif arg.startswith("--status="):
            kwds["status"] = arg.split("=",1)[1]
        elif arg.startswith("--header-"):
            (k,v) = arg[len("--header-"):].split("=",1)
            kwds.setdefault("headers",{})[k] = v
        elif arg.startswith("--body="):
            kwds["body"] = arg.split("=",1)[1]
        else:
            raise ValueError("unknown argument: %r" % (arg,))
        i += 1
    args = sys.argv[i:]
    if len(args) < 1:
        raise ValueError("response expects at least one argument")
    if len(args) > 2:
        raise ValueError("response expects at most two argument")
    conn = Connection(*args)
    response(conn,**kwds)


########NEW FILE########
__FILENAME__ = base
"""

m2wsgi.bio.base:  abstract base I/O classes for m2wsgi
======================================================

This module contains the base implementations of various m2wsgi classes.
Many of them are abstract, so don't use this module directly.
We have the following classes:

    :Connection:     represents the connection from your handler to Mongrel2,
                     through which you can read requests and send responses.

    :Client:         represents a client connected to the server, to whom you
                     can send data at any time.

    :Request:        represents a client request to which you can send
                     response data to at any time.

    :Handler:        a base class for implementing handlers, with nothing
                     WSGI-specific in it.

    :WSGIHandler:    a handler subclass specifically running a WSGI app.


    :WSGIResponder:  a class for managing the stateful aspects of a WSGI
                     response (status line, write callback, etc).

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.

import os
import sys
import re
import json
import time
import traceback
from collections import deque
from cStringIO import StringIO
from email.utils import formatdate as rfc822_format_date

import zmq

from m2wsgi.util import pop_tnetstring, unquote_path, unquote
from m2wsgi.util import InputStream, force_ascii


class Client(object):
    """Mongrel2 client connection object.

    Instances of this object represent a client connected to the Mongrel2
    server.  They encapsulate the server id and client connection id, and
    provide some handy methods to send data to the client.
    """

    def __init__(self,connection,server_id,client_id):
        self.connection = connection
        self.server_id = server_id
        self.client_id = client_id

    def __hash__(self):
        return hash((self.connection,self.server_id,self.client_id))

    def __eq__(self,other):
        if self.connection != other.connection:
            return False
        if self.server_id != other.server_id:
            return False
        if self.client_id != other.client_id:
            return False
        return True

    def __ne__(self,other):
        return not (self == other)

    def send(self,data):
        """Send some data to this client."""
        self.connection.send(self,data)

    def disconnect(self):
        """Terminate this client connection."""
        self.connection.send(self,"")


class Request(object):
    """Mongrel2 request object.

    This is a simple container object for the data in a Mongrel2 request.
    It can be used to poke around in the headers or body of the request,
    and to send replies to the request.
    """

    def __init__(self,client,path,headers,body):
        self.client = client
        self.path = path
        self.headers = headers
        self.body = body

    def __eq__(self,other):
        if self.client != other.client:
            return False
        if self.path != other.path:
            return False
        if self.headers != other.headers:
            return False
        if self.body != other.body:
            return False
        return True

    def __ne__(self,other):
        return not (self == other)

    @classmethod
    def parse(cls,client,msg):
        """Parse a Request out of a (partial) Mongrel2 message.

        This is an alternate constructor for the class, which takes the
        client object and the leftover parts of the Mongrel2 message and
        constructs a Request from that.
        """
        (path,rest) = msg.split(" ",1)
        (headers,rest) = pop_tnetstring(rest)
        (body,_) = pop_tnetstring(rest)
        if isinstance(headers,basestring):
            headers = force_ascii(json.loads(headers))
        return cls(client,path,headers,body)

    def respond(self,data):
        """Send some response data to the issuer of this request."""
        self.client.send(data)

    def disconnect(self):
        """Terminate the connection associated with this request."""
        self.client.disconnect()


class SocketSpec(object):
    """A specification for creating a socket.

    Instances of this class represent the information needed when specifying
    a socket, which may include:

        * socket address (zmq transport protocol and endpoint)
        * socket identity
        * whether to bind() or connect()

    To allow easy use in command-line applications, each SocketSpec has a
    canonical representation as a string in the following format::

        [protocol]://[identity]@[endpoint]#[connect or bind]

    For example, an anonymous socket binding to tcp 127.0.0.1 on port 999
    would be specified like this:

        tcp://127.0.0.1:999#bind

    While an ipc socket with identity "RILEY" connecting to path /my/sock
    would be specified like this:

        ipc://RILEY@/my/sock#connect

    Note that we don't use urlparse for this because it's got its own ideas
    about what protocols support for features of a URL, and they don't agree
    with our needs.
    """

    SPEC_RE = re.compile("""^
                            (?P<protocol>[a-zA-Z]+)
                            ://
                            ((?P<identity>[^@]*)@)?
                            (?P<endpoint>[^\#]+)
                            (\#(?P<mode>[a-zA-Z]*))?
                            $
                         """,re.X)

    def __init__(self,address,identity=None,bind=False):
        self.address = address
        self.identity = identity
        self.bind = bind

    @classmethod
    def parse(cls,str,default_bind=False):
        m = cls.SPEC_RE.match(str)
        if not m:
            raise ValueError("invalid socket spec: %s" % (str,))
        address = m.group("protocol") + "://" + m.group("endpoint")
        identity = m.group("identity")
        bind = m.group("mode")
        if not bind:
            bind = default_bind
        else:
            bind = bind.lower()
            if bind == "bind":
                bind = True
            elif bind == "connect":
                bind = False
            else:
                bind = default_bind
        return cls(address,identity,bind)

    def __str__(self):
        s = self.address
        if self.identity:
             (tr,ep) = self.address.split("://",1)
             s = "%s://%s@%s" % (tr,self.identity,ep,)
        if self.bind:
            s += "#bind"
        return s
 

class ConnectionBase(object):
    """Base class for Mongrel2 connection objects.

    Instances of ConnectionBase represent a handler's connection to the main
    Mongrel2 server(s).  They are used to receive requests and send responses.

    You generally don't want a direct instance of ConnectionBase; use one of
    the subclasses such as Connection or DispatcherConnection.  You might
    also like to make your own subclass by overriding the following methods:

        _poll:       block until sockets are ready for reading
        _interrupt:  interrupt any blocking calls to poll()
        _recv:       receive a request message from the server
        _send:       send response data to the server
        shutdown:    cleanly disconnect from the server

    """

    ZMQ_CTX = zmq.Context()

    ClientClass = Client
    RequestClass = Request

    def __init__(self):
        self.recv_buffer = deque()
        self._has_shutdown = False

    @classmethod
    def makesocket(cls,type,spec=None,bind=False):
        """Make a new socket of given type, according to the given spec.

        This method is used for easy creation of sockets from a string
        description.  It's used internally by ConnectionBase subclasses
        if they are given a string instead of a socket, and you can use
        it externally to create sockets for them.
        """
        sock = cls.ZMQ_CTX.socket(type)
        if spec is not None:
            if isinstance(spec,basestring):
                spec = SocketSpec.parse(spec,default_bind=bind)
            if spec.identity:
                sock.setsockopt(zmq.IDENTITY,spec.identity)
            if spec.address:
                if spec.bind:
                    sock.bind(spec.address)
                else:
                    sock.connect(spec.address)
        return sock

    @classmethod
    def copysockspec(cls,in_spec,relport):
        """Copy the given socket spec, adjust port.

        This is useful for filling in defaults, e.g. inferring the recv
        spec from the send spec.
        """
        if not isinstance(in_spec,basestring):
            return None
        try:
            (in_head,in_port) = in_spec.rsplit(":",1)
            if "#" not in in_port:
                in_tail = None
            else:
                (in_port,in_tail) = in_port.split("#",1)
            out_port = str(int(in_port) + relport)
            out_spec = in_head + ":" + out_port
            if in_tail is not None:
                out_spec += "#" + in_tail
            return out_spec
        except (ValueError,TypeError,IndexError):
            return None

    def recv(self,timeout=None):
        """Receive a request from the send socket.

        This method receives a request from the send socket, parses it into
        a Request object and returns it.
 
        You may specify the keyword argument 'timeout' to specify the max
        number of seconds to block.  Zero means non-blocking and None means
        blocking indefinitely.  If the timeout expires without a request
        being available, None is returned.
        """
        if self.recv_buffer:
            msg = self.recv_buffer.popleft()
        else:
            try:
                msg = self._recv(timeout=timeout)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    if not self._has_shutdown:
                        raise
                    if e.errno not in (zmq.ENOTSUP,zmq.EFAULT,):
                        raise
                return None
            else:
                if msg is None:
                    return None
        #  Parse out the request object and return.
        (server_id,client_id,rest) = msg.split(' ', 2)
        client = self.ClientClass(self,server_id,client_id)
        return self.RequestClass.parse(client,rest)

    def _recv(self,timeout=None):
        """Internal method for receving a message.

        This method must be implemented by subclasses.  It should retrieve
        a request message and return it, or return None if it times out.
        It's OK for it to raise EAGAIN, this will be captured up the chain.
        """
        raise NotImplementedError

    def _send(self,server_id,client_ids,data):
        """Internal method to send out response data."""
        raise NotImplementedError

    def _poll(self,sockets,timeout=None):
        """Poll the given sockets, waiting for one to be ready for reading.

        This method must be implemented by subclasses.  It should block until
        one of the sockets and/or file descriptors in 'sockets' is ready for
        reading, until the optional timeout has expired, or until someone calls
        the interrupt() method.

        Typically this would be a wrapper around zmq.core.poll.select, with
        whatever logic is necessary to allow interrupts from another thread.
        """
        raise NotImplementedError

    def _interrupt(self):
        """Internal method for interrupting a poll.

        This method must be implemented by subclasses.  It should cause any
        blocking calls to _poll() to return immediately.
        """
        raise NotImplementedError

    def send(self,client,data):
        """Send a response to the specified client."""
        self._send(client.server_id,client.client_id,data)

    def deliver(self,clients,data):
        """Send the same response to multiple clients.

        This more efficient than sending to them individually as it can
        batch up the replies.
        """
        #  Batch up the clients by their server id.
        #  If we get more than 100 to the same server, send them
        #  immediately.  The rest we send in a final iteration at the end.
        cids_by_sid = {}
        for client in clients:
            (sid,cid) = (client.server_id,client.client_id)
            if sid not in cids_by_sid:
                cids_by_sid[sid] = [cid]
            else:
                cids = cids_by_sid[sid]
                cids.append(cid)
                if len(cids) == 100:
                    self._send(sid," ".join(cids),data)
                    del cids_by_sid[sid]
        for (sid,cids) in cids_by_sid.itervalues():
            self._send(sid," ".join(cids),data)

    def interrupt(self):
        """Interrupt any blocking recv() calls on this connection.

        Calling this method will cause any blocking recv() calls to be
        interrupted and immediately return None.  You might like to call
        this if you're trying to shut down a handler from another thread.
        """
        if self._has_shutdown:
            return
        self._interrupt()

    def shutdown(self,timeout=None):
        """Shut down the connection.

        This indicates that no more requests should be received by the
        handler, but it is willing to process any that have already been
        transmitted.  Use it for graceful termination of handlers.

        After shutdown, you may only call recv() with timeout=0.
        """
        self._has_shutdown = True

    def close(self):
        """Close the connection."""
        self._has_shutdown = True



class Connection(ConnectionBase):
    """A standard PULL/PUB connection to Mongrel2.

    This class represents the standard handler connection to Mongrel2.
    It gets requests pushed to it via a PULL socket and sends response data
    via a PUB socket.
    """

    def __init__(self,send_sock,recv_sock=None):
        if recv_sock is None:
            recv_sock = self.copysockspec(send_sock,-1)
            if recv_sock is None:
                raise ValueError("could not infer recv socket spec")
        if isinstance(send_sock,basestring):
            send_sock = self.makesocket(zmq.PULL,send_sock)
        self.send_sock = send_sock
        if isinstance(recv_sock,basestring):
            recv_sock = self.makesocket(zmq.PUB,recv_sock)
        self.recv_sock = recv_sock
        super(Connection,self).__init__()

    def _recv(self,timeout=None):
        """Internal method for receving a message."""
        ready = self._poll([self.send_sock],timeout=timeout)
        if self.send_sock in ready:
            return self.send_sock.recv(zmq.NOBLOCK)

    def _send(self,server_id,client_ids,data):
        """Internal method to send out response data."""
        msg = "%s %d:%s, %s" % (server_id,len(client_ids),client_ids,data)
        self.recv_sock.send(msg)

    def shutdown(self,timeout=None):
        """Shut down the connection.

        This indicates that no more requests should be received by the
        handler, but it is willing to process any that have already been
        transmitted.  Use it for graceful termination of handlers.

        After shutdown, you may only call recv() with timeout=0.

        For the standard PULL socket, a clean shutdown is not possible
        as zmq has no API for it.  What we do is quickly ready anything
        that's pending for delivery then close the socket.  This leaves
        a slight race condition that a request will be pushed to us and
        then lost.
        """
        msg = self._recv(timeout=0)
        while msg is not None:
            self.recv_buffer.append(msg)
            msg = self._recv(timeout=0)
        self.send_sock.close()
        super(Connection,self).shutdown(timeout)

    def close(self):
        """Close the connection."""
        self.send_sock.close()
        self.recv_sock.close()
        super(Connection,self).close()


class DispatcherConnection(ConnectionBase):
    """A connection to Mongrel2 via a m2wsgi Dispatcher device.

    This class is designed to work with the m2wsgi Dispatcher device.  It
    gets requests and sends replies over a single XREQ socket, and also 
    listens for heartbeat pings on a SUB socket.
    """

    def __init__(self,disp_sock,ping_sock=None):
        super(DispatcherConnection,self).__init__()
        if ping_sock is None:
            ping_sock = self.copysockspec(disp_sock,1)
            if ping_sock is None:
                raise ValueError("could not infer ping socket spec")
        self._shutting_down = False
        if isinstance(disp_sock,basestring):
            disp_sock = self.makesocket(zmq.XREQ,disp_sock)
        self.disp_sock = disp_sock
        if isinstance(ping_sock,basestring):
            ping_sock = self.makesocket(zmq.SUB,ping_sock)
        ping_sock.setsockopt(zmq.SUBSCRIBE,"")
        self.ping_sock = ping_sock
        #  Introduce ourselves to the dispatcher
        self._send_xreq("")

    def _recv(self,timeout=None):
        """Internal method for receving a message."""
        socks = [self.disp_sock,self.ping_sock]
        ready = self._poll(socks,timeout=timeout)
        try:
            #  If we were pinged, respond to say we're still alive
            #  (or that we're shutting down)
            if self.ping_sock in ready:
                self.ping_sock.recv(zmq.NOBLOCK)
                if self._shutting_down:
                    self._send_xreq("X")
                else:
                    self._send_xreq("")
            #  Try to grab a request non-blockingly.
            return self._recv_xreq(zmq.NOBLOCK)
        except zmq.ZMQError, e:
            #  That didn't work out, return None.
            if e.errno != zmq.EAGAIN:
                if not self._has_shutdown:
                    raise
                if e.errno not in (zmq.ENOTSUP,zmq.EFAULT,):
                    raise
            return None

    def _send(self,server_id,client_ids,data):
        """Internal method to send out response data."""
        msg = "%s %d:%s, %s" % (server_id,len(client_ids),client_ids,data)
        self._send_xreq(msg)

    def _recv_xreq(self,flags=0):
        """Receive a message from the XREQ socket.

        This method contains the logic for stripping XREQ message delimiters,
        leaving just the message to be returned.
        """
        delim = self.disp_sock.recv(flags)
        if delim != "":
            return delim
        msg = self.disp_sock.recv(flags)
        return msg

    def _send_xreq(self,msg,flags=0):
        """Send a message through the XREQ socket.

        This method contains the logic for adding XREQ message delimiters
        to the message being sent.
        """
        self.disp_sock.send("",flags | zmq.SNDMORE)
        self.disp_sock.send(msg,flags)

    def shutdown(self,timeout=None):
        """Shut down the connection.

        This indicates that no more requests should be received by the
        handler, but it is willing to process any that have already been
        transmitted.  Use it for graceful termination of handlers.

        After shutdown, you may only call recv() with timeout=0.

        For the dispatcher connection, we send a single-byte message "X"
        to indicate that we're shutting down.  We then have to read in all
        incoming messages until the dispatcher responds with an "X" to
        indicate that the shutdown was recognised.
        """
        self._shutting_down = True
        self._send_xreq("X")
        t_start = time.time()
        msg = self._recv(timeout=timeout)
        t_end = time.time()
        timeout -= (t_end - t_start)
        while msg != "X" and (timeout is None or timeout > 0):
            if msg:
                self.recv_buffer.append(msg)
            t_start = time.time()
            msg = self._recv(timeout=timeout)
            t_end = time.time()
            timeout -= (t_end - t_start)
        super(DispatcherConnection,self).shutdown(timeout)

    def close(self):
        """Close the connection."""
        self.disp_sock.close()
        self.ping_sock.close()
        super(DispatcherConnection,self).close()



class Handler(object):
    """Mongrel2 request handler class.

    Instances of Handler act as a Mongrel2 handler process, dispatching
    incoming requests to their 'process_request' method.  The base class
    implementation does nothing.  See WSGIHandler for something useful.

    Handler objects must be constructed by passing in a Connection object.
    For convenience, you may pass a send_spec string instead of a Connection
    and one will be created for you.

    To enter the object's request-handling loop, call its 'serve' method; this
    will block until the server exits.  To exit the handler loop, call the
    'stop' method (probably from another thread).

    If you want more control over the handler, e.g. to integrate it with some
    other control loop, you can call the 'serve_one_request' method to serve
    a single request.  Note that this will block if there is not a request
    available - polling the underlying connection is up to you.
    """

    ConnectionClass = Connection

    def __init__(self,connection):
        self.started = False
        self.serving = False
        if isinstance(connection,basestring):
            self.connection = self.ConnectionClass(connection)
        else:
            self.connection = connection

    def serve(self):
        """Serve requests delivered by Mongrel2, until told to stop.

        This method is the main request-handling loop for Handler.  It calls
        the 'serve_one_request' method in a tight loop until told to stop
        by an explicit call to the 'stop' method.
        """
        self.serving = True
        self.started = True
        exc_info,exc_value,exc_tb = None,None,None
        try:
            while self.serving:
                self.serve_one_request()
        except Exception:
            self.running = False
            exc_info,exc_value,exc_tb = sys.exc_info()
            raise
        finally:
            #  Shut down the connection, but don't hide the original error.
            if exc_info is None:
                self._shutdown()
            else:
                try:
                    self._shutdown()
                except Exception:
                    print >>sys.stderr, "------- shutdown error -------"
                    traceback.print_exc()
                    print >>sys.stderr, "------------------------------"
                raise exc_info,exc_value,exc_tb

    def _shutdown(self):
        #  Attempt a clean disconnect from the socket.
        self.connection.shutdown(timeout=5)
        #  We have to handle anything that's already in our recv queue,
        #  or the requests will get lost when we close the socket.
        req = self.connection.recv(timeout=0)
        while req is not None:
            self.handle_request(req)
        self.wait_for_completion()
        self.connection.close()

    def stop(self):
        """Stop the request-handling loop and close down the connection."""
        self.serving = False
        self.started = False
        self.connection.interrupt()
    
    def serve_one_request(self,timeout=None):
        """Receive and serve a single request from Mongrel2."""
        req = self.connection.recv(timeout=timeout)
        if req is not None:
            self.handle_request(req)
        return req

    def handle_request(self,req):
        """Handle the given Request object.

        This method dispatches the given request object for processing.
        The base implementation just calls the process_request() method;
        subclasses might spawn a new thread or similar.

        It's a good idea to return control to the calling code as quickly as
        or you'll get a nice backlog of outstanding requests.
        """
        self.process_request(req)

    def process_request(self,req):
        """Process the given Request object.

        This method is the guts of a Mongrel2 handler, where you implement
        all your request-handling logic.  The base implementation does nothing.
        """
        pass

    def wait_for_completion(self):
        """Wait for all in-progress requests to be completed.

        Since the handle_request() method may operate asynchronously
        (e.g. by spawning a new thread) there must be a way to determine
        when all in-progress requets have been compeleted.  WSGIHandler
        subclasses should override this method to provide such behaviour.

        Note that the default implementation does nothing, since requests
        and handled synchronously in this case.
        """
        pass



class WSGIResponder(object):
    """Class for managing the WSGI response to a request.

    Instances of WSGIResponer manage the stateful details of responding
    to a particular Request object.  They provide the start_response callable
    and perform the internal buffering of status info required by the WSGI
    spec.

    Each WSGIResponder must be created with a single argument, the Request
    object to which it is responding.  You may then call the following methods
    to construct the response:

        start_response:  the standard WSGI start_response callable
        write:           send response data; doubles as the WSGI write callback
        finish           finalize the response, e.g. close the connection
        
    """

    def __init__(self,request):
        self.request = request
        self.status = None
        self.headers = None
        self.has_started = False
        self.is_chunked = False
        self.should_close = False

    def start_response(self,status,headers,exc_info=None):
        """Set the status code and response headers.

        This method provides the standard WSGI start_response callable.
        It just stores the given info internally for later use.
        """
        try:
            if self.has_started:
                if exc_info is not None:
                    raise exc_info[0], exc_info[1], exc_info[2]
                raise RuntimeError("response has already started")
            self.status = status
            self.headers = headers
            return self.write
        finally:
            exc_info = None

    def write(self,data):
        """Write the given data out on the response stream.

        This method sends the given data straight out to the client, sending
        headers and any framing info as necessary.
        """
        if not self.has_started:
            self.write_headers()
            self.has_started = True
        if self.is_chunked:
            self._write(hex(len(data))[2:])
            self._write("\r\n")
            self._write(data)
            self._write("\r\n")
        else:
            self._write(data)

    def finish(self):
        """Finalise the response.

        This method finalises the sending of the response, which may include
        sending a terminating data chunk or closing the connection.
        """
        if not self.has_started:
            self.write_headers()
            self.has_started = True
        if self.is_chunked:
            self._write("0\r\n\r\n")
        if self.should_close:
            self.request.disconnect()
            
    def write_headers(self):
        """Write out the response headers from the stored data.

        This method transmits the response headers stored from a previous call
        to start_response.  It also interrogates the headers to determine 
        various output modes, e.g. whether to use chunked encoding or whether
        to close the connection when finished.
        """
        self._write("HTTP/1.1 %s \r\n" % (self.status,))
        has_content_length = False
        has_date = False
        for (k,v) in self.headers:
            self._write("%s: %s\r\n" % (k,v,))
            if k.lower() == "content-length":
                has_content_length = True
            elif k.lower() == "date":
                has_date = True
        if not has_date:
            self._write("Date: %s\r\n" % (rfc822_format_date(),))
        if not has_content_length:
            if self.request.headers["VERSION"] == "HTTP/1.1":
                if self.request.headers["METHOD"] != "HEAD":
                    self._write("Transfer-Encoding: chunked\r\n")
                    self.is_chunked = True
            else:
                self.should_close = True
        self._write("\r\n")

    def _write(self,data):
        """Utility method for writing raw data to the response stream."""
        #  Careful; sending an empty string back to mongrel2 will
        #  cause the connection to be aborted!
        if data:
            self.request.respond(data)



class StreamingUploadFile(InputStream):
    """File-like object for streaming reads from in-progress uploads."""

    def __init__(self,request,fileobj):
        self.request = request
        self.fileobj = fileobj
        cl = request.headers.get("content-length","")
        if not cl:
            raise ValueError("missing content-length for streaming upload")
        try:
            cl = int(cl)
        except ValueError:
            msg = "malformed content-length for streaming upload: %r"
            raise ValueError(msg % (cl,))
        self.content_length = cl
        super(StreamingUploadFile,self).__init__()

    def close(self):
        super(StreamingUploadFile,self).close()
        self.fileobj.close()

    def _read(self,sizehint=-1):
        if self.fileobj.tell() >= self.content_length:
            return None
        if sizehint == 0:
            data = ""
        else:
            if sizehint > 0:
                data = self.fileobj.read(sizehint)
                while not data:
                    self._wait_for_data()
                    data = self.fileobj.read(sizehint)
            else:
                data = self.fileobj.read()
                while not data:
                    self._wait_for_data()
                    data = self.fileobj.read()
        return data

    def _wait_for_data(self):
        """Wait for more data to be available from this upload."""
        raise NotImplementedError


class WSGIHandler(Handler):
    """Mongrel2 Handler translating to WSGI.

    Instances of WSGIHandler act as Mongrel2 handler process, forwarding all
    requests to a WSGI application to provides a simple Mongrel2 => WSGI
    gateway.

    WSGIHandler objects must be constructed by passing in the target WSGI
    application and a Connection object.  For convenience, you may pass a
    send_spec string instead of a Connection and one will be created for you.

    To enter the object's request-handling loop, call its 'serve' method; this
    will block until the server exits.  To exit the handler loop, call the
    'stop' method (probably from another thread).

    If you want more control over the handler, e.g. to integrate it with some
    other control loop, you can call the 'serve_one_request' to serve a 
    single request.  Note that this will block if there is not a request
    available - polling the underlying connection is up to you.
    """

    ResponderClass = WSGIResponder
    StreamingUploadClass = StreamingUploadFile

    COMMA_SEPARATED_HEADERS = [
        'accept', 'accept-charset', 'accept-encoding', 'accept-language',
        'accept-ranges', 'allow', 'cache-control', 'connection',
        'content-encoding', 'content-language', 'expect', 'if-match',
        'if-none-match', 'pragma', 'proxy-authenticate', 'te', 'trailer',
        'transfer-encoding', 'upgrade', 'vary', 'via', 'warning',
        'www-authenticate'
    ]

    def __init__(self,application,connection):
        self.application = application
        super(WSGIHandler,self).__init__(connection)

    def process_request(self,req):
        """Process the given Request object.

        This method is the guts of the Mongrel2 => WSGI gateway.  It translates
        the mongrel2 request into a WSGI environ, invokes the application and
        sends the resulting response back to Mongrel2.
        """
        #  Mongrel2 uses JSON requests internally.
        #  We don't want them in our WSGI.
        if req.headers.get("METHOD","") == "JSON":
            return
        #  OK, it's a legitimate full HTTP request.
        #  Route it through the WSGI app.
        environ = {}
        responder = self.ResponderClass(req)
        try:
            #  If there's an async upload in progress, we have two options.
            #  If they sent a Content-Length header then we can do a streaming
            #  read from the file as it is being uploaded.  If there's no
            #  Content-Length then we have to wait for it all to upload (as
            #  there's no guarantee that the same handler will get both the
            #  start and end events for any upload).
            if "x-mongrel2-upload-start" in req.headers:
                if req.headers.get("content-length",""):
                    #  We'll streaming read it on the -start event,
                    #  so ignore the -done event.
                    if "x-mongrel2-upload-done" in req.headers:
                        return
                else:
                    #  We have to wait for the -done event,
                    #  so ignore the -start event.
                    if "x-mongrel2-upload-done" not in req.headers:
                        return
            #  Grab the full WSGI environ.
            #  This might error out, e.g. if someone tries any funny business
            #  with the mongrel2 upload headers.
            environ = self.get_wsgi_environ(req,environ)
            #  Call the WSGI app.
            #  Write all non-empty chunks, then clean up.
            chunks = self.application(environ,responder.start_response)
            try:
                for chunk in chunks:
                    if chunk:
                        responder.write(chunk)
                responder.finish()
            finally:
                if hasattr(chunks,"close"):
                    chunks.close()
        except Exception:
            print >>sys.stderr, "------- request handling error -------"
            traceback.print_exc()
            sys.stderr.write(str(environ) + "\n\n")
            print >>sys.stderr, "------------------------------ -------"
            #  Send an error response if we can.
            #  Always close the connection on error.
            if not responder.has_started:
                responder.start_response("500 Server Error",[],sys.exc_info())
                responder.write("server error")
                responder.finish()
            req.disconnect()
        finally:
            #  Make sure that the upload file is cleaned up.
            #  Mongrel doesn't reap these files itself, because the handler
            #  might e.g. move them somewhere.  We just read from them.
            try:
                environ["wsgi.input"].close()
            except (KeyError, AttributeError):
                pass
            upload_file = req.headers.get("x-mongrel2-upload-start",None)
            if upload_file:
                upload_file2 = req.headers.get("x-mongrel2-upload-done",None)
                if upload_file == upload_file2:
                    try:
                        os.unlink(upload_file)
                    except EnvironmentError:
                        pass

    def get_wsgi_environ(self,req,environ=None):
        """Construct a WSGI environ dict for the given Request object."""
        if environ is None:
            environ = {}
        #  Include keys required by the spec
        environ["REQUEST_METHOD"] = req.headers["METHOD"]
        script_name = req.headers["PATTERN"].split("(",1)[0]
        while script_name.endswith("/"):
            script_name = script_name[:-1]
        environ["SCRIPT_NAME"] = unquote_path(script_name)
        path_info = req.headers["PATH"][len(script_name):]
        environ["PATH_INFO"] = unquote_path(path_info)
        if "QUERY" in req.headers:
            environ["QUERY_STRING"] = unquote(req.headers["QUERY"])
        environ["SERVER_PROTOCOL"] = req.headers["VERSION"]
        #  TODO: mongrel2 doesn't seem to send me this info.
        #  How can I obtain it?  Suck it out of the config?
        #  Let's just hope the client sends a Host header...
        environ["SERVER_NAME"] = "localhost"
        environ["SERVER_PORT"] = "80"
        environ["REMOTE_ADDR"] = unquote(req.headers['x-forwarded-for'])
        #  Include standard wsgi keys
        environ['wsgi.input'] = self.get_input_file(req)
        # TODO: 100-continue support?
        environ['wsgi.errors'] = sys.stderr
        environ['wsgi.version'] = (1,0)
        environ['wsgi.multithread'] = True
        environ['wsgi.multiprocess'] = False
        environ['wsgi.url_scheme'] = "http"
        environ['wsgi.run_once'] = False
        #  Include the HTTP headers
        for (k,v) in req.headers.iteritems():
            #  The mongrel2 headers dict contains lots of things
            #  other than the HTTP headers.
            if not k.islower() or "." in k:
                continue
            #  The list-like headers are helpfully already lists.
            #  Sadly, we have to put them back into strings for WSGI.
            if isinstance(v,list):
                if k in self.COMMA_SEPARATED_HEADERS:
                    v = ", ".join(v)
                else:
                    v = v[-1]
            environ["HTTP_" + k.upper().replace("-","_")] = v
        #  Grab some special headers into expected names
        ct = environ.pop("HTTP_CONTENT_TYPE",None)
        if ct is not None:
            environ["CONTENT_TYPE"] = ct
        cl = environ.pop("HTTP_CONTENT_LENGTH",None)
        if cl is not None:
            environ["CONTENT_LENGTH"] = cl
        return environ

    def get_input_file(self,req):
        """Get a file-like object for use as environ['wsgi.input']

        For small requests this is a StringIO object.  For large requests
        where an async upload is performed, it is the actual tempfile into
        which the upload was dumped.

        If the request contains a content-length, then we can read the upload
        file while it is still comming in.  If not, we wait for it to
        compelte and then use the raw file object.
        """
        upload_file = req.headers.get("x-mongrel2-upload-start",None)
        if not upload_file:
            return StringIO(req.body)
        upload_file2 = req.headers.get("x-mongrel2-upload-done",None)
        if upload_file2 is None:
            return self.StreamingUploadClass(req,open(upload_file,"rb"))
        else:
            if upload_file != upload_file2:
                #  Highly suspicious behaviour; terminate immediately.
                raise RuntimeError("mismatched mongrel2-upload header")
            return open(upload_file,"rb")


def test_application(environ,start_response):
    start_response("200 OK",[("Content-Length","3")])
    yield "OK\n"


if __name__ == "__main__":
    s = WSGIHandler(test_application,"tcp://127.0.0.1:9999")
    s.serve()



########NEW FILE########
__FILENAME__ = eventlet
"""

m2wsgi.io.eventlet:  eventlet-based I/O module for m2wsgi
=========================================================


This module provides subclasses of m2wsgi.WSGIHandler and related classes
that are specifically tuned for running under eventlet.  You can import
and use the classes directory from here, or you can select this module
when launching m2wsgi from the command-line::

    m2wsgi --io=eventlet dotted.app.name tcp://127.0.0.1:9999

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


from __future__ import absolute_import 
from m2wsgi.util import fix_absolute_import
fix_absolute_import(__file__)

from m2wsgi.io import base

import zmq.core.poll as zmq_poll

import eventlet.hubs
from eventlet.green import zmq, time
from eventlet.timeout import Timeout
from eventlet.event import Event

from greenlet import GreenletExit


#  Older eventlet versions have buggy support for non-blocking zmq requests:
#     https://bitbucket.org/which_linden/eventlet/issue/76/
#
if map(int,eventlet.__version__.split(".")) <= [0,9,14]:
    raise ImportError("requires eventlet >= 0.9.15")


def monkey_patch():
    """Hook to monkey-patch the interpreter for this IO module.

    This calls the standard eventlet monkey-patching routines.  Don't worry,
    it's not called by default unless you're running from the command line.
    """
    eventlet.monkey_patch()


class Client(base.Client):
    __doc__ = base.Client.__doc__


class Request(base.Client):
    __doc__ = base.Client.__doc__


class ConnectionBase(base.ConnectionBase):
    __doc__ = base.ConnectionBase.__doc__ + """
    This ConnectionBase subclass is designed for use with eventlet.  It uses
    the monkey-patched zmq module from eventlet and spawns a number of
    greenthreads to manage non-blocking IO and interrupts.
    """
    ZMQ_CTX = zmq.Context()

    #  Since zmq.core.poll doesn't play nice with eventlet, we use a
    #  greenthread to implement interrupts.  Each call to _poll() spawns 
    #  a new greenthread for each socket and waits on them; calls to
    #  interrupt() kill the pending threads.
    def __init__(self):
        super(ConnectionBase,self).__init__()
        self.poll_threads = []

    def _poll(self,sockets,timeout=None):
        #  Don't bother trampolining if there's data available immediately.
        #  This also avoids calling into the eventlet hub with a timeout of
        #  zero, which doesn't work right (it still switches the greenthread)
        (r,_,_) = zmq_poll.select(sockets,[],[],timeout=0)
        if r:
            return r
        if timeout == 0:
            return []
        #  Looks like we'll have to block :-(
        ready = []
        threads = []
        res = Event()
        for sock in sockets:
            threads.append(eventlet.spawn(self._do_poll,sock,ready,res,timeout))
        self.poll_threads.append((res,threads))
        try:
            res.wait()
        finally:
            self.poll_threads.remove((res,threads))
            for t in threads:
                t.kill()
                try:
                    t.wait()
                except GreenletExit:
                    pass
        return ready

    def _do_poll(self,sock,ready,res,timeout):
        fd = sock.getsockopt(zmq.FD)
        try:
            zmq.trampoline(fd,read=True,timeout=timeout)
        except Timeout:
            pass
        else:
            ready.append(sock)
            if not res.ready():
                res.send()

    def _interrupt(self):
        for (res,threads) in self.poll_threads:
            if not res.ready():
                res.send()
            for t in threads:
                t.kill()


class Connection(base.Connection,ConnectionBase):
    __doc__ = base.Connection.__doc__ + """
    This Connection subclass is designed for use with eventlet.  It uses
    the monkey-patched zmq module from eventlet and spawns a number of
    green threads to manage non-blocking IO and interrupts.
    """


class DispatcherConnection(base.DispatcherConnection,ConnectionBase):
    __doc__ = base.DispatcherConnection.__doc__ + """
    This DispatcherConnection subclass is designed for use with eventlet.  It
    uses the monkey-patched zmq module from eventlet and spawns a number of
    green threads to manage non-blocking IO and interrupts.
    """


class StreamingUploadFile(base.StreamingUploadFile):
    __doc__ = base.StreamingUploadFile.__doc__ + """
    This StreamingUploadFile subclass is designed for use with eventlet.  It
    uses the monkey-patched time module from eventlet when sleeping.
    """
    def _wait_for_data(self):
        curpos = self.fileobj.tell()
        cursize = os.fstat(self.fileobj.fileno()).st_size
        while curpos >= cursize:
            time.sleep(0.01)
            cursize = os.fstat(self.fileobj.fileno()).st_size


class Handler(base.Handler):
    __doc__ = base.Handler.__doc__ + """
    This Handler subclass is designed for use with eventlet.  It spawns a
    a new green thread to handle each incoming request.
    """
    ConnectionClass = Connection

    def __init__(self,*args,**kwds):
        super(Handler,self).__init__(*args,**kwds)
        #  We need to count the number of inflight requests, so the
        #  main thread can wait for them to complete when shutting down.
        self._num_inflight_requests = 0
        self._all_requests_complete = None

    def handle_request(self,req):
        self._num_inflight_requests += 1
        if self._num_inflight_requests == 1:
            self._all_requests_complete = Event()
        @eventlet.spawn_n
        def do_handle_request():
            try:
                self.process_request(req)
            finally:
                self._num_inflight_requests -= 1
                if self._num_inflight_requests == 0:
                    self._all_requests_complete.send()
                    self._all_requests_complete = None

    def wait_for_completion(self):
        if self._num_inflight_requests > 0:
            self._all_requests_complete.wait()


class WSGIResponder(base.WSGIResponder):
    __doc__ = base.WSGIResponder.__doc__


class WSGIHandler(base.WSGIHandler,Handler):
    __doc__ = base.WSGIHandler.__doc__ + """
    This WSGIHandler subclass is designed for use with eventlet.  It spawns a
    a new green thread to handle each incoming request.
    """
    ResponderClass = WSGIResponder
    StreamingUploadClass = StreamingUploadFile


########NEW FILE########
__FILENAME__ = gevent
"""

m2wsgi.io.gevent:  gevent-based I/O module for m2wsgi
=====================================================


This module provides subclasses of m2wsgi.WSGIHandler and related classes
that are specifically tuned for running under gevent.  You can import
and use the classes directory from here, or you can select this module
when launching m2wsgi from the command-line::

    m2wsgi --io=gevent dotted.app.name tcp://127.0.0.1:9999

You will need the gevent_zeromq package from here:

    https://github.com/traviscline/gevent-zeromq

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


from __future__ import absolute_import
from m2wsgi.util import fix_absolute_import
fix_absolute_import(__file__)

from m2wsgi.io import base

import gevent
import gevent.monkey
import gevent.event
import gevent.core
import gevent.hub

import gevent_zeromq
from gevent_zeromq import zmq

import zmq.core.poll as zmq_poll

if hasattr(zmq, '_Context'):
    ZContext = zmq._Context
else:
    ZContext = zmq.Context

if hasattr(zmq, '_Socket'):
    ZSocket = zmq._Socket
else:
    ZSocket = zmq.Socket


def monkey_patch():
    """Hook to monkey-patch the interpreter for this IO module.

    This calls the standard gevent monkey-patching routines.  Don't worry,
    it's not called by default unless you're running from the command line.
    """
    gevent.monkey.patch_all()
    gevent_zeromq.monkey_patch()
    #  Patch signal module for gevent compatability.
    #  Courtesy of http://code.google.com/p/gevent/issues/detail?id=49
    import signal
    _orig_signal = signal.signal
    def gevent_signal_wrapper(signum,*args,**kwds):
        handler = signal.getsignal(signum)
        if callable(handler):
            handler(signum,None)
    def gevent_signal(signum,handler):
        _orig_signal(signum,handler)
        return gevent.hub.signal(signum,gevent_signal_wrapper,signum)
    signal.signal = gevent_signal


#  The BaseConnection recv logic is based on polling, but I can't get
#  gevent polling on multiple sockets to work correctly.
#  Instead, we simulate polling on each socket individually by reading an item
#  and keeping it in a local buffer.
#
#  Ideally I would juse use the _wait_read() method on gevent-zmq sockets,
#  but this seems to cause hangs for me.  Still investigating.

class _Context(ZContext):
    def socket(self,socket_type):
        if self.closed:
            raise zmq.ZMQError(zmq.ENOTSUP)
        return _Socket(self,socket_type)
    def term(self):
        #  This seems to be needed to let other greenthreads shut down.
        #  Omit it, and the SIGHUP handler gets  "bad file descriptor" errors.
        gevent.sleep(0.1)
        return super(_Context,self).term()

class _Socket(ZSocket):
    def __init__(self,*args,**kwds):
        self._polled_recv = None
        super(_Socket,self).__init__(*args,**kwds)
    #  This blockingly-reads a message from the socket, but stores
    #  it in a buffer rather than returning it.
    def _recv_poll(self,flags=0,copy=True,track=False):
        if self._polled_recv is None:
            self._polled_recv = super(_Socket,self).recv(flags,copy,track)
    #  This uses the buffered result if available, or polls otherwise.
    def recv(self,flags=0,copy=True,track=False):
        v = self._polled_recv
        while v is None:
            self._recv_poll(flags,copy=copy,track=track)
            v = self._polled_recv
        self._polled_recv = None
        return v

zmq.Context = _Context
zmq.Socket = _Socket



class Client(base.Client):
    __doc__ = base.Client.__doc__


class Request(base.Client):
    __doc__ = base.Client.__doc__


class ConnectionBase(base.ConnectionBase):
    __doc__ = base.ConnectionBase.__doc__ + """
    This ConnectionBase subclass is designed for use with gevent.  It uses
    the monkey-patched zmq module from gevent and spawns a number of green
    threads to manage non-blocking IO and interrupts.
    """
    ZMQ_CTX = zmq.Context()

    #  A blocking zmq.core.poll doesn't play nice with gevent.
    #  Instead we read from each socket in a separate greenthread, and keep
    #  the results in a local buffer so they don't get lost.  An interrupt
    #  then just kills all the currently-running threads.
    def __init__(self):
        super(ConnectionBase,self).__init__()
        self.poll_threads = []

    def _poll(self,sockets,timeout=None):
        #  If there's anything available non-blockingly, just use it.
        (ready,_,error) = zmq_poll.select(sockets,[],sockets,timeout=0)
        if ready:
            return ready
        if error:
            return []
        if timeout == 0:
            return []
        #  Spawn a greenthread to poll-recv from each socket.
        ready = []
        threads = []
        res = gevent.event.Event()
        for sock in sockets:
            threads.append(gevent.spawn(self._do_poll,sock,ready,res,timeout))
        self.poll_threads.append((res,threads))
        #  Wait for one of them to return, or for an interrupt.
        try:
            res.wait()
        finally:
            gevent.killall(threads)
            gevent.joinall(threads)
        return ready

    def _do_poll(self,sock,ready,res,timeout):
        if timeout is None:
            sock._recv_poll()
        else:
            with gevent.Timeout(timeout,False):
                sock._recv_poll()
        ready.append(sock)
        if not res.is_set():
            res.set()

    def _interrupt(self):
        for (res,threads) in self.poll_threads:
            gevent.killall(threads)
            if not res.is_set():
                res.set()



class Connection(base.Connection,ConnectionBase):
    __doc__ = base.Connection.__doc__ + """
    This Connection subclass is designed for use with gevent.  It uses the
    monkey-patched zmq module from gevent and spawns a number of green
    threads to manage non-blocking IO and interrupts.
    """


class DispatcherConnection(base.DispatcherConnection,ConnectionBase):
    __doc__ = base.DispatcherConnection.__doc__ + """
    This DispatcherConnection subclass is designed for use with gevent.  It
    uses the monkey-patched zmq module from gevent and spawns a number of
    green threads to manage non-blocking IO and interrupts.
    """


class StreamingUploadFile(base.StreamingUploadFile):
    __doc__ = base.StreamingUploadFile.__doc__ + """
    This StreamingUploadFile subclass is designed for use with gevent.  It
    uses uses gevent.sleep() instead of time.sleep().
    """
    def _wait_for_data(self):
        curpos = self.fileobj.tell()
        cursize = os.fstat(self.fileobj.fileno()).st_size
        while curpos >= cursize:
            gevent.sleep(0.01)
            cursize = os.fstat(self.fileobj.fileno()).st_size


class Handler(base.Handler):
    __doc__ = base.Handler.__doc__ + """
    This Handler subclass is designed for use with gevent.  It spawns a
    a new green thread to handle each incoming request.
    """

    ConnectionClass = Connection

    def __init__(self,*args,**kwds):
        super(Handler,self).__init__(*args,**kwds)
        #  We need to count the number of inflight requests, so the
        #  main thread can wait for them to complete when shutting down.
        self._num_inflight_requests = 0
        self._all_requests_complete = gevent.event.Event()

    def handle_request(self,req):
        self._num_inflight_requests += 1
        if self._num_inflight_requests >= 1:
            self._all_requests_complete.clear()
        @gevent.spawn
        def do_handle_request():
            try:
                self.process_request(req)
            finally:
                self._num_inflight_requests -= 1
                if self._num_inflight_requests == 0:
                    self._all_requests_complete.set()

    def wait_for_completion(self):
        if self._num_inflight_requests > 0:
            self._all_requests_complete.wait()


class WSGIResponder(base.WSGIResponder):
    __doc__ = base.WSGIResponder.__doc__


class WSGIHandler(base.WSGIHandler,Handler):
    __doc__ = base.WSGIHandler.__doc__ + """
    This WSGIHandler subclass is designed for use with gevent.  It spawns a
    a new green thread to handle each incoming request.
    """
    ResponderClass = WSGIResponder
    StreamingUploadClass = StreamingUploadFile

########NEW FILE########
__FILENAME__ = standard
"""

m2wsgi.io.standard:  standard I/O module for m2wsgi
===================================================


This module contains the basic classes for implementing handlers with m2wsgi.
They use standard blocking I/O and are designed to work with normal python
threads. If you don't explicitly select a different IO module, you'll get the
classes from in here.  We have the following classes:

    :Connection:     represents the connection from your handler to Mongrel2,
                     through which you can read requests and send responses.

    :Client:         represents a client connected to the server, to whom you
                     can send data at any time.

    :Request:        represents a client request to which you can send
                     response data to at any time.

    :Handler:        a base class for implementing handlers, with nothing
                     WSGI-specific in it.

    :WSGIHandler:    a handler subclass specifically running a WSGI app.


    :WSGIResponder:  a class for managing the stateful aspects of a WSGI
                     response (status line, write callback, etc).


"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.

from __future__ import absolute_import 
from m2wsgi.util import fix_absolute_import
fix_absolute_import(__file__)

import os
import time

import zmq.core.poll

from m2wsgi.io import base



def monkey_patch():
    """Hook to monkey-patch the interpreter for this IO module.

    Since this module is designed for standard blocking I/O, there's actually
    no need to monkey-patch anything.  But we provide a dummy function anyway.
    """
    pass


class Client(base.Client):
    __doc__ = base.Client.__doc__


class Request(base.Client):
    __doc__ = base.Client.__doc__


class ConnectionBase(base.ConnectionBase):
    __doc__ = base.ConnectionBase.__doc__ 

    def __init__(self):
        #  We use an anonymous pipe to interrupt blocking receives.
        #  The _poll() always polls intr_pipe_r.
        (self.intr_pipe_r,self.intr_pipe_w) = os.pipe()
        super(ConnectionBase,self).__init__()

    def _poll(self,sockets,timeout=None):
        if timeout != 0:
            sockets = sockets + [self.intr_pipe_r]
        (ready,_,_) = zmq.core.poll.select(sockets,[],[],timeout=timeout)
        if self.intr_pipe_r in ready:
            os.read(self.intr_pipe_r,1)
            ready.remove(self.intr_pipe_r)
        return ready

    def _interrupt(self):
        #  First make sure there are no old interrupts in the pipe.
        socks = [self.intr_pipe_r]
        (ready,_,_) = zmq.core.poll.select(socks,[],[],timeout=0)
        while ready:
            os.read(self.intr_pipe_r,1)
            (ready,_,_) = zmq.core.poll.select(socks,[],[],timeout=0)
        #  Now write to the interrupt pipe to trigger it.
        os.write(self.intr_pipe_w,"X")

    def close(self):
        super(ConnectionBase,self).close()
        os.close(self.intr_pipe_r)
        self.intr_pipe_r = None
        os.close(self.intr_pipe_w)
        self.intr_pipe_w = None


class Connection(base.Connection,ConnectionBase):
    __doc__ = base.Connection.__doc__ 


class DispatcherConnection(base.DispatcherConnection,ConnectionBase):
    __doc__ = base.DispatcherConnection.__doc__


class StreamingUploadFile(base.StreamingUploadFile):
    __doc__ = base.StreamingUploadFile.__doc__
    def _wait_for_data(self):
        """Wait for more data to be available from this upload.

        The standard implementation simply does a sleep loop until the
        file grows past its current position.  Eventually we could try
        using file notifications to detect change.
        """
        curpos = self.fileobj.tell()
        cursize = os.fstat(self.fileobj.fileno()).st_size
        while curpos >= cursize:
            time.sleep(0.01)
            cursize = os.fstat(self.fileobj.fileno()).st_size


class Handler(base.Handler):
    __doc__ = base.Handler.__doc__
    ConnectionClass = Connection


class WSGIResponder(base.WSGIResponder):
    __doc__ = base.WSGIResponder.__doc__


class WSGIHandler(base.WSGIHandler,Handler):
    __doc__ = base.WSGIHandler.__doc__
    ResponderClass = WSGIResponder
    StreamingUploadClass = StreamingUploadFile


########NEW FILE########
__FILENAME__ = buffer
"""

m2wsgi.middleware.buffer:  response buffering middleware
========================================================

This is a WSGI middleware class that buffers the response iterable so it 
doesn't return lots of small chunks.

It is completely and totally against the WSGI spec, which requires that the
server not delay transmission of any data to the client.  But if you don't care 
about this requirement, you can use this middelware to improve the performance
of e.g. content gzipping.

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


from __future__ import absolute_import


class BufferMiddleware(object):
    """WSGI middleware for buffering response content.

    This is completely and totally against the WSGI spec, which requires that
    the server not delay transmission of any data to the client.  But if you
    don't care about this requirement, you can use this middelware to improve
    the performance of e.g. content gzipping.

    Supports the following keyword arguments:

        :min_chunk_size:     minimum size of chunk to yield up the chain

    """

    def __init__(self,application,**kwds):
        self.application = application
        self.min_chunk_size = kwds.pop("min_chunk_size",200)

    def __call__(self,environ,start_response):
        output = self.application(environ,start_response)
        return BufferIter(output,self.min_chunk_size)


class BufferIter(object):
    """Iterator wrapper buffering chunks yielded by another iterator."""

    def __init__(self,iterator,min_chunk_size):
        self.iterator = iter(iterator)
        self.min_chunk_size = min_chunk_size
        self.buffer = []

    def __iter__(self):
        return self

    def __len__(self):
        #  We don't know how long the iterator is, with one exception.
        #  If it's only a single item, then so are we.
        nitems = len(self.iterator)
        if nitems > 1:
            raise TypeError
        return nitems

    def next(self):
        min_size = self.min_chunk_size
        try:
            size = 0
            while size < min_size:
                self.buffer.append(self.iterator.next())
                size += len(self.buffer[-1])
            chunk = "".join(self.buffer)
            del self.buffer[:]
            return chunk
        except StopIteration:
            if not self.buffer:
                raise
            else:
                chunk = "".join(self.buffer)
                del self.buffer[:]
                return chunk


########NEW FILE########
__FILENAME__ = gzip
"""

m2wsgi.middleware.gzip:  GZip content-encoding middleware
=========================================================

This is a GZip content-encoding WSGI middleware.  It strives hard for WSGI
compliance, even at the expense of compression.  If you want to trade off
compliance for better compression, put an instance of BufferMiddleware inside
it to collect small chunks and compress them all at once.

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


from __future__ import absolute_import

import gzip
from cStringIO import StringIO
from itertools import chain


class GZipMiddleware(object):
    """WSGI middleware for gzipping response content.

    Yeah yeah, don't do that, it's the province of the server.  Well, this
    is a server and an outer-layer middleware object seems like the simplest
    way to implement gzip compression support.

    Unlike every other gzipping-middleware I have ever seen (except a diff
    that's languished in Django's bugzilla for 3 years) this one is capable
    of compressing streaming responses.  But beware, if your app yields lots
    of small chunks this will probably *increase* the size of the payload
    due to the overhead of the compression data.

    This class supports the following keyword arguments:

        :compress_level:      gzip compression level; default is 9

        :min_compress_size:  don't bother compressing data smaller than this,
                             unless the spec requires it; default is 200 bytes

    """

    def __init__(self,application,**kwds):
        self.application = application
        self.compress_level = kwds.pop("compress_level",9)
        self.min_compress_size = kwds.pop("min_compress_size",200)

    def __call__(self,environ,start_response):
        handler = []
        #  We can't decide how to properly handle the response until we
        #  have the headers, which means we have to do this in the 
        #  start_response function.  It will append a callable and
        #  any required arguments to the 'handler' list.
        def my_start_response(status,headers,exc_info=None):
            if not self._should_gzip(environ,status,headers):
                handler.append(self._respond_uncompressed)
                return start_response(status,headers,exc_info)
            else:
                gzf = gzip.GzipFile(mode="wb",fileobj=StringIO(),
                                    compresslevel=self.compress_level)
                #  We must stream the chunks if there's no content-length
                has_content_length = False
                for (i,(k,v)) in enumerate(headers):
                    if k.lower() == "content-length":
                        has_content_length = True
                    elif k.lower() == "vary":
                        if "accept-encoding" not in v.lower():
                            if v:
                                headers[i] = (k,v+", Accept-Encoding")
                            else:
                                headers[i] = (k,"Accept-Encoding")
                headers.append(("Content-Encoding","gzip"))
                if has_content_length:
                    handler.append(self._respond_compressed_block)
                    handler.append(gzf)
                    handler.append(start_response)
                    handler.append(status)
                    handler.append(headers)
                    handler.append(exc_info)
                else:
                    start_response(status,headers,exc_info)
                    handler.append(self._respond_compressed_stream)
                    handler.append(gzf)
                #  This is the stupid write() function required by the spec.
                #  It will buffer all data written until a chunk is yielded
                #  from the application.
                return gzf.write
        output = self.application(environ,my_start_response)
        #  We have to read up to the first yielded chunk to give
        #  the app a change to call start_response.
        try:
            (_,output) = ipeek(iter(output))
        except StopIteration:
            output = [""]
        return handler[0](output,*handler[1:])

    def _respond_uncompressed(self,output):
        """Respond with raw uncompressed data; the easy case."""
        for chunk in output:
            yield chunk

    def _respond_compressed_stream(self,output,gzf):
        """Respond with a stream of compressed chunks.

        This is pretty easy, but you have to mind the WSGI requirement to
        always yield each chunk in full whenever the application yields a
        chunk.  Throw in some buffering middleware if you don't care about
        this requirement, it'll make compression much better.
        """
        for chunk in output:
            if not chunk:
                yield chunk
            else:
                gzf.write(chunk)
                gzf.flush()
                yield gzf.fileobj.getvalue()
                gzf.fileobj = StringIO()
        fileobj = gzf.fileobj
        gzf.close()
        yield fileobj.getvalue()

    def _respond_compressed_block(self,output,gzf,sr,status,headers,exc_info):
        """Respond with a single block of compressed data.

        Since this method will have to adjust the final content-length header,
        it maintains responsibility for calling start_response.

        Note that we can only maintain the WSGI requirement that we not delay
        any blocks if the application output provides a __len__ method and it           returns 1.  Otherwise, we have to *remove* the Content-Length header
        and stream the response, then let the server sort out how to terminate
        the connection.
        """
        #  Helper function to remove any content-length headers and
        #  then respond with streaming compression.
        def streamit():
            todel = []
            for (i,(k,v)) in enumerate(headers):
                if k.lower() == "content-length":
                    todel.append(i)
            for i in reversed(todel):
                del headers[i]
            sr(status,headers,exc_info)
            return self._respond_compressed_stream(output,gzf)
        #  Check if we can safely compress the whole body.
        #  If not, stream it a chunk at a time.
        try:
            num_chunks = len(output)
        except Exception:
            return streamit()
        else:
            if num_chunks > 1:
                return streamit()
        #  OK, we can compress it all in one go.
        #  Make sure to adjust content-length header.
        for chunk in output:
            gzf.write(chunk)
        gzf.close()
        body = gzf.getvalue()
        for (i,(k,v)) in headers:
            if k.lower() == "content-length":
                headers[i] = (k,str(len(body)))
        sr(status,headers,exc_info)
        return [body]

    def _should_gzip(self,environ,status,headers):
        """Determine whether we should bother gzipping.

        This checks whether the client will accept it, or whether it just
        seems like a bad idea.
        """
        code = status.split(" ",1)[0]
        #  Don't do it if the browser doesn't support it.
        if "gzip" not in environ.get("HTTP_ACCEPT_ENCODING",""):
            return False
        #  Don't do it for error responses, or things with no content.
        if not code.startswith("2"):
            return False
        if code in ("204",):
            return False
        #  Check various response headers
        for (k,v) in headers:
            #  If it's already content-encoded, must preserve
            if k.lower() == "content-encoding":
                return False
            #  If it's too small, don't bother
            if k.lower() == "content-length":
                try:
                    if int(v) < self.min_compress_size:
                        return False
                except Exception:
                    return False
            #  As usual, MSIE has issues
            if k.lower() == "content-type":
                if "msie" in environ.get("HTTP_USER_AGENT","").lower():
                    if not v.strip().startswith("text/"):
                        return False
                    if "javascript" in v:
                        return False
        return True


def ipeek(iterable):
    """Peek at the first item of an iterable.

    This returns a two-tuple giving the first item from the iteration,
    and a stream yielding all items from the iterable.  Use it like so:

        (first,iterable) = ipeek(iterable)

    If the iterable is empty, StopItertation is raised.
    """
    firstitem = iterable.next()
    return (firstitem,_PeekedIter(firstitem,iterable))


class _PeekedIter(object):
    """Iterable that has had its first item peeked at."""
    def __init__(self,firstitem,iterable):
        self.iterable = iterable
        self.allitems = chain((firstitem,),iterable)
    def __len__(self):
        return len(self.iterable)
    def __iter__(self):
        return self
    def next(self):
        return self.allitems.next()
        

########NEW FILE########
__FILENAME__ = test_m2wsgi

import unittest

import os
import sys
import shutil

import m2wsgi
import m2wsgi.io.base
from m2wsgi import io

class TestMisc(unittest.TestCase):

    def test_README(self):
        """Ensure that the README is in sync with the docstring.

        This test should always pass; if the README is out of sync it just
        updates it with the contents of m2wsgi.__doc__.
        """
        dirname = os.path.dirname
        readme = os.path.join(dirname(dirname(dirname(__file__))),"README.rst")
        if not os.path.isfile(readme):
            f = open(readme,"wb")
            f.write(m2wsgi.__doc__.encode())
            f.close()
        else:
            f = open(readme,"rb")
            if f.read() != m2wsgi.__doc__:
                f.close()
                f = open(readme,"wb")
                f.write(m2wsgi.__doc__.encode())
                f.close()

class TestRequestParsing(unittest.TestCase):

    def test_parsing_netstring_payloads(self):
        fnm = os.path.join(os.path.dirname(__file__),"request_payloads.txt")
        json_reqs = []; tns_reqs = []
        with open(fnm,"r") as f:
            for i,ln in enumerate(f):
                if i % 2 == 0:
                    json_reqs.append(ln.strip())
                else:
                    tns_reqs.append(ln.strip())
        assert len(json_reqs) == len(tns_reqs)
        def parse_request(data):
            (server_id,client_id,rest) = data.split(" ",2)
            client = io.base.Client(None,server_id,client_id)
            return io.base.Request.parse(client,rest)
        for (r_json,r_tns) in zip(json_reqs,tns_reqs):
            self.assertEquals(parse_request(r_json),parse_request(r_tns))

########NEW FILE########
__FILENAME__ = conhash
"""

m2wsgi.util.conhash:  classes for consistent hashing
====================================================

This module implements some simple classes for consistent hashing, to be
used for implementing "sticky sessions" in the dispatcher device.

The main interface is the class "ConsistentHash", which implements the
mapping interface to assign any given key to one of a set of targets.
Importantly, the target assigned to most keys will not change as targets
are added or removed from the hash.

Basic usage::

   ch = ConsistentHash()

   #  add some targets, which items will map to
   ch.add_target("ONE")
   ch.add_target("TWO")
   ch.add_target("THREE")

   #  now you can map items one one of the assigned targets
   assert ch["hello"] == "THREE"
   assert ch["world"] == "ONE"

   #  and removing targets leaves most mappings unchanged
   ch.rem_target("ONE")
   assert ch["hello"] == "THREE"
   assert ch["world"] == "THREE"


"""

import sys
import os
import hashlib
import bisect
import time

try:
    import scipy.stats
    import numpy
except ImportError:
    scipy = numpy = None


def md5hash(key):
    """Hash the object based on the md5 of its str().

    This is more expensive than the builtin hash() function but tends
    to shuffle better.  Python's builtin hash() has lots of special cases
    that make sense for dictionaries, but not for our purposes here.
    """
    return hashlib.md5(str(key)).hexdigest()[:8]
    return int(hashlib.md5(str(key)).hexdigest()[:8],16)


class RConsistentHash(object):
    """A consistent hash object based on arranging hashes in a ring.

    A ConsistentHash object maps arbitrary items onto one of a set of
    pre-specified targets, in such a way that adding or removing targets
    leaves the mapping of "most" of the items unchanged.

    This implementation is the one found in the paper introducing consistent
    hashing, and on wikipedia.  The hash values for the targets are arranged
    to form a closed ring.  To assign a key to a target, hash it to find its
    place on the ring then move clockwise until you find a target.

    This is nice from an efficiency standpoint as you only have to hash
    the key once, and the lookup is logarithmic in the number of targets.
    On the downside, it can be tricky to ensure uniformity of the target
    selection.  You must include many duplicates of each target to get an
    even distribution around the ring, and the right number to include will
    depend on the expected number of targets and the nature of your hash.
    """
    def __init__(self,hash=md5hash,num_duplicates=10000):
        self.target_ring = []
        self.hash = hash
        self.num_duplicates = num_duplicates

    def add_target(self,target):
        for i in xrange(self.num_duplicates):
            h = self.hash((i,target,))
            bisect.insort(self.target_ring,(h,target))

    def rem_target(self,target):
        self.target_ring = [(h,t) for (h,t) in self.target_ring if t != target]

    def has_target(self,target):
        for (h,t) in self.target_ring:
            if t == target:
                return True
        return False

    def __getitem__(self,key):
        h = self.hash(key)
        i = bisect.bisect_left(self.target_ring,(h,key))
        if i == len(self.target_ring):
            try:
                return self.target_ring[0][1]
            except IndexError:
                raise KeyError
        else:
            return self.target_ring[i][1]

    def __len__(self):
        return len(self.target_ring) / self.num_duplicates


class SConsistentHash(object):
    """A consistent hash object based on sorted hashes with each key.

    A ConsistentHash object maps arbitrary items onto one of a set of
    pre-specified targets, in such a way that adding or removing targets
    leaves the mapping of "most" of the items unchanged.

    This implementation is the one used by the Tahoe-LAFS project for server
    selection.  The key is hashed with each target and the resulting hashes
    are sorted.  The target producing the smallest hash is selected.

    What's nice about this implementation is that, assuming your hash function
    mixed well, it provides a very good uniform distribution without any
    tweaking.  It also uses much less memory than the RConsistentHash.
    On the downside, lookup is linear in the number of targets and you must
    call the hash function multiple times for each key.
    """
    def __init__(self,hash=md5hash):
        self.targets = set()
        self.hash = hash

    def add_target(self,target):
        self.targets.add(target)

    def rem_target(self,target):
        self.targets.remove(target)

    def has_target(self,target):
        return (target in self.targets)

    def __getitem__(self,key):
        targets = iter(self.targets)
        try:
            best_t = targets.next()
        except StopIteration:
            raise KeyError
        best_h = self.hash((key,best_t))
        for t in targets:
            h = self.hash((key,t))
            if h < best_h:
                best_t = t
                best_h = h
        return best_t

    def __len__(self):
        return len(self.targets)


#  For now, we use the SConsistentHash as standard.
#  It's slower but not really *slow*, and it consistently produces
#  a better uniform distribution of keys.
ConsistentHash = SConsistentHash


#
#  Some basic statistical tests for the hashes.
#  We're interested in:
#     * uniformity of distribution
#     * number of keys moved when a target is added/removed
#     * runtime performance
#

if numpy is not None:

    def iterpairs(seq):
        seq = iter(seq)
        try:
            first = seq.next()
            while True:
                second = seq.next()
                yield (first,second)
                first = second
        except StopIteration:
            pass

    def test_map(map):
        stats = get_map_stats(map)
        print "runtime:", "%.4f" % (stats[-1]["runtime"],)
        print "range:", stats[-1]["range"]
        print "stddev:", stats[-1]["stddev"]
        print "stdv/mean:", stats[-1]["stddev"] / stats[-1]["mean"] * 100
        for (first,second) in iterpairs(stats):
            res1 = first["results"]
            res2 = second["results"]
            nmoved = 0
            for k in res1:
                if res1[k] != res2[k]:
                    nmoved += 1
            pmoved = nmoved * 100.0 / len(res1)
            ntargets = len(second["counts"])
            print "added target, now ", ntargets, "total"
            print "should move around %.2f%% of keys" % (100.0 / ntargets,)
            print "moved %d of %d keys (%.2f%%)" % (nmoved,len(res1),pmoved,)
        if map_is_uniform(map,stats=stats):
            print "UNIFORM"
        else:
            print "BIASED"
        

    def map_is_uniform(map,p=0.01,stats=None):
        """Do a little chi-squared test for uniformity."""
        n = 4
        N = 100000
        E = N*1.0/n
        if stats is None:
            stats = get_map_stats(map,n,N)
        for s in stats:
            if scipy.stats.chisquare(s["counts"].values())[1] <= p:
                return False
        else:
            return True

    def get_map_stats(map,n=4,N=100000):
        """Gather some statistics by exercising the given map."""
        #  Randomly generate n+2 different targets
        res = [{},{},{}]
        stats = [{},{},{}]
        for i in xrange(n+2):
            t = os.urandom(4).encode("hex")
            try:
                while map[t] == t:
                    t = os.urandom(4).encode("hex")
            except (KeyError,IndexError,):
                pass
            map.add_target(t)
        #  For each of n, n+1, n+2, lookup N randomly-generated keys.
        #  We start at n+2, then remove a target for each iteration.
        keys = [os.urandom(16).encode("hex") for _ in xrange(N)]
        for i in reversed(xrange(3)):
            tstart = time.time()
            for k in keys:
                res[i][k] = map[k]
            tend = time.time()
            stats[i]["results"] = res[i]
            counts = {}
            for (k,t) in res[i].iteritems():
                counts[t] = counts.get(t,0) + 1
            stats[i]["counts"] = counts
            stats[i]["mean"] = sum(counts.values()) / len(counts)
            stats[i]["range"] = max(counts.values())-min(counts.values())
            stats[i]["stddev"] = numpy.std(counts.values())
            stats[i]["runtime"] = tend - tstart
            if i:
                t = res[i][keys[0]]
                map.rem_target(t)
        return stats

    
    if __name__ == "__main__":
        print "Testing ConsistentHash..."
        test_map(RConsistentHash())
        print "Testing SConsistentHash..."
        test_map(SConsistentHash())



########NEW FILE########
__FILENAME__ = __main__
"""

m2wsgi.__main__:  allow m2wsgi to be executed directly by python -m
===================================================================

This is a simple script that calls the m2wsgi.main() function.  It allows
python 2.7 and later to execute the m2wsgi package with `python -m m2wsgi`.

"""
#  Copyright (c) 2011, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.


import m2wsgi

if __name__ == "__main__":
    m2wsgi.main()


########NEW FILE########
