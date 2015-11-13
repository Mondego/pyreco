__FILENAME__ = CryptoEngine
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os, hmac, hashlib
from MacFailedException import MacFailedException
from Crypto.Cipher import AES
from struct import *

class CryptoEngine:

    def __init__(self, profile, cipherKey, macKey, counter):
        self.profile   = profile
        self.counter   = counter
        self.macKey    = macKey
        self.cipherKey = cipherKey
        self.cipher    = AES.new(self.cipherKey, AES.MODE_ECB)

    def calculateMac(self, port):
        hmacSha = hmac.new(self.macKey, port, hashlib.sha1)
        mac     = hmacSha.digest()
        return mac[:10]

    def verifyMac(self, port, remoteMac):
        localMac = self.calculateMac(port)

        if (localMac != remoteMac):
            raise MacFailedException, "MAC Doesn't Match!"

    def encryptCounter(self, counter):
        counterBytes = pack('!IIII', 0, 0, 0, counter)
        return self.cipher.encrypt(counterBytes)

    def encrypt(self, plaintextData):
        plaintextData += self.calculateMac(plaintextData)
        counterCrypt   = self.encryptCounter(self.counter)
        self.counter   = self.counter + 1
        encrypted      = str()

        for i in range((len(plaintextData))):
            encrypted += chr(ord(plaintextData[i]) ^ ord(counterCrypt[i]))

        self.profile.setCounter(self.counter)
        self.profile.storeCounter()

        return encrypted

    def decrypt(self, encryptedData, windowSize):
        for x in range(windowSize):
            try:
                counterCrypt = self.encryptCounter(self.counter + x)
                decrypted    = str()
                
                for i in range((len(encryptedData))):
                    decrypted += chr(ord(encryptedData[i]) ^ ord(counterCrypt[i]))
                    
                port = decrypted[:2]
                mac  = decrypted[2:]
                    
                self.verifyMac(port, mac)
                self.counter += x + 1

                self.profile.setCounter(self.counter)
                self.profile.storeCounter()

                return int(unpack("!H", port)[0])

            except MacFailedException:
                pass

        raise MacFailedException, "Ciphertext failed to decrypt in range..."

########NEW FILE########
__FILENAME__ = DaemonConfiguration
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os
import ConfigParser

class DaemonConfiguration:

    def __init__(self, file):
        try:
            parser = ConfigParser.SafeConfigParser({'delay': '15', 'error_window': '20'})
            parser.read(file)

            self.delay  = int(parser.get('main', 'delay'))
            self.window = int(parser.get('main', 'error_window'))
        except ConfigParser.NoSectionError:
            print "knockknock-daemon: config file not found, assuming defaults."
            self.delay  = 15
            self.window = 20

    def getDelay(self):
        return self.delay

    def getWindow(self):
        return self.window

########NEW FILE########
__FILENAME__ = daemonize
"""Disk And Execution MONitor (Daemon)

Configurable daemon behaviors:

   1.) The current working directory set to the "/" directory.
   2.) The current file creation mode mask set to 0.
   3.) Close all open files (1024). 
   4.) Redirect standard I/O streams to "/dev/null".

A failed call to fork() now raises an exception.

References:
   1) Advanced Programming in the Unix Environment: W. Richard Stevens
   2) Unix Programming Frequently Asked Questions:
         http://www.erlenstar.demon.co.uk/unix/faq_toc.html
"""

__author__    = "Chad J. Schroeder"
__copyright__ = "Copyright (C) 2005 Chad J. Schroeder"
__revision__  = "$Id$"
__version__   = "0.2"

import os               # Miscellaneous OS interfaces.
import sys              # System-specific parameters and functions.

UMASK   = 0
WORKDIR = "/"
MAXFD   = 1024

# The standard I/O file descriptors are redirected to /dev/null by default.
if (hasattr(os, "devnull")):
   REDIRECT_TO = os.devnull
else:
   REDIRECT_TO = "/dev/null"

