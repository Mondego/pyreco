__FILENAME__ = authstat
"""
Roomahost Authentication and Stats Module.

This module is responsible to communicate with external
authentication and stats module.

Function that  communicate with external auth & stats server:
* report_usage
  report traffic usage to server
* client_status
  get client status
* get_client_own_domain
  get own-domain of some client
"""
import time

import jsonrpclib
from gevent import coros

import rhconf

#Client status
RH_STATUS_OK = 0
RH_STATUS_NOT_FOUND = 1
RH_STATUS_QUOTA_EXCEEDED = 2
RH_STATUS_UNKNOWN_ERROR = 100

CL_STATUS_TAB = {}
cl_status_sem = coros.Semaphore()

def report_usage(username, trf_req, trf_rsp):
    '''Report data transfer usage.'''
    stat_server = jsonrpclib.Server(rhconf.AUTH_SERVER_URL)
    res = stat_server.usage_add(username, trf_req, trf_rsp)
    return res

def client_status(username):
    """Get client status."""
    status = cache_status_get(username)
    if status is not None:
        return status
    
    auth_server = jsonrpclib.Server(rhconf.AUTH_SERVER_URL)
    status = auth_server.status(username)
    if status != RH_STATUS_NOT_FOUND:
        cache_status_set(username, status)
    return status

def get_client_own_domain(host):
    '''Get client name that have own-domain.'''
    server = jsonrpclib.Server(rhconf.AUTH_SERVER_URL)
    res = server.rh_domain_client(host)
    return res

def client_status_msg(status, username):
    if status == RH_STATUS_NOT_FOUND:
        return client_notfound_str(username)

def cache_status_get(username):
    """get status from cache.
    return None if it can't found from cache
    or if cache exceed treshold."""
    try:
        cl_status_sem.acquire()
        st = CL_STATUS_TAB[username]
        cl_status_sem.release()
        
        if (time.time() - st['time']) <= rhconf.CACHE_STATUS_SECONDS:
            return st['status']
    except Exception:
        cl_status_sem.release()
        return None
    
def cache_status_set(username, status):
    #update cache
    ts = time.time()
    cl_status_sem.acquire()
    CL_STATUS_TAB[username] = {
        'time' : ts,
        'status' : status,
    }
    cl_status_sem.release()

def cache_status_del(username):
    try:
        cl_status_sem.acquire()
        del CL_STATUS_TAB[username]
    finally:
        cl_status_sem.release()

def client_notfound_str(username):
    html = "HTTP/1.1\n\
Server: roomahost/0.1\n\
Content-Type: text/html\n\
Connection: close\n\
\r\n\
"
    html += "<html><body>"
    html += "<center><big><b>" + username + " </b> is not registered</big></center>"
    html += "</body></html>"
    return html

def quota_exceeded_msg(username):
    html = "HTTP/1.1\n\
Server: roomahost/0.1\n\
Content-Type: text/html\n\
Connection: close\n\
\r\n\
"
    html += "<html><body>"
    html += "<center><big><b>" + username + "  : </b> Quota Exceeded</big></center>"
    html += "</body></html>"
    return html

def unknown_err_msg(username):
    html = "HTTP/1.1\n\
Server: roomahost/0.1\n\
Content-Type: text/html\n\
Connection: close\n\
\r\n\
"
    html += "<html><body>"
    html += "<center><big><b>" + username + " : </b> Unknown Error</big></center>"
    html += "</body></html>"
    return html
########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
"""
Roomahost client
Copyright(2012) Iwan Budi Kusnanto
"""
import sys
import socket
import select
import time
import datetime
import logging
import ConfigParser

import packet
import mysock

SERV_BUF_LEN = 1024
HOST_BUF_LEN = SERV_BUF_LEN - packet.MIN_HEADER_LEN

HOST_CONNS_DICT = {}

logging.basicConfig(level = logging.INFO, format='%(asctime)s : %(levelname)s : %(message)s')
LOG = logging.getLogger("rhclient")

LOCAL_STATUS_OK = 0
LOCAL_STATUS_DOWN = 1

class HostConn:
    '''Connection to host.'''
    def __init__(self, ses_id):
        self.sock = None
        self.ses_id = ses_id
        self.ended = False
        self.rsp_list = []
        self.first_rsp_recvd = False
    
    def reset(self):
        '''reset semua value (set None).'''
        try:
            self.sock.close()
        except Exception:
            pass
        
        self.sock = None
        self.rsp_list = []

class HostRsp:
    '''Response from host.'''
    def __init__(self, h_conn, payload):
        self.conn = h_conn
        self.payload = payload
        
        
def clean_host_conn():
    '''Clean HostConn.
    
    HostConn that will be deleted:
        hostconn that marked as ended
        host conn with empty rsp_list
    '''
    to_del = []
    for h_conn in HOST_CONNS_DICT.itervalues():
        if h_conn.ended == True and len(h_conn.rsp_list) == 0:
            to_del.append(h_conn)
    
    for h_conn in to_del:
        del_host_conn(h_conn.ses_id, h_conn)

def get_host_conn_by_sock(sock):
    '''Get HostConn object from a socket to host.'''
    if sock == None:
        return None
    
    for h_conn in HOST_CONNS_DICT.itervalues():
        if h_conn.sock == sock:
            return h_conn
    
    return None

def del_host_conn(ses_id, h_conn = None):
    '''Del HostConn by ses_id.'''
    conn = h_conn
    if conn == None:
        try:
            conn = HOST_CONNS_DICT[ses_id]
        except KeyError:
            LOG.debug("key_error")
            return 
    conn.reset()
    del HOST_CONNS_DICT[ses_id]

def forward_incoming_req_pkt(ba_req, ba_len, host_host, host_port):
    '''Forward incoming req packet to host.'''
    req = packet.DataReq(ba_req)
    if req.cek_valid() == False:
        LOG.fatal("Bad DATA-REQ packet")
        return
    
    ses_id = req.get_sesid()
    req_data = req.get_data()
    #req_data = rewrite_req(req_data, host_host, host_port)
    LOG.debug("ses_id=%d" % ses_id)
    
    try:
        h_conn = HOST_CONNS_DICT[ses_id]
        LOG.debug("use old connection.ses_id = %d" % h_conn.ses_id)
    except KeyError:
        h_conn = HostConn(ses_id)
        h_conn.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _, err = mysock.connect(h_conn.sock, (host_host, host_port))
        if err != None:
            LOG.fatal("Connection to %s port %d failed." % (host_host, host_port))
            LOG.fatal("Please check your local web server")
            return LOCAL_STATUS_DOWN, ses_id
        HOST_CONNS_DICT[ses_id] = h_conn
    
    h_sock = h_conn.sock
    written, err = mysock.send_all(h_sock, req_data)
    if err != None:
        print "error forward"
        del HOST_CONNS_DICT[ses_id]
        sys.exit(-1)
    
    if written != len(req_data):
        print "PARTIAL FORWARD to host"
        print "FATAL UNHANDLED COND"
        sys.exit(-1)
    
    return LOCAL_STATUS_OK, ses_id

