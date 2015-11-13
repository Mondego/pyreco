__FILENAME__ = asyncclientproxy
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: ConCoord Client Proxy
@copyright: See LICENSE
'''
import socket, os, sys, time, random, threading, select
from threading import Thread, Condition, RLock, Lock
import pickle
from concoord.pack import *
from concoord.enums import *
from concoord.utils import *
from concoord.exception import *
from concoord.connection import ConnectionPool, Connection
from concoord.message import *
from concoord.pvalue import PValueSet
try:
    import dns
    import dns.resolver
    import dns.exception
except:
    print("Install dnspython: http://www.dnspython.org/")

class ReqDesc:
    def __init__(self, clientproxy, args, token):
        # acquire a unique command number
        self.commandnumber = clientproxy.commandnumber
        clientproxy.commandnumber += 1
        self.cm = create_message(MSG_CLIENTREQUEST, clientproxy.me,
                                 {FLD_PROPOSAL: Proposal(clientproxy.me, self.commandnumber, args),
                                  FLD_TOKEN: token,
                                  FLD_CLIENTBATCH: False,
                                  FLD_SENDCOUNT: 0})
        self.reply = None
        self.replyarrived = False
        self.replyarrivedcond = Condition()
        self.sendcount = 0

    def __str__(self):
        return "Request Descriptor for cmd %d\nMessage %s\nReply %s" % (self.commandnumber, str(self.cm), self.reply)

class ClientProxy():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.debug = debug
        self.timeout = timeout
        self.domainname = None
        self.token = token
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.writelock = Lock()

        self.bootstraplist = self.discoverbootstrap(bootstrap)
        if len(self.bootstraplist) == 0:
            raise ConnectionError("No bootstrap found")
        if not self.connecttobootstrap():
            raise ConnectionError("Cannot connect to any bootstrap")
        myaddr = findOwnIP()
        myport = self.socket.getsockname()[1]
        self.me = Peer(myaddr,myport,NODE_CLIENT)
        self.commandnumber = random.randint(1, sys.maxint)

        # synchronization
        self.lock = Lock()
        self.pendingops = {}
        self.writelock = Lock()
        self.needreconfig = False
        self.outstanding = []

        # spawn thread, invoke recv_loop
        recv_thread = Thread(target=self.recv_loop, name='ReceiveThread')
        recv_thread.start()

    def _getipportpairs(self, bootaddr, bootport):
        for node in socket.getaddrinfo(bootaddr, bootport, socket.AF_INET, socket.SOCK_STREAM):
            yield (node[4][0],bootport)

    def getbootstrapfromdomain(self, domainname):
        tmpbootstraplist = []
        try:
            answers = dns.resolver.query('_concoord._tcp.'+domainname, 'SRV')
            for rdata in answers:
                for peer in self._getipportpairs(str(rdata.target), rdata.port):
                    if peer not in tmpbootstraplist:
                        tmpbootstraplist.append(peer)
        except (dns.resolver.NXDOMAIN, dns.exception.Timeout):
            if self.debug:
                print "Cannot resolve name"
        return tmpbootstraplist

    def discoverbootstrap(self, givenbootstrap):
        tmpbootstraplist = []
        try:
            for bootstrap in givenbootstrap.split(","):
                bootstrap = bootstrap.strip()
                # The bootstrap list is read only during initialization
                if bootstrap.find(":") >= 0:
                    bootaddr,bootport = bootstrap.split(":")
                    for peer in self._getipportpairs(bootaddr, int(bootport)):
                        if peer not in tmpbootstraplist:
                            tmpbootstraplist.append(peer)
                else:
                    self.domainname = bootstrap
                    tmpbootstraplist = self.getbootstrapfromdomain(self.domainname)
        except ValueError:
            if self.debug:
                print "bootstrap usage: ipaddr1:port1,ipaddr2:port2 or domainname"
            self._graceexit()
        return tmpbootstraplist

    def connecttobootstrap(self):
        connected = False
        for boottuple in self.bootstraplist:
            try:
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                self.socket.connect(boottuple)
                self.conn = Connection(self.socket)
                self.conn.settimeout(CLIENTRESENDTIMEOUT)
                self.bootstrap = boottuple
                connected = True
                if self.debug:
                    print "Connected to new bootstrap: ", boottuple
                break
            except socket.error, e:
                if self.debug:
                    print e
                continue
        return connected

    def trynewbootstrap(self):
        if self.domainname:
            self.bootstraplist = self.getbootstrapfromdomain(self.domainname)
        else:
            oldbootstrap = self.bootstraplist.pop(0)
            self.bootstraplist.append(oldbootstrap)
        return self.connecttobootstrap()

    def invoke_command_async(self, *args):
        # create a request descriptor
        reqdesc = ReqDesc(self, args, self.token)
        # send the clientrequest
        with self.writelock:
            success = self.conn.send(reqdesc.cm)
            self.pendingops[reqdesc.commandnumber] = reqdesc
            # if the message is not sent, we should reconfigure
            # and send it without making the client wait
            if not success:
                self.outstanding.append(reqdesc)
            self.needreconfig = not success
        return reqdesc

    def wait_until_command_done(self, reqdesc):
        with reqdesc.replyarrivedcond:
            while not reqdesc.replyarrived:
                reqdesc.replyarrivedcond.wait()
        if reqdesc.reply.replycode == CR_OK:
            return reqdesc.reply.reply
        elif reqdesc.reply.replycode == CR_EXCEPTION:
            raise Exception(reqdesc.reply.reply)
        else:
            return "Unexpected Client Reply Code: %d" % reqdesc.reply.replycode

    def recv_loop(self, *args):
        while True:
            try:
                for reply in self.conn.received_bytes():
                    if reply and reply.type == MSG_CLIENTREPLY:
                        # received a reply
                        reqdesc = self.pendingops[reply.inresponseto]
                        # Async Clientproxy doesn't support BLOCK and UNBLOCK
                        if reply.replycode == CR_OK or reply.replycode == CR_EXCEPTION:
                            # the request is done
                            reqdesc.reply = reply
                            with reqdesc.replyarrivedcond:
                                reqdesc.replyarrived = True
                                reqdesc.replyarrivedcond.notify()
                            del self.pendingops[reply.inresponseto]
                        elif reply.replycode == CR_INPROGRESS:
                            # the request is not done yet
                            pass
                        elif reply.replycode == CR_REJECTED or reply.replycode == CR_LEADERNOTREADY:
                            # the request should be resent after reconfiguration
                            with self.lock:
                                self.outstanding.append(reqdesc)
                                self.needreconfig = True
                        else:
                            print "Unknown Client Reply Code"
            except ConnectionError:
                self.needreconfig = True
            except KeyboardInterrupt:
                self._graceexit()

            with self.lock:
                if self.needreconfig:
                    if not self.trynewbootstrap():
                        raise ConnectionError("Cannot connect to any bootstrap")

            with self.writelock:
                for reqdesc in self.outstanding:
                    success = self.conn.send(reqdesc.cm)
                    if success:
                        self.outstanding.remove(reqdesc)

    def _graceexit(self):
        os._exit(0)

########NEW FILE########
__FILENAME__ = batchclientproxy
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: ConCoord Client Proxy
@copyright: See LICENSE
'''
import os, sys, random, socket, time
from threading import Thread, Condition, Lock
from concoord.pack import *
from concoord.enums import *
from concoord.utils import *
from concoord.exception import *
from concoord.connection import Connection
from concoord.message import *
try:
    import dns
    import dns.resolver
    import dns.exception
except:
    print("Install dnspython: http://www.dnspython.org/")

class ReqDesc:
    def __init__(self, clientproxy, token):
        self.clientproxy = clientproxy
        self.token = token
        # acquire a unique command number
        self.commandnumber = clientproxy.commandnumber
        clientproxy.commandnumber += 1
        self.batch = []
        self.cm = create_message(MSG_CLIENTREQUEST, self.clientproxy.me,
                                 {FLD_PROPOSAL: ProposalClientBatch(self.clientproxy.me,
                                                                    self.commandnumber,
                                                                    self.batch),
                                  FLD_TOKEN: self.token,
                                  FLD_CLIENTBATCH: True,
                                  FLD_SENDCOUNT: 0})
        self.reply = None
        self.replyarrived = False
        self.replyarrivedcond = Condition()
        self.sendcount = 0

    def rewrite_message(self):
        self.cm = create_message(MSG_CLIENTREQUEST, self.clientproxy.me,
                                 {FLD_PROPOSAL: ProposalClientBatch(self.clientproxy.me,
                                                                    self.commandnumber,
                                                                    self.batch),
                                  FLD_TOKEN: self.token,
                                  FLD_CLIENTBATCH: True,
                                  FLD_SENDCOUNT: 0})

    def finalize(self):
        self.clientproxy.finalize_batch()

    def __str__(self):
        return "Request Descriptor for cmd %d\nMessage %s\nReply %s" % (self.commandnumber, str(self.cm), self.reply)

class ClientProxy():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.debug = debug
        self.timeout = timeout
        self.domainname = None
        self.token = token
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.writelock = Lock()

        self.bootstraplist = self.discoverbootstrap(bootstrap)
        if len(self.bootstraplist) == 0:
            raise ConnectionError("No bootstrap found")
        if not self.connecttobootstrap():
            raise ConnectionError("Cannot connect to any bootstrap")
        myaddr = findOwnIP()
        myport = self.socket.getsockname()[1]
        self.me = Peer(myaddr,myport,NODE_CLIENT)
        self.commandnumber = random.randint(1, sys.maxint)

        # synchronization
        self.lock = Lock()
        self.pendingops = {}
        self.lastsendtime = time.time()
        self.reqdesc = ReqDesc(self, self.token)
        self.writelock = Lock()
        self.needreconfig = False
        self.outstanding = []

        # spawn thread, invoke recv_loop
        recv_thread = Thread(target=self.recv_loop, name='ReceiveThread')
        recv_thread.start()

    def _getipportpairs(self, bootaddr, bootport):
        for node in socket.getaddrinfo(bootaddr, bootport, socket.AF_INET, socket.SOCK_STREAM):
            yield (node[4][0],bootport)

    def getbootstrapfromdomain(self, domainname):
        tmpbootstraplist = []
        try:
            answers = dns.resolver.query('_concoord._tcp.'+domainname, 'SRV')
            for rdata in answers:
                for peer in self._getipportpairs(str(rdata.target), rdata.port):
                    if peer not in tmpbootstraplist:
                        tmpbootstraplist.append(peer)
        except (dns.resolver.NXDOMAIN, dns.exception.Timeout):
            if self.debug:
                print "Cannot resolve name"
        return tmpbootstraplist

    def discoverbootstrap(self, givenbootstrap):
        tmpbootstraplist = []
        try:
            for bootstrap in givenbootstrap.split(","):
                bootstrap = bootstrap.strip()
                # The bootstrap list is read only during initialization
                if bootstrap.find(":") >= 0:
                    bootaddr,bootport = bootstrap.split(":")
                    for peer in self._getipportpairs(bootaddr, int(bootport)):
                        if peer not in tmpbootstraplist:
                            tmpbootstraplist.append(peer)
                else:
                    self.domainname = bootstrap
                    tmpbootstraplist = self.getbootstrapfromdomain(self.domainname)
        except ValueError:
            if self.debug:
                print "bootstrap usage: ipaddr1:port1,ipaddr2:port2 or domainname"
            self._graceexit()
        return tmpbootstraplist

    def connecttobootstrap(self):
        connected = False
        for boottuple in self.bootstraplist:
            try:
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                self.socket.connect(boottuple)
                self.conn = Connection(self.socket)
                self.conn.settimeout(CLIENTRESENDTIMEOUT)
                self.bootstrap = boottuple
                connected = True
                if self.debug:
                    print "Connected to new bootstrap: ", boottuple
                break
            except socket.error, e:
                if self.debug:
                    print "Socket Error: ", e
                continue
        return connected

    def trynewbootstrap(self):
        if self.domainname:
            self.bootstraplist = self.getbootstrapfromdomain(self.domainname)
        else:
            oldbootstrap = self.bootstraplist.pop(0)
            self.bootstraplist.append(oldbootstrap)
        return self.connecttobootstrap()

    def invoke_command_async(self, *args):
        self.reqdesc.batch.append(args)
        # batch either 100000 requests or any number of requests that are collected
        # in less than 0.1 seconds.
        if len(self.reqdesc.batch) == 100000 or \
                time.time() - self.lastsendtime > 0.1 and len(self.reqdesc.batch) > 0:
            self.reqdesc.rewrite_message()
            reqdesc = self.reqdesc
            # send the clientrequest
            with self.writelock:
                success = self.conn.send(reqdesc.cm)
                self.lastsendtime = time.time()
                self.pendingops[reqdesc.commandnumber] = reqdesc
                # if the message is not sent, we should reconfigure
                # and send it without making the client wait
                if not success:
                    self.outstanding.append(reqdesc)
                self.needreconfig = not success
            self.reqdesc = ReqDesc(self, self.token)
            return reqdesc
        return self.reqdesc

    def finalize_batch(self):
        self.reqdesc.rewrite_message()
        reqdesc = self.reqdesc
        # send the clientrequest
        with self.writelock:
            success = self.conn.send(reqdesc.cm)
            self.lastsendtime = time.time()
            self.pendingops[reqdesc.commandnumber] = reqdesc
            # if the message is not sent, we should reconfigure
            # and send it without making the client wait
            if not success:
                self.outstanding.append(reqdesc)
            self.needreconfig = not success
        self.reqdesc = ReqDesc(self, self.token)

    def wait_until_command_done(self, reqdesc):
        with reqdesc.replyarrivedcond:
            while not reqdesc.replyarrived:
                reqdesc.replyarrivedcond.wait()
        if reqdesc.reply.replycode == CR_OK or reqdesc.reply.replycode == CR_BATCH:
            return reqdesc.reply.reply
        elif reqdesc.reply.replycode == CR_EXCEPTION:
            raise Exception(reqdesc.reply.reply)
        else:
            return "Unexpected Client Reply Code: %d" % reqdesc.reply.replycode

    def recv_loop(self, *args):
        while True:
            try:
                for reply in self.conn.received_bytes():
                    if reply and reply.type == MSG_CLIENTREPLY:
                        # received a reply
                        reqdesc = self.pendingops[reply.inresponseto]
                        # Async Clientproxy doesn't support BLOCK and UNBLOCK
                        if reply.replycode == CR_OK or reply.replycode == CR_EXCEPTION or reply.replycode == CR_BATCH:
                            # the request is done
                            reqdesc.reply = reply
                            with reqdesc.replyarrivedcond:
                                reqdesc.replyarrived = True
                                reqdesc.replyarrivedcond.notify()
                            del self.pendingops[reply.inresponseto]
                        elif reply.replycode == CR_INPROGRESS:
                            # the request is not done yet
                            pass
                        elif reply.replycode == CR_REJECTED or reply.replycode == CR_LEADERNOTREADY:
                            # the request should be resent after reconfiguration
                            with self.lock:
                                self.outstanding.append(reqdesc)
                                self.needreconfig = True
                        else:
                            print "Unknown Client Reply Code"
            except ConnectionError:
                self.needreconfig = True
            except KeyboardInterrupt:
                self._graceexit()

            with self.lock:
                if self.needreconfig:
                    if not self.trynewbootstrap():
                        raise ConnectionError("Cannot connect to any bootstrap")

            with self.writelock:
                for reqdesc in self.outstanding:
                    success = self.conn.send(reqdesc.cm)
                    if success:
                        self.outstanding.remove(reqdesc)

    def _graceexit(self):
        os._exit(0)

########NEW FILE########
__FILENAME__ = blockingclientproxy
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: ConCoord Client Proxy
@copyright: See LICENSE
'''
import os, random, select, socket, sys, threading, time
import cPickle as pickle
from threading import Thread, Condition, Lock
from concoord.pack import *
from concoord.enums import *
from concoord.utils import *
from concoord.exception import *
from concoord.connection import ConnectionPool, Connection
from concoord.message import *
from concoord.pvalue import PValueSet
try:
    import dns
    import dns.resolver
    import dns.exception
except:
    print("Install dnspython: http://www.dnspython.org/")

class ReqDesc:
    def __init__(self, clientproxy, args, token):
        with clientproxy.lock:
            # acquire a unique command number
            self.commandnumber = clientproxy.commandnumber
            clientproxy.commandnumber += 1
        self.cm = create_message(MSG_CLIENTREQUEST, clientproxy.me,
                                 {FLD_PROPOSAL: Proposal(clientproxy.me, self.commandnumber, args),
                                  FLD_TOKEN: token,
                                  FLD_CLIENTBATCH: False,
                                  FLD_SENDCOUNT: 0})
        self.starttime = time.time()
        self.replyarrived = Condition(clientproxy.lock)
        self.lastreplycr = -1
        self.replyvalid = False
        self.reply = None
        self.sendcount = 0

    def __str__(self):
        return "Request Descriptor for cmd %d\nMessage %s\nReply %s" % (self.commandnumber, str(self.cm), self.reply)

class ClientProxy():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.debug = debug
        self.timeout = timeout
        self.domainname = None
        self.token = token
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.setblocking(1)
        self.writelock = Lock()

        self.bootstraplist = self.discoverbootstrap(bootstrap)
        if len(self.bootstraplist) == 0:
            raise ConnectionError("No bootstrap found")
        if not self.connecttobootstrap():
            raise ConnectionError("Cannot connect to any bootstrap")
        myaddr = findOwnIP()
        myport = self.socket.getsockname()[1]
        self.me = Peer(myaddr, myport, NODE_CLIENT)
        self.commandnumber = random.randint(1, sys.maxint)

        # synchronization
        self.lock = Lock()
        self.pendingops = {}  # pending requests indexed by commandnumber
        self.doneops = {}  # requests that are finalized, indexed by command number

        # spawn thread, invoke recv_loop
        try:
            recv_thread = Thread(target=self.recv_loop, name='ReceiveThread')
            recv_thread.daemon = True
            recv_thread.start()
        except (KeyboardInterrupt, SystemExit):
            self._graceexit()

    def _getipportpairs(self, bootaddr, bootport):
        for node in socket.getaddrinfo(bootaddr, bootport, socket.AF_INET, socket.SOCK_STREAM):
            yield (node[4][0],bootport)

    def getbootstrapfromdomain(self, domainname):
        tmpbootstraplist = []
        try:
            answers = dns.resolver.query('_concoord._tcp.'+domainname, 'SRV')
            for rdata in answers:
                for peer in self._getipportpairs(str(rdata.target), rdata.port):
                    if peer not in tmpbootstraplist:
                        tmpbootstraplist.append(peer)
        except (dns.resolver.NXDOMAIN, dns.exception.Timeout):
            if self.debug: print "Cannot resolve name"
        return tmpbootstraplist

    def discoverbootstrap(self, givenbootstrap):
        tmpbootstraplist = []
        try:
            for bootstrap in givenbootstrap.split(","):
                bootstrap = bootstrap.strip()
                # The bootstrap list is read only during initialization
                if bootstrap.find(":") >= 0:
                    bootaddr,bootport = bootstrap.split(":")
                    for peer in self._getipportpairs(bootaddr, int(bootport)):
                        if peer not in tmpbootstraplist:
                            tmpbootstraplist.append(peer)
                else:
                    self.domainname = bootstrap
                    tmpbootstraplist = self.getbootstrapfromdomain(self.domainname)
        except ValueError:
            if self.debug: print "bootstrap usage: ipaddr1:port1,ipaddr2:port2 or domainname"
            self._graceexit()
        return tmpbootstraplist

    def connecttobootstrap(self):
        connected = False
        for boottuple in self.bootstraplist:
            try:
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                self.socket.connect(boottuple)
                self.conn = Connection(self.socket)
                self.conn.settimeout(CLIENTRESENDTIMEOUT)
                self.bootstrap = boottuple
                connected = True
                if self.debug: print "Connected to new bootstrap: ", boottuple
                break
            except socket.error, e:
                if self.debug: print "Socket.Error: ", e
                continue
        return connected

    def trynewbootstrap(self):
        if self.domainname:
            self.bootstraplist = self.getbootstrapfromdomain(self.domainname)
        else:
            oldbootstrap = self.bootstraplist.pop(0)
            self.bootstraplist.append(oldbootstrap)
        return self.connecttobootstrap()

    def invoke_command(self, *args):
        # create a request descriptor
        reqdesc = ReqDesc(self, args, self.token)
        self.pendingops[reqdesc.commandnumber] = reqdesc
        # send the request
        with self.writelock:
            self.conn.send(reqdesc.cm)
        with self.lock:
            try:
                while not reqdesc.replyvalid:
                    reqdesc.replyarrived.wait()
            except KeyboardInterrupt:
                self._graceexit()
            del self.pendingops[reqdesc.commandnumber]
        if reqdesc.reply.replycode == CR_OK or reqdesc.reply.replycode == CR_UNBLOCK:
            return reqdesc.reply.reply
        elif reqdesc.reply.replycode == CR_EXCEPTION:
            raise Exception(pickle.loads(reqdesc.reply.reply))
        else:
            print "Unexpected Client Reply Code: %d" % reqdesc.reply.replycode

    def recv_loop(self, *args):
        socketset = [self.socket]
        while True:
            try:
                needreconfig = False
                inputready,outputready,exceptready = select.select(socketset, [], socketset, 0)
                for s in inputready:
                    reply = self.conn.receive()
                    if reply is None:
                        needreconfig = True
                    elif reply and reply.type == MSG_CLIENTREPLY:
                        reqdesc = self.pendingops[reply.inresponseto]
                        with self.lock:
                            if reply.replycode == CR_OK or reply.replycode == CR_EXCEPTION or reply.replycode == CR_UNBLOCK:
                                # actionable response, wake up the thread
                                if reply.replycode == CR_UNBLOCK:
                                    assert reqdesc.lastcr == CR_BLOCK, "unblocked thread not previously blocked"
                                reqdesc.lastcr = reply.replycode
                                reqdesc.reply = reply
                                reqdesc.replyvalid = True
                                reqdesc.replyarrived.notify()
                            elif reply.replycode == CR_INPROGRESS or reply.replycode == CR_BLOCK:
                                # the thread is already waiting, no need to do anything
                                reqdesc.lastcr = reply.replycode
                            elif reply.replycode == CR_REJECTED or reply.replycode == CR_LEADERNOTREADY:
                                needreconfig = True
                            else:
                                print "should not happen -- unknown response type"

                while needreconfig:
                    if not self.trynewbootstrap():
                        raise ConnectionError("Cannot connect to any bootstrap")
                    needreconfig = False

                    # check if we need to re-send any pending operations
                    for commandno,reqdesc in self.pendingops.iteritems():
                        if not reqdesc.replyvalid and reqdesc.lastreplycr != CR_BLOCK:
                            reqdesc.sendcount += 1
                            reqdesc.cm[FLD_SENDCOUNT] = reqdesc.sendcount
                            if not self.conn.send(reqdesc.cm):
                                needreconfig = True
                            continue
            except KeyboardInterrupt:
                self._graceexit()

    def _graceexit(self):
        os._exit(0)

########NEW FILE########
__FILENAME__ = clientproxy
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: ConCoord Client Proxy
@copyright: See LICENSE
'''
import os, random, select, socket, sys, threading, time
from threading import Lock
import cPickle as pickle
from concoord.pack import *
from concoord.enums import *
from concoord.utils import *
from concoord.exception import *
from concoord.connection import ConnectionPool, Connection
from concoord.message import *
from concoord.pvalue import PValueSet
try:
    import dns
    import dns.resolver
    import dns.exception
except:
    print("Install dnspython: http://www.dnspython.org/")

class ClientProxy():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.debug = debug
        self.timeout = timeout
        self.domainname = None
        self.token = token
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.writelock = Lock()

        self.bootstraplist = self.discoverbootstrap(bootstrap)
        if len(self.bootstraplist) == 0:
            raise ConnectionError("No bootstrap found")
        if not self.connecttobootstrap():
            raise ConnectionError("Cannot connect to any bootstrap")
        myaddr = findOwnIP()
        myport = self.socket.getsockname()[1]
        self.me = Peer(myaddr, myport, NODE_CLIENT)
        self.commandnumber = random.randint(1, sys.maxint)

    def _getipportpairs(self, bootaddr, bootport):
        for node in socket.getaddrinfo(bootaddr, bootport, socket.AF_INET, socket.SOCK_STREAM):
            yield (node[4][0],bootport)

    def getbootstrapfromdomain(self, domainname):
        tmpbootstraplist = []
        try:
            answers = dns.resolver.query('_concoord._tcp.'+domainname, 'SRV')
            for rdata in answers:
                for peer in self._getipportpairs(str(rdata.target), rdata.port):
                    if peer not in tmpbootstraplist:
                        tmpbootstraplist.append(peer)
        except (dns.resolver.NXDOMAIN, dns.exception.Timeout):
            if self.debug: print "Cannot resolve name"
        return tmpbootstraplist

    def discoverbootstrap(self, givenbootstrap):
        tmpbootstraplist = []
        try:
            for bootstrap in givenbootstrap.split(","):
                bootstrap = bootstrap.strip()
                # The bootstrap list is read only during initialization
                if bootstrap.find(":") >= 0:
                    bootaddr,bootport = bootstrap.split(":")
                    for peer in self._getipportpairs(bootaddr, int(bootport)):
                        if peer not in tmpbootstraplist:
                            tmpbootstraplist.append(peer)
                else:
                    self.domainname = bootstrap
                    tmpbootstraplist = self.getbootstrapfromdomain(self.domainname)
        except ValueError:
            if self.debug: print "bootstrap usage: ipaddr1:port1,ipaddr2:port2 or domainname"
            self._graceexit()
        return tmpbootstraplist

    def connecttobootstrap(self):
        connected = False
        for boottuple in self.bootstraplist:
            try:
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                self.socket.connect(boottuple)
                self.conn = Connection(self.socket)
                self.conn.settimeout(CLIENTRESENDTIMEOUT)
                self.bootstrap = boottuple
                connected = True
                if self.debug: print "Connected to new bootstrap: ", boottuple
                break
            except socket.error, e:
                if self.debug: print "Socket.Error: ", e
                continue
        return connected

    def trynewbootstrap(self):
        if self.domainname:
            self.bootstraplist = self.getbootstrapfromdomain(self.domainname)
        else:
            oldbootstrap = self.bootstraplist.pop(0)
            self.bootstraplist.append(oldbootstrap)
        return self.connecttobootstrap()

    def invoke_command(self, *args):
        # create a request descriptor
        resend = True
        sendcount = -1
        lastreplycode = -1
        self.commandnumber += 1
        clientmsg = create_message(MSG_CLIENTREQUEST, self.me,
                                   {FLD_PROPOSAL: Proposal(self.me, self.commandnumber, args),
                                    FLD_TOKEN: self.token,
                                    FLD_CLIENTBATCH: False})
        while True:
            sendcount += 1
            clientmsg[FLD_SENDCOUNT] = sendcount
            # send the clientrequest
            if resend:
                success = self.conn.send(clientmsg)
                if not success:
                    self.reconfigure()
                    continue
                resend = False
        # Receive reply
            try:
                for reply in self.conn.received_bytes():
                    if reply and reply.type == MSG_CLIENTREPLY:
                        if reply.replycode == CR_OK:
                            return reply.reply
                        elif reply.replycode == CR_UNBLOCK:
                            # actionable response, wake up the thread
                            assert lastreplycode == CR_BLOCK, "unblocked thread not previously blocked"
                            return reply.reply
                        elif reply.replycode == CR_EXCEPTION:
                            raise Exception(pickle.loads(reply.reply))
                        elif reply.replycode == CR_INPROGRESS or reply.replycode == CR_BLOCK:
                            # the thread is already waiting, no need to do anything
                            lastreplycode = reply.replycode
                            # go wait for another message
                            continue
                        elif reply.replycode == CR_REJECTED or reply.replycode == CR_LEADERNOTREADY:
                            resend = True
                            self.reconfigure()
                            continue
                        else:
                            print "Unknown Client Reply Code."
            except ConnectionError:
                resend = True
                self.reconfigure()
                continue
            except KeyboardInterrupt:
                self._graceexit()

    def reconfigure(self):
        if not self.trynewbootstrap():
            raise ConnectionError("Cannot connect to any bootstrap")

    def _graceexit(self):
        os._exit(0)

########NEW FILE########
__FILENAME__ = codegen
# -*- coding: utf-8 -*-
"""
    codegen
    ~~~~~~~

    Extension to ast that allow ast -> python code generation.

    :copyright: Copyright 2008 by Armin Ronacher.
    :license: BSD.
"""
from ast import *

BOOLOP_SYMBOLS = {
    And:        'and',
    Or:         'or'
}

BINOP_SYMBOLS = {
    Add:        '+',
    Sub:        '-',
    Mult:       '*',
    Div:        '/',
    FloorDiv:   '//',
    Mod:        '%',
    LShift:     '<<',
    RShift:     '>>',
    BitOr:      '|',
    BitAnd:     '&',
    BitXor:     '^',
    Pow:        '**'
}

CMPOP_SYMBOLS = {
    Eq:         '==',
    Gt:         '>',
    GtE:        '>=',
    In:         'in',
    Is:         'is',
    IsNot:      'is not',
    Lt:         '<',
    LtE:        '<=',
    NotEq:      '!=',
    NotIn:      'not in'
}

UNARYOP_SYMBOLS = {
    Invert:     '~',
    Not:        'not',
    UAdd:       '+',
    USub:       '-'
}

ALL_SYMBOLS = {}
ALL_SYMBOLS.update(BOOLOP_SYMBOLS)
ALL_SYMBOLS.update(BINOP_SYMBOLS)
ALL_SYMBOLS.update(CMPOP_SYMBOLS)
ALL_SYMBOLS.update(UNARYOP_SYMBOLS)


def to_source(node, indent_with=' ' * 4, add_line_information=False):
    """This function can convert a node tree back into python sourcecode.
    This is useful for debugging purposes, especially if you're dealing with
    custom asts not generated by python itself.

    It could be that the sourcecode is evaluable when the AST itself is not
    compilable / evaluable.  The reason for this is that the AST contains some
    more data than regular sourcecode does, which is dropped during
    conversion.

    Each level of indentation is replaced with `indent_with`.  Per default this
    parameter is equal to four spaces as suggested by PEP 8, but it might be
    adjusted to match the application's styleguide.

    If `add_line_information` is set to `True` comments for the line numbers
    of the nodes are added to the output.  This can be used to spot wrong line
    number information of statement nodes.
    """
    generator = SourceGenerator(indent_with, add_line_information)
    generator.visit(node)
    return ''.join(generator.result)

