__FILENAME__ = ATVSettings
#!/usr/bin/env python

import sys
from os import sep
import ConfigParser
import fnmatch

from Debug import *  # dprint()



options = { \
    'libraryview'       :('List', 'Grid', 'Bookcase'), \
    'movieview'         :('Grid', 'List', 'Detailed List'), \
    'homevideoview'     :('Grid', 'List', 'Detailed List'), \
    'actorview'         :('Movies', 'Portrait'), \
    'showview'          :('List', 'Detailed List', 'Grid', 'Bookcase'), \
    'flattenseason'     :('False', 'True'), \
    'seasonview'        :('List', 'Coverflow'), \
    'channelview'       :('List', 'Grid', 'Bookcase'), \
    'durationformat'    :('Hours/Minutes', 'Minutes'), \
    'showtitles_movies'         :('Highlighted Only', 'Show All'), \
    'showtitles_tvshows'        :('Highlighted Only', 'Show All'), \
    'showtitles_homevideos'     :('Highlighted Only', 'Show All'), \
    'showtitles_channels'       :('Highlighted Only', 'Show All'), \
    'movies_navbar_unwatched'   :('checked', 'unchecked'), \
    'movies_navbar_byfolder'    :('checked', 'unchecked'), \
    'movies_navbar_collections' :('checked', 'unchecked'), \
    'movies_navbar_genres'      :('checked', 'unchecked'), \
    'movies_navbar_decades'     :('checked', 'unchecked'), \
    'movies_navbar_directors'   :('checked', 'unchecked'), \
    'movies_navbar_actors'      :('checked', 'unchecked'), \
    'movies_navbar_more'        :('checked', 'unchecked'), \
    'homevideos_navbar_unwatched'   :('checked', 'unchecked'), \
    'homevideos_navbar_byfolder'    :('checked', 'unchecked'), \
    'homevideos_navbar_collections' :('checked', 'unchecked'), \
    'homevideos_navbar_genres'      :('checked', 'unchecked'), \
    'tv_navbar_unwatched'       :('checked', 'unchecked'), \
    'tv_navbar_genres'          :('checked', 'unchecked'), \
    'tv_navbar_more'            :('checked', 'unchecked'), \
    'transcodequality'  :('1080p 40.0Mbps', \
                          '480p 2.0Mbps', \
                          '720p 3.0Mbps', '720p 4.0Mbps', \
                          '1080p 8.0Mbps', '1080p 10.0Mbps', '1080p 12.0Mbps', '1080p 20.0Mbps'), \
    'transcoderaction'  :('Auto', 'DirectPlay', 'Transcode'), \
    'remotebitrate'     :('720p 3.0Mbps', '720p 4.0Mbps', \
                          '1080p 8.0Mbps', '1080p 10.0Mbps', '1080p 12.0Mbps', '1080p 20.0Mbps', '1080p 40.0Mbps', \
                          '480p 2.0Mbps'), \
    'phototranscoderaction'     :('Auto', 'Transcode'), \
    'subtitlerenderer'  :('Auto', 'iOS, PMS', 'PMS'), \
    'subtitlesize'      :('100', '125', '150', '50', '75'), \
    'audioboost'        :('100', '175', '225', '300'), \
    'showunwatched'     :('True', 'False'), \
    'showsynopsis'      :('Hide', 'Show'), \
    'showplayerclock'   :('True', 'False'), \
    'overscanadjust'    :('0', '1', '2', '3', '-3', '-2', '-1'), \
    'clockposition'     :('Center', 'Right', 'Left'), \
    'showendtime'       :('True', 'False'), \
    'timeformat'        :('24 Hour', '12 Hour'), \
    'myplex_user'       :('', ), \
    'myplex_auth'       :('', ), \
    }



class CATVSettings():
    def __init__(self):
        dprint(__name__, 1, "init class CATVSettings")
        self.cfg = None
        self.loadSettings()
    
    
    
    # load/save config
    def loadSettings(self):
        dprint(__name__, 1, "load settings")
        # options -> default
        dflt = {}
        for opt in options:
            dflt[opt] = options[opt][0]
        
        # load settings
        self.cfg = ConfigParser.SafeConfigParser(dflt)
        self.cfg.read(self.getSettingsFile())
    
    def saveSettings(self):
        dprint(__name__, 1, "save settings")
        f = open(self.getSettingsFile(), 'wb')
        self.cfg.write(f)
        f.close()
    
    def getSettingsFile(self):
        return sys.path[0] + sep + "ATVSettings.cfg"
    
    def checkSection(self, UDID):
        # check for existing UDID section
        sections = self.cfg.sections()
        if not UDID in sections:
            self.cfg.add_section(UDID)
            dprint(__name__, 0, "add section {0}", UDID)
    
    
    
    # access/modify AppleTV options
    def getSetting(self, UDID, option):
        self.checkSection(UDID)
        dprint(__name__, 1, "getsetting {0}", self.cfg.get(UDID, option))
        return self.cfg.get(UDID, option)
    
    def setSetting(self, UDID, option, val):
        self.checkSection(UDID)
        self.cfg.set(UDID, option, val)
    
    def checkSetting(self, UDID, option):
        self.checkSection(UDID)
        val = self.cfg.get(UDID, option)
        opts = options[option]
        
        # check val in list
        found = False
        for opt in opts:
            if fnmatch.fnmatch(val, opt):
                found = True
        
        # if not found, correct to default
        if not found:
            self.cfg.set(UDID, option, opts[0])
            dprint(__name__, 1, "checksetting: default {0} to {1}", option, opts[0])
    
    def toggleSetting(self, UDID, option):
        self.checkSection(UDID)
        cur = self.cfg.get(UDID, option)
        opts = options[option]
    
        # find current in list
        i=0
        for i,opt in enumerate(opts):
            if opt==cur:
                break
    
        # get next option (circle to first)
        i=i+1
        if i>=len(opts):
            i=0
    
        # set
        self.cfg.set(UDID, option, opts[i])
    
    def setOptions(self, option, opts):
        global options
        if option in options:
            options[option] = opts
            dprint(__name__, 1, 'setOption: update {0} to {1}', option, opts)



if __name__=="__main__":
    ATVSettings = CATVSettings()
    
    UDID = '007'
    ATVSettings.checkSection(UDID)
    
    option = 'transcodequality'
    print ATVSettings.getSetting(UDID, option)
    
    print "setSetting"
    ATVSettings.setSetting(UDID, option, 'True')  # error - pick default
    print ATVSettings.getSetting(UDID, option)
    ATVSettings.setSetting(UDID, option, '9')
    print ATVSettings.getSetting(UDID, option)
    
    print "toggleSetting"
    ATVSettings.toggleSetting(UDID, option)
    print ATVSettings.getSetting(UDID, option)
    ATVSettings.toggleSetting(UDID, option)
    print ATVSettings.getSetting(UDID, option)
    ATVSettings.toggleSetting(UDID, option)
    print ATVSettings.getSetting(UDID, option)
    
    del ATVSettings

########NEW FILE########
__FILENAME__ = Debug
#!/usr/bin/env python

"""
Trying to channel debug output

debug levels (examples):
0 - non-repeating output (starting up, shutting down), error messages
1 - function return values
2 - lower debug data, function input values, intermediate info...
"""

dlevels = { "PlexConnect": 0, \
            "PlexAPI"    : 0, \
            "DNSServer"  : 1, \
            "WebServer"  : 1, \
            "XMLConverter" : 0, \
            "Settings"   : 0, \
            "ATVSettings": 0, \
            "Localize"   : 0, \
            "ATVLogger"  : 0, \
          }



import time

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree



g_logfile = ''
g_loglevel = 0

def dinit(src, param, newlog=False):    
    if 'LogFile' in param:
        global g_logfile
        g_logfile = param['LogFile']
        
    if 'LogLevel' in param:
        global g_loglevel
        g_loglevel = { "Normal": 0, "High": 2, "Off": -1 }.get(param['LogLevel'], 0)
    
    if not g_loglevel==-1 and not g_logfile=='' and newlog:
        f = open(g_logfile, 'w')
        f.close()
        
    dprint(src, 0, "started: {0}", time.strftime("%H:%M:%S"))



def dprint(src, dlevel, *args):
    logToTerminal = not (src in dlevels) or dlevel <= dlevels[src]
    logToFile = not g_loglevel==-1 and not g_logfile=='' and dlevel <= g_loglevel
    
    if logToTerminal or logToFile:
        asc_args = list(args)
        
        for i,arg in enumerate(asc_args):
            if isinstance(asc_args[i], str):
                asc_args[i] = asc_args[i].decode('utf-8', 'replace')  # convert as utf-8 just in case
            if isinstance(asc_args[i], unicode):
                asc_args[i] = asc_args[i].encode('ascii', 'replace')  # back to ascii
        
        # print to file (if filename defined)
        if logToFile:
            f = open(g_logfile, 'a')
            f.write(time.strftime("%H:%M:%S "))
            if len(asc_args)==0:
                f.write(src+":\n")
            elif len(asc_args)==1:
                f.write(src+": "+asc_args[0]+"\n")
            else:
                f.write(src+": "+asc_args[0].format(*asc_args[1:])+"\n")
            f.close()
        
        # print to terminal window
        if logToTerminal:
            print(time.strftime("%H:%M:%S")),
            if len(asc_args)==0:
                print src+":"
            elif len(asc_args)==1:
                print src+": "+asc_args[0]
            else:
                print src+": "+asc_args[0].format(*asc_args[1:])



"""
# XML in-place prettyprint formatter
# Source: http://stackoverflow.com/questions/749796/pretty-printing-xml-in-python
"""
def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def prettyXML(XML):
    if g_loglevel>0:
        indent(XML.getroot())
    return(etree.tostring(XML.getroot()))



if __name__=="__main__":
    dinit('Debug', {'LogFile':'Debug.log'}, True)  # True -> new file
    dinit('unknown', {'Logfile':'Debug.log'})  # False/Dflt -> append to file
    
    dprint('unknown', 0, "debugging {0}", __name__)
    dprint('unknown', 1, "level 1")
    
    dprint('PlexConnect', 0, "debugging {0}", 'PlexConnect')
    dprint('PlexConnect', 1, "level")
########NEW FILE########
__FILENAME__ = DNSServer
#!/usr/bin/env python

"""
Source:
http://code.google.com/p/minidns/source/browse/minidns
"""

"""
Header
  7  6  5  4  3  2  1  0  7  6  5  4  3  2  1  0
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      ID                       |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|QR|   Opcode  |AA|TC|RD|RA|   Z    |   RCODE   |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    QDCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    ANCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    NSCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    ARCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

Query
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                                               |
/                     QNAME                     /
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     QTYPE                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     QCLASS                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

ResourceRecord
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                                               |
/                      NAME                     /
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      TYPE                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     CLASS                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      TTL                      |
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                   RDLENGTH                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--|
|                                               |
/                     RDATA                     /
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

Source: http://doc-tcpip.org/Dns/named.dns.message.html
"""

"""
prevent aTV update
Source: http://forum.xbmc.org/showthread.php?tid=93604

loopback to 127.0.0.1...
  mesu.apple.com
  appldnld.apple.com
  appldnld.apple.com.edgesuite.net
"""


import sys
import socket
import struct
from multiprocessing import Pipe  # inter process communication
import signal

import Settings
from Debug import *  # dprint()



"""
 Hostname/DNS conversion
 Hostname: 'Hello.World'
 DNSdata:  '<len(Hello)>Hello<len(World)>World<NULL>
"""
def HostToDNS(Host):
    DNSdata = '.'+Host+'\0'  # python 2.6: bytearray()
    i=0
    while i<len(DNSdata)-1:
        next = DNSdata.find('.',i+1)
        if next==-1:
            next = len(DNSdata)-1
        DNSdata = DNSdata[:i] + chr(next-i-1) + DNSdata[i+1:]  # python 2.6: DNSdata[i] = next-i-1
        i = next
    
    return DNSdata

def DNSToHost(DNSdata, i, followlink=True):
    Host = ''
    while DNSdata[i]!='\0':
        nlen = ord(DNSdata[i])
        if nlen & 0xC0:
            if followlink:
                Host = Host + DNSToHost(DNSdata, ((ord(DNSdata[i]) & 0x3F)<<8) + ord(DNSdata[i+1]) , True)+'.'
            break
        else:
            Host = Host + DNSdata[i+1:i+nlen+1]+'.'
            i+=nlen+1
    Host = Host[:-1]
    return Host



def printDNSdata(paket):
    # HEADER
    print "ID {0:04x}".format((ord(paket[0])<<8)+ord(paket[1]))
    print "flags {0:02x} {1:02x}".format(ord(paket[2]), ord(paket[3]))
    print "OpCode "+str((ord(paket[2])>>3)&0x0F)
    print "RCode "+str((ord(paket[3])>>0)&0x0F)
    qdcount = (ord(paket[4])<<8)+ord(paket[5])
    ancount = (ord(paket[6])<<8)+ord(paket[7])
    nscount = (ord(paket[8])<<8)+ord(paket[9])
    arcount = (ord(paket[10])<<8)+ord(paket[11])
    print "Count - QD, AN, NS, AR:", qdcount, ancount, nscount, arcount
    adr = 12
    
    # QDCOUNT (query)
    for i in range(qdcount):
        print "QUERY"
        host = DNSToHost(paket, adr)
        
        """
        for j in range(len(host)+2+4):
            print ord(paket[adr+j]),
        print
        """
        
        adr = adr + len(host) + 2
        print host
        print "type "+str((ord(paket[adr+0])<<8)+ord(paket[adr+1]))
        print "class "+str((ord(paket[adr+2])<<8)+ord(paket[adr+3]))
        adr = adr + 4
    
    # ANCOUNT (resource record)
    for i in range(ancount):
        print "ANSWER"
        print ord(paket[adr])
        if ord(paket[adr]) & 0xC0:
            print"link"
            adr = adr + 2
        else:
            host = DNSToHost(paket, adr)
            adr = adr + len(host) + 2
        print host
        _type = (ord(paket[adr+0])<<8)+ord(paket[adr+1])
        _class = (ord(paket[adr+2])<<8)+ord(paket[adr+3])
        print "type, class: ", _type, _class
        adr = adr + 4
        print "ttl"
        adr = adr + 4
        rdlength = (ord(paket[adr+0])<<8)+ord(paket[adr+1])
        print "rdlength", rdlength
        adr = adr + 2
        if _type==1:
            print "IP:",
            for j in range(rdlength):
                print ord(paket[adr+j]),
            print
        elif _type==5:
            print "redirect:", DNSToHost(paket, adr)
        else:
            print "type unsupported:",
            for j in range(rdlength):
                print ord(paket[adr+j]),
            print
        adr = adr + rdlength

def printDNSdata_raw(DNSdata):
    # hex code
    for i in range(len(DNSdata)):
        if i % 16==0:
            print
        print "{0:02x}".format(ord(DNSdata[i])),
    print
    
    # printable characters
    for i in range(len(DNSdata)):
        if i % 16==0:
            print
        if (ord(DNSdata[i])>32) & (ord(DNSdata[i])<128):
            print DNSdata[i],
        else:
            print ".",
    print



def parseDNSdata(paket):
    
    def getWord(DNSdata, addr):
        return (ord(DNSdata[addr])<<8)+ord(DNSdata[addr+1])
    
    DNSstruct = {}
    adr = 0
    
    # header
    DNSstruct['head'] = { \
                    'id': getWord(paket, adr+0), \
                    'flags': getWord(paket, adr+2), \
                    'qdcnt': getWord(paket, adr+4), \
                    'ancnt': getWord(paket, adr+6), \
                    'nscnt': getWord(paket, adr+8), \
                    'arcnt': getWord(paket, adr+10) }
    adr = adr + 12
    
    # query
    DNSstruct['query'] = []
    for i in range(DNSstruct['head']['qdcnt']):
        DNSstruct['query'].append({})
        host_nolink = DNSToHost(paket, adr, followlink=False)
        host_link = DNSToHost(paket, adr, followlink=True)
        DNSstruct['query'][i]['host'] = host_link
        adr = adr + len(host_nolink)+2
        DNSstruct['query'][i]['type'] = getWord(paket, adr+0)
        DNSstruct['query'][i]['class'] = getWord(paket, adr+2)
        adr = adr + 4
    
    # resource records
    DNSstruct['resrc'] = []
    for i in range(DNSstruct['head']['ancnt'] + DNSstruct['head']['nscnt'] + DNSstruct['head']['arcnt']):
        DNSstruct['resrc'].append({})
        host_nolink = DNSToHost(paket, adr, followlink=False)
        host_link = DNSToHost(paket, adr, followlink=True)
        DNSstruct['resrc'][i]['host'] = host_link
        adr = adr + len(host_nolink)+2
        DNSstruct['resrc'][i]['type'] = getWord(paket, adr+0)
        DNSstruct['resrc'][i]['class'] = getWord(paket, adr+2)
        DNSstruct['resrc'][i]['ttl'] = (getWord(paket, adr+4)<<16)+getWord(paket, adr+6)
        DNSstruct['resrc'][i]['rdlen'] = getWord(paket, adr+8)
        adr = adr + 10
        DNSstruct['resrc'][i]['rdata'] = []
        if DNSstruct['resrc'][i]['type']==5:  # 5=redirect, evaluate name
            host = DNSToHost(paket, adr, followlink=True)
            DNSstruct['resrc'][i]['rdata'] = host
            adr = adr + DNSstruct['resrc'][i]['rdlen']
            DNSstruct['resrc'][i]['rdlen'] = len(host)
        else:  # 1=IP, ...
            for j in range(DNSstruct['resrc'][i]['rdlen']):
                DNSstruct['resrc'][i]['rdata'].append( paket[adr+j] )
            adr = adr + DNSstruct['resrc'][i]['rdlen']
    
    return DNSstruct

