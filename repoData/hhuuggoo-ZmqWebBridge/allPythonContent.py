__FILENAME__ = bridge
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from geventwebsocket.handler import WebSocketHandler
from gevent import pywsgi
from gevent_zeromq import zmq
import logging
log = logging.getLogger(__name__)
import simplejson
from gevent import spawn
import Queue
import hashlib

# demo app
class ZmqGatewayFactory(object):
    """ factory returns an existing gateway if we have one,
    or creates a new one and starts it if we don't
    """
    def __init__(self, HWM=100):
        self.gateways = {}
        self.ctx = zmq.Context()
        self.HWM = HWM
        
    def get(self, socket_type, zmq_conn_string):
        if (socket_type, zmq_conn_string) in self.gateways:
            gateway =  self.gateways[socket_type, zmq_conn_string]
            return gateway
        else:
            if socket_type == zmq.REQ:
                log.debug("spawning req socket %s" ,zmq_conn_string) 
                self.gateways[socket_type, zmq_conn_string] = \
                                ReqGateway(zmq_conn_string,
                                           self.HWM,
                                           ctx=self.ctx)
            elif socket_type == zmq.REP:
                log.debug("spawning rep socket %s" ,zmq_conn_string)
                self.gateways[socket_type, zmq_conn_string] = \
                                RepGateway(zmq_conn_string,
                                           self.HWM,
                                           ctx=self.ctx)
            else:
                log.debug("spawning sub socket %s" ,zmq_conn_string) 
                self.gateways[socket_type, zmq_conn_string] = \
                                    SubGateway(zmq_conn_string,
                                               self.HWM,
                                               ctx=self.ctx)
            self.gateways[socket_type, zmq_conn_string].start()
            return self.gateways[socket_type, zmq_conn_string]

    def shutdown(self):
        """
        Close all sockets associated with this context, and then
        terminate the context.
        """
        self.ctx.destroy()

class WebProxyHandler(object):
    """ generic handler which works with proxy objects, proxies can
    register with WebProxyHandler, and deregister with them
    """
    def __init__(self):
        self.proxies = {}
        
    def register(self, identity, proxy):
        self.proxies[identity] = proxy

    def deregister(self, identity):
        try:
            self.proxies.pop(identity)
        except KeyError as e:
            pass

    def close(self):
        for v in self.proxies.values():
            v.deregister()
            
class ZmqGateway(WebProxyHandler):
    """ proxy handler which handles the zeromq side of things.
    """
    def __init__(self, zmq_conn_string, ctx=None):
        super(ZmqGateway, self).__init__()
        self.zmq_conn_string = zmq_conn_string
        self.ctx = ctx
        
    def send_proxy(self, identity, msg):
        try:
            self.proxies[identity].send_web(msg)
        #what exception is thrown here?
        except Exception as e:
            log.exception(e)
            self.deregister(identity)
            
class SubGateway(ZmqGateway):
    def __init__(self, zmq_conn_string, HWM, ctx=None):
        super(SubGateway, self).__init__(zmq_conn_string, ctx=ctx)
        self.s = ctx.socket(zmq.SUB)
        self.s.setsockopt(zmq.SUBSCRIBE, '');
        if HWM:
            self.s.setsockopt(zmq.HWM, HWM);
        self.s.connect(zmq_conn_string)

    def run(self):
        while(True):
            msg = self.s.recv(copy=True)
            try:
                log.debug('subgateway, received %s', msg)
                for k in self.proxies.keys():
                    if self.proxies[k].msgfilter in msg:
                        self.send_proxy(k, msg)
            except Exception as e:
                log.exception(e)
                continue

    def start(self):
        self.thread = spawn(self.run)
        