class SourceGenerator(NodeVisitor):
    """This visitor is able to transform a well formed syntax tree into python
    sourcecode.  For more details have a look at the docstring of the
    `node_to_source` function.
    """

    def __init__(self, indent_with, add_line_information=False):
        self.result = []
        self.indent_with = indent_with
        self.add_line_information = add_line_information
        self.indentation = 0
        self.new_lines = 0

    def write(self, x):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)
            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0
        self.result.append(x)

    def newline(self, node=None, extra=0):
        self.new_lines = max(self.new_lines, 1 + extra)
        if node is not None and self.add_line_information:
            self.write('# line: %s' % node.lineno)
            self.new_lines = 1

    def body(self, statements):
        self.new_line = True
        self.indentation += 1
        for stmt in statements:
            self.visit(stmt)
        self.indentation -= 1

    def body_or_else(self, node):
        self.body(node.body)
        if node.orelse:
            self.newline()
            self.write('else:')
            self.body(node.orelse)

    def signature(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        padding = [None] * (len(node.args) - len(node.defaults))
        for arg, default in zip(node.args, padding + node.defaults):
            write_comma()
            self.visit(arg)
            if default is not None:
                self.write('=')
                self.visit(default)
        if node.vararg is not None:
            write_comma()
            self.write('*' + node.vararg)
        if node.kwarg is not None:
            write_comma()
            self.write('**' + node.kwarg)

    def decorators(self, node):
        for decorator in node.decorator_list:
            self.newline(decorator)
            self.write('@')
            self.visit(decorator)

    # Statements

    def visit_Assign(self, node):
        self.newline(node)
        for idx, target in enumerate(node.targets):
            if idx:
                self.write(', ')
            self.visit(target)
        self.write(' = ')
        self.visit(node.value)

    def visit_AugAssign(self, node):
        self.newline(node)
        self.visit(node.target)
        self.write(BINOP_SYMBOLS[type(node.op)] + '=')
        self.visit(node.value)

    def visit_ImportFrom(self, node):
        self.newline(node)
        self.write('from %s%s import ' % ('.' * node.level, node.module))
        for idx, item in enumerate(node.names):
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_Import(self, node):
        self.newline(node)
        for item in node.names:
            self.write('import ')
            self.visit(item)

    def visit_Expr(self, node):
        self.newline(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.newline(extra=1)
        self.decorators(node)
        self.newline(node)
        self.write('def %s(' % node.name)
        self.signature(node.args)
        self.write('):')
        self.body(node.body)

    def visit_ClassDef(self, node):
        have_args = []
        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args.append(True)
                self.write('(')

        self.newline(extra=2)
        self.decorators(node)
        self.newline(node)
        self.write('class %s' % node.name)
        for base in node.bases:
            paren_or_comma()
            self.visit(base)
        # the if here is used to keep this module compatible
        # with python 2.6.
        if hasattr(node, 'keywords'):
            for keyword in node.keywords:
                paren_or_comma()
                self.write(keyword.arg + '=')
                self.visit(keyword.value)
            if node.starargs is not None:
                paren_or_comma()
                self.write('*')
                self.visit(node.starargs)
            if node.kwargs is not None:
                paren_or_comma()
                self.write('**')
                self.visit(node.kwargs)
        self.write(have_args and '):' or ':')
        self.body(node.body)

    def visit_If(self, node):
        self.newline(node)
        self.write('if ')
        self.visit(node.test)
        self.write(':')
        self.body(node.body)
        while True:
            else_ = node.orelse
            if len(else_) == 1 and isinstance(else_[0], If):
                node = else_[0]
                self.newline()
                self.write('elif ')
                self.visit(node.test)
                self.write(':')
                self.body(node.body)
            else:
                self.newline()
                self.write('else:')
                self.body(else_)
                break

    def visit_For(self, node):
        self.newline(node)
        self.write('for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        self.write(':')
        self.body_or_else(node)

    def visit_While(self, node):
        self.newline(node)
        self.write('while ')
        self.visit(node.test)
        self.write(':')
        self.body_or_else(node)

    def visit_With(self, node):
        self.newline(node)
        self.write('with ')
        self.visit(node.context_expr)
        if node.optional_vars is not None:
            self.write(' as ')
            self.visit(node.optional_vars)
        self.write(':')
        self.body(node.body)

    def visit_Pass(self, node):
        self.newline(node)
        self.write('pass')

    def visit_Print(self, node):
        # python 2.6 only
        self.newline(node)
        self.write('print ')
        want_comma = False
        if node.dest is not None:
            self.write(' >> ')
            self.visit(node.dest)
            want_comma = True
        for value in node.values:
            if want_comma:
                self.write(', ')
            self.visit(value)
            want_comma = True
        if not node.nl:
            self.write(',')

    def visit_Delete(self, node):
        self.newline(node)
        self.write('del ')
        if hasattr(node, 'targets'):
            for idx, target in enumerate(node.targets):
                if idx:
                    self.write(', ')
        else:
            for idx, target in enumerate(node):
                if idx:
                    self.write(', ')
                self.visit(target)

    def visit_TryExcept(self, node):
        self.newline(node)
        self.write('try:')
        self.body(node.body)
        for handler in node.handlers:
            self.visit(handler)

    def visit_TryFinally(self, node):
        self.newline(node)
        self.write('try:')
        self.body(node.body)
        self.newline(node)
        self.write('finally:')
        self.body(node.finalbody)

    def visit_Global(self, node):
        self.newline(node)
        self.write('global ' + ', '.join(node.names))

    def visit_Nonlocal(self, node):
        self.newline(node)
        self.write('nonlocal ' + ', '.join(node.names))

    def visit_Return(self, node):
        self.newline(node)
        self.write('return ')
        if node.value is not None:
            self.visit(node.value)

    def visit_Break(self, node):
        self.newline(node)
        self.write('break')

    def visit_Continue(self, node):
        self.newline(node)
        self.write('continue')

    def visit_Raise(self, node):
        # Python 2.6 / 3.0 compatibility
        self.newline(node)
        self.write('raise')
        if hasattr(node, 'exc') and node.exc is not None:
            self.write(' ')
            self.visit(node.exc)
            if node.cause is not None:
                self.write(' from ')
                self.visit(node.cause)
        elif hasattr(node, 'type') and node.type is not None:
            self.visit(node.type)
            if node.inst is not None:
                self.write(', ')
                self.visit(node.inst)
            if node.tback is not None:
                self.write(', ')
                self.visit(node.tback)

    # Expressions

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.write('.' + node.attr)

    def visit_Call(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def visit_Name(self, node):
        self.write(node.id)

    def visit_Str(self, node):
        self.write(repr(node.s))

    def visit_Bytes(self, node):
        self.write(repr(node.s))

    def visit_Num(self, node):
        self.write(repr(node.n))

    def visit_Tuple(self, node):
        self.write('(')
        idx = -1
        for idx, item in enumerate(node.elts):
            if idx:
                self.write(', ')
            self.visit(item)
        self.write(idx and ')' or ',)')

    def sequence_visit(left, right):
        def visit(self, node):
            self.write(left)
            for idx, item in enumerate(node.elts):
                if idx:
                    self.write(', ')
                self.visit(item)
            self.write(right)
        return visit

    visit_List = sequence_visit('[', ']')
    visit_Set = sequence_visit('{', '}')
    del sequence_visit

    def visit_Dict(self, node):
        self.write('{')
        for idx, (key, value) in enumerate(zip(node.keys, node.values)):
            if idx:
                self.write(', ')
            self.visit(key)
            self.write(': ')
            self.visit(value)
        self.write('}')

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.write(' %s ' % BINOP_SYMBOLS[type(node.op)])
        self.visit(node.right)

    def visit_BoolOp(self, node):
        self.write('(')
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % BOOLOP_SYMBOLS[type(node.op)])
            self.visit(value)
        self.write(')')

    def visit_Compare(self, node):
        self.write('(')
        self.visit(node.left)
        for op, right in zip(node.ops, node.comparators):
            self.write(' %s %%' % CMPOP_SYMBOLS[type(op)])
            self.visit(right)
        self.write(')')

    def visit_UnaryOp(self, node):
        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)]
        self.write(op)
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):
        self.visit(node.value)
        self.write('[')
        self.visit(node.slice)
        self.write(']')

    def visit_Slice(self, node):
        if node.lower is not None:
            self.visit(node.lower)
        self.write(':')
        if node.upper is not None:
            self.visit(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, Name) and node.step.id == 'None'):
                self.visit(node.step)

    def visit_ExtSlice(self, node):
        for idx, item in node.dims:
            if idx:
                self.write(', ')
            self.visit(item)

    def visit_Yield(self, node):
        self.write('yield ')
        self.visit(node.value)

    def visit_Lambda(self, node):
        self.write('lambda ')
        self.signature(node.args)
        self.write(': ')
        self.visit(node.body)

    def visit_Ellipsis(self, node):
        self.write('Ellipsis')

    def generator_visit(left, right):
        def visit(self, node):
            self.write(left)
            self.visit(node.elt)
            for comprehension in node.generators:
                self.visit(comprehension)
            self.write(right)
        return visit

    visit_ListComp = generator_visit('[', ']')
    visit_GeneratorExp = generator_visit('(', ')')
    visit_SetComp = generator_visit('{', '}')
    del generator_visit

    def visit_DictComp(self, node):
        self.write('{')
        self.visit(node.key)
        self.write(': ')
        self.visit(node.value)
        for comprehension in node.generators:
            self.visit(comprehension)
        self.write('}')

    def visit_IfExp(self, node):
        self.visit(node.body)
        self.write(' if ')
        self.visit(node.test)
        self.write(' else ')
        self.visit(node.orelse)

    def visit_Starred(self, node):
        self.write('*')
        self.visit(node.value)

    def visit_Repr(self, node):
        # python 2.6 only
        self.write('`')
        self.visit(node.value)
        self.write('`')

    # Helper Nodes

    def visit_alias(self, node):
        self.write(node.name)
        if node.asname is not None:
            self.write(' as ' + node.asname)

    def visit_comprehension(self, node):
        self.write(' for ')
        self.visit(node.target)
        self.write(' in ')
        self.visit(node.iter)
        if node.ifs:
            for if_ in node.ifs:
                self.write(' if ')
                self.visit(if_)

    def visit_excepthandler(self, node):
        self.newline(node)
        self.write('except')
        if node.type is not None:
            self.write(' ')
            self.visit(node.type)
            if node.name is not None:
                self.write(' as ')
                self.visit(node.name)
        self.write(':')
        self.body(node.body)

########NEW FILE########
__FILENAME__ = connection
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Connections provide thread-safe send() and receive() functions, paying attention to message boundaries.
       ConnectionPools organize collections of connections.
@copyright: See LICENSE
'''
import sys
import socket, errno, select
import struct
import StringIO
import time
import msgpack
import random
from threading import Lock
from concoord.pack import *
from concoord.message import *
from concoord.exception import ConnectionError

class ConnectionPool():
    """ConnectionPool keeps the connections that a certain Node knows of.
    The connections can be indexed by a Peer instance or a socket."""
    def __init__(self):
        self.pool_lock = Lock()
        self.poolbypeer = {}
        self.poolbysocket = {}
        self.epoll = None
        self.epollsockets = {}
        # Sockets that are being actively listened to
        self.activesockets = set([])
        # Sockets that we didn't receive a msg on yet
        self.nascentsockets = set([])

    def add_connection_to_self(self, peer, conn):
        """Adds a SelfConnection to the ConnectionPool by its Peer"""
        if str(peer) not in self.poolbypeer:
            conn.peerid = str(peer)

    def add_connection_to_peer(self, peer, conn):
        """Adds a Connection to the ConnectionPool by its Peer"""
        if str(peer) not in self.poolbypeer:
            conn.peerid = str(peer)
            with self.pool_lock:
                self.poolbypeer[conn.peerid] = conn
                self.activesockets.add(conn.thesocket)
                if conn.thesocket in self.nascentsockets:
                    self.nascentsockets.remove(conn.thesocket)

    def del_connection_by_peer(self, peer):
        """ Deletes a Connection from the ConnectionPool by its Peer"""
        peerstr = str(peer)
        with self.pool_lock:
            if self.poolbypeer.has_key(peerstr):
                conn = self.poolbypeer[peerstr]
                del self.poolbypeer[peerstr]
                del self.poolbysocket[conn.thesocket.fileno()]
                if conn.thesocket in self.activesockets:
                    self.activesockets.remove(conn.thesocket)
                if conn.thesocket in self.nascentsockets:
                    self.nascentsockets.remove(conn.thesocket)
                conn.close()
            else:
                print "Trying to delete a non-existent connection from the connection pool."

    def del_connection_by_socket(self, thesocket):
        """ Deletes a Connection from the ConnectionPool by its Peer"""
        with self.pool_lock:
            if self.poolbysocket.has_key(thesocket.fileno()):
                connindict = self.poolbysocket[thesocket.fileno()]
                for connkey,conn in self.poolbypeer.iteritems():
                    if conn == connindict:
                        del self.poolbypeer[connkey]
                        break
                del self.poolbysocket[thesocket.fileno()]
                if thesocket in self.activesockets:
                    self.activesockets.remove(thesocket)
                if thesocket in self.nascentsockets:
                    self.nascentsockets.remove(thesocket)
                connindict.close()
            else:
                print "Trying to delete a non-existent socket from the connection pool."

    def get_connection_by_peer(self, peer):
        """Returns a Connection given corresponding Peer triple"""
        peerstr = str(peer)
        with self.pool_lock:
            if self.poolbypeer.has_key(peerstr):
                return self.poolbypeer[peerstr]
            else:
                try:
                    thesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    thesocket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                    thesocket.connect((peer[0], peer[1]))
                    thesocket.setblocking(0)
                    conn = Connection(thesocket, peerstr)
                    self.poolbypeer[peerstr] = conn
                    self.poolbysocket[thesocket.fileno()] = conn
                    if self.epoll:
                        self.epoll.register(thesocket.fileno(), select.EPOLLIN)
                        self.epollsockets[thesocket.fileno()] = thesocket
                    else:
                        self.activesockets.add(thesocket)
                        if thesocket in self.nascentsockets:
                            self.nascentsockets.remove(thesocket)
                    return conn
                except Exception as e:
                    return None

    def get_connection_by_socket(self, thesocket):
        """Returns a Connection given corresponding socket.
        A new Connection is created and added to the
        ConnectionPool if it doesn't exist.
        """
        with self.pool_lock:
            if self.poolbysocket.has_key(thesocket.fileno()):
                return self.poolbysocket[thesocket.fileno()]
            else:
                conn = Connection(thesocket)
                self.poolbysocket[thesocket.fileno()] = conn
                self.activesockets.add(thesocket)
                if thesocket in self.nascentsockets:
                    self.nascentsockets.remove(thesocket)
                return conn

    def __str__(self):
        """Returns ConnectionPool information"""
        peerstr= "\n".join(["%s: %s" % (str(peer), str(conn)) for peer,conn in self.poolbypeer.iteritems()])
        socketstr= "\n".join(["%s: %s" % (str(socket), str(conn)) for socket,conn in self.poolbysocket.iteritems()])
        temp = "Connection to Peers:\n%s\nConnection to Sockets:\n%s" %(peerstr, socketstr)
        return temp

class Connection():
    """Connection encloses the socket and send/receive functions for a connection."""
    def __init__(self, socket, peerid=None):
        """Initialize Connection"""
        self.thesocket = socket
        self.peerid = peerid
        self.readlock = Lock()
        self.writelock = Lock()
        self.outgoing = ''
        # Rethink the size of the bytearray versus the
        # number of bytes requested in recv_into
        self.incomingbytearray = bytearray(100000)
        self.incoming = memoryview(self.incomingbytearray)
        self.incomingoffset = 0
        # Busy wait count
        self.busywait = 0

    def __str__(self):
        """Return Connection information"""
        if self.thesocket is None:
            return "Connection empty."
        return "Connection to Peer %s" % (self.peerid)

    # deprecated
    def receive(self):
        with self.readlock:
            """receive a message on the Connection"""
            try:
                lstr = self.receive_n_bytes(4)
                msg_length = struct.unpack("I", lstr[0:4])[0]
                msgstr = self.receive_n_bytes(msg_length)
                msgdict = msgpack.unpackb(msgstr, use_list=False)
                return parse_message(msgdict)
            except IOError as inst:
                return None

    # used only while receiving a very large message
    def receive_n_bytes(self, msg_length):
        msgstr = ''
        while len(msgstr) != msg_length:
            try:
                chunk = self.thesocket.recv(min(1024, msg_length-len(msgstr)))
            except IOError, e:
                if isinstance(e.args, tuple):
                    if e[0] == errno.EAGAIN:
                        continue
                raise e
            if len(chunk) == 0:
                raise IOError
            msgstr += chunk
        return msgstr

    def received_bytes(self):
        with self.readlock:
            datalen = 0
            try:
                datalen = self.thesocket.recv_into(self.incoming[self.incomingoffset:],
                                                   100000-self.incomingoffset)
            except IOError as inst:
                # [Errno 104] Connection reset by peer
                raise ConnectionError()

            if datalen == 0:
                if self.incomingoffset == 100000:
                    # buffer too small for a complete message
                    msg_length = struct.unpack("I", self.incoming[0:4].tobytes())[0]
                    msgstr = self.incoming[4:].tobytes()
                    try:
                        msgstr += self.receive_n_bytes(msg_length-(len(self.incoming)-4))
                        msgdict = msgpack.unpackb(msgstr, use_list=False)
                        self.incomingoffset = 0
                        yield parse_message(msgdict)
                    except IOError as inst:
                        self.incomingoffset = 0
                        raise ConnectionError()
                else:
                    raise ConnectionError()

            self.incomingoffset += datalen
            while self.incomingoffset >= 4:
                msg_length = (ord(self.incoming[3]) << 24) | (ord(self.incoming[2]) << 16) | (ord(self.incoming[1]) << 8) | ord(self.incoming[0])
                # check if there is a complete msg, if so return the msg
                # otherwise return None
                if self.incomingoffset >= msg_length+4:
                    msgdict = msgpack.unpackb(self.incoming[4:msg_length+4].tobytes(), use_list=False)
                    # this operation cuts the incoming buffer
                    if self.incomingoffset > msg_length+4:
                        self.incoming[:self.incomingoffset-(msg_length+4)] = self.incoming[msg_length+4:self.incomingoffset]
                    self.incomingoffset -= msg_length+4
                    yield parse_message(msgdict)
                else:
                    break

    def send(self, msg):
        with self.writelock:
            """pack and send a message on the Connection"""
            messagestr = msgpack.packb(msg)
            message = struct.pack("I", len(messagestr)) + messagestr
            try:
                while len(message) > 0:
                    try:
                        bytesent = self.thesocket.send(message)
                        message = message[bytesent:]
                    except IOError, e:
                        if isinstance(e.args, tuple):
                            if e[0] == errno.EAGAIN:
                                self.busywait += 1
                                continue
                            else:
                                raise e
                return True
            except socket.error, e:
                 if isinstance(e.args, tuple):
                     if e[0] == errno.EPIPE:
                         return False
            except IOError, e:
                print "Send Error: ", e
            except AttributeError, e:
                pass
            return False

    def settimeout(self, timeout):
        try:
            self.thesocket.settimeout(timeout)
        except socket.error, e:
            if isinstance(e.args, tuple):
                if e[0] == errno.EBADF:
                    print "Socket closed."

    def close(self):
        """Close the Connection"""
        self.thesocket.close()
        self.thesocket = None

class SelfConnection():
    """Connection of a node to itself"""
    def __init__(self, receivedmessageslist, receivedmessages_semaphore, peerid=""):
        """Initialize Connection"""
        self.peerid = peerid
        self.receivedmessages_semaphore = receivedmessages_semaphore
        self.receivedmessageslist = receivedmessageslist

    def __str__(self):
        """Return Connection information"""
        return "SelfConnection of Peer %s" % (self.peerid)

    def send(self, msg):
        """Gets a msgdict and parses it and adds it to the received queue"""
        self.receivedmessages.append((parse_message(msg), self))
        self.receivedmessages_semaphore.release()
        return True

########NEW FILE########
__FILENAME__ = enums
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: This class holds enums that are widely used throughout the program
       Because it imports itself, this module MUST NOT HAVE ANY SIDE EFFECTS!!!!
@copyright: See LICENSE
'''
import enums

# message types
MSG_CLIENTREQUEST, MSG_CLIENTREPLY, MSG_INCCLIENTREQUEST, \
    MSG_PREPARE, MSG_PREPARE_ADOPTED, MSG_PREPARE_PREEMPTED, MSG_PROPOSE, \
    MSG_PROPOSE_ACCEPT, MSG_PROPOSE_REJECT, \
    MSG_HELO, MSG_HELOREPLY, MSG_PING, MSG_PINGREPLY, \
    MSG_UPDATE, MSG_UPDATEREPLY, \
    MSG_PERFORM, MSG_RESPONSE, \
    MSG_GARBAGECOLLECT, MSG_STATUS, MSG_ISSUE = range(20)

# message fields
FLD_ID, FLD_TYPE, FLD_SRC, FLD_BALLOTNUMBER, FLD_COMMANDNUMBER, \
FLD_PROPOSAL, FLD_DECISIONS, \
FLD_REPLY, FLD_REPLYCODE, FLD_INRESPONSETO, FLD_SNAPSHOT, FLD_PVALUESET, FLD_LEADER, \
FLD_TOKEN, FLD_CLIENTBATCH, FLD_SERVERBATCH, FLD_SENDCOUNT, FLD_DECISIONBALLOTNUMBER = range(18)

# node types
NODE_CLIENT, NODE_REPLICA, NODE_NAMESERVER = range(3)

# error_types
ERR_NOERROR, ERR_NOTLEADER, ERR_INITIALIZING = range(3)

# nameserver service types
NS_MASTER, NS_SLAVE, NS_ROUTE53 = range(1,4)

# proxy types
PR_BASIC, PR_BLOCK, PR_CBATCH, PR_SBATCH = range(4)

# command result
META = 'META'
BLOCK = 'BLOCK'
UNBLOCK = 'UNBLOCK'

# executed indexing
EXC_RCODE, EXC_RESULT, EXC_UNBLOCKED = range(3)

# client reply codes
CR_OK, CR_INPROGRESS, CR_LEADERNOTREADY, CR_REJECTED, \
CR_EXCEPTION, CR_BLOCK, CR_UNBLOCK, CR_META, CR_BATCH = range(9)

# timeouts
ACKTIMEOUT = 1
LIVENESSTIMEOUT = 5
NASCENTTIMEOUT = 20 * ACKTIMEOUT
CLIENTRESENDTIMEOUT = 5
BACKOFFDECREASETIMEOUT = 30
TESTTIMEOUT = 1
BOOTSTRAPCONNECTTIMEOUT = 60

# ballot
BALLOTEPOCH = 0
BALLOTNO = 1
BALLOTNODE = 2

# backoff
BACKOFFINCREASE = 0.1

METACOMMANDS = set(["_add_node", "_del_node", "_garbage_collect"])
WINDOW = 10
GARBAGEPERIOD = 100000

NOOP = "do_noop"

# UDPPACKETLEN
UDPMAXLEN = 1024

###########################
# code to convert enum variables to strings of different kinds

# convert a set of enums with a given prefix into a dictionary
def get_var_mappings(prefix):
    """Returns a dictionary with <enumvalue, enumname> mappings"""
    return dict([(getattr(enums,varname),varname.replace(prefix, "", 1)) for varname in dir(enums) if varname.startswith(prefix)])

# convert a set of enums with a given prefix into a list
def get_var_list(prefix):
    """Returns a list of enumnames"""
    return [name for (value,name) in sorted(get_var_mappings(prefix).iteritems())]

msg_names = get_var_list("MSG_")
node_names = get_var_list("NODE_")
cmd_states = get_var_list("CMD_")
err_types = get_var_list("ERR_")
cr_codes = get_var_list("CR_")
ns_services = get_var_list("NS_")

########NEW FILE########
__FILENAME__ = exception
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Common ConCoord exceptions.
@copyright: See LICENSE
'''
class ConCoordException(Exception):
    """Abstract base class shared by all concoord exceptions"""
    def __init__(self, msg=''):
        self.msg = msg

class Timeout(ConCoordException):
    """The operation timed out."""
    def __init__(self, value=''):
        self.value = value

    def __str__(self):
        return str(self.value)

class ConnectionError(ConCoordException):
    """Connection cannot be established"""
    def __init__(self, value=''):
        self.value = value

    def __str__(self):
        return str(self.value)

class BlockingReturn(ConCoordException):
    """Blocking Return"""
    def __init__(self, returnvalue=None):
        self.returnvalue = returnvalue

    def __str__(self):
        return str(self.returnvalue)

class UnblockingReturn(ConCoordException):
    """Unblocking Return"""
    def __init__(self, returnvalue=None, unblockeddict={}):
        self.returnvalue = returnvalue
        self.unblocked = unblockeddict

    def __str__(self):
        return str(self.returnvalue) + " ".join(unblockeddict.keys())

########NEW FILE########
__FILENAME__ = logdaemon
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: The Logger Daemon. Receives log messages and prints them.
@copyright: See LICENSE
"""
import socket, time, os, sys, select
from concoord.utils import *

def collect_input(s):
    msg = ''
    while '\n' not in msg:
        chunk = s.recv(1)
        if chunk == '':
            return False
        msg += chunk
    print_event(msg)
    return True

def print_event(event):
    print "%s: %s" % (time.asctime(time.localtime(time.time())), event.strip())
    
def main():
    addr = findOwnIP()
    port = 12000
    try:
        daemonsocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        daemonsocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        daemonsocket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        daemonsocket.bind((addr,int(port)))
        daemonsocket.listen(10)
    except socket.error:
        pass
    print_event("server ready on port %d\n" % port)

    socketset = [daemonsocket]
    while True:
        inputready,outputready,exceptready = select.select(socketset,[],socketset,1)
        for s in inputready:
            try:
                if s == daemonsocket:
                    clientsock,clientaddr = daemonsocket.accept()
                    print_event("accepted a connection from address %s\n" % str(clientaddr))
                    socketset.append(clientsock)
                else:
                    if not collect_input(s):
                        socketset.remove(s)
            except socket.error:
                socketset.remove(s)
        for s in exceptready:
            socketset.remove(s)
        
if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: concoord script
@date: January 20, 2012
@copyright: See LICENSE
'''
import argparse
import signal
from time import sleep,time
import os, sys, time, shutil
import ast, _ast
import concoord
from concoord.enums import *
from concoord.safetychecker import *
from concoord.proxygenerator import *
import ConfigParser

HELPSTR = "concoord, version 1.1.0-release:\n\
concoord replica [-a address -p port -o objectname -b bootstrap -l loggeraddress -w writetodisk -d debug -n domainname -r route53] - starts a replica\n\
concoord route53id [aws_access_key_id] - adds AWS_ACCESS_KEY_ID to route53 CONFIG file\n\
concoord route53key [aws_secret_access_key] - adds AWS_SECRET_ACCESS_KEY to route53 CONFIG file\n\
concoord object [objectfilepath classname] - concoordifies a python object"

ROUTE53CONFIGFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'route53.cfg')
config = ConfigParser.RawConfigParser()

## ROUTE53

def touch_config_file():
    with open(ROUTE53CONFIGFILE, 'a'):
        os.utime(ROUTE53CONFIGFILE, None)

def read_config_file():
    config.read(ROUTE53CONFIGFILE)
    section = 'ENVIRONMENT'
    options = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    rewritten = True
    if not config.has_section(section):
        rewritten = True
        config.add_section(section)
    for option in options:
        if not config.has_option(section, option):
            rewritten = True
            config.set(section, option, '')
    if rewritten:
        # Write to CONFIG file
        with open(ROUTE53CONFIGFILE, 'wb') as configfile:
            config.write(configfile)
        config.read(ROUTE53CONFIGFILE)
    awsid = config.get('ENVIRONMENT', 'AWS_ACCESS_KEY_ID')
    awskey = config.get('ENVIRONMENT', 'AWS_SECRET_ACCESS_KEY')
    return (awsid,awskey)

def print_config_file():
    print "AWS_ACCESS_KEY_ID= %s\nAWS_SECRET_ACCESS_KEY= %s" % read_config_file()

def add_id_to_config(newid):
    awsid,awskey = read_config_file()
    if awsid and awsid == newid:
        print "AWS_ACCESS_KEY_ID is already in the CONFIG file."
        return
    # Write to CONFIG file
    config.set('ENVIRONMENT', 'AWS_ACCESS_KEY_ID', newid)
    with open(ROUTE53CONFIGFILE, 'wb') as configfile:
        config.write(configfile)

def add_key_to_config(newkey):
    awsid,awskey = read_config_file()
    if awskey and awskey == newkey:
        print "AWS_SECRET_ACCESS_KEY is already in the CONFIG file."
        return
    # Write to CONFIG file
    config.set('ENVIRONMENT', 'AWS_SECRET_ACCESS_KEY', newkey)
    with open(ROUTE53CONFIGFILE, 'wb') as configfile:
        config.write(configfile)

## REPLICA

def start_replica():
    node = getattr(__import__('concoord.replica', globals(), locals(), -1), 'Replica')()
    node.startservice()
    signal.signal(signal.SIGINT, node.terminate_handler)
    signal.signal(signal.SIGTERM, node.terminate_handler)
    signal.pause()

def check_object(clientcode):
    astnode = compile(clientcode,"<string>","exec",_ast.PyCF_ONLY_AST)
    v = SafetyVisitor()
    v.visit(astnode)
    return v.safe

def concoordify():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--objectname", action="store", dest="objectname", default='',
                        help="client object dotted name module.Class")
    parser.add_argument("-t", "--token", action="store", dest="securitytoken", default=None,
                        help="security token")
    parser.add_argument("-p", "--proxytype", action="store", dest="proxytype", type=int, default=0,
                        help="0:BASIC, 1:BLOCKING, 2:CLIENT-SIDE BATCHING, 3: SERVER-SIDE BATCHING ")
    parser.add_argument("-s", "--safe", action="store_true", dest="safe", default=False,
                        help="safety checking on/off")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", default=None,
                        help="verbose mode on/off")
    args = parser.parse_args()

    if not args.objectname:
        print parser.print_help()
        return
    import importlib
    objectloc,a,classname = args.objectname.rpartition('.')
    object = None
    try:
        module = importlib.import_module(objectloc)
        if hasattr(module, classname):
            object = getattr(module, classname)()
    except (ValueError, ImportError, AttributeError):
        print "Can't find module %s, check your PYTHONPATH." % objectloc

    if module.__file__.endswith('pyc'):
        filename = module.__file__[:-1]
    else:
        filename = module.__file__
    with open(filename, 'rU') as fd:
        clientcode = fd.read()
    if args.safe:
        if args.verbose:
            print "Checking object safety"
        if not check_object(clientcode):
            print "Object is not safe to execute."
            os._exit(1)
        elif args.verbose:
            print "Object is safe!"
    if args.verbose:
        print "Creating clientproxy"
    clientproxycode = createclientproxy(clientcode, classname, args.securitytoken, args.proxytype)
    clientproxycode = clientproxycode.replace('\n\n\n', '\n\n')
    proxyfile = open(filename[:-3]+"proxy.py", 'w')
    proxyfile.write(clientproxycode)
    proxyfile.close()
    print "Client proxy file created with name: ", proxyfile.name


def main():
    if len(sys.argv) < 2:
        print HELPSTR
        sys.exit()

    eventtype = sys.argv[1].upper()
    sys.argv.pop(1)
    if eventtype == 'REPLICA':
        start_replica()
    elif eventtype == 'ROUTE53ID':
        print "Adding AWS_ACCESS_KEY_ID to CONFIG:", sys.argv[1]
        add_id_to_config(sys.argv[1])
    elif eventtype == 'ROUTE53KEY':
        print "Adding AWS_SECRET_ACCESS_KEY to CONFIG:", sys.argv[1]
        add_key_to_config(sys.argv[1])
    elif eventtype == 'INITIALIZE':
        initialize()
    elif eventtype == 'OBJECT':
        concoordify()
    else:
        print HELPSTR

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = message
from concoord.pack import *
from concoord.enums import *
from concoord.pvalue import *
import msgpack
from threading import Lock

msgidpool = 0
msgidpool_lock = Lock()

def assignuniqueid():
    global msgidpool
    global msgidpool_lock
    with msgidpool_lock:
        tempid = msgidpool
        msgidpool += 1
    return tempid

def create_message(msgtype, src, msgfields={}):
    global msgidpool
    global msgidpool_lock

    m = msgfields
    m[FLD_ID] = assignuniqueid()
    m[FLD_TYPE] = msgtype
    m[FLD_SRC] = src
    return m

