__FILENAME__ = config
#! /usr/bin/env python
# -*- coding: utf-8 -*-
import socket

default_port = 8001 # default port for adding a new server
listen_port = 8001 # port for the server to listen on
my_address = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
              if not ip.startswith("127.")][0]
dns_module_listen_port = 8002
default_ttl = 60   # in seconds
default_record_lifetime = 3600 * 24 * 30 # one month, duh

########NEW FILE########
__FILENAME__ = database
#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from config import *
import time
import sqlite3

class Domain(object):
    def __init__(self, domain, ip, key, ttl = default_ttl,
                 timestamp = time.time() + default_record_lifetime):
        self.domain = str(domain)
        self.ip = str(ip)
        self.key = str(key)
        self.ttl = float(ttl)
        self.timestamp = timestamp

class Database(object):
    def __init__(self):
        self._domains = {}
        self._nodes = {}

        c = sqlite3.connect('./db')

        c.execute("create table if not exists nodes (ip text, port text)")
        c.execute("create table if not exists domains "
                  "(domain text, ip text, key text, ttl text, timestamp text)")
        c.commit()
        for row in c.execute("select * from nodes"):
            self._nodes[row[0]] = int(row[1])      
        for row in c.execute("select * from domains"):
            self._domains[row[0]] = Domain(row[0], row[1], row[2], row[3], row[4])   
        c.close()

    def print_nodes(self):
        c = sqlite3.connect('./db')
        for row in c.execute("select * from nodes"):
            print("%s:%s" % (row[0], row[1])) 
        c.close()

    def print_domains(self):
        c = sqlite3.connect('./db')
        for row in c.execute("select * from domains"):
            print("%s: %s, valid till: %s" % (row[0], row[1], row[3])) 
        c.close()

    def add_node(self, host, port):
        if host not in self._nodes:
            self._nodes[host] = int(port)

            c = sqlite3.connect('./db')
            c.execute("insert into nodes values (?, ?)", (host, port))
            c.commit()
            c.close()

    def get_nodes(self):
        return self._nodes

    def have_node(self, ip):
        return ip in self._nodes

    def get_port(self, host):
        try:
            port = self._nodes[host]
        except KeyError:
            port = default_port
        return int(port)

    def add_domain(self, domain, ip, key, ttl = 120, timestamp = time.time() ):
        if domain not in self._domains:
            self._domains[domain] = Domain(domain, ip, key, ttl, timestamp)

            c = sqlite3.connect('./db')
            c.execute("insert into domains values (?, ?, ?, ?, ?)", (domain,
                                                                     ip,
                                                                     key,
                                                                     ttl,
                                                                     timestamp))
            c.commit()
            c.close()

    def get_domains(self):
        return self._domains

########NEW FILE########
__FILENAME__ = dns-server
"""
@original author: Jochen Ritzel
http://stackoverflow.com/questions/4399512/python-dns-server-with-custom-backend/4401671#4401671

I extended this to include zmq communication to support p2p-dns
"""
from twisted.names import dns, server, client, cache
from twisted.application import service, internet
from twisted.python import log
import zmq
import time
from twisted.internet import defer

p2p_dns_server_ip = "localhost"
p2p_dns_server_port = 8002

class CacheEntry(object):
    def __init__(self, ip, ttl):
        self.ip = ip
        self.ttl = int(ttl)
        self.valid_till = time.time() + int(ttl)
    def is_valid(self):
        return time.time() < self.valid_till
    def get_ip(self):
        return self.ip
    def get_ttl(self):
        return self.ttl