class RepGateway(ZmqGateway):
    def __init__(self, zmq_conn_string, HWM, ctx=None):
        super(RepGateway, self).__init__(zmq_conn_string, ctx=ctx)
        self.s = ctx.socket(zmq.XREP)
        if HWM:
            self.s.setsockopt(zmq.HWM, 100);
        self.s.bind(zmq_conn_string)
        self.queue = Queue.Queue()
        self.addresses = {}
        
    def send(self, identity, msg):
        self.queue.put(msg)

    def _send(self, multipart_msg):
        multipart_msg = [str(x) for x in multipart_msg]
        log.debug('sending %s', multipart_msg)
        self.s.send_multipart(multipart_msg)
        
    def run_recv_zmq(self):    
        while True:
            msg = self.s.recv_multipart(copy=True)
            log.debug('received %s', msg)
            try:
                target_ident = msg[-1]
                address_idx = msg.index('')
                address_data = msg[:address_idx]
                hashval = hashlib.sha1(str(address_data)).hexdigest()
                self.addresses[hashval] = address_data
                newmsg = [hashval] + [str(x) for x in \
                                      msg[address_idx:-1]]
                msg = simplejson.dumps(newmsg)
                self.send_proxy(target_ident, msg)
            except:
                pass
            
    def run_send_zmq(self):
        while True:
            try:
                obj = self.queue.get()
                log.debug('ws received %s', obj)
                obj = simplejson.loads(obj)
                address_data = self.addresses[obj[0]]
                self._send(address_data + obj[1:])
            except:
                pass
            
    def start(self):
        self.thread_recv = spawn(self.run_recv_zmq)
        self.thread_send = spawn(self.run_send_zmq)
    
class ReqGateway(ZmqGateway):
    def __init__(self, zmq_conn_string, HWM, ctx=None):
        super(ReqGateway, self).__init__(zmq_conn_string, ctx=ctx)
        self.s = ctx.socket(zmq.XREQ)
        if HWM:
            self.s.setsockopt(zmq.HWM, 100);
        self.s.connect(zmq_conn_string)
        self.queue = Queue.Queue()

    def send(self, identity, msg):
        self.queue.put((identity, msg))

    def _send(self, identity, msg):
        #append null string to front of message, just like REQ
        #embed identity the same way
        self.s.send_multipart([str(identity), '', str(msg)])
        #log.debug('reqgateway, sent %s', msg)

    def handle_request(self, msg):
        #strip off the trailing string
        identity = msg[0]
        msg = msg[-1]
        self.send_proxy(identity, msg)

    def start(self):
        self.thread_recv = spawn(self.run_recv_zmq)
        self.thread_send = spawn(self.run_send_zmq)
        
    def run_recv_zmq(self):
        while True:
            msg = self.s.recv_multipart(copy=True)
            try:
                log.debug('reqgateway, received %s', msg)
                self.handle_request(msg)
            except Exception as e:
                log.exception(e)
                continue

    def run_send_zmq(self):
        while True:
            try:
                obj = self.queue.get()
                identity, msg = obj
                self._send(identity, msg)
            except:
                pass
            