def accept_host_rsp(h_sock):
    '''accept host response.
    enqueue it to rsp_list.
    '''
    #get HostConn object
    h_conn = get_host_conn_by_sock(h_sock)
    if h_conn == None:
        print "FATAL UNHANDLED ERROR:can't get h_conn"
        sys.exit(-1)
        
    #receive the response
    ba_rsp, err = mysock.recv(h_sock, HOST_BUF_LEN)
    if err != None:
        print "FATAL ERROR. error recv resp from host"
        sys.exit(-1)
    
    if len(ba_rsp) == 0:
        LOG.debug("ses_id %d closed", h_conn.ses_id)
        h_sock.close()
        h_conn.ended = True
    
    if h_conn.first_rsp_recvd == False:
        #ba = rewrite_first_rsp(ba, "192.168.56.10", 80, "paijo.master.lan", 80)
        h_conn.first_rsp_recvd = True
        
    h_conn.rsp_list.append(ba_rsp)
        
def _send_rsp_pkt_to_server(rsp_pkt, server_sock):
    '''Send response packet to server.'''
    written, err = mysock.send_all(server_sock, rsp_pkt.payload)
    if err != None:
        print "error sending packet to server"
        sys.exit(-1)
    
    if written != len(rsp_pkt.payload):
        print "partial write to server"
        sys.exit(-1)

def forward_host_rsp(server_sock):
    '''Forward Host response to server.'''
    for h_conn in HOST_CONNS_DICT.itervalues():
        if len(h_conn.rsp_list) > 0:
            ba_rsp = h_conn.rsp_list.pop(0)
            rsp_pkt = packet.DataRsp()
            rsp_pkt.build(ba_rsp, h_conn.ses_id)
    
            if len(ba_rsp) == 0:
                rsp_pkt.set_eof()
            
            _send_rsp_pkt_to_server(rsp_pkt, server_sock)
            
            if rsp_pkt.is_eof():
                h_conn.ended = True

def any_host_response():
    '''check if there is any host response.'''
    for h_conn in HOST_CONNS_DICT.itervalues():
        if len(h_conn.rsp_list) > 0:
            return True
    return False
        
class Client:
    '''Client class.'''
    PING_REQ_PERIOD = 120
    PING_RSP_WAIT_TIME = PING_REQ_PERIOD / 2
    
    def __init__(self, server_sock):
        self.last_ping = time.time()
        self.server_sock = server_sock
        self.to_server_pkt = []
        self.wait_ping_rsp = False
    
    def cek_ping_req(self):
        '''Check last ping
        enqueue ping packet if it exceeded ping period.'''
        if time.time() - self.last_ping >= Client.PING_REQ_PERIOD:
            preq = packet.PingReq()
            self.to_server_pkt.append(preq)
    
    def cek_ping_rsp(self):
        '''Check ping response.
        
        Return false if it exceeding PING_RSP_WAIT_TIME timeout.
        '''
        if not self.wait_ping_rsp:
            return True
        
        if time.time() - self.last_ping > Client.PING_RSP_WAIT_TIME:
            return False
        
        return True
    
    def handle_ping_rsp(self, ba_rsp):
        '''Handle PING-RSP.'''
        self.wait_ping_rsp = False
        self.last_ping = time.time()
    
    def handle_ctrl_pkt(self, ba_pkt):
        """Ctrl Packet Handling dispatcher."""
        pkt = packet.CtrlPkt(ba_pkt)
        if pkt.cek_valid() == False:
            return False
        
        pkt_type = pkt.get_type()
        if pkt_type == pkt.T_PEER_DEAD:
            ses_id = pkt.peer_dead_ses_id()
            self.handle_peer_dead(ses_id)
        else:
            print "Unknown control packet"
            sys.exit(-1)
        
    def handle_peer_dead(self, ses_id):
        """Deleting host conn with ses_id = peer's session id."""
        del_host_conn(ses_id)
        
    def send_to_server_pkt(self):
        '''Send a packet in to_server queue'''
        if len(self.to_server_pkt) == 0:
            return True
        
        pkt = self.to_server_pkt.pop(0)
        
        written, err = mysock.send_all(self.server_sock, pkt.payload)
        if (err != None) or (written != len(pkt.payload)):
            LOG.error("can't send pkt to server")
            return False
        
        if pkt.payload[0] == packet.TYPE_PING_REQ:
            self.last_ping = time.time()
            self.wait_ping_rsp = True
            
        return True
    
    def any_pkt_to_server(self):
        '''True if there is pkt to server.'''
        return len(self.to_server_pkt) > 0
    
    def send_ctrl_local_down(self, ses_id):
        """Send Local Down Ctrl packet to server."""
        pkt = packet.CtrlPkt()
        pkt.build_local_down(ses_id)
        self.to_server_pkt.append(pkt)

def do_auth(user, password, server_sock):
    """Doing roomahost authentication."""
    auth_req = packet.AuthReq()
    auth_req.build(user, password)
    
    written, err = mysock.send(server_sock, auth_req.payload)
    
    #sending packet failed
    if err != None or written < len(auth_req.payload):
        print "can't send auth req to server.err = ", err
        return False
    
    #receiving reply failed
    ba_rsp, err = mysock.recv(server_sock, 1024)
    if err != None:
        print "failed to get auth reply"
        return False
    
    #bad username/password
    rsp = packet.AuthRsp(ba_rsp)
    if rsp.get_val() != packet.AUTH_RSP_OK:
        print "Authentication failed"
        if rsp.get_val() == packet.AUTH_RSP_BAD_USERPASS:
            print "Bad user/password"
            print "Please check your user/password"
        return False
    return True