class MapResolver(client.Resolver):
    """
    Resolves names by looking in a mapping. 
    If `name in mapping` then mapping[name] should return a IP
    else the next server in servers will be asked for name    
    """
    def __init__(self, servers):
        self.cache = { }
        client.Resolver.__init__(self, servers=servers)
        self.ttl = 10
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s:%d" % (p2p_dns_server_ip,
                                             p2p_dns_server_port) )
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def lookupAddress(self, name, timeout = None):
        # find out if this is a .kad. request
        if name in self.cache and self.cache[name].is_valid():
            ip = self.cache[name].get_ip() # get the result
            
            if ip == "0.0.0.0":
                # doesn't exist
                return self._lookup(name, dns.IN, dns.A, timeout)
            
            return defer.succeed([
                    (dns.RRHeader(name,
                                  dns.A,
                                  dns.IN,
                                  self.ttl,
                                  dns.Record_A(ip, self.ttl)),),
                    (),()
                    ])
        else:
            try:
                self.socket.send(name)
                # our p2p server should answer within 5 ms
                socks = dict(self.poller.poll(timeout=5))

                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    # format is "IP TTL"
                    msg = self.socket.recv().split(' ')
                    self.cache[name] = CacheEntry(msg[0], msg[1])
                    if msg[0] == "0.0.0.0":
                        # entry doesn't exist
                        return self._lookup(name, dns.IN, dns.A, timeout)
                    return self.lookupAddress(name)
            except zmq._zmq.ZMQError:
                log.msg("please start p2p-dns server")
            return self._lookup(name, dns.IN, dns.A, timeout)


## this sets up the application


application = service.Application('dnsserver', 1, 1)

# set up a resolver that uses the mapping or a secondary nameserver
p2presolver = MapResolver(servers=[('8.8.8.8', 53)])


# create the protocols
f = server.DNSServerFactory(caches=[cache.CacheResolver()],
                            clients=[p2presolver])
p = dns.DNSDatagramProtocol(f)
f.noisy = p.noisy = False


# register as tcp and udp
ret = service.MultiService()
PORT=53

for (klass, arg) in [(internet.TCPServer, f), (internet.UDPServer, p)]:
    s = klass(PORT, arg)
    s.setServiceParent(ret)


# run all of the above as a twistd application
ret.setServiceParent(service.IServiceCollection(application))


# run it through twistd!
if __name__ == '__main__':
    import sys
    print "Usage: twistd -y %s" % sys.argv[0]

########NEW FILE########
__FILENAME__ = dns_module
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from database import *
from config import *
from stoppable_thread import *
import threading
import zmq

class DNSModule(StoppableThread):
    def __init__(self, db, port = dns_module_listen_port):
        StoppableThread.__init__(self)
        self.database = db
        self.port = port

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:%d" % self.port)
        
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while not self.stopped():
            # timeout so we can free the socket and quit the program
            # if necessary; in ms
            socks = dict(poller.poll(timeout=100))
            
            if socket in socks and socks[socket] == zmq.POLLIN:
                print("got dns question")
                msg = socket.recv()
                if msg in self.database.domains:
                    domain = self.database.domains[msg]
                    socket.send("%s %d" % (domain.ip, domain.ttl))
                else:
                    socket.send("0.0.0.0 %d" % default_ttl)
                    # signal that domain doesn't exist

########NEW FILE########
__FILENAME__ = p2p-dns
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import readline
import sys
from optparse import OptionParser
import threading
import os
import re
from config import *
from server import *
from database import *
from dns_module import *