def encodeDNSstruct(DNSstruct):
    
    def appendWord(DNSdata, val):
        DNSdata.append((val>>8) & 0xFF)
        DNSdata.append( val     & 0xFF)
    
    DNS = bytearray()
    
    # header
    appendWord(DNS, DNSstruct['head']['id'])
    appendWord(DNS, DNSstruct['head']['flags'])
    appendWord(DNS, DNSstruct['head']['qdcnt'])
    appendWord(DNS, DNSstruct['head']['ancnt'])
    appendWord(DNS, DNSstruct['head']['nscnt'])
    appendWord(DNS, DNSstruct['head']['arcnt'])
    
    # query
    for i in range(DNSstruct['head']['qdcnt']):
        host = HostToDNS(DNSstruct['query'][i]['host'])
        DNS.extend(bytearray(host))
        appendWord(DNS, DNSstruct['query'][i]['type'])
        appendWord(DNS, DNSstruct['query'][i]['class'])
        
    # resource records
    for i in range(DNSstruct['head']['ancnt'] + DNSstruct['head']['nscnt'] + DNSstruct['head']['arcnt']):
        host = HostToDNS(DNSstruct['resrc'][i]['host'])  # no 'packing'/link - todo?
        DNS.extend(bytearray(host))
        appendWord(DNS, DNSstruct['resrc'][i]['type'])
        appendWord(DNS, DNSstruct['resrc'][i]['class'])
        appendWord(DNS, (DNSstruct['resrc'][i]['ttl']>>16) & 0xFFFF)
        appendWord(DNS, (DNSstruct['resrc'][i]['ttl']    ) & 0xFFFF)
        appendWord(DNS, DNSstruct['resrc'][i]['rdlen'])
        
        if DNSstruct['resrc'][i]['type']==5:  # 5=redirect, hostname
            host = HostToDNS(DNSstruct['resrc'][i]['rdata'])
            DNS.extend(bytearray(host))
        else:
            DNS.extend(DNSstruct['resrc'][i]['rdata'])
    
    return DNS

def printDNSstruct(DNSstruct):
    for i in range(DNSstruct['head']['qdcnt']):
        print "query:", DNSstruct['query'][i]['host']
    
    for i in range(DNSstruct['head']['ancnt'] + DNSstruct['head']['nscnt'] + DNSstruct['head']['arcnt']):
        print "resrc:",
        print DNSstruct['resrc'][i]['host']
        if DNSstruct['resrc'][i]['type']==1:
            print "->IP:",
            for j in range(DNSstruct['resrc'][i]['rdlen']):
                print ord(DNSstruct['resrc'][i]['rdata'][j]),
            print
        elif DNSstruct['resrc'][i]['type']==5:
            print "->alias:", DNSstruct['resrc'][i]['rdata']
        else:
            print "->unknown type"



def Run(cmdPipe, param):
    if not __name__ == '__main__':
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    dinit(__name__, param)  # init logging, DNSServer process
    
    cfg_IP_self = param['IP_self']
    cfg_Port_DNSServer = param['CSettings'].getSetting('port_dnsserver')
    cfg_IP_DNSMaster = param['CSettings'].getSetting('ip_dnsmaster')
    
    try:
        DNS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        DNS.settimeout(5.0)
        DNS.bind((cfg_IP_self, int(cfg_Port_DNSServer)))
    except Exception, e:
        dprint(__name__, 0, "Failed to create socket on UDP port {0}: {1}", cfg_Port_DNSServer, e)
        sys.exit(1)
    
    try:
        DNS_forward = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        DNS_forward.settimeout(5.0)
    except Exception, e:
        dprint(__name__, 0, "Failed to create socket on UDP port 49152: {0}", e)
        sys.exit(1)
    
    intercept = [param['HostToIntercept']]
    restrain = []
    if param['CSettings'].getSetting('prevent_atv_update')=='True':
        restrain = ['mesu.apple.com', 'appldnld.apple.com', 'appldnld.apple.com.edgesuite.net']
    
    dprint(__name__, 0, "***")
    dprint(__name__, 0, "DNSServer: Serving DNS on {0} port {1}.", cfg_IP_self, cfg_Port_DNSServer)
    dprint(__name__, 1, "intercept: {0} => {1}", intercept, cfg_IP_self)
    dprint(__name__, 1, "restrain: {0} => 127.0.0.1", restrain)
    dprint(__name__, 1, "forward other to higher level DNS: "+cfg_IP_DNSMaster)
    dprint(__name__, 0, "***")
    
    try:
        while True:
            # check command
            if cmdPipe.poll():
                cmd = cmdPipe.recv()
                if cmd=='shutdown':
                    break
            
            # do your work (with timeout)
            try:
                data, addr = DNS.recvfrom(1024)
                dprint(__name__, 1, "DNS request received!")
                dprint(__name__, 1, "Source: "+str(addr))
                
                #print "incoming:"
                #printDNSdata(data)
                
                # analyse DNS request
                # todo: how about multi-query messages?
                opcode = (ord(data[2]) >> 3) & 0x0F # Opcode bits (query=0, inversequery=1, status=2)
                if opcode == 0:                     # Standard query
                    domain = DNSToHost(data, 12)
                    dprint(__name__, 1, "Domain: "+domain)
                
                paket=''
                if domain in intercept:
                    dprint(__name__, 1, "***intercept request")
                    paket+=data[:2]         # 0:1 - ID
                    paket+="\x81\x80"       # 2:3 - flags
                    paket+=data[4:6]        # 4:5 - QDCOUNT - should be 1 for this code
                    paket+=data[4:6]        # 6:7 - ANCOUNT
                    paket+='\x00\x00'       # 8:9 - NSCOUNT
                    paket+='\x00\x00'       # 10:11 - ARCOUNT
                    paket+=data[12:]                                     # original query
                    paket+='\xc0\x0c'                                    # pointer to domain name/original query
                    paket+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'    # response type, ttl and resource data length -> 4 bytes
                    paket+=str.join('',map(lambda x: chr(int(x)), cfg_IP_self.split('.'))) # 4bytes of IP
                    dprint(__name__, 1, "-> DNS response: "+cfg_IP_self)
                
                elif domain in restrain:
                    dprint(__name__, 1, "***restrain request")
                    paket+=data[:2]         # 0:1 - ID
                    paket+="\x81\x80"       # 2:3 - flags
                    paket+=data[4:6]        # 4:5 - QDCOUNT - should be 1 for this code
                    paket+=data[4:6]        # 6:7 - ANCOUNT
                    paket+='\x00\x00'       # 8:9 - NSCOUNT
                    paket+='\x00\x00'       # 10:11 - ARCOUNT
                    paket+=data[12:]                                     # original query
                    paket+='\xc0\x0c'                                    # pointer to domain name/original query
                    paket+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'    # response type, ttl and resource data length -> 4 bytes
                    paket+='\x7f\x00\x00\x01'  # 4bytes of IP - 127.0.0.1, loopback
                    dprint(__name__, 1, "-> DNS response: "+cfg_IP_self)
                
                else:
                    dprint(__name__, 1, "***forward request")
                    DNS_forward.sendto(data, (cfg_IP_DNSMaster, 53))
                    paket, addr_master = DNS_forward.recvfrom(1024)
                    # todo: double check: ID has to be the same!
                    # todo: spawn thread to wait in parallel
                    dprint(__name__, 1, "-> DNS response from higher level")
                
                #print "-> respond back:"
                #printDNSdata(paket)
                
                # todo: double check: ID has to be the same!
                DNS.sendto(paket, addr)
            
            except socket.timeout:
                pass
            
            except socket.error as e:
                dprint(__name__, 1, "Warning: DNS error ({0}): {1}", e.errno, e.strerror)
            
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # we heard you!
        dprint(__name__, 0, "^C received.")
    finally:
        dprint(__name__, 0, "Shutting down.")
        DNS.close()
        DNS_forward.close()



if __name__ == '__main__':
    cmdPipe = Pipe()
    
    cfg = Settings.CSettings()
    param = {}
    param['CSettings'] = cfg
    
    param['IP_self'] = '192.168.178.20'  # IP_self?
    param['baseURL'] = 'http://'+ param['IP_self'] +':'+ cfg.getSetting('port_webserver')
    param['HostToIntercept'] = 'trailers.apple.com'
    
    Run(cmdPipe[1], param)

########NEW FILE########
__FILENAME__ = Localize
#!/usr/bin/env python

import os
import sys
import gettext
import re
from operator import itemgetter

from Debug import *  # dprint()



g_Translations = {}

def getTranslation(language):
    global g_Translations
    if language not in g_Translations:
        filename = os.path.join(sys.path[0], 'assets', 'locales', language, 'plexconnect.mo')
        try:
            fp = open(filename, 'rb')
            g_Translations[language] = gettext.GNUTranslations(fp)
            fp.close()
        except IOError:
            g_Translations[language] = gettext.NullTranslations()
    return g_Translations[language]



def pickLanguage(languages):
    language = 'en'
    language_aliases = {
        'zh_TW': 'zh_Hant',
        'zh_CN': 'zh_Hans'
    }
    
    languages = re.findall('(\w{2}(?:[-_]\w{2,})?)(?:;q=(\d+(?:\.\d+)?))?', languages)
    languages = [(lang.replace('-', '_'), float(quot) if quot else 1.) for (lang, quot) in languages]
    languages = [(language_aliases.get(lang, lang), quot) for (lang, quot) in languages]
    languages = sorted(languages, key=itemgetter(1), reverse=True)
    for lang, quot in languages:
        if os.path.exists(os.path.join(sys.path[0], 'assets', 'locales', lang, 'plexconnect.mo')):
                language = lang
                break
    dprint(__name__, 1, "aTVLanguage: "+language)
    return(language)



def replaceTEXT(textcontent, language):
    translation = getTranslation(language)
    for msgid in set(re.findall(r'\{\{TEXT\((.+?)\)\}\}', textcontent)):
        msgstr = translation.ugettext(msgid)
        textcontent = textcontent.replace('{{TEXT(%s)}}' % msgid, msgstr)
    return textcontent



if __name__=="__main__":
    languages = "de;q=0.9, en;q=0.8"
    language = pickLanguage(languages)
    
    Text = "Hello World"  # doesn't translate
    print getTranslation(language).ugettext(Text)
    
    Text = "Library"  # translates
    print getTranslation(language).ugettext(Text)
    
    Text = "{{TEXT(Channels)}}"  # translates
    print replaceTEXT(Text, language).encode('ascii', 'replace')

########NEW FILE########
__FILENAME__ = PlexAPI
#!/usr/bin/env python

"""
Collection of "connector functions" to Plex Media Server/MyPlex


PlexGDM:
loosely based on hippojay's plexGDM:
https://github.com/hippojay/plugin.video.plexbmc


Plex Media Server communication:
source (somewhat): https://github.com/hippojay/plugin.video.plexbmc
later converted from httplib to urllib2


Transcoder support:
PlexAPI_getTranscodePath() based on getTranscodeURL from pyplex/plexAPI
https://github.com/megawubs/pyplex/blob/master/plexAPI/info.py


MyPlex - Basic Authentication:
http://www.voidspace.org.uk/python/articles/urllib2.shtml
http://www.voidspace.org.uk/python/articles/authentication.shtml
http://stackoverflow.com/questions/2407126/python-urllib2-basic-auth-problem
http://stackoverflow.com/questions/111945/is-there-any-way-to-do-http-put-in-python
(and others...)
"""



import sys
import struct
import time
import urllib2, socket
from threading import Thread
import Queue

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

from urllib import urlencode, quote_plus

from Version import __VERSION__
from Debug import *  # dprint(), prettyXML()



"""
storage for PMS addresses and additional information - now per aTV! (replaces global PMS_list)
syntax: PMS[<ATV_UDID>][PMS_UUID][<data>]
    data: name, ip, ...type (local, myplex)
"""
g_PMS = {}


"""
Plex Media Server handling

parameters:
    ATV_udid
    uuid - PMS ID
    name, scheme, ip, port, type, owned, token
"""
def declarePMS(ATV_udid, uuid, name, scheme, ip, port):
    # store PMS information in g_PMS database
    global g_PMS
    if not ATV_udid in g_PMS:
        g_PMS[ATV_udid] = {}
    
    address = ip + ':' + port
    baseURL = scheme+'://'+ip+':'+port
    g_PMS[ATV_udid][uuid] = { 'name': name,
                              'scheme':scheme, 'ip': ip , 'port': port,
                              'address': address,
                              'baseURL': baseURL,
                              'local': '1',
                              'owned': '1',
                              'accesstoken': ''
                            }

def updatePMSProperty(ATV_udid, uuid, tag, value):
    # set property element of PMS by UUID
    if not ATV_udid in g_PMS:
        return ''  # no server known for this aTV
    if not uuid in g_PMS[ATV_udid]:
        return ''  # requested PMS not available
    
    g_PMS[ATV_udid][uuid][tag] = value

def getPMSProperty(ATV_udid, uuid, tag):
    # get name of PMS by UUID
    if not ATV_udid in g_PMS:
        return ''  # no server known for this aTV
    if not uuid in g_PMS[ATV_udid]:
        return ''  # requested PMS not available
    
    return g_PMS[ATV_udid][uuid].get(tag, '')

def getPMSFromAddress(ATV_udid, address):
    # find PMS by IP, return UUID
    if not ATV_udid in g_PMS:
        return ''  # no server known for this aTV
    
    for uuid in g_PMS[ATV_udid]:
        if address==g_PMS[ATV_udid][uuid].get('ip', None):
            return uuid
    return ''  # IP not found

def getPMSAddress(ATV_udid, uuid):
    # get address of PMS by UUID
    if not ATV_udid in g_PMS:
        return ''  # no server known for this aTV
    if not uuid in g_PMS[ATV_udid]:
        return ''  # requested PMS not available
    
    return g_PMS[ATV_udid][uuid]['ip'] + ':' + g_PMS[ATV_udid][uuid]['port']

def getPMSCount(ATV_udid):
    # get count of discovered PMS by UUID
    if not ATV_udid in g_PMS:
        return 0  # no server known for this aTV
    
    return len(g_PMS[ATV_udid])



"""
PlexGDM

parameters:
    none
result:
    PMS_list - dict() of PMSs found
"""
IP_PlexGDM = '<broadcast>'
Port_PlexGDM = 32414
Msg_PlexGDM = 'M-SEARCH * HTTP/1.0'

def PlexGDM():
    dprint(__name__, 0, "***")
    dprint(__name__, 0, "looking up Plex Media Server")
    dprint(__name__, 0, "***")
    
    # setup socket for discovery -> multicast message
    GDM = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    GDM.settimeout(1.0)
    
    # Set the time-to-live for messages to 1 for local network
    GDM.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    returnData = []
    try:
        # Send data to the multicast group
        dprint(__name__, 1, "Sending discovery message: {0}", Msg_PlexGDM)
        GDM.sendto(Msg_PlexGDM, (IP_PlexGDM, Port_PlexGDM))

        # Look for responses from all recipients
        while True:
            try:
                data, server = GDM.recvfrom(1024)
                dprint(__name__, 1, "Received data from {0}", server)
                dprint(__name__, 1, "Data received:\n {0}", data)
                returnData.append( { 'from' : server,
                                     'data' : data } )
            except socket.timeout:
                break
    finally:
        GDM.close()

    discovery_complete = True

    PMS_list = {}
    if returnData:
        for response in returnData:
            update = { 'ip' : response.get('from')[0] }
            
            # Check if we had a positive HTTP response                        
            if "200 OK" in response.get('data'):
                for each in response.get('data').split('\n'): 
                    # decode response data
                    update['discovery'] = "auto"
                    #update['owned']='1'
                    #update['master']= 1
                    #update['role']='master'
                    
                    if "Content-Type:" in each:
                        update['content-type'] = each.split(':')[1].strip()
                    elif "Resource-Identifier:" in each:
                        update['uuid'] = each.split(':')[1].strip()
                    elif "Name:" in each:
                        update['serverName'] = each.split(':')[1].strip().decode('utf-8', 'replace')  # store in utf-8
                    elif "Port:" in each:
                        update['port'] = each.split(':')[1].strip()
                    elif "Updated-At:" in each:
                        update['updated'] = each.split(':')[1].strip()
                    elif "Version:" in each:
                        update['version'] = each.split(':')[1].strip()
            
            PMS_list[update['uuid']] = update
    
    if PMS_list=={}:
        dprint(__name__, 0, "GDM: No servers discovered")
    else:
        dprint(__name__, 0, "GDM: Servers discovered: {0}", len(PMS_list))
        for uuid in PMS_list:
            dprint(__name__, 1, "{0} {1}:{2}", PMS_list[uuid]['serverName'], PMS_list[uuid]['ip'], PMS_list[uuid]['port'])
    
    return PMS_list