def createDaemon():
   """Detach a process from the controlling terminal and run it in the
   background as a daemon.
   """

   try:
      pid = os.fork()
   except OSError, e:
      raise Exception, "%s [%d]" % (e.strerror, e.errno)

   if (pid == 0):	# The first child.
      os.setsid()

      try:
         pid = os.fork()	# Fork a second child.
      except OSError, e:
         raise Exception, "%s [%d]" % (e.strerror, e.errno)

      if (pid == 0):	# The second child.
         os.chdir(WORKDIR)
         os.umask(UMASK)
      else:
         os._exit(0)	# Exit parent (the first child) of the second child.
   else:
      os._exit(0)	# Exit parent of the first child.

#   import resource		# Resource usage information.
#   maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
#   if (maxfd == resource.RLIM_INFINITY):
#      maxfd = MAXFD
  
   # Iterate through and close all file descriptors.
#   for fd in range(0, maxfd):
#      try:
#         os.close(fd)
#      except OSError:	# ERROR, fd wasn't open to begin with (ignored)
#         pass

   os.open(REDIRECT_TO, os.O_RDWR)	# standard input (0)
   os.dup2(0, 1)			# standard output (1)
   os.dup2(0, 2)			# standard error (2)

   return(0)

########NEW FILE########
__FILENAME__ = KnockWatcher
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import syslog

from LogEntry import LogEntry
from MacFailedException import MacFailedException

class KnockWatcher:

    def __init__(self, config, logFile, profiles, portOpener):
        self.config     = config
        self.logFile    = logFile
        self.profiles   = profiles
        self.portOpener = portOpener

    def tailAndProcess(self):
        for line in self.logFile.tail():
            try:
                logEntry = LogEntry(line)
                profile  = self.profiles.getProfileForPort(logEntry.getDestinationPort())

                if (profile != None):
                    try:
                        ciphertext = logEntry.getEncryptedData()
                        port       = profile.decrypt(ciphertext, self.config.getWindow())
                        sourceIP   = logEntry.getSourceIP()
                    
                        self.portOpener.open(sourceIP, port)
                        syslog.syslog("Received authenticated port-knock for port " + str(port) + " from " + sourceIP)
                    except MacFailedException:
                        pass
            except:
#                print "Unexpected error:", sys.exc_info()
                syslog.syslog("knocknock skipping unrecognized line.")

########NEW FILE########
__FILENAME__ = LogEntry
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import string
from struct import *


class LogEntry:

    def __init__(self, line):
        self.buildTokenMap(line)


    def buildTokenMap(self, line):
        self.tokenMap = dict()

        for token in line.split():
            index = token.find("=");            
            if index != -1:
                exploded = token.split('=')
                self.tokenMap[exploded[0]] = exploded[1]

    def getDestinationPort(self):
        return int(self.tokenMap['DPT'])

    def getEncryptedData(self):
        return pack('!HIIH', int(self.tokenMap['ID']), int(self.tokenMap['SEQ']), int(self.tokenMap['ACK']), int(self.tokenMap['WINDOW']))
                    
    def getSourceIP(self):
        return self.tokenMap['SRC']

########NEW FILE########
__FILENAME__ = LogFile
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import string, sys, os, syslog, time

class LogFile:

    def __init__(self, file):
        self.file = file        

    def checkForFileRotate(self, fd):
        freshFile = open(self.file)
            
        if (os.path.sameopenfile(freshFile.fileno(), fd.fileno())):
            freshFile.close()
            return fd
        else:
            fd.close()
            return freshFile

    def tail(self):
        fd = open(self.file)
        fd.seek(0, os.SEEK_END)
        
        while True:
            fd    = self.checkForFileRotate(fd)
            where = fd.tell()
            line  = fd.readline()

            if not line:
                time.sleep(.25)
                fd.seek(where)
            else:
                yield line

########NEW FILE########
__FILENAME__ = MacFailedException
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

class MacFailedException(Exception):
    pass

########NEW FILE########
__FILENAME__ = PortOpener
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os, syslog, time
import subprocess

from RuleTimer import RuleTimer

