__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import socket
import struct
import sys
import base64

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None

        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header 
        for non-tunneling proxies if needed 
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)

        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies 
        (i.e. thos which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt: 
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))

        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  "CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n"
        headers += "Host: " + destaddr + "\r\n"
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += self.__getauthheader() + "\r\n"
        headers += "\r\n"
        self.sendall(headers.encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) != type('')) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                print "WARN: SSL connections (generally on port 443) require the use of tunneling - failing back to PROXY_TYPE_HTTP"
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = sgtimezone
#! /opt/local/bin/python
# ----------------------------------------------------------------------------
#  SG_TIMEZONE module
#  this is rolled into the this shotgun api file to avoid having to require 
#  current users of api2 to install new modules and modify PYTHONPATH info.
# ----------------------------------------------------------------------------

class SgTimezone(object):
    from datetime import tzinfo, timedelta, datetime
    import time as _time

    ZERO = timedelta(0)
    STDOFFSET = timedelta(seconds = -_time.timezone)
    if _time.daylight:
        DSTOFFSET = timedelta(seconds = -_time.altzone)
    else:
        DSTOFFSET = STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET
    
    def __init__(self): 
        self.utc = self.UTC()
        self.local = self.LocalTimezone()
    
    class UTC(tzinfo):
        
        def utcoffset(self, dt):
            return SgTimezone.ZERO
        
        def tzname(self, dt):
            return "UTC"
        
        def dst(self, dt):
            return SgTimezone.ZERO
    
    class LocalTimezone(tzinfo):
        
        def utcoffset(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTOFFSET
            else:
                return SgTimezone.STDOFFSET
        
        def dst(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTDIFF
            else:
                return SgTimezone.ZERO
        
        def tzname(self, dt):
            return _time.tzname[self._isdst(dt)]
        
        def _isdst(self, dt):
            tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
            import time as _time
            stamp = _time.mktime(tt)
            tt = _time.localtime(stamp)
            return tt.tm_isdst > 0


########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
import re
import sys
import struct

from simplejson.scanner import make_scanner
def _import_c_scanstring():
    try:
        from simplejson._speedups import scanstring
        return scanstring
    except ImportError:
        return None
c_scanstring = _import_c_scanstring()

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


class JSONDecodeError(ValueError):
    """Subclass of ValueError with the following additional properties:

    msg: The unformatted error message
    doc: The JSON document being parsed
    pos: The start index of doc where parsing failed
    end: The end index of doc where parsing failed (may be None)
    lineno: The line corresponding to pos
    colno: The column corresponding to pos
    endlineno: The line corresponding to end (may be None)
    endcolno: The column corresponding to end (may be None)

    """
    def __init__(self, msg, doc, pos, end=None):
        ValueError.__init__(self, errmsg(msg, doc, pos, end=end))
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.end = end
        self.lineno, self.colno = linecol(doc, pos)
        if end is not None:
            self.endlineno, self.endcolno = linecol(doc, end)
        else:
            self.endlineno, self.endcolno = None, None


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        #fmt = '{0}: line {1} column {2} (char {3})'
        #return fmt.format(msg, lineno, colno, pos)
        fmt = '%s: line %d column %d (char %d)'
        return fmt % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    #fmt = '{0}: line {1} column {2} - line {3} column {4} (char {5} - {6})'
    #return fmt.format(msg, lineno, colno, endlineno, endcolno, pos, end)
    fmt = '%s: line %d column %d - line %d column %d (char %d - %d)'
    return fmt % (msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True,
        _b=BACKSLASH, _m=STRINGCHUNK.match):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at" % (terminator,)
                #msg = "Invalid control character {0!r} at".format(terminator)
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\escape: " + repr(esc)
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            # Unicode escape sequence
            esc = s[end + 1:end + 5]
            next_end = end + 5
            if len(esc) != 4:
                msg = "Invalid \\uXXXX escape"
                raise JSONDecodeError(msg, s, end)
            uni = int(esc, 16)
            # Check for surrogate pair on UCS-4 systems
            if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                if not s[end + 5:end + 7] == '\\u':
                    raise JSONDecodeError(msg, s, end)
                esc2 = s[end + 7:end + 11]
                if len(esc2) != 4:
                    raise JSONDecodeError(msg, s, end)
                uni2 = int(esc2, 16)
                uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                next_end += 6
            char = unichr(uni)
            end = next_end
        # Append the unescaped character
        _append(char)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject((s, end), encoding, strict, scan_once, object_hook,
        object_pairs_hook, memo=None,
        _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    # Backwards compatibility
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    pairs = []
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return result, end + 1
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return pairs, end + 1
        elif nextchar != '"':
            raise JSONDecodeError("Expecting property name", s, end)
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)
        key = memo_get(key, key)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise JSONDecodeError("Expecting : delimiter", s, end)

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        pairs.append((key, value))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting , delimiter", s, end - 1)

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise JSONDecodeError("Expecting property name", s, end - 1)

    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return result, end
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray((s, end), scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting , delimiter", s, end)

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None):
        """
        *encoding* determines the encoding used to interpret any
        :class:`str` objects decoded by this instance (``'utf-8'`` by
        default).  It has no effect when decoding :class:`unicode` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as :class:`unicode`.

        *object_hook*, if specified, will be called with the result of every
        JSON object decoded and its return value will be used in place of the
        given :class:`dict`.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        *object_pairs_hook* is an optional function that will be called with
        the result of any object literal decode with an ordered list of pairs.
        The return value of *object_pairs_hook* will be used instead of the
        :class:`dict`.  This feature can be used to implement custom decoders
        that rely on the order that the key and value pairs are decoded (for
        example, :func:`collections.OrderedDict` will remember the order of
        insertion). If *object_hook* is also defined, the *object_pairs_hook*
        takes priority.

        *parse_float*, if specified, will be called with the string of every
        JSON float to be decoded.  By default, this is equivalent to
        ``float(num_str)``. This can be used to use another datatype or parser
        for JSON floats (e.g. :class:`decimal.Decimal`).

        *parse_int*, if specified, will be called with the string of every
        JSON int to be decoded.  By default, this is equivalent to
        ``int(num_str)``.  This can be used to use another datatype or parser
        for JSON integers (e.g. :class:`float`).

        *parse_constant*, if specified, will be called with one of the
        following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
        can be used to raise an exception if invalid JSON numbers are
        encountered.

        *strict* controls the parser's behavior when it encounters an
        invalid control character in a string. The default setting of
        ``True`` means that unescaped control characters are parse errors, if
        ``False`` then control characters will be allowed in strings.

        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.memo = {}
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end, len(s))
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode``
        beginning with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        try:
            obj, end = self.scan_once(s, idx)
        except StopIteration:
            raise JSONDecodeError("No JSON object could be decoded", s, idx)
        return obj, end

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
import re
from decimal import Decimal

def _import_speedups():
    try:
        from simplejson import _speedups
        return _speedups.encode_basestring_ascii, _speedups.make_encoder
    except ImportError:
        return None, None
c_encode_basestring_ascii, c_make_encoder = _import_speedups()

from simplejson.decoder import PosInf

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    #ESCAPE_DCT.setdefault(chr(i), '\\u{0:04x}'.format(i))
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

FLOAT_REPR = repr

def encode_basestring(s):
    """Return a JSON representation of a Python string

    """
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return u'"' + ESCAPE.sub(replace, s) + u'"'


def py_encode_basestring_ascii(s):
    """Return an ASCII-only JSON representation of a Python string

    """
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                #return '\\u{0:04x}'.format(n)
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                #return '\\u{0:04x}\\u{1:04x}'.format(s1, s2)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = (
    c_encode_basestring_ascii or py_encode_basestring_ascii)

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None,
            use_decimal=False):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is true, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is true, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a string, then JSON array elements and object members
        will be pretty-printed with a newline followed by that string repeated
        for each level of nesting. ``None`` (the default) selects the most compact
        representation without any newlines. For backwards compatibility with
        versions of simplejson earlier than 2.1.0, an integer is also accepted
        and is converted to a string with that many spaces.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        If use_decimal is true (not the default), ``decimal.Decimal`` will
        be supported directly by the encoder. For the inverse, decode JSON
        with ``parse_float=decimal.Decimal``.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.use_decimal = use_decimal
        if isinstance(indent, (int, long)):
            indent = ' ' * indent
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        elif indent is not None:
            self.item_separator = ','
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError(repr(o) + " is not JSON serializable")

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> from simplejson import JSONEncoder
        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, str):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan,
                _repr=FLOAT_REPR, _inf=PosInf, _neginf=-PosInf):
            # Check for specials. Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on
            # the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text


        key_memo = {}
        if (_one_shot and c_make_encoder is not None
                and self.indent is None):
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan, key_memo, self.use_decimal)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot, self.use_decimal)
        try:
            return _iterencode(o, 0)
        finally:
            key_memo.clear()


class JSONEncoderForHTML(JSONEncoder):
    """An encoder that produces JSON safe to embed in HTML.

    To embed JSON content in, say, a script tag on a web page, the
    characters &, < and > should be escaped. They cannot be escaped
    with the usual entities (e.g. &amp;) because they are not expanded
    within <script> tags.
    """

    def encode(self, o):
        # Override JSONEncoder.encode because it has hacks for
        # performance that make things more complicated.
        chunks = self.iterencode(o, True)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        chunks = super(JSONEncoderForHTML, self).iterencode(o, _one_shot)
        for chunk in chunks:
            chunk = chunk.replace('&', '\\u0026')
            chunk = chunk.replace('<', '\\u003c')
            chunk = chunk.replace('>', '\\u003e')
            yield chunk


def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
        _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        _use_decimal,
        ## HACK: hand-optimized bytecode; turn globals into locals
        False=False,
        True=True,
        ValueError=ValueError,
        basestring=basestring,
        Decimal=Decimal,
        dict=dict,
        float=float,
        id=id,
        int=int,
        isinstance=isinstance,
        list=list,
        long=long,
        str=str,
        tuple=tuple,
    ):

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, basestring):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, (int, long)):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield buf + str(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = dct.items()
            items.sort(key=lambda kv: kv[0])
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif isinstance(key, (int, long)):
                key = str(key)
            elif _skipkeys:
                continue
            else:
                raise TypeError("key " + repr(key) + " is not a string")
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, basestring):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, (int, long)):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield str(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, basestring):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        elif _use_decimal and isinstance(o, Decimal):
            yield str(o)
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = ordered_dict
"""Drop-in replacement for collections.OrderedDict by Raymond Hettinger

http://code.activestate.com/recipes/576693/

"""
from UserDict import DictMixin

# Modified from original to support Python 2.4, see
# http://code.google.com/p/simplejson/issues/detail?id=53
try:
    all
except NameError:
    def all(seq):
        for elem in seq:
            if not elem:
                return False
        return True

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
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
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
        # Modified from original to support Python 2.4, see
        # http://code.google.com/p/simplejson/issues/detail?id=53
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
                   all(p==q for p, q in  zip(self.items(), other.items()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
def _import_c_make_scanner():
    try:
        from simplejson._speedups import make_scanner
        return make_scanner
    except ImportError:
        return None
c_make_scanner = _import_c_make_scanner()

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict,
                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = tool
r"""Command-line tool to validate and pretty-print JSON

Usage::

    $ echo '{"json":"obj"}' | python -m simplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m simplejson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import sys
import simplejson as json

def main():
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit(sys.argv[0] + " [infile [outfile]]")
    try:
        obj = json.load(infile,
                        object_pairs_hook=json.OrderedDict,
                        use_decimal=True)
    except ValueError, e:
        raise SystemExit(e)
    json.dump(obj, outfile, sort_keys=True, indent='    ', use_decimal=True)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = xmlrpclib
#! /opt/local/bin/python
 
# XML-RPC CLIENT LIBRARY
# $Id: xmlrpclib.py 41594 2005-12-04 19:11:17Z andrew.kuchling $
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Notes:
# this version is designed to work with Python 2.1 or newer.
#
# History:
# 1999-01-14 fl  Created
# 1999-01-15 fl  Changed dateTime to use localtime
# 1999-01-16 fl  Added Binary/base64 element, default to RPC2 service
# 1999-01-19 fl  Fixed array data element (from Skip Montanaro)
# 1999-01-21 fl  Fixed dateTime constructor, etc.
# 1999-02-02 fl  Added fault handling, handle empty sequences, etc.
# 1999-02-10 fl  Fixed problem with empty responses (from Skip Montanaro)
# 1999-06-20 fl  Speed improvements, pluggable parsers/transports (0.9.8)
# 2000-11-28 fl  Changed boolean to check the truth value of its argument
# 2001-02-24 fl  Added encoding/Unicode/SafeTransport patches
# 2001-02-26 fl  Added compare support to wrappers (0.9.9/1.0b1)
# 2001-03-28 fl  Make sure response tuple is a singleton
# 2001-03-29 fl  Don't require empty params element (from Nicholas Riley)
# 2001-06-10 fl  Folded in _xmlrpclib accelerator support (1.0b2)
# 2001-08-20 fl  Base xmlrpclib.Error on built-in Exception (from Paul Prescod)
# 2001-09-03 fl  Allow Transport subclass to override getparser
# 2001-09-10 fl  Lazy import of urllib, cgi, xmllib (20x import speedup)
# 2001-10-01 fl  Remove containers from memo cache when done with them
# 2001-10-01 fl  Use faster escape method (80% dumps speedup)
# 2001-10-02 fl  More dumps microtuning
# 2001-10-04 fl  Make sure import expat gets a parser (from Guido van Rossum)
# 2001-10-10 sm  Allow long ints to be passed as ints if they don't overflow
# 2001-10-17 sm  Test for int and long overflow (allows use on 64-bit systems)
# 2001-11-12 fl  Use repr() to marshal doubles (from Paul Felix)
# 2002-03-17 fl  Avoid buffered read when possible (from James Rucker)
# 2002-04-07 fl  Added pythondoc comments
# 2002-04-16 fl  Added __str__ methods to datetime/binary wrappers
# 2002-05-15 fl  Added error constants (from Andrew Kuchling)
# 2002-06-27 fl  Merged with Python CVS version
# 2002-10-22 fl  Added basic authentication (based on code from Phillip Eby)
# 2003-01-22 sm  Add support for the bool type
# 2003-02-27 gvr Remove apply calls
# 2003-04-24 sm  Use cStringIO if available
# 2003-04-25 ak  Add support for nil
# 2003-06-15 gn  Add support for time.struct_time
# 2003-07-12 gp  Correct marshalling of Faults
# 2003-10-31 mvl Add multicall support
# 2004-08-20 mvl Bump minimum supported Python version to 2.1
#
# Copyright (c) 1999-2002 by Secret Labs AB.
# Copyright (c) 1999-2002 by Fredrik Lundh.
#
# info@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The XML-RPC client interface is
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

#
# things to look into some day:

# TODO: sort out True/False/boolean issues for Python 2.3

"""
An XML-RPC client interface for Python.

The marshalling and response parser code can also be used to
implement XML-RPC servers.

Exported exceptions:
  
  Error          Base class for client errors
  ProtocolError  Indicates an HTTP protocol error
  ResponseError  Indicates a broken response package
  Fault          Indicates an XML-RPC fault package

Exported classes:
  
  ServerProxy    Represents a logical connection to an XML-RPC server
  
  MultiCall      Executor of boxcared xmlrpc requests
  Boolean        boolean wrapper to generate a "boolean" XML-RPC value
  DateTime       dateTime wrapper for an ISO 8601 string or time tuple or
                 localtime integer value to generate a "dateTime.iso8601"
                 XML-RPC value
  Binary         binary data wrapper
  
  SlowParser     Slow but safe standard parser (based on xmllib)
  Marshaller     Generate an XML-RPC params chunk from a Python data structure
  Unmarshaller   Unmarshal an XML-RPC response from incoming XML event message
  Transport      Handles an HTTP transaction to an XML-RPC server
  SafeTransport  Handles an HTTPS transaction to an XML-RPC server

Exported constants:
  
  True
  False

Exported functions:
  
  boolean        Convert any Python value to an XML-RPC boolean
  getparser      Create instance of the fastest available parser & attach
                 to an unmarshalling object
  dumps          Convert an argument tuple or a Fault instance to an XML-RPC
                 request (or response, if the methodresponse option is used).
  loads          Convert an XML-RPC packet to unmarshalled data plus a method
                 name (None if not present).
"""

import re, string, time, operator

from types import *
import socket
import errno
import httplib

# --------------------------------------------------------------------
# Internal stuff

try:
    unicode
except NameError:
    unicode = None # unicode support not available

try:
    import datetime
    #import sg_timezone
except ImportError:
    datetime = None

try:
    _bool_is_builtin = False.__class__.__name__ == "bool"
except NameError:
    _bool_is_builtin = 0

def _decode(data, encoding, is8bit=re.compile("[\x80-\xff]").search):
    # decode non-ascii string (if possible)
    if unicode and encoding and is8bit(data):
        data = unicode(data, encoding)
    return data

def escape(s, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    return replace(s, ">", "&gt;",)

if unicode:
    def _stringify(string):
        # convert to 7-bit ascii if possible
        try:
            return string.encode("ascii")
        except UnicodeError:
            return string
else:
    def _stringify(string):
        return string

#__version__ = "1.0.1"

# xmlrpc integer limits
MAXINT =  2L**31-1
MININT = -2L**31

# --------------------------------------------------------------------
# Error constants (from Dan Libby's specification at
# http://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php)

# Ranges of errors
PARSE_ERROR       = -32700
SERVER_ERROR      = -32600
APPLICATION_ERROR = -32500
SYSTEM_ERROR      = -32400
TRANSPORT_ERROR   = -32300

# Specific errors
NOT_WELLFORMED_ERROR  = -32700
UNSUPPORTED_ENCODING  = -32701
INVALID_ENCODING_CHAR = -32702
INVALID_XMLRPC        = -32600
METHOD_NOT_FOUND      = -32601
INVALID_METHOD_PARAMS = -32602
INTERNAL_ERROR        = -32603

# --------------------------------------------------------------------
# Exceptions

##
# Base class for all kinds of client-side errors.

class Error(Exception):
    """Base class for client errors."""
    def __str__(self):
        return repr(self)

##
# Indicates an HTTP-level protocol error.  This is raised by the HTTP
# transport layer, if the server returns an error code other than 200
# (OK).
#
# @param url The target URL.
# @param errcode The HTTP error code.
# @param errmsg The HTTP error message.
# @param headers The HTTP header dictionary.

class ProtocolError(Error):
    """Indicates an HTTP protocol error."""
    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers
    def __repr__(self):
        return (
            "<ProtocolError for %s: %s %s>" %
            (self.url, self.errcode, self.errmsg)
            )

##
# Indicates a broken XML-RPC response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response is
# malformed.

class ResponseError(Error):
    """Indicates a broken response package."""
    pass

##
# Indicates an XML-RPC fault response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response contains
# a fault string.  This exception can also used as a class, to
# generate a fault XML-RPC message.
#
# @param faultCode The XML-RPC fault code.
# @param faultString The XML-RPC fault string.

class Fault(Error):
    """Indicates an XML-RPC fault package."""
    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
    def __repr__(self):
        return (
            "<Fault %s: %s>" %
            (self.faultCode, repr(self.faultString))
            )

# --------------------------------------------------------------------
# Special values

##
# Wrapper for XML-RPC boolean values.  Use the xmlrpclib.True and
# xmlrpclib.False constants, or the xmlrpclib.boolean() function, to
# generate boolean XML-RPC values.
#
# @param value A boolean value.  Any true value is interpreted as True,
#              all other values are interpreted as False.

if _bool_is_builtin:
    boolean = Boolean = bool
    # to avoid breaking code which references xmlrpclib.{True,False}
    True, False = True, False
else:
    class Boolean:
        """Boolean-value wrapper.
        
        Use True or False to generate a "boolean" XML-RPC value.
        """
        
        def __init__(self, value = 0):
            self.value = operator.truth(value)
        
        def encode(self, out):
            out.write("<value><boolean>%d</boolean></value>\n" % self.value)
        
        def __cmp__(self, other):
            if isinstance(other, Boolean):
                other = other.value
            return cmp(self.value, other)
        
        def __repr__(self):
            if self.value:
                return "<Boolean True at %x>" % id(self)
            else:
                return "<Boolean False at %x>" % id(self)
        
        def __int__(self):
            return self.value
        
        def __nonzero__(self):
            return self.value
    
    True, False = Boolean(1), Boolean(0)
    
    ##
    # Map true or false value to XML-RPC boolean values.
    #
    # @def boolean(value)
    # @param value A boolean value.  Any true value is mapped to True,
    #              all other values are mapped to False.
    # @return xmlrpclib.True or xmlrpclib.False.
    # @see Boolean
    # @see True
    # @see False
    
    def boolean(value, _truefalse=(False, True)):
        """Convert any Python value to XML-RPC 'boolean'."""
        return _truefalse[operator.truth(value)]



########NEW FILE########
__FILENAME__ = sg_24
import os
import sys
import logging

from shotgun_api3.lib.httplib2 import Http, ProxyInfo, socks
from shotgun_api3.lib.sgtimezone import SgTimezone
from shotgun_api3.lib.xmlrpclib import Error, ProtocolError, ResponseError


LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)

try:
    import simplejson as json
except ImportError:
    LOG.debug("simplejson not found, dropping back to json")
    try:
        import json as json
    except ImportError:
        LOG.debug("json not found, dropping back to embedded simplejson")
        # We need to munge the path so that the absolute imports in simplejson will work.
        dir_path = os.path.dirname(__file__)
        lib_path = os.path.join(dir_path, 'lib')
        sys.path.append(lib_path)
        import shotgun_api3.lib.simplejson as json
        sys.path.pop()

########NEW FILE########
__FILENAME__ = sg_25
import sys
import os
import logging

from .lib.httplib2 import Http, ProxyInfo, socks
from .lib.sgtimezone import SgTimezone
from .lib.xmlrpclib import Error, ProtocolError, ResponseError

LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)

try:
    import simplejson as json
except ImportError:
    LOG.debug("simplejson not found, dropping back to json")
    try:
        import json as json
    except ImportError:
        LOG.debug("json not found, dropping back to embedded simplejson")
        # We need to munge the path so that the absolute imports in simplejson will work.
        dir_path = os.path.dirname(__file__)
        lib_path = os.path.join(dir_path, 'lib')
        sys.path.append(lib_path)
        from .lib import simplejson as json
        sys.path.pop()

########NEW FILE########
__FILENAME__ = shotgun
#!/usr/bin/env python
'''
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2011, Shotgun Software Inc

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


import base64
import cookielib    # used for attachment upload
import cStringIO    # used for attachment upload
import datetime
import logging
import mimetools    # used for attachment upload
import mimetypes    # used for attachment upload
mimetypes.add_type('video/webm','.webm') # webm and mp4 seem to be missing
mimetypes.add_type('video/mp4', '.mp4')  # from some OS/distros
import os
import re
import copy
import stat         # used for attachment upload
import sys
import time
import types
import urllib
import urllib2      # used for image upload
import urlparse
import shutil       # used for attachment download

# use relative import for versions >=2.5 and package import for python versions <2.5
if (sys.version_info[0] > 2) or (sys.version_info[0] == 2 and sys.version_info[1] >= 5):
    from sg_25 import *
else:
    from sg_24 import *

LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)

SG_TIMEZONE = SgTimezone()


try:
    import ssl
    NO_SSL_VALIDATION = False
except ImportError:
    LOG.debug("ssl not found, disabling certificate validation")
    NO_SSL_VALIDATION = True

# ----------------------------------------------------------------------------
# Version
__version__ = "3.0.17.dev"

# ----------------------------------------------------------------------------
# Errors

class ShotgunError(Exception):
    """Base for all Shotgun API Errors"""
    pass

class ShotgunFileDownloadError(ShotgunError):
    """Exception for file download-related errors"""
    pass

class Fault(ShotgunError):
    """Exception when server side exception detected."""
    pass

# ----------------------------------------------------------------------------
# API

class ServerCapabilities(object):
    """Container for the servers capabilities, such as version and paging.
    """

    def __init__(self, host, meta):
        """ServerCapabilities.__init__

        :param host: Host name for the server excluding protocol.

        :param meta: dict of meta data for the server returned from the
        info api method.
        """
        #Server host name
        self.host = host
        self.server_info = meta

        #Version from server is major.minor.rev or major.minor.rev."Dev"
        #Store version as triple and check dev flag
        try:
            self.version = meta.get("version", None)
        except AttributeError:
            self.version = None
        if not self.version:
            raise ShotgunError("The Shotgun Server didn't respond with a version number. "
                               "This may be because you are running an older version of "
                               "Shotgun against a more recent version of the Shotgun API. "
                               "For more information, please contact Shotgun Support.")

        if len(self.version) > 3 and self.version[3] == "Dev":
            self.is_dev = True
        else:
            self.is_dev = False

        self.version = tuple(self.version[:3])
        self._ensure_json_supported()


    def _ensure_json_supported(self):
        """Checks the server version supports the JSON api, raises an
        exception if it does not.

        :raises ShotgunError: The current server version does not support json
        """
        if not self.version or self.version < (2, 4, 0):
            raise ShotgunError("JSON API requires server version 2.4 or "\
                "higher, server is %s" % (self.version,))

    def ensure_include_archived_projects(self):
        """Checks the server version support include_archived_projects parameter
        to find.
        """
        if not self.version or self.version < (5, 3, 14):
            raise ShotgunError("The include_archived_projects flag requires server version 5.3.14 or "\
                "higher, server is %s" % (self.version,))


    def __str__(self):
        return "ServerCapabilities: host %s, version %s, is_dev %s"\
                 % (self.host, self.version, self.is_dev)

class ClientCapabilities(object):
    """Container for the client capabilities.

    Detects the current client platform and works out the SG field
    used for local data paths.
    """

    def __init__(self):
        system = sys.platform.lower()

        if system == 'darwin':
            self.platform = "mac"
        elif system.startswith('linux'):
            self.platform = 'linux'
        elif system == 'win32':
            self.platform = 'windows'
        else:
            self.platform = None

        if self.platform:
            self.local_path_field = "local_path_%s" % (self.platform)
        else:
            self.local_path_field = None

        self.py_version = ".".join(str(x) for x in sys.version_info[:2])

    def __str__(self):
        return "ClientCapabilities: platform %s, local_path_field %s, "\
            "py_verison %s" % (self.platform, self.local_path_field,
            self.py_version)

class _Config(object):
    """Container for the client configuration."""

    def __init__(self):
        self.max_rpc_attempts = 3
        # From http://docs.python.org/2.6/library/httplib.html:
        # If the optional timeout parameter is given, blocking operations 
        # (like connection attempts) will timeout after that many seconds 
        # (if it is not given, the global default timeout setting is used)
        self.timeout_secs = None
        self.api_ver = 'api3'
        self.convert_datetimes_to_utc = True
        self.records_per_page = 500
        self.api_key = None
        self.script_name = None
        self.user_login = None
        self.user_password = None
        self.sudo_as_login = None
        # uuid as a string
        self.session_uuid = None
        self.scheme = None
        self.server = None
        self.api_path = None
        self.proxy_server = None
        self.proxy_port = 8080
        self.proxy_user = None
        self.proxy_pass = None
        self.session_token = None
        self.authorization = None
        self.no_ssl_validation = False

class Shotgun(object):
    """Shotgun Client Connection"""

    # reg ex from
    # http://underground.infovark.com/2008/07/22/iso-date-validation-regex/
    # Note a length check is done before checking the reg ex
    _DATE_PATTERN = re.compile(
        "^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$")
    _DATE_TIME_PATTERN = re.compile(
        "^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])"\
        "(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?)?$")

    def __init__(self,
                 base_url,
                 script_name=None,
                 api_key=None,
                 convert_datetimes_to_utc=True,
                 http_proxy=None,
                 ensure_ascii=True,
                 connect=True,
				 ca_certs=None,
                 login=None,
                 password=None,
                 sudo_as_login=None):
        """Initialises a new instance of the Shotgun client.

        :param base_url: http or https url to the shotgun server.

        :param script_name: name of the client script, used to authenticate
        to the server. If script_name is provided, then api_key must be as
        well and neither login nor password can be provided.

        :param api_key: key assigned to the client script, used to
        authenticate to the server.  If api_key is provided, then script_name
        must be as well and neither login nor password can be provided.

        :param convert_datetimes_to_utc: If True date time values are
        converted from local time to UTC time before been sent to the server.
        Datetimes received from the server are converted back to local time.
        If False the client should use UTC date time values.
        Default is True.

        :param http_proxy: Optional, URL for the http proxy server, on the
        form [username:pass@]proxy.com[:8080]

        :param connect: If True, connect to the server. Only used for testing.
		
		:param ca_certs: The path to the SSL certificate file. Useful for users
		who would like to package their application into an executable.

        :param login: The login to use to authenticate to the server. If login
        is provided, then password must be as well and neither script_name nor
        api_key can be provided.

        :param password: The password for the login to use to authenticate to
        the server. If password is provided, then login must be as well and
        neither script_name nor api_key can be provided.
        
        :param sudo_as_login: A user login string for the user whose permissions will
        be applied to all actions and who will be logged as the user performing
        all actions. Note that logged events will have an additional extra meta-data parameter 
        'sudo_actual_user' indicating the script or user that actually authenticated.
        """

        # verify authentication arguments
        if login is not None or password is not None:
            if script_name is not None or api_key is not None:
                raise ValueError("cannot provide both login/password "
                                 "and script_name/api_key")
            if login is None:
                raise ValueError("password provided without login")
            if password is None:
                raise ValueError("login provided without password")

        if script_name is not None or api_key is not None:
            if script_name is None:
                raise ValueError("api_key provided without script_name")
            if api_key is None:
                raise ValueError("script_name provided without api_key")

        # Can't use 'all' with python 2.4
        if len([x for x in [script_name, api_key, login, password] if x]) == 0:
            if connect:
                raise ValueError("must provide either login/password "
                                 "or script_name/api_key")

        self.config = _Config()
        self.config.api_key = api_key
        self.config.script_name = script_name
        self.config.user_login = login
        self.config.user_password = password
        self.config.sudo_as_login = sudo_as_login
        self.config.convert_datetimes_to_utc = convert_datetimes_to_utc
        self.config.no_ssl_validation = NO_SSL_VALIDATION
        self._connection = None
        self.__ca_certs = ca_certs

        self.base_url = (base_url or "").lower()
        self.config.scheme, self.config.server, api_base, _, _ = \
            urlparse.urlsplit(self.base_url)
        if self.config.scheme not in ("http", "https"):
            raise ValueError("base_url must use http or https got '%s'" %
                self.base_url)
        self.config.api_path = urlparse.urljoin(urlparse.urljoin(
            api_base or "/", self.config.api_ver + "/"), "json")

        self.reset_user_agent()

        # if the service contains user information strip it out
        # copied from the xmlrpclib which turned the user:password into
        # and auth header
        auth, self.config.server = urllib.splituser(self.config.server)
        if auth:
            auth = base64.encodestring(urllib.unquote(auth))
            self.config.authorization = "Basic " + auth.strip()

        # foo:bar@123.456.789.012:3456
        if http_proxy:
            # check if we're using authentication
            p = http_proxy.split("@", 1)
            if len(p) > 1:
                self.config.proxy_user, self.config.proxy_pass = \
                    p[0].split(":", 1)
                proxy_server = p[1]
            else:
                proxy_server = http_proxy
            proxy_netloc_list = proxy_server.split(":", 1)
            self.config.proxy_server = proxy_netloc_list[0]
            if len(proxy_netloc_list) > 1:
                try:
                    self.config.proxy_port = int(proxy_netloc_list[1])
                except ValueError:
                    raise ValueError("Invalid http_proxy address '%s'. Valid " \
                        "format is '123.456.789.012' or '123.456.789.012:3456'"\
                        ". If no port is specified, a default of %d will be "\
                        "used." % (http_proxy, self.config.proxy_port))


        if ensure_ascii:
            self._json_loads = self._json_loads_ascii

        self.client_caps = ClientCapabilities()
        self._server_caps = None
        #test to ensure the the server supports the json API
        #call to server will only be made once and will raise error
        if connect:
            self.server_caps

    # ========================================================================
    # API Functions

    @property
    def server_info(self):
        """Returns server information."""
        return self.server_caps.server_info

    @property
    def server_caps(self):
        """
        :returns: ServerCapabilities that describe the server the client is
        connected to.
        """
        if not self._server_caps or (
            self._server_caps.host != self.config.server):
            self._server_caps = ServerCapabilities(self.config.server,
                self.info())
        return self._server_caps

    def connect(self):
        """Forces the client to connect to the server if it is not already
        connected.

        NOTE: The client will automatically connect to the server. Only
        call this function if you wish to confirm the client can connect.
        """
        self._get_connection()
        self.info()
        return

    def close(self):
        """Closes the current connection to the server.

        If the client needs to connect again it will do so automatically.
        """
        self._close_connection()
        return

    def info(self):
        """Calls the Info function on the Shotgun API to get the server meta.

        :returns: dict of the server meta data.
        """
        return self._call_rpc("info", None, include_auth_params=False)

    def find_one(self, entity_type, filters, fields=None, order=None,
        filter_operator=None, retired_only=False, include_archived_projects=True):
        """Calls the find() method and returns the first result, or None.

        :param entity_type: Required, entity type (string) to find.

        :param filters: Required, list of filters to apply.

        :param fields: Optional list of fields from the matched entities to
        return. Defaults to id.

        :param order: Optional list of fields to order the results by, list
        has the form [{'field_name':'foo','direction':'asc or desc'},]

        :param filter_operator: Optional operator to apply to the filters,
        supported values are 'all' and 'any'. Defaults to 'all'.

        :param limit: Optional, number of entities to return per page.
        Defaults to 0 which returns all entities that match.

        :param page: Optional, page of results to return. By default all
        results are returned. Use together with limit.

        :param retired_only: Optional, flag to return only entities that have
        been retried. Defaults to False which returns only entities which
        have not been retired.
        """

        results = self.find(entity_type, filters, fields, order,
            filter_operator, 1, retired_only, include_archived_projects=include_archived_projects)

        if results:
            return results[0]
        return None

    def find(self, entity_type, filters, fields=None, order=None,
            filter_operator=None, limit=0, retired_only=False, page=0,
            include_archived_projects=True):
        """Find entities matching the given filters.

        :param entity_type: Required, entity type (string) to find.

        :param filters: Required, list of filters to apply.

        :param fields: Optional list of fields from the matched entities to
        return. Defaults to id.

        :param order: Optional list of fields to order the results by, list
        has the form [{'field_name':'foo','direction':'asc or desc'},]

        :param filter_operator: Optional operator to apply to the filters,
        supported values are 'all' and 'any'. Defaults to 'all'.

        :param limit: Optional, number of entities to return per page.
        Defaults to 0 which returns all entities that match.

        :param page: Optional, page of results to return. By default all
        results are returned. Use together with limit.

        :param retired_only: Optional, flag to return only entities that have
        been retried. Defaults to False which returns only entities which
        have not been retired.

        :param include_archived_projects: Optional, flag to include entities
        whose projects have been archived

        :returns: list of the dicts for each entity with the requested fields,
        and their id and type.
        """

        if not isinstance(limit, int) or limit < 0:
            raise ValueError("limit parameter must be a positive integer")

        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)
        elif filter_operator:
            #TODO:Not sure if this test is correct, replicated from prev api
            raise ShotgunError("Deprecated: Use of filter_operator for find()"
                " is not valid any more. See the documentation on find()")

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            self.server_caps.ensure_include_archived_projects()


        params = self._construct_read_parameters(entity_type,
                                                 fields,
                                                 filters,
                                                 retired_only,
                                                 order,
                                                 include_archived_projects)

        if limit and limit <= self.config.records_per_page:
            params["paging"]["entities_per_page"] = limit
            # If page isn't set and the limit doesn't require pagination,
            # then trigger the faster code path.
            if page == 0:
                page = 1

        if self.server_caps.version and self.server_caps.version >= (3, 3, 0):
            params['api_return_image_urls'] = True

        # if page is specified, then only return the page of records requested
        if page != 0:
            # No paging_info needed, so optimize it out.
            params["return_paging_info"] = False
            params["paging"]["current_page"] = page
            records = self._call_rpc("read", params).get("entities", [])
            return self._parse_records(records)

        records = []
        result = self._call_rpc("read", params)
        while result.get("entities"):
            records.extend(result.get("entities"))

            if limit and len(records) >= limit:
                records = records[:limit]
                break
            if len(records) == result["paging_info"]["entity_count"]:
                break

            params['paging']['current_page'] += 1
            result = self._call_rpc("read", params)

        return self._parse_records(records)



    def _construct_read_parameters(self,
                                   entity_type,
                                   fields,
                                   filters,
                                   retired_only,
                                   order,
                                   include_archived_projects):
        params = {}
        params["type"] = entity_type
        params["return_fields"] = fields or ["id"]
        params["filters"] = filters
        params["return_only"] = (retired_only and 'retired') or "active"
        params["return_paging_info"] = True
        params["paging"] = { "entities_per_page": self.config.records_per_page,
                             "current_page": 1 }

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if order:
            sort_list = []
            for sort in order:
                if sort.has_key('column'):
                    # TODO: warn about deprecation of 'column' param name
                    sort['field_name'] = sort['column']
                sort.setdefault("direction", "asc")
                sort_list.append({
                    'field_name': sort['field_name'],
                    'direction' : sort['direction']
                })
            params['sorts'] = sort_list
        return params

    def summarize(self,
                  entity_type,
                  filters,
                  summary_fields,
                  filter_operator=None,
                  grouping=None,
                  include_archived_projects=True):
        """
        Return group and summary information for entity_type for summary_fields
        based on the given filters.
        """

        if not isinstance(grouping, list) and grouping != None:
            msg = "summarize() 'grouping' parameter must be a list or None"
            raise ValueError(msg)

        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)

        if not include_archived_projects:
            # This defaults to True on the server (no argument is sent)
            # So we only need to check the server version if it is False
            self.server_caps.ensure_include_archived_projects()

        params = {"type": entity_type,
                  "summaries": summary_fields,
                  "filters": filters}

        if include_archived_projects is False:
            # Defaults to True on the server, so only pass it if it's False
            params["include_archived_projects"] = False

        if grouping != None:
            params['grouping'] = grouping

        records = self._call_rpc('summarize', params)
        return records

    def create(self, entity_type, data, return_fields=None):
        """Create a new entity of the specified entity_type.

        :param entity_type: Required, entity type (string) to create.

        :param data: Required, dict fields to set on the new entity.

        :param return_fields: Optional list of fields from the new entity
        to return. Defaults to 'id' field.

        :returns: dict of the requested fields.
        """

        data = data.copy()
        if not return_fields:
            return_fields = ["id"]

        upload_image = None
        if 'image' in data:
            upload_image = data.pop('image')

        upload_filmstrip_image = None
        if 'filmstrip_image' in data:
            if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
                raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            upload_filmstrip_image = data.pop('filmstrip_image')

        params = {
            "type" : entity_type,
            "fields" : self._dict_to_list(data),
            "return_fields" : return_fields
        }

        record = self._call_rpc("create", params, first=True)
        result = self._parse_records(record)[0]

        if upload_image:
            image_id = self.upload_thumbnail(entity_type, result['id'],
                                             upload_image)
            image = self.find_one(entity_type, [['id', 'is', result.get('id')]],
                                  fields=['image'])
            result['image'] = image.get('image')

        if upload_filmstrip_image:
            filmstrip_id = self.upload_filmstrip_thumbnail(entity_type, result['id'], upload_filmstrip_image)
            filmstrip = self.find_one(entity_type,
                                     [['id', 'is', result.get('id')]],
                                     fields=['filmstrip_image'])
            result['filmstrip_image'] = filmstrip.get('filmstrip_image')

        return result

    def update(self, entity_type, entity_id, data):
        """Updates the specified entity with the supplied data.

        :param entity_type: Required, entity type (string) to update.

        :param entity_id: Required, id of the entity to update.

        :param data: Required, dict fields to update on the entity.

        :returns: dict of the fields updated, with the entity_type and
        id added.
        """

        data = data.copy()
        upload_image = None
        if 'image' in data and data['image'] is not None:
            upload_image = data.pop('image')
        upload_filmstrip_image = None
        if 'filmstrip_image' in data:
            if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
                raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            upload_filmstrip_image = data.pop('filmstrip_image')

        if data:
            params = {
                "type" : entity_type,
                "id" : entity_id,
                "fields" : self._dict_to_list(data)
            }
            record = self._call_rpc("update", params)
            result = self._parse_records(record)[0]
        else:
            result = {'id': entity_id, 'type': entity_type}

        if upload_image:
            image_id = self.upload_thumbnail(entity_type, entity_id,
                                             upload_image)
            image = self.find_one(entity_type, [['id', 'is', result.get('id')]],
                                  fields=['image'])
            result['image'] = image.get('image')

        if upload_filmstrip_image:
            filmstrip_id = self.upload_filmstrip_thumbnail(entity_type, result['id'], upload_filmstrip_image)
            filmstrip = self.find_one(entity_type,
                                     [['id', 'is', result.get('id')]],
                                     fields=['filmstrip_image'])
            result['filmstrip_image'] = filmstrip.get('filmstrip_image')

        return result

    def delete(self, entity_type, entity_id):
        """Retire the specified entity.

        The entity can be brought back to life using the revive function.

        :param entity_type: Required, entity type (string) to delete.

        :param entity_id: Required, id of the entity to delete.

        :returns: True if the entity was deleted, False otherwise e.g. if the
        entity has previously been deleted.
        """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("delete", params)

    def revive(self, entity_type, entity_id):
        """Revive an entity that has previously been deleted.

        :param entity_type: Required, entity type (string) to revive.

        :param entity_id: Required, id of the entity to revive.

        :returns: True if the entity was revived, False otherwise e.g. if the
        entity has previously been revived (or was not deleted).
        """

        params = {
            "type" : entity_type,
            "id" : entity_id
        }

        return self._call_rpc("revive", params)

    def batch(self, requests):
        """Make a batch request  of several create, update and delete calls.

        All requests are performed within a transaction, so either all will
        complete or none will.

        :param requests: A list of dict's of the form which have a
            request_type key and also specifies:
            - create: entity_type, data dict of fields to set
            - update: entity_type, entity_id, data dict of fields to set
            - delete: entity_type and entity_id

        :returns: A list of values for each operation, create and update
        requests return a dict of the fields updated. Delete requests
        return True if the entity was deleted.
        """

        if not isinstance(requests, list):
            raise ShotgunError("batch() expects a list.  Instead was sent "\
                "a %s" % type(requests))

        # If we have no requests, just return an empty list immediately.
        # Nothing to process means nothing to get results of.
        if len(requests) == 0:
            return []

        calls = []

        def _required_keys(message, required_keys, data):
            missing = set(required_keys) - set(data.keys())
            if missing:
                raise ShotgunError("%s missing required key: %s. "\
                    "Value was: %s." % (message, ", ".join(missing), data))

        for req in requests:
            _required_keys("Batched request",
                           ['request_type', 'entity_type'],
                           req)
            request_params = {'request_type': req['request_type'],
                              "type" : req["entity_type"]}

            if req["request_type"] == "create":
                _required_keys("Batched create request", ['data'], req)
                request_params['fields'] = self._dict_to_list(req["data"])
                request_params["return_fields"] = req.get("return_fields") or["id"]
            elif req["request_type"] == "update":
                _required_keys("Batched update request",
                               ['entity_id', 'data'],
                               req)
                request_params['id'] = req['entity_id']
                request_params['fields'] = self._dict_to_list(req["data"])
            elif req["request_type"] == "delete":
                _required_keys("Batched delete request", ['entity_id'], req)
                request_params['id'] = req['entity_id']
            else:
                raise ShotgunError("Invalid request_type '%s' for batch" % (
                                   req["request_type"]))
            calls.append(request_params)
        records = self._call_rpc("batch", calls)
        return self._parse_records(records)

    def work_schedule_read(self, start_date, end_date, project=None, user=None):
        """Get the work day rules for a given date range.

        reasons:
            STUDIO_WORK_WEEK
            STUDIO_EXCEPTION
            PROJECT_WORK_WEEK
            PROJECT_EXCEPTION
            USER_WORK_WEEK
            USER_EXCEPTION


        :param start_date: Start date of date range.
        :type start_date: str (YYYY-MM-DD)
        :param end_date: End date of date range.
        :type end_date: str (YYYY-MM-DD)
        :param dict project: Project entity to query WorkDayRules for. (optional)
        :param dict user: User entity to query WorkDayRules for. (optional)
        """

        if not self.server_caps.version or self.server_caps.version < (3, 2, 0):
            raise ShotgunError("Work schedule support requires server version 3.2 or "\
                "higher, server is %s" % (self.server_caps.version,))

        if not isinstance(start_date, str) or not isinstance(end_date, str):
            raise ShotgunError("The start_date and end_date arguments must be strings in YYYY-MM-DD format")

        params = dict(
            start_date=start_date,
            end_date=end_date,
            project=project,
            user=user
        )

        return self._call_rpc('work_schedule_read', params)

    def work_schedule_update(self, date, working, description=None, project=None, user=None, recalculate_field=None):
        """Update the work schedule for a given date. If neither project nor user are passed the studio work schedule will be updated.
        Project and User can only be used separately.

        :param date: Date of WorkDayRule to update.
        :type date: str (YYYY-MM-DD)
        :param bool working:
        :param str description: Reason for time off. (optional)
        :param dict project: Project entity to assign to. Cannot be used with user. (optional)
        :param dict user: User entity to assign to. Cannot be used with project. (optional)
        :param str recalculate_field: Choose the schedule field that will be recalculated on Tasks when they are affected by a change in working schedule. 'due_date' or 'duration', default is a Site Preference (optional)
        """

        if not self.server_caps.version or self.server_caps.version < (3, 2, 0):
            raise ShotgunError("Work schedule support requires server version 3.2 or "\
                "higher, server is %s" % (self.server_caps.version,))

        if not isinstance(date, str):
            raise ShotgunError("The date argument must be string in YYYY-MM-DD format")

        params = dict(
            date=date,
            working=working,
            description=description,
            project=project,
            user=user,
            recalculate_field=recalculate_field
        )

        return self._call_rpc('work_schedule_update', params)

    def follow(self, user, entity):
        """Adds the entity to the user's followed entities (or does nothing if the user is already following the entity)
        
        :param dict user: User entity to follow the entity
        :param dict entity: Entity to be followed
        
        :returns: dict with 'followed'=true, and dicts for the 'user' and 'entity' that were passed in
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            user=user,
            entity=entity
        )
        
        return self._call_rpc('follow', params)

    def unfollow(self, user, entity):
        """Removes entity from the user's followed entities (or does nothing if the user is not following the entity)
        
        :param dict user: User entity to unfollow the entity
        :param dict entity: Entity to be unfollowed
        
        :returns: dict with 'unfollowed'=true, and dicts for the 'user' and 'entity' that were passed in
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            user=user,
            entity=entity
        )
        
        return self._call_rpc('unfollow', params)

    def followers(self, entity):
        """Gets all followers of the entity.
        
        :param dict entity: Find all followers of this entity
        
        :returns list of dicts for all the users following the entity
        """

        if not self.server_caps.version or self.server_caps.version < (5, 1, 22):
            raise ShotgunError("Follow support requires server version 5.2 or "\
                "higher, server is %s" % (self.server_caps.version,))
        
        params = dict(
            entity=entity
        )
        
        return self._call_rpc('followers', params)

    def schema_entity_read(self):
        """Gets all active entities defined in the schema.

        :returns: dict of Entity Type to dict containing the display name.
        """

        return self._call_rpc("schema_entity_read", None)

    def schema_read(self):
        """Gets the schema for all fields in all entities.

        :returns: nested dicts
        """

        return self._call_rpc("schema_read", None)

    def schema_field_read(self, entity_type, field_name=None):
        """Gets all schema for fields in the specified entity_type or one
        field.

        :param entity_type: Required, entity type (string) to get the schema
        for.

        :param field_name: Optional, name of the field to get the schema
        definition for. If not supplied all fields for the entity type are
        returned.

        :returns: dict of field name to nested dicts which describe the field
        """

        params = {
            "type" : entity_type,
        }
        if field_name:
            params["field_name"] = field_name

        return self._call_rpc("schema_field_read", params)

    def schema_field_create(self, entity_type, data_type, display_name,
        properties=None):
        """Creates a field for the specified entity type.

        :param entity_type: Required, entity type (string) to add the field to

        :param data_type: Required, Shotgun data type for the new field.

        :param display_name: Required, display name for the new field.

        :param properties: Optional, dict of properties for the new field.

        :returns: The Shotgun name (string) for the new field, this is
        different to the display_name passed in.
        """

        params = {
            "type" : entity_type,
            "data_type" : data_type,
            "properties" : [
                {'property_name': 'name', 'value': display_name}
            ]
        }
        params["properties"].extend(self._dict_to_list(properties,
            key_name="property_name", value_name="value"))

        return self._call_rpc("schema_field_create", params)

    def schema_field_update(self, entity_type, field_name, properties):
        """Updates the specified field definition with the supplied
        properties.

        :param entity_type: Required, entity type (string) to add the field to

        :param field_name: Required, Shotgun name of the field to update.

        :param properties: Required, dict of updated properties for the field.

        :returns: True if the field was updated, False otherwise.
        """

        params = {
            "type" : entity_type,
            "field_name" : field_name,
            "properties": [
                {"property_name" : k, "value" : v}
                for k, v in (properties or {}).iteritems()
            ]
        }

        return self._call_rpc("schema_field_update", params)

    def schema_field_delete(self, entity_type, field_name):
        """Deletes the specified field definition from the entity_type.

        :param entity_type: Required, entity type (string) to delete the field
        from.

        :param field_name: Required, Shotgun name of the field to delete.

        :param properties: Required, dict of updated properties for the field.

        :returns: True if the field was updated, False otherwise.
        """

        params = {
            "type" : entity_type,
            "field_name" : field_name
        }

        return self._call_rpc("schema_field_delete", params)

    def add_user_agent(self, agent):
        """Add agent to the user-agent header

        Append agent to the string passed in as the user-agent to be logged
        in events for this API session.

        :param agent: Required, string to append to user-agent.
        """
        self._user_agents.append(agent)

    def reset_user_agent(self):
        """Reset user agent to the default
        """
        self._user_agents = ["shotgun-json (%s)" % __version__]

    def set_session_uuid(self, session_uuid):
        """Sets the browser session_uuid for this API session.

        Once set events generated by this API session will include the
        session_uuid in their EventLogEntries.

        :param session_uuid: Session UUID to set.
        """

        self.config.session_uuid = session_uuid
        return

    def share_thumbnail(self, entities, thumbnail_path=None, source_entity=None,
        filmstrip_thumbnail=False, **kwargs):
        if not self.server_caps.version or self.server_caps.version < (4, 0, 0):
            raise ShotgunError("Thumbnail sharing support requires server "\
                "version 4.0 or higher, server is %s" % (self.server_caps.version,))

        if not isinstance(entities, list) or len(entities) == 0:
            raise ShotgunError("'entities' parameter must be a list of entity "\
                "hashes and may not be empty")

        for e in entities:
            if not isinstance(e, dict) or 'id' not in e or 'type' not in e:
                raise ShotgunError("'entities' parameter must be a list of "\
                    "entity hashes with at least 'type' and 'id' keys.\nInvalid "\
                    "entity: %s" % e)

        if (not thumbnail_path and not source_entity) or \
            (thumbnail_path and source_entity):
            raise ShotgunError("You must supply either thumbnail_path OR "\
                "source_entity.")

        # upload thumbnail
        if thumbnail_path:
            source_entity = entities.pop(0)
            if filmstrip_thumbnail:
                thumb_id = self.upload_filmstrip_thumbnail(source_entity['type'],
                    source_entity['id'], thumbnail_path, **kwargs)
            else:
                thumb_id = self.upload_thumbnail(source_entity['type'],
                    source_entity['id'], thumbnail_path, **kwargs)
        else:
            if not isinstance(source_entity, dict) or 'id' not in source_entity \
                or 'type' not in source_entity:
                raise ShotgunError("'source_entity' parameter must be a dict "\
                    "with at least 'type' and 'id' keys.\nGot: %s (%s)" \
                    % (source_entity, type(source_entity)))

        # only 1 entity in list and we already uploaded the thumbnail to it
        if len(entities) == 0:
            return thumb_id

        # update entities with source_entity thumbnail
        entities_str = []
        for e in entities:
            entities_str.append("%s_%s" % (e['type'], e['id']))
        # format for post request
        if filmstrip_thumbnail:
            filmstrip_thumbnail = 1
        params = {
            "entities" : ','.join(entities_str),
            "source_entity": "%s_%s" % (source_entity['type'], source_entity['id']),
            "filmstrip_thumbnail" : filmstrip_thumbnail,
        }

        params.update(self._auth_params())

        # Create opener with extended form post support
        opener = self._build_opener(FormPostHandler)
        url = urlparse.urlunparse((self.config.scheme, self.config.server,
            "/upload/share_thumbnail", None, None, None))

        # Perform the request
        try:
            resp = opener.open(url, params)
            result = resp.read()
            # response headers are in str(resp.info()).splitlines()
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error. "
                    "\n%s\n(%s)\n%s\n\n" % (url, params, e))
            else:
                raise ShotgunError("Unanticipated error occurred %s" % (e))
        else:
            if not str(result).startswith("1"):
                raise ShotgunError("Unable to share thumbnail: %s" % result)
            else:
                # clearing thumbnail returns no attachment_id
                try:
                    attachment_id = int(str(result).split(":")[1].split("\n")[0])
                except ValueError:
                    attachment_id = None

        return attachment_id

    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Convenience function for uploading thumbnails, see upload.
        """
        return self.upload(entity_type, entity_id, path,
            field_name="thumb_image", **kwargs)

    def upload_filmstrip_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Convenience function for uploading thumbnails, see upload.
        """
        if not self.server_caps.version or self.server_caps.version < (3, 1, 0):
            raise ShotgunError("Filmstrip thumbnail support requires server version 3.1 or "\
                "higher, server is %s" % (self.server_caps.version,))

        return self.upload(entity_type, entity_id, path,
            field_name="filmstrip_thumb_image", **kwargs)

    def upload(self, entity_type, entity_id, path, field_name=None,
        display_name=None, tag_list=None):
        """Upload a file as an attachment/thumbnail to the specified
        entity_type and entity_id.

        :param entity_type: Required, entity type (string) to revive.

        :param entity_id: Required, id of the entity to revive.

        :param path: path to file on disk

        :param field_name: the field on the entity to upload to
            (ignored if thumbnail)

        :param display_name: the display name to use for the file in the ui
            (ignored if thumbnail)

        :param tag_list: comma-separated string of tags to assign to the file

        :returns: Id of the new attachment.
        """
        path = os.path.abspath(os.path.expanduser(path or ""))
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file, got '%s'" % path)

        is_thumbnail = (field_name == "thumb_image" or field_name == "filmstrip_thumb_image")

        params = {
            "entity_type" : entity_type,
            "entity_id" : entity_id,
        }

        params.update(self._auth_params())

        if is_thumbnail:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/publish_thumbnail", None, None, None))
            params["thumb_image"] = open(path, "rb")
            if field_name == "filmstrip_thumb_image":
                params["filmstrip"] = True

        else:
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/upload/upload_file", None, None, None))
            if display_name is None:
                display_name = os.path.basename(path)
            # we allow linking to nothing for generic reference use cases
            if field_name is not None:
                params["field_name"] = field_name
            params["display_name"] = display_name
            # None gets converted to a string and added as a tag...
            if tag_list:
                params["tag_list"] = tag_list

            params["file"] = open(path, "rb")

        # Create opener with extended form post support
        opener = self._build_opener(FormPostHandler)

        # Perform the request
        try:
            result = opener.open(url, params).read()
        except urllib2.HTTPError, e:
            if e.code == 500:
                raise ShotgunError("Server encountered an internal error. "
                    "\n%s\n(%s)\n%s\n\n" % (url, params, e))
            else:
                raise ShotgunError("Unanticipated error occurred uploading "
                    "%s: %s" % (path, e))
        else:
            if not str(result).startswith("1"):
                raise ShotgunError("Could not upload file successfully, but "\
                    "not sure why.\nPath: %s\nUrl: %s\nError: %s" % (
                    path, url, str(result)))

        attachment_id = int(str(result).split(":")[1].split("\n")[0])
        return attachment_id

    def download_attachment(self, attachment=False, file_path=None, 
                            attachment_id=None):
        """Downloads the file associated with a Shotgun Attachment.

        NOTE: On older (< v5.1.0) Shotgun versions, non-downloadable files 
        on Shotgun don't raise exceptions, they cause a server error which 
        returns a 200 with the page content.

        :param attachment: (mixed) Usually a dict representing an Attachment.
        The dict should have a 'url' key that specifies the download url. 
        Optionally, the dict can be a standard entity hash format with 'id' and
        'type' keys as long as 'type'=='Attachment'. This is only supported for
        backwards compatibility (#22150).
        If an int value is passed in, the Attachment with the matching id will
        be downloaded from the Shotgun server.

        :param file_path: (str) Optional. If provided, write the data directly
        to local disk using the file_path. This avoids loading all of the data 
        in memory and saves the file locally which is probably what is desired
        anyway. 

        :param attachment_id: (int) Optional. Deprecated in favor of passing in 
        Attachment hash to attachment param. This attachment_id exists only for
        backwards compatibility for scripts specifying the parameter with
        keywords.

        :returns: (str) If file_path is None, returns data of the Attachment 
        file as a string. If file_path is provided, returns file_path.
        """
        # backwards compatibility when passed via keyword argument 
        if attachment is False:
            if type(attachment_id) == int:
                attachment = attachment_id
            else:
                raise TypeError("Missing parameter 'attachment'. Expected a "\
                                "dict, int, NoneType value or"\
                                "an int for parameter attachment_id")
        # write to disk
        if file_path:
            try:
                fp = open(file_path, 'wb')
            except IOError, e:
                raise IOError("Unable to write Attachment to disk using "\
                              "file_path. %s" % e) 

        url = self.get_attachment_download_url(attachment)
        if url is None:
            return None

        # We only need to set the auth cookie for downloads from Shotgun server
        if self.config.server in url:
            self.set_up_auth_cookie()
   
        try:
            request = urllib2.Request(url)
            request.add_header('user-agent', "; ".join(self._user_agents))
            req = urllib2.urlopen(request)
            if file_path:
                shutil.copyfileobj(req, fp)
            else:
                attachment = req.read()
        # 400 [sg] Attachment id doesn't exist or is a local file
        # 403 [s3] link is invalid
        except urllib2.URLError, e:
            if file_path:
                fp.close()
            err = "Failed to open %s\n%s" % (url, e)
            if hasattr(e, 'code'):
                if e.code == 400:
                    err += "\nAttachment may not exist or is a local file?"
                elif e.code == 403:
                    # Only parse the body if it is an Amazon S3 url. 
                    if url.find('s3.amazonaws.com') != -1 \
                        and e.headers['content-type'] == 'application/xml':
                        body = e.readlines()
                        if body:
                            xml = ''.join(body)
                            # Once python 2.4 support is not needed we can think about using elementtree.
                            # The doc is pretty small so this shouldn't be an issue.
                            match = re.search('<Message>(.*)</Message>', xml)
                            if match:
                                err += ' - %s' % (match.group(1))
            raise ShotgunFileDownloadError(err)
        else:
            if file_path:
                return file_path
            else:
                return attachment

    def set_up_auth_cookie(self):
        """Sets up urllib2 with a cookie for authentication on the Shotgun 
        instance.
        """
        sid = self._get_session_token()
        cj = cookielib.LWPCookieJar()
        c = cookielib.Cookie('0', '_session_id', sid, None, False,
            self.config.server, False, False, "/", True, False, None, True,
            None, None, {})
        cj.set_cookie(c)
        cookie_handler = urllib2.HTTPCookieProcessor(cj)
        opener = self._build_opener(cookie_handler)
        urllib2.install_opener(opener)

    def get_attachment_download_url(self, attachment):
        """Returns the URL for downloading provided Attachment.

        :param attachment: (mixed) If type is an int, construct url to download
        Attachment with id from Shotgun. 
        If type is a dict, and a url key is present, use that url. 
        If type is a dict, and url key is not present, check if we have
        an id and type keys and the type is 'Attachment' in which case we 
        construct url to download Attachment with id from Shotgun as if just
        the id has been passed in. 

        :todo: Support for a standard entity hash should be removed: #22150

        :returns: (str) the download URL for the Attachment or None if None was
        passed to attachment param. This avoids raising an error when results
        from a find() are passed off to a download_attachment() call.
        """
        attachment_id = None
        if isinstance(attachment, int):
            attachment_id = attachment
        elif isinstance(attachment, dict):
            try:
                url = attachment['url']
            except KeyError:
                if ('id' in attachment and 'type' in attachment and 
                    attachment['type'] == 'Attachment'):
                    attachment_id = attachment['id']
                else:
                    raise ValueError("Missing 'url' key in Attachment dict")
        elif attachment is None:
            url = None
        else:
            raise TypeError("Unable to determine download url. Expected "\
                "dict, int, or NoneType. Instead got %s" % type(attachment))

        if attachment_id: 
            url = urlparse.urlunparse((self.config.scheme, self.config.server,
                "/file_serve/attachment/%s" % urllib.quote(str(attachment_id)),
                None, None, None))
        return url

    def authenticate_human_user(self, user_login, user_password):
        '''Authenticate Shotgun HumanUser. HumanUser must be an active account.
        @param user_login: Login name of Shotgun HumanUser
        @param user_password: Password for Shotgun HumanUser
        @return: Dictionary of HumanUser including ID if authenticated, None is unauthorized.
        '''
        if not user_login:
            raise ValueError('Please supply a username to authenticate.')

        if not user_password:
            raise ValueError('Please supply a password for the user.')

        # Override permissions on Config obj
        original_login = self.config.user_login
        original_password = self.config.user_password

        self.config.user_login = user_login
        self.config.user_password = user_password

        try:
            data = self.find_one('HumanUser', [['sg_status_list', 'is', 'act'], ['login', 'is', user_login]], ['id', 'login'], '', 'all')
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
            return data
        except Fault:
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
        except:
            # Set back to default - There finally and except cannot be used together in python2.4
            self.config.user_login = original_login
            self.config.user_password = original_password
            raise


    def update_project_last_accessed(self, project, user=None):
        """
        Update projects last_accessed_by_current_user field.
        
        :param project - a project entity hash
        :param user - A human user entity hash. Optional if either login or sudo_as are used.

        """
        if self.server_caps.version and self.server_caps.version < (5, 3, 17):
                raise ShotgunError("update_project_last_accessed requires server version 5.3.17 or "\
                    "higher, server is %s" % (self.server_caps.version,))

        # Find a page from the project
        page = self.find_one('Page', [['project','is',project], ['ui_category','is','project_overview']])
        if not page:
            # There should be a project overview page page for a live project, but if there is not,
            # another page from the project will work.
            page = self.find_one('Page', [['project','is',project]])

        if not page:
            raise RuntimeError("Unable to find page for project %s" % str(project))

        if not user:
            # Try to use sudo as user if present
            if self.config.sudo_as_login:
                user = self.find_one('HumanUser', [['login', 'is', self.config.sudo_as_login]])
            # Try to use login if present
            if self.config.user_login:
                user = self.find_one('HumanUser', [['login', 'is', self.config.user_login]])
        if not user:
            raise RuntimeError("No user supplied and unable to determine user from login or sudo_as")

        self.create( 'PageHit', { 'page': page, 'user': user } )


    def _get_session_token(self):
        """Hack to authenticate in order to download protected content
        like Attachments
        """
        if self.config.session_token:
            return self.config.session_token

        rv = self._call_rpc("get_session_token", None)
        session_token = (rv or {}).get("session_id")
        if not session_token:
            raise RuntimeError("Could not extract session_id from %s", rv)

        self.config.session_token = session_token
        return self.config.session_token

    def _build_opener(self, handler):
        """Build urllib2 opener with appropriate proxy handler."""
        if self.config.proxy_server:
            # handle proxy auth
            if self.config.proxy_user and self.config.proxy_pass:
                auth_string = "%s:%s@" % (self.config.proxy_user, self.config.proxy_pass)
            else:
                auth_string = ""
            proxy_addr = "http://%s%s:%d" % (auth_string, self.config.proxy_server, self.config.proxy_port)
            proxy_support = urllib2.ProxyHandler({self.config.scheme : proxy_addr})

            opener = urllib2.build_opener(proxy_support, handler)
        else:
            opener = urllib2.build_opener(handler)
        return opener

    # Deprecated methods from old wrapper
    def schema(self, entity_type):
        raise ShotgunError("Deprecated: use schema_field_read('type':'%s') "
            "instead" % entity_type)

    def entity_types(self):
        raise ShotgunError("Deprecated: use schema_entity_read() instead")
    # ========================================================================
    # RPC Functions

    def _call_rpc(self, method, params, include_auth_params=True, first=False):
        """Calls the specified method on the Shotgun Server sending the
        supplied payload.

        """

        LOG.debug("Starting rpc call to %s with params %s" % (
            method, params))

        params = self._transform_outbound(params)
        payload = self._build_payload(method, params,
            include_auth_params=include_auth_params)
        encoded_payload = self._encode_payload(payload)

        req_headers = {
            "content-type" : "application/json; charset=utf-8",
            "connection" : "keep-alive"
        }
        http_status, resp_headers, body = self._make_call("POST",
            self.config.api_path, encoded_payload, req_headers)
        LOG.debug("Completed rpc call to %s" % (method))
        try:
            self._parse_http_status(http_status)
        except ProtocolError, e:
            e.headers = resp_headers
            # 403 is returned with custom error page when api access is blocked
            if e.errcode == 403:
                e.errmsg += ": %s" % body
            raise

        response = self._decode_response(resp_headers, body)
        self._response_errors(response)
        response = self._transform_inbound(response)

        if not isinstance(response, dict) or "results" not in response:
            return response

        results = response.get("results")
        if first and isinstance(results, list):
            return results[0]
        return results

    def _auth_params(self):
        """ return a dictionary of the authentication parameters being used. """
        # Used to authenticate HumanUser credentials
        if self.config.user_login and self.config.user_password:
            auth_params = {
                "user_login" : str(self.config.user_login),
                "user_password" : str(self.config.user_password),
            }

        # Use script name instead
        elif self.config.script_name and self.config.api_key:
            auth_params = {
                "script_name" : str(self.config.script_name),
                "script_key" : str(self.config.api_key),
            }

        else:
            raise ValueError("invalid auth params")

        if self.config.session_uuid:
            auth_params["session_uuid"] = self.config.session_uuid

        # Make sure sudo_as_login is supported by server version
        if self.config.sudo_as_login:
            if self.server_caps.version and self.server_caps.version < (5, 3, 12):
                raise ShotgunError("Option 'sudo_as_login' requires server version 5.3.12 or "\
                    "higher, server is %s" % (self.server_caps.version,))
            auth_params["sudo_as_login"] = self.config.sudo_as_login

        return auth_params

    def _build_payload(self, method, params, include_auth_params=True):
        """Builds the payload to be send to the rpc endpoint.

        """
        if not method:
            raise ValueError("method is empty")

        call_params = []

        if include_auth_params:
            auth_params = self._auth_params()
            call_params.append(auth_params)

        if params:
            call_params.append(params)

        return {
            "method_name" : method,
            "params" : call_params
        }

    def _encode_payload(self, payload):
        """Encodes the payload to a string to be passed to the rpc endpoint.

        The payload is json encoded as a unicode string if the content
        requires it. The unicode string is then encoded as 'utf-8' as it must
        be in a single byte encoding to go over the wire.
        """

        wire = json.dumps(payload, ensure_ascii=False)
        if isinstance(wire, unicode):
            return wire.encode("utf-8")
        return wire

    def _make_call(self, verb, path, body, headers):
        """Makes a HTTP call to the server, handles retry and failure.
        """

        attempt = 0
        req_headers = {
            "user-agent": "; ".join(self._user_agents),
        }
        if self.config.authorization:
            req_headers["Authorization"] = self.config.authorization

        req_headers.update(headers or {})
        body = body or None

        max_rpc_attempts = self.config.max_rpc_attempts

        while (attempt < max_rpc_attempts):
            attempt += 1
            try:
                return self._http_request(verb, path, body, req_headers)
            except Exception:
                #TODO: LOG ?
                self._close_connection()
                if attempt == max_rpc_attempts:
                    raise

    def _http_request(self, verb, path, body, headers):
        """Makes the actual HTTP request.
        """
        url = urlparse.urlunparse((self.config.scheme, self.config.server,
            path, None, None, None))
        LOG.debug("Request is %s:%s" % (verb, url))
        LOG.debug("Request headers are %s" % headers)
        LOG.debug("Request body is %s" % body)

        conn = self._get_connection()
        resp, content = conn.request(url, method=verb, body=body,
            headers=headers)
        #http response code is handled else where
        http_status = (resp.status, resp.reason)
        resp_headers = dict(
            (k.lower(), v)
            for k, v in resp.iteritems()
        )
        resp_body = content

        LOG.debug("Response status is %s %s" % http_status)
        LOG.debug("Response headers are %s" % resp_headers)
        LOG.debug("Response body is %s" % resp_body)

        return (http_status, resp_headers, resp_body)

    def _parse_http_status(self, status):
        """Parse the status returned from the http request.

        :raises: RuntimeError if the http status is non success.

        :param status: Tuple of (code, reason).
        """
        error_code = status[0]
        errmsg = status[1]

        if status[0] >= 300:
            headers = "HTTP error from server"
            if status[0] == 503:
                errmsg = "Shotgun is currently down for maintenance. Please try again later."
            raise ProtocolError(self.config.server,
                                error_code,
                                errmsg,
                                headers)

        return

    def _decode_response(self, headers, body):
        """Decodes the response from the server from the wire format to
        a python data structure.

        :param headers: Headers from the server.

        :param body: Raw response body from the server.

        :returns: If the content-type starts with application/json or
        text/javascript the body is json decoded. Otherwise the raw body is
        returned.
        """
        if not body:
            return body

        ct = (headers.get("content-type") or "application/json").lower()

        if ct.startswith("application/json") or ct.startswith("text/javascript"):
            return self._json_loads(body)
        return body

    def _json_loads(self, body):
        return json.loads(body)

    def _json_loads_ascii(self, body):
        '''See http://stackoverflow.com/questions/956867'''
        def _decode_list(lst):
            newlist = []
            for i in lst:
                if isinstance(i, unicode):
                    i = i.encode('utf-8')
                elif isinstance(i, list):
                    i = _decode_list(i)
                newlist.append(i)
            return newlist

        def _decode_dict(dct):
            newdict = {}
            for k, v in dct.iteritems():
                if isinstance(k, unicode):
                    k = k.encode('utf-8')
                if isinstance(v, unicode):
                    v = v.encode('utf-8')
                elif isinstance(v, list):
                    v = _decode_list(v)
                newdict[k] = v
            return newdict
        return json.loads(body, object_hook=_decode_dict)


    def _response_errors(self, sg_response):
        """Raises any API errors specified in the response.

        :raises ShotgunError: If the server response contains an exception.
        """

        if isinstance(sg_response, dict) and sg_response.get("exception"):
            raise Fault(sg_response.get("message",
                "Unknown Error"))
        return

    def _visit_data(self, data, visitor):
        """Walk the data (simple python types) and call the visitor."""

        if not data:
            return data

        recursive = self._visit_data
        if isinstance(data, list):
            return [recursive(i, visitor) for i in data]

        if isinstance(data, tuple):
            return tuple(recursive(i, visitor) for i in data)

        if isinstance(data, dict):
            return dict(
                (k, recursive(v, visitor))
                for k, v in data.iteritems()
            )

        return visitor(data)

    def _transform_outbound(self, data):
        """Transforms data types or values before they are sent by the
        client.

        - changes timezones
        - converts dates and times to strings
        """

        if self.config.convert_datetimes_to_utc:
            def _change_tz(value):
                if value.tzinfo == None:
                    value = value.replace(tzinfo=SG_TIMEZONE.local)
                return value.astimezone(SG_TIMEZONE.utc)
        else:
            _change_tz = None

        local_now = datetime.datetime.now()

        def _outbound_visitor(value):

            if isinstance(value, datetime.datetime):
                if _change_tz:
                    value = _change_tz(value)

                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            if isinstance(value, datetime.date):
                #existing code did not tz transform dates.
                return value.strftime("%Y-%m-%d")

            if isinstance(value, datetime.time):
                value = local_now.replace(hour=value.hour,
                    minute=value.minute, second=value.second,
                    microsecond=value.microsecond)
                if _change_tz:
                    value = _change_tz(value)
                return value.strftime("%Y-%m-%dT%H:%M:%SZ")

            if isinstance(value, str):
                # Convert strings to unicode
                return value.decode("utf-8")

            return value

        return self._visit_data(data, _outbound_visitor)

    def _transform_inbound(self, data):
        """Transforms data types or values after they are received from the
        server."""
        #NOTE: The time zone is removed from the time after it is transformed
        #to the local time, otherwise it will fail to compare to datetimes
        #that do not have a time zone.
        if self.config.convert_datetimes_to_utc:
            _change_tz = lambda x: x.replace(tzinfo=SG_TIMEZONE.utc)\
                .astimezone(SG_TIMEZONE.local)
        else:
            _change_tz = None

        def _inbound_visitor(value):
            if isinstance(value, basestring):
                if len(value) == 20 and self._DATE_TIME_PATTERN.match(value):
                    try:
                        # strptime was not on datetime in python2.4
                        value = datetime.datetime(
                            *time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")[:6])
                    except ValueError:
                        return value
                    if _change_tz:
                        return _change_tz(value)
                    return value

            return value

        return self._visit_data(data, _inbound_visitor)

    # ========================================================================
    # Connection Functions

    def _get_connection(self):
        """Returns the current connection or creates a new connection to the
        current server.
        """
        if self._connection is not None:
            return self._connection

        if self.config.proxy_server:
            pi = ProxyInfo(socks.PROXY_TYPE_HTTP, self.config.proxy_server,
                 self.config.proxy_port, proxy_user=self.config.proxy_user,
                 proxy_pass=self.config.proxy_pass)
            self._connection = Http(timeout=self.config.timeout_secs, ca_certs=self.__ca_certs,
                proxy_info=pi, disable_ssl_certificate_validation=self.config.no_ssl_validation)
        else:
            self._connection = Http(timeout=self.config.timeout_secs, ca_certs=self.__ca_certs,
                disable_ssl_certificate_validation=self.config.no_ssl_validation)

        return self._connection

    def _close_connection(self):
        """Closes the current connection."""
        if self._connection is None:
            return

        for conn in self._connection.connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connection.connections.clear()
        self._connection = None
        return
    # ========================================================================
    # Utility

    def _parse_records(self, records):
        """Parses 'records' returned from the api to do local modifications:

        - Insert thumbnail urls
        - Insert local file paths.
        - Revert &lt; html entities that may be the result of input sanitization
          mechanisms back to a litteral < character.

        :param records: List of records (dicts) to process or a single record.

        :returns: A list of the records processed.
        """

        if not records:
            return []

        if not isinstance(records, (list, tuple)):
            records = [records, ]

        for rec in records:
            # skip results that aren't entity dictionaries
            if not isinstance(rec, dict):
                continue

            # iterate over each item and check each field for possible injection
            for k, v in rec.iteritems():
                if not v:
                    continue

                # Check for html entities in strings
                if isinstance(v, types.StringTypes):
                    rec[k] = rec[k].replace('&lt;', '<')

                # check for thumbnail for older version (<3.3.0) of shotgun
                if k == 'image' and \
                   self.server_caps.version and \
                   self.server_caps.version < (3, 3, 0):
                    rec['image'] = self._build_thumb_url(rec['type'],
                        rec['id'])
                    continue

                if isinstance(v, dict) and v.get('link_type') == 'local' \
                    and self.client_caps.local_path_field in v:
                    local_path = v[self.client_caps.local_path_field]
                    v['local_path'] = local_path
                    v['url'] = "file://%s" % (local_path or "",)

        return records

    def _build_thumb_url(self, entity_type, entity_id):
        """Returns the URL for the thumbnail of an entity given the
        entity type and the entity id.

        Note: This makes a call to the server for every thumbnail.

        :param entity_type: Entity type the id is for.

        :param entity_id: id of the entity to get the thumbnail for.

        :returns: Fully qualified url to the thumbnail.
        """
        # Example response from the end point
        # curl "https://foo.com/upload/get_thumbnail_url?entity_type=Version&entity_id=1"
        # 1
        # /files/0000/0000/0012/232/shot_thumb.jpg.jpg
        entity_info = {'e_type':urllib.quote(entity_type),
                       'e_id':urllib.quote(str(entity_id))}
        url = ("/upload/get_thumbnail_url?" +
                "entity_type=%(e_type)s&entity_id=%(e_id)s" % entity_info)

        body = self._make_call("GET", url, None, None)[2]

        code, thumb_url = body.splitlines()
        code = int(code)

        #code of 0 means error, second line is the error code
        if code == 0:
            raise ShotgunError(thumb_url)

        if code == 1:
            return urlparse.urlunparse((self.config.scheme,
                self.config.server, thumb_url.strip(), None, None, None))

        # Comments in prev version said we can get this sometimes.
        raise RuntimeError("Unknown code %s %s" % (code, thumb_url))

    def _dict_to_list(self, d, key_name="field_name", value_name="value"):
        """Utility function to convert a dict into a list dicts using the
        key_name and value_name keys.

        e.g. d {'foo' : 'bar'} changed to [{'field_name':'foo, 'value':'bar'}]
        """

        return [
            {key_name : k, value_name : v }
            for k, v in (d or {}).iteritems()
        ]


# Helpers from the previous API, left as is.

# Based on http://code.activestate.com/recipes/146306/
class FormPostHandler(urllib2.BaseHandler):
    """
    Handler for multipart form data
    """
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and not isinstance(data, basestring):
            files = []
            params = []
            for key, value in data.items():
                if isinstance(value, file):
                    files.append((key, value))
                else:
                    params.append((key, value))
            if not files:
                data = urllib.urlencode(params, True) # sequencing on
            else:
                boundary, data = self.encode(params, files)
                content_type = 'multipart/form-data; boundary=%s' % boundary
                request.add_unredirected_header('Content-Type', content_type)
            request.add_data(data)
        return request

    def encode(self, params, files, boundary=None, buffer=None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buffer is None:
            buffer = cStringIO.StringIO()
        for (key, value) in params:
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"' % key)
            buffer.write('\r\n\r\n%s\r\n' % value)
        for (key, fd) in files:
            filename = fd.name.split('/')[-1]
            content_type = mimetypes.guess_type(filename)[0]
            content_type = content_type or 'application/octet-stream'
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            buffer.write('--%s\r\n' % boundary)
            c_dis = 'Content-Disposition: form-data; name="%s"; filename="%s"%s'
            content_disposition = c_dis % (key, filename, '\r\n')
            buffer.write(content_disposition)
            buffer.write('Content-Type: %s\r\n' % content_type)
            buffer.write('Content-Length: %s\r\n' % file_size)
            fd.seek(0)
            buffer.write('\r\n%s\r\n' % fd.read())
        buffer.write('--%s--\r\n\r\n' % boundary)
        buffer = buffer.getvalue()
        return boundary, buffer

    def https_request(self, request):
        return self.http_request(request)


def _translate_filters(filters, filter_operator):
    '''_translate_filters translates filters params into data structure
    expected by rpc call.'''
    wrapped_filters = {
        "filter_operator": filter_operator or "all",
        "filters": filters
    }

    return _translate_filters_dict(wrapped_filters)

def _translate_filters_dict(sg_filter):
    new_filters = {}
    filter_operator = sg_filter.get("filter_operator")
    
    if filter_operator == "all" or filter_operator == "and":
        new_filters["logical_operator"] = "and"
    elif filter_operator == "any" or filter_operator == "or":
        new_filters["logical_operator"] = "or"
    else:
        raise ShotgunError("Invalid filter_operator %s" % filter_operator)

    if not isinstance(sg_filter["filters"], (list,tuple)):
        raise ShotgunError("Invalid filters, expected a list or a tuple, got %s" % sg_filter["filters"])
        
    new_filters["conditions"] = _translate_filters_list(sg_filter["filters"])
    
    return new_filters
    
def _translate_filters_list(filters):
    conditions = []
    
    for sg_filter in filters:
        if isinstance(sg_filter, (list,tuple)):
            conditions.append(_translate_filters_simple(sg_filter))
        elif isinstance(sg_filter, dict):
            conditions.append(_translate_filters_dict(sg_filter))
        else:
            raise ShotgunError("Invalid filters, expected a list, tuple or dict, got %s" % sg_filter)
    
    return conditions

def _translate_filters_simple(sg_filter):
    condition = {
        "path": sg_filter[0],
        "relation": sg_filter[1]
    }
    
    values = sg_filter[2:]
    if len(values) == 1 and isinstance(values[0], (list, tuple)):
        values = values[0]

    condition["values"] = values

    return condition

     

########NEW FILE########
__FILENAME__ = base
"""Base class for Shotgun API tests."""
import re
import unittest
from ConfigParser import ConfigParser


import mock

import shotgun_api3 as api
from shotgun_api3.shotgun import json
from shotgun_api3.shotgun import ServerCapabilities

CONFIG_PATH = 'tests/config'

class TestBase(unittest.TestCase):
    '''Base class for tests.

    Sets up mocking and database test data.'''

    def __init__(self, *args, **kws):
        unittest.TestCase.__init__(self, *args, **kws)
        self.human_user     = None
        self.project        = None
        self.shot           = None
        self.asset          = None
        self.version        = None
        self.note           = None
        self.task           = None
        self.ticket         = None
        self.human_password = None
        self.server_url     = None
        self.server_address = None
        self.connect        = False


    def setUp(self, auth_mode='ApiUser'):
        self.config = SgTestConfig()
        self.config.read_config(CONFIG_PATH)
        self.human_login    = self.config.human_login
        self.human_password = self.config.human_password
        self.server_url     = self.config.server_url
        self.script_name    = self.config.script_name
        self.api_key        = self.config.api_key
        self.http_proxy     = self.config.http_proxy
        self.session_uuid   = self.config.session_uuid

        if auth_mode == 'ApiUser':
            self.sg = api.Shotgun(self.config.server_url,
                                  self.config.script_name,
                                  self.config.api_key,
                                  http_proxy=self.config.http_proxy,
                                  connect=self.connect )
        elif auth_mode == 'HumanUser':
            self.sg = api.Shotgun(self.config.server_url,
                                  login=self.human_login,
                                  password=self.human_password,
                                  http_proxy=self.config.http_proxy,
                                  connect=self.connect )
        else:
            raise ValueError("Unknown value for auth_mode: %s" % auth_mode)

        if self.config.session_uuid:
            self.sg.set_session_uuid(self.config.session_uuid)


    def tearDown(self):
        self.sg = None


class MockTestBase(TestBase):
    '''Test base for tests mocking server interactions.'''
    def setUp(self):
        super(MockTestBase, self).setUp()
        #TODO see if there is another way to stop sg connecting
        self._setup_mock()
        self._setup_mock_data()


    def _setup_mock(self):
        """Setup mocking on the ShotgunClient to stop it calling a live server
        """
        #Replace the function used to make the final call to the server
        #eaiser than mocking the http connection + response
        self.sg._http_request = mock.Mock(spec=api.Shotgun._http_request,
                                          return_value=((200, "OK"), {}, None))

        #also replace the function that is called to get the http connection
        #to avoid calling the server. OK to return a mock as we will not use
        #it
        self.mock_conn = mock.Mock(spec=api.lib.httplib2.Http)
        #The Http objects connection property is a dict of connections
        #it is holding
        self.mock_conn.connections = dict()
        self.sg._connection = self.mock_conn
        self.sg._get_connection = mock.Mock(return_value=self.mock_conn)

        #create the server caps directly to say we have the correct version
        self.sg._server_caps = ServerCapabilities(self.sg.config.server,
                                                  {"version" : [2,4,0]})


    def _mock_http(self, data, headers=None, status=None):
        """Setup a mock response from the SG server.

        Only has an affect if the server has been mocked.
        """
        #test for a mock object rather than config.mock as some tests
        #force the mock to be created
        if not isinstance(self.sg._http_request, mock.Mock):
            return

        if not isinstance(data, basestring):
            data = json.dumps(data, ensure_ascii=False, encoding="utf-8")

        resp_headers = { 'cache-control': 'no-cache',
                         'connection': 'close',
                         'content-length': (data and str(len(data))) or 0 ,
                         'content-type': 'application/json; charset=utf-8',
                         'date': 'Wed, 13 Apr 2011 04:18:58 GMT',
                         'server': 'Apache/2.2.3 (CentOS)',
                         'status': '200 OK' }
        if headers:
            resp_headers.update(headers)

        if not status:
            status = (200, "OK")
        #create a new mock to reset call list etc.
        self._setup_mock()
        self.sg._http_request.return_value = (status, resp_headers, data)


    def _assert_http_method(self, method, params, check_auth=True):
        """Asserts _http_request is called with the method and params."""
        args, _ = self.sg._http_request.call_args
        arg_body = args[2]
        assert isinstance(arg_body, basestring)
        arg_body = json.loads(arg_body)

        arg_params = arg_body.get("params")

        self.assertEqual(method, arg_body["method_name"])
        if check_auth:
            auth = arg_params[0]
            self.assertEqual(self.script_name, auth["script_name"])
            self.assertEqual(self.api_key, auth["script_key"])

        if params:
            rpc_args = arg_params[len(arg_params)-1]
            self.assertEqual(params, rpc_args)


    def _setup_mock_data(self):
        self.human_user = { 'id':1,
                            'login':self.config.human_login,
                            'type':'HumanUser' }
        self.project    = { 'id':2,
                            'name':self.config.project_name,
                            'type':'Project' }
        self.shot       = { 'id':3,
                            'code':self.config.shot_code,
                            'type':'Shot' }
        self.asset      = { 'id':4,
                            'code':self.config.asset_code,
                            'type':'Asset' }
        self.version    = { 'id':5,
                            'code':self.config.version_code,
                            'type':'Version' }
        self.ticket    = { 'id':6,
                            'title':self.config.ticket_title,
                            'type':'Ticket' }

class LiveTestBase(TestBase):
    '''Test base for tests relying on connection to server.'''
    def setUp(self, auth_mode='ApiUser'):
        super(LiveTestBase, self).setUp(auth_mode)
        self.sg_version = self.sg.info()['version'][:3]
        self._setup_db(self.config)
        if self.sg.server_caps.version and \
           self.sg.server_caps.version >= (3, 3, 0) and \
           (self.sg.server_caps.host.startswith('0.0.0.0') or \
            self.sg.server_caps.host.startswith('127.0.0.1')):
                self.server_address = re.sub('^0.0.0.0|127.0.0.1', 'localhost', self.sg.server_caps.host)
        else:
            self.server_address = self.sg.server_caps.host

    def _setup_db(self, config):
        data = {'name':self.config.project_name}
        self.project = _find_or_create_entity(self.sg, 'Project', data)

        data = {'name':self.config.human_name,
                'login':self.config.human_login,
                'password_proxy':self.config.human_password}
        if self.sg_version >= (3, 0, 0):
            data['locked_until'] = None


        self.human_user = _find_or_create_entity(self.sg, 'HumanUser', data)

        data = {'code':self.config.asset_code,
                'project':self.project}
        keys = ['code']
        self.asset = _find_or_create_entity(self.sg, 'Asset', data, keys)

        data = {'project':self.project,
                'code':self.config.version_code,
                'entity':self.asset,
                'user':self.human_user,
                'sg_frames_aspect_ratio': 13.3,
                'frame_count': 33}
        keys = ['code','project']
        self.version = _find_or_create_entity(self.sg, 'Version', data, keys)

        keys = ['code','project']
        data = {'code':self.config.shot_code,
                'project':self.project}
        self.shot = _find_or_create_entity(self.sg, 'Shot', data, keys)

        keys = ['project','user']
        data = {'project':self.project,
                'user':self.human_user,
                'content':'anything'}
        self.note = _find_or_create_entity(self.sg, 'Note', data, keys)

        keys = ['code', 'entity_type']
        data = {'code': 'wrapper test step',
                'entity_type': 'Shot'}
        self.step = _find_or_create_entity(self.sg, 'Step', data, keys)

        keys = ['project', 'entity', 'content']
        data = {'project':self.project,
                'entity':self.asset,
                'content':self.config.task_content,
                'color':'Black',
                'due_date':'1968-10-13',
                'task_assignees': [self.human_user],
                'sg_status_list': 'ip'}
        self.task =  _find_or_create_entity(self.sg, 'Task', data, keys)

        data = {'project':self.project,
                'title':self.config.ticket_title,
                'sg_priority': '3'}
        keys = ['title','project', 'sg_priority']
        self.ticket = _find_or_create_entity(self.sg, 'Ticket', data, keys)

        keys = ['code']
        data = {'code':'api wrapper test storage',
                'mac_path':'nowhere',
                'windows_path':'nowhere',
                'linux_path':'nowhere'}

        self.local_storage = _find_or_create_entity(self.sg, 'LocalStorage', data, keys)


class HumanUserAuthLiveTestBase(LiveTestBase):
    '''
    Test base for relying on a Shotgun connection authenticate through the
    configured login/password pair.
    '''
    def setUp(self):
        super(HumanUserAuthLiveTestBase, self).setUp('HumanUser')


class SgTestConfig(object):
    '''Reads test config and holds values'''
    def __init__(self):
        self.mock           = True
        self.server_url     = None
        self.script_name    = None
        self.api_key        = None
        self.http_proxy     = None
        self.session_uuid   = None
        self.project_name   = None
        self.human_name     = None
        self.human_login    = None
        self.human_password = None
        self.asset_code     = None
        self.version_code   = None
        self.shot_code      = None
        self.task_content   = None


    def read_config(self, config_path):
        config_parser = ConfigParser()
        config_parser.read(config_path)
        for section in config_parser.sections():
            for option in config_parser.options(section):
                value = config_parser.get(section, option)
                setattr(self, option, value)


def _find_or_create_entity(sg, entity_type, data, identifyiers=None):
    '''Finds or creates entities.
    @params:
        sg           - shogun_json.Shotgun instance
        entity_type  - entity type
        data         - dictionary of data for the entity
        identifyiers -list of subset of keys from data which should be used to
                      uniquely identity the entity
    @returns dicitonary of the entity values
    '''
    identifyiers = identifyiers or ['name']
    fields = data.keys()
    filters = [[key, 'is', data[key]] for key in identifyiers]
    entity = sg.find_one(entity_type, filters, fields=fields)
    entity = entity or sg.create(entity_type, data, return_fields=fields)
    assert(entity)
    return entity


########NEW FILE########
__FILENAME__ = dummy_data
"""Dummy data returned for schema functions when mocking the server.

NOTE: Mostly abbreviated version of real data returned from the server. 
"""

schema_entity_read = {u'Version': {u'name': {u'editable': False, u'value': u'Version'}}}

schema_read = {
    u'Version' : {u'code': {u'data_type': {u'editable': False, u'value': u'text'},
           u'description': {u'editable': True, u'value': u''},
           u'editable': {u'editable': False, u'value': True},
           u'entity_type': {u'editable': False, u'value': u'Version'},
           u'mandatory': {u'editable': False, u'value': True},
           u'name': {u'editable': True, u'value': u'Version Name'},
           u'properties': {u'default_value': {u'editable': False,
                                              u'value': None},
                           u'summary_default': {u'editable': True,
                                                u'value': u'none'}}},
 u'created_at': {u'data_type': {u'editable': False, u'value': u'date_time'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Date Created'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'}}},
 u'created_by': {u'data_type': {u'editable': False, u'value': u'entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Created by'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'HumanUser',
                                                             u'ApiUser']}}},
 u'description': {u'data_type': {u'editable': False, u'value': u'text'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Description'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'entity': {u'data_type': {u'editable': False, u'value': u'entity'},
             u'description': {u'editable': True, u'value': u''},
             u'editable': {u'editable': False, u'value': True},
             u'entity_type': {u'editable': False, u'value': u'Version'},
             u'mandatory': {u'editable': False, u'value': False},
             u'name': {u'editable': True, u'value': u'Link'},
             u'properties': {u'default_value': {u'editable': False,
                                                u'value': None},
                             u'summary_default': {u'editable': True,
                                                  u'value': u'none'},
                             u'valid_types': {u'editable': True,
                                              u'value': [u'Asset',
                                                         u'Scene',
                                                         u'Sequence',
                                                         u'Shot']}}},
 u'frame_count': {u'data_type': {u'editable': False, u'value': u'number'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Frame Count'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'frame_range': {u'data_type': {u'editable': False, u'value': u'text'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Frame Range'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'id': {u'data_type': {u'editable': False, u'value': u'number'},
         u'description': {u'editable': True, u'value': u''},
         u'editable': {u'editable': False, u'value': False},
         u'entity_type': {u'editable': False, u'value': u'Version'},
         u'mandatory': {u'editable': False, u'value': False},
         u'name': {u'editable': True, u'value': u'Id'},
         u'properties': {u'default_value': {u'editable': False,
                                            u'value': None},
                         u'summary_default': {u'editable': True,
                                              u'value': u'none'}}},
 u'image': {u'data_type': {u'editable': False, u'value': u'image'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Thumbnail'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'}}},
 u'notes': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Notes'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'},
                            u'valid_types': {u'editable': True,
                                             u'value': [u'Note']}}},
 u'open_notes': {u'data_type': {u'editable': False,
                                u'value': u'multi_entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Open Notes'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'Note']}}},
 u'open_notes_count': {u'data_type': {u'editable': False, u'value': u'text'},
                       u'description': {u'editable': True, u'value': u''},
                       u'editable': {u'editable': False, u'value': False},
                       u'entity_type': {u'editable': False,
                                        u'value': u'Version'},
                       u'mandatory': {u'editable': False, u'value': False},
                       u'name': {u'editable': True,
                                 u'value': u'Open Notes Count'},
                       u'properties': {u'default_value': {u'editable': False,
                                                          u'value': None},
                                       u'summary_default': {u'editable': True,
                                                            u'value': u'none'}}},
 u'playlists': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
                u'description': {u'editable': True, u'value': u''},
                u'editable': {u'editable': False, u'value': True},
                u'entity_type': {u'editable': False, u'value': u'Version'},
                u'mandatory': {u'editable': False, u'value': False},
                u'name': {u'editable': True, u'value': u'Playlists'},
                u'properties': {u'default_value': {u'editable': False,
                                                   u'value': None},
                                u'summary_default': {u'editable': True,
                                                     u'value': u'none'},
                                u'valid_types': {u'editable': True,
                                                 u'value': [u'Playlist']}}},
 u'project': {u'data_type': {u'editable': False, u'value': u'entity'},
              u'description': {u'editable': True, u'value': u''},
              u'editable': {u'editable': False, u'value': True},
              u'entity_type': {u'editable': False, u'value': u'Version'},
              u'mandatory': {u'editable': False, u'value': False},
              u'name': {u'editable': True, u'value': u'Project'},
              u'properties': {u'default_value': {u'editable': False,
                                                 u'value': None},
                              u'summary_default': {u'editable': True,
                                                   u'value': u'none'},
                              u'valid_types': {u'editable': True,
                                               u'value': [u'Project']}}},
 u'sg_department': {u'data_type': {u'editable': False, u'value': u'text'},
                    u'description': {u'editable': True,
                                     u'value': u'The department the Version was submitted from. This is used to find the latest Version from the same department.'},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Department'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'}}},
 u'sg_first_frame': {u'data_type': {u'editable': False, u'value': u'number'},
                     u'description': {u'editable': True,
                                      u'value': u'The first frame number contained in the Version. Used in playback of the movie or frames to calculate the first frame available in the Version.'},
                     u'editable': {u'editable': False, u'value': True},
                     u'entity_type': {u'editable': False,
                                      u'value': u'Version'},
                     u'mandatory': {u'editable': False, u'value': False},
                     u'name': {u'editable': True, u'value': u'First Frame'},
                     u'properties': {u'default_value': {u'editable': False,
                                                        u'value': None},
                                     u'summary_default': {u'editable': True,
                                                          u'value': u'none'}}},
 u'sg_frames_aspect_ratio': {u'data_type': {u'editable': False,
                                            u'value': u'float'},
                             u'description': {u'editable': True,
                                              u'value': u'Aspect ratio of the high res frames. Used to format the image correctly for viewing.'},
                             u'editable': {u'editable': False,
                                           u'value': True},
                             u'entity_type': {u'editable': False,
                                              u'value': u'Version'},
                             u'mandatory': {u'editable': False,
                                            u'value': False},
                             u'name': {u'editable': True,
                                       u'value': u'Frames Aspect Ratio'},
                             u'properties': {u'default_value': {u'editable': False,
                                                                u'value': None},
                                             u'summary_default': {u'editable': True,
                                                                  u'value': u'none'}}},
 u'sg_frames_have_slate': {u'data_type': {u'editable': False,
                                          u'value': u'checkbox'},
                           u'description': {u'editable': True,
                                            u'value': u'Indicates whether the frames have a slate or not. This is used to include or omit the slate from playback.'},
                           u'editable': {u'editable': False, u'value': True},
                           u'entity_type': {u'editable': False,
                                            u'value': u'Version'},
                           u'mandatory': {u'editable': False,
                                          u'value': False},
                           u'name': {u'editable': True,
                                     u'value': u'Frames Have Slate'},
                           u'properties': {u'default_value': {u'editable': False,
                                                              u'value': False},
                                           u'summary_default': {u'editable': True,
                                                                u'value': u'none'}}},
 u'sg_last_frame': {u'data_type': {u'editable': False, u'value': u'number'},
                    u'description': {u'editable': True,
                                     u'value': u'The last frame number contained in the Version. Used in playback of the movie or frames to calculate the last frame available in the Version.'},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Last Frame'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'}}},
 u'sg_movie_aspect_ratio': {u'data_type': {u'editable': False,
                                           u'value': u'float'},
                            u'description': {u'editable': True,
                                             u'value': u'Aspect ratio of the the movie. Used to format the image correctly for viewing.'},
                            u'editable': {u'editable': False, u'value': True},
                            u'entity_type': {u'editable': False,
                                             u'value': u'Version'},
                            u'mandatory': {u'editable': False,
                                           u'value': False},
                            u'name': {u'editable': True,
                                      u'value': u'Movie Aspect Ratio'},
                            u'properties': {u'default_value': {u'editable': False,
                                                               u'value': None},
                                            u'summary_default': {u'editable': True,
                                                                 u'value': u'none'}}},
 u'sg_movie_has_slate': {u'data_type': {u'editable': False,
                                        u'value': u'checkbox'},
                         u'description': {u'editable': True,
                                          u'value': u'Indicates whether the movie file has a slate or not. This is used to include or omit the slate from playback.'},
                         u'editable': {u'editable': False, u'value': True},
                         u'entity_type': {u'editable': False,
                                          u'value': u'Version'},
                         u'mandatory': {u'editable': False, u'value': False},
                         u'name': {u'editable': True,
                                   u'value': u'Movie Has Slate'},
                         u'properties': {u'default_value': {u'editable': False,
                                                            u'value': False},
                                         u'summary_default': {u'editable': True,
                                                              u'value': u'none'}}},
 u'sg_path_to_frames': {u'data_type': {u'editable': False, u'value': u'text'},
                        u'description': {u'editable': True,
                                         u'value': u'Location of the high res frames on your local filesystem. Used for playback of high resolution frames.'},
                        u'editable': {u'editable': False, u'value': True},
                        u'entity_type': {u'editable': False,
                                         u'value': u'Version'},
                        u'mandatory': {u'editable': False, u'value': False},
                        u'name': {u'editable': True,
                                  u'value': u'Path to Frames'},
                        u'properties': {u'default_value': {u'editable': False,
                                                           u'value': None},
                                        u'summary_default': {u'editable': True,
                                                             u'value': u'none'}}},
 u'sg_path_to_movie': {u'data_type': {u'editable': False, u'value': u'text'},
                       u'description': {u'editable': True,
                                        u'value': u'Location of the movie on your local filesystem (not uploaded). Used for playback of lower resolution movie media stored locally.'},
                       u'editable': {u'editable': False, u'value': True},
                       u'entity_type': {u'editable': False,
                                        u'value': u'Version'},
                       u'mandatory': {u'editable': False, u'value': False},
                       u'name': {u'editable': True,
                                 u'value': u'Path to Movie'},
                       u'properties': {u'default_value': {u'editable': False,
                                                          u'value': None},
                                       u'summary_default': {u'editable': True,
                                                            u'value': u'none'}}},
 u'sg_status_list': {u'data_type': {u'editable': False,
                                    u'value': u'status_list'},
                     u'description': {u'editable': True, u'value': u''},
                     u'editable': {u'editable': False, u'value': True},
                     u'entity_type': {u'editable': False,
                                      u'value': u'Version'},
                     u'mandatory': {u'editable': False, u'value': False},
                     u'name': {u'editable': True, u'value': u'Status'},
                     u'properties': {u'default_value': {u'editable': True,
                                                        u'value': u'rev'},
                                     u'summary_default': {u'editable': True,
                                                          u'value': u'status_list'},
                                     u'valid_values': {u'editable': True,
                                                       u'value': [u'na',
                                                                  u'rev',
                                                                  u'vwd']}}},
 u'sg_task': {u'data_type': {u'editable': False, u'value': u'entity'},
              u'description': {u'editable': True, u'value': u''},
              u'editable': {u'editable': False, u'value': True},
              u'entity_type': {u'editable': False, u'value': u'Version'},
              u'mandatory': {u'editable': False, u'value': False},
              u'name': {u'editable': True, u'value': u'Task'},
              u'properties': {u'default_value': {u'editable': False,
                                                 u'value': None},
                              u'summary_default': {u'editable': True,
                                                   u'value': u'none'},
                              u'valid_types': {u'editable': True,
                                               u'value': [u'Task']}}},
 u'sg_uploaded_movie': {u'data_type': {u'editable': False, u'value': u'url'},
                        u'description': {u'editable': True,
                                         u'value': u'File field to contain the uploaded movie file. Used for playback of lower resolution movie media stored in Shotgun.'},
                        u'editable': {u'editable': False, u'value': True},
                        u'entity_type': {u'editable': False,
                                         u'value': u'Version'},
                        u'mandatory': {u'editable': False, u'value': False},
                        u'name': {u'editable': True,
                                  u'value': u'Uploaded Movie'},
                        u'properties': {u'default_value': {u'editable': False,
                                                           u'value': None},
                                        u'open_in_new_window': {u'editable': True,
                                                                u'value': True},
                                        u'summary_default': {u'editable': True,
                                                             u'value': u'none'}}},
 u'sg_version_type': {u'data_type': {u'editable': False, u'value': u'list'},
                      u'description': {u'editable': True, u'value': u''},
                      u'editable': {u'editable': False, u'value': True},
                      u'entity_type': {u'editable': False,
                                       u'value': u'Version'},
                      u'mandatory': {u'editable': False, u'value': False},
                      u'name': {u'editable': True, u'value': u'Type'},
                      u'properties': {u'default_value': {u'editable': False,
                                                         u'value': None},
                                      u'summary_default': {u'editable': True,
                                                           u'value': u'none'},
                                      u'valid_values': {u'editable': True,
                                                        u'value': []}}},
 u'step_0': {u'data_type': {u'editable': False, u'value': u'pivot_column'},
             u'description': {u'editable': True, u'value': u''},
             u'editable': {u'editable': False, u'value': False},
             u'entity_type': {u'editable': False, u'value': u'Version'},
             u'mandatory': {u'editable': False, u'value': False},
             u'name': {u'editable': True, u'value': u'ALL TASKS'},
             u'properties': {u'default_value': {u'editable': False,
                                                u'value': None},
                             u'summary_default': {u'editable': False,
                                                  u'value': u'none'}}},
 u'tag_list': {u'data_type': {u'editable': False, u'value': u'tag_list'},
               u'description': {u'editable': True, u'value': u''},
               u'editable': {u'editable': False, u'value': True},
               u'entity_type': {u'editable': False, u'value': u'Version'},
               u'mandatory': {u'editable': False, u'value': False},
               u'name': {u'editable': True, u'value': u'Tags'},
               u'properties': {u'default_value': {u'editable': False,
                                                  u'value': None},
                               u'summary_default': {u'editable': True,
                                                    u'value': u'none'},
                               u'valid_types': {u'editable': True,
                                                u'value': [u'Tag']}}},
 u'task_template': {u'data_type': {u'editable': False, u'value': u'entity'},
                    u'description': {u'editable': True, u'value': u''},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Task Template'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'},
                                    u'valid_types': {u'editable': True,
                                                     u'value': [u'TaskTemplate']}}},
 u'tasks': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Tasks'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'},
                            u'valid_types': {u'editable': True,
                                             u'value': [u'Task']}}},
 u'updated_at': {u'data_type': {u'editable': False, u'value': u'date_time'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Date Updated'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'}}},
 u'updated_by': {u'data_type': {u'editable': False, u'value': u'entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Updated by'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'HumanUser',
                                                             u'ApiUser']}}},
 u'user': {u'data_type': {u'editable': False, u'value': u'entity'},
           u'description': {u'editable': True, u'value': u''},
           u'editable': {u'editable': False, u'value': True},
           u'entity_type': {u'editable': False, u'value': u'Version'},
           u'mandatory': {u'editable': False, u'value': False},
           u'name': {u'editable': True, u'value': u'Artist'},
           u'properties': {u'default_value': {u'editable': False,
                                              u'value': None},
                           u'summary_default': {u'editable': True,
                                                u'value': u'none'},
                           u'valid_types': {u'editable': True,
                                            u'value': [u'HumanUser',
                                                       u'ApiUser']}}}
}}