"""
discoverPMS

parameters:
    ATV_udid
    CSettings - for manual PMS configuration. this one looks strange.
    MyPlexToken
result:
    g_PMS database for ATV_udid
"""
def discoverPMS(ATV_udid, CSettings, MyPlexToken=''):
    global g_PMS
    g_PMS[ATV_udid] = {}
    
    #debug
    #declarePMS(ATV_udid, '2ndServer', '2ndServer', 'http', '192.168.178.22', '32400', 'local', '1', 'token')
    #declarePMS(ATV_udid, 'remoteServer', 'remoteServer', 'http', '127.0.0.1', '1234', 'myplex', '1', 'token')
    #debug
    
    # local PMS
    if CSettings.getSetting('enable_plexgdm')=='False':
        # defined in setting.cfg
        ip = CSettings.getSetting('ip_pms')
        port = CSettings.getSetting('port_pms')
        XML = getXMLFromPMS('http://'+ip+':'+port, '/servers', None, '')
        
        if XML==False:
            pass  # no response from manual defined server (Settings.cfg)
        else:
            Server = XML.find('Server')
            uuid = Server.get('machineIdentifier')
            name = Server.get('name')
            
            declarePMS(ATV_udid, uuid, name, 'http', ip, port)  # dflt: token='', local, owned
    
    else:
        # PlexGDM
        PMS_list = PlexGDM()
        for uuid in PMS_list:
            PMS = PMS_list[uuid]
            declarePMS(ATV_udid, PMS['uuid'], PMS['serverName'], 'http', PMS['ip'], PMS['port'])  # dflt: token='', local, owned
    
    # MyPlex servers
    if not MyPlexToken=='':
        XML = getXMLFromPMS('https://plex.tv', '/pms/servers', None, MyPlexToken)
        
        if XML==False:
            pass  # no data from MyPlex
        else:
            queue = Queue.Queue()
            threads = []
            
            for Dir in XML.getiterator('Server'):
                uuid = Dir.get('machineIdentifier')
                name = Dir.get('name')
                scheme = Dir.get('scheme')
                ip = Dir.get('address')
                port = Dir.get('port')
                token = Dir.get('accessToken', '')
                owned = Dir.get('owned', '0')
                
                if uuid in g_PMS.get(ATV_udid, {}):
                    # server known: local, manually defined or PlexGDM
                    updatePMSProperty(ATV_udid, uuid, 'accesstoken', token)
                    updatePMSProperty(ATV_udid, uuid, 'owned', owned)
                else:
                    # remote servers
                    # check MyPlex data age - skip if >2 days
                    infoAge = time.time() - int(Dir.get('updatedAt'))
                    oneDayInSec = 60*60*24
                    if infoAge > 2*oneDayInSec:  # two days in seconds -> expiration in setting?
                        dprint(__name__, 1, "Server {0} not updated for {1} days - skipping.", name, infoAge/oneDayInSec)
                        continue
                    
                    # poke PMS, own thread for each poke
                    PMS = { 'baseURL': scheme+'://'+ip+':'+port, 'path': '/', 'options': None, 'token': token, \
                            'data': Dir }
                    t = Thread(target=getXMLFromPMSToQueue, args=(PMS, queue))
                    t.start()
                    threads.append(t)
            
            # wait for requests being answered
            for t in threads:
                t.join()
            
            # declare new PMSs
            while not queue.empty():
                    (Dir, PMS) = queue.get()
                    
                    if PMS==False:
                        continue
                    
                    uuid = Dir.get('machineIdentifier')
                    name = Dir.get('name')
                    scheme = Dir.get('scheme')
                    ip = Dir.get('address')
                    port = Dir.get('port')
                    token = Dir.get('accessToken', '')
                    owned = Dir.get('owned', '0')
                    
                    declarePMS(ATV_udid, uuid, name, scheme, ip, port)  # dflt: token='', local, owned - updated later
                    updatePMSProperty(ATV_udid, uuid, 'local', '0')  # todo - check IP?
                    updatePMSProperty(ATV_udid, uuid, 'accesstoken', token)
                    updatePMSProperty(ATV_udid, uuid, 'owned', owned)
    
    # debug print all servers
    dprint(__name__, 0, "Servers (local+MyPlex): {0}", len(g_PMS[ATV_udid]))
    for uuid in g_PMS[ATV_udid]:
        dprint(__name__, 1, str(g_PMS[ATV_udid][uuid]))



"""
Plex Media Server communication

parameters:
    host
    path
    options - dict() of PlexConnect-options as received from aTV, None for no std. X-Plex-Args
    authtoken - authentication answer from MyPlex Sign In
result:
    returned XML or 'False' in case of error
"""
def getXMLFromPMS(baseURL, path, options={}, authtoken=''):
    xargs = {}
    if not options==None:
        xargs = getXArgsDeviceInfo(options)
    if not authtoken=='':
        xargs['X-Plex-Token'] = authtoken
    
    dprint(__name__, 1, "URL: {0}{1}", baseURL, path)
    dprint(__name__, 1, "xargs: {0}", xargs)
    
    request = urllib2.Request(baseURL+path , None, xargs)
    try:
        response = urllib2.urlopen(request, timeout=20)
    except urllib2.URLError as e:
        dprint(__name__, 0, 'No Response from Plex Media Server')
        if hasattr(e, 'reason'):
            dprint(__name__, 0, "We failed to reach a server. Reason: {0}", e.reason)
        elif hasattr(e, 'code'):
            dprint(__name__, 0, "The server couldn't fulfill the request. Error code: {0}", e.code)
        return False
    except IOError:
        dprint(__name__, 0, 'Error loading response XML from Plex Media Server')
        return False
    
    # parse into etree
    XML = etree.parse(response)
    
    dprint(__name__, 1, "====== received PMS-XML ======")
    dprint(__name__, 1, prettyXML(XML))
    dprint(__name__, 1, "====== PMS-XML finished ======")
    
    #XMLTree = etree.ElementTree(etree.fromstring(response))
    
    return XML



def getXMLFromPMSToQueue(PMS, queue):
    XML = getXMLFromPMS(PMS['baseURL'],PMS['path'],PMS['options'],PMS['token'])
    queue.put( (PMS['data'], XML) )



def getXArgsDeviceInfo(options={}):
    xargs = dict()
    xargs['X-Plex-Device'] = 'AppleTV'
    xargs['X-Plex-Model'] = '3,1' # Base it on AppleTV model.
    #if not options is None:
    if 'PlexConnectUDID' in options:
            xargs['X-Plex-Client-Identifier'] = options['PlexConnectUDID']  # UDID for MyPlex device identification
    if 'PlexConnectATVName' in options:
            xargs['X-Plex-Device-Name'] = options['PlexConnectATVName'] # "friendly" name: aTV-Settings->General->Name.
    xargs['X-Plex-Platform'] = 'iOS'
    xargs['X-Plex-Client-Platform'] = 'iOS'
    if 'aTVFirmwareVersion' in options:
        xargs['X-Plex-Platform-Version'] = options['aTVFirmwareVersion']
    xargs['X-Plex-Product'] = 'PlexConnect'
    xargs['X-Plex-Version'] = __VERSION__
    
    return xargs



"""
provide combined XML representation of local servers' XMLs, eg. /library/section

parameters:
    ATV_udid
    path
    type - owned <> shared (previously: local, myplex)
    options
result:
    XML
"""
def getXMLFromMultiplePMS(ATV_udid, path, type, options={}):
    queue = Queue.Queue()
    threads = []
    
    root = etree.Element("MediaConverter")
    root.set('friendlyName', type+' Servers')
    
    if type=='owned':
        owned='1'
    elif type=='shared':
        owned='0'
    
    for uuid in g_PMS.get(ATV_udid, {}):
        if getPMSProperty(ATV_udid, uuid, 'owned')==owned:
            Server = etree.SubElement(root, 'Server')  # create "Server" node
            Server.set('name',    getPMSProperty(ATV_udid, uuid, 'name'))
            Server.set('address', getPMSProperty(ATV_udid, uuid, 'ip'))
            Server.set('port',    getPMSProperty(ATV_udid, uuid, 'port'))
            Server.set('baseURL', getPMSProperty(ATV_udid, uuid, 'baseURL'))
            Server.set('local',   getPMSProperty(ATV_udid, uuid, 'local'))
            Server.set('owned',   getPMSProperty(ATV_udid, uuid, 'owned'))
            
            baseURL = getPMSProperty(ATV_udid, uuid, 'baseURL')
            token = getPMSProperty(ATV_udid, uuid, 'accesstoken')
            PMS_mark = 'PMS(' + getPMSProperty(ATV_udid, uuid, 'ip') + ')'
            
            Server.set('searchKey', PMS_mark + getURL('', '', '/SearchForm.xml'))
            
            # request XMLs, one thread for each
            PMS = { 'baseURL':baseURL, 'path':path, 'options':options, 'token':token, \
                    'data': {'uuid': uuid, 'Server': Server} }
            t = Thread(target=getXMLFromPMSToQueue, args=(PMS, queue))
            t.start()
            threads.append(t)
    
    # wait for requests being answered
    for t in threads:
        t.join()
    
    # add new data to root XML, individual Server
    while not queue.empty():
            (data, XML) = queue.get()
            uuid = data['uuid']
            Server = data['Server']
            
            baseURL = getPMSProperty(ATV_udid, uuid, 'baseURL')
            token = getPMSProperty(ATV_udid, uuid, 'accesstoken')
            PMS_mark = 'PMS(' + getPMSProperty(ATV_udid, uuid, 'ip') + ')'
            
            if XML==False:
                Server.set('size',    '0')
            else:
                Server.set('size',    XML.getroot().get('size', '0'))
                
                for Dir in XML.getiterator('Directory'):  # copy "Directory" content, add PMS to links
                    key = Dir.get('key')  # absolute path
                    Dir.set('key',    PMS_mark + getURL('', path, key))
                    Dir.set('refreshKey', getURL(baseURL, path, key) + '/refresh')
                    if 'thumb' in Dir.attrib:
                        Dir.set('thumb',  PMS_mark + getURL('', path, Dir.get('thumb')))
                    if 'art' in Dir.attrib:
                        Dir.set('art',    PMS_mark + getURL('', path, Dir.get('art')))
                    Server.append(Dir)
    
    root.set('size', str(len(root.findall('Server'))))
    
    XML = etree.ElementTree(root)
    
    dprint(__name__, 1, "====== Local Server/Sections XML ======")
    dprint(__name__, 1, prettyXML(XML))
    dprint(__name__, 1, "====== Local Server/Sections XML finished ======")
    
    return XML  # XML representation - created "just in time". Do we need to cache it?



def getURL(baseURL, path, key):
    if key.startswith('http://') or key.startswith('https://'):  # external server
        URL = key
    elif key.startswith('/'):  # internal full path.
        URL = baseURL + key
    elif key == '':  # internal path
        URL = baseURL + path
    else:  # internal path, add-on
        URL = baseURL + path + '/' + key
    
    return URL



"""
MyPlex Sign In, Sign Out

parameters:
    username - Plex forum name, MyPlex login, or email address
    password
    options - dict() of PlexConnect-options as received from aTV - necessary: PlexConnectUDID
result:
    username
    authtoken - token for subsequent communication with MyPlex
"""
def MyPlexSignIn(username, password, options):
    # MyPlex web address
    MyPlexHost = 'plex.tv'
    MyPlexSignInPath = '/users/sign_in.xml'
    MyPlexURL = 'https://' + MyPlexHost + MyPlexSignInPath
    
    # create POST request
    xargs = getXArgsDeviceInfo(options)
    request = urllib2.Request(MyPlexURL, None, xargs)
    request.get_method = lambda: 'POST'  # turn into 'POST' - done automatically with data!=None. But we don't have data.
    
    # no certificate, will fail with "401 - Authentification required"
    """
    try:
        f = urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        print e.headers
        print "has WWW_Authenticate:", e.headers.has_key('WWW-Authenticate')
        print
    """
    
    # provide credentials
    ### optional... when 'realm' is unknown
    ##passmanager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    ##passmanager.add_password(None, address, username, password)  # None: default "realm"
    passmanager = urllib2.HTTPPasswordMgr()
    passmanager.add_password(MyPlexHost, MyPlexURL, username, password)  # realm = 'plex.tv'
    authhandler = urllib2.HTTPBasicAuthHandler(passmanager)
    urlopener = urllib2.build_opener(authhandler)
    
    # sign in, get MyPlex response
    try:
        response = urlopener.open(request).read()
    except urllib2.HTTPError, e:
        if e.code==401:
            dprint(__name__, 0, 'Authentication failed')
            return ('', '')
        else:
            raise
    
    dprint(__name__, 1, "====== MyPlex sign in XML ======")
    dprint(__name__, 1, response)
    dprint(__name__, 1, "====== MyPlex sign in XML finished ======")
    
    # analyse response
    XMLTree = etree.ElementTree(etree.fromstring(response))
    
    el_username = XMLTree.find('username')
    el_authtoken = XMLTree.find('authentication-token')    
    if el_username is None or \
       el_authtoken is None:
        username = ''
        authtoken = ''
        dprint(__name__, 0, 'MyPlex Sign In failed')
    else:
        username = el_username.text
        authtoken = el_authtoken.text
        dprint(__name__, 0, 'MyPlex Sign In successfull')
    
    return (username, authtoken)



def MyPlexSignOut(authtoken):
    # MyPlex web address
    MyPlexHost = 'plex.tv'
    MyPlexSignOutPath = '/users/sign_out.xml'
    MyPlexURL = 'http://' + MyPlexHost + MyPlexSignOutPath
    
    # create POST request
    xargs = { 'X-Plex-Token': authtoken }
    request = urllib2.Request(MyPlexURL, None, xargs)
    request.get_method = lambda: 'POST'  # turn into 'POST' - done automatically with data!=None. But we don't have data.
    
    response = urllib2.urlopen(request).read()
    
    dprint(__name__, 1, "====== MyPlex sign out XML ======")
    dprint(__name__, 1, response)
    dprint(__name__, 1, "====== MyPlex sign out XML finished ======")
    dprint(__name__, 0, 'MyPlex Sign Out done')



"""
Transcode Video support

parameters:
    path
    AuthToken
    options - dict() of PlexConnect-options as received from aTV
    action - transcoder action: Auto, Directplay, Transcode
    quality - (resolution, quality, bitrate)
    subtitle - {'selected', 'dontBurnIn', 'size'}
    audio - {'boost'}
result:
    final path to pull in PMS transcoder
"""
def getTranscodeVideoPath(path, AuthToken, options, action, quality, subtitle, audio):
    UDID = options['PlexConnectUDID']
    
    transcodePath = '/video/:/transcode/universal/start.m3u8?'
    
    vRes = quality[0]
    vQ = quality[1]
    mVB = quality[2]
    dprint(__name__, 1, "Setting transcode quality Res:{0} Q:{1} {2}Mbps", vRes, vQ, mVB)
    dprint(__name__, 1, "Subtitle: selected {0}, dontBurnIn {1}, size {2}", subtitle['selected'], subtitle['dontBurnIn'], subtitle['size'])
    dprint(__name__, 1, "Audio: boost {0}", audio['boost'])
    
    args = dict()
    args['session'] = UDID
    args['protocol'] = 'hls'
    args['videoResolution'] = vRes
    args['maxVideoBitrate'] = mVB
    args['videoQuality'] = vQ
    args['directStream'] = '0' if action=='Transcode' else '1'
    # 'directPlay' - handled by the client in MEDIARUL()
    args['subtitleSize'] = subtitle['size']
    args['skipSubtitles'] = subtitle['dontBurnIn']  #'1'  # shut off PMS subtitles. Todo: skip only for aTV native/SRT (or other supported)
    args['audioBoost'] = audio['boost']
    args['fastSeek'] = '1'
    args['path'] = path
    
    xargs = getXArgsDeviceInfo(options)
    xargs['X-Plex-Client-Capabilities'] = "protocols=http-live-streaming,http-mp4-streaming,http-streaming-video,http-streaming-video-720p,http-mp4-video,http-mp4-video-720p;videoDecoders=h264{profile:high&resolution:1080&level:41};audioDecoders=mp3,aac{bitrate:160000}"
    if not AuthToken=='':
        xargs['X-Plex-Token'] = AuthToken
    
    return transcodePath + urlencode(args) + '&' + urlencode(xargs)



"""
Direct Video Play support

parameters:
    path
    AuthToken
    Indirect - media indirect specified, grab child XML to gain real path
    options
result:
    final path to media file
"""
def getDirectVideoPath(key, AuthToken):
    if key.startswith('http://') or key.startswith('https://'):  # external address - keep
        path = key
    else:
        if AuthToken=='':
            path = key
        else:
            xargs = dict()
            xargs['X-Plex-Token'] = AuthToken
            if key.find('?')==-1:
                path = key + '?' + urlencode(xargs)
            else:
                path = key + '&' + urlencode(xargs)
    
    return path