class PortOpener:

    def __init__(self, stream, openDuration):
        self.stream       = stream
        self.openDuration = openDuration

    def waitForRequests(self):
        while True:
            sourceIP    = self.stream.readline().rstrip("\n")
            port        = self.stream.readline().rstrip("\n")

            if sourceIP == "" or port == "":
                syslog.syslog("knockknock.PortOpener: Parent process is closed.  Terminating.")
                os._exit(4)                    

            description = 'INPUT -m limit --limit 1/minute --limit-burst 1 -m state --state NEW -p tcp -s ' + sourceIP + ' --dport ' + str(port) + ' -j ACCEPT'
            command     = 'iptables -I ' + description
            command     = command.split()            

            subprocess.call(command, shell=False)

            RuleTimer(self.openDuration, description).start()

    def open(self, sourceIP, port):
        try:
            self.stream.write(sourceIP + "\n")
            self.stream.write(str(port) + "\n")
            self.stream.flush()
        except:
            syslog.syslog("knockknock:  Error, PortOpener process has died.  Terminating.")
            os._exit(4)

########NEW FILE########
__FILENAME__ = Profile
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os, string
import ConfigParser
import binascii
import stat
from struct import *

from CryptoEngine import CryptoEngine

class Profile:

    def __init__(self, directory, cipherKey=None, macKey=None, counter=None, knockPort=None):
        self.counterFile  = None
        self.directory    = directory
        self.name         = directory.rstrip('/').split('/')[-1]

        if (cipherKey == None):
            self.deserialize()
        else:
            self.cipherKey = cipherKey
            self.macKey    = macKey
            self.counter   = counter
            self.knockPort = knockPort

        self.cryptoEngine = CryptoEngine(self, self.cipherKey, self.macKey, self.counter)

    def deserialize(self):
        self.cipherKey    = self.loadCipherKey()
        self.macKey       = self.loadMacKey()
        self.counter      = self.loadCounter()
        self.knockPort    = self.loadConfig()

    def serialize(self):
        self.storeCipherKey()
        self.storeMacKey()
        self.storeCounter()
        self.storeConfig()

    # Getters And Setters

    def getIPAddrs(self):
        return self.ipAddressList

    def setIPAddrs(self, ipAddressList):
        self.ipAddressList = ipAddressList        

    def getName(self):
        return self.name

    def getDirectory(self):
        return self.directory

    def getKnockPort(self):
        return self.knockPort

    def setCounter(self, counter):
        self.counter = counter

    # Encrypt And Decrypt

    def decrypt(self, ciphertext, windowSize):
        return self.cryptoEngine.decrypt(ciphertext, windowSize)

    def encrypt(self, plaintext):
        return self.cryptoEngine.encrypt(plaintext)

    # Serialization Methods

    def loadCipherKey(self):
        return self.loadKey(self.directory + "/cipher.key")

    def loadMacKey(self):
        return self.loadKey(self.directory + "/mac.key")

    def loadCounter(self):
        # Privsep bullshit...
        if (self.counterFile == None):
            self.counterFile = open(self.directory + "/counter", 'r+')

        counter = self.counterFile.readline()
        counter = counter.rstrip("\n")

        return int(counter)

    def loadConfig(self):
        config = ConfigParser.SafeConfigParser()
        config.read(self.directory + "/config")
        
        return config.get('main', 'knock_port')

    def loadKey(self, keyFile):
        file = open(keyFile, 'r')
        key  = binascii.a2b_base64(file.readline())        

        file.close()
        return key

    def storeCipherKey(self):        
        self.storeKey(self.cipherKey, self.directory + "/cipher.key")

    def storeMacKey(self):
        self.storeKey(self.macKey, self.directory + "/mac.key")

    def storeCounter(self):
        # Privsep bullshit...
        if (self.counterFile == None):
            self.counterFile = open(self.directory + '/counter', 'w')
            self.setPermissions(self.directory + '/counter')

        self.counterFile.seek(0)
        self.counterFile.write(str(self.counter) + "\n")
        self.counterFile.flush()

    def storeConfig(self):
        config = ConfigParser.SafeConfigParser()
        config.add_section('main')
        config.set('main', 'knock_port', str(self.knockPort))

        configFile = open(self.directory + "/config", 'w')
        config.write(configFile)
        configFile.close()

        self.setPermissions(self.directory + "/config")

    def storeKey(self, key, path):
        file = open(path, 'w')
        file.write(binascii.b2a_base64(key))
        file.close()

        self.setPermissions(path)

    # Permissions

    def setPermissions(self, path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    # Debug

    def printHex(self, val):
        for c in val:
            print "%#x" % ord(c),
            
        print ""

########NEW FILE########
__FILENAME__ = Profiles
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import os, socket
from Profile import Profile

class Profiles:

    def __init__(self, directory):
        self.profiles = list()

        for item in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, item)):
                self.profiles.append(Profile(os.path.join(directory, item)))

    def getProfileForPort(self, port):
        for profile in self.profiles:
            if (int(profile.getKnockPort()) == int(port)):
                return profile

        return None

    def getProfileForName(self, name):
        for profile in self.profiles:
            if (name == profile.getName()):
                return profile

        return None

    def getProfileForIP(self, ip):
        for profile in self.profiles:
            ips = profile.getIPAddrs()
                        
            if ip in ips:
                return profile

        return None

    def resolveNames(self):
        for profile in self.profiles:
            name                     = profile.getName()
            address, alias, addrlist = socket.gethostbyname_ex(name)
            
            profile.setIPAddrs(addrlist)

    def isEmpty(self):
        return len(self.profiles) == 0