schema_field_read_version = {u'code': {u'data_type': {u'editable': False, u'value': u'text'},
           u'description': {u'editable': True, u'value': u''},
           u'editable': {u'editable': False, u'value': True},
           u'entity_type': {u'editable': False, u'value': u'Version'},
           u'mandatory': {u'editable': False, u'value': True},
           u'name': {u'editable': True, u'value': u'Version Name'},
           u'properties': {u'default_value': {u'editable': False,
                                              u'value': None},
                           u'summary_default': {u'editable': True,
                                                u'value': u'none'}}},
 u'created_at': {u'data_type': {u'editable': False, u'value': u'date_time'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Date Created'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'}}},
 u'created_by': {u'data_type': {u'editable': False, u'value': u'entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Created by'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'HumanUser',
                                                             u'ApiUser']}}},
 u'description': {u'data_type': {u'editable': False, u'value': u'text'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Description'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'entity': {u'data_type': {u'editable': False, u'value': u'entity'},
             u'description': {u'editable': True, u'value': u''},
             u'editable': {u'editable': False, u'value': True},
             u'entity_type': {u'editable': False, u'value': u'Version'},
             u'mandatory': {u'editable': False, u'value': False},
             u'name': {u'editable': True, u'value': u'Link'},
             u'properties': {u'default_value': {u'editable': False,
                                                u'value': None},
                             u'summary_default': {u'editable': True,
                                                  u'value': u'none'},
                             u'valid_types': {u'editable': True,
                                              u'value': [u'Asset',
                                                         u'Scene',
                                                         u'Sequence',
                                                         u'Shot']}}},
 u'frame_count': {u'data_type': {u'editable': False, u'value': u'number'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Frame Count'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'frame_range': {u'data_type': {u'editable': False, u'value': u'text'},
                  u'description': {u'editable': True, u'value': u''},
                  u'editable': {u'editable': False, u'value': True},
                  u'entity_type': {u'editable': False, u'value': u'Version'},
                  u'mandatory': {u'editable': False, u'value': False},
                  u'name': {u'editable': True, u'value': u'Frame Range'},
                  u'properties': {u'default_value': {u'editable': False,
                                                     u'value': None},
                                  u'summary_default': {u'editable': True,
                                                       u'value': u'none'}}},
 u'id': {u'data_type': {u'editable': False, u'value': u'number'},
         u'description': {u'editable': True, u'value': u''},
         u'editable': {u'editable': False, u'value': False},
         u'entity_type': {u'editable': False, u'value': u'Version'},
         u'mandatory': {u'editable': False, u'value': False},
         u'name': {u'editable': True, u'value': u'Id'},
         u'properties': {u'default_value': {u'editable': False,
                                            u'value': None},
                         u'summary_default': {u'editable': True,
                                              u'value': u'none'}}},
 u'image': {u'data_type': {u'editable': False, u'value': u'image'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Thumbnail'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'}}},
 u'notes': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Notes'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'},
                            u'valid_types': {u'editable': True,
                                             u'value': [u'Note']}}},
 u'open_notes': {u'data_type': {u'editable': False,
                                u'value': u'multi_entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Open Notes'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'Note']}}},
 u'open_notes_count': {u'data_type': {u'editable': False, u'value': u'text'},
                       u'description': {u'editable': True, u'value': u''},
                       u'editable': {u'editable': False, u'value': False},
                       u'entity_type': {u'editable': False,
                                        u'value': u'Version'},
                       u'mandatory': {u'editable': False, u'value': False},
                       u'name': {u'editable': True,
                                 u'value': u'Open Notes Count'},
                       u'properties': {u'default_value': {u'editable': False,
                                                          u'value': None},
                                       u'summary_default': {u'editable': True,
                                                            u'value': u'none'}}},
 u'playlists': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
                u'description': {u'editable': True, u'value': u''},
                u'editable': {u'editable': False, u'value': True},
                u'entity_type': {u'editable': False, u'value': u'Version'},
                u'mandatory': {u'editable': False, u'value': False},
                u'name': {u'editable': True, u'value': u'Playlists'},
                u'properties': {u'default_value': {u'editable': False,
                                                   u'value': None},
                                u'summary_default': {u'editable': True,
                                                     u'value': u'none'},
                                u'valid_types': {u'editable': True,
                                                 u'value': [u'Playlist']}}},
 u'project': {u'data_type': {u'editable': False, u'value': u'entity'},
              u'description': {u'editable': True, u'value': u''},
              u'editable': {u'editable': False, u'value': True},
              u'entity_type': {u'editable': False, u'value': u'Version'},
              u'mandatory': {u'editable': False, u'value': False},
              u'name': {u'editable': True, u'value': u'Project'},
              u'properties': {u'default_value': {u'editable': False,
                                                 u'value': None},
                              u'summary_default': {u'editable': True,
                                                   u'value': u'none'},
                              u'valid_types': {u'editable': True,
                                               u'value': [u'Project']}}},
 u'sg_department': {u'data_type': {u'editable': False, u'value': u'text'},
                    u'description': {u'editable': True,
                                     u'value': u'The department the Version was submitted from. This is used to find the latest Version from the same department.'},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Department'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'}}},
 u'sg_first_frame': {u'data_type': {u'editable': False, u'value': u'number'},
                     u'description': {u'editable': True,
                                      u'value': u'The first frame number contained in the Version. Used in playback of the movie or frames to calculate the first frame available in the Version.'},
                     u'editable': {u'editable': False, u'value': True},
                     u'entity_type': {u'editable': False,
                                      u'value': u'Version'},
                     u'mandatory': {u'editable': False, u'value': False},
                     u'name': {u'editable': True, u'value': u'First Frame'},
                     u'properties': {u'default_value': {u'editable': False,
                                                        u'value': None},
                                     u'summary_default': {u'editable': True,
                                                          u'value': u'none'}}},
 u'sg_frames_aspect_ratio': {u'data_type': {u'editable': False,
                                            u'value': u'float'},
                             u'description': {u'editable': True,
                                              u'value': u'Aspect ratio of the high res frames. Used to format the image correctly for viewing.'},
                             u'editable': {u'editable': False,
                                           u'value': True},
                             u'entity_type': {u'editable': False,
                                              u'value': u'Version'},
                             u'mandatory': {u'editable': False,
                                            u'value': False},
                             u'name': {u'editable': True,
                                       u'value': u'Frames Aspect Ratio'},
                             u'properties': {u'default_value': {u'editable': False,
                                                                u'value': None},
                                             u'summary_default': {u'editable': True,
                                                                  u'value': u'none'}}},
 u'sg_frames_have_slate': {u'data_type': {u'editable': False,
                                          u'value': u'checkbox'},
                           u'description': {u'editable': True,
                                            u'value': u'Indicates whether the frames have a slate or not. This is used to include or omit the slate from playback.'},
                           u'editable': {u'editable': False, u'value': True},
                           u'entity_type': {u'editable': False,
                                            u'value': u'Version'},
                           u'mandatory': {u'editable': False,
                                          u'value': False},
                           u'name': {u'editable': True,
                                     u'value': u'Frames Have Slate'},
                           u'properties': {u'default_value': {u'editable': False,
                                                              u'value': False},
                                           u'summary_default': {u'editable': True,
                                                                u'value': u'none'}}},
 u'sg_last_frame': {u'data_type': {u'editable': False, u'value': u'number'},
                    u'description': {u'editable': True,
                                     u'value': u'The last frame number contained in the Version. Used in playback of the movie or frames to calculate the last frame available in the Version.'},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Last Frame'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'}}},
 u'sg_movie_aspect_ratio': {u'data_type': {u'editable': False,
                                           u'value': u'float'},
                            u'description': {u'editable': True,
                                             u'value': u'Aspect ratio of the the movie. Used to format the image correctly for viewing.'},
                            u'editable': {u'editable': False, u'value': True},
                            u'entity_type': {u'editable': False,
                                             u'value': u'Version'},
                            u'mandatory': {u'editable': False,
                                           u'value': False},
                            u'name': {u'editable': True,
                                      u'value': u'Movie Aspect Ratio'},
                            u'properties': {u'default_value': {u'editable': False,
                                                               u'value': None},
                                            u'summary_default': {u'editable': True,
                                                                 u'value': u'none'}}},
 u'sg_movie_has_slate': {u'data_type': {u'editable': False,
                                        u'value': u'checkbox'},
                         u'description': {u'editable': True,
                                          u'value': u'Indicates whether the movie file has a slate or not. This is used to include or omit the slate from playback.'},
                         u'editable': {u'editable': False, u'value': True},
                         u'entity_type': {u'editable': False,
                                          u'value': u'Version'},
                         u'mandatory': {u'editable': False, u'value': False},
                         u'name': {u'editable': True,
                                   u'value': u'Movie Has Slate'},
                         u'properties': {u'default_value': {u'editable': False,
                                                            u'value': False},
                                         u'summary_default': {u'editable': True,
                                                              u'value': u'none'}}},
 u'sg_path_to_frames': {u'data_type': {u'editable': False, u'value': u'text'},
                        u'description': {u'editable': True,
                                         u'value': u'Location of the high res frames on your local filesystem. Used for playback of high resolution frames.'},
                        u'editable': {u'editable': False, u'value': True},
                        u'entity_type': {u'editable': False,
                                         u'value': u'Version'},
                        u'mandatory': {u'editable': False, u'value': False},
                        u'name': {u'editable': True,
                                  u'value': u'Path to Frames'},
                        u'properties': {u'default_value': {u'editable': False,
                                                           u'value': None},
                                        u'summary_default': {u'editable': True,
                                                             u'value': u'none'}}},
 u'sg_path_to_movie': {u'data_type': {u'editable': False, u'value': u'text'},
                       u'description': {u'editable': True,
                                        u'value': u'Location of the movie on your local filesystem (not uploaded). Used for playback of lower resolution movie media stored locally.'},
                       u'editable': {u'editable': False, u'value': True},
                       u'entity_type': {u'editable': False,
                                        u'value': u'Version'},
                       u'mandatory': {u'editable': False, u'value': False},
                       u'name': {u'editable': True,
                                 u'value': u'Path to Movie'},
                       u'properties': {u'default_value': {u'editable': False,
                                                          u'value': None},
                                       u'summary_default': {u'editable': True,
                                                            u'value': u'none'}}},
 u'sg_status_list': {u'data_type': {u'editable': False,
                                    u'value': u'status_list'},
                     u'description': {u'editable': True, u'value': u''},
                     u'editable': {u'editable': False, u'value': True},
                     u'entity_type': {u'editable': False,
                                      u'value': u'Version'},
                     u'mandatory': {u'editable': False, u'value': False},
                     u'name': {u'editable': True, u'value': u'Status'},
                     u'properties': {u'default_value': {u'editable': True,
                                                        u'value': u'rev'},
                                     u'summary_default': {u'editable': True,
                                                          u'value': u'status_list'},
                                     u'valid_values': {u'editable': True,
                                                       u'value': [u'na',
                                                                  u'rev',
                                                                  u'vwd']}}},
 u'sg_task': {u'data_type': {u'editable': False, u'value': u'entity'},
              u'description': {u'editable': True, u'value': u''},
              u'editable': {u'editable': False, u'value': True},
              u'entity_type': {u'editable': False, u'value': u'Version'},
              u'mandatory': {u'editable': False, u'value': False},
              u'name': {u'editable': True, u'value': u'Task'},
              u'properties': {u'default_value': {u'editable': False,
                                                 u'value': None},
                              u'summary_default': {u'editable': True,
                                                   u'value': u'none'},
                              u'valid_types': {u'editable': True,
                                               u'value': [u'Task']}}},
 u'sg_uploaded_movie': {u'data_type': {u'editable': False, u'value': u'url'},
                        u'description': {u'editable': True,
                                         u'value': u'File field to contain the uploaded movie file. Used for playback of lower resolution movie media stored in Shotgun.'},
                        u'editable': {u'editable': False, u'value': True},
                        u'entity_type': {u'editable': False,
                                         u'value': u'Version'},
                        u'mandatory': {u'editable': False, u'value': False},
                        u'name': {u'editable': True,
                                  u'value': u'Uploaded Movie'},
                        u'properties': {u'default_value': {u'editable': False,
                                                           u'value': None},
                                        u'open_in_new_window': {u'editable': True,
                                                                u'value': True},
                                        u'summary_default': {u'editable': True,
                                                             u'value': u'none'}}},
 u'sg_version_type': {u'data_type': {u'editable': False, u'value': u'list'},
                      u'description': {u'editable': True, u'value': u''},
                      u'editable': {u'editable': False, u'value': True},
                      u'entity_type': {u'editable': False,
                                       u'value': u'Version'},
                      u'mandatory': {u'editable': False, u'value': False},
                      u'name': {u'editable': True, u'value': u'Type'},
                      u'properties': {u'default_value': {u'editable': False,
                                                         u'value': None},
                                      u'summary_default': {u'editable': True,
                                                           u'value': u'none'},
                                      u'valid_values': {u'editable': True,
                                                        u'value': []}}},
 u'step_0': {u'data_type': {u'editable': False, u'value': u'pivot_column'},
             u'description': {u'editable': True, u'value': u''},
             u'editable': {u'editable': False, u'value': False},
             u'entity_type': {u'editable': False, u'value': u'Version'},
             u'mandatory': {u'editable': False, u'value': False},
             u'name': {u'editable': True, u'value': u'ALL TASKS'},
             u'properties': {u'default_value': {u'editable': False,
                                                u'value': None},
                             u'summary_default': {u'editable': False,
                                                  u'value': u'none'}}},
 u'tag_list': {u'data_type': {u'editable': False, u'value': u'tag_list'},
               u'description': {u'editable': True, u'value': u''},
               u'editable': {u'editable': False, u'value': True},
               u'entity_type': {u'editable': False, u'value': u'Version'},
               u'mandatory': {u'editable': False, u'value': False},
               u'name': {u'editable': True, u'value': u'Tags'},
               u'properties': {u'default_value': {u'editable': False,
                                                  u'value': None},
                               u'summary_default': {u'editable': True,
                                                    u'value': u'none'},
                               u'valid_types': {u'editable': True,
                                                u'value': [u'Tag']}}},
 u'task_template': {u'data_type': {u'editable': False, u'value': u'entity'},
                    u'description': {u'editable': True, u'value': u''},
                    u'editable': {u'editable': False, u'value': True},
                    u'entity_type': {u'editable': False,
                                     u'value': u'Version'},
                    u'mandatory': {u'editable': False, u'value': False},
                    u'name': {u'editable': True, u'value': u'Task Template'},
                    u'properties': {u'default_value': {u'editable': False,
                                                       u'value': None},
                                    u'summary_default': {u'editable': True,
                                                         u'value': u'none'},
                                    u'valid_types': {u'editable': True,
                                                     u'value': [u'TaskTemplate']}}},
 u'tasks': {u'data_type': {u'editable': False, u'value': u'multi_entity'},
            u'description': {u'editable': True, u'value': u''},
            u'editable': {u'editable': False, u'value': True},
            u'entity_type': {u'editable': False, u'value': u'Version'},
            u'mandatory': {u'editable': False, u'value': False},
            u'name': {u'editable': True, u'value': u'Tasks'},
            u'properties': {u'default_value': {u'editable': False,
                                               u'value': None},
                            u'summary_default': {u'editable': True,
                                                 u'value': u'none'},
                            u'valid_types': {u'editable': True,
                                             u'value': [u'Task']}}},
 u'updated_at': {u'data_type': {u'editable': False, u'value': u'date_time'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Date Updated'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'}}},
 u'updated_by': {u'data_type': {u'editable': False, u'value': u'entity'},
                 u'description': {u'editable': True, u'value': u''},
                 u'editable': {u'editable': False, u'value': False},
                 u'entity_type': {u'editable': False, u'value': u'Version'},
                 u'mandatory': {u'editable': False, u'value': False},
                 u'name': {u'editable': True, u'value': u'Updated by'},
                 u'properties': {u'default_value': {u'editable': False,
                                                    u'value': None},
                                 u'summary_default': {u'editable': True,
                                                      u'value': u'none'},
                                 u'valid_types': {u'editable': True,
                                                  u'value': [u'HumanUser',
                                                             u'ApiUser']}}},
 u'user': {u'data_type': {u'editable': False, u'value': u'entity'},
           u'description': {u'editable': True, u'value': u''},
           u'editable': {u'editable': False, u'value': True},
           u'entity_type': {u'editable': False, u'value': u'Version'},
           u'mandatory': {u'editable': False, u'value': False},
           u'name': {u'editable': True, u'value': u'Artist'},
           u'properties': {u'default_value': {u'editable': False,
                                              u'value': None},
                           u'summary_default': {u'editable': True,
                                                u'value': u'none'},
                           u'valid_types': {u'editable': True,
                                            u'value': [u'HumanUser',
                                                       u'ApiUser']}}}}