class App(object):
    def __init__(self):
        self.parser = OptionParser(version="%prog 0.1")

    def parse_commandline(self):

        self.parser.add_option("-d",
                          "--daemon",
                          action="store_true",
                          dest="daemon_mode",
                          default=False,
                          help="Starts this server in daemon mode" )

        (options, args) = self.parser.parse_args()

        if options.daemon_mode:
            print("in daemon mode")
            os.spawnl(os.P_NOWAIT, "touch", "touch", "./daemon")
            return True
        return False

    def print_help(self):
        commands = {
            "help":     "print this help",
            "daemon":   "detaches the server and exits this process",
            "connect":  "connect to another node",
            "nodes":    "print all known nodes",
            "domains":  "print all known domains",
            "register": "register a domain with all known nodes",
            "quit":     "exit this process"
            }
        self.parser.print_help()
        print("\n\tCLI commands:")
        for (command, explanaiton) in sorted( commands.items() ):
            print( "%-10s %s" % (command, explanaiton) )

    def start_daemon(self):
        proc_id = os.spawnl(os.P_NOWAIT,
                            sys.executable + " " + sys.argv[0],
                            "-d")
        print("process id: %s" % proc_id)
        self.quit()

    def start_server(self):
        self.db = Database()
        self.srv = Server(self.db)
        self.dns = DNSModule(self.db)

        
        self.dns.start()
        self.srv.start()

    def stop(self):
        self.dns.stop()
        self.srv.stop()
        
        self.srv.join()
        self.dns.join()
        
        sys.exit()

    def run(self):
        daemon_mode = self.parse_commandline()
        self.start_server()
        if not daemon_mode:
            print( """Welcome to this p2p-dns client.
    To run in daemon mode, use '-d' to start or type 'daemon'.
    To find out what other commands exist, type 'help'""" )

            while True:
                try:
                    io = raw_input("~> ")
                    if io == "help":
                        self.print_help()
                    elif io == "daemon":
                        self.start_daemon()
                    elif io == "connect":
                        server = raw_input("server:")
                        port = raw_input("port[%s]:" % default_port)

                        try:
                            port = int(port)
                        except:
                            port = default_port
                        
                        self.srv.add_node(server, port)
                    elif io == "nodes":
                        self.db.print_nodes()
                    elif io == "domains":
                        self.db.print_domains()
                    elif io == "register":
                        domain = raw_input("domain:")
                        ip = raw_input("IP:")
                        ttl = int(raw_input("TTL:"))
                        key = "" # not yet implemented, read key from file
                        self.srv.register_domain(domain, ip, key, ttl)
                    elif io == "quit":
                        self.stop()
                    else:
                        print("Didn't recognize command. "
                              "Please retry or type 'help'")
                except EOFError:
                    self.stop()
            
if __name__ == "__main__":
    app = App()
    app.run()

########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import re
from config import *
from database import *
from stoppable_thread import *
import socket, ssl

class MessageSender(StoppableThread):
    def __init__(self, db):
        StoppableThread.__init__(self)
        self.database = db
        self.msg_to_send = []
        self.cv = threading.Condition()
        
    def send_message(self, msg, host, port = None):
        self.cv.acquire()
        self.msg_to_send.append( (msg, host, port) )
        self.cv.notify()
        self.cv.release()

    def run(self):

        while not self.stopped():

            self.cv.acquire()
            while len(self.msg_to_send) < 1:
                self.cv.wait(0.05) # time out after 100 ms
                if self.stopped():
                    return
                
            msg, host, port = self.msg_to_send.pop()
            
            if port == None:
                port = self.database.get_port(host)
                
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl_sock = ssl.wrap_socket(s, cert_reqs=ssl.CERT_NONE)
            try:
                ssl_sock.connect((host, port))
            except socket.error:
                print("host %s doesn't accept connection" % host)
                return
            msg = "P2P-DNS 0.1\n" + msg

            # all messages are null-terminated so we know when we have
            # reached the end of it
            # the null will be stripped by the receiver
            if msg[-1] == '\0':
                ssl_sock.write(msg)
            else:
                ssl_sock.write(msg + '\0')
            ssl_sock.close()

            self.cv.release()

        