def client_loop(server, port, user, passwd, host_host, host_port):
    """Main client loop."""
    #connect to server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mysock.setkeepalives(server_sock)
    ret, err = mysock.connect(server_sock, (server, port))
    
    if err != None:
        LOG.error("can't connect to server")
        return
    
    if do_auth(user, passwd, server_sock) == False:
        sys.exit(1)
        
    LOG.info("Authentication successfull")
    
    client = Client(server_sock)
    
    #start looping
    while True:
        #cek last_ping
        client.cek_ping_req()
        
        #server_sock select()
        wsock = []
        if client.any_pkt_to_server() or any_host_response():
            wsock.append(server_sock)
            
        to_read, to_write, _ = select.select([server_sock],
            wsock, [], 1)
        
        if len(to_read) > 0:
            #read sock
            ba_pkt, err = packet.get_all_data_pkt(server_sock)
            if ba_pkt is None or err != None:
                LOG.error("Connection to server closed")
                break
            
            #request packet
            if ba_pkt[0] == packet.TYPE_DATA_REQ:
                local_status, ses_id = forward_incoming_req_pkt(ba_pkt, len(ba_pkt), host_host, host_port)
                if local_status == LOCAL_STATUS_DOWN:
                    client.send_ctrl_local_down(ses_id)
            
            #ping rsp
            elif ba_pkt[0] == packet.TYPE_PING_RSP:
                #print "PING-RSP ", datetime.datetime.now()
                client.handle_ping_rsp(ba_pkt)
            
            #ctrl packet
            elif ba_pkt[0] == packet.TYPE_CTRL:
                LOG.debug("CTRL Packet. subtype = %d" % ba_pkt[1])
                client.handle_ctrl_pkt(ba_pkt)
            else:
                LOG.error("Unknown packet.type = %d" % ba_pkt[0])
                LOG.fatal("exiting...")
                sys.exit(-1)
        
        if len(to_write) > 0:
            forward_host_rsp(server_sock)
            if client.send_to_server_pkt() == False:
                break
           
        clean_host_conn()
        
        #select() untuk host sock
        rlist = []
        for h_conn in HOST_CONNS_DICT.itervalues():
            if h_conn.sock != None and h_conn.ended == False:
                rlist.append(h_conn.sock)
        
        if len(rlist) > 0:      
            h_read, _, _ = select.select(rlist, [], [], 0.5)
        
            if len(h_read) > 0:
                for sock in h_read:
                    accept_host_rsp(sock)
        
        #cek ping rsp
        if client.cek_ping_rsp() == False:
            LOG.error("PING-RSP timeout")
            break
                
    LOG.error("Client disconnected")
    
        
if __name__ == '__main__':
    conf = ConfigParser.ConfigParser()
    conf.read("client.ini")
    
    SERVER = conf.get('roomahost', 'server')
    PORT = int(conf.get('roomahost','port'))
    USER = conf.get('roomahost','user')
    PASSWD = conf.get('roomahost','password')
    HOST_HOST = conf.get('roomahost','localhost_host')
    HOST_PORT = int(conf.get('roomahost','localhost_port'))
    AUTO_RECON_PERIOD = int(conf.get('roomahost','auto_reconnect_period'))
    
    LOG.info("roomahost server = %s" % SERVER)
    LOG.info("roomahost server port = %d" % PORT)
    LOG.info("roomahost user = %s" % USER)
    LOG.info("Local server = %s" % HOST_HOST)
    LOG.info("Local server port = %d" % HOST_PORT)
    LOG.info("Auto Reconnect Period = %d" % AUTO_RECON_PERIOD)
    
    while True:
        client_loop(SERVER, PORT, USER, PASSWD, HOST_HOST, HOST_PORT)
        if AUTO_RECON_PERIOD <= 0:
            break
        LOG.info("waiting for auto reconnection")
        time.sleep(AUTO_RECON_PERIOD)
        LOG.info("Reconnecting...")
########NEW FILE########
__FILENAME__ = clientd
"""
Client Daemon
Copyright : Iwan Budi Kusnanto
"""
import select
import logging
import logging.handlers

import gevent
from gevent.server import StreamServer
import jsonrpclib

import packet
import mysock
import rhconf
import rhmsg

AUTH_RES_OK = 1
AUTH_RES_UNKNOWN_ERR = 0
AUTH_RES_PKT_ERR = -1

BUF_LEN = 1024
CM = None

LOG_FILENAME = rhconf.LOG_FILE_CLIENTD
logging.basicConfig(level=rhconf.LOG_LEVEL_CLIENTD)
LOG = logging.getLogger("clientd")
rotfile_handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=rhconf.LOG_MAXBYTE_CLIENTD,
    backupCount=10,
)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
rotfile_handler.setFormatter(formatter)
LOG.addHandler(rotfile_handler)
LOG.setLevel(rhconf.LOG_LEVEL_CLIENTD)

if rhconf.LOG_STDERR_CLIENTD:
    stderr_handler = logging.StreamHandler()
    LOG.addHandler(stderr_handler)