schema_field_read_version_user = {u'user': {u'data_type': {u'editable': False, u'value': u'entity'},
           u'description': {u'editable': True, u'value': u''},
           u'editable': {u'editable': False, u'value': True},
           u'entity_type': {u'editable': False, u'value': u'Version'},
           u'mandatory': {u'editable': False, u'value': False},
           u'name': {u'editable': True, u'value': u'Artist'},
           u'properties': {u'default_value': {u'editable': False,
                                              u'value': None},
                           u'summary_default': {u'editable': True,
                                                u'value': u'none'},
                           u'valid_types': {u'editable': True,
                                            u'value': [u'HumanUser',
                                                       u'ApiUser']}}}}
                                                       
########NEW FILE########
__FILENAME__ = httplib2test
#!/usr/bin/env python2.4
"""
httplib2test

A set of unit tests for httplib2.py.

Requires Python 2.4 or later
"""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__license__ = "MIT"
__history__ = """ """
__version__ = "0.1 ($Rev: 118 $)"


import sys
import unittest
import httplib
import httplib2
import os
import urlparse
import time
import base64
import StringIO

# Python 2.3 support
if not hasattr(unittest.TestCase, 'assertTrue'):
    unittest.TestCase.assertTrue = unittest.TestCase.failUnless
    unittest.TestCase.assertFalse = unittest.TestCase.failIf

