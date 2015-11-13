__FILENAME__ = connections
#/usr/bin/env python
#
# Connection objects
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>

# $Id: connections.py 191145 2010-03-01 10:21:24Z msuchy $


import sys
import string
import SSL
import nonblocking

import httplib
import xmlrpclib

# Import into the local namespace some httplib-related names
_CS_REQ_SENT = httplib._CS_REQ_SENT
_CS_IDLE = httplib._CS_IDLE
ResponseNotReady = httplib.ResponseNotReady

class HTTPResponse(httplib.HTTPResponse):
    def set_callback(self, rs, ws, ex, user_data, callback):
        if not isinstance(self.fp, nonblocking.NonBlockingFile):
            self.fp = nonblocking.NonBlockingFile(self.fp)
        self.fp.set_callback(rs, ws, ex, user_data, callback)

    # Fix a bug in the upstream read() method - partial reads will incorrectly
    # update self.length with the intended, not the real, amount of bytes
    # See http://python.org/sf/988120
    def read(self, amt=None):
        if self.fp is None:
            return ''

        if self.chunked:
            return self._read_chunked(amt)

        if amt is None:
            # unbounded read
            if self.will_close:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)

        if self.length is not None:
            # Update the length with the amount of bytes we actually read
            self.length = self.length - len(s)

        return s


class HTTPConnection(httplib.HTTPConnection):
    response_class = HTTPResponse
    
    def __init__(self, host, port=None):
        httplib.HTTPConnection.__init__(self, host, port)
        self._cb_rs = []
        self._cb_ws = []
        self._cb_ex = []
        self._cb_user_data = None
        self._cb_callback = None
        self._user_agent = "rhn.connections $Revision: 191145 $ (python)"

    def set_callback(self, rs, ws, ex, user_data, callback):
        # XXX check the params
        self._cb_rs = rs
        self._cb_ws = ws
        self._cb_ex = ex
        self._cb_user_data = user_data
        self._cb_callback = callback

    def set_user_agent(self, user_agent):
        self._user_agent = user_agent

    # XXX Had to copy the function from httplib.py, because the nonblocking
    # framework had to be initialized
    def getresponse(self):
        "Get the response from the server."

        # check if a prior response has been completed
        if self.__response and self.__response.isclosed():
            self.__response = None

        #
        # if a prior response exists, then it must be completed (otherwise, we
        # cannot read this response's header to determine the connection-close
        # behavior)
        #
        # note: if a prior response existed, but was connection-close, then the
        # socket and response were made independent of this HTTPConnection
        # object since a new request requires that we open a whole new
        # connection
        #
        # this means the prior response had one of two states:
        #   1) will_close: this connection was reset and the prior socket and
        #                  response operate independently
        #   2) persistent: the response was retained and we await its
        #                  isclosed() status to become true.
        #
        if self.__state != _CS_REQ_SENT or self.__response:
            raise ResponseNotReady()

        if self.debuglevel > 0:
            response = self.response_class(self.sock, self.debuglevel)
        else:
            response = self.response_class(self.sock)
        
        # The only modification compared to the stock HTTPConnection
        if self._cb_callback:
            response.set_callback(self._cb_rs, self._cb_ws, self._cb_ex,
                self._cb_user_data, self._cb_callback)

        response.begin()
        assert response.will_close != httplib._UNKNOWN
        self.__state = _CS_IDLE

        if response.will_close:
            # this effectively passes the connection to the response
            self.close()
        else:
            # remember this, so we can tell when it is complete
            self.__response = response

        return response


class HTTPProxyConnection(HTTPConnection):
    def __init__(self, proxy, host, port=None, username=None, password=None):
        # The connection goes through the proxy
        HTTPConnection.__init__(self, proxy)
        # save the proxy values
        self.__proxy, self.__proxy_port = self.host, self.port
        # self.host and self.port will point to the real host
        self._set_hostport(host, port)
        # save the host and port
        self._host, self._port = self.host, self.port
        # Authenticated proxies support
        self.__username = username
        self.__password = password

    def connect(self):
        # We are actually connecting to the proxy
        self._set_hostport(self.__proxy, self.__proxy_port)
        HTTPConnection.connect(self)
        # Restore the real host and port
        self._set_hostport(self._host, self._port)

    def putrequest(self, method, url, skip_host=0):
        # The URL has to include the real host
        hostname = self._host
        if self._port != self.default_port:
            hostname = hostname + ':' + str(self._port)
        newurl = "http://%s%s" % (hostname, url)
        # Piggyback on the parent class
        HTTPConnection.putrequest(self, method, newurl, skip_host=skip_host)
        # Add proxy-specific headers
        self._add_proxy_headers()
        
    def _add_proxy_headers(self):
        if not self.__username:
            return
        # Authenticated proxy
        import base64
        userpass = "%s:%s" % (self.__username, self.__password)
        enc_userpass = string.replace(base64.encodestring(userpass), "\n", "")
        self.putheader("Proxy-Authorization", "Basic %s" % enc_userpass)
        
class HTTPSConnection(HTTPConnection):
    response_class = HTTPResponse
    default_port = httplib.HTTPSConnection.default_port

    def __init__(self, host, port=None, trusted_certs=None):
        HTTPConnection.__init__(self, host, port)
        trusted_certs = trusted_certs or []
        self.trusted_certs = trusted_certs

    def connect(self):
        "Connect to a host on a given (SSL) port"
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.sock = SSL.SSLSocket(sock, self.trusted_certs)
        self.sock.init_ssl()

class HTTPSProxyResponse(HTTPResponse):
    def begin(self):
        HTTPResponse.begin(self)
        self.will_close = 0

class HTTPSProxyConnection(HTTPProxyConnection):
    default_port = HTTPSConnection.default_port

    def __init__(self, proxy, host, port=None, username=None, password=None, 
            trusted_certs=None):
        HTTPProxyConnection.__init__(self, proxy, host, port, username, password)
        trusted_certs = trusted_certs or []
        self.trusted_certs = trusted_certs

    def connect(self):
        # Set the connection with the proxy
        HTTPProxyConnection.connect(self)
        # Use the stock HTTPConnection putrequest 
        host = "%s:%s" % (self._host, self._port)
        HTTPConnection.putrequest(self, "CONNECT", host)
        # Add proxy-specific stuff
        self._add_proxy_headers()
        # And send the request
        HTTPConnection.endheaders(self)
        # Save the response class
        response_class = self.response_class
        # And replace the response class with our own one, which does not
        # close the connection after 
        self.response_class = HTTPSProxyResponse
        response = HTTPConnection.getresponse(self)
        # Restore the response class
        self.response_class = response_class
        # Close the response object manually
        response.close()
        if response.status != 200:
            # Close the connection manually
            self.close()
            raise xmlrpclib.ProtocolError(host,
                response.status, response.reason, response.msg)
        self.sock = SSL.SSLSocket(self.sock, self.trusted_certs)
        self.sock.init_ssl()

    def putrequest(self, method, url, skip_host=0):
        return HTTPConnection.putrequest(self, method, url, skip_host=skip_host)

    def _add_proxy_headers(self):
        HTTPProxyConnection._add_proxy_headers(self)
        # Add a User-Agent header
        self.putheader("User-Agent", self._user_agent)

########NEW FILE########
__FILENAME__ = nonblocking
#!/usr/bin/env python
#
#
#
# $Id: nonblocking.py 191145 2010-03-01 10:21:24Z msuchy $

import select
import fcntl

# Testing which version of python we run
import sys
if hasattr(sys, "version_info"):
    # python 2.2 or newer; FCNTL is deprecated
    FCNTL = fcntl
else:
    # Older version, with valid FCNTL
    import FCNTL

class NonBlockingFile:
    def __init__(self, fd):
        # Keep a copy of the file descriptor
        self.fd = fd
        fcntl.fcntl(self.fd.fileno(), FCNTL.F_SETFL, FCNTL.O_NDELAY | FCNTL.FNDELAY)
        # Set the callback-related stuff
        self.read_fd_set = []
        self.write_fd_set = []
        self.exc_fd_set = []
        self.user_data = None
        self.callback = None

    def set_callback(self, read_fd_set, write_fd_set, exc_fd_set, 
            user_data, callback):
        self.read_fd_set = read_fd_set
        # Make the objects non-blocking
        for f in self.read_fd_set:
            fcntl.fcntl(f.fileno(), FCNTL.F_SETFL, FCNTL.O_NDELAY | FCNTL.FNDELAY)
            
        self.write_fd_set = write_fd_set
        self.exc_fd_set = exc_fd_set
        self.user_data = user_data
        self.callback = callback

    def read(self, amt=0):
        while 1:
            status_changed = 0
            readfds = self.read_fd_set + [self.fd]
            writefds = self.write_fd_set
            excfds = self.exc_fd_set
            print "Calling select", readfds
            readfds, writefds, excfds = select.select(readfds, writefds, excfds)
            print "Select returned", readfds, writefds, excfds
            if self.fd in readfds:
                # Our own file descriptor has changed status
                # Mark this, but also try to call the callback with the rest
                # of the file descriptors that changed status
                status_changed = 1
                readfds.remove(self.fd)
            if self.callback and (readfds or writefds or excfds):
                self.callback(readfds, writefds, excfds, self.user_data)
            if status_changed:
                break
        print "Returning"
        return self.fd.read(amt)

    def write(self, data):
        return self.fd.write(data)

    def __getattr__(self, name):
        return getattr(self.fd, name)

def callback(r, w, e, user_data):
    print "Callback called", r, w, e
    print r[0].read()

if __name__ == '__main__':
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("localhost", 5555))
    f = s.makefile()
    ss = NonBlockingFile(f)

    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.connect(("localhost", 5556))
    f = s2.makefile()
    ss.set_callback([f], [], [], None, callback)

    xx = ss.read()
    print len(xx)

########NEW FILE########
__FILENAME__ = rhnLockfile
#
# Copyright (c) 2008--2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import sys
import fcntl
from errno import EWOULDBLOCK, EEXIST
import fcntl

class LockfileLockedException(Exception):
    """thrown ONLY when pid file is locked."""
    pass

class Lockfile:

    """class that provides simple access to a PID-style lockfile.

    methods: __init__(lockfile), acquire(), and release()
    NOTE: currently acquires upon init
    The *.pid file will be acquired, or an LockfileLockedException is raised.
    """

    def __init__(self, lockfile, pid=None):
        """create (if need be), and acquire lock on lockfile

        lockfile example: '/var/run/up2date.pid'
        """

        # cleanup the path and assign it.
        self.lockfile = os.path.abspath(
                          os.path.expanduser(
                            os.path.expandvars(lockfile)))

        self.pid = pid
        if not self.pid:
            self.pid = os.getpid()

        # create the directory structure
        dirname = os.path.dirname(self.lockfile)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError, e:
                if hasattr(e, 'errno') and e.errno == EEXIST:
                    # race condition... dirname exists now.
                    pass
                else:
                    raise

        # open the file -- non-destructive read-write, unless it needs
        # to be created XXX: potential race condition upon create?
        self.f = os.open(self.lockfile, os.O_RDWR|os.O_CREAT|os.O_SYNC)
        self.acquire()

    def acquire(self):
        """acquire the lock; else raise LockfileLockedException."""

        try:
            fcntl.flock(self.f, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except IOError, e:
            if e.errno == EWOULDBLOCK:
                raise LockfileLockedException(
                  "cannot acquire lock on %s." % self.lockfile)
            else:
                raise
        # unlock upon exit
        fcntl.fcntl(self.f, fcntl.F_SETFD, 1)
        # truncate and write the pid
        os.ftruncate(self.f, 0)
        os.write(self.f, str(self.pid) + '\n')

    def release(self):
        # Remove the lock file
        os.unlink(self.lockfile)
        fcntl.flock(self.f, fcntl.LOCK_UN)
        os.close(self.f)


def main():
    """test code"""

    try:
        L = Lockfile('./test.pid')
    except LockfileLockedException, e:
        sys.stderr.write("%s\n" % e)
        sys.exit(-1)
    else:
        print "lock acquired "
        print "...sleeping for 10 seconds"
        import time
        time.sleep(10)
        L.release()
        print "lock released "

if __name__ == '__main__':
    # test code
    sys.exit(main() or 0)


########NEW FILE########
__FILENAME__ = rpclib
#/usr/bin/env python
#
# This module contains all the RPC-related functions the RHN code uses
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>

# $Id: rpclib.py 198366 2010-11-24 12:51:35Z msuchy $

__version__ = "$Revision: 198366 $"

import string
import transports
import urllib
import re
from types import ListType, TupleType, StringType, UnicodeType, DictType, DictionaryType

from UserDictCase import UserDictCase

# We may have an internalized version of xmlrpclib, we determine that in
# transports
xmlrpclib = transports.xmlrpclib
File = transports.File

# Wrappers around xmlrpclib objects
Fault = xmlrpclib.Fault

# XXX Do we want to do it this way, or are we going to use __init__ for this?
ResponseError = xmlrpclib.ResponseError
ProtocolError = xmlrpclib.ProtocolError

getparser = xmlrpclib.getparser

# Redirection handling

MAX_REDIRECTIONS = 5

# save the original handler in case of redirect
send_handler = None

#
# Function used to split host information in an URL per RFC 2396
# handle full hostname like user:passwd@host:port
#
# TODO: check IPv6 numerical IPs it may break
#
def split_host(hoststring):
    l = string.split(hoststring, '@', 1)
    host = None
    port = None
    user = None
    passwd = None

    if len(l) == 2:
        hostport = l[1]
        # userinfo present
        userinfo = string.split(l[0], ':', 1)
        user = userinfo[0]
        if len(userinfo) == 2:
            passwd = userinfo[1]
    else:
        hostport = l[0]

    # Now parse hostport
    arr = string.split(hostport, ':', 1)
    host = arr[0]
    if len(arr) == 2:
        port = arr[1]
        
    return (host, port, user, passwd)

def get_proxy_info(proxy):
    if proxy == None:
        raise ValueError, "Host string cannot be null"

    arr = string.split(proxy, '://', 1)
    if len(arr) == 2:
        # scheme found, strip it
        proxy = arr[1]
    
    return split_host(proxy)
        
# This is a cut-and-paste of xmlrpclib.ServerProxy, with the data members made
# protected instead of private
# It also adds support for changing the way the request is made (XMLRPC or
# GET)
class Server:
    """uri [,options] -> a logical connection to an XML-RPC server

    uri is the connection point on the server, given as
    scheme://host/target.

    The standard implementation always supports the "http" scheme.  If
    SSL socket support is available (Python 2.0), it also supports
    "https".

    If the target part and the slash preceding it are both omitted,
    "/RPC2" is assumed.

    The following options can be given as keyword arguments:

        transport: a transport factory
        encoding: the request encoding (default is UTF-8)
        verbose: verbosity level
        proxy: use an HTTP proxy
        username: username for authenticated HTTP proxy
        password: password for authenticated HTTP proxy

    All 8-bit strings passed to the server proxy are assumed to use
    the given encoding.
    """

    # Default factories
    _transport_class = transports.Transport
    _transport_class_https = transports.SafeTransport
    _transport_class_proxy = transports.ProxyTransport
    _transport_class_https_proxy = transports.SafeProxyTransport
    def __init__(self, uri, transport=None, encoding=None, verbose=0, 
        proxy=None, username=None, password=None, refreshCallback=None,
        progressCallback=None):
        # establish a "logical" server connection

        #
        # First parse the proxy information if available
        #
        if proxy != None:
            (ph, pp, pu, pw) = get_proxy_info(proxy)

            if pp is not None:
                proxy = "%s:%s" % (ph, pp)
            else:
                proxy = ph

            # username and password will override whatever was passed in the
            # URL
            if pu is not None and username is None:
                username = pu

                if pw is not None and password is None:
                    password = pw
                    
        self._uri = uri
        self._refreshCallback = None
        self._progressCallback = None
        self._bufferSize = None
        self._proxy = proxy
        self._username = username
        self._password = password

        # get the url
        type, uri = urllib.splittype(uri)
        type = (string.lower(type)).strip()
        self._type = type
        if type not in ("http", "https"):
            raise IOError, "unsupported XML-RPC protocol"
        self._host, self._handler = urllib.splithost(uri)
        if not self._handler:
            self._handler = "/RPC2"

        if transport is None:
            self._allow_redirect = 1
            transport = self.default_transport(type, proxy, username, password)
        else:
            #
            # dont allow redirect on unknow transports, that should be
            # set up independantly
            #
            self._allow_redirect = 0
            
        self._redirected = None
        self.use_handler_path = 1
        self._transport = transport

        self._trusted_cert_files = []
        self._lang = None

        self._encoding = encoding
        self._verbose = verbose

        self.set_refresh_callback(refreshCallback)
        self.set_progress_callback(progressCallback)

        self._headers = UserDictCase()

    def default_transport(self, type, proxy=None, username=None, password=None):
        if proxy:
            if type == 'https':
                transport = self._transport_class_https_proxy(proxy, 
                    proxyUsername=username, proxyPassword=password)
            else:
                transport = self._transport_class_proxy(proxy, 
                    proxyUsername=username, proxyPassword=password)
        else:
            if type == 'https':
                transport = self._transport_class_https()
            else:
                transport = self._transport_class()
        return transport

    def allow_redirect(self, allow):
        self._allow_redirect = allow

    def redirected(self):
        if not self._allow_redirect:
            return None
        return self._redirected

    def set_refresh_callback(self, refreshCallback):
        self._refreshCallback = refreshCallback
        self._transport.set_refresh_callback(refreshCallback)

    def set_buffer_size(self, bufferSize):
        self._bufferSize = bufferSize
        self._transport.set_buffer_size(bufferSize)

    def set_progress_callback(self, progressCallback, bufferSize=16384):
        self._progressCallback = progressCallback
        self._transport.set_progress_callback(progressCallback, bufferSize)

    def _req_body(self, params, methodname):
        return xmlrpclib.dumps(params, methodname, encoding=self._encoding)

    def get_response_headers(self):
        if self._transport:
            return self._transport.headers_in
        return None

    def get_response_status(self):
        if self._transport:
            return self._transport.response_status
        return None

    def get_response_reason(self):
        if self._transport:
            return self._transport.response_reason
        return None

    def get_content_range(self):
        """Returns a dictionary with three values:
            length: the total length of the entity-body (can be None)
            first_byte_pos: the position of the first byte (zero based)
            last_byte_pos: the position of the last byte (zero based)
           The range is inclusive; that is, a response 8-9/102 means two bytes
        """
        headers = self.get_response_headers()
        if not headers:
            return None
        content_range = headers.get('Content-Range')
        if not content_range:
            return None
        arr = filter(None, string.split(content_range))
        assert arr[0] == "bytes"
        assert len(arr) == 2
        arr = string.split(arr[1], '/')
        assert len(arr) == 2

        brange, total_len = arr
        if total_len == '*':
            # Per RFC, the server is allowed to use * if the length of the
            # entity-body is unknown or difficult to determine
            total_len = None
        else:
            total_len = int(total_len)

        start, end = string.split(brange, '-')
        result = {
            'length'            : total_len,
            'first_byte_pos'    : int(start),
            'last_byte_pos'     : int(end),
        }
        return result

    def accept_ranges(self):
        headers = self.get_response_headers()
        if not headers:
            return None
        if headers.has_key('Accept-Ranges'):
            return headers['Accept-Ranges']
        return None

    def _strip_characters(self, *args):
        """ Strip characters, which are not allowed according:
            http://www.w3.org/TR/2006/REC-xml-20060816/#charsets
            From spec:
            Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]  /* any Unicode character, excluding the surrogate blocks, FFFE, and FFFF. */
        """
        regexp = r'[\x00-\x08]|[\x0b-\x0c]|[\x0e-\x1f]'
        result=[]
        for item in args:
            item_type = type(item)
            if item_type == StringType or item_type == UnicodeType:
                item = re.sub(regexp, '', item)
            elif item_type == TupleType:
                item = tuple(map(self._strip_characters, item))
            elif item_type == ListType:
                item = map(self._strip_characters, item)
            elif item_type == DictType or item_type == DictionaryType:
                item = dict([(self._strip_characters(name, val)) for name, val in item.iteritems()])
            # else: some object - should take care of himself
            #        numbers - are safe
            result.append(item)
        if len(result) == 1:
            return result[0]
        else:
            return tuple(result)

    def _request(self, methodname, params):
        # call a method on the remote server
        # the loop is used to handle redirections
        redirect_response = 0
        retry = 0        
        while 1:
            if retry >= MAX_REDIRECTIONS:
                raise InvalidRedirectionError(
                      "Unable to fetch requested Package")

            # Clear the transport headers first
            self._transport.clear_headers()
            for k, v in self._headers.items():
                self._transport.set_header(k, v)
            
            self._transport.add_header("X-Info",
                'RPC Processor (C) Red Hat, Inc (version %s)' % 
                string.split(__version__)[1])
            # identify the capability set of this client to the server
            self._transport.set_header("X-Client-Version", 1)
            
            if self._allow_redirect:
                # Advertise that we follow redirects
                #changing the version from 1 to 2 to support backward compatibility
                self._transport.add_header("X-RHN-Transport-Capability",
                    "follow-redirects=3")

            if redirect_response:
                self._transport.add_header('X-RHN-Redirect', '0')
                if send_handler:
                    self._transport.add_header('X-RHN-Path', send_handler)

            request = self._req_body(self._strip_characters(params), methodname)

            try:
                if self._redirected: 
                    type, uri = urllib.splittype(self._redirected)
                    self._redirected = None
 
                    host, handler = urllib.splithost(uri) 
                    response = self._transport.request(host, handler, 
                        request, verbose=self._verbose) 
                else:    
                    response = self._transport.request(self._host, \
                                self._handler, request, verbose=self._verbose)
                save_response = self._transport.response_status
            except xmlrpclib.ProtocolError, pe:
                if self.use_handler_path:
                    raise pe
                else:
                     save_response = pe.errcode

            if not self._allow_redirect:
                raise InvalidRedirectionError("Redirects not allowed")
           
            if save_response == 200:
                # reset _host and _handler for next request
                type, uri = urllib.splittype(self._uri)
                self._host, self._handler = urllib.splithost(uri)
                # exit redirects loop and return response
                break
            elif save_response in (301, 302):
                self._redirected = self._transport.redirected()
                self.use_handler_path = 0
                redirect_response = 1
            else:
                # Retry pkg fetch
                 retry = retry + 1
                 self.use_handler_path = 1
                 continue
                                
            if self._verbose:
                print "%s redirected to %s" % (self._uri, self._redirected)

            typ, uri = urllib.splittype(self._redirected)
            
            if typ != None:
                typ = string.lower(typ)
            if typ not in ("http", "https"):
                raise InvalidRedirectionError(
                    "Redirected to unsupported protocol %s" % typ)

            #
            # We forbid HTTPS -> HTTP for security reasons
            # Note that HTTP -> HTTPS -> HTTP is allowed (because we compare
            # the protocol for the redirect with the original one)
            #
            if self._type == "https" and typ == "http":
                raise InvalidRedirectionError(
                    "HTTPS redirected to HTTP is not supported")

            if not self._handler:
                self._handler = "/RPC2"

            if save_response == 302:
                if not self._allow_redirect:
                    raise InvalidRedirectionError("Redirects not allowed")
                else:
                    redirect_response = 1
            # 
            # Create a new transport for the redirected service and 
            # set up the parameters on the new transport
            #
            del self._transport
            self._transport = self.default_transport(typ, self._proxy,
                                             self._username, self._password)
            self.set_progress_callback(self._progressCallback)
            self.set_refresh_callback(self._refreshCallback)
            self.set_buffer_size(self._bufferSize)
            self.setlang(self._lang)

            if self._trusted_cert_files != [] and \
               hasattr(self._transport, "add_trusted_cert"):
                for certfile in self._trusted_cert_files:
                    self._transport.add_trusted_cert(certfile)
            #
            # Then restart the loop to try the new entry point.
            #

        if isinstance(response, transports.File):
            # Just return the file
            return response
            
        # an XML-RPC encoded data structure
        if isinstance(response, TupleType) and len(response) == 1:
            response = response[0]

        return response

    def __repr__(self):
        return (
            "<%s for %s%s>" %
            (self.__class__.__name__, self._host, self._handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self._request, name)

    # note: to call a remote object with an non-standard name, use
    # result getattr(server, "strange-python-name")(args)

    def set_transport_flags(self, transfer=0, encoding=0, **kwargs):
        if not self._transport:
            # Nothing to do
            return
        kwargs.update({
            'transfer'  : transfer,
            'encoding'  : encoding,
        })
        apply(self._transport.set_transport_flags, (), kwargs)

    def get_transport_flags(self):
        if not self._transport:
            # Nothing to do
            return {}
        return self._transport.get_transport_flags()

    def reset_transport_flags(self):
        # Does nothing
        pass

    # Allow user-defined additional headers.
    def set_header(self, name, arg):
        if type(arg) in [ type([]), type(()) ]:
            # Multivalued header
            self._headers[name] = map(str, arg)
        else:
            self._headers[name] = str(arg)

    def add_header(self, name, arg):
        if self._headers.has_key(name):
            vlist = self._headers[name]
            if not isinstance(vlist, ListType):
                vlist = [ vlist ]
        else:
            vlist = self._headers[name] = []
        vlist.append(str(arg))

    # Sets the i18n options
    def setlang(self, lang):
        self._lang = lang
        if self._transport and hasattr(self._transport, "setlang"):
            self._transport.setlang(lang)
        
    # Sets the CA chain to be used
    def use_CA_chain(self, ca_chain = None):
        raise NotImplementedError, "This method is deprecated"

    def add_trusted_cert(self, certfile):
        self._trusted_cert_files.append(certfile)
        if self._transport and hasattr(self._transport, "add_trusted_cert"):
            self._transport.add_trusted_cert(certfile)
        
    def close(self):
        if self._transport:
            self._transport.close()
            self._transport = None

# RHN GET server
class GETServer(Server):
    def __init__(self, uri, transport=None, proxy=None, username=None,
            password=None, client_version=2, headers={}, refreshCallback=None,
            progressCallback=None):
        Server.__init__(self, uri, 
            proxy=proxy,
            username=username,
            password=password,
            transport=transport,
            refreshCallback=refreshCallback,
            progressCallback=progressCallback)
        self._client_version = client_version
        self._headers = headers
        # Back up the original handler, since we mangle it
        self._orig_handler = self._handler
        # Download resumption
        self.set_range(offset=None, amount=None)

    def _req_body(self, params, methodname):
        global send_handler
        
        if not params or len(params) < 1:
            raise Exception("Required parameter channel not found")
        # Strip the multiple / from the handler
        h_comps = filter(lambda x: x != '', string.split(self._orig_handler, '/'))
        # Set the handler we are going to request
        hndl = h_comps + ["$RHN", params[0], methodname] + list(params[1:])
        self._handler = '/' + string.join(hndl, '/')

        #save the constructed handler in case of redirect
        send_handler = self._handler
        
        # Add headers
        #override the handler to replace /XMLRPC with pkg path
        if self._redirected and not self.use_handler_path:
           self._handler = self._new_req_body()
            
        for h, v in self._headers.items():
            self._transport.set_header(h, v)

        if self._offset is not None:
            if self._offset >= 0:
                brange = str(self._offset) + '-'
                if self._amount is not None:
                    brange = brange + str(self._offset + self._amount - 1)
            else:
                # The last bytes
                # amount is ignored in this case
                brange = '-' + str(-self._offset)

            self._transport.set_header('Range', "bytes=" + brange)
            # Flag that we allow for partial content
            self._transport.set_transport_flags(allow_partial_content=1)
        # GET requests have empty body
        return ""

    def _new_req_body(self):
        type, tmpuri = urllib.splittype(self._redirected)
        site, handler = urllib.splithost(tmpuri)
        return handler
    
    def set_range(self, offset=None, amount=None):
        if offset is not None:
            try:
                offset = int(offset)
            except ValueError:
                # Error
                raise RangeError("Invalid value `%s' for offset" % offset)

        if amount is not None:
            try:
                amount = int(amount)
            except ValueError:
                # Error
                raise RangeError("Invalid value `%s' for amount" % amount)

            if amount <= 0:
                raise RangeError("Invalid value `%s' for amount" % amount)
                
        self._amount = amount
        self._offset = offset

    def reset_transport_flags(self):
        self._transport.set_transport_flags(allow_partial_content=0)

    def __getattr__(self, name):
        # magic method dispatcher
        return SlicingMethod(self._request, name)

    def default_transport(self, type, proxy=None, username=None, password=None):
	ret = Server.default_transport(self, type, proxy=proxy, username=username, password=password)
	ret.set_method("GET")
	return ret

class RangeError(Exception):
    pass

class InvalidRedirectionError(Exception):
    pass

def getHeaderValues(headers, name):
    import mimetools
    if not isinstance(headers, mimetools.Message):
        if headers.has_key(name):
            return [headers[name]]
        return []

    return map(lambda x: string.strip(string.split(x, ':', 1)[1]), 
            headers.getallmatchingheaders(name))

class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self._send = send
        self._name = name
    def __getattr__(self, name):
        return _Method(self._send, "%s.%s" % (self._name, name))
    def __call__(self, *args):
        return self._send(self._name, args)
    def __repr__(self):
        return (
            "<%s %s (%s)>" %
            (self.__class__.__name__, self._name, self._send)
            )
    __str__ = __repr__


class SlicingMethod(_Method):
    """
    A "slicing method" allows for byte range requests
    """
    def __init__(self, send, name):
        _Method.__init__(self, send, name)
        self._offset = None
    def __getattr__(self, name):
        return SlicingMethod(self._send, "%s.%s" % (self._name, name))
    def __call__(self, *args, **kwargs):
        self._offset = kwargs.get('offset')
        self._amount = kwargs.get('amount')

        # im_self is a pointer to self, so we can modify the class underneath 
        try:
            self._send.im_self.set_range(offset=self._offset,
                amount=self._amount)
        except AttributeError:
            pass

        result = self._send(self._name, args)

        # Reset "sticky" transport flags
        try:
            self._send.im_self.reset_transport_flags()
        except AttributeError:
            pass

        return result
        

def reportError(headers):
    # Reports the error from the headers
    errcode = 0
    errmsg = ""
    s = "X-RHN-Fault-Code"
    if headers.has_key(s):
        errcode = int(headers[s])
    s = "X-RHN-Fault-String"
    if headers.has_key(s):
        _sList = getHeaderValues(headers, s)
        if _sList:
            _s = string.join(_sList, '')
            import base64
            errmsg = "%s" % base64.decodestring(_s)

    return errcode, errmsg


########NEW FILE########
__FILENAME__ = SmartIO
#/usr/bin/env python
#
# Smart IO class
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>

# $Id: SmartIO.py 191145 2010-03-01 10:21:24Z msuchy $
"""
This module implements the SmartIO class
"""

import os
import time
from cStringIO import StringIO

class SmartIO:
    """
    The SmartIO class allows one to put a cap on the memory consumption.
    StringIO objects are very fast, because they are stored in memory, but
    if they are too big the memory footprint becomes noticeable.
    The write method of a SmartIO determines if the data that is to be added
    to the (initially) StrintIO object does not exceed a certain threshold; if
    it does, it switches the storage to a temporary disk file
    """
    def __init__(self, max_mem_size=16384, force_mem=0):
        self._max_mem_size = max_mem_size
        self._io = StringIO()
        # self._fixed is a flag to show if we're supposed to consider moving
        # the StringIO object into a tempfile
        # Invariant: if self._fixed == 0, we have a StringIO (if self._fixed
        # is 1 and force_mem was 0, then we have a file)
        if force_mem:
            self._fixed = 1
        else:
            self._fixed = 0

    def set_max_mem_size(self, max_mem_size):
        self._max_mem_size = max_mem_size

    def get_max_mem_size(self):
        return self._max_mem_size

    def write(self, data):
        if not self._fixed:
            # let's consider moving it to a file
            if len(data) + self._io.tell() > self._max_mem_size:
                # We'll overflow, change to a tempfile
                tmpfile = _tempfile()
                tmpfile.write(self._io.getvalue())
                self._fixed = 1
                self._io = tmpfile

        self._io.write(data)

    def __getattr__(self, name):
        return getattr(self._io, name)

# Creates a temporary file and passes back its file descriptor
def _tempfile(tmpdir='/tmp'):
    import tempfile
    (fd, fname) = tempfile.mkstemp(prefix="_rhn_transports-%d-" \
                                   % os.getpid(), dir=tmpdir)
    # tempfile, unlink it
    os.unlink(fname)
    return os.fdopen(fd, "wb+")


########NEW FILE########
__FILENAME__ = SSL
#!/usr/bin/python
#
# Higher-level SSL objects used by rpclib
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>

# $Id: SSL.py 191145 2010-03-01 10:21:24Z msuchy $

"""
rhn.SSL builds an abstraction on top of the objects provided by pyOpenSSL
"""

from OpenSSL import SSL, crypto
import os
import time

import socket
import select

DEFAULT_TIMEOUT = 120


class SSLSocket:
    """
    Class that wraps a pyOpenSSL Connection object, adding more methods
    """
    def __init__(self, socket, trusted_certs=None):
        # SSL.Context object
        self._ctx = None
        # SSL.Connection object 
        self._connection = None
        self._sock = socket
        self._trusted_certs = []
        # convert None to empty list
        trusted_certs = trusted_certs or []
        for f in trusted_certs:
            self.add_trusted_cert(f)
        # SSL method to use
        self._ssl_method = SSL.SSLv23_METHOD
        # Flags to pass to the SSL layer
        self._ssl_verify_flags = SSL.VERIFY_PEER 

        # Buffer size for reads
        self._buffer_size = 8192

        # Position, for tell()
        self._pos = 0
        # Buffer
        self._buffer = ""

        # Flag to show if makefile() was called
        self._makefile_called = 0

        self._closed = None

    def add_trusted_cert(self, file):
        """
        Adds a trusted certificate to the certificate store of the SSL context
        object.
        """
        if not os.access(file, os.R_OK):
            raise ValueError, "Unable to read certificate file %s" % file
        self._trusted_certs.append(file)

    def init_ssl(self):
        """
        Initializes the SSL connection.
        """
        self._check_closed()
        # Get a context
        self._ctx = SSL.Context(self._ssl_method)
        if self._trusted_certs:
            # We have been supplied with trusted CA certs
            for f in self._trusted_certs:
                self._ctx.load_verify_locations(f)
        else:
            # Reset the verify flags
            self._ssl_verify_flags = 0

        self._ctx.set_verify(self._ssl_verify_flags, ssl_verify_callback)
        if hasattr(SSL, "OP_DONT_INSERT_EMPTY_FRAGMENTS"):
            # Certain SSL implementations break when empty fragments are
            # initially sent (even if sending them is compliant to 
            # SSL 3.0 and TLS 1.0 specs). Play it safe and disable this
            # feature (openssl 0.9.6e and later)
            self._ctx.set_options(SSL.OP_DONT_INSERT_EMPTY_FRAGMENTS)

        # Init the connection
        self._connection = SSL.Connection(self._ctx, self._sock)
        # Place the connection in client mode
        self._connection.set_connect_state()

    def makefile(self, mode, bufsize=None):
        """
        Returns self, since we are a file-like object already
        """
        if bufsize:
            self._buffer_size = bufsize

        # Increment the counter with the number of times we've called makefile
        # - we don't want close to actually close things until all the objects
        # that originally called makefile() are gone
        self._makefile_called = self._makefile_called + 1
        return self
    
    def close(self):
        """
        Closes the SSL connection
        """
        # XXX Normally sock.makefile does a dup() on the socket file
        # descriptor; httplib relies on this, but there is no dup for an ssl
        # connection; so we have to count how may times makefile() was called
        if self._closed:
            # Nothing to do
            return
        if not self._makefile_called:
            self._really_close()
            return
        self._makefile_called = self._makefile_called - 1

    def _really_close(self):
        self._connection.shutdown()
        self._connection.close()
        self._closed = 1

    def _check_closed(self):
        if self._closed:
            raise ValueError, "I/O operation on closed file"

    def __getattr__(self, name):
        if hasattr(self._connection, name):
            return getattr(self._connection, name)
        raise AttributeError, name

    # File methods
    def isatty(self):
        """
        Returns false always.
        """
        return 0

    def tell(self):
        return self._pos

    def seek(self, pos, mode=0):
        raise NotImplementedError, "seek"

    def read(self, amt=None):
        """
        Reads up to amt bytes from the SSL connection.
        """
        self._check_closed()
        # Initially, the buffer size is the default buffer size.
        # Unfortunately, pending() does not return meaningful data until
        # recv() is called, so we only adjust the buffer size after the
        # first read
        buffer_size = self._buffer_size

        # Read only the specified amount of data
        while amt is None or len(self._buffer) < amt:
            # if amt is None (read till the end), fills in self._buffer
            if amt is not None:
                buffer_size = min(amt - len(self._buffer), buffer_size)

            try:
                data = self._connection.recv(buffer_size)
 
                self._buffer = self._buffer + data

                # More bytes to read?
                pending = self._connection.pending()
                if pending == 0:
                    # we're done here
                    break
            except SSL.ZeroReturnError:
                # Nothing more to be read
                break
            except SSL.SysCallError, e:
                print "SSL exception", e.args
                break
            except SSL.WantWriteError:
                self._poll(select.POLLOUT, 'read')
            except SSL.WantReadError:
                self._poll(select.POLLIN, 'read')

        if amt:
            ret = self._buffer[:amt]
            self._buffer = self._buffer[amt:]
        else:
            ret = self._buffer
            self._buffer = ""

        self._pos = self._pos + len(ret)
        return ret

    def _poll(self, filter_type, caller_name):
        poller = select.poll()
        poller.register(self._sock, filter_type)
        res = poller.poll(self._sock.gettimeout() * 1000)
        if len(res) != 1:
            raise TimeoutException, "Connection timed out on %s" % caller_name

    def write(self, data):
        """
        Writes to the SSL connection.
        """
        self._check_closed()
        
        # XXX Should use sendall 
        # sent = self._connection.sendall(data)
        origlen = len(data)
        while True:
            try:
                sent = self._connection.send(data)
                if sent == len(data):
                    break
                data = data[sent:]
            except SSL.WantWriteError:
                self._poll(select.POLLOUT, 'write')
            except SSL.WantReadError:
                self._poll(select.POLLIN, 'write')
                 
        return origlen

    def recv(self, amt):
        return self.read(amt)

    send = write

    sendall = write

    def readline(self, length=None):
        """
        Reads a single line (up to `length' characters long) from the SSL
        connection.
        """
        self._check_closed()
        while True:
            # charcount contains the number of chars to be outputted (or None
            # if none to be outputted at this time)
            charcount = None
            i = self._buffer.find('\n')
            if i >= 0:
                # Go one char past newline
                charcount = i + 1
            elif length and len(self._buffer) >= length:
                charcount = length

            if charcount is not None:
                ret = self._buffer[:charcount]
                self._buffer = self._buffer[charcount:]
                self._pos = self._pos + len(ret)
                return ret

            # Determine the number of chars to be read next
            bufsize = self._buffer_size
            if length:
                # we know length > len(self._buffer)
                bufsize = min(self._buffer_size, length - len(self._buffer))

            try:
                data = self._connection.recv(bufsize)
                self._buffer = self._buffer + data
            except SSL.ZeroReturnError:
                # Nothing more to be read
                break
            except SSL.WantWriteError:
                self._poll(select.POLLOUT, 'readline')
            except SSL.WantReadError:
                self._poll(select.POLLIN, 'readline')

        # We got here if we're done reading, so return everything
        ret = self._buffer
        self._buffer = ""
        self._pos = self._pos + len(ret)
        return ret


def ssl_verify_callback(conn, cert, errnum, depth, ok):
    """
    Verify callback, which will be called for each certificate in the
    certificate chain.
    """
    # Nothing by default
    return ok

class TimeoutException(SSL.Error):
    
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return "Timeout Exception"

########NEW FILE########
__FILENAME__ = transports
#/usr/bin/env python
#
# Helper transport objects
#
# Copyright (c) 2002-2005 Red Hat, Inc.
#
# Author: Mihai Ibanescu <misa@redhat.com>
# Based on what was previously shipped as cgiwrap:
#   - Cristian Gafton <gafton@redhat.com> 
#   - Erik Troan <ewt@redhat.com>

# $Id: transports.py 191145 2010-03-01 10:21:24Z msuchy $

# Transport objects
import os
import sys
import time
import string
from types import IntType, StringType, ListType
from SmartIO import SmartIO

from UserDictCase import UserDictCase

import connections
xmlrpclib = connections.xmlrpclib

__version__ = "$Revision: 191145 $"

# XXX
COMPRESS_LEVEL = 6

# Exceptions
class NotProcessed(Exception):
    pass

class Transport(xmlrpclib.Transport):
    user_agent = "rhn.rpclib.py/%s" % __version__
    _use_datetime = False

    def __init__(self, transfer=0, encoding=0, refreshCallback=None,
            progressCallback=None):
        self._transport_flags = {'transfer' : 0, 'encoding' : 0}
        self.set_transport_flags(transfer=transfer, encoding=encoding)
        self._headers = UserDictCase()
        self.verbose = 0
        self.connection = None
        self.method = "POST"
        self._lang = None
        self.refreshCallback = refreshCallback
        self.progressCallback = progressCallback
        self.bufferSize = 16384
        self.headers_in = None
        self.response_status = None
        self.response_reason = None
        self._redirected = None

    # set the progress callback
    def set_progress_callback(self, progressCallback, bufferSize=16384):
        self.progressCallback = progressCallback
        self.bufferSize = bufferSize

    # set the refresh callback
    def set_refresh_callback(self, refreshCallback):
        self.refreshCallback = refreshCallback

    # set the buffer size
    # The bigger this is, the faster the read is, but the more seldom is the 
    # progress callback called
    def set_buffer_size(self, bufferSize):
        if bufferSize is None:
            # No buffer size specified; go with 16k
            bufferSize = 16384

        self.bufferSize = bufferSize

    # set the request method
    def set_method(self, method):
        if method not in ("GET", "POST"):
            raise IOError, "Unknown request method %s" % method
        self.method = method
    
    # reset the transport options
    def set_transport_flags(self, transfer=None, encoding=None, **kwargs):
        # For backwards compatibility, we keep transfer and encoding as
        # positional parameters (they could come in as kwargs easily)

        self._transport_flags.update(kwargs)
        if transfer is not None:
            self._transport_flags['transfer'] = transfer
        if encoding is not None:
            self._transport_flags['encoding'] = encoding
        self.validate_transport_flags()

    def get_transport_flags(self):
        return self._transport_flags.copy()

    def validate_transport_flags(self):
        # Transfer and encoding are guaranteed to be there
        transfer = self._transport_flags.get('transfer')
        transfer = lookupTransfer(transfer, strict=1)
        self._transport_flags['transfer'] = transfer

        encoding = self._transport_flags.get('encoding')
        encoding = lookupEncoding(encoding, strict=1)
        self._transport_flags['encoding'] = encoding

    # Add arbitrary additional headers.
    def set_header(self, name, arg):
        if type(arg) in [ type([]), type(()) ]:
            # Multivalued header
            self._headers[name] = map(str, arg)
        else:
            self._headers[name] = str(arg)

    def add_header(self, name, arg):
        if self._headers.has_key(name):
            vlist = self._headers[name]
            if not isinstance(vlist, ListType):
                vlist = [ vlist ]
        else:
            vlist = self._headers[name] = []
        vlist.append(str(arg))

    def clear_headers(self):
        self._headers.clear()

    def get_connection(self, host):
        if self.verbose:
            print "Connecting via http to %s" % (host, )
        return connections.HTTPConnection(host)
        
    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        # XXX: automatically compute how to send depending on how much data
        #      you want to send
        
        # XXX Deal with HTTP/1.1 if necessary
        self.verbose = verbose
        
        # implement BASIC HTTP AUTHENTICATION
        host, extra_headers, x509 = self.get_host_info(host)
        if not extra_headers:
            extra_headers = []
        # Establish the connection
        connection = self.get_connection(host)
        # Setting the user agent. Only interesting for SSL tunnels, in any
        # other case the general headers are good enough.
        connection.set_user_agent(self.user_agent)
        if self.verbose:
            connection.set_debuglevel(self.verbose - 1)
        # Get the output object to push data with
        req = Output(connection=connection, method=self.method)
        apply(req.set_transport_flags, (), self._transport_flags)

        # Add the extra headers
        req.set_header('User-Agent', self.user_agent)
        for header, value in self._headers.items() + extra_headers:
            # Output.set_header correctly deals with multivalued headers now
            req.set_header(header, value)

        # Content-Type
        req.set_header("Content-Type", "text/xml")
        req.process(request_body)

        # Host and Content-Length are set by HTTP*Connection
        for h in ['Content-Length', 'Host']:
            req.clear_header(h)
        
        # XXX: should try-catch ProtocolError here. But I am not sure 
        # what to do with it if I get it, so for now letting it slip 
        # through to the next level is sortof working. 
        # Must be fixed before ship, though. --gafton
        headers, fd = req.send_http(host, handler)
        
        if self.verbose:
            print "Incoming headers:"
            for header, value in headers.items():
                print "\t%s : %s" % (header, value)

        if fd.status in (301, 302):
            self._redirected = headers["Location"]
            self.response_status = fd.status
            return None

        # Save the headers
        self.headers_in = headers
        self.response_status = fd.status
        self.response_reason = fd.reason

        return self._process_response(fd, connection)

    def _process_response(self, fd, connection):
        # Now use the Input class in case we get an enhanced response
        resp = Input(self.headers_in, progressCallback=self.progressCallback,
                bufferSize=self.bufferSize)
        
        fd = resp.decode(fd)
        
        if isinstance(fd, InputStream):
            # When the File object goes out of scope, so will the InputStream;
            # that will eventually call the connection's close() method and
            # cleanly reap it
            f = File(fd.fd, fd.length, fd.name, bufferSize=self.bufferSize,
                progressCallback=self.progressCallback)
            # Set the File's close method to the connection's
            # Note that calling the HTTPResponse's close() is not enough,
            # since the main socket would remain open, and this is
            # particularily bad with SSL
            f.close = connection.close
            return f

        # We can safely close the connection now; if we had an
        # application/octet/stream (for which Input.read passes the original
        # socket object), Input.decode would return an InputStream,
        # so we wouldn't reach this point
        connection.close()

        return self.parse_response(fd)

    # Give back the new URL if redirected
    def redirected(self):
        return self._redirected

    # Rewrite parse_response to provide refresh callbacks
    def parse_response(self, f):
        # read response from input file, and parse it

        p, u = self.getparser()

        while 1:
            response = f.read(1024)
            if not response:
                break
            if self.refreshCallback:
                self.refreshCallback()
            if self.verbose:
                print "body:", repr(response)
            p.feed(response)

        f.close()
        p.close()
        return u.close()

        
    def setlang(self, lang):
        self._lang = lang

class SafeTransport(Transport):
    def __init__(self, transfer=0, encoding=0, refreshCallback=None,
                progressCallback=None, trusted_certs=None):
        Transport.__init__(self, transfer, encoding, 
            refreshCallback=refreshCallback, progressCallback=progressCallback)
        self.trusted_certs = []
        for certfile in (trusted_certs or []):
            self.add_trusted_cert(certfile)

    def add_trusted_cert(self, certfile):
        if not os.access(certfile, os.R_OK):
            raise ValueError, "Certificate file %s is not accessible" % certfile
        self.trusted_certs.append(certfile)

    def get_connection(self, host):
        # implement BASIC HTTP AUTHENTICATION
        host, extra_headers, x509 = self.get_host_info(host)
        if self.verbose:
            print "Connecting via https to %s" % (host, )
        return connections.HTTPSConnection(host, trusted_certs=self.trusted_certs)


class ProxyTransport(Transport):
    def __init__(self, proxy, proxyUsername=None, proxyPassword=None,
            transfer=0, encoding=0, refreshCallback=None, progressCallback=None):
        Transport.__init__(self, transfer, encoding,
            refreshCallback=refreshCallback, progressCallback=progressCallback)
        self._proxy = proxy
        self._proxy_username = proxyUsername
        self._proxy_password = proxyPassword

    def get_connection(self, host):
        if self.verbose:
            print "Connecting via http to %s proxy %s, username %s, pass %s" % (
                host, self._proxy, self._proxy_username, self._proxy_password)
        return connections.HTTPProxyConnection(self._proxy, host, 
            username=self._proxy_username, password=self._proxy_password)

class SafeProxyTransport(ProxyTransport):
    def __init__(self, proxy, proxyUsername=None, proxyPassword=None,
            transfer=0, encoding=0, refreshCallback=None,
            progressCallback=None, trusted_certs=None):
        ProxyTransport.__init__(self, proxy, 
            proxyUsername=proxyUsername, proxyPassword=proxyPassword,
            transfer=transfer, encoding=encoding, 
            refreshCallback=refreshCallback,
            progressCallback=progressCallback)
        self.trusted_certs = []
        for certfile in (trusted_certs or []):
            self.add_trusted_cert(certfile)

    def add_trusted_cert(self, certfile):
        if not os.access(certfile, os.R_OK):
            raise ValueError, "Certificate file %s is not accessible" % certfile
        self.trusted_certs.append(certfile)

    def get_connection(self, host):
        if self.verbose:
            print "Connecting via https to %s proxy %s, username %s, pass %s" % (
                host, self._proxy, self._proxy_username, self._proxy_password)
        return connections.HTTPSProxyConnection(self._proxy, host, 
            username=self._proxy_username, password=self._proxy_password, 
            trusted_certs=self.trusted_certs)

# ============================================================================
# Extended capabilities for transport
#
# We allow for the following possible headers:
#
# Content-Transfer-Encoding:
#       This header tells us how the POST data is encoded in what we read.
#       If it is not set, we assume plain text that can be passed along
#       without any other modification. If set, valid values are:
#       - binary : straight binary data
#       - base64 : will pass through base64 decoder to get the binary data
#
# Content-Encoding:
#       This header tells us what should we do with the binary data obtained
#       after acting on the Content-Transfer-Encoding header. Valid values:
#       - x-gzip : will need to pass through GNU gunzip-like to get plain
#                  text out
#       - x-zlib : this denotes the Python's own zlib bindings which are a
#                  datastream based on gzip, but not quite
#       - x-gpg : will need to pass through GPG to get out the text we want

# ============================================================================
# Input class to automate reading the posting from the network
# Having to work with environment variables blows, though
class Input:
    def __init__(self, headers=None, progressCallback=None, bufferSize=1024,
            max_mem_size=16384):
        self.transfer = None
        self.encoding = None
        self.type = None
        self.length = 0
        self.lang = "C"
        self.name = ""
        self.progressCallback = progressCallback
        self.bufferSize = bufferSize
        self.max_mem_size = max_mem_size
        
        if not headers:
            # we need to get them from environment
            if os.environ.has_key("HTTP_CONTENT_TRANSFER_ENCODING"):
                self.transfer = string.lower(
                    os.environ["HTTP_CONTENT_TRANSFER_ENCODING"])
            if os.environ.has_key("HTTP_CONTENT_ENCODING"):
                self.encoding = string.lower(os.environ["HTTP_CONTENT_ENCODING"])
            if os.environ.has_key("CONTENT-TYPE"):
                self.type = string.lower(os.environ["CONTENT-TYPE"])
            if os.environ.has_key("CONTENT_LENGTH"):
                self.length = int(os.environ["CONTENT_LENGTH"])
            if os.environ.has_key("HTTP_ACCEPT_LANGUAGE"):
                self.lang = os.environ["HTTP_ACCEPT_LANGUAGE"]
            if os.environ.has_key("HTTP_X_PACKAGE_FILENAME"):
                self.name = os.environ["HTTP_X_PACKAGE_FILENAME"]
        else:
            # The stupid httplib screws up the headers from the HTTP repsonse
            # and converts them to lowercase. This means that we have to
            # convert to lowercase all the dictionary keys in case somebody calls
            # us with sane values --gaftonc (actually mimetools is the culprit)
            for header in headers.keys():
                value = headers[header]
                h = string.lower(header)
                if h == "content-length":
                    try:
                        self.length = int(value)
                    except ValueError:
                        self.length = 0
                elif h == "content-transfer-encoding":
                    # RFC 2045 #6.1: case insensitive
                    self.transfer = string.lower(value)
                elif h == "content-encoding":
                    # RFC 2616 #3.5: case insensitive
                    self.encoding = string.lower(value)
                elif h == "content-type":
                    # RFC 2616 #3.7: case insensitive
                    self.type = string.lower(value)
                elif h == "accept-language":
                    # RFC 2616 #3.10: case insensitive
                    self.lang = string.lower(value)
                elif h == "x-package-filename":
                    self.name = value
            
        self.io = None
   
    def read(self, fd = sys.stdin):
        # The octet-streams are passed right back
        if self.type == "application/octet-stream":
            return
        
        if self.length:
            # Read exactly the amount of data we were told
            self.io = _smart_read(fd, self.length, 
                bufferSize=self.bufferSize,
                progressCallback=self.progressCallback,
                max_mem_size=self.max_mem_size)
        else:
            # Oh well, no clue; read until EOF (hopefully)
            self.io = _smart_total_read(fd)

        if not self.transfer or self.transfer == "binary":
            return
        elif self.transfer == "base64":
            import base64
            old_io = self.io
            old_io.seek(0, 0)
            self.io = SmartIO(max_mem_size=self.max_mem_size)
            base64.decode(old_io, self.io)
        else:
            raise NotImplementedError(self.transfer)

    def decode(self, fd = sys.stdin):
        # The octet-stream data are passed right back
        if self.type in ["application/octet-stream", "application/x-rpm"]:
            return InputStream(fd, self.length, self.name, close=fd.close)
        
        if not self.io:
            self.read(fd)

        # At this point self.io exists (the only case when self.read() does
        # not initialize self.io is when content-type is
        # "application/octet-stream" - and we already dealt with that case

        # We can now close the file descriptor
        if hasattr(fd, "close"):
            fd.close()

        # Now we have the binary goo
        if not self.encoding or self.encoding == "__plain":
            # all is fine.
            pass
        elif self.encoding in ("x-zlib", "deflate"):
            import zlib
            obj = zlib.decompressobj()
            self.io.seek(0, 0)
            data = obj.decompress(self.io.read()) + obj.flush()
            del obj
            self.length = len(data)
            self.io = SmartIO(max_mem_size=self.max_mem_size)
            self.io.write(data)
        elif self.encoding in ("x-gzip", "gzip"):
            import gzip
            self.io.seek(0, 0)
            gz = gzip.GzipFile(mode="rb", compresslevel = COMPRESS_LEVEL,
                               fileobj=self.io)
            data = gz.read()
            self.length = len(data)
            self.io = SmartIO(max_mem_size=self.max_mem_size)
            self.io.write(data)
        elif self.encoding == "x-gpg":           
            # XXX: should be written
            raise NotImplementedError(self.transfer, self.encoding)
        else:
            raise NotImplementedError(self.transfer, self.encoding)

        # Play nicely and rewind the file descriptor
        self.io.seek(0, 0)
        return self.io
    
    def getlang(self):
        return self.lang

# Utility functions 

def _smart_total_read(fd, bufferSize=1024, max_mem_size=16384):
    """
    Tries to read data from the supplied stream, and puts the results into a
    StmartIO object. The data will be in memory or in a temporary file,
    depending on how much it's been read
    Returns a SmartIO object
    """
    io = SmartIO(max_mem_size=max_mem_size)
    while 1:
        chunk = fd.read(bufferSize)
        if not chunk:
            # EOF reached
            break
        io.write(chunk)

    return io

def _smart_read(fd, amt, bufferSize=1024, progressCallback=None,
        max_mem_size=16384):
    # Reads amt bytes from fd, or until the end of file, whichever
    # occurs first
    # The function will read in memory if the amout to be read is smaller than
    # max_mem_size, or to a temporary file otherwise
    #
    # Unlike read(), _smart_read tries to return exactly the requested amount
    # (whereas read will return _up_to_ that amount). Reads from sockets will
    # usually reaturn less data, or the read can be interrupted
    # 
    # Inspired by Greg Stein's httplib.py (the standard in python 2.x)
    #
    # support for progress callbacks added
    startTime = time.time()
    lastTime = startTime
    buf = SmartIO(max_mem_size=max_mem_size)
    
    origsize = amt
    while amt > 0:
        curTime = time.time()
        l = min(bufferSize, amt)
        chunk = fd.read(l)
        # read guarantees that len(chunk) <= l
        l = len(chunk)
        if not l:
            # Oops. Most likely EOF
            break

        # And since the original l was smaller than amt, we know amt >= 0
        amt = amt - l
        buf.write(chunk)
        if progressCallback is None:
            # No progress callback, so don't do fancy computations
            continue
        # We update the progress callback if:
        #  we haven't updated it for more than a secord, or
        #  it's the last read (amt == 0)
        if curTime - lastTime >= 1 or amt == 0:
            lastTime = curTime
            # use float() so that we force float division in the next step
            bytesRead = float(origsize - amt)
            # if amt == 0, on a fast machine it is possible to have 
            # curTime - lastTime == 0, so add an epsilon to prevent a division
            # by zero
            speed = bytesRead / ((curTime - startTime) + .000001)
            if origsize == 0:
                secs = 0
            else:
                # speed != 0 because bytesRead > 0
                # (if bytesRead == 0 then origsize == amt, which means a read
                # of 0 length; but that's impossible since we already checked
                # that l is non-null
                secs = amt / speed
            progressCallback(bytesRead, origsize, speed, secs) 

    # Now rewind the SmartIO
    buf.seek(0, 0)
    return buf

class InputStream:
    def __init__(self, fd, length, name = "<unknown>", close=None):
        self.fd = fd
        self.length = int(length)
        self.name = name
        # Close function
        self.close = close
    def __repr__(self):
        return "Input data is a stream of %d bytes for file %s.\n" % (self.length, self.name)


# ============================================================================
# Output class that will be used to build the temporary output string
class BaseOutput:
    # DEFINES for instances use   
    # Content-Encoding
    ENCODE_NONE = 0
    ENCODE_GZIP = 1
    ENCODE_ZLIB = 2
    ENCODE_GPG  = 3
    
    # Content-Transfer-Encoding
    TRANSFER_NONE   = 0
    TRANSFER_BINARY = 1
    TRANSFER_BASE64 = 2

     # Mappings to make things easy
    encodings = [
         [None, "__plain"],     # ENCODE_NONE
         ["x-gzip", "gzip"],    # ENCODE_GZIP
         ["x-zlib", "deflate"], # ENCODE_ZLIB
         ["x-gpg"],             # ENCODE_GPG
    ]
    transfers = [
         None,          # TRANSFER_NONE
         "binary",      # TRANSFRE_BINARY
         "base64",      # TRANSFER_BASE64
    ]

    def __init__(self, transfer=0, encoding=0, connection=None, method="POST"):
        # Assumes connection is an instance of HTTPConnection
        if connection:
            if not isinstance(connection, connections.HTTPConnection):
                raise Exception("Expected an HTTPConnection type object")

        self.method = method

        # Store the connection
        self._connection = connection

        self.data = None
        self.headers = UserDictCase()
        self.encoding = 0
        self.transfer = 0
        self.transport_flags = {}
        # for authenticated proxies
        self.username = None
        self.password = None
        # Fields to keep the information about the server
        self._host = None
        self._handler = None
        self._http_type = None
        self._protocol = None
        # Initialize self.transfer and self.encoding
        self.set_transport_flags(transfer=transfer, encoding=encoding)

        # internal flags
        self.__processed = 0
        
    def set_header(self, name, arg):
        if type(arg) in [ type([]), type(()) ]:
            # Multi-valued header
            #
            # Per RFC 2616, section 4.2 (Message Headers):
            # Multiple message-header fields with the same field-name MAY be
            # present in a message if and only if the entire field-value for
            # the header field is defined as a comma-separated list [i.e.
            # #(values)]. It MUST be possible to combine the multiple header
            # fields into one "field-name: field-value" pair, without
            # changing the semantics of the message, by appending each
            # subsequent field-value to the first, each separated by a comma.
            self.headers[name] = string.join(map(str, arg), ',')
        else:
            self.headers[name] = str(arg)

    def clear_header(self, name):
        if self.headers.has_key(name):
            del self.headers[name]

    def process(self, data):
        # Assume straight text/xml
        self.data = data

        # Content-Encoding header
        if self.encoding == self.ENCODE_GZIP:
            import gzip
            encoding_name = self.encodings[self.ENCODE_GZIP][0]
            self.set_header("Content-Encoding", encoding_name)
            f = SmartIO(force_mem=1)
            gz = gzip.GzipFile(mode="wb", compresslevel=COMPRESS_LEVEL,
                               fileobj = f)
            gz.write(data)
            gz.close()
            self.data = f.getvalue()
            f.close()
        elif self.encoding == self.ENCODE_ZLIB:
            import zlib
            encoding_name = self.encodings[self.ENCODE_ZLIB][0]
            self.set_header("Content-Encoding", encoding_name)
            obj = zlib.compressobj(COMPRESS_LEVEL)
            self.data = obj.compress(data) + obj.flush()
        elif self.encoding == self.ENCODE_GPG:
            # XXX: fix me.
            raise NotImplementedError(self.transfer, self.encoding)
            encoding_name = self.encodings[self.ENCODE_GPG][0]
            self.set_header("Content-Encoding", encoding_name)

        # Content-Transfer-Encoding header
        if self.transfer == self.TRANSFER_BINARY:
            transfer_name = self.transfers[self.TRANSFER_BINARY]
            self.set_header("Content-Transfer-Encoding", transfer_name)
            self.set_header("Content-Type", "application/binary")
        elif self.transfer == self.TRANSFER_BASE64:
            import base64
            transfer_name = self.transfers[self.TRANSFER_BASE64]
            self.set_header("Content-Transfer-Encoding", transfer_name)
            self.set_header("Content-Type", "text/base64")
            self.data = base64.encodestring(self.data)
            
        self.set_header("Content-Length", len(self.data))

        # other headers
        self.set_header("X-Transport-Info",
            'Extended Capabilities Transport (C) Red Hat, Inc (version %s)' % 
            string.split(__version__)[1])
        self.__processed = 1
        
    # reset the transport options
    def set_transport_flags(self, transfer=0, encoding=0, **kwargs):
        self.transfer = transfer
        self.encoding = encoding
        self.transport_flags.update(kwargs)

    def send_http(self, host, handler="/RPC2"):
        if not self.__processed:
            raise NotProcessed

        self._host = host

        if self._connection is None:
            raise Exception("No connection object found")
        self._connection.connect()
        self._connection.request(self.method, handler, body=self.data, 
            headers=self.headers)
        
        response = self._connection.getresponse()

        if not self.response_acceptable(response):
            raise xmlrpclib.ProtocolError("%s %s" % 
                (self._host, handler),
                response.status, response.reason, response.msg)
                
        # A response object has read() and close() methods, so we can safely
        # pass the whole object back
        return response.msg, response

    def response_acceptable(self, response):
        """Returns true if the response is acceptable"""
        if response.status == 200:
            return 1
        if response.status in (301, 302):
            return 1
        if response.status != 206:
            return 0
        # If the flag is not set, it's unacceptable
        if not self.transport_flags.get('allow_partial_content'):
            return 0
        if response.msg['Content-Type'] != 'application/octet-stream':
            # Don't allow anything else to be requested as a range, it could
            # break the XML parser
            return 0
        return 1

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

def lookupTransfer(transfer, strict=0):
    """Given a string or numeric representation of a transfer, return the
    transfer code"""
    if transfer is None:
        # Plain
        return 0
    if isinstance(transfer, IntType) and 0 <= transfer < len(Output.transfers):
        return transfer
    if isinstance(transfer, StringType):
        for i in range(len(Output.transfers)):
            if Output.transfers[i] == string.lower(transfer):
                return i
    if strict:
        raise ValueError("Unsupported transfer %s" % transfer)
    # Return default
    return 0

def lookupEncoding(encoding, strict=0):
    """Given a string or numeric representation of an encoding, return the
    encoding code"""
    if encoding is None:
        # Plain
        return 0
    if isinstance(encoding, IntType) and 0 <= encoding < len(Output.encodings):
        return encoding
    if isinstance(encoding, StringType):
        for i in range(len(Output.encodings)):
            if string.lower(encoding) in Output.encodings[i]:
                return i
    if strict:
        raise ValueError("Unsupported encoding %s" % encoding)
    # Return default
    return 0

Output = BaseOutput

# File object
class File:
    def __init__(self, file_obj, length = 0, name = None,
            progressCallback=None, bufferSize=16384):
        self.length = length
        self.file_obj = file_obj
        self.close = file_obj.close
        self.bufferSize=bufferSize
        self.name = ""
        if name:
            self.name = name[string.rfind(name, "/")+1:]
        self.progressCallback = progressCallback

    def __len__(self):
        return self.length

    def read(self, amt=None):
        # If they want to read everything, use _smart_read
        if amt is None:
            fd = self._get_file()
            return fd.read()

        return self.file_obj.read(amt)

    def read_to_file(self, file):
        """Copies the contents of this File object into another file
        object"""
        fd = self._get_file()
        while 1:
            buf = fd.read(self.bufferSize)
            if not buf:
                break
            file.write(buf)
        return file
        
    def _get_file(self):
        """Read everything into a temporary file and call the progress
        callbacks if the file length is defined, or just reads till EOF"""
        if self.length:
            io = _smart_read(self.file_obj, self.length,
                bufferSize=self.bufferSize, 
                progressCallback=self.progressCallback)
            io.seek(0, 0)
        else:
            # Read everuthing - no callbacks involved
            io = _smart_total_read(self.file_obj, bufferSize=self.bufferSize)
        io.seek(0, 0)
        return io

    def __del__(self):
        if self.close:
            self.close()
            self.close = None

########NEW FILE########
__FILENAME__ = UserDictCase
# This file implements a case insensitive dictionary on top of the
# UserDict standard python class
#
# Copyright (c) 2001-2005, Red Hat Inc.
# All rights reserved.
#
# $Id: UserDictCase.py 191145 2010-03-01 10:21:24Z msuchy $

import string

from types import StringType
from UserDict import UserDict

# A dictionary with case insensitive keys
class UserDictCase(UserDict):
    def __init__(self, data = None):
        self.kcase = {}
        UserDict.__init__(self, data)
    # some methods used to make the class work as a dictionary
    def __setitem__(self, key, value):
        lkey = key
        if isinstance(key, StringType):
            lkey = string.lower(key)
        self.data[lkey] = value
        self.kcase[lkey] = key
    def __getitem__(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        if not self.data.has_key(key):
            return None
        return self.data[key]   
    def __delitem__(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        del self.data[key]
        del self.kcase[key]
    get = __getitem__
    def keys(self):
        return self.kcase.values()
    def items(self):
        return self.get_hash().items()
    def has_key(self, key):
        if isinstance(key, StringType):
            key = string.lower(key)
        return self.data.has_key(key)
    def clear(self):
        self.data.clear()
        self.kcase.clear()        
    # return this data as a real hash
    def get_hash(self):
        return reduce(lambda a, (ik, v), hc=self.kcase:
                      a.update({ hc[ik] : v}) or a, self.data.items(), {})
                              
    # return the data for marshalling
    def __getstate__(self):
        return self.get_hash()
    # we need a setstate because of the __getstate__ presence screws up deepcopy
    def __setstate__(self, state):
        self.__init__(state)
    # get a dictionary out of this instance ({}.update doesn't get instances)
    def dict(self):
        return self.get_hash()
    def update(self, dict):
        for (k, v) in dict.items():
            lk = k
            if isinstance(k, StringType):
                lk = string.lower(k)
            self.data[lk] = v
            self.kcase[lk] = k
    # Expose an iterator. This would normally fail if there is no iter()
    # function defined - but __iter__ will never be called on python 1.5.2
    def __iter__(self):
        return iter(self.data)

########NEW FILE########
__FILENAME__ = _httplib
"""HTTP/1.1 client library

<intro stuff goes here>
<other stuff, too>

HTTPConnection go through a number of "states", which defines when a client
may legally make another request or fetch the response for a particular
request. This diagram details these state transitions:

    (null)
      |
      | HTTPConnection()
      v
    Idle
      |
      | putrequest()
      v
    Request-started
      |
      | ( putheader() )*  endheaders()
      v
    Request-sent
      |
      | response = getresponse()
      v
    Unread-response   [Response-headers-read]
      |\____________________
      |                     |
      | response.read()     | putrequest()
      v                     v
    Idle                  Req-started-unread-response
                     ______/|
                   /        |
   response.read() |        | ( putheader() )*  endheaders()
                   v        v
       Request-started    Req-sent-unread-response
                            |
                            | response.read()
                            v
                          Request-sent

This diagram presents the following rules:
  -- a second request may not be started until {response-headers-read}
  -- a response [object] cannot be retrieved until {request-sent}
  -- there is no differentiation between an unread response body and a
     partially read response body

Note: this enforcement is applied by the HTTPConnection class. The
      HTTPResponse class does not enforce this state machine, which
      implies sophisticated clients may accelerate the request/response
      pipeline. Caution should be taken, though: accelerating the states
      beyond the above pattern may imply knowledge of the server's
      connection-close behavior for certain requests. For example, it
      is impossible to tell whether the server will close the connection
      UNTIL the response headers have been read; this means that further
      requests cannot be placed into the pipeline until it is known that
      the server will NOT be closing the connection.

Logical State                  __state            __response
-------------                  -------            ----------
Idle                           _CS_IDLE           None
Request-started                _CS_REQ_STARTED    None
Request-sent                   _CS_REQ_SENT       None
Unread-response                _CS_IDLE           <response_class>
Req-started-unread-response    _CS_REQ_STARTED    <response_class>
Req-sent-unread-response       _CS_REQ_SENT       <response_class>
"""

import errno
import mimetools
import socket
import string

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__all__ = ["HTTP", "HTTPResponse", "HTTPConnection", "HTTPSConnection",
           "HTTPException", "NotConnected", "UnknownProtocol",
           "UnknownTransferEncoding", "IllegalKeywordArgument",
           "UnimplementedFileMode", "IncompleteRead", "InvalidURL",
           "ImproperConnectionState", "CannotSendRequest", "CannotSendHeader",
           "ResponseNotReady", "BadStatusLine", "error"]

HTTP_PORT = 80
HTTPS_PORT = 443

_UNKNOWN = 'UNKNOWN'

# connection states
_CS_IDLE = 'Idle'
_CS_REQ_STARTED = 'Request-started'
_CS_REQ_SENT = 'Request-sent'


class HTTPResponse:
    def __init__(self, sock, debuglevel=0):
        self.fp = sock.makefile('rb', 0)
        self.debuglevel = debuglevel

        self.msg = None

        # from the Status-Line of the response
        self.version = _UNKNOWN # HTTP-Version
        self.status = _UNKNOWN  # Status-Code
        self.reason = _UNKNOWN  # Reason-Phrase

        self.chunked = _UNKNOWN         # is "chunked" being used?
        self.chunk_left = _UNKNOWN      # bytes left to read in current chunk
        self.length = _UNKNOWN          # number of bytes left in response
        self.will_close = _UNKNOWN      # conn will close at end of response

    def begin(self):
        if self.msg is not None:
            # we've already started reading the response
            return

        line = self.fp.readline()
        if self.debuglevel > 0:
            print "reply:", repr(line)
        try:
            [version, status, reason] = string.split(line, None, 2)
        except ValueError:
            try:
                [version, status] = string.split(line, None, 1)
                reason = ""
            except ValueError:
                version = "HTTP/0.9"
                status = "200"
                reason = ""
        if version[:5] != 'HTTP/':
            self.close()
            raise BadStatusLine(line)

        # The status code is a three-digit number
        try:
            self.status = status = int(status)
            if status < 100 or status > 999:
                raise BadStatusLine(line)
        except ValueError:
            raise BadStatusLine(line)
        self.reason = string.strip(reason)

        if version == 'HTTP/1.0':
            self.version = 10
        elif startswith(version, 'HTTP/1.'):
            self.version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif version == 'HTTP/0.9':
            self.version = 9
        else:
            raise UnknownProtocol(version)

        if self.version == 9:
            self.msg = mimetools.Message(StringIO())
            return

        self.msg = mimetools.Message(self.fp, 0)
        if self.debuglevel > 0:
            for hdr in self.msg.headers:
                print "header:", hdr,

        # don't let the msg keep an fp
        self.msg.fp = None

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.msg.getheader('transfer-encoding')
        if tr_enc:
            if string.lower(tr_enc) != 'chunked':
                raise UnknownTransferEncoding()
            self.chunked = 1
            self.chunk_left = None
        else:
            self.chunked = 0

        # will the connection close at the end of the response?
        conn = self.msg.getheader('connection')
        if conn:
            conn = string.lower(conn)
            # a "Connection: close" will always close the connection. if we
            # don't see that and this is not HTTP/1.1, then the connection will
            # close unless we see a Keep-Alive header.
            self.will_close = string.find(conn, 'close') != -1 or \
                              ( self.version != 11 and \
                                not self.msg.getheader('keep-alive') )
        else:
            # for HTTP/1.1, the connection will always remain open
            # otherwise, it will remain open IFF we see a Keep-Alive header
            self.will_close = self.version != 11 and \
                              not self.msg.getheader('keep-alive')

        # do we have a Content-Length?
        # NOTE: RFC 2616, S4.4, #3 says we ignore this if tr_enc is "chunked"
        length = self.msg.getheader('content-length')
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
        else:
            self.length = None

        # does the body have a fixed length? (of zero)
        if (status == 204 or            # No Content
            status == 304 or            # Not Modified
            100 <= status < 200):       # 1xx codes
            self.length = 0

        # if the connection remains open, and we aren't using chunked, and
        # a content-length was not provided, then assume that the connection
        # WILL close.
        if not self.will_close and \
           not self.chunked and \
           self.length is None:
            self.will_close = 1

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def isclosed(self):
        # NOTE: it is possible that we will not ever call self.close(). This
        #       case occurs when will_close is TRUE, length is None, and we
        #       read up to the last byte, but NOT past it.
        #
        # IMPLIES: if will_close is FALSE, then self.close() will ALWAYS be
        #          called, meaning self.isclosed() is meaningful.
        return self.fp is None

    def read(self, amt=None):
        if self.fp is None:
            return ''

        if self.chunked:
            return self._read_chunked(amt)

        if amt is None:
            # unbounded read
            if self.will_close:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length
            self.length = self.length - amt

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)

        return s

    def _read_chunked(self, amt):
        assert self.chunked != _UNKNOWN
        chunk_left = self.chunk_left
        value = ''

        # XXX This accumulates chunks by repeated string concatenation,
        # which is not efficient as the number or size of chunks gets big.
        while 1:
            if chunk_left is None:
                line = self.fp.readline()
                i = string.find(line, ';')
                if i >= 0:
                    line = line[:i] # strip chunk-extensions
                chunk_left = string.atoi(line, 16)
                if chunk_left == 0:
                    break
            if amt is None:
                value = value + self._safe_read(chunk_left)
            elif amt < chunk_left:
                value = value + self._safe_read(amt)
                self.chunk_left = chunk_left - amt
                return value
            elif amt == chunk_left:
                value = value + self._safe_read(amt)
                self._safe_read(2)  # toss the CRLF at the end of the chunk
                self.chunk_left = None
                return value
            else:
                value = value + self._safe_read(chunk_left)
                amt = amt - chunk_left

            # we read the whole chunk, get another
            self._safe_read(2)      # toss the CRLF at the end of the chunk
            chunk_left = None

        # read and discard trailer up to the CRLF terminator
        ### note: we shouldn't have any trailers!
        while 1:
            line = self.fp.readline()
            if line == '\r\n':
                break

        # we read everything; close the "file"
        # XXX Shouldn't the client close the file?
        self.close()

        return value

    def _safe_read(self, amt):
        """Read the number of bytes requested, compensating for partial reads.

        Normally, we have a blocking socket, but a read() can be interrupted
        by a signal (resulting in a partial read).

        Note that we cannot distinguish between EOF and an interrupt when zero
        bytes have been read. IncompleteRead() will be raised in this
        situation.

        This function should be used when <amt> bytes "should" be present for
        reading. If the bytes are truly not available (due to EOF), then the
        IncompleteRead exception can be used to detect the problem.
        """
        s = ''
        while amt > 0:
            chunk = self.fp.read(amt)
            if not chunk:
                raise IncompleteRead(s)
            s = s + chunk
            amt = amt - len(chunk)
        return s

    def getheader(self, name, default=None):
        if self.msg is None:
            raise ResponseNotReady()
        return self.msg.getheader(name, default)


class HTTPConnection:

    _http_vsn = 11
    _http_vsn_str = 'HTTP/1.1'

    response_class = HTTPResponse
    default_port = HTTP_PORT
    auto_open = 1
    debuglevel = 0

    def __init__(self, host, port=None):
        self.sock = None
        self.__response = None
        self.__state = _CS_IDLE

        self._set_hostport(host, port)

    def _set_hostport(self, host, port):
        if port is None:
            i = string.find(host, ':')
            if i >= 0:
                try:
                    port = int(host[i+1:])
                except ValueError:
                    raise InvalidURL, "nonnumeric port: '%s'"%host[i+1:]
                host = host[:i]
            else:
                port = self.default_port
        self.host = host
        self.port = port

    def set_debuglevel(self, level):
        self.debuglevel = level

    def connect(self):
        """Connect to the host and port specified in __init__."""
        msg = "getaddrinfo returns an empty list"
        hostname, aliaslist, ipaddrlist = socket.gethostbyname_ex(self.host)
        for ipaddr in ipaddrlist:
            sa = (ipaddr, self.port)
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if self.debuglevel > 0:
                    print "connect: (%s, %s)" % (self.host, self.port)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0:
                    print 'connect fail:', (self.host, self.port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg

    def close(self):
        """Close the connection to the HTTP server."""
        if self.sock:
            self.sock.close()   # close it manually... there may be other refs
            self.sock = None
        if self.__response:
            self.__response.close()
            self.__response = None
        self.__state = _CS_IDLE

    def send(self, str):
        """Send `str' to the server."""
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        # send the data to the server. if we get a broken pipe, then close
        # the socket. we want to reconnect when somebody tries to send again.
        #
        # NOTE: we DO propagate the error, though, because we cannot simply
        #       ignore the error... the caller will know if they can retry.
        if self.debuglevel > 0:
            print "send:", repr(str)
        try:
            self.sock.send(str)
        except socket.error, v:
            if v[0] == 32:      # Broken pipe
                self.close()
            raise

    def putrequest(self, method, url, skip_host=0):
        """Send a request to the server.

        `method' specifies an HTTP request method, e.g. 'GET'.
        `url' specifies the object being requested, e.g. '/index.html'.
        """

        # check if a prior response has been completed
        if self.__response and self.__response.isclosed():
            self.__response = None

        #
        # in certain cases, we cannot issue another request on this connection.
        # this occurs when:
        #   1) we are in the process of sending a request.   (_CS_REQ_STARTED)
        #   2) a response to a previous request has signalled that it is going
        #      to close the connection upon completion.
        #   3) the headers for the previous response have not been read, thus
        #      we cannot determine whether point (2) is true.   (_CS_REQ_SENT)
        #
        # if there is no prior response, then we can request at will.
        #
        # if point (2) is true, then we will have passed the socket to the
        # response (effectively meaning, "there is no prior response"), and
        # will open a new one when a new request is made.
        #
        # Note: if a prior response exists, then we *can* start a new request.
        #       We are not allowed to begin fetching the response to this new
        #       request, however, until that prior response is complete.
        #
        if self.__state == _CS_IDLE:
            self.__state = _CS_REQ_STARTED
        else:
            raise CannotSendRequest()

        if not url:
            url = '/'
        str = '%s %s %s\r\n' % (method, url, self._http_vsn_str)

        try:
            self.send(str)
        except socket.error, v:
            # trap 'Broken pipe' if we're allowed to automatically reconnect
            if v[0] != 32 or not self.auto_open:
                raise
            # try one more time (the socket was closed; this will reopen)
            self.send(str)

        if self._http_vsn == 11:
            # Issue some standard headers for better HTTP/1.1 compliance

            if not skip_host:
                # this header is issued *only* for HTTP/1.1
                # connections. more specifically, this means it is
                # only issued when the client uses the new
                # HTTPConnection() class. backwards-compat clients
                # will be using HTTP/1.0 and those clients may be
                # issuing this header themselves. we should NOT issue
                # it twice; some web servers (such as Apache) barf
                # when they see two Host: headers

                # If we need a non-standard port,include it in the
                # header.  If the request is going through a proxy,
                # but the host of the actual URL, not the host of the
                # proxy.

                netloc = ''
                if startswith(url, 'http'):
                    nil, netloc, nil, nil, nil = urlsplit(url)

                if netloc:
                    self.putheader('Host', netloc)
                elif self.port == HTTP_PORT:
                    self.putheader('Host', self.host)
                else:
                    self.putheader('Host', "%s:%s" % (self.host, self.port))

            # note: we are assuming that clients will not attempt to set these
            #       headers since *this* library must deal with the
            #       consequences. this also means that when the supporting
            #       libraries are updated to recognize other forms, then this
            #       code should be changed (removed or updated).

            # we only want a Content-Encoding of "identity" since we don't
            # support encodings such as x-gzip or x-deflate.
            self.putheader('Accept-Encoding', 'identity')

            # we can accept "chunked" Transfer-Encodings, but no others
            # NOTE: no TE header implies *only* "chunked"
            #self.putheader('TE', 'chunked')

            # if TE is supplied in the header, then it must appear in a
            # Connection header.
            #self.putheader('Connection', 'TE')

        else:
            # For HTTP/1.0, the server will assume "not chunked"
            pass

    def putheader(self, header, value):
        """Send a request header line to the server.

        For example: h.putheader('Accept', 'text/html')
        """
        if self.__state != _CS_REQ_STARTED:
            raise CannotSendHeader()

        str = '%s: %s\r\n' % (header, value)
        self.send(str)

    def endheaders(self):
        """Indicate that the last header line has been sent to the server."""

        if self.__state == _CS_REQ_STARTED:
            self.__state = _CS_REQ_SENT
        else:
            raise CannotSendHeader()

        self.send('\r\n')

    def request(self, method, url, body=None, headers={}):
        """Send a complete request to the server."""

        try:
            self._send_request(method, url, body, headers)
        except socket.error, v:
            # trap 'Broken pipe' if we're allowed to automatically reconnect
            if v[0] != 32 or not self.auto_open:
                raise
            # try one more time
            self._send_request(method, url, body, headers)

    def _send_request(self, method, url, body, headers):
        # If headers already contains a host header, then define the
        # optional skip_host argument to putrequest().  The check is
        # harder because field names are case insensitive.
        if (headers.has_key('Host')
            or filter(lambda x: string.lower(x) == "host", headers.keys())):
            self.putrequest(method, url, skip_host=1)
        else:
            self.putrequest(method, url)

        if body:
            self.putheader('Content-Length', str(len(body)))
        for hdr, value in headers.items():
            self.putheader(hdr, value)
        self.endheaders()

        if body:
            self.send(body)

    def getresponse(self):
        "Get the response from the server."

        # check if a prior response has been completed
        if self.__response and self.__response.isclosed():
            self.__response = None

        #
        # if a prior response exists, then it must be completed (otherwise, we
        # cannot read this response's header to determine the connection-close
        # behavior)
        #
        # note: if a prior response existed, but was connection-close, then the
        # socket and response were made independent of this HTTPConnection
        # object since a new request requires that we open a whole new
        # connection
        #
        # this means the prior response had one of two states:
        #   1) will_close: this connection was reset and the prior socket and
        #                  response operate independently
        #   2) persistent: the response was retained and we await its
        #                  isclosed() status to become true.
        #
        if self.__state != _CS_REQ_SENT or self.__response:
            raise ResponseNotReady()

        if self.debuglevel > 0:
            response = self.response_class(self.sock, self.debuglevel)
        else:
            response = self.response_class(self.sock)

        response.begin()
        self.__state = _CS_IDLE

        if response.will_close:
            # this effectively passes the connection to the response
            self.close()
        else:
            # remember this, so we can tell when it is complete
            self.__response = response

        return response


class FakeSocket:
    def __init__(self, sock, ssl):
        self.__sock = sock
        self.__ssl = ssl

    def makefile(self, mode, bufsize=None):
        """Return a readable file-like object with data from socket.

        This method offers only partial support for the makefile
        interface of a real socket.  It only supports modes 'r' and
        'rb' and the bufsize argument is ignored.

        The returned object contains *all* of the file data
        """
        if mode != 'r' and mode != 'rb':
            raise UnimplementedFileMode()

        msgbuf = []
        while 1:
            try:
                buf = self.__ssl.read()
            except socket.sslerror, err:
                if err[0] == 'EOF':
                    break
                raise
            except socket.error, err:
                if err[0] == errno.EINTR:
                    continue
                raise
            if buf == '':
                break
            msgbuf.append(buf)
        return StringIO(string.join(msgbuf, ""))

    def send(self, stuff, flags = 0):
        return self.__ssl.write(stuff)

    def sendall(self, stuff, flags = 0):
        return self.__ssl.write(stuff)

    def recv(self, len = 1024, flags = 0):
        return self.__ssl.read(len)

    def __getattr__(self, attr):
        return getattr(self.__sock, attr)


class HTTPSConnection(HTTPConnection):
    "This class allows communication via SSL."

    default_port = HTTPS_PORT

    def __init__(self, host, port=None, **x509):
        keys = x509.keys()
        try:
            keys.remove('key_file')
        except ValueError:
            pass
        try:
            keys.remove('cert_file')
        except ValueError:
            pass
        if keys:
            raise IllegalKeywordArgument()
        HTTPConnection.__init__(self, host, port)
        self.key_file = x509.get('key_file')
        self.cert_file = x509.get('cert_file')

    def connect(self):
        "Connect to a host on a given (SSL) port."

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        realsock = sock
        if hasattr(sock, "_sock"):
            realsock = sock._sock
        # misa: XXX x509 client-side is broken in 2.2 anyway
        ssl = socket.ssl(realsock)
        self.sock = FakeSocket(sock, ssl)


class HTTP:
    "Compatibility class with httplib.py from 1.5."

    _http_vsn = 10
    _http_vsn_str = 'HTTP/1.0'

    debuglevel = 0

    _connection_class = HTTPConnection

    def __init__(self, host='', port=None):
        "Provide a default host, since the superclass requires one."

        # some joker passed 0 explicitly, meaning default port
        if port == 0:
            port = None

        # Note that we may pass an empty string as the host; this will throw
        # an error when we attempt to connect. Presumably, the client code
        # will call connect before then, with a proper host.
        self._setup(self._connection_class(host, port))

    def _setup(self, conn):
        self._conn = conn

        # set up delegation to flesh out interface
        self.send = conn.send
        self.putrequest = conn.putrequest
        self.endheaders = conn.endheaders
        self.set_debuglevel = conn.set_debuglevel

        conn._http_vsn = self._http_vsn
        conn._http_vsn_str = self._http_vsn_str

        self.file = None

    def connect(self, host=None, port=None):
        "Accept arguments to set the host/port, since the superclass doesn't."

        if host is not None:
            self._conn._set_hostport(host, port)
        self._conn.connect()

    def getfile(self):
        "Provide a getfile, since the superclass' does not use this concept."
        return self.file

    def putheader(self, header, *values):
        "The superclass allows only one value argument."
        self._conn.putheader(header, string.join(values, '\r\n\t'))

    def getreply(self):
        """Compat definition since superclass does not define it.

        Returns a tuple consisting of:
        - server status code (e.g. '200' if all goes well)
        - server "reason" corresponding to status code
        - any RFC822 headers in the response from the server
        """
        try:
            response = self._conn.getresponse()
        except BadStatusLine, e:
            ### hmm. if getresponse() ever closes the socket on a bad request,
            ### then we are going to have problems with self.sock

            ### should we keep this behavior? do people use it?
            # keep the socket open (as a file), and return it
            self.file = self._conn.sock.makefile('rb', 0)

            # close our socket -- we want to restart after any protocol error
            self.close()

            self.headers = None
            return -1, e.line, None

        self.headers = response.msg
        self.file = response.fp
        return response.status, response.reason, response.msg

    def close(self):
        self._conn.close()

        # note that self.file == response.fp, which gets closed by the
        # superclass. just clear the object ref here.
        ### hmm. messy. if status==-1, then self.file is owned by us.
        ### well... we aren't explicitly closing, but losing this ref will
        ### do it
        self.file = None

if hasattr(socket, 'ssl'):
    class HTTPS(HTTP):
        """Compatibility with 1.5 httplib interface

        Python 1.5.2 did not have an HTTPS class, but it defined an
        interface for sending http requests that is also useful for
        https.
        """

        _connection_class = HTTPSConnection

        def __init__(self, host='', port=None, **x509):
            # provide a default host, pass the X509 cert info

            # urf. compensate for bad input.
            if port == 0:
                port = None
            self._setup(apply(self._connection_class, (host, port), x509))

            # we never actually use these for anything, but we keep them
            # here for compatibility with post-1.5.2 CVS.
            self.key_file = x509.get('key_file')
            self.cert_file = x509.get('cert_file')


class HTTPException(Exception):
    pass

class NotConnected(HTTPException):
    pass

class InvalidURL(HTTPException):
    pass

class UnknownProtocol(HTTPException):
    def __init__(self, version):
        self.version = version

class UnknownTransferEncoding(HTTPException):
    pass

class IllegalKeywordArgument(HTTPException):
    pass

class UnimplementedFileMode(HTTPException):
    pass

class IncompleteRead(HTTPException):
    def __init__(self, partial):
        self.partial = partial

class ImproperConnectionState(HTTPException):
    pass

class CannotSendRequest(ImproperConnectionState):
    pass

class CannotSendHeader(ImproperConnectionState):
    pass

class ResponseNotReady(ImproperConnectionState):
    pass

class BadStatusLine(HTTPException):
    def __init__(self, line):
        self.line = line

# for backwards compatibility
error = HTTPException


#
# snarfed from httplib.py for now...
#
def test():
    """Test this module.

    The test consists of retrieving and displaying the Python
    home page, along with the error code and error string returned
    by the www.python.org server.
    """

    import sys
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], 'd')
    dl = 0
    for o, a in opts:
        if o == '-d': dl = dl + 1
    host = 'www.python.org'
    selector = '/'
    if args[0:]: host = args[0]
    if args[1:]: selector = args[1]
    h = HTTP()
    h.set_debuglevel(dl)
    h.connect(host)
    h.putrequest('GET', selector)
    h.endheaders()
    status, reason, headers = h.getreply()
    print 'status =', status
    print 'reason =', reason
    print
    if headers:
        for header in headers.headers: print string.strip(header)
    print
    print h.getfile().read()

    # minimal test that code to extract host from url works
    class HTTP11(HTTP):
        _http_vsn = 11
        _http_vsn_str = 'HTTP/1.1'

    h = HTTP11('www.python.org')
    h.putrequest('GET', 'http://www.python.org/~jeremy/')
    h.endheaders()
    h.getreply()
    h.close()

    if hasattr(socket, 'ssl'):
        host = 'sourceforge.net'
        selector = '/projects/python'
        hs = HTTPS()
        hs.connect(host)
        hs.putrequest('GET', selector)
        hs.endheaders()
        status, reason, headers = hs.getreply()
        print 'status =', status
        print 'reason =', reason
        print
        if headers:
            for header in headers.headers: print string.strip(header)
        print
        print hs.getfile().read()

# Stuff used by urlsplit
MAX_CACHE_SIZE = 20
_parse_cache = {}

uses_netloc = ['ftp', 'http', 'gopher', 'nntp', 'telnet', 'wais',
               'file',
               'https', 'shttp', 'snews',
               'prospero', 'rtsp', 'rtspu', '']
uses_query = ['http', 'wais',
              'https', 'shttp',
              'gopher', 'rtsp', 'rtspu', 'sip',
              '']
uses_fragment = ['ftp', 'hdl', 'http', 'gopher', 'news', 'nntp', 'wais',
                 'https', 'shttp', 'snews',
                 'file', 'prospero', '']

# Characters valid in scheme names
scheme_chars = ('abcdefghijklmnopqrstuvwxyz'
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                '0123456789'
                '+-.')


def clear_cache():
    """Clear the parse cache."""
    global _parse_cache
    _parse_cache = {}

# urlsplit does not exist in python 1.5
def urlsplit(url, scheme='', allow_fragments=1):
    """Parse a URL into 5 components:
    <scheme>://<netloc>/<path>?<query>#<fragment>
    Return a 5-tuple: (scheme, netloc, path, query, fragment).
    Note that we don't break the components up in smaller bits
    (e.g. netloc is a single string) and we don't expand % escapes."""
    key = url, scheme, allow_fragments
    cached = _parse_cache.get(key, None)
    if cached:
        return cached
    if len(_parse_cache) >= MAX_CACHE_SIZE: # avoid runaway growth
        clear_cache()
    netloc = query = fragment = ''
    i = string.find(url, ':')
    if i > 0:
        if url[:i] == 'http': # optimize the common case
            scheme = string.lower(url[:i])
            url = url[i+1:]
            if url[:2] == '//':
                i = string.find(url, '/', 2)
                if i < 0:
                    i = string.find(url, '#')
                    if i < 0:
                        i = len(url)
                netloc = url[2:i]
                url = url[i:]
            if allow_fragments and '#' in url:
                url, fragment = string.split(url, '#', 1)
            if '?' in url:
                url, query = string.split(url, '?', 1)
            tuple = scheme, netloc, url, query, fragment
            _parse_cache[key] = tuple
            return tuple
        for c in url[:i]:
            if c not in scheme_chars:
                break
        else:
            scheme, url = string.lower(url[:i]), url[i+1:]
    if scheme in uses_netloc:
        if url[:2] == '//':
            i = string.find(url, '/', 2)
            if i < 0:
                i = len(url)
            netloc, url = url[2:i], url[i:]
    if allow_fragments and scheme in uses_fragment and '#' in url:
        url, fragment = string.split(url, '#', 1)
    if scheme in uses_query and '?' in url:
        url, query = string.split(url, '?', 1)
    tuple = scheme, netloc, url, query, fragment
    _parse_cache[key] = tuple
    return tuple

# startswith not provided by the string module
def startswith(s, prefix):
    return s[:len(prefix)] == prefix 

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = _internal_xmlrpclib
#
# XML-RPC CLIENT LIBRARY
# $Id: _internal_xmlrpclib.py 89051 2005-11-30 23:16:43Z misa $
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Notes:
# this version is designed to work with Python 1.5.2 or newer.
# unicode encoding support requires at least Python 1.6.
# experimental HTTPS requires Python 2.0 built with SSL sockets.
# expat parser support requires Python 2.0 with pyexpat support.
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

# --------------------------------------------------------------------
# Internal stuff

try:
    unicode
except NameError:
    unicode = None # unicode support not available

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
            return str(string)
        except UnicodeError:
            return string
else:
    def _stringify(string):
        return string

__version__ = "1.0.1"

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

##
# Wrapper for XML-RPC DateTime values.  This converts a time value to
# the format used by XML-RPC.
# <p>
# The value can be given as a string in the format
# "yyyymmddThh:mm:ss", as a 9-item time tuple (as returned by
# time.localtime()), or an integer value (as returned by time.time()).
# The wrapper uses time.localtime() to convert an integer to a time
# tuple.
#
# @param value The time, given as an ISO 8601 string, a time
#              tuple, or a integer time value.

class DateTime:
    """DateTime wrapper for an ISO 8601 string or time tuple or
    localtime integer value to generate 'dateTime.iso8601' XML-RPC
    value.
    """

    def __init__(self, value=0):
        if not isinstance(value, StringType):
            if not isinstance(value, TupleType):
                if value == 0:
                    value = time.time()
                value = time.localtime(value)
            value = time.strftime("%Y%m%dT%H:%M:%S", value)
        self.value = value

    def __cmp__(self, other):
        if isinstance(other, DateTime):
            other = other.value
        return cmp(self.value, other)

    ##
    # Get date/time value.
    #
    # @return Date/time value, as an ISO 8601 string.

    def __str__(self):
        return self.value

    def __repr__(self):
        return "<DateTime %s at %x>" % (repr(self.value), id(self))

    def decode(self, data):
        self.value = string.strip(data)

    def encode(self, out):
        out.write("<value><dateTime.iso8601>")
        out.write(self.value)
        out.write("</dateTime.iso8601></value>\n")

def _datetime(data):
    # decode xml element contents into a DateTime structure.
    value = DateTime()
    value.decode(data)
    return value

##
# Wrapper for binary data.  This can be used to transport any kind
# of binary data over XML-RPC, using BASE64 encoding.
#
# @param data An 8-bit string containing arbitrary data.

class Binary:
    """Wrapper for binary data."""

    def __init__(self, data=None):
        self.data = data

    ##
    # Get buffer contents.
    #
    # @return Buffer contents, as an 8-bit string.

    def __str__(self):
        return self.data or ""

    def __cmp__(self, other):
        if isinstance(other, Binary):
            other = other.data
        return cmp(self.data, other)

    def decode(self, data):
        import base64
        self.data = base64.decodestring(data)

    def encode(self, out):
        import base64, StringIO
        out.write("<value><base64>\n")
        base64.encode(StringIO.StringIO(self.data), out)
        out.write("</base64></value>\n")

def _binary(data):
    # decode xml element contents into a Binary structure
    value = Binary()
    value.decode(data)
    return value

WRAPPERS = DateTime, Binary, Boolean

# --------------------------------------------------------------------
# XML parsers

try:
    # optional xmlrpclib accelerator.  for more information on this
    # component, contact info@pythonware.com
    import _xmlrpclib
    FastParser = _xmlrpclib.Parser
    FastUnmarshaller = _xmlrpclib.Unmarshaller
except (AttributeError, ImportError):
    FastParser = FastUnmarshaller = None

try:
    import _xmlrpclib
    FastMarshaller = _xmlrpclib.Marshaller
except (AttributeError, ImportError):
    FastMarshaller = None

#
# the SGMLOP parser is about 15x faster than Python's builtin
# XML parser.  SGMLOP sources can be downloaded from:
#
#     http://www.pythonware.com/products/xml/sgmlop.htm
#

try:
    import sgmlop
    if not hasattr(sgmlop, "XMLParser"):
        raise ImportError
except ImportError:
    SgmlopParser = None # sgmlop accelerator not available
else:
    class SgmlopParser:
        def __init__(self, target):

            # setup callbacks
            self.finish_starttag = target.start
            self.finish_endtag = target.end
            self.handle_data = target.data
            self.handle_xml = target.xml

            # activate parser
            self.parser = sgmlop.XMLParser()
            self.parser.register(self)
            self.feed = self.parser.feed
            self.entity = {
                "amp": "&", "gt": ">", "lt": "<",
                "apos": "'", "quot": '"'
                }

        def close(self):
            try:
                self.parser.close()
            finally:
                self.parser = self.feed = None # nuke circular reference

        def handle_proc(self, tag, attr):
            m = re.search("encoding\s*=\s*['\"]([^\"']+)[\"']", attr)
            if m:
                self.handle_xml(m.group(1), 1)

        def handle_entityref(self, entity):
            # <string> entity
            try:
                self.handle_data(self.entity[entity])
            except KeyError:
                self.handle_data("&%s;" % entity)

try:
    from xml.parsers import expat
    if not hasattr(expat, "ParserCreate"):
        raise ImportError
except ImportError:
    ExpatParser = None # expat not available
else:
    class ExpatParser:
        # fast expat parser for Python 2.0 and later.  this is about
        # 50% slower than sgmlop, on roundtrip testing
        def __init__(self, target):
            self._parser = parser = expat.ParserCreate(None, None)
            self._target = target
            parser.StartElementHandler = target.start
            parser.EndElementHandler = target.end
            parser.CharacterDataHandler = target.data
            encoding = None
            if not parser.returns_unicode:
                encoding = "utf-8"
            target.xml(encoding, None)

        def feed(self, data):
            self._parser.Parse(data, 0)

        def close(self):
            self._parser.Parse("", 1) # end of data
            del self._target, self._parser # get rid of circular references

class SlowParser:
    """Default XML parser (based on xmllib.XMLParser)."""
    # this is about 10 times slower than sgmlop, on roundtrip
    # testing.
    def __init__(self, target):
        import xmllib # lazy subclassing (!)
        if xmllib.XMLParser not in SlowParser.__bases__:
            SlowParser.__bases__ = (xmllib.XMLParser,)
        self.handle_xml = target.xml
        self.unknown_starttag = target.start
        self.handle_data = target.data
        self.handle_cdata = target.data
        self.unknown_endtag = target.end
        try:
            xmllib.XMLParser.__init__(self, accept_utf8=1)
        except TypeError:
            xmllib.XMLParser.__init__(self) # pre-2.0

# --------------------------------------------------------------------
# XML-RPC marshalling and unmarshalling code

##
# XML-RPC marshaller.
#
# @param encoding Default encoding for 8-bit strings.  The default
#     value is None (interpreted as UTF-8).
# @see dumps

class Marshaller:
    """Generate an XML-RPC params chunk from a Python data structure.

    Create a Marshaller instance for each set of parameters, and use
    the "dumps" method to convert your data (represented as a tuple)
    to an XML-RPC params chunk.  To write a fault response, pass a
    Fault instance instead.  You may prefer to use the "dumps" module
    function for this purpose.
    """

    # by the way, if you don't understand what's going on in here,
    # that's perfectly ok.

    def __init__(self, encoding=None):
        self.memo = {}
        self.data = None
        self.encoding = encoding

    dispatch = {}

    def dumps(self, values):
        out = []
        write = out.append
        dump = self.__dump
        if isinstance(values, Fault):
            # fault instance
            write("<fault>\n")
            dump(vars(values), write)
            write("</fault>\n")
        else:
            # parameter block
            # FIXME: the xml-rpc specification allows us to leave out
            # the entire <params> block if there are no parameters.
            # however, changing this may break older code (including
            # old versions of xmlrpclib.py), so this is better left as
            # is for now.  See @XMLRPC3 for more information. /F
            write("<params>\n")
            for v in values:
                write("<param>\n")
                dump(v, write)
                write("</param>\n")
            write("</params>\n")
        result = string.join(out, "")
        return result

    def __dump(self, value, write):
        try:
            f = self.dispatch[type(value)]
        except KeyError:
            raise TypeError, "cannot marshal %s objects" % type(value)
        else:
            f(self, value, write)

    def dump_int(self, value, write):
        # in case ints are > 32 bits
        if value > MAXINT or value < MININT:
            raise OverflowError, "int exceeds XML-RPC limits"
        write("<value><int>")
        write(str(value))
        write("</int></value>\n")
    dispatch[IntType] = dump_int

    def dump_long(self, value, write):
        if value > MAXINT or value < MININT:
            raise OverflowError, "long int exceeds XML-RPC limits"
        write("<value><int>")
        write(str(int(value)))
        write("</int></value>\n")
    dispatch[LongType] = dump_long

    def dump_double(self, value, write):
        write("<value><double>")
        write(repr(value))
        write("</double></value>\n")
    dispatch[FloatType] = dump_double

    def dump_string(self, value, write, escape=escape):
        write("<value><string>")
        write(escape(value))
        write("</string></value>\n")
    dispatch[StringType] = dump_string

    if unicode:
        def dump_unicode(self, value, write, escape=escape):
            value = value.encode(self.encoding)
            write("<value><string>")
            write(escape(value))
            write("</string></value>\n")
        dispatch[UnicodeType] = dump_unicode

    def dump_array(self, value, write):
        i = id(value)
        if self.memo.has_key(i):
            raise TypeError, "cannot marshal recursive sequences"
        self.memo[i] = None
        dump = self.__dump
        write("<value><array><data>\n")
        for v in value:
            dump(v, write)
        write("</data></array></value>\n")
        del self.memo[i]
    dispatch[TupleType] = dump_array
    dispatch[ListType] = dump_array

    def dump_struct(self, value, write, escape=escape):
        i = id(value)
        if self.memo.has_key(i):
            raise TypeError, "cannot marshal recursive dictionaries"
        self.memo[i] = None
        dump = self.__dump
        write("<value><struct>\n")
        for k in value.keys():
            write("<member>\n")
            if type(k) is not StringType:
                raise TypeError, "dictionary key must be string"
            write("<name>%s</name>\n" % escape(k))
            dump(value[k], write)
            write("</member>\n")
        write("</struct></value>\n")
        del self.memo[i]
    dispatch[DictType] = dump_struct

    def dump_instance(self, value, write):
        # check for special wrappers
        if value.__class__ in WRAPPERS:
            self.write = write
            value.encode(self)
            del self.write
        else:
            # store instance attributes as a struct (really?)
            self.dump_struct(value.__dict__, write)
    dispatch[InstanceType] = dump_instance

##
# XML-RPC unmarshaller.
#
# @see loads

class Unmarshaller:
    """Unmarshal an XML-RPC response, based on incoming XML event
    messages (start, data, end).  Call close() to get the resulting
    data structure.

    Note that this reader is fairly tolerant, and gladly accepts bogus
    XML-RPC data without complaining (but not bogus XML).
    """

    # and again, if you don't understand what's going on in here,
    # that's perfectly ok.

    def __init__(self):
        self._type = None
        self._stack = []
        self._marks = []
        self._data = []
        self._methodname = None
        self._encoding = "utf-8"
        self.append = self._stack.append

    def close(self):
        # return response tuple and target method
        if self._type is None or self._marks:
            raise ResponseError()
        if self._type == "fault":
            raise apply(Fault, (), self._stack[0])
        return tuple(self._stack)

    def getmethodname(self):
        return self._methodname

    #
    # event handlers

    def xml(self, encoding, standalone):
        self._encoding = encoding
        # FIXME: assert standalone == 1 ???

    def start(self, tag, attrs):
        # prepare to handle this element
        if tag == "array" or tag == "struct":
            self._marks.append(len(self._stack))
        self._data = []
        self._value = (tag == "value")

    def data(self, text):
        self._data.append(text)

    def end(self, tag, join=string.join):
        # call the appropriate end tag handler
        try:
            f = self.dispatch[tag]
        except KeyError:
            pass # unknown tag ?
        else:
            return f(self, join(self._data, ""))

    #
    # accelerator support

    def end_dispatch(self, tag, data):
        # dispatch data
        try:
            f = self.dispatch[tag]
        except KeyError:
            pass # unknown tag ?
        else:
            return f(self, data)

    #
    # element decoders

    dispatch = {}

    def end_boolean(self, data):
        if data == "0":
            self.append(False)
        elif data == "1":
            self.append(True)
        else:
            raise TypeError, "bad boolean value"
        self._value = 0
    dispatch["boolean"] = end_boolean

    def end_int(self, data):
        self.append(int(data))
        self._value = 0
    dispatch["i4"] = end_int
    dispatch["int"] = end_int

    def end_double(self, data):
        self.append(float(data))
        self._value = 0
    dispatch["double"] = end_double

    def end_string(self, data):
        if self._encoding:
            data = _decode(data, self._encoding)
        self.append(_stringify(data))
        self._value = 0
    dispatch["string"] = end_string
    dispatch["name"] = end_string # struct keys are always strings

    def end_array(self, data):
        mark = self._marks.pop()
        # map arrays to Python lists
        self._stack[mark:] = [self._stack[mark:]]
        self._value = 0
    dispatch["array"] = end_array

    def end_struct(self, data):
        mark = self._marks.pop()
        # map structs to Python dictionaries
        dict = {}
        items = self._stack[mark:]
        for i in range(0, len(items), 2):
            dict[_stringify(items[i])] = items[i+1]
        self._stack[mark:] = [dict]
        self._value = 0
    dispatch["struct"] = end_struct

    def end_base64(self, data):
        value = Binary()
        value.decode(data)
        self.append(value)
        self._value = 0
    dispatch["base64"] = end_base64

    def end_dateTime(self, data):
        value = DateTime()
        value.decode(data)
        self.append(value)
    dispatch["dateTime.iso8601"] = end_dateTime

    def end_value(self, data):
        # if we stumble upon a value element with no internal
        # elements, treat it as a string element
        if self._value:
            self.end_string(data)
    dispatch["value"] = end_value

    def end_params(self, data):
        self._type = "params"
    dispatch["params"] = end_params

    def end_fault(self, data):
        self._type = "fault"
    dispatch["fault"] = end_fault

    def end_methodName(self, data):
        if self._encoding:
            data = _decode(data, self._encoding)
        self._methodname = data
        self._type = "methodName" # no params
    dispatch["methodName"] = end_methodName


# --------------------------------------------------------------------
# convenience functions

##
# Create a parser object, and connect it to an unmarshalling instance.
# This function picks the fastest available XML parser.
#
# return A (parser, unmarshaller) tuple.

def getparser():
    """getparser() -> parser, unmarshaller

    Create an instance of the fastest available parser, and attach it
    to an unmarshalling object.  Return both objects.
    """
    if FastParser and FastUnmarshaller:
        target = FastUnmarshaller(True, False, _binary, _datetime, Fault)
        parser = FastParser(target)
    else:
        target = Unmarshaller()
        if FastParser:
            parser = FastParser(target)
        elif SgmlopParser:
            parser = SgmlopParser(target)
        elif ExpatParser:
            parser = ExpatParser(target)
        else:
            parser = SlowParser(target)
    return parser, target

##
# Convert a Python tuple or a Fault instance to an XML-RPC packet.
#
# @def dumps(params, **options)
# @param params A tuple or Fault instance.
# @keyparam methodname If given, create a methodCall request for
#     this method name.
# @keyparam methodresponse If given, create a methodResponse packet.
#     If used with a tuple, the tuple must be a singleton (that is,
#     it must contain exactly one element).
# @keyparam encoding The packet encoding.
# @return A string containing marshalled data.

def dumps(params, methodname=None, methodresponse=None, encoding=None):
    """data [,options] -> marshalled data

    Convert an argument tuple or a Fault instance to an XML-RPC
    request (or response, if the methodresponse option is used).

    In addition to the data object, the following options can be given
    as keyword arguments:

        methodname: the method name for a methodCall packet

        methodresponse: true to create a methodResponse packet.
        If this option is used with a tuple, the tuple must be
        a singleton (i.e. it can contain only one element).

        encoding: the packet encoding (default is UTF-8)

    All 8-bit strings in the data structure are assumed to use the
    packet encoding.  Unicode strings are automatically converted,
    where necessary.
    """

    assert isinstance(params, TupleType) or isinstance(params, Fault),\
           "argument must be tuple or Fault instance"

    if isinstance(params, Fault):
        methodresponse = 1
    elif methodresponse and isinstance(params, TupleType):
        assert len(params) == 1, "response tuple must be a singleton"

    if not encoding:
        encoding = "utf-8"

    if FastMarshaller:
        m = FastMarshaller(encoding)
    else:
        m = Marshaller(encoding)

    data = m.dumps(params)

    if encoding != "utf-8":
        xmlheader = "<?xml version='1.0' encoding='%s'?>\n" % str(encoding)
    else:
        xmlheader = "<?xml version='1.0'?>\n" # utf-8 is default

    # standard XML-RPC wrappings
    if methodname:
        # a method call
        if not isinstance(methodname, StringType):
            methodname = methodname.encode(encoding)
        data = (
            xmlheader,
            "<methodCall>\n"
            "<methodName>", methodname, "</methodName>\n",
            data,
            "</methodCall>\n"
            )
    elif methodresponse:
        # a method response, or a fault structure
        data = (
            xmlheader,
            "<methodResponse>\n",
            data,
            "</methodResponse>\n"
            )
    else:
        return data # return as is
    return string.join(data, "")

##
# Convert an XML-RPC packet to a Python object.  If the XML-RPC packet
# represents a fault condition, this function raises a Fault exception.
#
# @param data An XML-RPC packet, given as an 8-bit string.
# @return A tuple containing the the unpacked data, and the method name
#     (None if not present).
# @see Fault

def loads(data):
    """data -> unmarshalled data, method name

    Convert an XML-RPC packet to unmarshalled data plus a method
    name (None if not present).

    If the XML-RPC packet represents a fault condition, this function
    raises a Fault exception.
    """
    p, u = getparser()
    p.feed(data)
    p.close()
    return u.close(), u.getmethodname()


# --------------------------------------------------------------------
# request dispatcher

class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
        return self.__send(self.__name, args)

##
# Standard transport class for XML-RPC over HTTP.
# <p>
# You can create custom transports by subclassing this method, and
# overriding selected methods.

class Transport:
    """Handles an HTTP transaction to an XML-RPC server."""

    # client identifier (may be overridden)
    user_agent = "xmlrpclib.py/%s (by www.pythonware.com)" % __version__

    ##
    # Send a complete request, and parse the response.
    #
    # @param host Target host.
    # @param handler Target PRC handler.
    # @param request_body XML-RPC request body.
    # @param verbose Debugging flag.
    # @return Parsed response.

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        errcode, errmsg, headers = h.getreply()

        if errcode != 200:
            raise ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock)

    ##
    # Create parser.
    #
    # @return A 2-tuple containing a parser and a unmarshaller.

    def getparser(self):
        # get parser and unmarshaller
        return getparser()

    ##
    # Get authorization info from host parameter
    # Host may be a string, or a (host, x509-dict) tuple; if a string,
    # it is checked for a "user:pw@host" format, and a "Basic
    # Authentication" header is added if appropriate.
    #
    # @param host Host descriptor (URL or (URL, x509 info) tuple).
    # @return A 3-tuple containing (actual host, extra headers,
    #     x509 info).  The header and x509 fields may be None.

    def get_host_info(self, host):

        x509 = {}
        if isinstance(host, TupleType):
            host, x509 = host

        import urllib
        auth, host = urllib.splituser(host)

        if auth:
            import base64
            auth = base64.encodestring(urllib.unquote(auth))
            auth = string.join(string.split(auth), "") # get rid of whitespace
            extra_headers = [
                ("Authorization", "Basic " + auth)
                ]
        else:
            extra_headers = None

        return host, extra_headers, x509

    ##
    # Connect to server.
    #
    # @param host Target host.
    # @return A connection handle.

    def make_connection(self, host):
        # create a HTTP connection object from a host descriptor
        import httplib
        host, extra_headers, x509 = self.get_host_info(host)
        return httplib.HTTP(host)

    ##
    # Send request header.
    #
    # @param connection Connection handle.
    # @param handler Target RPC handler.
    # @param request_body XML-RPC body.

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler)

    ##
    # Send host name.
    #
    # @param connection Connection handle.
    # @param host Host name.

    def send_host(self, connection, host):
        host, extra_headers, x509 = self.get_host_info(host)
        connection.putheader("Host", host)
        if extra_headers:
            if isinstance(extra_headers, DictType):
                extra_headers = extra_headers.items()
            for key, value in extra_headers:
                connection.putheader(key, value)

    ##
    # Send user-agent identifier.
    #
    # @param connection Connection handle.

    def send_user_agent(self, connection):
        connection.putheader("User-Agent", self.user_agent)

    ##
    # Send request body.
    #
    # @param connection Connection handle.
    # @param request_body XML-RPC request body.

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/xml")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    ##
    # Parse response.
    #
    # @param file Stream.
    # @return Response tuple and target method.

    def parse_response(self, file):
        # compatibility interface
        return self._parse_response(file, None)

    ##
    # Parse response (alternate interface).  This is similar to the
    # parse_response method, but also provides direct access to the
    # underlying socket object (where available).
    #
    # @param file Stream.
    # @param sock Socket handle (or None, if the socket object
    #    could not be accessed).
    # @return Response tuple and target method.

    def _parse_response(self, file, sock):
        # read response from input file/socket, and parse it

        p, u = self.getparser()

        while 1:
            if sock:
                response = sock.recv(1024)
            else:
                response = file.read(1024)
            if not response:
                break
            if self.verbose:
                print "body:", repr(response)
            p.feed(response)

        file.close()
        p.close()

        return u.close()

##
# Standard transport class for XML-RPC over HTTPS.

class SafeTransport(Transport):
    """Handles an HTTPS transaction to an XML-RPC server."""

    # FIXME: mostly untested

    def make_connection(self, host):
        # create a HTTPS connection object from a host descriptor
        # host may be a string, or a (host, x509-dict) tuple
        import httplib
        host, extra_headers, x509 = self.get_host_info(host)
        try:
            HTTPS = httplib.HTTPS
        except AttributeError:
            raise NotImplementedError,\
                  "your version of httplib doesn't support HTTPS"
        else:
            return apply(HTTPS, (host, None), x509 or {})

    def send_host(self, connection, host):
        if isinstance(host, TupleType):
            host, x509 = host
        connection.putheader("Host", host)

##
# Standard server proxy.  This class establishes a virtual connection
# to an XML-RPC server.
# <p>
# This class is available as ServerProxy and Server.  New code should
# use ServerProxy, to avoid confusion.
#
# @def ServerProxy(uri, **options)
# @param uri The connection point on the server.
# @keyparam transport A transport factory, compatible with the
#    standard transport class.
# @keyparam encoding The default encoding used for 8-bit strings
#    (default is UTF-8).
# @keyparam verbose Use a true value to enable debugging output.
#    (printed to standard output).
# @see Transport

class ServerProxy:
    """uri [,options] -> a logical connection to an XML-RPC server

    uri is the connection point on the server, given as
    scheme://host/target.

    The standard implementation always supports the "http" scheme.  If
    SSL socket support is available (Python 2.0), it also supports
    "https".

    If the target part and the slash preceding it are both omitted,
    "/RPC2" is assumed.

    The following options can be given as keyword arguments:

        transport: a transport factory
        encoding: the request encoding (default is UTF-8)

    All 8-bit strings passed to the server proxy are assumed to use
    the given encoding.
    """

    def __init__(self, uri, transport=None, encoding=None, verbose=0):
        # establish a "logical" server connection

        # get the url
        import urllib
        type, uri = urllib.splittype(uri)
        if type not in ("http", "https"):
            raise IOError, "unsupported XML-RPC protocol"
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            self.__handler = "/RPC2"

        if transport is None:
            if type == "https":
                transport = SafeTransport()
            else:
                transport = Transport()
        self.__transport = transport

        self.__encoding = encoding
        self.__verbose = verbose

    def __request(self, methodname, params):
        # call a method on the remote server

        request = dumps(params, methodname, encoding=self.__encoding)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
            )

        if len(response) == 1:
            response = response[0]

        return response

    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)

    # note: to call a remote object with an non-standard name, use
    # result getattr(server, "strange-python-name")(args)

# compatibility

Server = ServerProxy

# --------------------------------------------------------------------
# test code

if __name__ == "__main__":

    # simple test program (from the XML-RPC specification)

    # server = ServerProxy("http://localhost:8000") # local server
    server = ServerProxy("http://betty.userland.com")

    print server

    try:
        print server.examples.getStateName(41)
    except Error, v:
        print "ERROR", v

########NEW FILE########
__FILENAME__ = createrepo_version
#! /usr/bin/python

import sys

def vercmp(a, b):
    al = a.split('.')
    bl = b.split('.')
    length = min(len(al), len(bl))
    for i in range(1, length):
        if cmp(al[i], bl[i]) < 0:
            return -1
        elif cmp(al[i], bl[i]) > 0:
            return 1
    return cmp(len(al), len(bl))

sys.path.append("/usr/share/createrepo")
import genpkgmetadata
print genpkgmetadata.__version__
sys.path.remove("/usr/share/createrepo")
del genpkgmetadata

print vercmp('0.4.4', '0.4.6')
print vercmp('0.4.8', '0.4.6')
print vercmp('0.4.6', '0.4.6')
print vercmp('0.4.6.0', '0.4.6')
print vercmp('0.4.6.1', '0.4.6')

########NEW FILE########
__FILENAME__ = rhntest
#!/usr/bin/python -u

import sys, os, rpm, string

sys.path.insert(0, "/usr/share/rhn/")
from up2date_client import up2dateAuth
from up2date_client import up2date
from up2date_client import config
from up2date_client import repoDirector
from up2date_client import rpcServer
from up2date_client import wrapperUtils
from up2date_client import rhnChannel

def getSystemId(dist):
    return open('/var/yam/'+dist+'/rhn-systemid').read(131072)

def subscribedChannels():
    ret = []
    debugprint(ret)
    li = up2dateAuth.getLoginInfo()
    if not li: return []
        
    channels = li.get('X-RHN-Auth-Channels')
    if not channels: return []

    for label, version, t, t in channels:
        ret.append(rhnChannel.rhnChannel(label = label, version = version, type = 'up2date', url = cfg['serverURL']))

    return ret

def debugprint(obj):
    if '__name__' in dir(obj):
        print 'DEBUGPRINT object %s' % obj.__name__
        print '  repr', obj
        print '  dir', dir(obj)
    elif '__class__' in dir(obj):
        print 'DEBUGPRINT class %s' % obj.__class__
        print '  repr', obj
        print '  dir', dir(obj)
        try: print '  keys', obj.keys()
        except: print 'FAILED'
        try:
            print '  list', 
            for i in obj: print i,
        except: print 'FAILED'
    elif '__module__' in dir(obj):
        print 'DEBUGPRINT module %s' % obj.__module__
        print '  repr', obj
        print '  dir', dir(obj)
    else:
        print 'DEBUGPRINT unknown ', dir(obj)
        print '  repr', obj
        print '  dir', dir(obj)
    print

registered = getSystemId('rhel3as-i386')
up2dateAuth.updateLoginInfo()
cfg = config.initUp2dateConfig()
repos = repoDirector.initRepoDirector()

### Print channels
debugprint(rhnChannel)
debugprint(rhnChannel.rhnChannelList())
debugprint(rhnChannel.rhnChannelList().list)
debugprint(rhnChannel.getChannels(force=1))
debugprint(rhnChannel.getChannels(force=1).list)
for channel in rhnChannel.rhnChannelList().list: print channel['label'],
print

for channel in rhnChannel.getChannels(force=1).list: print channel['label'],
print

for channel in repos.channels.list: print channel['label'],
print

for channel in subscribedChannels(): print channel['label'],
print
#sys.exit(0)

debugprint(up2dateAuth.getLoginInfo())

for channel in subscribedChannels():
    cfg['storageDir'] = '/var/yam/rhel4as-i386/'+channel['label']
    try: os.makedirs(cfg['storageDir'], 0755)
    except: pass
    print channel['label'], channel['type'], channel['url'], channel['version']
    package_list, type = rpcServer.doCall(repos.listPackages, channel, None, None)
    print channel['label'], 'has', len(package_list), 'packages'
#   for name, version, release, test, arch, test, label in package_list:
#       print name,
#   for pkg in package_list:
#       name, version, release, test, arch, test, label = pkg
#       rpcServer.doCall(repos.getPackage, pkg)
#       rpcServer.doCall(repos.getPackage, pkg, wrapperUtils.printPkg, wrapperUtils.printRetrieveHash)

### Print packages
#printList(rhnPackageInfo.getAvailableAllArchPackageList(), cfg['showChannels'])
#print rhnPackageInfo.getAvailableAllArchPackageList()

########NEW FILE########
__FILENAME__ = rhn_query
#! /usr/bin/python

import xmlrpclib
from optparse import OptionParser


host = 'xmlrpc.rhn.redhat.com'
username='rhnname'
password = 'rhnpass'
protocol = 'https'
url = "%s://%s/rpc/api" %(protocol,host)

server = xmlrpclib.ServerProxy(url)
session = server.auth.login(username, password)

systems = server.system.list_user_systems(session)
if len(systems) == 0:
    print "No systems are subscribed to RHN."
else:
    print "These machines are subscribed to RHN\n\n"
    print "Name: \t\tcheckin: \t\t\tsid: "
        for vals in systems:
        print "%s\t\t%s\t\t%s" % (vals['name'],vals['last_checkin'],vals['id'])

methods = server.system.listMethods()
print methods

for method in methods:
    print server.system.methodHelp(method)

########NEW FILE########
__FILENAME__ = rhn_tool
#! /usr/bin/python

import xmlrpclib
from optparse import OptionParser

def GetOptions():
    parser=OptionParser()

    parser.add_option("-d", "--delete",
        action="store_true", dest="delete", default=False,
        help = "Deletes system, group, or channel")

    parser.add_option("-s", "--system",
        action="store_true", dest="system", default=False,
        help="Used when performing operations to machines subscribe to RHN.")

        parser.add_option("-q", "--query",
        action="store_true", dest="query", default=False,
        help="Used in conjuction with -s to show subscribed systems.")


    parser.add_option("-n", "--name",dest="hostname",
        help="hostname of machine to perform operation on.", metavar=" hostname")

    global options
    (options,args) = parser.parse_args()

    return options.delete, options.system, options.hostname

def getSystemIds():
    systems = server.system.list_user_systems(session)
    return systems

def deleteSystem(sid):
    try:
        print "attempting to remove SID %s... with hostname of %s" % (sid,options.hostname)
            delete = server.system.delete_systems(session,sid)
        print "Deletion of %s successfull." % (options.hostname)
    except:
        print "Deletion of %s unsuccessfull." % (options.hostname)

host = 'xmlrpc.rhn.redhat.com'
username='IBM_RHN'
password = 'think'
protocol = 'https'
url = "%s://%s/rpc/api" %(protocol,host)

server = xmlrpclib.ServerProxy(url)
session = server.auth.login(username,password)

GetOptions()

if options.system:
    systems = getSystemIds()
    if options.query:
        if len(systems) == 0:
            print "No systems are subscribed to RHN."
        else:
            print "These machines are subscribed to RHN\n\n"
            print "Name: \t\tcheckin: \t\t\tsid: "
                for vals in systems:
                print "%s\t\t%s\t\t%s" % (vals['name'],vals['last_checkin'],vals['id'])

    if options.delete:
        for vals in systems:
            if vals['name'] == options.hostname:
                deleteSystem(vals['id'])

########NEW FILE########
__FILENAME__ = unittest
#!/usr/bin/python

import os
import sys

import os.path
testdir = os.path.abspath(os.path.dirname(__file__))
parentdir = os.path.dirname(testdir)
sys.path.insert(1, parentdir)

import unittest
import mrepo
from mrepo import mySet

class TestmySet(unittest.TestCase):

    def setUp(self):
        self.s = mySet([1, 2, 3, 4])
        
    def test_initempty(self):
        s = mySet()
        self.assert_(isinstance(s, mrepo.mySet))

    def test_init(self):
        s = mySet([ 1, 2, 3, 4 ])
        self.assert_(isinstance(s, mrepo.mySet))
        self.assert_(repr(s) == 'mySet([1, 2, 3, 4])')

    def test_add(self):
        s = self.s
        self.assert_(9 not in s)
        s.add(9)
        self.assert_(9 in s)

    def test_eq(self):
        s1 = mySet([1, 2, 3])
        s2 = mySet([1, 2, 3])
        self.assertEqual(s1, s2)

    def test_difference(self):
        s1 = mySet([ 1, 2, 3, 4 ])
        s2 = mySet([ 1, 3 ])
        s = s1.difference(s2)
        self.assertEqual(s, mySet([2, 4]))

    def test_iter(self):
        s = mySet([1, 2, 3])
        l = []
        for i in s:
            l.append(i)
        self.assertEqual(l, [1, 2, 3])


class TestSync(unittest.TestCase):
    def setUp(self):
        pass
    def test_synciter1(self):
        left = (
            1, 2, 4, 5
            )
        right = (
            2, 3, 5, 6, 7
            )

        onlyright = []
        onlyleft = []
        keyequal = []
        for a, b in mrepo.synciter(left, right):
            # print "%s, %s, %s" % ( a, b, k )
            if a is None:
                onlyright.append(b)
            elif b is None:
                onlyleft.append(a)
            else:
                keyequal.append(a)

        self.assertEqual(onlyright, [3, 6, 7])
        self.assertEqual(onlyleft, [1, 4])
        self.assertEqual(keyequal, [2, 5])

    def test_synciter2(self):
        left = (
            (1, 'l1'), (2, 'l2'), (4, 'l4'), (5, 'l5')
            )
        right = (
            (2, 'r2'), (3, 'r3'), (5, 'r5'), (6, 'r6'), (7, 'r7')
            )

        onlyright = []
        onlyleft = []
        keyequal = []
        # key is the first element
        for a, b in mrepo.synciter(left, right, key = lambda x: x[0]):
            if a is None:
                onlyright.append(b)
            elif b is None:
                onlyleft.append(a)
            else:
                keyequal.append((a, b))

        self.assertEqual(onlyright, [(3, 'r3'), (6, 'r6'), (7, 'r7')])
        self.assertEqual(onlyleft, [(1, 'l1'), (4, 'l4')])
        self.assertEqual(keyequal, [((2, 'l2'), (2, 'r2')),
                                    ((5, 'l5'), (5, 'r5'))])

class Testlinksync(unittest.TestCase):
    def setUp(self):
        mkdir = os.mkdir
        pj= os.path.join
        self.tmpdir = tmpdir = pj(testdir, 'tmp')

        os.mkdir(tmpdir)

        # global "op" is needed by mrepo.Config, horrible for testing!
        
        class TestConfig:
            pass
        
        self.cf = cf = TestConfig()

        cf.srcdir = pj(tmpdir, 'src')
        cf.wwwdir = pj(tmpdir, 'dst')
       
        self.dist = mrepo.Dist('testdist', 'i386', cf)
        self.repo = repo = mrepo.Repo('testrepo', '', self.dist, cf)
        srcdir = repo.srcdir


        # tmp/src/testdist-i386/testrepo
        os.makedirs(srcdir)

        # tmp/dst/testdist-i386/RPMS.testrepo
        os.makedirs(repo.wwwdir)

        for f in xrange(4):
            __touch(pj(srcdir, str(f) + '.rpm'))
        __touch(pj(srcdir, 'dontsync.txt'))
                
        os.mkdir(pj(srcdir, 'a'))
        __touch(pj(srcdir, 'a', '2.rpm'))
        __touch(pj(srcdir, 'a', 'a.rpm'))

        self.localdir = localdir = pj(cf.srcdir, 'testdist-i386', 'local')
        os.makedirs(localdir)
        for f in ('local.rpm', 'dont_sync2.txt'):
            __touch(pj(localdir, f))

        # this should be the result when linksync'ing srcdir
        self.linkbase = linkbase = '../../../src/testdist-i386/testrepo'
        self.links = [
            ('0.rpm', pj(linkbase, '0.rpm')),
            ('1.rpm', pj(linkbase, '1.rpm')),
            ('2.rpm', pj(linkbase, '2.rpm')),
            ('3.rpm', pj(linkbase, '3.rpm')),
            ('a.rpm', pj(linkbase, 'a', 'a.rpm'))
            ]
        self.links.sort()

        
    def tearDown(self):
        isdir = os.path.isdir
        walk = os.path.walk
        pathjoin= os.path.join
        tmpdir = self.tmpdir
        # for safety-reasons:
        if tmpdir.count('/') < 3:
            raise "Will not remove tmpdir %s" % ( tmpdir, )

        def rmfile(arg, path, files):
            for file in files:
                # print "%s" % ( file, )
                f = pathjoin(path, file)
                if isdir(f):
                    walk(f, rmfile, None)
                    #print "rmdir %s" % ( f, )
                    os.rmdir(f)
                else:
                    #print "unlink %s" % ( f, )
                    os.unlink(f)

        os.path.walk(tmpdir, rmfile, None)
        os.rmdir(tmpdir)

    def readlinks(self, dir):
        """return a list of (linkname, linktarget) tuples for all files in a directory"""
        pj = os.path.join
        readlink = os.readlink
        return [ (l, readlink(pj(dir, l))) for l in os.listdir(dir) ]

    def genlinks(self, links, dir=''):
        if not dir:
            dir = self.repo.wwwdir
        pj = os.path.join
        symlink = os.symlink
        for name, target in links:
            symlink(target, pj(dir, name))

    def test_listrpms(self):
        srcdir = self.repo.srcdir
        actual = mrepo.listrpms(srcdir)
        pj= os.path.join
        target = [
            ('0.rpm', srcdir),
            ('1.rpm', srcdir),
            ('2.rpm', srcdir),
            ('2.rpm', pj(srcdir, 'a')),
            ('3.rpm', srcdir),
            ('a.rpm', pj(srcdir, 'a')),
            ]
        self.assertEqual(actual, target)

    def test_listrpms_rel(self):
        srcdir = self.repo.srcdir
        linkbase = self.linkbase
        actual = mrepo.listrpms(srcdir, relative = self.repo.wwwdir)
        pj= os.path.join
        target = [
            ('0.rpm', linkbase),
            ('1.rpm', linkbase),
            ('2.rpm', linkbase),
            ('2.rpm', pj(linkbase, 'a')),
            ('3.rpm', linkbase),
            ('a.rpm', pj(linkbase, 'a')),
            ]
        self.assertEqual(actual, target)

    def test_linksync_new(self):
        repo = self.repo
        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        target = self.links
        self.assertEqual(actual, target)

    def test_linksync_missing(self):
        repo = self.repo
        links = self.links[:]

        # remove some links
        del links[0]
        del links[2]
        del links[-1:]
        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        target = self.links
        actual.sort()
        self.assertEqual(actual, target)

    def test_linksync_additional(self):
        repo = self.repo
        links = self.links[:]

        pj = os.path.join
        # add some links
        links.insert(0, ('new1.rpm', pj(self.linkbase, 'new1.rpm')))
        links.insert(2, ('new2.rpm', pj(self.linkbase, 'new2.rpm')))
        links.append(('new3.rpm', pj(self.linkbase, 'new3.rpm')))
        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        actual.sort()
        target = self.links
        self.assertEqual(actual, target)

    def test_linksync_targetchange(self):
        repo = self.repo
        links = self.links[:]

        pj = os.path.join
        # add some links
        
        # basename != target basename
        links[1] = (links[1][0], pj(self.linkbase, 'illegal.rpm'))
        # different dir
        links[2] = (links[2][0], pj(self.linkbase, 'illegaldir', links[2][0]))
        # correct, but absolute link
        links[3] = (links[3][0], pj(repo.srcdir, links[3][0]))

        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        actual.sort()
        target = self.links
        self.assertEqual(actual, target)


    def test_linksync_mod(self):
        self.dist.linksync(self.repo)

def _Testlinksync__touch(filename):
    open(filename, 'a')


if __name__ == '__main__':
    # mrepo.op = mrepo.Options(('-vvvvv', '-c/dev/null'))
    mrepo.op = mrepo.Options(('-c/dev/null')) # should really get rid of this!
    unittest.main()

########NEW FILE########
__FILENAME__ = capabilities
#!/usr/bin/python


# a dict with "capability name" as the key, and the version
# as the value.

import UserDict
import os
import sys
import config
import up2dateErrors
import rpcServer
import string


neededCaps = {"caneatCheese": {'version':"21"},
              "supportsAutoUp2dateOption": {'version': "1"},
              "registration.finish_message": {'version': "1"},
	      "xmlrpc.packages.extended_profile": {'version':"1"},
              "registration.delta_packages": {'version':"1"},
              "registration.remaining_subscriptions": {'version': '1'},
              "registration.update_contact_info": {'version': "1"}}

def parseCap(capstring):
    value = None
    caps = string.split(capstring, ',')

    capslist = []
    for cap in caps:
        try:
            (key_version, value) = map(string.strip, string.split(cap, "=", 1))
        except ValueError:
            # Bad directive: not in 'a = b' format
            continue
            
        # parse out the version
        # lets give it a shot sans regex's first...
        (key,version) = string.split(key_version, "(", 1)
        
        # just to be paranoid
        if version[-1] != ")":
            print "something broke in parsing the capabilited headers"
        #FIXME: raise an approriate exception here...

        # trim off the trailing paren
        version = version[:-1]
        data = {'version': version, 'value': value}

        capslist.append((key, data))

    return capslist

class Capabilities(UserDict.UserDict):
    def __init__(self):
        UserDict.UserDict.__init__(self)
        self.missingCaps = {}
        #self.populate()
#        self.validate()
        self.neededCaps = neededCaps
        self.cfg = config.initUp2dateConfig()


    def populate(self, headers):
        for key in headers.keys():
            if key == "x-rhn-server-capability":
                capslist = parseCap(headers[key])

                for (cap,data) in capslist:
                    self.data[cap] = data

    def parseCapVersion(self, versionString):
        index = string.find(versionString, '-')
        # version of "-" is bogus, ditto for "1-"
        if index > 0:
            rng = string.split(versionString, "-")
            start = rng[0]
            end = rng[1]
            versions = range(int(start), int(end)+1)
            return versions

        vers = string.split(versionString, ':')
        if len(vers) > 1:
            versions = map(lambda a:int(a), vers)
            return versions

        return [int(versionString)]

    def validateCap(self, cap, capvalue):
        if not self.data.has_key(cap):
            errstr = "This client requires the server to support %s, which the current " \
                     "server does not support" % cap
            self.missingCaps[cap] = None
        else:
            data = self.data[cap]
            # DOES the server have the version we need
            if int(capvalue['version']) not in self.parseCapVersion(data['version']):
                self.missingCaps[cap] =  self.neededCaps[cap]


    def validate(self):
        for key in self.neededCaps.keys():
            self.validateCap(key, self.neededCaps[key])

        self.workaroundMissingCaps()

    def setConfig(self, key, configItem):
        if self.tmpCaps.has_key(key):
            self.cfg[configItem] = 0
            del self.tmpCaps[key]
        else:
            self.cfg[configItem] = 1

    def workaroundMissingCaps(self):
        # if we have caps that we know we want, but we can
        # can work around, setup config variables here so
        # that we know to do just that
        self.tmpCaps = self.missingCaps

        # this is an example of how to work around it
        key = 'caneatCheese'
        if self.tmpCaps.has_key(key):
            # do whatevers needed to workaround
            del self.tmpCaps[key]
        else:
            # we support this, set a config option to
            # indicate that possibly
            pass

        # dict of key to configItem, and the config item that
        # corresponds with it

        capsConfigMap = {'supportsAutoUp2dateOption': 'supportsAutoUp2dateOption',
                         'registration.finish_message': 'supportsFinishMessage',
                         "registration.remaining_subscriptions" : 'supportsRemainingSubscriptions',
                         "registration.update_contact_info" : 'supportsUpdateContactInfo',
                         "registration.delta_packages" : 'supportsDeltaPackages',
                         "xmlrpc.packages.extended_profile" : 'supportsExtendedPackageProfile'}

        for key in capsConfigMap.keys():
            self.setConfig(key, capsConfigMap[key])

        # if we want to blow up on missing caps we cant eat around
        missingCaps = []
        wrongVersionCaps = []

        if len(self.tmpCaps):
            for cap in self.tmpCaps:
                capInfo = self.tmpCaps[cap]
                if capInfo == None:
                    # it's completly mssing
                    missingCaps.append((cap, capInfo))
                else:
                    wrongVersionCaps.append((cap, capInfo))


        errString = ""
        errorList = []
        if len(wrongVersionCaps):
            for (cap, capInfo) in wrongVersionCaps:
                errString = errString + "Needs %s of version: %s but server has version: %s\n" % (cap,
                                                                                    capInfo['version'],
                                                                                    self.data[cap]['version'])
                errorList.append({"capName":cap, "capInfo":capInfo, "serverVersion":self.data[cap]})

        if len(missingCaps):
            for (cap, capInfo) in missingCaps:
                errString = errString + "Needs %s but server does not support that capabilitie\n" % (cap)
                errorList.append({"capName":cap, "capInfo":capInfo, "serverVersion":""})

        if len(errString):
#            print errString
            # raise this once we have exception handling code in place to support it
            raise up2dateErrors.ServerCapabilityError(errString, errorList)

########NEW FILE########
__FILENAME__ = clientCaps
#!/usr/bin/python

# a dict with "capability name" as the key, and the version
# as the value.

import UserDict
import glob
import os
import string
import sys

import capabilities
import config
import up2dateErrors

class ClientCapabilities(UserDict.UserDict):
    def __init__(self):
        UserDict.UserDict.__init__(self)
        self.populate()

    def populate(self, capsToPopulate=None):
        # FIXME: at some point, this will be
        # intelligently populated...
        localcaps = {
#            "packages.runTransaction":{'version':1, 'value':1},
#            "blippyfoo":{'version':5, 'value':0},
            "caneatCheese":{'version':1, 'value': 1}
            }
        if capsToPopulate:
            localcaps = capsToPopulate
        self.data = localcaps

    def headerFormat(self):
        headerList = []
        for key in self.data.keys():
            headerName = "X-RHN-Client-Capability"
            value = "%s(%s)=%s" % (key,
                                   self.data[key]['version'],
                                   self.data[key]['value'])
            headerList.append((headerName, value))
        return headerList

caps = ClientCapabilities()

def loadLocalCaps():
    capsDir = "/etc/sysconfig/rhn/clientCaps.d"

    capsFiles = glob.glob("%s/*" % capsDir)

    for capsFile in capsFiles:
        if os.path.isdir(capsFile):
            continue
        if not os.access(capsFile, os.R_OK):
            continue

        fd = open(capsFile, "r")
        for line in fd.readlines():
            string.strip(line)
            if line[0] == "#":
                continue
            caplist = capabilities.parseCap(line)

            for (cap,data) in caplist:
                caps.data[cap] = data

#    print caps.data
    
loadLocalCaps()

# register local caps we require.
def registerCap(cap, data):
    caps.data[cap] = data
    

# figure out something pretty here
registerCap("packages.runTransaction", {'version':'1', 'value':'1'})
registerCap("packages.rollBack", {'version':'1', 'value':'1'})
registerCap("packages.verify", {'version':'1', 'value':'1'})
registerCap("packages.verifyAll", {'version':'1', 'value':'1'})
registerCap("packages.extended_profile", {'version':'1', 'value':'1'})
registerCap("reboot.reboot", {'version':'1', 'value':'1'})

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
#
# This file is a portion of the Red Hat Update Agent
# Copyright (c) 1999 - 2002 Red Hat, Inc.  Distributed under GPL
#
# Authors:
#       Cristian Gafton <gafton@redhat.com>
#       Adrian Likins   <alikins@redhat.com>
#
# $Id: config.py 87080 2005-11-04 20:49:52Z alikins $
"""
This module includes the Config and Up2date Config classes use by the
up2date agent to hold config info.
""" # " == emacs sucks

import os
import string
import sys

#cfg = None

# XXX: This could be moved in a more "static" location if it is too
# much of an eye sore
Defaults = {
    'enableProxy'       : ("Use a HTTP Proxy",
                           0),
    'serverURL'         : ("Remote server URL",
                           "https://xmlrpc.rhn.redhat.com/XMLRPC"),
    'noSSLServerURL'    : ("Remote server URL without SSL",
                           "http://xmlrpc.rhn.redhat.com/XMLRPC"),
    'debug'             : ("Whether or not debugging is enabled",
                           0),
    'systemIdPath'      : ("Location of system id",
                           "/etc/sysconfig/rhn/systemid"),
    'adminAddress'      : ("List of e-mail addresses for update agent "\
                           "to communicate with when run in batch mode",
                           ["root@localhost"]),
    'storageDir'        : ("Where to store packages and other data when "\
                           "they are retrieved",
                           "/var/spool/up2date"),
    'pkgSkipList'       : ("A list of package names, optionally including "\
                           "wildcards, to skip",
                           ["kernel*"]),
    'pkgsToInstallNotUpdate' : ("A list of provides names or package names of packages "\
                                "to install not update",
                           ["kernel", "kernel-unsupported"]),
    'removeSkipList'    : ("A list of package names, optionally including "\
                           "wildcards, that up2date will not remove",
                           ["kernel*"]),
    'fileSkipList'      : ("A list of file names, optionally including "\
                           "wildcards, to skip",
                           []),
    'noReplaceConfig'   : ("When selected, no packages that would change "\
                           "configuration data are automatically installed",
                           1),
    'retrieveOnly'      : ("Retrieve packages only",
                           0),
    'retrieveSource'    : ("Retrieve source RPM along with binary package",
                           0),
    'keepAfterInstall'  : ("Keep packages on disk after installation",
                           0),
    'versionOverride'   : ("Override the automatically determined "\
                           "system version",
                           ""),
    'useGPG'            : ("Use GPG to verify package integrity",
                           1),
    'headerCacheSize'   : ("The maximum number of rpm headers to cache in ram",
                           40),
    'headerFetchCount'  : ("The maximimum number of rpm headers to "\
                           "fetch at once", 
                           10),
    'forceInstall'      : ("Force package installation, ignoring package, "\
                           "file and config file skip list",
                           0),
    'httpProxy'         : ("HTTP proxy in host:port format, e.g. "\
                           "squid.redhat.com:3128",
                           ""),
    'proxyUser'         : ("The username for an authenticated proxy",
                           ""),
    'proxyPassword'     : ("The password to use for an authenticated proxy",
                           ""),
    'enableProxyAuth'   : ("To use an authenticated proxy or not",
                           0),
    'noBootLoader'      : ("To disable modification of the boot loader "\
                           "(lilo, silo, etc)",
                           0),
    'networkRetries'    : ("Number of attempts to make at network "\
                           "connections before giving up",
                           5),
    'sslCACert'         : ("The CA cert used to verify the ssl server",
                           "/usr/share/rhn/RHNS-CA-CERT"),
    'gpgKeyRing'        : ("The location of the gpg keyring to use for "\
                           "package checking.",
                           "/etc/sysconfig/rhn/up2date-keyring.gpg"),
    'enableRollbacks'   : ("Determine if up2date should create "\
                           "rollback rpms",
                           0),
    'noReboot'          : ("Disable the reboot action",
                           0),
    'updateUp2date'     : ("Allow up2date to update itself when possible", 1),
    'disallowConfChanges': ("Config options that can not be overwritten by a config update action",
                            ['sslCACert','useNoSSLForPackages','noSSLServerURL',
                             'serverURL','disallowConfChanges', 'noReboot']),
}

# a peristent configuration storage class
class ConfigFile:
    "class for handling persistent config options for the client"
    def __init__(self, filename = None):
	self.dict = {}
	self.fileName = filename
        if self.fileName:
            self.load()
            
    def load(self, filename = None):
        if filename:
            self.fileName = filename
	if self.fileName == None:
	    return
        if not os.access(self.fileName, os.R_OK):
#            print "warning: can't access %s" % self.fileName
            return
        
        f = open(self.fileName, "r")

	for line in f.readlines():
            # strip comments
            if '#' in line:
                line = line[:string.find(line, '#')]
            line = string.strip(line)            
            if not line:
		continue

            value = None
	    try:
		(key, value) = map(string.strip, string.split(line, "=", 1))
	    except ValueError:
                # Bad directive: not in 'a = b' format
		continue

            # decode a comment line
            comment = None
	    pos = string.find(key, "[comment]")
	    if pos != -1:
		key = key[:pos]
                comment = value
                value = None

            # figure out if we need to parse the value further
            if value:
		# possibly split value into a list
		values = string.split(value, ";")
                if key in ['proxyUser', 'proxyPassword']:
                    value = str(value)
		elif len(values) == 1:
		    try:
			value = int(value)
		    except ValueError:
			pass
		elif values[0] == "":
                    value = []
		else:
                    value = values[:-1]

            # now insert the (comment, value) in the dictionary
            newval = (comment, value)
            if self.dict.has_key(key): # do we need to update
                newval = self.dict[key]
                if comment is not None: # override comment
                    newval = (comment, newval[1])
                if value is not None: # override value
                    newval = (newval[0], value)
            self.dict[key] = newval
	f.close()

    def save(self):
	if self.fileName == None:
	    return

        # this really shouldn't happen, since it means that the
        # /etc/sysconfig/rhn directory doesn't exist, which is way broken

        # and note the attempted fix breaks useage of this by the applet
        # since it reuses this code to create its config file, and therefore
        # tries to makedirs() the users home dir again (with a specific perms)
        # and fails (see #130391)
        if not os.access(self.fileName, os.R_OK):
            if not os.access(os.path.dirname(self.fileName), os.R_OK):
                print "%s was not found" % os.path.dirname(self.fileName)
                return
        
        f = open(self.fileName, "w")
        os.chmod(self.fileName, 0600)

	f.write("# Automatically generated Red Hat Update Agent "\
                "config file, do not edit.\n")
	f.write("# Format: 1.0\n")
	f.write("")
	for key in self.dict.keys():
	    val = self.dict[key]
	    f.write("%s[comment]=%s\n" % (key, val[0]))
	    if type(val[1]) == type([]):
		f.write("%s=%s;\n" % (key, string.join(map(str, val[1]), ';')))
	    else:
		f.write("%s=%s\n" % (key, val[1]))
	    f.write("\n")
	f.close()

    # dictionary interface
    def has_key(self, name):
        return self.dict.has_key(name)
    def keys(self):
	return self.dict.keys()
    def values(self):
        return map(lambda a: a[1], self.dict.values())
    def update(self, dict):
        self.dict.update(dict)
    # we return None when we reference an invalid key instead of
    # raising an exception
    def __getitem__(self, name):
        if self.dict.has_key(name):
            return self.dict[name][1]
        return None    
    def __setitem__(self, name, value):
        if self.dict.has_key(name):
            val = self.dict[name]
        else:
            val = (None, None)
	self.dict[name] = (val[0], value)
    # we might need to expose the comments...
    def info(self, name):
        if self.dict.has_key(name):
            return self.dict[name][0]
        return ""

# a superclass for the ConfigFile that also handles runtime-only
# config values
class Config:
    def __init__(self, filename = None):
        self.stored = ConfigFile()
        self.stored.update(Defaults)
        if filename:
            self.stored.load(filename)
        self.runtime = {}

    # classic dictionary interface: we prefer values from the runtime
    # dictionary over the ones from the stored config
    def has_key(self, name):
        if self.runtime.has_key(name):
            return 1
        if self.stored.has_key(name):
            return 1
        return 0
    def keys(self):
        ret = self.runtime.keys()
        for k in self.stored.keys():
            if k not in ret:
                ret.append(k)
        return ret
    def values(self):
        ret = []
        for k in self.keys():
            ret.append(self.__getitem__(k))
        return ret
    def items(self):
        ret = []
        for k in self.keys():
            ret.append((k, self.__getitem__(k)))
        return ret
    def __len__(self):
        return len(self.keys())
    def __setitem__(self, name, value):
        self.runtime[name] = value
    # we return None when nothing is found instead of raising and exception
    def __getitem__(self, name):
        if self.runtime.has_key(name):
            return self.runtime[name]
        if self.stored.has_key(name):
            return self.stored[name]
        return None
        
    # These function expose access to the peristent storage for
    # updates and saves
    def info(self, name): # retrieve comments
        return self.stored.info(name)    
    def save(self):
        self.stored.save()
    def load(self, filename):
        self.stored.load(filename)
        # make sure the runtime cache is not polluted
        for k in self.stored.keys():
            if not self.runtime.has_key(k):
                continue
            # allow this one to pass through
            del self.runtime[k]
    # save straight in the persistent storage
    def set(self, name, value):
        self.stored[name] = value
        # clean up the runtime cache
        if self.runtime.has_key(name):
            del self.runtime[name]

class UuidConfig(ConfigFile):
    "derived from the ConfigFile class, with prepopulated default values"
    def __init__(self):
        ConfigFile.__init__(self)
        self.fileName = "/etc/sysconfig/rhn/up2date-uuid"

class NetworkConfig(ConfigFile):
    "derived from the ConfigFile class, with prepopulated default values"
    def __init__(self):
        ConfigFile.__init__(self)
        self.fileName = "/etc/sysconfig/rhn/network"


def initUp2dateConfig(file = "/etc/sysconfig/rhn/up2date"):
    global cfg
    try:
        cfg = cfg
    except NameError:
        cfg = None
        
    if cfg == None:

        cfg = Config(file)
        cfg["isatty"] = 0 
        if sys.stdout.isatty():
            cfg["isatty"] = 1
                # pull this into the main cfg dict from the
        # seperate config file, so we dont have to munge
        # main config file in a post
        uuidCfg = UuidConfig()
        uuidCfg.load()
        if uuidCfg['rhnuuid'] == None or uuidCfg['rhnuuid'] == "UNSPECIFIED":
            print "No rhnuuid config option found in /etc/sysconfig/rhn/up2date-uuid."
            sys.exit(1)
        cfg['rhnuuid'] = uuidCfg['rhnuuid']

        # set the HTTP_PROXY variable so urllib will find it
        # not a great, but a pretty close fix for bz #157070
        if cfg['enableProxy']:
            if cfg['httpProxy']:
                # more fixes for %157070, make sure proxyHost is in the format httplib requies
                # (aka, just one http://)
                proxyHost = cfg['httpProxy']
                if proxyHost[:7] != "http://":
                    proxyHost = "http://%s" % proxyHost

                os.environ["HTTP_PROXY"] = proxyHost

# there is no support in any of the built in python http stuff that yum repo stuff uses for
# authenticated proxies, so just ignore this. see comment #20 in bz #157070

#            if cfg['enableProxyAuth']:
#                if cfg['proxyUser'] and cfg['proxyPassword']:
#                    os.environ['HTTP_PROXY'] = "http://%s:%s@%s" % (cfg['proxyUser'], cfg['proxyPassword'], cfg['httpProxy']) 

#	networkConfig = NetworkConfig()
#	networkConfig.load()
	
	# override any of the settings in the up2date config with the ones in
	# in up2date
#	for key in networkConfig.keys():
#	    print "overriding value of %s from %s to %s" % (key, cfg[key], networkConfig[key])
#	    cfg[key] = networkConfig[key] 


    return cfg

def main():
    source = initUp2dateConfig("foo-test.config")

    print source["serverURL"]
    source["serverURL"] =  "http://hokeypokeyland.com"
    print source["serverURL"]
    print source.set("debug", 100)
    source.save()
    print source["debug"]

if __name__ == "__main__":
    __CFG = None
    main()

########NEW FILE########
__FILENAME__ = distrotype

########NEW FILE########
__FILENAME__ = gpgUtils
#!/usr/bin/python

import os
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

import config
import up2dateErrors
import up2dateMessages
import rpmUtils
import transaction
import re
import string
import distrotype



# directory to look for .gnupg/options, etc
gpg_home_dir = "/root/.gnupg"

# the fingerprints of our keys
redhat_gpg_fingerprint =      "219180CDDB42A60E"
redhat_beta_gpg_fingerprint = "FD372689897DA07A"
fedora_gpg_fingerprint =      "B44269D04F2A6FD2"
fedora_test_gpg_fingerprint = "DA84CBD430C9ECF8"

# basically determines if we care about the
# beta key or not.


def checkGPGInstallation():
    # return 1, gpg not installed
    # return 2, key not installed
    if not findKey(redhat_gpg_fingerprint):
        return 2

    if hasattr(distrotype, "fedora") and not findKey(fedora_gpg_fingerprint):
        return 2

    if hasattr(distrotype, "rawhide"):
        if not findKey(redhat_beta_gpg_fingerprint):
            return 2
	if hasattr(distrotype, "fedora") and not findKey(fedora_test_gpg_fingerprint):
	    return 2
    
    return 0

def checkGPGSanity():
    cfg = config.initUp2dateConfig()
    if cfg["useGPG"] and checkGPGInstallation() == 2:
        errMsg = up2dateMessages.gpgWarningMsg 
        raise up2dateErrors.GPGKeyringError(errMsg)

def findGpgFingerprints():
    # gpg is really really annoying the first time you run it
    # do this so the bits we care about are always atleast the second running
                                             # shut... up... gpg...
    command = "/usr/bin/gpg -q --list-keys > /dev/null 2>&1"
    fdno = os.popen(command)
    fdno.close()
    
    command  = "/usr/bin/gpg %s --list-keys --with-colons" % rpmUtils.getGPGflags()
    fdno = os.popen(command)
    lines = fdno.readlines()
    fdno.close()

    fingerprints = []
    for line in lines:
        parts = string.split(line, ":")
        if parts[0] == "pub":
            fingerprint = parts[4]
            fingerprints.append(fingerprint)

    return fingerprints

def findKey(fingerprint):
    version = string.lower("%s" % fingerprint[8:])
    return rpmUtils.installedHeadersNameVersion("gpg-pubkey", version)

def importKey(filename):
    fdno = open(filename, "r")
    pubkey = fdno.read()
    fdno.close()
    # need method to import ascii keys

    foo = os.popen("/bin/rpm --import %s  > /dev/null 2>&1" % filename)
    foo.read()
    foo.close()
    # I dont know, this doesnt seem to want to work
#    _ts.pgpImportPubkey(pubkey)

def importRedHatGpgKeys():
    keys = ["/usr/share/rhn/RPM-GPG-KEY"]
    if hasattr(distrotype, 'fedora') and distrotype.fedora:
        keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora")
    if hasattr(distrotype, 'rawhide') and distrotype.rawhide:
        keys.append("/usr/share/rhn/BETA-RPM-GPG-KEY")
        if hasattr(distrotype, 'fedora') and distrotype.fedora:
	    keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora-test")

    for key in keys:
        importKey(key)

def keysToImport():
    keys = ["/usr/share/rhn/RPM-GPG-KEY"]
    if hasattr(distrotype, 'fedora') and distrotype.fedora:
        keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora")
    if hasattr(distrotype, 'rawhide') and distrotype.rawhide:
        keys.append("/usr/share/rhn/BETA-RPM-GPG-KEY")
        if hasattr(distrotype, 'fedora') and distrotype.fedora:
	    keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora-test")

    return keys

def importGpgKeyring():
    # gpg is really really annoying the first time you run it
    # do this so the bits we care about are always atleast the second running
    command = "/usr/bin/gpg -q --list-keys > /dev/null 2>&1"
    fdno  = os.popen(command)
    fdno.close()
    # method to import an existing keyring into the new
    # rpm mechanism of storing supported keys as virtual
    # packages in the database
    for fingerprint in findGpgFingerprints():
        if findKey(fingerprint):
            continue

        command = "/usr/bin/gpg %s --export %s" % (
            rpmUtils.getGPGflags(), fingerprint)
        #    print command
        fdno = os.popen(command)
        pubkey = fdno.read()
        fdno.close()
        _ts = transaction.initReadOnlyTransaction()
        _ts.pgpImportPubkey(pubkey)
        #_ts.pgpPrtPkts(pubkey)
    return 0

# wrapper function for importing existing keyring, and
# adding the redhat keys if they are there already
def addGPGKeys():
    cfg = config.initUp2dateConfig()
    if os.access(cfg["gpgKeyRing"], os.R_OK):
        # if they have a keyring like 7.3 used, import the keys off
        # of it
        importGpgKeyring()

    # the red hat keys still arent there
    if not checkGPGInstallation():
        importRedHatGpgKeys()
        






def main():
    #importGpgKeyring()

##    print "checkGPGInstallation()"
##    print checkGPGInstallation()
##    print
##    sys.exit(1)

##    print "checkGPGSanity()"
##    try:
##        print checkGPGSanity()
##    except up2dateErrors.GPGKeyringError,e :
##        print e.errmsg
##    print
    
    print "findGpgFingerprints()"
    fingerprints = findGpgFingerprints()
    print fingerprints
    print

    print "findKeys"
    for fingerprint in fingerprints:
        print "findKey(%s)" % fingerprint
        print findKey(fingerprint)
    print

    #print """importKey("/usr/share/rhn/RPM-GPG-KEY")"""
    #print importKey("/usr/share/rhn/RPM-GPG-KEY")
    #print

    print "findKey(%s) RPM-GPG-KEY fingerprint" % redhat_gpg_fingerprint
    print findKey(redhat_gpg_fingerprint)
    print

    print "importGpgKeyring()"
    print importGpgKeyring()
    print

    print "findKey(%s) RPM-GPG-KEY fingerprint" % redhat_gpg_fingerprint
    print findKey(redhat_gpg_fingerprint)
    print
    

    

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = aptRepo
#!/usr/bin/python

import os
import sys
import time
import glob
import gzip
import string
import urllib
import xmlrpclib

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import rpmUtils
from up2date_client import config
from up2date_client import rpcServer
from up2date_client import up2dateUtils

import genericRepo
import genericSolveDep
import urlUtils


class AptSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "apt"


class AptRepoSource(rpmSource.PackageSource):
    def __init__(self,  proxyHost=None,
                 loginInfo = None, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self_loginInfo=loginInfo


    def listAllPackages(self, channel,
                        msgCallback = None, progressCallback = None):
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        rd = repoDirector.initRepoDirector()
        pkgList = rd.listPackages(channel, msgCallback, progressCallback)

        list = pkgList[0]
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)
        return list
    
    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        # TODO: implement cache invalidations, Last-Modified
        filePath =  "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])

        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])
        oldLists = glob.glob(globPattern)
        channelTimeStamp = None
        if oldLists:
            filename = oldLists[0]
            filename = os.path.basename(filename)
            oldVersion = string.split(filename, '.')[-1]
            channelTimeStamp = time.strptime(oldVersion,"%Y%m%d%H%M%S")

        # assuming this is always bz2?
        url = "%s/base/pkglist.%s.bz2" % (channel['url'], channel['dist'])
        if msgCallback:
	    msgCallback("Fetching %s" % url)


        ret = urlUtils.fetchUrl(url, lastModified=channelTimeStamp,
                                progressCallback = progressCallback,
                                agent = "Up2date %s/Apt" % up2dateUtils.version())
        if ret:
            (buffer, lmtime) = ret
        else:
            return None

        symlinkname =  "%s/link-%s" % (self.cfg["storageDir"], channel['label'])
        try:
            os.unlink(symlinkname)
        except OSError:
            # file doesnt exist, shrug
            pass

        

        self.version = time.strftime("%Y%m%d%H%M%S", lmtime)
        filePath =  "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], self.version)
        
        # sigh, no native bzip2 module... do it the old fashioned way
        tmpfilename = "%s/tmp-%s-%s" % (self.cfg['storageDir'], channel['label'], self.version)
        #print "timefilename: %s" % tmpfilename
        f = open("%s.bz2" % tmpfilename, "w")
        f.write(buffer)
        f.close()
        
        # FIXME, um, lame... once we settle on what url/http lib
        # we use, plugin in proper callbacks
        if progressCallback:
            progressCallback(1, 1)

        # well, since we dont have any knowledge about what the
        # channel version is supposed to be, I'cant really rely
        # on that (with up2date, the login tells me what channel
        # versions to look for). So we need a generic name
        # we symlink to the latest version.


        pipe = os.popen("/usr/bin/bunzip2 %s.bz2" % tmpfilename)
        tmp = pipe.read()

        os.symlink(tmpfilename, symlinkname)

        hdrList = rpm.readHeaderListFromFile(tmpfilename)
        # a list of rpm hdr's, handy!!

        pkgList = []

        for hdr in hdrList:
            epoch = hdr['epoch']
            if epoch == None or epoch == "0" or epoch == 0:
                epoch = ""
            pkgList.append([hdr['name'], hdr['version'],
                            hdr['release'], epoch, hdr['arch'],
                            # we want the actual filesize, but alas...
                            str(hdr['size']),
                            channel['label']])

            # what the hell, this is a little bit of a side effect, but
            # were already poking at headers, lets just save them while
            # were at it to same us some trouble
            rpmSourceUtils.saveHeader(hdr)
            self.headerCache["%s-%s-%s.%s" % (hdr['name'], hdr['version'],
                                              hdr['release'], hdr['arch'])] = hdr
             
        # nowwe have the package list, convert it to xmlrpc style
        # presentation and dump it
        pkgList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(pkgList, filePath, globPattern)


        return pkgList
        
    def getObsoletes(self, channel,
                     msgCallback = None,
                     progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])

        if msgCallback:
            msgCallback("Fetching obsoletes list for %s" % channel['url'])
            
        fileHdrList = "%s/link-%s" % (self.cfg['storageDir'], channel['label'])
        #print "fhl: %s" % fileHdrList

        
        hdrList = rpm.readHeaderListFromFile(fileHdrList)

        # FIXME: since we have the package list, and the headers, we dont
        # have to reload the headerlist...
        
        obsList = []
        total = len(hdrList)
        count = 0
        for hdr in hdrList:

            if progressCallback:
                progressCallback(count,total)
            count = count + 1
            # FIXME: we should share this logic somewhere...
            #   up2dateUtils maybe?
            if not hdr['obsoletes']:
                continue
            obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
            if obs:
                obsList = obsList + obs
                
        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        obsList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(obsList, filePath,globPattern) 

        return obsList


    def getHeader(self, package, msgCallback = None, progressCallback = None):
        # there are weird cases where this can happen, mostly as a result of
        # mucking with things in /var/spool/up2date
        #
        # not a particularly effiencent way to get the header, but we should
        # not get hit very often

        return None
        
 ##       channel =  rhnChannel.selected_channels.getByName(package[6])
##        fileHdrList = "/var/spool/up2date/link-%s" % (channel.name)
##        print "fhl: %s" % fileHdrList
##        hdrList = rpm.readHeaderListFromFile(fileHdrList)
##        for hdr in hdrList:
##            if package[0] != hdr['name']:
##                continue
##            if package[1] != hdr['version']:
##                continue
##            if package[2] != hdr['release']:
##                continue
##            if package[4] != hdr['arch']:
##                continue
            
##            rpmSourceUtils.saveHeader(hdr)
##            self.headerCache["%s-%s-%s.%s" % (hdr['name'], hdr['version'],
##                                              hdr['release'], hdr['arch'])] = hdr

##            return hdr
            
            

    def getPackage(self, package, msgCallback = None, progressCallback = None):
        filename = "%s-%s-%s.%s.rpm" % (package[0], package[1], package[2],
                                        package[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(package[6])
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        # FIXME: apt has some more sophisticated logic for actually finding
        # the package that this, probabaly need to implement to support
        # most repos
        url = "%s/RPMS.%s/%s" % (channel['url'], channel['dist'], filename)

        if msgCallback:
            #DEBUG
            msgCallback(filename)

        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Apt" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer
        
    def getPackageSource(self, channel, package, msgCallback = None, progressCallback = None):
        filename = package
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        if msgCallback:
            msgCallback(filename)
        url = "%s/SRPMS.%s/%s" % (channel['url'], channel['dist'], filename)

        
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Apt" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer

# see comment about YumDiskCache in yumRepo.py
class AptDiskCache(rpmSource.PackageSource):
    def __init__(self, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        globPattern = "%s/%s.*" %  (self.cfg["storageDir"], channel['label'])
        lists = glob.glob(globPattern)

        # FIXME?
        # we could sort and find the oldest, but there should
        # only be one
        
        if len(lists):
            localFilename = lists[0]
        else:
            # for now, fix PackageSourceChain to not freak
            # when everything returns None

            #FIXME
            return 12344444444444

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        tmp_args, tmp_method = xmlrpclib.loads(filecontents)
        
        # tmp_args[0] is the list of packages
        return tmp_args[0]
        

class AptRepo(genericRepo.GenericRepo):
    def __init__(self):
        genericRepo.GenericRepo.__init__(self)
        self.hds = rpmSource.DiskCache()
        self.ars = AptRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
        self.ads = AptDiskCache()
        self.hldc = rpmSource.LocalDisk()

        self.psc.headerCache = localHeaderCache

        

        self.sources = {'listPackages':[{'name':'apt', 'object': self.ars},
                                        {'name':'aptdiskcache', 'object':self.ads},
                                        ],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'apt', 'object': self.ars}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'apt', 'object': self.ars}],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hldc},
                                     {'name':'apt', 'object': self.ars}],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'apt', 'object': self.ars}
                                      ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'apt', 'object': self.ars}
                                            ]
                        
                        }

    def updateAuthInfo(self):
        pass

def register(rd):
    aptRepo = AptRepo()
    rd.handlers['apt']= aptRepo
    aptSolveDep = AptSolveDep()
    rd.depSolveHandlers['apt'] = aptSolveDep
    

########NEW FILE########
__FILENAME__ = dirRepo
#!/usr/bin/python


import os
import re
import sys
import time
import glob
import string
import fnmatch
import time  #remove

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import config
from up2date_client import rpcServer
from up2date_client import rpmUtils
from up2date_client import up2dateUtils
from up2date_client import transaction

import genericRepo
import genericSolveDep

class DirSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "dir"



#from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52664
def walk( root, recurse=0, pattern='*', return_folders=0 ):
    # initialize
    result = []
    
    # must have at least root folder
    try:
        names = os.listdir(root)
    except os.error:
        return result

    # expand pattern
    pattern = pattern or '*'
    pat_list = string.splitfields( pattern , ';' )
    
    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))

        # grab if it matches our pattern and entry type
        for pat in pat_list:
            if fnmatch.fnmatch(name, pat):
                if os.path.isfile(fullname) or (return_folders and os.path.isdir(fullname)):
                    result.append(fullname)
                continue

        # recursively scan other folders, appending results
        if recurse:
            if os.path.isdir(fullname) and not os.path.islink(fullname):
                result = result + walk( fullname, recurse, pattern, return_folders )

    return result



class DirRepoSource(rpmSource.PackageSource):
    def __init__(self, proxyHost=None,
                 loginInfo=None, cacheObject=None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self.headerCache = cacheObject
        self.obsList = []

        try:
            cmd = os.popen('uname -m')
            self._arch = cmd.read().strip('\n')
        except IOError:
            self._arch = 'unknown'

    def __getHeader(self, path):
        fd = os.open(path, os.R_OK)
        ts = transaction.initReadOnlyTransaction()
        
        try:
            hdr = ts.hdrFromFdno(fd)
        except:
            os.close(fd)
            return None
        os.close(fd)
        return hdr
   
    def _is_compatible_arch(self, arch):
        if rpm.archscore(arch) == 0:
            # Itanium special casing.
            if self._arch == 'ia64' and re.match('i.86', arch):
                return True
            else:
                return False
        else:
            return True

    def _get_all_packages_dict(self, path, label):
        rpmpaths = walk(path, recurse=0, pattern="*.rpm", return_folders=0)

        pkgsDict = {}
        for rpmpath in rpmpaths:
            filename = os.path.basename(rpmpath)
            bits = string.split(filename, ".")
            arch = bits[-2]
           
            if not self._is_compatible_arch(arch):
                continue

            # might as well collect the filesize 
            hdrBuf = self.__getHeader(rpmpath)
            # busted package of some sort, skip it
            if hdrBuf == None:
                continue
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())
            size = os.stat(rpmpath)[6]
            
            epoch = hdr['epoch']
            if epoch == None:
                epoch = ""
            else:
                epoch = str(epoch)
            
            pkg = [hdr['name'], hdr['version'], hdr['release'], epoch,
                hdr['arch'], size, label, rpmpath]

            # group packages by nvre and store the different arches in a list
            pkgNvre = tuple(pkg[:4])
            if not pkgsDict.has_key(pkgNvre):
                pkgsDict[pkgNvre] = []
            pkgsDict[pkgNvre].append(pkg)

        return pkgsDict

    def _package_list_from_dict(self, pkgsDict, storage_dir, label, name_suffix,
        version):
        pkgList = []
        names = pkgsDict.keys()
        names.sort()
        for name in names:
            pkgs = pkgsDict[name]
            for pkg in pkgs:
                pkgList.append(pkg)

        # nowi we have the package list, convert it to xmlrpc style
        # presentation and dump it
        filePath = "%s/%s%s.%s" % (storage_dir, label, name_suffix, version)
        fileGlobPattern = "%s/%s.*" % (storage_dir, label)
        
        rpmSourceUtils.saveListToDisk(pkgList, filePath, fileGlobPattern)

        return pkgList


    def listPackages(self, channel, msgCallback = None,
        progressCallback = None):
        pkgsDict = self._get_all_packages_dict(channel['path'],
            channel['label'])
            
        latestPkgsDict = {}
        for pkgNvre in pkgsDict.keys():
            # first version of this package, continue
            pkgName = pkgNvre[0]
            tupNvre = tuple(pkgNvre)
            if not latestPkgsDict.has_key(pkgName):
                latestPkgsDict[pkgName] = pkgsDict[tupNvre]
                continue


            ret = up2dateUtils.comparePackages(latestPkgsDict[pkgName][0],
                list(pkgNvre))
            if ret > 0:
                # don't care, we already have a better version
                continue
            if ret < 0:
                # Better version
                latestPkgsDict[pkgName] = pkgsDict[pkgNvre]
                continue
            # if it's 0, we already have it

        pkgList = self._package_list_from_dict(latestPkgsDict,
            self.cfg["storageDir"], channel['label'], "", channel['version'])

        # since were talking local file, and we are already
        # loading them up and poking at the headers, lets figure
        # out the obsoletes stuff now too while were at it
        self.obsList = []

        for pkg in pkgList:
            rpmpath = pkg[7]
            hdrBuf = self.__getHeader(rpmpath)
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())

            
            # look for header info
            if not hdr['obsoletes']:
                continue
            
            obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
            if obs:
                self.obsList = self.obsList + obs

        return pkgList

    def listAllPackages(self, channel, msgCallback = None,
        progressCallback = None):
        pkgs_dict = self._get_all_packages_dict(channel['path'],
            channel['label'])
        pkg_list = self._package_list_from_dict(pkgs_dict,
            self.cfg["storageDir"], channel['label'], "-all", 
            channel['version'])

        return pkg_list
   
    def getObsoletes(self, channel, msgCallback = None, progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])


        # if we already founf the list, just statsh it. However it
        # is possible for it to not exist (ie, user just delets the obsList
        # from the cache, but since the package list exists we never hit the
        # above code path. A FIXME
        if self.obsList:
            self.obsList.sort(lambda a, b: cmp(a[0], b[0]))
            rpmSourceUtils.saveListToDisk(self.obsList, filePath, globPattern)
            if progressCallback:
                progressCallback(1,1)
        else:
            if progressCallback:
                progressCallback(1,1)

        if self.obsList:
            return self.obsList
        return []
            

    
    def __saveHeader(self, hdr):
        tmp = rpmUtils.readHeaderBlob(hdr.unload())
        rpmSourceUtils.saveHeader(tmp)

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        channels = rhnChannel.getChannels()
        channel = channels.getByName(pkg[6])
        
        #filename = "%s/%s-%s-%s.%s.rpm" % (channel['path'],  pkg[0], pkg[1],
        #                                   pkg[2], pkg[4])
        filename = pkg[7]

        # package doesnt exist
        if not os.access(filename, os.R_OK):
            return None
        hdrBuf = self.__getHeader(filename)
        try:
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())
        except:
            return None
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
        self.__saveHeader(hdr)
        return hdr

            
    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        pkgFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2],
                                        pkg[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(pkg[6])
#        if msgCallback:
#            msgCallback(pkgFileName)

        storageFilePath = "%s/%s" % (self.cfg["storageDir"], pkgFileName)


        # symlink the file from /var/spool/up2date to whereever it is...
#        fileName = "%s/%s" % (channel['path'], pkgFileName)
        fileName = pkg[7]
        if (channel['path'] != self.cfg['storageDir']):
            try:
                os.remove(storageFilePath)
            except OSError:
                pass
            os.symlink(fileName, storageFilePath)

        if progressCallback:
            progressCallback(1,1)
        return 1


    # FIXME: need to add a path to SRPMS as well
    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        fileName = "%s/%s" % (channel['srpmpath'], srcpkg)
        if (channel['path'] != self.cfg['storageDir']):
            try:
                os.remove(fileName)
            except OSError:
                pass
            if msgCallback:
                msgCallback(fileName)
                os.symlink(tmpFileNames[0], fileName)
        
        return 1


class DirRepo(genericRepo.GenericRepo):
    def __init__(self):
        genericRepo.GenericRepo.__init__(self)
        self.hds = rpmSource.DiskCache()
        self.ds = DirRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hldc = rpmSource.LocalDisk()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
        self.hds = rpmSource.DiskCache()

        #FIXME: this functionality collides with the localDisk/-k stuff
        # a bit, need to figure out what to keep/toss
        self.hldc = rpmSource.LocalDisk()
        self.psc.headerCache = localHeaderCache

        # FIMXE: we need a way to figure out when a cached package list
        # is stale

        self.sources = {'listPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'dir', 'object':self.ds},
                                        ],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'dir', 'object':self.ds},
                                        ],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                       {'name':'diskcache', 'object':self.hds},
                                       {'name':'dir', 'object':self.ds},
                                       ],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hldc},
                                     {'name':'dir', 'object':self.ds},
                                     ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                             {'name':'diskcache', 'object':self.hds},
                                             {'name':'dir', 'object':self.ds},
                                             ],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                           {'name':'dir', 'object':self.ds}
                                           ]
                        }

    def updateAuthInfo(self):
        pass

def register(rd):
    dirRepo = DirRepo()
    rd.handlers['dir'] = dirRepo
    dirSolveDep = DirSolveDep()
    rd.depSolveHandlers['dir'] = dirSolveDep
        

########NEW FILE########
__FILENAME__ = genericRepo
#!/usr/bin/python


import os
import sys

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource

class GenericRepo:
    def __init__(self):
        self.psc = rpmSource.PackageSourceChain()
        self.sources = {}
        self.headerCache = None
        
    def __getattr__(self, name):
        self.psc.setSourceInstances(self.sources[name])
        if self.headerCache:
            self.psc.headerCache = self.headerCache
        return getattr(self.psc, name)



########NEW FILE########
__FILENAME__ = genericSolveDep
#!/usr/bin/python
import sys
import fnmatch
import UserDict
import pprint

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import config
from up2date_client import rpmUtils
from up2date_client import rhnChannel
from up2date_client import rpcServer
from up2date_client import up2dateLog
from up2date_client import repoDirector



class DictOfLists(UserDict.UserDict):
    def __init__(self, dict=None):
        UserDict.UserDict.__init__(self, dict)
    def __setitem__(self, key, value):
        if not self.data.has_key(key):
            self.data[key] = []
        self.data[key].append(value)
                                                                                                                                                      
    def getFlatList(self):
        x = self.keys()
        blip = []
        for i in x:
            for j in self[i]:
                blip.append((i, j))
        return blip



class GenericSolveDep:
    # so, what exactly does this do? well...
    # this is basically all to work around the fact that
    # when we solve a dep, we know what NVRE solves it
    # but not what arch. This used to not be a problem,
    # as you simply picked the best arch.
    #
    # However, with multilib/biarch, it means we have
    # to do some guessing. Basically, sometimes we only
    # want one arch, sometimes both, sometimes 1 or two
    # of the many arches available
    #
    # the cases where we only want one arch are:
    #    1. the other arch is already installed
    #    2. there is only one arch of that package available
    #    3. the user has specified a --arch, which means
    #       they want a particular arch install overriding 1&2
    #    4. We have both arches isntalled, and one of them
    #       is not the latest
    
    # the cases where we want to install "both" arches
    #    1. we have both arches installed, and there are
    #       newer versions available for both arches
    #    2. we have neither arch installed, but we need
    #       to install both to satisfy deps
    #          a. the same dep applies to both (aka, "libselinux")
    #          b. we have seperate deps that require each arch
    #              (aka, foo.i386 requires libbar.so,
    #                    foo.x86_64 requires libbar.so(64bit)
    #       (to some degree, the later gets done for seperate deps
    #        so doesnt factor into this particular function so
    #        much)
    
    # the cases where we want to install "some" of the arches
    #   These are kernel, glibc, gzip etc where there are
    #   two arch "colors" and more than one arch per color.
    #    aka, glibc.x86_64, glibc.i386, glibc.i686

    # Theres a few basket cases as well, for example when
    # you need to install "foobar" to solve a dep from
    # an x86_64 package and an i386 package. Doing this
    # correctly is further confused by the fact that we
    # dont know what arch of package raises a dep since it
    # is on the transaction as a whole, but we might be
    # able to change that?  WELL... we could... sorta
    # at least on RHEL4/FC3... the release of the package
    # that raises the deps is now actually "release.arch"
    # so thats a possibity, though it doesnt really help
    # us on RHEL2.1/RHEL3. But on RHEL4 we could pass it
    # in as part of the dep and use it as a hint...

    
    def __init__(self):
	self.selectedPkgs = []
        pass



    def __getSolutionsInstalled(self, solutions):
        solutionsInstalled = []
        for p in solutions:
            if self.installedPkgHash.has_key(p[0]):
                iList = self.installedPkgHash[p[0]]
                for iPkg in iList:
                    if self.availListHash.has_key(tuple(iPkg[:4])):
                        # find the avail packages as the same arch
                        # as the installed ones
                        for i in self.availListHash[tuple(p[:4])]:
                            solutionsInstalled.append(p)
        return solutionsInstalled
    
    def solveDep(self, unknowns, availList,
                 msgCallback = None,
                 progressCallback = None,
                 refreshCallback = None):
        self.cfg = config.initUp2dateConfig()
        self.log =  up2dateLog.initLog()
        self.log.log_me("solving dep for: %s" % unknowns)

        self.refreshCallback = refreshCallback
        self.progressCallback = progressCallback
        self.msgCallback = msgCallback
        self.availList = availList

        availList.sort()
        self.availListHash = {}
        for p in self.availList:
            if self.availListHash.has_key(tuple(p[:4])):
                self.availListHash[tuple(p[:4])].append(p)
            else:
                self.availListHash[tuple(p[:4])] = [p]
                
        self.retDict = {}
        self.getSolutions(unknowns,
                          progressCallback = self.progressCallback,
                          msgCallback = self.msgCallback)
        reslist = []

        self.depToPkg = DictOfLists()
        self.depsNotAvailable = DictOfLists()
#        self.depToPkg = {}
        #FIXME: this should be cached, I dont really need to query the db
        # for this everytime
        self.installedPkgList = rpmUtils.getInstalledPackageList(getArch=1)
        self.installedPkgHash = {}
        for pkg in self.installedPkgList:
            if self.installedPkgHash.has_key(pkg[0]):
                self.installedPkgHash[pkg[0]].append(pkg)
	    else:
            	self.installedPkgHash[pkg[0]] = [pkg]

        # we didnt get any results, bow out...
        if not len(self.retDict):
            return (reslist, self.depToPkg)
        
  


        newList = []
        availListNVRE = map(lambda p: p[:4], self.availList)

        failedDeps = []
        solutionPkgs = []
        pkgs = []
        for dep in self.retDict.keys():
            # skip the rest if we didnt get a result
            if len(self.retDict[dep]) == 0:
                continue

            solutions = self.retDict[dep]
            # fixme, grab the first package that satisfies the dep
            #   but make sure we match nvre against the list of avail packages
            #   so we grab the right version of the package
            # if we only get one soltution, use it. No point in jumping
            # though other hoops
            if len(solutions) == 1:
                for solution in solutions:
                    pkgs.append(solution)

            # we've got more than one possible solution, do some work
            # to figure out if I want one, some, or all of them
            elif len(solutions) > 1:
                # try to install the new version of whatever arch is
                # installed
                solutionsInstalled = self.__getSolutionsInstalled(solutions)
                found = 0

                if len(solutionsInstalled):
                    for p in solutionsInstalled:
                        pkgs.append(p)
                        self.depToPkg[dep] = p
                        found = 1
                    if found:
                        break
                # we dont have any of possible solutions installed, pick one
                else:
                    # this is where we could do all sort of heuristics to pick
                    # best one. For now, grab the first one in the list thats
                    # available

                    #FIXME: we need to arch score here for multilib/kernel
                    # packages that dont have a version installed

                    # This tends to happen a lot when isntalling into
                    # empty chroots (aka, pick which of the kernels to
                    # install).

                    # ie, this is the pure heuristic approach...

                    shortest = solutions[0]
                    for solution in solutions:
                        if len(shortest[0]) > len(solution[0]):
                            shortest = solution

                    # if we get this far, its still possible that we have package
                    # that is multilib and we need to install both versions of
                    # this is a check for that...
                    if self.installedPkgHash.has_key(shortest[0]):
                        iList = self.installedPkgHash[shortest[0]]
                        for iPkg in iList:
                            if self.availListHash.has_key(tuple(shortest[:4])):
                                for i in self.availListHash[tuple(shortest[:4])]:
                                    if self.cfg['forcedArch']:
                                        arches = self.cfg['forcedArch']
                                        if i[4] in arches:
                                            pkgs.append(i)
                                            self.depToPkg[dep] = i
                                            break
                                    else:
                                        # its not the same package we have installed
                                        if iPkg[:5] != i[:5]:
                                            # this arch matches the arch of a package
                                            # installed
                                            if iPkg[4] == i[4]:
                                                pkgs.append(i)
                                                self.depToPkg[dep] = i
                                        break


                    # you may be asking yourself, wtf is that madness that follows?
                    # well, good question...
                    # its basically a series of kluges to work around packaging problems
                    # in RHEL-3 (depends who you ask... But basically, its packages doing
                    # stuff that was determined to be "unsupported" at the time of the
                    # initial multilib support, but packages did it later anyway

                    # Basically, what we are trying to do is pick the best arch of
                    # a package to solve a  dep. Easy enough. The tricky part is
                    # what happens when we discover the best arch is already in
                    # transation and is _not_ solving the dep, so we need to look
                    # at the next best arch. So we check to see if we added it to
                    # the list of selected packges already, and if so, add the
                    # next best arch to the set. To make it uglier, the second best
                    # arch might not be valid at all, so in that case, dont use it
                    # (which will cause an unsolved dep, but they happen...)

                    if self.availListHash.has_key(tuple(shortest[:4])):
                        avail = self.availListHash[tuple(shortest[:4])]                            
                        bestArchP = None
                        useNextBestArch = None
                        bestArchP2 = None

                        # a saner approach might be to find the applicable arches,
                        # sort them, and walk over them in order

                        # remove the items with archscore <= 0
                        app_avail = filter(lambda a: rpm.archscore(a[4]), avail)
                        # sort the items by archscore, most approriate first
                        app_avail.sort(lambda a,b: cmp(rpm.archscore(a[4]),rpm.archscore(b[4])))

                        # so, whats wrong with this bit? well, if say "libgnutls.so(64bit)" doesn't
                        # find a dep, we'll try to solve it with gnutls.i386
                        # its because "gnutls" and "libgnutls.so(64bit)" are in the same set of
                        # deps. Since gnutls.x86_64 is added for the "gnutls" dep, its in the
                        # list of already selected for 
                        for i in app_avail:
                            if i in self.selectedPkgs:
                                continue
                            pkgs.append(i)
                            self.depToPkg[dep] = i
                            # we found something, stop iterating over available
                            break
                        # we found something for this dep, stop iterating
                        continue


            else:
                # FIXME: in an ideal world, I could raise an exception here, but that will break the current gui
                pkgs.append(p)                    
                self.depToPkg[dep] = p
                # raise UnsolvedDependencyError("Packages %s provide dep %s but are not available for install based on client config" % (pkgs,dep), dep, pkgs )

        for pkg in pkgs:
            self.selectedPkgs.append(pkg)
            if pkg[:4] in availListNVRE:
                newList.append(pkg)
            else:
                newList.append(pkg)
            reslist = newList
        # FIXME: we need to return the list of stuff that was skipped
        # because it wasn't on the available list and present it to the
        # user something like:
        # blippy-1.0-1  requires barpy-2.0-1 but barpy-3.0-1 is already isntalled
        #print "\n\nself.depsNotAvailable"
        #pprint.pprint(self.depsNotAvailable)
        #pprint.pprint(self.depToPkg)
        return (reslist, self.depToPkg)

class SolveByHeadersSolveDep(GenericSolveDep):
    def __init__(self):
        GenericSolveDep.__init__(self)

    def getHeader(self, pkg,
                  msgCallback = None,
                  progressCallback = None ):
        self.repos = repoDirector.initRepoDirector()
        hdr, type = rpcServer.doCall(self.repos.getHeader, pkg,
                                     msgCallback = msgCallback,
                                     progressCallback = progressCallback)
        return hdr
        
    def getSolutions(self, unknowns, msgCallback = None, progressCallback = None):
        channels = rhnChannel.getChannels()
        repoChannels = channels.getByType(self.type)
        repoPackages = []
        channelNames = []

        for channel in repoChannels:
            channelNames.append(channel['label'])

        for pkg in self.availList:
            if pkg[6] in channelNames:
                repoPackages.append(pkg)

        solutions = {}
        totalLen = len(repoPackages)
        count = 0
        # dont show the message if were not going to do anything
        if msgCallback and totalLen:
            msgCallback("Downloading headers to solve dependencies")
        for pkg in repoPackages:
            hdr = self.getHeader(pkg)
            if progressCallback:                
                progressCallback(count, totalLen)
            count = count + 1 
            # this bit basically straight out of yum/pkgaction.py GPL Duke Univeristy 2002
            fullprovideslist = hdr[rpm.RPMTAG_PROVIDES]
            if hdr[rpm.RPMTAG_FILENAMES] != None:
                fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_FILENAMES]
            if hdr[rpm.RPMTAG_DIRNAMES] != None:
                fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_DIRNAMES]
            unknownsCopy = unknowns[:]
            for unknown in unknowns:
                for item in fullprovideslist:
                    if unknown == item:
                        if solutions.has_key(unknown):
                            solutions[unknown].append(pkg)
                        else:
                            solutions[unknown] = [pkg]
                        try:
                            unknownsCopy.remove(unknown)
                        except ValueError:
                            # already removed from list
                            pass
                        if len(unknownsCopy) == 0:
                            break
            del fullprovideslist
                

        self.retDict = solutions


##class YumSolveDep(SolveByHeadersSolveDep):
##    def __init__(self):
##        SolveByHeadersSolveDep.__init__(self)
##        self.type = "yum"
        


class AptSolveDep(SolveByHeadersSolveDep):
    def __init__(self):
        SolveByHeadersSolveDep.__init__(self)
        self.type = "apt"

##class DirSolveDep(SolveByHeadersSolveDep):
##    def __init__(self):
##        SolveByHeadersSolveDep.__init__(self)
##        self.type = "dir"

########NEW FILE########
__FILENAME__ = up2dateRepo
#!/usr/bin/python

import os
import sys

import rpm
sys.path.append("/usr/share/rhn/")
import genericRepo
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import up2dateAuth
from up2date_client import rpcServer
from up2date_client import config
from up2date_client import up2dateUtils
from up2date_client import up2dateErrors
from up2date_client import rpmUtils
from up2date_client import rpcServer

import genericSolveDep

from rhn import rpclib, xmlrpclib



#FIXME: split it it so we seperate the "pick the best of the options"
#       and the "get the options" stuff and then share "pick the best of the options" stuff
class RhnSolveDep(genericSolveDep.GenericSolveDep):
    def __init__(self):
        genericSolveDep.GenericSolveDep.__init__(self)
        
    def getSolutions(self, unknowns, progressCallback = None, msgCallback = None):
        s = rpcServer.getServer(refreshCallback=self.refreshCallback)
        try:
            tmpRetList = rpcServer.doCall(s.up2date.solveDependencies,
                                            up2dateAuth.getSystemId(),
                                            unknowns)
        except rpclib.Fault, f:
            if f.faultCode == -26:
                #raise RpmError(f.faultString + _(", depended on by %s") % unknowns)
                raise up2dateErrors.RpmError(f.faultString)
            else:
                 raise up2dateErrors.CommunicationError(f.faultString)


        self.retDict = {}
        for unknown in tmpRetList.keys():
            if len(tmpRetList[unknown]) == 0:
                continue
            solutions = tmpRetList[unknown]

            # solution at this point is just [n,v,r,e]
            # so we find all the packages of that nvre, download the headers
            # and walk over the headers looking for more exact matches
            for solution in solutions:
                deppkgs = []
                hdrlist = []
                p = solution
                if self.availListHash.has_key(tuple(p[:4])):
                    for i in self.availListHash[tuple(p[:4])]:
                        deppkgs.append(i)

                for i in deppkgs:
                    hdr = self.getHeader(i)
                    hdrlist.append(hdr)

                answerlist = []
                for hdr in hdrlist:
                    fullprovideslist = hdr[rpm.RPMTAG_PROVIDES]
                    if hdr[rpm.RPMTAG_FILENAMES] != None:
                        fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_FILENAMES]
                    if hdr[rpm.RPMTAG_DIRNAMES] != None:
                        fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_DIRNAMES]
                    for item in fullprovideslist:
                        if unknown == item:
                            answerlist.append(hdr)

                for a in answerlist:
                    epoch = a['epoch']
                    if epoch == None:
                        epoch = ""
                    for i in self.availListHash[(a['name'], a['version'], a['release'], "%s" % epoch)]:
                        #                    print "\nI ", i
                        # just use the right arches
                        if a['arch'] == i[4]:
#                            print "SOLVING %s with %s" % (unknown, i)
                            if not self.retDict.has_key(unknown):
                                self.retDict[unknown] = []
                            self.retDict[unknown].append(i)

    def getHeader(self, pkg,
                  msgCallback = None,
                  progressCallback = None ):
        self.repos = repoDirector.initRepoDirector()
        hdr, type = rpcServer.doCall(self.repos.getHeader, pkg,
                                     msgCallback = msgCallback,
                                     progressCallback = progressCallback)
        return hdr
        

class HttpGetSource(rpmSource.PackageSource):
    def __init__(self, server, proxyHost,
                 loginInfo = None, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        self.s = server
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self._loginInfo=up2dateAuth.loginInfo

    # we need to relogin if we get a an auth time out, plus we need to
    # create a new server object with that auth info
    def updateAuthInfo(self):
        li = up2dateAuth.updateLoginInfo()
        self._loginInfo=li
        serverSettings = ServerSettings()
        self.s = getGETServer(li, serverSettings)

    def _readFD(self, fd, filename, fileflags, pdLen, status, startpoint=0):
        # Open the storage file
        f = open(filename, fileflags)

        # seek to the start point, overwriting the last bits
        if pdLen and status != 200:
            f.seek(startpoint)

        while 1:
            chunk = fd.read(rpmSource.BUFFER_SIZE)
            l = len(chunk)
            if not l:
                break
            f.write(chunk)
            
        f.flush()
        # Rewind
        f.seek(0, 0)
        return f.read()
            

    def getHeader(self, package, msgCallback = None, progressCallback = None):
        hdr = None
        # package list format
        # 0        1        3       4     5     6      7
        # name, version, release, epoch, arch, size, channel

        filename = "%s-%s-%s.%s.hdr" % (package[0], package[1], package[2],
            package[4])
        channel = package[6]

        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        self.s.set_progress_callback(progressCallback,rpmSource.BUFFER_SIZE )
        
        fd = self.s.getPackageHeader(channel, filename)

        pkgname = "%s-%s-%s" % (package[0], package[1], package[2])
        if msgCallback:
            msgCallback(filename)

        buffer = fd.read()
        open(filePath, "w+").write(buffer)
        fd.close()

        hdr = rpmUtils.readHeaderBlob(buffer)
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache["%s-%s-%s.%s" % (hdr['name'],
                                       hdr['version'],
                                       hdr['release'],
                                       hdr['arch'])] = hdr
        return hdr

    
    def getPackage(self, package, msgCallback = None, progressCallback = None):
 #       print "gh 232423423423"
        filename = "%s-%s-%s.%s.rpm" % (package[0], package[1], package[2],
                                        package[4])

        partialDownloadPath = "%s/%s" % (self.cfg["storageDir"], filename)
        if os.access(partialDownloadPath, os.R_OK):
            pdLen = os.stat(partialDownloadPath)[6]
        else:
            pdLen = None

        self.s.set_transport_flags(allow_partial_content=1)

        startpoint = 0
        if pdLen:
            size = package[5]
            # trim off the last kb since it's more likely to
            # be trash on a reget
            startpoint = long(pdLen) - 1024
            
        channel = package[6]

        if msgCallback:
            msgCallback(filename)

#        print progressCallback
#        print "\nself.s", self.s, progressCallback
        self.s.set_progress_callback(progressCallback, rpmSource.BUFFER_SIZE )
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        if pdLen:
            fd = self.s.getPackage(channel, filename, offset=startpoint)
        else:
            fd = self.s.getPackage(channel, filename)
         
        if pdLen:
            fflag = "r+"
        else:
            fflag = "w+"

        status = self.s.get_response_status()
        f = open(filePath, fflag)
        if pdLen and status != 200:
            f.seek(startpoint)
        f.write(fd.read())
        f.flush()
        f.close()

#        self._readFD(fd,filePath,fflag, pdLen, status, startpoint)
        
        fd.close()

        # verify that the file isnt corrupt, if it,
        # download it again in its entirety
        if not rpmUtils.checkRpmMd5(filePath):
            f = open(filePath, "w+")
            fd = self.s.getPackage(channel, filename)
            buffer = fd.read()
            f.write(buffer)
            f.close()
            fd.close()
        
        buffer = open(filePath, "r").read()    
        return buffer

    
    def getPackageSource(self, channel, package,
                         msgCallback = None, progressCallback = None):
        filename = package

        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        self.s.set_progress_callback(progressCallback,rpmSource.BUFFER_SIZE )
        fd = self.s.getPackageSource(channel['label'], filename)

        if msgCallback:
            msgCallback(package)

        channel = package[6]

        startpoint = 0
        pdLen = None
        fflag = "w+"
        status = self.s.get_response_status()
        buffer = self._readFD(fd, filePath, fflag, pdLen, status, startpoint)
        fd.close()
        return buffer
        

    def listPackages(self, channel,msgCallback = None, progressCallback = None):
        filePath = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])

        self.s.set_progress_callback(progressCallback)

        # FIXME: I still dont like the seemingly arbitrary fact that this
        # method returns a python structure, and all the other gets return
        # a file descriptor.
        list = self.s.listPackages(channel['label'], channel['version'])
        

        # do something to save it to disk.
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)

        return list

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        self.s.set_progress_callback(progressCallback)

        # FIXME: I still dont like the seemingly arbitrary fact that this
        # method returns a python structure, and all the other gets return
        # a file descriptor.
        list = self.s.listAllPackages(channel['label'], channel['version'])
        

        # do something to save it to disk.
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)

        return list


    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                            channel['label'])
        self.s.set_progress_callback(progressCallback)
        obsoletes = self.s.getObsoletes(channel['label'], channel['version'])
        
       
        rpmSourceUtils.saveListToDisk(obsoletes, filePath, globPattern)
        return obsoletes

def getGETServer(logininfo, serverSettings):
    server= rpcServer.RetryGETServer(serverSettings.serverList.server(),
                                     proxy = serverSettings.proxyUrl,
                                     username = serverSettings.proxyUser,
                                     password = serverSettings.proxyPassword,
                                     headers = logininfo)
    server.add_header("X-Up2date-Version", up2dateUtils.version())
    server.addServerList(serverSettings.serverList)
    return server


# containment class for handling server config info
class ServerSettings:
    def __init__(self):
        self.cfg = config.initUp2dateConfig()
        self.xmlrpcServerUrl = self.cfg["serverURL"]
        refreshServerList = 0
	if self.cfg["useNoSSLForPackages"]:
            self.httpServerUrls = self.cfg["noSSLServerURL"]
            refreshServerList = 1
	else:
	    self.httpServerUrls = self.cfg["serverURL"]

        if type(self.httpServerUrls) == type(""):
            self.httpServerUrls = [self.httpServerUrls]

        self.serverList = rpcServer.initServerList(self.httpServerUrls)
        # if the list of servers for packages and stuff is different,
        # refresh
        if refreshServerList:
            self.serverList.resetServerList(self.httpServerUrls)

        self.proxyUrl = None
        self.proxyUser = None
        self.proxyPassword = None
        
        if self.cfg["enableProxy"] and up2dateUtils.getProxySetting():
            self.proxyUrl = up2dateUtils.getProxySetting()
            if self.cfg["enableProxyAuth"]:
                if self.cfg["proxyUser"] and self.cfg["proxyPassword"]:
                    self.proxyPassword = self.cfg["proxyPassword"]
                    self.proxyUser = self.cfg["proxyUser"]
                    
    def settings(self):
        return self.xmlrpcServerUrl, self.httpServerUrls, \
               self.proxyUrl, self.proxyUser, self.proxyPassword

class Up2dateRepo(genericRepo.GenericRepo):
    def __init__(self):
        self.login = None
        genericRepo.GenericRepo.__init__(self)
        self.cfg = config.initUp2dateConfig()
        li = up2dateAuth.getLoginInfo()

        serverSettings = ServerSettings()
        self.httpServer = getGETServer(li,
                                       serverSettings)
        localHeaderCache = rpmSource.HeaderCache()
        self.gds = HttpGetSource(self.httpServer, None)
        self.hds = rpmSource.DiskCache()
        self.lds = rpmSource.LocalDisk()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
#        localHeaderCache = rpmSource.HeaderCache()
        self.psc.headerCache = localHeaderCache

        # header needs to be a shared object between several
        # different classes and isntances, so it's a bit weird.
        # should maybe reimplement it as class level storage
        # bits and shared onjects...

        
        self.sources = {'listPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'getPackage':[{'name':'localdisk','object':self.lds},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'get', 'object': self.gds},
                                     ],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hds},
                                     {'name':'get', 'object': self.gds}
                                     ],
                        'getPackageSource':[{'name':'localdisk','object':self.lds},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'get', 'object': self.gds},
                                     ],
                        }

    def updateAuthInfo(self):
        self.gds.updateAuthInfo()

        
def register(rd):
    up2dateRepo = Up2dateRepo()
    rd.handlers['up2date']=up2dateRepo
    rhnSolveDep = RhnSolveDep()
    rd.depSolveHandlers['up2date'] = rhnSolveDep
    
    
    




########NEW FILE########
__FILENAME__ = urlUtils
#!/usr/bin/python

# a url handler for non rhnlib stuff, based _heavily_ on
# http://diveintomark.org/projects/feed_parser/
# by  "Mark Pilgrim <http://diveintomark.org/>"
#  "Copyright 2002-3, Mark Pilgrim"

import sys
import urllib2
import StringIO
import gzip
import time
import re

from up2date_client import up2dateErrors

BUFFER_SIZE=8092
class MiscURLHandler(urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
	#print "code: %s" % code
        if ((code / 100) == 3) and (code != 304):
            return self.http_error_302(req, fp, code, msg, headers)
        if ((code / 100) == 4) and (code not in [404]):
            return self.http_error_404(req, fp, code, msg, headers)
        from urllib import addinfourl
        infourl = addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
#        raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
        return infourl


    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        if not hasattr(infourl, "status"):
            infourl.status = code

        return infourl

    def http_error_301(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    def http_error_404(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPDefaultErrorHandler.http_error_default(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    def http_error_403(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPDefaultErrorHandler.http_error_default(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    http_error_300 = http_error_302
    http_error_307 = http_error_302

def open_resource(source, etag=None, modified=None, agent=None, referrer=None, startRange=None, endRange=None):
    """
    URI, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it must be a tuple of 9 integers
    as returned by gmtime() in the standard Python time module. This MUST
    be in GMT (Greenwich Mean Time). The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.
    """

    if hasattr(source, "read"):
        return source

    if source == "-":
        return sys.stdin

    if not agent:
        agent = USER_AGENT
        
    # try to open with urllib2 (to use optional headers)
    request = urllib2.Request(source)
    if etag:
        request.add_header("If-None-Match", etag)
    if modified:
        request.add_header("If-Modified-Since", format_http_date(modified))
    request.add_header("User-Agent", agent)
    if referrer:
        request.add_header("Referer", referrer)
        request.add_header("Accept-encoding", "gzip")
    start = 0
    if startRange:
        start = startRange
    end = ""
    if endRange:
        end = endRange
    if startRange or endRange:
        range = "bytes=%s-%s" % (start, end)
        print range
        request.add_header("Range", range)
                           
    opener = urllib2.build_opener(MiscURLHandler())
    #print request.headers
    opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
    #return opener.open(request)
    try:
        return opener.open(request)
    except OSError:
	print "%s not a valud URL" % source
        # source is not a valid URL, but it might be a valid filename
        pass
    except ValueError:
	print "%s is of an unknown URL type" % source
    	pass


    # try to open with native open function (if source is a filename)
    try:
        return open(source)
    except:
	print sys.exc_info()
	print sys.exc_type
        pass

    # huh, not sure I like that at all... probabaly need
    # to change this to returning a fd/fh and reading on it.
    # but shrug, this is just for local files anway... -akl
    # treat source as string
    return StringIO.StringIO(str(source))

def get_etag(resource):
    """
    Get the ETag associated with a response returned from a call to 
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify an ETag for the resource, this will return None.
    """

    if hasattr(resource, "info"):
        return resource.info().getheader("ETag")
    return None

def get_modified(resource):
    """
    Get the Last-Modified timestamp for a response returned from a call to
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify a Last-Modified timestamp, this function will return None.
    Otherwise, it returns a tuple of 9 integers as returned by gmtime() in
    the standard Python time module().
    """

    if hasattr(resource, "info"):
        last_modified = resource.info().getheader("Last-Modified")
        if last_modified:
            return parse_http_date(last_modified)
    return None

short_weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
long_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_http_date(date):
    """
    Formats a tuple of 9 integers into an RFC 1123-compliant timestamp as
    required in RFC 2616. We don't use time.strftime() since the %a and %b
    directives can be affected by the current locale (HTTP dates have to be
    in English). The date MUST be in GMT (Greenwich Mean Time).
    """

    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (short_weekdays[date[6]], date[2], months[date[1] - 1], date[0], date[3], date[4], date[5])

def parse_http_date2(date):
    # I'm linux only, so just use strptime()
    # attemp to parse out the Last-Modified time
    # It means I can continue to avoid the use of
    # regexs if at all possible as well :->
    try:
        return time.strptime(date, "%a, %d %b %Y %H:%M:%S GMT")
    except:
        try:
            return time.strptime(date, "%A, %d-%b-%y %H:%M:%S GMT")
        except:
            try:
                return time.strptime(date, "%a %b %d %H:%M:%S %Y")
            except:
                return None



rfc1123_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}), (?P<day>\d{2}) (?P<month>[A-Z][a-z]{2}) (?P<year>\d{4}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
rfc850_match = re.compile(r"(?P<weekday>[A-Z][a-z]+), (?P<day>\d{2})-(?P<month>[A-Z][a-z]{2})-(?P<year>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
asctime_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}) (?P<month>[A-Z][a-z]{2})  ?(?P<day>\d\d?) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) (?P<year>\d{4})").match

def parse_http_date(date):
    """
    Parses any of the three HTTP date formats into a tuple of 9 integers as
    returned by time.gmtime(). This should not use time.strptime() since
    that function is not available on all platforms and could also be
    affected by the current locale.
    """

    date = str(date)
    year = 0
    weekdays = short_weekdays

    m = rfc1123_match(date)
    if not m:
        m = rfc850_match(date)
        if m:
            year = 1900
            weekdays = long_weekdays
        else:
            m = asctime_match(date)
            if not m:
                return None

    try:
        year = year + int(m.group("year"))
        month = months.index(m.group("month")) + 1
        day = int(m.group("day"))
        hour = int(m.group("hour"))
        minute = int(m.group("minute"))
        second = int(m.group("second"))
        weekday = weekdays.index(m.group("weekday"))
        a = int((14 - month) / 12)
        julian_day = (day - 32045 + int(((153 * (month + (12 * a) - 3)) + 2) / 5) + int((146097 * (year + 4800 - a)) / 400)) - (int((146097 * (year + 4799)) / 400) - 31738) + 1
        daylight_savings_flag = 0
        return (year, month, day, hour, minute, second, weekday, julian_day, daylight_savings_flag)
    except:
        # the month or weekday lookup probably failed indicating an invalid timestamp
        return None

def get_size(resource):
    if hasattr(resource, "info"):
        size = resource.info().getheader("Content-Length")
        if size == None:
            return size
        # packages can be big
        return long(size)
    return None


def readFDBuf(fd, progressCallback = None):
    # Open the storage file
    
    buf = ""

    size = get_size(fd)
    if size == None:
        return None
    size_read = 0
    while 1:
        chunk = fd.read(BUFFER_SIZE)
        l = len(chunk)
        if not l:
            break
        size_read = size_read + l
        buf = buf + chunk
        if progressCallback:
            progressCallback(size_read,size) 
    return buf



def readFDBufWriteFD(fd, writefd, progressCallback = None):
    # Open the storage file
    
    buf = ""

    startTime = time.time()
    lastTime = startTime
    
    size = get_size(fd)
    if size == None:
        return None

    size_read = 0
    while 1:
        curTime = time.time()
        chunk = fd.read(BUFFER_SIZE)
        l = len(chunk)
        if not l:
            break
        size_read = size_read + l
        amt = size - size_read
        if progressCallback:
            if curTime - lastTime >= 1 or amt == 0:
                lastTime = curTime
                bytesRead = float(size - amt)
                # if amt == 0, on a fast machine it is possible to have 
                # curTime - lastTime == 0, so add an epsilon to prevent a division
                # by zero
                speed = bytesRead / ((curTime - startTime) + .000001)
                if size == 0:
                    secs = 0
                else:
                    # speed != 0 because bytesRead > 0
                    # (if bytesRead == 0 then origsize == amt, which means a read
                    # of 0 length; but that's impossible since we already checked
                    # that l is non-null
                    secs = amt / speed
                progressCallback(size_read, size, speed, secs)
        writefd.write(chunk)
    writefd.flush()
    writefd.seek(0,0)
    
    return 1

# need to add callbacks at some point
def fetchUrl(url, progressCallback=None, msgCallback=None,
             lastModified=None, agent=None, start=None, end=None):
    fh = open_resource(url, modified=lastModified,
                       agent = agent, startRange=start,
                       endRange=end)

    if hasattr(fh,'status'):
        if fh.status == 304:
#            print "Header info not modified"
            return None

    # hook in progress callbacks
    lmtime = get_modified(fh)
    if not lmtime:
        lmtime = time.gmtime(time.time())

    #buffer = fh.read()
    buffer = readFDBuf(fh, progressCallback) 
    fh.close()

    return (buffer, lmtime)


# need to add callbacks at some point
def fetchUrlAndWriteFD(url, writefd, progressCallback=None, msgCallback=None,
             lastModified=None, agent=None):
    fh = open_resource(url, modified=lastModified,
                                    agent = agent)

    if hasattr(fh,'status'):
        if fh.status == 304:
#            print "Header info not modified"
            return None

    # hook in progress callbacks
    lmtime = get_modified(fh)
    if not lmtime:
        lmtime = time.gmtime(time.time())

    #buffer = fh.read()
    ret =  readFDBufWriteFD(fh, writefd, progressCallback) 
    fh.close()

    return (lmtime)

#    return (buffer, lmtime)

def main():
    fh = open_resource("http://www.japanairband.com/sdfsdfasdferwregsdfg/",
                       agent = "foobar")
    print fh

    if hasattr(fh, 'status'):
        print "status: %s" % fh.status
    else:
        print "no status"


if __name__ == "__main__":
    main()
    

########NEW FILE########
__FILENAME__ = yumRepo
#!/usr/bin/python


import os
import sys
import time
import glob
import gzip
import string
import urllib
import xmlrpclib

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import rpmUtils
from up2date_client import config
from up2date_client import rpcServer
from up2date_client import up2dateUtils

import genericRepo
import urlUtils
import genericSolveDep

class YumSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "yum"


class YumRepoSource(rpmSource.PackageSource):
    def __init__(self, proxyHost=None,
                 loginInfo=None, cacheObject=None,
                 register=None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self._loginInfo=loginInfo
        self.headerCache = cacheObject
        self.pkglists = {}


    # stright out of yum/clientstuff.py
    # might as well use there code to parse there info
    def _stripENVRA(self,str):
        archIndex = string.rfind(str, '.')
        arch = str[archIndex+1:]
        relIndex = string.rfind(str[:archIndex], '-')
        rel = str[relIndex+1:archIndex]
        verIndex = string.rfind(str[:relIndex], '-')
        ver = str[verIndex+1:relIndex]
        epochIndex = string.find(str, ':')
        epoch = str[:epochIndex]
        name = str[epochIndex + 1:verIndex]
        return (epoch, name, ver, rel, arch)


    def getHeader(self, package, msgCallback = None, progressCallback = None):
        # yum adds the epoch into the filename of the header, so create the
        # approriate remotename, handling epoch=0 crap as well
        if package[3] == "":
            remoteFilename = "%s-%s-%s-%s.%s.hdr" % (package[0], "0", package[1], package[2],
                                        package[4])
        else:
            remoteFilename = "%s-%s-%s-%s.%s.hdr" % (package[0], package[3], package[1], package[2],
                                        package[4])

        if msgCallback:
            msgCallback(remoteFilename)

        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(package[6])
        url = "%s/headers/%s" % (channel['url'],remoteFilename )
	if msgCallback:
		msgCallback("Fetching %s" % url)
        # heck, maybe even borrow the one from yum

        
        nohdr = 1
        count = 0
        while ((nohdr) and (count < 5)):
            count = count + 1 
            try:
                # fix this to use fetchUrl and stringIO's for gzip
                (fn, h) = urllib.urlretrieve(url)
                
                #        print fn
                # the yum headers are gzip'ped
                fh = gzip.open(fn, "r")
                
                hdrBuf = fh.read()
                
                # FIXME: lame, need real callbacks
                if progressCallback:
                    progressCallback(1,1)
            
                hdr = rpmUtils.readHeaderBlob(hdrBuf)
                rpmSourceUtils.saveHeader(hdr)
                self.headerCache["%s-%s-%s" % (hdr['name'],
                                               hdr['version'],
                                               hdr['release'])] = hdr
                nohdr = 0
            except:
                print "There was an error downloading:", "%s"  % url
                nohdr = 1

        return hdr

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        filename = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2],
                                        pkg[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(pkg[6])

	#print "self.pkgNamePath: %s" % self.pkgNamePath
        #print "stored rpmpath: %s" % self.pkgNamePath[(pkg[0], pkg[1], pkg[2], pkg[3], pkg[4])]
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
	#rpmPath = self.pkgNamePath[(pkg[0], pkg[1], pkg[2], pkg[3], pkg[4])]
        rpmPath = pkg[7]

        url = "%s/%s" % (channel['url'],rpmPath )
        if msgCallback:
            # for now, makes it easier to debug
            #msgCallback(url)
            msgCallback(filename)


            
        
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Yum" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer


    def getPackageSource(self, channel, package, msgCallback = None, progressCallback = None):
        filename = package
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        if msgCallback:
            msgCallback(package)
            
        # interesting, yum doesnt seem to let you specify a path for the
        # source rpm...

        # Actually, it does now, but I need to download another meta data
        # file to do it, will do but not till .16 or so

        url = "%s/SRPMS/%s" % (channel['url'], filename)

               
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Yum" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer
    

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        # TODO: where do we implement cache validation? guess we
        # use http header time stamps to make a best guess since we
        # dont have any real info about the file format
        
        # a glob used to find the old versions to cleanup

        # FIXME: this is probabaly overkill... Should only have
        # one version of any given
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])
        oldLists = glob.glob(globPattern)
        channelTimeStamp = None
        if oldLists:
            filename = oldLists[0]
            filename = os.path.basename(filename)
            oldVersion = string.split(filename, '.')[-1]
            channelTimeStamp = time.strptime(oldVersion,"%Y%m%d%H%M%S")


        # for yum stuff, we assume that serverUrl is the base
        # path, channel is the relative path, and version isnt
        # user
        url = "%s/headers/header.info" % (channel['url'])
        if msgCallback:
            msgCallback("Fetching %s" % url)

        # oh, this lame, but implement a fancy url fetcher later
        # heck, maybe even borrow the one from yum
        #print urlUtils
        
        ret = urlUtils.fetchUrl(url, lastModified=channelTimeStamp,
                                progressCallback = progressCallback,
                                agent = "Up2date %s/Yum" % up2dateUtils.version())
        
        if ret:
            (buffer, lmtime) = ret
        else:
            return None

        if not lmtime:
            lmtime = time.gmtime(time.time())
        version = time.strftime("%Y%m%d%H%M%S", lmtime)
        
        # use the time stamp on the headerlist as the channel "version"
        filePath = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], version)

        # it's possible to get bogus data here, so at least try not
        # to traceback
        if buffer:
            lines = string.split(buffer)
        else:
            lines = []

        # this gives us the raw yum header list, which is _not_
        # in the pretty format up2date likes, so convert it
        # and sadly, I can no longer proudly state that up2date
        # at no points attempts to parse rpm filenames into something
        # useful. At least yum includes the epoch
        pkgList = []
        # yum can have a different path for each rpm. Not exactly
        # sure how this meets the "keep it simple" idea, but alas
        self.pkgNamePath = {}
        for line in lines:
            if line == "" or line[0] == "#":
                continue
            (envra, rpmPath) = string.split(line, '=')
            rpmPath = string.strip(rpmPath)
            (epoch, name, ver, rel, arch) = self._stripENVRA(envra)
            # quite possibly need to encode channel info here as well
	    if epoch == "0" or epoch == 0:
                epoch = ""

            # hmm, if an arch doesnt apply, guess no point in
            # keeping it around, should make package lists smaller
            # and cut down on some churn
            if rpm.archscore(arch) == 0:
                continue



            self.pkgNamePath[(name,ver,rel,epoch,arch)] = rpmPath
            # doh, no size info. FIXME
            size = "1000"  # er, yeah... thats not lame at all...
            pkgList.append([name, ver, rel, epoch, arch, size, channel['label'], rpmPath])

        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        pkgList.sort(lambda a, b: cmp(a[0], b[0]))
        
        count = 0
        total = len(pkgList)
        rd = repoDirector.initRepoDirector()
        
        for pkg in pkgList:
            # were deep down in the yum specific bits, but we want to call
            # the generic getHeader to get it off disc or cache
            
            hdr = rd.getHeader([name,ver,rel,epoch,arch, "0",channel['label']])
            if progressCallback:
                progressCallback(count, total)
            count = count + 1

        rpmSourceUtils.saveListToDisk(pkgList, filePath, globPattern)
        self.pkglists[channel['label']] = pkgList
        return pkgList

    def listAllPackages(self, channel,
                        msgCallback = None, progressCallback = None):
        # yum only knows about the most recent packages. Can't say
        # I blame them. I wish i only had to know about the most recent...
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        rd = repoDirector.initRepoDirector()
        pkgList = rd.listPackages(channel, msgCallback, progressCallback)

        list = pkgList[0]
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)
        return list

    
    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        # well, we've got the headers, might as well create a proper
        # obslist at this point
        
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])

        
        if msgCallback:
            msgCallback("Fetching obsoletes list for %s" % channel['url'])

        try:
            pkgList = self.pkglists[channel['label']]
        except KeyError:
            # we just hit the getObsoletes path, with no package info known
            # figure it out ourselves
            rd = repoDirector.initRepoDirector()
            pkgList = rd.listPackages(channel, msgCallback, progressCallback)
            self.pkglists[channel['label']] = pkgList

        obsList = []
        total = len(pkgList)
        count = 0
        for pkg in pkgList:
            baseFileName = "%s-%s-%s.%s.hdr" % (pkg[0], pkg[1], pkg[2], pkg[4])
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            
            if os.access(fileName, os.R_OK):
                fd = open(fileName, "r")
                try:
                    hdr = rpmUtils.readHeaderBlob(fd.read())
                except:
                    continue
                fd.close()
                if not hdr['obsoletes']:
                    continue
                obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
                if obs:
#                    print obs
                    obsList = obsList + obs

            if progressCallback:
                progressCallback(count, total)
            count = count + 1
            
        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        obsList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(obsList, filePath,globPattern) 
#        print obsList
        return obsList
        

# since we use the diskcache secondary in yum/apt, and
# we dont know the version till after we look at the
# file, we glob for it, and use it 
class YumDiskCache(rpmSource.PackageSource):
    def __init__(self, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        globPattern = "%s/%s.*" %  (self.cfg["storageDir"], channel['label'])
        lists = glob.glob(globPattern)

        # FIXME?
        # we could sort and find the oldest, but there should
        # only be one
        
        if len(lists):
            localFilename = lists[0]
        else:
            # for now, fix PackageSourceChain to not freak
            # when everything returns None
            return 0

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        tmp_args, tmp_method = xmlrpclib.loads(filecontents)
        
        # tmp_args[0] is the list of packages
        return tmp_args[0]


        

class YumRepo(genericRepo.GenericRepo):
    def __init__(self):
        self.login = None
        genericRepo.GenericRepo.__init__(self)
        self.yds = YumDiskCache()
        self.yrs = YumRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)

        # need a layer here to look in the yum cache dir in /var/cache/yum
        # so if someone is using yum and up2date, they can share caches
        # in at least one dir

        self.hds = rpmSource.DiskCache()
        self.hldc = rpmSource.LocalDisk()
        
        self.psc.headerCache = localHeaderCache
        # note that for apt/yum we check to see if the server has been modified
        # and if not, fall back to the diskcache... up2date is the opposite
        self.sources = {'listPackages':[{'name':'yum', 'object': self.yrs},
                                        {'name':'yumdiskcache', 'object':self.yds}],
                       'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'yum', 'object': self.yrs}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'yum', 'object': self.yrs}],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'yum-diskcache', 'object':self.hds},
                                     {'name':'yum-localdisk', 'object':self.hldc},
                                     {'name':'yum', 'object': self.yrs}],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'yum', 'object': self.yrs}
                                      ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'yum', 'object': self.yrs}
                                            ]
                        }

    def updateAuthInfo(self):
        pass

    

def register(rd):
    yumRepo = YumRepo()
    rd.handlers['yum'] = yumRepo
    yumSolveDep = YumSolveDep()
    rd.depSolveHandlers['yum'] = yumSolveDep
    
    

########NEW FILE########
__FILENAME__ = repoDirector
#!/usr/bin/python

import os
import sys
import rhnChannel
import config
#import sourcesConfig
import up2dateLog


class RepoDirector:
    handlers = {}
    depSolveHandlers = {}
    def __init__(self, handlers=None, depSolveHandlers=None):
        if handlers:
            self.handlers = handlers
        if depSolveHandlers:
            self.depSolveHandlers = depSolveHandlers
        self.channels = rhnChannel.getChannels()

    def listPackages(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].listPackages(channel, msgCallback, progressCallback)

    def listAllPackages(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].listAllPackages(channel, msgCallback, progressCallback)


    def getObsoletes(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].getObsoletes(channel, msgCallback, progressCallback)

    def getHeader(self, pkg,  msgCallback = None, progressCallback = None):
        channel = self.channels.getByLabel(pkg[6])
        return self.handlers[channel['type']].getHeader(pkg, msgCallback, progressCallback)

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        channel = self.channels.getByLabel(pkg[6])
        return self.handlers[channel['type']].getPackage(pkg, msgCallback, progressCallback)

    def getPackageSource(self, channel, pkg,  msgCallback = None, progressCallback = None):
        return self.handlers[channel['type']].getPackageSource(channel, pkg, msgCallback, progressCallback)

    def getDepSolveHandlers(self):
        return self.depSolveHandlers

    def updateAuthInfo(self):
        for channeltype in self.handlers.keys():
            self.handlers[channeltype].updateAuthInfo()




def initRepoDirector():
    global rd
    try:
        rd = rd
    except NameError:
        rd = None
        
    if rd:
        return rd

    rd = RepoDirector()
    from repoBackends import up2dateRepo
    up2dateRepo.register(rd)

    return rd

########NEW FILE########
__FILENAME__ = rhnChannel
#!/usr/bin/python

# all the crap that is stored on the rhn side of stuff
# updating/fetching package lists, channels, etc

import os
import time
import random

import up2dateAuth
import up2dateErrors
import config
import up2dateLog
import rpcServer
#import sourcesConfig
import urlMirrors
from rhn import rpclib





global channel_blacklist
channel_blacklist = []


# FIXME?
# change this so it doesnt import sourceConfig, but
# instead sourcesConfig imports rhnChannel (and repoDirector)
# this use a repoDirector.repos.parseConfig() or the like for
# each line in "sources", which would then add approriate channels
# to rhnChannel.selected_channels and populate the sources lists
# the parseApt/parseYum stuff would move to repoBackends/*Repo.parseConfig()
# instead... then we should beable to fully modularize the backend support


# heh, dont get much more generic than this...
class rhnChannel:
    # shrug, use attributes for thetime being
    def __init__(self, **kwargs):
        self.dict = {}

        for kw in kwargs.keys():
            self.dict[kw] = kwargs[kw]
               
    def __getitem__(self, item):
        return self.dict[item]

    def __setitem__(self, item, value):
        self.dict[item] = value

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

class rhnChannelList:
    def __init__(self):
        # probabaly need to keep these in order for
        #precedence
        self.list = []

    def addChannel(self, channel):
        self.list.append(channel)


    def channels(self):
        return self.list

    def getByLabel(self, channelname):
        for channel in self.list:
            if channel['label'] == channelname:
                return channel
    def getByName(self, channelname):
        return self.getByLabel(channelname)

    def getByType(self, type):
        channels = []
        for channel in self.list:
            if channel['type'] == type:
                channels.append(channel)
        return channels

# for the gui client that needs to show more info
# maybe we should always make this call? If nothing
# else, wrapper should have a way to show extended channel info
def getChannelDetails():

    channels = []
    sourceChannels = getChannels()

    useRhn = None
    for sourceChannel in sourceChannels.channels():
        if sourceChannel['type'] == "up2date":
            useRhn = 1

    if useRhn:
        s = rpcServer.getServer()
        up2dateChannels = rpcServer.doCall(s.up2date.listChannels, up2dateAuth.getSystemId())

    for sourceChannel in sourceChannels.channels():
        if sourceChannel['type'] != 'up2date':
            # FIMXE: kluge since we dont have a good name, maybe be able to fix
            sourceChannel['name'] = sourceChannel['label']
            sourceChannel['description'] = "%s channel %s from  %s" % (sourceChannel['type'],
                                                                           sourceChannel['label'],
                                                                           sourceChannel['url'])
            channels.append(sourceChannel)
            continue
    
        if useRhn:
            for up2dateChannel in up2dateChannels:
                if up2dateChannel['label'] != sourceChannel['label']:
                    continue
                for key in up2dateChannel.keys():
                    sourceChannel[key] = up2dateChannel[key]
                channels.append(sourceChannel)
            

    return channels

def getMirror(source,url):

    mirrors = urlMirrors.getMirrors(source,url)

#    print "mirrors: %s" % mirrors
    length  = len(mirrors)
    # if we didnt find any mirrors, return the
    # default
    if not length:
        return url
    random.seed(time.time())
    index = random.randrange(0, length)
    randomMirror = mirrors[index]
    print "using mirror: %s" % randomMirror
    return randomMirror
    

cmdline_pkgs = []

global selected_channels
selected_channels = None
def getChannels(force=None, label_whitelist=None):
    cfg = config.initUp2dateConfig()
    log = up2dateLog.initLog()
    global selected_channels
    #bz:210625 the selected_chs is never filled
    # so it assumes there is no channel although
    # channels are subscribed
    selected_channels=label_whitelist
    if not selected_channels and not force:

        ### mrepo: hardcode sources so we don't depend on /etc/sysconfig/rhn/sources
        # sources = sourcesConfig.getSources()
        sources = [{'url': 'https://xmlrpc.rhn.redhat.com/XMLRPC', 'type': 'up2date'}]
        useRhn = 1

        if cfg.has_key('cmdlineChannel'):
            sources.append({'type':'cmdline', 'label':'cmdline'}) 

        selected_channels = rhnChannelList()
        cfg['useRhn'] = useRhn

        li = up2dateAuth.getLoginInfo()
        # login can fail...
        if not li:
            return []
        
        tmp = li.get('X-RHN-Auth-Channels')
        if tmp == None:
            tmp = []
        for i in tmp:
            if label_whitelist and not label_whitelist.has_key(i[0]):
                continue
                
            channel = rhnChannel(label = i[0], version = i[1],
                                 type = 'up2date', url = cfg["serverURL"])
            selected_channels.addChannel(channel)

        if len(selected_channels.list) == 0:
            raise up2dateErrors.NoChannelsError("This system may not be updated until it is associated with a channel.")

    return selected_channels
            

def setChannels(tempchannels):
    global selected_channels
    selected_channels = None
    whitelist = dict(map(lambda x: (x,1), tempchannels))
    return getChannels(label_whitelist=whitelist)



def subscribeChannels(channels,username,passwd):
    s = rpcServer.getServer()
    try:
        channels = rpcServer.doCall(s.up2date.subscribeChannels,
                          up2dateAuth.getSystemId(),
                          channels,
                          username,
                          passwd)
    except rpclib.Fault, f:
        if f.faultCode == -36:
            raise up2dateErrors.PasswordError(f.faultString)
        else:
            raise up2dateErrors.CommunicationError(f.faultString)

def unsubscribeChannels(channels,username,passwd):
    s = rpcServer.getServer()
    try:
        channels = rpcServer.doCall(s.up2date.unsubscribeChannels,
                          up2dateAuth.getSystemId(),
                          channels,
                          username,
                          passwd)
    except rpclib.Fault, f:
        if f.faultCode == -36:
            raise up2dateErrors.PasswordError(f.faultString)
        else:
            raise up2dateErrors.CommunicationError(f.faultString)


########NEW FILE########
__FILENAME__ = rhnErrata
#!/usr/bin/python
            
import rpm
import os   
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

import up2dateErrors
import up2dateMessages
import rpmUtils
import up2dateAuth
import up2dateLog
import up2dateUtils
import rpcServer
import transaction
import config

from rhn import rpclib



def getAdvisoryInfo(pkg, warningCallback=None):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
    # no errata for non rhn use
    if not cfg['useRhn']:
        return None
        
    s = rpcServer.getServer()

    ts = transaction.initReadOnlyTransaction()
    mi = ts.dbMatch('Providename', pkg[0])
    if not mi:
	return None

    # odd,set h to last value in mi. mi has to be iterated
    # to get values from it...
    h = None
    for h in mi:
        break

    info = None

    # in case of package less errata that somehow apply
    if h:
        try:
            pkgName = "%s-%s-%s" % (h['name'],
                                h['version'],
                                h['release'])
            log.log_me("getAdvisoryInfo for %s" % pkgName)
            info = rpcServer.doCall(s.errata.getPackageErratum,
                                    up2dateAuth.getSystemId(),
                                    pkg)
        except rpclib.Fault, f:
            if warningCallback:
                warningCallback(f.faultString)
            return None
    
    if info:
        return info
    
    try:
        log.log_me("getAdvisoryInfo for %s-0-0" % pkg[0])
        info = rpcServer.doCall(s.errata.GetByPackage,
                      "%s-0-0" % pkg[0],
                      up2dateUtils.getVersion())
    except rpclib.Fault, f:
        if warningCallback:
            warningCallback(f.faultString)
        return None
    
    return info

########NEW FILE########
__FILENAME__ = rpcServer
#!/usr/bin/python
#
# $Id: rpcServer.py 89799 2006-03-31 15:28:28Z pkilambi $

import os
import sys
import config
import types
import socket
import string
import time
import httplib
import urllib2

import clientCaps
import up2dateLog
import up2dateErrors 
import up2dateAuth 
import up2dateUtils
import repoDirector

#import wrapperUtils
from rhn import rpclib
    

def stdoutMsgCallback(msg):
    print msg


def hasSSL():
    return hasattr(socket, "ssl")

class RetryServer(rpclib.Server):
    def foobar(self):
        pass

    def addServerList(self, serverList):
        self.serverList = serverList

    def _request1(self, methodname, params):
        self.log = up2dateLog.initLog()
        while 1:
            try:
                ret = self._request(methodname, params)
            except rpclib.InvalidRedirectionError:
#                print "GOT a InvalidRedirectionError"
                raise
            except rpclib.Fault:
		raise 
            except:
                server = self.serverList.next()
                if server == None:
                    # since just because we failed, the server list could
                    # change (aka, firstboot, they get an option to reset the
                    # the server configuration) so reset the serverList
                    self.serverList.resetServerIndex()
                    raise

                msg = "An error occured talking to %s:\n" % self._host
                msg = msg + "%s\n%s\n" % (sys.exc_type, sys.exc_value)
                msg = msg + "Trying the next serverURL: %s\n" % self.serverList.server()
                self.log.log_me(msg)
                # try a different url

                # use the next serverURL
                import urllib
                typ, uri = urllib.splittype(self.serverList.server())
                typ = string.lower(typ)
                if typ not in ("http", "https"):
                    raise InvalidRedirectionError(
                        "Redirected to unsupported protocol %s" % typ)

#                print "gha2"
                self._host, self._handler = urllib.splithost(uri)
                self._orig_handler = self._handler
                self._type = typ
                if not self._handler:
                    self._handler = "/RPC2"
                self._allow_redirect = 1
                continue
            # if we get this far, we succedded
            break
        return ret

    
    def __getattr__(self, name):
        # magic method dispatcher
        return rpclib.xmlrpclib._Method(self._request1, name)
                

# uh, yeah, this could be an iterator, but we need it to work on 1.5 as well
class ServerList:
    def __init__(self, serverlist=[]):
        self.serverList = serverlist
        self.index = 0
        
    def server(self):
        self.serverurl = self.serverList[self.index]
        return self.serverurl


    def next(self):
        self.index = self.index + 1
        if self.index >= len(self.serverList):
            return None
        return self.server()

    def resetServerList(self, serverlist):
        self.serverList = serverlist
        self.index = 0

    def resetServerIndex(self):
        self.index = 0

# singleton for the ServerList
def initServerList(servers):
    global server_list
    try:
        server_list = server_list
    except NameError:
        server_list = None

    if server_list == None:
        server_list = ServerList(servers)

    # if we've changed the config, we need need to
    # update the server_list as well. Not really needed
    # in the app, but makes testing cleaner
    cfg = config.initUp2dateConfig()
    sl = cfg['serverURL']
    if type(sl) == type(""):
        sl  = [sl]
        
    if sl != server_list.serverList:
        server_list = ServerList(servers)

    return server_list

def getServer(refreshCallback=None):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
# Where do we keep the CA certificate for RHNS?
# The servers we're talking to need to have their certs
# signed by one of these CA.
    ca = cfg["sslCACert"]
    if type(ca) == type(""):
    	ca = [ca]

    rhns_ca_certs = ca or ["/usr/share/rhn/RHNS-CA-CERT"]
    if cfg["enableProxy"]:
        proxyHost = up2dateUtils.getProxySetting()
    else:
        proxyHost = None

    if hasSSL():
        serverUrls = cfg["serverURL"]
    else:
        serverUrls = cfg["noSSLServerURL"]

    # the standard is to be a string, so list-a-fy in that case
    if type(serverUrls) == type(""):
        serverUrls = [serverUrls]

    serverList = initServerList(serverUrls)

    proxyUser = None
    proxyPassword = None
    if cfg["enableProxyAuth"]:
        proxyUser = cfg["proxyUser"] or None
        proxyPassword = cfg["proxyPassword"] or None

    lang = None
    for env in 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG':
        if os.environ.has_key(env):
            if not os.environ[env]:
                # sometimes unset
                continue
            lang = string.split(os.environ[env], ':')[0]
            lang = string.split(lang, '.')[0]
            break


    s = RetryServer(serverList.server(),
                    refreshCallback=refreshCallback,
                    proxy=proxyHost,
                    username=proxyUser,
                    password=proxyPassword)
    s.addServerList(serverList)

    s.add_header("X-Up2date-Version", up2dateUtils.version())
    
    if lang:
        s.setlang(lang)

    # require RHNS-CA-CERT file to be able to authenticate the SSL connections
    for rhns_ca_cert in rhns_ca_certs:
        if not os.access(rhns_ca_cert, os.R_OK):
	    msg = "%s: %s" % ("ERROR: can not find RHNS CA file:",
				 rhns_ca_cert)
            log.log_me("%s" % msg)
	    print msg
            sys.exit(-1)

        # force the validation of the SSL cert
        s.add_trusted_cert(rhns_ca_cert)

    clientCaps.loadLocalCaps()

    # send up the capabality info
    headerlist = clientCaps.caps.headerFormat()
    for (headerName, value) in headerlist:
        s.add_header(headerName, value)
    return s

# inherinet the retry/failover from RetryServer here
class RetryGETServer(rpclib.GETServer, RetryServer):
    pass


# FIXME: doCall should probabaly be a method
# of a higher level server object
def doCall(method, *args, **kwargs):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
    ret = None

    attempt_count = 1
    attempts = cfg["networkRetries"] or 5

    while 1:
        failure = 0
        ret = None        
        try:
            ret = apply(method, args, kwargs)
        except KeyboardInterrupt:
            raise up2dateErrors.CommunicationError(
                "Connection aborted by the user")
        # if we get a socket error, keep tryingx2
        except (socket.error, socket.sslerror), e:
            log.log_me("A socket error occurred: %s, attempt #%s" % (
                e, attempt_count))
            if attempt_count >= attempts:
                if len(e.args) > 1:
                    raise up2dateErrors.CommunicationError(e.args[1])
                else:
                    raise up2dateErrors.CommunicationError(e.args[0])
            else:
                failure = 1
        except httplib.IncompleteRead:
            print "httplib.IncompleteRead" 
            raise up2dateErrors.CommunicationError("httplib.IncompleteRead")

        except urllib2.HTTPError, e:
            msg = "\nAn HTTP error occurred:\n"
            msg = msg + "URL: %s\n" % e.filename
            msg = msg + "Status Code: %s\n" % e.code
            msg = msg + "Error Message: %s\n" % e.msg
            log.log_me(msg)
            raise up2dateErrors.CommunicationError(msg)
        
        except rpclib.ProtocolError, e:
            
            log.log_me("A protocol error occurred: %s , attempt #%s," % (
                e.errmsg, attempt_count))
            (errCode, errMsg) = rpclib.reportError(e.headers)
            reset = 0
            if abs(errCode) == 34:
                log.log_me("Auth token timeout occurred\n errmsg: %s" % errMsg)
                # this calls login, which in tern calls doCall (ie,
                # this function) but login should never get a 34, so
                # should be safe from recursion

                rd = repoDirector.initRepoDirector()
                rd.updateAuthInfo()
                reset = 1

            # the servers are being throttle to pay users only, catch the
            # exceptions and display a nice error message
            if abs(errCode) == 51:
                log.log_me("Server has refused connection due to high load")
                raise up2dateErrors.CommunicationError(e.errmsg)
            # if we get a 404 from our server, thats pretty
            # fatal... no point in retrying over and over. Note that
            # errCode == 17 is specific to our servers, if the
            # serverURL is just pointing somewhere random they will
            # get a 0 for errcode and will raise a CommunicationError
            if abs(errCode) == 17:
		#in this case, the args are the package string, so lets try to
		# build a useful error message
                if type(args[0]) == type([]):
                    pkg = args[0]
                else:
                    pkg=args[1]
                    
                if type(pkg) == type([]):
                    pkgName = "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])
                else:
                    pkgName = pkg
		msg = "File Not Found: %s\n%s" % (pkgName, errMsg)
		log.log_me(msg)
                raise up2dateErrors.FileNotFoundError(msg)
                
            if not reset:
                if attempt_count >= attempts:
                    raise up2dateErrors.CommunicationError(e.errmsg)
                else:
                    failure = 1
            
        except rpclib.ResponseError:
            raise up2dateErrors.CommunicationError(
                "Broken response from the server.")

        if ret != None:
            break
        else:
            failure = 1


        if failure:
            # rest for five seconds before trying again
            time.sleep(5)
            attempt_count = attempt_count + 1
        
        if attempt_count > attempts:
            print "busted2"
            print method
            raise up2dateErrors.CommunicationError("The data returned from the server was incomplete")

    return ret
    

########NEW FILE########
__FILENAME__ = rpmSource
#!/usr/bin/python
#
# a chain of responsibilty class for stacking package sources
# for up2date
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Adrian Likins <alikins@redhat.com>
#
"""A chain of responsibility class for stacking package sources for up2date"""

#import timeoutsocket
#timeoutsocket.setDefaultSocketTimeout(1)
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

import up2dateUtils
import up2dateLog
import up2dateErrors
import glob
import socket
import re
import os
import rpm
import string
import time
import struct
import config
import rpmUtils
import up2dateAuth
import up2dateUtils
#import headers
#import rpcServer
import transaction
#import timeoutsocket
import urllib
import gzip
import rhnChannel
import sys
import rpmSourceUtils

from rhn import rpclib



BUFFER_SIZE = 8092


def factory(aClass, *args, **kwargs):
    return apply(aClass, args, kwargs)


class HeaderCache:
    def __init__(self):
        self.cfg = config.initUp2dateConfig()
        # how many headers to cache in ram
        if self.cfg["headerCacheSize"]:
            self.cache_size = self.cfg["headerCacheSize"]
        else:
            self.cache_size = 30
        self.__cache = {}
        self.__cacheLite = {}

    def set_cache_size(self, number_of_headers):
        self.cache_size = number_of_headers

    def __liteCopy(self, header):
        tmp = {}
        tmp['name'] = header['name']
        tmp['version'] = header['version']
        tmp['release'] = header['release']
        tmp['arch'] = header['arch']
        tmp['summary'] = header['summary']
        tmp['description'] = header['description']
        tmp['size'] = header['size']
        return tmp

    def __setitem__(self,item,value):
        if len(self.__cache) <= self.cache_size:
            self.__cache[item] = value
            self.__cacheLite[item] = self.__liteCopy(value)
        else:
            # okay, this is about as stupid of a cache as you can get
            # but if we hit the max cache size, this is as good as
            # any mechanism for freeing up space in the cache. This
            # would be a good place to put some smarts
            bar = self.__cache.keys()
            del self.__cache[bar[self.cache_size-1]]
            self.__cache[item] = value
            self.__cacheLite[item] = self.__liteCopy(value)

    def __getitem__(self, item):
        return self.__cache[item]
    

    def getLite(self, item):
        return self.__cacheLite[item]

    def __len__(self):
        return len(self.__cache)

    def keys(self):
        return self.__cache.keys()

    def values(self):
        return self.__cache.keys()

    def has_key(self, item,lite=None):
#        print "\n########\nhas_key called\n###########\n"
#        print "item: %s" % item
#        print self.__cache.keys()
        
        if lite:
            return self.__cacheLite.has_key(item)
        else:
            return self.__cache.has_key(item)

    def __delitem__(self, item):
        del self.__cache[item]

    def printLite(self):
        print self.__cacheLite


# this is going to be a factory. More than likely, it's input for
# it's init is going to be read from a config file. 
#
#  goals... easy "stacking" of data sources with some sort of priority
#      make the goal oblivous to the "names" of the data sources
class PackageSourceChain:
    def __init__(self, headerCacheObject = None, metainfolist = None):
        self.log = up2dateLog.initLog()
        self.metainfo = {}
        # lame, need to keep a list to keep the order
        self.source_list = []
        if metainfolist != None:
            for source in metainfolist:
                self.addSourceClass(source)

        self.headerCache = headerCacheObject


    def addSourceClass(self, metainfo):
        source = metainfo
        name = source['name']
        self.log.log_debug("add source class name", name)
        self.source_list.append(name)
        self.metainfo[name] = factory(
            source['class'], source['args'], source['kargs'])

        # automagically associated the header cache for the stack with each
        # object in the chain so we can populate the cache if need be
        self.metainfo[name].addHeaderCacheObject(self.headerCache)
        #log.log_debug("class: %s args: %s kargs %s" % (
        #    source['class'], source['args'], source['kargs']))


    def clearSourceInstances(self):
        self.metainfo = {}
        self.source_list = []

    def setSourceInstances(self, metainfoList):
        self.clearSourceInstances()
        for metainfo in metainfoList:
            self.addSourceInstance(metainfo)

    def addSourceInstance(self, metainfo):
        source = metainfo
        name = source['name']
        #        self.log.log_debug("add instance class name", name)
        self.source_list.append(name)
        self.metainfo[name] = source['object']

        # automagically associated the header cache for the stack with each
        # object in the chain so we can populate the cache if need be
        self.metainfo[name].addHeaderCacheObject(self.headerCache)
        self.metainfo[name]['name'] =  name       
        #log.log_debug("object: %s name: %s" % (source['object'], name))

    def getPackage(self, pkg, MsgCallback = None, progressCallback = None):
        self.log.log_debug("getPackage", pkg)
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            # FIXME: wrap in approriate exceptions
            package = source.getPackage(pkg, MsgCallback, progressCallback)
            if package != None:
                self.log.log_debug("Package %s Fetched via: %s" % (
                    pkg, source['name']))
                #self.fetchType[pkg] = source['name']
                return package
        return None

    def getPackageSource(self, channel, pkg,
                         MsgCallback = None, progressCallback = None):
        self.log.log_debug("getPackageSource", channel, pkg)
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            # FIXME: wrap in approriate exceptions
            package = source.getPackageSource(channel, pkg,
                                              MsgCallback, progressCallback)
            if package != None:
                self.log.log_debug("Source %s Package Fetched via: %s" %(
                    pkg, source['name']))
                return package
        return None
    

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        # if the package source is specified, use it
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            header = source.getHeader(pkg, progressCallback = progressCallback)
            # return the first one we find
            if header != None:
#                self.log.log_debug("Header for %s Fetched via: %s" % (
#                    pkg, source['name']))
                #print "source: %s" % source['name']
                # FIXME, the normal one only returns the header
                return (header,source['name'])
        return None

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            packageList = source.listPackages(channel,
                                              msgCallback, progressCallback)
            if packageList != None:
                self.log.log_debug("listPackages Fetched via:", source['name'])
                return (packageList, source['name'])
        return None

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        for source_key in self.source_list:
            source = self.metainfo[source_key]
            packageList = source.listAllPackages(channel,
                                              msgCallback, progressCallback)
            if packageList != None:
                self.log.log_debug("listAllPackages Fetched via:", source['name'])
                return (packageList, source['name'])
        return None

    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            obsoletesList = source.getObsoletes(channel,
                                                msgCallback, progressCallback)
            if obsoletesList != None:
                self.log.log_debug("getObsoletes Fetched via:", source['name'])
                return (obsoletesList, source['name'])
        return None


# template class for all the sources in the chain
class PackageSource:
    def __init__(self, cacheObject = None):
        self.headerCache = None
        self.info = {}
        
    def getHeader(self, pkg):
        ""
        pass
    
    def getPackage(self, pkg):
        ""
        pass
    
    def addHeaderCacheObject(self, cacheObject):
        ""
        self.headerCache = cacheObject
        
    def __setitem__(self, item, value):
        self.info[item] = value

    def __getitem__(self, item):
        return self.info[item]
        
class HeaderMemoryCache(PackageSource):
    def __init__(self, cacheObject = None):
        PackageSource.__init__(self,cacheObject)
    
    def getHeader(self, pkg, lite = None,
                  msgCallback = None, progressCallback = None):
        if lite:
            if self.headerCache.has_key(up2dateUtils.pkgToStringArch(pkg), lite = 1):
                return self.headerCache.getLite(up2dateUtils.pkgToStringArch(pkg))

        if self.headerCache.has_key(up2dateUtils.pkgToStringArch(pkg)):
            return self.headerCache[up2dateUtils.pkgToStringArch(pkg)]


class LocalDisk(PackageSource):
    def __init__(self, cacheObject = None, packagePath = None):
        self.cfg = config.initUp2dateConfig()
        self.log = up2dateLog.initLog()
        self.dir_list = up2dateUtils.getPackageSearchPath()
        if packagePath:
            self.dir_list = self.dir_list + packagePath

        self.ts = transaction.initReadOnlyTransaction()
        PackageSource.__init__(self, cacheObject = cacheObject)

    def addPackageDir(self, packagePath):
        self.dir_list = self.dir_list + packagePath

    def __saveHeader(self, hdr):
        tmp = rpmUtils.readHeaderBlob(hdr.unload())
        rpmSourceUtils.saveHeader(tmp)
        

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)

        fileNames = tmpFileNames
        if len(fileNames):
            if os.access(fileNames[0], os.R_OK):
                if not re.search("rpm$", fileNames[0]):
                    # it wasnt an rpm, so must be a header
                    if os.stat(fileNames[0])[6] == 0:
                        return None
                    fd = open(fileNames[0], "r")
                    # if this header is corrupt, rpmlib exits and we stop ;-<
                    try:
                        hdr = rpmUtils.readHeaderBlob(fd.read())
                    except:
                        return None
                    self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                    fd.close()
                    self.__saveHeader(hdr)
                    return hdr
                else:
                    fd = os.open(fileNames[0], 0)
                    # verify just the md5
                    self.ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
                    try:
                        #hdr = rpm.headerFromPackage(fd)
                        hdr = self.ts.hdrFromFdno(fd)
                    except:
                        os.close(fd)
                        self.ts.popVSFlags()
                        raise up2dateErrors.RpmError("Error reading header")
                    self.ts.popVSFlags()
                    os.close(fd)
                    self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                    self.__saveHeader(hdr)
                    return hdr
                    
            else:
                 return None        
        else:
            for dir in self.dir_list:
                fileNames = glob.glob("%s/%s.noarch.*" %
                                      (dir,
                                       up2dateUtils.pkgToString(pkg)))
            if len(fileNames):
                if os.access(fileNames[0], os.R_OK):
                    if not re.search("rpm$", fileNames[0]):
                        # it's not an rpm, must be a header
                        if os.stat(fileNames[0])[6] == 0:
                            return None
                        fd = open(fileNames[0], "r")
                        try:
                            hdr = rpmUtils.readHeaderBlob(fd.read())
                        except:
                            self.log.log_me("Corrupt header %s, skipping, "\
                                       "will download later..." % fileNames[0])
                            return None
                        fd.close()
                        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                        return hdr
                    else:
                        if os.access(fileNames[0], os.R_OK):
                            fd = os.open(fileNames[0], 0)
                            try:
                                #hdr = rpm.headerFromPackage(fd)
                                hdr = self.ts.hdrFromFdno(fd)
                            except:
                                os.close(fd)
                                raise up2dateErrors.RpmError("Error reading header")
                            os.close(fd)
                            self.log.log_me("Reading header from: %s" % fileNames)
                            self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                            return hdr
                        else:
                            return None
                else:
                    return None
            else:
                return None
    
    # this is kind of odd, since we actually just symlink to the package from
    # the cache dir, instead of copying it around, or keeping track of where
    # all the packages are from
    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            # if the file is in the storageDir, dont symlink it to itself ;->
            if len(tmpFileNames) and not (dir == self.cfg["storageDir"]):
                try:
                    os.remove(fileName)
                except OSError:
                    pass
                # no callback, since this will have to fall back to another repo to actually get
                os.symlink(tmpFileNames[0], fileName)
                fd = open(tmpFileNames[0], "r")
                buffer = fd.read()
                fd.close()
                return buffer

            
    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        baseFileName = "%s" % (srcpkg)
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            # if the file is in the storageDir, dont symlink it to itself ;->
            if len(tmpFileNames) and not (dir == self.cfg["storageDir"]):
                try:
                    os.remove(fileName)
                except OSError:
                    # symlink doesnt exist, this is fine
                    pass
                if msgCallback:
                    msgCallback(fileName)
                os.symlink(tmpFileNames[0], fileName)
                break


class DiskCache(PackageSource):
    def __init__(self, cacheObject = None):
        # this is the cache, stuff here is only in storageDir
        self.cfg = config.initUp2dateConfig()
        self.log = up2dateLog.initLog()
        self.dir_list = [self.cfg["storageDir"]]
        self.ts =  transaction.initReadOnlyTransaction()
        PackageSource.__init__(self, cacheObject = cacheObject)

    def __readHeaderFromRpm(self, fileNames, pkg):

        
        fd = os.open(fileNames[0], 0)
        self.ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
        try:
            hdr = self.ts.hdrFromFdno(fd)
        except:
             os.close(fd)
             self.ts.popVSFlags()
             raise up2dateErrors.RpmError("Error reading header")
        self.ts.popVSFlags()
        os.close(fd)
        self.log.log_me("Reading header from: %s" % fileNames)
        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
        return hdr
     

    def __readHeaderFromFile(self, fileNames, pkg):
        if os.access(fileNames[0], os.R_OK):
            if os.stat(fileNames[0])[6] == 0:
                print "stat failed", fileNames[0]
                return None
            hdr = rpmUtils.readHeader(fileNames[0])
            if hdr == None:
                return None
            self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
            return hdr
        else:
            return None
        
    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        for dir in self.dir_list:
            fileNames = glob.glob(
                "%s/%s.%s.hdr" % (dir, up2dateUtils.pkgToString(pkg), pkg[4]))
            # if we find anything, bail
            if len(fileNames):
                break


        if len(fileNames):
            hdr = self.__readHeaderFromFile(fileNames, pkg)
            if hdr:
                return hdr
            else:
                # the header aint there, return none so the rest
                # of the crap will go fetch it again
                return None

        else:
            for dir in self.dir_list:
                fileNames = glob.glob(
                    "%s/%s.noarch.hdr" % (dir, up2dateUtils.pkgToString(pkg)))

            # see if it is a .hdr file, if not try reading it as an rpm
            if len(fileNames):
                hdr = self.__readHeaderFromFile(fileNames, pkg)
                if hdr:
                    return hdr
                else:
                    hdr = self.__readHeaderFromRpm(fileNames,pkg)
                    return hdr

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):

        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        # check if we already have package and that they are valid
        fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)

        if os.access(fileName, os.R_OK) and \
               rpmUtils.checkRpmMd5(fileName):
            if msgCallback:
                msgCallback(baseFileName)
            if progressCallback != None:
                progressCallback(1, 1)
            return 1
        else:
            return None

    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        baseFileName = "%s" % (srcpkg)
        fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
        
        # check if we already have package and that they are valid
        if os.access(fileName, os.R_OK):
        # if os.access(fileName, os.R_OK) and \
        #    not rpmUtils.checkRpmMd5(fileName):
            if msgCallback:
                msgCallback(baseFileName)
            if progressCallback != None:
                progressCallback(1, 1)
            return 1
        else:
            return None


    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        localFilename = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)
        
        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        localFilename = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)
        
        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]


    def getObsoletes(self, channel, version,
                     msgCallback = None, progressCallback = None):
        localFilename = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                                channel['label'],
                                                channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]

        
    
# need a ton of helper functions for this one, but then, it's the main one
class Up2datePackageSource(PackageSource):
    def __init__(self, server, proxyHost, cacheObject = None):
        self.s = server
        PackageSource.__init__(self, cacheObject = cacheObject)
        

    # fetch it from the network, no caching of any sort
    def getHeader(self, pkg, lite = None,
                  msgCallback = None, progressCallback = None):
        hdr = None

        try:
            ret = self.s.up2date.header(up2dateAuth.getSystemId(), pkg)
        except KeyboardInterrupt:
            raise up2dateErrors.CommunicationError("Connection aborted by the user")
        except (socket.error, socket.sslerror), e:
            if len(e.args) > 1:
                raise up2dateErrors.CommunicationError(e.args[1])
            else:
                raise up2dateErrors.CommunicationError(e.args[0])
        except rpclib.ProtocolError, e:
            raise up2dateErrors.CommunicationError(e.errmsg)
        except rpclib.ResponseError:
            raise up2dateErrors.CommunicationError("Broken response from the server.");
        except rpclib.Fault, f:
            raise up2dateErrors.CommunicationError(f.faultString)

        bin = ret[0]
        hdr = rpmUtils.readHeaderBlob(bin.data)
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache["%s-%s-%s.%s" % (hdr['name'],
                                          hdr['version'],
                                          hdr['release'],
                                          hdr['arch'])] = hdr
        return hdr


def callback(total, complete):
    print "-- %s bytes of %s" % (total, complete)

# FIXME: super ugly hack that deserves to die
def updateHttpServer(packageSourceChain, logininfo, serverSettings):

    httpServer = getGETServer(LoginInfo.logininfo, serverSettings)

    hds = HttpGetSource(httpServer, None, loginInfo = logininfo)
    packageSourceChain.addSourceInstance({'name':'get', 'object': hds})

    return packageSourceChain



########NEW FILE########
__FILENAME__ = rpmSourceUtils
#!/usr/bin/python

import config
import rpm
import string
import os
import struct
import sys
import glob

from rhn import rpclib


def factory(aClass, *args, **kwargs):
    return apply(aClass, args, kwargs)


def saveHeader(hdr):
#    print hdr
#    print type(hdr)
    cfg = config.initUp2dateConfig()
    fileName = "%s/%s.%s.hdr" % (cfg["storageDir"],
                                 string.join( (hdr['name'],
                                               hdr['version'],
                                               hdr['release']),
                                              "-"),
                                 hdr['arch'])

#    print fileName
    fd = os.open(fileName, os.O_WRONLY|os.O_CREAT, 0600)

    os.write(fd, hdr.unload())
    os.close(fd)

    return 1



def saveListToDisk(list, filePath, globstring):

     # delete any existing versions
     filenames = glob.glob(globstring)
     for filename in filenames:
          # try to be at least a little paranoid
          # dont follow symlinks...
          # not too much to worry about, unless storageDir is
          # world writeable
          if not os.path.islink(filename):
               os.unlink(filename)

     # since we have historically used xmlrpclib.dumps() to do
     # this, might as well continue
     infostring = rpclib.xmlrpclib.dumps((list, ""))

     f = open(filePath, "w")
     f.write(infostring)
     f.close()

########NEW FILE########
__FILENAME__ = rpmUtils
#!/usr/bin/python
# some high level utility stuff for rpm handling

# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Preston Brown <pbrown@redhat.com>
#         Adrian Likins <alikins@redhat.com>
#


#
#  FIXME: Some exceptions in here are currently in up2date.py
#         fix by moving to up2dateErrors.py and importing from there
#
#
        
import os
import sys
import re
import struct
        
import up2dateErrors
import up2dateUtils
import config
import rpm
import fnmatch
import gpgUtils
import transaction
import string


from up2date_client import up2dateLog            

# mainly here to make conflicts resolution cleaner
def findDepLocal(ts, dep):
    if dep[0] == '/':
        tagN = 'Basenames'
    else:   
        tagN = 'Providename'
    for h in ts.dbMatch(tagN, dep):
        return h
    else:   
        return None

# conv wrapper for gettting index of a installed package
# ie, for removing it
def installedHeaderIndexByPkg(pkg):
    return installedHeaderIndex(name=pkg[0],
                                version=pkg[1],
                                release=pkg[2],
                                arch=pkg[4])


# um, this doesnt actually seem to work with epoch
# becuase of some rpm issues (it wants a None, but
# doesnt except a none. Workaround by just not
# matching on epoch, the rest should be specific enough
def installedHeaderByPkg(pkg):
    return installedHeaderByKeyword(name=pkg[0],
                           version=pkg[1],
                           release=pkg[2],
                           arch=pkg[4])

# call like installedHeaderIndex(name="kernel", version="12312")
def installedHeaderIndex(**kwargs):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch()
    for keyword in kwargs.keys():
        mi.pattern(keyword, rpm.RPMMIRE_GLOB, kwargs[keyword])
        
    # we really shouldnt be getting multiples here, but what the heck
    instanceList = []
    for h in mi:
        instance = mi.instance()
        instanceList.append(instance)

    return instanceList

# just cause this is such a potentially useful looking method...
def installedHeaderByKeyword(**kwargs):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch()
    for keyword in kwargs.keys():
        mi.pattern(keyword, rpm.RPMMIRE_GLOB, kwargs[keyword])
    # we really shouldnt be getting multiples here, but what the heck
    headerList = []
    for h in mi:
        #print "%s-%s-%s.%s" % ( h['name'], h['version'], h['release'], h['arch'])
        
        headerList.append(h)

    return headerList

    
    
    
        
def installedHeadersNameVersion(pkgName,version):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch('Name', pkgName)
    for h in mi:
        if h['version'] == version:
            return h
    return None 

def installedHeader(someName, ts):
    if type(someName) == type([]):
        pkgName = someName[0]
    else:           
        pkgName = someName

    mi = ts.dbMatch('Name', pkgName)
    if not mi:          # not found
        return None
    for h in ts.dbMatch('Name', pkgName):
        name = h['name']
        epoch = h['epoch']
        if epoch == None:
            epoch = ""
        version = h['version']
        release = h['release']
        if type(someName) == type([]):
            if (pkgName == name and
                pkgName[2] == version and
                pkgName[3] == release and
                pkgName[4] == epoch):
                break
        else:
            if (pkgName == name):
                break
    else:
	return None
    return h

global obsHash
obsHash = None
def getInstalledObsoletes(msgCallback = None, progressCallback = None, getArch = None):
    _ts = transaction.initReadOnlyTransaction()
    obs_list = []
    global obsHash 

    if obsHash:
        return obsHash
    obsHash = {}
    
    count = 0
    total = 0
    for h in _ts.dbMatch():
        if h == None:
            break
        count = count + 1

    total = count
    
    for h in _ts.dbMatch():
        if h == None:
            break
        obsoletes = h['obsoletes']
        name = h['name']
        version = h['version']
        release = h['release']
        
        nvr = "%s-%s-%s" % (name, version, release)
        if obsoletes:
            obs_list.append((nvr, obsoletes))

        if progressCallback != None:
            progressCallback(count, total)
        count = count + 1
    
    for nvr,obs in obs_list:
        for ob in obs:
            if not obsHash.has_key(ob):
                obsHash[ob] = []
            obsHash[ob].append(nvr)

    
    return obsHash


# check to see if a new file has a different MD5 sum
# from the package already on disk, and if true, if
# the on-disk file has been modified.
# this is a lot of args, but it helps...
def checkModified(index, fileNames, fileMD5s,installedFileNames,installedFileMD5s):
    ret = 0
    fileName = fileNames[index]

    #print "fileMD5s: %s: " % fileMD5s
    #print "installedFileMD5s: %s" % installedFileMD5s
    #this is a little ugly, but the order of the filelist in the old and the new
    # pacakges arent the same.
    for j in range(len(installedFileNames)):
        if (installedFileNames[j] == fileName):
            if installedFileMD5s[j] == fileMD5s[index]:
                # the md5 of the file in the local db  is the same as the one in the
                # incoming package, so skip the rest of the check and return 0
                continue
	    # grrr, symlinks marked as config files pointing to dirs are baaad, okay?
	    if not os.path.isdir(fileName):
            	if installedFileMD5s[j] != up2dateUtils.md5sum(fileName):
                    # the local file is different than the file in the local db
                    ret = 1
            	else:
                    # not changed on disk
                    pass
            break
    return ret


def checkHeaderForFileConfigExcludes(h,package,ts):
    fflag = 0

    cfg = config.initUp2dateConfig()
    # might as well just do this once...
    fileNames = h['filenames'] or []
    fileMD5s = h['filemd5s'] or []
    fileFlags = h['fileflags'] or []


    installedHdr = installedHeader(h['name'],ts)
    if not installedHdr:
        #throw a fault? should this happen?
        return None
        
    installedFileNames = installedHdr['filenames'] or []
    installedFileMD5s = installedHdr['filemd5s'] or []

    


    #    print "installedFileMD5s: %s" % installedFileMD5s

    removedList = []
    if cfg["forceInstall"]:
        return None

    # shrug, the apt headers dont have this, not much
    # we can do about it... Kind of odd considering how
    # paranoid apt is supposed to be about breaking configs...
    if not fileMD5s:
        return None

    if not fileFlags:
        return None

    fileSkipList = cfg["fileSkipList"]
    # bleah, have to use the index here because
    # of rpm's storing of filenames and their md5sums in parallel lists
    for f_i in range(len(fileNames)):
        # code to see if we want to disable this
        for pattern in fileSkipList:
            
            if fnmatch.fnmatch(fileNames[f_i],pattern):
                # got to get a better string to use here
                removedList.append((package, "File Name/pattern"))
                fflag = 1
                break
            # if we found a matching file, no need to
            # examine the rest in this package         
            if fflag:
                break

    configFilesToIgnore = cfg["configFilesToIgnore"] or []

    # cfg reads are a little heavier in this code base, so
    # might as well avoid doing them for every single file
    noReplaceConfig = cfg["noReplaceConfig"]
    for f_i in range(len(fileNames)):
        # Deal with config files
        if noReplaceConfig:
            # check for files that are config files, but skips those that
            # arent going to be replaced anyway
            # (1 << 4) == rpm.RPMFILE_NOREPLACE if it existed
            if fileFlags[f_i] & rpm.RPMFILE_CONFIG and not \
               fileFlags[f_i] & (1 << 4):
                if fileNames[f_i] not in configFilesToIgnore:
                    # check if config file and if so, if modified
                    if checkModified(f_i, fileNames, fileMD5s,
                                     installedFileNames, installedFileMD5s):
                        removedList.append((package, "Config modified"))
                        fflag = 1
                        break

        if fflag:
            break     

    if len(removedList):
        return removedList
    else:
        return None

def checkRpmMd5(fileName):
    _ts = transaction.initReadOnlyTransaction()
    # XXX Verify only header+payload MD5 with f*cked up contrapositive logic
    _ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
    
    fdno = os.open(fileName, os.O_RDONLY)
    try:
        h = _ts.hdrFromFdno(fdno)
    except rpm.error, e:
        _ts.popVSFlags()
        return 0
    os.close(fdno)
    _ts.popVSFlags()
    return 1

# JBJ: there's an rpmlib internal string that's probably more what you want.
# JBJ: You might have multiple rpm packages installed ...
def getRpmVersion():
    _ts = transaction.initReadOnlyTransaction()
    for h in _ts.dbMatch('Providename', "rpm"):
        version = ("rpm", h['version'], h['release'], h['epoch'])
        return version
    else:
        raise up2dateErrors.RpmError("Couldn't determine what version of rpm you are running.\nIf you get this error, try running \n\n\t\trpm --rebuilddb\n\n")



#rpm_version = getRpmVersion()
def getGPGflags():
    cfg = config.initUp2dateConfig()
    keyring_relocatable = 0
    rpm_version = getRpmVersion()
    if up2dateUtils.comparePackages(rpm_version, ("rpm", "4.0.4", "0", None)) >= 0:
        keyring_relocatable = 1

    if keyring_relocatable and cfg["gpgKeyRing"]:
        gpg_flags = "--homedir %s --no-default-keyring --keyring %s" % (gpgUtils.gpg_home_dir, cfg["gpgKeyRing"])
    else:
        gpg_flags = "--homedir %s" % gpgUtils.gpg_home_dir
    return gpg_flags


# given a list of package labels, run rpm -V on them
# and return a dict keyed off that data
def verifyPackages(packages):
    data = {}
    missing_packages = []                                                                            
    # data structure is keyed off package
    # label, with value being an array of each
    # line of the output from -V


    retlist = []
    for package in packages:
        (n,v,r,e,a) = package
        # we have to have at least name...

        # Note: we cant reliable match on epoch, so just
        # skip it... two packages that only diff by epoch is
        # way broken anyway
        name = version = release = arch = None
        if n != "":
            name = n
        if v != "":
            version = v
        if r != "":
            release = r
        if a != "":
            arch = a

        keywords = {}
        for token, value  in (("name", name),
                              ("version", version),
                              ("release",release),
#                              ("epoch",epoch),
                              ("arch", arch)):
            if value != None:
                keywords[token] = value

        headers = installedHeaderByKeyword(**keywords)
	if len(headers) == 0:            
	    missing_packages.append(package)

        for header in headers:
            epoch = header['epoch']
            if epoch == None:
                epoch = ""
            # gpg-pubkey "packages" can have an arch of None, see bz #162701
            h_arch = header["arch"] 
            if h_arch == None:
                h_arch = ""
                
            pkg = (header['name'], header['version'],
                   header['release'], epoch,
                   h_arch)

            # dont include arch in the label if it's a None arch, #162701
            if pkg[4] == "":
                packageLabel = "%s-%s-%s" % (pkg[0], pkg[1], pkg[2])
            else:
                packageLabel = "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])
                
            verifystring = "/usr/bin/rpmverify -V %s" % packageLabel
                                                                                
            fd = os.popen(verifystring)
            res = fd.readlines()
            fd.close()
                                                                                
            reslist = []
            for line in res:
                reslist.append(string.strip(line))
            retlist.append([pkg, reslist])

    return retlist, missing_packages


# run the equiv of `rpm -Va`. It aint gonna
# be fast, but...
def verifyAllPackages():
    data = {}

    packages = getInstalledPackageList(getArch=1)

    ret,missing_packages =  verifyPackages(packages)
    return ret

def rpmCallback(what, amount, total, key, cb):
    if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
        pass
        #fd = os.open(key, os.O_RDONLY)
        #return fd
    elif what == rpm.RPMCALLBACK_INST_START:
        pass
    elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
        print
    elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
        if cb:
            cb(amount, total)
        else:
            print "transaction %.5s%% done\r" % ((float(amount) / total) * 100),
    elif what == rpm.RPMCALLBACK_INST_PROGRESS:
        print "installation %.5s%% done\r" % ((float(amount) / total) * 100),

    if (rpm.__dict__.has_key("RPMCALLBACK_UNPACK_ERROR")):
        if ((what == rpm.RPMCALLBACK_UNPACK_ERROR) or
                   (what == rpm.RPMCALLBACK_CPIO_ERROR)):
            pkg = "%s-%s-%s" % (key[rpm.RPMTAG_NAME],
                                key[rpm.RPMTAG_VERSION],
                                key[rpm.RPMTAG_RELEASE])

            raise up2dateErrors.RpmInstallError, "There was a fatal error installing a package", pkg



    
#FIXME: this looks like a good candidate for caching, since it takes a second
# or two to run, and I can call it a couple of times
def getInstalledPackageList(msgCallback = None, progressCallback = None,
                            getArch=None, getInfo = None):
    pkg_list = []

    
    if msgCallback != None:
        msgCallback("Getting list of packages installed on the system")
 
    _ts = transaction.initReadOnlyTransaction()   
    count = 0
    total = 0
    
    for h in _ts.dbMatch():
        if h == None:
            break
        count = count + 1
    
    total = count
    
    count = 0
    for h in _ts.dbMatch():
        if h == None:
            break
        name = h['name']
        epoch = h['epoch']
        if epoch == None:
            epoch = ""
        version = h['version']
        release = h['release']
        if getArch:
            arch = h['arch']
            # the arch on gpg-pubkeys is "None"...
            if arch:
                pkg_list.append([name, version, release, epoch, arch])
        elif getInfo:
            arch = h['arch']
            cookie = h['cookie']
            if arch and cookie:
                pkg_list.append([name, version, release, epoch, arch, cookie])
        else:
            pkg_list.append([name, version, release, epoch])

        
        if progressCallback != None:
            progressCallback(count, total)
        count = count + 1
    
    pkg_list.sort()
    return pkg_list

def runTransaction(ts, rpmCallback, transdir=None):
    cfg = config.initUp2dateConfig()
    if transdir == None:
        transdir = cfg['storageDir']
    deps = ts.check()
    if deps:
        raise up2dateErrors.DependencyError(
            "Dependencies should have already been resolved, "\
            "but they are not.", deps)
    rc = ts.run(rpmCallback, transdir)
    if rc:
        errors = "\n"
        for e in rc:
            try:
                errors = errors + e[1] + "\n"
            except:
                errors = errors + str(e) + "\n"
        raise up2dateErrors.TransactionError(
            "Failed running transaction of  packages: %s" % errors, deps=rc)
    elif type(rc) == type([]) and not len(rc):
        # let the user know whats wrong
        log = up2dateLog.initLog()
        log.log_me("Failed running rpm transaction - %pre %pro failure ?.")
        raise up2dateErrors.RpmError("Failed running rpm transaction")

def readHeader(filename):
    if not os.access(filename, os.R_OK):
        return None
    blob = open(filename, "r").read()
#    print "reading blob for %s" % filename
    return readHeaderBlob(blob)

def readHeaderBlob(blob, filename=None):
    # Read two unsigned int32
    #print "blob: %s" % blob

#FIXME: for some reason, this fails alot
# not, but with current rpm, we dont really
# need it that much...
#    i0, i1 = struct.unpack("!2I", blob[:8])
#    if len(blob) != i0 * 16 + i1 + 8:
#        # Corrupt header
#        print "ugh, the header corruption test fails:"
#        log.trace_me()
#        return None
    # if this header is corrupt, rpmlib exits and we stop ;-<
    try:
        hdr = rpm.headerLoad(blob)
    except:
        if filename:
            print "rpm was unable to load the header: %s" % filename
        else:
            print "rpm was unable to load a header"
        return None
    # Header successfully read
    #print hdr['name']
    return hdr

def main():


    pkg = ["gpg-pubkey", "db42a60e", "37ea5438" , "", None]

    print verifyPackages([pkg])
    sys.exit()
    # zsh-4.0.4-8
    h = installedHeader("zsh", _ts)
    print
    if h['epoch'] == None:
        epoch = '0'
    pkg = [h['name'], h['version'] , h['release'], epoch, h['arch']]
    print installedHeaderIndexByPkg(pkg)

    pkg = ['kernel', '2.4.18', '7.93', '0','i686']
    print installedHeaderIndexByPkg(pkg)

    pkg = ['kernel', '2.4.18', '3', '0', 'i686']
    print installedHeaderIndexByPkg(pkg)


    print installedHeaderIndex(name="up2date")

    print installedHeaderIndex(epoch="1")

    print installedHeaderByKeyword(version="1.0")
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sourcesConfig
#!/usr/bin/python
#
# This file is a portion of the Red Hat Update Agent
# Copyright (c) 1999 - 2005 Red Hat, Inc.  Distributed under GPL
#
# Authors:
#       Cristian Gafton <gafton@redhat.com>
#       Adrian Likins   <alikins@redhat.com>
#
# $Id: sourcesConfig.py 113619 2007-03-21 19:20:39Z pkilambi $

import os
import sys
import string
import re

import config
import up2dateUtils
import up2dateLog
import wrapperUtils

# The format for sources v1 is stupid. each entry can only be one line
# each different source type has different info (aieee!) # comment stuff out (duh)


SOURCESFILE="/etc/sysconfig/rhn/sources"

def showError(line):
    print "Error parsing %s" % SOURCESFILE
    print "at line: %s" % line

class SourcesConfigFile:
    "class for parsing out the up2date/apt/yum src repo info"
    def __init__(self, filename = None):
        self.repos = []
        self.fileName = filename
        self.log = up2dateLog.initLog()
        self.cfg = config.initUp2dateConfig()
        #just so we dont import repomd info more than onc
        self.setupRepomd = None
        if self.fileName:
            self.load()
            

    def load(self, filename = None):
        if filename:
            self.fileName = filename
        if not self.fileName:
            return

        if not os.access(self.fileName, os.R_OK):
            print "warning: can't access %s" % self.fileName
            return

        f = open(self.fileName, "r")

        
	for line in f.readlines():
            # strip comments
            if '#' in line:
                line = line[:string.find(line, '#')]

            line = string.strip(line)
            if not line:
                continue

            data = string.split(line)
            repoType = data[0]
            if data[0] == "up2date":
                self.parseUp2date(line)
            if data[0] == "yum":
                self.parseYum(line)
            if data[0] == "apt":
                self.parseApt(line)
            if data[0] == "dir":
                self.parseDir(line)
            if data[0] == "bt":
                self.parseBt(line)
            if data[0] == "yum-mirror":
                self.parseYumMirror(line)
            if data[0] == "apt-mirror":
                self.parseAptMirror(line)
            if data[0] == "rpmmd":
                self.parseRpmmd(line)
            if data[0] == "repomd" and not self.setupRepomd:
                self.parseRepomd(line)
                self.setupRepomd = True

        f.close()

    # in some cases, we want to readd the line that points at RHN
    def writeUp2date(self):
        # parse the config file into something editable
        f = open(self.fileName, "r")
        lines = f.readlines()
        index = 0
        for line in lines:
            if '#' in line:
                line = line[:string.find(line, '#')]
                
            line = string.rstrip(line)
            if not line:
                index = index + 1
                continue
            
            firstUsedLine = index
            break
        
        f.close()
        
        f = open(self.fileName, "w")

        lines.insert(firstUsedLine-1, "up2date default\n")
        buf = string.join(lines, '')
        f.write(buf)
        f.close()
        
        
    def parseUp2date(self,line):
        try:
            (tmp, url) = string.split(line)
        except:
            showError(line)
            return
            
        if url == "default":
            self.repos.append({'type':'up2date', 'url':self.cfg['serverURL']})
        else:
            self.repos.append({'type':'up2date', 'url':url})

    def parseDir(self, line):
        try:
            (tmp, name, path) = string.split(line)
        except:
            showError(line)
            return
        
        self.repos.append({'type':'dir','path':path, 'label':name})

    def parseYum(self, line):

        try:
            (tmp, name, url) = string.split(line)
        except:
            showError(line)
            return
        try:
            (tmp, name, url) = string.split(line)
        except:
            showError(line)
            return



        url,name = self.subArchAndVersion(url, name)
        self.repos.append({'type':'yum', 'url':url, 'label':name})

    def subArchAndVersion(self, url,name):
        arch = up2dateUtils.getUnameArch()

        # bz:229847 parsing to get correct release 
        # version instead of hardcoding it, for ex:
        # 3Desktop, 4AS, 3AS
        releasever = re.split('[^0-9]', up2dateUtils.getVersion())[0]
        
        url = string.replace(url, "$ARCH", arch)
        name = string.replace(name, "$ARCH", arch)
        url = string.replace(url, "$RELEASE", releasever)
        name = string.replace(name, "$RELEASE", releasever)

        # support the yum format as well
        url = string.replace(url, "$basearch", arch)
        name = string.replace(name, "$basearch", arch)
        url = string.replace(url, "$releasever", releasever)
        name = string.replace(name, "$releasever", releasever)

        return (url, name)

    def parseYumMirror(self, line):
        try:
            tmp = []
            tmp = string.split(line)
        except:
            showError(line)
            return

        
        url = tmp[2]
        name = tmp[1]

        (url,name) = self.subArchAndVersion(url, name)
        
        self.repos.append({'type':'yum-mirror', 'url':url, 'label':name})
        
    def parseAptMirror(self, line):
        try:
            tmp = []
            tmp = string.split(line)
            server = tmp[2]
            path = tmp[3]
            label = tmp[1]
            dists = tmp[4:]
        except:
            showError(line)
            return

        
        (url,name) = self.subArchAndVersion(url, name)
        for dist in dists:
            self.repos.append({'type':'apt-mirror', 'url':"%s/%s" (server, path),
                               'label':name, 'dist': dist})


    def parseRepomd(self, line):
        try:
            parts = string.split(line)
        except:
            showError(line)
            return

        try:
            from repoBackends import yumBaseRepo
        except ImportError:
            self.log.log_me("Unable to import repomd so repomd support will not be available")
            return
        
        yb = yumBaseRepo.initYumRepo()
        channelName = parts[1]

        # use the built in yum config 
        from yum import repos
 
        for reponame in yb.repos.repos.keys():
            repo = yb.repos.repos[reponame]
            if repo.enabled:
                repo.baseurlSetup()
                # at some point this name got changed in yum
                if hasattr(repo, "baseurls"):
                    (url,name) = self.subArchAndVersion(repo.baseurls[0], repo.id)
                else:
                    (url,name) = self.subArchAndVersion(repo.baseurl[0], repo.id)
                self.repos.append({'type':'repomd', 'url':url, 'label':name})

    def parseApt(self, line):
        # of course, the debian one had to be weird
        # atm, we only support http one's
        try:
            data = string.split(line)
            name = data[1]
            server = data[2]
            path = data[3]
            dists = data[4:]
        except:
            print "Error parsing /etc/sysconfig/rhn/up2date"
            print "at line: %s" % line
            return
        # if multiple dists are appended, make them seperate
        # channels
        for dist in dists:
            self.repos.append({'type':'apt',
                          'url':'%s/%s' % (server, path),
                          'label': "%s-%s" % (name,dist),
                          'dist': dist})


def getSources():
    global sources
    try:
        sources = sources
    except NameError:
        sources = None

    if sources == None:
        scfg = SourcesConfigFile(filename="/etc/sysconfig/rhn/sources")
        sources = scfg.repos
        
    return sources
    
def configHasRepomd(sources):
    for source in sources:
        if source['type'] == "repomd":
            return 1
    return 0                    

########NEW FILE########
__FILENAME__ = transaction
#!/usr/bin/python

#
# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
#         Adrian Likins <alikins@redhat.com
#
#
# a couple of classes wrapping up transactions so that we  
#    can share transactions instead of creating new ones all over
#

import rpm

read_ts = None
ts = None

# ************* NOTE: ************#
# for the sake of clarity, the names "added/removed" as used here
# are indicative of what happened when the original transaction was
# ran. Aka, if you "up2date foobar" and it updates foobar-1-0 with
# foobar-2-0, you added foobar-2-0 and removed foobar-1-0
#
# The reason I mention this explicitly is the trouble of describing
# what happens when you rollback the transaction, which is basically
# the opposite, and leads to plenty of confusion
#


class TransactionData:
    # simple data structure designed to transport info
    # about rpm transactions around
    def __init__(self):
        self.data = {}
        # a list of tuples of pkg info, and mode ('e', 'i', 'u')
        # the pkgInfo is tuple of [name, version, release, epoch, arch]
        # size is never used directly for this, it's here as a place holder
        # arch is optional, if the server specifies it, go with what
        # removed packages only need [n,v,r,e,arch]
	self.data['packages'] = []
        # list of flags to set for the transaction
        self.data['flags'] = []
        self.data['vsflags'] = []
        self.data['probFilterFlags'] = []


    def display(self):
        out = ""
        removed = []
        installed = []
        updated = []
        misc = []
        for (pkgInfo, mode) in self.data['packages']:
            if mode == 'u':
                updated.append(pkgInfo)
            elif mode == 'i':
                installed.append(pkgInfo)
            elif mode == 'e':
                removed.append(pkgInfo)
            else:
                misc.append(pkgInfo)
        for pkgInfo in removed:
            out = out + "\t\t[e] %s-%s-%s:%s\n" % (pkgInfo[0], pkgInfo[1], pkgInfo[2], pkgInfo[3])
        for pkgInfo in installed:
            out = out + "\t\t[i] %s-%s-%s:%s\n" % (pkgInfo[0], pkgInfo[1], pkgInfo[2], pkgInfo[3])
        for pkgInfo in updated:
            out = out + "\t\t[u] %s-%s-%s:%s\n" % (pkgInfo[0], pkgInfo[1], pkgInfo[2], pkgInfo[3])
        for pkgInfo in misc:
            out = out + "\t\t[%s] %s-%s-%s:%s\n" % (pkgInfo[5], pkgInfo[0], pkgInfo[1],
                                                    pkgInfo[2], pkgInfo[3])
        return out

    
# wrapper/proxy class for rpm.Transaction so we can
# instrument it, etc easily
class Up2dateTransaction:
    def __init__(self):
        self.ts = rpm.TransactionSet()
        self._methods = ['dbMatch',
                         'check',
                         'order',
                         'addErase',
                         'addInstall',
                         'run',
                         'IDTXload',
                         'IDTXglob',
                         'rollback',
			 'pgpImportPubkey',
			 'pgpPrtPkts',
			 'Debug',
                         'setFlags',
                         'setVSFlags',
                         'setProbFilter',
                         'hdrFromFdno']
        self.tsflags = []

    def __getattr__(self, attr):
        if attr in self._methods:
            return self.getMethod(attr)
        else:
            raise AttributeError, attr

    def getMethod(self, method):
        # in theory, we can override this with
        # profile/etc info
        return getattr(self.ts, method)

    # push/pop methods so we dont lose the previous
    # set value, and we can potentiall debug a bit
    # easier
    def pushVSFlags(self, flags):
        self.tsflags.append(flags)
        self.ts.setVSFlags(self.tsflags[-1])

    def popVSFlags(self):
        del self.tsflags[-1]
        self.ts.setVSFlags(self.tsflags[-1])
        
def initReadOnlyTransaction():
    global read_ts
    if read_ts == None:
        read_ts =  Up2dateTransaction()
        # FIXME: replace with macro defination
        read_ts.pushVSFlags(-1)
    return read_ts


########NEW FILE########
__FILENAME__ = up2dateAuth
#!/usr/bin/python
#
# $Id: up2dateAuth.py 87091 2005-11-15 17:25:11Z alikins $

import rpcServer
import config
import os
import up2dateErrors
import up2dateUtils
import string
import up2dateLog
import clientCaps
import capabilities

from types import DictType

from rhn import rpclib

loginInfo = None

def getSystemId():
    cfg = config.initUp2dateConfig()
    path = cfg["systemIdPath"]
    if not os.access(path, os.R_OK):
        return None
    
    f = open(path, "r")
    ret = f.read()
        
    f.close()
    return ret

# if a user has upgraded to a newer release of Red Hat but still
# has a systemid from their older release, they need to get an updated
# systemid from the RHN servers.  This takes care of that.
def maybeUpdateVersion():
    cfg = config.initUp2dateConfig()
    try:
        idVer = rpclib.xmlrpclib.loads(getSystemId())[0][0]['os_release']
    except:
        # they may not even have a system id yet.
        return 0

    systemVer = up2dateUtils.getVersion()
    
    if idVer != systemVer:
      s = rpcServer.getServer()
    
      try:
          newSystemId = rpcServer.doCall(s.registration.upgrade_version,
                                         getSystemId(), systemVer)
      except rpclib.Fault, f:
          raise up2dateErrors.CommunicationError(f.faultString)

      path = cfg["systemIdPath"]
      dir = path[:string.rfind(path, "/")]
      if not os.access(dir, os.W_OK):
          try:
              os.mkdir(dir)
          except:
              return 0
      if not os.access(dir, os.W_OK):
          return 0

      if os.access(path, os.F_OK):
          # already have systemid file there; let's back it up
          savePath = path + ".save"
          try:
              os.rename(path, savePath)
          except:
              return 0

      f = open(path, "w")
      f.write(newSystemId)
      f.close()
      try:
          os.chmod(path, 0600)
      except:
          pass



# allow to pass in a system id for use in rhnreg
# a bit of a kluge to make caps work correctly
def login(systemId=None):
    server = rpcServer.getServer()
    log = up2dateLog.initLog()

    # send up the capabality info
    headerlist = clientCaps.caps.headerFormat()
    for (headerName, value) in headerlist:
        server.add_header(headerName, value)

    if systemId == None:
        systemId = getSystemId()

    if not systemId:
        return None
        
    maybeUpdateVersion()
    log.log_me("logging into up2date server")

    # the list of caps the client needs
    caps = capabilities.Capabilities()

    global loginInfo
    try:
        li = rpcServer.doCall(server.up2date.login, systemId)
    except rpclib.Fault, f:
        if abs(f.faultCode) == 49:
#            print f.faultString
            raise up2dateErrors.AbuseError(f.faultString)
        else:
            raise f
    # set a static in the LoginInfo class...
    response_headers =  server.get_response_headers()
    caps.populate(response_headers)

    # figure out if were missing any needed caps
    caps.validate()

#    for i in response_headers.keys():
#        print "key: %s foo: %s" % (i, response_headers[i])

    if type(li) == DictType:
        if type(loginInfo) == DictType:
            # must retain the reference.
            loginInfo.update(li)
        else:
            # this had better be the initial login or we lose the reference.
            loginInfo = li
    else:
        loginInfo = None

    if loginInfo:
        log.log_me("successfully retrieved authentication token "
                   "from up2date server")

    log.log_debug("logininfo:", loginInfo)
    return loginInfo

def updateLoginInfo():
    log = up2dateLog.initLog()
    log.log_me("updating login info")
    # NOTE: login() updates the loginInfo object
    login()
    if not loginInfo:
        raise up2dateErrors.AuthenticationError("Unable to authenticate")
    return loginInfo


def getLoginInfo():
    global loginInfo
    try:
        loginInfo = loginInfo
    except NameError:
        loginInfo = None
    if loginInfo:
        return loginInfo
    # NOTE: login() updates the loginInfo object
    login()
    return loginInfo


########NEW FILE########
__FILENAME__ = up2dateErrors
#!/usr/bin/python
#
# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Preston Brown <pbrown@redhat.com>
#         Adrian Likins <alikins@redhat.com
#         Cristian Gafton <gafton@redhat.com>
#

import up2dateLog


class Error:
    """base class for errors"""
    def __init__(self, errmsg):
        self.errmsg = errmsg
        self.log = up2dateLog.initLog()

    def __repr__(self):
        self.log.log_me(self.errmsg)
        return self.errmsg
    
class FileError(Error):
    """
    error to report when we encounter file errors (missing files/dirs,
    lack of permissions, quoat issues, etc"""
    def __repr__(self):
        msg = "Disk error.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class RpmError(Error):
    """rpm itself raised an error condition"""
    def __repr__(self):
        msg = "RPM error.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class RpmInstallError(Error):
    """Raise when a package fails to install properly"""
    def __init__(self, msg, pkg = None):
        self.errmsg = msg
        self.pkg = pkg
    def __repr__(self):
        msg = "There was a fatal error installing the package:\n"
        msg = msg + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg
    

class PasswordError(Error):
    """Raise when the server responds with that a password is incorrect"""
    def __repr__(self):
        log = up2dateLog.initLog()
        msg = "Password error. The message was:\n" + self.errmsg
        log.log_me(msg)
        return msg

class ConflictError(Error):
    """Raise when a rpm transaction set has a package conflict"""
    def __init__(self, msg, rc=None, data=None):
        self.rc = rc
        self.errmsg = msg
        self.data = data
    def __repr__(self):
        msg = "RPM package conflict error.  The message was:\n"
        msg = msg + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class FileConflictError(Error):
    """Raise when a rpm tranaction set has a file conflict"""
    def __init__(self, msg, rc=None):
        self.rc = rc
        self.errmsg = msg
    def __repr__(self):
        msg = "RPM file conflict error. The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg
    
class DependencyError(Error):
    """Raise when a rpm transaction set has a dependency error"""
    def __init__(self, msg, deps=None):
        self.errmsg = msg
        # just tag on the whole deps tuple, so we have plenty of info
        # to play with
        self.deps = deps
        
    def __repr__(self):
        msg = "RPM dependency error. The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class TransactionError(Error):
    """Raise when a rpm transaction set has a dependency error"""
    def __init__(self, msg, deps=None):
        self.errmsg = msg
        # just tag on the whole deps tuple, so we have plenty of info
        # to play with
        self.deps = deps
        
    def __repr__(self):
        msg = "RPM  error. The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg


class UnsolvedDependencyError(Error):
    """Raise when we have a dependency that the server can not find"""
    def __init__(self, msg, dep=None, pkgs=None):
        self.errmsg = msg
        self.dep = dep
        self.pkgs = pkgs 
    def __repr__(self):
        msg = "RPM dependency error.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class DependencySenseError(Error):
    """
    Raise when a rpm transaction set has a dependency sense "\
    "we don't understand"""
    def __init__(self, msg, sense=None):
        self.errmsg = msg
        self.sense = sense
    def __repr__(self):
        msg = "RPM dependency error.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class SkipListError(Error):
    """Raise when all the packages you want updated are on a skip list"""
    def __init__(self, msg, pkglist=None):
	self.errmsg = msg
	self.pkglist = pkglist 
    def __repr__(self):
        msg = "Package Skip List error.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class FileConfigSkipListError(Error):
    """
    Raise when all the packages you want updated are skip
    because of config or file skip list"""
    def __init__(self, msg, pkglist=None):
        self.errmsg = msg
        self.pkglist = pkglist
    def __repr__(self):
        msg = "File Skip List or config file overwrite error. "\
                "The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg


class CommunicationError(Error):
    """Indicates a problem doing xml-rpc http communication with the server"""
    def __repr__(self):
        msg =  "Error communicating with server. "\
                 "The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class FileNotFoundError(Error):
    """
    Raise when a package or header that is requested returns
    a 404 error code"""
    def __repr__(self):
        msg =  "File Not Found: \n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg


class DelayError(Error):
    """
    Raise when the expected response from a xml-rpc call
    exceeds a timeout"""
    def __repr__(self):
        msg =  "Delay error from server.  The message was:\n" + self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class RpmRemoveSkipListError(Error):
    """Raise when we try to remove a package on the RemoveSkipList"""
    def __repr__(self):
        msg = "Could not remove package \"%s\". "\
                "It was on the RemoveSkipList" % self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class RpmRemoveError(Error):
    """
    Raise when we can't remove a package for some reason
    (failed deps, etc)"""
    def __init__(self, args):
        self.args = args
        self.errmsg = ""
        for key in self.args.keys():
            self.errmsg = self.errmsg + "%s failed because of %s\n" % (
                key, self.args[key])
        self.data = self.args
    def __repr__(self):
        return self.errmsg

class GPGInstallationError(Error):
    """Raise when we we detect that the GPG is not installed properly"""
    def __repr__(self):
        msg = "GPG is not installed properly."
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class GPGKeyringError(Error):
    """
    Raise when we we detect that the gpg keyring for the user
    does not have the Red Hat Key installed"""
    def __repr__(self):
        msg = "GPG keyring does not include the Red Hat, Inc. "\
                "public package-signing key"
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class GPGVerificationError(Error):
    """Raise when we fail to verify a package is signed with a gpg signature"""
    def __init__(self, msg):
        self.errmsg = msg
        self.pkg = msg
    def __repr__(self):
        msg = "The package %s failed its gpg signature verification. "\
                "This means the package is corrupt." % self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class GPGVerificationUnsignedPackageError(Error):
    """
    Raise when a package that is supposed to be verified has
    no gpg signature"""
    def __init__(self, msg):
        self.errmsg = msg
        self.pkg = msg
    def __repr__(self):
        msg = "Package %s does not have a GPG signature.\n" %  self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class GPGVerificationUntrustedKeyError(Error):
    """
    Raise when a package that is supposed to be verified has an
    untrusted gpg signature"""
    def __init__(self, msg):
        self.errmsg = msg
        self.pkg = msg
    def __repr__(self):
        msg = "Package %s has a untrusted GPG signature.\n" % self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class GPGVerificationUnknownKeyError(Error):
    """
    Raise when a package that is supposed to be verified has an
    unknown gpg signature"""
    def __init__(self, msg):
        self.errmsg = msg
        self.pkg = msg
    def __repr__(self):
        msg = "Package %s has a unknown GPG signature.\n" % self.errmsg
        log = up2dateLog.initLog()
        log.log_me(msg)
        return msg

class OutOfSpaceError(Error):
    def __init__(self, totalSize, freeDiskSpace):
        self.ts = totalSize
        self.fds = freeDiskSpace
        self.errmsg = "The total size of the selected packages (%d kB) "\
                      "exceeds your free disk space (%d kB)." % (
            self.ts, self.fds)

    def __repr__(self):
        return self.errmsg

class ServerThrottleError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg
    
class AbuseError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class AuthenticationTicketError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class AuthenticationError(Error):
    def __init__(self, msg):
        self.errmsg = msg
 
    def __repr__(self):
        return self.errmsg

class ValidationError(Error):
    def __init__(self, errmsg):
        Error.__init__(self, errmsg)

    # indicates an error during server input validation
    def __repr__(self):
        return "Error validating data at server:\n" + self.errmsg

class InvalidProductRegistrationError(Error):
    def __init__(self, errmsg):
        Error.__init__(self, errmsg)

    # indicates an error during server input validation
    def __repr__(self):
        return "The subscription number is invalid" + self.errmsg
    
class OemInfoFileError(Error):
    def __init__(self,errmsg):
        Error.__init__(self, errmsg)

    def __repr__(self):
        return "Error parsing the oemInfo file at field:\n" + self.errmsg

class NoRollbacksToUndoError(Error):
    """
    Raise when attempting to undo but there are no rollbacks"""
    def __repr__(self):
        log = up2dateLog.initLog()
        log.log_me(self.errmsg)
        return self.errmsg

class RhnUuidUniquenessError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class Up2dateNeedsUpdateError(Error):
    def __init__(self, msg=""):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class ServerCapabilityError(Error):
    def __init__(self, msg, errorlist=None):
        self.errmsg = msg
        self.errorlist = []
        if errorlist:
            self.errorlist=errorlist

    def __repr__(self):
        return self.errmsg

class ServerCapabilityMissingError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class ServerCapabilityVersionError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class NoChannelsError(Error):
    def __init__(self, msg):
        self.errmsg = msg

    def __repr__(self):
        return self.errmsg

class PackageNotAvailableError(Error):
    def __init__(self, msg, missing_packages=None):
        self.errmsg = msg
        self.missing_packages = missing_packages
    def __repr__(self):
        errstring = "%s\n" % self.errmsg
        for i in self.missing_packages:
            errstring = errstring + "%s\n" % i
        return errstring

class PackageArchNotAvailableError(Error):
    def __init__(self, msg, missing_packages=None):
        self.errmsg = msg
        self.missing_packages = missing_packages
    def __repr__(self):
        errstring = "%s\n" % self.errmsg
        for i in self.missing_packages:
            errstring = errstring + "%s\n" % i
        return errstring

########NEW FILE########
__FILENAME__ = up2dateLog
#!/usr/bin/python
#
# $Id: up2dateLog.py 87091 2005-11-15 17:25:11Z alikins $

import time
import string
import config

class Log:
    """
    attempt to log all interesting stuff, namely, anything that hits
    the network any error messages, package installs, etc
    """ # " emacs sucks
    def __init__(self):
        self.app = "up2date"
        self.cfg = config.initUp2dateConfig()
        

    def log_debug(self, *args):
        if self.cfg["debug"] > 1:
            apply(self.log_me, args, {})
            if self.cfg["isatty"]:
                print "D:", string.join(map(lambda a: str(a), args), " ")
                
    def log_me(self, *args):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
	s = ""
        for i in args:
            s = s + "%s" % (i,)
        self.write_log(s)

    def trace_me(self):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
        import traceback
        x = traceback.extract_stack()
        bar = string.join(traceback.format_list(x))
        self.write_log(bar)

    def log_exception(self, type, value, tb):
        self.log_info = "[%s] %s" % (time.ctime(time.time()), self.app)
        import traceback
        x = traceback.extract_tb(tb)
        bar = string.join(traceback.format_list(x))
        # all of the exception we raise include an errmsg string
        if hasattr(value, "errmsg"):
            self.write_log(value.errmsg)
        self.write_log(bar)
        
    def write_log(self, s):
        
        log_name = self.cfg["logFile"] or "/var/log/up2date"
        log_file = open(log_name, 'a')
        msg = "%s %s\n" % (self.log_info, str(s))
        log_file.write(msg)
        log_file.flush()
        log_file.close()

def initLog():
    global log
    try:
        log = log
    except NameError:
        log = None

    if log == None:
        log = Log()

    return log

########NEW FILE########
__FILENAME__ = up2dateMessages
#!/usr/bin/python
#
#  module containing all the shared messages used by up2date
#
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Adrian Likins <alikins@redhat.com
#
# $Id: up2dateMessages.py 87080 2005-11-04 20:49:52Z alikins $

from up2date_client import config

#cfg = config.initUp2dateConfig()

needToRegister = "You need to register this system by running `up2date --register` before using this option"

storageDirWarningMsg = """The storage directory %s could not be found, or was not
accessable.""" % "/var/spool/up2date"

rootWarningMsg = "You must run the Update Agent as root."

registeredWarningMsg = """You are not registered with Red Hat Network.  To use Update Agent,
You must be registered.

To register, run \"up2date --register\"."""


gpgWarningGuiMsg = """Your GPG keyring does not contain the Red Hat, Inc. public key.
Without it, you will be unable to verify that packages Update Agent downloads
are securely signed by Red Hat.

Your Update Agent options specify that you want to use GPG."""

gpgWarningMsg = """Your GPG keyring does not contain the Red Hat, Inc. public key.
Without it, you will be unable to verify that packages Update Agent downloads
are securely signed by Red Hat.

Your Update Agent options specify that you want to use GPG.

To install the key, run the following as root:
"""

########NEW FILE########
__FILENAME__ = up2dateUtils
#/usr/bin/python
# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Preston Brown <pbrown@redhat.com>
#         Adrian Likins <alikins@redhat.com>
#
"""utility functions for up2date"""

import re
import os
import sys
import time
import rpm
import string

# Python >= 2.5
try:
    from hashlib import md5 as md5hash
# Python <= 2.4
except ImportError:
    from md5 import new as md5hash

sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")
import rpmUtils
import up2dateErrors
import transaction
import config


def rpmFlagsToOperator(flags):
    flags = flags & 0xFF
    buf = ""
    if flags != 0:
        if flags & rpm.RPMSENSE_LESS:
            buf = buf + "<"
        if flags & rpm.RPMSENSE_GREATER:
            buf = buf + ">"
        if flags & rpm.RPMSENSE_EQUAL:
            buf = buf + "="
        if flags & rpm.RPMSENSE_SERIAL:
            buf = buf + "S"
    return buf

def getPackageSearchPath():
    dir_list = []
    cfg = config.initUp2dateConfig()
    dir_list.append(cfg["storageDir"])

    dir_string = cfg["packageDir"]
    if dir_string:
        paths = string.split(dir_string, ':')
        fullpaths = []
        for path in paths:
            fullpath = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
            fullpaths.append(fullpath)
    	dir_list = dir_list + fullpaths
    return dir_list

def pkgToString(pkg):
    return "%s-%s-%s" % (pkg[0], pkg[1], pkg[2])

def pkgToStringArch(pkg):
    return "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])

def pkglistToString(pkgs):
    packages = "("
    for pkg in pkgs:
	packages = packages + pkgToString(pkg) + ","
    packages = packages + ")"
    return packages

def restartUp2date():
    print "Restarting up2date"
    args = sys.argv[:]
    return_code = os.spawnvp(os.P_WAIT, sys.argv[0], args)
    sys.exit(return_code)

def comparePackagesArch(pkg1, pkg2):
    arch1 = pkg1[4]
    arch2 = pkg2[4]

    score1 = rpm.archscore(arch1)
    score2 = rpm.archscore(arch2)

    if score1 > score2:
        return 1
    if score1 < score2:
        return -1
    if score1 == score2:
        return 0

# compare two RPM packages
def comparePackages(pkgLabel1, pkgLabel2):
    version1 = pkgLabel1[1]
    release1 = pkgLabel1[2]
    epoch1 = pkgLabel1[3]
    version2 = pkgLabel2[1]
    release2 = pkgLabel2[2]
    epoch2 = pkgLabel2[3]

    if epoch1 == "" or epoch1 == 0 or epoch1 == "0":
        epoch1 = None
    else:
        epoch1 = "%s" % epoch1
        
    if epoch2 == "" or epoch2 == 0 or epoch2 == "0":
            epoch2 = None
    else:
        epoch2 = "%s" % epoch2
        
    return rpm.labelCompare((epoch1, version1, release1),
                            (epoch2, version2, release2))
    

def parseObsoleteVersion(ver):
    s = ver
    epoch = ""
    if string.find(s, ":") >= 0:
        arr = string.split(s, ":", 1)
        epoch = arr[0]
        s = arr[1]
    release = "0"
    if string.find(s, '-') >= 0:
        arr = string.split(s, "-", 1)
        release = arr[1]
        s = arr[0]
    return s, release, epoch


def cmp2rpmSense(value):
    if value < 0:
        return rpm.RPMSENSE_LESS
    if value > 0:
        return rpm.RPMSENSE_GREATER
    return rpm.RPMSENSE_EQUAL

# see if a package is obsoleted by a given
# obsolete version and sense
def isObsoleted(obs, pkg, package=None):
    # if the obsoleting package and the package
    # to be obsoleted are different arches, it doesnt count
    if package:
        if pkg[4] != "noarch" and package[4] != "noarch":
            if pkg[4] != package[4]:
                return 0
    (n,v,r,e,a,obsName, obsVersion,obsSense) = obs
    if obsSense == "0":
        return 1
    candidate = (pkg[0], pkg[1], pkg[2], pkg[3])
    vv, rr, ee = parseObsoleteVersion(obsVersion)
    obsCandidate = (obsName, vv, rr, ee)
    ret = comparePackages(candidate, obsCandidate)
    op = cmp2rpmSense(ret)
    if op & int(obsSense):
        return 1

    return 0
    
    
    

def md5sum(fileName):
    hashvalue = md5hash()
    
    try:
        f = open(fileName, "r")
    except:
        return ""

    fData = f.read()
    hashvalue.update(fData)
    del fData
    f.close()
    
    hexvalue = string.hexdigits
    md5res = ""
    for c in hashvalue.digest():
        i = ord(c)
        md5res = md5res + hexvalue[(i >> 4) & 0xF] + hexvalue[i & 0xf]

    return md5res

# return a glob for your particular architecture.
def archGlob():
    if re.search("i.86", os.uname()[4]):
        return "i?86"
    elif re.search("sparc", os.uname()[4]):
        return "sparc*"
    else:
        return os.uname()[4]

def getProxySetting():
    cfg = config.initUp2dateConfig()
    proxy = None
    proxyHost = cfg["httpProxy"]
    # legacy for backwards compat
    if proxyHost == "":
        try:
            proxyHost = cfg["pkgProxy"]
        except:
            proxyHost = None

    if proxyHost:
        if proxyHost[:7] == "http://":
            proxy = proxyHost[7:]
        else:
            proxy = proxyHost

    return proxy

def getOSVersionAndRelease():
    cfg = config.initUp2dateConfig()
    ts = transaction.initReadOnlyTransaction()
    for h in ts.dbMatch('Providename', "redhat-release"):
        if cfg["versionOverride"]:
            version = cfg["versionOverride"]
        else:
            version = h['version']

        releaseVersion = (h['name'], version)
        return releaseVersion
    else:
       raise up2dateErrors.RpmError(
           "Could not determine what version of Red Hat Linux you "\
           "are running.\nIf you get this error, try running \n\n"\
           "\t\trpm --rebuilddb\n\n")



def getVersion():
    release, version = getOSVersionAndRelease()

    return version

def getOSRelease():
    release, version = getOSVersionAndRelease()
    return release

def getArch():
    if not os.access("/etc/rpm/platform", os.R_OK):
        return os.uname()[4]

    fd = open("/etc/rpm/platform", "r")
    platform = string.strip(fd.read())

    return platform

# FIXME: and again, ripped out of r-c-packages
# FIXME: ripped right out of anaconda, belongs in rhpl
def getUnameArch():
    arch = os.uname()[4]
    if (len (arch) == 4 and arch[0] == 'i' and
        arch[2:4] == "86"):
        arch = "i386"
                                                                                
    if arch == "sparc64":
        arch = "sparc"
                                                                                
    if arch == "s390x":
        arch = "s390"
                                                                                
    return arch



def version():
    # substituted to the real version by the Makefile at installation time.
    return "4.5.5-8.el3"

def pprint_pkglist(pkglist):
    if type(pkglist) == type([]):
        foo = map(lambda a : "%s-%s-%s" % (a[0],a[1],a[2]), pkglist)
    else:
        foo = "%s-%s-%s" % (pkglist[0], pkglist[1], pkglist[2])
    return foo

def genObsoleteTupleFromHdr(hdr):
    epoch = hdr['epoch']
    if epoch == None:
        epoch = ""
    # I think this is right, check with misa
    obsname =  hdr['obsoletename']
    obsvers = hdr['obsoleteversion']
    obsflags = hdr['obsoleteflags']
    name = hdr['name']
    version = hdr['version']
    release =  hdr['release']
    arch = hdr['arch']

    if type(obsname) == type([]) and len(obsname) > 1:
        obs = []
        for index in range(len(obsname)):
            obs.append([name, version, release, epoch, arch,
                   obsname[index], obsvers[index], obsflags[index]])
        return obs
    else:
        vers = ""
        if obsvers:
            vers = obsvers[0]
        flags = 0
        if obsflags:
	    if type(obsflags) == type([]):
               flags = obsflags[0]
	    else:
	       flags = obsflags	
        obs = [name, version, release, epoch, arch,
               obsname[0], vers, flags]
        return [obs]
    return None


def freeDiskSpace():
    cfg = config.initUp2dateConfig()
    import statvfs

    dfInfo = os.statvfs(cfg["storageDir"])
    return long(dfInfo[statvfs.F_BAVAIL]) * (dfInfo[statvfs.F_BSIZE])

# file used to keep track of the next time rhn_check 
# is allowed to update the package list on the server
LAST_UPDATE_FILE="/var/lib/up2date/dbtimestamp"
 
# the package DB expected to change on each RPM list change
#dbpath = "/var/lib/rpm"
#if cfg['dbpath']:
#    dbpath = cfg['dbpath']
#RPM_PACKAGE_FILE="%s/Packages" % dbpath 

def touchTimeStamp():
    try:
        file_d = open(LAST_UPDATE_FILE, "w+")
        file_d.close()
    except:
        return (0, "unable to open the timestamp file", {})
    # Never update the package list more than once every hour.
    t = time.time()
    try:
        os.utime(LAST_UPDATE_FILE, (t, t))

    except:
        return (0, "unable to set the time stamp on the time stamp file %s" % LAST_UPDATE_FILE, {})

########NEW FILE########
__FILENAME__ = urlMirrors
#!/usr/bin/python

import os
import sys
import string

import config
import up2dateUtils
from repoBackends import urlUtils

def getMirrors(source, defaultMirrorUrl=None):
    cfg = config.initUp2dateConfig()
    mirrorPath = "/etc/sysconfig/rhn/mirrors/"

    mirrorType = ""
    if cfg.has_key("mirrorLocation"):
        mirrorType = cfg['mirrorLocation']
    
    if mirrorType != "":
        mirrorFile = "%s/%s.%s" % (mirrorPath, source['label'], mirrorType)
    else:
        mirrorFile = "%s/%s" % (mirrorPath, source['label'])

 #   print "source: %s" % source
    mirrors = []
    arch = up2dateUtils.getUnameArch()
 #   print "mf1: %s" % mirrorFile
    if os.access(mirrorFile, os.R_OK):
 #       print "mirrorFile: %s" % mirrorFile
        f = open(mirrorFile, "r")
        for line in f.readlines():
            if line[0] == "#":
                continue
            line = string.strip(line)
            # just in case we want to add more info, like weight, etc
            tmp = []
            tmp = string.split(line, ' ')
            # sub in arch so we can use one mirror list for all arches
            url = string.replace(tmp[0], "$ARCH", arch)

            mirrors.append(url)

    # if there were user defined mirrors, use them
    if mirrors:
#        print "mirrors from /etc: %s" % mirrors
        return mirrors

#    print "gh2"
    #otherwise look for the dymanic ones in /var/spool/up2date
    mirrorPath = cfg['storageDir']
    mirrorFile = "%s/%s" % (mirrorPath, source['label'])
    mirrors = []

# we should cache these and do If-Modified fetches like we
# do for the package list info

##    if os.access(mirrorFile, os.R_OK):
###        print "mirrorFile: %s" % mirrorFile
##        f = open(mirrorFile, "r")
##        for line in f.readlines():
##            line = string.strip(line)
##            # just in case we want to add more info, like weight, etc
##            tmp = []
##            tmp = string.split(line, ' ')

##            mirrors.append(tmp[0])

    # if there were user defined mirrors, use them
    if mirrors:
        return mirrors

#    print "gh3"
    # download and save the latest mirror list

    # use the hardcode url for the moment, till we can
    # expect mirror lists to be in the base of the repo, hopefully
    # soon
    if defaultMirrorUrl == None:
        return []
    
    # we could try something heirarch here, aka, mirrors.us.es first, then mirrors.us, then mirrors
    if mirrorType != "":
        mirrorUrl = "%s.%s" % (defaultMirrorUrl,mirrorType)
    else:
        mirrorUrl = "%s" % (defaultMirrorUrl)

    print mirrorUrl
    try:
    
        readfd = urlUtils.open_resource(mirrorUrl, agent="Up2date/%s" % up2dateUtils.version())
    except IOError:
#        print "gh5"
        return []
#    print "DDDmirrorFile: %s" % mirrorFile
    fd = open(mirrorFile, "w")
    fd.write(readfd.read())
    readfd.close()
    fd.close()

    arch = up2dateUtils.getUnameArch()
    if os.access(mirrorFile, os.R_OK):
#        print "mirrorFile2: %s" % mirrorFile
        f = open(mirrorFile, "r")
        for line in f.readlines():
            line = string.strip(line)
            # blank line
            if len(line) == 0:
                continue
            if line[0] == "#":
                continue
            # just in case we want to add more info, like weight, etc
            tmp = []
            tmp = string.split(line, ' ')

            url = string.replace(tmp[0], "$ARCH", arch)
            mirrors.append(url)
    

#    print "mirrors: %s" % mirrors
    return mirrors

	

########NEW FILE########
__FILENAME__ = wrapperUtils
#!/usr/bin/python
#
# $Id: wrapperUtils.py 87091 2005-11-15 17:25:11Z alikins $

import os   
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")
import time
import string

import rpm

import up2dateErrors
import up2dateMessages
import rpmUtils
import rhnErrata
import up2dateUtils
import rpcServer
import config

# used for rpmCallbacks, hopefully better than having
# lots of globals lying around...
class RpmCallback:
    def __init__(self):
        self.fd = 0
        self.hashesPrinted = None
        self.progressCurrent = None
        self.progressTotal = None
        self.hashesPrinted = None
        self.lastPercent = None
        self.packagesTotal = None
        self.cfg = config.initUp2dateConfig()

    def callback(self, what, amount, total, hdr, path):
#        print "what: %s amount: %s total: %s hdr: %s path: %s" % (
#          what, amount, total, hdr, path)

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            fileName = "%s/%s-%s-%s.%s.rpm" % (path,
                                               hdr['name'],
                                               hdr['version'],
                                               hdr['release'],
                                               hdr['arch'])
            try:
                self.fd = os.open(fileName, os.O_RDONLY)
            except OSError:
                raise up2dateErrors.RpmError("Error opening %s" % fileName)

            return self.fd
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            os.close(self.fd)
            self.fd = 0

        elif what == rpm.RPMCALLBACK_INST_START:
            self.hashesPrinted = 0
            self.lastPercent = 0
            if type(hdr) == type(""):
                print "     %-23.23s" % ( hdr),
                sys.stdout.flush()

            else:
                fileName = "%s/%s-%s-%s.%s.rpm" % (path,
                                                   hdr['name'],
                                                   hdr['version'],
                                                   hdr['release'],
                                                   hdr['arch'])
                if self.cfg["isatty"]:
                    if self.progressCurrent == 0:
                        printit("Installing") 
                    print "%4d:%-23.23s" % (self.progressCurrent + 1,
                                            hdr['name']),
                    sys.stdout.flush()
                else:
                    printit("Installing %s" % fileName)


        # gets called at the start of each repackage, with a count of
        # which package and a total of the number of packages aka:
        # amount: 2 total: 7 for the second package being repackages
        # out of 7. That sounds obvious doesnt it?
        elif what == rpm.RPMCALLBACK_REPACKAGE_PROGRESS:
            pass
#            print "what: %s amount: %s total: %s hdr: %s path: %s" % (
#            what, amount, total, hdr, path)
#            self.printRpmHash(amount, total, noInc=1)
            
        elif what == rpm.RPMCALLBACK_REPACKAGE_START:
            printit( "Repackaging")
            #sys.stdout.flush()
            #print "what: %s amount: %s total: %s hdr: %s path: %s" % (
            # what, amount, total, hdr, path)
            
        elif what == rpm.RPMCALLBACK_INST_PROGRESS:
            if type(hdr) == type(""):
                # repackage...
                self.printRpmHash(amount,total, noInc=1)
            else:
                self.printRpmHash(amount,total)


        elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
            self.printRpmHash(amount, total, noInc=1)

            
        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.hashesPrinted = 0
            self.lastPercent = 0
            self.progressTotal = 1
            self.progressCurrent = 0
            print "%-23.23s" % "Preparing",
            sys.stdout.flush()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.printRpmHash(1, 1)
            self.progressTotal = self.packagesTotal
            self.progressCurrent = 0
            
        elif (what == rpm.RPMCALLBACK_UNINST_PROGRESS or
              what == rpm.RPMCALLBACK_UNINST_START or
              what == rpm.RPMCALLBACK_UNINST_STOP):
            pass
        
        if hasattr(rpm, "RPMCALLBACK_UNPACK_ERROR"):
            if ((what == rpm.RPMCALLBACK_UNPACK_ERROR) or
                (what == rpm.RPMCALLBACK_CPIO_ERROR)):
                pkg = "%s-%s-%s" % (hdr[rpm.RPMTAG_NAME],
                                    hdr[rpm.RPMTAG_VERSION],
                                    hdr[rpm.RPMTAG_RELEASE])

                if what == rpm.RPMCALLBACK_UNPACK_ERROR:
                    raise up2dateErrors.RpmInstallError, (
                        "There was a rpm unpack error "\
                        "installing the package: %s" % pkg, pkg)
                elif what == rpm.RPMCALLBACK_CPIO_ERROR:
                    raise up2dateErrors.RpmInstallError, (
                        "There was a cpio error "\
                        "installing the package: %s" % pkg, pkg)

    # ported from C code in RPM 2/28/01 -- PGB
    def printRpmHash(self,amount, total, noInc=0):
        hashesTotal = 44

        if total:
            percent = int(100 * (float(amount) / total))
        else:
            percent = 100
    
        if percent <= self.lastPercent:
            return

        self.lastPercent = percent

        if (self.hashesPrinted != hashesTotal):
            if total:
                hashesNeeded = int(hashesTotal * (float(amount) / total))
            else:
                hashesNeeded = hashesTotal

            if self.cfg["isatty"]:
                for i in range(hashesNeeded):
                    sys.stdout.write('#')

                for i in range(hashesNeeded, hashesTotal):
                    sys.stdout.write(' ')

                print "(%3d%%)" % percent, 
                for i in range(hashesTotal + 6):
                    sys.stdout.write("\b")

            self.hashesPrinted = hashesNeeded
            
            if self.hashesPrinted == hashesTotal:
                if self.cfg["isatty"]: 
                    #global progressCurrent, progressTotal
                    for i in range(1,hashesTotal):
                        sys.stdout.write("#")
                    # I dont want to increment the progress count for
                    # repackage info. Bit of a kluge
                    if not noInc:
                        self.progressCurrent = self.progressCurrent + 1
                    if self.progressTotal:
                        print " [%3d%%]" % int(100 * (float(self.progressCurrent) /
                                                      self.progressTotal))
                    else:
                        print " [%3d%%]" % 100

        sys.stdout.flush()


# this is used outside of rpmCallbacks, so
# cant really make it a method of rpmCallback
lastPercent = 0
def percent(amount, total, speed = 0, sec = 0):
    cfg = config.initUp2dateConfig()
    hashesTotal = 40

    if total:
        hashesNeeded = int(hashesTotal * (float(amount) / total))
    else:
        hashesNeeded = hashesTotal

    global lastPercent
    # dont print if were not running on a tty
    if cfg["isatty"] and (hashesNeeded > lastPercent or amount == total):
        for i in range(hashesNeeded):
            sys.stdout.write('#')

        sys.stdout.write('\r')

        if amount == total:
            print

    if amount == total:
        lastPercent = 0
    else:
        lastPercent = hashesNeeded



def printRetrieveHash(amount, total, speed = 0, secs = 0):
    cfg = config.initUp2dateConfig()
    hashesTotal = 26
    
    if total:
        percent = int(100 * (float(amount) / total))
        hashesNeeded = int(hashesTotal * (float(amount) / total))
    else:
        percent = 100
        hashesNeeded = hashesTotal

    if cfg["isatty"]:
        for i in range(hashesNeeded):
            sys.stdout.write('#')

        for i in range(hashesNeeded, hashesTotal):
            sys.stdout.write(' ')

    if cfg["isatty"]:
        if amount == total:
            print "%-25s" % " Done."
        else:
            print "%4d k/sec, %02d:%02d:%02d rem." % \
                  (speed / 1024, secs / (60*60), (secs % 3600) / 60,
                   secs % 60),
            for i in range(hashesTotal + 25):
                sys.stdout.write("\b")
    elif amount == total:
        print "Retrieved."

def printPkg(name, shortName = None):
    if shortName:
        print "%-27.27s " % (shortName + ":"),
    else:
        print "%-27.27s " % (name + ":"),

def printit(a):
    print "\n" + a + "..."


# generic warning dialog used in several places in wrapper
def warningDialog(message, hasGui):
    if hasGui:
        try:
            from up2date_client import gui
            gui.errorWindow(message)
        except:
            print "Unable to open gui. Try `up2date --nox`"
            print message
    else:
        print message


def printDepPackages(depPackages):
    print "The following packages were added to your selection to satisfy dependencies:"
    print """
Name                                    Version        Release
--------------------------------------------------------------"""
    for pkg in depPackages:
        print "%-40s%-15s%-20s" % (pkg[0], pkg[1], pkg[2])
    print
    
def stdoutMsgCallback(msg):
    print msg

warningCallback = stdoutMsgCallback


# these functions are kind of ugly but...
def printVerboseList(availUpdates):
    cfg = config.initUp2dateConfig()
    if cfg['showChannels']:
        print """
Name                          Version        Rel             Channel     
----------------------------------------------------------------------"""
        for pkg in availUpdates:
            print "%-30s%-15s%-15s%-20s" % (pkg[0], pkg[1], pkg[2], pkg[6])
            if cfg["debug"]:
                time.sleep(.25)
                advisories = rhnErrata.getAdvisoryInfo(pkg)
                if advisories:
                    for a in advisories:
                        topic = string.join(string.split(a['topic']), ' ')
                        print "[%s] %s\n" % (a['advisory'], topic)
                else:
                    print "No advisory information available\n"
        print
        return
    print """
Name                                    Version        Rel     
----------------------------------------------------------"""
    for pkg in availUpdates:
        print "%-40s%-15s%-18s%-6s" % (pkg[0], pkg[1], pkg[2], pkg[4])
        if cfg["debug"]:
            time.sleep(.25)
            advisories = rhnErrata.getAdvisoryInfo(pkg)
            if advisories:
                for a in advisories:
                    topic = string.join(string.split(a['topic']), ' ')
                    print "[%s] %s\n" % (a['advisory'], topic)
            else:
                print "No advisory information available\n"
    print

def printSkippedPackages(skippedUpdates):
    cfg = config.initUp2dateConfig()
    print "The following Packages were marked to be skipped by your configuration:"
    print """
Name                                    Version        Rel  Reason
-------------------------------------------------------------------------------"""
    for pkg,reason in skippedUpdates:
        print "%-40s%-15s%-5s%s" % (pkg[0], pkg[1], pkg[2], reason)
        if cfg["debug"]:
            time.sleep(.25)
            advisories = rhnErrata.getAdvisoryInfo(pkg)
            if advisories:
                for a in advisories:
                    topic = string.join(string.split(a['topic']), ' ')
                    print "[%s] %s\n" % (a['advisory'], topic)
            else:
                print "No advisory information available\n"
    print

def printEmptyGlobsWarning(listOfGlobs):
    print "The following wildcards did not match any packages:"
    for token in listOfGlobs:
        print token

def printEmptyCompsWarning(listOfComps):
    print "The following groups did not match any packages:"
    for token in listOfComps:
        print token

def printObsoletedPackages(obsoletedPackages):
    print "The following Packages are obsoleted by newer packages:"
    print """
Name-Version-Release        obsoleted by      Name-Version-Release
-------------------------------------------------------------------------------"""
    for (obs,newpackages) in obsoletedPackages:
        obsstr = "%s-%s-%s" % (obs[0],obs[1],obs[2])
        newpackage = newpackages[0]
        newstr = "%s-%s-%s" % (newpackage[0], newpackage[1], newpackage[2])
        print "%-40s%-40s" % (obsstr, newstr)
        # we can have more than one package obsoleting something
        for newpackage in newpackages[1:]:
            newstr = "%s-%s-%s" % (newpackage[0], newpackage[1], newpackage[2])
            print "%-40s%-40s\n" % ("", newstr)
                                       
def  printInstalledObsoletingPackages(installedObsoletingPackages):
    print "The following packages were not installed because they are obsoleted by installed packages:"
    print """
Name-Version-Release       obsoleted by      Name-Version-Release
-------------------------------------------------------------------------------"""
    for (obsoleted, obsoleting) in installedObsoletingPackages:
        obsstr = "%s-%s-%s" % (obsoleted[0],obsoleted[1],obsoleted[2])
        print "%-40s%-40s" % (obsstr, obsoleting[0])
        for obsoletingstr in obsoleting[1:]:
            print "%-40s%-40s" % (obsstr, obsoletingstr)

def printAvailablePackages(availablePackages):
    print "The following packages are not installed but available from Red Hat Network:"
    print """
Name                                    Version        Release  
--------------------------------------------------------------"""
    for pkg in availablePackages:
        print "%-40s%-14s%-14s" % (pkg[0], pkg[1], pkg[2])
    print

########NEW FILE########
