__FILENAME__ = blockfinder
blockfinder
########NEW FILE########
__FILENAME__ = blockfindertest
#!/usr/bin/python
import unittest
import os
import shutil
import sys
import tempfile

import blockfinder
from blockfinder import ipaddr


class BaseBlockfinderTest(unittest.TestCase):
    def setUp(self):
        self.base_test_dir = tempfile.mkdtemp()
        self.test_dir = self.base_test_dir + "/test/"
        self.database_cache = blockfinder.DatabaseCache(self.test_dir)
        self.downloader_parser = blockfinder.DownloaderParser(
                self.test_dir, self.database_cache, "Mozilla")
        self.lookup = blockfinder.Lookup(self.test_dir, self.database_cache)
        self.database_cache.connect_to_database()
        self.database_cache.set_db_version()
        shutil.copy('test_rir_data', self.test_dir + 'test_rir_data')
        shutil.copy('test_lir_data.gz', self.test_dir + 'test_lir_data.gz')
        self.downloader_parser.parse_rir_files(['test_rir_data'])
        self.downloader_parser.parse_lir_files(['test_lir_data.gz'])

    def tearDown(self):
        shutil.rmtree(self.base_test_dir, True)


class CheckReverseLookup(BaseBlockfinderTest):
    def test_rir_ipv4_lookup(self):
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'rir', int(ipaddr.IPv4Address('175.45.176.100'))), 'KP')
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'rir', int(ipaddr.IPv4Address('193.9.26.0'))), 'HU')
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'rir', int(ipaddr.IPv4Address('193.9.25.1'))), 'PL')
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'rir', int(ipaddr.IPv4Address('193.9.25.255'))), 'PL')

    def test_rir_asn_lookup(self):
        self.assertEqual(self.database_cache.fetch_country_code('asn',
                'rir', 681), 'NZ')
        self.assertEqual(self.database_cache.fetch_country_code('asn',
                'rir', 173), 'JP')

    def test_lir_ipv4_lookup(self):
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'lir', int(ipaddr.IPv4Address('80.16.151.184'))), 'IT')
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'lir', int(ipaddr.IPv4Address('80.16.151.180'))), 'IT')
        self.assertEqual(self.database_cache.fetch_country_code('ipv4',
                'lir', int(ipaddr.IPv4Address('213.95.6.32'))), 'DE')

    def test_lir_ipv6_lookup(self):
        self.assertEqual(self.database_cache.fetch_country_code('ipv6',
                'lir', int(ipaddr.IPv6Address('2001:0658:021A::'))), 'DE')
        self.assertEqual(self.database_cache.fetch_country_code('ipv6',
                'lir', int(ipaddr.IPv6Address('2001:67c:320::'))), 'DE')
        self.assertEqual(self.database_cache.fetch_country_code('ipv6',
                'lir', int(ipaddr.IPv6Address('2001:670:0085::'))), 'FI')


class CheckBlockFinder(BaseBlockfinderTest):
    def test_ipv4_bf(self):
        known_ipv4_assignments = (
                ('MM', ['203.81.64.0/19', '203.81.160.0/20']),
                ('KP', ['175.45.176.0/22']))
        for cc, values in known_ipv4_assignments:
            expected = [(int(ipaddr.IPv4Network(network_str).network_address),
                    int(ipaddr.IPv4Network(network_str).broadcast_address))
                    for network_str in values]
            result = self.database_cache.fetch_assignments('ipv4', cc)
            self.assertEqual(result, expected)

    def test_ipv6_bf(self):
        known_ipv6_assignments = ['2001:200::/35', '2001:200:2000::/35',
                                  '2001:200:4000::/34', '2001:200:8000::/33']
        expected = [(int(ipaddr.IPv6Network(network_str).network_address),
                int(ipaddr.IPv6Network(network_str).broadcast_address))
                for network_str in known_ipv6_assignments]
        result = self.database_cache.fetch_assignments('ipv6', 'JP')
        self.assertEqual(result, expected)


if __name__ == '__main__':
    failures = 0
    for test_class in [CheckReverseLookup, CheckBlockFinder]:
        test_suite = unittest.makeSuite(test_class)
        test_runner = unittest.TextTestRunner(verbosity=2)
        results = test_runner.run(test_suite)
        failures += len(results.errors)
        failures += len(results.failures)
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = ipaddr
#!/usr/bin/python
#
# Copyright 2007 Google Inc.
#  Licensed to PSF under a Contributor Agreement.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

"""A fast, lightweight IPv4/IPv6 manipulation library in Python.

This library is used to create/poke/manipulate IPv4 and IPv6 addresses
and networks.

"""

__version__ = 'trunk'

import struct

IPV4LENGTH = 32
IPV6LENGTH = 128


class AddressValueError(ValueError):
    """A Value Error related to the address."""


class NetmaskValueError(ValueError):
    """A Value Error related to the netmask."""