def parse_basic(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return Message(msg[FLD_ID], msg[FLD_TYPE], src)

def parse_status(msg):
    return Message(msg[FLD_ID], msg[FLD_TYPE], msg[FLD_SRC])

def parse_heloreply(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return HeloReplyMessage(msg[FLD_ID], msg[FLD_TYPE],
                            src, Peer(msg[FLD_LEADER][0],
                                      msg[FLD_LEADER][1],
                                      msg[FLD_LEADER][2]))

def parse_clientrequest(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    if msg[FLD_CLIENTBATCH]:
        proposal = ProposalClientBatch(msg[FLD_PROPOSAL][0],
                                       msg[FLD_PROPOSAL][1],
                                       msg[FLD_PROPOSAL][2])
    else:
        proposal = Proposal(msg[FLD_PROPOSAL][0],
                            msg[FLD_PROPOSAL][1],
                            msg[FLD_PROPOSAL][2])

    return ClientRequestMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                                proposal, msg[FLD_TOKEN],
                                msg[FLD_SENDCOUNT], msg[FLD_CLIENTBATCH])

def parse_clientreply(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return ClientReplyMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                              msg[FLD_REPLY], msg[FLD_REPLYCODE],
                              msg[FLD_INRESPONSETO])

def parse_prepare(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return PrepareMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                          msg[FLD_BALLOTNUMBER])

def parse_prepare_reply(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    pvalueset = PValueSet()
    for index,pvalue in msg[FLD_PVALUESET].iteritems():
        pvalueset.pvalues[Proposal(index[1][0],
                                   index[1][1],
                                   index[1][2])] = PValue(pvalue[0], pvalue[1], pvalue[2])
    return PrepareReplyMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                               msg[FLD_BALLOTNUMBER], msg[FLD_INRESPONSETO],
                               pvalueset)
def parse_propose(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    if msg[FLD_SERVERBATCH]:
        proposal = ProposalServerBatch([])
        for p in msg[FLD_PROPOSAL][0]:
            proposal.proposals.append(Proposal(p[0], p[1], p[2]))
    else:
        proposal = Proposal(msg[FLD_PROPOSAL][0], msg[FLD_PROPOSAL][1], msg[FLD_PROPOSAL][2])
    return ProposeMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                          msg[FLD_BALLOTNUMBER], msg[FLD_COMMANDNUMBER],
                          proposal, msg[FLD_SERVERBATCH])


def parse_propose_reply(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return ProposeReplyMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                               msg[FLD_BALLOTNUMBER], msg[FLD_INRESPONSETO],
                               msg[FLD_COMMANDNUMBER])

def parse_perform(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    if msg[FLD_SERVERBATCH]:
        proposal = ProposalServerBatch([])
        for p in msg[FLD_PROPOSAL][0]:
            pclient = Peer(p[0][0], p[0][1], p[0][2])
            proposal.proposals.append(Proposal(pclient, p[1], p[2]))
    elif msg[FLD_CLIENTBATCH]:
        proposalclient = Peer(msg[FLD_PROPOSAL][0][0],
                              msg[FLD_PROPOSAL][0][1],
                              msg[FLD_PROPOSAL][0][2])
        proposal = ProposalClientBatch(proposalclient, msg[FLD_PROPOSAL][1], msg[FLD_PROPOSAL][2])
    else:
        proposalclient = Peer(msg[FLD_PROPOSAL][0][0],
                              msg[FLD_PROPOSAL][0][1],
                              msg[FLD_PROPOSAL][0][2])
        proposal = Proposal(proposalclient, msg[FLD_PROPOSAL][1], msg[FLD_PROPOSAL][2])
    return PerformMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                          msg[FLD_COMMANDNUMBER], proposal,
                          msg[FLD_SERVERBATCH], msg[FLD_CLIENTBATCH],
                          msg[FLD_DECISIONBALLOTNUMBER])

def parse_response(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return Message(msg[FLD_ID], msg[FLD_TYPE], src)

def parse_incclientrequest(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    proposalclient = Peer(msg[FLD_PROPOSAL][0][0], msg[FLD_PROPOSAL][0][1], msg[FLD_PROPOSAL][0][2])
    proposal = Proposal(proposalclient, msg[FLD_PROPOSAL][1], msg[FLD_PROPOSAL][2])
    return ClientRequestMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                                proposal, msg[FLD_TOKEN])

def parse_updatereply(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    for commandnumber,command in msg[FLD_DECISIONS].iteritems():
        try:
            msg[FLD_DECISIONS][commandnumber] = Proposal(msg[FLD_DECISIONS][commandnumber][0],
                                                         msg[FLD_DECISIONS][commandnumber][1],
                                                         msg[FLD_DECISIONS][commandnumber][2])
        except IndexError as i:
            msg[FLD_DECISIONS][commandnumber] = Proposal(msg[FLD_DECISIONS][commandnumber][0][0][0],
                                                         msg[FLD_DECISIONS][commandnumber][0][0][1],
                                                         msg[FLD_DECISIONS][commandnumber][0][0][2])
    return UpdateReplyMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                              msg[FLD_DECISIONS])

def parse_garbagecollect(msg):
    src = Peer(msg[FLD_SRC][0], msg[FLD_SRC][1], msg[FLD_SRC][2])
    return GarbageCollectMessage(msg[FLD_ID], msg[FLD_TYPE], src,
                                 msg[FLD_COMMANDNUMBER], msg[FLD_SNAPSHOT])

def parse_message(msg):
    return parse_functions[msg[FLD_TYPE]](msg)

parse_functions = [
    parse_clientrequest, # MSG_CLIENTREQUEST
    parse_clientreply, # MSG_CLIENTREPLY
    parse_incclientrequest, # MSG_INCCLIENTREQUEST

    parse_prepare, # MSG_PREPARE
    parse_prepare_reply, # MSG_PREPARE_ADOPTED
    parse_prepare_reply, # MSG_PREPARE_PREEMPTED
    parse_propose, # MSG_PROPOSE
    parse_propose_reply, # MSG_PROPOSE_ACCEPT
    parse_propose_reply, # MSG_PROPOSE_REJECT

    parse_basic, # MSG_HELO
    parse_heloreply, # MSG_HELOREPLY
    parse_basic, # MSG_PING
    parse_basic, # MSG_PINGREPLY

    parse_basic, # MSG_UPDATE
    parse_updatereply, # MSG_UPDATEREPLY

    parse_perform, # MSG_PERFORM
    parse_response, # MSG_RESPONSE

    parse_garbagecollect,  # MSG_GARBAGECOLLECT
    parse_status,           # MSG_STATUS
    parse_basic            # MSG_ISSUE
    ]


########NEW FILE########
__FILENAME__ = nameserver
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: The Nameserver keeps track of the view by being involved in Paxos rounds and replies to DNS queries with the latest view.
@copyright: See LICENSE
"""
import socket, select, signal
from time import strftime, gmtime
from concoord.utils import *
from concoord.enums import *
from concoord.pack import *
from concoord.route53 import *
try:
    import dns.exception
    import dns.message
    import dns.rcode
    import dns.opcode
    import dns.rdatatype
    import dns.name
    from dns.flags import *
except:
    print "To use the nameserver install dnspython: http://www.dnspython.org/"

try:
    from boto.route53.connection import Route53Connection
    from boto.route53.exception import DNSServerError
except:
    pass

RRTYPE = ['','A','NS','MD','MF','CNAME','SOA', 'MB', 'MG', 'MR', 'NULL',
          'WKS', 'PTR', 'HINFO', 'MINFO', 'MX', 'TXT', 'RP', 'AFSDB',
          'X25', 'ISDN', 'RT', 'NSAP', 'NSAP_PTR', 'SIG', 'KEY', 'PX',
          'GPOS', 'AAAA', 'LOC', 'NXT', '', '', 'SRV']
RRCLASS = ['','IN','CS','CH','HS']
OPCODES = ['QUERY','IQUERY','STATUS']
RCODES = ['NOERROR','FORMERR','SERVFAIL','NXDOMAIN','NOTIMP','REFUSED']

SRVNAME = '_concoord._tcp.'

class Nameserver():
    """Nameserver keeps track of the connectivity state of the system and replies to
    QUERY messages from dnsserver."""
    def __init__(self, addr, domain, route53, replicas, debug):
        self.ipconverter = '.ipaddr.'+domain+'.'
        try:
            if domain.find('.') > 0:
                self.mydomain = dns.name.Name((domain+'.').split('.'))
            else:
                self.mydomain = domain
            self.mysrvdomain = dns.name.Name((SRVNAME+domain+'.').split('.'))
        except dns.name.EmptyLabel as e:
            print "A DNS name is required. Use -n option."
            raise e

        # Replicas of the Replica
        self.replicas = replicas
        self.debug = debug

        self.route53 = route53
        if self.route53:
            try:
                from boto.route53.connection import Route53Connection
                from boto.route53.exception import DNSServerError
            except Exception as e:
                print "To use Amazon Route 53, install boto: http://github.com/boto/boto/"
                raise e

            # Check if AWS CONFIG data is present
            ROUTE53CONFIGFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'route53.cfg')
            # Touching the CONFIG file
            with open(ROUTE53CONFIGFILE, 'a'):
                os.utime(ROUTE53CONFIGFILE, None)

            import ConfigParser
            config = ConfigParser.RawConfigParser()
            config.read(ROUTE53CONFIGFILE)

            try:
                AWS_ACCESS_KEY_ID = config.get('ENVIRONMENT', 'AWS_ACCESS_KEY_ID')
                AWS_SECRET_ACCESS_KEY = config.get('ENVIRONMENT', 'AWS_SECRET_ACCESS_KEY')
            except Exception as e:
                print "To use Route53 set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as follows:"
                print "$ concoord route53id [AWS_ACCESS_KEY_ID]"
                print "$ concoord route53key [AWS_SECRET_ACCESS_KEY]"
                sys.exit(1)

            # initialize Route 53 connection
            self.route53_name = domain+'.'
            self.route53_conn = Route53Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            # get the zone_id for the domainname, the domainname
            # should be added to the zones beforehand
            self.route53_zone_id = self.get_zone_id(self.route53_conn, self.route53_name)
            self.updateroute53()
        else: # STANDALONE NAMESERVER
            self.addr = addr if addr else findOwnIP()
            self.udpport = 53
            self.udpsocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            try:
                self.udpsocket.bind((self.addr,self.udpport))
                print "Connected to " + self.addr + ":" + str(self.udpport)
            except socket.error as e:
                print "Can't bind to UDP port 53: %s" % str(e)
                raise e

        # When the nameserver starts the revision number is 00 for that day
        self.revision = strftime("%Y%m%d", gmtime())+str(0).zfill(2)

    def add_logger(self, logger):
        self.logger = logger

    def udp_server_loop(self):
        while True:
            try:
                inputready,outputready,exceptready = select.select([self.udpsocket],[],[self.udpsocket])
                for s in exceptready:
                    if self.debug: self.logger.write("DNS Error", s)
                for s in inputready:
                    data,clientaddr = self.udpsocket.recvfrom(UDPMAXLEN)
                    if self.debug: self.logger.write("DNS State", "received a message from address %s" % str(clientaddr))
                    self.handle_query(data,clientaddr)
            except KeyboardInterrupt, EOFError:
                os._exit(0)
            except Exception as e:
                print "Error:", type(e), e.message
                continue
        self.udpsocket.close()
        return

    def aresponse(self, question=''):
        for address in get_addresses(self.replicas):
            yield address

    def nsresponse(self, question=''):
        # Check which Replicas are also Nameservers
        for replica in self.replicas:
            if replica.type == NODE_NAMESERVER:
                yield replica.addr

    def srvresponse(self, question=''):
        for address,port in get_addressportpairs(self.replicas):
            yield address+self.ipconverter,port

    def txtresponse(self, question=''):
        txtstr = ''
        for peer in self.replicas:
            txtstr += node_names[peer.type] +' '+ peer.addr + ':' + str(peer.port) + ';'
        return txtstr[:-1]

    def ismydomainname(self, question):
        return question.name == self.mydomain or (question.rdtype == dns.rdatatype.SRV and question.name == self.mysrvdomain)

    def should_answer(self, question):
        return (question.rdtype == dns.rdatatype.AAAA or \
                    question.rdtype == dns.rdatatype.A or \
                    question.rdtype == dns.rdatatype.TXT or \
                    question.rdtype == dns.rdatatype.NS or \
                    question.rdtype == dns.rdatatype.SRV or \
                    question.rdtype == dns.rdatatype.SOA) and self.ismydomainname(question)

    def handle_query(self, data, addr):
        query = dns.message.from_wire(data)
        response = dns.message.make_response(query)
        for question in query.question:
            if self.debug: self.logger.write("DNS State", "Received Query for %s\n" % question.name)
            if self.debug: self.logger.write("DNS State", "Mydomainname: %s Questionname: %s" % (self.mydomain, str(question.name)))
            if self.should_answer(question):
                if self.debug: self.logger.write("DNS State", "Query for my domain: %s" % str(question))
                flagstr = 'QR AA' # response, authoritative
                answerstr = ''
                if question.rdtype == dns.rdatatype.AAAA:
                    flagstr = 'QR' # response
                elif question.rdtype == dns.rdatatype.A:
                    # A Queries --> List all Replicas starting with the Leader
                    for address in self.aresponse(question):
                        answerstr += self.create_answer_section(question, addr=address)
                elif question.rdtype == dns.rdatatype.TXT:
                    # TXT Queries --> List all nodes
                    answerstr = self.create_answer_section(question, txt=self.txtresponse(question))
                elif question.rdtype == dns.rdatatype.NS:
                    # NS Queries --> List all Nameserver nodes
                    for address in self.nsresponse(question):
                        #answerstr += self.create_answer_section(question, name=address)
                        answerstr += self.create_answer_section(question, addr=address)
                elif question.rdtype == dns.rdatatype.SOA:
                    # SOA Query --> Reply with Metadata
                    answerstr = self.create_soa_answer_section(question)
                elif question.rdtype == dns.rdatatype.SRV:
                    # SRV Queries --> List all Replicas with addr:port
                    for address,port in self.srvresponse(question):
                        answerstr += self.create_srv_answer_section(question, addr=address, port=port)
                responsestr = self.create_response(response.id,opcode=dns.opcode.QUERY,
                                                   rcode=dns.rcode.NOERROR,flags=flagstr,
                                                   question=question.to_text(),answer=answerstr,
                                                   authority='',additional='')
                response = dns.message.from_text(responsestr)
            else:
                if self.debug: self.logger.write("DNS State", "UNSUPPORTED QUERY, %s" %str(question))
                return
        if self.debug: self.logger.write("DNS State", "RESPONSE:\n%s\n---\n" % str(response))

        towire = response.to_wire()
        self.udpsocket.sendto(towire, addr)

    def create_response(self, id, opcode=0, rcode=0, flags='', question='', answer='', authority='', additional=''):
        answerstr     = ';ANSWER\n'     + answer     + '\n' if answer != '' else ''
        authoritystr  = ';AUTHORITY\n'  + authority  + '\n' if authority != '' else ''
        additionalstr = ';ADDITIONAL\n' + additional + '\n' if additional != '' else ''

        responsestr = "id %s\nopcode %s\nrcode %s\nflags %s\n;QUESTION\n%s\n%s%s%s" % (str(id),
                                                                                       OPCODES[opcode],
                                                                                       RCODES[rcode],
                                                                                       flags,
                                                                                       question,
                                                                                       answerstr, authoritystr, additionalstr)
        return responsestr

    def create_srv_answer_section(self, question, ttl=30, rrclass=1, priority=0, weight=100, port=None, addr=''):
        answerstr = "%s %d %s %s %d %d %d %s\n" % (str(question.name), ttl, RRCLASS[rrclass], RRTYPE[question.rdtype], priority, weight, port, addr)
        return answerstr

    def create_mx_answer_section(self, question, ttl=30, rrclass=1, priority=0, addr=''):
        answerstr = "%s %d %s %s %d %s\n" % (str(question.name), ttl, RRCLASS[rrclass], RRTYPE[question.rdtype], priority, addr)
        return answerstr

    def create_soa_answer_section(self, question, ttl=30, rrclass=1):
        refreshrate = 86000 # time (in seconds) when the slave DNS server will refresh from the master
        updateretry = 7200  # time (in seconds) when the slave DNS server should retry contacting a failed master
        expiry = 360000     # time (in seconds) that a slave server will keep a cached zone file as valid
        minimum = 432000    # default time (in seconds) that the slave servers should cache the Zone file
        answerstr = "%s %d %s %s %s %s (%s %d %d %d %d)" % (str(question.name), ttl, RRCLASS[rrclass],
                                                            RRTYPE[question.rdtype],
                                                            str(self.mydomain),
                                                            'dns-admin.'+str(self.mydomain),
                                                            self.revision,
                                                            refreshrate,
                                                            updateretry,
                                                            expiry,
                                                            minimum)
        return answerstr

    def create_answer_section(self, question, ttl=30, rrclass=1, addr='', txt=None):
        if question.rdtype == dns.rdatatype.A:
            resp = str(addr)
        elif question.rdtype == dns.rdatatype.TXT:
            resp = '"%s"' % txt
        elif question.rdtype == dns.rdatatype.NS:
            resp = str(addr)
        answerstr = "%s %s %s %s %s\n" % (str(question.name), str(ttl), str(RRCLASS[rrclass]), str(RRTYPE[question.rdtype]), resp)
        return answerstr

    def create_authority_section(self, question, ttl='30', rrclass=1, rrtype=1, nshost=''):
        authoritystr = "%s %s %s %s %s\n" % (str(question.name), str(ttl), str(RRCLASS[rrclass]), str(RRTYPE[rrtype]), str(nshost))
        return authoritystr

    def create_additional_section(self, question, ttl='30', rrclass=1, rrtype=1, addr=''):
        additionalstr = "%s %s %s %s %s\n" % (str(question.name), str(ttl), str(RRCLASS[rrclass]), str(RRTYPE[rrtype]), str(addr))
        return additionalstr

    def update(self):
        self.updaterevision()
        if self.route53:
            self.updateroute53()

    ########## ROUTE 53 ##########

    def get_zone_id(self, conn, name):
        response = conn.get_all_hosted_zones()
        for zoneinfo in response['ListHostedZonesResponse']['HostedZones']:
            if zoneinfo['Name'] == name:
                return zoneinfo['Id'].split("/")[-1]

    def append_record(self, conn, hosted_zone_id, name, type, newvalues, ttl=600,
                      identifier=None, weight=None, comment=""):
        values = get_values(conn, hosted_zone_id, name, type)
        if values == '':
            values = newvalues
        else:
            values += ',' + newvalues
        change_record(conn, hosted_zone_id, name, type, values, ttl=ttl, identifier=identifier, weight=weight, comment=comment)

    def get_values(self, conn, hosted_zone_id, name, type):
        response = conn.get_all_rrsets(hosted_zone_id, 'A', name)
        for record in response:
            if record.type == type:
                values = ','.join(record.resource_records)
        return values

    def add_record_bool(self, conn, zone_id, name, type, values, ttl=600, identifier=None, weight=None, comment=""):
        # Add Record succeeds only when the type doesn't exist yet
        try:
            add_record(conn, zone_id, name, type, values, ttl=ttl, identifier=identifier, weight=weight, comment=comment)
        except DNSServerError as e:
            return False
        return True

    def change_record_bool(self, conn, zone_id, name, type, values, ttl=600, identifier=None, weight=None, comment=""):
        try:
            change_record(conn, zone_id, name, type, values, ttl=ttl, identifier=identifier, weight=weight, comment=comment)
        except DNSServerError as e:
            print e
            return False
        return True

    def append_record_bool(self, conn, zone_id, name, type, values, ttl=600, identifier=None, weight=None, comment=""):
        try:
            append_record(conn, zone_id, name, type, values, ttl=ttl, identifier=identifier, weight=weight, comment=comment)
        except DNSServerError as e:
            print e
            return False
        return True

    def del_record_bool(self, conn, zone_id, name, type, values, ttl=600, identifier=None, weight=None, comment=""):
        try:
            del_record(conn, zone_id, name, type, values, ttl=ttl, identifier=identifier, weight=weight, comment=comment)
        except DNSServerError as e:
            print e

    def route53_a(self):
        values = []
        for address in get_addresses(self.replicas):
            values.append(address)
        return ','.join(values)

    def route53_srv(self):
        values = []
        priority = 0
        weight = 100
        for address,port in get_addressportpairs(self.replicas):
            values.append('%d %d %d %s' % (priority, weight, port, address+self.ipconverter))
        return ','.join(values)

    def route53_txt(self):
        txtstr = self.txtresponse()
        lentxtstr = len(txtstr)
        strings = ["\""+txtstr[0:253]+"\""]
        if lentxtstr > 253:
            # cut the string in chunks
            for i in range(lentxtstr/253):
                strings.append("\""+txtstr[i*253:(i+1)*253]+"\"")
        return strings

    def updateroute53(self):
        # type A: update only if added node is a Replica
        rtype = 'A'
        newvalue = self.route53_a()
        self.change_record_bool(self.route53_conn, self.route53_zone_id,
                           self.route53_name, 'A', newvalue)
        # type SRV: update only if added node is a Replica
        rtype = 'SRV'
        newvalue = self.route53_srv()
        self.change_record_bool(self.route53_conn, self.route53_zone_id,
                           self.route53_name, 'SRV', newvalue)
        # type TXT: All Nodes
        rtype = 'TXT'
        newvalue = ','.join(self.route53_txt())
        self.change_record_bool(self.route53_conn, self.route53_zone_id,
                           self.route53_name, 'TXT', newvalue)

    def updaterevision(self):
        if self.debug: self.logger.write("State", "Updating Revision -- from: %s" % self.revision)
        if strftime("%Y%m%d", gmtime()) in self.revision:
            rno = int(self.revision[-2]+self.revision[-1])
            rno += 1
            self.revision = strftime("%Y%m%d", gmtime())+str(rno).zfill(2)
        else:
            self.revision = strftime("%Y%m%d", gmtime())+str(0).zfill(2)
        if self.debug: self.logger.write("State", "Updating Revision -- to: %s" % self.revision)

########NEW FILE########
__FILENAME__ = node
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Master class for all nodes
@copyright: See LICENSE
'''
import argparse
import os, sys
import random, struct
import cPickle as pickle
import time, socket, select
from Queue import Queue
from threading import Thread, RLock, Lock, Condition, Timer, Semaphore
from concoord.enums import *
from concoord.nameserver import Nameserver
from concoord.exception import ConnectionError
from concoord.utils import *
from concoord.message import *
from concoord.pack import *
from concoord.pvalue import PValueSet
from concoord.connection import ConnectionPool, Connection, SelfConnection

try:
    import dns.resolver, dns.exception
except:
    print("Install dnspython: http://www.dnspython.org/")

parser = argparse.ArgumentParser()

parser.add_argument("-a", "--addr", action="store", dest="addr",
                    help="address for the node")
parser.add_argument("-p", "--port", action="store", dest="port", type=int,
                    help="port for the node")
parser.add_argument("-b", "--boot", action="store", dest="bootstrap",
                    help="address:port tuple for the bootstrap peer")
parser.add_argument("-o", "--objectname", action="store", dest="objectname", default='',
                    help="client object dotted name")
parser.add_argument("-l", "--logger", action="store", dest="logger", default='',
                    help="logger address")
parser.add_argument("-n", "--domainname", action="store", dest="domain", default='',
                    help="domain name that the nameserver will accept queries for")
parser.add_argument("-r", "--route53", action="store_true", dest="route53", default=False,
                    help="use Route53 (requires a Route53 zone)")
parser.add_argument("-w", "--writetodisk", action="store_true", dest="writetodisk", default=False,
                    help="writing to disk on/off")
parser.add_argument("-d", "--debug", action="store_true", dest="debug", default=False,
                    help="debug on/off")
args = parser.parse_args()

class Node():
    """Node encloses the basic Node behaviour and state that
    are extended by Replicas and Nameservers.
    """
    def __init__(self,
                 addr=args.addr,
                 port=args.port,
                 givenbootstraplist=args.bootstrap,
                 debugoption=args.debug,
                 objectname=args.objectname,
                 logger=args.logger,
                 writetodisk=args.writetodisk):
        self.addr = addr if addr else findOwnIP()
        self.port = port
        self.debug = debugoption
        self.durable = writetodisk
        self.isnameserver = args.domain != ''
        self.domain = args.domain
        self.useroute53 = args.route53
        if objectname == '':
            parser.print_help()
            self._graceexit(1)
        self.objectname = objectname
        # initialize receive queue
        self.receivedmessages_semaphore = Semaphore(0)
        self.receivedmessages = []
        # lock to synchronize message handling
        self.lock = Lock()

        # create server socket and bind to a port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.setblocking(0)
        if self.port:
            try:
                self.socket.bind((self.addr,self.port))
            except socket.error as e:
                print "Cannot bind to port %d" % self.port
                print "Socket Error: ", e
                self._graceexit(1)
        else:
            for i in range(50):
                self.port = random.randint(14000,15000)
                try:
                    self.socket.bind((self.addr,self.port))
                    break
                except socket.error as e:
                    print "Socket Error: ", e
        self.socket.listen(10)
        self.connectionpool = ConnectionPool()

        try:
            self.connectionpool.epoll = select.epoll()
        except AttributeError as e:
            # the os doesn't support epoll
            self.connectionpool.epoll = None

        # set the logger
        if logger:
            LOGGERNODE = logger
        else:
            LOGGERNODE = None

        # Initialize replicas
        # Keeps {peer:outofreachcount}
        self.replicas = {}
        # Nameserver state
        if self.isnameserver:
            self.type = NODE_NAMESERVER
            try:
                self.nameserver = Nameserver(self.addr, self.domain, self.useroute53,
                                             self.replicas, self.debug)
            except Exception as e:
                print "Error:", e
                print "Could not start Replica as a Nameserver, exiting."
                self._graceexit(1)
        else:
            self.type = NODE_REPLICA

        self.alive = True
        self.me = Peer(self.addr,self.port,self.type)
        # set id
        self.id = '%s:%d' % (self.addr, self.port)
        # add self to connectionpool
        self.connectionpool.add_connection_to_self(self.me,
                                                   SelfConnection(self.receivedmessages,
                                                                  self.receivedmessages_semaphore))
        self.logger = Logger("%s-%s" % (node_names[self.type],self.id), lognode=LOGGERNODE)
        if self.isnameserver:
            self.nameserver.add_logger(self.logger)
        print "%s-%s connected." % (node_names[self.type],self.id)

        # Keeps the liveness of the nodes
        self.nodeliveness = {}
        self.bootstrapset = set()
        # connect to the bootstrap node
        if givenbootstraplist:
            self.discoverbootstrap(givenbootstraplist)
            self.connecttobootstrap()

        self.stateuptodate = False

    def _getipportpairs(self, bootaddr, bootport):
        for node in socket.getaddrinfo(bootaddr, bootport, socket.AF_INET, socket.SOCK_STREAM):
            yield Peer(node[4][0],bootport,NODE_REPLICA)

    def discoverbootstrap(self, givenbootstraplist):
        bootstrapstrlist = givenbootstraplist.split(",")
        for bootstrap in bootstrapstrlist:
            #ipaddr:port pair given as bootstrap
            if bootstrap.find(":") >= 0:
                bootaddr,bootport = bootstrap.split(":")
                for peer in self._getipportpairs(bootaddr, int(bootport)):
                    self.bootstrapset.add(peer)
            #dnsname given as bootstrap
            else:
                answers = []
                try:
                    answers = dns.resolver.query('_concoord._tcp.'+bootstrap, 'SRV')
                except (dns.resolver.NXDOMAIN, dns.exception.Timeout):
                    if self.debug: self.logger.write("DNS Error", "Cannot resolve %s" % str(bootstrap))
                for rdata in answers:
                    for peer in self._getipportpairs(str(rdata.target), rdata.port):
                        self.bootstrapset.append(peer)

    def connecttobootstrap(self):
        tries = 0
        keeptrying = True
        while tries < BOOTSTRAPCONNECTTIMEOUT and keeptrying:
            for bootpeer in self.bootstrapset:
                try:
                    if self.debug: self.logger.write("State",
                                                     "trying to connect to bootstrap: %s" % str(bootpeer))
                    helomessage = create_message(MSG_HELO, self.me)
                    successid = self.send(helomessage, peer=bootpeer)
                    if successid < 0:
                        tries += 1
                        continue
                    keeptrying = False
                    break
                except socket.error as e:
                    if self.debug: self.logger.write("Socket Error",
                                                     "cannot connect to bootstrap: %s" % str(e))
                    tries += 1
                    continue
            time.sleep(1)

    def startservice(self):
        # Start a thread that waits for inputs
        receiver_thread = Thread(target=self.server_loop, name='ReceiverThread')
        receiver_thread.start()
        # Start a thread with the server which will start a thread for each request
        main_thread = Thread(target=self.handle_messages, name='MainThread')
        main_thread.start()
        # Start a thread that pings all neighbors
        ping_thread = Timer(LIVENESSTIMEOUT, self.ping_neighbor)
        ping_thread.name = 'PingThread'
        ping_thread.start()
        # Start a thread that goes through the nascentset and cleans expired ones
        nascent_thread = Timer(NASCENTTIMEOUT, self.clean_nascent)
        nascent_thread.name = 'NascentThread'
        nascent_thread.start()
        # Start a thread that waits for inputs
        if self.debug:
            input_thread = Thread(target=self.get_user_input_from_shell, name='InputThread')
            input_thread.start()
        return self

    def __str__(self):
        return "%s NODE %s:%d" % (node_names[self.type], self.addr, self.port)

    def statestr(self):
        returnstr = ""
        for peer in self.replicas:
            returnstr += node_names[peer.type] + " %s:%d\n" % (peer.addr,peer.port)
        if hasattr(self, 'pendingcommands') and len(self.pendingcommands) > 0:
            pending =  "".join("%d: %s" % (cno, proposal) for cno,proposal \
                                   in self.pendingcommands.iteritems())
            returnstr = "%s\nPending:\n%s" % (returnstr, pending)
        return returnstr

    def ping_neighbor(self):
        """used to ping neighbors periodically"""
        # Only ping neighbors that didn't send a message recently
        while True:
            # Check nodeliveness
            for peer in self.replicas:
                if peer == self.me:
                    continue
                if peer in self.nodeliveness:
                    nosound = time.time() - self.nodeliveness[peer]
                else:
                    nosound = LIVENESSTIMEOUT + 1

                if nosound <= LIVENESSTIMEOUT:
                    # Peer is alive
                    self.replicas[peer] = 0
                    continue
                if nosound > LIVENESSTIMEOUT:
                    # Send PING to node
                    if self.debug: self.logger.write("State", "Sending PING to %s" % str(peer))
                    pingmessage = create_message(MSG_PING, self.me)
                    successid = self.send(pingmessage, peer=peer)
                if successid < 0 or nosound > (2*LIVENESSTIMEOUT):
                    # Neighbor not responding, mark the neighbor
                    if self.debug: self.logger.write("State",
                                                     "Neighbor not responding")
                    self.replicas[peer] += 1
            time.sleep(LIVENESSTIMEOUT)

    def clean_nascent(self):
        lastnascentset = set([])
        while True:
            for sock in lastnascentset.intersection(self.connectionpool.nascentsockets):
                # expired -- if it's not already in the set, it should be deleted
                self.connectionpool.activesockets.remove(sock)
                self.connectionpool.nascentsockets.remove(sock)
                lastnascentset = self.connectionpool.nascentsockets
            time.sleep(NASCENTTIMEOUT)

    def server_loop(self):
        """Serverloop that listens to multiple connections and accepts new ones.

        Server State
        - inputready: sockets that are ready for reading
        - exceptready: sockets that are ready according to an *exceptional condition*
        """
        self.socket.listen(10)

        if self.connectionpool.epoll:
            self.connectionpool.epoll.register(self.socket.fileno(), select.EPOLLIN)
            self.use_epoll()
        else:
            # the OS doesn't support epoll
            self.connectionpool.activesockets.add(self.socket)
            self.use_select()

        self.socket.close()
        return

    def use_epoll(self):
        while self.alive:
            try:
                events = self.connectionpool.epoll.poll(1)
                for fileno, event in events:
                    if fileno == self.socket.fileno():
                        clientsock, clientaddr = self.socket.accept()
                        clientsock.setblocking(0)
                        self.connectionpool.epoll.register(clientsock.fileno(), select.EPOLLIN)
                        self.connectionpool.epollsockets[clientsock.fileno()] = clientsock
                    elif event & select.EPOLLIN:
                        success = self.handle_connection(self.connectionpool.epollsockets[fileno])
                        if not success:
                            self.connectionpool.epoll.unregister(fileno)
                            self.connectionpool.del_connection_by_socket(self.connectionpool.epollsockets[fileno])
                            self.connectionpool.epollsockets[fileno].close()
                            del self.connectionpool.epollsockets[fileno]
                    elif event & select.EPOLLHUP:
                        self.connectionpool.epoll.unregister(fileno)
                        self.connectionpool.epollsockets[fileno].close()
                        del self.connectionpool.epollsockets[fileno]
            except KeyboardInterrupt, EOFError:
                os._exit(0)
        self.connectionpool.epoll.unregister(self.socket.fileno())
        self.connectionpool.epoll.close()

    def use_select(self):
        while self.alive:
            try:
                inputready,outputready,exceptready = select.select(self.connectionpool.activesockets,
                                                                   [],
                                                                   self.connectionpool.activesockets,
                                                                   1)

                for s in exceptready:
                    if self.debug: self.logger.write("Exception", "%s" % s)
                for s in inputready:
                    if s == self.socket:
                        clientsock,clientaddr = self.socket.accept()
                        if self.debug: self.logger.write("State",
                                                         "accepted a connection from address %s"
                                                         % str(clientaddr))
                        self.connectionpool.activesockets.add(clientsock)
                        self.connectionpool.nascentsockets.add(clientsock)
                        success = True
                    else:
                        success = self.handle_connection(s)
                    if not success:
                        self.connectionpool.del_connection_by_socket(s)
            except KeyboardInterrupt, EOFError:
                os._exit(0)

    def handle_connection(self, clientsock):
        """Receives a message and calls the corresponding message handler"""
        connection = self.connectionpool.get_connection_by_socket(clientsock)
        try:
            for message in connection.received_bytes():
                if self.debug: self.logger.write("State", "received %s" % str(message))
                if message.type == MSG_STATUS:
                        if self.debug: self.logger.write("State",
                                                         "Answering status message %s"
                                                         % self.__str__())
                        messagestr = pickle.dumps(self.__str__())
                        message = struct.pack("I", len(messagestr)) + messagestr
                        clientsock.send(message)
                        return False
                # Update nodeliveness
                if message.source.type != NODE_CLIENT:
                    self.nodeliveness[message.source] = time.time()
                    if message.source in self.replicas:
                        self.replicas[message.source] = 0

                # add to receivedmessages
                self.receivedmessages.append((message,connection))
                self.receivedmessages_semaphore.release()
                if message.type == MSG_CLIENTREQUEST or message.type == MSG_INCCLIENTREQUEST:
                    self.connectionpool.add_connection_to_peer(message.source, connection)
                elif message.type in (MSG_HELO, MSG_HELOREPLY, MSG_UPDATE):
                    self.connectionpool.add_connection_to_peer(message.source, connection)
            return True
        except ConnectionError as e:
            return False

    def handle_messages(self):
        while True:
            self.receivedmessages_semaphore.acquire()
            (message_to_process,connection) = self.receivedmessages.pop(0)
            if message_to_process.type == MSG_CLIENTREQUEST:
                if message_to_process.clientbatch:
                    self.process_message(message_to_process, connection)
                    continue
                # check if there are other client requests waiting
                msgconns = [(message_to_process,connection)]
                for m,c in self.receivedmessages:
                    if m.type == MSG_CLIENTREQUEST:
                        # decrement the semaphore count
                        self.receivedmessages_semaphore.acquire()
                        # remove the m,c pair from receivedmessages
                        self.receivedmessages.remove((m,c))
                        msgconns.append((m,c))
                if len(msgconns) > 1:
                    self.process_messagelist(msgconns)
                else:
                    self.process_message(message_to_process, connection)
            else:
                self.process_message(message_to_process, connection)
        return

    def process_messagelist(self, msgconnlist):
        """Processes given message connection pairs"""
        with self.lock:
            self.msg_clientrequest_batch(msgconnlist)
        return True

    def process_message(self, message, connection):
        """Processes given message connection pair"""
        # find method and invoke it holding a lock
        mname = "msg_%s" % msg_names[message.type].lower()
        try:
            method = getattr(self, mname)
            if self.debug: self.logger.write("State", "invoking method: %s" % mname)
        except AttributeError:
            if self.debug: self.logger.write("Method Error", "method not supported: %s" % mname)
            return False
        with self.lock:
            method(connection, message)
        return True

    # message handlers
    def msg_helo(self, conn, msg):
        return

    def msg_heloreply(self, conn, msg):
        if msg.leader:
            if msg.leader == self.me:
                if self.debug: self.logger.write("State", "I'm the leader.")
                return
            else:
                if self.debug: self.logger.write("State", "Adding new bootstrap.")
                if msg.source in self.bootstrapset:
                    self.bootstrapset.remove(msg.source)
                self.bootstrapset.add(msg.leader)
                self.connecttobootstrap()

    def msg_ping(self, conn, msg):
        if self.debug: self.logger.write("State", "Replying to PING.")
        pingreplymessage = create_message(MSG_PINGREPLY, self.me)
        conn.send(pingreplymessage)

    def msg_pingreply(self, conn, msg):
        return

    # shell commands generic to all nodes
    def cmd_help(self, args):
        """prints the commands that are supported
        by the corresponding Node."""
        print "Commands supported:"
        for attr in dir(self):
            if attr.startswith("cmd_"):
                print attr.replace("cmd_", "")

    def cmd_exit(self, args):
        """Changes the liveness state and dies"""
        self.alive = False
        os._exit(0)

    def cmd_state(self, args):
        """prints connectivity state of the corresponding Node."""
        print "\n%s\n" % (self.statestr())

    def get_user_input_from_shell(self):
        """Shell loop that accepts inputs from the command prompt and
        calls corresponding command handlers."""
        while self.alive:
            try:
                input = raw_input(">")
                if len(input) == 0:
                    continue
                else:
                    input = input.split()
                    mname = "cmd_%s" % input[0].lower()
                    try:
                        method = getattr(self, mname)
                    except AttributeError as e:
                        print "Command not supported: ", str(e)
                        continue
                    with self.lock:
                        method(input)
            except KeyboardInterrupt:
                os._exit(0)
            except EOFError:
                return
        return

    def send(self, message, peer=None, group=None):
        if peer:
            connection = self.connectionpool.get_connection_by_peer(peer)
            if connection == None:
                if self.debug: self.logger.write("Connection Error",
                                                 "Connection for %s cannot be found." % str(peer))
                return -1
            connection.send(message)
            return message[FLD_ID]
        elif group:
            ids = []
            for peer,liveness in group.iteritems():
                connection = self.connectionpool.get_connection_by_peer(peer)
                if connection == None:
                    if self.debug: self.logger.write("Connection Error",
                                                     "Connection for %s cannot be found." % str(peer))
                    continue
                connection.send(message)
                ids.append(message[FLD_ID])
                message[FLD_ID] = assignuniqueid()
            return ids

    def terminate_handler(self, signal, frame):
        if self.debug: self.logger.write("State", "exiting...")
        self.logger.close()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

    def _graceexit(self, exitcode=0):
        sys.stdout.flush()
        sys.stderr.flush()
        if hasattr(self, 'logger'): self.logger.close()
        os._exit(exitcode)

########NEW FILE########
__FILENAME__ = bank
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example bank object that keeps track of accounts
@copyright: See LICENSE
"""
class Bank():
    def __init__(self):
        self.accounts = {}

    def open(self, accntno):
        if self.accounts.has_key(accntno):
            return False
        else:
            self.accounts[accntno] = Account(accntno)
            return True

    def close(self, accntno):
        if self.accounts.has_key(accntno):
            del self.accounts[accntno]
            return True
        else:
            raise KeyError

    def debit(self, accntno, amount):
        if self.accounts.has_key(accntno):
            return self.accounts[accntno].debit(amount)
        else:
            raise KeyError

    def deposit(self, accntno, amount):
        if self.accounts.has_key(accntno):
            return self.accounts[accntno].deposit(amount)
        else:
            raise KeyError

    def balance(self, accntno):
        if self.accounts.has_key(accntno):
            return self.accounts[accntno].balance
        else:
            raise KeyError

    def __str__(self):
        return "\n".join(["%s" % (str(account)) for account in self.accounts.values()])

class Account():
    def __init__(self, number):
        self.number = number
        self.balance = 0

    def __str__(self):
        return "Account %s: balance = $%.2f" % (self.number, self.balance)

    def debit(self, amount):
        amount = float(amount)
        if amount >= self.balance:
            self.balance = self.balance - amount
            return self.balance
        else:
            return False

    def deposit(self, amount):
        amount = float(amount)
        self.balance = self.balance + amount
        return self.balance

########NEW FILE########
__FILENAME__ = barrier
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example barrier object
@copyright: See LICENSE
"""
from threading import Lock
from concoord.threadingobject.dcondition import DCondition

class Barrier():
    def __init__(self, count=1):
        self.count = int(count)
        self.current = 0
        self.condition = DCondition()

    def wait(self, _concoord_command):
        self.condition.acquire(_concoord_command)
        self.current += 1
        if self.current != self.count:
            self.condition.wait(_concoord_command)
        else:
            self.current = 0
            self.condition.notifyAll(_concoord_command)
        self.condition.release(_concoord_command)

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)





########NEW FILE########
__FILENAME__ = binarytree
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example binarytree
@copyright: See LICENSE
"""
class BinaryTree:
    def __init__(self):
        self.root = None

    def add_node(self, data):
        return Node(data)

    def insert(self, root, data):
        if root == None:
            return self.add_node(data)
        else:
            if data <= root.data:
                root.left = self.insert(root.left, data)
            else:
                root.right = self.insert(root.right, data)
            return root

    def find(self, root, target):
        if root == None:
            return False
        else:
            if target == root.data:
                return True
            else:
                if target < root.data:
                    return self.find(root.left, target)
                else:
                    return self.find(root.right, target)

    def delete(self, root, target):
        if root == None or not self.find(root, target):
            return False
        else:
            if target == root.data:
                del root
            else:
                if target < root.data:
                    return self.delete(root.left, target)
                else:
                    return self.delete(root.right, target)

    def get_min(self, root):
        while(root.left != None):
            root = root.left
        return root.data

    def get_max(self, root):
        while(root.right != None):
            root = root.right
        return root.data

    def get_depth(self, root):
        if root == None:
            return 0
        else:
            ldepth = self.get_depth(root.left)
            rdepth = self.get_depth(root.right)
            return max(ldepth, rdepth) + 1

    def get_size(self, root):
        if root == None:
            return 0
        else:
            return self.get_size(root.left) + 1 + self.get_size(root.right)

class Node:
    def __init__(self, data):
        self.left = None
        self.right = None
        self.data = data





########NEW FILE########
__FILENAME__ = boundedsemaphore
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example boundedsemaphore object
@copyright: See LICENSE
"""
from concoord.threadingobject.dboundedsemaphore import DBoundedSemaphore

class BoundedSemaphore():
    """Semaphore object that supports following functions:
    - acquire: locks the object
    - release: unlocks the object
    """
    def __init__(self, count=1):
        self.semaphore = DBoundedSemaphore(count)

    def __repr__(self):
        return repr(self.semaphore)

    def acquire(self, _concoord_command):
        try:
            return self.semaphore.acquire(_concoord_command)
        except Exception as e:
            raise e

    def release(self, _concoord_command):
        try:
            return self.semaphore.release(_concoord_command)
        except Exception as e:
            raise e

    def __str__(self):
        return str(self.semaphore)

########NEW FILE########
__FILENAME__ = condition
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example condition
@copyright: See LICENSE
"""
from concoord.threadingobject.dcondition import DCondition

class Condition():
    def __init__(self, lock=None):
        self.condition = DCondition()

    def __repr__(self):
        return repr(self.condition)

    def acquire(self, _concoord_command):
        try:
            self.condition.acquire(_concoord_command)
        except Exception as e:
            raise e

    def release(self, _concoord_command):
        try:
            self.condition.release(_concoord_command)
        except Exception as e:
            raise e

    def wait(self, _concoord_command):
        try:
            self.condition.wait(_concoord_command)
        except Exception as e:
            raise e

    def notify(self, _concoord_command):
        try:
            self.condition.notify(_concoord_command)
        except Exception as e:
            raise e

    def notifyAll(self, _concoord_command):
        try:
            self.condition.notifyAll(_concoord_command)
        except Exception as e:
            raise e

    def __str__(self):
        return str(self.condition)

########NEW FILE########
__FILENAME__ = counter
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example counter
@copyright: See LICENSE
"""
class Counter:
    def __init__(self, value=0):
        self.value = value

    def decrement(self):
        self.value -= 1

    def increment(self):
        self.value += 1

    def getvalue(self):
        return self.value

    def __str__(self):
        return "The counter value is %d" % self.value

########NEW FILE########
__FILENAME__ = jobmanager
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example jobmanager
@copyright: See LICENSE
"""
class JobManager():
    def __init__(self):
        self.jobs = []

    def schedule(self, job):
        self.jobs.append(job)

    def deschedule(self, job):
        self.jobs.remove(job)

    def update(self, job, key, value):
        self.jobe[job].setattr(value)

    def list_jobs(self):
        return self.jobs

    def __str__(self):
        return " ".join([str(j) for j in self.jobs])

class Job():
    def __init__(self, jobname, jobid, jobtime):
        self.name = jobname
        self.id = jobid
        self.time = jobtime

    def __str__(self):
        return "Job %s: %s @ %s" % (str(job.id), str(job.name), str(job.time))





########NEW FILE########
__FILENAME__ = lock
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example lock
@copyright: See LICENSE
"""
from concoord.threadingobject.dlock import DLock

class Lock():
    """Lock object that supports following functions:
    - acquire: locks the object
    - release: unlocks the object
    """
    def __init__(self):
        self.lock = DLock()

    def __repr__(self):
        return repr(self.lock)

    def acquire(self, _concoord_command):
        try:
            return self.lock.acquire(_concoord_command)
        except Exception as e:
            raise e

    def release(self, _concoord_command):
        try:
            self.lock.release(_concoord_command)
        except Exception as e:
            raise e

    def __str__(self):
        return str(self.lock)

########NEW FILE########
__FILENAME__ = log
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example log
@copyright: See LICENSE
"""
class Log():
    def __init__(self):
        self.log = []

    def write(self, entry):
        self.log = []
        self.log.append(entry)

    def append(self, entry):
        self.log.append(entry)

    def read(self):
        return self.__str__()

    def __str__(self):
        return " ".join([str(e) for e in self.log])






########NEW FILE########
__FILENAME__ = membership
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example membership object
@copyright: See LICENSE
"""
class Membership():
    def __init__(self):
        self.members = set()

    def add(self, member):
        if member not in self.members:
            self.members.add(member)

    def remove(self, member):
        if member in self.members:
            self.members.remove(member)
        else:
            raise KeyError(member)

    def __str__(self):
        return " ".join([str(m) for m in self.members])

########NEW FILE########
__FILENAME__ = meshmembership
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Membership object to coordinate a complete mesh
@copyright: See LICENSE
"""
from threading import RLock
from concoord.exception import *
from concoord.threadingobject.drlock import DRLock

class MeshMembership():
    def __init__(self):
        self.groups = {}

    def get_group_members(self, gname):
        if gname in self.groups:
            return self.groups[gname].get_members().keys()
        else:
            raise KeyError(gname)

    def get_group_epoch(self, gname):
        if gname in self.groups:
            return self.groups[gname].get_epoch()
        else:
            raise KeyError(gname)

    def get_group_state(self, gname):
        if gname in self.groups:
            return (self.groups[gname].get_members().keys(), self.groups[gname].get_epoch())
        else:
            raise KeyError(gname)

    def add_group(self, gname, minsize):
        if gname not in self.groups:
            self.groups[gname] = Group(minsize)

    def remove_group(self, gname):
        if gname in self.groups:
            del self.groups[gname]
        else:
            raise KeyError(gname)

    def approve_join(self, gname, node, epochno):
        if gname in self.groups:
            group = self.groups[gname]
            # Check if the epoch the node wants to be
            # added to is still the current epoch.
            success = False
            if group.get_epoch() == epochno:
                # Update the epoch and members
                group.inc_epoch()
                group.add_member(node)
                # Let other members know
                group.notifyAll()
                success = True
            return (success, group.get_epoch())
        else:
            raise KeyError(gname)

    def wait(self, gname):
        if gname in self.groups:
            return self.groups[gname].wait(_concoord_command)
        else:
            raise KeyError(gname)

    def check_member(self, gname, node):
        # returns True or False and the epoch number
        if gname in self.groups:
            return (node in self.groups[gname].get_members(), self.groups[gname].get_epoch())
        else:
            raise KeyError(gname)

    def notify_failure(self, gname, epoch, failednode):
        if gname in self.groups:
            # there is a failure in the group or at least
            # one node thinks so. take a record of it
            if self.groups[gname].get_epoch() != epoch:
                return (self.groups[gname].get_members(), self.groups[gname].get_epoch())
            self.groups[gname].get_members()[failednode] += 1
            if self.groups[gname].get_members()[failednode] >= len(self.groups[gname].get_members())/2.0:
                # more than half of the nodes think that a node has failed
                # we'll change the view
                self.groups[gname].remove_member(node)
                self.groups[gname].inc_epoch()
                # notify nodes that are waiting
                self.groups[gname].notifyAll()
                return (self.groups[gname].get_members(), self.groups[gname].get_epoch())
        else:
            raise KeyError(gname)

    def __str__(self):
        return "\n".join([str(n)+': '+str(s) for n,s in self.groups.iteritems()])

class Group():
    def __init__(self, minsize):
        # Coordination
        self._epoch = 1
        self._minsize = int(minsize)
        self._members = {} # Keeps nodename:strikecount

        # Note: This is not a normal Condition object, it doesn't have
        # a lock and it doesn't provide synchronization.
        self.__waiters = [] # This will always include self.members.keys() wait commands
        self.__atomic = RLock()

    def wait(self, _concoord_command):
        # put the caller on waitinglist and take the lock away
        with self.__atomic:
            self.__waiters.append(_concoord_command)
            raise BlockingReturn()

    # This function is used only by the Coordination Object
    def notifyAll(self):
        # Notify every client on the wait list
        with self.__atomic:
            if not self.__waiters:
                return
            unblocked = {}
            for waitcommand in self.__waiters:
                # notified client should be added to the lock queue
                unblocked[waitcommand] = True
            self.__waiters = []
            raise UnblockingReturn(unblockeddict=unblocked)

    def add_member(self, member):
        if member not in self._members:
            self._members[member] = 0
            return True
        else:
            return False

    def remove_member(self, member):
        if member in self._members:
            del self._members[member]
        else:
            raise KeyError(member)

    def get_size(self):
        return self._minsize

    def get_epoch(self):
        return self._epoch

    def get_members(self):
        return self._members

    def inc_epoch(self):
        self._epoch += 1

    def __str__(self):
        t = "Epoch: %d " % self._epoch
        t += "Minimum Size: %d " % self._minsize
        t += "Members: "
        t += " ".join([str(m) for m in self._members.keys()])
        return t

########NEW FILE########
__FILENAME__ = nameservercoord
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Nameserver coordination object that keeps subdomains and their corresponding nameservers
@copyright: See LICENSE
'''
from itertools import izip

def pairwise(iterable):
    a = iter(iterable)
    return izip(a, a)

class NameserverCoord():
    def __init__(self):
        self._nodes = {}

    def addnodetosubdomain(self, subdomain, nodetype, node):
        nodetype = int(nodetype)
        if subdomain.find('openreplica') == -1:
            subdomain = subdomain+'.openreplica.org.'
        if subdomain in self._nodes:
            if nodetype in self._nodes[subdomain]:
                self._nodes[subdomain][nodetype].add(node)
            else:
                self._nodes[subdomain][nodetype] = set()
                self._nodes[subdomain][nodetype].add(node)
        else:
            self._nodes[subdomain] = {}
            self._nodes[subdomain][nodetype] = set()
            self._nodes[subdomain][nodetype].add(node)

    def delsubdomain(self, subdomain):
        if subdomain.find('openreplica') == -1:
            subdomain = subdomain+'.openreplica.org.'
        exists = subdomain in self._nodes
        if exists:
            del self._nodes[subdomain]
        return exists

    def delnodefromsubdomain(self, subdomain, nodetype, node):
        if subdomain.find('openreplica') == -1:
            subdomain = subdomain+'.openreplica.org.'
        nodetype = int(nodetype)
        exists = subdomain in self._nodes and nodetype in self._nodes[subdomain] and node in self._nodes[subdomain][nodetype]
        if exists:
            self._nodes[subdomain][nodetype].remove(node)
        return exists

    def updatesubdomain(self, subdomain, nodes):
        if subdomain.find('openreplica') == -1:
            subdomain = subdomain+'.openreplica.org.'
        if subdomain in self._nodes.keys():
            self._nodes[subdomain] = nodes
        else:
            self._nodes[subdomain] = set()
            self._nodes[subdomain] = nodes

    def getnodes(self, subdomain):
        if subdomain.find('openreplica') == -1:
            subdomain = subdomain+'.openreplica.org.'
        return self._nodes[subdomain]

    def getsubdomains(self):
        subdomains = []
        for domain in self._nodes.keys():
            subdomains.append(domain.split('.')[0])
        return subdomains

    def getdomains(self):
        return self._nodes.keys()

    def _reinstantiate(self, state):
        self._nodes = {}
        for subdomain,nodes in pairwise(state.split(';')):
            self._nodes[subdomain] = {}
            nodestypes = nodes.strip("()").split('--')
            for typeofnode in nodestypes:
                if typeofnode:
                    typename = int(typeofnode.split('-')[0])
                    self._nodes[subdomain][typename] = set()
                    nodelist = typeofnode.split('-')[1]
                    for nodename in nodelist.split():
                        self._nodes[subdomain][typename].add(nodename)

    def __str__(self):
        rstr = ''
        for domain,nodes in self._nodes.iteritems():
            if domain.find('openreplica') == -1:
                continue
            rstr += domain + ';('
            for nodetype, nodes in nodes.iteritems():
                if len(nodes) > 0:
                    rstr += str(nodetype) + '-' + ' '.join(nodes) + "--"
            rstr += ');'
        return rstr

########NEW FILE########
__FILENAME__ = pinger
import socket, time
from threading import RLock, Thread
from concoord.exception import *
from concoord.threadingobject.dcondition import DCondition

MSG_PING = 8
PING_DELAY = 10

class Pinger():
    def __init__(self):
        self.members = set()
        self.membership_condition = DCondition()

        self.liveness = {}

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        myaddr = socket.gethostbyname(socket.gethostname())
        myport = self.socket.getsockname()[1]
        self.me = "%s:%d", (myaddr,myport)

        comm_thread = Thread(target=self.ping_members, name='PingThread')
        comm_thread.start()

    def add(self, member):
        if member not in self.members:
            self.members.add(member)
            self.liveness[member] = 0
        # Notify nodes of membership change
        self.membership_condition.notifyAll()

    def remove(self, member):
        if member in self.members:
            self.members.remove(member)
            del self.liveness[member]
        else:
            raise KeyError(member)
        # Notify nodes of membership change
        self.membership_condition.notifyAll()

    def get_members(self):
        return self.members

    def ping_members(self):
        while True:
            for member in self.members:
                print "Sending PING to %s" % str(member)
                pingmessage = PingMessage(self.me)
                success = self.send(pingmessage, peer=peer)
                if success < 0:
                    print "Node not responding, marking."
                    self.liveness[member] += 1

            time.sleep(PING_DELAY)

    def send(self, msg):
        messagestr = pickle.dumps(msg)
        message = struct.pack("I", len(messagestr)) + messagestr
        try:
            while len(message) > 0:
                try:
                    bytesent = self.thesocket.send(message)
                    message = message[bytesent:]
                except IOError, e:
                    if isinstance(e.args, tuple):
                        if e[0] == errno.EAGAIN:
                            continue
                        else:
                            raise e
                except AttributeError, e:
                    raise e
            return True
        except socket.error, e:
            if isinstance(e.args, tuple):
                if e[0] == errno.EPIPE:
                    print "Remote disconnect"
                    return False
        except IOError, e:
            print "Send Error: ", e
        except AttributeError, e:
            print "Socket deleted."
        return False

    def __str__(self):
        return " ".join([str(m) for m in self.members])

class PingMessage():
    def __init__(self, srcname):
        self.type = MSG_PING
        self.source = srcname

    def __str__(self):
        return 'PingMessage from %s' % str(self.source)

########NEW FILE########
__FILENAME__ = queue
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example queue
@copyright: See LICENSE
"""
import Queue

class Queue:
    def __init__(self, maxsize=0):
        self.queue = Queue.Queue(maxsize)

    def qsize(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()

    def full(self):
        return self.queue.full()

    def put(self, item):
        return self.queue.put_nowait(item)

    def get(self):
        return self.queue.get_nowait()

    def __str__(self):
        return str(self.queue)

########NEW FILE########
__FILENAME__ = rlock
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example rlock object
@copyright: See LICENSE
"""
from concoord.threadingobject.drlock import DRLock

class RLock():
    def __init__(self):
        self.rlock = DRLock()

    def __repr__(self):
        return repr(self.rlock)

    def acquire(self, _concoord_command):
        try:
            return self.rlock.acquire(_concoord_command)
        except Exception as e:
            raise e

    def release(self, _concoord_command):
        try:
            self.rlock.release(_concoord_command)
        except Exception as e:
            raise e

    def __str__(self):
        return str(self.rlock)

########NEW FILE########
__FILENAME__ = semaphore
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example semaphore object
@copyright: See LICENSE
"""
from concoord.threadingobject.dsemaphore import DSemaphore

class Semaphore():
    def __init__(self, count=1):
        self.semaphore = DSemaphore(count)

    def __repr__(self):
        return repr(self.semaphore)

    def acquire(self, _concoord_command):
        try:
            return self.semaphore.acquire(_concoord_command)
        except Exception as e:
            raise e

    def release(self, _concoord_command):
        try:
            return self.semaphore.release(_concoord_command)
        except Exception as e:
            raise e

    def __str__(self):
        return str(self.semaphore)

########NEW FILE########
__FILENAME__ = stack
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Example stack
@copyright: See LICENSE
"""
class Stack:
    def __init__(self):
        self.stack = []

    def append(self, item):
        self.stack.append(item)

    def pop(self):
        self.stack.pop()

    def get_size(self):
        return len(self.stack)

    def get_stack(self):
        return self.stack

    def __str__(self):
        return self.stack





########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: openreplica script
@date: February 2013
@copyright: See LICENSE
'''
import argparse
import signal
from time import sleep,time
import os, sys, time, shutil
import ast, _ast
import ConfigParser
from concoord.enums import *
from concoord.safetychecker import *
from concoord.proxygenerator import *
from concoord.openreplica.nodemanager import *

HELPSTR = "openreplica, version 1.1.0-release:\n\
openreplica config - prints config file\n\
openreplica addsshkey [sshkey_filename] - adds sshkey filename to config\n\
openreplica addusername [ssh_username] - adds ssh username to config\n\
openreplica addnode [public_dns] - adds public dns for node to config\n\
openreplica setup [public_dns] - downloads and sets up concoord on the given node\n\
openreplica route53 [public_dns aws_access_key_id aws_secret_access_key] - sets up route53 credentials on the given node\n\
openreplica replica [concoord arguments] - starts a replica remotely"

OPENREPLICACONFIGFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'openreplica.cfg')
config = ConfigParser.RawConfigParser()

def touch_config_file():
    with open(OPENREPLICACONFIGFILE, 'a'):
        os.utime(OPENREPLICACONFIGFILE, None)

def read_config_file():
    config.read(OPENREPLICACONFIGFILE)
    section = 'ENVIRONMENT'
    options = ['NODES', 'SSH_KEY_FILE', 'USERNAME']
    rewritten = True
    if not config.has_section(section):
        rewritten = True
        config.add_section(section)
    for option in options:
        if not config.has_option(section, option):
            rewritten = True
            config.set(section, option, '')
    if rewritten:
        # Write to CONFIG file
        with open(OPENREPLICACONFIGFILE, 'wb') as configfile:
            config.write(configfile)
        config.read(OPENREPLICACONFIGFILE)
    nodes = config.get('ENVIRONMENT', 'NODES')
    sshkeyfile = config.get('ENVIRONMENT', 'SSH_KEY_FILE')
    username = config.get('ENVIRONMENT', 'USERNAME')

    return (nodes,sshkeyfile,username)

def print_config_file():
    print "NODES= %s\nSSH_KEY_FILE= %s\nUSERNAME= %s" % read_config_file()

def add_node_to_config(node):
    nodes,sshkeyfile,username = read_config_file()
    nodemanager = NodeManager(nodes, sshkeyfile, username)
    if not nodemanager.username:
        print "Add a username to connect to the nodes"
        return
    # First check if the node is eligible
    cmd = ["ssh", nodemanager.username+'@'+node, 'python -V']
    ssh = subprocess.Popen(cmd, shell=False,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    nodemanager._waitforall([ssh])
    result = ssh.stdout.readlines()
    output = ssh.stderr.readlines()[0]
    try:
        versionmajor, versionminor, versionmicro = output.strip().split()[1].split('.')
    except IndexError:
        print "Cannot connect to node, check if it is up and running."
        return
    except ValueError:
        print "Could not check Python version:", output
        print "Try again!"
        return

    version = int(versionmajor)*100 + int(versionminor) * 10 + int(versionmicro)
    if version < 266:
        print "Python should be updated to 2.7 or later on this machine. Attempting update."
        cmds = []
        cmds.append("sudo yum install make automake gcc gcc-c++ kernel-devel git-core -y")
        cmds.append("sudo yum install python27-devel -y")
        cmds.append("sudo rm /usr/bin/python")
        cmds.append("sudo ln -s /usr/bin/python2.7 /usr/bin/python")
        cmds.append("sudo cp /usr/bin/yum /usr/bin/_yum_before_27")
        cmds.append("sudo sed -i s/python/python2.6/g /usr/bin/yum")
        cmds.append("sudo sed -i s/python2.6/python2.6/g /usr/bin/yum")
        cmds.append("sudo curl -o /tmp/ez_setup.py https://sources.rhodecode.com/setuptools/raw/bootstrap/ez_setup.py")
        cmds.append("sudo /usr/bin/python27 /tmp/ez_setup.py")
        cmds.append("sudo /usr/bin/easy_install-2.7 pip")
        cmds.append("sudo pip install virtualenv")
        for cmd in cmds:
            p = nodemanager._issuecommand(cmd)

        # Check the version on node again
        cmd = ["ssh", nodemanager.username+'@'+node, 'python -V']
        ssh = subprocess.Popen(cmd, shell=False,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        nodemanager._waitforall([ssh])
        result = ssh.stdout.readlines()
        output = ssh.stderr.readlines()[0]
        versionmajor, versionminor, versionmicro = output.strip().split()[1].split('.')
        version = int(versionmajor)*100 + int(versionminor) * 10 + int(versionmicro)
        if version < 266:
            print "Remote update failed. To update the node by sshing, you can follow the steps below:"
            print "Install build tools first: "
            print "sudo yum install make automake gcc gcc-c++ kernel-devel git-core -y"
            print "Install Python 2.7 and change python symlink: "
            print "$ sudo yum install python27-devel -y"
            print "$ sudo rm /usr/bin/python"
            print "$ sudo ln -s /usr/bin/python2.7 /usr/bin/python"
            print "Keep Python2.6 for yum: "
            print "$ sudo cp /usr/bin/yum /usr/bin/_yum_before_27"
            print "$ sudo sed -i s/python/python2.6/g /usr/bin/yum"
            print "$ sudo sed -i s/python2.6/python2.6/g /usr/bin/yum"
            print "Install pip for Python2.7: "
            print "$ sudo curl -o /tmp/ez_setup.py https://sources.rhodecode.com/setuptools/raw/bootstrap/ez_setup.py"
            print "$ sudo /usr/bin/python27 /tmp/ez_setup.py"
            print "$ sudo /usr/bin/easy_install-2.7 pip"
            print "$ sudo pip install virtualenv"
            return
    if nodes == '':
        # There are no nodes
        newnodes = node
    elif nodes.find(',')!=-1:
        # There are multiple nodes
        if node in nodes.split(','):
            print "Node is already in the CONFIG file."
            return
        newnodes = nodes+','+node
    else:
        # There is only one node
        if node == nodes:
            print "Node is already in the CONFIG file."
            return
        newnodes = nodes+','+node

    # Write to CONFIG file
    config.set('ENVIRONMENT', 'NODES', newnodes)
    with open(OPENREPLICACONFIGFILE, 'wb') as configfile:
        config.write(configfile)

def add_username_to_config(newusername):
    nodes,sshkeyfile,username = read_config_file()
    if username and username == newusername:
        print "USERNAME is already in the CONFIG file."
        return
    # Write to CONFIG file
    config.set('ENVIRONMENT', 'USERNAME', newusername)
    with open(OPENREPLICACONFIGFILE, 'wb') as configfile:
        config.write(configfile)

def add_sshkeyfile_to_config(newsshkeyfile):
    nodes,sshkeyfile,username = read_config_file()
    if sshkeyfile and sshkeyfile == newsshkeyfile:
        print "SSH_KEY_FILE is already in the CONFIG file."
        return
    # Write to CONFIG file
    config.set('ENVIRONMENT', 'SSH_KEY_FILE', newsshkeyfile)
    with open(OPENREPLICACONFIGFILE, 'wb') as configfile:
        config.write(configfile)

def setup_route53(instance, awsid, awskey):
    nodes,sshkeyfile,username = read_config_file()
    nodemanager = NodeManager(nodes, sshkeyfile, username)

    if instance not in nodemanager.instances:
        print "This instance is not in the configuration. Add and try again."
        return
    cmd = ['ssh', nodemanager.username+'@'+instance, 'concoord route53id '+awsid]
    nodemanager._waitforall([nodemanager._issuecommand(cmd)])
    cmd = ['ssh', nodemanager.username+'@'+instance, 'concoord route53key '+awskey]
    nodemanager._waitforall([nodemanager._issuecommand(cmd)])

def setup_concoord(instance):
    nodes,sshkeyfile,username = read_config_file()
    nodemanager = NodeManager(nodes, sshkeyfile, username)

    if instance not in nodemanager.instances:
        print "This instance is not in the configuration. Add and try again."
        return
    print "Downloading concoord.."
    cmd = ['ssh', nodemanager.username+'@'+instance, 'wget http://openreplica.org/src/concoord-'+VERSION+'.tar.gz']
    nodemanager._waitforall([nodemanager._issuecommand(cmd)])
    print "Installing concoord.."
    cmd = ['ssh', nodemanager.username+'@'+instance, 'tar xvzf concoord-'+VERSION+'.tar.gz']
    nodemanager._waitforall([nodemanager._issuecommand(cmd)])
    cmd = ['ssh', nodemanager.username+'@'+instance, 'cd concoord-'+VERSION+' && python setup.py install']
    nodemanager._waitforall([nodemanager._issuecommand(cmd)])

def start_replica():
    nodemanager = NodeManager(*read_config_file())
    i = random.choice(nodemanager.instances)
    if '-n' in sys.argv[1:] or '--domainname' in sys.argv[1:]:
        if '-r' in sys.argv[1:] or '--route53' in sys.argv[1:]:
            cmd = ["ssh", "-t", nodemanager.username+'@'+i,
                   "sudo python -c \"exec(\\\"import boto\\\")\""]

            ssh = subprocess.Popen(cmd, shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            nodemanager._waitforall([ssh])
            result = ssh.stdout.readlines()
            output = ssh.stderr.readlines()
            # Try and install boto automatically
            if result:
                cmd = ["ssh", "-t", nodemanager.username+'@'+i,
                       "sudo pip install -U boto"]
                ssh = subprocess.Popen(cmd)
                nodemanager._waitforall([ssh])
        else:
            # Check if nameserver can connect to port 53
            cmd = ["ssh", "-t", nodemanager.username+'@'+i,
                   "sudo python -c \"exec(\\\"import socket\\nsocket.socket(socket.AF_INET,socket.SOCK_STREAM).bind(('localhost', 53))\\\")\""]

            ssh = subprocess.Popen(cmd, shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            nodemanager._waitforall([ssh])
            result = ssh.stdout.readlines()
            output = ssh.stderr.readlines()
            if result:
                print "The Nameserver cannot bind to socket 53. Try another instance."
                return

    print "Starting replica on %s" % str(i)
    cmd = ["ssh", nodemanager.username+'@'+i, 'concoord replica ' + ' '.join(sys.argv[1:])]
    p = nodemanager._issuecommand(cmd)

def main():
    touch_config_file()
    if len(sys.argv) < 2:
        print HELPSTR
        sys.exit()

    eventtype = sys.argv[1].upper()
    sys.argv.pop(1)

    touch_config_file()
    read_config_file()

    if eventtype == 'CONFIG':
        print_config_file()
    elif eventtype == 'ADDSSHKEY':
        print "Adding SSHKEY to CONFIG:", sys.argv[1]
        add_sshkeyfile_to_config(sys.argv[1])
    elif eventtype == 'ADDUSERNAME':
        print "Adding USERNAME to CONFIG:", sys.argv[1]
        add_username_to_config(sys.argv[1])
    elif eventtype == 'ADDNODE':
        print "Adding NODE to CONFIG:", sys.argv[1]
        add_node_to_config(sys.argv[1])
    elif eventtype == 'SETUP':
        print "Setting up ConCoord on", sys.argv[1]
        setup_concoord(sys.argv[1])
    elif eventtype == 'ROUTE53':
        if len(sys.argv) < 4:
            print HELPSTR
            sys.exit()
        print "Adding Route53 Credentials on :", sys.argv[1]
        setup_route53(sys.argv[1], sys.argv[2], sys.argv[3])
    elif eventtype == 'REPLICA':
        start_replica()
    else:
        print HELPSTR

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = nodemanager
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: NodeManager that handles remote operations.
@copyright: See LICENSE
'''
from threading import Thread
import sys, os, socket, os.path
import random, time
import subprocess, signal

VERSION = '1.1.0'

class NodeManager():
    def __init__(self, nodes, sshkey, username):
        self.username = username
        # username
        if not self.username:
            print "There is no username. Add username."
            return
        # instances
        if nodes:
            self.instances = nodes.split(',')
        else:
            self.instances = []
            return
        # key-pair filename
        self.sshkey = sshkey
        if self.sshkey:
            home = os.path.expanduser("~")
            cmd = ['ssh-add', home+'/.ssh/' + self.sshkey]
            self._waitforall([self._issuecommand(cmd)])
        else:
            print "There is no sshkey filename. Add sshkey filename."
            return
        self.alive = True

    def _tryconnect(self, host):
        cmd = ["ssh", host, "ls"]
        return self._system(cmd, timeout=20) == 0

    def _system(self, cmd, timeout=300):
        p = self._issuecommand(cmd)
        return self._waitforall([p], timeout)

    def _issuecommand(self, cmd):
        return subprocess.Popen(cmd)

    def _waitforall(self, pipelist, timeout=300):
        start = time.time()
        while len(pipelist) > 0:
            todo = []
            for pipe in pipelist:
                rtv = pipe.poll()
                if rtv is None:
                    # not done
                    todo.append(pipe)
            if len(todo) > 0:
                time.sleep(0.1)
                now = time.time()
                if now - start > timeout:
                    # timeout reached
                    for p in todo:
                        os.kill(p.pid, signal.SIGKILL)
                        os.waitpid(p.pid, os.WNOHANG)
                    return -len(todo)
            pipelist = todo
        return 0

    def executecommandall(self, command, wait=True):
        pipedict = {}
        for node in self.nodes:
            cmd = ["ssh", self.host, command]
            pipe = self._issuecommand(cmd)
            if wait:
                pipedict[pipe] = pipe.communicate()
        if wait:
            return (self._waitforall(pipedict.keys()) == 0, pipedict)
        return

    def executecommandone(self, node, command, wait=True):
        cmd = ["ssh", host, command]
        pipe = self._issuecommand(cmd)
        if wait:
            pipe.poll()
            stdout,stderr = pipe.communicate()
            return (self._waitforall([pipe]) == 0, (stdout,stderr))
        return pipe

    def download(self, remote, local):
        cmd = "scp " + self.host + ":" + remote + " "+ local
        rtv = os.system(cmd)
        return rtv

    def upload(self, host, node, local, remote=""):
        """upload concoord src to amazon instance"""
        cmd = ["scp", local, host + ":" + remote]
        if os.path.isdir(local):
            cmd.insert(1, "-r")
        pipe = self._issuecommand(cmd)
        return self._waitforall([pipe]) == 0

    def __str__(self):
        rstr = "Username: " + self.username + '\n'
        rstr += "SSH key file: " + self.sshkey + '\n'
        rstr += "Instances:\n"
        rstr += '\n'.join(self.instances)
        return rstr

########NEW FILE########
__FILENAME__ = openreplicanameserver
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: OpenReplicaNameserver that uses OpenReplica Coordination Object to keep track of nameservers of subdomains of OpenReplica.
@copyright: See LICENSE
'''
from time import strftime, gmtime
from concoord.nameserver import *

OPENREPLICANS = {'ns1.openreplica.org.':'128.84.154.110', 'ns2.openreplica.org.':'128.84.154.40'}
OPENREPLICAWEBHOST = '128.84.154.110'
VIEWCHANGEFUNCTIONS = ['addnodetosubdomain','delnodefromsubdomain','delsubdomain']

class OpenReplicaNameserver(Nameserver):
    def __init__(self):
        Nameserver.__init__(self, domain='openreplica.org', instantiateobj=True)
        self.mysrvdomain = dns.name.Name(['_concoord', '_tcp', 'openreplica', 'org', ''])
        self.specialdomain = dns.name.Name(['ipaddr','openreplica','org',''])
        self.nsdomains = []
        for nsdomain in OPENREPLICANS.iterkeys():
            self.nsdomains.append(dns.name.Name(nsdomain.split(".")))
        # When the nameserver starts the revision number is 00 for that day
        self.revision = strftime("%Y%m%d", gmtime())+str(0).zfill(2)

    def performcore(self, command, dometaonly=False, designated=False):
        Replica.performcore(self, command, dometaonly, designated)
        commandtuple = command.command
        if type(commandtuple) == str:
            commandname = commandtuple
        else:
            commandname = commandtuple[0]
        if commandname in VIEWCHANGEFUNCTIONS:
            self.updaterevision()

    def perform(self, msg):
        Replica.perform(self, msg)

    def msg_perform(self, conn, msg):
        Replica.msg_perform(self, conn, msg)

    def ismysubdomainname(self, question):
        for subdomain in self.object.getsubdomains():
            if question.name in [dns.name.Name([subdomain, 'openreplica', 'org', '']), dns.name.Name(['_concoord', '_tcp', subdomain, 'openreplica', 'org', ''])]:
                return True
        return False

    def ismynsname(self, question):
        for nsdomain in OPENREPLICANS.iterkeys():
            if question.name == dns.name.Name(nsdomain.split(".")):
                return True
        return False

    def aresponse(self, question=''):
        yield OPENREPLICAWEBHOST

    def aresponse_ipaddr(self, question):
        # Asking for IPADDR.ipaddr.openreplica.org
        # Respond with IPADDR
        yield question.name.split(4)[0].to_text()

    def aresponse_ns(self, question):
        # Asking for ns1/ns2/ns3.openreplica.org
        # Respond with corresponding addr
        for nsdomain,nsaddr in OPENREPLICANS.iteritems():
            if dns.name.Name(nsdomain.split(".")) == question.name:
                yield nsaddr

    def aresponse_subdomain(self, question):
        for subdomain in self.object.getsubdomains():
            subdomain = subdomain.strip('.')
            if question.name in [dns.name.Name([subdomain, 'openreplica', 'org', '']), dns.name.Name(['_concoord', '_tcp', subdomain, 'openreplica', 'org', ''])]:
                for node in self.object.getnodes(subdomain)[NODE_REPLICA]:
                    addr,port = node.split(":")
                    yield addr

    def nsresponse(self, question):
        if question.name == self.mydomain or question.name.is_subdomain(self.specialdomain) or self.ismysubdomainname(question):
            for address,port in get_addressportpairs(self.nameservers):
                yield address+self.ipconverter
            yield self.addr+self.ipconverter
        for nsdomain,nsaddr in OPENREPLICANS.iteritems():
            yield nsdomain

    def nsresponse_subdomain(self, question):
        for subdomain in self.object.getsubdomains():
            subdomain = subdomain.strip('.')
            if question.name in [dns.name.Name([subdomain, 'openreplica', 'org', '']), dns.name.Name(['_concoord', '_tcp', subdomain, 'openreplica', 'org', ''])]:
                for node in self.object.getnodes(subdomain)[NODE_NAMESERVER]:
                    addr,port = node.split(":")
                    yield addr+self.ipconverter

    def txtresponse_subdomain(self, question):
        txtstr = ''
        for subdomain in self.object.getsubdomains():
            subdomain = subdomain.strip('.')
            if question.name in [dns.name.Name([subdomain, 'openreplica', 'org', '']), dns.name.Name(['_concoord', '_tcp', subdomain, 'openreplica', 'org', ''])]:
                for nodetype,nodes in self.object.getnodes(subdomain).iteritems():
                    for node in nodes:
                        txtstr += node_names[nodetype] + ' ' + node + ';'
        return txtstr

    def srvresponse_subdomain(self, question):
        for subdomain in self.object.getsubdomains():
            subdomain = subdomain.strip('.')
            if question.name in [dns.name.Name([subdomain, 'openreplica', 'org', '']), dns.name.Name(['_concoord', '_tcp', subdomain, 'openreplica', 'org', ''])]:
                for node in self.object.getnodes(subdomain)[NODE_REPLICA]:
                    try:
                        addr,port = node.split(":")
                        yield addr+self.ipconverter,int(port)
                    except:
                        pass

    def should_answer(self, question):
        formyname = (question.rdtype == dns.rdatatype.A or question.rdtype == dns.rdatatype.TXT or question.rdtype == dns.rdatatype.NS or question.rdtype == dns.rdatatype.SRV or question.rdtype == dns.rdatatype.MX or question.rdtype == dns.rdatatype.SOA) and self.ismydomainname(question)
        formysubdomainname = (question.rdtype == dns.rdatatype.A or question.rdtype == dns.rdatatype.TXT or question.rdtype == dns.rdatatype.NS or question.rdtype == dns.rdatatype.SRV or question.rdtype == dns.rdatatype.SOA) and self.ismysubdomainname(question)
        myresponsibility_a = question.rdtype == dns.rdatatype.A and (self.ismynsname(question) or question.name.is_subdomain(self.specialdomain))
        myresponsibility_ns = question.rdtype == dns.rdatatype.NS and self.ismysubdomainname(question)
        return formyname or formysubdomainname or myresponsibility_a or myresponsibility_ns

    def should_auth(self, question):
        return (question.rdtype == dns.rdatatype.AAAA or question.rdtype == dns.rdatatype.A or question.rdtype == dns.rdatatype.TXT or question.rdtype == dns.rdatatype.SRV) and self.ismysubdomainname(question) or (question.rdtype == dns.rdatatype.AAAA and (self.ismydomainname(question) or self.ismysubdomainname(question) or question.name.is_subdomain(self.specialdomain)))

    def handle_query(self, data, addr):
        query = dns.message.from_wire(data)
        response = dns.message.make_response(query)
        for question in query.question:
            if self.debug: self.logger.write("DNS State", "Received Query for %s\n" % question.name)
            if self.debug: self.logger.write("DNS State", "Received Query %s\n" % question)
            if self.should_answer(question):
                flagstr = 'QR AA' # response, authoritative
                answerstr = ''
                if question.rdtype == dns.rdatatype.A:
                    if self.ismydomainname(question):
                        # A Queries --> List all Replicas starting with the Leader
                        for address in self.aresponse(question):
                            answerstr += self.create_answer_section(question, addr=address)
                    elif self.ismysubdomainname(question):
                        for address in self.aresponse_subdomain(question):
                            answerstr += self.create_answer_section(question, addr=address)
                    elif self.ismynsname(question):
                        # A Queries --> List all Replicas starting with the Leader
                        for address in self.aresponse_ns(question):
                            answerstr += self.create_answer_section(question, addr=address)
                    elif question.name.is_subdomain(self.specialdomain):
                        # A Query for ipaddr --> Respond with ipaddr
                        for address in self.aresponse_ipaddr(question):
                            answerstr += self.create_answer_section(question, addr=address)
                elif question.rdtype == dns.rdatatype.TXT:
                    if self.ismydomainname(question):
                        # TXT Queries --> List all nodes
                        answerstr = self.create_answer_section(question, txt=self.txtresponse(question))
                    elif self.ismysubdomainname(question):
                        answerstr = self.create_answer_section(question, txt=self.txtresponse_subdomain(question))
                elif question.rdtype == dns.rdatatype.NS:
                    if self.ismydomainname(question):
                        # NS Queries --> List all Nameserver nodes
                        for address in self.nsresponse(question):
                            answerstr += self.create_answer_section(question, name=address)
                    elif self.ismysubdomainname(question):
                        # NS Queries --> List Nameservers of my subdomain
                        #for address in self.nsresponse_subdomain(question):
                        for address in self.nsresponse(question):
                            answerstr += self.create_answer_section(question, name=address)
                elif question.rdtype == dns.rdatatype.SRV:
                    if self.ismydomainname(question):
                        # SRV Queries --> List all Replicas with addr:port
                        for address,port in self.srvresponse(question):
                            answerstr += self.create_srv_answer_section(question, addr=address, port=port)
                    elif self.ismysubdomainname(question):
                        for address,port in self.srvresponse_subdomain(question):
                            answerstr += self.create_srv_answer_section(question, addr=address, port=port)
                elif question.rdtype == dns.rdatatype.MX:
                    if self.ismydomainname(question):
                        # MX Queries --> mail.systems.cs.cornell.edu
                        answerstr = self.create_mx_answer_section(question, ttl=86400, addr='mail.systems.cs.cornell.edu.')
                elif question.rdtype == dns.rdatatype.SOA:
                    if self.ismydomainname(question) or self.ismysubdomainname(question):
                        # SOA Query --> Reply with Metadata
                        answerstr = self.create_soa_answer_section(question)
                responsestr = self.create_response(response.id,opcode=dns.opcode.QUERY,rcode=dns.rcode.NOERROR,flags=flagstr,question=question.to_text(),answer=answerstr,authority='',additional='')
                response = dns.message.from_text(responsestr)
            elif self.should_auth(question):
                if self.debug: self.logger.write("DNS State", "Query for my subdomain: %s" % str(question))
                flagstr = 'QR' # response, not authoritative
                authstr = ''
                for address in self.nsresponse_subdomain(question):
                    authstr += self.create_authority_section(question, nshost=address, rrtype=dns.rdatatype.NS)
                responsestr = self.create_response(response.id,opcode=dns.opcode.QUERY,rcode=dns.rcode.NOERROR,flags=flagstr,question=question.to_text(),answer='',authority=authstr,additional='')
                response = dns.message.from_text(responsestr)
            else:
                # This Query is not something I know how to respond to
                if self.debug: self.logger.write("DNS State", "UNSUPPORTED QUERY, %s" %str(question))
                return
        if self.debug: self.logger.write("DNS State", "RESPONSE:\n%s\n---\n" % str(response))
        try:
            self.udpsocket.sendto(response.to_wire(), addr)
        except:
            if self.debug: self.logger.write("DNS Error", "Cannot send RESPONSE:\n%s\n---\n" % str(response))

def main():
    nameservernode = OpenReplicaNameserver()
    nameservernode.startservice()
    signal.signal(signal.SIGINT, nameservernode.terminate_handler)
    signal.signal(signal.SIGTERM, nameservernode.terminate_handler)
    signal.pause()

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = pack
"""
@author: Deniz Altinbuken
@note: Tuples used by ConCoord
@copyright: See LICENSE
"""
from collections import namedtuple

Proposal = namedtuple('Proposal', ['client', 'clientcommandnumber', 'command'])
ProposalClientBatch = namedtuple('ProposalClientBatch', ['client', 'clientcommandnumber', 'command'])
ProposalServerBatch = namedtuple('ProposalServerBatch', ['proposals'])

class Peer(namedtuple('Peer', ['addr', 'port', 'type'])):
        __slots__ = ()
        def __str__(self):
            return str((self.addr, self.port, self.type))

PValue = namedtuple('PValue', ['ballotnumber', 'commandnumber', 'proposal'])
Message = namedtuple('Message', ['id', 'type', 'source'])
IssueMessage = namedtuple('IssueMessage', ['id', 'type', 'source'])
StatusMessage = namedtuple('StatusMessage', ['id', 'type', 'source'])
HeloReplyMessage = namedtuple('HeloReplyMessage', ['id', 'type', 'source', 'leader'])
UpdateReplyMessage = namedtuple('UpdateReplyMessage', ['id', 'type', 'source', 'decisions'])
PrepareMessage = namedtuple('PrepareMessage', ['id', 'type', 'source', 'ballotnumber'])
PrepareReplyMessage = namedtuple('PrepareReplyMessage', ['id', 'type','source',
                                                         'ballotnumber', 'inresponseto',
                                                         'pvalueset'])
ProposeMessage = namedtuple('ProposeMessage', ['id', 'type','source',
                                               'ballotnumber', 'commandnumber',
                                               'proposal', 'serverbatch'])
ProposeReplyMessage = namedtuple('ProposeReplyMessage', ['id', 'type','source',
                                                         'ballotnumber', 'inresponseto',
                                                         'commandnumber'])
PerformMessage = namedtuple('PerformMessage', ['id', 'type','source',
                                               'commandnumber', 'proposal',
					       'serverbatch', 'clientbatch',
					       'decisionballotnumber'])

ClientRequestMessage = namedtuple('ClientRequestMessage', ['id', 'type', 'source',
                                                           'command', 'token',
                                                           'sendcount', 'clientbatch'])

ClientReplyMessage = namedtuple('ClientReplyMessage', ['id', 'type', 'source',
                                                       'reply', 'replycode', 'inresponseto'])

GarbageCollectMessage = namedtuple('GarbageCollectMessage', ['id', 'type', 'source',
                                                             'commandnumber', 'snapshot'])

########NEW FILE########
__FILENAME__ = bank
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Bank proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy
class Bank:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def open(self, accntno):
        return self.proxy.invoke_command('open', accntno)

    def close(self, accntno):
        return self.proxy.invoke_command('close', accntno)

    def debit(self, accntno, amount):
        return self.proxy.invoke_command('debit', accntno, amount)

    def deposit(self, accntno, amount):
        return self.proxy.invoke_command('deposit', accntno, amount)

    def balance(self, accntno):
        return self.proxy.invoke_command('balance', accntno)

    def __str__(self):
        return self.proxy.invoke_command('__str__')


########NEW FILE########
__FILENAME__ = barrier
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Barrier proxy
@copyright: See LICENSE
'''
from concoord.blockingclientproxy import ClientProxy

class Barrier:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self, count=1):
        return self.proxy.invoke_command('__init__', count)

    def wait(self):
        return self.proxy.invoke_command('wait')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = binarytree
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Binarytree proxy
@copyright: See LICENSE
"""
from concoord.clientproxy import ClientProxy
class BinaryTree:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def add_node(self, data):
        return self.proxy.invoke_command('add_node', data)

    def insert(self, root, data):
        return self.proxy.invoke_command('insert', root, data)

    def find(self, root, target):
        return self.proxy.invoke_command('find', root, target)

    def delete(self, root, target):
        return self.proxy.invoke_command('delete', root, target)

    def get_min(self, root):
        return self.proxy.invoke_command('get_min', root)

    def get_max(self, root):
        return self.proxy.invoke_command('get_max', root)

    def get_depth(self, root):
        return self.proxy.invoke_command('get_depth', root)

    def get_size(self, root):
        return self.proxy.invoke_command('get_size', root)





########NEW FILE########
__FILENAME__ = boundedsemaphore
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Bounded semaphore proxy
@copyright: See LICENSE
'''
from concoord.blockingclientproxy import ClientProxy

class BoundedSemaphore:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self, count=1):
        return self.proxy.invoke_command('__init__', count)

    def __repr__(self):
        return self.proxy.invoke_command('__repr__')

    def acquire(self):
        return self.proxy.invoke_command('acquire')

    def release(self):
        return self.proxy.invoke_command('release')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = condition
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Condition proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class Condition:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self, lock=None):
        return self.proxy.invoke_command('__init__', lock)

    def __repr__(self):
        return self.proxy.invoke_command('__repr__')

    def acquire(self):
        return self.proxy.invoke_command('acquire')

    def release(self):
        return self.proxy.invoke_command('release')

    def wait(self):
        return self.proxy.invoke_command('wait')

    def notify(self):
        return self.proxy.invoke_command('notify')

    def notifyAll(self):
        return self.proxy.invoke_command('notifyAll')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = counter
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Counter proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class Counter:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self, value=0):
        return self.proxy.invoke_command('__init__', value)

    def decrement(self):
        return self.proxy.invoke_command('decrement')

    def increment(self):
        return self.proxy.invoke_command('increment')

    def getvalue(self):
        return self.proxy.invoke_command('getvalue')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = jobmanager
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Jobmanager proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class JobManager:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def add_job(self, job):
        return self.proxy.invoke_command('add_job', job)

    def remove_job(self, job):
        return self.proxy.invoke_command('remove_job', job)

    def list_jobs(self):
        return self.proxy.invoke_command('list_jobs')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

class Job:
    def __init__(self, jobname, jobid, jobtime):
        self.name = jobname
        self.id = jobid
        self.time = jobtime

    def __str__(self):
        return 'Job %s: %s @ %s' % (str(job.id), str(job.name), str(job.time))

########NEW FILE########
__FILENAME__ = lock
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Lock proxy
@copyright: See LICENSE
'''
from concoord.blockingclientproxy import ClientProxy

class Lock:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def __repr__(self):
        return self.proxy.invoke_command('__repr__')

    def acquire(self):
        return self.proxy.invoke_command('acquire')

    def release(self):
        return self.proxy.invoke_command('release')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = log
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Log proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class Log:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def write(self, entry):
        return self.proxy.invoke_command('write', entry)

    def append(self, entry):
        return self.proxy.invoke_command('append', entry)

    def read(self):
        return self.proxy.invoke_command('read')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = membership
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Membership proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class Membership:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def add(self, member):
        return self.proxy.invoke_command('add', member)

    def remove(self, member):
        return self.proxy.invoke_command('remove', member)

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = meshmembership
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: MeshMembership proxy
@copyright: See LICENSE
"""
from concoord.blockingclientproxy import ClientProxy

class MeshMembership():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def get_group_members(self, gname):
        return self.proxy.invoke_command('get_group_members', gname)

    def get_group_epoch(self, gname):
        return self.proxy.invoke_command('get_group_epoch', gname)

    def get_group_state(self, gname):
        return self.proxy.invoke_command('get_group_state', gname)

    def add_group(self, gname, minsize):
        return self.proxy.invoke_command('add_group', gname, minsize)

    def remove_group(self, gname):
        return self.proxy.invoke_command('remove_group', gname)

    def approve_join(self, gname, node, epochno):
        return self.proxy.invoke_command('approve_join', gname, node, epochno)

    def wait(self, gname):
        return self.proxy.invoke_command('wait', gname)

    def check_member(self, gname, node):
        return self.proxy.invoke_command('check_member', gname, node)

    def notify_failure(self, gname, epoch, failednode):
        return self.proxy.invoke_command('notify_failure', gname, epoch, failednode)

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = nameservercoord
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Nameserver coordination object proxy
@copyright: See LICENSE
'''
from concoord.clientproxy import ClientProxy

class NameserverCoord:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def addnodetosubdomain(self, subdomain, nodetype, node):
        return self.proxy.invoke_command('addnodetosubdomain', subdomain, nodetype, node)

    def delsubdomain(self, subdomain):
        return self.proxy.invoke_command('delsubdomain', subdomain)

    def delnodefromsubdomain(self, subdomain, nodetype, node):
        return self.proxy.invoke_command('delnodefromsubdomain', subdomain, nodetype, node)

    def updatesubdomain(self, subdomain, nodes):
        return self.proxy.invoke_command('updatesubdomain', subdomain, nodes)

    def getnodes(self, subdomain):
        return self.proxy.invoke_command('getnodes', subdomain)

    def getsubdomains(self):
        return self.proxy.invoke_command('getsubdomains')

    def _reinstantiate(self, state):
        return self.proxy.invoke_command('_reinstantiate', state)

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = queue
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Queue proxy
@copyright: See LICENSE
"""
from concoord.clientproxy import ClientProxy
class Queue:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def append(self, item):
        return self.proxy.invoke_command('append', item)

    def remove(self):
        return self.proxy.invoke_command('remove')

    def get_size(self):
        return self.proxy.invoke_command('get_size')

    def get_queue(self):
        return self.proxy.invoke_command('get_queue')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = rlock
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: RLock proxy
@copyright: See LICENSE
'''
from concoord.blockingclientproxy import ClientProxy

class RLock:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def __repr__(self):
        return self.proxy.invoke_command('__repr__')

    def acquire(self):
        return self.proxy.invoke_command('acquire')

    def release(self):
        return self.proxy.invoke_command('release')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = semaphore
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Semaphore proxy
@copyright: See LICENSE
'''
from concoord.blockingclientproxy import ClientProxy

class Semaphore:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self, count=1):
        return self.proxy.invoke_command('__init__', count)

    def acquire(self):
        return self.proxy.invoke_command('acquire')

    def release(self):
        return self.proxy.invoke_command('release')

    def __str__(self):
        return self.proxy.invoke_command('__str__')

########NEW FILE########
__FILENAME__ = stack
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Stack proxy
@copyright: See LICENSE
"""
from concoord.clientproxy import ClientProxy
class Stack:
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def append(self, item):
        return self.proxy.invoke_command('append', item)

    def pop(self):
        return self.proxy.invoke_command('pop')

    def get_size(self):
        return self.proxy.invoke_command('get_size')

    def get_stack(self):
        return self.proxy.invoke_command('get_stack')

    def __str__(self):
        return self.proxy.invoke_command('__str__')




########NEW FILE########
__FILENAME__ = test
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Value object proxy to test concoord implementation
@copyright: See LICENSE
"""
from concoord.clientproxy import ClientProxy

class Test():
    def __init__(self, bootstrap, timeout=60, debug=False, token=None):
        self.proxy = ClientProxy(bootstrap, timeout, debug, token)

    def __concoordinit__(self):
        return self.proxy.invoke_command('__init__')

    def getvalue(self):
        return self.proxy.invoke_command('getvalue')

    def setvalue(self, newvalue):
        return self.proxy.invoke_command('setvalue', newvalue)

    def __str__(self):
        return self.proxy.invoke_command('__str__')


########NEW FILE########
__FILENAME__ = proxygenerator
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Proxy Generator that creates ConCoord proxy files from regular Python objects.
@copyright: See LICENSE
'''
import codegen
import ast, _ast
import os, shutil
import inspect, types, string
from concoord.enums import PR_BASIC, PR_BLOCK, PR_CBATCH, PR_SBATCH

class ProxyGen(ast.NodeTransformer):
    def __init__(self, objectname, securitytoken=None, proxytype=0):
        self.objectname = objectname
        self.classdepth = 0
        self.token = securitytoken
        self.proxytype = proxytype

    def generic_visit(self, node):
        ast.NodeTransformer.generic_visit(self, node)
        return node

    def visit_Module(self, node):
        if self.proxytype == PR_BASIC:
            importstmt = compile("from concoord.clientproxy import ClientProxy","<string>","exec",_ast.PyCF_ONLY_AST).body[0]
        elif self.proxytype == PR_BLOCK:
            importstmt = compile("from concoord.blockingclientproxy import ClientProxy","<string>","exec",_ast.PyCF_ONLY_AST).body[0]
        elif self.proxytype == PR_CBATCH:
            importstmt = compile("from concoord.batchclientproxy import ClientProxy","<string>","exec",_ast.PyCF_ONLY_AST).body[0]
        elif self.proxytype == PR_SBATCH:
            importstmt = compile("from concoord.asyncclientproxy import ClientProxy","<string>","exec",_ast.PyCF_ONLY_AST).body[0]
        node.body.insert(0, importstmt)
        return self.generic_visit(node)

    def visit_Import(self, node):
        return self.generic_visit(node)

    def visit_ImportFrom(self, node):
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        selectedclass = node.name == self.objectname
        if selectedclass or self.classdepth:
            self.classdepth += 1
        if self.classdepth == 1:
            for item in node.body:
                if type(item) == _ast.FunctionDef and item.name == "__init__":
                    #node.body.remove(item)
                    item.name = "__concoordinit__"
            # Add the new init method
            initfunc = compile("def __init__(self, bootstrap):\n"
                               "\tself.proxy = ClientProxy(bootstrap, token=\"%s\")" % self.token,
                               "<string>",
                               "exec",
                               _ast.PyCF_ONLY_AST).body[0]
            node.body.insert(0, initfunc)
        ret = self.generic_visit(node)
        if selectedclass or self.classdepth:
            self.classdepth -= 1
        return ret

    def visit_FunctionDef(self, node):
        if self.classdepth == 1:
            for i in node.args.args:
                if i.id == '_concoord_command':
                    node.args.args.remove(i)
            if node.name == "__init__":
                pass
            else:
                args = ["\'"+ node.name +"\'"]+[i.id for i in node.args.args[1:]]
                node.body = compile("return self.proxy.invoke_command(%s)" % ", ".join(args),
                                    "<string>",
                                    "exec",
                                    _ast.PyCF_ONLY_AST).body
            return node
        else:
            return self.generic_visit(node)

def createclientproxy(clientcode, objectname, securitytoken, proxytype=PR_BASIC, bootstrap=None):
    # Get the AST tree, transform it, convert back to string
    originalast = compile(clientcode, "<string>", "exec", _ast.PyCF_ONLY_AST)
    newast = ProxyGen(objectname, securitytoken, proxytype).visit(originalast)
    return codegen.to_source(newast)


########NEW FILE########
__FILENAME__ = pvalue
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: PValue is used to keep Paxos state in Acceptor and Leader nodes.
@copyright: See LICENSE
'''
from concoord.pack import *
import types

class PValueSet():
    """PValueSet encloses a set of pvalues with the highest ballotnumber (always)
    and supports corresponding set functions.
    """
    def __init__(self):
        self.pvalues = {} # indexed by (commandnumber,proposal): pvalue

    def add(self, pvalue):
        """Adds given PValue to the PValueSet overwriting matching
        (commandnumber,proposal) if it exists and has a smaller ballotnumber
        """
        if isinstance(pvalue.proposal, ProposalServerBatch):
            # list of Proposals cannot be hashed, cast them to tuple
            index = (pvalue.commandnumber,tuple(pvalue.proposal.proposals))
        else:
            index = (pvalue.commandnumber,pvalue.proposal)

        if self.pvalues.has_key(index):
            if self.pvalues[index].ballotnumber < pvalue.ballotnumber:
                self.pvalues[index] = pvalue
        else:
            self.pvalues[index] = pvalue

    def remove(self, pvalue):
        """Removes given pvalue"""
        if isinstance(pvalue.proposal, ProposalServerBatch):
            # list of Proposals cannot be hashed, cast them to tuple
            index = (pvalue.commandnumber,tuple(pvalue.proposal.proposals))
        else:
            index = (pvalue.commandnumber,pvalue.proposal)
        del self.pvalues[index]

    def truncateto(self, commandnumber):
        """Truncates the history up to given commandnumber"""
        keytuples = self.pvalues.keys()
        allkeys = sorted(keytuples, key=lambda keytuple: keytuple[0])
        # Sanity checking
        lastkey = allkeys[0][0]
        candelete = True
        for (cmdno,proposal) in allkeys:
            if cmdno == lastkey:
                lastkey += 1
            else:
                candelete = False
                break
        # Truncating
        if not candelete:
            return False
        for (cmdno,proposal) in allkeys:
            if cmdno < commandnumber:
                del self.pvalues[(cmdno,proposal)]
        return True

    def union(self, otherpvalueset):
        """Unionizes the pvalues of givenPValueSet with the pvalues of the
        PValueSet overwriting the (commandnumber,proposal) pairs with lower
        ballotnumber
        """
        for candidate in otherpvalueset.pvalues.itervalues():
            self.add(candidate)

    def pmax(self):
        """Returns a mapping from command numbers to proposals with the highest ballotnumbers"""
        pmaxresult = {}
        for (commandnumber,proposal) in self.pvalues.keys():
            pmaxresult[commandnumber] = proposal
        return pmaxresult

    def __len__(self):
        """Returns the number of PValues in the PValueSet"""
        return len(self.pvalues)

    def __str__(self):
        """Returns PValueSet information"""
        return "\n".join(str(pvalue) for pvalue in self.pvalues.itervalues())

########NEW FILE########
__FILENAME__ = replica
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: The Replica keeps an object and responds to Perform messages received from the Leader.
@copyright: See LICENSE
'''
import inspect
import time
import os, sys
import signal
import cPickle as pickle
from threading import Thread, Lock, Timer, Event
from concoord.pack import Proposal, PValue
from concoord.pvalue import PValueSet
from concoord.nameserver import Nameserver
from concoord.responsecollector import ResponseCollector
from concoord.exception import ConCoordException, BlockingReturn, UnblockingReturn
from concoord.node import *
from concoord.enums import *
from concoord.utils import *
from concoord.message import *

backoff_event = Event()
class Replica(Node):
    def __init__(self):
        Node.__init__(self)
        # load and initialize the object to be replicated
        import importlib
        objectloc,a,classname = self.objectname.rpartition('.')
        self.object = None
        try:
            module = importlib.import_module(objectloc)
            if hasattr(module, classname):
                self.object = getattr(module, classname)()
        except (ValueError, ImportError, AttributeError):
            self.object = None

        if not self.object:
            self.logger.write("Object Error", "Object cannot be found.")
            self._graceexit(1)
        try:
            self.token = getattr(self.object, '_%s__concoord_token' % self.objectname)
        except AttributeError as e:
            if self.debug: self.logger.write("State", "Object initialized without a token.")
            self.token = None

        # leadership state
        self.leader_initializing = False
        self.isleader = False
        self.ballotnumber = (0, 0, self.id)
        self.nexttoexecute = 1
        # decided commands: <commandnumber:command>
        self.decisions = {}
        self.decisionset = set()
        # executed commands: <command:(replycode,commandresult,unblocked{})>
        self.executed = {}
        # commands that are proposed: <commandnumber:command>
        self.proposals = {}
        self.proposalset = set()
        # commands that are received, not yet proposed: <commandnumber:command>
        self.pendingcommands = {}
        self.pendingcommandset = set()
        # commandnumbers known to be in use
        self.usedcommandnumbers = set()
        # nodes being added/deleted
        self.nodesbeingdeleted = set()
        # number for metacommands initiated from this replica
        self.metacommandnumber = 0
        # keep nodes that are recently updated
        self.recentlyupdatedpeerslock = Lock()
        self.recentlyupdatedpeers = []

        # Quorum state
        if self.durable:
            self.file = open('concoordlog', 'a')

        self.quorumballotnumber = (0, 0, '')
        self.last_accept_msg_id = -1
        self.quorumaccepted = PValueSet()
        self.objectsnapshot = (0,None)

        # PERFORMANCE MEASUREMENT VARS
        self.firststarttime = 0
        self.firststoptime = 0
        self.secondstarttime = 0
        self.secondstoptime = 0
        self.count = 0

        self.throughput_runs = 0
        self.throughput_stop = 0
        self.throughput_start = 0

    def __str__(self):
        rstr = "%s %s:%d\n" % ("LEADER" if self.isleader else node_names[self.type], self.addr, self.port)
        rstr += "Members:\n%s\n" % "\n".join(str(peer) for peer in self.replicas)
        rstr += "Waiting to execute command %d.\n" % self.nexttoexecute
        rstr += "Commands:\n"
        for commandnumber, command in self.decisions.iteritems():
            state = ''
            if command in self.executed:
                if isinstance(command, ProposalClientBatch):
                    state = '\t' + str(self.executed[command])
                else:
                    state = '\t' + cr_codes[self.executed[command][0]]+ '\t' + str(self.executed[command][1])
            rstr += str(commandnumber) + ":\t" + str(command) + state + '\n'
        if len(self.pendingcommands):
            rstr += "Pending Commands:\n"
            for commandnumber, command in self.pendingcommands.iteritems():
                rstr += str(commandnumber) + ":\t" + str(command) + '\n'
        if len(self.proposals):
            rstr += "Proposals:\n"
            for commandnumber, command in self.proposals.iteritems():
                rstr += str(commandnumber) + ":\t" + str(command) + '\n'
        # Add QUORUM State
        rstr += "Quorum Ballot Number: %s\n" % str(self.quorumballotnumber)
        rstr += "Accepted PValues: %s\n" % str(self.quorumaccepted)

        return rstr

    def _import_object(self, name):
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    def startservice(self):
        """Start the background services associated with a replica."""
        Node.startservice(self)

        if self.isnameserver and not self.useroute53:
            if self.debug: self.logger.write("State", "Starting the Nameserver Thread.")
            # Start a thread for the UDP server
            UDP_server_thread = Thread(target=self.nameserver.udp_server_loop, name='UDPServerThread')
            UDP_server_thread.start()

    @staticmethod
    def _apply_args_to_method(method, args, _concoord_command):
        argspec = inspect.getargspec(method)
        if argspec.args and argspec.args[-1] == '_concoord_command':
            return method(*args, _concoord_command=_concoord_command)
        elif argspec.keywords is not None:
            return method(*args, _concoord_command=_concoord_command)
        else:
            return method(*args)

    def performcore_clientbatch(self, commandbatch, designated=False):
        '''performs all clientrequests in a clientbatch and returns a batched result.'''
        if self.debug: self.logger.write("State", "Performing client batch.")
        clientreplies = []
        for commandtuple in commandbatch.command:
            commandname = commandtuple[0]
            commandargs = commandtuple[1:]
            # Result triple
            clientreplycode, givenresult, unblocked = (-1, None, {})
            try:
                method = getattr(self.object, commandname)
                # Watch out for the lock release and acquire!
                self.lock.release()
                try:
                    givenresult = method(*commandargs)
                    clientreplycode = CR_OK
                except BlockingReturn as blockingretexp:
                    if self.debug: self.logger.write("State", "Blocking Client.")
                    givenresult = blockingretexp.returnvalue
                    clientreplycode = CR_BLOCK
                except UnblockingReturn as unblockingretexp:
                    if self.debug: self.logger.write("State", "Unblocking Client(s).")
                    # Get the information about the method call
                    # These will be used to update executed and
                    # to send reply message to the caller client
                    givenresult = unblockingretexp.returnvalue
                    unblocked = unblockingretexp.unblocked
                    clientreplycode = CR_OK
                    # If there are clients to be unblocked that have
                    # been blocked previously, send them unblock messages
                    for unblockedclientcommand in unblocked.iterkeys():
                        self.send_reply_to_client(CR_UNBLOCK, None, unblockedclientcommand)
                except Exception as e:
                    if self.debug: self.logger.write("Execution Error", "Error during method invocation: %s" % str(e))
                    givenresult = pickle.dumps(e)
                    clientreplycode = CR_EXCEPTION
                    unblocked = {}
                self.lock.acquire()
            except (TypeError, AttributeError) as t:
                if self.debug: self.logger.write("Execution Error",
                                                 "command not supported: %s" % str(commandname))
                if self.debug: self.logger.write("Execution Error", "%s" % str(t))

                givenresult = 'Method Does Not Exist: ', commandname
                clientreplycode = CR_EXCEPTION
                unblocked = {}
            clientreplies.append((clientreplycode, givenresult, unblocked))
        self.add_to_executed(commandbatch, clientreplies)

        if self.isleader and str(commandbatch.client) in self.connectionpool.poolbypeer.keys():
            self.send_replybatch_to_client(clientreplies, commandbatch)

        if self.nexttoexecute % GARBAGEPERIOD == 0 and self.isleader:
            mynumber = self.metacommandnumber
            self.metacommandnumber += 1
            garbagetuple = ("_garbage_collect", self.nexttoexecute)
            garbagecommand = Proposal(self.me, mynumber, garbagetuple)
            if self.leader_initializing:
                self.handle_client_command(garbagecommand, prepare=True)
            else:
                self.handle_client_command(garbagecommand)
        if self.debug: self.logger.write("State:", "returning from performcore!")

    def performcore(self, command, dometaonly=False, designated=False):
        """The core function that performs a given command in a slot number. It
        executes regular commands as well as META-level commands (commands related
        to the managements of the Paxos protocol) with a delay of WINDOW commands."""
        commandtuple = command.command
        if type(commandtuple) == str:
            commandname = commandtuple
            commandargs = []
        else:
            commandname = commandtuple[0]
            commandargs = commandtuple[1:]
        ismeta = (commandname in METACOMMANDS)
        noop = (commandname == "noop")
        send_result_to_client = True
        if self.debug: self.logger.write("State:", "---> Command: %s DoMetaOnly: %s IsMeta: %s"
                          % (command, dometaonly, ismeta))
        # Result triple
        clientreplycode, givenresult, unblocked = (-1, None, {})
        try:
            if dometaonly and not ismeta:
                return
            elif noop:
                method = getattr(self, NOOP)
                clientreplycode = CR_OK
                givenresult = "NOOP"
                unblocked = {}
                send_result_to_client = False
            elif dometaonly and ismeta:
                # execute a metacommand when the window has expired
                if self.debug: self.logger.write("State",
                                                 "commandname: %s args: %s" %
                                                 (commandname, str(commandargs)))
                method = getattr(self, commandname)
                clientreplycode = CR_META
                givenresult = self._apply_args_to_method(method, commandargs, command)
                unblocked = {}
                send_result_to_client = False
            elif not dometaonly and ismeta:
                # meta command, but the window has not passed yet,
                # so just mark it as executed without actually executing it
                # the real execution will take place when the window has expired
                self.add_to_executed(command, (CR_META, META, {}))
                return
            elif not dometaonly and not ismeta:
                # this is the workhorse case that executes most normal commands
                method = getattr(self.object, commandname)
                # Watch out for the lock release and acquire!
                self.lock.release()
                try:
                    givenresult = self._apply_args_to_method(method, commandargs, command)
                    clientreplycode = CR_OK
                    send_result_to_client = True
                except BlockingReturn as blockingretexp:
                    if self.debug: self.logger.write("State", "Blocking Client.")
                    givenresult = blockingretexp.returnvalue
                    clientreplycode = CR_BLOCK
                    send_result_to_client = True
                except UnblockingReturn as unblockingretexp:
                    if self.debug: self.logger.write("State", "Unblocking Client(s).")
                    # Get the information about the method call
                    # These will be used to update executed and
                    # to send reply message to the caller client
                    givenresult = unblockingretexp.returnvalue
                    unblocked = unblockingretexp.unblocked
                    clientreplycode = CR_OK
                    send_result_to_client = True
                    # If there are clients to be unblocked that have
                    # been blocked previously, send them unblock messages
                    for unblockedclientcommand in unblocked.iterkeys():
                        self.send_reply_to_client(CR_UNBLOCK, None, unblockedclientcommand)
                except Exception as e:
                    if self.debug: self.logger.write("Execution Error",
                                                     "Error during method invocation: %s" % str(e))
                    givenresult = pickle.dumps(e)
                    clientreplycode = CR_EXCEPTION
                    send_result_to_client = True
                    unblocked = {}
                self.lock.acquire()
        except (TypeError, AttributeError) as t:
            if self.debug: self.logger.write("Execution Error",
                                             "command not supported: %s" % str(command))
            if self.debug: self.logger.write("Execution Error", "%s" % str(t))

            self.logger.write("Execution Error",
                              "command not supported: %s" % str(command))
            self.logger.write("Execution Error", "%s" % str(t))

            givenresult = 'Method Does Not Exist: ', commandname
            clientreplycode = CR_EXCEPTION
            unblocked = {}
            send_result_to_client = True
        self.add_to_executed(command, (clientreplycode,givenresult,unblocked))

        if commandname not in METACOMMANDS:
            # if this client contacted me for this operation, return him the response
            if send_result_to_client and self.isleader and \
                    str(command.client) in self.connectionpool.poolbypeer.keys():
                self.send_reply_to_client(clientreplycode, givenresult, command)

        if self.nexttoexecute % GARBAGEPERIOD == 0 and self.isleader:
            mynumber = self.metacommandnumber
            self.metacommandnumber += 1
            garbagetuple = ("_garbage_collect", self.nexttoexecute, self.ballotnumber)
            garbagecommand = Proposal(self.me, mynumber, garbagetuple)
            if self.leader_initializing:
                self.handle_client_command(garbagecommand, prepare=True)
            else:
                self.handle_client_command(garbagecommand)
        if self.debug: self.logger.write("State:", "returning from performcore!")

    def send_replybatch_to_client(self, givenresult, command):
        if self.debug: self.logger.write("State", "Sending REPLY to CLIENT")
        clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                     {FLD_REPLY: givenresult,
                                      FLD_REPLYCODE: CR_BATCH,
                                      FLD_INRESPONSETO: command.clientcommandnumber})
        clientconn = self.connectionpool.get_connection_by_peer(command.client)
        if clientconn == None or clientconn.thesocket == None:
            if self.debug: self.logger.write("State", "Client connection does not exist.")
            return
        clientconn.send(clientreply)

    def send_reply_to_client(self, clientreplycode, givenresult, command):
        if self.debug: self.logger.write("State", "Sending REPLY to CLIENT")
        clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                     {FLD_REPLY: givenresult,
                                      FLD_REPLYCODE: clientreplycode,
                                      FLD_INRESPONSETO: command.clientcommandnumber})
        if self.debug: self.logger.write("State", "Clientreply: %s" % str(clientreply))
        clientconn = self.connectionpool.get_connection_by_peer(command.client)
        if clientconn == None or clientconn.thesocket == None:
            if self.debug: self.logger.write("State", "Client connection does not exist.")
            return
        clientconn.send(clientreply)

    def perform(self, msg, designated=False):
        """Take a given PERFORM message, add it to the set of decided commands,
        and call performcore to execute."""
        if self.debug: self.logger.write("State:", "Performing msg %s" % str(msg))
        if msg.commandnumber not in self.decisions:
            self.add_to_decisions(msg.commandnumber, msg.proposal)
        # If replica was using this commandnumber for a different proposal, initiate it again
        if msg.commandnumber in self.proposals and msg.proposal != self.proposals[msg.commandnumber]:
            self.pick_commandnumber_add_to_pending(self.proposals[msg.commandnumber])
            self.issue_pending_commands()

        while self.nexttoexecute in self.decisions:
            requestedcommand = self.decisions[self.nexttoexecute]
            if isinstance(requestedcommand, ProposalServerBatch):
                for command in requestedcommand.proposals:
                    self.execute_command(command, msg, designated)
            else:
                self.execute_command(requestedcommand, msg, designated)
            self.nexttoexecute += 1
            # the window just got bumped by one
            # check if there are pending commands, and issue one of them
            self.issue_pending_commands()
        if self.debug: self.logger.write("State", "Returning from PERFORM!")

    def execute_command(self, requestedcommand, msg, designated):
        # commands are executed one by one here.
        if requestedcommand in self.executed:
            if self.debug: self.logger.write("State", "Previously executed command %d."
                                             % self.nexttoexecute)
            # Execute the metacommand associated with this command
            if self.nexttoexecute > WINDOW:
                if self.debug: self.logger.write("State",
                                                 "performcore %d" % (self.nexttoexecute-WINDOW))
                self.performcore(self.decisions[self.nexttoexecute-WINDOW], True)
            # If we are a leader, we should send a reply to the client for this command
            # in case the client didn't receive the reply from the previous leader
            if self.isleader:
                prevrcode, prevresult, prevunblocked = self.executed[requestedcommand]
                if prevrcode == CR_BLOCK:
                    # As dictionary is not sorted we have to start from the beginning every time
                    for resultset in self.executed.itervalues():
                        if resultset[EXC_UNBLOCKED] == requestedcommand:
                            # This client has been UNBLOCKED
                            prevresult = None
                            prevrcode = CR_UNBLOCK
                # Send a reply to the client only if there was a client
                if type(requestedcommand.command) == str:
                    commandname = requestedcommand.command
                else:
                    commandname = requestedcommand.command[0]
                if (commandname not in METACOMMANDS) and (commandname != 'noop'):
                    if self.debug: self.logger.write("State", "Sending reply to client.")
                    self.send_reply_to_client(prevrcode, prevresult, requestedcommand)
        elif requestedcommand not in self.executed:
            if self.debug: self.logger.write("State", "executing command %s." % str(requestedcommand))
            # check to see if there was a metacommand precisely WINDOW commands ago
            # that should now take effect
            # We are calling performcore 2 times, the timing gets screwed plus this
            # is very unefficient
            if self.nexttoexecute > WINDOW:
                if self.debug: self.logger.write("State", "performcore %d" % \
                                                     (self.nexttoexecute-WINDOW))
                if not (isinstance(self.decisions[self.nexttoexecute-WINDOW], ProposalServerBatch) or
                        isinstance(self.decisions[self.nexttoexecute-WINDOW], ProposalClientBatch)):
                    self.performcore(self.decisions[self.nexttoexecute-WINDOW], True,
                                     designated=designated)
            if self.debug: self.logger.write("State", "performcore %s" % str(requestedcommand))
            if isinstance(requestedcommand, ProposalClientBatch):
                self.performcore_clientbatch(requestedcommand, designated=designated)
            else:
                self.performcore(requestedcommand, designated=designated)

    def pick_commandnumber_add_to_pending(self, givenproposal):
        givencommandnumber = self.find_commandnumber()
        self.add_to_pendingcommands(givencommandnumber, givenproposal)

    def issue_next_command(self):
        if self.debug: self.logger.write("State", "Pending commands: %s" % str(self.pendingcommands))
        if self.debug: self.logger.write("State", "Pending commandset: %s" % str(self.pendingcommandset))
        if len(self.pendingcommands) == 0:
            return
        smallestcommandnumber = sorted(self.pendingcommands.keys())[0]
        if smallestcommandnumber in self.pendingcommands:
            if self.active:
                self.do_command_propose_from_pending(smallestcommandnumber)
            else:
                self.do_command_prepare_from_pending(smallestcommandnumber)

    def issue_pending_commands(self):
        if self.debug: self.logger.write("State", "Pending commands: %s" % str(self.pendingcommands))
        if len(self.pendingcommands) == 0:
            return
        sortedcommandnumbers = sorted(self.pendingcommands.keys())
        for smallestcommandnumber in sortedcommandnumbers:
            if self.active:
                self.do_command_propose_from_pending(smallestcommandnumber)
            else:
                self.do_command_prepare_from_pending(smallestcommandnumber)

    def msg_perform(self, conn, msg):
        """received a PERFORM message, perform it and send an
        UPDATE message to the source if necessary"""
        self.perform(msg)

        if not self.stateuptodate:
            if self.debug: self.logger.write("State", "Updating..")
            if msg.commandnumber == 1:
                self.stateuptodate = True
                return
            updatemessage = create_message(MSG_UPDATE, self.me)
            conn.send(updatemessage)

    def msg_issue(self, conn, msg):
        self.issue_pending_commands()

    def msg_helo(self, conn, msg):
        if self.debug: self.logger.write("State", "Received HELO")
        # This is the first other replica, it should be added by this replica
        if len(self.replicas) == 0:
            if self.debug: self.logger.write("State", "Adding the first REPLICA")
            # Agree on adding self and the first replica:
            self.become_leader()
            # Add self
            self.replicas[self.me] = 0
            addcommand = self.create_add_command(self.me)
            self.pick_commandnumber_add_to_pending(addcommand)
            for i in range(WINDOW+3):
                noopcommand = self.create_noop_command()
                self.pick_commandnumber_add_to_pending(noopcommand)
            self.issue_pending_commands()
            # Add replica
            addcommand = self.create_add_command(msg.source)
            self.pick_commandnumber_add_to_pending(addcommand)
            for i in range(WINDOW+3):
                noopcommand = self.create_noop_command()
                self.pick_commandnumber_add_to_pending(noopcommand)
            self.issue_pending_commands()
        else:
            if self.isleader:
                if self.debug: self.logger.write("State", "Adding the new node")
                addcommand = self.create_add_command(msg.source)
                self.pick_commandnumber_add_to_pending(addcommand)
                for i in range(WINDOW+3):
                    noopcommand = self.create_noop_command()
                    self.pick_commandnumber_add_to_pending(noopcommand)
                self.issue_pending_commands()
            else:
                if self.debug: self.logger.write("State", "Not the leader, sending a HELOREPLY")
                if self.debug: self.logger.write("State", "Leader is %s" % str(self.find_leader()))
                heloreplymessage = create_message(MSG_HELOREPLY, self.me,
                                                  {FLD_LEADER: self.find_leader()})
                conn.send(heloreplymessage)

    def msg_update(self, conn, msg):
        """a replica needs to be updated on the set of past decisions, send caller's decisions"""
        # This should be done only if it has not been done recently.
        with self.recentlyupdatedpeerslock:
            if msg.source in self.recentlyupdatedpeers:
                return
        updatereplymessage = create_message(MSG_UPDATEREPLY, self.me,
                                            {FLD_DECISIONS: self.decisions})
        conn.send(updatereplymessage)
        with self.recentlyupdatedpeerslock:
            self.recentlyupdatedpeers.append(msg.source)

    def msg_updatereply(self, conn, msg):
        """merge decisions received with local decisions"""
        # If the node is already up-to-date, return.
        if self.stateuptodate:
            return
        for key,value in self.decisions.iteritems():
            if key in msg.decisions:
                assert self.decisions[key] == msg.decisions[key], "Update Error"
        # update decisions cumulatively
        self.decisions.update(msg.decisions)
        self.decisionset = set(self.decisions.values())
        self.usedcommandnumbers = self.usedcommandnumbers.union(set(self.decisions.keys()))
        # Execute the ones that we can execute
        while self.nexttoexecute in self.decisions:
            requestedcommand = self.decisions[self.nexttoexecute]
            if requestedcommand in self.executed:
                if self.debug: self.logger.write("State",
                                                 "Previously executed command %d."
                                                 % self.nexttoexecute)
                # Execute the metacommand associated with this command
                if self.nexttoexecute > WINDOW:
                    if self.debug: self.logger.write("State",
                                                     "performcore %d"
                                                     % (self.nexttoexecute-WINDOW))
                    self.performcore(self.decisions[self.nexttoexecute-WINDOW], True)
                self.nexttoexecute += 1
            elif requestedcommand not in self.executed:
                if self.debug: self.logger.write("State", "executing command %d." % self.nexttoexecute)

                if self.nexttoexecute > WINDOW:
                    if self.debug: self.logger.write("State", "performcore %d" % \
                                                         (self.nexttoexecute-WINDOW))
                    self.performcore(self.decisions[self.nexttoexecute-WINDOW], True)
                if self.debug: self.logger.write("State", "performcore %d" % self.nexttoexecute)
                self.performcore(self.decisions[self.nexttoexecute])
                self.nexttoexecute += 1
        # the window got bumped
        # check if there are pending commands, and issue one of them
        self.issue_pending_commands()
        if self.debug: self.logger.write("State", "Update is done!")
        self.stateuptodate = True

    def do_noop(self):
        if self.debug: self.logger.write("State:", "doing noop!")

    def _add_node(self, nodetype, nodename, epoch):
        nodetype = int(nodetype)
        if self.debug: self.logger.write("State", "Adding node: %s %s" % (node_names[nodetype],
                                                                          nodename))
        ipaddr,port = nodename.split(":")
        nodepeer = Peer(ipaddr,int(port),nodetype)
        self.replicas[nodepeer] = 0

        # update the revision if nameserver
        if self.isnameserver:
            self.nameserver.update()

        # if leader, increment epoch in the ballotnumber
        temp = (self.ballotnumber[BALLOTEPOCH]+1,
                self.ballotnumber[BALLOTNO],
                self.ballotnumber[BALLOTNODE])
        if self.debug: self.logger.write("State:", "Incremented EPOCH: %s" % str(temp))
        self.ballotnumber = temp

        # check leadership state
        if self.stateuptodate:
            chosenleader = self.find_leader()
            if chosenleader == self.me and not self.isleader:
                # become the leader
                if not self.stateuptodate:
                    self.leader_initializing = True
                self.become_leader()
            elif chosenleader != self.me and self.isleader:
                # unbecome the leader
                self.unbecome_leader()

    def _del_node(self, nodetype, nodename, epoch):
        nodetype = int(nodetype)
        if self.debug: self.logger.write("State",
                                         "Deleting node: %s %s" % (node_names[nodetype], nodename))
        ipaddr,port = nodename.split(":")
        nodepeer = Peer(ipaddr,int(port),nodetype)
        try:
            del self.replicas[nodepeer]
        except KeyError:
            if self.debug: self.logger.write("State",
                                             "Cannot delete node that is not in the view: %s %s"
                                             % (node_names[nodetype], nodename))
        # remove the node from nodesbeingdeleted
        if nodepeer in self.nodesbeingdeleted:
            self.nodesbeingdeleted.remove(nodepeer)

        # update the revision if nameserver
        if self.isnameserver:
            self.nameserver.update()

        # if leader, increment epoch in the ballotnumber
        temp = (self.ballotnumber[BALLOTEPOCH]+1,
                self.ballotnumber[BALLOTNO],
                self.ballotnumber[BALLOTNODE])
        if self.debug: self.logger.write("State:", "Incremented EPOCH: %s" % str(temp))
        self.ballotnumber = temp

        # if deleted node is a replica and this replica is uptodate
        # check leadership state
        if self.stateuptodate:
            chosenleader = self.find_leader()
            if chosenleader == self.me and not self.isleader:
                # become the leader
                if not self.stateuptodate:
                    self.leader_initializing = True
                self.become_leader()
            elif chosenleader != self.me and self.isleader:
                # unbecome the leader
                self.unbecome_leader()

        # if deleted node is self and the node is not just replaying history
        if nodepeer == self.me:
            if self.debug: self.logger.write("State", "I have been deleted from the view.")
            self._rejoin()

    def _garbage_collect(self, garbagecommandnumber, epoch):
        """ garbage collect """
        if self.debug: self.logger.write("State",
                          "Initiating garbage collection upto cmd#%d"
                          % garbagecommandnumber)
        snapshot = pickle.dumps(self.object)
        garbagemsg = create_message(MSG_GARBAGECOLLECT, self.me,
                                    {FLD_COMMANDNUMBER: garbagecommandnumber,
                                     FLD_SNAPSHOT: snapshot})
        self.send(garbagemsg,group=self.replicas)
        # do local garbage collection
        self.local_garbage_collect(garbagecommandnumber)

    def local_garbage_collect(self, commandnumber):
        """
        Truncates decisions, executed and proposals
        up to given commandnumber
        """
        keys = sorted(self.decisions.keys())
        # Sanity checking
        lastkey = keys[0]
        candelete = True
        for cmdno in keys:
            if cmdno == lastkey:
                lastkey += 1
            else:
                candelete = False
                break
        # Truncating
        if not candelete:
            return False
        for cmdno in keys:
            if cmdno < commandnumber:
                if self.decisions[cmdno] in self.executed:
                    del self.executed[self.decisions[cmdno]]
                    try:
                        del self.proposals[cmdno]
                    except:
                        pass
                    #del self.decisions[cmdno]
                else:
                    break
        return True

# LEADER STATE
    def become_leader(self):
        """Leader State
        - active: indicates if the Leader has a *good* ballotnumber
        - ballotnumber: the highest ballotnumber Leader has used
        - outstandingprepares: ResponseCollector dictionary for MSG_PREPARE,
        indexed by ballotnumber
        - outstandingproposes: ResponseCollector dictionary for MSG_PROPOSE,
        indexed by commandnumber
        - receivedclientrequests: commands received from clients as
        <(client,clientcommandnumber):command> mappings
        - backoff: backoff amount that is used to determine how much a leader should
        backoff during a collusion
        - commandgap: next commandnumber that will be used by this leader
        """
        if not self.isleader:
            self.isleader = True
            self.active = False
            self.outstandingprepares = {}
            self.outstandingproposes = {}
            self.receivedclientrequests = {}
            self.backoff = 0
            self.commandgap = 1
            self.leader_initializing = True

            backoff_thread = Thread(target=self.update_backoff)
            backoff_event.clear()
            backoff_thread.start()
            if self.debug: self.logger.write("State", "Becoming LEADER!")

    def unbecome_leader(self):
        """drop LEADER state, become a replica"""
        # fail-stop tolerance, coupled with retries in the client, mean that a
        # leader can at any time discard all of its internal state and the protocol
        # will still work correctly.
        if self.debug: self.logger.write("State:", "Unbecoming LEADER!")
        self.isleader = False
        backoff_event.set()

    def update_backoff(self):
        """used by the backoffthread to decrease the backoff amount by half periodically"""
        while not backoff_event.isSet():
            self.backoff = self.backoff/2
            backoff_event.wait(BACKOFFDECREASETIMEOUT)

    def detect_colliding_leader(self, ballotnumber):
        """detects a colliding leader from the highest ballotnumber received from replicas"""
        otherleader_addr,otherleader_port = ballotnumber[BALLOTNODE].split(":")
        otherleader = Peer(otherleader_addr, int(otherleader_port), NODE_REPLICA)
        return otherleader

    def leader_is_alive(self):
        """returns a tuple if the leader is alive and the currentleader"""
        currentleader = self.find_leader()
        if currentleader != self.me:
            if self.debug: self.logger.write("State", "Sending PING to %s" % str(currentleader))
            pingmessage = create_message(MSG_PING, self.me)
            successid = self.send(pingmessage, peer=currentleader)
            if successid < 0:
                self.replicas[currentleader] += 1
                return False, currentleader
        return True, currentleader

    def find_leader(self):
        """returns the minimum peer that is alive as the leader"""
        # sort the replicas first
        replicas = sorted(self.replicas.items(), key=lambda t: t[0])
        if self.debug: self.logger.write("State", "All Replicas in my view:%s" %str(replicas))
        for (replica,liveness) in replicas:
            if liveness == 0:
                del replicas
                if self.debug: self.logger.write("State", "Leader is %s" %str(replica))
                return replica
        del replicas
        if self.debug: self.logger.write("State", "Leader is me")
        return self.me

    def update_ballotnumber(self, seedballotnumber):
        """update the ballotnumber with a higher value than the given ballotnumber"""
        assert seedballotnumber[BALLOTEPOCH] == self.ballotnumber[BALLOTEPOCH], \
            "%s is in epoch %d instead of %d" % \
            (str(self.me), seedballotnumber[BALLOTEPOCH], self.ballotnumber[BALLOTEPOCH])
        temp = (self.ballotnumber[BALLOTEPOCH],
                seedballotnumber[BALLOTNO]+1,
                self.ballotnumber[BALLOTNODE])
        if self.debug: self.logger.write("State:", "Updated ballotnumber to %s" % str(temp))
        self.ballotnumber = temp

    def find_commandnumber(self):
        """returns the first gap in proposals and decisions combined"""
        while self.commandgap <= len(self.usedcommandnumbers):
            if self.commandgap in self.usedcommandnumbers:
                self.commandgap += 1
            else:
                if self.debug: self.logger.write("State", "Picked command number: %d" % self.commandgap)
                self.usedcommandnumbers.add(self.commandgap)
                return self.commandgap
        if self.debug: self.logger.write("State", "Picked command number: %d" % self.commandgap)
        self.usedcommandnumbers.add(self.commandgap)
        return self.commandgap

    def add_to_executed(self, key, value):
        self.executed[key] = value

    def add_to_decisions(self, key, value):
        self.decisions[key] = value
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.decisionset.add(item)
        else:
            self.decisionset.add(value)
        self.usedcommandnumbers.add(key)

    def add_to_proposals(self, key, value):
        self.proposals[key] = value
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.proposalset.add(item)
        else:
            self.proposalset.add(value)
        self.usedcommandnumbers.add(key)

    def add_to_pendingcommands(self, key, value):
        # If a Replica adds a pendingcommand before it is up to date
        # it assigns 1 as a commandnumber for a command. This later
        # gets overwritten when the same command is added later with
        # a higher commandnumber in the pendingcommandset but not in
        # in the pendingcommands as they have different keys. The case
        # that causes this to happen should be prevented, adding an if
        # case in this function will not fix the logic, will just get rid
        # of the symptom.
        self.pendingcommands[key] = value
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.pendingcommandset.add(item)
        else:
            self.pendingcommandset.add(value)

    def remove_from_executed(self, key):
        del self.executed[key]

    def remove_from_decisions(self, key):
        value = self.decisions[key]
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.decisionset.remove(item)
        else:
            self.decisionset.remove(value)
        del self.decisions[key]
        self.usedcommandnumbers.remove(key)
        self.commandgap = key

    def remove_from_proposals(self, key):
        value = self.proposals[key]
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.proposalset.remove(item)
        else:
            self.proposalset.remove(value)
        del self.proposals[key]
        self.usedcommandnumbers.remove(key)
        self.commandgap = key

    def remove_from_pendingcommands(self, key):
        value = self.pendingcommands[key]
        if isinstance(value, ProposalServerBatch):
            for item in value.proposals:
                self.pendingcommandset.remove(item)
        else:
            self.pendingcommandset.remove(value)
        del self.pendingcommands[key]

    def handle_client_command(self, givencommand, sendcount=1, prepare=False):
        """handle received command
        - if it has been received before check if it has been executed
        -- if it has been executed send the result
        -- if it has not been executed yet send INPROGRESS
        - if this request has not been received before initiate a Paxos round for the command"""
        if not self.isleader:
            if self.debug: self.logger.write("Error", "Should not have come here: Called to handle client command but not Leader.")
            clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                         {FLD_REPLY: '',
                                          FLD_REPLYCODE: CR_REJECTED,
                                          FLD_INRESPONSETO: givencommand.clientcommandnumber})
            if self.debug: self.logger.write("State", "Rejecting clientrequest: %s" % str(clientreply))
            conn = self.connectionpool.get_connection_by_peer(givencommand.client)
            if conn is not None:
                conn.send(clientreply)
            else:
                if self.debug: self.logger.write("Error", "Cannot create connection to client")
            return

        if sendcount > 0 and (givencommand.client,
                              givencommand.clientcommandnumber) in self.receivedclientrequests:
            if self.debug: self.logger.write("State", "Client request received previously:")
            if self.debug: self.logger.write("State", "Client: %s Commandnumber: %s Replicas: %s"
                                             % (str(givencommand.client),
                                                str(givencommand.clientcommandnumber),
                                                str(self.replicas)))
            # Check if the request has been executed
            if givencommand in self.executed:
                # send REPLY
                clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                             {FLD_REPLY: self.executed[givencommand][EXC_RESULT],
                                              FLD_REPLYCODE: self.executed[givencommand][EXC_RCODE],
                                              FLD_INRESPONSETO: givencommand.clientcommandnumber})
                if self.debug: self.logger.write("State", "Sending Clientreply: %s" % str(clientreply))
            # Check if the request is somewhere in the Paxos pipeline
            elif givencommand in self.pendingcommandset or \
                    givencommand in self.proposalset or \
                    givencommand in self.decisionset:
                # send INPROGRESS
                clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                             {FLD_REPLY: '',
                                              FLD_REPLYCODE: CR_INPROGRESS,
                                              FLD_INRESPONSETO: givencommand.clientcommandnumber})
                if self.debug: self.logger.write("State", "Sending INPROGRESS: %s\nReplicas: %s"
                                  % (str(clientreply),str(self.replicas)))
            conn = self.connectionpool.get_connection_by_peer(givencommand.client)
            if conn is not None:
                conn.send(clientreply)
            else:
                if self.debug: self.logger.write("Error", "Cannot create connection to client")
        else:
            # The caller haven't received this command before
            self.receivedclientrequests[(givencommand.client,
                                         givencommand.clientcommandnumber)] = givencommand
            if self.debug: self.logger.write("State",
                                             "Initiating command. Leader is active: %s" % self.active)
            self.pick_commandnumber_add_to_pending(givencommand)
            self.issue_pending_commands()

    def handle_client_command_batch(self, msgconnlist, prepare=False):
        """handle received command
        - if it has been received before check if it has been executed
        -- if it has been executed send the result
        -- if it has not been executed yet send INPROGRESS
        - if this request has not been received before initiate a Paxos round for the command"""
        if not self.isleader:
            if self.debug: self.logger.write("Error",
                              "Should not have come here: Not Leader.")
            for (msg,conn) in msgconnlist:
                clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                             {FLD_REPLY: '',
                                              FLD_REPLYCODE: CR_REJECTED,
                                              FLD_INRESPONSETO: msg.command.clientcommandnumber})
                conn.send(clientreply)
            return

        clientreply = None
        commandstohandle = []
        for (msg,conn) in msgconnlist:
            if msg.sendcount == 0:
                # The caller haven't received this command before
                self.receivedclientrequests[(msg.command.client,
                                             msg.command.clientcommandnumber)] = msg.command
                commandstohandle.append(msg.command)
                continue
            if (msg.command.client, msg.command.clientcommandnumber) in self.receivedclientrequests:
                if self.debug: self.logger.write("State", "Client request received previously:")
                # Check if the request has been executed
                if msg.command in self.executed:
                    # send REPLY
                    clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                                 {FLD_REPLY: self.executed[msg.command][EXC_RESULT],
                                                  FLD_REPLYCODE: self.executed[msg.command][EXC_RCODE],
                                                  FLD_INRESPONSETO: msg.command.clientcommandnumber})
                    if self.debug: self.logger.write("State", "Clientreply: %s" % str(clientreply))
                # Check if the request is somewhere in the Paxos pipeline
                elif msg.command in self.pendingcommandset or msg.command in self.proposalset \
                        or msg.command in self.decisionset:
                    # send INPROGRESS
                    clientreply = create_message(MSG_CLIENTREPLY, self.me,
                                                 {FLD_REPLY: '',
                                                  FLD_REPLYCODE: CR_INPROGRESS,
                                                  FLD_INRESPONSETO: msg.command.clientcommandnumber})
                    if self.debug: self.logger.write("State", "Clientreply: %s\nReplicas: %s"
                                      % (str(clientreply),str(self.replicas)))
                if clientreply:
                    conn.send(clientreply)
        if self.debug: self.logger.write("State", "Initiating a new command. Leader is active: %s" % self.active)
        # Check if batching is still required
        if len(commandstohandle) == 0:
            return
        elif len(commandstohandle) == 1:
            self.pick_commandnumber_add_to_pending(commandstohandle[0])
        else:
            self.pick_commandnumber_add_to_pending(ProposalServerBatch(commandstohandle))
        self.issue_pending_commands()

    def send_reject_to_client(self, conn, clientcommandnumber):
        conn.send(create_message(MSG_CLIENTREPLY, self.me,
                                 {FLD_REPLY: '',
                                  FLD_REPLYCODE: CR_REJECTED,
                                  FLD_INRESPONSETO: clientcommandnumber}))
    def msg_clientbatch(self, conn, msg):
        self.msg_clientrequest(conn, msg)

    def msg_clientrequest(self, conn, msg):
        """called holding self.lock
        handles clientrequest message received according to replica's state
        - if not leader: reject
        - if leader: add connection to client connections and handle request"""
        if not self.stateuptodate:
            return
        if self.isleader:
            # if leader, handle the clientrequest
            if self.token and msg.token != self.token:
                if self.debug: self.logger.write("Error", "Security Token mismatch.")
                self.send_reject_to_client(conn, msg.command.clientcommandnumber)
            else:
                if self.debug: self.logger.write("State", "I'm the leader, handling the request.")
                self.handle_client_command(msg.command, msg.sendcount,
                                           prepare=self.leader_initializing)
        else:
            leaderalive, leader = self.leader_is_alive()
            if leaderalive and leader != self.me:
                if self.debug: self.logger.write("State", "Not Leader: Rejecting CLIENTREQUEST")
                self.send_reject_to_client(conn, msg.command.clientcommandnumber)
            elif leader == self.me:
                # check if should become leader
                self.become_leader()
                if self.token and msg.token != self.token:
                    if self.debug: self.logger.write("Error", "Security Token mismatch.")
                    self.send_reject_to_client(conn, msg.command.clientcommandnumber)
                else:
                    self.handle_client_command(msg.command, msg.sendcount,
                                               prepare=self.leader_initializing)
            elif not leaderalive and self.find_leader() == self.me:
                # check if should become leader
                self.become_leader()
                if leader not in self.nodesbeingdeleted and leader in self.replicas:
                    # if leader is not already (being) deleted
                    # take old leader out of the configuration
                    if self.debug: self.logger.write("State",
                                                     "Taking old leader out of the configuration.")
                    self.nodesbeingdeleted.add(leader)
                    delcommand = self.create_delete_command(leader)
                    self.pick_commandnumber_add_to_pending(delcommand)
                    for i in range(WINDOW):
                        noopcommand = self.create_noop_command()
                        self.pick_commandnumber_add_to_pending(noopcommand)
                    self.issue_pending_commands()
                # Check token and answer to client
                if self.token and msg.token != self.token:
                    if self.debug: self.logger.write("Error", "Security Token mismatch.")
                    self.send_reject_to_client(conn, msg.command.clientcommandnumber)
                else:
                    self.handle_client_command(msg.command, msg.sendcount,
                                               prepare=self.leader_initializing)

    def msg_clientrequest_batch(self, msgconnlist):
        """called holding self.lock
        handles clientrequest messages that are batched together"""
        if self.isleader:
            # if leader, handle the clientrequest
            for (msg,conn) in msgconnlist:
                if self.token and msg.token != self.token:
                    if self.debug: self.logger.write("Error", "Security Token mismatch.")
                    self.send_reject_to_client(conn, msg.command.clientcommandnumber)
                    msgconnlist.remove((msg,conn))
            self.handle_client_command_batch(msgconnlist, prepare=self.leader_initializing)
        else:
            leaderalive, leader = self.leader_is_alive()
            if leaderalive and leader != self.me:
                if self.debug: self.logger.write("State", "Not Leader: Rejecting all CLIENTREQUESTS")
                for (msg,conn) in msgconnlist:
                    self.send_reject_to_client(conn, msg.command.clientcommandnumber)
            elif leader == self.me:
                # check if should become leader
                self.become_leader()
                for (msg,conn) in msgconnlist:
                    if self.token and msg.token != self.token:
                        if self.debug: self.logger.write("Error", "Security Token mismatch.")
                        self.send_reject_to_client(conn, msg.command.clientcommandnumber)
                        msgconnlist.remove((msg,conn))
                self.handle_client_command_batch(msgconnlist, prepare=self.leader_initializing)
            elif not leaderalive and self.find_leader() == self.me:
                self.become_leader()

                if leader not in self.nodesbeingdeleted and leader in self.replicas:
                    # if leader is not already (being) deleted
                    # take old leader out of the configuration
                    if self.debug: self.logger.write("State",
                                                     "Taking old leader out of the configuration.")
                    self.nodesbeingdeleted.add(leader)
                    delcommand = self.create_delete_command(leader)
                    self.pick_commandnumber_add_to_pending(delcommand)
                    for i in range(WINDOW):
                        noopcommand = self.create_noop_command()
                        self.pick_commandnumber_add_to_pending(noopcommand)
                # Check token and answer to client
                for (msg,conn) in msgconnlist:
                    if self.token and msg.token != self.token:
                        if self.debug: self.logger.write("Error", "Security Token mismatch.")
                        self.send_reject_to_client(conn, msg.command.clientcommandnumber)
                        msgconnlist.remove((msg,conn))
                self.handle_client_command_batch(msgconnlist, prepare=self.leader_initializing)

    def msg_incclientrequest(self, conn, msg):
        """handles inconsistent requests from the client"""
        commandtuple = tuple(msg.command.command)
        commandname = commandtuple[0]
        commandargs = commandtuple[1:]
        send_result_to_client = True
        try:
            method = getattr(self.object, commandname)
            try:
                givenresult = self._apply_args_to_method(method, commandargs, command)
                clientreplycode = CR_OK
                send_result_to_client = True
            except BlockingReturn as blockingretexp:
                givenresult = blockingretexp.returnvalue
                clientreplycode = CR_BLOCK
                send_result_to_client = True
            except UnblockingReturn as unblockingretexp:
                # Get the information about the method call
                # These will be used to update executed and
                # to send reply message to the caller client
                givenresult = unblockingretexp.returnvalue
                unblocked = unblockingretexp.unblocked
                clientreplycode = CR_OK
                send_result_to_client = True
                # If there are clients to be unblocked that have
                # been blocked previously send them unblock messages
                for unblockedclientcommand in unblocked.iterkeys():
                    self.send_reply_to_client(CR_UNBLOCK, None, unblockedclientcommand)
            except Exception as e:
                givenresult = pickle.dumps(e)
                clientreplycode = CR_EXCEPTION
                send_result_to_client = True
                unblocked = {}
        except (TypeError, AttributeError) as t:
            if self.debug: self.logger.write("Execution Error",
                                             "command not supported: %s" % (command))
            if self.debug: self.logger.write("Execution Error", "%s" % str(t))
            givenresult = 'COMMAND NOT SUPPORTED'
            clientreplycode = CR_EXCEPTION
            unblocked = {}
            send_result_to_client = True
        if commandname not in METACOMMANDS and send_result_to_client:
            self.send_reply_to_client(clientreplycode, givenresult, command)

    def msg_clientreply(self, conn, msg):
        """this only occurs in response to commands initiated by the shell"""
        return