"""
Transcode Image support

parameters:
    key
    AuthToken
    path - source path of current XML: path[srcXML]
    width
    height
result:
    final path to image file
"""
def getTranscodeImagePath(key, AuthToken, path, width, height):
    if key.startswith('http://') or key.startswith('https://'):  # external address - can we get a transcoding request for external images?
        path = key
    elif key.startswith('/'):  # internal full path.
        path = 'http://127.0.0.1:32400' + key
    else:  # internal path, add-on
        path = 'http://127.0.0.1:32400' + path + '/' + key
    path = path.encode('utf8')
    
    # This is bogus (note the extra path component) but ATV is stupid when it comes to caching images, it doesn't use querystrings.
    # Fortunately PMS is lenient...
    transcodePath = '/photo/:/transcode/' +str(width)+'x'+str(height)+ '/' + quote_plus(path)
    
    args = dict()
    args['width'] = width
    args['height'] = height
    args['url'] = path
    
    if not AuthToken=='':
        args['X-Plex-Token'] = AuthToken
    
    return transcodePath + '?' + urlencode(args)



"""
Direct Image support

parameters:
    path
    AuthToken
result:
    final path to image file
"""
def getDirectImagePath(path, AuthToken):
    if not AuthToken=='':
        xargs = dict()
        xargs['X-Plex-Token'] = AuthToken
        if path.find('?')==-1:
            path = path + '?' + urlencode(xargs)
        else:
            path = path + '&' + urlencode(xargs)
    
    return path



"""
Transcode Audio support

parameters:
    path
    AuthToken
    options - dict() of PlexConnect-options as received from aTV
    maxAudioBitrate - [kbps]
result:
    final path to pull in PMS transcoder
"""
def getTranscodeAudioPath(path, AuthToken, options, maxAudioBitrate):
    UDID = options['PlexConnectUDID']
    
    transcodePath = '/music/:/transcode/universal/start.mp3?'
    
    args = dict()
    args['path'] = path
    args['session'] = UDID
    args['protocol'] = 'http'
    args['maxAudioBitrate'] = maxAudioBitrate
    
    xargs = getXArgsDeviceInfo(options)
    if not AuthToken=='':
        xargs['X-Plex-Token'] = AuthToken
    
    return transcodePath + urlencode(args) + '&' + urlencode(xargs)



"""
Direct Audio support

parameters:
    path
    AuthToken
result:
    final path to audio file
"""
def getDirectAudioPath(path, AuthToken):
    if not AuthToken=='':
        xargs = dict()
        xargs['X-Plex-Token'] = AuthToken
        if path.find('?')==-1:
            path = path + '?' + urlencode(xargs)
        else:
            path = path + '&' + urlencode(xargs)
    
    return path



if __name__ == '__main__':
    testPlexGDM = 0
    testLocalPMS = 0
    testSectionXML = 1
    testMyPlexXML = 0
    testMyPlexSignIn = 0
    testMyPlexSignOut = 0
    
    username = 'abc'
    password = 'def'
    token = 'xyz'
    
    
    # test PlexGDM
    if testPlexGDM:
        dprint('', 0, "*** PlexGDM")
        PMS_list = PlexGDM()
        dprint('', 0, PMS_list)
    
    
    # test XML from local PMS
    if testLocalPMS:
        dprint('', 0, "*** XML from local PMS")
        XML = getXMLFromPMS('http://127.0.0.1:32400', '/library/sections')
    
    
    # test local Server/Sections
    if testSectionXML:
        dprint('', 0, "*** local Server/Sections")
        PMS_list = PlexGDM()
        XML = getSectionXML(PMS_list, {}, '')
    
    
    # test XML from MyPlex
    if testMyPlexXML:
        dprint('', 0, "*** XML from MyPlex")
        XML = getXMLFromPMS('https://plex.tv', '/pms/servers', None, token)
        XML = getXMLFromPMS('https://plex.tv', '/pms/system/library/sections', None, token)
    
    
    # test MyPlex Sign In
    if testMyPlexSignIn:
        dprint('', 0, "*** MyPlex Sign In")
        options = {'PlexConnectUDID':'007'}
        
        (user, token) = MyPlexSignIn(username, password, options)
        if user=='' and token=='':
            dprint('', 0, "Authentication failed")
        else:
            dprint('', 0, "logged in: {0}, {1}", user, token)
    
    
    # test MyPlex Sign out
    if testMyPlexSignOut:
        dprint('', 0, "*** MyPlex Sign Out")
        MyPlexSignOut(token)
        dprint('', 0, "logged out")
    
    # test transcoder

########NEW FILE########
__FILENAME__ = PlexConnect
#!/usr/bin/env python

"""
PlexConnect

Sources:
inter-process-communication (queue): http://pymotw.com/2/multiprocessing/communication.html
"""


import sys, time
from os import sep
import socket
from multiprocessing import Process, Pipe
import signal, errno

from Version import __VERSION__
import DNSServer, WebServer
import Settings
from Debug import *  # dprint()



def getIP_self():
    cfg = param['CSettings']
    if cfg.getSetting('enable_plexconnect_autodetect')=='True':
        # get public ip of machine running PlexConnect
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('1.2.3.4', 1000))
        IP = s.getsockname()[0]
        dprint('PlexConnect', 0, "IP_self: "+IP)
    else:
        # manual override from "settings.cfg"
        IP = cfg.getSetting('ip_plexconnect')
        dprint('PlexConnect', 0, "IP_self (from settings): "+IP)
    
    return IP



procs = {}
pipes = {}
param = {}
running = False

def startup():
    global procs
    global pipes
    global param
    global running
    
    # Settings
    cfg = Settings.CSettings()
    param['CSettings'] = cfg
    
    # Logfile
    if cfg.getSetting('logpath').startswith('.'):
        # relative to current path
        logpath = sys.path[0] + sep + cfg.getSetting('logpath')
    else:
        # absolute path
        logpath = cfg.getSetting('logpath')
    
    param['LogFile'] = logpath + sep + 'PlexConnect.log'
    param['LogLevel'] = cfg.getSetting('loglevel')
    dinit('PlexConnect', param, True)  # init logging, new file, main process
    
    dprint('PlexConnect', 0, "Version: {0}", __VERSION__)
    dprint('PlexConnect', 0, "Python: {0}", sys.version)
    dprint('PlexConnect', 0, "Host OS: {0}", sys.platform)
    
    # more Settings
    param['IP_self'] = getIP_self()
    param['HostToIntercept'] = cfg.getSetting('hosttointercept')
    param['baseURL'] = 'http://'+ param['HostToIntercept']
    
    running = True
    
    # init DNSServer
    if cfg.getSetting('enable_dnsserver')=='True':
        master, slave = Pipe()  # endpoint [0]-PlexConnect, [1]-DNSServer
        proc = Process(target=DNSServer.Run, args=(slave, param))
        proc.start()
        
        time.sleep(0.1)
        if proc.is_alive():
            procs['DNSServer'] = proc
            pipes['DNSServer'] = master
        else:
            dprint('PlexConnect', 0, "DNSServer not alive. Shutting down.")
            running = False
    
    # init WebServer
    if running:
        master, slave = Pipe()  # endpoint [0]-PlexConnect, [1]-WebServer
        proc = Process(target=WebServer.Run, args=(slave, param))
        proc.start()
        
        time.sleep(0.1)
        if proc.is_alive():
            procs['WebServer'] = proc
            pipes['WebServer'] = master
        else:
            dprint('PlexConnect', 0, "WebServer not alive. Shutting down.")
            running = False
    
    # init WebServer_SSL
    if running and \
       cfg.getSetting('enable_webserver_ssl')=='True':
        master, slave = Pipe()  # endpoint [0]-PlexConnect, [1]-WebServer
        proc = Process(target=WebServer.Run_SSL, args=(slave, param))
        proc.start()
        
        time.sleep(0.1)
        if proc.is_alive():
            procs['WebServer_SSL'] = proc
            pipes['WebServer_SSL'] = master
        else:
            dprint('PlexConnect', 0, "WebServer_SSL not alive. Shutting down.")
            running = False
    
    # not started successful - clean up
    if not running:
        cmdShutdown()
        shutdown()
    
    return running

def run(timeout=60):
    # do something important
    try:
        time.sleep(timeout)
    except IOError as e:
        if e.errno == errno.EINTR and not running:
            pass  # mask "IOError: [Errno 4] Interrupted function call"
        else:
            raise
    
    return running

def shutdown():
    for slave in procs:
        procs[slave].join()
    dprint('PlexConnect', 0, "shutdown")

def cmdShutdown():
    global running
    running = False
    # send shutdown to all pipes
    for slave in pipes:
        pipes[slave].send('shutdown')
    dprint('PlexConnect', 0, "Shutting down.")