class Client:
    """Represent a client."""
    def __init__(self, user, sock, addr):
        self.ses_id = 1
        self.user = user
        self.addr = addr

        #socket for this user
        self.sock = sock
        
        #list of request packet from peer
        self.req_pkt = []
        
        #list of ctrt packet
        self.ctrl_pkt = []
        
        #true if this client is waiting for PING-RSP
        self.wait_ping_rsp = False
        
        #dict of peers mq
        self.peers_mq = {}
        
        #input mq
        self.in_mq = gevent.queue.Queue(10)
        
        #if dead
        self.dead = False
    
    def disconnect(self):
        """Disconnect this client."""
        if self.sock:
            print "closing the socket"
            self.sock.close()

    def _add_peer(self, in_mq):
        '''Add a peer to this client.'''
        ses_id = self._gen_ses_id()
        if ses_id < 0:
            return None
        self.peers_mq[ses_id] = in_mq
        
        return ses_id
    
    def _del_peer(self, ses_id):
        '''Del peer from this client.'''
        del self.peers_mq[ses_id]
    
    def _do_process_msg(self):
        '''process message.'''
        try:
            msg = self.in_mq.get_nowait()
        except gevent.queue.Empty:
            return 0
        
        if msg['mt'] == rhmsg.CL_ADDPEER_REQ:
            """Add peer request handler.
            Ses id will be set to None if there is no ses_id left."""
            q_rep = msg['q']
            ses_id = self._add_peer(msg['in_mq'])
            
            rsp = {}
            rsp['mt'] = rhmsg.CL_ADDPEER_RSP
            rsp['ses_id'] = ses_id
            try:
                q_rep.put(rsp)
            except gevent.queue.Full:
                pass
            
        elif msg['mt'] == rhmsg.CL_DELPEER_REQ:
            #print "[Client]del peer with ses_id=", msg['ses_id']
            ses_id = msg['ses_id']
            self._del_peer(ses_id)
            
        elif msg['mt'] == rhmsg.CL_ADD_REQPKT_REQ:
            self._add_req_pkt(msg['req_pkt'])
        else:
            LOG.error("Client.process_msg.unknown_message")
        
        return 1
    
    def process_msg(self):
        '''Process message to this client.'''
        for _ in xrange(0, 10):
            if self._do_process_msg() == 0:
                break
            
    def _inc_ses_id(self, ses_id):
        '''Increase session id.'''
        if ses_id == 255:
            return 1
        else:
            return ses_id + 1
    
    def _gen_ses_id(self):
        """Generate session id.
        return -1 if there is no ses_id left."""
        start_id = self.ses_id
        
        ses_id = start_id
        
        while ses_id in self.peers_mq.keys():
            ses_id = self._inc_ses_id(ses_id)
            if ses_id == start_id:
                return -1
            
        self.ses_id = self._inc_ses_id(ses_id)
        
        return ses_id
    
    def _add_req_pkt(self, req_pkt):
        '''add req pkt from to client's req_pkt list'''
        self.req_pkt.append(req_pkt)
    
    def req_pkt_fwd(self):
        '''Forward request packet to client.'''
        if len(self.req_pkt) == 0:
            return
        
        req = self.req_pkt.pop(0)
        
        req_pkt = packet.DataReq()
        req_pkt.build(req.payload, req.ses_id)
        
        written, err = mysock.send_all(self.sock, req_pkt.payload)
        
        if written != len(req_pkt.payload) or err != None:
            LOG.error("failed to send req pkt to client:%s" % self.user)
            self.dead = True
            return False
    
    def send_ctrl_pkt(self):
        '''send ctrl packet to client.'''
        if len(self.ctrl_pkt) == 0:
            return True
        
        LOG.debug("send ctrl pkt to client:%s" % self.user)
        
        pkt = self.ctrl_pkt.pop(0)
        written, err = mysock.send_all(self.sock, pkt.payload)
        if written != len(pkt.payload) or err != None:
            LOG.error("failed to send ctrl_pkt to:%s.type = %d" %
                      self.user, pkt.payload[1])
            self.dead = True
            return False
        return True
    
    def ping_rsp_send(self):
        '''Send PING-RSP to client.'''
        if self.wait_ping_rsp == False:
            return True
        
        p_rsp = packet.PingRsp()
        
        written, err = mysock.send_all(self.sock, p_rsp.payload)
        
        if err != None or (len(p_rsp.payload) != written):
            LOG.error("error sending PING-RSP to %s" % self.user)
            return False
        
        self.wait_ping_rsp = False
        
    def process_rsp_pkt(self, ba_rsp, rsp_len):
        '''Forwad response packet to peer.'''
        #len checking
        if rsp_len < packet.MIN_HEADER_LEN:
            LOG.error("FATAL:packet too small,discard.user = %s" % self.user)
            return
        
        if ba_rsp[0] == packet.TYPE_DATA_RSP:
            return self.process_datarsp_pkt(ba_rsp)
        elif ba_rsp[0] == packet.TYPE_CTRL:
            return self.process_ctrlrsp_pkt(ba_rsp)
        else:
            LOG.error("FATAL:unrecognized packet type = %s" % self.user)
            return
        
    def process_datarsp_pkt(self, ba_rsp):
        """Process Data Rsp Packet."""
        rsp = packet.DataRsp(ba_rsp)
        
        #get ses_id
        ses_id = rsp.get_sesid()
        
        if rsp.cek_valid() == False:
            LOG.error("FATAL :Not DATA-RSP.user = %s" % self.user)
            packet.print_header(rsp.payload)
            return False
        
        #get peer mq
        if ses_id not in self.peers_mq:
            """ses_id not found.
            - discard packet
            - kirim notifikasi ke client bahwa ses_id ini sudah dead."""
            LOG.debug("ses_id %d not found. peer already dead" % ses_id)
            peer_dead_pkt = packet.CtrlPkt()
            peer_dead_pkt.build_peer_dead(ses_id)
            self.ctrl_pkt.append(peer_dead_pkt)
            return
        
        peer_mq = self.peers_mq[ses_id]
        
        #send RSP-PKT to peer mq
        msg = {}
        msg['mt'] = rhmsg.PD_ADD_RSP_PKT
        msg['pkt'] = rsp
        
        peer_mq.put(msg)
    
    def process_ctrlrsp_pkt(self, ba_rsp):
        """Process Ctrl Rsp packet."""
        print "receive ctrl rsp"
        rsp = packet.CtrlPkt(ba_rsp)
        
        #get ses_id
        ses_id = rsp.get_ses_id()
        
        #get peer mq
        if ses_id not in self.peers_mq:
            """ses_id not found.
            - discard packet"""
            if rsp.is_local_down():
                """Client already closed the connection."""
                return
            else:
                """Send notification to client that this ses_id already died."""
                LOG.debug("ses_id %d not found. peer already dead" % ses_id)
                peer_dead_pkt = packet.CtrlPkt()
                peer_dead_pkt.build_peer_dead(ses_id)
                self.ctrl_pkt.append(peer_dead_pkt)
                return
        
        peer_mq = self.peers_mq[ses_id]
        
        #send RSP-PKT to peer mq
        msg = {}
        msg['mt'] = rhmsg.PD_ADD_RSP_PKT
        msg['pkt'] = rsp
        
        peer_mq.put(msg)

def client_auth_rpc(username, password):
    """Do client auth RPC call."""
    auth_server = jsonrpclib.Server(rhconf.AUTH_SERVER_URL)
    res = auth_server.rh_auth(str(username), str(password))
    return res


def client_auth(sock, addr):
    """Authenticate the client."""
    ba_req, err = mysock.recv(sock, BUF_LEN)
    if err != None:
        LOG.warning("can't recv auth req %s:%s" % addr)
        return None, AUTH_RES_UNKNOWN_ERR
    
    auth_req = packet.AuthReq(ba_req)
    if not auth_req.cek_valid():
        LOG.fatal("Bad AuthReq packet")
        return None, AUTH_RES_PKT_ERR
    
    auth_rsp = packet.AuthRsp()
    auth_res = AUTH_RES_OK
    
    user, password = auth_req.get_userpassword()
    if client_auth_rpc(user, password) != True:
        LOG.debug("auth rpc failed for user %s at %s" % (user, addr))
        auth_rsp.build(packet.AUTH_RSP_BAD_USERPASS)
        auth_res = AUTH_RES_UNKNOWN_ERR
    else:
        auth_rsp.build(packet.AUTH_RSP_OK)
        
    written, err = mysock.send_all(sock, auth_rsp.payload)
    if err != None or written < len(auth_rsp.payload):
        LOG.error("send auth reply failed.%s:%s" % addr)
        return user, AUTH_RES_UNKNOWN_ERR
    
    return user, auth_res


def unregister_client(client):
    """Unregister client from Client Manager."""
    msg = {}
    msg['mt'] = rhmsg.CM_DELCLIENT_REQ
    msg['user'] = client.user
    
    CM.in_mq.put(msg)

    
def register_client(user, in_mq):
    """Register client to Client Manager."""
    msg = {}
    msg['mt'] = rhmsg.CM_ADDCLIENT_REQ
    msg['user'] = user
    msg['in_mq'] = in_mq
    
    #send the message
    CM.in_mq.put(msg)
    
    #wait the reply
    return True

    