## PAXOS METHODS
    def do_command_propose_from_pending(self, givencommandnumber):
        """Initiates givencommandnumber from pendingcommands list.
        Stage p2a.
        - Remove command from pending and transfer it to proposals
        - If no Replicas, retreat and return
        - Else start from the PROPOSE STAGE:
        -- create MSG_PROPOSE: message carries ballotnumber, commandnumber, proposal
        -- create ResponseCollector object for PROPOSE STAGE:
        ResponseCollector keeps the state related to MSG_PROPOSE
        -- add the ResponseCollector to the outstanding propose set
        -- send MSG_PROPOSE to Replica nodes
        """
        givenproposal = self.pendingcommands[givencommandnumber]
        self.remove_from_pendingcommands(givencommandnumber)
        self.add_to_proposals(givencommandnumber, givenproposal)
        recentballotnumber = self.ballotnumber
        if self.debug: self.logger.write("State", "Proposing command: %d:%s with ballotnumber %s"
                          % (givencommandnumber,givenproposal,str(recentballotnumber)))
        # Since we never propose a commandnumber that is beyond the window,
        # we can simply use the current replica set here
        prc = ResponseCollector(self.replicas, recentballotnumber,
                                givencommandnumber, givenproposal)
        if len(prc.quorum) == 0:
            if self.debug: self.logger.write("Error", "There are no Replicas, returning!")
            self.remove_from_proposals(givencommandnumber)
            self.pick_commandnumber_add_to_pending(givenproposal)
            return
        self.outstandingproposes[givencommandnumber] = prc
        propose = create_message(MSG_PROPOSE, self.me,
                                 {FLD_BALLOTNUMBER: recentballotnumber,
                                  FLD_COMMANDNUMBER: givencommandnumber,
                                  FLD_PROPOSAL: givenproposal,
                                  FLD_SERVERBATCH: isinstance(givenproposal, ProposalServerBatch)})
        self.send(propose, group=prc.quorum)

    def do_command_prepare_from_pending(self, givencommandnumber):
        """Initiates givencommandnumber from pendingcommands list.
        Stage p1a.
        - Remove command from pending and transfer it to proposals
        - If no Replicas, retreat and return
        - Else start from the PREPARE STAGE:
        -- create MSG_PREPARE: message carries the corresponding ballotnumber
        -- create ResponseCollector object for PREPARE STAGE:
        ResponseCollector keeps the state related to MSG_PREPARE
        -- add the ResponseCollector to the outstanding prepare set
        -- send MSG_PREPARE to Replica nodes
        """
        givenproposal = self.pendingcommands[givencommandnumber]
        self.remove_from_pendingcommands(givencommandnumber)
        self.add_to_proposals(givencommandnumber, givenproposal)
        newballotnumber = self.ballotnumber
        if self.debug: self.logger.write("State", "Preparing command: %d:%s with ballotnumber %s"
                          % (givencommandnumber, givenproposal,str(newballotnumber)))
        prc = ResponseCollector(self.replicas, newballotnumber,
                                givencommandnumber, givenproposal)
        if len(prc.quorum) == 0:
            if self.debug: self.logger.write("Error", "There are no Replicas, returning!")
            self.remove_from_proposals(givencommandnumber)
            self.pick_commandnumber_add_to_pending(givenproposal)
            return
        self.outstandingprepares[newballotnumber] = prc
        prepare = create_message(MSG_PREPARE, self.me,
                                 {FLD_BALLOTNUMBER: newballotnumber})
        self.send(prepare, group=prc.quorum)