# The test resources base uri
base = 'http://bitworking.org/projects/httplib2/test/'
#base = 'http://localhost/projects/httplib2/test/'
cacheDirName = ".cache"


class CredentialsTest(unittest.TestCase):
    def test(self):
        c = httplib2.Credentials()
        c.add("joe", "password")
        self.assertEqual(("joe", "password"), list(c.iter("bitworking.org"))[0])
        self.assertEqual(("joe", "password"), list(c.iter(""))[0])
        c.add("fred", "password2", "wellformedweb.org")
        self.assertEqual(("joe", "password"), list(c.iter("bitworking.org"))[0])
        self.assertEqual(1, len(list(c.iter("bitworking.org"))))
        self.assertEqual(2, len(list(c.iter("wellformedweb.org"))))
        self.assertTrue(("fred", "password2") in list(c.iter("wellformedweb.org")))
        c.clear()
        self.assertEqual(0, len(list(c.iter("bitworking.org"))))
        c.add("fred", "password2", "wellformedweb.org")
        self.assertTrue(("fred", "password2") in list(c.iter("wellformedweb.org")))
        self.assertEqual(0, len(list(c.iter("bitworking.org"))))
        self.assertEqual(0, len(list(c.iter(""))))


class ParserTest(unittest.TestCase):
    def testFromStd66(self):
        self.assertEqual( ('http', 'example.com', '', None, None ), httplib2.parse_uri("http://example.com"))
        self.assertEqual( ('https', 'example.com', '', None, None ), httplib2.parse_uri("https://example.com"))
        self.assertEqual( ('https', 'example.com:8080', '', None, None ), httplib2.parse_uri("https://example.com:8080"))
        self.assertEqual( ('http', 'example.com', '/', None, None ), httplib2.parse_uri("http://example.com/"))
        self.assertEqual( ('http', 'example.com', '/path', None, None ), httplib2.parse_uri("http://example.com/path"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', None ), httplib2.parse_uri("http://example.com/path?a=1&b=2"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', 'fred' ), httplib2.parse_uri("http://example.com/path?a=1&b=2#fred"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', 'fred' ), httplib2.parse_uri("http://example.com/path?a=1&b=2#fred"))


class UrlNormTest(unittest.TestCase):
    def test(self):
        self.assertEqual( "http://example.org/", httplib2.urlnorm("http://example.org")[-1])
        self.assertEqual( "http://example.org/", httplib2.urlnorm("http://EXAMple.org")[-1])
        self.assertEqual( "http://example.org/?=b", httplib2.urlnorm("http://EXAMple.org?=b")[-1])
        self.assertEqual( "http://example.org/mypath?a=b", httplib2.urlnorm("http://EXAMple.org/mypath?a=b")[-1])
        self.assertEqual( "http://localhost:80/", httplib2.urlnorm("http://localhost:80")[-1])
        self.assertEqual( httplib2.urlnorm("http://localhost:80/"), httplib2.urlnorm("HTTP://LOCALHOST:80"))
        try:
            httplib2.urlnorm("/")
            self.fail("Non-absolute URIs should raise an exception")
        except httplib2.RelativeURIError:
            pass

class UrlSafenameTest(unittest.TestCase):
    def test(self):
        # Test that different URIs end up generating different safe names
        self.assertEqual( "example.org,fred,a=b,58489f63a7a83c3b7794a6a398ee8b1f", httplib2.safename("http://example.org/fred/?a=b"))
        self.assertEqual( "example.org,fred,a=b,8c5946d56fec453071f43329ff0be46b", httplib2.safename("http://example.org/fred?/a=b"))
        self.assertEqual( "www.example.org,fred,a=b,499c44b8d844a011b67ea2c015116968", httplib2.safename("http://www.example.org/fred?/a=b"))
        self.assertEqual( httplib2.safename(httplib2.urlnorm("http://www")[-1]), httplib2.safename(httplib2.urlnorm("http://WWW")[-1]))
        self.assertEqual( "www.example.org,fred,a=b,692e843a333484ce0095b070497ab45d", httplib2.safename("https://www.example.org/fred?/a=b"))
        self.assertNotEqual( httplib2.safename("http://www"), httplib2.safename("https://www"))
        # Test the max length limits
        uri = "http://" + ("w" * 200) + ".org"
        uri2 = "http://" + ("w" * 201) + ".org"
        self.assertNotEqual( httplib2.safename(uri2), httplib2.safename(uri))
        # Max length should be 200 + 1 (",") + 32
        self.assertEqual(233, len(httplib2.safename(uri2)))
        self.assertEqual(233, len(httplib2.safename(uri)))
        # Unicode
        if sys.version_info >= (2,3):
            self.assertEqual( "xn--http,-4y1d.org,fred,a=b,579924c35db315e5a32e3d9963388193", httplib2.safename(u"http://\u2304.org/fred/?a=b"))

class _MyResponse(StringIO.StringIO):
    def __init__(self, body, **kwargs):
        StringIO.StringIO.__init__(self, body)
        self.headers = kwargs

    def iteritems(self):
        return self.headers.iteritems()


class _MyHTTPConnection(object):
    "This class is just a mock of httplib.HTTPConnection used for testing"

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=None, proxy_info=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.log = ""

    def set_debuglevel(self, level):
        pass

    def connect(self):
        "Connect to a host on a given port."
        pass

    def close(self):
        pass

    def request(self, method, request_uri, body, headers):
        pass

    def getresponse(self):
        return _MyResponse("the body", status="200")


class HttpTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(cacheDirName): 
            [os.remove(os.path.join(cacheDirName, file)) for file in os.listdir(cacheDirName)]
        self.http = httplib2.Http(cacheDirName)
        self.http.clear_credentials()

    def testConnectionType(self):
        self.http.force_exception_to_status_code = False 
        response, content = self.http.request("http://bitworking.org", connection_type=_MyHTTPConnection)
        self.assertEqual(response['content-location'], "http://bitworking.org")
        self.assertEqual(content, "the body")

    def testGetUnknownServer(self):
        self.http.force_exception_to_status_code = False 
        try:
            self.http.request("http://fred.bitworking.org/")
            self.fail("An httplib2.ServerNotFoundError Exception must be thrown on an unresolvable server.")
        except httplib2.ServerNotFoundError:
            pass

        # Now test with exceptions turned off
        self.http.force_exception_to_status_code = True

        (response, content) = self.http.request("http://fred.bitworking.org/")
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertTrue(content.startswith("Unable to find"))
        self.assertEqual(response.status, 400)

    def testGetIRI(self):
        if sys.version_info >= (2,3):
            uri = urlparse.urljoin(base, u"reflector/reflector.cgi?d=\N{CYRILLIC CAPITAL LETTER DJE}")
            (response, content) = self.http.request(uri, "GET")
            d = self.reflector(content)
            self.assertTrue(d.has_key('QUERY_STRING')) 
            self.assertTrue(d['QUERY_STRING'].find('%D0%82') > 0) 
    
    def testGetIsDefaultMethod(self):
        # Test that GET is the default method
        uri = urlparse.urljoin(base, "methods/method_reflector.cgi")
        (response, content) = self.http.request(uri)
        self.assertEqual(response['x-method'], "GET")

    def testDifferentMethods(self):
        # Test that all methods can be used
        uri = urlparse.urljoin(base, "methods/method_reflector.cgi")
        for method in ["GET", "PUT", "DELETE", "POST"]:
            (response, content) = self.http.request(uri, method, body=" ")
            self.assertEqual(response['x-method'], method)

    def testHeadRead(self):
        # Test that we don't try to read the response of a HEAD request
        # since httplib blocks response.read() for HEAD requests.
        # Oddly enough this doesn't appear as a problem when doing HEAD requests
        # against Apache servers.
        uri = "http://www.google.com/"
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "")

    def testGetNoCache(self):
        # Test that can do a GET w/o the cache turned on.
        http = httplib2.Http()
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.previous, None)

    def testGetOnlyIfCachedCacheHit(self):
        # Test that can do a GET with cache and 'only-if-cached'
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, True)
        self.assertEqual(response.status, 200)

    def testGetOnlyIfCachedCacheMiss(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 504)

    def testGetOnlyIfCachedNoCacheAtAll(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        # Of course, there might be an intermediary beyond us
        # that responds to the 'only-if-cached', so this
        # test can't really be guaranteed to pass.
        http = httplib2.Http()
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 504)

    def testUserAgent(self):
        # Test that we provide a default user-agent
        uri = urlparse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith("Python-httplib2/"))

    def testUserAgentNonDefault(self):
        # Test that the default user-agent can be over-ridden

        uri = urlparse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET", headers={'User-Agent': 'fred/1.0'})
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith("fred/1.0"))

    def testGet300WithLocation(self):
        # Test the we automatically follow 300 redirects if a Location: header is provided
        uri = urlparse.urljoin(base, "300/with-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

        # Confirm that the intermediate 300 is not cached
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

    def testGet300WithLocationNoRedirect(self):
        # Test the we automatically follow 300 redirects if a Location: header is provided
        self.http.follow_redirects = False
        uri = urlparse.urljoin(base, "300/with-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 300)

    def testGet300WithoutLocation(self):
        # Not giving a Location: header in a 300 response is acceptable
        # In which case we just return the 300 response
        uri = urlparse.urljoin(base, "300/without-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 300)
        self.assertTrue(response['content-type'].startswith("text/html"))
        self.assertEqual(response.previous, None)

    def testGet301(self):
        # Test that we automatically follow 301 redirects
        # and that we cache the 301 response
        uri = urlparse.urljoin(base, "301/onestep.asis")
        destination = urlparse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertTrue(response.has_key('content-location'))
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, True)


    def testGet301NoRedirect(self):
        # Test that we automatically follow 301 redirects
        # and that we cache the 301 response
        self.http.follow_redirects = False
        uri = urlparse.urljoin(base, "301/onestep.asis")
        destination = urlparse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 301)


    def testGet302(self):
        # Test that we automatically follow 302 redirects
        # and that we DO NOT cache the 302 response
        uri = urlparse.urljoin(base, "302/onestep.asis")
        destination = urlparse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

        uri = urlparse.urljoin(base, "302/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)
        self.assertEqual(response.previous['content-location'], uri)

        uri = urlparse.urljoin(base, "302/twostep.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

    def testGet302RedirectionLimit(self):
        # Test that we can set a lower redirection limit
        # and that we raise an exception when we exceed
        # that limit.
        self.http.force_exception_to_status_code = False 

        uri = urlparse.urljoin(base, "302/twostep.asis")
        try:
            (response, content) = self.http.request(uri, "GET", redirections = 1)
            self.fail("This should not happen")
        except httplib2.RedirectLimit:
            pass
        except Exception, e:
            self.fail("Threw wrong kind of exception ")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True 

        (response, content) = self.http.request(uri, "GET", redirections = 1)
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Redirected more"))
        self.assertEqual("302", response['status'])
        self.assertTrue(content.startswith("<html>"))
        self.assertTrue(response.previous != None)

    def testGet302NoLocation(self):
        # Test that we throw an exception when we get
        # a 302 with no Location: header.
        self.http.force_exception_to_status_code = False 
        uri = urlparse.urljoin(base, "302/no-location.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.RedirectMissingLocation:
            pass
        except Exception, e:
            self.fail("Threw wrong kind of exception ")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True 

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Redirected but"))
        self.assertEqual("302", response['status'])
        self.assertTrue(content.startswith("This is content"))
 
# KB Test failing with freshly checkout code
#    def testGet302ViaHttps(self):
#        # Google always redirects to http://google.com
#        (response, content) = self.http.request("https://google.com", "GET")
#        self.assertEqual(200, response.status)
#        self.assertEqual(302, response.previous.status)

    def testGetViaHttps(self):
        # Test that we can handle HTTPS
        (response, content) = self.http.request("https://google.com/adsense/", "GET")
        self.assertEqual(200, response.status)

    def testGetViaHttpsSpecViolationOnLocation(self):
        # Test that we follow redirects through HTTPS
        # even if they violate the spec by including
        # a relative Location: header instead of an 
        # absolute one.
        (response, content) = self.http.request("https://google.com/adsense", "GET")
        self.assertEqual(200, response.status)
        self.assertNotEqual(None, response.previous)


    def testGetViaHttpsKeyCert(self):
        #  At this point I can only test
        #  that the key and cert files are passed in 
        #  correctly to httplib. It would be nice to have 
        #  a real https endpoint to test against.
        http = httplib2.Http(timeout=2)

        http.add_certificate("akeyfile", "acertfile", "bitworking.org")
        try:
            (response, content) = http.request("https://bitworking.org", "GET")
        except:
            pass
        self.assertEqual(http.connections["https:bitworking.org"].key_file, "akeyfile")
        self.assertEqual(http.connections["https:bitworking.org"].cert_file, "acertfile")

        try:
            (response, content) = http.request("https://notthere.bitworking.org", "GET")
        except:
            pass
        self.assertEqual(http.connections["https:notthere.bitworking.org"].key_file, None)
        self.assertEqual(http.connections["https:notthere.bitworking.org"].cert_file, None)




    def testGet303(self):
        # Do a follow-up GET on a Location: header
        # returned from a POST that gave a 303.
        uri = urlparse.urljoin(base, "303/303.cgi")
        (response, content) = self.http.request(uri, "POST", " ")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 303)

    def testGet303NoRedirect(self):
        # Do a follow-up GET on a Location: header
        # returned from a POST that gave a 303.
        self.http.follow_redirects = False
        uri = urlparse.urljoin(base, "303/303.cgi")
        (response, content) = self.http.request(uri, "POST", " ")
        self.assertEqual(response.status, 303)

    def test303ForDifferentMethods(self):
        # Test that all methods can be used
        uri = urlparse.urljoin(base, "303/redirect-to-reflector.cgi")
        for (method, method_on_303) in [("PUT", "GET"), ("DELETE", "GET"), ("POST", "GET"), ("GET", "GET"), ("HEAD", "GET")]: 
            (response, content) = self.http.request(uri, method, body=" ")
            self.assertEqual(response['x-method'], method_on_303)

    def testGet304(self):
        # Test that we use ETags properly to validate our cache
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'must-revalidate'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        cache_file_name = os.path.join(cacheDirName, httplib2.safename(httplib2.urlnorm(uri)[-1]))
        f = open(cache_file_name, "r")
        status_line = f.readline()
        f.close()

        self.assertTrue(status_line.startswith("status:"))

        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers = {'range': 'bytes=0-0'})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.fromcache, False)

    def testGetIgnoreEtag(self):
        # Test that we can forcibly ignore ETags 
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH')) 

        self.http.ignore_etag = True
        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertEqual(response.fromcache, False)
        self.assertFalse(d.has_key('HTTP_IF_NONE_MATCH')) 

    def testOverrideEtag(self):
        # Test that we can forcibly ignore ETags 
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH')) 
        self.assertNotEqual(d['HTTP_IF_NONE_MATCH'], "fred") 

        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0', 'if-none-match': 'fred'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH')) 
        self.assertEqual(d['HTTP_IF_NONE_MATCH'], "fred") 

