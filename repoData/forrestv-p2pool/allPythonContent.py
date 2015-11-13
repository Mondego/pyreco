__FILENAME__ = fpconst
"""Utilities for handling IEEE 754 floating point special values

This python module implements constants and functions for working with
IEEE754 double-precision special values.  It provides constants for
Not-a-Number (NaN), Positive Infinity (PosInf), and Negative Infinity
(NegInf), as well as functions to test for these values.

The code is implemented in pure python by taking advantage of the
'struct' standard module. Care has been taken to generate proper
results on both big-endian and little-endian machines. Some efficiency
could be gained by translating the core routines into C.

See <http://babbage.cs.qc.edu/courses/cs341/IEEE-754references.html>
for reference material on the IEEE 754 floating point standard.

Further information on this package is available at
<http://www.analytics.washington.edu/statcomp/projects/rzope/fpconst/>.

------------------------------------------------------------------
Author:    Gregory R. Warnes <Gregory.R.Warnes@Pfizer.com>
Date:      2005-02-24
Version:   0.7.2
Copyright: (c) 2003-2005 Pfizer, Licensed to PSF under a Contributor Agreement
License:   Licensed under the Apache License, Version 2.0 (the"License");
	   you may not use this file except in compliance with the License.
	   You may obtain a copy of the License at

	       http://www.apache.org/licenses/LICENSE-2.0

	   Unless required by applicable law or agreed to in
	   writing, software distributed under the License is
	   distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
	   CONDITIONS OF ANY KIND, either express or implied.  See
	   the License for the specific language governing
	   permissions and limitations under the License.
------------------------------------------------------------------
"""

__version__ = "0.7.2"
ident = "$Id: fpconst.py,v 1.16 2005/02/24 17:42:03 warnes Exp $"

import struct, operator

# check endianess
_big_endian = struct.pack('i',1)[0] != '\x01'

# and define appropriate constants
if(_big_endian): 
    NaN    = struct.unpack('d', '\x7F\xF8\x00\x00\x00\x00\x00\x00')[0]
    PosInf = struct.unpack('d', '\x7F\xF0\x00\x00\x00\x00\x00\x00')[0]
    NegInf = -PosInf
else:
    NaN    = struct.unpack('d', '\x00\x00\x00\x00\x00\x00\xf8\xff')[0]
    PosInf = struct.unpack('d', '\x00\x00\x00\x00\x00\x00\xf0\x7f')[0]
    NegInf = -PosInf

def _double_as_bytes(dval):
    "Use struct.unpack to decode a double precision float into eight bytes"
    tmp = list(struct.unpack('8B',struct.pack('d', dval)))
    if not _big_endian:
        tmp.reverse()
    return tmp

##
## Functions to extract components of the IEEE 754 floating point format
##

def _sign(dval):
    "Extract the sign bit from a double-precision floating point value"
    bb = _double_as_bytes(dval)
    return bb[0] >> 7 & 0x01

def _exponent(dval):
    """Extract the exponentent bits from a double-precision floating
    point value.

    Note that for normalized values, the exponent bits have an offset
    of 1023. As a consequence, the actual exponentent is obtained
    by subtracting 1023 from the value returned by this function
    """
    bb = _double_as_bytes(dval)
    return (bb[0] << 4 | bb[1] >> 4) & 0x7ff

def _mantissa(dval):
    """Extract the _mantissa bits from a double-precision floating
    point value."""

    bb = _double_as_bytes(dval)
    mantissa =  bb[1] & 0x0f << 48
    mantissa += bb[2] << 40
    mantissa += bb[3] << 32
    mantissa += bb[4]
    return mantissa 

def _zero_mantissa(dval):
    """Determine whether the mantissa bits of the given double are all
    zero."""
    bb = _double_as_bytes(dval)
    return ((bb[1] & 0x0f) | reduce(operator.or_, bb[2:])) == 0

##
## Functions to test for IEEE 754 special values
##

def isNaN(value):
    "Determine if the argument is a IEEE 754 NaN (Not a Number) value."
    return (_exponent(value)==0x7ff and not _zero_mantissa(value))

def isInf(value):
    """Determine if the argument is an infinite IEEE 754 value (positive
    or negative inifinity)"""
    return (_exponent(value)==0x7ff and _zero_mantissa(value))

def isFinite(value):
    """Determine if the argument is an finite IEEE 754 value (i.e., is
    not NaN, positive or negative inifinity)"""
    return (_exponent(value)!=0x7ff)

def isPosInf(value):
    "Determine if the argument is a IEEE 754 positive infinity value"
    return (_sign(value)==0 and _exponent(value)==0x7ff and \
            _zero_mantissa(value))

def isNegInf(value):
    "Determine if the argument is a IEEE 754 negative infinity value"
    return (_sign(value)==1 and _exponent(value)==0x7ff and \
            _zero_mantissa(value))

##
## Functions to test public functions.
## 

def test_isNaN():
    assert( not isNaN(PosInf) )
    assert( not isNaN(NegInf) )
    assert(     isNaN(NaN   ) )
    assert( not isNaN(   1.0) )
    assert( not isNaN(  -1.0) )

def test_isInf():
    assert(     isInf(PosInf) )
    assert(     isInf(NegInf) )
    assert( not isInf(NaN   ) )
    assert( not isInf(   1.0) )
    assert( not isInf(  -1.0) )

def test_isFinite():
    assert( not isFinite(PosInf) )
    assert( not isFinite(NegInf) )
    assert( not isFinite(NaN   ) )
    assert(     isFinite(   1.0) )
    assert(     isFinite(  -1.0) )

def test_isPosInf():
    assert(     isPosInf(PosInf) )
    assert( not isPosInf(NegInf) )
    assert( not isPosInf(NaN   ) )
    assert( not isPosInf(   1.0) )
    assert( not isPosInf(  -1.0) )

def test_isNegInf():
    assert( not isNegInf(PosInf) )
    assert(     isNegInf(NegInf) )
    assert( not isNegInf(NaN   ) )
    assert( not isNegInf(   1.0) )
    assert( not isNegInf(  -1.0) )

# overall test
def test():
    test_isNaN()
    test_isInf()
    test_isFinite()
    test_isPosInf()
    test_isNegInf()
    
if __name__ == "__main__":
    test()


########NEW FILE########
__FILENAME__ = ipdiscover
"""
Generic methods to retreive the IP address of the local machine.

TODO: Example

@author: Raphael Slinckx
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""

__revision__ = "$id"

import random, socket, logging, itertools

from twisted.internet import defer, reactor

from twisted.internet.protocol import DatagramProtocol
from twisted.internet.error import CannotListenError

from nattraverso.utils import is_rfc1918_ip, is_bogus_ip

@defer.inlineCallbacks
def get_local_ip():
    """
    Returns a deferred which will be called with a
    2-uple (lan_flag, ip_address) :
        - lan_flag:
            - True if it's a local network (RFC1918)
            - False if it's a WAN address
        
        - ip_address is the actual ip address
    
    @return: A deferred called with the above defined tuple
    @rtype: L{twisted.internet.defer.Deferred}
    """
    # first we try a connected udp socket, then via multicast
    logging.debug("Resolving dns to get udp ip")
    try:
        ipaddr = yield reactor.resolve('A.ROOT-SERVERS.NET')
    except:
        pass
    else:
        udpprot = DatagramProtocol()
        port = reactor.listenUDP(0, udpprot)
        udpprot.transport.connect(ipaddr, 7)
        localip = udpprot.transport.getHost().host
        port.stopListening()
        
        if is_bogus_ip(localip):
            raise RuntimeError, "Invalid IP address returned"
        else:
            defer.returnValue((is_rfc1918_ip(localip), localip))
    
    logging.debug("Multicast ping to retrieve local IP")
    ipaddr = yield _discover_multicast()
    defer.returnValue((is_rfc1918_ip(ipaddr), ipaddr))

@defer.inlineCallbacks
def get_external_ip():
    """
    Returns a deferred which will be called with a
    2-uple (wan_flag, ip_address):
        - wan_flag:
            - True if it's a WAN address
            - False if it's a LAN address
            - None if it's a localhost (127.0.0.1) address
        - ip_address: the most accessible ip address of this machine
    
    @return: A deferred called with the above defined tuple
    @rtype: L{twisted.internet.defer.Deferred}
    """
    
    try:
        local, ipaddr = yield get_local_ip()
    except:
        defer.returnValue((None, "127.0.0.1"))
    if not local:
        defer.returnValue((True, ipaddr))
    logging.debug("Got local ip, trying to use upnp to get WAN ip")
    import nattraverso.pynupnp
    try:
        ipaddr2 = yield nattraverso.pynupnp.get_external_ip()
    except:
        defer.returnValue((False, ipaddr))
    else:
        defer.returnValue((True, ipaddr2))

class _LocalNetworkMulticast(DatagramProtocol):
    def __init__(self, nonce):
        from p2pool.util import variable
        
        self.nonce = nonce
        self.address_received = variable.Event()
    
    def datagramReceived(self, dgram, addr):
        """Datagram received, we callback the IP address."""
        logging.debug("Received multicast pong: %s; addr:%r", dgram, addr)
        if dgram != self.nonce:
            return
        self.address_received.happened(addr[0])

@defer.inlineCallbacks
def _discover_multicast():
    """
    Local IP discovery protocol via multicast:
        - Broadcast 3 ping multicast packet with "ping" in it
        - Wait for an answer
        - Retrieve the ip address from the returning packet, which is ours
    """
    
    nonce = str(random.randrange(2**64))
    p = _LocalNetworkMulticast(nonce)
    
    for attempt in itertools.count():
        port = 11000 + random.randint(0, 5000)
        try:
            mcast = reactor.listenMulticast(port, p)
        except CannotListenError:
            if attempt >= 10:
                raise
            continue
        else:
            break
    
    try:
        yield mcast.joinGroup('239.255.255.250', socket.INADDR_ANY)
        
        logging.debug("Sending multicast ping")
        for i in xrange(3):
            p.transport.write(nonce, ('239.255.255.250', port))
        
        address, = yield p.address_received.get_deferred(5)
    finally:
        mcast.stopListening()
    
    defer.returnValue(address)

########NEW FILE########
__FILENAME__ = portmapper
"""
Generic NAT Port mapping interface.

TODO: Example

@author: Raphael Slinckx
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""

__revision__ = "$id"

from twisted.internet.base import BasePort

# Public API
def get_port_mapper(proto="TCP"):
    """
    Returns a L{NATMapper} instance, suited to map a port for
    the given protocol. Defaults to TCP.
    
    For the moment, only upnp mapper is available. It accepts both UDP and TCP.
    
    @param proto: The protocol: 'TCP' or 'UDP'
    @type proto: string
    @return: A deferred called with a L{NATMapper} instance
    @rtype: L{twisted.internet.defer.Deferred}
    """
    import nattraverso.pynupnp
    return nattraverso.pynupnp.get_port_mapper()

class NATMapper:
    """
    Define methods to map port objects (as returned by twisted's listenXX).
    This allows NAT to be traversed from incoming packets.
    
    Currently the only implementation of this class is the UPnP Mapper, which
    can map UDP and TCP ports, if an UPnP Device exists.
    """
    def __init__(self):
        raise NotImplementedError("Cannot instantiate the class")
    
    def map(self, port):
        """
        Create a mapping for the given twisted's port object.
        
        The deferred will call back with a tuple (extaddr, extport):
            - extaddr: The ip string of the external ip address of this host
            - extport: the external port number used to map the given Port object
        
        When called multiple times with the same Port,
        callback with the existing mapping.
        
        @param port: The port object to map
        @type port: a L{twisted.internet.interfaces.IListeningPort} object
        @return: A deferred called with the above defined tuple
        @rtype: L{twisted.internet.defer.Deferred}
        """
        raise NotImplementedError
    
    def info(self, port):
        """
        Returns the existing mapping for the given port object. That means map()
        has to be called before.
        
        @param port: The port object to retreive info from
        @type port: a L{twisted.internet.interfaces.IListeningPort} object
        @raise ValueError: When there is no such existing mapping
        @return: a tuple (extaddress, extport).
        @see: L{map() function<map>}
        """
        raise NotImplementedError
    
    def unmap(self, port):
        """
        Remove an existing mapping for the given twisted's port object.
        
        @param port: The port object to unmap
        @type port: a L{twisted.internet.interfaces.IListeningPort} object
        @return: A deferred called with None
        @rtype: L{twisted.internet.defer.Deferred}
        @raise ValueError: When there is no such existing mapping
        """
        raise NotImplementedError
    
    def get_port_mappings(self):
        """
        Returns a deferred that will be called with a dictionnary of the
        existing mappings.
        
        The dictionnary structure is the following:
            - Keys: tuple (protocol, external_port)
                - protocol is "TCP" or "UDP".
                - external_port is the external port number, as see on the
                    WAN side.
            - Values:tuple (internal_ip, internal_port)
                - internal_ip is the LAN ip address of the host.
                - internal_port is the internal port number mapped
                    to external_port.
        
        @return: A deferred called with the above defined dictionnary
        @rtype: L{twisted.internet.defer.Deferred}
        """
        raise NotImplementedError
    
    def _check_valid_port(self, port):
        """Various Port object validity checks. Raise a ValueError."""
        if not isinstance(port, BasePort):
            raise ValueError("expected a Port, got %r"%(port))
        
        if not port.connected:
            raise ValueError("Port %r is not listening"%(port))
        
        loc_addr = port.getHost()
        if loc_addr.port == 0:
            raise ValueError("Port %r has port number of 0"%(port))


########NEW FILE########
__FILENAME__ = soap
"""
This module is a SOAP client using twisted's deferreds.
It uses the SOAPpy package.

@author: Raphael Slinckx
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""

__revision__ = "$id"

import SOAPpy, logging
from SOAPpy.Config import Config
from twisted.web import client, error

#General config
Config.typed = False

class SoapError(Exception):
    """
    This is a SOAP error message, not an HTTP error message.
    
    The content of this error is a SOAPpy structure representing the
    SOAP error message.
    """
    pass

class SoapProxy:
    """
    Proxy for an url to which we send SOAP rpc calls.
    """
    def __init__(self, url, prefix):
        """
        Init the proxy, it will connect to the given url, using the
        given soap namespace.
        
        @param url: The url of the remote host to call
        @param prefix: The namespace prefix to use, eg.
            'urn:schemas-upnp-org:service:WANIPConnection:1'
        """
        logging.debug("Soap Proxy: '%s', prefix: '%s'", url, prefix)
        self._url = url
        self._prefix = prefix
    
    def call(self, method, **kwargs):
        """
        Call the given remote method with the given arguments, as keywords.
        
        Returns a deferred, called with SOAPpy structure representing
        the soap response.
        
        @param method: The method name to call, eg. 'GetExternalIP'
        @param kwargs: The parameters of the call, as keywords
        @return: A deferred called with the external ip address of this host
        @rtype: L{twisted.internet.defer.Deferred}
        """
        payload = SOAPpy.buildSOAP(method=method, config=Config, namespace=self._prefix, kw=kwargs)
        # Here begins the nasty hack
        payload = payload.replace(
            # Upnp wants s: instead of SOAP-ENV
            'SOAP-ENV','s').replace(
            # Doesn't seem to like these encoding stuff
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"', '').replace(
            'SOAP-ENC:root="1"', '').replace(
            # And it wants u: instead of ns1 namespace for arguments..
            'ns1','u')
        
        logging.debug("SOAP Payload:\n%s", payload)
        
        return client.getPage(self._url, postdata=payload, method="POST",
            headers={'content-type': 'text/xml',        'SOAPACTION': '%s#%s' % (self._prefix, method)}
    ).addCallbacks(self._got_page, self._got_error)
    
    def _got_page(self, result):
        """
        The http POST command was successful, we parse the SOAP
        answer, and return it.
        
        @param result: the xml content
        """
        parsed = SOAPpy.parseSOAPRPC(result)
        
        logging.debug("SOAP Answer:\n%s", result)
        logging.debug("SOAP Parsed Answer: %r", parsed)
        
        return parsed
    
    def _got_error(self, res):
        """
        The HTTP POST command did not succeed, depending on the error type:
            - it's a SOAP error, we parse it and return a L{SoapError}.
            - it's another type of error (http, other), we raise it as is
        """
        logging.debug("SOAP Error:\n%s", res)
        
        if isinstance(res.value, error.Error):
            try:
                logging.debug("SOAP Error content:\n%s", res.value.response)
                raise SoapError(SOAPpy.parseSOAPRPC(res.value.response)["detail"])
            except:
                raise
        raise Exception(res.value)

########NEW FILE########
__FILENAME__ = upnp
"""
This module is the heart of the upnp support. Device discover, ip discovery
and port mappings are implemented here.

@author: Raphael Slinckx
@author: Anthony Baxter
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""
__revision__ = "$id"

import socket, random, urlparse, logging

from twisted.internet import reactor, defer
from twisted.web import client
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.error import CannotListenError
from twisted.python import failure

from nattraverso.pynupnp.soap import SoapProxy
from nattraverso.pynupnp.upnpxml import UPnPXml
from nattraverso import ipdiscover, portmapper

class UPnPError(Exception):
    """
    A generic UPnP error, with a descriptive message as content.
    """
    pass

class UPnPMapper(portmapper.NATMapper):
    """
    This is the UPnP port mapper implementing the
    L{NATMapper<portmapper.NATMapper>} interface.
    
    @see: L{NATMapper<portmapper.NATMapper>}
    """
    
    def __init__(self, upnp):
        """
        Creates the mapper, with the given L{UPnPDevice} instance.
        
        @param upnp: L{UPnPDevice} instance
        """
        self._mapped = {}
        self._upnp = upnp
    
    def map(self, port):
        """
        See interface
        """
        self._check_valid_port(port)
        
        #Port is already mapped
        if port in self._mapped:
            return defer.succeed(self._mapped[port])
        
        #Trigger a new mapping creation, first fetch local ip.
        result = ipdiscover.get_local_ip()
        self._mapped[port] = result
        return result.addCallback(self._map_got_local_ip, port)
    
    def info(self, port):
        """
        See interface
        """
        # If the mapping exists, everything's ok
        if port in self._mapped:
            return self._mapped[port]
        else:
            raise ValueError('Port %r is not currently mapped'%(port))
    
    def unmap(self, port):
        """
        See interface
        """
        if port in self._mapped:
            existing = self._mapped[port]
            
            #Pending mapping, queue an unmap,return existing deferred
            if type(existing) is not tuple:
                existing.addCallback(lambda x: self.unmap(port))
                return existing
            
            #Remove our local mapping
            del self._mapped[port]
            
            #Ask the UPnP to remove the mapping
            extaddr, extport = existing
            return self._upnp.remove_port_mapping(extport, port.getHost().type)
        else:
            raise ValueError('Port %r is not currently mapped'%(port))
    
    def get_port_mappings(self):
        """
        See interface
        """
        return self._upnp.get_port_mappings()
    
    def _map_got_local_ip(self, ip_result, port):
        """
        We got the local ip address, retreive the existing port mappings
        in the device.
        
        @param ip_result: result of L{ipdiscover.get_local_ip}
        @param port: a L{twisted.internet.interfaces.IListeningPort} we
            want to map
        """
        local, ip = ip_result
        return self._upnp.get_port_mappings().addCallback(
            self._map_got_port_mappings, ip, port)
    
    def _map_got_port_mappings(self, mappings, ip, port):
        """
        We got all the existing mappings in the device, find an unused one
        and assign it for the requested port.
        
        @param ip: The local ip of this host "x.x.x.x"
        @param port: a L{twisted.internet.interfaces.IListeningPort} we
            want to map
        @param mappings: result of L{UPnPDevice.get_port_mappings}
        """
        
        #Get the requested mapping's info
        ptype = port.getHost().type
        intport = port.getHost().port
        
        for extport in [random.randrange(1025, 65536) for val in range(20)]:
            # Check if there is an existing mapping, if it does not exist, bingo
            if not (ptype, extport) in mappings:
                break
            
            if (ptype, extport) in mappings:
                existing = mappings[ptype, extport]
            
            local_ip, local_port = existing
            if local_ip == ip and local_port == intport:
                # Existing binding for this host/port/proto - replace it
                break
        
        # Triggers the creation of the mapping on the device
        result = self._upnp.add_port_mapping(ip, intport, extport, 'pynupnp', ptype)
        
        # We also need the external IP, so we queue first an
        # External IP Discovery, then we add the mapping.
        return result.addCallback(
            lambda x: self._upnp.get_external_ip()).addCallback(
                self._port_mapping_added, extport, port)
    
    def _port_mapping_added(self, extaddr, extport, port):
        """
        The port mapping was added in the device, this means::
            
            Internet        NAT         LAN
                |
        > IP:extaddr       |>       IP:local ip
            > Port:extport     |>       Port:port
                |
        
        @param extaddr: The exernal ip address
        @param extport: The external port as number
        @param port: The internal port as a
            L{twisted.internet.interfaces.IListeningPort} object, that has been
            mapped
        """
        self._mapped[port] = (extaddr, extport)
        return (extaddr, extport)

class UPnPDevice:
    """
    Represents an UPnP device, with the associated infos, and remote methods.
    """
    def __init__(self, soap_proxy, info):
        """
        Build the device, with the given SOAP proxy, and the meta-infos.
        
        @param soap_proxy: an initialized L{SoapProxy} to the device
        @param info: a dictionnary of various infos concerning the
            device extracted with L{UPnPXml}
        """
        self._soap_proxy = soap_proxy
        self._info = info
    
    def get_external_ip(self):
        """
        Triggers an external ip discovery on the upnp device. Returns
        a deferred called with the external ip of this host.
        
        @return: A deferred called with the ip address, as "x.x.x.x"
        @rtype: L{twisted.internet.defer.Deferred}
        """
        result = self._soap_proxy.call('GetExternalIPAddress')
        result.addCallback(self._on_external_ip)
        return result
    
    def get_port_mappings(self):
        """
        Retreive the existing port mappings
        
        @see: L{portmapper.NATMapper.get_port_mappings}
        @return: A deferred called with the dictionnary as defined
            in the interface L{portmapper.NATMapper.get_port_mappings}
        @rtype: L{twisted.internet.defer.Deferred}
        """
        return self._get_port_mapping()
    
    def add_port_mapping(self, local_ip, intport, extport, desc, proto, lease=0):
        """
        Add a port mapping in the upnp device. Returns a deferred.
        
        @param local_ip: the LAN ip of this host as "x.x.x.x"
        @param intport: the internal port number
        @param extport: the external port number
        @param desc: the description of this mapping (string)
        @param proto: "UDP" or "TCP"
        @param lease: The duration of the lease in (mili)seconds(??)
        @return: A deferred called with None when the mapping is done
        @rtype: L{twisted.internet.defer.Deferred}
        """
        result = self._soap_proxy.call('AddPortMapping', NewRemoteHost="",
            NewExternalPort=extport,
            NewProtocol=proto,
            NewInternalPort=intport,
            NewInternalClient=local_ip,
            NewEnabled=1,
            NewPortMappingDescription=desc,
            NewLeaseDuration=lease)
        
        return result.addCallbacks(self._on_port_mapping_added,
            self._on_no_port_mapping_added)
    
    def remove_port_mapping(self, extport, proto):
        """
        Remove an existing port mapping on the device. Returns a deferred
        
        @param extport: the external port number associated to the mapping
            to be removed
        @param proto: either "UDP" or "TCP"
        @return: A deferred called with None when the mapping is done
        @rtype: L{twisted.internet.defer.Deferred}
        """
        result = self._soap_proxy.call('DeletePortMapping', NewRemoteHost="",
            NewExternalPort=extport,
            NewProtocol=proto)
        
        return result.addCallbacks(self._on_port_mapping_removed,
            self._on_no_port_mapping_removed)
    
    # Private --------
    def _on_external_ip(self, res):
        """
        Called when we received the external ip address from the device.
        
        @param res: the SOAPpy structure of the result
        @return: the external ip string, as "x.x.x.x"
        """
        logging.debug("Got external ip struct: %r", res)
        return res['NewExternalIPAddress']
    
    def _get_port_mapping(self, mapping_id=0, mappings=None):
        """
        Fetch the existing mappings starting at index
        "mapping_id" from the device.
        
        To retreive all the mappings call this without parameters.
        
        @param mapping_id: The index of the mapping to start fetching from
        @param mappings: the dictionnary of already fetched mappings
        @return: A deferred called with the existing mappings when all have been
            retreived, see L{get_port_mappings}
        @rtype: L{twisted.internet.defer.Deferred}
        """
        if mappings == None:
            mappings = {}
        
        result = self._soap_proxy.call('GetGenericPortMappingEntry',
            NewPortMappingIndex=mapping_id)
        return result.addCallbacks(
            lambda x: self._on_port_mapping_received(x, mapping_id+1, mappings),
            lambda x: self._on_no_port_mapping_received(        x, mappings))
    
    def _on_port_mapping_received(self, response, mapping_id, mappings):
        """
        Called we we receive a single mapping from the device.
        
        @param response: a SOAPpy structure, representing the device's answer
        @param mapping_id: The index of the next mapping in the device
        @param mappings: the already fetched mappings, see L{get_port_mappings}
        @return: A deferred called with the existing mappings when all have been
            retreived, see L{get_port_mappings}
        @rtype: L{twisted.internet.defer.Deferred}
        """
        logging.debug("Got mapping struct: %r", response)
        mappings[
            response['NewProtocol'], response['NewExternalPort']
        ] = (response['NewInternalClient'], response['NewInternalPort'])
        return self._get_port_mapping(mapping_id, mappings)
    
    def _on_no_port_mapping_received(self, failure, mappings):
        """
        Called when we have no more port mappings to retreive, or an
        error occured while retreiving them.
        
        Either we have a "SpecifiedArrayIndexInvalid" SOAP error, and that's ok,
        it just means we have finished. If it returns some other error, then we
        fail with an UPnPError.
        
        @param mappings: the already retreived mappings
        @param failure: the failure
        @return: The existing mappings as defined in L{get_port_mappings}
        @raise UPnPError: When we got any other error
            than "SpecifiedArrayIndexInvalid"
        """
        logging.debug("_on_no_port_mapping_received: %s", failure)
        err = failure.value
        message = err.args[0]["UPnPError"]["errorDescription"]
        if "SpecifiedArrayIndexInvalid" == message:
            return mappings
        else:
            return failure
    
    
    def _on_port_mapping_added(self, response):
        """
        The port mapping was successfully added, return None to the deferred.
        """
        return None
    
    def _on_no_port_mapping_added(self, failure):
        """
        Called when the port mapping could not be added. Immediately
        raise an UPnPError, with the SOAPpy structure inside.
        
        @raise UPnPError: When the port mapping could not be added
        """
        return failure
    
    def _on_port_mapping_removed(self, response):
        """
        The port mapping was successfully removed, return None to the deferred.
        """
        return None
    
    def _on_no_port_mapping_removed(self, failure):
        """
        Called when the port mapping could not be removed. Immediately
        raise an UPnPError, with the SOAPpy structure inside.
        
        @raise UPnPError: When the port mapping could not be deleted
        """
        return failure

# UPNP multicast address, port and request string
_UPNP_MCAST = '239.255.255.250'
_UPNP_PORT = 1900
_UPNP_SEARCH_REQUEST = """M-SEARCH * HTTP/1.1\r
Host:%s:%s\r
ST:urn:schemas-upnp-org:device:InternetGatewayDevice:1\r
Man:"ssdp:discover"\r
MX:3\r
\r
""" % (_UPNP_MCAST, _UPNP_PORT)

class UPnPProtocol(DatagramProtocol, object):
    """
    The UPnP Device discovery udp multicast twisted protocol.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Init the protocol, no parameters needed.
        """
        super(UPnPProtocol, self).__init__(*args, **kwargs)
        
        #Device discovery deferred
        self._discovery = None
        self._discovery_timeout = None
        self.mcast = None
        self._done = False
    
    # Public methods
    def search_device(self):
        """
        Triggers a UPnP device discovery.
        
        The returned deferred will be called with the L{UPnPDevice} that has
        been found in the LAN.
        
        @return: A deferred called with the detected L{UPnPDevice} instance.
        @rtype: L{twisted.internet.defer.Deferred}
        """
        if self._discovery is not None:
            raise ValueError('already used')
        self._discovery = defer.Deferred()
        self._discovery_timeout = reactor.callLater(6, self._on_discovery_timeout)
        
        attempt = 0
        mcast = None
        while True:
            try:
                self.mcast = reactor.listenMulticast(1900+attempt, self)
                break
            except CannotListenError:
                attempt = random.randint(0, 500)
        
        # joined multicast group, starting upnp search
        self.mcast.joinGroup('239.255.255.250', socket.INADDR_ANY)
        
        self.transport.write(_UPNP_SEARCH_REQUEST, (_UPNP_MCAST, _UPNP_PORT))
        self.transport.write(_UPNP_SEARCH_REQUEST, (_UPNP_MCAST, _UPNP_PORT))
        self.transport.write(_UPNP_SEARCH_REQUEST, (_UPNP_MCAST, _UPNP_PORT))
        
        return self._discovery
    
    #Private methods
    def datagramReceived(self, dgram, address):
        if self._done:
            return
        """
        This is private, handle the multicast answer from the upnp device.
        """
        logging.debug("Got UPNP multicast search answer:\n%s", dgram)
        
        #This is an HTTP response
        response, message = dgram.split('\r\n', 1)
        
        # Prepare status line
        version, status, textstatus = response.split(None, 2)
        
        if not version.startswith('HTTP'):
            return
        if status != "200":
            return
        
        # Launch the info fetching
        def parse_discovery_response(message):
            """Separate headers and body from the received http answer."""
            hdict = {}
            body = ''
            remaining = message
            while remaining:
                line, remaining = remaining.split('\r\n', 1)
                line = line.strip()
                if not line:
                    body = remaining
                    break
                key, val = line.split(':', 1)
                key = key.lower()
                hdict.setdefault(key, []).append(val.strip())
            return hdict, body
        
        headers, body = parse_discovery_response(message)
        
        if not 'location' in headers:
            self._on_discovery_failed(
                UPnPError(
                    "No location header in response to M-SEARCH!: %r"%headers))
            return
        
        loc = headers['location'][0]
        result = client.getPage(url=loc)
        result.addCallback(self._on_gateway_response, loc).addErrback(self._on_discovery_failed)
    
    def _on_gateway_response(self, body, loc):
        if self._done:
            return
        """
        Called with the UPnP device XML description fetched via HTTP.
        
        If the device has suitable services for ip discovery and port mappings,
        the callback returned in L{search_device} is called with
        the discovered L{UPnPDevice}.
        
        @raise UPnPError: When no suitable service has been
            found in the description, or another error occurs.
        @param body: The xml description of the device.
        @param loc: the url used to retreive the xml description
        """
        
        # Parse answer
        upnpinfo = UPnPXml(body)
        
        # Check if we have a base url, if not consider location as base url
        urlbase = upnpinfo.urlbase
        if urlbase == None:
            urlbase = loc
        
        # Check the control url, if None, then the device cannot do what we want
        controlurl = upnpinfo.controlurl
        if controlurl == None:
            self._on_discovery_failed(UPnPError("upnp response showed no WANConnections"))
            return
        
        control_url2 = urlparse.urljoin(urlbase, controlurl)
        soap_proxy = SoapProxy(control_url2, upnpinfo.wanservice)
        self._on_discovery_succeeded(UPnPDevice(soap_proxy, upnpinfo.deviceinfos))
    
    def _on_discovery_succeeded(self, res):
        if self._done:
            return
        self._done = True
        self.mcast.stopListening()
        self._discovery_timeout.cancel()
        self._discovery.callback(res)
    
    def _on_discovery_failed(self, err):
        if self._done:
            return
        self._done = True
        self.mcast.stopListening()
        self._discovery_timeout.cancel()
        self._discovery.errback(err)
    
    def _on_discovery_timeout(self):
        if self._done:
            return
        self._done = True
        self.mcast.stopListening()
        self._discovery.errback(failure.Failure(defer.TimeoutError('in _on_discovery_timeout')))

def search_upnp_device ():
    """
    Check the network for an UPnP device. Returns a deferred
    with the L{UPnPDevice} instance as result, if found.
    
    @return: A deferred called with the L{UPnPDevice} instance
    @rtype: L{twisted.internet.defer.Deferred}
    """
    return defer.maybeDeferred(UPnPProtocol().search_device)

########NEW FILE########
__FILENAME__ = upnpxml
"""
This module parse an UPnP device's XML definition in an Object.

@author: Raphael Slinckx
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""

__revision__ = "$id"

from xml.dom import minidom
import logging

# Allowed UPnP services to use when mapping ports/external addresses
WANSERVICES = ['urn:schemas-upnp-org:service:WANIPConnection:1',
    'urn:schemas-upnp-org:service:WANPPPConnection:1']

class UPnPXml:
    """
    This objects parses the XML definition, and stores the useful
    results in attributes.
    
    The device infos dictionnary may contain the following keys:
        - friendlyname: A friendly name to call the device.
        - manufacturer: A manufacturer name for the device.
    
    Here are the different attributes:
        - deviceinfos: A dictionnary of device infos as defined above.
        - controlurl: The control url, this is the url to use when sending SOAP
            requests to the device, relative to the base url.
        - wanservice: The WAN service to be used, one of the L{WANSERVICES}
        - urlbase: The base url to use when talking in SOAP to the device.
    
    The full url to use is obtained by urljoin(urlbase, controlurl)
    """
    
    def __init__(self, xml):
        """
        Parse the given XML string for UPnP infos. This creates the attributes
        when they are found, or None if no value was found.
        
        @param xml: a xml string to parse
        """
        logging.debug("Got UPNP Xml description:\n%s", xml)
        doc = minidom.parseString(xml)
        
        # Fetch various device info
        self.deviceinfos = {}
        try:
            attributes = {
                'friendlyname':'friendlyName',
                'manufacturer' : 'manufacturer'
            }
            device = doc.getElementsByTagName('device')[0]
            for name, tag in attributes.iteritems():
                try:
                    self.deviceinfos[name] = device.getElementsByTagName(
                        tag)[0].firstChild.datas.encode('utf-8')
                except:
                    pass
        except:
            pass
        
        # Fetch device control url
        self.controlurl = None
        self.wanservice = None
        
        for service in doc.getElementsByTagName('service'):
            try:
                stype = service.getElementsByTagName(
                    'serviceType')[0].firstChild.data.encode('utf-8')
                if stype in WANSERVICES:
                    self.controlurl = service.getElementsByTagName(
                        'controlURL')[0].firstChild.data.encode('utf-8')
                    self.wanservice = stype
                    break
            except:
                pass
        
        # Find base url
        self.urlbase = None
        try:
            self.urlbase = doc.getElementsByTagName(
                'URLBase')[0].firstChild.data.encode('utf-8')
        except:
            pass


########NEW FILE########
__FILENAME__ = utils
"""
Various utility functions used in the nattraverso package.

@author: Raphael Slinckx
@copyright: Copyright 2005
@license: LGPL
@contact: U{raphael@slinckx.net<mailto:raphael@slinckx.net>}
@version: 0.1.0
"""
__revision__ = "$id"

def is_rfc1918_ip(ip):
    """
    Checks if the given ip address is a rfc1918 one.
    
    @param ip: The ip address to test
    @type ip: a string "x.x.x.x"
    @return: True if it's a LAN address, False otherwise
    """
    if isinstance(ip, basestring):
        ip = _ip_to_number(ip)
    
    for net, mask in _nets:
        if ip&mask == net:
            return True
    
    return False

def is_bogus_ip(ip):
    """
    Checks if the given ip address is bogus, i.e. 0.0.0.0 or 127.0.0.1.
    
    @param ip: The ip address to test
    @type ip: a string "x.x.x.x"
    @return: True if it's bogus, False otherwise
    """
    return ip.startswith('0.') or ip.startswith('127.')

def _ip_to_number(ipstr):
    """
    Translate a string ip address to a packed number.
    
    @param ipstr: the ip address to transform
    @type ipstr: a string "x.x.x.x"
    @return: an int32 number representing the ip address
    """
    net = [ int(digit) for digit in ipstr.split('.') ] + [ 0, 0, 0 ]
    net = net[:4]
    return  ((((((0L+net[0])<<8) + net[1])<<8) + net[2])<<8) +net[3]

# List of rfc1918 net/mask
_rfc1918_networks = [('127', 8), ('192.168', 16), ('10', 8), ('172.16', 12)]
# Machine readable form of the above
_nets = [(_ip_to_number(net), (2L**32 -1)^(2L**(32-mask)-1))
    for net, mask in _rfc1918_networks]


########NEW FILE########
__FILENAME__ = data
from __future__ import division

import hashlib
import random
import warnings

import p2pool
from p2pool.util import math, pack

def hash256(data):
    return pack.IntType(256).unpack(hashlib.sha256(hashlib.sha256(data).digest()).digest())

def hash160(data):
    if data == '04ffd03de44a6e11b9917f3a29f9443283d9871c9d743ef30d5eddcd37094b64d1b3d8090496b53256786bf5c82932ec23c3b74d9f05a6f95a8b5529352656664b'.decode('hex'):
        return 0x384f570ccc88ac2e7e00b026d1690a3fca63dd0 # hack for people who don't have openssl - this is the only value that p2pool ever hashes
    return pack.IntType(160).unpack(hashlib.new('ripemd160', hashlib.sha256(data).digest()).digest())

class ChecksummedType(pack.Type):
    def __init__(self, inner, checksum_func=lambda data: hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]):
        self.inner = inner
        self.checksum_func = checksum_func
    
    def read(self, file):
        obj, file = self.inner.read(file)
        data = self.inner.pack(obj)
        
        calculated_checksum = self.checksum_func(data)
        checksum, file = pack.read(file, len(calculated_checksum))
        if checksum != calculated_checksum:
            raise ValueError('invalid checksum')
        
        return obj, file
    
    def write(self, file, item):
        data = self.inner.pack(item)
        return (file, data), self.checksum_func(data)

class FloatingInteger(object):
    __slots__ = ['bits', '_target']
    
    @classmethod
    def from_target_upper_bound(cls, target):
        n = math.natural_to_string(target)
        if n and ord(n[0]) >= 128:
            n = '\x00' + n
        bits2 = (chr(len(n)) + (n + 3*chr(0))[:3])[::-1]
        bits = pack.IntType(32).unpack(bits2)
        return cls(bits)
    
    def __init__(self, bits, target=None):
        self.bits = bits
        self._target = None
        if target is not None and self.target != target:
            raise ValueError('target does not match')
    
    @property
    def target(self):
        res = self._target
        if res is None:
            res = self._target = math.shift_left(self.bits & 0x00ffffff, 8 * ((self.bits >> 24) - 3))
        return res
    
    def __hash__(self):
        return hash(self.bits)
    
    def __eq__(self, other):
        return self.bits == other.bits
    
    def __ne__(self, other):
        return not (self == other)
    
    def __cmp__(self, other):
        assert False
    
    def __repr__(self):
        return 'FloatingInteger(bits=%s, target=%s)' % (hex(self.bits), hex(self.target))

class FloatingIntegerType(pack.Type):
    _inner = pack.IntType(32)
    
    def read(self, file):
        bits, file = self._inner.read(file)
        return FloatingInteger(bits), file
    
    def write(self, file, item):
        return self._inner.write(file, item.bits)

address_type = pack.ComposedType([
    ('services', pack.IntType(64)),
    ('address', pack.IPV6AddressType()),
    ('port', pack.IntType(16, 'big')),
])

tx_type = pack.ComposedType([
    ('version', pack.IntType(32)),
    ('tx_ins', pack.ListType(pack.ComposedType([
        ('previous_output', pack.PossiblyNoneType(dict(hash=0, index=2**32 - 1), pack.ComposedType([
            ('hash', pack.IntType(256)),
            ('index', pack.IntType(32)),
        ]))),
        ('script', pack.VarStrType()),
        ('sequence', pack.PossiblyNoneType(2**32 - 1, pack.IntType(32))),
    ]))),
    ('tx_outs', pack.ListType(pack.ComposedType([
        ('value', pack.IntType(64)),
        ('script', pack.VarStrType()),
    ]))),
    ('lock_time', pack.IntType(32)),
])

merkle_link_type = pack.ComposedType([
    ('branch', pack.ListType(pack.IntType(256))),
    ('index', pack.IntType(32)),
])

merkle_tx_type = pack.ComposedType([
    ('tx', tx_type),
    ('block_hash', pack.IntType(256)),
    ('merkle_link', merkle_link_type),
])

block_header_type = pack.ComposedType([
    ('version', pack.IntType(32)),
    ('previous_block', pack.PossiblyNoneType(0, pack.IntType(256))),
    ('merkle_root', pack.IntType(256)),
    ('timestamp', pack.IntType(32)),
    ('bits', FloatingIntegerType()),
    ('nonce', pack.IntType(32)),
])

block_type = pack.ComposedType([
    ('header', block_header_type),
    ('txs', pack.ListType(tx_type)),
])

# merged mining

aux_pow_type = pack.ComposedType([
    ('merkle_tx', merkle_tx_type),
    ('merkle_link', merkle_link_type),
    ('parent_block_header', block_header_type),
])

aux_pow_coinbase_type = pack.ComposedType([
    ('merkle_root', pack.IntType(256, 'big')),
    ('size', pack.IntType(32)),
    ('nonce', pack.IntType(32)),
])

def make_auxpow_tree(chain_ids):
    for size in (2**i for i in xrange(31)):
        if size < len(chain_ids):
            continue
        res = {}
        for chain_id in chain_ids:
            pos = (1103515245 * chain_id + 1103515245 * 12345 + 12345) % size
            if pos in res:
                break
            res[pos] = chain_id
        else:
            return res, size
    raise AssertionError()

# merkle trees

merkle_record_type = pack.ComposedType([
    ('left', pack.IntType(256)),
    ('right', pack.IntType(256)),
])

def merkle_hash(hashes):
    if not hashes:
        return 0
    hash_list = list(hashes)
    while len(hash_list) > 1:
        hash_list = [hash256(merkle_record_type.pack(dict(left=left, right=right)))
            for left, right in zip(hash_list[::2], hash_list[1::2] + [hash_list[::2][-1]])]
    return hash_list[0]

def calculate_merkle_link(hashes, index):
    # XXX optimize this
    
    hash_list = [(lambda _h=h: _h, i == index, []) for i, h in enumerate(hashes)]
    
    while len(hash_list) > 1:
        hash_list = [
            (
                lambda _left=left, _right=right: hash256(merkle_record_type.pack(dict(left=_left(), right=_right()))),
                left_f or right_f,
                (left_l if left_f else right_l) + [dict(side=1, hash=right) if left_f else dict(side=0, hash=left)],
            )
            for (left, left_f, left_l), (right, right_f, right_l) in
                zip(hash_list[::2], hash_list[1::2] + [hash_list[::2][-1]])
        ]
    
    res = [x['hash']() for x in hash_list[0][2]]
    
    assert hash_list[0][1]
    if p2pool.DEBUG:
        new_hashes = [random.randrange(2**256) if x is None else x
            for x in hashes]
        assert check_merkle_link(new_hashes[index], dict(branch=res, index=index)) == merkle_hash(new_hashes)
    assert index == sum(k*2**i for i, k in enumerate([1-x['side'] for x in hash_list[0][2]]))
    
    return dict(branch=res, index=index)

def check_merkle_link(tip_hash, link):
    if link['index'] >= 2**len(link['branch']):
        raise ValueError('index too large')
    return reduce(lambda c, (i, h): hash256(merkle_record_type.pack(
        dict(left=h, right=c) if (link['index'] >> i) & 1 else
        dict(left=c, right=h)
    )), enumerate(link['branch']), tip_hash)

# targets

def target_to_average_attempts(target):
    assert 0 <= target and isinstance(target, (int, long)), target
    if target >= 2**256: warnings.warn('target >= 2**256!')
    return 2**256//(target + 1)

def average_attempts_to_target(average_attempts):
    assert average_attempts > 0
    return min(int(2**256/average_attempts - 1 + 0.5), 2**256-1)

def target_to_difficulty(target):
    assert 0 <= target and isinstance(target, (int, long)), target
    if target >= 2**256: warnings.warn('target >= 2**256!')
    return (0xffff0000 * 2**(256-64) + 1)/(target + 1)

def difficulty_to_target(difficulty):
    assert difficulty >= 0
    if difficulty == 0: return 2**256-1
    return min(int((0xffff0000 * 2**(256-64) + 1)/difficulty - 1 + 0.5), 2**256-1)

# human addresses

base58_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(bindata):
    bindata2 = bindata.lstrip(chr(0))
    return base58_alphabet[0]*(len(bindata) - len(bindata2)) + math.natural_to_string(math.string_to_natural(bindata2), base58_alphabet)

def base58_decode(b58data):
    b58data2 = b58data.lstrip(base58_alphabet[0])
    return chr(0)*(len(b58data) - len(b58data2)) + math.natural_to_string(math.string_to_natural(b58data2, base58_alphabet))

human_address_type = ChecksummedType(pack.ComposedType([
    ('version', pack.IntType(8)),
    ('pubkey_hash', pack.IntType(160)),
]))

def pubkey_hash_to_address(pubkey_hash, net):
    return base58_encode(human_address_type.pack(dict(version=net.ADDRESS_VERSION, pubkey_hash=pubkey_hash)))

def pubkey_to_address(pubkey, net):
    return pubkey_hash_to_address(hash160(pubkey), net)

def address_to_pubkey_hash(address, net):
    x = human_address_type.unpack(base58_decode(address))
    if x['version'] != net.ADDRESS_VERSION:
        raise ValueError('address not for this net!')
    return x['pubkey_hash']

# transactions

def pubkey_to_script2(pubkey):
    assert len(pubkey) <= 75
    return (chr(len(pubkey)) + pubkey) + '\xac'

def pubkey_hash_to_script2(pubkey_hash):
    return '\x76\xa9' + ('\x14' + pack.IntType(160).pack(pubkey_hash)) + '\x88\xac'

def script2_to_address(script2, net):
    try:
        pubkey = script2[1:-1]
        script2_test = pubkey_to_script2(pubkey)
    except:
        pass
    else:
        if script2_test == script2:
            return pubkey_to_address(pubkey, net)
    
    try:
        pubkey_hash = pack.IntType(160).unpack(script2[3:-2])
        script2_test2 = pubkey_hash_to_script2(pubkey_hash)
    except:
        pass
    else:
        if script2_test2 == script2:
            return pubkey_hash_to_address(pubkey_hash, net)

def script2_to_human(script2, net):
    try:
        pubkey = script2[1:-1]
        script2_test = pubkey_to_script2(pubkey)
    except:
        pass
    else:
        if script2_test == script2:
            return 'Pubkey. Address: %s' % (pubkey_to_address(pubkey, net),)
    
    try:
        pubkey_hash = pack.IntType(160).unpack(script2[3:-2])
        script2_test2 = pubkey_hash_to_script2(pubkey_hash)
    except:
        pass
    else:
        if script2_test2 == script2:
            return 'Address. Address: %s' % (pubkey_hash_to_address(pubkey_hash, net),)
    
    return 'Unknown. Script: %s'  % (script2.encode('hex'),)

########NEW FILE########
__FILENAME__ = getwork
'''
Representation of a getwork request/reply
'''

from __future__ import division

from . import data as bitcoin_data
from . import sha256
from p2pool.util import pack

def _swap4(s):
    if len(s) % 4:
        raise ValueError()
    return ''.join(s[x:x+4][::-1] for x in xrange(0, len(s), 4))

class BlockAttempt(object):
    def __init__(self, version, previous_block, merkle_root, timestamp, bits, share_target):
        self.version, self.previous_block, self.merkle_root, self.timestamp, self.bits, self.share_target = version, previous_block, merkle_root, timestamp, bits, share_target
    
    def __hash__(self):
        return hash((self.version, self.previous_block, self.merkle_root, self.timestamp, self.bits, self.share_target))
    
    def __eq__(self, other):
        if not isinstance(other, BlockAttempt):
            raise ValueError('comparisons only valid with other BlockAttempts')
        return self.__dict__ == other.__dict__
    
    def __ne__(self, other):
        return not (self == other)
    
    def __repr__(self):
        return 'BlockAttempt(%s)' % (', '.join('%s=%r' % (k, v) for k, v in self.__dict__.iteritems()),)
    
    def getwork(self, **extra):
        if 'data' in extra or 'hash1' in extra or 'target' in extra or 'midstate' in extra:
            raise ValueError()
        
        block_data = bitcoin_data.block_header_type.pack(dict(
            version=self.version,
            previous_block=self.previous_block,
            merkle_root=self.merkle_root,
            timestamp=self.timestamp,
            bits=self.bits,
            nonce=0,
        ))
        
        getwork = {
            'data': _swap4(block_data).encode('hex') + '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000',
            'hash1': '00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000',
            'target': pack.IntType(256).pack(self.share_target).encode('hex'),
            'midstate': _swap4(sha256.process(sha256.initial_state, block_data[:64])).encode('hex'),
        }
        
        getwork = dict(getwork)
        getwork.update(extra)
        
        return getwork
    
    @classmethod
    def from_getwork(cls, getwork):
        attrs = decode_data(getwork['data'])
        
        return cls(
            version=attrs['version'],
            previous_block=attrs['previous_block'],
            merkle_root=attrs['merkle_root'],
            timestamp=attrs['timestamp'],
            bits=attrs['bits'],
            share_target=pack.IntType(256).unpack(getwork['target'].decode('hex')),
        )
    
    def update(self, **kwargs):
        d = self.__dict__.copy()
        d.update(kwargs)
        return self.__class__(**d)

def decode_data(data):
    return bitcoin_data.block_header_type.unpack(_swap4(data.decode('hex'))[:80])

########NEW FILE########
__FILENAME__ = height_tracker
from twisted.internet import defer
from twisted.python import log

import p2pool
from p2pool.bitcoin import data as bitcoin_data
from p2pool.util import deferral, forest, jsonrpc, variable

class HeaderWrapper(object):
    __slots__ = 'hash previous_hash'.split(' ')
    
    @classmethod
    def from_header(cls, header):
        return cls(bitcoin_data.hash256(bitcoin_data.block_header_type.pack(header)), header['previous_block'])
    
    def __init__(self, hash, previous_hash):
        self.hash, self.previous_hash = hash, previous_hash

class HeightTracker(object):
    '''Point this at a factory and let it take care of getting block heights'''
    
    def __init__(self, best_block_func, factory, backlog_needed):
        self._best_block_func = best_block_func
        self._factory = factory
        self._backlog_needed = backlog_needed
        
        self._tracker = forest.Tracker()
        
        self._watch1 = self._factory.new_headers.watch(self._heard_headers)
        self._watch2 = self._factory.new_block.watch(self._request)
        
        self._requested = set()
        self._clear_task = deferral.RobustLoopingCall(self._requested.clear)
        self._clear_task.start(60)
        
        self._last_notified_size = 0
        
        self.updated = variable.Event()
        
        self._think_task = deferral.RobustLoopingCall(self._think)
        self._think_task.start(15)
        self._think2_task = deferral.RobustLoopingCall(self._think2)
        self._think2_task.start(15)
    
    def _think(self):
        try:
            highest_head = max(self._tracker.heads, key=lambda h: self._tracker.get_height_and_last(h)[0]) if self._tracker.heads else None
            if highest_head is None:
                return # wait for think2
            height, last = self._tracker.get_height_and_last(highest_head)
            if height < self._backlog_needed:
                self._request(last)
        except:
            log.err(None, 'Error in HeightTracker._think:')
    
    def _think2(self):
        self._request(self._best_block_func())
    
    def _heard_headers(self, headers):
        changed = False
        for header in headers:
            hw = HeaderWrapper.from_header(header)
            if hw.hash in self._tracker.items:
                continue
            changed = True
            self._tracker.add(hw)
        if changed:
            self.updated.happened()
        self._think()
        
        if len(self._tracker.items) >= self._last_notified_size + 100:
            print 'Have %i/%i block headers' % (len(self._tracker.items), self._backlog_needed)
            self._last_notified_size = len(self._tracker.items)
    
    @defer.inlineCallbacks
    def _request(self, last):
        if last in self._tracker.items:
            return
        if last in self._requested:
            return
        self._requested.add(last)
        (yield self._factory.getProtocol()).send_getheaders(version=1, have=[], last=last)
    
    def get_height_rel_highest(self, block_hash):
        # callers: highest height can change during yields!
        best_height, best_last = self._tracker.get_height_and_last(self._best_block_func())
        height, last = self._tracker.get_height_and_last(block_hash)
        if last != best_last:
            return -1000000000 # XXX hack
        return height - best_height

@defer.inlineCallbacks
def get_height_rel_highest_func(bitcoind, factory, best_block_func, net):
    if '\ngetblock ' in (yield deferral.retry()(bitcoind.rpc_help)()):
        @deferral.DeferredCacher
        @defer.inlineCallbacks
        def height_cacher(block_hash):
            try:
                x = yield bitcoind.rpc_getblock('%x' % (block_hash,))
            except jsonrpc.Error_for_code(-5): # Block not found
                if not p2pool.DEBUG:
                    raise deferral.RetrySilentlyException()
                else:
                    raise
            defer.returnValue(x['blockcount'] if 'blockcount' in x else x['height'])
        best_height_cached = variable.Variable((yield deferral.retry()(height_cacher)(best_block_func())))
        def get_height_rel_highest(block_hash):
            this_height = height_cacher.call_now(block_hash, 0)
            best_height = height_cacher.call_now(best_block_func(), 0)
            best_height_cached.set(max(best_height_cached.value, this_height, best_height))
            return this_height - best_height_cached.value
    else:
        get_height_rel_highest = HeightTracker(best_block_func, factory, 5*net.SHARE_PERIOD*net.CHAIN_LENGTH/net.PARENT.BLOCK_PERIOD).get_height_rel_highest
    defer.returnValue(get_height_rel_highest)

########NEW FILE########
__FILENAME__ = helper
import sys
import time

from twisted.internet import defer

import p2pool
from p2pool.bitcoin import data as bitcoin_data
from p2pool.util import deferral, jsonrpc

@deferral.retry('Error while checking Bitcoin connection:', 1)
@defer.inlineCallbacks
def check(bitcoind, net):
    if not (yield net.PARENT.RPC_CHECK(bitcoind)):
        print >>sys.stderr, "    Check failed! Make sure that you're connected to the right bitcoind with --bitcoind-rpc-port!"
        raise deferral.RetrySilentlyException()
    if not net.VERSION_CHECK((yield bitcoind.rpc_getinfo())['version']):
        print >>sys.stderr, '    Bitcoin version too old! Upgrade to 0.6.4 or newer!'
        raise deferral.RetrySilentlyException()

@deferral.retry('Error getting work from bitcoind:', 3)
@defer.inlineCallbacks
def getwork(bitcoind, use_getblocktemplate=False):
    def go():
        if use_getblocktemplate:
            return bitcoind.rpc_getblocktemplate(dict(mode='template'))
        else:
            return bitcoind.rpc_getmemorypool()
    try:
        start = time.time()
        work = yield go()
        end = time.time()
    except jsonrpc.Error_for_code(-32601): # Method not found
        use_getblocktemplate = not use_getblocktemplate
        try:
            start = time.time()
            work = yield go()
            end = time.time()
        except jsonrpc.Error_for_code(-32601): # Method not found
            print >>sys.stderr, 'Error: Bitcoin version too old! Upgrade to v0.5 or newer!'
            raise deferral.RetrySilentlyException()
    packed_transactions = [(x['data'] if isinstance(x, dict) else x).decode('hex') for x in work['transactions']]
    if 'height' not in work:
        work['height'] = (yield bitcoind.rpc_getblock(work['previousblockhash']))['height'] + 1
    elif p2pool.DEBUG:
        assert work['height'] == (yield bitcoind.rpc_getblock(work['previousblockhash']))['height'] + 1
    defer.returnValue(dict(
        version=work['version'],
        previous_block=int(work['previousblockhash'], 16),
        transactions=map(bitcoin_data.tx_type.unpack, packed_transactions),
        transaction_hashes=map(bitcoin_data.hash256, packed_transactions),
        transaction_fees=[x.get('fee', None) if isinstance(x, dict) else None for x in work['transactions']],
        subsidy=work['coinbasevalue'],
        time=work['time'] if 'time' in work else work['curtime'],
        bits=bitcoin_data.FloatingIntegerType().unpack(work['bits'].decode('hex')[::-1]) if isinstance(work['bits'], (str, unicode)) else bitcoin_data.FloatingInteger(work['bits']),
        coinbaseflags=work['coinbaseflags'].decode('hex') if 'coinbaseflags' in work else ''.join(x.decode('hex') for x in work['coinbaseaux'].itervalues()) if 'coinbaseaux' in work else '',
        height=work['height'],
        last_update=time.time(),
        use_getblocktemplate=use_getblocktemplate,
        latency=end - start,
    ))

@deferral.retry('Error submitting primary block: (will retry)', 10, 10)
def submit_block_p2p(block, factory, net):
    if factory.conn.value is None:
        print >>sys.stderr, 'No bitcoind connection when block submittal attempted! %s%064x' % (net.PARENT.BLOCK_EXPLORER_URL_PREFIX, bitcoin_data.hash256(bitcoin_data.block_header_type.pack(block['header'])))
        raise deferral.RetrySilentlyException()
    factory.conn.value.send_block(block=block)

@deferral.retry('Error submitting block: (will retry)', 10, 10)
@defer.inlineCallbacks
def submit_block_rpc(block, ignore_failure, bitcoind, bitcoind_work, net):
    if bitcoind_work.value['use_getblocktemplate']:
        try:
            result = yield bitcoind.rpc_submitblock(bitcoin_data.block_type.pack(block).encode('hex'))
        except jsonrpc.Error_for_code(-32601): # Method not found, for older litecoin versions
            result = yield bitcoind.rpc_getblocktemplate(dict(mode='submit', data=bitcoin_data.block_type.pack(block).encode('hex')))
        success = result is None
    else:
        result = yield bitcoind.rpc_getmemorypool(bitcoin_data.block_type.pack(block).encode('hex'))
        success = result
    success_expected = net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(block['header'])) <= block['header']['bits'].target
    if (not success and success_expected and not ignore_failure) or (success and not success_expected):
        print >>sys.stderr, 'Block submittal result: %s (%r) Expected: %s' % (success, result, success_expected)

def submit_block(block, ignore_failure, factory, bitcoind, bitcoind_work, net):
    submit_block_p2p(block, factory, net)
    submit_block_rpc(block, ignore_failure, bitcoind, bitcoind_work, net)

########NEW FILE########
__FILENAME__ = networks
import os
import platform

from twisted.internet import defer

from . import data
from p2pool.util import math, pack, jsonrpc

@defer.inlineCallbacks
def check_genesis_block(bitcoind, genesis_block_hash):
    try:
        yield bitcoind.rpc_getblock(genesis_block_hash)
    except jsonrpc.Error_for_code(-5):
        defer.returnValue(False)
    else:
        defer.returnValue(True)

nets = dict(
    bitcoin=math.Object(
        P2P_PREFIX='f9beb4d9'.decode('hex'),
        P2P_PORT=8333,
        ADDRESS_VERSION=0,
        RPC_PORT=8332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            (yield check_genesis_block(bitcoind, '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f')) and
            not (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//210000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=600, # s
        SYMBOL='BTC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Bitcoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Bitcoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.bitcoin'), 'bitcoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='https://blockchain.info/block/',
        ADDRESS_EXPLORER_URL_PREFIX='https://blockchain.info/address/',
        TX_EXPLORER_URL_PREFIX='https://blockchain.info/tx/',
        SANE_TARGET_RANGE=(2**256//2**32//1000 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=0.001e8,
    ),
    bitcoin_testnet=math.Object(
        P2P_PREFIX='0b110907'.decode('hex'),
        P2P_PORT=18333,
        ADDRESS_VERSION=111,
        RPC_PORT=18332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'bitcoinaddress' in (yield bitcoind.rpc_help()) and
            (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//210000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=600, # s
        SYMBOL='tBTC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Bitcoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Bitcoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.bitcoin'), 'bitcoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://blockexplorer.com/testnet/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://blockexplorer.com/testnet/address/',
        TX_EXPLORER_URL_PREFIX='http://blockexplorer.com/testnet/tx/',
        SANE_TARGET_RANGE=(2**256//2**32//1000 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=1e8,
    ),
    
    namecoin=math.Object(
        P2P_PREFIX='f9beb4fe'.decode('hex'),
        P2P_PORT=8334,
        ADDRESS_VERSION=52,
        RPC_PORT=8332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'namecoinaddress' in (yield bitcoind.rpc_help()) and
            not (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//210000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=600, # s
        SYMBOL='NMC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Namecoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Namecoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.namecoin'), 'bitcoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://explorer.dot-bit.org/b/',
        ADDRESS_EXPLORER_URL_PREFIX='http://explorer.dot-bit.org/a/',
        TX_EXPLORER_URL_PREFIX='http://explorer.dot-bit.org/tx/',
        SANE_TARGET_RANGE=(2**256//2**32 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=0.2e8,
    ),
    namecoin_testnet=math.Object(
        P2P_PREFIX='fabfb5fe'.decode('hex'),
        P2P_PORT=18334,
        ADDRESS_VERSION=111,
        RPC_PORT=8332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'namecoinaddress' in (yield bitcoind.rpc_help()) and
            (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//210000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=600, # s
        SYMBOL='tNMC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Namecoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Namecoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.namecoin'), 'bitcoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://testnet.explorer.dot-bit.org/b/',
        ADDRESS_EXPLORER_URL_PREFIX='http://testnet.explorer.dot-bit.org/a/',
        TX_EXPLORER_URL_PREFIX='http://testnet.explorer.dot-bit.org/tx/',
        SANE_TARGET_RANGE=(2**256//2**32 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=1e8,
    ),
    
    litecoin=math.Object(
        P2P_PREFIX='fbc0b6db'.decode('hex'),
        P2P_PORT=9333,
        ADDRESS_VERSION=48,
        RPC_PORT=9332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'litecoinaddress' in (yield bitcoind.rpc_help()) and
            not (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//840000,
        POW_FUNC=lambda data: pack.IntType(256).unpack(__import__('ltc_scrypt').getPoWHash(data)),
        BLOCK_PERIOD=150, # s
        SYMBOL='LTC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Litecoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Litecoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.litecoin'), 'litecoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://explorer.litecoin.net/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://explorer.litecoin.net/address/',
        TX_EXPLORER_URL_PREFIX='http://explorer.litecoin.net/tx/',
        SANE_TARGET_RANGE=(2**256//1000000000 - 1, 2**256//1000 - 1),
        DUMB_SCRYPT_DIFF=2**16,
        DUST_THRESHOLD=0.03e8,
    ),
    litecoin_testnet=math.Object(
        P2P_PREFIX='fcc1b7dc'.decode('hex'),
        P2P_PORT=19333,
        ADDRESS_VERSION=111,
        RPC_PORT=19332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'litecoinaddress' in (yield bitcoind.rpc_help()) and
            (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 50*100000000 >> (height + 1)//840000,
        POW_FUNC=lambda data: pack.IntType(256).unpack(__import__('ltc_scrypt').getPoWHash(data)),
        BLOCK_PERIOD=150, # s
        SYMBOL='tLTC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Litecoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Litecoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.litecoin'), 'litecoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://nonexistent-litecoin-testnet-explorer/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://nonexistent-litecoin-testnet-explorer/address/',
        TX_EXPLORER_URL_PREFIX='http://nonexistent-litecoin-testnet-explorer/tx/',
        SANE_TARGET_RANGE=(2**256//1000000000 - 1, 2**256 - 1),
        DUMB_SCRYPT_DIFF=2**16,
        DUST_THRESHOLD=1e8,
    ),

    terracoin=math.Object(
        P2P_PREFIX='42babe56'.decode('hex'),
        P2P_PORT=13333,
        ADDRESS_VERSION=0,
        RPC_PORT=13332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'terracoinaddress' in (yield bitcoind.rpc_help()) and
            not (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 20*100000000 >> (height + 1)//1050000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=120, # s
        SYMBOL='TRC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Terracoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Terracoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.terracoin'), 'terracoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/address/',
        TX_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/tx/',
        SANE_TARGET_RANGE=(2**256//2**32//1000 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=1e8,
    ),
    terracoin_testnet=math.Object(
        P2P_PREFIX='41babe56'.decode('hex'),
        P2P_PORT=23333,
        ADDRESS_VERSION=111,
        RPC_PORT=23332,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'terracoinaddress' in (yield bitcoind.rpc_help()) and
            (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 20*100000000 >> (height + 1)//1050000,
        POW_FUNC=data.hash256,
        BLOCK_PERIOD=120, # s
        SYMBOL='tTRC',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Terracoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Terracoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.terracoin'), 'terracoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/testnet/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/testnet/address/',
        TX_EXPLORER_URL_PREFIX='http://trc.cryptocoinexplorer.com/testnet/tx/',
        SANE_TARGET_RANGE=(2**256//2**32//1000 - 1, 2**256//2**32 - 1),
        DUMB_SCRYPT_DIFF=1,
        DUST_THRESHOLD=1e8,
    ),
    fastcoin=math.Object(
        P2P_PREFIX='fbc0b6db'.decode('hex'),
        P2P_PORT=9526,
        ADDRESS_VERSION=96,
        RPC_PORT=9527,
        RPC_CHECK=defer.inlineCallbacks(lambda bitcoind: defer.returnValue(
            'fastcoinaddress' in (yield bitcoind.rpc_help()) and
            not (yield bitcoind.rpc_getinfo())['testnet']
        )),
        SUBSIDY_FUNC=lambda height: 32*100000000 >> (height + 1)//2592000,
        POW_FUNC=lambda data: pack.IntType(256).unpack(__import__('ltc_scrypt').getPoWHash(data)),
        BLOCK_PERIOD=12, # s
        SYMBOL='FST',
        CONF_FILE_FUNC=lambda: os.path.join(os.path.join(os.environ['APPDATA'], 'Fastcoin') if platform.system() == 'Windows' else os.path.expanduser('~/Library/Application Support/Fastcoin/') if platform.system() == 'Darwin' else os.path.expanduser('~/.fastcoin'), 'fastcoin.conf'),
        BLOCK_EXPLORER_URL_PREFIX='http://fst.webboise.com/block/',
        ADDRESS_EXPLORER_URL_PREFIX='http://fst.webboise.com/address/',
        TX_EXPLORER_URL_PREFIX='http://fst.webboise.com/tx/',
        SANE_TARGET_RANGE=(2**256//100000000 - 1, 2**256//1000 - 1),
        DUMB_SCRYPT_DIFF=2**16,
        DUST_THRESHOLD=0.03e8,
    ),

)
for net_name, net in nets.iteritems():
    net.NAME = net_name

########NEW FILE########
__FILENAME__ = p2p
'''
Implementation of Bitcoin's p2p protocol
'''

import random
import sys
import time

from twisted.internet import protocol

import p2pool
from . import data as bitcoin_data
from p2pool.util import deferral, p2protocol, pack, variable

class Protocol(p2protocol.Protocol):
    def __init__(self, net):
        p2protocol.Protocol.__init__(self, net.P2P_PREFIX, 1000000, ignore_trailing_payload=True)
    
    def connectionMade(self):
        self.send_version(
            version=70002,
            services=1,
            time=int(time.time()),
            addr_to=dict(
                services=1,
                address=self.transport.getPeer().host,
                port=self.transport.getPeer().port,
            ),
            addr_from=dict(
                services=1,
                address=self.transport.getHost().host,
                port=self.transport.getHost().port,
            ),
            nonce=random.randrange(2**64),
            sub_version_num='/P2Pool:%s/' % (p2pool.__version__,),
            start_height=0,
        )
    
    message_version = pack.ComposedType([
        ('version', pack.IntType(32)),
        ('services', pack.IntType(64)),
        ('time', pack.IntType(64)),
        ('addr_to', bitcoin_data.address_type),
        ('addr_from', bitcoin_data.address_type),
        ('nonce', pack.IntType(64)),
        ('sub_version_num', pack.VarStrType()),
        ('start_height', pack.IntType(32)),
    ])
    def handle_version(self, version, services, time, addr_to, addr_from, nonce, sub_version_num, start_height):
        self.send_verack()
    
    message_verack = pack.ComposedType([])
    def handle_verack(self):
        self.get_block = deferral.ReplyMatcher(lambda hash: self.send_getdata(requests=[dict(type='block', hash=hash)]))
        self.get_block_header = deferral.ReplyMatcher(lambda hash: self.send_getheaders(version=1, have=[], last=hash))
        
        if hasattr(self.factory, 'resetDelay'):
            self.factory.resetDelay()
        if hasattr(self.factory, 'gotConnection'):
            self.factory.gotConnection(self)
        
        self.pinger = deferral.RobustLoopingCall(self.send_ping, nonce=1234)
        self.pinger.start(30)
    
    message_inv = pack.ComposedType([
        ('invs', pack.ListType(pack.ComposedType([
            ('type', pack.EnumType(pack.IntType(32), {1: 'tx', 2: 'block'})),
            ('hash', pack.IntType(256)),
        ]))),
    ])
    def handle_inv(self, invs):
        for inv in invs:
            if inv['type'] == 'tx':
                self.send_getdata(requests=[inv])
            elif inv['type'] == 'block':
                self.factory.new_block.happened(inv['hash'])
            else:
                print 'Unknown inv type', inv
    
    message_getdata = pack.ComposedType([
        ('requests', pack.ListType(pack.ComposedType([
            ('type', pack.EnumType(pack.IntType(32), {1: 'tx', 2: 'block'})),
            ('hash', pack.IntType(256)),
        ]))),
    ])
    message_getblocks = pack.ComposedType([
        ('version', pack.IntType(32)),
        ('have', pack.ListType(pack.IntType(256))),
        ('last', pack.PossiblyNoneType(0, pack.IntType(256))),
    ])
    message_getheaders = pack.ComposedType([
        ('version', pack.IntType(32)),
        ('have', pack.ListType(pack.IntType(256))),
        ('last', pack.PossiblyNoneType(0, pack.IntType(256))),
    ])
    message_getaddr = pack.ComposedType([])
    
    message_addr = pack.ComposedType([
        ('addrs', pack.ListType(pack.ComposedType([
            ('timestamp', pack.IntType(32)),
            ('address', bitcoin_data.address_type),
        ]))),
    ])
    def handle_addr(self, addrs):
        for addr in addrs:
            pass
    
    message_tx = pack.ComposedType([
        ('tx', bitcoin_data.tx_type),
    ])
    def handle_tx(self, tx):
        self.factory.new_tx.happened(tx)
    
    message_block = pack.ComposedType([
        ('block', bitcoin_data.block_type),
    ])
    def handle_block(self, block):
        block_hash = bitcoin_data.hash256(bitcoin_data.block_header_type.pack(block['header']))
        self.get_block.got_response(block_hash, block)
        self.get_block_header.got_response(block_hash, block['header'])
    
    message_headers = pack.ComposedType([
        ('headers', pack.ListType(bitcoin_data.block_type)),
    ])
    def handle_headers(self, headers):
        for header in headers:
            header = header['header']
            self.get_block_header.got_response(bitcoin_data.hash256(bitcoin_data.block_header_type.pack(header)), header)
        self.factory.new_headers.happened([header['header'] for header in headers])
    
    message_ping = pack.ComposedType([
        ('nonce', pack.IntType(64)),
    ])
    def handle_ping(self, nonce):
        self.send_pong(nonce=nonce)
    
    message_pong = pack.ComposedType([
        ('nonce', pack.IntType(64)),
    ])
    def handle_pong(self, nonce):
        pass
    
    message_alert = pack.ComposedType([
        ('message', pack.VarStrType()),
        ('signature', pack.VarStrType()),
    ])
    def handle_alert(self, message, signature):
        pass # print 'ALERT:', (message, signature)
    
    def connectionLost(self, reason):
        if hasattr(self.factory, 'gotConnection'):
            self.factory.gotConnection(None)
        if hasattr(self, 'pinger'):
            self.pinger.stop()
        if p2pool.DEBUG:
            print >>sys.stderr, 'Bitcoin connection lost. Reason:', reason.getErrorMessage()

class ClientFactory(protocol.ReconnectingClientFactory):
    protocol = Protocol
    
    maxDelay = 1
    
    def __init__(self, net):
        self.net = net
        self.conn = variable.Variable(None)
        
        self.new_block = variable.Event()
        self.new_tx = variable.Event()
        self.new_headers = variable.Event()
    
    def buildProtocol(self, addr):
        p = self.protocol(self.net)
        p.factory = self
        return p
    
    def gotConnection(self, conn):
        self.conn.set(conn)
    
    def getProtocol(self):
        return self.conn.get_not_none()

########NEW FILE########
__FILENAME__ = script
from p2pool.util import math, pack

def reads_nothing(f):
    return None, f
def protoPUSH(length):
    return lambda f: pack.read(f, length)
def protoPUSHDATA(size_len):
    def _(f):
        length_str, f = pack.read(f, size_len)
        length = math.string_to_natural(length_str[::-1].lstrip(chr(0)))
        data, f = pack.read(f, length)
        return data, f
    return _

opcodes = {}
for i in xrange(256):
    opcodes[i] = 'UNK_' + str(i), reads_nothing

opcodes[0] = 'PUSH', lambda f: ('', f)
for i in xrange(1, 76):
    opcodes[i] = 'PUSH', protoPUSH(i)
opcodes[76] = 'PUSH', protoPUSHDATA(1)
opcodes[77] = 'PUSH', protoPUSHDATA(2)
opcodes[78] = 'PUSH', protoPUSHDATA(4)
opcodes[79] = 'PUSH', lambda f: ('\x81', f)
for i in xrange(81, 97):
    opcodes[i] = 'PUSH', lambda f, _i=i: (chr(_i - 80), f)

opcodes[172] = 'CHECKSIG', reads_nothing
opcodes[173] = 'CHECKSIGVERIFY', reads_nothing
opcodes[174] = 'CHECKMULTISIG', reads_nothing
opcodes[175] = 'CHECKMULTISIGVERIFY', reads_nothing

def parse(script):
    f = script, 0
    while pack.size(f):
        opcode_str, f = pack.read(f, 1)
        opcode = ord(opcode_str)
        opcode_name, read_func = opcodes[opcode]
        opcode_arg, f = read_func(f)
        yield opcode_name, opcode_arg

def get_sigop_count(script):
    weights = {
        'CHECKSIG': 1,
        'CHECKSIGVERIFY': 1,
        'CHECKMULTISIG': 20,
        'CHECKMULTISIGVERIFY': 20,
    }
    return sum(weights.get(opcode_name, 0) for opcode_name, opcode_arg in parse(script))

def create_push_script(datums): # datums can be ints or strs
    res = []
    for datum in datums:
        if isinstance(datum, (int, long)):
            if datum == -1 or 1 <= datum <= 16:
                res.append(chr(datum + 80))
                continue
            negative = datum < 0
            datum = math.natural_to_string(abs(datum))
            if datum and ord(datum[0]) & 128:
                datum = '\x00' + datum
            if negative:
                datum = chr(ord(datum[0]) + 128) + datum[1:]
            datum = datum[::-1]
        if len(datum) < 76:
            res.append(chr(len(datum)))
        elif len(datum) <= 0xff:
            res.append(76)
            res.append(chr(len(datum)))
        elif len(datum) <= 0xffff:
            res.append(77)
            res.append(pack.IntType(16).pack(len(datum)))
        elif len(datum) <= 0xffffffff:
            res.append(78)
            res.append(pack.IntType(32).pack(len(datum)))
        else:
            raise ValueError('string too long')
        res.append(datum)
    return ''.join(res)

########NEW FILE########
__FILENAME__ = sha256
from __future__ import division

import struct


k = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

def process(state, chunk):
    def rightrotate(x, n):
        return (x >> n) | (x << 32 - n) % 2**32
    
    w = list(struct.unpack('>16I', chunk))
    for i in xrange(16, 64):
        s0 = rightrotate(w[i-15], 7) ^ rightrotate(w[i-15], 18) ^ (w[i-15] >> 3)
        s1 = rightrotate(w[i-2], 17) ^ rightrotate(w[i-2], 19) ^ (w[i-2] >> 10)
        w.append((w[i-16] + s0 + w[i-7] + s1) % 2**32)
    
    a, b, c, d, e, f, g, h = start_state = struct.unpack('>8I', state)
    for k_i, w_i in zip(k, w):
        t1 = (h + (rightrotate(e, 6) ^ rightrotate(e, 11) ^ rightrotate(e, 25)) + ((e & f) ^ (~e & g)) + k_i + w_i) % 2**32
        
        a, b, c, d, e, f, g, h = (
            (t1 + (rightrotate(a, 2) ^ rightrotate(a, 13) ^ rightrotate(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) % 2**32,
            a, b, c, (d + t1) % 2**32, e, f, g,
        )
    
    return struct.pack('>8I', *((x + y) % 2**32 for x, y in zip(start_state, [a, b, c, d, e, f, g, h])))


initial_state = struct.pack('>8I', 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)

class sha256(object):
    digest_size = 256//8
    block_size = 512//8
    
    def __init__(self, data='', _=(initial_state, '', 0)):
        self.state, self.buf, self.length = _
        self.update(data)
    
    def update(self, data):
        state = self.state
        buf = self.buf + data
        
        chunks = [buf[i:i + self.block_size] for i in xrange(0, len(buf) + 1, self.block_size)]
        for chunk in chunks[:-1]:
            state = process(state, chunk)
        
        self.state = state
        self.buf = chunks[-1]
        
        self.length += 8*len(data)
    
    def copy(self, data=''):
        return self.__class__(data, (self.state, self.buf, self.length))
    
    def digest(self):
        state = self.state
        buf = self.buf + '\x80' + '\x00'*((self.block_size - 9 - len(self.buf)) % self.block_size) + struct.pack('>Q', self.length)
        
        for chunk in [buf[i:i + self.block_size] for i in xrange(0, len(buf), self.block_size)]:
            state = process(state, chunk)
        
        return state
    
    def hexdigest(self):
        return self.digest().encode('hex')

########NEW FILE########
__FILENAME__ = stratum
import random
import sys

from twisted.internet import protocol, reactor
from twisted.python import log

from p2pool.bitcoin import data as bitcoin_data, getwork
from p2pool.util import expiring_dict, jsonrpc, pack


class StratumRPCMiningProvider(object):
    def __init__(self, wb, other, transport):
        self.wb = wb
        self.other = other
        self.transport = transport
        
        self.username = None
        self.handler_map = expiring_dict.ExpiringDict(300)
        
        self.watch_id = self.wb.new_work_event.watch(self._send_work)
    
    def rpc_subscribe(self, miner_version=None, session_id=None):
        reactor.callLater(0, self._send_work)
        
        return [
            ["mining.notify", "ae6812eb4cd7735a302a8a9dd95cf71f"], # subscription details
            "", # extranonce1
            self.wb.COINBASE_NONCE_LENGTH, # extranonce2_size
        ]
    
    def rpc_authorize(self, username, password):
        self.username = username
        
        reactor.callLater(0, self._send_work)
    
    def _send_work(self):
        try:
            x, got_response = self.wb.get_work(*self.wb.preprocess_request('' if self.username is None else self.username))
        except:
            log.err()
            self.transport.loseConnection()
            return
        jobid = str(random.randrange(2**128))
        self.other.svc_mining.rpc_set_difficulty(bitcoin_data.target_to_difficulty(x['share_target'])*self.wb.net.DUMB_SCRYPT_DIFF).addErrback(lambda err: None)
        self.other.svc_mining.rpc_notify(
            jobid, # jobid
            getwork._swap4(pack.IntType(256).pack(x['previous_block'])).encode('hex'), # prevhash
            x['coinb1'].encode('hex'), # coinb1
            x['coinb2'].encode('hex'), # coinb2
            [pack.IntType(256).pack(s).encode('hex') for s in x['merkle_link']['branch']], # merkle_branch
            getwork._swap4(pack.IntType(32).pack(x['version'])).encode('hex'), # version
            getwork._swap4(pack.IntType(32).pack(x['bits'].bits)).encode('hex'), # nbits
            getwork._swap4(pack.IntType(32).pack(x['timestamp'])).encode('hex'), # ntime
            True, # clean_jobs
        ).addErrback(lambda err: None)
        self.handler_map[jobid] = x, got_response
    
    def rpc_submit(self, worker_name, job_id, extranonce2, ntime, nonce):
        if job_id not in self.handler_map:
            print >>sys.stderr, '''Couldn't link returned work's job id with its handler. This should only happen if this process was recently restarted!'''
            return False
        x, got_response = self.handler_map[job_id]
        coinb_nonce = extranonce2.decode('hex')
        assert len(coinb_nonce) == self.wb.COINBASE_NONCE_LENGTH
        new_packed_gentx = x['coinb1'] + coinb_nonce + x['coinb2']
        header = dict(
            version=x['version'],
            previous_block=x['previous_block'],
            merkle_root=bitcoin_data.check_merkle_link(bitcoin_data.hash256(new_packed_gentx), x['merkle_link']),
            timestamp=pack.IntType(32).unpack(getwork._swap4(ntime.decode('hex'))),
            bits=x['bits'],
            nonce=pack.IntType(32).unpack(getwork._swap4(nonce.decode('hex'))),
        )
        return got_response(header, worker_name, coinb_nonce)
    
    def close(self):
        self.wb.new_work_event.unwatch(self.watch_id)

class StratumProtocol(jsonrpc.LineBasedPeer):
    def connectionMade(self):
        self.svc_mining = StratumRPCMiningProvider(self.factory.wb, self.other, self.transport)
    
    def connectionLost(self, reason):
        self.svc_mining.close()

class StratumServerFactory(protocol.ServerFactory):
    protocol = StratumProtocol
    
    def __init__(self, wb):
        self.wb = wb

########NEW FILE########
__FILENAME__ = worker_interface
from __future__ import division

import StringIO
import json
import random
import sys

from twisted.internet import defer

import p2pool
from p2pool.bitcoin import data as bitcoin_data, getwork
from p2pool.util import expiring_dict, jsonrpc, pack, variable

class _Provider(object):
    def __init__(self, parent, long_poll):
        self.parent = parent
        self.long_poll = long_poll
    
    def rpc_getwork(self, request, data=None):
        return self.parent._getwork(request, data, long_poll=self.long_poll)

class _GETableServer(jsonrpc.HTTPServer):
    def __init__(self, provider, render_get_func):
        jsonrpc.HTTPServer.__init__(self, provider)
        self.render_GET = render_get_func

class WorkerBridge(object):
    def __init__(self):
        self.new_work_event = variable.Event()
    
    def preprocess_request(self, request):
        return request, # *args to self.compute
    
    def get_work(self, request):
        raise NotImplementedError()

class WorkerInterface(object):
    def __init__(self, worker_bridge):
        self.worker_bridge = worker_bridge
        
        self.worker_views = {}
        
        self.merkle_root_to_handler = expiring_dict.ExpiringDict(300)
    
    def attach_to(self, res, get_handler=None):
        res.putChild('', _GETableServer(_Provider(self, long_poll=False), get_handler))
        
        def repost(request):
            request.content = StringIO.StringIO(json.dumps(dict(id=0, method='getwork')))
            return s.render_POST(request)
        s = _GETableServer(_Provider(self, long_poll=True), repost)
        res.putChild('long-polling', s)
    
    @defer.inlineCallbacks
    def _getwork(self, request, data, long_poll):
        request.setHeader('X-Long-Polling', '/long-polling')
        request.setHeader('X-Roll-NTime', 'expire=100')
        request.setHeader('X-Is-P2Pool', 'true')
        if request.getHeader('Host') is not None:
            request.setHeader('X-Stratum', 'stratum+tcp://' + request.getHeader('Host'))
        
        if data is not None:
            header = getwork.decode_data(data)
            if header['merkle_root'] not in self.merkle_root_to_handler:
                print >>sys.stderr, '''Couldn't link returned work's merkle root with its handler. This should only happen if this process was recently restarted!'''
                defer.returnValue(False)
            defer.returnValue(self.merkle_root_to_handler[header['merkle_root']](header, request.getUser() if request.getUser() is not None else '', '\0'*self.worker_bridge.COINBASE_NONCE_LENGTH))
        
        if p2pool.DEBUG:
            id = random.randrange(1000, 10000)
            print 'POLL %i START is_long_poll=%r user_agent=%r user=%r' % (id, long_poll, request.getHeader('User-Agent'), request.getUser())
        
        if long_poll:
            request_id = request.getClientIP(), request.getHeader('Authorization')
            if self.worker_views.get(request_id, self.worker_bridge.new_work_event.times) != self.worker_bridge.new_work_event.times:
                if p2pool.DEBUG:
                    print 'POLL %i PUSH' % (id,)
            else:
                if p2pool.DEBUG:
                    print 'POLL %i WAITING' % (id,)
                yield self.worker_bridge.new_work_event.get_deferred()
            self.worker_views[request_id] = self.worker_bridge.new_work_event.times
        
        x, handler = self.worker_bridge.get_work(*self.worker_bridge.preprocess_request(request.getUser() if request.getUser() is not None else ''))
        res = getwork.BlockAttempt(
            version=x['version'],
            previous_block=x['previous_block'],
            merkle_root=bitcoin_data.check_merkle_link(bitcoin_data.hash256(x['coinb1'] + '\0'*self.worker_bridge.COINBASE_NONCE_LENGTH + x['coinb2']), x['merkle_link']),
            timestamp=x['timestamp'],
            bits=x['bits'],
            share_target=x['share_target'],
        )
        assert res.merkle_root not in self.merkle_root_to_handler
        
        self.merkle_root_to_handler[res.merkle_root] = handler
        
        if p2pool.DEBUG:
            print 'POLL %i END identifier=%i' % (id, self.worker_bridge.new_work_event.times)
        
        extra_params = {}
        if request.getHeader('User-Agent') == 'Jephis PIC Miner':
            # ASICMINER BE Blades apparently have a buffer overflow bug and
            # can't handle much extra in the getwork response
            extra_params = {}
        else:
            extra_params = dict(identifier=str(self.worker_bridge.new_work_event.times), submitold=True)
        defer.returnValue(res.getwork(**extra_params))

class CachingWorkerBridge(object):
    def __init__(self, inner):
        self._inner = inner
        self.net = self._inner.net
        
        self.COINBASE_NONCE_LENGTH = (inner.COINBASE_NONCE_LENGTH+1)//2
        self.new_work_event = inner.new_work_event
        self.preprocess_request = inner.preprocess_request
        
        self._my_bits = (self._inner.COINBASE_NONCE_LENGTH - self.COINBASE_NONCE_LENGTH)*8
        
        self._cache = {}
        self._times = None
    
    def get_work(self, *args):
        if self._times != self.new_work_event.times:
            self._cache = {}
            self._times = self.new_work_event.times
        
        if args not in self._cache:
            x, handler = self._inner.get_work(*args)
            self._cache[args] = x, handler, 0
        
        x, handler, nonce = self._cache.pop(args)
        
        res = (
            dict(x, coinb1=x['coinb1'] + pack.IntType(self._my_bits).pack(nonce)),
            lambda header, user, coinbase_nonce: handler(header, user, pack.IntType(self._my_bits).pack(nonce) + coinbase_nonce),
        )
        
        if nonce + 1 != 2**self._my_bits:
            self._cache[args] = x, handler, nonce + 1
        
        return res

########NEW FILE########
__FILENAME__ = data
from __future__ import division

import hashlib
import os
import random
import sys
import time

from twisted.python import log

import p2pool
from p2pool.bitcoin import data as bitcoin_data, script, sha256
from p2pool.util import math, forest, pack

# hashlink

hash_link_type = pack.ComposedType([
    ('state', pack.FixedStrType(32)),
    ('extra_data', pack.FixedStrType(0)), # bit of a hack, but since the donation script is at the end, const_ending is long enough to always make this empty
    ('length', pack.VarIntType()),
])

def prefix_to_hash_link(prefix, const_ending=''):
    assert prefix.endswith(const_ending), (prefix, const_ending)
    x = sha256.sha256(prefix)
    return dict(state=x.state, extra_data=x.buf[:max(0, len(x.buf)-len(const_ending))], length=x.length//8)

def check_hash_link(hash_link, data, const_ending=''):
    extra_length = hash_link['length'] % (512//8)
    assert len(hash_link['extra_data']) == max(0, extra_length - len(const_ending))
    extra = (hash_link['extra_data'] + const_ending)[len(hash_link['extra_data']) + len(const_ending) - extra_length:]
    assert len(extra) == extra_length
    return pack.IntType(256).unpack(hashlib.sha256(sha256.sha256(data, (hash_link['state'], extra, 8*hash_link['length'])).digest()).digest())

# shares

share_type = pack.ComposedType([
    ('type', pack.VarIntType()),
    ('contents', pack.VarStrType()),
])

def load_share(share, net, peer_addr):
    assert peer_addr is None or isinstance(peer_addr, tuple)
    if share['type'] < Share.VERSION:
        from p2pool import p2p
        raise p2p.PeerMisbehavingError('sent an obsolete share')
    elif share['type'] == Share.VERSION:
        return Share(net, peer_addr, Share.share_type.unpack(share['contents']))
    else:
        raise ValueError('unknown share type: %r' % (share['type'],))

DONATION_SCRIPT = '4104ffd03de44a6e11b9917f3a29f9443283d9871c9d743ef30d5eddcd37094b64d1b3d8090496b53256786bf5c82932ec23c3b74d9f05a6f95a8b5529352656664bac'.decode('hex')

class Share(object):
    VERSION = 13
    VOTING_VERSION = 13
    SUCCESSOR = None
    
    small_block_header_type = pack.ComposedType([
        ('version', pack.VarIntType()),
        ('previous_block', pack.PossiblyNoneType(0, pack.IntType(256))),
        ('timestamp', pack.IntType(32)),
        ('bits', bitcoin_data.FloatingIntegerType()),
        ('nonce', pack.IntType(32)),
    ])
    
    share_info_type = pack.ComposedType([
        ('share_data', pack.ComposedType([
            ('previous_share_hash', pack.PossiblyNoneType(0, pack.IntType(256))),
            ('coinbase', pack.VarStrType()),
            ('nonce', pack.IntType(32)),
            ('pubkey_hash', pack.IntType(160)),
            ('subsidy', pack.IntType(64)),
            ('donation', pack.IntType(16)),
            ('stale_info', pack.EnumType(pack.IntType(8), dict((k, {0: None, 253: 'orphan', 254: 'doa'}.get(k, 'unk%i' % (k,))) for k in xrange(256)))),
            ('desired_version', pack.VarIntType()),
        ])),
        ('new_transaction_hashes', pack.ListType(pack.IntType(256))),
        ('transaction_hash_refs', pack.ListType(pack.VarIntType(), 2)), # pairs of share_count, tx_count
        ('far_share_hash', pack.PossiblyNoneType(0, pack.IntType(256))),
        ('max_bits', bitcoin_data.FloatingIntegerType()),
        ('bits', bitcoin_data.FloatingIntegerType()),
        ('timestamp', pack.IntType(32)),
        ('absheight', pack.IntType(32)),
        ('abswork', pack.IntType(128)),
    ])
    
    share_type = pack.ComposedType([
        ('min_header', small_block_header_type),
        ('share_info', share_info_type),
        ('ref_merkle_link', pack.ComposedType([
            ('branch', pack.ListType(pack.IntType(256))),
            ('index', pack.IntType(0)),
        ])),
        ('last_txout_nonce', pack.IntType(64)),
        ('hash_link', hash_link_type),
        ('merkle_link', pack.ComposedType([
            ('branch', pack.ListType(pack.IntType(256))),
            ('index', pack.IntType(0)), # it will always be 0
        ])),
    ])
    
    ref_type = pack.ComposedType([
        ('identifier', pack.FixedStrType(64//8)),
        ('share_info', share_info_type),
    ])
    
    gentx_before_refhash = pack.VarStrType().pack(DONATION_SCRIPT) + pack.IntType(64).pack(0) + pack.VarStrType().pack('\x6a\x28' + pack.IntType(256).pack(0) + pack.IntType(64).pack(0))[:3]
    
    @classmethod
    def generate_transaction(cls, tracker, share_data, block_target, desired_timestamp, desired_target, ref_merkle_link, desired_other_transaction_hashes_and_fees, net, known_txs=None, last_txout_nonce=0, base_subsidy=None):
        previous_share = tracker.items[share_data['previous_share_hash']] if share_data['previous_share_hash'] is not None else None
        
        height, last = tracker.get_height_and_last(share_data['previous_share_hash'])
        assert height >= net.REAL_CHAIN_LENGTH or last is None
        if height < net.TARGET_LOOKBEHIND:
            pre_target3 = net.MAX_TARGET
        else:
            attempts_per_second = get_pool_attempts_per_second(tracker, share_data['previous_share_hash'], net.TARGET_LOOKBEHIND, min_work=True, integer=True)
            pre_target = 2**256//(net.SHARE_PERIOD*attempts_per_second) - 1 if attempts_per_second else 2**256-1
            pre_target2 = math.clip(pre_target, (previous_share.max_target*9//10, previous_share.max_target*11//10))
            pre_target3 = math.clip(pre_target2, (net.MIN_TARGET, net.MAX_TARGET))
        max_bits = bitcoin_data.FloatingInteger.from_target_upper_bound(pre_target3)
        bits = bitcoin_data.FloatingInteger.from_target_upper_bound(math.clip(desired_target, (pre_target3//30, pre_target3)))
        
        new_transaction_hashes = []
        new_transaction_size = 0
        transaction_hash_refs = []
        other_transaction_hashes = []
        
        past_shares = list(tracker.get_chain(share_data['previous_share_hash'], min(height, 100)))
        tx_hash_to_this = {}
        for i, share in enumerate(past_shares):
            for j, tx_hash in enumerate(share.new_transaction_hashes):
                if tx_hash not in tx_hash_to_this:
                    tx_hash_to_this[tx_hash] = [1+i, j] # share_count, tx_count
        for tx_hash, fee in desired_other_transaction_hashes_and_fees:
            if tx_hash in tx_hash_to_this:
                this = tx_hash_to_this[tx_hash]
            else:
                if known_txs is not None:
                    this_size = bitcoin_data.tx_type.packed_size(known_txs[tx_hash])
                    if new_transaction_size + this_size > 50000: # only allow 50 kB of new txns/share
                        break
                    new_transaction_size += this_size
                new_transaction_hashes.append(tx_hash)
                this = [0, len(new_transaction_hashes)-1]
            transaction_hash_refs.extend(this)
            other_transaction_hashes.append(tx_hash)
        
        included_transactions = set(other_transaction_hashes)
        removed_fees = [fee for tx_hash, fee in desired_other_transaction_hashes_and_fees if tx_hash not in included_transactions]
        definite_fees = sum(0 if fee is None else fee for tx_hash, fee in desired_other_transaction_hashes_and_fees if tx_hash in included_transactions)
        if None not in removed_fees:
            share_data = dict(share_data, subsidy=share_data['subsidy'] - sum(removed_fees))
        else:
            assert base_subsidy is not None
            share_data = dict(share_data, subsidy=base_subsidy + definite_fees)
        
        weights, total_weight, donation_weight = tracker.get_cumulative_weights(previous_share.share_data['previous_share_hash'] if previous_share is not None else None,
            max(0, min(height, net.REAL_CHAIN_LENGTH) - 1),
            65535*net.SPREAD*bitcoin_data.target_to_average_attempts(block_target),
        )
        assert total_weight == sum(weights.itervalues()) + donation_weight, (total_weight, sum(weights.itervalues()) + donation_weight)
        
        amounts = dict((script, share_data['subsidy']*(199*weight)//(200*total_weight)) for script, weight in weights.iteritems()) # 99.5% goes according to weights prior to this share
        this_script = bitcoin_data.pubkey_hash_to_script2(share_data['pubkey_hash'])
        amounts[this_script] = amounts.get(this_script, 0) + share_data['subsidy']//200 # 0.5% goes to block finder
        amounts[DONATION_SCRIPT] = amounts.get(DONATION_SCRIPT, 0) + share_data['subsidy'] - sum(amounts.itervalues()) # all that's left over is the donation weight and some extra satoshis due to rounding
        
        if sum(amounts.itervalues()) != share_data['subsidy'] or any(x < 0 for x in amounts.itervalues()):
            raise ValueError()
        
        dests = sorted(amounts.iterkeys(), key=lambda script: (script == DONATION_SCRIPT, amounts[script], script))[-4000:] # block length limit, unlikely to ever be hit
        
        share_info = dict(
            share_data=share_data,
            far_share_hash=None if last is None and height < 99 else tracker.get_nth_parent_hash(share_data['previous_share_hash'], 99),
            max_bits=max_bits,
            bits=bits,
            timestamp=math.clip(desired_timestamp, (
                (previous_share.timestamp + net.SHARE_PERIOD) - (net.SHARE_PERIOD - 1), # = previous_share.timestamp + 1
                (previous_share.timestamp + net.SHARE_PERIOD) + (net.SHARE_PERIOD - 1),
            )) if previous_share is not None else desired_timestamp,
            new_transaction_hashes=new_transaction_hashes,
            transaction_hash_refs=transaction_hash_refs,
            absheight=((previous_share.absheight if previous_share is not None else 0) + 1) % 2**32,
            abswork=((previous_share.abswork if previous_share is not None else 0) + bitcoin_data.target_to_average_attempts(bits.target)) % 2**128,
        )
        
        gentx = dict(
            version=1,
            tx_ins=[dict(
                previous_output=None,
                sequence=None,
                script=share_data['coinbase'],
            )],
            tx_outs=[dict(value=amounts[script], script=script) for script in dests if amounts[script] or script == DONATION_SCRIPT] + [dict(
                value=0,
                script='\x6a\x28' + cls.get_ref_hash(net, share_info, ref_merkle_link) + pack.IntType(64).pack(last_txout_nonce),
            )],
            lock_time=0,
        )
        
        def get_share(header, last_txout_nonce=last_txout_nonce):
            min_header = dict(header); del min_header['merkle_root']
            share = cls(net, None, dict(
                min_header=min_header,
                share_info=share_info,
                ref_merkle_link=dict(branch=[], index=0),
                last_txout_nonce=last_txout_nonce,
                hash_link=prefix_to_hash_link(bitcoin_data.tx_type.pack(gentx)[:-32-8-4], cls.gentx_before_refhash),
                merkle_link=bitcoin_data.calculate_merkle_link([None] + other_transaction_hashes, 0),
            ))
            assert share.header == header # checks merkle_root
            return share
        
        return share_info, gentx, other_transaction_hashes, get_share
    
    @classmethod
    def get_ref_hash(cls, net, share_info, ref_merkle_link):
        return pack.IntType(256).pack(bitcoin_data.check_merkle_link(bitcoin_data.hash256(cls.ref_type.pack(dict(
            identifier=net.IDENTIFIER,
            share_info=share_info,
        ))), ref_merkle_link))
    
    __slots__ = 'net peer_addr contents min_header share_info hash_link merkle_link hash share_data max_target target timestamp previous_hash new_script desired_version gentx_hash header pow_hash header_hash new_transaction_hashes time_seen absheight abswork'.split(' ')
    
    def __init__(self, net, peer_addr, contents):
        self.net = net
        self.peer_addr = peer_addr
        self.contents = contents
        
        self.min_header = contents['min_header']
        self.share_info = contents['share_info']
        self.hash_link = contents['hash_link']
        self.merkle_link = contents['merkle_link']
        
        if not (2 <= len(self.share_info['share_data']['coinbase']) <= 100):
            raise ValueError('''bad coinbase size! %i bytes''' % (len(self.share_info['share_data']['coinbase']),))
        
        if len(self.merkle_link['branch']) > 16:
            raise ValueError('merkle branch too long!')
        
        assert not self.hash_link['extra_data'], repr(self.hash_link['extra_data'])
        
        self.share_data = self.share_info['share_data']
        self.max_target = self.share_info['max_bits'].target
        self.target = self.share_info['bits'].target
        self.timestamp = self.share_info['timestamp']
        self.previous_hash = self.share_data['previous_share_hash']
        self.new_script = bitcoin_data.pubkey_hash_to_script2(self.share_data['pubkey_hash'])
        self.desired_version = self.share_data['desired_version']
        self.absheight = self.share_info['absheight']
        self.abswork = self.share_info['abswork']
        
        n = set()
        for share_count, tx_count in self.iter_transaction_hash_refs():
            assert share_count < 110
            if share_count == 0:
                n.add(tx_count)
        assert n == set(range(len(self.share_info['new_transaction_hashes'])))
        
        self.gentx_hash = check_hash_link(
            self.hash_link,
            self.get_ref_hash(net, self.share_info, contents['ref_merkle_link']) + pack.IntType(64).pack(self.contents['last_txout_nonce']) + pack.IntType(32).pack(0),
            self.gentx_before_refhash,
        )
        merkle_root = bitcoin_data.check_merkle_link(self.gentx_hash, self.merkle_link)
        self.header = dict(self.min_header, merkle_root=merkle_root)
        self.pow_hash = net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(self.header))
        self.hash = self.header_hash = bitcoin_data.hash256(bitcoin_data.block_header_type.pack(self.header))
        
        if self.target > net.MAX_TARGET:
            from p2pool import p2p
            raise p2p.PeerMisbehavingError('share target invalid')
        
        if self.pow_hash > self.target:
            from p2pool import p2p
            raise p2p.PeerMisbehavingError('share PoW invalid')
        
        self.new_transaction_hashes = self.share_info['new_transaction_hashes']
        
        # XXX eww
        self.time_seen = time.time()
    
    def __repr__(self):
        return 'Share' + repr((self.net, self.peer_addr, self.contents))
    
    def as_share(self):
        return dict(type=self.VERSION, contents=self.share_type.pack(self.contents))
    
    def iter_transaction_hash_refs(self):
        return zip(self.share_info['transaction_hash_refs'][::2], self.share_info['transaction_hash_refs'][1::2])
    
    def check(self, tracker):
        from p2pool import p2p
        if self.share_data['previous_share_hash'] is not None:
            previous_share = tracker.items[self.share_data['previous_share_hash']]
            if type(self) is type(previous_share):
                pass
            elif type(self) is type(previous_share).SUCCESSOR:
                if tracker.get_height(previous_share.hash) < self.net.CHAIN_LENGTH:
                    from p2pool import p2p
                    raise p2p.PeerMisbehavingError('switch without enough history')
                
                # switch only valid if 85% of hashes in [self.net.CHAIN_LENGTH*9//10, self.net.CHAIN_LENGTH] for new version
                counts = get_desired_version_counts(tracker,
                    tracker.get_nth_parent_hash(previous_share.hash, self.net.CHAIN_LENGTH*9//10), self.net.CHAIN_LENGTH//10)
                if counts.get(self.VERSION, 0) < sum(counts.itervalues())*85//100:
                    raise p2p.PeerMisbehavingError('switch without enough hash power upgraded')
            else:
                raise p2p.PeerMisbehavingError('''%s can't follow %s''' % (type(self).__name__, type(previous_share).__name__))
        
        other_tx_hashes = [tracker.items[tracker.get_nth_parent_hash(self.hash, share_count)].share_info['new_transaction_hashes'][tx_count] for share_count, tx_count in self.iter_transaction_hash_refs()]
        
        share_info, gentx, other_tx_hashes2, get_share = self.generate_transaction(tracker, self.share_info['share_data'], self.header['bits'].target, self.share_info['timestamp'], self.share_info['bits'].target, self.contents['ref_merkle_link'], [(h, None) for h in other_tx_hashes], self.net, last_txout_nonce=self.contents['last_txout_nonce'])
        assert other_tx_hashes2 == other_tx_hashes
        if share_info != self.share_info:
            raise ValueError('share_info invalid')
        if bitcoin_data.hash256(bitcoin_data.tx_type.pack(gentx)) != self.gentx_hash:
            raise ValueError('''gentx doesn't match hash_link''')
        
        if bitcoin_data.calculate_merkle_link([None] + other_tx_hashes, 0) != self.merkle_link:
            raise ValueError('merkle_link and other_tx_hashes do not match')
        
        return gentx # only used by as_block
    
    def get_other_tx_hashes(self, tracker):
        parents_needed = max(share_count for share_count, tx_count in self.iter_transaction_hash_refs()) if self.share_info['transaction_hash_refs'] else 0
        parents = tracker.get_height(self.hash) - 1
        if parents < parents_needed:
            return None
        last_shares = list(tracker.get_chain(self.hash, parents_needed + 1))
        return [last_shares[share_count].share_info['new_transaction_hashes'][tx_count] for share_count, tx_count in self.iter_transaction_hash_refs()]
    
    def _get_other_txs(self, tracker, known_txs):
        other_tx_hashes = self.get_other_tx_hashes(tracker)
        if other_tx_hashes is None:
            return None # not all parents present
        
        if not all(tx_hash in known_txs for tx_hash in other_tx_hashes):
            return None # not all txs present
        
        return [known_txs[tx_hash] for tx_hash in other_tx_hashes]
    
    def should_punish_reason(self, previous_block, bits, tracker, known_txs):
        if (self.header['previous_block'], self.header['bits']) != (previous_block, bits) and self.header_hash != previous_block and self.peer_addr is not None:
            return True, 'Block-stale detected! height(%x) < height(%x) or %08x != %08x' % (self.header['previous_block'], previous_block, self.header['bits'].bits, bits.bits)
        
        if self.pow_hash <= self.header['bits'].target:
            return -1, 'block solution'
        
        other_txs = self._get_other_txs(tracker, known_txs)
        if other_txs is None:
            pass
        else:
            all_txs_size = sum(bitcoin_data.tx_type.packed_size(tx) for tx in other_txs)
            if all_txs_size > 1000000:
                return True, 'txs over block size limit'
            
            new_txs_size = sum(bitcoin_data.tx_type.packed_size(known_txs[tx_hash]) for tx_hash in self.share_info['new_transaction_hashes'])
            if new_txs_size > 50000:
                return True, 'new txs over limit'
        
        return False, None
    
    def as_block(self, tracker, known_txs):
        other_txs = self._get_other_txs(tracker, known_txs)
        if other_txs is None:
            return None # not all txs present
        return dict(header=self.header, txs=[self.check(tracker)] + other_txs)


class WeightsSkipList(forest.TrackerSkipList):
    # share_count, weights, total_weight
    
    def get_delta(self, element):
        from p2pool.bitcoin import data as bitcoin_data
        share = self.tracker.items[element]
        att = bitcoin_data.target_to_average_attempts(share.target)
        return 1, {share.new_script: att*(65535-share.share_data['donation'])}, att*65535, att*share.share_data['donation']
    
    def combine_deltas(self, (share_count1, weights1, total_weight1, total_donation_weight1), (share_count2, weights2, total_weight2, total_donation_weight2)):
        return share_count1 + share_count2, math.add_dicts(weights1, weights2), total_weight1 + total_weight2, total_donation_weight1 + total_donation_weight2
    
    def initial_solution(self, start, (max_shares, desired_weight)):
        assert desired_weight % 65535 == 0, divmod(desired_weight, 65535)
        return 0, None, 0, 0
    
    def apply_delta(self, (share_count1, weights_list, total_weight1, total_donation_weight1), (share_count2, weights2, total_weight2, total_donation_weight2), (max_shares, desired_weight)):
        if total_weight1 + total_weight2 > desired_weight and share_count2 == 1:
            assert (desired_weight - total_weight1) % 65535 == 0
            script, = weights2.iterkeys()
            new_weights = {script: (desired_weight - total_weight1)//65535*weights2[script]//(total_weight2//65535)}
            return share_count1 + share_count2, (weights_list, new_weights), desired_weight, total_donation_weight1 + (desired_weight - total_weight1)//65535*total_donation_weight2//(total_weight2//65535)
        return share_count1 + share_count2, (weights_list, weights2), total_weight1 + total_weight2, total_donation_weight1 + total_donation_weight2
    
    def judge(self, (share_count, weights_list, total_weight, total_donation_weight), (max_shares, desired_weight)):
        if share_count > max_shares or total_weight > desired_weight:
            return 1
        elif share_count == max_shares or total_weight == desired_weight:
            return 0
        else:
            return -1
    
    def finalize(self, (share_count, weights_list, total_weight, total_donation_weight), (max_shares, desired_weight)):
        assert share_count <= max_shares and total_weight <= desired_weight
        assert share_count == max_shares or total_weight == desired_weight
        return math.add_dicts(*math.flatten_linked_list(weights_list)), total_weight, total_donation_weight

class OkayTracker(forest.Tracker):
    def __init__(self, net):
        forest.Tracker.__init__(self, delta_type=forest.get_attributedelta_type(dict(forest.AttributeDelta.attrs,
            work=lambda share: bitcoin_data.target_to_average_attempts(share.target),
            min_work=lambda share: bitcoin_data.target_to_average_attempts(share.max_target),
        )))
        self.net = net
        self.verified = forest.SubsetTracker(delta_type=forest.get_attributedelta_type(dict(forest.AttributeDelta.attrs,
            work=lambda share: bitcoin_data.target_to_average_attempts(share.target),
        )), subset_of=self)
        self.get_cumulative_weights = WeightsSkipList(self)
    
    def attempt_verify(self, share):
        if share.hash in self.verified.items:
            return True
        height, last = self.get_height_and_last(share.hash)
        if height < self.net.CHAIN_LENGTH + 1 and last is not None:
            raise AssertionError()
        try:
            share.check(self)
        except:
            log.err(None, 'Share check failed: %064x -> %064x' % (share.hash, share.previous_hash if share.previous_hash is not None else 0))
            return False
        else:
            self.verified.add(share)
            return True
    
    def think(self, block_rel_height_func, previous_block, bits, known_txs):
        desired = set()
        bad_peer_addresses = set()
        
        # O(len(self.heads))
        #   make 'unverified heads' set?
        # for each overall head, attempt verification
        # if it fails, attempt on parent, and repeat
        # if no successful verification because of lack of parents, request parent
        bads = []
        for head in set(self.heads) - set(self.verified.heads):
            head_height, last = self.get_height_and_last(head)
            
            for share in self.get_chain(head, head_height if last is None else min(5, max(0, head_height - self.net.CHAIN_LENGTH))):
                if self.attempt_verify(share):
                    break
                bads.append(share.hash)
            else:
                if last is not None:
                    desired.add((
                        self.items[random.choice(list(self.reverse[last]))].peer_addr,
                        last,
                        max(x.timestamp for x in self.get_chain(head, min(head_height, 5))),
                        min(x.target for x in self.get_chain(head, min(head_height, 5))),
                    ))
        for bad in bads:
            assert bad not in self.verified.items
            #assert bad in self.heads
            bad_share = self.items[bad]
            if bad_share.peer_addr is not None:
                bad_peer_addresses.add(bad_share.peer_addr)
            if p2pool.DEBUG:
                print "BAD", bad
            try:
                self.remove(bad)
            except NotImplementedError:
                pass
        
        # try to get at least CHAIN_LENGTH height for each verified head, requesting parents if needed
        for head in list(self.verified.heads):
            head_height, last_hash = self.verified.get_height_and_last(head)
            last_height, last_last_hash = self.get_height_and_last(last_hash)
            # XXX review boundary conditions
            want = max(self.net.CHAIN_LENGTH - head_height, 0)
            can = max(last_height - 1 - self.net.CHAIN_LENGTH, 0) if last_last_hash is not None else last_height
            get = min(want, can)
            #print 'Z', head_height, last_hash is None, last_height, last_last_hash is None, want, can, get
            for share in self.get_chain(last_hash, get):
                if not self.attempt_verify(share):
                    break
            if head_height < self.net.CHAIN_LENGTH and last_last_hash is not None:
                desired.add((
                    self.items[random.choice(list(self.verified.reverse[last_hash]))].peer_addr,
                    last_last_hash,
                    max(x.timestamp for x in self.get_chain(head, min(head_height, 5))),
                    min(x.target for x in self.get_chain(head, min(head_height, 5))),
                ))
        
        # decide best tree
        decorated_tails = sorted((self.score(max(self.verified.tails[tail_hash], key=self.verified.get_work), block_rel_height_func), tail_hash) for tail_hash in self.verified.tails)
        if p2pool.DEBUG:
            print len(decorated_tails), 'tails:'
            for score, tail_hash in decorated_tails:
                print format_hash(tail_hash), score
        best_tail_score, best_tail = decorated_tails[-1] if decorated_tails else (None, None)
        
        # decide best verified head
        decorated_heads = sorted(((
            self.verified.get_work(self.verified.get_nth_parent_hash(h, min(5, self.verified.get_height(h)))),
            #self.items[h].peer_addr is None,
            -self.items[h].should_punish_reason(previous_block, bits, self, known_txs)[0],
            -self.items[h].time_seen,
        ), h) for h in self.verified.tails.get(best_tail, []))
        if p2pool.DEBUG:
            print len(decorated_heads), 'heads. Top 10:'
            for score, head_hash in decorated_heads[-10:]:
                print '   ', format_hash(head_hash), format_hash(self.items[head_hash].previous_hash), score
        best_head_score, best = decorated_heads[-1] if decorated_heads else (None, None)
        
        if best is not None:
            best_share = self.items[best]
            punish, punish_reason = best_share.should_punish_reason(previous_block, bits, self, known_txs)
            if punish > 0:
                print 'Punishing share for %r! Jumping from %s to %s!' % (punish_reason, format_hash(best), format_hash(best_share.previous_hash))
                best = best_share.previous_hash
            
            timestamp_cutoff = min(int(time.time()), best_share.timestamp) - 3600
            target_cutoff = int(2**256//(self.net.SHARE_PERIOD*best_tail_score[1] + 1) * 2 + .5) if best_tail_score[1] is not None else 2**256-1
        else:
            timestamp_cutoff = int(time.time()) - 24*60*60
            target_cutoff = 2**256-1
        
        if p2pool.DEBUG:
            print 'Desire %i shares. Cutoff: %s old diff>%.2f' % (len(desired), math.format_dt(time.time() - timestamp_cutoff), bitcoin_data.target_to_difficulty(target_cutoff))
            for peer_addr, hash, ts, targ in desired:
                print '   ', None if peer_addr is None else '%s:%i' % peer_addr, format_hash(hash), math.format_dt(time.time() - ts), bitcoin_data.target_to_difficulty(targ), ts >= timestamp_cutoff, targ <= target_cutoff
        
        return best, [(peer_addr, hash) for peer_addr, hash, ts, targ in desired if ts >= timestamp_cutoff], decorated_heads, bad_peer_addresses
    
    def score(self, share_hash, block_rel_height_func):
        # returns approximate lower bound on chain's hashrate in the last self.net.CHAIN_LENGTH*15//16*self.net.SHARE_PERIOD time
        
        head_height = self.verified.get_height(share_hash)
        if head_height < self.net.CHAIN_LENGTH:
            return head_height, None
        
        end_point = self.verified.get_nth_parent_hash(share_hash, self.net.CHAIN_LENGTH*15//16)
        
        block_height = max(block_rel_height_func(share.header['previous_block']) for share in
            self.verified.get_chain(end_point, self.net.CHAIN_LENGTH//16))
        
        return self.net.CHAIN_LENGTH, self.verified.get_delta(share_hash, end_point).work/((0 - block_height + 1)*self.net.PARENT.BLOCK_PERIOD)

def get_pool_attempts_per_second(tracker, previous_share_hash, dist, min_work=False, integer=False):
    assert dist >= 2
    near = tracker.items[previous_share_hash]
    far = tracker.items[tracker.get_nth_parent_hash(previous_share_hash, dist - 1)]
    attempts = tracker.get_delta(near.hash, far.hash).work if not min_work else tracker.get_delta(near.hash, far.hash).min_work
    time = near.timestamp - far.timestamp
    if time <= 0:
        time = 1
    if integer:
        return attempts//time
    return attempts/time

def get_average_stale_prop(tracker, share_hash, lookbehind):
    stales = sum(1 for share in tracker.get_chain(share_hash, lookbehind) if share.share_data['stale_info'] is not None)
    return stales/(lookbehind + stales)

def get_stale_counts(tracker, share_hash, lookbehind, rates=False):
    res = {}
    for share in tracker.get_chain(share_hash, lookbehind - 1):
        res['good'] = res.get('good', 0) + bitcoin_data.target_to_average_attempts(share.target)
        s = share.share_data['stale_info']
        if s is not None:
            res[s] = res.get(s, 0) + bitcoin_data.target_to_average_attempts(share.target)
    if rates:
        dt = tracker.items[share_hash].timestamp - tracker.items[tracker.get_nth_parent_hash(share_hash, lookbehind - 1)].timestamp
        res = dict((k, v/dt) for k, v in res.iteritems())
    return res

def get_user_stale_props(tracker, share_hash, lookbehind):
    res = {}
    for share in tracker.get_chain(share_hash, lookbehind - 1):
        stale, total = res.get(share.share_data['pubkey_hash'], (0, 0))
        total += 1
        if share.share_data['stale_info'] is not None:
            stale += 1
            total += 1
        res[share.share_data['pubkey_hash']] = stale, total
    return dict((pubkey_hash, stale/total) for pubkey_hash, (stale, total) in res.iteritems())

def get_expected_payouts(tracker, best_share_hash, block_target, subsidy, net):
    weights, total_weight, donation_weight = tracker.get_cumulative_weights(best_share_hash, min(tracker.get_height(best_share_hash), net.REAL_CHAIN_LENGTH), 65535*net.SPREAD*bitcoin_data.target_to_average_attempts(block_target))
    res = dict((script, subsidy*weight//total_weight) for script, weight in weights.iteritems())
    res[DONATION_SCRIPT] = res.get(DONATION_SCRIPT, 0) + subsidy - sum(res.itervalues())
    return res

def get_desired_version_counts(tracker, best_share_hash, dist):
    res = {}
    for share in tracker.get_chain(best_share_hash, dist):
        res[share.desired_version] = res.get(share.desired_version, 0) + bitcoin_data.target_to_average_attempts(share.target)
    return res

def get_warnings(tracker, best_share, net, bitcoind_getinfo, bitcoind_work_value):
    res = []
    
    desired_version_counts = get_desired_version_counts(tracker, best_share,
        min(net.CHAIN_LENGTH, 60*60//net.SHARE_PERIOD, tracker.get_height(best_share)))
    majority_desired_version = max(desired_version_counts, key=lambda k: desired_version_counts[k])
    if majority_desired_version > (Share.SUCCESSOR if Share.SUCCESSOR is not None else Share).VOTING_VERSION and desired_version_counts[majority_desired_version] > sum(desired_version_counts.itervalues())/2:
        res.append('A MAJORITY OF SHARES CONTAIN A VOTE FOR AN UNSUPPORTED SHARE IMPLEMENTATION! (v%i with %i%% support)\n'
            'An upgrade is likely necessary. Check http://p2pool.forre.st/ for more information.' % (
                majority_desired_version, 100*desired_version_counts[majority_desired_version]/sum(desired_version_counts.itervalues())))
    
    if bitcoind_getinfo['errors'] != '':
        if 'This is a pre-release test build' not in bitcoind_getinfo['errors']:
            res.append('(from bitcoind) %s' % (bitcoind_getinfo['errors'],))
    
    version_warning = getattr(net, 'VERSION_WARNING', lambda v: None)(bitcoind_getinfo['version'])
    if version_warning is not None:
        res.append(version_warning)
    
    if time.time() > bitcoind_work_value['last_update'] + 60:
        res.append('''LOST CONTACT WITH BITCOIND for %s! Check that it isn't frozen or dead!''' % (math.format_dt(time.time() - bitcoind_work_value['last_update']),))
    
    return res

def format_hash(x):
    if x is None:
        return 'xxxxxxxx'
    return '%08x' % (x % 2**32)

class ShareStore(object):
    def __init__(self, prefix, net, share_cb, verified_hash_cb):
        self.dirname = os.path.dirname(os.path.abspath(prefix))
        self.filename = os.path.basename(os.path.abspath(prefix))
        self.net = net
        
        known = {}
        filenames, next = self.get_filenames_and_next()
        for filename in filenames:
            share_hashes, verified_hashes = known.setdefault(filename, (set(), set()))
            with open(filename, 'rb') as f:
                for line in f:
                    try:
                        type_id_str, data_hex = line.strip().split(' ')
                        type_id = int(type_id_str)
                        if type_id == 0:
                            pass
                        elif type_id == 1:
                            pass
                        elif type_id == 2:
                            verified_hash = int(data_hex, 16)
                            verified_hash_cb(verified_hash)
                            verified_hashes.add(verified_hash)
                        elif type_id == 5:
                            raw_share = share_type.unpack(data_hex.decode('hex'))
                            if raw_share['type'] < Share.VERSION:
                                continue
                            share = load_share(raw_share, self.net, None)
                            share_cb(share)
                            share_hashes.add(share.hash)
                        else:
                            raise NotImplementedError("share type %i" % (type_id,))
                    except Exception:
                        log.err(None, "HARMLESS error while reading saved shares, continuing where left off:")
        
        self.known = known # filename -> (set of share hashes, set of verified hashes)
        self.known_desired = dict((k, (set(a), set(b))) for k, (a, b) in known.iteritems())
    
    def _add_line(self, line):
        filenames, next = self.get_filenames_and_next()
        if filenames and os.path.getsize(filenames[-1]) < 10e6:
            filename = filenames[-1]
        else:
            filename = next
        
        with open(filename, 'ab') as f:
            f.write(line + '\n')
        
        return filename
    
    def add_share(self, share):
        for filename, (share_hashes, verified_hashes) in self.known.iteritems():
            if share.hash in share_hashes:
                break
        else:
            filename = self._add_line("%i %s" % (5, share_type.pack(share.as_share()).encode('hex')))
            share_hashes, verified_hashes = self.known.setdefault(filename, (set(), set()))
            share_hashes.add(share.hash)
        share_hashes, verified_hashes = self.known_desired.setdefault(filename, (set(), set()))
        share_hashes.add(share.hash)
    
    def add_verified_hash(self, share_hash):
        for filename, (share_hashes, verified_hashes) in self.known.iteritems():
            if share_hash in verified_hashes:
                break
        else:
            filename = self._add_line("%i %x" % (2, share_hash))
            share_hashes, verified_hashes = self.known.setdefault(filename, (set(), set()))
            verified_hashes.add(share_hash)
        share_hashes, verified_hashes = self.known_desired.setdefault(filename, (set(), set()))
        verified_hashes.add(share_hash)
    
    def get_filenames_and_next(self):
        suffixes = sorted(int(x[len(self.filename):]) for x in os.listdir(self.dirname) if x.startswith(self.filename) and x[len(self.filename):].isdigit())
        return [os.path.join(self.dirname, self.filename + str(suffix)) for suffix in suffixes], os.path.join(self.dirname, self.filename + (str(suffixes[-1] + 1) if suffixes else str(0)))
    
    def forget_share(self, share_hash):
        for filename, (share_hashes, verified_hashes) in self.known_desired.iteritems():
            if share_hash in share_hashes:
                share_hashes.remove(share_hash)
        self.check_remove()
    
    def forget_verified_share(self, share_hash):
        for filename, (share_hashes, verified_hashes) in self.known_desired.iteritems():
            if share_hash in verified_hashes:
                verified_hashes.remove(share_hash)
        self.check_remove()
    
    def check_remove(self):
        to_remove = set()
        for filename, (share_hashes, verified_hashes) in self.known_desired.iteritems():
            #print filename, len(share_hashes) + len(verified_hashes)
            if not share_hashes and not verified_hashes:
                to_remove.add(filename)
        for filename in to_remove:
            self.known.pop(filename)
            self.known_desired.pop(filename)
            os.remove(filename)
            print "REMOVED", filename

########NEW FILE########
__FILENAME__ = main
from __future__ import division

import base64
import gc
import json
import os
import random
import sys
import time
import signal
import traceback
import urlparse

if '--iocp' in sys.argv:
    from twisted.internet import iocpreactor
    iocpreactor.install()
from twisted.internet import defer, reactor, protocol, tcp
from twisted.web import server
from twisted.python import log
from nattraverso import portmapper, ipdiscover

import bitcoin.p2p as bitcoin_p2p, bitcoin.data as bitcoin_data
from bitcoin import stratum, worker_interface, helper
from util import fixargparse, jsonrpc, variable, deferral, math, logging, switchprotocol
from . import networks, web, work
import p2pool, p2pool.data as p2pool_data, p2pool.node as p2pool_node

@defer.inlineCallbacks
def main(args, net, datadir_path, merged_urls, worker_endpoint):
    try:
        print 'p2pool (version %s)' % (p2pool.__version__,)
        print
        
        @defer.inlineCallbacks
        def connect_p2p():
            # connect to bitcoind over bitcoin-p2p
            print '''Testing bitcoind P2P connection to '%s:%s'...''' % (args.bitcoind_address, args.bitcoind_p2p_port)
            factory = bitcoin_p2p.ClientFactory(net.PARENT)
            reactor.connectTCP(args.bitcoind_address, args.bitcoind_p2p_port, factory)
            def long():
                print '''    ...taking a while. Common reasons for this include all of bitcoind's connection slots being used...'''
            long_dc = reactor.callLater(5, long)
            yield factory.getProtocol() # waits until handshake is successful
            if not long_dc.called: long_dc.cancel()
            print '    ...success!'
            print
            defer.returnValue(factory)
        
        if args.testnet: # establish p2p connection first if testnet so bitcoind can work without connections
            factory = yield connect_p2p()
        
        # connect to bitcoind over JSON-RPC and do initial getmemorypool
        url = '%s://%s:%i/' % ('https' if args.bitcoind_rpc_ssl else 'http', args.bitcoind_address, args.bitcoind_rpc_port)
        print '''Testing bitcoind RPC connection to '%s' with username '%s'...''' % (url, args.bitcoind_rpc_username)
        bitcoind = jsonrpc.HTTPProxy(url, dict(Authorization='Basic ' + base64.b64encode(args.bitcoind_rpc_username + ':' + args.bitcoind_rpc_password)), timeout=30)
        yield helper.check(bitcoind, net)
        temp_work = yield helper.getwork(bitcoind)
        
        bitcoind_getinfo_var = variable.Variable(None)
        @defer.inlineCallbacks
        def poll_warnings():
            bitcoind_getinfo_var.set((yield deferral.retry('Error while calling getinfo:')(bitcoind.rpc_getinfo)()))
        yield poll_warnings()
        deferral.RobustLoopingCall(poll_warnings).start(20*60)
        
        print '    ...success!'
        print '    Current block hash: %x' % (temp_work['previous_block'],)
        print '    Current block height: %i' % (temp_work['height'] - 1,)
        print
        
        if not args.testnet:
            factory = yield connect_p2p()
        
        print 'Determining payout address...'
        if args.pubkey_hash is None:
            address_path = os.path.join(datadir_path, 'cached_payout_address')
            
            if os.path.exists(address_path):
                with open(address_path, 'rb') as f:
                    address = f.read().strip('\r\n')
                print '    Loaded cached address: %s...' % (address,)
            else:
                address = None
            
            if address is not None:
                res = yield deferral.retry('Error validating cached address:', 5)(lambda: bitcoind.rpc_validateaddress(address))()
                if not res['isvalid'] or not res['ismine']:
                    print '    Cached address is either invalid or not controlled by local bitcoind!'
                    address = None
            
            if address is None:
                print '    Getting payout address from bitcoind...'
                address = yield deferral.retry('Error getting payout address from bitcoind:', 5)(lambda: bitcoind.rpc_getaccountaddress('p2pool'))()
            
            with open(address_path, 'wb') as f:
                f.write(address)
            
            my_pubkey_hash = bitcoin_data.address_to_pubkey_hash(address, net.PARENT)
        else:
            my_pubkey_hash = args.pubkey_hash
        print '    ...success! Payout address:', bitcoin_data.pubkey_hash_to_address(my_pubkey_hash, net.PARENT)
        print
        
        print "Loading shares..."
        shares = {}
        known_verified = set()
        def share_cb(share):
            share.time_seen = 0 # XXX
            shares[share.hash] = share
            if len(shares) % 1000 == 0 and shares:
                print "    %i" % (len(shares),)
        ss = p2pool_data.ShareStore(os.path.join(datadir_path, 'shares.'), net, share_cb, known_verified.add)
        print "    ...done loading %i shares (%i verified)!" % (len(shares), len(known_verified))
        print
        
        
        print 'Initializing work...'
        
        node = p2pool_node.Node(factory, bitcoind, shares.values(), known_verified, net)
        yield node.start()
        
        for share_hash in shares:
            if share_hash not in node.tracker.items:
                ss.forget_share(share_hash)
        for share_hash in known_verified:
            if share_hash not in node.tracker.verified.items:
                ss.forget_verified_share(share_hash)
        node.tracker.removed.watch(lambda share: ss.forget_share(share.hash))
        node.tracker.verified.removed.watch(lambda share: ss.forget_verified_share(share.hash))
        
        def save_shares():
            for share in node.tracker.get_chain(node.best_share_var.value, min(node.tracker.get_height(node.best_share_var.value), 2*net.CHAIN_LENGTH)):
                ss.add_share(share)
                if share.hash in node.tracker.verified.items:
                    ss.add_verified_hash(share.hash)
        deferral.RobustLoopingCall(save_shares).start(60)
        
        print '    ...success!'
        print
        
        
        print 'Joining p2pool network using port %i...' % (args.p2pool_port,)
        
        @defer.inlineCallbacks
        def parse(host):
            port = net.P2P_PORT
            if ':' in host:
                host, port_str = host.split(':')
                port = int(port_str)
            defer.returnValue(((yield reactor.resolve(host)), port))
        
        addrs = {}
        if os.path.exists(os.path.join(datadir_path, 'addrs')):
            try:
                with open(os.path.join(datadir_path, 'addrs'), 'rb') as f:
                    addrs.update(dict((tuple(k), v) for k, v in json.loads(f.read())))
            except:
                print >>sys.stderr, 'error parsing addrs'
        for addr_df in map(parse, net.BOOTSTRAP_ADDRS):
            try:
                addr = yield addr_df
                if addr not in addrs:
                    addrs[addr] = (0, time.time(), time.time())
            except:
                log.err()
        
        connect_addrs = set()
        for addr_df in map(parse, args.p2pool_nodes):
            try:
                connect_addrs.add((yield addr_df))
            except:
                log.err()
        
        node.p2p_node = p2pool_node.P2PNode(node,
            port=args.p2pool_port,
            max_incoming_conns=args.p2pool_conns,
            addr_store=addrs,
            connect_addrs=connect_addrs,
            desired_outgoing_conns=args.p2pool_outgoing_conns,
            advertise_ip=args.advertise_ip,
        )
        node.p2p_node.start()
        
        def save_addrs():
            with open(os.path.join(datadir_path, 'addrs'), 'wb') as f:
                f.write(json.dumps(node.p2p_node.addr_store.items()))
        deferral.RobustLoopingCall(save_addrs).start(60)
        
        print '    ...success!'
        print
        
        if args.upnp:
            @defer.inlineCallbacks
            def upnp_thread():
                while True:
                    try:
                        is_lan, lan_ip = yield ipdiscover.get_local_ip()
                        if is_lan:
                            pm = yield portmapper.get_port_mapper()
                            yield pm._upnp.add_port_mapping(lan_ip, args.p2pool_port, args.p2pool_port, 'p2pool', 'TCP')
                    except defer.TimeoutError:
                        pass
                    except:
                        if p2pool.DEBUG:
                            log.err(None, 'UPnP error:')
                    yield deferral.sleep(random.expovariate(1/120))
            upnp_thread()
        
        # start listening for workers with a JSON-RPC server
        
        print 'Listening for workers on %r port %i...' % (worker_endpoint[0], worker_endpoint[1])
        
        wb = work.WorkerBridge(node, my_pubkey_hash, args.donation_percentage, merged_urls, args.worker_fee)
        web_root = web.get_web_root(wb, datadir_path, bitcoind_getinfo_var)
        caching_wb = worker_interface.CachingWorkerBridge(wb)
        worker_interface.WorkerInterface(caching_wb).attach_to(web_root, get_handler=lambda request: request.redirect('static/'))
        web_serverfactory = server.Site(web_root)
        
        
        serverfactory = switchprotocol.FirstByteSwitchFactory({'{': stratum.StratumServerFactory(caching_wb)}, web_serverfactory)
        deferral.retry('Error binding to worker port:', traceback=False)(reactor.listenTCP)(worker_endpoint[1], serverfactory, interface=worker_endpoint[0])
        
        with open(os.path.join(os.path.join(datadir_path, 'ready_flag')), 'wb') as f:
            pass
        
        print '    ...success!'
        print
        
        
        # done!
        print 'Started successfully!'
        print 'Go to http://127.0.0.1:%i/ to view graphs and statistics!' % (worker_endpoint[1],)
        if args.donation_percentage > 1.1:
            print '''Donating %.1f%% of work towards P2Pool's development. Thanks for the tip!''' % (args.donation_percentage,)
        elif args.donation_percentage < .9:
            print '''Donating %.1f%% of work towards P2Pool's development. Please donate to encourage further development of P2Pool!''' % (args.donation_percentage,)
        else:
            print '''Donating %.1f%% of work towards P2Pool's development. Thank you!''' % (args.donation_percentage,)
            print 'You can increase this amount with --give-author argument! (or decrease it, if you must)'
        print
        
        
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, lambda signum, frame: reactor.callFromThread(
                sys.stderr.write, 'Watchdog timer went off at:\n' + ''.join(traceback.format_stack())
            ))
            signal.siginterrupt(signal.SIGALRM, False)
            deferral.RobustLoopingCall(signal.alarm, 30).start(1)
        
        if args.irc_announce:
            from twisted.words.protocols import irc
            class IRCClient(irc.IRCClient):
                nickname = 'p2pool%02i' % (random.randrange(100),)
                channel = net.ANNOUNCE_CHANNEL
                def lineReceived(self, line):
                    if p2pool.DEBUG:
                        print repr(line)
                    irc.IRCClient.lineReceived(self, line)
                def signedOn(self):
                    self.in_channel = False
                    irc.IRCClient.signedOn(self)
                    self.factory.resetDelay()
                    self.join(self.channel)
                    @defer.inlineCallbacks
                    def new_share(share):
                        if not self.in_channel:
                            return
                        if share.pow_hash <= share.header['bits'].target and abs(share.timestamp - time.time()) < 10*60:
                            yield deferral.sleep(random.expovariate(1/60))
                            message = '\x02%s BLOCK FOUND by %s! %s%064x' % (net.NAME.upper(), bitcoin_data.script2_to_address(share.new_script, net.PARENT), net.PARENT.BLOCK_EXPLORER_URL_PREFIX, share.header_hash)
                            if all('%x' % (share.header_hash,) not in old_message for old_message in self.recent_messages):
                                self.say(self.channel, message)
                                self._remember_message(message)
                    self.watch_id = node.tracker.verified.added.watch(new_share)
                    self.recent_messages = []
                def joined(self, channel):
                    self.in_channel = True
                def left(self, channel):
                    self.in_channel = False
                def _remember_message(self, message):
                    self.recent_messages.append(message)
                    while len(self.recent_messages) > 100:
                        self.recent_messages.pop(0)
                def privmsg(self, user, channel, message):
                    if channel == self.channel:
                        self._remember_message(message)
                def connectionLost(self, reason):
                    node.tracker.verified.added.unwatch(self.watch_id)
                    print 'IRC connection lost:', reason.getErrorMessage()
            class IRCClientFactory(protocol.ReconnectingClientFactory):
                protocol = IRCClient
            reactor.connectTCP("irc.freenode.net", 6667, IRCClientFactory(), bindAddress=(worker_endpoint[0], 0))
        
        @defer.inlineCallbacks
        def status_thread():
            last_str = None
            last_time = 0
            while True:
                yield deferral.sleep(3)
                try:
                    height = node.tracker.get_height(node.best_share_var.value)
                    this_str = 'P2Pool: %i shares in chain (%i verified/%i total) Peers: %i (%i incoming)' % (
                        height,
                        len(node.tracker.verified.items),
                        len(node.tracker.items),
                        len(node.p2p_node.peers),
                        sum(1 for peer in node.p2p_node.peers.itervalues() if peer.incoming),
                    ) + (' FDs: %i R/%i W' % (len(reactor.getReaders()), len(reactor.getWriters())) if p2pool.DEBUG else '')
                    
                    datums, dt = wb.local_rate_monitor.get_datums_in_last()
                    my_att_s = sum(datum['work']/dt for datum in datums)
                    my_shares_per_s = sum(datum['work']/dt/bitcoin_data.target_to_average_attempts(datum['share_target']) for datum in datums)
                    this_str += '\n Local: %sH/s in last %s Local dead on arrival: %s Expected time to share: %s' % (
                        math.format(int(my_att_s)),
                        math.format_dt(dt),
                        math.format_binomial_conf(sum(1 for datum in datums if datum['dead']), len(datums), 0.95),
                        math.format_dt(1/my_shares_per_s) if my_shares_per_s else '???',
                    )
                    
                    if height > 2:
                        (stale_orphan_shares, stale_doa_shares), shares, _ = wb.get_stale_counts()
                        stale_prop = p2pool_data.get_average_stale_prop(node.tracker, node.best_share_var.value, min(60*60//net.SHARE_PERIOD, height))
                        real_att_s = p2pool_data.get_pool_attempts_per_second(node.tracker, node.best_share_var.value, min(height - 1, 60*60//net.SHARE_PERIOD)) / (1 - stale_prop)
                        
                        this_str += '\n Shares: %i (%i orphan, %i dead) Stale rate: %s Efficiency: %s Current payout: %.4f %s' % (
                            shares, stale_orphan_shares, stale_doa_shares,
                            math.format_binomial_conf(stale_orphan_shares + stale_doa_shares, shares, 0.95),
                            math.format_binomial_conf(stale_orphan_shares + stale_doa_shares, shares, 0.95, lambda x: (1 - x)/(1 - stale_prop)),
                            node.get_current_txouts().get(bitcoin_data.pubkey_hash_to_script2(my_pubkey_hash), 0)*1e-8, net.PARENT.SYMBOL,
                        )
                        this_str += '\n Pool: %sH/s Stale rate: %.1f%% Expected time to block: %s' % (
                            math.format(int(real_att_s)),
                            100*stale_prop,
                            math.format_dt(2**256 / node.bitcoind_work.value['bits'].target / real_att_s),
                        )
                        
                        for warning in p2pool_data.get_warnings(node.tracker, node.best_share_var.value, net, bitcoind_getinfo_var.value, node.bitcoind_work.value):
                            print >>sys.stderr, '#'*40
                            print >>sys.stderr, '>>> Warning: ' + warning
                            print >>sys.stderr, '#'*40
                        
                        if gc.garbage:
                            print '%i pieces of uncollectable cyclic garbage! Types: %r' % (len(gc.garbage), map(type, gc.garbage))
                    
                    if this_str != last_str or time.time() > last_time + 15:
                        print this_str
                        last_str = this_str
                        last_time = time.time()
                except:
                    log.err()
        status_thread()
    except:
        reactor.stop()
        log.err(None, 'Fatal error:')

def run():
    if not hasattr(tcp.Client, 'abortConnection'):
        print "Twisted doesn't have abortConnection! Upgrade to a newer version of Twisted to avoid memory leaks!"
        print 'Pausing for 3 seconds...'
        time.sleep(3)
    
    realnets = dict((name, net) for name, net in networks.nets.iteritems() if '_testnet' not in name)
    
    parser = fixargparse.FixedArgumentParser(description='p2pool (version %s)' % (p2pool.__version__,), fromfile_prefix_chars='@')
    parser.add_argument('--version', action='version', version=p2pool.__version__)
    parser.add_argument('--net',
        help='use specified network (default: bitcoin)',
        action='store', choices=sorted(realnets), default='bitcoin', dest='net_name')
    parser.add_argument('--testnet',
        help='''use the network's testnet''',
        action='store_const', const=True, default=False, dest='testnet')
    parser.add_argument('--debug',
        help='enable debugging mode',
        action='store_const', const=True, default=False, dest='debug')
    parser.add_argument('-a', '--address',
        help='generate payouts to this address (default: <address requested from bitcoind>)',
        type=str, action='store', default=None, dest='address')
    parser.add_argument('--datadir',
        help='store data in this directory (default: <directory run_p2pool.py is in>/data)',
        type=str, action='store', default=None, dest='datadir')
    parser.add_argument('--logfile',
        help='''log to this file (default: data/<NET>/log)''',
        type=str, action='store', default=None, dest='logfile')
    parser.add_argument('--merged',
        help='call getauxblock on this url to get work for merged mining (example: http://ncuser:ncpass@127.0.0.1:10332/)',
        type=str, action='append', default=[], dest='merged_urls')
    parser.add_argument('--give-author', metavar='DONATION_PERCENTAGE',
        help='donate this percentage of work towards the development of p2pool (default: 1.0)',
        type=float, action='store', default=1.0, dest='donation_percentage')
    parser.add_argument('--iocp',
        help='use Windows IOCP API in order to avoid errors due to large number of sockets being open',
        action='store_true', default=False, dest='iocp')
    parser.add_argument('--irc-announce',
        help='announce any blocks found on irc://irc.freenode.net/#p2pool',
        action='store_true', default=False, dest='irc_announce')
    parser.add_argument('--no-bugreport',
        help='disable submitting caught exceptions to the author',
        action='store_true', default=False, dest='no_bugreport')
    
    p2pool_group = parser.add_argument_group('p2pool interface')
    p2pool_group.add_argument('--p2pool-port', metavar='PORT',
        help='use port PORT to listen for connections (forward this port from your router!) (default: %s)' % ', '.join('%s:%i' % (name, net.P2P_PORT) for name, net in sorted(realnets.items())),
        type=int, action='store', default=None, dest='p2pool_port')
    p2pool_group.add_argument('-n', '--p2pool-node', metavar='ADDR[:PORT]',
        help='connect to existing p2pool node at ADDR listening on port PORT (defaults to default p2pool P2P port) in addition to builtin addresses',
        type=str, action='append', default=[], dest='p2pool_nodes')
    parser.add_argument('--disable-upnp',
        help='''don't attempt to use UPnP to forward p2pool's P2P port from the Internet to this computer''',
        action='store_false', default=True, dest='upnp')
    p2pool_group.add_argument('--max-conns', metavar='CONNS',
        help='maximum incoming connections (default: 40)',
        type=int, action='store', default=40, dest='p2pool_conns')
    p2pool_group.add_argument('--outgoing-conns', metavar='CONNS',
        help='outgoing connections (default: 6)',
        type=int, action='store', default=6, dest='p2pool_outgoing_conns')
    parser.add_argument('--disable-advertise',
        help='''don't advertise local IP address as being available for incoming connections. useful for running a dark node, along with multiple -n ADDR's and --outgoing-conns 0''',
        action='store_false', default=True, dest='advertise_ip')
    
    worker_group = parser.add_argument_group('worker interface')
    worker_group.add_argument('-w', '--worker-port', metavar='PORT or ADDR:PORT',
        help='listen on PORT on interface with ADDR for RPC connections from miners (default: all interfaces, %s)' % ', '.join('%s:%i' % (name, net.WORKER_PORT) for name, net in sorted(realnets.items())),
        type=str, action='store', default=None, dest='worker_endpoint')
    worker_group.add_argument('-f', '--fee', metavar='FEE_PERCENTAGE',
        help='''charge workers mining to their own bitcoin address (by setting their miner's username to a bitcoin address) this percentage fee to mine on your p2pool instance. Amount displayed at http://127.0.0.1:WORKER_PORT/fee (default: 0)''',
        type=float, action='store', default=0, dest='worker_fee')
    
    bitcoind_group = parser.add_argument_group('bitcoind interface')
    bitcoind_group.add_argument('--bitcoind-address', metavar='BITCOIND_ADDRESS',
        help='connect to this address (default: 127.0.0.1)',
        type=str, action='store', default='127.0.0.1', dest='bitcoind_address')
    bitcoind_group.add_argument('--bitcoind-rpc-port', metavar='BITCOIND_RPC_PORT',
        help='''connect to JSON-RPC interface at this port (default: %s <read from bitcoin.conf if password not provided>)''' % ', '.join('%s:%i' % (name, net.PARENT.RPC_PORT) for name, net in sorted(realnets.items())),
        type=int, action='store', default=None, dest='bitcoind_rpc_port')
    bitcoind_group.add_argument('--bitcoind-rpc-ssl',
        help='connect to JSON-RPC interface using SSL',
        action='store_true', default=False, dest='bitcoind_rpc_ssl')
    bitcoind_group.add_argument('--bitcoind-p2p-port', metavar='BITCOIND_P2P_PORT',
        help='''connect to P2P interface at this port (default: %s <read from bitcoin.conf if password not provided>)''' % ', '.join('%s:%i' % (name, net.PARENT.P2P_PORT) for name, net in sorted(realnets.items())),
        type=int, action='store', default=None, dest='bitcoind_p2p_port')
    
    bitcoind_group.add_argument(metavar='BITCOIND_RPCUSERPASS',
        help='bitcoind RPC interface username, then password, space-separated (only one being provided will cause the username to default to being empty, and none will cause P2Pool to read them from bitcoin.conf)',
        type=str, action='store', default=[], nargs='*', dest='bitcoind_rpc_userpass')
    
    args = parser.parse_args()
    
    if args.debug:
        p2pool.DEBUG = True
        defer.setDebugging(True)
    else:
        p2pool.DEBUG = False
    
    net_name = args.net_name + ('_testnet' if args.testnet else '')
    net = networks.nets[net_name]
    
    datadir_path = os.path.join((os.path.join(os.path.dirname(sys.argv[0]), 'data') if args.datadir is None else args.datadir), net_name)
    if not os.path.exists(datadir_path):
        os.makedirs(datadir_path)
    
    if len(args.bitcoind_rpc_userpass) > 2:
        parser.error('a maximum of two arguments are allowed')
    args.bitcoind_rpc_username, args.bitcoind_rpc_password = ([None, None] + args.bitcoind_rpc_userpass)[-2:]
    
    if args.bitcoind_rpc_password is None:
        conf_path = net.PARENT.CONF_FILE_FUNC()
        if not os.path.exists(conf_path):
            parser.error('''Bitcoin configuration file not found. Manually enter your RPC password.\r\n'''
                '''If you actually haven't created a configuration file, you should create one at %s with the text:\r\n'''
                '''\r\n'''
                '''server=1\r\n'''
                '''rpcpassword=%x\r\n'''
                '''\r\n'''
                '''Keep that password secret! After creating the file, restart Bitcoin.''' % (conf_path, random.randrange(2**128)))
        conf = open(conf_path, 'rb').read()
        contents = {}
        for line in conf.splitlines(True):
            if '#' in line:
                line = line[:line.index('#')]
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            contents[k.strip()] = v.strip()
        for conf_name, var_name, var_type in [
            ('rpcuser', 'bitcoind_rpc_username', str),
            ('rpcpassword', 'bitcoind_rpc_password', str),
            ('rpcport', 'bitcoind_rpc_port', int),
            ('port', 'bitcoind_p2p_port', int),
        ]:
            if getattr(args, var_name) is None and conf_name in contents:
                setattr(args, var_name, var_type(contents[conf_name]))
        if args.bitcoind_rpc_password is None:
            parser.error('''Bitcoin configuration file didn't contain an rpcpassword= line! Add one!''')
    
    if args.bitcoind_rpc_username is None:
        args.bitcoind_rpc_username = ''
    
    if args.bitcoind_rpc_port is None:
        args.bitcoind_rpc_port = net.PARENT.RPC_PORT
    
    if args.bitcoind_p2p_port is None:
        args.bitcoind_p2p_port = net.PARENT.P2P_PORT
    
    if args.p2pool_port is None:
        args.p2pool_port = net.P2P_PORT
    
    if args.p2pool_outgoing_conns > 10:
        parser.error('''--outgoing-conns can't be more than 10''')
    
    if args.worker_endpoint is None:
        worker_endpoint = '', net.WORKER_PORT
    elif ':' not in args.worker_endpoint:
        worker_endpoint = '', int(args.worker_endpoint)
    else:
        addr, port = args.worker_endpoint.rsplit(':', 1)
        worker_endpoint = addr, int(port)
    
    if args.address is not None:
        try:
            args.pubkey_hash = bitcoin_data.address_to_pubkey_hash(args.address, net.PARENT)
        except Exception, e:
            parser.error('error parsing address: ' + repr(e))
    else:
        args.pubkey_hash = None
    
    def separate_url(url):
        s = urlparse.urlsplit(url)
        if '@' not in s.netloc:
            parser.error('merged url netloc must contain an "@"')
        userpass, new_netloc = s.netloc.rsplit('@', 1)
        return urlparse.urlunsplit(s._replace(netloc=new_netloc)), userpass
    merged_urls = map(separate_url, args.merged_urls)
    
    if args.logfile is None:
        args.logfile = os.path.join(datadir_path, 'log')
    
    logfile = logging.LogFile(args.logfile)
    pipe = logging.TimestampingPipe(logging.TeePipe([logging.EncodeReplacerPipe(sys.stderr), logfile]))
    sys.stdout = logging.AbortPipe(pipe)
    sys.stderr = log.DefaultObserver.stderr = logging.AbortPipe(logging.PrefixPipe(pipe, '> '))
    if hasattr(signal, "SIGUSR1"):
        def sigusr1(signum, frame):
            print 'Caught SIGUSR1, closing %r...' % (args.logfile,)
            logfile.reopen()
            print '...and reopened %r after catching SIGUSR1.' % (args.logfile,)
        signal.signal(signal.SIGUSR1, sigusr1)
    deferral.RobustLoopingCall(logfile.reopen).start(5)
    
    class ErrorReporter(object):
        def __init__(self):
            self.last_sent = None
        
        def emit(self, eventDict):
            if not eventDict["isError"]:
                return
            
            if self.last_sent is not None and time.time() < self.last_sent + 5:
                return
            self.last_sent = time.time()
            
            if 'failure' in eventDict:
                text = ((eventDict.get('why') or 'Unhandled Error')
                    + '\n' + eventDict['failure'].getTraceback())
            else:
                text = " ".join([str(m) for m in eventDict["message"]]) + "\n"
            
            from twisted.web import client
            client.getPage(
                url='http://u.forre.st/p2pool_error.cgi',
                method='POST',
                postdata=p2pool.__version__ + ' ' + net.NAME + '\n' + text,
                timeout=15,
            ).addBoth(lambda x: None)
    if not args.no_bugreport:
        log.addObserver(ErrorReporter().emit)
    
    reactor.callWhenRunning(main, args, net, datadir_path, merged_urls, worker_endpoint)
    reactor.run()

########NEW FILE########
__FILENAME__ = networks
from p2pool.bitcoin import networks
from p2pool.util import math

# CHAIN_LENGTH = number of shares back client keeps
# REAL_CHAIN_LENGTH = maximum number of shares back client uses to compute payout
# REAL_CHAIN_LENGTH must always be <= CHAIN_LENGTH
# REAL_CHAIN_LENGTH must be changed in sync with all other clients
# changes can be done by changing one, then the other

nets = dict(
    bitcoin=math.Object(
        PARENT=networks.nets['bitcoin'],
        SHARE_PERIOD=30, # seconds
        CHAIN_LENGTH=24*60*60//10, # shares
        REAL_CHAIN_LENGTH=24*60*60//10, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=3, # blocks
        IDENTIFIER='fc70035c7a81bc6f'.decode('hex'),
        PREFIX='2472ef181efcd37b'.decode('hex'),
        P2P_PORT=9333,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**32 - 1,
        PERSIST=True,
        WORKER_PORT=9332,
        BOOTSTRAP_ADDRS='forre.st vps.forre.st portals94.ns01.us 54.227.25.14 119.1.96.99 204.10.105.113 76.104.150.248 89.71.151.9 76.114.13.54 72.201.24.106 79.160.2.128 207.244.175.195 168.7.116.243 94.23.215.27 218.54.45.177 5.9.157.150 78.155.217.76 91.154.90.163 173.52.43.124 78.225.49.209 220.135.57.230 169.237.101.193:8335 98.236.74.28 204.19.23.19 98.122.165.84:8338 71.90.88.222 67.168.132.228 193.6.148.18 80.218.174.253 50.43.56.102 68.13.4.106 24.246.31.2 176.31.208.222 1.202.128.218 86.155.135.31 204.237.15.51 5.12.158.126:38007 202.60.68.242 94.19.53.147 65.130.126.82 184.56.21.182 213.112.114.73 218.242.51.246 86.173.200.160 204.15.85.157 37.59.15.50 62.217.124.203 80.87.240.47 198.61.137.12 108.161.134.32 198.154.60.183:10333 71.39.52.34:9335 46.23.72.52:9343 83.143.42.177 192.95.61.149 144.76.17.34 46.65.68.119 188.227.176.66:9336 75.142.155.245:9336 213.67.135.99 76.115.224.177 50.148.193.245 64.53.185.79 80.65.30.137 109.126.14.42 76.84.63.146'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool',
        VERSION_CHECK=lambda v: 50700 <= v < 60000 or 60010 <= v < 60100 or 60400 <= v,
        VERSION_WARNING=lambda v: 'Upgrade Bitcoin to >=0.8.5!' if v < 80500 else None,
    ),
    bitcoin_testnet=math.Object(
        PARENT=networks.nets['bitcoin_testnet'],
        SHARE_PERIOD=30, # seconds
        CHAIN_LENGTH=60*60//10, # shares
        REAL_CHAIN_LENGTH=60*60//10, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=3, # blocks
        IDENTIFIER='5fc2be2d4f0d6bfb'.decode('hex'),
        PREFIX='3f6057a15036f441'.decode('hex'),
        P2P_PORT=19333,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**32 - 1,
        PERSIST=False,
        WORKER_PORT=19332,
        BOOTSTRAP_ADDRS='forre.st vps.forre.st liteco.in'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-alt',
        VERSION_CHECK=lambda v: 50700 <= v < 60000 or 60010 <= v < 60100 or 60400 <= v,
    ),
    
    litecoin=math.Object(
        PARENT=networks.nets['litecoin'],
        SHARE_PERIOD=15, # seconds
        CHAIN_LENGTH=24*60*60//10, # shares
        REAL_CHAIN_LENGTH=24*60*60//10, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=3, # blocks
        IDENTIFIER='e037d5b8c6923410'.decode('hex'),
        PREFIX='7208c1a53ef629b0'.decode('hex'),
        P2P_PORT=9338,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**20 - 1,
        PERSIST=True,
        WORKER_PORT=9327,
        BOOTSTRAP_ADDRS='forre.st vps.forre.st liteco.in 95.211.21.103 37.229.117.57 66.228.48.21 180.169.60.179 112.84.181.102 74.214.62.115 209.141.46.154 78.27.191.182 66.187.70.88 88.190.223.96 78.47.242.59 158.182.39.43 180.177.114.80 216.230.232.35 94.231.56.87 62.38.194.17 82.67.167.12 183.129.157.220 71.19.240.182 216.177.81.88 109.106.0.130 113.10.168.210 218.22.102.12 85.69.35.7:54396 201.52.162.167 95.66.173.110:8331 109.65.171.93 95.243.237.90 208.68.17.67 87.103.197.163 101.1.25.211 144.76.17.34 209.99.52.72 198.23.245.250 46.151.21.226 66.43.209.193 59.127.188.231 178.194.42.169 85.10.35.90 110.175.53.212 98.232.129.196 116.228.192.46 94.251.42.75 195.216.115.94 24.49.138.81 61.158.7.36 213.168.187.27 37.59.10.166 72.44.88.49 98.221.44.200 178.19.104.251 87.198.219.221 85.237.59.130:9310 218.16.251.86 151.236.11.119 94.23.215.27 60.190.203.228 176.31.208.222 46.163.105.201 198.84.186.74 199.175.50.102 188.142.102.15 202.191.108.46 125.65.108.19 15.185.107.232 108.161.131.248 188.116.33.39 78.142.148.62 69.42.217.130 213.110.14.23 185.10.51.18 74.71.113.207 77.89.41.253 69.171.153.219 58.210.42.10 174.107.165.198 50.53.105.6 116.213.73.50 83.150.90.211 210.28.136.11 86.58.41.122 70.63.34.88 78.155.217.76 68.193.128.182 198.199.73.40 193.6.148.18 188.177.188.189 83.109.6.82 204.10.105.113 64.91.214.180 46.4.74.44 98.234.11.149 71.189.207.226'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-ltc',
        VERSION_CHECK=lambda v: True,
        VERSION_WARNING=lambda v: 'Upgrade Litecoin to >=0.8.5.1!' if v < 80501 else None,
    ),
    litecoin_testnet=math.Object(
        PARENT=networks.nets['litecoin_testnet'],
        SHARE_PERIOD=4, # seconds
        CHAIN_LENGTH=20*60//3, # shares
        REAL_CHAIN_LENGTH=20*60//3, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=3, # blocks
        IDENTIFIER='cca5e24ec6408b1e'.decode('hex'),
        PREFIX='ad9614f6466a39cf'.decode('hex'),
        P2P_PORT=19338,
        MIN_TARGET=2**256//50 - 1,
        MAX_TARGET=2**256//50 - 1,
        PERSIST=False,
        WORKER_PORT=19327,
        BOOTSTRAP_ADDRS='forre.st vps.forre.st'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-alt',
        VERSION_CHECK=lambda v: True,
    ),

    terracoin=math.Object(
        PARENT=networks.nets['terracoin'],
        SHARE_PERIOD=30, # seconds
        CHAIN_LENGTH=24*60*60//30, # shares
        REAL_CHAIN_LENGTH=24*60*60//30, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=15, # blocks
        IDENTIFIER='a41b2356a1b7d46e'.decode('hex'),
        PREFIX='5623b62178d2b9b3'.decode('hex'),
        P2P_PORT=9323,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**32 - 1,
        PERSIST=True,
        WORKER_PORT=9322,
        BOOTSTRAP_ADDRS='seed1.p2pool.terracoin.org seed2.p2pool.terracoin.org forre.st vps.forre.st 93.97.192.93 66.90.73.83 67.83.108.0 219.84.64.174 24.167.17.248 109.74.195.142 83.211.86.49 94.23.34.145 168.7.116.243 94.174.40.189:9344 89.79.79.195 portals94.ns01.us'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-alt',
        VERSION_CHECK=lambda v: 80002 <= v,
        VERSION_WARNING=lambda v: 'Upgrade Terracoin to >= 0.8.0.2!' if v < 80002 else None,
    ),
    terracoin_testnet=math.Object(
        PARENT=networks.nets['terracoin_testnet'],
        SHARE_PERIOD=30, # seconds
        CHAIN_LENGTH=60*60//30, # shares
        REAL_CHAIN_LENGTH=60*60//30, # shares
        TARGET_LOOKBEHIND=200, # shares
        SPREAD=15, # blocks
        IDENTIFIER='b41b2356a5b7d35d'.decode('hex'),
        PREFIX='1623b92172d2b8a2'.decode('hex'),
        P2P_PORT=19323,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**32 - 1,
        PERSIST=False,
        WORKER_PORT=19322,
        BOOTSTRAP_ADDRS='seed1.p2pool.terracoin.org seed2.p2pool.terracoin.org forre.st vps.forre.st'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-alt',
        VERSION_CHECK=lambda v: True,
        VERSION_WARNING=lambda v: 'Upgrade Terracoin to >= 0.8.0.1!' if v < 80001 else None,
    ),
    fastcoin=math.Object(
        PARENT=networks.nets['fastcoin'],
        SHARE_PERIOD=6, # seconds
        NEW_SHARE_PERIOD=6, # seconds
        CHAIN_LENGTH=24*60*60//10, # shares
        REAL_CHAIN_LENGTH=24*60*60//10, # shares
        TARGET_LOOKBEHIND=60, # shares
        SPREAD=150, # blocks
        NEW_SPREAD=150, # blocks
        IDENTIFIER='9f2e390aa41ffade'.decode('hex'),
        PREFIX='50f713ab040dfade'.decode('hex'),
        P2P_PORT=23660,
        MIN_TARGET=0,
        MAX_TARGET=2**256//2**20 - 1,
        PERSIST=True,
        WORKER_PORT=5150,
        BOOTSTRAP_ADDRS='fst.inetrader.com'.split(' '),
        ANNOUNCE_CHANNEL='#p2pool-fst',
        VERSION_CHECK=lambda v: True,
        VERSION_WARNING=lambda v: 'Upgrade Fastcoin to >= 0.8.5.1!' if v < 70002 else None,
    ),

)
for net_name, net in nets.iteritems():
    net.NAME = net_name

########NEW FILE########
__FILENAME__ = node
import random
import sys
import time

from twisted.internet import defer, reactor
from twisted.python import log

from p2pool import data as p2pool_data, p2p
from p2pool.bitcoin import data as bitcoin_data, helper, height_tracker
from p2pool.util import deferral, variable


class P2PNode(p2p.Node):
    def __init__(self, node, **kwargs):
        self.node = node
        p2p.Node.__init__(self,
            best_share_hash_func=lambda: node.best_share_var.value,
            net=node.net,
            known_txs_var=node.known_txs_var,
            mining_txs_var=node.mining_txs_var,
        **kwargs)
    
    def handle_shares(self, shares, peer):
        if len(shares) > 5:
            print 'Processing %i shares from %s...' % (len(shares), '%s:%i' % peer.addr if peer is not None else None)
        
        new_count = 0
        all_new_txs = {}
        for share, new_txs in shares:
            if new_txs is not None:
                all_new_txs.update((bitcoin_data.hash256(bitcoin_data.tx_type.pack(new_tx)), new_tx) for new_tx in new_txs)
            
            if share.hash in self.node.tracker.items:
                #print 'Got duplicate share, ignoring. Hash: %s' % (p2pool_data.format_hash(share.hash),)
                continue
            
            new_count += 1
            
            #print 'Received share %s from %r' % (p2pool_data.format_hash(share.hash), share.peer_addr)
            
            self.node.tracker.add(share)
        
        new_known_txs = dict(self.node.known_txs_var.value)
        new_known_txs.update(all_new_txs)
        self.node.known_txs_var.set(new_known_txs)
        
        if new_count:
            self.node.set_best_share()
        
        if len(shares) > 5:
            print '... done processing %i shares. New: %i Have: %i/~%i' % (len(shares), new_count, len(self.node.tracker.items), 2*self.node.net.CHAIN_LENGTH)
    
    @defer.inlineCallbacks
    def handle_share_hashes(self, hashes, peer):
        new_hashes = [x for x in hashes if x not in self.node.tracker.items]
        if not new_hashes:
            return
        try:
            shares = yield peer.get_shares(
                hashes=new_hashes,
                parents=0,
                stops=[],
            )
        except:
            log.err(None, 'in handle_share_hashes:')
        else:
            self.handle_shares([(share, []) for share in shares], peer)
    
    def handle_get_shares(self, hashes, parents, stops, peer):
        parents = min(parents, 1000//len(hashes))
        stops = set(stops)
        shares = []
        for share_hash in hashes:
            for share in self.node.tracker.get_chain(share_hash, min(parents + 1, self.node.tracker.get_height(share_hash))):
                if share.hash in stops:
                    break
                shares.append(share)
        if len(shares) > 0:
            print 'Sending %i shares to %s:%i' % (len(shares), peer.addr[0], peer.addr[1])
        return shares
    
    def handle_bestblock(self, header, peer):
        if self.node.net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(header)) > header['bits'].target:
            raise p2p.PeerMisbehavingError('received block header fails PoW test')
        self.node.handle_header(header)
    
    def broadcast_share(self, share_hash):
        shares = []
        for share in self.node.tracker.get_chain(share_hash, min(5, self.node.tracker.get_height(share_hash))):
            if share.hash in self.shared_share_hashes:
                break
            self.shared_share_hashes.add(share.hash)
            shares.append(share)
        
        for peer in self.peers.itervalues():
            peer.sendShares([share for share in shares if share.peer_addr != peer.addr], self.node.tracker, self.node.known_txs_var.value, include_txs_with=[share_hash])
    
    def start(self):
        p2p.Node.start(self)
        
        self.shared_share_hashes = set(self.node.tracker.items)
        self.node.tracker.removed.watch_weakref(self, lambda self, share: self.shared_share_hashes.discard(share.hash))
        
        @apply
        @defer.inlineCallbacks
        def download_shares():
            while True:
                desired = yield self.node.desired_var.get_when_satisfies(lambda val: len(val) != 0)
                peer_addr, share_hash = random.choice(desired)
                
                if len(self.peers) == 0:
                    yield deferral.sleep(1)
                    continue
                peer = random.choice(self.peers.values())
                
                print 'Requesting parent share %s from %s' % (p2pool_data.format_hash(share_hash), '%s:%i' % peer.addr)
                try:
                    shares = yield peer.get_shares(
                        hashes=[share_hash],
                        parents=random.randrange(500), # randomize parents so that we eventually get past a too large block of shares
                        stops=list(set(self.node.tracker.heads) | set(
                            self.node.tracker.get_nth_parent_hash(head, min(max(0, self.node.tracker.get_height_and_last(head)[0] - 1), 10)) for head in self.node.tracker.heads
                        ))[:100],
                    )
                except defer.TimeoutError:
                    print 'Share request timed out!'
                    continue
                except:
                    log.err(None, 'in download_shares:')
                    continue
                
                if not shares:
                    yield deferral.sleep(1) # sleep so we don't keep rerequesting the same share nobody has
                    continue
                self.handle_shares([(share, []) for share in shares], peer)
        
        
        @self.node.best_block_header.changed.watch
        def _(header):
            for peer in self.peers.itervalues():
                peer.send_bestblock(header=header)
        
        # send share when the chain changes to their chain
        self.node.best_share_var.changed.watch(self.broadcast_share)
        
        @self.node.tracker.verified.added.watch
        def _(share):
            if not (share.pow_hash <= share.header['bits'].target):
                return
            
            def spread():
                if (self.node.get_height_rel_highest(share.header['previous_block']) > -5 or
                    self.node.bitcoind_work.value['previous_block'] in [share.header['previous_block'], share.header_hash]):
                    self.broadcast_share(share.hash)
            spread()
            reactor.callLater(5, spread) # so get_height_rel_highest can update
        

class Node(object):
    def __init__(self, factory, bitcoind, shares, known_verified_share_hashes, net):
        self.factory = factory
        self.bitcoind = bitcoind
        self.net = net
        
        self.tracker = p2pool_data.OkayTracker(self.net)
        
        for share in shares:
            self.tracker.add(share)
        
        for share_hash in known_verified_share_hashes:
            if share_hash in self.tracker.items:
                self.tracker.verified.add(self.tracker.items[share_hash])
        
        self.p2p_node = None # overwritten externally
    
    @defer.inlineCallbacks
    def start(self):
        stop_signal = variable.Event()
        self.stop = stop_signal.happened
        
        # BITCOIND WORK
        
        self.bitcoind_work = variable.Variable((yield helper.getwork(self.bitcoind)))
        @defer.inlineCallbacks
        def work_poller():
            while stop_signal.times == 0:
                flag = self.factory.new_block.get_deferred()
                try:
                    self.bitcoind_work.set((yield helper.getwork(self.bitcoind, self.bitcoind_work.value['use_getblocktemplate'])))
                except:
                    log.err()
                yield defer.DeferredList([flag, deferral.sleep(15)], fireOnOneCallback=True)
        work_poller()
        
        # PEER WORK
        
        self.best_block_header = variable.Variable(None)
        def handle_header(new_header):
            # check that header matches current target
            if not (self.net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(new_header)) <= self.bitcoind_work.value['bits'].target):
                return
            bitcoind_best_block = self.bitcoind_work.value['previous_block']
            if (self.best_block_header.value is None
                or (
                    new_header['previous_block'] == bitcoind_best_block and
                    bitcoin_data.hash256(bitcoin_data.block_header_type.pack(self.best_block_header.value)) == bitcoind_best_block
                ) # new is child of current and previous is current
                or (
                    bitcoin_data.hash256(bitcoin_data.block_header_type.pack(new_header)) == bitcoind_best_block and
                    self.best_block_header.value['previous_block'] != bitcoind_best_block
                )): # new is current and previous is not a child of current
                self.best_block_header.set(new_header)
        self.handle_header = handle_header
        @defer.inlineCallbacks
        def poll_header():
            if self.factory.conn.value is None:
                return
            handle_header((yield self.factory.conn.value.get_block_header(self.bitcoind_work.value['previous_block'])))
        self.bitcoind_work.changed.watch(lambda _: poll_header())
        yield deferral.retry('Error while requesting best block header:')(poll_header)()
        
        # BEST SHARE
        
        self.known_txs_var = variable.Variable({}) # hash -> tx
        self.mining_txs_var = variable.Variable({}) # hash -> tx
        self.get_height_rel_highest = yield height_tracker.get_height_rel_highest_func(self.bitcoind, self.factory, lambda: self.bitcoind_work.value['previous_block'], self.net)
        
        self.best_share_var = variable.Variable(None)
        self.desired_var = variable.Variable(None)
        self.bitcoind_work.changed.watch(lambda _: self.set_best_share())
        self.set_best_share()
        
        # setup p2p logic and join p2pool network
        
        # update mining_txs according to getwork results
        @self.bitcoind_work.changed.run_and_watch
        def _(_=None):
            new_mining_txs = {}
            new_known_txs = dict(self.known_txs_var.value)
            for tx_hash, tx in zip(self.bitcoind_work.value['transaction_hashes'], self.bitcoind_work.value['transactions']):
                new_mining_txs[tx_hash] = tx
                new_known_txs[tx_hash] = tx
            self.mining_txs_var.set(new_mining_txs)
            self.known_txs_var.set(new_known_txs)
        # add p2p transactions from bitcoind to known_txs
        @self.factory.new_tx.watch
        def _(tx):
            new_known_txs = dict(self.known_txs_var.value)
            new_known_txs[bitcoin_data.hash256(bitcoin_data.tx_type.pack(tx))] = tx
            self.known_txs_var.set(new_known_txs)
        # forward transactions seen to bitcoind
        @self.known_txs_var.transitioned.watch
        @defer.inlineCallbacks
        def _(before, after):
            yield deferral.sleep(random.expovariate(1/1))
            if self.factory.conn.value is None:
                return
            for tx_hash in set(after) - set(before):
                self.factory.conn.value.send_tx(tx=after[tx_hash])
        
        @self.tracker.verified.added.watch
        def _(share):
            if not (share.pow_hash <= share.header['bits'].target):
                return
            
            block = share.as_block(self.tracker, self.known_txs_var.value)
            if block is None:
                print >>sys.stderr, 'GOT INCOMPLETE BLOCK FROM PEER! %s bitcoin: %s%064x' % (p2pool_data.format_hash(share.hash), self.net.PARENT.BLOCK_EXPLORER_URL_PREFIX, share.header_hash)
                return
            helper.submit_block(block, True, self.factory, self.bitcoind, self.bitcoind_work, self.net)
            print
            print 'GOT BLOCK FROM PEER! Passing to bitcoind! %s bitcoin: %s%064x' % (p2pool_data.format_hash(share.hash), self.net.PARENT.BLOCK_EXPLORER_URL_PREFIX, share.header_hash)
            print
        
        def forget_old_txs():
            new_known_txs = {}
            if self.p2p_node is not None:
                for peer in self.p2p_node.peers.itervalues():
                    new_known_txs.update(peer.remembered_txs)
            new_known_txs.update(self.mining_txs_var.value)
            for share in self.tracker.get_chain(self.best_share_var.value, min(120, self.tracker.get_height(self.best_share_var.value))):
                for tx_hash in share.new_transaction_hashes:
                    if tx_hash in self.known_txs_var.value:
                        new_known_txs[tx_hash] = self.known_txs_var.value[tx_hash]
            self.known_txs_var.set(new_known_txs)
        t = deferral.RobustLoopingCall(forget_old_txs)
        t.start(10)
        stop_signal.watch(t.stop)
        
        t = deferral.RobustLoopingCall(self.clean_tracker)
        t.start(5)
        stop_signal.watch(t.stop)
    
    def set_best_share(self):
        best, desired, decorated_heads, bad_peer_addresses = self.tracker.think(self.get_height_rel_highest, self.bitcoind_work.value['previous_block'], self.bitcoind_work.value['bits'], self.known_txs_var.value)
        
        self.best_share_var.set(best)
        self.desired_var.set(desired)
        if self.p2p_node is not None:
            for bad_peer_address in bad_peer_addresses:
                # XXX O(n)
                for peer in self.p2p_node.peers.itervalues():
                    if peer.addr == bad_peer_address:
                        peer.badPeerHappened()
                        break
    
    def get_current_txouts(self):
        return p2pool_data.get_expected_payouts(self.tracker, self.best_share_var.value, self.bitcoind_work.value['bits'].target, self.bitcoind_work.value['subsidy'], self.net)
    
    def clean_tracker(self):
        best, desired, decorated_heads, bad_peer_addresses = self.tracker.think(self.get_height_rel_highest, self.bitcoind_work.value['previous_block'], self.bitcoind_work.value['bits'], self.known_txs_var.value)
        
        # eat away at heads
        if decorated_heads:
            for i in xrange(1000):
                to_remove = set()
                for share_hash, tail in self.tracker.heads.iteritems():
                    if share_hash in [head_hash for score, head_hash in decorated_heads[-5:]]:
                        #print 1
                        continue
                    if self.tracker.items[share_hash].time_seen > time.time() - 300:
                        #print 2
                        continue
                    if share_hash not in self.tracker.verified.items and max(self.tracker.items[after_tail_hash].time_seen for after_tail_hash in self.tracker.reverse.get(tail)) > time.time() - 120: # XXX stupid
                        #print 3
                        continue
                    to_remove.add(share_hash)
                if not to_remove:
                    break
                for share_hash in to_remove:
                    if share_hash in self.tracker.verified.items:
                        self.tracker.verified.remove(share_hash)
                    self.tracker.remove(share_hash)
                #print "_________", to_remove
        
        # drop tails
        for i in xrange(1000):
            to_remove = set()
            for tail, heads in self.tracker.tails.iteritems():
                if min(self.tracker.get_height(head) for head in heads) < 2*self.tracker.net.CHAIN_LENGTH + 10:
                    continue
                to_remove.update(self.tracker.reverse.get(tail, set()))
            if not to_remove:
                break
            # if removed from this, it must be removed from verified
            #start = time.time()
            for aftertail in to_remove:
                if self.tracker.items[aftertail].previous_hash not in self.tracker.tails:
                    print "erk", aftertail, self.tracker.items[aftertail].previous_hash
                    continue
                if aftertail in self.tracker.verified.items:
                    self.tracker.verified.remove(aftertail)
                self.tracker.remove(aftertail)
            #end = time.time()
            #print "removed! %i %f" % (len(to_remove), (end - start)/len(to_remove))
        
        self.set_best_share()

########NEW FILE########
__FILENAME__ = p2p
from __future__ import division

import math
import random
import sys
import time

from twisted.internet import defer, protocol, reactor
from twisted.python import failure, log

import p2pool
from p2pool import data as p2pool_data
from p2pool.bitcoin import data as bitcoin_data
from p2pool.util import deferral, p2protocol, pack, variable

class PeerMisbehavingError(Exception):
    pass


def fragment(f, **kwargs):
    try:
        f(**kwargs)
    except p2protocol.TooLong:
        fragment(f, **dict((k, v[:len(v)//2]) for k, v in kwargs.iteritems()))
        fragment(f, **dict((k, v[len(v)//2:]) for k, v in kwargs.iteritems()))

class Protocol(p2protocol.Protocol):
    VERSION = 1300
    
    max_remembered_txs_size = 2500000
    
    def __init__(self, node, incoming):
        p2protocol.Protocol.__init__(self, node.net.PREFIX, 1000000, node.traffic_happened)
        self.node = node
        self.incoming = incoming
        
        self.other_version = None
        self.connected2 = False
    
    def connectionMade(self):
        self.factory.proto_made_connection(self)
        
        self.connection_lost_event = variable.Event()
        
        self.addr = self.transport.getPeer().host, self.transport.getPeer().port
        
        self.send_version(
            version=self.VERSION,
            services=0,
            addr_to=dict(
                services=0,
                address=self.transport.getPeer().host,
                port=self.transport.getPeer().port,
            ),
            addr_from=dict(
                services=0,
                address=self.transport.getHost().host,
                port=self.transport.getHost().port,
            ),
            nonce=self.node.nonce,
            sub_version=p2pool.__version__,
            mode=1,
            best_share_hash=self.node.best_share_hash_func(),
        )
        
        self.timeout_delayed = reactor.callLater(10, self._connect_timeout)
        
        self.get_shares = deferral.GenericDeferrer(
            max_id=2**256,
            func=lambda id, hashes, parents, stops: self.send_sharereq(id=id, hashes=hashes, parents=parents, stops=stops),
            timeout=15,
            on_timeout=self.disconnect,
        )
        
        self.remote_tx_hashes = set() # view of peer's known_txs # not actually initially empty, but sending txs instead of tx hashes won't hurt
        self.remote_remembered_txs_size = 0
        
        self.remembered_txs = {} # view of peer's mining_txs
        self.remembered_txs_size = 0
        self.known_txs_cache = {}
    
    def _connect_timeout(self):
        self.timeout_delayed = None
        print 'Handshake timed out, disconnecting from %s:%i' % self.addr
        self.disconnect()
    
    def packetReceived(self, command, payload2):
        try:
            if command != 'version' and not self.connected2:
                raise PeerMisbehavingError('first message was not version message')
            p2protocol.Protocol.packetReceived(self, command, payload2)
        except PeerMisbehavingError, e:
            print 'Peer %s:%i misbehaving, will drop and ban. Reason:' % self.addr, e.message
            self.badPeerHappened()
    
    def badPeerHappened(self):
        print "Bad peer banned:", self.addr
        self.disconnect()
        if self.transport.getPeer().host != '127.0.0.1': # never ban localhost
            self.node.bans[self.transport.getPeer().host] = time.time() + 60*60
    
    def _timeout(self):
        self.timeout_delayed = None
        print 'Connection timed out, disconnecting from %s:%i' % self.addr
        self.disconnect()
    
    message_version = pack.ComposedType([
        ('version', pack.IntType(32)),
        ('services', pack.IntType(64)),
        ('addr_to', bitcoin_data.address_type),
        ('addr_from', bitcoin_data.address_type),
        ('nonce', pack.IntType(64)),
        ('sub_version', pack.VarStrType()),
        ('mode', pack.IntType(32)), # always 1 for legacy compatibility
        ('best_share_hash', pack.PossiblyNoneType(0, pack.IntType(256))),
    ])
    def handle_version(self, version, services, addr_to, addr_from, nonce, sub_version, mode, best_share_hash):
        if self.other_version is not None:
            raise PeerMisbehavingError('more than one version message')
        if version < 1300:
            raise PeerMisbehavingError('peer too old')
        
        self.other_version = version
        self.other_sub_version = sub_version[:512]
        self.other_services = services
        
        if nonce == self.node.nonce:
            raise PeerMisbehavingError('was connected to self')
        if nonce in self.node.peers:
            if p2pool.DEBUG:
                print 'Detected duplicate connection, disconnecting from %s:%i' % self.addr
            self.disconnect()
            return
        
        self.nonce = nonce
        self.connected2 = True
        
        self.timeout_delayed.cancel()
        self.timeout_delayed = reactor.callLater(100, self._timeout)
        
        old_dataReceived = self.dataReceived
        def new_dataReceived(data):
            if self.timeout_delayed is not None:
                self.timeout_delayed.reset(100)
            old_dataReceived(data)
        self.dataReceived = new_dataReceived
        
        self.factory.proto_connected(self)
        
        self._stop_thread = deferral.run_repeatedly(lambda: [
            self.send_ping(),
        random.expovariate(1/100)][-1])
        
        if self.node.advertise_ip:
            self._stop_thread2 = deferral.run_repeatedly(lambda: [
                self.send_addrme(port=self.node.serverfactory.listen_port.getHost().port) if self.node.serverfactory.listen_port is not None else None,
            random.expovariate(1/(100*len(self.node.peers) + 1))][-1])
        
        if best_share_hash is not None:
            self.node.handle_share_hashes([best_share_hash], self)
        
        def update_remote_view_of_my_known_txs(before, after):
            added = set(after) - set(before)
            removed = set(before) - set(after)
            if added:
                self.send_have_tx(tx_hashes=list(added))
            if removed:
                self.send_losing_tx(tx_hashes=list(removed))
                
                # cache forgotten txs here for a little while so latency of "losing_tx" packets doesn't cause problems
                key = max(self.known_txs_cache) + 1 if self.known_txs_cache else 0
                self.known_txs_cache[key] = dict((h, before[h]) for h in removed)
                reactor.callLater(20, self.known_txs_cache.pop, key)
        watch_id = self.node.known_txs_var.transitioned.watch(update_remote_view_of_my_known_txs)
        self.connection_lost_event.watch(lambda: self.node.known_txs_var.transitioned.unwatch(watch_id))
        
        self.send_have_tx(tx_hashes=self.node.known_txs_var.value.keys())
        
        def update_remote_view_of_my_mining_txs(before, after):
            added = set(after) - set(before)
            removed = set(before) - set(after)
            if added:
                self.remote_remembered_txs_size += sum(100 + bitcoin_data.tx_type.packed_size(after[x]) for x in added)
                assert self.remote_remembered_txs_size <= self.max_remembered_txs_size
                fragment(self.send_remember_tx, tx_hashes=[x for x in added if x in self.remote_tx_hashes], txs=[after[x] for x in added if x not in self.remote_tx_hashes])
            if removed:
                self.send_forget_tx(tx_hashes=list(removed))
                self.remote_remembered_txs_size -= sum(100 + bitcoin_data.tx_type.packed_size(before[x]) for x in removed)
        watch_id2 = self.node.mining_txs_var.transitioned.watch(update_remote_view_of_my_mining_txs)
        self.connection_lost_event.watch(lambda: self.node.mining_txs_var.transitioned.unwatch(watch_id2))
        
        self.remote_remembered_txs_size += sum(100 + bitcoin_data.tx_type.packed_size(x) for x in self.node.mining_txs_var.value.values())
        assert self.remote_remembered_txs_size <= self.max_remembered_txs_size
        fragment(self.send_remember_tx, tx_hashes=[], txs=self.node.mining_txs_var.value.values())
    
    message_ping = pack.ComposedType([])
    def handle_ping(self):
        pass
    
    message_addrme = pack.ComposedType([
        ('port', pack.IntType(16)),
    ])
    def handle_addrme(self, port):
        host = self.transport.getPeer().host
        #print 'addrme from', host, port
        if host == '127.0.0.1':
            if random.random() < .8 and self.node.peers:
                random.choice(self.node.peers.values()).send_addrme(port=port) # services...
        else:
            self.node.got_addr((self.transport.getPeer().host, port), self.other_services, int(time.time()))
            if random.random() < .8 and self.node.peers:
                random.choice(self.node.peers.values()).send_addrs(addrs=[
                    dict(
                        address=dict(
                            services=self.other_services,
                            address=host,
                            port=port,
                        ),
                        timestamp=int(time.time()),
                    ),
                ])
    
    message_addrs = pack.ComposedType([
        ('addrs', pack.ListType(pack.ComposedType([
            ('timestamp', pack.IntType(64)),
            ('address', bitcoin_data.address_type),
        ]))),
    ])
    def handle_addrs(self, addrs):
        for addr_record in addrs:
            self.node.got_addr((addr_record['address']['address'], addr_record['address']['port']), addr_record['address']['services'], min(int(time.time()), addr_record['timestamp']))
            if random.random() < .8 and self.node.peers:
                random.choice(self.node.peers.values()).send_addrs(addrs=[addr_record])
    
    message_getaddrs = pack.ComposedType([
        ('count', pack.IntType(32)),
    ])
    def handle_getaddrs(self, count):
        if count > 100:
            count = 100
        self.send_addrs(addrs=[
            dict(
                timestamp=int(self.node.addr_store[host, port][2]),
                address=dict(
                    services=self.node.addr_store[host, port][0],
                    address=host,
                    port=port,
                ),
            ) for host, port in
            self.node.get_good_peers(count)
        ])
    
    message_shares = pack.ComposedType([
        ('shares', pack.ListType(p2pool_data.share_type)),
    ])
    def handle_shares(self, shares):
        result = []
        for wrappedshare in shares:
            if wrappedshare['type'] < p2pool_data.Share.VERSION: continue
            share = p2pool_data.load_share(wrappedshare, self.node.net, self.addr)
            if wrappedshare['type'] >= 13:
                txs = []
                for tx_hash in share.share_info['new_transaction_hashes']:
                    if tx_hash in self.node.known_txs_var.value:
                        tx = self.node.known_txs_var.value[tx_hash]
                    else:
                        for cache in self.known_txs_cache.itervalues():
                            if tx_hash in cache:
                                tx = cache[tx_hash]
                                print 'Transaction %064x rescued from peer latency cache!' % (tx_hash,)
                                break
                        else:
                            print >>sys.stderr, 'Peer referenced unknown transaction %064x, disconnecting' % (tx_hash,)
                            self.disconnect()
                            return
                    txs.append(tx)
            else:
                txs = None
            
            result.append((share, txs))
            
        self.node.handle_shares(result, self)
    
    def sendShares(self, shares, tracker, known_txs, include_txs_with=[]):
        tx_hashes = set()
        for share in shares:
            if share.VERSION >= 13:
                # send full transaction for every new_transaction_hash that peer does not know
                for tx_hash in share.share_info['new_transaction_hashes']:
                    assert tx_hash in known_txs, 'tried to broadcast share without knowing all its new transactions'
                    if tx_hash not in self.remote_tx_hashes:
                        tx_hashes.add(tx_hash)
                continue
            if share.hash in include_txs_with:
                x = share.get_other_tx_hashes(tracker)
                if x is not None:
                    tx_hashes.update(x)
        
        hashes_to_send = [x for x in tx_hashes if x not in self.node.mining_txs_var.value and x in known_txs]
        
        new_remote_remembered_txs_size = self.remote_remembered_txs_size + sum(100 + bitcoin_data.tx_type.packed_size(known_txs[x]) for x in hashes_to_send)
        if new_remote_remembered_txs_size > self.max_remembered_txs_size:
            raise ValueError('shares have too many txs')
        self.remote_remembered_txs_size = new_remote_remembered_txs_size
        
        fragment(self.send_remember_tx, tx_hashes=[x for x in hashes_to_send if x in self.remote_tx_hashes], txs=[known_txs[x] for x in hashes_to_send if x not in self.remote_tx_hashes])
        
        fragment(self.send_shares, shares=[share.as_share() for share in shares])
        
        self.send_forget_tx(tx_hashes=hashes_to_send)
        
        self.remote_remembered_txs_size -= sum(100 + bitcoin_data.tx_type.packed_size(known_txs[x]) for x in hashes_to_send)
    
    
    message_sharereq = pack.ComposedType([
        ('id', pack.IntType(256)),
        ('hashes', pack.ListType(pack.IntType(256))),
        ('parents', pack.VarIntType()),
        ('stops', pack.ListType(pack.IntType(256))),
    ])
    def handle_sharereq(self, id, hashes, parents, stops):
        shares = self.node.handle_get_shares(hashes, parents, stops, self)
        try:
            self.send_sharereply(id=id, result='good', shares=[share.as_share() for share in shares])
        except p2protocol.TooLong:
            self.send_sharereply(id=id, result='too long', shares=[])
    
    message_sharereply = pack.ComposedType([
        ('id', pack.IntType(256)),
        ('result', pack.EnumType(pack.VarIntType(), {0: 'good', 1: 'too long', 2: 'unk2', 3: 'unk3', 4: 'unk4', 5: 'unk5', 6: 'unk6'})),
        ('shares', pack.ListType(p2pool_data.share_type)),
    ])
    class ShareReplyError(Exception): pass
    def handle_sharereply(self, id, result, shares):
        if result == 'good':
            res = [p2pool_data.load_share(share, self.node.net, self.addr) for share in shares if share['type'] >= p2pool_data.Share.VERSION]
        else:
            res = failure.Failure(self.ShareReplyError(result))
        self.get_shares.got_response(id, res)
    
    
    message_bestblock = pack.ComposedType([
        ('header', bitcoin_data.block_header_type),
    ])
    def handle_bestblock(self, header):
        self.node.handle_bestblock(header, self)
    
    
    message_have_tx = pack.ComposedType([
        ('tx_hashes', pack.ListType(pack.IntType(256))),
    ])
    def handle_have_tx(self, tx_hashes):
        #assert self.remote_tx_hashes.isdisjoint(tx_hashes)
        self.remote_tx_hashes.update(tx_hashes)
        while len(self.remote_tx_hashes) > 10000:
            self.remote_tx_hashes.pop()
    message_losing_tx = pack.ComposedType([
        ('tx_hashes', pack.ListType(pack.IntType(256))),
    ])
    def handle_losing_tx(self, tx_hashes):
        #assert self.remote_tx_hashes.issuperset(tx_hashes)
        self.remote_tx_hashes.difference_update(tx_hashes)
    
    
    message_remember_tx = pack.ComposedType([
        ('tx_hashes', pack.ListType(pack.IntType(256))),
        ('txs', pack.ListType(bitcoin_data.tx_type)),
    ])
    def handle_remember_tx(self, tx_hashes, txs):
        for tx_hash in tx_hashes:
            if tx_hash in self.remembered_txs:
                print >>sys.stderr, 'Peer referenced transaction twice, disconnecting'
                self.disconnect()
                return
            
            if tx_hash in self.node.known_txs_var.value:
                tx = self.node.known_txs_var.value[tx_hash]
            else:
                for cache in self.known_txs_cache.itervalues():
                    if tx_hash in cache:
                        tx = cache[tx_hash]
                        print 'Transaction %064x rescued from peer latency cache!' % (tx_hash,)
                        break
                else:
                    print >>sys.stderr, 'Peer referenced unknown transaction %064x, disconnecting' % (tx_hash,)
                    self.disconnect()
                    return
            
            self.remembered_txs[tx_hash] = tx
            self.remembered_txs_size += 100 + bitcoin_data.tx_type.packed_size(tx)
        new_known_txs = dict(self.node.known_txs_var.value)
        warned = False
        for tx in txs:
            tx_hash = bitcoin_data.hash256(bitcoin_data.tx_type.pack(tx))
            if tx_hash in self.remembered_txs:
                print >>sys.stderr, 'Peer referenced transaction twice, disconnecting'
                self.disconnect()
                return
            
            if tx_hash in self.node.known_txs_var.value and not warned:
                print 'Peer sent entire transaction %064x that was already received' % (tx_hash,)
                warned = True
            
            self.remembered_txs[tx_hash] = tx
            self.remembered_txs_size += 100 + bitcoin_data.tx_type.packed_size(tx)
            new_known_txs[tx_hash] = tx
        self.node.known_txs_var.set(new_known_txs)
        if self.remembered_txs_size >= self.max_remembered_txs_size:
            raise PeerMisbehavingError('too much transaction data stored')
    message_forget_tx = pack.ComposedType([
        ('tx_hashes', pack.ListType(pack.IntType(256))),
    ])
    def handle_forget_tx(self, tx_hashes):
        for tx_hash in tx_hashes:
            self.remembered_txs_size -= 100 + bitcoin_data.tx_type.packed_size(self.remembered_txs[tx_hash])
            assert self.remembered_txs_size >= 0
            del self.remembered_txs[tx_hash]
    
    
    def connectionLost(self, reason):
        self.connection_lost_event.happened()
        if self.timeout_delayed is not None:
            self.timeout_delayed.cancel()
        if self.connected2:
            self.factory.proto_disconnected(self, reason)
            self._stop_thread()
            if self.node.advertise_ip:
                self._stop_thread2()
            self.connected2 = False
        self.factory.proto_lost_connection(self, reason)
        if p2pool.DEBUG:
            print "Peer connection lost:", self.addr, reason
        self.get_shares.respond_all(reason)
    
    @defer.inlineCallbacks
    def do_ping(self):
        start = reactor.seconds()
        yield self.get_shares(hashes=[0], parents=0, stops=[])
        end = reactor.seconds()
        defer.returnValue(end - start)

class ServerFactory(protocol.ServerFactory):
    def __init__(self, node, max_conns):
        self.node = node
        self.max_conns = max_conns
        
        self.conns = {}
        self.running = False
        self.listen_port = None
    
    def buildProtocol(self, addr):
        if sum(self.conns.itervalues()) >= self.max_conns or self.conns.get(self._host_to_ident(addr.host), 0) >= 3:
            return None
        if addr.host in self.node.bans and self.node.bans[addr.host] > time.time():
            return None
        p = Protocol(self.node, True)
        p.factory = self
        if p2pool.DEBUG:
            print "Got peer connection from:", addr
        return p
    
    def _host_to_ident(self, host):
        a, b, c, d = host.split('.')
        return a, b
    
    def proto_made_connection(self, proto):
        ident = self._host_to_ident(proto.transport.getPeer().host)
        self.conns[ident] = self.conns.get(ident, 0) + 1
    def proto_lost_connection(self, proto, reason):
        ident = self._host_to_ident(proto.transport.getPeer().host)
        self.conns[ident] -= 1
        if not self.conns[ident]:
            del self.conns[ident]
    
    def proto_connected(self, proto):
        self.node.got_conn(proto)
    def proto_disconnected(self, proto, reason):
        self.node.lost_conn(proto, reason)
    
    def start(self):
        assert not self.running
        self.running = True
        
        def attempt_listen():
            if self.running:
                self.listen_port = reactor.listenTCP(self.node.port, self)
        deferral.retry('Error binding to P2P port:', traceback=False)(attempt_listen)()
    
    def stop(self):
        assert self.running
        self.running = False
        
        return self.listen_port.stopListening()

class ClientFactory(protocol.ClientFactory):
    def __init__(self, node, desired_conns, max_attempts):
        self.node = node
        self.desired_conns = desired_conns
        self.max_attempts = max_attempts
        
        self.attempts = set()
        self.conns = set()
        self.running = False
    
    def _host_to_ident(self, host):
        a, b, c, d = host.split('.')
        return a, b
    
    def buildProtocol(self, addr):
        p = Protocol(self.node, False)
        p.factory = self
        return p
    
    def startedConnecting(self, connector):
        ident = self._host_to_ident(connector.getDestination().host)
        if ident in self.attempts:
            raise AssertionError('already have attempt')
        self.attempts.add(ident)
    
    def clientConnectionFailed(self, connector, reason):
        self.attempts.remove(self._host_to_ident(connector.getDestination().host))
    
    def clientConnectionLost(self, connector, reason):
        self.attempts.remove(self._host_to_ident(connector.getDestination().host))
    
    def proto_made_connection(self, proto):
        pass
    def proto_lost_connection(self, proto, reason):
        pass
    
    def proto_connected(self, proto):
        self.conns.add(proto)
        self.node.got_conn(proto)
    def proto_disconnected(self, proto, reason):
        self.conns.remove(proto)
        self.node.lost_conn(proto, reason)
    
    def start(self):
        assert not self.running
        self.running = True
        self._stop_thinking = deferral.run_repeatedly(self._think)
    def stop(self):
        assert self.running
        self.running = False
        self._stop_thinking()
    
    def _think(self):
        try:
            if len(self.conns) < self.desired_conns and len(self.attempts) < self.max_attempts and self.node.addr_store:
                (host, port), = self.node.get_good_peers(1)
                
                if self._host_to_ident(host) in self.attempts:
                    pass
                elif host in self.node.bans and self.node.bans[host] > time.time():
                    pass
                else:
                    #print 'Trying to connect to', host, port
                    reactor.connectTCP(host, port, self, timeout=5)
        except:
            log.err()
        
        return random.expovariate(1/1)

class SingleClientFactory(protocol.ReconnectingClientFactory):
    def __init__(self, node):
        self.node = node
    
    def buildProtocol(self, addr):
        p = Protocol(self.node, incoming=False)
        p.factory = self
        return p
    
    def proto_made_connection(self, proto):
        pass
    def proto_lost_connection(self, proto, reason):
        pass
    
    def proto_connected(self, proto):
        self.resetDelay()
        self.node.got_conn(proto)
    def proto_disconnected(self, proto, reason):
        self.node.lost_conn(proto, reason)

class Node(object):
    def __init__(self, best_share_hash_func, port, net, addr_store={}, connect_addrs=set(), desired_outgoing_conns=10, max_outgoing_attempts=30, max_incoming_conns=50, preferred_storage=1000, known_txs_var=variable.Variable({}), mining_txs_var=variable.Variable({}), advertise_ip=True):
        self.best_share_hash_func = best_share_hash_func
        self.port = port
        self.net = net
        self.addr_store = dict(addr_store)
        self.connect_addrs = connect_addrs
        self.preferred_storage = preferred_storage
        self.known_txs_var = known_txs_var
        self.mining_txs_var = mining_txs_var
        self.advertise_ip = advertise_ip
        
        self.traffic_happened = variable.Event()
        self.nonce = random.randrange(2**64)
        self.peers = {}
        self.bans = {} # address -> end_time
        self.clientfactory = ClientFactory(self, desired_outgoing_conns, max_outgoing_attempts)
        self.serverfactory = ServerFactory(self, max_incoming_conns)
        self.running = False
    
    def start(self):
        if self.running:
            raise ValueError('already running')
        
        self.clientfactory.start()
        self.serverfactory.start()
        self.singleclientconnectors = [reactor.connectTCP(addr, port, SingleClientFactory(self)) for addr, port in self.connect_addrs]
        
        self.running = True
        
        self._stop_thinking = deferral.run_repeatedly(self._think)
    
    def _think(self):
        try:
            if len(self.addr_store) < self.preferred_storage and self.peers:
                random.choice(self.peers.values()).send_getaddrs(count=8)
        except:
            log.err()
        
        return random.expovariate(1/20)
    
    @defer.inlineCallbacks
    def stop(self):
        if not self.running:
            raise ValueError('already stopped')
        
        self.running = False
        
        self._stop_thinking()
        yield self.clientfactory.stop()
        yield self.serverfactory.stop()
        for singleclientconnector in self.singleclientconnectors:
            yield singleclientconnector.factory.stopTrying()
            yield singleclientconnector.disconnect()
        del self.singleclientconnectors
    
    def got_conn(self, conn):
        if conn.nonce in self.peers:
            raise ValueError('already have peer')
        self.peers[conn.nonce] = conn
        
        print '%s connection to peer %s:%i established. p2pool version: %i %r' % ('Incoming' if conn.incoming else 'Outgoing', conn.addr[0], conn.addr[1], conn.other_version, conn.other_sub_version)
    
    def lost_conn(self, conn, reason):
        if conn.nonce not in self.peers:
            raise ValueError('''don't have peer''')
        if conn is not self.peers[conn.nonce]:
            raise ValueError('wrong conn')
        del self.peers[conn.nonce]
        
        print 'Lost peer %s:%i - %s' % (conn.addr[0], conn.addr[1], reason.getErrorMessage())
    
    
    def got_addr(self, (host, port), services, timestamp):
        if (host, port) in self.addr_store:
            old_services, old_first_seen, old_last_seen = self.addr_store[host, port]
            self.addr_store[host, port] = services, old_first_seen, max(old_last_seen, timestamp)
        else:
            if len(self.addr_store) < 10000:
                self.addr_store[host, port] = services, timestamp, timestamp
    
    def handle_shares(self, shares, peer):
        print 'handle_shares', (shares, peer)
    
    def handle_share_hashes(self, hashes, peer):
        print 'handle_share_hashes', (hashes, peer)
    
    def handle_get_shares(self, hashes, parents, stops, peer):
        print 'handle_get_shares', (hashes, parents, stops, peer)
    
    def handle_bestblock(self, header, peer):
        print 'handle_bestblock', header
    
    def get_good_peers(self, max_count):
        t = time.time()
        return [x[0] for x in sorted(self.addr_store.iteritems(), key=lambda (k, (services, first_seen, last_seen)):
            -math.log(max(3600, last_seen - first_seen))/math.log(max(3600, t - last_seen))*random.expovariate(1)
        )][:max_count]

########NEW FILE########
__FILENAME__ = test_data
import unittest

from p2pool.bitcoin import data, networks
from p2pool.util import pack


class Test(unittest.TestCase):
    def test_header_hash(self):
        assert data.hash256(data.block_header_type.pack(dict(
            version=1,
            previous_block=0x000000000000038a2a86b72387f93c51298298a732079b3b686df3603d2f6282,
            merkle_root=0x37a43a3b812e4eb665975f46393b4360008824aab180f27d642de8c28073bc44,
            timestamp=1323752685,
            bits=data.FloatingInteger(437159528),
            nonce=3658685446,
        ))) == 0x000000000000003aaaf7638f9f9c0d0c60e8b0eb817dcdb55fd2b1964efc5175
    
    def test_header_hash_litecoin(self):
        assert networks.nets['litecoin'].POW_FUNC(data.block_header_type.pack(dict(
            version=1,
            previous_block=0xd928d3066613d1c9dd424d5810cdd21bfeef3c698977e81ec1640e1084950073,
            merkle_root=0x03f4b646b58a66594a182b02e425e7b3a93c8a52b600aa468f1bc5549f395f16,
            timestamp=1327807194,
            bits=data.FloatingInteger(0x1d01b56f),
            nonce=20736,
        ))) < 2**256//2**30
    
    def test_tx_hash(self):
        assert data.hash256(data.tx_type.pack(dict(
            version=1,
            tx_ins=[dict(
                previous_output=None,
                sequence=None,
                script='70736a0468860e1a0452389500522cfabe6d6d2b2f33cf8f6291b184f1b291d24d82229463fcec239afea0ee34b4bfc622f62401000000000000004d696e656420627920425443204775696c6420ac1eeeed88'.decode('hex'),
            )],
            tx_outs=[dict(
                value=5003880250,
                script=data.pubkey_hash_to_script2(pack.IntType(160).unpack('ca975b00a8c203b8692f5a18d92dc5c2d2ebc57b'.decode('hex'))),
            )],
            lock_time=0,
        ))) == 0xb53802b2333e828d6532059f46ecf6b313a42d79f97925e457fbbfda45367e5c
    
    def test_address_to_pubkey_hash(self):
        assert data.address_to_pubkey_hash('1KUCp7YP5FP8ViRxhfszSUJCTAajK6viGy', networks.nets['bitcoin']) == pack.IntType(160).unpack('ca975b00a8c203b8692f5a18d92dc5c2d2ebc57b'.decode('hex'))
    
    def test_merkle_hash(self):
        assert data.merkle_hash([
            0xb53802b2333e828d6532059f46ecf6b313a42d79f97925e457fbbfda45367e5c,
            0x326dfe222def9cf571af37a511ccda282d83bedcc01dabf8aa2340d342398cf0,
            0x5d2e0541c0f735bac85fa84bfd3367100a3907b939a0c13e558d28c6ffd1aea4,
            0x8443faf58aa0079760750afe7f08b759091118046fe42794d3aca2aa0ff69da2,
            0x4d8d1c65ede6c8eab843212e05c7b380acb82914eef7c7376a214a109dc91b9d,
            0x1d750bc0fa276f89db7e6ed16eb1cf26986795121f67c03712210143b0cb0125,
            0x5179349931d714d3102dfc004400f52ef1fed3b116280187ca85d1d638a80176,
            0xa8b3f6d2d566a9239c9ad9ae2ed5178dee4a11560a8dd1d9b608fd6bf8c1e75,
            0xab4d07cd97f9c0c4129cff332873a44efdcd33bdbfc7574fe094df1d379e772f,
            0xf54a7514b1de8b5d9c2a114d95fba1e694b6e3e4a771fda3f0333515477d685b,
            0x894e972d8a2fc6c486da33469b14137a7f89004ae07b95e63923a3032df32089,
            0x86cdde1704f53fce33ab2d4f5bc40c029782011866d0e07316d695c41e32b1a0,
            0xf7cf4eae5e497be8215778204a86f1db790d9c27fe6a5b9f745df5f3862f8a85,
            0x2e72f7ddf157d64f538ec72562a820e90150e8c54afc4d55e0d6e3dbd8ca50a,
            0x9f27471dfbc6ce3cbfcf1c8b25d44b8d1b9d89ea5255e9d6109e0f9fd662f75c,
            0x995f4c9f78c5b75a0c19f0a32387e9fa75adaa3d62fba041790e06e02ae9d86d,
            0xb11ec2ad2049aa32b4760d458ee9effddf7100d73c4752ea497e54e2c58ba727,
            0xa439f288fbc5a3b08e5ffd2c4e2d87c19ac2d5e4dfc19fabfa33c7416819e1ec,
            0x3aa33f886f1357b4bbe81784ec1cf05873b7c5930ab912ee684cc6e4f06e4c34,
            0xcab9a1213037922d94b6dcd9c567aa132f16360e213c202ee59f16dde3642ac7,
            0xa2d7a3d2715eb6b094946c6e3e46a88acfb37068546cabe40dbf6cd01a625640,
            0x3d02764f24816aaa441a8d472f58e0f8314a70d5b44f8a6f88cc8c7af373b24e,
            0xcc5adf077c969ebd78acebc3eb4416474aff61a828368113d27f72ad823214d0,
            0xf2d8049d1971f02575eb37d3a732d46927b6be59a18f1bd0c7f8ed123e8a58a,
            0x94ffe8d46a1accd797351894f1774995ed7df3982c9a5222765f44d9c3151dbb,
            0x82268fa74a878636261815d4b8b1b01298a8bffc87336c0d6f13ef6f0373f1f0,
            0x73f441f8763dd1869fe5c2e9d298b88dc62dc8c75af709fccb3622a4c69e2d55,
            0xeb78fc63d4ebcdd27ed618fd5025dc61de6575f39b2d98e3be3eb482b210c0a0,
            0x13375a426de15631af9afdf00c490e87cc5aab823c327b9856004d0b198d72db,
            0x67d76a64fa9b6c5d39fde87356282ef507b3dec1eead4b54e739c74e02e81db4,
        ]) == 0x37a43a3b812e4eb665975f46393b4360008824aab180f27d642de8c28073bc44

########NEW FILE########
__FILENAME__ = test_getwork
import unittest

from p2pool.bitcoin import getwork, data as bitcoin_data

class Test(unittest.TestCase):
    def test_all(self):
        cases = [
            {
                'target': '0000000000000000000000000000000000000000000000f2b944000000000000',
                'midstate': '5982f893102dec03e374b472647c4f19b1b6d21ae4b2ac624f3d2f41b9719404',
                'hash1': '00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000',
                'data': '0000000163930d52a5ffca79b29b95a659a302cd4e1654194780499000002274000000002e133d9e51f45bc0886d05252038e421e82bff18b67dc14b90d9c3c2f422cd5c4dd4598e1a44b9f200000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'
            },
            {
                'midstate' : 'f4a9b048c0cb9791bc94b13ee0eec21e713963d524fd140b58bb754dd7b0955f',
                'data' : '000000019a1d7342fb62090bda686b22d90f9f73d0f5c418b9c980cd0000011a00000000680b07c8a2f97ecd831f951806857e09f98a3b81cdef1fa71982934fef8dc3444e18585d1a0abbcf00000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000',
                'hash1' : '00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000',
                'target' : '0000000000000000000000000000000000000000000000cfbb0a000000000000',
                'extrathing': 'hi!',
            },
            {
                'data' : '000000019a1d7342fb62090bda686b22d90f9f73d0f5c418b9c980cd0000011a00000000680b07c8a2f97ecd831f951806857e09f98a3b81cdef1fa71982934fef8dc3444e18585d1a0abbcf00000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000',
                'hash1' : '00000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000010000',
                'target' : '0000000000000000000000000000000000000000000000cfbb0a000000000000',
                'extrathing': 'hi!',
            },
        ]
        for case in cases:
            ba = getwork.BlockAttempt.from_getwork(case)
            
            extra = dict(case)
            del extra['data'], extra['hash1'], extra['target']
            extra.pop('midstate', None)
            
            getwork_check = ba.getwork(**extra)
            assert getwork_check == case or dict((k, v) for k, v in getwork_check.iteritems() if k != 'midstate') == case
        
        case2s = [
            getwork.BlockAttempt(
                1,
                0x148135e10208db85abb62754341a392eab1f186aab077a831cf7,
                0x534ea08be1ab529f484369344b6d5423ef5a0767db9b3ebb4e182bbb67962520,
                1305759879,
                bitcoin_data.FloatingInteger.from_target_upper_bound(0x44b9f20000000000000000000000000000000000000000000000),
                0x44b9f20000000000000000000000000000000000000000000000,
            ),
            getwork.BlockAttempt(
                1,
                0x148135e10208db85abb62754341a392eab1f186aab077a831cf7,
                0x534ea08be1ab529f484369344b6d5423ef5a0767db9b3ebb4e182bbb67962520,
                1305759879,
                bitcoin_data.FloatingInteger.from_target_upper_bound(0x44b9f20000000000000000000000000000000000000000000000),
                432*2**230,
            ),
            getwork.BlockAttempt(
                1,
                0x148135e10208db85abb62754341a392eab1f186aab077a831cf7,
                0x534ea08be1ab529f484369344b6d5423ef5a0767db9b3ebb4e182bbb67962520,
                1305759879,
                bitcoin_data.FloatingInteger.from_target_upper_bound(0x44b9f20000000000000000000000000000000000000000000000),
                7*2**240,
            )
        ]
        for case2 in case2s:
            assert getwork.BlockAttempt.from_getwork(case2.getwork()) == case2
            assert getwork.BlockAttempt.from_getwork(case2.getwork(ident='hi')) == case2
            case2 = case2.update(previous_block=case2.previous_block - 10)
            assert getwork.BlockAttempt.from_getwork(case2.getwork()) == case2
            assert getwork.BlockAttempt.from_getwork(case2.getwork(ident='hi')) == case2

########NEW FILE########
__FILENAME__ = test_p2p
from twisted.internet import defer, reactor
from twisted.trial import unittest

from p2pool.bitcoin import data, networks, p2p
from p2pool.util import deferral


class Test(unittest.TestCase):
    @defer.inlineCallbacks
    def test_get_block(self):
        factory = p2p.ClientFactory(networks.nets['bitcoin'])
        c = reactor.connectTCP('127.0.0.1', 8333, factory)
        try:
            h = 0x000000000000046acff93b0e76cd10490551bf871ce9ac9fad62e67a07ff1d1e
            block = yield deferral.retry()(defer.inlineCallbacks(lambda: defer.returnValue((yield (yield factory.getProtocol()).get_block(h)))))()
            assert data.merkle_hash(map(data.hash256, map(data.tx_type.pack, block['txs']))) == block['header']['merkle_root']
            assert data.hash256(data.block_header_type.pack(block['header'])) == h
        finally:
            factory.stopTrying()
            c.disconnect()

########NEW FILE########
__FILENAME__ = test_script
import unittest

from p2pool.bitcoin import script

class Test(unittest.TestCase):
    def test_all(self):
        data = '76  A9  14 89 AB CD EF AB BA AB BA AB BA AB BA AB BA AB BA AB BA AB BA  88 AC'.replace(' ', '').decode('hex')
        self.assertEquals(
            list(script.parse(data)),
            [('UNK_118', None), ('UNK_169', None), ('PUSH', '\x89\xab\xcd\xef\xab\xba\xab\xba\xab\xba\xab\xba\xab\xba\xab\xba\xab\xba\xab\xba'), ('UNK_136', None), ('CHECKSIG', None)],
        )
        self.assertEquals(script.get_sigop_count(data), 1)

########NEW FILE########
__FILENAME__ = test_sha256
from __future__ import division

import unittest
import hashlib
import random

from p2pool.bitcoin import sha256

class Test(unittest.TestCase):
    def test_all(self):
        for test in ['', 'a', 'b', 'abc', 'abc'*50, 'hello world']:
            #print test
            #print sha256.sha256(test).hexdigest()
            #print hashlib.sha256(test).hexdigest()
            #print
            assert sha256.sha256(test).hexdigest() == hashlib.sha256(test).hexdigest()
        def random_str(l):
            return ''.join(chr(random.randrange(256)) for i in xrange(l))
        for length in xrange(150):
            test = random_str(length)
            a = sha256.sha256(test).hexdigest()
            b = hashlib.sha256(test).hexdigest()
            assert a == b
        for i in xrange(100):
            test = random_str(int(random.expovariate(1/100)))
            test2 = random_str(int(random.expovariate(1/100)))
            
            a = sha256.sha256(test)
            a = a.copy()
            a.update(test2)
            a = a.hexdigest()
            
            b = hashlib.sha256(test)
            b = b.copy()
            b.update(test2)
            b = b.hexdigest()
            assert a == b

########NEW FILE########
__FILENAME__ = test_data
import random
import unittest

from p2pool import data
from p2pool.bitcoin import data as bitcoin_data
from p2pool.test.util import test_forest
from p2pool.util import forest

def random_bytes(length):
    return ''.join(chr(random.randrange(2**8)) for i in xrange(length))

class Test(unittest.TestCase):
    def test_hashlink1(self):
        for i in xrange(100):
            d = random_bytes(random.randrange(2048))
            x = data.prefix_to_hash_link(d)
            assert data.check_hash_link(x, '') == bitcoin_data.hash256(d)
    
    def test_hashlink2(self):
        for i in xrange(100):
            d = random_bytes(random.randrange(2048))
            d2 = random_bytes(random.randrange(2048))
            x = data.prefix_to_hash_link(d)
            assert data.check_hash_link(x, d2) == bitcoin_data.hash256(d + d2)
    
    def test_hashlink3(self):
        for i in xrange(100):
            d = random_bytes(random.randrange(2048))
            d2 = random_bytes(random.randrange(200))
            d3 = random_bytes(random.randrange(2048))
            x = data.prefix_to_hash_link(d + d2, d2)
            assert data.check_hash_link(x, d3, d2) == bitcoin_data.hash256(d + d2 + d3)
    
    def test_skiplist(self):
        t = forest.Tracker()
        d = data.WeightsSkipList(t)
        for i in xrange(200):
            t.add(test_forest.FakeShare(hash=i, previous_hash=i - 1 if i > 0 else None, new_script=i, share_data=dict(donation=1234), target=2**249))
        for i in xrange(200):
            a = random.randrange(200)
            d(a, random.randrange(a + 1), 1000000*65535)[1]

########NEW FILE########
__FILENAME__ = test_node
from __future__ import division

import base64
import random
import tempfile

from twisted.internet import defer, reactor
from twisted.python import failure
from twisted.trial import unittest
from twisted.web import client, resource, server

from p2pool import data, node, work
from p2pool.bitcoin import data as bitcoin_data, networks, worker_interface
from p2pool.util import deferral, jsonrpc, math, variable

class bitcoind(object): # can be used as p2p factory, p2p protocol, or rpc jsonrpc proxy
    def __init__(self):
        self.blocks = [0x000000000000016c169477c25421250ec5d32cf9c6d38538b5de970a2355fd89]
        self.headers = {0x16c169477c25421250ec5d32cf9c6d38538b5de970a2355fd89: {
            'nonce': 1853158954,
            'timestamp': 1351658517,
            'merkle_root': 2282849479936278423916707524932131168473430114569971665822757638339486597658L,
            'version': 1,
            'previous_block': 1048610514577342396345362905164852351970507722694242579238530L,
            'bits': bitcoin_data.FloatingInteger(bits=0x1a0513c5, target=0x513c50000000000000000000000000000000000000000000000L),
        }}
        
        self.conn = variable.Variable(self)
        self.new_headers = variable.Event()
        self.new_block = variable.Event()
        self.new_tx = variable.Event()
    
    # p2p factory
    
    def getProtocol(self):
        return self
    
    # p2p protocol
    
    def send_block(self, block):
        pass
    
    def send_tx(self, tx):
        pass
    
    def get_block_header(self, block_hash):
        return self.headers[block_hash]
    
    # rpc jsonrpc proxy
    
    def rpc_help(self):
        return '\ngetblock '
    
    def rpc_getblock(self, block_hash_hex):
        block_hash = int(block_hash_hex, 16)
        return dict(height=self.blocks.index(block_hash))
    
    def __getattr__(self, name):
        if name.startswith('rpc_'):
            return lambda *args, **kwargs: failure.Failure(jsonrpc.Error_for_code(-32601)('Method not found'))
    
    def rpc_getblocktemplate(self, param):
        if param['mode'] == 'template':
            pass
        elif param['mode'] == 'submit':
            result = param['data']
            block = bitcoin_data.block_type.unpack(result.decode('hex'))
            if sum(tx_out['value'] for tx_out in block['txs'][0]['tx_outs']) != sum(tx['tx_outs'][0]['value'] for tx in block['txs'][1:]) + 5000000000:
                print 'invalid fee'
            if block['header']['previous_block'] != self.blocks[-1]:
                return False
            if bitcoin_data.hash256(result.decode('hex')) > block['header']['bits'].target:
                return False
            header_hash = bitcoin_data.hash256(bitcoin_data.block_header_type.pack(block['header']))
            self.blocks.append(header_hash)
            self.headers[header_hash] = block['header']
            reactor.callLater(0, self.new_block.happened)
            return True
        else:
            raise jsonrpc.Error_for_code(-1)('invalid request')
        
        txs = []
        for i in xrange(100):
            fee = i
            txs.append(dict(
                data=bitcoin_data.tx_type.pack(dict(version=1, tx_ins=[], tx_outs=[dict(value=fee, script='hello!'*100)], lock_time=0)).encode('hex'),
                fee=fee,
            ))
        return {
            "version" : 2,
            "previousblockhash" : '%064x' % (self.blocks[-1],),
            "transactions" : txs,
            "coinbaseaux" : {
                "flags" : "062f503253482f"
            },
            "coinbasevalue" : 5000000000 + sum(tx['fee'] for tx in txs),
            "target" : "0000000000000513c50000000000000000000000000000000000000000000000",
            "mintime" : 1351655621,
            "mutable" : [
                "time",
                "transactions",
                "prevblock"
            ],
            "noncerange" : "00000000ffffffff",
            "sigoplimit" : 20000,
            "sizelimit" : 1000000,
            "curtime" : 1351659940,
            "bits" : "21008000",
            "height" : len(self.blocks),
        }

@apply
class mm_provider(object):
    def __getattr__(self, name):
        print '>>>>>>>', name
    def rpc_getauxblock(self, request, result1=None, result2=None):
        if result1 is not None:
            print result1, result2
            return True
        return {
            "target" : "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", # 2**256*2/3
            "hash" : "2756ea0315d46dc3d8d974f34380873fc88863845ac01a658ef11bc3b368af52",
            "chainid" : 1
        }

mynet = math.Object(
    NAME='mynet',
    PARENT=networks.nets['litecoin_testnet'],
    SHARE_PERIOD=5, # seconds
    CHAIN_LENGTH=20*60//3, # shares
    REAL_CHAIN_LENGTH=20*60//3, # shares
    TARGET_LOOKBEHIND=200, # shares
    SPREAD=3, # blocks
    IDENTIFIER='cca5e24ec6408b1e'.decode('hex'),
    PREFIX='ad9614f6466a39cf'.decode('hex'),
    P2P_PORT=19338,
    MIN_TARGET=2**256 - 1,
    MAX_TARGET=2**256 - 1,
    PERSIST=False,
    WORKER_PORT=19327,
    BOOTSTRAP_ADDRS='72.14.191.28'.split(' '),
    ANNOUNCE_CHANNEL='#p2pool-alt',
    VERSION_CHECK=lambda v: True,
)

class MiniNode(object):
    @classmethod
    @defer.inlineCallbacks
    def start(cls, net, factory, bitcoind, peer_ports, merged_urls):
        self = cls()
        
        self.n = node.Node(factory, bitcoind, [], [], net)
        yield self.n.start()
        
        self.n.p2p_node = node.P2PNode(self.n, port=0, max_incoming_conns=1000000, addr_store={}, connect_addrs=[('127.0.0.1', peer_port) for peer_port in peer_ports])
        self.n.p2p_node.start()
        
        wb = work.WorkerBridge(node=self.n, my_pubkey_hash=random.randrange(2**160), donation_percentage=random.uniform(0, 10), merged_urls=merged_urls, worker_fee=3)
        self.wb = wb
        web_root = resource.Resource()
        worker_interface.WorkerInterface(wb).attach_to(web_root)
        self.web_port = reactor.listenTCP(0, server.Site(web_root))
        
        defer.returnValue(self)
    
    @defer.inlineCallbacks
    def stop(self):
        yield self.web_port.stopListening()
        yield self.n.p2p_node.stop()
        yield self.n.stop()
        del self.web_port, self.n

class Test(unittest.TestCase):
    @defer.inlineCallbacks
    def test_node(self):
        bitd = bitcoind()
        
        mm_root = resource.Resource()
        mm_root.putChild('', jsonrpc.HTTPServer(mm_provider))
        mm_port = reactor.listenTCP(0, server.Site(mm_root))
        
        n = node.Node(bitd, bitd, [], [], mynet)
        yield n.start()
        
        wb = work.WorkerBridge(node=n, my_pubkey_hash=42, donation_percentage=2, merged_urls=[('http://127.0.0.1:%i' % (mm_port.getHost().port,), '')], worker_fee=3)
        web_root = resource.Resource()
        worker_interface.WorkerInterface(wb).attach_to(web_root)
        port = reactor.listenTCP(0, server.Site(web_root))
        
        proxy = jsonrpc.HTTPProxy('http://127.0.0.1:' + str(port.getHost().port),
            headers=dict(Authorization='Basic ' + base64.b64encode('user/0:password')))
        
        yield deferral.sleep(3)
        
        for i in xrange(100):
            blah = yield proxy.rpc_getwork()
            yield proxy.rpc_getwork(blah['data'])
        
        
        yield deferral.sleep(3)
        
        assert len(n.tracker.items) == 100
        assert n.tracker.verified.get_height(n.best_share_var.value) == 100
        
        wb.stop()
        n.stop()
        
        yield port.stopListening()
        del n, wb, web_root, port, proxy
        import gc
        gc.collect()
        gc.collect()
        gc.collect()
        
        yield deferral.sleep(20) # waiting for work_poller to exit
        yield mm_port.stopListening()
    #test_node.timeout = 15
    
    @defer.inlineCallbacks
    def test_nodes(self):
        N = 3
        SHARES = 600
        
        bitd = bitcoind()
        
        nodes = []
        for i in xrange(N):
            nodes.append((yield MiniNode.start(mynet, bitd, bitd, [mn.n.p2p_node.serverfactory.listen_port.getHost().port for mn in nodes], [])))
        
        yield deferral.sleep(3)
        
        for i in xrange(SHARES):
            proxy = jsonrpc.HTTPProxy('http://127.0.0.1:' + str(random.choice(nodes).web_port.getHost().port),
                headers=dict(Authorization='Basic ' + base64.b64encode('user/0:password')))
            blah = yield proxy.rpc_getwork()
            yield proxy.rpc_getwork(blah['data'])
            yield deferral.sleep(.05)
            print i
            print type(nodes[0].n.tracker.items[nodes[0].n.best_share_var.value])
        
        # crawl web pages
        from p2pool import web
        stop_event = variable.Event()
        web2_root = web.get_web_root(nodes[0].wb, tempfile.mkdtemp(), variable.Variable(None), stop_event)
        web2_port = reactor.listenTCP(0, server.Site(web2_root))
        for name in web2_root.listNames() + ['web/' + x for x in web2_root.getChildWithDefault('web', None).listNames()]:
            if name in ['web/graph_data', 'web/share', 'web/share_data']: continue
            print
            print name
            try:
                res = yield client.getPage('http://127.0.0.1:%i/%s' % (web2_port.getHost().port, name))
            except:
                import traceback
                traceback.print_exc()
            else:
                print repr(res)[:100]
            print
        yield web2_port.stopListening()
        stop_event.happened()
        del web2_root
        
        yield deferral.sleep(3)
        
        for i, n in enumerate(nodes):
            assert len(n.n.tracker.items) == SHARES, (i, len(n.n.tracker.items))
            assert n.n.tracker.verified.get_height(n.n.best_share_var.value) == SHARES, (i, n.n.tracker.verified.get_height(n.n.best_share_var.value))
            assert type(n.n.tracker.items[nodes[0].n.best_share_var.value]) is (data.Share.SUCCESSOR if data.Share.SUCCESSOR is not None else data.Share)
            assert type(n.n.tracker.items[n.n.tracker.get_nth_parent_hash(nodes[0].n.best_share_var.value, SHARES - 5)]) is data.Share
        
        for n in nodes:
            yield n.stop()
        
        del nodes, n
        import gc
        gc.collect()
        gc.collect()
        gc.collect()
        
        yield deferral.sleep(20) # waiting for work_poller to exit
    test_nodes.timeout = 300

########NEW FILE########
__FILENAME__ = test_p2p
import random

from twisted.internet import defer, endpoints, protocol, reactor
from twisted.trial import unittest

from p2pool import networks, p2p
from p2pool.bitcoin import data as bitcoin_data
from p2pool.util import deferral


class Test(unittest.TestCase):
    @defer.inlineCallbacks
    def test_sharereq(self):
        class MyNode(p2p.Node):
            def __init__(self, df):
                p2p.Node.__init__(self, lambda: None, 29333, networks.nets['bitcoin'], {}, set([('127.0.0.1', 9333)]), 0, 0, 0, 0)
                
                self.df = df
            
            def handle_share_hashes(self, hashes, peer):
                peer.get_shares(
                    hashes=[hashes[0]],
                    parents=5,
                    stops=[],
                ).chainDeferred(self.df)
        
        df = defer.Deferred()
        n = MyNode(df)
        n.start()
        try:
            yield df
        finally:
            yield n.stop()
    
    @defer.inlineCallbacks
    def test_tx_limit(self):
        class MyNode(p2p.Node):
            def __init__(self, df):
                p2p.Node.__init__(self, lambda: None, 29333, networks.nets['bitcoin'], {}, set([('127.0.0.1', 9333)]), 0, 0, 0, 0)
                
                self.df = df
                self.sent_time = 0
            
            @defer.inlineCallbacks
            def got_conn(self, conn):
                p2p.Node.got_conn(self, conn)
                
                yield deferral.sleep(.5)
                
                new_mining_txs = dict(self.mining_txs_var.value)
                for i in xrange(3):
                    huge_tx = dict(
                        version=0,
                        tx_ins=[],
                        tx_outs=[dict(
                            value=0,
                            script='x'*900000,
                        )],
                        lock_time=i,
                    )
                    new_mining_txs[bitcoin_data.hash256(bitcoin_data.tx_type.pack(huge_tx))] = huge_tx
                self.mining_txs_var.set(new_mining_txs)
                
                self.sent_time = reactor.seconds()
            
            def lost_conn(self, conn, reason):
                self.df.callback(None)
        try:
            p2p.Protocol.max_remembered_txs_size *= 10
            
            df = defer.Deferred()
            n = MyNode(df)
            n.start()
            yield df
            if not (n.sent_time <= reactor.seconds() <= n.sent_time + 1):
                raise ValueError('node did not disconnect within 1 seconds of receiving too much tx data')
            yield n.stop()
        finally:
            p2p.Protocol.max_remembered_txs_size //= 10

########NEW FILE########
__FILENAME__ = test_datachunker
import random
import unittest

from p2pool.util import datachunker

def random_bytes(length):
    return ''.join(chr(random.randrange(2**8)) for i in xrange(length))

class Test(unittest.TestCase):
    def test_stringbuffer(self):
        for i in xrange(100):
            sb = datachunker.StringBuffer()
            
            r = random_bytes(random.randrange(1000))
            
            amount_inserted = 0
            while amount_inserted < len(r):
                x = random.randrange(10)
                sb.add(r[amount_inserted:amount_inserted+x])
                amount_inserted += x
            
            amount_removed = 0
            while amount_removed < len(r):
                x = random.randrange(min(10, len(r) - amount_removed) + 1)
                this = sb.get(x)
                assert r[amount_removed:amount_removed+x] == this
                amount_removed += x

########NEW FILE########
__FILENAME__ = test_deferral
import random
import time

from twisted.internet import defer
from twisted.trial import unittest

from p2pool.util import deferral

class Test(unittest.TestCase):
    @defer.inlineCallbacks
    def test_sleep(self):
        for i in xrange(10):
            length = random.expovariate(1/0.1)
            start = time.time()
            yield deferral.sleep(length)
            end = time.time()
            assert length <= end - start <= length + 0.1

########NEW FILE########
__FILENAME__ = test_expiring_dict
from twisted.internet import defer
from twisted.trial import unittest

from p2pool.util import deferral, expiring_dict

class Test(unittest.TestCase):
    @defer.inlineCallbacks
    def test_expiring_dict1(self):
        e = expiring_dict.ExpiringDict(3, get_touches=True)
        e[1] = 2
        yield deferral.sleep(1.5)
        assert 1 in e
        yield deferral.sleep(3)
        assert 1 not in e
    
    @defer.inlineCallbacks
    def test_expiring_dict2(self):
        e = expiring_dict.ExpiringDict(3, get_touches=True)
        e[1] = 2
        yield deferral.sleep(2.25)
        e[1]
        yield deferral.sleep(2.25)
        assert 1 in e
    
    @defer.inlineCallbacks
    def test_expiring_dict3(self):
        e = expiring_dict.ExpiringDict(3, get_touches=False)
        e[1] = 2
        yield deferral.sleep(2.25)
        e[1]
        yield deferral.sleep(2.25)
        assert 1 not in e

########NEW FILE########
__FILENAME__ = test_forest
import random
import unittest

from p2pool.util import forest, math

class DumbTracker(object):
    def __init__(self, items=[]):
        self.items = {} # hash -> item
        self.reverse = {} # previous_hash -> set of item_hashes
        
        for item in items:
            self.add(item)
    
    def add(self, item):
        if item.hash in self.items:
            raise ValueError('item already present')
        self.items[item.hash] = item
        self.reverse.setdefault(item.previous_hash, set()).add(item.hash)
    
    def remove(self, item_hash):
        item = self.items[item_hash]
        del item_hash
        
        self.items.pop(item.hash)
        self.reverse[item.previous_hash].remove(item.hash)
        if not self.reverse[item.previous_hash]:
            self.reverse.pop(item.previous_hash)
    
    @property
    def heads(self):
        return dict((x, self.get_last(x)) for x in self.items if x not in self.reverse)
    
    @property
    def tails(self):
        return dict((x, set(y for y in self.items if self.get_last(y) == x and y not in self.reverse)) for x in self.reverse if x not in self.items)
    
    def get_nth_parent_hash(self, item_hash, n):
        for i in xrange(n):
            item_hash = self.items[item_hash].previous_hash
        return item_hash
    
    def get_height(self, item_hash):
        height, last = self.get_height_and_last(item_hash)
        return height
    
    def get_last(self, item_hash):
        height, last = self.get_height_and_last(item_hash)
        return last
    
    def get_height_and_last(self, item_hash):
        height = 0
        while item_hash in self.items:
            item_hash = self.items[item_hash].previous_hash
            height += 1
        return height, item_hash
    
    def get_chain(self, start_hash, length):
        # same implementation :/
        assert length <= self.get_height(start_hash)
        for i in xrange(length):
            yield self.items[start_hash]
            start_hash = self.items[start_hash].previous_hash
    
    def is_child_of(self, item_hash, possible_child_hash):
        if self.get_last(item_hash) != self.get_last(possible_child_hash):
            return None
        while True:
            if possible_child_hash == item_hash:
                return True
            if possible_child_hash not in self.items:
                return False
            possible_child_hash = self.items[possible_child_hash].previous_hash

class FakeShare(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self._attrs = kwargs

def test_tracker(self):
    t = DumbTracker(self.items.itervalues())
    
    assert self.items == t.items, (self.items, t.items)
    assert self.reverse == t.reverse, (self.reverse, t.reverse)
    assert self.heads == t.heads, (self.heads, t.heads)
    assert self.tails == t.tails, (self.tails, t.tails)
    
    if random.random() < 0.9:
        return
    
    for start in self.items:
        a, b = self.get_height_and_last(start), t.get_height_and_last(start)
        assert a == b, (a, b)
        
        other = random.choice(self.items.keys())
        assert self.is_child_of(start, other) == t.is_child_of(start, other)
        assert self.is_child_of(other, start) == t.is_child_of(other, start)
        
        length = random.randrange(a[0])
        assert list(self.get_chain(start, length)) == list(t.get_chain(start, length))

def generate_tracker_simple(n):
    t = forest.Tracker(math.shuffled(FakeShare(hash=i, previous_hash=i - 1 if i > 0 else None) for i in xrange(n)))
    test_tracker(t)
    return t

def generate_tracker_random(n):
    items = []
    for i in xrange(n):
        x = random.choice(items + [FakeShare(hash=None), FakeShare(hash=random.randrange(1000000, 2000000))]).hash
        items.append(FakeShare(hash=i, previous_hash=x))
    t = forest.Tracker(math.shuffled(items))
    test_tracker(t)
    return t

class Test(unittest.TestCase):
    def test_tracker(self):
        t = generate_tracker_simple(100)
        
        assert t.heads == {99: None}
        assert t.tails == {None: set([99])}
        
        assert t.get_nth_parent_hash(90, 50) == 90 - 50
        assert t.get_nth_parent_hash(91, 42) == 91 - 42
    
    def test_get_nth_parent_hash(self):
        t = generate_tracker_simple(200)
        
        for i in xrange(1000):
            a = random.randrange(200)
            b = random.randrange(a + 1)
            res = t.get_nth_parent_hash(a, b)
            assert res == a - b, (a, b, res)
    
    def test_tracker2(self):
        for ii in xrange(20):
            t = generate_tracker_random(random.randrange(100))
            #print "--start--"
            while t.items:
                while True:
                    try:
                        t.remove(random.choice(list(t.items)))
                    except NotImplementedError:
                        pass # print "aborted", x
                    else:
                        break
                test_tracker(t)
    
    def test_tracker3(self):
        for ii in xrange(10):
            items = []
            for i in xrange(random.randrange(100)):
                x = random.choice(items + [FakeShare(hash=None), FakeShare(hash=random.randrange(1000000, 2000000))]).hash
                items.append(FakeShare(hash=i, previous_hash=x))
            
            t = forest.Tracker()
            test_tracker(t)
            
            for item in math.shuffled(items):
                t.add(item)
                test_tracker(t)
                if random.randrange(3) == 0:
                    while True:
                        try:
                            t.remove(random.choice(list(t.items)))
                        except NotImplementedError:
                            pass
                        else:
                            break
                    test_tracker(t)
            
            for item in math.shuffled(items):
                if item.hash not in t.items:
                    t.add(item)
                    test_tracker(t)
                if random.randrange(3) == 0:
                    while True:
                        try:
                            t.remove(random.choice(list(t.items)))
                        except NotImplementedError:
                            pass
                        else:
                            break
                    test_tracker(t)
            
            while t.items:
                while True:
                    try:
                        t.remove(random.choice(list(t.items)))
                    except NotImplementedError:
                        pass
                    else:
                        break
                test_tracker(t)

########NEW FILE########
__FILENAME__ = test_graph
import unittest

from p2pool.util import graph

class Test(unittest.TestCase):
    def test_keep_largest(self):
        b = dict(a=1, b=3, c=5, d=7, e=9)
        assert graph.keep_largest(3, 'squashed')(b) == {'squashed': 9, 'd': 7, 'e': 9}
        assert graph.keep_largest(3)(b) == {'c': 5, 'd': 7, 'e': 9}

########NEW FILE########
__FILENAME__ = test_math
from __future__ import division

import random
import unittest

from p2pool.util import math

def generate_alphabet():
    if random.randrange(2):
        return None
    else:
        a = map(chr, xrange(256))
        random.shuffle(a)
        return a[:random.randrange(2, len(a))]

class Test(unittest.TestCase):
    def test_add_tuples(self):
        assert math.add_tuples((1, 2, 3), (4, 5, 6)) == (5, 7, 9)
    
    def test_bases(self):
        for i in xrange(10):
            alphabet = generate_alphabet()
            for i in xrange(100):
                n = random.choice([
                    random.randrange(3),
                    random.randrange(300),
                    random.randrange(100000000000000000000000000000),
                ])
                s = math.natural_to_string(n, alphabet)
                n2 = math.string_to_natural(s, alphabet)
                #print n, s.encode('hex'), n2
                self.assertEquals(n, n2)
    
    def test_binom(self):
        for n in xrange(1, 100):
            for x in xrange(n + 1):
                left, right = math.binomial_conf_interval(x, n)
                assert 0 <= left <= x/n <= right <= 1, (left, right, x, n)

########NEW FILE########
__FILENAME__ = test_pack
import unittest

from p2pool.util import pack

class Test(unittest.TestCase):
    def test_VarInt(self):
        t = pack.VarIntType()
        for i in xrange(2**20):
            assert t.unpack(t.pack(i)) == i
        for i in xrange(2**36, 2**36+25):
            assert t.unpack(t.pack(i)) == i

########NEW FILE########
__FILENAME__ = test_skiplist
from p2pool.util import skiplist

class NotSkipList(object):
    def __call__(self, start, *args):
        pos = start
        sol = self.initial_solution(start, args)
        while True:
            decision = self.judge(sol, args)
            if decision > 0:
                raise AssertionError()
            elif decision == 0:
                return self.finalize(sol)
            
            delta = self.get_delta(pos)
            sol = self.apply_delta(sol, delta, args)
            
            pos = self.previous(pos)
    
    def finalize(self, sol):
        return sol

skiplist.SkipList

########NEW FILE########
__FILENAME__ = datachunker
import collections

class StringBuffer(object):
    'Buffer manager with great worst-case behavior'
    
    def __init__(self, data=''):
        self.buf = collections.deque([data])
        self.buf_len = len(data)
        self.pos = 0
    
    def __len__(self):
        return self.buf_len - self.pos
    
    def add(self, data):
        self.buf.append(data)
        self.buf_len += len(data)
    
    def get(self, wants):
        if self.buf_len - self.pos < wants:
            raise IndexError('not enough data')
        data = []
        while wants:
            seg = self.buf[0][self.pos:self.pos+wants]
            self.pos += len(seg)
            while self.buf and self.pos >= len(self.buf[0]):
                x = self.buf.popleft()
                self.buf_len -= len(x)
                self.pos -= len(x)
            
            data.append(seg)
            wants -= len(seg)
        return ''.join(data)

def _DataChunker(receiver):
    wants = receiver.next()
    buf = StringBuffer()
    
    while True:
        if len(buf) >= wants:
            wants = receiver.send(buf.get(wants))
        else:
            buf.add((yield))
def DataChunker(receiver):
    '''
    Produces a function that accepts data that is input into a generator
    (receiver) in response to the receiver yielding the size of data to wait on
    '''
    x = _DataChunker(receiver)
    x.next()
    return x.send

########NEW FILE########
__FILENAME__ = deferral
from __future__ import division

import itertools
import random
import sys

from twisted.internet import defer, reactor
from twisted.python import failure, log

def sleep(t):
    d = defer.Deferred(canceller=lambda d_: dc.cancel())
    dc = reactor.callLater(t, d.callback, None)
    return d

def run_repeatedly(f, *args, **kwargs):
    current_dc = [None]
    def step():
        delay = f(*args, **kwargs)
        current_dc[0] = reactor.callLater(delay, step)
    step()
    def stop():
        current_dc[0].cancel()
    return stop

class RetrySilentlyException(Exception):
    pass

def retry(message='Error:', delay=3, max_retries=None, traceback=True):
    '''
    @retry('Error getting block:', 1)
    @defer.inlineCallbacks
    def get_block(hash):
        ...
    '''
    
    def retry2(func):
        @defer.inlineCallbacks
        def f(*args, **kwargs):
            for i in itertools.count():
                try:
                    result = yield func(*args, **kwargs)
                except Exception, e:
                    if i == max_retries:
                        raise
                    if not isinstance(e, RetrySilentlyException):
                        if traceback:
                            log.err(None, message)
                        else:
                            print >>sys.stderr, message, e
                    yield sleep(delay)
                else:
                    defer.returnValue(result)
        return f
    return retry2

class ReplyMatcher(object):
    '''
    Converts request/got response interface to deferred interface
    '''
    
    def __init__(self, func, timeout=5):
        self.func = func
        self.timeout = timeout
        self.map = {}
    
    def __call__(self, id):
        if id not in self.map:
            self.func(id)
        df = defer.Deferred()
        def timeout():
            self.map[id].remove((df, timer))
            if not self.map[id]:
                del self.map[id]
            df.errback(failure.Failure(defer.TimeoutError('in ReplyMatcher')))
        timer = reactor.callLater(self.timeout, timeout)
        self.map.setdefault(id, set()).add((df, timer))
        return df
    
    def got_response(self, id, resp):
        if id not in self.map:
            return
        for df, timer in self.map.pop(id):
            df.callback(resp)
            timer.cancel()

class GenericDeferrer(object):
    '''
    Converts query with identifier/got response interface to deferred interface
    '''
    
    def __init__(self, max_id, func, timeout=5, on_timeout=lambda: None):
        self.max_id = max_id
        self.func = func
        self.timeout = timeout
        self.on_timeout = on_timeout
        self.map = {}
    
    def __call__(self, *args, **kwargs):
        while True:
            id = random.randrange(self.max_id)
            if id not in self.map:
                break
        def cancel(df):
            df, timer = self.map.pop(id)
            timer.cancel()
        try:
            df = defer.Deferred(cancel)
        except TypeError:
            df = defer.Deferred() # handle older versions of Twisted
        def timeout():
            self.map.pop(id)
            df.errback(failure.Failure(defer.TimeoutError('in GenericDeferrer')))
            self.on_timeout()
        timer = reactor.callLater(self.timeout, timeout)
        self.map[id] = df, timer
        self.func(id, *args, **kwargs)
        return df
    
    def got_response(self, id, resp):
        if id not in self.map:
            return
        df, timer = self.map.pop(id)
        timer.cancel()
        df.callback(resp)
    
    def respond_all(self, resp):
        while self.map:
            id, (df, timer) = self.map.popitem()
            timer.cancel()
            df.errback(resp)

class NotNowError(Exception):
    pass

class DeferredCacher(object):
    '''
    like memoize, but for functions that return Deferreds
    
    @DeferredCacher
    def f(x):
        ...
        return df
    
    @DeferredCacher.with_backing(bsddb.hashopen(...))
    def f(x):
        ...
        return df
    '''
    
    @classmethod
    def with_backing(cls, backing):
        return lambda func: cls(func, backing)
    
    def __init__(self, func, backing=None):
        if backing is None:
            backing = {}
        
        self.func = func
        self.backing = backing
        self.waiting = {}
    
    @defer.inlineCallbacks
    def __call__(self, key):
        if key in self.waiting:
            yield self.waiting[key]
        
        if key in self.backing:
            defer.returnValue(self.backing[key])
        else:
            self.waiting[key] = defer.Deferred()
            try:
                value = yield self.func(key)
            finally:
                self.waiting.pop(key).callback(None)
        
        self.backing[key] = value
        defer.returnValue(value)
    
    _nothing = object()
    def call_now(self, key, default=_nothing):
        if key in self.backing:
            return self.backing[key]
        if key not in self.waiting:
            self.waiting[key] = defer.Deferred()
            def cb(value):
                self.backing[key] = value
                self.waiting.pop(key).callback(None)
            def eb(fail):
                self.waiting.pop(key).callback(None)
                if fail.check(RetrySilentlyException):
                    return
                print
                print 'Error when requesting noncached value:'
                fail.printTraceback()
                print
            self.func(key).addCallback(cb).addErrback(eb)
        if default is not self._nothing:
            return default
        raise NotNowError(key)

def deferred_has_been_called(df):
    still_running = True
    res2 = []
    def cb(res):
        if still_running:
            res2[:] = [res]
        else:
            return res
    df.addBoth(cb)
    still_running = False
    if res2:
        return True, res2[0]
    return False, None
def inlineCallbacks(f):
    from functools import wraps
    @wraps(f)
    def _(*args, **kwargs):
        gen = f(*args, **kwargs)
        stop_running = [False]
        def cancelled(df_):
            assert df_ is df
            stop_running[0] = True
            if currently_waiting_on:
                currently_waiting_on[0].cancel()
        df = defer.Deferred(cancelled)
        currently_waiting_on = []
        def it(cur):
            while True:
                try:
                    if isinstance(cur, failure.Failure):
                        res = cur.throwExceptionIntoGenerator(gen) # external code is run here
                    else:
                        res = gen.send(cur) # external code is run here
                    if stop_running[0]:
                        return
                except StopIteration:
                    df.callback(None)
                except defer._DefGen_Return as e:
                    # XXX should make sure direct child threw
                    df.callback(e.value)
                except:
                    df.errback()
                else:
                    if isinstance(res, defer.Deferred):
                        called, res2 = deferred_has_been_called(res)
                        if called:
                            cur = res2
                            continue
                        else:
                            currently_waiting_on[:] = [res]
                            def gotResult(res2):
                                assert currently_waiting_on[0] is res
                                currently_waiting_on[:] = []
                                if stop_running[0]:
                                    return
                                it(res2)
                            res.addBoth(gotResult) # external code is run between this and gotResult
                    else:
                        cur = res
                        continue
                break
        it(None)
        return df
    return _



class RobustLoopingCall(object):
    def __init__(self, func, *args, **kwargs):
        self.func, self.args, self.kwargs = func, args, kwargs
        
        self.running = False
    
    def start(self, period):
        assert not self.running
        self.running = True
        self._df = self._worker(period).addErrback(lambda fail: fail.trap(defer.CancelledError))
    
    @inlineCallbacks
    def _worker(self, period):
        assert self.running
        while self.running:
            try:
                self.func(*self.args, **self.kwargs)
            except:
                log.err()
            yield sleep(period)
    
    def stop(self):
        assert self.running
        self.running = False
        self._df.cancel()
        return self._df

########NEW FILE########
__FILENAME__ = deferred_resource
from __future__ import division

from twisted.internet import defer
from twisted.web import resource, server
from twisted.python import log

class DeferredResource(resource.Resource):
    def render(self, request):
        def finish(x):
            if request.channel is None: # disconnected
                return
            if x is not None:
                request.write(x)
            request.finish()
        
        def finish_error(fail):
            if request.channel is None: # disconnected
                return
            request.setResponseCode(500) # won't do anything if already written to
            request.write('---ERROR---')
            request.finish()
            log.err(fail, "Error in DeferredResource handler:")
        
        defer.maybeDeferred(resource.Resource.render, self, request).addCallbacks(finish, finish_error)
        return server.NOT_DONE_YET

########NEW FILE########
__FILENAME__ = expiring_dict
from __future__ import division

import time
import weakref

from p2pool.util import deferral

class Node(object):
    def __init__(self, contents, prev=None, next=None):
        self.contents, self.prev, self.next = contents, prev, next
    
    def insert_before(self, contents):
        self.prev.next = self.prev = node = Node(contents, self.prev, self)
        return node
    
    def insert_after(self, contents):
        self.next.prev = self.next = node = Node(contents, self, self.next)
        return node
    
    @staticmethod
    def connect(prev, next):
        if prev.next is not None or next.prev is not None:
            raise ValueError('node already connected')
        prev.next, next.prev = next, prev
    
    def replace(self, contents):
        self.contents = contents
    
    def delete(self):
        if self.prev.next is None or self.next.prev is None:
            raise ValueError('node not connected')
        self.prev.next, self.next.prev = self.next, self.prev
        self.next = self.prev = None


class LinkedList(object):
    def __init__(self, iterable=[]):
        self.start, self.end = Node(None), Node(None)
        Node.connect(self.start, self.end)
        
        for item in iterable:
            self.append(item)
    
    def __repr__(self):
        return 'LinkedList(%r)' % (list(self),)
    
    def __len__(self):
        return sum(1 for x in self)
    
    def __iter__(self):
        cur = self.start.next
        while cur is not self.end:
            cur2 = cur
            cur = cur.next
            yield cur2 # in case cur is deleted, but items inserted after are ignored
    
    def __reversed__(self):
        cur = self.end.prev
        while cur is not self.start:
            cur2 = cur
            cur = cur.prev
            yield cur2
    
    def __getitem__(self, index):
        if index < 0:
            cur = self.end
            for i in xrange(-index):
                cur = cur.prev
                if cur is self.start:
                    raise IndexError('index out of range')
        else:
            cur = self.start
            for i in xrange(index + 1):
                cur = cur.next
                if cur is self.end:
                    raise IndexError('index out of range')
        return cur
    
    def appendleft(self, item):
        return self.start.insert_after(item)
    
    def append(self, item):
        return self.end.insert_before(item)
    
    def popleft(self):
        node = self.start.next
        if node is self.end:
            raise IndexError('popleft from empty')
        node.delete()
        return node.contents
    
    def pop(self):
        node = self.end.prev
        if node is self.start:
            raise IndexError('pop from empty')
        node.delete()
        return node.contents


class ExpiringDict(object):
    def __init__(self, expiry_time, get_touches=True):
        self.expiry_time = expiry_time
        self.get_touches = get_touches
        
        self.expiry_deque = LinkedList()
        self.d = dict() # key -> node, value
        
        self_ref = weakref.ref(self, lambda _: expire_loop.stop() if expire_loop.running else None)
        self._expire_loop = expire_loop = deferral.RobustLoopingCall(lambda: self_ref().expire())
        expire_loop.start(1)
    
    def stop(self):
        self._expire_loop.stop()
    
    def __repr__(self):
        return 'ExpiringDict' + repr(self.__dict__)
    
    def __len__(self):
        return len(self.d)
    
    _nothing = object()
    def touch(self, key, value=_nothing):
        'Updates expiry node, optionally replacing value, returning new value'
        if value is self._nothing or key in self.d:
            node, old_value = self.d[key]
            node.delete()
        
        new_value = old_value if value is self._nothing else value
        self.d[key] = self.expiry_deque.append((time.time() + self.expiry_time, key)), new_value
        return new_value
    
    def expire(self):
        t = time.time()
        for node in self.expiry_deque:
            timestamp, key = node.contents
            if timestamp > t:
                break
            del self.d[key]
            node.delete()
    
    def __contains__(self, key):
        return key in self.d
    
    def __getitem__(self, key):
        if self.get_touches:
            value = self.touch(key)
        else:
            node, value = self.d[key]
        return value
    
    def __setitem__(self, key, value):
        self.touch(key, value)
    
    def __delitem__(self, key):
        node, value = self.d.pop(key)
        node.delete()
    
    def get(self, key, default_value=None):
        if key in self.d:
            res = self[key]
        else:
            res = default_value
        return res
    
    def setdefault(self, key, default_value):
        if key in self.d:
            return self[key]
        else:
            self[key] = default_value
            return default_value
    
    def keys(self):
        return self.d.keys()
    
    def values(self):
        return [value for node, value in self.d.itervalues()]
    
    def itervalues(self):
        for node, value in self.d.itervalues():
            yield value

########NEW FILE########
__FILENAME__ = fixargparse
from __future__ import absolute_import

import argparse
import sys


class FixedArgumentParser(argparse.ArgumentParser):
    '''
    fixes argparse's handling of empty string arguments
and changes @filename behaviour to accept multiple arguments on each line
    '''
    
    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:
            
            # for regular arguments, just add them back into the list
            if not arg_string or arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)
            
            # replace arguments referencing files with the file content
            else:
                try:
                    args_file = open(arg_string[1:])
                    try:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                    finally:
                        args_file.close()
                except IOError:
                    err = sys.exc_info()[1]
                    self.error(str(err))
        
        # return the modified argument list
        return new_arg_strings
    
    def convert_arg_line_to_args(self, arg_line):
        return [arg for arg in arg_line.split() if arg.strip()]

########NEW FILE########
__FILENAME__ = forest
'''
forest data structure
'''

import itertools

from p2pool.util import skiplist, variable


class TrackerSkipList(skiplist.SkipList):
    def __init__(self, tracker):
        skiplist.SkipList.__init__(self)
        self.tracker = tracker
        
        self.tracker.removed.watch_weakref(self, lambda self, item: self.forget_item(item.hash))
    
    def previous(self, element):
        return self.tracker._delta_type.from_element(self.tracker.items[element]).tail


class DistanceSkipList(TrackerSkipList):
    def get_delta(self, element):
        return element, 1, self.previous(element)
    
    def combine_deltas(self, (from_hash1, dist1, to_hash1), (from_hash2, dist2, to_hash2)):
        if to_hash1 != from_hash2:
            raise AssertionError()
        return from_hash1, dist1 + dist2, to_hash2
    
    def initial_solution(self, start, (n,)):
        return 0, start
    
    def apply_delta(self, (dist1, to_hash1), (from_hash2, dist2, to_hash2), (n,)):
        if to_hash1 != from_hash2:
            raise AssertionError()
        return dist1 + dist2, to_hash2
    
    def judge(self, (dist, hash), (n,)):
        if dist > n:
            return 1
        elif dist == n:
            return 0
        else:
            return -1
    
    def finalize(self, (dist, hash), (n,)):
        assert dist == n
        return hash

def get_attributedelta_type(attrs): # attrs: {name: func}
    class ProtoAttributeDelta(object):
        __slots__ = ['head', 'tail'] + attrs.keys()
        
        @classmethod
        def get_none(cls, element_id):
            return cls(element_id, element_id, **dict((k, 0) for k in attrs))
        
        @classmethod
        def from_element(cls, item):
            return cls(item.hash, item.previous_hash, **dict((k, v(item)) for k, v in attrs.iteritems()))
        
        @staticmethod
        def get_head(item):
            return item.hash
        
        @staticmethod
        def get_tail(item):
            return item.previous_hash
        
        def __init__(self, head, tail, **kwargs):
            self.head, self.tail = head, tail
            for k, v in kwargs.iteritems():
                setattr(self, k, v)
        
        def __add__(self, other):
            assert self.tail == other.head
            return self.__class__(self.head, other.tail, **dict((k, getattr(self, k) + getattr(other, k)) for k in attrs))
        
        def __sub__(self, other):
            if self.head == other.head:
                return self.__class__(other.tail, self.tail, **dict((k, getattr(self, k) - getattr(other, k)) for k in attrs))
            elif self.tail == other.tail:
                return self.__class__(self.head, other.head, **dict((k, getattr(self, k) - getattr(other, k)) for k in attrs))
            else:
                raise AssertionError()
        
        def __repr__(self):
            return '%s(%r, %r%s)' % (self.__class__, self.head, self.tail, ''.join(', %s=%r' % (k, getattr(self, k)) for k in attrs))
    ProtoAttributeDelta.attrs = attrs
    return ProtoAttributeDelta

AttributeDelta = get_attributedelta_type(dict(
    height=lambda item: 1,
))

class TrackerView(object):
    def __init__(self, tracker, delta_type):
        self._tracker = tracker
        self._delta_type = delta_type
        
        self._deltas = {} # item_hash -> delta, ref
        self._reverse_deltas = {} # ref -> set of item_hashes
        
        self._ref_generator = itertools.count()
        self._delta_refs = {} # ref -> delta
        self._reverse_delta_refs = {} # delta.tail -> ref
        
        self._tracker.remove_special.watch_weakref(self, lambda self, item: self._handle_remove_special(item))
        self._tracker.remove_special2.watch_weakref(self, lambda self, item: self._handle_remove_special2(item))
        self._tracker.removed.watch_weakref(self, lambda self, item: self._handle_removed(item))
    
    def _handle_remove_special(self, item):
        delta = self._delta_type.from_element(item)
        
        if delta.tail not in self._reverse_delta_refs:
            return
        
        # move delta refs referencing children down to this, so they can be moved up in one step
        for x in list(self._reverse_deltas.get(self._reverse_delta_refs.get(delta.head, object()), set())):
            self.get_last(x)
        
        assert delta.head not in self._reverse_delta_refs, list(self._reverse_deltas.get(self._reverse_delta_refs.get(delta.head, object()), set()))
        
        if delta.tail not in self._reverse_delta_refs:
            return
        
        # move ref pointing to this up
        
        ref = self._reverse_delta_refs[delta.tail]
        cur_delta = self._delta_refs[ref]
        assert cur_delta.tail == delta.tail
        self._delta_refs[ref] = cur_delta - delta
        assert self._delta_refs[ref].tail == delta.head
        del self._reverse_delta_refs[delta.tail]
        self._reverse_delta_refs[delta.head] = ref
    
    def _handle_remove_special2(self, item):
        delta = self._delta_type.from_element(item)
        
        if delta.tail not in self._reverse_delta_refs:
            return
        
        ref = self._reverse_delta_refs.pop(delta.tail)
        del self._delta_refs[ref]
        
        for x in self._reverse_deltas.pop(ref):
            del self._deltas[x]
    
    def _handle_removed(self, item):
        delta = self._delta_type.from_element(item)
        
        # delete delta entry and ref if it is empty
        if delta.head in self._deltas:
            delta1, ref = self._deltas.pop(delta.head)
            self._reverse_deltas[ref].remove(delta.head)
            if not self._reverse_deltas[ref]:
                del self._reverse_deltas[ref]
                delta2 = self._delta_refs.pop(ref)
                del self._reverse_delta_refs[delta2.tail]
    
    
    def get_height(self, item_hash):
        return self.get_delta_to_last(item_hash).height
    
    def get_work(self, item_hash):
        return self.get_delta_to_last(item_hash).work
    
    def get_last(self, item_hash):
        return self.get_delta_to_last(item_hash).tail
    
    def get_height_and_last(self, item_hash):
        delta = self.get_delta_to_last(item_hash)
        return delta.height, delta.tail
    
    def _get_delta(self, item_hash):
        if item_hash in self._deltas:
            delta1, ref = self._deltas[item_hash]
            delta2 = self._delta_refs[ref]
            res = delta1 + delta2
        else:
            res = self._delta_type.from_element(self._tracker.items[item_hash])
        assert res.head == item_hash
        return res
    
    def _set_delta(self, item_hash, delta):
        other_item_hash = delta.tail
        if other_item_hash not in self._reverse_delta_refs:
            ref = self._ref_generator.next()
            assert ref not in self._delta_refs
            self._delta_refs[ref] = self._delta_type.get_none(other_item_hash)
            self._reverse_delta_refs[other_item_hash] = ref
            del ref
        
        ref = self._reverse_delta_refs[other_item_hash]
        ref_delta = self._delta_refs[ref]
        assert ref_delta.tail == other_item_hash
        
        if item_hash in self._deltas:
            prev_ref = self._deltas[item_hash][1]
            self._reverse_deltas[prev_ref].remove(item_hash)
            if not self._reverse_deltas[prev_ref] and prev_ref != ref:
                self._reverse_deltas.pop(prev_ref)
                x = self._delta_refs.pop(prev_ref)
                self._reverse_delta_refs.pop(x.tail)
        self._deltas[item_hash] = delta - ref_delta, ref
        self._reverse_deltas.setdefault(ref, set()).add(item_hash)
    
    def get_delta_to_last(self, item_hash):
        assert isinstance(item_hash, (int, long, type(None)))
        delta = self._delta_type.get_none(item_hash)
        updates = []
        while delta.tail in self._tracker.items:
            updates.append((delta.tail, delta))
            this_delta = self._get_delta(delta.tail)
            delta += this_delta
        for update_hash, delta_then in updates:
            self._set_delta(update_hash, delta - delta_then)
        return delta
    
    def get_delta(self, item, ancestor):
        assert self._tracker.is_child_of(ancestor, item)
        return self.get_delta_to_last(item) - self.get_delta_to_last(ancestor)

class Tracker(object):
    def __init__(self, items=[], delta_type=AttributeDelta):
        self.items = {} # hash -> item
        self.reverse = {} # delta.tail -> set of item_hashes
        
        self.heads = {} # head hash -> tail_hash
        self.tails = {} # tail hash -> set of head hashes
        
        self.added = variable.Event()
        self.remove_special = variable.Event()
        self.remove_special2 = variable.Event()
        self.removed = variable.Event()
        
        self.get_nth_parent_hash = DistanceSkipList(self)
        
        self._delta_type = delta_type
        self._default_view = TrackerView(self, delta_type)
        
        for item in items:
            self.add(item)
    
    def __getattr__(self, name):
        attr = getattr(self._default_view, name)
        setattr(self, name, attr)
        return attr
    
    def add(self, item):
        assert not isinstance(item, (int, long, type(None)))
        delta = self._delta_type.from_element(item)
        
        if delta.head in self.items:
            raise ValueError('item already present')
        
        if delta.head in self.tails:
            heads = self.tails.pop(delta.head)
        else:
            heads = set([delta.head])
        
        if delta.tail in self.heads:
            tail = self.heads.pop(delta.tail)
        else:
            tail = self.get_last(delta.tail)
        
        self.items[delta.head] = item
        self.reverse.setdefault(delta.tail, set()).add(delta.head)
        
        self.tails.setdefault(tail, set()).update(heads)
        if delta.tail in self.tails[tail]:
            self.tails[tail].remove(delta.tail)
        
        for head in heads:
            self.heads[head] = tail
        
        self.added.happened(item)
    
    def remove(self, item_hash):
        assert isinstance(item_hash, (int, long, type(None)))
        if item_hash not in self.items:
            raise KeyError()
        
        item = self.items[item_hash]
        del item_hash
        
        delta = self._delta_type.from_element(item)
        
        children = self.reverse.get(delta.head, set())
        
        if delta.head in self.heads and delta.tail in self.tails:
            tail = self.heads.pop(delta.head)
            self.tails[tail].remove(delta.head)
            if not self.tails[delta.tail]:
                self.tails.pop(delta.tail)
        elif delta.head in self.heads:
            tail = self.heads.pop(delta.head)
            self.tails[tail].remove(delta.head)
            if self.reverse[delta.tail] != set([delta.head]):
                pass # has sibling
            else:
                self.tails[tail].add(delta.tail)
                self.heads[delta.tail] = tail
        elif delta.tail in self.tails and len(self.reverse[delta.tail]) <= 1:
            heads = self.tails.pop(delta.tail)
            for head in heads:
                self.heads[head] = delta.head
            self.tails[delta.head] = set(heads)
            
            self.remove_special.happened(item)
        elif delta.tail in self.tails and len(self.reverse[delta.tail]) > 1:
            heads = [x for x in self.tails[delta.tail] if self.is_child_of(delta.head, x)]
            self.tails[delta.tail] -= set(heads)
            if not self.tails[delta.tail]:
                self.tails.pop(delta.tail)
            for head in heads:
                self.heads[head] = delta.head
            assert delta.head not in self.tails
            self.tails[delta.head] = set(heads)
            
            self.remove_special2.happened(item)
        else:
            raise NotImplementedError()
        
        self.items.pop(delta.head)
        self.reverse[delta.tail].remove(delta.head)
        if not self.reverse[delta.tail]:
            self.reverse.pop(delta.tail)
        
        self.removed.happened(item)
    
    def get_chain(self, start_hash, length):
        assert length <= self.get_height(start_hash)
        for i in xrange(length):
            item = self.items[start_hash]
            yield item
            start_hash = self._delta_type.get_tail(item)
    
    def is_child_of(self, item_hash, possible_child_hash):
        height, last = self.get_height_and_last(item_hash)
        child_height, child_last = self.get_height_and_last(possible_child_hash)
        if child_last != last:
            return None # not connected, so can't be determined
        height_up = child_height - height
        return height_up >= 0 and self.get_nth_parent_hash(possible_child_hash, height_up) == item_hash

class SubsetTracker(Tracker):
    def __init__(self, subset_of, **kwargs):
        Tracker.__init__(self, **kwargs)
        self.get_nth_parent_hash = subset_of.get_nth_parent_hash # overwrites Tracker.__init__'s
        self._subset_of = subset_of
    
    def add(self, item):
        if self._subset_of is not None:
            assert self._delta_type.get_head(item) in self._subset_of.items
        Tracker.add(self, item)
    
    def remove(self, item_hash):
        if self._subset_of is not None:
            assert item_hash in self._subset_of.items
        Tracker.remove(self, item_hash)

########NEW FILE########
__FILENAME__ = graph
from __future__ import absolute_import
from __future__ import division

import math

from p2pool.util import math as math2


class DataViewDescription(object):
    def __init__(self, bin_count, total_width):
        self.bin_count = bin_count
        self.bin_width = total_width/bin_count

def _shift(x, shift, pad_item):
    left_pad = math2.clip(shift, (0, len(x)))
    right_pad = math2.clip(-shift, (0, len(x)))
    return [pad_item]*left_pad + x[right_pad:-left_pad if left_pad else None] + [pad_item]*right_pad

combine_bins = math2.add_dicts_ext(lambda (a1, b1), (a2, b2): (a1+a2, b1+b2), (0, 0))

nothing = object()
def keep_largest(n, squash_key=nothing, key=lambda x: x, add_func=lambda a, b: a+b):
    def _(d):
        items = sorted(d.iteritems(), key=lambda (k, v): (k != squash_key, key(v)), reverse=True)
        while len(items) > n:
            k, v = items.pop()
            if squash_key is not nothing:
                items[-1] = squash_key, add_func(items[-1][1], v)
        return dict(items)
    return _

def _shift_bins_so_t_is_not_past_end(bins, last_bin_end, bin_width, t):
    # returns new_bins, new_last_bin_end
    shift = max(0, int(math.ceil((t - last_bin_end)/bin_width)))
    return _shift(bins, shift, {}), last_bin_end + shift*bin_width

class DataView(object):
    def __init__(self, desc, ds_desc, last_bin_end, bins):
        assert len(bins) == desc.bin_count
        
        self.desc = desc
        self.ds_desc = ds_desc
        self.last_bin_end = last_bin_end
        self.bins = bins
    
    def _add_datum(self, t, value):
        if not self.ds_desc.multivalues:
            value = {'null': value}
        elif self.ds_desc.multivalue_undefined_means_0 and 'null' not in value:
            value = dict(value, null=0) # use null to hold sample counter
        self.bins, self.last_bin_end = _shift_bins_so_t_is_not_past_end(self.bins, self.last_bin_end, self.desc.bin_width, t)
        
        bin = int(math.floor((self.last_bin_end - t)/self.desc.bin_width))
        assert bin >= 0
        if bin < self.desc.bin_count:
            self.bins[bin] = self.ds_desc.keep_largest_func(combine_bins(self.bins[bin], dict((k, (v, 1)) for k, v in value.iteritems())))
    
    def get_data(self, t):
        bins, last_bin_end = _shift_bins_so_t_is_not_past_end(self.bins, self.last_bin_end, self.desc.bin_width, t)
        assert last_bin_end - self.desc.bin_width <= t <= last_bin_end
        
        def _((i, bin)):
            left, right = last_bin_end - self.desc.bin_width*(i + 1), min(t, last_bin_end - self.desc.bin_width*i)
            center, width = (left+right)/2, right-left
            if self.ds_desc.is_gauge and self.ds_desc.multivalue_undefined_means_0:
                real_count = max([0] + [count for total, count in bin.itervalues()])
                if real_count == 0:
                    val = None
                else:
                    val = dict((k, total/real_count) for k, (total, count) in bin.iteritems())
                default = 0
            elif self.ds_desc.is_gauge and not self.ds_desc.multivalue_undefined_means_0:
                val = dict((k, total/count) for k, (total, count) in bin.iteritems())
                default = None
            else:
                val = dict((k, total/width) for k, (total, count) in bin.iteritems())
                default = 0
            if not self.ds_desc.multivalues:
                val = None if val is None else val.get('null', default)
            return center, val, width, default
        return map(_, enumerate(bins))


class DataStreamDescription(object):
    def __init__(self, dataview_descriptions, is_gauge=True, multivalues=False, multivalues_keep=20, multivalues_squash_key=None, multivalue_undefined_means_0=False, default_func=None):
        self.dataview_descriptions = dataview_descriptions
        self.is_gauge = is_gauge
        self.multivalues = multivalues
        self.keep_largest_func = keep_largest(multivalues_keep, multivalues_squash_key, key=lambda (t, c): t/c if self.is_gauge else t, add_func=lambda (a1, b1), (a2, b2): (a1+a2, b1+b2))
        self.multivalue_undefined_means_0 = multivalue_undefined_means_0
        self.default_func = default_func

class DataStream(object):
    def __init__(self, desc, dataviews):
        self.desc = desc
        self.dataviews = dataviews
    
    def add_datum(self, t, value=1):
        for dv_name, dv in self.dataviews.iteritems():
            dv._add_datum(t, value)


class HistoryDatabase(object):
    @classmethod
    def from_obj(cls, datastream_descriptions, obj={}):
        def convert_bin(bin):
            if isinstance(bin, dict):
                return bin
            total, count = bin
            if not isinstance(total, dict):
                total = {'null': total}
            return dict((k, (v, count)) for k, v in total.iteritems()) if count else {}
        def get_dataview(ds_name, ds_desc, dv_name, dv_desc):
            if ds_name in obj:
                ds_data = obj[ds_name]
                if dv_name in ds_data:
                    dv_data = ds_data[dv_name]
                    if dv_data['bin_width'] == dv_desc.bin_width and len(dv_data['bins']) == dv_desc.bin_count:
                        return DataView(dv_desc, ds_desc, dv_data['last_bin_end'], map(convert_bin, dv_data['bins']))
            elif ds_desc.default_func is None:
                return DataView(dv_desc, ds_desc, 0, dv_desc.bin_count*[{}])
            else:
                return ds_desc.default_func(ds_name, ds_desc, dv_name, dv_desc, obj)
        return cls(dict(
            (ds_name, DataStream(ds_desc, dict(
                (dv_name, get_dataview(ds_name, ds_desc, dv_name, dv_desc))
                for dv_name, dv_desc in ds_desc.dataview_descriptions.iteritems()
            )))
            for ds_name, ds_desc in datastream_descriptions.iteritems()
        ))
    
    def __init__(self, datastreams):
        self.datastreams = datastreams
    
    def to_obj(self):
        return dict((ds_name, dict((dv_name, dict(last_bin_end=dv.last_bin_end, bin_width=dv.desc.bin_width, bins=dv.bins))
            for dv_name, dv in ds.dataviews.iteritems())) for ds_name, ds in self.datastreams.iteritems())


def make_multivalue_migrator(multivalue_keys, post_func=lambda bins: bins):
    def _(ds_name, ds_desc, dv_name, dv_desc, obj):
        if not obj:
            last_bin_end = 0
            bins = dv_desc.bin_count*[{}]
        else:
            inputs = dict((k, obj.get(v, {dv_name: dict(bins=[{}]*dv_desc.bin_count, last_bin_end=0)})[dv_name]) for k, v in multivalue_keys.iteritems())
            last_bin_end = max(inp['last_bin_end'] for inp in inputs.itervalues()) if inputs else 0
            assert all(len(inp['bins']) == dv_desc.bin_count for inp in inputs.itervalues())
            inputs = dict((k, dict(zip(['bins', 'last_bin_end'], _shift_bins_so_t_is_not_past_end(v['bins'], v['last_bin_end'], dv_desc.bin_width, last_bin_end)))) for k, v in inputs.iteritems())
            assert len(set(inp['last_bin_end'] for inp in inputs.itervalues())) <= 1
            bins = post_func([dict((k, v['bins'][i]['null']) for k, v in inputs.iteritems() if 'null' in v['bins'][i]) for i in xrange(dv_desc.bin_count)])
        return DataView(dv_desc, ds_desc, last_bin_end, bins)
    return _

########NEW FILE########
__FILENAME__ = jsonrpc
from __future__ import division

import json
import weakref

from twisted.internet import defer
from twisted.protocols import basic
from twisted.python import failure, log
from twisted.web import client, error

from p2pool.util import deferral, deferred_resource, memoize

class Error(Exception):
    def __init__(self, code, message, data=None):
        if type(self) is Error:
            raise TypeError("can't directly instantiate Error class; use Error_for_code")
        if not isinstance(code, int):
            raise TypeError('code must be an int')
        #if not isinstance(message, unicode):
        #    raise TypeError('message must be a unicode')
        self.code, self.message, self.data = code, message, data
    def __str__(self):
        return '%i %s' % (self.code, self.message) + (' %r' % (self.data, ) if self.data is not None else '')
    def _to_obj(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data,
        }

@memoize.memoize_with_backing(weakref.WeakValueDictionary())
def Error_for_code(code):
    class NarrowError(Error):
        def __init__(self, *args, **kwargs):
            Error.__init__(self, code, *args, **kwargs)
    return NarrowError


class Proxy(object):
    def __init__(self, func, services=[]):
        self._func = func
        self._services = services
    
    def __getattr__(self, attr):
        if attr.startswith('rpc_'):
            return lambda *params: self._func('.'.join(self._services + [attr[len('rpc_'):]]), params)
        elif attr.startswith('svc_'):
            return Proxy(self._func, self._services + [attr[len('svc_'):]])
        else:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, attr))

@defer.inlineCallbacks
def _handle(data, provider, preargs=(), response_handler=None):
        id_ = None
        
        try:
            try:
                try:
                    req = json.loads(data)
                except Exception:
                    raise Error_for_code(-32700)(u'Parse error')
                
                if 'result' in req or 'error' in req:
                    response_handler(req['id'], req['result'] if 'error' not in req or req['error'] is None else
                        failure.Failure(Error_for_code(req['error']['code'])(req['error']['message'], req['error'].get('data', None))))
                    defer.returnValue(None)
                
                id_ = req.get('id', None)
                method = req.get('method', None)
                if not isinstance(method, basestring):
                    raise Error_for_code(-32600)(u'Invalid Request')
                params = req.get('params', [])
                if not isinstance(params, list):
                    raise Error_for_code(-32600)(u'Invalid Request')
                
                for service_name in method.split('.')[:-1]:
                    provider = getattr(provider, 'svc_' + service_name, None)
                    if provider is None:
                        raise Error_for_code(-32601)(u'Service not found')
                
                method_meth = getattr(provider, 'rpc_' + method.split('.')[-1], None)
                if method_meth is None:
                    raise Error_for_code(-32601)(u'Method not found')
                
                result = yield method_meth(*list(preargs) + list(params))
                error = None
            except Error:
                raise
            except Exception:
                log.err(None, 'Squelched JSON error:')
                raise Error_for_code(-32099)(u'Unknown error')
        except Error, e:
            result = None
            error = e._to_obj()
        
        defer.returnValue(json.dumps(dict(
            jsonrpc='2.0',
            id=id_,
            result=result,
            error=error,
        )))

# HTTP

@defer.inlineCallbacks
def _http_do(url, headers, timeout, method, params):
    id_ = 0
    
    try:
        data = yield client.getPage(
            url=url,
            method='POST',
            headers=dict(headers, **{'Content-Type': 'application/json'}),
            postdata=json.dumps({
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': id_,
            }),
            timeout=timeout,
        )
    except error.Error, e:
        try:
            resp = json.loads(e.response)
        except:
            raise e
    else:
        resp = json.loads(data)
    
    if resp['id'] != id_:
        raise ValueError('invalid id')
    if 'error' in resp and resp['error'] is not None:
        raise Error_for_code(resp['error']['code'])(resp['error']['message'], resp['error'].get('data', None))
    defer.returnValue(resp['result'])
HTTPProxy = lambda url, headers={}, timeout=5: Proxy(lambda method, params: _http_do(url, headers, timeout, method, params))

class HTTPServer(deferred_resource.DeferredResource):
    def __init__(self, provider):
        deferred_resource.DeferredResource.__init__(self)
        self._provider = provider
    
    @defer.inlineCallbacks
    def render_POST(self, request):
        data = yield _handle(request.content.read(), self._provider, preargs=[request])
        assert data is not None
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Content-Length', len(data))
        request.write(data)

class LineBasedPeer(basic.LineOnlyReceiver):
    delimiter = '\n'
    
    def __init__(self):
        #basic.LineOnlyReceiver.__init__(self)
        self._matcher = deferral.GenericDeferrer(max_id=2**30, func=lambda id, method, params: self.sendLine(json.dumps({
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': id,
        })))
        self.other = Proxy(self._matcher)
    
    def lineReceived(self, line):
        _handle(line, self, response_handler=self._matcher.got_response).addCallback(lambda line2: self.sendLine(line2) if line2 is not None else None)

########NEW FILE########
__FILENAME__ = logging
import codecs
import datetime
import os
import sys

from twisted.python import log

class EncodeReplacerPipe(object):
    def __init__(self, inner_file):
        self.inner_file = inner_file
        self.softspace = 0
    def write(self, data):
        if isinstance(data, unicode):
            try:
                data = data.encode(self.inner_file.encoding, 'replace')
            except:
                data = data.encode('ascii', 'replace')
        self.inner_file.write(data)
    def flush(self):
        self.inner_file.flush()

class LogFile(object):
    def __init__(self, filename):
        self.filename = filename
        self.inner_file = None
        self.reopen()
    def reopen(self):
        if self.inner_file is not None:
            self.inner_file.close()
        open(self.filename, 'a').close()
        f = open(self.filename, 'rb')
        f.seek(0, os.SEEK_END)
        length = f.tell()
        if length > 100*1000*1000:
            f.seek(-1000*1000, os.SEEK_END)
            while True:
                if f.read(1) in ('', '\n'):
                    break
            data = f.read()
            f.close()
            f = open(self.filename, 'wb')
            f.write(data)
        f.close()
        self.inner_file = codecs.open(self.filename, 'a', 'utf-8')
    def write(self, data):
        self.inner_file.write(data)
    def flush(self):
        self.inner_file.flush()

class TeePipe(object):
    def __init__(self, outputs):
        self.outputs = outputs
    def write(self, data):
        for output in self.outputs:
            output.write(data)
    def flush(self):
        for output in self.outputs:
            output.flush()

class TimestampingPipe(object):
    def __init__(self, inner_file):
        self.inner_file = inner_file
        self.buf = ''
        self.softspace = 0
    def write(self, data):
        buf = self.buf + data
        lines = buf.split('\n')
        for line in lines[:-1]:
            self.inner_file.write('%s %s\n' % (datetime.datetime.now(), line))
            self.inner_file.flush()
        self.buf = lines[-1]
    def flush(self):
        pass

class AbortPipe(object):
    def __init__(self, inner_file):
        self.inner_file = inner_file
        self.softspace = 0
    def write(self, data):
        try:
            self.inner_file.write(data)
        except:
            sys.stdout = sys.__stdout__
            log.DefaultObserver.stderr = sys.stderr = sys.__stderr__
            raise
    def flush(self):
        self.inner_file.flush()

class PrefixPipe(object):
    def __init__(self, inner_file, prefix):
        self.inner_file = inner_file
        self.prefix = prefix
        self.buf = ''
        self.softspace = 0
    def write(self, data):
        buf = self.buf + data
        lines = buf.split('\n')
        for line in lines[:-1]:
            self.inner_file.write(self.prefix + line + '\n')
            self.inner_file.flush()
        self.buf = lines[-1]
    def flush(self):
        pass

########NEW FILE########
__FILENAME__ = math
from __future__ import absolute_import, division

import __builtin__
import math
import random
import time

def median(x, use_float=True):
    # there exist better algorithms...
    y = sorted(x)
    if not y:
        raise ValueError('empty sequence!')
    left = (len(y) - 1)//2
    right = len(y)//2
    sum = y[left] + y[right]
    if use_float:
        return sum/2
    else:
        return sum//2

def mean(x):
    total = 0
    count = 0
    for y in x:
        total += y
        count += 1
    return total/count

def shuffled(x):
    x = list(x)
    random.shuffle(x)
    return x

def shift_left(n, m):
    # python: :(
    if m >= 0:
        return n << m
    return n >> -m

def clip(x, (low, high)):
    if x < low:
        return low
    elif x > high:
        return high
    else:
        return x

add_to_range = lambda x, (low, high): (min(low, x), max(high, x))

def nth(i, n=0):
    i = iter(i)
    for _ in xrange(n):
        i.next()
    return i.next()

def geometric(p):
    if p <= 0 or p > 1:
        raise ValueError('p must be in the interval (0.0, 1.0]')
    if p == 1:
        return 1
    return int(math.log1p(-random.random()) / math.log1p(-p)) + 1

def add_dicts_ext(add_func=lambda a, b: a+b, zero=0):
    def add_dicts(*dicts):
        res = {}
        for d in dicts:
            for k, v in d.iteritems():
                res[k] = add_func(res.get(k, zero), v)
        return dict((k, v) for k, v in res.iteritems() if v != zero)
    return add_dicts
add_dicts = add_dicts_ext()

mult_dict = lambda c, x: dict((k, c*v) for k, v in x.iteritems())

def format(x, add_space=False):
    prefixes = 'kMGTPEZY'
    count = 0
    while x >= 100000 and count < len(prefixes) - 2:
        x = x//1000
        count += 1
    s = '' if count == 0 else prefixes[count - 1]
    if add_space and s:
        s = ' ' + s
    return '%i' % (x,) + s

def format_dt(dt):
    for value, name in [
        (365.2425*60*60*24, 'years'),
        (60*60*24, 'days'),
        (60*60, 'hours'),
        (60, 'minutes'),
        (1, 'seconds'),
    ]:
        if dt > value:
            break
    return '%.01f %s' % (dt/value, name)

perfect_round = lambda x: int(x + random.random())

def erf(x):
    # save the sign of x
    sign = 1
    if x < 0:
        sign = -1
    x = abs(x)
    
    # constants
    a1 =  0.254829592
    a2 = -0.284496736
    a3 =  1.421413741
    a4 = -1.453152027
    a5 =  1.061405429
    p  =  0.3275911
    
    # A&S formula 7.1.26
    t = 1.0/(1.0 + p*x)
    y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t*math.exp(-x*x)
    return sign*y # erf(-x) = -erf(x)

def find_root(y_over_dy, start, steps=10, bounds=(None, None)):
    guess = start
    for i in xrange(steps):
        prev, guess = guess, guess - y_over_dy(guess)
        if bounds[0] is not None and guess < bounds[0]: guess = bounds[0]
        if bounds[1] is not None and guess > bounds[1]: guess = bounds[1]
        if guess == prev:
            break
    return guess

def ierf(z):
    return find_root(lambda x: (erf(x) - z)/(2*math.e**(-x**2)/math.sqrt(math.pi)), 0)

def binomial_conf_interval(x, n, conf=0.95):
    assert 0 <= x <= n and 0 <= conf < 1
    if n == 0:
        left = random.random()*(1 - conf)
        return left, left + conf
    # approximate - Wilson score interval
    z = math.sqrt(2)*ierf(conf)
    p = x/n
    topa = p + z**2/2/n
    topb = z * math.sqrt(p*(1-p)/n + z**2/4/n**2)
    bottom = 1 + z**2/n
    return [clip(x, (0, 1)) for x in add_to_range(x/n, [(topa - topb)/bottom, (topa + topb)/bottom])]

minmax = lambda x: (min(x), max(x))

def format_binomial_conf(x, n, conf=0.95, f=lambda x: x):
    if n == 0:
        return '???'
    left, right = minmax(map(f, binomial_conf_interval(x, n, conf)))
    return '~%.1f%% (%.f-%.f%%)' % (100*f(x/n), math.floor(100*left), math.ceil(100*right))

def reversed(x):
    try:
        return __builtin__.reversed(x)
    except TypeError:
        return reversed(list(x))

class Object(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

def add_tuples(res, *tuples):
    for t in tuples:
        if len(t) != len(res):
            raise ValueError('tuples must all be the same length')
        res = tuple(a + b for a, b in zip(res, t))
    return res

def flatten_linked_list(x):
    while x is not None:
        x, cur = x
        yield cur

def weighted_choice(choices):
    choices = list((item, weight) for item, weight in choices)
    target = random.randrange(sum(weight for item, weight in choices))
    for item, weight in choices:
        if weight > target:
            return item
        target -= weight
    raise AssertionError()

def natural_to_string(n, alphabet=None):
    if n < 0:
        raise TypeError('n must be a natural')
    if alphabet is None:
        s = ('%x' % (n,)).lstrip('0')
        if len(s) % 2:
            s = '0' + s
        return s.decode('hex')
    else:
        assert len(set(alphabet)) == len(alphabet)
        res = []
        while n:
            n, x = divmod(n, len(alphabet))
            res.append(alphabet[x])
        res.reverse()
        return ''.join(res)

def string_to_natural(s, alphabet=None):
    if alphabet is None:
        assert not s.startswith('\x00')
        return int(s.encode('hex'), 16) if s else 0
    else:
        assert len(set(alphabet)) == len(alphabet)
        assert not s.startswith(alphabet[0])
        return sum(alphabet.index(char) * len(alphabet)**i for i, char in enumerate(reversed(s)))

class RateMonitor(object):
    def __init__(self, max_lookback_time):
        self.max_lookback_time = max_lookback_time
        
        self.datums = []
        self.first_timestamp = None
    
    def _prune(self):
        start_time = time.time() - self.max_lookback_time
        for i, (ts, datum) in enumerate(self.datums):
            if ts > start_time:
                self.datums[:] = self.datums[i:]
                return
    
    def get_datums_in_last(self, dt=None):
        if dt is None:
            dt = self.max_lookback_time
        assert dt <= self.max_lookback_time
        self._prune()
        now = time.time()
        return [datum for ts, datum in self.datums if ts > now - dt], min(dt, now - self.first_timestamp) if self.first_timestamp is not None else 0
    
    def add_datum(self, datum):
        self._prune()
        t = time.time()
        if self.first_timestamp is None:
            self.first_timestamp = t
        else:
            self.datums.append((t, datum))

def merge_dicts(*dicts):
    res = {}
    for d in dicts: res.update(d)
    return res

########NEW FILE########
__FILENAME__ = memoize
import itertools

class LRUDict(object):
    def __init__(self, n):
        self.n = n
        self.inner = {}
        self.counter = itertools.count()
    def get(self, key, default=None):
        if key in self.inner:
            x, value = self.inner[key]
            self.inner[key] = self.counter.next(), value
            return value
        return default
    def __setitem__(self, key, value):
        self.inner[key] = self.counter.next(), value
        while len(self.inner) > self.n:
            self.inner.pop(min(self.inner, key=lambda k: self.inner[k][0]))

_nothing = object()

def memoize_with_backing(backing, has_inverses=set()):
    def a(f):
        def b(*args):
            res = backing.get((f, args), _nothing)
            if res is not _nothing:
                return res
            
            res = f(*args)
            
            backing[(f, args)] = res
            for inverse in has_inverses:
                backing[(inverse, args[:-1] + (res,))] = args[-1]
            
            return res
        return b
    return a

def memoize(f):
    return memoize_with_backing({})(f)


class cdict(dict):
    def __init__(self, func):
        dict.__init__(self)
        self._func = func
    
    def __missing__(self, key):
        value = self._func(key)
        self[key] = value
        return value

def fast_memoize_single_arg(func):
    return cdict(func).__getitem__

class cdict2(dict):
    def __init__(self, func):
        dict.__init__(self)
        self._func = func
    
    def __missing__(self, key):
        value = self._func(*key)
        self[key] = value
        return value

def fast_memoize_multiple_args(func):
    f = cdict2(func).__getitem__
    return lambda *args: f(args)

########NEW FILE########
__FILENAME__ = memory
import os
import platform

_scale = {'kB': 1024, 'mB': 1024*1024,
    'KB': 1024, 'MB': 1024*1024}

def resident():
    if platform.system() == 'Windows':
        from wmi import WMI
        w = WMI('.')
        result = w.query("SELECT WorkingSet FROM Win32_PerfRawData_PerfProc_Process WHERE IDProcess=%d" % os.getpid())
        return int(result[0].WorkingSet)
    else:
        with open('/proc/%d/status' % os.getpid()) as f:
            v = f.read()
        i = v.index('VmRSS:')
        v = v[i:].split(None, 3)
        #assert len(v) == 3, v
        return float(v[1]) * _scale[v[2]]

########NEW FILE########
__FILENAME__ = p2protocol
'''
Generic message-based protocol used by Bitcoin and P2Pool for P2P communication
'''

import hashlib
import struct

from twisted.internet import protocol
from twisted.python import log

import p2pool
from p2pool.util import datachunker, variable

class TooLong(Exception):
    pass

class Protocol(protocol.Protocol):
    def __init__(self, message_prefix, max_payload_length, traffic_happened=variable.Event(), ignore_trailing_payload=False):
        self._message_prefix = message_prefix
        self._max_payload_length = max_payload_length
        self.dataReceived2 = datachunker.DataChunker(self.dataReceiver())
        self.traffic_happened = traffic_happened
        self.ignore_trailing_payload = ignore_trailing_payload
    
    def dataReceived(self, data):
        self.traffic_happened.happened('p2p/in', len(data))
        self.dataReceived2(data)
    
    def dataReceiver(self):
        while True:
            start = ''
            while start != self._message_prefix:
                start = (start + (yield 1))[-len(self._message_prefix):]
            
            command = (yield 12).rstrip('\0')
            length, = struct.unpack('<I', (yield 4))
            if length > self._max_payload_length:
                print 'length too large'
                continue
            checksum = yield 4
            payload = yield length
            
            if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
                print 'invalid hash for', self.transport.getPeer().host, repr(command), length, checksum.encode('hex')
                if p2pool.DEBUG:
                    print hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4].encode('hex'), payload.encode('hex')
                self.badPeerHappened()
                continue
            
            type_ = getattr(self, 'message_' + command, None)
            if type_ is None:
                if p2pool.DEBUG:
                    print 'no type for', repr(command)
                continue
            
            try:
                self.packetReceived(command, type_.unpack(payload, self.ignore_trailing_payload))
            except:
                print 'RECV', command, payload[:100].encode('hex') + ('...' if len(payload) > 100 else '')
                log.err(None, 'Error handling message: (see RECV line)')
                self.disconnect()
    
    def packetReceived(self, command, payload2):
        handler = getattr(self, 'handle_' + command, None)
        if handler is None:
            if p2pool.DEBUG:
                print 'no handler for', repr(command)
            return
        
        if getattr(self, 'connected', True) and not getattr(self, 'disconnecting', False):
            handler(**payload2)
    
    def disconnect(self):
        if hasattr(self.transport, 'abortConnection'):
            # Available since Twisted 11.1
            self.transport.abortConnection()
        else:
            # This doesn't always close timed out connections! warned about in main
            self.transport.loseConnection()
    
    def badPeerHappened(self):
        self.disconnect()
    
    def sendPacket(self, command, payload2):
        if len(command) >= 12:
            raise ValueError('command too long')
        type_ = getattr(self, 'message_' + command, None)
        if type_ is None:
            raise ValueError('invalid command')
        #print 'SEND', command, repr(payload2)[:500]
        payload = type_.pack(payload2)
        if len(payload) > self._max_payload_length:
            raise TooLong('payload too long')
        data = self._message_prefix + struct.pack('<12sI', command, len(payload)) + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] + payload
        self.traffic_happened.happened('p2p/out', len(data))
        self.transport.write(data)
    
    def __getattr__(self, attr):
        prefix = 'send_'
        if attr.startswith(prefix):
            command = attr[len(prefix):]
            return lambda **payload2: self.sendPacket(command, payload2)
        #return protocol.Protocol.__getattr__(self, attr)
        raise AttributeError(attr)

########NEW FILE########
__FILENAME__ = pack
import binascii
import struct

import p2pool
from p2pool.util import memoize

class EarlyEnd(Exception):
    pass

class LateEnd(Exception):
    pass

def read((data, pos), length):
    data2 = data[pos:pos + length]
    if len(data2) != length:
        raise EarlyEnd()
    return data2, (data, pos + length)

def size((data, pos)):
    return len(data) - pos

class Type(object):
    __slots__ = []
    
    def __hash__(self):
        rval = getattr(self, '_hash', None)
        if rval is None:
            try:
                rval = self._hash = hash((type(self), frozenset(self.__dict__.items())))
            except:
                print self.__dict__
                raise
        return rval
    
    def __eq__(self, other):
        return type(other) is type(self) and other.__dict__ == self.__dict__
    
    def __ne__(self, other):
        return not (self == other)
    
    def _unpack(self, data, ignore_trailing=False):
        obj, (data2, pos) = self.read((data, 0))
        
        assert data2 is data
        
        if pos != len(data) and not ignore_trailing:
            raise LateEnd()
        
        return obj
    
    def _pack(self, obj):
        f = self.write(None, obj)
        
        res = []
        while f is not None:
            res.append(f[1])
            f = f[0]
        res.reverse()
        return ''.join(res)
    
    
    def unpack(self, data, ignore_trailing=False):
        obj = self._unpack(data, ignore_trailing)
        
        if p2pool.DEBUG:
            packed = self._pack(obj)
            good = data.startswith(packed) if ignore_trailing else data == packed
            if not good:
                raise AssertionError()
        
        return obj
    
    def pack(self, obj):
        data = self._pack(obj)
        
        if p2pool.DEBUG:
            if self._unpack(data) != obj:
                raise AssertionError((self._unpack(data), obj))
        
        return data
    
    def packed_size(self, obj):
        if hasattr(obj, '_packed_size') and obj._packed_size is not None:
            type_obj, packed_size = obj._packed_size
            if type_obj is self:
                return packed_size
        
        packed_size = len(self.pack(obj))
        
        if hasattr(obj, '_packed_size'):
            obj._packed_size = self, packed_size
        
        return packed_size

class VarIntType(Type):
    def read(self, file):
        data, file = read(file, 1)
        first = ord(data)
        if first < 0xfd:
            return first, file
        if first == 0xfd:
            desc, length, minimum = '<H', 2, 0xfd
        elif first == 0xfe:
            desc, length, minimum = '<I', 4, 2**16
        elif first == 0xff:
            desc, length, minimum = '<Q', 8, 2**32
        else:
            raise AssertionError()
        data2, file = read(file, length)
        res, = struct.unpack(desc, data2)
        if res < minimum:
            raise AssertionError('VarInt not canonically packed')
        return res, file
    
    def write(self, file, item):
        if item < 0xfd:
            return file, struct.pack('<B', item)
        elif item <= 0xffff:
            return file, struct.pack('<BH', 0xfd, item)
        elif item <= 0xffffffff:
            return file, struct.pack('<BI', 0xfe, item)
        elif item <= 0xffffffffffffffff:
            return file, struct.pack('<BQ', 0xff, item)
        else:
            raise ValueError('int too large for varint')

class VarStrType(Type):
    _inner_size = VarIntType()
    
    def read(self, file):
        length, file = self._inner_size.read(file)
        return read(file, length)
    
    def write(self, file, item):
        return self._inner_size.write(file, len(item)), item

class EnumType(Type):
    def __init__(self, inner, pack_to_unpack):
        self.inner = inner
        self.pack_to_unpack = pack_to_unpack
        
        self.unpack_to_pack = {}
        for k, v in pack_to_unpack.iteritems():
            if v in self.unpack_to_pack:
                raise ValueError('duplicate value in pack_to_unpack')
            self.unpack_to_pack[v] = k
    
    def read(self, file):
        data, file = self.inner.read(file)
        if data not in self.pack_to_unpack:
            raise ValueError('enum data (%r) not in pack_to_unpack (%r)' % (data, self.pack_to_unpack))
        return self.pack_to_unpack[data], file
    
    def write(self, file, item):
        if item not in self.unpack_to_pack:
            raise ValueError('enum item (%r) not in unpack_to_pack (%r)' % (item, self.unpack_to_pack))
        return self.inner.write(file, self.unpack_to_pack[item])

class ListType(Type):
    _inner_size = VarIntType()
    
    def __init__(self, type, mul=1):
        self.type = type
        self.mul = mul
    
    def read(self, file):
        length, file = self._inner_size.read(file)
        length *= self.mul
        res = [None]*length
        for i in xrange(length):
            res[i], file = self.type.read(file)
        return res, file
    
    def write(self, file, item):
        assert len(item) % self.mul == 0
        file = self._inner_size.write(file, len(item)//self.mul)
        for subitem in item:
            file = self.type.write(file, subitem)
        return file

class StructType(Type):
    __slots__ = 'desc length'.split(' ')
    
    def __init__(self, desc):
        self.desc = desc
        self.length = struct.calcsize(self.desc)
    
    def read(self, file):
        data, file = read(file, self.length)
        return struct.unpack(self.desc, data)[0], file
    
    def write(self, file, item):
        return file, struct.pack(self.desc, item)

@memoize.fast_memoize_multiple_args
class IntType(Type):
    __slots__ = 'bytes step format_str max'.split(' ')
    
    def __new__(cls, bits, endianness='little'):
        assert bits % 8 == 0
        assert endianness in ['little', 'big']
        if bits in [8, 16, 32, 64]:
            return StructType(('<' if endianness == 'little' else '>') + {8: 'B', 16: 'H', 32: 'I', 64: 'Q'}[bits])
        else:
            return Type.__new__(cls, bits, endianness)
    
    def __init__(self, bits, endianness='little'):
        assert bits % 8 == 0
        assert endianness in ['little', 'big']
        self.bytes = bits//8
        self.step = -1 if endianness == 'little' else 1
        self.format_str = '%%0%ix' % (2*self.bytes)
        self.max = 2**bits
    
    def read(self, file, b2a_hex=binascii.b2a_hex):
        if self.bytes == 0:
            return 0, file
        data, file = read(file, self.bytes)
        return int(b2a_hex(data[::self.step]), 16), file
    
    def write(self, file, item, a2b_hex=binascii.a2b_hex):
        if self.bytes == 0:
            return file
        if not 0 <= item < self.max:
            raise ValueError('invalid int value - %r' % (item,))
        return file, a2b_hex(self.format_str % (item,))[::self.step]

class IPV6AddressType(Type):
    def read(self, file):
        data, file = read(file, 16)
        if data[:12] == '00000000000000000000ffff'.decode('hex'):
            return '.'.join(str(ord(x)) for x in data[12:]), file
        return ':'.join(data[i*2:(i+1)*2].encode('hex') for i in xrange(8)), file
    
    def write(self, file, item):
        if ':' in item:
            data = ''.join(item.replace(':', '')).decode('hex')
        else:
            bits = map(int, item.split('.'))
            if len(bits) != 4:
                raise ValueError('invalid address: %r' % (bits,))
            data = '00000000000000000000ffff'.decode('hex') + ''.join(chr(x) for x in bits)
        assert len(data) == 16, len(data)
        return file, data

_record_types = {}

def get_record(fields):
    fields = tuple(sorted(fields))
    if 'keys' in fields or '_packed_size' in fields:
        raise ValueError()
    if fields not in _record_types:
        class _Record(object):
            __slots__ = fields + ('_packed_size',)
            def __init__(self):
                self._packed_size = None
            def __repr__(self):
                return repr(dict(self))
            def __getitem__(self, key):
                return getattr(self, key)
            def __setitem__(self, key, value):
                setattr(self, key, value)
            #def __iter__(self):
            #    for field in fields:
            #        yield field, getattr(self, field)
            def keys(self):
                return fields
            def get(self, key, default=None):
                return getattr(self, key, default)
            def __eq__(self, other):
                if isinstance(other, dict):
                    return dict(self) == other
                elif isinstance(other, _Record):
                    for k in fields:
                        if getattr(self, k) != getattr(other, k):
                            return False
                    return True
                elif other is None:
                    return False
                raise TypeError()
            def __ne__(self, other):
                return not (self == other)
        _record_types[fields] = _Record
    return _record_types[fields]

class ComposedType(Type):
    def __init__(self, fields):
        self.fields = list(fields)
        self.field_names = set(k for k, v in fields)
        self.record_type = get_record(k for k, v in self.fields)
    
    def read(self, file):
        item = self.record_type()
        for key, type_ in self.fields:
            item[key], file = type_.read(file)
        return item, file
    
    def write(self, file, item):
        assert set(item.keys()) == self.field_names, (set(item.keys()) - self.field_names, self.field_names - set(item.keys()))
        for key, type_ in self.fields:
            file = type_.write(file, item[key])
        return file

class PossiblyNoneType(Type):
    def __init__(self, none_value, inner):
        self.none_value = none_value
        self.inner = inner
    
    def read(self, file):
        value, file = self.inner.read(file)
        return None if value == self.none_value else value, file
    
    def write(self, file, item):
        if item == self.none_value:
            raise ValueError('none_value used')
        return self.inner.write(file, self.none_value if item is None else item)

class FixedStrType(Type):
    def __init__(self, length):
        self.length = length
    
    def read(self, file):
        return read(file, self.length)
    
    def write(self, file, item):
        if len(item) != self.length:
            raise ValueError('incorrect length item!')
        return file, item

########NEW FILE########
__FILENAME__ = skiplist
from p2pool.util import math, memoize

class SkipList(object):
    def __init__(self, p=0.5):
        self.p = p
        
        self.skips = {}
    
    def forget_item(self, item):
        self.skips.pop(item, None)
    
    @memoize.memoize_with_backing(memoize.LRUDict(5))
    def __call__(self, start, *args):
        updates = {}
        pos = start
        sol = self.initial_solution(start, args)
        if self.judge(sol, args) == 0:
            return self.finalize(sol, args)
        while True:
            if pos not in self.skips:
                self.skips[pos] = math.geometric(self.p), [(self.previous(pos), self.get_delta(pos))]
            skip_length, skip = self.skips[pos]
            
            # fill previous updates
            for i in xrange(skip_length):
                if i in updates:
                    that_hash, delta = updates.pop(i)
                    x, y = self.skips[that_hash]
                    assert len(y) == i
                    y.append((pos, delta))
            
            # put desired skip nodes in updates
            for i in xrange(len(skip), skip_length):
                updates[i] = pos, None
            
            #if skip_length + 1 in updates:
            #    updates[skip_length + 1] = self.combine(updates[skip_length + 1], updates[skip_length])
            
            for jump, delta in reversed(skip):
                sol_if = self.apply_delta(sol, delta, args)
                decision = self.judge(sol_if, args)
                #print pos, sol, jump, delta, sol_if, decision
                if decision == 0:
                    return self.finalize(sol_if, args)
                elif decision < 0:
                    sol = sol_if
                    break
            else:
                raise AssertionError()
            
            sol = sol_if
            pos = jump
            
            # XXX could be better by combining updates
            for x in updates:
                updates[x] = updates[x][0], self.combine_deltas(updates[x][1], delta) if updates[x][1] is not None else delta
    
    def finalize(self, sol, args):
        return sol

########NEW FILE########
__FILENAME__ = switchprotocol
from twisted.internet import protocol

class FirstByteSwitchProtocol(protocol.Protocol):
    p = None
    def dataReceived(self, data):
        if self.p is None:
            if not data: return
            serverfactory = self.factory.first_byte_to_serverfactory.get(data[0], self.factory.default_serverfactory)
            self.p = serverfactory.buildProtocol(self.transport.getPeer())
            self.p.makeConnection(self.transport)
        self.p.dataReceived(data)
    def connectionLost(self, reason):
        if self.p is not None:
            self.p.connectionLost(reason)

class FirstByteSwitchFactory(protocol.ServerFactory):
    protocol = FirstByteSwitchProtocol
    
    def __init__(self, first_byte_to_serverfactory, default_serverfactory):
        self.first_byte_to_serverfactory = first_byte_to_serverfactory
        self.default_serverfactory = default_serverfactory
    
    def startFactory(self):
        for f in list(self.first_byte_to_serverfactory.values()) + [self.default_serverfactory]:
            f.doStart()
    
    def stopFactory(self):
        for f in list(self.first_byte_to_serverfactory.values()) + [self.default_serverfactory]:
            f.doStop()

########NEW FILE########
__FILENAME__ = variable
import itertools
import weakref

from twisted.internet import defer, reactor
from twisted.python import failure, log

class Event(object):
    def __init__(self):
        self.observers = {}
        self.id_generator = itertools.count()
        self._once = None
        self.times = 0
    
    def run_and_watch(self, func):
        func()
        return self.watch(func)
    def watch_weakref(self, obj, func):
        # func must not contain a reference to obj!
        watch_id = self.watch(lambda *args: func(obj_ref(), *args))
        obj_ref = weakref.ref(obj, lambda _: self.unwatch(watch_id))
    def watch(self, func):
        id = self.id_generator.next()
        self.observers[id] = func
        return id
    def unwatch(self, id):
        self.observers.pop(id)
    
    @property
    def once(self):
        res = self._once
        if res is None:
            res = self._once = Event()
        return res
    
    def happened(self, *event):
        self.times += 1
        
        once, self._once = self._once, None
        
        for id, func in sorted(self.observers.iteritems()):
            try:
                func(*event)
            except:
                log.err(None, "Error while processing Event callbacks:")
        
        if once is not None:
            once.happened(*event)
    
    def get_deferred(self, timeout=None):
        once = self.once
        df = defer.Deferred()
        id1 = once.watch(lambda *event: df.callback(event))
        if timeout is not None:
            def do_timeout():
                df.errback(failure.Failure(defer.TimeoutError('in Event.get_deferred')))
                once.unwatch(id1)
                once.unwatch(x)
            delay = reactor.callLater(timeout, do_timeout)
            x = once.watch(lambda *event: delay.cancel())
        return df

class Variable(object):
    def __init__(self, value):
        self.value = value
        self.changed = Event()
        self.transitioned = Event()
    
    def set(self, value):
        if value == self.value:
            return
        
        oldvalue = self.value
        self.value = value
        self.changed.happened(value)
        self.transitioned.happened(oldvalue, value)
    
    @defer.inlineCallbacks
    def get_when_satisfies(self, func):
        while True:
            if func(self.value):
                defer.returnValue(self.value)
            yield self.changed.once.get_deferred()
    
    def get_not_none(self):
        return self.get_when_satisfies(lambda val: val is not None)

########NEW FILE########
__FILENAME__ = web
from __future__ import division

import errno
import json
import os
import sys
import time
import traceback

from twisted.internet import defer, reactor
from twisted.python import log
from twisted.web import resource, static

import p2pool
from bitcoin import data as bitcoin_data
from . import data as p2pool_data, p2p
from util import deferral, deferred_resource, graph, math, memory, pack, variable

def _atomic_read(filename):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
    try:
        with open(filename + '.new', 'rb') as f:
            return f.read()
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
    return None

def _atomic_write(filename, data):
    with open(filename + '.new', 'wb') as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except:
            pass
    try:
        os.rename(filename + '.new', filename)
    except: # XXX windows can't overwrite
        os.remove(filename)
        os.rename(filename + '.new', filename)

def get_web_root(wb, datadir_path, bitcoind_getinfo_var, stop_event=variable.Event()):
    node = wb.node
    start_time = time.time()
    
    web_root = resource.Resource()
    
    def get_users():
        height, last = node.tracker.get_height_and_last(node.best_share_var.value)
        weights, total_weight, donation_weight = node.tracker.get_cumulative_weights(node.best_share_var.value, min(height, 720), 65535*2**256)
        res = {}
        for script in sorted(weights, key=lambda s: weights[s]):
            res[bitcoin_data.script2_to_address(script, node.net.PARENT)] = weights[script]/total_weight
        return res
    
    def get_current_scaled_txouts(scale, trunc=0):
        txouts = node.get_current_txouts()
        total = sum(txouts.itervalues())
        results = dict((script, value*scale//total) for script, value in txouts.iteritems())
        if trunc > 0:
            total_random = 0
            random_set = set()
            for s in sorted(results, key=results.__getitem__):
                if results[s] >= trunc:
                    break
                total_random += results[s]
                random_set.add(s)
            if total_random:
                winner = math.weighted_choice((script, results[script]) for script in random_set)
                for script in random_set:
                    del results[script]
                results[winner] = total_random
        if sum(results.itervalues()) < int(scale):
            results[math.weighted_choice(results.iteritems())] += int(scale) - sum(results.itervalues())
        return results
    
    def get_patron_sendmany(total=None, trunc='0.01'):
        if total is None:
            return 'need total argument. go to patron_sendmany/<TOTAL>'
        total = int(float(total)*1e8)
        trunc = int(float(trunc)*1e8)
        return json.dumps(dict(
            (bitcoin_data.script2_to_address(script, node.net.PARENT), value/1e8)
            for script, value in get_current_scaled_txouts(total, trunc).iteritems()
            if bitcoin_data.script2_to_address(script, node.net.PARENT) is not None
        ))
    
    def get_global_stats():
        # averaged over last hour
        if node.tracker.get_height(node.best_share_var.value) < 10:
            return None
        lookbehind = min(node.tracker.get_height(node.best_share_var.value), 3600//node.net.SHARE_PERIOD)
        
        nonstale_hash_rate = p2pool_data.get_pool_attempts_per_second(node.tracker, node.best_share_var.value, lookbehind)
        stale_prop = p2pool_data.get_average_stale_prop(node.tracker, node.best_share_var.value, lookbehind)
        return dict(
            pool_nonstale_hash_rate=nonstale_hash_rate,
            pool_hash_rate=nonstale_hash_rate/(1 - stale_prop),
            pool_stale_prop=stale_prop,
            min_difficulty=bitcoin_data.target_to_difficulty(node.tracker.items[node.best_share_var.value].max_target),
        )
    
    def get_local_stats():
        if node.tracker.get_height(node.best_share_var.value) < 10:
            return None
        lookbehind = min(node.tracker.get_height(node.best_share_var.value), 3600//node.net.SHARE_PERIOD)
        
        global_stale_prop = p2pool_data.get_average_stale_prop(node.tracker, node.best_share_var.value, lookbehind)
        
        my_unstale_count = sum(1 for share in node.tracker.get_chain(node.best_share_var.value, lookbehind) if share.hash in wb.my_share_hashes)
        my_orphan_count = sum(1 for share in node.tracker.get_chain(node.best_share_var.value, lookbehind) if share.hash in wb.my_share_hashes and share.share_data['stale_info'] == 'orphan')
        my_doa_count = sum(1 for share in node.tracker.get_chain(node.best_share_var.value, lookbehind) if share.hash in wb.my_share_hashes and share.share_data['stale_info'] == 'doa')
        my_share_count = my_unstale_count + my_orphan_count + my_doa_count
        my_stale_count = my_orphan_count + my_doa_count
        
        my_stale_prop = my_stale_count/my_share_count if my_share_count != 0 else None
        
        my_work = sum(bitcoin_data.target_to_average_attempts(share.target)
            for share in node.tracker.get_chain(node.best_share_var.value, lookbehind - 1)
            if share.hash in wb.my_share_hashes)
        actual_time = (node.tracker.items[node.best_share_var.value].timestamp -
            node.tracker.items[node.tracker.get_nth_parent_hash(node.best_share_var.value, lookbehind - 1)].timestamp)
        share_att_s = my_work / actual_time
        
        miner_hash_rates, miner_dead_hash_rates = wb.get_local_rates()
        (stale_orphan_shares, stale_doa_shares), shares, _ = wb.get_stale_counts()
        
        return dict(
            my_hash_rates_in_last_hour=dict(
                note="DEPRECATED",
                nonstale=share_att_s,
                rewarded=share_att_s/(1 - global_stale_prop),
                actual=share_att_s/(1 - my_stale_prop) if my_stale_prop is not None else 0, # 0 because we don't have any shares anyway
            ),
            my_share_counts_in_last_hour=dict(
                shares=my_share_count,
                unstale_shares=my_unstale_count,
                stale_shares=my_stale_count,
                orphan_stale_shares=my_orphan_count,
                doa_stale_shares=my_doa_count,
            ),
            my_stale_proportions_in_last_hour=dict(
                stale=my_stale_prop,
                orphan_stale=my_orphan_count/my_share_count if my_share_count != 0 else None,
                dead_stale=my_doa_count/my_share_count if my_share_count != 0 else None,
            ),
            miner_hash_rates=miner_hash_rates,
            miner_dead_hash_rates=miner_dead_hash_rates,
            efficiency_if_miner_perfect=(1 - stale_orphan_shares/shares)/(1 - global_stale_prop) if shares else None, # ignores dead shares because those are miner's fault and indicated by pseudoshare rejection
            efficiency=(1 - (stale_orphan_shares+stale_doa_shares)/shares)/(1 - global_stale_prop) if shares else None,
            peers=dict(
                incoming=sum(1 for peer in node.p2p_node.peers.itervalues() if peer.incoming),
                outgoing=sum(1 for peer in node.p2p_node.peers.itervalues() if not peer.incoming),
            ),
            shares=dict(
                total=shares,
                orphan=stale_orphan_shares,
                dead=stale_doa_shares,
            ),
            uptime=time.time() - start_time,
            attempts_to_share=bitcoin_data.target_to_average_attempts(node.tracker.items[node.best_share_var.value].max_target),
            attempts_to_block=bitcoin_data.target_to_average_attempts(node.bitcoind_work.value['bits'].target),
            block_value=node.bitcoind_work.value['subsidy']*1e-8,
            warnings=p2pool_data.get_warnings(node.tracker, node.best_share_var.value, node.net, bitcoind_getinfo_var.value, node.bitcoind_work.value),
            donation_proportion=wb.donation_percentage/100,
            version=p2pool.__version__,
            protocol_version=p2p.Protocol.VERSION,
            fee=wb.worker_fee,
        )
    
    class WebInterface(deferred_resource.DeferredResource):
        def __init__(self, func, mime_type='application/json', args=()):
            deferred_resource.DeferredResource.__init__(self)
            self.func, self.mime_type, self.args = func, mime_type, args
        
        def getChild(self, child, request):
            return WebInterface(self.func, self.mime_type, self.args + (child,))
        
        @defer.inlineCallbacks
        def render_GET(self, request):
            request.setHeader('Content-Type', self.mime_type)
            request.setHeader('Access-Control-Allow-Origin', '*')
            res = yield self.func(*self.args)
            defer.returnValue(json.dumps(res) if self.mime_type == 'application/json' else res)
    
    def decent_height():
        return min(node.tracker.get_height(node.best_share_var.value), 720)
    web_root.putChild('rate', WebInterface(lambda: p2pool_data.get_pool_attempts_per_second(node.tracker, node.best_share_var.value, decent_height())/(1-p2pool_data.get_average_stale_prop(node.tracker, node.best_share_var.value, decent_height()))))
    web_root.putChild('difficulty', WebInterface(lambda: bitcoin_data.target_to_difficulty(node.tracker.items[node.best_share_var.value].max_target)))
    web_root.putChild('users', WebInterface(get_users))
    web_root.putChild('user_stales', WebInterface(lambda: dict((bitcoin_data.pubkey_hash_to_address(ph, node.net.PARENT), prop) for ph, prop in
        p2pool_data.get_user_stale_props(node.tracker, node.best_share_var.value, node.tracker.get_height(node.best_share_var.value)).iteritems())))
    web_root.putChild('fee', WebInterface(lambda: wb.worker_fee))
    web_root.putChild('current_payouts', WebInterface(lambda: dict((bitcoin_data.script2_to_address(script, node.net.PARENT), value/1e8) for script, value in node.get_current_txouts().iteritems())))
    web_root.putChild('patron_sendmany', WebInterface(get_patron_sendmany, 'text/plain'))
    web_root.putChild('global_stats', WebInterface(get_global_stats))
    web_root.putChild('local_stats', WebInterface(get_local_stats))
    web_root.putChild('peer_addresses', WebInterface(lambda: ' '.join('%s%s' % (peer.transport.getPeer().host, ':'+str(peer.transport.getPeer().port) if peer.transport.getPeer().port != node.net.P2P_PORT else '') for peer in node.p2p_node.peers.itervalues())))
    web_root.putChild('peer_txpool_sizes', WebInterface(lambda: dict(('%s:%i' % (peer.transport.getPeer().host, peer.transport.getPeer().port), peer.remembered_txs_size) for peer in node.p2p_node.peers.itervalues())))
    web_root.putChild('pings', WebInterface(defer.inlineCallbacks(lambda: defer.returnValue(
        dict([(a, (yield b)) for a, b in
            [(
                '%s:%i' % (peer.transport.getPeer().host, peer.transport.getPeer().port),
                defer.inlineCallbacks(lambda peer=peer: defer.returnValue(
                    min([(yield peer.do_ping().addCallback(lambda x: x/0.001).addErrback(lambda fail: None)) for i in xrange(3)])
                ))()
            ) for peer in list(node.p2p_node.peers.itervalues())]
        ])
    ))))
    web_root.putChild('peer_versions', WebInterface(lambda: dict(('%s:%i' % peer.addr, peer.other_sub_version) for peer in node.p2p_node.peers.itervalues())))
    web_root.putChild('payout_addr', WebInterface(lambda: bitcoin_data.pubkey_hash_to_address(wb.my_pubkey_hash, node.net.PARENT)))
    web_root.putChild('recent_blocks', WebInterface(lambda: [dict(
        ts=s.timestamp,
        hash='%064x' % s.header_hash,
        number=pack.IntType(24).unpack(s.share_data['coinbase'][1:4]) if len(s.share_data['coinbase']) >= 4 else None,
        share='%064x' % s.hash,
    ) for s in node.tracker.get_chain(node.best_share_var.value, min(node.tracker.get_height(node.best_share_var.value), 24*60*60//node.net.SHARE_PERIOD)) if s.pow_hash <= s.header['bits'].target]))
    web_root.putChild('uptime', WebInterface(lambda: time.time() - start_time))
    web_root.putChild('stale_rates', WebInterface(lambda: p2pool_data.get_stale_counts(node.tracker, node.best_share_var.value, decent_height(), rates=True)))
    
    new_root = resource.Resource()
    web_root.putChild('web', new_root)
    
    stat_log = []
    if os.path.exists(os.path.join(datadir_path, 'stats')):
        try:
            with open(os.path.join(datadir_path, 'stats'), 'rb') as f:
                stat_log = json.loads(f.read())
        except:
            log.err(None, 'Error loading stats:')
    def update_stat_log():
        while stat_log and stat_log[0]['time'] < time.time() - 24*60*60:
            stat_log.pop(0)
        
        lookbehind = 3600//node.net.SHARE_PERIOD
        if node.tracker.get_height(node.best_share_var.value) < lookbehind:
            return None
        
        global_stale_prop = p2pool_data.get_average_stale_prop(node.tracker, node.best_share_var.value, lookbehind)
        (stale_orphan_shares, stale_doa_shares), shares, _ = wb.get_stale_counts()
        miner_hash_rates, miner_dead_hash_rates = wb.get_local_rates()
        
        stat_log.append(dict(
            time=time.time(),
            pool_hash_rate=p2pool_data.get_pool_attempts_per_second(node.tracker, node.best_share_var.value, lookbehind)/(1-global_stale_prop),
            pool_stale_prop=global_stale_prop,
            local_hash_rates=miner_hash_rates,
            local_dead_hash_rates=miner_dead_hash_rates,
            shares=shares,
            stale_shares=stale_orphan_shares + stale_doa_shares,
            stale_shares_breakdown=dict(orphan=stale_orphan_shares, doa=stale_doa_shares),
            current_payout=node.get_current_txouts().get(bitcoin_data.pubkey_hash_to_script2(wb.my_pubkey_hash), 0)*1e-8,
            peers=dict(
                incoming=sum(1 for peer in node.p2p_node.peers.itervalues() if peer.incoming),
                outgoing=sum(1 for peer in node.p2p_node.peers.itervalues() if not peer.incoming),
            ),
            attempts_to_share=bitcoin_data.target_to_average_attempts(node.tracker.items[node.best_share_var.value].max_target),
            attempts_to_block=bitcoin_data.target_to_average_attempts(node.bitcoind_work.value['bits'].target),
            block_value=node.bitcoind_work.value['subsidy']*1e-8,
        ))
        
        with open(os.path.join(datadir_path, 'stats'), 'wb') as f:
            f.write(json.dumps(stat_log))
    x = deferral.RobustLoopingCall(update_stat_log)
    x.start(5*60)
    stop_event.watch(x.stop)
    new_root.putChild('log', WebInterface(lambda: stat_log))
    
    def get_share(share_hash_str):
        if int(share_hash_str, 16) not in node.tracker.items:
            return None
        share = node.tracker.items[int(share_hash_str, 16)]
        
        return dict(
            parent='%064x' % share.previous_hash,
            children=['%064x' % x for x in sorted(node.tracker.reverse.get(share.hash, set()), key=lambda sh: -len(node.tracker.reverse.get(sh, set())))], # sorted from most children to least children
            type_name=type(share).__name__,
            local=dict(
                verified=share.hash in node.tracker.verified.items,
                time_first_seen=start_time if share.time_seen == 0 else share.time_seen,
                peer_first_received_from=share.peer_addr,
            ),
            share_data=dict(
                timestamp=share.timestamp,
                target=share.target,
                max_target=share.max_target,
                payout_address=bitcoin_data.script2_to_address(share.new_script, node.net.PARENT),
                donation=share.share_data['donation']/65535,
                stale_info=share.share_data['stale_info'],
                nonce=share.share_data['nonce'],
                desired_version=share.share_data['desired_version'],
                absheight=share.absheight,
                abswork=share.abswork,
            ),
            block=dict(
                hash='%064x' % share.header_hash,
                header=dict(
                    version=share.header['version'],
                    previous_block='%064x' % share.header['previous_block'],
                    merkle_root='%064x' % share.header['merkle_root'],
                    timestamp=share.header['timestamp'],
                    target=share.header['bits'].target,
                    nonce=share.header['nonce'],
                ),
                gentx=dict(
                    hash='%064x' % share.gentx_hash,
                    coinbase=share.share_data['coinbase'].ljust(2, '\x00').encode('hex'),
                    value=share.share_data['subsidy']*1e-8,
                    last_txout_nonce='%016x' % share.contents['last_txout_nonce'],
                ),
                other_transaction_hashes=['%064x' % x for x in share.get_other_tx_hashes(node.tracker)],
            ),
        )
    new_root.putChild('share', WebInterface(lambda share_hash_str: get_share(share_hash_str)))
    new_root.putChild('heads', WebInterface(lambda: ['%064x' % x for x in node.tracker.heads]))
    new_root.putChild('verified_heads', WebInterface(lambda: ['%064x' % x for x in node.tracker.verified.heads]))
    new_root.putChild('tails', WebInterface(lambda: ['%064x' % x for t in node.tracker.tails for x in node.tracker.reverse.get(t, set())]))
    new_root.putChild('verified_tails', WebInterface(lambda: ['%064x' % x for t in node.tracker.verified.tails for x in node.tracker.verified.reverse.get(t, set())]))
    new_root.putChild('best_share_hash', WebInterface(lambda: '%064x' % node.best_share_var.value))
    new_root.putChild('my_share_hashes', WebInterface(lambda: ['%064x' % my_share_hash for my_share_hash in wb.my_share_hashes]))
    def get_share_data(share_hash_str):
        if int(share_hash_str, 16) not in node.tracker.items:
            return ''
        share = node.tracker.items[int(share_hash_str, 16)]
        return p2pool_data.share_type.pack(share.as_share1a())
    new_root.putChild('share_data', WebInterface(lambda share_hash_str: get_share_data(share_hash_str), 'application/octet-stream'))
    new_root.putChild('currency_info', WebInterface(lambda: dict(
        symbol=node.net.PARENT.SYMBOL,
        block_explorer_url_prefix=node.net.PARENT.BLOCK_EXPLORER_URL_PREFIX,
        address_explorer_url_prefix=node.net.PARENT.ADDRESS_EXPLORER_URL_PREFIX,
        tx_explorer_url_prefix=node.net.PARENT.TX_EXPLORER_URL_PREFIX,
    )))
    new_root.putChild('version', WebInterface(lambda: p2pool.__version__))
    
    hd_path = os.path.join(datadir_path, 'graph_db')
    hd_data = _atomic_read(hd_path)
    hd_obj = {}
    if hd_data is not None:
        try:
            hd_obj = json.loads(hd_data)
        except Exception:
            log.err(None, 'Error reading graph database:')
    dataview_descriptions = {
        'last_hour': graph.DataViewDescription(150, 60*60),
        'last_day': graph.DataViewDescription(300, 60*60*24),
        'last_week': graph.DataViewDescription(300, 60*60*24*7),
        'last_month': graph.DataViewDescription(300, 60*60*24*30),
        'last_year': graph.DataViewDescription(300, 60*60*24*365.25),
    }
    hd = graph.HistoryDatabase.from_obj({
        'local_hash_rate': graph.DataStreamDescription(dataview_descriptions, is_gauge=False),
        'local_dead_hash_rate': graph.DataStreamDescription(dataview_descriptions, is_gauge=False),
        'local_share_hash_rates': graph.DataStreamDescription(dataview_descriptions, is_gauge=False,
            multivalues=True, multivalue_undefined_means_0=True,
            default_func=graph.make_multivalue_migrator(dict(good='local_share_hash_rate', dead='local_dead_share_hash_rate', orphan='local_orphan_share_hash_rate'),
                post_func=lambda bins: [dict((k, (v[0] - (sum(bin.get(rem_k, (0, 0))[0] for rem_k in ['dead', 'orphan']) if k == 'good' else 0), v[1])) for k, v in bin.iteritems()) for bin in bins])),
        'pool_rates': graph.DataStreamDescription(dataview_descriptions, multivalues=True,
            multivalue_undefined_means_0=True),
        'current_payout': graph.DataStreamDescription(dataview_descriptions),
        'current_payouts': graph.DataStreamDescription(dataview_descriptions, multivalues=True),
        'peers': graph.DataStreamDescription(dataview_descriptions, multivalues=True, default_func=graph.make_multivalue_migrator(dict(incoming='incoming_peers', outgoing='outgoing_peers'))),
        'miner_hash_rates': graph.DataStreamDescription(dataview_descriptions, is_gauge=False, multivalues=True),
        'miner_dead_hash_rates': graph.DataStreamDescription(dataview_descriptions, is_gauge=False, multivalues=True),
        'desired_version_rates': graph.DataStreamDescription(dataview_descriptions, multivalues=True,
            multivalue_undefined_means_0=True),
        'traffic_rate': graph.DataStreamDescription(dataview_descriptions, is_gauge=False, multivalues=True),
        'getwork_latency': graph.DataStreamDescription(dataview_descriptions),
        'memory_usage': graph.DataStreamDescription(dataview_descriptions),
    }, hd_obj)
    x = deferral.RobustLoopingCall(lambda: _atomic_write(hd_path, json.dumps(hd.to_obj())))
    x.start(100)
    stop_event.watch(x.stop)
    @wb.pseudoshare_received.watch
    def _(work, dead, user):
        t = time.time()
        hd.datastreams['local_hash_rate'].add_datum(t, work)
        if dead:
            hd.datastreams['local_dead_hash_rate'].add_datum(t, work)
        if user is not None:
            hd.datastreams['miner_hash_rates'].add_datum(t, {user: work})
            if dead:
                hd.datastreams['miner_dead_hash_rates'].add_datum(t, {user: work})
    @wb.share_received.watch
    def _(work, dead, share_hash):
        t = time.time()
        if not dead:
            hd.datastreams['local_share_hash_rates'].add_datum(t, dict(good=work))
        else:
            hd.datastreams['local_share_hash_rates'].add_datum(t, dict(dead=work))
        def later():
            res = node.tracker.is_child_of(share_hash, node.best_share_var.value)
            if res is None: res = False # share isn't connected to sharechain? assume orphaned
            if res and dead: # share was DOA, but is now in sharechain
                # move from dead to good
                hd.datastreams['local_share_hash_rates'].add_datum(t, dict(dead=-work, good=work))
            elif not res and not dead: # share wasn't DOA, and isn't in sharechain
                # move from good to orphan
                hd.datastreams['local_share_hash_rates'].add_datum(t, dict(good=-work, orphan=work))
        reactor.callLater(200, later)
    @node.p2p_node.traffic_happened.watch
    def _(name, bytes):
        hd.datastreams['traffic_rate'].add_datum(time.time(), {name: bytes})
    def add_point():
        if node.tracker.get_height(node.best_share_var.value) < 10:
            return None
        lookbehind = min(node.net.CHAIN_LENGTH, 60*60//node.net.SHARE_PERIOD, node.tracker.get_height(node.best_share_var.value))
        t = time.time()
        
        pool_rates = p2pool_data.get_stale_counts(node.tracker, node.best_share_var.value, lookbehind, rates=True)
        pool_total = sum(pool_rates.itervalues())
        hd.datastreams['pool_rates'].add_datum(t, pool_rates)
        
        current_txouts = node.get_current_txouts()
        hd.datastreams['current_payout'].add_datum(t, current_txouts.get(bitcoin_data.pubkey_hash_to_script2(wb.my_pubkey_hash), 0)*1e-8)
        miner_hash_rates, miner_dead_hash_rates = wb.get_local_rates()
        current_txouts_by_address = dict((bitcoin_data.script2_to_address(script, node.net.PARENT), amount) for script, amount in current_txouts.iteritems())
        hd.datastreams['current_payouts'].add_datum(t, dict((user, current_txouts_by_address[user]*1e-8) for user in miner_hash_rates if user in current_txouts_by_address))
        
        hd.datastreams['peers'].add_datum(t, dict(
            incoming=sum(1 for peer in node.p2p_node.peers.itervalues() if peer.incoming),
            outgoing=sum(1 for peer in node.p2p_node.peers.itervalues() if not peer.incoming),
        ))
        
        vs = p2pool_data.get_desired_version_counts(node.tracker, node.best_share_var.value, lookbehind)
        vs_total = sum(vs.itervalues())
        hd.datastreams['desired_version_rates'].add_datum(t, dict((str(k), v/vs_total*pool_total) for k, v in vs.iteritems()))
        try:
            hd.datastreams['memory_usage'].add_datum(t, memory.resident())
        except:
            if p2pool.DEBUG:
                traceback.print_exc()
    x = deferral.RobustLoopingCall(add_point)
    x.start(5)
    stop_event.watch(x.stop)
    @node.bitcoind_work.changed.watch
    def _(new_work):
        hd.datastreams['getwork_latency'].add_datum(time.time(), new_work['latency'])
    new_root.putChild('graph_data', WebInterface(lambda source, view: hd.datastreams[source].dataviews[view].get_data(time.time())))
    
    web_root.putChild('static', static.File(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'web-static')))
    
    return web_root

########NEW FILE########
__FILENAME__ = work
from __future__ import division

import base64
import random
import re
import sys
import time

from twisted.internet import defer
from twisted.python import log

import bitcoin.getwork as bitcoin_getwork, bitcoin.data as bitcoin_data
from bitcoin import helper, script, worker_interface
from util import forest, jsonrpc, variable, deferral, math, pack
import p2pool, p2pool.data as p2pool_data

class WorkerBridge(worker_interface.WorkerBridge):
    COINBASE_NONCE_LENGTH = 8
    
    def __init__(self, node, my_pubkey_hash, donation_percentage, merged_urls, worker_fee):
        worker_interface.WorkerBridge.__init__(self)
        self.recent_shares_ts_work = []
        
        self.node = node
        self.my_pubkey_hash = my_pubkey_hash
        self.donation_percentage = donation_percentage
        self.worker_fee = worker_fee
        
        self.net = self.node.net.PARENT
        self.running = True
        self.pseudoshare_received = variable.Event()
        self.share_received = variable.Event()
        self.local_rate_monitor = math.RateMonitor(10*60)
        self.local_addr_rate_monitor = math.RateMonitor(10*60)
        
        self.removed_unstales_var = variable.Variable((0, 0, 0))
        self.removed_doa_unstales_var = variable.Variable(0)
        
        
        self.my_share_hashes = set()
        self.my_doa_share_hashes = set()
        
        self.tracker_view = forest.TrackerView(self.node.tracker, forest.get_attributedelta_type(dict(forest.AttributeDelta.attrs,
            my_count=lambda share: 1 if share.hash in self.my_share_hashes else 0,
            my_doa_count=lambda share: 1 if share.hash in self.my_doa_share_hashes else 0,
            my_orphan_announce_count=lambda share: 1 if share.hash in self.my_share_hashes and share.share_data['stale_info'] == 'orphan' else 0,
            my_dead_announce_count=lambda share: 1 if share.hash in self.my_share_hashes and share.share_data['stale_info'] == 'doa' else 0,
        )))
        
        @self.node.tracker.verified.removed.watch
        def _(share):
            if share.hash in self.my_share_hashes and self.node.tracker.is_child_of(share.hash, self.node.best_share_var.value):
                assert share.share_data['stale_info'] in [None, 'orphan', 'doa'] # we made these shares in this instance
                self.removed_unstales_var.set((
                    self.removed_unstales_var.value[0] + 1,
                    self.removed_unstales_var.value[1] + (1 if share.share_data['stale_info'] == 'orphan' else 0),
                    self.removed_unstales_var.value[2] + (1 if share.share_data['stale_info'] == 'doa' else 0),
                ))
            if share.hash in self.my_doa_share_hashes and self.node.tracker.is_child_of(share.hash, self.node.best_share_var.value):
                self.removed_doa_unstales_var.set(self.removed_doa_unstales_var.value + 1)
        
        # MERGED WORK
        
        self.merged_work = variable.Variable({})
        
        @defer.inlineCallbacks
        def set_merged_work(merged_url, merged_userpass):
            merged_proxy = jsonrpc.HTTPProxy(merged_url, dict(Authorization='Basic ' + base64.b64encode(merged_userpass)))
            while self.running:
                auxblock = yield deferral.retry('Error while calling merged getauxblock on %s:' % (merged_url,), 30)(merged_proxy.rpc_getauxblock)()
                self.merged_work.set(math.merge_dicts(self.merged_work.value, {auxblock['chainid']: dict(
                    hash=int(auxblock['hash'], 16),
                    target='p2pool' if auxblock['target'] == 'p2pool' else pack.IntType(256).unpack(auxblock['target'].decode('hex')),
                    merged_proxy=merged_proxy,
                )}))
                yield deferral.sleep(1)
        for merged_url, merged_userpass in merged_urls:
            set_merged_work(merged_url, merged_userpass)
        
        @self.merged_work.changed.watch
        def _(new_merged_work):
            print 'Got new merged mining work!'
        
        # COMBINE WORK
        
        self.current_work = variable.Variable(None)
        def compute_work():
            t = self.node.bitcoind_work.value
            bb = self.node.best_block_header.value
            if bb is not None and bb['previous_block'] == t['previous_block'] and self.node.net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(bb)) <= t['bits'].target:
                print 'Skipping from block %x to block %x!' % (bb['previous_block'],
                    bitcoin_data.hash256(bitcoin_data.block_header_type.pack(bb)))
                t = dict(
                    version=bb['version'],
                    previous_block=bitcoin_data.hash256(bitcoin_data.block_header_type.pack(bb)),
                    bits=bb['bits'], # not always true
                    coinbaseflags='',
                    height=t['height'] + 1,
                    time=bb['timestamp'] + 600, # better way?
                    transactions=[],
                    transaction_fees=[],
                    merkle_link=bitcoin_data.calculate_merkle_link([None], 0),
                    subsidy=self.node.net.PARENT.SUBSIDY_FUNC(self.node.bitcoind_work.value['height']),
                    last_update=self.node.bitcoind_work.value['last_update'],
                )
            
            self.current_work.set(t)
        self.node.bitcoind_work.changed.watch(lambda _: compute_work())
        self.node.best_block_header.changed.watch(lambda _: compute_work())
        compute_work()
        
        self.new_work_event = variable.Event()
        @self.current_work.transitioned.watch
        def _(before, after):
            # trigger LP if version/previous_block/bits changed or transactions changed from nothing
            if any(before[x] != after[x] for x in ['version', 'previous_block', 'bits']) or (not before['transactions'] and after['transactions']):
                self.new_work_event.happened()
        self.merged_work.changed.watch(lambda _: self.new_work_event.happened())
        self.node.best_share_var.changed.watch(lambda _: self.new_work_event.happened())
    
    def stop(self):
        self.running = False
    
    def get_stale_counts(self):
        '''Returns (orphans, doas), total, (orphans_recorded_in_chain, doas_recorded_in_chain)'''
        my_shares = len(self.my_share_hashes)
        my_doa_shares = len(self.my_doa_share_hashes)
        delta = self.tracker_view.get_delta_to_last(self.node.best_share_var.value)
        my_shares_in_chain = delta.my_count + self.removed_unstales_var.value[0]
        my_doa_shares_in_chain = delta.my_doa_count + self.removed_doa_unstales_var.value
        orphans_recorded_in_chain = delta.my_orphan_announce_count + self.removed_unstales_var.value[1]
        doas_recorded_in_chain = delta.my_dead_announce_count + self.removed_unstales_var.value[2]
        
        my_shares_not_in_chain = my_shares - my_shares_in_chain
        my_doa_shares_not_in_chain = my_doa_shares - my_doa_shares_in_chain
        
        return (my_shares_not_in_chain - my_doa_shares_not_in_chain, my_doa_shares_not_in_chain), my_shares, (orphans_recorded_in_chain, doas_recorded_in_chain)
    
    def get_user_details(self, username):
        contents = re.split('([+/])', username)
        assert len(contents) % 2 == 1
        
        user, contents2 = contents[0], contents[1:]
        
        desired_pseudoshare_target = None
        desired_share_target = None
        for symbol, parameter in zip(contents2[::2], contents2[1::2]):
            if symbol == '+':
                try:
                    desired_pseudoshare_target = bitcoin_data.difficulty_to_target(float(parameter))
                except:
                    if p2pool.DEBUG:
                        log.err()
            elif symbol == '/':
                try:
                    desired_share_target = bitcoin_data.difficulty_to_target(float(parameter))
                except:
                    if p2pool.DEBUG:
                        log.err()
        
        if random.uniform(0, 100) < self.worker_fee:
            pubkey_hash = self.my_pubkey_hash
        else:
            try:
                pubkey_hash = bitcoin_data.address_to_pubkey_hash(user, self.node.net.PARENT)
            except: # XXX blah
                pubkey_hash = self.my_pubkey_hash
        
        return user, pubkey_hash, desired_share_target, desired_pseudoshare_target
    
    def preprocess_request(self, user):
        if (self.node.p2p_node is None or len(self.node.p2p_node.peers) == 0) and self.node.net.PERSIST:
            raise jsonrpc.Error_for_code(-12345)(u'p2pool is not connected to any peers')
        if time.time() > self.current_work.value['last_update'] + 60:
            raise jsonrpc.Error_for_code(-12345)(u'lost contact with bitcoind')
        user, pubkey_hash, desired_share_target, desired_pseudoshare_target = self.get_user_details(user)
        return pubkey_hash, desired_share_target, desired_pseudoshare_target
    
    def _estimate_local_hash_rate(self):
        if len(self.recent_shares_ts_work) == 50:
            hash_rate = sum(work for ts, work in self.recent_shares_ts_work[1:])//(self.recent_shares_ts_work[-1][0] - self.recent_shares_ts_work[0][0])
            if hash_rate > 0:
                return hash_rate
        return None
    
    def get_local_rates(self):
        miner_hash_rates = {}
        miner_dead_hash_rates = {}
        datums, dt = self.local_rate_monitor.get_datums_in_last()
        for datum in datums:
            miner_hash_rates[datum['user']] = miner_hash_rates.get(datum['user'], 0) + datum['work']/dt
            if datum['dead']:
                miner_dead_hash_rates[datum['user']] = miner_dead_hash_rates.get(datum['user'], 0) + datum['work']/dt
        return miner_hash_rates, miner_dead_hash_rates
    
    def get_local_addr_rates(self):
        addr_hash_rates = {}
        datums, dt = self.local_addr_rate_monitor.get_datums_in_last()
        for datum in datums:
            addr_hash_rates[datum['pubkey_hash']] = addr_hash_rates.get(datum['pubkey_hash'], 0) + datum['work']/dt
        return addr_hash_rates
    
    def get_work(self, pubkey_hash, desired_share_target, desired_pseudoshare_target):
        if self.node.best_share_var.value is None and self.node.net.PERSIST:
            raise jsonrpc.Error_for_code(-12345)(u'p2pool is downloading shares')
        
        if self.merged_work.value:
            tree, size = bitcoin_data.make_auxpow_tree(self.merged_work.value)
            mm_hashes = [self.merged_work.value.get(tree.get(i), dict(hash=0))['hash'] for i in xrange(size)]
            mm_data = '\xfa\xbemm' + bitcoin_data.aux_pow_coinbase_type.pack(dict(
                merkle_root=bitcoin_data.merkle_hash(mm_hashes),
                size=size,
                nonce=0,
            ))
            mm_later = [(aux_work, mm_hashes.index(aux_work['hash']), mm_hashes) for chain_id, aux_work in self.merged_work.value.iteritems()]
        else:
            mm_data = ''
            mm_later = []
        
        tx_hashes = [bitcoin_data.hash256(bitcoin_data.tx_type.pack(tx)) for tx in self.current_work.value['transactions']]
        tx_map = dict(zip(tx_hashes, self.current_work.value['transactions']))
        
        previous_share = self.node.tracker.items[self.node.best_share_var.value] if self.node.best_share_var.value is not None else None
        if previous_share is None:
            share_type = p2pool_data.Share
        else:
            previous_share_type = type(previous_share)
            
            if previous_share_type.SUCCESSOR is None or self.node.tracker.get_height(previous_share.hash) < self.node.net.CHAIN_LENGTH:
                share_type = previous_share_type
            else:
                successor_type = previous_share_type.SUCCESSOR
                
                counts = p2pool_data.get_desired_version_counts(self.node.tracker,
                    self.node.tracker.get_nth_parent_hash(previous_share.hash, self.node.net.CHAIN_LENGTH*9//10), self.node.net.CHAIN_LENGTH//10)
                upgraded = counts.get(successor_type.VERSION, 0)/sum(counts.itervalues())
                if upgraded > .65:
                    print 'Switchover imminent. Upgraded: %.3f%% Threshold: %.3f%%' % (upgraded*100, 95)
                print 
                # Share -> NewShare only valid if 95% of hashes in [net.CHAIN_LENGTH*9//10, net.CHAIN_LENGTH] for new version
                if counts.get(successor_type.VERSION, 0) > sum(counts.itervalues())*95//100:
                    share_type = successor_type
                else:
                    share_type = previous_share_type
        
        if desired_share_target is None:
            desired_share_target = 2**256-1
            local_hash_rate = self._estimate_local_hash_rate()
            if local_hash_rate is not None:
                desired_share_target = min(desired_share_target,
                    bitcoin_data.average_attempts_to_target(local_hash_rate * self.node.net.SHARE_PERIOD / 0.0167)) # limit to 1.67% of pool shares by modulating share difficulty
            
            local_addr_rates = self.get_local_addr_rates()
            lookbehind = 3600//self.node.net.SHARE_PERIOD
            block_subsidy = self.node.bitcoind_work.value['subsidy']
            if previous_share is not None and self.node.tracker.get_height(previous_share.hash) > lookbehind:
                expected_payout_per_block = local_addr_rates.get(pubkey_hash, 0)/p2pool_data.get_pool_attempts_per_second(self.node.tracker, self.node.best_share_var.value, lookbehind) \
                    * block_subsidy*(1-self.donation_percentage/100) # XXX doesn't use global stale rate to compute pool hash
                if expected_payout_per_block < self.node.net.PARENT.DUST_THRESHOLD:
                    desired_share_target = min(desired_share_target,
                        bitcoin_data.average_attempts_to_target((bitcoin_data.target_to_average_attempts(self.node.bitcoind_work.value['bits'].target)*self.node.net.SPREAD)*self.node.net.PARENT.DUST_THRESHOLD/block_subsidy)
                    )
        
        if True:
            share_info, gentx, other_transaction_hashes, get_share = share_type.generate_transaction(
                tracker=self.node.tracker,
                share_data=dict(
                    previous_share_hash=self.node.best_share_var.value,
                    coinbase=(script.create_push_script([
                        self.current_work.value['height'],
                        ] + ([mm_data] if mm_data else []) + [
                    ]) + self.current_work.value['coinbaseflags'])[:100],
                    nonce=random.randrange(2**32),
                    pubkey_hash=pubkey_hash,
                    subsidy=self.current_work.value['subsidy'],
                    donation=math.perfect_round(65535*self.donation_percentage/100),
                    stale_info=(lambda (orphans, doas), total, (orphans_recorded_in_chain, doas_recorded_in_chain):
                        'orphan' if orphans > orphans_recorded_in_chain else
                        'doa' if doas > doas_recorded_in_chain else
                        None
                    )(*self.get_stale_counts()),
                    desired_version=(share_type.SUCCESSOR if share_type.SUCCESSOR is not None else share_type).VOTING_VERSION,
                ),
                block_target=self.current_work.value['bits'].target,
                desired_timestamp=int(time.time() + 0.5),
                desired_target=desired_share_target,
                ref_merkle_link=dict(branch=[], index=0),
                desired_other_transaction_hashes_and_fees=zip(tx_hashes, self.current_work.value['transaction_fees']),
                net=self.node.net,
                known_txs=tx_map,
                base_subsidy=self.node.net.PARENT.SUBSIDY_FUNC(self.current_work.value['height']),
            )
        
        packed_gentx = bitcoin_data.tx_type.pack(gentx)
        other_transactions = [tx_map[tx_hash] for tx_hash in other_transaction_hashes]
        
        mm_later = [(dict(aux_work, target=aux_work['target'] if aux_work['target'] != 'p2pool' else share_info['bits'].target), index, hashes) for aux_work, index, hashes in mm_later]
        
        if desired_pseudoshare_target is None:
            target = 2**256-1
            local_hash_rate = self._estimate_local_hash_rate()
            if local_hash_rate is not None:
                target = min(target,
                    bitcoin_data.average_attempts_to_target(local_hash_rate * 1)) # limit to 1 share response every second by modulating pseudoshare difficulty
        else:
            target = desired_pseudoshare_target
        target = max(target, share_info['bits'].target)
        for aux_work, index, hashes in mm_later:
            target = max(target, aux_work['target'])
        target = math.clip(target, self.node.net.PARENT.SANE_TARGET_RANGE)
        
        getwork_time = time.time()
        lp_count = self.new_work_event.times
        merkle_link = bitcoin_data.calculate_merkle_link([None] + other_transaction_hashes, 0)
        
        print 'New work for worker! Difficulty: %.06f Share difficulty: %.06f Total block value: %.6f %s including %i transactions' % (
            bitcoin_data.target_to_difficulty(target),
            bitcoin_data.target_to_difficulty(share_info['bits'].target),
            self.current_work.value['subsidy']*1e-8, self.node.net.PARENT.SYMBOL,
            len(self.current_work.value['transactions']),
        )
        
        ba = dict(
            version=min(self.current_work.value['version'], 2),
            previous_block=self.current_work.value['previous_block'],
            merkle_link=merkle_link,
            coinb1=packed_gentx[:-self.COINBASE_NONCE_LENGTH-4],
            coinb2=packed_gentx[-4:],
            timestamp=self.current_work.value['time'],
            bits=self.current_work.value['bits'],
            share_target=target,
        )
        
        received_header_hashes = set()
        
        def got_response(header, user, coinbase_nonce):
            assert len(coinbase_nonce) == self.COINBASE_NONCE_LENGTH
            new_packed_gentx = packed_gentx[:-self.COINBASE_NONCE_LENGTH-4] + coinbase_nonce + packed_gentx[-4:] if coinbase_nonce != '\0'*self.COINBASE_NONCE_LENGTH else packed_gentx
            new_gentx = bitcoin_data.tx_type.unpack(new_packed_gentx) if coinbase_nonce != '\0'*self.COINBASE_NONCE_LENGTH else gentx
            
            header_hash = bitcoin_data.hash256(bitcoin_data.block_header_type.pack(header))
            pow_hash = self.node.net.PARENT.POW_FUNC(bitcoin_data.block_header_type.pack(header))
            try:
                if pow_hash <= header['bits'].target or p2pool.DEBUG:
                    helper.submit_block(dict(header=header, txs=[new_gentx] + other_transactions), False, self.node.factory, self.node.bitcoind, self.node.bitcoind_work, self.node.net)
                    if pow_hash <= header['bits'].target:
                        print
                        print 'GOT BLOCK FROM MINER! Passing to bitcoind! %s%064x' % (self.node.net.PARENT.BLOCK_EXPLORER_URL_PREFIX, header_hash)
                        print
            except:
                log.err(None, 'Error while processing potential block:')
            
            user, _, _, _ = self.get_user_details(user)
            assert header['previous_block'] == ba['previous_block']
            assert header['merkle_root'] == bitcoin_data.check_merkle_link(bitcoin_data.hash256(new_packed_gentx), merkle_link)
            assert header['bits'] == ba['bits']
            
            on_time = self.new_work_event.times == lp_count
            
            for aux_work, index, hashes in mm_later:
                try:
                    if pow_hash <= aux_work['target'] or p2pool.DEBUG:
                        df = deferral.retry('Error submitting merged block: (will retry)', 10, 10)(aux_work['merged_proxy'].rpc_getauxblock)(
                            pack.IntType(256, 'big').pack(aux_work['hash']).encode('hex'),
                            bitcoin_data.aux_pow_type.pack(dict(
                                merkle_tx=dict(
                                    tx=new_gentx,
                                    block_hash=header_hash,
                                    merkle_link=merkle_link,
                                ),
                                merkle_link=bitcoin_data.calculate_merkle_link(hashes, index),
                                parent_block_header=header,
                            )).encode('hex'),
                        )
                        @df.addCallback
                        def _(result, aux_work=aux_work):
                            if result != (pow_hash <= aux_work['target']):
                                print >>sys.stderr, 'Merged block submittal result: %s Expected: %s' % (result, pow_hash <= aux_work['target'])
                            else:
                                print 'Merged block submittal result: %s' % (result,)
                        @df.addErrback
                        def _(err):
                            log.err(err, 'Error submitting merged block:')
                except:
                    log.err(None, 'Error while processing merged mining POW:')
            
            if pow_hash <= share_info['bits'].target and header_hash not in received_header_hashes:
                last_txout_nonce = pack.IntType(8*self.COINBASE_NONCE_LENGTH).unpack(coinbase_nonce)
                share = get_share(header, last_txout_nonce)
                
                print 'GOT SHARE! %s %s prev %s age %.2fs%s' % (
                    user,
                    p2pool_data.format_hash(share.hash),
                    p2pool_data.format_hash(share.previous_hash),
                    time.time() - getwork_time,
                    ' DEAD ON ARRIVAL' if not on_time else '',
                )
                self.my_share_hashes.add(share.hash)
                if not on_time:
                    self.my_doa_share_hashes.add(share.hash)
                
                self.node.tracker.add(share)
                self.node.set_best_share()
                
                try:
                    if (pow_hash <= header['bits'].target or p2pool.DEBUG) and self.node.p2p_node is not None:
                        self.node.p2p_node.broadcast_share(share.hash)
                except:
                    log.err(None, 'Error forwarding block solution:')
                
                self.share_received.happened(bitcoin_data.target_to_average_attempts(share.target), not on_time, share.hash)
            
            if pow_hash > target:
                print 'Worker %s submitted share with hash > target:' % (user,)
                print '    Hash:   %56x' % (pow_hash,)
                print '    Target: %56x' % (target,)
            elif header_hash in received_header_hashes:
                print >>sys.stderr, 'Worker %s submitted share more than once!' % (user,)
            else:
                received_header_hashes.add(header_hash)
                
                self.pseudoshare_received.happened(bitcoin_data.target_to_average_attempts(target), not on_time, user)
                self.recent_shares_ts_work.append((time.time(), bitcoin_data.target_to_average_attempts(target)))
                while len(self.recent_shares_ts_work) > 50:
                    self.recent_shares_ts_work.pop(0)
                self.local_rate_monitor.add_datum(dict(work=bitcoin_data.target_to_average_attempts(target), dead=not on_time, user=user, share_target=share_info['bits'].target))
                self.local_addr_rate_monitor.add_datum(dict(work=bitcoin_data.target_to_average_attempts(target), pubkey_hash=pubkey_hash))
            
            return on_time
        
        return ba, got_response

########NEW FILE########
__FILENAME__ = run_p2pool
#!/usr/bin/env python

from p2pool import main

main.run()

########NEW FILE########
__FILENAME__ = Client
from __future__ import nested_scopes

"""
################################################################################
#
# SOAPpy - Cayce Ullman       (cayce@actzero.com)
#          Brian Matthews     (blm@actzero.com)
#          Gregory Warnes     (Gregory.R.Warnes@Pfizer.com)
#          Christopher Blunck (blunck@gst.com)
#
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""
ident = '$Id: Client.py 1496 2010-03-04 23:46:17Z pooryorick $'

from version import __version__

#import xml.sax
import urllib
from types import *
import re
import base64
import socket, httplib
from httplib import HTTPConnection, HTTP
import Cookie

# SOAPpy modules
from Errors      import *
from Config      import Config
from Parser      import parseSOAPRPC
from SOAPBuilder import buildSOAP
from Utilities   import *
from Types       import faultType, simplify

################################################################################
# Client
################################################################################


def SOAPUserAgent():
    return "SOAPpy " + __version__ + " (pywebsvcs.sf.net)"


class SOAPAddress:
    def __init__(self, url, config = Config):
        proto, uri = urllib.splittype(url)

        # apply some defaults
        if uri[0:2] != '//':
            if proto != None:
                uri = proto + ':' + uri

            uri = '//' + uri
            proto = 'http'

        host, path = urllib.splithost(uri)

        try:
            int(host)
            host = 'localhost:' + host
        except:
            pass

        if not path:
            path = '/'

        if proto not in ('http', 'https', 'httpg'):
            raise IOError, "unsupported SOAP protocol"
        if proto == 'httpg' and not config.GSIclient:
            raise AttributeError, \
                  "GSI client not supported by this Python installation"
        if proto == 'https' and not config.SSLclient:
            raise AttributeError, \
                "SSL client not supported by this Python installation"

        self.user,host = urllib.splituser(host)
        self.proto = proto
        self.host = host
        self.path = path

    def __str__(self):
        return "%(proto)s://%(host)s%(path)s" % self.__dict__

    __repr__ = __str__

class SOAPTimeoutError(socket.timeout):
    '''This exception is raised when a timeout occurs in SOAP operations'''
    pass

class HTTPConnectionWithTimeout(HTTPConnection):
    '''Extend HTTPConnection for timeout support'''

    def __init__(self, host, port=None, strict=None, timeout=None):
        HTTPConnection.__init__(self, host, port, strict)
        self._timeout = timeout

    def connect(self):
        HTTPConnection.connect(self)
        if self.sock and self._timeout:
            self.sock.settimeout(self._timeout) 


class HTTPWithTimeout(HTTP):

    _connection_class = HTTPConnectionWithTimeout

    ## this __init__ copied from httplib.HTML class
    def __init__(self, host='', port=None, strict=None, timeout=None):
        "Provide a default host, since the superclass requires one."

        # some joker passed 0 explicitly, meaning default port
        if port == 0:
            port = None

        # Note that we may pass an empty string as the host; this will throw
        # an error when we attempt to connect. Presumably, the client code
        # will call connect before then, with a proper host.
        self._setup(self._connection_class(host, port, strict, timeout))

class HTTPTransport:
            

    def __init__(self):
        self.cookies = Cookie.SimpleCookie();

    def getNS(self, original_namespace, data):
        """Extract the (possibly extended) namespace from the returned
        SOAP message."""

        if type(original_namespace) == StringType:
            pattern="xmlns:\w+=['\"](" + original_namespace + "[^'\"]*)['\"]"
            match = re.search(pattern, data)
            if match:
                return match.group(1)
            else:
                return original_namespace
        else:
            return original_namespace
    
    def __addcookies(self, r):
        '''Add cookies from self.cookies to request r
        '''
        for cname, morsel in self.cookies.items():
            attrs = []
            value = morsel.get('version', '')
            if value != '' and value != '0':
                attrs.append('$Version=%s' % value)
            attrs.append('%s=%s' % (cname, morsel.coded_value))
            value = morsel.get('path')
            if value:
                attrs.append('$Path=%s' % value)
            value = morsel.get('domain')
            if value:
                attrs.append('$Domain=%s' % value)
            r.putheader('Cookie', "; ".join(attrs))
    
    def call(self, addr, data, namespace, soapaction = None, encoding = None,
        http_proxy = None, config = Config, timeout=None):

        if not isinstance(addr, SOAPAddress):
            addr = SOAPAddress(addr, config)

        # Build a request
        if http_proxy:
            real_addr = http_proxy
            real_path = addr.proto + "://" + addr.host + addr.path
        else:
            real_addr = addr.host
            real_path = addr.path

        if addr.proto == 'httpg':
            from pyGlobus.io import GSIHTTP
            r = GSIHTTP(real_addr, tcpAttr = config.tcpAttr)
        elif addr.proto == 'https':
            r = httplib.HTTPS(real_addr, key_file=config.SSL.key_file, cert_file=config.SSL.cert_file)
        else:
            r = HTTPWithTimeout(real_addr, timeout=timeout)

        r.putrequest("POST", real_path)

        r.putheader("Host", addr.host)
        r.putheader("User-agent", SOAPUserAgent())
        t = 'text/xml';
        if encoding != None:
            t += '; charset=%s' % encoding
        r.putheader("Content-type", t)
        r.putheader("Content-length", str(len(data)))
        self.__addcookies(r);
        
        # if user is not a user:passwd format
        #    we'll receive a failure from the server. . .I guess (??)
        if addr.user != None:
            val = base64.encodestring(addr.user) 
            r.putheader('Authorization','Basic ' + val.replace('\012',''))

        # This fixes sending either "" or "None"
        if soapaction == None or len(soapaction) == 0:
            r.putheader("SOAPAction", "")
        else:
            r.putheader("SOAPAction", '"%s"' % soapaction)

        if config.dumpHeadersOut:
            s = 'Outgoing HTTP headers'
            debugHeader(s)
            print "POST %s %s" % (real_path, r._http_vsn_str)
            print "Host:", addr.host
            print "User-agent: SOAPpy " + __version__ + " (http://pywebsvcs.sf.net)"
            print "Content-type:", t
            print "Content-length:", len(data)
            print 'SOAPAction: "%s"' % soapaction
            debugFooter(s)

        r.endheaders()

        if config.dumpSOAPOut:
            s = 'Outgoing SOAP'
            debugHeader(s)
            print data,
            if data[-1] != '\n':
                print
            debugFooter(s)

        # send the payload
        r.send(data)

        # read response line
        code, msg, headers = r.getreply()

        self.cookies = Cookie.SimpleCookie();
        if headers:
            content_type = headers.get("content-type","text/xml")
            content_length = headers.get("Content-length")

            for cookie in headers.getallmatchingheaders("Set-Cookie"):
                self.cookies.load(cookie);

        else:
            content_type=None
            content_length=None

        # work around OC4J bug which does '<len>, <len>' for some reaason
        if content_length:
            comma=content_length.find(',')
            if comma>0:
                content_length = content_length[:comma]

        # attempt to extract integer message size
        try:
            message_len = int(content_length)
        except:
            message_len = -1
            
        if message_len < 0:
            # Content-Length missing or invalid; just read the whole socket
            # This won't work with HTTP/1.1 chunked encoding
            data = r.getfile().read()
            message_len = len(data)
        else:
            data = r.getfile().read(message_len)

        if(config.debug):
            print "code=",code
            print "msg=", msg
            print "headers=", headers
            print "content-type=", content_type
            print "data=", data
                
        if config.dumpHeadersIn:
            s = 'Incoming HTTP headers'
            debugHeader(s)
            if headers.headers:
                print "HTTP/1.? %d %s" % (code, msg)
                print "\n".join(map (lambda x: x.strip(), headers.headers))
            else:
                print "HTTP/0.9 %d %s" % (code, msg)
            debugFooter(s)

        def startswith(string, val):
            return string[0:len(val)] == val
        
        if code == 500 and not \
               ( startswith(content_type, "text/xml") and message_len > 0 ):
            raise HTTPError(code, msg)

        if config.dumpSOAPIn:
            s = 'Incoming SOAP'
            debugHeader(s)
            print data,
            if (len(data)>0) and (data[-1] != '\n'):
                print
            debugFooter(s)

        if code not in (200, 500):
            raise HTTPError(code, msg)


        # get the new namespace
        if namespace is None:
            new_ns = None
        else:
            new_ns = self.getNS(namespace, data)
        
        # return response payload
        return data, new_ns

################################################################################
# SOAP Proxy
################################################################################
class SOAPProxy:
    def __init__(self, proxy, namespace = None, soapaction = None,
                 header = None, methodattrs = None, transport = HTTPTransport,
                 encoding = 'UTF-8', throw_faults = 1, unwrap_results = None,
                 http_proxy=None, config = Config, noroot = 0,
                 simplify_objects=None, timeout=None):

        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        # get default values for unwrap_results and simplify_objects
        # from config
        if unwrap_results is None:
            self.unwrap_results=config.unwrap_results
        else:
            self.unwrap_results=unwrap_results

        if simplify_objects is None:
            self.simplify_objects=config.simplify_objects
        else:
            self.simplify_objects=simplify_objects

        self.proxy          = SOAPAddress(proxy, config)
        self.namespace      = namespace
        self.soapaction     = soapaction
        self.header         = header
        self.methodattrs    = methodattrs
        self.transport      = transport()
        self.encoding       = encoding
        self.throw_faults   = throw_faults
        self.http_proxy     = http_proxy
        self.config         = config
        self.noroot         = noroot
        self.timeout        = timeout

        # GSI Additions
        if hasattr(config, "channel_mode") and \
               hasattr(config, "delegation_mode"):
            self.channel_mode = config.channel_mode
            self.delegation_mode = config.delegation_mode
        #end GSI Additions
        
    def invoke(self, method, args):
        return self.__call(method, args, {})
        
    def __call(self, name, args, kw, ns = None, sa = None, hd = None,
        ma = None):

        ns = ns or self.namespace
        ma = ma or self.methodattrs

        if sa: # Get soapaction
            if type(sa) == TupleType:
                sa = sa[0]
        else:
            if self.soapaction:
                sa = self.soapaction
            else:
                sa = name
                
        if hd: # Get header
            if type(hd) == TupleType:
                hd = hd[0]
        else:
            hd = self.header

        hd = hd or self.header

        if ma: # Get methodattrs
            if type(ma) == TupleType: ma = ma[0]
        else:
            ma = self.methodattrs
        ma = ma or self.methodattrs

        m = buildSOAP(args = args, kw = kw, method = name, namespace = ns,
            header = hd, methodattrs = ma, encoding = self.encoding,
            config = self.config, noroot = self.noroot)


        call_retry = 0
        try:
            r, self.namespace = self.transport.call(self.proxy, m, ns, sa,
                                                    encoding = self.encoding,
                                                    http_proxy = self.http_proxy,
                                                    config = self.config,
                                                    timeout = self.timeout)

        except socket.timeout:
            raise SOAPTimeoutError

        except Exception, ex:
            #
            # Call failed.
            #
            # See if we have a fault handling vector installed in our
            # config. If we do, invoke it. If it returns a true value,
            # retry the call. 
            #
            # In any circumstance other than the fault handler returning
            # true, reraise the exception. This keeps the semantics of this
            # code the same as without the faultHandler code.
            #

            if hasattr(self.config, "faultHandler"):
                if callable(self.config.faultHandler):
                    call_retry = self.config.faultHandler(self.proxy, ex)
                    if not call_retry:
                        raise
                else:
                    raise
            else:
                raise

        if call_retry:
            try:
                r, self.namespace = self.transport.call(self.proxy, m, ns, sa,
                                                        encoding = self.encoding,
                                                        http_proxy = self.http_proxy,
                                                        config = self.config,
                                                        timeout = self.timeout)
            except socket.timeout:
                raise SOAPTimeoutError
            

        p, attrs = parseSOAPRPC(r, attrs = 1)

        try:
            throw_struct = self.throw_faults and \
                isinstance (p, faultType)
        except:
            throw_struct = 0

        if throw_struct:
            if Config.debug:
                print p
            raise p

        # If unwrap_results=1 and there is only element in the struct,
        # SOAPProxy will assume that this element is the result
        # and return it rather than the struct containing it.
        # Otherwise SOAPproxy will return the struct with all the
        # elements as attributes.
        if self.unwrap_results:
            try:
                count = 0
                for i in p.__dict__.keys():
                    if i[0] != "_":  # don't count the private stuff
                        count += 1
                        t = getattr(p, i)
                if count == 1: # Only one piece of data, bubble it up
                    p = t 
            except:
                pass

        # Automatically simplfy SOAP complex types into the
        # corresponding python types. (structType --> dict,
        # arrayType --> array, etc.)
        if self.simplify_objects:
            p = simplify(p)

        if self.config.returnAllAttrs:
            return p, attrs
        return p

    def _callWithBody(self, body):
        return self.__call(None, body, {})

    def __getattr__(self, name):  # hook to catch method calls
        if name in ( '__del__', '__getinitargs__', '__getnewargs__',
           '__getstate__', '__setstate__', '__reduce__', '__reduce_ex__'):
            raise AttributeError, name
        return self.__Method(self.__call, name, config = self.config)

    # To handle attribute weirdness
    class __Method:
        # Some magic to bind a SOAP method to an RPC server.
        # Supports "nested" methods (e.g. examples.getStateName) -- concept
        # borrowed from xmlrpc/soaplib -- www.pythonware.com
        # Altered (improved?) to let you inline namespaces on a per call
        # basis ala SOAP::LITE -- www.soaplite.com

        def __init__(self, call, name, ns = None, sa = None, hd = None,
            ma = None, config = Config):

            self.__call 	= call
            self.__name 	= name
            self.__ns   	= ns
            self.__sa   	= sa
            self.__hd   	= hd
            self.__ma           = ma
            self.__config       = config
            return

        def __call__(self, *args, **kw):
            if self.__name[0] == "_":
                if self.__name in ["__repr__","__str__"]:
                    return self.__repr__()
                else:
                    return self.__f_call(*args, **kw)
            else:
                return self.__r_call(*args, **kw)
                        
        def __getattr__(self, name):
            if name == '__del__':
                raise AttributeError, name
            if self.__name[0] == "_":
                # Don't nest method if it is a directive
                return self.__class__(self.__call, name, self.__ns,
                    self.__sa, self.__hd, self.__ma)

            return self.__class__(self.__call, "%s.%s" % (self.__name, name),
                self.__ns, self.__sa, self.__hd, self.__ma)

        def __f_call(self, *args, **kw):
            if self.__name == "_ns": self.__ns = args
            elif self.__name == "_sa": self.__sa = args
            elif self.__name == "_hd": self.__hd = args
            elif self.__name == "_ma": self.__ma = args
            return self

        def __r_call(self, *args, **kw):
            return self.__call(self.__name, args, kw, self.__ns, self.__sa,
                self.__hd, self.__ma)

        def __repr__(self):
            return "<%s at %d>" % (self.__class__, id(self))

########NEW FILE########
__FILENAME__ = Config
"""
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: Config.py 1298 2006-11-07 00:54:15Z sanxiyn $'
from version import __version__

import socket
from types import *

from NS import NS

################################################################################
# Configuration class
################################################################################


class SOAPConfig:
    __readonly = ('SSLserver', 'SSLclient', 'GSIserver', 'GSIclient')
    class SSLconfig:
        __slots__ = ('key_file', 'cert_file')
        key_file = None
        cert_file = None

    def __init__(self, config = None, **kw):
        d = self.__dict__

        if config:
            if not isinstance(config, SOAPConfig):
                raise AttributeError, \
                    "initializer must be SOAPConfig instance"

            s = config.__dict__

            for k, v in s.items():
                if k[0] != '_':
                    d[k] = v
        else:
            # Setting debug also sets returnFaultInfo,
            # dumpHeadersIn, dumpHeadersOut, dumpSOAPIn, and dumpSOAPOut
            self.debug = 0
            self.dumpFaultInfo = 1
            # Setting namespaceStyle sets typesNamespace, typesNamespaceURI,
            # schemaNamespace, and schemaNamespaceURI
            self.namespaceStyle = '1999'
            self.strictNamespaces = 0
            self.typed = 1
            self.buildWithNamespacePrefix = 1
            self.returnAllAttrs = 0

            # Strict checking of range for floats and doubles
            self.strict_range = 0

            # Default encoding for dictionary keys
            self.dict_encoding = 'ascii'

            # New argument name handling mechanism.  See
            # README.MethodParameterNaming for details
            self.specialArgs = 1

            # If unwrap_results=1 and there is only element in the struct,
            # SOAPProxy will assume that this element is the result
            # and return it rather than the struct containing it.
            # Otherwise SOAPproxy will return the struct with all the
            # elements as attributes.
            self.unwrap_results = 1

            # Automatically convert SOAP complex types, and
            # (recursively) public contents into the corresponding
            # python types. (Private subobjects have names that start
            # with '_'.)
            #
            # Conversions:
            # - faultType    --> raise python exception
            # - arrayType    --> array
            # - compoundType --> dictionary
            #
            self.simplify_objects = 0

            # Per-class authorization method.  If this is set, before
            # calling a any class method, the specified authorization
            # method will be called.  If it returns 1, the method call
            # will proceed, otherwise the call will throw with an
            # authorization error.
            self.authMethod = None

            # Globus Support if pyGlobus.io available
            try:
                from pyGlobus import io;
                d['GSIserver'] = 1
                d['GSIclient'] = 1
            except:
                d['GSIserver'] = 0
                d['GSIclient'] = 0


            # Server SSL support if M2Crypto.SSL available
            try:
                from M2Crypto import SSL
                d['SSLserver'] = 1
            except:
                d['SSLserver'] = 0

            # Client SSL support if socket.ssl available
            try:
                from socket import ssl
                d['SSLclient'] = 1
            except:
                d['SSLclient'] = 0

            # Cert support
            if d['SSLclient'] or d['SSLserver']:
                d['SSL'] = self.SSLconfig()

        for k, v in kw.items():
            if k[0] != '_':
                setattr(self, k, v)

    def __setattr__(self, name, value):
        if name in self.__readonly:
            raise AttributeError, "readonly configuration setting"

        d = self.__dict__

        if name in ('typesNamespace', 'typesNamespaceURI',
                    'schemaNamespace', 'schemaNamespaceURI'):

            if name[-3:] == 'URI':
                base, uri = name[:-3], 1
            else:
                base, uri = name, 0

            if type(value) == StringType:
                if NS.NSMAP.has_key(value):
                    n = (value, NS.NSMAP[value])
                elif NS.NSMAP_R.has_key(value):
                    n = (NS.NSMAP_R[value], value)
                else:
                    raise AttributeError, "unknown namespace"
            elif type(value) in (ListType, TupleType):
                if uri:
                    n = (value[1], value[0])
                else:
                    n = (value[0], value[1])
            else:
                raise AttributeError, "unknown namespace type"

            d[base], d[base + 'URI'] = n

            try:
                d['namespaceStyle'] = \
                    NS.STMAP_R[(d['typesNamespace'], d['schemaNamespace'])]
            except:
                d['namespaceStyle'] = ''

        elif name == 'namespaceStyle':
            value = str(value)

            if not NS.STMAP.has_key(value):
                raise AttributeError, "unknown namespace style"

            d[name] = value
            n = d['typesNamespace'] = NS.STMAP[value][0]
            d['typesNamespaceURI'] = NS.NSMAP[n]
            n = d['schemaNamespace'] = NS.STMAP[value][1]
            d['schemaNamespaceURI'] = NS.NSMAP[n]

        elif name == 'debug':
            d[name]                     = \
                d['returnFaultInfo']    = \
                d['dumpHeadersIn']      = \
                d['dumpHeadersOut']     = \
                d['dumpSOAPIn']         = \
                d['dumpSOAPOut']        = value

        else:
            d[name] = value


Config = SOAPConfig()

########NEW FILE########
__FILENAME__ = Errors
"""
################################################################################
#
# SOAPpy - Cayce Ullman       (cayce@actzero.com)
#          Brian Matthews     (blm@actzero.com)
#          Gregory Warnes     (Gregory.R.Warnes@Pfizer.com)
#          Christopher Blunck (blunck@gst.com)
#
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: Errors.py 921 2005-02-15 16:32:23Z warnes $'
from version import __version__

import exceptions

################################################################################
# Exceptions
################################################################################
class Error(exceptions.Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return "<Error : %s>" % self.msg
    __repr__ = __str__
    def __call__(self):
        return (msg,)

class RecursionError(Error):
    pass

class UnknownTypeError(Error):
    pass

class HTTPError(Error):
    # indicates an HTTP protocol error
    def __init__(self, code, msg):
        self.code = code
        self.msg  = msg
    def __str__(self):
        return "<HTTPError %s %s>" % (self.code, self.msg)
    __repr__ = __str__
    def __call___(self):
        return (self.code, self.msg, )

class UnderflowError(exceptions.ArithmeticError):
    pass


########NEW FILE########
__FILENAME__ = GSIServer
from __future__ import nested_scopes

"""
GSIServer - Contributed by Ivan R. Judson <judson@mcs.anl.gov>


################################################################################
#
# SOAPpy - Cayce Ullman       (cayce@actzero.com)
#          Brian Matthews     (blm@actzero.com)
#          Gregory Warnes     (Gregory.R.Warnes@Pfizer.com)
#          Christopher Blunck (blunck@gst.com)
#
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: GSIServer.py 1468 2008-05-24 01:55:33Z warnes $'
from version import __version__

#import xml.sax
import re
import socket
import sys
import SocketServer
from types import *
import BaseHTTPServer

# SOAPpy modules
from Parser      import parseSOAPRPC
from Config      import SOAPConfig
from Types       import faultType, voidType, simplify
from NS          import NS
from SOAPBuilder import buildSOAP
from Utilities   import debugHeader, debugFooter

try: from M2Crypto import SSL
except: pass

#####

from Server import *

from pyGlobus.io import GSITCPSocketServer, ThreadingGSITCPSocketServer
from pyGlobus import ioc

def GSIConfig():
    config = SOAPConfig()
    config.channel_mode = ioc.GLOBUS_IO_SECURE_CHANNEL_MODE_GSI_WRAP
    config.delegation_mode = ioc.GLOBUS_IO_SECURE_DELEGATION_MODE_FULL_PROXY
    config.tcpAttr = None
    config.authMethod = "_authorize"
    return config

Config = GSIConfig()

class GSISOAPServer(GSITCPSocketServer, SOAPServerBase):
    def __init__(self, addr = ('localhost', 8000),
                 RequestHandler = SOAPRequestHandler, log = 0,
                 encoding = 'UTF-8', config = Config, namespace = None):

        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        self.namespace          = namespace
        self.objmap             = {}
        self.funcmap            = {}
        self.encoding           = encoding
        self.config             = config
        self.log                = log
        
        self.allow_reuse_address= 1
        
        GSITCPSocketServer.__init__(self, addr, RequestHandler,
                                    self.config.channel_mode,
                                    self.config.delegation_mode,
                                    tcpAttr = self.config.tcpAttr)
        
    def get_request(self):
        sock, addr = GSITCPSocketServer.get_request(self)

        return sock, addr
       
class ThreadingGSISOAPServer(ThreadingGSITCPSocketServer, SOAPServerBase):

    def __init__(self, addr = ('localhost', 8000),
                 RequestHandler = SOAPRequestHandler, log = 0,
                 encoding = 'UTF-8', config = Config, namespace = None):
        
        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        self.namespace          = namespace
        self.objmap             = {}
        self.funcmap            = {}
        self.encoding           = encoding
        self.config             = config
        self.log                = log
        
        self.allow_reuse_address= 1
        
        ThreadingGSITCPSocketServer.__init__(self, addr, RequestHandler,
                                             self.config.channel_mode,
                                             self.config.delegation_mode,
                                             tcpAttr = self.config.tcpAttr)

    def get_request(self):
        sock, addr = ThreadingGSITCPSocketServer.get_request(self)

        return sock, addr


########NEW FILE########
__FILENAME__ = NS
from __future__ import nested_scopes

"""
################################################################################
#
# SOAPpy - Cayce Ullman       (cayce@actzero.com)
#          Brian Matthews     (blm@actzero.com)
#          Gregory Warnes     (Gregory.R.Warnes@Pfizer.com)
#          Christopher Blunck (blunck@gst.com)
#
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: NS.py 1468 2008-05-24 01:55:33Z warnes $'
from version import __version__

##############################################################################
# Namespace Class
################################################################################
def invertDict(dict):
    d = {}

    for k, v in dict.items():
        d[v] = k

    return d

class NS:
    XML  = "http://www.w3.org/XML/1998/namespace"

    ENV  = "http://schemas.xmlsoap.org/soap/envelope/"
    ENC  = "http://schemas.xmlsoap.org/soap/encoding/"

    XSD  = "http://www.w3.org/1999/XMLSchema"
    XSD2 = "http://www.w3.org/2000/10/XMLSchema"
    XSD3 = "http://www.w3.org/2001/XMLSchema"

    XSD_L = [XSD, XSD2, XSD3]
    EXSD_L= [ENC, XSD, XSD2, XSD3]

    XSI   = "http://www.w3.org/1999/XMLSchema-instance"
    XSI2  = "http://www.w3.org/2000/10/XMLSchema-instance"
    XSI3  = "http://www.w3.org/2001/XMLSchema-instance"
    XSI_L = [XSI, XSI2, XSI3]

    URN   = "http://soapinterop.org/xsd"

    # For generated messages
    XML_T = "xml"
    ENV_T = "SOAP-ENV"
    ENC_T = "SOAP-ENC"
    XSD_T = "xsd"
    XSD2_T= "xsd2"
    XSD3_T= "xsd3"
    XSI_T = "xsi"
    XSI2_T= "xsi2"
    XSI3_T= "xsi3"
    URN_T = "urn"

    NSMAP       = {ENV_T: ENV, ENC_T: ENC, XSD_T: XSD, XSD2_T: XSD2,
                    XSD3_T: XSD3, XSI_T: XSI, XSI2_T: XSI2, XSI3_T: XSI3,
                    URN_T: URN}
    NSMAP_R     = invertDict(NSMAP)

    STMAP       = {'1999': (XSD_T, XSI_T), '2000': (XSD2_T, XSI2_T),
                    '2001': (XSD3_T, XSI3_T)}
    STMAP_R     = invertDict(STMAP)

    def __init__(self):
        raise Error, "Don't instantiate this"




########NEW FILE########
__FILENAME__ = Parser
# SOAPpy modules
from Config    import Config
from Types     import *
from NS        import NS
from Utilities import *

import string
import fpconst
import xml.sax
from wstools.XMLname import fromXMLname

try: from M2Crypto import SSL
except: pass

ident = '$Id: Parser.py 1497 2010-03-08 06:06:52Z pooryorick $'
from version import __version__


################################################################################
# SOAP Parser
################################################################################
class RefHolder:
    def __init__(self, name, frame):
        self.name = name
        self.parent = frame
        self.pos = len(frame)
        self.subpos = frame.namecounts.get(name, 0)

    def __repr__(self):
        return "<%s %s at %d>" % (self.__class__, self.name, id(self))

    def __str__(self):
        return "<%s %s at %d>" % (self.__class__, self.name, id(self))

class SOAPParser(xml.sax.handler.ContentHandler):
    class Frame:
        def __init__(self, name, kind = None, attrs = {}, rules = {}):
            self.name = name
            self.kind = kind
            self.attrs = attrs
            self.rules = rules

            self.contents = []
            self.names = []
            self.namecounts = {}
            self.subattrs = []

        def append(self, name, data, attrs):
            self.names.append(name)
            self.contents.append(data)
            self.subattrs.append(attrs)

            if self.namecounts.has_key(name):
                self.namecounts[name] += 1
            else:
                self.namecounts[name] = 1

        def _placeItem(self, name, value, pos, subpos = 0, attrs = None):
            self.contents[pos] = value

            if attrs:
                self.attrs.update(attrs)

        def __len__(self):
            return len(self.contents)

        def __repr__(self):
            return "<%s %s at %d>" % (self.__class__, self.name, id(self))

    def __init__(self, rules = None):
        xml.sax.handler.ContentHandler.__init__(self)
        self.body       = None
        self.header     = None
        self.attrs      = {}
        self._data      = None
        self._next      = "E" # Keeping state for message validity
        self._stack     = [self.Frame('SOAP')]

        # Make two dictionaries to store the prefix <-> URI mappings, and
        # initialize them with the default
        self._prem      = {NS.XML_T: NS.XML}
        self._prem_r    = {NS.XML: NS.XML_T}
        self._ids       = {}
        self._refs      = {}
        self._rules    = rules

    def startElementNS(self, name, qname, attrs):

        def toStr( name ):
            prefix = name[0]
            tag    = name[1]
            if self._prem_r.has_key(prefix):
               tag = self._prem_r[name[0]] + ':' + name[1]
            elif prefix:
               tag = prefix + ":" + tag
            return tag
        
        # Workaround two sax bugs
        if name[0] == None and name[1][0] == ' ':
            name = (None, name[1][1:])
        else:
            name = tuple(name)

        # First some checking of the layout of the message

        if self._next == "E":
            if name[1] != 'Envelope':
                raise Error, "expected `SOAP-ENV:Envelope', " \
                    "got `%s'" % toStr( name )
            if name[0] != NS.ENV:
                raise faultType, ("%s:VersionMismatch" % NS.ENV_T,
                    "Don't understand version `%s' Envelope" % name[0])
            else:
                self._next = "HorB"
        elif self._next == "HorB":
            if name[0] == NS.ENV and name[1] in ("Header", "Body"):
                self._next = None
            else:
                raise Error, \
                    "expected `SOAP-ENV:Header' or `SOAP-ENV:Body', " \
                    "got `%s'" % toStr( name )
        elif self._next == "B":
            if name == (NS.ENV, "Body"):
                self._next = None
            else:
                raise Error, "expected `SOAP-ENV:Body', " \
                      "got `%s'" % toStr( name )
        elif self._next == "":
            raise Error, "expected nothing, " \
                  "got `%s'" % toStr( name )
                  

        if len(self._stack) == 2:
            rules = self._rules
        else:
            try:
                rules = self._stack[-1].rules[name[1]]
            except:
                rules = None

        if type(rules) not in (NoneType, DictType):
            kind = rules
        else:
            kind = attrs.get((NS.ENC, 'arrayType'))

            if kind != None:
                del attrs._attrs[(NS.ENC, 'arrayType')]

                i = kind.find(':')
                if i >= 0:
                    try:
                        kind = (self._prem[kind[:i]], kind[i + 1:])
                    except:
                        kind = None
                else:
                    kind = None

        self.pushFrame(self.Frame(name[1], kind, attrs._attrs, rules))

        self._data = [] # Start accumulating

    def pushFrame(self, frame):
        self._stack.append(frame)

    def popFrame(self):
        return self._stack.pop()

    def endElementNS(self, name, qname):
        # Workaround two sax bugs
        if name[0] == None and name[1][0] == ' ':
            ns, name = None, name[1][1:]
        else:
            ns, name = tuple(name)

        name = fromXMLname(name) # convert to SOAP 1.2 XML name encoding

        if self._next == "E":
            raise Error, "didn't get SOAP-ENV:Envelope"
        if self._next in ("HorB", "B"):
            raise Error, "didn't get SOAP-ENV:Body"

        cur = self.popFrame()
        attrs = cur.attrs

        idval = None

        if attrs.has_key((None, 'id')):
            idval = attrs[(None, 'id')]

            if self._ids.has_key(idval):
                raise Error, "duplicate id `%s'" % idval

            del attrs[(None, 'id')]

        root = 1

        if len(self._stack) == 3:
            if attrs.has_key((NS.ENC, 'root')):
                root = int(attrs[(NS.ENC, 'root')])

                # Do some preliminary checks. First, if root="0" is present,
                # the element must have an id. Next, if root="n" is present,
                # n something other than 0 or 1, raise an exception.

                if root == 0:
                    if idval == None:
                        raise Error, "non-root element must have an id"
                elif root != 1:
                    raise Error, "SOAP-ENC:root must be `0' or `1'"

                del attrs[(NS.ENC, 'root')]

        while 1:
            href = attrs.get((None, 'href'))
            if href:
                if href[0] != '#':
                    raise Error, "Non-local hrefs are not yet suppported."
                if self._data != None and \
                   string.join(self._data, "").strip() != '':
                    raise Error, "hrefs can't have data"

                href = href[1:]

                if self._ids.has_key(href):
                    data = self._ids[href]
                else:
                    data = RefHolder(name, self._stack[-1])

                    if self._refs.has_key(href):
                        self._refs[href].append(data)
                    else:
                        self._refs[href] = [data]

                del attrs[(None, 'href')]

                break

            kind = None

            if attrs:
                for i in NS.XSI_L:
                    if attrs.has_key((i, 'type')):
                        kind = attrs[(i, 'type')]
                        del attrs[(i, 'type')]

                if kind != None:
                    i = kind.find(':')
                    if i >= 0:
                        try:
                            kind = (self._prem[kind[:i]], kind[i + 1:])
                        except:
                            kind = (None, kind)
                    else:
# XXX What to do here? (None, kind) is just going to fail in convertType
                        #print "Kind with no NS:", kind
                        kind = (None, kind)

            null = 0

            if attrs:
                for i in (NS.XSI, NS.XSI2):
                    if attrs.has_key((i, 'null')):
                        null = attrs[(i, 'null')]
                        del attrs[(i, 'null')]

                if attrs.has_key((NS.XSI3, 'nil')):
                    null = attrs[(NS.XSI3, 'nil')]
                    del attrs[(NS.XSI3, 'nil')]


                ## Check for nil

                # check for nil='true'
                if type(null) in (StringType, UnicodeType):
                    if null.lower() == 'true':
                        null = 1

                # check for nil=1, but watch out for string values
                try:                
                    null = int(null)
                except ValueError, e:
                    if not e[0].startswith("invalid literal for int()"):
                        raise e
                    null = 0

                if null:
                    if len(cur) or \
                        (self._data != None and string.join(self._data, "").strip() != ''):
                        raise Error, "nils can't have data"

                    data = None

                    break

            if len(self._stack) == 2:
                if (ns, name) == (NS.ENV, "Header"):
                    self.header = data = headerType(attrs = attrs)
                    self._next = "B"
                    break
                elif (ns, name) == (NS.ENV, "Body"):
                    self.body = data = bodyType(attrs = attrs)
                    self._next = ""
                    break
            elif len(self._stack) == 3 and self._next == None:
                if (ns, name) == (NS.ENV, "Fault"):
                    data = faultType()
                    self._next = None # allow followons
                    break

            #print "\n"
            #print "data=", self._data
            #print "kind=", kind
            #print "cur.kind=", cur.kind
            #print "cur.rules=", cur.rules
            #print "\n"
                        

            if cur.rules != None:
                rule = cur.rules

                if type(rule) in (StringType, UnicodeType):
                    rule = (None, rule) # none flags special handling
                elif type(rule) == ListType:
                    rule = tuple(rule)

                #print "kind=",kind
                #print "rule=",rule


# XXX What if rule != kind?
                if callable(rule):
                    data = rule(string.join(self._data, ""))
                elif type(rule) == DictType:
                    data = structType(name = (ns, name), attrs = attrs)
                elif rule[1][:9] == 'arrayType':
                    data = self.convertType(cur.contents,
                                            rule, attrs)
                else:
                    data = self.convertType(string.join(self._data, ""),
                                            rule, attrs)

                break

            #print "No rules, using kind or cur.kind..."

            if (kind == None and cur.kind != None) or \
                (kind == (NS.ENC, 'Array')):
                kind = cur.kind

                if kind == None:
                    kind = 'ur-type[%d]' % len(cur)
                else:
                    kind = kind[1]

                if len(cur.namecounts) == 1:
                    elemsname = cur.names[0]
                else:
                    elemsname = None

                data = self.startArray((ns, name), kind, attrs, elemsname)

                break

            if len(self._stack) == 3 and kind == None and \
                len(cur) == 0 and \
                (self._data == None or string.join(self._data, "").strip() == ''):
                data = structType(name = (ns, name), attrs = attrs)
                break

            if len(cur) == 0 and ns != NS.URN:
                # Nothing's been added to the current frame so it must be a
                # simple type.

#                 print "cur:", cur
#                 print "ns:", ns
#                 print "attrs:", attrs
#                 print "kind:", kind
                

                if kind == None:
                    # If the current item's container is an array, it will
                    # have a kind. If so, get the bit before the first [,
                    # which is the type of the array, therefore the type of
                    # the current item.

                    kind = self._stack[-1].kind

                    if kind != None:
                        i = kind[1].find('[')
                        if i >= 0:
                            kind = (kind[0], kind[1][:i])
                    elif ns != None:
                        kind = (ns, name)

                if kind != None:
                    try:
                        data = self.convertType(string.join(self._data, ""),
                                                kind, attrs)
                    except UnknownTypeError:
                        data = None
                else:
                    data = None

                if data == None:
                    if self._data == None:
                        data = ''
                    else:
                        data = string.join(self._data, "")

                    if len(attrs) == 0:
                        try: data = str(data)
                        except: pass

                break

            data = structType(name = (ns, name), attrs = attrs)

            break

        if isinstance(data, compoundType):
            for i in range(len(cur)):
                v = cur.contents[i]
                data._addItem(cur.names[i], v, cur.subattrs[i])

                if isinstance(v, RefHolder):
                    v.parent = data

        if root:
            self._stack[-1].append(name, data, attrs)

        if idval != None:
            self._ids[idval] = data

            if self._refs.has_key(idval):
                for i in self._refs[idval]:
                    i.parent._placeItem(i.name, data, i.pos, i.subpos, attrs)

                del self._refs[idval]

        self.attrs[id(data)] = attrs

        if isinstance(data, anyType):
            data._setAttrs(attrs)

        self._data = None       # Stop accumulating

    def endDocument(self):
        if len(self._refs) == 1:
            raise Error, \
                "unresolved reference " + self._refs.keys()[0]
        elif len(self._refs) > 1:
            raise Error, \
                "unresolved references " + ', '.join(self._refs.keys())

    def startPrefixMapping(self, prefix, uri):
        self._prem[prefix] = uri
        self._prem_r[uri] = prefix

    def endPrefixMapping(self, prefix):
        try:
            del self._prem_r[self._prem[prefix]]
            del self._prem[prefix]
        except:
            pass

    def characters(self, c):
        if self._data != None:
            self._data.append(c)

    arrayre = '^(?:(?P<ns>[^:]*):)?' \
        '(?P<type>[^[]+)' \
        '(?:\[(?P<rank>,*)\])?' \
        '(?:\[(?P<asize>\d+(?:,\d+)*)?\])$'

    def startArray(self, name, kind, attrs, elemsname):
        if type(self.arrayre) == StringType:
            self.arrayre = re.compile (self.arrayre)

        offset = attrs.get((NS.ENC, "offset"))

        if offset != None:
            del attrs[(NS.ENC, "offset")]

            try:
                if offset[0] == '[' and offset[-1] == ']':
                    offset = int(offset[1:-1])
                    if offset < 0:
                        raise Exception
                else:
                    raise Exception
            except:
                raise AttributeError, "invalid Array offset"
        else:
            offset = 0

        try:
            m = self.arrayre.search(kind)

            if m == None:
                raise Exception

            t = m.group('type')

            if t == 'ur-type':
                return arrayType(None, name, attrs, offset, m.group('rank'),
                    m.group('asize'), elemsname)
            elif m.group('ns') != None:
                return typedArrayType(None, name,
                    (self._prem[m.group('ns')], t), attrs, offset,
                    m.group('rank'), m.group('asize'), elemsname)
            else:
                return typedArrayType(None, name, (None, t), attrs, offset,
                    m.group('rank'), m.group('asize'), elemsname)
        except:
            raise AttributeError, "invalid Array type `%s'" % kind

    # Conversion

    class DATETIMECONSTS:
        SIGNre = '(?P<sign>-?)'
        CENTURYre = '(?P<century>\d{2,})'
        YEARre = '(?P<year>\d{2})'
        MONTHre = '(?P<month>\d{2})'
        DAYre = '(?P<day>\d{2})'
        HOURre = '(?P<hour>\d{2})'
        MINUTEre = '(?P<minute>\d{2})'
        SECONDre = '(?P<second>\d{2}(?:\.\d*)?)'
        TIMEZONEre = '(?P<zulu>Z)|(?P<tzsign>[-+])(?P<tzhour>\d{2}):' \
            '(?P<tzminute>\d{2})'
        BOSre = '^\s*'
        EOSre = '\s*$'

        __allres = {'sign': SIGNre, 'century': CENTURYre, 'year': YEARre,
            'month': MONTHre, 'day': DAYre, 'hour': HOURre,
            'minute': MINUTEre, 'second': SECONDre, 'timezone': TIMEZONEre,
            'b': BOSre, 'e': EOSre}

        dateTime = '%(b)s%(sign)s%(century)s%(year)s-%(month)s-%(day)sT' \
            '%(hour)s:%(minute)s:%(second)s(%(timezone)s)?%(e)s' % __allres
        timeInstant = dateTime
        timePeriod = dateTime
        time = '%(b)s%(hour)s:%(minute)s:%(second)s(%(timezone)s)?%(e)s' % \
            __allres
        date = '%(b)s%(sign)s%(century)s%(year)s-%(month)s-%(day)s' \
            '(%(timezone)s)?%(e)s' % __allres
        century = '%(b)s%(sign)s%(century)s(%(timezone)s)?%(e)s' % __allres
        gYearMonth = '%(b)s%(sign)s%(century)s%(year)s-%(month)s' \
            '(%(timezone)s)?%(e)s' % __allres
        gYear = '%(b)s%(sign)s%(century)s%(year)s(%(timezone)s)?%(e)s' % \
            __allres
        year = gYear
        gMonthDay = '%(b)s--%(month)s-%(day)s(%(timezone)s)?%(e)s' % __allres
        recurringDate = gMonthDay
        gDay = '%(b)s---%(day)s(%(timezone)s)?%(e)s' % __allres
        recurringDay = gDay
        gMonth = '%(b)s--%(month)s--(%(timezone)s)?%(e)s' % __allres
        month = gMonth

        recurringInstant = '%(b)s%(sign)s(%(century)s|-)(%(year)s|-)-' \
            '(%(month)s|-)-(%(day)s|-)T' \
            '(%(hour)s|-):(%(minute)s|-):(%(second)s|-)' \
            '(%(timezone)s)?%(e)s' % __allres

        duration = '%(b)s%(sign)sP' \
            '((?P<year>\d+)Y)?' \
            '((?P<month>\d+)M)?' \
            '((?P<day>\d+)D)?' \
            '((?P<sep>T)' \
            '((?P<hour>\d+)H)?' \
            '((?P<minute>\d+)M)?' \
            '((?P<second>\d*(?:\.\d*)?)S)?)?%(e)s' % \
            __allres

        timeDuration = duration

        # The extra 31 on the front is:
        # - so the tuple is 1-based
        # - so months[month-1] is December's days if month is 1

        months = (31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

    def convertDateTime(self, value, kind):
        def getZoneOffset(d):
            zoffs = 0

            try:
                if d['zulu'] == None:
                    zoffs = 60 * int(d['tzhour']) + int(d['tzminute'])
                    if d['tzsign'] != '-':
                        zoffs = -zoffs
            except TypeError:
                pass

            return zoffs

        def applyZoneOffset(months, zoffs, date, minfield, posday = 1):
            if zoffs == 0 and (minfield > 4 or 0 <= date[5] < 60):
                return date

            if minfield > 5: date[5] = 0
            if minfield > 4: date[4] = 0

            if date[5] < 0:
                date[4] += int(date[5]) / 60
                date[5] %= 60

            date[4] += zoffs

            if minfield > 3 or 0 <= date[4] < 60: return date

            date[3] += date[4] / 60
            date[4] %= 60

            if minfield > 2 or 0 <= date[3] < 24: return date

            date[2] += date[3] / 24
            date[3] %= 24

            if minfield > 1:
                if posday and date[2] <= 0:
                    date[2] += 31       # zoffs is at most 99:59, so the
                                        # day will never be less than -3
                return date

            while 1:
                # The date[1] == 3 (instead of == 2) is because we're
                # going back a month, so we need to know if the previous
                # month is February, so we test if this month is March.

                leap = minfield == 0 and date[1] == 3 and \
                    date[0] % 4 == 0 and \
                    (date[0] % 100 != 0 or date[0] % 400 == 0)

                if 0 < date[2] <= months[date[1]] + leap: break

                date[2] += months[date[1] - 1] + leap

                date[1] -= 1

                if date[1] > 0: break

                date[1] = 12

                if minfield > 0: break

                date[0] -= 1

            return date

        try:
            exp = getattr(self.DATETIMECONSTS, kind)
        except AttributeError:
            return None

        if type(exp) == StringType:
            exp = re.compile(exp)
            setattr (self.DATETIMECONSTS, kind, exp)

        m = exp.search(value)

        try:
            if m == None:
                raise Exception

            d = m.groupdict()
            f = ('century', 'year', 'month', 'day',
                'hour', 'minute', 'second')
            fn = len(f)         # Index of first non-None value
            r = []

            if kind in ('duration', 'timeDuration'):
                if d['sep'] != None and d['hour'] == None and \
                    d['minute'] == None and d['second'] == None:
                    raise Exception

                f = f[1:]

                for i in range(len(f)):
                    s = d[f[i]]

                    if s != None:
                        if f[i] == 'second':
                            s = float(s)
                        else:
                            try: s = int(s)
                            except ValueError: s = long(s)

                        if i < fn: fn = i

                    r.append(s)

                if fn > len(r):         # Any non-Nones?
                    raise Exception

                if d['sign'] == '-':
                    r[fn] = -r[fn]

                return tuple(r)

            if kind == 'recurringInstant':
                for i in range(len(f)):
                    s = d[f[i]]

                    if s == None or s == '-':
                        if i > fn:
                            raise Exception
                        s = None
                    else:
                        if i < fn:
                            fn = i

                        if f[i] == 'second':
                            s = float(s)
                        else:
                            try:
                                s = int(s)
                            except ValueError:
                                s = long(s)

                    r.append(s)

                s = r.pop(0)

                if fn == 0:
                    r[0] += s * 100
                else:
                    fn -= 1

                if fn < len(r) and d['sign'] == '-':
                    r[fn] = -r[fn]

                cleanDate(r, fn)

                return tuple(applyZoneOffset(self.DATETIMECONSTS.months,
                    getZoneOffset(d), r, fn, 0))

            r = [0, 0, 1, 1, 0, 0, 0]

            for i in range(len(f)):
                field = f[i]

                s = d.get(field)

                if s != None:
                    if field == 'second':
                        s = float(s)
                    else:
                        try:
                            s = int(s)
                        except ValueError:
                            s = long(s)

                    if i < fn:
                        fn = i

                    r[i] = s

            if fn > len(r):     # Any non-Nones?
                raise Exception

            s = r.pop(0)

            if fn == 0:
                r[0] += s * 100
            else:
                fn -= 1

            if d.get('sign') == '-':
                r[fn] = -r[fn]

            cleanDate(r, fn)

            zoffs = getZoneOffset(d)

            if zoffs:
                r = applyZoneOffset(self.DATETIMECONSTS.months, zoffs, r, fn)

            if kind == 'century':
                return r[0] / 100

            s = []

            for i in range(1, len(f)):
                if d.has_key(f[i]):
                    s.append(r[i - 1])

            if len(s) == 1:
                return s[0]
            return tuple(s)
        except Exception, e:
            raise Error, "invalid %s value `%s' - %s" % (kind, value, e)

    intlimits = \
    {
        'nonPositiveInteger':   (0, None, 0),
        'non-positive-integer': (0, None, 0),
        'negativeInteger':      (0, None, -1),
        'negative-integer':     (0, None, -1),
        'long':                 (1, -9223372036854775808L,
                                    9223372036854775807L),
        'int':                  (0, -2147483648L, 2147483647L),
        'short':                (0, -32768, 32767),
        'byte':                 (0, -128, 127),
        'nonNegativeInteger':   (0, 0, None),
        'non-negative-integer': (0, 0, None),
        'positiveInteger':      (0, 1, None),
        'positive-integer':     (0, 1, None),
        'unsignedLong':         (1, 0, 18446744073709551615L),
        'unsignedInt':          (0, 0, 4294967295L),
        'unsignedShort':        (0, 0, 65535),
        'unsignedByte':         (0, 0, 255),
    }
    floatlimits = \
    {
        'float':        (7.0064923216240861E-46, -3.4028234663852886E+38,
                         3.4028234663852886E+38),
        'double':       (2.4703282292062327E-324, -1.7976931348623158E+308,
                         1.7976931348623157E+308),
    }
    zerofloatre = '[1-9]'


    def convertType(self, d, t, attrs, config=Config):
        if t[0] is None and t[1] is not None:
            type = t[1].strip()
            if type[:9] == 'arrayType':
                index_eq = type.find('=')
                index_obr = type.find('[')
                index_cbr = type.find(']')
                elemtype = type[index_eq+1:index_obr]
                elemnum  = type[index_obr+1:index_cbr]
                if elemtype=="ur-type":
                    return(d)
                else:
                    newarr = map( lambda(di):
                                  self.convertToBasicTypes(d=di,
                                                       t = ( NS.XSD, elemtype),
                                                       attrs=attrs,
                                                       config=config),
                                  d)
                    return newarr
            else:
                t = (NS.XSD, t[1])

        return self.convertToBasicTypes(d, t, attrs, config)


    def convertToSOAPpyTypes(self, d, t, attrs, config=Config):
        pass


    def convertToBasicTypes(self, d, t, attrs, config=Config):
        dnn = d or ''

        #if Config.debug:
            #print "convertToBasicTypes:"
            #print "   requested_type=", t
            #print "   data=", d


#         print "convertToBasicTypes:"
#         print "   requested_type=", t
#         print "   data=", d
#         print "   attrs=", attrs
#         print "   t[0]=", t[0]
#         print "   t[1]=", t[1]
            
#         print "   in?", t[0] in NS.EXSD_L

        if t[0] in NS.EXSD_L:
            if t[1]=="integer": # unbounded integer type
                try:
                    d = int(d)
                    if len(attrs):
                        d = long(d)
                except:
                    d = long(d)
                return d
            if self.intlimits.has_key (t[1]): # range-bounded integer types
                l = self.intlimits[t[1]]
                try: d = int(d)
                except: d = long(d)

                if l[1] != None and d < l[1]:
                    raise UnderflowError, "%s too small" % d
                if l[2] != None and d > l[2]:
                    raise OverflowError, "%s too large" % d

                if l[0] or len(attrs):
                    return long(d)
                return d
            if t[1] == "string":
                if len(attrs):
                    return unicode(dnn)
                try:
                    return str(dnn)
                except:
                    return dnn
            if t[1] in ("bool", "boolean"):
                d = d.strip().lower()
                if d in ('0', 'false'):
                    return False
                if d in ('1', 'true'):
                    return True
                raise AttributeError, "invalid boolean value"
            if t[1] in ('double','float'):
                l = self.floatlimits[t[1]]
                s = d.strip().lower()

                # Explicitly check for NaN and Infinities
                if s == "nan":
                    d = fpconst.NaN
                elif s[0:2]=="inf" or s[0:3]=="+inf":
                    d = fpconst.PosInf
                elif s[0:3] == "-inf":
                    d = fpconst.NegInf
                else :
                    d = float(s)

                if config.strict_range:
                    if fpconst.isNaN(d):
                        if s[0:2] != 'nan':
                            raise ValueError, "invalid %s: %s" % (t[1], s)
                    elif fpconst.isNegInf(d):
                        if s[0:3] != '-inf':
                            raise UnderflowError, "%s too small: %s" % (t[1], s)
                    elif fpconst.isPosInf(d):
                        if s[0:2] != 'inf' and s[0:3] != '+inf':
                            raise OverflowError, "%s too large: %s" % (t[1], s)
                    elif d < 0 and d < l[1]:
                            raise UnderflowError, "%s too small: %s" % (t[1], s)
                    elif d > 0 and ( d < l[0] or d > l[2] ):
                            raise OverflowError, "%s too large: %s" % (t[1], s)
                    elif d == 0:
                        if type(self.zerofloatre) == StringType:
                            self.zerofloatre = re.compile(self.zerofloatre)
    
                        if self.zerofloatre.search(s):
                            raise UnderflowError, "invalid %s: %s" % (t[1], s)
                return d
            
            if t[1] in ("dateTime", "date", "timeInstant", "time"):
                return self.convertDateTime(d, t[1])
            if t[1] == "decimal":
                return float(d)
            if t[1] in ("language", "QName", "NOTATION", "NMTOKEN", "Name",
                "NCName", "ID", "IDREF", "ENTITY"):
                return collapseWhiteSpace(d)
            if t[1] in ("IDREFS", "ENTITIES", "NMTOKENS"):
                d = collapseWhiteSpace(d)
                return d.split()
        if t[0] in NS.XSD_L:
            if t[1] in ("base64", "base64Binary"):
                if d:
                    return base64.decodestring(d)
                else:
                    return ''
            if t[1] == "hexBinary":
                if d:
                    return decodeHexString(d)
                else:
                    return
            if t[1] == "anyURI":
                return urllib.unquote(collapseWhiteSpace(d))
            if t[1] in ("normalizedString", "token"):
                return collapseWhiteSpace(d)
        if t[0] == NS.ENC:
            if t[1] == "base64":
                if d:
                    return base64.decodestring(d)
                else:
                    return ''
        if t[0] == NS.XSD:
            if t[1] == "binary":
                try:
                    e = attrs[(None, 'encoding')]

                    if d:
                        if e == 'hex':
                            return decodeHexString(d)
                        elif e == 'base64':
                            return base64.decodestring(d)
                    else:
                        return ''
                except:
                    pass

                raise Error, "unknown or missing binary encoding"
            if t[1] == "uri":
                return urllib.unquote(collapseWhiteSpace(d))
            if t[1] == "recurringInstant":
                return self.convertDateTime(d, t[1])
        if t[0] in (NS.XSD2, NS.ENC):
            if t[1] == "uriReference":
                return urllib.unquote(collapseWhiteSpace(d))
            if t[1] == "timePeriod":
                return self.convertDateTime(d, t[1])
            if t[1] in ("century", "year"):
                return self.convertDateTime(d, t[1])
        if t[0] in (NS.XSD, NS.XSD2, NS.ENC):
            if t[1] == "timeDuration":
                return self.convertDateTime(d, t[1])
        if t[0] == NS.XSD3:
            if t[1] == "anyURI":
                return urllib.unquote(collapseWhiteSpace(d))
            if t[1] in ("gYearMonth", "gMonthDay"):
                return self.convertDateTime(d, t[1])
            if t[1] == "gYear":
                return self.convertDateTime(d, t[1])
            if t[1] == "gMonth":
                return self.convertDateTime(d, t[1])
            if t[1] == "gDay":
                return self.convertDateTime(d, t[1])
            if t[1] == "duration":
                return self.convertDateTime(d, t[1])
        if t[0] in (NS.XSD2, NS.XSD3):
            if t[1] == "token":
                return collapseWhiteSpace(d)
            if t[1] == "recurringDate":
                return self.convertDateTime(d, t[1])
            if t[1] == "month":
                return self.convertDateTime(d, t[1])
            if t[1] == "recurringDay":
                return self.convertDateTime(d, t[1])
        if t[0] == NS.XSD2:
            if t[1] == "CDATA":
                return collapseWhiteSpace(d)

        raise UnknownTypeError, "unknown type `%s'" % (str(t[0]) + ':' + t[1])


################################################################################
# call to SOAPParser that keeps all of the info
################################################################################
def _parseSOAP(xml_str, rules = None):
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    parser = xml.sax.make_parser()
    t = SOAPParser(rules = rules)
    parser.setContentHandler(t)
    e = xml.sax.handler.ErrorHandler()
    parser.setErrorHandler(e)

    inpsrc = xml.sax.xmlreader.InputSource()
    inpsrc.setByteStream(StringIO(xml_str))

    # turn on namespace mangeling
    parser.setFeature(xml.sax.handler.feature_namespaces,1)

    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    try:
        parser.parse(inpsrc)
    except xml.sax.SAXParseException, e:
        parser._parser = None
        raise e
    
    return t

################################################################################
# SOAPParser's more public interface
################################################################################
def parseSOAP(xml_str, attrs = 0):
    t = _parseSOAP(xml_str)

    if attrs:
        return t.body, t.attrs
    return t.body


def parseSOAPRPC(xml_str, header = 0, body = 0, attrs = 0, rules = None):

    t = _parseSOAP(xml_str, rules = rules)
    p = t.body[0]

    # Empty string, for RPC this translates into a void
    if type(p) in (type(''), type(u'')) and p in ('', u''):
        name = "Response"
        for k in t.body.__dict__.keys():
            if k[0] != "_":
                name = k
        p = structType(name)
        
    if header or body or attrs:
        ret = (p,)
        if header : ret += (t.header,)
        if body: ret += (t.body,)
        if attrs: ret += (t.attrs,)
        return ret
    else:
        return p

########NEW FILE########
__FILENAME__ = Server
from __future__ import nested_scopes

"""
################################################################################
#
# SOAPpy - Cayce Ullman       (cayce@actzero.com)
#          Brian Matthews     (blm@actzero.com)
#          Gregory Warnes     (Gregory.R.Warnes@Pfizer.com)
#          Christopher Blunck (blunck@gst.com)
#
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: Server.py 1468 2008-05-24 01:55:33Z warnes $'
from version import __version__

#import xml.sax
import socket
import sys
import SocketServer
from types import *
import BaseHTTPServer
import thread

# SOAPpy modules
from Parser      import parseSOAPRPC
from Config      import Config
from Types       import faultType, voidType, simplify
from NS          import NS
from SOAPBuilder import buildSOAP
from Utilities   import debugHeader, debugFooter

try: from M2Crypto import SSL
except: pass

ident = '$Id: Server.py 1468 2008-05-24 01:55:33Z warnes $'

from version import __version__

################################################################################
# Call context dictionary
################################################################################

_contexts = dict()

def GetSOAPContext():
    global _contexts
    return _contexts[thread.get_ident()]

################################################################################
# Server
################################################################################

# Method Signature class for adding extra info to registered funcs, right now
# used just to indicate it should be called with keywords, instead of ordered
# params.
class MethodSig:
    def __init__(self, func, keywords=0, context=0):
        self.func     = func
        self.keywords = keywords
        self.context  = context
        self.__name__ = func.__name__

    def __call__(self, *args, **kw):
        return apply(self.func,args,kw)

class SOAPContext:
    def __init__(self, header, body, attrs, xmldata, connection, httpheaders,
        soapaction):

        self.header     = header
        self.body       = body
        self.attrs      = attrs
        self.xmldata    = xmldata
        self.connection = connection
        self.httpheaders= httpheaders
        self.soapaction = soapaction

# A class to describe how header messages are handled
class HeaderHandler:
    # Initially fail out if there are any problems.
    def __init__(self, header, attrs):
        for i in header.__dict__.keys():
            if i[0] == "_":
                continue

            d = getattr(header, i)

            try:
                fault = int(attrs[id(d)][(NS.ENV, 'mustUnderstand')])
            except:
                fault = 0

            if fault:
                raise faultType, ("%s:MustUnderstand" % NS.ENV_T,
                                  "Required Header Misunderstood",
                                  "%s" % i)

################################################################################
# SOAP Server
################################################################################
class SOAPServerBase:

    def get_request(self):
        sock, addr = SocketServer.TCPServer.get_request(self)

        if self.ssl_context:
            sock = SSL.Connection(self.ssl_context, sock)
            sock._setup_ssl(addr)
            if sock.accept_ssl() != 1:
                raise socket.error, "Couldn't accept SSL connection"

        return sock, addr

    def registerObject(self, object, namespace = '', path = ''):
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]
        self.objmap[namespace] = object

    def registerFunction(self, function, namespace = '', funcName = None,
                         path = ''):
        if not funcName : funcName = function.__name__
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]
        if self.funcmap.has_key(namespace):
            self.funcmap[namespace][funcName] = function
        else:
            self.funcmap[namespace] = {funcName : function}

    def registerKWObject(self, object, namespace = '', path = ''):
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]
        for i in dir(object.__class__):
            if i[0] != "_" and callable(getattr(object, i)):
                self.registerKWFunction(getattr(object,i), namespace)

    # convenience  - wraps your func for you.
    def registerKWFunction(self, function, namespace = '', funcName = None,
                           path = ''):
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]
        self.registerFunction(MethodSig(function,keywords=1), namespace,
        funcName)

    def unregisterObject(self, object, namespace = '', path = ''):
        if namespace == '' and path == '': namespace = self.namespace
        if namespace == '' and path != '':
            namespace = path.replace("/", ":")
            if namespace[0] == ":": namespace = namespace[1:]

        del self.objmap[namespace]
        
class SOAPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def version_string(self):
        return '<a href="http://pywebsvcs.sf.net">' + \
            'SOAPpy ' + __version__ + '</a> (Python ' + \
            sys.version.split()[0] + ')'

    def date_time_string(self):
        self.__last_date_time_string = \
            BaseHTTPServer.BaseHTTPRequestHandler.\
            date_time_string(self)

        return self.__last_date_time_string

    def do_POST(self):
        global _contexts
        
        status = 500
        try:
            if self.server.config.dumpHeadersIn:
                s = 'Incoming HTTP headers'
                debugHeader(s)
                print self.raw_requestline.strip()
                print "\n".join(map (lambda x: x.strip(),
                    self.headers.headers))
                debugFooter(s)

            data = self.rfile.read(int(self.headers["Content-length"]))

            if self.server.config.dumpSOAPIn:
                s = 'Incoming SOAP'
                debugHeader(s)
                print data,
                if data[-1] != '\n':
                    print
                debugFooter(s)

            (r, header, body, attrs) = \
                parseSOAPRPC(data, header = 1, body = 1, attrs = 1)

            method = r._name
            args   = r._aslist()
            kw     = r._asdict()

            if Config.simplify_objects:
                args = simplify(args)
                kw = simplify(kw)

            # Handle mixed named and unnamed arguments by assuming
            # that all arguments with names of the form "v[0-9]+"
            # are unnamed and should be passed in numeric order,
            # other arguments are named and should be passed using
            # this name.

            # This is a non-standard exension to the SOAP protocol,
            # but is supported by Apache AXIS.

            # It is enabled by default.  To disable, set
            # Config.specialArgs to False.


            ordered_args = {}
            named_args   = {}

            if Config.specialArgs: 
                
                for (k,v) in  kw.items():

                    if k[0]=="v":
                        try:
                            i = int(k[1:])
                            ordered_args[i] = v
                        except ValueError:
                            named_args[str(k)] = v

                    else:
                        named_args[str(k)] = v

            # We have to decide namespace precedence
            # I'm happy with the following scenario
            # if r._ns is specified use it, if not check for
            # a path, if it's specified convert it and use it as the
            # namespace. If both are specified, use r._ns.
            
            ns = r._ns

            if len(self.path) > 1 and not ns:
                ns = self.path.replace("/", ":")
                if ns[0] == ":": ns = ns[1:]
            
            # authorization method
            a = None

            keylist = ordered_args.keys()
            keylist.sort()

            # create list in proper order w/o names
            tmp = map( lambda x: ordered_args[x], keylist)
            ordered_args = tmp

            #print '<-> Argument Matching Yielded:'
            #print '<-> Ordered Arguments:' + str(ordered_args)
            #print '<-> Named Arguments  :' + str(named_args)
             
            resp = ""
            
            # For fault messages
            if ns:
                nsmethod = "%s:%s" % (ns, method)
            else:
                nsmethod = method

            try:
                # First look for registered functions
                if self.server.funcmap.has_key(ns) and \
                    self.server.funcmap[ns].has_key(method):
                    f = self.server.funcmap[ns][method]

                    # look for the authorization method
                    if self.server.config.authMethod != None:
                        authmethod = self.server.config.authMethod
                        if self.server.funcmap.has_key(ns) and \
                               self.server.funcmap[ns].has_key(authmethod):
                            a = self.server.funcmap[ns][authmethod]
                else:
                    # Now look at registered objects
                    # Check for nested attributes. This works even if
                    # there are none, because the split will return
                    # [method]
                    f = self.server.objmap[ns]
                    
                    # Look for the authorization method
                    if self.server.config.authMethod != None:
                        authmethod = self.server.config.authMethod
                        if hasattr(f, authmethod):
                            a = getattr(f, authmethod)

                    # then continue looking for the method
                    l = method.split(".")
                    for i in l:
                        f = getattr(f, i)
            except:
                info = sys.exc_info()
                try:
                    resp = buildSOAP(faultType("%s:Client" % NS.ENV_T,
                                               "Method Not Found",
                                               "%s : %s %s %s" % (nsmethod,
                                                                  info[0],
                                                                  info[1],
                                                                  info[2])),
                                     encoding = self.server.encoding,
                                     config = self.server.config)
                finally:
                    del info
                status = 500
            else:
                try:
                    if header:
                        x = HeaderHandler(header, attrs)

                    fr = 1

                    # call context book keeping
                    # We're stuffing the method into the soapaction if there
                    # isn't one, someday, we'll set that on the client
                    # and it won't be necessary here
                    # for now we're doing both

                    if "SOAPAction".lower() not in self.headers.keys() or \
                       self.headers["SOAPAction"] == "\"\"":
                        self.headers["SOAPAction"] = method
                        
                    thread_id = thread.get_ident()
                    _contexts[thread_id] = SOAPContext(header, body,
                                                       attrs, data,
                                                       self.connection,
                                                       self.headers,
                                                       self.headers["SOAPAction"])

                    # Do an authorization check
                    if a != None:
                        if not apply(a, (), {"_SOAPContext" :
                                             _contexts[thread_id] }):
                            raise faultType("%s:Server" % NS.ENV_T,
                                            "Authorization failed.",
                                            "%s" % nsmethod)
                    
                    # If it's wrapped, some special action may be needed
                    if isinstance(f, MethodSig):
                        c = None
                    
                        if f.context:  # retrieve context object
                            c = _contexts[thread_id]

                        if Config.specialArgs:
                            if c:
                                named_args["_SOAPContext"] = c
                            fr = apply(f, ordered_args, named_args)
                        elif f.keywords:
                            # This is lame, but have to de-unicode
                            # keywords
                            
                            strkw = {}
                            
                            for (k, v) in kw.items():
                                strkw[str(k)] = v
                            if c:
                                strkw["_SOAPContext"] = c
                            fr = apply(f, (), strkw)
                        elif c:
                            fr = apply(f, args, {'_SOAPContext':c})
                        else:
                            fr = apply(f, args, {})

                    else:
                        if Config.specialArgs:
                            fr = apply(f, ordered_args, named_args)
                        else:
                            fr = apply(f, args, {})

                    
                    if type(fr) == type(self) and \
                        isinstance(fr, voidType):
                        resp = buildSOAP(kw = {'%sResponse' % method: fr},
                            encoding = self.server.encoding,
                            config = self.server.config)
                    else:
                        resp = buildSOAP(kw =
                            {'%sResponse' % method: {'Result': fr}},
                            encoding = self.server.encoding,
                            config = self.server.config)

                    # Clean up _contexts
                    if _contexts.has_key(thread_id):
                        del _contexts[thread_id]
                        
                except Exception, e:
                    import traceback
                    info = sys.exc_info()

                    try:
                        if self.server.config.dumpFaultInfo:
                            s = 'Method %s exception' % nsmethod
                            debugHeader(s)
                            traceback.print_exception(info[0], info[1],
                                                      info[2])
                            debugFooter(s)

                        if isinstance(e, faultType):
                            f = e
                        else:
                            f = faultType("%s:Server" % NS.ENV_T,
                                          "Method Failed",
                                          "%s" % nsmethod)

                        if self.server.config.returnFaultInfo:
                            f._setDetail("".join(traceback.format_exception(
                                info[0], info[1], info[2])))
                        elif not hasattr(f, 'detail'):
                            f._setDetail("%s %s" % (info[0], info[1]))
                    finally:
                        del info

                    resp = buildSOAP(f, encoding = self.server.encoding,
                       config = self.server.config)
                    status = 500
                else:
                    status = 200
        except faultType, e:
            import traceback
            info = sys.exc_info()
            try:
                if self.server.config.dumpFaultInfo:
                    s = 'Received fault exception'
                    debugHeader(s)
                    traceback.print_exception(info[0], info[1],
                        info[2])
                    debugFooter(s)

                if self.server.config.returnFaultInfo:
                    e._setDetail("".join(traceback.format_exception(
                            info[0], info[1], info[2])))
                elif not hasattr(e, 'detail'):
                    e._setDetail("%s %s" % (info[0], info[1]))
            finally:
                del info

            resp = buildSOAP(e, encoding = self.server.encoding,
                config = self.server.config)
            status = 500
        except Exception, e:
            # internal error, report as HTTP server error

            if self.server.config.dumpFaultInfo:
                s = 'Internal exception %s' % e
                import traceback
                debugHeader(s)
                info = sys.exc_info()
                try:
                    traceback.print_exception(info[0], info[1], info[2])
                finally:
                    del info

                debugFooter(s)

            self.send_response(500)
            self.end_headers()

            if self.server.config.dumpHeadersOut and \
                self.request_version != 'HTTP/0.9':
                s = 'Outgoing HTTP headers'
                debugHeader(s)
                if self.responses.has_key(status):
                    s = ' ' + self.responses[status][0]
                else:
                    s = ''
                print "%s %d%s" % (self.protocol_version, 500, s)
                print "Server:", self.version_string()
                print "Date:", self.__last_date_time_string
                debugFooter(s)
        else:
            # got a valid SOAP response
            self.send_response(status)

            t = 'text/xml';
            if self.server.encoding != None:
                t += '; charset=%s' % self.server.encoding
            self.send_header("Content-type", t)
            self.send_header("Content-length", str(len(resp)))
            self.end_headers()

            if self.server.config.dumpHeadersOut and \
                self.request_version != 'HTTP/0.9':
                s = 'Outgoing HTTP headers'
                debugHeader(s)
                if self.responses.has_key(status):
                    s = ' ' + self.responses[status][0]
                else:
                    s = ''
                print "%s %d%s" % (self.protocol_version, status, s)
                print "Server:", self.version_string()
                print "Date:", self.__last_date_time_string
                print "Content-type:", t
                print "Content-length:", len(resp)
                debugFooter(s)

            if self.server.config.dumpSOAPOut:
                s = 'Outgoing SOAP'
                debugHeader(s)
                print resp,
                if resp[-1] != '\n':
                    print
                debugFooter(s)

            self.wfile.write(resp)
            self.wfile.flush()

            # We should be able to shut down both a regular and an SSL
            # connection, but under Python 2.1, calling shutdown on an
            # SSL connections drops the output, so this work-around.
            # This should be investigated more someday.

            if self.server.config.SSLserver and \
                isinstance(self.connection, SSL.Connection):
                self.connection.set_shutdown(SSL.SSL_SENT_SHUTDOWN |
                    SSL.SSL_RECEIVED_SHUTDOWN)
            else:
                self.connection.shutdown(1)

        def do_GET(self):
            
            #print 'command        ', self.command
            #print 'path           ', self.path
            #print 'request_version', self.request_version
            #print 'headers'
            #print '   type    ', self.headers.type
            #print '   maintype', self.headers.maintype
            #print '   subtype ', self.headers.subtype
            #print '   params  ', self.headers.plist
            
            path = self.path.lower()
            if path.endswith('wsdl'):
                method = 'wsdl'
                function = namespace = None
                if self.server.funcmap.has_key(namespace) \
                        and self.server.funcmap[namespace].has_key(method):
                    function = self.server.funcmap[namespace][method]
                else: 
                    if namespace in self.server.objmap.keys():
                        function = self.server.objmap[namespace]
                        l = method.split(".")
                        for i in l:
                            function = getattr(function, i)
            
                if function:
                    self.send_response(200)
                    self.send_header("Content-type", 'text/plain')
                    self.end_headers()
                    response = apply(function, ())
                    self.wfile.write(str(response))
                    return
            
            # return error
            self.send_response(200)
            self.send_header("Content-type", 'text/html')
            self.end_headers()
            self.wfile.write('''\
<title>
<head>Error!</head>
</title>

<body>
<h1>Oops!</h1>

<p>
  This server supports HTTP GET requests only for the the purpose of
  obtaining Web Services Description Language (WSDL) for a specific
  service.

  Either you requested an URL that does not end in "wsdl" or this
  server does not implement a wsdl method.
</p>


</body>''')

            
    def log_message(self, format, *args):
        if self.server.log:
            BaseHTTPServer.BaseHTTPRequestHandler.\
                log_message (self, format, *args)



class SOAPServer(SOAPServerBase, SocketServer.TCPServer):

    def __init__(self, addr = ('localhost', 8000),
        RequestHandler = SOAPRequestHandler, log = 0, encoding = 'UTF-8',
        config = Config, namespace = None, ssl_context = None):

        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        if ssl_context != None and not config.SSLserver:
            raise AttributeError, \
                "SSL server not supported by this Python installation"

        self.namespace          = namespace
        self.objmap             = {}
        self.funcmap            = {}
        self.ssl_context        = ssl_context
        self.encoding           = encoding
        self.config             = config
        self.log                = log

        self.allow_reuse_address= 1

        SocketServer.TCPServer.__init__(self, addr, RequestHandler)


class ThreadingSOAPServer(SOAPServerBase, SocketServer.ThreadingTCPServer):

    def __init__(self, addr = ('localhost', 8000),
        RequestHandler = SOAPRequestHandler, log = 0, encoding = 'UTF-8',
        config = Config, namespace = None, ssl_context = None):

        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        if ssl_context != None and not config.SSLserver:
            raise AttributeError, \
                "SSL server not supported by this Python installation"

        self.namespace          = namespace
        self.objmap             = {}
        self.funcmap            = {}
        self.ssl_context        = ssl_context
        self.encoding           = encoding
        self.config             = config
        self.log                = log

        self.allow_reuse_address= 1

        SocketServer.ThreadingTCPServer.__init__(self, addr, RequestHandler)

# only define class if Unix domain sockets are available
if hasattr(socket, "AF_UNIX"):

    class SOAPUnixSocketServer(SOAPServerBase, SocketServer.UnixStreamServer):
    
        def __init__(self, addr = 8000,
            RequestHandler = SOAPRequestHandler, log = 0, encoding = 'UTF-8',
            config = Config, namespace = None, ssl_context = None):
    
            # Test the encoding, raising an exception if it's not known
            if encoding != None:
                ''.encode(encoding)
    
            if ssl_context != None and not config.SSLserver:
                raise AttributeError, \
                    "SSL server not supported by this Python installation"
    
            self.namespace          = namespace
            self.objmap             = {}
            self.funcmap            = {}
            self.ssl_context        = ssl_context
            self.encoding           = encoding
            self.config             = config
            self.log                = log
    
            self.allow_reuse_address= 1
    
            SocketServer.UnixStreamServer.__init__(self, str(addr), RequestHandler)
    

########NEW FILE########
__FILENAME__ = SOAP
"""This file is here for backward compatibility with versions <= 0.9.9 

Delete when 1.0.0 is released!
"""

ident = '$Id: SOAP.py 541 2004-01-31 04:20:06Z warnes $'
from version import __version__

from Client      import *
from Config      import *
from Errors      import *
from NS          import *
from Parser      import *
from SOAPBuilder import *
from Server      import *
from Types       import *
from Utilities     import *
import wstools
import WSDL

from warnings import warn

warn("""

The sub-module SOAPpy.SOAP is deprecated and is only
provided for short-term backward compatibility.  Objects are now
available directly within the SOAPpy module.  Thus, instead of

   from SOAPpy import SOAP
   ...
   SOAP.SOAPProxy(...)

use

   from SOAPpy import SOAPProxy
   ...
   SOAPProxy(...)

instead.
""", DeprecationWarning)

########NEW FILE########
__FILENAME__ = SOAPBuilder
"""
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: SOAPBuilder.py 1498 2010-03-12 02:13:19Z pooryorick $'
from version import __version__

import cgi
from wstools.XMLname import toXMLname, fromXMLname
import fpconst

# SOAPpy modules
from Config import Config
from NS     import NS
from Types  import *

# Test whether this Python version has Types.BooleanType
# If it doesn't have it, then False and True are serialized as integers
try:
    BooleanType
    pythonHasBooleanType = 1
except NameError:
    pythonHasBooleanType = 0

################################################################################
# SOAP Builder
################################################################################
class SOAPBuilder:
    _xml_top = '<?xml version="1.0"?>\n'
    _xml_enc_top = '<?xml version="1.0" encoding="%s"?>\n'
    _env_top = ( '%(ENV_T)s:Envelope\n' + \
                 '  %(ENV_T)s:encodingStyle="%(ENC)s"\n' ) % \
                 NS.__dict__
    _env_bot = '</%(ENV_T)s:Envelope>\n' % NS.__dict__

    # Namespaces potentially defined in the Envelope tag.

    _env_ns = {NS.ENC: NS.ENC_T, NS.ENV: NS.ENV_T,
        NS.XSD: NS.XSD_T, NS.XSD2: NS.XSD2_T, NS.XSD3: NS.XSD3_T,
        NS.XSI: NS.XSI_T, NS.XSI2: NS.XSI2_T, NS.XSI3: NS.XSI3_T}

    def __init__(self, args = (), kw = {}, method = None, namespace = None,
        header = None, methodattrs = None, envelope = 1, encoding = 'UTF-8',
        use_refs = 0, config = Config, noroot = 0):

        # Test the encoding, raising an exception if it's not known
        if encoding != None:
            ''.encode(encoding)

        self.args       = args
        self.kw         = kw
        self.envelope   = envelope
        self.encoding   = encoding
        self.method     = method
        self.namespace  = namespace
        self.header     = header
        self.methodattrs= methodattrs
        self.use_refs   = use_refs
        self.config     = config
        self.out        = []
        self.tcounter   = 0
        self.ncounter   = 1
        self.icounter   = 1
        self.envns      = {}
        self.ids        = {}
        self.depth      = 0
        self.multirefs  = []
        self.multis     = 0
        self.body       = not isinstance(args, bodyType)
        self.noroot     = noroot

    def build(self):
        if Config.debug: print "In build."
        ns_map = {}

        # Cache whether typing is on or not
        typed = self.config.typed

        if self.header:
            # Create a header.
            self.dump(self.header, "Header", typed = typed)
            #self.header = None # Wipe it out so no one is using it.

        if self.body:
            # Call genns to record that we've used SOAP-ENV.
            self.depth += 1
            body_ns = self.genns(ns_map, NS.ENV)[0]
            self.out.append("<%sBody>\n" % body_ns)

        if self.method:
            # Save the NS map so that it can be restored when we
            # fall out of the scope of the method definition
            save_ns_map = ns_map.copy()
            self.depth += 1
            a = ''
            if self.methodattrs:
                for (k, v) in self.methodattrs.items():
                    a += ' %s="%s"' % (k, v)

            if self.namespace:  # Use the namespace info handed to us
                methodns, n = self.genns(ns_map, self.namespace)
            else:
                methodns, n = '', ''

            self.out.append('<%s%s%s%s%s>\n' % (
                methodns, self.method, n, a, self.genroot(ns_map)))

        try:
            if type(self.args) != TupleType:
                args = (self.args,)
            else:
                args = self.args

            for i in args:
                self.dump(i, typed = typed, ns_map = ns_map)

            if hasattr(self.config, "argsOrdering") and self.config.argsOrdering.has_key(self.method):
                for k in self.config.argsOrdering.get(self.method):
                    self.dump(self.kw.get(k), k, typed = typed, ns_map = ns_map)                
            else:
                for (k, v) in self.kw.items():
                    self.dump(v, k, typed = typed, ns_map = ns_map)
                
        except RecursionError:
            if self.use_refs == 0:
                # restart
                b = SOAPBuilder(args = self.args, kw = self.kw,
                    method = self.method, namespace = self.namespace,
                    header = self.header, methodattrs = self.methodattrs,
                    envelope = self.envelope, encoding = self.encoding,
                    use_refs = 1, config = self.config)
                return b.build()
            raise

        if self.method:
            self.out.append("</%s%s>\n" % (methodns, self.method))
            # End of the method definition; drop any local namespaces
            ns_map = save_ns_map
            self.depth -= 1

        if self.body:
            # dump may add to self.multirefs, but the for loop will keep
            # going until it has used all of self.multirefs, even those
            # entries added while in the loop.

            self.multis = 1

            for obj, tag in self.multirefs:
                self.dump(obj, tag, typed = typed, ns_map = ns_map)

            self.out.append("</%sBody>\n" % body_ns)
            self.depth -= 1

        if self.envelope:
            e = map (lambda ns: '  xmlns:%s="%s"\n' % (ns[1], ns[0]),
                self.envns.items())

            self.out = ['<', self._env_top] + e + ['>\n'] + \
                       self.out + \
                       [self._env_bot]

        if self.encoding != None:
            self.out.insert(0, self._xml_enc_top % self.encoding)
            return ''.join(self.out).encode(self.encoding)

        self.out.insert(0, self._xml_top)
        return ''.join(self.out)

    def gentag(self):
        if Config.debug: print "In gentag."
        self.tcounter += 1
        return "v%d" % self.tcounter

    def genns(self, ns_map, nsURI):
        if nsURI == None:
            return ('', '')

        if type(nsURI) == TupleType: # already a tuple
            if len(nsURI) == 2:
                ns, nsURI = nsURI
            else:
                ns, nsURI = None, nsURI[0]
        else:
            ns = None

        if ns_map.has_key(nsURI):
            return (ns_map[nsURI] + ':', '')

        if self._env_ns.has_key(nsURI):
            ns = self.envns[nsURI] = ns_map[nsURI] = self._env_ns[nsURI]
            return (ns + ':', '')

        if not ns:
            ns = "ns%d" % self.ncounter
            self.ncounter += 1
        ns_map[nsURI] = ns
        if self.config.buildWithNamespacePrefix:
            return (ns + ':', ' xmlns:%s="%s"' % (ns, nsURI))
        else:
            return ('', ' xmlns="%s"' % (nsURI))

    def genroot(self, ns_map):
        if self.noroot:
            return ''

        if self.depth != 2:
            return ''

        ns, n = self.genns(ns_map, NS.ENC)
        return ' %sroot="%d"%s' % (ns, not self.multis, n)

    # checkref checks an element to see if it needs to be encoded as a
    # multi-reference element or not. If it returns None, the element has
    # been handled and the caller can continue with subsequent elements.
    # If it returns a string, the string should be included in the opening
    # tag of the marshaled element.

    def checkref(self, obj, tag, ns_map):
        if self.depth < 2:
            return ''

        if not self.ids.has_key(id(obj)):
            n = self.ids[id(obj)] = self.icounter
            self.icounter = n + 1

            if self.use_refs == 0:
                return ''

            if self.depth == 2:
                return ' id="i%d"' % n

            self.multirefs.append((obj, tag))
        else:
            if self.use_refs == 0:
                raise RecursionError, "Cannot serialize recursive object"

            n = self.ids[id(obj)]

            if self.multis and self.depth == 2:
                return ' id="i%d"' % n

        self.out.append('<%s href="#i%d"%s/>\n' %
                        (tag, n, self.genroot(ns_map)))
        return None

    # dumpers

    def dump(self, obj, tag = None, typed = 1, ns_map = {}):
        if Config.debug: print "In dump.", "obj=", obj
        ns_map = ns_map.copy()
        self.depth += 1

        if type(tag) not in (NoneType, StringType, UnicodeType):
            raise KeyError, "tag must be a string or None"

        self.dump_dispatch(obj, tag, typed, ns_map)
        self.depth -= 1

    # generic dumper
    def dumper(self, nsURI, obj_type, obj, tag, typed = 1, ns_map = {},
               rootattr = '', id = '',
               xml = '<%(tag)s%(type)s%(id)s%(attrs)s%(root)s>%(data)s</%(tag)s>\n'):
        if Config.debug: print "In dumper."

        if nsURI == None:
            nsURI = self.config.typesNamespaceURI

        tag = tag or self.gentag()

        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

        a = n = t = ''
        if typed and obj_type:
            ns, n = self.genns(ns_map, nsURI)
            ins = self.genns(ns_map, self.config.schemaNamespaceURI)[0]
            t = ' %stype="%s%s"%s' % (ins, ns, obj_type, n)

        try: a = obj._marshalAttrs(ns_map, self)
        except: pass

        try: data = obj._marshalData()
        except:
            if (obj_type != "string"): # strings are already encoded
                data = cgi.escape(str(obj))
            else:
                data = obj



        return xml % {"tag": tag, "type": t, "data": data, "root": rootattr,
            "id": id, "attrs": a}

    def dump_float(self, obj, tag, typed = 1, ns_map = {}):
        if Config.debug: print "In dump_float."
        tag = tag or self.gentag()

        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

        if Config.strict_range:
            doubleType(obj)

        if fpconst.isPosInf(obj):
            obj = "INF"
        elif fpconst.isNegInf(obj):
            obj = "-INF"
        elif fpconst.isNaN(obj):
            obj = "NaN"
        else:
            obj = repr(obj)

        # Note: python 'float' is actually a SOAP 'double'.
        self.out.append(self.dumper(
            None, "double", obj, tag, typed, ns_map, self.genroot(ns_map)))

    def dump_int(self, obj, tag, typed = 1, ns_map = {}):
        if Config.debug: print "In dump_int."
        self.out.append(self.dumper(None, 'integer', obj, tag, typed,
                                     ns_map, self.genroot(ns_map)))

    def dump_bool(self, obj, tag, typed = 1, ns_map = {}):
        if Config.debug: print "In dump_bool."
        self.out.append(self.dumper(None, 'boolean', obj, tag, typed,
                                     ns_map, self.genroot(ns_map)))
        
    def dump_string(self, obj, tag, typed = 0, ns_map = {}):
        if Config.debug: print "In dump_string."
        tag = tag or self.gentag()
        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

        id = self.checkref(obj, tag, ns_map)
        if id == None:
            return

        try: data = obj._marshalData()
        except: data = obj

        self.out.append(self.dumper(None, "string", cgi.escape(data), tag,
                                    typed, ns_map, self.genroot(ns_map), id))

    dump_str = dump_string # For Python 2.2+
    dump_unicode = dump_string

    def dump_None(self, obj, tag, typed = 0, ns_map = {}):
        if Config.debug: print "In dump_None."
        tag = tag or self.gentag()
        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding
        ns = self.genns(ns_map, self.config.schemaNamespaceURI)[0]

        self.out.append('<%s %snull="1"%s/>\n' %
                        (tag, ns, self.genroot(ns_map)))

    dump_NoneType = dump_None # For Python 2.2+

    def dump_list(self, obj, tag, typed = 1, ns_map = {}):
        if Config.debug: print "In dump_list.",  "obj=", obj
        tag = tag or self.gentag()
        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

        if type(obj) == InstanceType:
            data = obj.data
        else:
            data = obj

        if typed:
            id = self.checkref(obj, tag, ns_map)
            if id == None:
                return

        try:
            sample = data[0]
            empty = 0
        except:
            # preserve type if present
            if getattr(obj,"_typed",None) and getattr(obj,"_type",None):
                if getattr(obj, "_complexType", None):
                    sample = typedArrayType(typed=obj._type,
                                            complexType = obj._complexType)
                    sample._typename = obj._type
                    if not getattr(obj,"_ns",None): obj._ns = NS.URN
                else:
                    sample = typedArrayType(typed=obj._type)
            else:
                sample = structType()
            empty = 1

        # First scan list to see if all are the same type
        same_type = 1

        if not empty:
            for i in data[1:]:
                if type(sample) != type(i) or \
                    (type(sample) == InstanceType and \
                        sample.__class__ != i.__class__):
                    same_type = 0
                    break

        ndecl = ''
        if same_type:
            if (isinstance(sample, structType)) or \
                   type(sample) == DictType or \
                   (isinstance(sample, anyType) and \
                    (getattr(sample, "_complexType", None) and \
                     sample._complexType)): # force to urn struct
                try:
                    tns = obj._ns or NS.URN
                except:
                    tns = NS.URN

                ns, ndecl = self.genns(ns_map, tns)

                try:
                    typename = sample._typename
                except:
                    typename = "SOAPStruct"

                t = ns + typename
                                
            elif isinstance(sample, anyType):
                ns = sample._validNamespaceURI(self.config.typesNamespaceURI,
                                               self.config.strictNamespaces)
                if ns:
                    ns, ndecl = self.genns(ns_map, ns)
                    t = ns + str(sample._type)
                else:
                    t = 'ur-type'
            else:
                typename = type(sample).__name__

                # For Python 2.2+
                if type(sample) == StringType: typename = 'string'

                # HACK: unicode is a SOAP string
                if type(sample) == UnicodeType: typename = 'string'
                
                # HACK: python 'float' is actually a SOAP 'double'.
                if typename=="float": typename="double"  
                t = self.genns(
                ns_map, self.config.typesNamespaceURI)[0] + typename

        else:
            t = self.genns(ns_map, self.config.typesNamespaceURI)[0] + \
                "ur-type"

        try: a = obj._marshalAttrs(ns_map, self)
        except: a = ''

        ens, edecl = self.genns(ns_map, NS.ENC)
        ins, idecl = self.genns(ns_map, self.config.schemaNamespaceURI)

        if typed:
            self.out.append(
                '<%s %sarrayType="%s[%d]" %stype="%sArray"%s%s%s%s%s%s>\n' %
                (tag, ens, t, len(data), ins, ens, ndecl, edecl, idecl,
                 self.genroot(ns_map), id, a))

        if typed:
            try: elemsname = obj._elemsname
            except: elemsname = "item"
        else:
            elemsname = tag
            
        if isinstance(data, (list, tuple, arrayType)):
            should_drill = True
        else:
            should_drill = not same_type
        
        for i in data:
            self.dump(i, elemsname, should_drill, ns_map)

        if typed: self.out.append('</%s>\n' % tag)

    dump_tuple = dump_list

    def dump_exception(self, obj, tag, typed = 0, ns_map = {}):
        if isinstance(obj, faultType):    # Fault
            cns, cdecl = self.genns(ns_map, NS.ENC)
            vns, vdecl = self.genns(ns_map, NS.ENV)
            self.out.append('<%sFault %sroot="1"%s%s>' % (vns, cns, vdecl, cdecl))
            self.dump(obj.faultcode, "faultcode", typed, ns_map)
            self.dump(obj.faultstring, "faultstring", typed, ns_map)
            if hasattr(obj, "detail"):
                self.dump(obj.detail, "detail", typed, ns_map)
            self.out.append("</%sFault>\n" % vns)

    def dump_dictionary(self, obj, tag, typed = 1, ns_map = {}):
        if Config.debug: print "In dump_dictionary."
        tag = tag or self.gentag()
        tag = toXMLname(tag) # convert from SOAP 1.2 XML name encoding

        id = self.checkref(obj, tag, ns_map)
        if id == None:
            return

        try: a = obj._marshalAttrs(ns_map, self)
        except: a = ''

        self.out.append('<%s%s%s%s>\n' % 
                        (tag, id, a, self.genroot(ns_map)))

        for (k, v) in obj.items():
            if k[0] != "_":
                self.dump(v, k, 1, ns_map)

        self.out.append('</%s>\n' % tag)

    dump_dict = dump_dictionary # For Python 2.2+

    def dump_dispatch(self, obj, tag, typed = 1, ns_map = {}):
        if not tag:
            # If it has a name use it.
            if isinstance(obj, anyType) and obj._name:
                tag = obj._name
            else:
                tag = self.gentag()

        # watch out for order! 
        dumpmap = (
            (Exception, self.dump_exception),
            (arrayType, self.dump_list),
            (basestring, self.dump_string),
            (NoneType, self.dump_None),
            (bool, self.dump_bool),
            (int, self.dump_int),
            (long, self.dump_int),
            (list, self.dump_list),
            (tuple, self.dump_list),
            (dict, self.dump_dictionary),
            (float, self.dump_float),
        )
        for dtype, func in dumpmap:
            if isinstance(obj, dtype):
                func(obj, tag, typed, ns_map)
                return

        r = self.genroot(ns_map)

        try: a = obj._marshalAttrs(ns_map, self)
        except: a = ''

        if isinstance(obj, voidType):     # void
            self.out.append("<%s%s%s></%s>\n" % (tag, a, r, tag))
        else:
            id = self.checkref(obj, tag, ns_map)
            if id == None:
                return

        if isinstance(obj, structType):
            # Check for namespace
            ndecl = ''
            ns = obj._validNamespaceURI(self.config.typesNamespaceURI,
                self.config.strictNamespaces)
            if ns:
                ns, ndecl = self.genns(ns_map, ns)
                tag = ns + tag
            self.out.append("<%s%s%s%s%s>\n" % (tag, ndecl, id, a, r))

            keylist = obj.__dict__.keys()

            # first write out items with order information
            if hasattr(obj, '_keyord'):
                for i in range(len(obj._keyord)):
                    self.dump(obj._aslist(i), obj._keyord[i], 1, ns_map)
                    keylist.remove(obj._keyord[i])

            # now write out the rest
            for k in keylist:
                if (k[0] != "_"):
                    self.dump(getattr(obj,k), k, 1, ns_map)

            if isinstance(obj, bodyType):
                self.multis = 1

                for v, k in self.multirefs:
                    self.dump(v, k, typed = typed, ns_map = ns_map)

            self.out.append('</%s>\n' % tag)

        elif isinstance(obj, anyType):
            t = ''

            if typed:
                ns = obj._validNamespaceURI(self.config.typesNamespaceURI,
                    self.config.strictNamespaces)
                if ns:
                    ons, ondecl = self.genns(ns_map, ns)
                    ins, indecl = self.genns(ns_map,
                        self.config.schemaNamespaceURI)
                    t = ' %stype="%s%s"%s%s' % \
                        (ins, ons, obj._type, ondecl, indecl)

            self.out.append('<%s%s%s%s%s>%s</%s>\n' %
                            (tag, t, id, a, r, obj._marshalData(), tag))

        else:                           # Some Class
            self.out.append('<%s%s%s>\n' % (tag, id, r))

            d1 = getattr(obj, '__dict__', None)
            if d1 is not None:
                for (k, v) in d1:
                    if k[0] != "_":
                        self.dump(v, k, 1, ns_map)

            self.out.append('</%s>\n' % tag)



################################################################################
# SOAPBuilder's more public interface
################################################################################

def buildSOAP(args=(), kw={}, method=None, namespace=None,
              header=None, methodattrs=None, envelope=1, encoding='UTF-8',
              config=Config, noroot = 0):
    t = SOAPBuilder(args=args, kw=kw, method=method, namespace=namespace,
                    header=header, methodattrs=methodattrs,envelope=envelope,
                    encoding=encoding, config=config,noroot=noroot)
    return t.build()

########NEW FILE########
__FILENAME__ = Types
from __future__ import nested_scopes

"""
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: Types.py 1496 2010-03-04 23:46:17Z pooryorick $'
from version import __version__

import UserList
import base64
import cgi
import urllib
import copy
import re
import time
from types import *

# SOAPpy modules
from Errors    import *
from NS        import NS
from Utilities import encodeHexString, cleanDate
from Config    import Config

###############################################################################
# Utility functions
###############################################################################

def isPrivate(name): return name[0]=='_'
def isPublic(name):  return name[0]!='_'

###############################################################################
# Types and Wrappers
###############################################################################

class anyType:
    _validURIs = (NS.XSD, NS.XSD2, NS.XSD3, NS.ENC)

    def __init__(self, data = None, name = None, typed = 1, attrs = None):
        if self.__class__ == anyType:
            raise Error, "anyType can't be instantiated directly"

        if type(name) in (ListType, TupleType):
            self._ns, self._name = name
        else:
            self._ns = self._validURIs[0]
            self._name = name
            
        self._typed = typed
        self._attrs = {}

        self._cache = None
        self._type = self._typeName()

        self._data = self._checkValueSpace(data)

        if attrs != None:
            self._setAttrs(attrs)

    def __str__(self):
        if hasattr(self,'_name') and self._name:
            return "<%s %s at %d>" % (self.__class__, self._name, id(self))
        return "<%s at %d>" % (self.__class__, id(self))

    __repr__ = __str__

    def _checkValueSpace(self, data):
        return data

    def _marshalData(self):
        return str(self._data)

    def _marshalAttrs(self, ns_map, builder):
        a = ''

        for attr, value in self._attrs.items():
            ns, n = builder.genns(ns_map, attr[0])
            a += n + ' %s%s="%s"' % \
                (ns, attr[1], cgi.escape(str(value), 1))

        return a

    def _fixAttr(self, attr):
        if type(attr) in (StringType, UnicodeType):
            attr = (None, attr)
        elif type(attr) == ListType:
            attr = tuple(attr)
        elif type(attr) != TupleType:
            raise AttributeError, "invalid attribute type"

        if len(attr) != 2:
            raise AttributeError, "invalid attribute length"

        if type(attr[0]) not in (NoneType, StringType, UnicodeType):
            raise AttributeError, "invalid attribute namespace URI type"

        return attr

    def _getAttr(self, attr):
        attr = self._fixAttr(attr)

        try:
            return self._attrs[attr]
        except:
            return None

    def _setAttr(self, attr, value):
        attr = self._fixAttr(attr)

        if type(value) is StringType:
            value = unicode(value)

        self._attrs[attr] = value
            

    def _setAttrs(self, attrs):
        if type(attrs) in (ListType, TupleType):
            for i in range(0, len(attrs), 2):
                self._setAttr(attrs[i], attrs[i + 1])

            return

        if type(attrs) == DictType:
            d = attrs
        elif isinstance(attrs, anyType):
            d = attrs._attrs
        else:
            raise AttributeError, "invalid attribute type"

        for attr, value in d.items():
            self._setAttr(attr, value)

    def _setMustUnderstand(self, val):
        self._setAttr((NS.ENV, "mustUnderstand"), val)

    def _getMustUnderstand(self):
        return self._getAttr((NS.ENV, "mustUnderstand"))

    def _setActor(self, val):
        self._setAttr((NS.ENV, "actor"), val)

    def _getActor(self):
        return self._getAttr((NS.ENV, "actor"))

    def _typeName(self):
        return self.__class__.__name__[:-4]

    def _validNamespaceURI(self, URI, strict):
        if not hasattr(self, '_typed') or not self._typed:
            return None
        if URI in self._validURIs:
            return URI
        if not strict:
            return self._ns
        raise AttributeError, \
            "not a valid namespace for type %s" % self._type

class voidType(anyType):
    pass

class stringType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type:" % self._type

        return data

    def _marshalData(self):
        return self._data


class untypedType(stringType):
    def __init__(self, data = None, name = None, attrs = None):
        stringType.__init__(self, data, name, 0, attrs)

class IDType(stringType): pass
class NCNameType(stringType): pass
class NameType(stringType): pass
class ENTITYType(stringType): pass
class IDREFType(stringType): pass
class languageType(stringType): pass
class NMTOKENType(stringType): pass
class QNameType(stringType): pass

class tokenType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3)
    __invalidre = '[\n\t]|^ | $|  '

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        if type(self.__invalidre) == StringType:
            self.__invalidre = re.compile(self.__invalidre)

            if self.__invalidre.search(data):
                raise ValueError, "invalid %s value" % self._type

        return data

class normalizedStringType(anyType):
    _validURIs = (NS.XSD3,)
    __invalidre = '[\n\r\t]'

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        if type(self.__invalidre) == StringType:
            self.__invalidre = re.compile(self.__invalidre)

            if self.__invalidre.search(data):
                raise ValueError, "invalid %s value" % self._type

        return data

class CDATAType(normalizedStringType):
    _validURIs = (NS.XSD2,)

class booleanType(anyType):
    def __int__(self):
        return self._data

    __nonzero__ = __int__

    def _marshalData(self):
        return ['false', 'true'][self._data]

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if data in (0, '0', 'false', ''):
            return 0
        if data in (1, '1', 'true'):
            return 1
        raise ValueError, "invalid %s value" % self._type

class decimalType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType, FloatType):
            raise Error, "invalid %s value" % self._type

        return data

class floatType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType, FloatType) or \
            data < -3.4028234663852886E+38 or \
            data >  3.4028234663852886E+38:
            raise ValueError, "invalid %s value: %s" % (self._type, repr(data))

        return data

    def _marshalData(self):
        return "%.18g" % self._data # More precision

class doubleType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType, FloatType) or \
            data < -1.7976931348623158E+308 or \
            data  > 1.7976931348623157E+308:
            raise ValueError, "invalid %s value: %s" % (self._type, repr(data))

        return data

    def _marshalData(self):
        return "%.18g" % self._data # More precision

class durationType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        try:
            # A tuple or a scalar is OK, but make them into a list

            if type(data) == TupleType:
                data = list(data)
            elif type(data) != ListType:
                data = [data]

            if len(data) > 6:
                raise Exception, "too many values"

            # Now check the types of all the components, and find
            # the first nonzero element along the way.

            f = -1

            for i in range(len(data)):
                if data[i] == None:
                    data[i] = 0
                    continue

                if type(data[i]) not in \
                    (IntType, LongType, FloatType):
                    raise Exception, "element %d a bad type" % i

                if data[i] and f == -1:
                    f = i

            # If they're all 0, just use zero seconds.

            if f == -1:
                self._cache = 'PT0S'

                return (0,) * 6

            # Make sure only the last nonzero element has a decimal fraction
            # and only the first element is negative.

            d = -1

            for i in range(f, len(data)):
                if data[i]:
                    if d != -1:
                        raise Exception, \
                            "all except the last nonzero element must be " \
                            "integers"
                    if data[i] < 0 and i > f:
                        raise Exception, \
                            "only the first nonzero element can be negative"
                    elif data[i] != long(data[i]):
                        d = i

            # Pad the list on the left if necessary.

            if len(data) < 6:
                n = 6 - len(data)
                f += n
                d += n
                data = [0] * n + data

            # Save index of the first nonzero element and the decimal
            # element for _marshalData.

            self.__firstnonzero = f
            self.__decimal = d

        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            t = 0

            if d[self.__firstnonzero] < 0:
                s = '-P'
            else:
                s = 'P'

            t = 0

            for i in range(self.__firstnonzero, len(d)):
                if d[i]:
                    if i > 2 and not t:
                        s += 'T'
                        t = 1
                    if self.__decimal == i:
                        s += "%g" % abs(d[i])
                    else:
                        s += "%d" % long(abs(d[i]))
                    s += ['Y', 'M', 'D', 'H', 'M', 'S'][i]

            self._cache = s

        return self._cache

class timeDurationType(durationType):
    _validURIs = (NS.XSD, NS.XSD2, NS.ENC)

class dateTimeType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.time()

            if (type(data) in (IntType, LongType)):
                data = list(time.gmtime(data)[:6])
            elif (type(data) == FloatType):
                f = data - int(data)
                data = list(time.gmtime(int(data))[:6])
                data[5] += f
            elif type(data) in (ListType, TupleType):
                if len(data) < 6:
                    raise Exception, "not enough values"
                if len(data) > 9:
                    raise Exception, "too many values"

                data = list(data[:6])

                cleanDate(data)
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            s = "%04d-%02d-%02dT%02d:%02d:%02d" % ((abs(d[0]),) + d[1:])
            if d[0] < 0:
                s = '-' + s
            f = d[5] - int(d[5])
            if f != 0:
                s += ("%g" % f)[1:]
            s += 'Z'

            self._cache = s

        return self._cache

class recurringInstantType(anyType):
    _validURIs = (NS.XSD,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = list(time.gmtime(time.time())[:6])
            if (type(data) in (IntType, LongType)):
                data = list(time.gmtime(data)[:6])
            elif (type(data) == FloatType):
                f = data - int(data)
                data = list(time.gmtime(int(data))[:6])
                data[5] += f
            elif type(data) in (ListType, TupleType):
                if len(data) < 1:
                    raise Exception, "not enough values"
                if len(data) > 9:
                    raise Exception, "too many values"

                data = list(data[:6])

                if len(data) < 6:
                    data += [0] * (6 - len(data))

                f = len(data)

                for i in range(f):
                    if data[i] == None:
                        if f < i:
                            raise Exception, \
                                "only leftmost elements can be none"
                    else:
                        f = i
                        break

                cleanDate(data, f)
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            e = list(d)
            neg = ''

            if not e[0]:
                e[0] = '--'
            else:
                if e[0] < 0:
                    neg = '-'
                    e[0] = abs(e[0])
                if e[0] < 100:
                    e[0] = '-' + "%02d" % e[0]
                else:
                    e[0] = "%04d" % e[0]

            for i in range(1, len(e)):
                if e[i] == None or (i < 3 and e[i] == 0):
                    e[i] = '-'
                else:
                    if e[i] < 0:
                        neg = '-'
                        e[i] = abs(e[i])

                    e[i] = "%02d" % e[i]

            if d[5]:
                f = abs(d[5] - int(d[5]))

                if f:
                    e[5] += ("%g" % f)[1:]

            s = "%s%s-%s-%sT%s:%s:%sZ" % ((neg,) + tuple(e))

            self._cache = s

        return self._cache

class timeInstantType(dateTimeType):
    _validURIs = (NS.XSD, NS.XSD2, NS.ENC)

class timePeriodType(dateTimeType):
    _validURIs = (NS.XSD2, NS.ENC)

class timeType(anyType):
    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[3:6]
            elif (type(data) == FloatType):
                f = data - int(data)
                data = list(time.gmtime(int(data))[3:6])
                data[2] += f
            elif type(data) in (IntType, LongType):
                data = time.gmtime(data)[3:6]
            elif type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[3:6]
                elif len(data) > 3:
                    raise Exception, "too many values"

                data = [None, None, None] + list(data)

                if len(data) < 6:
                    data += [0] * (6 - len(data))

                cleanDate(data, 3)

                data = data[3:]
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            #s = ''
            #
            #s = time.strftime("%H:%M:%S", (0, 0, 0) + d + (0, 0, -1))
            s = "%02d:%02d:%02d" % d
            f = d[2] - int(d[2])
            if f != 0:
                s += ("%g" % f)[1:]
            s += 'Z'

            self._cache = s

        return self._cache

class dateType(anyType):
    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[0:3]
            elif type(data) in (IntType, LongType, FloatType):
                data = time.gmtime(data)[0:3]
            elif type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[0:3]
                elif len(data) > 3:
                    raise Exception, "too many values"

                data = list(data)

                if len(data) < 3:
                    data += [1, 1, 1][len(data):]

                data += [0, 0, 0]

                cleanDate(data)

                data = data[:3]
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            s = "%04d-%02d-%02dZ" % ((abs(d[0]),) + d[1:])
            if d[0] < 0:
                s = '-' + s

            self._cache = s

        return self._cache

class gYearMonthType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[0:2]
            elif type(data) in (IntType, LongType, FloatType):
                data = time.gmtime(data)[0:2]
            elif type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[0:2]
                elif len(data) > 2:
                    raise Exception, "too many values"

                data = list(data)

                if len(data) < 2:
                    data += [1, 1][len(data):]

                data += [1, 0, 0, 0]

                cleanDate(data)

                data = data[:2]
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            s = "%04d-%02dZ" % ((abs(d[0]),) + d[1:])
            if d[0] < 0:
                s = '-' + s

            self._cache = s

        return self._cache

class gYearType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[0:1]
            elif type(data) in (IntType, LongType, FloatType):
                data = [data]

            if type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[0:1]
                elif len(data) < 1:
                    raise Exception, "too few values"
                elif len(data) > 1:
                    raise Exception, "too many values"

                if type(data[0]) == FloatType:
                    try: s = int(data[0])
                    except: s = long(data[0])

                    if s != data[0]:
                        raise Exception, "not integral"

                    data = [s]
                elif type(data[0]) not in (IntType, LongType):
                    raise Exception, "bad type"
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return data[0]

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            s = "%04dZ" % abs(d)
            if d < 0:
                s = '-' + s

            self._cache = s

        return self._cache

class centuryType(anyType):
    _validURIs = (NS.XSD2, NS.ENC)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[0:1] / 100
            elif type(data) in (IntType, LongType, FloatType):
                data = [data]

            if type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[0:1] / 100
                elif len(data) < 1:
                    raise Exception, "too few values"
                elif len(data) > 1:
                    raise Exception, "too many values"

                if type(data[0]) == FloatType:
                    try: s = int(data[0])
                    except: s = long(data[0])

                    if s != data[0]:
                        raise Exception, "not integral"

                    data = [s]
                elif type(data[0]) not in (IntType, LongType):
                    raise Exception, "bad type"
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return data[0]

    def _marshalData(self):
        if self._cache == None:
            d = self._data
            s = "%02dZ" % abs(d)
            if d < 0:
                s = '-' + s

            self._cache = s

        return self._cache

class yearType(gYearType):
    _validURIs = (NS.XSD2, NS.ENC)

class gMonthDayType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[1:3]
            elif type(data) in (IntType, LongType, FloatType):
                data = time.gmtime(data)[1:3]
            elif type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[0:2]
                elif len(data) > 2:
                    raise Exception, "too many values"

                data = list(data)

                if len(data) < 2:
                    data += [1, 1][len(data):]

                data = [0] + data + [0, 0, 0]

                cleanDate(data, 1)

                data = data[1:3]
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return tuple(data)

    def _marshalData(self):
        if self._cache == None:
            self._cache = "--%02d-%02dZ" % self._data

        return self._cache

class recurringDateType(gMonthDayType):
    _validURIs = (NS.XSD2, NS.ENC)

class gMonthType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[1:2]
            elif type(data) in (IntType, LongType, FloatType):
                data = [data]

            if type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[1:2]
                elif len(data) < 1:
                    raise Exception, "too few values"
                elif len(data) > 1:
                    raise Exception, "too many values"

                if type(data[0]) == FloatType:
                    try: s = int(data[0])
                    except: s = long(data[0])

                    if s != data[0]:
                        raise Exception, "not integral"

                    data = [s]
                elif type(data[0]) not in (IntType, LongType):
                    raise Exception, "bad type"

                if data[0] < 1 or data[0] > 12:
                    raise Exception, "bad value"
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return data[0]

    def _marshalData(self):
        if self._cache == None:
            self._cache = "--%02d--Z" % self._data

        return self._cache

class monthType(gMonthType):
    _validURIs = (NS.XSD2, NS.ENC)

class gDayType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        try:
            if data == None:
                data = time.gmtime(time.time())[2:3]
            elif type(data) in (IntType, LongType, FloatType):
                data = [data]

            if type(data) in (ListType, TupleType):
                if len(data) == 9:
                    data = data[2:3]
                elif len(data) < 1:
                    raise Exception, "too few values"
                elif len(data) > 1:
                    raise Exception, "too many values"

                if type(data[0]) == FloatType:
                    try: s = int(data[0])
                    except: s = long(data[0])

                    if s != data[0]:
                        raise Exception, "not integral"

                    data = [s]
                elif type(data[0]) not in (IntType, LongType):
                    raise Exception, "bad type"

                if data[0] < 1 or data[0] > 31:
                    raise Exception, "bad value"
            else:
                raise Exception, "invalid type"
        except Exception, e:
            raise ValueError, "invalid %s value - %s" % (self._type, e)

        return data[0]

    def _marshalData(self):
        if self._cache == None:
            self._cache = "---%02dZ" % self._data

        return self._cache

class recurringDayType(gDayType):
    _validURIs = (NS.XSD2, NS.ENC)

class hexBinaryType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        return data

    def _marshalData(self):
        if self._cache == None:
            self._cache = encodeHexString(self._data)

        return self._cache

class base64BinaryType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        return data

    def _marshalData(self):
        if self._cache == None:
            self._cache = base64.encodestring(self._data)

        return self._cache

class base64Type(base64BinaryType):
    _validURIs = (NS.ENC,)

class binaryType(anyType):
    _validURIs = (NS.XSD, NS.ENC)

    def __init__(self, data, name = None, typed = 1, encoding = 'base64',
        attrs = None):

        anyType.__init__(self, data, name, typed, attrs)

        self._setAttr('encoding', encoding)

    def _marshalData(self):
        if self._cache == None:
            if self._getAttr((None, 'encoding')) == 'base64':
                self._cache = base64.encodestring(self._data)
            else:
                self._cache = encodeHexString(self._data)

        return self._cache

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        return data

    def _setAttr(self, attr, value):
        attr = self._fixAttr(attr)

        if attr[1] == 'encoding':
            if attr[0] != None or value not in ('base64', 'hex'):
                raise AttributeError, "invalid encoding"

            self._cache = None

        anyType._setAttr(self, attr, value)


class anyURIType(anyType):
    _validURIs = (NS.XSD3,)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (StringType, UnicodeType):
            raise AttributeError, "invalid %s type" % self._type

        return data

    def _marshalData(self):
        if self._cache == None:
            self._cache = urllib.quote(self._data)

        return self._cache

class uriType(anyURIType):
    _validURIs = (NS.XSD,)

class uriReferenceType(anyURIType):
    _validURIs = (NS.XSD2,)

class NOTATIONType(anyType):
    def __init__(self, data, name = None, typed = 1, attrs = None):

        if self.__class__ == NOTATIONType:
            raise Error, "a NOTATION can't be instantiated directly"

        anyType.__init__(self, data, name, typed, attrs)

class ENTITIESType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) in (StringType, UnicodeType):
            return (data,)

        if type(data) not in (ListType, TupleType) or \
            filter (lambda x: type(x) not in (StringType, UnicodeType), data):
            raise AttributeError, "invalid %s type" % self._type

        return data

    def _marshalData(self):
        return ' '.join(self._data)

class IDREFSType(ENTITIESType): pass
class NMTOKENSType(ENTITIESType): pass

class integerType(anyType):
    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType):
            raise ValueError, "invalid %s value" % self._type

        return data

class nonPositiveIntegerType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or data > 0:
            raise ValueError, "invalid %s value" % self._type

        return data

class non_Positive_IntegerType(nonPositiveIntegerType):
    _validURIs = (NS.XSD,)

    def _typeName(self):
        return 'non-positive-integer'

class negativeIntegerType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or data >= 0:
            raise ValueError, "invalid %s value" % self._type

        return data

class negative_IntegerType(negativeIntegerType):
    _validURIs = (NS.XSD,)

    def _typeName(self):
        return 'negative-integer'

class longType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < -9223372036854775808L or \
            data >  9223372036854775807L:
            raise ValueError, "invalid %s value" % self._type

        return data

class intType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < -2147483648L or \
            data >  2147483647L:
            raise ValueError, "invalid %s value" % self._type

        return data

class shortType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < -32768 or \
            data >  32767:
            raise ValueError, "invalid %s value" % self._type

        return data

class byteType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < -128 or \
            data >  127:
            raise ValueError, "invalid %s value" % self._type

        return data

class nonNegativeIntegerType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or data < 0:
            raise ValueError, "invalid %s value" % self._type

        return data

class non_Negative_IntegerType(nonNegativeIntegerType):
    _validURIs = (NS.XSD,)

    def _typeName(self):
        return 'non-negative-integer'

class unsignedLongType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < 0 or \
            data > 18446744073709551615L:
            raise ValueError, "invalid %s value" % self._type

        return data

class unsignedIntType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < 0 or \
            data > 4294967295L:
            raise ValueError, "invalid %s value" % self._type

        return data

class unsignedShortType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < 0 or \
            data > 65535:
            raise ValueError, "invalid %s value" % self._type

        return data

class unsignedByteType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or \
            data < 0 or \
            data > 255:
            raise ValueError, "invalid %s value" % self._type

        return data

class positiveIntegerType(anyType):
    _validURIs = (NS.XSD2, NS.XSD3, NS.ENC)

    def _checkValueSpace(self, data):
        if data == None:
            raise ValueError, "must supply initial %s value" % self._type

        if type(data) not in (IntType, LongType) or data <= 0:
            raise ValueError, "invalid %s value" % self._type

        return data

class positive_IntegerType(positiveIntegerType):
    _validURIs = (NS.XSD,)

    def _typeName(self):
        return 'positive-integer'

# Now compound types

class compoundType(anyType):
    def __init__(self, data = None, name = None, typed = 1, attrs = None):
        if self.__class__ == compoundType:
            raise Error, "a compound can't be instantiated directly"

        anyType.__init__(self, data, name, typed, attrs)
        self._keyord    = []

        if type(data) == DictType:
            self.__dict__.update(data)

    def _aslist(self, item=None):
        if item is not None:
            return self.__dict__[self._keyord[item]]
        else:
            return map( lambda x: self.__dict__[x], self._keyord)

    def _asdict(self, item=None, encoding=Config.dict_encoding):
        if item is not None:
            if type(item) in (UnicodeType,StringType):
                item = item.encode(encoding)
            return self.__dict__[item]
        else:
            retval = {}
            def fun(x): retval[x.encode(encoding)] = self.__dict__[x]

            if hasattr(self, '_keyord'):
                map( fun, self._keyord)
            else:
                for name in dir(self):
                    if isPublic(name):
                        retval[name] = getattr(self,name)
            return retval

 
    def __getitem__(self, item):
        if type(item) == IntType:
            return self.__dict__[self._keyord[item]]
        else:
            return getattr(self, item)

    def __len__(self):
        return len(self._keyord)

    def __nonzero__(self):
        return 1

    def _keys(self):
        return filter(lambda x: x[0] != '_', self.__dict__.keys())

    def _addItem(self, name, value, attrs = None):

        if name in self._keyord:
            if type(self.__dict__[name]) != ListType:
                self.__dict__[name] = [self.__dict__[name]]
            self.__dict__[name].append(value)
        else:
            self.__dict__[name] = value
            self._keyord.append(name)
            
    def _placeItem(self, name, value, pos, subpos = 0, attrs = None):

        if subpos == 0 and type(self.__dict__[name]) != ListType:
            self.__dict__[name] = value
        else:
            self.__dict__[name][subpos] = value

        # only add to key order list if it does not already 
        # exist in list
        if not (name in self._keyord):
            if pos < len(x):
                self._keyord[pos] = name
            else:
                self._keyord.append(name)
              

    def _getItemAsList(self, name, default = []):
        try:
            d = self.__dict__[name]
        except:
            return default

        if type(d) == ListType:
            return d
        return [d]

    def __str__(self):
        return anyType.__str__(self) + ": " + str(self._asdict())

    def __repr__(self):
        return self.__str__()

class structType(compoundType):
    pass

class headerType(structType):
    _validURIs = (NS.ENV,)

    def __init__(self, data = None, typed = 1, attrs = None):
        structType.__init__(self, data, "Header", typed, attrs)

class bodyType(structType):
    _validURIs = (NS.ENV,)

    def __init__(self, data = None, typed = 1, attrs = None):
        structType.__init__(self, data, "Body", typed, attrs)

class arrayType(UserList.UserList, compoundType):
    def __init__(self, data = None, name = None, attrs = None,
        offset = 0, rank = None, asize = 0, elemsname = None):

        if data:
            if type(data) not in (ListType, TupleType):
                raise Error, "Data must be a sequence"

        UserList.UserList.__init__(self, data)
        compoundType.__init__(self, data, name, 0, attrs)

        self._elemsname = elemsname or "item"

        if data == None:
            self._rank = rank

            # According to 5.4.2.2 in the SOAP spec, each element in a
            # sparse array must have a position. _posstate keeps track of
            # whether we've seen a position or not. It's possible values
            # are:
            # -1 No elements have been added, so the state is indeterminate
            #  0 An element without a position has been added, so no
            #    elements can have positions
            #  1 An element with a position has been added, so all elements
            #    must have positions

            self._posstate = -1

            self._full = 0

            if asize in ('', None):
                asize = '0'

            self._dims = map (lambda x: int(x), str(asize).split(','))
            self._dims.reverse()   # It's easier to work with this way
            self._poss = [0] * len(self._dims)      # This will end up
                                                    # reversed too

            for i in range(len(self._dims)):
                if self._dims[i] < 0 or \
                    self._dims[i] == 0 and len(self._dims) > 1:
                    raise TypeError, "invalid Array dimensions"

                if offset > 0:
                    self._poss[i] = offset % self._dims[i]
                    offset = int(offset / self._dims[i])

                # Don't break out of the loop if offset is 0 so we test all the
                # dimensions for > 0.
            if offset:
                raise AttributeError, "invalid Array offset"

            a = [None] * self._dims[0]

            for i in range(1, len(self._dims)):
                b = []

                for j in range(self._dims[i]):
                    b.append(copy.deepcopy(a))

                a = b

            self.data = a


    def _aslist(self, item=None):
        if item is not None:
            return self.data[int(item)]
        else:
            return self.data

    def _asdict(self, item=None, encoding=Config.dict_encoding):
        if item is not None:
            if type(item) in (UnicodeType,StringType):
                item = item.encode(encoding)
            return self.data[int(item)]
        else:
            retval = {}
            def fun(x): retval[str(x).encode(encoding)] = self.data[x]
            
            map( fun, range(len(self.data)) )
            return retval
 
    def __getitem__(self, item):
        try:
            return self.data[int(item)]
        except ValueError:
            return getattr(self, item)

    def __len__(self):
        return len(self.data)

    def __nonzero__(self):
        return 1

    def __str__(self):
        return anyType.__str__(self) + ": " + str(self._aslist())

    def _keys(self):
        return filter(lambda x: x[0] != '_', self.__dict__.keys())

    def _addItem(self, name, value, attrs):
        if self._full:
            raise ValueError, "Array is full"

        pos = attrs.get((NS.ENC, 'position'))

        if pos != None:
            if self._posstate == 0:
                raise AttributeError, \
                    "all elements in a sparse Array must have a " \
                    "position attribute"

            self._posstate = 1

            try:
                if pos[0] == '[' and pos[-1] == ']':
                    pos = map (lambda x: int(x), pos[1:-1].split(','))
                    pos.reverse()

                    if len(pos) == 1:
                        pos = pos[0]

                        curpos = [0] * len(self._dims)

                        for i in range(len(self._dims)):
                            curpos[i] = pos % self._dims[i]
                            pos = int(pos / self._dims[i])

                            if pos == 0:
                                break

                        if pos:
                            raise Exception
                    elif len(pos) != len(self._dims):
                        raise Exception
                    else:
                        for i in range(len(self._dims)):
                            if pos[i] >= self._dims[i]:
                                raise Exception

                        curpos = pos
                else:
                    raise Exception
            except:
                raise AttributeError, \
                    "invalid Array element position %s" % str(pos)
        else:
            if self._posstate == 1:
                raise AttributeError, \
                    "only elements in a sparse Array may have a " \
                    "position attribute"

            self._posstate = 0

            curpos = self._poss

        a = self.data

        for i in range(len(self._dims) - 1, 0, -1):
            a = a[curpos[i]]

        if curpos[0] >= len(a):
            a += [None] * (len(a) - curpos[0] + 1)

        a[curpos[0]] = value

        if pos == None:
            self._poss[0] += 1

            for i in range(len(self._dims) - 1):
                if self._poss[i] < self._dims[i]:
                    break

                self._poss[i] = 0
                self._poss[i + 1] += 1

            if self._dims[-1] and self._poss[-1] >= self._dims[-1]:
                #self._full = 1
                #FIXME: why is this occuring?
                pass

    def _placeItem(self, name, value, pos, subpos, attrs = None):
        curpos = [0] * len(self._dims)

        for i in range(len(self._dims)):
            if self._dims[i] == 0:
                curpos[0] = pos
                break

            curpos[i] = pos % self._dims[i]
            pos = int(pos / self._dims[i])

            if pos == 0:
                break

        if self._dims[i] != 0 and pos:
            raise Error, "array index out of range"

        a = self.data

        for i in range(len(self._dims) - 1, 0, -1):
            a = a[curpos[i]]

        if curpos[0] >= len(a):
            a += [None] * (len(a) - curpos[0] + 1)

        a[curpos[0]] = value

class typedArrayType(arrayType):
    def __init__(self, data = None, name = None, typed = None, attrs = None,
        offset = 0, rank = None, asize = 0, elemsname = None, complexType = 0):

        arrayType.__init__(self, data, name, attrs, offset, rank, asize,
            elemsname)

        self._typed = 1
        self._type = typed
        self._complexType = complexType

class faultType(structType, Error):
    def __init__(self, faultcode = "", faultstring = "", detail = None):
        self.faultcode = faultcode
        self.faultstring = faultstring
        if detail != None:
            self.detail = detail

        structType.__init__(self, None, 0)

    def _setDetail(self, detail = None):
        if detail != None:
            self.detail = detail
        else:
            try: del self.detail
            except AttributeError: pass

    def __repr__(self):
        if getattr(self, 'detail', None) != None:
            return "<Fault %s: %s: %s>" % (self.faultcode,
                                           self.faultstring,
                                           self.detail)
        else:
            return "<Fault %s: %s>" % (self.faultcode, self.faultstring)

    __str__ = __repr__

    def __call__(self):
        return (self.faultcode, self.faultstring, self.detail)        

class SOAPException(Exception):
    def __init__(self, code="", string="", detail=None):
        self.value = ("SOAPpy SOAP Exception", code, string, detail)
        self.code = code
        self.string = string
        self.detail = detail

    def __str__(self):
        return repr(self.value)

class RequiredHeaderMismatch(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class MethodNotFound(Exception):
    def __init__(self, value):
        (val, detail) = value.split(":")
        self.value = val
        self.detail = detail

    def __str__(self):
        return repr(self.value, self.detail)

class AuthorizationFailed(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class MethodFailed(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
        
#######
# Convert complex SOAPpy objects to native python equivalents
#######

def simplify(object, level=0):
    """
    Convert the SOAPpy objects and their contents to simple python types.

    This function recursively converts the passed 'container' object,
    and all public subobjects. (Private subobjects have names that
    start with '_'.)
    
    Conversions:
    - faultType    --> raise python exception
    - arrayType    --> array
    - compoundType --> dictionary
    """
    
    if level > 10:
        return object
    
    if isinstance( object, faultType ):
        if object.faultstring == "Required Header Misunderstood":
            raise RequiredHeaderMismatch(object.detail)
        elif object.faultstring == "Method Not Found":
            raise MethodNotFound(object.detail)
        elif object.faultstring == "Authorization Failed":
            raise AuthorizationFailed(object.detail)
        elif object.faultstring == "Method Failed":
            raise MethodFailed(object.detail)
        else:
            se = SOAPException(object.faultcode, object.faultstring,
                               object.detail)
            raise se
    elif isinstance( object, arrayType ):
        data = object._aslist()
        for k in range(len(data)):
            data[k] = simplify(data[k], level=level+1)
        return data
    elif isinstance( object, compoundType ) or isinstance(object, structType):
        data = object._asdict()
        for k in data.keys():
            if isPublic(k):
                data[k] = simplify(data[k], level=level+1)
        return data
    elif type(object)==DictType:
        for k in object.keys():
            if isPublic(k):
                object[k] = simplify(object[k])
        return object
    elif type(object)==list:
        for k in range(len(object)):
            object[k] = simplify(object[k])
        return object
    else:
        return object


def simplify_contents(object, level=0):
    """
    Convert the contents of SOAPpy objects to simple python types.

    This function recursively converts the sub-objects contained in a
    'container' object to simple python types.
    
    Conversions:
    - faultType    --> raise python exception
    - arrayType    --> array
    - compoundType --> dictionary
    """
    
    if level>10: return object

    if isinstance( object, faultType ):
        for k in object._keys():
            if isPublic(k):
                setattr(object, k, simplify(object[k], level=level+1))
        raise object
    elif isinstance( object, arrayType ): 
        data = object._aslist()
        for k in range(len(data)):
            object[k] = simplify(data[k], level=level+1)
    elif isinstance(object, structType):
        data = object._asdict()
        for k in data.keys():
            if isPublic(k):
                setattr(object, k, simplify(data[k], level=level+1))
    elif isinstance( object, compoundType ) :
        data = object._asdict()
        for k in data.keys():
            if isPublic(k):
                object[k] = simplify(data[k], level=level+1)
    elif type(object)==DictType:
        for k in object.keys():
            if isPublic(k):
                object[k] = simplify(object[k])
    elif type(object)==list:
        for k in range(len(object)):
            object[k] = simplify(object[k])
    
    return object



########NEW FILE########
__FILENAME__ = URLopener
"""Provide a class for loading data from URL's that handles basic
authentication"""

ident = '$Id: URLopener.py 541 2004-01-31 04:20:06Z warnes $'
from version import __version__

from Config import Config
from urllib import FancyURLopener

class URLopener(FancyURLopener):

    username = None
    passwd = None


    def __init__(self, username=None, passwd=None, *args, **kw):
        FancyURLopener.__init__( self, *args, **kw)
        self.username = username
        self.passwd = passwd


    def prompt_user_passwd(self, host, realm):
       return self.username, self.passwd

########NEW FILE########
__FILENAME__ = Utilities
"""
################################################################################
# Copyright (c) 2003, Pfizer
# Copyright (c) 2001, Cayce Ullman.
# Copyright (c) 2001, Brian Matthews.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of actzero, inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
################################################################################
"""

ident = '$Id: Utilities.py 1298 2006-11-07 00:54:15Z sanxiyn $'
from version import __version__

import re
import string
import sys
from types import *

# SOAPpy modules
from Errors import *

################################################################################
# Utility infielders
################################################################################
def collapseWhiteSpace(s):
    return re.sub('\s+', ' ', s).strip()

def decodeHexString(data):
    conv = {
            '0': 0x0, '1': 0x1, '2': 0x2, '3': 0x3, '4': 0x4,
            '5': 0x5, '6': 0x6, '7': 0x7, '8': 0x8, '9': 0x9,
            
            'a': 0xa, 'b': 0xb, 'c': 0xc, 'd': 0xd, 'e': 0xe,
            'f': 0xf,
            
            'A': 0xa, 'B': 0xb, 'C': 0xc, 'D': 0xd, 'E': 0xe,
            'F': 0xf,
            }
    
    ws = string.whitespace

    bin = ''

    i = 0

    while i < len(data):
        if data[i] not in ws:
            break
        i += 1

    low = 0

    while i < len(data):
        c = data[i]

        if c in string.whitespace:
            break

        try:
            c = conv[c]
        except KeyError:
            raise ValueError, \
                "invalid hex string character `%s'" % c

        if low:
            bin += chr(high * 16 + c)
            low = 0
        else:
            high = c
            low = 1

        i += 1

    if low:
        raise ValueError, "invalid hex string length"

    while i < len(data):
        if data[i] not in string.whitespace:
            raise ValueError, \
                "invalid hex string character `%s'" % c

        i += 1

    return bin

def encodeHexString(data):
    h = ''

    for i in data:
        h += "%02X" % ord(i)

    return h

def leapMonth(year, month):
    return month == 2 and \
        year % 4 == 0 and \
        (year % 100 != 0 or year % 400 == 0)

def cleanDate(d, first = 0):
    ranges = (None, (1, 12), (1, 31), (0, 23), (0, 59), (0, 61))
    months = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    names = ('year', 'month', 'day', 'hours', 'minutes', 'seconds')

    if len(d) != 6:
        raise ValueError, "date must have 6 elements"

    for i in range(first, 6):
        s = d[i]

        if type(s) == FloatType:
            if i < 5:
                try:
                    s = int(s)
                except OverflowError:
                    if i > 0:
                        raise
                    s = long(s)

                if s != d[i]:
                    raise ValueError, "%s must be integral" % names[i]

                d[i] = s
        elif type(s) == LongType:
            try: s = int(s)
            except: pass
        elif type(s) != IntType:
            raise TypeError, "%s isn't a valid type" % names[i]

        if i == first and s < 0:
            continue

        if ranges[i] != None and \
            (s < ranges[i][0] or ranges[i][1] < s):
            raise ValueError, "%s out of range" % names[i]

    if first < 6 and d[5] >= 61:
        raise ValueError, "seconds out of range"

    if first < 2:
        leap = first < 1 and leapMonth(d[0], d[1])

        if d[2] > months[d[1]] + leap:
            raise ValueError, "day out of range"

def debugHeader(title):
    s = '*** ' + title + ' '
    print s + ('*' * (72 - len(s)))

def debugFooter(title):
    print '*' * 72
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = version
__version__="0.12.5"


########NEW FILE########
__FILENAME__ = WSDL
"""Parse web services description language to get SOAP methods.

Rudimentary support."""

ident = '$Id: WSDL.py 1467 2008-05-16 23:32:51Z warnes $'
from version import __version__

import wstools
import xml
from Errors import Error
from Client import SOAPProxy, SOAPAddress
from Config import Config
import urllib

class Proxy:
    """WSDL Proxy.
    
    SOAPProxy wrapper that parses method names, namespaces, soap actions from
    the web service description language (WSDL) file passed into the
    constructor.  The WSDL reference can be passed in as a stream, an url, a
    file name, or a string.

    Loads info into self.methods, a dictionary with methodname keys and values
    of WSDLTools.SOAPCallinfo.

    For example,
    
        url = 'http://www.xmethods.org/sd/2001/TemperatureService.wsdl'
        wsdl = WSDL.Proxy(url)
        print len(wsdl.methods)          # 1
        print wsdl.methods.keys()        # getTemp


    See WSDLTools.SOAPCallinfo for more info on each method's attributes.
    """

    def __init__(self, wsdlsource, config=Config, **kw ):

        reader = wstools.WSDLTools.WSDLReader()
        self.wsdl = None

        # From Mark Pilgrim's "Dive Into Python" toolkit.py--open anything.
        if self.wsdl is None and hasattr(wsdlsource, "read"):
            print 'stream:', wsdlsource
            try:
                self.wsdl = reader.loadFromStream(wsdlsource)
            except xml.parsers.expat.ExpatError, e:
                newstream = urllib.URLopener(key_file=config.SSL.key_file, cert_file=config.SSL.cert_file).open(wsdlsource)
                buf = newstream.readlines()
                raise Error, "Unable to parse WSDL file at %s: \n\t%s" % \
                      (wsdlsource, "\t".join(buf))
                

        # NOT TESTED (as of April 17, 2003)
        #if self.wsdl is None and wsdlsource == '-':
        #    import sys
        #    self.wsdl = reader.loadFromStream(sys.stdin)
        #    print 'stdin'

        if self.wsdl is None:
            try: 
                file(wsdlsource)
                self.wsdl = reader.loadFromFile(wsdlsource)
                #print 'file'
            except (IOError, OSError): pass
            except xml.parsers.expat.ExpatError, e:
                newstream = urllib.urlopen(wsdlsource)
                buf = newstream.readlines()
                raise Error, "Unable to parse WSDL file at %s: \n\t%s" % \
                      (wsdlsource, "\t".join(buf))
            
        if self.wsdl is None:
            try:
                stream = urllib.URLopener(key_file=config.SSL.key_file, cert_file=config.SSL.cert_file).open(wsdlsource)
                self.wsdl = reader.loadFromStream(stream, wsdlsource)
            except (IOError, OSError): pass
            except xml.parsers.expat.ExpatError, e:
                newstream = urllib.urlopen(wsdlsource)
                buf = newstream.readlines()
                raise Error, "Unable to parse WSDL file at %s: \n\t%s" % \
                      (wsdlsource, "\t".join(buf))
            
        if self.wsdl is None:
            import StringIO
            self.wsdl = reader.loadFromString(str(wsdlsource))
            #print 'string'

        # Package wsdl info as a dictionary of remote methods, with method name
        # as key (based on ServiceProxy.__init__ in ZSI library).
        self.methods = {}
        service = self.wsdl.services[0]
        port = service.ports[0]
        name = service.name
        binding = port.getBinding()
        portType = binding.getPortType()
        for operation in portType.operations:
            callinfo = wstools.WSDLTools.callInfoFromWSDL(port, operation.name)
            self.methods[callinfo.methodName] = callinfo

        self.soapproxy = SOAPProxy('http://localhost/dummy.webservice',
                                   config=config, **kw)

    def __str__(self): 
        s = ''
        for method in self.methods.values():
            s += str(method)
        return s

    def __getattr__(self, name):
        """Set up environment then let parent class handle call.

        Raises AttributeError is method name is not found."""

        if not self.methods.has_key(name): raise AttributeError, name

        callinfo = self.methods[name]
        self.soapproxy.proxy = SOAPAddress(callinfo.location)
        self.soapproxy.namespace = callinfo.namespace
        self.soapproxy.soapaction = callinfo.soapAction
        return self.soapproxy.__getattr__(name)

    def show_methods(self):
        for key in self.methods.keys():
            method = self.methods[key]
            print "Method Name:", key.ljust(15)
            print
            inps = method.inparams
            for parm in range(len(inps)):
                details = inps[parm]
                print "   In #%d: %s  (%s)" % (parm, details.name, details.type)
            print
            outps = method.outparams
            for parm in range(len(outps)):
                details = outps[parm]
                print "   Out #%d: %s  (%s)" % (parm, details.name, details.type)
            print


########NEW FILE########
__FILENAME__ = c14n
#! /usr/bin/env python
'''XML Canonicalization

Patches Applied to xml.dom.ext.c14n:
    http://sourceforge.net/projects/pyxml/

    [ 1444526 ] c14n.py: http://www.w3.org/TR/xml-exc-c14n/ fix
        -- includes [ 829905 ] c14n.py fix for bug #825115, 
           Date Submitted: 2003-10-24 23:43
        -- include dependent namespace declarations declared in ancestor nodes 
           (checking attributes and tags), 
        -- handle InclusiveNamespaces PrefixList parameter

This module generates canonical XML of a document or element.
    http://www.w3.org/TR/2001/REC-xml-c14n-20010315
and includes a prototype of exclusive canonicalization
    http://www.w3.org/Signature/Drafts/xml-exc-c14n

Requires PyXML 0.7.0 or later.

Known issues if using Ft.Lib.pDomlette:
    1. Unicode
    2. does not white space normalize attributes of type NMTOKEN and ID?
    3. seems to be include "\n" after importing external entities?

Note, this version processes a DOM tree, and consequently it processes
namespace nodes as attributes, not from a node's namespace axis. This
permits simple document and element canonicalization without
XPath. When XPath is used, the XPath result node list is passed and used to
determine if the node is in the XPath result list, but little else.

Authors:
    "Joseph M. Reagle Jr." <reagle@w3.org>
    "Rich Salz" <rsalz@zolera.com>

$Date$ by $Author$
'''

_copyright = '''Copyright 2001, Zolera Systems Inc.  All Rights Reserved.
Copyright 2001, MIT. All Rights Reserved.

Distributed under the terms of:
  Python 2.0 License or later.
  http://www.python.org/2.0.1/license.html
or
  W3C Software License
  http://www.w3.org/Consortium/Legal/copyright-software-19980720
'''

import string
from xml.dom import Node
try:
    from xml.ns import XMLNS
except:
    class XMLNS:
        BASE = "http://www.w3.org/2000/xmlns/"
        XML = "http://www.w3.org/XML/1998/namespace"
try:
    import cStringIO
    StringIO = cStringIO
except ImportError:
    import StringIO

_attrs = lambda E: (E.attributes and E.attributes.values()) or []
_children = lambda E: E.childNodes or []
_IN_XML_NS = lambda n: n.name.startswith("xmlns")
_inclusive = lambda n: n.unsuppressedPrefixes == None


# Does a document/PI has lesser/greater document order than the
# first element?
_LesserElement, _Element, _GreaterElement = range(3)

def _sorter(n1,n2):
    '''_sorter(n1,n2) -> int
    Sorting predicate for non-NS attributes.'''

    i = cmp(n1.namespaceURI, n2.namespaceURI)
    if i: return i
    return cmp(n1.localName, n2.localName)


def _sorter_ns(n1,n2):
    '''_sorter_ns((n,v),(n,v)) -> int
    "(an empty namespace URI is lexicographically least)."'''

    if n1[0] == 'xmlns': return -1
    if n2[0] == 'xmlns': return 1
    return cmp(n1[0], n2[0])

def _utilized(n, node, other_attrs, unsuppressedPrefixes):
    '''_utilized(n, node, other_attrs, unsuppressedPrefixes) -> boolean
    Return true if that nodespace is utilized within the node'''
    if n.startswith('xmlns:'):
        n = n[6:]
    elif n.startswith('xmlns'):
        n = n[5:]
    if (n=="" and node.prefix in ["#default", None]) or \
        n == node.prefix or n in unsuppressedPrefixes: 
            return 1
    for attr in other_attrs:
        if n == attr.prefix: return 1
    # For exclusive need to look at attributes
    if unsuppressedPrefixes is not None:
        for attr in _attrs(node):
            if n == attr.prefix: return 1
            
    return 0


def _inclusiveNamespacePrefixes(node, context, unsuppressedPrefixes):
    '''http://www.w3.org/TR/xml-exc-c14n/ 
    InclusiveNamespaces PrefixList parameter, which lists namespace prefixes that 
    are handled in the manner described by the Canonical XML Recommendation'''
    inclusive = []
    if node.prefix:
        usedPrefixes = ['xmlns:%s' %node.prefix]
    else:
        usedPrefixes = ['xmlns']

    for a in _attrs(node):
        if a.nodeName.startswith('xmlns') or not a.prefix: continue
        usedPrefixes.append('xmlns:%s' %a.prefix)

    unused_namespace_dict = {}
    for attr in context:
        n = attr.nodeName
        if n in unsuppressedPrefixes:
            inclusive.append(attr)
        elif n.startswith('xmlns:') and n[6:] in unsuppressedPrefixes:
            inclusive.append(attr)
        elif n.startswith('xmlns') and n[5:] in unsuppressedPrefixes:
            inclusive.append(attr)
        elif attr.nodeName in usedPrefixes:
            inclusive.append(attr)
        elif n.startswith('xmlns:'):
            unused_namespace_dict[n] = attr.value

    return inclusive, unused_namespace_dict

#_in_subset = lambda subset, node: not subset or node in subset
_in_subset = lambda subset, node: subset is None or node in subset # rich's tweak


class _implementation:
    '''Implementation class for C14N. This accompanies a node during it's
    processing and includes the parameters and processing state.'''

    # Handler for each node type; populated during module instantiation.
    handlers = {}

    def __init__(self, node, write, **kw):
        '''Create and run the implementation.'''
        self.write = write
        self.subset = kw.get('subset')
        self.comments = kw.get('comments', 0)
        self.unsuppressedPrefixes = kw.get('unsuppressedPrefixes')
        nsdict = kw.get('nsdict', { 'xml': XMLNS.XML, 'xmlns': XMLNS.BASE })
        
        # Processing state.
        self.state = (nsdict, {'xml':''}, {}, {}) #0422
        
        if node.nodeType == Node.DOCUMENT_NODE:
            self._do_document(node)
        elif node.nodeType == Node.ELEMENT_NODE:
            self.documentOrder = _Element        # At document element
            if not _inclusive(self):
                inherited,unused = _inclusiveNamespacePrefixes(node, self._inherit_context(node), 
                                self.unsuppressedPrefixes)
                self._do_element(node, inherited, unused=unused)
            else:
                inherited = self._inherit_context(node)
                self._do_element(node, inherited)
        elif node.nodeType == Node.DOCUMENT_TYPE_NODE:
            pass
        else:
            raise TypeError, str(node)


    def _inherit_context(self, node):
        '''_inherit_context(self, node) -> list
        Scan ancestors of attribute and namespace context.  Used only
        for single element node canonicalization, not for subset
        canonicalization.'''

        # Collect the initial list of xml:foo attributes.
        xmlattrs = filter(_IN_XML_NS, _attrs(node))

        # Walk up and get all xml:XXX attributes we inherit.
        inherited, parent = [], node.parentNode
        while parent and parent.nodeType == Node.ELEMENT_NODE:
            for a in filter(_IN_XML_NS, _attrs(parent)):
                n = a.localName
                if n not in xmlattrs:
                    xmlattrs.append(n)
                    inherited.append(a)
            parent = parent.parentNode
        return inherited


    def _do_document(self, node):
        '''_do_document(self, node) -> None
        Process a document node. documentOrder holds whether the document
        element has been encountered such that PIs/comments can be written
        as specified.'''

        self.documentOrder = _LesserElement
        for child in node.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                self.documentOrder = _Element        # At document element
                self._do_element(child)
                self.documentOrder = _GreaterElement # After document element
            elif child.nodeType == Node.PROCESSING_INSTRUCTION_NODE:
                self._do_pi(child)
            elif child.nodeType == Node.COMMENT_NODE:
                self._do_comment(child)
            elif child.nodeType == Node.DOCUMENT_TYPE_NODE:
                pass
            else:
                raise TypeError, str(child)
    handlers[Node.DOCUMENT_NODE] = _do_document


    def _do_text(self, node):
        '''_do_text(self, node) -> None
        Process a text or CDATA node.  Render various special characters
        as their C14N entity representations.'''
        if not _in_subset(self.subset, node): return
        s = string.replace(node.data, "&", "&amp;")
        s = string.replace(s, "<", "&lt;")
        s = string.replace(s, ">", "&gt;")
        s = string.replace(s, "\015", "&#xD;")
        if s: self.write(s)
    handlers[Node.TEXT_NODE] = _do_text
    handlers[Node.CDATA_SECTION_NODE] = _do_text


    def _do_pi(self, node):
        '''_do_pi(self, node) -> None
        Process a PI node. Render a leading or trailing #xA if the
        document order of the PI is greater or lesser (respectively)
        than the document element.
        '''
        if not _in_subset(self.subset, node): return
        W = self.write
        if self.documentOrder == _GreaterElement: W('\n')
        W('<?')
        W(node.nodeName)
        s = node.data
        if s:
            W(' ')
            W(s)
        W('?>')
        if self.documentOrder == _LesserElement: W('\n')
    handlers[Node.PROCESSING_INSTRUCTION_NODE] = _do_pi


    def _do_comment(self, node):
        '''_do_comment(self, node) -> None
        Process a comment node. Render a leading or trailing #xA if the
        document order of the comment is greater or lesser (respectively)
        than the document element.
        '''
        if not _in_subset(self.subset, node): return
        if self.comments:
            W = self.write
            if self.documentOrder == _GreaterElement: W('\n')
            W('<!--')
            W(node.data)
            W('-->')
            if self.documentOrder == _LesserElement: W('\n')
    handlers[Node.COMMENT_NODE] = _do_comment


    def _do_attr(self, n, value):
        ''''_do_attr(self, node) -> None
        Process an attribute.'''

        W = self.write
        W(' ')
        W(n)
        W('="')
        s = string.replace(value, "&", "&amp;")
        s = string.replace(s, "<", "&lt;")
        s = string.replace(s, '"', '&quot;')
        s = string.replace(s, '\011', '&#x9')
        s = string.replace(s, '\012', '&#xA')
        s = string.replace(s, '\015', '&#xD')
        W(s)
        W('"')


    def _do_element(self, node, initial_other_attrs = [], unused = None):
        '''_do_element(self, node, initial_other_attrs = [], unused = {}) -> None
        Process an element (and its children).'''

        # Get state (from the stack) make local copies.
        #   ns_parent -- NS declarations in parent
        #   ns_rendered -- NS nodes rendered by ancestors
        #        ns_local -- NS declarations relevant to this element
        #   xml_attrs -- Attributes in XML namespace from parent
        #       xml_attrs_local -- Local attributes in XML namespace.
        #   ns_unused_inherited -- not rendered namespaces, used for exclusive 
        ns_parent, ns_rendered, xml_attrs = \
                self.state[0], self.state[1].copy(), self.state[2].copy() #0422
                
        ns_unused_inherited = unused
        if unused is None:
            ns_unused_inherited = self.state[3].copy()
            
        ns_local = ns_parent.copy()
        inclusive = _inclusive(self)
        xml_attrs_local = {}

        # Divide attributes into NS, XML, and others.
        other_attrs = []
        in_subset = _in_subset(self.subset, node)
        for a in initial_other_attrs + _attrs(node):
            if a.namespaceURI == XMLNS.BASE:
                n = a.nodeName
                if n == "xmlns:": n = "xmlns"        # DOM bug workaround
                ns_local[n] = a.nodeValue
            elif a.namespaceURI == XMLNS.XML:
                if inclusive or (in_subset and  _in_subset(self.subset, a)): #020925 Test to see if attribute node in subset
                    xml_attrs_local[a.nodeName] = a #0426
            else:
                if  _in_subset(self.subset, a):     #020925 Test to see if attribute node in subset
                    other_attrs.append(a)
                    
#                # TODO: exclusive, might need to define xmlns:prefix here
#                if not inclusive and a.prefix is not None and not ns_rendered.has_key('xmlns:%s' %a.prefix):
#                    ns_local['xmlns:%s' %a.prefix] = ??

            #add local xml:foo attributes to ancestor's xml:foo attributes
            xml_attrs.update(xml_attrs_local)

        # Render the node
        W, name = self.write, None
        if in_subset: 
            name = node.nodeName
            if not inclusive:
                if node.prefix is not None:
                    prefix = 'xmlns:%s' %node.prefix
                else:
                    prefix = 'xmlns'
                    
                if not ns_rendered.has_key(prefix) and not ns_local.has_key(prefix):
                    if not ns_unused_inherited.has_key(prefix):
                        raise RuntimeError,\
                            'For exclusive c14n, unable to map prefix "%s" in %s' %(
                            prefix, node)
                    
                    ns_local[prefix] = ns_unused_inherited[prefix]
                    del ns_unused_inherited[prefix]
                
            W('<')
            W(name)

            # Create list of NS attributes to render.
            ns_to_render = []
            for n,v in ns_local.items():

                # If default namespace is XMLNS.BASE or empty,
                # and if an ancestor was the same
                if n == "xmlns" and v in [ XMLNS.BASE, '' ] \
                and ns_rendered.get('xmlns') in [ XMLNS.BASE, '', None ]:
                    continue

                # "omit namespace node with local name xml, which defines
                # the xml prefix, if its string value is
                # http://www.w3.org/XML/1998/namespace."
                if n in ["xmlns:xml", "xml"] \
                and v in [ 'http://www.w3.org/XML/1998/namespace' ]:
                    continue


                # If not previously rendered
                # and it's inclusive  or utilized
                if (n,v) not in ns_rendered.items():
                    if inclusive or _utilized(n, node, other_attrs, self.unsuppressedPrefixes):
                        ns_to_render.append((n, v))
                    elif not inclusive:
                        ns_unused_inherited[n] = v

            # Sort and render the ns, marking what was rendered.
            ns_to_render.sort(_sorter_ns)
            for n,v in ns_to_render:
                self._do_attr(n, v)
                ns_rendered[n]=v    #0417

            # If exclusive or the parent is in the subset, add the local xml attributes
            # Else, add all local and ancestor xml attributes
            # Sort and render the attributes.
            if not inclusive or _in_subset(self.subset,node.parentNode):  #0426
                other_attrs.extend(xml_attrs_local.values())
            else:
                other_attrs.extend(xml_attrs.values())
            other_attrs.sort(_sorter)
            for a in other_attrs:
                self._do_attr(a.nodeName, a.value)
            W('>')

        # Push state, recurse, pop state.
        state, self.state = self.state, (ns_local, ns_rendered, xml_attrs, ns_unused_inherited)
        for c in _children(node):
            _implementation.handlers[c.nodeType](self, c)
        self.state = state

        if name: W('</%s>' % name)
    handlers[Node.ELEMENT_NODE] = _do_element


def Canonicalize(node, output=None, **kw):
    '''Canonicalize(node, output=None, **kw) -> UTF-8

    Canonicalize a DOM document/element node and all descendents.
    Return the text; if output is specified then output.write will
    be called to output the text and None will be returned
    Keyword parameters:
        nsdict: a dictionary of prefix:uri namespace entries
                assumed to exist in the surrounding context
        comments: keep comments if non-zero (default is 0)
        subset: Canonical XML subsetting resulting from XPath
                (default is [])
        unsuppressedPrefixes: do exclusive C14N, and this specifies the
                prefixes that should be inherited.
    '''
    if output:
        apply(_implementation, (node, output.write), kw)
    else:
        s = StringIO.StringIO()
        apply(_implementation, (node, s.write), kw)
        return s.getvalue()

########NEW FILE########
__FILENAME__ = logging
# Copyright (c) 2003, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of
# any required approvals from the U.S. Dept. of Energy).  All rights
# reserved. 
#
"""Logging"""
ident = "$Id$"
import os, sys

WARN = 1
DEBUG = 2


class ILogger:
    '''Logger interface, by default this class
    will be used and logging calls are no-ops.
    '''
    level = 0
    def __init__(self, msg):
        return
    def warning(self, *args, **kw):
        return
    def debug(self, *args, **kw):
        return
    def error(self, *args, **kw):
        return
    def setLevel(cls, level):
        cls.level = level
    setLevel = classmethod(setLevel)
    
    debugOn = lambda self: self.level >= DEBUG
    warnOn = lambda self: self.level >= WARN
    

class BasicLogger(ILogger):
    last = ''
    
    def __init__(self, msg, out=sys.stdout):
        self.msg, self.out = msg, out

    def warning(self, msg, *args, **kw):
        if self.warnOn() is False: return
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %self.WARN,
        print >>self, msg %args
    WARN = '[WARN]'
    def debug(self, msg, *args, **kw):
        if self.debugOn() is False: return
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %self.DEBUG,
        print >>self, msg %args
    DEBUG = '[DEBUG]'
    def error(self, msg, *args, **kw):
        if BasicLogger.last != self.msg:
            BasicLogger.last = self.msg
            print >>self, "---- ", self.msg, " ----"
        print >>self, "    %s  " %self.ERROR,
        print >>self, msg %args
    ERROR = '[ERROR]'

    def write(self, *args):
        '''Write convenience function; writes strings.
        '''
        for s in args: self.out.write(s)
        event = ''.join(*args)


_LoggerClass = BasicLogger

class GridLogger(ILogger):
    def debug(self, msg, *args, **kw):
        kw['component'] = self.msg
        gridLog(event=msg %args, level='DEBUG', **kw)

    def warning(self, msg, *args, **kw):
        kw['component'] = self.msg
        gridLog(event=msg %args, level='WARNING', **kw)

    def error(self, msg, *args, **kw):
        kw['component'] = self.msg
        gridLog(event=msg %args, level='ERROR', **kw)


# 
# Registry of send functions for gridLog
# 
GLRegistry = {}

class GLRecord(dict):
    """Grid Logging Best Practices Record, Distributed Logging Utilities

    The following names are reserved:

    event -- log event name
        Below is EBNF for the event name part of a log message.
            name	= <nodot> ( "." <name> )? 
            nodot	= {RFC3896-chars except "."}

        Suffixes:
            start: Immediately before the first action in a task.
            end: Immediately after the last action in a task (that succeeded).
            error: an error condition that does not correspond to an end event.

    ts -- timestamp
    level -- logging level (see levels below)
    status -- integer status code
    gid -- global grid identifier 
    gid, cgid -- parent/child identifiers
    prog -- program name


    More info: http://www.cedps.net/wiki/index.php/LoggingBestPractices#Python

    reserved -- list of reserved names, 
    omitname -- list of reserved names, output only values ('ts', 'event',)
    levels -- dict of levels and description
    """
    reserved = ('ts', 'event', 'level', 'status', 'gid', 'prog')
    omitname = ()
    levels = dict(FATAL='Component cannot continue, or system is unusable.',
        ALERT='Action must be taken immediately.',
        CRITICAL='Critical conditions (on the system).',
        ERROR='Errors in the component; not errors from elsewhere.',
        WARNING='Problems that are recovered from, usually.',
        NOTICE='Normal but significant condition.',
        INFO='Informational messages that would be useful to a deployer or administrator.',
        DEBUG='Lower level information concerning program logic decisions, internal state, etc.',
        TRACE='Finest granularity, similar to "stepping through" the component or system.',
    )

    def __init__(self, date=None, **kw):
        kw['ts'] = date or self.GLDate()
        kw['gid'] = kw.get('gid') or os.getpid()
        dict.__init__(self, kw)

    def __str__(self):
        """
        """
        from cStringIO import StringIO
        s = StringIO(); n = " "
        reserved = self.reserved; omitname = self.omitname; levels = self.levels

        for k in ( list(filter(lambda i: self.has_key(i), reserved)) + 
            list(filter(lambda i: i not in reserved, self.keys()))
        ):
            v = self[k]
            if k in omitname: 
                s.write( "%s " %self.format[type(v)](v) )
                continue

            if k == reserved[2] and v not in levels:
                pass

            s.write( "%s=%s " %(k, self.format[type(v)](v) ) )

        s.write("\n")
        return s.getvalue()

    class GLDate(str):
        """Grid logging Date Format
        all timestamps should all be in the same time zone (UTC). 
        Grid timestamp value format that is a highly readable variant of the ISO8601 time standard [1]:

	YYYY-MM-DDTHH:MM:SS.SSSSSSZ 

        """
        def __new__(self, args=None):
            """args -- datetime (year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])
            """
            import datetime
            args = args or datetime.datetime.utcnow()
            l = (args.year, args.month, args.day, args.hour, args.minute, args.second, 
                 args.microsecond, args.tzinfo or 'Z')

            return str.__new__(self, "%04d-%02d-%02dT%02d:%02d:%02d.%06d%s" %l)

    format = { int:str, float:lambda x: "%lf" % x, long:str, str:lambda x:x,
        unicode:str, GLDate:str, }


def gridLog(**kw):
    """Send GLRecord, Distributed Logging Utilities
    If the scheme is passed as a keyword parameter
    the value is expected to be a callable function
    that takes 2 parameters: url, outputStr

    GRIDLOG_ON   -- turn grid logging on
    GRIDLOG_DEST -- provide URL destination
    """
    import os

    if not bool( int(os.environ.get('GRIDLOG_ON', 0)) ):
        return

    url = os.environ.get('GRIDLOG_DEST')
    if url is None: 
        return

    ## NOTE: urlparse problem w/customized schemes 
    try:
        scheme = url[:url.find('://')]
        send = GLRegistry[scheme]
        send( url, str(GLRecord(**kw)), )
    except Exception, ex:
        print >>sys.stderr, "*** gridLog failed -- %s" %(str(kw))


def sendUDP(url, outputStr):
    from socket import socket, AF_INET, SOCK_DGRAM
    idx1 = url.find('://') + 3; idx2 = url.find('/', idx1)
    if idx2 < idx1: idx2 = len(url)
    netloc = url[idx1:idx2]
    host,port = (netloc.split(':')+[80])[0:2]
    socket(AF_INET, SOCK_DGRAM).sendto( outputStr, (host,int(port)), )

def writeToFile(url, outputStr):
    print >> open(url.split('://')[1], 'a+'), outputStr

GLRegistry["gridlog-udp"] = sendUDP
GLRegistry["file"] = writeToFile


def setBasicLogger():
    '''Use Basic Logger. 
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(0)

def setGridLogger():
    '''Use GridLogger for all logging events.
    '''
    setLoggerClass(GridLogger)

def setBasicLoggerWARN():
    '''Use Basic Logger.
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(WARN)

def setBasicLoggerDEBUG():
    '''Use Basic Logger.
    '''
    setLoggerClass(BasicLogger)
    BasicLogger.setLevel(DEBUG)

def setLoggerClass(loggingClass):
    '''Set Logging Class.
    '''

def setLoggerClass(loggingClass):
    '''Set Logging Class.
    '''
    assert issubclass(loggingClass, ILogger), 'loggingClass must subclass ILogger'
    global _LoggerClass
    _LoggerClass = loggingClass

def setLevel(level=0):
    '''Set Global Logging Level.
    '''
    ILogger.level = level

def getLevel():
    return ILogger.level

def getLogger(msg):
    '''Return instance of Logging class.
    '''
    return _LoggerClass(msg)



########NEW FILE########
__FILENAME__ = MIMEAttachment
#TODO add the license
#I had to rewrite this class because the python MIME email.mime (version 2.5)
#are buggy, they use \n instead \r\n for new line which is not compliant
#to standard!
# http://bugs.python.org/issue5525

#TODO do not load all the message in memory stream it from the disk

import re
import random
import sys


#new line
NL='\r\n'

_width = len(repr(sys.maxint-1))
_fmt = '%%0%dd' % _width

class MIMEMessage:

    def __init__(self):
        self._files = []
        self._xmlMessage = ""
        self._startCID = ""
        self._boundary = ""

    def makeBoundary(self):
        #create the boundary 
        msgparts = []
        msgparts.append(self._xmlMessage)
        for i in self._files:
            msgparts.append(i.read())
        #this sucks, all in memory
        alltext = NL.join(msgparts)
        self._boundary  = _make_boundary(alltext)
        #maybe I can save some memory
        del alltext
        del msgparts
        self._startCID =  "<" + (_fmt % random.randrange(sys.maxint)) + (_fmt % random.randrange(sys.maxint)) + ">"


    def toString(self):
        '''it return a string with the MIME message'''
        if len(self._boundary) == 0:
            #the makeBoundary hasn't been called yet
            self.makeBoundary()
        #ok we have everything let's start to spit the message out
        #first the XML
        returnstr = NL + "--" + self._boundary + NL
        returnstr += "Content-Type: text/xml; charset=\"us-ascii\"" + NL
        returnstr += "Content-Transfer-Encoding: 7bit" + NL
        returnstr += "Content-Id: " + self._startCID + NL + NL
        returnstr += self._xmlMessage + NL
        #then the files
        for file in self._files:
            returnstr += "--" + self._boundary + NL
            returnstr += "Content-Type: application/octet-stream" + NL
            returnstr += "Content-Transfer-Encoding: binary" + NL
            returnstr += "Content-Id: <" + str(id(file)) + ">" + NL + NL
            file.seek(0)
            returnstr += file.read() + NL
        #closing boundary
        returnstr += "--" + self._boundary + "--" + NL 
        return returnstr

    def attachFile(self, file):
        '''
        it adds a file to this attachment
        '''
        self._files.append(file)

    def addXMLMessage(self, xmlMessage):
        '''
        it adds the XML message. we can have only one XML SOAP message
        '''
        self._xmlMessage = xmlMessage

    def getBoundary(self):
        '''
        this function returns the string used in the mime message as a 
        boundary. First the write method as to be called
        '''
        return self._boundary

    def getStartCID(self):
        '''
        This function returns the CID of the XML message
        '''
        return self._startCID


def _make_boundary(text=None):
    #some code taken from python stdlib
    # Craft a random boundary.  If text is given, ensure that the chosen
    # boundary doesn't appear in the text.
    token = random.randrange(sys.maxint)
    boundary = ('=' * 10) + (_fmt % token) + '=='
    if text is None:
        return boundary
    b = boundary
    counter = 0
    while True:
        cre = re.compile('^--' + re.escape(b) + '(--)?$', re.MULTILINE)
        if not cre.search(text):
            break
        b = boundary + '.' + str(counter)
        counter += 1
    return b


########NEW FILE########
__FILENAME__ = Namespaces
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
"""Namespace module, so you don't need PyXML 
"""

ident = "$Id$"
try:
    from xml.ns import SOAP, SCHEMA, WSDL, XMLNS, DSIG, ENCRYPTION
    DSIG.C14N       = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    
except:
    class SOAP:
        ENV         = "http://schemas.xmlsoap.org/soap/envelope/"
        ENC         = "http://schemas.xmlsoap.org/soap/encoding/"
        ACTOR_NEXT  = "http://schemas.xmlsoap.org/soap/actor/next"

    class SCHEMA:
        XSD1        = "http://www.w3.org/1999/XMLSchema"
        XSD2        = "http://www.w3.org/2000/10/XMLSchema"
        XSD3        = "http://www.w3.org/2001/XMLSchema"
        XSD_LIST    = [ XSD1, XSD2, XSD3]
        XSI1        = "http://www.w3.org/1999/XMLSchema-instance"
        XSI2        = "http://www.w3.org/2000/10/XMLSchema-instance"
        XSI3        = "http://www.w3.org/2001/XMLSchema-instance"
        XSI_LIST    = [ XSI1, XSI2, XSI3 ]
        BASE        = XSD3

    class WSDL:
        BASE        = "http://schemas.xmlsoap.org/wsdl/"
        BIND_HTTP   = "http://schemas.xmlsoap.org/wsdl/http/"
        BIND_MIME   = "http://schemas.xmlsoap.org/wsdl/mime/"
        BIND_SOAP   = "http://schemas.xmlsoap.org/wsdl/soap/"
        BIND_SOAP12 = "http://schemas.xmlsoap.org/wsdl/soap12/"

    class XMLNS:
        BASE        = "http://www.w3.org/2000/xmlns/"
        XML         = "http://www.w3.org/XML/1998/namespace"
        HTML        = "http://www.w3.org/TR/REC-html40"

    class DSIG:
        BASE         = "http://www.w3.org/2000/09/xmldsig#"
        C14N         = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        C14N_COMM    = "http://www.w3.org/TR/2000/CR-xml-c14n-20010315#WithComments"
        C14N_EXCL    = "http://www.w3.org/2001/10/xml-exc-c14n#"
        DIGEST_MD2   = "http://www.w3.org/2000/09/xmldsig#md2"
        DIGEST_MD5   = "http://www.w3.org/2000/09/xmldsig#md5"
        DIGEST_SHA1  = "http://www.w3.org/2000/09/xmldsig#sha1"
        ENC_BASE64   = "http://www.w3.org/2000/09/xmldsig#base64"
        ENVELOPED    = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
        HMAC_SHA1    = "http://www.w3.org/2000/09/xmldsig#hmac-sha1"
        SIG_DSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#dsa-sha1"
        SIG_RSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
        XPATH        = "http://www.w3.org/TR/1999/REC-xpath-19991116"
        XSLT         = "http://www.w3.org/TR/1999/REC-xslt-19991116"

    class ENCRYPTION:
        BASE    = "http://www.w3.org/2001/04/xmlenc#"
        BLOCK_3DES    = "http://www.w3.org/2001/04/xmlenc#des-cbc"
        BLOCK_AES128    = "http://www.w3.org/2001/04/xmlenc#aes128-cbc"
        BLOCK_AES192    = "http://www.w3.org/2001/04/xmlenc#aes192-cbc"
        BLOCK_AES256    = "http://www.w3.org/2001/04/xmlenc#aes256-cbc"
        DIGEST_RIPEMD160    = "http://www.w3.org/2001/04/xmlenc#ripemd160"
        DIGEST_SHA256    = "http://www.w3.org/2001/04/xmlenc#sha256"
        DIGEST_SHA512    = "http://www.w3.org/2001/04/xmlenc#sha512"
        KA_DH    = "http://www.w3.org/2001/04/xmlenc#dh"
        KT_RSA_1_5    = "http://www.w3.org/2001/04/xmlenc#rsa-1_5"
        KT_RSA_OAEP    = "http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p"
        STREAM_ARCFOUR    = "http://www.w3.org/2001/04/xmlenc#arcfour"
        WRAP_3DES    = "http://www.w3.org/2001/04/xmlenc#kw-3des"
        WRAP_AES128    = "http://www.w3.org/2001/04/xmlenc#kw-aes128"
        WRAP_AES192    = "http://www.w3.org/2001/04/xmlenc#kw-aes192"
        WRAP_AES256    = "http://www.w3.org/2001/04/xmlenc#kw-aes256"


class WSRF_V1_2:
    '''OASIS WSRF Specifications Version 1.2
    '''
    class LIFETIME:
        XSD_DRAFT1 = "http://docs.oasis-open.org/wsrf/2004/06/wsrf-WS-ResourceLifetime-1.2-draft-01.xsd"
        XSD_DRAFT4 = "http://docs.oasis-open.org/wsrf/2004/11/wsrf-WS-ResourceLifetime-1.2-draft-04.xsd"

        WSDL_DRAFT1 = "http://docs.oasis-open.org/wsrf/2004/06/wsrf-WS-ResourceLifetime-1.2-draft-01.wsdl"
        WSDL_DRAFT4 = "http://docs.oasis-open.org/wsrf/2004/11/wsrf-WS-ResourceLifetime-1.2-draft-04.wsdl"
        LATEST = WSDL_DRAFT4
        WSDL_LIST = (WSDL_DRAFT1, WSDL_DRAFT4)
        XSD_LIST = (XSD_DRAFT1, XSD_DRAFT4)

    class PROPERTIES:
        XSD_DRAFT1 = "http://docs.oasis-open.org/wsrf/2004/06/wsrf-WS-ResourceProperties-1.2-draft-01.xsd"
        XSD_DRAFT5 = "http://docs.oasis-open.org/wsrf/2004/11/wsrf-WS-ResourceProperties-1.2-draft-05.xsd"

        WSDL_DRAFT1 = "http://docs.oasis-open.org/wsrf/2004/06/wsrf-WS-ResourceProperties-1.2-draft-01.wsdl"
        WSDL_DRAFT5 = "http://docs.oasis-open.org/wsrf/2004/11/wsrf-WS-ResourceProperties-1.2-draft-05.wsdl"
        LATEST = WSDL_DRAFT5
        WSDL_LIST = (WSDL_DRAFT1, WSDL_DRAFT5)
        XSD_LIST = (XSD_DRAFT1, XSD_DRAFT5)

    class BASENOTIFICATION:
        XSD_DRAFT1 = "http://docs.oasis-open.org/wsn/2004/06/wsn-WS-BaseNotification-1.2-draft-01.xsd"

        WSDL_DRAFT1 = "http://docs.oasis-open.org/wsn/2004/06/wsn-WS-BaseNotification-1.2-draft-01.wsdl"
        LATEST = WSDL_DRAFT1
        WSDL_LIST = (WSDL_DRAFT1,)
        XSD_LIST = (XSD_DRAFT1,)

    class BASEFAULTS:
        XSD_DRAFT1 = "http://docs.oasis-open.org/wsrf/2004/06/wsrf-WS-BaseFaults-1.2-draft-01.xsd"
        XSD_DRAFT3 = "http://docs.oasis-open.org/wsrf/2004/11/wsrf-WS-BaseFaults-1.2-draft-03.xsd"
        #LATEST = DRAFT3
        #WSDL_LIST = (WSDL_DRAFT1, WSDL_DRAFT3)
        XSD_LIST = (XSD_DRAFT1, XSD_DRAFT3)

WSRF = WSRF_V1_2
WSRFLIST = (WSRF_V1_2,)


class OASIS:
    '''URLs for Oasis specifications
    '''
    WSSE    = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
    UTILITY = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
    
    class X509TOKEN:
        Base64Binary = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
        STRTransform = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0"
        PKCS7 = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#PKCS7"
        X509 = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509"
        X509PKIPathv1 = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509PKIPathv1"
        X509v3SubjectKeyIdentifier = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3SubjectKeyIdentifier"
        
    LIFETIME = WSRF_V1_2.LIFETIME.XSD_DRAFT1
    PROPERTIES = WSRF_V1_2.PROPERTIES.XSD_DRAFT1
    BASENOTIFICATION = WSRF_V1_2.BASENOTIFICATION.XSD_DRAFT1
    BASEFAULTS = WSRF_V1_2.BASEFAULTS.XSD_DRAFT1


class APACHE:
    '''This name space is defined by AXIS and it is used for the TC in TCapache.py,
    Map and file attachment (DataHandler)
    '''
    AXIS_NS = "http://xml.apache.org/xml-soap"


class WSTRUST:
    BASE = "http://schemas.xmlsoap.org/ws/2004/04/trust"
    ISSUE = "http://schemas.xmlsoap.org/ws/2004/04/trust/Issue"

class WSSE:
    BASE    = "http://schemas.xmlsoap.org/ws/2002/04/secext"
    TRUST   = WSTRUST.BASE


class WSU:
    BASE    = "http://schemas.xmlsoap.org/ws/2002/04/utility"
    UTILITY = "http://schemas.xmlsoap.org/ws/2002/07/utility"


class WSR:
    PROPERTIES = "http://www.ibm.com/xmlns/stdwip/web-services/WS-ResourceProperties"
    LIFETIME   = "http://www.ibm.com/xmlns/stdwip/web-services/WS-ResourceLifetime"


class WSA200508:
    ADDRESS    = "http://www.w3.org/2005/08/addressing"
    ANONYMOUS  = "%s/anonymous" %ADDRESS
    FAULT      = "%s/fault" %ADDRESS

class WSA200408:
    ADDRESS    = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
    ANONYMOUS  = "%s/role/anonymous" %ADDRESS
    FAULT      = "%s/fault" %ADDRESS

class WSA200403:
    ADDRESS    = "http://schemas.xmlsoap.org/ws/2004/03/addressing"
    ANONYMOUS  = "%s/role/anonymous" %ADDRESS
    FAULT      = "%s/fault" %ADDRESS

class WSA200303:
    ADDRESS    = "http://schemas.xmlsoap.org/ws/2003/03/addressing"
    ANONYMOUS  = "%s/role/anonymous" %ADDRESS
    FAULT      = None


WSA = WSA200408
WSA_LIST = (WSA200508, WSA200408, WSA200403, WSA200303)

class _WSAW(str):
    """ Define ADDRESS attribute to be compatible with WSA* layout """
    ADDRESS = property(lambda s: s)

WSAW200605 = _WSAW("http://www.w3.org/2006/05/addressing/wsdl")

WSAW_LIST = (WSAW200605,)
 
class WSP:
    POLICY = "http://schemas.xmlsoap.org/ws/2002/12/policy"

class BEA:
    SECCONV = "http://schemas.xmlsoap.org/ws/2004/04/sc"
    SCTOKEN = "http://schemas.xmlsoap.org/ws/2004/04/security/sc/sct"

class GLOBUS:
    SECCONV = "http://wsrf.globus.org/core/2004/07/security/secconv"
    CORE    = "http://www.globus.org/namespaces/2004/06/core"
    SIG     = "http://www.globus.org/2002/04/xmlenc#gssapi-sign"
    TOKEN   = "http://www.globus.org/ws/2004/09/security/sc#GSSAPI_GSI_TOKEN"

ZSI_SCHEMA_URI = 'http://www.zolera.com/schemas/ZSI/'

########NEW FILE########
__FILENAME__ = test_t1
############################################################################
# Joshua R. Boverhof, David W. Robertson, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################
import unittest
import test_wsdl
import utils

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(test_wsdl.makeTestSuite("services_by_file"))
    return suite

def main():
    loader = utils.MatchTestLoader(True, None, "makeTestSuite")
    unittest.main(defaultTest="makeTestSuite", testLoader=loader)

if __name__ == "__main__" : main()
    


########NEW FILE########
__FILENAME__ = test_wsdl
#!/usr/bin/env python

############################################################################
# Joshua R. Boverhof, David W. Robertson, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################

import sys, unittest
import ConfigParser
import os
from wstools.Utility import DOM
from wstools.WSDLTools import WSDLReader
from wstools.TimeoutSocket import TimeoutError

from wstools import tests
cwd = os.path.dirname(tests.__file__)

class WSDLToolsTestCase(unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.path = nameGenerator.next()
        print self.path
        sys.stdout.flush()

    def __str__(self):
        teststr = unittest.TestCase.__str__(self)
        if hasattr(self, "path"):
            return "%s: %s" % (teststr, self.path )
        else:
            return "%s" % (teststr)

    def checkWSDLCollection(self, tag_name, component, key='name'):
        if self.wsdl is None:
            return
        definition = self.wsdl.document.documentElement
        version = DOM.WSDLUriToVersion(definition.namespaceURI)
        nspname = DOM.GetWSDLUri(version)
        for node in DOM.getElements(definition, tag_name, nspname):
            name = DOM.getAttr(node, key)
            comp = component[name]
            self.failUnlessEqual(eval('comp.%s' %key), name)

    def checkXSDCollection(self, tag_name, component, node, key='name'):
        for cnode in DOM.getElements(node, tag_name):
            name = DOM.getAttr(cnode, key)
            component[name] 

    def test_all(self):
        try:
            if self.path[:7] == 'http://':
                self.wsdl = WSDLReader().loadFromURL(self.path)
            else:
                self.wsdl = WSDLReader().loadFromFile(self.path)

        except TimeoutError:
            print "connection timed out"
            sys.stdout.flush()
            return
        except:
            self.path = self.path + ": load failed, unable to start"
            raise

        try:
            self.checkWSDLCollection('service', self.wsdl.services)
        except:
            self.path = self.path + ": wsdl.services"
            raise

        try:
            self.checkWSDLCollection('message', self.wsdl.messages)
        except:
            self.path = self.path + ": wsdl.messages"
            raise

        try:
            self.checkWSDLCollection('portType', self.wsdl.portTypes)
        except:
            self.path = self.path + ": wsdl.portTypes"
            raise

        try:
            self.checkWSDLCollection('binding', self.wsdl.bindings)
        except:
            self.path = self.path + ": wsdl.bindings"
            raise

        try:
            self.checkWSDLCollection('import', self.wsdl.imports, key='namespace')
        except:
            self.path = self.path + ": wsdl.imports"
            raise

        try:
            for key in self.wsdl.types.keys(): 
                schema = self.wsdl.types[key]
                self.failUnlessEqual(key, schema.getTargetNamespace())

            definition = self.wsdl.document.documentElement
            version = DOM.WSDLUriToVersion(definition.namespaceURI)
            nspname = DOM.GetWSDLUri(version)
            for node in DOM.getElements(definition, 'types', nspname):
                for snode in DOM.getElements(node, 'schema'):
                    tns = DOM.findTargetNS(snode)
                    schema = self.wsdl.types[tns]
                    self.schemaAttributesDeclarations(schema, snode)
                    self.schemaAttributeGroupDeclarations(schema, snode)
                    self.schemaElementDeclarations(schema, snode)
                    self.schemaTypeDefinitions(schema, snode)
        except:
            self.path = self.path + ": wsdl.types"
            raise

        if self.wsdl.extensions:
            print 'No check for WSDLTools(%s) Extensions:' %(self.wsdl.name)
            for ext in self.wsdl.extensions: print '\t', ext

    def schemaAttributesDeclarations(self, schema, node):
        self.checkXSDCollection('attribute', schema.attr_decl, node)

    def schemaAttributeGroupDeclarations(self, schema, node):
        self.checkXSDCollection('group', schema.attr_groups, node)

    def schemaElementDeclarations(self, schema, node):
        self.checkXSDCollection('element', schema.elements, node)

    def schemaTypeDefinitions(self, schema, node):
        self.checkXSDCollection('complexType', schema.types, node)
        self.checkXSDCollection('simpleType', schema.types, node)


def setUpOptions(section):
    cp = ConfigParser.ConfigParser()
    cp.read(cwd+'/config.txt')
    if not cp.sections():
        print 'fatal error:  configuration file config.txt not present'
        sys.exit(0)
    if not cp.has_section(section):
        print '%s section not present in configuration file, exiting' % section
        sys.exit(0)
    return cp, len(cp.options(section))

def getOption(cp, section):
    for name, value in cp.items(section):
        yield value
    
def makeTestSuite(section='services_by_file'):
    global nameGenerator

    cp, numTests = setUpOptions(section)
    nameGenerator = getOption(cp, section)
    suite = unittest.TestSuite()
    for i in range(0, numTests):
        suite.addTest(unittest.makeSuite(WSDLToolsTestCase, 'test_'))
    return suite


def main():
    unittest.main(defaultTest="makeTestSuite")
                  

if __name__ == "__main__" : main()

########NEW FILE########
__FILENAME__ = test_wstools
#!/usr/bin/env python

############################################################################
# Joshua R. Boverhof, David W. Robertson, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################

import unittest, tarfile, os, ConfigParser
import test_wsdl


SECTION='files'
CONFIG_FILE = 'config.txt'

def extractFiles(section, option):
    config = ConfigParser.ConfigParser()
    config.read(CONFIG_FILE)
    archives = config.get(section, option)
    archives = eval(archives)
    for file in archives:
        tar = tarfile.open(file)
        if not os.access(tar.membernames[0], os.R_OK):
            for i in tar.getnames(): 
                tar.extract(i)

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(test_wsdl.makeTestSuite("services_by_file"))
    return suite

def main():
    extractFiles(SECTION, 'archives')
    unittest.main(defaultTest="makeTestSuite")

if __name__ == "__main__" : main()
    


########NEW FILE########
__FILENAME__ = test_wstools_net
#!/usr/bin/env python

############################################################################
# Joshua R. Boverhof, David W. Robertson, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################
import unittest
import test_wsdl

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(test_wsdl.makeTestSuite("services_by_http"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == "__main__" : main()
    


########NEW FILE########
__FILENAME__ = TimeoutSocket
"""Based on code from timeout_socket.py, with some tweaks for compatibility.
   These tweaks should really be rolled back into timeout_socket, but it's
   not totally clear who is maintaining it at this point. In the meantime,
   we'll use a different module name for our tweaked version to avoid any
   confusion.

   The original timeout_socket is by:

	Scott Cotton <scott@chronis.pobox.com>
	Lloyd Zusman <ljz@asfast.com>
	Phil Mayes <pmayes@olivebr.com>
	Piers Lauder <piers@cs.su.oz.au>
	Radovan Garabik <garabik@melkor.dnp.fmph.uniba.sk>
"""

ident = "$Id$"

import string, socket, select, errno

WSAEINVAL = getattr(errno, 'WSAEINVAL', 10022)


class TimeoutSocket:
    """A socket imposter that supports timeout limits."""

    def __init__(self, timeout=20, sock=None):
        self.timeout = float(timeout)
        self.inbuf = ''
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = sock
        self.sock.setblocking(0)
        self._rbuf = ''
        self._wbuf = ''

    def __getattr__(self, name):
        # Delegate to real socket attributes.
        return getattr(self.sock, name)

    def connect(self, *addr):
        timeout = self.timeout
        sock = self.sock
        try:
            # Non-blocking mode
            sock.setblocking(0)
            apply(sock.connect, addr)
            sock.setblocking(timeout != 0)
            return 1
        except socket.error,why:
            if not timeout:
                raise
            sock.setblocking(1)
            if len(why.args) == 1:
                code = 0
            else:
                code, why = why
            if code not in (
                errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK
                ):
                raise
            r,w,e = select.select([],[sock],[],timeout)
            if w:
                try:
                    apply(sock.connect, addr)
                    return 1
                except socket.error,why:
                    if len(why.args) == 1:
                        code = 0
                    else:
                        code, why = why
                    if code in (errno.EISCONN, WSAEINVAL):
                        return 1
                    raise
        raise TimeoutError('socket connect() timeout.')

    def send(self, data, flags=0):
        total = len(data)
        next = 0
        while 1:
            r, w, e = select.select([],[self.sock], [], self.timeout)
            if w:
                buff = data[next:next + 8192]
                sent = self.sock.send(buff, flags)
                next = next + sent
                if next == total:
                    return total
                continue
            raise TimeoutError('socket send() timeout.')

    def recv(self, amt, flags=0):
        if select.select([self.sock], [], [], self.timeout)[0]:
            return self.sock.recv(amt, flags)
        raise TimeoutError('socket recv() timeout.')

    buffsize = 4096
    handles = 1

    def makefile(self, mode="r", buffsize=-1):
        self.handles = self.handles + 1
        self.mode = mode
        return self

    def close(self):
        self.handles = self.handles - 1
        if self.handles == 0 and self.sock.fileno() >= 0:
            self.sock.close()

    def read(self, n=-1):
        if not isinstance(n, type(1)):
            n = -1
        if n >= 0:
            k = len(self._rbuf)
            if n <= k:
                data = self._rbuf[:n]
                self._rbuf = self._rbuf[n:]
                return data
            n = n - k
            L = [self._rbuf]
            self._rbuf = ""
            while n > 0:
                new = self.recv(max(n, self.buffsize))
                if not new: break
                k = len(new)
                if k > n:
                    L.append(new[:n])
                    self._rbuf = new[n:]
                    break
                L.append(new)
                n = n - k
            return "".join(L)
        k = max(4096, self.buffsize)
        L = [self._rbuf]
        self._rbuf = ""
        while 1:
            new = self.recv(k)
            if not new: break
            L.append(new)
            k = min(k*2, 1024**2)
        return "".join(L)

    def readline(self, limit=-1):
        data = ""
        i = self._rbuf.find('\n')
        while i < 0 and not (0 < limit <= len(self._rbuf)):
            new = self.recv(self.buffsize)
            if not new: break
            i = new.find('\n')
            if i >= 0: i = i + len(self._rbuf)
            self._rbuf = self._rbuf + new
        if i < 0: i = len(self._rbuf)
        else: i = i+1
        if 0 <= limit < len(self._rbuf): i = limit
        data, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return data

    def readlines(self, sizehint = 0):
        total = 0
        list = []
        while 1:
            line = self.readline()
            if not line: break
            list.append(line)
            total += len(line)
            if sizehint and total >= sizehint:
                break
        return list

    def writelines(self, list):
        self.send(''.join(list))

    def write(self, data):
        self.send(data)

    def flush(self):
        pass


class TimeoutError(Exception):
    pass

########NEW FILE########
__FILENAME__ = UserTuple
"""
A more or less complete user-defined wrapper around tuple objects.
Adapted version of the standard library's UserList.

Taken from Stefan Schwarzer's ftputil library, available at
<http://www.ndh.net/home/sschwarzer/python/python_software.html>, and used under this license:




Copyright (C) 1999, Stefan Schwarzer 
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

- Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

- Neither the name of the above author nor the names of the
  contributors to the software may be used to endorse or promote
  products derived from this software without specific prior written
  permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""




# $Id$

#XXX tuple instances (in Python 2.2) contain also:
#   __class__, __delattr__, __getattribute__, __hash__, __new__,
#   __reduce__, __setattr__, __str__
# What about these?

class UserTuple:
    def __init__(self, inittuple=None):
        self.data = ()
        if inittuple is not None:
            # XXX should this accept an arbitrary sequence?
            if type(inittuple) == type(self.data):
                self.data = inittuple
            elif isinstance(inittuple, UserTuple):
                # this results in
                #   self.data is inittuple.data
                # but that's ok for tuples because they are
                # immutable. (Builtin tuples behave the same.)
                self.data = inittuple.data[:]
            else:
                # the same applies here; (t is tuple(t)) == 1
                self.data = tuple(inittuple)
    def __repr__(self): return repr(self.data)
    def __lt__(self, other): return self.data <  self.__cast(other)
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __ne__(self, other): return self.data != self.__cast(other)
    def __gt__(self, other): return self.data >  self.__cast(other)
    def __ge__(self, other): return self.data >= self.__cast(other)
    def __cast(self, other):
        if isinstance(other, UserTuple): return other.data
        else: return other
    def __cmp__(self, other):
        return cmp(self.data, self.__cast(other))
    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]
    def __getslice__(self, i, j):
        i = max(i, 0); j = max(j, 0)
        return self.__class__(self.data[i:j])
    def __add__(self, other):
        if isinstance(other, UserTuple):
            return self.__class__(self.data + other.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(self.data + other)
        else:
            return self.__class__(self.data + tuple(other))
    # dir( () ) contains no __radd__ (at least in Python 2.2)
    def __mul__(self, n):
        return self.__class__(self.data*n)
    __rmul__ = __mul__


########NEW FILE########
__FILENAME__ = Utility
# Copyright (c) 2003, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of
# any required approvals from the U.S. Dept. of Energy).  All rights
# reserved. 
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.

ident = "$Id$"

import sys, types, httplib, urllib, socket, weakref
from os.path import isfile
from string import join, strip, split
from UserDict import UserDict
from cStringIO import StringIO
from TimeoutSocket import TimeoutSocket, TimeoutError
from urlparse import urlparse
from httplib import HTTPConnection, HTTPSConnection
from exceptions import Exception
try:
    from ZSI import _get_idstr
except:
    def _get_idstr(pyobj):
        '''Python 2.3.x generates a FutureWarning for negative IDs, so
        we use a different prefix character to ensure uniqueness, and
        call abs() to avoid the warning.'''
        x = id(pyobj)
        if x < 0:
            return 'x%x' % abs(x)
        return 'o%x' % x

import xml.dom.minidom
from xml.dom import Node

import logging
from c14n import Canonicalize
from Namespaces import SCHEMA, SOAP, XMLNS, ZSI_SCHEMA_URI


try:
    from xml.dom.ext import SplitQName
except:
    def SplitQName(qname):
        '''SplitQName(qname) -> (string, string)
        
           Split Qualified Name into a tuple of len 2, consisting 
           of the prefix and the local name.  
    
           (prefix, localName)
        
           Special Cases:
               xmlns -- (localName, 'xmlns')
               None -- (None, localName)
        '''
        
        l = qname.split(':')
        if len(l) == 1:
            l.insert(0, None)
        elif len(l) == 2:
            if l[0] == 'xmlns':
                l.reverse()
        else:
            return
        return tuple(l)

#
# python2.3 urllib.basejoin does not remove current directory ./
# from path and this causes problems on subsequent basejoins.
#
basejoin = urllib.basejoin
if sys.version_info[0:2] < (2, 4, 0, 'final', 0)[0:2]:
    #basejoin = lambda base,url: urllib.basejoin(base,url.lstrip('./'))
    token = './'
    def basejoin(base, url): 
        if url.startswith(token) is True:
            return urllib.basejoin(base,url[2:])
        return urllib.basejoin(base,url)

class NamespaceError(Exception):
    """Used to indicate a Namespace Error."""


class RecursionError(Exception):
    """Used to indicate a HTTP redirect recursion."""


class ParseError(Exception):
    """Used to indicate a XML parsing error."""


class DOMException(Exception):
    """Used to indicate a problem processing DOM."""


class Base:
    """Base class for instance level Logging"""
    def __init__(self, module=__name__):
        self.logger = logging.getLogger('%s-%s(%s)' %(module, self.__class__, _get_idstr(self)))


class HTTPResponse:
    """Captures the information in an HTTP response message."""

    def __init__(self, response):
        self.status = response.status
        self.reason = response.reason
        self.headers = response.msg
        self.body = response.read() or None
        response.close()

class TimeoutHTTP(HTTPConnection):
    """A custom http connection object that supports socket timeout."""
    def __init__(self, host, port=None, timeout=20):
        HTTPConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        self.sock = TimeoutSocket(self.timeout)
        self.sock.connect((self.host, self.port))


class TimeoutHTTPS(HTTPSConnection):
    """A custom https object that supports socket timeout. Note that this
       is not really complete. The builtin SSL support in the Python socket
       module requires a real socket (type) to be passed in to be hooked to
       SSL. That means our fake socket won't work and our timeout hacks are
       bypassed for send and recv calls. Since our hack _is_ in place at
       connect() time, it should at least provide some timeout protection."""
    def __init__(self, host, port=None, timeout=20, **kwargs):
        HTTPSConnection.__init__(self, str(host), port, **kwargs)
        self.timeout = timeout

    def connect(self):
        sock = TimeoutSocket(self.timeout)
        sock.connect((self.host, self.port))
        realsock = getattr(sock.sock, '_sock', sock.sock)
        ssl = socket.ssl(realsock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(sock, ssl)


def urlopen(url, timeout=20, redirects=None):
    """A minimal urlopen replacement hack that supports timeouts for http.
       Note that this supports GET only."""
    scheme, host, path, params, query, frag = urlparse(url)

    if not scheme in ('http', 'https'):
        return urllib.urlopen(url)
    if params: path = '%s;%s' % (path, params)
    if query:  path = '%s?%s' % (path, query)
    if frag:   path = '%s#%s' % (path, frag)

    if scheme == 'https':
        # If ssl is not compiled into Python, you will not get an exception
        # until a conn.endheaders() call.   We need to know sooner, so use
        # getattr.
        try:
            import M2Crypto
        except ImportError:
            if not hasattr(socket, 'ssl'):
                raise RuntimeError, 'no built-in SSL Support'

            conn = TimeoutHTTPS(host, None, timeout)
        else:
            ctx = M2Crypto.SSL.Context()
            ctx.set_session_timeout(timeout)
            conn = M2Crypto.httpslib.HTTPSConnection(host, ssl_context=ctx)
            conn.set_debuglevel(1)

    else:
        conn = TimeoutHTTP(host, None, timeout)

    conn.putrequest('GET', path)
    conn.putheader('Connection', 'close')
    conn.endheaders()
    response = None
    while 1:
        response = conn.getresponse()
        if response.status != 100:
            break
        conn._HTTPConnection__state = httplib._CS_REQ_SENT
        conn._HTTPConnection__response = None

    status = response.status

    # If we get an HTTP redirect, we will follow it automatically.
    if status >= 300 and status < 400:
        location = response.msg.getheader('location')
        if location is not None:
            response.close()
            if redirects is not None and redirects.has_key(location):
                raise RecursionError(
                    'Circular HTTP redirection detected.'
                    )
            if redirects is None:
                redirects = {}
            redirects[location] = 1
            return urlopen(location, timeout, redirects)
        raise HTTPResponse(response)

    if not (status >= 200 and status < 300):
        raise HTTPResponse(response)

    body = StringIO(response.read())
    response.close()
    return body

class DOM:
    """The DOM singleton defines a number of XML related constants and
       provides a number of utility methods for DOM related tasks. It
       also provides some basic abstractions so that the rest of the
       package need not care about actual DOM implementation in use."""

    # Namespace stuff related to the SOAP specification.

    NS_SOAP_ENV_1_1 = 'http://schemas.xmlsoap.org/soap/envelope/'
    NS_SOAP_ENC_1_1 = 'http://schemas.xmlsoap.org/soap/encoding/'

    NS_SOAP_ENV_1_2 = 'http://www.w3.org/2001/06/soap-envelope'
    NS_SOAP_ENC_1_2 = 'http://www.w3.org/2001/06/soap-encoding'

    NS_SOAP_ENV_ALL = (NS_SOAP_ENV_1_1, NS_SOAP_ENV_1_2)
    NS_SOAP_ENC_ALL = (NS_SOAP_ENC_1_1, NS_SOAP_ENC_1_2)

    NS_SOAP_ENV = NS_SOAP_ENV_1_1
    NS_SOAP_ENC = NS_SOAP_ENC_1_1

    _soap_uri_mapping = {
        NS_SOAP_ENV_1_1 : '1.1',
        NS_SOAP_ENV_1_2 : '1.2',
    }

    SOAP_ACTOR_NEXT_1_1 = 'http://schemas.xmlsoap.org/soap/actor/next'
    SOAP_ACTOR_NEXT_1_2 = 'http://www.w3.org/2001/06/soap-envelope/actor/next'
    SOAP_ACTOR_NEXT_ALL = (SOAP_ACTOR_NEXT_1_1, SOAP_ACTOR_NEXT_1_2)
    
    def SOAPUriToVersion(self, uri):
        """Return the SOAP version related to an envelope uri."""
        value = self._soap_uri_mapping.get(uri)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported SOAP envelope uri: %s' % uri
            )

    def GetSOAPEnvUri(self, version):
        """Return the appropriate SOAP envelope uri for a given
           human-friendly SOAP version string (e.g. '1.1')."""
        attrname = 'NS_SOAP_ENV_%s' % join(split(version, '.'), '_')
        value = getattr(self, attrname, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported SOAP version: %s' % version
            )

    def GetSOAPEncUri(self, version):
        """Return the appropriate SOAP encoding uri for a given
           human-friendly SOAP version string (e.g. '1.1')."""
        attrname = 'NS_SOAP_ENC_%s' % join(split(version, '.'), '_')
        value = getattr(self, attrname, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported SOAP version: %s' % version
            )

    def GetSOAPActorNextUri(self, version):
        """Return the right special next-actor uri for a given
           human-friendly SOAP version string (e.g. '1.1')."""
        attrname = 'SOAP_ACTOR_NEXT_%s' % join(split(version, '.'), '_')
        value = getattr(self, attrname, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported SOAP version: %s' % version
            )


    # Namespace stuff related to XML Schema.

    NS_XSD_99 = 'http://www.w3.org/1999/XMLSchema'
    NS_XSI_99 = 'http://www.w3.org/1999/XMLSchema-instance'    

    NS_XSD_00 = 'http://www.w3.org/2000/10/XMLSchema'
    NS_XSI_00 = 'http://www.w3.org/2000/10/XMLSchema-instance'    

    NS_XSD_01 = 'http://www.w3.org/2001/XMLSchema'
    NS_XSI_01 = 'http://www.w3.org/2001/XMLSchema-instance'

    NS_XSD_ALL = (NS_XSD_99, NS_XSD_00, NS_XSD_01)
    NS_XSI_ALL = (NS_XSI_99, NS_XSI_00, NS_XSI_01)

    NS_XSD = NS_XSD_01
    NS_XSI = NS_XSI_01

    _xsd_uri_mapping = {
        NS_XSD_99 : NS_XSI_99,
        NS_XSD_00 : NS_XSI_00,
        NS_XSD_01 : NS_XSI_01,
    }

    for key, value in _xsd_uri_mapping.items():
        _xsd_uri_mapping[value] = key


    def InstanceUriForSchemaUri(self, uri):
        """Return the appropriate matching XML Schema instance uri for
           the given XML Schema namespace uri."""
        return self._xsd_uri_mapping.get(uri)

    def SchemaUriForInstanceUri(self, uri):
        """Return the appropriate matching XML Schema namespace uri for
           the given XML Schema instance namespace uri."""
        return self._xsd_uri_mapping.get(uri)


    # Namespace stuff related to WSDL.

    NS_WSDL_1_1 = 'http://schemas.xmlsoap.org/wsdl/'
    NS_WSDL_ALL = (NS_WSDL_1_1,)
    NS_WSDL = NS_WSDL_1_1

    NS_SOAP_BINDING_1_1 = 'http://schemas.xmlsoap.org/wsdl/soap/'
    NS_HTTP_BINDING_1_1 = 'http://schemas.xmlsoap.org/wsdl/http/'
    NS_MIME_BINDING_1_1 = 'http://schemas.xmlsoap.org/wsdl/mime/'

    NS_SOAP_BINDING_ALL = (NS_SOAP_BINDING_1_1,)
    NS_HTTP_BINDING_ALL = (NS_HTTP_BINDING_1_1,)
    NS_MIME_BINDING_ALL = (NS_MIME_BINDING_1_1,)

    NS_SOAP_BINDING = NS_SOAP_BINDING_1_1
    NS_HTTP_BINDING = NS_HTTP_BINDING_1_1
    NS_MIME_BINDING = NS_MIME_BINDING_1_1

    NS_SOAP_HTTP_1_1 = 'http://schemas.xmlsoap.org/soap/http'
    NS_SOAP_HTTP_ALL = (NS_SOAP_HTTP_1_1,)
    NS_SOAP_HTTP = NS_SOAP_HTTP_1_1
    

    _wsdl_uri_mapping = {
        NS_WSDL_1_1 : '1.1',
    }
    
    def WSDLUriToVersion(self, uri):
        """Return the WSDL version related to a WSDL namespace uri."""
        value = self._wsdl_uri_mapping.get(uri)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported SOAP envelope uri: %s' % uri
            )

    def GetWSDLUri(self, version):
        attr = 'NS_WSDL_%s' % join(split(version, '.'), '_')
        value = getattr(self, attr, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported WSDL version: %s' % version
            )

    def GetWSDLSoapBindingUri(self, version):
        attr = 'NS_SOAP_BINDING_%s' % join(split(version, '.'), '_')
        value = getattr(self, attr, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported WSDL version: %s' % version
            )

    def GetWSDLHttpBindingUri(self, version):
        attr = 'NS_HTTP_BINDING_%s' % join(split(version, '.'), '_')
        value = getattr(self, attr, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported WSDL version: %s' % version
            )

    def GetWSDLMimeBindingUri(self, version):
        attr = 'NS_MIME_BINDING_%s' % join(split(version, '.'), '_')
        value = getattr(self, attr, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported WSDL version: %s' % version
            )

    def GetWSDLHttpTransportUri(self, version):
        attr = 'NS_SOAP_HTTP_%s' % join(split(version, '.'), '_')
        value = getattr(self, attr, None)
        if value is not None:
            return value
        raise ValueError(
            'Unsupported WSDL version: %s' % version
            )


    # Other xml namespace constants.
    NS_XMLNS     = 'http://www.w3.org/2000/xmlns/'



    def isElement(self, node, name, nsuri=None):
        """Return true if the given node is an element with the given
           name and optional namespace uri."""
        if node.nodeType != node.ELEMENT_NODE:
            return 0
        return node.localName == name and \
               (nsuri is None or self.nsUriMatch(node.namespaceURI, nsuri))

    def getElement(self, node, name, nsuri=None, default=join):
        """Return the first child of node with a matching name and
           namespace uri, or the default if one is provided."""
        nsmatch = self.nsUriMatch
        ELEMENT_NODE = node.ELEMENT_NODE
        for child in node.childNodes:
            if child.nodeType == ELEMENT_NODE:
                if ((child.localName == name or name is None) and
                    (nsuri is None or nsmatch(child.namespaceURI, nsuri))
                    ):
                    return child
        if default is not join:
            return default
        raise KeyError, name

    def getElementById(self, node, id, default=join):
        """Return the first child of node matching an id reference."""
        attrget = self.getAttr
        ELEMENT_NODE = node.ELEMENT_NODE
        for child in node.childNodes:
            if child.nodeType == ELEMENT_NODE:
                if attrget(child, 'id') == id:
                    return child
        if default is not join:
            return default
        raise KeyError, name

    def getMappingById(self, document, depth=None, element=None,
                       mapping=None, level=1):
        """Create an id -> element mapping of those elements within a
           document that define an id attribute. The depth of the search
           may be controlled by using the (1-based) depth argument."""
        if document is not None:
            element = document.documentElement
            mapping = {}
        attr = element._attrs.get('id', None)
        if attr is not None:
            mapping[attr.value] = element
        if depth is None or depth > level:
            level = level + 1
            ELEMENT_NODE = element.ELEMENT_NODE
            for child in element.childNodes:
                if child.nodeType == ELEMENT_NODE:
                    self.getMappingById(None, depth, child, mapping, level)
        return mapping        

    def getElements(self, node, name, nsuri=None):
        """Return a sequence of the child elements of the given node that
           match the given name and optional namespace uri."""
        nsmatch = self.nsUriMatch
        result = []
        ELEMENT_NODE = node.ELEMENT_NODE
        for child in node.childNodes:
            if child.nodeType == ELEMENT_NODE:
                if ((child.localName == name or name is None) and (
                    (nsuri is None) or nsmatch(child.namespaceURI, nsuri))):
                    result.append(child)
        return result

    def hasAttr(self, node, name, nsuri=None):
        """Return true if element has attribute with the given name and
           optional nsuri. If nsuri is not specified, returns true if an
           attribute exists with the given name with any namespace."""
        if nsuri is None:
            if node.hasAttribute(name):
                return True
            return False
        return node.hasAttributeNS(nsuri, name)

    def getAttr(self, node, name, nsuri=None, default=join):
        """Return the value of the attribute named 'name' with the
           optional nsuri, or the default if one is specified. If
           nsuri is not specified, an attribute that matches the
           given name will be returned regardless of namespace."""
        if nsuri is None:
            result = node._attrs.get(name, None)
            if result is None:
                for item in node._attrsNS.keys():
                    if item[1] == name:
                        result = node._attrsNS[item]
                        break
        else:
            result = node._attrsNS.get((nsuri, name), None)
        if result is not None:
            return result.value
        if default is not join:
            return default
        return ''

    def getAttrs(self, node):
        """Return a Collection of all attributes 
        """
        attrs = {}
        for k,v in node._attrs.items():
            attrs[k] = v.value
        return attrs

    def getElementText(self, node, preserve_ws=None):
        """Return the text value of an xml element node. Leading and trailing
           whitespace is stripped from the value unless the preserve_ws flag
           is passed with a true value."""
        result = []
        for child in node.childNodes:
            nodetype = child.nodeType
            if nodetype == child.TEXT_NODE or \
               nodetype == child.CDATA_SECTION_NODE:
                result.append(child.nodeValue)
        value = join(result, '')
        if preserve_ws is None:
            value = strip(value)
        return value

    def findNamespaceURI(self, prefix, node):
        """Find a namespace uri given a prefix and a context node."""
        attrkey = (self.NS_XMLNS, prefix)
        DOCUMENT_NODE = node.DOCUMENT_NODE
        ELEMENT_NODE = node.ELEMENT_NODE
        while 1:
            if node is None:
                raise DOMException('Value for prefix %s not found.' % prefix)
            if node.nodeType != ELEMENT_NODE:
                node = node.parentNode
                continue
            result = node._attrsNS.get(attrkey, None)
            if result is not None:
                return result.value
            if hasattr(node, '__imported__'):
                raise DOMException('Value for prefix %s not found.' % prefix)
            node = node.parentNode
            if node.nodeType == DOCUMENT_NODE:
                raise DOMException('Value for prefix %s not found.' % prefix)

    def findDefaultNS(self, node):
        """Return the current default namespace uri for the given node."""
        attrkey = (self.NS_XMLNS, 'xmlns')
        DOCUMENT_NODE = node.DOCUMENT_NODE
        ELEMENT_NODE = node.ELEMENT_NODE
        while 1:
            if node.nodeType != ELEMENT_NODE:
                node = node.parentNode
                continue
            result = node._attrsNS.get(attrkey, None)
            if result is not None:
                return result.value
            if hasattr(node, '__imported__'):
                raise DOMException('Cannot determine default namespace.')
            node = node.parentNode
            if node.nodeType == DOCUMENT_NODE:
                raise DOMException('Cannot determine default namespace.')

    def findTargetNS(self, node):
        """Return the defined target namespace uri for the given node."""
        attrget = self.getAttr
        attrkey = (self.NS_XMLNS, 'xmlns')
        DOCUMENT_NODE = node.DOCUMENT_NODE
        ELEMENT_NODE = node.ELEMENT_NODE
        while 1:
            if node.nodeType != ELEMENT_NODE:
                node = node.parentNode
                continue
            result = attrget(node, 'targetNamespace', default=None)
            if result is not None:
                return result
            node = node.parentNode
            if node.nodeType == DOCUMENT_NODE:
                raise DOMException('Cannot determine target namespace.')

    def getTypeRef(self, element):
        """Return (namespaceURI, name) for a type attribue of the given
           element, or None if the element does not have a type attribute."""
        typeattr = self.getAttr(element, 'type', default=None)
        if typeattr is None:
            return None
        parts = typeattr.split(':', 1)
        if len(parts) == 2:
            nsuri = self.findNamespaceURI(parts[0], element)
        else:
            nsuri = self.findDefaultNS(element)
        return (nsuri, parts[1])

    def importNode(self, document, node, deep=0):
        """Implements (well enough for our purposes) DOM node import."""
        nodetype = node.nodeType
        if nodetype in (node.DOCUMENT_NODE, node.DOCUMENT_TYPE_NODE):
            raise DOMException('Illegal node type for importNode')
        if nodetype == node.ENTITY_REFERENCE_NODE:
            deep = 0
        clone = node.cloneNode(deep)
        self._setOwnerDoc(document, clone)
        clone.__imported__ = 1
        return clone

    def _setOwnerDoc(self, document, node):
        node.ownerDocument = document
        for child in node.childNodes:
            self._setOwnerDoc(document, child)

    def nsUriMatch(self, value, wanted, strict=0, tt=type(())):
        """Return a true value if two namespace uri values match."""
        if value == wanted or (type(wanted) is tt) and value in wanted:
            return 1
        if not strict and value is not None:
            wanted = type(wanted) is tt and wanted or (wanted,)
            value = value[-1:] != '/' and value or value[:-1]
            for item in wanted:
                if item == value or item[:-1] == value:
                    return 1
        return 0

    def createDocument(self, nsuri, qname, doctype=None):
        """Create a new writable DOM document object."""
        impl = xml.dom.minidom.getDOMImplementation()
        return impl.createDocument(nsuri, qname, doctype)

    def loadDocument(self, data):
        """Load an xml file from a file-like object and return a DOM
           document instance."""
        return xml.dom.minidom.parse(data)

    def loadFromURL(self, url):
        """Load an xml file from a URL and return a DOM document."""
        if isfile(url) is True:
            file = open(url, 'r')
        else:
            file = urlopen(url)

        try:     
            result = self.loadDocument(file)
        except Exception, ex:
            file.close()
            raise ParseError(('Failed to load document %s' %url,) + ex.args)
        else:
            file.close()
        return result

DOM = DOM()


class MessageInterface:
    '''Higher Level Interface, delegates to DOM singleton, must 
    be subclassed and implement all methods that throw NotImplementedError.
    '''
    def __init__(self, sw):
        '''Constructor, May be extended, do not override.
            sw -- soapWriter instance
        '''
        self.sw = None
        if type(sw) != weakref.ReferenceType and sw is not None:
            self.sw = weakref.ref(sw)
        else:
            self.sw = sw

    def AddCallback(self, func, *arglist):
        self.sw().AddCallback(func, *arglist)

    def Known(self, obj):
        return self.sw().Known(obj)

    def Forget(self, obj):
        return self.sw().Forget(obj)

    def canonicalize(self):
        '''canonicalize the underlying DOM, and return as string.
        '''
        raise NotImplementedError, ''

    def createDocument(self, namespaceURI=SOAP.ENV, localName='Envelope'):
        '''create Document
        '''
        raise NotImplementedError, ''

    def createAppendElement(self, namespaceURI, localName):
        '''create and append element(namespaceURI,localName), and return
        the node.
        '''
        raise NotImplementedError, ''

    def findNamespaceURI(self, qualifiedName):
        raise NotImplementedError, ''

    def resolvePrefix(self, prefix):
        raise NotImplementedError, ''

    def setAttributeNS(self, namespaceURI, localName, value):
        '''set attribute (namespaceURI, localName)=value
        '''
        raise NotImplementedError, ''

    def setAttributeType(self, namespaceURI, localName):
        '''set attribute xsi:type=(namespaceURI, localName)
        '''
        raise NotImplementedError, ''

    def setNamespaceAttribute(self, namespaceURI, prefix):
        '''set namespace attribute xmlns:prefix=namespaceURI 
        '''
        raise NotImplementedError, ''


class ElementProxy(Base, MessageInterface):
    '''
    '''
    _soap_env_prefix = 'SOAP-ENV'
    _soap_enc_prefix = 'SOAP-ENC'
    _zsi_prefix = 'ZSI'
    _xsd_prefix = 'xsd'
    _xsi_prefix = 'xsi'
    _xml_prefix = 'xml'
    _xmlns_prefix = 'xmlns'

    _soap_env_nsuri = SOAP.ENV
    _soap_enc_nsuri = SOAP.ENC
    _zsi_nsuri = ZSI_SCHEMA_URI
    _xsd_nsuri =  SCHEMA.XSD3
    _xsi_nsuri = SCHEMA.XSI3
    _xml_nsuri = XMLNS.XML
    _xmlns_nsuri = XMLNS.BASE

    standard_ns = {\
        _xml_prefix:_xml_nsuri,
        _xmlns_prefix:_xmlns_nsuri
    }
    reserved_ns = {\
        _soap_env_prefix:_soap_env_nsuri,
        _soap_enc_prefix:_soap_enc_nsuri,
        _zsi_prefix:_zsi_nsuri,
        _xsd_prefix:_xsd_nsuri,
        _xsi_prefix:_xsi_nsuri,
    }
    name = None
    namespaceURI = None

    def __init__(self, sw, message=None):
        '''Initialize. 
           sw -- SoapWriter
        '''
        self._indx = 0
        MessageInterface.__init__(self, sw)
        Base.__init__(self)
        self._dom = DOM
        self.node = None
        if type(message) in (types.StringType,types.UnicodeType):
            self.loadFromString(message)
        elif isinstance(message, ElementProxy):
            self.node = message._getNode()
        else:
            self.node = message
        self.processorNss = self.standard_ns.copy()
        self.processorNss.update(self.reserved_ns)

    def __str__(self):
        return self.toString()

    def evaluate(self, expression, processorNss=None):
        '''expression -- XPath compiled expression
        '''
        from Ft.Xml import XPath
        if not processorNss:
            context = XPath.Context.Context(self.node, processorNss=self.processorNss)
        else:
            context = XPath.Context.Context(self.node, processorNss=processorNss)
        nodes = expression.evaluate(context)
        return map(lambda node: ElementProxy(self.sw,node), nodes)

    #############################################
    # Methods for checking/setting the
    # classes (namespaceURI,name) node. 
    #############################################
    def checkNode(self, namespaceURI=None, localName=None):
        '''
            namespaceURI -- namespace of element
            localName -- local name of element
        '''
        namespaceURI = namespaceURI or self.namespaceURI
        localName = localName or self.name
        check = False
        if localName and self.node:
            check = self._dom.isElement(self.node, localName, namespaceURI)
        if not check:
            raise NamespaceError, 'unexpected node type %s, expecting %s' %(self.node, localName)

    def setNode(self, node=None):
        if node:
            if isinstance(node, ElementProxy):
                self.node = node._getNode()
            else:
                self.node = node
        elif self.node:
            node = self._dom.getElement(self.node, self.name, self.namespaceURI, default=None)
            if not node:
                raise NamespaceError, 'cant find element (%s,%s)' %(self.namespaceURI,self.name)
            self.node = node
        else:
            #self.node = self._dom.create(self.node, self.name, self.namespaceURI, default=None)
            self.createDocument(self.namespaceURI, localName=self.name, doctype=None)
        
        self.checkNode()

    #############################################
    # Wrapper Methods for direct DOM Element Node access
    #############################################
    def _getNode(self):
        return self.node

    def _getElements(self):
        return self._dom.getElements(self.node, name=None)

    def _getOwnerDocument(self):
        return self.node.ownerDocument or self.node

    def _getUniquePrefix(self):
        '''I guess we need to resolve all potential prefixes
        because when the current node is attached it copies the 
        namespaces into the parent node.
        '''
        while 1:
            self._indx += 1
            prefix = 'ns%d' %self._indx
            try:
                self._dom.findNamespaceURI(prefix, self._getNode())
            except DOMException, ex:
                break
        return prefix

    def _getPrefix(self, node, nsuri):
        '''
        Keyword arguments:
            node -- DOM Element Node
            nsuri -- namespace of attribute value
        '''
        try:
            if node and (node.nodeType == node.ELEMENT_NODE) and \
                (nsuri == self._dom.findDefaultNS(node)):
                return None
        except DOMException, ex:
            pass
        if nsuri == XMLNS.XML:
            return self._xml_prefix
        if node.nodeType == Node.ELEMENT_NODE:
            for attr in node.attributes.values():
                if attr.namespaceURI == XMLNS.BASE \
                   and nsuri == attr.value:
                        return attr.localName
            else:
                if node.parentNode:
                    return self._getPrefix(node.parentNode, nsuri)
        raise NamespaceError, 'namespaceURI "%s" is not defined' %nsuri

    def _appendChild(self, node):
        '''
        Keyword arguments:
            node -- DOM Element Node
        '''
        if node is None:
            raise TypeError, 'node is None'
        self.node.appendChild(node)

    def _insertBefore(self, newChild, refChild):
        '''
        Keyword arguments:
            child -- DOM Element Node to insert
            refChild -- DOM Element Node 
        '''
        self.node.insertBefore(newChild, refChild)

    def _setAttributeNS(self, namespaceURI, qualifiedName, value):
        '''
        Keyword arguments:
            namespaceURI -- namespace of attribute
            qualifiedName -- qualified name of new attribute value
            value -- value of attribute
        '''
        self.node.setAttributeNS(namespaceURI, qualifiedName, value)

    #############################################
    #General Methods
    #############################################
    def isFault(self):
        '''check to see if this is a soap:fault message.
        '''
        return False

    def getPrefix(self, namespaceURI):
        try:
            prefix = self._getPrefix(node=self.node, nsuri=namespaceURI)
        except NamespaceError, ex:
            prefix = self._getUniquePrefix() 
            self.setNamespaceAttribute(prefix, namespaceURI)
        return prefix

    def getDocument(self):
        return self._getOwnerDocument()

    def setDocument(self, document):
        self.node = document

    def importFromString(self, xmlString):
        doc = self._dom.loadDocument(StringIO(xmlString))
        node = self._dom.getElement(doc, name=None)
        clone = self.importNode(node)
        self._appendChild(clone)

    def importNode(self, node):
        if isinstance(node, ElementProxy):
            node = node._getNode()
        return self._dom.importNode(self._getOwnerDocument(), node, deep=1)

    def loadFromString(self, data):
        self.node = self._dom.loadDocument(StringIO(data))

    def canonicalize(self):
        return Canonicalize(self.node)

    def toString(self):
        return self.canonicalize()

    def createDocument(self, namespaceURI, localName, doctype=None):
        '''If specified must be a SOAP envelope, else may contruct an empty document.
        '''
        prefix = self._soap_env_prefix

        if namespaceURI == self.reserved_ns[prefix]:
            qualifiedName = '%s:%s' %(prefix,localName)
        elif namespaceURI is localName is None:
            self.node = self._dom.createDocument(None,None,None)
            return
        else:
            raise KeyError, 'only support creation of document in %s' %self.reserved_ns[prefix]

        document = self._dom.createDocument(nsuri=namespaceURI, qname=qualifiedName, doctype=doctype)
        self.node = document.childNodes[0]

        #set up reserved namespace attributes
        for prefix,nsuri in self.reserved_ns.items():
            self._setAttributeNS(namespaceURI=self._xmlns_nsuri, 
                qualifiedName='%s:%s' %(self._xmlns_prefix,prefix), 
                value=nsuri)

    #############################################
    #Methods for attributes
    #############################################
    def hasAttribute(self, namespaceURI, localName):
        return self._dom.hasAttr(self._getNode(), name=localName, nsuri=namespaceURI)

    def setAttributeType(self, namespaceURI, localName):
        '''set xsi:type
        Keyword arguments:
            namespaceURI -- namespace of attribute value
            localName -- name of new attribute value

        '''
        self.logger.debug('setAttributeType: (%s,%s)', namespaceURI, localName)
        value = localName
        if namespaceURI:
            value = '%s:%s' %(self.getPrefix(namespaceURI),localName)

        xsi_prefix = self.getPrefix(self._xsi_nsuri)
        self._setAttributeNS(self._xsi_nsuri, '%s:type' %xsi_prefix, value)

    def createAttributeNS(self, namespace, name, value):
        document = self._getOwnerDocument()
        ##this function doesn't exist!! it has only two arguments
        attrNode = document.createAttributeNS(namespace, name, value)

    def setAttributeNS(self, namespaceURI, localName, value):
        '''
        Keyword arguments:
            namespaceURI -- namespace of attribute to create, None is for
                attributes in no namespace.
            localName -- local name of new attribute
            value -- value of new attribute
        ''' 
        prefix = None
        if namespaceURI:
            try:
                prefix = self.getPrefix(namespaceURI)
            except KeyError, ex:
                prefix = 'ns2'
                self.setNamespaceAttribute(prefix, namespaceURI)
        qualifiedName = localName
        if prefix:
            qualifiedName = '%s:%s' %(prefix, localName)
        self._setAttributeNS(namespaceURI, qualifiedName, value)

    def setNamespaceAttribute(self, prefix, namespaceURI):
        '''
        Keyword arguments:
            prefix -- xmlns prefix
            namespaceURI -- value of prefix
        '''
        self._setAttributeNS(XMLNS.BASE, 'xmlns:%s' %prefix, namespaceURI)

    #############################################
    #Methods for elements
    #############################################
    def createElementNS(self, namespace, qname):
        '''
        Keyword arguments:
            namespace -- namespace of element to create
            qname -- qualified name of new element
        '''
        document = self._getOwnerDocument()
        node = document.createElementNS(namespace, qname)
        return ElementProxy(self.sw, node)

    def createAppendSetElement(self, namespaceURI, localName, prefix=None):
        '''Create a new element (namespaceURI,name), append it
           to current node, then set it to be the current node.
        Keyword arguments:
            namespaceURI -- namespace of element to create
            localName -- local name of new element
            prefix -- if namespaceURI is not defined, declare prefix.  defaults
                to 'ns1' if left unspecified.
        '''
        node = self.createAppendElement(namespaceURI, localName, prefix=None)
        node=node._getNode()
        self._setNode(node._getNode())

    def createAppendElement(self, namespaceURI, localName, prefix=None):
        '''Create a new element (namespaceURI,name), append it
           to current node, and return the newly created node.
        Keyword arguments:
            namespaceURI -- namespace of element to create
            localName -- local name of new element
            prefix -- if namespaceURI is not defined, declare prefix.  defaults
                to 'ns1' if left unspecified.
        '''
        declare = False
        qualifiedName = localName
        if namespaceURI:
            try:
                prefix = self.getPrefix(namespaceURI)
            except:
                declare = True
                prefix = prefix or self._getUniquePrefix()
            if prefix: 
                qualifiedName = '%s:%s' %(prefix, localName)
        node = self.createElementNS(namespaceURI, qualifiedName)
        if declare:
            node._setAttributeNS(XMLNS.BASE, 'xmlns:%s' %prefix, namespaceURI)
        self._appendChild(node=node._getNode())
        return node

    def createInsertBefore(self, namespaceURI, localName, refChild):
        qualifiedName = localName
        prefix = self.getPrefix(namespaceURI)
        if prefix: 
            qualifiedName = '%s:%s' %(prefix, localName)
        node = self.createElementNS(namespaceURI, qualifiedName)
        self._insertBefore(newChild=node._getNode(), refChild=refChild._getNode())
        return node

    def getElement(self, namespaceURI, localName):
        '''
        Keyword arguments:
            namespaceURI -- namespace of element
            localName -- local name of element
        '''
        node = self._dom.getElement(self.node, localName, namespaceURI, default=None)
        if node:
            return ElementProxy(self.sw, node)
        return None

    def getAttributeValue(self, namespaceURI, localName):
        '''
        Keyword arguments:
            namespaceURI -- namespace of attribute
            localName -- local name of attribute
        '''
        if self.hasAttribute(namespaceURI, localName):
            attr = self.node.getAttributeNodeNS(namespaceURI,localName)
            return attr.value
        return None

    def getValue(self):
        return self._dom.getElementText(self.node, preserve_ws=True)    

    #############################################
    #Methods for text nodes
    #############################################
    def createAppendTextNode(self, pyobj):
        node = self.createTextNode(pyobj)
        self._appendChild(node=node._getNode())
        return node

    def createTextNode(self, pyobj):
        document = self._getOwnerDocument()
        node = document.createTextNode(pyobj)
        return ElementProxy(self.sw, node)

    #############################################
    #Methods for retrieving namespaceURI's
    #############################################
    def findNamespaceURI(self, qualifiedName):
        parts = SplitQName(qualifiedName)
        element = self._getNode()
        if len(parts) == 1:
            return (self._dom.findTargetNS(element), value)
        return self._dom.findNamespaceURI(parts[0], element)

    def resolvePrefix(self, prefix):
        element = self._getNode()
        return self._dom.findNamespaceURI(prefix, element)

    def getSOAPEnvURI(self):
        return self._soap_env_nsuri

    def isEmpty(self):
        return not self.node



class Collection(UserDict):
    """Helper class for maintaining ordered named collections."""
    default = lambda self,k: k.name
    def __init__(self, parent, key=None):
        UserDict.__init__(self)
        self.parent = weakref.ref(parent)
        self.list = []
        self._func = key or self.default

    def __getitem__(self, key):
        if type(key) is type(1):
            return self.list[key]
        return self.data[key]

    def __setitem__(self, key, item):
        item.parent = weakref.ref(self)
        self.list.append(item)
        self.data[key] = item

    def keys(self):
        return map(lambda i: self._func(i), self.list)

    def items(self):
        return map(lambda i: (self._func(i), i), self.list)

    def values(self):
        return self.list


class CollectionNS(UserDict):
    """Helper class for maintaining ordered named collections."""
    default = lambda self,k: k.name
    def __init__(self, parent, key=None):
        UserDict.__init__(self)
        self.parent = weakref.ref(parent)
        self.targetNamespace = None
        self.list = []
        self._func = key or self.default

    def __getitem__(self, key):
        self.targetNamespace = self.parent().targetNamespace
        if type(key) is types.IntType:
            return self.list[key]
        elif self.__isSequence(key):
            nsuri,name = key
            return self.data[nsuri][name]
        return self.data[self.parent().targetNamespace][key]

    def __setitem__(self, key, item):
        item.parent = weakref.ref(self)
        self.list.append(item)
        targetNamespace = getattr(item, 'targetNamespace', self.parent().targetNamespace)
        if not self.data.has_key(targetNamespace):
            self.data[targetNamespace] = {}
        self.data[targetNamespace][key] = item

    def __isSequence(self, key):
        return (type(key) in (types.TupleType,types.ListType) and len(key) == 2)

    def keys(self):
        keys = []
        for tns in self.data.keys():
            keys.append(map(lambda i: (tns,self._func(i)), self.data[tns].values()))
        return keys

    def items(self):
        return map(lambda i: (self._func(i), i), self.list)

    def values(self):
        return self.list



# This is a runtime guerilla patch for pulldom (used by minidom) so
# that xml namespace declaration attributes are not lost in parsing.
# We need them to do correct QName linking for XML Schema and WSDL.
# The patch has been submitted to SF for the next Python version.

from xml.dom.pulldom import PullDOM, START_ELEMENT
if 1:
    def startPrefixMapping(self, prefix, uri):
        if not hasattr(self, '_xmlns_attrs'):
            self._xmlns_attrs = []
        self._xmlns_attrs.append((prefix or 'xmlns', uri))
        self._ns_contexts.append(self._current_context.copy())
        self._current_context[uri] = prefix or ''

    PullDOM.startPrefixMapping = startPrefixMapping

    def startElementNS(self, name, tagName , attrs):
        # Retrieve xml namespace declaration attributes.
        xmlns_uri = 'http://www.w3.org/2000/xmlns/'
        xmlns_attrs = getattr(self, '_xmlns_attrs', None)
        if xmlns_attrs is not None:
            for aname, value in xmlns_attrs:
                attrs._attrs[(xmlns_uri, aname)] = value
            self._xmlns_attrs = []
        uri, localname = name
        if uri:
            # When using namespaces, the reader may or may not
            # provide us with the original name. If not, create
            # *a* valid tagName from the current context.
            if tagName is None:
                prefix = self._current_context[uri]
                if prefix:
                    tagName = prefix + ":" + localname
                else:
                    tagName = localname
            if self.document:
                node = self.document.createElementNS(uri, tagName)
            else:
                node = self.buildDocument(uri, tagName)
        else:
            # When the tagname is not prefixed, it just appears as
            # localname
            if self.document:
                node = self.document.createElement(localname)
            else:
                node = self.buildDocument(None, localname)

        for aname,value in attrs.items():
            a_uri, a_localname = aname
            if a_uri == xmlns_uri:
                if a_localname == 'xmlns':
                    qname = a_localname
                else:
                    qname = 'xmlns:' + a_localname
                attr = self.document.createAttributeNS(a_uri, qname)
                node.setAttributeNodeNS(attr)
            elif a_uri:
                prefix = self._current_context[a_uri]
                if prefix:
                    qname = prefix + ":" + a_localname
                else:
                    qname = a_localname
                attr = self.document.createAttributeNS(a_uri, qname)
                node.setAttributeNodeNS(attr)
            else:
                attr = self.document.createAttribute(a_localname)
                node.setAttributeNode(attr)
            attr.value = value

        self.lastEvent[1] = [(START_ELEMENT, node), None]
        self.lastEvent = self.lastEvent[1]
        self.push(node)

    PullDOM.startElementNS = startElementNS

#
# This is a runtime guerilla patch for minidom so
# that xmlns prefixed attributes dont raise AttributeErrors
# during cloning.
#
# Namespace declarations can appear in any start-tag, must look for xmlns
# prefixed attribute names during cloning.
#
# key (attr.namespaceURI, tag)
# ('http://www.w3.org/2000/xmlns/', u'xsd')   <xml.dom.minidom.Attr instance at 0x82227c4>
# ('http://www.w3.org/2000/xmlns/', 'xmlns')   <xml.dom.minidom.Attr instance at 0x8414b3c>
#
# xml.dom.minidom.Attr.nodeName = xmlns:xsd
# xml.dom.minidom.Attr.value =  = http://www.w3.org/2001/XMLSchema 

if 1:
    def _clone_node(node, deep, newOwnerDocument):
        """
        Clone a node and give it the new owner document.
        Called by Node.cloneNode and Document.importNode
        """
        if node.ownerDocument.isSameNode(newOwnerDocument):
            operation = xml.dom.UserDataHandler.NODE_CLONED
        else:
            operation = xml.dom.UserDataHandler.NODE_IMPORTED
        if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            clone = newOwnerDocument.createElementNS(node.namespaceURI,
                                                     node.nodeName)
            for attr in node.attributes.values():
                clone.setAttributeNS(attr.namespaceURI, attr.nodeName, attr.value)

                prefix, tag = xml.dom.minidom._nssplit(attr.nodeName)
                if prefix == 'xmlns':
                    a = clone.getAttributeNodeNS(attr.namespaceURI, tag)
                elif prefix:
                    a = clone.getAttributeNodeNS(attr.namespaceURI, tag)
                else:
                    a = clone.getAttributeNodeNS(attr.namespaceURI, attr.nodeName)
                a.specified = attr.specified

            if deep:
                for child in node.childNodes:
                    c = xml.dom.minidom._clone_node(child, deep, newOwnerDocument)
                    clone.appendChild(c)
        elif node.nodeType == xml.dom.minidom.Node.DOCUMENT_FRAGMENT_NODE:
            clone = newOwnerDocument.createDocumentFragment()
            if deep:
                for child in node.childNodes:
                    c = xml.dom.minidom._clone_node(child, deep, newOwnerDocument)
                    clone.appendChild(c)

        elif node.nodeType == xml.dom.minidom.Node.TEXT_NODE:
            clone = newOwnerDocument.createTextNode(node.data)
        elif node.nodeType == xml.dom.minidom.Node.CDATA_SECTION_NODE:
            clone = newOwnerDocument.createCDATASection(node.data)
        elif node.nodeType == xml.dom.minidom.Node.PROCESSING_INSTRUCTION_NODE:
            clone = newOwnerDocument.createProcessingInstruction(node.target,
                                                                 node.data)
        elif node.nodeType == xml.dom.minidom.Node.COMMENT_NODE:
            clone = newOwnerDocument.createComment(node.data)
        elif node.nodeType == xml.dom.minidom.Node.ATTRIBUTE_NODE:
            clone = newOwnerDocument.createAttributeNS(node.namespaceURI,
                                                       node.nodeName)
            clone.specified = True
            clone.value = node.value
        elif node.nodeType == xml.dom.minidom.Node.DOCUMENT_TYPE_NODE:
            assert node.ownerDocument is not newOwnerDocument
            operation = xml.dom.UserDataHandler.NODE_IMPORTED
            clone = newOwnerDocument.implementation.createDocumentType(
                node.name, node.publicId, node.systemId)
            clone.ownerDocument = newOwnerDocument
            if deep:
                clone.entities._seq = []
                clone.notations._seq = []
                for n in node.notations._seq:
                    notation = xml.dom.minidom.Notation(n.nodeName, n.publicId, n.systemId)
                    notation.ownerDocument = newOwnerDocument
                    clone.notations._seq.append(notation)
                    if hasattr(n, '_call_user_data_handler'):
                        n._call_user_data_handler(operation, n, notation)
                for e in node.entities._seq:
                    entity = xml.dom.minidom.Entity(e.nodeName, e.publicId, e.systemId,
                                    e.notationName)
                    entity.actualEncoding = e.actualEncoding
                    entity.encoding = e.encoding
                    entity.version = e.version
                    entity.ownerDocument = newOwnerDocument
                    clone.entities._seq.append(entity)
                    if hasattr(e, '_call_user_data_handler'):
                        e._call_user_data_handler(operation, n, entity)
        else:
            # Note the cloning of Document and DocumentType nodes is
            # implemenetation specific.  minidom handles those cases
            # directly in the cloneNode() methods.
            raise xml.dom.NotSupportedErr("Cannot clone node %s" % repr(node))

        # Check for _call_user_data_handler() since this could conceivably
        # used with other DOM implementations (one of the FourThought
        # DOMs, perhaps?).
        if hasattr(node, '_call_user_data_handler'):
            node._call_user_data_handler(operation, node, clone)
        return clone

    xml.dom.minidom._clone_node = _clone_node


########NEW FILE########
__FILENAME__ = WSDLTools
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.

ident = "$Id$"

import weakref
from cStringIO import StringIO
from Namespaces import OASIS, XMLNS, WSA, WSA_LIST, WSAW_LIST, WSRF_V1_2, WSRF
from Utility import Collection, CollectionNS, DOM, ElementProxy, basejoin
from XMLSchema import XMLSchema, SchemaReader, WSDLToolsAdapter


class WSDLReader:
    """A WSDLReader creates WSDL instances from urls and xml data."""

    # Custom subclasses of WSDLReader may wish to implement a caching
    # strategy or other optimizations. Because application needs vary 
    # so widely, we don't try to provide any caching by default.

    def loadFromStream(self, stream, name=None):
        """Return a WSDL instance loaded from a stream object."""
        document = DOM.loadDocument(stream)
        wsdl = WSDL()
        if name:
            wsdl.location = name
        elif hasattr(stream, 'name'):
            wsdl.location = stream.name
        wsdl.load(document)
        return wsdl

    def loadFromURL(self, url):
        """Return a WSDL instance loaded from the given url."""
        document = DOM.loadFromURL(url)
        wsdl = WSDL()
        wsdl.location = url
        wsdl.load(document)
        return wsdl

    def loadFromString(self, data):
        """Return a WSDL instance loaded from an xml string."""
        return self.loadFromStream(StringIO(data))

    def loadFromFile(self, filename):
        """Return a WSDL instance loaded from the given file."""
        file = open(filename, 'rb')
        try:
            wsdl = self.loadFromStream(file)
        finally:
            file.close()
        return wsdl

class WSDL:
    """A WSDL object models a WSDL service description. WSDL objects
       may be created manually or loaded from an xml representation
       using a WSDLReader instance."""

    def __init__(self, targetNamespace=None, strict=1):
        self.targetNamespace = targetNamespace or 'urn:this-document.wsdl'
        self.documentation = ''
        self.location = None
        self.document = None
        self.name = None
        self.services = CollectionNS(self)
        self.messages = CollectionNS(self)
        self.portTypes = CollectionNS(self)
        self.bindings = CollectionNS(self)
        self.imports = Collection(self)
        self.types = Types(self)
        self.extensions = []
        self.strict = strict

    def __del__(self):
        if self.document is not None:
            self.document.unlink()

    version = '1.1'

    def addService(self, name, documentation='', targetNamespace=None):
        if self.services.has_key(name):
            raise WSDLError(
                'Duplicate service element: %s' % name
                )
        item = Service(name, documentation)
        if targetNamespace:
            item.targetNamespace = targetNamespace
        self.services[name] = item
        return item

    def addMessage(self, name, documentation='', targetNamespace=None):
        if self.messages.has_key(name):
            raise WSDLError(
                'Duplicate message element: %s.' % name
                )
        item = Message(name, documentation)
        if targetNamespace:
            item.targetNamespace = targetNamespace
        self.messages[name] = item
        return item

    def addPortType(self, name, documentation='', targetNamespace=None):
        if self.portTypes.has_key(name):
            raise WSDLError(
                'Duplicate portType element: name'
                )
        item = PortType(name, documentation)
        if targetNamespace:
            item.targetNamespace = targetNamespace
        self.portTypes[name] = item
        return item

    def addBinding(self, name, type, documentation='', targetNamespace=None):
        if self.bindings.has_key(name):
            raise WSDLError(
                'Duplicate binding element: %s' % name
                )
        item = Binding(name, type, documentation)
        if targetNamespace:
            item.targetNamespace = targetNamespace
        self.bindings[name] = item
        return item

    def addImport(self, namespace, location):
        item = ImportElement(namespace, location)
        self.imports[namespace] = item
        return item

    def toDom(self):
        """ Generate a DOM representation of the WSDL instance.
        Not dealing with generating XML Schema, thus the targetNamespace
        of all XML Schema elements or types used by WSDL message parts 
        needs to be specified via import information items.
        """
        namespaceURI = DOM.GetWSDLUri(self.version)
        self.document = DOM.createDocument(namespaceURI ,'wsdl:definitions')

        # Set up a couple prefixes for easy reading.
        child = DOM.getElement(self.document, None)
        child.setAttributeNS(None, 'targetNamespace', self.targetNamespace)
        child.setAttributeNS(XMLNS.BASE, 'xmlns:wsdl', namespaceURI)
        child.setAttributeNS(XMLNS.BASE, 'xmlns:xsd', 'http://www.w3.org/1999/XMLSchema')
        child.setAttributeNS(XMLNS.BASE, 'xmlns:soap', 'http://schemas.xmlsoap.org/wsdl/soap/')
        child.setAttributeNS(XMLNS.BASE, 'xmlns:tns', self.targetNamespace)
        
        if self.name:
            child.setAttributeNS(None, 'name', self.name)

        # wsdl:import
        for item in self.imports: 
            item.toDom()
        # wsdl:message
        for item in self.messages:
            item.toDom()
        # wsdl:portType
        for item in self.portTypes:
            item.toDom()
        # wsdl:binding
        for item in self.bindings:
            item.toDom()
        # wsdl:service
        for item in self.services:
            item.toDom()

    def load(self, document):
        # We save a reference to the DOM document to ensure that elements
        # saved as "extensions" will continue to have a meaningful context
        # for things like namespace references. The lifetime of the DOM
        # document is bound to the lifetime of the WSDL instance.
        self.document = document

        definitions = DOM.getElement(document, 'definitions', None, None)
        if definitions is None:
            raise WSDLError(
                'Missing <definitions> element.'
                )
        self.version = DOM.WSDLUriToVersion(definitions.namespaceURI)
        NS_WSDL = DOM.GetWSDLUri(self.version)

        self.targetNamespace = DOM.getAttr(definitions, 'targetNamespace',
                                           None, None)
        self.name = DOM.getAttr(definitions, 'name', None, None)
        self.documentation = GetDocumentation(definitions)

        # 
        # Retrieve all <wsdl:import>'s, append all children of imported
        # document to main document.  First iteration grab all original 
        # <wsdl:import>'s from document, second iteration grab all 
        # "imported" <wsdl:imports> from document, etc break out when 
        # no more <wsdl:import>'s.
        # 
        imported = []
        base_location = self.location
        do_it = True
        while do_it:
            do_it = False
            for element in DOM.getElements(definitions, 'import', NS_WSDL):
                location = DOM.getAttr(element, 'location')

                if base_location is not None:
                    location = basejoin(base_location, location)
                    
                if location not in imported:
                    do_it = True
                    self._import(document, element, base_location)
                    imported.append(location)
                else:
                    definitions.removeChild(element)

            base_location = None

        # 
        # No more <wsdl:import>'s, now load up all other 
        # WSDL information items.
        # 
        for element in DOM.getElements(definitions, None, None):
            targetNamespace = DOM.getAttr(element, 'targetNamespace')
            localName = element.localName

            if not DOM.nsUriMatch(element.namespaceURI, NS_WSDL):
                if localName == 'schema':
                    tns = DOM.getAttr(element, 'targetNamespace')
                    reader = SchemaReader(base_url=self.imports[tns].location)
                    schema = reader.loadFromNode(WSDLToolsAdapter(self),
                                                 element)
#                    schema.setBaseUrl(self.location)
                    self.types.addSchema(schema)
                else:
                    self.extensions.append(element)
                continue

            elif localName == 'message':
                name = DOM.getAttr(element, 'name')
                docs = GetDocumentation(element)
                message = self.addMessage(name, docs, targetNamespace)
                parts = DOM.getElements(element, 'part', NS_WSDL)
                message.load(parts)
                continue

            elif localName == 'portType':
                name = DOM.getAttr(element, 'name')
                docs = GetDocumentation(element)
                ptype = self.addPortType(name, docs, targetNamespace)
                #operations = DOM.getElements(element, 'operation', NS_WSDL)
                #ptype.load(operations)
                ptype.load(element)
                continue

            elif localName == 'binding':
                name = DOM.getAttr(element, 'name')
                type = DOM.getAttr(element, 'type', default=None)
                if type is None:
                    raise WSDLError(
                        'Missing type attribute for binding %s.' % name
                        )
                type = ParseQName(type, element)
                docs = GetDocumentation(element)
                binding = self.addBinding(name, type, docs, targetNamespace)
                operations = DOM.getElements(element, 'operation', NS_WSDL)
                binding.load(operations)
                binding.load_ex(GetExtensions(element))
                continue

            elif localName == 'service':
                name = DOM.getAttr(element, 'name')
                docs = GetDocumentation(element)
                service = self.addService(name, docs, targetNamespace)
                ports = DOM.getElements(element, 'port', NS_WSDL)
                service.load(ports)
                service.load_ex(GetExtensions(element))
                continue

            elif localName == 'types':
                self.types.documentation = GetDocumentation(element)
                base_location = DOM.getAttr(element, 'base-location')
                if base_location:
                    element.removeAttribute('base-location')
                base_location = base_location or self.location
                reader = SchemaReader(base_url=base_location)
                for item in DOM.getElements(element, None, None):
                    if item.localName == 'schema':
                        schema = reader.loadFromNode(WSDLToolsAdapter(self), item)
                        # XXX <types> could have been imported
                        #schema.setBaseUrl(self.location)
                        schema.setBaseUrl(base_location)
                        self.types.addSchema(schema)
                    else:
                        self.types.addExtension(item)
                # XXX remove the attribute
                # element.removeAttribute('base-location')
                continue

    def _import(self, document, element, base_location=None):
        '''Algo take <import> element's children, clone them,
        and add them to the main document.  Support for relative 
        locations is a bit complicated.  The orig document context
        is lost, so we need to store base location in DOM elements
        representing <types>, by creating a special temporary 
        "base-location" attribute,  and <import>, by resolving
        the relative "location" and storing it as "location".
        
        document -- document we are loading
        element -- DOM Element representing <import> 
        base_location -- location of document from which this
            <import> was gleaned.
        '''
        namespace = DOM.getAttr(element, 'namespace', default=None)
        location = DOM.getAttr(element, 'location', default=None)
        if namespace is None or location is None:
            raise WSDLError(
                'Invalid import element (missing namespace or location).'
                )
        if base_location:
            location = basejoin(base_location, location)
            element.setAttributeNS(None, 'location', location)

        obimport = self.addImport(namespace, location)
        obimport._loaded = 1

        importdoc = DOM.loadFromURL(location)
        try:
            if location.find('#') > -1:
                idref = location.split('#')[-1]
                imported = DOM.getElementById(importdoc, idref)
            else:
                imported = importdoc.documentElement
            if imported is None:
                raise WSDLError(
                    'Import target element not found for: %s' % location
                    )

            imported_tns = DOM.findTargetNS(imported)
            if imported_tns != namespace:
                return

            if imported.localName == 'definitions':
                imported_nodes = imported.childNodes
            else:
                imported_nodes = [imported]
            parent = element.parentNode

            parent.removeChild(element)
            
            for node in imported_nodes:
                if node.nodeType != node.ELEMENT_NODE:
                    continue
                child = DOM.importNode(document, node, 1)
                parent.appendChild(child)
                child.setAttribute('targetNamespace', namespace)
                attrsNS = imported._attrsNS
                for attrkey in attrsNS.keys():
                    if attrkey[0] == DOM.NS_XMLNS:
                        attr = attrsNS[attrkey].cloneNode(1)
                        child.setAttributeNode(attr)

                #XXX Quick Hack, should be in WSDL Namespace.
                if child.localName == 'import':
                    rlocation = child.getAttributeNS(None, 'location')
                    alocation = basejoin(location, rlocation)
                    child.setAttribute('location', alocation)
                elif child.localName == 'types':
                    child.setAttribute('base-location', location)

        finally:
            importdoc.unlink()
        return location

class Element:
    """A class that provides common functions for WSDL element classes."""
    def __init__(self, name=None, documentation=''):
        self.name = name
        self.documentation = documentation
        self.extensions = []

    def addExtension(self, item):
        item.parent = weakref.ref(self)
        self.extensions.append(item)
        
    def getWSDL(self):
        """Return the WSDL object that contains this information item."""
        parent = self
        while 1:
            # skip any collections
            if isinstance(parent, WSDL):
                return parent
            try: parent = parent.parent()
            except: break
            
        return None


class ImportElement(Element):
    def __init__(self, namespace, location):
        self.namespace = namespace
        self.location = location

#    def getWSDL(self):
#        """Return the WSDL object that contains this Message Part."""
#        return self.parent().parent()

    def toDom(self):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, DOM.getElement(wsdl.document, None))
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'import')
        epc.setAttributeNS(None, 'namespace', self.namespace)
        epc.setAttributeNS(None, 'location', self.location)

    _loaded = None


class Types(Collection):
    default = lambda self,k: k.targetNamespace
    def __init__(self, parent):
        Collection.__init__(self, parent)
        self.documentation = ''
        self.extensions = []

    def addSchema(self, schema):
        name = schema.targetNamespace
        self[name] = schema
        return schema

    def addExtension(self, item):
        self.extensions.append(item)


class Message(Element):
    def __init__(self, name, documentation=''):
        Element.__init__(self, name, documentation)
        self.parts = Collection(self)

    def addPart(self, name, type=None, element=None):
        if self.parts.has_key(name):
            raise WSDLError(
                'Duplicate message part element: %s' % name
                )
        if type is None and element is None:
            raise WSDLError(
                'Missing type or element attribute for part: %s' % name
                )
        item = MessagePart(name)
        item.element = element
        item.type = type
        self.parts[name] = item
        return item

    def load(self, elements):
        for element in elements:
            name = DOM.getAttr(element, 'name')
            part = MessagePart(name)
            self.parts[name] = part
            elemref = DOM.getAttr(element, 'element', default=None)
            typeref = DOM.getAttr(element, 'type', default=None)
            if typeref is None and elemref is None:
                raise WSDLError(
                    'No type or element attribute for part: %s' % name
                    )
            if typeref is not None:
                part.type = ParseTypeRef(typeref, element)
            if elemref is not None:
                part.element = ParseTypeRef(elemref, element)

#    def getElementDeclaration(self):
#        """Return the XMLSchema.ElementDeclaration instance or None"""
#        element = None
#        if self.element:
#            nsuri,name = self.element
#            wsdl = self.getWSDL()
#            if wsdl.types.has_key(nsuri) and wsdl.types[nsuri].elements.has_key(name):
#                element = wsdl.types[nsuri].elements[name]
#        return element
#
#    def getTypeDefinition(self):
#        """Return the XMLSchema.TypeDefinition instance or None"""
#        type = None
#        if self.type:
#            nsuri,name = self.type
#            wsdl = self.getWSDL()
#            if wsdl.types.has_key(nsuri) and wsdl.types[nsuri].types.has_key(name):
#                type = wsdl.types[nsuri].types[name]
#        return type

#    def getWSDL(self):
#        """Return the WSDL object that contains this Message Part."""
#        return self.parent().parent()

    def toDom(self):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, DOM.getElement(wsdl.document, None))
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'message')
        epc.setAttributeNS(None, 'name', self.name)

        for part in self.parts:
            part.toDom(epc._getNode())


class MessagePart(Element):
    def __init__(self, name):
        Element.__init__(self, name, '')
        self.element = None
        self.type = None

#    def getWSDL(self):
#        """Return the WSDL object that contains this Message Part."""
#        return self.parent().parent().parent().parent()

    def getTypeDefinition(self):
        wsdl = self.getWSDL()
        nsuri,name = self.type
        schema = wsdl.types.get(nsuri, {})
        return schema.get(name)

    def getElementDeclaration(self):
        wsdl = self.getWSDL()
        nsuri,name = self.element
        schema = wsdl.types.get(nsuri, {})
        return schema.get(name)

    def toDom(self, node):
        """node -- node representing message"""
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'part')
        epc.setAttributeNS(None, 'name', self.name)

        if self.element is not None:
            ns,name = self.element
            prefix = epc.getPrefix(ns)
            epc.setAttributeNS(None, 'element', '%s:%s'%(prefix,name))
        elif self.type is not None:
            ns,name = self.type
            prefix = epc.getPrefix(ns)
            epc.setAttributeNS(None, 'type', '%s:%s'%(prefix,name))


class PortType(Element):
    '''PortType has a anyAttribute, thus must provide for an extensible
       mechanism for supporting such attributes.  ResourceProperties is
       specified in WS-ResourceProperties.   wsa:Action is specified in
       WS-Address.

       Instance Data:
           name -- name attribute
           resourceProperties -- optional. wsr:ResourceProperties attribute,
              value is a QName this is Parsed into a (namespaceURI, name)
              that represents a Global Element Declaration.
           operations
    '''

    def __init__(self, name, documentation=''):
        Element.__init__(self, name, documentation)
        self.operations = Collection(self)
        self.resourceProperties = None

#    def getWSDL(self):
#        return self.parent().parent()

    def getTargetNamespace(self):
        return self.targetNamespace or self.getWSDL().targetNamespace

    def getResourceProperties(self):
        return self.resourceProperties

    def addOperation(self, name, documentation='', parameterOrder=None):
        item = Operation(name, documentation, parameterOrder)
        self.operations[name] = item
        return item

    def load(self, element):
        self.name = DOM.getAttr(element, 'name')
        self.documentation = GetDocumentation(element)
        self.targetNamespace = DOM.getAttr(element, 'targetNamespace')

        for nsuri in WSRF_V1_2.PROPERTIES.XSD_LIST:
            if DOM.hasAttr(element, 'ResourceProperties', nsuri):
                rpref = DOM.getAttr(element, 'ResourceProperties', nsuri)
                self.resourceProperties = ParseQName(rpref, element)

        NS_WSDL = DOM.GetWSDLUri(self.getWSDL().version)
        elements = DOM.getElements(element, 'operation', NS_WSDL)
        for element in elements:
            name = DOM.getAttr(element, 'name')
            docs = GetDocumentation(element)
            param_order = DOM.getAttr(element, 'parameterOrder', default=None)
            if param_order is not None:
                param_order = param_order.split(' ')
            operation = self.addOperation(name, docs, param_order)

            item = DOM.getElement(element, 'input', None, None)
            if item is not None:
                name = DOM.getAttr(item, 'name')
                docs = GetDocumentation(item)
                msgref = DOM.getAttr(item, 'message')
                message = ParseQName(msgref, item)
                for WSA in WSA_LIST + WSAW_LIST:
                    action = DOM.getAttr(item, 'Action', WSA.ADDRESS, None)
                    if action: break
                operation.setInput(message, name, docs, action)

            item = DOM.getElement(element, 'output', None, None)
            if item is not None:
                name = DOM.getAttr(item, 'name')
                docs = GetDocumentation(item)
                msgref = DOM.getAttr(item, 'message')
                message = ParseQName(msgref, item)
                for WSA in WSA_LIST + WSAW_LIST:
                    action = DOM.getAttr(item, 'Action', WSA.ADDRESS, None)
                    if action: break
                operation.setOutput(message, name, docs, action)

            for item in DOM.getElements(element, 'fault', None):
                name = DOM.getAttr(item, 'name')
                docs = GetDocumentation(item)
                msgref = DOM.getAttr(item, 'message')
                message = ParseQName(msgref, item)
                for WSA in WSA_LIST + WSAW_LIST:
                    action = DOM.getAttr(item, 'Action', WSA.ADDRESS, None)
                    if action: break
                operation.addFault(message, name, docs, action)
                
    def toDom(self):
        wsdl = self.getWSDL()

        ep = ElementProxy(None, DOM.getElement(wsdl.document, None))
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'portType')
        epc.setAttributeNS(None, 'name', self.name)
        if self.resourceProperties:
            ns,name = self.resourceProperties
            prefix = epc.getPrefix(ns)
            epc.setAttributeNS(WSRF.PROPERTIES.LATEST, 'ResourceProperties', 
                                '%s:%s'%(prefix,name))

        for op in self.operations:
            op.toDom(epc._getNode())



class Operation(Element):
    def __init__(self, name, documentation='', parameterOrder=None):
        Element.__init__(self, name, documentation)
        self.parameterOrder = parameterOrder
        self.faults = Collection(self)
        self.input = None
        self.output = None

    def getWSDL(self):
        """Return the WSDL object that contains this Operation."""
        return self.parent().parent().parent().parent()

    def getPortType(self):
        return self.parent().parent()

    def getInputAction(self):
        """wsa:Action attribute"""
        return GetWSAActionInput(self)

    def getInputMessage(self):
        if self.input is None:
            return None
        wsdl = self.getPortType().getWSDL()
        return wsdl.messages[self.input.message]

    def getOutputAction(self):
        """wsa:Action attribute"""
        return GetWSAActionOutput(self)

    def getOutputMessage(self):
        if self.output is None:
            return None
        wsdl = self.getPortType().getWSDL()
        return wsdl.messages[self.output.message]

    def getFaultAction(self, name):
        """wsa:Action attribute"""
        return GetWSAActionFault(self, name)

    def getFaultMessage(self, name):
        wsdl = self.getPortType().getWSDL()
        return wsdl.messages[self.faults[name].message]

    def addFault(self, message, name, documentation='', action=None):
        if self.faults.has_key(name):
            raise WSDLError(
                'Duplicate fault element: %s' % name
                )
        item = MessageRole('fault', message, name, documentation, action)
        self.faults[name] = item
        return item

    def setInput(self, message, name='', documentation='', action=None):
        self.input = MessageRole('input', message, name, documentation, action)
        self.input.parent = weakref.ref(self)
        return self.input

    def setOutput(self, message, name='', documentation='', action=None):
        self.output = MessageRole('output', message, name, documentation, action)
        self.output.parent = weakref.ref(self)
        return self.output

    def toDom(self, node):
        wsdl = self.getWSDL()

        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'operation')
        epc.setAttributeNS(None, 'name', self.name)
        node = epc._getNode()
        if self.input:
           self.input.toDom(node)
        if self.output:
           self.output.toDom(node)
        for fault in self.faults:
           fault.toDom(node)


class MessageRole(Element):
    def __init__(self, type, message, name='', documentation='', action=None):
        Element.__init__(self, name, documentation)
        self.message = message
        self.type = type
        self.action = action
        
    def getWSDL(self):
        """Return the WSDL object that contains this information item."""
        parent = self
        while 1:
            # skip any collections
            if isinstance(parent, WSDL):
                return parent
            try: parent = parent.parent()
            except: break
            
        return None

    def getMessage(self):
        """Return the WSDL object that represents the attribute message 
        (namespaceURI, name) tuple
        """
        wsdl = self.getWSDL()
        return wsdl.messages[self.message]

    def toDom(self, node):
        wsdl = self.getWSDL()

        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), self.type)
        if not isinstance(self.message, basestring) and len(self.message) == 2:
            ns,name = self.message
            prefix = epc.getPrefix(ns)
            epc.setAttributeNS(None, 'message', '%s:%s' %(prefix,name))
        else:
            epc.setAttributeNS(None, 'message', self.message)

        if self.action:
            epc.setAttributeNS(WSA.ADDRESS, 'Action', self.action)
            
        if self.name:
            epc.setAttributeNS(None, 'name', self.name)
        

class Binding(Element):
    def __init__(self, name, type, documentation=''):
        Element.__init__(self, name, documentation)
        self.operations = Collection(self)
        self.type = type

#    def getWSDL(self):
#        """Return the WSDL object that contains this binding."""
#        return self.parent().parent()

    def getPortType(self):
        """Return the PortType object associated with this binding."""
        return self.getWSDL().portTypes[self.type]

    def findBinding(self, kind):
        for item in self.extensions:
            if isinstance(item, kind):
                return item
        return None

    def findBindings(self, kind):
        return [ item for item in self.extensions if isinstance(item, kind) ]

    def addOperationBinding(self, name, documentation=''):
        item = OperationBinding(name, documentation)
        self.operations[name] = item
        return item

    def load(self, elements):
        for element in elements:
            name = DOM.getAttr(element, 'name')
            docs = GetDocumentation(element)
            opbinding = self.addOperationBinding(name, docs)
            opbinding.load_ex(GetExtensions(element))

            item = DOM.getElement(element, 'input', None, None)
            if item is not None:
                #TODO: addInputBinding?
                mbinding = MessageRoleBinding('input')
                mbinding.documentation = GetDocumentation(item)
                opbinding.input = mbinding
                mbinding.load_ex(GetExtensions(item))
                mbinding.parent = weakref.ref(opbinding)

            item = DOM.getElement(element, 'output', None, None)
            if item is not None:
                mbinding = MessageRoleBinding('output')
                mbinding.documentation = GetDocumentation(item)
                opbinding.output = mbinding
                mbinding.load_ex(GetExtensions(item))
                mbinding.parent = weakref.ref(opbinding)

            for item in DOM.getElements(element, 'fault', None):
                name = DOM.getAttr(item, 'name')
                mbinding = MessageRoleBinding('fault', name)
                mbinding.documentation = GetDocumentation(item)
                opbinding.faults[name] = mbinding
                mbinding.load_ex(GetExtensions(item))
                mbinding.parent = weakref.ref(opbinding)

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_SOAP_BINDING_ALL and name == 'binding':
                transport = DOM.getAttr(e, 'transport', default=None)
                style = DOM.getAttr(e, 'style', default='document')
                ob = SoapBinding(transport, style)
                self.addExtension(ob)
                continue
            elif ns in DOM.NS_HTTP_BINDING_ALL and name == 'binding':
                verb = DOM.getAttr(e, 'verb')
                ob = HttpBinding(verb)
                self.addExtension(ob)
                continue
            else:
                self.addExtension(e)

    def toDom(self):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, DOM.getElement(wsdl.document, None))
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'binding')
        epc.setAttributeNS(None, 'name', self.name)

        ns,name = self.type
        prefix = epc.getPrefix(ns)
        epc.setAttributeNS(None, 'type', '%s:%s' %(prefix,name))

        node = epc._getNode()
        for ext in self.extensions:
            ext.toDom(node)
        for op_binding in self.operations:
            op_binding.toDom(node)


class OperationBinding(Element):
    def __init__(self, name, documentation=''):
        Element.__init__(self, name, documentation)
        self.input = None
        self.output = None
        self.faults = Collection(self)

#    def getWSDL(self):
#        """Return the WSDL object that contains this binding."""
#        return self.parent().parent().parent().parent()


    def getBinding(self):
        """Return the parent Binding object of the operation binding."""
        return self.parent().parent()

    def getOperation(self):
        """Return the abstract Operation associated with this binding."""
        return self.getBinding().getPortType().operations[self.name]
        
    def findBinding(self, kind):
        for item in self.extensions:
            if isinstance(item, kind):
                return item
        return None

    def findBindings(self, kind):
        return [ item for item in self.extensions if isinstance(item, kind) ]

    def addInputBinding(self, binding):
        if self.input is None:
            self.input = MessageRoleBinding('input')
            self.input.parent = weakref.ref(self)
        self.input.addExtension(binding)
        return binding

    def addOutputBinding(self, binding):
        if self.output is None:
            self.output = MessageRoleBinding('output')
            self.output.parent = weakref.ref(self)
        self.output.addExtension(binding)
        return binding

    def addFaultBinding(self, name, binding):
        fault = self.get(name, None)
        if fault is None:
            fault = MessageRoleBinding('fault', name)
        fault.addExtension(binding)
        return binding

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_SOAP_BINDING_ALL and name == 'operation':
                soapaction = DOM.getAttr(e, 'soapAction', default=None)
                style = DOM.getAttr(e, 'style', default=None)
                ob = SoapOperationBinding(soapaction, style)
                self.addExtension(ob)
                continue
            elif ns in DOM.NS_HTTP_BINDING_ALL and name == 'operation':
                location = DOM.getAttr(e, 'location')
                ob = HttpOperationBinding(location)
                self.addExtension(ob)
                continue
            else:
                self.addExtension(e)

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), 'operation')
        epc.setAttributeNS(None, 'name', self.name)

        node = epc._getNode()
        for ext in self.extensions:
            ext.toDom(node)
        if self.input:
            self.input.toDom(node)
        if self.output:
            self.output.toDom(node)
        for fault in self.faults:
            fault.toDom(node)


class MessageRoleBinding(Element):
    def __init__(self, type, name='', documentation=''):
        Element.__init__(self, name, documentation)
        self.type = type

    def findBinding(self, kind):
        for item in self.extensions:
            if isinstance(item, kind):
                return item
        return None

    def findBindings(self, kind):
        return [ item for item in self.extensions if isinstance(item, kind) ]

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_SOAP_BINDING_ALL and name == 'body':
                encstyle = DOM.getAttr(e, 'encodingStyle', default=None)
                namespace = DOM.getAttr(e, 'namespace', default=None)
                parts = DOM.getAttr(e, 'parts', default=None)
                use = DOM.getAttr(e, 'use', default=None)
                if use is None:
                    raise WSDLError(
                        'Invalid soap:body binding element.'
                        )
                ob = SoapBodyBinding(use, namespace, encstyle, parts)
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_SOAP_BINDING_ALL and name == 'fault':
                encstyle = DOM.getAttr(e, 'encodingStyle', default=None)
                namespace = DOM.getAttr(e, 'namespace', default=None)
                name = DOM.getAttr(e, 'name', default=None)
                use = DOM.getAttr(e, 'use', default=None)
                if use is None or name is None:
                    raise WSDLError(
                        'Invalid soap:fault binding element.'
                        )
                ob = SoapFaultBinding(name, use, namespace, encstyle)
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_SOAP_BINDING_ALL and name in (
                'header', 'headerfault'
                ):
                encstyle = DOM.getAttr(e, 'encodingStyle', default=None)
                namespace = DOM.getAttr(e, 'namespace', default=None)
                message = DOM.getAttr(e, 'message')
                part = DOM.getAttr(e, 'part')
                use = DOM.getAttr(e, 'use')
                if name == 'header':
                    _class = SoapHeaderBinding
                else:
                    _class = SoapHeaderFaultBinding
                message = ParseQName(message, e)
                ob = _class(message, part, use, namespace, encstyle)
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_HTTP_BINDING_ALL and name == 'urlReplacement':
                ob = HttpUrlReplacementBinding()
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_HTTP_BINDING_ALL and name == 'urlEncoded':
                ob = HttpUrlEncodedBinding()
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_MIME_BINDING_ALL and name == 'multipartRelated':
                ob = MimeMultipartRelatedBinding()
                self.addExtension(ob)
                ob.load_ex(GetExtensions(e))
                continue

            elif ns in DOM.NS_MIME_BINDING_ALL and name == 'content':
                part = DOM.getAttr(e, 'part', default=None)
                type = DOM.getAttr(e, 'type', default=None)
                ob = MimeContentBinding(part, type)
                self.addExtension(ob)
                continue

            elif ns in DOM.NS_MIME_BINDING_ALL and name == 'mimeXml':
                part = DOM.getAttr(e, 'part', default=None)
                ob = MimeXmlBinding(part)
                self.addExtension(ob)
                continue

            else:
                self.addExtension(e)

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), self.type)

        node = epc._getNode()
        for item in self.extensions:
            if item: item.toDom(node)


class Service(Element):
    def __init__(self, name, documentation=''):
        Element.__init__(self, name, documentation)
        self.ports = Collection(self)

    def getWSDL(self):
        return self.parent().parent()

    def addPort(self, name, binding, documentation=''):
        item = Port(name, binding, documentation)
        self.ports[name] = item
        return item

    def load(self, elements):
        for element in elements:
            name = DOM.getAttr(element, 'name', default=None)
            docs = GetDocumentation(element)
            binding = DOM.getAttr(element, 'binding', default=None)
            if name is None or binding is None:
                raise WSDLError(
                    'Invalid port element.'
                    )
            binding = ParseQName(binding, element)
            port = self.addPort(name, binding, docs)
            port.load_ex(GetExtensions(element))

    def load_ex(self, elements):
        for e in elements:
            self.addExtension(e)

    def toDom(self):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, DOM.getElement(wsdl.document, None))
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), "service")
        epc.setAttributeNS(None, "name", self.name)

        node = epc._getNode()
        for port in self.ports:
            port.toDom(node)


class Port(Element):
    def __init__(self, name, binding, documentation=''):
        Element.__init__(self, name, documentation)
        self.binding = binding

#    def getWSDL(self):
#        return self.parent().parent().getWSDL()

    def getService(self):
        """Return the Service object associated with this port."""
        return self.parent().parent()

    def getBinding(self):
        """Return the Binding object that is referenced by this port."""
        wsdl = self.getService().getWSDL()
        return wsdl.bindings[self.binding]

    def getPortType(self):
        """Return the PortType object that is referenced by this port."""
        wsdl = self.getService().getWSDL()
        binding = wsdl.bindings[self.binding]
        return wsdl.portTypes[binding.type]

    def getAddressBinding(self):
        """A convenience method to obtain the extension element used
           as the address binding for the port."""
        for item in self.extensions:
            if isinstance(item, SoapAddressBinding) or \
               isinstance(item, HttpAddressBinding):
                return item
        raise WSDLError(
            'No address binding found in port.'
            )

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_SOAP_BINDING_ALL and name == 'address':
                location = DOM.getAttr(e, 'location', default=None)
                ob = SoapAddressBinding(location)
                self.addExtension(ob)
                continue
            elif ns in DOM.NS_HTTP_BINDING_ALL and name == 'address':
                location = DOM.getAttr(e, 'location', default=None)
                ob = HttpAddressBinding(location)
                self.addExtension(ob)
                continue
            else:
                self.addExtension(e)

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLUri(wsdl.version), "port")
        epc.setAttributeNS(None, "name", self.name)

        ns,name = self.binding
        prefix = epc.getPrefix(ns)
        epc.setAttributeNS(None, "binding", "%s:%s" %(prefix,name))

        node = epc._getNode()
        for ext in self.extensions:
            ext.toDom(node)


class SoapBinding:
    def __init__(self, transport, style='rpc'):
        self.transport = transport
        self.style = style

    def getWSDL(self):
        return self.parent().getWSDL()

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLSoapBindingUri(wsdl.version), 'binding')
        if self.transport:
            epc.setAttributeNS(None, "transport", self.transport)
        if self.style:
            epc.setAttributeNS(None, "style", self.style)

class SoapAddressBinding:
    def __init__(self, location):
        self.location = location

    def getWSDL(self):
        return self.parent().getWSDL()

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLSoapBindingUri(wsdl.version), 'address')
        epc.setAttributeNS(None, "location", self.location)


class SoapOperationBinding:
    def __init__(self, soapAction=None, style=None):
        self.soapAction = soapAction
        self.style = style

    def getWSDL(self):
        return self.parent().getWSDL()

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLSoapBindingUri(wsdl.version), 'operation')
        if self.soapAction:
            epc.setAttributeNS(None, 'soapAction', self.soapAction)
        if self.style:
            epc.setAttributeNS(None, 'style', self.style)


class SoapBodyBinding:
    def __init__(self, use, namespace=None, encodingStyle=None, parts=None):
        if not use in ('literal', 'encoded'):
            raise WSDLError(
                'Invalid use attribute value: %s' % use
                )
        self.encodingStyle = encodingStyle
        self.namespace = namespace
        if type(parts) in (type(''), type(u'')):
            parts = parts.split()
        self.parts = parts
        self.use = use

    def getWSDL(self):
        return self.parent().getWSDL()

    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLSoapBindingUri(wsdl.version), 'body')
        epc.setAttributeNS(None, "use", self.use)
        epc.setAttributeNS(None, "namespace", self.namespace)


class SoapFaultBinding:
    def __init__(self, name, use, namespace=None, encodingStyle=None):
        if not use in ('literal', 'encoded'):
            raise WSDLError(
                'Invalid use attribute value: %s' % use
                )
        self.encodingStyle = encodingStyle
        self.namespace = namespace
        self.name = name
        self.use = use
        
    def getWSDL(self):
        return self.parent().getWSDL()
    
    def toDom(self, node):
        wsdl = self.getWSDL()
        ep = ElementProxy(None, node)
        epc = ep.createAppendElement(DOM.GetWSDLSoapBindingUri(wsdl.version), 'body')
        epc.setAttributeNS(None, "use", self.use)
        epc.setAttributeNS(None, "name", self.name)
        if self.namespace is not None:
            epc.setAttributeNS(None, "namespace", self.namespace)
        if self.encodingStyle is not None:
            epc.setAttributeNS(None, "encodingStyle", self.encodingStyle)


class SoapHeaderBinding:
    def __init__(self, message, part, use, namespace=None, encodingStyle=None):
        if not use in ('literal', 'encoded'):
            raise WSDLError(
                'Invalid use attribute value: %s' % use
                )
        self.encodingStyle = encodingStyle
        self.namespace = namespace
        self.message = message
        self.part = part
        self.use = use

    tagname = 'header'

class SoapHeaderFaultBinding(SoapHeaderBinding):
    tagname = 'headerfault'


class HttpBinding:
    def __init__(self, verb):
        self.verb = verb

class HttpAddressBinding:
    def __init__(self, location):
        self.location = location


class HttpOperationBinding:
    def __init__(self, location):
        self.location = location

class HttpUrlReplacementBinding:
    pass


class HttpUrlEncodedBinding:
    pass


class MimeContentBinding:
    def __init__(self, part=None, type=None):
        self.part = part
        self.type = type


class MimeXmlBinding:
    def __init__(self, part=None):
        self.part = part


class MimeMultipartRelatedBinding:
    def __init__(self):
        self.parts = []

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_MIME_BINDING_ALL and name == 'part':
                self.parts.append(MimePartBinding())
                continue


class MimePartBinding:
    def __init__(self):
        self.items = []

    def load_ex(self, elements):
        for e in elements:
            ns, name = e.namespaceURI, e.localName
            if ns in DOM.NS_MIME_BINDING_ALL and name == 'content':
                part = DOM.getAttr(e, 'part', default=None)
                type = DOM.getAttr(e, 'type', default=None)
                ob = MimeContentBinding(part, type)
                self.items.append(ob)
                continue

            elif ns in DOM.NS_MIME_BINDING_ALL and name == 'mimeXml':
                part = DOM.getAttr(e, 'part', default=None)
                ob = MimeXmlBinding(part)
                self.items.append(ob)
                continue

            elif ns in DOM.NS_SOAP_BINDING_ALL and name == 'body':
                encstyle = DOM.getAttr(e, 'encodingStyle', default=None)
                namespace = DOM.getAttr(e, 'namespace', default=None)
                parts = DOM.getAttr(e, 'parts', default=None)
                use = DOM.getAttr(e, 'use', default=None)
                if use is None:
                    raise WSDLError(
                        'Invalid soap:body binding element.'
                        )
                ob = SoapBodyBinding(use, namespace, encstyle, parts)
                self.items.append(ob)
                continue


class WSDLError(Exception):
    pass



def DeclareNSPrefix(writer, prefix, nsuri):
    if writer.hasNSPrefix(nsuri):
        return
    writer.declareNSPrefix(prefix, nsuri)

def ParseTypeRef(value, element):
    parts = value.split(':', 1)
    if len(parts) == 1:
        return (DOM.findTargetNS(element), value)
    nsuri = DOM.findNamespaceURI(parts[0], element)
    return (nsuri, parts[1])

def ParseQName(value, element):
    nameref = value.split(':', 1)
    if len(nameref) == 2:
        nsuri = DOM.findNamespaceURI(nameref[0], element)
        name = nameref[-1]
    else:
        nsuri = DOM.findTargetNS(element)
        name  = nameref[-1]
    return nsuri, name

def GetDocumentation(element):
    docnode = DOM.getElement(element, 'documentation', None, None)
    if docnode is not None:
        return DOM.getElementText(docnode)
    return ''

def GetExtensions(element):
    return [ item for item in DOM.getElements(element, None, None)
        if item.namespaceURI != DOM.NS_WSDL ]

def GetWSAActionFault(operation, name):
    """Find wsa:Action attribute, and return value or WSA.FAULT
       for the default.
    """
    attr = operation.faults[name].action
    if attr is not None:
        return attr
    return WSA.FAULT

def GetWSAActionInput(operation):
    """Find wsa:Action attribute, and return value or the default."""
    attr = operation.input.action
    if attr is not None:
        return attr
    portType = operation.getPortType()
    targetNamespace = portType.getTargetNamespace()
    ptName = portType.name
    msgName = operation.input.name
    if not msgName:
        msgName = operation.name + 'Request'
    if targetNamespace.endswith('/'):
        return '%s%s/%s' %(targetNamespace, ptName, msgName)
    return '%s/%s/%s' %(targetNamespace, ptName, msgName)

def GetWSAActionOutput(operation):
    """Find wsa:Action attribute, and return value or the default."""
    attr = operation.output.action
    if attr is not None:
        return attr
    targetNamespace = operation.getPortType().getTargetNamespace()
    ptName = operation.getPortType().name
    msgName = operation.output.name
    if not msgName:
        msgName = operation.name + 'Response'
    if targetNamespace.endswith('/'):
        return '%s%s/%s' %(targetNamespace, ptName, msgName)
    return '%s/%s/%s' %(targetNamespace, ptName, msgName)

def FindExtensions(object, kind, t_type=type(())):
    if isinstance(kind, t_type):
        result = []
        namespaceURI, name = kind
        return [ item for item in object.extensions
                if hasattr(item, 'nodeType') \
                and DOM.nsUriMatch(namespaceURI, item.namespaceURI) \
                and item.name == name ]
    return [ item for item in object.extensions if isinstance(item, kind) ]

def FindExtension(object, kind, t_type=type(())):
    if isinstance(kind, t_type):
        namespaceURI, name = kind
        for item in object.extensions:
            if hasattr(item, 'nodeType') \
            and DOM.nsUriMatch(namespaceURI, item.namespaceURI) \
            and item.name == name:
                return item
    else:
        for item in object.extensions:
            if isinstance(item, kind):
                return item
    return None


class SOAPCallInfo:
    """SOAPCallInfo captures the important binding information about a 
       SOAP operation, in a structure that is easier to work with than
       raw WSDL structures."""

    def __init__(self, methodName):
        self.methodName = methodName
        self.inheaders = []
        self.outheaders = []
        self.inparams = []
        self.outparams = []
        self.retval = None

    encodingStyle = DOM.NS_SOAP_ENC
    documentation = ''
    soapAction = None
    transport = None
    namespace = None
    location = None
    use = 'encoded'
    style = 'rpc'

    def addInParameter(self, name, type, namespace=None, element_type=0):
        """Add an input parameter description to the call info."""
        parameter = ParameterInfo(name, type, namespace, element_type)
        self.inparams.append(parameter)
        return parameter

    def addOutParameter(self, name, type, namespace=None, element_type=0):
        """Add an output parameter description to the call info."""
        parameter = ParameterInfo(name, type, namespace, element_type)
        self.outparams.append(parameter)
        return parameter

    def setReturnParameter(self, name, type, namespace=None, element_type=0):
        """Set the return parameter description for the call info."""
        parameter = ParameterInfo(name, type, namespace, element_type)
        self.retval = parameter
        return parameter

    def addInHeaderInfo(self, name, type, namespace, element_type=0,
                        mustUnderstand=0):
        """Add an input SOAP header description to the call info."""
        headerinfo = HeaderInfo(name, type, namespace, element_type)
        if mustUnderstand:
            headerinfo.mustUnderstand = 1
        self.inheaders.append(headerinfo)
        return headerinfo

    def addOutHeaderInfo(self, name, type, namespace, element_type=0,
                         mustUnderstand=0):
        """Add an output SOAP header description to the call info."""
        headerinfo = HeaderInfo(name, type, namespace, element_type)
        if mustUnderstand:
            headerinfo.mustUnderstand = 1
        self.outheaders.append(headerinfo)
        return headerinfo

    def getInParameters(self):
        """Return a sequence of the in parameters of the method."""
        return self.inparams

    def getOutParameters(self):
        """Return a sequence of the out parameters of the method."""
        return self.outparams

    def getReturnParameter(self):
        """Return param info about the return value of the method."""
        return self.retval

    def getInHeaders(self):
        """Return a sequence of the in headers of the method."""
        return self.inheaders

    def getOutHeaders(self):
        """Return a sequence of the out headers of the method."""
        return self.outheaders


class ParameterInfo:
    """A ParameterInfo object captures parameter binding information."""
    def __init__(self, name, type, namespace=None, element_type=0):
        if element_type:
            self.element_type = 1
        if namespace is not None:
            self.namespace = namespace
        self.name = name
        self.type = type

    element_type = 0
    namespace = None
    default = None


class HeaderInfo(ParameterInfo):
    """A HeaderInfo object captures SOAP header binding information."""
    def __init__(self, name, type, namespace, element_type=None):
        ParameterInfo.__init__(self, name, type, namespace, element_type)

    mustUnderstand = 0
    actor = None


def callInfoFromWSDL(port, name):
    """Return a SOAPCallInfo given a WSDL port and operation name."""
    wsdl = port.getService().getWSDL()
    binding = port.getBinding()
    portType = binding.getPortType()
    operation = portType.operations[name]
    opbinding = binding.operations[name]
    messages = wsdl.messages
    callinfo = SOAPCallInfo(name)

    addrbinding = port.getAddressBinding()
    if not isinstance(addrbinding, SoapAddressBinding):
        raise ValueError, 'Unsupported binding type.'        
    callinfo.location = addrbinding.location

    soapbinding = binding.findBinding(SoapBinding)
    if soapbinding is None:
        raise ValueError, 'Missing soap:binding element.'
    callinfo.transport = soapbinding.transport
    callinfo.style = soapbinding.style or 'document'

    soap_op_binding = opbinding.findBinding(SoapOperationBinding)
    if soap_op_binding is not None:
        callinfo.soapAction = soap_op_binding.soapAction
        callinfo.style = soap_op_binding.style or callinfo.style

    parameterOrder = operation.parameterOrder

    if operation.input is not None:
        message = messages[operation.input.message]
        msgrole = opbinding.input

        mime = msgrole.findBinding(MimeMultipartRelatedBinding)
        if mime is not None:
            raise ValueError, 'Mime bindings are not supported.'
        else:
            for item in msgrole.findBindings(SoapHeaderBinding):
                part = messages[item.message].parts[item.part]
                header = callinfo.addInHeaderInfo(
                    part.name,
                    part.element or part.type,
                    item.namespace,
                    element_type = part.element and 1 or 0
                    )
                header.encodingStyle = item.encodingStyle

            body = msgrole.findBinding(SoapBodyBinding)
            if body is None:
                raise ValueError, 'Missing soap:body binding.'
            callinfo.encodingStyle = body.encodingStyle
            callinfo.namespace = body.namespace
            callinfo.use = body.use

            if body.parts is not None:
                parts = []
                for name in body.parts:
                    parts.append(message.parts[name])
            else:
                parts = message.parts.values()

            for part in parts:
                callinfo.addInParameter(
                    part.name,
                    part.element or part.type,
                    element_type = part.element and 1 or 0
                    )

    if operation.output is not None:
        try:
            message = messages[operation.output.message]
        except KeyError:
            if self.strict:
                raise RuntimeError(
                    "Recieved message not defined in the WSDL schema: %s" %
                    operation.output.message)
            else:
                message = wsdl.addMessage(operation.output.message)
                print "Warning:", \
                      "Recieved message not defined in the WSDL schema.", \
                      "Adding it."
                print "Message:", operation.output.message
         
        msgrole = opbinding.output

        mime = msgrole.findBinding(MimeMultipartRelatedBinding)
        if mime is not None:
            raise ValueError, 'Mime bindings are not supported.'
        else:
            for item in msgrole.findBindings(SoapHeaderBinding):
                part = messages[item.message].parts[item.part]
                header = callinfo.addOutHeaderInfo(
                    part.name,
                    part.element or part.type,
                    item.namespace,
                    element_type = part.element and 1 or 0
                    )
                header.encodingStyle = item.encodingStyle

            body = msgrole.findBinding(SoapBodyBinding)
            if body is None:
                raise ValueError, 'Missing soap:body binding.'
            callinfo.encodingStyle = body.encodingStyle
            callinfo.namespace = body.namespace
            callinfo.use = body.use

            if body.parts is not None:
                parts = []
                for name in body.parts:
                    parts.append(message.parts[name])
            else:
                parts = message.parts.values()

            if parts:
                for part in parts:
                    callinfo.addOutParameter(
                        part.name,
                        part.element or part.type,
                        element_type = part.element and 1 or 0
                        )

    return callinfo

########NEW FILE########
__FILENAME__ = XMLname
"""Translate strings to and from SOAP 1.2 XML name encoding

Implements rules for mapping application defined name to XML names
specified by the w3 SOAP working group for SOAP version 1.2 in
Appendix A of "SOAP Version 1.2 Part 2: Adjuncts", W3C Working Draft
17, December 2001, <http://www.w3.org/TR/soap12-part2/#namemap>

Also see <http://www.w3.org/2000/xp/Group/xmlp-issues>.

Author: Gregory R. Warnes <Gregory.R.Warnes@Pfizer.com>
Date::  2002-04-25
Version 0.9.0

"""

ident = "$Id$"

from re import *


def _NCNameChar(x):
    return x.isalpha() or x.isdigit() or x=="." or x=='-' or x=="_" 


def _NCNameStartChar(x):
    return x.isalpha() or x=="_" 


def _toUnicodeHex(x):
    hexval = hex(ord(x[0]))[2:]
    hexlen = len(hexval)
    # Make hexval have either 4 or 8 digits by prepending 0's
    if   (hexlen==1): hexval = "000" + hexval
    elif (hexlen==2): hexval = "00"  + hexval
    elif (hexlen==3): hexval = "0"   + hexval
    elif (hexlen==4): hexval = ""    + hexval
    elif (hexlen==5): hexval = "000" + hexval
    elif (hexlen==6): hexval = "00"  + hexval
    elif (hexlen==7): hexval = "0"   + hexval
    elif (hexlen==8): hexval = ""    + hexval    
    else: raise Exception, "Illegal Value returned from hex(ord(x))"
    
    return "_x"+ hexval + "_"


def _fromUnicodeHex(x):
    return eval( r'u"\u'+x[2:-1]+'"' ) 


def toXMLname(string):
    """Convert string to a XML name."""
    if string.find(':') != -1 :
        (prefix, localname) = string.split(':',1)
    else:
        prefix = None
        localname = string
    
    T = unicode(localname)

    N = len(localname)
    X = [];
    for i in range(N) :
        if i< N-1 and T[i]==u'_' and T[i+1]==u'x':
            X.append(u'_x005F_')
        elif i==0 and N >= 3 and \
                 ( T[0]==u'x' or T[0]==u'X' ) and \
                 ( T[1]==u'm' or T[1]==u'M' ) and \
                 ( T[2]==u'l' or T[2]==u'L' ):
            X.append(u'_xFFFF_' + T[0])
        elif (not _NCNameChar(T[i])) or (i==0 and not _NCNameStartChar(T[i])):
            X.append(_toUnicodeHex(T[i]))
        else:
            X.append(T[i])
    
    if prefix:
        return "%s:%s" % (prefix, u''.join(X))
    return u''.join(X)


def fromXMLname(string):
    """Convert XML name to unicode string."""

    retval = sub(r'_xFFFF_','', string )

    def fun( matchobj ):
        return _fromUnicodeHex( matchobj.group(0) )

    retval = sub(r'_x[0-9A-Za-z]+_', fun, retval )
        
    return retval

########NEW FILE########
__FILENAME__ = XMLSchema
# Copyright (c) 2003, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory (subject to receipt of
# any required approvals from the U.S. Dept. of Energy).  All rights
# reserved. 
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.

ident = "$Id$"

import types, weakref, sys, warnings
from Namespaces import SCHEMA, XMLNS, SOAP, APACHE
from Utility import DOM, DOMException, Collection, SplitQName, basejoin
from StringIO import StringIO

# If we have no threading, this should be a no-op
try:
    from threading import RLock
except ImportError:
    class RLock:
        def acquire():
            pass
        def release():
            pass

# 
# Collections in XMLSchema class
# 
TYPES = 'types'
ATTRIBUTE_GROUPS = 'attr_groups'
ATTRIBUTES = 'attr_decl'
ELEMENTS = 'elements'
MODEL_GROUPS = 'model_groups'
BUILT_IN_NAMESPACES = [SOAP.ENC,] + SCHEMA.XSD_LIST + [APACHE.AXIS_NS]

def GetSchema(component):
    """convience function for finding the parent XMLSchema instance.
    """
    parent = component
    while not isinstance(parent, XMLSchema):
        parent = parent._parent()
    return parent
    
class SchemaReader:
    """A SchemaReader creates XMLSchema objects from urls and xml data.
    """
    
    namespaceToSchema = {}
    
    def __init__(self, domReader=None, base_url=None):
        """domReader -- class must implement DOMAdapterInterface
           base_url -- base url string
        """
        self.__base_url = base_url
        self.__readerClass = domReader
        if not self.__readerClass:
            self.__readerClass = DOMAdapter
        self._includes = {}
        self._imports = {}

    def __setImports(self, schema):
        """Add dictionary of imports to schema instance.
           schema -- XMLSchema instance
        """
        for ns,val in schema.imports.items(): 
            if self._imports.has_key(ns):
                schema.addImportSchema(self._imports[ns])

    def __setIncludes(self, schema):
        """Add dictionary of includes to schema instance.
           schema -- XMLSchema instance
        """
        for schemaLocation, val in schema.includes.items(): 
            if self._includes.has_key(schemaLocation):
                schema.addIncludeSchema(schemaLocation, self._imports[schemaLocation])

    def addSchemaByLocation(self, location, schema):
        """provide reader with schema document for a location.
        """
        self._includes[location] = schema

    def addSchemaByNamespace(self, schema):
        """provide reader with schema document for a targetNamespace.
        """
        self._imports[schema.targetNamespace] = schema

    def loadFromNode(self, parent, element):
        """element -- DOM node or document
           parent -- WSDLAdapter instance
        """
        reader = self.__readerClass(element)
        schema = XMLSchema(parent)
        #HACK to keep a reference
        schema.wsdl = parent
        schema.setBaseUrl(self.__base_url)
        schema.load(reader)
        return schema
        
    def loadFromStream(self, file, url=None):
        """Return an XMLSchema instance loaded from a file object.
           file -- file object
           url -- base location for resolving imports/includes.
        """
        reader = self.__readerClass()
        reader.loadDocument(file)
        schema = XMLSchema()
        if url is not None:
             schema.setBaseUrl(url)
        schema.load(reader)
        self.__setIncludes(schema)
        self.__setImports(schema)
        return schema

    def loadFromString(self, data):
        """Return an XMLSchema instance loaded from an XML string.
           data -- XML string
        """
        return self.loadFromStream(StringIO(data))

    def loadFromURL(self, url, schema=None):
        """Return an XMLSchema instance loaded from the given url.
           url -- URL to dereference
           schema -- Optional XMLSchema instance.
        """
        reader = self.__readerClass()
        if self.__base_url:
            url = basejoin(self.__base_url,url)

        reader.loadFromURL(url)
        schema = schema or XMLSchema()
        schema.setBaseUrl(url)
        schema.load(reader)
        self.__setIncludes(schema)
        self.__setImports(schema)
        return schema

    def loadFromFile(self, filename):
        """Return an XMLSchema instance loaded from the given file.
           filename -- name of file to open
        """
        if self.__base_url:
            filename = basejoin(self.__base_url,filename)
        file = open(filename, 'rb')
        try:
            schema = self.loadFromStream(file, filename)
        finally:
            file.close()

        return schema


class SchemaError(Exception): 
    pass

class NoSchemaLocationWarning(Exception): 
    pass


###########################
# DOM Utility Adapters 
##########################
class DOMAdapterInterface:
    def hasattr(self, attr, ns=None):
        """return true if node has attribute 
           attr -- attribute to check for
           ns -- namespace of attribute, by default None
        """
        raise NotImplementedError, 'adapter method not implemented'

    def getContentList(self, *contents):
        """returns an ordered list of child nodes
           *contents -- list of node names to return
        """
        raise NotImplementedError, 'adapter method not implemented'

    def setAttributeDictionary(self, attributes):
        """set attribute dictionary
        """
        raise NotImplementedError, 'adapter method not implemented'

    def getAttributeDictionary(self):
        """returns a dict of node's attributes
        """
        raise NotImplementedError, 'adapter method not implemented'

    def getNamespace(self, prefix):
        """returns namespace referenced by prefix.
        """
        raise NotImplementedError, 'adapter method not implemented'

    def getTagName(self):
        """returns tagName of node
        """
        raise NotImplementedError, 'adapter method not implemented'


    def getParentNode(self):
        """returns parent element in DOMAdapter or None
        """
        raise NotImplementedError, 'adapter method not implemented'

    def loadDocument(self, file):
        """load a Document from a file object
           file --
        """
        raise NotImplementedError, 'adapter method not implemented'

    def loadFromURL(self, url):
        """load a Document from an url
           url -- URL to dereference
        """
        raise NotImplementedError, 'adapter method not implemented'


class DOMAdapter(DOMAdapterInterface):
    """Adapter for ZSI.Utility.DOM
    """
    def __init__(self, node=None):
        """Reset all instance variables.
           element -- DOM document, node, or None
        """
        if hasattr(node, 'documentElement'):
            self.__node = node.documentElement
        else:
            self.__node = node
        self.__attributes = None

    def getNode(self):
        return self.__node
    
    def hasattr(self, attr, ns=None):
        """attr -- attribute 
           ns -- optional namespace, None means unprefixed attribute.
        """
        if not self.__attributes:
            self.setAttributeDictionary()
        if ns:
            return self.__attributes.get(ns,{}).has_key(attr)
        return self.__attributes.has_key(attr)

    def getContentList(self, *contents):
        nodes = []
        ELEMENT_NODE = self.__node.ELEMENT_NODE
        for child in DOM.getElements(self.__node, None):
            if child.nodeType == ELEMENT_NODE and\
               SplitQName(child.tagName)[1] in contents:
                nodes.append(child)
        return map(self.__class__, nodes)

    def setAttributeDictionary(self):
        self.__attributes = {}
        for v in self.__node._attrs.values():
            self.__attributes[v.nodeName] = v.nodeValue

    def getAttributeDictionary(self):
        if not self.__attributes:
            self.setAttributeDictionary()
        return self.__attributes

    def getTagName(self):
        return self.__node.tagName

    def getParentNode(self):
        if self.__node.parentNode.nodeType == self.__node.ELEMENT_NODE:
            return DOMAdapter(self.__node.parentNode)
        return None

    def getNamespace(self, prefix):
        """prefix -- deference namespace prefix in node's context.
           Ascends parent nodes until found.
        """
        namespace = None
        if prefix == 'xmlns':
            namespace = DOM.findDefaultNS(prefix, self.__node)
        else:
            try:
                namespace = DOM.findNamespaceURI(prefix, self.__node)
            except DOMException, ex:
                if prefix != 'xml':
                    raise SchemaError, '%s namespace not declared for %s'\
                        %(prefix, self.__node._get_tagName())
                namespace = XMLNS.XML
        return namespace
           
    def loadDocument(self, file):
        self.__node = DOM.loadDocument(file)
        if hasattr(self.__node, 'documentElement'):
            self.__node = self.__node.documentElement

    def loadFromURL(self, url):
        self.__node = DOM.loadFromURL(url)
        if hasattr(self.__node, 'documentElement'):
            self.__node = self.__node.documentElement

 
class XMLBase: 
    """ These class variables are for string indentation.
    """ 
    tag = None
    __indent = 0
    __rlock = RLock()

    def __str__(self):
        XMLBase.__rlock.acquire()
        XMLBase.__indent += 1
        tmp = "<" + str(self.__class__) + '>\n'
        for k,v in self.__dict__.items():
            tmp += "%s* %s = %s\n" %(XMLBase.__indent*'  ', k, v)
        XMLBase.__indent -= 1 
        XMLBase.__rlock.release()
        return tmp


"""Marker Interface:  can determine something about an instances properties by using 
        the provided convenience functions.

"""
class DefinitionMarker: 
    """marker for definitions
    """
    pass

class DeclarationMarker: 
    """marker for declarations
    """
    pass

class AttributeMarker: 
    """marker for attributes
    """
    pass

class AttributeGroupMarker: 
    """marker for attribute groups
    """
    pass

class WildCardMarker: 
    """marker for wildcards
    """
    pass

class ElementMarker: 
    """marker for wildcards
    """
    pass

class ReferenceMarker: 
    """marker for references
    """
    pass

class ModelGroupMarker: 
    """marker for model groups
    """
    pass

class AllMarker(ModelGroupMarker): 
    """marker for all model group
    """
    pass

class ChoiceMarker(ModelGroupMarker): 
    """marker for choice model group
    """
    pass

class SequenceMarker(ModelGroupMarker): 
    """marker for sequence model group
    """
    pass

class ExtensionMarker: 
    """marker for extensions
    """
    pass

class RestrictionMarker: 
    """marker for restrictions
    """
    facets = ['enumeration', 'length', 'maxExclusive', 'maxInclusive',\
        'maxLength', 'minExclusive', 'minInclusive', 'minLength',\
        'pattern', 'fractionDigits', 'totalDigits', 'whiteSpace']

class SimpleMarker: 
    """marker for simple type information
    """
    pass

class ListMarker: 
    """marker for simple type list
    """
    pass

class UnionMarker: 
    """marker for simple type Union
    """
    pass


class ComplexMarker: 
    """marker for complex type information
    """
    pass

class LocalMarker: 
    """marker for complex type information
    """
    pass


class MarkerInterface:
    def isDefinition(self):
        return isinstance(self, DefinitionMarker)

    def isDeclaration(self):
        return isinstance(self, DeclarationMarker)

    def isAttribute(self):
        return isinstance(self, AttributeMarker)

    def isAttributeGroup(self):
        return isinstance(self, AttributeGroupMarker)

    def isElement(self):
        return isinstance(self, ElementMarker)

    def isReference(self):
        return isinstance(self, ReferenceMarker)

    def isWildCard(self):
        return isinstance(self, WildCardMarker)

    def isModelGroup(self):
        return isinstance(self, ModelGroupMarker)

    def isAll(self):
        return isinstance(self, AllMarker)

    def isChoice(self):
        return isinstance(self, ChoiceMarker)

    def isSequence(self):
        return isinstance(self, SequenceMarker)

    def isExtension(self):
        return isinstance(self, ExtensionMarker)

    def isRestriction(self):
        return isinstance(self, RestrictionMarker)

    def isSimple(self):
        return isinstance(self, SimpleMarker)

    def isComplex(self):
        return isinstance(self, ComplexMarker)

    def isLocal(self):
        return isinstance(self, LocalMarker)

    def isList(self):
        return isinstance(self, ListMarker)

    def isUnion(self):
        return isinstance(self, UnionMarker)


##########################################################
# Schema Components
#########################################################
class XMLSchemaComponent(XMLBase, MarkerInterface):
    """
       class variables: 
           required -- list of required attributes
           attributes -- dict of default attribute values, including None.
               Value can be a function for runtime dependencies.
           contents -- dict of namespace keyed content lists.
               'xsd' content of xsd namespace.
           xmlns_key -- key for declared xmlns namespace.
           xmlns -- xmlns is special prefix for namespace dictionary
           xml -- special xml prefix for xml namespace.
    """
    required = []
    attributes = {}
    contents = {}
    xmlns_key = ''
    xmlns = 'xmlns'
    xml = 'xml'

    def __init__(self, parent=None):
        """parent -- parent instance
           instance variables:
               attributes -- dictionary of node's attributes
        """
        self.attributes = None
        self._parent = parent
        if self._parent:
            self._parent = weakref.ref(parent)

        if not self.__class__ == XMLSchemaComponent\
           and not (type(self.__class__.required) == type(XMLSchemaComponent.required)\
           and type(self.__class__.attributes) == type(XMLSchemaComponent.attributes)\
           and type(self.__class__.contents) == type(XMLSchemaComponent.contents)):
            raise RuntimeError, 'Bad type for a class variable in %s' %self.__class__

    def getItemTrace(self):
        """Returns a node trace up to the <schema> item.
        """
        item, path, name, ref = self, [], 'name', 'ref'
        while not isinstance(item,XMLSchema) and not isinstance(item,WSDLToolsAdapter):
            attr = item.getAttribute(name)
            if not attr:
                attr = item.getAttribute(ref)
                if not attr:
                    path.append('<%s>' %(item.tag))
                else: 
                    path.append('<%s ref="%s">' %(item.tag, attr))
            else:
                path.append('<%s name="%s">' %(item.tag,attr))

            item = item._parent()
        try:
            tns = item.getTargetNamespace()
        except: 
            tns = ''
        path.append('<%s targetNamespace="%s">' %(item.tag, tns))
        path.reverse()
        return ''.join(path)

    def getTargetNamespace(self):
        """return targetNamespace
        """
        parent = self
        targetNamespace = 'targetNamespace'
        tns = self.attributes.get(targetNamespace)
        while not tns and parent and parent._parent is not None:
            parent = parent._parent()
            tns = parent.attributes.get(targetNamespace)
        return tns or ''

    def getAttributeDeclaration(self, attribute):
        """attribute -- attribute with a QName value (eg. type).
           collection -- check types collection in parent Schema instance
        """
        return self.getQNameAttribute(ATTRIBUTES, attribute)

    def getAttributeGroup(self, attribute):
        """attribute -- attribute with a QName value (eg. type).
           collection -- check types collection in parent Schema instance
        """
        return self.getQNameAttribute(ATTRIBUTE_GROUPS, attribute)

    def getTypeDefinition(self, attribute):
        """attribute -- attribute with a QName value (eg. type).
           collection -- check types collection in parent Schema instance
        """
        return self.getQNameAttribute(TYPES, attribute)

    def getElementDeclaration(self, attribute):
        """attribute -- attribute with a QName value (eg. element).
           collection -- check elements collection in parent Schema instance.
        """
        return self.getQNameAttribute(ELEMENTS, attribute)

    def getModelGroup(self, attribute):
        """attribute -- attribute with a QName value (eg. ref).
           collection -- check model_group collection in parent Schema instance.
        """
        return self.getQNameAttribute(MODEL_GROUPS, attribute)

    def getQNameAttribute(self, collection, attribute):
        """returns object instance representing QName --> (namespace,name),
           or if does not exist return None.
           attribute -- an information item attribute, with a QName value.
           collection -- collection in parent Schema instance to search.
        """
        tdc = self.getAttributeQName(attribute)
        if not tdc:
            return

        obj = self.getSchemaItem(collection, tdc.getTargetNamespace(), tdc.getName())
        if obj: 
            return obj

#        raise SchemaError, 'No schema item "%s" in collection %s' %(tdc, collection)
        return

    def getSchemaItem(self, collection, namespace, name):
        """returns object instance representing namespace, name,
           or if does not exist return None if built-in, else
           raise SchemaError.
           
           namespace -- namespace item defined in.
           name -- name of item.
           collection -- collection in parent Schema instance to search.
        """
        parent = GetSchema(self)
        if parent.targetNamespace == namespace:
            try:
                obj = getattr(parent, collection)[name]
            except KeyError, ex:
                raise KeyError, 'targetNamespace(%s) collection(%s) has no item(%s)'\
                    %(namespace, collection, name)
                    
            return obj
        
        if not parent.imports.has_key(namespace):
            if namespace in BUILT_IN_NAMESPACES:            
                # built-in just return
                # WARNING: expecting import if "redefine" or add to built-in namespace.
                return
            
            raise SchemaError, 'schema "%s" does not import namespace "%s"' %(
                parent.targetNamespace, namespace)
            
        # Lazy Eval
        schema = parent.imports[namespace]
        if not isinstance(schema, XMLSchema):
            schema = schema.getSchema()    
            if schema is not None:
                parent.imports[namespace] = schema
            
        if schema is None:
            if namespace in BUILT_IN_NAMESPACES:
                # built-in just return
                return
            
            raise SchemaError, 'no schema instance for imported namespace (%s).'\
                %(namespace)
                
        if not isinstance(schema, XMLSchema):
            raise TypeError, 'expecting XMLSchema instance not "%r"' %schema
                
        try:
            obj = getattr(schema, collection)[name]
        except KeyError, ex:
            raise KeyError, 'targetNamespace(%s) collection(%s) has no item(%s)'\
                %(namespace, collection, name)
                    
        return obj

    def getXMLNS(self, prefix=None):
        """deference prefix or by default xmlns, returns namespace. 
        """
        if prefix == XMLSchemaComponent.xml:
            return XMLNS.XML
        parent = self
        ns = self.attributes[XMLSchemaComponent.xmlns].get(prefix or\
                XMLSchemaComponent.xmlns_key)
        while not ns:
            parent = parent._parent()
            ns = parent.attributes[XMLSchemaComponent.xmlns].get(prefix or\
                    XMLSchemaComponent.xmlns_key)
            if not ns and isinstance(parent, WSDLToolsAdapter):
                if prefix is None:
                    return ''
                raise SchemaError, 'unknown prefix %s' %prefix
        return ns

    def getAttribute(self, attribute):
        """return requested attribute value or None
        """
        if type(attribute) in (list, tuple):
            if len(attribute) != 2:
                raise LookupError, 'To access attributes must use name or (namespace,name)'

            ns_dict = self.attributes.get(attribute[0])
            if ns_dict is None:
                return None

            return ns_dict.get(attribute[1])

        return self.attributes.get(attribute)

    def getAttributeQName(self, attribute):
        """return requested attribute value as (namespace,name) or None 
        """
        qname = self.getAttribute(attribute)
        if isinstance(qname, TypeDescriptionComponent) is True:
            return qname
        if qname is None:
            return None

        prefix,ncname = SplitQName(qname)
        namespace = self.getXMLNS(prefix)
        return TypeDescriptionComponent((namespace,ncname))

    def getAttributeName(self):
        """return attribute name or None
        """
        return self.getAttribute('name')
 
    def setAttributes(self, node):
        """Sets up attribute dictionary, checks for required attributes and 
           sets default attribute values. attr is for default attribute values 
           determined at runtime.
           
           structure of attributes dictionary
               ['xmlns'][xmlns_key] --  xmlns namespace
               ['xmlns'][prefix] --  declared namespace prefix 
               [namespace][prefix] -- attributes declared in a namespace
               [attribute] -- attributes w/o prefix, default namespaces do
                   not directly apply to attributes, ie Name can't collide 
                   with QName.
        """
        self.attributes = {XMLSchemaComponent.xmlns:{}}
        for k,v in node.getAttributeDictionary().items():
            prefix,value = SplitQName(k)
            if value == XMLSchemaComponent.xmlns:
                self.attributes[value][prefix or XMLSchemaComponent.xmlns_key] = v
            elif prefix:
                ns = node.getNamespace(prefix)
                if not ns: 
                    raise SchemaError, 'no namespace for attribute prefix %s'\
                        %prefix
                if not self.attributes.has_key(ns):
                    self.attributes[ns] = {}
                elif self.attributes[ns].has_key(value):
                    raise SchemaError, 'attribute %s declared multiple times in %s'\
                        %(value, ns)
                self.attributes[ns][value] = v
            elif not self.attributes.has_key(value):
                self.attributes[value] = v
            else:
                raise SchemaError, 'attribute %s declared multiple times' %value

        if not isinstance(self, WSDLToolsAdapter):
            self.__checkAttributes()
        self.__setAttributeDefaults()

        #set QNames
        for k in ['type', 'element', 'base', 'ref', 'substitutionGroup', 'itemType']:
            if self.attributes.has_key(k):
                prefix, value = SplitQName(self.attributes.get(k))
                self.attributes[k] = \
                    TypeDescriptionComponent((self.getXMLNS(prefix), value))

        #Union, memberTypes is a whitespace separated list of QNames 
        for k in ['memberTypes']:
            if self.attributes.has_key(k):
                qnames = self.attributes[k]
                self.attributes[k] = []
                for qname in qnames.split():
                    prefix, value = SplitQName(qname)
                    self.attributes['memberTypes'].append(\
                        TypeDescriptionComponent(\
                            (self.getXMLNS(prefix), value)))

    def getContents(self, node):
        """retrieve xsd contents
        """
        return node.getContentList(*self.__class__.contents['xsd'])

    def __setAttributeDefaults(self):
        """Looks for default values for unset attributes.  If
           class variable representing attribute is None, then
           it must be defined as an instance variable.
        """
        for k,v in self.__class__.attributes.items():
            if v is not None and self.attributes.has_key(k) is False:
                if isinstance(v, types.FunctionType):
                    self.attributes[k] = v(self)
                else:
                    self.attributes[k] = v

    def __checkAttributes(self):
        """Checks that required attributes have been defined,
           attributes w/default cannot be required.   Checks
           all defined attributes are legal, attribute 
           references are not subject to this test.
        """
        for a in self.__class__.required:
            if not self.attributes.has_key(a):
                raise SchemaError,\
                    'class instance %s, missing required attribute %s'\
                    %(self.__class__, a)
        for a,v in self.attributes.items():
            # attribute #other, ie. not in empty namespace
            if type(v) is dict:
                continue
            
            # predefined prefixes xmlns, xml
            if a in (XMLSchemaComponent.xmlns, XMLNS.XML):
                continue
            
            if (a not in self.__class__.attributes.keys()) and not\
                (self.isAttribute() and self.isReference()):
                raise SchemaError, '%s, unknown attribute(%s,%s)' \
                    %(self.getItemTrace(), a, self.attributes[a])


class WSDLToolsAdapter(XMLSchemaComponent):
    """WSDL Adapter to grab the attributes from the wsdl document node.
    """
    attributes = {'name':None, 'targetNamespace':None}
    tag = 'definitions'

    def __init__(self, wsdl):
        XMLSchemaComponent.__init__(self, parent=wsdl)
        self.setAttributes(DOMAdapter(wsdl.document))

    def getImportSchemas(self):
        """returns WSDLTools.WSDL types Collection
        """
        return self._parent().types


class Notation(XMLSchemaComponent):
    """<notation>
       parent:
           schema
       attributes:
           id -- ID
           name -- NCName, Required
           public -- token, Required
           system -- anyURI
       contents:
           annotation?
    """
    required = ['name', 'public']
    attributes = {'id':None, 'name':None, 'public':None, 'system':None}
    contents = {'xsd':('annotation')}
    tag = 'notation'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class Annotation(XMLSchemaComponent):
    """<annotation>
       parent:
           all,any,anyAttribute,attribute,attributeGroup,choice,complexContent,
           complexType,element,extension,field,group,import,include,key,keyref,
           list,notation,redefine,restriction,schema,selector,simpleContent,
           simpleType,union,unique
       attributes:
           id -- ID
       contents:
           (documentation | appinfo)*
    """
    attributes = {'id':None}
    contents = {'xsd':('documentation', 'appinfo')}
    tag = 'annotation'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        content = []

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'documentation':
                #print_debug('class %s, documentation skipped' %self.__class__, 5)
                continue
            elif component == 'appinfo':
                #print_debug('class %s, appinfo skipped' %self.__class__, 5)
                continue
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
        self.content = tuple(content)


    class Documentation(XMLSchemaComponent):
        """<documentation>
           parent:
               annotation
           attributes:
               source, anyURI
               xml:lang, language
           contents:
               mixed, any
        """
        attributes = {'source':None, 'xml:lang':None}
        contents = {'xsd':('mixed', 'any')}
        tag = 'documentation'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.content = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)
            content = []

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component == 'mixed':
                    #print_debug('class %s, mixed skipped' %self.__class__, 5)
                    continue
                elif component == 'any':
                    #print_debug('class %s, any skipped' %self.__class__, 5)
                    continue
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            self.content = tuple(content)


    class Appinfo(XMLSchemaComponent):
        """<appinfo>
           parent:
               annotation
           attributes:
               source, anyURI
           contents:
               mixed, any
        """
        attributes = {'source':None, 'anyURI':None}
        contents = {'xsd':('mixed', 'any')}
        tag = 'appinfo'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.content = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)
            content = []

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component == 'mixed':
                    #print_debug('class %s, mixed skipped' %self.__class__, 5)
                    continue
                elif component == 'any':
                    #print_debug('class %s, any skipped' %self.__class__, 5)
                    continue
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            self.content = tuple(content)


class XMLSchemaFake:
    # This is temporary, for the benefit of WSDL until the real thing works.
    def __init__(self, element):
        self.targetNamespace = DOM.getAttr(element, 'targetNamespace')
        self.element = element

class XMLSchema(XMLSchemaComponent):
    """A schema is a collection of schema components derived from one
       or more schema documents, that is, one or more <schema> element
       information items. It represents the abstract notion of a schema
       rather than a single schema document (or other representation).

       <schema>
       parent:
           ROOT
       attributes:
           id -- ID
           version -- token
           xml:lang -- language
           targetNamespace -- anyURI
           attributeFormDefault -- 'qualified' | 'unqualified', 'unqualified'
           elementFormDefault -- 'qualified' | 'unqualified', 'unqualified'
           blockDefault -- '#all' | list of 
               ('substitution | 'extension' | 'restriction')
           finalDefault -- '#all' | list of 
               ('extension' | 'restriction' | 'list' | 'union')
        
       contents:
           ((include | import | redefine | annotation)*, 
            (attribute, attributeGroup, complexType, element, group, 
             notation, simpleType)*, annotation*)*


        attributes -- schema attributes
        imports -- import statements
        includes -- include statements
        redefines -- 
        types    -- global simpleType, complexType definitions
        elements -- global element declarations
        attr_decl -- global attribute declarations
        attr_groups -- attribute Groups
        model_groups -- model Groups
        notations -- global notations
    """
    attributes = {'id':None, 
        'version':None, 
        'xml:lang':None, 
        'targetNamespace':None,
        'attributeFormDefault':'unqualified',
        'elementFormDefault':'unqualified',
        'blockDefault':None,
        'finalDefault':None}
    contents = {'xsd':('include', 'import', 'redefine', 'annotation',
                       'attribute', 'attributeGroup', 'complexType',
                       'element', 'group', 'notation', 'simpleType',
                       'annotation')}
    empty_namespace = ''
    tag = 'schema'

    def __init__(self, parent=None): 
        """parent -- 
           instance variables:
           targetNamespace -- schema's declared targetNamespace, or empty string.
           _imported_schemas -- namespace keyed dict of schema dependencies, if 
              a schema is provided instance will not resolve import statement.
           _included_schemas -- schemaLocation keyed dict of component schemas, 
              if schema is provided instance will not resolve include statement.
           _base_url -- needed for relative URLs support, only works with URLs
               relative to initial document.
           includes -- collection of include statements
           imports -- collection of import statements
           elements -- collection of global element declarations
           types -- collection of global type definitions
           attr_decl -- collection of global attribute declarations
           attr_groups -- collection of global attribute group definitions
           model_groups -- collection of model group definitions
           notations -- collection of notations

        """
        self.__node = None
        self.targetNamespace = None
        XMLSchemaComponent.__init__(self, parent)
        f = lambda k: k.attributes['name']
        ns = lambda k: k.attributes['namespace']
        sl = lambda k: k.attributes['schemaLocation']
        self.includes = Collection(self, key=sl)
        self.imports = Collection(self, key=ns)
        self.elements = Collection(self, key=f)
        self.types = Collection(self, key=f)
        self.attr_decl = Collection(self, key=f)
        self.attr_groups = Collection(self, key=f)
        self.model_groups = Collection(self, key=f)
        self.notations = Collection(self, key=f)

        self._imported_schemas = {}
        self._included_schemas = {}
        self._base_url = None

    def getNode(self):
        """
        Interacting with the underlying DOM tree.
        """
        return self.__node
    
    def addImportSchema(self, schema):
        """for resolving import statements in Schema instance
           schema -- schema instance
           _imported_schemas 
        """
        if not isinstance(schema, XMLSchema):
            raise TypeError, 'expecting a Schema instance'
        if schema.targetNamespace != self.targetNamespace:
            self._imported_schemas[schema.targetNamespace] = schema
        else:
            raise SchemaError, 'import schema bad targetNamespace'

    def addIncludeSchema(self, schemaLocation, schema):
        """for resolving include statements in Schema instance
           schemaLocation -- schema location
           schema -- schema instance
           _included_schemas 
        """
        if not isinstance(schema, XMLSchema):
            raise TypeError, 'expecting a Schema instance'
        if not schema.targetNamespace or\
             schema.targetNamespace == self.targetNamespace:
            self._included_schemas[schemaLocation] = schema
        else:
            raise SchemaError, 'include schema bad targetNamespace'
        
    def setImportSchemas(self, schema_dict):
        """set the import schema dictionary, which is used to 
           reference depedent schemas.
        """
        self._imported_schemas = schema_dict

    def getImportSchemas(self):
        """get the import schema dictionary, which is used to 
           reference depedent schemas.
        """
        return self._imported_schemas

    def getSchemaNamespacesToImport(self):
        """returns tuple of namespaces the schema instance has declared
           itself to be depedent upon.
        """
        return tuple(self.includes.keys())

    def setIncludeSchemas(self, schema_dict):
        """set the include schema dictionary, which is keyed with 
           schemaLocation (uri).  
           This is a means of providing 
           schemas to the current schema for content inclusion.
        """
        self._included_schemas = schema_dict

    def getIncludeSchemas(self):
        """get the include schema dictionary, which is keyed with 
           schemaLocation (uri). 
        """
        return self._included_schemas

    def getBaseUrl(self):
        """get base url, used for normalizing all relative uri's 
        """
        return self._base_url

    def setBaseUrl(self, url):
        """set base url, used for normalizing all relative uri's 
        """
        self._base_url = url

    def getElementFormDefault(self):
        """return elementFormDefault attribute
        """
        return self.attributes.get('elementFormDefault')

    def isElementFormDefaultQualified(self):
        return self.attributes.get('elementFormDefault') == 'qualified'

    def getAttributeFormDefault(self):
        """return attributeFormDefault attribute
        """
        return self.attributes.get('attributeFormDefault')

    def getBlockDefault(self):
        """return blockDefault attribute
        """
        return self.attributes.get('blockDefault')

    def getFinalDefault(self):
        """return finalDefault attribute 
        """
        return self.attributes.get('finalDefault')

    def load(self, node, location=None):
        self.__node = node

        pnode = node.getParentNode()
        if pnode:
            pname = SplitQName(pnode.getTagName())[1]
            if pname == 'types':
                attributes = {}
                self.setAttributes(pnode)
                attributes.update(self.attributes)
                self.setAttributes(node)
                for k,v in attributes['xmlns'].items():
                    if not self.attributes['xmlns'].has_key(k):
                        self.attributes['xmlns'][k] = v
            else:
                self.setAttributes(node)
        else:
            self.setAttributes(node)

        self.targetNamespace = self.getTargetNamespace()
        for childNode in self.getContents(node):
            component = SplitQName(childNode.getTagName())[1]
                
            if component == 'include':
                tp = self.__class__.Include(self)
                tp.fromDom(childNode)

                sl = tp.attributes['schemaLocation']
                schema = tp.getSchema()

                if not self.getIncludeSchemas().has_key(sl):
                    self.addIncludeSchema(sl, schema)

                self.includes[sl] = tp

                pn = childNode.getParentNode().getNode()
                pn.removeChild(childNode.getNode())
                for child in schema.getNode().getNode().childNodes:
                    pn.appendChild(child.cloneNode(1))

                for collection in ['imports','elements','types',
                                   'attr_decl','attr_groups','model_groups',
                                   'notations']:
                    for k,v in getattr(schema,collection).items():
                        if not getattr(self,collection).has_key(k):
                            v._parent = weakref.ref(self)
                            getattr(self,collection)[k] = v
                        else:
                            warnings.warn("Not keeping schema component.")
      
            elif component == 'import':
                slocd = SchemaReader.namespaceToSchema
                tp = self.__class__.Import(self)
                tp.fromDom(childNode)
                import_ns = tp.getAttribute('namespace') or\
                    self.__class__.empty_namespace
                schema = slocd.get(import_ns)
                if schema is None:
                    schema = XMLSchema()
                    slocd[import_ns] = schema
                    try:
                        tp.loadSchema(schema)
                    except NoSchemaLocationWarning, ex:
                        # Dependency declaration, hopefully implementation
                        # is aware of this namespace (eg. SOAP,WSDL,?)
                        print "IMPORT: ", import_ns
                        print ex
                        del slocd[import_ns]
                        continue
                    except SchemaError, ex:
                        #warnings.warn(\
                        #    '<import namespace="%s" schemaLocation=?>, %s'\
                        #    %(import_ns, 'failed to load schema instance')
                        #)
                        print ex
                        del slocd[import_ns]
                        class _LazyEvalImport(str):
                            '''Lazy evaluation of import, replace entry in self.imports.'''
                            #attributes = dict(namespace=import_ns)
                            def getSchema(namespace):
                                schema = slocd.get(namespace)
                                if schema is None:
                                    parent = self._parent()
                                    wstypes = parent
                                    if isinstance(parent, WSDLToolsAdapter):
                                        wstypes = parent.getImportSchemas()
                                    schema = wstypes.get(namespace)
                                if isinstance(schema, XMLSchema):
                                    self.imports[namespace] = schema
                                    return schema

                                return None

                        self.imports[import_ns] = _LazyEvalImport(import_ns)
                        continue
                else:           
                    tp._schema = schema
            
                if self.getImportSchemas().has_key(import_ns):
                    warnings.warn(\
                        'Detected multiple imports of the namespace "%s" '\
                        %import_ns)
            
                self.addImportSchema(schema)
                # spec says can have multiple imports of same namespace
                # but purpose of import is just dependency declaration.
                self.imports[import_ns] = tp
                
            elif component == 'redefine':
                warnings.warn('redefine is ignored')
            elif component == 'annotation':
                warnings.warn('annotation is ignored')
            elif component == 'attribute':
                tp = AttributeDeclaration(self)
                tp.fromDom(childNode)
                self.attr_decl[tp.getAttribute('name')] = tp
            elif component == 'attributeGroup':
                tp = AttributeGroupDefinition(self)
                tp.fromDom(childNode)
                self.attr_groups[tp.getAttribute('name')] = tp
            elif component == 'element':
                tp = ElementDeclaration(self)
                tp.fromDom(childNode)
                self.elements[tp.getAttribute('name')] = tp
            elif component == 'group':
                tp = ModelGroupDefinition(self)
                tp.fromDom(childNode)
                self.model_groups[tp.getAttribute('name')] = tp
            elif component == 'notation':
                tp = Notation(self)
                tp.fromDom(childNode)
                self.notations[tp.getAttribute('name')] = tp
            elif component == 'complexType':
                tp = ComplexType(self)
                tp.fromDom(childNode)
                self.types[tp.getAttribute('name')] = tp
            elif component == 'simpleType':
                tp = SimpleType(self)
                tp.fromDom(childNode)
                self.types[tp.getAttribute('name')] = tp
            else:
                break

    class Import(XMLSchemaComponent):
        """<import> 
           parent:
               schema
           attributes:
               id -- ID
               namespace -- anyURI
               schemaLocation -- anyURI
           contents:
               annotation?
        """
        attributes = {'id':None,
                      'namespace':None,
                      'schemaLocation':None}
        contents = {'xsd':['annotation']}
        tag = 'import'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            self._schema = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)

            if self.attributes['namespace'] == self.getTargetNamespace():
                raise SchemaError, 'namespace of schema and import match'

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())

        def getSchema(self):
            """if schema is not defined, first look for a Schema class instance
               in parent Schema.  Else if not defined resolve schemaLocation
               and create a new Schema class instance, and keep a hard reference. 
            """
            if not self._schema:
                ns = self.attributes['namespace']
                schema = self._parent().getImportSchemas().get(ns)
                if not schema and self._parent()._parent:
                    schema = self._parent()._parent().getImportSchemas().get(ns)

                if not schema:
                    url = self.attributes.get('schemaLocation')
                    if not url:
                        raise SchemaError, 'namespace(%s) is unknown' %ns
                    base_url = self._parent().getBaseUrl()
                    reader = SchemaReader(base_url=base_url)
                    reader._imports = self._parent().getImportSchemas()
                    reader._includes = self._parent().getIncludeSchemas()
                    self._schema = reader.loadFromURL(url)
            return self._schema or schema
            
        def loadSchema(self, schema):
            """
            """
            base_url = self._parent().getBaseUrl()
            reader = SchemaReader(base_url=base_url)
            reader._imports = self._parent().getImportSchemas()
            reader._includes = self._parent().getIncludeSchemas()
            self._schema = schema

            if not self.attributes.has_key('schemaLocation'):
                raise NoSchemaLocationWarning('no schemaLocation attribute in import')

            reader.loadFromURL(self.attributes.get('schemaLocation'), schema)


    class Include(XMLSchemaComponent):
        """<include schemaLocation>
           parent:
               schema
           attributes:
               id -- ID
               schemaLocation -- anyURI, required
           contents:
               annotation?
        """
        required = ['schemaLocation']
        attributes = {'id':None,
            'schemaLocation':None}
        contents = {'xsd':['annotation']}
        tag = 'include'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            self._schema = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())

        def getSchema(self):
            """if schema is not defined, first look for a Schema class instance
               in parent Schema.  Else if not defined resolve schemaLocation
               and create a new Schema class instance.  
            """
            if not self._schema:
                schema = self._parent()
                self._schema = schema.getIncludeSchemas().get(\
                                   self.attributes['schemaLocation']
                                   )
                if not self._schema:
                    url = self.attributes['schemaLocation']
                    reader = SchemaReader(base_url=schema.getBaseUrl())
                    reader._imports = schema.getImportSchemas()
                    reader._includes = schema.getIncludeSchemas()
                    
                    # create schema before loading so chameleon include 
                    # will evalute targetNamespace correctly.
                    self._schema = XMLSchema(schema)
                    reader.loadFromURL(url, self._schema)

            return self._schema


class AttributeDeclaration(XMLSchemaComponent,\
                           AttributeMarker,\
                           DeclarationMarker):
    """<attribute name>
       parent: 
           schema
       attributes:
           id -- ID
           name -- NCName, required
           type -- QName
           default -- string
           fixed -- string
       contents:
           annotation?, simpleType?
    """
    required = ['name']
    attributes = {'id':None,
        'name':None,
        'type':None,
        'default':None,
        'fixed':None}
    contents = {'xsd':['annotation','simpleType']}
    tag = 'attribute'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        """ No list or union support
        """
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            elif component == 'simpleType':
                self.content = AnonymousSimpleType(self)
                self.content.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class LocalAttributeDeclaration(AttributeDeclaration,\
                                AttributeMarker,\
                                LocalMarker,\
                                DeclarationMarker):
    """<attribute name>
       parent: 
           complexType, restriction, extension, attributeGroup
       attributes:
           id -- ID
           name -- NCName,  required
           type -- QName
           form -- ('qualified' | 'unqualified'), schema.attributeFormDefault
           use -- ('optional' | 'prohibited' | 'required'), optional
           default -- string
           fixed -- string
       contents:
           annotation?, simpleType?
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None,
        'type':None,
        'form':lambda self: GetSchema(self).getAttributeFormDefault(),
        'use':'optional',
        'default':None,
        'fixed':None}
    contents = {'xsd':['annotation','simpleType']}

    def __init__(self, parent):
        AttributeDeclaration.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            elif component == 'simpleType':
                self.content = AnonymousSimpleType(self)
                self.content.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class AttributeWildCard(XMLSchemaComponent,\
                        AttributeMarker,\
                        DeclarationMarker,\
                        WildCardMarker):
    """<anyAttribute>
       parents: 
           complexType, restriction, extension, attributeGroup
       attributes:
           id -- ID
           namespace -- '##any' | '##other' | 
                        (anyURI* | '##targetNamespace' | '##local'), ##any
           processContents -- 'lax' | 'skip' | 'strict', strict
       contents:
           annotation?
    """
    attributes = {'id':None, 
        'namespace':'##any',
        'processContents':'strict'}
    contents = {'xsd':['annotation']}
    tag = 'anyAttribute'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class AttributeReference(XMLSchemaComponent,\
                         AttributeMarker,\
                         ReferenceMarker):
    """<attribute ref>
       parents: 
           complexType, restriction, extension, attributeGroup
       attributes:
           id -- ID
           ref -- QName, required
           use -- ('optional' | 'prohibited' | 'required'), optional
           default -- string
           fixed -- string
       contents:
           annotation?
    """
    required = ['ref']
    attributes = {'id':None, 
        'ref':None,
        'use':'optional',
        'default':None,
        'fixed':None}
    contents = {'xsd':['annotation']}
    tag = 'attribute'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def getAttributeDeclaration(self, attribute='ref'):
        return XMLSchemaComponent.getAttributeDeclaration(self, attribute)

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class AttributeGroupDefinition(XMLSchemaComponent,\
                               AttributeGroupMarker,\
                               DefinitionMarker):
    """<attributeGroup name>
       parents: 
           schema, redefine
       attributes:
           id -- ID
           name -- NCName,  required
       contents:
           annotation?, (attribute | attributeGroup)*, anyAttribute?
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None}
    contents = {'xsd':['annotation', 'attribute', 'attributeGroup', 'anyAttribute']}
    tag = 'attributeGroup'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.attr_content = None

    def getAttributeContent(self):
        return self.attr_content

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        content = []

        for indx in range(len(contents)):
            component = SplitQName(contents[indx].getTagName())[1]
            if (component == 'annotation') and (not indx):
                self.annotation = Annotation(self)
                self.annotation.fromDom(contents[indx])
            elif component == 'attribute':
                if contents[indx].hasattr('name'):
                    content.append(LocalAttributeDeclaration(self))
                elif contents[indx].hasattr('ref'):
                    content.append(AttributeReference(self))
                else:
                    raise SchemaError, 'Unknown attribute type'
                content[-1].fromDom(contents[indx])
            elif component == 'attributeGroup':
                content.append(AttributeGroupReference(self))
                content[-1].fromDom(contents[indx])
            elif component == 'anyAttribute':
                if len(contents) != indx+1: 
                    raise SchemaError, 'anyAttribute is out of order in %s' %self.getItemTrace()
                content.append(AttributeWildCard(self))
                content[-1].fromDom(contents[indx])
            else:
                raise SchemaError, 'Unknown component (%s)' %(contents[indx].getTagName())

        self.attr_content = tuple(content)

class AttributeGroupReference(XMLSchemaComponent,\
                              AttributeGroupMarker,\
                              ReferenceMarker):
    """<attributeGroup ref>
       parents: 
           complexType, restriction, extension, attributeGroup
       attributes:
           id -- ID
           ref -- QName, required
       contents:
           annotation?
    """
    required = ['ref']
    attributes = {'id':None, 
        'ref':None}
    contents = {'xsd':['annotation']}
    tag = 'attributeGroup'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def getAttributeGroup(self, attribute='ref'):
        """attribute -- attribute with a QName value (eg. type).
           collection -- check types collection in parent Schema instance
        """
        return XMLSchemaComponent.getAttributeGroup(self, attribute)

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component == 'annotation' and not self.annotation:
                self.annotation = Annotation(self)
                self.annotation.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())



######################################################
# Elements
#####################################################
class IdentityConstrants(XMLSchemaComponent):
    """Allow one to uniquely identify nodes in a document and ensure the 
       integrity of references between them.

       attributes -- dictionary of attributes
       selector -- XPath to selected nodes
       fields -- list of XPath to key field
    """
    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.selector = None
        self.fields = None
        self.annotation = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        fields = []

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                elif component == 'selector':
                    self.selector = self.Selector(self)
                    self.selector.fromDom(i)
                    continue
                elif component == 'field':
                    fields.append(self.Field(self))
                    fields[-1].fromDom(i)
                    continue
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            self.fields = tuple(fields)


    class Constraint(XMLSchemaComponent):
        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component in self.__class__.contents['xsd']:
                    if component == 'annotation' and not self.annotation:
                        self.annotation = Annotation(self)
                        self.annotation.fromDom(i)
                    else:
                        raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())

    class Selector(Constraint):
        """<selector xpath>
           parent: 
               unique, key, keyref
           attributes:
               id -- ID
               xpath -- XPath subset,  required
           contents:
               annotation?
        """
        required = ['xpath']
        attributes = {'id':None, 
            'xpath':None}
        contents = {'xsd':['annotation']}
        tag = 'selector'

    class Field(Constraint): 
        """<field xpath>
           parent: 
               unique, key, keyref
           attributes:
               id -- ID
               xpath -- XPath subset,  required
           contents:
               annotation?
        """
        required = ['xpath']
        attributes = {'id':None, 
            'xpath':None}
        contents = {'xsd':['annotation']}
        tag = 'field'


class Unique(IdentityConstrants):
    """<unique name> Enforce fields are unique w/i a specified scope.

       parent: 
           element
       attributes:
           id -- ID
           name -- NCName,  required
       contents:
           annotation?, selector, field+
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None}
    contents = {'xsd':['annotation', 'selector', 'field']}
    tag = 'unique'


class Key(IdentityConstrants):
    """<key name> Enforce fields are unique w/i a specified scope, and all
           field values are present w/i document.  Fields cannot
           be nillable.

       parent: 
           element
       attributes:
           id -- ID
           name -- NCName,  required
       contents:
           annotation?, selector, field+
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None}
    contents = {'xsd':['annotation', 'selector', 'field']}
    tag = 'key'


class KeyRef(IdentityConstrants):
    """<keyref name refer> Ensure a match between two sets of values in an 
           instance.
       parent: 
           element
       attributes:
           id -- ID
           name -- NCName,  required
           refer -- QName,  required
       contents:
           annotation?, selector, field+
    """
    required = ['name', 'refer']
    attributes = {'id':None, 
        'name':None,
        'refer':None}
    contents = {'xsd':['annotation', 'selector', 'field']}
    tag = 'keyref'


class ElementDeclaration(XMLSchemaComponent,\
                         ElementMarker,\
                         DeclarationMarker):
    """<element name>
       parents:
           schema
       attributes:
           id -- ID
           name -- NCName,  required
           type -- QName
           default -- string
           fixed -- string
           nillable -- boolean,  false
           abstract -- boolean,  false
           substitutionGroup -- QName
           block -- ('#all' | ('substition' | 'extension' | 'restriction')*), 
               schema.blockDefault 
           final -- ('#all' | ('extension' | 'restriction')*), 
               schema.finalDefault 
       contents:
           annotation?, (simpleType,complexType)?, (key | keyref | unique)*
           
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None,
        'type':None,
        'default':None,
        'fixed':None,
        'nillable':0,
        'abstract':0,
        'substitutionGroup':None,
        'block':lambda self: self._parent().getBlockDefault(),
        'final':lambda self: self._parent().getFinalDefault()}
    contents = {'xsd':['annotation', 'simpleType', 'complexType', 'key',\
        'keyref', 'unique']}
    tag = 'element'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None
        self.constraints = ()

    def isQualified(self):
        """Global elements are always qualified.
        """
        return True
    
    def getAttribute(self, attribute):
        """return attribute.
        If attribute is type and it's None, and no simple or complex content, 
        return the default type "xsd:anyType"
        """
        value = XMLSchemaComponent.getAttribute(self, attribute)
        if attribute != 'type' or value is not None:
            return value
        
        if self.content is not None:
            return None
        
        parent = self
        while 1:
            nsdict = parent.attributes[XMLSchemaComponent.xmlns]
            for k,v in nsdict.items():
                if v not in SCHEMA.XSD_LIST: continue
                return TypeDescriptionComponent((v, 'anyType'))
            
            if isinstance(parent, WSDLToolsAdapter)\
                or not hasattr(parent, '_parent'):
                break
            
            parent = parent._parent()
            
        raise SchemaError, 'failed to locate the XSD namespace'
    
    def getElementDeclaration(self, attribute):
        raise Warning, 'invalid operation for <%s>' %self.tag

    def getTypeDefinition(self, attribute=None):
        """If attribute is None, "type" is assumed, return the corresponding
        representation of the global type definition (TypeDefinition),
        or the local definition if don't find "type".  To maintain backwards
        compat, if attribute is provided call base class method.
        """
        if attribute:
            return XMLSchemaComponent.getTypeDefinition(self, attribute)
        gt = XMLSchemaComponent.getTypeDefinition(self, 'type')
        if gt:
            return gt
        return self.content

    def getConstraints(self):
        return self._constraints
    def setConstraints(self, constraints):
        self._constraints = tuple(constraints)
    constraints = property(getConstraints, setConstraints, None, "tuple of key, keyref, unique constraints")

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        constraints = []
        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                elif component == 'simpleType' and not self.content:
                    self.content = AnonymousSimpleType(self)
                    self.content.fromDom(i)
                elif component == 'complexType' and not self.content:
                    self.content = LocalComplexType(self)
                    self.content.fromDom(i)
                elif component == 'key':
                    constraints.append(Key(self))
                    constraints[-1].fromDom(i)
                elif component == 'keyref':
                    constraints.append(KeyRef(self))
                    constraints[-1].fromDom(i)
                elif component == 'unique':
                    constraints.append(Unique(self))
                    constraints[-1].fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())

        self.constraints = constraints


class LocalElementDeclaration(ElementDeclaration,\
                              LocalMarker):
    """<element>
       parents:
           all, choice, sequence
       attributes:
           id -- ID
           name -- NCName,  required
           form -- ('qualified' | 'unqualified'), schema.elementFormDefault
           type -- QName
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1
           default -- string
           fixed -- string
           nillable -- boolean,  false
           block -- ('#all' | ('extension' | 'restriction')*), schema.blockDefault 
       contents:
           annotation?, (simpleType,complexType)?, (key | keyref | unique)*
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None,
        'form':lambda self: GetSchema(self).getElementFormDefault(),
        'type':None,
        'minOccurs':'1',
        'maxOccurs':'1',
        'default':None,
        'fixed':None,
        'nillable':0,
        'abstract':0,
        'block':lambda self: GetSchema(self).getBlockDefault()}
    contents = {'xsd':['annotation', 'simpleType', 'complexType', 'key',\
        'keyref', 'unique']}

    def isQualified(self):
        """
Local elements can be qualified or unqualifed according
        to the attribute form, or the elementFormDefault.  By default
        local elements are unqualified.
        """
        form = self.getAttribute('form')
        if form == 'qualified':
            return True
        if form == 'unqualified':
            return False
        raise SchemaError, 'Bad form (%s) for element: %s' %(form, self.getItemTrace())


class ElementReference(XMLSchemaComponent,\
                       ElementMarker,\
                       ReferenceMarker):
    """<element ref>
       parents: 
           all, choice, sequence
       attributes:
           id -- ID
           ref -- QName, required
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1
       contents:
           annotation?
    """
    required = ['ref']
    attributes = {'id':None, 
        'ref':None,
        'minOccurs':'1',
        'maxOccurs':'1'}
    contents = {'xsd':['annotation']}
    tag = 'element'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def getElementDeclaration(self, attribute=None):
        """If attribute is None, "ref" is assumed, return the corresponding
        representation of the global element declaration (ElementDeclaration),
        To maintain backwards compat, if attribute is provided call base class method.
        """
        if attribute:
            return XMLSchemaComponent.getElementDeclaration(self, attribute)
        return XMLSchemaComponent.getElementDeclaration(self, 'ref')
 
    def fromDom(self, node):
        self.annotation = None
        self.setAttributes(node)
        for i in self.getContents(node):
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class ElementWildCard(LocalElementDeclaration, WildCardMarker):
    """<any>
       parents: 
           choice, sequence
       attributes:
           id -- ID
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1
           namespace -- '##any' | '##other' | 
                        (anyURI* | '##targetNamespace' | '##local'), ##any
           processContents -- 'lax' | 'skip' | 'strict', strict
       contents:
           annotation?
    """
    required = []
    attributes = {'id':None, 
        'minOccurs':'1',
        'maxOccurs':'1',
        'namespace':'##any',
        'processContents':'strict'}
    contents = {'xsd':['annotation']}
    tag = 'any'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def isQualified(self):
        """
        Global elements are always qualified, but if processContents
        are not strict could have dynamically generated local elements.
        """
        return GetSchema(self).isElementFormDefaultQualified()

    def getAttribute(self, attribute):
        """return attribute.
        """
        return XMLSchemaComponent.getAttribute(self, attribute)

    def getTypeDefinition(self, attribute):
        raise Warning, 'invalid operation for <%s>' % self.tag

    def fromDom(self, node):
        self.annotation = None
        self.setAttributes(node)
        for i in self.getContents(node):
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


######################################################
# Model Groups
#####################################################
class Sequence(XMLSchemaComponent,\
               SequenceMarker):
    """<sequence>
       parents: 
           complexType, extension, restriction, group, choice, sequence
       attributes:
           id -- ID
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1

       contents:
           annotation?, (element | group | choice | sequence | any)*
    """
    attributes = {'id':None, 
        'minOccurs':'1',
        'maxOccurs':'1'}
    contents = {'xsd':['annotation', 'element', 'group', 'choice', 'sequence',\
         'any']}
    tag = 'sequence'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        content = []

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                    continue
                elif component == 'element':
                    if i.hasattr('ref'):
                        content.append(ElementReference(self))
                    else:
                        content.append(LocalElementDeclaration(self))
                elif component == 'group':
                    content.append(ModelGroupReference(self))
                elif component == 'choice':
                    content.append(Choice(self))
                elif component == 'sequence':
                    content.append(Sequence(self))
                elif component == 'any':
                    content.append(ElementWildCard(self))
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                content[-1].fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
        self.content = tuple(content)


class All(XMLSchemaComponent,\
          AllMarker):
    """<all>
       parents: 
           complexType, extension, restriction, group
       attributes:
           id -- ID
           minOccurs -- '0' | '1', 1
           maxOccurs -- '1', 1

       contents:
           annotation?, element*
    """
    attributes = {'id':None, 
        'minOccurs':'1',
        'maxOccurs':'1'}
    contents = {'xsd':['annotation', 'element']}
    tag = 'all'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        content = []

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                    continue
                elif component == 'element':
                    if i.hasattr('ref'):
                        content.append(ElementReference(self))
                    else:
                        content.append(LocalElementDeclaration(self))
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                content[-1].fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
        self.content = tuple(content)


class Choice(XMLSchemaComponent,\
             ChoiceMarker):
    """<choice>
       parents: 
           complexType, extension, restriction, group, choice, sequence
       attributes:
           id -- ID
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1

       contents:
           annotation?, (element | group | choice | sequence | any)*
    """
    attributes = {'id':None, 
        'minOccurs':'1',
        'maxOccurs':'1'}
    contents = {'xsd':['annotation', 'element', 'group', 'choice', 'sequence',\
         'any']}
    tag = 'choice'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        content = []

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                    continue
                elif component == 'element':
                    if i.hasattr('ref'):
                        content.append(ElementReference(self))
                    else:
                        content.append(LocalElementDeclaration(self))
                elif component == 'group':
                    content.append(ModelGroupReference(self))
                elif component == 'choice':
                    content.append(Choice(self))
                elif component == 'sequence':
                    content.append(Sequence(self))
                elif component == 'any':
                    content.append(ElementWildCard(self))
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                content[-1].fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
        self.content = tuple(content)


class ModelGroupDefinition(XMLSchemaComponent,\
                           ModelGroupMarker,\
                           DefinitionMarker):
    """<group name>
       parents:
           redefine, schema
       attributes:
           id -- ID
           name -- NCName,  required

       contents:
           annotation?, (all | choice | sequence)?
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None}
    contents = {'xsd':['annotation', 'all', 'choice', 'sequence']}
    tag = 'group'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                    continue
                elif component == 'all' and not self.content:
                    self.content = All(self)
                elif component == 'choice' and not self.content:
                    self.content = Choice(self)
                elif component == 'sequence' and not self.content:
                    self.content = Sequence(self)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                self.content.fromDom(i)
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())


class ModelGroupReference(XMLSchemaComponent,\
                          ModelGroupMarker,\
                          ReferenceMarker):
    """<group ref>
       parents:
           choice, complexType, extension, restriction, sequence
       attributes:
           id -- ID
           ref -- NCName,  required
           minOccurs -- Whole Number, 1
           maxOccurs -- (Whole Number | 'unbounded'), 1

       contents:
           annotation?
    """
    required = ['ref']
    attributes = {'id':None, 
        'ref':None,
        'minOccurs':'1',
        'maxOccurs':'1'}
    contents = {'xsd':['annotation']}
    tag = 'group'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None

    def getModelGroupReference(self):
        return self.getModelGroup('ref')

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)

        for i in contents:
            component = SplitQName(i.getTagName())[1]
            if component in self.__class__.contents['xsd']:
                if component == 'annotation' and not self.annotation:
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(i)
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            else:
                raise SchemaError, 'Unknown component (%s)' %(i.getTagName())



class ComplexType(XMLSchemaComponent,\
                  DefinitionMarker,\
                  ComplexMarker):
    """<complexType name>
       parents:
           redefine, schema
       attributes:
           id -- ID
           name -- NCName,  required
           mixed -- boolean, false
           abstract -- boolean,  false
           block -- ('#all' | ('extension' | 'restriction')*), schema.blockDefault 
           final -- ('#all' | ('extension' | 'restriction')*), schema.finalDefault 

       contents:
           annotation?, (simpleContent | complexContent | 
           ((group | all | choice | sequence)?, (attribute | attributeGroup)*, anyAttribute?))
    """
    required = ['name']
    attributes = {'id':None, 
        'name':None,
        'mixed':0,
        'abstract':0,
        'block':lambda self: self._parent().getBlockDefault(),
        'final':lambda self: self._parent().getFinalDefault()}
    contents = {'xsd':['annotation', 'simpleContent', 'complexContent',\
        'group', 'all', 'choice', 'sequence', 'attribute', 'attributeGroup',\
        'anyAttribute', 'any']}
    tag = 'complexType'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None
        self.attr_content = None

    def isMixed(self):
        m = self.getAttribute('mixed')
        if m == 0 or m == False:
            return False
        if isinstance(m, basestring) is True:
            if m in ('false', '0'):
                return False
            if m in ('true', '1'):
                return True

        raise SchemaError, 'invalid value for attribute mixed(%s): %s'\
            %(m, self.getItemTrace())

    def getAttributeContent(self):
        return self.attr_content

    def getElementDeclaration(self, attribute):
        raise Warning, 'invalid operation for <%s>' %self.tag

    def getTypeDefinition(self, attribute):
        raise Warning, 'invalid operation for <%s>' %self.tag

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
      
        indx = 0
        num = len(contents)
        if not num:
            return

        component = SplitQName(contents[indx].getTagName())[1]
        if component == 'annotation':
            self.annotation = Annotation(self)
            self.annotation.fromDom(contents[indx])
            indx += 1
            if indx < num:
                component = SplitQName(contents[indx].getTagName())[1]

        self.content = None
        if component == 'simpleContent':
            self.content = self.__class__.SimpleContent(self)
            self.content.fromDom(contents[indx])
        elif component == 'complexContent':
            self.content = self.__class__.ComplexContent(self)
            self.content.fromDom(contents[indx])
        else:
            if component == 'all':
                self.content = All(self)
            elif component == 'choice':
                self.content = Choice(self)
            elif component == 'sequence':
                self.content = Sequence(self)
            elif component == 'group':
                self.content = ModelGroupReference(self)

            if self.content:
                self.content.fromDom(contents[indx])
                indx += 1

            self.attr_content = []
            while indx < num:
                component = SplitQName(contents[indx].getTagName())[1]
                if component == 'attribute':
                    if contents[indx].hasattr('ref'):
                        self.attr_content.append(AttributeReference(self))
                    else:
                        self.attr_content.append(LocalAttributeDeclaration(self))
                elif component == 'attributeGroup':
                    self.attr_content.append(AttributeGroupReference(self))
                elif component == 'anyAttribute':
                    self.attr_content.append(AttributeWildCard(self))
                else:
                    raise SchemaError, 'Unknown component (%s): %s' \
                        %(contents[indx].getTagName(),self.getItemTrace())
                self.attr_content[-1].fromDom(contents[indx])
                indx += 1

    class _DerivedType(XMLSchemaComponent):
        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            # XXX remove attribute derivation, inconsistent
            self.derivation = None
            self.content = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)

            for i in contents:
                component = SplitQName(i.getTagName())[1]
                if component in self.__class__.contents['xsd']:
                    if component == 'annotation' and not self.annotation:
                        self.annotation = Annotation(self)
                        self.annotation.fromDom(i)
                        continue
                    elif component == 'restriction' and not self.derivation:
                        self.derivation = self.__class__.Restriction(self)
                    elif component == 'extension' and not self.derivation:
                        self.derivation = self.__class__.Extension(self)
                    else:
                        raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
                self.derivation.fromDom(i)
            self.content = self.derivation

    class ComplexContent(_DerivedType,\
                         ComplexMarker):
        """<complexContent>
           parents:
               complexType
           attributes:
               id -- ID
               mixed -- boolean, false

           contents:
               annotation?, (restriction | extension)
        """
        attributes = {'id':None, 
            'mixed':0}
        contents = {'xsd':['annotation', 'restriction', 'extension']}
        tag = 'complexContent'

        def isMixed(self):
            m = self.getAttribute('mixed')
            if m == 0 or m == False:
                return False
            if isinstance(m, basestring) is True:
                if m in ('false', '0'):
                    return False
                if m in ('true', '1'):
                    return True
            raise SchemaError, 'invalid value for attribute mixed(%s): %s'\
                %(m, self.getItemTrace())

        class _DerivationBase(XMLSchemaComponent):
            """<extension>,<restriction>
               parents:
                   complexContent
               attributes:
                   id -- ID
                   base -- QName, required

               contents:
                   annotation?, (group | all | choice | sequence)?, 
                       (attribute | attributeGroup)*, anyAttribute?
            """
            required = ['base']
            attributes = {'id':None, 
                'base':None }
            contents = {'xsd':['annotation', 'group', 'all', 'choice',\
                'sequence', 'attribute', 'attributeGroup', 'anyAttribute']}

            def __init__(self, parent):
                XMLSchemaComponent.__init__(self, parent)
                self.annotation = None
                self.content = None
                self.attr_content = None

            def getAttributeContent(self):
                return self.attr_content

            def fromDom(self, node):
                self.setAttributes(node)
                contents = self.getContents(node)

                indx = 0
                num = len(contents)
                #XXX ugly
                if not num:
                    return
                component = SplitQName(contents[indx].getTagName())[1]
                if component == 'annotation':
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(contents[indx])
                    indx += 1
                    component = SplitQName(contents[indx].getTagName())[1]

                if component == 'all':
                    self.content = All(self)
                    self.content.fromDom(contents[indx])
                    indx += 1
                elif component == 'choice':
                    self.content = Choice(self)
                    self.content.fromDom(contents[indx])
                    indx += 1
                elif component == 'sequence':
                    self.content = Sequence(self)
                    self.content.fromDom(contents[indx])
                    indx += 1
                elif component == 'group':
                    self.content = ModelGroupReference(self)
                    self.content.fromDom(contents[indx])
                    indx += 1
                else:
                    self.content = None

                self.attr_content = []
                while indx < num:
                    component = SplitQName(contents[indx].getTagName())[1]
                    if component == 'attribute':
                        if contents[indx].hasattr('ref'):
                            self.attr_content.append(AttributeReference(self))
                        else:
                            self.attr_content.append(LocalAttributeDeclaration(self))
                    elif component == 'attributeGroup':
                        if contents[indx].hasattr('ref'):
                            self.attr_content.append(AttributeGroupReference(self))
                        else:
                            self.attr_content.append(AttributeGroupDefinition(self))
                    elif component == 'anyAttribute':
                        self.attr_content.append(AttributeWildCard(self))
                    else:
                        raise SchemaError, 'Unknown component (%s)' %(contents[indx].getTagName())
                    self.attr_content[-1].fromDom(contents[indx])
                    indx += 1

        class Extension(_DerivationBase, 
                        ExtensionMarker):
            """<extension base>
               parents:
                   complexContent
               attributes:
                   id -- ID
                   base -- QName, required

               contents:
                   annotation?, (group | all | choice | sequence)?, 
                       (attribute | attributeGroup)*, anyAttribute?
            """
            tag = 'extension'

        class Restriction(_DerivationBase,\
                          RestrictionMarker):
            """<restriction base>
               parents:
                   complexContent
               attributes:
                   id -- ID
                   base -- QName, required

               contents:
                   annotation?, (group | all | choice | sequence)?, 
                       (attribute | attributeGroup)*, anyAttribute?
            """
            tag = 'restriction'


    class SimpleContent(_DerivedType,\
                        SimpleMarker):
        """<simpleContent>
           parents:
               complexType
           attributes:
               id -- ID

           contents:
               annotation?, (restriction | extension)
        """
        attributes = {'id':None}
        contents = {'xsd':['annotation', 'restriction', 'extension']}
        tag = 'simpleContent'

        class Extension(XMLSchemaComponent,\
                        ExtensionMarker):
            """<extension base>
               parents:
                   simpleContent
               attributes:
                   id -- ID
                   base -- QName, required

               contents:
                   annotation?, (attribute | attributeGroup)*, anyAttribute?
            """
            required = ['base']
            attributes = {'id':None, 
                'base':None }
            contents = {'xsd':['annotation', 'attribute', 'attributeGroup', 
                'anyAttribute']}
            tag = 'extension'

            def __init__(self, parent):
                XMLSchemaComponent.__init__(self, parent)
                self.annotation = None
                self.attr_content = None
 
            def getAttributeContent(self):
                return self.attr_content

            def fromDom(self, node):
                self.setAttributes(node)
                contents = self.getContents(node)

                indx = 0
                num = len(contents)

                if num:
                    component = SplitQName(contents[indx].getTagName())[1]
                    if component == 'annotation':
                        self.annotation = Annotation(self)
                        self.annotation.fromDom(contents[indx])
                        indx += 1
                        component = SplitQName(contents[indx].getTagName())[1]
    
                content = []
                while indx < num:
                    component = SplitQName(contents[indx].getTagName())[1]
                    if component == 'attribute':
                        if contents[indx].hasattr('ref'):
                            content.append(AttributeReference(self))
                        else:
                            content.append(LocalAttributeDeclaration(self))
                    elif component == 'attributeGroup':
                        content.append(AttributeGroupReference(self))
                    elif component == 'anyAttribute':
                        content.append(AttributeWildCard(self))
                    else:
                        raise SchemaError, 'Unknown component (%s)'\
                            %(contents[indx].getTagName())
                    content[-1].fromDom(contents[indx])
                    indx += 1
                self.attr_content = tuple(content)


        class Restriction(XMLSchemaComponent,\
                          RestrictionMarker):
            """<restriction base>
               parents:
                   simpleContent
               attributes:
                   id -- ID
                   base -- QName, required

               contents:
                   annotation?, simpleType?, (enumeration | length | 
                   maxExclusive | maxInclusive | maxLength | minExclusive | 
                   minInclusive | minLength | pattern | fractionDigits | 
                   totalDigits | whiteSpace)*, (attribute | attributeGroup)*, 
                   anyAttribute?
            """
            required = ['base']
            attributes = {'id':None, 
                'base':None }
            contents = {'xsd':['annotation', 'simpleType', 'attribute',\
                'attributeGroup', 'anyAttribute'] + RestrictionMarker.facets}
            tag = 'restriction'

            def __init__(self, parent):
                XMLSchemaComponent.__init__(self, parent)
                self.annotation = None
                self.content = None
                self.attr_content = None
 
            def getAttributeContent(self):
                return self.attr_content

            def fromDom(self, node):
                self.content = []
                self.setAttributes(node)
                contents = self.getContents(node)

                indx = 0
                num = len(contents)
                component = SplitQName(contents[indx].getTagName())[1]
                if component == 'annotation':
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(contents[indx])
                    indx += 1
                    component = SplitQName(contents[indx].getTagName())[1]

                content = []
                while indx < num:
                    component = SplitQName(contents[indx].getTagName())[1]
                    if component == 'attribute':
                        if contents[indx].hasattr('ref'):
                            content.append(AttributeReference(self))
                        else:
                            content.append(LocalAttributeDeclaration(self))
                    elif component == 'attributeGroup':
                        content.append(AttributeGroupReference(self))
                    elif component == 'anyAttribute':
                        content.append(AttributeWildCard(self))
                    elif component == 'simpleType':
                        self.content.append(AnonymousSimpleType(self))
                        self.content[-1].fromDom(contents[indx])
                    else:
                        raise SchemaError, 'Unknown component (%s)'\
                            %(contents[indx].getTagName())
                    content[-1].fromDom(contents[indx])
                    indx += 1
                self.attr_content = tuple(content)


class LocalComplexType(ComplexType,\
                       LocalMarker):
    """<complexType>
       parents:
           element
       attributes:
           id -- ID
           mixed -- boolean, false

       contents:
           annotation?, (simpleContent | complexContent | 
           ((group | all | choice | sequence)?, (attribute | attributeGroup)*, anyAttribute?))
    """
    required = []
    attributes = {'id':None, 
        'mixed':0}
    tag = 'complexType'
    

class SimpleType(XMLSchemaComponent,\
                 DefinitionMarker,\
                 SimpleMarker):
    """<simpleType name>
       parents:
           redefine, schema
       attributes:
           id -- ID
           name -- NCName, required
           final -- ('#all' | ('extension' | 'restriction' | 'list' | 'union')*), 
               schema.finalDefault 

       contents:
           annotation?, (restriction | list | union)
    """
    required = ['name']
    attributes = {'id':None,
        'name':None,
        'final':lambda self: self._parent().getFinalDefault()}
    contents = {'xsd':['annotation', 'restriction', 'list', 'union']}
    tag = 'simpleType'

    def __init__(self, parent):
        XMLSchemaComponent.__init__(self, parent)
        self.annotation = None
        self.content = None

    def getElementDeclaration(self, attribute):
        raise Warning, 'invalid operation for <%s>' %self.tag

    def getTypeDefinition(self, attribute):
        raise Warning, 'invalid operation for <%s>' %self.tag

    def fromDom(self, node):
        self.setAttributes(node)
        contents = self.getContents(node)
        for child in contents:
            component = SplitQName(child.getTagName())[1]
            if component == 'annotation':
                self.annotation = Annotation(self)
                self.annotation.fromDom(child)
                continue
            break
        else:
            return
        if component == 'restriction':
            self.content = self.__class__.Restriction(self)
        elif component == 'list':
            self.content = self.__class__.List(self)
        elif component == 'union':
            self.content = self.__class__.Union(self)
        else:
            raise SchemaError, 'Unknown component (%s)' %(component)
        self.content.fromDom(child)

    class Restriction(XMLSchemaComponent,\
                      RestrictionMarker):
        """<restriction base>
           parents:
               simpleType
           attributes:
               id -- ID
               base -- QName, required or simpleType child

           contents:
               annotation?, simpleType?, (enumeration | length | 
               maxExclusive | maxInclusive | maxLength | minExclusive | 
               minInclusive | minLength | pattern | fractionDigits | 
               totalDigits | whiteSpace)*
        """
        attributes = {'id':None, 
            'base':None }
        contents = {'xsd':['annotation', 'simpleType']+RestrictionMarker.facets}
        tag = 'restriction'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            self.content = None
            self.facets = None

        def getAttributeBase(self):
            return XMLSchemaComponent.getAttribute(self, 'base')

        def getTypeDefinition(self, attribute='base'):
            return XMLSchemaComponent.getTypeDefinition(self, attribute)

        def getSimpleTypeContent(self):
            for el in self.content:
                if el.isSimple(): return el
            return None

        def fromDom(self, node):
            self.facets = []
            self.setAttributes(node)
            contents = self.getContents(node)
            content = []

            for indx in range(len(contents)):
                component = SplitQName(contents[indx].getTagName())[1]
                if (component == 'annotation') and (not indx):
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(contents[indx])
                    continue
                elif (component == 'simpleType') and (not indx or indx == 1):
                    content.append(AnonymousSimpleType(self))
                    content[-1].fromDom(contents[indx])
                elif component in RestrictionMarker.facets:
                    self.facets.append(contents[indx])
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            self.content = tuple(content)


    class Union(XMLSchemaComponent,
                UnionMarker):
        """<union>
           parents:
               simpleType
           attributes:
               id -- ID
               memberTypes -- list of QNames, required or simpleType child.

           contents:
               annotation?, simpleType*
        """
        attributes = {'id':None, 
            'memberTypes':None }
        contents = {'xsd':['annotation', 'simpleType']}
        tag = 'union'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            self.content = None

        def fromDom(self, node):
            self.setAttributes(node)
            contents = self.getContents(node)
            content = []

            for indx in range(len(contents)):
                component = SplitQName(contents[indx].getTagName())[1]
                if (component == 'annotation') and (not indx):
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(contents[indx])
                elif (component == 'simpleType'):
                    content.append(AnonymousSimpleType(self))
                    content[-1].fromDom(contents[indx])
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())
            self.content = tuple(content)

    class List(XMLSchemaComponent, 
               ListMarker):
        """<list>
           parents:
               simpleType
           attributes:
               id -- ID
               itemType -- QName, required or simpleType child.

           contents:
               annotation?, simpleType?
        """
        attributes = {'id':None, 
            'itemType':None }
        contents = {'xsd':['annotation', 'simpleType']}
        tag = 'list'

        def __init__(self, parent):
            XMLSchemaComponent.__init__(self, parent)
            self.annotation = None
            self.content = None

        def getItemType(self):
            return self.attributes.get('itemType')

        def getTypeDefinition(self, attribute='itemType'):
            """
            return the type refered to by itemType attribute or
            the simpleType content.  If returns None, then the 
            type refered to by itemType is primitive.
            """
            tp = XMLSchemaComponent.getTypeDefinition(self, attribute)
            return tp or self.content

        def fromDom(self, node):
            self.annotation = None
            self.content = None
            self.setAttributes(node)
            contents = self.getContents(node)
            for indx in range(len(contents)):
                component = SplitQName(contents[indx].getTagName())[1]
                if (component == 'annotation') and (not indx):
                    self.annotation = Annotation(self)
                    self.annotation.fromDom(contents[indx])
                elif (component == 'simpleType'):
                    self.content = AnonymousSimpleType(self)
                    self.content.fromDom(contents[indx])
                    break
                else:
                    raise SchemaError, 'Unknown component (%s)' %(i.getTagName())

                 
class AnonymousSimpleType(SimpleType,\
                          SimpleMarker,\
                          LocalMarker):
    """<simpleType>
       parents:
           attribute, element, list, restriction, union
       attributes:
           id -- ID

       contents:
           annotation?, (restriction | list | union)
    """
    required = []
    attributes = {'id':None}
    tag = 'simpleType'


class Redefine:
    """<redefine>
       parents:
       attributes:

       contents:
    """
    tag = 'redefine'


###########################
###########################


if sys.version_info[:2] >= (2, 2):
    tupleClass = tuple
else:
    import UserTuple
    tupleClass = UserTuple.UserTuple

class TypeDescriptionComponent(tupleClass):
    """Tuple of length 2, consisting of
       a namespace and unprefixed name.
    """
    def __init__(self, args):
        """args -- (namespace, name)
           Remove the name's prefix, irrelevant.
        """
        if len(args) != 2:
            raise TypeError, 'expecting tuple (namespace, name), got %s' %args
        elif args[1].find(':') >= 0:
            args = (args[0], SplitQName(args[1])[1])
        tuple.__init__(self, args)
        return

    def getTargetNamespace(self):
        return self[0]

    def getName(self):
        return self[1]



########NEW FILE########