## PAXOS ACCEPTOR MESSAGE HANDLERS
    def msg_prepare(self, conn, msg):
        """
        MSG_PREPARE is accepted only if it carries a ballotnumber greater
        than the highest ballotnumber Replica has ever received.

        Replies:
        - MSG_PREPARE_ADOPTED carries the ballotnumber that is received and
        all pvalues accepted thus far.
        - MSG_PREPARE_PREEMPTED carries the highest ballotnumber Replica
        has seen and all pvalues accepted thus far.
        """
        # this ballot should be strictly higher than previously accepted ballots
        if msg.ballotnumber >= self.quorumballotnumber:
            if self.debug: self.logger.write("Paxos State",
                              "prepare received with acceptable ballotnumber %s"
                              % str(msg.ballotnumber))

            self.quorumballotnumber = msg.ballotnumber
            self.last_accept_msg_id = msg.id
            replymsg = create_message(MSG_PREPARE_ADOPTED, self.me,
                                      {FLD_BALLOTNUMBER: self.quorumballotnumber,
                                       FLD_INRESPONSETO: msg.ballotnumber,
                                       FLD_PVALUESET: self.quorumaccepted.pvalues})
        # or else it should be a precise duplicate of the last request
        # in this case we do nothing
        elif msg.ballotnumber == self.quorumballotnumber and \
                msg.id == self.last_accept_msg_id:
            if self.debug: self.logger.write("Paxos State","message received before: %s" % msg)
            return
        else:
            if self.debug: self.logger.write("Paxos State",
                              ("prepare received with non-acceptable "
                               "ballotnumber %s ") % (str(msg.ballotnumber),))
            self.last_accept_msg_id = msg.id
            replymsg = create_message(MSG_PREPARE_PREEMPTED, self.me,
                                      {FLD_BALLOTNUMBER: self.quorumballotnumber,
                                       FLD_INRESPONSETO: msg.ballotnumber,
                                       FLD_PVALUESET: self.quorumaccepted.pvalues})

        if self.debug: self.logger.write("Paxos State", "prepare responding with %s"
                          % str(replymsg))
        conn.send(replymsg)

    def msg_propose(self, conn, msg):
        """
        MSG_PROPOSE is accepted only if it carries a ballotnumber greater
        than the highest ballotnumber Replica has received.

        Replies:
        - MSG_PROPOSE_ACCEPT carries ballotnumber and commandnumber received.
        - MSG_PROPOSE_REJECT carries the highest ballotnumber Replica has
        seen and the commandnumber that is received.
        """
        if msg.ballotnumber >= self.quorumballotnumber:
            if self.debug: self.logger.write("Paxos State",
                                             "propose received with acceptable ballotnumber %s"
                                             % str(msg.ballotnumber))
            self.quorumballotnumber = msg.ballotnumber
            newpvalue = PValue(msg.ballotnumber,msg.commandnumber,msg.proposal)
            self.quorumaccepted.add(newpvalue)
            replymsg = create_message(MSG_PROPOSE_ACCEPT, self.me,
                                      {FLD_BALLOTNUMBER: self.quorumballotnumber,
                                       FLD_INRESPONSETO: msg.ballotnumber,
                                       FLD_COMMANDNUMBER: msg.commandnumber})
            conn.send(replymsg)
            if self.durable:
                self.file.write(str(newpvalue))
                os.fsync(self.file)
        else:
            if self.debug: self.logger.write("Paxos State",
                                             "propose received with non-acceptable ballotnumber %s"
                                             % str(msg.ballotnumber))
            replymsg = create_message(MSG_PROPOSE_REJECT, self.me,
                                      {FLD_BALLOTNUMBER: self.quorumballotnumber,
                                       FLD_INRESPONSETO: msg.ballotnumber,
                                       FLD_COMMANDNUMBER: msg.commandnumber})
            conn.send(replymsg)

    def msg_garbagecollect(self, conn, msg):
        if self.debug: self.logger.write("Paxos State",
                                         "Doing garbage collection upto %d" % msg.commandnumber)
        success = self.quorumaccepted.truncateto(msg.commandnumber)
        if success:
            self.objectsnapshot = (msg.commandnumber,pickle.loads(msg.snapshot))
        else:
            if self.debug: self.logger.write("Garbage Collection Error",
                                             "Garbege Collection failed.")