def sighandler_shutdown(signum, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # we heard you!
    cmdShutdown()



if __name__=="__main__":
    signal.signal(signal.SIGINT, sighandler_shutdown)
    signal.signal(signal.SIGTERM, sighandler_shutdown)
    
    dprint('PlexConnect', 0, "***")
    dprint('PlexConnect', 0, "PlexConnect")
    dprint('PlexConnect', 0, "Press CTRL-C to shut down.")
    dprint('PlexConnect', 0, "***")
    
    running = startup()
    
    while running:
        running = run()
    
    shutdown()

########NEW FILE########
__FILENAME__ = PlexConnect_daemon
#!/usr/bin/env python

"""
PlexConnectDaemon

Creates a proper daemon on mac/linux
"""

import os
import sys
import signal
import argparse
import atexit
from PlexConnect import startup, shutdown, run, cmdShutdown


def daemonize(args):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    """

    # Make a non-session-leader child process
    try:
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]" % (e.strerror, e.errno))

    # decouple from parent environment
    os.setsid()

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2nd fork failed: %s [%d]" % (e.strerror, e.errno))

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file('/dev/null', 'r')
    so = file('/dev/null', 'a+')
    se = file('/dev/null', 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    if args.pidfile:
        try:
            atexit.register(delpid)
            pid = str(os.getpid())
            file(args.pidfile, 'w').write("%s\n" % pid)
        except IOError, e:
            raise SystemExit("Unable to write PID file: %s [%d]" % (e.strerror, e.errno))


def delpid():
    global args
    os.remove(args.pidfile)


def sighandler_shutdown(signum, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # we heard you!
    cmdShutdown()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sighandler_shutdown)
    signal.signal(signal.SIGTERM, sighandler_shutdown)

    parser = argparse.ArgumentParser(description='PlexConnect as daemon.')
    parser.add_argument('--pidfile', dest='pidfile')
    args = parser.parse_args()

    daemonize(args)

    running = startup()

    while running:
        running = run()

    shutdown()

########NEW FILE########
__FILENAME__ = PlexConnect_WinService
"""
PlexConnect_WinService
Starter script to run PlexConnect as a Windows Service

prerequisites:
http://sourceforge.net/projects/pywin32/

usage:
python PlexConnect_WinService.py <command>
with <command> = install, start, stop or remove

sources:
http://stackoverflow.com/questions/32404/can-i-run-a-python-script-as-a-service-in-windows-how
http://code.activestate.com/recipes/551780/
http://docs.activestate.com/activepython/2.4/pywin32/win32service.html
...and others
"""

import win32serviceutil
import win32service

import PlexConnect



class AppServerSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "PlexConnect-Service"
    _svc_display_name_ = "PlexConnect-Service"
    _svc_description_ = "Description"
    
    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        PlexConnect.cmdShutdown()
    
    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        running = PlexConnect.startup()
        
        while running:
            running = PlexConnect.run(timeout=10)
        
        PlexConnect.shutdown()
        
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)



if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)

########NEW FILE########
__FILENAME__ = Settings
#!/usr/bin/env python

import sys
from os import sep
import ConfigParser
import re

from Debug import *  # dprint()



"""
Global Settings...
syntax: 'setting': ('default', 'regex to validate')

PMS: plexgdm, ip_pms, port_pms
DNS: ip_dnsmaster - IP of Router, ISP's DNS, ... [dflt: google public DNS]
IP_self: enable_plexconnect_autodetect, ip_plexconnect - manual override for VPN usage
Intercept: Trailers-trailers.apple.com, WSJ-secure.marketwatch.com, iMovie-www.icloud.com
HTTP: port_webserver - override when using webserver + forwarding to PlexConnect
HTTPS: port_ssl, certfile, enable_webserver_ssl - configure SSL portion or webserver
"""
g_settings = [
    ('enable_plexgdm'  , ('True', '((True)|(False))')),
    ('ip_pms'          , ('192.168.178.10', '([0-9]{1,3}\.){3}[0-9]{1,3}')),
    ('port_pms'        , ('32400', '[0-9]{1,5}')),
    \
    ('enable_dnsserver', ('True', '((True)|(False))')),
    ('port_dnsserver'  , ('53', '[0-9]{1,5}')),
    ('ip_dnsmaster'    , ('8.8.8.8', '([0-9]{1,3}\.){3}[0-9]{1,3}')),
    ('prevent_atv_update'           , ('True', '((True)|(False))')),
    \
    ('enable_plexconnect_autodetect', ('True', '((True)|(False))')),
    ('ip_plexconnect'  , ('0.0.0.0', '([0-9]{1,3}\.){3}[0-9]{1,3}')),
    ('hosttointercept' , ('trailers.apple.com', '[a-zA-Z0-9_.]+')),
    \
    ('port_webserver'  , ('80', '[0-9]{1,5}')),
    ('enable_webserver_ssl'         , ('True', '((True)|(False))')),
    ('port_ssl'        , ('443', '[0-9]{1,5}')),
    ('certfile'        , ('./assets/certificates/trailers.pem', '.+.pem')),
    \
    ('loglevel'        , ('Normal', '((Off)|(Normal)|(High))')),
    ('logpath'         , ('.', '.+')),
    ]



class CSettings():
    def __init__(self):
        dprint(__name__, 1, "init class CSettings")
        self.cfg = ConfigParser.SafeConfigParser()
        self.section = 'PlexConnect'
        
        # set option for fixed ordering
        self.cfg.add_section(self.section)
        for (opt, (dflt, vldt)) in g_settings:
            self.cfg.set(self.section, opt, '\0')
        
        self.loadSettings()
        self.checkSection()
    
    
    
    # load/save config
    def loadSettings(self):
        dprint(__name__, 1, "load settings")
        self.cfg.read(self.getSettingsFile())
    
    def saveSettings(self):
        dprint(__name__, 1, "save settings")
        f = open(self.getSettingsFile(), 'wb')
        self.cfg.write(f)
        f.close()
    
    def getSettingsFile(self):
        return sys.path[0] + sep + "Settings.cfg"
    
    def checkSection(self):
        modify = False
        # check for existing section
        if not self.cfg.has_section(self.section):
            modify = True
            self.cfg.add_section(self.section)
            dprint(__name__, 0, "add section {0}", self.section)
        
        for (opt, (dflt, vldt)) in g_settings:
            setting = self.cfg.get(self.section, opt)
            if setting=='\0':
                # check settings - add if new
                modify = True
                self.cfg.set(self.section, opt, dflt)
                dprint(__name__, 0, "add setting {0}={1}", opt, dflt)
            
            elif not re.search('\A'+vldt+'\Z', setting):
                # check settings - default if unknown
                modify = True
                self.cfg.set(self.section, opt, dflt)
                dprint(__name__, 0, "bad setting {0}={1} - set default {2}", opt, setting, dflt)
        
        # save if changed
        if modify:
            self.saveSettings()
    
    
    
    # access/modify PlexConnect settings
    def getSetting(self, option):
        dprint(__name__, 1, "getsetting {0}={1}", option, self.cfg.get(self.section, option))
        return self.cfg.get(self.section, option)



if __name__=="__main__":
    Settings = CSettings()
    
    option = 'enable_plexgdm'
    print Settings.getSetting(option)
    
    option = 'enable_dnsserver'
    print Settings.getSetting(option)
    
    del Settings

########NEW FILE########
__FILENAME__ = Subtitle
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Subtitle transcoder functions
"""



import re
import urllib2
import json

from Debug import *  # dprint(), prettyXML()
import PlexAPI



"""
Plex Media Server: get subtitle, return as aTV subtitle JSON

parameters:
    PMS_address
    path
    options - dict() of PlexConnect-options as received from aTV, None for no std. X-Plex-Args
result:
    aTV subtitle JSON or 'False' in case of error
"""
def getSubtitleJSON(PMS_address, path, options):
    """
    # double check aTV UDID, redo from client IP if needed/possible
    if not 'PlexConnectUDID' in options:
        UDID = getATVFromIP(options['aTVAddress'])
        if UDID:
            options['PlexConnectUDID'] = UDID
    """
    path = path + '?' if not '?' in path else '&'
    path = path + 'encoding=utf-8'
    
    if not 'PlexConnectUDID' in options:
        # aTV unidentified, UDID not known
        return False
    
    UDID = options['PlexConnectUDID']
    
    # determine PMS_uuid, PMSBaseURL from IP (PMS_mark)
    xargs = {}
    PMS_uuid = PlexAPI.getPMSFromAddress(UDID, PMS_address)
    PMS_baseURL = PlexAPI.getPMSProperty(UDID, PMS_uuid, 'baseURL')
    xargs['X-Plex-Token'] = PlexAPI.getPMSProperty(UDID, PMS_uuid, 'accesstoken')
    
    dprint(__name__, 1, "subtitle URL: {0}{1}", PMS_baseURL, path)
    dprint(__name__, 1, "xargs: {0}", xargs)
    
    request = urllib2.Request(PMS_baseURL+path , None, xargs)
    try:
        response = urllib2.urlopen(request, timeout=20)
    except urllib2.URLError as e:
        dprint(__name__, 0, 'No Response from Plex Media Server')
        if hasattr(e, 'reason'):
            dprint(__name__, 0, "We failed to reach a server. Reason: {0}", e.reason)
        elif hasattr(e, 'code'):
            dprint(__name__, 0, "The server couldn't fulfill the request. Error code: {0}", e.code)
        return False
    except IOError:
        dprint(__name__, 0, 'Error loading response XML from Plex Media Server')
        return False
    
    # Todo: Deal with ANSI files. How to select used "codepage"?
    subtitleFile = response.read()
    
    print response.headers
    
    dprint(__name__, 1, "====== received Subtitle ======")
    dprint(__name__, 1, "{0} [...]", subtitleFile[:255])
    dprint(__name__, 1, "====== Subtitle finished ======")
    
    if options['PlexConnectSubtitleFormat']=='srt':
        subtitle = parseSRT(subtitleFile)
    else:
        return False
    
    JSON = json.dumps(subtitle)
    
    dprint(__name__, 1, "====== generated subtitle aTV subtitle JSON ======")
    dprint(__name__, 1, "{0} [...]", JSON[:255])
    dprint(__name__, 1, "====== aTV subtitle JSON finished ======")
    return(JSON)



"""
parseSRT - decode SRT file, create aTV subtitle structure

parameters:
    SRT - big string containing the SRT file
result:
    JSON - subtitle encoded into .js tree to feed PlexConnect's updateSubtitle() (see application.js)
"""
def parseSRT(SRT):
    subtitle = { 'Timestamp': [] }
    
    srtPart = re.split(r'(\r\n|\n\r|\n|\r)\1+(?=[0-9]+)', SRT.strip())[::2];  # trim whitespaces, split at multi-newline, check for following number
    timeHide_last = 0
    
    for Item in srtPart:
        ItemPart = re.split(r'\r\n|\n\r|\n|\r', Item.strip());  # trim whitespaces, split at newline
        
        timePart = re.split(r':|,|-->', ItemPart[1]);  # <StartTime> --> <EndTime> split at : , or -->
        timeShow = int(timePart[0])*1000*60*60 +\
                   int(timePart[1])*1000*60 +\
                   int(timePart[2])*1000 +\
                   int(timePart[3]);
        timeHide = int(timePart[4])*1000*60*60 +\
                   int(timePart[5])*1000*60 +\
                   int(timePart[6])*1000 +\
                   int(timePart[7]);
        
        # switch off? skip if new msg at same point in time.
        if timeHide_last!=timeShow:
            subtitle['Timestamp'].append({ 'time': timeHide_last })
        timeHide_last = timeHide
        
        # current time
        subtitle['Timestamp'].append({ 'time': timeShow, 'Line': [] })
        #JSON += '  { "time":'+str(timeHide_last)+', "Line": [\n'
        
        # analyse format: <...> - i_talics (light), b_old (heavy), u_nderline (?), font color (?)
        frmt_i = False
        frmt_b = False
        for i, line in enumerate(ItemPart[2:]):  # evaluate each text line
            for frmt in re.finditer(r'<([^/]*?)>', line):  # format switch on in current line
                if frmt.group(1)=='i': frmt_i = True
                if frmt.group(1)=='b': frmt_b = True
            
            weight = ''  # determine aTV font - from previous line or current
            if frmt_i: weight = 'light'
            if frmt_b: weight = 'heavy'
            
            for frmt in re.finditer(r'</(.*?)>', line):  # format switch off
                if frmt.group(1)=='i': frmt_i = False
                if frmt.group(1)=='b': frmt_b = False
            
            line = re.sub('<.*?>', "", line);  # remove the formatting identifiers
            
            subtitle['Timestamp'][-1]['Line'].append({ 'text': line })
            if weight: subtitle['Timestamp'][-1]['Line'][-1]['weight'] = weight
    
    subtitle['Timestamp'].append({ 'time': timeHide_last })  # switch off last subtitle
    return subtitle



if __name__ == '__main__':
    SRT = "\
1\n\
00:00:0,123 --> 00:00:03,456\n\
<i>Hello World</i>\n\
\n\
2\n\
00:00:03,456 --> 00:00:06,000\n\
<b>Question -</b>\n\
Does it run?\n\
\n\
3\n\
00:00:08,000 --> 00:00:10,000\n\
Yes, Python works!\n\
\n\
"
    
    dprint('', 0, "SRT file")
    dprint('', 0, SRT[:1000])
    subtitle = parseSRT(SRT)
    JSON = json.dumps(subtitle)
    dprint('', 0, "aTV subtitle JSON")
    dprint('', 0, JSON[:1000])
    
"""
JSON result (about):
{ "Timestamp": [
  { "time":0 },
  { "time":123, "Line": [
    { "text":"Hello World", "weight": "light" }
    ]
  },
  { "time":3456, "Line": [
    { "text":"Question -", "weight": "heavy" },
    { "text":"Does it run?" }
    ]
  },
  { "time":6000 },
  { "time":8000, "Line": [
    { "text":"Yes, Python works!" }
    ]
  },
  { "time":10000 }
  ]
}
"""

########NEW FILE########
__FILENAME__ = Version
#!/usr/bin/env python

"""
Version.py
"""



# Version string - globally available
__VERSION__ = '0.3.1+'

########NEW FILE########
__FILENAME__ = WebServer
#!/usr/bin/env python

"""
Sources:
http://fragments.turtlemeat.com/pythonwebserver.php
http://www.linuxjournal.com/content/tech-tip-really-simple-http-server-python
...stackoverflow.com and such

after 27Aug - Apple's switch to https:
- added https WebServer with SSL encryption - needs valid (private) vertificate on aTV and server
- for additional information see http://langui.sh/2013/08/27/appletv-ssl-plexconnect/
Thanks to reaperhulk for showing this solution!
"""


import sys
import string, cgi, time
from os import sep, path
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import ssl
from multiprocessing import Pipe  # inter process communication
import urllib
import signal

import Settings, ATVSettings
from Debug import *  # dprint()
import XMLConverter  # XML_PMS2aTV, XML_PlayVideo
import re
import Localize
import Subtitle



g_param = {}
def setParams(param):
    global g_param
    g_param = param



def JSConverter(file, options):
    f = open(sys.path[0] + "/assets/js/" + file)
    JS = f.read()
    f.close()
    
    # PlexConnect {{URL()}}->baseURL
    for path in set(re.findall(r'\{\{URL\((.*?)\)\}\}', JS)):
        JS = JS.replace('{{URL(%s)}}' % path, g_param['baseURL']+path)
    
    # localization
    JS = Localize.replaceTEXT(JS, options['aTVLanguage']).encode('utf-8')
    
    return JS



class MyHandler(BaseHTTPRequestHandler):
    
    # Fixes slow serving speed under Windows
    def address_string(self):
      host, port = self.client_address[:2]
      #return socket.getfqdn(host)
      return host
      
    def log_message(self, format, *args):
      pass
    
    def do_GET(self):
        global g_param
        try:
            dprint(__name__, 2, "http request header:\n{0}", self.headers)
            dprint(__name__, 2, "http request path:\n{0}", self.path)
            
            # check for PMS address
            PMSaddress = ''
            pms_end = self.path.find(')')
            if self.path.startswith('/PMS(') and pms_end>-1:
                PMSaddress = urllib.unquote_plus(self.path[5:pms_end])
                self.path = self.path[pms_end+1:]
            
            # break up path, separate PlexConnect options
            # clean path needed for filetype decoding
            parts = re.split(r'[?&]', self.path, 1)  # should be '?' only, but we do some things different :-)
            if len(parts)==1:
                self.path = parts[0]
                options = {}
                query = ''
            else:
                self.path = parts[0]
                
                # break up query string
                options = {}
                query = ''
                parts = parts[1].split('&')
                for part in parts:
                    if part.startswith('PlexConnect'):
                        # get options[]
                        opt = part.split('=', 1)
                        if len(opt)==1:
                            options[opt[0]] = ''
                        else:
                            options[opt[0]] = urllib.unquote(opt[1])
                    else:
                        # recreate query string (non-PlexConnect) - has to be merged back when forwarded
                        if query=='':
                            query = '?' + part
                        else:
                            query += '&' + part
            
            # get aTV language setting
            options['aTVLanguage'] = Localize.pickLanguage(self.headers.get('Accept-Language', 'en'))
            
            # add client address - to be used in case UDID is unknown
            if 'X-Forwarded-For' in self.headers:
                options['aTVAddress'] = self.headers['X-Forwarded-For'].split(',', 1)[0]
            else:
                options['aTVAddress'] = self.client_address[0]
            
            # get aTV hard-/software parameters
            options['aTVFirmwareVersion'] = self.headers.get('X-Apple-TV-Version', '5.1')
            options['aTVScreenResolution'] = self.headers.get('X-Apple-TV-Resolution', '720')
            
            dprint(__name__, 2, "pms address:\n{0}", PMSaddress)
            dprint(__name__, 2, "cleaned path:\n{0}", self.path)
            dprint(__name__, 2, "PlexConnect options:\n{0}", options)
            dprint(__name__, 2, "additional arguments:\n{0}", query)
            
            if 'User-Agent' in self.headers and \
               'AppleTV' in self.headers['User-Agent']:
                
                # recieve simple logging messages from the ATV
                if 'PlexConnectATVLogLevel' in options:
                    dprint('ATVLogger', int(options['PlexConnectATVLogLevel']), options['PlexConnectLog'])
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    return
                    
                # serve "*.cer" - Serve up certificate file to atv
                if self.path.endswith(".cer"):
                    dprint(__name__, 1, "serving *.cer: "+self.path)
                    if g_param['CSettings'].getSetting('certfile').startswith('.'):
                        # relative to current path
                        cfg_certfile = sys.path[0] + sep + g_param['CSettings'].getSetting('certfile')
                    else:
                        # absolute path
                        cfg_certfile = g_param['CSettings'].getSetting('certfile')
                    cfg_certfile = path.normpath(cfg_certfile)
                    
                    cfg_certfile = path.splitext(cfg_certfile)[0] + '.cer'
                    try:
                        f = open(cfg_certfile, "rb")
                    except:
                        dprint(__name__, 0, "Failed to access certificate: {0}", cfg_certfile)
                        return
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/xml')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
                    return 
                
                # serve .js files to aTV
                # application, main: ignore path, send /assets/js/application.js
                # otherwise: path should be '/js', send /assets/js/*.js
                dirname = path.dirname(self.path)
                basename = path.basename(self.path)
                if basename in ("application.js", "main.js", "javascript-packed.js", "bootstrap.js") or \
                   basename.endswith(".js") and dirname == '/js':
                    if basename in ("main.js", "javascript-packed.js", "bootstrap.js"):
                        basename = "application.js"
                    dprint(__name__, 1, "serving /js/{0}", basename)
                    JS = JSConverter(basename, options)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/javascript')
                    self.end_headers()
                    self.wfile.write(JS)
                    return
                
                # serve "*.jpg" - thumbnails for old-style mainpage
                if self.path.endswith(".jpg"):
                    dprint(__name__, 1, "serving *.jpg: "+self.path)
                    f = open(sys.path[0] + sep + "assets" + self.path, "rb")
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
                    return
                
                # serve "*.png" - only png's support transparent colors
                if self.path.endswith(".png"):
                    dprint(__name__, 1, "serving *.png: "+self.path)
                    f = open(sys.path[0] + sep + "assets" + self.path, "rb")
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
                    return
                
                # serve subtitle file - transcoded to aTV subtitle json
                if 'PlexConnect' in options and \
                   options['PlexConnect']=='Subtitle':
                    dprint(__name__, 1, "serving subtitle: "+self.path)
                    XML = Subtitle.getSubtitleJSON(PMSaddress, self.path + query, options)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(XML)
                    return
                
                # get everything else from XMLConverter - formerly limited to trailing "/" and &PlexConnect Cmds
                if True:
                    dprint(__name__, 1, "serving .xml: "+self.path)
                    XML = XMLConverter.XML_PMS2aTV(PMSaddress, self.path + query, options)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/xml')
                    self.end_headers()
                    self.wfile.write(XML)
                    return
                
                """
                # unexpected request
                self.send_error(403,"Access denied: %s" % self.path)
                """
            
            else:
                self.send_error(403,"Not Serving Client %s" % self.client_address[0])
        except IOError:
            self.send_error(404,"File Not Found: %s" % self.path)



def Run(cmdPipe, param):
    if not __name__ == '__main__':
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    dinit(__name__, param)  # init logging, WebServer process
    
    cfg_IP_WebServer = param['IP_self']
    cfg_Port_WebServer = param['CSettings'].getSetting('port_webserver')
    try:
        server = HTTPServer((cfg_IP_WebServer,int(cfg_Port_WebServer)), MyHandler)
        server.timeout = 1
    except Exception, e:
        dprint(__name__, 0, "Failed to connect to HTTP on {0} port {1}: {2}", cfg_IP_WebServer, cfg_Port_WebServer, e)
        sys.exit(1)
    
    socketinfo = server.socket.getsockname()
    
    dprint(__name__, 0, "***")
    dprint(__name__, 0, "WebServer: Serving HTTP on {0} port {1}.", socketinfo[0], socketinfo[1])
    dprint(__name__, 0, "***")
    
    setParams(param)
    XMLConverter.setParams(param)
    cfg = ATVSettings.CATVSettings()
    XMLConverter.setATVSettings(cfg)
    
    try:
        while True:
            # check command
            if cmdPipe.poll():
                cmd = cmdPipe.recv()
                if cmd=='shutdown':
                    break
            
            # do your work (with timeout)
            server.handle_request()
    
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # we heard you!
        dprint(__name__, 0,"^C received.")
    finally:
        dprint(__name__, 0, "Shutting down.")
        cfg.saveSettings()
        del cfg
        server.socket.close()



def Run_SSL(cmdPipe, param):
    if not __name__ == '__main__':
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    dinit(__name__, param)  # init logging, WebServer process
    
    cfg_IP_WebServer = param['IP_self']
    cfg_Port_SSL = param['CSettings'].getSetting('port_ssl')
    
    if param['CSettings'].getSetting('certfile').startswith('.'):
        # relative to current path
        cfg_certfile = sys.path[0] + sep + param['CSettings'].getSetting('certfile')
    else:
        # absolute path
        cfg_certfile = param['CSettings'].getSetting('certfile')
    cfg_certfile = path.normpath(cfg_certfile)
    
    try:
        certfile = open(cfg_certfile, 'r')
    except:
        dprint(__name__, 0, "Failed to access certificate: {0}", cfg_certfile)
        sys.exit(1)
    certfile.close()
    
    try:
        server = HTTPServer((cfg_IP_WebServer,int(cfg_Port_SSL)), MyHandler)
        server.socket = ssl.wrap_socket(server.socket, certfile=cfg_certfile, server_side=True)
        server.timeout = 1
    except Exception, e:
        dprint(__name__, 0, "Failed to connect to HTTPS on {0} port {1}: {2}", cfg_IP_WebServer, cfg_Port_SSL, e)
        sys.exit(1)
    
    socketinfo = server.socket.getsockname()
    
    dprint(__name__, 0, "***")
    dprint(__name__, 0, "WebServer: Serving HTTPS on {0} port {1}.", socketinfo[0], socketinfo[1])
    dprint(__name__, 0, "***")
    
    setParams(param)
    
    try:
        while True:
            # check command
            if cmdPipe.poll():
                cmd = cmdPipe.recv()
                if cmd=='shutdown':
                    break
            
            # do your work (with timeout)
            server.handle_request()
    
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # we heard you!
        dprint(__name__, 0,"^C received.")
    finally:
        dprint(__name__, 0, "Shutting down.")
        server.socket.close()



if __name__=="__main__":
    cmdPipe = Pipe()
    
    cfg = Settings.CSettings()
    param = {}
    param['CSettings'] = cfg
    
    param['IP_self'] = '192.168.178.20'  # IP_self?
    param['baseURL'] = 'http://'+ param['IP_self'] +':'+ cfg.getSetting('port_webserver')
    param['HostToIntercept'] = 'trailers.apple.com'
    
    if len(sys.argv)==1:
        Run(cmdPipe[1], param)
    elif len(sys.argv)==2 and sys.argv[1]=='SSL':
        Run_SSL(cmdPipe[1], param)

########NEW FILE########
__FILENAME__ = XMLConverter
#!/usr/bin/env python

"""
Sources:

ElementTree
http://docs.python.org/2/library/xml.etree.elementtree.html#xml.etree.ElementTree.SubElement

trailers.apple.com root URL
http://trailers.apple.com/appletv/us/js/application.js
navigation pane
http://trailers.apple.com/appletv/us/nav.xml
->top trailers: http://trailers.apple.com/appletv/us/index.xml
->calendar:     http://trailers.apple.com/appletv/us/calendar.xml
->browse:       http://trailers.apple.com/appletv/us/browse.xml
"""


import os
import sys
import traceback
import inspect 
import string, cgi, time
import copy  # deepcopy()

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

import time, uuid, hmac, hashlib, base64
from urllib import quote_plus
import urllib2
import urlparse

from Version import __VERSION__  # for {{EVAL()}}, display in settings page
import Settings, ATVSettings
import PlexAPI
from Debug import *  # dprint(), prettyXML()
import Localize



g_param = {}
def setParams(param):
    global g_param
    g_param = param

g_ATVSettings = None
def setATVSettings(cfg):
    global g_ATVSettings
    g_ATVSettings = cfg



# links to CMD class for module wide usage
g_CommandCollection = None



"""
# aTV XML ErrorMessage - hardcoded XML File
"""
def XML_Error(title, desc):
    errorXML = '\
<?xml version="1.0" encoding="UTF-8"?>\n\
<atv>\n\
    <body>\n\
        <dialog id="com.sample.error-dialog">\n\
            <title>' + title + '</title>\n\
            <description>' + desc + '</description>\n\
        </dialog>\n\
    </body>\n\
</atv>\n\
';
    return errorXML



def XML_PlayVideo_ChannelsV1(baseURL, path):
    XML = '\
<atv>\n\
  <body>\n\
    <videoPlayer id="com.sample.video-player">\n\
      <httpFileVideoAsset id="' + path + '">\n\
        <mediaURL>' + baseURL + path + '</mediaURL>\n\
        <title>*title*</title>\n\
        <!--bookmarkTime>{{EVAL(int({{VAL(Video/viewOffset:0)}}/1000))}}</bookmarkTime-->\n\
        <myMetadata>\n\
          <!-- PMS, OSD settings, ... -->\n\
          <baseURL>' + baseURL + '</baseURL>\n\
          <accessToken></accessToken>\n\
          <key></key>\n\
          <ratingKey></ratingKey>\n\
          <duration></duration>\n\
          <showClock>False</showClock>\n\
          <timeFormat></timeFormat>\n\
          <clockPosition></clockPosition>\n\
          <overscanAdjust></overscanAdjust>\n\
          <showEndtime>False</showEndtime>\n\
          <subtitleURL></subtitleURL>\n\
          <subtitleSize></subtitleSize>\n\
        </myMetadata>\n\
      </httpFileVideoAsset>\n\
    </videoPlayer>\n\
  </body>\n\
</atv>\n\
';
    dprint(__name__,2 , XML)
    return XML



"""
global list of known aTVs - to look up UDID by IP if needed

parameters:
    udid - from options['PlexConnectUDID']
    ip - from client_address btw options['aTVAddress']
"""
g_ATVList = {}

def declareATV(udid, ip):
    global g_ATVList
    if udid in g_ATVList:
        g_ATVList[udid]['ip'] = ip
    else:
        g_ATVList[udid] = {'ip': ip}

def getATVFromIP(ip):
    # find aTV by IP, return UDID
    for udid in g_ATVList:
        if ip==g_ATVList[udid].get('ip', None):
            return udid
    return None  # IP not found



"""
# XML converter functions
# - translate aTV request and send to PMS
# - receive reply from PMS
# - select XML template
# - translate to aTV XML
"""
def XML_PMS2aTV(PMS_address, path, options):
    # double check aTV UDID, redo from client IP if needed/possible
    if not 'PlexConnectUDID' in options:
        UDID = getATVFromIP(options['aTVAddress'])
        if UDID:
            options['PlexConnectUDID'] = UDID
        else:
            # aTV unidentified, UDID not known    
            return XML_Error('PlexConnect','Unexpected error - unidentified ATV')
    else:
        declareATV(options['PlexConnectUDID'], options['aTVAddress'])  # update with latest info
    
    UDID = options['PlexConnectUDID']
    
    # determine PMS_uuid, PMSBaseURL from IP (PMS_mark)
    PMS_uuid = PlexAPI.getPMSFromAddress(UDID, PMS_address)
    PMS_baseURL = PlexAPI.getPMSProperty(UDID, PMS_uuid, 'baseURL')
    
    # check cmd to work on
    cmd = ''
    channelsearchURL = ''
    if 'PlexConnect' in options:
        cmd = options['PlexConnect']
    
    if 'PlexConnectChannelsSearch' in options:
        channelsearchURL = options['PlexConnectChannelsSearch'].replace('+amp+', '&')
     
    dprint(__name__, 1, "PlexConnect Cmd: " + cmd)
    dprint(__name__, 1, "PlexConnectChannelsSearch: " + channelsearchURL)
    
    # check aTV language setting
    if not 'aTVLanguage' in options:
        dprint(__name__, 1, "no aTVLanguage - pick en")
        options['aTVLanguage'] = 'en'
    
    # XML Template selector
    # - PlexConnect command
    # - path
    # - PMS ViewGroup
    XMLtemplate = ''
    PMS = None
    PMSroot = None
    
    # XML direct request or
    # XMLtemplate defined by solely PlexConnect Cmd
    if path.endswith(".xml"):
        XMLtemplate = path.lstrip('/')
        path = ''  # clear path - we don't need PMS-XML
    
    elif cmd=='ChannelsSearch':
        XMLtemplate = 'ChannelsSearch.xml'
        path = ''
        
    elif cmd=='Play':
        XMLtemplate = 'PlayVideo.xml'
    
    elif cmd=='PlayVideo_ChannelsV1':
        dprint(__name__, 1, "playing Channels XML Version 1: {0}".format(path))
        auth_token = PlexAPI.getPMSProperty(UDID, PMS_uuid, 'accesstoken')
        path = PlexAPI.getDirectVideoPath(path, auth_token)
        return XML_PlayVideo_ChannelsV1(PMS_baseURL, path)  # direct link, no PMS XML available
    
    elif cmd=='PlayTrailer':
        trailerID = options['PlexConnectTrailerID']
        info = urllib2.urlopen("http://youtube.com/get_video_info?video_id=" + trailerID).read()
        parsed = urlparse.parse_qs(info)
        
        key = 'url_encoded_fmt_stream_map'
        if not key in parsed:
            return XML_Error('PlexConnect', 'Youtube: No Trailer Info available')
        streams = parsed[key][0].split(',')
        
        url = ''
        for i in range(len(streams)):
            stream = urlparse.parse_qs(streams[i])
            if stream['itag'][0] == '18':
                url = stream['url'][0]
        if url == '':
            return XML_Error('PlexConnect','Youtube: ATV compatible Trailer not available')
        
        return XML_PlayVideo_ChannelsV1('', url.replace('&','&amp;'))

    elif cmd=='ScrobbleMenu':
        XMLtemplate = 'ScrobbleMenu.xml'

    elif cmd=='ScrobbleMenuVideo':
        XMLtemplate = 'ScrobbleMenuVideo.xml'

    elif cmd=='ScrobbleMenuTVOnDeck':
        XMLtemplate = 'ScrobbleMenuTVOnDeck.xml'
        
    elif cmd=='ChangeShowArtwork':
        XMLtemplate = 'ChangeShowArtwork.xml'

    elif cmd=='ChangeSingleArtwork':
        XMLtemplate = 'ChangeSingleArtwork.xml'

    elif cmd=='ChangeSingleArtworkVideo':
        XMLtemplate = 'ChangeSingleArtworkVideo.xml'
        
    elif cmd=='PhotoBrowser':
        XMLtemplate = 'Photo_Browser.xml'
        
    elif cmd=='MoviePreview':
        XMLtemplate = 'MoviePreview.xml'
    
    elif cmd=='HomeVideoPrePlay':
        XMLtemplate = 'HomeVideoPrePlay.xml'
        
    elif cmd=='MoviePrePlay':
        XMLtemplate = 'MoviePrePlay.xml'

    elif cmd=='EpisodePrePlay':
        XMLtemplate = 'EpisodePrePlay.xml'
        
    elif cmd=='ChannelPrePlay':
        XMLtemplate = 'ChannelPrePlay.xml'
    
    elif cmd=='ChannelsVideo':
        XMLtemplate = 'ChannelsVideo.xml'

    elif cmd=='ByFolder':
        XMLtemplate = 'ByFolder.xml'

    elif cmd=='HomeVideoByFolder':
        XMLtemplate = 'HomeVideoByFolder.xml'

    elif cmd == 'HomeVideoDirectory':
        XMLtemplate = 'HomeVideoDirectory.xml'

    elif cmd=='MovieByFolder':
        XMLtemplate = 'MovieByFolder.xml'

    elif cmd == 'MovieDirectory':
        XMLtemplate = 'MovieDirectory.xml'

    elif cmd == 'MovieSection':
        XMLtemplate = 'MovieSection.xml'
    
    elif cmd == 'HomeVideoSection':
        XMLtemplate = 'HomeVideoSection.xml'
        
    elif cmd == 'TVSection':
        XMLtemplate = 'TVSection.xml'
    
    elif cmd.find('SectionPreview') != -1:
        XMLtemplate = cmd + '.xml'
    
    elif cmd == 'AllMovies':
        XMLtemplate = 'Movie_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'movieview').replace(' ','')+'.xml'  
    
    elif cmd == 'AllHomeVideos':
        XMLtemplate = 'HomeVideo_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'homevideoview').replace(' ','')+'.xml'  
        
    elif cmd == 'MovieSecondary':
        XMLtemplate = 'MovieSecondary.xml'
    
    elif cmd == 'AllShows':
        XMLtemplate = 'Show_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'showview').replace(' ','')+'.xml'  
          
    elif cmd == 'TVSecondary':
        XMLtemplate = 'TVSecondary.xml'
        
    elif cmd == 'PhotoSecondary':
        XMLtemplate = 'PhotoSecondary.xml'
        
    elif cmd == 'Directory':
        XMLtemplate = 'Directory.xml'
    
    elif cmd == 'DirectoryWithPreview':
        XMLtemplate = 'DirectoryWithPreview.xml'

    elif cmd == 'DirectoryWithPreviewActors':
        XMLtemplate = 'DirectoryWithPreviewActors.xml'
            
    elif cmd=='Settings':
        XMLtemplate = 'Settings.xml'
        path = ''  # clear path - we don't need PMS-XML
    
    elif cmd=='SettingsVideoOSD':
        XMLtemplate = 'Settings_VideoOSD.xml'
        path = ''  # clear path - we don't need PMS-XML
    
    elif cmd=='SettingsMovies':
        XMLtemplate = 'Settings_Movies.xml'
        path = ''  # clear path - we don't need PMS-XML
        
    elif cmd=='SettingsTVShows':
        XMLtemplate = 'Settings_TVShows.xml'
        path = ''  # clear path - we don't need PMS-XML
 
    elif cmd=='SettingsHomeVideos':
        XMLtemplate = 'Settings_HomeVideos.xml'
        path = ''  # clear path - we don't need PMS-XML

    elif cmd=='SettingsTopLevel':
        XMLtemplate = 'Settings_TopLevel.xml'
        path = ''  # clear path - we don't need PMS-XML
        
    elif cmd.startswith('SettingsToggle:'):
        opt = cmd[len('SettingsToggle:'):]  # cut command:
        parts = opt.split('+')
        g_ATVSettings.toggleSetting(options['PlexConnectUDID'], parts[0].lower())
        XMLtemplate = parts[1] + ".xml"
        dprint(__name__, 2, "ATVSettings->Toggle: {0} in template: {1}", parts[0], parts[1])
        
        path = ''  # clear path - we don't need PMS-XML
        
    elif cmd==('MyPlexLogin'):
        dprint(__name__, 2, "MyPlex->Logging In...")
        if not 'PlexConnectCredentials' in options:
            return XML_Error('PlexConnect', 'MyPlex Sign In called without Credentials.')
        
        parts = options['PlexConnectCredentials'].split(':',1)        
        (username, auth_token) = PlexAPI.MyPlexSignIn(parts[0], parts[1], options)
        
        g_ATVSettings.setSetting(UDID, 'myplex_user', username)
        g_ATVSettings.setSetting(UDID, 'myplex_auth', auth_token)
        
        XMLtemplate = 'Settings.xml'
        path = ''  # clear path - we don't need PMS-XML
    
    elif cmd=='MyPlexLogout':
        dprint(__name__, 2, "MyPlex->Logging Out...")
        
        auth_token = g_ATVSettings.getSetting(UDID, 'myplex_auth')
        PlexAPI.MyPlexSignOut(auth_token)
        
        g_ATVSettings.setSetting(UDID, 'myplex_user', '')
        g_ATVSettings.setSetting(UDID, 'myplex_auth', '')
        
        XMLtemplate = 'Settings.xml'
        path = ''  # clear path - we don't need PMS-XML
    
    elif cmd.startswith('Discover'):
        auth_token = g_ATVSettings.getSetting(UDID, 'myplex_auth')
        PlexAPI.discoverPMS(UDID, g_param['CSettings'], auth_token)
        
        return XML_Error('PlexConnect', 'Discover!')  # not an error - but aTV won't care anyways.
    
    elif path.startswith('/search?'):
        XMLtemplate = 'Search_Results.xml'
    
    elif path.find('serviceSearch') != -1 or (path.find('video') != -1 and path.lower().find('search') != -1):
        XMLtemplate = 'ChannelsVideoSearchResults.xml'
    
    elif path.find('SearchResults') != -1:
        XMLtemplate = 'ChannelsVideoSearchResults.xml'
        
    elif path=='/library/sections':  # from PlexConnect.xml -> for //local, //myplex
        XMLtemplate = 'Library.xml'
    
    elif path=='/channels/all':
        XMLtemplate = 'Channel_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'channelview')+'.xml'
        path = ''
    
    # request PMS XML
    if not path=='':
        if PMS_address[0].isalpha():  # owned, shared
            type = PMS_address
            PMS = PlexAPI.getXMLFromMultiplePMS(UDID, path, type, options)
        else:  # IP
            auth_token = PlexAPI.getPMSProperty(UDID, PMS_uuid, 'accesstoken')
            PMS = PlexAPI.getXMLFromPMS(PMS_baseURL, path, options, authtoken=auth_token)
        
        if PMS==False:
            return XML_Error('PlexConnect', 'No Response from Plex Media Server')
        
        PMSroot = PMS.getroot()
        
        dprint(__name__, 1, "viewGroup: "+PMSroot.get('viewGroup','None'))
    
    # XMLtemplate defined by PMS XML content
    if path=='':
        pass  # nothing to load
    
    elif not XMLtemplate=='':
        pass  # template already selected

    elif PMSroot.get('viewGroup','')=="secondary" and (PMSroot.get('art','').find('video') != -1 or PMSroot.get('thumb','').find('video') != -1):
        XMLtemplate = 'HomeVideoSectionTopLevel.xml'

    elif PMSroot.get('viewGroup','')=="secondary" and (PMSroot.get('art','').find('movie') != -1 or PMSroot.get('thumb','').find('movie') != -1):
        XMLtemplate = 'MovieSectionTopLevel.xml'
    
    elif PMSroot.get('viewGroup','')=="secondary" and (PMSroot.get('art','').find('show') != -1 or PMSroot.get('thumb','').find('show') != -1):
        XMLtemplate = 'TVSectionTopLevel.xml'
        
    elif PMSroot.get('viewGroup','')=="secondary" and (PMSroot.get('art','').find('photo') != -1 or PMSroot.get('thumb','').find('photo') != -1):
        XMLtemplate = 'PhotoSectionTopLevel.xml'
        
    elif PMSroot.get('viewGroup','')=="secondary":
        XMLtemplate = 'Directory.xml'
    
    elif PMSroot.get('viewGroup','')=='show':
        if PMSroot.get('title2')=='By Folder':
          # By Folder View
          XMLtemplate = 'ByFolder.xml'
        else:
          # TV Show grid view
          XMLtemplate = 'Show_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'showview')+'.xml'
        
    elif PMSroot.get('viewGroup','')=='season':
        # TV Season view
        XMLtemplate = 'Season_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'seasonview')+'.xml'

    elif PMSroot.get('viewGroup','')=='movie' and PMSroot.get('thumb','').find('video') != -1:
        if PMSroot.get('title2')=='By Folder':
          # By Folder View
          XMLtemplate = 'HomeVideoByFolder.xml'
        else:
          # Home Video listing
          XMLtemplate = 'HomeVideo_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'homevideoview').replace(' ','')+'.xml'
    
    elif PMSroot.get('viewGroup','')=='movie' and PMSroot.get('thumb','').find('movie') != -1:
        if PMSroot.get('title2')=='By Folder':
          # By Folder View
          XMLtemplate = 'MovieByFolder.xml'
        else:
          # Movie listing
          XMLtemplate = 'Movie_'+g_ATVSettings.getSetting(options['PlexConnectUDID'], 'homevideoview').replace(' ','')+'.xml'
          
    elif PMSroot.get('viewGroup','')=='track':
        XMLtemplate = 'Music_Track.xml'
   
    elif PMSroot.get('viewGroup','')=='episode':
        if PMSroot.get('title2')=='On Deck' or \
           PMSroot.get('title2')=='Recently Viewed Episodes' or \
           PMSroot.get('title2')=='Recently Aired' or \
           PMSroot.get('title2')=='Recently Added':
            # TV On Deck View
            XMLtemplate = 'TV_OnDeck.xml'
        else:
            # TV Episode view
            XMLtemplate = 'Episode.xml'
    
    elif PMSroot.get('viewGroup','')=='photo' or \
       path.startswith('/photos') or \
       PMSroot.find('Photo')!=None:
        if PMSroot.find('Directory')==None:
            # Photos only - directly show
            XMLtemplate = 'Photo_Browser.xml'
        else:
            # Photo listing / directory
            XMLtemplate = 'Photo_Directories.xml'
    
    else:
        XMLtemplate = 'Directory.xml'
    
    dprint(__name__, 1, "XMLTemplate: "+XMLtemplate)

    # get XMLtemplate
    aTVTree = etree.parse(sys.path[0]+'/assets/templates/'+XMLtemplate)
    aTVroot = aTVTree.getroot()
    
    # convert PMS XML to aTV XML using provided XMLtemplate
    global g_CommandCollection
    g_CommandCollection = CCommandCollection(options, PMSroot, PMS_address, path)
    XML_ExpandTree(aTVroot, PMSroot, 'main')
    XML_ExpandAllAttrib(aTVroot, PMSroot, 'main')
    del g_CommandCollection
    
    if cmd=='ChannelsSearch':
        for bURL in aTVroot.iter('baseURL'):
            if channelsearchURL.find('?') == -1:
                bURL.text = channelsearchURL + '?query='
            else:
                bURL.text = channelsearchURL + '&query='
                
    dprint(__name__, 1, "====== generated aTV-XML ======")
    dprint(__name__, 1, prettyXML(aTVTree))
    dprint(__name__, 1, "====== aTV-XML finished ======")
    
    return etree.tostring(aTVroot)



def XML_ExpandTree(elem, src, srcXML):
    # unpack template 'COPY'/'CUT' command in children
    res = False
    while True:
        if list(elem)==[]:  # no sub-elements, stop recursion
            break
        
        for child in elem:
            res = XML_ExpandNode(elem, child, src, srcXML, 'TEXT')
            if res==True:  # tree modified: restart from 1st elem
                break  # "for child"
            
            # recurse into children
            XML_ExpandTree(child, src, srcXML)
            
            res = XML_ExpandNode(elem, child, src, srcXML, 'TAIL')
            if res==True:  # tree modified: restart from 1st elem
                break  # "for child"
        
        if res==False:  # complete tree parsed with no change, stop recursion
            break  # "while True"



def XML_ExpandNode(elem, child, src, srcXML, text_tail):
    if text_tail=='TEXT':  # read line from text or tail
        line = child.text
    elif text_tail=='TAIL':
        line = child.tail
    else:
        dprint(__name__, 0, "XML_ExpandNode - text_tail badly specified: {0}", text_tail)
        return False
    
    pos = 0
    while line!=None:
        cmd_start = line.find('{{',pos)
        cmd_end   = line.find('}}',pos)
        next_start = line.find('{{',cmd_start+2)
        while next_start!=-1 and next_start<cmd_end:
            cmd_end = line.find('}}',cmd_end+2)
            next_start = line.find('{{',next_start+2)
        if cmd_start==-1 or cmd_end==-1 or cmd_start>cmd_end:
            return False  # tree not touched, line unchanged
        
        dprint(__name__, 2, "XML_ExpandNode: {0}", line)
        
        cmd = line[cmd_start+2:cmd_end]
        if cmd[-1]!=')':
            dprint(__name__, 0, "XML_ExpandNode - closing bracket missing: {0} ", line)
        
        parts = cmd.split('(',1)
        cmd = parts[0]
        param = parts[1].strip(')')  # remove ending bracket
        param = XML_ExpandLine(src, srcXML, param)  # expand any attributes in the parameter
        
        res = False
        if hasattr(CCommandCollection, 'TREE_'+cmd):  # expand tree, work COPY, CUT
            line = line[:cmd_start] + line[cmd_end+2:]  # remove cmd from text and tail
            if text_tail=='TEXT':  
                child.text = line
            elif text_tail=='TAIL':
                child.tail = line
            
            try:
                res = getattr(g_CommandCollection, 'TREE_'+cmd)(elem, child, src, srcXML, param)
            except:
                dprint(__name__, 0, "XML_ExpandNode - Error in cmd {0}, line {1}\n{2}", cmd, line, traceback.format_exc())
            
            if res==True:
                return True  # tree modified, node added/removed: restart from 1st elem
        
        elif hasattr(CCommandCollection, 'ATTRIB_'+cmd):  # check other known cmds: VAL, EVAL...
            dprint(__name__, 2, "XML_ExpandNode - Stumbled over {0} in line {1}", cmd, line)
            pos = cmd_end
        else:
            dprint(__name__, 0, "XML_ExpandNode - Found unknown cmd {0} in line {1}", cmd, line)
            line = line[:cmd_start] + "((UNKNOWN:"+cmd+"))" + line[cmd_end+2:]  # mark unknown cmd in text or tail
            if text_tail=='TEXT':
                child.text = line
            elif text_tail=='TAIL':
                child.tail = line
    
    dprint(__name__, 2, "XML_ExpandNode: {0} - done", line)
    return False



def XML_ExpandAllAttrib(elem, src, srcXML):
    # unpack template commands in elem.text
    line = elem.text
    if line!=None:
        elem.text = XML_ExpandLine(src, srcXML, line.strip())
    
    # unpack template commands in elem.tail
    line = elem.tail
    if line!=None:
        elem.tail = XML_ExpandLine(src, srcXML, line.strip())
    
    # unpack template commands in elem.attrib.value
    for attrib in elem.attrib:
        line = elem.get(attrib)
        elem.set(attrib, XML_ExpandLine(src, srcXML, line.strip()))
    
    # recurse into children
    for el in elem:
        XML_ExpandAllAttrib(el, src, srcXML)



def XML_ExpandLine(src, srcXML, line):
    pos = 0
    while True:
        cmd_start = line.find('{{',pos)
        cmd_end   = line.find('}}',pos)
        next_start = line.find('{{',cmd_start+2)
        while next_start!=-1 and next_start<cmd_end:
            cmd_end = line.find('}}',cmd_end+2)
            next_start = line.find('{{',next_start+2)

        if cmd_start==-1 or cmd_end==-1 or cmd_start>cmd_end:
            break;
        
        dprint(__name__, 2, "XML_ExpandLine: {0}", line)
        
        cmd = line[cmd_start+2:cmd_end]
        if cmd[-1]!=')':
            dprint(__name__, 0, "XML_ExpandLine - closing bracket missing: {0} ", line)
        
        parts = cmd.split('(',1)
        cmd = parts[0]
        param = parts[1][:-1]  # remove ending bracket
        param = XML_ExpandLine(src, srcXML, param)  # expand any attributes in the parameter
        
        if hasattr(CCommandCollection, 'ATTRIB_'+cmd):  # expand line, work VAL, EVAL...
            
            try:
                res = getattr(g_CommandCollection, 'ATTRIB_'+cmd)(src, srcXML, param)
                line = line[:cmd_start] + res + line[cmd_end+2:]
                pos = cmd_start+len(res)
            except:
                dprint(__name__, 0, "XML_ExpandLine - Error in {0}\n{1}", line, traceback.format_exc())
                line = line[:cmd_start] + "((ERROR:"+cmd+"))" + line[cmd_end+2:]
        
        elif hasattr(CCommandCollection, 'TREE_'+cmd):  # check other known cmds: COPY, CUT
            dprint(__name__, 2, "XML_ExpandLine - stumbled over {0} in line {1}", cmd, line)
            pos = cmd_end
        else:
            dprint(__name__, 0, "XML_ExpandLine - Found unknown cmd {0} in line {1}", cmd, line)
            line = line[:cmd_start] + "((UNKNOWN:"+cmd+"))" + line[cmd_end+2:]    
        
        dprint(__name__, 2, "XML_ExpandLine: {0} - done", line)
    return line



"""
# Command expander classes
# CCommandHelper():
#     base class to the following, provides basic parsing & evaluation functions
# CCommandCollection():
#     cmds to set up sources (ADDXML, VAR)
#     cmds with effect on the tree structure (COPY, CUT) - must be expanded first
#     cmds dealing with single node keys, text, tail only (VAL, EVAL, ADDR_PMS ,...)
"""
class CCommandHelper():
    def __init__(self, options, PMSroot, PMS_address, path):
        self.options = options
        self.PMSroot = {'main': PMSroot}
        self.PMS_address = PMS_address  # default PMS if nothing else specified
        self.path = {'main': path}
        
        self.ATV_udid = options['PlexConnectUDID']
        self.PMS_uuid = PlexAPI.getPMSFromAddress(self.ATV_udid, PMS_address)
        self.PMS_baseURL = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'baseURL')
        self.variables = {}
    
    # internal helper functions
    def getParam(self, src, param):
        parts = param.split(':',1)
        param = parts[0]
        leftover=''
        if len(parts)>1:
            leftover = parts[1]
        
        param = param.replace('&col;',':')  # colon  # replace XML_template special chars
        param = param.replace('&ocb;','{')  # opening curly brace
        param = param.replace('&ccb;','}')  # closinging curly brace
        
        param = param.replace('&quot;','"')  # replace XML special chars
        param = param.replace('&apos;',"'")
        param = param.replace('&lt;','<')
        param = param.replace('&gt;','>')
        param = param.replace('&amp;','&')  # must be last
        
        dprint(__name__, 2, "CCmds_getParam: {0}, {1}", param, leftover)
        return [param, leftover]
    
    def getKey(self, src, srcXML, param):
        attrib, leftover = self.getParam(src, param)
        default, leftover = self.getParam(src, leftover)
        
        el, srcXML, attrib = self.getBase(src, srcXML, attrib)         
        
        # walk the path if neccessary
        while '/' in attrib and el!=None:
            parts = attrib.split('/',1)
            if parts[0].startswith('#'):  # internal variable in path
                el = el.find(self.variables[parts[0][1:]])
            elif parts[0].startswith('$'):  # setting
                el = el.find(g_ATVSettings.getSetting(self.ATV_udid, parts[0][1:]))
            elif parts[0].startswith('%'):  # PMS property
                el = el.find(PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, parts[0][1:]))
            else:
                el = el.find(parts[0])
            attrib = parts[1]
        
        # check element and get attribute
        if attrib.startswith('#'):  # internal variable
            res = self.variables[attrib[1:]]
            dfltd = False
        elif attrib.startswith('$'):  # setting
            res = g_ATVSettings.getSetting(self.ATV_udid, attrib[1:])
            dfltd = False
        elif attrib.startswith('%'):  # PMS property
            res = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, attrib[1:])
            dfltd = False
        elif attrib.startswith('^'):  # aTV property, http request options
            res = self.options[attrib[1:]]
            dfltd = False
        elif el!=None and attrib in el.attrib:
            res = el.get(attrib)
            dfltd = False
        
        else:  # path/attribute not found
            res = default
            dfltd = True
        
        dprint(__name__, 2, "CCmds_getKey: {0},{1},{2}", res, leftover,dfltd)
        return [res,leftover,dfltd]
    
    def getElement(self, src, srcXML, param):
        tag, leftover = self.getParam(src, param)
        
        el, srcXML, tag = self.getBase(src, srcXML, tag)
        
        # walk the path if neccessary
        while len(tag)>0:
            parts = tag.split('/',1)
            el = el.find(parts[0])
            if not '/' in tag or el==None:
                break
            tag = parts[1]
        return [el, leftover]
    
    def getBase(self, src, srcXML, param):
        # get base element
        if param.startswith('@'):  # redirect to additional XML
            parts = param.split('/',1)
            srcXML = parts[0][1:]
            src = self.PMSroot[srcXML]
            leftover=''
            if len(parts)>1:
                leftover = parts[1]
        elif param.startswith('/'):  # start at root
            src = self.PMSroot['main']
            leftover = param[1:]
        else:
            leftover = param
        
        return [src, srcXML, leftover]
    
    def getConversion(self, src, param):
        conv, leftover = self.getParam(src, param)
        
        # build conversion "dictionary"
        convlist = []
        if conv!='':
            parts = conv.split('|')
            for part in parts:
                convstr = part.split('=')
                convlist.append((convstr[0], convstr[1]))
        
        dprint(__name__, 2, "CCmds_getConversion: {0},{1}", convlist, leftover)
        return [convlist, leftover]
    
    def applyConversion(self, val, convlist):
        # apply string conversion            
        if convlist!=[]:
            for part in reversed(sorted(convlist)):
                if val>=part[0]:
                    val = part[1]
                    break
        
        dprint(__name__, 2, "CCmds_applyConversion: {0}", val)
        return val
    
    def applyMath(self, val, math, frmt):
        # apply math function - eval
        try:
            x = eval(val)
            if math!='':
                x = eval(math)
            val = ('{0'+frmt+'}').format(x)
        except:
            dprint(__name__, 0, "CCmds_applyMath: Error in math {0}, frmt {1}\n{2}", math, frmt, traceback.format_exc())
        # apply format specifier
        
        dprint(__name__, 2, "CCmds_applyMath: {0}", val)
        return val
    
    def _(self, msgid):
        return Localize.getTranslation(self.options['aTVLanguage']).ugettext(msgid)



