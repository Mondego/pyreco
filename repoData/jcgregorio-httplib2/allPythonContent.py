__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# httplib2 documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 27 16:07:14 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys

# If your extensions are in another directory, add it here.
#sys.path.append('some/directory')

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'httplib2'
copyright = '2008, Joe Gregorio'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.4'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'httplib2doc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
#latex_documents = []

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
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
    (0xA0, 0xD7FF),
    (0xE000, 0xF8FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    (0x10000, 0x1FFFD),
    (0x20000, 0x2FFFD),
    (0x30000, 0x3FFFD),
    (0x40000, 0x4FFFD),
    (0x50000, 0x5FFFD),
    (0x60000, 0x6FFFD),
    (0x70000, 0x7FFFD),
    (0x80000, 0x8FFFD),
    (0x90000, 0x9FFFD),
    (0xA0000, 0xAFFFD),
    (0xB0000, 0xBFFFD),
    (0xC0000, 0xCFFFD),
    (0xD0000, 0xDFFFD),
    (0xE1000, 0xEFFFD),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
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

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

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
        (i.e. those which do not support the CONNECT method).
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
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
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
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
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
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = socket
from realsocket import gaierror, error, getaddrinfo, SOCK_STREAM

########NEW FILE########
__FILENAME__ = test_proxies
import unittest
import errno
import os
import signal
import subprocess
import tempfile

import nose

import httplib2
from httplib2 import socks
from httplib2.test import miniserver

tinyproxy_cfg = """
User "%(user)s"
Port %(port)s
Listen 127.0.0.1
PidFile "%(pidfile)s"
LogFile "%(logfile)s"
MaxClients 2
StartServers 1
LogLevel Info
"""


class FunctionalProxyHttpTest(unittest.TestCase):
    def setUp(self):
        if not socks:
            raise nose.SkipTest('socks module unavailable')
        if not subprocess:
            raise nose.SkipTest('subprocess module unavailable')

        # start a short-lived miniserver so we can get a likely port
        # for the proxy
        self.httpd, self.proxyport = miniserver.start_server(
            miniserver.ThisDirHandler)
        self.httpd.shutdown()
        self.httpd, self.port = miniserver.start_server(
            miniserver.ThisDirHandler)

        self.pidfile = tempfile.mktemp()
        self.logfile = tempfile.mktemp()
        fd, self.conffile = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        our_cfg = tinyproxy_cfg % {'user': os.getlogin(),
                                   'pidfile': self.pidfile,
                                   'port': self.proxyport,
                                   'logfile': self.logfile}
        f.write(our_cfg)
        f.close()
        try:
            # TODO use subprocess.check_call when 2.4 is dropped
            ret = subprocess.call(['tinyproxy', '-c', self.conffile])
            self.assertEqual(0, ret)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise nose.SkipTest('tinyproxy not available')
            raise

    def tearDown(self):
        self.httpd.shutdown()
        try:
            pid = int(open(self.pidfile).read())
            os.kill(pid, signal.SIGTERM)
        except OSError, e:
            if e.errno == errno.ESRCH:
                print '\n\n\nTinyProxy Failed to start, log follows:'
                print open(self.logfile).read()
                print 'end tinyproxy log\n\n\n'
            raise
        map(os.unlink, (self.pidfile,
                        self.logfile,
                        self.conffile))

    def testSimpleProxy(self):
        proxy_info = httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP,
                                        'localhost', self.proxyport)
        client = httplib2.Http(proxy_info=proxy_info)
        src = 'miniserver.py'
        response, body = client.request('http://localhost:%d/%s' %
                                        (self.port, src))
        self.assertEqual(response.status, 200)
        self.assertEqual(body, open(os.path.join(miniserver.HERE, src)).read())
        lf = open(self.logfile).read()
        expect = ('Established connection to host "127.0.0.1" '
                  'using file descriptor')
        self.assertTrue(expect in lf,
                        'tinyproxy did not proxy a request for miniserver')

########NEW FILE########
__FILENAME__ = miniserver
import logging
import os
import select
import SimpleHTTPServer
import SocketServer
import threading

HERE = os.path.dirname(__file__)
logger = logging.getLogger(__name__)


class ThisDirHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        return os.path.join(HERE, *filter(None, path.split('/')))

    def log_message(self, s, *args):
        # output via logging so nose can catch it
        logger.info(s, *args)