def IPAddress(address, version=None):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.
        version: An Integer, 4 or 6. If set, don't try to automatically
          determine what the IP address type is. important for things
          like IPAddress(1), which could be IPv4, '0.0.0.1',  or IPv6,
          '::1'.

    Returns:
        An IPv4Address or IPv6Address object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address.

    """
    if version:
        if version == 4:
            return IPv4Address(address)
        elif version == 6:
            return IPv6Address(address)

    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 address' %
                     address)


def IPNetwork(address, version=None, strict=False):
    """Take an IP string/int and return an object of the correct type.

    Args:
        address: A string or integer, the IP address.  Either IPv4 or
          IPv6 addresses may be supplied; integers less than 2**32 will
          be considered to be IPv4 by default.
        version: An Integer, if set, don't try to automatically
          determine what the IP address type is. important for things
          like IPNetwork(1), which could be IPv4, '0.0.0.1/32', or IPv6,
          '::1/128'.

    Returns:
        An IPv4Network or IPv6Network object.

    Raises:
        ValueError: if the string passed isn't either a v4 or a v6
          address. Or if a strict network was requested and a strict
          network wasn't given.

    """
    if version:
        if version == 4:
            return IPv4Network(address, strict)
        elif version == 6:
            return IPv6Network(address, strict)

    try:
        return IPv4Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    try:
        return IPv6Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass

    raise ValueError('%r does not appear to be an IPv4 or IPv6 network' %
                     address)


def v4_int_to_packed(address):
    """The binary representation of this address.

    Args:
        address: An integer representation of an IPv4 IP address.

    Returns:
        The binary representation of this address.

    Raises:
        ValueError: If the integer is too large to be an IPv4 IP
          address.
    """
    if address > _BaseV4._ALL_ONES:
        raise ValueError('Address too large for IPv4')
    return Bytes(struct.pack('!I', address))


def v6_int_to_packed(address):
    """The binary representation of this address.

    Args:
        address: An integer representation of an IPv6 IP address.

    Returns:
        The binary representation of this address.
    """
    return Bytes(struct.pack('!QQ', address >> 64, address & (2**64 - 1)))


def _find_address_range(addresses):
    """Find a sequence of addresses.

    Args:
        addresses: a list of IPv4 or IPv6 addresses.

    Returns:
        A tuple containing the first and last IP addresses in the sequence.

    """
    first = last = addresses[0]
    for ip in addresses[1:]:
        if ip._ip == last._ip + 1:
            last = ip
        else:
            break
    return (first, last)

def _get_prefix_length(number1, number2, bits):
    """Get the number of leading bits that are same for two numbers.

    Args:
        number1: an integer.
        number2: another integer.
        bits: the maximum number of bits to compare.

    Returns:
        The number of leading bits that are the same for two numbers.

    """
    for i in range(bits):
        if number1 >> i == number2 >> i:
            return bits - i
    return 0

def _count_righthand_zero_bits(number, bits):
    """Count the number of zero bits on the right hand side.

    Args:
        number: an integer.
        bits: maximum number of bits to count.

    Returns:
        The number of zero bits on the right hand side of the number.

    """
    if number == 0:
        return bits
    for i in range(bits):
        if (number >> i) % 2:
            return i

def summarize_address_range(first, last):
    """Summarize a network range given the first and last IP addresses.

    Example:
        >>> summarize_address_range(IPv4Address('1.1.1.0'),
            IPv4Address('1.1.1.130'))
        [IPv4Network('1.1.1.0/25'), IPv4Network('1.1.1.128/31'),
        IPv4Network('1.1.1.130/32')]

    Args:
        first: the first IPv4Address or IPv6Address in the range.
        last: the last IPv4Address or IPv6Address in the range.

    Returns:
        The address range collapsed to a list of IPv4Network's or
        IPv6Network's.

    Raise:
        TypeError:
            If the first and last objects are not IP addresses.
            If the first and last objects are not the same version.
        ValueError:
            If the last object is not greater than the first.
            If the version is not 4 or 6.

    """
    if not (isinstance(first, _BaseIP) and isinstance(last, _BaseIP)):
        raise TypeError('first and last must be IP addresses, not networks')
    if first.version != last.version:
        raise TypeError("%s and %s are not of the same version" % (
                str(first), str(last)))
    if first > last:
        raise ValueError('last IP address must be greater than first')

    networks = []

    if first.version == 4:
        ip = IPv4Network
    elif first.version == 6:
        ip = IPv6Network
    else:
        raise ValueError('unknown IP version')

    ip_bits = first._max_prefixlen
    first_int = first._ip
    last_int = last._ip
    while first_int <= last_int:
        nbits = _count_righthand_zero_bits(first_int, ip_bits)
        current = None
        while nbits >= 0:
            addend = 2**nbits - 1
            current = first_int + addend
            nbits -= 1
            if current <= last_int:
                break
        prefix = _get_prefix_length(first_int, current, ip_bits)
        net = ip('%s/%d' % (str(first), prefix))
        networks.append(net)
        if current == ip._ALL_ONES:
            break
        first_int = current + 1
        first = IPAddress(first_int, version=first._version)
    return networks

def _collapse_address_list_recursive(addresses):
    """Loops through the addresses, collapsing concurrent netblocks.

    Example:

        ip1 = IPv4Network('1.1.0.0/24')
        ip2 = IPv4Network('1.1.1.0/24')
        ip3 = IPv4Network('1.1.2.0/24')
        ip4 = IPv4Network('1.1.3.0/24')
        ip5 = IPv4Network('1.1.4.0/24')
        ip6 = IPv4Network('1.1.0.1/22')

        _collapse_address_list_recursive([ip1, ip2, ip3, ip4, ip5, ip6]) ->
          [IPv4Network('1.1.0.0/22'), IPv4Network('1.1.4.0/24')]

        This shouldn't be called directly; it is called via
          collapse_address_list([]).

    Args:
        addresses: A list of IPv4Network's or IPv6Network's

    Returns:
        A list of IPv4Network's or IPv6Network's depending on what we were
        passed.

    """
    ret_array = []
    optimized = False

    for cur_addr in addresses:
        if not ret_array:
            ret_array.append(cur_addr)
            continue
        if cur_addr in ret_array[-1]:
            optimized = True
        elif cur_addr == ret_array[-1].supernet().subnet()[1]:
            ret_array.append(ret_array.pop().supernet())
            optimized = True
        else:
            ret_array.append(cur_addr)

    if optimized:
        return _collapse_address_list_recursive(ret_array)

    return ret_array


def collapse_address_list(addresses):
    """Collapse a list of IP objects.

    Example:
        collapse_address_list([IPv4('1.1.0.0/24'), IPv4('1.1.1.0/24')]) ->
          [IPv4('1.1.0.0/23')]

    Args:
        addresses: A list of IPv4Network or IPv6Network objects.

    Returns:
        A list of IPv4Network or IPv6Network objects depending on what we
        were passed.

    Raises:
        TypeError: If passed a list of mixed version objects.

    """
    i = 0
    addrs = []
    ips = []
    nets = []

    # split IP addresses and networks
    for ip in addresses:
        if isinstance(ip, _BaseIP):
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(ips[-1])))
            ips.append(ip)
        elif ip._prefixlen == ip._max_prefixlen:
            if ips and ips[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(ips[-1])))
            ips.append(ip.ip)
        else:
            if nets and nets[-1]._version != ip._version:
                raise TypeError("%s and %s are not of the same version" % (
                        str(ip), str(nets[-1])))
            nets.append(ip)

    # sort and dedup
    ips = sorted(set(ips))
    nets = sorted(set(nets))

    while i < len(ips):
        (first, last) = _find_address_range(ips[i:])
        i = ips.index(last) + 1
        addrs.extend(summarize_address_range(first, last))

    return _collapse_address_list_recursive(sorted(
        addrs + nets, key=_BaseNet._get_networks_key))

# backwards compatibility
CollapseAddrList = collapse_address_list

# We need to distinguish between the string and packed-bytes representations
# of an IP address.  For example, b'0::1' is the IPv4 address 48.58.58.49,
# while '0::1' is an IPv6 address.
#
# In Python 3, the native 'bytes' type already provides this functionality,
# so we use it directly.  For earlier implementations where bytes is not a
# distinct type, we create a subclass of str to serve as a tag.
#
# Usage example (Python 2):
#   ip = ipaddr.IPAddress(ipaddr.Bytes('xxxx'))
#
# Usage example (Python 3):
#   ip = ipaddr.IPAddress(b'xxxx')
try:
    if bytes is str:
        raise TypeError("bytes is not a distinct type")
    Bytes = bytes
except (NameError, TypeError):
    class Bytes(str):
        def __repr__(self):
            return 'Bytes(%s)' % str.__repr__(self)

def get_mixed_type_key(obj):
    """Return a key suitable for sorting between networks and addresses.

    Address and Network objects are not sortable by default; they're
    fundamentally different so the expression

        IPv4Address('1.1.1.1') <= IPv4Network('1.1.1.1/24')

    doesn't make any sense.  There are some times however, where you may wish
    to have ipaddr sort these for you anyway. If you need to do this, you
    can use this function as the key= argument to sorted().

    Args:
      obj: either a Network or Address object.
    Returns:
      appropriate key.

    """
    if isinstance(obj, _BaseNet):
        return obj._get_networks_key()
    elif isinstance(obj, _BaseIP):
        return obj._get_address_key()
    return NotImplemented

class _IPAddrBase(object):

    """The mother class."""

    def __index__(self):
        return self._ip

    def __int__(self):
        return self._ip

    def __hex__(self):
        return hex(self._ip)

    @property
    def exploded(self):
        """Return the longhand version of the IP address as a string."""
        return self._explode_shorthand_ip_string()

    @property
    def compressed(self):
        """Return the shorthand version of the IP address as a string."""
        return str(self)


class _BaseIP(_IPAddrBase):

    """A generic IP object.

    This IP class contains the version independent methods which are
    used by single IP addresses.

    """

    def __eq__(self, other):
        try:
            return (self._ip == other._ip
                    and self._version == other._version)
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __le__(self, other):
        gt = self.__gt__(other)
        if gt is NotImplemented:
            return NotImplemented
        return not gt

    def __ge__(self, other):
        lt = self.__lt__(other)
        if lt is NotImplemented:
            return NotImplemented
        return not lt

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseIP):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self._ip != other._ip:
            return self._ip < other._ip
        return False

    def __gt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseIP):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self._ip != other._ip:
            return self._ip > other._ip
        return False

    # Shorthand for Integer addition and subtraction. This is not
    # meant to ever support addition/subtraction of addresses.
    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return IPAddress(int(self) + other, version=self._version)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return IPAddress(int(self) - other, version=self._version)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return  '%s' % self._string_from_ip_int(self._ip)

    def __hash__(self):
        return hash(hex(long(self._ip)))

    def _get_address_key(self):
        return (self._version, self)

    @property
    def version(self):
        raise NotImplementedError('BaseIP has no version')


class _BaseNet(_IPAddrBase):

    """A generic IP object.

    This IP class contains the version independent methods which are
    used by networks.

    """

    def __init__(self, address):
        self._cache = {}

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def iterhosts(self):
        """Generate Iterator over usable hosts in a network.

           This is like __iter__ except it doesn't return the network
           or broadcast addresses.

        """
        cur = int(self.network) + 1
        bcast = int(self.broadcast) - 1
        while cur <= bcast:
            cur += 1
            yield IPAddress(cur - 1, version=self._version)

    def __iter__(self):
        cur = int(self.network)
        bcast = int(self.broadcast)
        while cur <= bcast:
            cur += 1
            yield IPAddress(cur - 1, version=self._version)

    def __getitem__(self, n):
        network = int(self.network)
        broadcast = int(self.broadcast)
        if n >= 0:
            if network + n > broadcast:
                raise IndexError
            return IPAddress(network + n, version=self._version)
        else:
            n += 1
            if broadcast + n < network:
                raise IndexError
            return IPAddress(broadcast + n, version=self._version)

    def __lt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseNet):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self.network != other.network:
            return self.network < other.network
        if self.netmask != other.netmask:
            return self.netmask < other.netmask
        return False

    def __gt__(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (
                    str(self), str(other)))
        if not isinstance(other, _BaseNet):
            raise TypeError('%s and %s are not of the same type' % (
                    str(self), str(other)))
        if self.network != other.network:
            return self.network > other.network
        if self.netmask != other.netmask:
            return self.netmask > other.netmask
        return False

    def __le__(self, other):
        gt = self.__gt__(other)
        if gt is NotImplemented:
            return NotImplemented
        return not gt

    def __ge__(self, other):
        lt = self.__lt__(other)
        if lt is NotImplemented:
            return NotImplemented
        return not lt

    def __eq__(self, other):
        try:
            return (self._version == other._version
                    and self.network == other.network
                    and int(self.netmask) == int(other.netmask))
        except AttributeError:
            if isinstance(other, _BaseIP):
                return (self._version == other._version
                        and self._ip == other._ip)

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __str__(self):
        return  '%s/%s' % (str(self.ip),
                           str(self._prefixlen))

    def __hash__(self):
        return hash(int(self.network) ^ int(self.netmask))

    def __contains__(self, other):
        # always false if one is v4 and the other is v6.
        if self._version != other._version:
          return False
        # dealing with another network.
        if isinstance(other, _BaseNet):
            return (self.network <= other.network and
                    self.broadcast >= other.broadcast)
        # dealing with another address
        else:
            return (int(self.network) <= int(other._ip) <=
                    int(self.broadcast))

    def overlaps(self, other):
        """Tell if self is partly contained in other."""
        return self.network in other or self.broadcast in other or (
            other.network in self or other.broadcast in self)

    @property
    def network(self):
        x = self._cache.get('network')
        if x is None:
            x = IPAddress(self._ip & int(self.netmask), version=self._version)
            self._cache['network'] = x
        return x

    @property
    def network_address(self):
        return self.network

    @property
    def broadcast(self):
        x = self._cache.get('broadcast')
        if x is None:
            x = IPAddress(self._ip | int(self.hostmask), version=self._version)
            self._cache['broadcast'] = x
        return x

    @property
    def broadcast_address(self):
        return self.broadcast

    @property
    def hostmask(self):
        x = self._cache.get('hostmask')
        if x is None:
            x = IPAddress(int(self.netmask) ^ self._ALL_ONES,
                          version=self._version)
            self._cache['hostmask'] = x
        return x

    @property
    def with_prefixlen(self):
        return '%s/%d' % (str(self.ip), self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (str(self.ip), str(self.netmask))

    @property
    def with_hostmask(self):
        return '%s/%s' % (str(self.ip), str(self.hostmask))

    @property
    def numhosts(self):
        """Number of hosts in the current subnet."""
        return int(self.broadcast) - int(self.network) + 1

    @property
    def version(self):
        raise NotImplementedError('BaseNet has no version')

    @property
    def prefixlen(self):
        return self._prefixlen

    def address_exclude(self, other):
        """Remove an address from a larger block.

        For example:

            addr1 = IPNetwork('10.1.1.0/24')
            addr2 = IPNetwork('10.1.1.0/26')
            addr1.address_exclude(addr2) =
                [IPNetwork('10.1.1.64/26'), IPNetwork('10.1.1.128/25')]

        or IPv6:

            addr1 = IPNetwork('::1/32')
            addr2 = IPNetwork('::1/128')
            addr1.address_exclude(addr2) = [IPNetwork('::0/128'),
                IPNetwork('::2/127'),
                IPNetwork('::4/126'),
                IPNetwork('::8/125'),
                ...
                IPNetwork('0:0:8000::/33')]

        Args:
            other: An IPvXNetwork object of the same type.

        Returns:
            A sorted list of IPvXNetwork objects addresses which is self
            minus other.

        Raises:
            TypeError: If self and other are of difffering address
              versions, or if other is not a network object.
            ValueError: If other is not completely contained by self.

        """
        if not self._version == other._version:
            raise TypeError("%s and %s are not of the same version" % (
                str(self), str(other)))

        if not isinstance(other, _BaseNet):
            raise TypeError("%s is not a network object" % str(other))

        if other not in self:
            raise ValueError('%s not contained in %s' % (str(other),
                                                         str(self)))
        if other == self:
            return []

        ret_addrs = []

        # Make sure we're comparing the network of other.
        other = IPNetwork('%s/%s' % (str(other.network), str(other.prefixlen)),
                   version=other._version)

        s1, s2 = self.subnet()
        while s1 != other and s2 != other:
            if other in s1:
                ret_addrs.append(s2)
                s1, s2 = s1.subnet()
            elif other in s2:
                ret_addrs.append(s1)
                s1, s2 = s2.subnet()
            else:
                # If we got here, there's a bug somewhere.
                assert True == False, ('Error performing exclusion: '
                                       's1: %s s2: %s other: %s' %
                                       (str(s1), str(s2), str(other)))
        if s1 == other:
            ret_addrs.append(s2)
        elif s2 == other:
            ret_addrs.append(s1)
        else:
            # If we got here, there's a bug somewhere.
            assert True == False, ('Error performing exclusion: '
                                   's1: %s s2: %s other: %s' %
                                   (str(s1), str(s2), str(other)))

        return sorted(ret_addrs, key=_BaseNet._get_networks_key)

    def compare_networks(self, other):
        """Compare two IP objects.

        This is only concerned about the comparison of the integer
        representation of the network addresses.  This means that the
        host bits aren't considered at all in this method.  If you want
        to compare host bits, you can easily enough do a
        'HostA._ip < HostB._ip'

        Args:
            other: An IP object.

        Returns:
            If the IP versions of self and other are the same, returns:

            -1 if self < other:
              eg: IPv4('1.1.1.0/24') < IPv4('1.1.2.0/24')
              IPv6('1080::200C:417A') < IPv6('1080::200B:417B')
            0 if self == other
              eg: IPv4('1.1.1.1/24') == IPv4('1.1.1.2/24')
              IPv6('1080::200C:417A/96') == IPv6('1080::200C:417B/96')
            1 if self > other
              eg: IPv4('1.1.1.0/24') > IPv4('1.1.0.0/24')
              IPv6('1080::1:200C:417A/112') >
              IPv6('1080::0:200C:417A/112')

            If the IP versions of self and other are different, returns:

            -1 if self._version < other._version
              eg: IPv4('10.0.0.1/24') < IPv6('::1/128')
            1 if self._version > other._version
              eg: IPv6('::1/128') > IPv4('255.255.255.0/24')

        """
        if self._version < other._version:
            return -1
        if self._version > other._version:
            return 1
        # self._version == other._version below here:
        if self.network < other.network:
            return -1
        if self.network > other.network:
            return 1
        # self.network == other.network below here:
        if self.netmask < other.netmask:
            return -1
        if self.netmask > other.netmask:
            return 1
        # self.network == other.network and self.netmask == other.netmask
        return 0

    def _get_networks_key(self):
        """Network-only key function.

        Returns an object that identifies this address' network and
        netmask. This function is a suitable "key" argument for sorted()
        and list.sort().

        """
        return (self._version, self.network, self.netmask)

    def _ip_int_from_prefix(self, prefixlen=None):
        """Turn the prefix length netmask into a int for comparison.

        Args:
            prefixlen: An integer, the prefix length.

        Returns:
            An integer.

        """
        if not prefixlen and prefixlen != 0:
            prefixlen = self._prefixlen
        return self._ALL_ONES ^ (self._ALL_ONES >> prefixlen)

    def _prefix_from_ip_int(self, ip_int, mask=32):
        """Return prefix length from the decimal netmask.

        Args:
            ip_int: An integer, the IP address.
            mask: The netmask.  Defaults to 32.

        Returns:
            An integer, the prefix length.

        """
        while mask:
            if ip_int & 1 == 1:
                break
            ip_int >>= 1
            mask -= 1

        return mask

    def _ip_string_from_prefix(self, prefixlen=None):
        """Turn a prefix length into a dotted decimal string.

        Args:
            prefixlen: An integer, the netmask prefix length.

        Returns:
            A string, the dotted decimal netmask string.

        """
        if not prefixlen:
            prefixlen = self._prefixlen
        return self._string_from_ip_int(self._ip_int_from_prefix(prefixlen))

    def iter_subnets(self, prefixlen_diff=1, new_prefix=None):
        """The subnets which join to make the current subnet.

        In the case that self contains only one IP
        (self._prefixlen == 32 for IPv4 or self._prefixlen == 128
        for IPv6), return a list with just ourself.

        Args:
            prefixlen_diff: An integer, the amount the prefix length
              should be increased by. This should not be set if
              new_prefix is also set.
            new_prefix: The desired new prefix length. This must be a
              larger number (smaller prefix) than the existing prefix.
              This should not be set if prefixlen_diff is also set.

        Returns:
            An iterator of IPv(4|6) objects.

        Raises:
            ValueError: The prefixlen_diff is too small or too large.
                OR
            prefixlen_diff and new_prefix are both set or new_prefix
              is a smaller number than the current prefix (smaller
              number means a larger network)

        """
        if self._prefixlen == self._max_prefixlen:
            yield self
            return

        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError('new prefix must be longer')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = new_prefix - self._prefixlen

        if prefixlen_diff < 0:
            raise ValueError('prefix length diff must be > 0')
        new_prefixlen = self._prefixlen + prefixlen_diff

        if not self._is_valid_netmask(str(new_prefixlen)):
            raise ValueError(
                'prefix length diff %d is invalid for netblock %s' % (
                    new_prefixlen, str(self)))

        first = IPNetwork('%s/%s' % (str(self.network),
                                     str(self._prefixlen + prefixlen_diff)),
                         version=self._version)

        yield first
        current = first
        while True:
            broadcast = current.broadcast
            if broadcast == self.broadcast:
                return
            new_addr = IPAddress(int(broadcast) + 1, version=self._version)
            current = IPNetwork('%s/%s' % (str(new_addr), str(new_prefixlen)),
                                version=self._version)

            yield current

    def masked(self):
        """Return the network object with the host bits masked out."""
        return IPNetwork('%s/%d' % (self.network, self._prefixlen),
                         version=self._version)

    def subnet(self, prefixlen_diff=1, new_prefix=None):
        """Return a list of subnets, rather than an iterator."""
        return list(self.iter_subnets(prefixlen_diff, new_prefix))

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        """The supernet containing the current network.

        Args:
            prefixlen_diff: An integer, the amount the prefix length of
              the network should be decreased by.  For example, given a
              /24 network and a prefixlen_diff of 3, a supernet with a
              /21 netmask is returned.

        Returns:
            An IPv4 network object.

        Raises:
            ValueError: If self.prefixlen - prefixlen_diff < 0. I.e., you have a
              negative prefix length.
                OR
            If prefixlen_diff and new_prefix are both set or new_prefix is a
              larger number than the current prefix (larger number means a
              smaller network)

        """
        if self._prefixlen == 0:
            return self

        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError('new prefix must be shorter')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = self._prefixlen - new_prefix


        if self.prefixlen - prefixlen_diff < 0:
            raise ValueError(
                'current prefixlen is %d, cannot have a prefixlen_diff of %d' %
                (self.prefixlen, prefixlen_diff))
        return IPNetwork('%s/%s' % (str(self.network),
                                    str(self.prefixlen - prefixlen_diff)),
                         version=self._version)

    # backwards compatibility
    Subnet = subnet
    Supernet = supernet
    AddressExclude = address_exclude
    CompareNetworks = compare_networks
    Contains = __contains__


class _BaseV4(object):

    """Base IPv4 object.

    The following methods are used by IPv4 objects in both single IP
    addresses and networks.

    """

    # Equivalent to 255.255.255.255 or 32 bits of 1's.
    _ALL_ONES = (2**IPV4LENGTH) - 1
    _DECIMAL_DIGITS = frozenset('0123456789')

    def __init__(self, address):
        self._version = 4
        self._max_prefixlen = IPV4LENGTH

    def _explode_shorthand_ip_string(self):
        return str(self)

    def _ip_int_from_string(self, ip_str):
        """Turn the given IP string into an integer for comparison.

        Args:
            ip_str: A string, the IP ip_str.

        Returns:
            The IP ip_str as an integer.

        Raises:
            AddressValueError: if ip_str isn't a valid IPv4 Address.

        """
        octets = ip_str.split('.')
        if len(octets) != 4:
            raise AddressValueError(ip_str)

        packed_ip = 0
        for oc in octets:
            try:
                packed_ip = (packed_ip << 8) | self._parse_octet(oc)
            except ValueError:
                raise AddressValueError(ip_str)
        return packed_ip

    def _parse_octet(self, octet_str):
        """Convert a decimal octet into an integer.

        Args:
            octet_str: A string, the number to parse.

        Returns:
            The octet as an integer.

        Raises:
            ValueError: if the octet isn't strictly a decimal from [0..255].

        """
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._DECIMAL_DIGITS.issuperset(octet_str):
            raise ValueError
        octet_int = int(octet_str, 10)
        # Disallow leading zeroes, because no clear standard exists on
        # whether these should be interpreted as decimal or octal.
        if octet_int > 255 or (octet_str[0] == '0' and len(octet_str) > 1):
            raise ValueError
        return octet_int

    def _string_from_ip_int(self, ip_int):
        """Turns a 32-bit integer into dotted decimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            The IP address as a string in dotted decimal notation.

        """
        octets = []
        for _ in xrange(4):
            octets.insert(0, str(ip_int & 0xFF))
            ip_int >>= 8
        return '.'.join(octets)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        """The binary representation of this address."""
        return v4_int_to_packed(self._ip)

    @property
    def version(self):
        return self._version

    @property
    def is_reserved(self):
       """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within the
            reserved IPv4 Network range.

       """
       return self in IPv4Network('240.0.0.0/4')

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 1918.

        """
        return (self in IPv4Network('10.0.0.0/8') or
                self in IPv4Network('172.16.0.0/12') or
                self in IPv4Network('192.168.0.0/16'))

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is multicast.
            See RFC 3171 for details.

        """
        return self in IPv4Network('224.0.0.0/4')

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 5735 3.

        """
        return self in IPv4Network('0.0.0.0')

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback per RFC 3330.

        """
        return self in IPv4Network('127.0.0.0/8')

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is link-local per RFC 3927.

        """
        return self in IPv4Network('169.254.0.0/16')