## PAXOS REPLICA MESSAGE HANDLERS
    def msg_prepare_adopted(self, conn, msg):
        """MSG_PREPARE_ADOPTED is handled only if it belongs to an outstanding MSG_PREPARE,
        otherwise it is discarded.
        When MSG_PREPARE_ADOPTED is received, the corresponding ResponseCollector is retrieved
        and its state is updated accordingly.

        State Updates:
        - message is added to the received dictionary
        - the pvalue with the ResponseCollector's commandnumber is added to the possiblepvalueset
        - if naccepts is greater than the quorum size PREPARE STAGE is successful.
        -- Start the PROPOSE STAGE:
        --- create the pvalueset with highest ballotnumbers for distinctive commandnumbers
        --- update own proposals dictionary according to pmax dictionary
        --- remove the old ResponseCollector from the outstanding prepare set
        --- run the PROPOSE STAGE for each pvalue in proposals dictionary
        ---- create ResponseCollector object for PROPOSE STAGE: ResponseCollector keeps
        the state related to MSG_PROPOSE
        ---- add the new ResponseCollector to the outstanding propose set
        ---- create MSG_PROPOSE: message carries the corresponding ballotnumber, commandnumber and the proposal
        ---- send MSG_PROPOSE to the same Replica nodes from the PREPARE STAGE
        """
        if msg.inresponseto in self.outstandingprepares:
            prc = self.outstandingprepares[msg.inresponseto]
            prc.receivedcount += 1
            prc.receivedfrom.add(conn.peerid)
            if self.debug: self.logger.write("Paxos State",
                                             "got an accept for ballotno %s "\
                                             "commandno %s proposal %s with %d/%d"\
                                             % (prc.ballotnumber, prc.commandnumber, prc.proposal,
                                                prc.receivedcount, prc.ntotal))
            assert msg.ballotnumber == prc.ballotnumber, "[%s] MSG_PREPARE_ADOPTED cannot have non-matching ballotnumber" % self
            # add all the p-values from the response to the possiblepvalueset
            if msg.pvalueset is not None:
                prc.possiblepvalueset.union(msg.pvalueset)

            if prc.receivedcount >= prc.nquorum:
                if self.debug: self.logger.write("Paxos State", "suffiently many accepts on prepare!")
                # take this response collector out of the outstanding prepare set
                del self.outstandingprepares[msg.inresponseto]
                # choose pvalues with distinctive commandnumbers and highest ballotnumbers
                pmaxset = prc.possiblepvalueset.pmax()
                for commandnumber,proposal in pmaxset.iteritems():
                    self.add_to_proposals(commandnumber, proposal)
                # If the commandnumber we were planning to use is overwritten
                # we should try proposing with a new commandnumber
                if self.proposals[prc.commandnumber] != prc.proposal:
                    self.pick_commandnumber_add_to_pending(prc.proposal)
                    self.issue_pending_commands()
                for chosencommandnumber,chosenproposal in self.proposals.iteritems():
                    # send proposals for every outstanding proposal that is collected
                    if self.debug: self.logger.write("Paxos State", "Sending PROPOSE for %d, %s"
                                                     % (chosencommandnumber, chosenproposal))
                    newprc = ResponseCollector(prc.quorum, prc.ballotnumber,
                                               chosencommandnumber, chosenproposal)
                    self.outstandingproposes[chosencommandnumber] = newprc
                    propose = create_message(MSG_PROPOSE, self.me,
                                             {FLD_BALLOTNUMBER: prc.ballotnumber,
                                              FLD_COMMANDNUMBER: chosencommandnumber,
                                              FLD_PROPOSAL: chosenproposal,
                                              FLD_SERVERBATCH: isinstance(chosenproposal,
                                                                          ProposalServerBatch)})
                    self.send(propose, group=newprc.quorum)
                # As leader collected all proposals its state is up-to-date
                # and it is done initializing
                self.leader_initializing = False
                self.stateuptodate = True
                # become active
                self.active = True

    def msg_prepare_preempted(self, conn, msg):
        """MSG_PREPARE_PREEMPTED is handled only if it belongs to an outstanding MSG_PREPARE,
        otherwise it is discarded.
        A MSG_PREPARE_PREEMPTED causes the PREPARE STAGE to be unsuccessful, hence the current
        state is deleted and a ne PREPARE STAGE is initialized.

        State Updates:
        - kill the PREPARE STAGE that received a MSG_PREPARE_PREEMPTED
        -- remove the old ResponseCollector from the outstanding prepare set
        - remove the command from proposals, add it to pendingcommands
        - update the ballotnumber
        - initiate command
        """
        if msg.inresponseto in self.outstandingprepares:
            prc = self.outstandingprepares[msg.inresponseto]
            if self.debug: self.logger.write("Paxos State",
                                             "got a reject for ballotno %s proposal %s with %d/%d"
                                             % (prc.ballotnumber, prc.proposal,
                                                prc.receivedcount, prc.ntotal))
            # take this response collector out of the outstanding prepare set
            del self.outstandingprepares[msg.inresponseto]
            # become inactive
            self.active = False
            # handle reject
            self._handlereject(msg, prc)

    def msg_propose_accept(self, conn, msg):
        """MSG_PROPOSE_ACCEPT is handled only if it belongs to an outstanding MSG_PREPARE,
        otherwise it is discarded.
        When MSG_PROPOSE_ACCEPT is received, the corresponding ResponseCollector is retrieved
        and its state is updated accordingly.

        State Updates:
        - increment receivedcount
        - if receivedcount is greater than the quorum size, PROPOSE STAGE is successful.
        -- remove the old ResponseCollector from the outstanding prepare set
        -- create MSG_PERFORM: message carries the chosen commandnumber and proposal.
        -- send MSG_PERFORM to all Replicas and Leaders
        -- execute the command
        """
        if msg.commandnumber in self.outstandingproposes:
            prc = self.outstandingproposes[msg.commandnumber]
            if msg.inresponseto == prc.ballotnumber:
                prc.receivedcount += 1
                prc.receivedfrom.add(conn.peerid)
                if self.debug: self.logger.write("Paxos State",
                                                 "got an accept for proposal ballotno %s "\
                                                  "commandno %s proposal %s making %d/%d accepts" % \
                                                  (prc.ballotnumber, prc.commandnumber,
                                                   prc.proposal, prc.receivedcount, prc.ntotal))
                if prc.receivedcount >= prc.nquorum:
                    if self.debug: self.logger.write("Paxos State", "Agreed on %s" % str(prc.proposal))
                    # take this response collector out of the outstanding propose set
                    self.add_to_proposals(prc.commandnumber, prc.proposal)
                    # delete outstanding messages that caller does not need to check for anymore
                    del self.outstandingproposes[msg.commandnumber]

                    # now we can perform this action on the replicas
                    performmessage = create_message(MSG_PERFORM, self.me,
                                                    {FLD_COMMANDNUMBER: prc.commandnumber,
                                                     FLD_PROPOSAL: prc.proposal,
                                                     FLD_SERVERBATCH: isinstance(prc.proposal,
                                                                                 ProposalServerBatch),
                                                     FLD_CLIENTBATCH: isinstance(prc.proposal,
                                                                                 ProposalClientBatch),
                                                     FLD_DECISIONBALLOTNUMBER: prc.ballotnumber})

                    if self.debug: self.logger.write("Paxos State", "Sending PERFORM!")
                    if len(self.replicas) > 0:
                        self.send(performmessage, group=self.replicas)
                    self.perform(parse_message(performmessage), designated=True)
            if self.debug: self.logger.write("State", "returning from msg_propose_accept")

    def msg_propose_reject(self, conn, msg):
        """MSG_PROPOSE_REJECT is handled only if it belongs to an outstanding MSG_PROPOSE,
        otherwise it is discarded.
        A MSG_PROPOSE_REJECT causes the PROPOSE STAGE to be unsuccessful, hence the current
        state is deleted and a new PREPARE STAGE is initialized.

        State Updates:
        - kill the PROPOSE STAGE that received a MSG_PROPOSE_REJECT
        -- remove the old ResponseCollector from the outstanding prepare set
        - remove the command from proposals, add it to pendingcommands
        - update the ballotnumber
        - initiate command
        """
        if msg.commandnumber in self.outstandingproposes:
            prc = self.outstandingproposes[msg.commandnumber]
            if msg.inresponseto == prc.ballotnumber:
                if self.debug: self.logger.write("Paxos State",
                                                 "got a reject for proposal ballotno %s "\
                                                 "commandno %s proposal %s still %d "\
                                                 "out of %d accepts" % \
                                                 (prc.ballotnumber, prc.commandnumber,
                                                  prc.proposal, prc.receivedcount, prc.ntotal))
                # take this response collector out of the outstanding propose set
                del self.outstandingproposes[msg.commandnumber]
                # become inactive
                self.active = False
                # handle reject
                self._handlereject(msg, prc)

    def _handlereject(self, msg, prc):
        if self.debug: self.logger.write("State", "Handling the reject.")
        if msg.ballotnumber[BALLOTEPOCH] == self.ballotnumber[BALLOTEPOCH]:
            if self.debug: self.logger.write("State", "Updating ballotnumber and retrying.")
            # update the ballot number
            self.update_ballotnumber(msg.ballotnumber)
            # remove the proposal from proposals
            try:
                self.remove_from_proposals(prc.commandnumber)
            except KeyError:
                if self.debug: self.logger.write("State", "Proposal already removed.")
            self.pick_commandnumber_add_to_pending(prc.proposal)
            leader_causing_reject = self.detect_colliding_leader(msg.ballotnumber)
            if leader_causing_reject < self.me:
                # if caller lost to a replica whose name precedes its, back off more
                self.backoff += BACKOFFINCREASE
            if self.debug: self.logger.write("Paxos State",
                                             "There is another leader: %s" % \
                                                 str(leader_causing_reject))
            time.sleep(self.backoff)
            self.issue_pending_commands()

        # if the epoch is wrong, should collect the state and start from beginning
        else:
            if self.debug: self.logger.write("State", "In wrong EPOCH.")
            self._rejoin()

    def _rejoin(self):
        if not self.stateuptodate:
            return
        if self.debug: self.logger.write("State", "Rejoining.")
        # leadership state
        self.isleader = False
        self.leader_initializing = False
        self.stateuptodate = False
        # commands that are proposed: <commandnumber:command>
        self.proposals = {}
        self.proposalset = set()
        # commands that are received, not yet proposed: <commandnumber:command>
        self.pendingcommands = {}
        self.pendingcommandset = set()
        # nodes being added/deleted
        self.nodesbeingdeleted = set()
        # keep nodes that are recently updated
        self.recentlyupdatedpeerslock = Lock()
        self.recentlyupdatedpeers = []
        # send msg_helo to the replicas in the view
        for replicapeer in self.replicas:
            if replicapeer != self.me:
                if self.debug: self.logger.write("State", "Sending HELO to %s" %
                                                 str(replicapeer))
                helomessage = create_message(MSG_HELO, self.me)
                successid = self.send(helomessage, peer=replicapeer)

    def ping_neighbor(self):
        """used to ping neighbors periodically"""
        while True:
            # Go through all peers in the view
            for peer in self.replicas:
                successid = 0
                if peer == self.me:
                    continue
                # Check when last heard from peer
                if peer in self.nodeliveness:
                    nosound = time.time() - self.nodeliveness[peer]
                else:
                    # This peer did not send a message, send a PING
                    nosound = LIVENESSTIMEOUT + 1

                if nosound <= LIVENESSTIMEOUT:
                    # Peer is alive
                    self.replicas[peer] = 0
                    continue
                if nosound > LIVENESSTIMEOUT:
                    # Send PING to peer
                    if self.debug: self.logger.write("State", "Sending PING to %s" % str(peer))
                    pingmessage = create_message(MSG_PING, self.me)
                    successid = self.send(pingmessage, peer=peer)
                if successid < 0 or nosound > (2*LIVENESSTIMEOUT):
                    # The neighbor is not responding
                    if self.debug: self.logger.write("State",
                                                     "Neighbor not responding %s" % str(peer))
                    # Mark the neighbor
                    self.replicas[peer] += 1
                    # Check leadership
                    if not self.isleader and self.find_leader() == self.me:
                        if self.debug: self.logger.write("State",
                                                         "Becoming leader")
                        self.become_leader()
                    if self.isleader and \
                            peer not in self.nodesbeingdeleted and \
                            peer in self.replicas:
                        if self.debug: self.logger.write("State",
                                                         "Deleting node %s" % str(peer))
                        self.nodesbeingdeleted.add(peer)
                        delcommand = self.create_delete_command(peer)
                        self.pick_commandnumber_add_to_pending(delcommand)
                        for i in range(WINDOW):
                            noopcommand = self.create_noop_command()
                            self.pick_commandnumber_add_to_pending(noopcommand)
                        issuemsg = create_message(MSG_ISSUE, self.me)
                        self.send(issuemsg, peer=self.me)

            with self.recentlyupdatedpeerslock:
                self.recentlyupdatedpeers = []
            time.sleep(LIVENESSTIMEOUT)

    def create_delete_command(self, node):
        # include the ballotnumber in the metacommand
        mynumber = self.metacommandnumber
        self.metacommandnumber += 1
        nodename = node.addr + ":" + str(node.port)
        operationtuple = ("_del_node", node.type, nodename, self.ballotnumber)
        command = Proposal(self.me, mynumber, operationtuple)
        return command

    def create_add_command(self, node):
        mynumber = self.metacommandnumber
        self.metacommandnumber += 1
        nodename = node.addr + ":" + str(node.port)
        operationtuple = ("_add_node", node.type, nodename, self.ballotnumber)
        command = Proposal(self.me, mynumber, operationtuple)
        return command

    def create_noop_command(self):
        mynumber = self.metacommandnumber
        self.metacommandnumber += 1
        nooptuple = ("noop")
        command = Proposal(self.me, mynumber, nooptuple)
        return command

