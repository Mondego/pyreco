__FILENAME__ = tls
#!/usr/bin/env python

# Authors: 
#   Trevor Perrin
#   Marcelo Fernandez - bugfix and NPN support
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.
from __future__ import print_function
import sys
import os
import os.path
import socket
import time
import getopt
try:
    import httplib
    from SocketServer import *
    from BaseHTTPServer import *
    from SimpleHTTPServer import *
except ImportError:
    # Python 3.x
    from http import client as httplib
    from socketserver import *
    from http.server import *

if __name__ != "__main__":
    raise "This must be run as a command, not used as a module!"

from tlslite.api import *
from tlslite import __version__

try:
    from tack.structures.Tack import Tack

except ImportError:
    pass

def printUsage(s=None):
    if s:
        print("ERROR: %s" % s)

    print("")
    print("Version: %s" % __version__)
    print("")
    print("RNG: %s" % prngName)
    print("")
    print("Modules:")
    if tackpyLoaded:
        print("  tackpy      : Loaded")
    else:
        print("  tackpy      : Not Loaded")            
    if m2cryptoLoaded:
        print("  M2Crypto    : Loaded")
    else:
        print("  M2Crypto    : Not Loaded")
    if pycryptoLoaded:
        print("  pycrypto    : Loaded")
    else:
        print("  pycrypto    : Not Loaded")
    if gmpyLoaded:
        print("  GMPY        : Loaded")
    else:
        print("  GMPY        : Not Loaded")
    
    print("")
    print("""Commands:

  server  
    [-k KEY] [-c CERT] [-t TACK] [-v VERIFIERDB] [-d DIR]
    [--reqcert] HOST:PORT

  client
    [-k KEY] [-c CERT] [-u USER] [-p PASS]
    HOST:PORT
""")
    sys.exit(-1)

def printError(s):
    """Print error message and exit"""
    sys.stderr.write("ERROR: %s\n" % s)
    sys.exit(-1)


def handleArgs(argv, argString, flagsList=[]):
    # Convert to getopt argstring format:
    # Add ":" after each arg, ie "abc" -> "a:b:c:"
    getOptArgString = ":".join(argString) + ":"
    try:
        opts, argv = getopt.getopt(argv, getOptArgString, flagsList)
    except getopt.GetoptError as e:
        printError(e) 
    # Default values if arg not present  
    privateKey = None
    certChain = None
    username = None
    password = None
    tacks = None
    verifierDB = None
    reqCert = False
    directory = None
    
    for opt, arg in opts:
        if opt == "-k":
            s = open(arg, "rb").read()
            privateKey = parsePEMKey(s, private=True)            
        elif opt == "-c":
            s = open(arg, "rb").read()
            x509 = X509()
            x509.parse(s)
            certChain = X509CertChain([x509])
        elif opt == "-u":
            username = arg
        elif opt == "-p":
            password = arg
        elif opt == "-t":
            if tackpyLoaded:
                s = open(arg, "rU").read()
                tacks = Tack.createFromPemList(s)
        elif opt == "-v":
            verifierDB = VerifierDB(arg)
            verifierDB.open()
        elif opt == "-d":
            directory = arg
        elif opt == "--reqcert":
            reqCert = True
        else:
            assert(False)
            
    if not argv:
        printError("Missing address")
    if len(argv)>1:
        printError("Too many arguments")
    #Split address into hostname/port tuple
    address = argv[0]
    address = address.split(":")
    if len(address) != 2:
        raise SyntaxError("Must specify <host>:<port>")
    address = ( address[0], int(address[1]) )

    # Populate the return list
    retList = [address]
    if "k" in argString:
        retList.append(privateKey)
    if "c" in argString:
        retList.append(certChain)
    if "u" in argString:
        retList.append(username)
    if "p" in argString:
        retList.append(password)
    if "t" in argString:
        retList.append(tacks)
    if "v" in argString:
        retList.append(verifierDB)
    if "d" in argString:
        retList.append(directory)
    if "reqcert" in flagsList:
        retList.append(reqCert)
    return retList


def printGoodConnection(connection, seconds):
    print("  Handshake time: %.3f seconds" % seconds)
    print("  Version: %s" % connection.getVersionName())
    print("  Cipher: %s %s" % (connection.getCipherName(), 
        connection.getCipherImplementation()))
    if connection.session.srpUsername:
        print("  Client SRP username: %s" % connection.session.srpUsername)
    if connection.session.clientCertChain:
        print("  Client X.509 SHA1 fingerprint: %s" % 
            connection.session.clientCertChain.getFingerprint())
    if connection.session.serverCertChain:
        print("  Server X.509 SHA1 fingerprint: %s" % 
            connection.session.serverCertChain.getFingerprint())
    if connection.session.serverName:
        print("  SNI: %s" % connection.session.serverName)
    if connection.session.tackExt:   
        if connection.session.tackInHelloExt:
            emptyStr = "\n  (via TLS Extension)"
        else:
            emptyStr = "\n  (via TACK Certificate)" 
        print("  TACK: %s" % emptyStr)
        print(str(connection.session.tackExt))
    print("  Next-Protocol Negotiated: %s" % connection.next_proto) 
    

def clientCmd(argv):
    (address, privateKey, certChain, username, password) = \
        handleArgs(argv, "kcup")
        
    if (certChain and not privateKey) or (not certChain and privateKey):
        raise SyntaxError("Must specify CERT and KEY together")
    if (username and not password) or (not username and password):
        raise SyntaxError("Must specify USER with PASS")
    if certChain and username:
        raise SyntaxError("Can use SRP or client cert for auth, not both")

    #Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(address)
    connection = TLSConnection(sock)
    
    settings = HandshakeSettings()
    settings.useExperimentalTackExtension = True
    
    try:
        start = time.clock()
        if username and password:
            connection.handshakeClientSRP(username, password, 
                settings=settings, serverName=address[0])
        else:
            connection.handshakeClientCert(certChain, privateKey,
                settings=settings, serverName=address[0])
        stop = time.clock()        
        print("Handshake success")        
    except TLSLocalAlert as a:
        if a.description == AlertDescription.user_canceled:
            print(str(a))
        else:
            raise
        sys.exit(-1)
    except TLSRemoteAlert as a:
        if a.description == AlertDescription.unknown_psk_identity:
            if username:
                print("Unknown username")
            else:
                raise
        elif a.description == AlertDescription.bad_record_mac:
            if username:
                print("Bad username or password")
            else:
                raise
        elif a.description == AlertDescription.handshake_failure:
            print("Unable to negotiate mutually acceptable parameters")
        else:
            raise
        sys.exit(-1)
    printGoodConnection(connection, stop-start)
    connection.close()