class IPv4Address(_BaseV4, _BaseIP):

    """Represent and manipulate single IPv4 Addresses."""

    def __init__(self, address):

        """
        Args:
            address: A string or integer representing the IP
              '192.168.1.1'

              Additionally, an integer can be passed, so
              IPv4Address('192.168.1.1') == IPv4Address(3232235777).
              or, more generally
              IPv4Address(int(IPv4Address('192.168.1.1'))) ==
                IPv4Address('192.168.1.1')

        Raises:
            AddressValueError: If ipaddr isn't a valid IPv4 address.

        """
        _BaseV4.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, (int, long)):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError(address)
            return

        # Constructing from a packed address
        if isinstance(address, Bytes):
            try:
                self._ip, = struct.unpack('!I', address)
            except struct.error:
                raise AddressValueError(address)  # Wrong length.
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        self._ip = self._ip_int_from_string(addr_str)


class IPv4Network(_BaseV4, _BaseNet):

    """This class represents and manipulates 32-bit IPv4 networks.

    Attributes: [examples for IPv4Network('1.2.3.4/27')]
        ._ip: 16909060
        .ip: IPv4Address('1.2.3.4')
        .network: IPv4Address('1.2.3.0')
        .hostmask: IPv4Address('0.0.0.31')
        .broadcast: IPv4Address('1.2.3.31')
        .netmask: IPv4Address('255.255.255.224')
        .prefixlen: 27

    """

    # the valid octets for host and netmasks. only useful for IPv4.
    _valid_mask_octets = set((255, 254, 252, 248, 240, 224, 192, 128, 0))

    def __init__(self, address, strict=False):
        """Instantiate a new IPv4 network object.

        Args:
            address: A string or integer representing the IP [& network].
              '192.168.1.1/24'
              '192.168.1.1/255.255.255.0'
              '192.168.1.1/0.0.0.255'
              are all functionally the same in IPv4. Similarly,
              '192.168.1.1'
              '192.168.1.1/255.255.255.255'
              '192.168.1.1/32'
              are also functionaly equivalent. That is to say, failing to
              provide a subnetmask will create an object with a mask of /32.

              If the mask (portion after the / in the argument) is given in
              dotted quad form, it is treated as a netmask if it starts with a
              non-zero field (e.g. /255.0.0.0 == /8) and as a hostmask if it
              starts with a zero field (e.g. 0.255.255.255 == /8), with the
              single exception of an all-zero mask which is treated as a
              netmask == /0. If no mask is given, a default of /32 is used.

              Additionally, an integer can be passed, so
              IPv4Network('192.168.1.1') == IPv4Network(3232235777).
              or, more generally
              IPv4Network(int(IPv4Network('192.168.1.1'))) ==
                IPv4Network('192.168.1.1')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 192.168.1.0/24 and not an
              IP address on a network, eg, 192.168.1.1/24.

        Raises:
            AddressValueError: If ipaddr isn't a valid IPv4 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv4 address.
            ValueError: If strict was True and a network address was not
              supplied.

        """
        _BaseNet.__init__(self, address)
        _BaseV4.__init__(self, address)

        # Constructing from an integer or packed bytes.
        if isinstance(address, (int, long, Bytes)):
            self.ip = IPv4Address(address)
            self._ip = self.ip._ip
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ALL_ONES)
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = str(address).split('/')

        if len(addr) > 2:
            raise AddressValueError(address)

        self._ip = self._ip_int_from_string(addr[0])
        self.ip = IPv4Address(self._ip)

        if len(addr) == 2:
            mask = addr[1].split('.')
            if len(mask) == 4:
                # We have dotted decimal netmask.
                if self._is_valid_netmask(addr[1]):
                    self.netmask = IPv4Address(self._ip_int_from_string(
                            addr[1]))
                elif self._is_hostmask(addr[1]):
                    self.netmask = IPv4Address(
                        self._ip_int_from_string(addr[1]) ^ self._ALL_ONES)
                else:
                    raise NetmaskValueError('%s is not a valid netmask'
                                                     % addr[1])

                self._prefixlen = self._prefix_from_ip_int(int(self.netmask))
            else:
                # We have a netmask in prefix length form.
                if not self._is_valid_netmask(addr[1]):
                    raise NetmaskValueError(addr[1])
                self._prefixlen = int(addr[1])
                self.netmask = IPv4Address(self._ip_int_from_prefix(
                    self._prefixlen))
        else:
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv4Address(self._ip_int_from_prefix(
                self._prefixlen))
        if strict:
            if self.ip != self.network:
                raise ValueError('%s has host bits set' %
                                 self.ip)
        if self._prefixlen == (self._max_prefixlen - 1):
            self.iterhosts = self.__iter__

    def _is_hostmask(self, ip_str):
        """Test if the IP string is a hostmask (rather than a netmask).

        Args:
            ip_str: A string, the potential hostmask.

        Returns:
            A boolean, True if the IP string is a hostmask.

        """
        bits = ip_str.split('.')
        try:
            parts = [int(x) for x in bits if int(x) in self._valid_mask_octets]
        except ValueError:
            return False
        if len(parts) != len(bits):
            return False
        if parts[0] < parts[-1]:
            return True
        return False

    def _is_valid_netmask(self, netmask):
        """Verify that the netmask is valid.

        Args:
            netmask: A string, either a prefix or dotted decimal
              netmask.

        Returns:
            A boolean, True if the prefix represents a valid IPv4
            netmask.

        """
        mask = netmask.split('.')
        if len(mask) == 4:
            if [x for x in mask if int(x) not in self._valid_mask_octets]:
                return False
            if [y for idx, y in enumerate(mask) if idx > 0 and
                y > mask[idx - 1]]:
                return False
            return True
        try:
            netmask = int(netmask)
        except ValueError:
            return False
        return 0 <= netmask <= self._max_prefixlen

    # backwards compatibility
    IsRFC1918 = lambda self: self.is_private
    IsMulticast = lambda self: self.is_multicast
    IsLoopback = lambda self: self.is_loopback
    IsLinkLocal = lambda self: self.is_link_local