## SHELL COMMANDS
    def cmd_command(self, *args):
        """shell command [command]: initiate a new command."""
        try:
            cmdproposal = Proposal(self.me, random.randint(1,10000000), args[1:])
            self.handle_client_command(cmdproposal)
        except IndexError as e:
            print "command expects only one command: ", str(e)

    def cmd_goleader(self, args):
        """start Leader state"""
        self.become_leader()

    def cmd_showobject(self, args):
        """print replicated object information"""
        print self.object

    def cmd_info(self, args):
        """print next commandnumber to execute and executed commands"""
        print str(self)

    def cmd_proposals(self,args):
        """prints proposals"""
        for cmdnum,command in self.proposals.iteritems():
            print "%d: %s" % (cmdnum,str(command))

    def cmd_pending(self,args):
        """prints pending commands"""
        for cmdnum,command in self.pendingcommands.iteritems():
            print "%d: %s" % (cmdnum,str(command))

## TERMINATION METHODS
    def terminate_handler(self, signal, frame):
        self._graceexit()

    def _graceexit(self, exitcode=0):
        sys.stdout.flush()
        sys.stderr.flush()
        if hasattr(self, 'logger'): self.logger.close()
        os._exit(exitcode)

def main():
    replicanode = Replica()
    replicanode.startservice()
    signal.signal(signal.SIGINT, replicanode.terminate_handler)
    signal.signal(signal.SIGTERM, replicanode.terminate_handler)
    signal.pause()

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = responsecollector
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Class used to collect responses to both PREPARE and PROPOSE messages
@copyright: See LICENSE
'''
from concoord.pvalue import PValueSet
from concoord.pack import PValue

class ResponseCollector():
    """ResponseCollector keeps the state related to both MSG_PREPARE and
    MSG_PROPOSE.
    """
    def __init__(self, replicas, ballotnumber, commandnumber, proposal):
        """ResponseCollector state
        - ballotnumber: ballotnumber for the corresponding msg
        - commandnumber: commandnumber for the corresponding msg
        - proposal: proposal for the corresponding msg
        - quorum: group of replica nodes for the corresponding msg
        - sent: msgids for the messages that have been sent
        - received: dictionary that keeps <peer:reply> mappings
        - ntotal: # of replica nodes for the corresponding msg
        - nquorum: # of accepts needed for success
        - possiblepvalueset: Set of pvalues collected from replicas
        """
        self.ballotnumber = ballotnumber
        self.commandnumber = commandnumber
        self.proposal = proposal
        self.quorum = replicas
        self.receivedcount = 0
        self.receivedfrom = set()
        self.ntotal = len(self.quorum)
        self.nquorum = self.ntotal/2+1
        self.possiblepvalueset = PValueSet()

########NEW FILE########
__FILENAME__ = route53
# Author: Chris Moyer
#
# route53 is similar to sdbadmin for Route53, it's a simple
# console utility to perform the most frequent tasks with Route53
#
# Example usage.  Use route53 get after each command to see how the
# zone changes.
#
# Add a non-weighted record, change its value, then delete.  Default TTL:
#
# route53 add_record ZPO9LGHZ43QB9 rr.example.com A 4.3.2.1
# route53 change_record ZPO9LGHZ43QB9 rr.example.com A 9.8.7.6
# route53 del_record ZPO9LGHZ43QB9 rr.example.com A 9.8.7.6
#
# Add a weighted record with two different weights.  Note that the TTL
# must be specified as route53 uses positional parameters rather than
# option flags:
#
# route53 add_record ZPO9LGHZ43QB9 wrr.example.com A 1.2.3.4 600 foo9 10
# route53 add_record ZPO9LGHZ43QB9 wrr.example.com A 4.3.2.1 600 foo8 10
#
# route53 change_record ZPO9LGHZ43QB9 wrr.example.com A 9.9.9.9 600 foo8 10
#
# route53 del_record ZPO9LGHZ43QB9 wrr.example.com A 1.2.3.4 600 foo9 10
# route53 del_record ZPO9LGHZ43QB9 wrr.example.com A 9.9.9.9 600 foo8 10
#
# Add a non-weighted alias, change its value, then delete.  Alaises inherit
# their TTLs from the backing ELB:
#
# route53 add_alias ZPO9LGHZ43QB9 alias.example.com A Z3DZXE0Q79N41H lb-1218761514.us-east-1.elb.amazonaws.com.
# route53 change_alias ZPO9LGHZ43QB9 alias.example.com. A Z3DZXE0Q79N41H lb2-1218761514.us-east-1.elb.amazonaws.com.
# route53 delete_alias ZPO9LGHZ43QB9 alias.example.com. A Z3DZXE0Q79N41H lb2-1218761514.us-east-1.elb.amazonaws.com.

def _print_zone_info(zoneinfo):
    print "="*80
    print "| ID:   %s" % zoneinfo['Id'].split("/")[-1]
    print "| Name: %s" % zoneinfo['Name']
    print "| Ref:  %s" % zoneinfo['CallerReference']
    print "="*80
    print zoneinfo['Config']
    print

def create(conn, hostname, caller_reference=None, comment=''):
    """Create a hosted zone, returning the nameservers"""
    response = conn.create_hosted_zone(hostname, caller_reference, comment)
    print "Pending, please add the following Name Servers:"
    for ns in response.NameServers:
        print "\t", ns

def delete_zone(conn, hosted_zone_id):
    """Delete a hosted zone by ID"""
    response = conn.delete_hosted_zone(hosted_zone_id)
    print response

def ls(conn):
    """List all hosted zones"""
    response = conn.get_all_hosted_zones()
    for zoneinfo in response['ListHostedZonesResponse']['HostedZones']:
        _print_zone_info(zoneinfo)

def get(conn, hosted_zone_id, type=None, name=None, maxitems=None):
    """Get all the records for a single zone"""
    response = conn.get_all_rrsets(hosted_zone_id, type, name, maxitems=maxitems)
    # If a maximum number of items was set, we limit to that number
    # by turning the response into an actual list (copying it)
    # instead of allowing it to page
    if maxitems:
        response = response[:]
    print '%-40s %-5s %-20s %s' % ("Name", "Type", "TTL", "Value(s)")
    for record in response:
        print '%-40s %-5s %-20s %s' % (record.name, record.type, record.ttl, record.to_print())

def _add_del(conn, hosted_zone_id, change, name, type, identifier, weight, values, ttl, comment):
    from boto.route53.record import ResourceRecordSets
    changes = ResourceRecordSets(conn, hosted_zone_id, comment)
    change = changes.add_change(change, name, type, ttl,
                                identifier=identifier, weight=weight)
    for value in values.split(','):
        change.add_value(value)
    print changes.commit()

def _add_del_alias(conn, hosted_zone_id, change, name, type, identifier, weight, alias_hosted_zone_id, alias_dns_name, comment):
    from boto.route53.record import ResourceRecordSets
    changes = ResourceRecordSets(conn, hosted_zone_id, comment)
    change = changes.add_change(change, name, type,
                                identifier=identifier, weight=weight)
    change.set_alias(alias_hosted_zone_id, alias_dns_name)
    print changes.commit()

def add_record(conn, hosted_zone_id, name, type, values, ttl=600,
               identifier=None, weight=None, comment=""):
    """Add a new record to a zone.  identifier and weight are optional."""
    _add_del(conn, hosted_zone_id, "CREATE", name, type, identifier,
             weight, values, ttl, comment)

def del_record(conn, hosted_zone_id, name, type, values, ttl=600,
               identifier=None, weight=None, comment=""):
    """Delete a record from a zone: name, type, ttl, identifier, and weight must match."""
    _add_del(conn, hosted_zone_id, "DELETE", name, type, identifier,
             weight, values, ttl, comment)

def add_alias(conn, hosted_zone_id, name, type, alias_hosted_zone_id,
              alias_dns_name, identifier=None, weight=None, comment=""):
    """Add a new alias to a zone.  identifier and weight are optional."""
    _add_del_alias(conn, hosted_zone_id, "CREATE", name, type, identifier,
                   weight, alias_hosted_zone_id, alias_dns_name, comment)

def del_alias(conn, hosted_zone_id, name, type, alias_hosted_zone_id,
              alias_dns_name, identifier=None, weight=None, comment=""):
    """Delete an alias from a zone: name, type, alias_hosted_zone_id, alias_dns_name, weight and identifier must match."""
    _add_del_alias(conn, hosted_zone_id, "DELETE", name, type, identifier,
                   weight, alias_hosted_zone_id, alias_dns_name, comment)

def change_record(conn, hosted_zone_id, name, type, newvalues, ttl=600,
                   identifier=None, weight=None, comment=""):
    """Delete and then add a record to a zone.  identifier and weight are optional."""
    from boto.route53.record import ResourceRecordSets
    changes = ResourceRecordSets(conn, hosted_zone_id, comment)
    # Assume there are not more than 10 WRRs for a given (name, type)
    responses = conn.get_all_rrsets(hosted_zone_id, type, name, maxitems=10)
    for response in responses:
        if response.name != name or response.type != type:
            continue
        if response.identifier != identifier or response.weight != weight:
            continue
        change1 = changes.add_change("DELETE", name, type, response.ttl,
                                     identifier=response.identifier,
                                     weight=response.weight)
        for old_value in response.resource_records:
            change1.add_value(old_value)

    change2 = changes.add_change("CREATE", name, type, ttl,
            identifier=identifier, weight=weight)
    for new_value in newvalues.split(','):
        change2.add_value(new_value)
    print changes.commit()

def change_alias(conn, hosted_zone_id, name, type, new_alias_hosted_zone_id, new_alias_dns_name, identifier=None, weight=None, comment=""):
    """Delete and then add an alias to a zone.  identifier and weight are optional."""
    from boto.route53.record import ResourceRecordSets
    changes = ResourceRecordSets(conn, hosted_zone_id, comment)
    # Assume there are not more than 10 WRRs for a given (name, type)
    responses = conn.get_all_rrsets(hosted_zone_id, type, name, maxitems=10)
    for response in responses:
        if response.name != name or response.type != type:
            continue
        if response.identifier != identifier or response.weight != weight:
            continue
        change1 = changes.add_change("DELETE", name, type,
                                     identifier=response.identifier,
                                     weight=response.weight)
        change1.set_alias(response.alias_hosted_zone_id, response.alias_dns_name)
    change2 = changes.add_change("CREATE", name, type, identifier=identifier, weight=weight)
    change2.set_alias(new_alias_hosted_zone_id, new_alias_dns_name)
    print changes.commit()

def help(conn, fnc=None):
    """Prints this help message"""
    import inspect
    self = sys.modules['__main__']
    if fnc:
        try:
            cmd = getattr(self, fnc)
        except:
            cmd = None
        if not inspect.isfunction(cmd):
            print "No function named: %s found" % fnc
            sys.exit(2)
        (args, varargs, varkw, defaults) = inspect.getargspec(cmd)
        print cmd.__doc__
        print "Usage: %s %s" % (fnc, " ".join([ "[%s]" % a for a in args[1:]]))
    else:
        print "Usage: route53 [command]"
        for cname in dir(self):
            if not cname.startswith("_"):
                cmd = getattr(self, cname)
                if inspect.isfunction(cmd):
                    doc = cmd.__doc__
                    print "\t%-20s  %s" % (cname, doc)
    sys.exit(1)

if __name__ == "__main__":
    import boto
    import sys
    conn = boto.connect_route53()
    self = sys.modules['__main__']
    if len(sys.argv) >= 2:
        try:
            cmd = getattr(self, sys.argv[1])
        except:
            cmd = None
        args = sys.argv[2:]
    else:
        cmd = help
        args = []
    if not cmd:
        cmd = help
    try:
        cmd(conn, *args)
    except TypeError, e:
        print e
        help(conn, cmd.__name__)

########NEW FILE########
__FILENAME__ = safetychecker
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Checks the safety of the client object
@copyright: See LICENSE
'''
import ast, _ast
DEBUG = False