#MAP-commented this out because it consistently fails
#    def testGet304EndToEnd(self):
#       # Test that end to end headers get overwritten in the cache
#        uri = urlparse.urljoin(base, "304/end2end.cgi")
#        (response, content) = self.http.request(uri, "GET")
#        self.assertNotEqual(response['etag'], "")
#        old_date = response['date']
#        time.sleep(2)
#
#        (response, content) = self.http.request(uri, "GET", headers = {'Cache-Control': 'max-age=0'})
#        # The response should be from the cache, but the Date: header should be updated.
#        new_date = response['date']
#        self.assertNotEqual(new_date, old_date)
#        self.assertEqual(response.status, 200)
#        self.assertEqual(response.fromcache, True)

    def testGet304LastModified(self):
        # Test that we can still handle a 304 
        # by only using the last-modified cache validator.
        uri = urlparse.urljoin(base, "304/last-modified-only/last-modified-only.txt")
        (response, content) = self.http.request(uri, "GET")

        self.assertNotEqual(response['last-modified'], "")
        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

    def testGet307(self):
        # Test that we do follow 307 redirects but
        # do not cache the 307
        uri = urlparse.urljoin(base, "307/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

    def testGet410(self):
        # Test that we pass 410's through
        uri = urlparse.urljoin(base, "410/410.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 410)

    def testVaryHeaderSimple(self):
        """
        RFC 2616 13.6
        When the cache receives a subsequent request whose Request-URI
        specifies one or more cache entries including a Vary header field,
        the cache MUST NOT use such a cache entry to construct a response
        to the new request unless all of the selecting request-headers
        present in the new request match the corresponding stored
        request-headers in the original request.
        """
        # test that the vary header is sent
        uri = urlparse.urljoin(base, "vary/accept.asis")
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertTrue(response.has_key('vary'))

        # get the resource again, from the cache since accept header in this
        # request is the same as the request
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True, msg="Should be from cache")

        # get the resource again, not from cache since Accept headers does not match
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/html'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False, msg="Should not be from cache")

        # get the resource again, without any Accept header, so again no match
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False, msg="Should not be from cache")

    def testNoVary(self):
        # when there is no vary, a different Accept header (e.g.) should not
        # impact if the cache is used
        # test that the vary header is not sent
        uri = urlparse.urljoin(base, "vary/no-vary.asis")
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertFalse(response.has_key('vary'))

        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True, msg="Should be from cache")
        
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/html'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True, msg="Should be from cache")

    def testVaryHeaderDouble(self):
        uri = urlparse.urljoin(base, "vary/accept-double.asis")
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain', 'Accept-Language': 'da, en-gb;q=0.8, en;q=0.7'})
        self.assertEqual(response.status, 200)
        self.assertTrue(response.has_key('vary'))

        # we are from cache
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain', 'Accept-Language': 'da, en-gb;q=0.8, en;q=0.7'})
        self.assertEqual(response.fromcache, True, msg="Should be from cache")

        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        # get the resource again, not from cache, varied headers don't match exact
        (response, content) = self.http.request(uri, "GET", headers={'Accept-Language': 'da'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False, msg="Should not be from cache")


    def testHeadGZip(self):
        # Test that we don't try to decompress a HEAD response 
        uri = urlparse.urljoin(base, "gzip/final-destination.txt")
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertNotEqual(int(response['content-length']), 0)
        self.assertEqual(content, "")

    def testGetGZip(self):
        # Test that we support gzip compression
        uri = urlparse.urljoin(base, "gzip/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertFalse(response.has_key('content-encoding'))
        self.assertTrue(response.has_key('-content-encoding'))
        self.assertEqual(int(response['content-length']), len("This is the final destination.\n"))
        self.assertEqual(content, "This is the final destination.\n")

    def testGetGZipFailure(self):
        # Test that we raise a good exception when the gzip fails
        self.http.force_exception_to_status_code = False 
        uri = urlparse.urljoin(base, "gzip/failed-compression.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.FailedToDecompressContent:
            pass
        except Exception:
            self.fail("Threw wrong kind of exception")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True 

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Content purported"))

    def testTimeout(self):
        self.http.force_exception_to_status_code = True 
        uri = urlparse.urljoin(base, "timeout/timeout.cgi")
        try:
            import socket
            socket.setdefaulttimeout(1) 
        except:
            # Don't run the test if we can't set the timeout
            return 
        (response, content) = self.http.request(uri)
        self.assertEqual(response.status, 408)
        self.assertTrue(response.reason.startswith("Request Timeout"))
        self.assertTrue(content.startswith("Request Timeout"))

    def testIndividualTimeout(self):
        uri = urlparse.urljoin(base, "timeout/timeout.cgi")
        http = httplib2.Http(timeout=1)
        http.force_exception_to_status_code = True 

        (response, content) = http.request(uri)
        self.assertEqual(response.status, 408)
        self.assertTrue(response.reason.startswith("Request Timeout"))
        self.assertTrue(content.startswith("Request Timeout"))


    def testHTTPSInitTimeout(self):
        c = httplib2.HTTPSConnectionWithTimeout('localhost', 80, timeout=47)
        self.assertEqual(47, c.timeout)

    def testGetDeflate(self):
        # Test that we support deflate compression
        uri = urlparse.urljoin(base, "deflate/deflated.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertFalse(response.has_key('content-encoding'))
        self.assertEqual(int(response['content-length']), len("This is the final destination."))
        self.assertEqual(content, "This is the final destination.")

    def testGetDeflateFailure(self):
        # Test that we raise a good exception when the deflate fails
        self.http.force_exception_to_status_code = False 

        uri = urlparse.urljoin(base, "deflate/failed-compression.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.FailedToDecompressContent:
            pass
        except Exception:
            self.fail("Threw wrong kind of exception")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True 

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Content purported"))

    def testGetDuplicateHeaders(self):
        # Test that duplicate headers get concatenated via ','
        uri = urlparse.urljoin(base, "duplicate-headers/multilink.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is content\n")
        self.assertEqual(response['link'].split(",")[0], '<http://bitworking.org>; rel="home"; title="BitWorking"')

    def testGetCacheControlNoCache(self):
        # Test Cache-Control: no-cache on requests
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlPragmaNoCache(self):
        # Test Pragma: no-cache on requests
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'Pragma': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreRequest(self):
        # A no-store request means that the response should not be stored.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreResponse(self):
        # A no-store response means that the response should not be stored.
        uri = urlparse.urljoin(base, "no-store/no-store.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoCacheNoStoreRequest(self):
        # Test that a no-store, no-cache clears the entry from the cache
        # even if it was cached previously.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store, no-cache'})
        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store, no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testUpdateInvalidatesCache(self):
        # Test that calling PUT or DELETE on a 
        # URI that is cache invalidates that cache.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "DELETE")
        self.assertEqual(response.status, 405)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, False)

    def testUpdateUsesCachedETag(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/ 
        uri = urlparse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "PUT", body="foo")
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "PUT", body="foo")
        self.assertEqual(response.status, 412)

    def testUpdateUsesCachedETagAndOCMethod(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/ 
        uri = urlparse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.http.optimistic_concurrency_methods.append("DELETE")
        (response, content) = self.http.request(uri, "DELETE")
        self.assertEqual(response.status, 200)


    def testUpdateUsesCachedETagOverridden(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/ 
        uri = urlparse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "PUT", body="foo", headers={'if-match': 'fred'})
        self.assertEqual(response.status, 412)

    def testBasicAuth(self):
        # Test Basic Authentication
        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthWithDomain(self):
        # Test Basic Authentication
        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password', "example.org")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        domain = urlparse.urlparse(base)[1] 
        self.http.add_credentials('joe', 'password', domain)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)






    def testBasicAuthTwoDifferentCredentials(self):
        # Test Basic Authentication with multiple sets of credentials
        uri = urlparse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic2/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthNested(self):
        # Test Basic Authentication with resources
        # that are nested
        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        # Now add in credentials one at a time and test.
        self.http.add_credentials('joe', 'password')

        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')

        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testDigestAuth(self):
        # Test that we support Digest Authentication
        uri = urlparse.urljoin(base, "digest/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "digest/file.txt")
        (response, content) = self.http.request(uri, "GET")

    def testDigestAuthNextNonceAndNC(self):
        # Test that if the server sets nextnonce that we reset
        # the nonce count back to 1
        uri = urlparse.urljoin(base, "digest/file.txt")
        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info2 = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

        if info.has_key('nextnonce'):
            self.assertEqual(info2['nc'], 1)

    def testDigestAuthStale(self):
        # Test that we can handle a nonce becoming stale
        uri = urlparse.urljoin(base, "digest-expire/file.txt")
        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

        time.sleep(3)
        # Sleep long enough that the nonce becomes stale

        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        self.assertFalse(response.fromcache)
        self.assertTrue(response._stale_digest)
        info3 = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

    def reflector(self, content):
        return  dict( [tuple(x.split("=", 1)) for x in content.strip().split("\n")] )

    def testReflector(self):
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_USER_AGENT')) 

    def testConnectionClose(self):
        uri = "http://www.google.com/"
        (response, content) = self.http.request(uri, "GET")
        for c in self.http.connections.values():
            self.assertNotEqual(None, c.sock)
        (response, content) = self.http.request(uri, "GET", headers={"connection": "close"})
        for c in self.http.connections.values():
            self.assertEqual(None, c.sock)


try:
    import memcache
    class HttpTestMemCached(HttpTest):
        def setUp(self):
            self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)
            #self.cache = memcache.Client(['10.0.0.4:11211'], debug=1)
            self.http = httplib2.Http(self.cache)
            self.cache.flush_all()
            # Not exactly sure why the sleep is needed here, but
            # if not present then some unit tests that rely on caching
            # fail. Memcached seems to lose some sets immediately
            # after a flush_all if the set is to a value that
            # was previously cached. (Maybe the flush is handled async?)
            time.sleep(1)
            self.http.clear_credentials()
except:
    pass




# ------------------------------------------------------------------------

class HttpPrivateTest(unittest.TestCase):

    def testParseCacheControl(self):
        # Test that we can parse the Cache-Control header
        self.assertEqual({}, httplib2._parse_cache_control({}))
        self.assertEqual({'no-cache': 1}, httplib2._parse_cache_control({'cache-control': ' no-cache'}))
        cc = httplib2._parse_cache_control({'cache-control': ' no-cache, max-age = 7200'})
        self.assertEqual(cc['no-cache'], 1)
        self.assertEqual(cc['max-age'], '7200')
        cc = httplib2._parse_cache_control({'cache-control': ' , '})
        self.assertEqual(cc[''], 1)

        try:
            cc = httplib2._parse_cache_control({'cache-control': 'Max-age=3600;post-check=1800,pre-check=3600'})
            self.assertTrue("max-age" in cc)
        except:
            self.fail("Should not throw exception")

    def testNormalizeHeaders(self):
        # Test that we normalize headers to lowercase 
        h = httplib2._normalize_headers({'Cache-Control': 'no-cache', 'Other': 'Stuff'})
        self.assertTrue(h.has_key('cache-control'))
        self.assertTrue(h.has_key('other'))
        self.assertEqual('Stuff', h['other'])

    def testExpirationModelTransparent(self):
        # Test that no-cache makes our request TRANSPARENT
        response_headers = {
            'cache-control': 'max-age=7200'
        }
        request_headers = {
            'cache-control': 'no-cache'
        }
        self.assertEqual("TRANSPARENT", httplib2._entry_disposition(response_headers, request_headers))

    def testMaxAgeNonNumeric(self):
        # Test that no-cache makes our request TRANSPARENT
        response_headers = {
            'cache-control': 'max-age=fred, min-fresh=barney'
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))


    def testExpirationModelNoCacheResponse(self):
        # The date and expires point to an entry that should be
        # FRESH, but the no-cache over-rides that.
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+4)),
            'cache-control': 'no-cache'
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelStaleRequestMustReval(self):
        # must-revalidate forces STALE
        self.assertEqual("STALE", httplib2._entry_disposition({}, {'cache-control': 'must-revalidate'}))

    def testExpirationModelStaleResponseMustReval(self):
        # must-revalidate forces STALE
        self.assertEqual("STALE", httplib2._entry_disposition({'cache-control': 'must-revalidate'}, {}))

    def testExpirationModelFresh(self):
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            'cache-control': 'max-age=2'
        }
        request_headers = {
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))
        time.sleep(3)
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationMaxAge0(self):
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            'cache-control': 'max-age=0'
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpires(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+2)),
        }
        request_headers = {
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))
        time.sleep(3)
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpiresZero(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': "0",
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateOnly(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+3)),
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelOnlyIfCached(self):
        response_headers = {
        }
        request_headers = {
            'cache-control': 'only-if-cached',
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelMaxAgeBoth(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'cache-control': 'max-age=2'
        }
        request_headers = {
            'cache-control': 'max-age=0'
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpiresMinFresh1(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+2)),
        }
        request_headers = {
            'cache-control': 'min-fresh=2'
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpiresMinFresh2(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+4)),
        }
        request_headers = {
            'cache-control': 'min-fresh=2'
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))

    def testParseWWWAuthenticateEmpty(self):
        res = httplib2._parse_www_authenticate({})
        self.assertEqual(len(res.keys()), 0) 

    def testParseWWWAuthenticate(self):
        # different uses of spaces around commas
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="test realm" , foo=foo ,bar="bar", baz=baz,qux=qux'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(len(res['test'].keys()), 5)
        
        # tokens with non-alphanum
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'T*!%#st realm=to*!%#en, to*!%#en="quoted string"'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(len(res['t*!%#st'].keys()), 2)
        
        # quoted string with quoted pairs
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="a \\"test\\" realm"'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(res['test']['realm'], 'a "test" realm')

    def testParseWWWAuthenticateStrict(self):
        httplib2.USE_WWW_AUTH_STRICT_PARSING = 1;
        self.testParseWWWAuthenticate();
        httplib2.USE_WWW_AUTH_STRICT_PARSING = 0;

    def testParseWWWAuthenticateBasic(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me"'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me", algorithm="MD5"'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('MD5', basic['algorithm'])

        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me", algorithm=MD5'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('MD5', basic['algorithm'])

    def testParseWWWAuthenticateBasic2(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me",other="fred" '})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('fred', basic['other'])

    def testParseWWWAuthenticateBasic3(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic REAlm="me" '})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])


    def testParseWWWAuthenticateDigest(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41"'})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])


    def testParseWWWAuthenticateMultiple(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41" Basic REAlm="me" '})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

    def testParseWWWAuthenticateMultiple2(self):
        # Handle an added comma between challenges, which might get thrown in if the challenges were
        # originally sent in separate www-authenticate headers.
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me" '})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

    def testParseWWWAuthenticateMultiple3(self):
        # Handle an added comma between challenges, which might get thrown in if the challenges were
        # originally sent in separate www-authenticate headers.
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me", WSSE realm="foo", profile="UsernameToken"'})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        wsse = res['wsse']
        self.assertEqual('foo', wsse['realm'])
        self.assertEqual('UsernameToken', wsse['profile'])

    def testParseWWWAuthenticateMultiple4(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="test-real.m@host.com", qop \t=\t"\tauth,auth-int", nonce="(*)&^&$%#",opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me", WSSE realm="foo", profile="UsernameToken"'}) 
        digest = res['digest']
        self.assertEqual('test-real.m@host.com', digest['realm'])
        self.assertEqual('\tauth,auth-int', digest['qop'])
        self.assertEqual('(*)&^&$%#', digest['nonce'])

    def testParseWWWAuthenticateMoreQuoteCombos(self):
        res = httplib2._parse_www_authenticate({'www-authenticate':'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'})
        digest = res['digest']
        self.assertEqual('myrealm', digest['realm'])

    def testDigestObject(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = {
            'www-authenticate': 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth"'
        }
        content = ""
        
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        d.request("GET", request_uri, headers, content, cnonce="33033375ec278a46") 
        our_request = "Authorization: %s" % headers['Authorization']
        working_request = 'Authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46"'
        self.assertEqual(our_request, working_request)


    def testDigestObjectStale(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = httplib2.Response({ })
        response['www-authenticate'] = 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'
        response.status = 401
        content = ""
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        # Returns true to force a retry
        self.assertTrue( d.response(response, content) )

    def testDigestObjectAuthInfo(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = httplib2.Response({ })
        response['www-authenticate'] = 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'
        response['authentication-info'] = 'nextnonce="fred"'
        content = ""
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        # Returns true to force a retry
        self.assertFalse( d.response(response, content) )
        self.assertEqual('fred', d.challenge['nonce'])
        self.assertEqual(1, d.challenge['nc'])

    def testWsseAlgorithm(self):
        digest = httplib2._wsse_username_token("d36e316282959a9ed4c89851497a717f", "2003-12-15T14:43:07Z", "taadtaadpstcsm")
        expected = "quR/EWLAV4xLf9Zqyw4pDmfV9OY="
        self.assertEqual(expected, digest)

    def testEnd2End(self):
        # one end to end header
        response = {'content-type': 'application/atom+xml', 'te': 'deflate'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertTrue('content-type' in end2end)
        self.assertTrue('te' not in end2end)
        self.assertTrue('connection' not in end2end)

        # one end to end header that gets eliminated
        response = {'connection': 'content-type', 'content-type': 'application/atom+xml', 'te': 'deflate'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertTrue('content-type' not in end2end)
        self.assertTrue('te' not in end2end)
        self.assertTrue('connection' not in end2end)

        # Degenerate case of no headers
        response = {}
        end2end = httplib2._get_end2end_headers(response)
        self.assertEquals(0, len(end2end))

        # Degenerate case of connection referrring to a header not passed in 
        response = {'connection': 'content-type'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertEquals(0, len(end2end))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2011 Michael Foord & the mock team
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.7.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'MagicMock',
    'mocksignature',
    'patch',
    'patch_object',
    'sentinel',
    'DEFAULT'
)

__version__ = '0.7.0'

__unittest = True


import sys
import warnings

try:
    import inspect
except ImportError:
    # for alternative platforms that
    # may not have inspect
    inspect = None

try:
    BaseException
except NameError:
    # Python 2.4 compatibility
    BaseException = Exception

try:
    from functools import wraps
except ImportError:
    # Python 2.4 compatibility
    def wraps(original):
        def inner(f):
            f.__name__ = original.__name__
            f.__doc__ = original.__doc__
            f.__module__ = original.__module__
            return f
        return inner

try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

try:
    long
except NameError:
    # Python 3
    long = int

inPy3k = sys.version_info[0] == 3

if inPy3k:
    self = '__self__'
else:
    self = 'im_self'


# getsignature and mocksignature heavily "inspired" by
# the decorator module: http://pypi.python.org/pypi/decorator/
# by Michele Simionato

def _getsignature(func, skipfirst):
    if inspect is None:
        raise ImportError('inspect module not available')

    if inspect.isclass(func):
        func = func.__init__
        # will have a self arg
        skipfirst = True
    elif not (inspect.ismethod(func) or inspect.isfunction(func)):
        func = func.__call__

    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)

    # instance methods need to lose the self argument
    if getattr(func, self, None) is not None:
        regargs = regargs[1:]

    _msg = "_mock_ is a reserved argument name, can't mock signatures using _mock_"
    assert '_mock_' not in regargs, _msg
    if varargs is not None:
        assert '_mock_' not in varargs, _msg
    if varkwargs is not None:
        assert '_mock_' not in varkwargs, _msg
    if skipfirst:
        regargs = regargs[1:]
    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")
    return signature[1:-1], func


def _copy_func_details(func, funcopy):
    funcopy.__name__ = func.__name__
    funcopy.__doc__ = func.__doc__
    funcopy.__dict__.update(func.__dict__)
    funcopy.__module__ = func.__module__
    if not inPy3k:
        funcopy.func_defaults = func.func_defaults
    else:
        funcopy.__defaults__ = func.__defaults__
        funcopy.__kwdefaults__ = func.__kwdefaults__


def mocksignature(func, mock=None, skipfirst=False):
    """
    mocksignature(func, mock=None, skipfirst=False)

    Create a new function with the same signature as `func` that delegates
    to `mock`. If `skipfirst` is True the first argument is skipped, useful
    for methods where `self` needs to be omitted from the new function.

    If you don't pass in a `mock` then one will be created for you.

    The mock is set as the `mock` attribute of the returned function for easy
    access.

    `mocksignature` can also be used with classes. It copies the signature of
    the `__init__` method.

    When used with callable objects (instances) it copies the signature of the
    `__call__` method.
    """
    if mock is None:
        mock = Mock()
    signature, func = _getsignature(func, skipfirst)
    src = "lambda %(signature)s: _mock_(%(signature)s)" % {
        'signature': signature
    }

    funcopy = eval(src, dict(_mock_=mock))
    _copy_func_details(func, funcopy)
    funcopy.mock = mock
    return funcopy


def _is_magic(name):
    return '__%s__' % name[2:-2] == name


class SentinelObject(object):
    "A unique, named, sentinel object."
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SentinelObject "%s">' % self.name


class Sentinel(object):
    """Access attributes to return a named object, usable as a sentinel."""
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == '__bases__':
            # Without this help(mock) raises an exception
            raise AttributeError
        return self._sentinels.setdefault(name, SentinelObject(name))


sentinel = Sentinel()

DEFAULT = sentinel.DEFAULT


class OldStyleClass:
    pass
ClassType = type(OldStyleClass)


def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


if inPy3k:
    class_types = type
else:
    class_types = (type, ClassType)


class Mock(object):
    """
    Create a new ``Mock`` object. ``Mock`` takes several optional arguments
    that specify the behaviour of the Mock object:

    * ``spec``: This can be either a list of strings or an existing object (a
      class or instance) that acts as the specification for the mock object. If
      you pass in an object then a list of strings is formed by calling dir on
      the object (excluding unsupported magic attributes and methods). Accessing
      any attribute not in this list will raise an ``AttributeError``.

      If ``spec`` is an object (rather than a list of strings) then
      `mock.__class__` returns the class of the spec object. This allows mocks
      to pass `isinstance` tests.

    * ``spec_set``: A stricter variant of ``spec``. If used, attempting to *set*
      or get an attribute on the mock that isn't on the object passed as
      ``spec_set`` will raise an ``AttributeError``.

    * ``side_effect``: A function to be called whenever the Mock is called. See
      the :attr:`Mock.side_effect` attribute. Useful for raising exceptions or
      dynamically changing return values. The function is called with the same
      arguments as the mock, and unless it returns :data:`DEFAULT`, the return
      value of this function is used as the return value.

      Alternatively ``side_effect`` can be an exception class or instance. In
      this case the exception will be raised when the mock is called.

    * ``return_value``: The value returned when the mock is called. By default
      this is a new Mock (created on first access). See the
      :attr:`Mock.return_value` attribute.

    * ``wraps``: Item for the mock object to wrap. If ``wraps`` is not None
      then calling the Mock will pass the call through to the wrapped object
      (returning the real result and ignoring ``return_value``). Attribute
      access on the mock will return a Mock object that wraps the corresponding
      attribute of the wrapped object (so attempting to access an attribute that
      doesn't exist will raise an ``AttributeError``).

      If the mock has an explicit ``return_value`` set then calls are not passed
      to the wrapped object and the ``return_value`` is returned instead.

    * ``name``: If the mock has a name then it will be used in the repr of the
      mock. This can be useful for debugging. The name is propagated to child
      mocks.
    """
    def __new__(cls, *args, **kw):
        # every instance has its own class
        # so we can create magic methods on the
        # class without stomping on other mocks
        new = type(cls.__name__, (cls,), {'__doc__': cls.__doc__})
        return object.__new__(new)


    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                    wraps=None, name=None, spec_set=None, parent=None):
        self._parent = parent
        self._name = name
        _spec_class = None
        if spec_set is not None:
            spec = spec_set
            spec_set = True

        if spec is not None and not isinstance(spec, list):
            if isinstance(spec, class_types):
                _spec_class = spec
            else:
                _spec_class = spec.__class__
            spec = dir(spec)

        self._spec_class = _spec_class
        self._spec_set = spec_set
        self._methods = spec
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        self._wraps = wraps

        self.reset_mock()


    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class


    def reset_mock(self):
        "Restore the mock object to its initial state."
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.values():
            child.reset_mock()
        if isinstance(self._return_value, Mock):
            if not self._return_value is self:
                self._return_value.reset_mock()


    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = self._get_child_mock()
        return self._return_value

    def __set_return_value(self, value):
        self._return_value = value

    __return_value_doc = "The value to be returned when the mock is called."
    return_value = property(__get_return_value, __set_return_value,
                            __return_value_doc)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = callargs((args, kwargs))
        self.call_args_list.append(callargs((args, kwargs)))

        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append(callargs((name, args, kwargs)))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        ret_val = DEFAULT
        if self.side_effect is not None:
            if (isinstance(self.side_effect, BaseException) or
                isinstance(self.side_effect, class_types) and
                issubclass(self.side_effect, BaseException)):
                raise self.side_effect

            ret_val = self.side_effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if self._wraps is not None and self._return_value is DEFAULT:
            return self._wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val


    def __getattr__(self, name):
        if name == '_methods':
            raise AttributeError(name)
        elif self._methods is not None:
            if name not in self._methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute '%s'" % name)
        elif _is_magic(name):
            raise AttributeError(name)

        if name not in self._children:
            wraps = None
            if self._wraps is not None:
                wraps = getattr(self._wraps, name)
            self._children[name] = self._get_child_mock(parent=self, name=name, wraps=wraps)

        return self._children[name]


    def __repr__(self):
        if self._name is None and self._spec_class is None:
            return object.__repr__(self)

        name_string = ''
        spec_string = ''
        if self._name is not None:
            def get_name(name):
                if name is None:
                    return 'mock'
                return name
            parent = self._parent
            name = self._name
            while parent is not None:
                name = get_name(parent._name) + '.' + name
                parent = parent._parent
            name_string = ' name=%r' % name
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__
        return "<%s%s%s id='%s'>" % (type(self).__name__,
                                      name_string,
                                      spec_string,
                                      id(self))


    def __setattr__(self, name, value):
        if not 'method_calls' in self.__dict__:
            # allow all attribute setting until initialisation is complete
            return object.__setattr__(self, name, value)
        if (self._spec_set and self._methods is not None and name not in
            self._methods and name not in self.__dict__ and
            name != 'return_value'):
            raise AttributeError("Mock object has no attribute '%s'" % name)
        if name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)
        elif name in _all_magics:
            if self._methods is not None and name not in self._methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)

            if not isinstance(value, Mock):
                setattr(type(self), name, _get_method(name, value))
                original = value
                real = lambda *args, **kw: original(self, *args, **kw)
                value = mocksignature(value, real, skipfirst=True)
            else:
                setattr(type(self), name, value)
        return object.__setattr__(self, name, value)


    def __delattr__(self, name):
        if name in _all_magics and name in type(self).__dict__:
            delattr(type(self), name)
        return object.__delattr__(self, name)


    def assert_called_with(self, *args, **kwargs):
        """
        assert that the mock was called with the specified arguments.

        Raises an AssertionError if the args and keyword args passed in are
        different to the last call to the mock.
        """
        if self.call_args is None:
            raise AssertionError('Expected: %s\nNot called' % ((args, kwargs),))
        if not self.call_args == (args, kwargs):
            raise AssertionError(
                'Expected: %s\nCalled with: %s' % ((args, kwargs), self.call_args)
            )


    def assert_called_once_with(self, *args, **kwargs):
        """
        assert that the mock was called exactly once and with the specified
        arguments.
        """
        if not self.call_count == 1:
            msg = ("Expected to be called once. Called %s times." %
                   self.call_count)
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)


    def _get_child_mock(self, **kw):
        klass = type(self).__mro__[1]
        return klass(**kw)



class callargs(tuple):
    """
    A tuple for holding the results of a call to a mock, either in the form
    `(args, kwargs)` or `(name, args, kwargs)`.

    If args or kwargs are empty then a callargs tuple will compare equal to
    a tuple without those values. This makes comparisons less verbose::

        callargs('name', (), {}) == ('name',)
        callargs('name', (1,), {}) == ('name', (1,))
        callargs((), {'a': 'b'}) == ({'a': 'b'},)
    """
    def __eq__(self, other):
        if len(self) == 3:
            if other[0] != self[0]:
                return False
            args_kwargs = self[1:]
            other_args_kwargs = other[1:]
        else:
            args_kwargs = tuple(self)
            other_args_kwargs = other

        if len(other_args_kwargs) == 0:
            other_args, other_kwargs = (), {}
        elif len(other_args_kwargs) == 1:
            if isinstance(other_args_kwargs[0], tuple):
                other_args = other_args_kwargs[0]
                other_kwargs = {}
            else:
                other_args = ()
                other_kwargs = other_args_kwargs[0]
        else:
            other_args, other_kwargs = other_args_kwargs

        return tuple(args_kwargs) == (other_args, other_kwargs)


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class _patch(object):
    def __init__(self, target, attribute, new, spec, create,
                    mocksignature, spec_set):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.has_local = False
        self.mocksignature = mocksignature
        self.spec_set = spec_set


    def copy(self):
        return _patch(self.target, self.attribute, self.new, self.spec,
                        self.create, self.mocksignature, self.spec_set)


    def __call__(self, func):
        if isinstance(func, class_types):
            return self.decorate_class(func)
        else:
            return self.decorate_callable(func)


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if attr.startswith("test") and hasattr(attr_value, "__call__"):
                setattr(klass, attr, self.copy()(attr_value))
        return klass


    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with 2.5)
            extra_args = []
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.append(arg)
            args += tuple(extra_args)
            try:
                return func(*args, **keywargs)
            finally:
                for patching in reversed(getattr(patched, 'patchings', [])):
                    patching.__exit__()

        patched.patchings = [self]
        if hasattr(func, 'func_code'):
            # not in Python 3
            patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno",
                                                    func.func_code.co_firstlineno)
        return patched


    def get_original(self):
        target = self.target
        name = self.attribute

        original = DEFAULT
        local = False

        try:
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        else:
            local = True

        if not self.create and original is DEFAULT:
            raise AttributeError("%s does not have the attribute %r" % (target, name))
        return original, local


    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        original, local = self.get_original()
        if new is DEFAULT:
            # XXXX what if original is DEFAULT - shouldn't use it as a spec
            inherit = False
            if spec_set == True:
                spec_set = original
                if isinstance(spec_set, class_types):
                    inherit = True
            elif spec == True:
                # set spec to the object we are replacing
                spec = original
                if isinstance(spec, class_types):
                    inherit = True
            new = Mock(spec=spec, spec_set=spec_set)
            if inherit:
                new.return_value = Mock(spec=spec, spec_set=spec_set)
        new_attr = new
        if self.mocksignature:
            new_attr = mocksignature(original, new)

        self.temp_original = original
        self.is_local = local
        setattr(self.target, self.attribute, new_attr)
        return new


    def __exit__(self, *_):
        """Undo the patch."""
        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if not self.create and not hasattr(self.target, self.attribute):
                # needed for proxy objects like django settings
                setattr(self.target, self.attribute, self.temp_original)

        del self.temp_original
        del self.is_local

    start = __enter__
    stop = __exit__


def _patch_object(target, attribute, new=DEFAULT, spec=None, create=False,
                  mocksignature=False, spec_set=None):
    """
    patch.object(target, attribute, new=DEFAULT, spec=None, create=False,
                 mocksignature=False, spec_set=None)

    patch the named member (`attribute`) on an object (`target`) with a mock
    object.

    Arguments new, spec, create, mocksignature and spec_set have the same
    meaning as for patch.
    """
    return _patch(target, attribute, new, spec, create, mocksignature,
                  spec_set)


def patch_object(*args, **kwargs):
    "A deprecated form of patch.object(...)"
    warnings.warn(('Please use patch.object instead.'), DeprecationWarning, 2)
    return _patch_object(*args, **kwargs)


def patch(target, new=DEFAULT, spec=None, create=False,
            mocksignature=False, spec_set=None):
    """
    ``patch`` acts as a function decorator, class decorator or a context
    manager. Inside the body of the function or with statement, the ``target``
    (specified in the form `'PackageName.ModuleName.ClassName'`) is patched
    with a ``new`` object. When the function/with statement exits the patch is
    undone.

    The target is imported and the specified attribute patched with the new
    object, so it must be importable from the environment you are calling the
    decorator from.

    If ``new`` is omitted, then a new ``Mock`` is created and passed in as an
    extra argument to the decorated function.

    The ``spec`` and ``spec_set`` keyword arguments are passed to the ``Mock``
    if patch is creating one for you.

    In addition you can pass ``spec=True`` or ``spec_set=True``, which causes
    patch to pass in the object being mocked as the spec/spec_set object.

    If ``mocksignature`` is True then the patch will be done with a function
    created by mocking the one being replaced. If the object being replaced is
    a class then the signature of `__init__` will be copied. If the object
    being replaced is a callable object then the signature of `__call__` will
    be copied.

    By default ``patch`` will fail to replace attributes that don't exist. If
    you pass in 'create=True' and the attribute doesn't exist, patch will
    create the attribute for you when the patched function is called, and
    delete it again afterwards. This is useful for writing tests against
    attributes that your production code creates at runtime. It is off by by
    default because it can be dangerous. With it switched on you can write
    passing tests against APIs that don't actually exist!

    Patch can be used as a TestCase class decorator. It works by
    decorating each test method in the class. This reduces the boilerplate
    code when your test methods share a common patchings set.

    Patch can be used with the with statement, if this is available in your
    version of Python. Here the patching applies to the indented block after
    the with statement. If you use "as" then the patched object will be bound
    to the name after the "as"; very useful if `patch` is creating a mock
    object for you.

    `patch.dict(...)` and `patch.object(...)` are available for alternate
    use-cases.
    """
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" %
                        (target,))
    target = _importer(target)
    return _patch(target, attribute, new, spec, create, mocksignature, spec_set)


class _patch_dict(object):
    """
    Patch a dictionary and restore the dictionary to its original state after
    the test.

    `in_dict` can be a dictionary or a mapping like container. If it is a
    mapping then it must at least support getting, setting and deleting items
    plus iterating over keys.

    `in_dict` can also be a string specifying the name of the dictionary, which
    will then be fetched by importing it.

    `values` can be a dictionary of values to set in the dictionary. `values`
    can also be an iterable of ``(key, value)`` pairs.

    If `clear` is True then the dictionary will be cleared before the new
    values are set.
    """

    def __init__(self, in_dict, values=(), clear=False):
        if isinstance(in_dict, basestring):
            in_dict = _importer(in_dict)
        self.in_dict = in_dict
        # support any argument supported by dict(...) constructor
        self.values = dict(values)
        self.clear = clear
        self._original = None


    def __call__(self, f):
        if isinstance(f, class_types):
            return self.decorate_class(f)
        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if attr.startswith("test") and hasattr(attr_value, "__call__"):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass


    def __enter__(self):
        """Patch the dict."""
        self._patch_dict()


    def _patch_dict(self):
        """Unpatch the dict."""
        values = self.values
        in_dict = self.in_dict
        clear = self.clear

        try:
            original = in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original

        if clear:
            _clear_dict(in_dict)

        try:
            in_dict.update(values)
        except AttributeError:
            # dict like object with no update method
            for key in values:
                in_dict[key] = values[key]


    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original

        _clear_dict(in_dict)

        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]


    def __exit__(self, *args):
        self._unpatch_dict()
        return False

    start = __enter__
    stop = __exit__


def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]


patch.object = _patch_object
patch.dict = _patch_dict


magic_methods = (
    "lt le gt ge eq ne "
    "getitem setitem delitem "
    "len contains iter "
    "hash str sizeof "
    "enter exit "
    "divmod neg pos abs invert "
    "complex int float index "
    "trunc floor ceil "
)

numerics = "add sub mul div truediv floordiv mod lshift rshift and xor or pow "
inplace = ' '.join('i%s' % n for n in numerics.split())
right = ' '.join('r%s' % n for n in numerics.split())
extra = ''
if inPy3k:
    extra = 'bool next '
else:
    extra = 'unicode long nonzero oct hex '
# __truediv__ and __rtruediv__ not available in Python 3 either

# not including __prepare__, __instancecheck__, __subclasscheck__
# (as they are metaclass methods)
# __del__ is not supported at all as it causes problems if it exists

_non_defaults = set('__%s__' % method for method in [
    'cmp', 'getslice', 'setslice', 'coerce', 'subclasses',
    'dir', 'format', 'get', 'set', 'delete', 'reversed',
    'missing', 'reduce', 'reduce_ex', 'getinitargs',
    'getnewargs', 'getstate', 'setstate', 'getformat',
    'setformat', 'repr'
])


def _get_method(name, func):
    "Turns a callable object (like a mock) into a real function"
    def method(self, *args, **kw):
        return func(self, *args, **kw)
    method.__name__ = name
    return method


_magics = set(
    '__%s__' % method for method in
    ' '.join([magic_methods, numerics, inplace, right, extra]).split()
)

_all_magics = _magics | _non_defaults

_unsupported_magics = set([
    '__getattr__', '__setattr__',
    '__init__', '__new__', '__prepare__'
    '__instancecheck__', '__subclasscheck__',
    '__del__'
])

_calculate_return_value = {
    '__hash__': lambda self: object.__hash__(self),
    '__str__': lambda self: object.__str__(self),
    '__sizeof__': lambda self: object.__sizeof__(self),
    '__unicode__': lambda self: unicode(object.__str__(self)),
}

_return_values = {
    '__int__': 1,
    '__contains__': False,
    '__len__': 0,
    '__iter__': iter([]),
    '__exit__': False,
    '__complex__': 1j,
    '__float__': 1.0,
    '__bool__': True,
    '__nonzero__': True,
    '__oct__': '1',
    '__hex__': '0x1',
    '__long__': long(1),
    '__index__': 1,
}


def _set_return_value(mock, method, name):
    return_value = DEFAULT
    if name in _return_values:
        return_value = _return_values[name]
    elif name in _calculate_return_value:
        try:
            return_value = _calculate_return_value[name](mock)
        except AttributeError:
            return_value = AttributeError(name)
    if return_value is not DEFAULT:
        method.return_value = return_value


class MagicMock(Mock):
    """
    MagicMock is a subclass of :Mock with default implementations
    of most of the magic methods. You can use MagicMock without having to
    configure the magic methods yourself.

    If you use the ``spec`` or ``spec_set`` arguments then *only* magic
    methods that exist in the spec will be created.

    Attributes and the return value of a `MagicMock` will also be `MagicMocks`.
    """
    def __init__(self, *args, **kw):
        Mock.__init__(self, *args, **kw)

        these_magics = _magics
        if self._methods is not None:
            these_magics = _magics.intersection(self._methods)

        for entry in these_magics:
            # could specify parent?
            m = Mock()
            setattr(self, entry, m)
            _set_return_value(self, m, entry)

########NEW FILE########
__FILENAME__ = tests_proxy
#! /opt/local/bin/python
import sys
import base
import shotgun_api3 as api


class ServerConnectionTest(base.TestBase):
    '''Tests for server connection'''
    def setUp(self):
        super(ServerConnectionTest, self).setUp()

    def test_connection(self):
        '''Tests server connects and returns nothing'''
        result = self.sg.connect()
        self.assertEqual(result, None)

    def test_proxy_info(self):
        '''check proxy value depending http_proxy setting in config'''
        self.sg.connect()
        if self.config.http_proxy:
            sys.stderr.write("[WITH PROXY] ")
            self.assertTrue(isinstance(self.sg._connection.proxy_info, 
                                        api.lib.httplib2.ProxyInfo))
        else:
            sys.stderr.write("[NO PROXY] ")
            self.assertEqual(self.sg._connection.proxy_info, None)







        
        


########NEW FILE########
__FILENAME__ = tests_unit
#! /opt/local/bin/python
import unittest
from mock import patch, Mock
import shotgun_api3 as api

class TestShotgunInit(unittest.TestCase):
    '''Test case for Shotgun.__init__'''
    def setUp(self):
        self.server_path = 'http://server_path'
        self.script_name = 'script_name'
        self.api_key     = 'api_key'

    # Proxy Server Tests
    def test_http_proxy_server(self):
        proxy_server = "someserver.com"
        http_proxy = proxy_server
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, 8080)
        proxy_server = "123.456.789.012"
        http_proxy = proxy_server
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, 8080)

    def test_http_proxy_server_and_port(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, proxy_port)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        http_proxy = "%s:%d" % (proxy_server, proxy_port)
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, proxy_port)

    def test_http_proxy_server_and_port_with_authentication(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, 
                                      proxy_port)
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, proxy_port)
        self.assertEquals(sg.config.proxy_user, proxy_user)
        self.assertEquals(sg.config.proxy_pass, proxy_pass)
        proxy_server = "123.456.789.012"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, 
                                      proxy_port)
        sg = api.Shotgun(self.server_path, 
                         self.script_name, 
                         self.api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, proxy_port)
        self.assertEquals(sg.config.proxy_user, proxy_user)
        self.assertEquals(sg.config.proxy_pass, proxy_pass)
 
    def test_malformatted_proxy_info(self):
        proxy_server = "someserver.com"
        proxy_port = 1234
        proxy_user = "user"
        proxy_pass = "password"
        http_proxy = "%s:%s@%s:%d" % (proxy_user, proxy_pass, proxy_server, 
                                      proxy_port)
        conn_info = {
            'base_url': self.server_path,
            'script_name': self.script_name,
            'api_key': self.api_key, 
            'connect': False,
        }
        conn_info['http_proxy'] = 'http://someserver.com'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info['http_proxy'] = 'user@someserver.com'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
        conn_info['http_proxy'] = 'someserver.com:1234:5678'
        self.assertRaises(ValueError, api.Shotgun, **conn_info)
    