class ShutdownServer(SocketServer.TCPServer):
    """Mixin that allows serve_forever to be shut down.

    The methods in this mixin are backported from SocketServer.py in the Python
    2.6.4 standard library. The mixin is unnecessary in 2.6 and later, when
    BaseServer supports the shutdown method directly.
    """

    def __init__(self, *args, **kwargs):
        SocketServer.TCPServer.__init__(self, *args, **kwargs)
        self.__is_shut_down = threading.Event()
        self.__serving = False

    def serve_forever(self, poll_interval=0.1):
        """Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            r, w, e = select.select([self.socket], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
        self.__is_shut_down.set()

    def shutdown(self):
        """Stops the serve_forever loop.

        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will deadlock.
        """
        self.__serving = False
        self.__is_shut_down.wait()

    def handle_request(self):
        """Handle one request, possibly blocking.

        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = select.select([self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.close_request(request)


def start_server(handler):
    httpd = ShutdownServer(("", 0), handler)
    threading.Thread(target=httpd.serve_forever).start()
    _, port = httpd.socket.getsockname()
    return httpd, port

########NEW FILE########
__FILENAME__ = smoke_test
import os
import unittest

import httplib2

from httplib2.test import miniserver


class HttpSmokeTest(unittest.TestCase):
    def setUp(self):
        self.httpd, self.port = miniserver.start_server(
            miniserver.ThisDirHandler)

    def tearDown(self):
        self.httpd.shutdown()

    def testGetFile(self):
        client = httplib2.Http()
        src = 'miniserver.py'
        response, body = client.request('http://localhost:%d/%s' %
                                        (self.port, src))
        self.assertEqual(response.status, 200)
        self.assertEqual(body, open(os.path.join(miniserver.HERE, src)).read())

########NEW FILE########
__FILENAME__ = test_no_socket
"""Tests for httplib2 when the socket module is missing.

This helps ensure compatibility with environments such as AppEngine.
"""
import os
import sys
import unittest

import httplib2

class MissingSocketTest(unittest.TestCase):
    def setUp(self):
        self._oldsocks = httplib2.socks
        httplib2.socks = None

    def tearDown(self):
        httplib2.socks = self._oldsocks

    def testProxyDisabled(self):
        proxy_info = httplib2.ProxyInfo('blah',
                                        'localhost', 0)
        client = httplib2.Http(proxy_info=proxy_info)
        self.assertRaises(httplib2.ProxiesUnavailableError,
                          client.request, 'http://localhost:-1/')

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


import StringIO
import base64
import httplib
import httplib2
import os
import pickle
import socket
import sys
import time
import unittest
import urlparse

try:
    import ssl
except ImportError:
    pass

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
        self.sock = None

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

class _MyHTTPBadStatusConnection(object):
    "Mock of httplib.HTTPConnection that raises BadStatusLine."

    num_calls = 0

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=None, proxy_info=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.log = ""
        self.sock = None
        _MyHTTPBadStatusConnection.num_calls = 0

    def set_debuglevel(self, level):
        pass

    def connect(self):
        pass

    def close(self):
        pass

    def request(self, method, request_uri, body, headers):
        pass

    def getresponse(self):
        _MyHTTPBadStatusConnection.num_calls += 1
        raise httplib.BadStatusLine("")


class HttpTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(cacheDirName):
            [os.remove(os.path.join(cacheDirName, file)) for file in os.listdir(cacheDirName)]

        if sys.version_info < (2, 6):
            disable_cert_validation = True
        else:
            disable_cert_validation = False
        self.http = httplib2.Http(
                cacheDirName,
                disable_ssl_certificate_validation=disable_cert_validation)
        self.http.clear_credentials()

    def testIPv6NoSSL(self):
        try:
          self.http.request("http://[::1]/")
        except socket.gaierror:
          self.fail("should get the address family right for IPv6")
        except socket.error:
          # Even if IPv6 isn't installed on a machine it should just raise socket.error
          pass

    def testIPv6SSL(self):
        try:
          self.http.request("https://[::1]/")
        except socket.gaierror:
          self.fail("should get the address family right for IPv6")
        except httplib2.CertificateHostnameMismatch:
          # We connected and verified that the certificate doesn't match
          #  the name. Good enough.
          pass
        except socket.error:
          # Even if IPv6 isn't installed on a machine it should just raise socket.error
          pass

    def testConnectionType(self):
        self.http.force_exception_to_status_code = False
        response, content = self.http.request("http://bitworking.org", connection_type=_MyHTTPConnection)
        self.assertEqual(response['content-location'], "http://bitworking.org")
        self.assertEqual(content, "the body")

    def testBadStatusLineRetry(self):
        old_retries = httplib2.RETRIES
        httplib2.RETRIES = 1
        self.http.force_exception_to_status_code = False
        try:
            response, content = self.http.request("http://bitworking.org",
                connection_type=_MyHTTPBadStatusConnection)
        except httplib.BadStatusLine:
            self.assertEqual(2, _MyHTTPBadStatusConnection.num_calls)
        httplib2.RETRIES = old_retries

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

    def testGetConnectionRefused(self):
        self.http.force_exception_to_status_code = False
        try:
          self.http.request("http://localhost:7777/")
          self.fail("An socket.error exception must be thrown on Connection Refused.")
        except socket.error:
            pass

        # Now test with exceptions turned off
        self.http.force_exception_to_status_code = True

        (response, content) = self.http.request("http://localhost:7777/")
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertTrue("Connection refused" in content
            or "actively refused" in content,
            "Unexpected status %(content)s" % vars())
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

    def testHead301(self):
        # Test that we automatically follow 301 redirects
        uri = urlparse.urljoin(base, "301/onestep.asis")
        destination = urlparse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, False)

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

    def testGet301ViaHttps(self):
        # Google always redirects to https://www.google.com
        (response, content) = self.http.request("https://code.google.com/apis/", "GET")
        self.assertEqual(200, response.status)
        self.assertEqual(301, response.previous.status)

    def testGetViaHttps(self):
        # Test that we can handle HTTPS
        (response, content) = self.http.request("https://www.google.com/adsense/", "GET")
        self.assertEqual(200, response.status)

    def testGetViaHttpsSpecViolationOnLocation(self):
        # Test that we follow redirects through HTTPS
        # even if they violate the spec by including
        # a relative Location: header instead of an
        # absolute one.
        (response, content) = self.http.request("https://www.google.com/adsense", "GET")
        self.assertEqual(200, response.status)
        self.assertNotEqual(None, response.previous)

    def testSslCertValidation(self):
        if sys.version_info >= (2, 6):
            # Test that we get an ssl.SSLError when specifying a non-existent CA
            # certs file.
            http = httplib2.Http(ca_certs='/nosuchfile')
            self.assertRaises(ssl.SSLError,
                    http.request, "https://www.google.com/", "GET")

            # Test that we get a SSLHandshakeError if we try to access
            # https;//www.google.com, using a CA cert file that doesn't contain
            # the CA Gogole uses (i.e., simulating a cert that's not signed by a
            # trusted CA).
            other_ca_certs = os.path.join(
                    os.path.dirname(os.path.abspath(httplib2.__file__ )),
                    "test", "other_cacerts.txt")
            http = httplib2.Http(ca_certs=other_ca_certs)
            self.assertRaises(httplib2.SSLHandshakeError,
                    http.request, "https://www.google.com/", "GET")

    def testSslCertValidationDoubleDots(self):
        pass
        # No longer a valid test.
        #if sys.version_info >= (2, 6):
        # Test that we get match a double dot cert
        #try:
        #  self.http.request("https://www.appspot.com/", "GET")
        #except httplib2.CertificateHostnameMismatch:
        #  self.fail('cert with *.*.appspot.com should not raise an exception.')

    def testSslHostnameValidation(self):
      pass
        # No longer a valid test.
        #if sys.version_info >= (2, 6):
            # The SSL server at google.com:443 returns a certificate for
            # 'www.google.com', which results in a host name mismatch.
            # Note that this test only works because the ssl module and httplib2
            # do not support SNI; for requests specifying a server name of
            # 'google.com' via SNI, a matching cert would be returned.
        #    self.assertRaises(httplib2.CertificateHostnameMismatch,
        #            self.http.request, "https://google.com/", "GET")

    def testSslCertValidationWithoutSslModuleFails(self):
        if sys.version_info < (2, 6):
            http = httplib2.Http(disable_ssl_certificate_validation=False)
            self.assertRaises(httplib2.CertificateValidationUnsupported,
                    http.request, "https://www.google.com/", "GET")

    def testGetViaHttpsKeyCert(self):
        #  At this point I can only test
        #  that the key and cert files are passed in
        #  correctly to httplib. It would be nice to have
        #  a real https endpoint to test against.

        # bitworking.org presents an certificate for a non-matching host
        # (*.webfaction.com), so we need to disable cert checking for this test.
        http = httplib2.Http(timeout=2, disable_ssl_certificate_validation=True)

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

    def test303AndForwardAuthorizationHeader(self):
        # Test that all methods can be used
        uri = urlparse.urljoin(base, "303/redirect-to-header-reflector.cgi")
        headers = {'authorization': 'Bearer foo'}
        response, content = self.http.request(uri, 'GET', body=" ",
            headers=headers)
        # self.assertTrue('authorization' not in content)
        self.http.follow_all_redirects = True
        self.http.forward_authorization_headers = True
        response, content = self.http.request(uri, 'GET', body=" ",
            headers=headers)
        # Oh, how I wish Apache didn't eat the Authorization header.
        # self.assertTrue('authorization' in content)

    def testGet304(self):
        # Test that we use ETags properly to validate our cache
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
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
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH'))

        self.http.ignore_etag = True
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertEqual(response.fromcache, False)
        self.assertFalse(d.has_key('HTTP_IF_NONE_MATCH'))

    def testOverrideEtag(self):
        # Test that we can forcibly ignore ETags
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH'))
        self.assertNotEqual(d['HTTP_IF_NONE_MATCH'], "fred")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0', 'if-none-match': 'fred'})
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
        pass
        # when there is no vary, a different Accept header (e.g.) should not
        # impact if the cache is used
        # test that the vary header is not sent
        # uri = urlparse.urljoin(base, "vary/no-vary.asis")
        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        # self.assertEqual(response.status, 200)
        # self.assertFalse(response.has_key('vary'))

        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        # self.assertEqual(response.status, 200)
        # self.assertEqual(response.fromcache, True, msg="Should be from cache")
        #
        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/html'})
        # self.assertEqual(response.status, 200)
        # self.assertEqual(response.fromcache, True, msg="Should be from cache")

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

    def testVaryUnusedHeader(self):
        # A header's value is not considered to vary if it's not used at all.
        uri = urlparse.urljoin(base, "vary/unused-header.asis")
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertTrue(response.has_key('vary'))

        # we are from cache
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain',})
        self.assertEqual(response.fromcache, True, msg="Should be from cache")


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

    def testPostAndGZipResponse(self):
        uri = urlparse.urljoin(base, "gzip/post.cgi")
        (response, content) = self.http.request(uri, "POST", body=" ")
        self.assertEqual(response.status, 200)
        self.assertFalse(response.has_key('content-encoding'))
        self.assertTrue(response.has_key('-content-encoding'))

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
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'accept-encoding': 'identity', 'Cache-Control': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlPragmaNoCache(self):
        # Test Pragma: no-cache on requests
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET", headers= {'accept-encoding': 'identity'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'accept-encoding': 'identity', 'Pragma': 'no-cache'})
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

    def testUpdatePatchUsesCachedETag(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/
        uri = urlparse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "PATCH", body="foo")
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "PATCH", body="foo")
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

    def testPickleHttp(self):
        pickled_http = pickle.dumps(self.http)
        new_http = pickle.loads(pickled_http)

        self.assertEqual(sorted(new_http.__dict__.keys()),
                         sorted(self.http.__dict__.keys()))
        for key in new_http.__dict__:
            if key in ('certificates', 'credentials'):
                self.assertEqual(new_http.__dict__[key].credentials,
                                 self.http.__dict__[key].credentials)
            elif key == 'cache':
                self.assertEqual(new_http.__dict__[key].cache,
                                 self.http.__dict__[key].cache)
            else:
                self.assertEqual(new_http.__dict__[key],
                                 self.http.__dict__[key])

    def testPickleHttpWithConnection(self):
        self.http.request('http://bitworking.org',
                          connection_type=_MyHTTPConnection)
        pickled_http = pickle.dumps(self.http)
        new_http = pickle.loads(pickled_http)

        self.assertEqual(self.http.connections.keys(), ['http:bitworking.org'])
        self.assertEqual(new_http.connections, {})

    def testPickleCustomRequestHttp(self):
        def dummy_request(*args, **kwargs):
            return new_request(*args, **kwargs)
        dummy_request.dummy_attr = 'dummy_value'

        self.http.request = dummy_request
        pickled_http = pickle.dumps(self.http)
        self.assertFalse("S'request'" in pickled_http)

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

    def testParseWWWAuthenticateMalformed(self):
        try:
          res = httplib2._parse_www_authenticate({'www-authenticate':'OAuth "Facebook Platform" "invalid_token" "Invalid OAuth access token."'})
          self.fail("should raise an exception")
        except httplib2.MalformedHeader:
          pass

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
        our_request = "authorization: %s" % headers['authorization']
        working_request = 'authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46"'
        self.assertEqual(our_request, working_request)

    def testDigestObjectWithOpaque(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/'
        headers = {}
        response = {
            'www-authenticate': 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", opaque="atestopaque"'
        }
        content = ""

        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        d.request("GET", request_uri, headers, content, cnonce="33033375ec278a46")
        our_request = "authorization: %s" % headers['authorization']
        working_request = 'authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46", opaque="atestopaque"'
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


class TestProxyInfo(unittest.TestCase):
    def setUp(self):
        self.orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_from_url(self):
        pi = httplib2.proxy_info_from_url('http://myproxy.example.com')
        self.assertEquals(pi.proxy_host, 'myproxy.example.com')
        self.assertEquals(pi.proxy_port, 80)
        self.assertEquals(pi.proxy_user, None)

    def test_from_url_ident(self):
        pi = httplib2.proxy_info_from_url('http://zoidberg:fish@someproxy:99')
        self.assertEquals(pi.proxy_host, 'someproxy')
        self.assertEquals(pi.proxy_port, 99)
        self.assertEquals(pi.proxy_user, 'zoidberg')
        self.assertEquals(pi.proxy_pass, 'fish')

    def test_from_env(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:8080'
        pi = httplib2.proxy_info_from_environment()
        self.assertEquals(pi.proxy_host, 'myproxy.example.com')
        self.assertEquals(pi.proxy_port, 8080)
        self.assertEquals(pi.bypass_hosts, [])

    def test_from_env_no_proxy(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:80'
        os.environ['https_proxy'] = 'http://myproxy.example.com:81'
        os.environ['no_proxy'] = 'localhost,otherhost.domain.local'
        pi = httplib2.proxy_info_from_environment('https')
        self.assertEquals(pi.proxy_host, 'myproxy.example.com')
        self.assertEquals(pi.proxy_port, 81)
        self.assertEquals(pi.bypass_hosts, ['localhost',
            'otherhost.domain.local'])

    def test_from_env_none(self):
        os.environ.clear()
        pi = httplib2.proxy_info_from_environment()
        self.assertEquals(pi, None)

    def test_applies_to(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:80'
        os.environ['https_proxy'] = 'http://myproxy.example.com:81'
        os.environ['no_proxy'] = 'localhost,otherhost.domain.local,example.com'
        pi = httplib2.proxy_info_from_environment()
        self.assertFalse(pi.applies_to('localhost'))
        self.assertTrue(pi.applies_to('www.google.com'))
        self.assertFalse(pi.applies_to('www.example.com'))

    def test_no_proxy_star(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:80'
        os.environ['NO_PROXY'] = '*'
        pi = httplib2.proxy_info_from_environment()
        for host in ('localhost', '169.254.38.192', 'www.google.com'):
            self.assertFalse(pi.applies_to(host))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = httplib2test_appengine
"""
httplib2test_appengine

A set of unit tests for httplib2.py on Google App Engine

"""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2011, Joe Gregorio"

import os
import sys
import unittest

# The test resources base uri
base = 'http://bitworking.org/projects/httplib2/test/'
#base = 'http://localhost/projects/httplib2/test/'
cacheDirName = ".cache"
APP_ENGINE_PATH='../../google_appengine'

sys.path.insert(0, APP_ENGINE_PATH)

import dev_appserver
dev_appserver.fix_sys_path()

from google.appengine.ext import testbed
testbed = testbed.Testbed()
testbed.activate()
testbed.init_urlfetch_stub()

import google.appengine.api

import httplib2

class AppEngineHttpTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(cacheDirName):
            [os.remove(os.path.join(cacheDirName, file)) for file in os.listdir(cacheDirName)]

    def test(self):
        h = httplib2.Http()
        response, content = h.request("http://bitworking.org")
        self.assertEqual(httplib2.SCHEME_TO_CONNECTION['https'],
                         httplib2.AppEngineHttpsConnection)
        self.assertEquals(1, len(h.connections))
        self.assertEquals(response.status, 200)
        self.assertEquals(response['status'], '200')

    # It would be great to run the test below, but it really tests the
    # aberrant behavior of httplib on App Engine, but that special aberrant
    # httplib only appears when actually running on App Engine and not when
    # running via the SDK. When running via the SDK the httplib in std lib is
    # loaded, which throws a different error when a timeout occurs.
    #
    #def test_timeout(self):
    #    # The script waits 3 seconds, so a timeout of more than that should succeed.
    #    h = httplib2.Http(timeout=7)
    #    r, c = h.request('http://bitworking.org/projects/httplib2/test/timeout/timeout.cgi')
    #
    #    import httplib
    #    print httplib.__file__
    #    h = httplib2.Http(timeout=1)
    #    try:
    #      r, c = h.request('http://bitworking.org/projects/httplib2/test/timeout/timeout.cgi')
    #      self.fail('Timeout should have raised an exception.')
    #    except DeadlineExceededError:
    #      pass

    def test_proxy_info_ignored(self):
        h = httplib2.Http(proxy_info='foo.txt')
        response, content = h.request("http://bitworking.org")
        self.assertEquals(response.status, 200)


class AberrationsTest(unittest.TestCase):
    def setUp(self):
        self.orig_apiproxy_stub_map = google.appengine.api.apiproxy_stub_map

        # Force apiproxy_stub_map to None to trigger the test condition.
        google.appengine.api.apiproxy_stub_map = None
        reload(httplib2)

    def tearDown(self):
        google.appengine.api.apiproxy_stub_map = self.orig_apiproxy_stub_map
        reload(httplib2)

    def test(self):
        self.assertNotEqual(httplib2.SCHEME_TO_CONNECTION['https'],
                            httplib2.AppEngineHttpsConnection)
        self.assertNotEqual(httplib2.SCHEME_TO_CONNECTION['http'],
                            httplib2.AppEngineHttpConnection)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
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

import urllib.parse


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
    (0xA0, 0xD7FF),
    (0xE000, 0xF8FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    (0x10000, 0x1FFFD),
    (0x20000, 0x2FFFD),
    (0x30000, 0x3FFFD),
    (0x40000, 0x4FFFD),
    (0x50000, 0x5FFFD),
    (0x60000, 0x6FFFD),
    (0x70000, 0x7FFFD),
    (0x80000, 0x8FFFD),
    (0x90000, 0x9FFFD),
    (0xA0000, 0xAFFFD),
    (0xB0000, 0xBFFFD),
    (0xC0000, 0xCFFFD),
    (0xD0000, 0xDFFFD),
    (0xE1000, 0xEFFFD),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]

def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % o for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function."""
    if isinstance(uri ,str):
        (scheme, authority, path, query, fragment) = urllib.parse.urlsplit(uri)
        authority = authority.encode('idna').decode('utf-8')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8
        uri = urllib.parse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri

if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [
                "ftp://ftp.is.co.za/rfc/rfc1808.txt",
                "http://www.ietf.org/rfc/rfc2396.txt",
                "ldap://[2001:db8::7]/c=GB?objectClass?one",
                "mailto:John.Doe@example.com",
                "news:comp.infosystems.www.servers.unix",
                "tel:+1-816-555-1212",
                "telnet://192.0.2.16:80/",
                "urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))

        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri("http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri("http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri("http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri("#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri("/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri("/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri("/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()



########NEW FILE########
__FILENAME__ = httplib2test
#!/usr/bin/env python3
"""
httplib2test

A set of unit tests for httplib2.py.

Requires Python 3.0 or later
"""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = ["Mark Pilgrim"]
__license__ = "MIT"
__history__ = """ """
__version__ = "0.2 ($Rev: 118 $)"

import base64
import http.client
import httplib2
import io
import os
import pickle
import socket
import ssl
import sys
import time
import unittest
import urllib.parse

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
            self.assertEqual( "xn--http,-4y1d.org,fred,a=b,579924c35db315e5a32e3d9963388193", httplib2.safename("http://\u2304.org/fred/?a=b"))

class _MyResponse(io.BytesIO):
    def __init__(self, body, **kwargs):
        io.BytesIO.__init__(self, body)
        self.headers = kwargs

    def items(self):
        return self.headers.items()

    def iteritems(self):
        return iter(self.headers.items())


class _MyHTTPConnection(object):
    "This class is just a mock of httplib.HTTPConnection used for testing"

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=None, proxy_info=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.log = ""
        self.sock = None

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
        return _MyResponse(b"the body", status="200")


class _MyHTTPBadStatusConnection(object):
    "Mock of httplib.HTTPConnection that raises BadStatusLine."

    num_calls = 0

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=None, proxy_info=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.log = ""
        self.sock = None
        _MyHTTPBadStatusConnection.num_calls = 0

    def set_debuglevel(self, level):
        pass

    def connect(self):
        pass

    def close(self):
        pass

    def request(self, method, request_uri, body, headers):
        pass

    def getresponse(self):
        _MyHTTPBadStatusConnection.num_calls += 1
        raise http.client.BadStatusLine("")


class HttpTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(cacheDirName):
            [os.remove(os.path.join(cacheDirName, file)) for file in os.listdir(cacheDirName)]
        self.http = httplib2.Http(cacheDirName)
        self.http.clear_credentials()

    def testIPv6NoSSL(self):
        try:
          self.http.request("http://[::1]/")
        except socket.gaierror:
          self.fail("should get the address family right for IPv6")
        except socket.error:
          # Even if IPv6 isn't installed on a machine it should just raise socket.error
          pass

    def testIPv6SSL(self):
        try:
          self.http.request("https://[::1]/")
        except socket.gaierror:
          self.fail("should get the address family right for IPv6")
        except socket.error:
          # Even if IPv6 isn't installed on a machine it should just raise socket.error
          pass

    def testConnectionType(self):
        self.http.force_exception_to_status_code = False
        response, content = self.http.request("http://bitworking.org", connection_type=_MyHTTPConnection)
        self.assertEqual(response['content-location'], "http://bitworking.org")
        self.assertEqual(content, b"the body")


    def testBadStatusLineRetry(self):
        old_retries = httplib2.RETRIES
        httplib2.RETRIES = 1
        self.http.force_exception_to_status_code = False
        try:
            response, content = self.http.request("http://bitworking.org",
                connection_type=_MyHTTPBadStatusConnection)
        except http.client.BadStatusLine:
            self.assertEqual(2, _MyHTTPBadStatusConnection.num_calls)
        httplib2.RETRIES = old_retries


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
        self.assertTrue(content.startswith(b"Unable to find"))
        self.assertEqual(response.status, 400)

    def testGetConnectionRefused(self):
        self.http.force_exception_to_status_code = False
        try:
            self.http.request("http://localhost:7777/")
            self.fail("An socket.error exception must be thrown on Connection Refused.")
        except socket.error:
            pass

        # Now test with exceptions turned off
        self.http.force_exception_to_status_code = True

        (response, content) = self.http.request("http://localhost:7777/")
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertTrue(b"Connection refused" in content)
        self.assertEqual(response.status, 400)

    def testGetIRI(self):
        if sys.version_info >= (2,3):
            uri = urllib.parse.urljoin(base, "reflector/reflector.cgi?d=\N{CYRILLIC CAPITAL LETTER DJE}")
            (response, content) = self.http.request(uri, "GET")
            d = self.reflector(content)
            self.assertTrue('QUERY_STRING' in d)
            self.assertTrue(d['QUERY_STRING'].find('%D0%82') > 0)

    def testGetIsDefaultMethod(self):
        # Test that GET is the default method
        uri = urllib.parse.urljoin(base, "methods/method_reflector.cgi")
        (response, content) = self.http.request(uri)
        self.assertEqual(response['x-method'], "GET")

    def testDifferentMethods(self):
        # Test that all methods can be used
        uri = urllib.parse.urljoin(base, "methods/method_reflector.cgi")
        for method in ["GET", "PUT", "DELETE", "POST"]:
            (response, content) = self.http.request(uri, method, body=b" ")
            self.assertEqual(response['x-method'], method)

    def testHeadRead(self):
        # Test that we don't try to read the response of a HEAD request
        # since httplib blocks response.read() for HEAD requests.
        # Oddly enough this doesn't appear as a problem when doing HEAD requests
        # against Apache servers.
        uri = "http://www.google.com/"
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"")

    def testGetNoCache(self):
        # Test that can do a GET w/o the cache turned on.
        http = httplib2.Http()
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.previous, None)

    def testGetOnlyIfCachedCacheHit(self):
        # Test that can do a GET with cache and 'only-if-cached'
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, True)
        self.assertEqual(response.status, 200)

    def testGetOnlyIfCachedCacheMiss(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 504)

    def testGetOnlyIfCachedNoCacheAtAll(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        # Of course, there might be an intermediary beyond us
        # that responds to the 'only-if-cached', so this
        # test can't really be guaranteed to pass.
        http = httplib2.Http()
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 504)

    def testUserAgent(self):
        # Test that we provide a default user-agent
        uri = urllib.parse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith(b"Python-httplib2/"))

    def testUserAgentNonDefault(self):
        # Test that the default user-agent can be over-ridden

        uri = urllib.parse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET", headers={'User-Agent': 'fred/1.0'})
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith(b"fred/1.0"))

    def testGet300WithLocation(self):
        # Test the we automatically follow 300 redirects if a Location: header is provided
        uri = urllib.parse.urljoin(base, "300/with-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

        # Confirm that the intermediate 300 is not cached
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

    def testGet300WithLocationNoRedirect(self):
        # Test the we automatically follow 300 redirects if a Location: header is provided
        self.http.follow_redirects = False
        uri = urllib.parse.urljoin(base, "300/with-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 300)

    def testGet300WithoutLocation(self):
        # Not giving a Location: header in a 300 response is acceptable
        # In which case we just return the 300 response
        uri = urllib.parse.urljoin(base, "300/without-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 300)
        self.assertTrue(response['content-type'].startswith("text/html"))
        self.assertEqual(response.previous, None)

    def testGet301(self):
        # Test that we automatically follow 301 redirects
        # and that we cache the 301 response
        uri = urllib.parse.urljoin(base, "301/onestep.asis")
        destination = urllib.parse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertTrue('content-location' in response)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, True)

    def testHead301(self):
        # Test that we automatically follow 301 redirects
        uri = urllib.parse.urljoin(base, "301/onestep.asis")
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, False)

    def testGet301NoRedirect(self):
        # Test that we automatically follow 301 redirects
        # and that we cache the 301 response
        self.http.follow_redirects = False
        uri = urllib.parse.urljoin(base, "301/onestep.asis")
        destination = urllib.parse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 301)


    def testGet302(self):
        # Test that we automatically follow 302 redirects
        # and that we DO NOT cache the 302 response
        uri = urllib.parse.urljoin(base, "302/onestep.asis")
        destination = urllib.parse.urljoin(base, "302/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

        uri = urllib.parse.urljoin(base, "302/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(response['content-location'], destination)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)
        self.assertEqual(response.previous['content-location'], uri)

        uri = urllib.parse.urljoin(base, "302/twostep.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

    def testGet302RedirectionLimit(self):
        # Test that we can set a lower redirection limit
        # and that we raise an exception when we exceed
        # that limit.
        self.http.force_exception_to_status_code = False

        uri = urllib.parse.urljoin(base, "302/twostep.asis")
        try:
            (response, content) = self.http.request(uri, "GET", redirections = 1)
            self.fail("This should not happen")
        except httplib2.RedirectLimit:
            pass
        except Exception as e:
            self.fail("Threw wrong kind of exception ")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True

        (response, content) = self.http.request(uri, "GET", redirections = 1)
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Redirected more"))
        self.assertEqual("302", response['status'])
        self.assertTrue(content.startswith(b"<html>"))
        self.assertTrue(response.previous != None)

    def testGet302NoLocation(self):
        # Test that we throw an exception when we get
        # a 302 with no Location: header.
        self.http.force_exception_to_status_code = False
        uri = urllib.parse.urljoin(base, "302/no-location.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.RedirectMissingLocation:
            pass
        except Exception as e:
            self.fail("Threw wrong kind of exception ")

        # Re-run the test with out the exceptions
        self.http.force_exception_to_status_code = True

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 500)
        self.assertTrue(response.reason.startswith("Redirected but"))
        self.assertEqual("302", response['status'])
        self.assertTrue(content.startswith(b"This is content"))

    def testGet301ViaHttps(self):
        # Google always redirects to http://google.com
        (response, content) = self.http.request("https://code.google.com/apis/", "GET")
        self.assertEqual(200, response.status)
        self.assertEqual(301, response.previous.status)

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
        except AttributeError:
          self.assertEqual(http.connections["https:bitworking.org"].key_file, "akeyfile")
          self.assertEqual(http.connections["https:bitworking.org"].cert_file, "acertfile")
        except IOError:
          # Skip on 3.2
          pass

        try:
            (response, content) = http.request("https://notthere.bitworking.org", "GET")
        except httplib2.ServerNotFoundError:
          self.assertEqual(http.connections["https:notthere.bitworking.org"].key_file, None)
          self.assertEqual(http.connections["https:notthere.bitworking.org"].cert_file, None)
        except IOError:
          # Skip on 3.2
          pass

    def testSslCertValidation(self):
          # Test that we get an ssl.SSLError when specifying a non-existent CA
          # certs file.
          http = httplib2.Http(ca_certs='/nosuchfile')
          self.assertRaises(IOError,
                  http.request, "https://www.google.com/", "GET")

          # Test that we get a SSLHandshakeError if we try to access
          # https://www.google.com, using a CA cert file that doesn't contain
          # the CA Google uses (i.e., simulating a cert that's not signed by a
          # trusted CA).
          other_ca_certs = os.path.join(
                  os.path.dirname(os.path.abspath(httplib2.__file__ )),
                  "test", "other_cacerts.txt")
          http = httplib2.Http(ca_certs=other_ca_certs)
          self.assertRaises(ssl.SSLError,
            http.request,"https://www.google.com/", "GET")

    def testSniHostnameValidation(self):
        self.http.request("https://google.com/", method="GET")

    def testGet303(self):
        # Do a follow-up GET on a Location: header
        # returned from a POST that gave a 303.
        uri = urllib.parse.urljoin(base, "303/303.cgi")
        (response, content) = self.http.request(uri, "POST", " ")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 303)

    def testGet303NoRedirect(self):
        # Do a follow-up GET on a Location: header
        # returned from a POST that gave a 303.
        self.http.follow_redirects = False
        uri = urllib.parse.urljoin(base, "303/303.cgi")
        (response, content) = self.http.request(uri, "POST", " ")
        self.assertEqual(response.status, 303)

    def test303ForDifferentMethods(self):
        # Test that all methods can be used
        uri = urllib.parse.urljoin(base, "303/redirect-to-reflector.cgi")
        for (method, method_on_303) in [("PUT", "GET"), ("DELETE", "GET"), ("POST", "GET"), ("GET", "GET"), ("HEAD", "GET")]:
            (response, content) = self.http.request(uri, method, body=b" ")
            self.assertEqual(response['x-method'], method_on_303)

    def testGet304(self):
        # Test that we use ETags properly to validate our cache
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'must-revalidate'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        cache_file_name = os.path.join(cacheDirName, httplib2.safename(httplib2.urlnorm(uri)[-1]))
        f = open(cache_file_name, "r")
        status_line = f.readline()
        f.close()

        self.assertTrue(status_line.startswith("status:"))

        (response, content) = self.http.request(uri, "HEAD", headers = {'accept-encoding': 'identity'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'range': 'bytes=0-0'})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.fromcache, False)

    def testGetIgnoreEtag(self):
        # Test that we can forcibly ignore ETags
        uri = urllib.parse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue('HTTP_IF_NONE_MATCH' in d)

        self.http.ignore_etag = True
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertEqual(response.fromcache, False)
        self.assertFalse('HTTP_IF_NONE_MATCH' in d)

    def testOverrideEtag(self):
        # Test that we can forcibly ignore ETags
        uri = urllib.parse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue('HTTP_IF_NONE_MATCH' in d)
        self.assertNotEqual(d['HTTP_IF_NONE_MATCH'], "fred")

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'cache-control': 'max-age=0', 'if-none-match': 'fred'})
        d = self.reflector(content)
        self.assertTrue('HTTP_IF_NONE_MATCH' in d)
        self.assertEqual(d['HTTP_IF_NONE_MATCH'], "fred")

#MAP-commented this out because it consistently fails
#    def testGet304EndToEnd(self):
#       # Test that end to end headers get overwritten in the cache
#        uri = urllib.parse.urljoin(base, "304/end2end.cgi")
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
        uri = urllib.parse.urljoin(base, "304/last-modified-only/last-modified-only.txt")
        (response, content) = self.http.request(uri, "GET")

        self.assertNotEqual(response['last-modified'], "")
        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

    def testGet307(self):
        # Test that we do follow 307 redirects but
        # do not cache the 307
        uri = urllib.parse.urljoin(base, "307/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, b"This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

    def testGet410(self):
        # Test that we pass 410's through
        uri = urllib.parse.urljoin(base, "410/410.asis")
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
        uri = urllib.parse.urljoin(base, "vary/accept.asis")
        (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertTrue('vary' in response)

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
        pass
        # when there is no vary, a different Accept header (e.g.) should not
        # impact if the cache is used
        # test that the vary header is not sent
        # uri = urllib.parse.urljoin(base, "vary/no-vary.asis")
        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        # self.assertEqual(response.status, 200)
        # self.assertFalse('vary' in response)
        #
        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/plain'})
        # self.assertEqual(response.status, 200)
        # self.assertEqual(response.fromcache, True, msg="Should be from cache")
        #
        # (response, content) = self.http.request(uri, "GET", headers={'Accept': 'text/html'})
        # self.assertEqual(response.status, 200)
        # self.assertEqual(response.fromcache, True, msg="Should be from cache")

    def testVaryHeaderDouble(self):
        uri = urllib.parse.urljoin(base, "vary/accept-double.asis")
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain', 'Accept-Language': 'da, en-gb;q=0.8, en;q=0.7'})
        self.assertEqual(response.status, 200)
        self.assertTrue('vary' in response)

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

    def testVaryUnusedHeader(self):
        # A header's value is not considered to vary if it's not used at all.
        uri = urllib.parse.urljoin(base, "vary/unused-header.asis")
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain'})
        self.assertEqual(response.status, 200)
        self.assertTrue('vary' in response)

        # we are from cache
        (response, content) = self.http.request(uri, "GET", headers={
            'Accept': 'text/plain',})
        self.assertEqual(response.fromcache, True, msg="Should be from cache")

    def testHeadGZip(self):
        # Test that we don't try to decompress a HEAD response
        uri = urllib.parse.urljoin(base, "gzip/final-destination.txt")
        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertNotEqual(int(response['content-length']), 0)
        self.assertEqual(content, b"")

    def testGetGZip(self):
        # Test that we support gzip compression
        uri = urllib.parse.urljoin(base, "gzip/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertFalse('content-encoding' in response)
        self.assertTrue('-content-encoding' in response)
        self.assertEqual(int(response['content-length']), len(b"This is the final destination.\n"))
        self.assertEqual(content, b"This is the final destination.\n")

    def testPostAndGZipResponse(self):
        uri = urllib.parse.urljoin(base, "gzip/post.cgi")
        (response, content) = self.http.request(uri, "POST", body=" ")
        self.assertEqual(response.status, 200)
        self.assertFalse('content-encoding' in response)
        self.assertTrue('-content-encoding' in response)

    def testGetGZipFailure(self):
        # Test that we raise a good exception when the gzip fails
        self.http.force_exception_to_status_code = False
        uri = urllib.parse.urljoin(base, "gzip/failed-compression.asis")
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

    def testIndividualTimeout(self):
        uri = urllib.parse.urljoin(base, "timeout/timeout.cgi")
        http = httplib2.Http(timeout=1)
        http.force_exception_to_status_code = True

        (response, content) = http.request(uri)
        self.assertEqual(response.status, 408)
        self.assertTrue(response.reason.startswith("Request Timeout"))
        self.assertTrue(content.startswith(b"Request Timeout"))


    def testGetDeflate(self):
        # Test that we support deflate compression
        uri = urllib.parse.urljoin(base, "deflate/deflated.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertFalse('content-encoding' in response)
        self.assertEqual(int(response['content-length']), len("This is the final destination."))
        self.assertEqual(content, b"This is the final destination.")

    def testGetDeflateFailure(self):
        # Test that we raise a good exception when the deflate fails
        self.http.force_exception_to_status_code = False

        uri = urllib.parse.urljoin(base, "deflate/failed-compression.asis")
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
        uri = urllib.parse.urljoin(base, "duplicate-headers/multilink.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, b"This is content\n")
        self.assertEqual(response['link'].split(",")[0], '<http://bitworking.org>; rel="home"; title="BitWorking"')

    def testGetCacheControlNoCache(self):
        # Test Cache-Control: no-cache on requests
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'Cache-Control': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlPragmaNoCache(self):
        # Test Pragma: no-cache on requests
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers = {'accept-encoding': 'identity', 'Pragma': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreRequest(self):
        # A no-store request means that the response should not be stored.
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreResponse(self):
        # A no-store response means that the response should not be stored.
        uri = urllib.parse.urljoin(base, "no-store/no-store.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoCacheNoStoreRequest(self):
        # Test that a no-store, no-cache clears the entry from the cache
        # even if it was cached previously.
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")

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
        uri = urllib.parse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "DELETE")
        self.assertEqual(response.status, 405)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, False)

    def testUpdateUsesCachedETag(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/
        uri = urllib.parse.urljoin(base, "conditional-updates/test.cgi")

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


    def testUpdatePatchUsesCachedETag(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/
        uri = urllib.parse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "PATCH", body="foo")
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "PATCH", body="foo")
        self.assertEqual(response.status, 412)

    def testUpdateUsesCachedETagAndOCMethod(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/
        uri = urllib.parse.urljoin(base, "conditional-updates/test.cgi")

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
        uri = urllib.parse.urljoin(base, "conditional-updates/test.cgi")

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
        uri = urllib.parse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urllib.parse.urljoin(base, "basic/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthWithDomain(self):
        # Test Basic Authentication
        uri = urllib.parse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urllib.parse.urljoin(base, "basic/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password', "example.org")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urllib.parse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        domain = urllib.parse.urlparse(base)[1]
        self.http.add_credentials('joe', 'password', domain)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)






    def testBasicAuthTwoDifferentCredentials(self):
        # Test Basic Authentication with multiple sets of credentials
        uri = urllib.parse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urllib.parse.urljoin(base, "basic2/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthNested(self):
        # Test Basic Authentication with resources
        # that are nested
        uri = urllib.parse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urllib.parse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        # Now add in credentials one at a time and test.
        self.http.add_credentials('joe', 'password')

        uri = urllib.parse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')

        uri = urllib.parse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testDigestAuth(self):
        # Test that we support Digest Authentication
        uri = urllib.parse.urljoin(base, "digest/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urllib.parse.urljoin(base, "digest/file.txt")
        (response, content) = self.http.request(uri, "GET")

    def testDigestAuthNextNonceAndNC(self):
        # Test that if the server sets nextnonce that we reset
        # the nonce count back to 1
        uri = urllib.parse.urljoin(base, "digest/file.txt")
        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info2 = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

        if 'nextnonce' in info:
            self.assertEqual(info2['nc'], 1)

    def testDigestAuthStale(self):
        # Test that we can handle a nonce becoming stale
        uri = urllib.parse.urljoin(base, "digest-expire/file.txt")
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
        return  dict( [tuple(x.split("=", 1)) for x in content.decode('utf-8').strip().split("\n")] )

    def testReflector(self):
        uri = urllib.parse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        d = self.reflector(content)
        self.assertTrue('HTTP_USER_AGENT' in d)


    def testConnectionClose(self):
        uri = "http://www.google.com/"
        (response, content) = self.http.request(uri, "GET")
        for c in self.http.connections.values():
            self.assertNotEqual(None, c.sock)
        (response, content) = self.http.request(uri, "GET", headers={"connection": "close"})
        for c in self.http.connections.values():
            self.assertEqual(None, c.sock)

    def testPickleHttp(self):
        pickled_http = pickle.dumps(self.http)
        new_http = pickle.loads(pickled_http)

        self.assertEqual(sorted(new_http.__dict__.keys()),
                         sorted(self.http.__dict__.keys()))
        for key in new_http.__dict__:
            if key in ('certificates', 'credentials'):
                self.assertEqual(new_http.__dict__[key].credentials,
                                 self.http.__dict__[key].credentials)
            elif key == 'cache':
                self.assertEqual(new_http.__dict__[key].cache,
                                 self.http.__dict__[key].cache)
            else:
                self.assertEqual(new_http.__dict__[key],
                                 self.http.__dict__[key])

    def testPickleHttpWithConnection(self):
        self.http.request('http://bitworking.org',
                          connection_type=_MyHTTPConnection)
        pickled_http = pickle.dumps(self.http)
        new_http = pickle.loads(pickled_http)

        self.assertEqual(list(self.http.connections.keys()),
                         ['http:bitworking.org'])
        self.assertEqual(new_http.connections, {})

    def testPickleCustomRequestHttp(self):
        def dummy_request(*args, **kwargs):
            return new_request(*args, **kwargs)
        dummy_request.dummy_attr = 'dummy_value'

        self.http.request = dummy_request
        pickled_http = pickle.dumps(self.http)
        self.assertFalse(b"S'request'" in pickled_http)

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
        self.assertTrue('cache-control' in h)
        self.assertTrue('other' in h)
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
        self.assertEqual(len(list(res.keys())), 0)

    def testParseWWWAuthenticate(self):
        # different uses of spaces around commas
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="test realm" , foo=foo ,bar="bar", baz=baz,qux=qux'})
        self.assertEqual(len(list(res.keys())), 1)
        self.assertEqual(len(list(res['test'].keys())), 5)

        # tokens with non-alphanum
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'T*!%#st realm=to*!%#en, to*!%#en="quoted string"'})
        self.assertEqual(len(list(res.keys())), 1)
        self.assertEqual(len(list(res['t*!%#st'].keys())), 2)

        # quoted string with quoted pairs
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="a \\"test\\" realm"'})
        self.assertEqual(len(list(res.keys())), 1)
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

    def testParseWWWAuthenticateMalformed(self):
        try:
          res = httplib2._parse_www_authenticate({'www-authenticate':'OAuth "Facebook Platform" "invalid_token" "Invalid OAuth access token."'})
          self.fail("should raise an exception")
        except httplib2.MalformedHeader:
          pass

    def testDigestObject(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/'
        headers = {}
        response = {
            'www-authenticate': 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth"'
        }
        content = b""

        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        d.request("GET", request_uri, headers, content, cnonce="33033375ec278a46")
        our_request = "authorization: %s" % headers['authorization']
        working_request = 'authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46"'
        self.assertEqual(our_request, working_request)

    def testDigestObjectWithOpaque(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/'
        headers = {}
        response = {
            'www-authenticate': 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", opaque="atestopaque"'
        }
        content = ""

        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        d.request("GET", request_uri, headers, content, cnonce="33033375ec278a46")
        our_request = "authorization: %s" % headers['authorization']
        working_request = 'authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46", opaque="atestopaque"'
        self.assertEqual(our_request, working_request)

    def testDigestObjectStale(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/'
        headers = {}
        response = httplib2.Response({ })
        response['www-authenticate'] = 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'
        response.status = 401
        content = b""
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
        content = b""
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        # Returns true to force a retry
        self.assertFalse( d.response(response, content) )
        self.assertEqual('fred', d.challenge['nonce'])
        self.assertEqual(1, d.challenge['nc'])

    def testWsseAlgorithm(self):
        digest = httplib2._wsse_username_token("d36e316282959a9ed4c89851497a717f", "2003-12-15T14:43:07Z", "taadtaadpstcsm")
        expected = b"quR/EWLAV4xLf9Zqyw4pDmfV9OY="
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
        self.assertEqual(0, len(end2end))

        # Degenerate case of connection referrring to a header not passed in
        response = {'connection': 'content-type'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertEqual(0, len(end2end))


class TestProxyInfo(unittest.TestCase):
    def setUp(self):
        self.orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_from_url(self):
        pi = httplib2.proxy_info_from_url('http://myproxy.example.com')
        self.assertEqual(pi.proxy_host, 'myproxy.example.com')
        self.assertEqual(pi.proxy_port, 80)
        self.assertEqual(pi.proxy_user, None)

    def test_from_url_ident(self):
        pi = httplib2.proxy_info_from_url('http://zoidberg:fish@someproxy:99')
        self.assertEqual(pi.proxy_host, 'someproxy')
        self.assertEqual(pi.proxy_port, 99)
        self.assertEqual(pi.proxy_user, 'zoidberg')
        self.assertEqual(pi.proxy_pass, 'fish')

    def test_from_env(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:8080'
        pi = httplib2.proxy_info_from_environment()
        self.assertEqual(pi.proxy_host, 'myproxy.example.com')
        self.assertEqual(pi.proxy_port, 8080)

    def test_from_env_no_proxy(self):
        os.environ['http_proxy'] = 'http://myproxy.example.com:80'
        os.environ['https_proxy'] = 'http://myproxy.example.com:81'
        pi = httplib2.proxy_info_from_environment('https')
        self.assertEqual(pi.proxy_host, 'myproxy.example.com')
        self.assertEqual(pi.proxy_port, 81)

    def test_from_env_none(self):
        os.environ.clear()
        pi = httplib2.proxy_info_from_environment()
        self.assertEqual(pi, None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