########NEW FILE########
__FILENAME__ = EndpointConnection

import asyncore
import string
import socket

class EndpointConnection(asyncore.dispatcher_with_send):

    def __init__(self, shuttle, host, port):
        asyncore.dispatcher_with_send.__init__(self)
        self.shuttle         = shuttle
        self.buffer          = ""
        self.destination     = (host, port)
        self.closed          = False
        self.connectAttempts = 0

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(self.destination)

    def reconnect(self):
        if self.connectAttempts < 3:
            self.connectAttempts += 1
            self.close()
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect(self.destination)

    def handle_connect(self):
        (localIP, localPort) = self.socket.getsockname()
        self.shuttle.connectSucceeded(localIP, localPort)

    def handle_close(self):
        if not self.closed:
            self.closed = True
            self.shuttle.handle_close()
            self.close()

    def handle_error(self):
        self.reconnect()

    def handle_read(self):
        data = self.recv(4096)
        self.shuttle.receivedData(data)

    def write(self, data):
        if not self.closed:
            self.send(data)

########NEW FILE########
__FILENAME__ = KnockingEndpointConnection

from EndpointConnection import EndpointConnection

import subprocess
import time

from struct import *

class KnockingEndpointConnection(EndpointConnection):

    def __init__(self, shuttle, profile, host, port):
        self.profile = profile
        self.host    = host
        self.port    = port

        self.sendKnock(profile, host, port)
        EndpointConnection.__init__(self, shuttle, host, port)

    def reconnect(self):
        self.sendKnock(self.profile, self.host, self.port)
        EndpointConnection.reconnect(self)

    def sendKnock(self, profile, host, port):
        port       = pack('!H', int(port))
        packetData = profile.encrypt(port)
        knockPort  = profile.getKnockPort()
        
        idField, seqField, ackField, winField = unpack('!HIIH', packetData)

        command = "hping3 -q -S -c 1 -p " + str(knockPort) + " -N " + str(idField) + " -w " + str(winField) + " -M " + str(seqField) + " -L " + str(ackField) + " " + host;
        command = command.split()

        subprocess.call(command, shell=False, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
        time.sleep(0.25)

########NEW FILE########
__FILENAME__ = SocksRequestHandler

import asynchat, asyncore
import socket, string
from struct import *

from EndpointConnection import EndpointConnection
from KnockingEndpointConnection import KnockingEndpointConnection

class SocksRequestHandler(asynchat.async_chat):

    def __init__(self, sock, profiles):
        asynchat.async_chat.__init__(self, sock=sock)

        self.INITIAL_HEADER_LEN = 2
        self.REQUEST_HEADER_LEN = 4

        self.profiles     = profiles
        self.input        = []
        self.state        = 0
        self.endpoint     = None
        self.stateMachine = {
            0: self.processHeaders,
            1: self.processAuthenticationMethod,
            2: self.processRequestHeader,
            3: self.processAddressHeader,
            4: self.processAddressAndPort,
            }

        self.set_terminator(self.INITIAL_HEADER_LEN)

    def sendSuccessResponse(self, localIP, localPort):
        response = "\x05\x00\x00\x01" 
        
        quad = localIP.split(".")
        
        for segment in quad:
            response = response + chr(int(segment))
        
        response = response + pack('!H', int(localPort))

        self.push(response)

    def sendCommandNotSupportedResponse(self):
        response = "\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00"
        self.push(response)

    def sendAddressNotSupportedResponse(self):
        response = "\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00"
        self.push(response)

    def sendAuthenticationResponse(self, method):
        response = "\x05" + chr(method)
        self.push(response)

    def setupEndpoint(self):
        if (self.addressType == 0x01):            
            profile = self.profiles.getProfileForIP(self.address)
        else:
            profile = self.profiles.getProfileForName(self.address)

        if profile == None:
            self.endpoint = EndpointConnection(self, self.address, self.port)
        else:
            self.endpoint = KnockingEndpointConnection(self, profile, self.address, self.port)


    def processAddressAndPort(self):
        self.rawAddressAndPort = self.input

        if (self.addressType == 0x01):
            self.address = str(ord(self.input[0])) + "." + str(ord(self.input[1])) + "." + str(ord(self.input[2])) + "." + str(ord(self.input[3]))
        else:
            self.address = self.input[0:-2]

        self.port = ord(self.input[-2]) * 256 + ord(self.input[-1]) 

        self.set_terminator(None)
        self.setupEndpoint()

    def processAddressHeader(self):
        addressLength = ord(self.input[0]) + 2
        return addressLength

    def processRequestHeader(self):
        command          = ord(self.input[1])
        self.addressType = ord(self.input[3])

        if (command != 0x01):
            self.sendCommandNotSupportedResponse()
            self.handle_close()
            return

        if (self.addressType == 0x01):
            self.state = self.state + 1 # No Address Header
            return 6
        elif (self.addressType == 0x03):
            return 1
        else:
            self.sendAddressNotSupportedResponse()
            self.handle_close()        

    def processAuthenticationMethod(self):
        for method in self.input:
            if (ord(method) == 0):
                self.sendAuthenticationResponse(0x00)
                return self.REQUEST_HEADER_LEN

        self.sendAuthenticationResponse(0xFF)
        self.handle_close()

    def processHeaders(self):
        socksVersion = ord(self.input[0])
        methodCount  = ord(self.input[1])

        if (socksVersion != 5):
            self.handle_close()
            return

        return methodCount


    def handle_close(self):
        if (self.endpoint != None):
            self.endpoint.handle_close()

        asynchat.async_chat.handle_close(self)
        

    # async_chat impl

    def printHex(self, val):
        for c in val:
            print "%#x" % ord(c),
            
        print ""

    def collect_incoming_data(self, data):
        if (self.endpoint != None):
            self.endpoint.write(data)
        else:
            self.input.append(data)

    def found_terminator(self):
        self.input = "".join(self.input)
        terminator = self.stateMachine[self.state]()
        self.input = []
        self.state = self.state + 1
        
        self.set_terminator(terminator)
    
    # Shuttle Methods

    def connectSucceeded(self, localIP, localPort):
        self.sendSuccessResponse(localIP, localPort)
        
    def receivedData(self, data):
        self.push(data)

########NEW FILE########
__FILENAME__ = RuleTimer
# Copyright (c) 2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import subprocess
import time
import threading

class RuleTimer(threading.Thread):

    def __init__(self, openDuration, description):
        self.openDuration = openDuration
        self.description  = description
        threading.Thread.__init__(self)

    def run(self):
        time.sleep(self.openDuration)
        command = 'iptables -D ' + self.description
        command = command.split()

        subprocess.call(command, shell=False)

########NEW FILE########
__FILENAME__ = knockknock-daemon
#!/usr/bin/env python
"""knockknock-daemon implements Moxie Marlinspike's port knocking protocol."""

__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2009 Moxie Marlinspike <moxie@thoughtcrime.org>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

import os, sys, pwd, grp

from knockknock.LogEntry import LogEntry
from knockknock.LogFile import LogFile
from knockknock.Profiles import Profiles
from knockknock.PortOpener import PortOpener
from knockknock.DaemonConfiguration import DaemonConfiguration
from knockknock.KnockWatcher import KnockWatcher

import knockknock.daemonize

def checkPrivileges():
    if (not os.geteuid() == 0):
        print "Sorry, you have to run knockknock-daemon as root."
        sys.exit(3)

def checkConfiguration():
    if (not os.path.isdir('/etc/knockknock.d/')):
        print "/etc/knockknock.d/ does not exist.  You need to setup your profiles first.."
        sys.exit(3)

    if (not os.path.isdir('/etc/knockknock.d/profiles/')):
        print "/etc/knockknock.d/profiles/ does not exist.  You need to setup your profiles first..."
        sys.exit(3)

def dropPrivileges():
    nobody = pwd.getpwnam('nobody')
    adm    = grp.getgrnam('adm')

    os.setgroups([adm.gr_gid])
    os.setgid(adm.gr_gid)
    os.setuid(nobody.pw_uid)

def handleFirewall(input, config):
    portOpener = PortOpener(input, config.getDelay())
    portOpener.waitForRequests()

def handleKnocks(output, profiles, config):
    dropPrivileges()
    
    logFile      = LogFile('/var/log/kern.log')
    portOpener   = PortOpener(output, config.getDelay())
    knockWatcher = KnockWatcher(config, logFile, profiles, portOpener)

    knockWatcher.tailAndProcess()

def main(argv):
    checkPrivileges()
    checkConfiguration()

    profiles   = Profiles('/etc/knockknock.d/profiles/')
    config     = DaemonConfiguration('/etc/knockknock.d/config')

    if (profiles.isEmpty()):
        print 'WARNING: Running knockknock-daemon without any active profiles.'

    knockknock.daemonize.createDaemon()

    input, output = os.pipe()
    pid           = os.fork()

    if pid:
        os.close(input)
        handleKnocks(os.fdopen(output, 'w'), profiles, config)
    else:
        os.close(output)
        handleFirewall(os.fdopen(input, 'r'), config)
                
if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = knockknock-genprofile
#!/usr/bin/env python

__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2009 Moxie Marlinspike <moxie@thoughtcrime.org>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

import os, sys
from knockknock.Profiles import Profiles
from knockknock.Profile  import Profile

DAEMON_DIR   = '/etc/knockknock.d/'
PROFILES_DIR = DAEMON_DIR + 'profiles/'

def usage():
    print "knockknock-genprofile <profileName> <knockPort>"
    sys.exit(3)

def checkProfile(profileName):
    if (os.path.isdir(PROFILES_DIR + profileName)):
        print "Profile already exists.  First rm " + PROFILES_DIR + profileName + "/"
        sys.exit(0)

def checkPortConflict(knockPort):
    if (not os.path.isdir(PROFILES_DIR)):
        return

    profiles        = Profiles(PROFILES_DIR)    
    matchingProfile = profiles.getProfileForPort(knockPort)

    if (matchingProfile != None):
        print "A profile already exists for knock port: " + str(knockPort) + " at this location: " + matchingProfile.getDirectory()

def createDirectory(profileName):
    if not os.path.isdir(DAEMON_DIR):
        os.mkdir(DAEMON_DIR)

    if not os.path.isdir(PROFILES_DIR):
        os.mkdir(PROFILES_DIR)
    
    if not os.path.isdir(PROFILES_DIR + profileName):
        os.mkdir(PROFILES_DIR + profileName)

def main(argv):
    
    if len(argv) != 2:
        usage()

    profileName = argv[0]
    knockPort   = argv[1]
        
    checkProfile(profileName)
    checkPortConflict(knockPort)
    createDirectory(profileName)

    random    = open('/dev/urandom', 'rb')
    cipherKey = random.read(16)
    macKey    = random.read(16)
    counter   = 0

    profile = Profile(PROFILES_DIR + profileName, cipherKey, macKey, counter, knockPort)
    profile.serialize()
    random.close()

    print "Keys successfully generated in " + PROFILES_DIR + profileName

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = knockknock-proxy
#!/usr/bin/env python

__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2009 Moxie Marlinspike <moxie@thoughtcrime.org>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

import os, sys, asyncore, socket

from knockknock.Profiles import Profiles
from knockknock.proxy.SocksRequestHandler import SocksRequestHandler

import knockknock.daemonize

class ProxyServer(asyncore.dispatcher):

    def __init__(self, port, profiles):
        asyncore.dispatcher.__init__(self)
        self.profiles = profiles
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(("127.0.0.1", port))
        self.listen(5)

    def handle_accept(self):
        conn, addr = self.accept()
        SocksRequestHandler(conn, self.profiles)


def usage():
    print "knockknock-proxy <listenPort>"
    sys.exit(3)

def getProfiles():
    homedir  = os.path.expanduser('~')
    profiles = Profiles(homedir + '/.knockknock/')
    profiles.resolveNames()
    
    return profiles

def checkPrivileges():
    if not os.geteuid() == 0:
        print "\nSorry, knockknock-proxy has to be run as root.\n"
        usage()

def checkProfiles():
    homedir = os.path.expanduser('~')

    if not os.path.isdir(homedir + '/.knockknock/'):
        print "Error: you need to setup your profiles in " + homedir + "/.knockknock/"
        sys.exit(2)

def main(argv):
    
    if len(argv) != 1:
        usage()
        
    checkPrivileges()
    checkProfiles()

    profiles = getProfiles()        
    server   = ProxyServer(int(argv[0]), profiles)

    knockknock.daemonize.createDaemon()
    
    asyncore.loop(use_poll=True)

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = knockknock
#!/usr/bin/env python
__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2009 Moxie Marlinspike <moxie@thoughtcrime.org>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

"""

import time, os, sys
import getopt
import subprocess

from struct import *
from knockknock.Profile import Profile

def usage():
    print "Usage: knockknock.py -p <portToOpen> <host>"
    sys.exit(2)
    
def parseArguments(argv):
    try:
        port       = 0
        host       = ""
        opts, args = getopt.getopt(argv, "h:p:")
        
        for opt, arg in opts:
            if opt in ("-p"):
                port = arg
            else:
                usage()
                
        if len(args) != 1:
            usage()
        else:
            host = args[0]

    except getopt.GetoptError:           
        usage()                          

    if port == 0 or host == "":
        usage()

    return (port, host)

def getProfile(host):
    homedir = os.path.expanduser('~')
    
    if not os.path.isdir(homedir + '/.knockknock/'):
        print "Error: you need to setup your profiles in " + homedir + '/.knockknock/'
        sys.exit(2)

    if not os.path.isdir(homedir + '/.knockknock/' + host):
        print 'Error: profile for host ' + host + ' not found at ' + homedir + '/.knockknock/' + host
        sys.exit(2)

    return Profile(homedir + '/.knockknock/' + host)

def verifyPermissions():
    if os.getuid() != 0:
        print 'Sorry, you must be root to run this.'
        sys.exit(2)    

def existsInPath(command):
    def isExe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
        exeFile = os.path.join(path, command)
        if isExe(exeFile):
            return exeFile

    return None

def main(argv):
    (port, host) = parseArguments(argv)
    verifyPermissions()
    
    profile      = getProfile(host)
    port         = pack('!H', int(port))
    packetData   = profile.encrypt(port)
    knockPort    = profile.getKnockPort()
    
    (idField, seqField, ackField, winField) = unpack('!HIIH', packetData)

    hping = existsInPath("hping3")

    if hping is None:
        print "Error, you must install hping3 first."
        sys.exit(2)

    command = [hping, "-S", "-c", "1",
               "-p", str(knockPort),
               "-N", str(idField),
               "-w", str(winField),
               "-M", str(seqField),
               "-L", str(ackField),
               host]
    
    try:
        subprocess.call(command, shell=False, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
        print 'Knock sent.'

    except OSError:
        print "Error: Do you have hping3 installed?"
        sys.exit(3)

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