class _BaseV6(object):

    """Base IPv6 object.

    The following methods are used by IPv6 objects in both single IP
    addresses and networks.

    """

    _ALL_ONES = (2**IPV6LENGTH) - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')

    def __init__(self, address):
        self._version = 6
        self._max_prefixlen = IPV6LENGTH

    def _ip_int_from_string(self, ip_str):
        """Turn an IPv6 ip_str into an integer.

        Args:
            ip_str: A string, the IPv6 ip_str.

        Returns:
            A long, the IPv6 ip_str.

        Raises:
            AddressValueError: if ip_str isn't a valid IPv6 Address.

        """
        parts = ip_str.split(':')

        # An IPv6 address needs at least 2 colons (3 parts).
        if len(parts) < 3:
            raise AddressValueError(ip_str)

        # If the address has an IPv4-style suffix, convert it to hexadecimal.
        if '.' in parts[-1]:
            ipv4_int = IPv4Address(parts.pop())._ip
            parts.append('%x' % ((ipv4_int >> 16) & 0xFFFF))
            parts.append('%x' % (ipv4_int & 0xFFFF))

        # An IPv6 address can't have more than 8 colons (9 parts).
        if len(parts) > self._HEXTET_COUNT + 1:
            raise AddressValueError(ip_str)

        # Disregarding the endpoints, find '::' with nothing in between.
        # This indicates that a run of zeroes has been skipped.
        try:
            skip_index, = (
                [i for i in xrange(1, len(parts) - 1) if not parts[i]] or
                [None])
        except ValueError:
            # Can't have more than one '::'
            raise AddressValueError(ip_str)

        # parts_hi is the number of parts to copy from above/before the '::'
        # parts_lo is the number of parts to copy from below/after the '::'
        if skip_index is not None:
            # If we found a '::', then check if it also covers the endpoints.
            parts_hi = skip_index
            parts_lo = len(parts) - skip_index - 1
            if not parts[0]:
                parts_hi -= 1
                if parts_hi:
                    raise AddressValueError(ip_str)  # ^: requires ^::
            if not parts[-1]:
                parts_lo -= 1
                if parts_lo:
                    raise AddressValueError(ip_str)  # :$ requires ::$
            parts_skipped = self._HEXTET_COUNT - (parts_hi + parts_lo)
            if parts_skipped < 1:
                raise AddressValueError(ip_str)
        else:
            # Otherwise, allocate the entire address to parts_hi.  The endpoints
            # could still be empty, but _parse_hextet() will check for that.
            if len(parts) != self._HEXTET_COUNT:
                raise AddressValueError(ip_str)
            parts_hi = len(parts)
            parts_lo = 0
            parts_skipped = 0

        try:
            # Now, parse the hextets into a 128-bit integer.
            ip_int = 0L
            for i in xrange(parts_hi):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            ip_int <<= 16 * parts_skipped
            for i in xrange(-parts_lo, 0):
                ip_int <<= 16
                ip_int |= self._parse_hextet(parts[i])
            return ip_int
        except ValueError:
            raise AddressValueError(ip_str)

    def _parse_hextet(self, hextet_str):
        """Convert an IPv6 hextet string into an integer.

        Args:
            hextet_str: A string, the number to parse.

        Returns:
            The hextet as an integer.

        Raises:
            ValueError: if the input isn't strictly a hex number from [0..FFFF].

        """
        # Whitelist the characters, since int() allows a lot of bizarre stuff.
        if not self._HEX_DIGITS.issuperset(hextet_str):
            raise ValueError
        if len(hextet_str) > 4:
          raise ValueError
        hextet_int = int(hextet_str, 16)
        if hextet_int > 0xFFFF:
            raise ValueError
        return hextet_int

    def _compress_hextets(self, hextets):
        """Compresses a list of hextets.

        Compresses a list of strings, replacing the longest continuous
        sequence of "0" in the list with "" and adding empty strings at
        the beginning or at the end of the string such that subsequently
        calling ":".join(hextets) will produce the compressed version of
        the IPv6 address.

        Args:
            hextets: A list of strings, the hextets to compress.

        Returns:
            A list of strings.

        """
        best_doublecolon_start = -1
        best_doublecolon_len = 0
        doublecolon_start = -1
        doublecolon_len = 0
        for index in range(len(hextets)):
            if hextets[index] == '0':
                doublecolon_len += 1
                if doublecolon_start == -1:
                    # Start of a sequence of zeros.
                    doublecolon_start = index
                if doublecolon_len > best_doublecolon_len:
                    # This is the longest sequence of zeros so far.
                    best_doublecolon_len = doublecolon_len
                    best_doublecolon_start = doublecolon_start
            else:
                doublecolon_len = 0
                doublecolon_start = -1

        if best_doublecolon_len > 1:
            best_doublecolon_end = (best_doublecolon_start +
                                    best_doublecolon_len)
            # For zeros at the end of the address.
            if best_doublecolon_end == len(hextets):
                hextets += ['']
            hextets[best_doublecolon_start:best_doublecolon_end] = ['']
            # For zeros at the beginning of the address.
            if best_doublecolon_start == 0:
                hextets = [''] + hextets

        return hextets

    def _string_from_ip_int(self, ip_int=None):
        """Turns a 128-bit integer into hexadecimal notation.

        Args:
            ip_int: An integer, the IP address.

        Returns:
            A string, the hexadecimal representation of the address.

        Raises:
            ValueError: The address is bigger than 128 bits of all ones.

        """
        if not ip_int and ip_int != 0:
            ip_int = int(self._ip)

        if ip_int > self._ALL_ONES:
            raise ValueError('IPv6 address is too large')

        hex_str = '%032x' % ip_int
        hextets = []
        for x in range(0, 32, 4):
            hextets.append('%x' % int(hex_str[x:x+4], 16))

        hextets = self._compress_hextets(hextets)
        return ':'.join(hextets)

    def _explode_shorthand_ip_string(self):
        """Expand a shortened IPv6 address.

        Args:
            ip_str: A string, the IPv6 address.

        Returns:
            A string, the expanded IPv6 address.

        """
        if isinstance(self, _BaseNet):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)

        ip_int = self._ip_int_from_string(ip_str)
        parts = []
        for i in xrange(self._HEXTET_COUNT):
            parts.append('%04x' % (ip_int & 0xFFFF))
            ip_int >>= 16
        parts.reverse()
        if isinstance(self, _BaseNet):
            return '%s/%d' % (':'.join(parts), self.prefixlen)
        return ':'.join(parts)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def packed(self):
        """The binary representation of this address."""
        return v6_int_to_packed(self._ip)

    @property
    def version(self):
        return self._version

    @property
    def is_multicast(self):
        """Test if the address is reserved for multicast use.

        Returns:
            A boolean, True if the address is a multicast address.
            See RFC 2373 2.7 for details.

        """
        return self in IPv6Network('ff00::/8')

    @property
    def is_reserved(self):
        """Test if the address is otherwise IETF reserved.

        Returns:
            A boolean, True if the address is within one of the
            reserved IPv6 Network ranges.

        """
        return (self in IPv6Network('::/8') or
                self in IPv6Network('100::/8') or
                self in IPv6Network('200::/7') or
                self in IPv6Network('400::/6') or
                self in IPv6Network('800::/5') or
                self in IPv6Network('1000::/4') or
                self in IPv6Network('4000::/3') or
                self in IPv6Network('6000::/3') or
                self in IPv6Network('8000::/3') or
                self in IPv6Network('A000::/3') or
                self in IPv6Network('C000::/3') or
                self in IPv6Network('E000::/4') or
                self in IPv6Network('F000::/5') or
                self in IPv6Network('F800::/6') or
                self in IPv6Network('FE00::/9'))

    @property
    def is_unspecified(self):
        """Test if the address is unspecified.

        Returns:
            A boolean, True if this is the unspecified address as defined in
            RFC 2373 2.5.2.

        """
        return self._ip == 0 and getattr(self, '_prefixlen', 128) == 128

    @property
    def is_loopback(self):
        """Test if the address is a loopback address.

        Returns:
            A boolean, True if the address is a loopback address as defined in
            RFC 2373 2.5.3.

        """
        return self._ip == 1 and getattr(self, '_prefixlen', 128) == 128

    @property
    def is_link_local(self):
        """Test if the address is reserved for link-local.

        Returns:
            A boolean, True if the address is reserved per RFC 4291.

        """
        return self in IPv6Network('fe80::/10')

    @property
    def is_site_local(self):
        """Test if the address is reserved for site-local.

        Note that the site-local address space has been deprecated by RFC 3879.
        Use is_private to test if this address is in the space of unique local
        addresses as defined by RFC 4193.

        Returns:
            A boolean, True if the address is reserved per RFC 3513 2.5.6.

        """
        return self in IPv6Network('fec0::/10')

    @property
    def is_private(self):
        """Test if this address is allocated for private networks.

        Returns:
            A boolean, True if the address is reserved per RFC 4193.

        """
        return self in IPv6Network('fc00::/7')

    @property
    def ipv4_mapped(self):
        """Return the IPv4 mapped address.

        Returns:
            If the IPv6 address is a v4 mapped address, return the
            IPv4 mapped address. Return None otherwise.

        """
        if (self._ip >> 32) != 0xFFFF:
            return None
        return IPv4Address(self._ip & 0xFFFFFFFF)

    @property
    def teredo(self):
        """Tuple of embedded teredo IPs.

        Returns:
            Tuple of the (server, client) IPs or None if the address
            doesn't appear to be a teredo address (doesn't start with
            2001::/32)

        """
        if (self._ip >> 96) != 0x20010000:
            return None
        return (IPv4Address((self._ip >> 64) & 0xFFFFFFFF),
                IPv4Address(~self._ip & 0xFFFFFFFF))

    @property
    def sixtofour(self):
        """Return the IPv4 6to4 embedded address.

        Returns:
            The IPv4 6to4-embedded address if present or None if the
            address doesn't appear to contain a 6to4 embedded address.

        """
        if (self._ip >> 112) != 0x2002:
            return None
        return IPv4Address((self._ip >> 80) & 0xFFFFFFFF)


class IPv6Address(_BaseV6, _BaseIP):

    """Represent and manipulate single IPv6 Addresses.
    """

    def __init__(self, address):
        """Instantiate a new IPv6 address object.

        Args:
            address: A string or integer representing the IP

              Additionally, an integer can be passed, so
              IPv6Address('2001:4860::') ==
                IPv6Address(42541956101370907050197289607612071936L).
              or, more generally
              IPv6Address(IPv6Address('2001:4860::')._ip) ==
                IPv6Address('2001:4860::')

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.

        """
        _BaseV6.__init__(self, address)

        # Efficient constructor from integer.
        if isinstance(address, (int, long)):
            self._ip = address
            if address < 0 or address > self._ALL_ONES:
                raise AddressValueError(address)
            return

        # Constructing from a packed address
        if isinstance(address, Bytes):
            try:
                hi, lo = struct.unpack('!QQ', address)
            except struct.error:
                raise AddressValueError(address)  # Wrong length.
            self._ip = (hi << 64) | lo
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP string.
        addr_str = str(address)
        if not addr_str:
            raise AddressValueError('')

        self._ip = self._ip_int_from_string(addr_str)


class IPv6Network(_BaseV6, _BaseNet):

    """This class represents and manipulates 128-bit IPv6 networks.

    Attributes: [examples for IPv6('2001:658:22A:CAFE:200::1/64')]
        .ip: IPv6Address('2001:658:22a:cafe:200::1')
        .network: IPv6Address('2001:658:22a:cafe::')
        .hostmask: IPv6Address('::ffff:ffff:ffff:ffff')
        .broadcast: IPv6Address('2001:658:22a:cafe:ffff:ffff:ffff:ffff')
        .netmask: IPv6Address('ffff:ffff:ffff:ffff::')
        .prefixlen: 64

    """


    def __init__(self, address, strict=False):
        """Instantiate a new IPv6 Network object.

        Args:
            address: A string or integer representing the IPv6 network or the IP
              and prefix/netmask.
              '2001:4860::/128'
              '2001:4860:0000:0000:0000:0000:0000:0000/128'
              '2001:4860::'
              are all functionally the same in IPv6.  That is to say,
              failing to provide a subnetmask will create an object with
              a mask of /128.

              Additionally, an integer can be passed, so
              IPv6Network('2001:4860::') ==
                IPv6Network(42541956101370907050197289607612071936L).
              or, more generally
              IPv6Network(IPv6Network('2001:4860::')._ip) ==
                IPv6Network('2001:4860::')

            strict: A boolean. If true, ensure that we have been passed
              A true network address, eg, 192.168.1.0/24 and not an
              IP address on a network, eg, 192.168.1.1/24.

        Raises:
            AddressValueError: If address isn't a valid IPv6 address.
            NetmaskValueError: If the netmask isn't valid for
              an IPv6 address.
            ValueError: If strict was True and a network address was not
              supplied.

        """
        _BaseNet.__init__(self, address)
        _BaseV6.__init__(self, address)

        # Constructing from an integer or packed bytes.
        if isinstance(address, (int, long, Bytes)):
            self.ip = IPv6Address(address)
            self._ip = self.ip._ip
            self._prefixlen = self._max_prefixlen
            self.netmask = IPv6Address(self._ALL_ONES)
            return

        # Assume input argument to be string or any object representation
        # which converts into a formatted IP prefix string.
        addr = str(address).split('/')

        if len(addr) > 2:
            raise AddressValueError(address)

        self._ip = self._ip_int_from_string(addr[0])
        self.ip = IPv6Address(self._ip)

        if len(addr) == 2:
            if self._is_valid_netmask(addr[1]):
                self._prefixlen = int(addr[1])
            else:
                raise NetmaskValueError(addr[1])
        else:
            self._prefixlen = self._max_prefixlen

        self.netmask = IPv6Address(self._ip_int_from_prefix(self._prefixlen))

        if strict:
            if self.ip != self.network:
                raise ValueError('%s has host bits set' %
                                 self.ip)
        if self._prefixlen == (self._max_prefixlen - 1):
            self.iterhosts = self.__iter__

    def _is_valid_netmask(self, prefixlen):
        """Verify that the netmask/prefixlen is valid.

        Args:
            prefixlen: A string, the netmask in prefix length format.

        Returns:
            A boolean, True if the prefix represents a valid IPv6
            netmask.

        """
        try:
            prefixlen = int(prefixlen)
        except ValueError:
            return False
        return 0 <= prefixlen <= self._max_prefixlen

    @property
    def with_netmask(self):
        return self.with_prefixlen

########NEW FILE########
__FILENAME__ = ipaddr_test
#!/usr/bin/python
#
# Copyright 2007 Google Inc.
#  Licensed to PSF under a Contributor Agreement.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unittest for ipaddr module."""


import unittest
import time
import ipaddr

# Compatibility function to cast str to bytes objects
if issubclass(ipaddr.Bytes, str):
    _cb = ipaddr.Bytes
else:
    _cb = lambda bytestr: bytes(bytestr, 'charmap')