def handle_client(sock, addr):
    """Client handler."""
    LOG.debug("new client %s:%s" % addr)
    #client authentication
    user, auth_res = client_auth(sock, addr)
    if auth_res != AUTH_RES_OK:
        LOG.debug("AUTH failed.addr = %s:%s" % addr)
        return
    
    cli = Client(user, sock, addr)
    #register to client manager
    if register_client(cli.user, cli.in_mq) == False:
        LOG.fatal("REGISTER failed.user = %s" % cli.user)
        return
    
    while True:
        #process incoming messages
        cli.process_msg()
        
        #select() sock
        wlist = []
        if len(cli.req_pkt) > 0 or cli.wait_ping_rsp == True or     len(cli.ctrl_pkt) > 0:
            wlist.append(sock)
            
        rsocks, wsocks, _ = select.select([sock], wlist, [], 0.1)
        if len(rsocks) > 0:
            ba_pkt, err = packet.get_all_data_pkt(sock)
            if ba_pkt is None or err is not None:
                LOG.debug("read client sock err.exiting")
                break
            
            if ba_pkt[0] == packet.TYPE_DATA_RSP or ba_pkt[0] == packet.TYPE_CTRL:
                cli.process_rsp_pkt(ba_pkt, len(ba_pkt))
            elif ba_pkt[0] == packet.TYPE_PING_REQ:
                cli.wait_ping_rsp = True

        if len(wsocks) > 0:
            if cli.send_ctrl_pkt() == False:
                break
            #forward http request packet to client
            if cli.req_pkt_fwd() == False:
                break
            #send PING-RSP to client
            if cli.ping_rsp_send() == False:
                break

        gevent.sleep(0)
    
    unregister_client(cli)
    cli.disconnect()


def client_server(port):
    """Client daemon initialization function."""
    server = StreamServer(('0.0.0.0', port), handle_client)
    print 'Starting client server on port ', port
    server.serve_forever()

########NEW FILE########
__FILENAME__ = client_mgr
"""
Roomahost's Client Manager
Copyritght(2012) Iwan Budi Kusnanto
"""
import logging
import logging.handlers

import gevent.queue

import authstat
import rhmsg
import rhconf

LOG_FILENAME = rhconf.LOG_FILE_CM
logging.basicConfig(level = rhconf.LOG_LEVEL_CM)
LOG = logging.getLogger("cm")
rotfile_handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME,
    maxBytes = rhconf.LOG_MAXBYTE_CM,
    backupCount = 10
)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
rotfile_handler.setFormatter(formatter)
LOG.addHandler(rotfile_handler)
LOG.setLevel(rhconf.LOG_LEVEL_CM)


class ClientMgr(gevent.Greenlet):
    '''Client Manager.'''
    PUT_TIMEOUT_DEFAULT = 5
        
    def __init__(self):
        gevent.Greenlet.__init__(self)
        self.clients_mq = {}
        
        #queue of infinite size (gevent > 1.0)
        self.in_mq = gevent.queue.Queue(0)
    
    def _run(self):
        while True:
            msg = self.in_mq.get(block = True, timeout = None)
            self.proc_msg(msg)
            gevent.sleep(0)
            
    def _add_client(self, user, in_mq):
        self.clients_mq[str(user)] = in_mq
    
    def _del_client(self, user):
        try:
            del self.clients_mq[str(user)]
            authstat.cache_status_del(str(user))
        except KeyError:
            LOG.info("Del client : User %s not found"% str(user))
        
    def _get_client_mq(self, user_str):
        if user_str in self.clients_mq:
            return self.clients_mq[user_str]
        else:
            return None
    
    def proc_msg(self, msg):
        '''Memproses message dari client & peer.'''
        if msg['mt'] == rhmsg.CM_ADDCLIENT_REQ:
            '''Add Client Msg.'''
            user = msg['user']
            in_mq = msg['in_mq']
            LOG.info("add user=%s"% user)
            
            self._add_client(user, in_mq)
            
        elif msg['mt'] == rhmsg.CM_DELCLIENT_REQ:
            '''Del Client message.'''
            user = msg['user']
            LOG.info("del user=%s" % user)
            self._del_client(user)
        
        elif msg['mt'] == rhmsg.CM_GETCLIENT_REQ:
            user_str = msg['user_str']
            q = msg['q']
            
            rsp = {}
            rsp['mt'] = rhmsg.CM_GETCLIENT_RSP
            rsp['client_mq'] = self._get_client_mq(user_str)
            
            try:
                q.put(rsp, timeout = self.PUT_TIMEOUT_DEFAULT)
            except gevent.queue.Full:
                pass
            
        else:
            LOG.warning("CM.proc_msg.unknown message")
########NEW FILE########
__FILENAME__ = http_utils
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
# try to import C parser then fallback in pure python parser.
try:
    from http_parser.parser import HttpParser
    print "Using C HTTP parser"
except ImportError:
    print "Using pure Python HTTP parser"
    from http_parser.pyparser import HttpParser

def get_subdom(request, base_domain):
    """Get subdomain in the Host header."""
    pass

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

def get_http_req_header(request):
    '''Get HTTP Request headers.'''
    http_req = HTTPRequest(request)
    
    try:
        return http_req.headers
    except AttributeError:
        print "FATAL.ERR, headers not found. req = ", request
        return None

########NEW FILE########
__FILENAME__ = mysock
"""
My socket wrapper
Copyright(c) Iwan Budi Kusnanto 2012
"""
import socket

def connect(sock, addr):
    """Connect to server."""
    try:
        sock.connect(addr)
    except socket.error as (_, err_str):
        return -1, (socket.error, err_str)
    except socket.herror as (_, err_str):
        return -1, (socket.herror, err_str)
    except socket.gaierror as (_, err_str):
        return -1, (socket.gaierror, err_str)
    except socket.timeout:
        return -1, (socket.timeout, "")
    
    return 0, None

def _send(sock, payload):
    """Send payload to socket."""
    written = 0
    try:
        written = sock.send(payload)
    except socket.error as (_, err_str):
        return written, (socket.error, err_str)
    except socket.timeout:
        return written, (socket.timeout, "")
    
    return written, None

def send(sock, payload):
    """Send payload."""
    return _send(sock, payload)
    
def send_all(sock, data):
    """Send all payload."""
    if isinstance(data, unicode):
        data = data.encode()
    err = None
    data_sent = 0
    while data_sent < len(data):
        written, err = _send(sock, data)
        data_sent += written
        if err is not None:
            break
    
    return data_sent, err
        
def recv_str(sock, count):
    """Read count byte from socket."""
    try:
        the_str = sock.recv(count)
    except socket.error as (_, err_str):
        return None, (socket.error, err_str)
    except socket.timeout:
        return None, (socket.timeout, "")
    
    return the_str, None

def recv(sock, count):
    """Read count byte from socket."""
    try:
        recv_str = sock.recv(count)
    except socket.error as (_, err_str):
        return None, (socket.error, err_str)
    except socket.timeout:
        return None, (socket.timeout, "")
    
    ba = bytearray(recv_str)
    return ba, None

def recv_safe(sock, count):
    """Recv all data from socket."""
    ba, err = recv(sock, count)
    if err != None or (ba != None and len(ba) == 0):
        return None, err
    buf = ba
    while len(buf) < count:
        ba, err = recv(sock, count - len(buf))
        if err != None or (ba != None and len(ba) == 0):
            return None, err
        buf += ba
        
    return buf, err