class CCommandCollection(CCommandHelper):
    # XML TREE modifier commands
    # add new commands to this list!
    def TREE_COPY(self, elem, child, src, srcXML, param):
        tag, param_enbl = self.getParam(src, param)

        src, srcXML, tag = self.getBase(src, srcXML, tag)        
        
        # walk the src path if neccessary
        while '/' in tag and src!=None:
            parts = tag.split('/',1)
            src = src.find(parts[0])
            tag = parts[1]
        
        # find index of child in elem - to keep consistent order
        for ix, el in enumerate(list(elem)):
            if el==child:
                break
        
        # duplicate child and add to tree
        for elemSRC in src.findall(tag):
            key = 'COPY'
            if param_enbl!='':
                key, leftover, dfltd = self.getKey(elemSRC, srcXML, param_enbl)
                conv, leftover = self.getConversion(elemSRC, leftover)
                if not dfltd:
                    key = self.applyConversion(key, conv)
            
            if key:
                el = copy.deepcopy(child)
                XML_ExpandTree(el, elemSRC, srcXML)
                XML_ExpandAllAttrib(el, elemSRC, srcXML)
                
                if el.tag=='__COPY__':
                    for el_child in list(el):
                        elem.insert(ix, el_child)
                        ix += 1
                else:
                    elem.insert(ix, el)
                    ix += 1
        
        # remove template child
        elem.remove(child)
        return True  # tree modified, nodes updated: restart from 1st elem
    
    def TREE_CUT(self, elem, child, src, srcXML, param):
        key, leftover, dfltd = self.getKey(src, srcXML, param)
        conv, leftover = self.getConversion(src, leftover)
        if not dfltd:
            key = self.applyConversion(key, conv)
        if key:
            elem.remove(child)
            return True  # tree modified, node removed: restart from 1st elem
        else:
            return False  # tree unchanged
    
    def TREE_ADDXML(self, elem, child, src, srcXML, param):
        tag, leftover = self.getParam(src, param)
        key, leftover, dfltd = self.getKey(src, srcXML, leftover)
        
        PMS_address = self.PMS_address
        
        if key.startswith('//'):  # local servers signature
            pathstart = key.find('/',3)
            PMS_address= key[:pathstart]
            path = key[pathstart:]
        elif key.startswith('/'):  # internal full path.
            path = key
        #elif key.startswith('http://'):  # external address
        #    path = key
        elif key == '':  # internal path
            path = self.path[srcXML]
        else:  # internal path, add-on
            path = self.path[srcXML] + '/' + key
        
        if PMS_address[0].isalpha():  # owned, shared
            type = self.PMS_address
            PMS = PlexAPI.getXMLFromMultiplePMS(self.ATV_udid, path, type, self.options)
        else:  # IP
            auth_token = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'accesstoken')
            PMS = PlexAPI.getXMLFromPMS(self.PMS_baseURL, path, self.options, auth_token)
        
        self.PMSroot[tag] = PMS.getroot()  # store additional PMS XML
        self.path[tag] = path  # store base path
        
        return False  # tree unchanged (well, source tree yes. but that doesn't count...)
    
    def TREE_VAR(self, elem, child, src, srcXML, param):
        var, leftover = self.getParam(src, param)
        key, leftover, dfltd = self.getKey(src, srcXML, leftover)
        conv, leftover = self.getConversion(src, leftover)
        if not dfltd:
            key = self.applyConversion(key, conv)
        
        self.variables[var] = key
        return False  # tree unchanged
    
    
    # XML ATTRIB modifier commands
    # add new commands to this list!
    def ATTRIB_VAL(self, src, srcXML, param):
        key, leftover, dfltd = self.getKey(src, srcXML, param)
        conv, leftover = self.getConversion(src, leftover)
        if not dfltd:
            key = self.applyConversion(key, conv)
        return key
    
    def ATTRIB_EVAL(self, src, srcXML, param):
        return str(eval(param))

    def ATTRIB_SVAL(self, src, srcXML, param):
        key, leftover, dfltd = self.getKey(src, srcXML, param)
        conv, leftover = self.getConversion(src, leftover)
        if not dfltd:
            key = self.applyConversion(key, conv)
        return quote_plus(unicode(key).encode("utf-8"))

    def ATTRIB_SETTING(self, src, srcXML, param):
        opt, leftover = self.getParam(src, param)
        return g_ATVSettings.getSetting(self.ATV_udid, opt)
    
    def ATTRIB_ADDPATH(self, src, srcXML, param):
        addpath, leftover, dfltd = self.getKey(src, srcXML, param)
        if addpath.startswith('/'):
            res = addpath
        elif addpath == '':
            res = self.path[srcXML]
        else:
            res = self.path[srcXML]+'/'+addpath
        return res
    
    def ATTRIB_IMAGEURL(self, src, srcXML, param):
        key, leftover, dfltd = self.getKey(src, srcXML, param)
        width, leftover = self.getParam(src, leftover)
        height, leftover = self.getParam(src, leftover)
        if height=='':
            height = width
        
        PMS_uuid = self.PMS_uuid
        PMS_baseURL = self.PMS_baseURL
        cmd_start = key.find('PMS(')
        cmd_end = key.find(')', cmd_start)
        if cmd_start>-1 and cmd_end>-1 and cmd_end>cmd_start:
            PMS_address = key[cmd_start+4:cmd_end]
            PMS_uuid = PlexAPI.getPMSFromAddress(self.ATV_udid, PMS_address)
            PMS_baseURL = PlexAPI.getPMSProperty(self.ATV_udid, PMS_uuid, 'baseURL')
            key = key[cmd_end+1:]
        
        AuthToken = PlexAPI.getPMSProperty(self.ATV_udid, PMS_uuid, 'accesstoken')
        
        # transcoder action
        transcoderAction = g_ATVSettings.getSetting(self.ATV_udid, 'phototranscoderaction')
        
        # aTV native filetypes
        parts = key.rsplit('.',1)
        photoATVNative = parts[-1].lower() in ['jpg','jpeg','tif','tiff','gif','png']
        dprint(__name__, 2, "photo: ATVNative - {0}", photoATVNative)
        
        if width=='' and \
           transcoderAction=='Auto' and \
           photoATVNative:
            # direct play
            res = PlexAPI.getDirectImagePath(key, AuthToken)
        else:
            if width=='':
                width = 1920  # max for HDTV. Relate to aTV version? Increase for KenBurns effect?
            if height=='':
                height = 1080  # as above
            # request transcoding
            res = PlexAPI.getTranscodeImagePath(key, AuthToken, self.path[srcXML], width, height)
        
        if res.startswith('/'):  # internal full path.
            res = PMS_baseURL + res
        elif res.startswith('http://') or key.startswith('https://'):  # external address
            pass
        else:  # internal path, add-on
            res = PMS_baseURL + self.path[srcXML] + '/' + res
        
        dprint(__name__, 1, 'ImageURL: {0}', res)
        return res
    
    def ATTRIB_MUSICURL(self, src, srcXML, param):
        Track, leftover = self.getElement(src, srcXML, param)
        
        AuthToken = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'accesstoken')
        
        if not Track:
            # not a complete audio/track structure - take key directly and build direct-play path
            key, leftover, dfltd = self.getKey(src, srcXML, param)
            res = PlexAPI.getDirectAudioPath(key, AuthToken)
            res = PlexAPI.getURL(self.PMS_baseURL, self.path[srcXML], res)
            dprint(__name__, 1, 'MusicURL - direct: {0}', res)
            return res
        
        # complete track structure - request transcoding if needed
        Media = Track.find('Media')
        
        # check "Media" element and get key
        if Media!=None:
            # transcoder action setting?
            # transcoder bitrate setting [kbps] -  eg. 128, 256, 384, 512?
            maxAudioBitrate = '384'
            
            audioATVNative = \
                Media.get('audioCodec','-') in ("mp3", "aac", "ac3", "drms", "alac", "aiff", "wav")
            # check Media.get('container') as well - mp3, m4a, ...?
            
            dprint(__name__, 2, "audio: ATVNative - {0}", audioATVNative)
            
            if audioATVNative and\
               int(Media.get('bitrate','0')) < int(maxAudioBitrate):
                # direct play
                res, leftover, dfltd = self.getKey(Media, srcXML, 'Part/key')
                res = PlexAPI.getDirectAudioPath(res, AuthToken)
            else:
                # request transcoding
                res, leftover, dfltd = self.getKey(Track, srcXML, 'key')
                res = PlexAPI.getTranscodeAudioPath(res, AuthToken, self.options, maxAudioBitrate)
        
        else:
            dprint(__name__, 0, "MEDIAPATH - element not found: {0}", param)
            res = 'FILE_NOT_FOUND'  # not found?
        
        res = PlexAPI.getURL(self.PMS_baseURL, self.path[srcXML], res)
        dprint(__name__, 1, 'MusicURL: {0}', res)
        return res
    
    def ATTRIB_URL(self, src, srcXML, param):
        key, leftover, dfltd = self.getKey(src, srcXML, param)
        
        # compare PMS_mark in PlexAPI/getXMLFromMultiplePMS()
        PMS_mark = '/PMS(' + PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'ip') + ')'
        
        # overwrite with URL embedded PMS address
        cmd_start = key.find('PMS(')
        cmd_end = key.find(')', cmd_start)
        if cmd_start>-1 and cmd_end>-1 and cmd_end>cmd_start:
            PMS_mark = '/'+key[cmd_start:cmd_end+1]
            key = key[cmd_end+1:]
        
        res = g_param['baseURL']  # base address to PlexConnect
        
        if key.endswith('.js'):  # link to PlexConnect owned .js stuff
            res = res + key
        elif key.startswith('http://') or key.startswith('https://'):  # external server
            res = key
            """
            parts = urlparse.urlsplit(key)  # (scheme, networklocation, path, ...)
            key = urlparse.urlunsplit(('', '', parts[2], parts[3], parts[4]))  # keep path only
            PMS_uuid = PlexAPI.getPMSFromIP(g_param['PMS_list'], parts.hostname)
            PMSaddress = PlexAPI.getAddress(g_param['PMS_list'], PMS_uuid)  # get PMS address (might be local as well!?!)
            res = res + '/PMS(' + quote_plus(PMSaddress) + ')' + key
            """
        elif key.startswith('/'):  # internal full path.
            res = res + PMS_mark + key
        elif key == '':  # internal path
            res = res + PMS_mark + self.path[srcXML]
        else:  # internal path, add-on
            res = res + PMS_mark + self.path[srcXML] + '/' + key
        
        return res
    
    def ATTRIB_VIDEOURL(self, src, srcXML, param):
        Video, leftover = self.getElement(src, srcXML, param)
        
        AuthToken = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'accesstoken')
        
        if not Video:
            # not a complete video structure - take key directly and build direct-play path
            key, leftover, dfltd = self.getKey(src, srcXML, param)
            res = PlexAPI.getDirectVideoPath(key, AuthToken)
            res = PlexAPI.getURL(self.PMS_baseURL, self.path[srcXML], res)
            return res
        
        # complete video structure - request transcoding if needed
        Media = Video.find('Media')
        
        # check "Media" element and get key
        if Media!=None:
            # transcoder action
            transcoderAction = g_ATVSettings.getSetting(self.ATV_udid, 'transcoderaction')
            
            # video format
            #    HTTP live stream
            # or native aTV media
            videoATVNative = \
                Media.get('protocol','-') in ("hls") \
                or \
                Media.get('container','-') in ("mov", "mp4") and \
                Media.get('videoCodec','-') in ("mpeg4", "h264", "drmi") and \
                Media.get('audioCodec','-') in ("aac", "ac3", "drms")
            
            for Stream in Media.find('Part').findall('Stream'):
                if Stream.get('streamType','') == '1' and\
                   Stream.get('codec','-') in ("mpeg4", "h264"):
                    if Stream.get('profile', '-') == 'high 10' or \
                        int(Stream.get('refFrames','0')) > 8:
                            videoATVNative = False
                    break
            
            dprint(__name__, 2, "video: ATVNative - {0}", videoATVNative)
            
            # quality limits: quality=(resolution, quality, bitrate)
            qLookup = { '480p 2.0Mbps' :('720x480', '60', '2000'), \
                        '720p 3.0Mbps' :('1280x720', '75', '3000'), \
                        '720p 4.0Mbps' :('1280x720', '100', '4000'), \
                        '1080p 8.0Mbps' :('1920x1080', '60', '8000'), \
                        '1080p 10.0Mbps' :('1920x1080', '75', '10000'), \
                        '1080p 12.0Mbps' :('1920x1080', '90', '12000'), \
                        '1080p 20.0Mbps' :('1920x1080', '100', '20000'), \
                        '1080p 40.0Mbps' :('1920x1080', '100', '40000') }
            if PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'local')=='1':
                qLimits = qLookup[g_ATVSettings.getSetting(self.ATV_udid, 'transcodequality')]
            else:
                qLimits = qLookup[g_ATVSettings.getSetting(self.ATV_udid, 'remotebitrate')]
            
            # subtitle renderer, subtitle selection
            subtitleRenderer = g_ATVSettings.getSetting(self.ATV_udid, 'subtitlerenderer')
            
            subtitleId = ''
            subtitleKey = ''
            subtitleFormat = ''
            for Stream in Media.find('Part').findall('Stream'):  # Todo: check 'Part' existance, deal with multi part video
                if Stream.get('streamType','') == '3' and\
                   Stream.get('selected','0') == '1':
                    subtitleId = Stream.get('id','')
                    subtitleKey = Stream.get('key','')
                    subtitleFormat = Stream.get('format','')
                    break
            
            subtitleIOSNative = \
                subtitleKey=='' and subtitleFormat=="tx3g"  # embedded
            subtitlePlexConnect = \
                subtitleKey!='' and subtitleFormat=="srt"  # external
            
            # subtitle suitable for direct play?
            #    no subtitle
            # or 'Auto'    with subtitle by iOS or PlexConnect
            # or 'iOS,PMS' with subtitle by iOS
            subtitleDirectPlay = \
                subtitleId=='' \
                or \
                subtitleRenderer=='Auto' and \
                ( (videoATVNative and subtitleIOSNative) or subtitlePlexConnect ) \
                or \
                subtitleRenderer=='iOS, PMS' and \
                (videoATVNative and subtitleIOSNative)
            dprint(__name__, 2, "subtitle: IOSNative - {0}, PlexConnect - {1}, DirectPlay - {2}", subtitleIOSNative, subtitlePlexConnect, subtitleDirectPlay)
            
            # determine video URL
            if transcoderAction=='DirectPlay' \
               or \
               transcoderAction=='Auto' and \
               videoATVNative and \
               int(Media.get('bitrate','0')) < int(qLimits[2]) and \
               subtitleDirectPlay:
                # direct play for...
                #    force direct play
                # or videoATVNative (HTTP live stream m4v/h264/aac...)
                #    limited by quality setting
                #    with aTV supported subtitle (iOS embedded tx3g, PlexConnext external srt)
                res, leftover, dfltd = self.getKey(Media, srcXML, 'Part/key')
                
                if Media.get('indirect', False):  # indirect... todo: select suitable resolution, today we just take first Media
                    PMS = PlexAPI.getXMLFromPMS(self.PMS_baseURL, res, self.options, AuthToken)  # todo... check key for trailing '/' or even 'http'
                    res, leftover, dfltd = self.getKey(PMS.getroot(), srcXML, 'Video/Media/Part/key')
                
                res = PlexAPI.getDirectVideoPath(res, AuthToken)
            else:
                # request transcoding
                res = Video.get('key','')
                
                # misc settings: subtitlesize, audioboost
                subtitle = { 'selected': '1' if subtitleId else '0', \
                             'dontBurnIn': '1' if subtitleDirectPlay else '0', \
                             'size': g_ATVSettings.getSetting(self.ATV_udid, 'subtitlesize') }
                audio = { 'boost': g_ATVSettings.getSetting(self.ATV_udid, 'audioboost') }
                res = PlexAPI.getTranscodeVideoPath(res, AuthToken, self.options, transcoderAction, qLimits, subtitle, audio)
        
        else:
            dprint(__name__, 0, "MEDIAPATH - element not found: {0}", param)
            res = 'FILE_NOT_FOUND'  # not found?
        
        if res.startswith('/'):  # internal full path.
            res = self.PMS_baseURL + res
        elif res.startswith('http://') or res.startswith('https://'):  # external address
            pass
        else:  # internal path, add-on
            res = self.PMS_baseURL + self.path[srcXML] + res
        
        dprint(__name__, 1, 'VideoURL: {0}', res)
        return res
    
    def ATTRIB_episodestring(self, src, srcXML, param):
        parentIndex, leftover, dfltd = self.getKey(src, srcXML, param)  # getKey "defaults" if nothing found.
        index, leftover, dfltd = self.getKey(src, srcXML, leftover)
        title, leftover, dfltd = self.getKey(src, srcXML, leftover)
        out = self._("{0:0d}x{1:02d} {2}").format(int(parentIndex), int(index), title)
        return out
    
    def ATTRIB_getDurationString(self, src, srcXML, param):
        duration, leftover, dfltd = self.getKey(src, srcXML, param)
        min = int(duration)/1000/60
        if g_ATVSettings.getSetting(self.ATV_udid, 'durationformat') == 'Minutes':
            return self._("{0:d} Minutes").format(min)
        else:
            if len(duration) > 0:
                hour = min/60
                min = min%60
                if hour == 0: return self._("{0:d} Minutes").format(min)
                else: return self._("{0:d}hr {1:d}min").format(hour, min)
        return ""
    
    def ATTRIB_contentRating(self, src, srcXML, param):
        rating, leftover, dfltd = self.getKey(src, srcXML, param)
        if rating.find('/') != -1:
            parts = rating.split('/')
            return parts[1]
        else:
            return rating
        
    def ATTRIB_unwatchedCountGrid(self, src, srcXML, param):
        total, leftover, dfltd = self.getKey(src, srcXML, param)
        viewed, leftover, dfltd = self.getKey(src, srcXML, leftover)
        unwatched = int(total) - int(viewed)
        return str(unwatched)
    
    def ATTRIB_unwatchedCountList(self, src, srcXML, param):
        total, leftover, dfltd = self.getKey(src, srcXML, param)
        viewed, leftover, dfltd = self.getKey(src, srcXML, leftover)
        unwatched = int(total) - int(viewed)
        if unwatched > 0: return self._("{0} unwatched").format(unwatched)
        else: return ""
    
    def ATTRIB_TEXT(self, src, srcXML, param):
        return self._(param)
    
    def ATTRIB_PMSCOUNT(self, src, srcXML, param):
        return str(PlexAPI.getPMSCount(self.ATV_udid))
    
    def ATTRIB_PMSNAME(self, src, srcXML, param):
        PMS_name = PlexAPI.getPMSProperty(self.ATV_udid, self.PMS_uuid, 'name')
        if PMS_name=='':
            return "No Server in Proximity"
        else:
            return PMS_name