class TestShotgunSummarize(unittest.TestCase):
    '''Test case for _create_summary_request function and parameter
    validation as it exists in Shotgun.summarize.

    Does not require database connection or test data.'''
    def setUp(self):
        self.sg = api.Shotgun('http://server_path',
                              'script_name', 
                              'api_key', 
                              connect=False)


    def test_filter_operator_none(self):
        expected_logical_operator = 'and'
        filter_operator = None
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def _assert_filter_operator(self, expected_logical_operator, filter_operator):
        result = self.get_call_rpc_params(None, {'filter_operator':filter_operator})
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_all(self):
        expected_logical_operator = 'and'
        filter_operator = 'all'
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filter_operator_or(self):
        expected_logical_operator = 'or'
        filter_operator = 'or'
        self._assert_filter_operator(expected_logical_operator, filter_operator)

    def test_filters(self):
        path = 'path'
        relation = 'relation'
        value = 'value'
        expected_condition = {'path':path, 'relation':relation, 'values':[value]}
        args = ['',[[path, relation, value]],None]
        result = self.get_call_rpc_params(args, {})
        actual_condition = result['filters']['conditions'][0]
        self.assertEquals(expected_condition, actual_condition)
        
    @patch('shotgun_api3.Shotgun._call_rpc')
    def get_call_rpc_params(self, args, kws, call_rpc):
        '''Return params sent to _call_rpc from summarize.'''
        if not args:
            args = [None, [], None]
        self.sg.summarize(*args, **kws)
        return call_rpc.call_args[0][1]

    def test_grouping(self):
        result = self.get_call_rpc_params(None, {})
        self.assertFalse(result.has_key('grouping'))
        grouping = ['something']
        kws = {'grouping':grouping} 
        result = self.get_call_rpc_params(None, kws)
        self.assertEqual(grouping, result['grouping'])

    def test_grouping_type(self):
        '''test_grouping_type tests that grouping parameter is a list or None'''
        self.assertRaises(ValueError, self.sg.summarize, '', [], [], grouping='Not a list')