class IpaddrUnitTest(unittest.TestCase):

    def setUp(self):
        self.ipv4 = ipaddr.IPv4Network('1.2.3.4/24')
        self.ipv4_hostmask = ipaddr.IPv4Network('10.0.0.1/0.255.255.255')
        self.ipv6 = ipaddr.IPv6Network('2001:658:22a:cafe:200:0:0:1/64')

    def tearDown(self):
        del(self.ipv4)
        del(self.ipv4_hostmask)
        del(self.ipv6)
        del(self)

    def testRepr(self):
        self.assertEqual("IPv4Network('1.2.3.4/32')",
                         repr(ipaddr.IPv4Network('1.2.3.4')))
        self.assertEqual("IPv6Network('::1/128')",
                         repr(ipaddr.IPv6Network('::1')))

    def testAutoMasking(self):
        addr1 = ipaddr.IPv4Network('1.1.1.255/24')
        addr1_masked = ipaddr.IPv4Network('1.1.1.0/24')
        self.assertEqual(addr1_masked, addr1.masked())

        addr2 = ipaddr.IPv6Network('2000:cafe::efac:100/96')
        addr2_masked = ipaddr.IPv6Network('2000:cafe::/96')
        self.assertEqual(addr2_masked, addr2.masked())

    # issue57
    def testAddressIntMath(self):
        self.assertEqual(ipaddr.IPv4Address('1.1.1.1') + 255,
                         ipaddr.IPv4Address('1.1.2.0'))
        self.assertEqual(ipaddr.IPv4Address('1.1.1.1') - 256,
                         ipaddr.IPv4Address('1.1.0.1'))
        self.assertEqual(ipaddr.IPv6Address('::1') + (2**16 - 2),
                         ipaddr.IPv6Address('::ffff'))
        self.assertEqual(ipaddr.IPv6Address('::ffff') - (2**16 - 2),
                         ipaddr.IPv6Address('::1'))

    def testInvalidStrings(self):
        def AssertInvalidIP(ip_str):
            self.assertRaises(ValueError, ipaddr.IPAddress, ip_str)
        AssertInvalidIP("")
        AssertInvalidIP("016.016.016.016")
        AssertInvalidIP("016.016.016")
        AssertInvalidIP("016.016")
        AssertInvalidIP("016")
        AssertInvalidIP("000.000.000.000")
        AssertInvalidIP("000")
        AssertInvalidIP("0x0a.0x0a.0x0a.0x0a")
        AssertInvalidIP("0x0a.0x0a.0x0a")
        AssertInvalidIP("0x0a.0x0a")
        AssertInvalidIP("0x0a")
        AssertInvalidIP("42.42.42.42.42")
        AssertInvalidIP("42.42.42")
        AssertInvalidIP("42.42")
        AssertInvalidIP("42")
        AssertInvalidIP("42..42.42")
        AssertInvalidIP("42..42.42.42")
        AssertInvalidIP("42.42.42.42.")
        AssertInvalidIP("42.42.42.42...")
        AssertInvalidIP(".42.42.42.42")
        AssertInvalidIP("...42.42.42.42")
        AssertInvalidIP("42.42.42.-0")
        AssertInvalidIP("42.42.42.+0")
        AssertInvalidIP(".")
        AssertInvalidIP("...")
        AssertInvalidIP("bogus")
        AssertInvalidIP("bogus.com")
        AssertInvalidIP("192.168.0.1.com")
        AssertInvalidIP("12345.67899.-54321.-98765")
        AssertInvalidIP("257.0.0.0")
        AssertInvalidIP("42.42.42.-42")
        AssertInvalidIP("3ffe::1.net")
        AssertInvalidIP("3ffe::1::1")
        AssertInvalidIP("1::2::3::4:5")
        AssertInvalidIP("::7:6:5:4:3:2:")
        AssertInvalidIP(":6:5:4:3:2:1::")
        AssertInvalidIP("2001::db:::1")
        AssertInvalidIP("FEDC:9878")
        AssertInvalidIP("+1.+2.+3.4")
        AssertInvalidIP("1.2.3.4e0")
        AssertInvalidIP("::7:6:5:4:3:2:1:0")
        AssertInvalidIP("7:6:5:4:3:2:1:0::")
        AssertInvalidIP("9:8:7:6:5:4:3::2:1")
        AssertInvalidIP("0:1:2:3::4:5:6:7")
        AssertInvalidIP("3ffe:0:0:0:0:0:0:0:1")
        AssertInvalidIP("3ffe::10000")
        AssertInvalidIP("3ffe::goog")
        AssertInvalidIP("3ffe::-0")
        AssertInvalidIP("3ffe::+0")
        AssertInvalidIP("3ffe::-1")
        AssertInvalidIP(":")
        AssertInvalidIP(":::")
        AssertInvalidIP("::1.2.3")
        AssertInvalidIP("::1.2.3.4.5")
        AssertInvalidIP("::1.2.3.4:")
        AssertInvalidIP("1.2.3.4::")
        AssertInvalidIP("2001:db8::1:")
        AssertInvalidIP(":2001:db8::1")
        AssertInvalidIP(":1:2:3:4:5:6:7")
        AssertInvalidIP("1:2:3:4:5:6:7:")
        AssertInvalidIP(":1:2:3:4:5:6:")
        AssertInvalidIP("192.0.2.1/32")
        AssertInvalidIP("2001:db8::1/128")
        AssertInvalidIP("02001:db8::")

        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv4Network, '')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv4Network,
                          'google.com')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv4Network,
                          '::1.2.3.4')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network, '')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          'google.com')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          '1.2.3.4')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          'cafe:cafe::/128/190')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          '1234:axy::b')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Address,
                          '1234:axy::b')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Address,
                          '2001:db8:::1')
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Address,
                          '2001:888888::1')
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Address(1)._ip_int_from_string,
                          '1.a.2.3')
        self.assertEqual(False, ipaddr.IPv4Network(1)._is_hostmask('1.a.2.3'))

    def testGetNetwork(self):
        self.assertEqual(int(self.ipv4.network), 16909056)
        self.assertEqual(str(self.ipv4.network), '1.2.3.0')
        self.assertEqual(str(self.ipv4_hostmask.network), '10.0.0.0')

        self.assertEqual(int(self.ipv6.network),
                         42540616829182469433403647294022090752)
        self.assertEqual(str(self.ipv6.network),
                         '2001:658:22a:cafe::')
        self.assertEqual(str(self.ipv6.hostmask),
                         '::ffff:ffff:ffff:ffff')

    def testBadVersionComparison(self):
        # These should always raise TypeError
        v4addr = ipaddr.IPAddress('1.1.1.1')
        v4net = ipaddr.IPNetwork('1.1.1.1')
        v6addr = ipaddr.IPAddress('::1')
        v6net = ipaddr.IPAddress('::1')

        self.assertRaises(TypeError, v4addr.__lt__, v6addr)
        self.assertRaises(TypeError, v4addr.__gt__, v6addr)
        self.assertRaises(TypeError, v4net.__lt__, v6net)
        self.assertRaises(TypeError, v4net.__gt__, v6net)

        self.assertRaises(TypeError, v6addr.__lt__, v4addr)
        self.assertRaises(TypeError, v6addr.__gt__, v4addr)
        self.assertRaises(TypeError, v6net.__lt__, v4net)
        self.assertRaises(TypeError, v6net.__gt__, v4net)

    def testMixedTypeComparison(self):
        v4addr = ipaddr.IPAddress('1.1.1.1')
        v4net = ipaddr.IPNetwork('1.1.1.1/32')
        v6addr = ipaddr.IPAddress('::1')
        v6net = ipaddr.IPNetwork('::1/128')

        self.assertFalse(v4net.__contains__(v6net))
        self.assertFalse(v6net.__contains__(v4net))

        self.assertRaises(TypeError, lambda: v4addr < v4net)
        self.assertRaises(TypeError, lambda: v4addr > v4net)
        self.assertRaises(TypeError, lambda: v4net < v4addr)
        self.assertRaises(TypeError, lambda: v4net > v4addr)

        self.assertRaises(TypeError, lambda: v6addr < v6net)
        self.assertRaises(TypeError, lambda: v6addr > v6net)
        self.assertRaises(TypeError, lambda: v6net < v6addr)
        self.assertRaises(TypeError, lambda: v6net > v6addr)

        # with get_mixed_type_key, you can sort addresses and network.
        self.assertEqual([v4addr, v4net], sorted([v4net, v4addr],
                                                 key=ipaddr.get_mixed_type_key))
        self.assertEqual([v6addr, v6net], sorted([v6net, v6addr],
                                                 key=ipaddr.get_mixed_type_key))

    def testIpFromInt(self):
        self.assertEqual(self.ipv4.ip, ipaddr.IPv4Network(16909060).ip)
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Network, 2**32)
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Network, -1)

        ipv4 = ipaddr.IPNetwork('1.2.3.4')
        ipv6 = ipaddr.IPNetwork('2001:658:22a:cafe:200:0:0:1')
        self.assertEqual(ipv4, ipaddr.IPNetwork(int(ipv4)))
        self.assertEqual(ipv6, ipaddr.IPNetwork(int(ipv6)))

        v6_int = 42540616829182469433547762482097946625
        self.assertEqual(self.ipv6.ip, ipaddr.IPv6Network(v6_int).ip)
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv6Network, 2**128)
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv6Network, -1)

        self.assertEqual(ipaddr.IPNetwork(self.ipv4.ip).version, 4)
        self.assertEqual(ipaddr.IPNetwork(self.ipv6.ip).version, 6)

    def testIpFromPacked(self):
        ip = ipaddr.IPNetwork

        self.assertEqual(self.ipv4.ip,
                         ip(_cb('\x01\x02\x03\x04')).ip)
        self.assertEqual(ip('255.254.253.252'),
                         ip(_cb('\xff\xfe\xfd\xfc')))
        self.assertRaises(ValueError, ipaddr.IPNetwork, _cb('\x00' * 3))
        self.assertRaises(ValueError, ipaddr.IPNetwork, _cb('\x00' * 5))
        self.assertEqual(self.ipv6.ip,
                         ip(_cb('\x20\x01\x06\x58\x02\x2a\xca\xfe'
                           '\x02\x00\x00\x00\x00\x00\x00\x01')).ip)
        self.assertEqual(ip('ffff:2:3:4:ffff::'),
                         ip(_cb('\xff\xff\x00\x02\x00\x03\x00\x04' +
                               '\xff\xff' + '\x00' * 6)))
        self.assertEqual(ip('::'),
                         ip(_cb('\x00' * 16)))
        self.assertRaises(ValueError, ip, _cb('\x00' * 15))
        self.assertRaises(ValueError, ip, _cb('\x00' * 17))

    def testGetIp(self):
        self.assertEqual(int(self.ipv4.ip), 16909060)
        self.assertEqual(str(self.ipv4.ip), '1.2.3.4')
        self.assertEqual(str(self.ipv4_hostmask.ip), '10.0.0.1')

        self.assertEqual(int(self.ipv6.ip),
                         42540616829182469433547762482097946625)
        self.assertEqual(str(self.ipv6.ip),
                         '2001:658:22a:cafe:200::1')

    def testGetNetmask(self):
        self.assertEqual(int(self.ipv4.netmask), 4294967040L)
        self.assertEqual(str(self.ipv4.netmask), '255.255.255.0')
        self.assertEqual(str(self.ipv4_hostmask.netmask), '255.0.0.0')
        self.assertEqual(int(self.ipv6.netmask),
                         340282366920938463444927863358058659840)
        self.assertEqual(self.ipv6.prefixlen, 64)

    def testZeroNetmask(self):
        ipv4_zero_netmask = ipaddr.IPv4Network('1.2.3.4/0')
        self.assertEqual(int(ipv4_zero_netmask.netmask), 0)
        self.assertTrue(ipv4_zero_netmask._is_valid_netmask(str(0)))

        ipv6_zero_netmask = ipaddr.IPv6Network('::1/0')
        self.assertEqual(int(ipv6_zero_netmask.netmask), 0)
        self.assertTrue(ipv6_zero_netmask._is_valid_netmask(str(0)))

    def testGetBroadcast(self):
        self.assertEqual(int(self.ipv4.broadcast), 16909311L)
        self.assertEqual(str(self.ipv4.broadcast), '1.2.3.255')

        self.assertEqual(int(self.ipv6.broadcast),
                         42540616829182469451850391367731642367)
        self.assertEqual(str(self.ipv6.broadcast),
                         '2001:658:22a:cafe:ffff:ffff:ffff:ffff')

    def testGetPrefixlen(self):
        self.assertEqual(self.ipv4.prefixlen, 24)

        self.assertEqual(self.ipv6.prefixlen, 64)

    def testGetSupernet(self):
        self.assertEqual(self.ipv4.supernet().prefixlen, 23)
        self.assertEqual(str(self.ipv4.supernet().network), '1.2.2.0')
        self.assertEqual(ipaddr.IPv4Network('0.0.0.0/0').supernet(),
                         ipaddr.IPv4Network('0.0.0.0/0'))

        self.assertEqual(self.ipv6.supernet().prefixlen, 63)
        self.assertEqual(str(self.ipv6.supernet().network),
                         '2001:658:22a:cafe::')
        self.assertEqual(ipaddr.IPv6Network('::0/0').supernet(),
                         ipaddr.IPv6Network('::0/0'))

    def testGetSupernet3(self):
        self.assertEqual(self.ipv4.supernet(3).prefixlen, 21)
        self.assertEqual(str(self.ipv4.supernet(3).network), '1.2.0.0')

        self.assertEqual(self.ipv6.supernet(3).prefixlen, 61)
        self.assertEqual(str(self.ipv6.supernet(3).network),
                         '2001:658:22a:caf8::')

    def testGetSupernet4(self):
        self.assertRaises(ValueError, self.ipv4.supernet, prefixlen_diff=2,
                          new_prefix=1)
        self.assertRaises(ValueError, self.ipv4.supernet, new_prefix=25)
        self.assertEqual(self.ipv4.supernet(prefixlen_diff=2),
                         self.ipv4.supernet(new_prefix=22))

        self.assertRaises(ValueError, self.ipv6.supernet, prefixlen_diff=2,
                          new_prefix=1)
        self.assertRaises(ValueError, self.ipv6.supernet, new_prefix=65)
        self.assertEqual(self.ipv6.supernet(prefixlen_diff=2),
                         self.ipv6.supernet(new_prefix=62))

    def testIterSubnets(self):
        self.assertEqual(self.ipv4.subnet(), list(self.ipv4.iter_subnets()))
        self.assertEqual(self.ipv6.subnet(), list(self.ipv6.iter_subnets()))

    def testIterHosts(self):
        self.assertEqual([ipaddr.IPv4Address('2.0.0.0'),
                          ipaddr.IPv4Address('2.0.0.1')],
                         list(ipaddr.IPNetwork('2.0.0.0/31').iterhosts()))

    def testFancySubnetting(self):
        self.assertEqual(sorted(self.ipv4.subnet(prefixlen_diff=3)),
                         sorted(self.ipv4.subnet(new_prefix=27)))
        self.assertRaises(ValueError, self.ipv4.subnet, new_prefix=23)
        self.assertRaises(ValueError, self.ipv4.subnet,
                          prefixlen_diff=3, new_prefix=27)
        self.assertEqual(sorted(self.ipv6.subnet(prefixlen_diff=4)),
                         sorted(self.ipv6.subnet(new_prefix=68)))
        self.assertRaises(ValueError, self.ipv6.subnet, new_prefix=63)
        self.assertRaises(ValueError, self.ipv6.subnet,
                          prefixlen_diff=4, new_prefix=68)

    def testGetSubnet(self):
        self.assertEqual(self.ipv4.subnet()[0].prefixlen, 25)
        self.assertEqual(str(self.ipv4.subnet()[0].network), '1.2.3.0')
        self.assertEqual(str(self.ipv4.subnet()[1].network), '1.2.3.128')

        self.assertEqual(self.ipv6.subnet()[0].prefixlen, 65)

    def testGetSubnetForSingle32(self):
        ip = ipaddr.IPv4Network('1.2.3.4/32')
        subnets1 = [str(x) for x in ip.subnet()]
        subnets2 = [str(x) for x in ip.subnet(2)]
        self.assertEqual(subnets1, ['1.2.3.4/32'])
        self.assertEqual(subnets1, subnets2)

    def testGetSubnetForSingle128(self):
        ip = ipaddr.IPv6Network('::1/128')
        subnets1 = [str(x) for x in ip.subnet()]
        subnets2 = [str(x) for x in ip.subnet(2)]
        self.assertEqual(subnets1, ['::1/128'])
        self.assertEqual(subnets1, subnets2)

    def testSubnet2(self):
        ips = [str(x) for x in self.ipv4.subnet(2)]
        self.assertEqual(
            ips,
            ['1.2.3.0/26', '1.2.3.64/26', '1.2.3.128/26', '1.2.3.192/26'])

        ipsv6 = [str(x) for x in self.ipv6.subnet(2)]
        self.assertEqual(
            ipsv6,
            ['2001:658:22a:cafe::/66',
             '2001:658:22a:cafe:4000::/66',
             '2001:658:22a:cafe:8000::/66',
             '2001:658:22a:cafe:c000::/66'])

    def testSubnetFailsForLargeCidrDiff(self):
        self.assertRaises(ValueError, self.ipv4.subnet, 9)
        self.assertRaises(ValueError, self.ipv6.subnet, 65)

    def testSupernetFailsForLargeCidrDiff(self):
        self.assertRaises(ValueError, self.ipv4.supernet, 25)
        self.assertRaises(ValueError, self.ipv6.supernet, 65)

    def testSubnetFailsForNegativeCidrDiff(self):
        self.assertRaises(ValueError, self.ipv4.subnet, -1)
        self.assertRaises(ValueError, self.ipv6.subnet, -1)

    def testGetNumHosts(self):
        self.assertEqual(self.ipv4.numhosts, 256)
        self.assertEqual(self.ipv4.subnet()[0].numhosts, 128)
        self.assertEqual(self.ipv4.supernet().numhosts, 512)

        self.assertEqual(self.ipv6.numhosts, 18446744073709551616)
        self.assertEqual(self.ipv6.subnet()[0].numhosts, 9223372036854775808)
        self.assertEqual(self.ipv6.supernet().numhosts, 36893488147419103232)

    def testContains(self):
        self.assertTrue(ipaddr.IPv4Network('1.2.3.128/25') in self.ipv4)
        self.assertFalse(ipaddr.IPv4Network('1.2.4.1/24') in self.ipv4)
        self.assertTrue(self.ipv4 in self.ipv4)
        self.assertTrue(self.ipv6 in self.ipv6)
        # We can test addresses and string as well.
        addr1 = ipaddr.IPv4Address('1.2.3.37')
        self.assertTrue(addr1 in self.ipv4)
        # issue 61, bad network comparison on like-ip'd network objects
        # with identical broadcast addresses.
        self.assertFalse(ipaddr.IPv4Network('1.1.0.0/16').__contains__(
                ipaddr.IPv4Network('1.0.0.0/15')))

    def testBadAddress(self):
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv4Network,
                          'poop')
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Network, '1.2.3.256')

        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          'poopv6')
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Network, '1.2.3.4/32/24')
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv4Network, '10/8')
        self.assertRaises(ipaddr.AddressValueError,
                          ipaddr.IPv6Network, '10/8')


    def testBadNetMask(self):
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv4Network, '1.2.3.4/')
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv4Network, '1.2.3.4/33')
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv4Network, '1.2.3.4/254.254.255.256')
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv4Network, '1.1.1.1/240.255.0.0')
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv6Network, '::1/')
        self.assertRaises(ipaddr.NetmaskValueError,
                          ipaddr.IPv6Network, '::1/129')

    def testNth(self):
        self.assertEqual(str(self.ipv4[5]), '1.2.3.5')
        self.assertRaises(IndexError, self.ipv4.__getitem__, 256)

        self.assertEqual(str(self.ipv6[5]),
                         '2001:658:22a:cafe::5')

    def testGetitem(self):
        # http://code.google.com/p/ipaddr-py/issues/detail?id=15
        addr = ipaddr.IPv4Network('172.31.255.128/255.255.255.240')
        self.assertEqual(28, addr.prefixlen)
        addr_list = list(addr)
        self.assertEqual('172.31.255.128', str(addr_list[0]))
        self.assertEqual('172.31.255.128', str(addr[0]))
        self.assertEqual('172.31.255.143', str(addr_list[-1]))
        self.assertEqual('172.31.255.143', str(addr[-1]))
        self.assertEqual(addr_list[-1], addr[-1])

    def testEqual(self):
        self.assertTrue(self.ipv4 == ipaddr.IPv4Network('1.2.3.4/24'))
        self.assertFalse(self.ipv4 == ipaddr.IPv4Network('1.2.3.4/23'))
        self.assertFalse(self.ipv4 == ipaddr.IPv6Network('::1.2.3.4/24'))
        self.assertFalse(self.ipv4 == '')
        self.assertFalse(self.ipv4 == [])
        self.assertFalse(self.ipv4 == 2)
        self.assertTrue(ipaddr.IPNetwork('1.1.1.1/32') ==
                        ipaddr.IPAddress('1.1.1.1'))
        self.assertTrue(ipaddr.IPNetwork('1.1.1.1/24') ==
                        ipaddr.IPAddress('1.1.1.1'))
        self.assertFalse(ipaddr.IPNetwork('1.1.1.0/24') ==
                         ipaddr.IPAddress('1.1.1.1'))

        self.assertTrue(self.ipv6 ==
            ipaddr.IPv6Network('2001:658:22a:cafe:200::1/64'))
        self.assertTrue(ipaddr.IPNetwork('::1/128') ==
                        ipaddr.IPAddress('::1'))
        self.assertTrue(ipaddr.IPNetwork('::1/127') ==
                        ipaddr.IPAddress('::1'))
        self.assertFalse(ipaddr.IPNetwork('::0/127') ==
                         ipaddr.IPAddress('::1'))
        self.assertFalse(self.ipv6 ==
            ipaddr.IPv6Network('2001:658:22a:cafe:200::1/63'))
        self.assertFalse(self.ipv6 == ipaddr.IPv4Network('1.2.3.4/23'))
        self.assertFalse(self.ipv6 == '')
        self.assertFalse(self.ipv6 == [])
        self.assertFalse(self.ipv6 == 2)

    def testNotEqual(self):
        self.assertFalse(self.ipv4 != ipaddr.IPv4Network('1.2.3.4/24'))
        self.assertTrue(self.ipv4 != ipaddr.IPv4Network('1.2.3.4/23'))
        self.assertTrue(self.ipv4 != ipaddr.IPv6Network('::1.2.3.4/24'))
        self.assertTrue(self.ipv4 != '')
        self.assertTrue(self.ipv4 != [])
        self.assertTrue(self.ipv4 != 2)

        addr2 = ipaddr.IPAddress('2001:658:22a:cafe:200::1')
        self.assertFalse(self.ipv6 !=
            ipaddr.IPv6Network('2001:658:22a:cafe:200::1/64'))
        self.assertTrue(self.ipv6 !=
            ipaddr.IPv6Network('2001:658:22a:cafe:200::1/63'))
        self.assertTrue(self.ipv6 != ipaddr.IPv4Network('1.2.3.4/23'))
        self.assertTrue(self.ipv6 != '')
        self.assertTrue(self.ipv6 != [])
        self.assertTrue(self.ipv6 != 2)

    def testSlash32Constructor(self):
        self.assertEqual(str(ipaddr.IPv4Network('1.2.3.4/255.255.255.255')),
                          '1.2.3.4/32')

    def testSlash128Constructor(self):
        self.assertEqual(str(ipaddr.IPv6Network('::1/128')),
                                  '::1/128')

    def testSlash0Constructor(self):
        self.assertEqual(str(ipaddr.IPv4Network('1.2.3.4/0.0.0.0')),
                          '1.2.3.4/0')

    def testCollapsing(self):
        # test only IP addresses including some duplicates
        ip1 = ipaddr.IPv4Address('1.1.1.0')
        ip2 = ipaddr.IPv4Address('1.1.1.1')
        ip3 = ipaddr.IPv4Address('1.1.1.2')
        ip4 = ipaddr.IPv4Address('1.1.1.3')
        ip5 = ipaddr.IPv4Address('1.1.1.4')
        ip6 = ipaddr.IPv4Address('1.1.1.0')
        # check that addreses are subsumed properly.
        collapsed = ipaddr.collapse_address_list([ip1, ip2, ip3, ip4, ip5, ip6])
        self.assertEqual(collapsed, [ipaddr.IPv4Network('1.1.1.0/30'),
                                     ipaddr.IPv4Network('1.1.1.4/32')])

        # test a mix of IP addresses and networks including some duplicates
        ip1 = ipaddr.IPv4Address('1.1.1.0')
        ip2 = ipaddr.IPv4Address('1.1.1.1')
        ip3 = ipaddr.IPv4Address('1.1.1.2')
        ip4 = ipaddr.IPv4Address('1.1.1.3')
        ip5 = ipaddr.IPv4Network('1.1.1.4/30')
        ip6 = ipaddr.IPv4Network('1.1.1.4/30')
        # check that addreses are subsumed properly.
        collapsed = ipaddr.collapse_address_list([ip5, ip1, ip2, ip3, ip4, ip6])
        self.assertEqual(collapsed, [ipaddr.IPv4Network('1.1.1.0/29')])

        # test only IP networks
        ip1 = ipaddr.IPv4Network('1.1.0.0/24')
        ip2 = ipaddr.IPv4Network('1.1.1.0/24')
        ip3 = ipaddr.IPv4Network('1.1.2.0/24')
        ip4 = ipaddr.IPv4Network('1.1.3.0/24')
        ip5 = ipaddr.IPv4Network('1.1.4.0/24')
        # stored in no particular order b/c we want CollapseAddr to call [].sort
        ip6 = ipaddr.IPv4Network('1.1.0.0/22')
        # check that addreses are subsumed properly.
        collapsed = ipaddr.collapse_address_list([ip1, ip2, ip3, ip4, ip5, ip6])
        self.assertEqual(collapsed, [ipaddr.IPv4Network('1.1.0.0/22'),
                                     ipaddr.IPv4Network('1.1.4.0/24')])

        # test that two addresses are supernet'ed properly
        collapsed = ipaddr.collapse_address_list([ip1, ip2])
        self.assertEqual(collapsed, [ipaddr.IPv4Network('1.1.0.0/23')])

        # test same IP networks
        ip_same1 = ip_same2 = ipaddr.IPv4Network('1.1.1.1/32')
        self.assertEqual(ipaddr.collapse_address_list([ip_same1, ip_same2]),
                         [ip_same1])

        # test same IP addresses
        ip_same1 = ip_same2 = ipaddr.IPv4Address('1.1.1.1')
        self.assertEqual(ipaddr.collapse_address_list([ip_same1, ip_same2]),
                         [ipaddr.IPNetwork('1.1.1.1/32')])
        ip1 = ipaddr.IPv6Network('::2001:1/100')
        ip2 = ipaddr.IPv6Network('::2002:1/120')
        ip3 = ipaddr.IPv6Network('::2001:1/96')
        # test that ipv6 addresses are subsumed properly.
        collapsed = ipaddr.collapse_address_list([ip1, ip2, ip3])
        self.assertEqual(collapsed, [ip3])

        # the toejam test
        ip1 = ipaddr.IPAddress('1.1.1.1')
        ip2 = ipaddr.IPAddress('::1')
        self.assertRaises(TypeError, ipaddr.collapse_address_list,
                          [ip1, ip2])

    def testSummarizing(self):
        #ip = ipaddr.IPAddress
        #ipnet = ipaddr.IPNetwork
        summarize = ipaddr.summarize_address_range
        ip1 = ipaddr.IPAddress('1.1.1.0')
        ip2 = ipaddr.IPAddress('1.1.1.255')
        # test a /24 is sumamrized properly
        self.assertEqual(summarize(ip1, ip2)[0], ipaddr.IPNetwork('1.1.1.0/24'))
        # test an  IPv4 range that isn't on a network byte boundary
        ip2 = ipaddr.IPAddress('1.1.1.8')
        self.assertEqual(summarize(ip1, ip2), [ipaddr.IPNetwork('1.1.1.0/29'),
                                               ipaddr.IPNetwork('1.1.1.8')])

        ip1 = ipaddr.IPAddress('1::')
        ip2 = ipaddr.IPAddress('1:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
        # test a IPv6 is sumamrized properly
        self.assertEqual(summarize(ip1, ip2)[0], ipaddr.IPNetwork('1::/16'))
        # test an IPv6 range that isn't on a network byte boundary
        ip2 = ipaddr.IPAddress('2::')
        self.assertEqual(summarize(ip1, ip2), [ipaddr.IPNetwork('1::/16'),
                                               ipaddr.IPNetwork('2::/128')])

        # test exception raised when first is greater than last
        self.assertRaises(ValueError, summarize, ipaddr.IPAddress('1.1.1.0'),
            ipaddr.IPAddress('1.1.0.0'))
        # test exception raised when first and last aren't IP addresses
        self.assertRaises(TypeError, summarize,
                          ipaddr.IPNetwork('1.1.1.0'),
                          ipaddr.IPNetwork('1.1.0.0'))
        self.assertRaises(TypeError, summarize,
            ipaddr.IPNetwork('1.1.1.0'), ipaddr.IPNetwork('1.1.0.0'))
        # test exception raised when first and last are not same version
        self.assertRaises(TypeError, summarize, ipaddr.IPAddress('::'),
            ipaddr.IPNetwork('1.1.0.0'))

    def testAddressComparison(self):
        self.assertTrue(ipaddr.IPAddress('1.1.1.1') <=
                        ipaddr.IPAddress('1.1.1.1'))
        self.assertTrue(ipaddr.IPAddress('1.1.1.1') <=
                        ipaddr.IPAddress('1.1.1.2'))
        self.assertTrue(ipaddr.IPAddress('::1') <= ipaddr.IPAddress('::1'))
        self.assertTrue(ipaddr.IPAddress('::1') <= ipaddr.IPAddress('::2'))

    def testNetworkComparison(self):
        # ip1 and ip2 have the same network address
        ip1 = ipaddr.IPv4Network('1.1.1.0/24')
        ip2 = ipaddr.IPv4Network('1.1.1.1/24')
        ip3 = ipaddr.IPv4Network('1.1.2.0/24')

        self.assertTrue(ip1 < ip3)
        self.assertTrue(ip3 > ip2)

        self.assertEqual(ip1.compare_networks(ip2), 0)
        self.assertTrue(ip1._get_networks_key() == ip2._get_networks_key())
        self.assertEqual(ip1.compare_networks(ip3), -1)
        self.assertTrue(ip1._get_networks_key() < ip3._get_networks_key())

        ip1 = ipaddr.IPv6Network('2001::2000/96')
        ip2 = ipaddr.IPv6Network('2001::2001/96')
        ip3 = ipaddr.IPv6Network('2001:ffff::2000/96')

        self.assertTrue(ip1 < ip3)
        self.assertTrue(ip3 > ip2)
        self.assertEqual(ip1.compare_networks(ip2), 0)
        self.assertTrue(ip1._get_networks_key() == ip2._get_networks_key())
        self.assertEqual(ip1.compare_networks(ip3), -1)
        self.assertTrue(ip1._get_networks_key() < ip3._get_networks_key())

        # Test comparing different protocols.
        # Should always raise a TypeError.
        ipv6 = ipaddr.IPv6Network('::/0')
        ipv4 = ipaddr.IPv4Network('0.0.0.0/0')
        self.assertRaises(TypeError, ipv4.__lt__, ipv6)
        self.assertRaises(TypeError, ipv4.__gt__, ipv6)
        self.assertRaises(TypeError, ipv6.__lt__, ipv4)
        self.assertRaises(TypeError, ipv6.__gt__, ipv4)

        # Regression test for issue 19.
        ip1 = ipaddr.IPNetwork('10.1.2.128/25')
        self.assertFalse(ip1 < ip1)
        self.assertFalse(ip1 > ip1)
        ip2 = ipaddr.IPNetwork('10.1.3.0/24')
        self.assertTrue(ip1 < ip2)
        self.assertFalse(ip2 < ip1)
        self.assertFalse(ip1 > ip2)
        self.assertTrue(ip2 > ip1)
        ip3 = ipaddr.IPNetwork('10.1.3.0/25')
        self.assertTrue(ip2 < ip3)
        self.assertFalse(ip3 < ip2)
        self.assertFalse(ip2 > ip3)
        self.assertTrue(ip3 > ip2)

        # Regression test for issue 28.
        ip1 = ipaddr.IPNetwork('10.10.10.0/31')
        ip2 = ipaddr.IPNetwork('10.10.10.0')
        ip3 = ipaddr.IPNetwork('10.10.10.2/31')
        ip4 = ipaddr.IPNetwork('10.10.10.2')
        sorted = [ip1, ip2, ip3, ip4]
        unsorted = [ip2, ip4, ip1, ip3]
        unsorted.sort()
        self.assertEqual(sorted, unsorted)
        unsorted = [ip4, ip1, ip3, ip2]
        unsorted.sort()
        self.assertEqual(sorted, unsorted)
        self.assertRaises(TypeError, ip1.__lt__, ipaddr.IPAddress('10.10.10.0'))
        self.assertRaises(TypeError, ip2.__lt__, ipaddr.IPAddress('10.10.10.0'))

        # <=, >=
        self.assertTrue(ipaddr.IPNetwork('1.1.1.1') <=
                        ipaddr.IPNetwork('1.1.1.1'))
        self.assertTrue(ipaddr.IPNetwork('1.1.1.1') <=
                        ipaddr.IPNetwork('1.1.1.2'))
        self.assertFalse(ipaddr.IPNetwork('1.1.1.2') <=
                        ipaddr.IPNetwork('1.1.1.1'))
        self.assertTrue(ipaddr.IPNetwork('::1') <= ipaddr.IPNetwork('::1'))
        self.assertTrue(ipaddr.IPNetwork('::1') <= ipaddr.IPNetwork('::2'))
        self.assertFalse(ipaddr.IPNetwork('::2') <= ipaddr.IPNetwork('::1'))

    def testStrictNetworks(self):
        self.assertRaises(ValueError, ipaddr.IPNetwork, '192.168.1.1/24',
                          strict=True)
        self.assertRaises(ValueError, ipaddr.IPNetwork, '::1/120', strict=True)

    def testOverlaps(self):
        other = ipaddr.IPv4Network('1.2.3.0/30')
        other2 = ipaddr.IPv4Network('1.2.2.0/24')
        other3 = ipaddr.IPv4Network('1.2.2.64/26')
        self.assertTrue(self.ipv4.overlaps(other))
        self.assertFalse(self.ipv4.overlaps(other2))
        self.assertTrue(other2.overlaps(other3))

    def testEmbeddedIpv4(self):
        ipv4_string = '192.168.0.1'
        ipv4 = ipaddr.IPv4Network(ipv4_string)
        v4compat_ipv6 = ipaddr.IPv6Network('::%s' % ipv4_string)
        self.assertEqual(int(v4compat_ipv6.ip), int(ipv4.ip))
        v4mapped_ipv6 = ipaddr.IPv6Network('::ffff:%s' % ipv4_string)
        self.assertNotEqual(v4mapped_ipv6.ip, ipv4.ip)
        self.assertRaises(ipaddr.AddressValueError, ipaddr.IPv6Network,
                          '2001:1.1.1.1:1.1.1.1')

    # Issue 67: IPv6 with embedded IPv4 address not recognized.
    def testIPv6AddressTooLarge(self):
        # RFC4291 2.5.5.2
        self.assertEqual(ipaddr.IPAddress('::FFFF:192.0.2.1'),
                          ipaddr.IPAddress('::FFFF:c000:201'))
        # RFC4291 2.2 (part 3) x::d.d.d.d 
        self.assertEqual(ipaddr.IPAddress('FFFF::192.0.2.1'),
                          ipaddr.IPAddress('FFFF::c000:201'))

    def testIPVersion(self):
        self.assertEqual(self.ipv4.version, 4)
        self.assertEqual(self.ipv6.version, 6)

    def testMaxPrefixLength(self):
        self.assertEqual(self.ipv4.max_prefixlen, 32)
        self.assertEqual(self.ipv6.max_prefixlen, 128)

    def testPacked(self):
        self.assertEqual(self.ipv4.packed,
                         _cb('\x01\x02\x03\x04'))
        self.assertEqual(ipaddr.IPv4Network('255.254.253.252').packed,
                         _cb('\xff\xfe\xfd\xfc'))
        self.assertEqual(self.ipv6.packed,
                         _cb('\x20\x01\x06\x58\x02\x2a\xca\xfe'
                             '\x02\x00\x00\x00\x00\x00\x00\x01'))
        self.assertEqual(ipaddr.IPv6Network('ffff:2:3:4:ffff::').packed,
                         _cb('\xff\xff\x00\x02\x00\x03\x00\x04\xff\xff'
                            + '\x00' * 6))
        self.assertEqual(ipaddr.IPv6Network('::1:0:0:0:0').packed,
                         _cb('\x00' * 6 + '\x00\x01' + '\x00' * 8))

    def testIpStrFromPrefixlen(self):
        ipv4 = ipaddr.IPv4Network('1.2.3.4/24')
        self.assertEqual(ipv4._ip_string_from_prefix(), '255.255.255.0')
        self.assertEqual(ipv4._ip_string_from_prefix(28), '255.255.255.240')

    def testIpType(self):
        ipv4net = ipaddr.IPNetwork('1.2.3.4')
        ipv4addr = ipaddr.IPAddress('1.2.3.4')
        ipv6net = ipaddr.IPNetwork('::1.2.3.4')
        ipv6addr = ipaddr.IPAddress('::1.2.3.4')
        self.assertEqual(ipaddr.IPv4Network, type(ipv4net))
        self.assertEqual(ipaddr.IPv4Address, type(ipv4addr))
        self.assertEqual(ipaddr.IPv6Network, type(ipv6net))
        self.assertEqual(ipaddr.IPv6Address, type(ipv6addr))

    def testReservedIpv4(self):
        # test networks
        self.assertEqual(True, ipaddr.IPNetwork('224.1.1.1/31').is_multicast)
        self.assertEqual(False, ipaddr.IPNetwork('240.0.0.0').is_multicast)

        self.assertEqual(True, ipaddr.IPNetwork('192.168.1.1/17').is_private)
        self.assertEqual(False, ipaddr.IPNetwork('192.169.0.0').is_private)
        self.assertEqual(True, ipaddr.IPNetwork('10.255.255.255').is_private)
        self.assertEqual(False, ipaddr.IPNetwork('11.0.0.0').is_private)
        self.assertEqual(True, ipaddr.IPNetwork('172.31.255.255').is_private)
        self.assertEqual(False, ipaddr.IPNetwork('172.32.0.0').is_private)

        self.assertEqual(True,
                          ipaddr.IPNetwork('169.254.100.200/24').is_link_local)
        self.assertEqual(False,
                          ipaddr.IPNetwork('169.255.100.200/24').is_link_local)

        self.assertEqual(True,
                          ipaddr.IPNetwork('127.100.200.254/32').is_loopback)
        self.assertEqual(True, ipaddr.IPNetwork('127.42.0.0/16').is_loopback)
        self.assertEqual(False, ipaddr.IPNetwork('128.0.0.0').is_loopback)

        # test addresses
        self.assertEqual(True, ipaddr.IPAddress('224.1.1.1').is_multicast)
        self.assertEqual(False, ipaddr.IPAddress('240.0.0.0').is_multicast)

        self.assertEqual(True, ipaddr.IPAddress('192.168.1.1').is_private)
        self.assertEqual(False, ipaddr.IPAddress('192.169.0.0').is_private)
        self.assertEqual(True, ipaddr.IPAddress('10.255.255.255').is_private)
        self.assertEqual(False, ipaddr.IPAddress('11.0.0.0').is_private)
        self.assertEqual(True, ipaddr.IPAddress('172.31.255.255').is_private)
        self.assertEqual(False, ipaddr.IPAddress('172.32.0.0').is_private)

        self.assertEqual(True,
                          ipaddr.IPAddress('169.254.100.200').is_link_local)
        self.assertEqual(False,
                          ipaddr.IPAddress('169.255.100.200').is_link_local)

        self.assertEqual(True,
                          ipaddr.IPAddress('127.100.200.254').is_loopback)
        self.assertEqual(True, ipaddr.IPAddress('127.42.0.0').is_loopback)
        self.assertEqual(False, ipaddr.IPAddress('128.0.0.0').is_loopback)
        self.assertEqual(True, ipaddr.IPNetwork('0.0.0.0').is_unspecified)

    def testReservedIpv6(self):

        self.assertEqual(True, ipaddr.IPNetwork('ffff::').is_multicast)
        self.assertEqual(True, ipaddr.IPNetwork(2**128-1).is_multicast)
        self.assertEqual(True, ipaddr.IPNetwork('ff00::').is_multicast)
        self.assertEqual(False, ipaddr.IPNetwork('fdff::').is_multicast)

        self.assertEqual(True, ipaddr.IPNetwork('fecf::').is_site_local)
        self.assertEqual(True, ipaddr.IPNetwork(
                'feff:ffff:ffff:ffff::').is_site_local)
        self.assertEqual(False, ipaddr.IPNetwork('fbf:ffff::').is_site_local)
        self.assertEqual(False, ipaddr.IPNetwork('ff00::').is_site_local)

        self.assertEqual(True, ipaddr.IPNetwork('fc00::').is_private)
        self.assertEqual(True, ipaddr.IPNetwork(
                'fc00:ffff:ffff:ffff::').is_private)
        self.assertEqual(False, ipaddr.IPNetwork('fbff:ffff::').is_private)
        self.assertEqual(False, ipaddr.IPNetwork('fe00::').is_private)

        self.assertEqual(True, ipaddr.IPNetwork('fea0::').is_link_local)
        self.assertEqual(True, ipaddr.IPNetwork('febf:ffff::').is_link_local)
        self.assertEqual(False, ipaddr.IPNetwork('fe7f:ffff::').is_link_local)
        self.assertEqual(False, ipaddr.IPNetwork('fec0::').is_link_local)

        self.assertEqual(True, ipaddr.IPNetwork('0:0::0:01').is_loopback)
        self.assertEqual(False, ipaddr.IPNetwork('::1/127').is_loopback)
        self.assertEqual(False, ipaddr.IPNetwork('::').is_loopback)
        self.assertEqual(False, ipaddr.IPNetwork('::2').is_loopback)

        self.assertEqual(True, ipaddr.IPNetwork('0::0').is_unspecified)
        self.assertEqual(False, ipaddr.IPNetwork('::1').is_unspecified)
        self.assertEqual(False, ipaddr.IPNetwork('::/127').is_unspecified)

        # test addresses
        self.assertEqual(True, ipaddr.IPAddress('ffff::').is_multicast)
        self.assertEqual(True, ipaddr.IPAddress(2**128-1).is_multicast)
        self.assertEqual(True, ipaddr.IPAddress('ff00::').is_multicast)
        self.assertEqual(False, ipaddr.IPAddress('fdff::').is_multicast)

        self.assertEqual(True, ipaddr.IPAddress('fecf::').is_site_local)
        self.assertEqual(True, ipaddr.IPAddress(
                'feff:ffff:ffff:ffff::').is_site_local)
        self.assertEqual(False, ipaddr.IPAddress('fbf:ffff::').is_site_local)
        self.assertEqual(False, ipaddr.IPAddress('ff00::').is_site_local)

        self.assertEqual(True, ipaddr.IPAddress('fc00::').is_private)
        self.assertEqual(True, ipaddr.IPAddress(
                'fc00:ffff:ffff:ffff::').is_private)
        self.assertEqual(False, ipaddr.IPAddress('fbff:ffff::').is_private)
        self.assertEqual(False, ipaddr.IPAddress('fe00::').is_private)

        self.assertEqual(True, ipaddr.IPAddress('fea0::').is_link_local)
        self.assertEqual(True, ipaddr.IPAddress('febf:ffff::').is_link_local)
        self.assertEqual(False, ipaddr.IPAddress('fe7f:ffff::').is_link_local)
        self.assertEqual(False, ipaddr.IPAddress('fec0::').is_link_local)

        self.assertEqual(True, ipaddr.IPAddress('0:0::0:01').is_loopback)
        self.assertEqual(True, ipaddr.IPAddress('::1').is_loopback)
        self.assertEqual(False, ipaddr.IPAddress('::2').is_loopback)

        self.assertEqual(True, ipaddr.IPAddress('0::0').is_unspecified)
        self.assertEqual(False, ipaddr.IPAddress('::1').is_unspecified)

        # some generic IETF reserved addresses
        self.assertEqual(True, ipaddr.IPAddress('100::').is_reserved)
        self.assertEqual(True, ipaddr.IPNetwork('4000::1/128').is_reserved)

    def testIpv4Mapped(self):
        self.assertEqual(ipaddr.IPAddress('::ffff:192.168.1.1').ipv4_mapped,
                         ipaddr.IPAddress('192.168.1.1'))
        self.assertEqual(ipaddr.IPAddress('::c0a8:101').ipv4_mapped, None)
        self.assertEqual(ipaddr.IPAddress('::ffff:c0a8:101').ipv4_mapped,
                         ipaddr.IPAddress('192.168.1.1'))

    def testAddrExclude(self):
        addr1 = ipaddr.IPNetwork('10.1.1.0/24')
        addr2 = ipaddr.IPNetwork('10.1.1.0/26')
        addr3 = ipaddr.IPNetwork('10.2.1.0/24')
        addr4 = ipaddr.IPAddress('10.1.1.0')
        self.assertEqual(addr1.address_exclude(addr2),
                         [ipaddr.IPNetwork('10.1.1.64/26'),
                          ipaddr.IPNetwork('10.1.1.128/25')])
        self.assertRaises(ValueError, addr1.address_exclude, addr3)
        self.assertRaises(TypeError, addr1.address_exclude, addr4)
        self.assertEqual(addr1.address_exclude(addr1), [])

    def testHash(self):
        self.assertEqual(hash(ipaddr.IPNetwork('10.1.1.0/24')),
                          hash(ipaddr.IPNetwork('10.1.1.0/24')))
        self.assertEqual(hash(ipaddr.IPAddress('10.1.1.0')),
                          hash(ipaddr.IPAddress('10.1.1.0')))
        # i70
        self.assertEqual(hash(ipaddr.IPAddress('1.2.3.4')),
                          hash(ipaddr.IPAddress(
                    long(ipaddr.IPAddress('1.2.3.4')._ip))))
        ip1 = ipaddr.IPAddress('10.1.1.0')
        ip2 = ipaddr.IPAddress('1::')
        dummy = {}
        dummy[self.ipv4] = None
        dummy[self.ipv6] = None
        dummy[ip1] = None
        dummy[ip2] = None
        self.assertTrue(self.ipv4 in dummy)
        self.assertTrue(ip2 in dummy)

    def testCopyConstructor(self):
        addr1 = ipaddr.IPNetwork('10.1.1.0/24')
        addr2 = ipaddr.IPNetwork(addr1)
        addr3 = ipaddr.IPNetwork('2001:658:22a:cafe:200::1/64')
        addr4 = ipaddr.IPNetwork(addr3)
        addr5 = ipaddr.IPv4Address('1.1.1.1')
        addr6 = ipaddr.IPv6Address('2001:658:22a:cafe:200::1')

        self.assertEqual(addr1, addr2)
        self.assertEqual(addr3, addr4)
        self.assertEqual(addr5, ipaddr.IPv4Address(addr5))
        self.assertEqual(addr6, ipaddr.IPv6Address(addr6))

    def testCompressIPv6Address(self):
        test_addresses = {
            '1:2:3:4:5:6:7:8': '1:2:3:4:5:6:7:8/128',
            '2001:0:0:4:0:0:0:8': '2001:0:0:4::8/128',
            '2001:0:0:4:5:6:7:8': '2001::4:5:6:7:8/128',
            '2001:0:3:4:5:6:7:8': '2001:0:3:4:5:6:7:8/128',
            '2001:0:3:4:5:6:7:8': '2001:0:3:4:5:6:7:8/128',
            '0:0:3:0:0:0:0:ffff': '0:0:3::ffff/128',
            '0:0:0:4:0:0:0:ffff': '::4:0:0:0:ffff/128',
            '0:0:0:0:5:0:0:ffff': '::5:0:0:ffff/128',
            '1:0:0:4:0:0:7:8': '1::4:0:0:7:8/128',
            '0:0:0:0:0:0:0:0': '::/128',
            '0:0:0:0:0:0:0:0/0': '::/0',
            '0:0:0:0:0:0:0:1': '::1/128',
            '2001:0658:022a:cafe:0000:0000:0000:0000/66':
            '2001:658:22a:cafe::/66',
            '::1.2.3.4': '::102:304/128',
            '1:2:3:4:5:ffff:1.2.3.4': '1:2:3:4:5:ffff:102:304/128',
            '::7:6:5:4:3:2:1': '0:7:6:5:4:3:2:1/128',
            '::7:6:5:4:3:2:0': '0:7:6:5:4:3:2:0/128',
            '7:6:5:4:3:2:1::': '7:6:5:4:3:2:1:0/128',
            '0:6:5:4:3:2:1::': '0:6:5:4:3:2:1:0/128',
            }
        for uncompressed, compressed in test_addresses.items():
            self.assertEqual(compressed, str(ipaddr.IPv6Network(uncompressed)))

    def testExplodeShortHandIpStr(self):
        addr1 = ipaddr.IPv6Network('2001::1')
        addr2 = ipaddr.IPv6Address('2001:0:5ef5:79fd:0:59d:a0e5:ba1')
        self.assertEqual('2001:0000:0000:0000:0000:0000:0000:0001/128',
                         addr1.exploded)
        self.assertEqual('0000:0000:0000:0000:0000:0000:0000:0001/128',
                         ipaddr.IPv6Network('::1/128').exploded)
        # issue 77
        self.assertEqual('2001:0000:5ef5:79fd:0000:059d:a0e5:0ba1',
                         addr2.exploded)

    def testIntRepresentation(self):
        self.assertEqual(16909060, int(self.ipv4))
        self.assertEqual(42540616829182469433547762482097946625, int(self.ipv6))

    def testHexRepresentation(self):
        self.assertEqual(hex(0x1020304),
                         hex(self.ipv4))

        self.assertEqual(hex(0x20010658022ACAFE0200000000000001),
                         hex(self.ipv6))

    # backwards compatibility
    def testBackwardsCompability(self):
        self.assertEqual(ipaddr.CollapseAddrList(
            [ipaddr.IPNetwork('1.1.0.0/24'), ipaddr.IPNetwork('1.1.1.0/24')]),
                         [ipaddr.IPNetwork('1.1.0.0/23')])

        self.assertEqual(ipaddr.IPNetwork('::42:0/112').AddressExclude(
            ipaddr.IPNetwork('::42:8000/113')),
                         [ipaddr.IPNetwork('::42:0/113')])

        self.assertTrue(ipaddr.IPNetwork('1::/8').CompareNetworks(
            ipaddr.IPNetwork('2::/9')) < 0)

        self.assertEqual(ipaddr.IPNetwork('1::/16').Contains(
            ipaddr.IPNetwork('2::/16')), False)

        self.assertEqual(ipaddr.IPNetwork('0.0.0.0/0').Subnet(),
                         [ipaddr.IPNetwork('0.0.0.0/1'),
                          ipaddr.IPNetwork('128.0.0.0/1')])
        self.assertEqual(ipaddr.IPNetwork('::/127').Subnet(),
                         [ipaddr.IPNetwork('::/128'),
                          ipaddr.IPNetwork('::1/128')])

        self.assertEqual(ipaddr.IPNetwork('1.0.0.0/32').Supernet(),
                         ipaddr.IPNetwork('1.0.0.0/31'))
        self.assertEqual(ipaddr.IPNetwork('::/121').Supernet(),
                         ipaddr.IPNetwork('::/120'))

        self.assertEqual(ipaddr.IPNetwork('10.0.0.2').IsRFC1918(), True)
        self.assertEqual(ipaddr.IPNetwork('10.0.0.0').IsMulticast(), False)
        self.assertEqual(ipaddr.IPNetwork('127.255.255.255').IsLoopback(), True)
        self.assertEqual(ipaddr.IPNetwork('169.255.255.255').IsLinkLocal(),
                         False)

    def testForceVersion(self):
        self.assertEqual(ipaddr.IPNetwork(1).version, 4)
        self.assertEqual(ipaddr.IPNetwork(1, version=6).version, 6)

    def testWithStar(self):
        self.assertEqual(str(self.ipv4.with_prefixlen), "1.2.3.4/24")
        self.assertEqual(str(self.ipv4.with_netmask), "1.2.3.4/255.255.255.0")
        self.assertEqual(str(self.ipv4.with_hostmask), "1.2.3.4/0.0.0.255")

        self.assertEqual(str(self.ipv6.with_prefixlen),
                         '2001:658:22a:cafe:200::1/64')
        # rfc3513 sec 2.3 says that ipv6 only uses cidr notation for
        # subnets
        self.assertEqual(str(self.ipv6.with_netmask),
                         '2001:658:22a:cafe:200::1/64')
        # this probably don't make much sense, but it's included for
        # compatibility with ipv4
        self.assertEqual(str(self.ipv6.with_hostmask),
                         '2001:658:22a:cafe:200::1/::ffff:ffff:ffff:ffff')

    def testNetworkElementCaching(self):
        # V4 - make sure we're empty
        self.assertFalse(self.ipv4._cache.has_key('network'))
        self.assertFalse(self.ipv4._cache.has_key('broadcast'))
        self.assertFalse(self.ipv4._cache.has_key('hostmask'))

        # V4 - populate and test
        self.assertEqual(self.ipv4.network, ipaddr.IPv4Address('1.2.3.0'))
        self.assertEqual(self.ipv4.broadcast, ipaddr.IPv4Address('1.2.3.255'))
        self.assertEqual(self.ipv4.hostmask, ipaddr.IPv4Address('0.0.0.255'))

        # V4 - check we're cached
        self.assertTrue(self.ipv4._cache.has_key('network'))
        self.assertTrue(self.ipv4._cache.has_key('broadcast'))
        self.assertTrue(self.ipv4._cache.has_key('hostmask'))

        # V6 - make sure we're empty
        self.assertFalse(self.ipv6._cache.has_key('network'))
        self.assertFalse(self.ipv6._cache.has_key('broadcast'))
        self.assertFalse(self.ipv6._cache.has_key('hostmask'))

        # V6 - populate and test
        self.assertEqual(self.ipv6.network,
                         ipaddr.IPv6Address('2001:658:22a:cafe::'))
        self.assertEqual(self.ipv6.broadcast, ipaddr.IPv6Address(
            '2001:658:22a:cafe:ffff:ffff:ffff:ffff'))
        self.assertEqual(self.ipv6.hostmask,
                         ipaddr.IPv6Address('::ffff:ffff:ffff:ffff'))

        # V6 - check we're cached
        self.assertTrue(self.ipv6._cache.has_key('network'))
        self.assertTrue(self.ipv6._cache.has_key('broadcast'))
        self.assertTrue(self.ipv6._cache.has_key('hostmask'))

    def testTeredo(self):
        # stolen from wikipedia
        server = ipaddr.IPv4Address('65.54.227.120')
        client = ipaddr.IPv4Address('192.0.2.45')
        teredo_addr = '2001:0000:4136:e378:8000:63bf:3fff:fdd2'
        self.assertEqual((server, client),
                         ipaddr.IPAddress(teredo_addr).teredo)
        bad_addr = '2000::4136:e378:8000:63bf:3fff:fdd2'
        self.assertFalse(ipaddr.IPAddress(bad_addr).teredo)
        bad_addr = '2001:0001:4136:e378:8000:63bf:3fff:fdd2'
        self.assertFalse(ipaddr.IPAddress(bad_addr).teredo)

        # i77
        teredo_addr = ipaddr.IPv6Address('2001:0:5ef5:79fd:0:59d:a0e5:ba1')
        self.assertEqual((ipaddr.IPv4Address('94.245.121.253'),
                          ipaddr.IPv4Address('95.26.244.94')),
                         teredo_addr.teredo)


    def testsixtofour(self):
        sixtofouraddr = ipaddr.IPAddress('2002:ac1d:2d64::1')
        bad_addr = ipaddr.IPAddress('2000:ac1d:2d64::1')
        self.assertEqual(ipaddr.IPv4Address('172.29.45.100'),
                         sixtofouraddr.sixtofour)
        self.assertFalse(bad_addr.sixtofour)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