blacklist = ["open","setattr","getattr","compile","exec","eval","execfile", "globals", "type"]

class SafetyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True
        self.classes = []

    def generic_visit(self, node):
        if DEBUG:
            print "---", ast.dump(node)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Import(self, node):
        self.safe = False
        print "%d | No imports allowed: %s --> EXIT" % (node.lineno,node.names[0].name)

    def visit_ImportFrom(self, node):
        self.safe = False
        print "%d | No imports allowed: %s --> EXIT" % (node.lineno,node.module)

    def visit_Exec(self, node):
        self.safe = False
        print "%d | Exec not allowed --> EXIT" % node.lineno

    def visit_Call(self, node):
        if DEBUG:
            print 'Call : '
        self.check_functioncall(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        if DEBUG:
            print 'ClassDef : ', node.name
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if DEBUG:
            print 'Name :', node.id

    def visit_Num(self, node):
        if DEBUG:
            print 'Num :', node.__dict__['n']

    def visit_Str(self, node):
        if DEBUG:
            print "Str :", node.s

    def visit_Print(self, node):
        if DEBUG:
            print "Print :"
        self.generic_visit(node)

    def visit_Assign(self, node):
        if DEBUG:
            print "Assign :"
        self.check_assignment(node)
        self.generic_visit(node)

    def visit_Expr(self, node):
        if DEBUG:
            print "Expr :"
        self.generic_visit(node)

    def check_assignment(self, node):
        if DEBUG:
            print "Checking assignment.."
        global blacklist
        if type(node.value).__name__ == 'Name':
            if node.value.id in blacklist:
                self.safe = False
                print "%d | Function assignment: %s --> EXIT" % (node.lineno,node.value.id)

    def check_functioncall(self, node):
        if DEBUG:
            print "Checking function call.."
        global blacklist
        isopen = False
        for fname,fvalue in ast.iter_fields(node):
            if DEBUG:
                print fname, " ", fvalue
            if fname == 'func' and type(fvalue).__name__ == 'Name':
                if fvalue.id == 'open':
                    isopen = True
                elif fvalue.id in blacklist:
                    self.safe = False
                    print "%d | Forbidden function call: %s --> EXIT" % (node.lineno,fvalue.id)
            if fname == 'args' and isopen:
                for arg in fvalue:
                    if type(arg).__name__ == 'Str':
                        if arg.__dict__['s'] == 'w' or arg.__dict__['s'] == 'a':
                            self.safe = False
                            print "%d | Write to file --> EXIT" % node.lineno
                    elif type(arg).__name__ == 'Name':
                        self.safe = False
                        print "%d | File operation with variable argument: %s --> EXIT" % (node.lineno,arg.id)

def main():
    path = "./safetytest.py"
    astnode = compile(open(path, 'rU').read(),"<string>","exec",_ast.PyCF_ONLY_AST)
    v = SafetyVisitor()
    v.visit(astnode)

if __name__=='__main__':
    main()


########NEW FILE########
__FILENAME__ = test_partition
# Creates a partition and tests ConCoord's behavior.
# Create 3 replicas
# Create 2 partitions P1 and P2 as follows:
# P1: 1 Replica: Minority
# P2: 2 Replicas: Majority
# Since P2 has majority of the replicas, P2 should make progress
import sys, os
import signal, time
import socket, struct
import cPickle as pickle
import subprocess
from concoord.message import *
from concoord.proxy.counter import Counter
from concoord.exception import ConnectionError

class TimeoutException(Exception):
    pass

def get_replica_status(replica):
    # Create Status Message
    sm = create_message(MSG_STATUS, None)
    messagestr = msgpack.packb(sm)
    message = struct.pack("I", len(messagestr)) + messagestr

    addr, port = replica.split(':')
    try:
        # Open a socket
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        s.settimeout(22)
        s.connect((addr,int(port)))
        s.send(message)
        lstr = s.recv(4)
        msg_length = struct.unpack("I", lstr[0:4])[0]
        msg = ''
        while len(msg) < msg_length:
            chunk = s.recv(msg_length-len(msg))
            msg = msg + chunk
            if chunk == '':
                break
        s.close()
        return pickle.loads(msg)
    except:
        print "Cannot connect to Replica  %s:%d" % (addr, int(port))
        return None

def timeout(timeout):
    def timeout_function(f):
        def f2(*args):
            def timeout_handler(signum, frame):
                raise TimeoutException()

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout) # trigger alarm in timeout seconds
            try:
                retval = f(*args)
            except TimeoutException:
                return False
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_function

def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

@timeout(30)
def connect_to_minority():
    c_minority = Counter('127.0.0.1:14000')
    for i in range(50):
        c_minority.increment()
    # This method will timeout before it reaches here.
    print "Counter value: %d" % c_minority.getvalue()
    return True

def test_partition():
    processes = []
    p1_pids = []
    p2_pids = []

    # P1 Nodes
    print "Running replica 0"
    p = subprocess.Popen(['concoord', 'replica',
                          '-o', 'concoord.object.counter.Counter',
                          '-a', '127.0.0.1', '-p', '14000'])
    processes.append(p)
    p1_pids.append(p.pid)

    # P2 Nodes
    print "Running replica 1"
    p = subprocess.Popen(['concoord', 'replica',
                          '-o', 'concoord.object.counter.Counter',
                          '-a', '127.0.0.1', '-p', '14001',
                          '-b', '127.0.0.1:14000'])
    processes.append(p)
    p2_pids.append(p.pid)

    print "Running replica 2"
    p = subprocess.Popen(['concoord', 'replica',
                          '-o', 'concoord.object.counter.Counter',
                          '-a', '127.0.0.1', '-p', '14002',
                          '-b', '127.0.0.1:14000'])
    processes.append(p)
    p2_pids.append(p.pid)

    # Give the system some time to initialize
    time.sleep(10)

    # This client can only connect to the replicas in this partition
    c_P1 = Counter('127.0.0.1:14000')
    c_P2 = Counter('127.0.0.1:14001,127.0.0.1:14002')
    # The client should work
    print "Sending requests to the leader"
    for i in range(50):
        c_P1.increment()
    print "Counter value after 50 increments: %d" % c_P1.getvalue()

    # Save iptables settings for later recovery
    with open('test.iptables.rules', 'w') as output:
        subprocess.Popen(['sudo', 'iptables-save'], stdout=output)

    # Start partition
    iptablerules = []
    p1_ports = [14000]
    p2_ports = [14001, 14002]
    connectedports = []

    # Find all ports that R1, A1 and A2 and have connecting to R0 and A0
    for port in p1_ports:
        for pid in p2_pids:
            p1 = subprocess.Popen(['lsof', '-w', '-a', '-p%d'%pid, '-i4'], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['grep', ':%d'%port], stdin=p1.stdout, stdout=subprocess.PIPE)
            output = p2.communicate()[0]
            if output:
                connectedports.append(output.split()[8].split('->')[0].split(':')[1])

    # Block all traffic to/from R0 and A0 from other nodes but each other
    for porttoblock in connectedports:
        iptablerules.append(subprocess.Popen(['sudo', 'iptables',
                                              '-I', 'INPUT',
                                              '-p', 'tcp',
                                              '--dport', '14000',
                                              '--sport', porttoblock,
                                              '-j', 'DROP']))

    for porttoblock in p2_ports:
        iptablerules.append(subprocess.Popen(['sudo', 'iptables',
                                              '-I', 'INPUT',
                                              '-p', 'tcp',
                                              '--dport', '%d'%porttoblock,
                                              '--sport', '14000',
                                              '-j', 'DROP']))

    print "Created the partition. Waiting for system to stabilize."
    time.sleep(20)

    # c_P2 should make progress
    print "Connecting to the majority, which should have a new leader."
    for i in range(50):
        c_P2.increment()
    print "Counter value after 50 more increments: %d" % c_P2.getvalue()
    if c_P2.getvalue() == 100:
        print "SUCCESS: Majority made progress."

    print "Connecting to the minority, which should not make progress."
    if connect_to_minority():
        print "===== TEST FAILED ====="
        sys.exit('Minority made progress.')
    print "SUCCESS: Minority did not make progress."

    print "Ending partition."
    # End partition
    with open('test.iptables.rules', 'r') as input:
        subprocess.Popen(['sudo', 'iptables-restore'], stdin=input)
    subprocess.Popen(['sudo', 'rm', 'test.iptables.rules'])

    time.sleep(40)
    # c_P1 should make progress
    print "Connecting to the old leader."
    if not connect_to_minority():
        print "===== TEST FAILED ====="
        print "Old leader could not recover after partition."
        print get_replica_status('127.0.0.1:14000')
        for p in (processes):
            p.kill()
        return True
    if c_P1.getvalue() == 150:
        print "SUCCESS: Old leader recovered."
        print "===== TEST PASSED ====="
    else:
        print "FAILURE: Old leader lost some client commands."
        print "===== TEST FAILED ====="
    print get_replica_status('127.0.0.1:14000')

    for p in (processes):
        p.kill()
    return True

def main():
    if not which('iptables'):
        sys.exit('Test requires iptables to run')

    if not os.geteuid() == 0:
        sys.exit('Test must be run as root')

    test_partition()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_replicacomeback
# Create 5 replicas and kill them in turn, until 1 is left
# Every time kill the leader
# Then bring the leaders back in the reverse order, forcing 4 handovers.
import signal, time
import subprocess
import time
from concoord.proxy.counter import Counter

class TimeoutException(Exception):
    pass

def timeout(timeout):
    def timeout_function(f):
        def f2(*args):
            def timeout_handler(signum, frame):
                raise TimeoutException()

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout) # trigger alarm in timeout seconds
            try:
                retval = f(*args)
            except TimeoutException:
                return False
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_function

@timeout(120)
def test_failure(numreplicas):
    replicas = []
    replicanames = []

    print "Running replica 0"
    replicas.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '14000']))
    replicanames.append("127.0.0.1:14000")

    for i in range(1, numreplicas):
        print "Running replica %d" %i
        replicas.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '1400%d'%i,
                                      '-b', '127.0.0.1:14000']))
        replicanames.append("127.0.0.1:1400%d"%i)

    # Give the system sometime to initialize
    time.sleep(10)

    replicastring = ','.join(replicanames)
    # Test Clientproxy operations
    c = Counter(replicastring)
    for i in range(50):
        c.increment()
    print "Counter value after 50 increments: %d" % c.getvalue()

    # Start kiling replicas
    print "Killing replicas one by one."
    for i in range((numreplicas-1)/2):
        print "Killing replica %d" %i
        replicas[i].kill()

        # Clientproxy operations should still work
        c = Counter('127.0.0.1:1400%d'%(i+1))
        for i in range(50):
            c.increment()
        print "Counter value after 50 more increments: %d" % c.getvalue()

    # Start bringing replicas back
    for i in reversed(xrange((numreplicas-1)/2)):
        print "Running replica %d" %i
        replicas.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '1400%d'%i,
                                      '-b', '127.0.0.1:1400%d'%(i+1)]))
        time.sleep(10)
        # Clientproxy operations should still work
        connected = False
        while(not connected):
            try:
                c = Counter('127.0.0.1:1400%d'%i)
            except:
                continue
            connected = True

        for i in range(50):
            c.increment()
        print "Counter value after 50 more increments: %d" % c.getvalue()

    for p in (replicas):
        p.kill()
    return True

def main():
    print "===== TEST 3 REPLICAS ====="
    s = "PASSED" if test_failure(3) else "TIMED OUT"
    print "===== TEST %s =====" % s
    print "===== TEST 5 REPLICAS ====="
    s = "PASSED" if test_failure(5) else "TIMED OUT"
    print "===== TEST %s =====" % s
    print "===== TEST 7 REPLICAS ====="
    s = "PASSED" if test_failure(7) else "TIMED OUT"
    print "===== TEST %s =====" % s

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_replicacrashfailure
# Create 5 replicas and kill them in turn, until 1 is left
# Every time kill the leader
import signal, time
import subprocess
import time
from concoord.proxy.counter import Counter

class TimeoutException(Exception):
    pass

def timeout(timeout):
    def timeout_function(f):
        def f2(*args):
            def timeout_handler(signum, frame):
                raise TimeoutException()

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout) # trigger alarm in timeout seconds
            try:
                retval = f(*args)
            except TimeoutException:
                return False
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_function

@timeout(100)
def test_failure(numreplicas):
    replicas = []
    replicanames = []

    print "Running replica 0"
    replicas.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '14000']))
    replicanames.append("127.0.0.1:14000")

    for i in range(1,numreplicas):
        print "Running replica %d" %i
        replicas.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '1400%d'%i,
                                      '-b', '127.0.0.1:14000']))
        replicanames.append("127.0.0.1:1400%d"%i)

    # Give the system some time to initialize
    time.sleep(10)

    replicastring = ','.join(replicanames)
    # Test Clientproxy operations
    c = Counter(replicastring)
    for i in range(100):
        c.increment()
    print "Counter value after 100 increments: %d" % c.getvalue()

    # Start kiling replicas
    for i in range((numreplicas-1)/2):
        print "Killing replica %d" %i
        replicas[i].kill()

        # Clientproxy operations should still work
        for i in range(100):
            c.increment()
        print "Counter value after 100 more increments: %d" % c.getvalue()

    for p in (replicas):
        p.kill()
    return True

def main():
    print "===== TEST 3 REPLICAS ====="
    s = "PASSED" if test_failure(3) else "TIMED OUT"
    print "===== TEST %s =====" % s
    print "===== TEST 5 REPLICAS ====="
    s = "PASSED" if test_failure(5) else "TIMED OUT"
    print "===== TEST %s =====" % s
    print "===== TEST 7 REPLICAS ====="
    s = "PASSED" if test_failure(7) else "TIMED OUT"
    print "===== TEST %s =====" % s

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_timeout
# Cuts the connection to the leader and tests liveness
import sys,os
import signal, time
import subprocess
import time
from concoord.proxy.counter import Counter
from concoord.exception import ConnectionError

class TimeoutException(Exception):
    pass

def timeout(timeout):
    def timeout_function(f):
        def f2(*args):
            def timeout_handler(signum, frame):
                raise TimeoutException()

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout) # trigger alarm in timeout seconds
            try:
                retval = f(*args)
            except TimeoutException:
                return False
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_function

def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

@timeout(30)
def connect_to_leader():
    c_leader = Counter('127.0.0.1:14000')
    print "Connecting to old leader"
    for i in range(100):
        c_leader.increment()
    # This method will timeout before it reaches here.
    print "Client Made Progress: Counter value: %d" % c_minority.getvalue()
    return True

def test_timeout():
    numreplicas = 3
    processes = []

    print "Running replica 0"
    processes.append(subprocess.Popen(['concoord', 'replica',
                                      '-o', 'concoord.object.counter.Counter',
                                      '-a', '127.0.0.1', '-p', '14000']))

    for i in range(1, numreplicas):
        print "Running replica %d" %i
        processes.append(subprocess.Popen(['concoord', 'replica',
                                           '-o', 'concoord.object.counter.Counter',
                                           '-a', '127.0.0.1', '-p', '1400%d'%i,
                                           '-b', '127.0.0.1:14000']))

    # Give the system some time to initialize
    time.sleep(10)

    # This client can only connect to the replicas in this partition
    c_P1 = Counter('127.0.0.1:14000', debug = True)
    c_P2 = Counter('127.0.0.1:14001, 127.0.0.1:14002')
    # The client should work
    print "Sending requests to the leader"
    for i in range(100):
        c_P1.increment()
    print "Counter value after 100 increments: %d" % c_P1.getvalue()

    # Save iptables settings for later recovery
    with open('test.iptables.rules', 'w') as output:
        subprocess.Popen(['sudo', 'iptables-save'], stdout=output)

    # Block all incoming traffic to leader
    iptablerule = subprocess.Popen(['sudo', 'iptables',
                                          '-I', 'INPUT',
                                          '-p', 'tcp',
                                          '--dport', '14000',
                                          '-j', 'DROP'])

    print "Cutting the connections to the leader. Waiting for system to stabilize."
    time.sleep(10)

    print "Connecting to old leader, which should not make progress."
    if connect_to_leader():
        print "===== TEST FAILED ====="
    else:
        # c_P2 should make progress
        print "Connecting to other nodes, which should have a new leader."
        for i in range(100):
            c_P2.increment()
        print "Counter value after 100 increments: %d" % c_P2.getvalue()
        print "===== TEST PASSED ====="

    print "Fixing the connections and cleaning up."
    with open('test.iptables.rules', 'r') as input:
        subprocess.Popen(['sudo', 'iptables-restore'], stdin=input)
    subprocess.Popen(['sudo', 'rm', 'test.iptables.rules'])

    for p in (processes):
        p.kill()
    return True

def main():
    if not which('iptables'):
        sys.exit('Test requires iptables to run')

    if not os.geteuid() == 0:
        sys.exit('Script must be run as root')

    test_timeout()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dboundedsemaphore
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Bounded Semaphore Coordination Object
@copyright: See LICENSE
"""
from threading import Lock
from concoord.exception import *

class DBoundedSemaphore():
    def __init__(self, count=1):
        if count < 0:
            raise ValueError
        self.__count = int(count)
        self.__queue = []
        self.__atomic = Lock()
        self._initial_value = int(count)

    def __repr__(self):
        return "<%s count=%d init=%d>" % (self.__class__.__name__, self.__count, self._initial_value)

    def acquire(self, _concoord_command):
        with self.__atomic:
            self.__count -= 1
            if self.__count < 0:
                self.__queue.append(_concoord_command)
                raise BlockingReturn
            else:
                return True

    def release(self, _concoord_command):
        with self.__atomic:
            if self.__count == self._initial_value:
                return ValueError("Semaphore released too many times")
            else:
                self.__count += 1
            if len(self.__queue) > 0:
                unblockcommand = self.__queue.pop(0)
                # add the popped command to the exception args
                unblocked = {}
                unblocked[unblockcommand] = True
                raise UnblockingReturn(unblockeddict=unblocked)

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)

########NEW FILE########
__FILENAME__ = dcondition
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Condition Coordination Object
@copyright: See LICENSE
"""
from threading import RLock
from concoord.exception import *
from concoord.threadingobject.drlock import DRLock

class DCondition():
    def __init__(self, lock=None):
        if lock is None:
            lock = DRLock()
        self.__lock = lock
        # Export the lock's acquire() and release() methods
        self.acquire = lock.acquire
        self.release = lock.release
        self.__waiters = []
        self.__atomic = RLock()

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self.__lock, len(self.__waiters))

    def wait(self, _concoord_command):
        # put the caller on waitinglist and take the lock away
        with self.__atomic:
            if not self.__lock._is_owned(_concoord_command.client):
                raise RuntimeError("cannot wait on un-acquired lock")
            self.__waiters.append(_concoord_command)
            self.__lock.release(_concoord_command)
            raise BlockingReturn()

    def notify(self, _concoord_command):
        # Notify the next client on the wait list
        with self.__atomic:
            if not self.__lock._is_owned(_concoord_command.client):
                raise RuntimeError("cannot notify on un-acquired lock")
            if not self.__waiters:
                return
            waitcommand = self.__waiters.pop(0)
            # notified client should be added to the lock queue
            self.__lock._add_to_queue(waitcommand)

    def notifyAll(self, _concoord_command):
        # Notify every client on the wait list
        with self.__atomic:
            if not self.__lock._is_owned(_concoord_command.client):
                raise RuntimeError("cannot notify on un-acquired lock")
            if not self.__waiters:
                return
            for waitcommand in self.__waiters:
                # notified client should be added to the lock queue
                self.__lock._add_to_queue(waitcommand)
            self.__waiters = []

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)


########NEW FILE########
__FILENAME__ = dlock
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Lock Coordination Object
@copyright: See LICENSE
"""
from threading import Lock
from concoord.enums import *
from concoord.exception import *

class DLock():
    def __init__(self):
        self.__locked = False
        self.__owner = None
        self.__queue = []
        self.__atomic = Lock()

    def __repr__(self):
        return "<%s owner=%s>" % (self.__class__.__name__, str(self.__owner))

    def acquire(self, _concoord_command):
        with self.__atomic:
            if self.__locked:
                self.__queue.append(_concoord_command)
                raise BlockingReturn()
            else:
                self.__locked = True
                self.__owner = _concoord_command.client

    def release(self, _concoord_command):
        with self.__atomic:
            if self.__owner != _concoord_command.client:
                raise RuntimeError("cannot release un-acquired lock")
            if len(self.__queue) > 0:
                unblockcommand = self.__queue.pop(0)
                self.__owner = unblockcommand.client
                # add the popped command to the exception args
                unblocked = {}
                unblocked[unblockcommand] = True
                raise UnblockingReturn(unblockeddict=unblocked)
            elif len(self.__queue) == 0:
                self.__owner = None
                self.__locked = False

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)


########NEW FILE########
__FILENAME__ = drlock
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: RLock Coordination Object
@copyright: See LICENSE
"""
from threading import Lock
from concoord.enums import *
from concoord.exception import *

class DRLock():
    def __init__(self):
        self.__count = 0
        self.__owner = None
        self.__queue = []
        self.__atomic = Lock()

    def __repr__(self):
        return "<%s owner=%r count=%d>" % (self.__class__.__name__, self.__owner, self.__count)

    def acquire(self, _concoord_command):
        with self.__atomic:
            if self.__count > 0 and self.__owner != _concoord_command.client:
                self.__queue.append(_concoord_command)
                raise BlockingReturn()
            elif self.__count > 0 and self.__owner == _concoord_command.client:
                self.__count += 1
                return 1
            else:
                self.__count = 1
                self.__owner = _concoord_command.client
                return True

    def release(self, _concoord_command):
        with self.__atomic:
            if self.__owner != _concoord_command.client:
                raise RuntimeError("cannot release un-acquired lock")
            self.__count -= 1

            if self.__count == 0 and len(self.__queue) > 0:
                self.__count += 1
                unblockcommand = self.__queue.pop(0)
                self.__owner = unblockcommand.client
                # add the popped command to the exception args
                unblocked = {}
                unblocked[unblockcommand] = True
                raise UnblockingReturn(unblockeddict=unblocked)
            elif self.__count == 0 and len(self.__queue) == 0:
                self.__owner = None

    # Internal methods used by condition variables
    def _is_owned(self, client):
        return self.__owner == client

    def _add_to_queue(self, clientcommand):
        self.__queue.append(clientcommand)

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)


########NEW FILE########
__FILENAME__ = dsemaphore
"""
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Semaphore Coordination Object
@copyright: See LICENSE
"""
from threading import Lock
from concoord.exception import *
from concoord.enums import *

class DSemaphore():
    def __init__(self, count=1):
        if count < 0:
            raise ValueError
        self.__count = int(count)
        self.__queue = []
        self.__atomic = Lock()

    def __repr__(self):
        return "<%s count=%d>" % (self.__class__.__name__, self.__count)

    def acquire(self, _concoord_command):
        with self.__atomic:
            self.__count -= 1
            if self.__count < 0:
                self.__queue.append(_concoord_command)
                raise BlockingReturn()
            else:
                return True

    def release(self, _concoord_command):
        with self.__atomic:
            self.__count += 1
            if len(self.__queue) > 0:
                unblockcommand = self.__queue.pop(0)
                unblocked = {}
                unblocked[unblockcommand] = True
                raise UnblockingReturn(unblockeddict=unblocked)

    def __str__(self):
        return "<%s object>" % (self.__class__.__name__)

########NEW FILE########
__FILENAME__ = utils
'''
@author: Deniz Altinbuken, Emin Gun Sirer
@note: Utility functions for the runtime. Includes a timer module for collecting measurements.
@copyright: See LICENSE
'''
import socket
import os, sys
import time
import string
import threading
from concoord.enums import *

def findOwnIP():
    """Retrieves the hostname of the caller"""
    return socket.gethostbyname(socket.gethostname())

def get_addressportpairs(group):
    for peer in group.iterkeys():
        yield (peer.addr,peer.port)

def get_addresses(group):
    for peer in group.iterkeys():
        yield peer.addr

# A logger will always print to the screen. It can also log to a file or to a network log daemon.
class NoneLogger():
    def write(self, cls, string):
        return

    def close(self):
        return

class Logger():
    def __init__(self, name, filename=None, lognode=None):
        self.prefix = name
        self.log = None
        if filename is not None:
            self.log = open("concoord_log_"+name, 'w')
        if lognode is not None:
            logaddr,logport = lognode.split(':')
            try:
                self.log = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.log.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                self.log.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                self.log.connect((logaddr,int(logport)))
            except IOError:
                self.log = None
                return

    def write(self, cls, string):
        print "[%s] %s %s: %s" % (self.prefix + '_' + threading.current_thread().name,
                                  time.time(), # time.asctime(time.localtime(time.time())),
                                  cls, string)
        if self.log is not None:
            self.log.write("[%s] %s %s: %s" % (self.prefix + '_' + threading.current_thread().name,
                                               time.time(), # time.asctime(time.localtime(time.time())),
                                               cls, string))
            self.log.flush()

    def close(self):
        if self.log is not None:
            self.log.close()

# PERFORMANCE MEASUREMENT UTILS
timers = {}
def starttimer(timerkey, timerno):
    global timers
    index = "%s-%s" % (str(timerkey),str(timerno))
    if not timers.has_key(index):
        timers[index] = [time.time(), 0]

def endtimer(timerkey, timerno):
    global timers
    index = "%s-%s" % (str(timerkey),str(timerno))
    try:
        if timers[index][1] == 0:
            timers[index][1] = time.time()
    except:
        print "Can't stop timer %s %s." % (str(timerkey),str(timerno))

def dumptimers(numreplicas, ownertype, outputdict):
    global timers
    filename = "output/replica/%s" % str(numreplicas)
    try:
        outputfile = open(outputdict+filename, "w")
    except:
        outputfile = open("./"+filename, "w")
    for index,numbers in timers.iteritems():
        timerkey, timerno = index.rsplit("-")
        if not numbers[1]-numbers[0] < 0:
            outputfile.write("%s:\t%s\t%s\n"  % (str(timerno),
                                                     str(numreplicas),
                                                     str(numbers[1]-numbers[0])))
    outputfile.close()

def starttiming(fn):
    """
    Decorator used to start timing.
    Keeps track of the count for the first and second calls.
    """
    def new(*args, **kw):
        obj = args[0]
        if obj.firststarttime == 0:
            obj.firststarttime = time.time()
        elif obj.secondstarttime == 0:
            obj.secondstarttime = time.time()
        profile_on()
        return fn(*args, **kw)
    return new

def endtiming(fn):
    """
    Decorator used to end timing.
    Keeps track of the count for the first and second calls.
    """
    NITER = 10000
    def new(*args, **kw):
        ret = fn(*args, **kw)
        obj = args[0]
        if obj.firststoptime == 0:
            obj.firststoptime = time.time()
        elif obj.secondstoptime == 0:
            obj.secondstoptime = time.time()
        elif obj.count == NITER:
            now = time.time()
            total = now - obj.secondstarttime
            perrequest = total/NITER
            filename = "output/%s" % (str(len(obj.groups[NODE_REPLICA])+1))
            outputfile = open("./"+filename, "a")
            # numreplicas #perrequest #total
            outputfile.write("%s\t%s\t%s\n" % (str(len(obj.groups[NODE_REPLICA])+1),
                                                   str(perrequest), str(total)))
            outputfile.close()
            obj.count += 1
            sys.stdout.flush()
            profile_off()
            profilerdict = get_profile_stats()
            for key, value in sorted(profilerdict.iteritems(),
                                     key=lambda (k,v): (v[2],k)):
                print "%s: %s" % (key, value)
            time.sleep(10)
            sys.stdout.flush()
            os._exit(0)
        else:
            obj.count += 1
        return ret
    return new

def throughput_test(fn):
    """Decorator used to measure throughput."""
    def new(*args, **kw):
        ret = fn(*args, **kw)
        obj = args[0]
        obj.throughput_runs += 1
        if obj.throughput_runs == 100:
            obj.throughput_start = time.time()
        elif obj.throughput_runs == 1100:
            obj.throughput_stop = time.time()
            totaltime = obj.throughput_stop - obj.throughput_start
            print "********************************************"
            print "TOTAL: ", totaltime
            print "TPUT: ", 1000/totaltime, "req/s"
            print "********************************************"
            obj._graceexit(1)
        return ret
    return new


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ConCoord documentation build configuration file, created by
# sphinx-quickstart on Tue Mar 27 16:31:41 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ConCoord'
copyright = u'2012, Deniz Altinbuken, Emin Gun Sirer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.1.0'
# The full version, including alpha/beta/rc tags.
release = '1.1.0'

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
exclude_patterns = []

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
htmlhelp_basename = 'ConCoorddoc'


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
  ('index', 'ConCoord.tex', u'ConCoord Documentation',
   u'Deniz Altinbuken, Emin Gun Sirer', 'manual'),
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
    ('index', 'concoord', u'ConCoord Documentation',
     [u'Deniz Altinbuken, Emin Gun Sirer'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'ConCoord', u'ConCoord Documentation',
   u'Deniz Altinbuken, Emin Gun Sirer', 'ConCoord', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