class TestShotgunBatch(unittest.TestCase):
    def setUp(self):
        self.sg = api.Shotgun('http://server_path',
                              'script_name', 
                              'api_key', 
                              connect=False)

    def test_missing_required_key(self):
        req = {}
        # requires keys request_type and entity_type
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req['entity_type'] = 'Entity'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        req['request_type'] = 'not_real_type'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # create requires data key
        req['request_type'] = 'create'
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # update requires entity_id and data
        req['request_type'] = 'update'
        req['data'] = {}
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        del req['data']
        req['entity_id'] = 2334
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])
        # delete requires entity_id
        req['request_type'] = 'delete'
        del req['entity_id']
        self.assertRaises(api.ShotgunError, self.sg.batch, [req])


class TestServerCapabilities(unittest.TestCase):
    def test_no_server_version(self):
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {})


    def test_bad_version(self):
        '''test_bad_meta tests passing bad meta data type'''
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {'version':(0,0,0)})

    def test_dev_version(self):
        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version':(3,4,0,'Dev')})
        self.assertEqual(serverCapabilities.version, (3,4,0))
        self.assertTrue(serverCapabilities.is_dev)

        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version':(2,4,0)})
        self.assertEqual(serverCapabilities.version, (2,4,0))
        self.assertFalse(serverCapabilities.is_dev)

class TestClientCapabilities(unittest.TestCase):

    def test_darwin(self):
        self.assert_platform('Darwin', 'mac')

    def test_windows(self):
        self.assert_platform('win32','windows')
        
    def test_linux(self):
        self.assert_platform('Linux', 'linux')

    def assert_platform(self, sys_ret_val, expected):
        platform = api.shotgun.sys.platform
        try:
            api.shotgun.sys.platform = sys_ret_val
            expected_local_path_field = "local_path_%s" % expected

            client_caps = api.shotgun.ClientCapabilities()
            self.assertEquals(client_caps.platform, expected)
            self.assertEquals(client_caps.local_path_field, expected_local_path_field)
        finally:
            api.shotgun.sys.platform = platform

    def test_no_platform(self):
        platform = api.shotgun.sys.platform
        try:
            api.shotgun.sys.platform = "unsupported"
            client_caps = api.shotgun.ClientCapabilities()
            self.assertEquals(client_caps.platform, None)
            self.assertEquals(client_caps.local_path_field, None)
        finally:
            api.shotgun.sys.platform = platform
        
    @patch('shotgun_api3.shotgun.sys')
    def test_py_version(self, mock_sys):
        major = 2
        minor = 7
        micro = 3
        mock_sys.version_info = (major, minor, micro, 'final', 0)
        expected_py_version = "%s.%s" % (major, minor)
        client_caps = api.shotgun.ClientCapabilities()
        self.assertEquals(client_caps.py_version, expected_py_version)
        