class Server(StoppableThread):
    def __init__(self, db):
        StoppableThread.__init__(self)
        self.port = default_port
        self.database = db
        self.sender = MessageSender(db)
        self.sender.start()

    def isP2PMessage(self, msg):
        return "P2P-DNS" in msg

    def handle_data(self, socket, address):
        msg = ""
        while True:
            msg += str( socket.read() )
            if msg[-1] == "\0":
                socket.close()
                break
        return self.handle_message(msg[:-1], socket, address)

    def handle_message(self, msg, socket, address):
        if self.isP2PMessage(msg):
            if "REQUEST" in msg:
                print "requesting", 
                if "CONNECTION" in msg:
                    print("a connection!")
                    self.sender.send_message("ACCEPT CONNECTION\nPORT %d"
                                             % listen_port,
                                             address)
                    port = int( re.findall(r'PORT (\d+)', msg)[0] )

                    self.database.add_node(address, port)                
                    print("have new node: %s:%s" % (address, port))
                    self.sender.send_message("REQUEST NODES", address)
                    self.sender.send_message("REQUEST DOMAINS", address)
                elif "NODES" in msg:
                    print("all the nodes I know!")
                    msg = "DATA NODES"
                    for (ip, port) in self.database.get_nodes().items():
                        msg += "\n%s %s" % (ip, port)
                    self.sender.send_message(msg, address)
                elif "DOMAINS" in msg:
                    print("all the domains I know!")
                    msg = "DATA DOMAINS"
                    for (domain, record) in self.database.get_domains().items():
                        # "domain ip ttl timestamp key"
                        msg += "\n%s %s %d %s %s" % (domain,
                                                record.ip,
                                                record.ttl,
                                                record.timestamp,
                                                record.key)
                    self.sender.send_message(msg, address)
            elif "ACCEPT" in msg:
                if "CONNECTION" in msg:
                    print("node accepted the connection")
                    port = int( re.findall(r'PORT (\d+)', msg)[0] )
                    self.database.add_node(address, port)
                    self.sender.send_message("REQUEST NODES", address)
                    self.sender.send_message("REQUEST DOMAINS", address)
            elif "DATA" in msg:
                print "got",
                if "NODES" in msg:
                    print("nodes")
                    for l in msg.split('\n')[2:]:
                        n = l.split(' ')

                        if (n[0] != address and
                            n[0] != my_address and
                            not self.database.have_node(n[0]) ):
                            self.sender.send_message("REQUEST CONNECTION\nPORT %d"
                                              % listen_port,
                                              n[0],
                                              int(n[1]))
                elif "DOMAINS" in msg:
                    print("domains")
                    for l in msg.split('\n')[2:]:
                        n = l.split(' ')
                        self.database.add_domain(n[0], n[1], n[2], n[3], n[4]) 
        return True
                
    def add_node(self, host, port):
        self.sender.send_message("REQUEST CONNECTION\nPORT %s" % listen_port,
                          host,
                          port)
        # that's the port this server is listening on

    def register_domain(self, domain, ip, key, ttl = default_ttl):
        # put in db
        self.database.add_domain(domain, ip, key, ttl)

        # announce to all known nodes
        for (node_ip, node_port) in self.database.get_nodes().items():
            # "domain ip ttl timestamp key"
            self.sender.send_message("DATA DOMAINS\n%s %s %d %s %s" % (
                    domain,
                    ip,
                    ttl,
                    time.time() + default_record_lifetime,
                    key),
                                     node_ip,
                                     node_port)

    def run(self):
        s = socket.socket()
        s.bind(('', listen_port))
        s.listen(5)
        s.settimeout(0.1)
        
        while not self.stopped():
            try:
                sck, addr = s.accept()
                ssl_socket = ssl.wrap_socket(sck,
                                             server_side=True,
                                             certfile="server.pem",
                                             keyfile="server.pem",
                                             ssl_version=ssl.PROTOCOL_SSLv3)
                self.handle_data(ssl_socket, addr[0])
            except socket.timeout:
                pass
        self.sender.stop()
        self.sender.join()
        
        

        

########NEW FILE########
__FILENAME__ = stoppable_thread
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import threading

class StoppableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._stopped = threading.Event()
    
    def stop(self):
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

########NEW FILE########