class BridgeWebProxyHandler(WebProxyHandler):
    """
    should rename this to BridgeWebSocketGateway
    proxy handler which handles the web socket side of things.
    you have one of these per web socket connection.  it listens on the web
    socket, and when a connection request is received, grabs the appropriate
    zeromq gateway from the factory.  It also registers the proxy with this
    object nad the zeromq gateway
    """
    
    def __init__(self, ws, gateway_factory):
        super(BridgeWebProxyHandler, self).__init__()
        self.ws = ws
        self.gateway_factory = gateway_factory
        
    def zmq_allowed(self, options):
        return True
    
    def connect(self, identity, content):
        content = simplejson.loads(content);
        zmq_conn_string = content['zmq_conn_string']
        socket_type = content['socket_type']
        if socket_type == zmq.REQ:
            proxy = ReqSocketProxy(identity)
        elif socket_type == zmq.REP:
            proxy = RepSocketProxy(identity)
        else:
            proxy = SubSocketProxy(identity, content.get('msgfilter', ''))
        gateway = self.gateway_factory.get(socket_type, zmq_conn_string)
        proxy.register(self, gateway)
                
    def handle_request(self, msg):
        msg = simplejson.loads(msg)
        
        msg_type = msg.get('msg_type')
        identity = msg.get('identity')
        content = msg.get('content')
        
        if msg_type == 'connect':
            if self.zmq_allowed(content):
                self.connect(identity, content)
                content = simplejson.dumps({'status' : 'success'})
                self.send(identity, content, msg_type='connection_reply')
            else:
                content = simplejson.dumps({'status' : 'error'})
                self.send(identity, content, msg_type='connection_reply')
        else:
            self.send_proxy(identity, content)
            
    def send_proxy(self, identity, content):
        try:
            self.proxies[identity].send_zmq(content)
        #what exception is thrown here?
        except Exception as e:
            log.exception(e)
            self.deregister(identity)

    def send(self, identity, msg, msg_type=None):
        json_msg = {'identity' : identity,
                    'content' : msg}
        if msg_type is not None:
            json_msg['msg_type'] = msg_type
        log.debug('ws sent %s', json_msg)
        self.ws.send(simplejson.dumps(json_msg))
        
    def run(self):
        while True:
            msg = self.ws.receive()
            #log.debug('ws received %s', msg)
            if msg is None:
                self.close()
                break
            self.handle_request(msg)

"""these proxy objects below are dumb objects.  all they do is manage
relationships with their reqpective websocket and zeromq gateways.
the gateways use this object to get to the appropriate opposing gateway
SocketProxy
ReqSocketProxy
SubSocketProxy
you have one instance of this, for every fake zeromq socket you have on the
js side
"""
class SocketProxy(object):

    def __init__(self, identity):
        self.identity = identity

    def register(self, wsgateway, zmqgateway):
        self.wsgateway = wsgateway
        self.zmqgateway = zmqgateway
        wsgateway.register(self.identity, self)
        zmqgateway.register(self.identity, self)

    def deregister(self):
        self.wsgateway.deregister(self.identity)
        self.zmqgateway.deregister(self.identity)
        
    def send_web(self, msg):
        self.wsgateway.send(self.identity, msg)

    def send_zmq(self, msg):
        self.zmqgateway.send(self.identity, msg)
        
class ReqSocketProxy(SocketProxy):
    socket_type = zmq.REQ
    
class RepSocketProxy(SocketProxy):
    socket_type = zmq.REP


class SubSocketProxy(SocketProxy):
    socket_type = zmq.SUB
    def __init__(self, identity, msgfilter):
        super(SubSocketProxy, self).__init__(identity)
        self.msgfilter = msgfilter