class TestFilters(unittest.TestCase):
    def test_empty(self):
        expected = {
            "logical_operator": "and",
            "conditions": []
        }
        
        result = api.shotgun._translate_filters([], None)
        self.assertEquals(result, expected)
    
    def test_simple(self):
        filters = [
            ["code", "is", "test"],
            ["sg_status_list", "is", "ip"]
        ]

        expected = {
            "logical_operator": "or",
            "conditions": [
                { "path": "code", "relation": "is", "values": ["test"] },
                { "path": "sg_status_list", "relation": "is", "values": ["ip"] }
            ]
        }
        
        result = api.shotgun._translate_filters(filters, "any")
        self.assertEquals(result, expected)
    
    # Test both styles of passing arrays
    def test_arrays(self):
        expected = {
            "logical_operator": "and",
            "conditions": [
                { "path": "code", "relation": "in", "values": ["test1", "test2", "test3"] }
            ]
        }
        
        filters = [
            ["code", "in", "test1", "test2", "test3"]
        ]
        
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEquals(result, expected)
        
        filters = [
            ["code", "in", ["test1", "test2", "test3"]]
        ]
        
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEquals(result, expected)

    def test_nested(self):
        filters = [
            ["code", "in", "test"],
            {
                "filter_operator": "any",
                "filters": [
                    ["sg_status_list", "is", "ip"],
                    ["sg_status_list", "is", "fin"],
                    {
                        "filter_operator": "all",
                        "filters": [
                            ["sg_status_list", "is", "hld"],
                            ["assets", "is", { "type": "Asset", "id": 9 }]
                        ]
                    }
                ]
            }
        ]
        
        expected = {
            "logical_operator": "and",
            "conditions": [
                { "path": "code", "relation": "in", "values": ["test"] },
                {
                    "logical_operator": "or",
                    "conditions": [
                        { "path": "sg_status_list", "relation": "is", "values": ["ip"] },
                        { "path": "sg_status_list", "relation": "is", "values": ["fin"] },
                        {
                            "logical_operator": "and",
                            "conditions": [
                                { "path": "sg_status_list", "relation": "is", "values": ["hld"] },
                                { "path": "assets", "relation": "is", "values": [ { "type": "Asset", "id": 9 } ] },
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = api.shotgun._translate_filters(filters, "all")
        self.assertEquals(result, expected)
    
    def test_invalid(self):
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, [], "bogus")
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, ["bogus"], "all")
        
        filters = [{
            "filter_operator": "bogus",
            "filters": []
        }]
        
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")
        
        filters = [{
            "filters": []
        }]
        
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")
        
        filters = [{
            "filter_operator": "all",
            "filters": { "bogus": "bogus" }
        }]
        
        self.assertRaises(api.ShotgunError, api.shotgun._translate_filters, filters, "all")

if __name__ == '__main__':
    unittest.main()





        
        


########NEW FILE########
__FILENAME__ = test_api
"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See
test_api_long for other tests.
"""

import datetime
import os
import re
from mock import patch, Mock, MagicMock
import time
import unittest
import urlparse

import shotgun_api3
from shotgun_api3.lib.httplib2 import Http

import base

class TestShotgunApi(base.LiveTestBase):
    def setUp(self):
        super(TestShotgunApi, self).setUp()
        # give note unicode content
        self.sg.update('Note', self.note['id'], {'content':u'La Pe\xf1a'})

    def test_info(self):
        """Called info"""
        #TODO do more to check results
        self.sg.info()

    def test_server_dates(self):
        """Pass datetimes to the server"""
        #TODO check results
        t = { 'project': self.project,
              'start_date': datetime.date.today() }
        self.sg.create('Task', t, ['content', 'sg_status_list'])


    def test_batch(self):
        """Batched create, update, delete"""

        requests = [
        {
            "request_type" : "create",
            "entity_type" : "Shot",
            "data": {
                "code" : "New Shot 5",
                "project" : self.project
            }
        },
        {
            "request_type" : "update",
            "entity_type" : "Shot",
            "entity_id" : self.shot['id'],
            "data" : {
                "code" : "Changed 1"
            }
        }]

        new_shot, updated_shot = self.sg.batch(requests)

        self.assertEqual(self.shot['id'], updated_shot["id"])
        self.assertTrue(new_shot.get("id"))

        new_shot_id = new_shot["id"]
        requests = [{ "request_type" : "delete",
                      "entity_type"  : "Shot",
                      "entity_id"    : new_shot_id
                    },
                    {
                        "request_type" : "update",
                        "entity_type" : "Shot",
                        "entity_id" : self.shot['id'],
                        "data" : {
                            "code" : self.shot['code']
                            }
                    }
                    ]

        result = self.sg.batch(requests)[0]
        self.assertEqual(True, result)

    def test_empty_batch(self):
        """Empty list sent to .batch()"""
        result = self.sg.batch([])
        self.assertEqual([], result)

    def test_create_update_delete(self):
        """Called create, update, delete, revive"""
        data = {
            'project': self.project,
            'code':'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list':'rev',
            'entity': self.asset,
            'user': self.human_user
        }

        version = self.sg.create("Version", data, return_fields = ["id"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        #TODO check results more thoroughly
        #TODO: test returned fields are requested fields

        data = data = {
            "description" : "updated test"
        }
        version = self.sg.update("Version", version["id"], data)
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)

        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(True, rv)
        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(False, rv)

        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(True, rv)
        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(False, rv)

    def test_last_accessed(self):
        page = self.sg.find('Page', [], fields=['last_accessed'], limit=1)
        self.assertEqual("Page", page[0]['type'])
        self.assertEqual(datetime.datetime, type(page[0]['last_accessed']))

    def test_get_session_token(self):
        """Got session UUID"""
        #TODO test results
        rv = self.sg._get_session_token()
        self.assertTrue(rv)

    def test_upload_download(self):
        """Upload and download an attachment tests"""
        # upload / download only works against a live server because it does
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
            return

        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        attach_id = self.sg.upload("Ticket",
            self.ticket['id'], path, 'attachments',
            tag_list="monkeys, everywhere, send, help")

        # test download with attachment_id
        attach_file = self.sg.download_attachment(attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)

        # test download with attachment_id as keyword
        attach_file = self.sg.download_attachment(attachment_id=attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)

        # test download with attachment_id (write to disk)
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sg_logo_download.jpg")
        result = self.sg.download_attachment(attach_id, file_path=file_path)
        self.assertEqual(result, file_path)
    	# On windows read may not read to end of file unless opened 'rb'
        fp = open(file_path, 'rb')
        attach_file = fp.read()
        fp.close()
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test download with attachment hash
        ticket = self.sg.find_one('Ticket', [['id', 'is', self.ticket['id']]],
                                  ['attachments'])
        attach_file = self.sg.download_attachment(ticket['attachments'][0])
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test download with attachment hash (write to disk)
        result = self.sg.download_attachment(ticket['attachments'][0],
                                             file_path=file_path)
        self.assertEqual(result, file_path)
        fp = open(file_path, 'rb')
        attach_file = fp.read()
        fp.close()
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test invalid requests
        INVALID_S3_URL = "https://sg-media-usor-01.s3.amazonaws.com/ada3de3ee3873875e1dd44f2eb0882c75ae36a4a/cd31346421dbeef781e0e480f259a3d36652d7f2/IMG_0465.MOV?AWSAccessKeyId=AKIAIQGOBSVN3FSQ5QFA&Expires=1371789959&Signature=SLbzv7DuVlZ8XAoOSQQAiGpF3u8%3D"
        self.assertRaises(shotgun_api3.ShotgunFileDownloadError, 
                            self.sg.download_attachment,
                            {"url": INVALID_S3_URL})
        INVALID_ATTACHMENT_ID = 99999999
        self.assertRaises(shotgun_api3.ShotgunFileDownloadError, 
                            self.sg.download_attachment,
                            INVALID_ATTACHMENT_ID)
        self.assertRaises(TypeError, self.sg.download_attachment,
                            "/path/to/some/file.jpg")
        self.assertRaises(ValueError, self.sg.download_attachment,
                            {"id":123, "type":"Shot"})
        self.assertRaises(TypeError, self.sg.download_attachment)

        # cleanup
        os.remove(file_path)

    def test_upload_thumbnail_in_create(self):
        """Upload a thumbnail via the create method"""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # test thumbnail upload
        data = {'image': path, 'code': 'Test Version',
                'project': self.project}
        new_version = self.sg.create("Version", data, return_fields=['image'])
        self.assertTrue(new_version is not None)
        self.assertTrue(isinstance(new_version, dict))
        self.assertTrue(isinstance(new_version.get('id'), int))
        self.assertEqual(new_version.get('type'), 'Version')
        self.assertEqual(new_version.get('project'), self.project)
        self.assertTrue(new_version.get('image') is not None)

        h = Http(".cache")
        thumb_resp, content = h.request(new_version.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        self.sg.delete("Version", new_version['id'])

        # test filmstrip image upload
        data = {'filmstrip_image': path, 'code': 'Test Version',
                'project': self.project}
        new_version = self.sg.create("Version", data, return_fields=['filmstrip_image'])
        self.assertTrue(new_version is not None)
        self.assertTrue(isinstance(new_version, dict))
        self.assertTrue(isinstance(new_version.get('id'), int))
        self.assertEqual(new_version.get('type'), 'Version')
        self.assertEqual(new_version.get('project'), self.project)
        self.assertTrue(new_version.get('filmstrip_image') is not None)

        h = Http(".cache")
        filmstrip_thumb_resp, content = h.request(new_version.get('filmstrip_image'), "GET")
        self.assertEqual(filmstrip_thumb_resp['status'], '200')
        self.assertEqual(filmstrip_thumb_resp['content-type'], 'image/jpeg')

        self.sg.delete("Version", new_version['id'])
    # end test_upload_thumbnail_in_create

    def test_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = self.sg.find_one('Version',
            [['id', 'is', self.version['id']]],
            fields=['image'])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])


        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image':None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_upload_thumbnail_for_task(self):
        """simple upload thumbnail for task test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Task",
            self.task['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        task_with_thumbnail = self.sg.find_one('Task',
            [['id', 'is', self.task['id']]],
            fields=['image'])

        self.assertEqual(task_with_thumbnail.get('type'), 'Task')
        self.assertEqual(task_with_thumbnail.get('id'), self.task['id'])

        h = Http(".cache")
        thumb_resp, content = h.request(task_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_linked_thumbnail_url(self):
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        thumb_id = self.sg.upload_thumbnail("Project",
            self.version['project']['id'], path)

        response_version_with_project = self.sg.find(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'project.Project.image']
        )

        if self.sg.server_caps.version and self.sg.server_caps.version >= (3, 3, 0):

            self.assertEqual(response_version_with_project[0].get('type'), 'Version')
            self.assertEqual(response_version_with_project[0].get('id'), self.version['id'])
            self.assertEqual(response_version_with_project[0].get('code'), 'Sg unittest version')

            h = Http(".cache")
            thumb_resp, content = h.request(response_version_with_project[0].get('project.Project.image'), "GET")
            self.assertEqual(thumb_resp['status'], '200')
            self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        else:
            expected_version_with_project = [
                {
                    'code': 'Sg unittest version',
                    'type': 'Version',
                    'id': self.version['id'],
                    'project.Project.image': thumb_id
                }
            ]
            self.assertEqual(expected_version_with_project, response_version_with_project)

    def test_share_thumbnail(self):
        """share thumbnail between two entities"""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))

        # upload thumbnail to first entity and share it with the rest
        thumbnail_id = self.sg.share_thumbnail(
            [self.version, self.shot],
            thumbnail_path=path)
        response_version_thumbnail = self.sg.find_one(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = self.sg.find_one(
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urlparse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urlparse.urlparse(response_version_thumbnail.get('image'))
        shot_path = _get_path(shot_url)
        version_path = _get_path(version_url)
        self.assertEqual(shot_path, version_path)

        # share thumbnail from source entity with entities
        source_thumbnail_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        thumbnail_id = self.sg.share_thumbnail(
            [self.asset, self.shot],
            source_entity=self.version)
        response_version_thumbnail = self.sg.find_one(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = self.sg.find_one(
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )
        response_asset_thumbnail = self.sg.find_one(
            'Asset',
            [['id', 'is', self.asset['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urlparse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urlparse.urlparse(response_version_thumbnail.get('image'))
        asset_url = urlparse.urlparse(response_asset_thumbnail.get('image'))

        shot_path = _get_path(shot_url)
        version_path = _get_path(version_url)
        asset_path = _get_path(asset_url)

        self.assertEqual(version_path, shot_path)
        self.assertEqual(version_path, asset_path)

        # raise errors when missing required params or providing conflicting ones
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.share_thumbnail,
                          [self.shot, self.asset], path, self.version)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.share_thumbnail,
                          [self.shot, self.asset])

    def test_deprecated_functions(self):
        """Deprecated functions raise errors"""
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema, "foo")
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.entity_types)


    def test_simple_summary(self):
        '''test_simple_summary tests simple query using summarize.'''
        summaries = [{'field': 'id', 'type': 'count'}]
        grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        assert(result['groups'])
        assert(result['groups'][0]['group_name'])
        assert(result['groups'][0]['group_value'])
        assert(result['groups'][0]['summaries'])
        assert(result['summaries'])

    def test_summary_include_archived_projects(self):
        if self.sg.server_caps.version > (5, 3, 13):
            # archive project
            self.sg.update('Project', self.project['id'], {'archived':True})
            # Ticket #25082 ability to hide archived projects in summary
            summaries = [{'field': 'id', 'type': 'count'}]
            grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
            filters = [['project', 'is', self.project]]
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_archived_projects=False)
            self.assertEqual(result['summaries']['id'],  0)
            self.sg.update('Project', self.project['id'], {'archived':False})

    def test_summary_values(self):
        ''''''
        # try to fix data if not in expected state
        shots = self.sg.find('Shot',[['project','is',self.project],['code','in',['shot 1','shot 2','shot 3']]])
        print len(shots)
        for shot in shots:
            # These shots should have been deleted,if they still exist it is due to an failure in mid-test
            self.sg.delete('Shot', shot['id'])


        shot_data = {
            'sg_status_list': 'ip',
            'sg_cut_duration': 100,
            'project': self.project
        }
        shots = []
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 1'}.items())))
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 2'}.items())))
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 3',
                                     'sg_status_list': 'fin'}.items())))
        summaries = [{'field': 'id', 'type': 'count'},
                     {'field': 'sg_cut_duration', 'type': 'sum'}]
        grouping = [{'direction': 'asc', 'field': 'sg_status_list', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        count = {'id': 4, 'sg_cut_duration': 300}
        groups =[
                {
                    'group_name': 'fin',
                    'group_value': 'fin',
                    'summaries': {'id': 1, 'sg_cut_duration': 100}
                },
                 {
                    'group_name': 'ip',
                    'group_value': 'ip',
                    'summaries': {'id': 2, 'sg_cut_duration': 200}
                },
                {
                    'group_name': 'wtg',
                    'group_value': 'wtg',
                    'summaries': {'id': 1, 'sg_cut_duration': 0}
                }
                ]
        # clean up
        batch_data = []
        for s in shots:
            batch_data.append({"request_type": "delete",
                               "entity_type": "Shot",
                               "entity_id": s['id']
                              })
        self.sg.batch(batch_data)

        self.assertEqual(result['summaries'], count)
        self.assertEqual(result['groups'], groups)

    def test_ensure_ascii(self):
        '''test_ensure_ascii tests ensure_unicode flag.'''
        sg_ascii = shotgun_api3.Shotgun(self.config.server_url,
                              self.config.script_name,
                              self.config.api_key,
                              ensure_ascii=True)

        result = sg_ascii.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        self.assertFalse(_has_unicode(result))


    def test_ensure_unicode(self):
        '''test_ensure_unicode tests ensure_unicode flag.'''
        sg_unicode = shotgun_api3.Shotgun(self.config.server_url,
                              self.config.script_name,
                              self.config.api_key,
                              ensure_ascii=False)
        result = sg_unicode.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        self.assertTrue(_has_unicode(result))

    def test_work_schedule(self):
        '''test_work_schedule tests WorkDayRules api'''
        self.maxDiff = None

        start_date = '2012-01-01'
        start_date_obj = datetime.datetime(2012, 1, 1)
        end_date = '2012-01-07'
        end_date_obj = datetime.datetime(2012, 1, 7)

        project = self.project
        user = self.sg.find_one('HumanUser', [['projects', 'is', project]], ['name'])

        work_schedule = self.sg.work_schedule_read(start_date, end_date, project, user)

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_read, start_date_obj, end_date_obj, project, user)

        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        self.assertEqual(work_schedule, resp)

        resp = self.sg.work_schedule_update('2012-01-02', False, 'Studio Holiday')
        expected = {
            'date': '2012-01-02',
            'description': 'Studio Holiday',
            'project': None,
            'user': None,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-02'] = {"reason": "STUDIO_EXCEPTION", "working": False, "description": "Studio Holiday"}
        self.assertEqual(work_schedule, resp)

        resp = self.sg.work_schedule_update('2012-01-03', False, 'Project Holiday', project)
        expected = {
            'date': '2012-01-03',
            'description': 'Project Holiday',
            'project': project,
            'user': None,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-03'] = {"reason": "PROJECT_EXCEPTION", "working": False, "description": "Project Holiday"}
        self.assertEqual(work_schedule, resp)

        jan4 = datetime.datetime(2012, 1, 4)

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_update, jan4, False, 'Artist Holiday',  user=user)

        resp = self.sg.work_schedule_update("2012-01-04", False, 'Artist Holiday',  user=user)
        expected = {'date': '2012-01-04',
            'description': 'Artist Holiday',
            'project': None,
            'user': user,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-04'] = {"reason": "USER_EXCEPTION", "working": False, "description": "Artist Holiday"}
        self.assertEqual(work_schedule, resp)

class TestDataTypes(base.LiveTestBase):
    '''Test fields representing the different data types mapped on the server side.

     Untested data types:  password, percent, pivot_column, serializable, image, currency
                           multi_entity, system_task_type, timecode, url, uuid, url_template
    '''
    def setUp(self):
        super(TestDataTypes, self).setUp()

    def test_set_checkbox(self):
        entity = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'email_notes'
        pos_values = [False, True]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)


    def test_set_color(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'color'
        pos_values = ['pipeline_step', '222,0,0']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)


    def test_set_date(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'due_date'
        pos_values = ['2008-05-08', '2011-05-05']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_date_time(self):
        entity = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'locked_until'
        local = shotgun_api3.shotgun.SG_TIMEZONE.local
        dt_1 = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=local)
        dt_2 = datetime.datetime(2009, 10, 13, 23, 10, tzinfo=local)
        pos_values = [dt_1, dt_2]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_duration(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'duration'
        pos_values = [2100, 1300]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_entity(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'entity'
        pos_values = [self.asset, self.shot]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected['id'], actual['id'])

    def test_set_float(self):
        entity = 'Version'
        entity_id = self.version['id']
        field_name = 'sg_movie_aspect_ratio'
        pos_values = [2.0, 3.0]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)


    def test_set_list(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'sg_note_type'
        pos_values = ['Internal','Client']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)


    def test_set_number(self):
        entity = 'Shot'
        entity_id = self.shot['id']
        field_name = 'head_in'
        pos_values = [2300, 1300]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_status_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'sg_status_list'
        pos_values = ['rdy','fin']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_status_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'sg_status_list'
        pos_values = ['rdy','fin']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_tag_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'tag_list'
        pos_values = [['a','b'],['c']]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_text(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'content'
        pos_values = ['this content', 'that content']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_text_html_entity(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'content'
        pos_values = ['<', '<']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def assert_set_field(self, entity, entity_id, field_name, pos_values):
        query_result = self.sg.find_one(entity,
                                         [['id', 'is', entity_id]],
                                         [field_name])
        initial_value = query_result[field_name]
        new_value = (initial_value == pos_values[0] and pos_values[1]) or pos_values[0]
        self.sg.update(entity, entity_id, {field_name:new_value})
        new_values = self.sg.find_one(entity,
                                     [['id', 'is', entity_id]],
                                     [field_name])
        return new_value, new_values[field_name]

class TestUtc(base.LiveTestBase):
    '''Test utc options'''

    def setUp(self):
        super(TestUtc, self).setUp()
        utc = shotgun_api3.shotgun.SG_TIMEZONE.utc
        self.datetime_utc = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=utc)
        local = shotgun_api3.shotgun.SG_TIMEZONE.local
        self.datetime_local = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=local)
        self.datetime_none = datetime.datetime(2008, 10, 13, 23, 10)

    def test_convert_to_utc(self):
        sg_utc= shotgun_api3.Shotgun(self.config.server_url,
                            self.config.script_name,
                            self.config.api_key,
                            http_proxy=self.config.http_proxy,
                            convert_datetimes_to_utc=True)
        self._assert_expected(sg_utc, self.datetime_none, self.datetime_local)
        self._assert_expected(sg_utc, self.datetime_local, self.datetime_local)

    def test_no_convert_to_utc(self):
        sg_no_utc= shotgun_api3.Shotgun(self.config.server_url,
                               self.config.script_name,
                               self.config.api_key,
                               http_proxy=self.config.http_proxy,
                               convert_datetimes_to_utc=False)
        self._assert_expected(sg_no_utc, self.datetime_none, self.datetime_none)
        self._assert_expected(sg_no_utc, self.datetime_utc, self.datetime_none)

    def _assert_expected(self, sg, date_time, expected):
        entity_name = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'locked_until'
        sg.update(entity_name, entity_id, {field_name:date_time})
        result = sg.find_one(entity_name, [['id','is',entity_id]],[field_name])
        self.assertEqual(result[field_name], expected)


class TestFind(base.LiveTestBase):
    def setUp(self):
        super(TestFind, self).setUp()
        # We will need the created_at field for the shot
        fields = self.shot.keys()[:]
        fields.append('created_at')
        self.shot = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], fields)
        # We will need the uuid field for our LocalStorage
        fields = self.local_storage.keys()[:]
        fields.append('uuid')
        self.local_storage = self.sg.find_one('LocalStorage', [['id', 'is', self.local_storage['id']]], fields)

    def test_find(self):
        """Called find, find_one for known entities"""
        filters = []
        filters.append(['project','is', self.project])
        filters.append(['id','is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

    def _id_in_result(self, entity_type, filters, expected_id):
        """
        Checks that a given id matches that of entities returned
        for particular filters.
        """
        results = self.sg.find(entity_type, filters)
        # can't use 'any' in python 2.4
        for result in results:
            if result['id'] == expected_id:
                return True
        return False

    #TODO test all applicable data types for 'in'
        #'currency' => [BigDecimal, Float, NilClass],
        #'image' => [Hash, NilClass],
        #'percent' => [Bignum, Fixnum, NilClass],
        #'serializable' => [Hash, Array, NilClass],
        #'system_task_type' => [String, NilClass],
        #'timecode' => [Bignum, Fixnum, NilClass],
        #'footage' => [Bignum, Fixnum, NilClass, String, Float, BigDecimal],
        #'url' => [Hash, NilClass],

        #'uuid' => [String],

    def test_in_relation_comma_id(self):
        """
        Test that 'in' relation using commas (old format) works with ids.
        """
        filters = [['id', 'in', self.project['id'], 99999]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_in_relation_list_id(self):
        """
        Test that 'in' relation using list (new format) works with ids.
        """
        filters = [['id', 'in', [self.project['id'], 99999]]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_not_in_relation_id(self):
        """
        Test that 'not_in' relation using commas (old format) works with ids.
        """
        filters = [['id', 'not_in', self.project['id'], 99999]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertFalse(result)

    def test_in_relation_comma_text(self):
        """
        Test that 'in' relation using commas (old format) works with text fields.
        """
        filters = [['name', 'in', self.project['name'], 'fake project name']]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_in_relation_list_text(self):
        """
        Test that 'in' relation using list (new format) works with text fields.
        """
        filters = [['name', 'in', [self.project['name'], 'fake project name']]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_not_in_relation_text(self):
        """
        Test that 'not_in' relation using commas (old format) works with ids.
        """
        filters = [['name', 'not_in', [self.project['name'], 'fake project name']]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertFalse(result)

    def test_in_relation_comma_color(self):
        """
        Test that 'in' relation using commas (old format) works with color fields.
        """
        filters = [['color', 'in', self.task['color'], 'Green'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_color(self):
        """
        Test that 'in' relation using list (new format) works with color fields.
        """
        filters = [['color', 'in', [self.task['color'], 'Green']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_color(self):
        """
        Test that 'not_in' relation using commas (old format) works with color fields.
        """
        filters = [['color', 'not_in', [self.task['color'], 'Green']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_date(self):
        """
        Test that 'in' relation using commas (old format) works with date fields.
        """
        filters = [['due_date', 'in', self.task['due_date'], '2012-11-25'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_date(self):
        """
        Test that 'in' relation using list (new format) works with date fields.
        """
        filters = [['due_date', 'in', [self.task['due_date'], '2012-11-25']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_date(self):
        """
        Test that 'not_in' relation using commas (old format) works with date fields.
        """
        filters = [['due_date', 'not_in', [self.task['due_date'], '2012-11-25']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    #TODO add datetime test for in and not_in

    def test_in_relation_comma_duration(self):
        """
        Test that 'in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', self.task['duration']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_duration(self):
        """
        Test that 'in' relation using list (new format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', [self.task['duration'],]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_duration(self):
        """
        Test that 'not_in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)

        filters = [['duration', 'not_in', [self.task['duration'],]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_entity(self):
        """
        Test that 'in' relation using commas (old format) works with entity fields.
        """
        filters = [['entity', 'in', self.task['entity'], self.asset],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_entity(self):
        """
        Test that 'in' relation using list (new format) works with entity fields.
        """
        filters = [['entity', 'in', [self.task['entity'], self.asset]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_entity(self):
        """
        Test that 'not_in' relation using commas (old format) works with entity fields.
        """
        filters = [['entity', 'not_in', [self.task['entity'], self.asset]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_entity_type(self):
        """
        Test that 'in' relation using commas (old format) works with entity_type fields.
        """
        filters = [['entity_type', 'in', self.step['entity_type'], 'something else']]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertTrue(result)

    def test_in_relation_list_entity_type(self):
        """
        Test that 'in' relation using list (new format) works with entity_type fields.
        """
        filters = [['entity_type', 'in', [self.step['entity_type'], 'something else']]]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertTrue(result)

    def test_not_in_relation_entity_type(self):
        """
        Test that 'not_in' relation using commas (old format) works with entity_type fields.
        """
        filters = [['entity_type', 'not_in', [self.step['entity_type'], 'something else']]]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertFalse(result)

    def test_in_relation_comma_float(self):
        """
        Test that 'in' relation using commas (old format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'in', self.version['sg_frames_aspect_ratio'], 44.0],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_in_relation_list_float(self):
        """
        Test that 'in' relation using list (new format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'in', [self.version['sg_frames_aspect_ratio'], 30.0]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_not_in_relation_float(self):
        """
        Test that 'not_in' relation using commas (old format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'not_in', [self.version['sg_frames_aspect_ratio'], 4.4]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertFalse(result)

    def test_in_relation_comma_list(self):
        """
        Test that 'in' relation using commas (old format) works with list fields.
        """
        filters = [['sg_priority', 'in', self.ticket['sg_priority'], '1'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertTrue(result)

    def test_in_relation_list_list(self):
        """
        Test that 'in' relation using list (new format) works with list fields.
        """
        filters = [['sg_priority', 'in', [self.ticket['sg_priority'], '1']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertTrue(result)

    def test_not_in_relation_list(self):
        """
        Test that 'not_in' relation using commas (old format) works with list fields.
        """
        filters = [['sg_priority', 'not_in', [self.ticket['sg_priority'], '1']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertFalse(result)

    def test_in_relation_comma_multi_entity(self):
        """
        Test that 'in' relation using commas (old format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'in', self.human_user, ],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_multi_entity(self):
        """
        Test that 'in' relation using list (new format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'in', [self.human_user, ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_multi_entity(self):
        """
        Test that 'not_in' relation using commas (old format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'not_in', [self.human_user, ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_number(self):
        """
        Test that 'in' relation using commas (old format) works with number fields.
        """
        filters = [['frame_count', 'in', self.version['frame_count'], 1],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_in_relation_list_number(self):
        """
        Test that 'in' relation using list (new format) works with number fields.
        """
        filters = [['frame_count', 'in', [self.version['frame_count'], 1]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_not_in_relation_number(self):
        """
        Test that 'not_in' relation using commas (old format) works with number fields.
        """
        filters = [['frame_count', 'not_in', [self.version['frame_count'], 1]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertFalse(result)


    def test_in_relation_comma_status_list(self):
        """
        Test that 'in' relation using commas (old format) works with status_list fields.
        """
        filters = [['sg_status_list', 'in', self.task['sg_status_list'], 'fin'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_status_list(self):
        """
        Test that 'in' relation using list (new format) works with status_list fields.
        """
        filters = [['sg_status_list', 'in', [self.task['sg_status_list'], 'fin']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_status_list(self):
        """
        Test that 'not_in' relation using commas (old format) works with status_list fields.
        """
        filters = [['sg_status_list', 'not_in', [self.task['sg_status_list'], 'fin']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_uuid(self):
        """
        Test that 'in' relation using commas (old format) works with uuid fields.
        """
        filters = [['uuid', 'in', self.local_storage['uuid'],]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_in_relation_list_uuid(self):
        """
        Test that 'in' relation using list (new format) works with uuid fields.
        """
        filters = [['uuid', 'in', [self.local_storage['uuid'],]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_not_in_relation_uuid(self):
        """
        Test that 'not_in' relation using commas (old format) works with uuid fields.
        """
        filters = [['uuid', 'not_in', [self.local_storage['uuid'],]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertFalse(result)

    def test_find(self):
        """Called find, find_one for known entities"""
        filters = []
        filters.append(['project','is', self.project])
        filters.append(['id','is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

    def test_find_in(self):
        """Test use of 'in' relation with find."""
        # id
        # old comma seperated format
        filters = [['id', 'in', self.project['id'], 99999]]
        projects = self.sg.find('Project', filters)
        # can't use 'any' in py 2.4
        match = False
        for project in projects:
            if project['id'] == self.project['id']:
                match = True
        self.assertTrue(match)

        # new list format
        filters = [['id', 'in', [self.project['id'], 99999]]]
        projects = self.sg.find('Project', filters)
        # can't use 'any' in py 2.4
        match = False
        for project in projects:
            if project['id'] == self.project['id']:
                match = True
        self.assertTrue(match)

        # text field
        filters = [['name', 'in', [self.project['name'], 'fake project name']]]
        projects = self.sg.find('Project', filters)
        project = projects[0]
        self.assertEqual(self.project['id'], project['id'])

    def test_unsupported_filters(self):
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Shot', [['image', 'is_not', [ {"type": "Thumbnail", "id": 9 }]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'HumanUser', [['password_proxy', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'EventLogEntry', [['meta', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Revision', [['meta', 'attachment', [None]]])

    def test_zero_is_not_none(self):
        '''Test the zero and None are differentiated using "is_not" filter.
           Ticket #25127
        '''
        # Create a number field if it doesn't already exist
        num_field = 'sg_api_tests_number_field'
        if num_field not in self.sg.schema_field_read('Asset').keys():
            self.sg.schema_field_create('Asset', 'number', num_field.replace('sg_','').replace('_',' '))

        # Set to None
        self.sg.update( 'Asset', self.asset['id'], { num_field: None })

        # Should be filtered out
        result = self.sg.find( 'Asset', [['id','is',self.asset['id']],[num_field, 'is_not', None]] ,[num_field] )
        self.assertEquals([], result)

        # Set it to zero
        self.sg.update( 'Asset', self.asset['id'], { num_field: 0 })

        # Should not be filtered out
        result = self.sg.find_one( 'Asset', [['id','is',self.asset['id']],[num_field, 'is_not', None]] ,[num_field] )
        self.assertFalse(result == None)


        # Set it to some other number
        self.sg.update( 'Asset', self.asset['id'], { num_field: 1 })

        # Should not be filtered out
        result = self.sg.find_one( 'Asset', [['id','is',self.asset['id']],[num_field, 'is_not', None]] ,[num_field] )
        self.assertFalse(result == None)

    def test_include_archived_projects(self):
        if self.sg.server_caps.version > (5, 3, 13):
            # Ticket #25082
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(self.shot['id'], result['id'])

            # archive project 
            self.sg.update('Project', self.project['id'], {'archived':True})

            # setting defaults to True, so we should get result
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(self.shot['id'], result['id'])

            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]], include_archived_projects=False)
            self.assertEquals(None, result)

            # unarchive project
            self.sg.update('Project', self.project['id'], {'archived':False})

class TestFollow(base.LiveTestBase):
    def setUp(self):
        super(TestFollow, self).setUp()
        self.sg.update( 'HumanUser', self.human_user['id'], {'projects':[self.project]})

    def test_follow(self):
        '''Test follow method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return

        result = self.sg.follow(self.human_user, self.shot)
        assert(result['followed'])

    def test_unfollow(self):
        '''Test unfollow method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return
        
        result = self.sg.unfollow(self.human_user, self.shot)
        assert(result['unfollowed'])
    
    def test_followers(self):
        '''Test followers method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return
        
        result = self.sg.follow(self.human_user, self.shot)
        assert(result['followed'])
        
        result = self.sg.followers(self.shot)
        self.assertEqual( 1, len(result) )
        self.assertEqual( self.human_user['id'], result[0]['id'] )

class TestErrors(base.TestBase):
    def test_bad_auth(self):
        '''test_bad_auth invalid script name or api key raises fault'''
        server_url = self.config.server_url
        script_name = 'not_real_script_name'
        api_key = self.config.api_key
        login = self.config.human_login
        password = self.config.human_password

        # Test various combinations of illegal arguments
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, None, api_key)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, None)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, api_key, login=login, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, login=login)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, login=login, password=password)

        # Test failed authentications
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

        script_name = self.config.script_name
        api_key = 'notrealapikey'
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

        sg = shotgun_api3.Shotgun(server_url, login=login, password='not a real password')
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

    @patch('shotgun_api3.shotgun.Http.request')
    def test_status_not_200(self, mock_request):
        response = MagicMock(name="response mock", spec=dict)
        response.status = 300
        response.reason = 'reason'
        mock_request.return_value = (response, {})
        self.assertRaises(shotgun_api3.ProtocolError, self.sg.find_one, 'Shot', [])

#    def test_malformed_response(self):
#        #TODO ResponseError
#        pass


class TestScriptUserSudoAuth(base.LiveTestBase):
    def setUp(self):
        super(TestScriptUserSudoAuth, self).setUp('ApiUser')
    
    def test_user_is_creator(self):
        """
        Test 'sudo_as_login' option: on create, ensure appropriate user is set in created-by
        """
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 3, 12):
            return

        x = shotgun_api3.Shotgun(self.config.server_url,
                    self.config.script_name,
                    self.config.api_key,
                    http_proxy=self.config.http_proxy,
                    sudo_as_login=self.config.human_login )
                    
        data = {
            'project': self.project,
            'code':'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list':'na',
            'entity': self.asset,
            'user': self.human_user
        }

        version = x.create("Version", data, return_fields = ["id","created_by"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        self.assertTrue("created_by" in version)
        self.assertEqual( self.config.human_name, version['created_by']['name'] )

class TestHumanUserSudoAuth(base.TestBase):
    def setUp(self):
        super(TestHumanUserSudoAuth, self).setUp('HumanUser')
    
    def test_human_user_sudo_auth_fails(self):
        """
        Test 'sudo_as_login' option for HumanUser.
        Request fails on server because user has no permission to Sudo.
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 3, 12):
            return

        x = shotgun_api3.Shotgun(self.config.server_url,
                    login=self.config.human_login,
                    password=self.config.human_password,
                    http_proxy=self.config.http_proxy,
                    sudo_as_login="blah" )
        self.assertRaises(shotgun_api3.Fault, x.find_one, 'Shot', [])
        try :
            x.find_one('Shot',[])
        except shotgun_api3.Fault, e:
            # py24 exceptions don't have message attr
            if hasattr(e, 'message'):
                self.assertEquals("The user does not have permission to 'sudo': ", e.message)
            else:
                self.assertEquals("The user does not have permission to 'sudo': ", e.args[0])



class TestHumanUserAuth(base.HumanUserAuthLiveTestBase):
    def test_humanuser_find(self):
        """Called find, find_one for known entities as human user"""
        filters = []
        filters.append(['project', 'is', self.project])
        filters.append(['id', 'is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

    def test_humanuser_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test as human user."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = self.sg.find_one('Version',
            [['id', 'is', self.version['id']]],
            fields=['image'])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])


        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image':None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)


class TestProjectLastAccessedByCurrentUser(base.LiveTestBase):
    # Ticket #24681
    def test_logged_in_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 17):
            return

        sg = shotgun_api3.Shotgun(self.config.server_url,
                    login=self.config.human_login,
                    password=self.config.human_password,
                    http_proxy=self.config.http_proxy)
 
        initial = sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])

        sg.update_project_last_accessed(self.project)

        current =  sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual( initial, current )
        # it's possible initial is None
        if initial:
            assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])


    def test_pass_in_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 17):
            return

        sg = shotgun_api3.Shotgun( self.config.server_url,
                                   login=self.config.human_login,
                                   password=self.config.human_password,
                                   http_proxy=self.config.http_proxy )
 
        initial = sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])

        # this instance of the api is not logged in as a user
        self.sg.update_project_last_accessed(self.project, user=self.human_user)

        current =  sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual( initial, current )
        # it's possible initial is None
        if initial:
            assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])

    def test_sudo_as_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 17):
            return

        sg = shotgun_api3.Shotgun( self.config.server_url,
                                   self.config.script_name,
                                   self.config.api_key,
                                   http_proxy=self.config.http_proxy,
                                   sudo_as_login=self.config.human_login )

        initial = sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])
        time.sleep(1)

        sg.update_project_last_accessed(self.project)

        current =  sg.find_one('Project', [['id','is',self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual( initial, current )
        # it's possible initial is None
        if initial:
            assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])

def  _has_unicode(data):
    for k, v in data.items():
        if (isinstance(k, unicode)):
            return True
        if (isinstance(v, unicode)):
            return True
    return False

def _get_path(url):
    # url_parse returns native objects for older python versions (2.4)
    if isinstance(url, dict):
        return url.get('path')
    elif isinstance(url, tuple):
        return os.path.join(url[:4])
    else:
        return url.path

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_api_long
"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

import base

class TestShotgunApiLong(base.LiveTestBase):
    
    def test_automated_find(self):
        """Called find for each entity type and read all fields"""
        all_entities = self.sg.schema_entity_read().keys()
        direction = "asc"
        filter_operator = "all"
        limit = 1
        page = 1
        for entity_type in all_entities:
            if entity_type in ("Asset", "Task", "Shot", "Attachment",
                               "Candidate"):
                continue
            print "Finding entity type", entity_type

            fields = self.sg.schema_field_read(entity_type)
            if not fields:
                print "No fields for %s skipping" % (entity_type,)
                continue
                 
            #trying to use some different code paths to the other find test
            #TODO for our test project, we haven't populated these entities....
            order = [{'field_name': fields.keys()[0], 'direction': direction}]
            if "project" in fields:
                filters = [['project', 'is', self.project]]
            else:
                filters = []

            records = self.sg.find(entity_type, filters, fields=fields.keys(), 
                                   order=order, filter_operator=filter_operator,
                                   limit=limit, page=page)
            
            self.assertTrue(isinstance(records, list))
            
            if filter_operator == "all":
                filter_operator = "any"
            else: 
                filter_operator = "all"
            if direction == "desc":
                direction = "asc"
            else: 
                direction = "desc"
            limit = (limit % 5) + 1
            page = (page % 3) + 1
        

    def test_schema(self):
        """Called schema functions"""
        
        schema = self.sg.schema_entity_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)

        schema = self.sg.schema_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        
        schema = self.sg.schema_field_read("Version")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        
        schema = self.sg.schema_field_read("Version", field_name="user")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        self.assertTrue("user" in schema)
                
        properties = { "description" : "How many monkeys were needed" }
        new_field_name = self.sg.schema_field_create("Version", "number", 
                                                     "Monkey Count", 
                                                     properties=properties)
           
        properties = {"description" : "How many monkeys turned up"}
        ret_val = self.sg.schema_field_update("Version",
                                               new_field_name, 
                                               properties)
        self.assertTrue(ret_val)
        
        ret_val = self.sg.schema_field_delete("Version", new_field_name)
        self.assertTrue(ret_val)
        
if __name__ == '__main__': 
    base.unittest.main()

########NEW FILE########
__FILENAME__ = test_client
"""Tests against the client software that do not involve calling the
CRUD functions. These tests always use a mock http connection so not not
need a live server to run against."""

import base64
import datetime
import re
try:
    import simplejson as json
except ImportError:
    try:
        import json as json
    except ImportError:
        import shotgun_api3.lib.simplejson as json

import platform
import sys
import time
import unittest
import mock

import shotgun_api3.lib.httplib2 as httplib2
import shotgun_api3 as api
from shotgun_api3.shotgun import ServerCapabilities, SG_TIMEZONE
import base

class TestShotgunClient(base.MockTestBase):
    '''Test case for shotgun api with server interactions mocked.'''

    def setUp(self):
        super(TestShotgunClient, self).setUp()
        #get domain and uri scheme
        match = re.search('(https?://)(.*)', self.server_url)
        self.uri_prefix = match.group(1)
        self.domain     = match.group(2)
        #always want the mock on
        self._setup_mock()

    def test_detect_client_caps(self):
        """Client and server capabilities detected"""
        client_caps = self.sg.client_caps
        self.sg.connect()
        self.assertEqual(1, self.sg._http_request.call_count)

        self.assertTrue(client_caps is not None)
        self.assertTrue(client_caps.platform in ("windows", "linux", "mac"))
        self.assertTrue(client_caps.local_path_field.startswith("local_path"))
        self.assertTrue(str(client_caps).startswith("ClientCapabilities"))
        self.assertTrue(client_caps.py_version.startswith(str(sys.version_info[0])))
        self.assertTrue(client_caps.py_version.endswith(str(sys.version_info[1])))

    def test_detect_server_caps(self):
        '''test_detect_server_caps tests that ServerCapabilities object is made
        with appropriate settings for given server version.'''
        #has paging is tested else where.
        server_info = { "version" : [9,9,9] }
        self._mock_http(server_info)
        # ensrue the server caps is re-read
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps is not None)
        self.assertFalse(self.sg.server_caps.is_dev)
        self.assertEqual((9,9,9), self.sg.server_caps.version)
        self.assertTrue(self.server_url.endswith(self.sg.server_caps.host))
        self.assertTrue(str(self.sg.server_caps).startswith( "ServerCapabilities"))
        self.assertEqual(server_info, self.sg.server_info)

        self._mock_http({ "version" : [9,9,9, "Dev"] })
        self.sg._server_caps = None
        self.assertTrue(self.sg.server_caps.is_dev)


    def test_server_version_json(self):
        '''test_server_version_json tests expected versions for json support.'''
        sc = ServerCapabilities("foo", {"version" : (2,4,0)})

        sc.version = (2,3,99)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)
        self.assertRaises(api.ShotgunError, ServerCapabilities, "foo",
            {"version" : (2,2,0)})

        sc.version = (0,0,0)
        self.assertRaises(api.ShotgunError, sc._ensure_json_supported)

        sc.version = (2,4,0)
        sc._ensure_json_supported()

        sc.version = (2,5,0)
        sc._ensure_json_supported()


    def test_session_uuid(self):
        """test_session_uuid tests session UUID is included in request"""
        #ok for the mock server to just return an error, we want to look at
        #whats in the request
        self._mock_http({ "message":"Go BANG",
                          "exception":True })

        def auth_args():
            args = self.sg._http_request.call_args[0]
            body = args[2]
            body = json.loads(body)
            return body["params"][0]

        self.sg.set_session_uuid(None)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertTrue("session_uuid" not in auth_args())

        my_uuid = '5a1d49b0-0c69-11e0-a24c-003048d17544'
        self.sg.set_session_uuid(my_uuid)
        self.assertRaises(api.Fault, self.sg.delete, "FakeType", 1)
        self.assertEqual(my_uuid, auth_args()["session_uuid"])

    def test_config(self):
        """Client config can be created"""
        x = api.shotgun._Config()
        self.assertTrue(x is not None)

    def test_url(self):
        """Server url is parsed correctly"""
        login    = self.human_user['login']
        password = self.human_password

        self.assertRaises(ValueError, api.Shotgun, None, None, None, connect=False)
        self.assertRaises(ValueError, api.Shotgun, "file://foo.com",None,None, connect=False)

        self.assertEqual("/api3/json", self.sg.config.api_path)

        #support auth details in the url of the form
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)
        sg = api.Shotgun(auth_url, None, None, connect=False)
        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, sg.config.authorization)

    def test_authorization(self):
        """Authorization passed to server"""
        login    = self.human_user['login']
        password = self.human_password
        login_password = "%s:%s" % (login, password)
        # login:password@domain
        auth_url = "%s%s@%s" % (self.uri_prefix, login_password, self.domain)

        self.sg = api.Shotgun(auth_url, "foo", "bar", connect=False)
        self._setup_mock()
        self._mock_http({ 'version': [2, 4, 0, u'Dev'] })

        self.sg.info()

        args, _ = self.sg._http_request.call_args
        verb, path, body, headers = args

        expected = "Basic " + base64.encodestring(login_password).strip()
        self.assertEqual(expected, headers.get("Authorization"))

    def test_user_agent(self):
        """User-Agent passed to server"""
        # test default user agent
        self.sg.info()
        args, _ = self.sg._http_request.call_args
        (_, _, _, headers) = args
        expected = "shotgun-json (%s)" % api.__version__
        self.assertEqual(expected, headers.get("user-agent"))

        # test adding to user agent
        self.sg.add_user_agent("test-agent")
        self.sg.info()
        args, _ = self.sg._http_request.call_args
        (_, _, _, headers) = args
        expected = "shotgun-json (%s); test-agent" % api.__version__
        self.assertEqual(expected, headers.get("user-agent"))

        # test resetting user agent
        self.sg.reset_user_agent()
        self.sg.info()
        args, _ = self.sg._http_request.call_args
        (_, _, _, headers) = args
        expected = "shotgun-json (%s)" % api.__version__
        self.assertEqual(expected, headers.get("user-agent"))

    def test_connect_close(self):
        """Connection is closed and opened."""
        #The mock created an existing mock connection,
        self.sg.connect()
        self.assertEqual(0, self.mock_conn.request.call_count)
        self.sg.close()
        self.assertEqual(None, self.sg._connection)


    def test_network_retry(self):
        """Network failure is retried"""
        self.sg._http_request.side_effect = httplib2.HttpLib2Error

        self.assertRaises(httplib2.HttpLib2Error, self.sg.info)
        self.assertTrue(
            self.sg.config.max_rpc_attempts ==self.sg._http_request.call_count,
            "Call is repeated")

    def test_http_error(self):
        """HTTP error raised and not retried."""

        self._mock_http( "big old error string",
                       status=(500, "Internal Server Error"))

        self.assertRaises(api.ProtocolError, self.sg.info)
        self.assertEqual(1,
                        self.sg._http_request.call_count,
                        "Call is not repeated")

    def test_rpc_error(self):
        """RPC error transformed into Python error"""

        self._mock_http({ "message":"Go BANG",
                          "exception":True })

        self.assertRaises(api.Fault, self.sg.info)

        try:
            self.sg.info()
        except api.Fault, e:
            self.assertEqual("Go BANG", str(e))

    def test_call_rpc(self):
        """Named rpc method is called and results handled"""

        d = { "no-results" : "data without a results key" }
        self._mock_http(d)
        rv = self.sg._call_rpc("no-results", None)
        self._assert_http_method("no-results", None)
        expected = "rpc response without results key is returned as-is"
        self.assertEqual(d, rv, expected )

        d = { "results" : {"singleton" : "result"} }
        self._mock_http(d)
        rv = self.sg._call_rpc("singleton", None)
        self._assert_http_method("singleton", None)
        expected = "rpc response with singleton result"
        self.assertEqual(d["results"], rv, expected )

        d = { "results" : ["foo", "bar"] }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list", a)
        self._assert_http_method("list", a)
        expected = "rpc response with list result"
        self.assertEqual(d["results"], rv, expected )

        d = { "results" : ["foo", "bar"] }
        a = {"some" : "args"}
        self._mock_http(d)
        rv = self.sg._call_rpc("list-first", a, first=True)
        self._assert_http_method("list-first", a)
        expected = "rpc response with list result, first item"
        self.assertEqual(d["results"][0], rv, expected )

        # Test unicode mixed with utf-8 as reported in Ticket #17959
        d = { "results" : ["foo", "bar"] }
        a = { "utf_str": "\xe2\x88\x9a", "unicode_str": "\xe2\x88\x9a".decode("utf-8") }
        self._mock_http(d)
        rv = self.sg._call_rpc("list", a)
        expected = "rpc response with list result"
        self.assertEqual(d["results"], rv, expected )



    def test_transform_data(self):
        """Outbound data is transformed"""
        timestamp = time.time()
        #microseconds will be last during transforms
        now = datetime.datetime.fromtimestamp(timestamp).replace(
            microsecond=0, tzinfo=SG_TIMEZONE.local)
        utc_now = datetime.datetime.utcfromtimestamp(timestamp).replace(
            microsecond=0)
        local = {
            "date" : now.strftime('%Y-%m-%d'),
            "datetime" : now,
            "time" : now.time()
        }
        #date will still be the local date, because they are not transformed
        utc = {
            "date" : now.strftime('%Y-%m-%d'),
            "datetime": utc_now,
            "time" : utc_now.time()
        }

        def _datetime(s, f):
            return datetime.datetime(*time.strptime(s, f)[:6])

        def assert_wire(wire, match):
            self.assertTrue(isinstance(wire["date"], basestring))
            d = _datetime(wire["date"], "%Y-%m-%d").date()
            d = wire['date']
            self.assertEqual(match["date"], d)
            self.assertTrue(isinstance(wire["datetime"], basestring))
            d = _datetime(wire["datetime"], "%Y-%m-%dT%H:%M:%SZ")
            self.assertEqual(match["datetime"], d)
            self.assertTrue(isinstance(wire["time"], basestring))
            d = _datetime(wire["time"], "%Y-%m-%dT%H:%M:%SZ")
            self.assertEqual(match["time"], d.time())

        #leave as local
        #AMORTON: tests disabled for now, always have utc over the wire
        # self.sg.config.convert_datetimes_to_utc = False
        # wire = self.sg._transform_outbound(local)
        # print "local ", local
        # print "wire ", wire
        # assert_wire(wire, local)
        # wire = self.sg._transform_inbound(wire)
        # #times will become datetime over the wire
        # wire["time"] = wire["time"].time()
        # self.assertEqual(local, wire)

        self.sg.config.convert_datetimes_to_utc = True
        wire = self.sg._transform_outbound(local)
        assert_wire(wire, utc)
        wire = self.sg._transform_inbound(wire)
        #times will become datetime over the wire
        wire["time"] = wire["time"].time()
        self.assertEqual(local, wire)

    def test_encode_payload(self):
        """Request body is encoded as JSON"""

        d = {
            "this is " : u"my data \u00E0"
        }
        j = self.sg._encode_payload(d)
        self.assertTrue(isinstance(j, str))

        d = {
            "this is " : u"my data"
        }
        j = self.sg._encode_payload(d)
        self.assertTrue(isinstance(j, str))

    def test_decode_response_ascii(self):
        self._assert_decode_resonse(True, u"my data \u00E0".encode('utf8'))

    def test_decode_response_unicode(self):
        self._assert_decode_resonse(False, u"my data \u00E0")

    def _assert_decode_resonse(self, ensure_ascii, data):
        """HTTP Response is decoded as JSON or text"""

        headers = {
            "content-type" : "application/json;charset=utf-8"
        }
        d = {
            "this is " : data
        }
        sg = api.Shotgun(self.config.server_url,
                         self.config.script_name,
                         self.config.api_key,
                         http_proxy=self.config.http_proxy,
                         ensure_ascii = ensure_ascii,
                         connect=False)

        j = json.dumps(d, ensure_ascii=ensure_ascii, encoding="utf-8")
        self.assertEqual(d, sg._decode_response(headers, j))

        headers["content-type"] = "text/javascript"
        self.assertEqual(d, sg._decode_response(headers, j))

        headers["content-type"] = "text/foo"
        self.assertEqual(j, sg._decode_response(headers, j))


    def test_parse_records(self):
        """Parse records to replace thumbnail and local paths"""

        system = platform.system().lower()
        if system =='darwin':
            local_path_field = "local_path_mac"
        elif system == 'windows':
            local_path_field = "local_path_windows"
        elif system == 'linux':
            local_path_field = "local_path_linux"
        orig = {
            "type" : "FakeAsset",
            "id" : 1234,
            "image" : "blah",
            "foo" : {
                "link_type" : "local",
                local_path_field: "/foo/bar.jpg",
            }
        }
        url = "http://foo/files/0000/0000/0012/232/shot_thumb.jpg"
        self.sg._build_thumb_url = mock.Mock(
            return_value=url)

        modified, txt = self.sg._parse_records([orig, "plain text"])
        self.assertEqual("plain text", txt,
            "non dict value is left as is")

        self.sg._build_thumb_url.assert_called_once_with("FakeAsset", 1234)

        self.assertEqual(url, modified["image"],
            "image path changed to url path")
        self.assertEqual("/foo/bar.jpg", modified["foo"]["local_path"])
        self.assertEqual("file:///foo/bar.jpg", modified["foo"]["url"])


    def test_thumb_url(self):
        """Thumbnail endpoint used to get thumbnail url"""

        #the thumbnail service returns a two line
        #test response success code on line 1, data on line 2
        resp = "1\n/files/0000/0000/0012/232/shot_thumb.jpg"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.sg.config.scheme = "http"
        self.sg.config.server = "foo.com"

        url = self.sg._build_thumb_url("FakeAsset", 1234)

        self.assertEqual(
            "http://foo.com/files/0000/0000/0012/232/shot_thumb.jpg", url)
        self.assertTrue(self.sg._http_request.called,
            "http request made to get url")
        args, _ = self.sg._http_request.call_args
        verb, path, body, headers = args
        self.assertEqual(
            "/upload/get_thumbnail_url?entity_type=FakeAsset&entity_id=1234",
            path, "thumbnail url called with correct args")

        resp = "0\nSome Error"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.assertRaises(api.ShotgunError, self.sg._build_thumb_url,
            "FakeAsset", 456)

        resp = "99\nSome Error"
        self._mock_http(resp, headers={"content-type" : "text/plain"})
        self.assertRaises(RuntimeError, self.sg._build_thumb_url,
            "FakeAsset", 456)

class TestShotgunClientInterface(base.MockTestBase):
    '''Tests expected interface for shotgun module and client'''
    def test_client_interface(self):
        expected_attributes = ['base_url',
                               'config',
                               'client_caps',
                               'server_caps']
        for expected_attribute in expected_attributes:
            if not hasattr(self.sg, expected_attribute):
                assert False, '%s not found on %s' % (expected_attribute,
                                                      self.sg)

    def test_module_interface(self):
        import shotgun_api3
        expected_contents = ['Shotgun', 'ShotgunError', 'Fault',
                             'ProtocolError', 'ResponseError', 'Error',
                             'sg_timezone', '__version__']
        for expected_content in expected_contents:
            if not hasattr(shotgun_api3, expected_content):
                assert False, '%s not found on module %s' % (expected_content,
                                                            shotgun_api3)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