def setkeepalives(sock):
    """Set socket to keepalive socket."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
########NEW FILE########
__FILENAME__ = packet
import sys
import hashlib

import mysock

"""
1. type
2. header len (fixed = 5)
3. 
"""
MIN_HEADER_LEN = 5

MAX_USERNAME_LEN = 30
PASS_HASH_LEN = 40

TYPE_AUTH_REQ = 1
TYPE_AUTH_RSP = 2
TYPE_DATA_REQ = 3
TYPE_DATA_RSP = 4
TYPE_PING_REQ = 5
TYPE_PING_RSP = 6
TYPE_CTRL = 7
'''
Auth REQ packet
header
- type (1)
- user len (1)
- pass len (1)

payload
- user (user len)
- pass (pass len)
'''

class AuthReq:
    def __init__(self, payload = None):
        self.payload = payload
    
    def cek_valid(self):
        if self.payload[0] != TYPE_AUTH_REQ:
            return False
        
        #pass len
        if self.payload[2] != PASS_HASH_LEN:
            return False

        #user len
        if self.payload[1] > MAX_USERNAME_LEN:
            return False
        
        #payload len
        if len(self.payload) != MIN_HEADER_LEN + self.payload[1] + self.payload[2]:
            return False
        return True
    
    def build(self, user, password):
        pass_hash = hashlib.sha1(password).hexdigest()
        self.payload = bytearray(MIN_HEADER_LEN) + bytearray(user) + bytearray(pass_hash)
        self.payload[0] = TYPE_AUTH_REQ
        self.payload[1] = len(user)
        self.payload[2] = len(pass_hash)
    
    def get_userpassword(self):
        user_len = self.payload[1]
        user = self.payload[MIN_HEADER_LEN : MIN_HEADER_LEN + user_len]
        
        pass_len = self.payload[2]
        password = self.payload[MIN_HEADER_LEN + user_len : MIN_HEADER_LEN + user_len + pass_len]
        return user, password
'''
AUTH RSP Packet
header
- type

payload
- val (AUTH_RSP_OK, AUTH_RSP_FAILED)
'''
AUTH_RSP_OK = 1
AUTH_RSP_BAD_USERPASS = 2

class AuthRsp:
    def __init__(self, payload = None):
        self.payload = payload
    
    def build(self, val):
        self.payload = bytearray(MIN_HEADER_LEN + 1)
        self.payload[0] = TYPE_AUTH_RSP
        self.payload[MIN_HEADER_LEN] = val
        
    def cek(self):
        '''Cek apakah ini packet auth rsp.'''
        return self.payload[0] == TYPE_AUTH_RSP and len(self.payload) == MIN_HEADER_LEN + 1
    
    def get_val(self):
        return self.payload[MIN_HEADER_LEN]
    
class DataReq:
    '''
    DATA REQ packet
    header
    - (0) type
    - (1) subtype
          undefined = 0
    - (2) ses id
    - (3,4) len
    
    payload
    - request
    '''
    def __init__(self, payload = None):
        self.type = TYPE_DATA_REQ
        self.payload = payload
    
    def build(self, data, ses_id):
        '''Build DATA REQ packet.'''
        self.payload = bytearray(MIN_HEADER_LEN)
        self.payload += data
        self.payload[0] = TYPE_DATA_REQ
        self.payload[2] = ses_id
        
        data_len = len(data)
        self.payload[3] = data_len >> 8
        self.payload[4] = data_len & 0xff
    
    def get_sesid(self):
        return self.payload[2]
    
    def cek_valid(self):
        return self.payload[0] == TYPE_DATA_REQ
    
    def get_data(self):
        return self.payload[MIN_HEADER_LEN:]
        
    def get_len(self):
        return (self.payload[3] << 8) | self.payload[4]

class DataRsp:
    '''
    DATA RSP packet
    header
    - (0) type
    - (1) subtype:
          undefined = 0
          EOF = 1
    - (2) ses id
    - (3,4) len
    payload
    - response
    '''
    DATA_RSP_TYPE_EOF = 1
    def __init__(self, payload = None):
        self.type = TYPE_DATA_RSP
        self.payload = payload
    
    def build(self, data, ses_id, sub_type = 0):
        self.payload = bytearray(MIN_HEADER_LEN)
        self.payload += data
        self.payload[0] = TYPE_DATA_RSP
        self.payload[1] = sub_type
        self.payload[2] = ses_id
        data_len = len(data)
        self.payload[3] = data_len >> 8
        self.payload[4] = data_len & 0xff
    
    def get_data(self):
        return self.payload[MIN_HEADER_LEN:]
    
    def get_sesid(self):
        return self.payload[2]
    
    def set_eof(self):
        self.payload[1] = DataRsp.DATA_RSP_TYPE_EOF
        
    def is_eof(self):
        return self.payload[1] == DataRsp.DATA_RSP_TYPE_EOF
    
    def get_len(self):
        return (self.payload[3] << 8) | self.payload[4]
        
    def cek_valid(self):
        return self.payload[0] == TYPE_DATA_RSP

class Ping:
    '''
    Ping Packet:
    header:
    - (0) type (REQ/RSP)
    - (1) 0
    - (2) 0
    - (3,4) len (0)
    
    payload/data
    No data
    '''
    def __init__(self):
        self.payload = bytearray(MIN_HEADER_LEN)
        #set len = 0
        self.payload[3] = 0
        self.payload[4] = 0
    
    def get_len(self):
        get_len_from_header(self.payload)

class PingReq(Ping):
    def __init__(self):
        Ping.__init__(self)
        self.payload[0] = TYPE_PING_REQ
    
    def cek_valid(self):
        return self.payload[0] == TYPE_PING_REQ

class PingRsp(Ping):
    def __init__(self):
        Ping.__init__(self)
        self.payload[0] = TYPE_PING_RSP
    
    def cek_valid(self):
        return self.payload[0] == TYPE_PING_RSP

class CtrlPkt():
    '''
    Header
    (0) type
    (1) subtype
    
    Data
    None
    '''
    #peer died
    T_PEER_DEAD = 1
    
    #Local webserver is down
    T_LOCAL_DOWN = 2
    
    def __init__(self, payload = None):
        self.payload = payload
    
    def get_type(self):
        return self.payload[1]
    
    def get_ses_id(self):
        return self.payload[2]
        
    def cek_valid(self):
        if self.payload != None:
            return (self.payload[0] == TYPE_CTRL)
            
        return True
    
    def build(self, ses_id, subtype):
        payload = bytearray(5)
        payload[0] = TYPE_CTRL
        payload[1] = subtype
        payload[2] = ses_id
        
        self.payload = payload
        
    ####### peer dead ##########
    def build_peer_dead(self, ses_id):
        self.build(ses_id, self.T_PEER_DEAD)
    
    def peer_dead_ses_id(self):
        return self.payload[2]
    
    ###### Local Down #####
    def build_local_down(self, ses_id):
        self.build(ses_id, self.T_LOCAL_DOWN)
    
    def is_local_down(self):
        return self.payload[1] == self.T_LOCAL_DOWN
        
class Packet:
    def __init__(self, type = None, payload = None):
        self.type = type
        self.payload = payload
    
    def get_type(self):
        return self.payload[0]

def print_header(payload):
    print "====== header ======="
    print "[0]", payload[0]
    print "[1]", payload[1]
    print "[2]", payload[2]
    print "[3]", payload[3]
    print "[4]", payload[4]

def get_len_from_header(header):
    '''Get packet len from given packet header.'''
    return (header[3] << 8) | header[4]

def get_all_data_pkt(sock):
    '''get complete Data packet.'''
    #read the header
    ba, err = mysock.recv_safe(sock, MIN_HEADER_LEN)
    
    if ba == None or err != None:
        '''something error happened.'''
        print "null BA"
        return None, None

    if len(ba) != MIN_HEADER_LEN:
        print "FATAL ERROR.len(ba) = ", len(ba)
        return None, None
    
    pkt_len = get_len_from_header(ba)
    #print "need to recv ", pkt_len, " bytes"
    pkt = ba
    
    if pkt_len > 0:
        buf, err = mysock.recv_safe(sock, pkt_len)
        if buf == None:
            print "NULL ba"
            return None, None
        #print "---> get ", len(buf), " bytes"
        pkt += buf
    
    return pkt, None

########NEW FILE########
__FILENAME__ = peerd
"""
Peer Daemon
Copyright 2012 Iwan Budi Kusnanto
"""
import select
import logging
import logging.handlers

import gevent
from gevent.server import StreamServer
import jsonrpclib

import mysock
import http_utils
import rhconf
import rhmsg
import authstat
import packet

BASE_DOMAIN = ""
CM = None
BUF_LEN = 1024

LOG_FILENAME = rhconf.LOG_FILE_PEERD
logging.basicConfig(level = rhconf.LOG_LEVEL_PEERD) 
LOG = logging.getLogger("peerd")
rotfile_handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME,
    maxBytes = rhconf.LOG_MAXBYTE_PEERD,
    backupCount = 10
)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
rotfile_handler.setFormatter(formatter)
LOG.addHandler(rotfile_handler)
LOG.setLevel(rhconf.LOG_LEVEL_PEERD)

if rhconf.LOG_STDERR_PEERD:
    stderr_handler = logging.StreamHandler()
    LOG.addHandler(stderr_handler)

class Peer:
    """Class that represents a Peer."""
    RSP_FORWARD_NUM = 5
    
    def __init__(self, sock, addr, client_name, client_mq = None):
        self.sock = sock
        self.addr = addr
        self.client_name = client_name
        self.ses_id = None
        self.ended = False
        self.rsp_list = []
        self.in_mq = gevent.queue.Queue(10)
        
        self.client_mq = client_mq
        
        #Transferred RSP packet, in bytes
        self.trf_rsp = 0
        
        #transferred Req packets, in bytes
        self.trf_req = 0
    
    def close(self):
        '''Close peer connection.'''
        self.sock.close()
        self._unreg()
        self.rsp_list = []
        return True
    
    def _unreg(self):
        '''unreg the peer from client.'''
        msg = {}
        msg['mt'] = rhmsg.CL_DELPEER_REQ
        msg['ses_id'] = self.ses_id
        self.client_mq.put(msg)
        
    def enq_rsp(self, payload):
        '''Enqueue response packet.'''
        self.rsp_list.insert(0, payload)
    
    def _do_forward_rsp_pkt(self):
        '''Forward response packet to peer.'''
        if len(self.rsp_list) == 0:
            return True, 0
        
        rsp = self.rsp_list.pop(0)
        
        if rsp.payload[0] == packet.TYPE_DATA_RSP:
            return self._do_forward_data_pkt(rsp)
        elif rsp.payload[0] == packet.TYPE_CTRL:
            return self._handle_ctrl_pkt(rsp)
        else:
            LOG.info("unknown rsp packet type for client = %s" % self.client_name)
            return False, 0
        
    def _do_forward_data_pkt(self, rsp):
        """Forward DataRsp packet."""
        data = rsp.get_data()
        
        written, err = mysock.send(self.sock, data)
        if err != None:
            LOG.warning("_do_forward_data_pkt:can't forward data to peer. end this peer")
            self.ended = True
            return False, -1
        
        if written != len(data):
            LOG.warning("peer.forward_rsp_pkt partial %s:%s" % self.addr)
            self.enq_rsp(data[written])
        
        if rsp.is_eof() == True:
            self.ended = True
        
        return True, written
    
    def _handle_ctrl_pkt(self, rsp):
        """Handle Ctrl packet from client."""
        if rsp.is_local_down():
            handle_local_down(self.client_name, self.sock)
            return False, 0
        else:
            LOG.warning("unknown ctrl pkt type=", rsp.payload[1])
            return False, 0
        
    def forward_rsp_pkt(self):
        '''Forward response packet to peer.'''
        for _ in xrange(0, self.RSP_FORWARD_NUM):
            is_ok, written = self._do_forward_rsp_pkt()
            if not is_ok:
                return False
            if written <= 0:
                break
            self.trf_rsp += written
        
        return True

def user_offline_str(user):
    '''User not found error message.'''
    html = "HTTP/1.1\n\
Server: roomahost/0.1\n\
Content-Type: text/html\n\
Content-Length: 173\n\
Connection: close\n\
\r\n\
"
    html += "<html><body>"
    html += "<center><big><b>" + user + " </b> is not online now</big></center>"
    html += "</body></html>"
    return html

def handle_client_offline(client_name, sock):
    '''User not found handler.'''
    LOG.info("Send 'client not online' message to peer. Client = %s " % client_name)
    str_err = user_offline_str(client_name)
    mysock.send_all(sock, str_err)

def local_down_str(client_name):
    '''User not found error message.'''
    html = "HTTP/1.1\n\
Server: roomahost/0.1\n\
Content-Type: text/html\n\
Content-Length: 173\n\
Connection: close\n\
\r\n\
"
    html += "<html><body>"
    html += "<center><big>Local web server of <b>" + client_name + " </b> is down now</big></center>"
    html += "</body></html>"
    return html

def handle_local_down(client_name, sock):
    LOG.info("Send 'local down' message to peer. Client = %s " % client_name)
    str_err = local_down_str(client_name)
    mysock.send_all(sock, str_err)
    
def get_client_name(req, base_domain = BASE_DOMAIN):
    '''Get client name dari HTTP Request header.'''
    header = http_utils.get_http_req_header(req)
    
    if header == None:
        return None
    try:
        host = header['Host']
        idx = host.find("." + base_domain)
        if idx < 0:
            return authstat.get_client_own_domain(host)
        else:
            return host[:idx]
    except AttributeError:
        return None

def get_client_mq(subdom):
    '''get client Queue.
    The queue will be used to send request packet.
    '''
    temp_q = gevent.queue.Queue(1)
    msg = {}
    msg['mt'] = rhmsg.CM_GETCLIENT_REQ
    msg['user_str'] = subdom
    msg['q'] = temp_q
    
    CM.in_mq.put(msg)
    
    rsp = temp_q.get()
    client_mq = rsp['client_mq']
    return client_mq
    
def register_peer(peer):
    '''Register peer to client.'''
    temp_q = gevent.queue.Queue(1)
    msg = {}
    msg['mt'] = rhmsg.CL_ADDPEER_REQ
    msg['in_mq'] = peer.in_mq
    msg['q'] = temp_q
    peer.client_mq.put(msg)
    
    rsp = temp_q.get()
    
    return rsp['ses_id']
    
def forward_reqpkt_to_client(client_mq, ses_id, ba_req):
    '''Forward request packet to client.'''
    req_pkt = rhmsg.HttpReq(ses_id, ba_req)
    msg = {}
    msg['mt'] = rhmsg.CL_ADD_REQPKT_REQ
    msg['req_pkt'] = req_pkt
    client_mq.put(msg)

def handle_peer(sock, addr):
    '''Peer connection handler.'''
    #LOG.debug("new_peer.addr = %s %s" % addr)
    
    #get request
    ba_req, err = mysock.recv(sock, BUF_LEN)
    if err != None or len(ba_req) == 0:
        return
    
    #get client name
    client_name = get_client_name(ba_req, BASE_DOMAIN)
    
    if client_name is None:
        LOG.warning("client name not found.aaddr = %s:%s" % addr)
        sock.close()
        return
    
    #check client status
    client_status = authstat.client_status(client_name) 
    if client_status != authstat.RH_STATUS_OK:
        LOG.info("Access denied. Client status for %s is %d." % (client_name, client_status))
        mysock.send_all(sock, authstat.client_status_msg(client_status, client_name))
        return
    
    #get pointer to client mq
    client_mq = get_client_mq(client_name)
    
    if client_mq == None:
        handle_client_offline(client_name, sock)
        return
    
    #register peer to client
    peer = Peer(sock, addr, client_name, client_mq)
    peer.ses_id = register_peer(peer)
    
    if peer.ses_id == None:
        LOG.error("can't add peer. MAX_CONN REACHED %s" % client_name)
        peer.close()
        return
    
    #forward request packet to client
    forward_reqpkt_to_client(client_mq, peer.ses_id, ba_req)
    peer.trf_req += len(ba_req)
    
    while True:
        #fetch response packet
        try:
            for _ in xrange(0, Peer.RSP_FORWARD_NUM):
                msg = peer.in_mq.get_nowait()
                rsp = msg['pkt']
                peer.rsp_list.append(rsp)
        except gevent.queue.Empty:
            pass
        
        #select() sock utk write jika ada RSP-pkt
        wlist = []
        if len(peer.rsp_list) > 0:
            wlist.append(sock)
            
        rsocks, wsocks, _ = select.select([sock], wlist , [], 0.1)
        
        #rsocks can be read
        if len(rsocks) > 0:
            ba_req, err = mysock.recv(sock, BUF_LEN)
            if len(ba_req) == 0:
                peer.ended = True
                break    
            elif len(ba_req) > 0:
                forward_reqpkt_to_client(client_mq, peer.ses_id, ba_req)
                peer.trf_req += len(ba_req)
        
        if len(wsocks) > 0:
            is_ok = peer.forward_rsp_pkt()
        
        if peer.ended == True:
            break
        
        gevent.sleep(0)
    
    peer.close()
    
    #send usage to server
    authstat.report_usage(client_name, peer.trf_req, peer.trf_rsp)
        
def peer_server(port):
    '''Peer daemon startup function.'''
    server = StreamServer(('0.0.0.0', port), handle_peer)
    print 'Starting peer daemon on port ', port
    print 'BASE_DOMAIN = ', BASE_DOMAIN
    server.serve_forever()
########NEW FILE########
__FILENAME__ = rhmsg
"""
roomahost message
Copyright(2012) - Iwan Budi Kusnanto
"""

#client daemon message type
CL_ADDPEER_REQ = 1 #add peer request
CL_ADDPEER_RSP = 2 #add peer response
CL_DELPEER_REQ = 3 #del peer request
CL_DELPEER_RSP = 4 #del peer response
CL_ADD_REQPKT_REQ = 5 #add request pkt request
CL_ADD_REQPKT_RSP = 6 #add request pkt response

#Client manager message type
CM_ADDCLIENT_REQ = 1
CM_ADDCLIENT_RSP = 2
CM_DELCLIENT_REQ = 3
CM_DELCLIENT_RSP = 4
CM_GETCLIENT_REQ = 5
CM_GETCLIENT_RSP = 6

#peer daemon message type
PD_ADD_RSP_PKT = 1

class HttpReq:
    '''HTTP request message that send from peerd to clientd.'''
    def __init__(self, ses_id, payload):
        self.ses_id = ses_id
        self.payload = payload
########NEW FILE########
__FILENAME__ = server
"""
Roomahost main server
Copyright : Iwan Budi Kusnanto 2012
"""
import sys

import gevent.pool
from gevent import monkey; monkey.patch_all()

import client_mgr
import clientd
import peerd

if __name__ == '__main__':
    BASE_DOMAIN = sys.argv[1]
    group = gevent.pool.Group()

    CM = client_mgr.ClientMgr()    
    CM.start()
    
    peerd.CM = CM
    peerd.BASE_DOMAIN = BASE_DOMAIN
    
    clientd.CM = CM
    
    cs = group.spawn(clientd.client_server, 3939)
    ps = group.spawn(peerd.peer_server, 4000)
    #gevent.joinall([cs, ps])
    group.join()

########NEW FILE########
__FILENAME__ = simple_rpcd
import hashlib

from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

import authstat

#dictionary of user-password
userpass_dict = {
    "iwanbk":"iwanbk",
    "ibk":"ibk",
    "paijo":"paijo",
}
userdomain_dict = {
    "iwanbk.lan":"iwanbk",
}

#authentication
def rh_auth(username, password):
    try:
        passwd = userpass_dict[username]
    except KeyError:
        print "user not found : ", username
        return False
    
    hashed_pass = hashlib.sha1(passwd).hexdigest()
    if hashed_pass == password:
        return True
    else:
        print "bad pasword = ", password
        return False

#add data transfer usage
def usage_add(username, trf_req, trf_rsp):
    print "---usage add"
    print "username = ", username
    print "trf_req = ", trf_req
    print "trf_rsp = ", trf_rsp
    return True

#get client status
def status(username):
    return authstat.RH_STATUS_OK

#client own domain
def rh_domain_client(domain):
    print "domain = ", domain
    try:
        client_name = userdomain_dict[domain]
        return client_name
    except KeyError:
        return None

if __name__ == '__main__':
    server = SimpleJSONRPCServer(('0.0.0.0',6565 ))
    server.register_function(rh_auth)
    server.register_function(usage_add)
    server.register_function(status)
    server.register_function(rh_domain_client)
    server.serve_forever()
########NEW FILE########