if __name__=="__main__":
    cfg = Settings.CSettings()
    param = {}
    param['CSettings'] = cfg
    
    param['HostToIntercept'] = 'trailers.apple.com'
    setParams(param)
    
    cfg = ATVSettings.CATVSettings()
    setATVSettings(cfg)
    
    print "load PMS XML"
    _XML = '<PMS number="1" string="Hello"> \
                <DATA number="42" string="World"></DATA> \
                <DATA string="Sun"></DATA> \
            </PMS>'
    PMSroot = etree.fromstring(_XML)
    PMSTree = etree.ElementTree(PMSroot)
    print prettyXML(PMSTree)
    
    print
    print "load aTV XML template"
    _XML = '<aTV> \
                <INFO num="{{VAL(number)}}" str="{{VAL(string)}}">Info</INFO> \
                <FILE str="{{VAL(string)}}" strconv="{{VAL(string::World=big|Moon=small|Sun=huge)}}" num="{{VAL(number:5)}}" numfunc="{{EVAL(int({{VAL(number:5)}}/10))}}"> \
                    File{{COPY(DATA)}} \
                </FILE> \
                <PATH path="{{ADDPATH(file:unknown)}}" /> \
                <accessories> \
                    <cut />{{CUT(number::0=cut|1=)}} \
                    <dontcut />{{CUT(attribnotfound)}} \
                </accessories> \
                <ADDPATH>{{ADDPATH(string)}}</ADDPATH> \
                <COPY2>={{COPY(DATA)}}=</COPY2> \
            </aTV>'
    aTVroot = etree.fromstring(_XML)
    aTVTree = etree.ElementTree(aTVroot)
    print prettyXML(aTVTree)
    
    print
    print "unpack PlexConnect COPY/CUT commands"
    options = {}
    options['PlexConnectUDID'] = '007'
    PMS_address = 'PMS_IP'
    g_CommandCollection = CCommandCollection(options, PMSroot, PMS_address, '/library/sections')
    XML_ExpandTree(aTVroot, PMSroot, 'main')
    XML_ExpandAllAttrib(aTVroot, PMSroot, 'main')
    del g_CommandCollection
    
    print
    print "resulting aTV XML"
    print prettyXML(aTVTree)
    
    print
    #print "store aTV XML"
    #str = prettyXML(aTVTree)
    #f=open(sys.path[0]+'/XML/aTV_fromTmpl.xml', 'w')
    #f.write(str)
    #f.close()
    
    del cfg

########NEW FILE########