"""
Gevent wsgi handler - the main server.  once instnace of this per process
"""
class WsgiHandler(object):
    bridge_class = BridgeWebProxyHandler
    HWM = 100
    def __init__(self):
        self.zmq_gateway_factory = ZmqGatewayFactory(self.HWM)
        
    def websocket_allowed(self, environ):
        return True
    
    def wsgi_handle(self, environ, start_response):
        if 'wsgi.websocket' in environ and self.websocket_allowed(environ):
            handler = self.bridge_class(environ['wsgi.websocket'],
                                        self.zmq_gateway_factory)
            handler.run()
        else:
            start_response("404 Not Found", [])
            return []

    def __del__(self):
        """
        Upon destruction shut down any open sockets, don't rely
        on the garbage collector which can leave sockets
        dangling open.
        """
        self.zmq_gateway_factory.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = WsgiHandler()
    server = pywsgi.WSGIServer(('127.0.0.1', 8000), app.wsgi_handle,
                               # keyfile='/etc/nginx/server.key',
                               # certfile='/etc/nginx/server.crt',
                               handler_class=WebSocketHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Shutting down gracefully.'
        server.zmq_gateway_factory.shutdown()

########NEW FILE########
__FILENAME__ = bridgeutils
import zmq
import simplejson as jsonapi
import logging
log = logging.getLogger(__name__)

class RPCClient(object):
    def __init__(self, socket, ident, timeout=1000.0):
        self.socket = socket
        self.ident = ident
        self.timeout = timeout
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        
    def rpc(self, funcname, *args, **kwargs):
        msg = {'funcname' : funcname,
               'args' : args}
        self.socket.send_multipart(['', jsonapi.dumps(msg), self.ident])

        socks = dict(self.poller.poll(timeout=self.timeout))
        if self.socket in socks:
            message = self.socket.recv_multipart()
            print message
            msgobj = jsonapi.loads(message[-1])
            return msgobj.get('returnval', None)
        else:
            return None

class RPCServer(object):
    #none, means we can rpc any function
    #explicit iterable means, only those
    #functions in the iterable can be executed
    #(use a set)
    
    authorized_functions = None 
    
    def __init__(self, reqrep_socket, timeout=1000.0):
        self.reqrep_socket = reqrep_socket
        self.poller = zmq.Poller()
        self.poller.register(self.reqrep_socket, zmq.POLLIN)
        self.kill = False
        self.timeout = timeout
        
    def run_rpc(self):
        while True:
            #the follow code must be wrapped in an exception handler
            #we don't know what we're getting
            socks = dict(self.poller.poll(timeout=self.timeout))
            if self.reqrep_socket in socks:
                try:
                    msg = self.reqrep_socket.recv()
                    msgobj = jsonapi.loads(msg)
                    response_obj = self.get_response(msgobj)
                    response = jsonapi.dumps(response_obj)
                except Exception as e:
                    log.exception(e)
                    response_obj = self.error_obj('unknown ooger')
                    response = jsonapi.dumps(response_obj)
                self.reqrep_socket.send(jsonapi.dumps(response_obj))
            else:
                if self.kill:
                    break

    def error_obj(self, error_msg):
        return {'status' : 'error',
                'error_msg' : error_msg}
    
    def returnval_obj(self, returnval):
        return {'returnval' : returnval}
    
    def get_response(self, msgobj):
        funcname = msgobj['funcname']
        args = msgobj.get('args', [])
        kwargs = msgobj.get('kwargs', {})
        auth = False
        if self.authorized_functions is not None \
           and funcname not in self.authorized_functions:
            return self.error_obj('unauthorized access')
          
        if hasattr(self, 'can_' + funcname):
            auth = self.can_funcname(*args, **kwargs)
            if not auth:
                return self.error_obj('unauthorized access')
            
        func = getattr(self, funcname)
        retval = func(*args, **kwargs)
        return self.returnval_obj(retval)

########NEW FILE########
__FILENAME__ = pyzmq_pub
import zmq
import time

c = zmq.Context()
s = c.socket(zmq.PUB)
s.bind('tcp://127.0.0.1:10002')
while(True):
    for c  in  range(100):
        print c
        s.send(str(c))
        time.sleep(1)

    

########NEW FILE########
__FILENAME__ = pyzmq_rep_server
import gevent.monkey
gevent.monkey.patch_all()
from gevent_zeromq import zmq
import gevent
import time

c = zmq.Context()
s = c.socket(zmq.XREP)
s.bind('tcp://127.0.0.1:10001')
ident = None
def loop():
    global ident
    while True:
        print 'starting'
        msg = s.recv_multipart()
        print 'received', msg
        if 'IDENT' in msg[-1]:
            ident = msg[-1].split()[-1]
        s.send_multipart(msg)
reploop = gevent.spawn(loop)
s2 = c.socket(zmq.REQ)
s2.connect('tcp://127.0.0.1:10003')

import geventbridgeutils
while True:
    if ident is None:
        gevent.sleep(1)
    else:
        rpcclient = geventbridgeutils.GeventRPCClient(s2, ident, timeout=1000.0)
        break
        
while(True):
    for c  in  range(100):
        print 'sending %s' % c
        retval = rpcclient.rpc('echo', c);
        print 'got %s' % retval
        print type(retval)
        gevent.sleep(1)

    




########NEW FILE########
__FILENAME__ = pyzmq_req_client
import zmq
import time

c = zmq.Context()
s = c.socket(zmq.REQ)
s.connect('tcp://127.0.0.1:10003')
while(True):
    for c  in  range(100):
        print 'sending %s' % c
        s.send(str(c))
        print s.recv();
        time.sleep(1)

    

########NEW FILE########
__FILENAME__ = test
import gevent
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import logging
import bridge
import simplejson
logging.basicConfig(level=logging.DEBUG)
class MyBridgeClass(bridge.BridgeWebProxyHandler):
    def zmq_allowed(self, params):
        params = simplejson.loads(params)
        zmq_conn_string = params['zmq_conn_string']
        socket_type = params['socket_type']
        print 'auth', params['username'], params['socket_type']
        return params['username'] == 'hugo'
        

class MyWsgiHandler(bridge.WsgiHandler):
    bridge_class = MyBridgeClass
    def websocket_allowed(self, environ):
        #you can add logic here to do auth
        return True


app = MyWsgiHandler()
server = pywsgi.WSGIServer(('0.0.0.0', 8000), app.wsgi_handle,
                           # keyfile='/etc/nginx/server.key',
                           # certfile='/etc/nginx/server.crt',
                           handler_class=WebSocketHandler)
server.serve_forever()


########NEW FILE########
__FILENAME__ = geventbridgeutils
import gevent
import gevent.queue
from gevent_zeromq import zmq
import logging
log = logging.getLogger(__name__)
import simplejson
from gevent import spawn
import collections
import logging
import time
log = logging.getLogger('__name__')
jsonapi = simplejson

class GeventZMQRPC(object):
    #none, means we can rpc any function
    #explicit iterable means, only those
    #functions in the iterable can be executed
    #(use a set)
    
    authorized_functions = None 
    
    def __init__(self, reqrep_socket):
        self.reqrep_socket = reqrep_socket

    def run_rpc(self):
        while True:
            try:
                #the follow code must be wrapped in an exception handler
                #we don't know what we're getting
                msg = self.reqrep_socket.recv()
                msgobj = jsonapi.loads(msg)
                response_obj = self.get_response(msgobj)
                response = jsonapi.dumps(response_obj)
                
            except Exception as e:
                log.exception(e)
                response_obj = self.error_obj('unknown error')
                response = jsonapi.dumps(response_obj)
                
            self.reqrep_socket.send(jsonapi.dumps(response_obj))

    def error_obj(self, error_msg):
        return {'status' : 'error',
                'error_msg' : error_msg}
    
    def returnval_obj(self, returnval):
        return {'returnval' : returnval}
    
    def get_response(self, msgobj):
        funcname = msgobj['funcname']
        args = msgobj.get('args', [])
        kwargs = msgobj.get('kwargs', {})
        auth = False
        if self.authorized_functions is not None \
           and funcname not in self.authorized_functions:
            return self.error_obj('unauthorized access')
          
        if hasattr(self, 'can_' + funcname):
            auth = self.can_funcname(*args, **kwargs)
            if not auth:
                return self.error_obj('unauthorized access')
            
        func = getattr(self, funcname)
        retval = func(*args, **kwargs)
        return self.returnval_obj(retval)
        
                       
        
class PubSubRPCClient(object):
    def __init__(self, socket):
        self.socket = socket
        self.queue = gevent.queue.Queue()
        
    def rpc(self, funcname, *args, **kwargs):
        msg = {'funcname' : funcname,
               'args' : args}
        self.queue.put(jsonapi.dumps(msg))

    def run_pub(self):
        while True:
            msg = self.queue.get()
            self.socket.send(msg)
                        

class GeventRPCClient(object):
    def __init__(self, socket, ident, timeout=1.0):
        self.socket = socket
        self.ident = ident
        self.queue = gevent.queue.Queue()
        self.timeout = timeout
        
    def rpc(self, funcname, *args, **kwargs):
        msg = {'funcname' : funcname,
               'args' : args}
        self.socket.send_multipart([jsonapi.dumps(msg), self.ident])
        data = []
        def recv():
            val = self.socket.recv()
            data.append(val)
        recv_t = gevent.spawn(recv)
        recv_t.join(timeout=self.timeout)
        recv_t.kill()
        if len(data) == 1:
            return jsonapi.loads(data[0])['returnval']
        else:
            return None
        
    def run_send(self):
        while True:
            msg = self.queue.get()
            self.socket.send(msg)
        
                       

########NEW FILE########
__FILENAME__ = client
import numpy as np
import websocket
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
from geventwebsocket.handler import WebSocketHandler
import bridge
from gevent import pywsgi
import time
import logging
log = logging.getLogger(__name__)
import simplejson
logging.basicConfig(level=logging.INFO)
import uuid

with open("rrports.txt","r") as f:
    ports = [int(x) for x in f.read().split(",")]
results = {}
def test(port, sock_type, num_reqs):
    identity = str(uuid.uuid4())
    results[port, identity] = 0
    sock = websocket.WebSocket()
    sock.io_sock.settimeout(1.0)
    zmq_conn_string = "tcp://127.0.0.1:" + str(port)
    sock.connect('ws://127.0.0.1:9000')
    auth = {
        'zmq_conn_string' : zmq_conn_string,
        'socket_type' : sock_type
        }
    auth = simplejson.dumps(auth)
    sock.send(simplejson.dumps(
        {
            'identity' : identity,
            'msg_type' : 'connect',
            'content' : auth
        }))
    msg = sock.recv()
    for c in range(num_reqs):
        try:
            sock.send(simplejson.dumps(
                {'identity' : identity,
                 'msg_type' : 'user',
                 'content' : identity}))
            msg = sock.recv()
            log.debug(msg)
            assert simplejson.loads(msg)['content'] == identity
            #print identity
            results[port, identity] += 1
        except:
            pass
    sock.close()

num_reqs = 100
num_per_port = 10
num_ports = len(ports)
while True:
    threads = []
    for p in ports:
        for c in range(num_per_port):
            threads.append(spawn(test, p, zmq.REQ, num_reqs))
    #threads = [spawn(test, p, zmq.REQ, 100) for p in ports]
    def report():
        while(True):
            log.info("%s, %s, %s", len(results),
                      np.sum(np.array(results.values())),
                      num_reqs * num_per_port * num_ports)
            gevent.sleep(1)
    threads.append(spawn(report))
    gevent.sleep(5.0)
    [x.kill() for x in threads]

########NEW FILE########
__FILENAME__ = run_bridge
import numpy as np
import websocket
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
from geventwebsocket.handler import WebSocketHandler
import bridge
from gevent import pywsgi
import time
import logging
log = logging.getLogger(__name__)
import simplejson
logging.basicConfig(level=logging.INFO)

app = bridge.WsgiHandler()
server = pywsgi.WSGIServer(('0.0.0.0', 9000), app.wsgi_handle,
                           handler_class=WebSocketHandler)
server.serve_forever()




########NEW FILE########
__FILENAME__ = server
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
import time
import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

num_reqrep = 20
rr = []
def rr_test(s):
    while True:
        msg = s.recv()
        log.debug(msg)
        s.send(msg)
ctx = zmq.Context()
for c in range(num_reqrep):
    s = ctx.socket(zmq.REP)
    s.setsockopt(zmq.HWM, 100)
    port = s.bind_to_random_port("tcp://127.0.0.1")
    t = spawn(rr_test, s)
    rr.append((s,t, port))

with open("rrports.txt","w+") as f:
    f.write(",".join([str(x[-1]) for x in rr]))

threads = [x[1] for x in rr]
gevent.joinall(threads)






########NEW FILE########
__FILENAME__ = basic_test
import unittest
import websocket
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
from geventwebsocket.handler import WebSocketHandler
import bridge
from gevent import pywsgi
import time
import logging
log = logging.getLogger(__name__)
import simplejson
import test_utils
wait_until = test_utils.wait_until
connect = test_utils.connect
port = 10010
class ReqRepTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.reqrep = self.ctx.socket(zmq.REP)
        self.rr_port = self.reqrep.bind_to_random_port("tcp://127.0.0.1")
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', port), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)
        self.rr_thread = spawn(self.rr_func)

    def rr_func(self):
        while True:
            msg = self.reqrep.recv()
            self.reqrep.send(msg)
            
    def tearDown(self):
        self.rr_thread.kill()
        self.bridge_thread.kill()

        
    def test_reqrep(self):
        sock = connect(self.server, "ws://127.0.0.1:" + str(port),
                       'tcp://127.0.0.1:' + str(self.rr_port),
                       zmq.REQ)
        sock.send(simplejson.dumps(
            {
                'identity' : 'testidentity',
                'msg_type' : 'user',
                'content' : 'MYMSG'
            }))
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        assert msgobj['content'] == 'MYMSG'
        

class SubTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub_port = self.pub.bind_to_random_port("tcp://127.0.0.1")
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', port), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)

    def tearDown(self):
        self.bridge_thread.kill()

    def test_sub(self):
        sock = connect(self.server, "ws://127.0.0.1:" + str(port),
                       'tcp://127.0.0.1:' + str(self.pub_port),
                       zmq.SUB)
        self.pub.send('hellohello')
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        assert msgobj['identity'] == 'testidentity'
        assert msgobj['content'] == 'hellohello'
        self.pub.send('boingyboingy')
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        assert msgobj['identity'] == 'testidentity'
        assert msgobj['content'] == 'boingyboingy'
        
class ClientRepTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.reqrep = self.ctx.socket(zmq.REQ)
        self.reqrep.connect("tcp://127.0.0.1:101010")
        self.req_port = 101010
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', port), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)
        self.ws_thread = spawn(self.ws_reqrep)

        
    def tearDown(self):
        self.bridge_thread.kill()
        self.ws_thread.kill()
    
    def ws_reqrep(self):
        sock = connect(self.server, "ws://127.0.0.1:" + str(port),
                       'tcp://127.0.0.1:' + str(self.req_port),
                       zmq.REP)
        while True:
            msg = sock.recv()
            log.debug(msg)
            msgobj = simplejson.loads(msg)
            sock.send(msg)
            
    def test_req_rep(self):
        self.reqrep.send_multipart(['hello', 'testidentity'])
        a = self.reqrep.recv_multipart()
        assert a[0] == 'hello'

########NEW FILE########
__FILENAME__ = rpc_test
import unittest
import websocket
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
from geventwebsocket.handler import WebSocketHandler
import bridge
from gevent import pywsgi
import time
import logging
log = logging.getLogger(__name__)
import simplejson
import test_utils
wait_until = test_utils.wait_until
connect = test_utils.connect
import bridgeutils
import geventbridgeutils

port = 10020

class TestRPC(geventbridgeutils.GeventZMQRPC):
    def echo(self, msg):
        return msg
        
class ReqRepTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.reqrep = self.ctx.socket(zmq.REP)
        self.rr_port = self.reqrep.bind_to_random_port("tcp://127.0.0.1")
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', 9999), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)
        self.rpc = TestRPC(self.reqrep)
        self.rr_thread = spawn(self.rpc.run_rpc)
            
    def tearDown(self):
        self.rr_thread.kill()
        self.bridge_thread.kill()

    def test_reqrep(self):
        sock = connect(self.server, "ws://127.0.0.1:9999",
                       'tcp://127.0.0.1:' + str(self.rr_port),
                       zmq.REQ)

        rpc_request_obj = {'funcname' : 'echo',
                       'args' : ['echome'],
                       'kwargs' : {}}
        rpc_request_msg = simplejson.dumps(rpc_request_obj)
        sock.send(simplejson.dumps(
            {
                'identity' : 'testidentity',
                'msg_type' : 'user',
                'content' : rpc_request_msg
            }))
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        payload = msgobj['content']
        payload = simplejson.loads(payload)
        payload = payload['returnval']
        assert payload == 'echome'
        

class SubTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub_port = self.pub.bind_to_random_port("tcp://127.0.0.1")
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', 9999), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)

    def tearDown(self):
        self.bridge_thread.kill()

    def test_sub(self):
        sock = connect(self.server, "ws://127.0.0.1:9999",
                       'tcp://127.0.0.1:' + str(self.pub_port),
                       zmq.SUB)
        self.pub.send('hellohello')
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        assert msgobj['identity'] == 'testidentity'
        assert msgobj['content'] == 'hellohello'
        self.pub.send('boingyboingy')
        msg = sock.recv()
        msgobj = simplejson.loads(msg)
        assert msgobj['identity'] == 'testidentity'
        assert msgobj['content'] == 'boingyboingy'
        
        
        
class ClientRepTest(unittest.TestCase):
    def setUp(self):
        self.ctx = zmq.Context()
        self.reqrep = self.ctx.socket(zmq.REQ)
        self.reqrep.connect("tcp://127.0.0.1:9010")
        self.req_port = 9010
        self.app = bridge.WsgiHandler()
        self.server = pywsgi.WSGIServer(('0.0.0.0', port), self.app.wsgi_handle,
                                        handler_class=WebSocketHandler)
        self.bridge_thread = spawn(self.server.serve_forever)
        self.ws_thread = spawn(self.ws_reqrep)

        
    def tearDown(self):
        self.bridge_thread.kill()
        self.ws_thread.kill()
    
    def ws_reqrep(self):
        sock = connect(self.server, "ws://127.0.0.1:" + str(port),
                       'tcp://127.0.0.1:' + str(self.req_port),
                       zmq.REP)
        while True:
            msg = sock.recv()
            log.debug(msg)
            msgobj = simplejson.loads(msg)
            sock.send(msg)
            
    def test_req_rep(self):
        self.reqrep.send_multipart(['hello', 'testidentity'])
        a = self.reqrep.recv_multipart()
        assert a[0] == 'hello'

########NEW FILE########
__FILENAME__ = test_utils
import unittest
import websocket
from gevent_zeromq import zmq
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import spawn
from geventwebsocket.handler import WebSocketHandler
import bridge
from gevent import pywsgi
import time
import logging
log = logging.getLogger(__name__)
import simplejson

def wait_until(func, timeout=1.0, interval=0.01):
    st = time.time()
    while True:
        if func():
            return True
        if (time.time() - st) > interval:
            return False
        gevent.sleep(interval)

def connect(server, ws_address, zmq_conn_string, sock_type):
    wait_until(lambda : server.started)
    sock = websocket.WebSocket()
    sock.io_sock.settimeout(1.0)
    sock.connect(ws_address)
    auth = {
        'zmq_conn_string' : zmq_conn_string,
        'socket_type' : sock_type
        }
    auth = simplejson.dumps(auth)
    sock.send(simplejson.dumps(
        {
            'identity' : 'testidentity',
            'msg_type' : 'connect',
            'content' : auth
        }))
    msg = sock.recv()
    msgobj = simplejson.loads(msg)
    msgobj = simplejson.loads(msgobj['content'])
    assert msgobj['status']        
    return sock

########NEW FILE########