def serverCmd(argv):
    (address, privateKey, certChain, tacks, 
        verifierDB, directory, reqCert) = handleArgs(argv, "kctbvd", ["reqcert"])


    if (certChain and not privateKey) or (not certChain and privateKey):
        raise SyntaxError("Must specify CERT and KEY together")
    if tacks and not certChain:
        raise SyntaxError("Must specify CERT with Tacks")
    
    print("I am an HTTPS test server, I will listen on %s:%d" % 
            (address[0], address[1]))    
    if directory:
        os.chdir(directory)
    print("Serving files from %s" % os.getcwd())
    
    if certChain and privateKey:
        print("Using certificate and private key...")
    if verifierDB:
        print("Using verifier DB...")
    if tacks:
        print("Using Tacks...")
        
    #############
    sessionCache = SessionCache()

    class MyHTTPServer(ThreadingMixIn, TLSSocketServerMixIn, HTTPServer):
        def handshake(self, connection):
            print("About to handshake...")
            activationFlags = 0
            if tacks:
                if len(tacks) == 1:
                    activationFlags = 1
                elif len(tacks) == 2:
                    activationFlags = 3

            try:
                start = time.clock()
                settings = HandshakeSettings()
                settings.useExperimentalTackExtension=True
                connection.handshakeServer(certChain=certChain,
                                              privateKey=privateKey,
                                              verifierDB=verifierDB,
                                              tacks=tacks,
                                              activationFlags=activationFlags,
                                              sessionCache=sessionCache,
                                              settings=settings,
                                              nextProtos=[b"http/1.1"])
                                              # As an example (does not work here):
                                              #nextProtos=[b"spdy/3", b"spdy/2", b"http/1.1"])
                stop = time.clock()
            except TLSRemoteAlert as a:
                if a.description == AlertDescription.user_canceled:
                    print(str(a))
                    return False
                else:
                    raise
            except TLSLocalAlert as a:
                if a.description == AlertDescription.unknown_psk_identity:
                    if username:
                        print("Unknown username")
                        return False
                    else:
                        raise
                elif a.description == AlertDescription.bad_record_mac:
                    if username:
                        print("Bad username or password")
                        return False
                    else:
                        raise
                elif a.description == AlertDescription.handshake_failure:
                    print("Unable to negotiate mutually acceptable parameters")
                    return False
                else:
                    raise
                
            connection.ignoreAbruptClose = True
            printGoodConnection(connection, stop-start)
            return True

    httpd = MyHTTPServer(address, SimpleHTTPRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        printUsage("Missing command")
    elif sys.argv[1] == "client"[:len(sys.argv[1])]:
        clientCmd(sys.argv[2:])
    elif sys.argv[1] == "server"[:len(sys.argv[1])]:
        serverCmd(sys.argv[2:])
    else:
        printUsage("Unknown command: %s" % sys.argv[1])


########NEW FILE########
__FILENAME__ = tlsdb
#!/usr/bin/env python

# Authors: 
#   Trevor Perrin
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

from __future__ import print_function
import sys
import os
import socket
import math

if __name__ != "__main__":
    raise "This must be run as a command, not used as a module!"


from tlslite import *
from tlslite import __version__

if len(sys.argv) == 1 or (len(sys.argv)==2 and sys.argv[1].lower().endswith("help")):
    print("")
    print("Version: %s" % __version__)
    print("")
    print("RNG: %s" % prngName)
    print("")
    print("Modules:")
    if m2cryptoLoaded:
        print("  M2Crypto    : Loaded")
    else:
        print("  M2Crypto    : Not Loaded")
    if pycryptoLoaded:
        print("  pycrypto    : Loaded")
    else:
        print("  pycrypto    : Not Loaded")
    if gmpyLoaded:
        print("  GMPY        : Loaded")
    else:
        print("  GMPY        : Not Loaded")
    print("")
    print("Commands:")
    print("")
    print("  createsrp       <db>")
    print("")
    print("  add    <db> <user> <pass> [<bits>]")
    print("  del    <db> <user>")
    print("  check  <db> <user> [<pass>]")
    print("  list   <db>")
    sys.exit()

cmd = sys.argv[1].lower()

class Args:
    def __init__(self, argv):
        self.argv = argv
    def get(self, index):
        if len(self.argv)<=index:
            raise SyntaxError("Not enough arguments")
        return self.argv[index]
    def getLast(self, index):
        if len(self.argv)>index+1:
            raise SyntaxError("Too many arguments")
        return self.get(index)

args = Args(sys.argv)

def reformatDocString(s):
    lines = s.splitlines()
    newLines = []
    for line in lines:
        newLines.append("  " + line.strip())
    return "\n".join(newLines)

try:
    if cmd == "help":
        command = args.getLast(2).lower()
        if command == "valid":
            print("")
        else:
            print("Bad command: '%s'" % command)

    elif cmd == "createsrp":
        dbName = args.get(2)

        db = VerifierDB(dbName)
        db.create()

    elif cmd == "add":
        dbName = args.get(2)
        username = args.get(3)
        password = args.get(4)

        db = VerifierDB(dbName)
        db.open()
        if username in db:
            print("User already in database!")
            sys.exit()
        bits = int(args.getLast(5))
        N, g, salt, verifier = VerifierDB.makeVerifier(username, password, bits)
        db[username] = N, g, salt, verifier

    elif cmd == "del":
        dbName = args.get(2)
        username = args.getLast(3)
        db = VerifierDB(dbName)
        db.open()
        del(db[username])

    elif cmd == "check":
        dbName = args.get(2)
        username = args.get(3)
        if len(sys.argv)>=5:
            password = args.getLast(4)
        else:
            password = None

        db = VerifierDB(dbName)
        db.open()

        try:
            db[username]
            print("Username exists")

            if password:
                if db.check(username, password):
                    print("Password is correct")
                else:
                    print("Password is wrong")
        except KeyError:
            print("Username does not exist")
            sys.exit()

    elif cmd == "list":
        dbName = args.get(2)
        db = VerifierDB(dbName)
        db.open()

        print("Verifier Database")
        def numBits(n):
            if n==0:
                return 0
            return int(math.floor(math.log(n, 2))+1)
        for username in db.keys():
            N, g, s, v = db[username]
            print(numBits(N), username)
    else:
        print("Bad command: '%s'" % cmd)
except:
    raise

########NEW FILE########
__FILENAME__ = httpsclient
#!/usr/bin/env python
from __future__ import print_function
from tlslite import HTTPTLSConnection, HandshakeSettings

settings = HandshakeSettings()
settings.useExperimentalTackExtension = True

h = HTTPTLSConnection("localhost", 4443, settings=settings)    
h.request("GET", "/index.html")
r = h.getresponse()
print(r.read())

########NEW FILE########
__FILENAME__ = tlstest
#!/usr/bin/env python

# Authors: 
#   Trevor Perrin
#   Kees Bos - Added tests for XML-RPC
#   Dimitris Moraitis - Anon ciphersuites
#   Marcelo Fernandez - Added test for NPN
#   Martin von Loewis - python 3 port

#
# See the LICENSE file for legal information regarding use of this file.
from __future__ import print_function
import sys
import os
import os.path
import socket
import time
import getopt
try:
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, SimpleHTTPRequestHandler

from tlslite import TLSConnection, Fault, HandshakeSettings, \
    X509, X509CertChain, IMAP4_TLS, VerifierDB, Session, SessionCache, \
    parsePEMKey, constants, \
    AlertDescription, HTTPTLSConnection, TLSSocketServerMixIn, \
    POP3_TLS, m2cryptoLoaded, pycryptoLoaded, gmpyLoaded, tackpyLoaded, \
    Checker, __version__

from tlslite.errors import *
from tlslite.utils.cryptomath import prngName
try:
    import xmlrpclib
except ImportError:
    # Python 3
    from xmlrpc import client as xmlrpclib
from tlslite import *

try:
    from tack.structures.Tack import Tack
    
except ImportError:
    pass

def printUsage(s=None):
    if m2cryptoLoaded:
        crypto = "M2Crypto/OpenSSL"
    else:
        crypto = "Python crypto"        
    if s:
        print("ERROR: %s" % s)
    print("""\ntls.py version %s (using %s)  

Commands:
  server HOST:PORT DIRECTORY

  client HOST:PORT DIRECTORY
""" % (__version__, crypto))
    sys.exit(-1)
    

def testConnClient(conn):
    b1 = os.urandom(1)
    b10 = os.urandom(10)
    b100 = os.urandom(100)
    b1000 = os.urandom(1000)
    conn.write(b1)
    conn.write(b10)
    conn.write(b100)
    conn.write(b1000)
    assert(conn.read(min=1, max=1) == b1)
    assert(conn.read(min=10, max=10) == b10)
    assert(conn.read(min=100, max=100) == b100)
    assert(conn.read(min=1000, max=1000) == b1000)

def clientTestCmd(argv):
    
    address = argv[0]
    dir = argv[1]    

    #Split address into hostname/port tuple
    address = address.split(":")
    address = ( address[0], int(address[1]) )

    def connect():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(sock, 'settimeout'): #It's a python 2.3 feature
            sock.settimeout(5)
        sock.connect(address)
        c = TLSConnection(sock)
        return c

    test = 0

    badFault = False

    print("Test 0 - anonymous handshake")
    connection = connect()
    connection.handshakeClientAnonymous()
    testConnClient(connection)
    connection.close()
        
    print("Test 1 - good X509 (plus SNI)")
    connection = connect()
    connection.handshakeClientCert(serverName=address[0])
    testConnClient(connection)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    assert(connection.session.serverName == address[0])
    connection.close()

    print("Test 1.a - good X509, SSLv3")
    connection = connect()
    settings = HandshakeSettings()
    settings.minVersion = (3,0)
    settings.maxVersion = (3,0)
    connection.handshakeClientCert(settings=settings)
    testConnClient(connection)    
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    connection.close()    

    print("Test 1.b - good X509, RC4-MD5")
    connection = connect()
    settings = HandshakeSettings()
    settings.macNames = ["md5"]
    connection.handshakeClientCert(settings=settings)
    testConnClient(connection)    
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    assert(connection.session.cipherSuite == constants.CipherSuite.TLS_RSA_WITH_RC4_128_MD5)
    connection.close()

    if tackpyLoaded:
                    
        settings = HandshakeSettings()
        settings.useExperimentalTackExtension = True

        print("Test 2.a - good X.509, TACK")
        connection = connect()
        connection.handshakeClientCert(settings=settings)
        assert(connection.session.tackExt.tacks[0].getTackId() == "rrted.ptvtl.d2uiq.ox2xe.w4ss3")
        assert(connection.session.tackExt.activation_flags == 1)        
        testConnClient(connection)    
        connection.close()    

        print("Test 2.b - good X.509, TACK unrelated to cert chain")
        connection = connect()
        try:
            connection.handshakeClientCert(settings=settings)
            assert(False)
        except TLSLocalAlert as alert:
            if alert.description != AlertDescription.illegal_parameter:
                raise        
        connection.close()

    print("Test 3 - good SRP")
    connection = connect()
    connection.handshakeClientSRP("test", "password")
    testConnClient(connection)
    connection.close()

    print("Test 4 - SRP faults")
    for fault in Fault.clientSrpFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeClientSRP("test", "password")
            print("  Good Fault %s" % (Fault.faultNames[fault]))
        except TLSFaultError as e:
            print("  BAD FAULT %s: %s" % (Fault.faultNames[fault], str(e)))
            badFault = True

    print("Test 6 - good SRP: with X.509 certificate, TLSv1.0")
    settings = HandshakeSettings()
    settings.minVersion = (3,1)
    settings.maxVersion = (3,1)    
    connection = connect()
    connection.handshakeClientSRP("test", "password", settings=settings)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    testConnClient(connection)
    connection.close()

    print("Test 7 - X.509 with SRP faults")
    for fault in Fault.clientSrpFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeClientSRP("test", "password")
            print("  Good Fault %s" % (Fault.faultNames[fault]))
        except TLSFaultError as e:
            print("  BAD FAULT %s: %s" % (Fault.faultNames[fault], str(e)))
            badFault = True

    print("Test 11 - X.509 faults")
    for fault in Fault.clientNoAuthFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeClientCert()
            print("  Good Fault %s" % (Fault.faultNames[fault]))
        except TLSFaultError as e:
            print("  BAD FAULT %s: %s" % (Fault.faultNames[fault], str(e)))
            badFault = True

    print("Test 14 - good mutual X509")
    x509Cert = X509().parse(open(os.path.join(dir, "clientX509Cert.pem")).read())
    x509Chain = X509CertChain([x509Cert])
    s = open(os.path.join(dir, "clientX509Key.pem")).read()
    x509Key = parsePEMKey(s, private=True)

    connection = connect()
    connection.handshakeClientCert(x509Chain, x509Key)
    testConnClient(connection)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    connection.close()

    print("Test 14.a - good mutual X509, SSLv3")
    connection = connect()
    settings = HandshakeSettings()
    settings.minVersion = (3,0)
    settings.maxVersion = (3,0)
    connection.handshakeClientCert(x509Chain, x509Key, settings=settings)
    testConnClient(connection)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    connection.close()

    print("Test 15 - mutual X.509 faults")
    for fault in Fault.clientCertFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeClientCert(x509Chain, x509Key)
            print("  Good Fault %s" % (Fault.faultNames[fault]))
        except TLSFaultError as e:
            print("  BAD FAULT %s: %s" % (Fault.faultNames[fault], str(e)))
            badFault = True

    print("Test 18 - good SRP, prepare to resume... (plus SNI)")
    connection = connect()
    connection.handshakeClientSRP("test", "password", serverName=address[0])
    testConnClient(connection)
    connection.close()
    session = connection.session

    print("Test 19 - resumption (plus SNI)")
    connection = connect()
    connection.handshakeClientSRP("test", "garbage", serverName=address[0], 
                                    session=session)
    testConnClient(connection)
    #Don't close! -- see below

    print("Test 20 - invalidated resumption (plus SNI)")
    connection.sock.close() #Close the socket without a close_notify!
    connection = connect()
    try:
        connection.handshakeClientSRP("test", "garbage", 
                        serverName=address[0], session=session)
        assert(False)
    except TLSRemoteAlert as alert:
        if alert.description != AlertDescription.bad_record_mac:
            raise
    connection.close()
    
    print("Test 21 - HTTPS test X.509")
    address = address[0], address[1]+1
    if hasattr(socket, "timeout"):
        timeoutEx = socket.timeout
    else:
        timeoutEx = socket.error
    while 1:
        try:
            time.sleep(2)
            htmlBody = bytearray(open(os.path.join(dir, "index.html")).read(), "utf-8")
            fingerprint = None
            for y in range(2):
                checker =Checker(x509Fingerprint=fingerprint)
                h = HTTPTLSConnection(\
                        address[0], address[1], checker=checker)
                for x in range(3):
                    h.request("GET", "/index.html")
                    r = h.getresponse()
                    assert(r.status == 200)
                    b = bytearray(r.read())
                    assert(b == htmlBody)
                fingerprint = h.tlsSession.serverCertChain.getFingerprint()
                assert(fingerprint)
            time.sleep(2)
            break
        except timeoutEx:
            print("timeout, retrying...")
            pass

    address = address[0], address[1]+1

    implementations = []
    if m2cryptoLoaded:
        implementations.append("openssl")
    if pycryptoLoaded:
        implementations.append("pycrypto")
    implementations.append("python")

    print("Test 22 - different ciphers, TLSv1.0")
    for implementation in implementations:
        for cipher in ["aes128", "aes256", "rc4"]:

            print("Test 22:", end=' ')
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]
            settings.minVersion = (3,1)
            settings.maxVersion = (3,1)            
            connection.handshakeClientCert(settings=settings)
            testConnClient(connection)
            print("%s %s" % (connection.getCipherName(), connection.getCipherImplementation()))
            connection.close()

    print("Test 23 - throughput test")
    for implementation in implementations:
        for cipher in ["aes128", "aes256", "3des", "rc4"]:
            if cipher == "3des" and implementation not in ("openssl", "pycrypto"):
                continue

            print("Test 23:", end=' ')
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]
            connection.handshakeClientCert(settings=settings)
            print("%s %s:" % (connection.getCipherName(), connection.getCipherImplementation()), end=' ')

            startTime = time.clock()
            connection.write(b"hello"*10000)
            h = connection.read(min=50000, max=50000)
            stopTime = time.clock()
            if stopTime-startTime:
                print("100K exchanged at rate of %d bytes/sec" % int(100000/(stopTime-startTime)))
            else:
                print("100K exchanged very fast")

            assert(h == b"hello"*10000)
            connection.close()
    
    print("Test 24.a - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'http/1.1')
    connection.close()

    print("Test 24.b - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"spdy/2", b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'spdy/2')
    connection.close()
    
    print("Test 24.c - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"spdy/2", b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'spdy/2')
    connection.close()
    
    print("Test 24.d - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"spdy/3", b"spdy/2", b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'spdy/2')
    connection.close()
    
    print("Test 24.e - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"spdy/3", b"spdy/2", b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'spdy/3')
    connection.close()

    print("Test 24.f - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'http/1.1')
    connection.close()

    print("Test 24.g - Next-Protocol Client Negotiation")
    connection = connect()
    connection.handshakeClientCert(nextProtos=[b"spdy/2", b"http/1.1"])
    #print("  Next-Protocol Negotiated: %s" % connection.next_proto)
    assert(connection.next_proto == b'spdy/2')
    connection.close()
    
    print('Test 25 - good standard XMLRPC https client')
    time.sleep(2) # Hack for lack of ability to set timeout here
    address = address[0], address[1]+1
    server = xmlrpclib.Server('https://%s:%s' % address)
    assert server.add(1,2) == 3
    assert server.pow(2,4) == 16

    print('Test 26 - good tlslite XMLRPC client')
    transport = XMLRPCTransport(ignoreAbruptClose=True)
    server = xmlrpclib.Server('https://%s:%s' % address, transport)
    assert server.add(1,2) == 3
    assert server.pow(2,4) == 16

    print('Test 27 - good XMLRPC ignored protocol')
    server = xmlrpclib.Server('http://%s:%s' % address, transport)
    assert server.add(1,2) == 3
    assert server.pow(2,4) == 16
        
    print("Test 28 - Internet servers test")
    try:
        i = IMAP4_TLS("cyrus.andrew.cmu.edu")
        i.login("anonymous", "anonymous@anonymous.net")
        i.logout()
        print("Test 28: IMAP4 good")
        p = POP3_TLS("pop.gmail.com")
        p.quit()
        print("Test 29: POP3 good")
    except socket.error as e:
        print("Non-critical error: socket error trying to reach internet server: ", e)   

    if not badFault:
        print("Test succeeded")
    else:
        print("Test failed")



def testConnServer(connection):
    count = 0
    while 1:
        s = connection.read()
        count += len(s)
        if len(s) == 0:
            break
        connection.write(s)
        if count == 1111:
            break

def serverTestCmd(argv):

    address = argv[0]
    dir = argv[1]
    
    #Split address into hostname/port tuple
    address = address.split(":")
    address = ( address[0], int(address[1]) )

    #Connect to server
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind(address)
    lsock.listen(5)

    def connect():
        return TLSConnection(lsock.accept()[0])

    x509Cert = X509().parse(open(os.path.join(dir, "serverX509Cert.pem")).read())
    x509Chain = X509CertChain([x509Cert])
    s = open(os.path.join(dir, "serverX509Key.pem")).read()
    x509Key = parsePEMKey(s, private=True)

    print("Test 0 - Anonymous server handshake")
    connection = connect()
    connection.handshakeServer(anon=True)
    testConnServer(connection)    
    connection.close() 
    
    print("Test 1 - good X.509")
    connection = connect()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key)
    assert(connection.session.serverName == address[0])    
    testConnServer(connection)    
    connection.close()

    print("Test 1.a - good X.509, SSL v3")
    connection = connect()
    settings = HandshakeSettings()
    settings.minVersion = (3,0)
    settings.maxVersion = (3,0)
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, settings=settings)
    testConnServer(connection)
    connection.close()            

    print("Test 1.b - good X.509, RC4-MD5")
    connection = connect()
    settings = HandshakeSettings()
    settings.macNames = ["sha", "md5"]
    settings.cipherNames = ["rc4"]
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, settings=settings)
    testConnServer(connection)
    connection.close()            
    
    if tackpyLoaded:
        tack = Tack.createFromPem(open("./TACK1.pem", "rU").read())
        tackUnrelated = Tack.createFromPem(open("./TACKunrelated.pem", "rU").read())    
            
        settings = HandshakeSettings()
        settings.useExperimentalTackExtension = True

        print("Test 2.a - good X.509, TACK")
        connection = connect()
        connection.handshakeServer(certChain=x509Chain, privateKey=x509Key,
            tacks=[tack], activationFlags=1, settings=settings)
        testConnServer(connection)    
        connection.close()        

        print("Test 2.b - good X.509, TACK unrelated to cert chain")
        connection = connect()
        try:
            connection.handshakeServer(certChain=x509Chain, privateKey=x509Key,
                tacks=[tackUnrelated], settings=settings)
            assert(False)
        except TLSRemoteAlert as alert:
            if alert.description != AlertDescription.illegal_parameter:
                raise        
    
    print("Test 3 - good SRP")
    verifierDB = VerifierDB()
    verifierDB.create()
    entry = VerifierDB.makeVerifier("test", "password", 1536)
    verifierDB["test"] = entry

    connection = connect()
    connection.handshakeServer(verifierDB=verifierDB)
    testConnServer(connection)
    connection.close()

    print("Test 4 - SRP faults")
    for fault in Fault.clientSrpFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeServer(verifierDB=verifierDB)
            assert()
        except:
            pass
        connection.close()

    print("Test 6 - good SRP: with X.509 cert")
    connection = connect()
    connection.handshakeServer(verifierDB=verifierDB, \
                               certChain=x509Chain, privateKey=x509Key)
    testConnServer(connection)    
    connection.close()

    print("Test 7 - X.509 with SRP faults")
    for fault in Fault.clientSrpFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeServer(verifierDB=verifierDB, \
                                       certChain=x509Chain, privateKey=x509Key)
            assert()
        except:
            pass
        connection.close()

    print("Test 11 - X.509 faults")
    for fault in Fault.clientNoAuthFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeServer(certChain=x509Chain, privateKey=x509Key)
            assert()
        except:
            pass
        connection.close()

    print("Test 14 - good mutual X.509")
    connection = connect()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, reqCert=True)
    testConnServer(connection)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    connection.close()

    print("Test 14a - good mutual X.509, SSLv3")
    connection = connect()
    settings = HandshakeSettings()
    settings.minVersion = (3,0)
    settings.maxVersion = (3,0)
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, reqCert=True, settings=settings)
    testConnServer(connection)
    assert(isinstance(connection.session.serverCertChain, X509CertChain))
    connection.close()

    print("Test 15 - mutual X.509 faults")
    for fault in Fault.clientCertFaults + Fault.genericFaults:
        connection = connect()
        connection.fault = fault
        try:
            connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, reqCert=True)
            assert()
        except:
            pass
        connection.close()

    print("Test 18 - good SRP, prepare to resume")
    sessionCache = SessionCache()
    connection = connect()
    connection.handshakeServer(verifierDB=verifierDB, sessionCache=sessionCache)
    assert(connection.session.serverName == address[0])    
    testConnServer(connection)
    connection.close()

    print("Test 19 - resumption")
    connection = connect()
    connection.handshakeServer(verifierDB=verifierDB, sessionCache=sessionCache)
    assert(connection.session.serverName == address[0])
    testConnServer(connection)    
    #Don't close! -- see next test

    print("Test 20 - invalidated resumption")
    try:
        connection.read(min=1, max=1)
        assert() #Client is going to close the socket without a close_notify
    except TLSAbruptCloseError as e:
        pass
    connection = connect()
    try:
        connection.handshakeServer(verifierDB=verifierDB, sessionCache=sessionCache)
    except TLSLocalAlert as alert:
        if alert.description != AlertDescription.bad_record_mac:
            raise
    connection.close()

    print("Test 21 - HTTPS test X.509")

    #Close the current listening socket
    lsock.close()

    #Create and run an HTTP Server using TLSSocketServerMixIn
    class MyHTTPServer(TLSSocketServerMixIn,
                       HTTPServer):
        def handshake(self, tlsConnection):
                tlsConnection.handshakeServer(certChain=x509Chain, privateKey=x509Key)
                return True
    cd = os.getcwd()
    os.chdir(dir)
    address = address[0], address[1]+1
    httpd = MyHTTPServer(address, SimpleHTTPRequestHandler)
    for x in range(6):
        httpd.handle_request()
    httpd.server_close()
    cd = os.chdir(cd)

    #Re-connect the listening socket
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = address[0], address[1]+1
    lsock.bind(address)
    lsock.listen(5)

    implementations = []
    if m2cryptoLoaded:
        implementations.append("openssl")
    if pycryptoLoaded:
        implementations.append("pycrypto")
    implementations.append("python")

    print("Test 22 - different ciphers")
    for implementation in ["python"] * len(implementations):
        for cipher in ["aes128", "aes256", "rc4"]:

            print("Test 22:", end=' ')
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]

            connection.handshakeServer(certChain=x509Chain, privateKey=x509Key,
                                        settings=settings)
            print(connection.getCipherName(), connection.getCipherImplementation())
            testConnServer(connection)
            connection.close()

    print("Test 23 - throughput test")
    for implementation in implementations:
        for cipher in ["aes128", "aes256", "3des", "rc4"]:
            if cipher == "3des" and implementation not in ("openssl", "pycrypto"):
                continue

            print("Test 23:", end=' ')
            connection = connect()

            settings = HandshakeSettings()
            settings.cipherNames = [cipher]
            settings.cipherImplementations = [implementation, "python"]

            connection.handshakeServer(certChain=x509Chain, privateKey=x509Key,
                                        settings=settings)
            print(connection.getCipherName(), connection.getCipherImplementation())
            h = connection.read(min=50000, max=50000)
            assert(h == b"hello"*10000)
            connection.write(h)
            connection.close()

    print("Test 24.a - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"http/1.1"])
    testConnServer(connection)
    connection.close()

    print("Test 24.b - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"spdy/2", b"http/1.1"])
    testConnServer(connection)
    connection.close()
    
    print("Test 24.c - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"http/1.1", b"spdy/2"])
    testConnServer(connection)
    connection.close()

    print("Test 24.d - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"spdy/2", b"http/1.1"])
    testConnServer(connection)
    connection.close()
    
    print("Test 24.e - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"http/1.1", b"spdy/2", b"spdy/3"])
    testConnServer(connection)
    connection.close()
    
    print("Test 24.f - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[b"spdy/3", b"spdy/2"])
    testConnServer(connection)
    connection.close()
    
    print("Test 24.g - Next-Protocol Server Negotiation")
    connection = connect()
    settings = HandshakeSettings()
    connection.handshakeServer(certChain=x509Chain, privateKey=x509Key, 
                               settings=settings, nextProtos=[])
    testConnServer(connection)
    connection.close()

    print("Tests 25-27 - XMLRPXC server")
    address = address[0], address[1]+1
    class Server(TLSXMLRPCServer):

        def handshake(self, tlsConnection):
          try:
              tlsConnection.handshakeServer(certChain=x509Chain,
                                            privateKey=x509Key,
                                            sessionCache=sessionCache)
              tlsConnection.ignoreAbruptClose = True
              return True
          except TLSError as error:
              print("Handshake failure:", str(error))
              return False

    class MyFuncs:
        def pow(self, x, y): return pow(x, y)
        def add(self, x, y): return x + y

    server = Server(address)
    server.register_instance(MyFuncs())
    #sa = server.socket.getsockname()
    #print "Serving HTTPS on", sa[0], "port", sa[1]
    for i in range(6):
        server.handle_request()

    print("Test succeeded")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        printUsage("Missing command")
    elif sys.argv[1] == "client"[:len(sys.argv[1])]:
        clientTestCmd(sys.argv[2:])
    elif sys.argv[1] == "server"[:len(sys.argv[1])]:
        serverTestCmd(sys.argv[2:])
    else:
        printUsage("Unknown command: %s" % sys.argv[1])

########NEW FILE########
__FILENAME__ = api
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

__version__ = "0.4.5"
from .constants import AlertLevel, AlertDescription, Fault
from .errors import *
from .checker import Checker
from .handshakesettings import HandshakeSettings
from .session import Session
from .sessioncache import SessionCache
from .tlsconnection import TLSConnection
from .verifierdb import VerifierDB
from .x509 import X509
from .x509certchain import X509CertChain

from .integration.httptlsconnection import HTTPTLSConnection
from .integration.tlssocketservermixin import TLSSocketServerMixIn
from .integration.tlsasyncdispatchermixin import TLSAsyncDispatcherMixIn
from .integration.pop3_tls import POP3_TLS
from .integration.imap4_tls import IMAP4_TLS
from .integration.smtp_tls import SMTP_TLS
from .integration.xmlrpctransport import XMLRPCTransport
from .integration.xmlrpcserver import TLSXMLRPCRequestHandler, \
                                      TLSXMLRPCServer, \
                                      MultiPathTLSXMLRPCServer

from .utils.cryptomath import m2cryptoLoaded, gmpyLoaded, \
                             pycryptoLoaded, prngName
from .utils.keyfactory import generateRSAKey, parsePEMKey, \
                             parseAsPublicKey, parsePrivateKey
from .utils.tackwrapper import tackpyLoaded

########NEW FILE########
__FILENAME__ = basedb
# Authors: 
#   Trevor Perrin
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""Base class for SharedKeyDB and VerifierDB."""

try:
    import anydbm
except ImportError:
    # Python 3
    import dbm as anydbm
import threading

class BaseDB(object):
    def __init__(self, filename, type):
        self.type = type
        self.filename = filename
        if self.filename:
            self.db = None
        else:
            self.db = {}
        self.lock = threading.Lock()

    def create(self):
        """Create a new on-disk database.

        @raise anydbm.error: If there's a problem creating the database.
        """
        if self.filename:
            self.db = anydbm.open(self.filename, "n") #raises anydbm.error
            self.db["--Reserved--type"] = self.type
            self.db.sync()
        else:
            self.db = {}

    def open(self):
        """Open a pre-existing on-disk database.

        @raise anydbm.error: If there's a problem opening the database.
        @raise ValueError: If the database is not of the right type.
        """
        if not self.filename:
            raise ValueError("Can only open on-disk databases")
        self.db = anydbm.open(self.filename, "w") #raises anydbm.error
        try:
            if self.db["--Reserved--type"] != self.type:
                raise ValueError("Not a %s database" % self.type)
        except KeyError:
            raise ValueError("Not a recognized database")

    def __getitem__(self, username):
        if self.db == None:
            raise AssertionError("DB not open")

        self.lock.acquire()
        try:
            valueStr = self.db[username]
        finally:
            self.lock.release()

        return self._getItem(username, valueStr)

    def __setitem__(self, username, value):
        if self.db == None:
            raise AssertionError("DB not open")

        valueStr = self._setItem(username, value)

        self.lock.acquire()
        try:
            self.db[username] = valueStr
            if self.filename:
                self.db.sync()
        finally:
            self.lock.release()

    def __delitem__(self, username):
        if self.db == None:
            raise AssertionError("DB not open")

        self.lock.acquire()
        try:
            del(self.db[username])
            if self.filename:
                self.db.sync()
        finally:
            self.lock.release()

    def __contains__(self, username):
        """Check if the database contains the specified username.

        @type username: str
        @param username: The username to check for.

        @rtype: bool
        @return: True if the database contains the username, False
        otherwise.

        """
        if self.db == None:
            raise AssertionError("DB not open")

        self.lock.acquire()
        try:
            return self.db.has_key(username)
        finally:
            self.lock.release()

    def check(self, username, param):
        value = self.__getitem__(username)
        return self._checkItem(value, username, param)

    def keys(self):
        """Return a list of usernames in the database.

        @rtype: list
        @return: The usernames in the database.
        """
        if self.db == None:
            raise AssertionError("DB not open")

        self.lock.acquire()
        try:
            usernames = self.db.keys()
        finally:
            self.lock.release()
        usernames = [u for u in usernames if not u.startswith("--Reserved--")]
        return usernames

########NEW FILE########
__FILENAME__ = checker
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Class for post-handshake certificate checking."""

from .x509 import X509
from .x509certchain import X509CertChain
from .errors import *


class Checker(object):
    """This class is passed to a handshake function to check the other
    party's certificate chain.

    If a handshake function completes successfully, but the Checker
    judges the other party's certificate chain to be missing or
    inadequate, a subclass of
    L{tlslite.errors.TLSAuthenticationError} will be raised.

    Currently, the Checker can check an X.509 chain.
    """

    def __init__(self, 
                 x509Fingerprint=None,
                 checkResumedSession=False):
        """Create a new Checker instance.

        You must pass in one of these argument combinations:
         - x509Fingerprint

        @type x509Fingerprint: str
        @param x509Fingerprint: A hex-encoded X.509 end-entity
        fingerprint which the other party's end-entity certificate must
        match.

        @type checkResumedSession: bool
        @param checkResumedSession: If resumed sessions should be
        checked.  This defaults to False, on the theory that if the
        session was checked once, we don't need to bother
        re-checking it.
        """

        self.x509Fingerprint = x509Fingerprint
        self.checkResumedSession = checkResumedSession

    def __call__(self, connection):
        """Check a TLSConnection.

        When a Checker is passed to a handshake function, this will
        be called at the end of the function.

        @type connection: L{tlslite.tlsconnection.TLSConnection}
        @param connection: The TLSConnection to examine.

        @raise tlslite.errors.TLSAuthenticationError: If the other
        party's certificate chain is missing or bad.
        """
        if not self.checkResumedSession and connection.resumed:
            return

        if self.x509Fingerprint:
            if connection._client:
                chain = connection.session.serverCertChain
            else:
                chain = connection.session.clientCertChain

            if self.x509Fingerprint:
                if isinstance(chain, X509CertChain):
                    if self.x509Fingerprint:
                        if chain.getFingerprint() != self.x509Fingerprint:
                            raise TLSFingerprintError(\
                                "X.509 fingerprint mismatch: %s, %s" % \
                                (chain.getFingerprint(), self.x509Fingerprint))
                elif chain:
                    raise TLSAuthenticationTypeError()
                else:
                    raise TLSNoAuthenticationError()
########NEW FILE########
__FILENAME__ = constants
# Authors: 
#   Trevor Perrin
#   Google - defining ClientCertificateType
#   Google (adapted by Sam Rushing) - NPN support
#   Dimitris Moraitis - Anon ciphersuites
#   Dave Baggett (Arcode Corporation) - canonicalCipherName
#
# See the LICENSE file for legal information regarding use of this file.

"""Constants used in various places."""

class CertificateType:
    x509 = 0
    openpgp = 1

class ClientCertificateType:
    rsa_sign = 1
    dss_sign = 2
    rsa_fixed_dh = 3
    dss_fixed_dh = 4
 
class HandshakeType:
    hello_request = 0
    client_hello = 1
    server_hello = 2
    certificate = 11
    server_key_exchange = 12
    certificate_request = 13
    server_hello_done = 14
    certificate_verify = 15
    client_key_exchange = 16
    finished = 20
    next_protocol = 67

class ContentType:
    change_cipher_spec = 20
    alert = 21
    handshake = 22
    application_data = 23
    all = (20,21,22,23)

class ExtensionType:    # RFC 6066 / 4366
    server_name = 0     # RFC 6066 / 4366
    srp = 12            # RFC 5054  
    cert_type = 9       # RFC 6091
    tack = 0xF300
    supports_npn = 13172
    
class NameType:
    host_name = 0

class AlertLevel:
    warning = 1
    fatal = 2

class AlertDescription:
    """
    @cvar bad_record_mac: A TLS record failed to decrypt properly.

    If this occurs during a SRP handshake it most likely
    indicates a bad password.  It may also indicate an implementation
    error, or some tampering with the data in transit.

    This alert will be signalled by the server if the SRP password is bad.  It
    may also be signalled by the server if the SRP username is unknown to the
    server, but it doesn't wish to reveal that fact.


    @cvar handshake_failure: A problem occurred while handshaking.

    This typically indicates a lack of common ciphersuites between client and
    server, or some other disagreement (about SRP parameters or key sizes,
    for example).

    @cvar protocol_version: The other party's SSL/TLS version was unacceptable.

    This indicates that the client and server couldn't agree on which version
    of SSL or TLS to use.

    @cvar user_canceled: The handshake is being cancelled for some reason.

    """

    close_notify = 0
    unexpected_message = 10
    bad_record_mac = 20
    decryption_failed = 21
    record_overflow = 22
    decompression_failure = 30
    handshake_failure = 40
    no_certificate = 41 #SSLv3
    bad_certificate = 42
    unsupported_certificate = 43
    certificate_revoked = 44
    certificate_expired = 45
    certificate_unknown = 46
    illegal_parameter = 47
    unknown_ca = 48
    access_denied = 49
    decode_error = 50
    decrypt_error = 51
    export_restriction = 60
    protocol_version = 70
    insufficient_security = 71
    internal_error = 80
    user_canceled = 90
    no_renegotiation = 100
    unknown_psk_identity = 115


class CipherSuite:
    # Weird pseudo-ciphersuite from RFC 5746
    # Signals that "secure renegotiation" is supported
    # We actually don't do any renegotiation, but this
    # prevents renegotiation attacks
    TLS_EMPTY_RENEGOTIATION_INFO_SCSV = 0x00FF
    
    TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA  = 0xC01A
    TLS_SRP_SHA_WITH_AES_128_CBC_SHA = 0xC01D
    TLS_SRP_SHA_WITH_AES_256_CBC_SHA = 0xC020

    TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA = 0xC01B
    TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA = 0xC01E
    TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA = 0xC021


    TLS_RSA_WITH_3DES_EDE_CBC_SHA = 0x000A
    TLS_RSA_WITH_AES_128_CBC_SHA = 0x002F
    TLS_RSA_WITH_AES_256_CBC_SHA = 0x0035
    TLS_RSA_WITH_RC4_128_SHA = 0x0005
    
    TLS_RSA_WITH_RC4_128_MD5 = 0x0004

    TLS_DH_ANON_WITH_AES_128_CBC_SHA = 0x0034
    TLS_DH_ANON_WITH_AES_256_CBC_SHA = 0x003A

    tripleDESSuites = []
    tripleDESSuites.append(TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA)
    tripleDESSuites.append(TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA)
    tripleDESSuites.append(TLS_RSA_WITH_3DES_EDE_CBC_SHA)

    aes128Suites = []
    aes128Suites.append(TLS_SRP_SHA_WITH_AES_128_CBC_SHA)
    aes128Suites.append(TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA)
    aes128Suites.append(TLS_RSA_WITH_AES_128_CBC_SHA)
    aes128Suites.append(TLS_DH_ANON_WITH_AES_128_CBC_SHA)

    aes256Suites = []
    aes256Suites.append(TLS_SRP_SHA_WITH_AES_256_CBC_SHA)
    aes256Suites.append(TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA)
    aes256Suites.append(TLS_RSA_WITH_AES_256_CBC_SHA)
    aes256Suites.append(TLS_DH_ANON_WITH_AES_256_CBC_SHA)

    rc4Suites = []
    rc4Suites.append(TLS_RSA_WITH_RC4_128_SHA)
    rc4Suites.append(TLS_RSA_WITH_RC4_128_MD5)
    
    shaSuites = []
    shaSuites.append(TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA)
    shaSuites.append(TLS_SRP_SHA_WITH_AES_128_CBC_SHA)
    shaSuites.append(TLS_SRP_SHA_WITH_AES_256_CBC_SHA)
    shaSuites.append(TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA)
    shaSuites.append(TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA)
    shaSuites.append(TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA)
    shaSuites.append(TLS_RSA_WITH_3DES_EDE_CBC_SHA)
    shaSuites.append(TLS_RSA_WITH_AES_128_CBC_SHA)
    shaSuites.append(TLS_RSA_WITH_AES_256_CBC_SHA)
    shaSuites.append(TLS_RSA_WITH_RC4_128_SHA)
    shaSuites.append(TLS_DH_ANON_WITH_AES_128_CBC_SHA)
    shaSuites.append(TLS_DH_ANON_WITH_AES_256_CBC_SHA)
    
    md5Suites = []
    md5Suites.append(TLS_RSA_WITH_RC4_128_MD5)

    @staticmethod
    def _filterSuites(suites, settings):
        macNames = settings.macNames
        cipherNames = settings.cipherNames
        macSuites = []
        if "sha" in macNames:
            macSuites += CipherSuite.shaSuites
        if "md5" in macNames:
            macSuites += CipherSuite.md5Suites

        cipherSuites = []
        if "aes128" in cipherNames:
            cipherSuites += CipherSuite.aes128Suites
        if "aes256" in cipherNames:
            cipherSuites += CipherSuite.aes256Suites
        if "3des" in cipherNames:
            cipherSuites += CipherSuite.tripleDESSuites
        if "rc4" in cipherNames:
            cipherSuites += CipherSuite.rc4Suites

        return [s for s in suites if s in macSuites and s in cipherSuites]

    srpSuites = []
    srpSuites.append(TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA)
    srpSuites.append(TLS_SRP_SHA_WITH_AES_128_CBC_SHA)
    srpSuites.append(TLS_SRP_SHA_WITH_AES_256_CBC_SHA)
    
    @staticmethod
    def getSrpSuites(settings):
        return CipherSuite._filterSuites(CipherSuite.srpSuites, settings)

    srpCertSuites = []
    srpCertSuites.append(TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA)
    srpCertSuites.append(TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA)
    srpCertSuites.append(TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA)
    
    @staticmethod
    def getSrpCertSuites(settings):
        return CipherSuite._filterSuites(CipherSuite.srpCertSuites, settings)

    srpAllSuites = srpSuites + srpCertSuites

    @staticmethod
    def getSrpAllSuites(settings):
        return CipherSuite._filterSuites(CipherSuite.srpAllSuites, settings)

    certSuites = []
    certSuites.append(TLS_RSA_WITH_3DES_EDE_CBC_SHA)
    certSuites.append(TLS_RSA_WITH_AES_128_CBC_SHA)
    certSuites.append(TLS_RSA_WITH_AES_256_CBC_SHA)
    certSuites.append(TLS_RSA_WITH_RC4_128_SHA)
    certSuites.append(TLS_RSA_WITH_RC4_128_MD5)
    certAllSuites = srpCertSuites + certSuites
    
    @staticmethod
    def getCertSuites(settings):
        return CipherSuite._filterSuites(CipherSuite.certSuites, settings)

    anonSuites = []
    anonSuites.append(TLS_DH_ANON_WITH_AES_128_CBC_SHA)
    anonSuites.append(TLS_DH_ANON_WITH_AES_256_CBC_SHA)
    
    @staticmethod
    def getAnonSuites(settings):
        return CipherSuite._filterSuites(CipherSuite.anonSuites, settings)

    @staticmethod
    def canonicalCipherName(ciphersuite):
        "Return the canonical name of the cipher whose number is provided."
        if ciphersuite in CipherSuite.aes128Suites:
            return "aes128"
        elif ciphersuite in CipherSuite.aes256Suites:
            return "aes256"
        elif ciphersuite in CipherSuite.rc4Suites:
            return "rc4"
        elif ciphersuite in CipherSuite.tripleDESSuites:
            return "3des"
        else:
            return None

    @staticmethod
    def canonicalMacName(ciphersuite):
        "Return the canonical name of the MAC whose number is provided."
        if ciphersuite in CipherSuite.shaSuites:
            return "sha"
        elif ciphersuite in CipherSuite.md5Suites:
            return "md5"
        else:
            return None


# The following faults are induced as part of testing.  The faultAlerts
# dictionary describes the allowed alerts that may be triggered by these
# faults.
class Fault:
    badUsername = 101
    badPassword = 102
    badA = 103
    clientSrpFaults = list(range(101,104))

    badVerifyMessage = 601
    clientCertFaults = list(range(601,602))

    badPremasterPadding = 501
    shortPremasterSecret = 502
    clientNoAuthFaults = list(range(501,503))

    badB = 201
    serverFaults = list(range(201,202))

    badFinished = 300
    badMAC = 301
    badPadding = 302
    genericFaults = list(range(300,303))

    faultAlerts = {\
        badUsername: (AlertDescription.unknown_psk_identity, \
                      AlertDescription.bad_record_mac),\
        badPassword: (AlertDescription.bad_record_mac,),\
        badA: (AlertDescription.illegal_parameter,),\
        badPremasterPadding: (AlertDescription.bad_record_mac,),\
        shortPremasterSecret: (AlertDescription.bad_record_mac,),\
        badVerifyMessage: (AlertDescription.decrypt_error,),\
        badFinished: (AlertDescription.decrypt_error,),\
        badMAC: (AlertDescription.bad_record_mac,),\
        badPadding: (AlertDescription.bad_record_mac,)
        }

    faultNames = {\
        badUsername: "bad username",\
        badPassword: "bad password",\
        badA: "bad A",\
        badPremasterPadding: "bad premaster padding",\
        shortPremasterSecret: "short premaster secret",\
        badVerifyMessage: "bad verify message",\
        badFinished: "bad finished message",\
        badMAC: "bad MAC",\
        badPadding: "bad padding"
        }

########NEW FILE########
__FILENAME__ = errors
# Authors: 
#   Trevor Perrin
#   Dave Baggett (Arcode Corporation) - Added TLSUnsupportedError.
#
# See the LICENSE file for legal information regarding use of this file.

"""Exception classes.
@sort: TLSError, TLSAbruptCloseError, TLSAlert, TLSLocalAlert, TLSRemoteAlert,
TLSAuthenticationError, TLSNoAuthenticationError, TLSAuthenticationTypeError,
TLSFingerprintError, TLSAuthorizationError, TLSValidationError, TLSFaultError,
TLSUnsupportedError
"""
import socket

from .constants import AlertDescription, AlertLevel

class TLSError(Exception):
    """Base class for all TLS Lite exceptions."""
    
    def __str__(self):
        """"At least print out the Exception time for str(...)."""
        return repr(self)    

class TLSClosedConnectionError(TLSError, socket.error):
    """An attempt was made to use the connection after it was closed."""
    pass

class TLSAbruptCloseError(TLSError):
    """The socket was closed without a proper TLS shutdown.

    The TLS specification mandates that an alert of some sort
    must be sent before the underlying socket is closed.  If the socket
    is closed without this, it could signify that an attacker is trying
    to truncate the connection.  It could also signify a misbehaving
    TLS implementation, or a random network failure.
    """
    pass

class TLSAlert(TLSError):
    """A TLS alert has been signalled."""
    pass

    _descriptionStr = {\
        AlertDescription.close_notify: "close_notify",\
        AlertDescription.unexpected_message: "unexpected_message",\
        AlertDescription.bad_record_mac: "bad_record_mac",\
        AlertDescription.decryption_failed: "decryption_failed",\
        AlertDescription.record_overflow: "record_overflow",\
        AlertDescription.decompression_failure: "decompression_failure",\
        AlertDescription.handshake_failure: "handshake_failure",\
        AlertDescription.no_certificate: "no certificate",\
        AlertDescription.bad_certificate: "bad_certificate",\
        AlertDescription.unsupported_certificate: "unsupported_certificate",\
        AlertDescription.certificate_revoked: "certificate_revoked",\
        AlertDescription.certificate_expired: "certificate_expired",\
        AlertDescription.certificate_unknown: "certificate_unknown",\
        AlertDescription.illegal_parameter: "illegal_parameter",\
        AlertDescription.unknown_ca: "unknown_ca",\
        AlertDescription.access_denied: "access_denied",\
        AlertDescription.decode_error: "decode_error",\
        AlertDescription.decrypt_error: "decrypt_error",\
        AlertDescription.export_restriction: "export_restriction",\
        AlertDescription.protocol_version: "protocol_version",\
        AlertDescription.insufficient_security: "insufficient_security",\
        AlertDescription.internal_error: "internal_error",\
        AlertDescription.user_canceled: "user_canceled",\
        AlertDescription.no_renegotiation: "no_renegotiation",\
        AlertDescription.unknown_psk_identity: "unknown_psk_identity"}

class TLSLocalAlert(TLSAlert):
    """A TLS alert has been signalled by the local implementation.

    @type description: int
    @ivar description: Set to one of the constants in
    L{tlslite.constants.AlertDescription}

    @type level: int
    @ivar level: Set to one of the constants in
    L{tlslite.constants.AlertLevel}

    @type message: str
    @ivar message: Description of what went wrong.
    """
    def __init__(self, alert, message=None):
        self.description = alert.description
        self.level = alert.level
        self.message = message

    def __str__(self):
        alertStr = TLSAlert._descriptionStr.get(self.description)
        if alertStr == None:
            alertStr = str(self.description)
        if self.message:
            return alertStr + ": " + self.message
        else:
            return alertStr

class TLSRemoteAlert(TLSAlert):
    """A TLS alert has been signalled by the remote implementation.

    @type description: int
    @ivar description: Set to one of the constants in
    L{tlslite.constants.AlertDescription}

    @type level: int
    @ivar level: Set to one of the constants in
    L{tlslite.constants.AlertLevel}
    """
    def __init__(self, alert):
        self.description = alert.description
        self.level = alert.level

    def __str__(self):
        alertStr = TLSAlert._descriptionStr.get(self.description)
        if alertStr == None:
            alertStr = str(self.description)
        return alertStr

class TLSAuthenticationError(TLSError):
    """The handshake succeeded, but the other party's authentication
    was inadequate.

    This exception will only be raised when a
    L{tlslite.Checker.Checker} has been passed to a handshake function.
    The Checker will be invoked once the handshake completes, and if
    the Checker objects to how the other party authenticated, a
    subclass of this exception will be raised.
    """
    pass

class TLSNoAuthenticationError(TLSAuthenticationError):
    """The Checker was expecting the other party to authenticate with a
    certificate chain, but this did not occur."""
    pass

class TLSAuthenticationTypeError(TLSAuthenticationError):
    """The Checker was expecting the other party to authenticate with a
    different type of certificate chain."""
    pass

class TLSFingerprintError(TLSAuthenticationError):
    """The Checker was expecting the other party to authenticate with a
    certificate chain that matches a different fingerprint."""
    pass

class TLSAuthorizationError(TLSAuthenticationError):
    """The Checker was expecting the other party to authenticate with a
    certificate chain that has a different authorization."""
    pass

class TLSValidationError(TLSAuthenticationError):
    """The Checker has determined that the other party's certificate
    chain is invalid."""
    def __init__(self, msg, info=None):
        # Include a dict containing info about this validation failure
        TLSAuthenticationError.__init__(self, msg)
        self.info = info

class TLSFaultError(TLSError):
    """The other party responded incorrectly to an induced fault.

    This exception will only occur during fault testing, when a
    TLSConnection's fault variable is set to induce some sort of
    faulty behavior, and the other party doesn't respond appropriately.
    """
    pass


class TLSUnsupportedError(TLSError):
    """The implementation doesn't support the requested (or required)
    capabilities."""
    pass

########NEW FILE########
__FILENAME__ = handshakesettings
# Authors: 
#   Trevor Perrin
#   Dave Baggett (Arcode Corporation) - cleanup handling of constants
#
# See the LICENSE file for legal information regarding use of this file.

"""Class for setting handshake parameters."""

from .constants import CertificateType
from .utils import cryptomath
from .utils import cipherfactory

# RC4 is preferred as faster in Python, works in SSL3, and immune to CBC
# issues such as timing attacks
CIPHER_NAMES = ["rc4", "aes256", "aes128", "3des"]
MAC_NAMES = ["sha"] # "md5" is allowed
CIPHER_IMPLEMENTATIONS = ["openssl", "pycrypto", "python"]
CERTIFICATE_TYPES = ["x509"]

class HandshakeSettings(object):
    """This class encapsulates various parameters that can be used with
    a TLS handshake.
    @sort: minKeySize, maxKeySize, cipherNames, macNames, certificateTypes,
    minVersion, maxVersion

    @type minKeySize: int
    @ivar minKeySize: The minimum bit length for asymmetric keys.

    If the other party tries to use SRP, RSA, or Diffie-Hellman
    parameters smaller than this length, an alert will be
    signalled.  The default is 1023.

    @type maxKeySize: int
    @ivar maxKeySize: The maximum bit length for asymmetric keys.

    If the other party tries to use SRP, RSA, or Diffie-Hellman
    parameters larger than this length, an alert will be signalled.
    The default is 8193.

    @type cipherNames: list
    @ivar cipherNames: The allowed ciphers, in order of preference.

    The allowed values in this list are 'aes256', 'aes128', '3des', and
    'rc4'.  If these settings are used with a client handshake, they
    determine the order of the ciphersuites offered in the ClientHello
    message.

    If these settings are used with a server handshake, the server will
    choose whichever ciphersuite matches the earliest entry in this
    list.

    NOTE:  If '3des' is used in this list, but TLS Lite can't find an
    add-on library that supports 3DES, then '3des' will be silently
    removed.

    The default value is ['rc4', 'aes256', 'aes128', '3des'].

    @type macNames: list
    @ivar macNames: The allowed MAC algorithms.
    
    The allowed values in this list are 'sha' and 'md5'.
    
    The default value is ['sha'].


    @type certificateTypes: list
    @ivar certificateTypes: The allowed certificate types, in order of
    preference.

    The only allowed certificate type is 'x509'.  This list is only used with a
    client handshake.  The client will advertise to the server which certificate
    types are supported, and will check that the server uses one of the
    appropriate types.


    @type minVersion: tuple
    @ivar minVersion: The minimum allowed SSL/TLS version.

    This variable can be set to (3,0) for SSL 3.0, (3,1) for
    TLS 1.0, or (3,2) for TLS 1.1.  If the other party wishes to
    use a lower version, a protocol_version alert will be signalled.
    The default is (3,0).

    @type maxVersion: tuple
    @ivar maxVersion: The maximum allowed SSL/TLS version.

    This variable can be set to (3,0) for SSL 3.0, (3,1) for
    TLS 1.0, or (3,2) for TLS 1.1.  If the other party wishes to
    use a higher version, a protocol_version alert will be signalled.
    The default is (3,2).  (WARNING: Some servers may (improperly)
    reject clients which offer support for TLS 1.1.  In this case,
    try lowering maxVersion to (3,1)).
    
    @type useExperimentalTackExtension: bool
    @ivar useExperimentalTackExtension: Whether to enabled TACK support.
    
    Note that TACK support is not standardized by IETF and uses a temporary
    TLS Extension number, so should NOT be used in production software.
    """
    def __init__(self):
        self.minKeySize = 1023
        self.maxKeySize = 8193
        self.cipherNames = CIPHER_NAMES
        self.macNames = MAC_NAMES
        self.cipherImplementations = CIPHER_IMPLEMENTATIONS
        self.certificateTypes = CERTIFICATE_TYPES
        self.minVersion = (3,0)
        self.maxVersion = (3,2)
        self.useExperimentalTackExtension = False

    # Validates the min/max fields, and certificateTypes
    # Filters out unsupported cipherNames and cipherImplementations
    def _filter(self):
        other = HandshakeSettings()
        other.minKeySize = self.minKeySize
        other.maxKeySize = self.maxKeySize
        other.cipherNames = self.cipherNames
        other.macNames = self.macNames
        other.cipherImplementations = self.cipherImplementations
        other.certificateTypes = self.certificateTypes
        other.minVersion = self.minVersion
        other.maxVersion = self.maxVersion

        if not cipherfactory.tripleDESPresent:
            other.cipherNames = [e for e in self.cipherNames if e != "3des"]
        if len(other.cipherNames)==0:
            raise ValueError("No supported ciphers")
        if len(other.certificateTypes)==0:
            raise ValueError("No supported certificate types")

        if not cryptomath.m2cryptoLoaded:
            other.cipherImplementations = \
                [e for e in other.cipherImplementations if e != "openssl"]
        if not cryptomath.pycryptoLoaded:
            other.cipherImplementations = \
                [e for e in other.cipherImplementations if e != "pycrypto"]
        if len(other.cipherImplementations)==0:
            raise ValueError("No supported cipher implementations")

        if other.minKeySize<512:
            raise ValueError("minKeySize too small")
        if other.minKeySize>16384:
            raise ValueError("minKeySize too large")
        if other.maxKeySize<512:
            raise ValueError("maxKeySize too small")
        if other.maxKeySize>16384:
            raise ValueError("maxKeySize too large")
        for s in other.cipherNames:
            if s not in CIPHER_NAMES:
                raise ValueError("Unknown cipher name: '%s'" % s)
        for s in other.cipherImplementations:
            if s not in CIPHER_IMPLEMENTATIONS:
                raise ValueError("Unknown cipher implementation: '%s'" % s)
        for s in other.certificateTypes:
            if s not in CERTIFICATE_TYPES:
                raise ValueError("Unknown certificate type: '%s'" % s)

        if other.minVersion > other.maxVersion:
            raise ValueError("Versions set incorrectly")

        if not other.minVersion in ((3,0), (3,1), (3,2)):
            raise ValueError("minVersion set incorrectly")

        if not other.maxVersion in ((3,0), (3,1), (3,2)):
            raise ValueError("maxVersion set incorrectly")

        return other

    def _getCertificateTypes(self):
        l = []
        for ct in self.certificateTypes:
            if ct == "x509":
                l.append(CertificateType.x509)
            else:
                raise AssertionError()
        return l

########NEW FILE########
__FILENAME__ = asyncstatemachine
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""
A state machine for using TLS Lite with asynchronous I/O.
"""

class AsyncStateMachine:
    """
    This is an abstract class that's used to integrate TLS Lite with
    asyncore and Twisted.

    This class signals wantsReadsEvent() and wantsWriteEvent().  When
    the underlying socket has become readable or writeable, the event
    should be passed to this class by calling inReadEvent() or
    inWriteEvent().  This class will then try to read or write through
    the socket, and will update its state appropriately.

    This class will forward higher-level events to its subclass.  For
    example, when a complete TLS record has been received,
    outReadEvent() will be called with the decrypted data.
    """

    def __init__(self):
        self._clear()

    def _clear(self):
        #These store the various asynchronous operations (i.e.
        #generators).  Only one of them, at most, is ever active at a
        #time.
        self.handshaker = None
        self.closer = None
        self.reader = None
        self.writer = None

        #This stores the result from the last call to the
        #currently active operation.  If 0 it indicates that the
        #operation wants to read, if 1 it indicates that the
        #operation wants to write.  If None, there is no active
        #operation.
        self.result = None

    def _checkAssert(self, maxActive=1):
        #This checks that only one operation, at most, is
        #active, and that self.result is set appropriately.
        activeOps = 0
        if self.handshaker:
            activeOps += 1
        if self.closer:
            activeOps += 1
        if self.reader:
            activeOps += 1
        if self.writer:
            activeOps += 1

        if self.result == None:
            if activeOps != 0:
                raise AssertionError()
        elif self.result in (0,1):
            if activeOps != 1:
                raise AssertionError()
        else:
            raise AssertionError()
        if activeOps > maxActive:
            raise AssertionError()

    def wantsReadEvent(self):
        """If the state machine wants to read.

        If an operation is active, this returns whether or not the
        operation wants to read from the socket.  If an operation is
        not active, this returns None.

        @rtype: bool or None
        @return: If the state machine wants to read.
        """
        if self.result != None:
            return self.result == 0
        return None

    def wantsWriteEvent(self):
        """If the state machine wants to write.

        If an operation is active, this returns whether or not the
        operation wants to write to the socket.  If an operation is
        not active, this returns None.

        @rtype: bool or None
        @return: If the state machine wants to write.
        """
        if self.result != None:
            return self.result == 1
        return None

    def outConnectEvent(self):
        """Called when a handshake operation completes.

        May be overridden in subclass.
        """
        pass

    def outCloseEvent(self):
        """Called when a close operation completes.

        May be overridden in subclass.
        """
        pass

    def outReadEvent(self, readBuffer):
        """Called when a read operation completes.

        May be overridden in subclass."""
        pass

    def outWriteEvent(self):
        """Called when a write operation completes.

        May be overridden in subclass."""
        pass

    def inReadEvent(self):
        """Tell the state machine it can read from the socket."""
        try:
            self._checkAssert()
            if self.handshaker:
                self._doHandshakeOp()
            elif self.closer:
                self._doCloseOp()
            elif self.reader:
                self._doReadOp()
            elif self.writer:
                self._doWriteOp()
            else:
                self.reader = self.tlsConnection.readAsync(16384)
                self._doReadOp()
        except:
            self._clear()
            raise

    def inWriteEvent(self):
        """Tell the state machine it can write to the socket."""
        try:
            self._checkAssert()
            if self.handshaker:
                self._doHandshakeOp()
            elif self.closer:
                self._doCloseOp()
            elif self.reader:
                self._doReadOp()
            elif self.writer:
                self._doWriteOp()
            else:
                self.outWriteEvent()
        except:
            self._clear()
            raise

    def _doHandshakeOp(self):
        try:
            self.result = self.handshaker.next()
        except StopIteration:
            self.handshaker = None
            self.result = None
            self.outConnectEvent()

    def _doCloseOp(self):
        try:
            self.result = self.closer.next()
        except StopIteration:
            self.closer = None
            self.result = None
            self.outCloseEvent()

    def _doReadOp(self):
        self.result = self.reader.next()
        if not self.result in (0,1):
            readBuffer = self.result
            self.reader = None
            self.result = None
            self.outReadEvent(readBuffer)

    def _doWriteOp(self):
        try:
            self.result = self.writer.next()
        except StopIteration:
            self.writer = None
            self.result = None

    def setHandshakeOp(self, handshaker):
        """Start a handshake operation.

        @type handshaker: generator
        @param handshaker: A generator created by using one of the
        asynchronous handshake functions (i.e. handshakeServerAsync, or
        handshakeClientxxx(..., async=True).
        """
        try:
            self._checkAssert(0)
            self.handshaker = handshaker
            self._doHandshakeOp()
        except:
            self._clear()
            raise

    def setServerHandshakeOp(self, **args):
        """Start a handshake operation.

        The arguments passed to this function will be forwarded to
        L{tlslite.tlsconnection.TLSConnection.handshakeServerAsync}.
        """
        handshaker = self.tlsConnection.handshakeServerAsync(**args)
        self.setHandshakeOp(handshaker)

    def setCloseOp(self):
        """Start a close operation.
        """
        try:
            self._checkAssert(0)
            self.closer = self.tlsConnection.closeAsync()
            self._doCloseOp()
        except:
            self._clear()
            raise

    def setWriteOp(self, writeBuffer):
        """Start a write operation.

        @type writeBuffer: str
        @param writeBuffer: The string to transmit.
        """
        try:
            self._checkAssert(0)
            self.writer = self.tlsConnection.writeAsync(writeBuffer)
            self._doWriteOp()
        except:
            self._clear()
            raise


########NEW FILE########
__FILENAME__ = clienthelper
# Authors: 
#   Trevor Perrin
#   Dimitris Moraitis - Anon ciphersuites
#
# See the LICENSE file for legal information regarding use of this file.

"""
A helper class for using TLS Lite with stdlib clients
(httplib, xmlrpclib, imaplib, poplib).
"""

from tlslite.checker import Checker

class ClientHelper(object):
    """This is a helper class used to integrate TLS Lite with various
    TLS clients (e.g. poplib, smtplib, httplib, etc.)"""

    def __init__(self,
              username=None, password=None,
              certChain=None, privateKey=None,
              checker=None,
              settings = None, 
              anon = False):
        """
        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP,
        or you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The constructor does not perform the TLS handshake itself, but
        simply stores these arguments for later.  The handshake is
        performed only when this class needs to connect with the
        server.  Then you should be prepared to handle TLS-specific
        exceptions.  See the client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type username: str
        @param username: SRP username.  Requires the
        'password' argument.

        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP arguments.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP arguments.

        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.
        """

        self.username = None
        self.password = None
        self.certChain = None
        self.privateKey = None
        self.checker = None
        self.anon = anon

        #SRP Authentication
        if username and password and not \
                (certChain or privateKey):
            self.username = username
            self.password = password

        #Certificate Chain Authentication
        elif certChain and privateKey and not \
                (username or password):
            self.certChain = certChain
            self.privateKey = privateKey

        #No Authentication
        elif not password and not username and not \
                certChain and not privateKey:
            pass

        else:
            raise ValueError("Bad parameters")

        self.checker = checker
        self.settings = settings

        self.tlsSession = None

    def _handshake(self, tlsConnection):
        if self.username and self.password:
            tlsConnection.handshakeClientSRP(username=self.username,
                                             password=self.password,
                                             checker=self.checker,
                                             settings=self.settings,
                                             session=self.tlsSession)
        elif self.anon:
            tlsConnection.handshakeClientAnonymous(session=self.tlsSession,
                                                settings=self.settings,
                                                checker=self.checker)
        else:
            tlsConnection.handshakeClientCert(certChain=self.certChain,
                                              privateKey=self.privateKey,
                                              checker=self.checker,
                                              settings=self.settings,
                                              session=self.tlsSession)
        self.tlsSession = tlsConnection.session
########NEW FILE########
__FILENAME__ = httptlsconnection
# Authors: 
#   Trevor Perrin
#   Kees Bos - Added ignoreAbruptClose parameter
#   Dimitris Moraitis - Anon ciphersuites
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + httplib."""

import socket
try:
    import httplib
except ImportError:
    # Python 3
    from http import client as httplib
from tlslite.tlsconnection import TLSConnection
from tlslite.integration.clienthelper import ClientHelper


class HTTPTLSConnection(httplib.HTTPConnection, ClientHelper):
    """This class extends L{httplib.HTTPConnection} to support TLS."""

    def __init__(self, host, port=None, strict=None, 
                timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                source_address=None,
                username=None, password=None,
                certChain=None, privateKey=None,
                checker=None,
                settings=None,
                ignoreAbruptClose=False, 
                anon=False):
        """Create a new HTTPTLSConnection.

        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP
        or you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The constructor does not perform the TLS handshake itself, but
        simply stores these arguments for later.  The handshake is
        performed only when this class needs to connect with the
        server.  Thus you should be prepared to handle TLS-specific
        exceptions when calling methods inherited from
        L{httplib.HTTPConnection} such as request(), connect(), and
        send().  See the client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type host: str
        @param host: Server to connect to.

        @type port: int
        @param port: Port to connect to.

        @type username: str
        @param username: SRP username.  Requires the
        'password' argument.

        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain} or
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP arguments.
        
        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP arguments. 
        
        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.          

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.

        @type ignoreAbruptClose: bool
        @param ignoreAbruptClose: ignore the TLSAbruptCloseError on 
        unexpected hangup.
        """
        if source_address:
            httplib.HTTPConnection.__init__(self, host, port, strict,
                                            timeout, source_address)
        if not source_address:
            httplib.HTTPConnection.__init__(self, host, port, strict,
                                            timeout)
        self.ignoreAbruptClose = ignoreAbruptClose
        ClientHelper.__init__(self,
                 username, password, 
                 certChain, privateKey,
                 checker,
                 settings, 
                 anon)

    def connect(self):
        httplib.HTTPConnection.connect(self)
        self.sock = TLSConnection(self.sock)
        self.sock.ignoreAbruptClose = self.ignoreAbruptClose
        ClientHelper._handshake(self, self.sock)

########NEW FILE########
__FILENAME__ = imap4_tls
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + imaplib."""

import socket
from imaplib import IMAP4
from tlslite.tlsconnection import TLSConnection
from tlslite.integration.clienthelper import ClientHelper

# IMAP TLS PORT
IMAP4_TLS_PORT = 993

class IMAP4_TLS(IMAP4, ClientHelper):
    """This class extends L{imaplib.IMAP4} with TLS support."""

    def __init__(self, host = '', port = IMAP4_TLS_PORT,
                 username=None, password=None,
                 certChain=None, privateKey=None,
                 checker=None,
                 settings=None):
        """Create a new IMAP4_TLS.

        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP
        or you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The caller should be prepared to handle TLS-specific
        exceptions.  See the client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type host: str
        @param host: Server to connect to.

        @type port: int
        @param port: Port to connect to.

        @type username: str
        @param username: SRP username.  Requires the
        'password' argument.

        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP arguments.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP arguments.
        
        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.
        """

        ClientHelper.__init__(self,
                 username, password,
                 certChain, privateKey,
                 checker,
                 settings)

        IMAP4.__init__(self, host, port)


    def open(self, host = '', port = IMAP4_TLS_PORT):
        """Setup connection to remote server on "host:port".

        This connection will be used by the routines:
        read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock = TLSConnection(self.sock)
        ClientHelper._handshake(self, self.sock)
        self.file = self.sock.makefile('rb')
########NEW FILE########
__FILENAME__ = pop3_tls
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + poplib."""

import socket
from poplib import POP3, POP3_SSL_PORT
from tlslite.tlsconnection import TLSConnection
from tlslite.integration.clienthelper import ClientHelper

class POP3_TLS(POP3, ClientHelper):
    """This class extends L{poplib.POP3} with TLS support."""

    def __init__(self, host, port = POP3_SSL_PORT,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                 username=None, password=None,
                 certChain=None, privateKey=None,
                 checker=None,
                 settings=None):
        """Create a new POP3_TLS.

        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP or
        you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The caller should be prepared to handle TLS-specific
        exceptions.  See the client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type host: str
        @param host: Server to connect to.

        @type port: int
        @param port: Port to connect to.

        @type username: str
        @param username: SRP username.
        
        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP argument.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP argument.

        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.
        """
        self.host = host
        self.port = port
        sock = socket.create_connection((host, port), timeout)
        ClientHelper.__init__(self,
                 username, password,
                 certChain, privateKey,
                 checker,
                 settings)
        connection = TLSConnection(sock) 
        ClientHelper._handshake(self, connection)
        self.sock = connection
        self.file = self.sock.makefile('rb')
        self._debugging = 0
        self.welcome = self._getresp()
########NEW FILE########
__FILENAME__ = smtp_tls
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + smtplib."""

from smtplib import SMTP
from tlslite.tlsconnection import TLSConnection
from tlslite.integration.clienthelper import ClientHelper

class SMTP_TLS(SMTP):
    """This class extends L{smtplib.SMTP} with TLS support."""

    def starttls(self,
                 username=None, password=None,
                 certChain=None, privateKey=None,
                 checker=None,
                 settings=None):
        """Puts the connection to the SMTP server into TLS mode.

        If the server supports TLS, this will encrypt the rest of the SMTP
        session.

        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP or
        you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The caller should be prepared to handle TLS-specific
        exceptions.  See the client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type username: str
        @param username: SRP username.  Requires the
        'password' argument.

        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP arguments.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP arguments.

        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.
        """
        (resp, reply) = self.docmd("STARTTLS")
        if resp == 220:
            helper = ClientHelper(
                     username, password, 
                     certChain, privateKey,
                     checker,
                     settings)
            conn = TLSConnection(self.sock)
            helper._handshake(conn)
            self.sock = conn
            self.file = conn.makefile('rb')
        return (resp, reply)
########NEW FILE########
__FILENAME__ = tlsasyncdispatchermixin
# Authors: 
#   Trevor Perrin
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + asyncore."""


import asyncore
from tlslite.tlsconnection import TLSConnection
from .asyncstatemachine import AsyncStateMachine


class TLSAsyncDispatcherMixIn(AsyncStateMachine):
    """This class can be "mixed in" with an
    L{asyncore.dispatcher} to add TLS support.

    This class essentially sits between the dispatcher and the select
    loop, intercepting events and only calling the dispatcher when
    applicable.

    In the case of handle_read(), a read operation will be activated,
    and when it completes, the bytes will be placed in a buffer where
    the dispatcher can retrieve them by calling recv(), and the
    dispatcher's handle_read() will be called.

    In the case of handle_write(), the dispatcher's handle_write() will
    be called, and when it calls send(), a write operation will be
    activated.

    To use this class, you must combine it with an asyncore.dispatcher,
    and pass in a handshake operation with setServerHandshakeOp().

    Below is an example of using this class with medusa.  This class is
    mixed in with http_channel to create http_tls_channel.  Note:
     1. the mix-in is listed first in the inheritance list

     2. the input buffer size must be at least 16K, otherwise the
       dispatcher might not read all the bytes from the TLS layer,
       leaving some bytes in limbo.

     3. IE seems to have a problem receiving a whole HTTP response in a
     single TLS record, so HTML pages containing '\\r\\n\\r\\n' won't
     be displayed on IE.

    Add the following text into 'start_medusa.py', in the 'HTTP Server'
    section::

        from tlslite import *
        s = open("./serverX509Cert.pem").read()
        x509 = X509()
        x509.parse(s)
        certChain = X509CertChain([x509])

        s = open("./serverX509Key.pem").read()
        privateKey = parsePEMKey(s, private=True)

        class http_tls_channel(TLSAsyncDispatcherMixIn,
                               http_server.http_channel):
            ac_in_buffer_size = 16384

            def __init__ (self, server, conn, addr):
                http_server.http_channel.__init__(self, server, conn, addr)
                TLSAsyncDispatcherMixIn.__init__(self, conn)
                self.tlsConnection.ignoreAbruptClose = True
                self.setServerHandshakeOp(certChain=certChain,
                                          privateKey=privateKey)

        hs.channel_class = http_tls_channel

    If the TLS layer raises an exception, the exception will be caught
    in asyncore.dispatcher, which will call close() on this class.  The
    TLS layer always closes the TLS connection before raising an
    exception, so the close operation will complete right away, causing
    asyncore.dispatcher.close() to be called, which closes the socket
    and removes this instance from the asyncore loop.

    """


    def __init__(self, sock=None):
        AsyncStateMachine.__init__(self)

        if sock:
            self.tlsConnection = TLSConnection(sock)

        #Calculate the sibling I'm being mixed in with.
        #This is necessary since we override functions
        #like readable(), handle_read(), etc., but we
        #also want to call the sibling's versions.
        for cl in self.__class__.__bases__:
            if cl != TLSAsyncDispatcherMixIn and cl != AsyncStateMachine:
                self.siblingClass = cl
                break
        else:
            raise AssertionError()

    def readable(self):
        result = self.wantsReadEvent()
        if result != None:
            return result
        return self.siblingClass.readable(self)

    def writable(self):
        result = self.wantsWriteEvent()
        if result != None:
            return result
        return self.siblingClass.writable(self)

    def handle_read(self):
        self.inReadEvent()

    def handle_write(self):
        self.inWriteEvent()

    def outConnectEvent(self):
        self.siblingClass.handle_connect(self)

    def outCloseEvent(self):
        asyncore.dispatcher.close(self)

    def outReadEvent(self, readBuffer):
        self.readBuffer = readBuffer
        self.siblingClass.handle_read(self)

    def outWriteEvent(self):
        self.siblingClass.handle_write(self)

    def recv(self, bufferSize=16384):
        if bufferSize < 16384 or self.readBuffer == None:
            raise AssertionError()
        returnValue = self.readBuffer
        self.readBuffer = None
        return returnValue

    def send(self, writeBuffer):
        self.setWriteOp(writeBuffer)
        return len(writeBuffer)

    def close(self):
        if hasattr(self, "tlsConnection"):
            self.setCloseOp()
        else:
            asyncore.dispatcher.close(self)

########NEW FILE########
__FILENAME__ = tlssocketservermixin
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""TLS Lite + SocketServer."""

from tlslite.tlsconnection import TLSConnection

class TLSSocketServerMixIn:
    """
    This class can be mixed in with any L{SocketServer.TCPServer} to
    add TLS support.

    To use this class, define a new class that inherits from it and
    some L{SocketServer.TCPServer} (with the mix-in first). Then
    implement the handshake() method, doing some sort of server
    handshake on the connection argument.  If the handshake method
    returns True, the RequestHandler will be triggered.  Below is a
    complete example of a threaded HTTPS server::

        from SocketServer import *
        from BaseHTTPServer import *
        from SimpleHTTPServer import *
        from tlslite import *

        s = open("./serverX509Cert.pem").read()
        x509 = X509()
        x509.parse(s)
        certChain = X509CertChain([x509])

        s = open("./serverX509Key.pem").read()
        privateKey = parsePEMKey(s, private=True)

        sessionCache = SessionCache()

        class MyHTTPServer(ThreadingMixIn, TLSSocketServerMixIn,
                           HTTPServer):
          def handshake(self, tlsConnection):
              try:
                  tlsConnection.handshakeServer(certChain=certChain,
                                                privateKey=privateKey,
                                                sessionCache=sessionCache)
                  tlsConnection.ignoreAbruptClose = True
                  return True
              except TLSError, error:
                  print "Handshake failure:", str(error)
                  return False

        httpd = MyHTTPServer(('localhost', 443), SimpleHTTPRequestHandler)
        httpd.serve_forever()
    """


    def finish_request(self, sock, client_address):
        tlsConnection = TLSConnection(sock)
        if self.handshake(tlsConnection) == True:
            self.RequestHandlerClass(tlsConnection, client_address, self)
            tlsConnection.close()

    #Implement this method to do some form of handshaking.  Return True
    #if the handshake finishes properly and the request is authorized.
    def handshake(self, tlsConnection):
        raise NotImplementedError()
########NEW FILE########
__FILENAME__ = xmlrpcserver
# Authors:
#   Kees Bos
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""xmlrpcserver.py - simple XML RPC server supporting TLS"""
try:
    from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
except ImportError:
    # Python 3
    from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from .tlssocketservermixin import TLSSocketServerMixIn


class TLSXMLRPCRequestHandler(SimpleXMLRPCRequestHandler):
    """XMLRPCRequestHandler using TLS"""
    
    # Redefine the setup method (see SocketServer.StreamRequestHandler)
    def setup(self):
        self.connection = self.request
        if getattr(self, 'timeout', None) is not None:
            # Python 2.7
            self.connection.settimeout(self.timeout)
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)
        
    def do_POST(self):
        """Handles the HTTPS POST request."""
        SimpleXMLRPCRequestHandler.do_POST(self)
        try:
            # shut down the connection
            self.connection.shutdown()
        except:
            pass


class TLSXMLRPCServer(TLSSocketServerMixIn,
                      SimpleXMLRPCServer):
    """Simple XML-RPC server using TLS""" 

    def __init__(self, addr, *args, **kwargs):
        if not args and not 'requestHandler' in kwargs:
            kwargs['requestHandler'] = TLSXMLRPCRequestHandler
        SimpleXMLRPCServer.__init__(self, addr, *args, **kwargs)


class MultiPathTLSXMLRPCServer(TLSXMLRPCServer):
    """Multipath XML-RPC Server using TLS"""

    def __init__(self, addr, *args, **kwargs):
        TLSXMLRPCServer.__init__(addr, *args, **kwargs)
        self.dispatchers = {}
        self.allow_none = allow_none
        self.encoding = encoding

########NEW FILE########
__FILENAME__ = xmlrpctransport
# Authors: 
#   Trevor Perrin
#   Kees Bos - Fixes for compatibility with different Python versions
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.


"""TLS Lite + xmlrpclib."""

try:
    import xmlrpclib
    import httplib
except ImportError:
    # Python 3
    from xmlrpc import client as xmlrpclib
    from http import client as httplib
from tlslite.integration.httptlsconnection import HTTPTLSConnection
from tlslite.integration.clienthelper import ClientHelper
import tlslite.errors


class XMLRPCTransport(xmlrpclib.Transport, ClientHelper):
    """Handles an HTTPS transaction to an XML-RPC server."""

    # Pre python 2.7, the make_connection returns a HTTP class
    transport = xmlrpclib.Transport()
    conn_class_is_http = not hasattr(transport, '_connection')
    del(transport)

    def __init__(self, use_datetime=0,
                 username=None, password=None,
                 certChain=None, privateKey=None,
                 checker=None,
                 settings=None,
                 ignoreAbruptClose=False):
        """Create a new XMLRPCTransport.

        An instance of this class can be passed to L{xmlrpclib.ServerProxy}
        to use TLS with XML-RPC calls::

            from tlslite import XMLRPCTransport
            from xmlrpclib import ServerProxy

            transport = XMLRPCTransport(user="alice", password="abra123")
            server = ServerProxy("https://localhost", transport)

        For client authentication, use one of these argument
        combinations:
         - username, password (SRP)
         - certChain, privateKey (certificate)

        For server authentication, you can either rely on the
        implicit mutual authentication performed by SRP or
        you can do certificate-based server
        authentication with one of these argument combinations:
         - x509Fingerprint

        Certificate-based server authentication is compatible with
        SRP or certificate-based client authentication.

        The constructor does not perform the TLS handshake itself, but
        simply stores these arguments for later.  The handshake is
        performed only when this class needs to connect with the
        server.  Thus you should be prepared to handle TLS-specific
        exceptions when calling methods of L{xmlrpclib.ServerProxy}.  See the
        client handshake functions in
        L{tlslite.TLSConnection.TLSConnection} for details on which
        exceptions might be raised.

        @type username: str
        @param username: SRP username.  Requires the
        'password' argument.

        @type password: str
        @param password: SRP password for mutual authentication.
        Requires the 'username' argument.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: Certificate chain for client authentication.
        Requires the 'privateKey' argument.  Excludes the SRP arguments.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: Private key for client authentication.
        Requires the 'certChain' argument.  Excludes the SRP arguments.

        @type checker: L{tlslite.checker.Checker}
        @param checker: Callable object called after handshaking to 
        evaluate the connection and raise an Exception if necessary.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.

        @type ignoreAbruptClose: bool
        @param ignoreAbruptClose: ignore the TLSAbruptCloseError on 
        unexpected hangup.
        """

        # self._connection is new in python 2.7, since we're using it here,
        # we'll add this ourselves too, just in case we're pre-2.7
        self._connection = (None, None)
        xmlrpclib.Transport.__init__(self, use_datetime)
        self.ignoreAbruptClose = ignoreAbruptClose
        ClientHelper.__init__(self,
                 username, password, 
                 certChain, privateKey,
                 checker,
                 settings)

    def make_connection(self, host):
        # return an existing connection if possible.  This allows
        # HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            http = self._connection[1]
        else:
            # create a HTTPS connection object from a host descriptor
            chost, extra_headers, x509 = self.get_host_info(host)

            http = HTTPTLSConnection(chost, None,
                                     username=self.username, password=self.password,
                                     certChain=self.certChain, privateKey=self.privateKey,
                                     checker=self.checker,
                                     settings=self.settings,
                                     ignoreAbruptClose=self.ignoreAbruptClose)
            # store the host argument along with the connection object
            self._connection = host, http
        if not self.conn_class_is_http:
            return http
        http2 = httplib.HTTP()
        http2._setup(http)
        return http2

########NEW FILE########
__FILENAME__ = mathtls
# Authors: 
#   Trevor Perrin
#   Dave Baggett (Arcode Corporation) - MD5 support for MAC_SSL
#
# See the LICENSE file for legal information regarding use of this file.

"""Miscellaneous helper functions."""

from .utils.compat import *
from .utils.cryptomath import *

import hmac

#1024, 1536, 2048, 3072, 4096, 6144, and 8192 bit groups]
goodGroupParameters = [(2,0xEEAF0AB9ADB38DD69C33F80AFA8FC5E86072618775FF3C0B9EA2314C9C256576D674DF7496EA81D3383B4813D692C6E0E0D5D8E250B98BE48E495C1D6089DAD15DC7D7B46154D6B6CE8EF4AD69B15D4982559B297BCF1885C529F566660E57EC68EDBC3C05726CC02FD4CBF4976EAA9AFD5138FE8376435B9FC61D2FC0EB06E3),\
                       (2,0x9DEF3CAFB939277AB1F12A8617A47BBBDBA51DF499AC4C80BEEEA9614B19CC4D5F4F5F556E27CBDE51C6A94BE4607A291558903BA0D0F84380B655BB9A22E8DCDF028A7CEC67F0D08134B1C8B97989149B609E0BE3BAB63D47548381DBC5B1FC764E3F4B53DD9DA1158BFD3E2B9C8CF56EDF019539349627DB2FD53D24B7C48665772E437D6C7F8CE442734AF7CCB7AE837C264AE3A9BEB87F8A2FE9B8B5292E5A021FFF5E91479E8CE7A28C2442C6F315180F93499A234DCF76E3FED135F9BB),\
                       (2,0xAC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4A099ED8193E0757767A13DD52312AB4B03310DCD7F48A9DA04FD50E8083969EDB767B0CF6095179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF747359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B9078717461A5B9D32E688F87748544523B524B0D57D5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB694B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73),\
                       (2,0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF),\
                       (5,0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C934063199FFFFFFFFFFFFFFFF),\
                       (5,0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C93402849236C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B332051512BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97FBEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AACC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58BB7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E6DCC4024FFFFFFFFFFFFFFFF),\
                       (5,0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C93402849236C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B332051512BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97FBEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AACC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58BB7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E6DBE115974A3926F12FEE5E438777CB6A932DF8CD8BEC4D073B931BA3BC832B68D9DD300741FA7BF8AFC47ED2576F6936BA424663AAB639C5AE4F5683423B4742BF1C978238F16CBE39D652DE3FDB8BEFC848AD922222E04A4037C0713EB57A81A23F0C73473FC646CEA306B4BCBC8862F8385DDFA9D4B7FA2C087E879683303ED5BDD3A062B3CF5B3A278A66D2A13F83F44F82DDF310EE074AB6A364597E899A0255DC164F31CC50846851DF9AB48195DED7EA1B1D510BD7EE74D73FAF36BC31ECFA268359046F4EB879F924009438B481C6CD7889A002ED5EE382BC9190DA6FC026E479558E4475677E9AA9E3050E2765694DFC81F56E880B96E7160C980DD98EDD3DFFFFFFFFFFFFFFFFF)]

def P_hash(macFunc, secret, seed, length):
    bytes = bytearray(length)
    A = seed
    index = 0
    while 1:
        A = macFunc(secret, A)
        output = macFunc(secret, A + seed)
        for c in output:
            if index >= length:
                return bytes
            bytes[index] = c
            index += 1
    return bytes

def PRF(secret, label, seed, length):
    #Split the secret into left and right halves
    # which may share a byte if len is odd
    S1 = secret[ : int(math.ceil(len(secret)/2.0))]
    S2 = secret[ int(math.floor(len(secret)/2.0)) : ]

    #Run the left half through P_MD5 and the right half through P_SHA1
    p_md5 = P_hash(HMAC_MD5, S1, label + seed, length)
    p_sha1 = P_hash(HMAC_SHA1, S2, label + seed, length)

    #XOR the output values and return the result
    for x in range(length):
        p_md5[x] ^= p_sha1[x]
    return p_md5


def PRF_SSL(secret, seed, length):
    bytes = bytearray(length)
    index = 0
    for x in range(26):
        A = bytearray([ord('A')+x] * (x+1)) # 'A', 'BB', 'CCC', etc..
        input = secret + SHA1(A + secret + seed)
        output = MD5(input)
        for c in output:
            if index >= length:
                return bytes
            bytes[index] = c
            index += 1
    return bytes

def calcMasterSecret(version, premasterSecret, clientRandom, serverRandom):
    if version == (3,0):
        masterSecret = PRF_SSL(premasterSecret,
                            clientRandom + serverRandom, 48)
    elif version in ((3,1), (3,2)):
        masterSecret = PRF(premasterSecret, b"master secret",
                            clientRandom + serverRandom, 48)
    else:
        raise AssertionError()
    return masterSecret


def makeX(salt, username, password):
    if len(username)>=256:
        raise ValueError("username too long")
    if len(salt)>=256:
        raise ValueError("salt too long")
    innerHashResult = SHA1(username + bytearray(b":") + password)
    outerHashResult = SHA1(salt + innerHashResult)
    return bytesToNumber(outerHashResult)

#This function is used by VerifierDB.makeVerifier
def makeVerifier(username, password, bits):
    bitsIndex = {1024:0, 1536:1, 2048:2, 3072:3, 4096:4, 6144:5, 8192:6}[bits]
    g,N = goodGroupParameters[bitsIndex]
    salt = getRandomBytes(16)
    x = makeX(salt, username, password)
    verifier = powMod(g, x, N)
    return N, g, salt, verifier

def PAD(n, x):
    nLength = len(numberToByteArray(n))
    b = numberToByteArray(x)
    if len(b) < nLength:
        b = (b"\0" * (nLength-len(b))) + b
    return b

def makeU(N, A, B):
  return bytesToNumber(SHA1(PAD(N, A) + PAD(N, B)))

def makeK(N, g):
  return bytesToNumber(SHA1(numberToByteArray(N) + PAD(N, g)))

def createHMAC(k, digestmod=hashlib.sha1):
    return hmac.HMAC(k, digestmod=digestmod)

def createMAC_SSL(k, digestmod=None):
    mac = MAC_SSL()
    mac.create(k, digestmod=digestmod)
    return mac


class MAC_SSL(object):
    def create(self, k, digestmod=None):
        self.digestmod = digestmod or hashlib.sha1
        # Repeat pad bytes 48 times for MD5; 40 times for other hash functions.
        self.digest_size = 16 if (self.digestmod is hashlib.md5) else 20
        repeat = 40 if self.digest_size == 20 else 48
        opad = b"\x5C" * repeat
        ipad = b"\x36" * repeat

        self.ohash = self.digestmod(k + opad)
        self.ihash = self.digestmod(k + ipad)

    def update(self, m):
        self.ihash.update(m)

    def copy(self):
        new = MAC_SSL()
        new.ihash = self.ihash.copy()
        new.ohash = self.ohash.copy()
        new.digestmod = self.digestmod
        new.digest_size = self.digest_size
        return new

    def digest(self):
        ohash2 = self.ohash.copy()
        ohash2.update(self.ihash.digest())
        return bytearray(ohash2.digest())

########NEW FILE########
__FILENAME__ = messages
# Authors: 
#   Trevor Perrin
#   Google - handling CertificateRequest.certificate_types
#   Google (adapted by Sam Rushing and Marcelo Fernandez) - NPN support
#   Dimitris Moraitis - Anon ciphersuites
#
# See the LICENSE file for legal information regarding use of this file.

"""Classes representing TLS messages."""

from .utils.compat import *
from .utils.cryptomath import *
from .errors import *
from .utils.codec import *
from .constants import *
from .x509 import X509
from .x509certchain import X509CertChain
from .utils.tackwrapper import *

class RecordHeader3(object):
    def __init__(self):
        self.type = 0
        self.version = (0,0)
        self.length = 0
        self.ssl2 = False

    def create(self, version, type, length):
        self.type = type
        self.version = version
        self.length = length
        return self

    def write(self):
        w = Writer()
        w.add(self.type, 1)
        w.add(self.version[0], 1)
        w.add(self.version[1], 1)
        w.add(self.length, 2)
        return w.bytes

    def parse(self, p):
        self.type = p.get(1)
        self.version = (p.get(1), p.get(1))
        self.length = p.get(2)
        self.ssl2 = False
        return self

class RecordHeader2(object):
    def __init__(self):
        self.type = 0
        self.version = (0,0)
        self.length = 0
        self.ssl2 = True

    def parse(self, p):
        if p.get(1)!=128:
            raise SyntaxError()
        self.type = ContentType.handshake
        self.version = (2,0)
        #We don't support 2-byte-length-headers; could be a problem
        self.length = p.get(1)
        return self


class Alert(object):
    def __init__(self):
        self.contentType = ContentType.alert
        self.level = 0
        self.description = 0

    def create(self, description, level=AlertLevel.fatal):
        self.level = level
        self.description = description
        return self

    def parse(self, p):
        p.setLengthCheck(2)
        self.level = p.get(1)
        self.description = p.get(1)
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.add(self.level, 1)
        w.add(self.description, 1)
        return w.bytes


class HandshakeMsg(object):
    def __init__(self, handshakeType):
        self.contentType = ContentType.handshake
        self.handshakeType = handshakeType
    
    def postWrite(self, w):
        headerWriter = Writer()
        headerWriter.add(self.handshakeType, 1)
        headerWriter.add(len(w.bytes), 3)
        return headerWriter.bytes + w.bytes

class ClientHello(HandshakeMsg):
    def __init__(self, ssl2=False):
        HandshakeMsg.__init__(self, HandshakeType.client_hello)
        self.ssl2 = ssl2
        self.client_version = (0,0)
        self.random = bytearray(32)
        self.session_id = bytearray(0)
        self.cipher_suites = []         # a list of 16-bit values
        self.certificate_types = [CertificateType.x509]
        self.compression_methods = []   # a list of 8-bit values
        self.srp_username = None        # a string
        self.tack = False
        self.supports_npn = False
        self.server_name = bytearray(0)

    def create(self, version, random, session_id, cipher_suites,
               certificate_types=None, srpUsername=None,
               tack=False, supports_npn=False, serverName=None):
        self.client_version = version
        self.random = random
        self.session_id = session_id
        self.cipher_suites = cipher_suites
        self.certificate_types = certificate_types
        self.compression_methods = [0]
        if srpUsername:
            self.srp_username = bytearray(srpUsername, "utf-8")
        self.tack = tack
        self.supports_npn = supports_npn
        if serverName:
            self.server_name = bytearray(serverName, "utf-8")
        return self

    def parse(self, p):
        if self.ssl2:
            self.client_version = (p.get(1), p.get(1))
            cipherSpecsLength = p.get(2)
            sessionIDLength = p.get(2)
            randomLength = p.get(2)
            self.cipher_suites = p.getFixList(3, cipherSpecsLength//3)
            self.session_id = p.getFixBytes(sessionIDLength)
            self.random = p.getFixBytes(randomLength)
            if len(self.random) < 32:
                zeroBytes = 32-len(self.random)
                self.random = bytearray(zeroBytes) + self.random
            self.compression_methods = [0]#Fake this value

            #We're not doing a stopLengthCheck() for SSLv2, oh well..
        else:
            p.startLengthCheck(3)
            self.client_version = (p.get(1), p.get(1))
            self.random = p.getFixBytes(32)
            self.session_id = p.getVarBytes(1)
            self.cipher_suites = p.getVarList(2, 2)
            self.compression_methods = p.getVarList(1, 1)
            if not p.atLengthCheck():
                totalExtLength = p.get(2)
                soFar = 0
                while soFar != totalExtLength:
                    extType = p.get(2)
                    extLength = p.get(2)
                    index1 = p.index
                    if extType == ExtensionType.srp:
                        self.srp_username = p.getVarBytes(1)
                    elif extType == ExtensionType.cert_type:
                        self.certificate_types = p.getVarList(1, 1)
                    elif extType == ExtensionType.tack:
                        self.tack = True
                    elif extType == ExtensionType.supports_npn:
                        self.supports_npn = True
                    elif extType == ExtensionType.server_name:
                        serverNameListBytes = p.getFixBytes(extLength)
                        p2 = Parser(serverNameListBytes)
                        p2.startLengthCheck(2)
                        while 1:
                            if p2.atLengthCheck():
                                break # no host_name, oh well
                            name_type = p2.get(1)
                            hostNameBytes = p2.getVarBytes(2)
                            if name_type == NameType.host_name:
                                self.server_name = hostNameBytes
                                break
                    else:
                        _ = p.getFixBytes(extLength)
                    index2 = p.index
                    if index2 - index1 != extLength:
                        raise SyntaxError("Bad length for extension_data")
                    soFar += 4 + extLength
            p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.add(self.client_version[0], 1)
        w.add(self.client_version[1], 1)
        w.addFixSeq(self.random, 1)
        w.addVarSeq(self.session_id, 1, 1)
        w.addVarSeq(self.cipher_suites, 2, 2)
        w.addVarSeq(self.compression_methods, 1, 1)

        w2 = Writer() # For Extensions
        if self.certificate_types and self.certificate_types != \
                [CertificateType.x509]:
            w2.add(ExtensionType.cert_type, 2)
            w2.add(len(self.certificate_types)+1, 2)
            w2.addVarSeq(self.certificate_types, 1, 1)
        if self.srp_username:
            w2.add(ExtensionType.srp, 2)
            w2.add(len(self.srp_username)+1, 2)
            w2.addVarSeq(self.srp_username, 1, 1)
        if self.supports_npn:
            w2.add(ExtensionType.supports_npn, 2)
            w2.add(0, 2)
        if self.server_name:
            w2.add(ExtensionType.server_name, 2)
            w2.add(len(self.server_name)+5, 2)
            w2.add(len(self.server_name)+3, 2)            
            w2.add(NameType.host_name, 1)
            w2.addVarSeq(self.server_name, 1, 2) 
        if self.tack:
            w2.add(ExtensionType.tack, 2)
            w2.add(0, 2)
        if len(w2.bytes):
            w.add(len(w2.bytes), 2)
            w.bytes += w2.bytes
        return self.postWrite(w)

class BadNextProtos(Exception):
    def __init__(self, l):
        self.length = l

    def __str__(self):
        return 'Cannot encode a list of next protocols because it contains an element with invalid length %d. Element lengths must be 0 < x < 256' % self.length

class ServerHello(HandshakeMsg):
    def __init__(self):
        HandshakeMsg.__init__(self, HandshakeType.server_hello)
        self.server_version = (0,0)
        self.random = bytearray(32)
        self.session_id = bytearray(0)
        self.cipher_suite = 0
        self.certificate_type = CertificateType.x509
        self.compression_method = 0
        self.tackExt = None
        self.next_protos_advertised = None
        self.next_protos = None

    def create(self, version, random, session_id, cipher_suite,
               certificate_type, tackExt, next_protos_advertised):
        self.server_version = version
        self.random = random
        self.session_id = session_id
        self.cipher_suite = cipher_suite
        self.certificate_type = certificate_type
        self.compression_method = 0
        self.tackExt = tackExt
        self.next_protos_advertised = next_protos_advertised
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        self.server_version = (p.get(1), p.get(1))
        self.random = p.getFixBytes(32)
        self.session_id = p.getVarBytes(1)
        self.cipher_suite = p.get(2)
        self.compression_method = p.get(1)
        if not p.atLengthCheck():
            totalExtLength = p.get(2)
            soFar = 0
            while soFar != totalExtLength:
                extType = p.get(2)
                extLength = p.get(2)
                if extType == ExtensionType.cert_type:
                    if extLength != 1:
                        raise SyntaxError()
                    self.certificate_type = p.get(1)
                elif extType == ExtensionType.tack and tackpyLoaded:
                    self.tackExt = TackExtension(p.getFixBytes(extLength))
                elif extType == ExtensionType.supports_npn:
                    self.next_protos = self.__parse_next_protos(p.getFixBytes(extLength))
                else:
                    p.getFixBytes(extLength)
                soFar += 4 + extLength
        p.stopLengthCheck()
        return self

    def __parse_next_protos(self, b):
        protos = []
        while True:
            if len(b) == 0:
                break
            l = b[0]
            b = b[1:]
            if len(b) < l:
                raise BadNextProtos(len(b))
            protos.append(b[:l])
            b = b[l:]
        return protos

    def __next_protos_encoded(self):
        b = bytearray()
        for e in self.next_protos_advertised:
            if len(e) > 255 or len(e) == 0:
                raise BadNextProtos(len(e))
            b += bytearray( [len(e)] ) + bytearray(e)
        return b

    def write(self):
        w = Writer()
        w.add(self.server_version[0], 1)
        w.add(self.server_version[1], 1)
        w.addFixSeq(self.random, 1)
        w.addVarSeq(self.session_id, 1, 1)
        w.add(self.cipher_suite, 2)
        w.add(self.compression_method, 1)

        w2 = Writer() # For Extensions
        if self.certificate_type and self.certificate_type != \
                CertificateType.x509:
            w2.add(ExtensionType.cert_type, 2)
            w2.add(1, 2)
            w2.add(self.certificate_type, 1)
        if self.tackExt:
            b = self.tackExt.serialize()
            w2.add(ExtensionType.tack, 2)
            w2.add(len(b), 2)
            w2.bytes += b
        if self.next_protos_advertised is not None:
            encoded_next_protos_advertised = self.__next_protos_encoded()
            w2.add(ExtensionType.supports_npn, 2)
            w2.add(len(encoded_next_protos_advertised), 2)
            w2.addFixSeq(encoded_next_protos_advertised, 1)
        if len(w2.bytes):
            w.add(len(w2.bytes), 2)
            w.bytes += w2.bytes        
        return self.postWrite(w)


class Certificate(HandshakeMsg):
    def __init__(self, certificateType):
        HandshakeMsg.__init__(self, HandshakeType.certificate)
        self.certificateType = certificateType
        self.certChain = None

    def create(self, certChain):
        self.certChain = certChain
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        if self.certificateType == CertificateType.x509:
            chainLength = p.get(3)
            index = 0
            certificate_list = []
            while index != chainLength:
                certBytes = p.getVarBytes(3)
                x509 = X509()
                x509.parseBinary(certBytes)
                certificate_list.append(x509)
                index += len(certBytes)+3
            if certificate_list:
                self.certChain = X509CertChain(certificate_list)
        else:
            raise AssertionError()

        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        if self.certificateType == CertificateType.x509:
            chainLength = 0
            if self.certChain:
                certificate_list = self.certChain.x509List
            else:
                certificate_list = []
            #determine length
            for cert in certificate_list:
                bytes = cert.writeBytes()
                chainLength += len(bytes)+3
            #add bytes
            w.add(chainLength, 3)
            for cert in certificate_list:
                bytes = cert.writeBytes()
                w.addVarSeq(bytes, 1, 3)
        else:
            raise AssertionError()
        return self.postWrite(w)

class CertificateRequest(HandshakeMsg):
    def __init__(self):
        HandshakeMsg.__init__(self, HandshakeType.certificate_request)
        #Apple's Secure Transport library rejects empty certificate_types, so
        #default to rsa_sign.
        self.certificate_types = [ClientCertificateType.rsa_sign]
        self.certificate_authorities = []

    def create(self, certificate_types, certificate_authorities):
        self.certificate_types = certificate_types
        self.certificate_authorities = certificate_authorities
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        self.certificate_types = p.getVarList(1, 1)
        ca_list_length = p.get(2)
        index = 0
        self.certificate_authorities = []
        while index != ca_list_length:
          ca_bytes = p.getVarBytes(2)
          self.certificate_authorities.append(ca_bytes)
          index += len(ca_bytes)+2
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.addVarSeq(self.certificate_types, 1, 1)
        caLength = 0
        #determine length
        for ca_dn in self.certificate_authorities:
            caLength += len(ca_dn)+2
        w.add(caLength, 2)
        #add bytes
        for ca_dn in self.certificate_authorities:
            w.addVarSeq(ca_dn, 1, 2)
        return self.postWrite(w)

class ServerKeyExchange(HandshakeMsg):
    def __init__(self, cipherSuite):
        HandshakeMsg.__init__(self, HandshakeType.server_key_exchange)
        self.cipherSuite = cipherSuite
        self.srp_N = 0
        self.srp_g = 0
        self.srp_s = bytearray(0)
        self.srp_B = 0
        # Anon DH params:
        self.dh_p = 0
        self.dh_g = 0
        self.dh_Ys = 0
        self.signature = bytearray(0)

    def createSRP(self, srp_N, srp_g, srp_s, srp_B):
        self.srp_N = srp_N
        self.srp_g = srp_g
        self.srp_s = srp_s
        self.srp_B = srp_B
        return self
    
    def createDH(self, dh_p, dh_g, dh_Ys):
        self.dh_p = dh_p
        self.dh_g = dh_g
        self.dh_Ys = dh_Ys
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        if self.cipherSuite in CipherSuite.srpAllSuites:
            self.srp_N = bytesToNumber(p.getVarBytes(2))
            self.srp_g = bytesToNumber(p.getVarBytes(2))
            self.srp_s = p.getVarBytes(1)
            self.srp_B = bytesToNumber(p.getVarBytes(2))
            if self.cipherSuite in CipherSuite.srpCertSuites:
                self.signature = p.getVarBytes(2)
        elif self.cipherSuite in CipherSuite.anonSuites:
            self.dh_p = bytesToNumber(p.getVarBytes(2))
            self.dh_g = bytesToNumber(p.getVarBytes(2))
            self.dh_Ys = bytesToNumber(p.getVarBytes(2))
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        if self.cipherSuite in CipherSuite.srpAllSuites:
            w.addVarSeq(numberToByteArray(self.srp_N), 1, 2)
            w.addVarSeq(numberToByteArray(self.srp_g), 1, 2)
            w.addVarSeq(self.srp_s, 1, 1)
            w.addVarSeq(numberToByteArray(self.srp_B), 1, 2)
            if self.cipherSuite in CipherSuite.srpCertSuites:
                w.addVarSeq(self.signature, 1, 2)
        elif self.cipherSuite in CipherSuite.anonSuites:
            w.addVarSeq(numberToByteArray(self.dh_p), 1, 2)
            w.addVarSeq(numberToByteArray(self.dh_g), 1, 2)
            w.addVarSeq(numberToByteArray(self.dh_Ys), 1, 2)
            if self.cipherSuite in []: # TODO support for signed_params
                w.addVarSeq(self.signature, 1, 2)
        return self.postWrite(w)

    def hash(self, clientRandom, serverRandom):
        oldCipherSuite = self.cipherSuite
        self.cipherSuite = None
        try:
            bytes = clientRandom + serverRandom + self.write()[4:]
            return MD5(bytes) + SHA1(bytes)
        finally:
            self.cipherSuite = oldCipherSuite

class ServerHelloDone(HandshakeMsg):
    def __init__(self):
        HandshakeMsg.__init__(self, HandshakeType.server_hello_done)

    def create(self):
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        return self.postWrite(w)

class ClientKeyExchange(HandshakeMsg):
    def __init__(self, cipherSuite, version=None):
        HandshakeMsg.__init__(self, HandshakeType.client_key_exchange)
        self.cipherSuite = cipherSuite
        self.version = version
        self.srp_A = 0
        self.encryptedPreMasterSecret = bytearray(0)

    def createSRP(self, srp_A):
        self.srp_A = srp_A
        return self

    def createRSA(self, encryptedPreMasterSecret):
        self.encryptedPreMasterSecret = encryptedPreMasterSecret
        return self
    
    def createDH(self, dh_Yc):
        self.dh_Yc = dh_Yc
        return self
    
    def parse(self, p):
        p.startLengthCheck(3)
        if self.cipherSuite in CipherSuite.srpAllSuites:
            self.srp_A = bytesToNumber(p.getVarBytes(2))
        elif self.cipherSuite in CipherSuite.certSuites:
            if self.version in ((3,1), (3,2)):
                self.encryptedPreMasterSecret = p.getVarBytes(2)
            elif self.version == (3,0):
                self.encryptedPreMasterSecret = \
                    p.getFixBytes(len(p.bytes)-p.index)
            else:
                raise AssertionError()
        elif self.cipherSuite in CipherSuite.anonSuites:
            self.dh_Yc = bytesToNumber(p.getVarBytes(2))            
        else:
            raise AssertionError()
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        if self.cipherSuite in CipherSuite.srpAllSuites:
            w.addVarSeq(numberToByteArray(self.srp_A), 1, 2)
        elif self.cipherSuite in CipherSuite.certSuites:
            if self.version in ((3,1), (3,2)):
                w.addVarSeq(self.encryptedPreMasterSecret, 1, 2)
            elif self.version == (3,0):
                w.addFixSeq(self.encryptedPreMasterSecret, 1)
            else:
                raise AssertionError()
        elif self.cipherSuite in CipherSuite.anonSuites:
            w.addVarSeq(numberToByteArray(self.dh_Yc), 1, 2)            
        else:
            raise AssertionError()
        return self.postWrite(w)

class CertificateVerify(HandshakeMsg):
    def __init__(self):
        HandshakeMsg.__init__(self, HandshakeType.certificate_verify)
        self.signature = bytearray(0)

    def create(self, signature):
        self.signature = signature
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        self.signature = p.getVarBytes(2)
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.addVarSeq(self.signature, 1, 2)
        return self.postWrite(w)

class ChangeCipherSpec(object):
    def __init__(self):
        self.contentType = ContentType.change_cipher_spec
        self.type = 1

    def create(self):
        self.type = 1
        return self

    def parse(self, p):
        p.setLengthCheck(1)
        self.type = p.get(1)
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.add(self.type,1)
        return w.bytes


class NextProtocol(HandshakeMsg):
    def __init__(self):
        HandshakeMsg.__init__(self, HandshakeType.next_protocol)
        self.next_proto = None

    def create(self, next_proto):
        self.next_proto = next_proto
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        self.next_proto = p.getVarBytes(1)
        _ = p.getVarBytes(1)
        p.stopLengthCheck()
        return self

    def write(self, trial=False):
        w = Writer()
        w.addVarSeq(self.next_proto, 1, 1)
        paddingLen = 32 - ((len(self.next_proto) + 2) % 32)
        w.addVarSeq(bytearray(paddingLen), 1, 1)
        return self.postWrite(w)

class Finished(HandshakeMsg):
    def __init__(self, version):
        HandshakeMsg.__init__(self, HandshakeType.finished)
        self.version = version
        self.verify_data = bytearray(0)

    def create(self, verify_data):
        self.verify_data = verify_data
        return self

    def parse(self, p):
        p.startLengthCheck(3)
        if self.version == (3,0):
            self.verify_data = p.getFixBytes(36)
        elif self.version in ((3,1), (3,2)):
            self.verify_data = p.getFixBytes(12)
        else:
            raise AssertionError()
        p.stopLengthCheck()
        return self

    def write(self):
        w = Writer()
        w.addFixSeq(self.verify_data, 1)
        return self.postWrite(w)

class ApplicationData(object):
    def __init__(self):
        self.contentType = ContentType.application_data
        self.bytes = bytearray(0)

    def create(self, bytes):
        self.bytes = bytes
        return self
        
    def splitFirstByte(self):
        newMsg = ApplicationData().create(self.bytes[:1])
        self.bytes = self.bytes[1:]
        return newMsg

    def parse(self, p):
        self.bytes = p.bytes
        return self

    def write(self):
        return self.bytes

########NEW FILE########
__FILENAME__ = session
# Authors: 
#   Trevor Perrin
#   Dave Baggett (Arcode Corporation) - canonicalCipherName
#
# See the LICENSE file for legal information regarding use of this file.

"""Class representing a TLS session."""

from .utils.compat import *
from .mathtls import *
from .constants import *

class Session(object):
    """
    This class represents a TLS session.

    TLS distinguishes between connections and sessions.  A new
    handshake creates both a connection and a session.  Data is
    transmitted over the connection.

    The session contains a more permanent record of the handshake.  The
    session can be inspected to determine handshake results.  The
    session can also be used to create a new connection through
    "session resumption". If the client and server both support this,
    they can create a new connection based on an old session without
    the overhead of a full handshake.

    The session for a L{tlslite.TLSConnection.TLSConnection} can be
    retrieved from the connection's 'session' attribute.

    @type srpUsername: str
    @ivar srpUsername: The client's SRP username (or None).

    @type clientCertChain: L{tlslite.x509certchain.X509CertChain}
    @ivar clientCertChain: The client's certificate chain (or None).

    @type serverCertChain: L{tlslite.x509certchain.X509CertChain}
    @ivar serverCertChain: The server's certificate chain (or None).

    @type tackExt: L{tack.structures.TackExtension.TackExtension}
    @ivar tackExt: The server's TackExtension (or None).

    @type tackInHelloExt: L{bool}
    @ivar tackInHelloExt: True if a TACK was presented via TLS Extension.
    """

    def __init__(self):
        self.masterSecret = bytearray(0)
        self.sessionID = bytearray(0)
        self.cipherSuite = 0
        self.srpUsername = ""
        self.clientCertChain = None
        self.serverCertChain = None
        self.tackExt = None
        self.tackInHelloExt = False
        self.serverName = ""
        self.resumable = False

    def create(self, masterSecret, sessionID, cipherSuite,
            srpUsername, clientCertChain, serverCertChain, 
            tackExt, tackInHelloExt, serverName, resumable=True):
        self.masterSecret = masterSecret
        self.sessionID = sessionID
        self.cipherSuite = cipherSuite
        self.srpUsername = srpUsername
        self.clientCertChain = clientCertChain
        self.serverCertChain = serverCertChain
        self.tackExt = tackExt
        self.tackInHelloExt = tackInHelloExt  
        self.serverName = serverName
        self.resumable = resumable

    def _clone(self):
        other = Session()
        other.masterSecret = self.masterSecret
        other.sessionID = self.sessionID
        other.cipherSuite = self.cipherSuite
        other.srpUsername = self.srpUsername
        other.clientCertChain = self.clientCertChain
        other.serverCertChain = self.serverCertChain
        other.tackExt = self.tackExt
        other.tackInHelloExt = self.tackInHelloExt
        other.serverName = self.serverName
        other.resumable = self.resumable
        return other

    def valid(self):
        """If this session can be used for session resumption.

        @rtype: bool
        @return: If this session can be used for session resumption.
        """
        return self.resumable and self.sessionID

    def _setResumable(self, boolean):
        #Only let it be set to True if the sessionID is non-null
        if (not boolean) or (boolean and self.sessionID):
            self.resumable = boolean

    def getTackId(self):
        if self.tackExt and self.tackExt.tack:
            return self.tackExt.tack.getTackId()
        else:
            return None
        
    def getBreakSigs(self):
        if self.tackExt and self.tackExt.break_sigs:
            return self.tackExt.break_sigs
        else:
            return None

    def getCipherName(self):
        """Get the name of the cipher used with this connection.

        @rtype: str
        @return: The name of the cipher used with this connection.
        """
        return CipherSuite.canonicalCipherName(self.cipherSuite)
        
    def getMacName(self):
        """Get the name of the HMAC hash algo used with this connection.

        @rtype: str
        @return: The name of the HMAC hash algo used with this connection.
        """
        return CipherSuite.canonicalMacName(self.cipherSuite)

########NEW FILE########
__FILENAME__ = sessioncache
# Authors: 
#   Trevor Perrin
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""Class for caching TLS sessions."""

import threading
import time

class SessionCache(object):
    """This class is used by the server to cache TLS sessions.

    Caching sessions allows the client to use TLS session resumption
    and avoid the expense of a full handshake.  To use this class,
    simply pass a SessionCache instance into the server handshake
    function.

    This class is thread-safe.
    """

    #References to these instances
    #are also held by the caller, who may change the 'resumable'
    #flag, so the SessionCache must return the same instances
    #it was passed in.

    def __init__(self, maxEntries=10000, maxAge=14400):
        """Create a new SessionCache.

        @type maxEntries: int
        @param maxEntries: The maximum size of the cache.  When this
        limit is reached, the oldest sessions will be deleted as
        necessary to make room for new ones.  The default is 10000.

        @type maxAge: int
        @param maxAge:  The number of seconds before a session expires
        from the cache.  The default is 14400 (i.e. 4 hours)."""

        self.lock = threading.Lock()

        # Maps sessionIDs to sessions
        self.entriesDict = {}

        #Circular list of (sessionID, timestamp) pairs
        self.entriesList = [(None,None)] * maxEntries

        self.firstIndex = 0
        self.lastIndex = 0
        self.maxAge = maxAge

    def __getitem__(self, sessionID):
        self.lock.acquire()
        try:
            self._purge() #Delete old items, so we're assured of a new one
            session = self.entriesDict[bytes(sessionID)]

            #When we add sessions they're resumable, but it's possible
            #for the session to be invalidated later on (if a fatal alert
            #is returned), so we have to check for resumability before
            #returning the session.

            if session.valid():
                return session
            else:
                raise KeyError()
        finally:
            self.lock.release()


    def __setitem__(self, sessionID, session):
        self.lock.acquire()
        try:
            #Add the new element
            self.entriesDict[bytes(sessionID)] = session
            self.entriesList[self.lastIndex] = (sessionID, time.time())
            self.lastIndex = (self.lastIndex+1) % len(self.entriesList)

            #If the cache is full, we delete the oldest element to make an
            #empty space
            if self.lastIndex == self.firstIndex:
                del(self.entriesDict[self.entriesList[self.firstIndex][0]])
                self.firstIndex = (self.firstIndex+1) % len(self.entriesList)
        finally:
            self.lock.release()

    #Delete expired items
    def _purge(self):
        currentTime = time.time()

        #Search through the circular list, deleting expired elements until
        #we reach a non-expired element.  Since elements in list are
        #ordered in time, we can break once we reach the first non-expired
        #element
        index = self.firstIndex
        while index != self.lastIndex:
            if currentTime - self.entriesList[index][1] > self.maxAge:
                del(self.entriesDict[self.entriesList[index][0]])
                index = (index+1) % len(self.entriesList)
            else:
                break
        self.firstIndex = index

def _test():
    import doctest, SessionCache
    return doctest.testmod(SessionCache)

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = tlsconnection
# Authors: 
#   Trevor Perrin
#   Google - added reqCAs parameter
#   Google (adapted by Sam Rushing and Marcelo Fernandez) - NPN support
#   Dimitris Moraitis - Anon ciphersuites
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""
MAIN CLASS FOR TLS LITE (START HERE!).
"""

import socket
from .utils.compat import formatExceptionTrace
from .tlsrecordlayer import TLSRecordLayer
from .session import Session
from .constants import *
from .utils.cryptomath import getRandomBytes
from .errors import *
from .messages import *
from .mathtls import *
from .handshakesettings import HandshakeSettings
from .utils.tackwrapper import *


class TLSConnection(TLSRecordLayer):
    """
    This class wraps a socket and provides TLS handshaking and data
    transfer.

    To use this class, create a new instance, passing a connected
    socket into the constructor.  Then call some handshake function.
    If the handshake completes without raising an exception, then a TLS
    connection has been negotiated.  You can transfer data over this
    connection as if it were a socket.

    This class provides both synchronous and asynchronous versions of
    its key functions.  The synchronous versions should be used when
    writing single-or multi-threaded code using blocking sockets.  The
    asynchronous versions should be used when performing asynchronous,
    event-based I/O with non-blocking sockets.

    Asynchronous I/O is a complicated subject; typically, you should
    not use the asynchronous functions directly, but should use some
    framework like asyncore or Twisted which TLS Lite integrates with
    (see
    L{tlslite.integration.tlsasyncdispatchermixin.TLSAsyncDispatcherMixIn}).
    """

    def __init__(self, sock):
        """Create a new TLSConnection instance.

        @param sock: The socket data will be transmitted on.  The
        socket should already be connected.  It may be in blocking or
        non-blocking mode.

        @type sock: L{socket.socket}
        """
        TLSRecordLayer.__init__(self, sock)

    #*********************************************************
    # Client Handshake Functions
    #*********************************************************

    def handshakeClientAnonymous(self, session=None, settings=None, 
                                checker=None, serverName="",
                                async=False):
        """Perform an anonymous handshake in the role of client.

        This function performs an SSL or TLS handshake using an
        anonymous Diffie Hellman ciphersuite.
        
        Like any handshake function, this can be called on a closed
        TLS connection, or on a TLS connection that is already open.
        If called on an open connection it performs a re-handshake.

        If the function completes without raising an exception, the
        TLS connection will be open and available for data transfer.

        If an exception is raised, the connection will have been
        automatically closed (if it was ever open).

        @type session: L{tlslite.Session.Session}
        @param session: A TLS session to attempt to resume.  If the
        resumption does not succeed, a full handshake will be
        performed.

        @type settings: L{tlslite.HandshakeSettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.

        @type checker: L{tlslite.Checker.Checker}
        @param checker: A Checker instance.  This instance will be
        invoked to examine the other party's authentication
        credentials, if the handshake completes succesfully.
        
        @type serverName: string
        @param serverName: The ServerNameIndication TLS Extension.

        @type async: bool
        @param async: If False, this function will block until the
        handshake is completed.  If True, this function will return a
        generator.  Successive invocations of the generator will
        return 0 if it is waiting to read from the socket, 1 if it is
        waiting to write to the socket, or will raise StopIteration if
        the handshake operation is completed.

        @rtype: None or an iterable
        @return: If 'async' is True, a generator object will be
        returned.

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        @raise tlslite.errors.TLSAuthenticationError: If the checker
        doesn't like the other party's authentication credentials.
        """
        handshaker = self._handshakeClientAsync(anonParams=(True),
                                                session=session,
                                                settings=settings,
                                                checker=checker,
                                                serverName=serverName)
        if async:
            return handshaker
        for result in handshaker:
            pass

    def handshakeClientSRP(self, username, password, session=None,
                           settings=None, checker=None, 
                           reqTack=True, serverName="",
                           async=False):
        """Perform an SRP handshake in the role of client.

        This function performs a TLS/SRP handshake.  SRP mutually
        authenticates both parties to each other using only a
        username and password.  This function may also perform a
        combined SRP and server-certificate handshake, if the server
        chooses to authenticate itself with a certificate chain in
        addition to doing SRP.

        If the function completes without raising an exception, the
        TLS connection will be open and available for data transfer.

        If an exception is raised, the connection will have been
        automatically closed (if it was ever open).

        @type username: str
        @param username: The SRP username.

        @type password: str
        @param password: The SRP password.

        @type session: L{tlslite.session.Session}
        @param session: A TLS session to attempt to resume.  This
        session must be an SRP session performed with the same username
        and password as were passed in.  If the resumption does not
        succeed, a full SRP handshake will be performed.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.

        @type checker: L{tlslite.checker.Checker}
        @param checker: A Checker instance.  This instance will be
        invoked to examine the other party's authentication
        credentials, if the handshake completes succesfully.

        @type reqTack: bool
        @param reqTack: Whether or not to send a "tack" TLS Extension, 
        requesting the server return a TackExtension if it has one.

        @type serverName: string
        @param serverName: The ServerNameIndication TLS Extension.

        @type async: bool
        @param async: If False, this function will block until the
        handshake is completed.  If True, this function will return a
        generator.  Successive invocations of the generator will
        return 0 if it is waiting to read from the socket, 1 if it is
        waiting to write to the socket, or will raise StopIteration if
        the handshake operation is completed.

        @rtype: None or an iterable
        @return: If 'async' is True, a generator object will be
        returned.

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        @raise tlslite.errors.TLSAuthenticationError: If the checker
        doesn't like the other party's authentication credentials.
        """
        handshaker = self._handshakeClientAsync(srpParams=(username, password),
                        session=session, settings=settings, checker=checker,
                        reqTack=reqTack, serverName=serverName)
        # The handshaker is a Python Generator which executes the handshake.
        # It allows the handshake to be run in a "piecewise", asynchronous
        # fashion, returning 1 when it is waiting to able to write, 0 when
        # it is waiting to read.
        #
        # If 'async' is True, the generator is returned to the caller, 
        # otherwise it is executed to completion here.  
        if async:
            return handshaker
        for result in handshaker:
            pass

    def handshakeClientCert(self, certChain=None, privateKey=None,
                            session=None, settings=None, checker=None,
                            nextProtos=None, reqTack=True, serverName="",
                            async=False):
        """Perform a certificate-based handshake in the role of client.

        This function performs an SSL or TLS handshake.  The server
        will authenticate itself using an X.509 certificate
        chain.  If the handshake succeeds, the server's certificate
        chain will be stored in the session's serverCertChain attribute.
        Unless a checker object is passed in, this function does no
        validation or checking of the server's certificate chain.

        If the server requests client authentication, the
        client will send the passed-in certificate chain, and use the
        passed-in private key to authenticate itself.  If no
        certificate chain and private key were passed in, the client
        will attempt to proceed without client authentication.  The
        server may or may not allow this.

        If the function completes without raising an exception, the
        TLS connection will be open and available for data transfer.

        If an exception is raised, the connection will have been
        automatically closed (if it was ever open).

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: The certificate chain to be used if the
        server requests client authentication.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: The private key to be used if the server
        requests client authentication.

        @type session: L{tlslite.session.Session}
        @param session: A TLS session to attempt to resume.  If the
        resumption does not succeed, a full handshake will be
        performed.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites, certificate types, and SSL/TLS versions
        offered by the client.

        @type checker: L{tlslite.checker.Checker}
        @param checker: A Checker instance.  This instance will be
        invoked to examine the other party's authentication
        credentials, if the handshake completes succesfully.
        
        @type nextProtos: list of strings.
        @param nextProtos: A list of upper layer protocols ordered by
        preference, to use in the Next-Protocol Negotiation Extension.
        
        @type reqTack: bool
        @param reqTack: Whether or not to send a "tack" TLS Extension, 
        requesting the server return a TackExtension if it has one.        

        @type serverName: string
        @param serverName: The ServerNameIndication TLS Extension.

        @type async: bool
        @param async: If False, this function will block until the
        handshake is completed.  If True, this function will return a
        generator.  Successive invocations of the generator will
        return 0 if it is waiting to read from the socket, 1 if it is
        waiting to write to the socket, or will raise StopIteration if
        the handshake operation is completed.

        @rtype: None or an iterable
        @return: If 'async' is True, a generator object will be
        returned.

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        @raise tlslite.errors.TLSAuthenticationError: If the checker
        doesn't like the other party's authentication credentials.
        """
        handshaker = self._handshakeClientAsync(certParams=(certChain,
                        privateKey), session=session, settings=settings,
                        checker=checker, serverName=serverName, 
                        nextProtos=nextProtos, reqTack=reqTack)
        # The handshaker is a Python Generator which executes the handshake.
        # It allows the handshake to be run in a "piecewise", asynchronous
        # fashion, returning 1 when it is waiting to able to write, 0 when
        # it is waiting to read.
        #
        # If 'async' is True, the generator is returned to the caller, 
        # otherwise it is executed to completion here.                        
        if async:
            return handshaker
        for result in handshaker:
            pass


    def _handshakeClientAsync(self, srpParams=(), certParams=(), anonParams=(),
                             session=None, settings=None, checker=None,
                             nextProtos=None, serverName="", reqTack=True):

        handshaker = self._handshakeClientAsyncHelper(srpParams=srpParams,
                certParams=certParams,
                anonParams=anonParams,
                session=session,
                settings=settings,
                serverName=serverName,
                nextProtos=nextProtos,
                reqTack=reqTack)
        for result in self._handshakeWrapperAsync(handshaker, checker):
            yield result


    def _handshakeClientAsyncHelper(self, srpParams, certParams, anonParams,
                               session, settings, serverName, nextProtos, reqTack):
        
        self._handshakeStart(client=True)

        #Unpack parameters
        srpUsername = None      # srpParams[0]
        password = None         # srpParams[1]
        clientCertChain = None  # certParams[0]
        privateKey = None       # certParams[1]

        # Allow only one of (srpParams, certParams, anonParams)
        if srpParams:
            assert(not certParams)
            assert(not anonParams)
            srpUsername, password = srpParams
        if certParams:
            assert(not srpParams)
            assert(not anonParams)            
            clientCertChain, privateKey = certParams
        if anonParams:
            assert(not srpParams)         
            assert(not certParams)

        #Validate parameters
        if srpUsername and not password:
            raise ValueError("Caller passed a username but no password")
        if password and not srpUsername:
            raise ValueError("Caller passed a password but no username")
        if clientCertChain and not privateKey:
            raise ValueError("Caller passed a certChain but no privateKey")
        if privateKey and not clientCertChain:
            raise ValueError("Caller passed a privateKey but no certChain")
        if reqTack:
            if not tackpyLoaded:
                reqTack = False
            if not settings or not settings.useExperimentalTackExtension:
                reqTack = False
        if nextProtos is not None:
            if len(nextProtos) == 0:
                raise ValueError("Caller passed no nextProtos")
        
        # Validates the settings and filters out any unsupported ciphers
        # or crypto libraries that were requested        
        if not settings:
            settings = HandshakeSettings()
        settings = settings._filter()

        if clientCertChain:
            if not isinstance(clientCertChain, X509CertChain):
                raise ValueError("Unrecognized certificate type")
            if "x509" not in settings.certificateTypes:
                raise ValueError("Client certificate doesn't match "\
                                 "Handshake Settings")
                                  
        if session:
            # session.valid() ensures session is resumable and has 
            # non-empty sessionID
            if not session.valid():
                session = None #ignore non-resumable sessions...
            elif session.resumable: 
                if session.srpUsername != srpUsername:
                    raise ValueError("Session username doesn't match")
                if session.serverName != serverName:
                    raise ValueError("Session servername doesn't match")

        #Add Faults to parameters
        if srpUsername and self.fault == Fault.badUsername:
            srpUsername += "GARBAGE"
        if password and self.fault == Fault.badPassword:
            password += "GARBAGE"

        #Tentatively set the version to the client's minimum version.
        #We'll use this for the ClientHello, and if an error occurs
        #parsing the Server Hello, we'll use this version for the response
        self.version = settings.maxVersion
        
        # OK Start sending messages!
        # *****************************

        # Send the ClientHello.
        for result in self._clientSendClientHello(settings, session, 
                                        srpUsername, srpParams, certParams,
                                        anonParams, serverName, nextProtos,
                                        reqTack):
            if result in (0,1): yield result
            else: break
        clientHello = result
        
        #Get the ServerHello.
        for result in self._clientGetServerHello(settings, clientHello):
            if result in (0,1): yield result
            else: break
        serverHello = result
        cipherSuite = serverHello.cipher_suite
        
        # Choose a matching Next Protocol from server list against ours
        # (string or None)
        nextProto = self._clientSelectNextProto(nextProtos, serverHello)

        #If the server elected to resume the session, it is handled here.
        for result in self._clientResume(session, serverHello, 
                        clientHello.random, 
                        settings.cipherImplementations,
                        nextProto):
            if result in (0,1): yield result
            else: break
        if result == "resumed_and_finished":
            self._handshakeDone(resumed=True)
            return

        #If the server selected an SRP ciphersuite, the client finishes
        #reading the post-ServerHello messages, then derives a
        #premasterSecret and sends a corresponding ClientKeyExchange.
        if cipherSuite in CipherSuite.srpAllSuites:
            for result in self._clientSRPKeyExchange(\
                    settings, cipherSuite, serverHello.certificate_type, 
                    srpUsername, password,
                    clientHello.random, serverHello.random, 
                    serverHello.tackExt):                
                if result in (0,1): yield result
                else: break                
            (premasterSecret, serverCertChain, tackExt) = result

        #If the server selected an anonymous ciphersuite, the client
        #finishes reading the post-ServerHello messages.
        elif cipherSuite in CipherSuite.anonSuites:
            for result in self._clientAnonKeyExchange(settings, cipherSuite,
                                    clientHello.random, serverHello.random):
                if result in (0,1): yield result
                else: break
            (premasterSecret, serverCertChain, tackExt) = result     
               
        #If the server selected a certificate-based RSA ciphersuite,
        #the client finishes reading the post-ServerHello messages. If 
        #a CertificateRequest message was sent, the client responds with
        #a Certificate message containing its certificate chain (if any),
        #and also produces a CertificateVerify message that signs the 
        #ClientKeyExchange.
        else:
            for result in self._clientRSAKeyExchange(settings, cipherSuite,
                                    clientCertChain, privateKey,
                                    serverHello.certificate_type,
                                    clientHello.random, serverHello.random,
                                    serverHello.tackExt):
                if result in (0,1): yield result
                else: break
            (premasterSecret, serverCertChain, clientCertChain, 
             tackExt) = result
                        
        #After having previously sent a ClientKeyExchange, the client now
        #initiates an exchange of Finished messages.
        for result in self._clientFinished(premasterSecret,
                            clientHello.random, 
                            serverHello.random,
                            cipherSuite, settings.cipherImplementations,
                            nextProto):
                if result in (0,1): yield result
                else: break
        masterSecret = result
        
        # Create the session object which is used for resumptions
        self.session = Session()
        self.session.create(masterSecret, serverHello.session_id, cipherSuite,
            srpUsername, clientCertChain, serverCertChain,
            tackExt, serverHello.tackExt!=None, serverName)
        self._handshakeDone(resumed=False)


    def _clientSendClientHello(self, settings, session, srpUsername,
                                srpParams, certParams, anonParams, 
                                serverName, nextProtos, reqTack):
        #Initialize acceptable ciphersuites
        cipherSuites = [CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV]
        if srpParams:
            cipherSuites += CipherSuite.getSrpAllSuites(settings)
        elif certParams:
            cipherSuites += CipherSuite.getCertSuites(settings)
        elif anonParams:
            cipherSuites += CipherSuite.getAnonSuites(settings)
        else:
            assert(False)

        #Initialize acceptable certificate types
        certificateTypes = settings._getCertificateTypes()
            
        #Either send ClientHello (with a resumable session)...
        if session and session.sessionID:
            #If it's resumable, then its
            #ciphersuite must be one of the acceptable ciphersuites
            if session.cipherSuite not in cipherSuites:
                raise ValueError("Session's cipher suite not consistent "\
                                 "with parameters")
            else:
                clientHello = ClientHello()
                clientHello.create(settings.maxVersion, getRandomBytes(32),
                                   session.sessionID, cipherSuites,
                                   certificateTypes, 
                                   session.srpUsername,
                                   reqTack, nextProtos is not None,
                                   session.serverName)

        #Or send ClientHello (without)
        else:
            clientHello = ClientHello()
            clientHello.create(settings.maxVersion, getRandomBytes(32),
                               bytearray(0), cipherSuites,
                               certificateTypes, 
                               srpUsername,
                               reqTack, nextProtos is not None, 
                               serverName)
        for result in self._sendMsg(clientHello):
            yield result
        yield clientHello


    def _clientGetServerHello(self, settings, clientHello):
        for result in self._getMsg(ContentType.handshake,
                                  HandshakeType.server_hello):
            if result in (0,1): yield result
            else: break
        serverHello = result

        #Get the server version.  Do this before anything else, so any
        #error alerts will use the server's version
        self.version = serverHello.server_version

        #Future responses from server must use this version
        self._versionCheck = True

        #Check ServerHello
        if serverHello.server_version < settings.minVersion:
            for result in self._sendError(\
                AlertDescription.protocol_version,
                "Too old version: %s" % str(serverHello.server_version)):
                yield result
        if serverHello.server_version > settings.maxVersion:
            for result in self._sendError(\
                AlertDescription.protocol_version,
                "Too new version: %s" % str(serverHello.server_version)):
                yield result
        if serverHello.cipher_suite not in clientHello.cipher_suites:
            for result in self._sendError(\
                AlertDescription.illegal_parameter,
                "Server responded with incorrect ciphersuite"):
                yield result
        if serverHello.certificate_type not in clientHello.certificate_types:
            for result in self._sendError(\
                AlertDescription.illegal_parameter,
                "Server responded with incorrect certificate type"):
                yield result
        if serverHello.compression_method != 0:
            for result in self._sendError(\
                AlertDescription.illegal_parameter,
                "Server responded with incorrect compression method"):
                yield result
        if serverHello.tackExt:            
            if not clientHello.tack:
                for result in self._sendError(\
                    AlertDescription.illegal_parameter,
                    "Server responded with unrequested Tack Extension"):
                    yield result
        if serverHello.next_protos and not clientHello.supports_npn:
            for result in self._sendError(\
                AlertDescription.illegal_parameter,
                "Server responded with unrequested NPN Extension"):
                yield result
            if not serverHello.tackExt.verifySignatures():
                for result in self._sendError(\
                    AlertDescription.decrypt_error,
                    "TackExtension contains an invalid signature"):
                    yield result
        yield serverHello

    def _clientSelectNextProto(self, nextProtos, serverHello):
        # nextProtos is None or non-empty list of strings
        # serverHello.next_protos is None or possibly-empty list of strings
        #
        # !!! We assume the client may have specified nextProtos as a list of
        # strings so we convert them to bytearrays (it's awkward to require
        # the user to specify a list of bytearrays or "bytes", and in 
        # Python 2.6 bytes() is just an alias for str() anyways...
        if nextProtos is not None and serverHello.next_protos is not None:
            for p in nextProtos:
                if bytearray(p) in serverHello.next_protos:
                    return bytearray(p)
            else:
                # If the client doesn't support any of server's protocols,
                # or the server doesn't advertise any (next_protos == [])
                # the client SHOULD select the first protocol it supports.
                return bytearray(nextProtos[0])
        return None
 
    def _clientResume(self, session, serverHello, clientRandom, 
                      cipherImplementations, nextProto):
        #If the server agrees to resume
        if session and session.sessionID and \
            serverHello.session_id == session.sessionID:

            if serverHello.cipher_suite != session.cipherSuite:
                for result in self._sendError(\
                    AlertDescription.illegal_parameter,\
                    "Server's ciphersuite doesn't match session"):
                    yield result

            #Calculate pending connection states
            self._calcPendingStates(session.cipherSuite, 
                                    session.masterSecret, 
                                    clientRandom, serverHello.random, 
                                    cipherImplementations)                                   

            #Exchange ChangeCipherSpec and Finished messages
            for result in self._getFinished(session.masterSecret):
                yield result
            for result in self._sendFinished(session.masterSecret, nextProto):
                yield result

            #Set the session for this connection
            self.session = session
            yield "resumed_and_finished"        
            
    def _clientSRPKeyExchange(self, settings, cipherSuite, certificateType, 
            srpUsername, password,
            clientRandom, serverRandom, tackExt):

        #If the server chose an SRP+RSA suite...
        if cipherSuite in CipherSuite.srpCertSuites:
            #Get Certificate, ServerKeyExchange, ServerHelloDone
            for result in self._getMsg(ContentType.handshake,
                    HandshakeType.certificate, certificateType):
                if result in (0,1): yield result
                else: break
            serverCertificate = result
        else:
            serverCertificate = None

        for result in self._getMsg(ContentType.handshake,
                HandshakeType.server_key_exchange, cipherSuite):
            if result in (0,1): yield result
            else: break
        serverKeyExchange = result

        for result in self._getMsg(ContentType.handshake,
                HandshakeType.server_hello_done):
            if result in (0,1): yield result
            else: break
        serverHelloDone = result
            
        #Calculate SRP premaster secret
        #Get and check the server's group parameters and B value
        N = serverKeyExchange.srp_N
        g = serverKeyExchange.srp_g
        s = serverKeyExchange.srp_s
        B = serverKeyExchange.srp_B

        if (g,N) not in goodGroupParameters:
            for result in self._sendError(\
                    AlertDescription.insufficient_security,
                    "Unknown group parameters"):
                yield result
        if numBits(N) < settings.minKeySize:
            for result in self._sendError(\
                    AlertDescription.insufficient_security,
                    "N value is too small: %d" % numBits(N)):
                yield result
        if numBits(N) > settings.maxKeySize:
            for result in self._sendError(\
                    AlertDescription.insufficient_security,
                    "N value is too large: %d" % numBits(N)):
                yield result
        if B % N == 0:
            for result in self._sendError(\
                    AlertDescription.illegal_parameter,
                    "Suspicious B value"):
                yield result

        #Check the server's signature, if server chose an
        #SRP+RSA suite
        serverCertChain = None
        if cipherSuite in CipherSuite.srpCertSuites:
            #Hash ServerKeyExchange/ServerSRPParams
            hashBytes = serverKeyExchange.hash(clientRandom, serverRandom)

            #Extract signature bytes from ServerKeyExchange
            sigBytes = serverKeyExchange.signature
            if len(sigBytes) == 0:
                for result in self._sendError(\
                        AlertDescription.illegal_parameter,
                        "Server sent an SRP ServerKeyExchange "\
                        "message without a signature"):
                    yield result

            # Get server's public key from the Certificate message
            # Also validate the chain against the ServerHello's TACKext (if any)
            # If none, and a TACK cert is present, return its TACKext  
            for result in self._clientGetKeyFromChain(serverCertificate,
                                               settings, tackExt):
                if result in (0,1): yield result
                else: break
            publicKey, serverCertChain, tackExt = result

            #Verify signature
            if not publicKey.verify(sigBytes, hashBytes):
                for result in self._sendError(\
                        AlertDescription.decrypt_error,
                        "Signature failed to verify"):
                    yield result

        #Calculate client's ephemeral DH values (a, A)
        a = bytesToNumber(getRandomBytes(32))
        A = powMod(g, a, N)

        #Calculate client's static DH values (x, v)
        x = makeX(s, bytearray(srpUsername, "utf-8"),
                    bytearray(password, "utf-8"))
        v = powMod(g, x, N)

        #Calculate u
        u = makeU(N, A, B)

        #Calculate premaster secret
        k = makeK(N, g)
        S = powMod((B - (k*v)) % N, a+(u*x), N)

        if self.fault == Fault.badA:
            A = N
            S = 0
            
        premasterSecret = numberToByteArray(S)

        #Send ClientKeyExchange
        for result in self._sendMsg(\
                ClientKeyExchange(cipherSuite).createSRP(A)):
            yield result
        yield (premasterSecret, serverCertChain, tackExt)
                   

    def _clientRSAKeyExchange(self, settings, cipherSuite, 
                                clientCertChain, privateKey,
                                certificateType,
                                clientRandom, serverRandom,
                                tackExt):

        #Get Certificate[, CertificateRequest], ServerHelloDone
        for result in self._getMsg(ContentType.handshake,
                HandshakeType.certificate, certificateType):
            if result in (0,1): yield result
            else: break
        serverCertificate = result

        # Get CertificateRequest or ServerHelloDone
        for result in self._getMsg(ContentType.handshake,
                (HandshakeType.server_hello_done,
                HandshakeType.certificate_request)):
            if result in (0,1): yield result
            else: break
        msg = result
        certificateRequest = None
        if isinstance(msg, CertificateRequest):
            certificateRequest = msg
            # We got CertificateRequest, so this must be ServerHelloDone
            for result in self._getMsg(ContentType.handshake,
                    HandshakeType.server_hello_done):
                if result in (0,1): yield result
                else: break
            serverHelloDone = result
        elif isinstance(msg, ServerHelloDone):
            serverHelloDone = msg

        # Get server's public key from the Certificate message
        # Also validate the chain against the ServerHello's TACKext (if any)
        # If none, and a TACK cert is present, return its TACKext  
        for result in self._clientGetKeyFromChain(serverCertificate,
                                           settings, tackExt):
            if result in (0,1): yield result
            else: break
        publicKey, serverCertChain, tackExt = result

        #Calculate premaster secret
        premasterSecret = getRandomBytes(48)
        premasterSecret[0] = settings.maxVersion[0]
        premasterSecret[1] = settings.maxVersion[1]

        if self.fault == Fault.badPremasterPadding:
            premasterSecret[0] = 5
        if self.fault == Fault.shortPremasterSecret:
            premasterSecret = premasterSecret[:-1]

        #Encrypt premaster secret to server's public key
        encryptedPreMasterSecret = publicKey.encrypt(premasterSecret)

        #If client authentication was requested, send Certificate
        #message, either with certificates or empty
        if certificateRequest:
            clientCertificate = Certificate(certificateType)

            if clientCertChain:
                #Check to make sure we have the same type of
                #certificates the server requested
                wrongType = False
                if certificateType == CertificateType.x509:
                    if not isinstance(clientCertChain, X509CertChain):
                        wrongType = True
                if wrongType:
                    for result in self._sendError(\
                            AlertDescription.handshake_failure,
                            "Client certificate is of wrong type"):
                        yield result

                clientCertificate.create(clientCertChain)
            for result in self._sendMsg(clientCertificate):
                yield result
        else:
            #The server didn't request client auth, so we
            #zeroize these so the clientCertChain won't be
            #stored in the session.
            privateKey = None
            clientCertChain = None

        #Send ClientKeyExchange
        clientKeyExchange = ClientKeyExchange(cipherSuite,
                                              self.version)
        clientKeyExchange.createRSA(encryptedPreMasterSecret)
        for result in self._sendMsg(clientKeyExchange):
            yield result

        #If client authentication was requested and we have a
        #private key, send CertificateVerify
        if certificateRequest and privateKey:
            if self.version == (3,0):
                masterSecret = calcMasterSecret(self.version,
                                         premasterSecret,
                                         clientRandom,
                                         serverRandom)
                verifyBytes = self._calcSSLHandshakeHash(masterSecret, b"")
            elif self.version in ((3,1), (3,2)):
                verifyBytes = self._handshake_md5.digest() + \
                                self._handshake_sha.digest()
            if self.fault == Fault.badVerifyMessage:
                verifyBytes[0] = ((verifyBytes[0]+1) % 256)
            signedBytes = privateKey.sign(verifyBytes)
            certificateVerify = CertificateVerify()
            certificateVerify.create(signedBytes)
            for result in self._sendMsg(certificateVerify):
                yield result
        yield (premasterSecret, serverCertChain, clientCertChain, tackExt)

    def _clientAnonKeyExchange(self, settings, cipherSuite, clientRandom, 
                               serverRandom):
        for result in self._getMsg(ContentType.handshake,
                HandshakeType.server_key_exchange, cipherSuite):
            if result in (0,1): yield result
            else: break
        serverKeyExchange = result

        for result in self._getMsg(ContentType.handshake,
                HandshakeType.server_hello_done):
            if result in (0,1): yield result
            else: break
        serverHelloDone = result
            
        #calculate Yc
        dh_p = serverKeyExchange.dh_p
        dh_g = serverKeyExchange.dh_g
        dh_Xc = bytesToNumber(getRandomBytes(32))
        dh_Ys = serverKeyExchange.dh_Ys
        dh_Yc = powMod(dh_g, dh_Xc, dh_p)
        
        #Send ClientKeyExchange
        for result in self._sendMsg(\
                ClientKeyExchange(cipherSuite, self.version).createDH(dh_Yc)):
            yield result
            
        #Calculate premaster secret
        S = powMod(dh_Ys, dh_Xc, dh_p)
        premasterSecret = numberToByteArray(S)
                     
        yield (premasterSecret, None, None)
        
    def _clientFinished(self, premasterSecret, clientRandom, serverRandom,
                        cipherSuite, cipherImplementations, nextProto):

        masterSecret = calcMasterSecret(self.version, premasterSecret,
                            clientRandom, serverRandom)
        self._calcPendingStates(cipherSuite, masterSecret, 
                                clientRandom, serverRandom, 
                                cipherImplementations)

        #Exchange ChangeCipherSpec and Finished messages
        for result in self._sendFinished(masterSecret, nextProto):
            yield result
        for result in self._getFinished(masterSecret, nextProto=nextProto):
            yield result
        yield masterSecret

    def _clientGetKeyFromChain(self, certificate, settings, tackExt=None):
        #Get and check cert chain from the Certificate message
        certChain = certificate.certChain
        if not certChain or certChain.getNumCerts() == 0:
            for result in self._sendError(AlertDescription.illegal_parameter,
                    "Other party sent a Certificate message without "\
                    "certificates"):
                yield result

        #Get and check public key from the cert chain
        publicKey = certChain.getEndEntityPublicKey()
        if len(publicKey) < settings.minKeySize:
            for result in self._sendError(AlertDescription.handshake_failure,
                    "Other party's public key too small: %d" % len(publicKey)):
                yield result
        if len(publicKey) > settings.maxKeySize:
            for result in self._sendError(AlertDescription.handshake_failure,
                    "Other party's public key too large: %d" % len(publicKey)):
                yield result
        
        # If there's no TLS Extension, look for a TACK cert
        if tackpyLoaded:
            if not tackExt:
                tackExt = certChain.getTackExt()
         
            # If there's a TACK (whether via TLS or TACK Cert), check that it
            # matches the cert chain   
            if tackExt and tackExt.tacks:
                for tack in tackExt.tacks: 
                    if not certChain.checkTack(tack):
                        for result in self._sendError(  
                                AlertDescription.illegal_parameter,
                                "Other party's TACK doesn't match their public key"):
                                yield result

        yield publicKey, certChain, tackExt


    #*********************************************************
    # Server Handshake Functions
    #*********************************************************


    def handshakeServer(self, verifierDB=None,
                        certChain=None, privateKey=None, reqCert=False,
                        sessionCache=None, settings=None, checker=None,
                        reqCAs = None, 
                        tacks=None, activationFlags=0,
                        nextProtos=None, anon=False):
        """Perform a handshake in the role of server.

        This function performs an SSL or TLS handshake.  Depending on
        the arguments and the behavior of the client, this function can
        perform an SRP, or certificate-based handshake.  It
        can also perform a combined SRP and server-certificate
        handshake.

        Like any handshake function, this can be called on a closed
        TLS connection, or on a TLS connection that is already open.
        If called on an open connection it performs a re-handshake.
        This function does not send a Hello Request message before
        performing the handshake, so if re-handshaking is required,
        the server must signal the client to begin the re-handshake
        through some other means.

        If the function completes without raising an exception, the
        TLS connection will be open and available for data transfer.

        If an exception is raised, the connection will have been
        automatically closed (if it was ever open).

        @type verifierDB: L{tlslite.verifierdb.VerifierDB}
        @param verifierDB: A database of SRP password verifiers
        associated with usernames.  If the client performs an SRP
        handshake, the session's srpUsername attribute will be set.

        @type certChain: L{tlslite.x509certchain.X509CertChain}
        @param certChain: The certificate chain to be used if the
        client requests server certificate authentication.

        @type privateKey: L{tlslite.utils.rsakey.RSAKey}
        @param privateKey: The private key to be used if the client
        requests server certificate authentication.

        @type reqCert: bool
        @param reqCert: Whether to request client certificate
        authentication.  This only applies if the client chooses server
        certificate authentication; if the client chooses SRP
        authentication, this will be ignored.  If the client
        performs a client certificate authentication, the sessions's
        clientCertChain attribute will be set.

        @type sessionCache: L{tlslite.sessioncache.SessionCache}
        @param sessionCache: An in-memory cache of resumable sessions.
        The client can resume sessions from this cache.  Alternatively,
        if the client performs a full handshake, a new session will be
        added to the cache.

        @type settings: L{tlslite.handshakesettings.HandshakeSettings}
        @param settings: Various settings which can be used to control
        the ciphersuites and SSL/TLS version chosen by the server.

        @type checker: L{tlslite.checker.Checker}
        @param checker: A Checker instance.  This instance will be
        invoked to examine the other party's authentication
        credentials, if the handshake completes succesfully.
        
        @type reqCAs: list of L{bytearray} of unsigned bytes
        @param reqCAs: A collection of DER-encoded DistinguishedNames that
        will be sent along with a certificate request. This does not affect
        verification.        

        @type nextProtos: list of strings.
        @param nextProtos: A list of upper layer protocols to expose to the
        clients through the Next-Protocol Negotiation Extension, 
        if they support it.

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        @raise tlslite.errors.TLSAuthenticationError: If the checker
        doesn't like the other party's authentication credentials.
        """
        for result in self.handshakeServerAsync(verifierDB,
                certChain, privateKey, reqCert, sessionCache, settings,
                checker, reqCAs, 
                tacks=tacks, activationFlags=activationFlags, 
                nextProtos=nextProtos, anon=anon):
            pass


    def handshakeServerAsync(self, verifierDB=None,
                             certChain=None, privateKey=None, reqCert=False,
                             sessionCache=None, settings=None, checker=None,
                             reqCAs=None, 
                             tacks=None, activationFlags=0,
                             nextProtos=None, anon=False
                             ):
        """Start a server handshake operation on the TLS connection.

        This function returns a generator which behaves similarly to
        handshakeServer().  Successive invocations of the generator
        will return 0 if it is waiting to read from the socket, 1 if it is
        waiting to write to the socket, or it will raise StopIteration
        if the handshake operation is complete.

        @rtype: iterable
        @return: A generator; see above for details.
        """
        handshaker = self._handshakeServerAsyncHelper(\
            verifierDB=verifierDB, certChain=certChain,
            privateKey=privateKey, reqCert=reqCert,
            sessionCache=sessionCache, settings=settings, 
            reqCAs=reqCAs, 
            tacks=tacks, activationFlags=activationFlags, 
            nextProtos=nextProtos, anon=anon)
        for result in self._handshakeWrapperAsync(handshaker, checker):
            yield result


    def _handshakeServerAsyncHelper(self, verifierDB,
                             certChain, privateKey, reqCert, sessionCache,
                             settings, reqCAs, 
                             tacks, activationFlags, 
                             nextProtos, anon):

        self._handshakeStart(client=False)

        if (not verifierDB) and (not certChain) and not anon:
            raise ValueError("Caller passed no authentication credentials")
        if certChain and not privateKey:
            raise ValueError("Caller passed a certChain but no privateKey")
        if privateKey and not certChain:
            raise ValueError("Caller passed a privateKey but no certChain")
        if reqCAs and not reqCert:
            raise ValueError("Caller passed reqCAs but not reqCert")            
        if certChain and not isinstance(certChain, X509CertChain):
            raise ValueError("Unrecognized certificate type")
        if activationFlags and not tacks:
            raise ValueError("Nonzero activationFlags requires tacks")
        if tacks:
            if not tackpyLoaded:
                raise ValueError("tackpy is not loaded")
            if not settings or not settings.useExperimentalTackExtension:
                raise ValueError("useExperimentalTackExtension not enabled")

        if not settings:
            settings = HandshakeSettings()
        settings = settings._filter()
        
        # OK Start exchanging messages
        # ******************************
        
        # Handle ClientHello and resumption
        for result in self._serverGetClientHello(settings, certChain,\
                                            verifierDB, sessionCache,
                                            anon):
            if result in (0,1): yield result
            elif result == None:
                self._handshakeDone(resumed=True)                
                return # Handshake was resumed, we're done 
            else: break
        (clientHello, cipherSuite) = result
        
        #If not a resumption...

        # Create the ServerHello message
        if sessionCache:
            sessionID = getRandomBytes(32)
        else:
            sessionID = bytearray(0)
        
        if not clientHello.supports_npn:
            nextProtos = None

        # If not doing a certificate-based suite, discard the TACK
        if not cipherSuite in CipherSuite.certAllSuites:
            tacks = None

        # Prepare a TACK Extension if requested
        if clientHello.tack:
            tackExt = TackExtension.create(tacks, activationFlags)
        else:
            tackExt = None
        serverHello = ServerHello()
        serverHello.create(self.version, getRandomBytes(32), sessionID, \
                            cipherSuite, CertificateType.x509, tackExt,
                            nextProtos)

        # Perform the SRP key exchange
        clientCertChain = None
        if cipherSuite in CipherSuite.srpAllSuites:
            for result in self._serverSRPKeyExchange(clientHello, serverHello, 
                                    verifierDB, cipherSuite, 
                                    privateKey, certChain):
                if result in (0,1): yield result
                else: break
            premasterSecret = result

        # Perform the RSA key exchange
        elif cipherSuite in CipherSuite.certSuites:
            for result in self._serverCertKeyExchange(clientHello, serverHello, 
                                        certChain, privateKey,
                                        reqCert, reqCAs, cipherSuite,
                                        settings):
                if result in (0,1): yield result
                else: break
            (premasterSecret, clientCertChain) = result

        # Perform anonymous Diffie Hellman key exchange
        elif cipherSuite in CipherSuite.anonSuites:
            for result in self._serverAnonKeyExchange(clientHello, serverHello, 
                                        cipherSuite, settings):
                if result in (0,1): yield result
                else: break
            premasterSecret = result
        
        else:
            assert(False)
                        
        # Exchange Finished messages      
        for result in self._serverFinished(premasterSecret, 
                                clientHello.random, serverHello.random,
                                cipherSuite, settings.cipherImplementations,
                                nextProtos):
                if result in (0,1): yield result
                else: break
        masterSecret = result

        #Create the session object
        self.session = Session()
        if cipherSuite in CipherSuite.certAllSuites:        
            serverCertChain = certChain
        else:
            serverCertChain = None
        srpUsername = None
        serverName = None
        if clientHello.srp_username:
            srpUsername = clientHello.srp_username.decode("utf-8")
        if clientHello.server_name:
            serverName = clientHello.server_name.decode("utf-8")
        self.session.create(masterSecret, serverHello.session_id, cipherSuite,
            srpUsername, clientCertChain, serverCertChain,
            tackExt, serverHello.tackExt!=None, serverName)
            
        #Add the session object to the session cache
        if sessionCache and sessionID:
            sessionCache[sessionID] = self.session

        self._handshakeDone(resumed=False)


    def _serverGetClientHello(self, settings, certChain, verifierDB,
                                sessionCache, anon):
        #Initialize acceptable cipher suites
        cipherSuites = []
        if verifierDB:
            if certChain:
                cipherSuites += \
                    CipherSuite.getSrpCertSuites(settings)
            cipherSuites += CipherSuite.getSrpSuites(settings)
        elif certChain:
            cipherSuites += CipherSuite.getCertSuites(settings)
        elif anon:
            cipherSuites += CipherSuite.getAnonSuites(settings)
        else:
            assert(False)

        #Tentatively set version to most-desirable version, so if an error
        #occurs parsing the ClientHello, this is what we'll use for the
        #error alert
        self.version = settings.maxVersion

        #Get ClientHello
        for result in self._getMsg(ContentType.handshake,
                                   HandshakeType.client_hello):
            if result in (0,1): yield result
            else: break
        clientHello = result

        #If client's version is too low, reject it
        if clientHello.client_version < settings.minVersion:
            self.version = settings.minVersion
            for result in self._sendError(\
                  AlertDescription.protocol_version,
                  "Too old version: %s" % str(clientHello.client_version)):
                yield result

        #If client's version is too high, propose my highest version
        elif clientHello.client_version > settings.maxVersion:
            self.version = settings.maxVersion

        else:
            #Set the version to the client's version
            self.version = clientHello.client_version  

        #If resumption was requested and we have a session cache...
        if clientHello.session_id and sessionCache:
            session = None

            #Check in the session cache
            if sessionCache and not session:
                try:
                    session = sessionCache[clientHello.session_id]
                    if not session.resumable:
                        raise AssertionError()
                    #Check for consistency with ClientHello
                    if session.cipherSuite not in cipherSuites:
                        for result in self._sendError(\
                                AlertDescription.handshake_failure):
                            yield result
                    if session.cipherSuite not in clientHello.cipher_suites:
                        for result in self._sendError(\
                                AlertDescription.handshake_failure):
                            yield result
                    if clientHello.srp_username:
                        if not session.srpUsername or \
                            clientHello.srp_username != bytearray(session.srpUsername, "utf-8"):
                            for result in self._sendError(\
                                    AlertDescription.handshake_failure):
                                yield result
                    if clientHello.server_name:
                        if not session.serverName or \
                            clientHello.server_name != bytearray(session.serverName, "utf-8"):
                            for result in self._sendError(\
                                    AlertDescription.handshake_failure):
                                yield result                    
                except KeyError:
                    pass

            #If a session is found..
            if session:
                #Send ServerHello
                serverHello = ServerHello()
                serverHello.create(self.version, getRandomBytes(32),
                                   session.sessionID, session.cipherSuite,
                                   CertificateType.x509, None, None)
                for result in self._sendMsg(serverHello):
                    yield result

                #From here on, the client's messages must have right version
                self._versionCheck = True

                #Calculate pending connection states
                self._calcPendingStates(session.cipherSuite, 
                                        session.masterSecret,
                                        clientHello.random, 
                                        serverHello.random,
                                        settings.cipherImplementations)

                #Exchange ChangeCipherSpec and Finished messages
                for result in self._sendFinished(session.masterSecret):
                    yield result
                for result in self._getFinished(session.masterSecret):
                    yield result

                #Set the session
                self.session = session
                    
                yield None # Handshake done!

        #Calculate the first cipher suite intersection.
        #This is the 'privileged' ciphersuite.  We'll use it if we're
        #doing a new negotiation.  In fact,
        #the only time we won't use it is if we're resuming a
        #session, in which case we use the ciphersuite from the session.
        #
        #Given the current ciphersuite ordering, this means we prefer SRP
        #over non-SRP.
        for cipherSuite in cipherSuites:
            if cipherSuite in clientHello.cipher_suites:
                break
        else:
            for result in self._sendError(\
                    AlertDescription.handshake_failure,
                    "No mutual ciphersuite"):
                yield result
        if cipherSuite in CipherSuite.srpAllSuites and \
                            not clientHello.srp_username:
            for result in self._sendError(\
                    AlertDescription.unknown_psk_identity,
                    "Client sent a hello, but without the SRP username"):
                yield result
           
        #If an RSA suite is chosen, check for certificate type intersection
        if cipherSuite in CipherSuite.certAllSuites and CertificateType.x509 \
                                not in clientHello.certificate_types:
            for result in self._sendError(\
                    AlertDescription.handshake_failure,
                    "the client doesn't support my certificate type"):
                yield result

        # If resumption was not requested, or
        # we have no session cache, or
        # the client's session_id was not found in cache:
        yield (clientHello, cipherSuite)

    def _serverSRPKeyExchange(self, clientHello, serverHello, verifierDB, 
                                cipherSuite, privateKey, serverCertChain):

        srpUsername = clientHello.srp_username.decode("utf-8")
        self.allegedSrpUsername = srpUsername
        #Get parameters from username
        try:
            entry = verifierDB[srpUsername]
        except KeyError:
            for result in self._sendError(\
                    AlertDescription.unknown_psk_identity):
                yield result
        (N, g, s, v) = entry

        #Calculate server's ephemeral DH values (b, B)
        b = bytesToNumber(getRandomBytes(32))
        k = makeK(N, g)
        B = (powMod(g, b, N) + (k*v)) % N

        #Create ServerKeyExchange, signing it if necessary
        serverKeyExchange = ServerKeyExchange(cipherSuite)
        serverKeyExchange.createSRP(N, g, s, B)
        if cipherSuite in CipherSuite.srpCertSuites:
            hashBytes = serverKeyExchange.hash(clientHello.random,
                                               serverHello.random)
            serverKeyExchange.signature = privateKey.sign(hashBytes)

        #Send ServerHello[, Certificate], ServerKeyExchange,
        #ServerHelloDone
        msgs = []
        msgs.append(serverHello)
        if cipherSuite in CipherSuite.srpCertSuites:
            certificateMsg = Certificate(CertificateType.x509)
            certificateMsg.create(serverCertChain)
            msgs.append(certificateMsg)
        msgs.append(serverKeyExchange)
        msgs.append(ServerHelloDone())
        for result in self._sendMsgs(msgs):
            yield result

        #From here on, the client's messages must have the right version
        self._versionCheck = True

        #Get and check ClientKeyExchange
        for result in self._getMsg(ContentType.handshake,
                                  HandshakeType.client_key_exchange,
                                  cipherSuite):
            if result in (0,1): yield result
            else: break
        clientKeyExchange = result
        A = clientKeyExchange.srp_A
        if A % N == 0:
            for result in self._sendError(AlertDescription.illegal_parameter,
                    "Suspicious A value"):
                yield result
            assert(False) # Just to ensure we don't fall through somehow

        #Calculate u
        u = makeU(N, A, B)

        #Calculate premaster secret
        S = powMod((A * powMod(v,u,N)) % N, b, N)
        premasterSecret = numberToByteArray(S)
        
        yield premasterSecret


    def _serverCertKeyExchange(self, clientHello, serverHello, 
                                serverCertChain, privateKey,
                                reqCert, reqCAs, cipherSuite,
                                settings):
        #Send ServerHello, Certificate[, CertificateRequest],
        #ServerHelloDone
        msgs = []

        # If we verify a client cert chain, return it
        clientCertChain = None

        msgs.append(serverHello)
        msgs.append(Certificate(CertificateType.x509).create(serverCertChain))
        if reqCert and reqCAs:
            msgs.append(CertificateRequest().create(\
                [ClientCertificateType.rsa_sign], reqCAs))
        elif reqCert:
            msgs.append(CertificateRequest())
        msgs.append(ServerHelloDone())
        for result in self._sendMsgs(msgs):
            yield result

        #From here on, the client's messages must have the right version
        self._versionCheck = True

        #Get [Certificate,] (if was requested)
        if reqCert:
            if self.version == (3,0):
                for result in self._getMsg((ContentType.handshake,
                                           ContentType.alert),
                                           HandshakeType.certificate,
                                           CertificateType.x509):
                    if result in (0,1): yield result
                    else: break
                msg = result

                if isinstance(msg, Alert):
                    #If it's not a no_certificate alert, re-raise
                    alert = msg
                    if alert.description != \
                            AlertDescription.no_certificate:
                        self._shutdown(False)
                        raise TLSRemoteAlert(alert)
                elif isinstance(msg, Certificate):
                    clientCertificate = msg
                    if clientCertificate.certChain and \
                            clientCertificate.certChain.getNumCerts()!=0:
                        clientCertChain = clientCertificate.certChain
                else:
                    raise AssertionError()
            elif self.version in ((3,1), (3,2)):
                for result in self._getMsg(ContentType.handshake,
                                          HandshakeType.certificate,
                                          CertificateType.x509):
                    if result in (0,1): yield result
                    else: break
                clientCertificate = result
                if clientCertificate.certChain and \
                        clientCertificate.certChain.getNumCerts()!=0:
                    clientCertChain = clientCertificate.certChain
            else:
                raise AssertionError()

        #Get ClientKeyExchange
        for result in self._getMsg(ContentType.handshake,
                                  HandshakeType.client_key_exchange,
                                  cipherSuite):
            if result in (0,1): yield result
            else: break
        clientKeyExchange = result

        #Decrypt ClientKeyExchange
        premasterSecret = privateKey.decrypt(\
            clientKeyExchange.encryptedPreMasterSecret)

        # On decryption failure randomize premaster secret to avoid
        # Bleichenbacher's "million message" attack
        randomPreMasterSecret = getRandomBytes(48)
        versionCheck = (premasterSecret[0], premasterSecret[1])
        if not premasterSecret:
            premasterSecret = randomPreMasterSecret
        elif len(premasterSecret)!=48:
            premasterSecret = randomPreMasterSecret
        elif versionCheck != clientHello.client_version:
            if versionCheck != self.version: #Tolerate buggy IE clients
                premasterSecret = randomPreMasterSecret

        #Get and check CertificateVerify, if relevant
        if clientCertChain:
            if self.version == (3,0):
                masterSecret = calcMasterSecret(self.version, premasterSecret,
                                         clientHello.random, serverHello.random)
                verifyBytes = self._calcSSLHandshakeHash(masterSecret, b"")
            elif self.version in ((3,1), (3,2)):
                verifyBytes = self._handshake_md5.digest() + \
                                self._handshake_sha.digest()
            for result in self._getMsg(ContentType.handshake,
                                      HandshakeType.certificate_verify):
                if result in (0,1): yield result
                else: break
            certificateVerify = result
            publicKey = clientCertChain.getEndEntityPublicKey()
            if len(publicKey) < settings.minKeySize:
                for result in self._sendError(\
                        AlertDescription.handshake_failure,
                        "Client's public key too small: %d" % len(publicKey)):
                    yield result

            if len(publicKey) > settings.maxKeySize:
                for result in self._sendError(\
                        AlertDescription.handshake_failure,
                        "Client's public key too large: %d" % len(publicKey)):
                    yield result

            if not publicKey.verify(certificateVerify.signature, verifyBytes):
                for result in self._sendError(\
                        AlertDescription.decrypt_error,
                        "Signature failed to verify"):
                    yield result
        yield (premasterSecret, clientCertChain)


    def _serverAnonKeyExchange(self, clientHello, serverHello, cipherSuite, 
                               settings):
        # Calculate DH p, g, Xs, Ys
        dh_p = getRandomSafePrime(32, False)
        dh_g = getRandomNumber(2, dh_p)        
        dh_Xs = bytesToNumber(getRandomBytes(32))        
        dh_Ys = powMod(dh_g, dh_Xs, dh_p)

        #Create ServerKeyExchange
        serverKeyExchange = ServerKeyExchange(cipherSuite)
        serverKeyExchange.createDH(dh_p, dh_g, dh_Ys)
        
        #Send ServerHello[, Certificate], ServerKeyExchange,
        #ServerHelloDone  
        msgs = []
        msgs.append(serverHello)
        msgs.append(serverKeyExchange)
        msgs.append(ServerHelloDone())
        for result in self._sendMsgs(msgs):
            yield result
        
        #From here on, the client's messages must have the right version
        self._versionCheck = True
        
        #Get and check ClientKeyExchange
        for result in self._getMsg(ContentType.handshake,
                                   HandshakeType.client_key_exchange,
                                   cipherSuite):
            if result in (0,1):
                yield result 
            else:
                break
        clientKeyExchange = result
        dh_Yc = clientKeyExchange.dh_Yc
        
        if dh_Yc % dh_p == 0:
            for result in self._sendError(AlertDescription.illegal_parameter,
                    "Suspicious dh_Yc value"):
                yield result
            assert(False) # Just to ensure we don't fall through somehow            

        #Calculate premaster secre
        S = powMod(dh_Yc,dh_Xs,dh_p)
        premasterSecret = numberToByteArray(S)
        
        yield premasterSecret


    def _serverFinished(self,  premasterSecret, clientRandom, serverRandom,
                        cipherSuite, cipherImplementations, nextProtos):
        masterSecret = calcMasterSecret(self.version, premasterSecret,
                                      clientRandom, serverRandom)
        
        #Calculate pending connection states
        self._calcPendingStates(cipherSuite, masterSecret, 
                                clientRandom, serverRandom,
                                cipherImplementations)

        #Exchange ChangeCipherSpec and Finished messages
        for result in self._getFinished(masterSecret, 
                        expect_next_protocol=nextProtos is not None):
            yield result

        for result in self._sendFinished(masterSecret):
            yield result
        
        yield masterSecret        


    #*********************************************************
    # Shared Handshake Functions
    #*********************************************************


    def _sendFinished(self, masterSecret, nextProto=None):
        #Send ChangeCipherSpec
        for result in self._sendMsg(ChangeCipherSpec()):
            yield result

        #Switch to pending write state
        self._changeWriteState()

        if nextProto is not None:
            nextProtoMsg = NextProtocol().create(nextProto)
            for result in self._sendMsg(nextProtoMsg):
                yield result

        #Calculate verification data
        verifyData = self._calcFinished(masterSecret, True)
        if self.fault == Fault.badFinished:
            verifyData[0] = (verifyData[0]+1)%256

        #Send Finished message under new state
        finished = Finished(self.version).create(verifyData)
        for result in self._sendMsg(finished):
            yield result

    def _getFinished(self, masterSecret, expect_next_protocol=False, nextProto=None):
        #Get and check ChangeCipherSpec
        for result in self._getMsg(ContentType.change_cipher_spec):
            if result in (0,1):
                yield result
        changeCipherSpec = result

        if changeCipherSpec.type != 1:
            for result in self._sendError(AlertDescription.illegal_parameter,
                                         "ChangeCipherSpec type incorrect"):
                yield result

        #Switch to pending read state
        self._changeReadState()

        #Server Finish - Are we waiting for a next protocol echo? 
        if expect_next_protocol:
            for result in self._getMsg(ContentType.handshake, HandshakeType.next_protocol):
                if result in (0,1):
                    yield result
            if result is None:
                for result in self._sendError(AlertDescription.unexpected_message,
                                             "Didn't get NextProtocol message"):
                    yield result

            self.next_proto = result.next_proto
        else:
            self.next_proto = None

        #Client Finish - Only set the next_protocol selected in the connection
        if nextProto:
            self.next_proto = nextProto

        #Calculate verification data
        verifyData = self._calcFinished(masterSecret, False)

        #Get and check Finished message under new state
        for result in self._getMsg(ContentType.handshake,
                                  HandshakeType.finished):
            if result in (0,1):
                yield result
        finished = result
        if finished.verify_data != verifyData:
            for result in self._sendError(AlertDescription.decrypt_error,
                                         "Finished message is incorrect"):
                yield result

    def _calcFinished(self, masterSecret, send=True):
        if self.version == (3,0):
            if (self._client and send) or (not self._client and not send):
                senderStr = b"\x43\x4C\x4E\x54"
            else:
                senderStr = b"\x53\x52\x56\x52"

            verifyData = self._calcSSLHandshakeHash(masterSecret, senderStr)
            return verifyData

        elif self.version in ((3,1), (3,2)):
            if (self._client and send) or (not self._client and not send):
                label = b"client finished"
            else:
                label = b"server finished"

            handshakeHashes = self._handshake_md5.digest() + \
                                self._handshake_sha.digest()
            verifyData = PRF(masterSecret, label, handshakeHashes, 12)
            return verifyData
        else:
            raise AssertionError()


    def _handshakeWrapperAsync(self, handshaker, checker):
        if not self.fault:
            try:
                for result in handshaker:
                    yield result
                if checker:
                    try:
                        checker(self)
                    except TLSAuthenticationError:
                        alert = Alert().create(AlertDescription.close_notify,
                                               AlertLevel.fatal)
                        for result in self._sendMsg(alert):
                            yield result
                        raise
            except GeneratorExit:
                raise
            except TLSAlert as alert:
                if not self.fault:
                    raise
                if alert.description not in Fault.faultAlerts[self.fault]:
                    raise TLSFaultError(str(alert))
                else:
                    pass
            except:
                self._shutdown(False)
                raise

########NEW FILE########
__FILENAME__ = tlsrecordlayer
# Authors: 
#   Trevor Perrin
#   Google (adapted by Sam Rushing) - NPN support
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""Helper class for TLSConnection."""
from __future__ import generators

from .utils.compat import *
from .utils.cryptomath import *
from .utils.cipherfactory import createAES, createRC4, createTripleDES
from .utils.codec import *
from .errors import *
from .messages import *
from .mathtls import *
from .constants import *
from .utils.cryptomath import getRandomBytes

import socket
import errno
import traceback

class _ConnectionState(object):
    def __init__(self):
        self.macContext = None
        self.encContext = None
        self.seqnum = 0

    def getSeqNumBytes(self):
        w = Writer()
        w.add(self.seqnum, 8)
        self.seqnum += 1
        return w.bytes


class TLSRecordLayer(object):
    """
    This class handles data transmission for a TLS connection.

    Its only subclass is L{tlslite.TLSConnection.TLSConnection}.  We've
    separated the code in this class from TLSConnection to make things
    more readable.


    @type sock: socket.socket
    @ivar sock: The underlying socket object.

    @type session: L{tlslite.Session.Session}
    @ivar session: The session corresponding to this connection.

    Due to TLS session resumption, multiple connections can correspond
    to the same underlying session.

    @type version: tuple
    @ivar version: The TLS version being used for this connection.

    (3,0) means SSL 3.0, and (3,1) means TLS 1.0.

    @type closed: bool
    @ivar closed: If this connection is closed.

    @type resumed: bool
    @ivar resumed: If this connection is based on a resumed session.

    @type allegedSrpUsername: str or None
    @ivar allegedSrpUsername:  This is set to the SRP username
    asserted by the client, whether the handshake succeeded or not.
    If the handshake fails, this can be inspected to determine
    if a guessing attack is in progress against a particular user
    account.

    @type closeSocket: bool
    @ivar closeSocket: If the socket should be closed when the
    connection is closed, defaults to True (writable).

    If you set this to True, TLS Lite will assume the responsibility of
    closing the socket when the TLS Connection is shutdown (either
    through an error or through the user calling close()).  The default
    is False.

    @type ignoreAbruptClose: bool
    @ivar ignoreAbruptClose: If an abrupt close of the socket should
    raise an error (writable).

    If you set this to True, TLS Lite will not raise a
    L{tlslite.errors.TLSAbruptCloseError} exception if the underlying
    socket is unexpectedly closed.  Such an unexpected closure could be
    caused by an attacker.  However, it also occurs with some incorrect
    TLS implementations.

    You should set this to True only if you're not worried about an
    attacker truncating the connection, and only if necessary to avoid
    spurious errors.  The default is False.

    @sort: __init__, read, readAsync, write, writeAsync, close, closeAsync,
    getCipherImplementation, getCipherName
    """

    def __init__(self, sock):
        self.sock = sock

        #My session object (Session instance; read-only)
        self.session = None

        #Am I a client or server?
        self._client = None

        #Buffers for processing messages
        self._handshakeBuffer = []
        self.clearReadBuffer()
        self.clearWriteBuffer()

        #Handshake digests
        self._handshake_md5 = hashlib.md5()
        self._handshake_sha = hashlib.sha1()

        #TLS Protocol Version
        self.version = (0,0) #read-only
        self._versionCheck = False #Once we choose a version, this is True

        #Current and Pending connection states
        self._writeState = _ConnectionState()
        self._readState = _ConnectionState()
        self._pendingWriteState = _ConnectionState()
        self._pendingReadState = _ConnectionState()

        #Is the connection open?
        self.closed = True #read-only
        self._refCount = 0 #Used to trigger closure

        #Is this a resumed session?
        self.resumed = False #read-only

        #What username did the client claim in his handshake?
        self.allegedSrpUsername = None

        #On a call to close(), do we close the socket? (writeable)
        self.closeSocket = True

        #If the socket is abruptly closed, do we ignore it
        #and pretend the connection was shut down properly? (writeable)
        self.ignoreAbruptClose = False

        #Fault we will induce, for testing purposes
        self.fault = None

    def clearReadBuffer(self):
        self._readBuffer = b''

    def clearWriteBuffer(self):
        self._send_writer = None


    #*********************************************************
    # Public Functions START
    #*********************************************************

    def read(self, max=None, min=1):
        """Read some data from the TLS connection.

        This function will block until at least 'min' bytes are
        available (or the connection is closed).

        If an exception is raised, the connection will have been
        automatically closed.

        @type max: int
        @param max: The maximum number of bytes to return.

        @type min: int
        @param min: The minimum number of bytes to return

        @rtype: str
        @return: A string of no more than 'max' bytes, and no fewer
        than 'min' (unless the connection has been closed, in which
        case fewer than 'min' bytes may be returned).

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        """
        for result in self.readAsync(max, min):
            pass
        return result

    def readAsync(self, max=None, min=1):
        """Start a read operation on the TLS connection.

        This function returns a generator which behaves similarly to
        read().  Successive invocations of the generator will return 0
        if it is waiting to read from the socket, 1 if it is waiting
        to write to the socket, or a string if the read operation has
        completed.

        @rtype: iterable
        @return: A generator; see above for details.
        """
        try:
            while len(self._readBuffer)<min and not self.closed:
                try:
                    for result in self._getMsg(ContentType.application_data):
                        if result in (0,1):
                            yield result
                    applicationData = result
                    self._readBuffer += applicationData.write()
                except TLSRemoteAlert as alert:
                    if alert.description != AlertDescription.close_notify:
                        raise
                except TLSAbruptCloseError:
                    if not self.ignoreAbruptClose:
                        raise
                    else:
                        self._shutdown(True)

            if max == None:
                max = len(self._readBuffer)

            returnBytes = self._readBuffer[:max]
            self._readBuffer = self._readBuffer[max:]
            yield bytes(returnBytes)
        except GeneratorExit:
            raise
        except:
            self._shutdown(False)
            raise

    def unread(self, b):
        """Add bytes to the front of the socket read buffer for future
        reading. Be careful using this in the context of select(...): if you
        unread the last data from a socket, that won't wake up selected waiters,
        and those waiters may hang forever.
        """
        self._readBuffer = b + self._readBuffer

    def write(self, s):
        """Write some data to the TLS connection.

        This function will block until all the data has been sent.

        If an exception is raised, the connection will have been
        automatically closed.

        @type s: str
        @param s: The data to transmit to the other party.

        @raise socket.error: If a socket error occurs.
        """
        for result in self.writeAsync(s):
            pass

    def writeAsync(self, s):
        """Start a write operation on the TLS connection.

        This function returns a generator which behaves similarly to
        write().  Successive invocations of the generator will return
        1 if it is waiting to write to the socket, or will raise
        StopIteration if the write operation has completed.

        @rtype: iterable
        @return: A generator; see above for details.
        """
        try:
            if self.closed:
                raise TLSClosedConnectionError("attempt to write to closed connection")

            index = 0
            blockSize = 16384
            randomizeFirstBlock = True
            while 1:
                startIndex = index * blockSize
                endIndex = startIndex + blockSize
                if startIndex >= len(s):
                    break
                if endIndex > len(s):
                    endIndex = len(s)
                block = bytearray(s[startIndex : endIndex])
                applicationData = ApplicationData().create(block)
                for result in self._sendMsg(applicationData, \
                                            randomizeFirstBlock):
                    yield result
                randomizeFirstBlock = False #only on 1st message
                index += 1
        except GeneratorExit:
            raise
        except Exception:
            self._shutdown(False)
            raise

    def close(self):
        """Close the TLS connection.

        This function will block until it has exchanged close_notify
        alerts with the other party.  After doing so, it will shut down the
        TLS connection.  Further attempts to read through this connection
        will return "".  Further attempts to write through this connection
        will raise ValueError.

        If makefile() has been called on this connection, the connection
        will be not be closed until the connection object and all file
        objects have been closed.

        Even if an exception is raised, the connection will have been
        closed.

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        """
        if not self.closed:
            for result in self._decrefAsync():
                pass

    # Python 3 callback
    _decref_socketios = close

    def closeAsync(self):
        """Start a close operation on the TLS connection.

        This function returns a generator which behaves similarly to
        close().  Successive invocations of the generator will return 0
        if it is waiting to read from the socket, 1 if it is waiting
        to write to the socket, or will raise StopIteration if the
        close operation has completed.

        @rtype: iterable
        @return: A generator; see above for details.
        """
        if not self.closed:
            for result in self._decrefAsync():
                yield result

    def _decrefAsync(self):
        self._refCount -= 1
        if self._refCount == 0 and not self.closed:
            try:
                for result in self._sendMsg(Alert().create(\
                        AlertDescription.close_notify, AlertLevel.warning)):
                    yield result
                alert = None
                # By default close the socket, since it's been observed
                # that some other libraries will not respond to the 
                # close_notify alert, thus leaving us hanging if we're
                # expecting it
                if self.closeSocket:
                    self._shutdown(True)
                else:
                    while not alert:
                        for result in self._getMsg((ContentType.alert, \
                                                  ContentType.application_data)):
                            if result in (0,1):
                                yield result
                        if result.contentType == ContentType.alert:
                            alert = result
                    if alert.description == AlertDescription.close_notify:
                        self._shutdown(True)
                    else:
                        raise TLSRemoteAlert(alert)
            except (socket.error, TLSAbruptCloseError):
                #If the other side closes the socket, that's okay
                self._shutdown(True)
            except GeneratorExit:
                raise
            except:
                self._shutdown(False)
                raise

    def getVersionName(self):
        """Get the name of this TLS version.

        @rtype: str
        @return: The name of the TLS version used with this connection.
        Either None, 'SSL 3.0', 'TLS 1.0', or 'TLS 1.1'.
        """
        if self.version == (3,0):
            return "SSL 3.0"
        elif self.version == (3,1):
            return "TLS 1.0"
        elif self.version == (3,2):
            return "TLS 1.1"
        else:
            return None
        
    def getCipherName(self):
        """Get the name of the cipher used with this connection.

        @rtype: str
        @return: The name of the cipher used with this connection.
        Either 'aes128', 'aes256', 'rc4', or '3des'.
        """
        if not self._writeState.encContext:
            return None
        return self._writeState.encContext.name

    def getCipherImplementation(self):
        """Get the name of the cipher implementation used with
        this connection.

        @rtype: str
        @return: The name of the cipher implementation used with
        this connection.  Either 'python', 'openssl', or 'pycrypto'.
        """
        if not self._writeState.encContext:
            return None
        return self._writeState.encContext.implementation



    #Emulate a socket, somewhat -
    def send(self, s):
        """Send data to the TLS connection (socket emulation).

        @raise socket.error: If a socket error occurs.
        """
        self.write(s)
        return len(s)

    def sendall(self, s):
        """Send data to the TLS connection (socket emulation).

        @raise socket.error: If a socket error occurs.
        """
        self.write(s)

    def recv(self, bufsize):
        """Get some data from the TLS connection (socket emulation).

        @raise socket.error: If a socket error occurs.
        @raise tlslite.errors.TLSAbruptCloseError: If the socket is closed
        without a preceding alert.
        @raise tlslite.errors.TLSAlert: If a TLS alert is signalled.
        """
        return self.read(bufsize)

    def recv_into(self, b):
        # XXX doc string
        data = self.read(len(b))
        if not data:
            return None
        b[:len(data)] = data
        return len(data)

    def makefile(self, mode='r', bufsize=-1):
        """Create a file object for the TLS connection (socket emulation).

        @rtype: L{socket._fileobject}
        """
        self._refCount += 1
        # So, it is pretty fragile to be using Python internal objects
        # like this, but it is probably the best/easiest way to provide
        # matching behavior for socket emulation purposes.  The 'close'
        # argument is nice, its apparently a recent addition to this
        # class, so that when fileobject.close() gets called, it will
        # close() us, causing the refcount to be decremented (decrefAsync).
        #
        # If this is the last close() on the outstanding fileobjects / 
        # TLSConnection, then the "actual" close alerts will be sent,
        # socket closed, etc.
        if sys.version_info < (3,):
            return socket._fileobject(self, mode, bufsize, close=True)
        else:
            # XXX need to wrap this further if buffering is requested
            return socket.SocketIO(self, mode)

    def getsockname(self):
        """Return the socket's own address (socket emulation)."""
        return self.sock.getsockname()

    def getpeername(self):
        """Return the remote address to which the socket is connected
        (socket emulation)."""
        return self.sock.getpeername()

    def settimeout(self, value):
        """Set a timeout on blocking socket operations (socket emulation)."""
        return self.sock.settimeout(value)

    def gettimeout(self):
        """Return the timeout associated with socket operations (socket
        emulation)."""
        return self.sock.gettimeout()

    def setsockopt(self, level, optname, value):
        """Set the value of the given socket option (socket emulation)."""
        return self.sock.setsockopt(level, optname, value)

    def shutdown(self, how):
        """Shutdown the underlying socket."""
        return self.sock.shutdown(how)
    	
    def fileno(self):
        """Not implement in TLS Lite."""
        raise NotImplementedError()
    	

     #*********************************************************
     # Public Functions END
     #*********************************************************

    def _shutdown(self, resumable):
        self._writeState = _ConnectionState()
        self._readState = _ConnectionState()
        self.version = (0,0)
        self._versionCheck = False
        self.closed = True
        if self.closeSocket:
            self.sock.close()

        #Even if resumable is False, we'll never toggle this on
        if not resumable and self.session:
            self.session.resumable = False


    def _sendError(self, alertDescription, errorStr=None):
        alert = Alert().create(alertDescription, AlertLevel.fatal)
        for result in self._sendMsg(alert):
            yield result
        self._shutdown(False)
        raise TLSLocalAlert(alert, errorStr)

    def _sendMsgs(self, msgs):
        randomizeFirstBlock = True
        for msg in msgs:
            for result in self._sendMsg(msg, randomizeFirstBlock):
                yield result
            randomizeFirstBlock = True

    def _sendMsg(self, msg, randomizeFirstBlock = True):
        #Whenever we're connected and asked to send an app data message,
        #we first send the first byte of the message.  This prevents
        #an attacker from launching a chosen-plaintext attack based on
        #knowing the next IV (a la BEAST).
        if not self.closed and randomizeFirstBlock and self.version <= (3,1) \
                and self._writeState.encContext \
                and self._writeState.encContext.isBlockCipher \
                and isinstance(msg, ApplicationData):
            msgFirstByte = msg.splitFirstByte()
            for result in self._sendMsg(msgFirstByte,
                                       randomizeFirstBlock = False):
                yield result                                            

        b = msg.write()
        
        # If a 1-byte message was passed in, and we "split" the 
        # first(only) byte off above, we may have a 0-length msg:
        if len(b) == 0:
            return
            
        contentType = msg.contentType

        #Update handshake hashes
        if contentType == ContentType.handshake:
            self._handshake_md5.update(compat26Str(b))
            self._handshake_sha.update(compat26Str(b))

        #Calculate MAC
        if self._writeState.macContext:
            seqnumBytes = self._writeState.getSeqNumBytes()
            mac = self._writeState.macContext.copy()
            mac.update(compatHMAC(seqnumBytes))
            mac.update(compatHMAC(bytearray([contentType])))
            if self.version == (3,0):
                mac.update( compatHMAC( bytearray([len(b)//256] )))
                mac.update( compatHMAC( bytearray([len(b)%256] )))
            elif self.version in ((3,1), (3,2)):
                mac.update(compatHMAC( bytearray([self.version[0]] )))
                mac.update(compatHMAC( bytearray([self.version[1]] )))
                mac.update( compatHMAC( bytearray([len(b)//256] )))
                mac.update( compatHMAC( bytearray([len(b)%256] )))
            else:
                raise AssertionError()
            mac.update(compatHMAC(b))
            macBytes = bytearray(mac.digest())
            if self.fault == Fault.badMAC:
                macBytes[0] = (macBytes[0]+1) % 256

        #Encrypt for Block or Stream Cipher
        if self._writeState.encContext:
            #Add padding and encrypt (for Block Cipher):
            if self._writeState.encContext.isBlockCipher:

                #Add TLS 1.1 fixed block
                if self.version == (3,2):
                    b = self.fixedIVBlock + b

                #Add padding: b = b+ (macBytes + paddingBytes)
                currentLength = len(b) + len(macBytes) + 1
                blockLength = self._writeState.encContext.block_size
                paddingLength = blockLength-(currentLength % blockLength)

                paddingBytes = bytearray([paddingLength] * (paddingLength+1))
                if self.fault == Fault.badPadding:
                    paddingBytes[0] = (paddingBytes[0]+1) % 256
                endBytes = macBytes + paddingBytes
                b += endBytes
                #Encrypt
                b = self._writeState.encContext.encrypt(b)

            #Encrypt (for Stream Cipher)
            else:
                b += macBytes
                b = self._writeState.encContext.encrypt(b)

        #Add record header and send
        r = RecordHeader3().create(self.version, contentType, len(b))
        s = r.write() + b
        while 1:
            try:
                bytesSent = self.sock.send(s) #Might raise socket.error
            except socket.error as why:
                if why.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    yield 1
                    continue
                else:
                    # The socket was unexpectedly closed.  The tricky part
                    # is that there may be an alert sent by the other party
                    # sitting in the read buffer.  So, if we get here after
                    # handshaking, we will just raise the error and let the
                    # caller read more data if it would like, thus stumbling
                    # upon the error.
                    #
                    # However, if we get here DURING handshaking, we take
                    # it upon ourselves to see if the next message is an 
                    # Alert.
                    if contentType == ContentType.handshake:
                        
                        # See if there's an alert record
                        # Could raise socket.error or TLSAbruptCloseError
                        for result in self._getNextRecord():
                            if result in (0,1):
                                yield result
                                
                        # Closes the socket
                        self._shutdown(False)
                        
                        # If we got an alert, raise it        
                        recordHeader, p = result                        
                        if recordHeader.type == ContentType.alert:
                            alert = Alert().parse(p)
                            raise TLSRemoteAlert(alert)
                    else:
                        # If we got some other message who know what
                        # the remote side is doing, just go ahead and
                        # raise the socket.error
                        raise
            if bytesSent == len(s):
                return
            s = s[bytesSent:]
            yield 1


    def _getMsg(self, expectedType, secondaryType=None, constructorType=None):
        try:
            if not isinstance(expectedType, tuple):
                expectedType = (expectedType,)

            #Spin in a loop, until we've got a non-empty record of a type we
            #expect.  The loop will be repeated if:
            #  - we receive a renegotiation attempt; we send no_renegotiation,
            #    then try again
            #  - we receive an empty application-data fragment; we try again
            while 1:
                for result in self._getNextRecord():
                    if result in (0,1):
                        yield result
                recordHeader, p = result

                #If this is an empty application-data fragment, try again
                if recordHeader.type == ContentType.application_data:
                    if p.index == len(p.bytes):
                        continue

                #If we received an unexpected record type...
                if recordHeader.type not in expectedType:

                    #If we received an alert...
                    if recordHeader.type == ContentType.alert:
                        alert = Alert().parse(p)

                        #We either received a fatal error, a warning, or a
                        #close_notify.  In any case, we're going to close the
                        #connection.  In the latter two cases we respond with
                        #a close_notify, but ignore any socket errors, since
                        #the other side might have already closed the socket.
                        if alert.level == AlertLevel.warning or \
                           alert.description == AlertDescription.close_notify:

                            #If the sendMsg() call fails because the socket has
                            #already been closed, we will be forgiving and not
                            #report the error nor invalidate the "resumability"
                            #of the session.
                            try:
                                alertMsg = Alert()
                                alertMsg.create(AlertDescription.close_notify,
                                                AlertLevel.warning)
                                for result in self._sendMsg(alertMsg):
                                    yield result
                            except socket.error:
                                pass

                            if alert.description == \
                                   AlertDescription.close_notify:
                                self._shutdown(True)
                            elif alert.level == AlertLevel.warning:
                                self._shutdown(False)

                        else: #Fatal alert:
                            self._shutdown(False)

                        #Raise the alert as an exception
                        raise TLSRemoteAlert(alert)

                    #If we received a renegotiation attempt...
                    if recordHeader.type == ContentType.handshake:
                        subType = p.get(1)
                        reneg = False
                        if self._client:
                            if subType == HandshakeType.hello_request:
                                reneg = True
                        else:
                            if subType == HandshakeType.client_hello:
                                reneg = True
                        #Send no_renegotiation, then try again
                        if reneg:
                            alertMsg = Alert()
                            alertMsg.create(AlertDescription.no_renegotiation,
                                            AlertLevel.warning)
                            for result in self._sendMsg(alertMsg):
                                yield result
                            continue

                    #Otherwise: this is an unexpected record, but neither an
                    #alert nor renegotiation
                    for result in self._sendError(\
                            AlertDescription.unexpected_message,
                            "received type=%d" % recordHeader.type):
                        yield result

                break

            #Parse based on content_type
            if recordHeader.type == ContentType.change_cipher_spec:
                yield ChangeCipherSpec().parse(p)
            elif recordHeader.type == ContentType.alert:
                yield Alert().parse(p)
            elif recordHeader.type == ContentType.application_data:
                yield ApplicationData().parse(p)
            elif recordHeader.type == ContentType.handshake:
                #Convert secondaryType to tuple, if it isn't already
                if not isinstance(secondaryType, tuple):
                    secondaryType = (secondaryType,)

                #If it's a handshake message, check handshake header
                if recordHeader.ssl2:
                    subType = p.get(1)
                    if subType != HandshakeType.client_hello:
                        for result in self._sendError(\
                                AlertDescription.unexpected_message,
                                "Can only handle SSLv2 ClientHello messages"):
                            yield result
                    if HandshakeType.client_hello not in secondaryType:
                        for result in self._sendError(\
                                AlertDescription.unexpected_message):
                            yield result
                    subType = HandshakeType.client_hello
                else:
                    subType = p.get(1)
                    if subType not in secondaryType:
                        for result in self._sendError(\
                                AlertDescription.unexpected_message,
                                "Expecting %s, got %s" % (str(secondaryType), subType)):
                            yield result

                #Update handshake hashes
                self._handshake_md5.update(compat26Str(p.bytes))
                self._handshake_sha.update(compat26Str(p.bytes))

                #Parse based on handshake type
                if subType == HandshakeType.client_hello:
                    yield ClientHello(recordHeader.ssl2).parse(p)
                elif subType == HandshakeType.server_hello:
                    yield ServerHello().parse(p)
                elif subType == HandshakeType.certificate:
                    yield Certificate(constructorType).parse(p)
                elif subType == HandshakeType.certificate_request:
                    yield CertificateRequest().parse(p)
                elif subType == HandshakeType.certificate_verify:
                    yield CertificateVerify().parse(p)
                elif subType == HandshakeType.server_key_exchange:
                    yield ServerKeyExchange(constructorType).parse(p)
                elif subType == HandshakeType.server_hello_done:
                    yield ServerHelloDone().parse(p)
                elif subType == HandshakeType.client_key_exchange:
                    yield ClientKeyExchange(constructorType, \
                                            self.version).parse(p)
                elif subType == HandshakeType.finished:
                    yield Finished(self.version).parse(p)
                elif subType == HandshakeType.next_protocol:
                    yield NextProtocol().parse(p)
                else:
                    raise AssertionError()

        #If an exception was raised by a Parser or Message instance:
        except SyntaxError as e:
            for result in self._sendError(AlertDescription.decode_error,
                                         formatExceptionTrace(e)):
                yield result


    #Returns next record or next handshake message
    def _getNextRecord(self):

        #If there's a handshake message waiting, return it
        if self._handshakeBuffer:
            recordHeader, b = self._handshakeBuffer[0]
            self._handshakeBuffer = self._handshakeBuffer[1:]
            yield (recordHeader, Parser(b))
            return

        #Otherwise...
        #Read the next record header
        b = bytearray(0)
        recordHeaderLength = 1
        ssl2 = False
        while 1:
            try:
                s = self.sock.recv(recordHeaderLength-len(b))
            except socket.error as why:
                if why.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    yield 0
                    continue
                else:
                    raise

            #If the connection was abruptly closed, raise an error
            if len(s)==0:
                raise TLSAbruptCloseError()

            b += bytearray(s)
            if len(b)==1:
                if b[0] in ContentType.all:
                    ssl2 = False
                    recordHeaderLength = 5
                elif b[0] == 128:
                    ssl2 = True
                    recordHeaderLength = 2
                else:
                    raise SyntaxError()
            if len(b) == recordHeaderLength:
                break

        #Parse the record header
        if ssl2:
            r = RecordHeader2().parse(Parser(b))
        else:
            r = RecordHeader3().parse(Parser(b))

        #Check the record header fields
        if r.length > 18432:
            for result in self._sendError(AlertDescription.record_overflow):
                yield result

        #Read the record contents
        b = bytearray(0)
        while 1:
            try:
                s = self.sock.recv(r.length - len(b))
            except socket.error as why:
                if why.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    yield 0
                    continue
                else:
                    raise

            #If the connection is closed, raise a socket error
            if len(s)==0:
                    raise TLSAbruptCloseError()

            b += bytearray(s)
            if len(b) == r.length:
                break

        #Check the record header fields (2)
        #We do this after reading the contents from the socket, so that
        #if there's an error, we at least don't leave extra bytes in the
        #socket..
        #
        # THIS CHECK HAS NO SECURITY RELEVANCE (?), BUT COULD HURT INTEROP.
        # SO WE LEAVE IT OUT FOR NOW.
        #
        #if self._versionCheck and r.version != self.version:
        #    for result in self._sendError(AlertDescription.protocol_version,
        #            "Version in header field: %s, should be %s" % (str(r.version),
        #                                                       str(self.version))):
        #        yield result

        #Decrypt the record
        for result in self._decryptRecord(r.type, b):
            if result in (0,1): yield result
            else: break
        b = result
        p = Parser(b)

        #If it doesn't contain handshake messages, we can just return it
        if r.type != ContentType.handshake:
            yield (r, p)
        #If it's an SSLv2 ClientHello, we can return it as well
        elif r.ssl2:
            yield (r, p)
        else:
            #Otherwise, we loop through and add the handshake messages to the
            #handshake buffer
            while 1:
                if p.index == len(b): #If we're at the end
                    if not self._handshakeBuffer:
                        for result in self._sendError(\
                                AlertDescription.decode_error, \
                                "Received empty handshake record"):
                            yield result
                    break
                #There needs to be at least 4 bytes to get a header
                if p.index+4 > len(b):
                    for result in self._sendError(\
                            AlertDescription.decode_error,
                            "A record has a partial handshake message (1)"):
                        yield result
                p.get(1) # skip handshake type
                msgLength = p.get(3)
                if p.index+msgLength > len(b):
                    for result in self._sendError(\
                            AlertDescription.decode_error,
                            "A record has a partial handshake message (2)"):
                        yield result

                handshakePair = (r, b[p.index-4 : p.index+msgLength])
                self._handshakeBuffer.append(handshakePair)
                p.index += msgLength

            #We've moved at least one handshake message into the
            #handshakeBuffer, return the first one
            recordHeader, b = self._handshakeBuffer[0]
            self._handshakeBuffer = self._handshakeBuffer[1:]
            yield (recordHeader, Parser(b))


    def _decryptRecord(self, recordType, b):
        if self._readState.encContext:

            #Decrypt if it's a block cipher
            if self._readState.encContext.isBlockCipher:
                blockLength = self._readState.encContext.block_size
                if len(b) % blockLength != 0:
                    for result in self._sendError(\
                            AlertDescription.decryption_failed,
                            "Encrypted data not a multiple of blocksize"):
                        yield result
                b = self._readState.encContext.decrypt(b)
                if self.version == (3,2): #For TLS 1.1, remove explicit IV
                    b = b[self._readState.encContext.block_size : ]

                #Check padding
                paddingGood = True
                paddingLength = b[-1]
                if (paddingLength+1) > len(b):
                    paddingGood=False
                    totalPaddingLength = 0
                else:
                    if self.version == (3,0):
                        totalPaddingLength = paddingLength+1
                    elif self.version in ((3,1), (3,2)):
                        totalPaddingLength = paddingLength+1
                        paddingBytes = b[-totalPaddingLength:-1]
                        for byte in paddingBytes:
                            if byte != paddingLength:
                                paddingGood = False
                                totalPaddingLength = 0
                    else:
                        raise AssertionError()

            #Decrypt if it's a stream cipher
            else:
                paddingGood = True
                b = self._readState.encContext.decrypt(b)
                totalPaddingLength = 0

            #Check MAC
            macGood = True
            macLength = self._readState.macContext.digest_size
            endLength = macLength + totalPaddingLength
            if endLength > len(b):
                macGood = False
            else:
                #Read MAC
                startIndex = len(b) - endLength
                endIndex = startIndex + macLength
                checkBytes = b[startIndex : endIndex]

                #Calculate MAC
                seqnumBytes = self._readState.getSeqNumBytes()
                b = b[:-endLength]
                mac = self._readState.macContext.copy()
                mac.update(compatHMAC(seqnumBytes))
                mac.update(compatHMAC(bytearray([recordType])))
                if self.version == (3,0):
                    mac.update( compatHMAC(bytearray( [len(b)//256] ) ))
                    mac.update( compatHMAC(bytearray( [len(b)%256] ) ))
                elif self.version in ((3,1), (3,2)):
                    mac.update(compatHMAC(bytearray( [self.version[0]] ) ))
                    mac.update(compatHMAC(bytearray( [self.version[1]] ) ))
                    mac.update(compatHMAC(bytearray( [len(b)//256] ) ))
                    mac.update(compatHMAC(bytearray( [len(b)%256] ) ))
                else:
                    raise AssertionError()
                mac.update(compatHMAC(b))
                macBytes = bytearray(mac.digest())

                #Compare MACs
                if macBytes != checkBytes:
                    macGood = False

            if not (paddingGood and macGood):
                for result in self._sendError(AlertDescription.bad_record_mac,
                                          "MAC failure (or padding failure)"):
                    yield result

        yield b

    def _handshakeStart(self, client):
        if not self.closed:
            raise ValueError("Renegotiation disallowed for security reasons")
        self._client = client
        self._handshake_md5 = hashlib.md5()
        self._handshake_sha = hashlib.sha1()
        self._handshakeBuffer = []
        self.allegedSrpUsername = None
        self._refCount = 1

    def _handshakeDone(self, resumed):
        self.resumed = resumed
        self.closed = False

    def _calcPendingStates(self, cipherSuite, masterSecret,
            clientRandom, serverRandom, implementations):
        if cipherSuite in CipherSuite.aes128Suites:
            keyLength = 16
            ivLength = 16
            createCipherFunc = createAES
        elif cipherSuite in CipherSuite.aes256Suites:
            keyLength = 32
            ivLength = 16
            createCipherFunc = createAES
        elif cipherSuite in CipherSuite.rc4Suites:
            keyLength = 16
            ivLength = 0
            createCipherFunc = createRC4
        elif cipherSuite in CipherSuite.tripleDESSuites:
            keyLength = 24
            ivLength = 8
            createCipherFunc = createTripleDES
        else:
            raise AssertionError()
            
        if cipherSuite in CipherSuite.shaSuites:
            macLength = 20
            digestmod = hashlib.sha1        
        elif cipherSuite in CipherSuite.md5Suites:
            macLength = 16
            digestmod = hashlib.md5

        if self.version == (3,0):
            createMACFunc = createMAC_SSL
        elif self.version in ((3,1), (3,2)):
            createMACFunc = createHMAC

        outputLength = (macLength*2) + (keyLength*2) + (ivLength*2)

        #Calculate Keying Material from Master Secret
        if self.version == (3,0):
            keyBlock = PRF_SSL(masterSecret,
                               serverRandom + clientRandom,
                               outputLength)
        elif self.version in ((3,1), (3,2)):
            keyBlock = PRF(masterSecret,
                           b"key expansion",
                           serverRandom + clientRandom,
                           outputLength)
        else:
            raise AssertionError()

        #Slice up Keying Material
        clientPendingState = _ConnectionState()
        serverPendingState = _ConnectionState()
        p = Parser(keyBlock)
        clientMACBlock = p.getFixBytes(macLength)
        serverMACBlock = p.getFixBytes(macLength)
        clientKeyBlock = p.getFixBytes(keyLength)
        serverKeyBlock = p.getFixBytes(keyLength)
        clientIVBlock  = p.getFixBytes(ivLength)
        serverIVBlock  = p.getFixBytes(ivLength)
        clientPendingState.macContext = createMACFunc(
            compatHMAC(clientMACBlock), digestmod=digestmod)
        serverPendingState.macContext = createMACFunc(
            compatHMAC(serverMACBlock), digestmod=digestmod)
        clientPendingState.encContext = createCipherFunc(clientKeyBlock,
                                                         clientIVBlock,
                                                         implementations)
        serverPendingState.encContext = createCipherFunc(serverKeyBlock,
                                                         serverIVBlock,
                                                         implementations)

        #Assign new connection states to pending states
        if self._client:
            self._pendingWriteState = clientPendingState
            self._pendingReadState = serverPendingState
        else:
            self._pendingWriteState = serverPendingState
            self._pendingReadState = clientPendingState

        if self.version == (3,2) and ivLength:
            #Choose fixedIVBlock for TLS 1.1 (this is encrypted with the CBC
            #residue to create the IV for each sent block)
            self.fixedIVBlock = getRandomBytes(ivLength)

    def _changeWriteState(self):
        self._writeState = self._pendingWriteState
        self._pendingWriteState = _ConnectionState()

    def _changeReadState(self):
        self._readState = self._pendingReadState
        self._pendingReadState = _ConnectionState()

    #Used for Finished messages and CertificateVerify messages in SSL v3
    def _calcSSLHandshakeHash(self, masterSecret, label):
        imac_md5 = self._handshake_md5.copy()
        imac_sha = self._handshake_sha.copy()

        imac_md5.update(compatHMAC(label + masterSecret + bytearray([0x36]*48)))
        imac_sha.update(compatHMAC(label + masterSecret + bytearray([0x36]*40)))

        md5Bytes = MD5(masterSecret + bytearray([0x5c]*48) + \
                         bytearray(imac_md5.digest()))
        shaBytes = SHA1(masterSecret + bytearray([0x5c]*40) + \
                         bytearray(imac_sha.digest()))

        return md5Bytes + shaBytes


########NEW FILE########
__FILENAME__ = aes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Abstract class for AES."""

class AES(object):
    def __init__(self, key, mode, IV, implementation):
        if len(key) not in (16, 24, 32):
            raise AssertionError()
        if mode != 2:
            raise AssertionError()
        if len(IV) != 16:
            raise AssertionError()
        self.isBlockCipher = True
        self.block_size = 16
        self.implementation = implementation
        if len(key)==16:
            self.name = "aes128"
        elif len(key)==24:
            self.name = "aes192"
        elif len(key)==32:
            self.name = "aes256"
        else:
            raise AssertionError()

    #CBC-Mode encryption, returns ciphertext
    #WARNING: *MAY* modify the input as well
    def encrypt(self, plaintext):
        assert(len(plaintext) % 16 == 0)

    #CBC-Mode decryption, returns plaintext
    #WARNING: *MAY* modify the input as well
    def decrypt(self, ciphertext):
        assert(len(ciphertext) % 16 == 0)
########NEW FILE########
__FILENAME__ = asn1parser
# Author: Trevor Perrin
# Patch from Google adding getChildBytes()
#
# See the LICENSE file for legal information regarding use of this file.

"""Class for parsing ASN.1"""
from .compat import *
from .codec import *

#Takes a byte array which has a DER TLV field at its head
class ASN1Parser(object):
    def __init__(self, bytes):
        p = Parser(bytes)
        p.get(1) #skip Type

        #Get Length
        self.length = self._getASN1Length(p)

        #Get Value
        self.value = p.getFixBytes(self.length)

    #Assuming this is a sequence...
    def getChild(self, which):
        return ASN1Parser(self.getChildBytes(which))

    def getChildBytes(self, which):
        p = Parser(self.value)
        for x in range(which+1):
            markIndex = p.index
            p.get(1) #skip Type
            length = self._getASN1Length(p)
            p.getFixBytes(length)
        return p.bytes[markIndex : p.index]

    #Decode the ASN.1 DER length field
    def _getASN1Length(self, p):
        firstLength = p.get(1)
        if firstLength<=127:
            return firstLength
        else:
            lengthLength = firstLength & 0x7F
            return p.get(lengthLength)

########NEW FILE########
__FILENAME__ = cipherfactory
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Factory functions for symmetric cryptography."""

import os

from tlslite.utils import python_aes
from tlslite.utils import python_rc4

from tlslite.utils import cryptomath

tripleDESPresent = False

if cryptomath.m2cryptoLoaded:
    from tlslite.utils import openssl_aes
    from tlslite.utils import openssl_rc4
    from tlslite.utils import openssl_tripledes
    tripleDESPresent = True

if cryptomath.pycryptoLoaded:
    from tlslite.utils import pycrypto_aes
    from tlslite.utils import pycrypto_rc4
    from tlslite.utils import pycrypto_tripledes
    tripleDESPresent = True

# **************************************************************************
# Factory Functions for AES
# **************************************************************************

def createAES(key, IV, implList=None):
    """Create a new AES object.

    @type key: str
    @param key: A 16, 24, or 32 byte string.

    @type IV: str
    @param IV: A 16 byte string

    @rtype: L{tlslite.utils.AES}
    @return: An AES object.
    """
    if implList == None:
        implList = ["openssl", "pycrypto", "python"]

    for impl in implList:
        if impl == "openssl" and cryptomath.m2cryptoLoaded:
            return openssl_aes.new(key, 2, IV)
        elif impl == "pycrypto" and cryptomath.pycryptoLoaded:
            return pycrypto_aes.new(key, 2, IV)
        elif impl == "python":
            return python_aes.new(key, 2, IV)
    raise NotImplementedError()

def createRC4(key, IV, implList=None):
    """Create a new RC4 object.

    @type key: str
    @param key: A 16 to 32 byte string.

    @type IV: object
    @param IV: Ignored, whatever it is.

    @rtype: L{tlslite.utils.RC4}
    @return: An RC4 object.
    """
    if implList == None:
        implList = ["openssl", "pycrypto", "python"]

    if len(IV) != 0:
        raise AssertionError()
    for impl in implList:
        if impl == "openssl" and cryptomath.m2cryptoLoaded:
            return openssl_rc4.new(key)
        elif impl == "pycrypto" and cryptomath.pycryptoLoaded:
            return pycrypto_rc4.new(key)
        elif impl == "python":
            return python_rc4.new(key)
    raise NotImplementedError()

#Create a new TripleDES instance
def createTripleDES(key, IV, implList=None):
    """Create a new 3DES object.

    @type key: str
    @param key: A 24 byte string.

    @type IV: str
    @param IV: An 8 byte string

    @rtype: L{tlslite.utils.TripleDES}
    @return: A 3DES object.
    """
    if implList == None:
        implList = ["openssl", "pycrypto"]

    for impl in implList:
        if impl == "openssl" and cryptomath.m2cryptoLoaded:
            return openssl_tripledes.new(key, 2, IV)
        elif impl == "pycrypto" and cryptomath.pycryptoLoaded:
            return pycrypto_tripledes.new(key, 2, IV)
    raise NotImplementedError()
########NEW FILE########
__FILENAME__ = codec
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Classes for reading/writing binary data (such as TLS records)."""

from .compat import *

class Writer(object):
    def __init__(self):
        self.bytes = bytearray(0)

    def add(self, x, length):
        self.bytes += bytearray(length)
        newIndex = len(self.bytes) - 1
        for count in range(length):
            self.bytes[newIndex] = x & 0xFF
            x >>= 8
            newIndex -= 1

    def addFixSeq(self, seq, length):
        for e in seq:
            self.add(e, length)

    def addVarSeq(self, seq, length, lengthLength):
        self.add(len(seq)*length, lengthLength)
        for e in seq:
            self.add(e, length)

class Parser(object):
    def __init__(self, bytes):
        self.bytes = bytes
        self.index = 0

    def get(self, length):
        if self.index + length > len(self.bytes):
            raise SyntaxError()
        x = 0
        for count in range(length):
            x <<= 8
            x |= self.bytes[self.index]
            self.index += 1
        return x

    def getFixBytes(self, lengthBytes):
        bytes = self.bytes[self.index : self.index+lengthBytes]
        self.index += lengthBytes
        return bytes

    def getVarBytes(self, lengthLength):
        lengthBytes = self.get(lengthLength)
        return self.getFixBytes(lengthBytes)

    def getFixList(self, length, lengthList):
        l = [0] * lengthList
        for x in range(lengthList):
            l[x] = self.get(length)
        return l

    def getVarList(self, length, lengthLength):
        lengthList = self.get(lengthLength)
        if lengthList % length != 0:
            raise SyntaxError()
        lengthList = lengthList // length
        l = [0] * lengthList
        for x in range(lengthList):
            l[x] = self.get(length)
        return l

    def startLengthCheck(self, lengthLength):
        self.lengthCheck = self.get(lengthLength)
        self.indexCheck = self.index

    def setLengthCheck(self, length):
        self.lengthCheck = length
        self.indexCheck = self.index

    def stopLengthCheck(self):
        if (self.index - self.indexCheck) != self.lengthCheck:
            raise SyntaxError()

    def atLengthCheck(self):
        if (self.index - self.indexCheck) < self.lengthCheck:
            return False
        elif (self.index - self.indexCheck) == self.lengthCheck:
            return True
        else:
            raise SyntaxError()

########NEW FILE########
__FILENAME__ = compat
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Miscellaneous functions to mask Python version differences."""

import sys
import os
import math
import binascii

if sys.version_info >= (3,0):

    def compat26Str(x): return x
    
    # Python 3 requires bytes instead of bytearrays for HMAC   
    
    # So, python 2.6 requires strings, python 3 requires 'bytes',
    # and python 2.7 can handle bytearrays...     
    def compatHMAC(x): return bytes(x)
    
    def raw_input(s):
        return input(s)
    
    # So, the python3 binascii module deals with bytearrays, and python2
    # deals with strings...  I would rather deal with the "a" part as
    # strings, and the "b" part as bytearrays, regardless of python version,
    # so...
    def a2b_hex(s):
        try:
            b = bytearray(binascii.a2b_hex(bytearray(s, "ascii")))
        except Exception as e:
            raise SyntaxError("base16 error: %s" % e) 
        return b  

    def a2b_base64(s):
        try:
            b = bytearray(binascii.a2b_base64(bytearray(s, "ascii")))
        except Exception as e:
            raise SyntaxError("base64 error: %s" % e)
        return b

    def b2a_hex(b):
        return binascii.b2a_hex(b).decode("ascii")    
            
    def b2a_base64(b):
        return binascii.b2a_base64(b).decode("ascii") 

    def b2a_base32(b):
        return base64.b32encode(b).decode("ascii")
        
    def readStdinBinary():
        return sys.stdin.buffer.read()        

else:
    # Python 2.6 requires strings instead of bytearrays in a couple places,
    # so we define this function so it does the conversion if needed.
    if sys.version_info < (2,7):
        def compat26Str(x): return str(x)
    else:
        def compat26Str(x): return x

    # So, python 2.6 requires strings, python 3 requires 'bytes',
    # and python 2.7 can handle bytearrays...     
    def compatHMAC(x): return compat26Str(x)

    def a2b_hex(s):
        try:
            b = bytearray(binascii.a2b_hex(s))
        except Exception as e:
            raise SyntaxError("base16 error: %s" % e)
        return b

    def a2b_base64(s):
        try:
            b = bytearray(binascii.a2b_base64(s))
        except Exception as e:
            raise SyntaxError("base64 error: %s" % e)
        return b
        
    def b2a_hex(b):
        return binascii.b2a_hex(compat26Str(b))
        
    def b2a_base64(b):
        return binascii.b2a_base64(compat26Str(b))
        
    def b2a_base32(b):
        return base64.b32encode(str(b))

import traceback
def formatExceptionTrace(e):
    newStr = "".join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
    return newStr


########NEW FILE########
__FILENAME__ = cryptomath
# Authors: 
#   Trevor Perrin
#   Martin von Loewis - python 3 port
#
# See the LICENSE file for legal information regarding use of this file.

"""cryptomath module

This module has basic math/crypto code."""
from __future__ import print_function
import os
import math
import base64
import binascii

from .compat import *


# **************************************************************************
# Load Optional Modules
# **************************************************************************

# Try to load M2Crypto/OpenSSL
try:
    from M2Crypto import m2
    m2cryptoLoaded = True

except ImportError:
    m2cryptoLoaded = False

#Try to load GMPY
try:
    import gmpy
    gmpyLoaded = True
except ImportError:
    gmpyLoaded = False

#Try to load pycrypto
try:
    import Crypto.Cipher.AES
    pycryptoLoaded = True
except ImportError:
    pycryptoLoaded = False


# **************************************************************************
# PRNG Functions
# **************************************************************************

# Check that os.urandom works
import zlib
length = len(zlib.compress(os.urandom(1000)))
assert(length > 900)

def getRandomBytes(howMany):
    b = bytearray(os.urandom(howMany))
    assert(len(b) == howMany)
    return b

prngName = "os.urandom"

# **************************************************************************
# Simple hash functions
# **************************************************************************

import hmac
import hashlib

def MD5(b):
    return bytearray(hashlib.md5(compat26Str(b)).digest())

def SHA1(b):
    return bytearray(hashlib.sha1(compat26Str(b)).digest())

def HMAC_MD5(k, b):
    k = compatHMAC(k)
    b = compatHMAC(b)
    return bytearray(hmac.new(k, b, hashlib.md5).digest())

def HMAC_SHA1(k, b):
    k = compatHMAC(k)
    b = compatHMAC(b)
    return bytearray(hmac.new(k, b, hashlib.sha1).digest())


# **************************************************************************
# Converter Functions
# **************************************************************************

def bytesToNumber(b):
    total = 0
    multiplier = 1
    for count in range(len(b)-1, -1, -1):
        byte = b[count]
        total += multiplier * byte
        multiplier *= 256
    return total

def numberToByteArray(n, howManyBytes=None):
    """Convert an integer into a bytearray, zero-pad to howManyBytes.

    The returned bytearray may be smaller than howManyBytes, but will
    not be larger.  The returned bytearray will contain a big-endian
    encoding of the input integer (n).
    """    
    if howManyBytes == None:
        howManyBytes = numBytes(n)
    b = bytearray(howManyBytes)
    for count in range(howManyBytes-1, -1, -1):
        b[count] = int(n % 256)
        n >>= 8
    return b

def mpiToNumber(mpi): #mpi is an openssl-format bignum string
    if (ord(mpi[4]) & 0x80) !=0: #Make sure this is a positive number
        raise AssertionError()
    b = bytearray(mpi[4:])
    return bytesToNumber(b)

def numberToMPI(n):
    b = numberToByteArray(n)
    ext = 0
    #If the high-order bit is going to be set,
    #add an extra byte of zeros
    if (numBits(n) & 0x7)==0:
        ext = 1
    length = numBytes(n) + ext
    b = bytearray(4+ext) + b
    b[0] = (length >> 24) & 0xFF
    b[1] = (length >> 16) & 0xFF
    b[2] = (length >> 8) & 0xFF
    b[3] = length & 0xFF
    return bytes(b)


# **************************************************************************
# Misc. Utility Functions
# **************************************************************************

def numBits(n):
    if n==0:
        return 0
    s = "%x" % n
    return ((len(s)-1)*4) + \
    {'0':0, '1':1, '2':2, '3':2,
     '4':3, '5':3, '6':3, '7':3,
     '8':4, '9':4, 'a':4, 'b':4,
     'c':4, 'd':4, 'e':4, 'f':4,
     }[s[0]]
    return int(math.floor(math.log(n, 2))+1)

def numBytes(n):
    if n==0:
        return 0
    bits = numBits(n)
    return int(math.ceil(bits / 8.0))

# **************************************************************************
# Big Number Math
# **************************************************************************

def getRandomNumber(low, high):
    if low >= high:
        raise AssertionError()
    howManyBits = numBits(high)
    howManyBytes = numBytes(high)
    lastBits = howManyBits % 8
    while 1:
        bytes = getRandomBytes(howManyBytes)
        if lastBits:
            bytes[0] = bytes[0] % (1 << lastBits)
        n = bytesToNumber(bytes)
        if n >= low and n < high:
            return n

def gcd(a,b):
    a, b = max(a,b), min(a,b)
    while b:
        a, b = b, a % b
    return a

def lcm(a, b):
    return (a * b) // gcd(a, b)

#Returns inverse of a mod b, zero if none
#Uses Extended Euclidean Algorithm
def invMod(a, b):
    c, d = a, b
    uc, ud = 1, 0
    while c != 0:
        q = d // c
        c, d = d-(q*c), c
        uc, ud = ud - (q * uc), uc
    if d == 1:
        return ud % b
    return 0


if gmpyLoaded:
    def powMod(base, power, modulus):
        base = gmpy.mpz(base)
        power = gmpy.mpz(power)
        modulus = gmpy.mpz(modulus)
        result = pow(base, power, modulus)
        return long(result)

else:
    def powMod(base, power, modulus):
        if power < 0:
            result = pow(base, power*-1, modulus)
            result = invMod(result, modulus)
            return result
        else:
            return pow(base, power, modulus)

#Pre-calculate a sieve of the ~100 primes < 1000:
def makeSieve(n):
    sieve = list(range(n))
    for count in range(2, int(math.sqrt(n))+1):
        if sieve[count] == 0:
            continue
        x = sieve[count] * 2
        while x < len(sieve):
            sieve[x] = 0
            x += sieve[count]
    sieve = [x for x in sieve[2:] if x]
    return sieve

sieve = makeSieve(1000)

def isPrime(n, iterations=5, display=False):
    #Trial division with sieve
    for x in sieve:
        if x >= n: return True
        if n % x == 0: return False
    #Passed trial division, proceed to Rabin-Miller
    #Rabin-Miller implemented per Ferguson & Schneier
    #Compute s, t for Rabin-Miller
    if display: print("*", end=' ')
    s, t = n-1, 0
    while s % 2 == 0:
        s, t = s//2, t+1
    #Repeat Rabin-Miller x times
    a = 2 #Use 2 as a base for first iteration speedup, per HAC
    for count in range(iterations):
        v = powMod(a, s, n)
        if v==1:
            continue
        i = 0
        while v != n-1:
            if i == t-1:
                return False
            else:
                v, i = powMod(v, 2, n), i+1
        a = getRandomNumber(2, n)
    return True

def getRandomPrime(bits, display=False):
    if bits < 10:
        raise AssertionError()
    #The 1.5 ensures the 2 MSBs are set
    #Thus, when used for p,q in RSA, n will have its MSB set
    #
    #Since 30 is lcm(2,3,5), we'll set our test numbers to
    #29 % 30 and keep them there
    low = ((2 ** (bits-1)) * 3) // 2
    high = 2 ** bits - 30
    p = getRandomNumber(low, high)
    p += 29 - (p % 30)
    while 1:
        if display: print(".", end=' ')
        p += 30
        if p >= high:
            p = getRandomNumber(low, high)
            p += 29 - (p % 30)
        if isPrime(p, display=display):
            return p

#Unused at the moment...
def getRandomSafePrime(bits, display=False):
    if bits < 10:
        raise AssertionError()
    #The 1.5 ensures the 2 MSBs are set
    #Thus, when used for p,q in RSA, n will have its MSB set
    #
    #Since 30 is lcm(2,3,5), we'll set our test numbers to
    #29 % 30 and keep them there
    low = (2 ** (bits-2)) * 3//2
    high = (2 ** (bits-1)) - 30
    q = getRandomNumber(low, high)
    q += 29 - (q % 30)
    while 1:
        if display: print(".", end=' ')
        q += 30
        if (q >= high):
            q = getRandomNumber(low, high)
            q += 29 - (q % 30)
        #Ideas from Tom Wu's SRP code
        #Do trial division on p and q before Rabin-Miller
        if isPrime(q, 0, display=display):
            p = (2 * q) + 1
            if isPrime(p, display=display):
                if isPrime(q, display=display):
                    return p

########NEW FILE########
__FILENAME__ = datefuncs
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

import os

#Functions for manipulating datetime objects
#CCYY-MM-DDThh:mm:ssZ
def parseDateClass(s):
    year, month, day = s.split("-")
    day, tail = day[:2], day[2:]
    hour, minute, second = tail[1:].split(":")
    second = second[:2]
    year, month, day = int(year), int(month), int(day)
    hour, minute, second = int(hour), int(minute), int(second)
    return createDateClass(year, month, day, hour, minute, second)


if os.name != "java":
    from datetime import datetime, timedelta

    #Helper functions for working with a date/time class
    def createDateClass(year, month, day, hour, minute, second):
        return datetime(year, month, day, hour, minute, second)

    def printDateClass(d):
        #Split off fractional seconds, append 'Z'
        return d.isoformat().split(".")[0]+"Z"

    def getNow():
        return datetime.utcnow()

    def getHoursFromNow(hours):
        return datetime.utcnow() + timedelta(hours=hours)

    def getMinutesFromNow(minutes):
        return datetime.utcnow() + timedelta(minutes=minutes)

    def isDateClassExpired(d):
        return d < datetime.utcnow()

    def isDateClassBefore(d1, d2):
        return d1 < d2

else:
    #Jython 2.1 is missing lots of python 2.3 stuff,
    #which we have to emulate here:
    import java
    import jarray

    def createDateClass(year, month, day, hour, minute, second):
        c = java.util.Calendar.getInstance()
        c.setTimeZone(java.util.TimeZone.getTimeZone("UTC"))
        c.set(year, month-1, day, hour, minute, second)
        return c

    def printDateClass(d):
        return "%04d-%02d-%02dT%02d:%02d:%02dZ" % \
        (d.get(d.YEAR), d.get(d.MONTH)+1, d.get(d.DATE), \
        d.get(d.HOUR_OF_DAY), d.get(d.MINUTE), d.get(d.SECOND))

    def getNow():
        c = java.util.Calendar.getInstance()
        c.setTimeZone(java.util.TimeZone.getTimeZone("UTC"))
        c.get(c.HOUR) #force refresh?
        return c

    def getHoursFromNow(hours):
        d = getNow()
        d.add(d.HOUR, hours)
        return d

    def isDateClassExpired(d):
        n = getNow()
        return d.before(n)

    def isDateClassBefore(d1, d2):
        return d1.before(d2)

########NEW FILE########
__FILENAME__ = keyfactory
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Factory functions for asymmetric cryptography.
@sort: generateRSAKey, parsePEMKey, parseAsPublicKey
"""

from .compat import *

from .rsakey import RSAKey
from .python_rsakey import Python_RSAKey
from tlslite.utils import cryptomath

if cryptomath.m2cryptoLoaded:
    from .openssl_rsakey import OpenSSL_RSAKey

if cryptomath.pycryptoLoaded:
    from .pycrypto_rsakey import PyCrypto_RSAKey

# **************************************************************************
# Factory Functions for RSA Keys
# **************************************************************************

def generateRSAKey(bits, implementations=["openssl", "python"]):
    """Generate an RSA key with the specified bit length.

    @type bits: int
    @param bits: Desired bit length of the new key's modulus.

    @rtype: L{tlslite.utils.rsakey.RSAKey}
    @return: A new RSA private key.
    """
    for implementation in implementations:
        if implementation == "openssl" and cryptomath.m2cryptoLoaded:
            return OpenSSL_RSAKey.generate(bits)
        elif implementation == "python":
            return Python_RSAKey.generate(bits)
    raise ValueError("No acceptable implementations")

#Parse as an OpenSSL or Python key
def parsePEMKey(s, private=False, public=False, passwordCallback=None,
                implementations=["openssl", "python"]):
    """Parse a PEM-format key.

    The PEM format is used by OpenSSL and other tools.  The
    format is typically used to store both the public and private
    components of a key.  For example::

       -----BEGIN RSA PRIVATE KEY-----
        MIICXQIBAAKBgQDYscuoMzsGmW0pAYsmyHltxB2TdwHS0dImfjCMfaSDkfLdZY5+
        dOWORVns9etWnr194mSGA1F0Pls/VJW8+cX9+3vtJV8zSdANPYUoQf0TP7VlJxkH
        dSRkUbEoz5bAAs/+970uos7n7iXQIni+3erUTdYEk2iWnMBjTljfgbK/dQIDAQAB
        AoGAJHoJZk75aKr7DSQNYIHuruOMdv5ZeDuJvKERWxTrVJqE32/xBKh42/IgqRrc
        esBN9ZregRCd7YtxoL+EVUNWaJNVx2mNmezEznrc9zhcYUrgeaVdFO2yBF1889zO
        gCOVwrO8uDgeyj6IKa25H6c1N13ih/o7ZzEgWbGG+ylU1yECQQDv4ZSJ4EjSh/Fl
        aHdz3wbBa/HKGTjC8iRy476Cyg2Fm8MZUe9Yy3udOrb5ZnS2MTpIXt5AF3h2TfYV
        VoFXIorjAkEA50FcJmzT8sNMrPaV8vn+9W2Lu4U7C+K/O2g1iXMaZms5PC5zV5aV
        CKXZWUX1fq2RaOzlbQrpgiolhXpeh8FjxwJBAOFHzSQfSsTNfttp3KUpU0LbiVvv
        i+spVSnA0O4rq79KpVNmK44Mq67hsW1P11QzrzTAQ6GVaUBRv0YS061td1kCQHnP
        wtN2tboFR6lABkJDjxoGRvlSt4SOPr7zKGgrWjeiuTZLHXSAnCY+/hr5L9Q3ZwXG
        6x6iBdgLjVIe4BZQNtcCQQDXGv/gWinCNTN3MPWfTW/RGzuMYVmyBFais0/VrgdH
        h1dLpztmpQqfyH/zrBXQ9qL/zR4ojS6XYneO/U18WpEe
        -----END RSA PRIVATE KEY-----

    To generate a key like this with OpenSSL, run::

        openssl genrsa 2048 > key.pem

    This format also supports password-encrypted private keys.  TLS
    Lite can only handle password-encrypted private keys when OpenSSL
    and M2Crypto are installed.  In this case, passwordCallback will be
    invoked to query the user for the password.

    @type s: str
    @param s: A string containing a PEM-encoded public or private key.

    @type private: bool
    @param private: If True, a L{SyntaxError} will be raised if the
    private key component is not present.

    @type public: bool
    @param public: If True, the private key component (if present) will
    be discarded, so this function will always return a public key.

    @type passwordCallback: callable
    @param passwordCallback: This function will be called, with no
    arguments, if the PEM-encoded private key is password-encrypted.
    The callback should return the password string.  If the password is
    incorrect, SyntaxError will be raised.  If no callback is passed
    and the key is password-encrypted, a prompt will be displayed at
    the console.

    @rtype: L{tlslite.utils.RSAKey.RSAKey}
    @return: An RSA key.

    @raise SyntaxError: If the key is not properly formatted.
    """
    for implementation in implementations:
        if implementation == "openssl" and cryptomath.m2cryptoLoaded:
            key = OpenSSL_RSAKey.parse(s, passwordCallback)
            break
        elif implementation == "python":
            key = Python_RSAKey.parsePEM(s)
            break
    else:
        raise ValueError("No acceptable implementations")

    return _parseKeyHelper(key, private, public)


def _parseKeyHelper(key, private, public):
    if private:
        if not key.hasPrivateKey():
            raise SyntaxError("Not a private key!")

    if public:
        return _createPublicKey(key)

    if private:
        if hasattr(key, "d"):
            return _createPrivateKey(key)
        else:
            return key

    return key

def parseAsPublicKey(s):
    """Parse a PEM-formatted public key.

    @type s: str
    @param s: A string containing a PEM-encoded public or private key.

    @rtype: L{tlslite.utils.rsakey.RSAKey}
    @return: An RSA public key.

    @raise SyntaxError: If the key is not properly formatted.
    """
    return parsePEMKey(s, public=True)

def parsePrivateKey(s):
    """Parse a PEM-formatted private key.

    @type s: str
    @param s: A string containing a PEM-encoded private key.

    @rtype: L{tlslite.utils.rsakey.RSAKey}
    @return: An RSA private key.

    @raise SyntaxError: If the key is not properly formatted.
    """
    return parsePEMKey(s, private=True)

def _createPublicKey(key):
    """
    Create a new public key.  Discard any private component,
    and return the most efficient key possible.
    """
    if not isinstance(key, RSAKey):
        raise AssertionError()
    return _createPublicRSAKey(key.n, key.e)

def _createPrivateKey(key):
    """
    Create a new private key.  Return the most efficient key possible.
    """
    if not isinstance(key, RSAKey):
        raise AssertionError()
    if not key.hasPrivateKey():
        raise AssertionError()
    return _createPrivateRSAKey(key.n, key.e, key.d, key.p, key.q, key.dP,
                                key.dQ, key.qInv)

def _createPublicRSAKey(n, e, implementations = ["openssl", "pycrypto",
                                                "python"]):
    for implementation in implementations:
        if implementation == "openssl" and cryptomath.m2cryptoLoaded:
            return OpenSSL_RSAKey(n, e)
        elif implementation == "pycrypto" and cryptomath.pycryptoLoaded:
            return PyCrypto_RSAKey(n, e)
        elif implementation == "python":
            return Python_RSAKey(n, e)
    raise ValueError("No acceptable implementations")

def _createPrivateRSAKey(n, e, d, p, q, dP, dQ, qInv,
                        implementations = ["pycrypto", "python"]):
    for implementation in implementations:
        if implementation == "pycrypto" and cryptomath.pycryptoLoaded:
            return PyCrypto_RSAKey(n, e, d, p, q, dP, dQ, qInv)
        elif implementation == "python":
            return Python_RSAKey(n, e, d, p, q, dP, dQ, qInv)
    raise ValueError("No acceptable implementations")

########NEW FILE########
__FILENAME__ = openssl_aes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""OpenSSL/M2Crypto AES implementation."""

from .cryptomath import *
from .aes import *

if m2cryptoLoaded:

    def new(key, mode, IV):
        return OpenSSL_AES(key, mode, IV)

    class OpenSSL_AES(AES):

        def __init__(self, key, mode, IV):
            AES.__init__(self, key, mode, IV, "openssl")
            self.key = key
            self.IV = IV

        def _createContext(self, encrypt):
            context = m2.cipher_ctx_new()
            if len(self.key)==16:
                cipherType = m2.aes_128_cbc()
            if len(self.key)==24:
                cipherType = m2.aes_192_cbc()
            if len(self.key)==32:
                cipherType = m2.aes_256_cbc()
            m2.cipher_init(context, cipherType, self.key, self.IV, encrypt)
            return context

        def encrypt(self, plaintext):
            AES.encrypt(self, plaintext)
            context = self._createContext(1)
            ciphertext = m2.cipher_update(context, plaintext)
            m2.cipher_ctx_free(context)
            self.IV = ciphertext[-self.block_size:]
            return bytearray(ciphertext)

        def decrypt(self, ciphertext):
            AES.decrypt(self, ciphertext)
            context = self._createContext(0)
            #I think M2Crypto has a bug - it fails to decrypt and return the last block passed in.
            #To work around this, we append sixteen zeros to the string, below:
            plaintext = m2.cipher_update(context, ciphertext+('\0'*16))

            #If this bug is ever fixed, then plaintext will end up having a garbage
            #plaintext block on the end.  That's okay - the below code will discard it.
            plaintext = plaintext[:len(ciphertext)]
            m2.cipher_ctx_free(context)
            self.IV = ciphertext[-self.block_size:]
            return bytearray(plaintext)

########NEW FILE########
__FILENAME__ = openssl_rc4
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""OpenSSL/M2Crypto RC4 implementation."""

from .cryptomath import *
from .rc4 import RC4

if m2cryptoLoaded:

    def new(key):
        return OpenSSL_RC4(key)

    class OpenSSL_RC4(RC4):

        def __init__(self, key):
            RC4.__init__(self, key, "openssl")
            self.rc4 = m2.rc4_new()
            m2.rc4_set_key(self.rc4, key)

        def __del__(self):
            m2.rc4_free(self.rc4)

        def encrypt(self, plaintext):
            return bytearray(m2.rc4_update(self.rc4, plaintext))

        def decrypt(self, ciphertext):
            return bytearray(self.encrypt(ciphertext))

########NEW FILE########
__FILENAME__ = openssl_rsakey
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""OpenSSL/M2Crypto RSA implementation."""

from .cryptomath import *

from .rsakey import *
from .python_rsakey import Python_RSAKey

#copied from M2Crypto.util.py, so when we load the local copy of m2
#we can still use it
def password_callback(v, prompt1='Enter private key passphrase:',
                           prompt2='Verify passphrase:'):
    from getpass import getpass
    while 1:
        try:
            p1=getpass(prompt1)
            if v:
                p2=getpass(prompt2)
                if p1==p2:
                    break
            else:
                break
        except KeyboardInterrupt:
            return None
    return p1


if m2cryptoLoaded:
    class OpenSSL_RSAKey(RSAKey):
        def __init__(self, n=0, e=0):
            self.rsa = None
            self._hasPrivateKey = False
            if (n and not e) or (e and not n):
                raise AssertionError()
            if n and e:
                self.rsa = m2.rsa_new()
                m2.rsa_set_n(self.rsa, numberToMPI(n))
                m2.rsa_set_e(self.rsa, numberToMPI(e))

        def __del__(self):
            if self.rsa:
                m2.rsa_free(self.rsa)

        def __getattr__(self, name):
            if name == 'e':
                if not self.rsa:
                    return 0
                return mpiToNumber(m2.rsa_get_e(self.rsa))
            elif name == 'n':
                if not self.rsa:
                    return 0
                return mpiToNumber(m2.rsa_get_n(self.rsa))
            else:
                raise AttributeError

        def hasPrivateKey(self):
            return self._hasPrivateKey

        def _rawPrivateKeyOp(self, m):
            b = numberToByteArray(m, numBytes(self.n))
            s = m2.rsa_private_encrypt(self.rsa, bytes(b), m2.no_padding)
            c = bytesToNumber(bytearray(s))
            return c

        def _rawPublicKeyOp(self, c):
            b = numberToByteArray(c, numBytes(self.n))
            s = m2.rsa_public_decrypt(self.rsa, bytes(b), m2.no_padding)
            m = bytesToNumber(bytearray(s))
            return m

        def acceptsPassword(self): return True

        def write(self, password=None):
            bio = m2.bio_new(m2.bio_s_mem())
            if self._hasPrivateKey:
                if password:
                    def f(v): return password
                    m2.rsa_write_key(self.rsa, bio, m2.des_ede_cbc(), f)
                else:
                    def f(): pass
                    m2.rsa_write_key_no_cipher(self.rsa, bio, f)
            else:
                if password:
                    raise AssertionError()
                m2.rsa_write_pub_key(self.rsa, bio)
            s = m2.bio_read(bio, m2.bio_ctrl_pending(bio))
            m2.bio_free(bio)
            return s

        def generate(bits):
            key = OpenSSL_RSAKey()
            def f():pass
            key.rsa = m2.rsa_generate_key(bits, 3, f)
            key._hasPrivateKey = True
            return key
        generate = staticmethod(generate)

        def parse(s, passwordCallback=None):
            # Skip forward to the first PEM header
            start = s.find("-----BEGIN ")
            if start == -1:
                raise SyntaxError()
            s = s[start:]            
            if s.startswith("-----BEGIN "):
                if passwordCallback==None:
                    callback = password_callback
                else:
                    def f(v, prompt1=None, prompt2=None):
                        return passwordCallback()
                    callback = f
                bio = m2.bio_new(m2.bio_s_mem())
                try:
                    m2.bio_write(bio, s)
                    key = OpenSSL_RSAKey()
                    if s.startswith("-----BEGIN RSA PRIVATE KEY-----"):
                        def f():pass
                        key.rsa = m2.rsa_read_key(bio, callback)
                        if key.rsa == None:
                            raise SyntaxError()
                        key._hasPrivateKey = True
                    elif s.startswith("-----BEGIN PUBLIC KEY-----"):
                        key.rsa = m2.rsa_read_pub_key(bio)
                        if key.rsa == None:
                            raise SyntaxError()
                        key._hasPrivateKey = False
                    else:
                        raise SyntaxError()
                    return key
                finally:
                    m2.bio_free(bio)
            else:
                raise SyntaxError()

        parse = staticmethod(parse)

########NEW FILE########
__FILENAME__ = openssl_tripledes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""OpenSSL/M2Crypto 3DES implementation."""

from .cryptomath import *
from .tripledes import *

if m2cryptoLoaded:

    def new(key, mode, IV):
        return OpenSSL_TripleDES(key, mode, IV)

    class OpenSSL_TripleDES(TripleDES):

        def __init__(self, key, mode, IV):
            TripleDES.__init__(self, key, mode, IV, "openssl")
            self.key = key
            self.IV = IV

        def _createContext(self, encrypt):
            context = m2.cipher_ctx_new()
            cipherType = m2.des_ede3_cbc()
            m2.cipher_init(context, cipherType, self.key, self.IV, encrypt)
            return context

        def encrypt(self, plaintext):
            TripleDES.encrypt(self, plaintext)
            context = self._createContext(1)
            ciphertext = m2.cipher_update(context, plaintext)
            m2.cipher_ctx_free(context)
            self.IV = ciphertext[-self.block_size:]
            return bytearray(ciphertext)

        def decrypt(self, ciphertext):
            TripleDES.decrypt(self, ciphertext)
            context = self._createContext(0)
            #I think M2Crypto has a bug - it fails to decrypt and return the last block passed in.
            #To work around this, we append sixteen zeros to the string, below:
            plaintext = m2.cipher_update(context, ciphertext+('\0'*16))

            #If this bug is ever fixed, then plaintext will end up having a garbage
            #plaintext block on the end.  That's okay - the below code will ignore it.
            plaintext = plaintext[:len(ciphertext)]
            m2.cipher_ctx_free(context)
            self.IV = ciphertext[-self.block_size:]
            return bytearray(plaintext)
########NEW FILE########
__FILENAME__ = pem
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

from .compat import *
import binascii

#This code is shared with tackpy (somewhat), so I'd rather make minimal
#changes, and preserve the use of a2b_base64 throughout.

def dePem(s, name):
    """Decode a PEM string into a bytearray of its payload.
    
    The input must contain an appropriate PEM prefix and postfix
    based on the input name string, e.g. for name="CERTIFICATE":

    -----BEGIN CERTIFICATE-----
    MIIBXDCCAUSgAwIBAgIBADANBgkqhkiG9w0BAQUFADAPMQ0wCwYDVQQDEwRUQUNL
...
    KoZIhvcNAQEFBQADAwA5kw==
    -----END CERTIFICATE-----    

    The first such PEM block in the input will be found, and its
    payload will be base64 decoded and returned.
    """
    prefix  = "-----BEGIN %s-----" % name
    postfix = "-----END %s-----" % name    
    start = s.find(prefix)
    if start == -1:
        raise SyntaxError("Missing PEM prefix")
    end = s.find(postfix, start+len(prefix))
    if end == -1:
        raise SyntaxError("Missing PEM postfix")
    s = s[start+len("-----BEGIN %s-----" % name) : end]
    retBytes = a2b_base64(s) # May raise SyntaxError
    return retBytes
    
def dePemList(s, name):
    """Decode a sequence of PEM blocks into a list of bytearrays.

    The input must contain any number of PEM blocks, each with the appropriate
    PEM prefix and postfix based on the input name string, e.g. for
    name="TACK BREAK SIG".  Arbitrary text can appear between and before and
    after the PEM blocks.  For example:

    " Created by TACK.py 0.9.3 Created at 2012-02-01T00:30:10Z -----BEGIN TACK
    BREAK SIG-----
    ATKhrz5C6JHJW8BF5fLVrnQss6JnWVyEaC0p89LNhKPswvcC9/s6+vWLd9snYTUv
    YMEBdw69PUP8JB4AdqA3K6Ap0Fgd9SSTOECeAKOUAym8zcYaXUwpk0+WuPYa7Zmm
    SkbOlK4ywqt+amhWbg9txSGUwFO5tWUHT3QrnRlE/e3PeNFXLx5Bckg= -----END TACK
    BREAK SIG----- Created by TACK.py 0.9.3 Created at 2012-02-01T00:30:11Z
    -----BEGIN TACK BREAK SIG-----
    ATKhrz5C6JHJW8BF5fLVrnQss6JnWVyEaC0p89LNhKPswvcC9/s6+vWLd9snYTUv
    YMEBdw69PUP8JB4AdqA3K6BVCWfcjN36lx6JwxmZQncS6sww7DecFO/qjSePCxwM
    +kdDqX/9/183nmjx6bf0ewhPXkA0nVXsDYZaydN8rJU1GaMlnjcIYxY= -----END TACK
    BREAK SIG----- "
    
    All such PEM blocks will be found, decoded, and return in an ordered list
    of bytearrays, which may have zero elements if not PEM blocks are found.
     """
    bList = []
    prefix  = "-----BEGIN %s-----" % name
    postfix = "-----END %s-----" % name
    while 1:
        start = s.find(prefix)
        if start == -1:
            return bList
        end = s.find(postfix, start+len(prefix))
        if end == -1:
            raise SyntaxError("Missing PEM postfix")
        s2 = s[start+len(prefix) : end]
        retBytes = a2b_base64(s2) # May raise SyntaxError
        bList.append(retBytes)
        s = s[end+len(postfix) : ]

def pem(b, name):
    """Encode a payload bytearray into a PEM string.
    
    The input will be base64 encoded, then wrapped in a PEM prefix/postfix
    based on the name string, e.g. for name="CERTIFICATE":
    
    -----BEGIN CERTIFICATE-----
    MIIBXDCCAUSgAwIBAgIBADANBgkqhkiG9w0BAQUFADAPMQ0wCwYDVQQDEwRUQUNL
...
    KoZIhvcNAQEFBQADAwA5kw==
    -----END CERTIFICATE-----    
    """
    s1 = b2a_base64(b)[:-1] # remove terminating \n
    s2 = ""
    while s1:
        s2 += s1[:64] + "\n"
        s1 = s1[64:]
    s = ("-----BEGIN %s-----\n" % name) + s2 + \
        ("-----END %s-----\n" % name)     
    return s

def pemSniff(inStr, name):
    searchStr = "-----BEGIN %s-----" % name
    return searchStr in inStr

########NEW FILE########
__FILENAME__ = pycrypto_aes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""PyCrypto AES implementation."""

from .cryptomath import *
from .aes import *

if pycryptoLoaded:
    import Crypto.Cipher.AES

    def new(key, mode, IV):
        return PyCrypto_AES(key, mode, IV)

    class PyCrypto_AES(AES):

        def __init__(self, key, mode, IV):
            AES.__init__(self, key, mode, IV, "pycrypto")
            key = bytes(key)
            IV = bytes(IV)
            self.context = Crypto.Cipher.AES.new(key, mode, IV)

        def encrypt(self, plaintext):
            plaintext = bytes(plaintext)
            return bytearray(self.context.encrypt(plaintext))

        def decrypt(self, ciphertext):
            ciphertext = bytes(ciphertext)
            return bytearray(self.context.decrypt(ciphertext))

########NEW FILE########
__FILENAME__ = pycrypto_rc4
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""PyCrypto RC4 implementation."""

from .cryptomath import *
from .rc4 import *

if pycryptoLoaded:
    import Crypto.Cipher.ARC4

    def new(key):
        return PyCrypto_RC4(key)

    class PyCrypto_RC4(RC4):

        def __init__(self, key):
            RC4.__init__(self, key, "pycrypto")
            key = bytes(key)
            self.context = Crypto.Cipher.ARC4.new(key)

        def encrypt(self, plaintext):
            plaintext = bytes(plaintext)
            return bytearray(self.context.encrypt(plaintext))

        def decrypt(self, ciphertext):
            ciphertext = bytes(ciphertext)
            return bytearray(self.context.decrypt(ciphertext))
########NEW FILE########
__FILENAME__ = pycrypto_rsakey
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""PyCrypto RSA implementation."""

from .cryptomath import *

from .rsakey import *
from .python_rsakey import Python_RSAKey

if pycryptoLoaded:

    from Crypto.PublicKey import RSA

    class PyCrypto_RSAKey(RSAKey):
        def __init__(self, n=0, e=0, d=0, p=0, q=0, dP=0, dQ=0, qInv=0):
            if not d:
                self.rsa = RSA.construct( (long(n), long(e)) )
            else:
                self.rsa = RSA.construct( (long(n), long(e), long(d), long(p), long(q)) )

        def __getattr__(self, name):
            return getattr(self.rsa, name)

        def hasPrivateKey(self):
            return self.rsa.has_private()

        def _rawPrivateKeyOp(self, m):
            c = self.rsa.decrypt((m,))
            return c

        def _rawPublicKeyOp(self, c):
            m = self.rsa.encrypt(c, None)[0]
            return m

        def generate(bits):
            key = PyCrypto_RSAKey()
            def f(numBytes):
                return bytes(getRandomBytes(numBytes))
            key.rsa = RSA.generate(bits, f)
            return key
        generate = staticmethod(generate)

########NEW FILE########
__FILENAME__ = pycrypto_tripledes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""PyCrypto 3DES implementation."""

from .cryptomath import *
from .tripledes import *

if pycryptoLoaded:
    import Crypto.Cipher.DES3

    def new(key, mode, IV):
        return PyCrypto_TripleDES(key, mode, IV)

    class PyCrypto_TripleDES(TripleDES):

        def __init__(self, key, mode, IV):
            TripleDES.__init__(self, key, mode, IV, "pycrypto")
            key = bytes(key)
            IV = bytes(IV)
            self.context = Crypto.Cipher.DES3.new(key, mode, IV)

        def encrypt(self, plaintext):
            plaintext = bytes(plaintext)
            return bytearray(self.context.encrypt(plaintext))

        def decrypt(self, ciphertext):
            ciphertext = bytes(ciphertext)
            return bytearray(self.context.decrypt(ciphertext))
########NEW FILE########
__FILENAME__ = python_aes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Pure-Python AES implementation."""

from .cryptomath import *

from .aes import *
from .rijndael import rijndael

def new(key, mode, IV):
    return Python_AES(key, mode, IV)

class Python_AES(AES):
    def __init__(self, key, mode, IV):
        AES.__init__(self, key, mode, IV, "python")
        self.rijndael = rijndael(key, 16)
        self.IV = IV

    def encrypt(self, plaintext):
        AES.encrypt(self, plaintext)

        plaintextBytes = plaintext[:]
        chainBytes = self.IV[:]

        #CBC Mode: For each block...
        for x in range(len(plaintextBytes)//16):

            #XOR with the chaining block
            blockBytes = plaintextBytes[x*16 : (x*16)+16]
            for y in range(16):
                blockBytes[y] ^= chainBytes[y]

            #Encrypt it
            encryptedBytes = self.rijndael.encrypt(blockBytes)

            #Overwrite the input with the output
            for y in range(16):
                plaintextBytes[(x*16)+y] = encryptedBytes[y]

            #Set the next chaining block
            chainBytes = encryptedBytes

        self.IV = chainBytes[:]
        return plaintextBytes

    def decrypt(self, ciphertext):
        AES.decrypt(self, ciphertext)

        ciphertextBytes = ciphertext[:]
        chainBytes = self.IV[:]

        #CBC Mode: For each block...
        for x in range(len(ciphertextBytes)//16):

            #Decrypt it
            blockBytes = ciphertextBytes[x*16 : (x*16)+16]
            decryptedBytes = self.rijndael.decrypt(blockBytes)

            #XOR with the chaining block and overwrite the input with output
            for y in range(16):
                decryptedBytes[y] ^= chainBytes[y]
                ciphertextBytes[(x*16)+y] = decryptedBytes[y]

            #Set the next chaining block
            chainBytes = blockBytes

        self.IV = chainBytes[:]
        return ciphertextBytes

########NEW FILE########
__FILENAME__ = python_rc4
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Pure-Python RC4 implementation."""

from .rc4 import RC4
from .cryptomath import *

def new(key):
    return Python_RC4(key)

class Python_RC4(RC4):
    def __init__(self, keyBytes):
        RC4.__init__(self, keyBytes, "python")
        S = [i for i in range(256)]
        j = 0
        for i in range(256):
            j = (j + S[i] + keyBytes[i % len(keyBytes)]) % 256
            S[i], S[j] = S[j], S[i]

        self.S = S
        self.i = 0
        self.j = 0

    def encrypt(self, plaintextBytes):
        ciphertextBytes = plaintextBytes[:]
        S = self.S
        i = self.i
        j = self.j
        for x in range(len(ciphertextBytes)):
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            t = (S[i] + S[j]) % 256
            ciphertextBytes[x] ^= S[t]
        self.i = i
        self.j = j
        return ciphertextBytes

    def decrypt(self, ciphertext):
        return self.encrypt(ciphertext)

########NEW FILE########
__FILENAME__ = python_rsakey
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Pure-Python RSA implementation."""

from .cryptomath import *
from .asn1parser import ASN1Parser
from .rsakey import *
from .pem import *

class Python_RSAKey(RSAKey):
    def __init__(self, n=0, e=0, d=0, p=0, q=0, dP=0, dQ=0, qInv=0):
        if (n and not e) or (e and not n):
            raise AssertionError()
        self.n = n
        self.e = e
        self.d = d
        self.p = p
        self.q = q
        self.dP = dP
        self.dQ = dQ
        self.qInv = qInv
        self.blinder = 0
        self.unblinder = 0

    def hasPrivateKey(self):
        return self.d != 0

    def _rawPrivateKeyOp(self, m):
        #Create blinding values, on the first pass:
        if not self.blinder:
            self.unblinder = getRandomNumber(2, self.n)
            self.blinder = powMod(invMod(self.unblinder, self.n), self.e,
                                  self.n)

        #Blind the input
        m = (m * self.blinder) % self.n

        #Perform the RSA operation
        c = self._rawPrivateKeyOpHelper(m)

        #Unblind the output
        c = (c * self.unblinder) % self.n

        #Update blinding values
        self.blinder = (self.blinder * self.blinder) % self.n
        self.unblinder = (self.unblinder * self.unblinder) % self.n

        #Return the output
        return c


    def _rawPrivateKeyOpHelper(self, m):
        #Non-CRT version
        #c = powMod(m, self.d, self.n)

        #CRT version  (~3x faster)
        s1 = powMod(m, self.dP, self.p)
        s2 = powMod(m, self.dQ, self.q)
        h = ((s1 - s2) * self.qInv) % self.p
        c = s2 + self.q * h
        return c

    def _rawPublicKeyOp(self, c):
        m = powMod(c, self.e, self.n)
        return m

    def acceptsPassword(self): return False

    def generate(bits):
        key = Python_RSAKey()
        p = getRandomPrime(bits//2, False)
        q = getRandomPrime(bits//2, False)
        t = lcm(p-1, q-1)
        key.n = p * q
        key.e = 65537
        key.d = invMod(key.e, t)
        key.p = p
        key.q = q
        key.dP = key.d % (p-1)
        key.dQ = key.d % (q-1)
        key.qInv = invMod(q, p)
        return key
    generate = staticmethod(generate)

    def parsePEM(s, passwordCallback=None):
        """Parse a string containing a <privateKey> or <publicKey>, or
        PEM-encoded key."""

        if pemSniff(s, "PRIVATE KEY"):
            bytes = dePem(s, "PRIVATE KEY")
            return Python_RSAKey._parsePKCS8(bytes)
        elif pemSniff(s, "RSA PRIVATE KEY"):
            bytes = dePem(s, "RSA PRIVATE KEY")
            return Python_RSAKey._parseSSLeay(bytes)
        else:
            raise SyntaxError("Not a PEM private key file")
    parsePEM = staticmethod(parsePEM)

    def _parsePKCS8(bytes):
        p = ASN1Parser(bytes)

        version = p.getChild(0).value[0]
        if version != 0:
            raise SyntaxError("Unrecognized PKCS8 version")

        rsaOID = p.getChild(1).value
        if list(rsaOID) != [6, 9, 42, 134, 72, 134, 247, 13, 1, 1, 1, 5, 0]:
            raise SyntaxError("Unrecognized AlgorithmIdentifier")

        #Get the privateKey
        privateKeyP = p.getChild(2)

        #Adjust for OCTET STRING encapsulation
        privateKeyP = ASN1Parser(privateKeyP.value)

        return Python_RSAKey._parseASN1PrivateKey(privateKeyP)
    _parsePKCS8 = staticmethod(_parsePKCS8)

    def _parseSSLeay(bytes):
        privateKeyP = ASN1Parser(bytes)
        return Python_RSAKey._parseASN1PrivateKey(privateKeyP)
    _parseSSLeay = staticmethod(_parseSSLeay)

    def _parseASN1PrivateKey(privateKeyP):
        version = privateKeyP.getChild(0).value[0]
        if version != 0:
            raise SyntaxError("Unrecognized RSAPrivateKey version")
        n = bytesToNumber(privateKeyP.getChild(1).value)
        e = bytesToNumber(privateKeyP.getChild(2).value)
        d = bytesToNumber(privateKeyP.getChild(3).value)
        p = bytesToNumber(privateKeyP.getChild(4).value)
        q = bytesToNumber(privateKeyP.getChild(5).value)
        dP = bytesToNumber(privateKeyP.getChild(6).value)
        dQ = bytesToNumber(privateKeyP.getChild(7).value)
        qInv = bytesToNumber(privateKeyP.getChild(8).value)
        return Python_RSAKey(n, e, d, p, q, dP, dQ, qInv)
    _parseASN1PrivateKey = staticmethod(_parseASN1PrivateKey)

########NEW FILE########
__FILENAME__ = rc4
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Abstract class for RC4."""


class RC4(object):
    def __init__(self, keyBytes, implementation):
        if len(keyBytes) < 16 or len(keyBytes) > 256:
            raise ValueError()
        self.isBlockCipher = False
        self.name = "rc4"
        self.implementation = implementation

    def encrypt(self, plaintext):
        raise NotImplementedError()

    def decrypt(self, ciphertext):
        raise NotImplementedError()
########NEW FILE########
__FILENAME__ = rijndael
# Authors:
#   Bram Cohen
#   Trevor Perrin - various changes
#
# See the LICENSE file for legal information regarding use of this file.
# Also see Bram Cohen's statement below

"""
A pure python (slow) implementation of rijndael with a decent interface

To include -

from rijndael import rijndael

To do a key setup -

r = rijndael(key, block_size = 16)

key must be a string of length 16, 24, or 32
blocksize must be 16, 24, or 32. Default is 16

To use -

ciphertext = r.encrypt(plaintext)
plaintext = r.decrypt(ciphertext)

If any strings are of the wrong length a ValueError is thrown
"""

# ported from the Java reference code by Bram Cohen, bram@gawth.com, April 2001
# this code is public domain, unless someone makes
# an intellectual property claim against the reference
# code, in which case it can be made public domain by
# deleting all the comments and renaming all the variables

import copy
import string

shifts = [[[0, 0], [1, 3], [2, 2], [3, 1]],
          [[0, 0], [1, 5], [2, 4], [3, 3]],
          [[0, 0], [1, 7], [3, 5], [4, 4]]]

# [keysize][block_size]
num_rounds = {16: {16: 10, 24: 12, 32: 14}, 24: {16: 12, 24: 12, 32: 14}, 32: {16: 14, 24: 14, 32: 14}}

A = [[1, 1, 1, 1, 1, 0, 0, 0],
     [0, 1, 1, 1, 1, 1, 0, 0],
     [0, 0, 1, 1, 1, 1, 1, 0],
     [0, 0, 0, 1, 1, 1, 1, 1],
     [1, 0, 0, 0, 1, 1, 1, 1],
     [1, 1, 0, 0, 0, 1, 1, 1],
     [1, 1, 1, 0, 0, 0, 1, 1],
     [1, 1, 1, 1, 0, 0, 0, 1]]

# produce log and alog tables, needed for multiplying in the
# field GF(2^m) (generator = 3)
alog = [1]
for i in range(255):
    j = (alog[-1] << 1) ^ alog[-1]
    if j & 0x100 != 0:
        j ^= 0x11B
    alog.append(j)

log = [0] * 256
for i in range(1, 255):
    log[alog[i]] = i

# multiply two elements of GF(2^m)
def mul(a, b):
    if a == 0 or b == 0:
        return 0
    return alog[(log[a & 0xFF] + log[b & 0xFF]) % 255]

# substitution box based on F^{-1}(x)
box = [[0] * 8 for i in range(256)]
box[1][7] = 1
for i in range(2, 256):
    j = alog[255 - log[i]]
    for t in range(8):
        box[i][t] = (j >> (7 - t)) & 0x01

B = [0, 1, 1, 0, 0, 0, 1, 1]

# affine transform:  box[i] <- B + A*box[i]
cox = [[0] * 8 for i in range(256)]
for i in range(256):
    for t in range(8):
        cox[i][t] = B[t]
        for j in range(8):
            cox[i][t] ^= A[t][j] * box[i][j]

# S-boxes and inverse S-boxes
S =  [0] * 256
Si = [0] * 256
for i in range(256):
    S[i] = cox[i][0] << 7
    for t in range(1, 8):
        S[i] ^= cox[i][t] << (7-t)
    Si[S[i] & 0xFF] = i

# T-boxes
G = [[2, 1, 1, 3],
    [3, 2, 1, 1],
    [1, 3, 2, 1],
    [1, 1, 3, 2]]

AA = [[0] * 8 for i in range(4)]

for i in range(4):
    for j in range(4):
        AA[i][j] = G[i][j]
        AA[i][i+4] = 1

for i in range(4):
    pivot = AA[i][i]
    if pivot == 0:
        t = i + 1
        while AA[t][i] == 0 and t < 4:
            t += 1
            assert t != 4, 'G matrix must be invertible'
            for j in range(8):
                AA[i][j], AA[t][j] = AA[t][j], AA[i][j]
            pivot = AA[i][i]
    for j in range(8):
        if AA[i][j] != 0:
            AA[i][j] = alog[(255 + log[AA[i][j] & 0xFF] - log[pivot & 0xFF]) % 255]
    for t in range(4):
        if i != t:
            for j in range(i+1, 8):
                AA[t][j] ^= mul(AA[i][j], AA[t][i])
            AA[t][i] = 0

iG = [[0] * 4 for i in range(4)]

for i in range(4):
    for j in range(4):
        iG[i][j] = AA[i][j + 4]

def mul4(a, bs):
    if a == 0:
        return 0
    r = 0
    for b in bs:
        r <<= 8
        if b != 0:
            r = r | mul(a, b)
    return r

T1 = []
T2 = []
T3 = []
T4 = []
T5 = []
T6 = []
T7 = []
T8 = []
U1 = []
U2 = []
U3 = []
U4 = []

for t in range(256):
    s = S[t]
    T1.append(mul4(s, G[0]))
    T2.append(mul4(s, G[1]))
    T3.append(mul4(s, G[2]))
    T4.append(mul4(s, G[3]))

    s = Si[t]
    T5.append(mul4(s, iG[0]))
    T6.append(mul4(s, iG[1]))
    T7.append(mul4(s, iG[2]))
    T8.append(mul4(s, iG[3]))

    U1.append(mul4(t, iG[0]))
    U2.append(mul4(t, iG[1]))
    U3.append(mul4(t, iG[2]))
    U4.append(mul4(t, iG[3]))

# round constants
rcon = [1]
r = 1
for t in range(1, 30):
    r = mul(2, r)
    rcon.append(r)

del A
del AA
del pivot
del B
del G
del box
del log
del alog
del i
del j
del r
del s
del t
del mul
del mul4
del cox
del iG

class rijndael:
    def __init__(self, key, block_size = 16):
        if block_size != 16 and block_size != 24 and block_size != 32:
            raise ValueError('Invalid block size: ' + str(block_size))
        if len(key) != 16 and len(key) != 24 and len(key) != 32:
            raise ValueError('Invalid key size: ' + str(len(key)))
        self.block_size = block_size

        ROUNDS = num_rounds[len(key)][block_size]
        BC = block_size // 4
        # encryption round keys
        Ke = [[0] * BC for i in range(ROUNDS + 1)]
        # decryption round keys
        Kd = [[0] * BC for i in range(ROUNDS + 1)]
        ROUND_KEY_COUNT = (ROUNDS + 1) * BC
        KC = len(key) // 4

        # copy user material bytes into temporary ints
        tk = []
        for i in range(0, KC):
            tk.append((key[i * 4] << 24) | (key[i * 4 + 1] << 16) |
                (key[i * 4 + 2] << 8) | key[i * 4 + 3])

        # copy values into round key arrays
        t = 0
        j = 0
        while j < KC and t < ROUND_KEY_COUNT:
            Ke[t // BC][t % BC] = tk[j]
            Kd[ROUNDS - (t // BC)][t % BC] = tk[j]
            j += 1
            t += 1
        tt = 0
        rconpointer = 0
        while t < ROUND_KEY_COUNT:
            # extrapolate using phi (the round key evolution function)
            tt = tk[KC - 1]
            tk[0] ^= (S[(tt >> 16) & 0xFF] & 0xFF) << 24 ^  \
                     (S[(tt >>  8) & 0xFF] & 0xFF) << 16 ^  \
                     (S[ tt        & 0xFF] & 0xFF) <<  8 ^  \
                     (S[(tt >> 24) & 0xFF] & 0xFF)       ^  \
                     (rcon[rconpointer]    & 0xFF) << 24
            rconpointer += 1
            if KC != 8:
                for i in range(1, KC):
                    tk[i] ^= tk[i-1]
            else:
                for i in range(1, KC // 2):
                    tk[i] ^= tk[i-1]
                tt = tk[KC // 2 - 1]
                tk[KC // 2] ^= (S[ tt        & 0xFF] & 0xFF)       ^ \
                              (S[(tt >>  8) & 0xFF] & 0xFF) <<  8 ^ \
                              (S[(tt >> 16) & 0xFF] & 0xFF) << 16 ^ \
                              (S[(tt >> 24) & 0xFF] & 0xFF) << 24
                for i in range(KC // 2 + 1, KC):
                    tk[i] ^= tk[i-1]
            # copy values into round key arrays
            j = 0
            while j < KC and t < ROUND_KEY_COUNT:
                Ke[t // BC][t % BC] = tk[j]
                Kd[ROUNDS - (t // BC)][t % BC] = tk[j]
                j += 1
                t += 1
        # inverse MixColumn where needed
        for r in range(1, ROUNDS):
            for j in range(BC):
                tt = Kd[r][j]
                Kd[r][j] = U1[(tt >> 24) & 0xFF] ^ \
                           U2[(tt >> 16) & 0xFF] ^ \
                           U3[(tt >>  8) & 0xFF] ^ \
                           U4[ tt        & 0xFF]
        self.Ke = Ke
        self.Kd = Kd

    def encrypt(self, plaintext):
        if len(plaintext) != self.block_size:
            raise ValueError('wrong block length, expected ' + str(self.block_size) + ' got ' + str(len(plaintext)))
        Ke = self.Ke

        BC = self.block_size // 4
        ROUNDS = len(Ke) - 1
        if BC == 4:
            SC = 0
        elif BC == 6:
            SC = 1
        else:
            SC = 2
        s1 = shifts[SC][1][0]
        s2 = shifts[SC][2][0]
        s3 = shifts[SC][3][0]
        a = [0] * BC
        # temporary work array
        t = []
        # plaintext to ints + key
        for i in range(BC):
            t.append((plaintext[i * 4    ] << 24 |
                      plaintext[i * 4 + 1] << 16 |
                      plaintext[i * 4 + 2] <<  8 |
                      plaintext[i * 4 + 3]        ) ^ Ke[0][i])
        # apply round transforms
        for r in range(1, ROUNDS):
            for i in range(BC):
                a[i] = (T1[(t[ i           ] >> 24) & 0xFF] ^
                        T2[(t[(i + s1) % BC] >> 16) & 0xFF] ^
                        T3[(t[(i + s2) % BC] >>  8) & 0xFF] ^
                        T4[ t[(i + s3) % BC]        & 0xFF]  ) ^ Ke[r][i]
            t = copy.copy(a)
        # last round is special
        result = []
        for i in range(BC):
            tt = Ke[ROUNDS][i]
            result.append((S[(t[ i           ] >> 24) & 0xFF] ^ (tt >> 24)) & 0xFF)
            result.append((S[(t[(i + s1) % BC] >> 16) & 0xFF] ^ (tt >> 16)) & 0xFF)
            result.append((S[(t[(i + s2) % BC] >>  8) & 0xFF] ^ (tt >>  8)) & 0xFF)
            result.append((S[ t[(i + s3) % BC]        & 0xFF] ^  tt       ) & 0xFF)
        return bytearray(result)

    def decrypt(self, ciphertext):
        if len(ciphertext) != self.block_size:
            raise ValueError('wrong block length, expected ' + str(self.block_size) + ' got ' + str(len(plaintext)))
        Kd = self.Kd

        BC = self.block_size // 4
        ROUNDS = len(Kd) - 1
        if BC == 4:
            SC = 0
        elif BC == 6:
            SC = 1
        else:
            SC = 2
        s1 = shifts[SC][1][1]
        s2 = shifts[SC][2][1]
        s3 = shifts[SC][3][1]
        a = [0] * BC
        # temporary work array
        t = [0] * BC
        # ciphertext to ints + key
        for i in range(BC):
            t[i] = (ciphertext[i * 4    ] << 24 |
                    ciphertext[i * 4 + 1] << 16 |
                    ciphertext[i * 4 + 2] <<  8 |
                    ciphertext[i * 4 + 3]        ) ^ Kd[0][i]
        # apply round transforms
        for r in range(1, ROUNDS):
            for i in range(BC):
                a[i] = (T5[(t[ i           ] >> 24) & 0xFF] ^
                        T6[(t[(i + s1) % BC] >> 16) & 0xFF] ^
                        T7[(t[(i + s2) % BC] >>  8) & 0xFF] ^
                        T8[ t[(i + s3) % BC]        & 0xFF]  ) ^ Kd[r][i]
            t = copy.copy(a)
        # last round is special
        result = []
        for i in range(BC):
            tt = Kd[ROUNDS][i]
            result.append((Si[(t[ i           ] >> 24) & 0xFF] ^ (tt >> 24)) & 0xFF)
            result.append((Si[(t[(i + s1) % BC] >> 16) & 0xFF] ^ (tt >> 16)) & 0xFF)
            result.append((Si[(t[(i + s2) % BC] >>  8) & 0xFF] ^ (tt >>  8)) & 0xFF)
            result.append((Si[ t[(i + s3) % BC]        & 0xFF] ^  tt       ) & 0xFF)
        return bytearray(result)

def encrypt(key, block):
    return rijndael(key, len(block)).encrypt(block)

def decrypt(key, block):
    return rijndael(key, len(block)).decrypt(block)

def test():
    def t(kl, bl):
        b = 'b' * bl
        r = rijndael('a' * kl, bl)
        assert r.decrypt(r.encrypt(b)) == b
    t(16, 16)
    t(16, 24)
    t(16, 32)
    t(24, 16)
    t(24, 24)
    t(24, 32)
    t(32, 16)
    t(32, 24)
    t(32, 32)


########NEW FILE########
__FILENAME__ = rsakey
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Abstract class for RSA."""

from .cryptomath import *


class RSAKey(object):
    """This is an abstract base class for RSA keys.

    Particular implementations of RSA keys, such as
    L{openssl_rsakey.OpenSSL_RSAKey},
    L{python_rsakey.Python_RSAKey}, and
    L{pycrypto_rsakey.PyCrypto_RSAKey},
    inherit from this.

    To create or parse an RSA key, don't use one of these classes
    directly.  Instead, use the factory functions in
    L{tlslite.utils.keyfactory}.
    """

    def __init__(self, n=0, e=0):
        """Create a new RSA key.

        If n and e are passed in, the new key will be initialized.

        @type n: int
        @param n: RSA modulus.

        @type e: int
        @param e: RSA public exponent.
        """
        raise NotImplementedError()

    def __len__(self):
        """Return the length of this key in bits.

        @rtype: int
        """
        return numBits(self.n)

    def hasPrivateKey(self):
        """Return whether or not this key has a private component.

        @rtype: bool
        """
        raise NotImplementedError()

    def hashAndSign(self, bytes):
        """Hash and sign the passed-in bytes.

        This requires the key to have a private component.  It performs
        a PKCS1-SHA1 signature on the passed-in data.

        @type bytes: str or L{bytearray} of unsigned bytes
        @param bytes: The value which will be hashed and signed.

        @rtype: L{bytearray} of unsigned bytes.
        @return: A PKCS1-SHA1 signature on the passed-in data.
        """
        hashBytes = SHA1(bytearray(bytes))
        prefixedHashBytes = self._addPKCS1SHA1Prefix(hashBytes)
        sigBytes = self.sign(prefixedHashBytes)
        return sigBytes

    def hashAndVerify(self, sigBytes, bytes):
        """Hash and verify the passed-in bytes with the signature.

        This verifies a PKCS1-SHA1 signature on the passed-in data.

        @type sigBytes: L{bytearray} of unsigned bytes
        @param sigBytes: A PKCS1-SHA1 signature.

        @type bytes: str or L{bytearray} of unsigned bytes
        @param bytes: The value which will be hashed and verified.

        @rtype: bool
        @return: Whether the signature matches the passed-in data.
        """
        hashBytes = SHA1(bytearray(bytes))
        
        # Try it with/without the embedded NULL
        prefixedHashBytes1 = self._addPKCS1SHA1Prefix(hashBytes, False)
        prefixedHashBytes2 = self._addPKCS1SHA1Prefix(hashBytes, True)
        result1 = self.verify(sigBytes, prefixedHashBytes1)
        result2 = self.verify(sigBytes, prefixedHashBytes2)
        return (result1 or result2)

    def sign(self, bytes):
        """Sign the passed-in bytes.

        This requires the key to have a private component.  It performs
        a PKCS1 signature on the passed-in data.

        @type bytes: L{bytearray} of unsigned bytes
        @param bytes: The value which will be signed.

        @rtype: L{bytearray} of unsigned bytes.
        @return: A PKCS1 signature on the passed-in data.
        """
        if not self.hasPrivateKey():
            raise AssertionError()
        paddedBytes = self._addPKCS1Padding(bytes, 1)
        m = bytesToNumber(paddedBytes)
        if m >= self.n:
            raise ValueError()
        c = self._rawPrivateKeyOp(m)
        sigBytes = numberToByteArray(c, numBytes(self.n))
        return sigBytes

    def verify(self, sigBytes, bytes):
        """Verify the passed-in bytes with the signature.

        This verifies a PKCS1 signature on the passed-in data.

        @type sigBytes: L{bytearray} of unsigned bytes
        @param sigBytes: A PKCS1 signature.

        @type bytes: L{bytearray} of unsigned bytes
        @param bytes: The value which will be verified.

        @rtype: bool
        @return: Whether the signature matches the passed-in data.
        """
        if len(sigBytes) != numBytes(self.n):
            return False
        paddedBytes = self._addPKCS1Padding(bytes, 1)
        c = bytesToNumber(sigBytes)
        if c >= self.n:
            return False
        m = self._rawPublicKeyOp(c)
        checkBytes = numberToByteArray(m, numBytes(self.n))
        return checkBytes == paddedBytes

    def encrypt(self, bytes):
        """Encrypt the passed-in bytes.

        This performs PKCS1 encryption of the passed-in data.

        @type bytes: L{bytearray} of unsigned bytes
        @param bytes: The value which will be encrypted.

        @rtype: L{bytearray} of unsigned bytes.
        @return: A PKCS1 encryption of the passed-in data.
        """
        paddedBytes = self._addPKCS1Padding(bytes, 2)
        m = bytesToNumber(paddedBytes)
        if m >= self.n:
            raise ValueError()
        c = self._rawPublicKeyOp(m)
        encBytes = numberToByteArray(c, numBytes(self.n))
        return encBytes

    def decrypt(self, encBytes):
        """Decrypt the passed-in bytes.

        This requires the key to have a private component.  It performs
        PKCS1 decryption of the passed-in data.

        @type encBytes: L{bytearray} of unsigned bytes
        @param encBytes: The value which will be decrypted.

        @rtype: L{bytearray} of unsigned bytes or None.
        @return: A PKCS1 decryption of the passed-in data or None if
        the data is not properly formatted.
        """
        if not self.hasPrivateKey():
            raise AssertionError()
        if len(encBytes) != numBytes(self.n):
            return None
        c = bytesToNumber(encBytes)
        if c >= self.n:
            return None
        m = self._rawPrivateKeyOp(c)
        decBytes = numberToByteArray(m, numBytes(self.n))
        #Check first two bytes
        if decBytes[0] != 0 or decBytes[1] != 2:
            return None
        #Scan through for zero separator
        for x in range(1, len(decBytes)-1):
            if decBytes[x]== 0:
                break
        else:
            return None
        return decBytes[x+1:] #Return everything after the separator

    def _rawPrivateKeyOp(self, m):
        raise NotImplementedError()

    def _rawPublicKeyOp(self, c):
        raise NotImplementedError()

    def acceptsPassword(self):
        """Return True if the write() method accepts a password for use
        in encrypting the private key.

        @rtype: bool
        """
        raise NotImplementedError()

    def write(self, password=None):
        """Return a string containing the key.

        @rtype: str
        @return: A string describing the key, in whichever format (PEM)
        is native to the implementation.
        """
        raise NotImplementedError()

    def generate(bits):
        """Generate a new key with the specified bit length.

        @rtype: L{tlslite.utils.RSAKey.RSAKey}
        """
        raise NotImplementedError()
    generate = staticmethod(generate)


    # **************************************************************************
    # Helper Functions for RSA Keys
    # **************************************************************************

    def _addPKCS1SHA1Prefix(self, bytes, withNULL=True):
        # There is a long history of confusion over whether the SHA1 
        # algorithmIdentifier should be encoded with a NULL parameter or 
        # with the parameter omitted.  While the original intention was 
        # apparently to omit it, many toolkits went the other way.  TLS 1.2
        # specifies the NULL should be included, and this behavior is also
        # mandated in recent versions of PKCS #1, and is what tlslite has
        # always implemented.  Anyways, verification code should probably 
        # accept both.  However, nothing uses this code yet, so this is 
        # all fairly moot.
        if not withNULL:
            prefixBytes = bytearray(\
            [0x30,0x1f,0x30,0x07,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x04,0x14])            
        else:
            prefixBytes = bytearray(\
            [0x30,0x21,0x30,0x09,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x05,0x00,0x04,0x14])            
        prefixedBytes = prefixBytes + bytes
        return prefixedBytes

    def _addPKCS1Padding(self, bytes, blockType):
        padLength = (numBytes(self.n) - (len(bytes)+3))
        if blockType == 1: #Signature padding
            pad = [0xFF] * padLength
        elif blockType == 2: #Encryption padding
            pad = bytearray(0)
            while len(pad) < padLength:
                padBytes = getRandomBytes(padLength * 2)
                pad = [b for b in padBytes if b != 0]
                pad = pad[:padLength]
        else:
            raise AssertionError()

        padding = bytearray([0,blockType] + pad + [0])
        paddedBytes = padding + bytes
        return paddedBytes

########NEW FILE########
__FILENAME__ = tackwrapper
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

try:
    from tack.structures.Tack import Tack
    from tack.structures.TackExtension import TackExtension
    from tack.tls.TlsCertificate import TlsCertificate
    
    tackpyLoaded = True
except ImportError:
    tackpyLoaded = False

########NEW FILE########
__FILENAME__ = tripledes
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Abstract class for 3DES."""

class TripleDES(object):
    def __init__(self, key, mode, IV, implementation):
        if len(key) != 24:
            raise ValueError()
        if mode != 2:
            raise ValueError()
        if len(IV) != 8:
            raise ValueError()
        self.isBlockCipher = True
        self.block_size = 8
        self.implementation = implementation
        self.name = "3des"

    #CBC-Mode encryption, returns ciphertext
    #WARNING: *MAY* modify the input as well
    def encrypt(self, plaintext):
        assert(len(plaintext) % 8 == 0)

    #CBC-Mode decryption, returns plaintext
    #WARNING: *MAY* modify the input as well
    def decrypt(self, ciphertext):
        assert(len(ciphertext) % 8 == 0)

########NEW FILE########
__FILENAME__ = verifierdb
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Class for storing SRP password verifiers."""

from .utils.cryptomath import *
from .utils.compat import *
from tlslite import mathtls
from .basedb import BaseDB

class VerifierDB(BaseDB):
    """This class represent an in-memory or on-disk database of SRP
    password verifiers.

    A VerifierDB can be passed to a server handshake to authenticate
    a client based on one of the verifiers.

    This class is thread-safe.
    """
    def __init__(self, filename=None):
        """Create a new VerifierDB instance.

        @type filename: str
        @param filename: Filename for an on-disk database, or None for
        an in-memory database.  If the filename already exists, follow
        this with a call to open().  To create a new on-disk database,
        follow this with a call to create().
        """
        BaseDB.__init__(self, filename, "verifier")

    def _getItem(self, username, valueStr):
        (N, g, salt, verifier) = valueStr.split(" ")
        N = bytesToNumber(a2b_base64(N))
        g = bytesToNumber(a2b_base64(g))
        salt = a2b_base64(salt)
        verifier = bytesToNumber(a2b_base64(verifier))
        return (N, g, salt, verifier)

    def __setitem__(self, username, verifierEntry):
        """Add a verifier entry to the database.

        @type username: str
        @param username: The username to associate the verifier with.
        Must be less than 256 characters in length.  Must not already
        be in the database.

        @type verifierEntry: tuple
        @param verifierEntry: The verifier entry to add.  Use
        L{tlslite.verifierdb.VerifierDB.makeVerifier} to create a
        verifier entry.
        """
        BaseDB.__setitem__(self, username, verifierEntry)


    def _setItem(self, username, value):
        if len(username)>=256:
            raise ValueError("username too long")
        N, g, salt, verifier = value
        N = b2a_base64(numberToByteArray(N))
        g = b2a_base64(numberToByteArray(g))
        salt = b2a_base64(salt)
        verifier = b2a_base64(numberToByteArray(verifier))
        valueStr = " ".join( (N, g, salt, verifier)  )
        return valueStr

    def _checkItem(self, value, username, param):
        (N, g, salt, verifier) = value
        x = mathtls.makeX(salt, username, param)
        v = powMod(g, x, N)
        return (verifier == v)


    def makeVerifier(username, password, bits):
        """Create a verifier entry which can be stored in a VerifierDB.

        @type username: str
        @param username: The username for this verifier.  Must be less
        than 256 characters in length.

        @type password: str
        @param password: The password for this verifier.

        @type bits: int
        @param bits: This values specifies which SRP group parameters
        to use.  It must be one of (1024, 1536, 2048, 3072, 4096, 6144,
        8192).  Larger values are more secure but slower.  2048 is a
        good compromise between safety and speed.

        @rtype: tuple
        @return: A tuple which may be stored in a VerifierDB.
        """
        usernameBytes = bytearray(username, "utf-8")
        passwordBytes = bytearray(password, "utf-8")
        return mathtls.makeVerifier(usernameBytes, passwordBytes, bits)
    makeVerifier = staticmethod(makeVerifier)

########NEW FILE########
__FILENAME__ = x509
# Authors: 
#   Trevor Perrin
#   Google - parsing subject field
#
# See the LICENSE file for legal information regarding use of this file.

"""Class representing an X.509 certificate."""

from .utils.asn1parser import ASN1Parser
from .utils.cryptomath import *
from .utils.keyfactory import _createPublicRSAKey
from .utils.pem import *


class X509(object):
    """This class represents an X.509 certificate.

    @type bytes: L{bytearray} of unsigned bytes
    @ivar bytes: The DER-encoded ASN.1 certificate

    @type publicKey: L{tlslite.utils.rsakey.RSAKey}
    @ivar publicKey: The subject public key from the certificate.

    @type subject: L{bytearray} of unsigned bytes
    @ivar subject: The DER-encoded ASN.1 subject distinguished name.
    """

    def __init__(self):
        self.bytes = bytearray(0)
        self.publicKey = None
        self.subject = None

    def parse(self, s):
        """Parse a PEM-encoded X.509 certificate.

        @type s: str
        @param s: A PEM-encoded X.509 certificate (i.e. a base64-encoded
        certificate wrapped with "-----BEGIN CERTIFICATE-----" and
        "-----END CERTIFICATE-----" tags).
        """

        bytes = dePem(s, "CERTIFICATE")
        self.parseBinary(bytes)
        return self

    def parseBinary(self, bytes):
        """Parse a DER-encoded X.509 certificate.

        @type bytes: str or L{bytearray} of unsigned bytes
        @param bytes: A DER-encoded X.509 certificate.
        """

        self.bytes = bytearray(bytes)
        p = ASN1Parser(bytes)

        #Get the tbsCertificate
        tbsCertificateP = p.getChild(0)

        #Is the optional version field present?
        #This determines which index the key is at.
        if tbsCertificateP.value[0]==0xA0:
            subjectPublicKeyInfoIndex = 6
        else:
            subjectPublicKeyInfoIndex = 5

        #Get the subject
        self.subject = tbsCertificateP.getChildBytes(\
                           subjectPublicKeyInfoIndex - 1)

        #Get the subjectPublicKeyInfo
        subjectPublicKeyInfoP = tbsCertificateP.getChild(\
                                    subjectPublicKeyInfoIndex)

        #Get the algorithm
        algorithmP = subjectPublicKeyInfoP.getChild(0)
        rsaOID = algorithmP.value
        if list(rsaOID) != [6, 9, 42, 134, 72, 134, 247, 13, 1, 1, 1, 5, 0]:
            raise SyntaxError("Unrecognized AlgorithmIdentifier")

        #Get the subjectPublicKey
        subjectPublicKeyP = subjectPublicKeyInfoP.getChild(1)

        #Adjust for BIT STRING encapsulation
        if (subjectPublicKeyP.value[0] !=0):
            raise SyntaxError()
        subjectPublicKeyP = ASN1Parser(subjectPublicKeyP.value[1:])

        #Get the modulus and exponent
        modulusP = subjectPublicKeyP.getChild(0)
        publicExponentP = subjectPublicKeyP.getChild(1)

        #Decode them into numbers
        n = bytesToNumber(modulusP.value)
        e = bytesToNumber(publicExponentP.value)

        #Create a public key instance
        self.publicKey = _createPublicRSAKey(n, e)

    def getFingerprint(self):
        """Get the hex-encoded fingerprint of this certificate.

        @rtype: str
        @return: A hex-encoded fingerprint.
        """
        return b2a_hex(SHA1(self.bytes))

    def writeBytes(self):
        return self.bytes



########NEW FILE########
__FILENAME__ = x509certchain
# Author: Trevor Perrin
# See the LICENSE file for legal information regarding use of this file.

"""Class representing an X.509 certificate chain."""

from .utils import cryptomath
from .utils.tackwrapper import *
from .utils.pem import *
from .x509 import X509

class X509CertChain(object):
    """This class represents a chain of X.509 certificates.

    @type x509List: list
    @ivar x509List: A list of L{tlslite.x509.X509} instances,
    starting with the end-entity certificate and with every
    subsequent certificate certifying the previous.
    """

    def __init__(self, x509List=None):
        """Create a new X509CertChain.

        @type x509List: list
        @param x509List: A list of L{tlslite.x509.X509} instances,
        starting with the end-entity certificate and with every
        subsequent certificate certifying the previous.
        """
        if x509List:
            self.x509List = x509List
        else:
            self.x509List = []

    def parsePemList(self, s):
        """Parse a string containing a sequence of PEM certs.

        Raise a SyntaxError if input is malformed.
        """
        x509List = []
        bList = dePemList(s, "CERTIFICATE")
        for b in bList:
            x509 = X509()
            x509.parseBinary(b)
            x509List.append(x509)
        self.x509List = x509List

    def getNumCerts(self):
        """Get the number of certificates in this chain.

        @rtype: int
        """
        return len(self.x509List)

    def getEndEntityPublicKey(self):
        """Get the public key from the end-entity certificate.

        @rtype: L{tlslite.utils.rsakey.RSAKey}
        """
        if self.getNumCerts() == 0:
            raise AssertionError()
        return self.x509List[0].publicKey

    def getFingerprint(self):
        """Get the hex-encoded fingerprint of the end-entity certificate.

        @rtype: str
        @return: A hex-encoded fingerprint.
        """
        if self.getNumCerts() == 0:
            raise AssertionError()
        return self.x509List[0].getFingerprint()
        
    def checkTack(self, tack):
        if self.x509List:
            tlsCert = TlsCertificate(self.x509List[0].bytes)
            if tlsCert.matches(tack):
                return True
        return False
        
    def getTackExt(self):
        """Get the TACK and/or Break Sigs from a TACK Cert in the chain."""
        tackExt = None
        # Search list in backwards order
        for x509 in self.x509List[::-1]:
            tlsCert = TlsCertificate(x509.bytes)
            if tlsCert.tackExt:
                if tackExt:
                    raise SyntaxError("Multiple TACK Extensions")
                else:
                    tackExt = tlsCert.tackExt
        return tackExt
                

########NEW FILE########
